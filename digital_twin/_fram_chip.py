"""Twin fake of an SPI FRAM: answers asy_fram_driver.py's opcode/CS-session protocol, independent
of tests/_fram_chip_fake.py. It frames each transaction by write() pairing, not by CS (fidelity table); its size and
RDID come from machine.py's table."""

import os

from _fault_injection import FaultInjector
from _twin_common import fill_buffer, saturating_add

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import overload

    _Slice = slice[int | None, int | None, int | None]


_OPCODE_WREN = 0x06
_OPCODE_WRDI = 0x04
_OPCODE_RDSR = 0x05
_OPCODE_WRSR = 0x01
_OPCODE_READ = 0x03
_OPCODE_WRITE = 0x02
_OPCODE_RDID = 0x9F

_WEL_BIT = 0x02
_OVERRUN_MIN_READ = 32  # ports/rp2/machine_spi.c DMA threshold, the one SPI path that can raise (pinned equal to machine._SPI_DMA_MIN_SIZE)
_WRITES_AT_MAX_KEYS = 2048  # an erase's 256-byte units plus every chunk's two block addresses fit

_ADDR_16BIT_MAX = 0xFFFF  # matches src/asy_fram_driver.py's own _ADDR_16BIT_MAX exactly: a chip at
# or under this size gets a 2-byte address (3-byte opcode+address header); a larger chip (dev's
# 256KB MB85RS2MTA) gets a 3-byte address (4-byte header) - _setup_addr_buffer()'s own
# _ADDR_BUF_24BIT/_ADDR_BUF_16BIT split.

_SAVE_CHUNK_SIZE = 512  # bytes per chunk streamed to disk: no one contiguous allocation for the whole image (README "FRAM persistence")

_LOAD_CHUNK_CHARS = 1024  # hex chars per chunk in _load_state() - read-side mirror of the above.

_PAGE_SIZE = 4096  # bytes per page of the chip's memory: a 256KB part as one bytearray needs a contiguous
# run a fragmented test heap may lack with most of it free (digital_twin/README.md, "FRAM persistence").


class _PagedMemory:
    """The chip's memory as fixed-size pages, read and written like the bytearray it replaces."""

    def __init__(self, size: int) -> None:
        self._size = size
        self._pages = [bytearray(min(_PAGE_SIZE, size - start)) for start in range(0, size, _PAGE_SIZE)]

    def __eq__(self, other: object) -> bool:
        if isinstance(other, _PagedMemory):
            return self._pages == other._pages
        return NotImplemented

    if TYPE_CHECKING:

        @overload
        def __getitem__(self, key: int) -> int: ...
        @overload
        def __getitem__(self, key: "_Slice") -> bytearray: ...

    def __getitem__(self, key: "int | _Slice") -> "int | bytearray":
        if isinstance(key, int):
            if not 0 <= key < self._size:
                raise IndexError("FRAM address out of range")
            return self._pages[key // _PAGE_SIZE][key % _PAGE_SIZE]
        start, stop = self._bounds(key)
        stop = min(stop, self._size)  # a read past the end comes back short, as a bytearray slice does
        out = bytearray()
        while start < stop:
            page, offset = divmod(start, _PAGE_SIZE)
            n = min(stop - start, _PAGE_SIZE - offset)
            out += self._pages[page][offset : offset + n]
            start += n
        return out

    def __iter__(self) -> "Iterator[int]":
        for page in self._pages:
            yield from page

    def __len__(self) -> int:
        return self._size

    def __setitem__(self, key: "int | _Slice", value: "int | bytes | bytearray | memoryview") -> None:
        if isinstance(key, int):
            if not isinstance(value, int):
                raise TypeError("a FRAM address takes one byte value")
            if not 0 <= key < self._size:
                raise IndexError("FRAM address out of range")
            self._pages[key // _PAGE_SIZE][key % _PAGE_SIZE] = value
            return
        if isinstance(value, int):
            raise TypeError("a FRAM slice takes bytes")
        start, stop = self._bounds(key)
        if stop - start != len(value) or stop > self._size:
            raise IndexError("a FRAM write must fit the chip and keep its length")
        done = 0
        while done < len(value):
            page, offset = divmod(start + done, _PAGE_SIZE)
            n = min(len(value) - done, _PAGE_SIZE - offset)
            self._pages[page][offset : offset + n] = value[done : done + n]
            done += n

    def _bounds(self, key: "_Slice") -> "tuple[int, int]":
        if key.step not in (None, 1):
            raise ValueError("FRAM memory slices take no step")
        start = 0 if key.start is None else key.start
        stop = self._size if key.stop is None else key.stop
        if start < 0 or stop < 0:
            raise IndexError("FRAM memory takes no negative addresses")
        return start, max(start, stop)

    def zero(self) -> None:
        # Blanks the chip in place, one page-sized zero block at a time: no allocation of the whole size.
        blank = bytes(min(_PAGE_SIZE, self._size))
        for page in self._pages:
            page[:] = memoryview(blank)[: len(page)]


def _header_size(prefix: str) -> "int | None":
    # The "size" a state file's header names, or None when it names none.
    idx = prefix.find('"size": ')
    if idx == -1:
        return None
    digits = prefix[idx + len('"size": ') :].split(",", 1)[0].strip()
    return int(digits) if digits.isdigit() else None


class FRAMChip:
    TEST_API = ("drop_next_wren", "fault", "rdid_once", "silent", "write_count", "writes_at", "writes_at_dropped")

    def __init__(self, size: int, rdid_response: bytes, state_path: "str | None" = None) -> None:
        self.size = size
        self.state_path = state_path
        self.status = 0x00
        self.rdid_response = rdid_response
        # rp2's SPI raises only on a reading transfer (ports/rp2/machine_spi.c:312-315): only readinto() takes a fault.
        self.fault = FaultInjector(raisable_ops=("readinto",))
        self.drop_next_wren = 0  # twin-only test knob: each WREN while > 0 leaves WEL clear and counts down
        self.rdid_once: bytes | None = None  # twin-only test knob: answered by the next RDID only, then cleared
        # Twin-only test knob: a deselected or lost chip - every write() changes nothing, every readinto() reads 0x00
        # (SO is High-Z, MB85RS64V datasheet p10; the MISO pad's reset pull-down reads 0, RP2040 datasheet Table 341).
        self.silent = False
        # Twin-only test surface: the payload WRITEs that reached the array (more than one data byte), and by start address.
        self.write_count = 0
        self.writes_at: dict[int, int] = {}
        self.writes_at_dropped = 0  # writes at a new address once writes_at holds _WRITES_AT_MAX_KEYS
        self.memory = _PagedMemory(size)
        self._pending_op: int | None = None
        self._pending_addr: int | None = None
        self._load_state()

    def _count_write(self, addr: int) -> None:
        self.write_count = saturating_add(self.write_count)
        if addr in self.writes_at:
            self.writes_at[addr] = saturating_add(self.writes_at[addr])
        elif len(self.writes_at) < _WRITES_AT_MAX_KEYS:
            self.writes_at[addr] = 1
        else:
            self.writes_at_dropped = saturating_add(self.writes_at_dropped)

    def _decode_addr(self, data: bytes) -> int:
        # The address counter rolls over past the most significant address (MB85RS64V datasheet p9, READ/WRITE).
        if self.size > _ADDR_16BIT_MAX:
            return ((data[1] << 16) | (data[2] << 8) | data[3]) % self.size
        return ((data[1] << 8) | data[2]) % self.size

    def _header_len(self) -> int:
        # Opcode plus a 2-byte address, or a 3-byte one past 64 KB (asy_fram_driver.py's _setup_addr_buffer()).
        return 4 if self.size > _ADDR_16BIT_MAX else 3

    def _load_state(self) -> None:
        if self.state_path is None:
            return
        try:
            f = open(self.state_path)
        except OSError:
            return  # no persisted state yet - start from a blank chip, matches a factory-fresh part
        try:
            # Hand-parsed, not json.load() - same contiguous-allocation risk as save_state()'s own
            # fixed bug, avoided here on the read path too (see _SAVE_CHUNK_SIZE's own comment).
            header = f.read(128)  # the '{"size": N, "memory_hex": "' prefix is always well under this
            marker = '"memory_hex": "'
            idx = header.find(marker)
            if idx == -1:
                self._not_loaded("marker")
                return
            if _header_size(header[:idx]) != self.size:  # missing, malformed or the other chip's size
                self._not_loaded("size")
                return
            pending = header[idx + len(marker) :]
            pos = 0
            while pos < self.size:
                chunk = f.read(_LOAD_CHUNK_CHARS)
                piece = pending + chunk
                pending = ""
                if not piece:
                    break
                end = piece.find('"')
                done = end != -1
                if done:
                    piece = piece[:end]
                if len(piece) % 2:  # a hex byte pair straddled this chunk boundary - hold the
                    pending = piece[-1:]  # trailing nibble for the next round instead of mis-pairing
                    piece = piece[:-1]
                if piece:
                    n = min(len(piece) // 2, self.size - pos)
                    self.memory[pos : pos + n] = bytearray.fromhex(piece[: n * 2])
                    pos += n
                if done or not chunk:
                    break
            if pos < self.size:
                self._not_loaded("truncated")
        finally:
            f.close()

    def _not_loaded(self, reason: str) -> None:
        # A state file that exists but cannot be loaded says so: the factory-fresh chip, in place (owner, 2026-08-13).
        print("FRAM state", self.state_path, "not loaded (" + reason + "): starting from a factory-fresh chip")
        self.memory.zero()

    def _read_wrapped(self, buf: "bytearray | memoryview", addr: int) -> None:
        # A read past the end wraps to address 0, as the chip's counter does; at most two copies per wrap.
        done = 0
        while done < len(buf):
            n = min(len(buf) - done, self.size - addr)
            buf[done : done + n] = self.memory[addr : addr + n]
            done += n
            addr = 0

    @property
    def _wel(self) -> bool:
        return bool(self.status & _WEL_BIT)

    def _write_wrapped(self, addr: int, data: bytes) -> None:
        done = 0
        while done < len(data):
            n = min(len(data) - done, self.size - addr)
            self.memory[addr : addr + n] = data[done : done + n]
            done += n
            addr = 0

    # _write_value is what the bus puts on MOSI while clocking a read out, so a device-side fake
    # never reads it; named for SPI.readinto()'s positional-only second argument. The buffer type
    # matches that signature too - the body uses only len() and buf[:], valid on a memoryview.
    def readinto(self, buf: "bytearray | memoryview", _write_value: int = 0x00) -> None:
        self.fault.maybe_hang("readinto")
        if len(buf) >= _OVERRUN_MIN_READ:  # a shorter read never raises on rp2, so a queued fault waits for a long one
            self.fault.maybe_raise("readinto", key=self._pending_op)
        if self.silent:
            fill_buffer(buf, b"")
            return
        if self._pending_op == _OPCODE_READ and self._pending_addr is not None:
            self._read_wrapped(buf, self._pending_addr)
        elif self._pending_op == _OPCODE_RDSR:
            fill_buffer(buf, bytes([self.status]))
        elif self._pending_op == _OPCODE_RDID:
            answer = self.rdid_response if self.rdid_once is None else self.rdid_once
            self.rdid_once = None
            # "SO holds the output state of the last bit in 32-bit Device ID until CS is risen" (both FRAM datasheets, p10).
            fill_buffer(buf, answer, 0xFF if answer[-1] & 0x01 else 0x00)
        else:
            fill_buffer(buf, b"")
        self._pending_op = None
        self._pending_addr = None

    def save_state(self) -> None:
        if self.state_path is None:
            return
        # Streamed by hand (not json.dump()) - see _SAVE_CHUNK_SIZE's own comment above for why a
        # single-shot bytes(self.memory).hex() is a real fragmentation risk. The written file is
        # still exactly the JSON object _load_state() expects (hex digits never need escaping).
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            f.write(f'{{"size": {self.size}, "memory_hex": "')
            for start in range(0, self.size, _SAVE_CHUNK_SIZE):
                f.write(self.memory[start : start + _SAVE_CHUNK_SIZE].hex())
            f.write('"}')
        os.rename(tmp, self.state_path)  # atomic, POSIX rename(2) (extmod/vfs_posix.c:340-349): a cut save keeps the old image

    def write(self, buf: bytes) -> None:
        self.fault.maybe_hang("write")
        if self.silent:
            return
        data = bytes(buf)
        if self._pending_op == _OPCODE_WRITE and self._pending_addr is not None:
            # data phase of a previously-opened WRITE (opcode+address arrived in the prior call)
            if self._wel:
                self._write_wrapped(self._pending_addr, data)
                if len(data) > 1:  # a chunk copy, a clear or an erase unit, never a one-byte status write
                    self._count_write(self._pending_addr)
            self.status &= ~_WEL_BIT  # WEL auto-clears at the CS rising edge after WRITE recognition
            self._pending_op = None
            self._pending_addr = None
            return
        opcode = data[0]
        if opcode == _OPCODE_WREN:
            if self.drop_next_wren > 0:
                self.drop_next_wren -= 1
            else:
                self.status |= _WEL_BIT
        elif opcode == _OPCODE_WRDI:
            self.status &= ~_WEL_BIT
        elif opcode == _OPCODE_WRSR:
            if self._wel:
                self.status = (data[1] & ~_WEL_BIT) | (self.status & _WEL_BIT)
            self.status &= ~_WEL_BIT  # WEL auto-clears at the CS rising edge after WRSR recognition
        elif opcode == _OPCODE_WRITE:
            if len(data) > self._header_len():
                raise ValueError("FRAM fake: opcode, address and data in one write() - the fake frames by write() pairing (fidelity table)")
            self._pending_op = _OPCODE_WRITE
            self._pending_addr = self._decode_addr(data)
        elif opcode == _OPCODE_READ:
            self._pending_op = _OPCODE_READ
            self._pending_addr = self._decode_addr(data)
        elif opcode == _OPCODE_RDSR:
            self._pending_op = _OPCODE_RDSR
        elif opcode == _OPCODE_RDID:
            self._pending_op = _OPCODE_RDID
