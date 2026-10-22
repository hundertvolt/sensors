"""Shared base classes and primitives: the session lock (Lockable, DeviceSession), region buffers (RegionBuffer), received bytes in pieces (PieceBuffer), shared scalars (LockedCounter, LockedFlag, LockedValue: no method awaits, so no lock), elapsed seconds (TickSeconds), the UTC timestamp, and the sensor-driver base (SensorReader, SensorReaderConfig) with error bookkeeping and optional JSON config storage.
Every method returns a well-defined value, never raises; PieceBuffer's construction alone may raise MemoryError, its caller's cap bounding it.
"""
# __init__ never calls self.pr.setup() (sync vs. async): setup() does it first (SensorReader), then the
# store's (SensorReaderConfig) - both inside the one-time boot batch, never lazily in a task (Part A.7).

import asyncio
import time
from collections import namedtuple

from micropython import const

from asy_config_manager import ConfigManager, check_cfg_get_default, config_filename, instance_name, schema_dict, schema_names, type_or_range_error
from asy_print_log import DEFAULT_LOG, LogConfig, make_logger

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterator, Mapping
    from typing import Literal, NamedTuple, Protocol, TypeVar

    from machine import Timer
    from typing_extensions import Self

    from asy_config_manager import CfgValue, ConfigSchema, FieldSchema, WriteValidity
    from asy_i2c_driver import I2C, I2CDevice
    from asy_print_log import ErrorLog, PrintLogHistory

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
    SetupFct = Callable[[], Awaitable[bool]]  # one boot setup: True when ready

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
_ERR_TIMER = const(17)
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
        except RuntimeError:  # in case it's already released somehow
            pass
        return False


class DeviceSession(Lockable):
    # One device's session lock plus its bus device (SPECIFICATION.md C.2/G.2); every sensor driver's chip sits on
    # I2C, so the device is typed as one - an SPI chip, when one exists, gets its own typed session.
    def __init__(self, bus_device: "I2CDevice") -> None:
        super().__init__()
        self.i2c_device = bus_device


class RegionBuffer:
    def __init__(self, size: int, data_start: int = 0, data_length: int | None = None) -> None:
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
                self._buf = None  # silent: no logger here and print() stays in asy_print_log.py; the owner reads None

    def get_buf(self) -> bytearray | None:
        return self._buf

    def get_data_buf(self) -> memoryview | None:
        if self._buf is None:
            return None
        return memoryview(self._buf)[self.data_start : self.data_end]


class PieceBuffer:
    # Bytes too many for one allocation, held as pieces of at most piece_bytes: no allocation is larger
    # than one piece (owner, 2026-10-05). Read through its length, its pieces and copy-out, never joined.
    def __init__(self, size: int, piece_bytes: int) -> None:
        self._size = size
        self._piece_bytes = piece_bytes
        # Every piece allocated here, after the caller's cap admitted size; a MemoryError is not caught.
        self._pieces = [bytearray(min(piece_bytes, size - start)) for start in range(0, size, piece_bytes)]

    def __len__(self) -> int:
        return self._size

    def copy_into(self, dest: bytearray | memoryview, start: int = 0) -> bool:
        # The bytes from start to the end into the front of dest; a short dest gets nothing, never a partial copy.
        if start < 0 or start > self._size or len(dest) < self._size - start:
            return False
        index, at = divmod(start, self._piece_bytes)
        pos = 0
        while index < len(self._pieces):
            piece = self._pieces[index]
            n = len(piece) - at
            dest[pos : pos + n] = memoryview(piece)[at:]
            pos += n
            index += 1
            at = 0
        return True

    def pieces(self) -> "Iterator[bytearray]":
        return iter(self._pieces)

    def trim(self, length: int) -> bool:
        # A short train's length: trailing pieces dropped and the last one shortened in place, nothing allocated.
        if length < 0 or length > self._size:
            return False
        keep = (length + self._piece_bytes - 1) // self._piece_bytes
        while len(self._pieces) > keep:
            self._pieces.pop()
        if keep:
            self._pieces[-1][length - (keep - 1) * self._piece_bytes :] = b""
        self._size = length
        return True

    def write_at(self, offset: int, src: bytes | bytearray | memoryview) -> bool:
        if offset < 0 or offset + len(src) > self._size:
            return False
        view = memoryview(src)
        index, at = divmod(offset, self._piece_bytes)
        done = 0
        while done < len(view):
            piece = self._pieces[index]
            n = min(len(piece) - at, len(view) - done)
            piece[at : at + n] = view[done : done + n]
            done += n
            index += 1
            at = 0
        return True


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


def arm_tick_timer(timer: "Timer", flag: asyncio.ThreadSafeFlag, pr: "PrintLogHistory", what: str) -> bool:
    # The one starter shape of the 1 s tick timers (system uptime, WiFi uptime, NTP sync age): False when
    # the alarm pool refuses the arm (Part F.1), reported here in one wording; the caller degrades.
    try:
        timer.init(period=1000, mode=timer.PERIODIC, callback=lambda _b: flag.set())
    except (MemoryError, OSError) as e:
        pr.err("Could not arm", what, "timer:", e)
        return False
    return True


class SensorReader:
    # Set by a reader that divides the 1 s base tick (BMP3XX, ISL29125); read by _trigger_loop() only.
    _base_trigger_event: asyncio.ThreadSafeFlag
    _read_event: asyncio.ThreadSafeFlag
    _trigger_counter: int
    _trigger_period: LockedValue
    start_timer: "TimerStarter"

    def __init__(
        self,
        init_data: "NamedTuple",
        name: str,
        # @tunable module.max_error = 5
        max_module_error: int = 5,
        name_ext: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        # name_ext="" (every module today) reproduces `name` unchanged - see instance_name()'s own
        # comment and SPECIFICATION.md Part C.14. Resolved once here, so self.pr.name and self.name agree.
        resolved_name = instance_name(name, name_ext)
        self.pr = make_logger(log, resolved_name)
        self.name = resolved_name  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (sensors=/error_sources=/settings=).
        self._datastruct = init_data
        self._data_lock = asyncio.Lock()  # guards the last sample across a reader's read and a GET
        self._max_module_error = max_module_error
        self._err_cnt_internal = 0
        self._set_lock = asyncio.Lock()  # serialises one module's config PUT (Part C.5.2)
        # Per-field live-push callbacks: a subclass registers {field_name: async_push_fn} entries
        # after super().__init__(); a field with no entry is persist-only (see SPECIFICATION.md C.5.2).
        self._push_callbacks: dict[str, PushFct] = {}
        # Per-field live read-back for _recover_failed_push's fallback chain (optional, unlike
        # _push_callbacks); a field with no entry skips to the next rung (see SPECIFICATION.md C.5.2).
        self._get_callbacks: dict[str, Callable[[], Awaitable[CfgValue]]] = {}
        self._rungs = 0  # the _RUNG_* bits this failure episode already ran
        self._bus_mark = 0  # _recovery_bus.recoveries when this episode began
        self._recovery_bus: I2C | None = None  # set by a driver whose chip sits on I2C
        self._timer_error: Exception | None = None  # a failed read-trigger arm, until its task reports it

    async def _get_dict_cfg(
        self,
        name: str,
        cfg_vals: "ConfigSchema",
        callback: "Callable[[], Awaitable[dict[str, CfgValue]]] | None" = None,
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

    async def _set_dict_cfg(self, data: "JsonMapping", cfg_vals: "ConfigSchema") -> "WriteValidity":
        # Setter mirror of _get_dict_cfg (Part C.5.2): stage first, push only the changed fields, then commit the
        # staged write, so the flash write follows the pushes. One PUT per module at a time: a failed push's
        # recovery can never overwrite a value a later PUT stored meanwhile.
        async with self._set_lock:
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

            try:
                for key in data:
                    # Defense-in-depth: a misbehaving _set_mgr_cfg override could report persisted=True but
                    # omit a key from results (the real ConfigManager-backed path never does).
                    results.setdefault(key, "Failed")
                for key, value in data.items():
                    if results.get(key) != "Valid":
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
                        await self.pr.err_s("Error pushing", key, "to sensor:", e, errno=_ERR_PUSH_RAISED)
                        pushed = False
                    if not pushed:
                        results[key] = "Failed"
                        await self._recover_failed_push(key, old_values, cfg_vals, fields=fields)
            finally:  # a cancelled PUT still releases its staged write
                self._commit_mgr_cfg()
            return results

    async def _set_meas_data(self, data: "NamedTuple") -> None:
        async with self._data_lock:
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
                await self.pr.err_s("Device recovery raised:", e, errno=_ERR_CALLBACK)
                return  # a failed rung: its one entry is this error
            if ok is True:  # a failed hook has logged its own error; None means no participant rung
                await self.pr.wrn_s("Device recovery after", n, "failed cycles: done", wrnno=_WRN_DEVICE_RECOVERY)
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
            self._err_cnt_internal += 1
            await self.pr.err_s("Error counter increased to", self._err_cnt_internal, errno=_ERR_STREAK)
            if self._err_cnt_internal > self._max_module_error:
                await self.pr.err_s("Maximum error count reached!", errno=_ERR_GIVE_UP)
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
            await self.pr.wrn_s("I2C bus was held at boot and cleared, status", status, wrnno=_WRN_BUS_RECOVERY)

    async def _init_failed(self) -> None:
        # A driver's _init_*() calls it before a chip-setup failure's return False: the bus is cleared and
        # its controller rebuilt before the task's restart budget reaches the reboot.
        bus = self._recovery_bus
        if bus is None:
            return
        self._bus_mark = bus.recoveries  # the setup attempt starts its own episode
        self._rungs |= _RUNG_BUS
        await self._recover_bus(_RUNG_CONTROLLER)

    async def _recover_bus(self, rung: int) -> None:
        # One bus rung per bus per episode: a reader that sees the bus already recovered since its episode
        # began (another reader on it ran the rung) only marks its own rung as spent.
        bus = self._recovery_bus
        if bus is None or self._rungs & rung:
            return
        self._rungs |= rung
        if bus.recoveries != self._bus_mark:
            return
        if rung == _RUNG_BUS:
            status = await bus.clear()
            await self.pr.wrn_s("I2C bus cleared, status", status, wrnno=_WRN_BUS_RECOVERY)
        else:
            status = await bus.recover()
            await self.pr.wrn_s("I2C controller re-initialised, status", status, wrnno=_WRN_BUS_RECOVERY)
        self._bus_mark = bus.recoveries  # this reader's own rung is not another reader's at the next one

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
            persisted, res = await self._set_mgr_cfg({key: recovered}, cfg_vals)
            res = _checked_write_results(res)
        except Exception as e:
            await self.pr.err_s("Error correcting", key, "after failed push:", e, errno=_ERR_RECOVERY_WRITE_RAISED)
            return
        if not persisted or res.get(key) not in ("Valid", "Unchanged"):
            # Console only: the store that refused the recovery persisted its own entry.
            self.pr.err("Recovery of", key, "after a failed push was not stored:", res.get(key))

    async def _republish(self, names: tuple[str, ...], **changes: object) -> None:
        # The last sample again with the named fields changed, in one hold with no await inside, so a
        # concurrent store is never overwritten by a stale copy; names are the namedtuple's fields in order.
        async with self._data_lock:
            old = self._datastruct
            values = (changes[n] if n in changes else getattr(old, n) for n in names)
            self._datastruct = type(old)(*values)  # type: ignore[arg-type]  # the sample's own namedtuple class, not NamedTuple's factory

    def _timer_failed(self, e: Exception, waiter: asyncio.ThreadSafeFlag) -> None:
        # A read-trigger arm failed in a sync starter: keep it for the waiting task and wake that task.
        self._timer_error = e
        self.pr.err("Could not start timer:", e)
        waiter.set()

    async def _timer_fault(self) -> bool:
        # True once a failed arm is persisted: the woken task then ends, and its restart re-arms.
        if self._timer_error is None:
            return False
        await self.pr.err_s("Read trigger timer not armed:", self._timer_error, errno=_ERR_TIMER)
        return True

    async def _trigger_loop(self) -> None:
        # The shared divider (Part C.9): every n-th base tick sets the read event, n the trigger period; a
        # failed arm is retried first, and a fault seen after a wake ends the task.
        if self._timer_error is not None:
            self._timer_error = None
            self.start_timer()
        self._trigger_counter = 0
        while True:
            await self._base_trigger_event.wait()
            if await self._timer_fault():
                return
            self._trigger_counter += 1
            period = await self._trigger_period.get_value()  # set at construction, never None
            if period is not None and self._trigger_counter >= period:
                self._read_event.set()
                self._trigger_counter = 0

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

    async def setup(self) -> bool:
        # True = ready; a logger that could not reach its store has logged it and runs in RAM.
        await self.pr.setup()
        return True


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

    async def _get_mgr_cfg(self, cfg: list[str]) -> dict[str, int | float | str | bool | None] | None:
        self.pr.evt("Reading config via cfgmgr.")
        return await self.cfgmgr.get_dict(cfg)

    async def _set_mgr_cfg(self, data: "JsonMapping", _cfg_vals: "ConfigSchema") -> "tuple[bool, WriteValidity]":
        # Overridable extension point mirroring _get_mgr_cfg - a subclass with a different persistence backend
        # can override just this and still reuse _set_dict_cfg's orchestration. Deferred: _commit_mgr_cfg() releases it.
        self.pr.evt("Writing config via cfgmgr.")
        return await self.cfgmgr.write_config(data, defer=True)

    def _commit_mgr_cfg(self) -> None:
        self.cfgmgr.commit()

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

    async def setup(self) -> bool:
        # The reader's own logger first, then the store and its logger; True when the store is valid.
        await super().setup()
        await self.cfgmgr.setup()
        return self.cfgmgr.valid
