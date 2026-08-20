"""Digital-twin chip fake for the Sensirion SGP40 (I2C 0x59) — answers `asy_sgp40_driver.py`'s exact word-oriented protocol (serial-number/self-test/general-call-reset/measure-raw) with datasheet-ranged random SRAW_VOC ticks.
Independent implementation, not shared with `tests/machine.py`'s fake I2C."""

import random as _random_module

from _crc8 import word
from _fault_injection import FaultInjector

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

_CMD_SERIAL_NUMBER = b"\x36\x82"
_CMD_SELF_TEST = b"\x28\x0e"
_CMD_MEASURE_RAW = b"\x26\x0f"


class Sgp40Chip:
    def __init__(
        self,
        random_source: "Any | None" = None,
        min_raw: int = 26000,
        max_raw: int = 34000,
        raw_step: int = 1000,
        corrupt_next_reply: bool = False,
    ) -> None:
        self._random = random_source if random_source is not None else _random_module
        self._min_raw = min_raw
        self._max_raw = max_raw
        # Not datasheet-derived (min_raw/max_raw are) - see _scd30_chip.py's own *_step comment for
        # the same judgment-call framing, applied here to per-command VOC tick drift.
        self._raw_step = raw_step
        self._corrupt_next_reply = corrupt_next_reply
        self.fault = FaultInjector()
        self._pending_reply = bytes(3)
        # Initial value: one draw within [min_raw,max_raw] at construction - every value after this
        # one steps from the last instead (see handle_writeto()'s MEASURE_RAW branch below).
        self._raw = self._random.randint(self._min_raw, self._max_raw)

    def _maybe_corrupt(self, reply: bytes) -> bytes:
        if not self._corrupt_next_reply:
            return reply
        self._corrupt_next_reply = False
        # Flip the trailing CRC byte of the last word in the reply - a real bus disturbance
        # landing on the checksum is exactly what the driver's own CRC checks must catch.
        return reply[:-1] + bytes([reply[-1] ^ 0xFF])

    def handle_writeto(self, data: bytes) -> None:
        self.fault.maybe_raise("writeto")
        if data == _CMD_SERIAL_NUMBER:
            word1 = self._random.getrandbits(16)
            word2 = self._random.getrandbits(16)
            reply = word(0x0000) + word(word1) + word(word2)
        elif data == _CMD_SELF_TEST:
            reply = word(0xD400)  # datasheet Table 13: high byte 0xD4 = all tests passed
        elif len(data) == 8 and data[0:2] == _CMD_MEASURE_RAW:
            delta = self._random.randint(-self._raw_step, self._raw_step)
            self._raw = max(self._min_raw, min(self._max_raw, self._raw + delta))
            reply = word(self._raw)
        else:
            # Unrecognized command - real hardware would simply not respond usefully; keep
            # whatever was already pending rather than raising, matching a real bus's silence.
            return
        self._pending_reply = self._maybe_corrupt(reply)

    def handle_readfrom_into(self, nbytes: int) -> bytes:
        self.fault.maybe_raise("readfrom_into")
        return (self._pending_reply + bytes(nbytes))[:nbytes]
