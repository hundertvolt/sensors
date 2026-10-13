"""The bench device's real task graph at MicroPython's own gc default for a fixed window, while the HOST drives
the MQTT client through broker faults; heap figures sampled, every unretrieved task exception printed
(SPECIFICATION.md Part A.11, Part I.4(e)). The bench test completes the module import with the device's name."""

import asyncio
import gc
import sys
import time

import sensortask_ as sensortask_bench  # type: ignore[import-not-found]  # completed from the device TOML carrying the client

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asyncio.events import _Context

# Explicit, never inherited: mpremote's raw-REPL soft reset keeps whatever threshold was in force (MEASUREMENTS M3.8).
gc.threshold(-1)
# @tunable l4.mqtt_at_default_gc_window_s = 420
_WINDOW_S = 420  # the host's whole fault timeline fits inside it, with its own stop well before the end
# @tunable l4.mqtt_at_default_gc_sample_s = 10
_SAMPLE_S = 10


def _report_unretrieved(_loop: object, context: "_Context") -> None:
    # The PC tiers' always-printing report, copied: the host gate greps this output for memory markers, and the
    # firmware's own report is silent at DebugLevel 0 (Part I.4(e)).
    try:
        try:
            print("UNRETRIEVED TASK EXCEPTION:", context["message"])
            sys.print_exception(context["exception"])
        finally:
            context["exception"] = None
            context["future"] = None
    except Exception:  # an escape would end asyncio.run()
        pass


async def _run() -> None:
    asyncio.get_event_loop().set_exception_handler(_report_unretrieved)  # before main(): the firmware then keeps it
    print(f"GC_THRESHOLD={gc.threshold()}")
    main_task = asyncio.get_event_loop().create_task(sensortask_bench.main())
    started = time.ticks_ms()
    samples = 0
    try:
        while time.ticks_diff(time.ticks_ms(), started) < _WINDOW_S * 1000:
            await asyncio.sleep(_SAMPLE_S)
            print(f"MEM_SAMPLE free={gc.mem_free()} alloc={gc.mem_alloc()}")  # no collect: the reactive default is under test
            samples += 1
    finally:
        main_task.cancel()
    print(f"SAMPLES={samples}")
    print("RESULT: PASS window complete")


try:
    asyncio.run(_run())
except Exception as e:  # a failure here is a result, reported rather than raised into the harness
    print(f"RESULT: FAIL {e!r}")
