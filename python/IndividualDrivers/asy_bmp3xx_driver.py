# SPDX-FileCopyrightText: 2018 Carter Nelson for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_bmp3xx`
====================================================

CircuitPython driver from BMP388 Temperature and Barometric Pressure sensor.

* Author(s): Carter Nelson

Implementation Notes
--------------------

**Hardware:**

* `Adafruit BMP388 - Precision Barometric Pressure and Altimeter
  <https://www.adafruit.com/product/3966>`_ (Product ID: 3966)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library:
  https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

"""
import struct
import asyncio
import time
import math_helpers
from micropython import const
from asy_i2c_driver import I2C, I2CDevice
from machine import Timer
from async_manager import DataManager, LockedValue, TimeCounterManager


_BMP388_CHIP_ID = const(0x50)
_BMP390_CHIP_ID = const(0x60)

# pylint: disable=import-outside-toplevel
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



class BMP3xx_Reader:
    def __init__(self, i2c, asy_cfg_callback, trigger_sec=1, max_i2c_err=5, debug=False):
        self.bmp = BMP3XX_I2C(i2c)
        self.meas_data = DataManager(4)
        self.base_trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_timer = Timer()
        self.trigger_period = LockedValue(int(trigger_sec))
        self.trigger_counter = 0
        self.error_counter = TimeCounterManager()  # use inherently limited counter here as overall error counter
        self.max_i2c_err = max_i2c_err
        self.cfg_callback = asy_cfg_callback  # expects (valid, [BMPSampleInterv, PressOversampling, PressOffset, TempOversampling, TempOffset, FiltCoeff])
        self.debug = debug

    def start_asy_read(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_bmp())

    def start_asy_trigger(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._base_trigger())

    def start_timer(self):
        self.trigger_timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda b: self.base_trigger_event.set())

    def stop_timer(self):
        self.trigger_timer.deinit()

    async def set_trigger_secs(self, value):
        await self.trigger_period.setValue(int(value))

    async def get_error_counter(self):
        return await self.error_counter.get_counter()

    async def get_data(self, startIdx=0, length=-1):
        return await self.meas_data.get_data(startIdx=startIdx, length=length)

    async def _base_trigger(self):
        self.trigger_counter = 0
        while True:
            await self.base_trigger_event.wait()
            self.trigger_counter += 1
            if self.trigger_counter >= await self.trigger_period.getValue():
                self.trigger_event.set()
                if self.debug: print("BMP388 sensor trigger, period:", self.trigger_counter)
                self.trigger_counter = 0

    async def read_bmp(self):
        err_cnt = 0
        try:
            await self.bmp.setup()
        except:
            err_cnt = 1
        (valid, [SInt, POvs, POffs, TOvs, TOffs, FCoeff, SeaLevel, AtmTemp]) = await self.cfg_callback()
        del POffs, TOffs, SeaLevel, AtmTemp
        if valid:
            try:
                await self.trigger_period.setValue(SInt)
                await self.bmp.set_pressure_oversampling(POvs)
                await self.bmp.set_temperature_oversampling(TOvs)
                await self.bmp.set_filter_coefficient(FCoeff)
            except:
                err_cnt = 1
            if self.debug: print("Setting BMP388 sensor config at startup.")
        else:  # valid
            err_cnt = 1
        del valid, SInt, POvs, TOvs, FCoeff

        if err_cnt != 0:
            await self.error_counter.increment()
            if self.debug: print("Error reading BMP388 config data / setting sensor at startup!")
            return False
        while True:
            await self.trigger_event.wait()
            err = False
            try:
                Timestamp = time.mktime(time.gmtime())
                Pressure = await self.bmp.get_pressure()
                Temperature = await self.bmp.get_temperature()
                if self.debug: print("BMP388 gelesen")
            except:
                err = True
                Timestamp = None
                Pressure = None
                Temperature = None
                if self.debug: print("BMP388 Lesefehler!")

            if err:
                await self.error_counter.increment()
                err_cnt += 1
                if self.debug: print("BMP388 Fehlerzähler erhöht auf", err_cnt)
                if err_cnt > self.max_i2c_err:
                    if self.debug: print("BMP388 Maximale Fehleranzahl erreicht!")
                    return False    # Abbruch der Schleife führt zu System-Reset
            else:
                if err_cnt > 0:
                    err_cnt -= 1
                    if self.debug: print("BMP388 Fehlerzähler zurück auf", err_cnt)

                (valid, [SInt, POvs, POffs, TOvs, TOffs, FCoeff, SeaLevel, AtmTemp]) = await self.cfg_callback()
                del SInt, POvs, TOvs, FCoeff
                if not valid:
                    POffs = 0.0
                    TOffs = 0.0
                    SeaLevel = 0.0
                    AtmTemp = 15.0
                    await self.error_counter.increment()
                    if self.debug: print("Error reading BMP388 config data!")

                await self.meas_data.set_data([Pressure - POffs,
                                               Temperature - TOffs,
                                               math_helpers.altitude_baro(Pressure - POffs, -SeaLevel, AtmTemp),
                                               Timestamp])
                if self.debug: print("BMP388 Daten gespeichert")
                del POffs, TOffs, SeaLevel, AtmTemp

    # selected low-level direct sensor driver function forwards
    async def get_pressure_oversampling(self):
        return await self.bmp.get_pressure_oversampling()

    async def set_pressure_oversampling(self, oversample):
        await self.bmp.set_pressure_oversampling(oversample)

    async def get_temperature_oversampling(self):
        return await self.bmp.get_temperature_oversampling()

    async def set_temperature_oversampling(self, oversample):
        await self.bmp.set_temperature_oversampling(oversample)

    async def get_filter_coefficient(self):
        return await self.bmp.get_filter_coefficient()

    async def set_filter_coefficient(self, coef):
        await self.bmp.set_filter_coefficient(coef)


class BMP3XX_I2C:
    """Base class for BMP3XX sensor."""
    def __init__(self, i2c: I2C, address: int = 0x77) -> None:
        self._i2c = I2CDevice(i2c, address)

    def setup(self, sea_level_pressure: float = 1013.25) -> None:
        await self._i2c.setup()
        chip_id = await self._read_byte(_REGISTER_CHIPID)
        if chip_id not in (_BMP388_CHIP_ID, _BMP390_CHIP_ID):
            raise RuntimeError(f"Failed to find BMP3XX! Chip ID {hex(chip_id)}")
        await self._read_coefficients()
        await self.reset()
        self.sea_level_pressure = sea_level_pressure
        self._wait_time = 0.002  # change this value to have faster reads if needed
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
        return 44307.7 * (1 - (await self.get_pressure() / self.sea_level_pressure) ** 0.190284)

    async def get_pressure_oversampling(self) -> int:
        """The pressure oversampling setting."""
        return _OSR_SETTINGS[await self._read_byte(_REGISTER_OSR) & 0x07]

    async def set_pressure_oversampling(self, oversample: int) -> None:
        if oversample not in _OSR_SETTINGS:
            raise ValueError(f"Oversampling must be one of: {_OSR_SETTINGS}")
        new_setting = await self._read_byte(_REGISTER_OSR) & 0xF8 | _OSR_SETTINGS.index(
            oversample
        )
        await self._write_register_byte(_REGISTER_OSR, new_setting)

    async def get_temperature_oversampling(self) -> int:
        """The temperature oversampling setting."""
        return _OSR_SETTINGS[await self._read_byte(_REGISTER_OSR) >> 3 & 0x07]

    async def set_temperature_oversampling(self, oversample: int) -> None:
        if oversample not in _OSR_SETTINGS:
            raise ValueError(f"Oversampling must be one of: {_OSR_SETTINGS}")
        new_setting = (
            await self._read_byte(_REGISTER_OSR) & 0xC7 | _OSR_SETTINGS.index(oversample) << 3
        )
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
        coeff = struct.unpack("<HHbhhbbHHbbhbb", coeff)
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
        async with self._i2c as i2c:
            await i2c.write(bytes([register & 0xFF]))
            await i2c.readinto(result)
            return result

    async def _write_register_byte(self, register: int, value: int) -> None:
        """Low level register writing over I2C, writes one 8-bit value"""
        async with self._i2c as i2c:
            await i2c.write(bytes((register & 0xFF, value & 0xFF)))
