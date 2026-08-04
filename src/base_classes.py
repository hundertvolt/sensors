"""Shared base classes: async-lock-guarded objects/buffers (Lockable, LockableBuffer), lock-
protected scalars (LockedCounter, LockedFlag, LockedValue), and the sensor-driver base
(SensorReader, SensorReaderConfig) with error bookkeeping and optional JSON config storage. Every
method returns a well-defined value, never raises. `__init__` never calls `self.pr.setup()` (sync
vs. async) - the caller's own async setup must, or FRAM persistence stays inert.
"""

import asyncio

from config_manager import ConfigManager, check_cfg_get_default, schema_dict, schema_names, type_or_range_error
from print_log import PrintLogHistory, PrintLogHistoryStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from types import TracebackType
    from typing import Any, NamedTuple, TypeVar

    from asy_fram_manager import AsyFramManager
    from config_manager import ConfigSchema, WriteValidity

    LockableType = TypeVar("LockableType", bound="Lockable")
    MeasDataType = TypeVar("MeasDataType", bound=tuple[int | float | None, ...])


class Lockable:
    def __init__(self, asy_lock: asyncio.Lock | None = None) -> None:
        self.asy_lock = asyncio.Lock() if asy_lock is None else asy_lock

    async def __aenter__(self: "LockableType") -> "LockableType":
        await self.asy_lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: "type[BaseException] | None",
        exc_val: "BaseException | None",
        exc_tb: "TracebackType | None",
    ) -> bool:
        try:
            self.asy_lock.release()
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
            self.buf = None
        else:
            # A valid size can still exhaust heap (real FRAM chunk buffers allocate fresh on every
            # read/write over an indefinite uptime) or overflow bytearray's internal size conversion
            # at 2**63 - both degrade the same way as the guards above, not a caller mistake either.
            try:
                self.buf = bytearray(size)
            except (MemoryError, OverflowError):
                self.buf = None

    def get_buf(self) -> bytearray | None:
        return self.buf

    def get_data_buf(self) -> memoryview | None:
        if self.buf is None:
            return None
        return memoryview(self.buf)[self.data_start : self.data_end]


class LockedCounter:
    def __init__(self, init_value: int | None = 0x00, max_val: int = 0xFF) -> None:
        # A negative max_val is a dev-time-typo risk, never a real call-site input - clamped to 0
        # here so the counter's own [0, max_val] invariant holds for every value, rather than letting
        # _clamp collapse every value to the negative max_val itself.
        self.max_val = max(max_val, 0)
        self.value = self._clamp(init_value)
        self.value_lock = asyncio.Lock()

    async def _step(self, delta: int) -> int:
        async with self.value_lock:
            current = 0 if self.value is None else self.value
            current = min(max(current + delta, 0), self.max_val)
            self.value = current
        return current

    def _clamp(self, value: int | None) -> int | None:  # None = "never happened" sentinel; real values clamp into [0, max_val]
        if value is None:
            return None
        return min(max(value, 0), self.max_val)

    async def get_value(self) -> int | None:
        async with self.value_lock:
            ret = self.value
        return ret

    async def set_value(self, value: int | None) -> None:
        async with self.value_lock:
            self.value = self._clamp(value)

    async def increment(self) -> int:  # None counts as 0 - first increment turns "never happened" into a real count
        return await self._step(1)

    async def decrement(self) -> int:
        return await self._step(-1)


class LockedFlag:
    def __init__(self, init_value: bool = False) -> None:
        self.value = init_value
        self.value_lock = asyncio.Lock()

    async def get_value(self) -> bool:
        async with self.value_lock:
            ret = self.value
        return ret

    async def set_true(self) -> None:
        async with self.value_lock:
            self.value = True

    async def set_false(self) -> None:
        async with self.value_lock:
            self.value = False


class LockedValue:
    def __init__(self, init_value: int | float) -> None:
        self.value = init_value
        self.value_lock = asyncio.Lock()

    async def get_value(self) -> int | float:
        async with self.value_lock:
            ret = self.value
        return ret

    async def set_value(self, value: int | float) -> None:
        async with self.value_lock:
            self.value = value


class SensorReader:
    def __init__(
        self,
        init_data: "NamedTuple",
        max_i2c_err: int,
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        if fram is None:
            self.pr = PrintLogHistory(history_length, debug)
            self.pr.one("Init with memory logging.")
        else:
            self.pr = PrintLogHistoryStore(fram, history_length, debug)
            self.pr.one("Init with FRAM logging.")
        self._datastruct = init_data
        self._datalock = asyncio.Lock()
        self.max_i2c_err = max_i2c_err
        self._err_cnt_internal = 0

    async def _get_meas_data(self) -> "NamedTuple":
        async with self._datalock:
            return self._datastruct

    async def _get_mgr_cfg(self, cfg: list[str]) -> dict[str, int | float | str | bool | None] | None:
        return {}

    async def _get_dict_cfg(
        self,
        name: str,
        cfg_vals: "ConfigSchema",
        callback: "Callable[[], Coroutine[Any, Any, dict[str, int | float | str | bool | None]]] | None" = None,
    ) -> dict[str, dict[str, int | float | str | bool | None]]:
        cfg = schema_names(cfg_vals)
        ret: dict[str, dict[str, int | float | str | bool | None]] = {name: {key: None for key in cfg}}

        try:  # _get_mgr_cfg is an overridable extension point - the call itself, not just its result, could misbehave
            sensor_conf = await self._get_mgr_cfg(cfg)
            if sensor_conf is not None:
                if not all(k in ret[name] for k in sensor_conf):
                    await self.pr.wrn_s("Warning: Sensor config manager adds unknown keys to config dict!", wrnno=2)
                ret[name].update(sensor_conf)
        except Exception as e:  # subclass override could legitimately misbehave; not statically ruled out
            await self.pr.err_s("Error updating config dict:", e, errno=3)

        if callback is not None:
            try:
                sensor_callback = await callback()
                if not all(k in ret[name] for k in sensor_callback):
                    await self.pr.wrn_s("Warning: Sensor callback adds unknown keys to config dict!", wrnno=1)
                ret[name].update(sensor_callback)
            except Exception as e:  # callback is caller-supplied; its runtime behavior isn't statically known
                await self.pr.err_s("Error reading config from sensor:", e, errno=4)

        return ret

    async def _set_meas_data(self, data: "NamedTuple") -> None:
        async with self._datalock:
            self._datastruct = data

    async def _error_check(self, results: "MeasDataType", name: str, condition: bool = True) -> bool:
        # centralizes the increment/decrement-error-counter-and-decide-to-give-up logic every
        # sensortask-*.py driver used to hand-roll separately; False tells the caller to give up
        # (triggers the task supervisor's own reset), True to keep going.
        if any(res is None for res in results) and condition:
            self._err_cnt_internal += 1
            await self.pr.err_s(name + " Fehlerzähler erhöht auf", self._err_cnt_internal, errno=1)
            if self._err_cnt_internal > self.max_i2c_err:
                await self.pr.err_s(name + " Maximale Fehleranzahl erreicht!", errno=2)
                return False  # Abbruch der Schleife führt zu Task-Reset
        else:
            if self._err_cnt_internal > 0:
                self._err_cnt_internal -= 1
                self.pr.err(name + " Fehlerzähler zurück auf", self._err_cnt_internal)
        return True

    async def reset_error_counter(self) -> None:
        # Resets both counters this file tracks, not just pr's persisted history/err_count -
        # _err_cnt_internal is the separate consecutive-failure streak _error_check's give-up
        # decision relies on, and must not survive a reset the caller expects to be total.
        self._err_cnt_internal = 0
        await self.pr.reset()


class SensorReaderConfig(SensorReader):
    def __init__(
        self,
        init_data: "NamedTuple",
        max_i2c_err: int,
        name: str,
        default_vals: "ConfigSchema",
        cfg_path: str = "",
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        super().__init__(init_data, max_i2c_err, fram, history_length, debug)
        self.cfg_schema = default_vals
        self.cfgmgr = ConfigManager(
            cfg_path + "config_" + name + ".cfg",
            default_vals,
            self.pr,
        )
        # Per-field live-push callbacks, module-local and registered once here at construction
        # (project decision - constant at runtime, no per-call plumbing needed): a subclass adds
        # its own {field_name: async_push_fn} entries after calling super().__init__(). A field
        # with no entry is persist-only, exactly like most of today's schema fields already are.
        self._push_callbacks: dict[str, Callable[[int | float | str | bool | None], Coroutine[Any, Any, bool]]] = {}
        # Per-field live read-back callbacks, same registration shape as _push_callbacks - used
        # only by _set_dict_cfg's failed-push recovery chain below to ask "what does the sensor
        # actually have right now" before falling further back. A field with no entry here simply
        # skips straight to the next fallback rung; registering one is optional, unlike push
        # callbacks which are the whole point of a field having one.
        self._get_callbacks: dict[str, Callable[[], Coroutine[Any, Any, int | float | str | bool | None]]] = {}

    async def _get_mgr_cfg(self, cfg: list[str]) -> dict[str, int | float | str | bool | None] | None:
        return await self.cfgmgr.get_dict(cfg)

    async def _set_mgr_cfg(
        self, data: "dict[str, int | float | str | bool | None]", cfg_vals: "ConfigSchema"
    ) -> "tuple[bool, WriteValidity]":
        # Overridable extension point, mirroring _get_mgr_cfg: the concrete implementation here
        # delegates to the real ConfigManager, but a subclass with a fundamentally different
        # persistence backend (the "hypothetical sensor with onboard nonvolatile storage" case)
        # could override this alone and still reuse _set_dict_cfg's per-field push orchestration -
        # storage location stays fully abstracted away from callers of _set_dict_cfg.
        return await self.cfgmgr.write_config(data, cfg_vals)

    async def _set_dict_cfg(
        self, data: "dict[str, int | float | str | bool | None]", cfg_vals: "ConfigSchema"
    ) -> "WriteValidity":
        # Setter mirror of _get_dict_cfg: persist first (so a value that made it onto the device is
        # always the value still there after an unplanned reset - project decision), then push live
        # only the fields that actually changed ("Valid") and have a registered callback. Every
        # field is reported individually - an unknown key or an out-of-range value only fails that
        # one key (ConfigManager.write_config's own per-key tolerance), never the whole request.
        #
        # Snapshot each requested field's pre-write value before persisting overwrites it - this is
        # the one rung of _recover_failed_push's fallback chain that only exists here, before the
        # write below, mirroring legacy set_sensor_value()'s "fall back to the stored config" step
        # (which ran against a config that hadn't been touched yet).
        try:  # _get_mgr_cfg is an overridable extension point, same defense as _get_dict_cfg's own use of it
            old_values = await self._get_mgr_cfg(list(data.keys()))
        except Exception as e:
            await self.pr.err_s("Error reading previous config for fallback:", e, errno=7)
            old_values = None
        if old_values is None:
            old_values = {}

        try:  # _set_mgr_cfg is an overridable extension point - the call itself, not just its
            # result, could misbehave on a misbehaving subclass override (mirrors _get_dict_cfg's
            # own _get_mgr_cfg handling) - the isinstance check below extends that same defense to
            # a malformed *shape* of an otherwise-successful return, not just a raised exception.
            persisted, results = await self._set_mgr_cfg(data, cfg_vals)
            if not isinstance(results, dict):
                raise TypeError("_set_mgr_cfg returned a non-dict result")
        except Exception as e:
            await self.pr.err_s("Error writing config dict:", e, errno=5)
            persisted, results = False, {}

        if not persisted:
            # Whole-operation failure (invalid ConfigManager, or an internal write error) - nothing
            # was stored, so every requested key is "Failed", not "Invalid" (which would misleadingly
            # suggest the values themselves were the problem) and nothing is pushed live either.
            return {key: "Failed" for key in data}

        for key in data:
            # Defense-in-depth against a misbehaving _set_mgr_cfg override that reports persisted=True
            # but returns a results dict missing one of the requested keys (the real ConfigManager-
            # backed implementation never does this - write_config() always accounts for every key in
            # data) - without this, such a key would simply vanish from the returned dict instead of
            # being reported, breaking this method's own "every field reported independently" contract.
            results.setdefault(key, "Failed")

        for key, value in data.items():
            if results.get(key) != "Valid":
                continue  # only an actual, successfully-persisted change gets pushed live
            callback = self._push_callbacks.get(key)
            if callback is None:
                continue  # persist-only field, nothing to push
            try:
                pushed = await callback(value)
            except Exception as e:  # callback is caller-supplied; its runtime behavior isn't statically known
                await self.pr.err_s("Error pushing", key, "to sensor:", e, errno=6)
                pushed = False
            if not pushed:
                results[key] = "Failed"
                await self._recover_failed_push(key, old_values, cfg_vals)
        return results

    async def _recover_failed_push(
        self,
        key: str,
        old_values: "dict[str, int | float | str | bool | None]",
        cfg_vals: "ConfigSchema",
    ) -> None:
        # Mirrors legacy set_sensor_value()'s getter/previous-config/default fallback chain: a
        # failed live push must not permanently leave the config file holding a value that was
        # requested but never confirmed applied to the hardware (persist-first already wrote it
        # before this push was even attempted - see _set_dict_cfg above). Recover, in order: a live
        # read-back from the sensor itself (most authoritative, via _get_callbacks), else the value
        # that was stored before this request (old_values, snapshotted in _set_dict_cfg before the
        # overwrite), else the schema's own default for this field. The corrected value is written
        # straight back through _set_mgr_cfg, deliberately bypassing _push_callbacks entirely so a
        # persistently-failing push can't loop. The field's caller-visible status in _set_dict_cfg's
        # returned dict stays "Failed" regardless, matching legacy exactly (the client is told the
        # truth: their request wasn't applied) - only the underlying persisted value is repaired.
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
                await self.pr.err_s("Error reading", key, "back from sensor:", e, errno=8)
                recovered = None
            # A getter is caller-supplied and reads live, possibly-adversarial hardware state - its
            # return value isn't statically known to satisfy this field's own schema (e.g. a
            # corrupted register read-back). Treating an out-of-schema value the same as a raised
            # exception (fall through to the next rung) keeps this cascade's own invariant that
            # every rung it actually accepts is schema-valid - matters because _set_mgr_cfg below is
            # the last check before persisting, and a value it rejects would leave this recovery
            # attempt silently doing nothing instead of falling further back.
            if recovered is not None and type_or_range_error(recovered, field):
                recovered = None
        if recovered is None:
            recovered = old_values.get(key, default_val)

        try:
            await self._set_mgr_cfg({key: recovered}, cfg_vals)
        except Exception as e:
            await self.pr.err_s("Error correcting", key, "after failed push:", e, errno=9)

    def get_cfg_schema(self) -> "ConfigSchema":
        # Single source of truth for every subclass's schema - captured once, right here, from
        # whatever default_vals a subclass already passes into super().__init__(). No I/O or
        # locking involved (unlike _get_mgr_cfg/_get_dict_cfg below), so this stays a plain sync
        # call. self.cfg_schema itself stays a public attribute too - existing callers reach into
        # it directly (see CLAUDE.md's "Microdot / REST layer" section and DRIVER_SPEC.md section 5).
        return self.cfg_schema
