"""Generic system-housekeeping service shared by every sensortask-*.py device file: uptime
counting, a one-per-boot "boot signature" (NTP timestamp once synced, else a random fallback after
a wait), reboot/reboot-to-bootloader with FRAM storage-pause coordination, timed storage pause (the
REST `mempause` command), a staggered generic startup sequence driven by each driver's own
get_task_starters()/get_timer_starters(), and the top-level task supervisor loop (restart dead
tasks, decay/accumulate a failure counter, feed the watchdog, reboot past the failure budget).

Contract: every method returns a well-defined value and never raises - including the caller-
supplied ntp_is_synced callback and every driver-supplied task/timer starter, none of which this
file controls. reboot_system()/reboot_bootloader() deliberately trigger a real
machine.reset()/machine.bootloader() after _RESET_DELAY; that's the intended effect, not a failure
to guard against.
"""

import asyncio
import random
import time

from machine import WDT, Timer
from machine import bootloader as system_bootloader
from machine import reset as system_reset
from micropython import const

from base_classes import LockedCounter, LockedValue
from print_log import PrintLogHistory, PrintLogHistoryStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any

    from asy_fram_manager import AsyFramManager

_RESET_DELAY = const(4)  # seconds between reset command and execution (keep < watchdog timeout!)
_MAX_STORAGE_PAUSE = const(3600)  # one hour max pause for FRAM
_NTP_WAIT_TIME = const(120)  # 2 mins until random boot signature is used
_TIMER_BASE_PERIOD = const(1000)  # milliseconds for sensor triggers base period
_TASK_CHECK_TIME = const(2)  # seconds period to check running tasks (keep << watchdog timeout!)
_TASK_FAIL_INCREMENT = const(100)  # absolute value important for decrease time,...
_TASK_FAIL_MAX = const(300)  # ...ratio important for triggering reset (multiple errors)


class SystemService:
    def __init__(
        self,
        asy_ntp_callback: "Callable[[], Coroutine[Any, Any, bool]]",
        watchdog: WDT | None = None,
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        # callback for starting and stopping permanent storage communication
        self.storage_pause: Callable[[bool], None] | None = None
        if fram is None:
            self.pr = PrintLogHistory(history_length, debug)
            self.pr.one("Init with memory logging.")
        else:
            self.pr = PrintLogHistoryStore(fram, history_length, debug)
            self.storage_pause = fram.set_pause
            self.pr.one("Init with FRAM logging.")
        self.uptime = LockedCounter(max_val=0xFFFFFFFF)  # seconds of about 136 years(!!) perfectly fits into 32bit unsigned
        self.uptime_event = asyncio.ThreadSafeFlag()
        self.timers_running = asyncio.ThreadSafeFlag()
        self.uptime_timer = Timer()
        self.reset_timer = Timer()
        self.storage_timer = Timer()
        self.ntp_is_synced = asy_ntp_callback
        self.start_time_set = False
        self.boot_signature = LockedValue(1)
        self.watchdog = watchdog
        # Set only if a reboot's own reset_timer.init() couldn't be armed (alarm-pool exhaustion) -
        # start_and_check_tasks() then stops feeding the watchdog so it resets us anyway, the same
        # backstop it already relies on past _TASK_FAIL_MAX. One-way: never cleared once set, since
        # the whole point is forcing a reset within the watchdog's own timeout.
        self._force_watchdog_starve = False

    def start_asy_uptime_counter(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.status_counter())

    def start_uptime_timer(self) -> None:
        self.uptime_timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda b: self.uptime_event.set())

    def stop_uptime_timer(self) -> None:
        self.uptime_timer.deinit()

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_uptime_counter]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return [self.start_uptime_timer]

    def _reboot(self, message: str, action: "Callable[[], None]") -> None:
        self.reset_timer.deinit()
        self.storage_timer.deinit()
        self.pr.evt(message)
        if self.storage_pause is not None:
            self.storage_pause(True)
            self.pr.evt("Storage paused")
        try:
            self.reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda b: action())
        except OSError as e:  # alarm-pool exhaustion (confirmed: ports/rp2/machine_timer.c's ENOMEM
            # path) - can't arm the delayed reset, so fall back to the same backstop
            # start_and_check_tasks() already relies on past _TASK_FAIL_MAX: stop feeding the
            # watchdog and let it reset us within its own timeout instead.
            self.pr.err("Could not arm reset timer, stopping watchdog feed instead:", e)
            self._force_watchdog_starve = True

    def reboot_system(self) -> None:
        self._reboot("Reboot triggered", system_reset)

    def reboot_bootloader(self) -> None:
        self._reboot("Reboot into bootloader triggered", system_bootloader)

    def pause_permanent_storage(self, duration: int) -> None:
        if self.storage_pause is not None:
            duration = min(max(duration, 0), _MAX_STORAGE_PAUSE)
            self.storage_timer.deinit()
            if duration == 0:
                self.pr.evt("Storage immediately unpaused.")
                self.storage_pause(False)
            else:
                self.pr.evt("Storage paused for", duration, "seconds.")
                self.storage_pause(True)
                storage_pause = self.storage_pause  # local capture: mypy can't narrow a closed-over self attribute
                try:
                    self.storage_timer.init(
                        period=duration * 1000,
                        mode=Timer.ONE_SHOT,
                        callback=lambda b: storage_pause(False),
                    )
                except OSError as e:  # alarm-pool exhaustion (confirmed: ports/rp2/machine_timer.c's
                    # ENOMEM path) - without the auto-unpause timer armed, storage would stay paused
                    # forever; safer to abort the pause than risk that.
                    self.pr.err("Could not arm auto-unpause timer, aborting pause:", e)
                    storage_pause(False)

    async def get_uptime(self) -> int:
        value = await self.uptime.get_value()  # never None: only ever set_value(0)/increment(), never a None sentinel
        return 0 if value is None else value

    async def get_boot_signature(self) -> int:
        # unique number: UTC timestamp if NTP synced, random number otherwise after _NTP_WAIT_TIME
        res = await self.boot_signature.get_value()
        return int(res)

    async def _ntp_boot_signature(self) -> int | None:
        # None: not synced yet, or the sync callback/timestamp computation itself failed - caller
        # falls back to a random signature after _NTP_WAIT_TIME either way.
        try:
            synced = await self.ntp_is_synced()
        except Exception as e:  # caller-supplied callback (async_connect.py, not itself promoted/audited) - could legitimately misbehave
            await self.pr.err_s("NTP sync callback failed:", e, errno=1)
            return None
        if not synced:
            return None
        try:
            return time.mktime(time.gmtime())
        except (OverflowError, OSError) as e:  # rp2's mktime() raises OverflowError past its ~2037 32-bit epoch range
            await self.pr.err_s("Computing boot signature timestamp failed:", e, errno=2)
            return None

    async def status_counter(self) -> None:
        await self.uptime.set_value(0)
        await self.boot_signature.set_value(-1)
        while True:
            await self.uptime_event.wait()
            uptime = await self.uptime.increment()
            self.pr.all("System uptime incremented to", uptime)
            if self.start_time_set:
                continue
            utc = await self._ntp_boot_signature()
            if utc is not None:
                await self.boot_signature.set_value(utc)
                self.pr.one("System boot signature set by NTP.")
                self.start_time_set = True
            elif uptime >= _NTP_WAIT_TIME:
                await self.boot_signature.set_value(random.getrandbits(32))
                self.pr.one("System boot signature set by random number.")
                self.start_time_set = True

    def _timer_sequencer(self, timers: "list[Callable[[], None]]", counter: int = 0) -> None:
        try:
            timers[counter]()
        except Exception as e:
            # driver-supplied starter (get_timer_starters()) - could legitimately misbehave; this
            # runs in a sync Timer-callback context (no event loop here), so only the non-persisting
            # pr.err() is usable, not the async err_s().
            self.pr.err("Timer starter", counter, "failed:", e)
        else:
            self.pr.evt("Timer started:", counter)
        counter += 1
        if counter < len(timers):
            delay = int(_TIMER_BASE_PERIOD / (len(timers) + 1))
            try:
                # one delay after each start, also (virtually) for last one
                Timer(
                    period=delay,
                    mode=Timer.ONE_SHOT,
                    callback=lambda b: self._timer_sequencer(timers, counter=counter),
                )
                return
            except OSError as e:  # alarm-pool exhaustion (confirmed: ports/rp2/machine_timer.c's
                # ENOMEM path) - stop sequencing further timers rather than leaving start_timers()
                # waiting on timers_running forever.
                self.pr.err("Could not schedule the next timer starter, stopping early:", e)
        self.pr.one("All timers running.")
        self.timers_running.set()

    async def start_timers(self, timers: "list[Callable[[], None]]") -> None:
        self._timer_sequencer(timers, counter=0)
        await self.timers_running.wait()

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        return await self.pr.get_log("Tasks")

    async def reset_error_counter(self) -> None:
        await self.pr.reset()

    async def _start_task(self, starter: "Callable[[], asyncio.Task[Any]]", n: int) -> "asyncio.Task[Any] | None":
        try:
            return starter()
        except Exception as e:  # driver-supplied starter (get_task_starters()) - could legitimately misbehave
            await self.pr.err_s("Task starter", n, "failed to start:", e, errno=3)
            return None

    async def start_and_check_tasks(self, task_starters: "list[Callable[[], asyncio.Task[Any]]]") -> None:
        await self.pr.setup()  # required for all logged warnings and errors
        tasks: list[asyncio.Task[Any] | None] = [None] * len(task_starters)
        for n, starter in enumerate(task_starters):
            tasks[n] = await self._start_task(starter, n)
            await asyncio.sleep(1.0 / len(task_starters))
        task_errors = 0

        while True:
            no_fail = True
            for n in range(0, len(tasks)):
                if tasks[n] is None or tasks[n].done():  # type: ignore[union-attr]
                    task_errors += _TASK_FAIL_INCREMENT
                    tasks[n] = await self._start_task(task_starters[n], n)
                    no_fail = False
                    await self.pr.wrn_s(
                        "Task wurde beendet - versuche Neustart, Fehlerzähler erhöht auf", task_errors, wrnno=n + 1
                    )

            if no_fail:
                self.pr.all("Alle Tasks laufen.")
                if task_errors > 0:
                    task_errors -= 1
                    self.pr.evt("Task Fehlerzähler reduziert auf", task_errors)

            if task_errors <= _TASK_FAIL_MAX:
                if self.watchdog is not None and not self._force_watchdog_starve:
                    self.watchdog.feed()
            else:
                await self.pr.err_s("Task Fehlerzähler über", _TASK_FAIL_MAX, "- Reboot ausgelöst!", errno=4)
                self.reboot_system()
                return

            await asyncio.sleep(_TASK_CHECK_TIME)
