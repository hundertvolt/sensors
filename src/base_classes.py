"""Shared base classes every other improved-quality/ driver/manager builds on: async-lock-guarded
objects/buffers (Lockable, LockableBuffer), lock-protected scalars (LockedCounter, LockedFlag,
LockedValue), and the shared sensor-driver base (SensorReader, SensorReaderConfig) that
centralizes per-sensor error-count bookkeeping and (optionally) per-sensor JSON config storage.

Shared contract: every method returns a well-defined value and never raises, except where noted
per class below.

SensorReader accepts an optional `fram`: when None (the path exercised for real by
tests/test_base_classes.py), logging is pure in-memory (print_log.py's PrintLogHistory); when a
real AsyFramManager is passed, logging persists into FRAM (PrintLogHistStore) instead - but
asy_fram_manager.py hasn't itself cleared the src/ promotion checklist yet (see BACKLOG.md), so
that path stays an untested backlog item here, same as print_log.py's own FRAM-backed methods.
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
        if self.data_end > size:
            self.buf = None
        else:
            self.buf = bytearray(size)

    def get_buf(self) -> bytearray | None:
        return self.buf

    def get_data_buf(self) -> memoryview | None:
        if self.buf is None:
            return None
        return memoryview(self.buf)[self.data_start : self.data_end]


class LockedCounter:
    def __init__(self, init_value: int = 0x00, max_val: int = 0xFF) -> None:
        self.uptime = init_value
        self.uptime_lock = asyncio.Lock()
        self.max_val = max_val

    async def set_counter(self, value: int) -> None:
        async with self.uptime_lock:
            self.uptime = value if value <= self.max_val else self.max_val

    async def get_counter(self) -> int:
        async with self.uptime_lock:
            ret = self.uptime
        return ret

    async def increment(self) -> int:
        async with self.uptime_lock:
            if self.uptime < self.max_val:
                self.uptime += 1
            ret = self.uptime
        return ret

    async def decrement(self) -> int:
        async with self.uptime_lock:
            if self.uptime > 0:
                self.uptime -= 1
            ret = self.uptime
        return ret


class LockedFlag:
    def __init__(self, init_value: bool = False) -> None:
        self.flag = init_value
        self.flag_lock = asyncio.Lock()

    async def set_true(self) -> None:
        async with self.flag_lock:
            self.flag = True

    async def set_false(self) -> None:
        async with self.flag_lock:
            self.flag = False

    async def get_value(self) -> bool:
        async with self.flag_lock:
            ret = self.flag
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

        sensor_conf = await self._get_mgr_cfg(cfg)
        if sensor_conf is not None:
            try:
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
