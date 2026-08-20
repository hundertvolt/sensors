"""Digital-twin chip fake for the Bosch BMP388/BMP390 (I2C 0x77) — answers `asy_bmp3xx_driver.py`'s register-addressed protocol with raw ADC bytes that decode, through the real (Newton's-method-inverted) cubic compensation formula, to a chosen pressure/temperature.
Calibration block is hand-picked, not real-chip data; see `digital_twin/README.md`'s "Known gaps" section."""

import struct

from _fault_injection import FaultInjector

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

_BMP390_CHIP_ID = 0x60

_REGISTER_CHIPID = 0x00
_REGISTER_ERR = 0x02
_REGISTER_STATUS = 0x03
_REGISTER_PRESSUREDATA = 0x04
_REGISTER_CONTROL = 0x1B
_REGISTER_OSR = 0x1C
_REGISTER_CONFIG = 0x1F
_REGISTER_CAL_DATA = 0x31
_REGISTER_CMD = 0x7E

_STATUS_CMD_RDY = 0x10
_STATUS_DATA_READY = 0x60
_CONTROL_FORCED_MODE = 0x13
_CMD_SOFT_RESET = 0xB6

# T1 T2 T3 P1 P2 P3 P4 P5 P6 P7 P8 P9 P10 P11 raw values - see digital_twin/README.md's "Known
# gaps" section for how these were chosen/verified.
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


class Bmp3xxChip:
    def __init__(
        self,
        random_source: "Any | None" = None,
        min_temp_c: float = 15.0,
        max_temp_c: float = 30.0,
        min_pressure_hpa: float = 950.0,
        max_pressure_hpa: float = 1050.0,
        temp_step_c: float = 1.0,
        pressure_step_hpa: float = 5.0,
    ) -> None:
        if random_source is None:
            import random as _random_module

            random_source = _random_module
        self._random = random_source
        self._min_temp_c, self._max_temp_c = min_temp_c, max_temp_c
        self._min_pressure_hpa, self._max_pressure_hpa = min_pressure_hpa, max_pressure_hpa
        # Not datasheet-derived (the min/max above are) - see _scd30_chip.py's own *_step comment
        # for the same judgment-call framing, applied here to weather-scale pressure/temperature.
        self._temp_step_c, self._pressure_step_hpa = temp_step_c, pressure_step_hpa
        self._status = _STATUS_CMD_RDY
        self._osr = 0
        self._config = 0
        self._burst = bytes(6)
        self.fault = FaultInjector()
        self._temp_calib, self._pressure_calib = _decode_calibration(_CAL_RAW)
        # Initial value: one uniform draw within [min,max] at construction - every value after this
        # one steps from the last instead (see _trigger_measurement() below). The ADC burst itself
        # stays at its all-zero default until the first forced-mode trigger actually computes one -
        # unchanged from before this walk existed (real hardware has nothing to report before its
        # first conversion either).
        self._temp_c = self._random.uniform(self._min_temp_c, self._max_temp_c)
        self._pressure_hpa = self._random.uniform(self._min_pressure_hpa, self._max_pressure_hpa)

    def _clamp(self, value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))

    def _trigger_measurement(self) -> None:
        self._temp_c = self._clamp(self._temp_c + self._random.uniform(-self._temp_step_c, self._temp_step_c), self._min_temp_c, self._max_temp_c)
        self._pressure_hpa = self._clamp(
            self._pressure_hpa + self._random.uniform(-self._pressure_step_hpa, self._pressure_step_hpa), self._min_pressure_hpa, self._max_pressure_hpa
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
            ]
        )
        self._status = _STATUS_CMD_RDY | _STATUS_DATA_READY

    def handle_writeto(self, data: bytes) -> None:
        # asy_i2c_driver.py's I2CDevice.setup()/_probe_for_device() writes zero bytes to every I2C
        # device at construction time to check for an ACK, before any register access - real
        # hardware ACKs this fine regardless of protocol family. Found during baseline
        # verification: this chip fake only had handle_writeto_mem() (matching
        # its real register-addressed protocol), so the twin's I2C dispatch (machine.py's own
        # writeto() -> device.handle_writeto()) raised AttributeError on every real BMP3xx boot,
        # repeatedly failing/restarting its whole reader task. Nothing else in this codebase's own
        # BMP3xx driver ever calls plain writeto() (every real register access goes through
        # writeto_mem()), so this only needs to answer the empty-probe shape.
        self.fault.maybe_raise("writeto")

    def handle_writeto_mem(self, reg_addr: int, data: bytes) -> None:
        self.fault.maybe_hang("writeto_mem")
        self.fault.maybe_raise("writeto_mem")
        if reg_addr == _REGISTER_CONTROL:
            if data and data[0] == _CONTROL_FORCED_MODE:
                self._trigger_measurement()
        elif reg_addr == _REGISTER_OSR:
            self._osr = data[0]
        elif reg_addr == _REGISTER_CONFIG:
            self._config = data[0]
        elif reg_addr == _REGISTER_CMD:
            if data and data[0] == _CMD_SOFT_RESET:
                self._status = _STATUS_CMD_RDY
        # any other register: real hardware would just silently accept/ignore it too.

    def handle_readfrom_mem(self, reg_addr: int, nbytes: int) -> bytes:
        self.fault.maybe_hang("readfrom_mem")
        self.fault.maybe_raise("readfrom_mem")
        if reg_addr == _REGISTER_CHIPID:
            reply = bytes([_BMP390_CHIP_ID])
        elif reg_addr == _REGISTER_ERR:
            reply = bytes([0x00])
        elif reg_addr == _REGISTER_STATUS:
            reply = bytes([self._status])
        elif reg_addr == _REGISTER_PRESSUREDATA:
            reply = self._burst
        elif reg_addr == _REGISTER_OSR:
            reply = bytes([self._osr])
        elif reg_addr == _REGISTER_CONFIG:
            reply = bytes([self._config])
        elif reg_addr == _REGISTER_CAL_DATA:
            reply = _CAL_RAW
        else:
            reply = bytes(nbytes)
        return (reply + bytes(nbytes))[:nbytes]
