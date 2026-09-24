"""Isolated-driver device script: what the heap looks like on real silicon once the whole dev object
graph exists - how much the survivors cost, how big a contiguous block is still obtainable, and
where the survivors sit (the block map, measured host-side by heap_map.py). SPECIFICATION.md I."""

import asyncio
import gc

import micropython
import sensortask_dev

# Explicit, never inherited: mpremote's raw-REPL soft reset keeps the boot entry's threshold (rp2's
# main.c runs gc_init() once, outside the soft-reset loop), so this script's own first arm read 32768
# until 2026-09-24 despite reporting a reactive-default figure (MEASUREMENTS 0B.7).
gc.threshold(-1)
# Doubling/halving search bounds for the largest contiguous block. 64 B is below anything worth
# reporting; 192 KB is already above the RP2040's whole 264 KB SRAM, so the search always converges
# from a real failure rather than running off the top.
_PROBE_MIN = 64
_PROBE_MAX = 192 * 1024
# Rereads allowed when the probe pins its own buffer (see _report_checked). Three is generous: one
# has always been enough on the twin, at every heap size tried.
_PROBE_RETRIES = 3

# The largest contiguous allocation this firmware could be asked to make when these floors were
# set, measured against the code rather than a board reading: 4,096 B as configured, 16,384 B worst
# case through microdot's own max_body_length default (MEASUREMENTS 7A.9).
_WORST_CASE_ALLOCATION = 16_384
# That worst case fell to 2,048 B once both caps were bound (SPECIFICATION.md Part I.6). Not
# re-derived on purpose: these are a regression tripwire with margin, not a restatement of the
# requirement, so lowering them would only cost sensitivity.

# Requirement, not a fitted floor: room for the worst case twice over. 32,768 B is 12% of the
# RP2040's 264 KB SRAM, where the retired 80,000 B floor was 30% - a third of physical memory, which
# is what the owner retired it for on 2026-09-19. Nothing here may be raised to fit a reading.
_MIN_LARGEST_BLOCK = 2 * _WORST_CASE_ALLOCATION
# Survivor volume. Every [HW] reading of a fully built dev graph is 87,760-87,968 B, so this is
# ~14% over the measured cost of the object graph itself, and catches a regression that adds
# permanent objects rather than one that scatters them.
_MAX_USED = 100_000


def _largest_block() -> int:
    # Binary search on bytearray(n), which allocates one contiguous run - the same shape a real
    # json.dumps()/read buffer needs, and the reason total free can be ample while an allocation
    # still fails on a fragmented heap.
    gc.collect()
    low, high = 0, _PROBE_MAX
    while low < high:
        mid = (low + high + 1) // 2
        if mid < _PROBE_MIN:
            break
        try:
            probe = bytearray(mid)
        except MemoryError:
            high = mid - 1
        else:
            del probe
            low = mid
        gc.collect()
    return low


def _report(label: str) -> "tuple[int, int, int]":
    gc.collect()
    free, base = gc.mem_free(), gc.mem_alloc()
    largest = _largest_block()
    gc.collect()
    retained = gc.mem_alloc() - base
    print(f"HEAP {label}: free={free} alloc={gc.mem_alloc()} largest_block={largest} retained={retained}")
    return free, largest, retained


def _dump_map(label: str) -> None:
    # The layout itself, for the host side to measure: mem_info(1) prints the per-block map and the
    # exact largest free run, allocating nothing. tests_hardware/heap_map.py parses it; the device
    # cannot, the map going to the platform print rather than to sys.stdout.
    gc.collect()
    print(f"=== MAP {label} ===")
    micropython.mem_info(1)
    print(f"=== ENDMAP {label} ===")


def _report_checked(label: str) -> "tuple[int, int]":
    # A probe run can pin its own buffer through a stale root; every later attempt then fails and the
    # search converges on the pinned size - always _PROBE_MAX >> k, e.g. 49,152 (MEASUREMENTS 7F.8).
    # Unretried that is a false FAIL against the contiguity check below, on a healthy image.
    free, largest, retained = _report(label)
    attempt = 0
    while retained >= _PROBE_MIN and attempt < _PROBE_RETRIES:
        attempt += 1
        free, largest, retained = _report(f"{label}_retry{attempt}")
    if retained >= _PROBE_MIN:
        print(f"WARNING {label}: probe still holding {retained} B after {_PROBE_RETRIES} rereads - largest_block is a floor, not a figure")
    return free, largest


async def _main() -> None:
    print(f"GC_THRESHOLD={gc.threshold()}")  # set at module level, so the build runs at the (e) stage
    _report_checked("baseline")
    # The "before" half of the placement delta: what the BOOT adds up high is attributable only by
    # comparing against what was already there, which is what makes that check independent of the
    # suite position (MEASUREMENTS 7D.2, 7G.5).
    _dump_map("baseline")
    try:
        await sensortask_dev.build_system(cfg_path="", web_host="127.0.0.1", web_port=8080)
    except Exception as e:
        print(f"RESULT: FAIL build_system() raised on real hardware: {e!r}")
        return
    # Deliberately measured at MicroPython's own reactive-only default first: a headroom figure that
    # only holds with a proactive threshold isn't headroom (CLAUDE.md's memory-safety ladder).
    free, largest = _report_checked("after_build_system")
    used = gc.mem_alloc()  # read here, not after the threshold lines below, so all three checks are one position
    _dump_map("after_build_system")
    # Control first at the unchanged threshold, so the next line's difference cannot be confused
    # with a difference between two probe runs at the same position (MEASUREMENTS 7F.8).
    _report_checked("after_build_system_control")
    gc.threshold(32768)  # what buildgen.codegen.generate_boot_entry_source() sets in the real firmware
    print(f"GC_THRESHOLD={gc.threshold()}")
    _report_checked("after_build_system_production_threshold")

    # Two of the three checks the owner's 2026-09-19 statement asks for. The third - that long-lived
    # objects have not colonised the top of the heap - needs the block map, so it is asserted host-
    # side in flash/test_memory_stress.py against the dump above.
    if used > _MAX_USED:
        print(f"RESULT: FAIL the built object graph holds more than it should: {used} > {_MAX_USED} B allocated")
        return
    if largest < _MIN_LARGEST_BLOCK:
        print(f"RESULT: FAIL no room for the worst real allocation twice over: {largest} < {_MIN_LARGEST_BLOCK} B contiguous")
        return
    print(f"RESULT: PASS {used} B allocated, {free} B free, {largest} B contiguous - {largest // _WORST_CASE_ALLOCATION}x the worst reachable allocation")


asyncio.run(_main())
