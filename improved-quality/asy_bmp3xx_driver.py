import time
import asyncio
import math_helpers
from micropython import const
from uasyncio import ThreadSafeFlag
from collections import namedtuple
from machine import Timer
from struct import unpack
from asy_i2c_driver import I2C, I2CDevice
from asy_fram_manager import AsyFramManager
from config_manager import make_dict, name_cfg
from base_classes import SensorReaderConfig, LockedValue, Lockable
from typing import Dict, Tuple, Union, Any, List, Callable, cast


_BMP388_CHIP_ID = const(0x50)
_BMP390_CHIP_ID = const(0x60)

_REGISTER_CHIPID = const(0x00)
_REGISTER_STATUS = const(0x03)
_REGISTER_PRESSUREDATA = const(0x04)
_REGISTER_TEMPDATA = const(0x07)
_REGISTER_CONTROL = const(0x1B)
_REGISTER_OSR = const(0x1C)
_REGISTER_ODR = const(0x1D)
_REGISTER_CONFIG = const(0x1F)
_REGISTER_CAL_DATA = const(0x31)
_REGISTER_CMD = const(0x7E)

_OSR_SETTINGS = (1, 2, 4, 8, 16, 32)  # pressure and temperature oversampling settings
_IIR_SETTINGS = (0, 2, 4, 8, 16, 32, 64, 128)  # IIR filter coefficients

_VAL_SI = const((("SampleInterv", "int", 2, 1, 3600, None),))
_VAL_POV = const((("PressOvers", "int", 1, 0, 5, None),))
_VAL_TOV = const((("TempOvers", "int", 1, 0, 5, None),))
_VAL_FC = const((("FiltCoeff", "int", 0, 0, 7, None),))
_VAL_PO = const((("PressOffset", "float", 0.0, -500.0, 500.0, None),))
_VAL_TO = const((("TempOffset", "float", 0.0, -10.0, 10.0, None),))
_VAL_SLO = const((("SeaLevelOffs", "float", 0.0, -1000.0, 5000.0, None),))
_VAL_ATM = const((("MeanAtmTemp", "float", 15.0, -50.0, 50.0, None),))

_NAME = const("BMP3XX")
BMP3XX = namedtuple("BMP3XX", ("Pres", "Temp", "SLPres", "TS"))
BMPResults = Tuple[Union[float, None], Union[float, None], Union[int, None]]
# pressure, temperature, timestamp


class BMP3xx_Reader(SensorReaderConfig):
    def __init__(
        self,
        i2c: I2C,
        address: int = 0x77,
        trigger_sec: int = 1,
        max_i2c_err: int = 5,
        cfg_path: str = "",
        fram: AsyFramManager | None = None,
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
        self.base_trigger_event = ThreadSafeFlag()
        self.trigger_event = ThreadSafeFlag()
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

    def get_task_starters(self) -> List[Callable[[], asyncio.Task[Any]]]:
        return [self.start_asy_read, self.start_asy_trigger]

    def get_timer_starters(self) -> List[Callable[[], None]]:
        return [self.start_timer]

    async def set_trigger_secs(self, value: int | float) -> None:
        await self.trigger_period.set_value(int(value))

    async def get_data(self) -> BMP3XX:
        data = await self._get_meas_data()
        return cast(BMP3XX, data)

    async def get_dict_data(self) -> Dict[str, Dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data)

    async def get_error_counter(self) -> Dict[str, Dict[str, int | List[int] | List[str]]]:
        return await self.pr.get_log(_NAME)

    async def _read_sensor_dict(self) -> Dict[str, int | float | str | bool | None]:
        ret: Dict[str, int | float | str | bool | None] = {
            name_cfg(_VAL_POV): await self.get_pressure_oversampling(),
            name_cfg(_VAL_TOV): await self.get_temperature_oversampling(),
            name_cfg(_VAL_FC): await self.get_filter_coefficient(),
        }
        return ret  # only for callback in _get_dict_cfg, is automatically inside try-except!

    async def get_dict_cfg(self) -> Dict[str, Dict[str, int | float | str | bool | None]]:
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

        try:
            await self.trigger_period.set_value(cfg_values[0])  # BMPSampleInterv
            await self.bmp.set_pressure_oversampling(cfg_values[1])  # BMPPressOvers
            await self.bmp.set_temperature_oversampling(cfg_values[2])  # BMPTempOvers
            await self.bmp.set_filter_coefficient(cfg_values[3])  # BMPFiltCoeff
        except Exception as e:
            await self.pr.err_s(_NAME, "Error setting config data:", e, errno=12)
            return False  # error
        self.pr.one(_NAME, "initialized")
        return True

    async def _read_bmp(self) -> BMPResults:
        try:
            timestamp = time.mktime(time.gmtime())  # type: ignore[call-arg]
            pressure = await self.bmp.get_pressure()
            temperature = await self.bmp.get_temperature()
            self.pr.all(_NAME, "gelesen")
        except Exception as e:
            timestamp = pressure = temperature = None
            await self.pr.err_s(_NAME, "Lesefehler:", e, errno=13)
        return pressure, temperature, timestamp

    async def _store_bmp(self, results: BMPResults) -> None:
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

    # selected low-level direct sensor driver function forwards
    async def get_pressure_oversampling(self) -> int | None:
        try:
            return await self.bmp.get_pressure_oversampling()
        except Exception:
            return None

    async def set_pressure_oversampling(self, oversample: int) -> bool:
        try:
            await self.bmp.set_pressure_oversampling(oversample)
            return True
        except Exception:
            return False

    async def get_temperature_oversampling(self) -> int | None:
        try:
            return await self.bmp.get_temperature_oversampling()
        except Exception:
            return None

    async def set_temperature_oversampling(self, oversample: int) -> bool:
        try:
            await self.bmp.set_temperature_oversampling(oversample)
            return True
        except Exception:
            return False

    async def get_filter_coefficient(self) -> int | None:
        try:
            return await self.bmp.get_filter_coefficient()
        except Exception:
            return None

    async def set_filter_coefficient(self, coef: int) -> bool:
        try:
            await self.bmp.set_filter_coefficient(coef)
            return True
        except Exception:
            return False


class BMP3xx_DeviceSession(Lockable):
    def __init__(self, i2c_device: I2CDevice):
        super().__init__()
        self.i2c_device = i2c_device


class BMP3XX_I2C:
    """Base class for BMP3XX sensor."""

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
        self.sea_level_pressure = sea_level_pressure
        self._wait_time = wait_time  # change this value to have faster reads if needed
        """Sea level pressure in hPa."""

    async def get_pressure(self) -> float:
        """The pressure in hPa."""
        res = await self._read()
        return res[0] / 100

    async def get_temperature(self) -> float:
        """The temperature in degrees Celsius"""
        res = await self._read()
        return res[1]

    async def get_altitude(self) -> float:
        """The altitude in meters based on the currently set sea level pressure."""
        # see https://www.weather.gov/media/epz/wxcalc/pressureAltitude.pdf
        return float(44307.7 * (1.0 - (await self.get_pressure() / self.sea_level_pressure) ** 0.190284))

    async def get_pressure_oversampling(self) -> int:
        """The pressure oversampling setting."""
        return _OSR_SETTINGS[await self._read_byte(_REGISTER_OSR) & 0x07]

    async def set_pressure_oversampling(self, oversample: int) -> None:
        if oversample not in _OSR_SETTINGS:
            raise ValueError(f"Oversampling must be one of: {_OSR_SETTINGS}")
        new_setting = await self._read_byte(_REGISTER_OSR) & 0xF8 | _OSR_SETTINGS.index(oversample)
        await self._write_register_byte(_REGISTER_OSR, new_setting)

    async def get_temperature_oversampling(self) -> int:
        """The temperature oversampling setting."""
        return _OSR_SETTINGS[await self._read_byte(_REGISTER_OSR) >> 3 & 0x07]

    async def set_temperature_oversampling(self, oversample: int) -> None:
        if oversample not in _OSR_SETTINGS:
            raise ValueError(f"Oversampling must be one of: {_OSR_SETTINGS}")
        new_setting = await self._read_byte(_REGISTER_OSR) & 0xC7 | _OSR_SETTINGS.index(oversample) << 3
        await self._write_register_byte(_REGISTER_OSR, new_setting)

    async def get_filter_coefficient(self) -> int:
        """The IIR filter coefficient."""
        return _IIR_SETTINGS[await self._read_byte(_REGISTER_CONFIG) >> 1 & 0x07]

    async def set_filter_coefficient(self, coef: int) -> None:
        if coef not in _IIR_SETTINGS:
            raise ValueError(f"Filter coefficient must be one of: {_IIR_SETTINGS}")
        await self._write_register_byte(_REGISTER_CONFIG, _IIR_SETTINGS.index(coef) << 1)

    async def reset(self) -> None:
        """Perform a power on reset. All user configuration settings are overwritten
        with their default state.
        """
        await self._write_register_byte(_REGISTER_CMD, 0xB6)

    async def _read(self) -> Tuple[float, float]:
        """Returns a tuple for temperature and pressure."""

        # Perform one measurement in forced mode
        await self._write_register_byte(_REGISTER_CONTROL, 0x13)

        # Wait for *both* conversions to complete
        while await self._read_byte(_REGISTER_STATUS) & 0x60 != 0x60:
            await asyncio.sleep(self._wait_time)

        # Get ADC values
        data = await self._read_register(_REGISTER_PRESSUREDATA, 6)
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

        # pressure in hPa, temperature in deg C
        return pressure, temperature

    async def _read_coefficients(self) -> None:
        """Read & save the calibration coefficients"""
        coeff = await self._read_register(_REGISTER_CAL_DATA, 21)
        # See datasheet, pg. 27, table 22
        coeff = unpack("<HHbhhbbHHbbhbb", coeff)
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
        """Read a byte register value and return it"""
        ret = await self._read_register(register, 1)
        return ret[0]

    async def _read_register(self, register: int, length: int) -> bytearray:
        """Low level register reading over I2C, returns a list of values"""
        result = bytearray(length)
        async with self.i2c_bmp3xx as bmp3xx:  # device session
            async with bmp3xx.i2c_device as i2c:  # bus session
                await i2c.write(bytes([register & 0xFF]))
            await asyncio.sleep(0)
            async with bmp3xx.i2c_device as i2c:  # bus session
                await i2c.readinto(result)
        return result

    async def _write_register_byte(self, register: int, value: int) -> None:
        """Low level register writing over I2C, writes one 8-bit value"""
        async with self.i2c_bmp3xx as bmp3xx:  # device session
            async with bmp3xx.i2c_device as i2c:  # bus session
                await i2c.write(bytes((register & 0xFF, value & 0xFF)))
