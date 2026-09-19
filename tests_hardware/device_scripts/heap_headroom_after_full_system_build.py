"""Isolated-driver device script: how much GC heap is actually left on real silicon once the whole
dev object graph exists. Reports free/allocated bytes and the largest single block still obtainable
- the figure that decides whether an allocation fails, not total free (SPECIFICATION.md Part I)."""

import asyncio
import gc

import sensortask_dev

# Doubling/halving search bounds for the largest contiguous block. 64 B is below anything worth
# reporting; 192 KB is already above the RP2040's whole 264 KB SRAM, so the search always converges
# from a real failure rather than running off the top.
_PROBE_MIN = 64
_PROBE_MAX = 192 * 1024
# Rereads allowed when the probe pins its own buffer (see _report_checked). Three is generous: one
# has always been enough on the twin, at every heap size tried.
_PROBE_RETRIES = 3

# Floors, not expected values: measured 2026-09-11 (free=130720, largest_block=116032) and set
# ~23%/~31% under. Raise them only against a fresh measurement. build_system() carries the boot
# collects (Part I.4(f.1)), and the figure is suite-position-dependent - MEASUREMENTS 7D.2.
_MIN_FREE = 100_000
_MIN_LARGEST_BLOCK = 80_000


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


def _report_checked(label: str) -> "tuple[int, int]":
    # A probe run can pin its own buffer through a stale root; every later attempt then fails and the
    # search converges on the pinned size - always _PROBE_MAX >> k, e.g. 49,152 (MEASUREMENTS 7F.8).
    # Unretried that is a false FAIL against the floor below, on an image that is fine.
    free, largest, retained = _report(label)
    attempt = 0
    while retained >= _PROBE_MIN and attempt < _PROBE_RETRIES:
        attempt += 1
        free, largest, retained = _report(f"{label}_retry{attempt}")
    if retained >= _PROBE_MIN:
        print(f"WARNING {label}: probe still holding {retained} B after {_PROBE_RETRIES} rereads - largest_block is a floor, not a figure")
    return free, largest


async def _main() -> None:
    _report_checked("baseline")  # interpreter + this script only, before anything else exists
    try:
        await sensortask_dev.build_system(cfg_path="", web_host="127.0.0.1", web_port=8080)
    except Exception as e:
        print(f"RESULT: FAIL build_system() raised on real hardware: {e!r}")
        return
    # Deliberately measured at MicroPython's own reactive-only default first: a headroom figure that
    # only holds with a proactive threshold isn't headroom (CLAUDE.md's memory-safety ladder).
    free, largest = _report_checked("after_build_system")
    # Control first at the unchanged threshold, so the next line's difference cannot be confused
    # with a difference between two probe runs at the same position (MEASUREMENTS 7F.8).
    _report_checked("after_build_system_control")
    gc.threshold(32768)  # what buildgen.codegen.generate_boot_entry_source() sets in the real firmware
    _report_checked("after_build_system_production_threshold")

    if free < _MIN_FREE:
        print(f"RESULT: FAIL free heap after a full system build fell below the floor: {free} < {_MIN_FREE}")
        return
    if largest < _MIN_LARGEST_BLOCK:
        print(f"RESULT: FAIL largest obtainable block fell below the floor: {largest} < {_MIN_LARGEST_BLOCK}")
        return
    print(f"RESULT: PASS real heap headroom after a full system build: {free} B free, {largest} B largest single block")


asyncio.run(_main())
