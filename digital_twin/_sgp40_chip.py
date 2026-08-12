"""Digital-twin chip fake for the Sensirion SGP40 (I2C address 0x59) - answers the exact raw
word-oriented command/reply shapes src/asy_sgp40_driver.py's SGP40_I2C sends (get-serial-number
0x3682, self-test 0x280e, general-call reset via address 0x00 - handled by machine.py's I2C bus
itself, not this class - and measure-raw 0x260f + humidity/temperature compensation words), with
randomized-but-plausible SRAW_VOC ticks instead of a hand-scripted fixture. Verified against
Sensirion's SGP40 datasheet (datasheets/sgp40/, v1.2 - Feb 2022, Table 1): SRAW_VOC's own documented
range is 0-65'535 ticks; this twin's default range (26'000-34'000) is a sensible indoor-clean-air
sub-range of that, matching the values tests/test_asy_sgp40_driver.py's own fixtures already use
(28'000-31'000).

Sits at the same raw-transaction mocking boundary as tests/machine.py's fake I2C, but is a separate,
independent implementation (FINAL_WIRING_PLAN.md's Step 3 - not imported from tests/machine.py).
"""

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
        corrupt_next_reply: bool = False,
    ) -> None:
        self._random = random_source if random_source is not None else _random_module
        self._min_raw = min_raw
        self._max_raw = max_raw
        self._corrupt_next_reply = corrupt_next_reply
        self.fault = FaultInjector()
        self._pending_reply = bytes(3)

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
            raw = self._random.randint(self._min_raw, self._max_raw)
            reply = word(raw)
        else:
            # Unrecognized command - real hardware would simply not respond usefully; keep
            # whatever was already pending rather than raising, matching a real bus's silence.
            return
        self._pending_reply = self._maybe_corrupt(reply)

    def handle_readfrom_into(self, nbytes: int) -> bytes:
        self.fault.maybe_raise("readfrom_into")
        return (self._pending_reply + bytes(nbytes))[:nbytes]
