"""Isolated-driver device script: the real production boot plus a periodic heap dump, so the host
can hold a full ceiling of connections open and see what the heap looks like AT PEAK. The DUT emits
only mem_info(1) - the one value with no other way out (SPECIFICATION.md Part E.9)."""

import asyncio
import gc
import time

import _bench_device as device  # rendered: the bench device's generated module

from asy_print_log import PrintLog

# @include _shared/facts.py
# @include _shared/map_dump.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.map_dump import dump
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Sampling only, never a collect before a dump: the ceiling question is what the allocator has to work with while
# requests are in flight, garbage included. The threshold is the boot entry's own, set rather than inherited.
# @tunable gc.threshold_bytes = 32768
gc.threshold(32768)
# @tunable l3.heap_under_connection_ceiling_sample_interval_ms = 1000
_SAMPLE_INTERVAL_MS = 1000
# Long enough for the host to see this boot serve, settle, and drive several full-ceiling rounds.
# @tunable l3.heap_under_connection_ceiling_window_s = 90
_WINDOW_S = 90
# A fixed wait, never an in-process readiness request: one would share the heap under measurement (Part E.9).
# @tunable l3.heap_under_connection_ceiling_boot_wait_s = 20
_BOOT_WAIT_S = 20
# The product's own unretrieved-task report at the error level, so it prints whatever level the board's config holds.
_REPORT = PrintLog(level=1, name="UNRETRIEVED TASK EXCEPTION:")


async def _run() -> None:
    asyncio.get_event_loop().set_exception_handler(_REPORT.report_unretrieved)  # before main(): the firmware keeps it
    fact("gc_threshold", gc.threshold())
    wdt = arm()
    # Production config path: the only writes it can cause are the ones a production boot makes anyway (an absent
    # file's first write, a malformed file's repair).
    main_task = asyncio.get_event_loop().create_task(device.main(watchdog=wdt))
    try:
        await fed_sleep_ms(wdt, _BOOT_WAIT_S * 1000)
        dump("after_boot")
        print("READY")  # the banner the host waits on before its load
        await _sampler()
    finally:
        main_task.cancel()
    done()


async def _sampler() -> None:
    started = time.ticks_ms()
    index = 0
    while time.ticks_diff(time.ticks_ms(), started) < _WINDOW_S * 1000:
        dump(f"t{index:03d}_{time.ticks_diff(time.ticks_ms(), started)}ms")
        index += 1
        await asyncio.sleep_ms(_SAMPLE_INTERVAL_MS)


asyncio.run(_run())
