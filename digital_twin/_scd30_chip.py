"""Twin fake of the Sensirion SCD30 (I2C 0x61): answers asy_scd30_driver.py's word-command protocol
with walked CO2/T/RH, checked argument CRCs and an RDY edge per measurement. The NVM-backed settings and the measuring
status persist to a state file (digital_twin/README.md "SCD30 persistence")."""

import json
import os
import random as _random_module
import struct
from collections import namedtuple

from _crc8 import crc8, word
from _fault_injection import FaultInjector
from _twin_common import Walk, saturating_add

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import NamedTuple, Protocol

    from machine import Timer  # type-only: machine passes the simulation Timer in through timer_factory

    class _RandomSource(Protocol):
        # Structural stand-in for the `random` module (the default) or a seeded random.Random -
        # machine.py's configure_random_source() seam. Only uniform() is ever called here.
        def uniform(self, a: float, b: float) -> float: ...

    class _RdyPin(Protocol):
        # Structural stand-in for machine.py's Pin (and any test's own pin fake) - only the
        # twin-only simulate_edge() is ever called here.
        def simulate_edge(self, new_value: int) -> None: ...

    class SCD30Nvm(NamedTuple):
        # The NVM-held settings a chip powers up with (Interface Description 1.4.1, 1.4.3).
        measurement_interval_s: int
        measuring: bool

else:
    SCD30Nvm = namedtuple("SCD30Nvm", ("measurement_interval_s", "measuring"))

_CMD_CONTINUOUS_MEASUREMENT = 0x0010  # Interface Description 1.4.1
_CMD_STOP_CONTINUOUS_MEASUREMENT = 0x0104  # 1.4.2
_CMD_SET_MEASUREMENT_INTERVAL = 0x4600  # 1.4.3
_CMD_GET_DATA_READY = 0x0202  # 1.4.4
_CMD_READ_MEASUREMENT = 0x0300  # 1.4.5
_CMD_AUTOMATIC_SELF_CALIBRATION = 0x5306  # 1.4.6
_CMD_SET_FORCED_RECALIBRATION_FACTOR = 0x5204  # 1.4.6, "Set Forced Recalibration value (FRC)"
_CMD_SET_TEMPERATURE_OFFSET = 0x5403  # 1.4.7
_CMD_SET_ALTITUDE_COMPENSATION = 0x5102  # 1.4.8
_CMD_READ_FIRMWARE_VERSION = 0xD100  # 1.4.9
_CMD_SOFT_RESET = 0xD304  # 1.4.10
# The argument commands whose value the chip keeps in NVM (Interface Description 1.4.1, 1.4.3, 1.4.6-1.4.8).
_NVM_ARG_COMMANDS = (
    _CMD_CONTINUOUS_MEASUREMENT,
    _CMD_SET_MEASUREMENT_INTERVAL,
    _CMD_SET_ALTITUDE_COMPENSATION,
    _CMD_SET_FORCED_RECALIBRATION_FACTOR,
    _CMD_AUTOMATIC_SELF_CALIBRATION,
    _CMD_SET_TEMPERATURE_OFFSET,
)
_INTERVAL_MIN_S = 2  # "Available range: [2 ... 1800]" (1.4.3)
_INTERVAL_MAX_S = 1800
_FRC_MIN_PPM = 400  # "400 ppm <= cref(CO2) <= 2000 ppm" (1.4.6 FRC)
_FRC_MAX_PPM = 2000
_FRC_POWER_UP_PPM = 400  # "After repowering the sensor, the command will return the standard reference value of 400 ppm"

# Not datasheet-derived: room ranges inside the datasheet's 400-10 000 ppm, -40-70 C, 0-100 %RH (SCD30 datasheet
# Tables 1-3); the steps are plausibility bounds.
_CO2_WALK_DEFAULT = Walk(400.0, 2000.0, 50.0)  # ppm
_TEMP_WALK_DEFAULT = Walk(15.0, 30.0, 1.0)  # degC
_HUM_WALK_DEFAULT = Walk(20.0, 70.0, 3.0)  # %RH

# Not datasheet-derived: a factory SCD30 is idle until 0x0010; the twin starts from a provisioned unit so every boot
# produces readings - pass measuring=False to model an unprovisioned sensor. The 2 s interval is the initial one (1.4.3).
_PROVISIONED_NVM = SCD30Nvm(2, True)

_FIRMWARE_VERSION = 0x0342  # plausible fixed value (major.minor as two nibble-pairs) - never checked by the driver
_STATE_SETTINGS = ("measurement_interval_s", "ambient_pressure", "altitude", "temp_offset_raw", "asc_enabled")


def _pack_float(value: float) -> bytes:
    raw = struct.pack(">f", value)
    return _pack_measurement_word(raw[0:2]) + _pack_measurement_word(raw[2:4])


def _pack_measurement_word(raw2: bytes) -> bytes:
    return raw2 + bytes([crc8(raw2)])


class SCD30Chip:
    TEST_API = ("bad_crc_commands", "co2", "corrupt_next", "fault", "hum", "nvm_writes", "power_cycle", "rdy_stuck_high", "save_state", "temp")

    def __init__(
        self,
        random_source: "_RandomSource | None" = None,
        co2: Walk = _CO2_WALK_DEFAULT,
        temp: Walk = _TEMP_WALK_DEFAULT,
        hum: Walk = _HUM_WALK_DEFAULT,
        rdy_pin: "_RdyPin | None" = None,
        nvm: SCD30Nvm = _PROVISIONED_NVM,
        *,
        timer_factory: "Callable[[], Timer] | None" = None,
        state_path: "str | None" = None,
    ) -> None:
        self._random = random_source if random_source is not None else _random_module
        # Twin-only test knob: a test may replace a walk, e.g. step 0 for a constant CO2.
        self.co2, self.temp, self.hum = co2, temp, hum
        self._measurement_interval_s = nvm.measurement_interval_s
        self._measuring = nvm.measuring
        self._ambient_pressure = 0
        self._altitude = 0
        self._temp_offset_raw = 0
        self._asc_enabled = 0
        self._frc_reference = _FRC_POWER_UP_PPM
        self._data_ready = False
        self._buffer = bytes(18)
        self._last_cmd: int | None = None
        self._rdy_pin = rdy_pin
        self.fault = FaultInjector()
        self._corrupt_next = False
        self.rdy_stuck_high = False  # twin-only test knob: RDY reads high while no new measurement completes
        # Twin-only test surface: the NVM-writing commands the fake applied, and the argument frames it refused.
        self.nvm_writes = 0
        self.bad_crc_commands = 0
        self._timer_factory = timer_factory  # None: no measurement Timer, readings only through _produce_new_reading()
        self._timer: Timer | None = None
        self.state_path = state_path
        self._load_state()  # the NVM settings and the measuring status; the walks stay unpersisted
        # One uniform draw within each walk's [lo,hi] at construction; every later value steps from the
        # last (see _produce_new_reading()).
        self._co2 = self._random.uniform(co2.lo, co2.hi)
        self._temp = self._random.uniform(temp.lo, temp.hi)
        self._hum = self._random.uniform(hum.lo, hum.hi)
        self._start_timer()

    def _apply(self, cmd: int, arg: int) -> bool:
        # One CRC-checked argument command; False when the fake ignores it (an assumption for each out-of-range case).
        if cmd == _CMD_SET_MEASUREMENT_INTERVAL:
            if not _INTERVAL_MIN_S <= arg <= _INTERVAL_MAX_S:
                return False
            self._measurement_interval_s = arg
            if self._timer is not None:
                self._start_timer()  # re-arm at the new cadence, matching real hardware
        elif cmd == _CMD_AUTOMATIC_SELF_CALIBRATION:
            self._asc_enabled = 1 if arg else 0
        elif cmd == _CMD_CONTINUOUS_MEASUREMENT:
            self._measuring = True
            self._ambient_pressure = arg
        elif cmd == _CMD_SET_ALTITUDE_COMPENSATION:
            self._altitude = arg
        elif cmd == _CMD_SET_TEMPERATURE_OFFSET:
            self._temp_offset_raw = arg
        elif cmd == _CMD_SET_FORCED_RECALIBRATION_FACTOR:
            if not _FRC_MIN_PPM <= arg <= _FRC_MAX_PPM:
                return False
            self._frc_reference = arg
        return True

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _count_nvm_write(self) -> None:
        self.nvm_writes = saturating_add(self.nvm_writes)

    def _drive_rdy(self, level: int) -> None:
        if self._rdy_pin is not None:
            self._rdy_pin.simulate_edge(1 if self.rdy_stuck_high else level)

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
                self._not_loaded("json")
                return
        finally:
            f.close()
        if not isinstance(data, dict):
            self._not_loaded("shape")
            return
        current = (self._measurement_interval_s, self._ambient_pressure, self._altitude, self._temp_offset_raw, self._asc_enabled)
        settings = [data.get(key, value) for key, value in zip(_STATE_SETTINGS, current)]  # noqa: B905 - MicroPython zip() rejects strict=
        measuring = data.get("measuring", self._measuring)
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in settings) or not isinstance(measuring, bool):
            self._not_loaded("type")
            return
        self._measurement_interval_s, self._ambient_pressure, self._altitude, self._temp_offset_raw, self._asc_enabled = settings
        self._measuring = measuring

    def _not_loaded(self, reason: str) -> None:
        # Missing, malformed, truncated or mistyped file: the factory-fresh chip (owner, 2026-08-13), and a line saying so.
        print("SCD30 state", self.state_path, "not loaded (" + reason + "): starting from factory-fresh settings")

    def _power_up(self) -> None:
        # Soft reset: "the same state as after powering up" (Interface Description 1.4.10); NVM settings survive.
        self._data_ready = False
        self._buffer = bytes(18)
        self._frc_reference = _FRC_POWER_UP_PPM
        self._drive_rdy(0)
        self._start_timer()

    def _produce_new_reading(self) -> None:
        if not self._measuring:
            return  # stopped (0x0104, or an unprovisioned chip): no measurement, no RDY edge
        if self.rdy_stuck_high:
            self._drive_rdy(1)  # the line is stuck, and no measurement completes behind it
            return
        co2, temp, hum = self.co2, self.temp, self.hum
        self._co2 = self._clamp(self._co2 + self._random.uniform(-co2.step, co2.step), co2.lo, co2.hi)
        self._temp = self._clamp(self._temp + self._random.uniform(-temp.step, temp.step), temp.lo, temp.hi)
        self._hum = self._clamp(self._hum + self._random.uniform(-hum.step, hum.step), hum.lo, hum.hi)
        # The walk is the sensor's own temperature; the chip reports it less the offset (datasheets/scd30 Low Power
        # Mode, "Set temperature offset"). The offset shifts RH too, by a formula no datasheet gives: RH is reported as walked.
        self._buffer = _pack_float(self._co2) + _pack_float(self._temp - self._temp_offset_raw / 100) + _pack_float(self._hum)
        self._data_ready = True
        self._drive_rdy(1)

    def _start_timer(self) -> None:
        if self._timer_factory is None:
            return
        if self._timer is None:  # built once; init() replaces the previous schedule
            self._timer = self._timer_factory()
        self._timer.init(
            period=self._measurement_interval_s * 1000,
            mode=self._timer.PERIODIC,
            callback=lambda _t: self._produce_new_reading(),
        )

    def corrupt_next(self) -> None:
        # Twin-only test knob: flips the CRC of the next measurement read-out's first word.
        self._corrupt_next = True

    def handle_readfrom_into(self, nbytes: int) -> bytes:
        self.fault.maybe_hang("readfrom_into")
        self.fault.maybe_raise("readfrom_into", key=self._last_cmd)
        cmd = self._last_cmd
        if cmd == _CMD_GET_DATA_READY:
            reply = word(1 if self._data_ready else 0)
        elif cmd == _CMD_READ_MEASUREMENT:
            reply = self._buffer
            if self._corrupt_next:
                self._corrupt_next = False
                reply = reply[:2] + bytes([reply[2] ^ 0xFF]) + reply[3:]
            self._data_ready = False
            self._drive_rdy(0)
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
            reply = word(self._frc_reference)  # "the most recently used reference ... after repowering ... 400 ppm" (1.4.6)
        elif cmd == _CMD_READ_FIRMWARE_VERSION:
            reply = word(_FIRMWARE_VERSION)
        else:
            reply = bytes(3)
        return (reply + bytes(nbytes))[:nbytes]

    def handle_writeto(self, data: bytes) -> None:
        self.fault.maybe_hang("writeto")
        self.fault.maybe_raise("writeto", key=(data[0] << 8) | data[1] if len(data) >= 2 else None)
        if len(data) == 2:
            self._last_cmd = (data[0] << 8) | data[1]
            if self._last_cmd == _CMD_STOP_CONTINUOUS_MEASUREMENT:
                self._measuring = False
                self._count_nvm_write()  # the measurement status is kept in NVM (Interface Description 1.4.1-1.4.2)
            elif self._last_cmd == _CMD_SOFT_RESET:
                self._power_up()
            return
        if len(data) == 5:
            cmd = (data[0] << 8) | data[1]
            arg = (data[2] << 8) | data[3]
            self._last_cmd = cmd
            if data[4] != crc8(data[2:4]):
                # Assumption: the datasheet states no reaction to a wrong argument CRC; the fake ignores the command
                # (fidelity row).
                self.bad_crc_commands = saturating_add(self.bad_crc_commands)
                return
            if self._apply(cmd, arg) and cmd in _NVM_ARG_COMMANDS:
                self._count_nvm_write()
            return
        # Unrecognized shape - real hardware would just not respond usefully.

    def power_cycle(self) -> None:
        # Twin-only test knob: a re-plugged chip powers up with its NVM settings and the walk kept.
        self._power_up()

    def save_state(self) -> None:
        if self.state_path is None:
            return
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(
                {
                    "measurement_interval_s": self._measurement_interval_s,
                    # Persistence of the pressure value itself is an assumption (Interface Description 1.4.1 names only
                    # the status as NVM); BACKLOG real-hardware row.
                    "ambient_pressure": self._ambient_pressure,
                    "altitude": self._altitude,
                    "temp_offset_raw": self._temp_offset_raw,
                    "asc_enabled": self._asc_enabled,
                    "measuring": self._measuring,
                },
                f,
            )
        os.rename(tmp, self.state_path)  # atomic, POSIX rename(2) (extmod/vfs_posix.c:340-349): a cut save keeps the old file
