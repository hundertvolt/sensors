import asyncio
import struct

from _fram_chip_fake import FakeMB85RS64V

import asy_spi_driver
from asy_fram_manager import AsyFramManager
from asy_spi_driver import SPI
from crc_checks import CRC32
from voc_algorithm import VOCAlgorithm

# Same one-process-per-test-file FRAM chip swap as tests/test_asy_sgp40_driver.py and every other
# FRAM-touching test file - see their own comments.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def make_fram_manager() -> "tuple[AsyFramManager, FakeMB85RS64V, SPI]":
    spi_bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(spi_bus, 1, max_size=0x2000)
    chip = manager.fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return manager, chip, spi_bus


def make_fram_manager_sharing(spi_bus: SPI) -> AsyFramManager:
    # A second, independently-allocating AsyFramManager sharing the first's underlying spi_bus (and
    # so its FakeMB85RS64V chip/memory) - simulates a real reboot's fresh manager object replaying
    # the identical get_chunk() call against surviving on-chip data, matching
    # tests/test_asy_sgp40_driver.py's/tests/test_fram_integration.py's own pattern.
    return AsyFramManager(spi_bus, 1, max_size=0x2000)

# ---------------------------------------------------------------------------
# get_params_memsize / initial state
# ---------------------------------------------------------------------------


def test_get_params_memsize_matches_struct_size() -> None:
    assert VOCAlgorithm.get_params_memsize() == 256 == struct.calcsize("32q")


def test_fresh_instance_has_zeroed_dynamic_state() -> None:
    algo = VOCAlgorithm()
    assert algo.params.muptime == 0
    assert algo.params.msraw == 0
    assert algo.params.mvoc_index == 0
    # __init__ delegates to reset(); vocalgorithm_init() (called separately by the driver) is what
    # actually fills in the fixed-point defaults - confirms these two steps stay distinct.
    assert algo.params.mvoc_index_offset == 0


def test_init_sets_up_default_tuning_parameters() -> None:
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    # mvoc_index_offset = f16(100) = 100 * 65536
    assert algo.params.mvoc_index_offset == 100 * 65536
    assert algo.params.muptime == 0
    assert algo.params.msraw == 0
    assert algo.params.mvoc_index == 0


# ---------------------------------------------------------------------------
# vocalgorithm_process - blackout, clamping, output range
# ---------------------------------------------------------------------------


def test_process_during_initial_blackout_only_advances_uptime() -> None:
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    for _ in range(45):  # _VOCALGORITHM_INITIAL_BLACKOUT
        voc_index = algo.vocalgorithm_process(30000)
        assert voc_index == 0  # mvoc_index never touched yet, cast(0 + f16(0.5)) == 0
    assert algo.params.muptime == 45 * 65536


def test_process_after_blackout_produces_index_in_documented_range() -> None:
    # Datasheet Table 1: VOC Index output range is 1-500. Blackout uses <=, so muptime==45s (the
    # 46th call, i==45) is still the last blackout call - real processing starts at i==46.
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    last = 0
    for i in range(120):
        last = algo.vocalgorithm_process(30000 + (i % 5) * 200)
        if i >= 46:
            assert 1 <= last <= 500
    assert 1 <= last <= 500


def test_process_sraw_out_of_valid_range_still_produces_an_index() -> None:
    # sraw <= 0 or >= 65000 skips updating msraw (datasheet SRAW_VOC is 0-65535 ticks; the
    # algorithm's own valid processing window is narrower) but must never raise or hang.
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    for _ in range(50):
        algo.vocalgorithm_process(30000)  # past blackout
    voc_index = algo.vocalgorithm_process(0)
    assert isinstance(voc_index, int)
    voc_index = algo.vocalgorithm_process(65535)
    assert isinstance(voc_index, int)


def test_process_sraw_clamped_to_20001_52767_window() -> None:
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    for _ in range(50):
        algo.vocalgorithm_process(30000)
    algo.vocalgorithm_process(1)  # below 20001 -> clamped to 20001 internally
    assert algo.params.msraw == (20001 - 20000) * 65536
    algo.vocalgorithm_process(60000)  # above 52767 -> clamped to 52767 internally
    assert algo.params.msraw == (52767 - 20000) * 65536


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


def test_reset_reinitializes_to_fresh_state() -> None:
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    for i in range(60):
        algo.vocalgorithm_process(30000 + i * 50)
    assert algo.params.muptime > 0
    algo.vocalgorithm_reset()
    assert algo.params.muptime == 0
    assert algo.params.msraw == 0
    assert algo.params.mvoc_index == 0
    assert algo.params.mvoc_index_offset == 100 * 65536  # vocalgorithm_init() ran again


# ---------------------------------------------------------------------------
# get_states / set_states - Sensirion's own short-interruption-only API
# ---------------------------------------------------------------------------


def test_get_states_set_states_round_trip_mean_and_std() -> None:
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    for i in range(60):
        algo.vocalgorithm_process(30000 + i * 37)
    state0, state1 = algo._vocalgorithm_get_states()

    fresh = VOCAlgorithm()
    fresh.vocalgorithm_init()
    fresh._vocalgorithm_set_states(state0, state1)
    assert fresh.params.msraw == state0
    got0, got1 = fresh._vocalgorithm_get_states()
    assert got1 == state1


# ---------------------------------------------------------------------------
# vocalgorithm_proc_ser_des - pack/unpack full-state persistence (the FRAM backup mechanism)
# ---------------------------------------------------------------------------


def test_proc_ser_des_no_buf_never_serializes_or_deserializes() -> None:
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    voc_index, serialized, deserialized = algo.vocalgorithm_proc_ser_des(30000, None, serialize=True, deserialize=True)
    assert isinstance(voc_index, int)
    assert serialized is False
    assert deserialized is False


def test_proc_ser_des_serialize_writes_full_state_into_buffer() -> None:
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    for i in range(50):
        algo.vocalgorithm_process(30000 + i * 11)
    buf = bytearray(VOCAlgorithm.get_params_memsize())
    _voc_index, serialized, deserialized = algo.vocalgorithm_proc_ser_des(31000, buf, serialize=True, deserialize=False)
    assert serialized is True
    assert deserialized is False
    assert buf != bytearray(len(buf))  # not left all-zero


def test_pack_into_unpack_from_round_trip_is_byte_exact() -> None:
    # Pure pack/unpack fidelity, via DFRobot_vocalgorithmParams directly - vocalgorithm_proc_ser_des()
    # itself always also runs vocalgorithm_process() around (de)serializing (see the next test), so
    # isolating just the struct round-trip needs the params object's own methods, not that wrapper.
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    for i in range(80):
        algo.vocalgorithm_process(30000 + (i * 53) % 4000)
    buf = bytearray(VOCAlgorithm.get_params_memsize())
    assert algo.params.pack_into(buf) is True
    original_state = dict(algo.params.__dict__)

    restored = VOCAlgorithm()  # a fresh instance, never initialized
    assert restored.params.unpack_from(buf) is True
    assert dict(restored.params.__dict__) == original_state


def test_proc_ser_des_restore_resumes_identically_to_the_original() -> None:
    # This is the actual mechanism asy_sgp40_driver.py relies on to survive a reboot: not
    # Sensirion's own get_states()/set_states() (mean/std only), but a full 32-field dump/restore
    # - including the uptime_gamma/uptime_gating learning-progress counters (see module docstring).
    # vocalgorithm_proc_ser_des() always processes the given sraw around (de)serializing, so a
    # restore-with-deserialize=True call also advances state by one sample, same as the original
    # would have for that same sample - proven below by feeding both the same sample and comparing.
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    for i in range(80):
        algo.vocalgorithm_process(30000 + (i * 53) % 4000)
    buf = bytearray(VOCAlgorithm.get_params_memsize())
    assert algo.params.pack_into(buf) is True

    restored = VOCAlgorithm()  # a fresh instance, never initialized
    voc_index_original = algo.vocalgorithm_process(30500)
    voc_index_restored, _serialized, deserialized = restored.vocalgorithm_proc_ser_des(30500, buf, deserialize=True)
    assert deserialized is True
    assert voc_index_restored == voc_index_original

    # Continuing to process on both from here must keep producing identical output.
    for i in range(10):
        a = algo.vocalgorithm_process(30000 + i * 90)
        b = restored.vocalgorithm_process(30000 + i * 90)
        assert a == b


def test_proc_ser_des_offset_places_state_at_given_position() -> None:
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    for i in range(30):
        algo.vocalgorithm_process(30000 + i * 7)
    size = VOCAlgorithm.get_params_memsize()
    buf = bytearray(16 + size)
    algo.vocalgorithm_proc_ser_des(30500, buf, serialize=True, offset=16)
    assert buf[0:16] == bytearray(16)  # nothing written before the offset
    assert buf[16:] != bytearray(size)


def test_pack_into_buffer_too_small_returns_false_not_raise() -> None:
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    too_small = bytearray(VOCAlgorithm.get_params_memsize() - 1)
    assert algo.params.pack_into(too_small) is False


def test_unpack_from_buffer_too_small_returns_false_not_raise() -> None:
    algo = VOCAlgorithm()
    too_small = bytearray(VOCAlgorithm.get_params_memsize() - 1)
    assert algo.params.unpack_from(too_small) is False


def test_deserialize_with_malformed_buffer_leaves_algorithm_usable() -> None:
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    bad_buf = bytearray(4)  # far too small
    voc_index, _serialized, deserialized = algo.vocalgorithm_proc_ser_des(30000, bad_buf, deserialize=True)
    assert deserialized is False
    assert isinstance(voc_index, int)  # processing still ran despite the failed deserialize


# ---------------------------------------------------------------------------
# Fixed-point (fix16) helpers - the arithmetic primitives every formula above builds on
# ---------------------------------------------------------------------------


def test_fix16_mul_and_div_are_approximate_inverses() -> None:
    algo = VOCAlgorithm()
    a = algo._fix16_from_int(10)
    b = algo._fix16_from_int(4)
    product = algo._fix16_mul(a, b)
    assert algo._fix16_cast_to_int(product) == 40
    quotient = algo._fix16_div(product, b)
    assert algo._fix16_cast_to_int(quotient) == 10


def test_fix16_div_by_zero_returns_minimum_sentinel() -> None:
    algo = VOCAlgorithm()
    assert algo._fix16_div(algo._fix16_from_int(5), 0) == 0x80000000  # _FIX16_MINIMUM


def test_fix16_mul_overflow_returns_overflow_sentinel() -> None:
    # fix16 has 16 integer bits (signed) - a real product past ~32767 can't be represented.
    algo = VOCAlgorithm()
    a = algo._fix16_from_int(200)
    b = algo._fix16_from_int(200)  # 200*200 = 40000 > 32767
    assert algo._fix16_mul(a, b) == 0x80000000  # _FIX16_OVERFLOW


def test_fix16_sqrt_matches_integer_square_root() -> None:
    algo = VOCAlgorithm()
    x = algo._fix16_from_int(144)
    result = algo._fix16_sqrt(x)
    assert algo._fix16_cast_to_int(result) == 12


def test_fix16_exp_saturates_at_documented_bounds() -> None:
    algo = VOCAlgorithm()
    # Values from the C reference's own overflow guards (x >= f16(10.3972) -> FIX16_MAXIMUM,
    # x <= f16(-11.7835) -> 0).
    assert algo._fix16_exp(algo._f16(11.0)) == 0x7FFFFFFF
    assert algo._fix16_exp(algo._f16(-12.0)) == 0
    assert algo._fix16_exp(algo._f16(0.0)) == algo._f16(1.0)  # e^0 == 1


# ---------------------------------------------------------------------------
# Real-FRAM integration and fault propagation - VOCAlgorithm's own pack_into()/unpack_from()
# through a real AsyFramManager + simulated chip, decoupled from asy_sgp40_driver.py entirely
# (that file's own FRAM tests exercise the same mechanism, but always coupled to a full sensor
# read cycle - see tests/test_asy_sgp40_driver.py). Matches tests/README.md's mocking-boundary plan.
# ---------------------------------------------------------------------------


def test_voc_state_round_trips_through_a_real_fram_chunk_across_a_simulated_reboot() -> None:
    manager, _chip, spi_bus = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_chunk(VOCAlgorithm.get_params_memsize(), crc=CRC32())
    assert chunk is not None

    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    for i in range(80):
        algo.vocalgorithm_process(30000 + (i * 53) % 4000)

    async def write() -> None:
        buf = chunk.get_buffer()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        assert algo.params.pack_into(dbuf) is True
        assert await chunk.write_into(buf) is True

    run(write())

    # A second manager sharing the same underlying chip - simulates a real reboot: fresh
    # VOCAlgorithm, never processed a single sample, must recover the exact converged state.
    manager2 = make_fram_manager_sharing(spi_bus)
    run(manager2.setup())
    chunk2 = manager2.get_chunk(VOCAlgorithm.get_params_memsize(), crc=CRC32())
    assert chunk2 is not None

    async def read() -> bytearray:
        buf = chunk2.get_buffer()
        assert await chunk2.read_into(buf) is True
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        return bytearray(dbuf)

    raw = run(read())
    restored = VOCAlgorithm()  # fresh instance, never initialized
    assert restored.params.unpack_from(raw) is True
    assert dict(restored.params.__dict__) == dict(algo.params.__dict__)

    # Continuing to process on both must produce identical output - proves the *whole* state (not
    # just mean/std) survived a real FRAM round trip, not just the in-memory struct round trip
    # test_pack_into_unpack_from_round_trip_is_byte_exact already covers.
    for i in range(10):
        a = algo.vocalgorithm_process(30000 + i * 90)
        b = restored.vocalgorithm_process(30000 + i * 90)
        assert a == b


def test_voc_state_restore_from_a_hard_fram_read_failure_leaves_algorithm_state_untouched() -> None:
    # Both redundant on-chip copies corrupted (not just one, which would self-heal - see
    # tests/test_asy_fram_manager.py's own test_read_fails_when_both_blocks_have_crc_invalid_payloads)
    # -> chunk.read_into() cleanly returns False, the same shape every other FRAM hardware failure
    # this codebase models takes. asy_sgp40_driver.py's own _run_restore() never calls unpack_from()
    # at all once read_into()/ts_storage.read_into() has already failed - proven here directly
    # against VOCAlgorithm/its params, not just inferred from that caller's own short-circuit logic.
    manager, chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_chunk(VOCAlgorithm.get_params_memsize(), crc=CRC32())
    assert chunk is not None

    async def write() -> None:
        buf = chunk.get_buffer()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        writer = VOCAlgorithm()
        writer.vocalgorithm_init()
        for i in range(20):
            writer.vocalgorithm_process(30000 + i * 13)
        assert writer.params.pack_into(dbuf) is True
        assert await chunk.write_into(buf) is True

    run(write())
    addr0, addr1 = chunk.block_addr
    chip.memory[addr0] ^= 0xFF  # both copies corrupted - a real, unrecoverable hardware fault
    chip.memory[addr1] ^= 0xFF

    restored = VOCAlgorithm()
    restored.vocalgorithm_init()
    before_state = dict(restored.params.__dict__)

    async def read() -> bool:
        buf = chunk.get_buffer()
        ok = await chunk.read_into(buf)
        if ok:
            dbuf = buf.get_data_buf()
            assert dbuf is not None
            restored.params.unpack_from(dbuf)
        return ok

    assert run(read()) is False
    assert dict(restored.params.__dict__) == before_state  # nothing touched restored.params


def test_voc_state_self_heals_from_a_single_corrupted_copy_through_real_fram() -> None:
    # Mirror of the hard-failure test above, but only one of the two redundant copies is
    # corrupted - _AsyBaseFramChunk's own dual-copy redundancy must recover from the other,
    # untouched copy and still hand back the exact original state, not just "read succeeded".
    manager, chip, _spi_bus = make_fram_manager()
    run(manager.setup())
    chunk = manager.get_chunk(VOCAlgorithm.get_params_memsize(), crc=CRC32())
    assert chunk is not None

    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    for i in range(30):
        algo.vocalgorithm_process(30000 + i * 19)

    async def write() -> None:
        buf = chunk.get_buffer()
        dbuf = buf.get_data_buf()
        assert dbuf is not None
        assert algo.params.pack_into(dbuf) is True
        assert await chunk.write_into(buf) is True

    run(write())
    addr0, _addr1 = chunk.block_addr
    chip.memory[addr0] ^= 0xFF  # only block 0 corrupted

    restored = VOCAlgorithm()

    async def read() -> bool:
        buf = chunk.get_buffer()
        ok = await chunk.read_into(buf)
        if ok:
            dbuf = buf.get_data_buf()
            assert dbuf is not None
            restored.params.unpack_from(dbuf)
        return ok

    assert run(read()) is True
    assert dict(restored.params.__dict__) == dict(algo.params.__dict__)


# ---------------------------------------------------------------------------
# Untested-but-safe conditions found during a deeper review pass
# ---------------------------------------------------------------------------


def test_pack_into_negative_offset_returns_false_not_raise() -> None:
    # Confirmed directly against the real interpreter: MicroPython's struct.pack_into() raises
    # ValueError for a negative offset (unlike CPython's struct, which treats a negative offset as
    # relative to the buffer's end) - already caught by pack_into()'s own try/except Exception, but
    # previously untested. No real caller in this codebase ever passes a negative offset today.
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    buf = bytearray(300)
    assert algo.params.pack_into(buf, offset=-50) is False


def test_unpack_from_negative_offset_returns_false_not_raise() -> None:
    algo = VOCAlgorithm()
    buf = bytearray(300)
    assert algo.params.unpack_from(buf, offset=-50) is False


def test_set_tuning_parameters_smoke_test_normal_values() -> None:
    # _vocalgorithm_set_tuning_parameters() has no caller anywhere in this codebase today -
    # asy_sgp40_driver.py never calls it; only _vocalgorithm_get_states()/_vocalgorithm_set_states()
    # are used (Sensirion's own short-interruption API). Kept as documented, Sensirion-mirroring API
    # surface, but had zero test coverage at all until now. This is a smoke test confirming it
    # threads the given values through correctly and leaves the algorithm in a usable state - not a
    # claim that it's exercised by any real caller today (see BACKLOG.md).
    algo = VOCAlgorithm()
    algo.vocalgorithm_init()
    algo._vocalgorithm_set_tuning_parameters(
        voc_index_offset=100.0,
        learning_time_hours=12.0,
        gating_max_duration_minutes=180.0,
        std_initial=50.0,
    )
    assert algo.params.mvoc_index_offset == algo._fix16_from_int(100.0)
    assert algo.params.mtau_mean_variance_hours == algo._fix16_from_int(12.0)
    assert algo.params.mgating_max_duration_minutes == algo._fix16_from_int(180.0)
    assert algo.params.msraw_std_initial == algo._fix16_from_int(50.0)
    voc_index = algo.vocalgorithm_process(30000)  # must still produce a valid index afterward
    assert isinstance(voc_index, int)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
