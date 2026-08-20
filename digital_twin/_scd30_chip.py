"""Digital-twin chip fake for the Sensirion SCD30 (I2C 0x61) — answers `asy_scd30_driver.py`'s exact word-register protocol with datasheet-ranged random CO2/temperature/humidity and a real RDY-pin IRQ transition.
Persists its five NVM-backed settings only; see `digital_twin/README.md`'s "SCD30 persistence" section."""

import json
import struct

from _crc8 import crc8, word
from _fault_injection import FaultInjector

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

_CMD_CONTINUOUS_MEASUREMENT = 0x0010
_CMD_STOP_CONTINUOUS_MEASUREMENT = 0x0104
_CMD_SET_MEASUREMENT_INTERVAL = 0x4600
_CMD_GET_DATA_READY = 0x0202
_CMD_READ_MEASUREMENT = 0x0300
_CMD_AUTOMATIC_SELF_CALIBRATION = 0x5306
_CMD_SET_FORCED_RECALIBRATION_FACTOR = 0x5204
_CMD_SET_TEMPERATURE_OFFSET = 0x5403
_CMD_SET_ALTITUDE_COMPENSATION = 0x5102
_CMD_SOFT_RESET = 0xD304
_CMD_READ_FIRMWARE_VERSION = 0xD100

_FIRMWARE_VERSION = 0x0342  # plausible fixed value (major.minor as two nibble-pairs) - never checked by the driver


def _pack_measurement_word(raw2: bytes) -> bytes:
    return raw2 + bytes([crc8(raw2)])


def _pack_float(value: float) -> bytes:
    raw = struct.pack(">f", value)
    return _pack_measurement_word(raw[0:2]) + _pack_measurement_word(raw[2:4])


class Scd30Chip:
    def __init__(
        self,
        random_source: "Any | None" = None,
        min_co2: float = 400.0,
        max_co2: float = 2000.0,
        min_temp: float = 15.0,
        max_temp: float = 30.0,
        min_hum: float = 20.0,
        max_hum: float = 70.0,
        co2_step: float = 50.0,
        temp_step: float = 1.0,
        hum_step: float = 3.0,
        measurement_interval_s: int = 2,
        rdy_pin: "Any | None" = None,
        auto_refresh: bool = True,
        state_path: "str | None" = None,
    ) -> None:
        if random_source is None:
            import random as _random_module

            random_source = _random_module
        self._random = random_source
        self._min_co2, self._max_co2 = min_co2, max_co2
        self._min_temp, self._max_temp = min_temp, max_temp
        self._min_hum, self._max_hum = min_hum, max_hum
        # *_step: NOT datasheet-derived (the min/max above are) - a physical-plausibility judgment
        # call bounding how far one reading can move from the last, so successive measurements walk
        # instead of jumping independently around the whole configured range every time.
        self._co2_step, self._temp_step, self._hum_step = co2_step, temp_step, hum_step
        self._measurement_interval_s = measurement_interval_s
        self._ambient_pressure = 0
        self._altitude = 0
        self._temp_offset_raw = 0
        self._asc_enabled = 0
        self._data_ready = False
        self._buffer = bytes(18)
        self._last_cmd: int | None = None
        self._rdy_pin = rdy_pin
        self.fault = FaultInjector()
        self.corrupt_next_measurement = False
        self._timer: Any | None = None
        self.state_path = state_path
        self._load_state()  # may override the *_s/_ambient_pressure/_altitude/_temp_offset_raw/
        # _asc_enabled defaults just set above - never the co2/temp/hum draws below, see class docstring
        # for why those stay unpersisted.
        # Initial value: one uniform draw within [min,max] at construction - every value after this
        # one steps from the last instead (see _produce_new_reading() below).
        self._co2 = self._random.uniform(self._min_co2, self._max_co2)
        self._temp = self._random.uniform(self._min_temp, self._max_temp)
        self._hum = self._random.uniform(self._min_hum, self._max_hum)
        if auto_refresh:
            self._start_timer()

    def _load_state(self) -> None:
        if self.state_path is None:
            return
        try:
            f = open(self.state_path)
        except OSError:
            return  # no persisted state yet - start from factory-fresh settings
        try:
            try:
                data = json.load(f)
            except ValueError:
                return  # malformed/truncated file - leave settings at their factory-fresh defaults
        finally:
            f.close()
        self._measurement_interval_s = data.get("measurement_interval_s", self._measurement_interval_s)
        self._ambient_pressure = data.get("ambient_pressure", self._ambient_pressure)
        self._altitude = data.get("altitude", self._altitude)
        self._temp_offset_raw = data.get("temp_offset_raw", self._temp_offset_raw)
        self._asc_enabled = data.get("asc_enabled", self._asc_enabled)

    def save_state(self) -> None:
        if self.state_path is None:
            return
        with open(self.state_path, "w") as f:
            json.dump(
                {
                    "measurement_interval_s": self._measurement_interval_s,
                    "ambient_pressure": self._ambient_pressure,
                    "altitude": self._altitude,
                    "temp_offset_raw": self._temp_offset_raw,
                    "asc_enabled": self._asc_enabled,
                },
                f,
            )

    def _start_timer(self) -> None:
        from machine import Timer as _Timer

        self._timer = _Timer()
        self._timer.init(
            period=self._measurement_interval_s * 1000,
            mode=_Timer.PERIODIC,
            callback=lambda t: self._produce_new_reading(),
        )

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _produce_new_reading(self) -> None:
        self._co2 = self._clamp(self._co2 + self._random.uniform(-self._co2_step, self._co2_step), self._min_co2, self._max_co2)
        self._temp = self._clamp(self._temp + self._random.uniform(-self._temp_step, self._temp_step), self._min_temp, self._max_temp)
        self._hum = self._clamp(self._hum + self._random.uniform(-self._hum_step, self._hum_step), self._min_hum, self._max_hum)
        self._buffer = _pack_float(self._co2) + _pack_float(self._temp) + _pack_float(self._hum)
        self._data_ready = True
        if self._rdy_pin is not None:
            self._rdy_pin.simulate_edge(1)

    def handle_writeto(self, data: bytes) -> None:
        self.fault.maybe_raise("writeto")
        if len(data) == 2:
            self._last_cmd = (data[0] << 8) | data[1]
            if self._last_cmd == _CMD_STOP_CONTINUOUS_MEASUREMENT:
                pass  # nothing to model - readback for this command doesn't exist
            elif self._last_cmd == _CMD_SOFT_RESET:
                pass  # no persistent chip-side state modeled that a reset would need to clear
            return
        if len(data) == 5:
            cmd = (data[0] << 8) | data[1]
            arg = (data[2] << 8) | data[3]
            if cmd == _CMD_SET_MEASUREMENT_INTERVAL:
                self._measurement_interval_s = arg
                if self._timer is not None:
                    self._start_timer()  # re-arm at the new cadence, matching real hardware
            elif cmd == _CMD_AUTOMATIC_SELF_CALIBRATION:
                self._asc_enabled = 1 if arg else 0
            elif cmd == _CMD_CONTINUOUS_MEASUREMENT:
                self._ambient_pressure = arg
            elif cmd == _CMD_SET_ALTITUDE_COMPENSATION:
                self._altitude = arg
            elif cmd == _CMD_SET_TEMPERATURE_OFFSET:
                self._temp_offset_raw = arg
            elif cmd == _CMD_SET_FORCED_RECALIBRATION_FACTOR:
                pass  # volatile readback always reports 400 regardless (real hardware quirk)
            self._last_cmd = cmd
            return
        # Unrecognized shape - real hardware would just not respond usefully.

    def handle_readfrom_into(self, nbytes: int) -> bytes:
        self.fault.maybe_raise("readfrom_into")
        cmd = self._last_cmd
        if cmd == _CMD_GET_DATA_READY:
            reply = word(1 if self._data_ready else 0)
        elif cmd == _CMD_READ_MEASUREMENT:
            reply = self._buffer
            if self.corrupt_next_measurement:
                self.corrupt_next_measurement = False
                reply = reply[:2] + bytes([reply[2] ^ 0xFF]) + reply[3:]
            self._data_ready = False
            if self._rdy_pin is not None:
                self._rdy_pin.simulate_edge(0)
        elif cmd == _CMD_SET_MEASUREMENT_INTERVAL:
            reply = word(self._measurement_interval_s)
        elif cmd == _CMD_AUTOMATIC_SELF_CALIBRATION:
            reply = word(self._asc_enabled)
        elif cmd == _CMD_CONTINUOUS_MEASUREMENT:
            reply = word(self._ambient_pressure)
        elif cmd == _CMD_SET_ALTITUDE_COMPENSATION:
            reply = word(self._altitude)
        elif cmd == _CMD_SET_TEMPERATURE_OFFSET:
            reply = word(self._temp_offset_raw)
        elif cmd == _CMD_SET_FORCED_RECALIBRATION_FACTOR:
            reply = word(400)  # always reports 400 after any "power cycle" - see class docstring
        elif cmd == _CMD_READ_FIRMWARE_VERSION:
            reply = word(_FIRMWARE_VERSION)
        else:
            reply = bytes(3)
        return (reply + bytes(nbytes))[:nbytes]
