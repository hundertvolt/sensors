"""Generic system-housekeeping service shared by every sensortask-*.py device: uptime, a one-per-
boot boot signature, reboot/reboot-to-bootloader with FRAM storage-pause coordination, the
staggered driver-startup sequence, the task supervisor loop (restart dead tasks, decay a failure
counter, feed the watchdog), and a general, module-independent persisted system-settings store
(config_SYSTEM.cfg - DebugLevel today, expected to grow further; see get_debug_level()/
set_debug_level() and this module's own get_cfg_schema()). A live debug-level change is pushed out
through a registry of other loggers' own set_level() methods (set_level_setters(), set up once at
boot - see sensortask_wozi.py's _collect_level_setters()), not a shared mutable value - each
PrintLog instance stays a plain, independent object with no cross-module coupling. Every method
returns a well-defined value, never raises - reboot_system()/reboot_bootloader()'s real reset
after _RESET_DELAY is the intent, not a failure.
"""

import asyncio
import random
import time

from machine import WDT, Timer
from machine import bootloader as system_bootloader
from machine import reset as system_reset
from micropython import const

from base_classes import LockedCounter
from config_manager import ConfigManager, schema_names
from print_log import make_logger

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any

    from asy_fram_manager import AsyFramManager
    from config_manager import ConfigSchema, WriteValidity

_RESET_DELAY = const(4)  # seconds between reset command and execution (keep < watchdog timeout!)
_MAX_STORAGE_PAUSE = const(3600)  # one hour max pause for FRAM
_NTP_WAIT_TIME = const(120)  # 2 mins until random boot signature is used
_TIMER_BASE_PERIOD = const(1000)  # milliseconds for sensor triggers base period
_TASK_CHECK_TIME = const(2)  # seconds period to check running tasks (keep << watchdog timeout!)
_TASK_FAIL_INCREMENT = const(100)  # absolute value important for decrease time,...
_TASK_FAIL_MAX = const(300)  # ...ratio important for triggering reset (multiple errors)
_NAME = const("SYSTEM")

# General, module-independent system-settings schema (config_SYSTEM.cfg, via _NAME above) - the
# real, connected successor to the old improved-quality/sensortask-wozi.py "config_SYSTEM.cfg"
# schema that migration removed as a disconnected, never-read duplicate (see that file's own
# api_helpers.py-migration comment). DebugLevel is the first field; owner-confirmed intent is to
# grow this with more device-wide settings over time (e.g. timing/timezone info currently on
# AsyNtpClient, future rsyslog settings) - adding a field here is exactly the same one-line
# _VAL_*-tuple-concatenation pattern every other ConfigManager-backed module already uses (see
# SPECIFICATION.md Part C), not a mechanism that needs revisiting per new field.
_VAL_DEBUG_LEVEL = const((("DebugLevel", "int", 0, 0, 5, None),))  # range matches print_log.py's
# PrintLog.level_off()..level_info() (0-5); default 0 matches the reference file's own debug=False.


class SystemService:
    def __init__(
        self,
        asy_ntp_callback: "Callable[[], Coroutine[Any, Any, bool]]",
        watchdog: WDT | None = None,
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
        cfg_path: str = "",
    ) -> None:
        # callback for starting and stopping permanent storage communication
        self.storage_pause: Callable[[bool], None] | None = None
        self.pr = make_logger(fram, history_length, debug, _NAME)
        self.name = _NAME  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (error_sources=/settings=).
        if fram is not None:
            self.storage_pause = fram.set_pause
        self.uptime = LockedCounter(max_val=0xFFFFFFFF)  # seconds of about 136 years(!!) perfectly fits into 32bit unsigned
        self.uptime_event = asyncio.ThreadSafeFlag()
        self.timers_running = asyncio.ThreadSafeFlag()
        self.uptime_timer = Timer()
        self.reset_timer = Timer()
        self.storage_timer = Timer()
        self.ntp_is_synced = asy_ntp_callback
        self.start_time_set = False
        # None until status_counter() resolves it - a later change to this value signals a reboot happened.
        self.boot_signature = LockedCounter(init_value=None, max_val=0xFFFFFFFF)
        self.watchdog = watchdog
        # Set when _reboot()'s reset_timer can't be armed, so the supervisor loop stops feeding the
        # watchdog and lets it reset us instead (one-way).
        self._force_watchdog_starve = False
        # System-settings store - not a SensorReaderConfig subclass (no measurement data, no
        # max_module_error error-streak concept, both of which SensorReaderConfig would drag in
        # unused), just its own directly-embedded ConfigManager, same underlying class and file
        # convention every other module already uses. self.cfg_schema stays public, matching
        # SPECIFICATION.md's convention for a module whose caller writes to cfgmgr directly.
        self.cfg_schema: ConfigSchema = _VAL_DEBUG_LEVEL
        self.cfgmgr = ConfigManager(cfg_path + "config_" + _NAME + ".cfg", self.cfg_schema, _NAME)
        # get_debug_level()'s own source of truth - starts at the schema default; setup()/
        # set_debug_level() keep it current from there.
        self._current_debug_level = 0
        # Registry of every other logger's own set_level() bound method (print_log.py's
        # PrintLog.set_level - already exists, nothing new added there), set up once at boot via
        # set_level_setters() below, the same style as get_task_starters()/get_timer_starters():
        # a caller (sensortask_wozi.py's build_system()) collects the list, hands it in once, and
        # this class calls every entry whenever the level changes (setup(), set_debug_level()).
        # Empty until set - degrades gracefully (persistence/get_debug_level() still work, just no
        # other logger is pushed a live update), matching every other optional dependency on this
        # class (watchdog, fram).
        self._level_setters: list[Callable[[int], None]] = []

    def _reboot(self, message: str, action: "Callable[[], None]") -> None:
        self.reset_timer.deinit()
        self.storage_timer.deinit()
        self.pr.evt(message)
        if self.storage_pause is not None:
            self.storage_pause(True)
            self.pr.evt("Storage paused")
        try:
            self.reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda b: action())
        except (OSError, MemoryError) as e:  # alarm-pool exhaustion (ENOMEM) - falls back to the same watchdog-starve
            # backstop start_and_check_tasks() already uses past _TASK_FAIL_MAX.
            self.pr.err("Could not arm reset timer, stopping watchdog feed instead:", e)
            self._force_watchdog_starve = True

    async def _ntp_boot_signature(self) -> int | None:
        # None if not synced yet or the sync/mktime computation itself failed; caller falls back to random after _NTP_WAIT_TIME.
        try:
            synced = await self.ntp_is_synced()
        except Exception as e:  # caller-supplied callback, typed as any Callable - guarded broadly
            # since it isn't guaranteed to be a specific, known-safe implementation
            await self.pr.err_s("NTP sync callback failed:", e, errno=1)
            return None
        if not synced:
            return None
        try:
            return time.mktime(time.gmtime())
        except (OverflowError, OSError) as e:  # rp2's mktime() raises OverflowError past its ~2037 32-bit epoch range
            await self.pr.err_s("Computing boot signature timestamp failed:", e, errno=2)
            return None

    def _timer_sequencer(self, timers: "list[Callable[[], None]]", counter: int = 0) -> None:
        try:
            timers[counter]()
        except Exception as e:
            # driver-supplied starter - could misbehave; sync Timer-callback context (no event loop),
            # so only pr.err() is usable, not the async err_s().
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
            except (OSError, MemoryError) as e:  # alarm-pool exhaustion (ENOMEM) - stop sequencing rather than
                # leaving start_timers() waiting on timers_running forever.
                self.pr.err("Could not schedule the next timer starter, stopping early:", e)
        self.pr.one("All timers running.")
        self.timers_running.set()

    async def _start_task(self, starter: "Callable[[], asyncio.Task[Any]]", n: int) -> "asyncio.Task[Any] | None":
        try:
            return starter()
        except Exception as e:  # driver-supplied starter (get_task_starters()) - could legitimately misbehave
            await self.pr.err_s("Task starter", n, "failed to start:", e, errno=3)
            return None

    def start_asy_uptime_counter(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.status_counter())

    def start_uptime_timer(self) -> None:
        try:
            self.uptime_timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda b: self.uptime_event.set())
        except (OSError, MemoryError) as e:  # alarm-pool exhaustion (ENOMEM) - degrades gracefully rather than rebooting;
            # only uptime/boot-signature stay unresolved this boot.
            self.pr.err("Could not arm uptime timer:", e)

    async def start_timers(self, timers: "list[Callable[[], None]]") -> None:
        if not timers:  # nothing to sequence - avoid _timer_sequencer's timers[0] on an empty list
            self.timers_running.set()
            return
        self._timer_sequencer(timers, counter=0)
        await self.timers_running.wait()

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
                        "Task ended - attempting restart, error counter increased to", task_errors, wrnno=n + 1
                    )

            if no_fail:
                self.pr.all("All tasks running.")
                if task_errors > 0:
                    task_errors -= 1
                    self.pr.evt("Task error counter reduced to", task_errors)

            if task_errors <= _TASK_FAIL_MAX:
                if self.watchdog is not None and not self._force_watchdog_starve:
                    self.watchdog.feed()
            else:
                await self.pr.err_s("Task error counter above", _TASK_FAIL_MAX, "- reboot triggered!", errno=4)
                self.reboot_system()
                return

            await asyncio.sleep(_TASK_CHECK_TIME)

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_uptime_counter]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return [self.start_uptime_timer]

    def stop_uptime_timer(self) -> None:
        self.uptime_timer.deinit()

    async def get_uptime(self) -> int:
        value = await self.uptime.get_value()  # never None: only ever set_value(0)/increment(), never a None sentinel
        return 0 if value is None else value

    async def get_boot_signature(self) -> int | None:
        # None until resolved; then a UTC timestamp if NTP synced, else random after _NTP_WAIT_TIME -
        # stable for the rest of this boot, so a later change means a reboot happened.
        return await self.boot_signature.get_value()

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        return await self.pr.get_log()

    async def setup(self) -> None:
        # Resolves the persisted system-settings store (SPECIFICATION.md C.13's sync-__init__/
        # async-setup() pattern). Always updates _current_debug_level (get_debug_level()'s own
        # source of truth); additionally pushes the same value out through every registered level
        # setter, so every other logger reflects the real, persisted level from here on, not
        # whatever it started at.
        await self.cfgmgr.setup()
        level = await self.cfgmgr.get_int_values(self.cfg_schema)
        if level is None:
            return
        self._current_debug_level = level[0]
        self._apply_level(level[0])

    def get_cfg_schema(self) -> "ConfigSchema":
        return self.cfg_schema

    async def get_dict_cfg(self) -> "dict[str, int | float | str | bool | None]":
        # SettingsGroup-shaped counterpart to get_cfg_schema() - lets
        # asy_webserver_service.py's /system route treat this module uniformly with every other
        # SettingsGroup-registered module, without special-casing DebugLevel in the webserver layer.
        result = await self.cfgmgr.get_dict(schema_names(self.cfg_schema))
        return {} if result is None else result

    async def _set_dict_cfg(
        self, data: "dict[str, int | float | str | bool | None]", cfg_vals: "ConfigSchema"
    ) -> "WriteValidity":
        # Persist via cfgmgr, then re-resolve/push DebugLevel out through the level-setter registry -
        # set_debug_level() below is now just this call for its own one-field case, kept as a named,
        # direct API for callers that don't want the generic dict-shaped one. Matches the original
        # set_debug_level()'s own behavior exactly: pushes on "Unchanged" too (a request for the
        # already-persisted value), not just on a real change, so every logger's live level stays
        # provably in sync with cfgmgr's own persisted value after any accepted request.
        persisted, results = await self.cfgmgr.write_config(data, cfg_vals)
        if not persisted:
            return {key: "Failed" for key in data}
        if results.get("DebugLevel") in ("Valid", "Unchanged"):
            level = await self.cfgmgr.get_int_values(_VAL_DEBUG_LEVEL)
            if level is not None:
                self._current_debug_level = level[0]
                self._apply_level(level[0])
        return results

    def set_level_setters(self, setters: "list[Callable[[int], None]]") -> None:
        # Called once at boot (sensortask_wozi.py's build_system(), the same style as
        # start_timers(timer_starters)/start_and_check_tasks(task_starters) receiving their own
        # collected lists) - stored rather than consumed immediately, since a setter needs calling
        # again on every future level change, not just once.
        self._level_setters = list(setters)

    def _apply_level(self, value: int) -> None:
        # Iterates the registry, pushing value to every other logger's own set_level() (already
        # existing on every PrintLog - see print_log.py). Each call is individually guarded:
        # set_level() itself is documented to never raise, but a registry entry is a plain
        # Callable[[int], None] from this class's own point of view, not guaranteed to be exactly
        # that implementation - matching this codebase's established "driver/caller-supplied
        # callback could misbehave" defense (e.g. _timer_sequencer()'s own per-starter try/except),
        # so one bad entry can't stop the rest of the registry from being updated.
        for setter in self._level_setters:
            try:
                setter(value)
            except Exception as e:
                self.pr.err("Level setter failed:", e)

    def get_debug_level(self) -> int:
        return self._current_debug_level

    async def set_debug_level(self, value: int) -> bool:
        results = await self._set_dict_cfg({"DebugLevel": value}, self.cfg_schema)
        return results.get("DebugLevel") in ("Valid", "Unchanged")

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
                except (OSError, MemoryError) as e:  # alarm-pool exhaustion (ENOMEM) - without the auto-unpause timer,
                    # storage would stay paused forever; safer to abort the pause than risk that.
                    self.pr.err("Could not arm auto-unpause timer, aborting pause:", e)
                    storage_pause(False)

    async def status_counter(self) -> None:
        await self.uptime.set_value(0)
        await self.boot_signature.set_value(None)
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
                # get_rand_32()-seeded (pico-sdk pico_rand, real ring-oscillator entropy) - unique
                # per boot, not a fixed/repeatable seed.
                await self.boot_signature.set_value(random.getrandbits(32))
                self.pr.one("System boot signature set by random number.")
                self.start_time_set = True

    async def reset_error_counter(self) -> None:
        await self.pr.reset()
