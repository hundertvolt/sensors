"""Isolated-driver device script: the real production boot plus a periodic heap dump, so the host
can hold a full ceiling of connections open and see what the heap looks like AT PEAK. The DUT emits
only mem_info(1) - the one value with no other way out (SPECIFICATION.md Part E.9)."""

import asyncio
import gc
import sys
import time

import micropython
import sensortask_dev

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asyncio.events import _Context

# Sampling only, never a collect before a dump: the ceiling question is what the allocator has to
# work with while requests are in flight, garbage included. The threshold is the boot entry's own,
# set rather than inherited - it is what MEASUREMENTS archive 7R.2 was taken at.
# @tunable gc.threshold_bytes = 32768
gc.threshold(32768)
# @tunable l3.heap_under_connection_ceiling_sample_interval_ms = 1000
_SAMPLE_INTERVAL_MS = 1000
# Long enough for the host to see this boot serve, settle, and drive several full-ceiling rounds.
# @tunable l3.heap_under_connection_ceiling_window_s = 90
_WINDOW_S = 90
# @tunable l3.heap_under_connection_ceiling_boot_wait_s = 20
_BOOT_WAIT_S = 20


def _report_unretrieved(_loop: object, context: "_Context") -> None:
    # The PC tiers' always-printing report, copied: this board-side script cannot import digital_twin/, the host gate
    # greps its output for memory markers, and the firmware's own report is silent at DebugLevel 0 (Part I.4(e)).
    try:
        try:
            print("UNRETRIEVED TASK EXCEPTION:", context["message"])
            sys.print_exception(context["exception"])
        finally:
            context["exception"] = None
            context["future"] = None
    except Exception:  # an escape would end asyncio.run()
        pass


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
    asyncio.get_event_loop().set_exception_handler(_report_unretrieved)  # before main(): the firmware then keeps it
    print(f"GC_THRESHOLD={gc.threshold()}")
    main_task = asyncio.get_event_loop().create_task(sensortask_dev.main())
    # No readiness probe from in here: a request driven from this process would share the heap
    # under measurement, which is the whole thing Part E.9 forbids. The host polls the real HTTP
    # port itself, once main.py's own server has gone quiet (harness.wait_for_script_server()).
    await asyncio.sleep(_BOOT_WAIT_S)
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
