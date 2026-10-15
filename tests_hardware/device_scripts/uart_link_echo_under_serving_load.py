"""The serving board's own UART initiator carries a multi-chunk SET under HTTP load: the generated device module's main()
boots as a task, and once the host's load reaches its webserver the initiator SETs a multi-chunk echo and GETs it back
round after round, each answer compared byte for byte; facts out, the host test judges (SPECIFICATION.md J.7)."""

import asyncio
import time

import _bench_device as device  # rendered: the bench device's generated module

from asy_print_log import PrintLog
from asy_system_service import BOOT_DONE
from asy_uart_comm import ROLE_INITIATOR
from asy_uart_link_driver import UARTLinkDriver

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import _ERRORS_KEPT, done, errors, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts
    from machine import WDT

    from asy_uart_comm import UARTComm

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_CMD_ECHO = 0x02  # source: src/asy_uart_link_driver.py _CMD_ECHO (a folded const, unreadable at run time)
# A fixed wait, never an in-process readiness request: one would share the heap under the load (SPECIFICATION.md E.9).
# @tunable l3.heap_under_connection_ceiling_boot_wait_s = 20
_BOOT_WAIT_S = 20
# At least this many rounds, and rounds until the window has passed, so the echoes span the host's whole load.
# @tunable l3.uart_link_echo_under_serving_load_rounds = 20
_ROUNDS = 20
# @tunable l3.uart_link_echo_under_serving_load_window_ms = 30000
_WINDOW_MS = 30000
# @tunable l3.uart_link_echo_under_serving_load_load_wait_ms = 90000
_LOAD_WAIT_MS = 90000
# @tunable l3.uart_link_echo_under_serving_load_poll_ms = 250
_POLL_MS = 250
# The product's own unretrieved-task report at the error level, so it prints whatever level the board's config holds.
_REPORT = PrintLog(level=1, name="UNRETRIEVED TASK EXCEPTION:")


async def _echo_rounds(wdt: "WDT", comm: "UARTComm") -> None:
    # Each round's pattern is written into the one sent buffer, the answer copied into the one scratch of its length.
    size = comm._payload_size * 2 + 7  # three data chunks: a multi-chunk train both ways
    sent = bytearray(size)
    scratch = bytearray(size)
    intact = 0
    failed: list[str] = []
    total_failed = 0
    round_no = 0
    started = time.ticks_ms()
    while round_no < _ROUNDS or time.ticks_diff(time.ticks_ms(), started) < _WINDOW_MS:
        for i in range(size):
            sent[i] = (round_no * 31 + i) & 0xFF
        stored = await comm.uart_set(_CMD_ECHO, sent)
        answer = await comm.uart_get(_CMD_ECHO) if stored else None
        if answer is not None and len(answer) == size and answer.copy_into(scratch) and scratch == sent:
            intact += 1
        else:
            total_failed += 1
            if len(failed) < _ERRORS_KEPT:
                failed.append("round " + str(round_no) + ": stored " + str(stored) + ", answer " + ("None" if answer is None else str(len(answer)) + " B"))
        round_no += 1
        wdt.feed()
        await asyncio.sleep_ms(0)
    fact("size", size)
    fact("total", round_no)
    fact("intact", intact)
    errors("echo_failures", total_failed, failed)


def _initiator() -> "UARTLinkDriver | None":
    # The generated module's uart_link instance whose role initiates, found by its label in BENCH, never named here.
    for label, instance in BENCH["instances"].items():
        link = getattr(device, label, None)
        if instance["driver"] == "uart_link" and isinstance(link, UARTLinkDriver) and link._role == ROLE_INITIATOR:
            return link
    return None


async def _load_seen(wdt: "WDT") -> bool:
    # Whether the host's load reached the webserver: its own open-connection count, read without a request.
    webserver = device.webserver
    started = time.ticks_ms()
    while webserver is not None and time.ticks_diff(time.ticks_ms(), started) < _LOAD_WAIT_MS:
        if webserver._open_conns.value:
            return True
        wdt.feed()
        await asyncio.sleep_ms(_POLL_MS)
    return False


async def _run() -> None:
    asyncio.get_event_loop().set_exception_handler(_REPORT.report_unretrieved)  # before main(): the firmware keeps it
    wdt = arm()
    # Production config path: the only writes it can cause are the ones a production boot makes anyway (an absent
    # file's first write, a malformed file's repair).
    main_task = asyncio.get_event_loop().create_task(device.main(watchdog=wdt))
    try:
        await fed_sleep_ms(wdt, _BOOT_WAIT_S * 1000)
        link = _initiator()
        fact("initiator_found", link is not None)
        if link is not None:
            fact("before", await link.get_link_status())
            fact("load_seen", await _load_seen(wdt))
            await _echo_rounds(wdt, link._comm)
            fact("after", await link.get_link_status())
    finally:
        main_task.cancel()
        sysfunct = device.sysfunct
        if sysfunct is not None:
            sysfunct.boot_phase(BOOT_DONE)  # the reset after this script reads as the harness's, never a boot failure
    done()


asyncio.run(_run())
