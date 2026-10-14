"""Twin fake of the Bosch BMP388/BMP390 (I2C 0x77): answers asy_bmp3xx_driver.py's register
protocol with raw ADC bytes that decode, through the real compensation formula inverted by Newton's method, to a
walked pressure and temperature. The calibration block is synthetic (digital_twin/README.md fidelity table)."""

import random as _random_module
import struct

from _fault_injection import FaultInjector
from _twin_common import Walk

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    class _RandomSource(Protocol):
        # Structural stand-in for the `random` module (the default) or a seeded random.Random -
        # machine.py's configure_random_source() seam. Only uniform() is ever called here.
        def uniform(self, a: float, b: float) -> float: ...

_BMP390_CHIP_ID = 0x60  # BMP390's id; BMP384/BMP388 answer 0x50 (fidelity table)

_REGISTER_CHIPID = 0x00
_REGISTER_ERR = 0x02
_REGISTER_STATUS = 0x03
_REGISTER_PRESSUREDATA = 0x04
_REGISTER_EVENT = 0x10
_REGISTER_CONTROL = 0x1B
_REGISTER_OSR = 0x1C
_REGISTER_CONFIG = 0x1F
_REGISTER_CAL_DATA = 0x31
_REGISTER_CMD = 0x7E

_STATUS_CMD_RDY = 0x10
_STATUS_DATA_READY = 0x60
_CONTROL_FORCED_MODE = 0x13
_CMD_SOFT_RESET = 0xB6
_OSR_RESET = 0x02  # OSR's default value (DS001 register map)
_CONFIG_RESET = 0x00  # CONFIG's default value (DS001 register map)
_EVENT_POR_DETECTED = 0x01  # EVENT bit 0: set by a power-up or a soft reset, clear-on-read (DS001 4.3.7)
_FATAL_ERR_BIT = 0x01  # ERR_REG bit 0 fatal_err (DS001 4.3.2)

# Not datasheet-derived: room ranges inside the BMP388's 300-1250 hPa, -40-85 C operating range (DS001 Table 1);
# the step is a plausibility bound.
_TEMP_WALK_DEFAULT = Walk(15.0, 30.0, 1.0)  # degC
_PRESSURE_WALK_DEFAULT = Walk(950.0, 1050.0, 5.0)  # hPa

# T1-T3, P1-P11 raw coefficients: synthetic, chosen so the inverted compensation round-trips across the walk's range
# (fidelity table).
_CAL_RAW = bytes.fromhex("6c6b5014fd9065a041ec05381868101ef4e0fc03fe")


def _decode_calibration(raw: bytes) -> "tuple[tuple[float, float, float], tuple[float, ...]]":
    coeff = struct.unpack("<HHbhhbbHHbbhbb", raw)
    temp_calib = (coeff[0] / 2**-8.0, coeff[1] / 2**30.0, coeff[2] / 2**48.0)
    pressure_calib = (
        (coeff[3] - 2**14.0) / 2**20.0,
        (coeff[4] - 2**14.0) / 2**29.0,
        coeff[5] / 2**32.0,
        coeff[6] / 2**37.0,
        coeff[7] / 2**-3.0,
        coeff[8] / 2**6.0,
        coeff[9] / 2**8.0,
        coeff[10] / 2**15.0,
        coeff[11] / 2**48.0,
        coeff[12] / 2**48.0,
        coeff[13] / 2**65.0,
    )
    return temp_calib, pressure_calib


def _invert_pressure(pressure_calib: "tuple[float, ...]", temperature: float, target_pa: float, guess: float = 8_000_000.0) -> float:
    p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11 = pressure_calib
    po1 = p5 + p6 * temperature + p7 * temperature**2.0 + p8 * temperature**3.0
    lin = p1 + p2 * temperature + p3 * temperature**2.0 + p4 * temperature**3.0
    quad = p9 + p10 * temperature
    x = guess
    for _ in range(40):
        f = po1 + x * lin + (x * x) * quad + p11 * (x**3.0) - target_pa
        fp = lin + 2 * x * quad + 3 * p11 * (x * x)
        if fp == 0:
            break
        x -= f / fp
    return x


def _invert_temperature(t1: float, t2: float, t3: float, target_c: float, guess: float = 8_000_000.0) -> float:
    x = guess
    for _ in range(20):
        pd1 = x - t1
        f = pd1 * t2 + pd1 * pd1 * t3 - target_c
        fp = t2 + 2 * t3 * pd1
        if fp == 0:
            break
        x -= f / fp
    return x


class BMP3XXChip:
    TEST_API = ("fatal_err", "fault", "power_cycle")
    REGISTER_ADDRSIZE = 8  # register-addressed: machine.I2C routes an address-prefixed writeto() here

    def __init__(
        self,
        random_source: "_RandomSource | None" = None,
        temp: Walk = _TEMP_WALK_DEFAULT,
        pressure: Walk = _PRESSURE_WALK_DEFAULT,
    ) -> None:
        self._random = random_source if random_source is not None else _random_module
        self._min_temp_c, self._max_temp_c = temp.lo, temp.hi
        self._min_pressure_hpa, self._max_pressure_hpa = pressure.lo, pressure.hi
        self._temp_step_c, self._pressure_step_hpa = temp.step, pressure.step
        self._power_up()  # the register state a powered-up chip holds
        self.fatal_err = False  # twin-only test knob: ERR_REG reports fatal_err
        self.fault = FaultInjector()
        self._temp_calib, self._pressure_calib = _decode_calibration(_CAL_RAW)
        # One uniform draw within [min,max] at construction; every later value steps from the
        # last (see _trigger_measurement()). The ADC burst stays all-zero until the first forced
        # trigger computes one, as real hardware has nothing to report before its first conversion.
        self._temp_c = self._random.uniform(self._min_temp_c, self._max_temp_c)
        self._pressure_hpa = self._random.uniform(self._min_pressure_hpa, self._max_pressure_hpa)

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _power_up(self) -> None:
        self._event = 0  # the soft reset below raises por_detected, EVENT's power-up value (DS001 register map)
        self._soft_reset()
        self._burst = bytes(6)

    def _soft_reset(self) -> None:
        # 0xB6: "all user configuration settings are overwritten with their default state" (DS001 4.3.22).
        self._status = _STATUS_CMD_RDY
        self._osr = _OSR_RESET
        self._config = _CONFIG_RESET
        self._event |= _EVENT_POR_DETECTED  # por_detected "'1' after device power up or softreset" (DS001 4.3.7)

    def _trigger_measurement(self) -> None:
        self._temp_c = self._clamp(self._temp_c + self._random.uniform(-self._temp_step_c, self._temp_step_c), self._min_temp_c, self._max_temp_c)
        self._pressure_hpa = self._clamp(
            self._pressure_hpa + self._random.uniform(-self._pressure_step_hpa, self._pressure_step_hpa), self._min_pressure_hpa, self._max_pressure_hpa,
        )
        target_temp = self._temp_c
        target_pressure_pa = self._pressure_hpa * 100.0
        t1, t2, t3 = self._temp_calib
        adc_t = _invert_temperature(t1, t2, t3, target_temp)
        adc_p = _invert_pressure(self._pressure_calib, target_temp, target_pressure_pa)
        adc_t_i = max(0, min(0xFFFFFF, round(adc_t)))
        adc_p_i = max(0, min(0xFFFFFF, round(adc_p)))
        self._burst = bytes(
            [
                adc_p_i & 0xFF,
                (adc_p_i >> 8) & 0xFF,
                (adc_p_i >> 16) & 0xFF,
                adc_t_i & 0xFF,
                (adc_t_i >> 8) & 0xFF,
                (adc_t_i >> 16) & 0xFF,
            ],
        )
        self._status = _STATUS_CMD_RDY | _STATUS_DATA_READY

    def handle_readfrom_mem(self, reg_addr: int, nbytes: int) -> bytes:
        self.fault.maybe_hang("readfrom_mem")
        self.fault.maybe_raise("readfrom_mem", key=reg_addr)
        if reg_addr == _REGISTER_CHIPID:
            reply = bytes([_BMP390_CHIP_ID])
        elif _REGISTER_ERR <= reg_addr <= _REGISTER_PRESSUREDATA + 5:
            # ERR_REG, STATUS and the six data bytes are one auto-incremented file (0x02-0x09), so a burst
            # from any of them reads on through the rest, as the driver's 8-byte burst from ERR_REG does.
            block = bytes([_FATAL_ERR_BIT if self.fatal_err else 0x00, self._status]) + self._burst
            reply = block[reg_addr - _REGISTER_ERR :]
        elif reg_addr == _REGISTER_EVENT:
            reply = bytes([self._event])
            self._event = 0  # clear-on-read
        elif reg_addr == _REGISTER_OSR:
            reply = bytes([self._osr])
        elif reg_addr == _REGISTER_CONFIG:
            reply = bytes([self._config])
        elif reg_addr == _REGISTER_CAL_DATA:
            reply = _CAL_RAW
        else:
            reply = bytes(nbytes)
        return (reply + bytes(nbytes))[:nbytes]

    def handle_writeto(self, _data: bytes) -> None:
        # Only the driver's zero-byte presence probe calls plain writeto(); every register access goes through writeto_mem().
        self.fault.maybe_hang("writeto")
        self.fault.maybe_raise("writeto")

    def handle_writeto_mem(self, reg_addr: int, data: bytes) -> None:
        self.fault.maybe_hang("writeto_mem")
        self.fault.maybe_raise("writeto_mem", key=reg_addr)
        if reg_addr == _REGISTER_CONTROL:
            if data and data[0] == _CONTROL_FORCED_MODE:
                self._trigger_measurement()
        elif reg_addr == _REGISTER_OSR:
            self._osr = data[0]
        elif reg_addr == _REGISTER_CONFIG:
            self._config = data[0]
        elif reg_addr == _REGISTER_CMD and data and data[0] == _CMD_SOFT_RESET:
            self._soft_reset()
        # any other register: real hardware would just silently accept/ignore it too.

    def power_cycle(self) -> None:
        # Twin-only test knob: a re-plugged chip powers up; the walk position is kept.
        self._power_up()
