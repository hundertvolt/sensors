import struct

from voc_algorithm import VOCAlgorithm

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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
