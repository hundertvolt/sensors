"""The bench device's real task graph at MicroPython's own gc default for a fixed window, while the HOST drives
the MQTT client through broker faults: free heap sampled without a collect, every unretrieved task exception
reported by the product's own handler (SPECIFICATION.md Part A.12, Part I.4(e))."""

import asyncio
import gc
import time

import _bench_device as device  # rendered: the bench device's generated module

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/unretrieved.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.unretrieved import report_unretrieved
    from _shared.watchdog import arm, fed_sleep_ms

# Explicit, never inherited: mpremote's raw-REPL soft reset keeps whatever threshold was in force (MEASUREMENTS M3.8).
gc.threshold(-1)
_WINDOW_S = 420  # the host's whole fault timeline fits inside it, with its own stop well before the end
_SAMPLE_S = 10


async def _run() -> None:
    report_unretrieved()  # before main(): the firmware then keeps it
    fact("gc_threshold", gc.threshold())
    wdt = arm()
    # Production config path: the only writes it can cause are the ones a production boot makes anyway (an absent
    # file's first write, a malformed file's repair).
    main_task = asyncio.get_event_loop().create_task(device.main(watchdog=wdt))
    started = time.ticks_ms()
    free: list[int] = []
    try:
        while time.ticks_diff(time.ticks_ms(), started) < _WINDOW_S * 1000:
            await fed_sleep_ms(wdt, _SAMPLE_S * 1000)
            free.append(gc.mem_free())  # no collect: the reactive default is under test
    finally:
        main_task.cancel()
    fact("mem_free", free)
    done()


asyncio.run(_run())
