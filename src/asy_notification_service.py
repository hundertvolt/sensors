"""Generic threshold-triggered LED notification signalling: `NotificationSignal` (per-condition data
holder) and `NotificationCoordinator` (shared sleep-window/interval/`AutoOn`/flash brightness+duration).
Promoted from improved-quality/neopixel_signal.py's `airquality_auto_signal()`/`auto_led_override()` (see CLAUDE.md/BACKLOG.md); drives an LED through `request_signal_cb`, decoupled from any concrete LED implementation.
"""
# Signals are passed at construction; a refused one is printed at once and persisted by setup().

import asyncio
import time
from collections import namedtuple

from micropython import const

from base_classes import LockedCounter, SensorReaderConfig
from config_manager import make_dict, name_cfg, schema_names
from print_log import DEFAULT_LOG, LogConfig

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, Protocol

    # The stubs model a ticks_ms() value as an opaque type, not a plain int, precisely so it can
    # only ever reach time.ticks_diff() - _next_sleep_secs()'s t0 is exactly such a value.
    from _mpy_shed.time_mp import _TicksMs

    from base_classes import ValueRef
    from config_manager import ConfigSchema
    from print_log import ErrorLog

    # Structural Protocol for whatever local-time struct the caller's callback returns
    # (SPECIFICATION.md Part C.10's typing convention) - read-only, so a namedtuple
    # (asy_ntp_client.py's GMTimeStruct, the production wiring) satisfies it too.
    class _LocalTime(Protocol):
        @property
        def hour(self) -> int: ...
        @property
        def minute(self) -> int: ...

    class _ValueSource(Protocol):
        # Structural stand-in for a NotificationSignal's producer (SPECIFICATION.md Part C.10's
        # typing convention) - any *_Reader exposing the same get_data() -> NamedTuple contract
        # every driver already has (C.4.2). Only get_data() is used here.
        async def get_data(self) -> "Any": ...

# Codes from the global catalog (buildgen/error_catalog.json; SPECIFICATION.md Part C.7.1).
_ERR_CALLBACK = const(14)
_ERR_SOURCE = const(15)
_ERR_CFG_READ = const(26)
_WRN_CFG_READ = const(13)
_WRN_NOTIFY_NAME_COLLISION = const(44)
_WRN_NOTIFY_SCHEMA_SHAPE = const(45)

_MAX_OVERRIDE_TIME = const(3600)
_NAME = const("NOTIFY")
# @tunable notify.loop_tick_s = 1
_LOOP_TICK_S = const(1)  # auto_led_override()'s countdown step
# @tunable notify.min_sleep_s = 0.1
_MIN_SLEEP_S = const(0.1)  # floor of monitor_loop()'s sleep to its next cycle
# @tunable notify.cfg_fail_interval_s = 600.0
_CFG_FAIL_INTERVAL_S = const(600.0)  # cycle interval while the own configuration cannot be read

# This driver's live cross-instance dependencies (Parts C.14 and L.4): the LED it signals through,
# required, in "attr" mode - the resolved NeopixelDriver's own request_signal bound method is passed
# as request_signal_cb, per Part L.2's "no getters in generated code" - plus the optional FRAM.
# @wiring signal_sink NeopixelDriver request_signal required attr
# @wiring fram_target AsyFramManager log optional kwarg


class _DefaultSignalSink:
    """The wiring-defaults mechanism (SPECIFICATION.md Part L.6.2), opted into via
    [instance.wiring].signal_sink = {default = true} - a no-op LED sink for a notification setup
    that shouldn't blink any LED."""

    # Signature and return-value contract match NeopixelDriver.request_signal exactly, so codegen's
    # existing attr-mode rendering (f"{var}.{wf.target}") needs no special-casing for a defaulted field.
    async def request_signal(self, r: int, g: int, b: int, t: float) -> bool:
        return False

# Own schema; config keys carry no "Led" prefix (`WarnCO2`, not `LedWarnCO2`): the new API is the
# only reference (owner, 2026-09-26), SPECIFICATION.md A.4. Ranges and defaults mirror legacy's
# REST bounds.
_VAL_ON_H = const((("OnH", "int", 10, 0, 23, None),))
_VAL_ON_M = const((("OnM", "int", 0, 0, 59, None),))
_VAL_OFF_H = const((("OffH", "int", 18, 0, 23, None),))
_VAL_OFF_M = const((("OffM", "int", 0, 0, 59, None),))
_VAL_FLASH_BRI = const((("FlashBri", "int", 200, 1, 255, None),))
_VAL_INTERV = const((("Interv", "float", 300.0, 60.0, 3600.0, None),))
_VAL_FLASH_DUR = const((("FlashDur", "float", 2.0, 0.5, 10.0, None),))
_VAL_AUTO_ON = const((("AutoOn", "bool", True, None, None, None),))

# WarnCO2/WarnVOC/WarnHum come with each signal passed at construction, not as _VAL_* constants here,
# so their web metadata is generator-owned (buildgen.definitions._WARN_SIGNAL_WEB_CATALOG, the parallel
# of codegen._KNOWN_SIGNALS) - neither is a per-device fact this file could tag (Part L.5).

# Literal submitGroup ("autoConfig"), not the "self" sentinel the sensors use: this is a singleton
# service, so there is nothing to disambiguate, and the hand-written definitions established it.
# @web-group section=notification submitGroup=autoConfig label="Automatic Notification Configuration" submit=true
# @web AutoOn section=notification submitGroup=autoConfig label="Automatic Notifications" description="Auto On must be before Off, on the same day."
# @web OnH section=notification submitGroup=autoConfig label="Auto On Hour"
# @web OnM section=notification submitGroup=autoConfig label="Auto On Minute"
# @web OffH section=notification submitGroup=autoConfig label="Auto Off Hour"
# @web OffM section=notification submitGroup=autoConfig label="Auto Off Minute"
# @web FlashBri section=notification submitGroup=autoConfig label="Flash Brightness"
# @web Interv section=notification submitGroup=autoConfig label="Flash Interval" unit="s"
# @web FlashDur section=notification submitGroup=autoConfig label="Flash Duration" unit="s"

_VAL_INT_FIELDS = _VAL_ON_H + _VAL_ON_M + _VAL_OFF_H + _VAL_OFF_M + _VAL_FLASH_BRI
_VAL_FLOAT_FIELDS = _VAL_INTERV + _VAL_FLASH_DUR
_VAL_BOOL_FIELDS = _VAL_AUTO_ON
# Own static schema fragment; the constructor appends one field per kept signal to it.
_VAL_OWN_SCHEMA = _VAL_INT_FIELDS + _VAL_FLOAT_FIELDS + _VAL_BOOL_FIELDS

# Minimal but real measurement snapshot in C.4.2's get_data() shape, like every other Reader:
# whether anything was triggered as of the last completed poll cycle. Kept as a literal tuple, not
# `_FIELDS`: mypy's namedtuple plugin infers field names only from a literal at the call site.
NOTIFY = namedtuple("NOTIFY", ("Triggered", "TS"))
_FIELDS = const(("Triggered", "TS"))  # kept in sync with NOTIFY's own fields above


class NotificationSignal:
    def __init__(
        self,
        name: str,
        value: "ValueRef",
        field_schema: "ConfigSchema",
        color: "tuple[int, int, int]",
        *,
        above: bool = True,
    ) -> None:
        self.name = name
        # A reference to the producer plus the field to read off its get_data() result (Part C.14):
        # never a wrapping getter.
        self.value = value
        self.field_schema = field_schema
        self.color = color  # per-channel weight (0/1), scaled by FlashBri at trigger time
        self.above = above
        # Only ever touched by the coordinator's single poll-loop task - no lock needed.
        self.last_value: int | float | None = None
        self.triggered = False


def _refusal(notif: NotificationSignal, taken: "set[str]") -> "tuple[str, int]":
    # ("", 0) accepts the signal; otherwise the reason and its warning code.
    key = name_cfg(notif.field_schema)
    if key == "":
        return "field_schema must have exactly one field, ignoring", _WRN_NOTIFY_SCHEMA_SHAPE
    if key in taken:
        return "field name '" + key + "' collides, ignoring", _WRN_NOTIFY_NAME_COLLISION
    return "", 0


class NotificationCoordinator(SensorReaderConfig):
    def __init__(
        self,
        request_signal_cb: "Callable[[int, int, int, float], Coroutine[Any, Any, bool]]",
        local_time_callback: "Callable[[], Coroutine[Any, Any, _LocalTime | None]]",
        signals: "tuple[NotificationSignal, ...]",
        cfg_path: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        # Each signal is checked in order before the schema exists; a refused one is buffered and
        # printed once the logger exists, then persisted by setup() (no logger before super()).
        accepted: list[NotificationSignal] = []
        self._pending_wrn: list[tuple[str, int]] = []
        taken = set(schema_names(_VAL_OWN_SCHEMA))
        combined: ConfigSchema = _VAL_OWN_SCHEMA
        for notif in signals:
            reason, wrnno = _refusal(notif, taken)
            if reason:
                self._pending_wrn.append((reason + ": " + notif.name, wrnno))
            else:
                accepted.append(notif)
                taken.add(name_cfg(notif.field_schema))
                combined = combined + notif.field_schema
        self._registered = tuple(accepted)
        super().__init__(
            NOTIFY(Triggered=False, TS=None),
            _NAME,
            combined,
            max_module_error=0,  # no failure streak: a restart re-reads nothing monitor_loop() doesn't (Part C.7.2)
            cfg_path=cfg_path,
            log=log,
        )
        for msg, _wrnno in self._pending_wrn:
            self.pr.wrn(msg)
        self._request_signal_cb = request_signal_cb
        self._local_time_callback = local_time_callback
        self.override_secs = LockedCounter(max_val=_MAX_OVERRIDE_TIME)
        self._auto_active = True

    def _next_sleep_secs(self, interv: float, t0: "_TicksMs") -> float:  # t0: an opaque ticks_ms() value - only ever compared via time.ticks_diff()
        # Isolated from monitor_loop() specifically so it's directly unit-testable without needing
        # a real elapsed time close to Interv's own 60.0s schema floor to observe the floor kick in.
        rem_interv = interv - (time.ticks_diff(time.ticks_ms(), t0) * 0.001)  # run duration so far in sec
        return max(rem_interv, _MIN_SLEEP_S)

    def _now(self) -> int | None:
        try:
            return time.mktime(time.gmtime())
        except (OverflowError, OSError):  # rp2's mktime()/gmtime() raise past its ~2037 32-bit epoch range
            return None

    async def _safe_local_time(self) -> "_LocalTime | None":
        try:  # caller-supplied callback, could legitimately misbehave
            return await self._local_time_callback()
        except Exception as e:
            await self.pr.err_s("local_time_callback failed:", e, errno=_ERR_CALLBACK)
            return None

    async def _check_one(self, notif: NotificationSignal) -> bool:
        # Direct read of the producer's own get_data() (SPECIFICATION.md Part C.14) - get_data()
        # never raises, but the specific field can legitimately be None (not yet measured, or the
        # producer's own error streak gave up) - a normal, expected input here, not exceptional.
        value: int | float | None
        source: _ValueSource = notif.value.source  # the annotated local narrows the namedtuple field (C.4.2)
        try:
            data = await source.get_data()
            value = getattr(data, notif.value.field, None)
        except Exception as e:
            await self.pr.err_s(notif.name, "Value read failed:", e, errno=_ERR_SOURCE)
            value = None
        notif.last_value = value
        if value is None:
            notif.triggered = False
            return False
        thresholds = await self.cfgmgr.get_float_values(notif.field_schema)  # works for an "int" schema field too - float(cached_int) never raises
        if thresholds is None:
            await self.pr.err_s(notif.name, "Threshold config read failed!", errno=_ERR_CFG_READ)
            notif.triggered = False
            return False
        threshold = thresholds[0]  # exactly one field - the constructor refuses any other shape
        # float(value): getattr()'s own return is untyped even after the None-check above (the
        # field name is dynamic, not a literal) - narrows to a real numeric comparison the same way
        # every removed value_callback() used to explicitly cast its own return.
        numeric_value = float(value)
        triggered = (numeric_value >= threshold) if notif.above else (numeric_value <= threshold)
        notif.triggered = triggered
        return triggered

    async def _trigger_signal(self, notif: NotificationSignal, flash_bri: int, flash_dur: float) -> None:
        r, g, b = notif.color
        try:  # caller-supplied callback, could legitimately misbehave
            await self._request_signal_cb(r * flash_bri, g * flash_bri, b * flash_bri, flash_dur)
        except Exception as e:
            await self.pr.err_s(notif.name, "request_signal_cb failed:", e, errno=_ERR_CALLBACK)

    async def _store_notif_data(self, *, any_triggered: bool) -> None:
        await self._set_meas_data(NOTIFY(any_triggered, self._now()))

    def start_asy_notify_monitor(self) -> "asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.monitor_loop())

    def start_asy_auto_override(self) -> "asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.auto_led_override())

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_notify_monitor, self.start_asy_auto_override]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return []  # no machine.Timer anywhere in this file (SPECIFICATION.md C.9 shape)

    async def get_data(self) -> NOTIFY:
        # Narrows to this Reader's concrete NOTIFY - see SPECIFICATION.md C.4.2's get_data() convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data, _FIELDS, name=self.name)

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        # self.cfg_schema is the full combined schema (own fields + every kept signal's field),
        # built once at construction, so this covers everything in one call.
        return await self._get_dict_cfg(self.name, self.cfg_schema)

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def get_override_led(self) -> int:
        value = await self.override_secs.get_value()  # never None: never constructed/set with a None sentinel
        return 0 if value is None else value

    async def set_override_led(self, secs: int) -> None:
        await self.override_secs.set_value(secs)  # LockedCounter clamps into [0, _MAX_OVERRIDE_TIME] itself

    async def setup(self) -> None:  # call once, before any task starter runs
        await super().setup()
        await self.pr.setup()  # the refusals below persist through a set-up logger
        while self._pending_wrn:
            msg, wrnno = self._pending_wrn.pop(0)
            await self.pr.wrn_s(msg, wrnno=wrnno)

    async def auto_led_override(self) -> None:
        self._auto_active = True
        while True:
            secs = await self.override_secs.decrement()
            if secs > 0:
                if self._auto_active:
                    self._auto_active = False
                    self.pr.evt("LED Override active.")
            elif not self._auto_active:
                self._auto_active = True
                self.pr.evt("LED Override off.")
            await asyncio.sleep(_LOOP_TICK_S)

    async def monitor_loop(self) -> None:
        await self.pr.setup()  # required for all logged warnings and errors
        # No self._auto_active = True here, unlike __init__/auto_led_override() which own it - this
        # task only reads it. A supervisor-driven restart of this task used to reset it, clobbering
        # an override set mid-run: two independently-restartable tasks over one unlocked flag.
        while True:
            t0 = time.ticks_ms()
            cfg_int = await self.cfgmgr.get_int_values(_VAL_INT_FIELDS)
            cfg_float = await self.cfgmgr.get_float_values(_VAL_FLOAT_FIELDS)
            cfg_bool = await self.cfgmgr.get_bool_values(_VAL_BOOL_FIELDS)
            if (
                cfg_int is None
                or cfg_float is None
                or cfg_bool is None
                or len(cfg_int) != len(_VAL_INT_FIELDS)
                or len(cfg_float) != len(_VAL_FLOAT_FIELDS)
                or len(cfg_bool) != 1
            ):
                interv = _CFG_FAIL_INTERVAL_S
                # Persisted every failing cycle; a repeat spends no slot (the newest-entry rule).
                await self.pr.wrn_s("Error reading own configuration!", wrnno=_WRN_CFG_READ)
            else:
                on_h, on_m, off_h, off_m, flash_bri = cfg_int
                interv, flash_dur = cfg_float
                auto_on = cfg_bool[0]
                any_triggered = False
                if auto_on and self._auto_active:
                    cur_time = await self._safe_local_time()
                    if cur_time is not None:  # no NTP sync, missing config, or a raising callback
                        on_min_of_day = (on_h * 60) + on_m
                        off_min_of_day = (off_h * 60) + off_m
                        cur_min_of_day = (cur_time.hour * 60) + cur_time.minute
                        if on_min_of_day <= cur_min_of_day <= off_min_of_day:
                            for notif in self._registered:
                                if await self._check_one(notif):
                                    any_triggered = True
                                    await self._trigger_signal(notif, flash_bri, flash_dur)
                                    await asyncio.sleep(2 * flash_dur)
                await self._store_notif_data(any_triggered=any_triggered)
            await asyncio.sleep(self._next_sleep_secs(interv, t0))
