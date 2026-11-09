"""CRC8/16/32 and CRCPass against cited check values: bounds and refusals, pass mode, and incremental use matching one
bulk pass."""

from _async_harness import run

from asy_crc_checks import CRC8, CRC16, CRC32, CRCBase, CRCPass, _crc

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import NoReturn


# ---------------------------------------------------------------------------
# CRC8 - correctness against Sensirion's own documented test vectors
# ---------------------------------------------------------------------------


def test_crc8_matches_sgp40_datasheet_vectors() -> None:
    # SGP40 datasheet v1.2 Table 10: the CRC byte printed beside the default, minimum and maximum RH/T tick words.
    crc8 = CRC8()
    vectors = [
        (bytearray([0x66, 0x66]), 0x93),
        (bytearray([0x00, 0x00]), 0x81),
        (bytearray([0x80, 0x00]), 0xA2),
        (bytearray([0xFF, 0xFF]), 0xAC),
    ]
    for data, expected in vectors:
        assert _crc(data, 0, len(data), crc8._all_set, 0x31, 0) == expected


def test_crc8_matches_sensirion_example_vector() -> None:
    # SGP40 datasheet v1.2 Table 7's example, CRC(0xBE 0xEF) = 0x92; the SCD30 Interface Description §1.1.3 gives the same.
    crc8 = CRC8()
    assert _crc(bytearray([0xBE, 0xEF]), 0, 2, crc8._all_set, 0x31, 0) == 0x92


# ---------------------------------------------------------------------------
# add/check round trips
# ---------------------------------------------------------------------------


def test_add_check_round_trip_crc8() -> None:
    crc8 = CRC8()
    data = bytearray(b"hello world")
    added = run(crc8.add(data))
    assert added is not None
    assert added != data
    checked = run(crc8.check(added))
    assert checked == data


def test_add_check_round_trip_crc16() -> None:
    crc16 = CRC16()
    data = bytearray(b"hello world")
    added = run(crc16.add(data))
    assert added is not None
    checked = run(crc16.check(added))
    assert checked == data


def test_add_check_round_trip_crc32() -> None:
    crc32 = CRC32()
    data = bytearray(b"hello world")
    added = run(crc32.add(data))
    assert added is not None
    checked = run(crc32.check(added))
    assert checked == data


def test_check_rejects_corrupted_data() -> None:
    crc8 = CRC8()
    added = run(crc8.add(bytearray(b"hello world")))
    assert added is not None
    corrupted = bytearray(added)
    corrupted[0] ^= 0xFF
    assert run(crc8.check(corrupted)) is None


def test_check_rejects_data_no_longer_than_crc_itself() -> None:
    crc8 = CRC8()  # _num_bytes == 1
    assert run(crc8.check(bytearray([0x00]))) is None
    assert run(crc8.check(bytearray())) is None


def test_check_boundary_just_above_crc_length_accepted() -> None:
    crc8 = CRC8()
    added = run(crc8.add(bytearray(b"x")))  # 1 payload byte + 1 CRC byte = 2 bytes total
    assert added is not None
    assert len(added) == 2
    assert run(crc8.check(added)) == bytearray(b"x")


# ---------------------------------------------------------------------------
# CRCPass - zero-length no-op
# ---------------------------------------------------------------------------


def test_crc_pass_length_is_zero() -> None:
    assert CRCPass().length() == 0


def test_crc_pass_add_and_check_are_identity() -> None:
    cp = CRCPass()
    data = bytearray(b"unchanged")
    assert run(cp.add(data)) == data
    assert run(cp.check(data)) == data


def test_crc_pass_accepts_empty_buffer() -> None:
    cp = CRCPass()
    assert run(cp.check(bytearray())) == bytearray()


def test_crc_pass_ignores_explicit_poly() -> None:
    # poly is forwarded to CRCBase for constructor-shape consistency with CRC8/16/32, but
    # _num_bytes == 0 always nullifies it back to None (CRCBase's own existing invariant).
    cp = CRCPass(poly=0x31)
    assert cp._poly is None
    assert cp.length() == 0


def test_crc8_with_poly_none_degrades_to_pass_mode() -> None:
    c8 = CRC8(poly=None)
    assert c8._poly is None
    assert c8.length() == 0
    data = bytearray(b"unchanged")
    assert run(c8.add(data)) == data


# ---------------------------------------------------------------------------
# add_into / check_from - shared-buffer variants
# ---------------------------------------------------------------------------


def test_add_into_and_check_from_round_trip() -> None:
    crc8 = CRC8()
    buf = bytearray(b"XY\x00")  # 2 payload bytes + 1 byte reserved for the CRC
    written = run(crc8.add_into(buf, 2))
    assert written == 3
    consumed = run(crc8.check_from(buf, 3))
    assert consumed == 2


def test_add_into_rejects_buffer_too_small_for_crc() -> None:
    crc8 = CRC8()
    buf = bytearray(b"XY")  # no room for the trailing CRC byte
    assert run(crc8.add_into(buf, 2)) is None


def test_add_into_rejects_non_positive_size() -> None:
    crc8 = CRC8()
    buf = bytearray(3)
    assert run(crc8.add_into(buf, 0)) is None
    assert run(crc8.add_into(buf, -1)) is None


def test_add_into_rejects_negative_start() -> None:
    crc8 = CRC8()
    buf = bytearray(3)
    assert run(crc8.add_into(buf, 1, start=-1)) is None


def test_check_from_rejects_corrupted_data() -> None:
    crc8 = CRC8()
    buf = bytearray(b"XY\x00")
    run(crc8.add_into(buf, 2))
    buf[0] ^= 0xFF
    assert run(crc8.check_from(buf, 3)) is None


def test_check_from_defaults_size_to_full_buffer() -> None:
    crc8 = CRC8()
    buf = bytearray(b"XY\x00")
    run(crc8.add_into(buf, 2))
    assert run(crc8.check_from(buf)) == 2


def test_check_from_rejects_size_not_longer_than_crc() -> None:
    crc8 = CRC8()
    assert run(crc8.check_from(bytearray([0x00]), 1)) is None


def test_add_into_and_check_from_with_start_offset() -> None:
    crc8 = CRC8()
    buf = bytearray(b"\x00\x00" + b"XY" + b"\x00")  # leading padding before the payload
    written = run(crc8.add_into(buf, 2, start=2))
    assert written == 3
    consumed = run(crc8.check_from(buf, 3, start=2))
    assert consumed == 2


def test_crc_pass_add_into_and_check_from_are_size_identity() -> None:
    cp = CRCPass()
    buf = bytearray(b"XYZ")
    assert run(cp.add_into(buf, 3)) == 3
    assert run(cp.check_from(buf, 3)) == 3
    assert run(cp.check_from(buf)) == 3


def test_pass_mode_add_into_and_check_from_refuse_bad_bounds() -> None:
    # Pass mode refuses the same zero, negative and overrunning sizes the real CRCs refuse.
    for crc in (CRCPass(), CRC8(poly=None)):
        buf = bytearray(3)
        assert run(crc.add_into(buf, 0)) is None
        assert run(crc.add_into(buf, -1)) is None
        assert run(crc.add_into(buf, 1, start=-1)) is None
        assert run(crc.add_into(bytearray(2), 3)) is None
        assert run(crc.check_from(buf, 0)) is None
        assert run(crc.check_from(buf, -1)) is None
        assert run(crc.check_from(buf, 1, start=-1)) is None
        assert run(crc.check_from(bytearray(2), 3)) is None


# ---------------------------------------------------------------------------
# Incremental API: run_inc / check_inc
# ---------------------------------------------------------------------------


def test_incremental_round_trip_matches_bulk() -> None:
    crc8 = CRC8()
    data = bytearray(b"hello world")
    added = run(crc8.add(data))
    assert added is not None

    async def feed() -> int | None:
        assert await crc8.run_inc(added[0:5])
        assert await crc8.run_inc(added[5:])
        return await crc8.check_inc()

    assert run(feed()) == len(data)


def test_incremental_rejects_corrupted_data() -> None:
    crc8 = CRC8()
    added = run(crc8.add(bytearray(b"hello world")))
    assert added is not None
    corrupted = bytearray(added)
    corrupted[-1] ^= 0xFF

    async def feed() -> int | None:
        await crc8.run_inc(corrupted)
        return await crc8.check_inc()

    assert run(feed()) is None


def test_check_inc_without_run_inc_returns_none() -> None:
    crc8 = CRC8()
    assert run(crc8.check_inc()) is None


def test_check_inc_resets_state_after_call() -> None:
    # A check_inc() call (success or failure) must reset internal state so a later, unrelated
    # run_inc()/check_inc() sequence doesn't silently continue the previous computation.
    crc8 = CRC8()
    added = run(crc8.add(bytearray(b"first message")))
    assert added is not None

    async def first_pass() -> int | None:
        await crc8.run_inc(added)
        return await crc8.check_inc()

    assert run(first_pass()) == len(b"first message")
    assert crc8._inc_crc is None
    # A fresh sequence starts clean rather than continuing stale state.
    assert run(crc8.check_inc()) is None


def test_run_inc_with_insufficient_data_rejected_by_check_inc() -> None:
    # Fewer total bytes fed than the CRC width itself must never report a valid (let alone
    # negative) length, even though nothing here would normally drive the CRC register to zero.
    crc16 = CRC16()

    async def feed() -> int | None:
        await crc16.run_inc(bytearray(b"A"))  # 1 byte fed, CRC16 needs > 2 bytes total
        return await crc16.check_inc()

    assert run(feed()) is None


def test_run_inc_rejects_invalid_init() -> None:
    crc8 = CRC8()

    async def feed() -> bool:
        return await crc8.run_inc(bytearray(b"x"), init=-1)

    assert run(feed()) is False
    assert crc8._inc_crc is None  # left in a clean state, not stuck mid-sequence


def test_run_inc_recovers_after_invalid_init() -> None:
    crc8 = CRC8()
    added = run(crc8.add(bytearray(b"hello world")))
    assert added is not None

    async def bad_then_good() -> int | None:
        await crc8.run_inc(bytearray(b"x"), init=-1)  # rejected, must not leave stale state
        await crc8.run_inc(added)
        return await crc8.check_inc()

    assert run(bad_then_good()) == len(b"hello world")


def test_run_inc_ignores_init_on_later_calls() -> None:
    # init only applies on the first run_inc() call of a sequence; a later call passing a
    # (deliberately invalid) init must not retroactively invalidate the sequence.
    crc8 = CRC8()
    added = run(crc8.add(bytearray(b"hello world")))
    assert added is not None

    async def feed() -> int | None:
        await crc8.run_inc(added[0:5])  # starts the sequence with the real default init
        await crc8.run_inc(added[5:], init=-1)  # init ignored here - sequence already started
        return await crc8.check_inc()

    assert run(feed()) == len(b"hello world")


def test_run_inc_accepts_memoryview() -> None:
    crc8 = CRC8()
    added = run(crc8.add(bytearray(b"hello world")))
    assert added is not None

    async def feed() -> int | None:
        mv = memoryview(added)
        await crc8.run_inc(mv[0:5])
        await crc8.run_inc(mv[5:])
        return await crc8.check_inc()

    assert run(feed()) == len(b"hello world")


def test_crc_pass_incremental_accepts_empty() -> None:
    cp = CRCPass()

    async def feed() -> int | None:
        await cp.run_inc(bytearray())
        return await cp.check_inc()

    assert run(feed()) == 0


# ---------------------------------------------------------------------------
# init parameter validation
# ---------------------------------------------------------------------------


def test_explicit_init_matches_default() -> None:
    crc8 = CRC8()
    data = bytearray(b"hello world")
    added_default = run(crc8.add(data, init=None))
    added_explicit = run(crc8.add(data, init=crc8._all_set))
    assert added_default == added_explicit


def test_init_above_all_set_rejected() -> None:
    crc8 = CRC8()
    assert run(crc8.add(bytearray(b"x"), init=crc8._all_set + 1)) is None


def test_init_negative_rejected() -> None:
    crc8 = CRC8()
    assert run(crc8.add(bytearray(b"x"), init=-1)) is None


def test_init_boundary_values_accepted() -> None:
    # CRC-8 poly 0x31 over 0x78, MSB first: from init 0x00 the register ends at 0x41, from 0xFF at 0xED.
    crc8 = CRC8()
    assert run(crc8.add(bytearray(b"x"), init=0)) == bytearray(b"x\x41")
    assert run(crc8.add(bytearray(b"x"), init=crc8._all_set)) == bytearray(b"x\xed")


def test_check_rejects_invalid_init() -> None:
    # check()'s own init validation, mirroring add()'s coverage above - a corrupt-looking init
    # must be rejected before any CRC computation runs, not just for add()/add_into().
    crc8 = CRC8()
    added = run(crc8.add(bytearray(b"hello world")))
    assert added is not None
    assert run(crc8.check(added, init=-1)) is None
    assert run(crc8.check(added, init=crc8._all_set + 1)) is None


# ---------------------------------------------------------------------------
# poly validation
# ---------------------------------------------------------------------------


def test_poly_above_all_set_degrades_to_pass_mode() -> None:
    base = CRCBase(1, 0x1FF, ">B")  # poly wider than a single byte can hold
    assert base._poly is None
    assert run(base.add(bytearray(b"x"))) == bytearray(b"x")


def test_poly_negative_degrades_to_pass_mode() -> None:
    base = CRCBase(1, -1, ">B")
    assert base._poly is None


def test_num_bytes_negative_degrades_to_pass_mode() -> None:
    base = CRCBase(-1, 0x31, ">B")
    assert base._num_bytes == 0
    assert base._poly is None


def test_a_width_beyond_the_engines_word_degrades_to_pass_mode() -> None:
    # The engine's word is 32 bits on silicon, so a 5-byte register is refused like any other invalid config.
    base = CRCBase(5, 0x1B, ">Q")
    assert (base.length(), base._poly) == (0, None)
    assert CRCBase(4, 0x1B, ">I").length() == 4


# ---------------------------------------------------------------------------
# CRC16 - width-specific parity with CRC8's coverage above
# ---------------------------------------------------------------------------


def test_crc16_check_rejects_corrupted_data() -> None:
    crc16 = CRC16()
    added = run(crc16.add(bytearray(b"hello world")))
    assert added is not None
    corrupted = bytearray(added)
    corrupted[0] ^= 0xFF
    assert run(crc16.check(corrupted)) is None


def test_crc16_check_rejects_data_no_longer_than_crc_itself() -> None:
    crc16 = CRC16()  # _num_bytes == 2
    assert run(crc16.check(bytearray(2))) is None


def test_crc16_check_boundary_just_above_crc_length_accepted() -> None:
    crc16 = CRC16()
    added = run(crc16.add(bytearray(b"x")))  # 1 payload byte + 2 CRC bytes = 3 bytes total
    assert added is not None
    assert len(added) == 3
    assert run(crc16.check(added)) == bytearray(b"x")


def test_crc16_add_into_check_from_round_trip() -> None:
    crc16 = CRC16()
    buf = bytearray(b"XY" + b"\x00\x00")
    written = run(crc16.add_into(buf, 2))
    assert written == 4
    assert run(crc16.check_from(buf, 4)) == 2


def test_crc16_incremental_round_trip_matches_bulk() -> None:
    crc16 = CRC16()
    data = bytearray(b"hello world")
    added = run(crc16.add(data))
    assert added is not None

    async def feed() -> int | None:
        assert await crc16.run_inc(added[0:5])
        assert await crc16.run_inc(added[5:])
        return await crc16.check_inc()

    assert run(feed()) == len(data)


# ---------------------------------------------------------------------------
# CRC32 - width-specific parity with CRC8's coverage above
# ---------------------------------------------------------------------------


def test_crc32_check_rejects_corrupted_data() -> None:
    crc32 = CRC32()
    added = run(crc32.add(bytearray(b"hello world")))
    assert added is not None
    corrupted = bytearray(added)
    corrupted[0] ^= 0xFF
    assert run(crc32.check(corrupted)) is None


def test_crc32_check_rejects_data_no_longer_than_crc_itself() -> None:
    crc32 = CRC32()  # _num_bytes == 4
    assert run(crc32.check(bytearray(4))) is None


def test_crc32_check_boundary_just_above_crc_length_accepted() -> None:
    crc32 = CRC32()
    added = run(crc32.add(bytearray(b"x")))  # 1 payload byte + 4 CRC bytes = 5 bytes total
    assert added is not None
    assert len(added) == 5
    assert run(crc32.check(added)) == bytearray(b"x")


def test_crc32_add_into_check_from_round_trip() -> None:
    crc32 = CRC32()
    buf = bytearray(b"XY" + b"\x00\x00\x00\x00")
    written = run(crc32.add_into(buf, 2))
    assert written == 6
    assert run(crc32.check_from(buf, 6)) == 2


def test_crc32_incremental_round_trip_matches_bulk() -> None:
    crc32 = CRC32()
    data = bytearray(b"hello world")
    added = run(crc32.add(data))
    assert added is not None

    async def feed() -> int | None:
        assert await crc32.run_inc(added[0:5])
        assert await crc32.run_inc(added[5:])
        return await crc32.check_inc()

    assert run(feed()) == len(data)


# ---------------------------------------------------------------------------
# Incremental step counts: 1 call, and "many" small calls (2 calls is already covered above)
# ---------------------------------------------------------------------------


def test_incremental_single_call_matches_bulk() -> None:
    crc32 = CRC32()
    data = bytearray(b"hello world")
    added = run(crc32.add(data))
    assert added is not None

    async def feed() -> int | None:
        assert await crc32.run_inc(added)  # entire buffer fed in one call
        return await crc32.check_inc()

    assert run(feed()) == len(data)


def test_incremental_many_single_byte_calls_matches_bulk() -> None:
    crc32 = CRC32()
    data = bytearray(range(50))  # 50 arbitrary payload bytes
    added = run(crc32.add(data))
    assert added is not None

    async def feed() -> int | None:
        for i in range(len(added)):
            assert await crc32.run_inc(added[i : i + 1])  # one byte per call
        return await crc32.check_inc()

    assert run(feed()) == len(data)


# ---------------------------------------------------------------------------
# check_inc: threshold precision (exactly at vs. just above the CRC width)
# ---------------------------------------------------------------------------


def test_check_inc_rejects_exactly_crc_length_fed() -> None:
    # inc_count == _num_bytes (not > _num_bytes) must be rejected regardless of content, since
    # that leaves no room for any actual payload.
    crc8 = CRC8()  # _num_bytes == 1

    async def feed() -> int | None:
        await crc8.run_inc(bytearray(1))  # exactly _num_bytes fed, zero payload bytes
        return await crc8.check_inc()

    assert run(feed()) is None


def test_check_inc_accepts_minimal_one_byte_payload() -> None:
    crc16 = CRC16()
    added = run(crc16.add(bytearray(b"z")))  # 1 payload byte + 2 CRC bytes
    assert added is not None

    async def feed() -> int | None:
        await crc16.run_inc(added)
        return await crc16.check_inc()

    assert run(feed()) == 1


# ---------------------------------------------------------------------------
# check_from: length mismatches against what add_into actually protected
# ---------------------------------------------------------------------------


def test_check_from_rejects_size_larger_than_buffer() -> None:
    crc8 = CRC8()
    buf = bytearray(b"XY\x00")
    run(crc8.add_into(buf, 2))
    assert run(crc8.check_from(buf, 10)) is None  # size beyond len(buf)


def test_check_from_rejects_invalid_init() -> None:
    # check_from()'s own init/size/start validation, mirroring add_into()'s coverage above -
    # none of these three sub-conditions were previously exercised for check_from() at all.
    crc8 = CRC8()
    buf = bytearray(b"XY\x00")
    run(crc8.add_into(buf, 2))
    assert run(crc8.check_from(buf, 3, init=-1)) is None
    assert run(crc8.check_from(buf, 3, init=crc8._all_set + 1)) is None


def test_check_from_rejects_non_positive_size() -> None:
    crc8 = CRC8()
    buf = bytearray(b"XY\x00")
    run(crc8.add_into(buf, 2))
    assert run(crc8.check_from(buf, 0)) is None
    assert run(crc8.check_from(buf, -1)) is None


def test_check_from_rejects_negative_start() -> None:
    crc8 = CRC8()
    buf = bytearray(b"XY\x00")
    run(crc8.add_into(buf, 2))
    assert run(crc8.check_from(buf, 3, start=-1)) is None


# ---------------------------------------------------------------------------
# Critical / boundary content patterns
# ---------------------------------------------------------------------------


def test_add_check_round_trip_all_zero_bytes() -> None:
    crc16 = CRC16()
    data = bytearray(16)  # all 0x00
    added = run(crc16.add(data))
    assert added is not None
    assert run(crc16.check(added)) == data


def test_add_check_round_trip_all_ff_bytes() -> None:
    crc32 = CRC32()
    data = bytearray(b"\xff" * 16)
    added = run(crc32.add(data))
    assert added is not None
    assert run(crc32.check(added)) == data


def test_add_check_round_trip_single_byte_payload_all_widths() -> None:
    for crc in (CRC8(), CRC16(), CRC32()):
        data = bytearray(b"\x00")
        added = run(crc.add(data))
        assert added is not None
        assert run(crc.check(added)) == data


def test_crc16_matches_the_ccitt_false_check_value() -> None:
    # The CRC-16/CCITT-FALSE check value; the oracle is named in the CRC-32 test below.
    crc16 = CRC16()
    assert _crc(bytearray(b"123456789"), 0, 9, crc16._all_set, 0x1021, 8) == 0x29B1


def test_crc32_matches_the_mpeg2_check_value() -> None:
    # Independent oracles computed on the host: CPython's binascii.crc_hqx(data, 0xFFFF) for CRC16, and zlib.crc32
    # over bit-reversed bytes, reflected back and xor-ed, for CRC-32/MPEG-2 (the CRC catalogue's CRC-32/MPEG-2).
    vectors = [
        (bytearray(b"123456789"), 0x0376E6E7),
        (bytearray(256), 0xE55E964F),
        (bytearray(range(256)), 0x494A116A),
    ]
    for data, expected in vectors:
        assert _crc(data, 0, len(data), 0xFFFFFFFF, 0x04C11DB7, 24) == expected


# Rows per width (data seed, length, init, CRC), the CRCs computed on the host by GF(2) division of the message, checked
# against binascii.crc_hqx (CRC16) and the zlib.crc32 construction above (CRC32): seed None is the 37i + 11 pattern at
# the default init, the 0/1/264/512-byte edges; the other rows are _lcg_bytes() data at a random init.
_ORACLE_ROWS = {
    CRC8: ((None, 0, 0xFF, 0xFF), (None, 1, 0xFF, 0x46), (None, 264, 0xFF, 0xAD), (None, 512, 0xFF, 0xA6), (394431668, 26, 250, 50), (623088224, 318, 70, 218), (910866977, 192, 93, 213), (17529307, 447, 238, 235)),
    CRC16: ((None, 0, 0xFFFF, 0xFFFF), (None, 1, 0xFFFF, 20635), (None, 264, 0xFFFF, 2768), (None, 512, 0xFFFF, 50080), (1883084724, 50, 26882, 64344), (1058962288, 111, 48858, 58825), (2094959691, 431, 21146, 7155), (683917094, 335, 39649, 52022)),
    CRC32: ((None, 0, 0xFFFFFFFF, 0xFFFFFFFF), (None, 1, 0xFFFFFFFF, 1698919637), (None, 264, 0xFFFFFFFF, 1788925217), (None, 512, 0xFFFFFFFF, 2336564053), (1724006962, 472, 693398165, 2031868003), (909990323, 206, 2652568907, 3189247331), (1848231682, 360, 372891647, 2223587924), (396852702, 358, 1087734844, 446169664)),
}


def _lcg_bytes(seed: int | None, n: int) -> bytearray:
    out = bytearray(n)
    for i in range(n):
        if seed is None:
            out[i] = (i * 37 + 11) & 0xFF
        else:
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            out[i] = (seed >> 16) & 0xFF
    return out


def test_every_width_matches_the_host_oracles_and_leaves_a_zero_residue() -> None:
    # The values are contracts: Sensirion's wire (CRC8), the UART peer's (CRC16), the stored FRAM chunks (CRC32). The CRC
    # add() appends, run again over payload and CRC at the same init, leaves 0: what check() and check_from() test.
    for cls, rows in _ORACLE_ROWS.items():
        crc = cls()
        width, poly, shift = crc.length(), crc._poly, crc._crc_shift
        assert poly is not None
        for seed, n, init, expected in rows:
            data = _lcg_bytes(seed, n)
            assert _crc(data, 0, n, init, poly, shift) == expected, (cls, seed, n)
            framed = run(crc.add(data, init=init))
            assert framed is not None
            assert framed[n:] == expected.to_bytes(width, "big"), (cls, seed, n)
            assert _crc(framed, 0, n + width, init, poly, shift) == 0, (cls, seed, n)
            assert run(crc.check(framed, init=init)) == (data if n else None), (cls, seed, n)


def test_crc32_round_trips_at_a_non_default_init() -> None:
    crc32 = CRC32()
    data = bytearray(range(40))
    added = run(crc32.add(data, init=0x12345678))
    assert added is not None
    assert added != run(crc32.add(data))
    assert run(crc32.check(added, init=0x12345678)) == data
    assert run(crc32.check(added)) is None


def test_trailing_zero_padding_passes_every_check_so_callers_pass_the_true_length() -> None:
    # A register at 0 stays 0 through further 0x00 bytes (the module comment's limitation): every
    # check accepts the padded buffer and strips the wrong bytes, so callers must pass the true length.
    for crc in (CRC8(), CRC16(), CRC32()):
        added = run(crc.add(bytearray(b"payload")))
        assert added is not None
        width = crc.length()
        for k in range(1, 4):
            padded = added + bytearray(k)
            assert run(crc.check(padded)) == padded[0 : len(padded) - width]
            assert run(crc.check_from(padded, len(padded))) == len(padded) - width

            async def incremental(buf: bytearray, crc: CRCBase = crc) -> int | None:
                assert await crc.run_inc(buf[0:3])
                assert await crc.run_inc(buf[3:])
                return await crc.check_inc()

            assert run(incremental(padded)) == len(padded) - width


# ---------------------------------------------------------------------------
# Forgotten/dangling incremental sequences
# ---------------------------------------------------------------------------


def test_forgotten_check_inc_continues_stale_sequence_instead_of_resetting() -> None:
    # Documents a sharp edge in the API contract: if a caller starts feeding a new logical
    # buffer via run_inc() without finalizing the previous sequence via check_inc() first, the
    # old bytes are still folded into _inc_crc/inc_count - it does NOT silently start fresh.
    crc8 = CRC8()
    first = run(crc8.add(bytearray(b"first")))
    assert first is not None
    run(crc8.run_inc(first))  # sequence left dangling - check_inc() never called

    second = run(crc8.add(bytearray(b"second")))
    assert second is not None

    async def resume() -> int | None:
        await crc8.run_inc(second)
        return await crc8.check_inc()

    assert run(resume()) is None  # "first"'s stale bytes corrupt this computation


def test_run_inc_after_check_inc_starts_a_clean_new_sequence() -> None:
    # The supported way to reuse one instance across back-to-back (non-concurrent) sequences:
    # always finalize with check_inc() before starting the next one.
    crc8 = CRC8()
    first = run(crc8.add(bytearray(b"first")))
    second = run(crc8.add(bytearray(b"second")))
    assert first is not None
    assert second is not None

    async def two_sequences() -> tuple[int | None, int | None]:
        await crc8.run_inc(first)
        r1 = await crc8.check_inc()
        await crc8.run_inc(second)
        r2 = await crc8.check_inc()
        return r1, r2

    assert run(two_sequences()) == (len(b"first"), len(b"second"))


def test_dangling_incremental_sequence_does_not_affect_adhoc_calls() -> None:
    # run_inc()/check_inc()'s state is independent of add()/check(): leaving an incremental
    # sequence unfinished must not break unrelated ad-hoc calls on the same instance.
    crc8 = CRC8()
    run(crc8.run_inc(bytearray(b"dangling")))  # never finalized
    data = bytearray(b"unrelated ad-hoc call")
    added = run(crc8.add(data))
    assert added is not None
    assert run(crc8.check(added)) == data


def test_run_inc_empty_chunk_between_real_chunks_is_a_noop() -> None:
    crc8 = CRC8()
    added = run(crc8.add(bytearray(b"hello world")))
    assert added is not None

    async def feed() -> int | None:
        assert await crc8.run_inc(added[0:5])
        assert await crc8.run_inc(bytearray())  # empty chunk - must not disturb the sequence
        assert await crc8.run_inc(added[5:])
        return await crc8.check_inc()

    assert run(feed()) == len(b"hello world")


# ---------------------------------------------------------------------------
# Empty-payload asymmetry between add() and check() - flagged, not silently fixed (see PR
# discussion): add() happily encodes a zero-byte payload, but no check* method can ever verify
# the result back, since all three require strictly more than _num_bytes total.
# ---------------------------------------------------------------------------


def test_add_on_empty_payload_produces_buffer_check_cannot_verify() -> None:
    crc8 = CRC8()
    added = run(crc8.add(bytearray()))
    assert added is not None
    assert len(added) == crc8._num_bytes  # just the CRC, no payload bytes
    assert run(crc8.check(added)) is None  # ...and check() can never validate it


# ---------------------------------------------------------------------------
# MemoryError propagation - add()/check() are the module docstring's one documented exception to this file's
# "every public method returns None/False on invalid input, never raises" contract: both allocate a new
# buffer, and a failed allocation is handed straight to the caller rather than swallowed.
#
# Every caller must catch it - see asy_uart_driver.py's guarded call sites, fault-injected in
# tests/test_asy_uart_driver.py. Nothing pinned that contract down from this side until now.
# ---------------------------------------------------------------------------


def test_add_lets_a_memoryerror_from_its_own_buffer_allocation_propagate() -> None:
    # add()'s new buffer is bytearray(self._num_bytes), whitebox-widened here to a size confirmed against the
    # real interpreter to raise MemoryError - the same allocation-exhaustion technique
    # test_asy_base_classes.py's RegionBuffer tests use. The CRC itself still runs at the real width.
    crc8 = CRC8()
    crc8._num_bytes = 2**62
    try:
        run(crc8.add(bytearray(b"hello world")))
        raise AssertionError("expected MemoryError to propagate out of add()")
    except MemoryError:
        pass


class _MemoryErrorOnCopyBuffer(bytearray):
    # check()'s own allocation is its payload copy, and no real buffer large enough for the copy to exhaust the heap can
    # itself be allocated: this bytearray computes the true CRC, and its slice, check()'s copy, raises.
    def __getitem__(self, item: object) -> "NoReturn":
        raise MemoryError("simulated allocation failure")


def test_check_lets_a_memoryerror_from_its_own_payload_copy_propagate() -> None:
    crc8 = CRC8()
    added = run(crc8.add(bytearray(b"hello world")))
    assert added is not None
    try:
        run(crc8.check(_MemoryErrorOnCopyBuffer(added)))
        raise AssertionError("expected MemoryError to propagate out of check()")
    except MemoryError:
        pass


def test_add_into_refuses_an_init_outside_the_crc_width_and_leaves_the_buffer_untouched() -> None:
    for crc in (CRC8(), CRC16(), CRC32()):
        for init in (-1, crc._all_set + 1):
            buf = bytearray(b"ab" + bytes(crc.length()))
            assert run(crc.add_into(buf, 2, init=init)) is None, (crc, init)
            assert buf == bytearray(b"ab" + bytes(crc.length())), (crc, init)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
