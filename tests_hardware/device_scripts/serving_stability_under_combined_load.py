"""Isolated-driver device script: the real production boot at MicroPython's OWN reactive gc default,
so the host can hammer every heavy REST endpoint while every sensor task runs and see whether the
board serves it all without a single allocation failure (CLAUDE.md's I.4(e) bar)."""

import asyncio
import gc
import time

import micropython
import sensortask_dev

# Set explicitly, not merely left alone: mpremote interrupts main.py but does NOT reset the
# interpreter, so the boot entry's own gc.threshold(32768) is still in force when this starts
# (SPECIFICATION.md Part I.4). -1 is MicroPython's own reactive default.
gc.threshold(-1)
_SAMPLE_INTERVAL_MS = 5000
_COLLECT_BEFORE_SAMPLE = False  # combined_load_sweep.py --margin sets True: each dump then shows only the live
# set, the free-heap margin under load. Instrumentation, never the fix: it also cleans the heap every
# sample, so a margin run's stability verdict is not evidence - the plain run's is.
_WINDOW_S = 150


def _dump(label: str) -> None:
    if _COLLECT_BEFORE_SAMPLE:
        gc.collect()
    print(f"=== MAP {label} ===")
    micropython.mem_info(1)
    print(f"=== ENDMAP {label} ===")


async def _sampler() -> None:
    started = time.ticks_ms()
    index = 0
    while time.ticks_diff(time.ticks_ms(), started) < _WINDOW_S * 1000:
        _dump(f"t{index:03d}_{time.ticks_diff(time.ticks_ms(), started)}ms")
        index += 1
        await asyncio.sleep_ms(_SAMPLE_INTERVAL_MS)


async def _run() -> None:
    print(f"GC_THRESHOLD={gc.threshold()}")
    main_task = asyncio.get_event_loop().create_task(sensortask_dev.main())
    await asyncio.sleep(20)  # the host waits for READY, then drives the load itself (Part E.9)
    _dump("after_boot")
    print("READY")
    try:
        await _sampler()
    finally:
        main_task.cancel()
    print("RESULT: PASS window complete")


try:
    asyncio.run(_run())
except Exception as e:  # a failure here is a result, reported rather than raised into the harness
    print(f"RESULT: FAIL {e!r}")
