"""Generic bit-banged CRC engine (MSB-first, no reflection, no final XOR): CRC8 (Sensirion's
documented CRC-8), CRC16 (CRC-16/CCITT-FALSE), CRC32 (CRC-32/MPEG-2), plus CRCPass (a zero-length no-op).
"""
# CRC8 poly 0x31/init 0xFF; CRC16 0x1021/0xFFFF; CRC32 0x04C11DB7/0xFFFFFFFF. Every public method
# returns None/False on invalid input rather than raising, except add()/check(), which allocate and
# let MemoryError propagate. run_inc()/check_inc() hold per-instance state - never share one.

# Zero-padding limitation inherent to this CRC class (CRC linearity; agent, 2026-07-15): a register at 0 stays 0 through further 0x00
# bytes, so check()/check_from()/check_inc() can't detect trailing zero-padding past the buffer's
# true end - callers must supply an accurate length.

import asyncio
from struct import pack_into

from micropython import const

_WORD_BYTES = const(2)  # the widest register the one-word loop runs: its intermediates stay below 2**17


class CRCBase:
    def __init__(self, num_bytes: int, poly: int | None, fmt: str) -> None:
        # An invalid config (negative num_bytes, poly out of range for the width) silently
        # degrades to pass-through mode rather than raising - see module docstring's contract.
        self._num_bytes = 0 if poly is None or num_bytes < 0 else num_bytes
        self._all_set = 0 if self._num_bytes <= 0 else (1 << (self._num_bytes * 8)) - 1
        self._msb_set = 0 if self._num_bytes <= 0 else 1 << ((self._num_bytes * 8) - 1)
        self._crc_shift = 0 if self._num_bytes <= 0 else 8 * (self._num_bytes - 1)
        self._poly = None if poly is None or self._num_bytes == 0 or not (0 <= poly <= self._all_set) else poly
        self._fmt = fmt
        self._inc_crc: int | None = None
        self._inc_count = 0

    async def _crc(self, buf: bytearray | memoryview, crc: int, poly: int) -> int:
        # Core polynomial-division loop (see the module docstring for the algorithm identity per
        # width), over the polynomial the caller has already checked; yields after every byte so a large buffer
        # can't stall other tasks.
        if self._poly is None:
            return crc
        if self._num_bytes > _WORD_BYTES:
            return await self._crc_wide(buf, crc, poly)
        for c in buf:
            crc ^= c << self._crc_shift  # XOR high byte
            for _ in range(8):
                if crc & self._msb_set:  # Check MSB
                    crc = (crc << 1) ^ poly
                else:
                    crc <<= 1
                crc &= self._all_set  # Keep number of bits
            await asyncio.sleep(0)  # Yield control
        return crc

    # A register wider than 16 bits runs as two words: rp2 small ints stop at 2**30 - 1, so a 32-bit
    # register would allocate a heap int on every bit step (agent, 2026-09-29).
    async def _crc_wide(self, buf: bytearray | memoryview, crc: int, poly: int) -> int:
        hi_bits = self._num_bytes * 8 - 16
        hi_mask = (1 << hi_bits) - 1
        hi_msb = 1 << (hi_bits - 1)
        shift = hi_bits - 8
        poly_hi = poly >> 16
        poly_lo = poly & 0xFFFF
        hi = crc >> 16
        lo = crc & 0xFFFF
        for c in buf:
            hi ^= c << shift
            for _ in range(8):
                carry = lo >> 15
                lo = (lo << 1) & 0xFFFF
                if hi & hi_msb:
                    hi = (((hi << 1) | carry) & hi_mask) ^ poly_hi
                    lo ^= poly_lo
                else:
                    hi = ((hi << 1) | carry) & hi_mask
            await asyncio.sleep(0)  # Yield control
        return (hi << 16) | lo

    def _validate_init(self, init: int | None) -> int | None:
        # Defaults to all-bits-1 (the standard "no data seen yet" CRC register state) if unset;
        # rejects anything outside the CRC's valid bit width.
        init = self._all_set if init is None else init
        return init if 0 <= init <= self._all_set else None

    async def add(self, bytearr: bytearray, init: int | None = None) -> bytearray | None:
        # Appends this buffer's CRC to a new copy of it, ready to send/store.
        if self._poly is None:  # uninitialized or "pass" mode
            return bytearr
        init = self._validate_init(init)
        if init is None:
            return None
        crc = await self._crc(bytearr, init, self._poly)
        crc_b = bytearray(self._num_bytes)
        try:
            pack_into(self._fmt, crc_b, 0, crc)
            return bytearr + crc_b
        except ValueError:
            return None

    async def add_into(self, buffer: bytearray, size: int, start: int = 0, init: int | None = None) -> int | None:
        # Like add(), but writes the CRC directly into a slice of an existing buffer instead of
        # allocating a new one; returns the total size written (payload + CRC).
        if size <= 0 or start < 0 or start + size + self._num_bytes > len(buffer):
            return None
        if self._poly is None:  # uninitialized or "pass" mode
            return size
        init = self._validate_init(init)
        if init is None:
            return None
        mv = memoryview(buffer)[start : (start + size + self._num_bytes)]
        crc = await self._crc(mv[0:size], init, self._poly)
        try:
            pack_into(self._fmt, mv, size, crc)
            return size + self._num_bytes
        except ValueError:
            return None

    async def check(self, bytearr: bytearray, init: int | None = None) -> bytearray | None:
        # Verifies a buffer's trailing CRC; returns the payload with the CRC stripped on success.
        if self._poly is None:  # uninitialized or "pass" mode
            return bytearr
        init = self._validate_init(init)
        if init is None:
            return None
        if len(bytearr) <= self._num_bytes:
            return None
        if await self._crc(bytearr, init, self._poly) == 0:
            return bytearr[0 : len(bytearr) - self._num_bytes]
        return None

    async def check_from(
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
        mv = memoryview(buffer)[start : start + size]
        if await self._crc(mv, init, self._poly) == 0:
            return size - self._num_bytes
        return None

    async def check_inc(self) -> int | None:
        # Finalizes a run_inc() sequence: returns the payload length (excluding the CRC) on
        # success, None otherwise. Always resets state, so a later sequence starts clean.
        if self._inc_crc is None:
            return None
        valid = self._poly is None or (self._inc_crc == 0 and self._inc_count > self._num_bytes)
        self._inc_crc = None
        return self._inc_count - self._num_bytes if valid else None

    def length(self) -> int:
        # CRC width in bytes; 0 in pass-through mode (CRCPass, or any width constructed with
        # poly=None).
        return self._num_bytes

    # Feeds one chunk of data into an in-progress incremental CRC computation. Call once per
    # chunk until all chunks are fed in, then call check_inc() once to verify.
    async def run_inc(self, bytearr: bytearray | memoryview, init: int | None = None) -> bool:
        if self._inc_crc is None:  # First call, initialize
            self._inc_count = 0
            self._inc_crc = 0 if self._poly is None else self._validate_init(init)
            if self._inc_crc is None:  # Invalid init value
                return False

        if self._poly is not None:  # Only process CRC if enabled
            self._inc_crc = await self._crc(bytearr, self._inc_crc, self._poly)

        self._inc_count += len(bytearr)
        return True


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
