"""Shared base classes and primitives: the session lock (Lockable, DeviceSession), region buffers (RegionBuffer),
an hourly window counter (HourlyWindowCounter: no
method awaits, so no lock), elapsed seconds (TickSeconds), a periodic deadline wait (TickGrid) and the UTC timestamp.

The sensor-driver base (SensorReader, SensorReaderConfig) with error bookkeeping and optional JSON config storage.

Every method returns a well-defined value, never raises.
"""
# __init__ never calls self.pr.setup() (sync vs. async): setup() does it first (SensorReader), then the
# store's (SensorReaderConfig) - both inside the one-time boot batch, never lazily in a task (Part A.7).

import asyncio
import time
from collections import namedtuple

from micropython import const

from asy_config_manager import FAILED, UNCHANGED, VALID, ConfigManager, check_cfg_get_default, config_filename, instance_name, schema_dict, schema_names, type_or_range_error
from asy_print_log import DEFAULT_LOG, LogConfig, make_logger, report_if_fatal

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping
    from typing import Literal, NamedTuple, Protocol, TypeVar

    from _mpy_shed.time_mp import _TicksMs
    from typing_extensions import Self

    from asy_config_manager import CfgValue, ConfigSchema, FieldSchema, WriteValidity
    from asy_i2c_driver import I2C, I2CDevice
    from asy_print_log import ErrorLog, PrintLog, PrintLogHistory

    MeasDataType = TypeVar("MeasDataType", bound=tuple[int | float | None, ...])

    # Shared typing aliases (SPECIFICATION.md Part C.10), declared once here and imported under
    # TYPE_CHECKING by their users: starter lists, REST payloads and the fan-in shapes.
    TaskStarter = Callable[[], asyncio.Task[None]]
    TimerStarter = Callable[[], None]
    JsonValue = int | float | str | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
    JsonDict = dict[str, JsonValue]
    JsonMapping = Mapping[str, JsonValue]  # a REST body as a module receives it: read, never mutated
    PushFct = Callable[[CfgValue], Awaitable[bool]]  # a field's live push: True when the value reached the module
    NtpSyncFct = Callable[[], Awaitable[bool]]  # whether the clock is NTP-synced
    AsyncCallback = Callable[[], Awaitable[None]]
    SetupFct = Callable[[], Awaitable[None]]  # one boot setup

    class ErrorSource(Protocol):
        # One /status error-log entry: what every get_error_sources() list holds (Part C.14).
        name: str

        async def get_error_counter(self) -> "ErrorLog": ...
        async def reset_error_counter(self) -> bool: ...

    class LoggerOwner(Protocol):
        # A module whose loggers join the system-wide debug-level registry (Part C.14).
        def get_loggers(self) -> "list[PrintLogHistory]": ...

    class _DataProducer(Protocol):
        # Any module exposing the get_data() -> NamedTuple contract every driver has (C.4.2).
        async def get_data(self) -> object: ...

    # a producer plus the field to read off its get_data() (SPECIFICATION.md C.14)
    class ValueRef(NamedTuple):
        source: _DataProducer
        field: str

else:
    ValueRef = namedtuple("ValueRef", ("source", "field"))

# 2**30 - 1: rp2's largest small int (object repr A), 34 years in seconds; no counter or cap may exceed it
COUNTER_CAP = const(0x3FFFFFFF)
# The degraded-source marker's word: a source that could not read its values answers {"error": UNAVAILABLE} (Part C.6).
UNAVAILABLE = const("unavailable")
# HourlyWindowCounter's window: 24 bins of one hour each
_WINDOW_HOURS = const(24)
_HOUR_S = const(3600)

# Codes from the global catalog (buildgen/error_catalog.json): the base band every SensorReader inherits.
_ERR_STREAK = const(1)
_ERR_GIVE_UP = const(2)
_ERR_CFG_GET_RAISED = const(3)
_ERR_CFG_CALLBACK_RAISED = const(4)
_ERR_CFG_SET_RAISED = const(5)
_ERR_PUSH_RAISED = const(6)
_ERR_CFG_SNAPSHOT_RAISED = const(7)
_ERR_RECOVERY_READ_RAISED = const(8)
_ERR_RECOVERY_WRITE_RAISED = const(9)
_ERR_CALLBACK = const(14)
_WRN_CALLBACK_KEYS = const(1)
_WRN_CFG_KEYS = const(2)
_WRN_DEVICE_RECOVERY = const(14)
_WRN_BUS_RECOVERY = const(15)

# Recovery ladder: participant at the 2nd failed cycle, bus clear at the 3rd, controller at the 4th, task end
# past max_module_error (owner, 2026-09-30: smallest blast radius first; thresholds agent, 2026-09-30).
# @tunable module.recover_device_at = 2
_RECOVER_DEVICE_AT = const(2)
# @tunable module.recover_bus_at = 3
_RECOVER_BUS_AT = const(3)
# @tunable module.recover_controller_at = 4
_RECOVER_CONTROLLER_AT = const(4)
_RUNG_DEVICE = const(1)
_RUNG_BUS = const(2)
_RUNG_CONTROLLER = const(4)


class Lockable:
    def __init__(self, session_lock: asyncio.Lock | None = None) -> None:
        self.session_lock = asyncio.Lock() if session_lock is None else session_lock

    async def __aenter__(self) -> "Self":
        await self.session_lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,  # `object`, not TracebackType: the precise name only exists under TYPE_CHECKING
    ) -> "Literal[False]":  # Literal, not bool: this CM never suppresses, and saying so lets mypy
        # see the code after an `async with` as unreachable instead of demanding a redundant
        # trailing return on every caller (SPECIFICATION.md Part D.7).
        try:
            self.session_lock.release()
        except RuntimeError as e:  # already released somehow; a C-stack overflow on the call is recorded for the reboot
            report_if_fatal(e)
        return False


class DeviceSession(Lockable):
    # One device's session lock plus its bus device (SPECIFICATION.md C.2/G.2); every sensor driver's chip sits on
    # I2C, so the device is typed as one - an SPI chip, when one exists, gets its own typed session.
    def __init__(self, bus_device: "I2CDevice") -> None:
        super().__init__()
        self.i2c_device = bus_device


class RegionBuffer:
    def __init__(self, size: int, data_start: int = 0, data_length: int | None = None, logger: "PrintLog | None" = None) -> None:
        self.data_start = data_start
        data_length = size - data_start if data_length is None else data_length
        self.data_end = data_start + data_length
        # A negative size/data_start/data_length is a caller mistake, not a hardware fault - guard
        # it the same way as an oversized region (buf=None) instead of letting bytearray(negative)
        # raise MemoryError or silently wrapping around to a wrong-offset slice.
        if size < 0 or data_start < 0 or data_length < 0 or self.data_end > size:
            self._buf = None
        else:
            # A valid size can still exhaust heap (real FRAM chunk buffers allocate fresh on every
            # read/write over an indefinite uptime) or overflow bytearray's internal size conversion
            # at 2**63 - both degrade the same way as the guards above, not a caller mistake either.
            try:
                self._buf = bytearray(size)
            except (MemoryError, OverflowError) as e:
                if logger is not None:  # its builder's: silent without one
                    logger.err("RegionBuffer: buffer allocation failed:", e)
                self._buf = None

    def get_buf(self) -> bytearray | None:
        return self._buf

    def get_data_buf(self) -> memoryview | None:
        if self._buf is None:
            return None
        return memoryview(self._buf)[self.data_start : self.data_end]


class HourlyWindowCounter:
    # Events in the last 24 hours at hourly resolution: 24 fixed bins advanced lazily from the uptime
    # seconds (monotonic, untouched by NTP steps), so no event, read or hour change allocates; an event
    # leaves the window 23-24 hours after it happened (owner, 2026-10-01).
    def __init__(self) -> None:
        self._bins = [0] * _WINDOW_HOURS  # the one allocation, at construction
        self._hour = 0  # the uptime hour the bins were last advanced to

    # Plain methods: nothing here awaits, so no other task can interleave and no lock is needed.
    def _advance(self, now_s: int) -> None:
        hour = now_s // _HOUR_S
        gap = hour - self._hour
        if gap <= 0:
            return
        if gap >= _WINDOW_HOURS:
            for i in range(_WINDOW_HOURS):
                self._bins[i] = 0
        else:
            for h in range(self._hour + 1, hour + 1):
                self._bins[h % _WINDOW_HOURS] = 0
        self._hour = hour

    def add(self, now_s: int) -> None:
        self._advance(now_s)
        i = self._hour % _WINDOW_HOURS
        if self._bins[i] < COUNTER_CAP:
            self._bins[i] += 1

    def reset(self) -> None:
        for i in range(_WINDOW_HOURS):
            self._bins[i] = 0

    def total(self, now_s: int) -> int:
        self._advance(now_s)
        s = 0
        for b in self._bins:
            if b >= COUNTER_CAP - s:  # checked before the step: no intermediate leaves the small-int range
                return COUNTER_CAP
            s += b
        return s


class TickSeconds:
    # Elapsed whole seconds from ticks_ms() deltas plus a millisecond remainder, up or down, saturating at
    # COUNTER_CAP; a caller reads it at least once per 2**29 ms (6.2 days, ticks_diff()'s horizon); a
    # negative delta (never on target within that horizon) is ignored. No method awaits, so no lock.
    def __init__(self, *, count_down: bool = False) -> None:
        self._down = count_down
        self._value = 0
        self._rem_ms = 0
        self._last = time.ticks_ms()

    def read(self) -> int:
        now = time.ticks_ms()
        delta = time.ticks_diff(now, self._last)
        self._last = now
        if delta > 0:
            ms = self._rem_ms + delta
            secs = ms // 1000
            self._rem_ms = ms - secs * 1000
            if self._down:
                self._value = self._value - secs if self._value > secs else 0
            else:
                self._value = self._value + secs if self._value < COUNTER_CAP - secs else COUNTER_CAP
        return self._value

    def restart(self, value_s: int = 0) -> None:
        self._value = min(max(value_s, 0), COUNTER_CAP)
        self._rem_ms = 0
        self._last = time.ticks_ms()


_utc_valid = False  # one writer (the NTP client's sync success), no await between read and use


def set_utc_valid() -> None:
    # The NTP client calls it once it has set the RTC; the clock then stays valid for the boot (Part G.2).
    global _utc_valid
    _utc_valid = True


class TickGrid:
    # Wakes at start + k * period_ms on ticks_ms(), start the first wait(): a late wake shortens the next wait, and one
    # later than a whole period runs once and resumes on the grid, so nothing accumulates or drifts.
    def __init__(self, period_ms: int) -> None:
        self._period = period_ms
        self._next: _TicksMs | None = None

    async def wait(self) -> None:
        now = time.ticks_ms()
        due = time.ticks_add(now if self._next is None else self._next, self._period)
        late = time.ticks_diff(now, due)
        if late > 0:
            due = time.ticks_add(due, late - late % self._period)
        self._next = due
        await asyncio.sleep_ms(-late if late < 0 else 0)


class SensorReader:
    # Set by a reader that divides the 1 s base tick (BMP3XX, ISL29125); read by _trigger_loop() only.
    _base_trigger_event: asyncio.ThreadSafeFlag
    _read_event: asyncio.ThreadSafeFlag
    _trigger_counter: int
    _trigger_period: int
    start_timer: "TimerStarter"

    def __init__(
        self,
        init_data: "NamedTuple",
        name: str,
        # @tunable module.max_error = 5
        max_module_error: int = 5,
        name_ext: str = "",
        log: LogConfig = DEFAULT_LOG,
        logger: "PrintLogHistory | None" = None,
    ) -> None:
        # name_ext="" (every module today) reproduces `name` unchanged - see instance_name()'s own comment and SPECIFICATION.md
        # Part C.14. Resolved once here: self.pr.name agrees with it unless logger= shares a sibling's logger.
        resolved_name = instance_name(name, name_ext)
        self.pr = logger if logger is not None else make_logger(log, resolved_name)  # reach-through: reuse a directly-bound sibling object's own logger
        self.name = resolved_name  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (sensors=/error_sources=/settings=).
        self._datastruct = init_data  # the last sample: read and replaced whole with no await, so it needs no lock
        self._max_module_error = max_module_error
        self._err_cnt_internal = 0
        self._set_lock = asyncio.Lock()  # serialises one module's config PUT and GET (Part C.5.2)
        # Per-field live-push callbacks: a subclass registers {field_name: async_push_fn} entries
        # after super().__init__(); a field with no entry is persist-only (see SPECIFICATION.md C.5.2).
        self._push_callbacks: dict[str, PushFct] = {}
        # Per-field live read-back for _recover_failed_push's fallback chain (optional, unlike
        # _push_callbacks); a field with no entry skips to the next rung (see SPECIFICATION.md C.5.2).
        self._get_callbacks: dict[str, Callable[[], Awaitable[CfgValue]]] = {}
        self._rungs = 0  # the _RUNG_* bits this failure episode already ran
        self._bus_mark = 0  # _recovery_bus.recoveries when this episode began
        self._rebuild_mark = 0  # _recovery_bus.rebuilds when this episode began
        self._recovery_bus: I2C | None = None  # set by a driver whose chip sits on I2C

    async def _get_dict_cfg(
        self,
        name: str,
        cfg_vals: "ConfigSchema",
        callback: "Callable[[], Awaitable[dict[str, CfgValue] | None]] | None" = None,
    ) -> dict[str, dict[str, int | float | str | bool | None]]:
        # Under the PUT's lock (Part C.5.2), so a GET reads a module before or after a PUT, never between. A failed
        # read goes out as the {"error": "unavailable"} marker in place of the field map, never as nulls
        # a reader would take for unset values (the /status sources' shape).
        async with self._set_lock:
            cfg = schema_names(cfg_vals)
            values: dict[str, int | float | str | bool | None] = dict.fromkeys(cfg)
            try:  # _get_mgr_cfg is an overridable extension point - the call itself, not just its result, could misbehave
                sensor_conf = await self._get_mgr_cfg(cfg)
                if sensor_conf is not None:
                    if not all(k in values for k in sensor_conf):
                        self.pr.wrn_s("Warning: Sensor config manager adds unknown keys to config dict!", wrnno=_WRN_CFG_KEYS)
                    values.update(sensor_conf)
            except Exception as e:  # subclass override could legitimately misbehave; not statically ruled out
                self.pr.err_s("Error updating config dict:", e, errno=_ERR_CFG_GET_RAISED)
                return {name: {"error": UNAVAILABLE}}
            if sensor_conf is None:
                return {name: {"error": UNAVAILABLE}}  # the store persisted its own entry; the callback is not read

            if callback is not None:
                try:
                    sensor_callback = await callback()
                    if sensor_callback is None:
                        return {name: {"error": UNAVAILABLE}}  # the driver persisted its own entry
                    if not all(k in values for k in sensor_callback):
                        self.pr.wrn_s("Warning: Sensor callback adds unknown keys to config dict!", wrnno=_WRN_CALLBACK_KEYS)
                    values.update(sensor_callback)
                except Exception as e:  # callback is caller-supplied; its runtime behavior isn't statically known
                    self.pr.err_s("Error reading config from sensor:", e, errno=_ERR_CFG_CALLBACK_RAISED)
                    return {name: {"error": UNAVAILABLE}}

            return {name: values}

    async def _get_meas_data(self) -> "NamedTuple":
        return self._datastruct

    async def _get_mgr_cfg(self, _cfg: list[str]) -> dict[str, int | float | str | bool | None] | None:
        return {}

    async def _set_dict_cfg(self, data: "JsonMapping", cfg_vals: "ConfigSchema") -> "WriteValidity":
        # Setter mirror of _get_dict_cfg (Part C.5.2): stage first, push only the changed fields, then commit the
        # staged write, so the flash write follows the pushes. One PUT per module at a time: a failed push's
        # recovery can never overwrite a value a later PUT stored meanwhile.
        async with self._set_lock:
            if self._writes_closed():
                # Closed by an accepted system command: nothing writes, flash or chip, until the reset (owner, 2026-10-02).
                return dict.fromkeys(data, FAILED)
            fields = schema_dict(cfg_vals)
            # The pre-write snapshot covers only what _recover_failed_push can use: a persisted key with a
            # push callback, so a store without push callbacks (SCD30's chip) pays no second read.
            persisted_keys = [
                key for key, field in fields.items()
                if key in data and key in self._push_callbacks and check_cfg_get_default(field)[0]
            ]
            try:  # _get_mgr_cfg is an overridable extension point, same defense as _get_dict_cfg's own use of it
                old_values = await self._get_mgr_cfg(persisted_keys) if persisted_keys else {}
            except Exception as e:
                self.pr.err_s("Error reading previous config for fallback:", e, errno=_ERR_CFG_SNAPSHOT_RAISED)
                old_values = None
            if old_values is None:
                old_values = {}

            try:  # _set_mgr_cfg is an overridable extension point - the call itself could raise on a subclass
                # override (mirrors _get_dict_cfg's own _get_mgr_cfg handling); its return shape is mypy's (D.2).
                persisted, results = await self._set_mgr_cfg(data, cfg_vals)
            except Exception as e:
                self.pr.err_s("Error writing config dict:", e, errno=_ERR_CFG_SET_RAISED)
                persisted, results = False, {}

            if not persisted:
                # Whole-operation failure (invalid ConfigManager, or an internal write error) - nothing
                # was stored, so every requested key is "Failed", not "Invalid" (which would misleadingly
                # suggest the values themselves were the problem) and nothing is pushed live either.
                return dict.fromkeys(data, FAILED)

            try:
                for key in data:
                    # Defense-in-depth: a misbehaving _set_mgr_cfg override could report persisted=True but
                    # omit a key from results (the real ConfigManager-backed path never does).
                    results.setdefault(key, FAILED)
                for key, value in data.items():
                    if results.get(key) != VALID:
                        continue  # only an actual, successfully-persisted change gets pushed live
                    callback = self._push_callbacks.get(key)
                    field = fields.get(key)
                    if callback is None or field is None:
                        continue  # persist-only field, nothing to push
                    # Push the coerced value that was actually persisted, not the caller's raw
                    # pre-coercion one - see SPECIFICATION.md Part C.5.2's push-callback contract.
                    _is_error, push_value = type_or_range_error(value, field)
                    try:
                        pushed = await callback(push_value)
                    except Exception as e:  # callback is caller-supplied; its runtime behavior isn't statically known
                        self.pr.err_s("Error pushing", key, "to sensor:", e, errno=_ERR_PUSH_RAISED)
                        pushed = False
                    if not pushed:
                        results[key] = FAILED
                        await self._recover_failed_push(key, old_values, cfg_vals, fields=fields)
            finally:  # a cancelled PUT still releases its staged write
                self._commit_mgr_cfg()
            return results

    async def _set_meas_data(self, data: "NamedTuple") -> None:
        self._datastruct = data

    async def _set_mgr_cfg(self, _data: "JsonMapping", _cfg_vals: "ConfigSchema") -> "tuple[bool, WriteValidity]":
        # No store: nothing persists, so _set_dict_cfg() answers every requested key "Failed".
        return False, {}

    async def _climb_ladder(self) -> None:
        # One rung per failed cycle, each at most once per episode; the bit is set before the first await.
        n = self._err_cnt_internal
        if n >= _RECOVER_DEVICE_AT and not self._rungs & _RUNG_DEVICE:
            self._rungs |= _RUNG_DEVICE
            try:
                ok = await self._recover_device()
            except Exception as e:  # an overridable extension point, guarded like this file's others
                self.pr.err_s("Device recovery raised:", e, errno=_ERR_CALLBACK)
                return  # a failed rung: its one entry is this error
            if ok is True:  # a failed hook has logged its own error; None means no participant rung
                self.pr.wrn_s("Device recovery after", n, "failed cycles: done", wrnno=_WRN_DEVICE_RECOVERY)
        elif n >= _RECOVER_BUS_AT and not self._rungs & _RUNG_BUS:
            await self._recover_bus(_RUNG_BUS)
        elif n >= _RECOVER_CONTROLLER_AT:
            await self._recover_bus(_RUNG_CONTROLLER)

    def _commit_mgr_cfg(self) -> None:
        # Releases a store's deferred write once the pushes ended; no store, nothing deferred.
        return

    async def _error_check(self, results: "MeasDataType", *, condition: bool = True) -> bool:
        # Shared consecutive-failure-streak counter and recovery ladder - see SPECIFICATION.md Part
        # C.7's _error_check() bullet for the full contract.
        if any(res is None for res in results) and condition:
            if self._err_cnt_internal == 0 and self._recovery_bus is not None:
                self._bus_mark = self._recovery_bus.recoveries  # a new episode: no reader has recovered the bus yet
                self._rebuild_mark = self._recovery_bus.rebuilds
            self._err_cnt_internal += 1
            self.pr.err_s("Error counter increased to", self._err_cnt_internal, errno=_ERR_STREAK)
            if self._err_cnt_internal > self._max_module_error:
                self.pr.err_s("Maximum error count reached!", errno=_ERR_GIVE_UP)
                return False  # breaking the loop triggers a task reset
            await self._climb_ladder()
            return True
        if self._err_cnt_internal > 0:
            self._err_cnt_internal -= 1
            self.pr.err("Error counter back to", self._err_cnt_internal)
        if self._err_cnt_internal == 0:
            self._rungs = 0  # the episode ends: every rung is armed again
        return True

    async def _init_done(self) -> None:
        # A driver's _init_*() calls it after a successful setup: the episode ends, and the bus's
        # construction-time clear is reported once, by the first reader on that bus.
        self._rungs = 0
        bus = self._recovery_bus
        if bus is None:
            return
        status = bus.take_boot_clear_status()
        if status:
            self.pr.wrn_s("I2C bus was held at boot and cleared, status", status, wrnno=_WRN_BUS_RECOVERY)

    async def _recover_bus(self, rung: int) -> None:
        # One bus rung per bus per episode: since its episode began, a reader skips the clear if any rung was entered on
        # its bus and the controller rung only if a rebuild was (it clears too); either way its own rung is spent.
        bus = self._recovery_bus
        if bus is None or self._rungs & rung:
            return
        self._rungs |= rung
        if rung == _RUNG_BUS:
            if bus.recoveries != self._bus_mark:
                return
            status = await bus.clear()
            self.pr.wrn_s("I2C bus cleared, status", status, wrnno=_WRN_BUS_RECOVERY)
        else:
            if bus.rebuilds != self._rebuild_mark:
                return
            status = await bus.recover()
            self.pr.wrn_s("I2C controller re-initialised, status", status, wrnno=_WRN_BUS_RECOVERY)

    async def _recover_device(self) -> bool | None:
        # The participant rung a driver overrides: True done, False failed (it has persisted its own error),
        # never a raise. None: this reader has none, and nothing is logged.
        return None

    async def _recover_failed_push(
        self,
        key: str,
        old_values: "dict[str, CfgValue]",
        cfg_vals: "ConfigSchema",
        *,
        fields: "dict[str, FieldSchema]",
    ) -> None:
        # Recovery chain for a failed live push (see SPECIFICATION.md C.5.2): live read-back via
        # _get_callbacks, else old_values' pre-write snapshot, else the schema default - written
        # back through _set_mgr_cfg only, bypassing _push_callbacks so a failing push can't loop.
        field = fields.get(key)
        if field is None:
            return  # shouldn't happen - key was already validated against cfg_vals above
        use_value, default_val = check_cfg_get_default(field)
        if not use_value:
            return  # command-only/special-alone field (e.g. a trigger) - nothing to persist-correct,
            # mirrors legacy's own cmd_keys exclusion from this exact fallback chain

        recovered: CfgValue = None
        getter = self._get_callbacks.get(key)
        if getter is not None:
            try:
                recovered = await getter()
            except Exception as e:  # getter is caller-supplied; its runtime behavior isn't statically known
                self.pr.err_s("Error reading", key, "back from sensor:", e, errno=_ERR_RECOVERY_READ_RAISED)
                recovered = None
            # A getter reads live, possibly-adversarial hardware state - a value outside this
            # field's own schema is treated the same as a raised exception (fall through), so
            # every rung this cascade accepts is guaranteed schema-valid before it's persisted.
            if recovered is not None:
                is_error, coerced = type_or_range_error(recovered, field)
                recovered = None if is_error else coerced
        if recovered is None:
            recovered = old_values.get(key, default_val)

        try:
            persisted, res = await self._set_mgr_cfg({key: recovered}, cfg_vals)
        except Exception as e:
            self.pr.err_s("Error correcting", key, "after failed push:", e, errno=_ERR_RECOVERY_WRITE_RAISED)
            return
        if not persisted or res.get(key) not in (VALID, UNCHANGED):
            # Console only: the store that refused the recovery persisted its own entry.
            self.pr.err("Recovery of", key, "after a failed push was not stored:", res.get(key))

    async def _republish(self, names: tuple[str, ...], **changes: object) -> None:
        # The last sample again with the named fields changed, with no await between the read and the store, so a
        # concurrent store is never overwritten by a stale copy; names are the namedtuple's fields in order.
        old = self._datastruct
        values = (changes[n] if n in changes else getattr(old, n) for n in names)
        self._datastruct = type(old)(*values)  # type: ignore[arg-type]  # the sample's own namedtuple class, not NamedTuple's factory

    async def _trigger_loop(self) -> None:
        # The shared divider (Part C.9): every n-th base tick sets the read event, n the trigger period.
        self._trigger_counter = 0
        while True:
            await self._base_trigger_event.wait()
            self._trigger_counter += 1
            if self._trigger_counter >= self._trigger_period:
                self._read_event.set()
                self._trigger_counter = 0

    def _writes_closed(self) -> bool:
        # No store: nothing to close, so a PUT is never refused here.
        return False

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []  # none here: a subclass with a machine.Timer lists its starter (SPECIFICATION.md C.9)

    def get_trigger_starters(self) -> "list[TimerStarter]":
        # Read-trigger timer starters the system service staggers (SPECIFICATION.md Part C.9.1); none here.
        return []

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    def get_error_sources(self) -> "list[ErrorSource]":
        # N-to-1 fan-in primitive (Part C.14/G.2): every module the generated
        # _collect_error_sources() reaches implements this structurally, no shared base required, so
        # the aggregator holds a collected list rather than a hand-enumerated one.
        return [self]

    def get_loggers(self) -> "list[PrintLogHistory]":
        # Same fan-in shape as get_error_sources(), for a system-wide debug-level registry instead
        # (SPECIFICATION.md Part C.14) - one entry per logger this module itself owns.
        return [self.pr]

    async def reset_error_counter(self) -> bool:
        # Resets both counters this file tracks, not just pr's persisted history/_err_count -
        # _err_cnt_internal is the separate consecutive-failure streak _error_check's give-up
        # decision relies on, and must not survive a reset the caller expects to be total.
        self._err_cnt_internal = 0
        self._rungs = 0
        return await self.pr.reset()

    async def setup(self) -> None:
        # A logger that could not reach its store has logged it and runs in RAM.
        await self.pr.setup()


def utc_now() -> int | None:
    # The current UTC timestamp (Part G.2): None until the NTP client has set the clock this boot.
    return time.mktime(time.gmtime()) if _utc_valid else None


class SensorReaderConfig(SensorReader):
    # False where the owner keeps a module's config store off FRAM (SCD30, owner, 2026-09-29: 'no extra FRAM chunk')
    _CFG_LOG_FRAM = True

    def __init__(
        self,
        init_data: "NamedTuple",
        name: str,
        default_vals: "ConfigSchema",
        # @tunable module.max_error = 5
        max_module_error: int = 5,
        name_ext: str = "",
        cfg_path: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        super().__init__(init_data, name, max_module_error=max_module_error, name_ext=name_ext, log=log)
        self._cfg_schema = default_vals
        # self.name - already instance_name(name, name_ext) from super().__init__() - threads the
        # per-instance extension into both the on-flash filename and this ConfigManager's own
        # "CFGMGR_<name>" logger (Part C.14). Never the raw `name`, which is the type's base name.
        cfg_log = log if self._CFG_LOG_FRAM else LogConfig(None, log.history_length, log.debug)
        self.cfgmgr = ConfigManager(config_filename(cfg_path, self.name), default_vals, self.name, log=cfg_log)
        self.cfgmgr.owner_lock = self._set_lock  # this module's one PUT lock (_set_dict_cfg())

    async def _get_mgr_cfg(self, cfg: list[str]) -> dict[str, int | float | str | bool | None] | None:
        self.pr.evt("Reading config via cfgmgr.")
        if not self.cfgmgr.writable:
            return None  # defaults standing in for a file it could not read: the GET's marker, as SYSTEM's (Part C.6)
        return await self.cfgmgr.get_dict(cfg)

    async def _set_mgr_cfg(self, data: "JsonMapping", _cfg_vals: "ConfigSchema") -> "tuple[bool, WriteValidity]":
        # Overridable extension point mirroring _get_mgr_cfg - a subclass with a different persistence backend
        # can override just this and still reuse _set_dict_cfg's orchestration. Deferred: _commit_mgr_cfg() releases it.
        self.pr.evt("Writing config via cfgmgr.")
        return await self.cfgmgr.write_config(data, defer=True)

    def _commit_mgr_cfg(self) -> None:
        self.cfgmgr.commit()

    def _writes_closed(self) -> bool:
        # A store closed for a commanded reset refuses this module's PUTs.
        return self.cfgmgr.writes_closed()

    def get_cfg_schema(self) -> "ConfigSchema":
        # Captured once from super().__init__()'s default_vals; sync (no I/O/locking involved).
        return self._cfg_schema

    def get_error_sources(self) -> "list[ErrorSource]":
        # Extends SensorReader.get_error_sources() with this class's own nested error-logging
        # sub-object (self.cfgmgr) - see that method's own comment for the full fan-in convention.
        return [self, self.cfgmgr]

    def get_loggers(self) -> "list[PrintLogHistory]":
        # Same extension as get_error_sources() above, for the debug-level registry instead.
        return [self.pr, self.cfgmgr.pr]

    async def setup(self) -> None:
        # The reader's own logger first, then the store and its logger.
        await super().setup()
        await self.cfgmgr.setup()
