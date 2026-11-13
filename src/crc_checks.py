"""One native CRC engine (MSB-first, no reflection, no final XOR) for widths of 1 to 4 bytes: CRC8 (Sensirion's
documented CRC-8), CRC16 (CRC-16/CCITT-FALSE), CRC32 (CRC-32/MPEG-2), plus CRCPass (a zero-length no-op).
"""
# CRC8 poly 0x31/init 0xFF; CRC16 0x1021/0xFFFF; CRC32 0x04C11DB7/0xFFFFFFFF. Every public method
# returns None/False on invalid input rather than raising, except add()/check(), which allocate and
# let MemoryError propagate. An instance keeps no state between calls.

# Zero-padding limitation inherent to this CRC class (CRC linearity; agent, 2026-07-15): a register at 0 stays 0 through
# further 0x00 bytes, so check()/check_from() can't detect trailing zero-padding past the buffer's true end
# - callers must supply an accurate length.

from struct import pack_into

import micropython
from micropython import const

_MAX_BYTES = const(4)  # the widest register the engine runs: its word is 32 bits on silicon


@micropython.viper
def _crc(buf: object, start: int, end: int, crc: uint, poly: uint, shift: int) -> uint:
    # Native code over buf[start:end], whose bounds the caller checked (ptr8 checks none); shift is the width less 8. The
    # word is 64-bit on the Unix port and 32-bit on silicon: masked to the width, both give the same value.
    p = ptr8(buf)  # type: ignore[arg-type]
    top = uint(0x80) << shift
    for i in range(start, end):
        crc ^= uint(p[i]) << shift
        for _ in range(8):
            crc = (crc << 1) ^ poly if crc & top else crc << 1
    return crc & ((top << 1) - 1)


class CRCBase:
    def __init__(self, num_bytes: int, poly: int | None, fmt: str) -> None:
        # An invalid config (num_bytes outside 0..4, poly out of range for the width) silently
        # degrades to pass-through mode rather than raising - see module docstring's contract.
        self._num_bytes = 0 if poly is None or not 0 <= num_bytes <= _MAX_BYTES else num_bytes
        self._all_set = 0 if self._num_bytes <= 0 else (1 << (self._num_bytes * 8)) - 1
        self._crc_shift = 0 if self._num_bytes <= 0 else 8 * (self._num_bytes - 1)
        self._poly = None if poly is None or self._num_bytes == 0 or not (0 <= poly <= self._all_set) else poly
        self._fmt = fmt

    def _validate_init(self, init: int | None) -> int | None:
        # Defaults to all-bits-1 (the standard "no data seen yet" CRC register state) if unset;
        # rejects anything outside the CRC's valid bit width.
        init = self._all_set if init is None else init
        return init if 0 <= init <= self._all_set else None

    def add(self, bytearr: bytearray, init: int | None = None) -> bytearray | None:
        # Appends this buffer's CRC to a new copy of it, ready to send/store.
        if self._poly is None:  # uninitialized or "pass" mode
            return bytearr
        init = self._validate_init(init)
        if init is None:
            return None
        crc = _crc(bytearr, 0, len(bytearr), init, self._poly, self._crc_shift)
        crc_b = bytearray(self._num_bytes)
        pack_into(self._fmt, crc_b, 0, crc)
        return bytearr + crc_b

    def add_into(self, buffer: bytearray, size: int, start: int = 0, init: int | None = None) -> int | None:
        # Like add(), but writes the CRC directly into a slice of an existing buffer instead of
        # allocating a new one; returns the total size written (payload + CRC).
        if size <= 0 or start < 0 or start + size + self._num_bytes > len(buffer):
            return None
        if self._poly is None:  # uninitialized or "pass" mode
            return size
        init = self._validate_init(init)
        if init is None:
            return None
        pack_into(self._fmt, buffer, start + size, _crc(buffer, start, start + size, init, self._poly, self._crc_shift))
        return size + self._num_bytes

    def check(self, bytearr: bytearray, init: int | None = None) -> bytearray | None:
        # Verifies a buffer's trailing CRC; returns the payload with the CRC stripped on success.
        if self._poly is None:  # uninitialized or "pass" mode
            return bytearr
        init = self._validate_init(init)
        if init is None:
            return None
        if len(bytearr) <= self._num_bytes:
            return None
        if _crc(bytearr, 0, len(bytearr), init, self._poly, self._crc_shift) == 0:
            return bytearr[0 : len(bytearr) - self._num_bytes]
        return None

    def check_from(
        self, buffer: bytearray, size: int | None = None, start: int = 0, init: int | None = None,
    ) -> int | None:
        # Like check(), but verifies in place within a shared buffer; returns just the payload
        # length (excluding the CRC) instead of a copy of the data.
        size = len(buffer) if size is None else size
        if size <= self._num_bytes or start < 0 or start + size > len(buffer):
            return None
        if self._poly is None:  # uninitialized or "pass" mode
            return size
        init = self._validate_init(init)
        if init is None:
            return None
        if _crc(buffer, start, start + size, init, self._poly, self._crc_shift) == 0:
            return size - self._num_bytes
        return None

    def length(self) -> int:
        # CRC width in bytes; 0 in pass-through mode (CRCPass, or any width constructed with
        # poly=None).
        return self._num_bytes


class CRCPass(CRCBase):
    def __init__(self, poly: int | None = None) -> None:
        super().__init__(0, poly, "x")


class CRC8(CRCBase):
    def __init__(self, poly: int | None = 0x31) -> None:
        super().__init__(1, poly, ">B")


class CRC16(CRCBase):
    def __init__(self, poly: int | None = 0x1021) -> None:
        super().__init__(2, poly, ">H")


class CRC32(CRCBase):
    def __init__(self, poly: int | None = 0x04C11DB7) -> None:
        super().__init__(4, poly, ">I")
