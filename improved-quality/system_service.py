import random
import time
import asyncio
from base_classes import PrintLogHistory, PrintLogHistStore, LockedCounter, LockedValue
from asy_fram_manager import AsyFramManager
from uasyncio import ThreadSafeFlag
from machine import WDT, Timer, reset as system_reset, bootloader as system_bootloader
from micropython import const
from typing import Callable, Any, Coroutine, List, Dict

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
        asy_ntp_callback: Callable[[], Coroutine[Any, Any, bool]],
        watchdog: WDT | None = None,
        fram: AsyFramManager | None = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        # callback for starting and stopping permanent storage communication
        self.storage_pause: Callable[[bool], None] | None = None
        if fram is None:
            self.pr = PrintLogHistory(history_length, debug)
            self.pr.one("Init with memory logging.")
        else:
            self.pr = PrintLogHistStore(fram, history_length, debug)
            self.storage_pause = fram.set_pause
            self.pr.one("Init with FRAM logging.")
        self.uptime = LockedCounter(max_val=0xFFFFFFFF)  # seconds of about 136 years(!!) perfectly fits into 32bit unsigned
        self.uptime_event = ThreadSafeFlag()
        self.timers_running = ThreadSafeFlag()
        self.uptime_timer = Timer()
        self.reset_timer = Timer()
        self.storage_timer = Timer()
        self.ntp_is_synced = asy_ntp_callback
        self.start_time_set = False
        self.boot_signature = LockedValue(1)
        self.watchdog = watchdog

    def start_asy_uptime_counter(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.status_counter())

    def start_uptime_timer(self) -> None:
        self.uptime_timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda b: self.uptime_event.set())

    def stop_uptime_timer(self) -> None:
        self.uptime_timer.deinit()

    def get_task_starters(self) -> List[Callable[[], asyncio.Task[Any]]]:
        return [self.start_asy_uptime_counter]

    def get_timer_starters(self) -> List[Callable[[], None]]:
        return [self.start_uptime_timer]

    def reboot_system(self) -> None:
        self.reset_timer.deinit()
        self.storage_timer.deinit()
        self.pr.evt("Reboot triggered")
        if self.storage_pause is not None:
            self.storage_pause(True)
            self.pr.evt("Storage paused")
        self.reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda b: system_reset())

    def reboot_bootloader(self) -> None:
        self.reset_timer.deinit()
        self.storage_timer.deinit()
        self.pr.evt("Reboot into bootloader triggered")
        if self.storage_pause is not None:
            self.storage_pause(True)
            self.pr.evt("Storage paused")
        self.reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda b: system_bootloader())

    def pause_permanent_storage(self, duration: int) -> None:
        if self.storage_pause is not None:
            if duration <= 0:
                duration = 0
            elif duration > _MAX_STORAGE_PAUSE:
                duration = _MAX_STORAGE_PAUSE
            if duration == 0:
                self.storage_timer.deinit()
                self.pr.evt("Storage immediately unpaused.")
                self.storage_pause(False)
            else:
                self.storage_timer.deinit()
                self.pr.evt("Storage paused for", duration, "seconds.")
                self.storage_pause(True)
                self.storage_timer.init(
                    period=duration * 1000,
                    mode=Timer.ONE_SHOT,
                    callback=lambda b: self.storage_pause(False),
                )

    async def get_uptime(self) -> int:
        value = await self.uptime.get_value()  # never None: only ever set_value(0)/increment(), never a None sentinel
        return 0 if value is None else value

    async def get_boot_signature(self) -> int:
        # unique number. UTC timestamp if NTP synced, random number otherwise after wait time# unique number.
        # UTC timestamp if NTP synced, random number otherwise after wait time
        res = await self.boot_signature.get_value()
        return int(res)

    async def status_counter(self) -> None:
        await self.uptime.set_value(0)
        await self.boot_signature.set_value(-1)
        while True:
            await self.uptime_event.wait()
            uptime = await self.uptime.increment()
            self.pr.all("System uptime incremented to", uptime)
            if not self.start_time_set:
                if await self.ntp_is_synced():
                    await self.boot_signature.set_value(time.mktime(time.gmtime()))  # type: ignore[call-arg]
                    self.pr.one("System boot signature set by NTP.")
                    self.start_time_set = True
                else:  # ntp not synced
                    if uptime >= _NTP_WAIT_TIME:
                        await self.boot_signature.set_value(random.getrandbits(32))
                        self.pr.one("System boot signature set by random number.")
                        self.start_time_set = True

    def _timer_sequencer(self, timers: List[Callable[[], None]], counter: int = 0) -> None:
        timers[counter]()
        self.pr.evt("Timer started:", counter)
        counter += 1
        if counter < len(timers):
            delay = int(_TIMER_BASE_PERIOD / (len(timers) + 1))
            # one delay after each start, also (virtually) for last one
            Timer(
                period=delay,
                mode=Timer.ONE_SHOT,
                callback=lambda b: self._timer_sequencer(timers, counter=counter),
            )
        else:
            self.pr.one("All timers running.")
            self.timers_running.set()

    async def start_timers(self, timers: List[Callable[[], None]]) -> None:
        self._timer_sequencer(timers, counter=0)
        await self.timers_running.wait()

    async def get_error_counter(self) -> Dict[str, Dict[str, int | List[int] | List[str]]]:
        return await self.pr.get_log("Tasks")

    async def reset_error_counter(self) -> None:
        await self.pr.reset()

    async def start_and_check_tasks(self, task_starters: List[Callable[[], asyncio.Task[Any]]]) -> None:
        await self.pr.setup()  # required for all logged warnings and errors
        tasks = []
        for starter in task_starters:
            tasks.append(starter())
            await asyncio.sleep(1.0 / len(task_starters))
        task_errors = 0

        while True:
            no_fail = True
            for n in range(0, len(tasks)):
                if tasks[n].done():
                    task_errors += _TASK_FAIL_INCREMENT
                    tasks[n] = task_starters[n]()
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
                if self.watchdog is not None:
                    self.watchdog.feed()
            else:
                await self.pr.err_s("Task Fehlerzähler über", _TASK_FAIL_MAX, "- Reboot ausgelöst!", errno=1)
                self.reboot_system()
                return

            await asyncio.sleep(_TASK_CHECK_TIME)
