"""Digital-twin chip fake for the Sensirion SCD30 (I2C 0x61) — answers `asy_scd30_driver.py`'s exact word-register protocol with datasheet-ranged random CO2/temperature/humidity and a real RDY-pin IRQ transition.
Reports the temperature less its set offset, as the chip does. Persists its five NVM-backed settings only; see `digital_twin/README.md`'s "SCD30 persistence" section."""

import json
import struct

from _crc8 import crc8, word
from _fault_injection import FaultInjector
from _twin_common import Walk

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    from machine import Timer  # type-only: the runtime import of Timer stays inside _start_timer()

    class _RandomSource(Protocol):
        # Structural stand-in for the `random` module (the default) or a seeded random.Random -
        # machine.py's configure_random_source() seam. Only uniform() is ever called here.
        def uniform(self, a: float, b: float) -> float: ...

    class _RdyPin(Protocol):
        # Structural stand-in for machine.py's Pin (and any test's own pin fake) - only the
        # twin-only simulate_edge() is ever called here.
        def simulate_edge(self, new_value: int) -> None: ...

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
# The argument commands whose value the chip keeps in NVM (Interface Description 1.4.1, 1.4.3, 1.4.6-1.4.8).
_NVM_ARG_COMMANDS = (
    _CMD_CONTINUOUS_MEASUREMENT,
    _CMD_SET_MEASUREMENT_INTERVAL,
    _CMD_SET_ALTITUDE_COMPENSATION,
    _CMD_SET_FORCED_RECALIBRATION_FACTOR,
    _CMD_AUTOMATIC_SELF_CALIBRATION,
    _CMD_SET_TEMPERATURE_OFFSET,
)

_CO2_WALK_DEFAULT = Walk(400.0, 2000.0, 50.0)  # ppm
_TEMP_WALK_DEFAULT = Walk(15.0, 30.0, 1.0)  # degC
_HUM_WALK_DEFAULT = Walk(20.0, 70.0, 3.0)  # %RH

_FIRMWARE_VERSION = 0x0342  # plausible fixed value (major.minor as two nibble-pairs) - never checked by the driver


def _pack_measurement_word(raw2: bytes) -> bytes:
    return raw2 + bytes([crc8(raw2)])


def _pack_float(value: float) -> bytes:
    raw = struct.pack(">f", value)
    return _pack_measurement_word(raw[0:2]) + _pack_measurement_word(raw[2:4])


class Scd30Chip:
    def __init__(
        self,
        random_source: "_RandomSource | None" = None,
        co2: Walk = _CO2_WALK_DEFAULT,
        temp: Walk = _TEMP_WALK_DEFAULT,
        hum: Walk = _HUM_WALK_DEFAULT,
        measurement_interval_s: int = 2,
        rdy_pin: "_RdyPin | None" = None,
        *,
        auto_refresh: bool = True,
        state_path: "str | None" = None,
    ) -> None:
        if random_source is None:
            import random as _random_module

            random_source = _random_module
        self._random = random_source
        self._min_co2, self._max_co2 = co2.lo, co2.hi
        self._min_temp, self._max_temp = temp.lo, temp.hi
        self._min_hum, self._max_hum = hum.lo, hum.hi
        # Each walk's step: NOT datasheet-derived (lo/hi are) - a physical-plausibility judgment call
        # bounding how far one reading can move from the last, so successive measurements walk
        # instead of jumping independently around the whole configured range every time.
        self._co2_step, self._temp_step, self._hum_step = co2.step, temp.step, hum.step
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
        # Test surface, not chip behaviour: one count per NVM-writing command frame the fake applies.
        self.nvm_writes = 0
        self._timer: Timer | None = None
        self.state_path = state_path
        self._load_state()  # may override the *_s/_ambient_pressure/_altitude/_temp_offset_raw/
        # _asc_enabled defaults just set above - never the co2/temp/hum draws below, which the
        # class docstring explains staying unpersisted.

        # One uniform draw within each walk's [lo,hi] at construction; every later value steps from the
        # last (see _produce_new_reading()).
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
            callback=lambda _t: self._produce_new_reading(),
        )

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _produce_new_reading(self) -> None:
        self._co2 = self._clamp(self._co2 + self._random.uniform(-self._co2_step, self._co2_step), self._min_co2, self._max_co2)
        self._temp = self._clamp(self._temp + self._random.uniform(-self._temp_step, self._temp_step), self._min_temp, self._max_temp)
        self._hum = self._clamp(self._hum + self._random.uniform(-self._hum_step, self._hum_step), self._min_hum, self._max_hum)
        # The walk is the sensor's own temperature; the chip reports it less the offset (datasheets/scd30 Low Power
        # Mode, "Set temperature offset": the offset is the output's difference from ambient), as the driver's gate expects.
        self._buffer = _pack_float(self._co2) + _pack_float(self._temp - self._temp_offset_raw / 100) + _pack_float(self._hum)
        self._data_ready = True
        if self._rdy_pin is not None:
            self._rdy_pin.simulate_edge(1)

    def handle_writeto(self, data: bytes) -> None:
        self.fault.maybe_hang("writeto")
        self.fault.maybe_raise("writeto")
        if len(data) == 2:
            self._last_cmd = (data[0] << 8) | data[1]
            if self._last_cmd == _CMD_STOP_CONTINUOUS_MEASUREMENT:
                self.nvm_writes += 1  # the measurement status is kept in NVM (Interface Description 1.4.1-1.4.2)
            elif self._last_cmd == _CMD_SOFT_RESET:
                pass  # no persistent chip-side state modeled that a reset would need to clear
            return
        if len(data) == 5:
            cmd = (data[0] << 8) | data[1]
            arg = (data[2] << 8) | data[3]
            if cmd in _NVM_ARG_COMMANDS:
                self.nvm_writes += 1
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
        self.fault.maybe_hang("readfrom_into")
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
