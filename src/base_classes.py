"""Shared base classes every other improved-quality/ driver/manager builds on: async-lock-guarded
objects/buffers (Lockable, LockableBuffer), lock-protected scalars (LockedCounter, LockedFlag,
LockedValue - a common get_value/set_value shape, each adding its own specialty on top), and the
shared sensor-driver base (SensorReader, SensorReaderConfig) that centralizes per-sensor
error-count bookkeeping and (optionally) per-sensor JSON config storage.

Shared contract: every method returns a well-defined value and never raises.

SensorReader accepts an optional `fram`: when None, logging is pure in-memory (print_log.py's
PrintLogHistory); when a real AsyFramManager is passed, logging persists into FRAM
(PrintLogHistStore) instead. asy_fram_manager.py itself hasn't cleared the src/ promotion checklist
yet (see BACKLOG.md), so this path is tested here the same way print_log.py tests its own
FRAM-backed methods: against tests/_fram_mock.py's mock, not the real allocator.
"""

import asyncio

from config_manager import ConfigManager, schema_names
from print_log import PrintLogHistory, PrintLogHistStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from types import TracebackType
    from typing import Any, NamedTuple, TypeVar

    from asy_fram_manager import AsyFramManager

    from config_manager import ConfigSchema

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
            # A valid, non-negative size can still exhaust RP2040's heap - real FRAM chunk buffers
            # (asy_fram_manager.py's AsyFramChunkBuffer) are allocated fresh on every read/write over
            # an indefinite uptime, so a fragmentation-driven MemoryError here is a real operational
            # risk, not just a caller-mistake corner case. Degrade the same way as the guards above.
            # OverflowError is caught too: confirmed directly against the pinned Unix-port
            # interpreter that bytearray(n) raises OverflowError instead of MemoryError once n hits
            # the signed-64-bit machine-word boundary (2**63) - a second, distinct exception type
            # for the same "can't actually allocate this" outcome, not a caller-mistake case either.
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
        self.max_val = max_val
        self.value = self._clamp(init_value)
        self.value_lock = asyncio.Lock()

    def _clamp(self, value: int | None) -> int | None:  # None = "never happened" sentinel; real values clamp into [0, max_val]
        if value is None:
            return None
        return min(max(value, 0), self.max_val)

    async def set_value(self, value: int | None) -> None:
        async with self.value_lock:
            self.value = self._clamp(value)

    async def get_value(self) -> int | None:
        async with self.value_lock:
            ret = self.value
        return ret

    async def increment(self) -> int:  # None counts as 0 - first increment turns "never happened" into a real count
        return await self._step(1)

    async def decrement(self) -> int:
        return await self._step(-1)

    async def _step(self, delta: int) -> int:
        async with self.value_lock:
            current = 0 if self.value is None else self.value
            current = min(max(current + delta, 0), self.max_val)
            self.value = current
        return current


class LockedFlag:
    def __init__(self, init_value: bool = False) -> None:
        self.value = init_value
        self.value_lock = asyncio.Lock()

    async def set_true(self) -> None:
        async with self.value_lock:
            self.value = True

    async def set_false(self) -> None:
        async with self.value_lock:
            self.value = False

    async def get_value(self) -> bool:
        async with self.value_lock:
            ret = self.value
        return ret


class LockedValue:
    def __init__(self, init_value: int | float) -> None:
        self.value = init_value
        self.value_lock = asyncio.Lock()

    async def set_value(self, value: int | float) -> None:
        async with self.value_lock:
            self.value = value

    async def get_value(self) -> int | float:
        async with self.value_lock:
            ret = self.value
        return ret


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
            self.pr = PrintLogHistStore(fram, history_length, debug)
            self.pr.one("Init with FRAM logging.")
        self._datastruct = init_data
        self._datalock = asyncio.Lock()
        self.max_i2c_err = max_i2c_err
        self._err_cnt_internal = 0

    async def reset_error_counter(self) -> None:
        await self.pr.reset()

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

    async def _get_meas_data(self) -> "NamedTuple":
        async with self._datalock:
            return self._datastruct

    async def _set_meas_data(self, data: "NamedTuple") -> None:
        async with self._datalock:
            self._datastruct = data

    async def _get_mgr_cfg(self, cfg: list[str]) -> dict[str, int | float | str | None] | None:
        return {}

    async def _get_dict_cfg(
        self,
        name: str,
        cfg_vals: "ConfigSchema",
        callback: "Callable[[], Coroutine[Any, Any, dict[str, int | float | str | None]]] | None" = None,
    ) -> dict[str, dict[str, int | float | str | None]]:
        cfg = schema_names(cfg_vals)
        ret: dict[str, dict[str, int | float | str | None]] = {name: {key: None for key in cfg}}

        try:  # _get_mgr_cfg is an overridable extension point - the call itself, not just its result, could misbehave
            sensor_conf = await self._get_mgr_cfg(cfg)
            if sensor_conf is not None:
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
        self.cfgmgr = ConfigManager(
            cfg_path + "config_" + name + ".cfg",
            default_vals,
            self.pr,
        )

    async def _get_mgr_cfg(self, cfg: list[str]) -> dict[str, int | float | str | None] | None:
        return await self.cfgmgr.get_dict(cfg)
