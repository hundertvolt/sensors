# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
# SPDX-License-Identifier: MIT
# From adafruit_scd30, restructured for asyncio + MicroPython - see THIRD_PARTY_LICENSES.md.

"""Async I2C driver for the Sensirion SCD30 CO2/temperature/relative-humidity sensor. SCD30_I2C
wraps the raw command set (16-bit commands, CRC-8 protected); SCD30_Reader runs the read loop plus an IRQ-pin self-healing trigger, feeding CO2/Temp/Hum/WetBulb/DewPoint (see SPECIFICATION.md Part C).
Source: Sensirion CO2 Sensors SCD30 Interface Description & Datasheet (datasheets/scd30/).
"""

import asyncio
import math
from collections import namedtuple
from struct import unpack, unpack_from

from machine import Pin, Timer
from micropython import const

import math_helpers
from asy_base_classes import Lockable, SensorReader, utc_now
from asy_config_manager import compare_before_write, make_dict, name_cfg
from asy_crc_checks import CRC8
from asy_i2c_driver import I2C, I2CDevice
from asy_print_log import DEFAULT_LOG, LogConfig

try:
    from typing import TYPE_CHECKING, cast
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

    def cast(_typ: object, val: "T") -> "T":  # type: ignore[no-redef]  # no-op at runtime either way
        return val

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, TypeVar

    from asy_base_classes import JsonMapping, TimerStarter
    from asy_config_manager import CfgValue, ConfigSchema, WriteValidity
    from asy_print_log import ErrorLog

    T = TypeVar("T")  # narrows a struct.unpack() result for the cast() shim above


# Codes from the global catalog (buildgen/error_catalog.json; SPECIFICATION.md Part C.7.1).
_ERR_INIT = const(10)
_ERR_READ = const(11)
_ERR_CHIP_GET = const(12)
_ERR_CHIP_SET = const(13)
_ERR_BAD_ARG = const(21)

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
_CMD_READ_FIRMWARE_VERSION = const(0xD100)

_VAL_TEMP_OFFSET = const((("TempOffset", "float", None, 0.0, 655.35, None),))
_VAL_MEAS_INTERVAL = const((("MeasInterval", "int", None, 2, 1800, None),))
_VAL_AMB_PRES = const((("AmbPres", "int", None, 700, 1400, 0),))
_VAL_ALTITUDE = const((("Altitude", "int", None, 0, 65535, None),))
_VAL_FORCE_CAL_REF = const((("ForceCalRef", "int", None, 400, 2000, None),))
_VAL_SELF_CAL = const((("SelfCal", "bool", None, None, None, None),))

# @web-group section=sensors submitGroup=self label="SCD30 — CO2, Temperature, Humidity" submit=true
# @web TempOffset section=sensors submitGroup=self label="Temperature Offset" unit="K"
# @web MeasInterval section=sensors submitGroup=self label="Measurement Interval" unit="s"
# @web AmbPres section=sensors submitGroup=self label="Ambient Pressure (starts continuous measurement)" unit="hPa" special:0="Compensation off / use Altitude" alwaysExecuted=true
# @web Altitude section=sensors submitGroup=self label="Altitude above sea level" unit="m" description="Only used if Ambient Pressure is 0."
# @web ForceCalRef section=sensors submitGroup=self label="Forced Calibration Reference" unit="ppm" alwaysExecuted=true
# @web SelfCal section=sensors submitGroup=self label="Automatic Self-Calibration"

# Same datasheet limits the _VAL_* schema entries above carry, named for the driver's own argument
# validation (Interface Description sections 1.4.1-1.4.6).
_MEAS_INTERVAL_MIN = const(2)
_MEAS_INTERVAL_MAX = const(1800)
_AMB_PRESSURE_MIN = const(700)
_AMB_PRESSURE_MAX = const(1400)
_ALTITUDE_MAX = const(65535)
_TEMP_OFFSET_MAX = const(655.35)
_FORCED_RECAL_MIN = const(400)
_FORCED_RECAL_MAX = const(2000)
# A 16-bit word on this bus is 2 payload bytes plus one CRC-8 byte - what CRC8.add_into()/
# check_from() return on success (total written / payload length respectively).
_WORD_BYTES = const(2)
_WORD_CRC_BYTES = const(3)
# The order a PUT's chip writes are applied in, whatever the body's key order.
_APPLY_ORDER = const(("TempOffset", "MeasInterval", "AmbPres", "Altitude", "ForceCalRef", "SelfCal"))
# Waits between a command and its result, after a soft reset, and the start-trigger timer's period.
# @tunable scd30.cmd_response_wait_s = 0.05
_CMD_RESPONSE_WAIT_S = const(0.05)
# @tunable scd30.asc_enable_wait_s = 0.01
_ASC_ENABLE_WAIT_S = const(0.01)
# @tunable scd30.soft_reset_wait_s = 2.5
_SOFT_RESET_WAIT_S = const(2.5)
# @tunable scd30.start_trigger_period_ms = 500
_START_TRIGGER_PERIOD_MS = const(500)


def _snapshot_dict(snap: tuple[float, int, int, int, int, bool]) -> "dict[str, CfgValue]":
    # The six chip-stored settings by name, from one get_config_snapshot() tuple.
    return {
        name_cfg(_VAL_TEMP_OFFSET): snap[0],
        name_cfg(_VAL_MEAS_INTERVAL): snap[1],
        name_cfg(_VAL_AMB_PRES): snap[2],
        name_cfg(_VAL_ALTITUDE): snap[3],
        name_cfg(_VAL_FORCE_CAL_REF): snap[4],
        name_cfg(_VAL_SELF_CAL): snap[5],
    }


# Deliberately no _VAL_* entry for "ContMeas": the SCD30 cannot report whether continuous
# measurement is running, and these params live on the sensor rather than in a local cache. The
# freestanding @web tag below supplies what a real _VAL_* tuple would otherwise let buildgen infer.
# @web ContMeas section=sensors submitGroup=self kind=toggle label="Continuous Measurement" onLabel="On" offLabel="Off" description="Setting this to Off stops continuous measurement; restart it via Ambient Pressure above." defaultValue=true alwaysExecuted=true

_NAME = const("SCD30")
# Kept as a literal tuple inline (not `_FIELDS` below) because mypy's namedtuple plugin can only
# infer field names from a literal at the call site, not through a variable indirection.
SCD30 = namedtuple("SCD30", ("CO2", "Temp", "Hum", "WetBulb", "DewPoint", "TS"))
_FIELDS = const(("CO2", "Temp", "Hum", "WetBulb", "DewPoint", "TS"))  # kept in sync with SCD30's own fields above

# @web-group section=measurements submitGroup=self label="SCD30 — CO2, Temperature, Humidity"
# @web CO2 section=measurements submitGroup=self kind=readonly label="CO2" unit="ppm"
# @web Temp section=measurements submitGroup=self kind=readonly label="Temperature" unit="°C"
# @web Hum section=measurements submitGroup=self kind=readonly label="Relative Humidity" unit="%"
# @web WetBulb section=measurements submitGroup=self kind=readonly label="Wet Bulb Temperature" unit="°C"
# @web DewPoint section=measurements submitGroup=self kind=readonly label="Dew Point" unit="°C"
# @web TS section=measurements submitGroup=self kind=readonly label="Timestamp" format=epoch

# Datasheets/scd30/..._Interface_Description.pdf p.2: clock stretching is normally <=30ms but
# reaches 150ms once a day for internal calibration, past rp2's own 50ms I2C default. Enforced as a
# generator-checked build requirement (Part L.5), not a comment each TOML author must remember.
# @requires bus.timeout>=200000
# Datasheet hard maximum, same source (Interface Description p.2): "Maximal I2C speed is
# 100 kHz" - Sensirion recommends 50 kHz or less, which every device TOML uses today.
# @requires bus.frequency<=100000
# @wiring fram_target FRAMManager log optional kwarg

if TYPE_CHECKING:
    SCDResults = tuple[float | None, float | None, float | None, int | None]  # CO2, temperature, humidity, timestamp


def _temp_offset_ticks(offset: float) -> int:
    # Nearest 0.01 degC tick, not truncation: in float32 130 of the 2001 two-decimal inputs land one tick low when truncated (0.00-20.00; offset is validated >= 0 first).
    return int(offset * 100 + 0.5)


class SCD30_Reader(SensorReader):
    def __init__(
        self,
        i2c: I2C,
        irq_pin: int,
        trigger_s: int = 3,
        # @tunable module.max_error = 5
        max_module_error: int = 5,
        name_ext: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        super().__init__(
            SCD30(None, None, None, None, None, None), _NAME, max_module_error=max_module_error, name_ext=name_ext, log=log,
        )
        self._scd = SCD30_I2C(i2c)
        self._irq_pin = Pin(irq_pin, mode=Pin.IN)
        self._base_trigger_event = asyncio.ThreadSafeFlag()
        self._start_trigger_timer = Timer()
        self._trigger_half_ticks = 2 * int(trigger_s)
        self._read_event = asyncio.ThreadSafeFlag()
        self._scd_timer_triggers = 0

    async def _get_mgr_cfg(self, cfg: list[str]) -> "dict[str, CfgValue] | None":
        # The chip is this module's config store (SPECIFICATION.md C.4.3).
        current = await self._config_snapshot()
        if current is None:
            return None
        return {key: current[key] for key in cfg if key in current}

    async def _set_mgr_cfg(self, data: "JsonMapping", cfg_vals: "ConfigSchema") -> "tuple[bool, WriteValidity]":
        # Compare-before-write against a fresh chip snapshot, writes in _APPLY_ORDER, ContMeas last. "a PUT whose
        # get_config_snapshot() fails is refused as a whole, nothing written, the response reports the failure,
        # as legacy" (owner, 2026-09-29).
        rest = dict(data)
        has_cont_meas = "ContMeas" in rest
        cont_meas = rest.pop("ContMeas", None)
        current: dict[str, CfgValue] = {}
        if has_cont_meas or any(key in rest for key in _APPLY_ORDER):  # a body with no chip key reads no snapshot
            snapshot = await self._config_snapshot()
            if snapshot is None:
                return False, {}
            current = snapshot
        # TempOffset compares in chip ticks; the primitive applies the rounding only to a value the schema validated as a float.
        resolution = {"TempOffset": _temp_offset_ticks}
        outcome = compare_before_write(rest, cfg_vals, current, always=("AmbPres", "ForceCalRef"), resolution=resolution)  # type: ignore[arg-type]
        if outcome is None:
            return False, {}
        write, results = outcome
        for key, result in results.items():
            if result == "Invalid":
                await self.pr.err_s("Invalid value for", key, errno=_ERR_BAD_ARG)
        setters = (
            self.set_temperature_offset,
            self.set_measurement_interval,
            self.set_ambient_pressure,
            self.set_altitude,
            self.set_forced_recalibration_reference,
            self.set_self_calibration_enabled,
        )
        for key, setter in zip(_APPLY_ORDER, setters):  # noqa: B905 - MicroPython zip() rejects strict=
            # write[key] is the value the schema validated and coerced for exactly this key's setter.
            if key in write and not await setter(write[key]):  # type: ignore[arg-type]
                results[key] = "Failed"
        if has_cont_meas:
            # ContMeas is a command, not a stored value: True keeps the chip running (nothing to send),
            # False stops it - after the writes, so an AmbPres in the same body cannot restart it.
            if type(cont_meas) is not bool:
                results["ContMeas"] = "Invalid"
                await self.pr.err_s("Invalid value for ContMeas", errno=_ERR_BAD_ARG)
            elif cont_meas:
                results["ContMeas"] = "Valid"
            else:
                results["ContMeas"] = "Valid" if await self.stop_continuous_measurement(value=False) else "Failed"
        return True, results

    async def _config_snapshot(self) -> "dict[str, CfgValue] | None":
        # One batched read (get_config_snapshot()), not six separately-locked get_*() calls, so a
        # concurrent write never mixes pre- and post-write values; a failure logs CHIP_GET and is None.
        try:
            snap = await self._scd.get_config_snapshot()
        except Exception as e:
            await self.pr.err_s("Error reading the config snapshot:", e, errno=_ERR_CHIP_GET)
            return None
        return _snapshot_dict(snap)

    async def _init_scd(self) -> bool:
        # Continuous measurement is never started here: the first ambient-pressure PUT starts it, and
        # the chip keeps it across power cycles (SPECIFICATION.md A.4; owner, 2026-09-26).
        self._err_cnt_internal = 0
        try:
            await self._scd.setup()
        except Exception as e:
            await self.pr.err_s("Error in initial setup:", e, errno=_ERR_INIT)
            return False
        self.pr.one("initialized")
        return True

    # Trigger the CO2 sensor IRQ if it isn't running (pin stays HIGH if not read!)
    async def _irq_loop(self) -> None:
        while True:
            await self._base_trigger_event.wait()
            if self._irq_pin.value() == 1:
                self._scd_timer_triggers += 1

            if self._scd_timer_triggers >= self._trigger_half_ticks:  # consecutive intervals seen (500ms rate)
                self.pr.evt("Interrupt Start Trigger")
                self._read_event.set()

    async def _read_loop(self) -> bool:
        if not await self._init_scd():
            return False
        while True:
            await self._read_event.wait()
            self.pr.evt("sensor trigger")
            self._scd_timer_triggers = 0
            results = await self._read_scd()
            # A failed read clears every measured value; TS alone is None until the first NTP sync, which is no failure.
            if not await self._error_check(results, condition=results[0] is None):
                return False
            await self._store_scd(results)

    async def _read_scd(self) -> "SCDResults":
        timestamp = utc_now()  # None until the NTP client has set the clock this boot
        try:
            # read_measurement() must run exactly once per cycle, before the getters below.
            await self._scd.read_measurement()
            co2 = await self._scd.get_CO2()
            temperature = await self._scd.get_temperature()
            humidity = await self._scd.get_relative_humidity()
            self.pr.all("read")
        except Exception as e:
            co2 = temperature = humidity = None
            await self.pr.err_s("Read failed:", e, errno=_ERR_READ)
        return co2, temperature, humidity, timestamp

    async def _store_scd(self, results: "SCDResults") -> None:
        if results[0] is None or results[1] is None or results[2] is None:
            return  # the timestamp may be None before the first sync
        await self._set_meas_data(
            SCD30(
                CO2=results[0],
                Temp=results[1],
                Hum=results[2],
                WetBulb=math_helpers.wet_bulb_temperature(results[1], results[2]),
                DewPoint=math_helpers.dew_point(results[1], results[2]),
                TS=results[3],
            ),
        )
        self.pr.all("data stored")

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_read, self.start_asy_irq]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return [self.start_timer]

    def start_asy_irq(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._irq_loop())

    def start_asy_read(self) -> asyncio.Task[bool]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._read_loop())

    def start_timer(self) -> None:
        try:
            self._start_trigger_timer.init(
                period=_START_TRIGGER_PERIOD_MS,
                mode=Timer.PERIODIC,
                callback=lambda _b: self._base_trigger_event.set(),
            )
        except (MemoryError, OSError) as e:  # alarm-pool exhaustion (ENOMEM) - degrades gracefully
            # instead of crashing the caller (this sensor just never gets triggered this cycle).
            self.pr.err("Could not start timer:", e)
        self._irq_pin.irq(
            trigger=self._irq_pin.IRQ_RISING,
            handler=lambda _b: self._read_event.set(),
        )

    def stop_timer(self) -> None:
        self._start_trigger_timer.deinit()

    async def get_altitude(self) -> int | None:
        try:
            return await self._scd.get_altitude()
        except Exception as e:
            await self.pr.err_s("Error reading altitude:", e, errno=_ERR_CHIP_GET)
            return None

    async def get_ambient_pressure(self) -> int | None:
        try:
            return await self._scd.get_ambient_pressure()
        except Exception as e:
            await self.pr.err_s("Error reading ambient pressure:", e, errno=_ERR_CHIP_GET)
            return None

    def get_cfg_schema(self) -> "ConfigSchema":
        # SCD30_Reader is a plain SensorReader with no local cfgmgr, so it does not inherit
        # SensorReaderConfig.get_cfg_schema() - but _put_sensors() calls that uniformly on every
        # registered sensor, and without this every PUT /sensors touching SCD30 raised a 500.
        return _VAL_TEMP_OFFSET + _VAL_MEAS_INTERVAL + _VAL_AMB_PRES + _VAL_ALTITUDE + _VAL_FORCE_CAL_REF + _VAL_SELF_CAL

    async def get_data(self) -> SCD30:
        # Narrows to this Reader's concrete SCD30 - see SPECIFICATION.md C.4.2's get_data() convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(self.name, _VAL_TEMP_OFFSET + _VAL_MEAS_INTERVAL + _VAL_AMB_PRES + _VAL_ALTITUDE + _VAL_FORCE_CAL_REF + _VAL_SELF_CAL)

    async def get_dict_data(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        data = await self.get_data()
        return make_dict(data, _FIELDS, name=self.name)

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def get_forced_recalibration_reference(self) -> int | None:
        try:
            return await self._scd.get_forced_recalibration_reference()
        except Exception as e:
            await self.pr.err_s("Error reading forced recalibration reference:", e, errno=_ERR_CHIP_GET)
            return None

    async def get_measurement_interval(self) -> int | None:
        try:
            return await self._scd.get_measurement_interval()
        except Exception as e:
            await self.pr.err_s("Error reading measurement interval:", e, errno=_ERR_CHIP_GET)
            return None

    async def get_self_calibration_enabled(self) -> bool | None:
        try:
            return await self._scd.get_self_calibration_enabled()
        except Exception as e:
            await self.pr.err_s("Error reading self calibration enabled:", e, errno=_ERR_CHIP_GET)
            return None

    async def get_temperature_offset(self) -> float | None:
        try:
            return await self._scd.get_temperature_offset()
        except Exception as e:
            await self.pr.err_s("Error reading temperature offset:", e, errno=_ERR_CHIP_GET)
            return None

    async def set_altitude(self, altitude: int) -> bool:
        try:
            await self._scd.set_altitude(altitude)
        except Exception as e:
            await self.pr.err_s("Error setting altitude:", e, errno=_ERR_CHIP_SET)
            return False
        else:
            return True

    async def set_ambient_pressure(self, pressure_mbar: float) -> bool:
        try:
            await self._scd.set_ambient_pressure(pressure_mbar)
        except Exception as e:
            await self.pr.err_s("Error setting ambient pressure:", e, errno=_ERR_CHIP_SET)
            return False
        else:
            return True

    async def set_forced_recalibration_reference(self, reference_value: int) -> bool:
        try:
            await self._scd.set_forced_recalibration_reference(reference_value)
        except Exception as e:
            await self.pr.err_s("Error setting forced recalibration reference:", e, errno=_ERR_CHIP_SET)
            return False
        else:
            return True

    async def set_measurement_interval(self, value: int) -> bool:
        try:
            await self._scd.set_measurement_interval(value)
        except Exception as e:
            await self.pr.err_s("Error setting measurement interval:", e, errno=_ERR_CHIP_SET)
            return False
        else:
            return True

    async def set_self_calibration_enabled(self, enabled: bool) -> bool:
        try:
            await self._scd.set_self_calibration_enabled(enabled)
        except Exception as e:
            await self.pr.err_s("Error setting self calibration enabled:", e, errno=_ERR_CHIP_SET)
            return False
        else:
            return True

    async def set_temperature_offset(self, offset: float) -> bool:
        try:
            await self._scd.set_temperature_offset(offset)
        except Exception as e:
            await self.pr.err_s("Error setting temperature offset:", e, errno=_ERR_CHIP_SET)
            return False
        else:
            return True

    # Selected low-level driver forwards (stop_continuous_measurement() and the chip-backed get_*()/set_*()):
    # each failure is logged via self.pr (not swallowed silently) so a transient bus fault on a REST-triggered
    # config get/set stays visible in the sensor's own error history, not just a bare None/False back to the caller.
    async def stop_continuous_measurement(self, *, value: bool) -> bool:
        # value is the desired ContMeas state; True (keep running) is a no-op, only False stops it.
        if value:
            return False
        try:
            await self._scd.stop_continuous_measurement()
        except Exception as e:
            await self.pr.err_s("Error stopping continuous measurement:", e, errno=_ERR_CHIP_SET)
            return False
        else:
            return True


class SCD30_DeviceSession(Lockable):  # lock for consecutive i2c communication and self._buffer
    def __init__(self, i2c_device: I2CDevice) -> None:
        super().__init__()
        self.i2c_device = i2c_device


class SCD30_I2C:
    def __init__(self, i2c_bus: I2C, address: int = _SCD30_DEFAULT_ADDR) -> None:
        self._i2c_scd30 = SCD30_DeviceSession(I2CDevice(i2c_bus, address))
        self._buffer = bytearray(18)
        self.crc = CRC8()

        # cached readings
        self._temperature: float | None = None
        self._relative_humidity: float | None = None
        self._co2: float | None = None

    async def _read_dev_register(self, i2c: I2CDevice, reg_addr: int) -> int:
        self._buffer[0] = reg_addr >> 8
        self._buffer[1] = reg_addr & 0xFF
        if not await i2c.write(self._buffer, end=2):
            raise OSError("I2C bus not initialized")
        # Separate readinto: the SCD30 has no repeated-start, so this stops the bus first; the
        # delay clears the datasheet's >3ms minimum (Interface Description 1.4.4).
        await asyncio.sleep(_CMD_RESPONSE_WAIT_S)
        if not await i2c.readinto(self._buffer, end=3):
            raise OSError("I2C bus not initialized")  # before the CRC check: a stale buffer would pass it
        if await self.crc.check_from(self._buffer, 3) != _WORD_BYTES:
            raise RuntimeError("CRC check failed while reading data")
        return cast(int, unpack_from(">H", self._buffer)[0])

    async def _read_register(self, reg_addr: int) -> int:
        async with self._i2c_scd30 as scd30, scd30.i2c_device as i2c:
            return await self._read_dev_register(i2c, reg_addr)

    async def _send_command(self, command: int, arguments: int | None = None) -> None:
        async with self._i2c_scd30 as scd30, scd30.i2c_device as i2c:
            await self._send_dev_command(i2c, command, arguments)

    async def _send_dev_command(self, i2c: I2CDevice, command: int, arguments: int | None = None) -> None:
        # if there is an argument, calculate the CRC and include it as well.
        self._buffer[0] = command >> 8
        self._buffer[1] = command & 0xFF
        end_byte = 2
        if arguments is not None:
            self._buffer[2] = arguments >> 8
            self._buffer[3] = arguments & 0xFF
            if await self.crc.add_into(self._buffer, 2, start=2) != _WORD_CRC_BYTES:
                raise RuntimeError("CRC generation failed")
            end_byte = 5
        if not await i2c.write(self._buffer, end=end_byte):
            raise OSError("I2C bus not initialized")
        await asyncio.sleep(_CMD_RESPONSE_WAIT_S)  # delay for response

    async def get_CO2(self) -> float | None:
        # Pure cache read from the last read_measurement() call, no I2C of its own - see read_measurement()'s
        # comment for why it, get_temperature() and get_relative_humidity() must never re-check data-ready.
        return self._co2

    async def get_altitude(self) -> int:
        return await self._read_register(_CMD_SET_ALTITUDE_COMPENSATION)

    async def get_ambient_pressure(self) -> int:
        return await self._read_register(_CMD_CONTINUOUS_MEASUREMENT)

    async def get_config_snapshot(self) -> tuple[float, int, int, int, int, bool]:
        # One device-session lock hold across all 6 config registers, closing the torn-read window a
        # concurrent set_*() could land inside mid-batch. Same "allowed to raise" layer as every
        # other SCD30_I2C method: a mid-batch fault fails the snapshot, never mixes fresh and stale.
        async with self._i2c_scd30 as scd30, scd30.i2c_device as i2c:
            temp_offset = await self._read_dev_register(i2c, _CMD_SET_TEMPERATURE_OFFSET) / 100.0
            measurement_interval = await self._read_dev_register(i2c, _CMD_SET_MEASUREMENT_INTERVAL)
            ambient_pressure = await self._read_dev_register(i2c, _CMD_CONTINUOUS_MEASUREMENT)
            altitude = await self._read_dev_register(i2c, _CMD_SET_ALTITUDE_COMPENSATION)
            frc = await self._read_dev_register(i2c, _CMD_SET_FORCED_RECALIBRATION_FACTOR)
            self_cal = await self._read_dev_register(i2c, _CMD_AUTOMATIC_SELF_CALIBRATION) == 1
        return temp_offset, measurement_interval, ambient_pressure, altitude, frc, self_cal

    async def get_forced_recalibration_reference(self) -> int:
        # Volatile readback: always returns 400 after a power cycle regardless of the last FRC
        # value applied - the calibration curve update itself is permanent, just not this readback.
        return await self._read_register(_CMD_SET_FORCED_RECALIBRATION_FACTOR)

    async def get_measurement_interval(self) -> int:
        return await self._read_register(_CMD_SET_MEASUREMENT_INTERVAL)

    async def get_relative_humidity(self) -> float | None:
        return self._relative_humidity

    async def get_self_calibration_enabled(self) -> bool:
        return await self._read_register(_CMD_AUTOMATIC_SELF_CALIBRATION) == 1

    async def get_temperature(self) -> float | None:
        return self._temperature

    async def get_temperature_offset(self) -> float:
        raw_offset = await self._read_register(_CMD_SET_TEMPERATURE_OFFSET)
        return raw_offset / 100.0

    async def set_altitude(self, altitude: int) -> None:
        # NVM-persisted. Validated before truncating - see set_ambient_pressure()'s comment for
        # why int(-0.5) == 0 would otherwise slip through.
        if altitude < 0 or altitude > _ALTITUDE_MAX:
            raise ValueError("altitude must be from 0 to 65535 meters")
        await self._send_command(_CMD_SET_ALTITUDE_COMPENSATION, int(altitude))

    async def set_ambient_pressure(self, pressure_mbar: float) -> None:
        # 0x0010 doubles as "trigger continuous measurement" and is NVM-persisted (Interface
        # Description 1.4.1). Validated before truncating - int(-0.5) == 0 would otherwise slip
        # through as the "disable" value instead of being rejected; NaN is rejected explicitly too.
        if pressure_mbar != pressure_mbar:  # NaN is the only value unequal to itself
            raise ValueError("ambient_pressure must not be NaN")
        if pressure_mbar != 0 and (pressure_mbar > _AMB_PRESSURE_MAX or pressure_mbar < _AMB_PRESSURE_MIN):
            raise ValueError("ambient_pressure must be from 700 to 1400 mBar")
        await self._send_command(_CMD_CONTINUOUS_MEASUREMENT, int(pressure_mbar))

    async def set_forced_recalibration_reference(self, reference_value: int) -> None:
        if reference_value < _FORCED_RECAL_MIN or reference_value > _FORCED_RECAL_MAX:
            raise ValueError("forced_recalibration_reference must be from 400 to 2000 ppm")
        await self._send_command(_CMD_SET_FORCED_RECALIBRATION_FACTOR, reference_value)

    async def set_measurement_interval(self, value: int) -> None:
        # NVM-persisted - survives reset() and power cycles.
        if value < _MEAS_INTERVAL_MIN or value > _MEAS_INTERVAL_MAX:
            raise ValueError("measurement_interval must be from 2-1800 seconds")
        await self._send_command(_CMD_SET_MEASUREMENT_INTERVAL, value)

    async def set_self_calibration_enabled(self, enabled: bool) -> None:
        # NVM-persisted - survives reset() and power cycles.
        await self._send_command(_CMD_AUTOMATIC_SELF_CALIBRATION, enabled)
        if enabled:
            await asyncio.sleep(_ASC_ENABLE_WAIT_S)

    async def set_temperature_offset(self, offset: float) -> None:
        # NVM-persisted - survives reset() and power cycles. NaN rejected explicitly first - see
        # set_ambient_pressure()'s comment. Sent as the nearest tick (_temp_offset_ticks()).
        if offset != offset:  # NaN is the only value unequal to itself
            raise ValueError("temperature_offset must not be NaN")
        if offset < 0 or offset > _TEMP_OFFSET_MAX:
            raise ValueError("temperature_offset must be from 0 to 655.35 degrees Celsius")
        await self._send_command(_CMD_SET_TEMPERATURE_OFFSET, _temp_offset_ticks(offset))

    async def read_measurement(self) -> None:
        # Call exactly once per cycle (data-ready clears the instant it's read - Interface
        # Description 1.4.4); a second call would wipe fresh data back to None. If not ready,
        # leaves the cache untouched, matching the legacy driver.
        async with self._i2c_scd30 as scd30:
            async with scd30.i2c_device as i2c:
                new_data = await self._read_dev_register(i2c, _CMD_GET_DATA_READY) > 0
            await asyncio.sleep(0)
            if new_data:
                async with scd30.i2c_device as i2c:
                    await self._send_dev_command(i2c, _CMD_READ_MEASUREMENT)
                await asyncio.sleep(0)
                async with scd30.i2c_device as i2c:
                    if not await i2c.readinto(self._buffer):
                        raise OSError("I2C bus not initialized")

            if not new_data:
                return

            crcs_good = True
            for i in range(0, 18, 3):
                if await self.crc.check_from(self._buffer, 3, start=i) == _WORD_BYTES:
                    continue
                crcs_good = False
            if not crcs_good:
                raise RuntimeError("CRC check failed while reading data")

            co2 = cast(float, unpack(">f", self._buffer[0:2] + self._buffer[3:5])[0])
            temperature = cast(float, unpack(">f", self._buffer[6:8] + self._buffer[9:11])[0])
            humidity = cast(float, unpack(">f", self._buffer[12:14] + self._buffer[15:17])[0])
            # The words are raw IEEE-754 and CRC-valid NaN/inf still decode; MicroPython's json.dumps()
            # would ship them as bare nan/inf, breaking the whole page (Part F.1). A failed read instead.
            if not (math.isfinite(co2) and math.isfinite(temperature) and math.isfinite(humidity)):
                raise ValueError(f"non-finite measurement (co2={co2}, t={temperature}, rh={humidity})")
            self._co2 = co2
            self._temperature = temperature
            self._relative_humidity = humidity

    async def reset(self) -> None:
        await self._send_command(_CMD_SOFT_RESET)
        # Boot-up is documented as <2s (Interface Description 1.1); wait the full bound since this
        # also runs on every failure-triggered restart, not just cold boot.
        await asyncio.sleep(_SOFT_RESET_WAIT_S)

    async def setup(self) -> bool:
        async with self._i2c_scd30 as scd30, scd30.i2c_device as i2c:
            await i2c.setup()
        # CRC-valid firmware-version read confirms a real SCD30 is responding (matches
        # BMP3xx/SGP40's identity checks) - the version value itself isn't checked.
        await self._read_register(_CMD_READ_FIRMWARE_VERSION)
        await self.reset()
        return True

    async def stop_continuous_measurement(self) -> None:
        # Turn off continuous measurement (turn on with ambient pressure command)
        await self._send_command(_CMD_STOP_CONTINUOUS_MEASUREMENT)
