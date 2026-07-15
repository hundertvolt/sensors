"""Generic bit-banged CRC engine (MSB-first, no reflection, no final XOR). CRC8 (poly 0x31, init
0xFF) is Sensirion's documented CRC-8, verified against real datasheet test vectors; CRC16 (poly
0x1021, init 0xFFFF) is CRC-16/CCITT-FALSE; CRC32 (poly 0x04C11DB7, init 0xFFFFFFFF) is
CRC-32/MPEG-2. CRC_Pass is a zero-length no-op.

Shared contract: every public method returns None (or False for run_inc) - never raises - for
invalid input (bad init/poly, buffer too small, insufficient data).
"""

import asyncio
from struct import pack_into


class CRC_Base:
    def __init__(self, num_bytes: int, poly: int | None, fmt: str) -> None:
        # An invalid config (negative num_bytes, poly out of range for the width) silently
        # degrades to pass-through mode rather than raising - see module docstring's contract.
        self.num_bytes = 0 if poly is None or num_bytes < 0 else num_bytes
        self.all_set = 0 if self.num_bytes <= 0 else (1 << (self.num_bytes * 8)) - 1
        self.msb_set = 0 if self.num_bytes <= 0 else 1 << ((self.num_bytes * 8) - 1)
        self.crc_shift = 0 if self.num_bytes <= 0 else 8 * (self.num_bytes - 1)
        self.poly = None if poly is None or self.num_bytes == 0 or not (0 <= poly <= self.all_set) else poly
        self.fmt = fmt
        self.inc_crc: int | None = None
        self.inc_count = 0

    def length(self) -> int:
        # CRC width in bytes; 0 in pass-through mode (CRC_Pass, or any width constructed with
        # poly=None).
        return self.num_bytes

    def _validate_init(self, init: int | None) -> int | None:
        # Defaults to all-bits-1 (the standard "no data seen yet" CRC register state) if unset;
        # rejects anything outside the CRC's valid bit width.
        init = self.all_set if init is None else init
        return init if 0 <= init <= self.all_set else None

    async def _crc(self, buf: bytearray | memoryview, crc: int) -> int:
        # Core polynomial-division loop (see module docstring for the exact algorithm identity per
        # width); yields after every byte so a large buffer can't stall other tasks.
        if self.poly is None:
            return crc
        for c in buf:
            crc ^= c << self.crc_shift  # XOR high byte
            for _ in range(8):
                if crc & self.msb_set:  # Check MSB
                    crc = (crc << 1) ^ self.poly
                else:
                    crc <<= 1
                crc &= self.all_set  # Keep number of bits
            await asyncio.sleep(0)  # Yield control
        return crc

    async def add(self, bytearr: bytearray, init: int | None = None) -> bytearray | None:
        # Appends this buffer's CRC to a new copy of it, ready to send/store.
        if self.poly is None:  # uninitialized or "pass" mode
            return bytearr
        init = self._validate_init(init)
        if init is None:
            return None
        crc = await self._crc(bytearr, init)
        crc_b = bytearray(self.num_bytes)
        try:
            pack_into(self.fmt, crc_b, 0, crc)
            return bytearr + crc_b
        except ValueError:
            return None

    async def check(self, bytearr: bytearray, init: int | None = None) -> bytearray | None:
        # Verifies a buffer's trailing CRC; returns the payload with the CRC stripped on success.
        if self.poly is None:  # uninitialized or "pass" mode
            return bytearr
        init = self._validate_init(init)
        if init is None:
            return None
        if len(bytearr) <= self.num_bytes:
            return None
        if await self._crc(bytearr, init) == 0:
            return bytearr[0 : len(bytearr) - self.num_bytes]
        return None

    # Feeds one chunk of data into an in-progress incremental CRC computation. Call once per
    # chunk until all chunks are fed in, then call check_inc() once to verify.
    async def run_inc(self, bytearr: bytearray | memoryview, init: int | None = None) -> bool:
        if self.inc_crc is None:  # First call, initialize
            self.inc_count = 0
            self.inc_crc = 0 if self.poly is None else self._validate_init(init)
            if self.inc_crc is None:  # Invalid init value
                return False

        if self.poly is not None:  # Only process CRC if enabled
            self.inc_crc = await self._crc(bytearr, self.inc_crc)

        self.inc_count += len(bytearr)
        return True

    async def check_inc(self) -> int | None:
        # Finalizes a run_inc() sequence: returns the payload length (excluding the CRC) on
        # success, None otherwise. Always resets state, so a later sequence starts clean.
        if self.inc_crc is None:
            return None
        valid = self.poly is None or (self.inc_crc == 0 and self.inc_count > self.num_bytes)
        self.inc_crc = None
        return self.inc_count - self.num_bytes if valid else None

    async def add_into(self, buffer: bytearray, size: int, start: int = 0, init: int | None = None) -> int | None:
        # Like add(), but writes the CRC directly into a slice of an existing buffer instead of
        # allocating a new one; returns the total size written (payload + CRC).
        if self.poly is None:  # uninitialized or "pass" mode
            return size
        init = self._validate_init(init)
        if init is None or size <= 0 or start < 0:  # init must be valid, size must be > 0
            return None
        if start + size + self.num_bytes > len(buffer):  # buffer must be sufficient for CRC
            return None
        mv = memoryview(buffer)[start : (start + size + self.num_bytes)]
        crc = await self._crc(mv[0:size], init)
        try:
            pack_into(self.fmt, mv, size, crc)
            return size + self.num_bytes
        except ValueError:
            return None

    async def check_from(
        self, buffer: bytearray, size: int | None = None, start: int = 0, init: int | None = None
    ) -> int | None:
        # Like check(), but verifies in place within a shared buffer; returns just the payload
        # length (excluding the CRC) instead of a copy of the data.
        if self.poly is None:  # uninitialized or "pass" mode
            return len(buffer) if size is None else size
        size = len(buffer) if size is None else size
        init = self._validate_init(init)
        if init is None or size <= 0 or start < 0:  # init must be valid, size must be > 0
            return None
        if start + size > len(buffer) or size <= self.num_bytes:
            return None
        mv = memoryview(buffer)[start : start + size]
        if await self._crc(mv, init) == 0:
            return size - self.num_bytes
        return None


class CRC_Pass(CRC_Base):
    def __init__(self, poly: int | None = None) -> None:
        super().__init__(0, poly, "x")


class CRC8(CRC_Base):
    def __init__(self, poly: int | None = 0x31) -> None:
        super().__init__(1, poly, ">B")


class CRC16(CRC_Base):
    def __init__(self, poly: int | None = 0x1021) -> None:
        super().__init__(2, poly, ">H")


class CRC32(CRC_Base):
    def __init__(self, poly: int | None = 0x04C11DB7) -> None:
        super().__init__(4, poly, ">I")
