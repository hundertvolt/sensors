"""Unit tests for src/asy_framing_codecs.py - the pluggable frame codec asy_uart_driver.py writes
through (SPECIFICATION.md Part G.2). Covers the pass-through default's byte-identity guarantee, COBS
round-trips including every shape the protocol can emit, and each malformed-input rejection."""

from _async_harness import run
from _recording_print import record_prints

import asy_framing_codecs
from asy_framing_codecs import COBS_DELIMITER, FramingCOBS, FramingPass

# @tunable l1.framing_codecs_run_bound_s = 5
_RUN_BOUND_S = 5


def encoded(codec: "FramingPass | FramingCOBS", payload: bytes) -> bytes:
    buf = bytearray(payload)
    view = run(codec.encode_into(buf, len(payload)), _RUN_BOUND_S)
    assert view is not None
    return bytes(view)


def decoded(codec: "FramingPass | FramingCOBS", frame: bytes) -> "bytes | None":
    buf = bytearray(frame)
    size = run(codec.decode_from(buf, len(frame)), _RUN_BOUND_S)
    if size is None:
        return None
    return bytes(buf[:size])


# ---------------------------------------------------------------------------
# Pass-through - the default, and the regression that proves nothing changed
# ---------------------------------------------------------------------------


def test_pass_through_is_byte_identical() -> None:
    codec = FramingPass()
    for payload in (b"", b"\x00", b"\x00\x01\xff", bytes(range(64))):
        assert encoded(codec, payload) == payload
        assert decoded(codec, payload) == payload


def test_pass_through_has_no_overhead_and_no_delimiter() -> None:
    codec = FramingPass()
    assert codec.overhead(0) == 0
    assert codec.overhead(255) == 0
    assert codec.max_encoded(48) == 48
    assert codec.is_delimited() is False


def test_pass_through_is_always_ready() -> None:
    # ready()'s counterpart: a codec that allocates nothing can never fail to construct.
    assert FramingPass().ready() is True


def test_pass_through_still_bounds_every_size_against_the_buffer() -> None:
    # FramingPass overrides nothing, so the base class's own bound check is what holds here: a
    # pass-through codec may still not hand out a view past the end of the caller's buffer, nor
    # report a decoded length longer than what actually arrived.
    codec = FramingPass()
    assert codec.delimiter() is None
    assert run(codec.encode_into(bytearray(4), 5), _RUN_BOUND_S) is None
    assert run(codec.encode_into(bytearray(4), -1), _RUN_BOUND_S) is None
    assert run(codec.decode_from(bytearray(4), 5), _RUN_BOUND_S) is None
    assert run(codec.decode_from(bytearray(4), -1), _RUN_BOUND_S) is None


# ---------------------------------------------------------------------------
# COBS - round-trip
# ---------------------------------------------------------------------------


def test_cobs_round_trips_every_protocol_frame_shape() -> None:
    codec = FramingCOBS(262)
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
    codec = FramingCOBS(600)
    for size in (0, 1, 48, 55, 253, 254, 255, 508, 600):
        payload = bytes((i % 251) + 1 for i in range(size))  # no zeros: the worst case for overhead
        assert len(encoded(codec, payload)) <= codec.max_encoded(size), f"size {size} exceeded its own bound"


def test_cobs_never_emits_the_delimiter_over_a_fuzz_sweep() -> None:
    # A deterministic sweep, not unseeded randomness: a linear-congruential walk over
    # buffers of every length up to the maximum frame.
    codec = FramingCOBS(300)
    state = 12345
    for size in range(0, 300, 7):
        payload = bytearray(size)
        for i in range(size):
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            payload[i] = (state >> 16) & 0xFF
        frame = encoded(codec, bytes(payload))
        assert COBS_DELIMITER not in frame[:-1]
        assert decoded(codec, frame[:-1]) == bytes(payload)


def test_cobs_round_trips_every_length_up_to_the_frame_bound() -> None:
    # Every length, not a stride: all-zero, zero-free and zero-every-third payloads.
    codec = FramingCOBS(303)  # max_encoded(300)
    for size in range(301):
        for pattern in (0, 1, 3):
            payload = bytearray(size)
            for i in range(size):
                payload[i] = 0 if pattern == 0 or (pattern == 3 and i % 3 == 2) else (i % 255) + 1
            frame = encoded(codec, bytes(payload))
            assert COBS_DELIMITER not in frame[:-1], f"inner 0x00 at size {size}, pattern {pattern}"
            assert len(frame) <= codec.max_encoded(size), f"size {size} exceeded its own bound"
            assert decoded(codec, frame[:-1]) == bytes(payload), f"round trip failed at size {size}, pattern {pattern}"


def test_a_262_byte_frame_bound_decodes_every_length_and_refuses_one_past() -> None:
    # A codec sized exactly to its frame (a 255-byte payload frame plus CRC16): the decode input is the encoded
    # frame without its delimiter, up to the run-code bytes longer than the frame, and every length decodes.
    codec = FramingCOBS(262)
    for size in range(263):
        for pattern in (0, 1):
            payload = bytes(size) if pattern == 0 else bytes((i % 255) + 1 for i in range(size))
            frame = encoded(codec, payload)
            buf = bytearray(frame[:-1])
            assert run(codec.decode_from(buf, len(buf)), _RUN_BOUND_S) == size, f"size {size}, pattern {pattern}"
            assert bytes(buf[:size]) == payload, f"size {size}, pattern {pattern}"
    past = codec.max_encoded(262)  # one byte past the longest legal decode input, max_encoded(262) - 1
    assert run(codec.decode_from(bytearray(b"\x01" * past), past), _RUN_BOUND_S) is None
    assert run(codec.decode_from(bytearray(b"\x01" * (past - 1)), past - 1), _RUN_BOUND_S) is not None


def test_a_returned_view_aliases_the_scratch_until_the_next_encode() -> None:
    # The contract: a caller finishes with a returned view before the next encode_into().
    codec = FramingCOBS(64)
    first = run(codec.encode_into(bytearray(b"abc"), 3), _RUN_BOUND_S)
    assert first is not None
    snapshot = bytes(first)
    second = run(codec.encode_into(bytearray(b"defgh"), 5), _RUN_BOUND_S)
    assert second is not None
    assert bytes(first) != snapshot
    assert bytes(first) == bytes(second)[0 : len(snapshot)]


# ---------------------------------------------------------------------------
# Malformed input and bounds
# ---------------------------------------------------------------------------


def test_cobs_rejects_a_code_byte_pointing_past_the_frame_end() -> None:
    # The decoder must validate every offset before following it, not walk off the buffer.
    codec = FramingCOBS(64)
    assert decoded(codec, b"\x20\x01\x02") is None


def test_cobs_rejects_a_zero_code_byte_inside_a_frame() -> None:
    codec = FramingCOBS(64)
    assert decoded(codec, b"\x03\x01\x02\x00\x01") is None


def test_cobs_rejects_an_oversized_frame() -> None:
    # The maximum frame length bounds the codec, so an over-long input is a decode
    # failure rather than an out-of-range write into a buffer sized for the worst legal case.
    codec = FramingCOBS(16)
    buf = bytearray(64)
    assert run(codec.encode_into(buf, 40), _RUN_BOUND_S) is None
    assert run(codec.decode_from(buf, 40), _RUN_BOUND_S) is None


def test_cobs_rejects_a_negative_or_oversized_size() -> None:
    codec = FramingCOBS(64)
    buf = bytearray(64)
    assert run(codec.encode_into(buf, -1), _RUN_BOUND_S) is None
    assert run(codec.decode_from(buf, -1), _RUN_BOUND_S) is None
    assert run(codec.encode_into(bytearray(4), 8), _RUN_BOUND_S) is None  # size beyond the buffer itself


def test_cobs_decode_of_an_empty_frame_is_empty_not_a_failure() -> None:
    # The other half: the codec itself round-trips a zero-length payload; skipping *empty
    # frames on the wire* is the read loop's job, not this layer's.
    codec = FramingCOBS(64)
    assert decoded(codec, b"\x01") == b""


def test_cobs_failed_allocation_degrades_to_not_ready() -> None:
    # A codec that could not allocate its scratch reports it instead of looking constructed.
    codec = FramingCOBS(-1)  # an impossible frame bound, the same guard RegionBuffer applies
    assert codec.ready() is False
    assert run(codec.encode_into(bytearray(8), 4), _RUN_BOUND_S) is None
    assert run(codec.decode_from(bytearray(8), 4), _RUN_BOUND_S) is None


def test_cobs_scratch_too_large_for_the_heap_degrades_the_same_way() -> None:
    # The other half of ready(). A negative bound never reaches the allocation at all, so the except
    # clause that catches a real MemoryError/OverflowError - the case that actually happens on a
    # fragmented heap, rather than a caller typo - had no test of its own.
    with record_prints() as rec:  # recorded, never printed: the interpreter's own text would trip the memory gates
        codec = FramingCOBS(1 << 40)  # well-formed, and far past what any heap here can serve
        huge = FramingCOBS(1 << 63)  # past the machine word: bytearray() raises OverflowError instead
    assert codec._scratch is None
    assert codec.ready() is False
    assert run(codec.encode_into(bytearray(8), 4), _RUN_BOUND_S) is None
    assert huge.ready() is False
    assert [(line[:2], type(line[2])) for line in rec.lines] == [
        (("FramingCOBS", "scratch allocation failed:"), MemoryError),
        (("FramingCOBS", "scratch allocation failed:"), OverflowError),
    ]


def test_a_failed_cobs_scratch_allocation_prints_its_own_text_once() -> None:
    # No logger in the codec: a caught allocation failure prints one console line with its own text, so the memory
    # gates read it, while a bound that never allocates (a caller mistake) prints nothing.
    err = MemoryError("injected for the codec scratch")  # worded clear of the memory gates' markers

    def failing(*_args: object) -> bytearray:
        raise err

    asy_framing_codecs.bytearray = failing  # type: ignore[attr-defined]
    try:
        with record_prints() as rec:
            codec = FramingCOBS(64)
    finally:
        del asy_framing_codecs.bytearray  # type: ignore[attr-defined]
    assert codec.ready() is False
    assert rec.lines == [("FramingCOBS", "scratch allocation failed:", err)]
    assert rec.text() == "FramingCOBS scratch allocation failed: injected for the codec scratch"
    with record_prints() as rec:
        guarded = [FramingCOBS(0), FramingCOBS(-1)]
    assert [c.ready() for c in guarded] == [False, False]
    assert rec.lines == []
    assert FramingCOBS(64).ready() is True  # the module's own bytearray is back


def test_cobs_reports_itself_as_delimited() -> None:
    codec = FramingCOBS(64)
    assert codec.is_delimited() is True
    assert codec.delimiter() == COBS_DELIMITER


def test_cobs_scratch_is_reused_across_frames() -> None:
    # allocated once from the frame bound, never per frame: the second encode lands where the first did.
    codec = FramingCOBS(128)
    scratch = codec._scratch
    assert scratch is not None
    first = run(codec.encode_into(bytearray(b"abc"), 3), _RUN_BOUND_S)
    second = run(codec.encode_into(bytearray(b"defg"), 4), _RUN_BOUND_S)
    assert first is not None
    assert second is not None
    assert codec._scratch is scratch
    assert bytes(scratch[0 : len(second)]) == bytes(second) == b"\x05defg\x00"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
