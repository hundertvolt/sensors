"""Generic system-housekeeping service shared by every sensortask-*.py device: uptime, boot signature, reboot/reboot-to-bootloader, the staggered driver-startup sequence, the task supervisor loop, and a persisted system-settings store (config_SYSTEM.cfg).
Every method returns a well-defined value, never raises.
"""
# A live debug-level change is pushed through the other loggers' own set_level() methods (the level_setters provider,
# resolved once in setup()), not a shared mutable value (owner, 2026-08-11, paraphrase: SharedLevel was reverted for breaking encapsulation).
# The real reset reboot_system()/reboot_bootloader() take after _RESET_DELAY is the intent, not a failure.

import asyncio
import gc
import random
import time

from machine import WDT, Timer
from machine import bootloader as system_bootloader
from machine import reset as system_reset
from micropython import const

from asy_base_classes import LockedCounter, LockedValue, arm_tick_timer, utc_now
from asy_config_manager import ConfigManager, name_cfg, schema_names
from asy_print_log import DEFAULT_LOG, LogConfig, make_logger

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Any, Protocol

    from asy_base_classes import ErrorSource, TaskStarter, TimerStarter
    from asy_config_manager import CfgValue, ConfigSchema, WriteValidity
    from asy_fram_manager import FRAMManager
    from asy_print_log import ErrorLog, PrintLogHistory

    # Keyword-only call shape of FRAMManager.set_pause(), which a plain Callable[...] alias
    # cannot express - same structural-Protocol convention as asy_print_log.py's _FramChunk.
    class _StoragePause(Protocol):
        def __call__(self, *, value: bool) -> None: ...

# Codes from the global catalog (buildgen/error_catalog.json): the shared ones and SYSTEM's band.
_ERR_CALLBACK = const(14)
_ERR_TIMER = const(17)
_ERR_TASK_STARTER_RAISED = const(40)
_ERR_TASK_BUDGET_REBOOT = const(41)
_ERR_TASK_RAISED = const(42)
_ERR_TASK_CANCELLED = const(43)
_ERR_TASK_RETURNED = const(44)

# @tunable system.reset_delay_s = 4
_RESET_DELAY = const(4)  # seconds between reset command and execution (keep < watchdog timeout!)
_MAX_STORAGE_PAUSE = const(3600)  # one hour max pause for FRAM
# @tunable system.ntp_wait_s = 120
_NTP_WAIT_TIME = const(120)  # 2 mins until random boot signature is used
# @tunable system.timer_base_period_ms = 1000
_TIMER_BASE_PERIOD = const(1000)  # milliseconds for sensor triggers base period
# @tunable system.task_check_s = 2
_TASK_CHECK_TIME = const(2)  # seconds period to check running tasks (keep << watchdog timeout!)
# @tunable system.task_fail_increment = 100
_TASK_FAIL_INCREMENT = const(100)  # absolute value important for decrease time,...
# @tunable system.task_fail_max = 300
_TASK_FAIL_MAX = const(300)  # ...ratio important for triggering reset (multiple errors)
_NAME = const("SYSTEM")

# This service's one optional live cross-instance dependency (SPECIFICATION.md Part C.14): its FRAM
# error-log target, resolved from [device.wiring].fram_target implicitly because this is mandatory
# infra, never an [[instance]] entry (Part L.4).
# @wiring fram_target FRAMManager log optional kwarg

# General, module-independent system-settings schema (config_SYSTEM.cfg, via _NAME above) - Part C.5
# has the setSGP/setBMP history this superseded. Adding a field is the same one-line _VAL_*-tuple
# concatenation every other ConfigManager-backed module uses.
# @web-group section=system submitGroup=settings label="System Settings" submit=true
# @web DebugLevel section=system submitGroup=settings label="Debug Level"
_VAL_DEBUG_LEVEL = const((("DebugLevel", "int", 0, 0, 5, None),))  # range matches asy_print_log.py's
# PrintLog.level_off()..level_info() (0-5); default 0 matches the reference file's own debug=False.


class SystemService:
    def __init__(
        self,
        asy_ntp_callback: "Callable[[], Awaitable[bool]]",
        watchdog: WDT | None = None,
        storage: "FRAMManager | None" = None,
        level_setters: "Callable[[], list[Callable[[int], None]]] | None" = None,
        cfg_path: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        self.pr = make_logger(log, _NAME)
        self.name = _NAME  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (error_sources=/settings=).
        # callback for starting and stopping permanent storage communication
        self._storage_pause: _StoragePause | None = storage.set_pause if storage is not None else None
        self.uptime = LockedCounter()  # seconds, saturating at COUNTER_CAP (34 years)
        self._uptime_event = asyncio.ThreadSafeFlag()
        self._uptime_timer = Timer()
        self._reset_timer = Timer()
        self._storage_timer = Timer()
        # Preallocated like the other timers: start_timers() re-.init()s it for each stagger wait rather than constructing a
        # fresh Timer() each time, which the GC would disarm before it fires (SPECIFICATION.md Part F.1).
        self._sequencer_timer = Timer()
        self._sequencer_flag = asyncio.ThreadSafeFlag()  # one waiter: start_timers() runs once per boot
        self.ntp_is_synced = asy_ntp_callback
        self._start_time_set = False
        # None until _status_loop() resolves it (owner, 2026-07-18) - a later change to this value signals a reboot happened.
        self.boot_signature = LockedValue(init_value=None)
        self.watchdog = watchdog
        # Set when _reboot()'s _reset_timer can't be armed, so the supervisor loop stops feeding the
        # watchdog and lets it reset us instead (one-way).
        self._force_watchdog_starve = False
        # System-settings store, deliberately not a SensorReaderConfig subclass - no measurement
        # data and no error-streak concept, both of which that base would drag in unused - just a
        # directly-embedded ConfigManager.
        self._cfg_schema: ConfigSchema = _VAL_DEBUG_LEVEL
        self.cfgmgr = ConfigManager(cfg_path + "config_" + _NAME + ".cfg", self._cfg_schema, _NAME, log=log)
        # get_debug_level()'s own source of truth - starts at the schema default; setup()/
        # set_debug_level() keep it current from there.
        self._current_debug_level = 0
        # Every logger's own set_level(), resolved once from the provider in setup() and called on every level change.
        self._level_setters_provider = level_setters
        self._level_setters: list[Callable[[int], None]] = []

    async def _set_dict_cfg(
        self, data: dict[str, int | float | str | bool | None], cfg_vals: "ConfigSchema",
    ) -> "WriteValidity":
        # Persist through cfgmgr, then re-resolve and push DebugLevel out over the level-setter
        # registry. It pushes on "Unchanged" too, not only on a real change, so every logger's live
        # level stays provably in sync with the persisted value after any accepted request.
        persisted, results = await self.cfgmgr.write_config(data, cfg_vals)
        if not persisted:
            return dict.fromkeys(data, "Failed")
        if results.get(name_cfg(_VAL_DEBUG_LEVEL)) in ("Valid", "Unchanged"):
            level = await self.cfgmgr.get_int_values(_VAL_DEBUG_LEVEL)
            if level is not None:
                self._current_debug_level = level[0]
                await self._apply_level(level[0])
        return results

    async def _apply_level(self, value: int) -> None:
        # Each call guarded individually, the same caller-supplied-callback defense
        # start_timers() uses per starter, so one bad entry cannot stop the rest. async because
        # both call sites already are, and so the failure persists via err_s() like every other one.
        for setter in self._level_setters:
            try:
                setter(value)
            except Exception as e:
                await self.pr.err_s("Level setter failed:", e, errno=_ERR_CALLBACK)

    def _charge_task_budget(self, budget: int) -> int:
        # One task end's charge, checked before the step: past _TASK_FAIL_MAX the reboot is due and the
        # value stops, so it never exceeds _TASK_FAIL_MAX + _TASK_FAIL_INCREMENT.
        return budget + _TASK_FAIL_INCREMENT if budget <= _TASK_FAIL_MAX else budget

    async def _log_dead_task(self, task: "asyncio.Task[Any]", n: int) -> None:
        # A finished Task has no .exception()/.result() (Part F.1): awaiting it again is how to learn why it
        # ended, giving the restart line below real diagnostic content.
        try:
            await task
        except asyncio.CancelledError:
            await self.pr.err_s("Task", n, "ended: was cancelled", errno=_ERR_TASK_CANCELLED)
        except Exception as e:
            await self.pr.err_s("Task", n, "ended with exception:", e, errno=_ERR_TASK_RAISED)
        else:
            await self.pr.err_s("Task", n, "ended: returned", errno=_ERR_TASK_RETURNED)

    async def _ntp_boot_signature(self) -> int | None:
        # None if not synced yet - a failing NTP callback counts as not synced (owner, 2026-07-18);
        # the caller falls back to random after _NTP_WAIT_TIME.
        try:
            synced = await self.ntp_is_synced()
        except Exception as e:  # caller-supplied callback, typed as any Callable - guarded broadly
            # since it isn't guaranteed to be a specific, known-safe implementation
            await self.pr.err_s("NTP sync callback failed:", e, errno=_ERR_CALLBACK)
            return None
        if not synced:
            return None
        return utc_now()

    def _reboot(self, message: str, action: "Callable[[], None]") -> None:
        self._reset_timer.deinit()
        self._storage_timer.deinit()
        self.pr.evt(message)
        if self._storage_pause is not None:
            self._storage_pause(value=True)
            self.pr.evt("Storage paused")
        try:
            self._reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda _b: action())
        except (MemoryError, OSError) as e:  # alarm-pool exhaustion (ENOMEM) - falls back to the same watchdog-starve
            # backstop start_and_check_tasks() already uses past _TASK_FAIL_MAX.
            self.pr.err("Could not arm reset timer, stopping watchdog feed instead:", e)
            self._force_watchdog_starve = True

    async def _run_timer_starter(self, starter: "TimerStarter", n: int) -> None:
        try:
            starter()
        except Exception as e:  # driver-supplied starter - could misbehave; persisted, and sequencing continues
            await self.pr.err_s("Timer starter", n, "failed:", e, errno=_ERR_TASK_STARTER_RAISED)
        else:
            self.pr.evt("Timer started:", n)

    async def _start_task(self, starter: "Callable[[], asyncio.Task[Any]]", n: int) -> "asyncio.Task[Any] | None":
        try:
            return starter()
        except Exception as e:  # driver-supplied starter (get_task_starters()) - could legitimately misbehave
            await self.pr.err_s("Task starter", n, "failed to start:", e, errno=_ERR_TASK_STARTER_RAISED)
            return None

    async def _status_loop(self) -> None:
        await self.uptime.set_value(0)
        await self.boot_signature.set_value(None)
        while True:
            await self._uptime_event.wait()
            uptime = await self.uptime.increment()
            self.pr.all("System uptime incremented to", uptime)
            if self._start_time_set:
                continue
            utc = await self._ntp_boot_signature()
            if utc is not None:
                await self.boot_signature.set_value(utc)
                self.pr.one("System boot signature set by NTP.")
                self._start_time_set = True
            elif uptime >= _NTP_WAIT_TIME:
                # get_rand_32()-seeded (pico-sdk pico_rand, real ring-oscillator entropy) - unique
                # per boot, not a fixed/repeatable seed.
                await self.boot_signature.set_value(random.getrandbits(32))
                self.pr.one("System boot signature set by random number.")
                self._start_time_set = True

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_status]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return [self.start_uptime_timer]

    def start_asy_status(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._status_loop())

    def start_uptime_timer(self) -> None:
        # A failed arm degrades rather than reboots: only uptime and the boot signature stay unresolved this boot.
        arm_tick_timer(self._uptime_timer, self._uptime_event, self.pr, "uptime")

    def stop_uptime_timer(self) -> None:
        self._uptime_timer.deinit()

    async def get_boot_signature(self) -> int | float | None:
        # None until resolved; then a UTC timestamp if NTP synced, else random after _NTP_WAIT_TIME -
        # stable for the rest of this boot, so a later change means a reboot happened.
        return await self.boot_signature.get_value()

    def get_cfg_schema(self) -> "ConfigSchema":
        return self._cfg_schema

    def get_debug_level(self) -> int:
        return self._current_debug_level

    async def get_dict_cfg(self) -> "dict[str, dict[str, CfgValue]]":
        # the nested {name: {field: value}} shape every SettingsGroup module returns (Part C.6).
        names = schema_names(self._cfg_schema)
        values = await self.cfgmgr.get_dict(names)
        return {_NAME: values if values is not None else dict.fromkeys(names)}

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    def get_error_sources(self) -> "list[ErrorSource]":
        # Fan-in primitive (SPECIFICATION.md Part C.14/G.2) - matches asy_base_classes.py's
        # SensorReaderConfig.get_error_sources() shape (this class owns a cfgmgr too), duck-typed
        # rather than inherited (see this module's own "not a SensorReaderConfig subclass" comment).
        return [self, self.cfgmgr]

    def get_loggers(self) -> "list[PrintLogHistory]":
        return [self.pr, self.cfgmgr.pr]

    async def get_uptime(self) -> int:
        value = await self.uptime.get_value()  # never None: only ever set_value(0)/increment(), never a None sentinel
        return 0 if value is None else value

    async def set_debug_level(self, value: int) -> bool:
        results = await self._set_dict_cfg({name_cfg(_VAL_DEBUG_LEVEL): value}, self._cfg_schema)
        return results.get(name_cfg(_VAL_DEBUG_LEVEL)) in ("Valid", "Unchanged")

    def feed_watchdog(self) -> None:
        # The one reusable, no-op-safe watchdog access point (SPECIFICATION.md Part G.2): every feed
        # site calls this instead of repeating the "watchdog=None, or the reset timer failed to arm"
        # check. A device with no watchdog and one deliberately left to die take the same path.
        if self.watchdog is not None and not self._force_watchdog_starve:
            self.watchdog.feed()

    def pause_permanent_storage(self, duration: int) -> None:
        if self._storage_pause is not None:
            duration = min(max(duration, 0), _MAX_STORAGE_PAUSE)
            self._storage_timer.deinit()
            if duration == 0:
                self.pr.evt("Storage immediately unpaused.")
                self._storage_pause(value=False)
            else:
                self.pr.evt("Storage paused for", duration, "seconds.")
                self._storage_pause(value=True)
                storage_pause = self._storage_pause  # local capture: mypy can't narrow a closed-over self attribute
                try:
                    self._storage_timer.init(
                        period=duration * 1000,
                        mode=Timer.ONE_SHOT,
                        callback=lambda _b: storage_pause(value=False),
                    )
                except (MemoryError, OSError) as e:  # alarm-pool exhaustion (ENOMEM) - without the auto-unpause timer,
                    # storage would stay paused forever; safer to abort the pause than risk that.
                    self.pr.err("Could not arm auto-unpause timer, aborting pause:", e)
                    storage_pause(value=False)

    def reboot_bootloader(self) -> None:
        self._reboot("Reboot into bootloader triggered", system_bootloader)

    def reboot_system(self) -> None:
        self._reboot("Reboot triggered", system_reset)

    async def reset_error_counter(self) -> None:
        await self.pr.reset()

    async def setup(self) -> bool:
        # Its own logger first, then the level-setter provider once and the persisted system-settings store
        # (Part C.13's sync-__init__/async-setup()); the stored level reaches every setter. True when the store is valid.
        await self.pr.setup()
        if self._level_setters_provider is not None:
            self._level_setters = self._level_setters_provider()
        await self.cfgmgr.setup()
        level = await self.cfgmgr.get_int_values(self._cfg_schema)
        if level is not None:
            self._current_debug_level = level[0]
            await self._apply_level(level[0])
        return self.cfgmgr.valid

    async def start_and_check_tasks(self, task_starters: "list[Callable[[], asyncio.Task[Any]]]") -> None:
        # Task[Any], not the TaskStarter alias, until every reader's task returns None (its read loop still returns bool).
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
                task = tasks[n]
                if task is None or task.done():
                    if task is not None:
                        await self._log_dead_task(task, n)
                    task_errors = self._charge_task_budget(task_errors)
                    tasks[n] = await self._start_task(task_starters[n], n)
                    no_fail = False
                    self.pr.wrn("Task ended - attempting restart, error counter increased to", task_errors, "- task", n)

            if no_fail:
                self.pr.all("All tasks running.")
                if task_errors > 0:  # the decay, checked before the step
                    task_errors -= 1
                    self.pr.evt("Task error counter reduced to", task_errors)

            if task_errors <= _TASK_FAIL_MAX:
                self.feed_watchdog()
            else:
                await self.pr.err_s("Task error counter above", _TASK_FAIL_MAX, "- reboot triggered!", errno=_ERR_TASK_BUDGET_REBOOT)
                self.reboot_system()
                return

            await asyncio.sleep(_TASK_CHECK_TIME)

    async def start_timers(self, triggers: "list[TimerStarter]", timers: "list[TimerStarter]") -> None:
        # The unstaggered timer starters in order, then each read trigger k at t0 + k * slot from one shared
        # start, in task context (SPECIFICATION.md Part C.9.1): a stagger wait is a one-shot that only sets a
        # flag; its failed arm sleeps instead, so every trigger still starts.
        for n, starter in enumerate(timers):
            await self._run_timer_starter(starter, n)
        t0 = time.ticks_ms()
        slot = _TIMER_BASE_PERIOD // (len(triggers) + 1)
        for k, starter in enumerate(triggers):
            wait = time.ticks_diff(time.ticks_add(t0, k * slot), time.ticks_ms())
            if wait > 0:
                try:
                    self._sequencer_timer.init(period=wait, mode=Timer.ONE_SHOT, callback=lambda _b: self._sequencer_flag.set())
                except (MemoryError, OSError) as e:  # alarm-pool exhaustion (ENOMEM)
                    await self.pr.err_s("Could not arm the stagger timer, using sleep:", e, errno=_ERR_TIMER)
                    await asyncio.sleep_ms(wait)
                else:
                    await self._sequencer_flag.wait()  # no software timeout: the watchdog is the backstop (owner, 2026-07-18)
            await self._run_timer_starter(starter, len(timers) + k)
        self.pr.one("All timers running.")
