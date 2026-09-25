"""Generic system-housekeeping service shared by every sensortask-*.py device: uptime, boot signature, reboot/reboot-to-bootloader, the staggered driver-startup sequence, the task supervisor loop, and a persisted system-settings store (config_SYSTEM.cfg).
Every method returns a well-defined value, never raises.
"""
# A live debug-level change is pushed through a registry of other loggers' own set_level() methods
# (set_level_setters(), filled once at boot), never a shared mutable value. The real reset
# reboot_system()/reboot_bootloader() take after _RESET_DELAY is the intent, not a failure.

import asyncio
import gc
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
    from typing import Any, Protocol

    from asy_fram_manager import AsyFramManager
    from config_manager import ConfigSchema, WriteValidity
    from print_log import ErrorLog, PrintLogHistory

    # Keyword-only call shape of AsyFramManager.set_pause(), which a plain Callable[...] alias
    # cannot express - same structural-Protocol convention as print_log.py's _FramChunk.
    class _StoragePause(Protocol):
        def __call__(self, *, value: bool) -> None: ...

_RESET_DELAY = const(4)  # seconds between reset command and execution (keep < watchdog timeout!)
_MAX_STORAGE_PAUSE = const(3600)  # one hour max pause for FRAM
_NTP_WAIT_TIME = const(120)  # 2 mins until random boot signature is used
_TIMER_BASE_PERIOD = const(1000)  # milliseconds for sensor triggers base period
_TASK_CHECK_TIME = const(2)  # seconds period to check running tasks (keep << watchdog timeout!)
_TASK_FAIL_INCREMENT = const(100)  # absolute value important for decrease time,...
_TASK_FAIL_MAX = const(300)  # ...ratio important for triggering reset (multiple errors)
_NAME = const("SYSTEM")

# This service's one optional live cross-instance dependency (SPECIFICATION.md Part C.14): its FRAM
# error-log target, resolved from [device.wiring].fram_target implicitly because this is mandatory
# infra, never an [[instance]] entry (Part L.4).
# @wiring fram_target AsyFramManager fram optional kwarg

# General, module-independent system-settings schema (config_SYSTEM.cfg, via _NAME above) - Part C.5
# has the setSGP/setBMP history this superseded. Adding a field is the same one-line _VAL_*-tuple
# concatenation every other ConfigManager-backed module uses.
# @web-group section=system submitGroup=settings label="System Settings" submit=true
# @web DebugLevel section=system submitGroup=settings label="Debug Level"
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
        self.storage_pause: _StoragePause | None = None
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
        # Preallocated like the three timers above: _timer_sequencer() re-.init()s this one rather
        # than constructing a fresh, unreferenced Timer() each step, because an unstored Timer is
        # GC-eligible before its ONE_SHOT callback fires (Part F.1's soft-callback-drop gotcha).
        self.sequencer_timer = Timer()
        self.ntp_is_synced = asy_ntp_callback
        self.start_time_set = False
        # None until status_counter() resolves it - a later change to this value signals a reboot happened.
        self.boot_signature = LockedCounter(init_value=None, max_val=0xFFFFFFFF)
        self.watchdog = watchdog
        # Set when _reboot()'s reset_timer can't be armed, so the supervisor loop stops feeding the
        # watchdog and lets it reset us instead (one-way).
        self._force_watchdog_starve = False
        # System-settings store, deliberately not a SensorReaderConfig subclass - no measurement
        # data and no error-streak concept, both of which that base would drag in unused - just a
        # directly-embedded ConfigManager. cfg_schema stays public (Part C.5's convention).
        self.cfg_schema: ConfigSchema = _VAL_DEBUG_LEVEL
        self.cfgmgr = ConfigManager(cfg_path + "config_" + _NAME + ".cfg", self.cfg_schema, _NAME, fram=fram)
        # get_debug_level()'s own source of truth - starts at the schema default; setup()/
        # set_debug_level() keep it current from there.
        self._current_debug_level = 0
        # Registry of every other logger's own set_level(), filled once at boot the way
        # get_task_starters()/get_timer_starters() are, and called whenever the level changes. Empty
        # until set, degrading gracefully then - like watchdog and fram, the other optionals here.
        self._level_setters: list[Callable[[int], None]] = []

    def feed_watchdog(self) -> None:
        # The one reusable, no-op-safe watchdog access point (SPECIFICATION.md Part G.2): every feed
        # site calls this instead of repeating the "watchdog=None, or the reset timer failed to arm"
        # check. A device with no watchdog and one deliberately left to die take the same path.
        if self.watchdog is not None and not self._force_watchdog_starve:
            self.watchdog.feed()

    def _reboot(self, message: str, action: "Callable[[], None]") -> None:
        self.reset_timer.deinit()
        self.storage_timer.deinit()
        self.pr.evt(message)
        if self.storage_pause is not None:
            self.storage_pause(value=True)
            self.pr.evt("Storage paused")
        try:
            self.reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda _b: action())
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
                # Reuses the preallocated self.sequencer_timer rather than a bare Timer() here - an
                # unreferenced Timer is GC-eligible before its ONE_SHOT callback fires, silently
                # hanging every caller of start_timers() forever (SPECIFICATION.md Part F.1).
                self.sequencer_timer.init(
                    period=delay,
                    mode=Timer.ONE_SHOT,
                    callback=lambda _b: self._timer_sequencer(timers, counter=counter),
                )
            except (OSError, MemoryError) as e:  # alarm-pool exhaustion (ENOMEM) - stop sequencing rather than
                # leaving start_timers() waiting on timers_running forever.
                self.pr.err("Could not schedule the next timer starter, stopping early:", e)
            else:
                return
        self.pr.one("All timers running.")
        self.timers_running.set()

    async def _start_task(self, starter: "Callable[[], asyncio.Task[Any]]", n: int) -> "asyncio.Task[Any] | None":
        try:
            return starter()
        except Exception as e:  # driver-supplied starter (get_task_starters()) - could legitimately misbehave
            await self.pr.err_s("Task starter", n, "failed to start:", e, errno=3)
            return None

    async def _log_dead_task(self, task: "asyncio.Task[Any]", n: int) -> None:
        # A finished Task carries no .exception()/.result() in MicroPython's asyncio - awaiting it
        # again is the only way to recover why it ended (a real exception re-raises here, a clean
        # return does not), giving the restart warning below real diagnostic content.
        try:
            await task
        except asyncio.CancelledError:
            # Previously logged via the non-persisting self.pr.err() - left zero trace in errcount,
            # indistinguishable from a clean return. Persists now via its own errno=6, distinct from
            # errno=5's real-exception case (see SPECIFICATION.md's errno/wrnno table).
            await self.pr.err_s("Task", n, "ended: was cancelled", errno=6)
        except Exception as e:
            await self.pr.err_s("Task", n, "ended with exception:", e, errno=5)

    def start_asy_uptime_counter(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.status_counter())

    def start_uptime_timer(self) -> None:
        try:
            self.uptime_timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda _b: self.uptime_event.set())
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
        # Measure B (SPECIFICATION.md Part I.4(f.1)): the second of the two one-time boot lists that
        # get a placement reset between their units - each collect puts the allocator's free-scan
        # index back to zero. Not hygiene, not compaction, and never in the supervisor below.
        gc.collect()
        for n, starter in enumerate(task_starters):
            tasks[n] = await self._start_task(starter, n)
            await asyncio.sleep(1.0 / len(task_starters))
            gc.collect()
        task_errors = 0

        while True:
            no_fail = True
            for n in range(len(tasks)):
                if tasks[n] is None or tasks[n].done():  # type: ignore[union-attr]
                    if tasks[n] is not None:
                        await self._log_dead_task(tasks[n], n)  # type: ignore[arg-type]
                    task_errors += _TASK_FAIL_INCREMENT
                    tasks[n] = await self._start_task(task_starters[n], n)
                    no_fail = False
                    await self.pr.wrn_s(
                        "Task ended - attempting restart, error counter increased to", task_errors, wrnno=n + 1,
                    )

            if no_fail:
                self.pr.all("All tasks running.")
                if task_errors > 0:
                    task_errors -= 1
                    self.pr.evt("Task error counter reduced to", task_errors)

            if task_errors <= _TASK_FAIL_MAX:
                self.feed_watchdog()
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

    def get_error_sources(self) -> "list[Any]":
        # Fan-in primitive (SPECIFICATION.md Part C.14/G.2) - matches base_classes.py's
        # SensorReaderConfig.get_error_sources() shape (this class owns a cfgmgr too), duck-typed
        # rather than inherited (see this module's own "not a SensorReaderConfig subclass" comment).
        return [self, self.cfgmgr]

    def get_loggers(self) -> "list[PrintLogHistory]":
        return [self.pr, self.cfgmgr.pr]

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def setup(self) -> None:
        # Resolves the persisted system-settings store (Part C.13's sync-__init__/async-setup()
        # pattern). Always updates _current_debug_level, then pushes it through every registered
        # level setter so each logger reflects the persisted level rather than whatever it started at.
        await self.cfgmgr.setup()
        level = await self.cfgmgr.get_int_values(self.cfg_schema)
        if level is None:
            return
        self._current_debug_level = level[0]
        await self._apply_level(level[0])

    def get_cfg_schema(self) -> "ConfigSchema":
        return self.cfg_schema

    async def get_dict_cfg(self) -> "dict[str, int | float | str | bool | None]":
        # SettingsGroup-shaped counterpart to get_cfg_schema() - lets
        # asy_webserver_service.py's /system route treat this module uniformly with every other
        # SettingsGroup-registered module, without special-casing DebugLevel in the webserver layer.
        result = await self.cfgmgr.get_dict(schema_names(self.cfg_schema))
        return {} if result is None else result

    async def _set_dict_cfg(
        self, data: "dict[str, int | float | str | bool | None]", cfg_vals: "ConfigSchema",
    ) -> "WriteValidity":
        # Persist through cfgmgr, then re-resolve and push DebugLevel out over the level-setter
        # registry. It pushes on "Unchanged" too, not only on a real change, so every logger's live
        # level stays provably in sync with the persisted value after any accepted request.
        persisted, results = await self.cfgmgr.write_config(data, cfg_vals)
        if not persisted:
            return dict.fromkeys(data, "Failed")
        if results.get("DebugLevel") in ("Valid", "Unchanged"):
            level = await self.cfgmgr.get_int_values(_VAL_DEBUG_LEVEL)
            if level is not None:
                self._current_debug_level = level[0]
                await self._apply_level(level[0])
        return results

    def set_level_setters(self, setters: "list[Callable[[int], None]]") -> None:
        # Called once at boot, the same style as start_timers()/start_and_check_tasks() receiving
        # their own collected lists - but stored rather than consumed, since a setter is called
        # again on every future level change.
        self._level_setters = list(setters)

    async def _apply_level(self, value: int) -> None:
        # Each call guarded individually, the same caller-supplied-callback defense
        # _timer_sequencer() uses per starter, so one bad entry cannot stop the rest. async because
        # both call sites already are, and so the failure persists via err_s() like every other one.
        for setter in self._level_setters:
            try:
                setter(value)
            except Exception as e:
                await self.pr.err_s("Level setter failed:", e, errno=7)

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
                self.storage_pause(value=False)
            else:
                self.pr.evt("Storage paused for", duration, "seconds.")
                self.storage_pause(value=True)
                storage_pause = self.storage_pause  # local capture: mypy can't narrow a closed-over self attribute
                try:
                    self.storage_timer.init(
                        period=duration * 1000,
                        mode=Timer.ONE_SHOT,
                        callback=lambda _b: storage_pause(value=False),
                    )
                except (OSError, MemoryError) as e:  # alarm-pool exhaustion (ENOMEM) - without the auto-unpause timer,
                    # storage would stay paused forever; safer to abort the pause than risk that.
                    self.pr.err("Could not arm auto-unpause timer, aborting pause:", e)
                    storage_pause(value=False)

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
