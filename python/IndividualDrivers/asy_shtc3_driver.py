
# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_shtc3`
================================================================================

A helper library for using the Sensirion SHTC3 Humidity and Temperature Sensor


* Author(s): Bryan Siepert

Implementation Notes
--------------------

**Hardware:**

* `Adafruit SHTC3 Temperature & Humidity Sensor
  <https://www.adafruit.com/product/4636>`_ (Product ID: 4636)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library:
  https://github.com/adafruit/Adafruit_CircuitPython_BusDevice

* Adafruit's Register library:
  https://github.com/adafruit/Adafruit_CircuitPython_Register

"""

# imports
import asyncio
import time
from struct import unpack_from
from asy_i2c_driver import I2CDevice, I2C
from micropython import const
from machine import Timer
from async_manager import DataManager, LockedValue, TimeCounterManager
import math_helpers


_SHTC3_DEFAULT_ADDR = const(0x70)  # SHTC3 I2C Address
_SHTC3_NORMAL_MEAS_TFIRST_STRETCH = const(0x7CA2)  # Normal measurement, temp first with Clock Stretch Enabled
_SHTC3_LOWPOW_MEAS_TFIRST_STRETCH = const(0x6458)  # Low power measurement, temp first with Clock Stretch Enabled
_SHTC3_NORMAL_MEAS_HFIRST_STRETCH = const(0x5C24)  # Normal measurement, hum first with Clock Stretch Enabled
_SHTC3_LOWPOW_MEAS_HFIRST_STRETCH = const(0x44DE)  # Low power measurement, hum first with Clock Stretch Enabled
_SHTC3_NORMAL_MEAS_TFIRST = const(0x7866)  # Normal measurement, temp first with Clock Stretch disabled
_SHTC3_LOWPOW_MEAS_TFIRST = const(0x609C)  # Low power measurement, temp first with Clock Stretch disabled
_SHTC3_NORMAL_MEAS_HFIRST = const(0x58E0)  # Normal measurement, hum first with Clock Stretch disabled
_SHTC3_LOWPOW_MEAS_HFIRST = const(0x401A)  # Low power measurement, hum first with Clock Stretch disabled

_SHTC3_READID = const(0xEFC8)  # Read Out of ID Register
_SHTC3_SOFTRESET = const(0x805D)  # Soft Reset
_SHTC3_SLEEP = const(0xB098)  # Enter sleep mode
_SHTC3_WAKEUP = const(0x3517)  # Wakeup mode
_SHTC3_CHIP_ID = const(0x807)


class SHTC3_Reader:
    def __init__(self, i2c, asy_cfg_callback, trigger_sec=1, max_i2c_err=5, debug=False):
        self.shtc = SHTC3(i2c)
        self.meas_data = DataManager(5)
        self.base_trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_event = asyncio.ThreadSafeFlag()
        self.trigger_timer = Timer()
        self.trigger_period = LockedValue(int(trigger_sec))
        self.trigger_counter = 0
        self.error_counter = TimeCounterManager()  # use inherently limited counter here as overall error counter
        self.max_i2c_err = max_i2c_err
        self.cfg_callback = asy_cfg_callback  # expects (valid, [SHTCSampleInterval, TemperatureOffset, FilterCoefficient])
        self.debug = debug

    def start_asy_read(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_shtc())

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
                if self.debug: print("SHTC3 sensor trigger, period:", self.trigger_counter)
                self.trigger_counter = 0

    async def read_shtc(self):
        err_cnt = 0
        try:
            await self.shtc.setup()
        except:
            err_cnt = 1
        (valid, [SInt, TOffs, FiltCoeff]) = await self.cfg_callback()
        del TOffs, FiltCoeff
        if valid:
            await self.trigger_period.setValue(SInt)
            if self.debug: print("Setting SHTC3 sensor config at startup.")
        else:  # valid
            err_cnt = 1
        del valid, SInt

        if err_cnt != 0:
            await self.error_counter.increment()
            if self.debug: print("Error reading SHTC3 config data / setting sensor at startup!")
            return False
        while True:
            await self.trigger_event.wait()
            err = False
            try:
                Timestamp = time.mktime(time.gmtime())
                (Temperature, Humidity) = await self.shtc.get_measurements()
                if self.debug: print("SHTC3 gelesen")
            except:
                err = True
                Timestamp = None
                Temperature = None
                Humidity = None
                if self.debug: print("SHTC3 Lesefehler!")

            if err:
                await self.error_counter.increment()
                err_cnt += 1
                if self.debug: print("SHTC3 Fehlerzähler erhöht auf", err_cnt)
                if err_cnt > self.max_i2c_err:
                    if self.debug: print("SHTC3 Maximale Fehleranzahl erreicht!")
                    return False    # Abbruch der Schleife führt zu System-Reset
            else:
                if err_cnt > 0:
                    err_cnt -= 1
                    if self.debug: print("SHTC3 Fehlerzähler zurück auf", err_cnt)

                (valid, [SInt, TOffs, FiltCoeff]) = await self.cfg_callback()
                del SInt
                if not valid:
                    TOffs = 0.0
                    FiltCoeff = 0.0
                    await self.error_counter.increment()
                    if self.debug: print("Error reading SHTC3 config data!")

                tc = Temperature - TOffs
                rh = None  #  temperature offset compensation for humidity
                ah = math_helpers.abs_humidity(Temperature, Humidity)
                if ah is not None:
                    rh = math_helpers.rel_humidity(tc, ah)
                if rh is None:
                    rh = Humidity
                    if self.debug: print("Error compensating SHTC3 humidity data!")

                if FiltCoeff > 0.0:  # optional first-order lowpass filter
                    if FiltCoeff > 1.0: FiltCoeff = 1.0
                    [tc_old, rh_old] = await self.meas_data.get_data(startIdx=0, length=2)
                    if (tc_old is not None) and (rh_old is not None):
                        tc = tc_old + (FiltCoeff * (tc - tc_old))
                        rh = rh_old + (FiltCoeff * (rh - rh_old))

                await self.meas_data.set_data([tc,
                                               rh,
                                               math_helpers.wet_bulb_temperature(tc, rh),
                                               math_helpers.dew_point(tc, rh),
                                               Timestamp])
                if self.debug: print("SHTC3 Daten gespeichert")
                del TOffs, FiltCoeff


class SHTC3:
    """
    A driver for the SHTC3 temperature and humidity sensor.

    :param ~busio.I2C i2c_bus: The I2C bus the SHTC3 is connected to.

    **Quickstart: Importing and using the SHTC3 temperature and humidity sensor**

        Here is an example of using the :class:`SHTC3`.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            import adafruit_shtc3

        Once this is done, you can define your `board.I2C` object and define your sensor

        .. code-block:: python

            i2c = board.I2C()   # uses board.SCL and board.SDA
            sht = adafruit_shtc3.SHTC3(i2c)

        Now you have access to the temperature and humidity using the :attr:`measurements`.
        it will return a tuple with the :attr:`temperature` and :attr:`relative_humidity`
        measurements

        .. code-block:: python

            temperature, relative_humidity = sht.measurements

    """

    def __init__(self, i2c_bus: I2C) -> None:
        self.i2c_device = I2CDevice(i2c_bus, _SHTC3_DEFAULT_ADDR)
        self._buffer = bytearray(6)
        self.low_power = False
        self.sleeping = False

    async def setup(self) -> None:
        await self.i2c_device.setup()
        await self.reset()
        chip_id = await self._get_chip_id()
        if chip_id != _SHTC3_CHIP_ID:
            raise RuntimeError("Failed to find an SHTC3 sensor - check your wiring!")
        await self.set_sleeping(True)

    async def _write_command(self, command: int) -> None:
        """helper function to write a command to the i2c device"""
        self._buffer[0] = command >> 8
        self._buffer[1] = command & 0xFF
        async with self.i2c_device as i2c:
            await i2c.write(self._buffer, start=0, end=2)

    async def _get_chip_id(self) -> int:
        """Determines the chip id of the sensor"""
        await self._write_command(_SHTC3_READID)
        await asyncio.sleep(0.001)
        async with self.i2c_device as i2c:
            await i2c.readinto(self._buffer)
        return unpack_from(">H", self._buffer)[0] & 0x083F

    async def reset(self) -> None:
        """Perform a soft reset of the sensor, resetting all settings to their power-on defaults"""
        await self.set_sleeping(False)
        try:
            await self._write_command(_SHTC3_SOFTRESET)
        except RuntimeError as run_err:
            if run_err.args and run_err.args[0] != "I2C device address was NACK'd":
                raise run_err
        await asyncio.sleep(0.001)

    async def get_sleeping(self) -> bool:
        """Determines the sleep state of the sensor"""
        return self.sleeping

    async def set_sleeping(self, sleep_enabled: bool) -> None:
        if sleep_enabled:
            await self._write_command(_SHTC3_SLEEP)
        else:
            await self._write_command(_SHTC3_WAKEUP)
        await asyncio.sleep(0.001)
        self.sleeping = sleep_enabled

    async def get_low_power(self) -> bool:
        """Enables the less accurate low power mode, trading accuracy for power consumption"""
        return self.low_power

    async def set_low_power(self, low_power_enabled: bool) -> None:
        self.low_power = low_power_enabled

    async def get_relative_humidity(self) -> float:
        """The current relative humidity in % rH. This is a value from 0-100%."""
        meas = await self.get_measurements()
        return meas[1]

    async def get_temperature(self) -> float:
        """The current temperature in degrees Celsius"""
        meas = await self.get_measurements()
        return meas[0]

    async def get_measurements(self):
        """both `temperature` and `relative_humidity`, read simultaneously"""
        await self.set_sleeping(False)
        temperature = None
        humidity = None
        # send correct command for the current power state
        if self.low_power:
            await self._write_command(_SHTC3_LOWPOW_MEAS_TFIRST)
            await asyncio.sleep(0.001)
        else:
            await self._write_command(_SHTC3_NORMAL_MEAS_TFIRST)
            await asyncio.sleep(0.013)

        # read the measured data into our buffer
        async with self.i2c_device as i2c:
            await i2c.readinto(self._buffer)

        # separate the read data
        temp_data = self._buffer[0:2]
        temp_crc = self._buffer[2]
        humidity_data = self._buffer[3:5]
        humidity_crc = self._buffer[5]

        # check CRC of bytes
        if temp_crc != self._crc8(temp_data) or humidity_crc != self._crc8(humidity_data):
            return (temperature, humidity)

        # decode data into human values:
        # convert bytes into 16-bit signed integer
        # convert the LSB value to a human value according to the datasheet
        raw_temp = unpack_from(">H", temp_data)[0]
        raw_temp = ((4375 * raw_temp) >> 14) - 4500
        temperature = raw_temp / 100.0

        # repeat above steps for humidity data
        raw_humidity = unpack_from(">H", humidity_data)[0]
        raw_humidity = (625 * raw_humidity) >> 12
        humidity = raw_humidity / 100.0

        await self.set_sleeping(True)

        return (temperature, humidity)

    ## CRC-8 formula from page 14 of SHTC3 datasheet
    # https://media.digikey.com/pdf/Data%20Sheets/Sensirion%20PDFs/HT_DS_SHTC3_D1.pdf
    # Test data [0xBE, 0xEF] should yield 0x92

    @staticmethod
    def _crc8(buffer: bytearray) -> int:
        """verify the crc8 checksum"""
        crc = 0xFF
        for byte in buffer:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
        return crc & 0xFF  # return the bottom 8 bits
