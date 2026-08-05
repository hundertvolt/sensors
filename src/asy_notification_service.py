"""Generic threshold-triggered LED notification signalling: `NotificationSignal` (a plain,
dependency-free per-condition data holder) and `NotificationCoordinator` (owns everything shared -
sleep-window/interval/`AutoOn`/global flash brightness+duration, the override/pause countdown, one
combined `ConfigManager`, one combined `PrintLogHistory`(Store)). Promoted from
improved-quality/neopixel_signal.py's `airquality_auto_signal()`/`auto_led_override()` (see
CLAUDE.md/BACKLOG.md); drives a real LED through `request_signal_cb` (matches
asy_neopixel_driver.py's `request_signal()` signature), kept fully decoupled from any concrete LED
implementation.

Staged registration, deferred construction: construct every `NotificationSignal`, call
`register()` for each - in the order checks should run, since that order becomes the poll loop's
own deterministic check order - then call `finalize()` exactly once, before any task starter runs.
`finalize()` is the single point `self.pr`/`self.cfgmgr` come into existence, built from this
class's own static schema plus every registered signal's one field. This is safe specifically
because the number and order of registered signals is guaranteed constant once `finalize()` has
run (a one-time boot handshake, not a runtime-mutable registry) - achieved with zero changes to
`ConfigManager`/`PrintLogHistory`(Store)/`base_classes.py` themselves.

`register()`/`finalize()` are both plain sync calls (matching every other module's plain sync
`__init__`-time wiring), but a rejected registration still needs `self.pr.wrn_s()` - async, and
`self.pr` may not exist yet pre-`finalize()`. Resolved by buffering every rejection's message and
draining it from `monitor_loop()` at the top of every cycle (in addition to right after
`self.pr.setup()`), rather than firing an async task from sync code with no guaranteed running
loop - a real rejection is still always logged, just on the next cycle boundary rather than
instantly.

`NotificationSignal.color` is a per-channel weight (0 or 1 per channel, e.g. `(1, 0, 0)` for a
pure-red condition), not an absolute color - it is scaled by the coordinator's own shared `FlashBri`
at trigger time, so one global brightness setting really does apply to every registered condition
(matches today's CO2/VOC/Humidity red/green/blue scheme exactly when each uses a single-channel
weight).
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
# change). Ranges/defaults mirror sensortask-wozi.py's own legacy update_valid_json() calls.
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
# The coordinator's own static schema fragment - stays const()-folded. The full combined schema
# built in finalize() cannot be (it's assembled at runtime from however many signals registered) -
# see finalize()'s own comment.
_VAL_OWN_SCHEMA = _VAL_INT_FIELDS + _VAL_FLOAT_FIELDS + _VAL_BOOL_FIELDS

# Minimal but real measurement snapshot (DRIVER_SPEC.md's get_data()/get_dict_data() shape, same as
# every other Reader) - whether anything was triggered as of the most recently completed poll cycle.
NotifData = namedtuple("NotifData", ("Triggered", "TS"))


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
        self.color = color
        self.above = above
        # Only ever touched by the coordinator's single poll-loop task - no lock needed (see
        # src/README.md section 4's "don't add locking just in case").
        self.last_value: int | float | None = None
        self.triggered = False


class NotificationCoordinator(SensorReaderConfig):
    def __init__(
        self,
        request_signal_cb: "Callable[[int, int, int, float], Coroutine[Any, Any, bool]]",
        local_time_callback: "Callable[[], Coroutine[Any, Any, Any]]",
        max_i2c_err: int = 5,
        cfg_path: str = "",
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        # Deferred construction (see module docstring): super().__init__() only runs inside
        # finalize() - self.pr/self.cfgmgr/self.cfg_schema don't exist until then.
        self._request_signal_cb = request_signal_cb
        self._local_time_callback = local_time_callback
        self._max_i2c_err = max_i2c_err
        self._cfg_path = cfg_path
        self._fram = fram
        self._history_length = history_length
        self._debug = debug
        self._registered: list[NotificationSignal] = []
        self._finalized = False
        # Buffered rejection messages - see module docstring on why register()/finalize() can't
        # just call self.pr.wrn_s() directly from their own sync bodies.
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
            await self.pr.wrn_s(_NAME, msg, wrnno=wrnno)

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
            await self.pr.err_s(_NAME, "local_time_callback failed:", e, errno=3)
            return None

    async def _check_one(self, notif: NotificationSignal) -> bool:
        try:  # caller-supplied callback, could legitimately misbehave
            value = await notif.get_value()
        except Exception as e:
            await self.pr.err_s(_NAME, notif.name, "Value callback failed:", e, errno=1)
            value = None
        notif.last_value = value
        if value is None:
            notif.triggered = False
            return False
        key = name_cfg(notif.field_schema)
        threshold_dict = await self.cfgmgr.get_dict([key])
        if threshold_dict is None or key not in threshold_dict:
            await self.pr.err_s(_NAME, notif.name, "Threshold config read failed!", errno=2)
            notif.triggered = False
            return False
        threshold = threshold_dict[key]
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            notif.triggered = False
            return False
        # NaN/inf degrade cleanly through these comparisons already (both sides of a NaN
        # comparison are always False - see math_helpers.py's own precedent) - no extra guard needed.
        triggered = (value >= threshold) if notif.above else (value <= threshold)
        notif.triggered = triggered
        return triggered

    async def _trigger_signal(self, notif: NotificationSignal, flash_bri: int, flash_dur: float) -> None:
        r, g, b = notif.color
        try:  # caller-supplied callback, could legitimately misbehave
            await self._request_signal_cb(r * flash_bri, g * flash_bri, b * flash_bri, flash_dur)
        except Exception as e:
            await self.pr.err_s(_NAME, notif.name, "request_signal_cb failed:", e, errno=4)

    async def _store_notif_data(self, any_triggered: bool) -> None:
        await self._set_meas_data(NotifData(any_triggered, self._now()))

    def start_asy_notify_monitor(self) -> "asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.monitor_loop())

    def start_asy_auto_override(self) -> "asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.auto_led_override())

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_notify_monitor, self.start_asy_auto_override]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return []  # no machine.Timer anywhere in this file (DRIVER_SPEC.md section 9 shape)

    async def get_data(self) -> NotifData:
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data)

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        # self.cfg_schema is already the full combined schema (own fields + every registered
        # signal's field) - built once, inside finalize() - so this covers everything in one call.
        return await self._get_dict_cfg(_NAME, self.cfg_schema)

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        return await self.pr.get_log(_NAME)

    async def get_override_led(self) -> int:
        value = await self.override_secs.get_value()  # never None: never constructed/set with a None sentinel
        return 0 if value is None else value

    def register(self, notif: NotificationSignal) -> None:
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

    def finalize(self) -> None:
        if self._finalized:
            self._reject_registration("(coordinator)", "finalize() called again, ignoring", 4)
            return
        super().__init__(
            NotifData(False, None),
            self._max_i2c_err,
            _NAME,
            self._combined_schema(),
            cfg_path=self._cfg_path,
            fram=self._fram,
            history_length=self._history_length,
            debug=self._debug,
        )
        self._finalized = True

    async def set_override_led(self, secs: int) -> None:
        await self.override_secs.set_value(secs)  # LockedCounter clamps into [0, _MAX_OVERRIDE_TIME] itself

    async def auto_led_override(self) -> None:
        self._auto_active = True
        while True:
            secs = await self.override_secs.decrement()
            if secs > 0:
                self._auto_active = False
            else:
                self._auto_active = True
            await asyncio.sleep(1)

    async def monitor_loop(self) -> None:
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
                interv = 600.0
                await self.pr.wrn_s(_NAME, "Error reading own configuration!", wrnno=5)
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
                await self._store_notif_data(any_triggered)
            await asyncio.sleep(self._next_sleep_secs(interv, t0))
