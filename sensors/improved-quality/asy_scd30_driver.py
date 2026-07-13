import time
import asyncio
import math_helpers
from micropython import const
from uasyncio import ThreadSafeFlag
from collections import namedtuple
from machine import Timer, Pin
from struct import unpack_from, unpack
from crc_checks import CRC8
from asy_i2c_driver import I2C, I2CDevice
from asy_fram_manager import AsyFramManager
from config_manager import make_dict, name_cfg
from base_classes import SensorReader, Lockable
from typing import Dict, Tuple, Union, Any, List, Callable, cast


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

_VAL_TO = const('|"TempOffs": {"def": null, "type": "float", "min": 0.0, "max": 655.35, "special": null}|')
_VAL_MI = const('|"MeasInt": {"def": null, "type": "int", "min": 2, "max": 1800, "special": null}|')
_VAL_AP = const('|"AmbPres": {"def": null, "type": "int", "min": 700, "max": 1400, "special": 0}|')
_VAL_ALT = const('|"Altitude": {"def": null, "type": "int", "min": 0, "max": 65535, "special": null}|')
_VAL_CAL = const('|"ForceCalRef": {"def": null, "type": "int", "min": 400, "max": 2000, "special": null}|')
_VAL_SC = const('|"SelfCal": {"def": null, "type": "bool", "min": null, "max": null, "special": null}|')
# TODO: Stop Measurement command
# no default value for config, params are stored on sensor

_NAME = const("SCD30")
SCD30 = namedtuple("SCD30", ("CO2", "Temp", "Hum", "WetBulb", "DewPoint", "TS"))
SCDResults = Tuple[
    Union[float, None], Union[float, None], Union[float, None], Union[int, None]
]  # CO2, temperature, humidity, timestamp


class SCD30_Reader(SensorReader):
    def __init__(
        self,
        i2c: I2C,
        irq_pin: int,
        trigger_sec: int = 3,
        max_i2c_err: int = 5,
        fram: AsyFramManager | None = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        super().__init__(
            SCD30(None, None, None, None, None, None),
            max_i2c_err,
            fram=fram,
            history_length=history_length,
            debug=debug,
        )
        self.scd = SCD30_I2C(i2c)
        self.irq_pin = Pin(irq_pin, mode=Pin.IN)
        self.start_trigger_event = ThreadSafeFlag()
        self.start_trigger_timer = Timer()
        self.trigger_half_sec = 2 * int(trigger_sec)
        self.irq_trigger_event = ThreadSafeFlag()
        self.scd_timer_triggers = 0

    def start_asy_read(self) -> asyncio.Task[bool]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_loop())

    def start_asy_init(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.scd_init_irq())

    def start_timer(self) -> None:
        self.start_trigger_timer.init(
            period=500,
            mode=Timer.PERIODIC,
            callback=lambda b: self.start_trigger_event.set(),
        )
        self.irq_pin.irq(
            trigger=self.irq_pin.IRQ_RISING,
            handler=lambda b: self.irq_trigger_event.set(),
        )

    def stop_timer(self) -> None:
        self.start_trigger_timer.deinit()

    def get_task_starters(self) -> List[Callable[[], asyncio.Task[Any]]]:
        return [self.start_asy_read, self.start_asy_init]

    def get_timer_starters(self) -> List[Callable[[], None]]:
        return [self.start_timer]

    async def get_data(self) -> SCD30:
        data = await self._get_meas_data()
        return cast(SCD30, data)

    async def get_dict_data(self) -> Dict[str, Dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data)

    async def _read_sensor_dict(self) -> Dict[str, int | float | str | bool | None]:
        ret: Dict[str, int | float | str | bool | None] = {
            name_cfg(_VAL_TO): await self.get_temperature_offset(),
            name_cfg(_VAL_MI): await self.get_measurement_interval(),
            name_cfg(_VAL_AP): await self.get_ambient_pressure(),
            name_cfg(_VAL_ALT): await self.get_altitude(),
            name_cfg(_VAL_CAL): await self.get_forced_recalibration_reference(),
            name_cfg(_VAL_SC): await self.get_self_calibration_enabled(),
        }
        return ret  # only for callback in _get_dict_cfg, is automatically inside try-except!

    async def get_dict_cfg(self) -> Dict[str, Dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(
            _NAME,
            _VAL_TO + _VAL_MI + _VAL_AP + _VAL_ALT + _VAL_CAL + _VAL_SC,
            callback=self._read_sensor_dict,
        )

    async def get_error_counter(self) -> Dict[str, Dict[str, int | List[int] | List[str]]]:
        return await self.pr.get_log(_NAME)

    async def _init_scd(self) -> bool:
        await self.pr.setup()  # required for all logged warnings and errors
        self.err_cnt_internal = 0
        try:
            await self.scd.setup()
        except Exception as e:
            await self.pr.err_s(_NAME, "Error in initial setup:", e, errno=10)
            return False  # error
        self.pr.one(_NAME, "initialized")
        return True

    async def _read_scd(self) -> SCDResults:
        try:
            timestamp = time.mktime(time.gmtime())  # type: ignore[call-arg]
            co2 = await self.scd.get_CO2()
            temperature = await self.scd.get_temperature()
            humidity = await self.scd.get_relative_humidity()
            self.pr.all(_NAME, "gelesen")
        except Exception as e:
            timestamp = co2 = temperature = humidity = None
            await self.pr.err_s(_NAME, "Lesefehler:", e, errno=11)
        return co2, temperature, humidity, timestamp

    async def _store_scd(self, results: SCDResults) -> None:
        if results[0] is None or results[1] is None or results[2] is None or results[3] is None:
            return  # don't run on invalid data

        # results: CO2, temperature, humidity, timestamp
        await self._set_meas_data(
            SCD30(
                results[0],  # CO2
                results[1],  # Temperature
                results[2],  # Humidity
                math_helpers.wet_bulb_temperature(results[1], results[2]),
                math_helpers.dew_point(results[1], results[2]),
                results[3],  # Timestamp
            )
        )
        self.pr.all(_NAME, "Daten gespeichert")

    async def read_loop(self) -> bool:
        if not await self._init_scd():  # init sensor at startup
            return False  # break and restart if init fails
        while True:
            await self.irq_trigger_event.wait()  # wait for read trigger IRQ
            self.pr.evt(_NAME, "sensor trigger")
            self.scd_timer_triggers = 0  # reset no-irq-timer
            results = await self._read_scd()  # read data
            if not await self._error_check(results, _NAME):  # check and count errors
                return False  # break and restart if too many errors
            await self._store_scd(results)  # store data in result buffer

    # CO2 Sensor IRQ triggern falls es nicht läuft (Pin bleibt HIGH wenn nicht gelesen!)
    async def scd_init_irq(self) -> None:
        while True:
            await self.start_trigger_event.wait()
            if self.irq_pin.value() == 1:  # Interrupt pin is currently set
                self.scd_timer_triggers += 1

            if (
                self.scd_timer_triggers >= self.trigger_half_sec
            ):  # consecutive intervals with interrupt pin set (meas rate 500ms)
                self.pr.evt(_NAME, "Interrupt Start Trigger")
                self.irq_trigger_event.set()

    # selected low-level direct sensor driver function forwards
    async def stop_continuous_measurement(self, value: bool) -> bool:
        if value:
            return False
        try:
            await self.scd.stop_continuous_measurement()
            return True
        except Exception:
            return False

    async def get_measurement_interval(self) -> int | None:
        try:
            return await self.scd.get_measurement_interval()
        except Exception:
            return None

    async def set_measurement_interval(self, value: int) -> bool:
        try:
            await self.scd.set_measurement_interval(value)
            return True
        except Exception:
            return False

    async def get_self_calibration_enabled(self) -> bool | None:
        try:
            return await self.scd.get_self_calibration_enabled()
        except Exception:
            return None

    async def set_self_calibration_enabled(self, enabled: bool) -> bool:
        try:
            await self.scd.set_self_calibration_enabled(enabled)
            return True
        except Exception:
            return False

    async def get_ambient_pressure(self) -> int | None:
        try:
            return await self.scd.get_ambient_pressure()
        except Exception:
            return None

    async def set_ambient_pressure(self, pressure_mbar: int | float) -> bool:
        try:
            await self.scd.set_ambient_pressure(pressure_mbar)
            return True
        except Exception:
            return False

    async def get_altitude(self) -> int | None:
        try:
            return await self.scd.get_altitude()
        except Exception:
            return None

    async def set_altitude(self, altitude: int) -> bool:
        try:
            await self.scd.set_altitude(altitude)
            return True
        except Exception:
            return False

    async def get_temperature_offset(self) -> float | None:
        try:
            return await self.scd.get_temperature_offset()
        except Exception:
            return None

    async def set_temperature_offset(self, offset: int | float) -> bool:
        try:
            await self.scd.set_temperature_offset(offset)
            return True
        except Exception:
            return False

    async def get_forced_recalibration_reference(self) -> int | None:
        try:
            return await self.scd.get_forced_recalibration_reference()
        except Exception:
            return None

    async def set_forced_recalibration_reference(self, reference_value: int) -> bool:
        try:
            await self.scd.set_forced_recalibration_reference(reference_value)
            return True
        except Exception:
            return False


class SCD30_DeviceSession(Lockable):  # lock for consecutive i2c communication and self._buffer
    def __init__(self, i2c_device: I2CDevice):
        super().__init__()
        self.i2c_device = i2c_device


class SCD30_I2C:
    def __init__(self, i2c_bus: I2C, address: int = _SCD30_DEFAULT_ADDR) -> None:
        self.i2c_scd30 = SCD30_DeviceSession(I2CDevice(i2c_bus, address))
        self._buffer = bytearray(18)
        self.crc = CRC8()

        # cached readings
        self._temperature: float | None = None
        self._relative_humidity: float | None = None
        self._co2: float | None = None

    async def setup(self) -> None:
        async with self.i2c_scd30 as scd30:  # device session
            async with scd30.i2c_device as i2c:  # bus session
                await i2c.setup()
        await self.reset()

    async def reset(self) -> None:
        # Perform a soft reset on the sensor, restoring default values
        await self._send_command(_CMD_SOFT_RESET)
        await asyncio.sleep(0.2)
        # not mentioned by datasheet, but required to avoid IO error

    async def stop_continuous_measurement(self) -> None:
        # Turn off continuous measurement (turn on with ambient pressure command)
        await self._send_command(_CMD_STOP_CONTINUOUS_MEASUREMENT)

    async def get_measurement_interval(self) -> int:
        return await self._read_register(_CMD_SET_MEASUREMENT_INTERVAL)

    async def set_measurement_interval(self, value: int) -> None:
        # Sets the interval between readings in seconds. The interval value must be from 2-1800
        # This value will be saved and will not be reset on boot or by calling `reset`.
        if value < 2 or value > 1800:
            raise AttributeError("measurement_interval must be from 2-1800 seconds")
        await self._send_command(_CMD_SET_MEASUREMENT_INTERVAL, value)

    async def get_self_calibration_enabled(self) -> bool:
        return await self._read_register(_CMD_AUTOMATIC_SELF_CALIBRATION) == 1

    async def set_self_calibration_enabled(self, enabled: bool) -> None:
        # Enables or disables automatic self calibration (ASC)
        # This value will be saved and will not be reset on boot or by calling `reset`.
        await self._send_command(_CMD_AUTOMATIC_SELF_CALIBRATION, enabled)
        if enabled:
            await asyncio.sleep(0.01)

    async def get_ambient_pressure(self) -> int:
        return await self._read_register(_CMD_CONTINUOUS_MEASUREMENT)

    async def set_ambient_pressure(self, pressure_mbar: int | float) -> None:
        # Specifies the ambient air pressure at the measurement location in mBar.
        pressure_mbar = int(pressure_mbar)
        if pressure_mbar != 0 and (pressure_mbar > 1400 or pressure_mbar < 700):
            raise AttributeError("ambient_pressure must be from 700 to 1400 mBar")
        await self._send_command(_CMD_CONTINUOUS_MEASUREMENT, pressure_mbar)

    async def get_altitude(self) -> int:
        return await self._read_register(_CMD_SET_ALTITUDE_COMPENSATION)

    async def set_altitude(self, altitude: int) -> None:
        # Specifies the altitude at the measurement location in meters above sea level.
        # This value will be saved and will not be reset on boot or by calling `reset`.
        await self._send_command(_CMD_SET_ALTITUDE_COMPENSATION, int(altitude))

    async def get_temperature_offset(self) -> float:
        raw_offset = await self._read_register(_CMD_SET_TEMPERATURE_OFFSET)
        return raw_offset / 100.0

    async def set_temperature_offset(self, offset: float | int) -> None:
        # Specifies the offset to be added to the reported measurements to account for a bias in
        # the measured signal.
        # This value will be saved and will not be reset on boot or by calling `reset`.
        if offset > 655.35:
            raise AttributeError("Offset value must be less than or equal to 655.35 degrees Celsius")

        await self._send_command(_CMD_SET_TEMPERATURE_OFFSET, int(offset * 100))

    async def get_forced_recalibration_reference(self) -> int:
        return await self._read_register(_CMD_SET_FORCED_RECALIBRATION_FACTOR)

    async def set_forced_recalibration_reference(self, reference_value: int) -> None:
        # Specifies the concentration of a reference source of CO2
        await self._send_command(_CMD_SET_FORCED_RECALIBRATION_FACTOR, reference_value)

    async def get_CO2(self) -> float | None:
        # Returns the CO2 concentration in PPM (parts per million)
        await self._read_data()
        return self._co2

    async def get_temperature(self) -> float | None:
        # Returns the current temperature in degrees Celsius
        await self._read_data()
        return self._temperature

    async def get_relative_humidity(self) -> float | None:
        # Returns the current relative humidity in %rH.
        await self._read_data()
        return self._relative_humidity

    async def _send_command(self, command: int, arguments: int | None = None) -> None:
        async with self.i2c_scd30 as scd30:
            async with scd30.i2c_device as i2c:
                await self._send_dev_command(i2c, command, arguments)

    async def _send_dev_command(self, i2c: I2CDevice, command: int, arguments: int | None = None) -> None:
        # if there is an argument, calculate the CRC and include it as well.
        self._buffer[0] = command >> 8
        self._buffer[1] = command & 0xFF
        end_byte = 2
        if arguments is not None:
            self._buffer[2] = arguments >> 8
            self._buffer[3] = arguments & 0xFF
            if await self.crc.add_into(self._buffer, 2, start=2) != 3:
                raise RuntimeError("CRC generation failed!")
            end_byte = 5
        await i2c.write(self._buffer, end=end_byte)
        await asyncio.sleep(0.05)  # delay for response

    async def _read_register(self, reg_addr: int) -> int:
        async with self.i2c_scd30 as scd30:
            async with scd30.i2c_device as i2c:
                ret = await self._read_dev_register(i2c, reg_addr)
        return ret

    async def _read_dev_register(self, i2c: I2CDevice, reg_addr: int) -> int:
        self._buffer[0] = reg_addr >> 8
        self._buffer[1] = reg_addr & 0xFF
        await i2c.write(self._buffer, end=2)
        # separate readinto because the SCD30 wants an i2c stop before the read
        # (non-repeated start)
        await asyncio.sleep(0.05)  # delay for response
        # min 3 ms delay
        await i2c.readinto(self._buffer, end=3)
        if await self.crc.check_from(self._buffer, 3) != 2:
            raise RuntimeError("CRC check failed while reading data")
        return cast(int, unpack_from(">H", self._buffer)[0])

    async def _read_data(self) -> None:
        async with self.i2c_scd30 as scd30:
            async with scd30.i2c_device as i2c:
                new_data = await self._read_dev_register(i2c, _CMD_GET_DATA_READY) > 0
            await asyncio.sleep(0)
            if new_data:
                async with scd30.i2c_device as i2c:
                    await self._send_dev_command(i2c, _CMD_READ_MEASUREMENT)
                await asyncio.sleep(0)
                async with scd30.i2c_device as i2c:
                    await i2c.readinto(self._buffer)

            if not new_data:
                return

            crcs_good = True
            for i in range(0, 18, 3):
                if await self.crc.check_from(self._buffer, 3, start=i) == 2:
                    continue
                crcs_good = False
            if not crcs_good:
                raise RuntimeError("CRC check failed while reading data")

            self._co2 = cast(float, unpack(">f", self._buffer[0:2] + self._buffer[3:5])[0])
            self._temperature = cast(float, unpack(">f", self._buffer[6:8] + self._buffer[9:11])[0])
            self._relative_humidity = cast(float, unpack(">f", self._buffer[12:14] + self._buffer[15:17])[0])
