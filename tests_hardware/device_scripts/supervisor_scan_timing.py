"""Isolated-driver device script: SPECIFICATION.md Part N's system.scan_budget on real hardware - one supervisor pass
with every supervised task ended, its SYSTEM entries persisted to FRAM, timed from the feed before it to the feed after
the reboot's entry, then the countdown to the reset, which is stubbed: no flash write, no reset, no record left."""

import asyncio
import time

import asy_spi_driver
import asy_system_service
from asy_fram_manager import FRAMManager
from asy_print_log import LogConfig
from asy_system_service import SystemService

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _mpy_shed.time_mp import _TicksMs
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts
    from machine import WDT

    from asy_base_classes import TaskStarter

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_TASKS = 5  # more than the three ends the budget allows before the pass escalates, so the count is the worst case
_HISTORY_LENGTH = 10  # source: src/asy_print_log.py _DEFAULT_HISTORY_LENGTH - the product's SYSTEM history
_LEVEL = 0  # source: src/asy_system_service.py _VAL_DEBUG_LEVEL default
_STEP_MS = 500  # the script's own feeds while the supervisor starves the watchdog for the reset
_WAIT_STEPS = 40  # 20 s: the clean pass, the dying pass and the reset countdown, with room


class _TimedWatchdog:
    # Forwards every supervisor feed to the real watchdog and stamps it.
    def __init__(self, wdt: "WDT") -> None:
        self._wdt = wdt
        self.feeds: list[_TicksMs] = []

    def feed(self) -> None:
        self.feeds.append(time.ticks_ms())
        self._wdt.feed()


async def _main() -> None:
    wdt = arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "fram")
    bus = BENCH["bus"][chip["bus"]]
    spi = asy_spi_driver.SPI(bus["id"], sck_pin=bus["sck_pin"], mosi_pin=bus["mosi_pin"], miso_pin=bus["miso_pin"])
    fram = FRAMManager(spi, chip["cs_pin"], BENCH["fram_max_size"])
    await fram.setup()
    fact("setup", fram.initialized)
    timed = _TimedWatchdog(wdt)
    sysfunct = SystemService(_ntp_never_synced, watchdog=timed, log=LogConfig(fram, _HISTORY_LENGTH, _LEVEL))  # type: ignore[arg-type]
    await sysfunct.pr.setup()
    fact("initialized", sysfunct.pr.initialized)
    if not (fram.initialized and sysfunct.pr.initialized):
        done()
        return
    reset_at: list[_TicksMs] = []
    asy_system_service.system_reset = lambda: reset_at.append(time.ticks_ms())  # stubbed: the board keeps running
    end = asyncio.Event()
    try:
        fact("cleared_first", await sysfunct.pr.reset())
        await sysfunct.start_tasks([_starter(end) for _ in range(_TASKS)], task_names=[f"t{n}" for n in range(_TASKS)])
        supervisor = asyncio.create_task(sysfunct.supervise_tasks())
        ended_at = 0
        for _ in range(_WAIT_STEPS):
            await asyncio.sleep_ms(_STEP_MS)
            wdt.feed()
            if not ended_at and timed.feeds:
                ended_at = len(timed.feeds)  # the clean pass fed: every task ends before the next one
                end.set()
            if reset_at:
                break
        supervisor.cancel()
        try:
            await supervisor
        except asyncio.CancelledError:
            pass
        feeds = timed.feeds
        fact("feeds", len(feeds))
        if ended_at and len(feeds) > ended_at:
            fact("scan_feed_to_feed_ms", time.ticks_diff(feeds[ended_at], feeds[ended_at - 1]))
        if reset_at and feeds:
            fact("feed_to_reset_ms", time.ticks_diff(reset_at[0], feeds[-1]))
        fact("system", (await sysfunct.get_error_counter())["SYSTEM"])
    finally:
        record = asy_system_service.mem_backup(0)  # the escalation's record, cleared as the next boot would
        for i in range(len(record)):
            record[i] = 0
        fact("cleared_last", await sysfunct.pr.reset())
    done()


def _starter(end: asyncio.Event) -> "TaskStarter":
    def start() -> "asyncio.Task[None]":
        return asyncio.create_task(_ends_on(end))

    return start


async def _ends_on(end: asyncio.Event) -> None:
    await end.wait()


async def _ntp_never_synced() -> bool:
    return False


asyncio.run(_main())
