"""Fake for the narrow FRAM API surface print_log.py's PrintLogHistStore actually calls:
AsyFramManager.get_chunk() -> a chunk exposing get_buffer()/write_into()/read_into(). Mirrors
tests/README.md's "mocking boundary" precedent (tests/machine.py mocks only the raw bus
transactions, real driver logic runs against it): this mocks only the raw chunk-storage
transaction, not asy_fram_manager.py's actual allocator/CRC/dual-copy-redundancy machinery, which
isn't itself promoted to src/ yet (see BACKLOG.md).

MockFramBacking is the "chip": raw bytes plus which offsets have actually been written (a real
FRAM chip's contents survive a power cycle; a freshly-constructed MockAsyFramManager does not, by
itself, reflect that - see below). MockAsyFramManager reproduces AsyFramManager.get_chunk()'s own
bump-pointer allocation (same offsets in the same call order), so passing the *same*
MockFramBacking instance into a second MockAsyFramManager and replaying the same get_chunk() call
sequence genuinely simulates "data survives a reboot", which is the entire point of FRAM-backed
storage (see BACKLOG.md's "Trace-log error codes inside FRAM, surviving a reboot").

Remove this file (and the tests built on it) once asy_fram_manager.py itself clears its own src/
promotion checklist and a real AsyFramManager becomes available under tests/ instead - see
BACKLOG.md.
"""

from base_classes import LockableBuffer
from crc_checks import CRC_Pass

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from crc_checks import CRC_Base


class MockFramBacking:
    def __init__(self, size: int = 0x2000) -> None:
        self.storage = bytearray(size)
        self._written_offsets: set[int] = set()

    def write(self, offset: int, data: bytes) -> None:
        self.storage[offset : offset + len(data)] = data
        self._written_offsets.add(offset)

    def read(self, offset: int, length: int) -> bytearray | None:
        # An offset that's never been written is indistinguishable from "erased" on real FRAM -
        # a chunk allocated but never written should read back as invalid, not as zeros.
        if offset not in self._written_offsets:
            return None
        return bytearray(self.storage[offset : offset + length])


class _MockFramChunk:
    def __init__(self, backing: MockFramBacking, offset: int, size: int, crc: "CRC_Base") -> None:
        self._backing = backing
        self._offset = offset
        self._size = size
        self._crc_len = crc.length()

    def get_buffer(self) -> LockableBuffer:
        return LockableBuffer(self._size + self._crc_len, data_start=0, data_length=self._size)

    async def write_into(self, buf: LockableBuffer, override_pause: bool = False) -> bool:
        raw = buf.get_buf()
        if raw is None:
            return False
        self._backing.write(self._offset, bytes(raw))
        return True

    async def read_into(self, buf: LockableBuffer, override_pause: bool = False) -> bool:
        raw = buf.get_buf()
        if raw is None:
            return False
        data = self._backing.read(self._offset, len(raw))
        if data is None:
            return False
        raw[:] = data
        return True


class MockAsyFramManager:
    def __init__(self, backing: "MockFramBacking | None" = None, out_of_memory: bool = False) -> None:
        self.backing = MockFramBacking() if backing is None else backing
        self._allocated = 0
        self._out_of_memory = out_of_memory

    def get_chunk(
        self, size: int, crc: "CRC_Base | None" = None, verify: int = 0, check_length: int = 8
    ) -> "_MockFramChunk | None":
        crc = CRC_Pass() if crc is None else crc
        full_size = size + crc.length()
        if self._out_of_memory or self._allocated + full_size > len(self.backing.storage):
            return None
        chunk = _MockFramChunk(self.backing, self._allocated, size, crc)
        self._allocated += full_size
        return chunk
