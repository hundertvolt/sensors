"""Generic threshold-triggered LED notification signalling: `NotificationSignal` (per-condition data
holder) and `NotificationCoordinator` (shared sleep-window/interval/`AutoOn`/flash brightness+
duration, one combined `ConfigManager`/`PrintLogHistory`(Store)). Promoted from
improved-quality/neopixel_signal.py's `airquality_auto_signal()`/`auto_led_override()` (see
CLAUDE.md/BACKLOG.md); drives an LED through `request_signal_cb`, decoupled from any concrete LED
implementation. Registration is staged: `register()` each signal, then `finalize()` once - see
their own comments below.
"""

import asyncio
import time
from collections import namedtuple

from micropython import const

from base_classes import LockedCounter, SensorReaderConfig
from config_manager import make_dict, name_cfg, schema_names

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any

    from asy_fram_manager import AsyFramManager
    from config_manager import ConfigSchema

_MAX_OVERRIDE_TIME = const(3600)
_NAME = const("NOTIFY")

# Own schema, "Led" prefix dropped (matches asy_wifi_service.py/asy_sgp40_driver.py's own field
# naming convention - see CLAUDE.md's "Current architecture" note on this deliberate wire-format
# change). Ranges/defaults mirror the legacy REST handler's own already-validated bounds.
_VAL_ON_H = const((("OnH", "int", 10, 0, 23, None),))
_VAL_ON_M = const((("OnM", "int", 0, 0, 59, None),))
_VAL_OFF_H = const((("OffH", "int", 18, 0, 23, None),))
_VAL_OFF_M = const((("OffM", "int", 0, 0, 59, None),))
_VAL_FLASH_BRI = const((("FlashBri", "int", 200, 1, 255, None),))
_VAL_INTERV = const((("Interv", "float", 300.0, 60.0, 3600.0, None),))
_VAL_FLASH_DUR = const((("FlashDur", "float", 2.0, 0.5, 10.0, None),))
_VAL_AUTO_ON = const((("AutoOn", "bool", True, None, None, None),))

_VAL_INT_FIELDS = _VAL_ON_H + _VAL_ON_M + _VAL_OFF_H + _VAL_OFF_M + _VAL_FLASH_BRI
_VAL_FLOAT_FIELDS = _VAL_INTERV + _VAL_FLASH_DUR
_VAL_BOOL_FIELDS = _VAL_AUTO_ON
# Own static schema fragment - stays const()-folded, unlike the full combined schema finalize()
# assembles at runtime from however many signals registered.
_VAL_OWN_SCHEMA = _VAL_INT_FIELDS + _VAL_FLOAT_FIELDS + _VAL_BOOL_FIELDS

# Minimal but real measurement snapshot (SPECIFICATION.md C.4.2's get_data()/get_dict_data() shape, same as
# every other Reader) - whether anything was triggered as of the most recently completed poll cycle.
NOTIFY = namedtuple("NOTIFY", ("Triggered", "TS"))


class NotificationSignal:
    def __init__(
        self,
        name: str,
        get_value: "Callable[[], Coroutine[Any, Any, int | float | None]]",
        field_schema: "ConfigSchema",
        color: "tuple[int, int, int]",
        above: bool = True,
    ) -> None:
        self.name = name
        self.get_value = get_value
        self.field_schema = field_schema
        self.color = color  # per-channel weight (0/1), scaled by FlashBri at trigger time
        self.above = above
        # Only ever touched by the coordinator's single poll-loop task - no lock needed.
        self.last_value: int | float | None = None
        self.triggered = False


class NotificationCoordinator(SensorReaderConfig):
    def __init__(
        self,
        request_signal_cb: "Callable[[int, int, int, float], Coroutine[Any, Any, bool]]",
        local_time_callback: "Callable[[], Coroutine[Any, Any, Any]]",
        max_module_error: int = 5,
        cfg_path: str = "",
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        # Deferred: super().__init__() only runs inside finalize(), once every signal is
        # registered - self.pr/self.cfgmgr/self.cfg_schema don't exist until then.
        self._request_signal_cb = request_signal_cb
        self._local_time_callback = local_time_callback
        self._max_module_error = max_module_error
        self._cfg_path = cfg_path
        self._fram = fram
        self._history_length = history_length
        self._debug = debug
        self._registered: list[NotificationSignal] = []
        self._finalized = False
        # Buffered: register()/finalize() are sync and self.pr may not exist yet, so rejections
        # drain via monitor_loop() instead of calling the async self.pr.wrn_s() directly.
        self._pending_wrn: list[tuple[str, int]] = []
        self.override_secs = LockedCounter(max_val=_MAX_OVERRIDE_TIME)
        self._auto_active = True

    def _combined_schema(self) -> "ConfigSchema":
        combined: ConfigSchema = _VAL_OWN_SCHEMA
        for notif in self._registered:
            combined = combined + notif.field_schema
        return combined

    def _reject_registration(self, name: str, reason: str, wrnno: int) -> None:
        self._pending_wrn.append((reason + ": " + name, wrnno))

    async def _flush_pending_registration_warnings(self) -> None:
        while self._pending_wrn:
            msg, wrnno = self._pending_wrn.pop(0)
            await self.pr.wrn_s(msg, wrnno=wrnno)

    def _next_sleep_secs(self, interv: float, t0: "Any") -> float:  # t0: an opaque ticks_ms() value, not a plain int
        # Isolated from monitor_loop() specifically so it's directly unit-testable without needing
        # a real elapsed time close to Interv's own 60.0s schema floor to observe the floor kick in.
        rem_interv = interv - (time.ticks_diff(time.ticks_ms(), t0) * 0.001)  # run duration so far in sec
        return rem_interv if rem_interv >= 0.1 else 0.1

    def _now(self) -> int | None:
        try:
            return time.mktime(time.gmtime())
        except (OverflowError, OSError):  # rp2's mktime()/gmtime() raise past its ~2037 32-bit epoch range
            return None

    async def _safe_local_time(self) -> "Any":
        try:  # caller-supplied callback, could legitimately misbehave
            return await self._local_time_callback()
        except Exception as e:
            await self.pr.err_s("local_time_callback failed:", e, errno=3)
            return None

    async def _check_one(self, notif: NotificationSignal) -> bool:
        try:  # caller-supplied callback, could legitimately misbehave
            value = await notif.get_value()
        except Exception as e:
            await self.pr.err_s(notif.name, "Value callback failed:", e, errno=1)
            value = None
        notif.last_value = value
        if value is None:
            notif.triggered = False
            return False
        thresholds = await self.cfgmgr.get_float_values(notif.field_schema)  # works for an "int" schema field too - float(cached_int) never raises
        if thresholds is None:
            await self.pr.err_s(notif.name, "Threshold config read failed!", errno=2)
            notif.triggered = False
            return False
        threshold = thresholds[0]  # exactly one field - register() rejects any other shape
        triggered = (value >= threshold) if notif.above else (value <= threshold)
        notif.triggered = triggered
        return triggered

    async def _trigger_signal(self, notif: NotificationSignal, flash_bri: int, flash_dur: float) -> None:
        r, g, b = notif.color
        try:  # caller-supplied callback, could legitimately misbehave
            await self._request_signal_cb(r * flash_bri, g * flash_bri, b * flash_bri, flash_dur)
        except Exception as e:
            await self.pr.err_s(notif.name, "request_signal_cb failed:", e, errno=4)

    async def _store_notif_data(self, any_triggered: bool) -> None:
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
        if not self._finalized:  # finalize() hasn't run yet - self._datastruct doesn't exist; caller-ordering
            return NOTIFY(False, None)  # bug, defense-in-depth only
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data)

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        if not self._finalized:  # self.cfg_schema doesn't exist yet - same caller-ordering guard as get_data()
            return {_NAME: {}}
        # self.cfg_schema is already the full combined schema (own fields + every registered
        # signal's field) - built once, inside finalize() - so this covers everything in one call.
        return await self._get_dict_cfg(_NAME, self.cfg_schema)

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        if not self._finalized:  # self.pr doesn't exist yet - same caller-ordering guard as get_data()
            return {_NAME: {"ErrCount": 0, "ErrNum": [], "ErrType": []}}
        return await self.pr.get_log()

    async def get_override_led(self) -> int:
        value = await self.override_secs.get_value()  # never None: never constructed/set with a None sentinel
        return 0 if value is None else value

    async def set_override_led(self, secs: int) -> None:
        await self.override_secs.set_value(secs)  # LockedCounter clamps into [0, _MAX_OVERRIDE_TIME] itself

    def register(self, notif: NotificationSignal) -> None:  # call once per signal, in check order, before finalize()
        if self._finalized:
            self._reject_registration(notif.name, "register() called after finalize(), ignoring", 3)
            return
        key = name_cfg(notif.field_schema)
        if key == "":
            self._reject_registration(notif.name, "field_schema must have exactly one field, ignoring", 2)
            return
        existing = set(schema_names(_VAL_OWN_SCHEMA))
        existing.update(name_cfg(n.field_schema) for n in self._registered)
        if key in existing:
            self._reject_registration(notif.name, "field name '" + key + "' collides, ignoring", 1)
            return
        self._registered.append(notif)

    def finalize(self) -> None:  # call exactly once, after all register() calls, before any task starter runs
        if self._finalized:
            self._reject_registration("(coordinator)", "finalize() called again, ignoring", 4)
            return
        super().__init__(
            NOTIFY(False, None),
            self._max_module_error,
            _NAME,
            self._combined_schema(),
            cfg_path=self._cfg_path,
            fram=self._fram,
            history_length=self._history_length,
            debug=self._debug,
        )
        self._finalized = True

    async def setup(self) -> None:  # call after finalize(), before any task starter runs
        if not self._finalized:  # self.cfgmgr doesn't exist yet - caller-ordering bug, defense-in-depth only
            return
        await super().setup()

    async def reset_error_counter(self) -> None:
        if not self._finalized:  # self.pr doesn't exist yet - same caller-ordering guard as get_data()
            return
        await super().reset_error_counter()

    async def auto_led_override(self) -> None:
        if not self._finalized:  # self.pr doesn't exist yet - same caller-ordering guard as monitor_loop()
            return
        self._auto_active = True
        while True:
            secs = await self.override_secs.decrement()
            if secs > 0:
                if self._auto_active:
                    self._auto_active = False
                    self.pr.evt("LED Override active.")
            else:
                if not self._auto_active:
                    self._auto_active = True
                    self.pr.evt("LED Override off.")
            await asyncio.sleep(1)

    async def monitor_loop(self) -> None:
        if not self._finalized:  # self.pr/self.cfgmgr don't exist yet - caller-ordering bug, defense-in-depth only
            return
        await self.pr.setup()  # required for all logged warnings and errors
        self._err_cnt_internal = 0
        self._auto_active = True
        while True:
            t0 = time.ticks_ms()
            await self._flush_pending_registration_warnings()
            cfg_int = await self.cfgmgr.get_int_values(_VAL_INT_FIELDS)
            cfg_float = await self.cfgmgr.get_float_values(_VAL_FLOAT_FIELDS)
            cfg_bool = await self.cfgmgr.get_bool_values(_VAL_BOOL_FIELDS)
            if (
                cfg_int is None
                or cfg_float is None
                or cfg_bool is None
                or len(cfg_int) != 5
                or len(cfg_float) != 2
                or len(cfg_bool) != 1
            ):
                cfg_read_failed = True
                interv = 600.0
                await self.pr.wrn_s("Error reading own configuration!", wrnno=5)
            else:
                cfg_read_failed = False
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
                await self._store_notif_data(any_triggered)
            # consecutive-failure-streak give-up, matching every other Reader's own read_loop() shape -
            # max_module_error is otherwise accepted and stored but never actually enforced.
            if not await self._error_check((None,), condition=cfg_read_failed):
                return  # too many consecutive own-config-read failures - let the task supervisor restart us
            await asyncio.sleep(self._next_sleep_secs(interv, t0))
