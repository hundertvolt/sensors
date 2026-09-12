# SPDX-FileCopyrightText: Copyright (c) 2023 Jose D. Montoya (original MicroPython_ISL29125) -
# restructured/rewritten for asyncio + this project's driver shape, see THIRD_PARTY_LICENSES.md.
# SPDX-License-Identifier: MIT

"""Renesas/Intersil ISL29125 RGB colour sensor driver: lux, sensor RGB/HSB, relative CCT, and a self-calibrating auto-range state machine driven by the chip's own threshold interrupt.
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
from config_manager import name_cfg
from crc_checks import CRC32

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any

    from asy_fram_manager import AsyFramManager, AsyFramTimestampedChunk
    from asy_i2c_driver import I2C
    from print_log import ErrorLog


_DEVICE_ID = const(0x7D)  # datasheet p9, Table 2
_CMD_RESET = const(0x46)  # written to 0x00: "the device will reset all registers to their default states" (p9)

_REGISTER_DEVICE_ID = const(0x00)
_REGISTER_CONFIG1 = const(0x01)
_REGISTER_CONFIG2 = const(0x02)
_REGISTER_CONFIG3 = const(0x03)
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
# none of these is one (see ISL29125_PROMOTION_PLAN.md section 8.3's own classification table).
_DARK_COUNTS = const(1)  # DDark typ 1 / max 5 counts at range 0 (p3, Electrical Specifications)
_CCT_FLOOR_COUNTS = const(64)  # ~13x the worst-case dark count: below it a 5-count additive error
# moves a channel ratio by more than ~8%, and chromaticity noise grows far faster than hue noise.
_GAIN_RATIO_NOMINAL = const(26.666666666666668)  # 10000/375 - the ratio a fresh unit starts from
_GAIN_RATIO_MIN = const(20.0)  # a plausibility gate around nominal, applied where an untrusted
_GAIN_RATIO_MAX = const(34.0)  # value enters (on load and on learn), never in the hot path
_GAIN_EMA_COEFF = const(0.1)  # the learning filter's own time constant
_GAIN_LEARN_PERIOD_S = const(3600)  # the ratio is a device constant, so re-measuring it hourly is
# generous; each measurement costs one extra range switch and two settle windows.
_AR_CROSS_FIELD_DIVISOR = const(53.333333333333336)  # 2 x the range ratio - the no-chatter margin
# AutoRangeDown must clear: d <= u/(2r), see ISL29125_PROMOTION_PLAN.md section 7.6.
_SETTLE_WAIT_MAX_ROUNDS = const(2)  # one extra cycle past the deadline, so a stream of concurrent
# config writes can extend the settle but can never starve the read loop indefinitely.
_PERIODIC_ONLY_WARN_AT = const(5)  # consecutive periodic-path switches with no preceding interrupt

_MIN_TRIGGER_SECS = const(1)
_MAX_TRIGGER_SECS = const(3600)
_MIN_SETTLE_CYCLES = const(1)
_MAX_SETTLE_CYCLES = const(10)
_MIN_DWELL_S = const(0.0)
_MAX_DWELL_S = const(300.0)
_MIN_FILT_COEFF = const(-1.0)
_MAX_FILT_COEFF = const(1.0)
_MIN_AR_UP = const(50.0)
_MAX_AR_UP = const(95.0)
_MIN_AR_DOWN = const(0.2)
_MAX_AR_DOWN = const(3.0)

_VAL_SI = const((("SampleInterv", "int", 1, _MIN_TRIGGER_SECS, _MAX_TRIGGER_SECS, None),))
# Resolution/Range/AutoRangePersist/IrCompOffset are genuine discrete allowed-value sets, not
# continuous ranges - the 6th-slot `special` shape asy_bmp3xx_driver.py's own _VAL_POV established.
_VAL_RES = const((("Resolution", "int", 16, None, None, _RESOLUTIONS),))
_VAL_RA = const((("RangeAuto", "bool", True, None, None, None),))
_VAL_RNG = const((("Range", "int", 10000, None, None, _RANGES),))
_VAL_AR_UP = const((("AutoRangeUp", "float", 85.0, _MIN_AR_UP, _MAX_AR_UP, None),))
_VAL_AR_DOWN = const((("AutoRangeDown", "float", 1.5, _MIN_AR_DOWN, _MAX_AR_DOWN, None),))
_VAL_AR_SETTLE = const((("AutoRangeSettle", "int", 1, _MIN_SETTLE_CYCLES, _MAX_SETTLE_CYCLES, None),))
_VAL_AR_PERSIST = const((("AutoRangePersist", "int", 4, None, None, _PRST_SETTINGS),))
_VAL_AR_DWELL = const((("AutoRangeDwell", "float", 10.0, _MIN_DWELL_S, _MAX_DWELL_S, None),))
_VAL_ICO = const((("IrCompOffset", "int", 0, None, None, _IR_OFFSETS),))
_VAL_ICA = const((("IrCompAdjust", "int", 40, 0, 63, None),))
_VAL_FC = const((("FiltCoeff", "float", -1.0, _MIN_FILT_COEFF, _MAX_FILT_COEFF, None),))
# Command-only trigger, not a persisted config value - the schema's "special-alone" shape
# (def=None + a non-tuple special, SPECIFICATION.md Part C.5.2.1). Deliberately excluded from
# get_dict_cfg()'s own schema argument and from the bool batch below: this key is never in
# ConfigManager's _cache, so either would fail at runtime rather than at type-check time.
_VAL_RESETCAL = const((("ISLResetCal", "bool", None, None, None, True),))

_N_INT_CFG = const(7)  # SampleInterv + Resolution + Range + AutoRangeSettle + AutoRangePersist + IrCompOffset + IrCompAdjust
_N_FLOAT_CFG = const(4)  # AutoRangeUp + AutoRangeDown + AutoRangeDwell + FiltCoeff
_N_BOOL_CFG = const(1)  # RangeAuto ALONE - ISLResetCal is command-only (see _VAL_RESETCAL above)

_NAME = const("ISL29125")
# Kept as a literal tuple inline (not `_FIELDS` below) because mypy's namedtuple plugin can only
# infer field names from a literal at the call site, not through a variable indirection.
ISL29125 = namedtuple("ISL29125", ("Lux", "Red", "Green", "Blue", "Hue", "Sat", "Bri", "CCT", "RangeAct", "TS"))
_FIELDS = const(("Lux", "Red", "Green", "Blue", "Hue", "Sat", "Bri", "CCT", "RangeAct", "TS"))  # kept in sync with ISL29125's own fields above
if TYPE_CHECKING:
    # Narrow on purpose - CCT is legitimately None in a dark room, and base_classes._error_check()
    # counts a failed read when ANY element is None, so the wide namedtuple must never reach it.
    # The 4th element is the full-scale range the sample was TAKEN on: a cycle ending in a switch
    # still reports a sample acquired on the old gain, so _store_isl() must not read the reader's
    # current range back.
    ISLResults = tuple[int | None, int | None, int | None, int | None, int | None]


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


def _normalise_triple(
    green: int, red: int, blue: int, *, resolution_bits: int, dark_offset: int,
) -> "tuple[int, int, int]":
    # Steps 2 and 3 of the normalisation chain: put 12- and 16-bit readings on one 0-65535 scale,
    # then remove the additive dark offset. An unknown resolution falls back to "no shift", the
    # conservative direction - shifting when you should not inflates every reading 16x, while not
    # shifting when you should only under-reports.
    shift = 4 if resolution_bits == _RESOLUTION_12BIT else 0
    scaled = [max(0, min(_FULL_SCALE_COUNTS, (value << shift) - dark_offset)) for value in (green, red, blue)]
    return scaled[0], scaled[1], scaled[2]


def _counts_to_lux(count: int, full_scale: int, gain_correction: float) -> float:
    # p1's feature list gives 375/65535 = 5.72 mlux and 10000/65535 = 0.1526 lux per LSB, matching
    # the datasheet's own stated figures exactly - the LSB really is FS/65535 on both ranges.
    # gain_correction is validated where an untrusted ratio ENTERS (_load_gain_ratio), never here:
    # a plausibility gate in the hot path would run every sample for a value that changes daily.
    return count * (full_scale / 65535.0) * gain_correction


def _fraction_to_counts(fraction: float) -> int:
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


def _is_bus_fault_pattern(counts: "tuple[int, int, int] | None", status: object) -> bool:
    # A dead bus reads all-ones, and the community failure reports for this part are exactly that.
    # Taken on the RAW counts, before normalisation: the pattern is a property of the wire, not of
    # the scaled value, which is what makes the 12-bit case exact (a real 12-bit reading cannot
    # exceed 4095, so at 12 bits this has no false-positive mode at all).
    if counts is None or len(counts) != _CHANNELS:
        return False
    if not all(count == _FULL_SCALE_COUNTS for count in counts):
        return False
    # 0x08's B7:B6 and B3 are reserved and read zero (p12, Table 15), so any of them set is
    # impossible on a working part - and a non-int is layer 1 failing to produce a byte at all.
    return type(status) is not int or bool(status & _STATUS_RESERVED_MASK)


def _is_saturated(green: int, red: int, blue: int, *, resolution_bits: int) -> bool:
    # ANY channel at its RAW maximum: the output is a colour triple, so a clipped red with green
    # at 40% of full scale still destroys Hue, Sat and CCT. Raw and before normalisation, because
    # a post-normalisation `== 65535` test is simply wrong at 12 bits, where 4095 << 4 is 65520
    # and the auto-range fast path would be silently dead.
    maximum = (1 << resolution_bits) - 1 if resolution_bits == _RESOLUTION_12BIT else _FULL_SCALE_COUNTS
    return green >= maximum or red >= maximum or blue >= maximum


def _decode_config_bytes(raw: "bytes | bytearray | memoryview | None") -> "tuple[int, int, int, int, int] | None":
    # The exact inverse of ISL29125_I2C._encode_shadow(), for the five hardware-backed config
    # fields. An illegal field encoding is returned as decoded, never coerced - that is
    # information the caller needs, not an error this function gets to resolve.
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
        fram_ntp_callback: "Callable[[], Coroutine[Any, Any, bool]] | None" = None,
        history_length: int = 10,
        debug: int | None = None,
    ) -> None:
        super().__init__(
            ISL29125(None, None, None, None, None, None, None, None, None, None),
            max_module_error,
            _NAME,
            _VAL_SI + _VAL_RES + _VAL_RA + _VAL_RNG + _VAL_AR_UP + _VAL_AR_DOWN + _VAL_AR_SETTLE
            + _VAL_AR_PERSIST + _VAL_AR_DWELL + _VAL_ICO + _VAL_ICA + _VAL_FC + _VAL_RESETCAL,
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
        # and the pin IRQ - which is safe and is what makes the interrupt the fast path and the
        # timer the guaranteed one: a set with no waiter is remembered, so an INT arriving
        # mid-cycle coalesces into exactly one extra cycle rather than being lost or queued.
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
        self._ar_up = 85.0
        self._ar_down = 1.5
        self._ar_dwell_s = 10.0
        self._last_switch_ms = time.ticks_ms()
        self._brownout_seen = False
        self._periodic_only_switches = 0
        self._gain_ratio = _GAIN_RATIO_NOMINAL
        self._gain_ratio_ts: int | None = None
        self._gain_learn_ms = time.ticks_ms()
        self._filtered: list[float | None] = [None, None, None]  # green, red, blue, in lux
        if fram is None or fram_ntp_callback is None:
            self.ts_storage: AsyFramTimestampedChunk | None = None
        else:
            try:  # broad on purpose, matching asy_sgp40_driver.py's own FRAM-allocation guard -
                # __init__ runs before any task supervisor exists to catch an escaped exception.
                self.ts_storage = fram.get_timestamped_chunk(4, fram_ntp_callback, crc=CRC32())
            except Exception:
                self.ts_storage = None
            if self.ts_storage is None:
                self.pr.err("FRAM calibration storage allocation failed!")
        self._push_callbacks[name_cfg(_VAL_SI)] = self._push_trigger_secs
        self._push_callbacks[name_cfg(_VAL_RES)] = self._push_resolution
        self._push_callbacks[name_cfg(_VAL_RA)] = self._push_range_auto
        self._push_callbacks[name_cfg(_VAL_RNG)] = self._push_range
        self._push_callbacks[name_cfg(_VAL_AR_UP)] = self._push_autorange_up
        self._push_callbacks[name_cfg(_VAL_AR_DOWN)] = self._push_autorange_down
        self._push_callbacks[name_cfg(_VAL_AR_SETTLE)] = self._push_autorange_settle
        self._push_callbacks[name_cfg(_VAL_AR_PERSIST)] = self._push_autorange_persist
        self._push_callbacks[name_cfg(_VAL_AR_DWELL)] = self._push_autorange_dwell
        self._push_callbacks[name_cfg(_VAL_ICO)] = self._push_ir_comp_offset
        self._push_callbacks[name_cfg(_VAL_ICA)] = self._push_ir_comp_adjust
        self._push_callbacks[name_cfg(_VAL_FC)] = self._push_filter_coefficient
        self._push_callbacks[name_cfg(_VAL_RESETCAL)] = self._push_reset_gain_calibration
        # Live read-back for _set_dict_cfg's failed-push recovery chain (SPECIFICATION.md C.5.2).
        # Only the five hardware-backed fields have one; the software knobs (the timer divider,
        # the four auto-range policy numbers, the output filter) have nothing to read back, and
        # ISLResetCal is command-only so _recover_failed_push() skips it by design.
        self._get_callbacks[name_cfg(_VAL_RES)] = self.get_resolution
        self._get_callbacks[name_cfg(_VAL_RNG)] = self.get_range
        self._get_callbacks[name_cfg(_VAL_ICO)] = self.get_ir_comp_offset
        self._get_callbacks[name_cfg(_VAL_ICA)] = self.get_ir_comp_adjust
        self._get_callbacks[name_cfg(_VAL_AR_PERSIST)] = self.get_autorange_persist

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

        int_values = await self.cfgmgr.get_int_values(
            _VAL_SI + _VAL_RES + _VAL_RNG + _VAL_AR_SETTLE + _VAL_AR_PERSIST + _VAL_ICO + _VAL_ICA,
        )
        float_values = await self.cfgmgr.get_float_values(_VAL_AR_UP + _VAL_AR_DOWN + _VAL_AR_DWELL + _VAL_FC)
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
        self._ar_up, self._ar_down, self._ar_dwell_s = float_values[0], float_values[1], float_values[2]
        self.isl.settle_cycles = int_values[3]
        self._range_auto = bool_values[0]
        self._fixed_range = int_values[2]
        self._active_range = _RANGE_HIGH_LUX if self._range_auto else int_values[2]
        try:  # one burst, applying resolution, range, IR compensation and persistence together
            await self.isl.configure(
                resolution=int_values[1],
                range_fs=self._active_range,
                persist=int_values[4],
                ir_offset=int_values[5],
                ir_adjust=int_values[6],
                int_select=_INTSEL_GREEN if self._range_auto else _INTSEL_NONE,
            )
        except Exception as e:
            await self.pr.err_s("Error setting config data:", e, errno=13)
            return False  # error

        await self._load_gain_ratio()  # never fails the init - degrades to the nominal ratio
        if self._range_auto:
            # Easy to miss: without this the part boots with its power-on thresholds and the
            # interrupt path is dead until the first switch would have happened anyway.
            await self._switch_range(self._active_range)
        self.pr.one("initialized")
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

    async def _base_trigger(self) -> None:
        self.trigger_counter = 0
        while True:
            await self.base_trigger_event.wait()
            self.trigger_counter += 1
            if self.trigger_counter >= await self.trigger_period.get_value():
                self.read_event.set()
                self.trigger_counter = 0

    # -- read path ---------------------------------------------------------

    async def _read_isl(self) -> "ISLResults":
        timestamp: int | None = None
        green: int | None = None
        red: int | None = None
        blue: int | None = None
        sample_range: int | None = None
        try:
            timestamp = time.mktime(time.gmtime())
            if self.isl.time_to_settle_ms() > 0:
                await self._settle_wait()
            try:
                status = await self.isl.read_status()
            except Exception as e:  # distinguishable from a data-read failure, and not re-raised
                await self.pr.err_s("Status read failed:", e, errno=31)
                return None, None, None, None, None
            brownout, threshold_fired = self._handle_status(status)
            if not brownout:
                self._brownout_seen = False
            else:
                # The chip went through power-down, so its whole configuration is 0x00 and the
                # data registers hold nothing measured - there is no sample to report this cycle.
                await self._recover_brownout()
                return None, None, None, None, None

            raw = await self.isl.read_counts()
            if _is_bus_fault_pattern(raw, status) and not await self._device_id_answers():
                await self.pr.err_s("All-ones data with an implausible status byte, confirmed by a failed device-ID re-read", errno=32)
                return None, None, None, None, None

            resolution = self.isl.resolution_bits()
            saturated = _is_saturated(raw[0], raw[1], raw[2], resolution_bits=resolution)
            counts = _normalise_triple(raw[0], raw[1], raw[2], resolution_bits=resolution, dark_offset=self._dark_offset())
            # Captured BEFORE the switch below, which updates self._active_range: this sample was
            # taken on the old gain and must be scaled by it, once per switch, in the direction
            # that would otherwise make the error largest.
            sample_range = self._active_range
            target = self._evaluate_range(counts, saturated=saturated)
            if target is not None:
                await self._note_decision_source(threshold_fired=threshold_fired)
                self.pr.evt("range switch", sample_range, "->", target, "peak", max(counts))
                await self._switch_range(target)
            elif saturated and sample_range == _RANGE_HIGH_LUX:
                await self.pr.wrn_s("Saturated on the high range - the scene exceeds the part.", wrnno=14)
            await self._learn_gain_ratio(counts[0])
            self.pr.all("read")
            green, red, blue = counts
        except Exception as e:
            green = red = blue = sample_range = timestamp = None
            await self.pr.err_s("Read failed:", e, errno=11)
        return green, red, blue, sample_range, timestamp

    def _dark_offset(self) -> int:
        # DDark is specified at range 0 only (p3), and that is the only place it is material: the
        # same dark current yields ~1/26.67 of a count on the high range, so subtracting a whole
        # one there would remove 0.15 lux of real signal rather than an offset.
        return _DARK_COUNTS if self._active_range == _RANGE_LOW_LUX else 0

    async def _device_id_answers(self) -> bool:
        # One extra transaction, spent only when the all-ones heuristic already fired - so a false
        # positive costs one wasted read and never decides the verdict on its own.
        try:
            return await self.isl.get_device_id() == _DEVICE_ID
        except Exception:
            return False

    async def _note_decision_source(self, *, threshold_fired: bool) -> None:
        # Requirement 17's silent-failure detector: the periodic evaluation is the safety net, and
        # this is what makes it visible when the net is carrying the load on its own.
        if threshold_fired:
            self._periodic_only_switches = 0
            return
        self._periodic_only_switches += 1
        if self._periodic_only_switches >= _PERIODIC_ONLY_WARN_AT:
            await self.pr.wrn_s("Range decided by the periodic path only - the interrupt may be dead.", wrnno=15)
            self._periodic_only_switches = 0

    def _handle_status(self, status: object) -> "tuple[bool, bool]":
        if type(status) is not int:  # layer 1 failed to produce a byte - the read path decides
            return False, False
        self.pr.all(
            "status", status,
            "RGBCF", (status >> _STATUS_RGBCF_SHIFT) & 0x03,
            "CONVENF", bool(status & _STATUS_CONVENF),
        )
        return bool(status & _STATUS_BOUTF), bool(status & _STATUS_RGBTHF)

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

    async def _store_isl(self, results: "ISLResults") -> None:
        green, red, blue, sample_range, timestamp = results
        if green is None or red is None or blue is None or sample_range is None or timestamp is None:
            return  # don't run on invalid data

        cfg_values = await self.cfgmgr.get_float_values(_VAL_AR_UP + _VAL_AR_DOWN + _VAL_AR_DWELL + _VAL_FC)
        if cfg_values is None or len(cfg_values) != _N_FLOAT_CFG:
            cfg_values = [85.0, 1.5, 10.0, -1.0]
            await self.pr.err_s("Error reading config data!", errno=14)
        filter_coefficient = cfg_values[3]

        correction = self._gain_correction(sample_range)
        lux = [_counts_to_lux(count, sample_range, correction) for count in (green, red, blue)]
        # The filter runs on the three absolute lux channels, not on the derived outputs, so Lux,
        # RGB, HSB and CCT all stay mutually consistent and there is exactly one filter state.
        for index, value in enumerate(lux):
            filtered = math_helpers.ema_step(self._filtered[index], value, filter_coefficient)
            if filtered is not None:
                self._filtered[index] = filtered
                lux[index] = filtered

        # The denominator is the whole auto-range SPAN (10000 lux), not the active range: dividing
        # by the active full scale would step every normalised output by the gain ratio at each
        # switch, which is exactly the discontinuity auto-range exists to remove. With RangeAuto
        # off there is no span to be continuous across, so the selected fixed range is right.
        span = float(_RANGE_HIGH_LUX if self._range_auto else self._fixed_range)
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
        # The LOW range is the reference, so the learned ratio only ever corrects the high one -
        # correcting both would make the absolute scale drift with the calibration.
        # learned/nominal, not its reciprocal: a unit whose real high-range full scale exceeds the
        # nominal 10000 produces FEWER counts for the same light, so the reported lux needs
        # scaling UP by exactly that excess.
        if range_fs != _RANGE_HIGH_LUX:
            return 1.0
        return self._gain_ratio / _GAIN_RATIO_NOMINAL

    # -- auto-range --------------------------------------------------------

    def _evaluate_range(self, counts: "tuple[int, int, int]", *, saturated: bool) -> int | None:
        # Decides on the PEAK of the three channels in both directions. The hardware path is
        # green-only because INTSEL has one channel, but the software path has all three in hand
        # and the output is a colour triple. Using the peak only for "up" would oscillate: a
        # red-dominant scene switches up, green lands below the down threshold, the dwell expires,
        # and it switches back.
        if not self._range_auto:
            return None
        if self.isl.time_to_settle_ms() > 0:
            return None  # a conversion restarted by the last switch has not completed yet
        peak = max(counts)
        if self._active_range == _RANGE_LOW_LUX:
            if saturated or peak >= _fraction_to_counts(self._ar_up):
                return _RANGE_HIGH_LUX
            return None
        if peak > _fraction_to_counts(self._ar_down):
            return None
        # React fast to bright, slowly to dark: PRST is one field applied to both crossings and so
        # cannot be asymmetric, which is what AutoRangeDwell is for. ticks_diff, never subtraction.
        if time.ticks_diff(time.ticks_ms(), self._last_switch_ms) < int(self._ar_dwell_s * 1000):
            self.pr.all("switch down suppressed by AutoRangeDwell")
            return None
        return _RANGE_LOW_LUX

    async def _switch_range(self, target_range: int) -> bool:
        # Only ONE threshold is live per range, because the two switch points sit on different
        # gain scales: on the low range only an up-crossing can matter, on the high range only a
        # down-crossing. The counts are scaled to the ACTIVE resolution - the threshold registers
        # are compared against the raw ADC value, so a 16-bit-scaled threshold would never be
        # crossed at 12 bits and the hardware fast path would be silently dead there.
        bits = self.isl.resolution_bits()
        shift = 16 - bits
        if target_range == _RANGE_LOW_LUX:
            low_counts, high_counts = 0, _fraction_to_counts(self._ar_up) >> shift
        else:
            low_counts, high_counts = _fraction_to_counts(self._ar_down) >> shift, (1 << bits) - 1
        try:  # thresholds FIRST: the other order leaves a window where the new gain is live
            await self.isl.set_thresholds(low_counts, high_counts)  # against the old thresholds
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
        # Bounded rather than an open `while pending`: a stream of concurrent config writes can
        # push the deadline out, and past this bound the driver proceeds and lets the reading
        # stand - a possibly-stale sample beats a starved read loop, and the leaky bucket catches
        # a persistent problem anyway.
        for _ in range(_SETTLE_WAIT_MAX_ROUNDS):
            remaining = self.isl.time_to_settle_ms()
            if remaining <= 0:
                return
            self.pr.all("settle discard", remaining)
            await asyncio.sleep_ms(remaining)

    # -- gain-ratio calibration -------------------------------------------

    async def _learn_gain_ratio(self, green_counts: int) -> None:
        # 26.67 is nominal; the real per-device ratio differs, and that error IS the visible step
        # at each transition. Measured as a PAIR of readings on the two ranges within one quiet
        # period, because the dominant error source is the scene changing between them.
        if not self._range_auto or self.isl.time_to_settle_ms() > 0:
            return
        if time.ticks_diff(time.ticks_ms(), self._gain_learn_ms) < _GAIN_LEARN_PERIOD_S * 1000:
            return
        if time.ticks_diff(time.ticks_ms(), self._last_switch_ms) < int(self._ar_dwell_s * 1000):
            return
        # Only inside the overlap band - bright enough to be well clear of the dark floor on the
        # low range, dim enough not to clip it.
        if not _fraction_to_counts(self._ar_down) < green_counts < _fraction_to_counts(self._ar_up):
            return
        here = self._active_range
        there = _RANGE_LOW_LUX if here == _RANGE_HIGH_LUX else _RANGE_HIGH_LUX
        self._gain_learn_ms = time.ticks_ms()
        if not await self._switch_range(there):
            return
        try:
            await self._settle_wait()
            raw = await self.isl.read_counts()
        except Exception as e:
            await self.pr.err_s("Paired gain-ratio reading failed:", e, errno=11)
            await self._switch_range(here)
            return
        paired = _normalise_triple(
            raw[0], raw[1], raw[2], resolution_bits=self.isl.resolution_bits(), dark_offset=self._dark_offset(),
        )[0]
        await self._switch_range(here)
        low_counts, high_counts = (green_counts, paired) if here == _RANGE_LOW_LUX else (paired, green_counts)
        if high_counts <= 0:
            return
        sample_ratio = low_counts / high_counts
        if not _GAIN_RATIO_MIN <= sample_ratio <= _GAIN_RATIO_MAX:
            await self.pr.wrn_s("Learned gain ratio implausible, keeping the previous one:", sample_ratio, wrnno=13)
            return
        updated = math_helpers.ema_step(self._gain_ratio, sample_ratio, _GAIN_EMA_COEFF)
        if updated is None:
            return
        self.pr.evt("gain ratio", self._gain_ratio, "->", updated)
        self._gain_ratio = updated
        await self._persist_gain_ratio()

    async def _load_gain_ratio(self) -> None:
        # Every failure here degrades to "use the nominal ratio", never to a failed init and never
        # to a raise. The plausibility gate is applied on LOAD, not only on learn: this is the
        # boundary where an untrusted value enters (see _counts_to_lux's own note).
        if self.ts_storage is None:
            await self.pr.wrn_s("No calibration storage - using the nominal gain ratio.", wrnno=11)
            return
        buf = self.ts_storage.get_buffer()
        try:
            valid, stored_ts, age = await self.ts_storage.read_into(buf)
        except Exception as e:
            await self.pr.err_s("Error reading the gain-ratio backup:", e, errno=35)
            return
        data = buf.get_data_buf()
        if not valid or data is None:
            await self.pr.wrn_s("No gain-ratio backup found!", wrnno=11)
            return
        try:  # single precision: MicroPython's float is 4 bytes on rp2, so "<d" would waste half
            ratio = float(struct.unpack_from("<f", data, 0)[0])  # the chunk and misstate the precision
        except Exception:
            await self.pr.wrn_s("Stored gain ratio is unreadable, using nominal.", wrnno=12)
            return
        if not _GAIN_RATIO_MIN <= ratio <= _GAIN_RATIO_MAX:
            await self.pr.wrn_s("Stored gain ratio is implausible, using nominal:", ratio, wrnno=13)
            return
        if stored_ts is None:
            await self.pr.wrn_s("Gain ratio restored without a timestamp.", wrnno=12)
        self._gain_ratio = ratio
        self._gain_ratio_ts = stored_ts
        self.pr.one("Gain ratio restored:", ratio, "age", age)

    async def _persist_gain_ratio(self) -> None:
        if self.ts_storage is None:
            return
        buf = self.ts_storage.get_buffer()
        data = buf.get_data_buf()
        if data is None:
            return
        try:
            struct.pack_into("<f", data, 0, self._gain_ratio)
            ntp_synced, written_ts, ok = await self.ts_storage.write_into(buf)
        except Exception as e:
            await self.pr.err_s("Error writing the gain-ratio backup:", e, errno=36)
            return
        if not ok:
            await self.pr.err_s("Write error during the gain-ratio backup!", errno=36)
            return
        self._gain_ratio_ts = written_ts if ntp_synced else None

    async def _clear_gain_ratio(self) -> bool:
        if self.ts_storage is None:
            return True  # nothing allocated to clear - vacuously satisfied, not a failure
        try:
            return await self.ts_storage.clear()
        except Exception as e:
            await self.pr.err_s("Error clearing the gain-ratio backup:", e, errno=37)
            return False

    # -- live config read-back --------------------------------------------

    async def _read_sensor_dict(self) -> "dict[str, int | float | str | bool | None]":
        # Reads the real registers rather than reporting the shadow, because this is the only
        # thing in the driver that can detect the two having diverged. Table 7 (p10) makes only a
        # WRITE to 0x01 restart the conversion, so a read-only snapshot costs one transaction and
        # nothing else - section 8.7's shadow rule is about the read-modify-write hazard, which a
        # read-only snapshot does not create.
        try:
            raw = await self.isl.get_config_snapshot()
        except Exception as e:
            await self.pr.err_s("Error reading config from sensor:", e, errno=28)
            return dict.fromkeys(
                (name_cfg(_VAL_RES), name_cfg(_VAL_RNG), name_cfg(_VAL_ICO), name_cfg(_VAL_ICA), name_cfg(_VAL_AR_PERSIST)),
                None,
            )
        await self._check_divergence(raw)
        decoded = _decode_config_bytes(raw)
        if decoded is None:
            return {}
        resolution, range_fs, ir_offset, ir_adjust, persist = decoded
        result: dict[str, int | float | str | bool | None] = {
            name_cfg(_VAL_RES): resolution,
            name_cfg(_VAL_ICO): ir_offset,
            name_cfg(_VAL_ICA): ir_adjust,
            name_cfg(_VAL_AR_PERSIST): persist,
        }
        # Under auto-range the chip's RNG bit is the state machine's choice, not the user's
        # setting, so reporting it as the Range CONFIG field would overwrite the stored preference
        # in the displayed config. The active range is an output and is reported as RangeAct.
        if not self._range_auto:
            result[name_cfg(_VAL_RNG)] = range_fs
        return result

    async def _check_divergence(self, raw: bytes) -> None:
        # A masked comparison of every meaningful bit, not of five decoded fields: mode, SYNC,
        # CONVEN and INTSEL are exactly what a brownout or a stray write zeroes, and decoding them
        # away first is what would make this check blind to the thing it exists for.
        shadow = self.isl.encode_shadow()
        if len(raw) != _CONFIG_BURST_LEN:
            return
        masks = (_CONFIG1_MASK, _CONFIG2_MASK, _CONFIG3_MASK)
        if all(raw[i] & masks[i] == shadow[i] & masks[i] for i in range(_CONFIG_BURST_LEN)):
            return
        await self.pr.wrn_s("Chip configuration diverged from the shadow - re-applying.", wrnno=10)
        try:
            await self.isl.configure(force=True)
        except Exception as e:
            await self.pr.err_s("Error re-applying the diverged configuration:", e, errno=34)
            return
        if self._range_auto:
            await self._switch_range(self._active_range)

    # -- push callbacks ----------------------------------------------------

    async def _push_trigger_secs(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not int:
            return False
        return await self.set_trigger_secs(value)

    async def _push_resolution(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not int:
            return False
        return await self.set_resolution(value)

    async def _push_range_auto(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not bool:
            return False
        return await self.set_range_auto(flag=value)

    async def _push_range(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not int:
            return False
        return await self.set_range(value)

    async def _push_autorange_up(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not float:
            return False
        return await self.set_autorange_up(value)

    async def _push_autorange_down(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not float:
            return False
        return await self.set_autorange_down(value)

    async def _push_autorange_settle(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not int:
            return False
        return await self.set_autorange_settle(value)

    async def _push_autorange_persist(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not int:
            return False
        return await self.set_autorange_persist(value)

    async def _push_autorange_dwell(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not float:
            return False
        return await self.set_autorange_dwell(value)

    async def _push_ir_comp_offset(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not int:
            return False
        return await self.set_ir_comp_offset(value)

    async def _push_ir_comp_adjust(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not int:
            return False
        return await self.set_ir_comp_adjust(value)

    async def _push_filter_coefficient(self, value: "int | float | str | bool | None") -> bool:
        if type(value) is not float:
            return False
        return await self.set_filter_coefficient(value)

    async def _push_reset_gain_calibration(self, value: "int | float | str | bool | None") -> bool:
        # Reports success unconditionally once the type check passes: a recalibration that finds
        # nothing to discard has not FAILED, and returning False would run _recover_failed_push()
        # on a command-only field that cannot be recovered (SPECIFICATION.md Part C.5.2.1).
        if type(value) is not bool:
            return False
        await self.reset_gain_calibration(flag=value)
        return True

    # -- setters -----------------------------------------------------------

    async def set_trigger_secs(self, value: float) -> bool:
        try:
            # int(float('inf'))/int(float('-inf')) raise OverflowError, not ValueError - confirmed
            # against the real MicroPython Unix-port interpreter.
            trigger_secs = int(value)
            if not (_MIN_TRIGGER_SECS <= trigger_secs <= _MAX_TRIGGER_SECS):
                raise ValueError(f"trigger interval must be between {_MIN_TRIGGER_SECS} and {_MAX_TRIGGER_SECS} seconds")
        except (TypeError, ValueError, OverflowError) as e:
            await self.pr.err_s("Error setting trigger interval:", e, errno=25)
            return False
        await self.trigger_period.set_value(trigger_secs)
        return True

    async def set_resolution(self, value: int) -> bool:
        try:
            await self.isl.configure(resolution=value)
        except Exception as e:
            await self.pr.err_s("Error setting resolution:", e, errno=16)
            return False
        if self._range_auto:
            # The threshold registers are compared against the RAW ADC value, so they are scaled
            # to the resolution that was active when they were written - a resolution change
            # therefore has to re-arm them or the hardware fast path is left on the wrong scale.
            await self._switch_range(self._active_range)
        return True

    async def set_range(self, value: int) -> bool:
        if value not in _RANGES:
            await self.pr.err_s("Error setting range: must be one of", _RANGES, errno=18)
            return False
        self._fixed_range = value
        if self._range_auto:
            return True  # stored as the preference; the state machine owns the chip's RNG bit
        try:
            await self.isl.configure(range_fs=value)
        except Exception as e:
            await self.pr.err_s("Error setting range:", e, errno=18)
            return False
        self._active_range = value
        return True

    async def set_range_auto(self, *, flag: bool) -> bool:
        # Not a purely software flag: turning it OFF applies the stored fixed range (a CONFIG1
        # write) and disarms the interrupt by writing INTSEL = 00 (a CONFIG3 write). Parking the
        # thresholds cannot disarm it - the part fires on "below OR EQUAL TO" the low threshold,
        # so a low threshold of 0x0000 still interrupts in total darkness.
        self._range_auto = flag
        try:
            if flag:
                await self.isl.configure(int_select=_INTSEL_GREEN)
            else:
                await self.isl.configure(range_fs=self._fixed_range, int_select=_INTSEL_NONE)
                self._active_range = self._fixed_range
        except Exception as e:
            await self.pr.err_s("Error applying the auto-range mode:", e, errno=38)
            return False
        if flag:
            await self._switch_range(self._active_range)  # re-arm the thresholds for where we are
        return True

    async def set_autorange_up(self, value: float) -> bool:
        if not await self._check_cross_field(up=value, down=self._ar_down, field="AutoRangeUp", low=_MIN_AR_UP, high=_MAX_AR_UP, checked=value):
            return False
        self._ar_up = value
        return True

    async def set_autorange_down(self, value: float) -> bool:
        if not await self._check_cross_field(up=self._ar_up, down=value, field="AutoRangeDown", low=_MIN_AR_DOWN, high=_MAX_AR_DOWN, checked=value):
            return False
        self._ar_down = value
        return True

    async def _check_cross_field(self, *, up: float, down: float, field: str, low: float, high: float, checked: float) -> bool:
        # FieldSchema's per-field min/max cannot express a relation between two fields, so the
        # driver enforces it: immediately after a switch up the same light reads u/r of the high
        # range, so d must clear u/(2r) for the loop not to chatter on noise alone.
        try:
            if not low <= checked <= high:
                raise ValueError(f"{field} must be between {low} and {high}")
            if not down <= up / _AR_CROSS_FIELD_DIVISOR:
                raise ValueError(f"AutoRangeDown must be <= AutoRangeUp/{_AR_CROSS_FIELD_DIVISOR:.1f} ({up / _AR_CROSS_FIELD_DIVISOR:.3f})")
        except (TypeError, ValueError, OverflowError, ZeroDivisionError) as e:
            await self.pr.err_s("Error setting", field, ":", e, errno=27)
            return False
        return True

    async def set_autorange_settle(self, value: int) -> bool:
        try:
            cycles = int(value)
            if not _MIN_SETTLE_CYCLES <= cycles <= _MAX_SETTLE_CYCLES:
                raise ValueError(f"AutoRangeSettle must be between {_MIN_SETTLE_CYCLES} and {_MAX_SETTLE_CYCLES} cycles")
        except (TypeError, ValueError, OverflowError) as e:
            await self.pr.err_s("Error setting AutoRangeSettle:", e, errno=27)
            return False
        self.isl.settle_cycles = cycles
        return True

    async def set_autorange_persist(self, value: int) -> bool:
        try:
            await self.isl.configure(persist=value)
        except Exception as e:
            await self.pr.err_s("Error setting AutoRangePersist:", e, errno=24)
            return False
        return True

    async def set_autorange_dwell(self, value: float) -> bool:
        try:
            dwell = float(value)
            if not _MIN_DWELL_S <= dwell <= _MAX_DWELL_S:
                raise ValueError(f"AutoRangeDwell must be between {_MIN_DWELL_S} and {_MAX_DWELL_S} seconds")
        except (TypeError, ValueError, OverflowError) as e:
            await self.pr.err_s("Error setting AutoRangeDwell:", e, errno=27)
            return False
        self._ar_dwell_s = dwell
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

    async def set_filter_coefficient(self, value: float) -> bool:
        try:
            coefficient = float(value)
            if not _MIN_FILT_COEFF <= coefficient <= _MAX_FILT_COEFF:
                raise ValueError(f"FiltCoeff must be between {_MIN_FILT_COEFF} and {_MAX_FILT_COEFF}")
        except (TypeError, ValueError, OverflowError) as e:
            await self.pr.err_s("Error setting filter coefficient:", e, errno=26)
            return False
        return True

    async def reset_gain_calibration(self, *, flag: bool) -> bool:
        # flag=False is deliberately a no-op, matching SGP40_Reader.reset_voc()'s own contract.
        if not flag:
            return False
        self._gain_ratio = _GAIN_RATIO_NOMINAL
        self._gain_ratio_ts = None
        self._gain_learn_ms = time.ticks_ms()
        cleared = await self._clear_gain_ratio()
        self.pr.one("Gain calibration discarded, relearning from nominal.")
        return cleared

    # -- getters (live chip read-back for the failed-push recovery chain) --

    async def _snapshot_field(self, index: int, errno: int, what: str) -> int | None:
        try:
            decoded = _decode_config_bytes(await self.isl.get_config_snapshot())
        except Exception as e:
            await self.pr.err_s("Error reading", what, ":", e, errno=errno)
            return None
        if decoded is None:
            return None
        return decoded[index]

    async def get_resolution(self) -> int | None:
        return await self._snapshot_field(0, 15, "resolution")

    async def get_range(self) -> int | None:
        return await self._snapshot_field(1, 17, "range")

    async def get_ir_comp_offset(self) -> int | None:
        return await self._snapshot_field(2, 19, "IR compensation offset")

    async def get_ir_comp_adjust(self) -> int | None:
        return await self._snapshot_field(3, 21, "IR compensation adjust")

    async def get_autorange_persist(self) -> int | None:
        return await self._snapshot_field(4, 23, "AutoRangePersist")

    # -- registration and data access --------------------------------------

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
        # wrnno=15 exist for, not a flood. The handler allocates nothing.
        self.irq_pin.irq(
            trigger=self.irq_pin.IRQ_FALLING,
            handler=lambda _b: self.read_event.set(),
        )

    def stop_timer(self) -> None:
        self.trigger_timer.deinit()  # Timer.deinit() IS real on rp2, unlike I2C/SPI (Part F.5.1)

    def get_task_starters(self) -> "list[Callable[[], asyncio.Task[Any]]]":
        return [self.start_asy_read, self.start_asy_trigger]

    def get_timer_starters(self) -> "list[Callable[[], None]]":
        return [self.start_timer]

    async def get_data(self) -> ISL29125:
        # Narrows to this Reader's concrete ISL29125 - see SPECIFICATION.md C.4.2's convention.
        return await self._get_meas_data()  # type: ignore[return-value]

    async def get_dict_data(self) -> "dict[str, dict[str, Any]]":
        # The one genuine override in this driver: the measurement body is nested (requirement
        # 11), which make_dict()'s flat one-level contract cannot express. Written out explicitly
        # rather than derived from the namedtuple because _asdict()/_fields need a ROM level above
        # rp2's own (see config_manager.make_dict()'s comment).
        data = await self.get_data()
        return {
            _NAME: {
                "Lux": data.Lux,
                "RGB": {"R": data.Red, "G": data.Green, "B": data.Blue},
                "HSB": {"H": data.Hue, "S": data.Sat, "B": data.Bri},
                "CCT": data.CCT,
                "RangeAct": data.RangeAct,
                "TS": data.TS,
            },
        }

    async def get_dict_cfg(self) -> "dict[str, dict[str, int | float | str | bool | None]]":
        # ISLResetCal is deliberately absent from this schema argument: ConfigManager.get_dict()
        # is all-or-nothing and would KeyError on a key it never persisted.
        return await self._get_dict_cfg(
            _NAME,
            _VAL_SI + _VAL_RES + _VAL_RA + _VAL_RNG + _VAL_AR_UP + _VAL_AR_DOWN + _VAL_AR_SETTLE
            + _VAL_AR_PERSIST + _VAL_AR_DWELL + _VAL_ICO + _VAL_ICA + _VAL_FC,
            callback=self._read_sensor_dict,
        )

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    async def get_mem_status(self) -> "tuple[float | None, int | None]":
        return self._gain_ratio, self._gain_ratio_ts


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
        # Set by the reader whenever AutoRangeSettle is applied: the POLICY stays on the reader,
        # the arithmetic lives next to the write that needs it.
        self.settle_cycles = 1

    def resolution_bits(self) -> int:
        return self._resolution

    def cycle_ms(self) -> int:
        return _CYCLE_MS_12BIT if self._resolution == _RESOLUTION_12BIT else _CYCLE_MS_16BIT

    def time_to_settle_ms(self) -> int:
        return max(0, time.ticks_diff(self._settle_until_ms, time.ticks_ms()))

    def encode_shadow(self) -> bytes:
        # Every field masked to its own width before shifting, so an out-of-range value can never
        # disturb a neighbouring bit - the same guard asy_i2c_driver.py's set_bits() applies.
        # Masks rather than validates: validation belongs at the setter boundary, and an encoder
        # that could raise would make configure()'s own failure modes ambiguous.
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
            # set_register_struct() takes a single value but accepts bytes, so an "Ns" format is
            # how a burst write goes through the promoted bus layer. struct.pack() silently
            # truncates on MicroPython rather than raising, which is why the value handed over is
            # already bytes of the exact length instead of an int.
            await i2c.set_register_struct(first_register, f"{len(payload)}s", payload)

    async def setup(self) -> None:
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            await i2c.setup()
        device_id = await self.get_device_id()
        if device_id != _DEVICE_ID:
            raise RuntimeError(f"Failed to find ISL29125! Device ID {hex(device_id)}")
        await self.reset()
        await self.clear_brownout()  # BOUTF is high at power-up and only a write clears it (p12)
        # SYNC and CONVEN are written explicitly rather than left at their reset default, so a
        # later change cannot flip either silently: SYNC = 1 turns INT into an INPUT and inverts
        # the whole interrupt path, and CONVEN would mux conversion-done onto the pin the
        # thresholds need.
        await self.configure(mode=_MODE_RGB, int_select=_INTSEL_GREEN, sync=0, conven=0, force=True)

    async def reset(self) -> None:
        # The datasheet specifies no post-reset settle time (unlike BMP3xx's documented 2ms), so
        # the verify read IS the settle. Only CONFIG1-3 are verified: SparkFun's own reset() also
        # requires STATUS to read 0x00, but Table 15 documents 0x04 as that register's default
        # (BOUTF high), so including it would contradict the datasheet - and reading 0x08 here
        # would break the "exactly one destructive status read per cycle" invariant besides.
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

    async def configure(
        self,
        *,
        mode: int | None = None,
        range_fs: int | None = None,
        resolution: int | None = None,
        ir_offset: int | None = None,
        ir_adjust: int | None = None,
        persist: int | None = None,
        int_select: int | None = None,
        sync: int | None = None,
        conven: int | None = None,
        force: bool = False,
    ) -> None:
        # The single write path. Writes the MINIMAL burst: three bytes from 0x01 when CONFIG1's
        # own byte changed, two from 0x02 otherwise, nothing at all when nothing changed - so an
        # IR-compensation change never restarts the conversion cycle. force=True re-applies the
        # whole shadow unconditionally, which is what brownout recovery and the divergence check
        # need (there is nothing to diff against a chip that has lost its configuration).
        before = self.encode_shadow()
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
        if int_select is not None:
            self._int_select = int_select
        if sync is not None:
            self._sync = sync
        if conven is not None:
            self._conven = conven
        after = self.encode_shadow()
        if after == before and not force:
            return
        wrote_config1 = force or after[0] != before[0]
        await self._write_shadow(_REGISTER_CONFIG1 if wrote_config1 else _REGISTER_CONFIG2)
        if wrote_config1:
            # Any writer of CONFIG1 restarts the conversion (p10, Table 7), and there are three of
            # them - the range switch, a resolution push and brownout recovery. Setting the
            # deadline in the function that does the write makes it impossible for a caller to
            # forget, and refreshes it automatically when a config push lands mid-settle.
            self._settle_until_ms = time.ticks_add(time.ticks_ms(), self.settle_cycles * self.cycle_ms())

    async def set_thresholds(self, low_counts: int, high_counts: int) -> None:
        low = max(0, min(_FULL_SCALE_COUNTS, low_counts))
        high = max(0, min(_FULL_SCALE_COUNTS, high_counts))
        packed = struct.pack("<HH", low, high)  # 0x04-0x07, low pair then high pair (p12, Table 14)
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            await i2c.set_register_struct(_REGISTER_THRESHOLDS, "4s", packed)

    async def read_counts(self) -> "tuple[int, int, int]":
        # "6s", NOT "<HHH": get_register_struct() returns unpacked[0] only, so a three-value
        # format would silently discard red and blue. The single most likely implementation
        # mistake in this driver, and it fails silently.
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            raw = await i2c.get_register_struct(_REGISTER_DATA, "6s")
        counts = _decode_rgb_burst(raw if isinstance(raw, bytes) else None)
        if counts is None:
            raise OSError("unexpected RGB data burst read result")
        return counts

    async def read_status(self) -> int:
        # DESTRUCTIVE: the read clears RGBTHF and releases the INT pin (p11/p12), so it happens
        # exactly once per read cycle and nothing else in this driver may read 0x08 "just to
        # check" - a second reader would silently consume another consumer's interrupt state.
        return await self._read_byte(_REGISTER_STATUS)

    async def clear_brownout(self) -> None:
        # Table 15 marks 0x08 "RO", but p12's own BOUTF text requires an I2C write to clear it -
        # the marking is a datasheet defect, not a prohibition.
        async with self.i2c_isl29125 as isl, isl.i2c_device as i2c:
            await i2c.set_register_struct(_REGISTER_STATUS, "B", 0x00)

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
