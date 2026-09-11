"""Unit tests for src/framing_codecs.py - the pluggable frame codec asy_uart_driver.py writes
through (requirement B2). Covers the pass-through default's byte-identity guarantee, COBS
round-trips including every shape the protocol can emit, and each malformed-input rejection."""

import asyncio

from framing_codecs import COBS_DELIMITER, Framing_COBS, Framing_Pass

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(asyncio.wait_for(coro, 5))


def encoded(codec: "Framing_Pass | Framing_COBS", payload: bytes) -> bytes:
    buf = bytearray(payload)
    view = run(codec.encode_into(buf, len(payload)))
    assert view is not None
    return bytes(view)


def decoded(codec: "Framing_Pass | Framing_COBS", frame: bytes) -> "bytes | None":
    buf = bytearray(frame)
    size = run(codec.decode_from(buf, len(frame)))
    if size is None:
        return None
    return bytes(buf[:size])


# ---------------------------------------------------------------------------
# Pass-through - the default, and the regression that proves nothing changed
# ---------------------------------------------------------------------------


def test_pass_through_is_byte_identical() -> None:
    codec = Framing_Pass()
    for payload in (b"", b"\x00", b"\x00\x01\xff", bytes(range(64))):
        assert encoded(codec, payload) == payload
        assert decoded(codec, payload) == payload


def test_pass_through_has_no_overhead_and_no_delimiter() -> None:
    codec = Framing_Pass()
    assert codec.overhead(0) == 0
    assert codec.overhead(255) == 0
    assert codec.max_encoded(48) == 48
    assert codec.is_delimited() is False


def test_pass_through_is_always_ready() -> None:
    # B2.8's counterpart: a codec that allocates nothing can never fail to construct.
    assert Framing_Pass().ready() is True


# ---------------------------------------------------------------------------
# COBS - round-trip
# ---------------------------------------------------------------------------


def test_cobs_round_trips_every_protocol_frame_shape() -> None:
    codec = Framing_COBS(262)
    shapes = (
        b"",
        b"\x00",
        bytes(53),  # an all-zero frame: UID 0, CRC 0, zero payload
        b"\x00\x01\x02\x00\x00\xff",
        bytes(range(256)),
        bytes(254),  # exactly one maximal zero run
        b"\xff" * 254,  # exactly one maximal non-zero run
        b"\xff" * 255,
    )
    for payload in shapes:
        frame = encoded(codec, payload)
        assert COBS_DELIMITER not in frame[:-1], f"encoded output must contain no 0x00: {payload!r}"
        assert frame[-1] == COBS_DELIMITER
        assert decoded(codec, frame[:-1]) == payload, f"round trip failed for {payload!r}"


def test_cobs_overhead_matches_the_documented_bound() -> None:
    codec = Framing_COBS(600)
    for size in (0, 1, 48, 55, 253, 254, 255, 508, 600):
        payload = bytes((i % 251) + 1 for i in range(size))  # no zeros: the worst case for overhead
        assert len(encoded(codec, payload)) <= codec.max_encoded(size), f"size {size} exceeded its own bound"


def test_cobs_never_emits_the_delimiter_over_a_fuzz_sweep() -> None:
    # A deterministic sweep, not unseeded randomness (A3.1): a linear-congruential walk over
    # buffers of every length up to the maximum frame.
    codec = Framing_COBS(300)
    state = 12345
    for size in range(0, 300, 7):
        payload = bytearray(size)
        for i in range(size):
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            payload[i] = (state >> 16) & 0xFF
        frame = encoded(codec, bytes(payload))
        assert COBS_DELIMITER not in frame[:-1]
        assert decoded(codec, frame[:-1]) == bytes(payload)


# ---------------------------------------------------------------------------
# B2.4/B2.5 - malformed input and bounds
# ---------------------------------------------------------------------------


def test_cobs_rejects_a_code_byte_pointing_past_the_frame_end() -> None:
    # B2.4: the decoder must validate every offset before following it, not walk off the buffer.
    codec = Framing_COBS(64)
    assert decoded(codec, b"\x20\x01\x02") is None


def test_cobs_rejects_a_zero_code_byte_inside_a_frame() -> None:
    codec = Framing_COBS(64)
    assert decoded(codec, b"\x03\x01\x02\x00\x01") is None


def test_cobs_rejects_an_oversized_frame() -> None:
    # B2.1/B2.5: the maximum frame length bounds the codec, so an over-long input is a decode
    # failure rather than an out-of-range write into a buffer sized for the worst legal case.
    codec = Framing_COBS(16)
    buf = bytearray(64)
    assert run(codec.encode_into(buf, 40)) is None
    assert run(codec.decode_from(buf, 40)) is None


def test_cobs_rejects_a_negative_or_oversized_size() -> None:
    codec = Framing_COBS(64)
    buf = bytearray(64)
    assert run(codec.encode_into(buf, -1)) is None
    assert run(codec.decode_from(buf, -1)) is None
    assert run(codec.encode_into(bytearray(4), 8)) is None  # size beyond the buffer itself


def test_cobs_decode_of_an_empty_frame_is_empty_not_a_failure() -> None:
    # B2.3's other half: the codec itself round-trips a zero-length payload; skipping *empty
    # frames on the wire* is the read loop's job, not this layer's.
    codec = Framing_COBS(64)
    assert decoded(codec, b"\x01") == b""


def test_cobs_failed_allocation_degrades_to_not_ready() -> None:
    # B2.8: a codec that could not allocate its scratch reports it instead of looking constructed.
    codec = Framing_COBS(-1)  # an impossible frame bound, the same guard LockableBuffer applies
    assert codec.ready() is False
    assert run(codec.encode_into(bytearray(8), 4)) is None
    assert run(codec.decode_from(bytearray(8), 4)) is None


def test_cobs_reports_itself_as_delimited() -> None:
    codec = Framing_COBS(64)
    assert codec.is_delimited() is True
    assert codec.delimiter() == COBS_DELIMITER


def test_cobs_scratch_is_reused_across_frames() -> None:
    # B2.5: allocated once from the frame bound, never per frame.
    codec = Framing_COBS(128)
    first = run(codec.encode_into(bytearray(b"abc"), 3))
    second = run(codec.encode_into(bytearray(b"defg"), 4))
    assert first is not None
    assert second is not None
    assert codec.allocations == 1


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
