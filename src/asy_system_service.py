"""Generic system-housekeeping service shared by every generated sensortask_<device>.py: uptime, boot signature, reset reason, the reboot commands, the staggered timer start, the task supervisor, and a persisted system-settings store (config_SYSTEM.cfg).
Every method returns a well-defined value, never raises.
Reset reason and boot phase live in machine.mem_backup() regions 0/1 - RAM that survives a reset, never flash or FRAM (owner, 2026-09-26).
"""
# A live debug-level change is pushed through the other loggers' own set_level() methods (the level_setters provider,
# resolved once in setup()), not a shared mutable value (owner, 2026-08-11, paraphrase: SharedLevel was reverted for breaking encapsulation).
# The real reset a reboot command takes after _RESET_DELAY (Part N system.reset_delay_s) is the intent, not a failure.

import asyncio
import gc
import random
import time

from machine import PWRON_RESET, WDT, Timer, mem_backup, reset_cause
from machine import bootloader as system_bootloader
from machine import reset as system_reset
from micropython import const

from asy_base_classes import LockedValue, TickSeconds, arm_tick_timer, utc_now
from asy_config_manager import ConfigManager, config_filename, instance_name, name_cfg, schema_names
from asy_print_log import DEFAULT_LOG, LogConfig, make_logger

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, Protocol

    from _mpy_shed.time_mp import _TicksMs

    from asy_base_classes import ErrorSource, JsonMapping, NtpSyncFct, TaskStarter, TimerStarter
    from asy_config_manager import CfgValue, ConfigSchema, WriteValidity
    from asy_fram_manager import FRAMManager
    from asy_print_log import ErrorLog, PrintLogHistory

    # Keyword-only call shape of FRAMManager.set_pause(), which a plain Callable[...] alias
    # cannot express - same structural-Protocol convention as asy_print_log.py's _FramChunk.
    class _StoragePause(Protocol):
        def __call__(self, *, value: bool) -> None: ...

# Codes from the global catalog (buildgen/error_catalog.json): the shared ones and SYSTEM's bands.
_ERR_CALLBACK = const(14)
_ERR_TIMER = const(17)
_ERR_TASK_STARTER_RAISED = const(40)
_ERR_TASK_BUDGET_REBOOT = const(41)
_ERR_TASK_RAISED = const(42)
_ERR_TASK_CANCELLED = const(43)
_ERR_TASK_RETURNED = const(44)
_WRN_CONFIG_LOST = const(69)

# @tunable system.reset_delay_s = 4
_RESET_DELAY = const(4)  # seconds from arming the reset to running it; nothing feeds meanwhile, keep < watchdog timeout
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

# The reset-reason record (region 0) and the boot-phase marker (region 1) each store [magic, value, value ^ check]; every
# word stays below 2**30, so no store allocates. The codes and their decoding: SPECIFICATION.md Part F.5.4.
_RR_MAGIC = const(0x2A5E0001)
_BP_MAGIC = const(0x2A5E0002)
_RR_CHECK = const(0x15A5A5A5)
_RR_UNKNOWN = const(0)
_RR_POWER_ON = const(1)
_RR_WATCHDOG = const(2)
_RR_REBOOT = const(3)
_RR_BOOTLOADER = const(4)
_RR_TASK_BUDGET = const(5)
_RR_STARVE_ARM_FAILED = const(6)
_RR_CONFIG_RESET = const(7)
_RR_FRAM_ERASED = const(8)
_RR_COMMAND_INCOMPLETE = const(9)
_RR_BOOT_FAILURE = const(10)  # + the boot phase that never completed
BOOT_CONSTRUCTION = const(1)
BOOT_SETUP = const(2)
BOOT_TASKS = const(3)
BOOT_TIMERS = const(4)
BOOT_NTP = const(5)
BOOT_DONE = const(6)

# This service's one optional live cross-instance dependency (SPECIFICATION.md Part C.14.2): its FRAM
# error-log target, resolved from [device.wiring].fram_target implicitly because this is mandatory
# infra, never an [[instance]] entry.
# @wiring fram_target FRAMManager log optional kwarg

# General, module-independent system-settings schema (config_SYSTEM.cfg, via _NAME above) - Part C.5
# has the setSGP/setBMP history this superseded. Adding a field is the same one-line _VAL_*-tuple
# concatenation every other ConfigManager-backed module uses.
# @web-group section=system submitGroup=settings label="System Settings" submit=true
# @web DebugLevel section=system submitGroup=settings label="Debug Level"
_VAL_DEBUG_LEVEL = const((("DebugLevel", "int", 0, 0, 5, None),))  # range matches PrintLog's six levels
# (0 off … 5 all); default 0 matches the reference file's own debug=False.


def _write_region(region: int, magic: int, value: int) -> None:
    # Three word stores, magic last: a reset between them leaves a record that reads as invalid, never as valid.
    mem = mem_backup(region)
    mem[1] = value
    mem[2] = value ^ _RR_CHECK
    mem[0] = magic


def begin_boot() -> int:
    # Once per boot, before any construction: decodes this boot's reset reason, clears the record (magic first)
    # and marks phase 1, so a crash in any constructor already reads as a boot failure.
    record = mem_backup(0)
    phase = mem_backup(1)
    if reset_cause() == PWRON_RESET:
        code = _RR_POWER_ON
    elif record[0] == _RR_MAGIC and record[2] == record[1] ^ _RR_CHECK:
        code = record[1]
    elif record[0] != 0:
        code = _RR_UNKNOWN
    elif phase[0] == _BP_MAGIC and phase[2] == phase[1] ^ _RR_CHECK and BOOT_CONSTRUCTION <= phase[1] < BOOT_DONE:
        code = _RR_BOOT_FAILURE + phase[1]
    else:
        code = _RR_WATCHDOG
    for i in range(len(record)):
        record[i] = 0
    _write_region(1, _BP_MAGIC, BOOT_CONSTRUCTION)
    return code


def write_reset_record(code: int) -> None:
    # Written immediately before an intended reset; the next boot's begin_boot() reads and clears it.
    _write_region(0, _RR_MAGIC, code)


class SystemService:
    def __init__(
        self,
        asy_ntp_callback: "NtpSyncFct",
        watchdog: WDT | None = None,
        storage: "FRAMManager | None" = None,
        level_setters: "Callable[[], list[Callable[[int], bool]]] | None" = None,
        config_stores: "Callable[[], list[ConfigManager]] | None" = None,
        reset_reason: int = _RR_UNKNOWN,
        cfg_path: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        self.pr = make_logger(log, _NAME)
        self.name = _NAME  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (error_sources=/settings=).
        # callback for starting and stopping permanent storage communication
        self._storage_pause: _StoragePause | None = storage.set_pause if storage is not None else None
        self._uptime = TickSeconds()  # measured seconds since construction, saturating at COUNTER_CAP
        self._uptime_event = asyncio.ThreadSafeFlag()
        self._uptime_timer = Timer()
        self._reset_timer = Timer()
        # Preallocated like the other timers: start_timers() re-.init()s it for each stagger wait rather than constructing a
        # fresh Timer() each time, which the GC would disarm before it fires (SPECIFICATION.md Part F.1).
        self._sequencer_timer = Timer()
        self._sequencer_flag = asyncio.ThreadSafeFlag()  # one waiter: start_timers() runs once per boot
        self._ntp_is_synced = asy_ntp_callback
        self._start_time_set = False
        # None until _status_loop() resolves it (owner, 2026-07-18) - a later change to this value signals a reboot happened.
        self._boot_signature = LockedValue(init_value=None)
        self._watchdog = watchdog
        # One-way: set once a reset is armed or cannot be armed; no feed site feeds after it.
        self._force_watchdog_starve = False
        # System-settings store, deliberately not a SensorReaderConfig subclass - no measurement
        # data and no error-streak concept, both of which that base would drag in unused - just a
        # directly-embedded ConfigManager.
        self._cfg_schema: ConfigSchema = _VAL_DEBUG_LEVEL
        self.cfgmgr = ConfigManager(config_filename(cfg_path, instance_name(_NAME, "")), self._cfg_schema, _NAME, log=log)
        # Every logger's own set_level(), resolved once from the provider in setup() and called on every level change.
        self._level_setters_provider = level_setters
        self._level_setters: list[Callable[[int], bool]] = []
        # Every module's config store, resolved once from the provider in setup(); every reset flushes them.
        self._config_stores_provider = config_stores
        self._config_stores: list[ConfigManager] = []
        self._reset_reason = reset_reason
        self._reset_armed = False  # one-way: the first armed reset is the one that fires
        self._reset_due = asyncio.ThreadSafeFlag()  # set by the reset timer; _reset_when_due() runs the reset
        self._reset_task: asyncio.Task[None] | None = None
        self._supervisor_task: asyncio.Task[None] | None = None
        self._never = asyncio.Event()  # never set: start_and_check_tasks() waits on it for good
        # Task[Any], not the TaskStarter alias, until every reader's task returns None (its read loop still returns bool).
        self._task_starters: list[Callable[[], asyncio.Task[Any]]] = []
        self._tasks: list[asyncio.Task[Any] | None] = []
        self._unpause_at: _TicksMs | None = None  # ticks_ms() deadline of a mempause auto-unpause; None when none is pending
        # True while the uptime tick timer is unarmed: _status_loop() then sleeps one second per pass and re-arms.
        self._tick_failed = False

    async def _set_dict_cfg(
        self, data: "JsonMapping", _cfg_vals: "ConfigSchema",
    ) -> "WriteValidity":
        # The SettingsGroup call shape: persist through cfgmgr on its own schema (the argument goes unused), then push the
        # registry. It pushes on "Unchanged" too, not only on a real change, so every logger's live
        # level stays provably in sync with the persisted value after any accepted request.
        persisted, results = await self.cfgmgr.write_config(data)
        if not persisted:
            return dict.fromkeys(data, "Failed")
        if results.get(name_cfg(_VAL_DEBUG_LEVEL)) in ("Valid", "Unchanged"):
            level = await self.cfgmgr.get_int_values(self._cfg_schema)
            if level is not None:
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

    async def _flush_config_stores(self, *, close: bool = False) -> None:
        # The stores are caller-supplied through the provider: one failing flush never stops the others or the arm.
        if close:
            for store in self._config_stores:
                store.close_writes()
        for store in self._config_stores:
            try:
                await store.flush_pending()
            except Exception as e:
                await self.pr.err_s("Config flush before reset failed:", store.name, e, errno=_ERR_CALLBACK)

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
            synced = await self._ntp_is_synced()
        except Exception as e:  # caller-supplied callback, typed as any Callable - guarded broadly
            # since it isn't guaranteed to be a specific, known-safe implementation
            await self.pr.err_s("NTP sync callback failed:", e, errno=_ERR_CALLBACK)
            return None
        if not synced:
            return None
        return utc_now()

    async def _reboot(self, code: int, message: str, action: "Callable[[], None]") -> None:
        # Every reset's one path: record, flush, pause, then arm the one-shot whose flag wakes _reset_when_due().
        if self._reset_armed:
            self.pr.evt("Reset already armed, request ignored")
            return
        self._reset_armed = True
        write_reset_record(code)
        await self._flush_config_stores()
        self.pr.evt(message)
        if self._storage_pause is not None:
            self._storage_pause(value=True)
            self.pr.evt("Storage paused")
        try:
            self._reset_task = asyncio.create_task(self._reset_when_due(action))
            self._reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda _b: self._reset_due.set())
            # Nothing feeds the countdown: a one-shot the scheduler drops leaves the watchdog to reset (Part C.9).
            self._force_watchdog_starve = True
        except (MemoryError, OSError) as e:  # alarm-pool exhaustion (ENOMEM) or the task's allocation
            if self._reset_task is not None:
                self._reset_task.cancel()
            write_reset_record(_RR_STARVE_ARM_FAILED)
            self._force_watchdog_starve = True
            # print-only: FRAM is paused here, so a persisted entry would be dropped;
            # the reset-reason record (code 6) is this failure's persisted trace.
            self.pr.err("Could not arm reset timer, stopping watchdog feed instead:", e)

    async def _reset_when_due(self, action: "Callable[[], None]") -> None:
        await self._reset_due.wait()
        # The last flush: a write the store took inside the countdown is on flash when the reset fires; with FRAM
        # paused, a failure here reaches the console only. The stores close first and nothing awaits between the last
        # flush and the reset, so no write can start in between.
        await self._flush_config_stores(close=True)
        action()

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
        # Uptime is measured, never counted, so a restart of this task keeps it and the boot signature. Each pass
        # waits on the 1 s tick, or sleeps a second and re-arms while that timer is unarmed (SPECIFICATION.md Part C.9).
        reported = False
        while True:
            if self._tick_failed:
                if not reported:
                    await self.pr.err_s("Uptime timer not armed - one-second sleep instead, re-arm retried", errno=_ERR_TIMER)
                    reported = True
                await asyncio.sleep_ms(1000)
                self._tick_failed = not arm_tick_timer(self._uptime_timer, self._uptime_event, self.pr, "uptime")
            else:
                await self._uptime_event.wait()
            uptime = self._uptime.read()
            self.pr.all("System uptime:", uptime)
            if self._unpause_at is not None and time.ticks_diff(time.ticks_ms(), self._unpause_at) >= 0:
                self._unpause_at = None
                # A reset has paused storage for good; a late auto-unpause must not reopen it.
                if not self._reset_armed and self._storage_pause is not None:
                    self._storage_pause(value=False)
                    self.pr.evt("Storage auto-unpaused.")
            if self._start_time_set:
                continue
            utc = await self._ntp_boot_signature()
            if utc is not None:
                await self._boot_signature.set_value(utc)
                self.pr.one("System boot signature set by NTP.")
                self._start_time_set = True
            elif uptime >= _NTP_WAIT_TIME:
                # get_rand_32()-seeded (pico-sdk pico_rand, real ring-oscillator entropy) - unique
                # per boot, not a fixed/repeatable seed.
                await self._boot_signature.set_value(random.getrandbits(32))
                self.pr.one("System boot signature set by random number.")
                self._start_time_set = True

    async def _supervise(self) -> None:
        # The supervisor loop, its own task (start_and_check_tasks() owns it): restarts every ended task, charging
        # the restart budget, and feeds the watchdog once per pass (SPECIFICATION.md Part G.2).
        task_errors = 0
        while True:
            escalate = False
            no_fail = True
            for n in range(len(self._tasks)):
                task = self._tasks[n]
                if task is None or task.done():
                    if task is not None:
                        await self._log_dead_task(task, n)
                        # Retired before the escalation can break out: a second await of an ended task can raise None
                        # (SPECIFICATION.md Part F.1), and an empty slot is restarted without a second entry.
                        self._tasks[n] = None
                    task_errors = self._charge_task_budget(task_errors)
                    no_fail = False
                    if task_errors > _TASK_FAIL_MAX and not self._reset_armed:
                        # Escalate at the first end past the budget, fed once: a scan of every dead task could outlast the
                        # watchdog before the reset is even armed.
                        escalate = True
                        break
                    self._tasks[n] = await self._start_task(self._task_starters[n], n)
                    self.pr.wrn("Task ended - attempting restart, error counter increased to", task_errors, "- task", n)
            if escalate:
                await self.pr.err_s("Task error counter above", _TASK_FAIL_MAX, "- reboot triggered!", errno=_ERR_TASK_BUDGET_REBOOT)
                # One feed after the entry, then starve one-way: the reset arms below and nothing feeds until it
                # fires; later passes keep restarting, unfed.
                self.feed_watchdog()
                self._force_watchdog_starve = True
                await self._reboot(_RR_TASK_BUDGET, "Reboot triggered", system_reset)
            if no_fail:
                self.pr.all("All tasks running.")
                if task_errors > 0:  # the decay, checked before the step
                    task_errors -= 1
                    self.pr.evt("Task error counter reduced to", task_errors)
            self.feed_watchdog()
            await asyncio.sleep(_TASK_CHECK_TIME)

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_status]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return [self.start_uptime_timer]

    def start_asy_status(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._status_loop())

    def start_uptime_timer(self) -> None:
        # A failed arm degrades rather than reboots: _status_loop() falls back to one-second sleeps and re-arms.
        self._tick_failed = not arm_tick_timer(self._uptime_timer, self._uptime_event, self.pr, "uptime")
        if self._tick_failed:
            self._uptime_event.set()  # wakes _status_loop() into its one-second fallback

    async def get_boot_signature(self) -> int | float | None:
        # None until resolved; then a UTC timestamp if NTP synced, else random after _NTP_WAIT_TIME -
        # stable for the rest of this boot, so a later change means a reboot happened.
        return await self._boot_signature.get_value()

    def get_cfg_schema(self) -> "ConfigSchema":
        return self._cfg_schema

    async def get_dict_cfg(self) -> "dict[str, dict[str, CfgValue]]":
        # the nested {name: {field: value}} shape every SettingsGroup module returns, or the unavailable marker (Part C.6)
        # when the store answers nothing or only defaults standing in for a file it could not read.
        values = await self.cfgmgr.get_dict(schema_names(self._cfg_schema))
        return {_NAME: values if values is not None and self.cfgmgr.writable else {"error": "unavailable"}}

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    def get_error_sources(self) -> "list[ErrorSource]":
        # Fan-in primitive (SPECIFICATION.md Part C.14/G.2) - matches asy_base_classes.py's
        # SensorReaderConfig.get_error_sources() shape (this class owns a cfgmgr too), duck-typed
        # rather than inherited (see this module's own "not a SensorReaderConfig subclass" comment).
        return [self, self.cfgmgr]

    def get_loggers(self) -> "list[PrintLogHistory]":
        return [self.pr, self.cfgmgr.pr]

    def get_reset_reason(self) -> int:
        return self._reset_reason

    async def get_uptime(self) -> int:
        return self._uptime.read()

    def boot_phase(self, phase: int) -> None:
        # Marks a boot-phase transition in region 1: a watchdog reset before BOOT_DONE then decodes as 10 + phase.
        _write_region(1, _BP_MAGIC, phase)

    def feed_watchdog(self) -> None:
        # The one reusable, no-op-safe watchdog access point (SPECIFICATION.md Part G.2): every feed
        # site calls this instead of repeating the "watchdog=None, or the reset timer failed to arm"
        # check. A device with no watchdog and one deliberately left to die take the same path.
        if self._watchdog is not None and not self._force_watchdog_starve:
            self._watchdog.feed()

    def pause_permanent_storage(self, duration: int) -> bool:
        # True: a pause always ends - its deadline is tested on a pass that already runs, so nothing can fail after it began.
        if self._storage_pause is not None:
            duration = min(max(duration, 0), _MAX_STORAGE_PAUSE)
            if duration == 0:
                self._unpause_at = None
                self.pr.evt("Storage immediately unpaused.")
                self._storage_pause(value=False)
            else:
                self.pr.evt("Storage paused for", duration, "seconds.")
                self._storage_pause(value=True)
                # A deadline, not a timer: tested on every uptime pass, so no fire can be lost (SPECIFICATION.md Part F.1).
                self._unpause_at = time.ticks_add(time.ticks_ms(), duration * 1000)
        return True

    async def reboot_bootloader(self) -> None:
        await self._reboot(_RR_BOOTLOADER, "Reboot into bootloader triggered", system_bootloader)

    async def reboot_system(self) -> None:
        await self._reboot(_RR_REBOOT, "Reboot triggered", system_reset)

    async def reset_error_counter(self) -> bool:
        return await self.pr.reset()

    async def setup(self) -> bool:
        # Resolves both boot providers once, then the persisted level: the store's value wins over the constructor's
        # debug=, an unreadable store keeps the constructed level (Part C.13's sync-__init__/async-setup()).
        await self.pr.setup()
        if self._level_setters_provider is not None:
            self._level_setters = self._level_setters_provider()
        if self._config_stores_provider is not None:
            self._config_stores = self._config_stores_provider()
        await self.cfgmgr.setup()
        if self.cfgmgr.absent_at_boot and self.pr.restored and self._reset_reason not in (_RR_CONFIG_RESET, _RR_COMMAND_INCOMPLETE):
            # The stock _boot.py reformats an unmountable filesystem silently; a missing settings file beside
            # surviving FRAM history is its one trace (a commanded config reset deletes the files itself).
            await self.pr.wrn_s("Config file absent while FRAM history exists - filesystem reformatted or wiped", wrnno=_WRN_CONFIG_LOST)
        if self.cfgmgr.writable:
            level = await self.cfgmgr.get_int_values(self._cfg_schema)
            if level is not None:
                await self._apply_level(level[0])
        return self.cfgmgr.valid

    async def start_and_check_tasks(self, task_starters: "list[Callable[[], asyncio.Task[Any]]]") -> None:
        # The boot placement reset (SPECIFICATION.md I.4(f.1)): the second of the two one-time boot lists that get a
        # placement reset between their units - each collect puts the allocator's free-scan index back to zero.
        # Not hygiene, not compaction, and never in the supervisor below.
        self._task_starters = task_starters
        self._tasks = [None] * len(task_starters)
        gc.collect()
        # A task that dies with nobody awaiting it reaches SYSTEM's level-gated report (Part F.1). A handler already
        # set stays: the PC tiers install one that prints at every level, so their memory gates see each death.
        loop = asyncio.get_event_loop()
        if loop.get_exception_handler() is None:
            loop.set_exception_handler(self.pr.report_unretrieved)
        for n, starter in enumerate(task_starters):
            self._tasks[n] = await self._start_task(starter, n)
            await asyncio.sleep_ms(1000 // len(task_starters))
            gc.collect()
        # Never returns: the supervisor runs as its own task so a system command can cancel it and prove it stopped
        # (owner, 2026-09-30); cancelling this call cancels it too.
        self._supervisor_task = asyncio.create_task(self._supervise())
        try:
            await self._never.wait()
        finally:
            self._supervisor_task.cancel()

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
