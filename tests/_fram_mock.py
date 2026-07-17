"""Fake for the narrow FRAM API surface print_log.py's PrintLogHistoryStore actually calls:
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

Every failure mode print_log.py defends against can be simulated here, since asy_fram_manager.py
isn't itself audited yet and offers no narrower documented failure contract to mock selectively:
- MockAsyFramManager(out_of_memory=True) / raise_on_get_chunk=True: get_chunk() returns None / raises.
- _MockFramChunk.raise_on_get_buffer / .broken_buffer: get_buffer() raises / returns an unusable
  (zero-length data region) buffer.
- .raise_on_write / .write_returns_false: write_into() raises / reports hardware failure (no raise).
- .raise_on_read / .read_returns_false: read_into() raises / reports hardware failure (no raise).

There's deliberately no "corrupt the stored bytes to make struct.unpack_from() raise" mode: get_buffer()
always hands back a freshly-sized LockableBuffer derived from the same len(history) used to write it,
so a length mismatch in struct's own sense can only ever come from get_buffer() itself misbehaving
(.broken_buffer already covers that), never from what was previously persisted at that offset.

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
        # Fault injection, all off by default - see module docstring for what each simulates.
        self.raise_on_get_buffer = False
        self.broken_buffer = False
        self.raise_on_write = False
        self.write_returns_false = False
        self.raise_on_read = False
        self.read_returns_false = False

    def get_buffer(self) -> LockableBuffer:
        if self.raise_on_get_buffer:
            raise RuntimeError("simulated FRAM buffer allocation failure")
        if self.broken_buffer:
            # data_start > size makes LockableBuffer's own data_end > size check fail, so
            # get_buf()/get_data_buf() both come back None - a "successfully allocated, but
            # unusable" buffer, distinct from get_buffer() raising outright.
            return LockableBuffer(1, data_start=2, data_length=1)
        return LockableBuffer(self._size + self._crc_len, data_start=0, data_length=self._size)

    async def write_into(self, buf: LockableBuffer, override_pause: bool = False) -> bool:
        if self.raise_on_write:
            raise RuntimeError("simulated FRAM write failure")
        if self.write_returns_false:
            return False
        raw = buf.get_buf()
        if raw is None:
            return False
        self._backing.write(self._offset, bytes(raw))
        return True

    async def read_into(self, buf: LockableBuffer, override_pause: bool = False) -> bool:
        if self.raise_on_read:
            raise RuntimeError("simulated FRAM read failure")
        if self.read_returns_false:
            return False
        raw = buf.get_buf()
        if raw is None:
            return False
        data = self._backing.read(self._offset, len(raw))
        if data is None:
            return False
        raw[:] = data
        return True


class MockAsyFramManager:
    def __init__(
        self,
        backing: "MockFramBacking | None" = None,
        out_of_memory: bool = False,
        raise_on_get_chunk: bool = False,
    ) -> None:
        self.backing = MockFramBacking() if backing is None else backing
        self._allocated = 0
        self._out_of_memory = out_of_memory
        self.raise_on_get_chunk = raise_on_get_chunk

    def get_chunk(
        self, size: int, crc: "CRC_Base | None" = None, verify: int = 0, check_length: int = 8
    ) -> "_MockFramChunk | None":
        if self.raise_on_get_chunk:
            raise RuntimeError("simulated FRAM allocation failure")
        crc = CRC_Pass() if crc is None else crc
        full_size = size + crc.length()
        if self._out_of_memory or self._allocated + full_size > len(self.backing.storage):
            return None
        chunk = _MockFramChunk(self.backing, self._allocated, size, crc)
        self._allocated += full_size
        return chunk
