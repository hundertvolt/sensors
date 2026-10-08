# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya (original MicroPython_ISL29125) -
# restructured/rewritten for asyncio + this project's driver shape, see THIRD_PARTY_LICENSES.md.
# SPDX-License-Identifier: MIT

"""Renesas/Intersil ISL29125 RGB colour sensor driver: lux, sensor RGB/HSB, relative CCT, and an auto-range state machine driven by the chip's own threshold interrupt.
ISL29125_I2C is the protocol layer; ISL29125_Reader is the asyncio task/config layer (see SPECIFICATION.md Part C).
Verified against FN8424 Rev 3.00 (datasheets/isl29125/REN_isl29125_DST_20151201_1.pdf).
"""

import asyncio
import struct
import time
from collections import namedtuple

from machine import Pin, Timer
from micropython import const

import math_helpers
from asy_base_classes import COUNTER_CAP, DeviceSession, LockedValue, SensorReaderConfig, utc_now
from asy_config_manager import checked_numeric, name_cfg
from asy_i2c_driver import I2CDevice
from asy_print_log import DEFAULT_LOG, LogConfig

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_base_classes import JsonDict, TaskStarter, TimerStarter
    from asy_config_manager import CfgValue, ConfigSchema
    from asy_i2c_driver import I2C
    from asy_print_log import ErrorLog


# Codes from the global catalog (buildgen/error_catalog.json; SPECIFICATION.md Part C.7.1).
_ERR_INIT = const(10)
_ERR_READ = const(11)
_ERR_CHIP_GET = const(12)
_ERR_CHIP_SET = const(13)
_ERR_BAD_ARG = const(21)
_ERR_CFG_READ = const(26)
_ERR_ISL_STATUS_READ = const(55)
_ERR_ISL_BUS_FAULT = const(56)
_WRN_ISL_BROWNOUT = const(30)
_WRN_ISL_DIVERGED = const(31)
_WRN_ISL_PERIODIC_ONLY = const(32)
_WRN_ISL_CAL_TIMEOUT = const(75)

_ISL29125_ADDR = const(0x44)  # hard-wired "1000100" (FN8424 p15): a second part needs another bus
_DEVICE_ID = const(0x7D)  # datasheet p9, Table 2
_CMD_RESET = const(0x46)  # written to 0x00: "the device will reset all registers to their default states" (p9)

_REGISTER_DEVICE_ID = const(0x00)
_REGISTER_CONFIG1 = const(0x01)
_REGISTER_CONFIG2 = const(0x02)
_REGISTER_THRESHOLDS = const(0x04)  # 0x04-0x07, low pair then high pair (p12, Table 14)
_REGISTER_STATUS = const(0x08)
_REGISTER_DATA = const(0x09)  # 0x09-0x0E, GREEN then RED then BLUE (p9, Table 1)

_MODE_RGB = const(0x05)  # p10, Table 4 - the only mode that yields all three channels
_CONFIG1_MODE_MASK = const(0x07)
_CONFIG1_RNG = const(0x08)  # p10, Table 5: 0 = 375 lux, 1 = 10000 lux
_CONFIG1_BITS = const(0x10)  # p10, Table 6: 0 = 16-bit, 1 = 12-bit
_CONFIG1_SYNC = const(0x20)  # p10, Table 7 - kept 0: a 1 turns INT into an INPUT and inverts the whole path
_CONFIG2_IRCOMP_OFFSET = const(0x80)  # p10: B7 adds 106 codes on top of B[5:0]
_CONFIG2_ALSCC_MASK = const(0x3F)
_CONFIG3_INTSEL_MASK = const(0x03)  # p11, Table 11
_CONFIG3_PRST_SHIFT = const(2)  # p11, Table 12
_CONFIG3_CONVEN = const(0x10)  # p11, Table 13 - kept 0, see SPECIFICATION.md Part C
_INTSEL_NONE = const(0x00)
_INTSEL_GREEN = const(0x01)

# Reserved bits, which p9 says "can change without any notice" - masked out of every shadow-vs-chip
# comparison so a divergence report is never triggered by a bit nobody owns.
_CONFIG1_MASK = const(0x3F)  # B7:B6 reserved
_CONFIG2_MASK = const(0xBF)  # B6 reserved
_CONFIG3_MASK = const(0x1F)  # B7:B5 reserved

_STATUS_RGBTHF = const(0x01)  # p12, Table 16
_STATUS_CONVENF = const(0x02)  # p12, Table 17 - decoded for logging only
_STATUS_BOUTF = const(0x04)  # p12, Table 18
_STATUS_RGBCF_SHIFT = const(4)  # p12, Table 19 - decoded for logging only
_STATUS_RESERVED_MASK = const(0xC8)  # B7:B6 and B3 read zero on a working part (p12, Table 15)

_DATA_BURST_LEN = const(6)
_CONFIG_BURST_LEN = const(3)

_RANGE_LOW_LUX = const(375)  # p10, Table 5
_RANGE_HIGH_LUX = const(10000)
_RANGES = const((375, 10000))
_RESOLUTION_12BIT = const(12)
_RESOLUTION_16BIT = const(16)
_RESOLUTIONS = const((12, 16))
_CHANNELS = const(3)  # green, red, blue - the width of every triple in this module
_IR_OFFSETS = const((0, 1))
_PRST_SETTINGS = const((1, 2, 4, 8))  # p11, Table 12 - index is the register encoding
_FULL_SCALE_COUNTS = const(65535)  # p3: "Full Scale ADC Code, ADC 16 bits"
_CYCLE_MS_16BIT = const(303)  # 3 x tINT, tINT = 101ms typ at 16 bits (p3)
_CYCLE_MS_12BIT = const(19)  # 3 x ~6.3ms: p6 makes tINT an n-bit counter on one oscillator, 101 x 2**-4

# Device/maths constants, not config fields (agent, 2026-09-14) - requirement 1 (SPECIFICATION.md
# Part M.1.1) governs preferences, and none of these is one.
_DARK_COUNTS = const(1)  # DDark typ 1 / max 5 counts at range 0 (p3, Electrical Specifications)
# @tunable isl29125.cct_floor_counts = 64
_CCT_FLOOR_COUNTS = const(64)  # ~13x the worst-case dark count: below it a 5-count additive error
# moves a channel ratio by more than ~8%, and chromaticity noise grows far faster than hue noise.
_GAIN_RATIO_NOMINAL = const(26.666666666666668)  # 10000/375 - the ratio a fresh unit starts from
# @tunable isl29125.gain_ratio_min = 20.0
_GAIN_RATIO_MIN = const(20.0)  # a plausibility gate around nominal, applied where an untrusted
# @tunable isl29125.gain_ratio_max = 34.0
_GAIN_RATIO_MAX = const(34.0)  # value enters (on load and on learn), never in the hot path
# Calibration is a bounded, user-started run, never a background schedule (owner, 2026-09-13): the driver only ever
# READS GainRatio, so nothing it does can write the flash (SPECIFICATION.md Part M.1.5).
# @tunable isl29125.cal_window_ms = 120000
_CAL_WINDOW_MS = const(120000)  # hard stop on a run that never converges - ~100 attempts at 16 bit
# @tunable isl29125.cal_hold_ms = 600000
_CAL_HOLD_MS = const(600000)  # how long a finished run's candidate stays readable before it clears
# @tunable isl29125.cal_converge_n = 3
_CAL_CONVERGE_N = const(3)  # consecutive stable ratios that must agree before the run stops early
# @tunable isl29125.cal_converge_tol = 0.01
_CAL_CONVERGE_TOL = const(0.01)  # 1%: one bench scene measured 28.11/28.01/28.09, a 0.4% spread
# @tunable isl29125.cal_stability_tol = 0.02
_CAL_STABILITY_TOL = const(0.02)  # 2% between the sandwich's first and third reading of one range
_AR_DOWN_DIVISOR = const(53.333333333333336)  # 2 x the NOMINAL range ratio - see _down_thresh()
# @tunable isl29125.settle_cycles = 2
_SETTLE_CYCLES = const(2)  # conversions discarded after a CONFIG1 write, fixed - see configure()
# @tunable isl29125.settle_wait_max_rounds = 2
_SETTLE_WAIT_MAX_ROUNDS = const(2)  # one extra cycle past the deadline, so a stream of concurrent
# config writes can extend the settle but can never starve the read loop indefinitely.
# @tunable isl29125.periodic_only_warn_at = 5
_PERIODIC_ONLY_WARN_AT = const(5)  # consecutive periodic-path switches with no preceding interrupt

_MIN_TRIGGER_S = const(1)
_MAX_TRIGGER_S = const(3600)
_MIN_DWELL_S = const(0.0)
_MAX_DWELL_S = const(300.0)
_MAX_DWELL_MS = const(300000)  # _MAX_DWELL_S in ms, the stored-tick bound of _evaluate_range()
_MIN_FILT_COEFF = const(-1.0)
_MAX_FILT_COEFF = const(1.0)
_MIN_AR_THRESH = const(50.0)
_MAX_AR_THRESH = const(95.0)

_VAL_SAMPLE_INTERVAL = const((("SampleInterval", "int", 1, _MIN_TRIGGER_S, _MAX_TRIGGER_S, None),))
# Resolution/Range/IRCompOffset are genuine discrete allowed-value sets, not
# continuous ranges - the 6th-slot `special` shape asy_bmp3xx_driver.py's own _VAL_PRES_OVERS established.
_VAL_RESOLUTION = const((("Resolution", "int", 16, None, None, _RESOLUTIONS),))
_VAL_RANGE_AUTO = const((("RangeAuto", "bool", True, None, None, None),))
_VAL_RANGE = const((("Range", "int", 10000, None, None, _RANGES),))
# The single switch-up point, as a percentage of full scale. The down point is DERIVED from it
# (_down_thresh()) rather than configured: there is one correct hysteresis gap for a given
# threshold, and a second field could only ever be used to get it wrong.
_VAL_AUTO_RANGE_THRESH = const((("AutoRangeThresh", "float", 85.0, _MIN_AR_THRESH, _MAX_AR_THRESH, None),))
_VAL_AUTO_RANGE_DWELL = const((("AutoRangeDwell", "float", 10.0, _MIN_DWELL_S, _MAX_DWELL_S, None),))
_VAL_IR_COMP_OFFSET = const((("IRCompOffset", "int", 0, None, None, _IR_OFFSETS),))
_VAL_IR_COMP_ADJUST = const((("IRCompAdjust", "int", 40, 0, 63, None),))
_VAL_FILT_COEFF = const((("FiltCoeff", "float", -1.0, _MIN_FILT_COEFF, _MAX_FILT_COEFF, None),))
# The applied scale factor, and the only thing _gain_correction() reads. A user PUT is its only
# writer - the driver never writes its own config, which keeps every flash write on the REST path.
# A measured candidate is published as GainMeas for the user to copy across, never adopted.
_VAL_GAIN_RATIO = const((("GainRatio", "float", _GAIN_RATIO_NOMINAL, _GAIN_RATIO_MIN, _GAIN_RATIO_MAX, None),))
# Command-only trigger, the schema's "special-alone" shape (SPECIFICATION.md Part C.5.2.1).
# Excluded from get_dict_cfg()'s schema argument and from the bool batch below: the key is never
# in ConfigManager's _cache, so either would fail at runtime rather than at type-check time.
_VAL_CALIBRATE = const((("Calibrate", "bool", None, None, None, True),))

_N_INT_CFG = const(5)  # SampleInterval + Resolution + Range + IRCompOffset + IRCompAdjust
_N_FLOAT_CFG = const(4)  # AutoRangeThresh + AutoRangeDwell + FiltCoeff + GainRatio
_N_BOOL_CFG = const(1)  # RangeAuto ALONE - Calibrate is command-only (see _VAL_CALIBRATE above)

# @web-group section=sensors submitGroup=self label="ISL29125 — Light, Colour" submit=true
# @web SampleInterval section=sensors submitGroup=self label="Measurement Interval" unit="s"
# @web Resolution section=sensors submitGroup=self label="ADC Resolution" description="16 bit integrates for 101 ms, an exact multiple of both the 50 Hz and 60 Hz mains period, so it rejects lighting flicker. 12 bit is ~16x faster and rejects none." special:12="12 bit (fast)" special:16="16 bit (flicker-rejecting)"
# @web RangeAuto section=sensors submitGroup=self label="Automatic Range" onLabel="Auto" offLabel="Fixed" description="Switches gain between the two ranges on its own, using the chip's threshold interrupt as the fast path and every periodic read as the guaranteed one."
# @web Range section=sensors submitGroup=self label="Fixed Range" unit="lx" description="Used only while Automatic Range is off." special:375="375 lx" special:10000="10000 lx"
# @web AutoRangeThresh section=sensors submitGroup=self label="Switch Threshold" unit="%" description="Percent of the low range's full scale above which the driver switches up. The switch-back-down point is derived from this - 1/53.3 of it - so both ends of the hysteresis always move together and can never be set against each other."
# @web AutoRangeDwell section=sensors submitGroup=self label="Switch-Down Dwell" unit="s" description="Minimum time on the high range before a switch back down is honoured, so a passing shadow does not cost a range change." special:0.0="No dwell - hardware persistence alone"
# @web IRCompOffset section=sensors submitGroup=self label="IR Compensation Offset" description="Adds 106 codes on top of IR Compensation Adjust. Changing IR compensation shifts the lux scale." special:0="Off (0-63 codes)" special:1="On (106-169 codes)"
# @web IRCompAdjust section=sensors submitGroup=self label="IR Compensation Adjust" unit="codes" description="Fine infrared rejection. Changing it shifts the lux scale: the reported full scale is nominal at one setting only."
# @web FiltCoeff section=sensors submitGroup=self label="Output Filter" description="First-order exponential moving average over the measured channels, stepped once per read cycle." special:-1.0="Filter off"
# @web GainRatio section=sensors submitGroup=self label="Range Gain Ratio" decimals=3 description="The applied ratio between the 375 lx and 10000 lx full scales. Nominally 26.667; every real part differs, and the error shows as a step at each range change. Changed only here - measure a candidate with Calibrate below, read it off Measured Gain Ratio, and enter it."
# @web Calibrate section=sensors submitGroup=self label="Calibrate Gain Ratio" onLabel="On" offLabel="Off" description="Only 'On' has effect. Measures the ratio for up to two minutes while the light stays in the auto-range overlap band, and publishes the result as Measured Gain Ratio. Changes nothing on its own." dispatch=true defaultValue=false

_NAME = const("ISL29125")
# Kept as a literal tuple inline (not `_FIELDS` below) because mypy's namedtuple plugin can only
# infer field names from a literal at the call site, not through a variable indirection.
ISL29125 = namedtuple("ISL29125", ("Lux", "Red", "Green", "Blue", "Hue", "Sat", "Bri", "CCT", "RangeAct", "Overrange", "GainMeas", "CalLight", "TS"))
_FIELDS = const(("Lux", "Red", "Green", "Blue", "Hue", "Sat", "Bri", "CCT", "RangeAct", "Overrange", "GainMeas", "CalLight", "TS"))  # kept in sync with ISL29125's own fields above
if TYPE_CHECKING:
    # Narrow on purpose: _error_check() counts a failed read when ANY element is None, and CCT is
    # legitimately None in a dark room. Elements 4 and 5 travel WITH the sample - the range the lux
    # conversion divides by, the span the normalised outputs do - never read back at store time.
    ISLResults = tuple[int | None, int | None, int | None, int | None, int | None, int | None]

# @web-group section=measurements submitGroup=self label="ISL29125 — Light, Colour"
# @web Lux section=measurements submitGroup=self kind=readonly label="Illuminance" unit="lx" decimals=2
# @web R section=measurements submitGroup=self kind=readonly label="Red" path="RGB.R" decimals=4 description="Sensor red, normalised over the whole auto-range span (10000 lx). Relative colour, not a colorimetric measurement."
# @web G section=measurements submitGroup=self kind=readonly label="Green" path="RGB.G" decimals=4
# @web B section=measurements submitGroup=self kind=readonly label="Blue" path="RGB.B" decimals=4
# @web H section=measurements submitGroup=self kind=readonly label="Hue" unit="°" path="HSB.H" decimals=1
# @web S section=measurements submitGroup=self kind=readonly label="Saturation" path="HSB.S" decimals=3
# @web Bri section=measurements submitGroup=self kind=readonly label="Brightness" path="HSB.B" decimals=4 description="Same scale and denominator as RGB, so a dim room reads near 0.003. Read Illuminance when magnitude matters."
# @web CCT section=measurements submitGroup=self kind=readonly label="Colour Temperature" unit="K" decimals=0 description="Relative and uncalibrated - a documented placeholder RGB->XYZ matrix, so repeatable and monotonic rather than a colorimeter reading. Blank below the low-light floor."
# @web RangeAct section=measurements submitGroup=self kind=readonly label="Active Range" unit="lx" decimals=0 description="The full-scale range this sample was taken on, which under automatic ranging is not always the one currently programmed."
# @web Overrange section=measurements submitGroup=self kind=readonly label="Overrange" description="True whenever the current reading is saturated with nothing left to mitigate it: on Fixed range, the configured range itself; under Automatic Range, only once already on the highest range with nowhere further to switch. Not an error - a transient, harmless, always-current status."
# @web GainMeas section=measurements submitGroup=self kind=readonly label="Measured Gain Ratio" decimals=3 description="A candidate measured by the last calibration run, held for ten minutes and then cleared. Blank unless a run produced one. Nothing applies it - copy it into Range Gain Ratio if you want it used."
# @web CalLight section=measurements submitGroup=self kind=readonly label="Calibration Light" description="0 not applicable now (fixed range, or the range is changing), 1 suitable for Calibrate Gain Ratio, 2 too dark, 3 too bright." codes=CalLight
# @web TS section=measurements submitGroup=self kind=readonly label="Timestamp" format=epoch decimals=0

# This driver's one optional live cross-instance dependency (SPECIFICATION.md Part C.14): its own
# FRAM backup target, resolved by buildgen/ (SPECIFICATION.md Part L.4) to an
# already-constructed instance, passed directly as this driver's own log= kwarg.
# @wiring fram_target FRAMManager log optional kwarg

# Driver-declared value domains (SPECIFICATION.md Part L.6.4), read by buildgen/limits.py from the
# tags below - bounds kept in sync with _MIN/_MAX_TRIGGER_S by hand, since a comment cannot
# reference a name. 0x44 is hard-wired (p15), so this driver has no TOML `address` field at all.
# @limits trigger_s 1..3600


class ISL29125_Reader(SensorReaderConfig):
    def __init__(
        self,
        i2c: "I2C",
        irq_pin: int,
        *,
        trigger_s: int = 1,
        irq_pull_up: bool = True,
        # @tunable module.max_error = 5
        max_module_error: int = 5,
        name_ext: str = "",
        cfg_path: str = "",
        log: LogConfig = DEFAULT_LOG,
    ) -> None:
        super().__init__(
            ISL29125(None, None, None, None, None, None, None, None, None, None, None, None, None),
            _NAME,
            _VAL_SAMPLE_INTERVAL + _VAL_RESOLUTION + _VAL_RANGE_AUTO + _VAL_RANGE + _VAL_AUTO_RANGE_THRESH + _VAL_AUTO_RANGE_DWELL
            + _VAL_IR_COMP_OFFSET + _VAL_IR_COMP_ADJUST + _VAL_FILT_COEFF + _VAL_GAIN_RATIO + _VAL_CALIBRATE,
            max_module_error=max_module_error,
            name_ext=name_ext,
            cfg_path=cfg_path,
            log=log,
        )
        self._isl = ISL29125_I2C(i2c)
        self._recovery_bus = i2c
        # This INT is open-drain (p6), so the high level needs a resistor somewhere - unlike SCD30's
        # push-pull RDY. irq_pull_up=True enables the internal one; a board with its own external
        # resistor passes False and gets a bare Pin.IN, so the two are never stacked.
        self.irq_pin = Pin(irq_pin, mode=Pin.IN, pull=Pin.PULL_UP) if irq_pull_up else Pin(irq_pin, mode=Pin.IN)
        # Two flags, two tasks, matching SCD30's shape. _read_event has TWO setters - the divider
        # and the pin IRQ - making the interrupt the fast path and the timer the guaranteed one: a
        # set with no waiter is remembered, so an INT mid-cycle coalesces into one extra cycle.
        self._base_trigger_event = asyncio.ThreadSafeFlag()
        self._read_event = asyncio.ThreadSafeFlag()
        # Bare Timer() is valid on rp2 (id defaults to -1) despite the installed stub package
        # requiring a positional id - a stub inaccuracy, not a code bug.
        self._trigger_timer = Timer()
        self._trigger_period = LockedValue(init_value=int(trigger_s))
        self._trigger_counter = 0
        self._range_auto = True
        self._fixed_range = _RANGE_HIGH_LUX
        # Start on the high range: it cannot clip, so a first sample taken before any decision is
        # made is always usable, where starting low could saturate outright.
        self._active_range = _RANGE_HIGH_LUX
        self._ar_thresh = 85.0
        self._ar_dwell_s = 10.0
        self._last_switch_ms = time.ticks_ms()
        self._periodic_only_switches = 0
        # INTSEL parked because the peak rule overrules the green window it watches (see _read_isl()).
        self._int_held = False
        # One INT re-arm per dead-line episode; cleared by the next interrupt-led decision.
        self._int_rearmed = False
        # Serialises every threshold/range writer: derive the counts, write, commit.
        self._threshold_lock = asyncio.Lock()
        # The Overrange output field for the most recent stored sample, set once per read cycle in
        # _read_isl() and read back by _store_isl(): a transient, always-current status belongs in the
        # measurement output, not the error log (C.7.1).
        self._last_overrange = False
        self._last_cal_light = 0  # the CalLight code for the most recent stored sample, set once per read cycle like Overrange
        # The protocol layer's failed-write sequence as of the last reconciliation - see
        # _verify_config(). Starts level with it, so a clean boot reconciles nothing.
        self._reconciled_write_failures = 0
        # Set by the pin handler, consumed once per read cycle. RGBTHF cannot stand in for it: the
        # CHIP raises that flag, so it is set just the same when the line itself is dead - the
        # missing-pull-up case requirement 17 names (SPECIFICATION.md Part M.1.1).
        self._irq_fired = False
        self._gain_ratio = _GAIN_RATIO_NOMINAL  # the APPLIED factor, replaced only by a config push
        # FiltCoeff, cached like the other software knobs, and the value this cycle captured (schema default: off).
        self._filt_coeff = -1.0
        self._cycle_filter = -1.0
        self._unsettled_cycle = False  # this cycle's settle outlasted its bound: discarded, never a failure
        # Calibration-run state, all RAM-only: a run is user-started, bounded, and publishes a
        # measurement - nothing here reaches the flash. A flag plus a bare deadline, not an Optional
        # one: time.ticks_ms() types as the stubs' _TicksMs, unspellable in an annotation (F.1).
        self._calibrating = False
        self._cal_until_ms = time.ticks_ms()
        self._cal_recent: list[float] = []  # consecutive stable ratios, for the convergence check
        self._cal_meas: float | None = None  # the published candidate, or None when none is current
        self._cal_meas_until_ms = time.ticks_ms()  # when _cal_meas stops being offered
        self._filtered: list[float | None] = [None, None, None]  # green, red, blue, in lux
        self._push_callbacks[name_cfg(_VAL_SAMPLE_INTERVAL)] = self._push_trigger_s
        self._push_callbacks[name_cfg(_VAL_RESOLUTION)] = self._push_resolution
        self._push_callbacks[name_cfg(_VAL_RANGE_AUTO)] = self._push_range_auto
        self._push_callbacks[name_cfg(_VAL_RANGE)] = self._push_range
        self._push_callbacks[name_cfg(_VAL_AUTO_RANGE_THRESH)] = self._push_autorange_thresh
        self._push_callbacks[name_cfg(_VAL_AUTO_RANGE_DWELL)] = self._push_autorange_dwell
        self._push_callbacks[name_cfg(_VAL_IR_COMP_OFFSET)] = self._push_ir_comp_offset
        self._push_callbacks[name_cfg(_VAL_IR_COMP_ADJUST)] = self._push_ir_comp_adjust
        self._push_callbacks[name_cfg(_VAL_FILT_COEFF)] = self._push_filter_coefficient
        self._push_callbacks[name_cfg(_VAL_GAIN_RATIO)] = self._push_gain_ratio
        self._push_callbacks[name_cfg(_VAL_CALIBRATE)] = self._push_calibrate
        # Live read-back for _set_dict_cfg's failed-push recovery chain (SPECIFICATION.md C.5.2).
        # Only the four hardware-backed fields have one: the software knobs have nothing to read
        # back, and Calibrate is command-only, so _recover_failed_push() skips it by design.
        self._get_callbacks[name_cfg(_VAL_RESOLUTION)] = self.get_resolution
        self._get_callbacks[name_cfg(_VAL_RANGE)] = self.get_range
        self._get_callbacks[name_cfg(_VAL_IR_COMP_OFFSET)] = self.get_ir_comp_offset
        self._get_callbacks[name_cfg(_VAL_IR_COMP_ADJUST)] = self.get_ir_comp_adjust

    async def _set_int_armed(self, *, armed: bool) -> None:
        try:
            await self._isl.configure(threshold_interrupt=armed)
        except Exception as e:
            await self.pr.err_s("Error setting the interrupt select:", e, errno=_ERR_CHIP_SET)
            return
        self._int_held = not armed

    def _band_code(self, green_counts: int) -> int:
        # The calibration band: 1 inside the overlap, 2 too dark, 3 too bright (the CalLight codes, SPECIFICATION.md M.1.5).
        lo = self._isl.fraction_to_counts(self._down_thresh())
        hi = self._isl.fraction_to_counts(self._ar_thresh)
        if green_counts <= lo:
            return 2
        if green_counts >= hi:
            return 3
        return 1

    async def _check_divergence(self, raw: bytes) -> None:
        if self._isl.matches_shadow(raw):
            return
        await self.pr.wrn_s("Chip configuration diverged from the shadow - re-applying.", wrnno=_WRN_ISL_DIVERGED)
        try:
            await self._isl.configure(force=True)
        except Exception as e:
            await self.pr.err_s("Error re-applying the diverged configuration:", e, errno=_ERR_CHIP_SET)
            return
        if self._range_auto:
            await self._switch_range(self._active_range)

    async def _checked_cfg(self, value: int | float, schema: "ConfigSchema") -> int | float | None:
        # Part G.2's numeric primitive, not a second hand-rolled cast-and-compare: the bounds come
        # from the field's own schema record, so they cannot drift from the config path's, and the
        # int<->float coercion is the identical policy (a fractional 12.5 is rejected, not cut).
        checked = checked_numeric(value, schema[0])
        if checked is None:
            await self.pr.err_s("Error setting", schema[0][0], "- out of range:", value, errno=_ERR_BAD_ARG)
            return None
        return checked

    def _colour_temperature(self, green_counts: int, norm: list[float]) -> float | None:
        # A dark room is NOT a fault: below the floor the chromaticity denominator collapses and
        # McCamy's n diverges, so None is the correct, expected output here and is logged at `all`.
        if green_counts < _CCT_FLOOR_COUNTS:
            self.pr.all("below the CCT low-light floor", green_counts)
            return None
        xyz = math_helpers.rgb_to_xyz(norm[1], norm[0], norm[2])
        if xyz is None:
            return None
        chroma = math_helpers.chromaticity_xy(xyz[0], xyz[1], xyz[2])
        if chroma is None:
            return None
        return math_helpers.cct_mccamy(chroma[0], chroma[1])

    async def _device_id_answers(self) -> bool:
        # One extra transaction, spent only when the all-ones heuristic already fired - so a false
        # positive costs one wasted read and never decides the verdict on its own.
        try:
            await self._isl.verify_device_id()
        except Exception as e:
            self.pr.err("Device-ID re-read failed:", e)
            return False
        return True

    def _down_thresh(self, ar_thresh: float | None = None) -> float:
        # DERIVED, never configured: right after a switch up the same light reads t/r of the high
        # range, so the down point must clear t/(2r) not to chatter on noise. Against the NOMINAL
        # 26.67, not GainRatio - the factor 2 absorbs that field's whole [20, 34] band.
        return (self._ar_thresh if ar_thresh is None else ar_thresh) / _AR_DOWN_DIVISOR

    async def _end_calibration(self, why: str, *, converged: bool) -> None:
        self._calibrating = False
        self._cal_recent = []
        self.pr.one("Gain-ratio calibration finished:", why)
        if not converged:
            await self.pr.wrn_s("Gain-ratio calibration timed out: no stable reading in the window.", wrnno=_WRN_ISL_CAL_TIMEOUT)

    def _evaluate_range(self, counts: tuple[int, int, int], *, saturated: bool) -> int | None:
        # Decides on the PEAK of all three channels in both directions (owner, 2026-09-12): hardware
        # is green-only (one INTSEL channel), but the output is a colour triple. Peak-up with
        # green-down oscillates - a red-dominant scene switches up, then back once the dwell ends.
        if not self._range_auto:
            return None
        if self._isl.time_to_settle_ms() > 0:
            return None  # a conversion restarted by the last switch has not completed yet
        peak = max(counts)
        if self._active_range == _RANGE_LOW_LUX:
            if saturated or peak >= self._isl.fraction_to_counts(self._ar_thresh):
                return _RANGE_HIGH_LUX
            return None
        now = time.ticks_ms()
        elapsed = time.ticks_diff(now, self._last_switch_ms)
        if elapsed > _MAX_DWELL_MS:
            # Keeps the stored tick within the largest dwell, far inside ticks_diff()'s 2**29 ms horizon.
            self._last_switch_ms = time.ticks_add(now, -_MAX_DWELL_MS)
        if peak > self._isl.fraction_to_counts(self._down_thresh()):
            return None
        # React fast to bright, slowly to dark: PRST is one field applied to both crossings and so
        # cannot be asymmetric, which is what AutoRangeDwell is for. ticks_diff, never subtraction.
        if elapsed < int(self._ar_dwell_s * 1000):
            self.pr.all("switch down suppressed by AutoRangeDwell")
            return None
        return _RANGE_LOW_LUX

    async def _expire_calibration(self) -> bool:
        # Run every cycle, a failed one too: an expired candidate goes and a run past its 2-minute window ends, so
        # neither stored tick is compared after an outage longer than ticks_diff()'s 2**29 ms horizon. True: still running.
        self._measured_ratio()
        if self._calibrating and time.ticks_diff(time.ticks_ms(), self._cal_until_ms) >= 0:
            await self._end_calibration("no stable reading converged before the window closed", converged=False)
        return self._calibrating

    def _gain_correction(self, range_fs: int) -> float:
        # The LOW range is the reference, so the ratio corrects the high one alone - correcting both
        # would drift the absolute scale. learned/nominal, not its reciprocal: a part whose real
        # high full scale exceeds 10000 gives FEWER counts, so lux scales UP by that excess.
        if range_fs != _RANGE_HIGH_LUX:
            return 1.0
        return self._gain_ratio / _GAIN_RATIO_NOMINAL

    def _green_in_window(self, green: int) -> bool:
        # Strictly inside the window the active range arms: on the low range a 0 threshold still fires on 'below or
        # equal' (FN8424 p12).
        if self._active_range == _RANGE_HIGH_LUX:
            return self._isl.fraction_to_counts(self._down_thresh()) < green
        return 0 < green < self._isl.fraction_to_counts(self._ar_thresh)

    def _handle_status(self, status: object) -> tuple[bool, bool]:
        decoded = self._isl.decode_status(status)
        if decoded is None:  # layer 1 failed to produce a byte - the read path decides
            return False, False
        brownout, threshold_fired, rgb_cycles, conversion_done = decoded
        self.pr.all("status", status, "RGBCF", rgb_cycles, "CONVENF", conversion_done)
        return brownout, threshold_fired

    async def _init_isl(self) -> bool:
        self._err_cnt_internal = 0
        self._filtered[0] = self._filtered[1] = self._filtered[2] = None
        self._irq_fired = False
        self._periodic_only_switches = 0
        self._int_held = False
        self._int_rearmed = False
        try:
            await self._isl.setup()
        except Exception as e:
            await self.pr.err_s("Error in initial setup:", e, errno=_ERR_INIT)
            await self._init_failed()
            return False  # error

        self.pr.one("Setting sensor config at startup.")

        int_values = await self.cfgmgr.get_int_values(_VAL_SAMPLE_INTERVAL + _VAL_RESOLUTION + _VAL_RANGE + _VAL_IR_COMP_OFFSET + _VAL_IR_COMP_ADJUST)
        float_values = await self.cfgmgr.get_float_values(_VAL_AUTO_RANGE_THRESH + _VAL_AUTO_RANGE_DWELL + _VAL_FILT_COEFF + _VAL_GAIN_RATIO)
        # The bool batch is RangeAuto alone, and it is not optional: step 9 below cannot decide
        # whether to arm the thresholds without it.
        bool_values = await self.cfgmgr.get_bool_values(_VAL_RANGE_AUTO)
        if (
            int_values is None
            or len(int_values) != _N_INT_CFG
            or float_values is None
            or len(float_values) != _N_FLOAT_CFG
            or bool_values is None
            or len(bool_values) != _N_BOOL_CFG
        ):
            await self.pr.err_s("Error reading config data!", errno=_ERR_CFG_READ)
            return False  # error

        # set_trigger_s() never raises (logs BAD_ARG, keeps the previous value) - a bad stored
        # SampleInterval is a pure software timing knob, not a reason to fail this whole init attempt.
        await self.set_trigger_s(int_values[0])
        self._ar_thresh, self._ar_dwell_s, self._filt_coeff = float_values[0], float_values[1], float_values[2]
        self._gain_ratio = float_values[3]  # already schema-bounded to [20, 34] on the way in
        self._range_auto = bool_values[0]
        self._fixed_range = int_values[2]
        self._active_range = _RANGE_HIGH_LUX if self._range_auto else int_values[2]
        try:  # one burst, applying resolution, range, IR compensation and persistence together
            await self._isl.configure(
                resolution=int_values[1],
                range_fs=self._active_range,
                # Derived from the two fields that determine it, never stored - see
                # persist_for_interval(). configure() applies the resolution from this same call,
                # so the cycle length it is chosen against is the one about to be in force.
                persist=self._isl.persist_for_interval(int_values[0]),
                ir_offset=int_values[3],
                ir_adjust=int_values[4],
                threshold_interrupt=self._range_auto,
            )
        except Exception as e:
            await self.pr.err_s("Error setting config data:", e, errno=_ERR_CHIP_SET)
            await self._init_failed()
            return False  # error

        if self._range_auto:
            # Easy to miss: without this the part boots with its power-on thresholds and the
            # interrupt path is dead until the first switch would have happened anyway.
            await self._switch_range(self._active_range)
        await self._init_done()
        self.pr.one("initialized")
        return True

    async def _measure_gain_ratio(self, green_counts: int) -> None:
        # Only runs inside a user-started window. A SANDWICH - this range, the other, then this one
        # again - because the dominant error is the scene moving between the two readings, which a
        # pair alone cannot tell from a real ratio. Publishes a candidate, never adopts it (M.1.5).
        if not await self._expire_calibration():
            return
        if not self._range_auto or self._isl.time_to_settle_ms() > 0:
            return
        # Only inside the overlap band - bright enough to be well clear of the dark floor on the
        # low range, dim enough not to clip it.
        if self._band_code(green_counts) != 1:
            self.pr.evt("calibration: scene outside the overlap band, waiting")
            return
        here = self._active_range
        there = _RANGE_LOW_LUX if here == _RANGE_HIGH_LUX else _RANGE_HIGH_LUX
        paired = await self._read_on(there)
        # The third leg runs even when the second failed, because it is also what puts the range
        # BACK - skipping it on a clipped or unreadable partner would strand every later sample on
        # the wrong range, which is far worse than the wasted read.
        back = await self._read_on(here)
        if paired is None or back is None:
            return
        # The stability test the pair alone cannot do: if this range no longer reads what it read a
        # moment ago, the light moved during the sandwich and the ratio measures that, not the part.
        if green_counts <= 0 or abs(back - green_counts) > green_counts * _CAL_STABILITY_TOL:
            self._cal_recent = []
            self.pr.evt("calibration: scene moved during the pair", green_counts, "->", back)
            return
        low_counts, high_counts = (green_counts, paired) if here == _RANGE_LOW_LUX else (paired, green_counts)
        if high_counts <= 0:
            return
        sample_ratio = low_counts / high_counts
        if not _GAIN_RATIO_MIN <= sample_ratio <= _GAIN_RATIO_MAX:
            self._cal_recent = []
            self.pr.evt("calibration: ratio implausible, discarding", sample_ratio)
            return
        await self._note_candidate(sample_ratio)

    def _measured_ratio(self) -> float | None:
        # None once the hold expires, and the candidate goes, so nothing compares the stored tick after it.
        if self._cal_meas is None:
            return None
        if time.ticks_diff(time.ticks_ms(), self._cal_meas_until_ms) >= 0:
            self._cal_meas = None
            return None
        return self._cal_meas

    async def _note_candidate(self, sample_ratio: float) -> None:
        # Converged means several consecutive stable sandwiches agreed - one good-looking reading
        # is not evidence, since a slow drift produces a run of self-consistent wrong answers.
        if self._cal_recent and abs(sample_ratio - self._cal_recent[-1]) > self._cal_recent[-1] * _CAL_CONVERGE_TOL:
            self._cal_recent = []
        self._cal_recent.append(sample_ratio)
        self._publish_candidate(sample_ratio)
        self.pr.evt("calibration: candidate", sample_ratio, "run", len(self._cal_recent))
        if len(self._cal_recent) >= _CAL_CONVERGE_N:
            await self._end_calibration(f"{len(self._cal_recent)} consecutive readings agreed, last {sample_ratio:.3f}", converged=True)

    async def _note_decision_source(self, *, threshold_fired: bool) -> None:
        # Requirement 17's silent-failure detector: the periodic evaluation is the safety net, and
        # this is what makes it visible when the net is carrying the load on its own.
        if self._int_held:
            return  # Parked on purpose (agent, 2026-09-29): a periodic-led decision is by design now, not a dead line.
        if threshold_fired:
            self._periodic_only_switches = 0
            self._int_rearmed = False
            return
        self._periodic_only_switches += 1
        if self._periodic_only_switches < _PERIODIC_ONLY_WARN_AT:
            return
        self._periodic_only_switches = 0
        # "Interrupt-led" needs BOTH the pin edge and the latched crossing: either alone is still
        # satisfied by a fault. persist_for_interval() always leaves the chip time to raise RGBTHF
        # first, so five periodic-only decisions running means the line is not delivering them.
        await self.pr.wrn_s("Range decided by the periodic path only - the interrupt may be dead.", wrnno=_WRN_ISL_PERIODIC_ONLY)
        if not self._int_rearmed:
            self._int_rearmed = True
            await self._rearm_interrupt()

    def _on_irq(self, _pin: object) -> None:
        # Soft IRQ (rp2's Pin.irq() defaults to hard=False), so it must allocate nothing, and does
        # not: both lines store into attributes __init__ already created, and ThreadSafeFlag.set()
        # is itself only `self.state = 1` (extmod/asyncio/event.py sanctions it from IRQ context).
        self._irq_fired = True
        self._read_event.set()

    def _publish_candidate(self, value: float) -> None:
        # Every stable sandwich republishes, so the user sees the run settling rather than only its
        # final answer - and the hold restarts from the most recent one, not the first.
        self._cal_meas = value
        self._cal_meas_until_ms = time.ticks_add(time.ticks_ms(), _CAL_HOLD_MS)

    async def _push_autorange_dwell(self, value: int | float | str | bool | None) -> bool:
        return type(value) is float and await self.set_autorange_dwell(value)

    async def _push_autorange_thresh(self, value: int | float | str | bool | None) -> bool:
        return type(value) is float and await self.set_autorange_thresh(value)

    async def _push_calibrate(self, value: int | float | str | bool | None) -> bool:
        # Reports success unconditionally once the type check passes: starting a run that later
        # finds no usable scene has not FAILED, and returning False would run
        # _recover_failed_push() on a command-only field that cannot be recovered (Part C.5.2.1).
        if type(value) is not bool:
            return False
        await self.start_calibration(flag=value)
        return True

    async def _push_filter_coefficient(self, value: int | float | str | bool | None) -> bool:
        return type(value) is float and await self.set_filter_coefficient(value)

    async def _push_gain_ratio(self, value: int | float | str | bool | None) -> bool:
        return type(value) is float and await self.set_gain_ratio(value)

    async def _push_ir_comp_adjust(self, value: int | float | str | bool | None) -> bool:
        return type(value) is int and await self.set_ir_comp_adjust(value)

    async def _push_ir_comp_offset(self, value: int | float | str | bool | None) -> bool:
        return type(value) is int and await self.set_ir_comp_offset(value)

    async def _push_range(self, value: int | float | str | bool | None) -> bool:
        return type(value) is int and await self.set_range(value)

    async def _push_range_auto(self, value: int | float | str | bool | None) -> bool:
        return type(value) is bool and await self.set_range_auto(flag=value)

    async def _push_resolution(self, value: int | float | str | bool | None) -> bool:
        return type(value) is int and await self.set_resolution(value)

    async def _push_trigger_s(self, value: int | float | str | bool | None) -> bool:
        return type(value) is int and await self.set_trigger_s(value)

    async def _read_isl(self) -> "ISLResults":
        self._unsettled_cycle = False
        timestamp = utc_now()  # None until the NTP client has set the clock this boot
        await self._expire_calibration()  # whatever this cycle's read does
        green: int | None = None
        red: int | None = None
        blue: int | None = None
        sample_range: int | None = None
        sample_span: int | None = None
        try:
            # First, once per cycle: a brownout zeroes CONFIG1-3 as well, and BOUTF names it, so that
            # cycle takes the brownout path alone, never also the divergence check on the zeroed CONFIG.
            try:
                status = await self._isl.read_status()
            except Exception as e:  # distinguishable from a data-read failure, and not re-raised
                await self.pr.err_s("Status read failed:", e, errno=_ERR_ISL_STATUS_READ)
                return None, None, None, None, None, timestamp
            # Consumed here, once, so a decision is credited to the interrupt only when the LINE
            # actually woke this cycle - see _note_decision_source().
            irq_fired, self._irq_fired = self._irq_fired, False
            brownout, threshold_fired = self._handle_status(status)
            if brownout:
                # The chip went through power-down, so its whole configuration is 0x00 and the
                # data registers hold nothing measured - there is no sample to report this cycle.
                await self._recover_brownout()
                return None, None, None, None, None, timestamp
            # Before the settle wait, so a re-apply it triggers restarts the conversion in time for
            # that same wait to absorb it - no extra return path, and no sample taken mid-re-apply.
            await self._verify_config()
            if self._isl.time_to_settle_ms() > 0:
                await self._settle_wait()
                if self._isl.time_to_settle_ms() > 0:
                    # Past the bound the data may come from the previous CONFIG1: discard the cycle, count nothing.
                    self._unsettled_cycle = True
                    return None, None, None, None, None, timestamp
            # The three inputs that scale this reading, captured after the settle wait - which is
            # what guarantees the conversion was made under the config live now - and before the
            # first await that can yield. p13: a later push cannot change what is read, only this.
            sample_range = self._active_range
            sample_resolution = self._isl.resolution()
            sample_range_auto = self._range_auto
            sample_span = _RANGE_HIGH_LUX if sample_range_auto else self._fixed_range
            self._cycle_filter = self._filt_coeff

            raw = await self._isl.read_counts()
            if self._isl.is_bus_fault_pattern(raw, status) and not await self._device_id_answers():
                await self.pr.err_s("All-ones data with an implausible status byte, confirmed by a failed device-ID re-read", errno=_ERR_ISL_BUS_FAULT)
                return None, None, None, None, None, timestamp

            counts, saturated = self._isl.normalise(raw, range_fs=sample_range, resolution=sample_resolution)
            target = self._evaluate_range(counts, saturated=saturated)
            if target is not None:
                await self._note_decision_source(threshold_fired=threshold_fired and irq_fired)
                self.pr.evt("range switch", sample_range, "->", target, "peak", max(counts))
                await self._switch_range(target)
            elif self._range_auto:
                # The chip flags green outside its window; the peak of three may hold the range anyway, and in
                # darkness the low range's 0 threshold matches 'below or equal'. Left armed the flag re-fires every
                # PRST window, so it is parked until green is back inside (agent, 2026-09-29).
                if self._int_held:
                    if self._green_in_window(counts[0]):
                        await self._set_int_armed(armed=True)
                elif threshold_fired and irq_fired:
                    await self._set_int_armed(armed=False)
            # Overrange is true only when nothing left could mitigate the saturation: the configured
            # range under Fixed, or Automatic already on its highest. A saturated LOW-range sample
            # under Automatic is excluded - target is non-None above, so a switch is in progress.

            # Judged against sample_range_auto, the mode captured BEFORE the switch-range await, like
            # sample_range/sample_span: a concurrent set_range_auto() landing mid-switch must not
            # retroactively change which mode this already-taken sample is judged against.
            self._last_overrange = saturated and (not sample_range_auto or sample_range == _RANGE_HIGH_LUX)
            self._last_cal_light = 0 if not sample_range_auto or target is not None else self._band_code(counts[0])
            await self._measure_gain_ratio(counts[0])
            self.pr.all("read")
            green, red, blue = counts
        except Exception as e:
            green = red = blue = sample_range = sample_span = None
            await self.pr.err_s("Read failed:", e, errno=_ERR_READ)
        return green, red, blue, sample_range, sample_span, timestamp

    async def _read_loop(self) -> None:
        if not await self._init_isl():  # init sensor at startup
            return  # break and restart if init fails
        while True:
            await self._read_event.wait()  # timer divider or INT pin, whichever came first
            self.pr.evt("sensor trigger")
            results = await self._read_isl()  # read data
            # A failed read clears every measured value; TS alone is None until the first NTP sync, and a cycle
            # discarded past the settle bound read nothing to fail - neither counts.
            if not await self._error_check(results, condition=results[0] is None and not self._unsettled_cycle):
                return  # break and restart if too many errors
            await self._store_isl(results)  # store data in result buffer

    async def _read_on(self, target_range: int) -> int | None:
        # One leg of the sandwich: switch, wait out the settle the switch just armed, read green.
        # Returns None on any failure, having logged it - the caller abandons the whole sandwich.
        if not await self._switch_range(target_range):
            return None
        try:
            await self._settle_wait()
            raw = await self._isl.read_counts()
        except Exception as e:
            await self.pr.err_s("Paired gain-ratio reading failed:", e, errno=_ERR_READ)
            return None
        counts, saturated = self._isl.normalise(raw, range_fs=self._active_range)
        if saturated:
            # A clipped leg measures the clamp, not the part: the band gate is range-agnostic, so a
            # scene fine on THIS range can be far past full scale on the other one.
            self._cal_recent = []
            self.pr.evt("calibration: the other range cannot represent this scene")
            return None
        return counts[0]

    async def _read_sensor_dict(self) -> "dict[str, CfgValue] | None":
        # Reads the real registers rather than the shadow - the only thing that can detect the two
        # diverging. A read of 0x01 is not the write Table 7 names, so a read-only snapshot starts
        # nothing and creates no read-modify-write hazard. No reading is None: the GET's unavailable marker.
        try:
            raw = await self._isl.get_config_snapshot()
        except Exception as e:
            await self.pr.err_s("Error reading config from sensor:", e, errno=_ERR_CHIP_GET)
            return None
        await self._check_divergence(raw)
        decoded = self._isl.decode_config(raw)
        if decoded is None:
            return None
        resolution, range_fs, ir_offset, ir_adjust, _persist = decoded
        result: dict[str, CfgValue] = {
            name_cfg(_VAL_RESOLUTION): resolution,
            name_cfg(_VAL_IR_COMP_OFFSET): ir_offset,
            name_cfg(_VAL_IR_COMP_ADJUST): ir_adjust,
        }
        # Under auto-range the chip's RNG bit is the state machine's choice, not the user's
        # setting, so reporting it as the Range CONFIG field would overwrite the stored preference
        # in the displayed config. The active range is an output and is reported as RangeAct.
        if not self._range_auto:
            result[name_cfg(_VAL_RANGE)] = range_fs
        return result

    async def _reapply_configuration(self) -> bool:
        # The whole shadow, BOUTF cleared and the thresholds re-armed: the brownout's recovery and the participant rung.
        try:
            await self._isl.configure(force=True)
            await self._isl.clear_brownout()
        except Exception as e:
            await self.pr.err_s("Error re-applying configuration:", e, errno=_ERR_CHIP_SET)
            return False
        if self._range_auto:
            await self._switch_range(self._active_range)  # never raises; logs its own
        return True

    async def _reapply_persist(self, trigger_s: int) -> bool:
        # Called by the only two setters whose value feeds the derivation. Writing the same value
        # back is free - configure() diffs the shadow and writes nothing when nothing changed.
        try:
            await self._isl.configure(persist=self._isl.persist_for_interval(trigger_s))
        except Exception as e:
            await self.pr.err_s("Error applying the derived transient rejection:", e, errno=_ERR_CHIP_SET)
            return False
        return True

    async def _rearm_interrupt(self) -> None:
        try:
            await self._isl.configure(force=True)
        except Exception as e:
            await self.pr.err_s("Error re-arming the interrupt:", e, errno=_ERR_CHIP_SET)
            return
        await self._write_thresholds()  # logs its own

    async def _recover_brownout(self) -> bool:
        # Every brownout warns: a supply that keeps sagging is counted per event, and the
        # newest-entry rule spends one slot for the run (SPECIFICATION.md C.7.1).
        await self.pr.wrn_s("Brownout detected - re-applying the whole configuration.", wrnno=_WRN_ISL_BROWNOUT)
        return await self._reapply_configuration()

    async def _recover_device(self) -> bool:
        # Participant rung: re-configuration from the shadow; the 0x46 reset stays setup()'s (task restart).
        return await self._reapply_configuration()

    async def _settle_wait(self) -> None:
        # Bounded rather than an open `while pending`: concurrent config writes can keep pushing the
        # deadline out; past the bound the cycle is discarded, never published, so the loop cannot
        # starve and nothing stale is reported.
        for _ in range(_SETTLE_WAIT_MAX_ROUNDS):
            remaining = self._isl.time_to_settle_ms()
            if remaining <= 0:
                return
            self.pr.all("settle discard", remaining)
            await asyncio.sleep_ms(remaining)

    async def _snapshot_field(self, index: int, what: str) -> int | None:
        try:
            decoded = self._isl.decode_config(await self._isl.get_config_snapshot())
        except Exception as e:
            await self.pr.err_s("Error reading", what, ":", e, errno=_ERR_CHIP_GET)
            return None
        if decoded is None:
            return None
        return decoded[index]

    async def _store_isl(self, results: "ISLResults") -> None:
        green, red, blue, sample_range, sample_span, timestamp = results
        if green is None or red is None or blue is None or sample_range is None or sample_span is None:
            return  # don't run on invalid data; the timestamp may be None before the first sync
        filter_coefficient = self._cycle_filter

        correction = self._gain_correction(sample_range)
        lux = [self._isl.counts_to_lux(count, sample_range, correction) for count in (green, red, blue)]
        # The filter runs on the three absolute lux channels, not on the derived outputs, so Lux,
        # RGB, HSB and CCT all stay mutually consistent and there is exactly one filter state.
        for index, value in enumerate(lux):
            filtered = math_helpers.ema_step(self._filtered[index], value, filter_coefficient)
            if filtered is not None:
                self._filtered[index] = filtered
                lux[index] = filtered

        # The whole auto-range SPAN, not the active range: dividing by the active full scale would
        # step every normalised output by the gain ratio at each switch - the discontinuity
        # auto-range exists to remove. With RangeAuto off there is no span, so the pinned range is.
        span = float(sample_span)
        norm = [min(1.0, max(0.0, value / span)) for value in lux]

        hsb = math_helpers.rgb_to_hsb(norm[1], norm[0], norm[2])  # red, green, blue
        hue, sat, bri = hsb if hsb is not None else (None, None, None)
        await self._set_meas_data(
            ISL29125(
                Lux=lux[0],  # green alone: its response approximates the CIE Y curve (p14, Figure 13)
                Red=norm[1],
                Green=norm[0],
                Blue=norm[2],
                Hue=hue,
                Sat=sat,
                Bri=bri,
                CCT=self._colour_temperature(green, norm),
                RangeAct=sample_range,
                Overrange=self._last_overrange,
                GainMeas=self._measured_ratio(),  # None unless a recent run produced a candidate
                CalLight=self._last_cal_light,
                TS=timestamp,
            ),
        )
        self.pr.all("data stored")

    async def _switch_range(self, target_range: int) -> bool:
        # One threshold per range, because the two switch points sit on different gain scales: low
        # range up-crossing only, high range down-crossing only. Both counts arrive on the 16-bit
        # scale; set_thresholds() rescales them to the resolution the chip is running.
        async with self._threshold_lock:
            # thresholds FIRST: the other order leaves a window where the new gain is live against the old thresholds
            if not await self._write_thresholds_locked(target_range, self._ar_thresh):
                return False
            try:
                await self._isl.configure(range_fs=target_range)
            except Exception as e:
                # _active_range is deliberately NOT updated, so the next cycle re-evaluates and
                # retries the whole switch - idempotent, since both writes are absolute values.
                await self.pr.err_s("Error writing the range bit:", e, errno=_ERR_CHIP_SET)
                return False
            self._last_switch_ms = time.ticks_ms()
            self._active_range = target_range
        return True

    async def _verify_config(self) -> None:
        # The chip is the authority: one snapshot per cycle catches a burst that NAKed partway and a
        # CONFIG byte corrupted on the bus, on a headless device too.
        seen = self._isl.write_failures()
        try:
            raw = await self._isl.get_config_snapshot()
        except Exception as e:
            self.pr.err("Config read-back for reconciliation failed, retried next cycle:", e)
            return
        self._reconciled_write_failures = seen
        await self._check_divergence(raw)

    async def _write_thresholds(self, ar_thresh: float | None = None) -> bool:
        # The range and the threshold are read inside the hold, so a switch or a push landing while this waits
        # never leaves counts derived from a stale pair; the cache changes only once the chip took them.
        async with self._threshold_lock:
            value = self._ar_thresh if ar_thresh is None else ar_thresh
            if not await self._write_thresholds_locked(self._active_range, value):
                return False
            if ar_thresh is not None:
                self._ar_thresh = ar_thresh
        return True

    async def _write_thresholds_locked(self, range_fs: int, ar_thresh: float) -> bool:
        # The caller holds _threshold_lock. Low range: the up-crossing alone; high range: the down-crossing,
        # the omitted up-crossing parked at the top of scale, where it cannot fire.
        try:
            if range_fs == _RANGE_LOW_LUX:
                await self._isl.set_thresholds(0, self._isl.fraction_to_counts(ar_thresh))
            else:
                await self._isl.set_thresholds(self._isl.fraction_to_counts(self._down_thresh(ar_thresh)))
        except Exception as e:
            await self.pr.err_s("Error writing auto-range thresholds:", e, errno=_ERR_CHIP_SET)
            return False
        return True

    # -- starters ----------------------------------------------------------

    def get_task_starters(self) -> "list[TaskStarter]":
        return [self.start_asy_read, self.start_asy_trigger]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []

    def get_trigger_starters(self) -> "list[TimerStarter]":
        return [self.start_timer]

    def start_asy_read(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._read_loop())

    def start_asy_trigger(self) -> asyncio.Task[None]:
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._trigger_loop())

    def start_timer(self) -> None:
        try:
            self._trigger_timer.init(
                period=1000,
                mode=Timer.PERIODIC,
                callback=lambda _b: self._base_trigger_event.set(),
            )
        except (MemoryError, OSError) as e:
            # Alarm pool exhausted (ENOMEM) or no memory: wake the waiting task, which logs it and ends; its restart re-arms.
            self._timer_failed(e, self._base_trigger_event)
        # FALLING, not rising: the INT is active-low open-drain (p6). A line held low by a fault
        # produces exactly one edge and then silence - which is what the periodic path and
        # the ISL_PERIODIC_ONLY warning exist for, not a flood. The bound method is built once, here, not per edge.
        self.irq_pin.irq(
            trigger=self.irq_pin.IRQ_FALLING,
            handler=self._on_irq,
        )

    def stop_timer(self) -> None:
        self._trigger_timer.deinit()  # Timer.deinit() IS real on rp2, unlike I2C/SPI (Part F.5.1)

    # -- getters -----------------------------------------------------------

    async def get_data(self) -> ISL29125:
        # Narrows to this Reader's concrete ISL29125 - see SPECIFICATION.md C.4.2's convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_cfg(self) -> dict[str, dict[str, int | float | str | bool | None]]:
        # Calibrate is deliberately absent from this schema argument: ConfigManager.get_dict()
        # is all-or-nothing and would KeyError on a key it never persisted.
        return await self._get_dict_cfg(
            self.name,
            _VAL_SAMPLE_INTERVAL + _VAL_RESOLUTION + _VAL_RANGE_AUTO + _VAL_RANGE + _VAL_AUTO_RANGE_THRESH + _VAL_AUTO_RANGE_DWELL
            + _VAL_IR_COMP_OFFSET + _VAL_IR_COMP_ADJUST + _VAL_FILT_COEFF + _VAL_GAIN_RATIO,
            callback=self._read_sensor_dict,
        )

    async def get_dict_data(self) -> "JsonDict":
        # The one genuine override here: the measurement body is nested, which make_dict()'s flat
        # one-level contract cannot express. Written out explicitly rather than from the namedtuple,
        # because _asdict()/_fields need a ROM level above rp2's own.
        data = await self.get_data()
        return {
            self.name: {
                "Lux": data.Lux,
                "RGB": {"R": data.Red, "G": data.Green, "B": data.Blue},
                "HSB": {"H": data.Hue, "S": data.Sat, "B": data.Bri},
                "CCT": data.CCT,
                "RangeAct": data.RangeAct,
                "Overrange": data.Overrange,
                "GainMeas": data.GainMeas,
                "CalLight": data.CalLight,
                "TS": data.TS,
            },
        }

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def get_ir_comp_adjust(self) -> int | None:
        return await self._snapshot_field(3, "IR compensation adjust")

    async def get_ir_comp_offset(self) -> int | None:
        return await self._snapshot_field(2, "IR compensation offset")

    async def get_range(self) -> int | None:
        return await self._snapshot_field(1, "range")

    async def get_resolution(self) -> int | None:
        return await self._snapshot_field(0, "resolution")

    # -- setters -----------------------------------------------------------

    async def set_autorange_dwell(self, value: float) -> bool:
        dwell = await self._checked_cfg(value, _VAL_AUTO_RANGE_DWELL)
        if dwell is None:
            return False
        self._ar_dwell_s = float(dwell)
        return True

    async def set_autorange_thresh(self, value: float) -> bool:
        # The down point follows automatically; the cache changes only once the chip's registers took the
        # value, so a failed push restores a consistent persisted value.
        thresh = await self._checked_cfg(value, _VAL_AUTO_RANGE_THRESH)
        if thresh is None:
            return False
        return await self._write_thresholds(ar_thresh=float(thresh))

    async def set_filter_coefficient(self, value: float) -> bool:
        # Caches the coefficient like the other software knobs; the read cycle captures it with the range and resolution.
        coeff = await self._checked_cfg(value, _VAL_FILT_COEFF)
        if coeff is None:
            return False
        self._filt_coeff = float(coeff)
        return True

    async def set_gain_ratio(self, value: float) -> bool:
        # The one and only way the applied factor changes, cached like the other software knobs:
        # _gain_correction() reads the attribute on every sample rather than going back to cfgmgr.
        coerced = await self._checked_cfg(value, _VAL_GAIN_RATIO)
        if coerced is None:
            return False
        self._gain_ratio = float(coerced)
        return True

    async def set_ir_comp_adjust(self, value: int) -> bool:
        try:
            await self._isl.configure(ir_adjust=value)
        except Exception as e:
            await self.pr.err_s("Error setting IR compensation adjust:", e, errno=_ERR_CHIP_SET)
            return False
        return True

    async def set_ir_comp_offset(self, value: int) -> bool:
        try:
            await self._isl.configure(ir_offset=value)
        except Exception as e:
            await self.pr.err_s("Error setting IR compensation offset:", e, errno=_ERR_CHIP_SET)
            return False
        return True

    async def set_range(self, value: int) -> bool:
        try:
            if self._range_auto:  # stored as the preference only; the state machine owns the RNG bit
                self._isl.check_range(value)
            else:
                await self._isl.configure(range_fs=value)
                self._active_range = value
        except Exception as e:
            await self.pr.err_s("Error setting range:", e, errno=_ERR_CHIP_SET)
            return False
        self._fixed_range = value
        return True

    async def set_range_auto(self, *, flag: bool) -> bool:
        # Not a purely software flag: turning it OFF applies the stored fixed range (CONFIG1) and
        # disarms the interrupt with INTSEL = 00 (CONFIG3). Parking the thresholds cannot disarm it -
        # the part fires on "below OR EQUAL TO", so 0x0000 still interrupts in total darkness.
        try:  # neither branch reads the flag, so it is cached only once the chip has taken it -
            # a False here makes _recover_failed_push() roll the PERSISTED value back, and a cache
            # updated regardless would leave the two disagreeing until the next restart.
            if flag:
                await self._isl.configure(threshold_interrupt=True)
                self._int_held = False
            else:
                await self._isl.configure(range_fs=self._fixed_range, threshold_interrupt=False)
                self._active_range = self._fixed_range
        except Exception as e:
            await self.pr.err_s("Error applying the auto-range mode:", e, errno=_ERR_CHIP_SET)
            return False
        self._range_auto = flag
        if flag:
            await self._switch_range(self._active_range)  # re-arm the thresholds for where we are
        return True

    async def set_resolution(self, value: int) -> bool:
        try:
            await self._isl.configure(resolution=value)
        except Exception as e:
            await self.pr.err_s("Error setting resolution:", e, errno=_ERR_CHIP_SET)
            return False
        # A resolution change changes the cycle length, so the derived persistence changes with it.
        period = await self._trigger_period.get_value()  # set at construction, never None
        if period is None or not await self._reapply_persist(int(period)):
            return False
        # The registers compare the RAW ADC value, so a resolution change rescales them, armed or not.
        await self._write_thresholds()
        return True

    async def set_trigger_s(self, value: float) -> bool:
        trigger_s = await self._checked_cfg(value, _VAL_SAMPLE_INTERVAL)
        if trigger_s is None:
            return False
        await self._trigger_period.set_value(int(trigger_s))
        return await self._reapply_persist(int(trigger_s))

    # -- others ------------------------------------------------------------

    async def start_calibration(self, *, flag: bool) -> bool:
        # flag=False is deliberately a no-op, matching SGP40_Reader.reset_voc()'s own contract.
        if not flag:
            return False
        self._cal_until_ms = time.ticks_add(time.ticks_ms(), _CAL_WINDOW_MS)
        self._calibrating = True
        self._cal_recent = []
        self.pr.one("Gain-ratio calibration started - measuring while the scene stays in the overlap band.")
        return True


class ISL29125_I2C:
    # Protocol layer for the ISL29125. Holds a SHADOW of all three config bytes and never reads
    # them back to modify them: CONFIG1 has two writers (auto-range's RNG and the API's BITS), so
    # a read-modify-write could silently lose a concurrent change.

    def __init__(self, i2c: "I2C") -> None:
        self._i2c_isl29125 = DeviceSession(I2CDevice(i2c, _ISL29125_ADDR))
        # The post-reset state of every field (p9-p11, Tables 3/8/10: all three registers 0x00).
        self._mode = 0
        self._range_fs = _RANGE_LOW_LUX
        self._resolution = _RESOLUTION_16BIT
        self._sync = 0
        self._ir_offset = 0
        self._ir_adjust = 0
        self._persist = 1
        self._int_select = _INTSEL_NONE
        self._conven = 0
        self._settle_until_ms = time.ticks_ms()
        # Bumped whenever a shadow write raises: a wrap-by-design sequence (wraps at COUNTER_CAP)
        # the reader compares for equality - saturating it would freeze reconciliation.
        self._write_failures = 0

    @staticmethod
    def _dark_offset(range_fs: int) -> int:
        # DDark is specified at range 0 only (p3), where it is material: the same dark current is
        # ~1/26.67 count on the high range, so subtracting one there would remove real signal.
        # DDark is specified in 16-bit counts (FN8424 p3), so it is subtracted after the 12-bit shift.
        return _DARK_COUNTS if range_fs == _RANGE_LOW_LUX else 0

    @staticmethod
    def _decode_rgb_burst(raw: bytes | bytearray | memoryview | None) -> tuple[int, int, int] | None:
        # Register order is GREEN, RED, BLUE (p9, Table 1) - p13's Table 20 mislabels its own rows.
        if raw is None:
            return None
        try:
            if len(raw) != _DATA_BURST_LEN:
                return None
            green, red, blue = struct.unpack("<HHH", bytes(raw))
        except (TypeError, ValueError):
            return None
        return int(green), int(red), int(blue)

    async def _read_byte(self, register: int) -> int:
        # One register byte; None from the bus layer means no bus, raised so every caller's error path logs it.
        async with self._i2c_isl29125 as isl, isl.i2c_device as i2c:
            raw = await i2c.get_register_bytes(register, 1)
        if raw is None:
            raise OSError("I2C bus not initialized")
        return raw[0]

    @staticmethod
    def _reject_outside(value: int, low: int, high: int, what: str) -> None:
        # _reject_unless for a contiguous field - same type-then-value order, same reasons.
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{what} must be an integer from {low} to {high}")

    @staticmethod
    def _reject_unless(value: int, allowed: tuple[int, ...], what: str) -> None:
        # C.3's contract: reject loudly here rather than let encode_shadow() silently mask an
        # out-of-range value to its bit width (an IRCompAdjust of 200 would land as 8). The type
        # check is not redundant: 375.0 passes `in`, then raises inside a function contracted not to.
        if type(value) is not int or value not in allowed:
            raise ValueError(f"{what} must be one of {allowed}")

    async def _write_shadow_locked(self, i2c: I2CDevice, first_register: int) -> None:
        # The caller already holds both the device-session and bus locks, so this takes none of its
        # own: re-acquiring the session lock here would let a concurrent reader see a mutated shadow
        # against an unwritten chip.
        payload = self.encode_shadow()[first_register - _REGISTER_CONFIG1 :]
        # set_register_struct() takes one value but accepts bytes, so an "Ns" format is how a
        # burst write goes through the promoted bus layer. The payload is already bytes of the
        # exact length because struct.pack() truncates silently on MicroPython.
        if not await i2c.set_register_struct(first_register, f"{len(payload)}s", payload):
            raise OSError("I2C bus not initialized")

    async def get_config_snapshot(self) -> bytes:
        # One 3-byte burst under one device-session lock, returned UNDECODED: decoding here would
        # throw away mode, SYNC, CONVEN and INTSEL, which are the four things a brownout or a
        # stray write actually corrupts - defeating the divergence check this exists for.
        async with self._i2c_isl29125 as isl, isl.i2c_device as i2c:
            raw = await i2c.get_register_bytes(_REGISTER_CONFIG1, _CONFIG_BURST_LEN)
        if raw is None:
            raise OSError("I2C bus not initialized")
        return raw

    async def get_device_id(self) -> int:
        return await self._read_byte(_REGISTER_DEVICE_ID)

    @staticmethod
    def is_bus_fault_pattern(counts: tuple[int, int, int] | None, status: object) -> bool:
        # A dead bus reads all-ones, which is exactly what this part's community failure reports
        # show. Taken on the RAW counts: the pattern is a property of the wire, not of the scaled
        # value, which makes the 12-bit case exact - a real 12-bit reading cannot exceed 4095.
        if counts is None or len(counts) != _CHANNELS:
            return False
        if not all(count == _FULL_SCALE_COUNTS for count in counts):
            return False
        # 0x08's B7:B6 and B3 are reserved and read zero (p12, Table 15), so any of them set is
        # impossible on a working part - and a non-int is layer 1 failing to produce a byte at all.
        return type(status) is not int or bool(status & _STATUS_RESERVED_MASK)

    async def set_thresholds(self, low_counts: int, high_counts: int | None = None) -> None:
        # Both counts arrive on the 16-bit scale and are rescaled to the active resolution (the registers
        # compare RAW values); an omitted high_counts parks the up-crossing. Scaled inside the session:
        # the resolution shadow may change while this waits for the lock.
        async with self._i2c_isl29125 as isl, isl.i2c_device as i2c:
            twelve_bit = self._resolution == _RESOLUTION_12BIT
            shift = 4 if twelve_bit else 0
            ceiling = (1 << _RESOLUTION_12BIT) - 1 if twelve_bit else _FULL_SCALE_COUNTS
            low = max(0, min(ceiling, low_counts >> shift))
            high = ceiling if high_counts is None else max(0, min(ceiling, high_counts >> shift))
            packed = struct.pack("<HH", low, high)  # 0x04-0x07, low pair then high pair (p12, Table 14)
            if not await i2c.set_register_struct(_REGISTER_THRESHOLDS, "4s", packed):
                raise OSError("I2C bus not initialized")

    def check_range(self, value: int) -> None:
        # The same guard configure() applies, reachable without writing: the reader stores a fixed
        # range as a preference while auto-range owns the chip's RNG bit, and that preference still
        # has to be a range the part actually has.
        self._reject_unless(value, _RANGES, "range")

    async def clear_brownout(self) -> None:
        # Table 15 marks 0x08 "RO", but p12's own BOUTF text requires an I2C write to clear it -
        # the marking is a datasheet defect, not a prohibition.
        async with self._i2c_isl29125 as isl, isl.i2c_device as i2c:
            if not await i2c.set_register_struct(_REGISTER_STATUS, "B", 0x00):
                raise OSError("I2C bus not initialized")

    async def configure(
        self,
        *,
        mode: int | None = None,
        range_fs: int | None = None,
        resolution: int | None = None,
        ir_offset: int | None = None,
        ir_adjust: int | None = None,
        persist: int | None = None,
        threshold_interrupt: bool | None = None,
        sync: int | None = None,
        conven: int | None = None,
        force: bool = False,
    ) -> None:
        # The single write path, writing the MINIMAL burst: three bytes from 0x01 when CONFIG1
        # changed, two from 0x02 otherwise, nothing when nothing changed. force=True re-applies the
        # whole shadow, which brownout recovery and the divergence check need. Every field is guarded.
        if resolution is not None:
            self._reject_unless(resolution, _RESOLUTIONS, "resolution")
        if range_fs is not None:
            self.check_range(range_fs)
        if ir_offset is not None:
            self._reject_unless(ir_offset, _IR_OFFSETS, "IR compensation offset")
        if ir_adjust is not None:
            self._reject_outside(ir_adjust, 0, _CONFIG2_ALSCC_MASK, "IR compensation adjust")
        if persist is not None:
            self._reject_unless(persist, _PRST_SETTINGS, "threshold persistence")
        # Validate-mutate-write(-rollback) runs under ONE hold of the device-session lock, not just
        # the final write (Part C.8): a shadow mutated outside it would let a concurrent matches_shadow()
        # see a change the chip has not taken - a false divergence report.
        wrote_config1 = False
        async with self._i2c_isl29125 as isl, isl.i2c_device as i2c:
            before = self.encode_shadow()
            # Every mutable field, captured as one tuple so a failed write can put all of them back.
            restore = (self._mode, self._range_fs, self._resolution, self._ir_offset, self._ir_adjust, self._persist, self._int_select, self._sync, self._conven)
            if mode is not None:
                self._mode = mode
            if range_fs is not None:
                self._range_fs = range_fs
            if resolution is not None:
                self._resolution = resolution
            if ir_offset is not None:
                self._ir_offset = ir_offset
            if ir_adjust is not None:
                self._ir_adjust = ir_adjust
            if persist is not None:
                self._persist = persist
            if threshold_interrupt is not None:
                # INTSEL selects ONE channel (p11, Table 11) and green is the one the auto-range
                # state machine watches, so "armed" and "green" are the same choice - the caller
                # asks for the behaviour and this owns the encoding.
                self._int_select = _INTSEL_GREEN if threshold_interrupt else _INTSEL_NONE
            if sync is not None:
                self._sync = sync
            if conven is not None:
                self._conven = conven
            after = self.encode_shadow()
            if after == before and not force:
                return
            wrote_config1 = force or after[0] != before[0]
            try:
                await self._write_shadow_locked(i2c, _REGISTER_CONFIG1 if wrote_config1 else _REGISTER_CONFIG2)
            except Exception:
                # The shadow must never claim a value the part did not take: normalise() scales every
                # reading by it, so a lost resolution write shifts every later sample 16x while the
                # reads still succeed. Rolled back inside the lock, so it is never observable.
                (self._mode, self._range_fs, self._resolution, self._ir_offset, self._ir_adjust, self._persist, self._int_select, self._sync, self._conven) = restore
                self._write_failures = self._write_failures + 1 if self._write_failures < COUNTER_CAP else 0
                raise
        if wrote_config1:
            # Table 7 starts the ADC at an I2C write to 0x01 and leaves open whether a conversion in flight
            # restarts, so every CONFIG1 writer arms the settle deadline where the write happens; outside
            # the lock: timing bookkeeping only.
            self._settle_until_ms = time.ticks_add(time.ticks_ms(), _SETTLE_CYCLES * self.cycle_ms())

    @staticmethod
    def counts_to_lux(count: int, full_scale: int, gain_correction: float) -> float:
        # p1 gives 375/65535 = 5.72 mlux and 10000/65535 = 0.1526 lux per LSB, so the LSB really is
        # FS/65535 on both ranges. gain_correction is validated where an untrusted ratio ENTERS
        # (GainRatio's schema bounds), never here - a hot-path gate would run on every sample.
        return count * (full_scale / 65535.0) * gain_correction

    def cycle_ms(self) -> int:
        return _CYCLE_MS_12BIT if self._resolution == _RESOLUTION_12BIT else _CYCLE_MS_16BIT

    @staticmethod
    def decode_config(raw: bytes | bytearray | memoryview | None) -> tuple[int, int, int, int, int] | None:
        # The exact inverse of encode_shadow(), for the five hardware-backed config fields. An
        # illegal field encoding is returned as decoded, never coerced - that is information the
        # caller needs, not an error this function gets to resolve.
        if raw is None:
            return None
        try:
            if len(raw) != _CONFIG_BURST_LEN:
                return None
            config1, config2, config3 = raw[0], raw[1], raw[2]
        except (IndexError, TypeError):
            return None
        resolution = _RESOLUTION_12BIT if config1 & _CONFIG1_BITS else _RESOLUTION_16BIT
        range_fs = _RANGE_HIGH_LUX if config1 & _CONFIG1_RNG else _RANGE_LOW_LUX
        ir_offset = 1 if config2 & _CONFIG2_IRCOMP_OFFSET else 0
        ir_adjust = config2 & _CONFIG2_ALSCC_MASK
        persist: int = _PRST_SETTINGS[(config3 >> _CONFIG3_PRST_SHIFT) & 0x03]
        return resolution, range_fs, ir_offset, ir_adjust, persist

    @staticmethod
    def decode_status(status: object) -> tuple[bool, bool, int, bool] | None:
        # Brownout, threshold crossing, the RGBCF conversion counter and CONVENF (p12, Tables
        # 15-19). None means layer 1 never produced a byte at all - what that means is the
        # caller's decision, not a value this can invent.
        if type(status) is not int:
            return None
        return (
            bool(status & _STATUS_BOUTF),
            bool(status & _STATUS_RGBTHF),
            (status >> _STATUS_RGBCF_SHIFT) & 0x03,
            bool(status & _STATUS_CONVENF),
        )

    def encode_shadow(self) -> bytes:
        # Every field masked to its own width before shifting, so an out-of-range value cannot
        # disturb a neighbour - the guard asy_i2c_driver.py's set_bits() applies. Masks rather than
        # validates: that belongs at the setter boundary, and a raising encoder would blur configure().
        config1 = (self._mode & _CONFIG1_MODE_MASK) | (_CONFIG1_RNG if self._range_fs == _RANGE_HIGH_LUX else 0)
        config1 |= (_CONFIG1_BITS if self._resolution == _RESOLUTION_12BIT else 0) | (_CONFIG1_SYNC if self._sync else 0)
        config2 = (_CONFIG2_IRCOMP_OFFSET if self._ir_offset else 0) | (self._ir_adjust & _CONFIG2_ALSCC_MASK)
        prst = _PRST_SETTINGS.index(self._persist)
        config3 = (self._int_select & _CONFIG3_INTSEL_MASK) | (prst << _CONFIG3_PRST_SHIFT)
        config3 |= _CONFIG3_CONVEN if self._conven else 0
        return bytes((config1, config2, config3))

    @staticmethod
    def fraction_to_counts(fraction: float) -> int:
        # The whole computation in float, rounded exactly once at the end. RIOT's own driver writes
        # `(uint16_t)(65535 / max_range)` and truncates 6.55 to 6 - a 9% error from doing the scaling
        # in integer arithmetic, which is why this is a named function rather than an inline expression.
        if fraction != fraction:  # NaN, which no comparison below would catch
            return 0
        counts = fraction * 0.01 * 65535.0
        if not counts > 0.0:  # also catches -inf
            return 0
        if counts >= _FULL_SCALE_COUNTS:  # also catches +inf
            return _FULL_SCALE_COUNTS
        # round() returns an int on MicroPython as well as on CPython (verified directly against the
        # pinned Unix-port interpreter), so no int() wrapper is needed here.
        return round(counts)

    def matches_shadow(self, raw: bytes | bytearray | memoryview) -> bool:
        # A masked comparison of every meaningful bit, not of five decoded fields: mode, SYNC, CONVEN
        # and INTSEL are exactly what a brownout zeroes, and decoding them away would blind this
        # check. An unreadable length answers True - a failed read is not evidence of divergence.
        if len(raw) != _CONFIG_BURST_LEN:
            return True
        shadow = self.encode_shadow()
        masks = (_CONFIG1_MASK, _CONFIG2_MASK, _CONFIG3_MASK)
        return all(raw[i] & masks[i] == shadow[i] & masks[i] for i in range(_CONFIG_BURST_LEN))

    def normalise(self, raw: tuple[int, int, int], *, range_fs: int, resolution: int | None = None) -> tuple[tuple[int, int, int], bool]:
        # Saturation is judged RAW, because a post-rescale `== 65535` test is wrong at 12 bits (4095
        # << 4 is 65520) and would leave the fast path dead. ANY channel at its maximum counts - a
        # clipped red destroys Hue, Sat and CCT. Both range_fs and resolution are the SAMPLE's.
        green, red, blue = raw
        twelve_bit = (self._resolution if resolution is None else resolution) == _RESOLUTION_12BIT
        maximum = (1 << _RESOLUTION_12BIT) - 1 if twelve_bit else _FULL_SCALE_COUNTS
        saturated = green >= maximum or red >= maximum or blue >= maximum
        # 12- and 16-bit readings onto one 0-65535 scale, and the additive dark offset off. An
        # unknown resolution falls back to "no shift", the conservative direction: shifting when you
        # should not inflates every reading 16x, not shifting only under-reports.
        shift = 4 if twelve_bit else 0
        offset = self._dark_offset(range_fs)
        scaled = [max(0, min(_FULL_SCALE_COUNTS, (value << shift) - offset)) for value in (green, red, blue)]
        return (scaled[0], scaled[1], scaled[2]), saturated

    def persist_for_interval(self, trigger_s: int) -> int:
        # PRST is DERIVED: the largest transient rejection whose window still closes inside one
        # sample interval, so the chip always raises RGBTHF before the periodic re-check decides; a
        # hand-set PRST can leave the fast path structurally dead (Part M.1.4).
        cycle = self.cycle_ms()
        options: tuple[int, ...] = _PRST_SETTINGS  # const() is Any to mypy; same annotation decode_config() uses
        for persist in reversed(options):
            if persist * cycle < trigger_s * 1000:
                return persist
        # Unreachable at the current schema bounds - one 16-bit cycle is 303ms against a minimum
        # 1s interval - but this is the honest degradation if either bound ever moves.
        return options[0]

    async def read_counts(self) -> tuple[int, int, int]:
        async with self._i2c_isl29125 as isl, isl.i2c_device as i2c:
            raw = await i2c.get_register_bytes(_REGISTER_DATA, _DATA_BURST_LEN)
        if raw is None:
            raise OSError("I2C bus not initialized")
        counts = self._decode_rgb_burst(raw)
        if counts is None:
            raise OSError("unexpected RGB data burst read result")
        return counts

    async def read_status(self) -> int:
        # DESTRUCTIVE: the read clears RGBTHF and releases the INT pin (p11/p12), so it happens
        # exactly once per read cycle and nothing else in this driver may read 0x08 "just to
        # check" - a second reader would silently consume another consumer's interrupt state.
        return await self._read_byte(_REGISTER_STATUS)

    async def reset(self) -> None:
        # The datasheet specifies no post-reset settle, so the verify read IS the settle. CONFIG1-3
        # only, NOT status the way SparkFun's reset() does: reading 0x08 would consume a destructive
        # read outside the one-per-cycle invariant read_status() depends on (M.1.2).
        async with self._i2c_isl29125 as isl, isl.i2c_device as i2c:
            if not await i2c.set_register_struct(_REGISTER_DEVICE_ID, "B", _CMD_RESET):
                raise OSError("I2C bus not initialized")
            config = await i2c.get_register_bytes(_REGISTER_CONFIG1, _CONFIG_BURST_LEN)
        if config is None:
            raise OSError("I2C bus not initialized")
        if any(config):
            raise RuntimeError(f"reset did not clear the config registers (read {config!r})")
        self._mode = 0
        self._range_fs = _RANGE_LOW_LUX
        self._resolution = _RESOLUTION_16BIT
        self._sync = 0
        self._ir_offset = 0
        self._ir_adjust = 0
        self._persist = 1
        self._int_select = _INTSEL_NONE
        self._conven = 0

    def resolution(self) -> int:
        # The shadow's own value, for a caller that has to pair a reading with the resolution the
        # part made it under rather than with whatever is live by the time it scales it.
        return self._resolution

    async def setup(self) -> bool:
        async with self._i2c_isl29125 as isl, isl.i2c_device as i2c:
            await i2c.setup()
        await self.verify_device_id()
        await self.reset()
        # BOUTF is high at power-up (p12). Kept even though the 0x46 reset and any status read both
        # clear it on real silicon (Part M.1.2): it is the one clear the datasheet promises, costs
        # one transaction per init, and makes the post-setup state mechanism-independent.
        await self.clear_brownout()
        # SYNC and CONVEN are written explicitly rather than left at their reset default, so neither
        # can flip silently later: SYNC = 1 turns INT into an INPUT and inverts the whole interrupt
        # path, and CONVEN would mux conversion-done onto the pin the thresholds need.
        await self.configure(mode=_MODE_RGB, threshold_interrupt=True, sync=0, conven=0, force=True)
        return True

    def time_to_settle_ms(self) -> int:
        remaining = time.ticks_diff(self._settle_until_ms, time.ticks_ms())
        if remaining <= 0:
            # A passed deadline moves up to now, so the stored tick never ages past the ticks horizon.
            self._settle_until_ms = time.ticks_ms()
            return 0
        return remaining

    async def verify_device_id(self) -> None:
        # Raising rather than returning a verdict, so setup() fails loudly on the wrong part and
        # the reader's own all-ones bus-fault confirmation can just catch it.
        device_id = await self.get_device_id()
        if device_id != _DEVICE_ID:
            raise RuntimeError(f"failed to find ISL29125, device ID {hex(device_id)}")

    def write_failures(self) -> int:
        # The failed-shadow-write sequence (compared for equality only). The chip is the authority
        # after one, because the burst may have landed in part - see configure()'s own roll-back.
        return self._write_failures
