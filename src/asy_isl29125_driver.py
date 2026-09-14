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
from asy_i2c_driver import I2CDevice
from base_classes import Lockable, LockedValue, SensorReaderConfig
from config_manager import name_cfg, type_or_range_error

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from asy_fram_manager import AsyFramManager
    from asy_i2c_driver import I2C
    from config_manager import ConfigSchema
    from print_log import ErrorLog


_DEVICE_ID = const(0x7D)  # datasheet p9, Table 2
_CMD_RESET = const(0x46)  # written to 0x00: "the device will reset all registers to their default states" (p9)

_REGISTER_DEVICE_ID = const(0x00)
_REGISTER_CONFIG1 = const(0x01)
_REGISTER_CONFIG2 = const(0x02)
_REGISTER_CONFIG3 = const(0x03)  # never addressed on its own - only ever written as the tail of a burst from 0x01/0x02
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

# Device/maths constants, deliberately NOT config fields - requirement 1 governs preferences, and
# none of these is one (SPECIFICATION.md Part C.11.2's own classification note).
_DARK_COUNTS = const(1)  # DDark typ 1 / max 5 counts at range 0 (p3, Electrical Specifications)
_CCT_FLOOR_COUNTS = const(64)  # ~13x the worst-case dark count: below it a 5-count additive error
# moves a channel ratio by more than ~8%, and chromaticity noise grows far faster than hue noise.
_GAIN_RATIO_NOMINAL = const(26.666666666666668)  # 10000/375 - the ratio a fresh unit starts from
_GAIN_RATIO_MIN = const(20.0)  # a plausibility gate around nominal, applied where an untrusted
_GAIN_RATIO_MAX = const(34.0)  # value enters (on load and on learn), never in the hot path
# Calibration is a bounded, user-started run, never a background schedule: the driver only ever
# READS GainRatio, so nothing it does can write the flash (SPECIFICATION.md Part C.11.3).
_CAL_WINDOW_MS = const(120000)  # hard stop on a run that never converges - ~100 attempts at 16 bit
_CAL_HOLD_MS = const(600000)  # how long a finished run's candidate stays readable before it clears
_CAL_CONVERGE_N = const(3)  # consecutive stable ratios that must agree before the run stops early
_CAL_CONVERGE_TOL = const(0.01)  # 1%: one bench scene measured 28.11/28.01/28.09, a 0.4% spread
_CAL_STABILITY_TOL = const(0.02)  # 2% between the sandwich's first and third reading of one range
_AR_DOWN_DIVISOR = const(53.333333333333336)  # 2 x the NOMINAL range ratio - see _down_thresh()
_SETTLE_CYCLES = const(2)  # conversions discarded after a range switch, fixed - see configure()
_SETTLE_WAIT_MAX_ROUNDS = const(2)  # one extra cycle past the deadline, so a stream of concurrent
# config writes can extend the settle but can never starve the read loop indefinitely.
_PERIODIC_ONLY_WARN_AT = const(5)  # consecutive periodic-path switches with no preceding interrupt

_MIN_TRIGGER_SECS = const(1)
_MAX_TRIGGER_SECS = const(3600)
_MIN_DWELL_S = const(0.0)
_MAX_DWELL_S = const(300.0)
_MIN_FILT_COEFF = const(-1.0)
_MAX_FILT_COEFF = const(1.0)
_MIN_AR_THRESH = const(50.0)
_MAX_AR_THRESH = const(95.0)

_VAL_SI = const((("SampleInterv", "int", 1, _MIN_TRIGGER_SECS, _MAX_TRIGGER_SECS, None),))
# Resolution/Range/IrCompOffset are genuine discrete allowed-value sets, not
# continuous ranges - the 6th-slot `special` shape asy_bmp3xx_driver.py's own _VAL_POV established.
_VAL_RES = const((("Resolution", "int", 16, None, None, _RESOLUTIONS),))
_VAL_RA = const((("RangeAuto", "bool", True, None, None, None),))
_VAL_RNG = const((("Range", "int", 10000, None, None, _RANGES),))
# The single switch-up point, as a percentage of full scale. The down point is DERIVED from it
# (_down_thresh()) rather than configured: there is one correct hysteresis gap for a given
# threshold, and a second field could only ever be used to get it wrong.
_VAL_AR_THRESH = const((("AutoRangeThresh", "float", 85.0, _MIN_AR_THRESH, _MAX_AR_THRESH, None),))
_VAL_AR_DWELL = const((("AutoRangeDwell", "float", 10.0, _MIN_DWELL_S, _MAX_DWELL_S, None),))
_VAL_ICO = const((("IrCompOffset", "int", 0, None, None, _IR_OFFSETS),))
_VAL_ICA = const((("IrCompAdjust", "int", 40, 0, 63, None),))
_VAL_FC = const((("FiltCoeff", "float", -1.0, _MIN_FILT_COEFF, _MAX_FILT_COEFF, None),))
# The applied scale factor, and the only thing _gain_correction() reads. A user PUT is its only
# writer - the driver never writes its own config, which keeps every flash write on the REST path.
# A measured candidate is published as GainMeas for the user to copy across, never adopted.
_VAL_GR = const((("GainRatio", "float", _GAIN_RATIO_NOMINAL, _GAIN_RATIO_MIN, _GAIN_RATIO_MAX, None),))
# Command-only trigger, the schema's "special-alone" shape (SPECIFICATION.md Part C.5.2.1).
# Excluded from get_dict_cfg()'s schema argument and from the bool batch below: the key is never
# in ConfigManager's _cache, so either would fail at runtime rather than at type-check time.
_VAL_CALIB = const((("ISLCalibrate", "bool", None, None, None, True),))

_N_INT_CFG = const(5)  # SampleInterv + Resolution + Range + IrCompOffset + IrCompAdjust
_N_FLOAT_CFG = const(4)  # AutoRangeThresh + AutoRangeDwell + FiltCoeff + GainRatio
_N_BOOL_CFG = const(1)  # RangeAuto ALONE - ISLCalibrate is command-only (see _VAL_CALIB above)
_N_STORE_CFG = const(1)  # FiltCoeff ALONE - the only config value the store path reads per sample

_NAME = const("ISL29125")
# Kept as a literal tuple inline (not `_FIELDS` below) because mypy's namedtuple plugin can only
# infer field names from a literal at the call site, not through a variable indirection.
ISL29125 = namedtuple("ISL29125", ("Lux", "Red", "Green", "Blue", "Hue", "Sat", "Bri", "CCT", "RangeAct", "GainMeas", "TS"))
_FIELDS = const(("Lux", "Red", "Green", "Blue", "Hue", "Sat", "Bri", "CCT", "RangeAct", "GainMeas", "TS"))  # kept in sync with ISL29125's own fields above
if TYPE_CHECKING:
    # Narrow on purpose: _error_check() counts a failed read when ANY element is None, and CCT is
    # legitimately None in a dark room. Elements 4 and 5 travel WITH the sample - the range the lux
    # conversion divides by, the span the normalised outputs do - never read back at store time.
    ISLResults = tuple[int | None, int | None, int | None, int | None, int | None, int | None]


class ISL29125_Reader(SensorReaderConfig):
    def __init__(
        self,
        i2c: "I2C",
        irq_pin: int,
        address: int = 0x44,
        trigger_sec: int = 1,
        max_module_error: int = 5,
        cfg_path: str = "",
        fram: "AsyFramManager | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        super().__init__(
            ISL29125(None, None, None, None, None, None, None, None, None, None, None),
            max_module_error,
            _NAME,
            _VAL_SI + _VAL_RES + _VAL_RA + _VAL_RNG + _VAL_AR_THRESH + _VAL_AR_DWELL
            + _VAL_ICO + _VAL_ICA + _VAL_FC + _VAL_GR + _VAL_CALIB,
            cfg_path=cfg_path,
            fram=fram,
            history_length=history_length,
            debug=debug,
        )
        self.isl = ISL29125_I2C(i2c, address=address)
        # PULL_UP, unlike SCD30's bare Pin.IN: this INT is open-drain pull-down (p6), so the high
        # level has to come from a resistor. The dev board has an external 10k, and enabling the
        # internal one too is harmless there and is what makes the driver work on a board without.
        self.irq_pin = Pin(irq_pin, mode=Pin.IN, pull=Pin.PULL_UP)
        # Two flags, two tasks, matching SCD30's shape. read_event has TWO setters - the divider
        # and the pin IRQ - making the interrupt the fast path and the timer the guaranteed one: a
        # set with no waiter is remembered, so an INT mid-cycle coalesces into one extra cycle.
        self.base_trigger_event = asyncio.ThreadSafeFlag()
        self.read_event = asyncio.ThreadSafeFlag()
        # Bare Timer() is valid on rp2 (id defaults to -1) despite the installed stub package
        # requiring a positional id - a stub inaccuracy, not a code bug.
        self.trigger_timer = Timer()
        self.trigger_period = LockedValue(init_value=int(trigger_sec))
        self.trigger_counter = 0
        self._range_auto = True
        self._fixed_range = _RANGE_HIGH_LUX
        # Start on the high range: it cannot clip, so a first sample taken before any decision is
        # made is always usable, where starting low could saturate outright.
        self._active_range = _RANGE_HIGH_LUX
        self._ar_thresh = 85.0
        self._ar_dwell_s = 10.0
        self._last_switch_ms = time.ticks_ms()
        self._brownout_seen = False
        self._periodic_only_switches = 0
        # The protocol layer's failed-write count as of the last reconciliation - see
        # _verify_after_failed_write(). Starts level with it, so a clean boot reconciles nothing.
        self._reconciled_write_failures = 0
        # Set by the pin handler, consumed once per read cycle. RGBTHF alone cannot stand in for
        # it: the flag is raised by the CHIP, so it is set just the same when the line itself is
        # dead - which is precisely the missing pull-up / broken jumper requirement 17 names.
        self._irq_fired = False
        self._gain_ratio = _GAIN_RATIO_NOMINAL  # the APPLIED factor, replaced only by a config push
        # Calibration-run state, all RAM-only: a run is user-started, bounded, and publishes a
        # measurement - nothing here reaches the flash. A flag plus a bare deadline, not an Optional
        # one: time.ticks_ms() types as the stubs' _TicksMs, unspellable in an annotation (F.1).
        self._calibrating = False
        self._cal_until_ms = time.ticks_ms()
        self._cal_recent: list[float] = []  # consecutive stable ratios, for the convergence check
        self._cal_meas: float | None = None  # the published candidate, or None when none is current
        self._cal_meas_until_ms = time.ticks_ms()  # when _cal_meas stops being offered
        self._filtered: list[float | None] = [None, None, None]  # green, red, blue, in lux
        self._push_callbacks[name_cfg(_VAL_SI)] = self._push_trigger_secs
        self._push_callbacks[name_cfg(_VAL_RES)] = self._push_resolution
        self._push_callbacks[name_cfg(_VAL_RA)] = self._push_range_auto
        self._push_callbacks[name_cfg(_VAL_RNG)] = self._push_range
        self._push_callbacks[name_cfg(_VAL_AR_THRESH)] = self._push_autorange_thresh
        self._push_callbacks[name_cfg(_VAL_AR_DWELL)] = self._push_autorange_dwell
        self._push_callbacks[name_cfg(_VAL_ICO)] = self._push_ir_comp_offset
        self._push_callbacks[name_cfg(_VAL_ICA)] = self._push_ir_comp_adjust
        self._push_callbacks[name_cfg(_VAL_FC)] = self._push_filter_coefficient
        self._push_callbacks[name_cfg(_VAL_GR)] = self._push_gain_ratio
        self._push_callbacks[name_cfg(_VAL_CALIB)] = self._push_calibrate
        # Live read-back for _set_dict_cfg's failed-push recovery chain (SPECIFICATION.md C.5.2).
        # Only the four hardware-backed fields have one: the software knobs have nothing to read
        # back, and ISLCalibrate is command-only, so _recover_failed_push() skips it by design.
        self._get_callbacks[name_cfg(_VAL_RES)] = self.get_resolution
        self._get_callbacks[name_cfg(_VAL_RNG)] = self.get_range
        self._get_callbacks[name_cfg(_VAL_ICO)] = self.get_ir_comp_offset
        self._get_callbacks[name_cfg(_VAL_ICA)] = self.get_ir_comp_adjust

    # -- lifecycle ---------------------------------------------------------

    async def _init_isl(self) -> bool:
        await self.pr.setup()  # required for all logged warnings and errors
        self._err_cnt_internal = 0
        try:
            await self.isl.setup()
        except Exception as e:
            await self.pr.err_s("Error in initial setup:", e, errno=10)
            return False  # error

        self.pr.one("Setting sensor config at startup.")

        int_values = await self.cfgmgr.get_int_values(_VAL_SI + _VAL_RES + _VAL_RNG + _VAL_ICO + _VAL_ICA)
        float_values = await self.cfgmgr.get_float_values(_VAL_AR_THRESH + _VAL_AR_DWELL + _VAL_FC + _VAL_GR)
        # The bool batch is RangeAuto alone, and it is not optional: step 9 below cannot decide
        # whether to arm the thresholds without it.
        bool_values = await self.cfgmgr.get_bool_values(_VAL_RA)
        if (
            int_values is None
            or len(int_values) != _N_INT_CFG
            or float_values is None
            or len(float_values) != _N_FLOAT_CFG
            or bool_values is None
            or len(bool_values) != _N_BOOL_CFG
        ):
            await self.pr.err_s("Error reading config data!", errno=12)
            return False  # error

        # set_trigger_secs() never raises (logs errno=25, keeps the previous value) - a bad stored
        # SampleInterv is a pure software timing knob, not a reason to fail this whole init attempt.
        await self.set_trigger_secs(int_values[0])
        self._ar_thresh, self._ar_dwell_s = float_values[0], float_values[1]
        self._gain_ratio = float_values[3]  # already schema-bounded to [20, 34] on the way in
        self._range_auto = bool_values[0]
        self._fixed_range = int_values[2]
        self._active_range = _RANGE_HIGH_LUX if self._range_auto else int_values[2]
        try:  # one burst, applying resolution, range, IR compensation and persistence together
            await self.isl.configure(
                resolution=int_values[1],
                range_fs=self._active_range,
                # Derived from the two fields that determine it, never stored - see
                # persist_for_interval(). configure() applies the resolution from this same call,
                # so the cycle length it is chosen against is the one about to be in force.
                persist=self.isl.persist_for_interval(int_values[0]),
                ir_offset=int_values[3],
                ir_adjust=int_values[4],
                threshold_interrupt=self._range_auto,
            )
        except Exception as e:
            await self.pr.err_s("Error setting config data:", e, errno=13)
            return False  # error

        if self._range_auto:
            # Easy to miss: without this the part boots with its power-on thresholds and the
            # interrupt path is dead until the first switch would have happened anyway.
            await self._switch_range(self._active_range)
        self.pr.one("initialized")
        return True

    async def _base_trigger(self) -> None:
        self.trigger_counter = 0
        while True:
            await self.base_trigger_event.wait()
            self.trigger_counter += 1
            if self.trigger_counter >= await self.trigger_period.get_value():
                self.read_event.set()
                self.trigger_counter = 0

    def _on_irq(self, _pin: object) -> None:
        # Soft IRQ (rp2's Pin.irq() defaults to hard=False), so it must allocate nothing, and does
        # not: both lines store into attributes __init__ already created, and ThreadSafeFlag.set()
        # is itself only `self.state = 1` (extmod/asyncio/event.py sanctions it from IRQ context).
        self._irq_fired = True
        self.read_event.set()

    # -- read path ---------------------------------------------------------

    async def _read_isl(self) -> "ISLResults":
        timestamp: int | None = None
        green: int | None = None
        red: int | None = None
        blue: int | None = None
        sample_range: int | None = None
        sample_span: int | None = None
        try:
            timestamp = time.mktime(time.gmtime())
            # Before the settle wait, so a re-apply it triggers restarts the conversion in time for
            # that same wait to absorb it - no extra return path, and no sample taken mid-re-apply.
            await self._verify_after_failed_write()
            if self.isl.time_to_settle_ms() > 0:
                await self._settle_wait()
            # The three inputs that scale this reading, captured after the settle wait - which is
            # what guarantees the conversion was made under the config live now - and before the
            # first await that can yield. p13: a later push cannot change what is read, only this.
            sample_range = self._active_range
            sample_resolution = self.isl.resolution()
            sample_span = _RANGE_HIGH_LUX if self._range_auto else self._fixed_range
            try:
                status = await self.isl.read_status()
            except Exception as e:  # distinguishable from a data-read failure, and not re-raised
                await self.pr.err_s("Status read failed:", e, errno=31)
                return None, None, None, None, None, None
            # Consumed here, once, so a decision is credited to the interrupt only when the LINE
            # actually woke this cycle - see _note_decision_source().
            irq_fired, self._irq_fired = self._irq_fired, False
            brownout, threshold_fired = self._handle_status(status)
            if not brownout:
                self._brownout_seen = False
            else:
                # The chip went through power-down, so its whole configuration is 0x00 and the
                # data registers hold nothing measured - there is no sample to report this cycle.
                await self._recover_brownout()
                return None, None, None, None, None, None

            raw = await self.isl.read_counts()
            if self.isl.is_bus_fault_pattern(raw, status) and not await self._device_id_answers():
                await self.pr.err_s("All-ones data with an implausible status byte, confirmed by a failed device-ID re-read", errno=32)
                return None, None, None, None, None, None

            counts, saturated = self.isl.normalise(raw, range_fs=sample_range, resolution=sample_resolution)
            target = self._evaluate_range(counts, saturated=saturated)
            if target is not None:
                await self._note_decision_source(threshold_fired=threshold_fired and irq_fired)
                self.pr.evt("range switch", sample_range, "->", target, "peak", max(counts))
                await self._switch_range(target)
            elif saturated and sample_range == _RANGE_HIGH_LUX:
                await self.pr.wrn_s("Saturated on the high range - the scene exceeds the part.", wrnno=12)
            await self._measure_gain_ratio(counts[0])
            self.pr.all("read")
            green, red, blue = counts
        except Exception as e:
            green = red = blue = sample_range = sample_span = timestamp = None
            await self.pr.err_s("Read failed:", e, errno=11)
        return green, red, blue, sample_range, sample_span, timestamp

    async def _device_id_answers(self) -> bool:
        # One extra transaction, spent only when the all-ones heuristic already fired - so a false
        # positive costs one wasted read and never decides the verdict on its own.
        try:
            await self.isl.verify_device_id()
        except Exception:
            return False
        return True

    async def _note_decision_source(self, *, threshold_fired: bool) -> None:
        # Requirement 17's silent-failure detector: the periodic evaluation is the safety net, and
        # this is what makes it visible when the net is carrying the load on its own.
        if threshold_fired:
            self._periodic_only_switches = 0
            return
        self._periodic_only_switches += 1
        if self._periodic_only_switches < _PERIODIC_ONLY_WARN_AT:
            return
        self._periodic_only_switches = 0
        # "Interrupt-led" needs BOTH the pin edge and the latched crossing: either alone is still
        # satisfied by a fault. persist_for_interval() always leaves the chip time to raise RGBTHF
        # first, so five periodic-only decisions running means the line is not delivering them.
        await self.pr.wrn_s("Range decided by the periodic path only - the interrupt may be dead.", wrnno=13)

    def _handle_status(self, status: object) -> "tuple[bool, bool]":
        decoded = self.isl.decode_status(status)
        if decoded is None:  # layer 1 failed to produce a byte - the read path decides
            return False, False
        brownout, threshold_fired, rgb_cycles, conversion_done = decoded
        self.pr.all("status", status, "RGBCF", rgb_cycles, "CONVENF", conversion_done)
        return brownout, threshold_fired

    async def _recover_brownout(self) -> bool:
        if not self._brownout_seen:
            # Logged on the TRANSITION only, so a supply that keeps sagging produces one warning
            # per real event rather than one per second.
            self._brownout_seen = True
            await self.pr.wrn_s("Brownout detected - re-applying the whole configuration.", wrnno=10)
        try:
            await self.isl.configure(force=True)
            await self.isl.clear_brownout()
        except Exception as e:
            await self.pr.err_s("Error re-applying configuration after brownout:", e, errno=33)
            return False
        if self._range_auto:
            await self._switch_range(self._active_range)  # never raises; logs its own errnos
        return True

    async def _verify_after_failed_write(self) -> None:
        # configure()'s roll-back describes the chip only when NOTHING landed; a burst NAKing
        # partway leaves it a mixture. The chip is the authority, so one snapshot settles it - here,
        # not only in _read_sensor_dict(), which a headless device never reaches.
        seen = self.isl.write_failures()
        if seen == self._reconciled_write_failures:
            return
        try:
            raw = await self.isl.get_config_snapshot()
        except Exception:
            return  # the bus is down; the counts still differ, so the next cycle tries again
        self._reconciled_write_failures = seen
        await self._check_divergence(raw)

    async def _store_isl(self, results: "ISLResults") -> None:
        green, red, blue, sample_range, sample_span, timestamp = results
        if green is None or red is None or blue is None or sample_range is None or sample_span is None or timestamp is None:
            return  # don't run on invalid data

        # FiltCoeff ALONE, matching spec R5: the other three floats in the init batch are
        # auto-range POLICY, already cached on the reader by their own setters, so reading them
        # again here would cost a config lookup per sample for values this function never uses.
        cfg_values = await self.cfgmgr.get_float_values(_VAL_FC)
        if cfg_values is None or len(cfg_values) != _N_STORE_CFG:
            cfg_values = [-1.0]
            await self.pr.err_s("Error reading config data!", errno=14)
        filter_coefficient = cfg_values[0]

        correction = self._gain_correction(sample_range)
        lux = [self.isl.counts_to_lux(count, sample_range, correction) for count in (green, red, blue)]
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
                GainMeas=self._measured_ratio(),  # None unless a recent run produced a candidate
                TS=timestamp,
            ),
        )
        self.pr.all("data stored")

    def _colour_temperature(self, green_counts: int, norm: "list[float]") -> float | None:
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

    def _gain_correction(self, range_fs: int) -> float:
        # The LOW range is the reference, so the ratio corrects the high one alone - correcting both
        # would drift the absolute scale. learned/nominal, not its reciprocal: a part whose real
        # high full scale exceeds 10000 gives FEWER counts, so lux scales UP by that excess.
        if range_fs != _RANGE_HIGH_LUX:
            return 1.0
        return self._gain_ratio / _GAIN_RATIO_NOMINAL

    # -- auto-range --------------------------------------------------------

    def _evaluate_range(self, counts: "tuple[int, int, int]", *, saturated: bool) -> int | None:
        # Decides on the PEAK of all three channels in both directions: the hardware path is
        # green-only because INTSEL has one channel, but the output is a colour triple. Peak-up with
        # green-down oscillates - a red-dominant scene switches up, then back once the dwell ends.
        if not self._range_auto:
            return None
        if self.isl.time_to_settle_ms() > 0:
            return None  # a conversion restarted by the last switch has not completed yet
        peak = max(counts)
        if self._active_range == _RANGE_LOW_LUX:
            if saturated or peak >= self.isl.fraction_to_counts(self._ar_thresh):
                return _RANGE_HIGH_LUX
            return None
        if peak > self.isl.fraction_to_counts(self._down_thresh()):
            return None
        # React fast to bright, slowly to dark: PRST is one field applied to both crossings and so
        # cannot be asymmetric, which is what AutoRangeDwell is for. ticks_diff, never subtraction.
        if time.ticks_diff(time.ticks_ms(), self._last_switch_ms) < int(self._ar_dwell_s * 1000):
            self.pr.all("switch down suppressed by AutoRangeDwell")
            return None
        return _RANGE_LOW_LUX

    async def _switch_range(self, target_range: int) -> bool:
        # One threshold per range, because the two switch points sit on different gain scales: low
        # range up-crossing only, high range down-crossing only. Both counts arrive on the 16-bit
        # scale; set_thresholds() rescales them to the resolution the chip is running.
        try:  # thresholds FIRST: the other order leaves a window where the new gain is live
            if target_range == _RANGE_LOW_LUX:  # against the old thresholds
                await self.isl.set_thresholds(0, self.isl.fraction_to_counts(self._ar_thresh))
            else:  # the omitted up-crossing parks at the top of scale, where it cannot fire
                await self.isl.set_thresholds(self.isl.fraction_to_counts(self._down_thresh()))
        except Exception as e:
            await self.pr.err_s("Error writing auto-range thresholds:", e, errno=29)
            return False
        try:
            await self.isl.configure(range_fs=target_range)
        except Exception as e:
            # _active_range is deliberately NOT updated, so the next cycle re-evaluates and
            # retries the whole switch - idempotent, since both writes are absolute values.
            await self.pr.err_s("Error writing the range bit:", e, errno=30)
            return False
        self._last_switch_ms = time.ticks_ms()
        self._active_range = target_range
        return True

    async def _settle_wait(self) -> None:
        # Bounded rather than an open `while pending`: concurrent config writes can keep pushing the
        # deadline out. Past the bound the reading stands - a possibly-stale sample beats a starved
        # read loop, and the leaky bucket catches a persistent problem anyway.
        for _ in range(_SETTLE_WAIT_MAX_ROUNDS):
            remaining = self.isl.time_to_settle_ms()
            if remaining <= 0:
                return
            self.pr.all("settle discard", remaining)
            await asyncio.sleep_ms(remaining)

    # -- gain-ratio calibration -------------------------------------------

    async def _measure_gain_ratio(self, green_counts: int) -> None:
        # Only runs inside a user-started window. A SANDWICH - this range, the other, then this one
        # again - because the dominant error is the scene moving between the two readings, which a
        # pair alone cannot tell from a real ratio. Publishes a candidate, never adopts it (C.11.3).
        if not self._calibrating:
            return
        if time.ticks_diff(time.ticks_ms(), self._cal_until_ms) >= 0:
            await self._end_calibration("no stable reading converged before the window closed")
            return
        if not self._range_auto or self.isl.time_to_settle_ms() > 0:
            return
        # Only inside the overlap band - bright enough to be well clear of the dark floor on the
        # low range, dim enough not to clip it.
        if not self.isl.fraction_to_counts(self._down_thresh()) < green_counts < self.isl.fraction_to_counts(self._ar_thresh):
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

    async def _read_on(self, target_range: int) -> int | None:
        # One leg of the sandwich: switch, wait out the settle the switch just armed, read green.
        # Returns None on any failure, having logged it - the caller abandons the whole sandwich.
        if not await self._switch_range(target_range):
            return None
        try:
            await self._settle_wait()
            raw = await self.isl.read_counts()
        except Exception as e:
            await self.pr.err_s("Paired gain-ratio reading failed:", e, errno=11)
            return None
        counts, saturated = self.isl.normalise(raw, range_fs=self._active_range)
        if saturated:
            # A clipped leg measures the clamp, not the part: the band gate is range-agnostic, so a
            # scene fine on THIS range can be far past full scale on the other one.
            self._cal_recent = []
            self.pr.evt("calibration: the other range cannot represent this scene")
            return None
        return counts[0]

    async def _note_candidate(self, sample_ratio: float) -> None:
        # Converged means several consecutive stable sandwiches agreed - one good-looking reading
        # is not evidence, since a slow drift produces a run of self-consistent wrong answers.
        if self._cal_recent and abs(sample_ratio - self._cal_recent[-1]) > self._cal_recent[-1] * _CAL_CONVERGE_TOL:
            self._cal_recent = []
        self._cal_recent.append(sample_ratio)
        self._publish_candidate(sample_ratio)
        self.pr.evt("calibration: candidate", sample_ratio, "run", len(self._cal_recent))
        if len(self._cal_recent) >= _CAL_CONVERGE_N:
            await self._end_calibration(f"{len(self._cal_recent)} consecutive readings agreed, last {sample_ratio:.3f}")

    def _publish_candidate(self, value: float) -> None:
        # Every stable sandwich republishes, so the user sees the run settling rather than only its
        # final answer - and the hold restarts from the most recent one, not the first.
        self._cal_meas = value
        self._cal_meas_until_ms = time.ticks_add(time.ticks_ms(), _CAL_HOLD_MS)

    def _measured_ratio(self) -> float | None:
        # None once the hold expires, so a stale candidate can never be mistaken for a fresh one.
        if self._cal_meas is None or time.ticks_diff(time.ticks_ms(), self._cal_meas_until_ms) >= 0:
            return None
        return self._cal_meas

    async def _end_calibration(self, why: str) -> None:
        self._calibrating = False
        self._cal_recent = []
        self.pr.one("Gain-ratio calibration finished:", why)

    async def _read_sensor_dict(self) -> "dict[str, int | float | str | bool | None]":
        # Reads the real registers rather than the shadow - the only thing in the driver that can
        # detect the two diverging. Only a WRITE to 0x01 restarts the conversion (p10, Table 7), so
        # a read-only snapshot costs one transaction and creates no read-modify-write hazard.
        try:
            raw = await self.isl.get_config_snapshot()
        except Exception as e:
            await self.pr.err_s("Error reading config from sensor:", e, errno=28)
            return dict.fromkeys(
                (name_cfg(_VAL_RES), name_cfg(_VAL_RNG), name_cfg(_VAL_ICO), name_cfg(_VAL_ICA)),
                None,
            )
        await self._check_divergence(raw)
        decoded = self.isl.decode_config(raw)
        if decoded is None:
            return {}
        resolution, range_fs, ir_offset, ir_adjust, _persist = decoded
        result: dict[str, int | float | str | bool | None] = {
            name_cfg(_VAL_RES): resolution,
            name_cfg(_VAL_ICO): ir_offset,
            name_cfg(_VAL_ICA): ir_adjust,
        }
        # Under auto-range the chip's RNG bit is the state machine's choice, not the user's
        # setting, so reporting it as the Range CONFIG field would overwrite the stored preference
        # in the displayed config. The active range is an output and is reported as RangeAct.
        if not self._range_auto:
            result[name_cfg(_VAL_RNG)] = range_fs
        return result

    async def _check_divergence(self, raw: bytes) -> None:
        if self.isl.matches_shadow(raw):
            return
        await self.pr.wrn_s("Chip configuration diverged from the shadow - re-applying.", wrnno=11)
        try:
            await self.isl.configure(force=True)
        except Exception as e:
            await self.pr.err_s("Error re-applying the diverged configuration:", e, errno=34)
            return
        if self._range_auto:
            await self._switch_range(self._active_range)

    async def _snapshot_field(self, index: int, errno: int, what: str) -> int | None:
        try:
            decoded = self.isl.decode_config(await self.isl.get_config_snapshot())
        except Exception as e:
            await self.pr.err_s("Error reading", what, ":", e, errno=errno)
            return None
        if decoded is None:
            return None
        return decoded[index]

    async def _checked_cfg(self, value: "int | float", schema: "ConfigSchema", errno: int) -> "int | float | None":
        # Part G.2's numeric primitive, not a second hand-rolled cast-and-compare: the bounds come
        # from the field's own schema record, so they cannot drift from the config path's, and the
        # int<->float coercion is the identical policy (a fractional 12.5 is rejected, not cut).
        is_error, coerced = type_or_range_error(value, schema[0])
        # isinstance() guard: type_or_range_error() is typed to hand back Any, and a malformed
        # schema record is the one way something non-numeric could come back out of it - the same
        # narrow-then-validate shape asy_webserver_service.py's _put_notification() applies.
        if is_error or not isinstance(coerced, (int, float)):
            await self.pr.err_s("Error setting", schema[0][0], "- out of range:", value, errno=errno)
            return None
        return coerced

    async def _reapply_persist(self, trigger_secs: int) -> bool:
        # Called by the only two setters whose value feeds the derivation. Writing the same value
        # back is free - configure() diffs the shadow and writes nothing when nothing changed.
        try:
            await self.isl.configure(persist=self.isl.persist_for_interval(trigger_secs))
        except Exception as e:
            await self.pr.err_s("Error applying the derived transient rejection:", e, errno=24)
            return False
        return True

    def _down_thresh(self) -> float:
        # DERIVED, never configured: right after a switch up the same light reads t/r of the high
        # range, so the down point must clear t/(2r) not to chatter on noise. Against the NOMINAL
        # 26.67, not GainRatio - the factor 2 absorbs that field's whole [20, 34] band.
        return self._ar_thresh / _AR_DOWN_DIVISOR

    # -- push callbacks ----------------------------------------------------

    async def _push_trigger_secs(self, value: "int | float | str | bool | None") -> bool:
        return type(value) is int and await self.set_trigger_secs(value)

    async def _push_resolution(self, value: "int | float | str | bool | None") -> bool:
        return type(value) is int and await self.set_resolution(value)

    async def _push_range_auto(self, value: "int | float | str | bool | None") -> bool:
        return type(value) is bool and await self.set_range_auto(flag=value)

    async def _push_range(self, value: "int | float | str | bool | None") -> bool:
        return type(value) is int and await self.set_range(value)

    async def _push_autorange_thresh(self, value: "int | float | str | bool | None") -> bool:
        return type(value) is float and await self.set_autorange_thresh(value)

    async def _push_autorange_dwell(self, value: "int | float | str | bool | None") -> bool:
        return type(value) is float and await self.set_autorange_dwell(value)

    async def _push_ir_comp_offset(self, value: "int | float | str | bool | None") -> bool:
        return type(value) is int and await self.set_ir_comp_offset(value)

    async def _push_ir_comp_adjust(self, value: "int | float | str | bool | None") -> bool:
        return type(value) is int and await self.set_ir_comp_adjust(value)

    async def _push_filter_coefficient(self, value: "int | float | str | bool | None") -> bool:
        return type(value) is float and await self.set_filter_coefficient(value)

    async def _push_gain_ratio(self, value: "int | float | str | bool | None") -> bool:
        return type(value) is float and await self.set_gain_ratio(value)

    async def _push_calibrate(self, value: "int | float | str | bool | None") -> bool:
        # Reports success unconditionally once the type check passes: starting a run that later
        # finds no usable scene has not FAILED, and returning False would run
        # _recover_failed_push() on a command-only field that cannot be recovered (Part C.5.2.1).
        if type(value) is not bool:
            return False
        await self.start_calibration(flag=value)
        return True

    # -- starters ----------------------------------------------------------

    def start_asy_read(self) -> "asyncio.Task[bool]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self.read_loop())

    def start_asy_trigger(self) -> "asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._base_trigger())

    def start_timer(self) -> None:
        try:
            self.trigger_timer.init(
                period=1000,
                mode=Timer.PERIODIC,
                callback=lambda _b: self.base_trigger_event.set(),
            )
        except (OSError, MemoryError) as e:  # alarm-pool exhaustion (ENOMEM) - degrades gracefully
            # instead of crashing the caller (this sensor just never gets triggered this cycle).
            self.pr.err("Could not start timer:", e)
        # FALLING, not rising: the INT is active-low open-drain (p6). A line held low by a fault
        # produces exactly one edge and then silence - which is what the periodic path and
        # wrnno=13 exist for, not a flood. The bound method is built once, here, not per edge.
        self.irq_pin.irq(
            trigger=self.irq_pin.IRQ_FALLING,
            handler=self._on_irq,
        )

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_read, self.start_asy_trigger]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return [self.start_timer]

    def stop_timer(self) -> None:
        self.trigger_timer.deinit()  # Timer.deinit() IS real on rp2, unlike I2C/SPI (Part F.5.1)

    # -- getters -----------------------------------------------------------

    async def get_data(self) -> ISL29125:
        # Narrows to this Reader's concrete ISL29125 - see SPECIFICATION.md C.4.2's convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_data(self) -> "dict[str, dict[str, Any]]":
        # The one genuine override here: the measurement body is nested, which make_dict()'s flat
        # one-level contract cannot express. Written out explicitly rather than from the namedtuple,
        # because _asdict()/_fields need a ROM level above rp2's own.
        data = await self.get_data()
        return {
            _NAME: {
                "Lux": data.Lux,
                "RGB": {"R": data.Red, "G": data.Green, "B": data.Blue},
                "HSB": {"H": data.Hue, "S": data.Sat, "B": data.Bri},
                "CCT": data.CCT,
                "RangeAct": data.RangeAct,
                "GainMeas": data.GainMeas,
                "TS": data.TS,
            },
        }

    async def get_dict_cfg(self) -> "dict[str, dict[str, int | float | str | bool | None]]":
        # ISLCalibrate is deliberately absent from this schema argument: ConfigManager.get_dict()
        # is all-or-nothing and would KeyError on a key it never persisted.
        return await self._get_dict_cfg(
            _NAME,
            _VAL_SI + _VAL_RES + _VAL_RA + _VAL_RNG + _VAL_AR_THRESH + _VAL_AR_DWELL
            + _VAL_ICO + _VAL_ICA + _VAL_FC + _VAL_GR,
            callback=self._read_sensor_dict,
        )

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def get_resolution(self) -> int | None:
        return await self._snapshot_field(0, 15, "resolution")

    async def get_range(self) -> int | None:
        return await self._snapshot_field(1, 17, "range")

    async def get_ir_comp_offset(self) -> int | None:
        return await self._snapshot_field(2, 19, "IR compensation offset")

    async def get_ir_comp_adjust(self) -> int | None:
        return await self._snapshot_field(3, 21, "IR compensation adjust")

    # -- setters -----------------------------------------------------------

    async def set_trigger_secs(self, value: float) -> bool:
        trigger_secs = await self._checked_cfg(value, _VAL_SI, 25)
        if trigger_secs is None:
            return False
        await self.trigger_period.set_value(int(trigger_secs))
        return await self._reapply_persist(int(trigger_secs))

    async def set_resolution(self, value: int) -> bool:
        try:
            await self.isl.configure(resolution=value)
        except Exception as e:
            await self.pr.err_s("Error setting resolution:", e, errno=16)
            return False
        # A resolution change changes the cycle length, so the derived persistence changes with it.
        if not await self._reapply_persist(int(await self.trigger_period.get_value())):
            return False
        if self._range_auto:
            # The threshold registers are compared against the RAW ADC value, so they are scaled
            # to the resolution that was active when they were written - a resolution change
            # therefore has to re-arm them or the hardware fast path is left on the wrong scale.
            await self._switch_range(self._active_range)
        return True

    async def set_range(self, value: int) -> bool:
        try:
            if self._range_auto:  # stored as the preference only; the state machine owns the RNG bit
                self.isl.check_range(value)
            else:
                await self.isl.configure(range_fs=value)
                self._active_range = value
        except Exception as e:
            await self.pr.err_s("Error setting range:", e, errno=18)
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
                await self.isl.configure(threshold_interrupt=True)
            else:
                await self.isl.configure(range_fs=self._fixed_range, threshold_interrupt=False)
                self._active_range = self._fixed_range
        except Exception as e:
            await self.pr.err_s("Error applying the auto-range mode:", e, errno=38)
            return False
        self._range_auto = flag
        if flag:
            await self._switch_range(self._active_range)  # re-arm the thresholds for where we are
        return True

    async def set_autorange_thresh(self, value: float) -> bool:
        # The down point follows automatically - it is computed from this value, not stored, so
        # there is no second field to keep in step and no order in which a push can strand one.
        thresh = await self._checked_cfg(value, _VAL_AR_THRESH, 27)
        if thresh is None:
            return False
        self._ar_thresh = float(thresh)
        return True

    async def set_autorange_dwell(self, value: float) -> bool:
        dwell = await self._checked_cfg(value, _VAL_AR_DWELL, 27)
        if dwell is None:
            return False
        self._ar_dwell_s = float(dwell)
        return True

    async def set_ir_comp_offset(self, value: int) -> bool:
        try:
            await self.isl.configure(ir_offset=value)
        except Exception as e:
            await self.pr.err_s("Error setting IR compensation offset:", e, errno=20)
            return False
        return True

    async def set_ir_comp_adjust(self, value: int) -> bool:
        try:
            await self.isl.configure(ir_adjust=value)
        except Exception as e:
            await self.pr.err_s("Error setting IR compensation adjust:", e, errno=22)
            return False
        return True

    async def set_gain_ratio(self, value: float) -> bool:
        # The one and only way the applied factor changes. Unlike set_filter_coefficient() this
        # DOES store locally: _gain_correction() reads the cached attribute on every sample rather
        # than going back to cfgmgr, so the live value has to be updated here too.
        coerced = await self._checked_cfg(value, _VAL_GR, 26)
        if coerced is None:
            return False
        self._gain_ratio = float(coerced)
        return True

    async def set_filter_coefficient(self, value: float) -> bool:
        # Validates but stores NOTHING, unlike the other software knobs: _store_isl() takes the value
        # from cfgmgr on the sample it applies it to, so the persisted value IS the live one. What
        # this owns is the verdict - a False here makes _set_dict_cfg() report the field "Failed".
        return await self._checked_cfg(value, _VAL_FC, 26) is not None

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

    async def read_loop(self) -> bool:
        if not await self._init_isl():  # init sensor at startup
            return False  # break and restart if init fails
        while True:
            await self.read_event.wait()  # timer divider or INT pin, whichever came first
            self.pr.evt("sensor trigger")
            results = await self._read_isl()  # read data
            if not await self._error_check(results):  # check and count errors
                return False  # break and restart if too many errors
            await self._store_isl(results)  # store data in result buffer


class ISL29125_DeviceSession(Lockable):
    def __init__(self, i2c_device: I2CDevice) -> None:
        super().__init__()
        self.i2c_device = i2c_device


class ISL29125_I2C:
    # Protocol layer for the ISL29125. Holds a SHADOW of all three config bytes and never reads
    # them back to modify them: CONFIG1 has two writers (auto-range's RNG and the API's BITS), so
    # a read-modify-write could silently lose a concurrent change.

    def __init__(self, i2c: "I2C", address: int = 0x44) -> None:
        # 0x44 is hard-wired (p15, "1000100") - there is no address-select pin, so the parameter
        # exists only for test injection, exactly as BMP3XX_I2C's does.
        self.i2c_isl29125 = ISL29125_DeviceSession(I2CDevice(i2c, address))
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
        # Bumped whenever a shadow write raises. A COUNT, not a flag: the reader remembers which
        # value it has reconciled, so a write that fails while it is re-reading the chip is still
        # ahead afterwards and gets its own cycle instead of being cleared away unseen.
        self._write_failures = 0

    @staticmethod
    def _reject_unless(value: int, allowed: "tuple[int, ...]", what: str) -> None:
        # C.3's contract: reject loudly here rather than let encode_shadow() silently mask an
        # out-of-range value to its bit width (an IrCompAdjust of 200 would land as 8). The type
        # check is not redundant: 375.0 passes `in`, then raises inside a function contracted not to.
        if type(value) is not int or value not in allowed:
            raise ValueError(f"{what} must be one of {allowed}")

    @staticmethod
    def _reject_outside(value: int, low: int, high: int, what: str) -> None:
        # _reject_unless for a contiguous field - same type-then-value order, same reasons.
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{what} must be an integer from {low} to {high}")

    @staticmethod
    def _dark_offset(range_fs: int) -> int:
        # DDark is specified at range 0 only (p3), and that is the only place it is material: the
        # same dark current yields ~1/26.67 of a count on the high range, so subtracting a whole
        # one there would remove 0.15 lux of real signal rather than an offset.
        return _DARK_COUNTS if range_fs == _RANGE_LOW_LUX else 0

    @staticmethod
    def _decode_rgb_burst(raw: "bytes | bytearray | memoryview | None") -> "tuple[int, int, int] | None":
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
        # The one place layer 1's mixed contract is normalised: get_register_struct() returns None
        # for a malformed request but lets a real bus OSError straight through, so every read here
        # has to check for None AND sit inside a caller that expects a raise.
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            value = await i2c.get_register_struct(register, "B")
        if not isinstance(value, int):
            raise OSError(f"failed to read register {register:#x}")
        return value

    async def _write_shadow(self, first_register: int) -> None:
        payload = self.encode_shadow()[first_register - _REGISTER_CONFIG1 :]
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            # set_register_struct() takes one value but accepts bytes, so an "Ns" format is how a
            # burst write goes through the promoted bus layer. The payload is already bytes of the
            # exact length because struct.pack() truncates silently on MicroPython.
            await i2c.set_register_struct(first_register, f"{len(payload)}s", payload)

    async def get_config_snapshot(self) -> bytes:
        # One 3-byte burst under one device-session lock, returned UNDECODED: decoding here would
        # throw away mode, SYNC, CONVEN and INTSEL, which are the four things a brownout or a
        # stray write actually corrupts - defeating the divergence check this exists for.
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            raw = await i2c.get_register_struct(_REGISTER_CONFIG1, "3s")
        if not isinstance(raw, bytes) or len(raw) != _CONFIG_BURST_LEN:
            raise OSError("unexpected config snapshot read result")
        return raw

    async def get_device_id(self) -> int:
        return await self._read_byte(_REGISTER_DEVICE_ID)

    def write_failures(self) -> int:
        # How many shadow writes have raised. The chip is the authority after one, because the
        # burst may have landed in part - see configure()'s own roll-back.
        return self._write_failures

    def resolution(self) -> int:
        # The shadow's own value, for a caller that has to pair a reading with the resolution the
        # part made it under rather than with whatever is live by the time it scales it.
        return self._resolution

    async def set_thresholds(self, low_counts: int, high_counts: int | None = None) -> None:
        # Both counts arrive on the 16-bit scale and are rescaled DOWN to the active resolution: the
        # threshold registers compare against the RAW ADC value, so a 16-bit-scaled threshold would
        # never cross at 12 bits. An omitted high_counts parks the up-crossing where it cannot fire.
        twelve_bit = self._resolution == _RESOLUTION_12BIT
        shift = 4 if twelve_bit else 0
        ceiling = (1 << _RESOLUTION_12BIT) - 1 if twelve_bit else _FULL_SCALE_COUNTS
        low = max(0, min(ceiling, low_counts >> shift))
        high = ceiling if high_counts is None else max(0, min(ceiling, high_counts >> shift))
        packed = struct.pack("<HH", low, high)  # 0x04-0x07, low pair then high pair (p12, Table 14)
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            await i2c.set_register_struct(_REGISTER_THRESHOLDS, "4s", packed)

    def check_range(self, value: int) -> None:
        # The same guard configure() applies, reachable without writing: the reader stores a fixed
        # range as a preference while auto-range owns the chip's RNG bit, and that preference still
        # has to be a range the part actually has.
        self._reject_unless(value, _RANGES, "range")

    @staticmethod
    def decode_config(raw: "bytes | bytearray | memoryview | None") -> "tuple[int, int, int, int, int] | None":
        # The exact inverse of encode_shadow(), for the five hardware-backed config fields. An
        # illegal field encoding is returned as decoded, never coerced - that is information the
        # caller needs, not an error this function gets to resolve.
        if raw is None:
            return None
        try:
            if len(raw) != _CONFIG_BURST_LEN:
                return None
            config1, config2, config3 = raw[0], raw[1], raw[2]
        except (TypeError, IndexError):
            return None
        resolution = _RESOLUTION_12BIT if config1 & _CONFIG1_BITS else _RESOLUTION_16BIT
        range_fs = _RANGE_HIGH_LUX if config1 & _CONFIG1_RNG else _RANGE_LOW_LUX
        ir_offset = 1 if config2 & _CONFIG2_IRCOMP_OFFSET else 0
        ir_adjust = config2 & _CONFIG2_ALSCC_MASK
        persist: int = _PRST_SETTINGS[(config3 >> _CONFIG3_PRST_SHIFT) & 0x03]
        return resolution, range_fs, ir_offset, ir_adjust, persist

    @staticmethod
    def decode_status(status: object) -> "tuple[bool, bool, int, bool] | None":
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

    @staticmethod
    def counts_to_lux(count: int, full_scale: int, gain_correction: float) -> float:
        # p1 gives 375/65535 = 5.72 mlux and 10000/65535 = 0.1526 lux per LSB, so the LSB really is
        # FS/65535 on both ranges. gain_correction is validated where an untrusted ratio ENTERS
        # (GainRatio's schema bounds), never here - a hot-path gate would run on every sample.
        return count * (full_scale / 65535.0) * gain_correction

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

    @staticmethod
    def is_bus_fault_pattern(counts: "tuple[int, int, int] | None", status: object) -> bool:
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

    def normalise(self, raw: "tuple[int, int, int]", *, range_fs: int, resolution: int | None = None) -> "tuple[tuple[int, int, int], bool]":
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

    def matches_shadow(self, raw: "bytes | bytearray | memoryview") -> bool:
        # A masked comparison of every meaningful bit, not of five decoded fields: mode, SYNC, CONVEN
        # and INTSEL are exactly what a brownout zeroes, and decoding them away would blind this
        # check. An unreadable length answers True - a failed read is not evidence of divergence.
        if len(raw) != _CONFIG_BURST_LEN:
            return True
        shadow = self.encode_shadow()
        masks = (_CONFIG1_MASK, _CONFIG2_MASK, _CONFIG3_MASK)
        return all(raw[i] & masks[i] == shadow[i] & masks[i] for i in range(_CONFIG_BURST_LEN))

    def cycle_ms(self) -> int:
        return _CYCLE_MS_12BIT if self._resolution == _RESOLUTION_12BIT else _CYCLE_MS_16BIT

    def persist_for_interval(self, trigger_secs: int) -> int:
        # PRST is DERIVED: the largest transient rejection whose window still closes inside one
        # sample interval, so the chip always gets to raise RGBTHF before the periodic re-check would
        # decide. Configuring it by hand left the fast path structurally dead (Part C.11.1.3).
        cycle = self.cycle_ms()
        options: tuple[int, ...] = _PRST_SETTINGS  # const() is Any to mypy; same annotation decode_config() uses
        for persist in reversed(options):
            if persist * cycle < trigger_secs * 1000:
                return persist
        # Unreachable at the current schema bounds - one 16-bit cycle is 303ms against a minimum
        # 1s interval - but this is the honest degradation if either bound ever moves.
        return options[0]

    def time_to_settle_ms(self) -> int:
        return max(0, time.ticks_diff(self._settle_until_ms, time.ticks_ms()))

    def encode_shadow(self) -> bytes:
        # Every field masked to its own width before shifting, so an out-of-range value cannot
        # disturb a neighbour - the guard asy_i2c_driver.py's set_bits() applies. Masks rather than
        # validates: that belongs at the setter boundary, and a raising encoder would blur configure().
        config1 = (self._mode & _CONFIG1_MODE_MASK) | (_CONFIG1_RNG if self._range_fs == _RANGE_HIGH_LUX else 0)
        config1 |= (_CONFIG1_BITS if self._resolution == _RESOLUTION_12BIT else 0) | (_CONFIG1_SYNC if self._sync else 0)
        config2 = (_CONFIG2_IRCOMP_OFFSET if self._ir_offset else 0) | (self._ir_adjust & _CONFIG2_ALSCC_MASK)
        try:
            prst = _PRST_SETTINGS.index(self._persist)
        except ValueError:
            prst = 0
        config3 = (self._int_select & _CONFIG3_INTSEL_MASK) | (prst << _CONFIG3_PRST_SHIFT)
        config3 |= _CONFIG3_CONVEN if self._conven else 0
        return bytes((config1, config2, config3))

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
            # INTSEL selects ONE channel (p11, Table 11) and green is the one the auto-range state
            # machine watches, so "armed" and "green" are the same choice - the caller asks for the
            # behaviour and this owns the encoding.
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
            await self._write_shadow(_REGISTER_CONFIG1 if wrote_config1 else _REGISTER_CONFIG2)
        except Exception:
            # The shadow must never claim a value the part did not take: normalise() scales every
            # reading by it, so a lost resolution write would shift every later sample 16x with the
            # reads still succeeding. Rolled back, as _switch_range() declines to update its range.
            (self._mode, self._range_fs, self._resolution, self._ir_offset, self._ir_adjust, self._persist, self._int_select, self._sync, self._conven) = restore
            self._write_failures += 1
            raise
        if wrote_config1:
            # Any writer of CONFIG1 restarts the conversion (p10, Table 7), and there are three.
            # Arming the deadline in the function that does the write makes it impossible for a
            # caller to forget, and refreshes it when a config push lands mid-settle.
            self._settle_until_ms = time.ticks_add(time.ticks_ms(), _SETTLE_CYCLES * self.cycle_ms())

    async def read_counts(self) -> "tuple[int, int, int]":
        # "6s", NOT "<HHH": get_register_struct() returns unpacked[0] only, so a three-value
        # format would silently discard red and blue. The single most likely implementation
        # mistake in this driver, and it fails silently.
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            raw = await i2c.get_register_struct(_REGISTER_DATA, "6s")
        counts = self._decode_rgb_burst(raw if isinstance(raw, bytes) else None)
        if counts is None:
            raise OSError("unexpected RGB data burst read result")
        return counts

    async def read_status(self) -> int:
        # DESTRUCTIVE: the read clears RGBTHF and releases the INT pin (p11/p12), so it happens
        # exactly once per read cycle and nothing else in this driver may read 0x08 "just to
        # check" - a second reader would silently consume another consumer's interrupt state.
        return await self._read_byte(_REGISTER_STATUS)

    async def verify_device_id(self) -> None:
        # Raising rather than returning a verdict, so setup() fails loudly on the wrong part and
        # the reader's own all-ones bus-fault confirmation can just catch it.
        device_id = await self.get_device_id()
        if device_id != _DEVICE_ID:
            raise RuntimeError(f"Failed to find ISL29125! Device ID {hex(device_id)}")

    async def clear_brownout(self) -> None:
        # Table 15 marks 0x08 "RO", but p12's own BOUTF text requires an I2C write to clear it -
        # the marking is a datasheet defect, not a prohibition.
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            await i2c.set_register_struct(_REGISTER_STATUS, "B", 0x00)

    async def setup(self) -> None:
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            await i2c.setup()
        await self.verify_device_id()
        await self.reset()
        # BOUTF is high at power-up (p12). Kept even though the 0x46 reset and any status read both
        # clear it on real silicon (Part C.11.1.1): it is the one clear the datasheet promises, costs
        # one transaction per init, and makes the post-setup state mechanism-independent.
        await self.clear_brownout()
        # SYNC and CONVEN are written explicitly rather than left at their reset default, so neither
        # can flip silently later: SYNC = 1 turns INT into an INPUT and inverts the whole interrupt
        # path, and CONVEN would mux conversion-done onto the pin the thresholds need.
        await self.configure(mode=_MODE_RGB, threshold_interrupt=True, sync=0, conven=0, force=True)

    async def reset(self) -> None:
        # The datasheet specifies no post-reset settle, so the verify read IS the settle. CONFIG1-3
        # only, NOT status the way SparkFun's reset() does: reading 0x08 would consume a destructive
        # read outside the one-per-cycle invariant read_status() depends on (C.11.1.1).
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            await i2c.set_register_struct(_REGISTER_DEVICE_ID, "B", _CMD_RESET)
            config = await i2c.get_register_struct(_REGISTER_CONFIG1, "3s")
        if not isinstance(config, bytes) or len(config) != _CONFIG_BURST_LEN:
            raise OSError("failed to read the config registers back after reset")
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
