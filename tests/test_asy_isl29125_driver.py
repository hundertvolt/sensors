import asyncio
import errno as errno_mod
import struct
import time

from _error_codes import code
from _ticks30 import TICKS_PERIOD, Ticks30Time
from _tmp_scratch import TmpScratch
from machine import I2C as FakeI2C
from machine import Pin as FakePin
from machine import Timer as FakeTimer

import asy_base_classes
import asy_isl29125_driver
from asy_i2c_driver import I2C
from asy_isl29125_driver import (
    ISL29125,
    ISL29125_I2C,
    ISL29125_Reader,
)
from asy_print_log import LogConfig

# Mirrors of asy_isl29125_driver.py's own underscore-prefixed micropython.const() values - those
# are folded into every use site at compile time and are NOT importable module attributes (see
# test_asy_bmp3xx_driver.py's own note on the same trap). Kept in sync by citation, not re-derived.
_ADDR = 0x44  # hard-wired, p15 ("1000100")
_DEVICE_ID = 0x7D  # p9, Table 2
_CMD_RESET = 0x46
_REG_ID = 0x00
_REG_CONFIG1 = 0x01
_REG_CONFIG2 = 0x02
_REG_THRESHOLDS = 0x04
_REG_STATUS = 0x08
_REG_DATA = 0x09
_MODE_RGB = 0x05
_RNG_HIGH = 0x08
_BITS_12 = 0x10
_INTSEL_GREEN = 0x01
_STATUS_RGBTHF = 0x01
_STATUS_BOUTF = 0x04
_RANGE_LOW_LUX = 375
_RANGE_HIGH_LUX = 10000
_GAIN_RATIO_NOMINAL = 26.666666666666668
_GAIN_RATIO_MIN = 20.0  # the plausibility band the GainRatio field itself allows
_GAIN_RATIO_MAX = 34.0
_AR_DOWN_DIVISOR = 53.333333333333336  # 2 x the nominal range ratio - the derived down point
_CAL_CONVERGE_N = 3  # mirrors the driver's own const: consecutive agreeing readings that end a run

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    from typing_extensions import Self

    from asy_base_classes import JsonDict, PushFct
    from asy_config_manager import CfgValue
    from asy_isl29125_driver import ISLResults
    from asy_print_log import ErrorLog

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


async def _push(callback: "PushFct", value: "CfgValue") -> bool:
    # A push callback is typed to return an Awaitable (asy_base_classes' PushFct); run() takes a coroutine.
    return await callback(value)


class _FastAsyncSleep:
    # I2CDevice.setup()'s _probe_for_device() makes two real 0.1s asyncio.sleep() calls, and this
    # driver's own settle wait sleeps a whole 303ms conversion cycle - both far too slow for a
    # test driving _read_loop() as a background task. Same technique as test_asy_bmp3xx_driver.py's.
    def __enter__(self) -> "Self":
        self._real_sleep = asyncio.sleep
        self._real_sleep_ms = asyncio.sleep_ms

        async def _fast(_seconds: float) -> None:
            await self._real_sleep(0)

        async def _fast_ms(_ms: int) -> None:
            await self._real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # deliberate monkeypatch
        asyncio.sleep_ms = _fast_ms  # type: ignore[assignment]
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real_sleep
        asyncio.sleep_ms = self._real_sleep_ms


class _RaiseOnArm:
    # Same technique as test_asy_bmp3xx_driver.py's own _RaiseOnArm.
    def __init__(self, exc: "type[BaseException]" = OSError) -> None:
        self._exc = exc

    def __enter__(self) -> "Self":
        FakeTimer.raise_on_arm_exc = self._exc
        FakeTimer.raise_on_arm = True
        return self

    def __exit__(self, *exc_info: object) -> None:
        FakeTimer.raise_on_arm = False
        FakeTimer.raise_on_arm_exc = OSError


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that module's
# own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("isl29125")


def _tmp_cfg_path(name: str) -> str:
    return _scratch.dir(name)


def make_i2c() -> I2C:
    # A fresh static bus 0 (this tier has no per-test reset), its construction entry dropped so the
    # log holds only the test's own traffic.
    FakeI2C.reset_id(0)
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    fake(i2c).log.clear()
    fake(i2c).register_device(_ADDR)  # register-addressed (p9-p10), as the driver reads it
    _model_the_config_block(i2c)
    return i2c


def _model_the_config_block(i2c: I2C) -> None:
    # The address pointer auto-increments (p7), so a burst from 0x02 lands in CONFIG2-3 and a snapshot from 0x01
    # reads it back; tests/machine.py keys every write by its first register, so this mirrors it into 0x01's block.
    bus = fake(i2c)
    real_writeto = bus.writeto

    def writeto(address: int, buf: object, stop: bool = True) -> int:  # noqa: FBT001, FBT002  # machine.I2C's own positional stop
        acked = real_writeto(address, buf, stop)
        data = bytes(buf)  # type: ignore[call-overload]
        if address == _ADDR and stop and acked == len(data) > 1 and _REG_CONFIG2 <= data[0] <= _REG_CONFIG1 + 2:
            block = bus.registers.setdefault((address, _REG_CONFIG1), bytearray(3))
            for offset, value in enumerate(data[1 : 4 - (data[0] - _REG_CONFIG1)]):
                block[data[0] - _REG_CONFIG1 + offset] = value
        return acked

    bus.writeto = writeto  # type: ignore[method-assign]


def fake(i2c: I2C) -> FakeI2C:
    return i2c._i2c  # type: ignore[return-value]


def seed(i2c: I2C, register: int, payload: "bytes | bytearray", address: int = _ADDR) -> None:
    fake(i2c).registers[(address, register)] = bytearray(payload)


def seed_healthy_chip(i2c: I2C, address: int = _ADDR) -> None:
    # The minimum a real ISL29125 has to answer for setup() to succeed: the device ID, the three
    # config registers reading back zero after the reset write, and a status byte.
    seed(i2c, _REG_ID, bytes([_DEVICE_ID]), address)
    seed(i2c, _REG_CONFIG1, bytes([0x00, 0x00, 0x00]), address)
    seed(i2c, _REG_STATUS, bytes([0x00]), address)
    seed(i2c, _REG_DATA, bytes(6), address)


def counts_burst(green: int, red: int, blue: int) -> bytes:
    return struct.pack("<HHH", green, red, blue)


def make_protocol() -> "tuple[I2C, ISL29125_I2C]":
    i2c = make_i2c()
    return i2c, ISL29125_I2C(i2c)


def ready_protocol() -> "tuple[I2C, ISL29125_I2C]":
    i2c, isl = make_protocol()
    seed_healthy_chip(i2c)
    return i2c, isl


def protocol_at(bits: int) -> ISL29125_I2C:
    # Parks the shadow through the real write path, so normalise()/set_thresholds() run against a
    # shadow the driver set itself. A value configure() rejects goes straight onto the shadow:
    # normalise()'s unknown-resolution fallback is defence in depth, tested as such (Part E.4).
    _i2c, isl = make_protocol()
    if bits in (12, 16):
        run(isl.configure(resolution=bits))
    else:
        isl._resolution = bits
    return isl


def register_writes(i2c: I2C) -> "list[tuple[int, bytes]]":
    # A register write is one writeto() of the register byte and the payload, with a stop.
    return [(entry[2][0], entry[2][1:]) for entry in fake(i2c).log if entry[0] == "writeto" and entry[3] and len(entry[2]) > 1]


def register_reads(i2c: I2C) -> "list[tuple[int, int]]":
    # A register read is a no-stop writeto() of the register byte, then readfrom_into(): (register, length).
    reads: list[tuple[int, int]] = []
    pointer = None
    for entry in fake(i2c).log:
        if entry[0] == "writeto" and not entry[3] and len(entry[2]) == 1:
            pointer = entry[2][0]
        elif entry[0] == "readfrom_into" and pointer is not None:
            reads.append((pointer, len(entry[2])))
            pointer = None
    return reads


def fail_register_writes(i2c: I2C, times: int = 1) -> None:
    # The next `times` register writes raise EIO (a NACK); reads, whose no-stop pointer write carries the
    # same register byte, are left alone - a match= on the register could not tell the two apart.
    bus = fake(i2c)
    real_writeto = bus.writeto
    remaining = [times]

    def failing(address: int, buf: object, stop: bool = True) -> int:  # noqa: FBT001, FBT002  # machine.I2C's own positional stop
        if remaining[0] and stop and len(buf) > 1:  # type: ignore[arg-type]
            remaining[0] -= 1
            if not remaining[0]:
                bus.writeto = real_writeto  # type: ignore[method-assign]
            raise OSError(errno_mod.EIO, "no ACK")
        return real_writeto(address, buf, stop)

    bus.writeto = failing  # type: ignore[method-assign]


def logged(counters: "ErrorLog", kind: str, name: str = "ISL29125") -> "list[int]":
    # asy_print_log.py keeps errors and warnings in ONE history list, discriminated by the parallel
    # ErrType entry ("E"/"W") - so asserting on ErrNum alone would let warning 13 satisfy a test
    # written for error 13, and vice versa.
    entry = counters[name]
    # No strict= (ruff B905): MicroPython's zip() rejects it (CPython 3.10+-only), and ErrEntry
    # keeps both lists in step by construction - the same note src/asy_webserver_service.py carries.
    return [number for number, entry_kind in zip(entry["ErrNum"], entry["ErrType"]) if entry_kind == kind]  # noqa: B905


def err_count(counters: "ErrorLog", name: str = "ISL29125") -> int:
    count = counters[name]["ErrCount"]
    assert isinstance(count, int)
    return count


def errors(counters: "ErrorLog", name: str = "ISL29125") -> "list[int]":
    return logged(counters, "E", name)


def warnings(counters: "ErrorLog", name: str = "ISL29125") -> "list[int]":
    return logged(counters, "W", name)


# ---------------------------------------------------------------------------
# Pure helpers - F1 _decode_rgb_burst
# ---------------------------------------------------------------------------


def test_decode_rgb_burst_returns_green_red_blue_in_register_order() -> None:
    # Register order is GREEN, RED, BLUE (p9, Table 1); p13's Table 20 mislabels its own rows.
    assert ISL29125_I2C._decode_rgb_burst(counts_burst(0x1234, 0x5678, 0x9ABC)) == (0x1234, 0x5678, 0x9ABC)
    # Little-endian, proven by a byte string whose halves are distinguishable either way round.
    assert ISL29125_I2C._decode_rgb_burst(bytes([0x34, 0x12, 0x78, 0x56, 0xBC, 0x9A])) == (0x1234, 0x5678, 0x9ABC)


def test_decode_rgb_burst_rejects_short_and_none() -> None:
    assert ISL29125_I2C._decode_rgb_burst(None) is None
    assert ISL29125_I2C._decode_rgb_burst(b"") is None
    assert ISL29125_I2C._decode_rgb_burst(bytes(5)) is None
    assert ISL29125_I2C._decode_rgb_burst(bytes(7)) is None
    assert ISL29125_I2C._decode_rgb_burst(42) is None  # type: ignore[arg-type]


def test_decode_rgb_burst_accepts_a_bytearray_and_a_memoryview() -> None:
    # Both are legitimate returns from layer 1's own struct.unpack path.
    payload = counts_burst(1, 2, 3)
    assert ISL29125_I2C._decode_rgb_burst(bytearray(payload)) == (1, 2, 3)
    assert ISL29125_I2C._decode_rgb_burst(memoryview(payload)) == (1, 2, 3)


def test_decode_rgb_burst_decodes_the_all_ones_bus_fault_pattern() -> None:
    assert ISL29125_I2C._decode_rgb_burst(bytes([0xFF] * 6)) == (0xFFFF, 0xFFFF, 0xFFFF)


# ---------------------------------------------------------------------------
# F2 ISL29125_I2C.normalise - the rescale half
# ---------------------------------------------------------------------------


def test_normalise_shifts_only_at_12_bit() -> None:
    assert protocol_at(16).normalise((100, 200, 300), range_fs=_RANGE_HIGH_LUX)[0] == (100, 200, 300)
    assert protocol_at(12).normalise((100, 200, 300), range_fs=_RANGE_HIGH_LUX)[0] == (1600, 3200, 4800)


def test_normalise_12_bit_maximum_is_65520_not_65535() -> None:
    # The saturation trap, and why the two halves have to share one call: the shift cannot reach
    # full scale, so a saturation test written against the NORMALISED value is wrong at 12 bits.
    counts, saturated = protocol_at(12).normalise((4095, 4095, 4095), range_fs=_RANGE_HIGH_LUX)
    assert counts == (65520, 65520, 65520)
    assert saturated is True


def test_normalise_subtracts_the_dark_offset_on_the_low_range_only_and_clamps_at_zero() -> None:
    # DDark is specified at range 0 only (p3), so the range the sample was TAKEN on decides.
    assert protocol_at(16).normalise((10, 5, 1), range_fs=_RANGE_LOW_LUX)[0] == (9, 4, 0)
    assert protocol_at(16).normalise((10, 5, 1), range_fs=_RANGE_HIGH_LUX)[0] == (10, 5, 1)
    assert protocol_at(16).normalise((0, 0, 0), range_fs=_RANGE_LOW_LUX)[0] == (0, 0, 0)


def test_normalise_clamps_at_full_scale() -> None:
    assert protocol_at(16).normalise((70000, 65535, 65536), range_fs=_RANGE_HIGH_LUX)[0] == (65535, 65535, 65535)


def test_normalise_falls_back_to_no_shift_for_an_unknown_resolution() -> None:
    # The conservative direction: shifting when you should not inflates every reading 16x, while
    # not shifting when you should only under-reports.
    assert protocol_at(10).normalise((100, 100, 100), range_fs=_RANGE_HIGH_LUX)[0] == (100, 100, 100)


# ---------------------------------------------------------------------------
# F3 _counts_to_lux
# ---------------------------------------------------------------------------


def test_counts_to_lux_matches_the_datasheet_lsb_figures() -> None:
    # An external check, not a self-consistent one: p1's feature list states 5.7 mlux per LSB on
    # range 0 and 0.152 lux per LSB on range 1.
    assert abs(ISL29125_I2C.counts_to_lux(1, _RANGE_LOW_LUX, 1.0) - 0.00572) < 1e-5
    assert abs(ISL29125_I2C.counts_to_lux(1, _RANGE_HIGH_LUX, 1.0) - 0.15259) < 1e-5


def test_counts_to_lux_reaches_full_scale_at_full_count() -> None:
    assert ISL29125_I2C.counts_to_lux(0, _RANGE_LOW_LUX, 1.0) == 0.0
    assert abs(ISL29125_I2C.counts_to_lux(65535, _RANGE_LOW_LUX, 1.0) - 375.0) < 1e-9
    assert abs(ISL29125_I2C.counts_to_lux(65535, _RANGE_HIGH_LUX, 1.0) - 10000.0) < 1e-9


def test_counts_to_lux_applies_the_gain_correction_multiplicatively() -> None:
    assert abs(ISL29125_I2C.counts_to_lux(65535, _RANGE_HIGH_LUX, 0.97) - 9700.0) < 1e-6


# ---------------------------------------------------------------------------
# F4 _fraction_to_counts
# ---------------------------------------------------------------------------


def test_fraction_to_counts_does_not_truncate_like_the_riot_driver() -> None:
    # RIOT's own `(uint16_t)(65535 / max_range)` does the scaling in integer arithmetic and
    # truncates - 6.55 becomes 6, a 9% error. Doing it in float and rounding once is why this is
    # a named function at all, and these are the two schema defaults the design depends on.
    assert ISL29125_I2C.fraction_to_counts(85.0) == 55705
    assert ISL29125_I2C.fraction_to_counts(1.5) == 983


def test_fraction_to_counts_clamps_to_the_register_range() -> None:
    assert ISL29125_I2C.fraction_to_counts(0.0) == 0
    assert ISL29125_I2C.fraction_to_counts(100.0) == 65535
    assert ISL29125_I2C.fraction_to_counts(-5.0) == 0
    assert ISL29125_I2C.fraction_to_counts(1000.0) == 65535


def test_fraction_to_counts_lands_somewhere_defined_for_nan_and_inf() -> None:
    # int() raises ValueError for NaN and OverflowError for inf on MicroPython, so the guard has
    # to be explicit rather than incidental.
    assert ISL29125_I2C.fraction_to_counts(float("nan")) == 0
    assert ISL29125_I2C.fraction_to_counts(float("inf")) == 65535
    assert ISL29125_I2C.fraction_to_counts(float("-inf")) == 0


# ---------------------------------------------------------------------------
# F5 _is_bus_fault_pattern
# ---------------------------------------------------------------------------


def test_is_bus_fault_pattern_needs_all_three_channels_and_a_reserved_bit() -> None:
    assert ISL29125_I2C.is_bus_fault_pattern((0xFFFF, 0xFFFF, 0xFFFF), 0xFF) is True
    # A genuinely saturated white scene with a plausible status byte is NOT a bus fault.
    assert ISL29125_I2C.is_bus_fault_pattern((0xFFFF, 0xFFFF, 0xFFFF), 0x11) is False
    # Two of three at full scale is a real saturated scene with one unsaturated channel.
    assert ISL29125_I2C.is_bus_fault_pattern((0xFFFF, 0xFFFF, 0x1234), 0xFF) is False


def test_is_bus_fault_pattern_fires_on_raw_all_ones_at_both_resolutions() -> None:
    # A dead bus reads 0xFF bytes regardless of BITS, so the raw pattern is identical either way.
    for _bits in (12, 16):
        assert ISL29125_I2C.is_bus_fault_pattern((0xFFFF, 0xFFFF, 0xFFFF), 0xC8) is True


def test_is_bus_fault_pattern_is_false_for_a_clipped_12_bit_scene() -> None:
    # What is special about 12-bit is the OPPOSITE of "never fires": a real 12-bit reading cannot
    # exceed 4095, so at 12 bits this heuristic has no false-positive mode at all.
    assert ISL29125_I2C.is_bus_fault_pattern((4095, 4095, 4095), 0xFF) is False


def test_is_bus_fault_pattern_treats_a_non_int_status_as_implausible() -> None:
    assert ISL29125_I2C.is_bus_fault_pattern((0xFFFF, 0xFFFF, 0xFFFF), None) is True


def test_is_bus_fault_pattern_tolerates_a_missing_triple() -> None:
    assert ISL29125_I2C.is_bus_fault_pattern(None, 0xFF) is False


# ---------------------------------------------------------------------------
# F6 ISL29125_I2C.normalise - the saturation half
# ---------------------------------------------------------------------------


def test_normalise_reports_saturation_at_the_raw_resolution_maximum_not_65535() -> None:
    # The 12-bit trap from the other side: 4095 raw IS saturated, while the same reading after
    # normalisation is 65520 - which a post-normalisation `== 65535` test would miss entirely.
    assert protocol_at(12).normalise((4095, 0, 0), range_fs=_RANGE_HIGH_LUX)[1] is True
    assert protocol_at(12).normalise((65520, 0, 0), range_fs=_RANGE_HIGH_LUX)[1] is True  # >= , so an out-of-range test value still reads saturated
    assert protocol_at(12).normalise((4094, 4094, 4094), range_fs=_RANGE_HIGH_LUX)[1] is False
    assert protocol_at(16).normalise((65535, 0, 0), range_fs=_RANGE_HIGH_LUX)[1] is True
    assert protocol_at(16).normalise((65534, 65534, 65534), range_fs=_RANGE_HIGH_LUX)[1] is False


def test_normalise_reports_saturation_when_any_single_channel_clips() -> None:
    # Any channel, because the output is a colour triple: a clipped red with green at 40% of full
    # scale still destroys Hue, Sat and CCT.
    assert protocol_at(16).normalise((26214, 65535, 100), range_fs=_RANGE_HIGH_LUX)[1] is True
    assert protocol_at(16).normalise((65535, 26214, 100), range_fs=_RANGE_HIGH_LUX)[1] is True
    assert protocol_at(16).normalise((100, 26214, 65535), range_fs=_RANGE_HIGH_LUX)[1] is True


def test_normalise_falls_back_to_16_bit_saturation_for_an_unknown_resolution() -> None:
    assert protocol_at(10).normalise((4095, 4095, 4095), range_fs=_RANGE_HIGH_LUX)[1] is False


def test_decode_status_separates_the_four_flags() -> None:
    # p12, Tables 15-19: BOUTF is B2, RGBTHF B0, CONVENF B1, and RGBCF is the two-bit counter at
    # B5:B4 - an order that is easy to transpose and that nothing downstream would catch.
    assert ISL29125_I2C.decode_status(0x00) == (False, False, 0, False)
    assert ISL29125_I2C.decode_status(_STATUS_BOUTF) == (True, False, 0, False)
    assert ISL29125_I2C.decode_status(_STATUS_RGBTHF) == (False, True, 0, False)
    assert ISL29125_I2C.decode_status(0x02) == (False, False, 0, True)
    assert ISL29125_I2C.decode_status(0x20) == (False, False, 2, False)
    assert ISL29125_I2C.decode_status(0xFF) == (True, True, 3, True)


def test_decode_status_answers_none_for_anything_that_is_not_a_byte() -> None:
    # None is "layer 1 never produced a byte", which the read path treats as no flags at all -
    # a bool included, since True would otherwise decode as a threshold crossing.
    assert ISL29125_I2C.decode_status(None) is None
    assert ISL29125_I2C.decode_status(b"\x01") is None
    assert ISL29125_I2C.decode_status(True) is None
    assert ISL29125_I2C.decode_status(1.0) is None


def test_matches_shadow_ignores_reserved_bits_but_not_meaningful_ones() -> None:
    _i2c, isl = ready_protocol()
    run(isl.setup())
    shadow = isl.encode_shadow()
    assert isl.matches_shadow(shadow) is True
    # B7:B6 of CONFIG1 "can change without any notice" (p9), so they are not a divergence.
    assert isl.matches_shadow(bytes([shadow[0] | 0xC0, shadow[1], shadow[2]])) is True
    assert isl.matches_shadow(bytes([shadow[0] ^ _MODE_RGB, shadow[1], shadow[2]])) is False
    assert isl.matches_shadow(bytes(3)) is False  # the all-zero post-brownout chip


def test_matches_shadow_does_not_report_divergence_on_an_uncomparable_read() -> None:
    # A short read is a failed read, not evidence the chip moved - reporting divergence here
    # would make the reader re-apply the whole configuration on a bus glitch.
    _i2c, isl = ready_protocol()
    run(isl.setup())
    assert isl.matches_shadow(b"") is True
    assert isl.matches_shadow(bytes(2)) is True


# ---------------------------------------------------------------------------
# F7 ISL29125_I2C.decode_config
# ---------------------------------------------------------------------------


def test_decode_config_decodes_every_field() -> None:
    # CONFIG1 = mode 5 | RNG | BITS(12), CONFIG2 = IR offset + 40 codes, CONFIG3 = INTSEL green,
    # PRST = 10 -> 4 cycles.
    decoded = ISL29125_I2C.decode_config(bytes([_MODE_RGB | _RNG_HIGH | _BITS_12, 0x80 | 40, _INTSEL_GREEN | 0x08]))
    assert decoded == (12, _RANGE_HIGH_LUX, 1, 40, 4)
    decoded = ISL29125_I2C.decode_config(bytes([_MODE_RGB, 0x00, 0x00]))
    assert decoded == (16, _RANGE_LOW_LUX, 0, 0, 1)


def test_decode_config_round_trips_against_encode_shadow() -> None:
    _i2c, isl = make_protocol()
    for resolution in (12, 16):
        for range_fs in (_RANGE_LOW_LUX, _RANGE_HIGH_LUX):
            for ir_offset in (0, 1):
                for ir_adjust in (0, 40, 63):
                    for persist in (1, 2, 4, 8):
                        isl._resolution = resolution
                        isl._range_fs = range_fs
                        isl._ir_offset = ir_offset
                        isl._ir_adjust = ir_adjust
                        isl._persist = persist
                        assert ISL29125_I2C.decode_config(isl.encode_shadow()) == (resolution, range_fs, ir_offset, ir_adjust, persist)


def test_decode_config_ignores_the_reserved_bits() -> None:
    # p9: "the value of the reserved bit can change without any notice" - CONFIG1 B7:B6,
    # CONFIG2 B6 and CONFIG3 B7:B5.
    plain = ISL29125_I2C.decode_config(bytes([_MODE_RGB, 40, 0x00]))
    noisy = ISL29125_I2C.decode_config(bytes([_MODE_RGB | 0xC0, 40 | 0x40, 0xE0]))
    assert plain == noisy


def test_decode_config_decodes_an_all_zero_post_brownout_chip() -> None:
    # A chip that went through power-down reads 0x00 everywhere. That must decode without raising
    # AND be distinguishable from a configured chip - which it is, by the mode bits the caller
    # compares separately (this function deliberately does not decode mode).
    assert ISL29125_I2C.decode_config(bytes(3)) == (16, _RANGE_LOW_LUX, 0, 0, 1)


def test_decode_config_rejects_the_wrong_length_and_none() -> None:
    assert ISL29125_I2C.decode_config(None) is None
    assert ISL29125_I2C.decode_config(bytes(2)) is None
    assert ISL29125_I2C.decode_config(bytes(4)) is None
    # The TypeError half of the same guard: len() on a non-buffer, which a failed read that
    # returned something unexpected rather than None would hand it.
    assert ISL29125_I2C.decode_config(42) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Protocol layer - setup / reset / identity
# ---------------------------------------------------------------------------


def test_setup_sequence_is_id_reset_brownout_config() -> None:
    i2c, isl = ready_protocol()
    with _FastAsyncSleep():
        assert run(isl.setup()) is True
    reads = register_reads(i2c)
    writes = register_writes(i2c)
    assert reads[0][0] == _REG_ID  # identity first
    assert writes[0] == (_REG_ID, bytes([_CMD_RESET]))  # then the reset command
    assert reads[1][0] == _REG_CONFIG1  # the reset verify read
    assert writes[1] == (_REG_STATUS, bytes([0x00]))  # then BOUTF is cleared
    assert writes[2][0] == _REG_CONFIG1  # then one 3-byte config burst
    assert len(writes[2][1]) == 3


def test_setup_raises_on_a_wrong_device_id() -> None:
    i2c, isl = ready_protocol()
    seed(i2c, _REG_ID, bytes([0x42]))
    with _FastAsyncSleep():
        try:
            run(isl.setup())
        except RuntimeError as e:
            assert str(e) == "failed to find ISL29125, device ID 0x42"
            return
    raise AssertionError("setup() must refuse a chip that is not an ISL29125")


def test_setup_raises_when_the_bus_naks() -> None:
    i2c, isl = ready_protocol()
    fake(i2c).nak_addresses.add(_ADDR)
    with _FastAsyncSleep():
        try:
            run(isl.setup())
        except (OSError, ValueError):
            return
    raise AssertionError("setup() must raise on a bus that never ACKs")


def test_setup_writes_sync_and_conven_as_zero() -> None:
    # SYNC = 1 turns the INT pin into an INPUT and inverts the whole interrupt path (p6/p10
    # Table 7); CONVEN would mux conversion-done onto the pin the thresholds need.
    i2c, isl = ready_protocol()
    with _FastAsyncSleep():
        run(isl.setup())
    config1, _config2, config3 = register_writes(i2c)[2][1]
    assert config1 & 0x20 == 0  # SYNC
    assert config3 & 0x10 == 0  # CONVEN
    assert config1 & 0x07 == _MODE_RGB


def test_reset_raises_when_the_config_registers_do_not_clear() -> None:
    i2c, isl = ready_protocol()
    seed(i2c, _REG_CONFIG1, bytes([0x05, 0x00, 0x00]))
    try:
        run(isl.reset())
    except RuntimeError:
        return
    raise AssertionError("reset() must refuse to believe a reset that did not land")


def test_reset_does_not_read_the_destructive_status_register() -> None:
    # Reading 0x08 clears RGBTHF and releases INT, so the one-status-read-per-cycle invariant holds
    # here too - which is why this verify covers CONFIG1-3 only. SparkFun's reset() also requires
    # STATUS == 0x00, which contradicts Table 15's documented 0x04 default.
    i2c, isl = ready_protocol()
    run(isl.reset())
    assert all(register != _REG_STATUS for register, _length in register_reads(i2c))


def test_reset_restores_the_shadow_to_the_chips_own_defaults() -> None:
    # Shadow and chip have to agree again afterwards, or the next configure() would diff against
    # a state the chip no longer holds and write the wrong minimal burst.
    i2c, isl = ready_protocol()
    run(isl.configure(mode=_MODE_RGB, range_fs=_RANGE_HIGH_LUX, resolution=12, ir_adjust=40))
    assert isl.encode_shadow() != bytes(3)
    # tests/machine.py's I2C is a plain dict of registers with no reset semantics of its own, so
    # the chip-side clear the real 0x46 command performs is seeded here explicitly.
    seed(i2c, _REG_CONFIG1, bytes(3))
    run(isl.reset())
    assert isl.encode_shadow() == bytes(3)


def test_get_device_id_reads_one_byte_from_register_zero() -> None:
    i2c, isl = ready_protocol()
    assert run(isl.get_device_id()) == _DEVICE_ID
    assert register_reads(i2c) == [(_REG_ID, 1)]


# ---------------------------------------------------------------------------
# Protocol layer - the shadow write path
# ---------------------------------------------------------------------------


def test_encode_shadow_places_every_field_in_its_documented_bit() -> None:
    _i2c, isl = make_protocol()
    isl._mode = _MODE_RGB
    isl._range_fs = _RANGE_HIGH_LUX
    isl._resolution = 12
    isl._ir_offset = 1
    isl._ir_adjust = 40
    isl._persist = 8
    isl._int_select = _INTSEL_GREEN
    assert isl.encode_shadow() == bytes([_MODE_RGB | _RNG_HIGH | _BITS_12, 0x80 | 40, _INTSEL_GREEN | 0x0C])


def test_encode_shadow_masks_an_over_wide_field_instead_of_disturbing_its_neighbour() -> None:
    _i2c, isl = make_protocol()
    isl._mode = 0xFF  # far wider than the 3-bit MODE field
    isl._ir_adjust = 0xFF  # far wider than the 6-bit ALSCC field
    isl._int_select = 0xFF  # far wider than the 2-bit INTSEL field
    config1, config2, config3 = isl.encode_shadow()
    assert config1 & 0xF8 == 0  # nothing above MODE was disturbed
    assert config2 & 0x40 == 0  # CONFIG2's reserved B6 stays clear
    assert config3 & 0xF0 == 0  # nothing above PRST was disturbed


def test_encode_shadow_leaves_every_reserved_bit_zero() -> None:
    _i2c, isl = make_protocol()
    isl._mode = _MODE_RGB
    isl._range_fs = _RANGE_HIGH_LUX
    isl._resolution = 12
    isl._ir_offset = 1
    isl._ir_adjust = 63
    isl._persist = 8
    isl._int_select = _INTSEL_GREEN
    config1, config2, config3 = isl.encode_shadow()
    assert config1 & 0xC0 == 0
    assert config2 & 0x40 == 0
    assert config3 & 0xE0 == 0


def test_configure_writes_three_bytes_only_when_config1_changed() -> None:
    i2c, isl = ready_protocol()
    run(isl.configure(mode=_MODE_RGB))
    assert register_writes(i2c) == [(_REG_CONFIG1, bytes([_MODE_RGB, 0x00, 0x00]))]


def test_configure_writes_two_bytes_from_0x02_for_an_ir_only_change() -> None:
    # An IR-compensation change alone must not restart the conversion cycle, so it is a 2-byte
    # burst at 0x02 rather than a 3-byte one at 0x01.
    i2c, isl = ready_protocol()
    run(isl.configure(mode=_MODE_RGB))
    fake(i2c).log.clear()
    run(isl.configure(ir_adjust=40))
    assert register_writes(i2c) == [(_REG_CONFIG2, bytes([40, 0x00]))]


def test_configure_writes_nothing_when_nothing_changed() -> None:
    i2c, isl = ready_protocol()
    run(isl.configure(mode=_MODE_RGB))
    fake(i2c).log.clear()
    run(isl.configure(mode=_MODE_RGB))
    assert register_writes(i2c) == []


def test_configure_force_rewrites_all_three_bytes_even_with_no_change() -> None:
    # What brownout recovery and the divergence check need: there is nothing to diff against a
    # chip that has lost its configuration.
    i2c, isl = ready_protocol()
    run(isl.configure(mode=_MODE_RGB))
    fake(i2c).log.clear()
    run(isl.configure(force=True))
    assert register_writes(i2c) == [(_REG_CONFIG1, bytes([_MODE_RGB, 0x00, 0x00]))]


def test_configure_sets_the_settle_deadline_only_on_a_config1_write() -> None:
    _i2c, isl = ready_protocol()
    run(isl.configure(mode=_MODE_RGB))
    assert isl.time_to_settle_ms() > 0
    isl._settle_until_ms = time.ticks_add(time.ticks_ms(), -1000)  # the deadline has passed
    run(isl.configure(ir_adjust=40))
    assert isl.time_to_settle_ms() == 0


def test_the_settle_window_is_two_full_cycles_at_either_resolution() -> None:
    # Two cycles: Table 7 starts the ADC at an I2C write to 0x01 and leaves open whether a conversion in flight
    # restarts, so the second cycle is the margin; it costs one sample.
    for bits, cycle_ms in ((16, 303), (12, 19)):
        _i2c, isl = ready_protocol()
        isl._resolution = bits
        run(isl.configure(mode=_MODE_RGB))
        remaining = isl.time_to_settle_ms()
        assert cycle_ms < remaining <= 2 * cycle_ms


def test_cycle_time_follows_the_configured_resolution() -> None:
    _i2c, isl = make_protocol()
    assert isl.cycle_ms() == 303  # 3 x tINT, tINT = 101ms typ at 16 bits (p3)
    isl._resolution = 12
    assert isl.cycle_ms() == 19  # 3 x ~6.3ms, from p6's own n-bit-counter model


def test_time_to_settle_crosses_the_ticks_wrap() -> None:
    # A deadline armed 10 ms ahead, 5 ms before rp2's 2**30 ms wrap, lands past it: the whole wait reads before the
    # wrap, its last ms after it, and none once it has passed. A subtraction reads it as long past from the start.
    _i2c, isl = make_protocol()
    clock = Ticks30Time(TICKS_PERIOD - 5)
    asy_isl29125_driver.time = clock  # type: ignore[assignment]
    try:
        isl._settle_until_ms = clock.ticks_add(clock.ticks_ms(), 10)  # type: ignore[assignment]  # a ticks value from the fake
        reads = [isl.time_to_settle_ms()]
        clock.advance(9)
        reads.append(isl.time_to_settle_ms())
        clock.advance(2)
        reads.append(isl.time_to_settle_ms())
    finally:
        asy_isl29125_driver.time = time
    assert reads == [10, 1, 0], reads


def test_a_passed_settle_deadline_never_ages_past_the_tick_horizon() -> None:
    # A week with no CONFIG1 write: read hourly, a passed deadline moves up to now, so it never reads as the future
    # once 2**29 ms have gone by - no reading reports a settle pending and the wait sleeps on none.
    _i2c, reader = ready_reader("settle_horizon")
    clock = Ticks30Time(1000)
    slept: list[int] = []
    real_sleep_ms = asyncio.sleep_ms

    async def recording(ms: int) -> None:
        slept.append(ms)
        await real_sleep_ms(0)

    reads = []
    asy_isl29125_driver.time = clock  # type: ignore[assignment]
    asyncio.sleep_ms = recording  # type: ignore[assignment]
    try:
        reader._isl._settle_until_ms = clock.ticks_add(clock.ticks_ms(), 10)  # type: ignore[assignment]  # a ticks value from the fake
        passed = 0
        while passed <= (1 << 29) + 1000:
            clock.advance(3_600_000)
            passed += 3_600_000
            reads.append(reader._isl.time_to_settle_ms())
            run(reader._settle_wait())
    finally:
        asy_isl29125_driver.time = time
        asyncio.sleep_ms = real_sleep_ms
    assert set(reads) == {0}, [(index, value) for index, value in enumerate(reads) if value]
    assert slept == []


# ---------------------------------------------------------------------------
# Protocol layer - thresholds, data, status
# ---------------------------------------------------------------------------


def test_set_thresholds_is_one_four_byte_burst_little_endian() -> None:
    i2c, isl = ready_protocol()
    run(isl.set_thresholds(0x1234, 0xABCD))
    # Table 14's own row labels invite a byte-order mistake, so both values are distinguishable
    # whichever way round they land.
    assert register_writes(i2c) == [(_REG_THRESHOLDS, bytes([0x34, 0x12, 0xCD, 0xAB]))]


def test_set_thresholds_clamps_out_of_range_counts() -> None:
    i2c, isl = ready_protocol()
    run(isl.set_thresholds(-10, 70000))
    assert register_writes(i2c) == [(_REG_THRESHOLDS, bytes([0x00, 0x00, 0xFF, 0xFF]))]


def test_set_thresholds_rescales_both_counts_to_the_active_resolution() -> None:
    # Callers hand over 16-bit-scale counts; the registers are compared against the RAW ADC value,
    # so at 12 bits an unscaled threshold could never be crossed and the fast path would be dead.
    i2c, isl = make_protocol()
    run(isl.configure(resolution=12))
    fake(i2c).log.clear()  # drop the resolution write itself
    run(isl.set_thresholds(983, 55705))
    assert register_writes(i2c) == [(_REG_THRESHOLDS, struct.pack("<HH", 983 >> 4, 55705 >> 4))]


def test_set_thresholds_parks_an_omitted_up_crossing_at_the_top_of_the_active_scale() -> None:
    # The high range's only live threshold is the down-crossing, so the up-crossing has to sit
    # where it cannot fire - 4095 at 12 bits, NOT 65535, which the part would never reach.
    for bits, ceiling in ((12, 4095), (16, 65535)):
        i2c, isl = make_protocol()
        run(isl.configure(resolution=bits))
        fake(i2c).log.clear()
        run(isl.set_thresholds(0))
        assert register_writes(i2c) == [(_REG_THRESHOLDS, struct.pack("<HH", 0, ceiling))]


def test_read_counts_uses_a_six_byte_burst_not_three_halfwords() -> None:
    # Named for the trap: one 6-byte burst, never three 2-byte reads, so the three channels come from one conversion.
    i2c, isl = ready_protocol()
    seed(i2c, _REG_DATA, counts_burst(0x1111, 0x2222, 0x3333))
    assert run(isl.read_counts()) == (0x1111, 0x2222, 0x3333)
    assert register_reads(i2c) == [(_REG_DATA, 6)]


def test_read_counts_raises_rather_than_returning_none_on_a_bus_fault() -> None:
    i2c, isl = ready_protocol()
    fake(i2c).inject_fault("readfrom_into", OSError(errno_mod.EIO, "no ACK"), match=_REG_DATA)
    try:
        run(isl.read_counts())
    except OSError:
        return
    raise AssertionError("a failed data burst must raise, not return None")


def test_every_protocol_read_raises_rather_than_returning_none() -> None:
    # Layer 1 returns None for a malformed request but lets a real OSError through; this layer
    # normalises both into a raise so the reader's try blocks see one shape.
    for call, register in (("get_device_id", _REG_ID), ("read_status", _REG_STATUS), ("get_config_snapshot", _REG_CONFIG1), ("read_counts", _REG_DATA)):
        i2c, isl = ready_protocol()
        fake(i2c).inject_fault("readfrom_into", OSError(errno_mod.EIO, "no ACK"), match=register)
        try:
            run(getattr(isl, call)())
        except OSError:
            continue
        raise AssertionError(f"{call}() must raise on a bus fault")


def test_every_protocol_write_raises_on_a_bus_that_is_down() -> None:
    # A write the bus never made is no silent no-op: each raises, and configure() keeps its shadow on
    # what the chip still holds.
    i2c, isl = ready_protocol()
    i2c.deinit()
    calls: tuple[Callable[[], Coroutine[Any, Any, None]], ...] = (
        lambda: isl.configure(resolution=12),
        lambda: isl.set_thresholds(0, 1000),
        isl.clear_brownout,
    )
    for call in calls:
        try:
            run(call())
            message = ""
        except OSError as e:
            message = str(e)
        assert message == "I2C bus not initialized"
    decoded = ISL29125_I2C.decode_config(isl.encode_shadow())
    assert decoded is not None
    assert decoded[0] == 16


def test_read_status_reads_one_byte_and_clear_brownout_writes_it_low() -> None:
    i2c, isl = ready_protocol()
    seed(i2c, _REG_STATUS, bytes([_STATUS_BOUTF | _STATUS_RGBTHF]))
    assert run(isl.read_status()) == (_STATUS_BOUTF | _STATUS_RGBTHF)
    run(isl.clear_brownout())
    assert register_writes(i2c) == [(_REG_STATUS, bytes([0x00]))]


def test_get_config_snapshot_is_one_transaction_and_returns_the_raw_bytes_unmodified() -> None:
    i2c, isl = ready_protocol()
    seed(i2c, _REG_CONFIG1, bytes([0x15, 0xA8, 0x0D]))
    assert run(isl.get_config_snapshot()) == bytes([0x15, 0xA8, 0x0D])
    assert register_reads(i2c) == [(_REG_CONFIG1, 3)]


def test_get_config_snapshot_reports_the_chip_not_the_shadow() -> None:
    i2c, isl = ready_protocol()
    run(isl.configure(mode=_MODE_RGB, range_fs=_RANGE_HIGH_LUX))
    seed(i2c, _REG_CONFIG1, bytes([0x00, 0x00, 0x00]))  # the chip loses its configuration
    assert run(isl.get_config_snapshot()) == bytes(3)
    assert isl.encode_shadow() != bytes(3)


def test_construction_performs_no_bus_transactions() -> None:
    i2c, _isl = make_protocol()
    assert fake(i2c).log == []


# ---------------------------------------------------------------------------
# Reader construction and lifecycle - R1-R3
# ---------------------------------------------------------------------------


def make_reader(
    name: str,
    *,
    max_module_error: int = 5,
    healthy: bool = True,
    irq_pull_up: bool = True,
) -> "tuple[I2C, ISL29125_Reader]":
    FakeTimer.all_timers.clear()
    i2c = make_i2c()
    if healthy:
        seed_healthy_chip(i2c)
    reader = ISL29125_Reader(
        i2c,
        6,
        max_module_error=max_module_error,
        cfg_path=_tmp_cfg_path(name),
        irq_pull_up=irq_pull_up,
    )
    run(reader.setup())
    return i2c, reader


async def init_reader(reader: ISL29125_Reader, i2c: I2C) -> bool:
    # tests/machine.py's I2C is a plain dict of registers with no reset semantics, so the
    # chip-side clear that the real 0x46 command performs is seeded here before every init.
    seed(i2c, _REG_CONFIG1, bytes(3))
    return await reader._init_isl()


def ready_reader(name: str, **kwargs: "object") -> "tuple[I2C, ISL29125_Reader]":
    import time as _time

    i2c, reader = make_reader(name, **kwargs)  # type: ignore[arg-type]  # **object forwarding, checked at each call site
    with _FastAsyncSleep():
        assert run(init_reader(reader, i2c)) is True
    # init's CONFIG1 burst legitimately leaves a settle pending, and these tests run in zero wall
    # clock - so the first conversion is marked complete here rather than every test sleeping 303ms.
    # The settle behaviour has its own tests (test_no_sample_is_reported_during_the_settle_window).
    reader._isl._settle_until_ms = _time.ticks_ms()
    # 0x00 is read-only as the device ID and write-only as the reset command on real hardware, a
    # split tests/machine.py's flat register dict cannot model - so setup()'s reset write leaves
    # 0x46 where the ID should be. Restored so a later device-ID re-read sees a real chip.
    seed(i2c, _REG_ID, bytes([_DEVICE_ID]))
    fake(i2c).log.clear()
    return i2c, reader


def seed_cycle(i2c: I2C, green: int, red: int, blue: int, status: int = 0x00) -> None:
    seed(i2c, _REG_STATUS, bytes([status]))
    seed(i2c, _REG_DATA, counts_burst(green, red, blue))




def test_reader_construction_performs_no_bus_transactions() -> None:
    # Requirement 20, satisfied here or nowhere: every generated device's object graph is built against a fake
    # holding no ISL registers.
    i2c = make_i2c()
    ISL29125_Reader(i2c, 6, cfg_path=_tmp_cfg_path("no_io"))
    assert fake(i2c).log == []


def test_the_log_config_sets_both_loggers_length_and_level() -> None:
    reader = ISL29125_Reader(make_i2c(), 6, cfg_path=_tmp_cfg_path("log_config"), log=LogConfig(None, 3, 2))
    for pr in (reader.pr, reader.cfgmgr.pr):
        assert len(pr.history) == 3
        assert pr.level == 2
    assert reader._isl._i2c_isl29125.i2c_device.device_address == _ADDR  # the chip's one fixed address


def test_reader_construction_enables_the_internal_pull_up_on_the_int_pin() -> None:
    # The only promoted driver that needs one: this INT is open-drain pull-down (p6), unlike
    # SCD30's push-pull RDY line. irq_pull_up defaults True, so this is the no-argument shape.
    _i2c, reader = make_reader("pullup")
    assert reader.irq_pin.mode == FakePin.IN
    assert reader.irq_pin.pull == FakePin.PULL_UP


def test_reader_construction_can_disable_the_internal_pull_up_for_a_board_with_its_own_resistor() -> None:
    # irq_pull_up=False -> a bare Pin.IN, matching SCD30's own no-pull construction exactly, for a
    # board (like the real dev bench) that already carries an external pull-up on this line.
    _i2c, reader = make_reader("no_pullup", irq_pull_up=False)
    assert reader.irq_pin.mode == FakePin.IN
    assert reader.irq_pin.pull == -1  # tests/machine.py's own Pin: -1 means "never configured"


def test_init_returns_false_and_logs_an_init_error_and_reinitialises_the_controller() -> None:
    # A chip-setup failure runs the controller rung at once: the bus is cleared and its controller rebuilt.
    i2c, reader = make_reader("absent", healthy=False)
    fake(i2c).nak_addresses.add(_ADDR)
    before = i2c.recoveries

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            assert await init_reader(reader, i2c) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    assert errors(counters)[-1] == code("E", "INIT")
    assert warnings(counters) == [code("W", "BUS_RECOVERY")]
    assert i2c.recoveries == before + 1


def test_init_returns_false_when_the_config_is_unreadable_logs_in_both_layers() -> None:
    i2c, reader = make_reader("nocfg")
    reader.cfgmgr.valid = False  # what an unreadable/corrupt config file produces
    before = i2c.recoveries

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            assert await init_reader(reader, i2c) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    assert errors(counters)[-1] == code("E", "CFG_READ")
    # Each layer keeps its own entry: the reader's refusal here, the store's there.
    assert run(reader.cfgmgr.pr.get_log())[reader.cfgmgr.name]["ErrNum"][-1] == code("E", "CFG_NOT_VALID")
    assert i2c.recoveries == before  # no rung: an unreadable config is no bus fault
    assert warnings(counters) == []


def test_init_returns_false_and_logs_chip_set_when_applying_the_config_raises() -> None:
    i2c, reader = make_reader("cfgwrite")
    real_configure = reader._isl.configure

    async def only_the_startup_burst_fails(**kwargs: object) -> None:
        # setup()'s own configure() call has to succeed for init to reach the step under test;
        # the one carrying `resolution=` is the startup burst _init_isl() issues afterwards.
        if "resolution" in kwargs:
            raise OSError(errno_mod.EIO, "injected")
        await real_configure(**kwargs)  # type: ignore[arg-type]

    reader._isl.configure = only_the_startup_burst_fails  # type: ignore[method-assign]

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            assert await init_reader(reader, i2c) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    entry = counters["ISL29125"]
    assert (entry["ErrNum"][-2:], entry["ErrType"][-2:]) == ([code("E", "CHIP_SET"), code("W", "BUS_RECOVERY")], ["E", "W"])


def test_init_arms_the_thresholds_for_the_starting_range() -> None:
    # Easy to miss: without this the part boots with its power-on thresholds and the interrupt
    # path is dead until the first switch would have happened anyway.
    i2c, reader = make_reader("armed")
    with _FastAsyncSleep():
        assert run(init_reader(reader, i2c)) is True
    threshold_writes = [payload for register, payload in register_writes(i2c) if register == _REG_THRESHOLDS]
    assert len(threshold_writes) == 1
    # Starting on the high range, so only the DOWN crossing is armed: low = the derived
    # 85/53.33 = 1.594% of full scale, high parked at the resolution's own maximum.
    assert threshold_writes[0] == struct.pack("<HH", 1044, 65535)


def test_init_leaves_no_state_behind_after_a_failed_attempt() -> None:
    i2c, reader = make_reader("restart")
    reader._err_cnt_internal = 4
    fake(i2c).nak_addresses.add(_ADDR)
    with _FastAsyncSleep():
        assert run(init_reader(reader, i2c)) is False
    assert reader._err_cnt_internal == 0  # the streak counter is reset before anything can fail
    fake(i2c).nak_addresses.clear()
    seed_healthy_chip(i2c)
    with _FastAsyncSleep():
        assert run(init_reader(reader, i2c)) is True


def test_a_restart_resets_the_output_filter() -> None:
    # The filter state belongs to the task: after a restart the first sample is its own raw value, never an average
    # with a reading taken before it.
    i2c, reader = ready_reader("restart_filter")
    assert run(reader.cfgmgr.write_config({"FiltCoeff": 0.5}))[0] is True
    with _FastAsyncSleep():
        assert run(reader.set_filter_coefficient(0.5)) is True
        for green in (10000, 20000):
            seed_cycle(i2c, green, green, green)
            run(reader._store_isl(run(reader._read_isl())))
        assert run(init_reader(reader, i2c)) is True
        reader._isl._settle_until_ms = time.ticks_ms()
        seed(i2c, _REG_ID, bytes([_DEVICE_ID]))
        seed_cycle(i2c, 40000, 40000, 40000)
        run(reader._store_isl(run(reader._read_isl())))
    lux = run(reader.get_data()).Lux
    assert lux is not None
    assert abs(lux - ISL29125_I2C.counts_to_lux(40000, _RANGE_HIGH_LUX, 1.0)) < 1e-9, lux


def test_an_edge_seen_before_a_restart_is_not_credited_after_it() -> None:
    # An edge from before the restart says nothing about the line now: the first decision after it is periodic-led.
    i2c, reader = ready_reader("restart_edge")
    reader._irq_fired = True
    with _FastAsyncSleep():
        assert run(init_reader(reader, i2c)) is True
        reader._isl._settle_until_ms = time.ticks_ms()
        seed(i2c, _REG_ID, bytes([_DEVICE_ID]))
        reader._ar_dwell_s = 0.0
        reader._last_switch_ms = time.ticks_add(time.ticks_ms(), -1000)
        seed_cycle(i2c, 100, 100, 100, status=_STATUS_RGBTHF)
        run(reader._read_isl())
    assert reader._active_range == _RANGE_LOW_LUX
    assert reader._periodic_only_switches == 1


def test_read_loop_calls_error_check_exactly_once_per_cycle() -> None:
    i2c, reader = make_reader("cycles")
    seed_cycle(i2c, 20000, 20000, 20000)
    calls = []
    real_error_check = reader._error_check

    async def counting(results: "ISLResults", *, condition: bool = True) -> bool:
        calls.append(results)
        return await real_error_check(results, condition=condition)

    reader._error_check = counting  # type: ignore[method-assign, assignment]

    async def scenario() -> None:
        with _FastAsyncSleep():
            seed(i2c, _REG_CONFIG1, bytes(3))
            task = reader.start_asy_read()
            for _ in range(3):
                reader._read_event.set()
                for _ in range(40):
                    await asyncio.sleep(0)
            await _cancel_and_join(task)

    run(scenario())
    assert len(calls) == 3


def test_read_loop_climbs_the_ladder_then_gives_up() -> None:
    # The 2nd failed cycle re-applies the shadow (it fails on the dead bus: CHIP_SET, no DEVICE_RECOVERY), the 3rd
    # clears the bus once, and the 4th - past max_module_error - ends the task.
    i2c, reader = make_reader("budget", max_module_error=3)

    async def scenario() -> "list[bool]":
        with _FastAsyncSleep():
            assert await init_reader(reader, i2c) is True
            fake(i2c).nak_addresses.add(_ADDR)  # every later transaction fails
            verdicts = []
            for _ in range(4):
                verdicts.append(await reader._error_check(await reader._read_isl()))  # noqa: PERF401 - await is a SyntaxError in a MicroPython comprehension
            return verdicts

    before = i2c.recoveries
    assert run(scenario()) == [True, True, True, False]
    assert i2c.recoveries == before + 1
    counters = run(reader.get_error_counter())
    assert warnings(counters) == [code("W", "BUS_RECOVERY")]
    assert code("E", "CHIP_SET") in errors(counters)
    assert code("E", "STREAK") in errors(counters)
    assert errors(counters)[-1] == code("E", "GIVE_UP")


def test_no_exception_escapes_the_reader_layer() -> None:
    # The reader's never-raise contract, parametrised over every layer-2 entry point the read
    # path touches. Each injected raise must surface as an all-None result, never a traceback.
    for method in ("read_status", "read_counts", "get_config_snapshot", "get_device_id", "configure", "set_thresholds"):
        _i2c, reader = ready_reader("noraise_" + method)

        async def boom(*_args: object, **_kwargs: object) -> None:
            raise OSError(errno_mod.EIO, "injected")

        setattr(reader._isl, method, boom)
        with _FastAsyncSleep():
            # None of these may raise, whichever entry point was poisoned - that is the reader
            # layer's whole contract. read_status/read_counts additionally have to surface as a
            # failed read; the others are not on the per-cycle read path at all.
            results = run(reader._read_isl())
            run(reader._store_isl(results))
            run(reader._read_sensor_dict())
            run(reader.get_dict_cfg())
            run(reader.get_resolution())
            run(reader.set_resolution(12))
        if method in ("read_status", "read_counts"):
            assert results[0] is None, method


# ---------------------------------------------------------------------------
# Read path and derived outputs - R4-R7, R11
# ---------------------------------------------------------------------------


def _isl_group(body: "JsonDict") -> "JsonDict":
    # The REST body's one measurement group, narrowed from the JSON value type.
    group = body["ISL29125"]
    assert isinstance(group, dict)
    return group


class _UTCValid:
    # The NTP client's first clock set of the boot, as utc_now() sees it, undone on exit.
    def __enter__(self) -> "_UTCValid":
        asy_base_classes.set_utc_valid()
        return self

    def __exit__(self, *_exc: object) -> None:
        asy_base_classes.set_utc_valid(valid=False)


def test_a_read_before_the_first_sync_publishes_with_ts_none_and_steps_no_streak() -> None:
    # utc_now() is None until the NTP client sets the clock: the sample is published with TS None,
    # and the read loop's condition counts only a cycle whose measured values are gone.
    i2c, reader = make_reader("presync", max_module_error=1)
    seed_cycle(i2c, 20000, 20000, 20000)

    async def scenario() -> bool:
        with _FastAsyncSleep():
            seed(i2c, _REG_CONFIG1, bytes(3))
            task = reader.start_asy_read()
            for _ in range(40):  # the init, whose CONFIG1 write arms a settle no wall clock passes here
                await asyncio.sleep(0)
            for _ in range(3):  # three good cycles: past max_module_error had TS counted as a failure
                reader._isl._settle_until_ms = time.ticks_ms()
                reader._read_event.set()
                for _ in range(40):
                    await asyncio.sleep(0)
            running = not task.done()
            await _cancel_and_join(task)
        return running

    assert run(scenario()) is True
    data = run(reader.get_data())
    assert data.Lux is not None
    assert data.TS is None
    assert reader._err_cnt_internal == 0


def test_a_failed_read_keeps_the_last_good_sample_and_its_timestamp() -> None:
    i2c, reader = ready_reader("last_good")
    seed_cycle(i2c, 20000, 20000, 20000)
    with _FastAsyncSleep(), _UTCValid():
        run(reader._store_isl(run(reader._read_isl())))
        good = run(reader.get_data())
        fake(i2c).nak_addresses.add(_ADDR)
        failed = run(reader._read_isl())
        run(reader._store_isl(failed))
    assert good.TS is not None
    assert failed[0] is None
    assert run(reader.get_data()) == good  # the last good sample, its TS unchanged


def test_read_returns_a_narrow_results_tuple_without_cct() -> None:
    # The narrow tuple keeps CCT out: it is legitimately None in a dark room, and the read loop's
    # condition counts only a cycle whose measured values are gone.
    i2c, reader = ready_reader("narrow")
    seed_cycle(i2c, 20000, 21000, 22000)
    with _FastAsyncSleep():
        results = run(reader._read_isl())
    assert len(results) == 6
    # The range the sample was taken on AND the span its normalised outputs divide by - both
    # travel with the sample rather than being read back at store time (see ISLResults).
    assert results == (20000, 21000, 22000, _RANGE_HIGH_LUX, _RANGE_HIGH_LUX, results[5])


def test_the_results_tuple_carries_the_range_the_sample_was_taken_on() -> None:
    i2c, reader = ready_reader("carries_range")
    seed_cycle(i2c, 20000, 20000, 20000)
    with _FastAsyncSleep():
        results = run(reader._read_isl())
    assert results[3] == _RANGE_HIGH_LUX
    assert results[4] == _RANGE_HIGH_LUX  # the span
    assert results[5] is None  # TS: no NTP sync in this test


def test_a_switching_cycle_is_scaled_by_the_old_range_not_the_new_one() -> None:
    # The defect this 5-tuple exists for, asserted from both ends: the switch takes effect for
    # the NEXT cycle, so a sample acquired on the old gain must be scaled by the old full scale.
    i2c, reader = ready_reader("old_range")
    reader._ar_dwell_s = 0.0
    seed_cycle(i2c, 100, 100, 100)  # far below the down threshold -> switch down to 375 lux
    with _FastAsyncSleep():
        results = run(reader._read_isl())
    assert results[3] == _RANGE_HIGH_LUX  # the sample's own range
    assert reader._active_range == _RANGE_LOW_LUX  # the chip is already on the new one
    with _FastAsyncSleep():
        run(reader._store_isl(results))
    data = run(reader.get_data())
    assert data.RangeAct == _RANGE_HIGH_LUX
    # 99 counts on the high range is ~15 lux; scaled by the LOW range it would be ~0.57 lux.
    assert 14.0 < data.Lux < 16.0


def test_a_dark_room_never_increments_the_error_counter() -> None:
    # The same trap from the outside: CCT is None below the low-light floor, every cycle, and
    # that must not restart the task at max_module_error.
    i2c, reader = ready_reader("dark")
    seed_cycle(i2c, 2, 2, 2)
    reader._ar_dwell_s = 0.0

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            for _ in range(10):
                reader._isl._settle_until_ms = time.ticks_ms()  # the switch down's settle: no wall clock passes here
                results = await reader._read_isl()
                assert await reader._error_check(results, condition=results[0] is None and not reader._unsettled_cycle) is True  # the read loop's condition
                await reader._store_isl(results)
        return await reader.get_error_counter()

    counters = run(scenario())
    assert run(reader.get_data()).CCT is None
    assert errors(counters) == []  # a dark cycle is no failure
    assert reader._err_cnt_internal == 0


def test_store_produces_the_documented_nested_body() -> None:
    i2c, reader = ready_reader("nested")
    seed_cycle(i2c, 30000, 20000, 10000)
    with _FastAsyncSleep():
        run(reader._store_isl(run(reader._read_isl())))
    body = run(reader.get_dict_data())
    assert set(body) == {"ISL29125"}
    group = body["ISL29125"]
    assert isinstance(group, dict)
    assert set(group) == {"Lux", "RGB", "HSB", "CCT", "RangeAct", "Overrange", "GainMeas", "CalLight", "TS"}
    rgb, hsb = group["RGB"], group["HSB"]
    assert isinstance(rgb, dict) and isinstance(hsb, dict)
    assert set(rgb) == {"R", "G", "B"}
    assert set(hsb) == {"H", "S", "B"}
    assert group["RangeAct"] == _RANGE_HIGH_LUX
    assert group["Overrange"] is False


def test_cal_light_marks_the_calibration_band_at_its_edges() -> None:
    # The CalLight code is the calibration run's own band test: 2 at or below the derived down point, 3 at or above
    # the switch-up point, 1 strictly between; 0 with RangeAuto off or on a cycle that switches range.
    i2c, reader = ready_reader("cal_light")
    lo = ISL29125_I2C.fraction_to_counts(85.0 / _AR_DOWN_DIVISOR)
    hi = ISL29125_I2C.fraction_to_counts(85.0)

    async def code_for(green: int) -> "int | None":
        seed_cycle(i2c, green, green, green)
        reader._isl._settle_until_ms = time.ticks_ms()
        await reader._store_isl(await reader._read_isl())
        data = await reader.get_data()
        cal_light: int | None = data.CalLight
        return cal_light

    async def scenario() -> "list[int | None]":
        with _FastAsyncSleep():
            seen = []
            for green in (lo, lo + 1, hi - 1, hi):  # the dwell holds the range on all four
                seen.append(await code_for(green))  # noqa: PERF401 - await is a SyntaxError in a MicroPython comprehension
            assert await reader.set_range_auto(flag=False) is True
            seen.append(await code_for(2000))
            assert await reader.set_range_auto(flag=True) is True
            reader._ar_dwell_s = 0.0
            reader._last_switch_ms = time.ticks_add(time.ticks_ms(), -1000)
            seen.append(await code_for(100))  # below the down point with no dwell: this cycle switches down
        return seen

    assert run(scenario()) == [2, 1, 1, 3, 0, 0]
    assert reader._active_range == _RANGE_LOW_LUX

    _i2c, cal = calibrating_reader("cal_light_run")
    accepted: list[int] = []

    async def recording_leg(_target_range: int) -> "int | None":
        accepted.append(1)
        return None

    cal._read_on = recording_leg  # type: ignore[method-assign, assignment]
    for green in (lo, lo + 1, hi - 1, hi):
        accepted.clear()
        cal._isl._settle_until_ms = time.ticks_ms()
        with _FastAsyncSleep():
            run(cal._measure_gain_ratio(green))
        assert bool(accepted) is (cal._band_code(green) == 1), green


def test_cct_is_none_below_the_low_light_floor_and_present_above_it() -> None:
    i2c, reader = ready_reader("cct_floor")
    with _FastAsyncSleep():
        seed_cycle(i2c, 63, 50, 40)  # just below the 64-count floor
        run(reader._store_isl(run(reader._read_isl())))
        assert run(reader.get_data()).CCT is None
        # Comfortably above it, with a daylight-ish ratio McCamy's span accepts.
        seed_cycle(i2c, 20000, 19000, 18000)
        run(reader._store_isl(run(reader._read_isl())))
        assert run(reader.get_data()).CCT is not None


def test_hue_and_saturation_are_invariant_across_a_resolution_change() -> None:
    # All three channels share one RNG bit and one resolution, so any common scale factor
    # cancels out of the R:G:B ratios - H and S need no correction at all.
    i2c, reader = ready_reader("hs_invariant")
    with _FastAsyncSleep():
        seed_cycle(i2c, 32000, 16000, 8000)
        run(reader._store_isl(run(reader._read_isl())))
        at_16 = run(reader.get_data())
        run(reader.set_resolution(12))
        seed_cycle(i2c, 2000, 1000, 500)  # the same ratios, one resolution down
        run(reader._store_isl(run(reader._read_isl())))
        at_12 = run(reader.get_data())
    assert at_16.Hue is not None and at_12.Hue is not None
    assert abs(at_16.Hue - at_12.Hue) < 0.5
    assert at_16.Sat is not None and at_12.Sat is not None
    assert abs(at_16.Sat - at_12.Sat) < 0.01


def test_rgb_is_normalised_over_the_span_not_the_active_range() -> None:
    # Requirement 4: the same illumination read on each range must produce the same RGB/Bri. The
    # active-range form would step every normalised output by the ~26.67x gain ratio per switch,
    # which is exactly the discontinuity auto-range exists to remove.
    i2c, reader = ready_reader("span")
    with _FastAsyncSleep():
        seed_cycle(i2c, 6554, 6554, 6554)  # ~1000 lux on the high range
        run(reader._store_isl(run(reader._read_isl())))
        on_high = run(reader.get_data())
        reader._active_range = _RANGE_LOW_LUX
        reader._range_auto = True
        seed_cycle(i2c, 65535, 65535, 65535)  # 375 lux on the low range, its own full scale
        results = run(reader._read_isl())
        run(reader._store_isl(results))
        on_low = run(reader.get_data())
    assert on_high.Green is not None and on_low.Green is not None
    # 1000 lux over the 10000 lux span is 0.1; 375 lux over the same span is 0.0375. Both are
    # fractions of the SPAN - under an active-range denominator the second would read 1.0.
    assert abs(on_high.Green - 0.1) < 0.01
    assert abs(on_low.Green - 0.0375) < 0.01


def test_output_filter_applies_only_when_filtcoeff_is_positive() -> None:
    i2c, reader = ready_reader("filter")
    with _FastAsyncSleep():
        seed_cycle(i2c, 10000, 10000, 10000)
        run(reader._store_isl(run(reader._read_isl())))
        first = run(reader.get_data()).Lux
        seed_cycle(i2c, 20000, 20000, 20000)
        run(reader._store_isl(run(reader._read_isl())))
        unfiltered = run(reader.get_data()).Lux
        assert first is not None and unfiltered is not None
        # Off by default (FiltCoeff = -1.0), so the reported value tracks the raw one exactly.
        assert abs(unfiltered - 2.0 * first) < 1e-9
        # Now with the filter on: one step must land a tenth of the way, not all the way.
        run(reader.set_filter_coefficient(0.1))
        assert run(reader.cfgmgr.write_config({"FiltCoeff": 0.1}))[0] is True
        seed_cycle(i2c, 40000, 40000, 40000)
        run(reader._store_isl(run(reader._read_isl())))
        filtered = run(reader.get_data()).Lux
    assert filtered is not None
    assert abs(filtered - (unfiltered + 0.1 * (2.0 * unfiltered - unfiltered))) < 0.2


def test_status_register_is_read_exactly_once_per_cycle() -> None:
    # A hard invariant, not a style point: the read is destructive (it clears RGBTHF and releases
    # the INT pin), so a second reader would silently consume another consumer's interrupt state.
    i2c, reader = ready_reader("one_status")
    seed_cycle(i2c, 20000, 20000, 20000)
    with _FastAsyncSleep():
        run(reader._read_isl())
    assert [register for register, _length in register_reads(i2c)].count(_REG_STATUS) == 1


def test_handle_status_decodes_every_byte_value_without_raising() -> None:
    _i2c, reader = make_reader("status_table")
    for value in range(256):
        brownout, threshold_fired = reader._handle_status(value)
        assert brownout is bool(value & _STATUS_BOUTF)
        assert threshold_fired is bool(value & _STATUS_RGBTHF)
    assert reader._handle_status(None) == (False, False)
    assert reader._handle_status(b"\x01") == (False, False)


def test_a_bus_fault_pattern_is_confirmed_by_a_failed_device_id_re_read() -> None:
    i2c, reader = ready_reader("busfault")
    # 0xC8 is B7|B6|B3 - the reserved bits that read zero on a working part (p12, Table 15), and
    # deliberately NOT 0xFF, which would also set BOUTF and be handled as a brownout first.
    seed_cycle(i2c, 0xFFFF, 0xFFFF, 0xFFFF, status=0xC8)
    seed(i2c, _REG_ID, bytes([0x00]))  # the chip no longer answers with its real identity

    async def scenario() -> "tuple[ISLResults, ErrorLog]":
        with _FastAsyncSleep():
            results = await reader._read_isl()
        return results, await reader.get_error_counter()

    results, counters = run(scenario())
    assert results[0] is None
    assert code("E", "ISL_BUS_FAULT") in errors(counters)


def test_a_raising_device_id_re_read_prints_and_adds_no_second_entry() -> None:
    # One event, one persisted entry: the bus fault is the caller's ISL_BUS_FAULT; the re-read that raised is a
    # console line only.
    i2c, reader = ready_reader("busfault_id_raises")
    seed_cycle(i2c, 0xFFFF, 0xFFFF, 0xFFFF, status=0xC8)
    fake(i2c).inject_fault("readfrom_into", OSError(errno_mod.EIO, "no ACK"), match=_REG_ID)
    printed: list[tuple[object, ...]] = []
    real_err = reader.pr.err

    def spy(*args: object, sep: str = " ", end: str = "\n") -> None:
        printed.append(args)
        real_err(*args, sep=sep, end=end)

    reader.pr.err = spy  # type: ignore[method-assign]
    with _FastAsyncSleep():
        results = run(reader._read_isl())
    counters = run(reader.get_error_counter())
    assert results[0] is None
    assert err_count(counters) == 1
    assert errors(counters) == [code("E", "ISL_BUS_FAULT")]
    assert [line[0] for line in printed] == ["Device-ID re-read failed:"]


def test_a_genuinely_saturated_white_scene_survives_the_device_id_re_read() -> None:
    # The false-positive cost is one wasted transaction, never a discarded real sample.
    i2c, reader = ready_reader("real_sat")
    seed_cycle(i2c, 0xFFFF, 0xFFFF, 0xFFFF, status=0xC8)  # the ID still reads 0x7D

    async def scenario() -> "tuple[ISLResults, ErrorLog]":
        with _FastAsyncSleep():
            results = await reader._read_isl()
        return results, await reader.get_error_counter()

    results, counters = run(scenario())
    assert results[0] == 65535
    # Overrange belongs in the measurement output, not the log (BACKLOG.md) - already on the high
    # range with nowhere further to switch, so the scene wins and the field says so directly.
    assert warnings(counters) == []
    assert reader._last_overrange is True


def test_fixed_range_saturation_on_the_low_range_is_overrange_too() -> None:
    # A real gap the old saturation warning never covered, it only ever checking sample_range == _RANGE_HIGH_LUX:
    # with RangeAuto off, nothing will ever switch a saturated LOW range up, so "no option left to mitigate
    # it" is equally true there - a saturated fixed-low reading silently under-reported before this field.
    i2c, reader = ready_reader("fixed_low_sat")
    reader._range_auto = False
    reader._active_range = _RANGE_LOW_LUX
    seed_cycle(i2c, 0xFFFF, 0xFFFF, 0xFFFF)
    with _FastAsyncSleep():
        run(reader._read_isl())
    assert reader._last_overrange is True


def test_autorange_saturation_on_the_low_range_is_not_overrange_while_a_switch_is_under_way() -> None:
    # The mirror-image case: under Automatic Range, a saturated LOW-range sample always triggers
    # an immediate switch-up (_evaluate_range), so there IS an option left to mitigate it - that
    # is a normal, expected, momentary state on the way to the high range, not "nothing left".
    i2c, reader = ready_reader("auto_low_sat")
    assert reader._range_auto is True
    reader._active_range = _RANGE_LOW_LUX
    seed_cycle(i2c, 0xFFFF, 0xFFFF, 0xFFFF)
    with _FastAsyncSleep():
        run(reader._read_isl())
    assert reader._last_overrange is False
    assert reader._active_range == _RANGE_HIGH_LUX  # the switch really did happen


def test_the_dark_offset_is_subtracted_on_the_low_range_only() -> None:
    # DDark is specified at range 0 (p3), and that is the only place an additive count matters:
    # on the high range the same dark current is ~1/26.67 of a count, so subtracting a whole one
    # would remove 0.15 lux of real signal instead of an offset.
    i2c, reader = ready_reader("dark_offset")
    with _FastAsyncSleep():
        seed_cycle(i2c, 1000, 1000, 1000)
        assert run(reader._read_isl())[0] == 1000  # high range: nothing subtracted
        reader._active_range = _RANGE_LOW_LUX
        assert run(reader._read_isl())[0] == 999  # low range: the one documented dark count


def test_no_sample_is_reported_during_the_settle_window() -> None:
    i2c, reader = ready_reader("settle")
    seed_cycle(i2c, 20000, 20000, 20000)
    slept: list[int] = []
    real_sleep_ms = asyncio.sleep_ms

    async def recording(ms: int) -> None:
        slept.append(ms)
        await real_sleep_ms(0)

    asyncio.sleep_ms = recording  # type: ignore[assignment]
    try:
        with _FastAsyncSleep():
            run(reader._isl.configure(resolution=12))  # a CONFIG1 write, so a settle is now pending
            assert reader._isl.time_to_settle_ms() > 0
            asyncio.sleep_ms = recording  # type: ignore[assignment]  # _FastAsyncSleep replaced it
            run(reader._read_isl())
    finally:
        asyncio.sleep_ms = real_sleep_ms
    assert slept  # the cycle really did wait rather than reading straight through


def test_the_settle_wait_is_bounded_against_a_stream_of_config_writes() -> None:
    # The bound keeps the loop from starving; past it the cycle is discarded (see test_an_unsettled_cycle_is_no_failure).
    _i2c, reader = ready_reader("settle_bound")
    rounds = []
    real_sleep_ms = asyncio.sleep_ms

    async def extending(_ms: int) -> None:
        rounds.append(1)
        run_extend = reader._isl
        run_extend._settle_until_ms = __import__("time").ticks_add(__import__("time").ticks_ms(), 500)
        await real_sleep_ms(0)

    asyncio.sleep_ms = extending  # type: ignore[assignment]
    try:
        reader._isl._settle_until_ms = __import__("time").ticks_add(__import__("time").ticks_ms(), 500)
        run(reader._settle_wait())
    finally:
        asyncio.sleep_ms = real_sleep_ms
    assert len(rounds) == 2  # _SETTLE_WAIT_MAX_ROUNDS, not an unbounded loop


# ---------------------------------------------------------------------------
# Auto-range - R9, R10
# ---------------------------------------------------------------------------


def test_switch_up_on_saturation_without_waiting_for_persistence() -> None:
    _i2c, reader = make_reader("sat_up")
    reader._active_range = _RANGE_LOW_LUX
    # Well below AutoRangeThresh's own count, so only the saturation fast path can decide this.
    assert reader._evaluate_range((1000, 1000, 1000), saturated=True) == _RANGE_HIGH_LUX
    assert reader._evaluate_range((1000, 1000, 1000), saturated=False) is None


def test_switch_up_when_only_red_clips_and_green_is_mid_scale() -> None:
    # The peak-vs-green rule: green alone would leave this scene un-ranged, and it is exactly
    # what the NeoPixel rig drives.
    _i2c, reader = make_reader("peak_up")
    reader._active_range = _RANGE_LOW_LUX
    assert reader._evaluate_range((26214, 65535, 5000), saturated=True) == _RANGE_HIGH_LUX


def test_that_scene_does_not_switch_back_down_after_the_dwell_expires() -> None:
    # The oscillation the green-only version would have shipped: after the switch up, green sits
    # below the down threshold while red is still well above it.
    _i2c, reader = make_reader("peak_down")
    reader._active_range = _RANGE_HIGH_LUX
    reader._ar_dwell_s = 0.0  # the dwell has expired
    green_only = 900  # below the derived down point's own 1044 counts
    red_still_bright = 40000
    assert reader._evaluate_range((green_only, red_still_bright, 300), saturated=False) is None
    # Green alone really would have decided to go back down - that is what makes this a proof.
    assert reader._evaluate_range((green_only, 300, 300), saturated=False) == _RANGE_LOW_LUX


def test_switch_points_cannot_chatter_anywhere_in_the_threshold_band() -> None:
    # Immediately after a switch up the same light reads t/r of the high range, so the no-chatter
    # condition is t/r > t/(2r) - swept here as a real state machine, not asserted as arithmetic.
    # DERIVING the down point is what makes the whole legal band safe rather than one chosen pair.
    for thresh in (50.0, 85.0, 95.0):  # both schema bounds, and the default between them
        _i2c, reader = make_reader(f"chatter_{thresh}")
        reader._ar_thresh, reader._ar_dwell_s = thresh, 0.0
        reader._active_range = _RANGE_LOW_LUX
        thresh_counts = ISL29125_I2C.fraction_to_counts(thresh)
        # Just past the switch-up point on the low range.
        assert reader._evaluate_range((thresh_counts, thresh_counts, thresh_counts), saturated=False) == _RANGE_HIGH_LUX
        reader._active_range = _RANGE_HIGH_LUX
        # The SAME light, now on the high range: 26.67x fewer counts. It must stay put.
        after = int(thresh_counts / (10000.0 / 375.0))
        assert reader._evaluate_range((after, after, after), saturated=False) is None


def test_switch_down_is_suppressed_inside_the_dwell_window() -> None:
    _i2c, reader = make_reader("dwell")
    reader._active_range = _RANGE_HIGH_LUX
    reader._ar_dwell_s = 300.0
    reader._last_switch_ms = time.ticks_ms()
    assert reader._evaluate_range((10, 10, 10), saturated=False) is None
    reader._ar_dwell_s = 0.0
    assert reader._evaluate_range((10, 10, 10), saturated=False) == _RANGE_LOW_LUX


def test_no_range_decision_is_made_while_auto_is_off_or_a_settle_is_pending() -> None:
    _i2c, reader = make_reader("guards")
    reader._active_range = _RANGE_LOW_LUX
    reader._range_auto = False
    assert reader._evaluate_range((65535, 65535, 65535), saturated=True) is None
    reader._range_auto = True
    reader._isl._settle_until_ms = time.ticks_add(time.ticks_ms(), 500)
    assert reader._evaluate_range((65535, 65535, 65535), saturated=True) is None


def test_thresholds_are_written_before_the_range_bit() -> None:
    # The other order leaves a window where the new gain is live against the old thresholds,
    # which on a bright-to-dim transition fires an immediate spurious interrupt.
    i2c, reader = ready_reader("order")
    with _FastAsyncSleep():
        assert run(reader._switch_range(_RANGE_LOW_LUX)) is True
    writes = register_writes(i2c)
    assert writes[0][0] == _REG_THRESHOLDS
    assert writes[1][0] == _REG_CONFIG1
    # On the low range only an UP crossing matters: high = 85% of full scale, low parked at 0.
    assert writes[0][1] == struct.pack("<HH", 0, 55705)


def test_thresholds_are_scaled_to_the_active_resolution() -> None:
    # The threshold registers are compared against the RAW ADC value, so a 16-bit-scaled
    # threshold could never be crossed at 12 bits and the hardware fast path would be silently
    # dead there. ISL29125_I2C.fraction_to_counts() itself stays a pure fraction-of-65535 helper.
    i2c, reader = ready_reader("thresh_bits")
    with _FastAsyncSleep():
        run(reader._isl.configure(resolution=12))
        fake(i2c).log.clear()
        run(reader._switch_range(_RANGE_LOW_LUX))
    writes = [payload for register, payload in register_writes(i2c) if register == _REG_THRESHOLDS]
    assert writes[0] == struct.pack("<HH", 0, 55705 >> 4)  # 3481, inside a 12-bit reading's range


def test_a_partial_switch_is_retried_on_the_next_cycle() -> None:
    # Idempotent by construction: both writes are absolute values, and _active_range is NOT
    # updated when the second one fails, so the next evaluation re-decides and retries.
    i2c, reader = ready_reader("partial")
    with _FastAsyncSleep():
        fail_register_writes(i2c, times=1)
        assert run(reader._switch_range(_RANGE_LOW_LUX)) is False
        assert reader._active_range == _RANGE_HIGH_LUX
        assert run(reader._switch_range(_RANGE_LOW_LUX)) is True
        assert reader._active_range == _RANGE_LOW_LUX


def test_a_failed_threshold_write_and_a_failed_range_write_each_log_chip_set() -> None:
    i2c, reader = ready_reader("switch_errnos")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            fail_register_writes(i2c, times=1)
            await reader._switch_range(_RANGE_LOW_LUX)  # the threshold burst fails -> CHIP_SET
            real_configure = reader._isl.configure

            async def failing_configure(**_kwargs: object) -> None:
                raise OSError(errno_mod.EIO, "injected")

            reader._isl.configure = failing_configure  # type: ignore[method-assign]
            await reader._switch_range(_RANGE_LOW_LUX)  # thresholds land, CONFIG1 fails -> CHIP_SET
            reader._isl.configure = real_configure  # type: ignore[method-assign]
        return await reader.get_error_counter()

    counters = run(scenario())
    assert err_count(counters) == 2  # one count per failure, one slot for the repeated code
    assert errors(counters)[-1] == code("E", "CHIP_SET")
    assert reader._active_range == _RANGE_HIGH_LUX


def test_the_periodic_path_switches_range_when_the_interrupt_never_fires() -> None:
    # Requirement 17 in one test: the status byte reports no threshold crossing at all, and the
    # range still tracks - because the periodic evaluation runs on the same sample.
    i2c, reader = ready_reader("periodic")
    reader._ar_dwell_s = 0.0
    seed_cycle(i2c, 100, 100, 100, status=0x00)  # RGBTHF clear: the INT never asserted
    with _FastAsyncSleep():
        run(reader._read_isl())
    assert reader._active_range == _RANGE_LOW_LUX


def test_a_periodic_only_switch_warns_after_five_consecutive_occurrences() -> None:
    i2c, reader = ready_reader("wrn15")
    reader._ar_dwell_s = 0.0

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            for index in range(5):
                # Alternate the illumination so every cycle really does decide a switch. The
                # settle deadline each switch legitimately arms is cleared between cycles: no
                # wall-clock time passes in this test, and the settle guard has its own coverage.
                if index % 2 == 0:
                    seed_cycle(i2c, 100, 100, 100, status=0x00)
                else:
                    seed_cycle(i2c, 65535, 65535, 65535, status=0x00)
                reader._isl._settle_until_ms = time.ticks_ms()
                reader._last_switch_ms = time.ticks_add(time.ticks_ms(), -1000)
                await reader._read_isl()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert code("W", "ISL_PERIODIC_ONLY") in warnings(counters)


def test_an_interrupt_driven_switch_resets_the_periodic_only_counter() -> None:
    i2c, reader = ready_reader("wrn13_reset")
    reader._ar_dwell_s = 0.0

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            for index in range(3):  # three, not five - the counter must not reach its own warn point
                seed_cycle(i2c, 100, 100, 100, status=0x00) if index % 2 == 0 else seed_cycle(i2c, 65535, 65535, 65535, status=0x00)
                reader._isl._settle_until_ms = time.ticks_ms()
                await reader._read_isl()
            assert reader._periodic_only_switches == 3
            # The third iteration left the reader on the LOW range, so a BRIGHT scene is what
            # makes this last cycle decide a switch at all - and this time both halves of a
            # healthy fast path are present: the chip latched the crossing AND the line woke us.
            seed_cycle(i2c, 65535, 65535, 65535, status=_STATUS_RGBTHF)
            reader._irq_fired = True
            reader._isl._settle_until_ms = time.ticks_ms()
            await reader._read_isl()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert reader._periodic_only_switches == 0
    assert code("W", "ISL_PERIODIC_ONLY") not in warnings(counters), "the counter was reset by reaching its warn point, not by the interrupt"


def test_a_latched_flag_with_no_pin_edge_still_counts_as_a_periodic_only_switch() -> None:
    # The fault requirement 17 actually names - a missing pull-up or a broken jumper - leaves the
    # CHIP working: it latches RGBTHF exactly as before, and only the line never moves. Keying the
    # detector on the flag alone would therefore report a healthy fast path throughout.
    i2c, reader = ready_reader("wrn13_line_dead")
    reader._ar_dwell_s = 0.0
    with _FastAsyncSleep():
        seed_cycle(i2c, 100, 100, 100, status=_STATUS_RGBTHF)  # flag set...
        reader._irq_fired = False  # ...but no edge ever arrived
        reader._isl._settle_until_ms = time.ticks_ms()
        run(reader._read_isl())
    assert reader._active_range == _RANGE_LOW_LUX  # the switch still happened, via the periodic path
    assert reader._periodic_only_switches == 1


def test_the_pin_handler_records_the_edge_as_well_as_waking_the_read_loop() -> None:
    _i2c, reader = make_reader("irq_records")
    reader.start_timer()
    # Captured into a local first: mypy keeps a narrowed member type across an opaque call, so
    # asserting on reader._irq_fired twice would make the second assertion look unreachable.
    before = reader._irq_fired
    reader.irq_pin.trigger_irq()
    assert before is False
    assert reader._irq_fired is True
    assert _drain_flag(reader._read_event) is True


def test_five_periodic_led_decisions_in_a_row_report_a_possibly_dead_interrupt() -> None:
    # The derived window always leaves the chip time to raise RGBTHF first, so the periodic path
    # carrying five decisions running has exactly one reading left: the line is not delivering.
    i2c, reader = ready_reader("wrn13_12bit")

    async def scenario() -> "ErrorLog":
        await reader._isl.configure(resolution=12, persist=8)
        fake(i2c).log.clear()
        for _ in range(5):
            await reader._note_decision_source(threshold_fired=False)
        return await reader.get_error_counter()

    counters = run(scenario())
    assert code("W", "ISL_PERIODIC_ONLY") in warnings(counters)
    # The one fixable cause from this side: the chip's interrupt setup, re-written once - CONFIG1-3 and the thresholds.
    assert [payload for register, payload in register_writes(i2c) if register == _REG_CONFIG1] == [reader._isl.encode_shadow()]
    assert len(_threshold_bursts(i2c)) == 1
    assert reader._int_rearmed is True
    run(reader._note_decision_source(threshold_fired=True))
    assert reader._int_rearmed is False  # an interrupt-led decision ends the episode


def test_the_interrupt_is_rearmed_once_per_dead_line_episode() -> None:
    # Ten periodic-only decisions warn twice into one slot but re-arm once; an interrupt-led decision ends the
    # episode, and five more periodic-only ones re-arm again.
    i2c, reader = ready_reader("rearm_once")

    async def periodic(n: int) -> None:
        for _ in range(n):
            await reader._note_decision_source(threshold_fired=False)

    def config1_bursts() -> int:
        return sum(1 for register, _payload in register_writes(i2c) if register == _REG_CONFIG1)

    with _FastAsyncSleep():
        run(periodic(10))
        counters = run(reader.get_error_counter())
        assert warnings(counters) == [code("W", "ISL_PERIODIC_ONLY")]
        assert err_count(counters) == 2
        assert config1_bursts() == 1
        run(reader._note_decision_source(threshold_fired=True))
        run(periodic(5))
    assert config1_bursts() == 2


def _config2_bursts(i2c: I2C) -> "list[bytes]":
    return [payload for register, payload in register_writes(i2c) if register == _REG_CONFIG2]


def _parked(reader: ISL29125_Reader) -> bool:
    # Read through a call: mypy keeps a narrowed attribute across the cycles that change it.
    return reader._int_held


def _cycle(reader: ISL29125_Reader, i2c: I2C, counts: "tuple[int, int, int]", status: int = 0x00, *, irq: bool = False) -> None:
    # One read cycle whose conversion has completed; irq stands for the INT edge the pin handler records.
    seed_cycle(i2c, counts[0], counts[1], counts[2], status=status)
    reader._isl._settle_until_ms = time.ticks_ms()
    reader._irq_fired = irq
    with _FastAsyncSleep():
        run(reader._read_isl())


def test_an_int_the_peak_rule_overrules_is_parked_until_green_is_back_in_its_window() -> None:
    # A red-dominant scene on the high range: green crosses its down threshold, the peak holds the range, and the
    # flag would re-fire every PRST window - so the cycle parks INTSEL until green is back inside its window.
    i2c, reader = ready_reader("park_red")
    _cycle(reader, i2c, (10, 60000, 10), _STATUS_RGBTHF, irq=True)
    assert reader._active_range == _RANGE_HIGH_LUX
    assert [payload[-1] & 0x03 for payload in _config2_bursts(i2c)] == [0x00]
    assert _parked(reader) is True
    fake(i2c).log.clear()
    for _ in range(5):
        _cycle(reader, i2c, (10, 60000, 10))
    assert _config2_bursts(i2c) == []
    assert code("W", "ISL_PERIODIC_ONLY") not in warnings(run(reader.get_error_counter()))
    _cycle(reader, i2c, (2000, 60000, 10))  # green above the down threshold again
    assert [payload[-1] & 0x03 for payload in _config2_bursts(i2c)] == [_INTSEL_GREEN]
    assert _parked(reader) is False


def test_darkness_on_the_low_range_parks_the_zero_threshold() -> None:
    # The low range's lower threshold is 0, and the chip fires on "below or equal" (p12): total darkness keeps the
    # flag up for good. Parked while dark; re-armed at the first green count above zero.
    i2c, reader = ready_reader("park_dark")
    with _FastAsyncSleep():
        assert run(reader._switch_range(_RANGE_LOW_LUX)) is True
    fake(i2c).log.clear()
    _cycle(reader, i2c, (0, 0, 0), _STATUS_RGBTHF, irq=True)
    assert _parked(reader) is True
    assert [payload[-1] & 0x03 for payload in _config2_bursts(i2c)] == [0x00]
    for _ in range(3):
        _cycle(reader, i2c, (1, 1, 1))  # the 1-count dark offset leaves 0 counts: still dark
    assert _parked(reader) is True
    assert len(_config2_bursts(i2c)) == 1
    _cycle(reader, i2c, (2, 2, 2))
    assert _parked(reader) is False
    assert [payload[-1] & 0x03 for payload in _config2_bursts(i2c)] == [0x00, _INTSEL_GREEN]


def test_a_parked_int_stays_parked_across_a_periodic_down_switch() -> None:
    # Switches the periodic path makes neither arm the INT nor count toward a dead line while it is parked:
    # it stays parked until green is inside the new range's window, then one re-arm burst.
    i2c, reader = ready_reader("park_switch")
    reader._ar_dwell_s = 0.0
    _cycle(reader, i2c, (10, 60000, 10), _STATUS_RGBTHF, irq=True)
    assert _parked(reader) is True
    for index in range(5):
        reader._last_switch_ms = time.ticks_add(time.ticks_ms(), -1000)
        _cycle(reader, i2c, (10, 10, 10) if index % 2 == 0 else (65535, 65535, 65535))
    assert reader._active_range == _RANGE_LOW_LUX
    assert _parked(reader) is True
    assert reader._isl.encode_shadow()[2] & 0x03 == 0x00
    assert reader._periodic_only_switches == 0
    assert code("W", "ISL_PERIODIC_ONLY") not in warnings(run(reader.get_error_counter()))
    fake(i2c).log.clear()
    _cycle(reader, i2c, (1000, 1000, 1000))  # inside the low range's window
    assert [payload[-1] & 0x03 for payload in _config2_bursts(i2c)] == [_INTSEL_GREEN]
    assert _parked(reader) is False


def test_set_range_auto_racing_a_parking_cycle_leaves_intsel_and_the_flag_agreeing() -> None:
    # Every INTSEL write sets the flag with no await between, so a RangeAuto push landing inside a parking cycle
    # leaves INTSEL armed exactly when the flag says the INT is not parked.
    i2c, reader = ready_reader("park_race")
    real_switch = reader._switch_range

    async def yielding_switch(target_range: int) -> bool:
        await asyncio.sleep(0)
        return await real_switch(target_range)

    reader._switch_range = yielding_switch  # type: ignore[method-assign]
    seed_cycle(i2c, 10, 60000, 10, status=_STATUS_RGBTHF)
    reader._isl._settle_until_ms = time.ticks_ms()
    reader._irq_fired = True

    async def scenario() -> None:
        push = asyncio.create_task(reader.set_range_auto(flag=True))
        await reader._read_isl()
        assert await push is True

    with _FastAsyncSleep():
        run(scenario())
    assert (reader._isl.encode_shadow()[2] & 0x03 == _INTSEL_GREEN) is (not reader._int_held)


def test_a_switch_down_is_never_suppressed_by_a_week_old_switch_tick() -> None:
    # A week on the high range in a bright scene, evaluated hourly: the stored switch tick stays within the largest
    # dwell, so the first dark evaluation switches down instead of reading a tick past 2**29 ms as the future.
    _i2c, reader = make_reader("week_dwell")
    clock = Ticks30Time(5000)
    asy_isl29125_driver.time = clock  # type: ignore[assignment]
    try:
        reader._active_range = _RANGE_HIGH_LUX
        reader._ar_dwell_s = 10.0
        reader._last_switch_ms = clock.ticks_ms()  # type: ignore[assignment]  # a ticks value from the fake
        reader._isl._settle_until_ms = clock.ticks_ms()  # type: ignore[assignment]
        for _ in range(7 * 24):
            clock.advance(3_600_000)
            assert reader._evaluate_range((2000, 2000, 2000), saturated=False) is None
        clock.advance(3_600_000)
        decided = reader._evaluate_range((10, 10, 10), saturated=False)
    finally:
        asy_isl29125_driver.time = time
    assert decided == _RANGE_LOW_LUX


# ---------------------------------------------------------------------------
# Brownout - R8
# ---------------------------------------------------------------------------


def test_brownout_reapplies_the_whole_configuration_and_discards_one_cycle() -> None:
    i2c, reader = ready_reader("brownout")
    seed_cycle(i2c, 20000, 20000, 20000, status=_STATUS_BOUTF)
    with _FastAsyncSleep():
        results = run(reader._read_isl())
    assert results[:5] == (None,) * 5  # no sample: the chip was in power-down; the last element is the cycle's TS
    writes = register_writes(i2c)
    assert any(register == _REG_CONFIG1 and len(payload) == 3 for register, payload in writes)
    assert (_REG_STATUS, bytes([0x00])) in writes  # BOUTF written low
    assert any(register == _REG_THRESHOLDS for register, _payload in writes)  # thresholds re-armed


def test_repeated_brownouts_each_warn_into_one_slot() -> None:
    # Every detected brownout warns; the newest-entry rule folds the run into one slot.
    i2c, reader = ready_reader("brownout_flood")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            for _ in range(5):
                seed_cycle(i2c, 20000, 20000, 20000, status=_STATUS_BOUTF)
                reader._isl._settle_until_ms = time.ticks_ms()  # each re-apply's settle: no wall clock passes here
                await reader._read_isl()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert warnings(counters) == [code("W", "ISL_BROWNOUT")]
    assert errors(counters) == []
    assert err_count(counters) == 5


def test_a_recovered_brownout_and_the_next_one_share_one_slot() -> None:
    i2c, reader = ready_reader("brownout_again")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            for status in (_STATUS_BOUTF, 0x00, _STATUS_BOUTF):  # a dip, the supply recovered, and a dip again
                seed_cycle(i2c, 20000, 20000, 20000, status=status)
                reader._isl._settle_until_ms = time.ticks_ms()  # each re-apply's settle: no wall clock passes here
                await reader._read_isl()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert warnings(counters) == [code("W", "ISL_BROWNOUT")]
    assert errors(counters) == []
    assert err_count(counters) == 2


def test_brownout_does_not_feed_the_leaky_bucket_beyond_its_own_lost_cycle() -> None:
    # One increment, deliberately: the driver genuinely has no sample that cycle. That is the
    # intended cost of a recovered brownout - recovered, but not free.
    i2c, reader = ready_reader("brownout_bucket")

    async def scenario() -> int:
        with _FastAsyncSleep():
            seed_cycle(i2c, 20000, 20000, 20000, status=_STATUS_BOUTF)
            lost = await reader._read_isl()
            await reader._error_check(lost, condition=lost[0] is None and not reader._unsettled_cycle)  # the read loop's condition
            after_brownout = reader._err_cnt_internal
            seed_cycle(i2c, 20000, 20000, 20000, status=0x00)
            reader._isl._settle_until_ms = time.ticks_ms()  # the re-apply's settle: no wall clock passes here
            good = await reader._read_isl()
            await reader._error_check(good, condition=good[0] is None and not reader._unsettled_cycle)
        assert after_brownout == 1
        return reader._err_cnt_internal

    assert run(scenario()) == 0  # and a good cycle immediately pays it back
    # Each layer the brownout reaches keeps its entry: the driver's warning, then the streak step.
    counters = run(reader.get_error_counter())
    assert warnings(counters) == [code("W", "ISL_BROWNOUT")]
    assert errors(counters) == [code("E", "STREAK")]


def test_one_brownout_gives_one_entry_and_one_reapply() -> None:
    # A brownout zeroes CONFIG1-3 and raises BOUTF: the status read comes first, so the cycle takes the brownout
    # path alone - one W30, one re-apply - and never also reports the zeroed CONFIG as a divergence.
    i2c, reader = ready_reader("brownout_once")
    reapplied = [0]
    real_reapply = reader._reapply_configuration

    async def counting_reapply() -> bool:
        reapplied[0] += 1
        return await real_reapply()

    reader._reapply_configuration = counting_reapply  # type: ignore[method-assign]
    seed(i2c, _REG_CONFIG1, bytes(3))  # the chip's power-on CONFIG image
    seed_cycle(i2c, 20000, 20000, 20000, status=_STATUS_BOUTF)
    with _FastAsyncSleep():
        results = run(reader._read_isl())
    counters = run(reader.get_error_counter())
    assert results[:5] == (None,) * 5
    assert warnings(counters) == [code("W", "ISL_BROWNOUT")]
    assert err_count(counters) == 1
    assert reapplied[0] == 1
    assert [payload for register, payload in register_writes(i2c) if register == _REG_CONFIG1] == [reader._isl.encode_shadow()]


def test_a_brownout_recovery_write_failure_logs_chip_set() -> None:
    i2c, reader = ready_reader("brownout_fail")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            seed_cycle(i2c, 20000, 20000, 20000, status=_STATUS_BOUTF)
            fail_register_writes(i2c, times=5)
            await reader._read_isl()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert counters["ISL29125"]["ErrNum"][-2:] == [code("W", "ISL_BROWNOUT"), code("E", "CHIP_SET")]
    assert counters["ISL29125"]["ErrType"][-2:] == ["W", "E"]


# ---------------------------------------------------------------------------
# Live config read-back and divergence - R6
# ---------------------------------------------------------------------------


def test_read_sensor_dict_reports_the_five_hardware_backed_fields() -> None:
    _i2c, reader = ready_reader("sensor_dict")
    reader._range_auto = False
    with _FastAsyncSleep():
        result = run(reader._read_sensor_dict())
    assert result is not None
    assert set(result) == {"Resolution", "Range", "IRCompOffset", "IRCompAdjust"}


def test_read_sensor_dict_returns_none_when_the_snapshot_cannot_be_decoded() -> None:
    # The caller's own half of the guard above: an undecodable snapshot is no reading, so None (the
    # GET's unavailable marker) rather than a raise from the tuple unpack or an empty map.
    _i2c, reader = ready_reader("sensor_dict_undecodable")
    reader._range_auto = False
    reader._isl.decode_config = lambda _raw: None  # type: ignore[method-assign, assignment]  # deliberate monkeypatch
    with _FastAsyncSleep():
        assert run(reader._read_sensor_dict()) is None


def test_a_snapshot_field_read_degrades_to_none_when_the_snapshot_cannot_be_decoded() -> None:
    # Same guard on the single-field path, which every per-field getter goes through.
    _i2c, reader = ready_reader("snapshot_field_undecodable")
    reader._isl.decode_config = lambda _raw: None  # type: ignore[method-assign, assignment]  # deliberate monkeypatch
    with _FastAsyncSleep():
        assert run(reader._snapshot_field(0, "resolution")) is None


def test_read_sensor_dict_key_names_produce_no_unknown_key_warning() -> None:
    # _get_dict_cfg() warns (CALLBACK_KEYS) on any key the schema does not carry, so a typo here would
    # log a warning on every GET /sensors rather than failing anywhere visible.
    _i2c, reader = ready_reader("sensor_dict_keys")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            await reader.get_dict_cfg()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert code("W", "CALLBACK_KEYS") not in warnings(counters)


def test_range_readback_is_suppressed_while_autorange_is_on() -> None:
    # Under auto-range the chip's RNG bit is the state machine's choice, not the user's setting -
    # reporting it as the Range CONFIG field would overwrite the stored preference.
    _i2c, reader = ready_reader("range_readback")
    reader._range_auto = True
    with _FastAsyncSleep():
        automatic = run(reader._read_sensor_dict())
    assert automatic is not None
    assert "Range" not in automatic
    reader._range_auto = False
    with _FastAsyncSleep():
        manual = run(reader._read_sensor_dict())
    assert manual is not None
    assert "Range" in manual


def test_read_sensor_dict_returns_none_and_logs_chip_get_on_a_bus_fault() -> None:
    # Caught HERE, so the bus fault keeps its own CHIP_GET entry; the None tells _get_dict_cfg()
    # to answer the unavailable marker rather than fields a reader would take for unset ones.
    i2c, reader = ready_reader("sensor_dict_fail")

    async def scenario() -> "tuple[dict[str, int | float | str | bool | None] | None, ErrorLog]":
        with _FastAsyncSleep():
            fake(i2c).nak_addresses.add(_ADDR)
            result = await reader._read_sensor_dict()
        return result, await reader.get_error_counter()

    result, counters = run(scenario())
    assert result is None
    assert errors(counters).count(code("E", "CHIP_GET")) == 1


def test_get_dict_cfg_is_the_unavailable_marker_after_a_bus_fault_or_an_undecodable_snapshot() -> None:
    # Both of _read_sensor_dict()'s no-reading paths reach the GET as exactly the marker, in place
    # of the map: no stored value beside it, and the bus fault's one CHIP_GET entry.
    i2c, reader = ready_reader("dict_cfg_bus_fault")

    async def bus_fault() -> "tuple[dict[str, dict[str, int | float | str | bool | None]], ErrorLog]":
        with _FastAsyncSleep():
            fake(i2c).nak_addresses.add(_ADDR)
            body = await reader.get_dict_cfg()
        return body, await reader.get_error_counter()

    body, counters = run(bus_fault())
    assert body == {"ISL29125": {"error": "unavailable"}}
    assert errors(counters).count(code("E", "CHIP_GET")) == 1
    assert code("E", "CFG_CALLBACK_RAISED") not in errors(counters)

    _i2c, undecodable = ready_reader("dict_cfg_undecodable")
    undecodable._isl.decode_config = lambda _raw: None  # type: ignore[method-assign, assignment]  # a planted undecodable snapshot
    with _FastAsyncSleep():
        assert run(undecodable.get_dict_cfg()) == {"ISL29125": {"error": "unavailable"}}


def test_read_sensor_dict_detects_a_diverged_mode_and_reapplies_the_shadow() -> None:
    # The divergence the OLD five-decoded-value return could not see: mode, SYNC, CONVEN and
    # INTSEL are exactly the bits a brownout or a stray write zeroes, and decoding them away
    # first is what would make this check blind to the thing it exists for.
    i2c, reader = ready_reader("divergence")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            shadow = reader._isl.encode_shadow()
            seed(i2c, _REG_CONFIG1, bytes([shadow[0] & ~0x07, shadow[1], shadow[2]]))  # mode zeroed
            await reader._read_sensor_dict()
        return await reader.get_error_counter()

    counters = run(scenario())
    # ISL_DIVERGED, not ISL_BROWNOUT: a chip that disagrees with the shadow for any other reason
    # is a different event.
    assert warnings(counters).count(code("W", "ISL_DIVERGED")) == 1
    assert code("W", "ISL_BROWNOUT") not in warnings(counters)
    assert any(register == _REG_CONFIG1 and len(payload) == 3 for register, payload in register_writes(i2c))


def test_a_reserved_bit_difference_is_not_reported_as_divergence() -> None:
    # p9: "the value of the reserved bit can change without any notice" - a driver comparing raw
    # bytes would eventually report a divergence that is not one.
    i2c, reader = ready_reader("reserved_bits")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            shadow = reader._isl.encode_shadow()
            seed(i2c, _REG_CONFIG1, bytes([shadow[0] | 0xC0, shadow[1] | 0x40, shadow[2] | 0xE0]))
            await reader._read_sensor_dict()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert code("W", "ISL_DIVERGED") not in warnings(counters)


def test_get_dict_cfg_excludes_the_command_only_field() -> None:
    # ConfigManager.get_dict() is all-or-nothing and would KeyError on a key it never persisted.
    _i2c, reader = ready_reader("cfg_excl")
    with _FastAsyncSleep():
        body = run(reader.get_dict_cfg())
    assert "Calibrate" not in body["ISL29125"]
    assert "SampleInterval" in body["ISL29125"]
    assert set(body["ISL29125"]) == {
        "SampleInterval", "Resolution", "RangeAuto", "Range", "AutoRangeThresh",
        "AutoRangeDwell", "IRCompOffset", "IRCompAdjust", "FiltCoeff", "GainRatio",
    }


# ---------------------------------------------------------------------------
# Config surface - the eleven pushes, the setters and the four getters
# ---------------------------------------------------------------------------


def test_every_schema_field_has_a_push_callback() -> None:
    _i2c, reader = make_reader("push_coverage")
    names = [field[0] for field in reader.get_cfg_schema()]
    assert len(names) == 11  # AutoRangePersist, AutoRangeDown and AutoRangeSettle all derived now
    assert sorted(reader._push_callbacks) == sorted(names)


def test_only_the_five_hardware_backed_fields_have_a_getter() -> None:
    # A software-only knob has nothing to read back, and _recover_failed_push() skips a
    # command-only field by design - a getter for either would be dead code.
    _i2c, reader = make_reader("get_coverage")
    assert sorted(reader._get_callbacks) == [
        "IRCompAdjust", "IRCompOffset", "Range", "Resolution",
    ]


def test_each_push_rejects_the_wrong_type_without_touching_the_bus() -> None:
    # type(value) is not int, deliberately NOT isinstance: isinstance(True, int) is True in
    # Python, so a bool would slip straight through into an int field.
    i2c, reader = ready_reader("push_types")
    wrong: dict[str, int | float | str | bool | None] = {
        "SampleInterval": True, "Resolution": 16.0, "RangeAuto": 1, "Range": "10000",
        "AutoRangeThresh": 85,
        "AutoRangeDwell": 10, "IRCompOffset": False, "IRCompAdjust": 40.0, "FiltCoeff": 0,
        "GainRatio": 26, "Calibrate": 1,
    }
    with _FastAsyncSleep():
        for field, value in wrong.items():
            assert run(_push(reader._push_callbacks[field], value)) is False, field
    assert register_writes(i2c) == []


def test_pushing_resolution_reaches_the_chip_byte_exactly() -> None:
    i2c, reader = ready_reader("push_resolution")
    with _FastAsyncSleep():
        assert run(_push(reader._push_callbacks["Resolution"], 12)) is True
    config1 = next(payload for register, payload in register_writes(i2c) if register == _REG_CONFIG1)
    assert config1[0] & _BITS_12


def test_pushing_ir_compensation_reaches_config2_without_touching_config1() -> None:
    i2c, reader = ready_reader("push_ir")
    with _FastAsyncSleep():
        assert run(_push(reader._push_callbacks["IRCompOffset"], 1)) is True
        assert run(_push(reader._push_callbacks["IRCompAdjust"], 63)) is True
    writes = register_writes(i2c)
    assert all(register == _REG_CONFIG2 for register, _payload in writes)
    assert writes[-1][1][0] == 0x80 | 63


def test_the_derived_persistence_reaches_config3_and_tracks_its_two_inputs() -> None:
    # PRST is not pushable any more - it is derived from Resolution and SampleInterval, so the only
    # way it reaches the chip is one of those two changing. 12 bit makes a cycle ~16x shorter, so
    # the same interval then affords the largest rejection the part offers.
    i2c, reader = ready_reader("derived_persist")
    with _FastAsyncSleep():
        assert run(reader.set_resolution(12)) is True
    writes = register_writes(i2c)
    assert any(w[0] == _REG_CONFIG2 and w[1][1] & 0x0C == 0x0C for w in writes), "12 bit should derive PRST=8"


def test_the_derivation_never_lets_the_window_outlast_the_sample_interval() -> None:
    # The property the whole change exists for, asserted across every combination the schema can
    # produce rather than at the default alone: whatever the user sets, the chip can still raise
    # RGBTHF before the periodic re-check would have decided.
    _i2c, reader = ready_reader("derived_invariant")
    for resolution in (12, 16):
        reader._isl._resolution = resolution
        for trigger_s in (1, 2, 5, 60, 3600):
            window_ms = reader._isl.persist_for_interval(trigger_s) * reader._isl.cycle_ms()
            assert window_ms < trigger_s * 1000, (resolution, trigger_s)
    # And it is the LARGEST that fits, not merely a safe one - a derivation that always returned 1
    # would satisfy the assertion above while throwing away every bit of transient rejection.
    reader._isl._resolution = 16
    assert reader._isl.persist_for_interval(1) == 2  # 606ms of 1000ms; 4 cycles would be 1212ms
    reader._isl._resolution = 12
    assert reader._isl.persist_for_interval(1) == 8  # ~152ms of 1000ms


def test_the_derivation_degrades_to_the_shortest_window_when_none_fits() -> None:
    # The fallback the reader cannot reach - _MIN_TRIGGER_S is 1s against a 303ms cycle, so some
    # option always fits. The protocol layer takes no such bound, and the honest degradation is the
    # SHORTEST rejection. Asserted so a bound change surfaces as a decision, not a surprise.
    _i2c, isl = make_protocol()
    assert isl.persist_for_interval(0) == 1
    run(isl.configure(resolution=12))
    assert isl.persist_for_interval(0) == 1


def test_a_rangeauto_push_landing_between_the_read_and_the_store_cannot_renormalise_the_sample() -> None:
    # Guard: the span travels with the sample, so a RangeAuto push between read and store cannot renormalise
    # it: 20000 counts on the 10000 lx range stay 0.305 of the span, not a clamped 1.0.
    i2c, reader = ready_reader("store_mode_push")
    seed_cycle(i2c, 20000, 20000, 20000)
    with _FastAsyncSleep():
        # Stored as a preference only while RangeAuto is on - no chip write - so this is purely
        # what the push below will select.
        assert run(reader.set_range(_RANGE_LOW_LUX)) is True
        results = run(reader._read_isl())
        assert run(reader.set_range_auto(flag=False)) is True
        run(reader._store_isl(results))
    data = run(reader.get_data())
    assert data.Green is not None
    assert 0.30 < data.Green < 0.31, data.Green


def test_a_config_push_landing_mid_read_scales_the_sample_by_the_gain_it_was_taken_on() -> None:
    # asyncio can run a REST handler at any of a cycle's awaits, so a Resolution PUT can land
    # between the capture and the data read. p13's double buffering means what comes back is
    # still the OLD config's conversion - scaling it by the new one is 16x out and fakes saturation.
    i2c, reader = ready_reader("mid_read_push")
    seed_cycle(i2c, 20000, 20000, 20000)
    real_counts = reader._isl.read_counts

    async def _a_rest_push_then_the_data() -> "tuple[int, int, int]":
        assert await reader.set_resolution(12) is True
        return await real_counts()

    reader._isl.read_counts = _a_rest_push_then_the_data  # type: ignore[method-assign]
    with _FastAsyncSleep():
        green, red, blue, sample_range, _sample_span, _timestamp = run(reader._read_isl())
    assert (green, red, blue) == (20000, 20000, 20000), "a 16-bit conversion must not be shifted as if it were 12-bit"
    assert sample_range == _RANGE_HIGH_LUX
    assert reader._last_overrange is False, "no saturation happened"


def test_a_failed_config_write_leaves_the_shadow_on_the_value_the_chip_still_holds() -> None:
    # The shadow is not bookkeeping - normalise() scales EVERY reading by it. A resolution the chip
    # never took shifts every later sample 16x and reports saturation above 4095, pinning auto-range
    # high. Nothing in the read path notices: the reads themselves keep succeeding.
    i2c, isl = ready_protocol()
    run(isl.setup())
    fail_register_writes(i2c, times=1)
    raised = False
    try:
        run(isl.configure(resolution=12))
    except OSError:
        raised = True
    assert raised, "configure() still reports the failure to its caller"
    decoded = ISL29125_I2C.decode_config(isl.encode_shadow())
    assert decoded is not None
    assert decoded[0] == 16, "the chip is still at 16 bit, so the shadow must be too"
    # And the consequence the shadow exists to get right, asserted through the real scaler.
    counts, saturated = isl.normalise((20000, 20000, 20000), range_fs=_RANGE_HIGH_LUX)
    assert counts == (20000, 20000, 20000), "a 16-bit reading must not be shifted as if it were 12-bit"
    assert saturated is False


def test_a_reconciling_re_read_that_itself_fails_is_retried_on_the_following_cycle() -> None:
    # The bus being down is exactly when a write fails, so the re-read that follows is likely to
    # fail too. Recording it as reconciled anyway would drop the torn chip on the floor - the count
    # stays behind instead, which is what makes the next cycle pick it up.
    i2c, reader = ready_reader("reconcile_retry")
    reader._isl._write_failures = 1
    printed: list[tuple[object, ...]] = []
    real_err = reader.pr.err

    def spy(*args: object, sep: str = " ", end: str = "\n") -> None:
        printed.append(args)
        real_err(*args, sep=sep, end=end)

    reader.pr.err = spy  # type: ignore[method-assign]
    with _FastAsyncSleep():
        fake(i2c).inject_fault("readfrom_into", OSError(errno_mod.EIO, "no ACK"), match=_REG_CONFIG1)
        run(reader._verify_config())
    assert reader._reconciled_write_failures == 0, "a failed re-read reconciles nothing"
    assert err_count(run(reader.get_error_counter())) == 0, "a console line, never a persisted entry"
    assert [line[0] for line in printed] == ["Config read-back for reconciliation failed, retried next cycle:"]

    # The following cycle, with the bus back, does the work the failed one could not.
    seed(i2c, _REG_CONFIG1, bytes([_BITS_12, 0x00, 0x00]))  # a chip that disagrees with the shadow
    with _FastAsyncSleep():
        run(reader._verify_config())
    assert reader._reconciled_write_failures == 1
    assert code("W", "ISL_DIVERGED") in warnings(run(reader.get_error_counter()))


def test_a_write_that_fails_during_the_reconciling_re_read_is_not_lost() -> None:
    # Why the reader tracks a COUNT, not a flag. The re-read takes one transaction, and a REST push
    # landing on it can fail too - a flag's clear would wipe that newer failure. The count recorded
    # is the one seen BEFORE the re-read, so a later failure is still ahead of it.
    i2c, reader = ready_reader("reconcile_race")
    chip = fake(i2c)
    reader._isl._write_failures = 1  # one failure already outstanding
    real_read = chip.readfrom_into

    def _fail_a_write_during_the_re_read(address: int, buf: object, stop: bool = True) -> None:  # noqa: FBT001, FBT002  # machine.I2C's own positional stop
        chip.readfrom_into = real_read  # type: ignore[method-assign]  # once only
        reader._isl._write_failures += 1  # a second write fails while this read is in flight
        real_read(address, buf, stop)

    chip.readfrom_into = _fail_a_write_during_the_re_read  # type: ignore[method-assign]
    with _FastAsyncSleep():
        run(reader._verify_config())
    assert reader._reconciled_write_failures == 1, "only what was seen before the re-read counts as reconciled"
    # So the next cycle still has work to do, rather than having had it cleared out from under it.
    assert reader._isl.write_failures() != reader._reconciled_write_failures


def test_a_config_burst_that_lands_only_partly_is_reconciled_by_the_next_read_cycle() -> None:
    # The rollback covers the usual failure - a NAK on the address phase, nothing written. A NAK
    # partway through the burst leaves the chip a mixture, so normalise() scales by the old
    # resolution while the part runs the new one. Only a config GET used to notice.
    i2c, reader = ready_reader("torn_burst")
    chip = fake(i2c)
    real_write = chip.writeto

    def _land_config1_only(address: int, buf: object, stop: bool = True) -> int:  # noqa: FBT001, FBT002  # machine.I2C's own positional stop
        data = bytes(buf)  # type: ignore[call-overload]
        if not stop or len(data) <= 2:
            return real_write(address, buf, stop)
        real_write(address, data[:2], stop)  # the register byte and CONFIG1 land, then the NACK
        raise OSError(errno_mod.EIO, "no ACK on the second byte")

    chip.writeto = _land_config1_only  # type: ignore[method-assign]
    try:
        with _FastAsyncSleep():
            assert run(reader.set_resolution(12)) is False
    finally:
        chip.writeto = real_write  # type: ignore[method-assign]
    # The chip now carries the 12-bit BITS flag the shadow was rolled back out of.
    assert bytes(chip.registers[(_ADDR, _REG_CONFIG1)])[0] & _BITS_12 == _BITS_12

    seed_cycle(i2c, 20000, 20000, 20000)
    with _FastAsyncSleep():
        run(reader._read_isl())
    counters = run(reader.get_error_counter())
    assert code("W", "ISL_DIVERGED") in warnings(counters), "the next read cycle must notice the chip disagreeing"
    assert bytes(chip.registers[(_ADDR, _REG_CONFIG1)])[0] & _BITS_12 == 0, "and put the chip back on the shadow"


def test_the_write_failure_sequence_wraps_and_still_reconciles() -> None:
    # A wrap-by-design sequence compared for equality: at COUNTER_CAP the next failure wraps to 0, and the next
    # read cycle still takes its one snapshot and leaves the two counts level.
    i2c, reader = ready_reader("sequence_wrap")
    reader._isl._write_failures = reader._reconciled_write_failures = asy_base_classes.COUNTER_CAP
    fail_register_writes(i2c, times=1)
    try:
        run(reader._isl.configure(ir_adjust=7))
    except OSError:
        pass
    assert reader._isl.write_failures() == 0
    fake(i2c).log.clear()
    seed_cycle(i2c, 20000, 20000, 20000)
    with _FastAsyncSleep():
        run(reader._read_isl())
    assert register_reads(i2c).count((_REG_CONFIG1, 3)) == 1
    assert reader._isl.write_failures() == reader._reconciled_write_failures


def test_a_corrupted_config_byte_is_found_on_a_cycle_without_a_failed_write() -> None:
    # The snapshot runs every cycle, not only after a failed write: a CONFIG byte changed on the chip with no write
    # of ours is caught on the next cycle, warned once and re-applied; a chip that agrees costs one read, no entry.
    i2c, reader = ready_reader("corrupt_byte")
    seed_cycle(i2c, 20000, 20000, 20000)
    with _FastAsyncSleep():
        run(reader._read_isl())
    assert register_reads(i2c).count((_REG_CONFIG1, 3)) == 1
    assert run(reader.get_error_counter())["ISL29125"]["ErrCount"] == 0
    shadow = reader._isl.encode_shadow()
    seed(i2c, _REG_CONFIG1, bytes([shadow[0] ^ _BITS_12, shadow[1], shadow[2]]))
    fake(i2c).log.clear()
    with _FastAsyncSleep():
        run(reader._read_isl())
    counters = run(reader.get_error_counter())
    assert warnings(counters) == [code("W", "ISL_DIVERGED")]
    assert err_count(counters) == 1
    assert (_REG_CONFIG1, shadow) in register_writes(i2c)
    printed: list[tuple[object, ...]] = []
    real_err = reader.pr.err

    def spy(*args: object, sep: str = " ", end: str = "\n") -> None:
        printed.append(args)
        real_err(*args, sep=sep, end=end)

    reader.pr.err = spy  # type: ignore[method-assign]
    fake(i2c).inject_fault("readfrom_into", OSError(errno_mod.EIO, "no ACK"), match=_REG_CONFIG1)
    fake(i2c).log.clear()
    with _FastAsyncSleep():
        run(reader._read_isl())  # the snapshot fails: a console line, and the cycle goes on
        run(reader._read_isl())  # the next cycle retries it
    assert [line[0] for line in printed] == ["Config read-back for reconciliation failed, retried next cycle:"]
    assert register_reads(i2c).count((_REG_CONFIG1, 3)) == 1


def test_a_failed_config_write_does_not_make_the_divergence_check_see_a_phantom_change() -> None:
    # The same defect seen from the other side: a shadow carrying a value the chip never took makes
    # matches_shadow() report a divergence that is really the driver's own lost write, so the
    # recovery path would re-apply a setting the caller was already told had failed.
    i2c, isl = ready_protocol()
    run(isl.setup())
    on_chip = isl.encode_shadow()
    fail_register_writes(i2c, times=1)
    try:
        run(isl.configure(range_fs=_RANGE_HIGH_LUX, ir_adjust=7))
    except OSError:
        pass
    assert isl.matches_shadow(on_chip) is True


def test_re_deriving_the_transient_rejection_logs_chip_set_when_that_write_fails() -> None:
    # CONFIG3 is a real chip write and fails like any other; the console line names the derived
    # window, so a reader does not look for a bad SampleInterval or Resolution.
    i2c, reader = ready_reader("persist_write_fail")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            fail_register_writes(i2c, times=1)
            assert await reader._reapply_persist(2) is False
        return await reader.get_error_counter()

    assert code("E", "CHIP_SET") in errors(run(scenario()))


def test_set_resolution_reports_failure_when_the_derived_window_cannot_be_re_applied() -> None:
    # The resolution byte itself landed, so this is not a rolled-back write - it is the second half
    # of the same change failing. Reporting True would leave the chip rejecting transients over a
    # window sized for the OLD cycle length, which at 16 -> 12 bit is 16x too long.
    i2c, reader = ready_reader("resolution_persist_fail")
    # inject_fault() queues from the NEXT call, and set_resolution() makes two: the resolution's
    # own CONFIG1 burst first, then the re-derived CONFIG3. Only the second is this test's
    # subject, so the fault is placed by call index rather than by queueing one up front.
    chip = fake(i2c)
    real_write = chip.writeto
    calls = [0]

    def _fail_the_second_write(address: int, buf: object, stop: bool = True) -> int:  # noqa: FBT001, FBT002  # machine.I2C's own positional stop
        if stop and len(buf) > 1:  # type: ignore[arg-type]  # a register write, not a read's pointer
            calls[0] += 1
            if calls[0] == 2:
                raise OSError(errno_mod.EIO, "no ACK")
        return real_write(address, buf, stop)

    chip.writeto = _fail_the_second_write  # type: ignore[method-assign]
    try:
        with _FastAsyncSleep():
            assert run(reader.set_resolution(12)) is False
    finally:
        chip.writeto = real_write  # type: ignore[method-assign]
    assert calls[0] == 2, "the CONFIG1 burst must have landed before the CONFIG3 write failed"



def test_pushing_the_software_knobs_write_only_the_thresholds_they_derive() -> None:
    # AutoRangeThresh moves the chip's down crossing at once; AutoRangeDwell and FiltCoeff are driver state only.
    i2c, reader = ready_reader("push_software")
    with _FastAsyncSleep():
        assert run(_push(reader._push_callbacks["AutoRangeThresh"], 90.0)) is True
        assert run(_push(reader._push_callbacks["AutoRangeDwell"], 30.0)) is True
        assert run(_push(reader._push_callbacks["FiltCoeff"], 0.25)) is True
    assert reader._ar_thresh == 90.0
    assert reader._ar_dwell_s == 30.0
    assert reader._filt_coeff == 0.25
    assert register_writes(i2c) == [(_REG_THRESHOLDS, struct.pack("<HH", ISL29125_I2C.fraction_to_counts(90.0 / _AR_DOWN_DIVISOR), 65535))]


def test_set_autorange_thresh_on_the_low_range_writes_the_up_crossing() -> None:
    i2c, reader = ready_reader("thresh_low")
    with _FastAsyncSleep():
        assert run(reader._switch_range(_RANGE_LOW_LUX)) is True
        fake(i2c).log.clear()
        assert run(reader.set_autorange_thresh(90.0)) is True
    assert register_writes(i2c) == [(_REG_THRESHOLDS, struct.pack("<HH", 0, ISL29125_I2C.fraction_to_counts(90.0)))]


def test_a_failed_threshold_write_leaves_the_cached_threshold() -> None:
    # The cache changes only once the chip took the value, so a failed push's recovery restores a consistent pair.
    i2c, reader = ready_reader("thresh_fail")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            fail_register_writes(i2c, times=1)
            assert await reader.set_autorange_thresh(90.0) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    assert reader._ar_thresh == 85.0
    assert errors(counters) == [code("E", "CHIP_SET")]


def test_set_resolution_rescales_the_thresholds_with_auto_range_off() -> None:
    # The registers compare the RAW ADC value, so a resolution change rescales them armed or not: arming later
    # never runs on a wrong-scale window.
    i2c, reader = ready_reader("thresh_rescale")
    with _FastAsyncSleep():
        assert run(reader.set_range_auto(flag=False)) is True
        fake(i2c).log.clear()
        assert run(reader.set_resolution(12)) is True
    assert _threshold_bursts(i2c) == [struct.pack("<HH", ISL29125_I2C.fraction_to_counts(85.0 / _AR_DOWN_DIVISOR) >> 4, 4095)]


def test_pushing_the_sample_interval_re_derives_the_transient_rejection() -> None:
    # A consequence of deriving PRST: SampleInterval stopped being a software-only knob. At 16 bit a
    # 1s interval affords 2 cycles and a 7s one 8, so this push must reach the chip - updating only
    # the timer would leave the part rejecting less transient noise than the interval allows.
    i2c, reader = ready_reader("push_interval")
    assert reader._isl._persist == 2  # derived at init from the 1s default
    with _FastAsyncSleep():
        assert run(_push(reader._push_callbacks["SampleInterval"], 7)) is True
    assert run(reader._trigger_period.get_value()) == 7
    assert reader._isl._persist == 8
    writes = register_writes(i2c)
    assert any(w[0] == _REG_CONFIG2 and w[1][1] & 0x0C == 0x0C for w in writes), "the new PRST has to reach CONFIG3"


def test_the_down_point_is_derived_from_the_threshold_and_cannot_be_set() -> None:
    # There is exactly one correct hysteresis gap for a given switch-up point, so the field that
    # used to let a user get it wrong is gone along with the cross-field rule that policed it.
    # Moving the threshold moves the down point in the same call: the two cannot disagree at all.
    _i2c, reader = ready_reader("derived_down")

    async def scenario() -> None:
        assert abs(reader._down_thresh() - 85.0 / _AR_DOWN_DIVISOR) < 1e-12
        assert await reader.set_autorange_thresh(50.0) is True
        assert abs(reader._down_thresh() - 50.0 / _AR_DOWN_DIVISOR) < 1e-12
        assert await reader.set_autorange_thresh(95.0) is True
        assert abs(reader._down_thresh() - 95.0 / _AR_DOWN_DIVISOR) < 1e-12

    run(scenario())
    assert "AutoRangeDown" not in reader._push_callbacks
    assert not hasattr(reader, "set_autorange_down")
    assert not hasattr(reader, "_check_cross_field")


def test_turning_autorange_off_writes_intsel_zero_and_applies_the_stored_range() -> None:
    # Parking the thresholds cannot disarm the interrupt: the part fires on "below OR EQUAL TO"
    # the low threshold, so a low threshold of 0x0000 still interrupts in total darkness.
    i2c, reader = ready_reader("auto_off")
    with _FastAsyncSleep():
        assert run(reader.set_range(_RANGE_LOW_LUX)) is True
        assert run(reader.set_range_auto(flag=False)) is True
    config1, _config2, config3 = register_writes(i2c)[-1][1]
    assert config3 & 0x03 == 0x00  # INTSEL = "No Interrupt"
    assert config1 & _RNG_HIGH == 0  # the stored fixed range applied
    assert reader._active_range == _RANGE_LOW_LUX


def test_turning_autorange_back_on_rearms_intsel_and_the_thresholds() -> None:
    i2c, reader = ready_reader("auto_on")
    with _FastAsyncSleep():
        run(reader.set_range_auto(flag=False))
        fake(i2c).log.clear()
        assert run(reader.set_range_auto(flag=True)) is True
    writes = register_writes(i2c)
    assert any(register == _REG_THRESHOLDS for register, _payload in writes)
    config = next(payload for register, payload in writes if register in (_REG_CONFIG1, _REG_CONFIG2))
    assert config[-1] & 0x03 == _INTSEL_GREEN


def test_turning_autorange_off_logs_chip_set_when_that_write_fails() -> None:
    i2c, reader = ready_reader("auto_off_fail")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            fail_register_writes(i2c, times=1)
            assert await reader.set_range_auto(flag=False) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    assert code("E", "CHIP_SET") in errors(counters)


def test_a_failed_autorange_mode_write_leaves_the_live_flag_where_the_config_still_says() -> None:
    # The one setter that caches a config value in RAM *and* writes to the chip. _recover_failed_push
    # rolls the persisted value back when a push reports False, so caching regardless would leave the
    # reader auto-ranging against a config that says it is not - invisible until the next restart.
    i2c, reader = ready_reader("auto_off_flag")

    async def scenario() -> None:
        with _FastAsyncSleep():
            fail_register_writes(i2c, times=1)
            assert await reader.set_range_auto(flag=False) is False

    run(scenario())
    assert reader._range_auto is True


def test_setting_range_while_autorange_is_on_stores_the_preference_without_a_chip_write() -> None:
    i2c, reader = ready_reader("range_pref")
    with _FastAsyncSleep():
        assert run(reader.set_range(_RANGE_LOW_LUX)) is True
    assert reader._fixed_range == _RANGE_LOW_LUX
    assert reader._active_range == _RANGE_HIGH_LUX  # the state machine still owns the chip
    assert register_writes(i2c) == []


def test_set_range_rejects_a_value_outside_the_two_real_ranges() -> None:
    _i2c, reader = ready_reader("range_bad")

    async def scenario() -> "ErrorLog":
        assert await reader.set_range(5000) is False
        return await reader.get_error_counter()

    assert code("E", "CHIP_SET") in errors(run(scenario()))


def test_set_trigger_s_refuses_bad_values_with_bad_arg_and_never_raises() -> None:
    _i2c, reader = make_reader("trigger_bad")

    async def scenario() -> "ErrorLog":
        assert await reader.set_trigger_s("not-a-number") is False  # type: ignore[arg-type]
        assert await reader.set_trigger_s(float("inf")) is False  # OverflowError, not ValueError
        assert await reader.set_trigger_s(0) is False
        assert await reader.set_trigger_s(3601) is False
        assert await reader.set_trigger_s(30) is True
        return await reader.get_error_counter()

    counters = run(scenario())
    # One event per rejected value, one slot: a non-number, +inf, and both out-of-range ends.
    assert err_count(counters) == 4
    assert errors(counters)[-1] == code("E", "BAD_ARG")
    assert run(reader._trigger_period.get_value()) == 30


def test_every_hardware_setter_logs_chip_set_on_a_bus_fault() -> None:
    # Numbers name the failure class; the console line names the field.
    expected = {"set_resolution": 12, "set_ir_comp_offset": 1, "set_ir_comp_adjust": 63}
    for method, argument in expected.items():
        i2c, reader = ready_reader("setter_" + method)

        async def scenario(
            method: str = method, argument: int = argument, i2c: I2C = i2c, reader: ISL29125_Reader = reader,
        ) -> "ErrorLog":
            with _FastAsyncSleep():
                fake(i2c).nak_addresses.add(_ADDR)
                assert await getattr(reader, method)(argument) is False
            return await reader.get_error_counter()

        counters = run(scenario())
        assert errors(counters)[-1] == code("E", "CHIP_SET"), method


def test_every_getter_logs_chip_get_and_returns_none_on_a_bus_fault() -> None:
    # Numbers name the failure class; the console line names the field.
    for method in ("get_resolution", "get_range", "get_ir_comp_offset", "get_ir_comp_adjust"):
        i2c, reader = ready_reader("getter_" + method)

        async def scenario(method: str = method, i2c: I2C = i2c, reader: ISL29125_Reader = reader) -> "ErrorLog":
            with _FastAsyncSleep():
                fake(i2c).nak_addresses.add(_ADDR)
                assert await getattr(reader, method)() is None
            return await reader.get_error_counter()

        counters = run(scenario())
        assert errors(counters)[-1] == code("E", "CHIP_GET"), method


def test_the_getters_read_the_live_chip_not_the_shadow() -> None:
    i2c, reader = ready_reader("getters_live")
    with _FastAsyncSleep():
        seed(i2c, _REG_CONFIG1, bytes([_MODE_RGB | _BITS_12, 0x80 | 7, _INTSEL_GREEN | 0x04]))
        assert run(reader.get_resolution()) == 12
        assert run(reader.get_range()) == _RANGE_LOW_LUX
        assert run(reader.get_ir_comp_offset()) == 1
        assert run(reader.get_ir_comp_adjust()) == 7


def test_a_failed_push_recovers_through_the_getter_then_the_snapshot_then_the_default() -> None:
    # _recover_failed_push()'s own chain: a live read-back first, then the pre-write snapshot,
    # then the schema default - and every rung it accepts is validated against the schema, so a
    # misbehaving chip cannot get an out-of-schema value persisted.
    i2c, reader = ready_reader("recover")

    async def scenario() -> "dict[str, Any]":
        with _FastAsyncSleep():
            real_configure = reader._isl.configure

            async def failing(**_kwargs: object) -> None:
                raise OSError(errno_mod.EIO, "injected")

            reader._isl.configure = failing  # type: ignore[method-assign]
            # The chip reads back a resolution the schema accepts, so recovery uses it.
            seed(i2c, _REG_CONFIG1, bytes([_MODE_RGB | _BITS_12, 0x00, 0x00]))
            results = await reader._set_dict_cfg({"Resolution": 12}, reader.get_cfg_schema())
            reader._isl.configure = real_configure  # type: ignore[method-assign]
            stored = await reader.cfgmgr.get_dict(["Resolution"])
        assert results["Resolution"] == "Failed"
        assert stored is not None
        return stored

    assert run(scenario())["Resolution"] == 12


def test_a_getter_returning_an_out_of_schema_value_is_rejected_by_the_recovery_chain() -> None:
    _i2c, reader = ready_reader("recover_bad")

    async def scenario() -> "dict[str, Any]":
        with _FastAsyncSleep():
            async def failing(**_kwargs: object) -> None:
                raise OSError(errno_mod.EIO, "injected")

            async def nonsense() -> int:
                return 999  # neither 12 nor 16

            reader._isl.configure = failing  # type: ignore[method-assign]
            reader._get_callbacks["Resolution"] = nonsense
            await reader._set_dict_cfg({"Resolution": 12}, reader.get_cfg_schema())
            stored = await reader.cfgmgr.get_dict(["Resolution"])
        assert stored is not None
        return stored

    assert run(scenario())["Resolution"] == 16  # the pre-write snapshot, not the chip's nonsense


def test_starting_a_calibration_returns_valid_twice_in_a_row() -> None:
    # A run that later finds no usable scene has not FAILED - returning False would run
    # _recover_failed_push() on a field that cannot be recovered.
    _i2c, reader = ready_reader("calibrate_twice")

    async def scenario() -> "list[Any]":
        with _FastAsyncSleep():
            first = await reader._set_dict_cfg({"Calibrate": True}, reader.get_cfg_schema())
            second = await reader._set_dict_cfg({"Calibrate": True}, reader.get_cfg_schema())
        return [first["Calibrate"], second["Calibrate"]]

    assert run(scenario()) == ["Valid", "Valid"]


# ---------------------------------------------------------------------------
# Gain-ratio calibration - R12-R15
# ---------------------------------------------------------------------------


def test_the_gain_correction_is_one_on_the_low_range_and_applied_over_nominal_on_the_high_one() -> None:
    # The LOW range is the reference, so the applied ratio only ever corrects the high one -
    # correcting both would make the absolute scale drift with the calibration.
    _i2c, reader = make_reader("gain_direction")
    reader._gain_ratio = 25.9
    assert reader._gain_correction(_RANGE_LOW_LUX) == 1.0
    assert abs(reader._gain_correction(_RANGE_HIGH_LUX) - 25.9 / _GAIN_RATIO_NOMINAL) < 1e-9
    # A unit whose real high-range full scale EXCEEDS nominal produces fewer counts for the same
    # light, so the reported lux has to be scaled UP - the direction this assertion pins.
    reader._gain_ratio = 30.0
    assert reader._gain_correction(_RANGE_HIGH_LUX) > 1.0


# ---------------------------------------------------------------------------
# _trigger_loop() - the shared 1 Hz base tick divided down by the sample interval (SPECIFICATION.md C.9)
# ---------------------------------------------------------------------------


def test_base_trigger_produces_one_read_event_per_sample_interval() -> None:
    _i2c, reader = make_reader("divider")

    async def scenario() -> int:
        await reader.set_trigger_s(3)
        fired = 0
        task = reader.start_asy_trigger()
        for _ in range(9):
            reader._base_trigger_event.set()
            for _ in range(5):
                await asyncio.sleep(0)
            if _drain_flag(reader._read_event):
                fired += 1
        await _cancel_and_join(task)
        return fired

    assert run(scenario()) == 3


async def _cancel_and_join(task: "asyncio.Task[Any]") -> None:
    # Cancelling alone is not enough for a task parked on ThreadSafeFlag.wait(): the await is what
    # unwinds the cancellation through wait() and UNREGISTERS its poll object. Leaked registrations
    # grow asyncio's pollfds array and segfault the process (SPECIFICATION.md F.7 row 12).
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def _drain_flag(flag: "asyncio.ThreadSafeFlag") -> bool:
    # Reads ThreadSafeFlag's own state and clears it: a wait_for_ms() probe registers a poll object
    # per call (SPECIFICATION.md F.7 row 12).
    was_set = bool(flag.state)
    flag.clear()
    return was_set


def test_changing_the_sample_interval_takes_effect_on_the_next_boundary() -> None:
    _i2c, reader = make_reader("divider_live")

    async def scenario() -> "list[int]":
        await reader.set_trigger_s(2)
        fired = []
        task = reader.start_asy_trigger()
        for tick in range(4):
            reader._base_trigger_event.set()
            for _ in range(5):
                await asyncio.sleep(0)
            if _drain_flag(reader._read_event):
                fired.append(tick)
            if tick == 1:
                await reader.set_trigger_s(1)
        await _cancel_and_join(task)
        return fired

    assert run(scenario()) == [1, 2, 3]


def test_the_timer_and_the_falling_edge_irq_both_reach_the_read_event() -> None:
    _i2c, reader = make_reader("wiring")
    reader.start_timer()
    timer = reader._trigger_timer
    assert timer.period == 1000
    assert reader.irq_pin._irq_trigger == FakePin.IRQ_FALLING  # active-low, open-drain (p6)

    async def scenario() -> "tuple[bool, bool]":
        assert timer.callback is not None
        timer.callback(timer)  # one hardware tick
        from_timer = _drain_flag(reader._base_trigger_event)
        reader.irq_pin.trigger_irq()  # one real falling edge
        from_irq = _drain_flag(reader._read_event)
        return from_timer, from_irq

    assert run(scenario()) == (True, True)


def test_start_timer_degrades_when_the_alarm_pool_is_exhausted() -> None:
    for exc in (OSError, MemoryError):
        _i2c, reader = make_reader("timer_" + exc.__name__)
        with _RaiseOnArm(exc):
            reader.start_timer()  # must not raise
        # The IRQ is still wired even though the timer could not arm - the interrupt path is
        # independent of the divider, which is what requirement 17 relies on in reverse.
        assert reader.irq_pin._irq_handler is not None
        assert _drain_flag(reader._base_trigger_event) is True, "the waiting task must be woken to report it"


def test_a_failed_trigger_arm_ends_the_trigger_task_with_one_timer_entry_and_a_restart_rearms() -> None:
    # The woken divider persists the failure once and ends; its restart re-arms the timer, whose tick drives a read.
    for exc in (OSError, MemoryError):
        _i2c, reader = make_reader("timer_task_" + exc.__name__)
        armed_before = len(FakeTimer.all_timers)

        async def scenario(reader: ISL29125_Reader = reader, exc: "type[BaseException]" = exc) -> "tuple[bool, ErrorLog, bool]":
            task = reader.start_asy_trigger()  # parked on the base tick when the arm fails
            await asyncio.sleep(0)
            with _RaiseOnArm(exc):
                reader.start_timer()
            for _ in range(10):
                await asyncio.sleep(0)
            ended = task.done()
            counters = await reader.get_error_counter()
            await reader.set_trigger_s(1)
            restarted = reader.start_asy_trigger()
            for _ in range(5):
                await asyncio.sleep(0)
            timer = reader._trigger_timer
            assert timer.callback is not None
            timer.callback(timer)  # one hardware tick
            for _ in range(5):
                await asyncio.sleep(0)
            fired = _drain_flag(reader._read_event)
            await _cancel_and_join(restarted)
            return ended, counters, fired

        ended, counters, fired = run(scenario())
        assert ended is True, exc
        assert errors(counters) == [code("E", "TIMER")], exc
        assert err_count(counters) == 1
        assert reader._trigger_timer.period == 1000
        assert fired is True, exc
        assert len(FakeTimer.all_timers) == armed_before  # re-armed in place, no second Timer


def test_stop_timer_deinits_the_real_timer() -> None:
    _i2c, reader = make_reader("timer_stop")
    reader.start_timer()
    reader.stop_timer()
    assert reader._trigger_timer.deinit_called is True


def test_task_and_trigger_starters_are_registered() -> None:
    _i2c, reader = make_reader("starters")
    assert [fn.__name__ for fn in reader.get_task_starters()] == ["start_asy_read", "start_asy_trigger"]
    assert [fn.__name__ for fn in reader.get_trigger_starters()] == ["start_timer"]
    assert reader.get_timer_starters() == []


def test_get_data_returns_the_all_none_namedtuple_before_the_first_read() -> None:
    _i2c, reader = make_reader("predata")
    data = run(reader.get_data())
    assert isinstance(data, ISL29125)
    assert data == ISL29125(*(None,) * 13)


# ---------------------------------------------------------------------------
# Paths that ran but were never asserted on
# ---------------------------------------------------------------------------


def _threshold_bursts(i2c: I2C) -> "list[bytes]":
    return [payload for register, payload in register_writes(i2c) if register == _REG_THRESHOLDS]


def test_a_diverged_configuration_re_arms_the_range_thresholds_too() -> None:
    # configure(force=True) rewrites CONFIG1-3 and nothing else, but the threshold registers are
    # separate and a brownout or stray write zeroes them just the same. Without the re-arm the
    # recovery leaves a correctly configured chip whose fast path never fires again.
    i2c, reader = ready_reader("divergence_thresholds")

    async def scenario() -> None:
        with _FastAsyncSleep():
            shadow = reader._isl.encode_shadow()
            seed(i2c, _REG_CONFIG1, bytes([shadow[0] & ~0x07, shadow[1], shadow[2]]))  # mode zeroed
            fake(i2c).log.clear()
            await reader._read_sensor_dict()

    run(scenario())
    assert _threshold_bursts(i2c) != [], "the recovery left the threshold registers as the fault found them"


def test_a_failed_re_apply_after_divergence_logs_chip_set_and_stops_there() -> None:
    # The other end of the same path: if the re-apply itself fails there is nothing to re-arm the
    # thresholds against, and writing them anyway would arm a configuration that never landed.
    i2c, reader = ready_reader("divergence_reapply_fails")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            shadow = reader._isl.encode_shadow()
            seed(i2c, _REG_CONFIG1, bytes([shadow[0] & ~0x07, shadow[1], shadow[2]]))

            async def failing_configure(**_kwargs: object) -> None:
                raise OSError(errno_mod.EIO, "injected")

            reader._isl.configure = failing_configure  # type: ignore[method-assign]
            fake(i2c).log.clear()
            await reader._read_sensor_dict()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert code("E", "CHIP_SET") in errors(counters)
    assert _threshold_bursts(i2c) == [], "thresholds were armed against a configuration that never landed"


def test_a_warm_scene_reports_a_lower_colour_temperature_than_a_cool_one() -> None:
    # Every other CCT assertion in this file is None-vs-not-None, which a swapped channel index in
    # the rgb_to_xyz() call would sail straight through - the driver passes norm[1], norm[0],
    # norm[2] to put RED first, and getting that wrong still yields a plausible-looking number.
    i2c, reader = ready_reader("cct_order")

    # Mildly tinted on purpose: a strongly saturated scene leaves McCamy's valid domain, where
    # cct_mccamy() returns None and is right to - that is a property of the formula, not a fault,
    # and it would turn this into a None-vs-None comparison that proves nothing.
    async def scenario() -> "tuple[float | None, float | None]":
        with _FastAsyncSleep():
            seed_cycle(i2c, 19660, 22937, 16384)  # green, RED-leaning, blue
            await reader._store_isl(await reader._read_isl())
            warm = (await reader.get_data()).CCT
            seed_cycle(i2c, 19660, 16384, 22937)  # green, red, BLUE-leaning
            await reader._store_isl(await reader._read_isl())
            cool = (await reader.get_data()).CCT
        return warm, cool

    warm, cool = run(scenario())
    assert warm is not None and cool is not None, f"both scenes must be inside McCamy's domain: {warm}, {cool}"
    assert warm < cool, f"a red-dominant scene reported {warm:.0f}K against {cool:.0f}K for a blue-dominant one"


def test_a_failed_status_read_drops_the_whole_sample_without_storing_or_raising() -> None:
    # The status read is the first bus transaction of the cycle and its own code, separate from a
    # data-read failure. A sample must not be invented from registers that were never read.
    i2c, reader = ready_reader("status_fail")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            async def failing_status() -> int:
                raise OSError(errno_mod.EIO, "injected")

            reader._isl.read_status = failing_status  # type: ignore[method-assign]
            results = await reader._read_isl()
            assert results == (None, None, None, None, None, None)
            await reader._store_isl(results)
        return await reader.get_error_counter()

    counters = run(scenario())
    assert code("E", "ISL_STATUS_READ") in errors(counters)
    assert run(reader.get_data()).Lux is None, "a sample was stored from a cycle whose status read never succeeded"
    assert _threshold_bursts(i2c) == [], "the range was evaluated on data that was never read"


def test_the_filter_coefficient_rejects_values_outside_its_band_with_bad_arg() -> None:
    # The setter owns the verdict even though it stores nothing - a False here is what makes
    # _set_dict_cfg() report the field "Failed" instead of silently accepting an unusable value.
    _i2c, reader = ready_reader("filter_reject")

    async def scenario() -> "ErrorLog":
        assert await reader.set_filter_coefficient(-1.0) is True  # the "off" sentinel, in band
        assert await reader.set_filter_coefficient(1.0) is True  # the other boundary, inclusive
        assert await reader.set_filter_coefficient(-1.01) is False
        assert await reader.set_filter_coefficient(1.01) is False
        assert await reader.set_filter_coefficient(float("nan")) is False  # every comparison False
        assert await reader.set_filter_coefficient("nope") is False  # type: ignore[arg-type]
        return await reader.get_error_counter()

    counters = run(scenario())
    assert err_count(counters) == 4, "one event per rejected value; the two boundaries add none"
    assert errors(counters)[-1] == code("E", "BAD_ARG")


def test_the_read_loop_stores_healthy_samples_and_gives_up_once_the_budget_is_spent() -> None:
    # _read_loop() IS the coroutine asy_system_service.py's supervisor runs, and its return ending the task is
    # the restart contract. Every other test in this file drives _read_isl()/_error_check()
    # directly, so the loop that wires them together - and both of its exits - never ran.
    i2c, reader = make_reader("loop_contract", max_module_error=2)
    stored: list[ISLResults] = []
    healthy = [0]

    async def scenario() -> bool:
        real_store, real_read = reader._store_isl, reader._read_isl

        async def counting_store(results: "ISLResults") -> None:
            stored.append(results)
            await real_store(results)

        async def ready() -> None:
            return  # the timer divider and the INT pin are both tested on their own

        async def two_good_then_broken() -> "ISLResults":
            reader._unsettled_cycle = False  # as the real _read_isl() starts every cycle
            if healthy[0] < 2:
                healthy[0] += 1
                reader._isl._settle_until_ms = time.ticks_ms()  # no wall clock passes in this test
                return await real_read()
            if healthy[0] == 2:
                healthy[0] += 1
                fake(i2c).log.clear()  # from here on the bus log holds the rung's writes alone
            return None, None, None, None, None, None

        with _FastAsyncSleep():
            seed(i2c, _REG_CONFIG1, bytes(3))
            seed_cycle(i2c, 20000, 20000, 20000)
            reader._read_event.wait = ready  # type: ignore[method-assign]
            reader._store_isl = counting_store  # type: ignore[method-assign]
            reader._read_isl = two_good_then_broken  # type: ignore[method-assign]
            await reader._read_loop()
            return True

    assert run(scenario()) is True, "a spent error budget must end the task so the supervisor restarts it"
    # Every cycle inside the budget reaches _store_isl, failing ones included - it is _store_isl
    # that discards an all-None result, not the loop. What matters is that exactly the healthy
    # cycles carried data through, and that the reader really published one.
    assert sum(1 for entry in stored if entry[0] is not None) == 2, f"healthy cycles that reached the store: {stored}"
    assert run(reader.get_data()).Lux is not None, "the loop never published a reading"
    # The 2nd failed cycle ran the participant rung: the healthy chip takes one CONFIG1-3 burst from the shadow.
    assert [payload for register, payload in register_writes(i2c) if register == _REG_CONFIG1] == [reader._isl.encode_shadow()]
    counters = run(reader.get_error_counter())
    assert warnings(counters) == [code("W", "DEVICE_RECOVERY")]
    assert errors(counters)[-1] == code("E", "GIVE_UP")


def test_the_read_loop_gives_up_immediately_when_the_chip_is_not_there_at_all() -> None:
    # The other exit: a failed init returns False WITHOUT entering the loop. Getting this wrong
    # parks the task forever on _read_event.wait() against a chip that never answers - a silently
    # dead sensor that the supervisor cannot see, because the task never ends.
    i2c, reader = make_reader("loop_init_fail", healthy=False)
    fake(i2c).nak_addresses.add(_ADDR)
    entered = [0]

    async def scenario() -> None:
        async def counted_wait() -> None:
            entered[0] += 1

        with _FastAsyncSleep():
            reader._read_event.wait = counted_wait  # type: ignore[method-assign]
            await reader._read_loop()

    run(scenario())
    assert entered[0] == 0, "the loop was entered despite the init having failed"
    counters = run(reader.get_error_counter())
    assert code("E", "INIT") in errors(counters)
    assert warnings(counters) == [code("W", "BUS_RECOVERY")]


def test_two_failed_status_reads_reapply_the_shadow_and_rearm_the_thresholds() -> None:
    # The participant rung with no brownout: the 2nd failed cycle writes CONFIG1-3 from the shadow and re-arms the
    # thresholds for the active range, one DEVICE_RECOVERY warning.
    i2c, reader = ready_reader("rung_status")
    seed_cycle(i2c, 20000, 20000, 20000)
    fake(i2c).inject_fault("readfrom_into", OSError(errno_mod.EIO, "no ACK"), times=2, match=_REG_STATUS)
    with _FastAsyncSleep():
        for _ in range(2):
            results = run(reader._read_isl())
            assert run(reader._error_check(results, condition=results[0] is None)) is True
    assert [payload for register, payload in register_writes(i2c) if register == _REG_CONFIG1] == [reader._isl.encode_shadow()]
    assert _threshold_bursts(i2c) == [struct.pack("<HH", 1044, 65535)]
    assert warnings(run(reader.get_error_counter())) == [code("W", "DEVICE_RECOVERY")]


def test_a_raising_reapply_burst_logs_one_chip_set_and_no_recovery_warning() -> None:
    # A failed rung is its own one entry: the re-apply's CHIP_SET, no "done" warning and no threshold write.
    i2c, reader = ready_reader("rung_fails")
    seed_cycle(i2c, 20000, 20000, 20000)
    fake(i2c).inject_fault("readfrom_into", OSError(errno_mod.EIO, "no ACK"), times=2, match=_REG_STATUS)
    with _FastAsyncSleep():
        results = run(reader._read_isl())
        assert run(reader._error_check(results, condition=results[0] is None)) is True
        fail_register_writes(i2c, times=1)
        results = run(reader._read_isl())
        assert run(reader._error_check(results, condition=results[0] is None)) is True
    counters = run(reader.get_error_counter())
    assert errors(counters)[-1] == code("E", "CHIP_SET")
    assert warnings(counters) == []
    assert _threshold_bursts(i2c) == []


def test_an_unsettled_cycle_is_no_failure() -> None:
    # A stream of CONFIG1 writes holding the settle open past the bound: the cycle is discarded - nothing published,
    # no streak step (max_module_error=1 would end the task on a second count) - and the next completed cycle publishes.
    i2c, reader = make_reader("unsettled", max_module_error=1)
    seed_cycle(i2c, 20000, 20000, 20000)
    keep_extending = [True]
    real_sleep_ms = asyncio.sleep_ms

    async def extending(_ms: int) -> None:
        if keep_extending[0]:
            reader._isl._settle_until_ms = time.ticks_add(time.ticks_ms(), 500)
        await real_sleep_ms(0)

    async def scenario() -> "tuple[bool, ISL29125]":
        with _FastAsyncSleep():
            asyncio.sleep_ms = extending  # type: ignore[assignment]  # _FastAsyncSleep restores the real one
            seed(i2c, _REG_CONFIG1, bytes(3))
            task = reader.start_asy_read()
            for _ in range(40):
                await asyncio.sleep(0)
            for _ in range(3):
                reader._isl._settle_until_ms = time.ticks_add(time.ticks_ms(), 500)
                reader._read_event.set()
                for _ in range(40):
                    await asyncio.sleep(0)
            running = not task.done()
            discarded = await reader.get_data()
            keep_extending[0] = False
            reader._isl._settle_until_ms = time.ticks_ms()
            reader._read_event.set()
            for _ in range(40):
                await asyncio.sleep(0)
            await _cancel_and_join(task)
        return running, discarded

    running, discarded = run(scenario())
    assert running is True
    assert discarded.Lux is None, "a cycle past the settle bound published a sample"
    assert reader._err_cnt_internal == 0
    assert run(reader.get_data()).Lux is not None, "the settled cycle did not publish"


def test_every_protocol_read_raises_when_layer_one_answers_none_instead_of_raising() -> None:
    # Layer 1 answers None for a bus it cannot use; each protocol read raises instead, so a caller's
    # error path sees one shape. reset() is listed because its verify read IS the settle.
    for call in ("get_device_id", "read_status", "get_config_snapshot", "read_counts", "reset"):
        _i2c, isl = ready_protocol()

        async def silent_none(*_args: object, **_kwargs: object) -> None:
            return None

        isl._i2c_isl29125.i2c_device.get_register_bytes = silent_none  # type: ignore[method-assign]
        try:
            run(getattr(isl, call)())
        except OSError:
            continue
        raise AssertionError(f"{call}() passed layer 1's None straight through instead of raising")


def test_the_config_decoder_survives_an_answer_that_is_not_bytes_at_all() -> None:
    # Same contract seen from the decoder: it is handed whatever layer 1 produced, and len() on a
    # non-sequence raises TypeError rather than returning a wrong length.
    assert ISL29125_I2C.decode_config(None) is None
    assert ISL29125_I2C.decode_config(b"\x01\x02") is None  # right type, wrong length
    assert ISL29125_I2C.decode_config(5) is None  # type: ignore[arg-type]


def test_pinning_a_range_while_autorange_is_off_actually_programs_the_chip() -> None:
    # With auto ON the stored Range is only a preference - the state machine owns the RNG bit. The
    # moment auto is OFF the same field has to reach CONFIG1, or the user pins a range the part
    # never adopts and every later reading is scaled by the range it is still really on.
    i2c, reader = ready_reader("fixed_range")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            assert await reader.set_range(_RANGE_LOW_LUX) is True  # auto still on: preference only
            assert reader._active_range == _RANGE_HIGH_LUX, "the RNG bit moved while auto-range owned it"
            assert await reader._push_callbacks["RangeAuto"](False) is True
            fake(i2c).log.clear()
            assert await reader._push_callbacks["Range"](_RANGE_HIGH_LUX) is True
            assert reader._active_range == _RANGE_HIGH_LUX
            assert any(register == _REG_CONFIG1 for register, _payload in register_writes(i2c)), "the pinned range never reached CONFIG1"
            fake(i2c).nak_addresses.add(_ADDR)
            assert await reader.set_range(_RANGE_LOW_LUX) is False
            assert await reader.set_range(999) is False  # not one of the two real full scales
        return await reader.get_error_counter()

    counters = run(scenario())
    assert err_count(counters) == 2
    assert errors(counters)[-1] == code("E", "CHIP_SET")


def test_the_two_remaining_auto_range_knobs_reject_out_of_range_values_with_bad_arg() -> None:
    # Both are pure software knobs with no chip write, so a rejected value has to be caught here
    # or it silently becomes the live policy - a negative dwell removes the asymmetry that stops
    # the range chattering, and a threshold below its floor leaves no headroom before saturation.
    _i2c, reader = ready_reader("knob_reject")

    async def scenario() -> "ErrorLog":
        assert await reader.set_autorange_thresh(50.0) is True  # the low boundary, inclusive
        assert await reader.set_autorange_thresh(95.0) is True  # the high boundary, inclusive
        assert await reader.set_autorange_thresh(49.9) is False
        assert await reader.set_autorange_thresh(95.1) is False
        assert await reader.set_autorange_thresh("x") is False  # type: ignore[arg-type]
        assert await reader.set_autorange_dwell(0.0) is True
        assert await reader.set_autorange_dwell(300.0) is True
        assert await reader.set_autorange_dwell(-0.1) is False
        assert await reader.set_autorange_dwell(float("inf")) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    assert err_count(counters) == 5, "one event per rejected value; neither boundary adds one"
    assert errors(counters)[-1] == code("E", "BAD_ARG")
    assert reader._ar_thresh == 95.0, "a rejected value must not disturb the last good one"
    assert reader._ar_dwell_s == 300.0


def test_an_out_of_band_knob_is_rejected_by_the_schema_rung_not_the_setter() -> None:
    # WHICH rung rejects it is the point, not just that it is rejected. "Invalid" means the schema bound
    # caught it and the value never reached the driver; "Failed" would mean the setter ran and refused,
    # which for a pure software knob leaves the live policy momentarily reachable with an unvalidated value.
    #
    # The test above pins the setter's own guard; this pins that _set_dict_cfg never gets that far. Neither
    # implies the other.
    _i2c, reader = ready_reader("knob_rung")

    async def scenario() -> "list[Any]":
        with _FastAsyncSleep():
            low = await reader._set_dict_cfg({"AutoRangeThresh": 20.0}, reader.get_cfg_schema())
            good = await reader._set_dict_cfg({"AutoRangeThresh": 60.0}, reader.get_cfg_schema())
            dwell = await reader._set_dict_cfg({"AutoRangeDwell": -5.0}, reader.get_cfg_schema())
        return [low["AutoRangeThresh"], good["AutoRangeThresh"], dwell["AutoRangeDwell"]]

    assert run(scenario()) == ["Invalid", "Valid", "Invalid"]
    assert reader._ar_thresh == 60.0, "the accepted value is the one that must be live afterwards"


# ---------------------------------------------------------------------------
# The hardware driver's own field guard, and the reader's coercion policy
# ---------------------------------------------------------------------------


def test_configure_rejects_a_field_the_chip_cannot_take_instead_of_masking_it() -> None:
    # The whole point of the guard: encode_shadow() masks every field to its own bit width, so
    # an IRCompAdjust of 200 would otherwise be written to the chip as 200 & 0x3F = 8 and
    # reported as a success. Nothing may reach the bus on a rejected value.
    i2c, isl = ready_protocol()
    run(isl.setup())
    fake(i2c).log.clear()
    for kwargs in (
        {"resolution": 8},
        {"range_fs": 5000},
        {"ir_offset": 2},
        {"ir_adjust": 200},
        {"ir_adjust": -1},
        {"persist": 3},
        # An integral float compares EQUAL to the value it shadows, so every one of these passes a
        # membership or bounds test and then meets encode_shadow()'s bitwise masking, where a
        # float raises TypeError out of a function documented as unable to raise.
        {"resolution": 12.0},
        {"range_fs": 375.0},
        {"ir_offset": 0.0},
        {"ir_adjust": 40.5},
        {"ir_adjust": 40.0},
        {"persist": 2.0},
    ):
        raised = False
        try:
            run(isl.configure(**kwargs))  # deliberately out of contract
        except ValueError:
            raised = True
        assert raised, f"configure({kwargs}) must raise, not mask"
    assert register_writes(i2c) == [], "a rejected field must not reach the bus at all"


def test_configure_accepts_every_value_the_datasheet_does_allow() -> None:
    # The other side of the guard, so it cannot be satisfied by rejecting everything.
    _i2c, isl = ready_protocol()
    run(isl.setup())
    for kwargs in (
        {"resolution": 12}, {"resolution": 16},
        {"range_fs": _RANGE_LOW_LUX}, {"range_fs": _RANGE_HIGH_LUX},
        {"ir_offset": 0}, {"ir_offset": 1},
        {"ir_adjust": 0}, {"ir_adjust": 63},
        {"persist": 1}, {"persist": 2}, {"persist": 4}, {"persist": 8},
    ):
        run(isl.configure(**kwargs))  # type: ignore[arg-type]  # one keyword per iteration


def test_check_range_is_the_same_verdict_configure_applies_without_writing() -> None:
    # The reader stores a fixed range as a preference while auto-range owns the RNG bit, so it
    # needs the verdict without the write - and the two must not be able to drift apart.
    i2c, isl = ready_protocol()
    run(isl.setup())
    fake(i2c).log.clear()
    isl.check_range(_RANGE_LOW_LUX)
    isl.check_range(_RANGE_HIGH_LUX)
    for bad in (0, 375.0, 5000, 10001, True):  # True == 1 is not a range either
        raised = False
        try:
            isl.check_range(bad)  # type: ignore[arg-type]  # 375.0 is deliberately the wrong type
        except ValueError:
            raised = True
        assert raised, f"check_range({bad}) must raise"
    assert register_writes(i2c) == []


def test_verify_device_id_raises_on_the_wrong_part_and_passes_on_the_right_one() -> None:
    i2c, isl = ready_protocol()
    run(isl.verify_device_id())  # 0x7D, seeded - no raise
    seed(i2c, _REG_ID, bytes([0x44]))  # a plausible wrong answer: the part's own I2C address
    raised = False
    try:
        run(isl.verify_device_id())
    except RuntimeError:
        raised = True
    assert raised, "a mismatched device ID must raise, not be reported as a verdict"


def test_the_dark_offset_is_a_datasheet_constant_on_the_low_range_alone() -> None:
    # DDark is specified at range 0 only (p3): the same dark current is ~1/26.67 of a count on
    # the high range, so subtracting a whole one there would remove real signal, not an offset.
    assert ISL29125_I2C._dark_offset(_RANGE_LOW_LUX) == 1
    assert ISL29125_I2C._dark_offset(_RANGE_HIGH_LUX) == 0


def test_every_hardware_backed_setter_reports_a_rejected_field_without_writing() -> None:
    # Each setter refuses (its own False), one CHIP_SET count each, and nothing on the bus - the reader
    # must surface the hardware driver's refusal rather than swallow it into a silent success.
    i2c, reader = ready_reader("field_guard")

    async def scenario() -> "ErrorLog":
        assert await reader.set_resolution(8) is False
        assert await reader.set_ir_comp_offset(2) is False
        assert await reader.set_ir_comp_adjust(200) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    assert err_count(counters) == 3
    assert errors(counters)[-1] == code("E", "CHIP_SET")
    assert register_writes(i2c) == []


def test_set_range_rejects_a_bad_value_with_auto_range_off_too() -> None:
    # The auto-range-on path validates without writing and the off path validates by writing;
    # both have to refuse, or the stored preference and the chip can disagree.
    i2c, reader = ready_reader("range_bad_fixed")

    async def scenario() -> "ErrorLog":
        assert await reader.set_range_auto(flag=False) is True
        fake(i2c).log.clear()
        assert await reader.set_range(5000) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    assert code("E", "CHIP_SET") in errors(counters)
    assert register_writes(i2c) == []
    assert reader._fixed_range == _RANGE_HIGH_LUX, "a rejected range must not become the preference"


def test_a_fractional_setting_is_rejected_rather_than_silently_truncated() -> None:
    # The project-wide coercion policy (SPECIFICATION.md Part A.8), reached by routing these
    # setters through asy_config_manager's own type_or_range_error() instead of a local int() cast:
    # a fat-fingered 12.5 must not become a stored 12.
    _i2c, reader = ready_reader("coerce")

    async def scenario() -> "ErrorLog":
        assert await reader.set_trigger_s(12.5) is False
        assert await reader.set_trigger_s(30.0) is True  # integral float: exactly representable
        assert await reader.set_autorange_dwell(10) is True  # int widened to float, always exact
        assert await reader.set_autorange_thresh(85) is True  # the same widening, on a % field
        return await reader.get_error_counter()

    counters = run(scenario())
    assert err_count(counters) == 1  # the accepted values prove which one was refused
    assert errors(counters)[-1] == code("E", "BAD_ARG")
    assert run(reader._trigger_period.get_value()) == 30
    assert reader._ar_dwell_s == 10.0
    assert reader._ar_thresh == 85.0


def test_a_bool_is_never_accepted_as_a_numeric_setting() -> None:
    # bool is an int subclass in MicroPython as in CPython, so a `True` reaching a numeric field
    # would otherwise store 1 - inside every one of these fields' own bounds except AutoRangeThresh.
    _i2c, reader = ready_reader("bool_reject")

    async def scenario() -> None:
        assert await reader.set_trigger_s(True) is False
        assert await reader.set_autorange_thresh(True) is False
        assert await reader.set_autorange_dwell(True) is False
        assert await reader.set_filter_coefficient(True) is False

    run(scenario())
    assert reader._ar_thresh == 85.0, "the seeded value, untouched"


def test_the_derived_gap_keeps_its_margin_across_the_whole_gain_ratio_band() -> None:
    # The divisor is 2x the part's NOMINAL 26.67, not the measured GainRatio. Deliberate: the
    # factor 2 absorbs the entire [20, 34] band that field allows, so coupling the two would add
    # a dependency without moving a single decision. Proven over the band rather than argued.
    _i2c, reader = ready_reader("derived_margin")

    async def scenario() -> None:
        for thresh in (50.0, 85.0, 95.0):
            assert await reader.set_autorange_thresh(thresh) is True
            for ratio in (_GAIN_RATIO_MIN, _GAIN_RATIO_NOMINAL, _GAIN_RATIO_MAX):
                # A light sitting exactly at the switch-up point reads thresh/ratio once the range
                # has changed under it, and that has to stay clear of the derived down point.
                assert thresh / ratio > reader._down_thresh()

    run(scenario())


def test_configure_arms_and_disarms_the_threshold_interrupt_by_intent() -> None:
    # The reader asks for the behaviour; INTSEL's encoding (one channel, p11 Table 11) stays
    # inside the hardware driver, so a wrong channel cannot be requested from outside at all.
    _i2c, isl = ready_protocol()
    run(isl.setup())
    assert isl.encode_shadow()[2] & 0x03 == _INTSEL_GREEN
    run(isl.configure(threshold_interrupt=False))
    assert isl.encode_shadow()[2] & 0x03 == 0x00
    run(isl.configure(threshold_interrupt=True))
    assert isl.encode_shadow()[2] & 0x03 == _INTSEL_GREEN


# ---------------------------------------------------------------------------
# Paths the happy cases never reach - each one a real fault, not a patched method
# ---------------------------------------------------------------------------


def test_the_colour_temperature_chain_gives_up_instead_of_dividing_by_a_collapsed_sum() -> None:
    # Both guards below the low-light floor. _store_isl() clamps `norm` into 0..1 before calling,
    # so the out-of-domain arm is defence in depth (Part E.4); the collapsed-sum arm is reachable
    # whenever the output filter has not yet caught up with a scene that just went dark.
    _i2c, reader = ready_reader("cct_guards")
    assert reader._colour_temperature(1000, [1.5, 1.5, 1.5]) is None, "out of the matrix's domain"
    assert reader._colour_temperature(1000, [0.0, 0.0, 0.0]) is None, "X+Y+Z == 0 has no chromaticity"
    # And the floor itself still answers None rather than reaching either guard.
    assert reader._colour_temperature(1, [0.2, 0.3, 0.2]) is None


# ---------------------------------------------------------------------------
# Manual gain-ratio calibration: a run only MEASURES and publishes a candidate, never writes.
# ---------------------------------------------------------------------------


def queue_legs(reader: ISL29125_Reader, *triples: "tuple[int, int, int]") -> None:
    # A sandwich reads three scenes (this range, the other, this one again) while seed() sets one
    # static register, so the legs are driven through read_counts() itself. The last triple repeats
    # once the queue drains, which is what a steady scene looks like.
    pending = list(triples)

    async def _read_counts() -> "tuple[int, int, int]":
        # Cycles rather than repeating the last triple: a run takes several sandwiches, and each
        # one has to see the same pair of scenes again for the readings to agree.
        if not pending:
            pending.extend(triples)
        return pending.pop(0)

    reader._isl.read_counts = _read_counts  # type: ignore[method-assign]


def calibrating_reader(name: str) -> "tuple[I2C, ISL29125_Reader]":
    i2c, reader = ready_reader(name)
    assert run(reader.start_calibration(flag=True)) is True
    return i2c, reader


def test_no_calibration_runs_until_the_user_starts_one() -> None:
    # The whole point of the redesign: nothing measures, and nothing is published, on its own.
    _i2c, reader = ready_reader("cal_idle")
    queue_legs(reader, (51800, 51800, 51800))
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
    assert reader._measured_ratio() is None
    assert reader._active_range == _RANGE_HIGH_LUX  # no range was ever switched away from


def test_a_run_publishes_a_candidate_and_leaves_the_applied_ratio_alone() -> None:
    # The applied factor is config, written by a user PUT alone. A run that measured 25.9 must
    # publish 25.9 and still be correcting by the nominal ratio afterwards.
    _i2c, reader = calibrating_reader("cal_publish")
    queue_legs(reader, (51800, 51800, 51800), (2000, 2000, 2000))
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
    measured = reader._measured_ratio()
    assert measured is not None
    assert abs(measured - 51799 / 2000) < 1e-9  # the low range carries a 1-count dark offset
    assert reader._gain_ratio == _GAIN_RATIO_NOMINAL, "a measurement must never become the applied factor"
    assert reader._active_range == _RANGE_HIGH_LUX  # the sandwich put the range back


def test_a_scene_that_moves_during_the_sandwich_is_rejected() -> None:
    # The reason for the third reading. A pair alone cannot tell a real ratio from a light that
    # changed between its two legs, and that is the dominant error in this measurement.
    _i2c, reader = calibrating_reader("cal_moved")
    # Back on the original range the scene now reads 2600, 30% up from the 2000 it started at.
    queue_legs(reader, (51800, 51800, 51800), (2600, 2600, 2600))
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
    assert reader._measured_ratio() is None, "a ratio measured across a moving scene is not evidence"
    assert reader._cal_recent == []


def test_a_clipped_partner_leg_is_rejected() -> None:
    # The band gate is range-agnostic, so a scene comfortable on this range can be far past full
    # scale on the other one - and a clipped leg measures the clamp, not the part.
    _i2c, reader = calibrating_reader("cal_clipped")
    queue_legs(reader, (65535, 65535, 65535), (2000, 2000, 2000))
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
    assert reader._measured_ratio() is None
    assert reader._active_range == _RANGE_HIGH_LUX


def test_an_implausible_ratio_is_discarded_rather_than_published() -> None:
    _i2c, reader = calibrating_reader("cal_implausible")
    # 20000/2000 = 10, far under the 20.0 floor - a real pair cannot look like this.
    queue_legs(reader, (20000, 20000, 20000), (2000, 2000, 2000))
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
    assert reader._measured_ratio() is None


def test_calibration_waits_for_a_scene_inside_the_overlap_band() -> None:
    _i2c, reader = calibrating_reader("cal_band")
    queue_legs(reader, (51800, 51800, 51800), (2000, 2000, 2000))
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(64000))  # above AutoRangeThresh - the low range would clip
        run(reader._measure_gain_ratio(10))  # below the derived down point - at the dark floor
    assert reader._measured_ratio() is None
    assert reader._calibrating is True, "an unusable scene pauses the run, it does not end it"


def test_calibration_is_skipped_during_settle_and_while_auto_range_is_off() -> None:
    _i2c, reader = calibrating_reader("cal_gated")
    queue_legs(reader, (51800, 51800, 51800), (2000, 2000, 2000))
    reader._isl._settle_until_ms = time.ticks_add(time.ticks_ms(), 10_000)
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
    assert reader._measured_ratio() is None, "a reading taken mid-settle is not a measurement"
    reader._isl._settle_until_ms = time.ticks_ms()
    reader._range_auto = False
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
    assert reader._measured_ratio() is None, "a pinned range cannot be swapped out from under the user"


def test_the_run_ends_once_consecutive_readings_agree() -> None:
    # One good-looking reading is not evidence - a slow drift produces a run of self-consistent
    # wrong answers, which is what the consecutive-agreement rule is for.
    _i2c, reader = calibrating_reader("cal_converge")
    queue_legs(reader, (51800, 51800, 51800), (2000, 2000, 2000))
    with _FastAsyncSleep():
        for _ in range(_CAL_CONVERGE_N):
            assert reader._calibrating is True
            # Each sandwich's last switch arms a settle the real read loop waits out between
            # samples; these tests run in zero wall-clock time, so it is retired by hand.
            reader._isl._settle_until_ms = time.ticks_ms()
            run(reader._measure_gain_ratio(2000))
    assert reader._calibrating is False, "the run stops itself once it has converged"
    assert reader._measured_ratio() is not None


def test_a_disagreeing_reading_restarts_the_agreement_run() -> None:
    _i2c, reader = calibrating_reader("cal_restart")
    queue_legs(reader, (51800, 51800, 51800), (2000, 2000, 2000))
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
        assert len(reader._cal_recent) == 1
        # A different scene: 48000/2000 = 24.0, well outside the 1% agreement tolerance.
        queue_legs(reader, (48000, 48000, 48000), (2000, 2000, 2000))
        reader._isl._settle_until_ms = time.ticks_ms()  # as above: no wall clock passes here
        run(reader._measure_gain_ratio(2000))
    assert len(reader._cal_recent) == 1, "a disagreeing reading starts the count again"
    assert reader._calibrating is True


def test_the_run_gives_up_when_its_window_closes() -> None:
    _i2c, reader = calibrating_reader("cal_window")
    reader._cal_until_ms = time.ticks_add(time.ticks_ms(), -1)
    queue_legs(reader, (51800, 51800, 51800), (2000, 2000, 2000))
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
    assert reader._calibrating is False
    assert reader._measured_ratio() is None, "a window that closed with nothing stable publishes nothing"


def test_a_published_candidate_stops_being_offered_once_its_hold_expires() -> None:
    _i2c, reader = calibrating_reader("cal_hold")
    queue_legs(reader, (51800, 51800, 51800), (2000, 2000, 2000))
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
    assert reader._measured_ratio() is not None
    reader._cal_meas_until_ms = time.ticks_add(time.ticks_ms(), -1)
    assert reader._measured_ratio() is None, "a stale candidate must not read as a fresh one"


def test_a_calibration_window_without_a_stable_reading_warns_once() -> None:
    # A run whose window closes unconverged persists one ISL_CAL_TIMEOUT, readable in the module's errcount; a
    # converged run persists nothing and keeps its console line.
    _i2c, reader = calibrating_reader("cal_timeout")
    reader._cal_until_ms = time.ticks_add(time.ticks_ms(), -1)
    queue_legs(reader, (51800, 51800, 51800), (2000, 2000, 2000))
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
        run(reader._measure_gain_ratio(2000))  # the run is over: no second entry
    counters = run(reader.get_error_counter())
    assert warnings(counters) == [code("W", "ISL_CAL_TIMEOUT")]
    assert err_count(counters) == 1

    _i2c, converged = calibrating_reader("cal_converged")
    queue_legs(converged, (51800, 51800, 51800), (2000, 2000, 2000))
    printed: list[tuple[object, ...]] = []
    real_one = converged.pr.one

    def spy(*args: object, sep: str = " ", end: str = "\n") -> None:
        printed.append(args)
        real_one(*args, sep=sep, end=end)

    converged.pr.one = spy  # type: ignore[method-assign]
    with _FastAsyncSleep():
        for _ in range(_CAL_CONVERGE_N):
            converged._isl._settle_until_ms = time.ticks_ms()
            run(converged._measure_gain_ratio(2000))
    assert converged._calibrating is False
    assert err_count(run(converged.get_error_counter())) == 0
    assert [line[0] for line in printed] == ["Gain-ratio calibration finished:"]


def test_failing_reads_past_the_window_end_the_run_and_drop_the_candidate() -> None:
    # The expiries run every cycle, a failed one too: reads failing past both deadlines still end the run with its
    # ISL_CAL_TIMEOUT and drop the candidate, which the next good cycle does not republish.
    i2c, reader = calibrating_reader("cal_outage")
    reader._publish_candidate(25.9)
    reader._cal_until_ms = time.ticks_add(time.ticks_ms(), -1)
    reader._cal_meas_until_ms = time.ticks_add(time.ticks_ms(), -1)
    fake(i2c).nak_addresses.add(_ADDR)
    with _FastAsyncSleep():
        results = run(reader._read_isl())
    assert results[0] is None
    assert reader._calibrating is False
    assert reader._cal_meas is None
    assert code("W", "ISL_CAL_TIMEOUT") in warnings(run(reader.get_error_counter()))
    fake(i2c).nak_addresses.clear()
    seed_cycle(i2c, 20000, 20000, 20000)
    reader._isl._settle_until_ms = time.ticks_ms()
    with _FastAsyncSleep():
        run(reader._store_isl(run(reader._read_isl())))
    assert run(reader.get_data()).GainMeas is None


def test_a_week_of_failing_reads_never_revives_a_run_or_a_candidate_across_the_wrap() -> None:
    # Reads failing hourly for a week, then one good cycle: both deadlines were acted on in the first hour, so
    # nothing reads a stored tick past 2**29 ms as the future - the run stays over and the candidate gone.
    i2c, reader = calibrating_reader("cal_outage_week")
    clock = Ticks30Time(9000)
    asy_isl29125_driver.time = clock  # type: ignore[assignment]
    try:
        reader._isl._settle_until_ms = clock.ticks_ms()  # type: ignore[assignment]  # ticks values from the fake
        reader._last_switch_ms = clock.ticks_ms()  # type: ignore[assignment]
        assert run(reader.start_calibration(flag=True)) is True
        reader._publish_candidate(25.9)
        fake(i2c).nak_addresses.add(_ADDR)
        with _FastAsyncSleep():
            for _ in range(7 * 24):
                clock.advance(3_600_000)
                run(reader._read_isl())
            fake(i2c).nak_addresses.clear()
            seed_cycle(i2c, 20000, 20000, 20000)
            clock.advance(3_600_000)
            run(reader._store_isl(run(reader._read_isl())))
        calibrating, gain_meas = reader._calibrating, run(reader.get_data()).GainMeas
    finally:
        asy_isl29125_driver.time = time
    assert calibrating is False
    assert gain_meas is None
    assert warnings(run(reader.get_error_counter())).count(code("W", "ISL_CAL_TIMEOUT")) == 1


def test_a_published_candidate_expires_and_stays_expired_across_a_week() -> None:
    # Read hourly for a week, a candidate held ten minutes is gone from the first hour on - and stays gone once its
    # stored tick would read as the future past 2**29 ms, because the candidate itself is dropped on expiry.
    _i2c, reader = ready_reader("cal_week")
    clock = Ticks30Time(7000)
    asy_isl29125_driver.time = clock  # type: ignore[assignment]
    seen = []
    try:
        reader._publish_candidate(25.9)
        assert reader._measured_ratio() == 25.9
        for _ in range(7 * 24):
            clock.advance(3_600_000)
            seen.append(reader._measured_ratio())
    finally:
        asy_isl29125_driver.time = time
    assert set(seen) == {None}, [index for index, value in enumerate(seen) if value is not None]
    assert reader._cal_meas is None


def test_the_measured_candidate_travels_with_every_reading() -> None:
    # GainMeas is a MEASUREMENT, so it rides the same tuple as Lux and RGB rather than sitting in
    # config or in the maintenance group - which is what lets the user read it and copy it across.
    i2c, reader = ready_reader("cal_in_tuple")
    seed_cycle(i2c, 2000, 1000, 500)
    with _FastAsyncSleep():
        run(reader._read_isl())
        run(reader._store_isl((2000, 1000, 500, _RANGE_HIGH_LUX, _RANGE_HIGH_LUX, 1754997000)))
    # Asserted through get_dict_data(), NOT get_data(): the REST body is a hand-written override
    # (the measurement group is nested), so a field can exist on the namedtuple and still never
    # reach the API. That is exactly what happened when this field was added.
    assert _isl_group(run(reader.get_dict_data()))["GainMeas"] is None
    reader._publish_candidate(25.9)
    with _FastAsyncSleep():
        run(reader._store_isl((2000, 1000, 500, _RANGE_HIGH_LUX, _RANGE_HIGH_LUX, 1754997000)))
    assert _isl_group(run(reader.get_dict_data()))["GainMeas"] == 25.9


def test_only_a_config_push_changes_the_applied_ratio() -> None:
    _i2c, reader = ready_reader("cal_setter")
    assert run(reader.set_gain_ratio(24.5)) is True
    assert reader._gain_ratio == 24.5
    for refused in (19.9, 34.1):
        assert run(reader.set_gain_ratio(refused)) is False, f"{refused} is outside the plausibility band"
    assert reader._gain_ratio == 24.5, "a refused push must not disturb the live value"


def test_starting_a_calibration_with_false_is_a_no_op() -> None:
    # Matches SGP40_Reader.reset_voc()'s own contract for a command-only field.
    _i2c, reader = ready_reader("cal_false")
    assert run(reader.start_calibration(flag=False)) is False
    assert reader._calibrating is False


def test_a_failed_partner_read_logs_a_read_error_and_puts_the_range_back() -> None:
    _i2c, reader = calibrating_reader("cal_read_fails")

    async def _boom() -> "tuple[int, int, int]":
        raise OSError(5)

    reader._isl.read_counts = _boom  # type: ignore[method-assign]
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
    assert reader._measured_ratio() is None
    counter = (run(reader.get_error_counter()))["ISL29125"]
    assert counter["ErrCount"] >= 1
    err_num = counter["ErrNum"]
    assert isinstance(err_num, list)
    assert err_num[-1] == code("E", "READ"), f"the calibration leg's own failure must log READ, got {err_num}"
    assert reader._active_range == _RANGE_HIGH_LUX


def test_a_partner_reading_of_zero_is_not_turned_into_a_ratio() -> None:
    # A division guard, not a plausibility one. Starting on the LOW range deliberately: that is the
    # only arrangement where the PARTNER leg is the divisor. Passing green_counts=0 instead returns
    # at the band gate, so the assertion passes with nothing measured - the range check is the floor.
    _i2c, reader = calibrating_reader("cal_zero")
    reader._active_range = _RANGE_LOW_LUX
    queue_legs(reader, (0, 0, 0), (2000, 2000, 2000))
    with _FastAsyncSleep():
        run(reader._measure_gain_ratio(2000))
    assert reader._measured_ratio() is None
    assert reader._active_range == _RANGE_LOW_LUX, "all three legs ran, so the divisor guard is what stopped this - not the band gate"


def test_a_leg_whose_range_switch_fails_abandons_the_sandwich_without_a_candidate() -> None:
    # The other way a leg can fail: the switch that ARMS it never lands, so the reading comes off
    # the range the run measures against. The legs give 53340/2000 = 26.67 deliberately - a swallowed
    # failure then produces a PUBLISHABLE answer, so only this guard can refuse it, not the band.
    i2c, reader = calibrating_reader("cal_switch_fail")
    queue_legs(reader, (53340, 53340, 53340), (2000, 2000, 2000))
    with _FastAsyncSleep():
        fail_register_writes(i2c, times=1)
        run(reader._measure_gain_ratio(2000))
    assert code("E", "CHIP_SET") in errors(run(reader.get_error_counter())), "the switch really did fail"
    assert reader._measured_ratio() is None, "a leg read off an unswitched chip must not become a candidate"
    # The third leg still runs - it is also what puts the range back - so the run ends where it
    # started rather than stranding every later sample on the partner's range.
    assert reader._active_range == _RANGE_HIGH_LUX


# ---------------------------------------------------------------------------
# Bus-hazard coverage moved from tests/test_bus_hazard_multi_device.py (SPECIFICATION.md Part
# C.8): genuinely ISL29125-specific - the same-device test targets this chip's own destructive
# 0x08 status-register read, a real datasheet quirk, not a generic template.
# ---------------------------------------------------------------------------


async def _gather(a: "Coroutine[Any, Any, Any]", b: "Coroutine[Any, Any, Any]") -> None:
    # asyncio.gather() itself returns a Future, not a Coroutine - mypy rejects passing it straight
    # to run() (same call-shape convention test_asy_i2c_driver.py's own scenario() wrapping uses).
    await asyncio.gather(a, b)


def test_concurrent_read_and_write_never_interleave_on_the_wire() -> None:
    # The ISL's same-device hazard is sharper than its siblings': the status read at 0x08 is DESTRUCTIVE,
    # clearing the interrupt flag and releasing the INT line, and the data burst after it belongs to the
    # same logical cycle. A config write between the two restarts the conversion under a committed read.
    i2c, isl = ready_protocol()
    seed(i2c, _REG_DATA, counts_burst(0x2000, 0x1800, 0x1000))
    read_iterations = 6

    async def reader() -> None:
        for _ in range(read_iterations):
            await isl.read_status()
            counts = await isl.read_counts()
            assert counts == (0x2000, 0x1800, 0x1000), f"a concurrent write tore the data burst: {counts}"
            await asyncio.sleep(0)

    async def writer() -> None:
        await asyncio.sleep(0)  # let the reader get partway into its first cycle first
        for adjust in (10, 20, 30):
            await isl.configure(ir_adjust=adjust)
            await asyncio.sleep(0)

    with _FastAsyncSleep():
        run(_gather(reader(), writer()))

    # Every logged transaction went to this one address, and the config writes really did land.
    touched = {entry[1] for entry in fake(i2c).log if entry[0] in ("writeto", "readfrom_into")}
    assert touched == {_ADDR}
    config_writes = [register for register, _payload in register_writes(i2c) if register == _REG_CONFIG2]
    assert len(config_writes) == 3


def test_configure_never_exposes_the_shadow_ahead_of_a_write_still_in_flight() -> None:
    # configure() mutates the shadow only under the device-session lock (C.8): holding that lock stands in for an
    # operation in flight, and the shadow must not move meanwhile.
    _i2c, isl = ready_protocol()
    assert isl.resolution() == 16

    async def change_resolution() -> None:
        await isl.configure(resolution=12)

    async def scenario() -> None:
        lock = isl._i2c_isl29125.session_lock
        await lock.acquire()  # simulate another operation already in flight on this sensor
        writer = asyncio.get_event_loop().create_task(change_resolution())
        try:
            await asyncio.sleep(0)  # let configure() run up to where it must wait for the lock
            assert isl.resolution() == 16, "the shadow changed before the write could even be attempted"
        finally:
            # Always released, even if the assertion above fails - a held lock would leave
            # `writer` permanently parked waiting on it, an unexplained hang layered on top of
            # what should be a clean, immediately visible assertion failure.
            lock.release()
        await writer

    run(scenario())
    assert isl.resolution() == 12  # the write did land, once the lock actually freed up


def test_set_thresholds_scales_to_the_resolution_live_when_it_gets_the_session() -> None:
    # A resolution change landing while set_thresholds() waits for the session lock: the counts are scaled inside the
    # hold, to the resolution the chip runs when the write happens.
    i2c, isl = make_protocol()

    async def scenario() -> None:
        lock = isl._i2c_isl29125.session_lock
        await lock.acquire()  # a configure() holding the session
        writer = asyncio.get_event_loop().create_task(isl.set_thresholds(0, 32768))
        try:
            await asyncio.sleep(0)
            isl._resolution = 12  # what that configure() commits inside its hold
        finally:
            lock.release()
        await writer

    run(scenario())
    assert register_writes(i2c) == [(_REG_THRESHOLDS, struct.pack("<HH", 0, 32768 >> 4))]


def _chip_thresholds(i2c: I2C) -> bytes:
    return bytes(fake(i2c).registers[(_ADDR, _REG_THRESHOLDS)])


def _expected_thresholds(reader: ISL29125_Reader) -> bytes:
    if reader._active_range == _RANGE_LOW_LUX:
        return struct.pack("<HH", 0, ISL29125_I2C.fraction_to_counts(reader._ar_thresh))
    return struct.pack("<HH", ISL29125_I2C.fraction_to_counts(reader._ar_thresh / _AR_DOWN_DIVISOR), 65535)


def test_a_threshold_push_racing_a_range_switch_leaves_chip_and_cache_agreeing() -> None:
    # One reader-level lock serialises every threshold writer, and each derives its counts inside it: whichever
    # order the two land in, the chip holds the counts the cached threshold and the active range give.
    i2c, reader = ready_reader("thresh_race")
    real_set = reader._isl.set_thresholds

    async def yielding_set(low_counts: int, high_counts: "int | None" = None) -> None:
        await asyncio.sleep(0)
        await real_set(low_counts, high_counts)

    reader._isl.set_thresholds = yielding_set  # type: ignore[method-assign]

    async def scenario() -> None:
        switch = asyncio.create_task(reader._switch_range(_RANGE_LOW_LUX))
        await asyncio.sleep(0)
        assert await reader.set_autorange_thresh(90.0) is True
        assert await switch is True

    with _FastAsyncSleep():
        run(scenario())
    assert reader._active_range == _RANGE_LOW_LUX
    assert reader._ar_thresh == 90.0
    assert _chip_thresholds(i2c) == _expected_thresholds(reader)


def test_two_concurrent_threshold_pushes_end_on_the_later_one() -> None:
    i2c, reader = ready_reader("thresh_two")
    real_set = reader._isl.set_thresholds

    async def yielding_set(low_counts: int, high_counts: "int | None" = None) -> None:
        await asyncio.sleep(0)
        await real_set(low_counts, high_counts)

    reader._isl.set_thresholds = yielding_set  # type: ignore[method-assign]

    async def scenario() -> None:
        first = asyncio.create_task(reader.set_autorange_thresh(60.0))
        await asyncio.sleep(0)
        assert await reader.set_autorange_thresh(90.0) is True
        assert await first is True

    with _FastAsyncSleep():
        run(scenario())
    assert reader._ar_thresh == 90.0
    assert _chip_thresholds(i2c) == _expected_thresholds(reader)


def test_never_touches_any_address_but_its_own() -> None:
    i2c, isl = ready_protocol()
    seed(i2c, _REG_DATA, counts_burst(0x2000, 0x1800, 0x1000))

    async def exercise() -> None:
        for call in (
            isl.setup,
            isl.reset,
            isl.get_device_id,
            isl.read_status,
            isl.clear_brownout,
            isl.read_counts,
            isl.get_config_snapshot,
            lambda: isl.configure(mode=0x05, range_fs=375, resolution=12),
            lambda: isl.set_thresholds(983, 55705),
        ):
            try:
                await call()
            except Exception:  # only the addresses *touched* matter for this sweep, not success
                pass

    with _FastAsyncSleep():
        run(exercise())

    touched = {entry[1] for entry in fake(i2c).log if entry[0] in ("writeto", "readfrom_into")}
    assert touched == {_ADDR}, f"ISL29125_I2C touched unexpected address(es): {touched - {_ADDR}}"



def test_init_runs_on_the_defaults_when_its_config_file_cannot_be_written() -> None:
    # A failed config write does not end the read task: the reader runs on the defaults (SPECIFICATION.md C.7.3).
    FakeTimer.all_timers.clear()
    i2c = make_i2c()
    seed_healthy_chip(i2c)
    reader = ISL29125_Reader(i2c, 6, cfg_path=_tmp_cfg_path("unwritable") + "missing_dir/")
    assert run(reader.setup()) is True  # the config store's validity: the defaults are valid
    assert reader.cfgmgr.valid is True

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            assert await init_reader(reader, i2c) is True
        return await reader.get_error_counter()

    assert err_count(run(scenario())) == 0
    assert run(reader.cfgmgr.pr.get_log())[reader.cfgmgr.name]["ErrNum"][-1] == code("E", "CFG_FILE_WRITE")


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
