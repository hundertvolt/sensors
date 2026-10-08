"""Mock-tier comm-hazard suite for the UART protocol (SPECIFICATION.md Part E.6) - the UART-shaped analogue
of the standing bus-hazard rule. A link has exactly two participants, so multi-device interleaving
and an address sweep are replaced by same-instance concurrency, both-ends-transmitting, and a full frame-field sweep."""

import asyncio

from _error_codes import code
from _uart_comm_harness import Pair, PollRoundClock, accept_set, copied_out, echo_get, frames, run, transfer_limits
from _uart_comm_hazard_common import _EXCHANGE_LIMIT_S, _PAYLOAD, _STEP_BOUND_S, _TIMEOUT_MS, hazard_pair, register_both_crc_modes

from asy_crc_checks import CRC16
from asy_uart_comm import ROLE_RESPONDER, ResponderCallbacks, UARTComm

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from _uart_comm_hazard_common import CrcMaker
    from machine import _LinkDirection as Direction  # one direction of the crossover link

    from asy_base_classes import PieceBuffer

_FRAME = 5 + _PAYLOAD

_CMD_ACK = 0x01
_CMD_GET = 0x02
_CMD_SET = 0x04
_UID = 0
_CMD = 1
_SIZE = 2
_CHUNKS = 3
_CUR = 4
_POS = 5

# @tunable l1.uart_comm_hazard_limit_s = 10
_LIMIT_S = 10
# @tunable l1.uart_comm_hazard_task_bound_s = 8
_TASK_BOUND_S = 8
# @tunable l1.uart_comm_hazard_listener_settle_ms = 5
_LISTENER_SETTLE_MS = 5
# @tunable l1.uart_comm_hazard_concurrency_limit_s = 25
_CONCURRENCY_LIMIT_S = 25
# @tunable l1.uart_comm_hazard_lock_take_ms = 1
_LOCK_TAKE_MS = 1
# @tunable l1.uart_comm_hazard_in_flight_ms = 2
_IN_FLIGHT_MS = 2
# @tunable l1.uart_comm_hazard_listener_park_ms = 5
_LISTENER_PARK_MS = 5
# @tunable l1.uart_comm_hazard_recovery_limit_s = 30
_RECOVERY_LIMIT_S = 30
# @tunable l1.uart_comm_hazard_retention_limit_s = 120
_RETENTION_LIMIT_S = 120
# @tunable l1.uart_comm_hazard_fragment_gap_ms = 3
_FRAGMENT_GAP_MS = 3
# @tunable l1.uart_comm_hazard_mismatch_limit_s = 60
_MISMATCH_LIMIT_S = 60
# @tunable l1.uart_comm_hazard_hammer_limit_s = 300
_HAMMER_LIMIT_S = 300
# @tunable l1.uart_comm_hazard_sustained_timeout_factor = 8
_SUSTAINED_TIMEOUT_FACTOR = 8
# @tunable l1.uart_comm_hazard_recovery_attempts = 4
_RECOVERY_ATTEMPTS = 4
# @tunable l1.uart_comm_hazard_retention_per_transaction_max_bytes = 6.0
_RETENTION_PER_TRANSACTION_MAX_BYTES = 6.0
# @tunable l1.uart_comm_hazard_retention_per_failure_max_bytes = 16.0
_RETENTION_PER_FAILURE_MAX_BYTES = 16.0


def wire_frame(crc: "CrcMaker") -> int:
    # What one frame actually occupies on the wire. The protocol's own frame is 5 + payload_size;
    # a CRC is appended below it, so every assertion that slices or counts whole frames has to add
    # its length or it is silently asserting the no-CRC layout in both modes.
    return _FRAME + (0 if crc is None else crc().length())


# A sustained CLEAN run never consumes the timeout, so the short budget above buys it nothing: at 1x the
# no-CRC arm sits only 1.25x over the 24ms floor, and this gives it the CRC arm's 10x (Part J.7).
_SUSTAINED_TIMEOUT_MS = _TIMEOUT_MS * _SUSTAINED_TIMEOUT_FACTOR


def raw_frame(
    uid: int = 1, cmd: int = _CMD_SET, size: int = 1, chunks: int = 2, cur: int = 1,
    payload: bytes = b"\x07", crc: "CrcMaker" = None,
) -> bytes:
    # With a CRC selected the injected frame carries a correct one, so a field sweep still proves
    # the *structural* rejection it is about rather than being rejected by the CRC layer first.
    frame = bytearray(_FRAME)
    frame[_UID] = uid
    frame[_CMD] = cmd
    frame[_SIZE] = size
    frame[_CHUNKS] = chunks
    frame[_CUR] = cur
    frame[_POS : _POS + len(payload)] = payload
    if crc is None:
        return bytes(frame)
    framed = run(crc().add(frame))
    assert framed is not None
    return bytes(framed)


def listen_once(pair: Pair, injected: bytes) -> "tuple[Any, bytes]":
    # Feeds one raw frame into the responder's receive path and returns what uart_listen() made of
    # it plus every byte it put back on the wire. The wire log is the real assertion: withholding
    # an ACK is the only way this protocol signals rejection.
    pair.fake_b.feed_rx(injected)
    result = run(pair.responder.uart_listen(), limit=_LIMIT_S)
    pair.link.settle()
    return result, pair.wire_from_responder()


# ---------------------------------------------------------------------------
# Same-instance concurrency
# ---------------------------------------------------------------------------


def _check_two_tasks_initiating_at_once_never_interleave_frames(crc: "CrcMaker") -> None:
    # Either the session lock serializes them or the role/re-entrancy gate refuses one; what must
    # never happen is two transactions interleaving frames on the wire.
    pair = hazard_pair(crc)

    async def scenario() -> "list[bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        first = asyncio.create_task(pair.initiator.uart_set(1, b"aaaa"))
        second = asyncio.create_task(pair.initiator.uart_set(2, b"bbbb"))
        results = [await asyncio.wait_for(first, _TASK_BOUND_S), await asyncio.wait_for(second, _TASK_BOUND_S)]
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        listener.cancel()
        return results

    results = run(scenario(), limit=_CONCURRENCY_LIMIT_S)
    assert results.count(True) <= 1  # at most one transaction ran; the other was refused
    pair.link.settle()
    emitted = pair.wire_from_initiator()
    assert len(emitted) % wire_frame(crc) == 0  # only whole frames reached the wire
    for frame in frames(emitted, wire_frame(crc)):
        assert frame[_CUR] <= frame[_CHUNKS]  # and each is internally consistent


def _check_a_second_call_during_a_transaction_is_refused_with_a_sentinel(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)

    async def scenario() -> "tuple[Any, Any]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        first = asyncio.create_task(pair.initiator.uart_get(1))
        await asyncio.sleep_ms(_LOCK_TAKE_MS)  # let the first take the lock
        refused = await pair.initiator.uart_get(2)
        answer = await asyncio.wait_for(first, _TASK_BOUND_S)
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        listener.cancel()
        return answer, refused

    answer, refused = run(scenario(), limit=_CONCURRENCY_LIMIT_S)
    assert refused is None  # the sentinel, never a corrupted second transaction
    assert answer is not None


# ---------------------------------------------------------------------------
# clear() racing an in-flight transaction
# ---------------------------------------------------------------------------


def _check_clear_racing_a_transaction_leaves_it_completed_or_cleanly_failed(crc: "CrcMaker") -> None:
    # The one outcome that must not occur is a silently half-completed transfer: whatever clear()
    # interrupts, the caller is told the truth about it.
    pair = hazard_pair(crc)

    async def scenario() -> "tuple[bool, bytes]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        transfer = asyncio.create_task(pair.initiator.uart_set(1, bytes(_PAYLOAD * 2)))
        await asyncio.sleep_ms(_IN_FLIGHT_MS)
        await asyncio.wait_for(pair.initiator.clear(), _TASK_BOUND_S)
        sent = await asyncio.wait_for(transfer, _TASK_BOUND_S)
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        listener.cancel()
        pair.link.settle()
        return sent, pair.wire_from_initiator()

    sent, emitted = run(scenario(), limit=_CONCURRENCY_LIMIT_S)
    assert sent in (True, False)  # a definite answer either way
    assert len(emitted) % wire_frame(crc) == 0  # never a partial frame left on the wire by the interruption


def _check_clear_terminates_even_while_a_listener_is_parked_forever(crc: "CrcMaker") -> None:
    # The unbounded listen wait holds the bus lock, so this is the only safe interruption - and it
    # must be bounded, which the limit= on run() is what proves.
    pair = hazard_pair(crc)

    async def scenario() -> bool:
        listener = asyncio.create_task(pair.responder.uart_listen())
        await asyncio.sleep_ms(_LISTENER_PARK_MS)
        await asyncio.wait_for(pair.responder.clear(), _TASK_BOUND_S)
        listener.cancel()
        return True

    assert run(scenario(), limit=_EXCHANGE_LIMIT_S) is True


# ---------------------------------------------------------------------------
# Both participants transmitting
# ---------------------------------------------------------------------------


def _check_a_peer_initiating_mid_transaction_is_detected_and_both_recover(crc: "CrcMaker") -> None:
    # Simultaneous initiation is out of contract - there is no arbitration anywhere in the design -
    # so the test proves it is detected and recovered from, never that it works.
    pair = hazard_pair(crc)
    # A GET arrives where this side is waiting for its own ACK: the peer's violation, not noise.
    pair.fake_a.feed_rx(raw_frame(cmd=_CMD_GET, chunks=1, cur=1, crc=crc))

    async def scenario() -> "tuple[bool, Any]":
        first = await pair.initiator.uart_set(1, b"x")  # sees the GET instead of its ACK
        # The aborted transfer left its own chunk 1 sitting in the responder's receive path, so
        # the responder quiesces too before the link is retried - which is exactly what both sides
        # doing a quiesce-and-resync means.
        await pair.responder.clear()
        listener = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")  # the link works again afterwards
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        listener.cancel()
        return first, recovered

    first, recovered = run(scenario(), limit=_CONCURRENCY_LIMIT_S)
    assert first is False
    assert recovered is True
    counts = run(pair.initiator.get_error_counter())
    assert counts["UART_A"]["ErrCount"] > 0  # logged distinctly rather than silently absorbed


# ---------------------------------------------------------------------------
# The frame/field sweep, with wire-log assertions
# ---------------------------------------------------------------------------


def _check_the_command_field_sweep_accepts_only_the_expected_command(crc: "CrcMaker") -> None:
    # Swept against one fixed expectation, which is what a real read site has: only the exact
    # command it is waiting for may pass. A bitmask test would let 0x06 and 0x03 through here.
    pair = hazard_pair(crc)
    for cmd in range(256):
        accepted = pair.responder._validate(bytearray(raw_frame(cmd=cmd, crc=crc)), _CMD_SET, 1, None, None) == 0
        assert accepted == (cmd == _CMD_SET), f"CMD 0x{cmd:02x} was not treated as expected"


def _check_the_uid_field_sweep_stops_at_0xfe(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    for uid in range(256):
        accepted = pair.responder._validate(bytearray(raw_frame(uid=uid, crc=crc)), _CMD_SET, 1, None, None) == 0
        assert accepted == (uid <= 0xFE), f"UID 0x{uid:02x} was not treated as expected"


def _check_the_first_chunk_size_field_sweep_accepts_only_one(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    for size in range(256):
        accepted = pair.responder._validate(bytearray(raw_frame(size=size, crc=crc)), _CMD_SET, 1, None, None) == 0
        assert accepted == (size == 1), f"first-chunk SIZE {size} was not treated as expected"


def _check_the_middle_chunk_size_field_sweep_accepts_only_a_full_payload(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    for size in range(256):
        frame = bytearray(raw_frame(size=size, chunks=4, cur=2, uid=2, crc=crc))
        accepted = pair.responder._validate(frame, _CMD_SET, 2, 4, 2) == 0
        assert accepted == (size == _PAYLOAD), f"middle-chunk SIZE {size} was not treated as expected"


def _check_the_chunks_field_sweep_rejects_zero_and_one_for_a_set(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    for chunks in range(256):
        accepted = pair.responder._validate(bytearray(raw_frame(chunks=chunks, crc=crc)), _CMD_SET, 1, None, None) == 0
        assert accepted == (chunks >= 2), f"CHUNKS {chunks} was not treated as expected"


def _check_the_current_chunk_field_sweep_matches_only_the_expected_index(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    for cur in range(256):
        frame = bytearray(raw_frame(size=_PAYLOAD, chunks=4, cur=cur, uid=2, crc=crc))
        accepted = pair.responder._validate(frame, _CMD_SET, 2, 4, 2) == 0
        assert accepted == (cur == 2), f"CUR_CHUNK {cur} was not treated as expected"


def _check_the_chunks_field_sweep_accepts_only_one_for_a_get(crc: "CrcMaker") -> None:
    # J.4: the initiator sends a GET as a one-chunk train, so any other CHUNKS is an invalid frame.
    pair = hazard_pair(crc)
    for chunks in range(256):
        frame = bytearray(raw_frame(cmd=_CMD_GET, size=1, chunks=chunks, cur=1, crc=crc))
        accepted = pair.responder._validate(frame, _CMD_GET, 1, None, None) == 0
        assert accepted == (chunks == 1), f"GET CHUNKS {chunks} was not treated as expected"


def _check_the_last_chunk_size_sweep_follows_the_train_shape(crc: "CrcMaker") -> None:
    # J.3/J.4: a last chunk carries 1 to payload_size bytes; an empty one is legal only closing a two-chunk train.
    pair = hazard_pair(crc)
    for chunks, low in ((3, 1), (2, 0)):
        for size in range(256):
            frame = bytearray(raw_frame(uid=chunks, size=size, chunks=chunks, cur=chunks, crc=crc))
            accepted = pair.responder._validate(frame, _CMD_SET, chunks, chunks, chunks) == 0
            assert accepted == (low <= size <= _PAYLOAD), f"last-chunk SIZE {size} of a {chunks}-chunk train was not treated as expected"


def _ack_frame(crc: "CrcMaker", uid: int, cmd: int = _CMD_ACK, size: int = 0, chunks: int = 1, cur: int = 1) -> bytearray:
    return bytearray(raw_frame(uid=uid, cmd=cmd, size=size, chunks=chunks, cur=cur, payload=b"", crc=crc))


def _get_frame(crc: "CrcMaker", uid: int = 1, cmd: int = _CMD_GET, size: int = 1, cur: int = 1) -> bytearray:
    return bytearray(raw_frame(uid=uid, cmd=cmd, size=size, chunks=1, cur=cur, payload=b"\x01", crc=crc))


def _check_every_ack_field_sweep_accepts_only_the_ack_shape(crc: "CrcMaker") -> None:
    # An ACK is SIZE 0, CHUNKS 1, CUR_CHUNK 1 and the UID of the frame it confirms (J.3); its CMD is swept below.
    pair = hazard_pair(crc)
    uid = 5
    for value in range(256):
        for label, frame, legal in (
            ("SIZE", _ack_frame(crc, uid, size=value), 0),
            ("CHUNKS", _ack_frame(crc, uid, chunks=value), 1),
            ("CUR_CHUNK", _ack_frame(crc, uid, cur=value), 1),
        ):
            accepted = pair.responder._validate(frame, _CMD_ACK, 1, 1, uid) == 0
            assert accepted == (value == legal), f"ACK {label} {value} was not treated as expected"
        err = pair.responder._validate(_ack_frame(crc, value), _CMD_ACK, 1, 1, uid)
        # 0xFF is no UID at all; any other is a stale or foreign ACK, which must not confirm this frame.
        expected = 0 if value == uid else code("E", "UART_FRAME_INVALID") if value == 0xFF else code("E", "UART_NO_ACK")
        assert err == expected, f"ACK UID 0x{value:02x} returned {err}, expected {expected}"


def _check_every_get_field_sweep_accepts_only_a_one_byte_first_chunk(crc: "CrcMaker") -> None:
    # A GET's one chunk carries the one-byte command id at UID up to 0xFE; its CMD and CHUNKS have their own sweeps.
    pair = hazard_pair(crc)
    for value in range(256):
        for label, frame, accept in (
            ("SIZE", _get_frame(crc, size=value), value == 1),
            ("CUR_CHUNK", _get_frame(crc, cur=value), value == 1),
            ("UID", _get_frame(crc, uid=value), value <= 0xFE),
        ):
            accepted = pair.responder._validate(frame, _CMD_GET, 1, None, None) == 0
            assert accepted == accept, f"GET {label} {value} was not treated as expected"


def _check_the_data_chunk_uid_sweep_accepts_only_the_successor(crc: "CrcMaker") -> None:
    # A data chunk's UID is its predecessor's plus one, wrapping 0xFE -> 0 (0xFF is never sent, J.3).
    pair = hazard_pair(crc)
    for previous in (0x00, 0x7F, 0xFE):
        successor = 0 if previous == 0xFE else previous + 1
        for uid in range(256):
            frame = bytearray(raw_frame(uid=uid, size=_PAYLOAD, chunks=3, cur=2, crc=crc))
            accepted = pair.responder._validate(frame, _CMD_SET, 2, 3, successor) == 0
            assert accepted == (uid == successor), f"data-chunk UID 0x{uid:02x} after 0x{previous:02x} was not treated as expected"


def _check_the_chunks_constancy_sweep_accepts_only_the_latched_total(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    for chunks in range(256):
        frame = bytearray(raw_frame(uid=2, size=_PAYLOAD, chunks=chunks, cur=2, crc=crc))
        accepted = pair.responder._validate(frame, _CMD_SET, 2, 4, 2) == 0
        assert accepted == (chunks == 4), f"CHUNKS {chunks} on chunk 2 of a 4-chunk train was not treated as expected"


def _check_the_command_sweep_against_an_expected_ack_and_get(crc: "CrcMaker") -> None:
    # The SET sweep's twin for the other two read sites: each accepts only its own exact command.
    pair = hazard_pair(crc)
    for cmd in range(256):
        accepted = pair.responder._validate(_ack_frame(crc, 5, cmd=cmd), _CMD_ACK, 1, 1, 5) == 0
        assert accepted == (cmd == _CMD_ACK), f"CMD 0x{cmd:02x} where an ACK was expected was not treated as expected"
        accepted = pair.responder._validate(_get_frame(crc, cmd=cmd), _CMD_GET, 1, None, None) == 0
        assert accepted == (cmd == _CMD_GET), f"CMD 0x{cmd:02x} where a GET was expected was not treated as expected"


def _check_no_ack_is_emitted_for_any_rejected_frame(crc: "CrcMaker") -> None:
    # A rejected frame and a silently mishandled one both return failure, so the wire log is
    # what tells them apart. Withholding the ACK *is* the rejection signal in this protocol.
    rejected = (
        ("multi-bit CMD", raw_frame(cmd=0x06, crc=crc)),
        ("undefined CMD", raw_frame(cmd=0x00, crc=crc)),
        ("UID 0xFF", raw_frame(uid=0xFF, crc=crc)),
        ("first chunk SIZE 0", raw_frame(size=0, crc=crc)),
        ("first chunk SIZE 2", raw_frame(size=2, crc=crc)),
        ("SET with CHUNKS 1", raw_frame(chunks=1, crc=crc)),
        ("CHUNKS 0", raw_frame(chunks=0, crc=crc)),
        ("CUR_CHUNK past CHUNKS", raw_frame(chunks=2, cur=3, crc=crc)),
        ("SIZE past payload_size", raw_frame(size=_PAYLOAD + 1, crc=crc)),
        ("GET with CHUNKS 2", raw_frame(cmd=_CMD_GET, chunks=2, crc=crc)),
        ("GET with SIZE 2", raw_frame(cmd=_CMD_GET, size=2, chunks=1, crc=crc)),
    )
    for label, frame in rejected:
        pair = hazard_pair(crc)
        result, emitted = listen_once(pair, frame)
        assert result.cmd_id is None, f"{label} was accepted"
        assert emitted == b"", f"{label} was acknowledged - rejection is signalled by silence"


def _check_a_legal_frame_is_acknowledged_on_the_wire(crc: "CrcMaker") -> None:
    # The positive control for the test above: without it, a responder that acknowledged nothing
    # at all would pass the whole rejection sweep. A two-frame SET is the right shape here - it
    # completes with no peer scheduled, whereas a GET's answer needs the initiator to acknowledge it.
    pair = hazard_pair(crc)
    pair.fake_b.feed_rx(raw_frame(uid=1, cmd=_CMD_SET, size=1, chunks=2, cur=1, payload=b"\x07", crc=crc))
    pair.fake_b.feed_rx(raw_frame(uid=2, cmd=_CMD_SET, size=3, chunks=2, cur=2, payload=b"abc", crc=crc))
    result = run(pair.responder.uart_listen(), limit=_LIMIT_S)
    pair.link.settle()
    emitted = pair.wire_from_responder()
    assert result.cmd_id == 0x07
    assert copied_out(result.payload) == b"abc"
    assert len(emitted) == 2 * wire_frame(crc)  # one ACK per frame, the second deferred until the size check
    assert emitted[_CMD] == _CMD_ACK
    assert emitted[_UID] == 1
    assert emitted[wire_frame(crc) + _UID] == 2


def _check_a_train_whose_chunks_total_changes_is_rejected_before_the_data_is_kept(crc: "CrcMaker") -> None:
    # The multi-frame half of the sweep: the peer re-declares CHUNKS mid-train to truncate the
    # transfer, and the receiver must not report success on partial data.
    pair = hazard_pair(crc)
    pair.fake_b.feed_rx(raw_frame(uid=1, cmd=_CMD_SET, size=1, chunks=3, cur=1, crc=crc))
    pair.fake_b.feed_rx(raw_frame(uid=2, cmd=_CMD_SET, size=_PAYLOAD, chunks=2, cur=2, crc=crc))
    result = run(pair.responder.uart_listen(), limit=_LIMIT_S)
    assert result.cmd_id is None
    assert result.payload is None


def _check_a_train_with_a_stale_data_chunk_uid_is_rejected(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    pair.fake_b.feed_rx(raw_frame(uid=10, cmd=_CMD_SET, size=1, chunks=3, cur=1, crc=crc))
    pair.fake_b.feed_rx(raw_frame(uid=99, cmd=_CMD_SET, size=_PAYLOAD, chunks=3, cur=2, crc=crc))  # not 11
    result = run(pair.responder.uart_listen(), limit=_LIMIT_S)
    assert result.cmd_id is None


def _check_a_three_chunk_train_ending_in_an_empty_chunk_is_rejected(crc: "CrcMaker") -> None:
    # A lone last chunk is refused for its CUR_CHUNK first, so the empty-last rule is reached only through a real
    # train: chunks 1 and 2 are acknowledged, the empty chunk 3 is not (J.4's deferred final ACK).
    pair = hazard_pair(crc)
    pair.fake_b.feed_rx(raw_frame(uid=1, cmd=_CMD_SET, size=1, chunks=3, cur=1, crc=crc))
    pair.fake_b.feed_rx(raw_frame(uid=2, cmd=_CMD_SET, size=_PAYLOAD, chunks=3, cur=2, crc=crc))
    pair.fake_b.feed_rx(raw_frame(uid=3, cmd=_CMD_SET, size=0, chunks=3, cur=3, payload=b"", crc=crc))
    result = run(pair.responder.uart_listen(), limit=_LIMIT_S)
    pair.link.settle()
    assert result.cmd_id is None, "a three-chunk train with an empty last chunk was delivered"
    assert len(pair.wire_from_responder()) == 2 * wire_frame(crc), "the empty last chunk was acknowledged"


# ---------------------------------------------------------------------------
# Byte-level faults, recovered from
# ---------------------------------------------------------------------------


def _check_a_corrupted_byte_stream_recovers_to_a_working_exchange(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    direction = pair.link.direction_from(pair.fake_a)
    direction.corrupt_indices = {1: 0xFF}  # rewrite the very first frame's CMD field

    async def scenario() -> "tuple[bool, bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        broken = await pair.initiator.uart_set(1, b"x")
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        listener.cancel()
        direction.corrupt_indices = {}
        healthy = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        healthy.cancel()
        return broken, recovered

    broken, recovered = run(scenario(), limit=_RECOVERY_LIMIT_S)
    assert broken is False
    assert recovered is True


def _check_a_truncated_frame_recovers_to_a_working_exchange(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    direction = pair.link.direction_from(pair.fake_a)
    direction.truncate_after = wire_frame(crc) // 2  # the first frame never completes

    async def scenario() -> "tuple[bool, bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        broken = await pair.initiator.uart_set(1, b"x")
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        listener.cancel()
        direction.truncate_after = None
        healthy = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        healthy.cancel()
        return broken, recovered

    broken, recovered = run(scenario(), limit=_RECOVERY_LIMIT_S)
    assert broken is False
    assert recovered is True


def _check_injected_noise_before_a_real_frame_is_recovered_from(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    pair.link.direction_from(pair.fake_a).noise_before_next = bytearray(b"\xde\xad\xbe\xef")

    async def scenario() -> "tuple[bool, bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        broken = await pair.initiator.uart_set(1, b"x")
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        listener.cancel()
        healthy = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        healthy.cancel()
        return broken, recovered

    broken, recovered = run(scenario(), limit=_RECOVERY_LIMIT_S)
    assert broken is False  # the noise shifts the frame, so this one cannot succeed
    assert recovered is True  # but the link is usable again afterwards


def _check_one_sided_silence_recovers_once_the_direction_returns(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    direction = pair.link.direction_from(pair.fake_b)
    direction.silent = True

    async def scenario() -> "tuple[bool, bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        broken = await pair.initiator.uart_set(1, b"x")
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        listener.cancel()
        direction.silent = False
        healthy = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        healthy.cancel()
        return broken, recovered

    broken, recovered = run(scenario(), limit=_RECOVERY_LIMIT_S)
    assert broken is False
    assert recovered is True


def _check_a_receive_overrun_recovers_to_a_working_exchange(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    pair.fake_b.plant_rx_error(0x08)  # UARTRSR OE: the far UART lost a received byte before its ring

    async def scenario() -> "tuple[bool, bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        broken = await pair.initiator.uart_set(1, b"x")
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        listener.cancel()
        healthy = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")
        await asyncio.sleep_ms(_LISTENER_SETTLE_MS)
        healthy.cancel()
        return broken, recovered

    broken, recovered = run(scenario(), limit=_RECOVERY_LIMIT_S)
    assert broken is False
    assert pair.driver_b.rx_overruns == 1
    assert recovered is True


# ---- steady-state memory (audit pass) --------------------------------------------------------

# @tunable l1.uart_comm_hazard_warmup_rounds = 20
_WARMUP = 20
# @tunable l1.uart_comm_hazard_measured_rounds = 100
_MEASURED = 100


def _scrub(pair: Pair) -> None:
    # The link's wire log is scaffolding a test reads back, not something the protocol retains.
    for direction in (pair.link.a_to_b, pair.link.b_to_a):
        direction.wire_log.clear()


async def _listen_rounds(pair: Pair, rounds: int) -> None:
    for _ in range(rounds):
        await pair.responder.uart_listen()


async def _yield_like_one_transaction(pair: Pair) -> None:
    # One transaction's scheduling profile without the protocol: a 4-frame train plus its 4 ACKs,
    # each frame CRC'd on write and checked on read. With no CRC configured this is a single yield,
    # which is what an uncrc'd transaction costs.
    crc = pair.driver_a.crc
    width = crc.length()
    if not width:
        await asyncio.sleep_ms(0)
        return
    scratch = bytearray(_FRAME + width)
    for _ in range(8):
        await crc.add_into(scratch, _FRAME)
        await crc.check_from(scratch, size=_FRAME + width)


async def _measure_retention(pair: Pair, clock: PollRoundClock) -> "tuple[int, float]":
    import gc

    # Three rounds per transaction, not one: a listen round is not always consumed by a completed
    # transaction, and a budget of exactly n+1 starves the last few rather than measuring them. With it
    # raised, 120/120 complete with zero errors in both CRC modes, so the shortfall was the harness's.
    listener = asyncio.create_task(_listen_rounds(pair, (_WARMUP + _MEASURED) * 3))
    payload = bytes(_PAYLOAD * 3)
    done = 0
    for _ in range(_WARMUP):  # every path taken at least once before the heap is sampled
        done += 1 if await pair.initiator.uart_set(1, payload) else 0
        _scrub(pair)
    # An ambient control first, yield-matched: listeners parked by earlier tests keep allocating
    # whenever this one yields, and a CRC yields once per byte. Repeating that CRC work with no link
    # involved measures the scheduling churn instead of charging it to the protocol.
    gc.collect()
    idle_before = gc.mem_alloc()
    for _ in range(_MEASURED):
        await _yield_like_one_transaction(pair)
    gc.collect()
    ambient = gc.mem_alloc() - idle_before

    gc.collect()
    before = gc.mem_alloc()
    clock.arm()
    for _ in range(_MEASURED):
        done += 1 if await pair.initiator.uart_set(1, payload) else 0
        _scrub(pair)
    assert clock.disarm(), "the planted stall did not fire inside the measured run"
    gc.collect()
    grew = max(0, (gc.mem_alloc() - before) - ambient) / _MEASURED
    listener.cancel()
    try:
        await listener
    except asyncio.CancelledError:  # expected; anything else is a real failure
        pass
    return done, grew


def _retention(crc: "CrcMaker", stall_after: int = 0, stall_ms: int = 0) -> None:
    # CLAUDE.md's memory-safety ladder at its most direct: a link running for weeks has no backstop
    # below the watchdog, so the steady state must not grow the heap. The fakes' recorders are muted
    # so the number is src/'s alone; hazard_pair(crc) is built out here (its asyncio.run() cannot nest).
    pair = hazard_pair(crc, timeout_ms=_SUSTAINED_TIMEOUT_MS)
    for fake in (pair.fake_a, pair.fake_b):
        fake.log.append = lambda entry: None  # type: ignore[method-assign]
    clock = PollRoundClock(stall_after, stall_ms)
    with clock:
        completed, per_transaction = run(_measure_retention(pair, clock), limit=_RETENTION_LIMIT_S)
    assert completed == _WARMUP + _MEASURED, completed
    # A strict zero would be brittle against interpreter-internal caches; one frame of slack still
    # catches any real per-transaction retention long before it could matter on the target.
    assert per_transaction < wire_frame(crc), f"{per_transaction} bytes retained per transaction"


def _check_a_long_run_of_transactions_retains_no_memory(crc: "CrcMaker") -> None:
    _retention(crc)


# ---------------------------------------------------------------------------
# Which error is reported, not merely that one was: every test above asserts ErrCount, none ErrNum,
# so a fault reporting the wrong code would pass the whole suite. The catalog is the module's only
# diagnostic surface (the global catalog's UART band, SPECIFICATION.md Part C.7.1).
# ---------------------------------------------------------------------------


def errnos(comm: UARTComm) -> "list[int]":
    # Errors only: ErrNum holds both kinds and ErrType tells them apart. Indexed, not zip()ed: MicroPython has no strict=.
    entry = run(comm.get_error_counter())[comm.name]
    nums, kinds = entry["ErrNum"], entry["ErrType"]
    return [nums[i] for i in range(len(nums)) if kinds[i] == "E"]


def last_errno(comm: UARTComm) -> int:
    codes = errnos(comm)
    return codes[-1] if codes else 0


def _check_a_silent_peer_reports_no_ack_not_a_generic_failure(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    pair.link.direction_from(pair.fake_b).silent = True
    assert run(pair.with_listener(pair.initiator.uart_set(0x02, b"x"), rounds=0), limit=_LIMIT_S) is False
    assert last_errno(pair.initiator) == code("E", "UART_NO_ACK"), f"a silent peer reported errno {last_errno(pair.initiator)}"


def _check_a_listener_whose_frame_never_arrives_reports_a_read_timeout(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)

    async def scenario() -> None:
        await pair.responder.uart_listen()

    # Nothing is fed, and clear() cancels the parked read - the listener's own documented unstick.
    async def drive() -> None:
        listener = asyncio.create_task(scenario())
        await asyncio.sleep_ms(_LISTENER_PARK_MS)
        await pair.responder.clear()
        await asyncio.wait_for(listener, _STEP_BOUND_S)

    run(drive(), limit=_LIMIT_S)
    assert last_errno(pair.responder) == code("E", "TIMEOUT")


def _check_a_reentrant_call_reports_its_own_errno(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    pair.link.direction_from(pair.fake_b).silent = True

    async def scenario() -> None:
        first = asyncio.create_task(pair.initiator.uart_get(0x01))
        await asyncio.sleep_ms(_IN_FLIGHT_MS)
        assert await pair.initiator.uart_get(0x01) is None  # refused while the first holds the link
        await asyncio.wait_for(first, _STEP_BOUND_S)

    run(scenario(), limit=_EXCHANGE_LIMIT_S)
    # Read outside the coroutine: errnos() drives its own asyncio.run(), and nesting one inside a
    # running loop segfaults this interpreter rather than raising (CLAUDE.md's known segfault).
    assert code("E", "UART_REENTRANT") in errnos(pair.initiator), f"got {errnos(pair.initiator)}"


def _check_a_bad_argument_reports_bad_arg_before_anything_reaches_the_wire(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    assert run(pair.initiator.uart_set(0x101, b"x"), limit=_STEP_BOUND_S) is False  # command id past one byte
    assert last_errno(pair.initiator) == code("E", "BAD_ARG")
    assert pair.wire_from_initiator() == b"", "a refused argument still put bytes on the wire"


def _check_an_oversized_payload_reports_payload_too_large(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    # _CHUNKS_MAX is 255, so 254 data chunks is the ceiling; one byte past it must be refused.
    too_big = bytes(_PAYLOAD * 254 + 1)
    assert run(pair.initiator.uart_set(0x02, too_big), limit=_EXCHANGE_LIMIT_S) is False
    assert last_errno(pair.initiator) == code("E", "UART_PAYLOAD_TOO_LARGE")
    assert pair.wire_from_initiator() == b"", "an oversized payload was partially sent before being refused"


def _check_a_peer_initiating_mid_transaction_reports_peer_initiated(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    # A data frame where an ACK is due: the one out-of-contract case the protocol names separately,
    # because there is no arbitration and it is the peer's violation rather than link noise.
    pair.fake_a.feed_rx(raw_frame(cmd=_CMD_GET, size=1, chunks=2, cur=1, crc=crc))
    assert run(pair.initiator.uart_get(0x01), limit=_LIMIT_S) is None
    assert code("E", "UART_PEER_INITIATED") in errnos(pair.initiator), f"got {errnos(pair.initiator)}"


def _check_a_size_mismatch_against_an_expected_size_reports_it_distinctly(crc: "CrcMaker") -> None:
    # The answer is 2 bytes; the caller declared it expects 5. A wrong-length answer must be named,
    # not silently truncated or padded into something plausible, and its final ACK withheld (J.4).
    pair = hazard_pair(crc)
    ack = raw_frame(uid=1, cmd=_CMD_ACK, size=0, chunks=1, cur=1, payload=b"", crc=crc)
    # The peer's whole answer is queued before the call, so every read finds its frame waiting and a
    # host stall cannot expire a reply budget first: the verdict is scheduling-independent (J.7).
    pair.fake_a.feed_rx(
        ack
        + raw_frame(uid=1, cmd=_CMD_SET, size=1, chunks=2, cur=1, payload=b"\x01", crc=crc)
        + raw_frame(uid=2, cmd=_CMD_SET, size=2, chunks=2, cur=2, payload=b"vv", crc=crc),
    )
    assert run(pair.initiator.uart_get(0x01, exp_size=5), limit=_LIMIT_S) is None
    assert errnos(pair.initiator) == [code("E", "UART_SIZE_MISMATCH")], f"got {errnos(pair.initiator)}"
    get = raw_frame(uid=1, cmd=_CMD_GET, size=1, chunks=1, cur=1, payload=b"\x01", crc=crc)
    assert pair.wire_from_initiator() == get + ack, "the mismatched train's final chunk was acknowledged"


# ---------------------------------------------------------------------------
# Dropped, duplicated and delayed bytes. A framing/parity/overrun fault never raises on rp2
# (SPECIFICATION.md Part C.3.2), so every electrical fault reaches this layer as one of these three
# stream shapes - the whole observable surface of the physical layer, not exotic extras.
# ---------------------------------------------------------------------------


def _check_a_dropped_byte_mid_frame_recovers_to_a_working_exchange(crc: "CrcMaker") -> None:
    # A byte lost to a framing error or a full FIFO shortens the frame: the read cannot complete,
    # and recovery has to come from the timeout plus resync, not from the frame itself.
    pair = hazard_pair(crc)
    direction = pair.link.direction_from(pair.fake_b)
    direction.drop_indices = {3}  # inside the first answer frame's header
    assert run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=_EXCHANGE_LIMIT_S) is None
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] > 0

    direction.drop_indices = set()
    run(pair.initiator.clear(), limit=_LIMIT_S)
    run(pair.responder.clear(), limit=_LIMIT_S)
    answer = run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=_EXCHANGE_LIMIT_S)
    assert copied_out(answer) == b"v", "the link never recovered after a dropped byte"


def _check_duplicated_bytes_on_the_wire_recover_to_a_working_exchange(crc: "CrcMaker") -> None:
    # A repeated byte is what a stuck line or a re-sent buffer looks like from here: it desynchronises
    # the fixed-size framing, so the next frame reads as garbage until a resync realigns it.
    pair = hazard_pair(crc)
    direction = pair.link.direction_from(pair.fake_b)
    direction.duplicate_next = 3
    run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=_EXCHANGE_LIMIT_S)

    direction.duplicate_next = 0
    run(pair.initiator.clear(), limit=_LIMIT_S)
    run(pair.responder.clear(), limit=_LIMIT_S)
    answer = run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=_EXCHANGE_LIMIT_S)
    assert copied_out(answer) == b"v", "the link never recovered after duplicated bytes"


def _check_a_frame_delivered_in_two_fragments_still_assembles(crc: "CrcMaker") -> None:
    # The ordinary case at a real baud rate: a frame does not arrive atomically. The read loop must
    # keep waiting across the gap rather than treat a partial frame as a fault - this is the one of
    # the three that must NOT produce an error.
    pair = hazard_pair(crc)
    direction = pair.link.direction_from(pair.fake_b)

    async def scenario() -> "PieceBuffer | None":
        listener = asyncio.create_task(pair.responder.uart_listen())
        direction.delay = True
        work = asyncio.create_task(pair.initiator.uart_get(0x01))
        await asyncio.sleep_ms(_FRAGMENT_GAP_MS)
        direction.delay = False
        pair.link.release_delayed()  # the held bytes land in one go, mid-transaction
        answer = await asyncio.wait_for(work, _STEP_BOUND_S)
        await asyncio.wait_for(listener, _STEP_BOUND_S)
        return answer

    answer = run(scenario(), limit=_EXCHANGE_LIMIT_S)
    assert copied_out(answer) == b"v"
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] == 0, (
        "a fragmented but complete frame was treated as a fault"
    )


# ---------------------------------------------------------------------------
# The integrity envelope. The dev wiring selects CRCPass, so structural field validation is the
# *only* check (SPECIFICATION.md Part J). These pin exactly where that boundary falls: "corruption
# is handled" is true of the header and false of the payload.
# ---------------------------------------------------------------------------


def _check_a_corrupted_header_byte_is_caught_by_structural_validation(crc: "CrcMaker") -> None:
    # The CMD field: a flipped bit here makes the frame structurally impossible, and the receiver
    # rejects it without needing a CRC.
    pair = hazard_pair(crc)
    pair.link.direction_from(pair.fake_b).corrupt_indices = {_CMD: 0xFF}
    assert run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=_EXCHANGE_LIMIT_S) is None
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] > 0


def _answer_payload_offset(marker: int = ord("v"), crc: "CrcMaker" = None) -> int:
    # corrupt_indices addresses a STREAM offset, not a frame offset, and the answer comes back as a
    # multi-frame train behind the ACK - so the payload byte's position is searched for rather than
    # computed. The sustained budget: a probe that timed out would derive an offset from a short stream.
    probe = hazard_pair(crc, timeout_ms=_SUSTAINED_TIMEOUT_MS)
    assert run(probe.with_listener(probe.initiator.uart_get(0x01)), limit=_EXCHANGE_LIMIT_S) is not None, "the probe GET did not complete, so no offset can be derived from it"
    wire = probe.wire_from_responder()
    offset = wire.find(bytes([marker]), wire_frame(crc))  # past the ACK frame
    assert offset > 0, f"no answer payload byte found in the responder's wire log: {wire!r}"
    return offset


def _check_the_probed_payload_offset_lands_on_a_frames_payload_start(crc: "CrcMaker") -> None:
    # What the search above has to produce for the injection below to mean anything, asserted
    # without assuming how many frames the train carries: a payload position of SOME whole frame.
    # A shifted stream would otherwise put the corruption in a header and read as "rejected".
    offset = _answer_payload_offset(crc=crc)
    assert (offset - _POS) % wire_frame(crc) == 0, f"probed offset {offset} is not a frame's payload start ({wire_frame(crc)}-byte frames, header {_POS})"


def _check_a_corrupted_payload_byte_is_delivered_undetected_without_a_crc(crc: "CrcMaker") -> None:
    # The other half of the same boundary, and the uncomfortable one: with no CRC configured, a bit flip in
    # the payload passes every structural check and reaches the caller as good data. A documented property
    # of the dev configuration, pinned so enabling a CRC is visibly what changes it.
    offset = _answer_payload_offset(crc=crc)
    # The sustained budget, not this tier's 1x: a transaction that times out returns None here too,
    # which would read as "the corruption was caught" and quietly retire the claim below.
    pair = hazard_pair(crc, timeout_ms=_SUSTAINED_TIMEOUT_MS)
    pair.link.direction_from(pair.fake_b).corrupt_indices = {offset: 0xFF}
    answer = run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=_EXCHANGE_LIMIT_S)
    wire = pair.wire_from_responder()
    # Proves the injection landed on the payload byte rather than somewhere a shifted stream put
    # it, so a future divergence names itself instead of arriving as "the frame was rejected".
    assert len(wire) > offset and wire[offset] == (ord("v") ^ 0xFF), f"the corruption did not land on the answer payload at offset {offset}: {wire!r}"
    assert answer is not None, f"no answer for a payload corruption at stream offset {offset} - this test no longer pins what it claims. Responder wire: {wire!r}"
    assert copied_out(answer) == bytes([ord("v") ^ 0xFF]), f"expected a corrupted byte, got {copied_out(answer)!r}"
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] == 0, (
        "a payload corruption was somehow counted - the no-CRC envelope has changed"
    )


def _check_with_a_crc_configured_the_same_payload_corruption_is_caught(crc: "CrcMaker") -> None:
    # Same injection, CRC16 on the bus objects: now the frame fails verification and is rejected.
    # This is what makes the test above a statement about configuration rather than about the
    # protocol being unable to detect corruption at all.
    #
    # The sustained budget for the same reason as above, and more so: a CRC yields once per byte,
    # so this pair is the slowest one in the file and a timeout would make this pass vacuously.
    pair = Pair(
        payload_size=_PAYLOAD, timeout=_SUSTAINED_TIMEOUT_MS, get_callback=echo_get(b"v"), set_callback=accept_set(),
        crc_a=CRC16(), crc_b=CRC16(),
    )
    assert run(pair.setup()) is True
    # A byte inside the answer train, past the ACK frame. Which byte does not matter here and is
    # deliberately not pinned: the claim is that with a CRC every corruption in the frame is caught,
    # whereas the test above shows a payload byte specifically is not caught without one.
    pair.link.direction_from(pair.fake_b).corrupt_indices = {wire_frame(crc) + 7: 0xFF}
    assert run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=_EXCHANGE_LIMIT_S) is None, (
        "a CRC-protected corruption was still delivered"
    )
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] > 0


def _check_a_receive_buffer_smaller_than_a_frame_is_refused_at_construction(crc: "CrcMaker") -> None:
    # The silent-tail-loss failure: a frame that does not fit the receive ring loses its end, and the result is
    # indistinguishable from a link fault. The module refuses the configuration instead (SPECIFICATION.md Part J.6).
    from asy_uart_comm import ROLE_INITIATOR, UARTComm
    from asy_uart_driver import UART as Driver
    # rxbuf holds the 260-byte frame, so only the ring's floor can refuse this: both refuse with one code.
    too_small = Driver(0, tx_pin=0, rx_pin=1, rxbuf=512, txbuf=256, rx_ring=256, poll_wait_ms=1, poll_idle_ms=1)
    comm = UARTComm(too_small, ROLE_INITIATOR, limits=transfer_limits(payload_size=255, timeout=_TIMEOUT_MS), name="UART_TINY")
    assert comm._init_errno == code("E", "UART_RXBUF"), "a receive ring below one whole frame was accepted"
    assert run(comm.setup()) is False, "a refused construction still opened its readiness gate"



# ---------------------------------------------------------------------------
# The mismatched-peer signature: parameters are agreed out of band and never negotiated, so a pair
# configured differently is diagnosed (E89, link unintelligible), never recovered (SPECIFICATION.md
# Part J.6). The signature the C-port reconciliation will most likely meet first.
# ---------------------------------------------------------------------------


def _mismatched_responder(pair: Pair, payload_size: int) -> UARTComm:
    # Same link, same wire, a responder that disagrees about the frame size. Every frame the
    # initiator sends is then the wrong length for it, which is exactly what a wrong payload_size,
    # a wrong baud rate or a different CRC algorithm all look like from the receiving end.
    return UARTComm(
        pair.driver_b, ROLE_RESPONDER, limits=transfer_limits(payload_size=payload_size, timeout=pair.responder._timeout),
        callbacks=ResponderCallbacks(echo_get(b"v"), accept_set(), None), name="UART_MISMATCH",
    )


def _check_a_payload_size_mismatch_never_delivers_wrong_data(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    responder = _mismatched_responder(pair, _PAYLOAD + 8)
    assert run(responder.setup()) is True

    async def scenario() -> bool:
        listener = asyncio.create_task(responder.uart_listen())
        try:
            return await pair.initiator.uart_set(0x02, b"mismatched")
        finally:
            await responder.clear()
            try:
                await asyncio.wait_for(listener, _STEP_BOUND_S)
            except asyncio.TimeoutError:
                listener.cancel()

    # The one configuration error the design cannot self-heal: it must fail, not deliver a
    # wrong-length payload as though it were right.
    assert run(scenario(), limit=_MISMATCH_LIMIT_S) is False
    assert errnos(pair.initiator), "a payload_size mismatch produced no logged error at all"


async def _failed_exchanges(initiator: UARTComm, responder: UARTComm, count: int) -> None:
    # Each exchange with its own listener, unstuck by clear() if the initiator gave up first.
    for _ in range(count):
        listener = asyncio.create_task(responder.uart_listen())
        await initiator.uart_set(0x02, b"nonsense")
        await responder.clear()
        try:
            await asyncio.wait_for(listener, _STEP_BOUND_S)
        except asyncio.TimeoutError:
            listener.cancel()


def _check_a_peer_that_never_produces_a_valid_frame_is_diagnosed(crc: "CrcMaker") -> None:
    # A speak-when-spoken-to peer with a mismatched payload_size: its frames die inside the failing read, which
    # counts them, so the diagnostic fires once the streak is reached (SPECIFICATION.md Part J.6).
    pair = hazard_pair(crc)
    responder = _mismatched_responder(pair, _PAYLOAD + 8)
    assert run(responder.setup()) is True
    run(_failed_exchanges(pair.initiator, responder, 1), limit=_RETENTION_LIMIT_S)
    # The diagnostic waits for a streak, so one failed exchange must not trip it and several in a row must.
    assert code("E", "UART_LINK_UNINTELLIGIBLE") not in errnos(responder), f"fired after one exchange: {errnos(responder)}"
    run(_failed_exchanges(pair.initiator, responder, 3), limit=_RETENTION_LIMIT_S)
    assert code("E", "UART_LINK_UNINTELLIGIBLE") in errnos(responder), f"never fired against a mismatched peer: {errnos(responder)}"


def _check_a_peer_whose_frames_all_fail_their_crc_is_diagnosed(crc: "CrcMaker") -> None:
    # The CRC-mismatched form of the same peer: every frame completes, then fails its check inside the read.
    pair = hazard_pair(crc)
    to_responder = pair.link.direction_from(pair.fake_a)
    to_responder.corrupt_indices = {k * wire_frame(crc) - 1: 0x01 for k in range(1, 17)}  # each frame's last CRC byte
    run(_failed_exchanges(pair.initiator, pair.responder, 4), limit=_RETENTION_LIMIT_S)
    assert code("E", "UART_LINK_UNINTELLIGIBLE") in errnos(pair.responder), f"never fired against a CRC-mismatched peer: {errnos(pair.responder)}"


def _check_a_break_like_run_of_nulls_recovers_to_a_working_exchange(crc: "CrcMaker") -> None:
    # A line break, a stuck-low driver and a disconnected floating RX all reach this layer the same
    # way: a run of 0x00 bytes. rp2 never raises for it (C.3.2), so the only correct behaviour is to
    # treat it as garbage, resync past it, and keep working.
    pair = hazard_pair(crc)
    pair.fake_a.feed_rx(bytes(wire_frame(crc) * 3))
    run(pair.initiator.clear(), limit=_EXCHANGE_LIMIT_S)
    answer = run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=_RECOVERY_LIMIT_S)
    assert copied_out(answer) == b"v", "the link never recovered from a break-like null run"


# ---------------------------------------------------------------------------
# Recombined failure modes: a real degraded link does not fail one way at a time - a marginal
# connector drops bytes AND corrupts them AND stalls. Faults are applied in pairs, because the
# question is whether two recovery paths running over each other still converge.
# ---------------------------------------------------------------------------


async def _exchange_quietly(pair: Pair) -> "PieceBuffer | None":
    # One GET with its listener, never raising out whatever the faults do to it.
    listener = asyncio.create_task(pair.responder.uart_listen())
    try:
        return await pair.initiator.uart_get(0x01)
    finally:
        await pair.responder.clear()
        try:
            await asyncio.wait_for(listener, _STEP_BOUND_S)
        except asyncio.TimeoutError:
            listener.cancel()


def _recombination_check(crc: "CrcMaker", apply_faults: "Callable[[Direction, Direction], None]") -> None:
    # Shared body: apply a pair of faults, drive several exchanges through them, then clear the
    # faults and require the link to come back. The contract is never-raises plus self-healing,
    # so what is asserted is convergence, not that any particular exchange survived.
    pair = hazard_pair(crc)
    to_initiator = pair.link.direction_from(pair.fake_b)
    to_responder = pair.link.direction_from(pair.fake_a)
    apply_faults(to_initiator, to_responder)

    async def under_fault() -> None:
        for _ in range(3):
            await _exchange_quietly(pair)

    run(under_fault(), limit=_RETENTION_LIMIT_S)

    for direction in (to_initiator, to_responder):
        direction.silent = False
        direction.drop_indices = set()
        direction.corrupt_indices = {}
        direction.truncate_after = None
        direction.duplicate_next = 0
        direction.capacity = 4096
    run(pair.initiator.clear(), limit=_RECOVERY_LIMIT_S)
    run(pair.responder.clear(), limit=_RECOVERY_LIMIT_S)

    recovered = False
    for _ in range(_RECOVERY_ATTEMPTS):  # several attempts: a resync hold-off may still be running down
        answer = run(_exchange_quietly(pair), limit=_MISMATCH_LIMIT_S)
        if copied_out(answer) == b"v":
            recovered = True
            break
    assert recovered, "the link never converged after the faults were cleared"


def _check_corruption_plus_dropped_bytes_still_converges(crc: "CrcMaker") -> None:
    def faults(to_initiator: "Direction", _to_responder: "Direction") -> None:
        to_initiator.corrupt_indices = {2: 0xFF, 9: 0x0F}
        to_initiator.drop_indices = {5, 17}

    _recombination_check(crc, faults)


def _check_truncation_plus_noise_still_converges(crc: "CrcMaker") -> None:
    def faults(to_initiator: "Direction", _to_responder: "Direction") -> None:
        to_initiator.truncate_after = 9
        to_initiator.noise_before_next = bytearray(b"\xa5\x5a\xa5")

    _recombination_check(crc, faults)


def _check_overrun_plus_duplication_still_converges(crc: "CrcMaker") -> None:
    def faults(to_initiator: "Direction", _to_responder: "Direction") -> None:
        to_initiator.capacity = wire_frame(crc) // 2  # the far FIFO cannot hold one whole frame
        to_initiator.duplicate_next = 4

    _recombination_check(crc, faults)


def _check_faults_in_both_directions_at_once_still_converges(crc: "CrcMaker") -> None:
    # The worst shape: neither end can trust what it receives, so both recovery paths run at once.
    def faults(to_initiator: "Direction", to_responder: "Direction") -> None:
        to_initiator.corrupt_indices = {3: 0xFF}
        to_responder.drop_indices = {6}

    _recombination_check(crc, faults)


def _check_silence_then_corruption_then_clean_still_converges(crc: "CrcMaker") -> None:
    # Sequential rather than simultaneous: a link that goes away, comes back wrong, then comes back
    # right. Each transition has to leave the state machine somewhere it can recover from.
    pair = hazard_pair(crc)
    to_initiator = pair.link.direction_from(pair.fake_b)

    to_initiator.silent = True
    run(_exchange_quietly(pair), limit=_MISMATCH_LIMIT_S)
    to_initiator.silent = False
    to_initiator.corrupt_indices = {4: 0xFF}
    run(_exchange_quietly(pair), limit=_MISMATCH_LIMIT_S)
    to_initiator.corrupt_indices = {}
    run(pair.initiator.clear(), limit=_RECOVERY_LIMIT_S)
    run(pair.responder.clear(), limit=_RECOVERY_LIMIT_S)

    recovered = False
    for _ in range(_RECOVERY_ATTEMPTS):
        answer = run(_exchange_quietly(pair), limit=_MISMATCH_LIMIT_S)
        if copied_out(answer) == b"v":
            recovered = True
            break
    assert recovered, "the link never converged after silence, then corruption, then a clean line"


# ---------------------------------------------------------------------------
# Hammering the link on its own, heap watched throughout. A link deployed for weeks has no backstop
# below the watchdog (CLAUDE.md's memory-safety ladder), so "works once" and "works for an hour"
# are different claims.
# ---------------------------------------------------------------------------

# @tunable l1.uart_comm_hazard_hammer_rounds = 150
_HAMMER_ROUNDS = 150
_HAMMER_SAMPLE_AT = _HAMMER_ROUNDS // 3  # the warm-up that absorbs first-touch allocation
_HAMMER_MEASURED = _HAMMER_ROUNDS - _HAMMER_SAMPLE_AT - 1  # transactions the heap delta spans


def _hammer_clean(crc: "CrcMaker", stall_after: int = 0, stall_ms: int = 0) -> None:
    import gc

    pair = hazard_pair(crc, timeout_ms=_SUSTAINED_TIMEOUT_MS)
    clock = PollRoundClock(stall_after, stall_ms)
    for fake in (pair.fake_a, pair.fake_b):
        fake.log.append = lambda entry: None  # type: ignore[method-assign]
    payload = bytes(_PAYLOAD * 3)

    async def hammer() -> "tuple[int, int]":
        listener = asyncio.create_task(_listen_rounds(pair, _HAMMER_ROUNDS * 3))
        ok = 0
        for i in range(_HAMMER_ROUNDS):
            if await pair.initiator.uart_set(1, payload):
                ok += 1
            _scrub(pair)
            if i == _HAMMER_SAMPLE_AT:  # sample once the steady state is genuinely reached
                gc.collect()
                mid[0] = gc.mem_alloc()
                clock.arm()
        assert clock.disarm(), "the planted stall did not fire inside the measured run"
        gc.collect()
        grew = gc.mem_alloc() - mid[0]
        listener.cancel()
        try:
            await listener
        except asyncio.CancelledError:  # expected
            pass
        return ok, grew

    mid = [0]
    with clock:
        ok, grew = run(hammer(), limit=_HAMMER_LIMIT_S)
    assert ok == _HAMMER_ROUNDS, f"only {ok}/{_HAMMER_ROUNDS} hammered transactions completed"
    assert not errnos(pair.initiator), f"a clean link logged errors under sustained load: {errnos(pair.initiator)}"
    # A per-transaction RATE over the span actually measured: a leak scales with the work done,
    # while interpreter caching is a host-dependent fixed sprinkle (0 B locally, 64 B and 288 B on
    # two runners). The bound sits above that, far below one retained frame's 13+ B/transaction.
    per_transaction = grew / _HAMMER_MEASURED
    assert per_transaction < _RETENTION_PER_TRANSACTION_MAX_BYTES, f"{grew} bytes over {_HAMMER_MEASURED} transactions = {per_transaction:.2f} B/transaction"


def _hammer_faulted(crc: "CrcMaker", stall_after: int = 0, stall_ms: int = 0) -> None:
    # The same hammer with a fault running underneath it: the failure path is the one that
    # allocates hardest (resync, drain, backoff), so this is where an unbounded retry or a leak in
    # the recovery path would show.
    import gc

    pair = hazard_pair(crc)
    for fake in (pair.fake_a, pair.fake_b):
        fake.log.append = lambda entry: None  # type: ignore[method-assign]
    to_initiator = pair.link.direction_from(pair.fake_b)
    fault = to_initiator.corrupt_indices  # one dict, re-aimed in place before each transaction
    clock = PollRoundClock(stall_after, stall_ms)

    async def burst(rounds: int, *, measured: bool = False) -> int:
        failures = 0
        for i in range(rounds):
            if measured and i == rounds - 1:
                clock.arm()  # the last one: a transaction failed there is still recovering when the heap is sampled
            # corrupt_indices takes stream offsets, so each transaction's own first frame back is aimed at:
            # the SIZE byte of the ACK its GET is waiting for, which fails every one of them.
            fault.clear()
            fault[to_initiator.offered + _SIZE] = 0xFF
            if await pair.initiator.uart_get(0x01) is None:  # none may raise
                failures += 1
            _scrub(pair)
        return failures

    async def hammer() -> "tuple[int, int]":
        listener = asyncio.create_task(_listen_rounds(pair, 240))
        # The first fault allocates a fixed ~3.4kB - the log history's buffers and the resync scratch, built
        # once and reused. Measured constant at 10, 30, 60 and 120 failures, so it is a one-time cost, not
        # per-failure retention. The first burst absorbs it; only the second is measured.
        await burst(30)
        gc.collect()
        before[0] = gc.mem_alloc()
        failures = await burst(30, measured=True)
        assert clock.disarm(), "the planted stall did not fire inside the measured burst"
        gc.collect()
        grew = gc.mem_alloc() - before[0]
        listener.cancel()
        try:
            await listener
        except asyncio.CancelledError:  # expected
            pass
        return failures, grew

    before = [0]
    with clock:  # one entry for both halves: a deadline stored on the clock stays on it
        failures, grew = run(hammer(), limit=_HAMMER_LIMIT_S)
        # The bound is per failure, so it means something only when every measured transaction failed.
        assert failures == 30, f"{failures} of the 30 measured transactions failed"
        # Same reasoning as the clean hammer, against the failure path's scale. The one-time cost absorbed in
        # the first burst is ~114 B/failure here, so a bound well below that still catches an unabsorbed or
        # leaking path while tolerating host-dependent interpreter noise (CI 4.3, locally 0).
        per_failure = grew / 30
        assert per_failure < _RETENTION_PER_FAILURE_MAX_BYTES, f"{grew} bytes over 30 failures = {per_failure:.1f} B/failure"

        fault.clear()
        run(pair.initiator.clear(), limit=_RECOVERY_LIMIT_S)
        run(pair.responder.clear(), limit=_RECOVERY_LIMIT_S)
        recovered = False
        for _ in range(_RECOVERY_ATTEMPTS):
            answer = run(_exchange_quietly(pair), limit=_MISMATCH_LIMIT_S)
            if copied_out(answer) == b"v":
                recovered = True
                break
    assert recovered, "a hammered, faulted link never recovered once the fault was cleared"


# ---------------------------------------------------------------------------
# Second-pass gaps: the three cases the systematic sweep over the general UART failure taxonomy
# found uncovered. Each is a field scenario rather than a theoretical one.
# ---------------------------------------------------------------------------


def _check_a_lost_final_ack_is_reported_as_failure_though_the_peer_acted(crc: "CrcMaker") -> None:
    # The protocol's at-least-once seam: the final ACK is deferred until after the responder's
    # total-size check, so a lost one leaves the peer having accepted the whole train while
    # this side reports failure. A caller that retries on False must tolerate that (Part J).
    pair = hazard_pair(crc)
    first_ack = raw_frame(uid=1, cmd=_CMD_ACK, size=0, chunks=1, cur=1, payload=b"", crc=crc)
    # Every read finds its frame already waiting, so no host stall can expire a budget first (J.7):
    # the initiator runs with only the header's ACK queued, so the final one is lost by construction.
    pair.fake_a.feed_rx(first_ack)
    assert run(pair.initiator.uart_set(0x02, b"acted-on"), limit=_LIMIT_S) is False, "a lost final ACK was reported as success"
    assert errnos(pair.initiator) == [code("E", "UART_NO_ACK")], f"got {errnos(pair.initiator)}"
    # The responder then reads the very bytes the initiator sent, already queued on its side.
    result = run(pair.responder.uart_listen(), limit=_LIMIT_S)
    # The asymmetry itself: the responder did the work the initiator was told failed.
    assert copied_out(result.payload) == b"acted-on", f"the responder did not actually receive the train: {result!r}"
    final_ack = raw_frame(uid=2, cmd=_CMD_ACK, size=0, chunks=1, cur=1, payload=b"", crc=crc)
    assert pair.wire_from_responder() == first_ack + final_ack, "the responder's ACKs differ from the ones the initiator was scripted with"


def _check_a_peer_that_resets_mid_transaction_converges_once_it_returns(crc: "CrcMaker") -> None:
    # The Arduino rebooting mid-train: the peer vanishes, loses all protocol state, and comes back
    # with a fresh UID sequence and an empty buffer while this side is still mid-transaction. A
    # fresh responder on the same bus is exactly that - it shares nothing with the old one.
    pair = hazard_pair(crc)
    to_initiator = pair.link.direction_from(pair.fake_b)

    async def cut_off_mid_train() -> None:
        listener = asyncio.create_task(pair.responder.uart_listen())
        to_initiator.silent = True  # the peer stops answering part-way through
        try:
            await pair.initiator.uart_set(0x02, bytes(_PAYLOAD * 3))
        finally:
            await pair.responder.clear()
            try:
                await asyncio.wait_for(listener, _STEP_BOUND_S)
            except asyncio.TimeoutError:
                listener.cancel()

    run(cut_off_mid_train(), limit=_MISMATCH_LIMIT_S)

    # The peer returns as a brand-new instance: no UID history, no half-read frame, nothing.
    to_initiator.silent = False
    reborn = UARTComm(
        pair.driver_b, ROLE_RESPONDER, limits=transfer_limits(payload_size=_PAYLOAD, timeout=pair.responder._timeout),
        callbacks=ResponderCallbacks(echo_get(b"v"), accept_set(), None), name="UART_REBORN",
    )
    assert run(reborn.setup()) is True  # setup() drains whatever the old instance left behind
    run(pair.initiator.clear(), limit=_RECOVERY_LIMIT_S)

    async def one() -> "PieceBuffer | None":
        listener = asyncio.create_task(reborn.uart_listen())
        try:
            return await pair.initiator.uart_get(0x01)
        finally:
            await reborn.clear()
            try:
                await asyncio.wait_for(listener, _STEP_BOUND_S)
            except asyncio.TimeoutError:
                listener.cancel()

    recovered = False
    for _ in range(_RECOVERY_ATTEMPTS):
        answer = run(one(), limit=_MISMATCH_LIMIT_S)
        if copied_out(answer) == b"v":
            recovered = True
            break
    assert recovered, "the link never converged after the peer reset mid-transaction"


def _check_a_disconnect_then_reconnect_mid_frame_recovers(crc: "CrcMaker") -> None:
    # A cable pulled and pushed back: the stream stops part-way through a frame, then resumes at an
    # arbitrary byte boundary. The receiver is left holding half a frame that will never complete,
    # and the bytes that follow are the middle of a different one.
    pair = hazard_pair(crc)
    to_initiator = pair.link.direction_from(pair.fake_b)
    to_initiator.truncate_after = wire_frame(crc) // 2  # cut mid-frame
    run(_exchange_quietly(pair), limit=_MISMATCH_LIMIT_S)

    to_initiator.truncate_after = None
    # Reconnection lands mid-frame: a partial frame's worth of bytes with no header at the front.
    pair.fake_a.feed_rx(bytes(range(wire_frame(crc) // 2)))
    run(pair.initiator.clear(), limit=_RECOVERY_LIMIT_S)

    recovered = False
    for _ in range(_RECOVERY_ATTEMPTS):
        answer = run(_exchange_quietly(pair), limit=_MISMATCH_LIMIT_S)
        if copied_out(answer) == b"v":
            recovered = True
            break
    assert recovered, "the link never recovered from a disconnect/reconnect mid-frame"


def _check_the_crc_appears_on_the_wire_big_endian_after_the_payload(crc: "CrcMaker") -> None:
    # Byte order is part of the wire contract, not an implementation detail: the C peer appends its own CRC
    # in the platform's NATIVE order and is deliberately not wire-compatible with this one (SPECIFICATION.md
    # Part J, UART_C_PORT_CHANGELOG.md A7). A silent change here looks exactly like a dead link.
    if crc is None:
        return  # nothing is appended without a CRC; the companion mode covers the other half
    pair = hazard_pair(crc)
    assert run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=_EXCHANGE_LIMIT_S) is not None
    wire = pair.wire_from_initiator()
    width = crc().length()
    assert len(wire) >= wire_frame(crc)
    first = wire[:wire_frame(crc)]
    body, tail = first[:-width], first[-width:]
    expected = run(crc().add(bytearray(body)))
    assert expected is not None
    assert bytes(tail) == bytes(expected[-width:]), (
        f"the CRC on the wire is not what this CRC produces for that body: {bytes(tail)!r}"
    )
    # Big-endian specifically: the high byte first. A native-order switch would flip these.
    assert tail[0] == (int.from_bytes(bytes(tail), "big") >> 8) & 0xFF


# CLAUDE.md's standing rule for a stress test: it must pass under gc.threshold(-1), MicroPython's
# own default, BEFORE the project's chosen 32768 - one that only passes with proactive collection
# hides the defect the rule exists to surface. gc.threshold() is global, so each body restores it.
# @tunable gc.threshold_bytes = 32768
_GC_THRESHOLDS = (("gcdefault", -1), ("gc32768", 32768))


def _under_threshold(body: "Callable[[CrcMaker], None]", crc: "CrcMaker", threshold: int) -> None:
    import gc

    original = gc.threshold()
    gc.threshold(threshold)
    try:
        body(crc)
    finally:
        gc.threshold(original)


def _check_sustained_hammering_never_degrades_or_grows_the_heap(crc: "CrcMaker") -> None:
    for _, threshold in _GC_THRESHOLDS:
        _under_threshold(_hammer_clean, crc, threshold)


def _check_hammering_a_faulted_link_never_raises_and_still_recovers(crc: "CrcMaker") -> None:
    for _, threshold in _GC_THRESHOLDS:
        _under_threshold(_hammer_faulted, crc, threshold)


# One host stall past every reply budget above (30 and 240 ms), planted inside each measured window: on the wall
# clock it fails a transaction there and flips each check, the faulted hammer's on the coverage build (its heap
# figures are larger); on the poll-round clock no bound can expire.
_PLANTED_STALL_MS = 300
_PLANTED_STALL_AFTER = 4  # sleeps after arm(): inside the reply wait of the transaction arm() precedes


def _check_a_host_stall_cannot_fail_the_retention_check(crc: "CrcMaker") -> None:
    _retention(crc, _PLANTED_STALL_AFTER, _PLANTED_STALL_MS)


def _check_a_host_stall_cannot_fail_the_sustained_hammer(crc: "CrcMaker") -> None:
    _hammer_clean(crc, _PLANTED_STALL_AFTER, _PLANTED_STALL_MS)


def _check_a_host_stall_cannot_fail_the_faulted_hammer(crc: "CrcMaker") -> None:
    _hammer_faulted(crc, _PLANTED_STALL_AFTER, _PLANTED_STALL_MS)


# Registered once per mode, so a failure names the configuration that broke. Three checks are about one
# configuration by construction, not omission: without a CRC a payload corruption is undetectable and a frame
# cannot fail its check, so each in the opposite mode would assert the opposite of what it says.
_MODE_SPECIFIC = {
    "a_corrupted_payload_byte_is_delivered_undetected_without_a_crc": "nocrc",
    "with_a_crc_configured_the_same_payload_corruption_is_caught": "crc16",
    "a_peer_whose_frames_all_fail_their_crc_is_diagnosed": "crc16",
}
# These enter the poll-round clock themselves, with a planted stall or around a measured window.
_OWN_CLOCK = (
    "a_long_run_of_transactions_retains_no_memory",
    "sustained_hammering_never_degrades_or_grows_the_heap",
    "hammering_a_faulted_link_never_raises_and_still_recovers",
    "a_host_stall_cannot_fail_the_retention_check",
    "a_host_stall_cannot_fail_the_sustained_hammer",
    "a_host_stall_cannot_fail_the_faulted_hammer",
)
register_both_crc_modes(globals(), _MODE_SPECIFIC, _OWN_CLOCK)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
