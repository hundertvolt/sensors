"""Leveled console logging (PrintLog) plus a bounded in-memory error/warning history
(PrintLogHistory) and its optional FRAM-backed persistence (PrintLogHistStore), so a history of
recent error/warning codes survives a reboot (see base_classes.py's SensorReader, which uses
PrintLogHistStore only when constructed with a real fram, and PrintLogHistory's pure in-memory
behavior otherwise).

Shared contract: every method here returns a well-defined value and never raises - err_s()/wrn_s()
both persist the error/warning code (in memory, and in FRAM for the Store variant) and still
print() it; logging is additive to the existing console output, not a replacement for it.

PrintLogHistStore's FRAM-touching _write()/_read() are exercised by tests/test_print_log.py against
tests/_fram_mock.py, a fake standing in for the narrow slice of asy_fram_manager.AsyFramManager's
API this file actually calls (get_chunk(), then get_buffer()/write_into()/read_into() on the chunk
it returns) - not the real asy_fram_manager.py, which hasn't itself cleared the src/ promotion
checklist yet (see BACKLOG.md), and whose actual allocator/CRC/dual-copy-redundancy machinery this
mock does not attempt to reproduce.
"""

import struct
from collections import deque

from micropython import const

from crc_checks import CRC8

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any, Protocol

    from crc_checks import CRC_Base

    # PrintLogHistStore only ever calls fram.get_chunk() and, on the chunk it gets back,
    # get_buffer()/write_into()/read_into() - not the full asy_fram_manager.AsyFramManager API.
    # Protocols express that narrower real dependency directly, instead of naming the concrete
    # AsyFramManager/AsyFramChunk classes (which would also drag in asy_fram_manager.py, itself not
    # promoted to src/ yet - see BACKLOG.md) - and let tests/_fram_mock.py's fake satisfy the type
    # by having the right shape, with no inheritance relationship to the real classes required.
    class _FramBuffer(Protocol):
        def get_buf(self) -> "bytearray | None": ...
        def get_data_buf(self) -> "memoryview | None": ...

    class _FramChunk(Protocol):
        def get_buffer(self) -> "_FramBuffer": ...
        # buf is always whatever this same chunk's own get_buffer() just returned, fed straight
        # back in - real AsyFramChunk/tests/_fram_mock.py's _MockFramChunk each narrow this to
        # their own concrete buffer subtype, which is fine for get_buffer()'s covariant return but
        # would make write_into()/read_into()'s parameter contravariantly incompatible with a
        # shared _FramBuffer protocol type here; Any sidesteps that mismatch since this file never
        # inspects buf itself, only round-trips it.
        async def write_into(self, buf: "Any", override_pause: bool = False) -> bool: ...
        async def read_into(self, buf: "Any", override_pause: bool = False) -> bool: ...

    class _FramManager(Protocol):
        def get_chunk(
            self, size: int, crc: "CRC_Base | None" = None, verify: int = 0, check_length: int = 8
        ) -> "_FramChunk | None": ...


# defs for PrintLog
_LOG_OFF = const(0)
_LOG_ERR = const(1)
_LOG_WARN = const(2)
_LOG_ONCE = const(3)
_LOG_EVENT = const(4)
_LOG_ALL = const(5)

# defs for history logging
_NO_ERR = const(0x00)
_MAX_ERR = const(0x7F)
_NO_WRN = const(0x80)
_MAX_WRN = const(0xFF)
_MAX_CNT = const(0xFFFF)


class PrintLog:
    def __init__(self, level: int | None = None) -> None:
        self.level = _LOG_OFF
        self.set_level(level)

    @staticmethod
    def level_off() -> int:
        return _LOG_OFF

    @staticmethod
    def level_err() -> int:
        return _LOG_ERR

    @staticmethod
    def level_warn() -> int:
        return _LOG_WARN

    @staticmethod
    def level_once() -> int:
        return _LOG_ONCE

    @staticmethod
    def level_event() -> int:
        return _LOG_EVENT

    @staticmethod
    def level_info() -> int:
        return _LOG_ALL

    def set_level(self, level: int | None) -> None:  # clamps to the valid [off, all] range instead of rejecting
        if level is None:
            self.level = _LOG_OFF
        elif level < _LOG_OFF:
            self.level = _LOG_OFF
        elif level > _LOG_ALL:
            self.level = _LOG_ALL
        else:
            self.level = level

    def get_level(self) -> int:
        return self.level

    def err(self, *args: "Any", **kwargs: "Any") -> None:
        if self.level >= _LOG_ERR:
            print(*args, **kwargs)

    def wrn(self, *args: "Any", **kwargs: "Any") -> None:
        if self.level >= _LOG_WARN:
            print(*args, **kwargs)

    def one(self, *args: "Any", **kwargs: "Any") -> None:
        if self.level >= _LOG_ONCE:
            print(*args, **kwargs)

    def evt(self, *args: "Any", **kwargs: "Any") -> None:
        if self.level >= _LOG_EVENT:
            print(*args, **kwargs)

    def all(self, *args: "Any", **kwargs: "Any") -> None:
        if self.level >= _LOG_ALL:
            print(*args, **kwargs)


class PrintLogHistory(PrintLog):
    def __init__(self, history_length: int = 10, level: int | None = None) -> None:
        super().__init__(level=level)
        self.hl = history_length
        self.history = deque([_NO_ERR] * history_length, history_length)
        self.err_count = 0
        self.initialized = False

    async def setup(self) -> None:  # no persistence to load in the pure in-memory case
        self.initialized = True

    async def _write(self) -> bool:
        return True

    async def _read(self) -> bool:
        return True

    async def _store_err(self, min_e: int, max_e: int, errno: int) -> None:
        if self.err_count < _MAX_CNT:
            self.err_count += 1
        elif self.level > _LOG_OFF:
            print("PrintLog: Error count reached maximum value!")
        if errno <= _NO_ERR:
            return
        errno += min_e
        if errno <= max_e:
            self.history.append(errno)
        elif self.level > _LOG_OFF:
            print("PrintLog: Error number", errno - min_e, "is invalid!")
        if not self.initialized and self.level > _LOG_OFF:
            print("PrintLog: Uninitialized, call setup first!")
            return
        if not await self._write() and self.level > _LOG_OFF:
            print("PrintLog: History write failed!")

    async def err_s(self, *args: "Any", errno: int = _NO_ERR, **kwargs: "Any") -> None:
        await self._store_err(_NO_ERR, _MAX_ERR, errno)
        if self.level >= _LOG_ERR:
            print(*args, **kwargs)

    async def wrn_s(self, *args: "Any", wrnno: int = _NO_ERR, **kwargs: "Any") -> None:
        await self._store_err(_NO_WRN, _MAX_WRN, wrnno)
        if self.level >= _LOG_WARN:
            print(*args, **kwargs)

    async def reset(self) -> None:
        self.history.extend([_NO_ERR] * len(self.history))
        self.err_count = 0
        if not self.initialized and self.level > _LOG_OFF:
            print("PrintLog: Uninitialized, call setup first!")
            return
        if not await self._write() and self.level > _LOG_OFF:
            print("PrintLog: History reset write failed!")

    async def get_log(self, name: str) -> dict[str, dict[str, int | list[int] | list[str]]]:
        err_num = []
        err_type = []
        for errno in self.history:
            if errno == _NO_ERR or errno == _NO_WRN:
                err_num.append(errno)
                err_type.append("N")
            elif errno <= _MAX_ERR:
                err_num.append(errno - _NO_ERR)
                err_type.append("E")
            elif errno <= _MAX_WRN:
                err_num.append(errno - _NO_WRN)
                err_type.append("W")
        return {name: {"ErrCount": self.err_count, "ErrNum": err_num, "ErrType": err_type}}


class PrintLogHistStore(PrintLogHistory):
    def __init__(self, fram: "_FramManager", history_length: int = 10, level: int | None = None) -> None:
        super().__init__(history_length=history_length, level=level)
        self.fram: _FramChunk | None = fram.get_chunk(struct.calcsize("H" + "B" * len(self.history)), crc=CRC8())
        if self.fram is None and self.level > _LOG_OFF:
            print("PrintLog: FRAM allocation failed!")

    async def setup(self) -> None:
        if self.fram is None or self.initialized:
            return
        if await self._read():
            self.initialized = True
        elif await self._write():
            self.initialized = True
        elif self.level > _LOG_OFF:
            print("PrintLog: FRAM setup failed!")

    async def _write(self) -> bool:
        if self.fram is None:
            return False
        buf = self.fram.get_buffer()
        dbuf = buf.get_data_buf()
        try:  # broad on purpose: asy_fram_manager.py isn't itself promoted/audited yet (see module docstring)
            struct.pack_into("H", dbuf, 0, self.err_count)
            struct.pack_into("B" * len(self.history), dbuf, struct.calcsize("H"), *self.history)
            return bool(await self.fram.write_into(buf))
        except Exception:
            return False

    async def _read(self) -> bool:
        if self.fram is None:
            return False
        buf = self.fram.get_buffer()
        dbuf = buf.get_data_buf()
        if not await self.fram.read_into(buf):
            return False
        try:  # broad on purpose: asy_fram_manager.py isn't itself promoted/audited yet (see module docstring)
            self.err_count = struct.unpack_from("H", dbuf, 0)[0]
            self.history.extend(struct.unpack_from("B" * len(self.history), dbuf, struct.calcsize("H")))
            return True
        except Exception:
            return False
