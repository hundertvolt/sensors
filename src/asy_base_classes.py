"""Shared base classes and primitives: the session lock (Lockable), lock-guarded buffers (LockableBuffer), shared scalars (LockedCounter, LockedFlag, LockedValue: no method awaits, so no lock), elapsed seconds (TickSeconds), the UTC timestamp, and the sensor-driver base (SensorReader, SensorReaderConfig) with error bookkeeping and optional JSON config storage.
Every method returns a well-defined value, never raises.
"""
# __init__ never calls self.pr.setup() (sync vs. async): setup() does it first (SensorReader), then the
# store's (SensorReaderConfig) - both inside the one-time boot batch, never lazily in a task (Part A.7).

import asyncio
import time
from collections import namedtuple

from micropython import const

from asy_config_manager import ConfigManager, check_cfg_get_default, instance_name, schema_dict, schema_names, type_or_range_error
from asy_print_log import DEFAULT_LOG, LogConfig, PrintLogHistory, make_logger

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Literal, NamedTuple, Protocol, TypeVar

    from machine import Timer
    from typing_extensions import Self

    from asy_config_manager import CfgValue, ConfigSchema, WriteValidity
    from asy_print_log import ErrorLog

    MeasDataType = TypeVar("MeasDataType", bound=tuple[int | float | None, ...])

    # Shared typing aliases (SPECIFICATION.md Part C.10), declared once here and imported under
    # TYPE_CHECKING by their users: starter lists, REST payloads and the fan-in shapes.
    TaskStarter = Callable[[], asyncio.Task[None]]
    TimerStarter = Callable[[], None]
    JsonValue = int | float | str | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
    JsonDict = dict[str, JsonValue]

    class ErrorSource(Protocol):
        # One /status error-log entry: what every get_error_sources() list holds (Part C.14).
        name: str

        async def get_error_counter(self) -> "ErrorLog": ...
        async def reset_error_counter(self) -> None: ...

    class LoggerOwner(Protocol):
        # A module whose loggers join the system-wide debug-level registry (Part C.14).
        def get_loggers(self) -> list[PrintLogHistory]: ...

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
_WRN_CALLBACK_KEYS = const(1)
_WRN_CFG_KEYS = const(2)


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
        except RuntimeError:  # in case it's already released somehow
            pass
        return False


class LockableBuffer(Lockable):
    def __init__(self, size: int, data_start: int = 0, data_length: int | None = None) -> None:
        super().__init__()
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
            except (MemoryError, OverflowError):
                self._buf = None

    def get_buf(self) -> bytearray | None:
        return self._buf

    def get_data_buf(self) -> memoryview | None:
        if self._buf is None:
            return None
        return memoryview(self._buf)[self.data_start : self.data_end]


class LockedCounter:
    # No method awaits, so no lock is needed; kept async for a uniform call shape.
    def __init__(self, *, init_value: int | None = 0, max_val: int = COUNTER_CAP) -> None:
        # A negative max_val is a dev-time-typo risk, never a real call-site input - clamped to 0, and
        # anything above COUNTER_CAP to it, so _max_val keeps the counter's own [0, _max_val] invariant
        # for every value rather than letting _clamp collapse every value to a negative _max_val.
        self._max_val = min(max(max_val, 0), COUNTER_CAP)
        self.value = self._clamp(init_value)

    def _clamp(self, value: int | None) -> int | None:  # None = "never happened" sentinel; real values clamp into [0, max_val]
        if value is None:
            return None
        return min(max(value, 0), self._max_val)

    async def get_value(self) -> int | None:
        return self.value

    async def set_value(self, value: int | None) -> None:
        self.value = self._clamp(value)

    async def decrement(self) -> int:
        current = 0 if self.value is None else self.value
        if current > 0:
            current -= 1
        self.value = current
        return current

    async def increment(self) -> int:  # None counts as 0 - first increment turns "never happened" into a real count
        current = 0 if self.value is None else self.value
        if current < self._max_val:  # checked before the step: no intermediate above the cap
            current += 1
        self.value = current
        return current


class LockedFlag:
    # No method awaits, so no lock is needed; kept async for a uniform call shape.
    def __init__(self, *, init_value: bool = False) -> None:
        self.value = init_value

    async def get_value(self) -> bool:
        return self.value

    async def set_false(self) -> None:
        self.value = False

    async def set_true(self) -> None:
        self.value = True


class LockedValue:
    # No method awaits, so no lock is needed; kept async for a uniform call shape.
    def __init__(self, *, init_value: int | float | None) -> None:
        self.value = init_value

    async def get_value(self) -> int | float | None:
        return self.value

    async def set_value(self, value: int | float | None) -> None:
        self.value = value


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


def _checked_write_results(results: "WriteValidity") -> "WriteValidity":
    # Lives out here so the raise isn't inside _set_dict_cfg's own try block: an overriding
    # _set_mgr_cfg could return a malformed shape, which has to surface as that try's logged failure.
    if not isinstance(results, dict):
        raise TypeError("_set_mgr_cfg returned a non-dict result")
    return results


_utc_valid = False  # one writer (the NTP client's sync success), no await between read and use


def set_utc_valid(*, valid: bool = True) -> None:
    # The NTP client calls it once it has set the RTC; the clock then stays valid for the boot (Part G.2).
    global _utc_valid
    _utc_valid = valid


def arm_tick_timer(timer: "Timer", flag: asyncio.ThreadSafeFlag, pr: PrintLogHistory, what: str) -> bool:
    # The one starter shape of the 1 s tick timers (system uptime, WiFi uptime, NTP sync age): False when
    # the alarm pool refuses the arm (Part F.1), reported here in one wording; the caller degrades.
    try:
        timer.init(period=1000, mode=timer.PERIODIC, callback=lambda _b: flag.set())
    except (MemoryError, OSError) as e:
        pr.err("Could not arm", what, "timer:", e)
        return False
    return True


class SensorReader:
    def __init__(
        self,
        init_data: "NamedTuple",
        name: str,
        # @tunable module.max_error = 5
        max_module_error: int = 5,
        name_ext: str = "",
        log: LogConfig = DEFAULT_LOG,
        logger: PrintLogHistory | None = None,
    ) -> None:
        # name_ext="" (every module today) reproduces `name` unchanged - see instance_name()'s own
        # comment and SPECIFICATION.md Part C.14. Resolved once here, before either logger branch,
        # so self.pr.name/self.name always agree regardless of which branch runs.
        resolved_name = instance_name(name, name_ext)
        if logger is not None:  # reach-through: reuse a directly-bound sibling object's own logger
            self.pr = logger
        else:
            self.pr = make_logger(log, resolved_name)
        self.name = resolved_name  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (sensors=/error_sources=/settings=).
        self._datastruct = init_data
        self._data_lock = asyncio.Lock()
        self.max_module_error = max_module_error
        self._err_cnt_internal = 0
        # Per-field live-push callbacks: a subclass registers {field_name: async_push_fn} entries
        # after super().__init__(); a field with no entry is persist-only (see SPECIFICATION.md C.5.2).
        self._push_callbacks: dict[str, Callable[[CfgValue], Coroutine[object, object, bool]]] = {}
        # Per-field live read-back for _recover_failed_push's fallback chain (optional, unlike
        # _push_callbacks); a field with no entry skips to the next rung (see SPECIFICATION.md C.5.2).
        self._get_callbacks: dict[str, Callable[[], Coroutine[object, object, CfgValue]]] = {}

    async def _get_dict_cfg(
        self,
        name: str,
        cfg_vals: "ConfigSchema",
        callback: "Callable[[], Coroutine[object, object, dict[str, CfgValue]]] | None" = None,
    ) -> dict[str, dict[str, int | float | str | bool | None]]:
        cfg = schema_names(cfg_vals)
        ret: dict[str, dict[str, int | float | str | bool | None]] = {name: dict.fromkeys(cfg)}

        try:  # _get_mgr_cfg is an overridable extension point - the call itself, not just its result, could misbehave
            sensor_conf = await self._get_mgr_cfg(cfg)
            if sensor_conf is not None:
                if not all(k in ret[name] for k in sensor_conf):
                    await self.pr.wrn_s("Warning: Sensor config manager adds unknown keys to config dict!", wrnno=_WRN_CFG_KEYS)
                ret[name].update(sensor_conf)
        except Exception as e:  # subclass override could legitimately misbehave; not statically ruled out
            await self.pr.err_s("Error updating config dict:", e, errno=_ERR_CFG_GET_RAISED)

        if callback is not None:
            try:
                sensor_callback = await callback()
                if not all(k in ret[name] for k in sensor_callback):
                    await self.pr.wrn_s("Warning: Sensor callback adds unknown keys to config dict!", wrnno=_WRN_CALLBACK_KEYS)
                ret[name].update(sensor_callback)
            except Exception as e:  # callback is caller-supplied; its runtime behavior isn't statically known
                await self.pr.err_s("Error reading config from sensor:", e, errno=_ERR_CFG_CALLBACK_RAISED)

        return ret

    async def _get_meas_data(self) -> "NamedTuple":
        async with self._data_lock:
            return self._datastruct

    async def _get_mgr_cfg(self, _cfg: list[str]) -> dict[str, int | float | str | bool | None] | None:
        return {}

    async def _set_dict_cfg(
        self, data: dict[str, int | float | str | bool | None], cfg_vals: "ConfigSchema",
    ) -> "WriteValidity":
        # Setter mirror of _get_dict_cfg (Part C.5.2): persist first, then push only the changed fields.
        # The pre-write snapshot covers only what _recover_failed_push can use: a persisted key with a
        # push callback, so a store without push callbacks (SCD30's chip) pays no second read.
        persisted_keys = [
            key for key, field in schema_dict(cfg_vals).items()
            if key in data and key in self._push_callbacks and check_cfg_get_default(field)[0]
        ]
        try:  # _get_mgr_cfg is an overridable extension point, same defense as _get_dict_cfg's own use of it
            old_values = await self._get_mgr_cfg(persisted_keys) if persisted_keys else {}
        except Exception as e:
            await self.pr.err_s("Error reading previous config for fallback:", e, errno=_ERR_CFG_SNAPSHOT_RAISED)
            old_values = None
        if old_values is None:
            old_values = {}

        try:  # _set_mgr_cfg is an overridable extension point - the call itself could misbehave on a
            # subclass override (mirrors _get_dict_cfg's own _get_mgr_cfg handling); the isinstance
            # check below extends that defense to a malformed return shape, not just a raise.
            persisted, results = await self._set_mgr_cfg(data, cfg_vals)
            results = _checked_write_results(results)
        except Exception as e:
            await self.pr.err_s("Error writing config dict:", e, errno=_ERR_CFG_SET_RAISED)
            persisted, results = False, {}

        if not persisted:
            # Whole-operation failure (invalid ConfigManager, or an internal write error) - nothing
            # was stored, so every requested key is "Failed", not "Invalid" (which would misleadingly
            # suggest the values themselves were the problem) and nothing is pushed live either.
            return dict.fromkeys(data, "Failed")

        for key in data:
            # Defense-in-depth: a misbehaving _set_mgr_cfg override could report persisted=True but
            # omit a key from results (the real ConfigManager-backed path never does) - without this,
            # that key would silently vanish instead of being reported.
            results.setdefault(key, "Failed")

        for key, value in data.items():
            if results.get(key) != "Valid":
                continue  # only an actual, successfully-persisted change gets pushed live
            callback = self._push_callbacks.get(key)
            if callback is None:
                continue  # persist-only field, nothing to push
            # Push the coerced value that was actually persisted, not the caller's raw
            # pre-coercion one - see SPECIFICATION.md Part C.5.2's push-callback contract.
            field = schema_dict(cfg_vals).get(key)
            push_value = value
            if field is not None:
                _is_error, push_value = type_or_range_error(value, field)
            try:
                pushed = await callback(push_value)
            except Exception as e:  # callback is caller-supplied; its runtime behavior isn't statically known
                await self.pr.err_s("Error pushing", key, "to sensor:", e, errno=_ERR_PUSH_RAISED)
                pushed = False
            if not pushed:
                results[key] = "Failed"
                await self._recover_failed_push(key, old_values, cfg_vals)
        return results

    async def _set_meas_data(self, data: "NamedTuple") -> None:
        async with self._data_lock:
            self._datastruct = data

    async def _set_mgr_cfg(
        self, _data: dict[str, int | float | str | bool | None], _cfg_vals: "ConfigSchema",
    ) -> "tuple[bool, WriteValidity]":
        # No store: nothing persists, so _set_dict_cfg() answers every requested key "Failed".
        return False, {}

    async def _error_check(self, results: "MeasDataType", *, condition: bool = True) -> bool:
        # Shared consecutive-failure-streak counter - see SPECIFICATION.md Part C.7's
        # _error_check() bullet for the full contract.
        if any(res is None for res in results) and condition:
            self._err_cnt_internal += 1
            await self.pr.err_s("Error counter increased to", self._err_cnt_internal, errno=_ERR_STREAK)
            if self._err_cnt_internal > self.max_module_error:
                await self.pr.err_s("Maximum error count reached!", errno=_ERR_GIVE_UP)
                return False  # breaking the loop triggers a task reset
        elif self._err_cnt_internal > 0:
            self._err_cnt_internal -= 1
            self.pr.err("Error counter back to", self._err_cnt_internal)
        return True

    async def _recover_failed_push(
        self,
        key: str,
        old_values: dict[str, int | float | str | bool | None],
        cfg_vals: "ConfigSchema",
    ) -> None:
        # Recovery chain for a failed live push (see SPECIFICATION.md C.5.2): live read-back via
        # _get_callbacks, else old_values' pre-write snapshot, else the schema default - written
        # back through _set_mgr_cfg only, bypassing _push_callbacks so a failing push can't loop.
        field = schema_dict(cfg_vals).get(key)
        if field is None:
            return  # shouldn't happen - key was already validated against cfg_vals above
        use_value, default_val = check_cfg_get_default(field)
        if not use_value:
            return  # command-only/special-alone field (e.g. a trigger) - nothing to persist-correct,
            # mirrors legacy's own cmd_keys exclusion from this exact fallback chain

        recovered: int | float | str | bool | None = None
        getter = self._get_callbacks.get(key)
        if getter is not None:
            try:
                recovered = await getter()
            except Exception as e:  # getter is caller-supplied; its runtime behavior isn't statically known
                await self.pr.err_s("Error reading", key, "back from sensor:", e, errno=_ERR_RECOVERY_READ_RAISED)
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
            await self._set_mgr_cfg({key: recovered}, cfg_vals)
        except Exception as e:
            await self.pr.err_s("Error correcting", key, "after failed push:", e, errno=_ERR_RECOVERY_WRITE_RAISED)

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

    def get_loggers(self) -> list[PrintLogHistory]:
        # Same fan-in shape as get_error_sources(), for a system-wide debug-level registry instead
        # (SPECIFICATION.md Part C.14) - one entry per logger this module itself owns.
        return [self.pr]

    async def reset_error_counter(self) -> None:
        # Resets both counters this file tracks, not just pr's persisted history/_err_count -
        # _err_cnt_internal is the separate consecutive-failure streak _error_check's give-up
        # decision relies on, and must not survive a reset the caller expects to be total.
        self._err_cnt_internal = 0
        await self.pr.reset()

    async def setup(self) -> bool:
        # True = ready; a logger that could not reach its store has logged it and runs in RAM.
        await self.pr.setup()
        return True


def utc_now() -> int | None:
    # The current UTC timestamp (Part G.2): None until the NTP client has set the clock this boot.
    return time.mktime(time.gmtime()) if _utc_valid else None


class SensorReaderConfig(SensorReader):
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
        self.cfgmgr = ConfigManager(
            cfg_path + "config_" + self.name + ".cfg",
            default_vals,
            self.name,
            log=log,
        )

    async def _get_mgr_cfg(self, cfg: list[str]) -> dict[str, int | float | str | bool | None] | None:
        self.pr.evt("Reading config via cfgmgr.")
        return await self.cfgmgr.get_dict(cfg)

    async def _set_mgr_cfg(
        self, data: dict[str, int | float | str | bool | None], cfg_vals: "ConfigSchema",
    ) -> "tuple[bool, WriteValidity]":
        # Overridable extension point mirroring _get_mgr_cfg - a subclass with a different
        # persistence backend can override just this and still reuse _set_dict_cfg's orchestration.
        self.pr.evt("Writing config via cfgmgr.")
        return await self.cfgmgr.write_config(data, cfg_vals)

    def get_cfg_schema(self) -> "ConfigSchema":
        # Captured once from super().__init__()'s default_vals; sync (no I/O/locking involved).
        return self._cfg_schema

    def get_error_sources(self) -> "list[ErrorSource]":
        # Extends SensorReader.get_error_sources() with this class's own nested error-logging
        # sub-object (self.cfgmgr) - see that method's own comment for the full fan-in convention.
        return [self, self.cfgmgr]

    def get_loggers(self) -> list[PrintLogHistory]:
        # Same extension as get_error_sources() above, for the debug-level registry instead.
        return [self.pr, self.cfgmgr.pr]

    async def setup(self) -> bool:
        # The reader's own logger first, then the store and its logger; True when the store is valid.
        await super().setup()
        await self.cfgmgr.setup()
        return self.cfgmgr.valid
