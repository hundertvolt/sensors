"""Isolated-driver device script: the real production boot plus a periodic heap dump, so the host
can hold a full ceiling of connections open and see what the heap looks like AT PEAK. The DUT emits
only mem_info(1) - the one value with no other way out (SPECIFICATION.md Part E.9)."""

import asyncio
import gc
import time

import micropython
import sensortask_dev

# Sampling only, never a collect before a dump: the ceiling question is what the allocator has to
# work with while requests are in flight, garbage included. The threshold is the boot entry's own,
# set rather than inherited - it is what MEASUREMENTS 7R.2 was taken at.
gc.threshold(32768)
_SAMPLE_INTERVAL_MS = 1000
# Long enough for the host to see this boot serve, settle, and drive several full-ceiling rounds.
_WINDOW_S = 90


def _dump(label: str) -> None:
    # heap_map.parse_labelled()'s own delimiters, matched exactly - it keys on the label and
    # requires the ENDMAP to repeat it; mem_info(1) writes to this board's USB serial console.
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
    # No readiness probe from in here: a request driven from this process would share the heap
    # under measurement, which is the whole thing Part E.9 forbids. The host polls the real HTTP
    # port itself, once main.py's own server has gone quiet (harness.wait_for_script_server()).
    await asyncio.sleep(20)
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
