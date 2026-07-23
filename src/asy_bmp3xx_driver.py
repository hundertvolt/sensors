"""Async I2C driver for the Bosch BMP384/BMP388/BMP390 pressure/temperature sensor (Sparkfun
breakout; forced-mode single-shot reads only). BMP3XX_I2C is the sensor-protocol layer (register
access, calibration, compensation math); BMP3xx_Reader is the asyncio task/config/data-distribution
layer built on base_classes.py's SensorReaderConfig, the shared shape used by every *_Reader class.

Verified against Bosch's BST-BMP388-DS001/BST-BMP384-DS003 datasheets (datasheets/bmp3xx/) and the
official BMP3_SensorAPI reference driver - not training memory. See BACKLOG.md's
"asy_bmp3xx_driver.py -> src/" entry for the full design/verification history.

Shared contract: BMP3XX_I2C methods raise on any hardware/protocol failure rather than returning a
sentinel, matching asy_i2c_driver.py's own bus-fault carve-out; set_pressure_oversampling()/
set_temperature_oversampling()/set_filter_coefficient() additionally raise ValueError outside the
sensor's own discrete oversampling/filter-coefficient domain.
"""

import asyncio
import time
from collections import namedtuple
from struct import unpack

from machine import Timer
from micropython import const

import math_helpers
from asy_i2c_driver import I2C, I2CDevice
from base_classes import Lockable, LockedValue, SensorReaderConfig
from config_manager import make_dict, name_cfg

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from asy_fram_manager import AsyFramManager


_BMP388_CHIP_ID = const(0x50)  # also reported by BMP384 (datasheet sec 4.3.1); BMP390 differs
_BMP390_CHIP_ID = const(0x60)

_REGISTER_CHIPID = const(0x00)
_REGISTER_ERR = const(0x02)
_REGISTER_STATUS = const(0x03)
_REGISTER_PRESSUREDATA = const(0x04)  # burst-read base; the 6-byte burst covers temp data too
_REGISTER_CONTROL = const(0x1B)
_REGISTER_OSR = const(0x1C)
_REGISTER_CONFIG = const(0x1F)
_REGISTER_CAL_DATA = const(0x31)
_REGISTER_CMD = const(0x7E)

_ERR_CMD = const(0x02)  # ERR_REG bit 1 "cmd_err": command execution failed (datasheet sec 4.3.2)

_STATUS_CMD_RDY = const(0x10)  # STATUS bit 4: command decoder ready for a new CMD (sec 4.3.3)
_STATUS_DATA_READY = const(0x60)  # STATUS bits 5+6: drdy_press | drdy_temp (sec 4.3.3)

_CMD_RDY_TIMEOUT_MS = const(50)  # cmd_rdy clears near-instantly outside an in-flight command
_MEAS_TIMEOUT_MS = const(300)  # datasheet sec 3.9.2: max ~129ms at x32/x32 osr; generous margin

_OSR_SETTINGS = (1, 2, 4, 8, 16, 32)  # pressure and temperature oversampling settings
# IIR filter coefficients (datasheet sec 4.3.20's CONFIG register: encoding index -> 2^index - 1,
# not a power of two). Cross-checked against Bosch's reference driver, the Linux kernel IIO driver,
# and both datasheets - see BACKLOG.md's "asy_bmp3xx_driver.py" entry for the full verification.
_IIR_SETTINGS = (0, 1, 3, 7, 15, 31, 63, 127)

_MIN_TRIGGER_SECS = const(1)
_MAX_TRIGGER_SECS = const(3600)

_VAL_SI = const((("SampleInterv", "int", 2, _MIN_TRIGGER_SECS, _MAX_TRIGGER_SECS, None),))
_VAL_POV = const((("PressOvers", "int", 1, 1, 32, None),))
_VAL_TOV = const((("TempOvers", "int", 1, 1, 32, None),))
_VAL_FC = const((("FiltCoeff", "int", 0, 0, 127, None),))
_VAL_PO = const((("PressOffset", "float", 0.0, -500.0, 500.0, None),))
_VAL_TO = const((("TempOffset", "float", 0.0, -10.0, 10.0, None),))
_VAL_SLO = const((("SeaLevelOffs", "float", 0.0, -1000.0, 5000.0, None),))
_VAL_ATM = const((("MeanAtmTemp", "float", 15.0, -50.0, 50.0, None),))

_NAME = const("BMP3XX")
BMP3XX = namedtuple("BMP3XX", ("Pres", "Temp", "SLPres", "TS"))
if TYPE_CHECKING:
    BMPResults = tuple[float | None, float | None, int | None]  # pressure, temperature, timestamp


class BMP3xx_Reader(SensorReaderConfig):
    def __init__(
        self,
        i2c: I2C,
        address: int = 0x77,
        trigger_sec: int = 1,
        max_i2c_err: int = 5,
        cfg_path: str = "",
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        super().__init__(
            BMP3XX(None, None, None, None),
            max_i2c_err,
            _NAME,
            _VAL_SI + _VAL_POV + _VAL_TOV + _VAL_FC + _VAL_PO + _VAL_TO + _VAL_SLO + _VAL_ATM,
            cfg_path=cfg_path,
            fram=fram,
            history_length=history_length,
            debug=debug,
        )
        self.bmp = BMP3XX_I2C(i2c, address=address)
        self.base_trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_event = asyncio.ThreadSafeFlag()
        # Bare Timer() is valid on rp2 (id defaults to -1) despite the installed stub package
        # requiring a positional id - a stub inaccuracy, not a code bug; see BACKLOG.md's Timer
        # finding.
        self.trigger_timer = Timer()
        self.trigger_period = LockedValue(int(trigger_sec))
        self.trigger_counter = 0

    def start_asy_read(self) -> asyncio.Task[bool]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_loop())

    def start_asy_trigger(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._base_trigger())

    def start_timer(self) -> None:
        self.trigger_timer.init(
            period=1000,
            mode=Timer.PERIODIC,
            callback=lambda b: self.base_trigger_event.set(),
        )

    def stop_timer(self) -> None:
        self.trigger_timer.deinit()

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_read, self.start_asy_trigger]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return [self.start_timer]

    async def set_trigger_secs(self, value: int | float) -> None:
        try:
            # int(float('inf'))/int(float('-inf')) raise OverflowError, not ValueError - confirmed
            # against the real MicroPython Unix-port interpreter; +-inf is a legitimate int | float
            # input this must degrade cleanly for, not crash on.
            trigger_secs = int(value)
            if not (_MIN_TRIGGER_SECS <= trigger_secs <= _MAX_TRIGGER_SECS):
                raise ValueError(f"trigger interval must be between {_MIN_TRIGGER_SECS} and {_MAX_TRIGGER_SECS} seconds")
        except (TypeError, ValueError, OverflowError) as e:
            await self.pr.err_s(_NAME, "Error setting trigger interval:", e, errno=21)
            return
        await self.trigger_period.set_value(trigger_secs)

    async def get_data(self) -> BMP3XX:
        # Narrows _get_meas_data()'s generic "NamedTuple" to this Reader's concrete BMP3XX;
        # typing.cast() isn't usable (no runtime presence on MicroPython) so this identity return
        # does the same job - see DRIVER_SPEC.md's get_data() narrowing convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data)

    async def get_error_counter(self) -> dict[str, dict[str, int | list[int] | list[str]]]:
        return await self.pr.get_log(_NAME)

    async def _read_sensor_dict(self) -> dict[str, int | float | str | bool | None]:
        ret: dict[str, int | float | str | bool | None] = {
            name_cfg(_VAL_POV): await self.get_pressure_oversampling(),
            name_cfg(_VAL_TOV): await self.get_temperature_oversampling(),
            name_cfg(_VAL_FC): await self.get_filter_coefficient(),
        }
        return ret  # only for callback in _get_dict_cfg, is automatically inside try-except!

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(
            _NAME,
            _VAL_SI + _VAL_POV + _VAL_TOV + _VAL_FC + _VAL_PO + _VAL_TO + _VAL_SLO + _VAL_ATM,
            callback=self._read_sensor_dict,
        )

    async def _base_trigger(self) -> None:
        self.trigger_counter = 0
        while True:
            await self.base_trigger_event.wait()
            self.trigger_counter += 1
            if self.trigger_counter >= await self.trigger_period.get_value():
                self.trigger_event.set()
                self.trigger_counter = 0

    async def _init_bmp(self) -> bool:
        await self.pr.setup()  # required for all logged warnings and errors
        self._err_cnt_internal = 0
        try:
            await self.bmp.setup()
        except Exception as e:
            await self.pr.err_s(_NAME, "Error in initial setup:", e, errno=10)
            return False  # error

        self.pr.one(_NAME, "Setting sensor config at startup.")

        cfg_values = await self.cfgmgr.get_int_values(_VAL_SI + _VAL_POV + _VAL_TOV + _VAL_FC)
        if cfg_values is None or len(cfg_values) != 4:
            await self.pr.err_s(_NAME, "Error reading config data!", errno=11)
            return False  # error

        # set_trigger_secs() never raises (logs errno=21, keeps the previous value) - a bad stored
        # SampleInterv is a pure software timing knob, not a reason to fail this whole init attempt.
        await self.set_trigger_secs(cfg_values[0])  # BMPSampleInterv
        try:
            await self.bmp.set_pressure_oversampling(cfg_values[1])  # BMPPressOvers
            await self.bmp.set_temperature_oversampling(cfg_values[2])  # BMPTempOvers
            await self.bmp.set_filter_coefficient(cfg_values[3])  # BMPFiltCoeff
        except Exception as e:
            await self.pr.err_s(_NAME, "Error setting config data:", e, errno=12)
            return False  # error
        self.pr.one(_NAME, "initialized")
        return True

    async def _read_bmp(self) -> "BMPResults":
        timestamp: int | None = None
        pressure: float | None = None
        temperature: float | None = None
        try:
            timestamp = time.mktime(time.gmtime())
            pressure, temperature = await self.bmp.get_pressure_and_temperature()
            self.pr.all(_NAME, "gelesen")
        except Exception as e:
            timestamp = pressure = temperature = None
            await self.pr.err_s(_NAME, "Lesefehler:", e, errno=13)
        return pressure, temperature, timestamp

    async def _store_bmp(self, results: "BMPResults") -> None:
        if results[0] is None or results[1] is None or results[2] is None:
            return  # don't run on invalid data

        comp_values = await self.cfgmgr.get_float_values(_VAL_PO + _VAL_TO + _VAL_SLO + _VAL_ATM)
        if comp_values is None or len(comp_values) != 4:
            comp_values = [0.0, 0.0, 0.0, 15.0]
            await self.pr.err_s(_NAME, "Error reading config data!", errno=14)

        # results: (pressure, temperature, timestamp)
        p_comp = results[0] - comp_values[0]  # pressure - BMPPressOffset
        t_comp = results[1] - comp_values[1]  # temperature - BMPTempOffset
        await self._set_meas_data(
            BMP3XX(
                p_comp,
                t_comp,  # temperature - BMPTempOffset
                math_helpers.altitude_baro(p_comp, -comp_values[2], comp_values[3]),
                # local pressure, -BMPSeaLevelOffs, BMPMeanAtmTemp
                results[2],  # timestamp
            )
        )
        self.pr.all(_NAME, "Daten gespeichert")
        return

    async def read_loop(self) -> bool:
        if not await self._init_bmp():  # init sensor at startup
            return False  # break and restart if init fails
        while True:
            await self.trigger_event.wait()  # wait for read trigger event
            self.pr.evt(_NAME, "sensor trigger")
            results = await self._read_bmp()  # read data
            if not await self._error_check(results, _NAME):  # check and count errors
                return False  # break and restart if too many errors
            await self._store_bmp(results)  # store data in result buffer

    # Selected low-level driver forwards below: each failure is logged via self.pr (not swallowed
    # silently) so a transient bus fault on a REST-triggered config get/set stays visible in the
    # sensor's own error history, not just a bare None/False back to the caller.
    async def get_pressure_oversampling(self) -> int | None:
        try:
            return await self.bmp.get_pressure_oversampling()
        except Exception as e:
            await self.pr.err_s(_NAME, "Error reading pressure oversampling:", e, errno=15)
            return None

    async def set_pressure_oversampling(self, oversample: int) -> bool:
        try:
            await self.bmp.set_pressure_oversampling(oversample)
            return True
        except Exception as e:
            await self.pr.err_s(_NAME, "Error setting pressure oversampling:", e, errno=16)
            return False

    async def get_temperature_oversampling(self) -> int | None:
        try:
            return await self.bmp.get_temperature_oversampling()
        except Exception as e:
            await self.pr.err_s(_NAME, "Error reading temperature oversampling:", e, errno=17)
            return None

    async def set_temperature_oversampling(self, oversample: int) -> bool:
        try:
            await self.bmp.set_temperature_oversampling(oversample)
            return True
        except Exception as e:
            await self.pr.err_s(_NAME, "Error setting temperature oversampling:", e, errno=18)
            return False

    async def get_filter_coefficient(self) -> int | None:
        try:
            return await self.bmp.get_filter_coefficient()
        except Exception as e:
            await self.pr.err_s(_NAME, "Error reading filter coefficient:", e, errno=19)
            return None

    async def set_filter_coefficient(self, coef: int) -> bool:
        try:
            await self.bmp.set_filter_coefficient(coef)
            return True
        except Exception as e:
            await self.pr.err_s(_NAME, "Error setting filter coefficient:", e, errno=20)
            return False


class BMP3xx_DeviceSession(Lockable):
    def __init__(self, i2c_device: I2CDevice):
        super().__init__()
        self.i2c_device = i2c_device


class BMP3XX_I2C:
    # Base class for BMP3XX sensor.

    def __init__(self, i2c: I2C, address: int = 0x77) -> None:
        self.i2c_bmp3xx = BMP3xx_DeviceSession(I2CDevice(i2c, address))
        self._wait_time = 0.002  # just init with default here, set in setup()
        self.sea_level_pressure = 1013.25  # just init with default here, set in setup()

    async def setup(self, sea_level_pressure: float = 1013.25, wait_time: float = 0.002) -> None:
        async with self.i2c_bmp3xx as bmp3xx:  # device session
            async with bmp3xx.i2c_device as i2c:  # bus session
                await i2c.setup()
        chip_id = await self._read_byte(_REGISTER_CHIPID)
        if chip_id not in (_BMP388_CHIP_ID, _BMP390_CHIP_ID):
            raise RuntimeError(f"Failed to find BMP3XX! Chip ID {hex(chip_id)}")
        await self._read_coefficients()
        await self.reset()
        self.sea_level_pressure = sea_level_pressure  # in hPa
        self._wait_time = wait_time  # change this value to have faster reads if needed

    async def get_pressure(self) -> float:
        # The pressure in hPa.
        res = await self._read()
        return res[0] / 100

    async def get_temperature(self) -> float:
        # The temperature in degrees Celsius.
        res = await self._read()
        return res[1]

    async def get_pressure_and_temperature(self) -> tuple[float, float]:
        # Pressure (hPa) and temperature (degC) from one measurement cycle, so the two are never
        # up to a whole conversion apart in time - unlike calling get_pressure()/get_temperature()
        # separately, which each trigger their own full conversion.
        pressure, temperature = await self._read()
        return pressure / 100, temperature

    async def get_altitude(self) -> float:
        # The altitude in meters based on the currently set sea level pressure.
        # see https://www.weather.gov/media/epz/wxcalc/pressureAltitude.pdf
        if self.sea_level_pressure <= 0:
            # A non-positive base here otherwise raises a confusing TypeError/ZeroDivisionError
            # from Python's numeric tower (confirmed against the real Unix-port interpreter) -
            # replaced with one clear, deliberate error instead.
            raise ValueError(f"sea_level_pressure must be positive, got {self.sea_level_pressure}")
        return float(44307.7 * (1.0 - (await self.get_pressure() / self.sea_level_pressure) ** 0.190284))

    async def _get_osr_setting(self, start_bit: int) -> int:
        # Shared by get_pressure_oversampling()/get_temperature_oversampling() - osr_p and osr_t
        # are both 3-bit fields in the same OSR register (datasheet sec 4.3.17), differing only in
        # start_bit (0 vs 3).
        async with self.i2c_bmp3xx as bmp3xx:  # device session
            async with bmp3xx.i2c_device as i2c:  # bus session
                osr = await i2c.get_bits(3, _REGISTER_OSR, start_bit)
        if osr is None:
            raise OSError(f"failed to read OSR bit-field at bit {start_bit}")
        # Datasheet sec 4.3.17 only documents encodings 0-5 (x1..x32); 6/7 are reserved and could
        # surface from a bus disturbance flipping a bit - checked explicitly rather than letting a
        # bare IndexError leak out of this protocol-layer failure.
        if osr >= len(_OSR_SETTINGS):
            raise OSError(f"OSR bit-field at bit {start_bit} read back reserved encoding {osr}")
        return _OSR_SETTINGS[osr]

    async def _set_osr_setting(self, start_bit: int, oversample: int) -> None:
        if oversample not in _OSR_SETTINGS:
            raise ValueError(f"Oversampling must be one of: {_OSR_SETTINGS}")
        # get_bits()/set_bits() do their own read-modify-write with no await in between, so this
        # is atomic against a concurrent call setting the OSR register's *other* 3-bit field -
        # unlike the previous hand-rolled read-then-write pair, which was not.
        async with self.i2c_bmp3xx as bmp3xx:  # device session
            async with bmp3xx.i2c_device as i2c:  # bus session
                await i2c.set_bits(3, _REGISTER_OSR, start_bit, _OSR_SETTINGS.index(oversample))

    async def get_pressure_oversampling(self) -> int:
        # The pressure oversampling setting.
        return await self._get_osr_setting(0)

    async def set_pressure_oversampling(self, oversample: int) -> None:
        await self._set_osr_setting(0, oversample)

    async def get_temperature_oversampling(self) -> int:
        # The temperature oversampling setting.
        return await self._get_osr_setting(3)

    async def set_temperature_oversampling(self, oversample: int) -> None:
        await self._set_osr_setting(3, oversample)

    async def get_filter_coefficient(self) -> int:
        # The IIR filter coefficient.
        async with self.i2c_bmp3xx as bmp3xx:  # device session
            async with bmp3xx.i2c_device as i2c:  # bus session
                iir = await i2c.get_bits(3, _REGISTER_CONFIG, 1)
        if iir is None:
            raise OSError("failed to read filter coefficient")
        return _IIR_SETTINGS[iir]

    async def set_filter_coefficient(self, coef: int) -> None:
        if coef not in _IIR_SETTINGS:
            raise ValueError(f"Filter coefficient must be one of: {_IIR_SETTINGS}")
        async with self.i2c_bmp3xx as bmp3xx:  # device session
            async with bmp3xx.i2c_device as i2c:  # bus session
                await i2c.set_bits(3, _REGISTER_CONFIG, 1, _IIR_SETTINGS.index(coef))

    async def _wait_status_bits(self, bmp3xx: "BMP3xx_DeviceSession", mask: int, timeout_ms: int) -> None:
        # Polls STATUS until every bit in mask is set, or raises OSError after timeout_ms - bounds
        # an otherwise-unbounded loop if a bus disturbance leaves STATUS never reporting ready.
        # Caller must already hold bmp3xx's device-session lock, spanning the whole operation.
        start = time.ticks_ms()
        while True:
            async with bmp3xx.i2c_device as i2c:  # bus session
                status = await i2c.get_register_struct(_REGISTER_STATUS, "B")
            if isinstance(status, int) and status & mask == mask:
                return
            if time.ticks_diff(time.ticks_ms(), start) >= timeout_ms:
                raise OSError(f"STATUS bits {mask:#x} not set within {timeout_ms}ms")
            await asyncio.sleep(self._wait_time)

    async def reset(self) -> None:
        # Soft reset via CMD register (datasheet sec 4.3.22, cmd 0xB6); all config reverts to
        # default. Matches Bosch's reference sequence (bmp3_soft_reset()): wait cmd_rdy, settle
        # 2ms, verify via ERR_REG's cmd_err - a blind write can be ignored/corrupted on a bad bus.
        async with self.i2c_bmp3xx as bmp3xx:  # device session
            await self._wait_status_bits(bmp3xx, _STATUS_CMD_RDY, _CMD_RDY_TIMEOUT_MS)
            async with bmp3xx.i2c_device as i2c:  # bus session
                await i2c.set_register_struct(_REGISTER_CMD, "B", 0xB6)
            await asyncio.sleep(0.002)  # datasheet-confirmed 2ms post-reset settle time
            async with bmp3xx.i2c_device as i2c:  # bus session
                err = await i2c.get_register_struct(_REGISTER_ERR, "B")
        if isinstance(err, int) and err & _ERR_CMD:
            raise RuntimeError("reset command rejected (ERR_REG cmd_err set)")

    async def _read(self) -> tuple[float, float]:
        # Returns a (pressure_pa, temperature_degC) tuple. The whole cycle (trigger, poll, data
        # burst) is held under one device-session lock so a concurrent oversampling/filter/reset
        # call from another coroutine can't interleave mid-conversion.
        async with self.i2c_bmp3xx as bmp3xx:  # device session
            # Forced-mode measurement (PWR_CTRL=0x13: press_en|temp_en|mode=forced, sec 4.3.16).
            async with bmp3xx.i2c_device as i2c:  # bus session
                await i2c.set_register_struct(_REGISTER_CONTROL, "B", 0x13)

            # Bounded by the datasheet's own worst-case conversion time (sec 3.9.2) plus margin, so
            # a bus disturbance that corrupts STATUS into never reporting ready raises like any
            # other bus fault instead of hanging this task forever.
            await self._wait_status_bits(bmp3xx, _STATUS_DATA_READY, _MEAS_TIMEOUT_MS)

            # Get ADC values
            async with bmp3xx.i2c_device as i2c:  # bus session
                data = await i2c.get_register_struct(_REGISTER_PRESSUREDATA, "6s")
        if not isinstance(data, bytes) or len(data) != 6:
            raise OSError("unexpected data burst read result")
        adc_p = data[2] << 16 | data[1] << 8 | data[0]
        adc_t = data[5] << 16 | data[4] << 8 | data[3]

        # datasheet, sec 9.2 Temperature compensation
        T1, T2, T3 = self._temp_calib

        pd1 = adc_t - T1
        pd2 = pd1 * T2

        temperature = pd2 + (pd1 * pd1) * T3

        # datasheet, sec 9.3 Pressure compensation
        P1, P2, P3, P4, P5, P6, P7, P8, P9, P10, P11 = self._pressure_calib

        pd1 = P6 * temperature
        pd2 = P7 * temperature**2.0
        pd3 = P8 * temperature**3.0
        po1 = P5 + pd1 + pd2 + pd3

        pd1 = P2 * temperature
        pd2 = P3 * temperature**2.0
        pd3 = P4 * temperature**3.0
        po2 = adc_p * (P1 + pd1 + pd2 + pd3)

        pd1 = adc_p**2.0
        pd2 = P9 + P10 * temperature
        pd3 = pd1 * pd2
        pd4 = pd3 + P11 * adc_p**3.0

        pressure = po1 + po2 + pd4

        # pressure is in Pa here, temperature in deg C - get_pressure() divides by 100 for hPa;
        # the datasheet's own operating range below is in hPa, so it's applied after that same
        # conversion
        pressure_hpa = pressure / 100
        # Rejects a reading outside the datasheet's own operating range (sec 1, Table 2). This bus
        # has no CRC framing, unlike SCD30/SGP40, so a bit flip in the burst read (or a NaN/inf from
        # the arithmetic) is otherwise undetectable - treated as a failed read by the caller.
        if not (300.0 <= pressure_hpa <= 1250.0 and -40.0 <= temperature <= 85.0):
            raise ValueError(f"reading outside operating range (p={pressure_hpa} hPa, t={temperature} degC)")
        return pressure, temperature

    async def _read_coefficients(self) -> None:
        # Read & save the calibration coefficients.
        raw = await self._read_register(_REGISTER_CAL_DATA, 21)
        # Per Bosch's self-test app note (BST-MPS-AN006), trimming data is verified against bounds
        # this codebase doesn't have the exact values for - a factory-trimmed block is never
        # legitimately all-0x00/all-0xFF, which catches the same class of fault without them.
        if raw == bytes([raw[0]]) * len(raw) and raw[0] in (0x00, 0xFF):
            raise RuntimeError(f"calibration data implausible (all bytes {raw[0]:#04x})")
        # See datasheet, pg. 27, table 22
        coeff = unpack("<HHbhhbbHHbbhbb", raw)
        # See datasheet, sec 9.1
        # Note: forcing float math to prevent issues with boards that
        #       do not support long ints for 2**<large int>
        self._temp_calib = (
            coeff[0] / 2**-8.0,  # T1
            coeff[1] / 2**30.0,  # T2
            coeff[2] / 2**48.0,
        )  # T3
        self._pressure_calib = (
            (coeff[3] - 2**14.0) / 2**20.0,  # P1
            (coeff[4] - 2**14.0) / 2**29.0,  # P2
            coeff[5] / 2**32.0,  # P3
            coeff[6] / 2**37.0,  # P4
            coeff[7] / 2**-3.0,  # P5
            coeff[8] / 2**6.0,  # P6
            coeff[9] / 2**8.0,  # P7
            coeff[10] / 2**15.0,  # P8
            coeff[11] / 2**48.0,  # P9
            coeff[12] / 2**48.0,  # P10
            coeff[13] / 2**65.0,
        )  # P11

    async def _read_byte(self, register: int) -> int:
        # Read a byte register value and return it.
        return (await self._read_register(register, 1))[0]

    async def _read_register(self, register: int, length: int) -> bytes:
        # Low level register reading over I2C, returns the raw bytes read.
        async with self.i2c_bmp3xx as bmp3xx:  # device session
            async with bmp3xx.i2c_device as i2c:  # bus session
                value = await i2c.get_register_struct(register, f"{length}s")
        if not isinstance(value, bytes) or len(value) != length:
            raise OSError(f"failed to read {length} bytes from register {register:#x}")
        return value
