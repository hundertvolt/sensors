"""Leveled console logging (PrintLog), a bounded in-memory error/warning history (PrintLogHistory),
and its optional FRAM-backed persistence (PrintLogHistoryStore), surviving a reboot.

Contract: every method returns a well-defined value and never raises. PrintLogHistoryStore's FRAM
calls are wrapped broadly, matching asy_fram_manager.py's own "never raises" contract (see
BACKLOG.md) plus defense-in-depth against the general _FramManager/_FramChunk Protocol below;
tests/test_print_log.py exercises this against the real AsyFramManager (tests/_fram_chip_fake.py's
simulated chip) and every failure mode still reachable through it.
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

    from base_classes import LockableBuffer
    from crc_checks import CRC_Base

    # Narrow structural Protocols for the FRAM slice this file calls - kept even now that
    # asy_fram_manager.py is promoted to src/, avoiding a real runtime import cycle (it imports
    # PrintLogHistory from here) and decoupling from its concrete chunk shapes - see BACKLOG.md.
    class _FramChunk(Protocol):
        def get_buffer(self) -> "LockableBuffer": ...
        # Any: real chunk classes narrow buf's type in a way that's contravariantly incompatible
        # with a shared Protocol type here; this file only round-trips buf, never inspects it.
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
        # Clamp to [0, _MAX_CNT] (err_count's own uint16 range) before allocating: `[x] * n` can
        # segfault the interpreter uncatchably in a size range bytearray()'s own guards don't cover
        # - see BACKLOG.md for the measured failure-size boundaries.
        history_length = min(max(history_length, 0), _MAX_CNT)
        try:  # still reachable well below the overflow boundary on a genuinely memory-constrained device
            self.history = deque([_NO_ERR] * history_length, history_length)
        except MemoryError:
            history_length = 0
            self.history = deque([], 0)
        self.err_count = 0
        self.initialized = False

    async def setup(self) -> None:  # no persistence to load in the pure in-memory case
        self.initialized = True

    async def _write(self) -> bool:
        return True

    async def _read(self) -> bool:
        return True

    def _diag(self, *args: "Any") -> None:  # internal-failure prints, gated on any logging being enabled at all
        if self.level > _LOG_OFF:
            print(*args)

    async def _store_err(self, min_e: int, max_e: int, errno: int) -> None:
        # errno<=_NO_ERR (0) is the shared "nothing to record" sentinel for err_s()/wrn_s() alike;
        # a real code is only shifted into its own sub-range by min_e past this check.
        if self.err_count < _MAX_CNT:
            self.err_count += 1
        else:
            self._diag("PrintLog: Error count reached maximum value!")
        if errno <= _NO_ERR:
            return
        errno += min_e
        if errno <= max_e:
            self.history.append(errno)
        else:
            self._diag("PrintLog: Error number", errno - min_e, "is invalid!")
        if not self.initialized:
            # Return regardless of logging level - don't write stale state to FRAM before setup().
            self._diag("PrintLog: Uninitialized, call setup first!")
            return
        if not await self._write():
            self._diag("PrintLog: History write failed!")

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
        if not self.initialized:
            # Same "return regardless of self.level" reasoning as _store_err() above.
            self._diag("PrintLog: Uninitialized, call setup first!")
            return
        if not await self._write():
            self._diag("PrintLog: History reset write failed!")

    async def get_log(self, name: str) -> dict[str, dict[str, int | list[int] | list[str]]]:
        # Reverses _store_err()'s encoding: 0x00/0x80 are "nothing recorded"; else shift back by
        # _NO_ERR/_NO_WRN to recover the original error/warning code.
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


class PrintLogHistoryStore(PrintLogHistory):
    _HDR_FMT = "<H"  # explicit little-endian, no padding - bare format defaults to "@" here, not "<"; see BACKLOG.md
    _HDR_SIZE = struct.calcsize(_HDR_FMT)

    def __init__(self, fram: "_FramManager", history_length: int = 10, level: int | None = None) -> None:
        super().__init__(history_length=history_length, level=level)
        # len(self.history) is fixed for this object's lifetime (deque maxlen never changes), so
        # this format string is cached once here instead of being rebuilt on every _write()/_read().
        self._history_fmt = "B" * len(self.history)
        size = self._HDR_SIZE + len(self.history)  # each "B" is exactly 1 byte
        try:  # broad on purpose: defense-in-depth against the Protocol in the abstract, not this one
            # concrete, audited-to-never-raise implementation (see module docstring)
            self.fram: _FramChunk | None = fram.get_chunk(size, crc=CRC8())
        except Exception:
            self.fram = None
        if self.fram is None:
            self._diag("PrintLog: FRAM allocation failed!")

    async def setup(self) -> None:
        if self.fram is None or self.initialized:
            return
        if await self._read():
            self.initialized = True
        elif await self._write():
            self.initialized = True
        else:
            self._diag("PrintLog: FRAM setup failed!")

    async def _write(self) -> bool:
        if self.fram is None:
            return False
        try:  # broad on purpose: defense-in-depth against the Protocol in the abstract, not this one
            # concrete, audited-to-never-raise implementation (see module docstring)
            buf = self.fram.get_buffer()
            dbuf = buf.get_data_buf()
            struct.pack_into(self._HDR_FMT, dbuf, 0, self.err_count)
            struct.pack_into(self._history_fmt, dbuf, self._HDR_SIZE, *self.history)
            return bool(await self.fram.write_into(buf))
        except Exception:
            return False

    async def _read(self) -> bool:
        if self.fram is None:
            return False
        try:  # broad on purpose: defense-in-depth against the Protocol in the abstract, not this one
            # concrete, audited-to-never-raise implementation (see module docstring)
            buf = self.fram.get_buffer()
            dbuf = buf.get_data_buf()
            if not await self.fram.read_into(buf):
                return False
            self.err_count = struct.unpack_from(self._HDR_FMT, dbuf, 0)[0]
            self.history.extend(struct.unpack_from(self._history_fmt, dbuf, self._HDR_SIZE))
            return True
        except Exception:
            return False
