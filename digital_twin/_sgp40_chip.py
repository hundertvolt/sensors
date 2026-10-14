"""Twin fake of the Sensirion SGP40 (I2C 0x59): answers asy_sgp40_driver.py's word commands
(serial number, self-test, measure-raw, heater-off) with walked SRAW_VOC ticks, and resets on the I2C general call
(datasheet Table 17). Independent of tests/machine.py's fake I2C."""

import random as _random_module

from _crc8 import word
from _fault_injection import FaultInjector
from _twin_common import Walk, saturating_add

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    class _RandomSource(Protocol):
        # Structural stand-in for the `random` module (the default) or a seeded random.Random -
        # machine.py's configure_random_source() seam. Only these two are ever called here.
        def getrandbits(self, k: int) -> int: ...
        def randint(self, a: int, b: int) -> int: ...

_CMD_SERIAL_NUMBER = b"\x36\x82"  # datasheet Table 15
_CMD_SELF_TEST = b"\x28\x0e"  # datasheet Table 12
_CMD_MEASURE_RAW = b"\x26\x0f"  # "launches/continues the VOC measurement mode" (datasheet 3.1)
_CMD_HEATER_OFF = b"\x36\x15"  # datasheet Table 14: hotplate off, idle mode
_GENERAL_CALL_RESET = b"\x06"  # the byte after the general-call address 0x00 (datasheet Table 17)
# Not datasheet-derived: a typical indoor walk inside the datasheet's SRAW_VOC range 0-65 535 ticks (SGP40 datasheet
# Table 1); the step is a plausibility bound.
_RAW_WALK_DEFAULT = Walk(26000, 34000, 1000)


class SGP40Chip:
    TEST_API = ("corrupt_next", "fault", "heater_offs", "power_cycle", "raw", "resets")

    def __init__(
        self,
        random_source: "_RandomSource | None" = None,
        raw: Walk = _RAW_WALK_DEFAULT,
    ) -> None:
        self._random = random_source if random_source is not None else _random_module
        self.raw = raw  # twin-only test knob: a test may replace the walk
        self._corrupt_next = False
        self.fault = FaultInjector()
        self._pending_reply = bytes(3)
        self._last_cmd: int | None = None
        self._measuring = False  # read by tests only: no reply depends on it
        self.resets = 0  # twin-only test surface: general-call resets the chip took
        self.heater_offs = 0  # twin-only test surface: heater-off commands the chip took
        # Initial value: one draw within the walk's [lo,hi] at construction - every value after this
        # one steps from the last instead (see handle_writeto()'s MEASURE_RAW branch below).
        self._raw = self._random.randint(int(raw.lo), int(raw.hi))

    def _idle(self) -> None:
        self._pending_reply = bytes(3)
        self._measuring = False

    def _maybe_corrupt(self, reply: bytes) -> bytes:
        if not self._corrupt_next:
            return reply
        self._corrupt_next = False
        # Flip the trailing CRC byte of the last word in the reply - a real bus disturbance
        # landing on the checksum is exactly what the driver's own CRC checks must catch.
        return reply[:-1] + bytes([reply[-1] ^ 0xFF])

    def corrupt_next(self) -> None:
        # Twin-only test knob: flips the CRC of the next reply's last word.
        self._corrupt_next = True

    def handle_general_call(self, data: bytes) -> None:
        self.fault.maybe_raise("general_call")
        if data == _GENERAL_CALL_RESET:
            # soft_reset 0x00 0x06 "resetting all devices connected to the same I2C bus" (datasheet Table 17);
            # the gas walk is kept.
            self._idle()
            self.resets = saturating_add(self.resets)

    def handle_readfrom_into(self, nbytes: int) -> bytes:
        self.fault.maybe_hang("readfrom_into")
        self.fault.maybe_raise("readfrom_into", key=self._last_cmd)
        return (self._pending_reply + bytes(nbytes))[:nbytes]

    def handle_writeto(self, data: bytes) -> None:
        self.fault.maybe_hang("writeto")
        key = (data[0] << 8) | data[1] if len(data) >= 2 else None
        self.fault.maybe_raise("writeto", key=key)
        if key is not None:
            self._last_cmd = key
        if data == _CMD_SERIAL_NUMBER:
            word1 = self._random.getrandbits(16)
            word2 = self._random.getrandbits(16)
            reply = word(0x0000) + word(word1) + word(word2)
        elif data == _CMD_SELF_TEST:
            reply = word(0xD400)  # datasheet Table 13: high byte 0xD4 = all tests passed
        elif len(data) == 8 and data[0:2] == _CMD_MEASURE_RAW:
            step = int(self.raw.step)
            self._raw = max(int(self.raw.lo), min(int(self.raw.hi), self._raw + self._random.randint(-step, step)))
            self._measuring = True
            reply = word(self._raw)
        elif data == _CMD_HEATER_OFF:
            self._idle()
            self.heater_offs = saturating_add(self.heater_offs)
            return
        else:
            return  # assumption: the datasheet states no reaction to an unknown command (fidelity row)
        self._pending_reply = self._maybe_corrupt(reply)

    def power_cycle(self) -> None:
        # Twin-only test knob: a re-plugged chip powers up idle ("The idle mode is activated after power-up", Table 2).
        self._idle()
