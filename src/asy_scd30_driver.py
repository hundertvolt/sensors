# SPDX-FileCopyrightText: Copyright (c) 2020 Bryan Siepert for Adafruit Industries
# SPDX-License-Identifier: MIT
# From adafruit_scd30, restructured for asyncio + MicroPython - see THIRD_PARTY_LICENSES.md.

"""Async I2C driver for the Sensirion SCD30 CO2/temperature/relative-humidity sensor. SCD30_I2C
wraps the raw command set (16-bit commands, CRC-8 protected); SCD30_Reader runs the read loop plus an IRQ-pin self-healing trigger, and publishes the readings with wet bulb, dew point and the forced-recalibration readiness code (see SPECIFICATION.md Part C).
Source: Sensirion CO2 Sensors SCD30 Interface Description & Datasheet (datasheets/scd30/).
"""

import asyncio
import math
from collections import namedtuple
from struct import unpack, unpack_from

from machine import Pin, Timer
from micropython import const

import math_helpers
from asy_base_classes import DeviceSession, SensorReaderConfig, utc_now
from asy_config_manager import compare_before_write, make_dict, name_cfg, schema_names, type_or_range_error
from asy_crc_checks import CRC8
from asy_i2c_driver import I2C, I2CDevice
from asy_print_log import DEFAULT_LOG, LogConfig

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_base_classes import JsonMapping, TaskStarter, TimerStarter
    from asy_config_manager import CfgValue, ConfigSchema, FieldSchema, WriteValidity
    from asy_print_log import ErrorLog


_SCD30_ADDR = const(0x61)  # Interface Description 1.1.1: the address is fixed
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

# Same datasheet limits the _VAL_* schema entries below carry, named for the driver's own argument
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
# Measurement ranges, SCD30 Datasheet Tables 1-3: the plausibility gate on a decoded reading (no CRC can catch a
# wrong-but-valid word) (the RH/T element reads to 120 °C, footnote 9; above 70 °C the part may be damaged).
_CO2_MIN_PPM = const(0.0)
_CO2_MAX_PPM = const(40000.0)
_TEMP_MIN_C = const(-40.0)
_TEMP_MAX_C = const(70.0)
_HUM_MIN_PCT = const(0.0)
_HUM_MAX_PCT = const(100.0)
# Waits between a command and its result, after a soft reset, and the start-trigger timer's period.
# @tunable scd30.cmd_response_wait_s = 0.05
_CMD_RESPONSE_WAIT_S = const(0.05)
# @tunable scd30.asc_enable_wait_s = 0.01
_ASC_ENABLE_WAIT_S = const(0.01)
# @tunable scd30.soft_reset_wait_s = 2.5
_SOFT_RESET_WAIT_S = const(2.5)
# @tunable scd30.start_trigger_period_ms = 500
_START_TRIGGER_PERIOD_MS = const(500)

# Codes from the global catalog (buildgen/error_catalog.json; SPECIFICATION.md Part C.7.1).
_ERR_INIT = const(10)
_ERR_READ = const(11)
_ERR_CHIP_GET = const(12)
_ERR_CHIP_SET = const(13)
_ERR_BAD_ARG = const(21)
_ERR_READ_RANGE = const(27)
_WRN_SCD_NOT_READY = const(73)
# @tunable scd30.not_ready_warn_at = 5
_NOT_READY_WARN_AT = const(5)  # consecutive not-ready reads, as ISL29125's _PERIODIC_ONLY_WARN_AT

# Forced-recalibration readiness: the published codes, then the criteria (Low Power Mode note: 6 minutes or 5
# intervals before an FRC; Datasheet Table 1: a CO2 temperature stability of 2.5 ppm/°C).
_FRC_NOT_MEASURING = const(0)
_FRC_SETTLING = const(1)
_FRC_DRIFTING = const(2)
_FRC_NOISY = const(3)
_FRC_READY = const(4)
_FRC_SETTLE_S = const(360)
_FRC_MIN_INTERVALS = const(5)
_FRC_TEMP_PPM_PER_C = const(2.5)
_FRC_MIN_WINDOW = const(3)  # a residual about a fitted line needs three samples
_FRC_MAX_WINDOW = const(1800)  # FRCWindow's 3600 s at the 2 s minimum interval

# No _VAL_* entry for "ContMeas": the SCD30 cannot report whether continuous measurement is
# running, so the freestanding @web tag below stands in for one and the value is validated
# through the synthetic FieldSchema _CONT_MEAS_FIELD, as PauseTime is.
_CONT_MEAS_FIELD: "FieldSchema" = ("ContMeas", "bool", None, None, None, None)
# The order a PUT's chip writes are applied in, whatever the body's key order.
_APPLY_ORDER = const(("TempOffset", "MeasInterval", "AmbPres", "Altitude", "ForceCalRef", "SelfCal"))

_VAL_TEMP_OFFSET = const((("TempOffset", "float", None, 0.0, 655.35, None),))
_VAL_MEAS_INTERVAL = const((("MeasInterval", "int", None, 2, 1800, None),))
_VAL_AMB_PRES = const((("AmbPres", "int", None, 700, 1400, 0),))
_VAL_ALTITUDE = const((("Altitude", "int", None, 0, 65535, None),))
_VAL_FORCE_CAL_REF = const((("ForceCalRef", "int", None, 400, 2000, None),))
_VAL_SELF_CAL = const((("SelfCal", "bool", None, None, None, None),))
# FRC readiness settings: noise floor 2 x the repeatability (owner, 2026-09-29: 1-2 x); rate and window
# provisional until measured on the bench (agent, 2026-09-29; owner-reviewed, 2026-10-02).
_VAL_FRC_NOISE = const((("FRCNoise", "float", 20.0, 1.0, 500.0, None),))
_VAL_FRC_RATE = const((("FRCRate", "float", 10.0, 0.1, 1000.0, None),))
_VAL_FRC_WINDOW = const((("FRCWindow", "int", 60, 20, 3600, None),))

# @web-group section=sensors submitGroup=self label="SCD30 — CO2, Temperature, Humidity" submit=true
# @web TempOffset section=sensors submitGroup=self label="Temperature Offset" unit="K"
# @web MeasInterval section=sensors submitGroup=self label="Measurement Interval" unit="s"
# @web AmbPres section=sensors submitGroup=self label="Ambient Pressure (starts continuous measurement)" unit="hPa" special:0="Compensation off / use Altitude" alwaysExecuted=true
# @web Altitude section=sensors submitGroup=self label="Altitude above sea level" unit="m" description="Only used while Ambient Pressure is 0; a pressure value overrides it."
# Interface Description 1.4.6 and its FRC section (p14), Low Power Mode note (6 min / 5 intervals), Field Calibration note (the configured interval).
# @web ForceCalRef section=sensors submitGroup=self label="Forced Calibration Reference" unit="ppm" description="A calibration run, carried out on every Apply. Only valid after continuous measurement at the configured interval for 6 minutes or 5 intervals, whichever is longer, in stable air of known CO2 (400-2000 ppm). FRC Readiness shows when that holds." alwaysExecuted=true
# @web SelfCal section=sensors submitGroup=self label="Automatic Self-Calibration" description="Needs 7 days of uninterrupted power with at least 1 hour of fresh air every day; a power loss in the first 7 days restarts the search."
# @web FRCNoise section=sensors submitGroup=self label="FRC Noise Floor" unit="ppm"
# @web FRCRate section=sensors submitGroup=self label="FRC Change-Rate Limit" unit="ppm/min"
# @web FRCWindow section=sensors submitGroup=self label="FRC Stability Window" unit="s"
# @web ContMeas section=sensors submitGroup=self kind=toggle label="Continuous Measurement" onLabel="On" offLabel="Off" description="Setting this to Off stops continuous measurement; restart it via Ambient Pressure above." defaultValue=true alwaysExecuted=true

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


def _temp_offset_ticks(offset: float) -> int:
    # Nearest 0.01 degC tick, not truncation: in float32 130 of the 2001 two-decimal inputs land one tick low when truncated (0.00-20.00; offset is validated >= 0 first).
    return int(offset * 100 + 0.5)


_NAME = const("SCD30")
# Kept as a literal tuple inline (not `_FIELDS` below) because mypy's namedtuple plugin can only
# infer field names from a literal at the call site, not through a variable indirection.
SCD30 = namedtuple("SCD30", ("CO2", "Temp", "Hum", "WetBulb", "DewPoint", "FRCState", "FRCWait", "TS"))
_FIELDS = const(("CO2", "Temp", "Hum", "WetBulb", "DewPoint", "FRCState", "FRCWait", "TS"))  # kept in sync with SCD30's own fields above

# @web-group section=measurements submitGroup=self label="SCD30 — CO2, Temperature, Humidity"
# @web CO2 section=measurements submitGroup=self kind=readonly label="CO2" unit="ppm"
# @web Temp section=measurements submitGroup=self kind=readonly label="Temperature" unit="°C"
# @web Hum section=measurements submitGroup=self kind=readonly label="Relative Humidity" unit="%"
# @web WetBulb section=measurements submitGroup=self kind=readonly label="Wet Bulb Temperature" unit="°C"
# @web DewPoint section=measurements submitGroup=self kind=readonly label="Dew Point" unit="°C"
# @web FRCState section=measurements submitGroup=self kind=readonly label="FRC Readiness" description="0 not measuring, 1 settling, 2 CO2 drifting, 3 CO2 noisy, 4 ready for a forced recalibration." codes=FRCState
# @web FRCWait section=measurements submitGroup=self kind=readonly label="FRC Settling Left" unit="s" decimals=0
# @web TS section=measurements submitGroup=self kind=readonly label="Timestamp" format=epoch

# Datasheets/scd30/..._Interface_Description.pdf p.2: clock stretching is normally <=30ms but
# reaches 150ms once a day for internal calibration, past rp2's own 50ms I2C default. Enforced as a
# generator-checked build requirement (Part L.5), not a comment each TOML author must remember.
# @requires bus.timeout>=200000
# Datasheet hard maximum, same source (Interface Description p.2): "Maximal I2C speed is
# 100 kHz" - Sensirion recommends 50 kHz or less, which every device TOML uses today.
# @requires bus.frequency<=100000
# @wiring fram_target FRAMManager log optional kwarg
# Stuck-pin fallback reads after 2 * trigger_s ticks of 500 ms: at least one full second, at
# most the chip's longest measurement interval (agent, 2026-09-29).
# @limits trigger_s 1..1800

if TYPE_CHECKING:
    SCDResults = tuple[float | None, float | None, float | None, int | None]  # CO2, temperature, humidity, timestamp


class SCD30_Reader(SensorReaderConfig):
    # CFGMGR_SCD30 stays RAM-only: no extra FRAM chunk for the FRC settings (owner, 2026-09-29).
    _CFG_LOG_FRAM = False

    def __init__(
        self,
        i2c: I2C,
        irq_pin: int,
        trigger_s: int = 3,
        # @tunable module.max_error = 5
        max_module_error: int = 5,
        name_ext: str = "",
        cfg_path: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        super().__init__(
            SCD30(None, None, None, None, None, None, None, None),
            _NAME,
            _VAL_FRC_NOISE + _VAL_FRC_RATE + _VAL_FRC_WINDOW,
            max_module_error=max_module_error,
            name_ext=name_ext,
            cfg_path=cfg_path,
            log=log,
        )
        self._scd = SCD30_I2C(i2c)
        self._recovery_bus = i2c
        self._irq_pin = Pin(irq_pin, mode=Pin.IN)
        self._base_trigger_event = asyncio.ThreadSafeFlag()
        self._start_trigger_timer = Timer()
        self._trigger_half_ticks = 2 * int(trigger_s)
        self._read_event = asyncio.ThreadSafeFlag()
        self._scd_timer_triggers = 0
        self._not_ready_reads = 0
        # FRC readiness, RAM only: the interval _init_scd() reads, the settings each cycle captures, the
        # uninterrupted count, the 500 ms ticks since the last measurement, and one regression window.
        self._frc_interval_s = _MEAS_INTERVAL_MIN
        self._frc_noise: float = _VAL_FRC_NOISE[0][2]
        self._frc_rate: float = _VAL_FRC_RATE[0][2]
        self._frc_window_s: int = _VAL_FRC_WINDOW[0][2]
        self._frc_cfg_ok = True
        self._frc_measuring = False
        self._frc_count = 0
        self._frc_idle_ticks = 0
        self._frc_verdict = 0  # the last closed window's code since the count reached its target; 0 none yet
        self._frc_n = 0
        self._frc_co2_first = 0.0
        self._frc_sum_d = 0.0
        self._frc_sum_d2 = 0.0
        self._frc_sum_id = 0.0
        self._frc_t_first = 0.0
        self._frc_t_last = 0.0

    async def _get_mgr_cfg(self, cfg: list[str]) -> "dict[str, CfgValue] | None":
        # A composite store (SPECIFICATION.md C.4.3): the six chip keys from one chip snapshot, the three
        # FRC keys from the config file; a failed snapshot leaves the chip keys out (None in the GET).
        values: dict[str, CfgValue] = {}
        if any(key in _APPLY_ORDER for key in cfg):
            current = await self._config_snapshot()
            if current is not None:
                values.update({key: current[key] for key in cfg if key in current})
        frc = [key for key in cfg if key not in _APPLY_ORDER]
        if frc:
            stored = await super()._get_mgr_cfg(frc)
            if stored is not None:
                values.update(stored)
        return values

    async def _set_mgr_cfg(self, data: "JsonMapping", cfg_vals: "ConfigSchema") -> "tuple[bool, WriteValidity]":
        # Compare-before-write against a fresh chip snapshot, writes in _APPLY_ORDER, ContMeas last. "a PUT whose
        # get_config_snapshot() fails is refused as a whole, nothing written, the response reports the failure,
        # as legacy" (owner, 2026-09-29); the FRC keys go to the config file, and fall with the body too.
        frc_names = schema_names(_VAL_FRC_NOISE + _VAL_FRC_RATE + _VAL_FRC_WINDOW)
        frc = {key: value for key, value in data.items() if key in frc_names}
        rest = {key: value for key, value in data.items() if key not in frc}
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
            if key not in write:
                continue
            if not await setter(write[key]):  # type: ignore[arg-type]
                results[key] = "Failed"
            elif key == "MeasInterval":  # a new interval: readiness starts over at it
                self._frc_interval_s = write[key]  # type: ignore[assignment]
                self._frc_reset()
            elif key == "AmbPres":  # 0x0010 (re)starts continuous measurement
                self._frc_reset()
                self._frc_measuring = True
        if has_cont_meas:
            # ContMeas is a command, not a stored value: True keeps the chip running (nothing to send),
            # False stops it - after the writes, so an AmbPres in the same body cannot restart it.
            is_error, flag = type_or_range_error(cont_meas, _CONT_MEAS_FIELD)
            if is_error:
                results["ContMeas"] = "Invalid"
                await self.pr.err_s("Invalid value for ContMeas", errno=_ERR_BAD_ARG)
            elif flag:
                results["ContMeas"] = "Valid"
            elif await self.stop_continuous_measurement(value=False):
                results["ContMeas"] = "Valid"
                self._frc_reset()
                await self._frc_not_measuring()
            else:
                results["ContMeas"] = "Failed"
        if frc:
            persisted, frc_results = await super()._set_mgr_cfg(frc, _VAL_FRC_NOISE + _VAL_FRC_RATE + _VAL_FRC_WINDOW)
            results.update(frc_results if persisted else dict.fromkeys(frc, "Failed"))
        return True, results

    async def _capture_frc_config(self) -> None:
        # The cycle's FRC settings, read before its measurement (the capture rule, C.4.2); a failed read
        # keeps the last values and publishes the cycle as settling.
        floats = await self.cfgmgr.get_float_values(_VAL_FRC_NOISE + _VAL_FRC_RATE)
        ints = await self.cfgmgr.get_int_values(_VAL_FRC_WINDOW)
        self._frc_cfg_ok = floats is not None and ints is not None
        if floats is not None and ints is not None:
            self._frc_noise, self._frc_rate = floats
            self._frc_window_s = ints[0]

    async def _config_snapshot(self) -> "dict[str, CfgValue] | None":
        # One batched read (get_config_snapshot()), not six separately-locked get_*() calls, so a
        # concurrent write never mixes pre- and post-write values; a failure logs CHIP_GET and is None.
        try:
            snap = await self._scd.get_config_snapshot()
        except Exception as e:
            await self.pr.err_s("Error reading the config snapshot:", e, errno=_ERR_CHIP_GET)
            return None
        return _snapshot_dict(snap)

    def _frc_add(self, co2: float, temperature: float) -> None:
        # Deviations from the window's first sample keep the float32 sums small; the sample index is n.
        if self._frc_n == 0:
            self._frc_co2_first = co2
            self._frc_t_first = temperature
        d = co2 - self._frc_co2_first
        self._frc_sum_d += d
        self._frc_sum_d2 += d * d
        self._frc_sum_id += self._frc_n * d
        self._frc_t_last = temperature
        if self._frc_n < _FRC_MAX_WINDOW:
            self._frc_n += 1

    def _frc_clear_window(self) -> None:
        self._frc_n = 0
        self._frc_sum_d = 0.0
        self._frc_sum_d2 = 0.0
        self._frc_sum_id = 0.0

    def _frc_close(self, interval: int) -> int:
        # Least squares over the window's sample index: the slope as a rate, the residual about the line as the
        # noise; Sum(i) and Sum(i^2) in closed form, so no stored value grows with the window.
        n = float(self._frc_n)
        s_i = n * (n - 1) / 2
        s_ii = (n - 1) * n * (2 * n - 1) / 6
        sxx = s_ii - s_i * s_i / n
        sxy = self._frc_sum_id - s_i * self._frc_sum_d / n
        syy = self._frc_sum_d2 - self._frc_sum_d * self._frc_sum_d / n
        rate = abs(sxy / sxx) * 60 / interval  # ppm/min
        noise = math.sqrt(max(0.0, syy - sxy * sxy / sxx) / (n - 2))
        self._frc_clear_window()
        if rate > self._frc_rate or abs(self._frc_t_last - self._frc_t_first) * _FRC_TEMP_PPM_PER_C > self._frc_noise:
            return _FRC_DRIFTING
        if noise > self._frc_noise:
            return _FRC_NOISY
        return _FRC_READY

    async def _frc_not_measuring(self) -> None:
        # The last sample again with state 0 and its own TS, in one data-lock hold (no await inside).
        self._frc_measuring = False
        await self._republish(_FIELDS, FRCState=_FRC_NOT_MEASURING, FRCWait=None)

    def _frc_reset(self) -> None:
        # Readiness starts over: a soft reset, an interval change, a measurement start, a stop or a missed measurement.
        self._frc_idle_ticks = 0
        self._frc_restart()

    def _frc_restart(self) -> None:
        # The uninterrupted count and the window start over; the ticks since the last measurement keep counting.
        self._frc_count = 0
        self._frc_verdict = 0
        self._frc_clear_window()

    def _frc_step(self, co2: float, temperature: float) -> tuple[int, int | None]:
        # One new measurement into the readiness state: the uninterrupted count, the window, the verdict.
        interval = self._frc_interval_s
        if self._frc_idle_ticks > 3 * interval:  # more than 1.5 intervals since the last one: a missed measurement
            self._frc_reset()
        self._frc_idle_ticks = 0
        self._frc_measuring = True
        target = max(math.ceil(_FRC_SETTLE_S / interval), _FRC_MIN_INTERVALS)
        if self._frc_count < target:
            self._frc_count += 1
        size = max(math.ceil(self._frc_window_s / interval), _FRC_MIN_WINDOW)  # never over _FRC_MAX_WINDOW
        self._frc_add(co2, temperature)
        if self._frc_n >= size:
            verdict = self._frc_close(interval)
            if self._frc_count >= target:
                self._frc_verdict = verdict
        if self._frc_count < target or self._frc_verdict == 0 or not self._frc_cfg_ok:
            left = target - self._frc_count  # samples to the uninterrupted target
            to_close = size - self._frc_n  # samples to this window's close
            if to_close < left:
                to_close += math.ceil((left - to_close) / size) * size
            return _FRC_SETTLING, to_close * interval
        return self._frc_verdict, None

    async def _init_scd(self) -> bool:
        # Continuous measurement is never started here: the first ambient-pressure PUT starts it, and
        # the chip keeps it across power cycles (SPECIFICATION.md A.4; owner, 2026-09-26).
        self._err_cnt_internal = 0
        self._not_ready_reads = 0
        try:
            await self._scd.setup()
            interval = await self._scd.get_measurement_interval()
        except Exception as e:
            await self.pr.err_s("Error in initial setup:", e, errno=_ERR_INIT)
            await self._init_failed()
            return False
        # The chip's word, held to the datasheet range so the readiness arithmetic never divides by zero.
        self._frc_interval_s = min(max(interval, _MEAS_INTERVAL_MIN), _MEAS_INTERVAL_MAX)
        self._frc_reset()  # the soft reset restarted the measurement
        await self._init_done()
        self.pr.one("initialized")
        return True

    # Trigger the CO2 sensor IRQ if it isn't running (pin stays HIGH if not read!); the same 500 ms tick
    # counts the time since the last measurement for the FRC readiness.
    async def _irq_loop(self) -> None:
        if self._timer_error is not None:  # a restart after a failed arm re-arms first
            self._timer_error = None
            self.start_timer()
        while True:
            await self._base_trigger_event.wait()
            if await self._timer_fault():
                return
            if self._irq_pin.value() == 1 and self._scd_timer_triggers < self._trigger_half_ticks:
                self._scd_timer_triggers += 1  # ticks with the pin high since the last read, not necessarily consecutive; capped at the threshold
            idle_limit = 4 * self._frc_interval_s  # two intervals without a measurement: not measuring
            if self._frc_idle_ticks < idle_limit + 2:
                self._frc_idle_ticks += 1
                if self._frc_idle_ticks == idle_limit:
                    self._frc_restart()
                    await self._frc_not_measuring()

            if self._scd_timer_triggers >= self._trigger_half_ticks:
                self.pr.evt("Interrupt Start Trigger")
                self._read_event.set()

    async def _read_loop(self) -> None:
        if not await self._init_scd():
            return
        while True:
            await self._read_event.wait()
            self.pr.evt("sensor trigger")
            self._scd_timer_triggers = 0
            results, new_data = await self._read_scd()
            # A failed read clears every measured value; TS alone is None until the first NTP sync, which is no failure.
            if not await self._error_check(results, condition=results[0] is None):
                return
            await self._store_scd(results, new_data)

    async def _read_scd(self) -> "tuple[SCDResults, bool]":
        timestamp = utc_now()  # None until the NTP client has set the clock this boot
        await self._capture_frc_config()
        try:
            # read_measurement() must run exactly once per cycle, before the getters below.
            new_data = await self._scd.read_measurement()
            co2 = await self._scd.get_CO2()
            temperature = await self._scd.get_temperature()
            humidity = await self._scd.get_relative_humidity()
            self.pr.all("read")
        except ValueError as e:
            # The range gate's rejected value, kept apart from a bus fault in the log; it still counts as a failed read.
            co2 = temperature = humidity = None
            new_data = False
            await self.pr.err_s("Reading rejected:", e, errno=_ERR_READ_RANGE)
        except Exception as e:
            co2 = temperature = humidity = None
            new_data = False
            await self.pr.err_s("Read failed:", e, errno=_ERR_READ)
        else:
            if new_data:
                self._not_ready_reads = 0
            elif self._not_ready_reads < _NOT_READY_WARN_AT:
                self._not_ready_reads += 1
                if self._not_ready_reads == _NOT_READY_WARN_AT:  # one warning per episode, cleared by new data
                    await self.pr.wrn_s("Data ready signalled but no new measurement - RDY line stuck?", wrnno=_WRN_SCD_NOT_READY)
        return (co2, temperature, humidity, timestamp), new_data

    async def _recover_device(self) -> bool:
        # The participant rung: a soft reset under the setter lock, so a PUT runs wholly before or after the
        # chip's restart; the chip reloads its NVM settings itself, so nothing is written (Interface Description 1.4.10).
        async with self._set_lock:
            try:
                await self._scd.reset()
            except Exception as e:
                await self.pr.err_s("Soft reset failed:", e, errno=_ERR_CHIP_SET)
                return False
        self._frc_reset()  # the soft reset restarted the measurement, as at _init_scd()
        return True

    async def _store_scd(self, results: "SCDResults", new_data: bool) -> None:
        if results[0] is None or results[1] is None or results[2] is None:
            return  # the timestamp may be None before the first sync
        co2, temperature, humidity = results[0], results[1], results[2]
        state: object = None
        wait: object = None
        if new_data:
            state, wait = self._frc_step(co2, temperature)
        wet_bulb = math_helpers.wet_bulb_temperature(temperature, humidity)
        dew_point = math_helpers.dew_point(temperature, humidity)
        async with self._data_lock:  # one hold: a not-ready cycle keeps the state the sample already carries
            if not new_data:
                state = getattr(self._datastruct, "FRCState", None)
                wait = getattr(self._datastruct, "FRCWait", None)
            self._datastruct = SCD30(co2, temperature, humidity, wet_bulb, dew_point, state, wait, results[3])
        self.pr.all("data stored")

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_read, self.start_asy_irq]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return [self.start_timer]

    def start_asy_irq(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._irq_loop())

    def start_asy_read(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._read_loop())

    def start_timer(self) -> None:
        try:
            self._start_trigger_timer.init(
                period=_START_TRIGGER_PERIOD_MS,
                mode=Timer.PERIODIC,
                callback=lambda _b: self._base_trigger_event.set(),
            )
        except (MemoryError, OSError) as e:
            # Alarm pool exhausted (ENOMEM) or no memory: wake the waiting task, which logs it and ends; its restart re-arms.
            self._timer_failed(e, self._base_trigger_event)
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
        # The nine keys a PUT may carry: six stored on the chip, three in the config file.
        return _VAL_TEMP_OFFSET + _VAL_MEAS_INTERVAL + _VAL_AMB_PRES + _VAL_ALTITUDE + _VAL_FORCE_CAL_REF + _VAL_SELF_CAL + _VAL_FRC_NOISE + _VAL_FRC_RATE + _VAL_FRC_WINDOW

    async def get_data(self) -> SCD30:
        # Narrows to this Reader's concrete SCD30 - see SPECIFICATION.md C.4.2's get_data() convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        return await self._get_dict_cfg(self.name, self.get_cfg_schema())

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


class SCD30_I2C:
    def __init__(self, i2c_bus: I2C) -> None:
        self._i2c_scd30 = DeviceSession(I2CDevice(i2c_bus, _SCD30_ADDR))  # its lock also guards self._buffer
        self._buffer = bytearray(18)
        self.crc = CRC8()

        # cached readings
        self._temperature: float | None = None
        self._relative_humidity: float | None = None
        self._co2: float | None = None
        self._temp_offset_ticks = 0  # the chip's offset word, read at setup() and kept by set_temperature_offset()

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
        value: int = unpack_from(">H", self._buffer)[0]
        return value

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
        # 0x0010 starts continuous measurement, whose on/off status the chip keeps in NVM (Interface Description
        # 1.4.1); whether the pressure value itself persists is undocumented. Validated before truncating -
        # int(-0.5) == 0 would otherwise slip through as the "disable" value; NaN is rejected explicitly too.
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
        ticks = _temp_offset_ticks(offset)
        await self._send_command(_CMD_SET_TEMPERATURE_OFFSET, ticks)
        self._temp_offset_ticks = ticks  # what the range gate adds back, once the chip took it

    async def read_measurement(self) -> bool:
        # Call exactly once per cycle (data-ready clears the instant it's read - Interface
        # Description 1.4.4); a second call would wipe fresh data back to None. If not ready,
        # leaves the cache untouched, matching the legacy driver, and answers False.
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
                return False

            crcs_good = True
            for i in range(0, 18, 3):
                if await self.crc.check_from(self._buffer, 3, start=i) == _WORD_BYTES:
                    continue
                crcs_good = False
            if not crcs_good:
                raise RuntimeError("CRC check failed while reading data")

            co2: float = unpack(">f", self._buffer[0:2] + self._buffer[3:5])[0]
            temperature: float = unpack(">f", self._buffer[6:8] + self._buffer[9:11])[0]
            humidity: float = unpack(">f", self._buffer[12:14] + self._buffer[15:17])[0]
            # The words are raw IEEE-754 and CRC-valid NaN/inf still decode; MicroPython's json.dumps()
            # would ship them as bare nan/inf, breaking the whole page (Part F.1). A failed read instead,
            # and a finite value outside the datasheet ranges is rejected the same way.
            if not (math.isfinite(co2) and math.isfinite(temperature) and math.isfinite(humidity)):
                raise ValueError(f"non-finite measurement (co2={co2}, t={temperature}, rh={humidity})")
            # The temperature half gates the sensor's own reading, before the on-chip offset (Interface Description 1.4.7).
            sensed = temperature + self._temp_offset_ticks / 100
            if not (_CO2_MIN_PPM <= co2 <= _CO2_MAX_PPM and _TEMP_MIN_C <= sensed <= _TEMP_MAX_C and _HUM_MIN_PCT <= humidity <= _HUM_MAX_PCT):
                raise ValueError(f"reading outside measurement range (co2={co2}, t={temperature}, rh={humidity})")
            self._co2 = co2
            self._temperature = temperature
            self._relative_humidity = humidity
            return True

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
        self._temp_offset_ticks = await self._read_register(_CMD_SET_TEMPERATURE_OFFSET)
        return True

    async def stop_continuous_measurement(self) -> None:
        # Turn off continuous measurement (turn on with ambient pressure command)
        await self._send_command(_CMD_STOP_CONTINUOUS_MEASUREMENT)
