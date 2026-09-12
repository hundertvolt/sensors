"""Pluggable frame codecs for asy_uart_driver.py: Framing_Pass (byte-identical no-op, the default)
and Framing_COBS (delimiter framing, no 0x00 anywhere in an encoded frame).
Every method returns None on invalid input or a failed allocation - never raises."""
# Encode order on write is build -> CRC -> encode -> delimiter, the exact reverse on read, so the
# CRC keeps its position underneath the codec (SPECIFICATION.md Part J.3). Selecting a delimited
# codec changes the bytes on the wire and is a coordinated flag day - UART_C_PORT_CHANGELOG.md A11.

import asyncio

from micropython import const

COBS_DELIMITER = const(0x00)

_COBS_MAX_RUN = const(0xFF)  # a code byte of 0xFF means "254 data bytes, no zero follows"
_COBS_RUN_LEN = const(254)


class Framing_Base:
    # Pass-through by construction: every method below is the identity, and a subclass overrides
    # only what it actually changes. Mirrors crc_checks.py's CRC_Base/CRC_Pass split, so a caller
    # can hold either family behind one dispatch table.
    def __init__(self, max_frame: int = 0, run_length: int = 0, trailer: int = 0) -> None:
        # Parameterized like crc_checks.py's CRC_Base, so a subclass supplies constants rather than
        # arithmetic: run_length is the longest span one code byte can describe (0 = no code bytes
        # at all) and trailer the delimiter bytes appended after it.
        self.max_frame = max(max_frame, 0)
        self.run_length = max(run_length, 0)
        self.trailer = max(trailer, 0)
        self.allocations = 0  # long-lived scratch allocations; 1 at most, never per frame

    def ready(self) -> bool:  # False once a scratch allocation has failed (B2.8)
        return True

    def is_delimited(self) -> bool:
        return False

    def delimiter(self) -> int | None:
        return None

    def overhead(self, size: int) -> int:
        # Integer arithmetic only: no float division on a target without an FPU.
        if self.run_length <= 0:
            return self.trailer
        return (size // self.run_length) + 1 + self.trailer

    def max_encoded(self, size: int) -> int:
        return size + self.overhead(size)

    def _checked(self, buf: bytearray, size: int) -> bool:
        return self.ready() and 0 <= size <= len(buf)

    async def encode_into(self, buf: bytearray, size: int) -> memoryview | None:
        # Returns the bytes to transmit. The pass-through case is a view of the caller's own
        # buffer, so the default costs no copy at all; a delimited codec returns a view of its own
        # long-lived scratch instead, which is why this is a view rather than a length.
        if not self._checked(buf, size):
            return None
        return memoryview(buf)[0:size]

    async def decode_from(self, buf: bytearray, size: int) -> int | None:
        # Decodes in place and returns the decoded length. In-place is safe for every codec here:
        # decoding never grows a frame.
        if not self._checked(buf, size):
            return None
        return size


class Framing_Pass(Framing_Base):
    # The explicit no-op, named so a construction site states the choice rather than relying on a
    # default - the same reason crc_checks.py spells out CRC_Pass.
    def __init__(self) -> None:
        super().__init__(0, run_length=0, trailer=0)  # no code bytes, no delimiter, no overhead


class Framing_COBS(Framing_Base):
    # Consistent Overhead Byte Stuffing: the encoded form provably contains no 0x00, so a single
    # 0x00 delimiter frames it unambiguously whatever the payload, CRC or UID happen to be.
    def __init__(self, max_frame: int) -> None:
        super().__init__(max_frame, run_length=_COBS_RUN_LEN, trailer=1)
        # One long-lived scratch, sized for the worst case from max_frame - never per frame (B2.5).
        self._scratch: bytearray | None = None
        if max_frame > 0:
            try:
                self._scratch = bytearray(self.max_encoded(self.max_frame))
                self.allocations = 1
            except (MemoryError, OverflowError):
                self._scratch = None

    def ready(self) -> bool:
        return self._scratch is not None

    def is_delimited(self) -> bool:
        return True

    def delimiter(self) -> int | None:
        return COBS_DELIMITER

    def _checked(self, buf: bytearray, size: int) -> bool:
        return self.ready() and 0 <= size <= len(buf) and size <= self.max_frame

    async def encode_into(self, buf: bytearray, size: int) -> memoryview | None:
        if not self._checked(buf, size) or self._scratch is None:
            return None
        out = self._scratch
        code_index = 0
        out[0] = 0  # placeholder, overwritten with the run length once the run ends
        length = 1
        code = 1
        for index in range(size):
            byte = buf[index]
            if byte != COBS_DELIMITER:
                out[length] = byte
                length += 1
                code += 1
                if code != _COBS_MAX_RUN:
                    continue
            out[code_index] = code
            code_index = length
            length += 1
            code = 1
            await asyncio.sleep(0)  # a maximal train is 255 runs; yield so nothing else stalls
        out[code_index] = code
        out[length] = COBS_DELIMITER
        return memoryview(out)[0 : length + 1]

    async def decode_from(self, buf: bytearray, size: int) -> int | None:
        # `buf` holds one encoded frame *without* its delimiter - the read loop strips it, since
        # the delimiter is what told the loop the frame had ended in the first place.
        if not self._checked(buf, size):
            return None
        read = 0
        written = 0
        while read < size:
            code = buf[read]
            if code == COBS_DELIMITER:  # a zero code byte cannot occur in a well-formed frame
                return None
            read += 1
            end = read + code - 1
            if end > size:  # B2.4: validated before it is followed, never walked off the buffer
                return None
            while read < end:
                buf[written] = buf[read]
                written += 1
                read += 1
            if code != _COBS_MAX_RUN and read < size:
                buf[written] = COBS_DELIMITER
                written += 1
            await asyncio.sleep(0)
        return written
