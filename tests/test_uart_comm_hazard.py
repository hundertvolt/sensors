"""Mock-tier comm-hazard suite for the UART protocol (requirement H1) - the UART-shaped analogue
of the standing bus-hazard rule. A link has exactly two participants, so multi-device interleaving
and an address sweep are replaced by same-instance concurrency, both-ends-transmitting, and a full frame-field sweep."""

import asyncio

from _uart_comm_harness import Pair, accept_set, echo_get, frames, run

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

# A short timeout keeps each recovery cycle cheap: this tier is about which frames are accepted and
# what is emitted, not about real-world durations, and every value still clears the module's own
# floor of 2 x poll_wait_ms + the worst-case GC pause.
_TIMEOUT_MS = 30
_PAYLOAD = 8
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


def hazard_pair() -> Pair:
    pair = Pair(payload_size=_PAYLOAD, timeout=_TIMEOUT_MS, get_callback=echo_get(b"v"), set_callback=accept_set())
    assert run(pair.setup()) is True
    return pair


def raw_frame(uid: int = 1, cmd: int = _CMD_SET, size: int = 1, chunks: int = 2, cur: int = 1, payload: bytes = b"\x07") -> bytes:
    frame = bytearray(_FRAME)
    frame[_UID] = uid
    frame[_CMD] = cmd
    frame[_SIZE] = size
    frame[_CHUNKS] = chunks
    frame[_CUR] = cur
    frame[_POS : _POS + len(payload)] = payload
    return bytes(frame)


def listen_once(pair: Pair, injected: bytes) -> "tuple[Any, bytes]":
    # Feeds one raw frame into the responder's receive path and returns what uart_listen() made of
    # it plus every byte it put back on the wire. The wire log is the real assertion: withholding
    # an ACK is the only way this protocol signals rejection.
    pair.fake_b.feed_rx(injected)
    result = run(pair.responder.uart_listen(), limit=10)
    pair.link.settle()
    return result, pair.wire_from_responder()


# ---------------------------------------------------------------------------
# H1.1 - same-instance concurrency
# ---------------------------------------------------------------------------


def test_two_tasks_initiating_at_once_never_interleave_frames() -> None:
    # Either the session lock serializes them or the role/re-entrancy gate refuses one; what must
    # never happen is two transactions interleaving frames on the wire.
    pair = hazard_pair()

    async def scenario() -> "list[bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        first = asyncio.create_task(pair.initiator.uart_set(1, b"aaaa"))
        second = asyncio.create_task(pair.initiator.uart_set(2, b"bbbb"))
        results = [await asyncio.wait_for(first, 8), await asyncio.wait_for(second, 8)]
        await asyncio.sleep_ms(5)
        listener.cancel()
        return results

    results = run(scenario(), limit=25)
    assert results.count(True) <= 1  # at most one transaction ran; the other was refused
    pair.link.settle()
    emitted = pair.wire_from_initiator()
    assert len(emitted) % _FRAME == 0  # only whole frames reached the wire
    for frame in frames(emitted, _FRAME):
        assert frame[_CUR] <= frame[_CHUNKS]  # and each is internally consistent


def test_a_second_call_during_a_transaction_is_refused_with_a_sentinel() -> None:
    pair = hazard_pair()

    async def scenario() -> "tuple[Any, Any]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        first = asyncio.create_task(pair.initiator.uart_get(1))
        await asyncio.sleep_ms(1)  # let the first take the lock
        refused = await pair.initiator.uart_get(2)
        answer = await asyncio.wait_for(first, 8)
        await asyncio.sleep_ms(5)
        listener.cancel()
        return answer, refused

    answer, refused = run(scenario(), limit=25)
    assert refused is None  # the sentinel, never a corrupted second transaction
    assert answer is not None


# ---------------------------------------------------------------------------
# H1.2 - clear() racing an in-flight transaction
# ---------------------------------------------------------------------------


def test_clear_racing_a_transaction_leaves_it_completed_or_cleanly_failed() -> None:
    # The one outcome that must not occur is a silently half-completed transfer: whatever clear()
    # interrupts, the caller is told the truth about it.
    pair = hazard_pair()

    async def scenario() -> "tuple[bool, bytes]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        transfer = asyncio.create_task(pair.initiator.uart_set(1, bytes(_PAYLOAD * 2)))
        await asyncio.sleep_ms(2)
        await asyncio.wait_for(pair.initiator.clear(), 8)
        sent = await asyncio.wait_for(transfer, 8)
        await asyncio.sleep_ms(5)
        listener.cancel()
        pair.link.settle()
        return sent, pair.wire_from_initiator()

    sent, emitted = run(scenario(), limit=25)
    assert sent in (True, False)  # a definite answer either way
    assert len(emitted) % _FRAME == 0  # never a partial frame left on the wire by the interruption


def test_clear_terminates_even_while_a_listener_is_parked_forever() -> None:
    # The unbounded listen wait holds the bus lock, so this is the only safe interruption - and it
    # must be bounded, which the limit= on run() is what proves.
    pair = hazard_pair()

    async def scenario() -> bool:
        listener = asyncio.create_task(pair.responder.uart_listen())
        await asyncio.sleep_ms(5)
        await asyncio.wait_for(pair.responder.clear(), 8)
        listener.cancel()
        return True

    assert run(scenario(), limit=20) is True


# ---------------------------------------------------------------------------
# H1.3 - both participants transmitting
# ---------------------------------------------------------------------------


def test_a_peer_initiating_mid_transaction_is_detected_and_both_recover() -> None:
    # Simultaneous initiation is out of contract - there is no arbitration anywhere in the design -
    # so the test proves it is detected and recovered from, never that it works.
    pair = hazard_pair()
    # A GET arrives where this side is waiting for its own ACK: the peer's violation, not noise.
    pair.fake_a.feed_rx(raw_frame(cmd=_CMD_GET, chunks=1, cur=1))

    async def scenario() -> "tuple[bool, Any]":
        first = await pair.initiator.uart_set(1, b"x")  # sees the GET instead of its ACK
        # The aborted transfer left its own chunk 1 sitting in the responder's receive path, so
        # the responder quiesces too before the link is retried - which is exactly what both sides
        # doing a quiesce-and-resync means.
        await pair.responder.clear()
        listener = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")  # the link works again afterwards
        await asyncio.sleep_ms(5)
        listener.cancel()
        return first, recovered

    first, recovered = run(scenario(), limit=25)
    assert first is False
    assert recovered is True
    counts = run(pair.initiator.get_error_counter())
    assert counts["UART_A"]["ErrCount"] > 0  # logged distinctly rather than silently absorbed


# ---------------------------------------------------------------------------
# H1.4/H1.5 - the frame/field sweep, with wire-log assertions
# ---------------------------------------------------------------------------


def test_the_command_field_sweep_accepts_only_the_expected_command() -> None:
    # Swept against one fixed expectation, which is what a real read site has: only the exact
    # command it is waiting for may pass. A bitmask test would let 0x06 and 0x03 through here.
    pair = hazard_pair()
    for cmd in range(256):
        accepted = pair.responder._validate(bytearray(raw_frame(cmd=cmd)), _CMD_SET, 1, None, None) == 0
        assert accepted == (cmd == _CMD_SET), f"CMD 0x{cmd:02x} was not treated as expected"


def test_the_uid_field_sweep_stops_at_0xfe() -> None:
    pair = hazard_pair()
    for uid in range(256):
        accepted = pair.responder._validate(bytearray(raw_frame(uid=uid)), _CMD_SET, 1, None, None) == 0
        assert accepted == (uid <= 0xFE), f"UID 0x{uid:02x} was not treated as expected"


def test_the_first_chunk_size_field_sweep_accepts_only_one() -> None:
    pair = hazard_pair()
    for size in range(256):
        accepted = pair.responder._validate(bytearray(raw_frame(size=size)), _CMD_SET, 1, None, None) == 0
        assert accepted == (size == 1), f"first-chunk SIZE {size} was not treated as expected"


def test_the_middle_chunk_size_field_sweep_accepts_only_a_full_payload() -> None:
    pair = hazard_pair()
    for size in range(256):
        frame = bytearray(raw_frame(size=size, chunks=4, cur=2, uid=2))
        accepted = pair.responder._validate(frame, _CMD_SET, 2, 4, 2) == 0
        assert accepted == (size == _PAYLOAD), f"middle-chunk SIZE {size} was not treated as expected"


def test_the_chunks_field_sweep_rejects_zero_and_one_for_a_set() -> None:
    pair = hazard_pair()
    for chunks in range(256):
        accepted = pair.responder._validate(bytearray(raw_frame(chunks=chunks)), _CMD_SET, 1, None, None) == 0
        assert accepted == (chunks >= 2), f"CHUNKS {chunks} was not treated as expected"


def test_the_current_chunk_field_sweep_matches_only_the_expected_index() -> None:
    pair = hazard_pair()
    for cur in range(256):
        frame = bytearray(raw_frame(size=_PAYLOAD, chunks=4, cur=cur, uid=2))
        accepted = pair.responder._validate(frame, _CMD_SET, 2, 4, 2) == 0
        assert accepted == (cur == 2), f"CUR_CHUNK {cur} was not treated as expected"


def test_no_ack_is_emitted_for_any_rejected_frame() -> None:
    # H1.5: a rejected frame and a silently mishandled one both return failure, so the wire log is
    # what tells them apart. Withholding the ACK *is* the rejection signal in this protocol.
    rejected = (
        ("multi-bit CMD", raw_frame(cmd=0x06)),
        ("undefined CMD", raw_frame(cmd=0x00)),
        ("UID 0xFF", raw_frame(uid=0xFF)),
        ("first chunk SIZE 0", raw_frame(size=0)),
        ("first chunk SIZE 2", raw_frame(size=2)),
        ("SET with CHUNKS 1", raw_frame(chunks=1)),
        ("CHUNKS 0", raw_frame(chunks=0)),
        ("CUR_CHUNK past CHUNKS", raw_frame(chunks=2, cur=3)),
        ("SIZE past payload_size", raw_frame(size=_PAYLOAD + 1)),
    )
    for label, frame in rejected:
        pair = hazard_pair()
        result, emitted = listen_once(pair, frame)
        assert result.cmd_id is None, f"{label} was accepted"
        assert emitted == b"", f"{label} was acknowledged - rejection is signalled by silence"


def test_a_legal_frame_is_acknowledged_on_the_wire() -> None:
    # The positive control for the test above: without it, a responder that acknowledged nothing
    # at all would pass the whole rejection sweep. A two-frame SET is the right shape here - it
    # completes with no peer scheduled, whereas a GET's answer needs the initiator to acknowledge it.
    pair = hazard_pair()
    pair.fake_b.feed_rx(raw_frame(uid=1, cmd=_CMD_SET, size=1, chunks=2, cur=1, payload=b"\x07"))
    pair.fake_b.feed_rx(raw_frame(uid=2, cmd=_CMD_SET, size=3, chunks=2, cur=2, payload=b"abc"))
    result = run(pair.responder.uart_listen(), limit=10)
    pair.link.settle()
    emitted = pair.wire_from_responder()
    assert result.cmd_id == 0x07
    assert bytes(result.payload) == b"abc"
    assert len(emitted) == 2 * _FRAME  # one ACK per frame, the second deferred until the size check
    assert emitted[_CMD] == _CMD_ACK
    assert emitted[_UID] == 1
    assert emitted[_FRAME + _UID] == 2


def test_a_train_whose_chunks_total_changes_is_rejected_before_the_data_is_kept() -> None:
    # The multi-frame half of the sweep: the peer re-declares CHUNKS mid-train to truncate the
    # transfer, and the receiver must not report success on partial data.
    pair = hazard_pair()
    pair.fake_b.feed_rx(raw_frame(uid=1, cmd=_CMD_SET, size=1, chunks=3, cur=1))
    pair.fake_b.feed_rx(raw_frame(uid=2, cmd=_CMD_SET, size=_PAYLOAD, chunks=2, cur=2))
    result = run(pair.responder.uart_listen(), limit=10)
    assert result.cmd_id is None
    assert result.payload is None


def test_a_train_with_a_stale_data_chunk_uid_is_rejected() -> None:
    pair = hazard_pair()
    pair.fake_b.feed_rx(raw_frame(uid=10, cmd=_CMD_SET, size=1, chunks=3, cur=1))
    pair.fake_b.feed_rx(raw_frame(uid=99, cmd=_CMD_SET, size=_PAYLOAD, chunks=3, cur=2))  # not 11
    result = run(pair.responder.uart_listen(), limit=10)
    assert result.cmd_id is None


# ---------------------------------------------------------------------------
# Byte-level faults, recovered from
# ---------------------------------------------------------------------------


def test_a_corrupted_byte_stream_recovers_to_a_working_exchange() -> None:
    pair = hazard_pair()
    direction = pair.link.direction_from(pair.fake_a)
    direction.corrupt_indices = {1: 0xFF}  # rewrite the very first frame's CMD field

    async def scenario() -> "tuple[bool, bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        broken = await pair.initiator.uart_set(1, b"x")
        await asyncio.sleep_ms(5)
        listener.cancel()
        direction.corrupt_indices = {}
        healthy = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")
        await asyncio.sleep_ms(5)
        healthy.cancel()
        return broken, recovered

    broken, recovered = run(scenario(), limit=30)
    assert broken is False
    assert recovered is True


def test_a_truncated_frame_recovers_to_a_working_exchange() -> None:
    pair = hazard_pair()
    direction = pair.link.direction_from(pair.fake_a)
    direction.truncate_after = _FRAME // 2  # the first frame never completes

    async def scenario() -> "tuple[bool, bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        broken = await pair.initiator.uart_set(1, b"x")
        await asyncio.sleep_ms(5)
        listener.cancel()
        direction.truncate_after = None
        healthy = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")
        await asyncio.sleep_ms(5)
        healthy.cancel()
        return broken, recovered

    broken, recovered = run(scenario(), limit=30)
    assert broken is False
    assert recovered is True


def test_injected_noise_before_a_real_frame_is_recovered_from() -> None:
    pair = hazard_pair()
    pair.link.direction_from(pair.fake_a).noise_before_next = bytearray(b"\xde\xad\xbe\xef")

    async def scenario() -> "tuple[bool, bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        broken = await pair.initiator.uart_set(1, b"x")
        await asyncio.sleep_ms(5)
        listener.cancel()
        healthy = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")
        await asyncio.sleep_ms(5)
        healthy.cancel()
        return broken, recovered

    broken, recovered = run(scenario(), limit=30)
    assert broken is False  # the noise shifts the frame, so this one cannot succeed
    assert recovered is True  # but the link is usable again afterwards


def test_one_sided_silence_recovers_once_the_direction_returns() -> None:
    pair = hazard_pair()
    direction = pair.link.direction_from(pair.fake_b)
    direction.silent = True

    async def scenario() -> "tuple[bool, bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        broken = await pair.initiator.uart_set(1, b"x")
        await asyncio.sleep_ms(5)
        listener.cancel()
        direction.silent = False
        healthy = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")
        await asyncio.sleep_ms(5)
        healthy.cancel()
        return broken, recovered

    broken, recovered = run(scenario(), limit=30)
    assert broken is False
    assert recovered is True


def test_a_receive_overrun_recovers_to_a_working_exchange() -> None:
    pair = hazard_pair()
    direction = pair.link.direction_from(pair.fake_a)
    direction.capacity = _FRAME // 2  # the far buffer cannot hold one whole frame

    async def scenario() -> "tuple[bool, bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        broken = await pair.initiator.uart_set(1, b"x")
        await asyncio.sleep_ms(5)
        listener.cancel()
        direction.capacity = 512
        healthy = asyncio.create_task(pair.responder.uart_listen())
        recovered = await pair.initiator.uart_set(2, b"y")
        await asyncio.sleep_ms(5)
        healthy.cancel()
        return broken, recovered

    broken, recovered = run(scenario(), limit=30)
    assert broken is False
    assert direction.dropped_overrun > 0
    assert recovered is True


# ---- steady-state memory (audit pass) --------------------------------------------------------

_WARMUP = 20
_MEASURED = 100


def _scrub(pair: Pair) -> None:
    # The link's wire log is scaffolding a test reads back, not something the protocol retains.
    for direction in (pair.link.a_to_b, pair.link.b_to_a):
        direction.wire_log = bytearray()


async def _listen_rounds(pair: Pair, rounds: int) -> None:
    for _ in range(rounds):
        await pair.responder.uart_listen()


async def _measure_retention(pair: Pair) -> "tuple[int, float]":
    import gc

    listener = asyncio.create_task(_listen_rounds(pair, _WARMUP + _MEASURED + 1))
    payload = bytes(_PAYLOAD * 3)
    done = 0
    for _ in range(_WARMUP):  # every path taken at least once before the heap is sampled
        done += 1 if await pair.initiator.uart_set(1, payload) else 0
        _scrub(pair)
    gc.collect()
    before = gc.mem_alloc()
    for _ in range(_MEASURED):
        done += 1 if await pair.initiator.uart_set(1, payload) else 0
        _scrub(pair)
    gc.collect()
    grew = (gc.mem_alloc() - before) / _MEASURED
    listener.cancel()
    try:
        await listener
    except asyncio.CancelledError:  # expected; anything else is a real failure
        pass
    return done, grew


def test_a_long_run_of_transactions_retains_no_memory() -> None:
    # CLAUDE.md's memory-safety ladder at its most direct: a link running for weeks has no backstop
    # below the watchdog, so the steady state must not grow the heap. The fakes' recorders are muted
    # so the number is src/'s alone; hazard_pair() is built out here (its asyncio.run() cannot nest).
    pair = hazard_pair()
    for fake in (pair.fake_a, pair.fake_b):
        fake.log.append = lambda entry: None  # type: ignore[method-assign]
    completed, per_transaction = run(_measure_retention(pair), limit=120)
    assert completed == _WARMUP + _MEASURED, completed
    # A strict zero would be brittle against interpreter-internal caches; one frame of slack still
    # catches any real per-transaction retention long before it could matter on the target.
    assert per_transaction < _FRAME, f"{per_transaction} bytes retained per transaction"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
