import asyncio

from crc_checks import CRC8, CRC16, CRC32, CRC_Base, CRC_Pass

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# CRC8 - correctness against Sensirion's own documented test vectors
# ---------------------------------------------------------------------------


def test_crc8_matches_sgp40_datasheet_vectors() -> None:
    # Table 10 of the SGP40 datasheet (also quoted in asy_sgp40_driver.py's docstring).
    crc8 = CRC8()
    vectors = [
        (bytearray([0x66, 0x66]), 0x93),
        (bytearray([0x00, 0x00]), 0x81),
        (bytearray([0x80, 0x00]), 0xA2),
        (bytearray([0xFF, 0xFF]), 0xAC),
    ]
    for data, expected in vectors:
        assert run(crc8._crc(data, crc8.all_set)) == expected


def test_crc8_matches_sensirion_example_vector() -> None:
    # 0xBEEF -> 0x92 is Sensirion's other commonly-quoted worked example (e.g. SHT3x datasheet).
    crc8 = CRC8()
    assert run(crc8._crc(bytearray([0xBE, 0xEF]), crc8.all_set)) == 0x92


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
    crc8 = CRC8()  # num_bytes == 1
    assert run(crc8.check(bytearray([0x00]))) is None
    assert run(crc8.check(bytearray())) is None


def test_check_boundary_just_above_crc_length_accepted() -> None:
    crc8 = CRC8()
    added = run(crc8.add(bytearray(b"x")))  # 1 payload byte + 1 CRC byte = 2 bytes total
    assert added is not None
    assert len(added) == 2
    assert run(crc8.check(added)) == bytearray(b"x")


# ---------------------------------------------------------------------------
# CRC_Pass - zero-length no-op
# ---------------------------------------------------------------------------


def test_crc_pass_length_is_zero() -> None:
    assert CRC_Pass().length() == 0


def test_crc_pass_add_and_check_are_identity() -> None:
    cp = CRC_Pass()
    data = bytearray(b"unchanged")
    assert run(cp.add(data)) == data
    assert run(cp.check(data)) == data


def test_crc_pass_accepts_empty_buffer() -> None:
    cp = CRC_Pass()
    assert run(cp.check(bytearray())) == bytearray()


def test_crc_pass_ignores_explicit_poly() -> None:
    # poly is forwarded to CRC_Base for constructor-shape consistency with CRC8/16/32, but
    # num_bytes == 0 always nullifies it back to None (CRC_Base's own existing invariant).
    cp = CRC_Pass(poly=0x31)
    assert cp.poly is None
    assert cp.length() == 0


def test_crc8_with_poly_none_degrades_to_pass_mode() -> None:
    c8 = CRC8(poly=None)
    assert c8.poly is None
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
    cp = CRC_Pass()
    buf = bytearray(b"XYZ")
    assert run(cp.add_into(buf, 3)) == 3
    assert run(cp.check_from(buf, 3)) == 3
    assert run(cp.check_from(buf)) == 3


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
    assert crc8.inc_crc is None
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
    assert crc8.inc_crc is None  # left in a clean state, not stuck mid-sequence


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
    cp = CRC_Pass()

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
    added_explicit = run(crc8.add(data, init=crc8.all_set))
    assert added_default == added_explicit


def test_init_above_all_set_rejected() -> None:
    crc8 = CRC8()
    assert run(crc8.add(bytearray(b"x"), init=crc8.all_set + 1)) is None


def test_init_negative_rejected() -> None:
    crc8 = CRC8()
    assert run(crc8.add(bytearray(b"x"), init=-1)) is None


def test_init_boundary_values_accepted() -> None:
    crc8 = CRC8()
    assert run(crc8.add(bytearray(b"x"), init=0)) is not None
    assert run(crc8.add(bytearray(b"x"), init=crc8.all_set)) is not None


# ---------------------------------------------------------------------------
# poly validation
# ---------------------------------------------------------------------------


def test_poly_above_all_set_degrades_to_pass_mode() -> None:
    base = CRC_Base(1, 0x1FF, ">B")  # poly wider than a single byte can hold
    assert base.poly is None
    assert run(base.add(bytearray(b"x"))) == bytearray(b"x")


def test_poly_negative_degrades_to_pass_mode() -> None:
    base = CRC_Base(1, -1, ">B")
    assert base.poly is None


def test_num_bytes_negative_degrades_to_pass_mode() -> None:
    base = CRC_Base(-1, 0x31, ">B")
    assert base.num_bytes == 0
    assert base.poly is None


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
    crc16 = CRC16()  # num_bytes == 2
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
    crc32 = CRC32()  # num_bytes == 4
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
    # inc_count == num_bytes (not > num_bytes) must be rejected regardless of content, since
    # that leaves no room for any actual payload.
    crc8 = CRC8()  # num_bytes == 1

    async def feed() -> int | None:
        await crc8.run_inc(bytearray(1))  # exactly num_bytes fed, zero payload bytes
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


# ---------------------------------------------------------------------------
# Forgotten/dangling incremental sequences
# ---------------------------------------------------------------------------


def test_forgotten_check_inc_continues_stale_sequence_instead_of_resetting() -> None:
    # Documents a sharp edge in the API contract: if a caller starts feeding a new logical
    # buffer via run_inc() without finalizing the previous sequence via check_inc() first, the
    # old bytes are still folded into inc_crc/inc_count - it does NOT silently start fresh.
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
# the result back, since all three require strictly more than num_bytes total.
# ---------------------------------------------------------------------------


def test_add_on_empty_payload_produces_buffer_check_cannot_verify() -> None:
    crc8 = CRC8()
    added = run(crc8.add(bytearray()))
    assert added is not None
    assert len(added) == crc8.num_bytes  # just the CRC, no payload bytes
    assert run(crc8.check(added)) is None  # ...and check() can never validate it


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
