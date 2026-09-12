import asyncio
import errno as errno_mod
import os
import struct
import time

from _fram_chip_fake import FakeMB85RS64V
from machine import I2C as FakeI2C
from machine import Pin as FakePin
from machine import Timer as FakeTimer

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_i2c_driver import I2C
from asy_isl29125_driver import (
    ISL29125,
    ISL29125_I2C,
    ISL29125_Reader,
    _counts_to_lux,
    _decode_config_bytes,
    _decode_rgb_burst,
    _fraction_to_counts,
    _is_bus_fault_pattern,
    _is_saturated,
    _normalise_triple,
)
from asy_spi_driver import SPI

# Same one-process-per-test-file swap as test_asy_bmp3xx_driver.py: routes AsyFramManager's SPI
# traffic to the simulated FRAM chip instead of unavailable real hardware.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

# Mirrors of asy_isl29125_driver.py's own underscore-prefixed micropython.const() values - those
# are folded into every use site at compile time and are NOT importable module attributes (see
# test_asy_bmp3xx_driver.py's own note on the same trap). Kept in sync by citation, not re-derived.
_ADDR = 0x44  # hard-wired, p15 ("1000100")
_DEVICE_ID = 0x7D  # p9, Table 2
_CMD_RESET = 0x46
_REG_ID = 0x00
_REG_CONFIG1 = 0x01
_REG_CONFIG2 = 0x02
_REG_CONFIG3 = 0x03
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

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    from typing_extensions import Self

    from asy_isl29125_driver import ISLResults
    from print_log import ErrorLog

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


class _FastAsyncSleep:
    # I2CDevice.setup()'s _probe_for_device() makes two real 0.1s asyncio.sleep() calls, and this
    # driver's own settle wait sleeps a whole 303ms conversion cycle - both far too slow for a
    # test driving read_loop() as a background task. Same technique as test_asy_bmp3xx_driver.py's.
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


_TMP_DIR = "tests/_tmp"


def _tmp_cfg_path(name: str) -> str:
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    path = _TMP_DIR + "/isl_" + name + "_"
    try:
        os.remove(path + "config_ISL29125.cfg")
    except OSError:
        pass
    return path


def make_i2c() -> I2C:
    return I2C(0, scl_pin=1, sda_pin=0, frequency=100000)


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


def make_protocol(address: int = _ADDR) -> "tuple[I2C, ISL29125_I2C]":
    i2c = make_i2c()
    return i2c, ISL29125_I2C(i2c, address=address)


def ready_protocol(address: int = _ADDR) -> "tuple[I2C, ISL29125_I2C]":
    i2c, isl = make_protocol(address)
    seed_healthy_chip(i2c, address)
    return i2c, isl


def mem_writes(i2c: I2C) -> "list[tuple[int, bytes]]":
    return [(entry[2], entry[3]) for entry in fake(i2c).log if entry[0] == "writeto_mem"]


def mem_reads(i2c: I2C) -> "list[tuple[int, int]]":
    return [(entry[2], entry[3]) for entry in fake(i2c).log if entry[0] == "readfrom_mem"]


def logged(counters: "ErrorLog", kind: str, name: str = "ISL29125") -> "list[int]":
    # print_log.py keeps errors and warnings in ONE history list, discriminated by the parallel
    # ErrType entry ("E"/"W") - so asserting on ErrNum alone would let wrnno=13 satisfy a test
    # written for errno=13, and vice versa.
    entry = counters[name]
    # No strict= (ruff B905): MicroPython's zip() rejects it (CPython 3.10+-only), and ErrEntry
    # keeps both lists in step by construction - the same note src/asy_webserver_service.py carries.
    return [number for number, entry_kind in zip(entry["ErrNum"], entry["ErrType"]) if entry_kind == kind]  # noqa: B905


def errors(counters: "ErrorLog", name: str = "ISL29125") -> "list[int]":
    return logged(counters, "E", name)


def warnings(counters: "ErrorLog", name: str = "ISL29125") -> "list[int]":
    return logged(counters, "W", name)


# ---------------------------------------------------------------------------
# Pure helpers - F1 _decode_rgb_burst
# ---------------------------------------------------------------------------


def test_decode_rgb_burst_returns_green_red_blue_in_register_order() -> None:
    # Register order is GREEN, RED, BLUE (p9, Table 1); p13's Table 20 mislabels its own rows.
    assert _decode_rgb_burst(counts_burst(0x1234, 0x5678, 0x9ABC)) == (0x1234, 0x5678, 0x9ABC)
    # Little-endian, proven by a byte string whose halves are distinguishable either way round.
    assert _decode_rgb_burst(bytes([0x34, 0x12, 0x78, 0x56, 0xBC, 0x9A])) == (0x1234, 0x5678, 0x9ABC)


def test_decode_rgb_burst_rejects_short_and_none() -> None:
    assert _decode_rgb_burst(None) is None
    assert _decode_rgb_burst(b"") is None
    assert _decode_rgb_burst(bytes(5)) is None
    assert _decode_rgb_burst(bytes(7)) is None
    assert _decode_rgb_burst(42) is None  # type: ignore[arg-type]


def test_decode_rgb_burst_accepts_a_bytearray_and_a_memoryview() -> None:
    # Both are legitimate returns from layer 1's own struct.unpack path.
    payload = counts_burst(1, 2, 3)
    assert _decode_rgb_burst(bytearray(payload)) == (1, 2, 3)
    assert _decode_rgb_burst(memoryview(payload)) == (1, 2, 3)


def test_decode_rgb_burst_decodes_the_all_ones_bus_fault_pattern() -> None:
    assert _decode_rgb_burst(bytes([0xFF] * 6)) == (0xFFFF, 0xFFFF, 0xFFFF)


# ---------------------------------------------------------------------------
# F2 _normalise_triple
# ---------------------------------------------------------------------------


def test_normalise_triple_shifts_only_at_12_bit() -> None:
    assert _normalise_triple(100, 200, 300, resolution_bits=16, dark_offset=0) == (100, 200, 300)
    assert _normalise_triple(100, 200, 300, resolution_bits=12, dark_offset=0) == (1600, 3200, 4800)


def test_normalise_triple_12_bit_maximum_is_65520_not_65535() -> None:
    # The saturation trap: the shift cannot reach full scale, so any saturation test written
    # against the NORMALISED value is wrong at 12 bits. F6 tests the raw maximum instead.
    assert _normalise_triple(4095, 4095, 4095, resolution_bits=12, dark_offset=0) == (65520, 65520, 65520)


def test_normalise_triple_subtracts_the_dark_offset_and_clamps_at_zero() -> None:
    assert _normalise_triple(10, 5, 1, resolution_bits=16, dark_offset=1) == (9, 4, 0)
    assert _normalise_triple(0, 0, 0, resolution_bits=16, dark_offset=5) == (0, 0, 0)


def test_normalise_triple_clamps_at_full_scale() -> None:
    assert _normalise_triple(70000, 65535, 65536, resolution_bits=16, dark_offset=0) == (65535, 65535, 65535)


def test_normalise_triple_falls_back_to_no_shift_for_an_unknown_resolution() -> None:
    # The conservative direction: shifting when you should not inflates every reading 16x, while
    # not shifting when you should only under-reports.
    assert _normalise_triple(100, 100, 100, resolution_bits=10, dark_offset=0) == (100, 100, 100)


# ---------------------------------------------------------------------------
# F3 _counts_to_lux
# ---------------------------------------------------------------------------


def test_counts_to_lux_matches_the_datasheet_lsb_figures() -> None:
    # An external check, not a self-consistent one: p1's feature list states 5.7 mlux per LSB on
    # range 0 and 0.152 lux per LSB on range 1.
    assert abs(_counts_to_lux(1, _RANGE_LOW_LUX, 1.0) - 0.00572) < 1e-5
    assert abs(_counts_to_lux(1, _RANGE_HIGH_LUX, 1.0) - 0.15259) < 1e-5


def test_counts_to_lux_reaches_full_scale_at_full_count() -> None:
    assert _counts_to_lux(0, _RANGE_LOW_LUX, 1.0) == 0.0
    assert abs(_counts_to_lux(65535, _RANGE_LOW_LUX, 1.0) - 375.0) < 1e-9
    assert abs(_counts_to_lux(65535, _RANGE_HIGH_LUX, 1.0) - 10000.0) < 1e-9


def test_counts_to_lux_applies_the_gain_correction_multiplicatively() -> None:
    assert abs(_counts_to_lux(65535, _RANGE_HIGH_LUX, 0.97) - 9700.0) < 1e-6


# ---------------------------------------------------------------------------
# F4 _fraction_to_counts
# ---------------------------------------------------------------------------


def test_fraction_to_counts_does_not_truncate_like_the_riot_driver() -> None:
    # RIOT's own `(uint16_t)(65535 / max_range)` does the scaling in integer arithmetic and
    # truncates - 6.55 becomes 6, a 9% error. Doing it in float and rounding once is why this is
    # a named function at all, and these are the two schema defaults the design depends on.
    assert _fraction_to_counts(85.0) == 55705
    assert _fraction_to_counts(1.5) == 983


def test_fraction_to_counts_clamps_to_the_register_range() -> None:
    assert _fraction_to_counts(0.0) == 0
    assert _fraction_to_counts(100.0) == 65535
    assert _fraction_to_counts(-5.0) == 0
    assert _fraction_to_counts(1000.0) == 65535


def test_fraction_to_counts_lands_somewhere_defined_for_nan_and_inf() -> None:
    # int() raises ValueError for NaN and OverflowError for inf on MicroPython, so the guard has
    # to be explicit rather than incidental.
    assert _fraction_to_counts(float("nan")) == 0
    assert _fraction_to_counts(float("inf")) == 65535
    assert _fraction_to_counts(float("-inf")) == 0


# ---------------------------------------------------------------------------
# F5 _is_bus_fault_pattern
# ---------------------------------------------------------------------------


def test_is_bus_fault_pattern_needs_all_three_channels_and_a_reserved_bit() -> None:
    assert _is_bus_fault_pattern((0xFFFF, 0xFFFF, 0xFFFF), 0xFF) is True
    # A genuinely saturated white scene with a plausible status byte is NOT a bus fault.
    assert _is_bus_fault_pattern((0xFFFF, 0xFFFF, 0xFFFF), 0x11) is False
    # Two of three at full scale is a real saturated scene with one unsaturated channel.
    assert _is_bus_fault_pattern((0xFFFF, 0xFFFF, 0x1234), 0xFF) is False


def test_is_bus_fault_pattern_fires_on_raw_all_ones_at_both_resolutions() -> None:
    # A dead bus reads 0xFF bytes regardless of BITS, so the raw pattern is identical either way.
    for _bits in (12, 16):
        assert _is_bus_fault_pattern((0xFFFF, 0xFFFF, 0xFFFF), 0xC8) is True


def test_is_bus_fault_pattern_is_false_for_a_clipped_12_bit_scene() -> None:
    # What is special about 12-bit is the OPPOSITE of "never fires": a real 12-bit reading cannot
    # exceed 4095, so at 12 bits this heuristic has no false-positive mode at all.
    assert _is_bus_fault_pattern((4095, 4095, 4095), 0xFF) is False


def test_is_bus_fault_pattern_treats_a_non_int_status_as_implausible() -> None:
    assert _is_bus_fault_pattern((0xFFFF, 0xFFFF, 0xFFFF), None) is True


def test_is_bus_fault_pattern_tolerates_a_missing_triple() -> None:
    assert _is_bus_fault_pattern(None, 0xFF) is False


# ---------------------------------------------------------------------------
# F6 _is_saturated
# ---------------------------------------------------------------------------


def test_is_saturated_uses_the_raw_resolution_maximum_not_65535() -> None:
    # The 12-bit trap from the other side: 4095 raw IS saturated, while the same reading after
    # normalisation is 65520 - which a post-normalisation `== 65535` test would miss entirely.
    assert _is_saturated(4095, 0, 0, resolution_bits=12) is True
    assert _is_saturated(65520, 0, 0, resolution_bits=12) is True  # >= , so an out-of-range test value still reads saturated
    assert _is_saturated(4094, 4094, 4094, resolution_bits=12) is False
    assert _is_saturated(65535, 0, 0, resolution_bits=16) is True
    assert _is_saturated(65534, 65534, 65534, resolution_bits=16) is False


def test_is_saturated_is_true_when_any_single_channel_clips() -> None:
    # Any channel, because the output is a colour triple: a clipped red with green at 40% of full
    # scale still destroys Hue, Sat and CCT.
    assert _is_saturated(26214, 65535, 100, resolution_bits=16) is True
    assert _is_saturated(65535, 26214, 100, resolution_bits=16) is True
    assert _is_saturated(100, 26214, 65535, resolution_bits=16) is True


def test_is_saturated_falls_back_to_16_bit_for_an_unknown_resolution() -> None:
    assert _is_saturated(4095, 4095, 4095, resolution_bits=10) is False


# ---------------------------------------------------------------------------
# F7 _decode_config_bytes
# ---------------------------------------------------------------------------


def test_decode_config_bytes_decodes_every_field() -> None:
    # CONFIG1 = mode 5 | RNG | BITS(12), CONFIG2 = IR offset + 40 codes, CONFIG3 = INTSEL green,
    # PRST = 10 -> 4 cycles.
    decoded = _decode_config_bytes(bytes([_MODE_RGB | _RNG_HIGH | _BITS_12, 0x80 | 40, _INTSEL_GREEN | 0x08]))
    assert decoded == (12, _RANGE_HIGH_LUX, 1, 40, 4)
    decoded = _decode_config_bytes(bytes([_MODE_RGB, 0x00, 0x00]))
    assert decoded == (16, _RANGE_LOW_LUX, 0, 0, 1)


def test_decode_config_bytes_round_trips_against_encode_shadow() -> None:
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
                        assert _decode_config_bytes(isl.encode_shadow()) == (resolution, range_fs, ir_offset, ir_adjust, persist)


def test_decode_config_bytes_ignores_the_reserved_bits() -> None:
    # p9: "the value of the reserved bit can change without any notice" - CONFIG1 B7:B6,
    # CONFIG2 B6 and CONFIG3 B7:B5.
    plain = _decode_config_bytes(bytes([_MODE_RGB, 40, 0x00]))
    noisy = _decode_config_bytes(bytes([_MODE_RGB | 0xC0, 40 | 0x40, 0xE0]))
    assert plain == noisy


def test_decode_config_bytes_decodes_an_all_zero_post_brownout_chip() -> None:
    # A chip that went through power-down reads 0x00 everywhere. That must decode without raising
    # AND be distinguishable from a configured chip - which it is, by the mode bits the caller
    # compares separately (this function deliberately does not decode mode).
    assert _decode_config_bytes(bytes(3)) == (16, _RANGE_LOW_LUX, 0, 0, 1)


def test_decode_config_bytes_rejects_the_wrong_length_and_none() -> None:
    assert _decode_config_bytes(None) is None
    assert _decode_config_bytes(bytes(2)) is None
    assert _decode_config_bytes(bytes(4)) is None


# ---------------------------------------------------------------------------
# Protocol layer - setup / reset / identity
# ---------------------------------------------------------------------------


def test_setup_sequence_is_id_reset_brownout_config() -> None:
    i2c, isl = ready_protocol()
    with _FastAsyncSleep():
        run(isl.setup())
    reads = mem_reads(i2c)
    writes = mem_writes(i2c)
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
        except RuntimeError:
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
    config1, _config2, config3 = mem_writes(i2c)[2][1]
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
    # Reading 0x08 clears RGBTHF and releases the INT pin, so the "exactly one status read per
    # cycle" invariant has to hold here too - which is also why this verify covers CONFIG1-3 only
    # (SparkFun's own reset() additionally requires STATUS == 0x00, but Table 15 documents 0x04
    # as that register's own default, so that check contradicts the datasheet).
    i2c, isl = ready_protocol()
    run(isl.reset())
    assert all(register != _REG_STATUS for register, _length in mem_reads(i2c))


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
    assert mem_reads(i2c) == [(_REG_ID, 1)]


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
    assert mem_writes(i2c) == [(_REG_CONFIG1, bytes([_MODE_RGB, 0x00, 0x00]))]


def test_configure_writes_two_bytes_from_0x02_for_an_ir_only_change() -> None:
    # An IR-compensation change alone must not restart the conversion cycle, so it is a 2-byte
    # burst at 0x02 rather than a 3-byte one at 0x01.
    i2c, isl = ready_protocol()
    run(isl.configure(mode=_MODE_RGB))
    fake(i2c).log.clear()
    run(isl.configure(ir_adjust=40))
    assert mem_writes(i2c) == [(_REG_CONFIG2, bytes([40, 0x00]))]


def test_configure_writes_nothing_when_nothing_changed() -> None:
    i2c, isl = ready_protocol()
    run(isl.configure(mode=_MODE_RGB))
    fake(i2c).log.clear()
    run(isl.configure(mode=_MODE_RGB))
    assert mem_writes(i2c) == []


def test_configure_force_rewrites_all_three_bytes_even_with_no_change() -> None:
    # What brownout recovery and the divergence check need: there is nothing to diff against a
    # chip that has lost its configuration.
    i2c, isl = ready_protocol()
    run(isl.configure(mode=_MODE_RGB))
    fake(i2c).log.clear()
    run(isl.configure(force=True))
    assert mem_writes(i2c) == [(_REG_CONFIG1, bytes([_MODE_RGB, 0x00, 0x00]))]


def test_configure_sets_the_settle_deadline_only_on_a_config1_write() -> None:
    _i2c, isl = ready_protocol()
    run(isl.configure(mode=_MODE_RGB))
    assert isl.time_to_settle_ms() > 0
    isl._settle_until_ms = time.ticks_add(time.ticks_ms(), -1000)  # the deadline has passed
    run(isl.configure(ir_adjust=40))
    assert isl.time_to_settle_ms() == 0


def test_autorange_settle_of_five_waits_five_cycles_not_one() -> None:
    # Requirement 14 calls this knob the settle MARGIN, so a value above 1 has to change the
    # deadline itself and not merely bound a loop.
    for bits, cycle_ms in ((16, 303), (12, 19)):
        _i2c, isl = ready_protocol()
        isl._resolution = bits
        isl.settle_cycles = 5
        run(isl.configure(mode=_MODE_RGB))
        remaining = isl.time_to_settle_ms()
        assert 4 * cycle_ms < remaining <= 5 * cycle_ms


def test_cycle_time_follows_the_configured_resolution() -> None:
    _i2c, isl = make_protocol()
    assert isl.cycle_ms() == 303  # 3 x tINT, tINT = 101ms typ at 16 bits (p3)
    isl._resolution = 12
    assert isl.cycle_ms() == 19  # 3 x ~6.3ms, from p6's own n-bit-counter model


def test_time_to_settle_stays_sane_across_a_ticks_wrap() -> None:
    # time.ticks_ms() wraps (at 2**30 on rp2, at a different period on this Unix port), so this
    # has to use ticks_diff()/ticks_add() and never a plain subtraction. A deadline one second in
    # the PAST is the discriminating case: ticks_diff() reports it as past regardless of where
    # the counter happens to sit, while a subtraction reports a hugely positive remaining time
    # whenever the deadline was computed on the other side of a wrap.
    import time as _time

    _i2c, isl = make_protocol()
    isl._settle_until_ms = _time.ticks_add(_time.ticks_ms(), -1000)
    assert isl.time_to_settle_ms() == 0
    isl._settle_until_ms = _time.ticks_add(_time.ticks_ms(), 500)
    assert 0 < isl.time_to_settle_ms() <= 500


# ---------------------------------------------------------------------------
# Protocol layer - thresholds, data, status
# ---------------------------------------------------------------------------


def test_set_thresholds_is_one_four_byte_burst_little_endian() -> None:
    i2c, isl = ready_protocol()
    run(isl.set_thresholds(0x1234, 0xABCD))
    # Table 14's own row labels invite a byte-order mistake, so both values are distinguishable
    # whichever way round they land.
    assert mem_writes(i2c) == [(_REG_THRESHOLDS, bytes([0x34, 0x12, 0xCD, 0xAB]))]


def test_set_thresholds_clamps_out_of_range_counts() -> None:
    i2c, isl = ready_protocol()
    run(isl.set_thresholds(-10, 70000))
    assert mem_writes(i2c) == [(_REG_THRESHOLDS, bytes([0x00, 0x00, 0xFF, 0xFF]))]


def test_read_counts_uses_a_six_byte_burst_not_three_halfwords() -> None:
    # Named for the trap: get_register_struct() returns unpacked[0] only, so passing "<HHH" would
    # silently discard red and blue. This is the single most likely implementation mistake here
    # and it fails silently, so the test asserts all three channels come back distinct.
    i2c, isl = ready_protocol()
    seed(i2c, _REG_DATA, counts_burst(0x1111, 0x2222, 0x3333))
    assert run(isl.read_counts()) == (0x1111, 0x2222, 0x3333)
    assert mem_reads(i2c) == [(_REG_DATA, 6)]


def test_read_counts_raises_rather_than_returning_none_on_a_bus_fault() -> None:
    i2c, isl = ready_protocol()
    fake(i2c).inject_fault("readfrom_mem", OSError(errno_mod.EIO, "no ACK"))
    try:
        run(isl.read_counts())
    except OSError:
        return
    raise AssertionError("a failed data burst must raise, not return None")


def test_every_protocol_read_raises_rather_than_returning_none() -> None:
    # Layer 1 returns None for a malformed request but lets a real OSError through; this layer
    # normalises both into a raise so the reader's try blocks see one shape.
    for call in ("get_device_id", "read_status", "get_config_snapshot", "read_counts"):
        i2c, isl = ready_protocol()
        fake(i2c).inject_fault("readfrom_mem", OSError(errno_mod.EIO, "no ACK"))
        try:
            run(getattr(isl, call)())
        except OSError:
            continue
        raise AssertionError(f"{call}() must raise on a bus fault")


def test_read_status_reads_one_byte_and_clear_brownout_writes_it_low() -> None:
    i2c, isl = ready_protocol()
    seed(i2c, _REG_STATUS, bytes([_STATUS_BOUTF | _STATUS_RGBTHF]))
    assert run(isl.read_status()) == (_STATUS_BOUTF | _STATUS_RGBTHF)
    run(isl.clear_brownout())
    assert mem_writes(i2c) == [(_REG_STATUS, bytes([0x00]))]


def test_get_config_snapshot_is_one_transaction_and_returns_the_raw_bytes_unmodified() -> None:
    i2c, isl = ready_protocol()
    seed(i2c, _REG_CONFIG1, bytes([0x15, 0xA8, 0x0D]))
    assert run(isl.get_config_snapshot()) == bytes([0x15, 0xA8, 0x0D])
    assert mem_reads(i2c) == [(_REG_CONFIG1, 3)]


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


def make_fram_manager() -> "tuple[AsyFramManager, FakeMB85RS64V, SPI]":
    spi_bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(spi_bus, 1, max_size=0x2000)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip, spi_bus


async def _always_synced() -> bool:
    return True


async def _never_synced() -> bool:
    return False


def make_reader(
    name: str,
    *,
    max_module_error: int = 5,
    fram: "AsyFramManager | None" = None,
    ntp: "Callable[[], Coroutine[Any, Any, bool]] | None" = None,
    healthy: bool = True,
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
        fram=fram,
        fram_ntp_callback=ntp,
    )
    run(reader.cfgmgr.setup())
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
    # init's own CONFIG1 burst legitimately leaves a settle deadline pending, and these tests run
    # in zero wall-clock time - so the first conversion after it is marked complete here rather
    # than every test having to sleep 303ms of real time. The settle behaviour itself has its own
    # tests (test_no_sample_is_reported_during_the_settle_window and its siblings).
    reader.isl._settle_until_ms = _time.ticks_ms()
    # Register 0x00 is read-only as the device ID and write-only as the reset command on real
    # hardware; tests/machine.py's flat dict of registers cannot model that split, so setup()'s
    # own reset write leaves 0x46 sitting where the ID should be. Restored here so a later
    # device-ID re-read (the bus-fault confirmation) sees what a real chip would.
    seed(i2c, _REG_ID, bytes([_DEVICE_ID]))
    fake(i2c).log.clear()
    return i2c, reader


def seed_cycle(i2c: I2C, green: int, red: int, blue: int, status: int = 0x00) -> None:
    seed(i2c, _REG_STATUS, bytes([status]))
    seed(i2c, _REG_DATA, counts_burst(green, red, blue))


class _RefusingFramManager:
    # An AsyFramManager stand-in whose allocator is out of space - the real one returns None
    # rather than raising, and __init__ has to degrade to "no persisted calibration" either way.
    def get_timestamped_chunk(self, *_args: object, **_kwargs: object) -> None:
        return None


class _RaisingFramManager:
    def get_timestamped_chunk(self, *_args: object, **_kwargs: object) -> None:
        raise MemoryError("simulated allocation failure")


def test_reader_construction_performs_no_bus_transactions() -> None:
    # Requirement 20, and it is satisfied here or nowhere: tests/test_sensortask_dev.py builds
    # the whole dev object graph against a fake with no ISL registers in it at all.
    FakeTimer.all_timers.clear()
    i2c = make_i2c()
    ISL29125_Reader(i2c, 6, cfg_path=_tmp_cfg_path("no_io"))
    assert fake(i2c).log == []


def test_reader_construction_survives_a_fram_manager_that_refuses_allocation() -> None:
    for manager in (_RefusingFramManager(), _RaisingFramManager()):
        FakeTimer.all_timers.clear()
        i2c = make_i2c()
        reader = ISL29125_Reader(
            i2c, 6, cfg_path=_tmp_cfg_path("no_fram"), fram=manager, fram_ntp_callback=_always_synced,  # type: ignore[arg-type]
        )
        assert reader.ts_storage is None
        assert fake(i2c).log == []


def test_reader_construction_enables_the_internal_pull_up_on_the_int_pin() -> None:
    # The only promoted driver that needs one: this INT is open-drain pull-down (p6), unlike
    # SCD30's push-pull RDY line.
    FakeTimer.all_timers.clear()
    _i2c, reader = make_reader("pullup")
    assert reader.irq_pin.mode == FakePin.IN
    assert reader.irq_pin.pull == FakePin.PULL_UP


def test_init_returns_false_and_logs_errno_10_when_the_chip_is_absent() -> None:
    i2c, reader = make_reader("absent", healthy=False)
    fake(i2c).nak_addresses.add(_ADDR)

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            assert await init_reader(reader, i2c) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    assert errors(counters)[-1] == 10


def test_init_returns_false_and_logs_errno_12_when_the_config_is_unreadable() -> None:
    i2c, reader = make_reader("nocfg")
    reader.cfgmgr.valid = False  # what an unreadable/corrupt config file produces

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            assert await init_reader(reader, i2c) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    assert 12 in errors(counters)


def test_init_returns_false_and_logs_errno_13_when_applying_the_config_raises() -> None:
    i2c, reader = make_reader("cfgwrite")
    real_configure = reader.isl.configure

    async def only_the_startup_burst_fails(**kwargs: object) -> None:
        # setup()'s own configure() call has to succeed for init to reach the step under test;
        # the one carrying `resolution=` is the startup burst _init_isl() issues afterwards.
        if "resolution" in kwargs:
            raise OSError(errno_mod.EIO, "injected")
        await real_configure(**kwargs)  # type: ignore[arg-type]

    reader.isl.configure = only_the_startup_burst_fails  # type: ignore[method-assign]

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            assert await init_reader(reader, i2c) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    assert 13 in errors(counters)


def test_init_arms_the_thresholds_for_the_starting_range() -> None:
    # Easy to miss: without this the part boots with its power-on thresholds and the interrupt
    # path is dead until the first switch would have happened anyway.
    i2c, reader = make_reader("armed")
    with _FastAsyncSleep():
        assert run(init_reader(reader, i2c)) is True
    threshold_writes = [payload for register, payload in mem_writes(i2c) if register == _REG_THRESHOLDS]
    assert len(threshold_writes) == 1
    # Starting on the high range, so only the DOWN crossing is armed: low = 1.5% of full scale,
    # high parked at the resolution's own maximum.
    assert threshold_writes[0] == struct.pack("<HH", 983, 65535)


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
                reader.read_event.set()
                for _ in range(40):
                    await asyncio.sleep(0)
            await _cancel_and_join(task)

    run(scenario())
    assert len(calls) == 3


def test_read_loop_exits_after_max_module_error_consecutive_failures() -> None:
    i2c, reader = make_reader("budget", max_module_error=3)

    async def scenario() -> bool:
        with _FastAsyncSleep():
            assert await init_reader(reader, i2c) is True
            fake(i2c).nak_addresses.add(_ADDR)  # every later transaction fails
            for _ in range(3):
                results = await reader._read_isl()
                assert await reader._error_check(results) is True
            for _ in range(2):
                results = await reader._read_isl()
                await reader._error_check(results)
            return await reader._error_check(await reader._read_isl())

    assert run(scenario()) is False


def test_no_exception_escapes_the_reader_layer() -> None:
    # The reader's never-raise contract, parametrised over every layer-2 entry point the read
    # path touches. Each injected raise must surface as an all-None result, never a traceback.
    for method in ("read_status", "read_counts", "get_config_snapshot", "get_device_id", "configure", "set_thresholds"):
        _i2c, reader = ready_reader("noraise_" + method)

        async def boom(*_args: object, **_kwargs: object) -> None:
            raise OSError(errno_mod.EIO, "injected")

        setattr(reader.isl, method, boom)
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


def test_read_returns_a_narrow_results_tuple_without_cct() -> None:
    # The _error_check trap: base_classes counts a failed read when ANY element is None, and CCT
    # is legitimately None in a dark room - so the wide namedtuple must never reach it.
    i2c, reader = ready_reader("narrow")
    seed_cycle(i2c, 20000, 21000, 22000)
    with _FastAsyncSleep():
        results = run(reader._read_isl())
    assert len(results) == 5
    assert results == (20000, 21000, 22000, _RANGE_HIGH_LUX, results[4])


def test_the_results_tuple_carries_the_range_the_sample_was_taken_on() -> None:
    i2c, reader = ready_reader("carries_range")
    seed_cycle(i2c, 20000, 20000, 20000)
    with _FastAsyncSleep():
        results = run(reader._read_isl())
    assert results[3] == _RANGE_HIGH_LUX
    assert results[4] is not None  # the timestamp, taken first


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
                results = await reader._read_isl()
                assert await reader._error_check(results) is True
                await reader._store_isl(results)
        return await reader.get_error_counter()

    counters = run(scenario())
    assert run(reader.get_data()).CCT is None
    assert errors(counters) == []  # in particular no errno=1, _error_check's own increment
    assert reader._err_cnt_internal == 0


def test_store_produces_the_documented_nested_body() -> None:
    i2c, reader = ready_reader("nested")
    seed_cycle(i2c, 30000, 20000, 10000)
    with _FastAsyncSleep():
        run(reader._store_isl(run(reader._read_isl())))
    body = run(reader.get_dict_data())
    assert set(body) == {"ISL29125"}
    group = body["ISL29125"]
    assert set(group) == {"Lux", "RGB", "HSB", "CCT", "RangeAct", "TS"}
    assert set(group["RGB"]) == {"R", "G", "B"}
    assert set(group["HSB"]) == {"H", "S", "B"}
    assert group["RangeAct"] == _RANGE_HIGH_LUX


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
        assert run(reader.cfgmgr.write_config({"FiltCoeff": 0.1}, reader.cfg_schema))[0] is True
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
    assert [register for register, _length in mem_reads(i2c)].count(_REG_STATUS) == 1


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
    assert 32 in errors(counters)


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
    assert 14 in warnings(counters)  # already on the high range, so the scene wins


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
            run(reader.isl.configure(resolution=12))  # a CONFIG1 write, so a settle is now pending
            assert reader.isl.time_to_settle_ms() > 0
            asyncio.sleep_ms = recording  # type: ignore[assignment]  # _FastAsyncSleep replaced it
            run(reader._read_isl())
    finally:
        asyncio.sleep_ms = real_sleep_ms
    assert slept  # the cycle really did wait rather than reading straight through


def test_the_settle_wait_is_bounded_against_a_stream_of_config_writes() -> None:
    # A possibly-stale sample beats a starved read loop, and the leaky bucket catches a
    # persistent problem anyway.
    _i2c, reader = ready_reader("settle_bound")
    rounds = []
    real_sleep_ms = asyncio.sleep_ms

    async def extending(_ms: int) -> None:
        rounds.append(1)
        run_extend = reader.isl
        run_extend._settle_until_ms = __import__("time").ticks_add(__import__("time").ticks_ms(), 500)
        await real_sleep_ms(0)

    asyncio.sleep_ms = extending  # type: ignore[assignment]
    try:
        reader.isl._settle_until_ms = __import__("time").ticks_add(__import__("time").ticks_ms(), 500)
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
    # Well below AutoRangeUp's own count, so only the saturation fast path can decide this.
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
    green_only = 900  # below AutoRangeDown's own 983 counts
    red_still_bright = 40000
    assert reader._evaluate_range((green_only, red_still_bright, 300), saturated=False) is None
    # Green alone really would have decided to go back down - that is what makes this a proof.
    assert reader._evaluate_range((green_only, 300, 300), saturated=False) == _RANGE_LOW_LUX


def test_switch_points_do_not_chatter_at_the_schema_defaults() -> None:
    # Immediately after a switch up the same light reads u/r of the high range, so the no-chatter
    # condition is u/r > d - swept here as a real state machine, not asserted as arithmetic.
    for up, down in ((85.0, 1.5), (50.0, 0.9375)):  # the defaults, and the worst legal pair
        _i2c, reader = make_reader(f"chatter_{up}")
        reader._ar_up, reader._ar_down, reader._ar_dwell_s = up, down, 0.0
        reader._active_range = _RANGE_LOW_LUX
        up_counts = _fraction_to_counts(up)
        # Just past the up threshold on the low range.
        assert reader._evaluate_range((up_counts, up_counts, up_counts), saturated=False) == _RANGE_HIGH_LUX
        reader._active_range = _RANGE_HIGH_LUX
        # The SAME light, now on the high range: 26.67x fewer counts. It must stay put.
        after = int(up_counts / (10000.0 / 375.0))
        assert reader._evaluate_range((after, after, after), saturated=False) is None


def test_switch_down_is_suppressed_inside_the_dwell_window() -> None:
    import time as _time

    _i2c, reader = make_reader("dwell")
    reader._active_range = _RANGE_HIGH_LUX
    reader._ar_dwell_s = 300.0
    reader._last_switch_ms = _time.ticks_ms()
    assert reader._evaluate_range((10, 10, 10), saturated=False) is None
    reader._ar_dwell_s = 0.0
    assert reader._evaluate_range((10, 10, 10), saturated=False) == _RANGE_LOW_LUX


def test_no_range_decision_is_made_while_auto_is_off_or_a_settle_is_pending() -> None:
    import time as _time

    _i2c, reader = make_reader("guards")
    reader._active_range = _RANGE_LOW_LUX
    reader._range_auto = False
    assert reader._evaluate_range((65535, 65535, 65535), saturated=True) is None
    reader._range_auto = True
    reader.isl._settle_until_ms = _time.ticks_add(_time.ticks_ms(), 500)
    assert reader._evaluate_range((65535, 65535, 65535), saturated=True) is None


def test_thresholds_are_written_before_the_range_bit() -> None:
    # The other order leaves a window where the new gain is live against the old thresholds,
    # which on a bright-to-dim transition fires an immediate spurious interrupt.
    i2c, reader = ready_reader("order")
    with _FastAsyncSleep():
        assert run(reader._switch_range(_RANGE_LOW_LUX)) is True
    writes = mem_writes(i2c)
    assert writes[0][0] == _REG_THRESHOLDS
    assert writes[1][0] == _REG_CONFIG1
    # On the low range only an UP crossing matters: high = 85% of full scale, low parked at 0.
    assert writes[0][1] == struct.pack("<HH", 0, 55705)


def test_thresholds_are_scaled_to_the_active_resolution() -> None:
    # The threshold registers are compared against the RAW ADC value, so a 16-bit-scaled
    # threshold could never be crossed at 12 bits and the hardware fast path would be silently
    # dead there. _fraction_to_counts() itself stays a pure fraction-of-65535 helper.
    i2c, reader = ready_reader("thresh_bits")
    with _FastAsyncSleep():
        run(reader.isl.configure(resolution=12))
        fake(i2c).log.clear()
        run(reader._switch_range(_RANGE_LOW_LUX))
    writes = [payload for register, payload in mem_writes(i2c) if register == _REG_THRESHOLDS]
    assert writes[0] == struct.pack("<HH", 0, 55705 >> 4)  # 3481, inside a 12-bit reading's range


def test_a_partial_switch_is_retried_on_the_next_cycle() -> None:
    # Idempotent by construction: both writes are absolute values, and _active_range is NOT
    # updated when the second one fails, so the next evaluation re-decides and retries.
    i2c, reader = ready_reader("partial")
    with _FastAsyncSleep():
        fake(i2c).inject_fault("writeto_mem", OSError(errno_mod.EIO, "no ACK"), times=1)
        assert run(reader._switch_range(_RANGE_LOW_LUX)) is False
        assert reader._active_range == _RANGE_HIGH_LUX
        assert run(reader._switch_range(_RANGE_LOW_LUX)) is True
        assert reader._active_range == _RANGE_LOW_LUX


def test_a_failed_threshold_write_logs_errno_29_and_the_range_write_logs_errno_30() -> None:
    i2c, reader = ready_reader("switch_errnos")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            fake(i2c).inject_fault("writeto_mem", OSError(errno_mod.EIO, "no ACK"), times=1)
            await reader._switch_range(_RANGE_LOW_LUX)  # the threshold burst fails -> errno 29
            real_configure = reader.isl.configure

            async def failing_configure(**_kwargs: object) -> None:
                raise OSError(errno_mod.EIO, "injected")

            reader.isl.configure = failing_configure  # type: ignore[method-assign]
            await reader._switch_range(_RANGE_LOW_LUX)  # thresholds land, CONFIG1 fails -> errno 30
            reader.isl.configure = real_configure  # type: ignore[method-assign]
        return await reader.get_error_counter()

    counters = run(scenario())
    assert 29 in errors(counters)
    assert 30 in errors(counters)


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
                reader.isl._settle_until_ms = time.ticks_ms()
                reader._last_switch_ms = time.ticks_add(time.ticks_ms(), -1000)
                await reader._read_isl()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert 15 in warnings(counters)


def test_an_interrupt_driven_switch_resets_the_periodic_only_counter() -> None:
    i2c, reader = ready_reader("wrn15_reset")
    reader._ar_dwell_s = 0.0
    with _FastAsyncSleep():
        for index in range(4):
            seed_cycle(i2c, 100, 100, 100, status=0x00) if index % 2 == 0 else seed_cycle(i2c, 65535, 65535, 65535, status=0x00)
            reader.isl._settle_until_ms = time.ticks_ms()
            run(reader._read_isl())
        assert reader._periodic_only_switches != 0
        # The fourth iteration left the reader on the HIGH range, so a DIM scene is what makes
        # this last cycle decide a switch at all - and this time the status byte says the
        # interrupt did fire, which is what has to reset the counter.
        seed_cycle(i2c, 100, 100, 100, status=_STATUS_RGBTHF)
        reader.isl._settle_until_ms = time.ticks_ms()
        run(reader._read_isl())
    assert reader._periodic_only_switches == 0


# ---------------------------------------------------------------------------
# Brownout - R8
# ---------------------------------------------------------------------------


def test_brownout_reapplies_the_whole_configuration_and_discards_one_cycle() -> None:
    i2c, reader = ready_reader("brownout")
    seed_cycle(i2c, 20000, 20000, 20000, status=_STATUS_BOUTF)
    with _FastAsyncSleep():
        results = run(reader._read_isl())
    assert results == (None, None, None, None, None)  # no sample: the chip was in power-down
    writes = mem_writes(i2c)
    assert any(register == _REG_CONFIG1 and len(payload) == 3 for register, payload in writes)
    assert (_REG_STATUS, bytes([0x00])) in writes  # BOUTF written low
    assert any(register == _REG_THRESHOLDS for register, _payload in writes)  # thresholds re-armed


def test_repeated_brownout_warns_once_per_event_not_once_per_cycle() -> None:
    i2c, reader = ready_reader("brownout_flood")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            for _ in range(5):
                seed_cycle(i2c, 20000, 20000, 20000, status=_STATUS_BOUTF)
                await reader._read_isl()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert warnings(counters).count(10) == 1


def test_a_recovered_brownout_warns_again_on_the_next_real_event() -> None:
    i2c, reader = ready_reader("brownout_again")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            seed_cycle(i2c, 20000, 20000, 20000, status=_STATUS_BOUTF)
            await reader._read_isl()
            seed_cycle(i2c, 20000, 20000, 20000, status=0x00)  # supply recovered
            await reader._read_isl()
            seed_cycle(i2c, 20000, 20000, 20000, status=_STATUS_BOUTF)  # and dips again
            await reader._read_isl()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert warnings(counters).count(10) == 2


def test_brownout_does_not_feed_the_leaky_bucket_beyond_its_own_lost_cycle() -> None:
    # One increment, deliberately: the driver genuinely has no sample that cycle. That is the
    # intended cost of a recovered brownout - recovered, but not free.
    i2c, reader = ready_reader("brownout_bucket")

    async def scenario() -> int:
        with _FastAsyncSleep():
            seed_cycle(i2c, 20000, 20000, 20000, status=_STATUS_BOUTF)
            await reader._error_check(await reader._read_isl())
            after_brownout = reader._err_cnt_internal
            seed_cycle(i2c, 20000, 20000, 20000, status=0x00)
            await reader._error_check(await reader._read_isl())
        assert after_brownout == 1
        return reader._err_cnt_internal

    assert run(scenario()) == 0  # and a good cycle immediately pays it back


def test_a_brownout_recovery_write_failure_logs_errno_33() -> None:
    i2c, reader = ready_reader("brownout_fail")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            seed_cycle(i2c, 20000, 20000, 20000, status=_STATUS_BOUTF)
            fake(i2c).inject_fault("writeto_mem", OSError(errno_mod.EIO, "no ACK"), times=5)
            await reader._read_isl()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert 33 in errors(counters)


# ---------------------------------------------------------------------------
# Live config read-back and divergence - R6
# ---------------------------------------------------------------------------


def test_read_sensor_dict_reports_the_five_hardware_backed_fields() -> None:
    _i2c, reader = ready_reader("sensor_dict")
    reader._range_auto = False
    with _FastAsyncSleep():
        result = run(reader._read_sensor_dict())
    assert set(result) == {"Resolution", "Range", "IrCompOffset", "IrCompAdjust", "AutoRangePersist"}


def test_read_sensor_dict_key_names_produce_no_unknown_key_warning() -> None:
    # _get_dict_cfg() warns (wrnno=1) on any key the schema does not carry, so a typo here would
    # log a warning on every GET /sensors rather than failing anywhere visible.
    _i2c, reader = ready_reader("sensor_dict_keys")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            await reader.get_dict_cfg()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert 1 not in warnings(counters)


def test_range_readback_is_suppressed_while_autorange_is_on() -> None:
    # Under auto-range the chip's RNG bit is the state machine's choice, not the user's setting -
    # reporting it as the Range CONFIG field would overwrite the stored preference.
    _i2c, reader = ready_reader("range_readback")
    reader._range_auto = True
    with _FastAsyncSleep():
        assert "Range" not in run(reader._read_sensor_dict())
    reader._range_auto = False
    with _FastAsyncSleep():
        assert "Range" in run(reader._read_sensor_dict())


def test_read_sensor_dict_returns_all_none_and_logs_errno_28_on_a_bus_fault() -> None:
    # Caught HERE rather than left to _get_dict_cfg()'s own guard: that outer guard skips the
    # whole dict update and leaves the fields showing persisted values as if they were live.
    i2c, reader = ready_reader("sensor_dict_fail")

    async def scenario() -> "tuple[dict[str, int | float | str | bool | None], ErrorLog]":
        with _FastAsyncSleep():
            fake(i2c).nak_addresses.add(_ADDR)
            result = await reader._read_sensor_dict()
        return result, await reader.get_error_counter()

    result, counters = run(scenario())
    assert set(result) == {"Resolution", "Range", "IrCompOffset", "IrCompAdjust", "AutoRangePersist"}
    assert all(value is None for value in result.values())
    assert 28 in errors(counters)


def test_read_sensor_dict_detects_a_diverged_mode_and_reapplies_the_shadow() -> None:
    # The divergence the OLD five-decoded-value return could not see: mode, SYNC, CONVEN and
    # INTSEL are exactly the bits a brownout or a stray write zeroes, and decoding them away
    # first is what would make this check blind to the thing it exists for.
    i2c, reader = ready_reader("divergence")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            shadow = reader.isl.encode_shadow()
            seed(i2c, _REG_CONFIG1, bytes([shadow[0] & ~0x07, shadow[1], shadow[2]]))  # mode zeroed
            await reader._read_sensor_dict()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert warnings(counters).count(10) == 1
    assert any(register == _REG_CONFIG1 and len(payload) == 3 for register, payload in mem_writes(i2c))


def test_a_reserved_bit_difference_is_not_reported_as_divergence() -> None:
    # p9: "the value of the reserved bit can change without any notice" - a driver comparing raw
    # bytes would eventually report a divergence that is not one.
    i2c, reader = ready_reader("reserved_bits")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            shadow = reader.isl.encode_shadow()
            seed(i2c, _REG_CONFIG1, bytes([shadow[0] | 0xC0, shadow[1] | 0x40, shadow[2] | 0xE0]))
            await reader._read_sensor_dict()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert 10 not in warnings(counters)


def test_get_dict_cfg_excludes_the_command_only_field() -> None:
    # ConfigManager.get_dict() is all-or-nothing and would KeyError on a key it never persisted.
    _i2c, reader = ready_reader("cfg_excl")
    with _FastAsyncSleep():
        body = run(reader.get_dict_cfg())
    assert "ISLResetCal" not in body["ISL29125"]
    assert "SampleInterv" in body["ISL29125"]
    assert set(body["ISL29125"]) == {
        "SampleInterv", "Resolution", "RangeAuto", "Range", "AutoRangeUp", "AutoRangeDown",
        "AutoRangeSettle", "AutoRangePersist", "AutoRangeDwell", "IrCompOffset", "IrCompAdjust",
        "FiltCoeff",
    }


# ---------------------------------------------------------------------------
# Config surface - the thirteen pushes, the setters and the five getters
# ---------------------------------------------------------------------------


def test_every_schema_field_has_a_push_callback() -> None:
    _i2c, reader = make_reader("push_coverage")
    names = [field[0] for field in reader.cfg_schema]
    assert len(names) == 13
    assert sorted(reader._push_callbacks) == sorted(names)


def test_only_the_five_hardware_backed_fields_have_a_getter() -> None:
    # A software-only knob has nothing to read back, and _recover_failed_push() skips a
    # command-only field by design - a getter for either would be dead code.
    _i2c, reader = make_reader("get_coverage")
    assert sorted(reader._get_callbacks) == [
        "AutoRangePersist", "IrCompAdjust", "IrCompOffset", "Range", "Resolution",
    ]


def test_each_push_rejects_the_wrong_type_without_touching_the_bus() -> None:
    # type(value) is not int, deliberately NOT isinstance: isinstance(True, int) is True in
    # Python, so a bool would slip straight through into an int field.
    i2c, reader = ready_reader("push_types")
    wrong: dict[str, int | float | str | bool | None] = {
        "SampleInterv": True, "Resolution": 16.0, "RangeAuto": 1, "Range": "10000",
        "AutoRangeUp": 85, "AutoRangeDown": 2, "AutoRangeSettle": 1.0, "AutoRangePersist": 4.0,
        "AutoRangeDwell": 10, "IrCompOffset": False, "IrCompAdjust": 40.0, "FiltCoeff": 0,
        "ISLResetCal": 1,
    }
    with _FastAsyncSleep():
        for field, value in wrong.items():
            assert run(reader._push_callbacks[field](value)) is False, field
    assert mem_writes(i2c) == []


def test_pushing_resolution_reaches_the_chip_byte_exactly() -> None:
    i2c, reader = ready_reader("push_resolution")
    with _FastAsyncSleep():
        assert run(reader._push_callbacks["Resolution"](12)) is True
    config1 = next(payload for register, payload in mem_writes(i2c) if register == _REG_CONFIG1)
    assert config1[0] & _BITS_12


def test_pushing_ir_compensation_reaches_config2_without_touching_config1() -> None:
    i2c, reader = ready_reader("push_ir")
    with _FastAsyncSleep():
        assert run(reader._push_callbacks["IrCompOffset"](1)) is True
        assert run(reader._push_callbacks["IrCompAdjust"](63)) is True
    writes = mem_writes(i2c)
    assert all(register == _REG_CONFIG2 for register, _payload in writes)
    assert writes[-1][1][0] == 0x80 | 63


def test_pushing_autorange_persist_reaches_config3() -> None:
    i2c, reader = ready_reader("push_persist")
    with _FastAsyncSleep():
        assert run(reader._push_callbacks["AutoRangePersist"](8)) is True
    writes = mem_writes(i2c)
    assert writes[-1][0] == _REG_CONFIG2  # the 2-byte burst that carries CONFIG3
    assert writes[-1][1][1] & 0x0C == 0x0C  # PRST = 11 -> 8 cycles


def test_pushing_the_software_knobs_changes_only_driver_state() -> None:
    i2c, reader = ready_reader("push_software")
    with _FastAsyncSleep():
        assert run(reader._push_callbacks["SampleInterv"](7)) is True
        assert run(reader._push_callbacks["AutoRangeUp"](90.0)) is True
        assert run(reader._push_callbacks["AutoRangeDown"](0.5)) is True
        assert run(reader._push_callbacks["AutoRangeSettle"](5)) is True
        assert run(reader._push_callbacks["AutoRangeDwell"](30.0)) is True
        assert run(reader._push_callbacks["FiltCoeff"](0.25)) is True
    assert run(reader.trigger_period.get_value()) == 7
    assert reader._ar_up == 90.0
    assert reader._ar_down == 0.5
    assert reader.isl.settle_cycles == 5
    assert reader._ar_dwell_s == 30.0
    assert mem_writes(i2c) == []


def test_autorange_down_is_rejected_when_it_violates_the_cross_field_constraint() -> None:
    # FieldSchema's per-field min/max cannot express a relation between two fields, so the driver
    # enforces d <= u/(2r) itself - and it has to hold whichever side moves.
    _i2c, reader = ready_reader("cross_field")

    async def scenario() -> "ErrorLog":
        reader._ar_up, reader._ar_down = 85.0, 1.5
        assert await reader.set_autorange_down(3.0) is False  # 3.0 > 85/53.33 = 1.59
        assert reader._ar_down == 1.5  # unchanged
        assert await reader.set_autorange_down(1.5) is True
        assert await reader.set_autorange_up(50.0) is False  # 1.5 > 50/53.33 = 0.94
        assert reader._ar_up == 85.0
        assert await reader.set_autorange_up(95.0) is True  # raising u is always safe
        return await reader.get_error_counter()

    counters = run(scenario())
    assert errors(counters).count(27) == 2


def test_turning_autorange_off_writes_intsel_zero_and_applies_the_stored_range() -> None:
    # Parking the thresholds cannot disarm the interrupt: the part fires on "below OR EQUAL TO"
    # the low threshold, so a low threshold of 0x0000 still interrupts in total darkness.
    i2c, reader = ready_reader("auto_off")
    with _FastAsyncSleep():
        assert run(reader.set_range(_RANGE_LOW_LUX)) is True
        assert run(reader.set_range_auto(flag=False)) is True
    config1, _config2, config3 = mem_writes(i2c)[-1][1]
    assert config3 & 0x03 == 0x00  # INTSEL = "No Interrupt"
    assert config1 & _RNG_HIGH == 0  # the stored fixed range applied
    assert reader._active_range == _RANGE_LOW_LUX


def test_turning_autorange_back_on_rearms_intsel_and_the_thresholds() -> None:
    i2c, reader = ready_reader("auto_on")
    with _FastAsyncSleep():
        run(reader.set_range_auto(flag=False))
        fake(i2c).log.clear()
        assert run(reader.set_range_auto(flag=True)) is True
    writes = mem_writes(i2c)
    assert any(register == _REG_THRESHOLDS for register, _payload in writes)
    config = next(payload for register, payload in writes if register in (_REG_CONFIG1, _REG_CONFIG2))
    assert config[-1] & 0x03 == _INTSEL_GREEN


def test_turning_autorange_off_logs_errno_38_when_that_write_fails() -> None:
    i2c, reader = ready_reader("auto_off_fail")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            fake(i2c).inject_fault("writeto_mem", OSError(errno_mod.EIO, "no ACK"), times=1)
            assert await reader.set_range_auto(flag=False) is False
        return await reader.get_error_counter()

    counters = run(scenario())
    assert 38 in errors(counters)


def test_setting_range_while_autorange_is_on_stores_the_preference_without_a_chip_write() -> None:
    i2c, reader = ready_reader("range_pref")
    with _FastAsyncSleep():
        assert run(reader.set_range(_RANGE_LOW_LUX)) is True
    assert reader._fixed_range == _RANGE_LOW_LUX
    assert reader._active_range == _RANGE_HIGH_LUX  # the state machine still owns the chip
    assert mem_writes(i2c) == []


def test_set_range_rejects_a_value_outside_the_two_real_ranges() -> None:
    _i2c, reader = ready_reader("range_bad")

    async def scenario() -> "ErrorLog":
        assert await reader.set_range(5000) is False
        return await reader.get_error_counter()

    assert 18 in errors(run(scenario()))


def test_set_trigger_secs_logs_errno_25_and_does_not_raise_on_a_bad_value() -> None:
    _i2c, reader = make_reader("trigger_bad")

    async def scenario() -> "ErrorLog":
        assert await reader.set_trigger_secs("not-a-number") is False  # type: ignore[arg-type]
        assert await reader.set_trigger_secs(float("inf")) is False  # OverflowError, not ValueError
        assert await reader.set_trigger_secs(0) is False
        assert await reader.set_trigger_secs(3601) is False
        assert await reader.set_trigger_secs(30) is True
        await reader.pr.setup()
        return await reader.get_error_counter()

    counters = run(scenario())
    # One per rejected value: a non-number, +inf (OverflowError, not ValueError), and both
    # out-of-range ends. The valid one must not be counted.
    assert errors(counters).count(25) == 4
    assert run(reader.trigger_period.get_value()) == 30


def test_every_hardware_setter_logs_its_own_errno_on_a_bus_fault() -> None:
    expected = {
        "set_resolution": (16, 12),
        "set_autorange_persist": (24, 8),
        "set_ir_comp_offset": (20, 1),
        "set_ir_comp_adjust": (22, 63),
    }
    for method, (errno_value, argument) in expected.items():
        i2c, reader = ready_reader("setter_" + method)

        async def scenario(
            method: str = method, argument: int = argument, i2c: I2C = i2c, reader: ISL29125_Reader = reader,
        ) -> "ErrorLog":
            with _FastAsyncSleep():
                fake(i2c).nak_addresses.add(_ADDR)
                assert await getattr(reader, method)(argument) is False
            return await reader.get_error_counter()

        counters = run(scenario())
        assert errno_value in errors(counters), method


def test_every_getter_logs_its_own_errno_and_returns_none_on_a_bus_fault() -> None:
    expected = {"get_resolution": 15, "get_range": 17, "get_ir_comp_offset": 19, "get_ir_comp_adjust": 21, "get_autorange_persist": 23}
    for method, errno_value in expected.items():
        i2c, reader = ready_reader("getter_" + method)

        async def scenario(method: str = method, i2c: I2C = i2c, reader: ISL29125_Reader = reader) -> "ErrorLog":
            with _FastAsyncSleep():
                fake(i2c).nak_addresses.add(_ADDR)
                assert await getattr(reader, method)() is None
            return await reader.get_error_counter()

        counters = run(scenario())
        assert errno_value in errors(counters), method


def test_the_getters_read_the_live_chip_not_the_shadow() -> None:
    i2c, reader = ready_reader("getters_live")
    with _FastAsyncSleep():
        seed(i2c, _REG_CONFIG1, bytes([_MODE_RGB | _BITS_12, 0x80 | 7, _INTSEL_GREEN | 0x04]))
        assert run(reader.get_resolution()) == 12
        assert run(reader.get_range()) == _RANGE_LOW_LUX
        assert run(reader.get_ir_comp_offset()) == 1
        assert run(reader.get_ir_comp_adjust()) == 7
        assert run(reader.get_autorange_persist()) == 2


def test_a_failed_push_recovers_through_the_getter_then_the_snapshot_then_the_default() -> None:
    # _recover_failed_push()'s own chain: a live read-back first, then the pre-write snapshot,
    # then the schema default - and every rung it accepts is validated against the schema, so a
    # misbehaving chip cannot get an out-of-schema value persisted.
    i2c, reader = ready_reader("recover")

    async def scenario() -> "dict[str, Any]":
        with _FastAsyncSleep():
            real_configure = reader.isl.configure

            async def failing(**_kwargs: object) -> None:
                raise OSError(errno_mod.EIO, "injected")

            reader.isl.configure = failing  # type: ignore[method-assign]
            # The chip reads back a resolution the schema accepts, so recovery uses it.
            seed(i2c, _REG_CONFIG1, bytes([_MODE_RGB | _BITS_12, 0x00, 0x00]))
            results = await reader._set_dict_cfg({"Resolution": 12}, reader.cfg_schema)
            reader.isl.configure = real_configure  # type: ignore[method-assign]
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

            reader.isl.configure = failing  # type: ignore[method-assign]
            reader._get_callbacks["Resolution"] = nonsense
            await reader._set_dict_cfg({"Resolution": 12}, reader.cfg_schema)
            stored = await reader.cfgmgr.get_dict(["Resolution"])
        assert stored is not None
        return stored

    assert run(scenario())["Resolution"] == 16  # the pre-write snapshot, not the chip's nonsense


def test_reset_cal_returns_valid_twice_in_a_row() -> None:
    # A recalibration that finds nothing to discard has not FAILED - returning False would run
    # _recover_failed_push() on a field that cannot be recovered.
    _i2c, reader = ready_reader("resetcal_twice")

    async def scenario() -> "list[Any]":
        with _FastAsyncSleep():
            first = await reader._set_dict_cfg({"ISLResetCal": True}, reader.cfg_schema)
            second = await reader._set_dict_cfg({"ISLResetCal": True}, reader.cfg_schema)
        return [first["ISLResetCal"], second["ISLResetCal"]]

    assert run(scenario()) == ["Valid", "Valid"]


def test_reset_cal_with_false_is_a_no_op() -> None:
    _i2c, reader = make_reader("resetcal_false")
    reader._gain_ratio = 24.0
    assert run(reader.reset_gain_calibration(flag=False)) is False
    assert reader._gain_ratio == 24.0
    assert run(reader._push_callbacks["ISLResetCal"](False)) is True  # still a successful push


# ---------------------------------------------------------------------------
# Gain-ratio calibration - R12-R15
# ---------------------------------------------------------------------------


def test_gain_ratio_round_trips_through_the_fram_chunk() -> None:
    manager, chip, spi_bus = make_fram_manager()
    run(manager.setup())
    i2c, reader = ready_reader("gain_rt", fram=manager, ntp=_always_synced)
    assert reader.ts_storage is not None

    async def scenario() -> float | None:
        reader._gain_ratio = 25.25
        await reader._persist_gain_ratio()
        # A real reboot re-constructs everything downstream of the surviving chip memory.
        manager2 = AsyFramManager(spi_bus, 1, max_size=0x2000)
        manager2.fram._spidev.spi._spi = chip
        await manager2.setup()
        FakeTimer.all_timers.clear()
        rebooted = ISL29125_Reader(
            i2c, 6, cfg_path=_tmp_cfg_path("gain_rt2"), fram=manager2, fram_ntp_callback=_always_synced,
        )
        await rebooted.cfgmgr.setup()
        await rebooted.pr.setup()
        await rebooted._load_gain_ratio()
        return rebooted._gain_ratio

    restored = run(scenario())
    assert restored is not None
    assert abs(restored - 25.25) < 1e-3  # single precision, deliberately: rp2's float is 4 bytes


def test_a_corrupt_or_implausible_stored_ratio_falls_back_to_nominal_with_a_warning() -> None:
    manager, _chip, _spi = make_fram_manager()
    run(manager.setup())
    _i2c, reader = ready_reader("gain_bad", fram=manager, ntp=_always_synced)
    assert reader.ts_storage is not None

    async def scenario() -> "ErrorLog":
        reader._gain_ratio = 99.0  # outside the 20-34 plausibility band
        await reader._persist_gain_ratio()
        reader._gain_ratio = _GAIN_RATIO_NOMINAL
        await reader._load_gain_ratio()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert reader._gain_ratio == _GAIN_RATIO_NOMINAL
    assert 13 in warnings(counters)


def test_an_absent_chunk_degrades_to_nominal_with_no_error_and_no_crash() -> None:
    _i2c, reader = ready_reader("gain_absent")  # no fram= at all
    assert reader.ts_storage is None

    async def scenario() -> "ErrorLog":
        await reader._load_gain_ratio()
        assert await reader._clear_gain_ratio() is True
        await reader._persist_gain_ratio()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert reader._gain_ratio == _GAIN_RATIO_NOMINAL
    assert 11 in warnings(counters)
    assert errors(counters) == []  # a missing chunk is expected, not an error


def test_a_fresh_unit_with_storage_warns_that_there_is_no_backup_yet() -> None:
    manager, _chip, _spi = make_fram_manager()
    run(manager.setup())
    _i2c, reader = ready_reader("gain_fresh", fram=manager, ntp=_always_synced)

    async def scenario() -> "ErrorLog":
        await reader._load_gain_ratio()
        return await reader.get_error_counter()

    assert 11 in warnings(run(scenario()))


def test_reset_cal_clears_the_chunk_and_returns_to_nominal() -> None:
    manager, _chip, _spi = make_fram_manager()
    run(manager.setup())
    _i2c, reader = ready_reader("gain_reset", fram=manager, ntp=_always_synced)

    async def scenario() -> "tuple[float, Any]":
        reader._gain_ratio = 25.0
        await reader._persist_gain_ratio()
        await reader.reset_gain_calibration(flag=True)
        ratio_after_reset = reader._gain_ratio
        await reader._load_gain_ratio()  # nothing left to restore
        return ratio_after_reset, await reader.get_mem_status()

    ratio_after_reset, mem_status = run(scenario())
    assert ratio_after_reset == _GAIN_RATIO_NOMINAL
    assert mem_status == (_GAIN_RATIO_NOMINAL, None)


def test_the_gain_correction_is_one_on_the_low_range_and_learned_over_nominal_on_the_high_one() -> None:
    # The LOW range is the reference, so the learned ratio only ever corrects the high one -
    # correcting both would make the absolute scale drift with the calibration.
    _i2c, reader = make_reader("gain_direction")
    reader._gain_ratio = 25.9
    assert reader._gain_correction(_RANGE_LOW_LUX) == 1.0
    assert abs(reader._gain_correction(_RANGE_HIGH_LUX) - 25.9 / _GAIN_RATIO_NOMINAL) < 1e-9
    # A unit whose real high-range full scale EXCEEDS nominal produces fewer counts for the same
    # light, so the reported lux has to be scaled UP - the direction this assertion pins.
    reader._gain_ratio = 30.0
    assert reader._gain_correction(_RANGE_HIGH_LUX) > 1.0


def test_learning_is_skipped_during_settle_and_dwell_and_while_auto_is_off() -> None:
    import time as _time

    i2c, reader = ready_reader("learn_guards")
    with _FastAsyncSleep():
        reader._gain_learn_ms = _time.ticks_add(_time.ticks_ms(), -4_000_000)  # the period has elapsed
        reader._ar_dwell_s = 0.0
        reader._range_auto = False
        fake(i2c).log.clear()
        run(reader._learn_gain_ratio(20000))
        assert mem_writes(i2c) == []  # auto off
        reader._range_auto = True
        reader.isl._settle_until_ms = _time.ticks_add(_time.ticks_ms(), 500)
        run(reader._learn_gain_ratio(20000))
        assert mem_writes(i2c) == []  # settle pending
        reader.isl._settle_until_ms = _time.ticks_ms()
        reader._ar_dwell_s = 300.0
        reader._last_switch_ms = _time.ticks_ms()
        run(reader._learn_gain_ratio(20000))
        assert mem_writes(i2c) == []  # inside the dwell window


def test_learning_is_skipped_outside_the_overlap_band() -> None:
    import time as _time

    i2c, reader = ready_reader("learn_band")
    with _FastAsyncSleep():
        reader._gain_learn_ms = _time.ticks_add(_time.ticks_ms(), -4_000_000)
        reader._ar_dwell_s = 0.0
        fake(i2c).log.clear()
        run(reader._learn_gain_ratio(10))  # far below AutoRangeDown's own count
        assert mem_writes(i2c) == []
        run(reader._learn_gain_ratio(65535))  # clipped, far above AutoRangeUp's
        assert mem_writes(i2c) == []


def test_learning_takes_a_paired_reading_and_returns_to_the_original_range() -> None:
    import time as _time

    i2c, reader = ready_reader("learn_pair")
    with _FastAsyncSleep():
        reader._gain_learn_ms = _time.ticks_add(_time.ticks_ms(), -4_000_000)
        reader._ar_dwell_s = 0.0
        # On the high range, reading 2000 counts; the low range sees the same light at ~25.9x.
        seed(i2c, _REG_DATA, counts_burst(51801, 51801, 51801))
        run(reader._learn_gain_ratio(2000))
    assert reader._active_range == _RANGE_HIGH_LUX  # back where it started
    # ratio = low/high = 51800/2000 = 25.9, low-passed one step from the nominal 26.667.
    assert reader._gain_ratio < _GAIN_RATIO_NOMINAL
    assert abs(reader._gain_ratio - (_GAIN_RATIO_NOMINAL + 0.1 * (25.9 - _GAIN_RATIO_NOMINAL))) < 1e-9


def test_an_implausible_learned_ratio_is_rejected_with_a_warning() -> None:
    import time as _time

    i2c, reader = ready_reader("learn_bad")

    async def scenario() -> "ErrorLog":
        with _FastAsyncSleep():
            reader._gain_learn_ms = _time.ticks_add(_time.ticks_ms(), -4_000_000)
            reader._ar_dwell_s = 0.0
            # The paired low-range reading and the high-range one differ by only ~10x here,
            # which is nowhere near the 20-34 band a real part's range ratio has to fall in.
            seed(i2c, _REG_DATA, counts_burst(20000, 20000, 20000))
            await reader._learn_gain_ratio(2000)
        return await reader.get_error_counter()

    counters = run(scenario())
    assert reader._gain_ratio == _GAIN_RATIO_NOMINAL
    assert 13 in warnings(counters)


# ---------------------------------------------------------------------------
# Trigger divider, registration and data access - R16, R48-R58
# ---------------------------------------------------------------------------


def test_base_trigger_produces_one_read_event_per_sample_interval() -> None:
    _i2c, reader = make_reader("divider")

    async def scenario() -> int:
        await reader.set_trigger_secs(3)
        fired = 0
        task = reader.start_asy_trigger()
        for _ in range(9):
            reader.base_trigger_event.set()
            for _ in range(5):
                await asyncio.sleep(0)
            if _drain_flag(reader.read_event):
                fired += 1
        await _cancel_and_join(task)
        return fired

    assert run(scenario()) == 3


async def _cancel_and_join(task: "asyncio.Task[Any]") -> None:
    # Cancelling alone is not enough for a task parked on ThreadSafeFlag.wait(): the await is
    # what lets the cancellation unwind through wait() and UNREGISTER its poll object. Leaking
    # those registrations grows asyncio's shared pollfds array, which is the confirmed Unix-port
    # bug digital_twin/unix_port_poll_prewarm.py documents - and it segfaults the process, one
    # test file at a time, with no failing assertion anywhere to point at it.
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def _drain_flag(flag: "asyncio.ThreadSafeFlag") -> bool:
    # Reads ThreadSafeFlag's own `state` and clears it, rather than probing with a bounded
    # wait_for_ms(): each such probe registers and abandons a poll object, which segfaults this
    # Unix port (the same confirmed extmod/modselect.c dangling-pointer bug
    # digital_twin/unix_port_poll_prewarm.py exists for). A direct state read is also what the
    # question actually is - "was it set?" - with no scheduling involved at all.
    was_set = bool(flag.state)
    flag.clear()
    return was_set


def test_changing_the_sample_interval_takes_effect_on_the_next_boundary() -> None:
    _i2c, reader = make_reader("divider_live")

    async def scenario() -> "list[int]":
        await reader.set_trigger_secs(2)
        fired = []
        task = reader.start_asy_trigger()
        for tick in range(4):
            reader.base_trigger_event.set()
            for _ in range(5):
                await asyncio.sleep(0)
            if _drain_flag(reader.read_event):
                fired.append(tick)
            if tick == 1:
                await reader.set_trigger_secs(1)
        await _cancel_and_join(task)
        return fired

    assert run(scenario()) == [1, 2, 3]


def test_the_timer_and_the_falling_edge_irq_both_reach_the_read_event() -> None:
    _i2c, reader = make_reader("wiring")
    reader.start_timer()
    timer = reader.trigger_timer
    assert timer.period == 1000
    assert reader.irq_pin._irq_trigger == FakePin.IRQ_FALLING  # active-low, open-drain (p6)

    async def scenario() -> "tuple[bool, bool]":
        assert timer.callback is not None
        timer.callback(timer)  # one hardware tick
        from_timer = _drain_flag(reader.base_trigger_event)
        reader.irq_pin.trigger_irq()  # one real falling edge
        from_irq = _drain_flag(reader.read_event)
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


def test_stop_timer_deinits_the_real_timer() -> None:
    _i2c, reader = make_reader("timer_stop")
    reader.start_timer()
    reader.stop_timer()
    assert reader.trigger_timer.deinit_called is True


def test_task_and_timer_starters_are_registered() -> None:
    _i2c, reader = make_reader("starters")
    assert [fn.__name__ for fn in reader.get_task_starters()] == ["start_asy_read", "start_asy_trigger"]
    assert [fn.__name__ for fn in reader.get_timer_starters()] == ["start_timer"]


def test_get_data_returns_the_all_none_namedtuple_before_the_first_read() -> None:
    _i2c, reader = make_reader("predata")
    data = run(reader.get_data())
    assert isinstance(data, ISL29125)
    assert data == ISL29125(None, None, None, None, None, None, None, None, None, None)


def test_get_mem_status_reports_the_ratio_and_its_timestamp() -> None:
    _i2c, reader = make_reader("memstatus")
    assert run(reader.get_mem_status()) == (_GAIN_RATIO_NOMINAL, None)



if __name__ == "__main__":
    import microtest

    microtest.run(globals())
