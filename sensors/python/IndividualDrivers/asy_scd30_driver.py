# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
#
# SPDX-License-Identifier: MIT
"""
`adafruit_scd30`
================================================================================

Helper library for the SCD30 CO2 sensor


* Author(s): Bryan Siepert

Implementation Notes
--------------------

**Hardware:**

* `Adafruit SCD30 Breakout <https://www.adafruit.com/product/4867>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases


 * Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
 * Adafruit's Register library: https://github.com/adafruit/Adafruit_CircuitPython_Register
"""

# imports
import asyncio
import time
import math_helpers
from struct import unpack_from, unpack
from asy_i2c_driver import I2CDevice, I2C
from machine import Pin
from micropython import const
from machine import Timer
from async_manager import DataManager, TimeCounterManager

_SCD30_DEFAULT_ADDR = const(0x61)
_CMD_CONTINUOUS_MEASUREMENT = const(0x0010)
_CMD_STOP_CONTINUOUS_MEASUREMENT = const(0x0104)
_CMD_SET_MEASUREMENT_INTERVAL = const(0x4600)
_CMD_GET_DATA_READY = const(0x0202)
_CMD_READ_MEASUREMENT = const(0x0300)
_CMD_AUTOMATIC_SELF_CALIBRATION = const(0x5306)
_CMD_SET_FORCED_RECALIBRATION_FACTOR = const(0x5204)
_CMD_SET_TEMPERATURE_OFFSET = const(0x5403)
_CMD_SET_ALTITUDE_COMPENSATION = const(0x5102)
_CMD_SOFT_RESET = const(0xD304)


class SCD30_Reader:
    def __init__(self, i2c, irq_pin, trigger_sec=3, max_i2c_err=5, debug=False):
        self.scd = SCD30(i2c)
        self.irq_pin = Pin(irq_pin, mode=Pin.IN)
        self.meas_data = DataManager(6)
        self.start_trigger_event = asyncio.ThreadSafeFlag()
        self.start_trigger_timer = Timer()
        self.trigger_half_sec = 2 * int(trigger_sec)
        self.irq_trigger_event = asyncio.ThreadSafeFlag()
        self.scd_timer_triggers = 0
        self.error_counter = TimeCounterManager()  # use inherently limited counter here as overall error counter
        self.max_i2c_err = max_i2c_err
        self.debug = debug

    def start_asy_read(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_scd())

    def start_asy_init(self):
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.scd_init_irq())

    def start_timer(self):
        self.start_trigger_timer.init(period=500, mode=Timer.PERIODIC, callback=lambda b: self.start_trigger_event.set())
        self.irq_pin.irq(trigger=self.irq_pin.IRQ_RISING, handler=lambda b: self.irq_trigger_event.set())

    def stop_timer(self):
        self.start_trigger_timer.deinit()

    async def get_error_counter(self):
        return await self.error_counter.get_counter()

    async def get_data(self, startIdx=0, length=-1):
        return await self.meas_data.get_data(startIdx=startIdx, length=length)

    async def read_scd(self):
        err_cnt = 0
        try:
            await self.scd.setup()
        except:
            err_cnt = 1

        if err_cnt != 0:
            await self.error_counter.increment()
            if self.debug: print("Error reading SCD30 config data / setting sensor at startup!")
            return False
        while True:
            await self.irq_trigger_event.wait()
            self.scd_timer_triggers = 0
            err = False
            try:
                Timestamp = time.mktime(time.gmtime())
                CO2 = await self.scd.get_CO2()
                Temperature = await self.scd.get_temperature()
                Humidity = await self.scd.get_relative_humidity()
                if self.debug: print("SCD30 gelesen")
            except:
                err = True
                Timestamp = None
                CO2 = None
                Temperature = None
                Humidity = None
                if self.debug: print("SCD30 Lesefehler!")

            if err:
                err_cnt += 1
                await self.error_counter.increment()
                if self.debug: print("SCD30 Fehlerzähler erhöht auf", err_cnt)
                if err_cnt > self.max_i2c_err:
                    if self.debug: print("SCD30 Maximale Fehleranzahl erreicht!")
                    return False    # Abbruch des Tasks
            else:
                if err_cnt > 0:
                    err_cnt -= 1
                    if self.debug: print("SCD30 Fehlerzähler zurück auf", err_cnt)
                await self.meas_data.set_data([CO2,
                                               Temperature,
                                               Humidity,
                                               math_helpers.wet_bulb_temperature(Temperature, Humidity),
                                               math_helpers.dew_point(Temperature, Humidity),
                                               Timestamp])
                if self.debug: print("SCD30 Daten gespeichert")

    # CO2 Sensor IRQ triggern falls es nicht läuft (Pin bleibt HIGH wenn nicht gelesen!)
    async def scd_init_irq(self):
        while True:
            await self.start_trigger_event.wait()
            if self.irq_pin.value() == 1:  # Interrupt pin is currently set
                self.scd_timer_triggers += 1

            if self.scd_timer_triggers >= self.trigger_half_sec:  # consecutive intervals with interrupt pin set (meas rate 500ms)
                if self.debug: print("SCD30 Interrupt Start Trigger")
                self.irq_trigger_event.set()

    # selected low-level direct sensor driver function forwards
    async def stop_continuous_measurement(self, value):  # value needs to be False (= Off) to trigger
        if not value:
            await self.scd.stop_continuous_measurement()

    async def get_measurement_interval(self):
        return await self.scd.get_measurement_interval()

    async def set_measurement_interval(self, value):
        await self.scd.set_measurement_interval(value)

    async def get_self_calibration_enabled(self):
        return await self.scd.get_self_calibration_enabled()

    async def set_self_calibration_enabled(self, enabled):
        await self.scd.set_self_calibration_enabled(enabled)

    async def get_ambient_pressure(self):
        return await self.scd.get_ambient_pressure()

    async def set_ambient_pressure(self, pressure_mbar):
        await self.scd.set_ambient_pressure(pressure_mbar)

    async def get_altitude(self):
        return await self.scd.get_altitude()

    async def set_altitude(self, altitude):
        await self.scd.set_altitude(altitude)

    async def get_temperature_offset(self):
        return await self.scd.get_temperature_offset()

    async def set_temperature_offset(self, offset):
        await self.scd.set_temperature_offset(offset)

    async def get_forced_recalibration_reference(self):
        return await self.scd.get_forced_recalibration_reference()

    async def set_forced_recalibration_reference(self, reference_value):
        await self.scd.set_forced_recalibration_reference(reference_value)


class SCD30:
    """
    CircuitPython helper class for using the SCD30 CO2 sensor

    :param ~busio.I2C i2c_bus: The I2C bus the SCD30 is connected to.
    :param int ambient_pressure: Ambient pressure compensation. Defaults to :const:`0`
    :param int address: The I2C device address for the sensor. Default is :const:`0x61`

    **Quickstart: Importing and using the SCD30**

        Here is an example of using the :class:`SCD30` class.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            import adafruit_scd30

        Once this is done you can define your `board.I2C` object and define your sensor object

        .. code-block:: python

            i2c = board.I2C()   # uses board.SCL and board.SDA
            scd = adafruit_scd30.SCD30(i2c)

        Now you have access to the CO2, temperature and humidity using
        the :attr:`CO2`, :attr:`temperature` and :attr:`relative_humidity` attributes

        .. code-block:: python

            temperature = scd.temperature
            relative_humidity = scd.relative_humidity
            co2_ppm_level = scd.CO2

    """

    def __init__(
        self, i2c_bus: I2C, address: int = _SCD30_DEFAULT_ADDR
    ) -> None:

        self.i2c_device = I2CDevice(i2c_bus, address)
        self._buffer = bytearray(18)
        self._crc_buffer = bytearray(2)

        # cached readings
        self._temperature = None
        self._relative_humidity = None
        self._co2 = None

    async def setup(self) -> None:
        await self.i2c_device.setup()
        await self.reset()

    async def reset(self) -> None:
        """Perform a soft reset on the sensor, restoring default values"""
        await self._send_command(_CMD_SOFT_RESET)
        await asyncio.sleep(0.2)  # not mentioned by datasheet, but required to avoid IO error

    async def stop_continuous_measurement(self) -> None:
        """Turn off continuous measurement (turn on with ambient pressure command)"""
        await self._send_command(_CMD_STOP_CONTINUOUS_MEASUREMENT)

    async def get_measurement_interval(self) -> int:
        """Sets the interval between readings in seconds. The interval value must be from 2-1800

        .. note::
            This value will be saved and will not be reset on boot or by calling `reset`.

        """

        return await self._read_register(_CMD_SET_MEASUREMENT_INTERVAL)

    async def set_measurement_interval(self, value: int) -> None:
        if value < 2 or value > 1800:
            raise AttributeError("measurement_interval must be from 2-1800 seconds")
        await self._send_command(_CMD_SET_MEASUREMENT_INTERVAL, value)

    async def get_self_calibration_enabled(self) -> bool:
        """Enables or disables automatic self calibration (ASC). To work correctly, the sensor must
        be on and active for 7 days after enabling ASC, and exposed to fresh air for at least 1 hour
        per day. Consult the manufacturer's documentation for more information.

        .. note::
            Enabling self calibration will override any values set by specifying a
            `forced_recalibration_reference`

        .. note::
            This value will be saved and will not be reset on boot or by calling `reset`.

        """

        return await self._read_register(_CMD_AUTOMATIC_SELF_CALIBRATION) == 1

    async def set_self_calibration_enabled(self, enabled: bool) -> None:
        await self._send_command(_CMD_AUTOMATIC_SELF_CALIBRATION, enabled)
        if enabled:
            await asyncio.sleep(0.01)

    async def data_available(self) -> bool:
        """Check the sensor to see if new data is available"""
        return await self._read_register(_CMD_GET_DATA_READY)

    async def get_ambient_pressure(self) -> int:
        """Specifies the ambient air pressure at the measurement location in mBar. Setting this
        value adjusts the CO2 measurement calculations to account for the air pressure's effect on
        readings. Values must be in mBar, from 700 to 1400 mBar"""
        return await self._read_register(_CMD_CONTINUOUS_MEASUREMENT)

    async def set_ambient_pressure(self, pressure_mbar: int) -> None:
        pressure_mbar = int(pressure_mbar)
        if pressure_mbar != 0 and (pressure_mbar > 1400 or pressure_mbar < 700):
            raise AttributeError("ambient_pressure must be from 700 to 1400 mBar")
        await self._send_command(_CMD_CONTINUOUS_MEASUREMENT, pressure_mbar)

    async def get_altitude(self) -> int:
        """Specifies the altitude at the measurement location in meters above sea level. Setting
        this value adjusts the CO2 measurement calculations to account for the air pressure's effect
        on readings.

        .. note::
            This value will be saved and will not be reset on boot or by calling `reset`.
        """
        return await self._read_register(_CMD_SET_ALTITUDE_COMPENSATION)

    async def set_altitude(self, altitude: int) -> None:
        await self._send_command(_CMD_SET_ALTITUDE_COMPENSATION, int(altitude))

    async def get_temperature_offset(self) -> float:
        """Specifies the offset to be added to the reported measurements to account for a bias in
        the measured signal. Value is in degrees Celsius with a resolution of 0.01 degrees and a
        maximum value of 655.35 C

        .. note::
            This value will be saved and will not be reset on boot or by calling `reset`.

        """
        raw_offset = await self._read_register(_CMD_SET_TEMPERATURE_OFFSET)
        return raw_offset / 100.0

    async def set_temperature_offset(self, offset: Union[float, int]) -> None:
        if offset > 655.35:
            raise AttributeError(
                "Offset value must be less than or equal to 655.35 degrees Celsius"
            )

        await self._send_command(_CMD_SET_TEMPERATURE_OFFSET, int(offset * 100))

    async def get_forced_recalibration_reference(self) -> int:
        """Specifies the concentration of a reference source of CO2 placed in close proximity to the
        sensor. The value must be from 400 to 2000 ppm.

        .. note::
            Specifying a forced recalibration reference will override any calibration values
            set by Automatic Self Calibration
        """
        return await self._read_register(_CMD_SET_FORCED_RECALIBRATION_FACTOR)

    async def set_forced_recalibration_reference(self, reference_value: int) -> None:
        await self._send_command(_CMD_SET_FORCED_RECALIBRATION_FACTOR, reference_value)

    async def get_CO2(self) -> float:  # pylint:disable=invalid-name
        """Returns the CO2 concentration in PPM (parts per million)
        .. note::
            Between measurements, the most recent reading will be cached and returned.
        """
        if await self.data_available():
            await self._read_data()
        return self._co2

    async def get_temperature(self) -> float:
        """Returns the current temperature in degrees Celsius

        .. note::
            Between measurements, the most recent reading will be cached and returned.

        """
        if await self.data_available():
            await self._read_data()
        return self._temperature

    async def get_relative_humidity(self) -> float:
        """Returns the current relative humidity in %rH.

        .. note::
            Between measurements, the most recent reading will be cached and returned.

        """
        if await self.data_available():
            await self._read_data()
        return self._relative_humidity

    async def _send_command(self, command: int, arguments: Optional[int] = None) -> None:
        # if there is an argument, calculate the CRC and include it as well.
        if arguments is not None:
            self._crc_buffer[0] = arguments >> 8
            self._crc_buffer[1] = arguments & 0xFF
            self._buffer[2] = arguments >> 8
            self._buffer[3] = arguments & 0xFF
            crc = self._crc8(self._crc_buffer)
            self._buffer[4] = crc
            end_byte = 5
        else:
            end_byte = 2

        self._buffer[0] = command >> 8
        self._buffer[1] = command & 0xFF

        async with self.i2c_device as i2c:
            await i2c.write(self._buffer, end=end_byte)
        await asyncio.sleep(0.05)  # 3ms min delay

    async def _read_register(self, reg_addr: int) -> int:
        self._buffer[0] = reg_addr >> 8
        self._buffer[1] = reg_addr & 0xFF
        async with self.i2c_device as i2c:
            await i2c.write(self._buffer, end=2)
            # separate readinto because the SCD30 wants an i2c stop before the read
            # (non-repeated start)
            await asyncio.sleep(0.005)  # min 3 ms delay
            await i2c.readinto(self._buffer, end=3)
        if not self._check_crc(self._buffer[:2], self._buffer[2]):
            raise RuntimeError("CRC check failed while reading data")
        return unpack_from(">H", self._buffer[0:2])[0]

    async def _read_data(self) -> None:
        await self._send_command(_CMD_READ_MEASUREMENT)
        async with self.i2c_device as i2c:
            await i2c.readinto(self._buffer)

        crcs_good = True

        for i in range(0, 18, 3):
            crc_good = self._check_crc(self._buffer[i : i + 2], self._buffer[i + 2])
            if crc_good:
                continue
            crcs_good = False
        if not crcs_good:
            raise RuntimeError("CRC check failed while reading data")

        self._co2 = unpack(">f", self._buffer[0:2] + self._buffer[3:5])[0]
        self._temperature = unpack(">f", self._buffer[6:8] + self._buffer[9:11])[0]
        self._relative_humidity = unpack(
            ">f", self._buffer[12:14] + self._buffer[15:17]
        )[0]

    def _check_crc(self, data_bytes: ReadableBuffer, crc: int) -> bool:
        return crc == self._crc8(bytearray(data_bytes))

    @staticmethod
    def _crc8(buffer: bytearray) -> int:
        crc = 0xFF
        for byte in buffer:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
        return crc & 0xFF  # return the bottom 8 bits
