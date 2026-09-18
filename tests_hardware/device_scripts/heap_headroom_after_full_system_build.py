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

# Floors, not expected values. Measured on the real dev board at MicroPython 1.29.0 (2026-09-11):
# free=130720, largest_block=116032 after a full build_system(). These sit ~23%/~31% below that, so
# an ordinary allocation-pattern change won't trip them but a real regression will - a new static
# buffer, or a future MicroPython bump moving more code into SRAM the way 1.29 already did with the
# interpreter core (12,918 B, Part F.5.3). Raise them only with a fresh measurement to point at.
# Two facts about what this figure now means. build_system() carries the boot-confined placement
# reset (Part I.4(f.1)), so largest_block is the *with-collects* layout - a reading below the floor
# means the layout regressed past what those collects recover, not that they are absent. And the
# number depends on WHEN in a suite it is taken: Board.run_isolated() interrupts the running
# firmware without resetting, so a freshly-flashed standalone run measures a young heap and a run
# deep in a suite measures an aged one - 95,104 B against 28,864 B on the same firmware, with free
# unchanged (HEAP_FRAGMENTATION_MEASUREMENTS.md 7D.2). Compare only like suite positions.
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


def _report(label: str) -> "tuple[int, int]":
    gc.collect()
    free, largest = gc.mem_free(), _largest_block()
    print(f"HEAP {label}: free={free} alloc={gc.mem_alloc()} largest_block={largest}")
    return free, largest


async def _main() -> None:
    _report("baseline")  # interpreter + this script only, before anything else exists
    try:
        await sensortask_dev.build_system(cfg_path="", web_host="127.0.0.1", web_port=8080)
    except Exception as e:
        print(f"RESULT: FAIL build_system() raised on real hardware: {e!r}")
        return
    # Deliberately measured at MicroPython's own reactive-only default first: a headroom figure that
    # only holds with a proactive threshold isn't headroom (CLAUDE.md's memory-safety ladder).
    free, largest = _report("after_build_system")
    gc.threshold(32768)  # what buildgen.codegen.generate_boot_entry_source() sets in the real firmware
    _report("after_build_system_production_threshold")

    if free < _MIN_FREE:
        print(f"RESULT: FAIL free heap after a full system build fell below the floor: {free} < {_MIN_FREE}")
        return
    if largest < _MIN_LARGEST_BLOCK:
        print(f"RESULT: FAIL largest obtainable block fell below the floor: {largest} < {_MIN_LARGEST_BLOCK}")
        return
    print(f"RESULT: PASS real heap headroom after a full system build: {free} B free, {largest} B largest single block")


asyncio.run(_main())
