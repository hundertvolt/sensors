"""Mock-tier comm-hazard suite for the UART protocol (requirement H1) - the UART-shaped analogue
of the standing bus-hazard rule. A link has exactly two participants, so multi-device interleaving
and an address sweep are replaced by same-instance concurrency, both-ends-transmitting, and a full frame-field sweep."""

import asyncio

from _uart_comm_harness import Pair, accept_set, echo_get, frames, run

from asy_uart_comm import ROLE_RESPONDER, UART_Comm
from crc_checks import CRC16

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from crc_checks import CRC_Base

    # None means "no CRC on the bus"; otherwise a zero-argument factory, called once per end.
    # A factory rather than an instance: CRC_Base carries incremental state, so the two ends must
    # never share one object. Not type[CRC_Base] - that would demand CRC_Base's own three-argument
    # constructor, which the concrete widths (CRC16 and friends) deliberately do not take.
    CrcMaker = Callable[[], CRC_Base] | None

    from machine import _LinkDirection as Direction  # one direction of the crossover link

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


# Standing rule (project owner, 2026-09-12): every test here runs both with and without a CRC.
# The deployed link runs CRC_Pass, so the no-CRC path is the one in the field - but a CRC changes
# which corruptions are detectable at all, and a suite that only ran one way would be pinning half
# the contract. CRC_MODES is what each test iterates; `crc()` builds a fresh instance per pair,
# since CRC_Base carries incremental state and two ends must not share one object.
CRC_MODES = (("nocrc", None), ("crc16", CRC16))


def wire_frame(crc: "CrcMaker") -> int:
    # What one frame actually occupies on the wire. The protocol's own frame is 5 + payload_size;
    # a CRC is appended below it, so every assertion that slices or counts whole frames has to add
    # its length or it is silently asserting the no-CRC layout in both modes.
    return _FRAME + (0 if crc is None else crc().length())


def timeout_for(crc: "CrcMaker") -> int:
    # A CRC yields once per byte (crc_checks.py's own loop), so the same wall-clock budget covers
    # far fewer bytes once other tasks share the loop - measured as transactions timing out at the
    # tier's deliberately tiny 30ms. The real link's own 1000ms has ample headroom; this keeps the
    # mock's speed while giving the CRC path the same *relative* margin.
    return _TIMEOUT_MS if crc is None else _TIMEOUT_MS * 8


def hazard_pair(crc: "CrcMaker" = None) -> Pair:
    maker = (lambda: None) if crc is None else crc
    pair = Pair(
        payload_size=_PAYLOAD, timeout=timeout_for(crc), get_callback=echo_get(b"v"), set_callback=accept_set(),
        crc_a=maker(), crc_b=maker(),
    )
    assert run(pair.setup()) is True
    return pair


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
    result = run(pair.responder.uart_listen(), limit=10)
    pair.link.settle()
    return result, pair.wire_from_responder()


# ---------------------------------------------------------------------------
# H1.1 - same-instance concurrency
# ---------------------------------------------------------------------------


def _check_two_tasks_initiating_at_once_never_interleave_frames(crc: "CrcMaker") -> None:
    # Either the session lock serializes them or the role/re-entrancy gate refuses one; what must
    # never happen is two transactions interleaving frames on the wire.
    pair = hazard_pair(crc)

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
    assert len(emitted) % wire_frame(crc) == 0  # only whole frames reached the wire
    for frame in frames(emitted, wire_frame(crc)):
        assert frame[_CUR] <= frame[_CHUNKS]  # and each is internally consistent


def _check_a_second_call_during_a_transaction_is_refused_with_a_sentinel(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)

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


def _check_clear_racing_a_transaction_leaves_it_completed_or_cleanly_failed(crc: "CrcMaker") -> None:
    # The one outcome that must not occur is a silently half-completed transfer: whatever clear()
    # interrupts, the caller is told the truth about it.
    pair = hazard_pair(crc)

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
    assert len(emitted) % wire_frame(crc) == 0  # never a partial frame left on the wire by the interruption


def _check_clear_terminates_even_while_a_listener_is_parked_forever(crc: "CrcMaker") -> None:
    # The unbounded listen wait holds the bus lock, so this is the only safe interruption - and it
    # must be bounded, which the limit= on run() is what proves.
    pair = hazard_pair(crc)

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


def _check_no_ack_is_emitted_for_any_rejected_frame(crc: "CrcMaker") -> None:
    # H1.5: a rejected frame and a silently mishandled one both return failure, so the wire log is
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
    result = run(pair.responder.uart_listen(), limit=10)
    pair.link.settle()
    emitted = pair.wire_from_responder()
    assert result.cmd_id == 0x07
    assert bytes(result.payload) == b"abc"
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
    result = run(pair.responder.uart_listen(), limit=10)
    assert result.cmd_id is None
    assert result.payload is None


def _check_a_train_with_a_stale_data_chunk_uid_is_rejected(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    pair.fake_b.feed_rx(raw_frame(uid=10, cmd=_CMD_SET, size=1, chunks=3, cur=1, crc=crc))
    pair.fake_b.feed_rx(raw_frame(uid=99, cmd=_CMD_SET, size=_PAYLOAD, chunks=3, cur=2, crc=crc))  # not 11
    result = run(pair.responder.uart_listen(), limit=10)
    assert result.cmd_id is None


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


def _check_a_truncated_frame_recovers_to_a_working_exchange(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    direction = pair.link.direction_from(pair.fake_a)
    direction.truncate_after = wire_frame(crc) // 2  # the first frame never completes

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


def _check_injected_noise_before_a_real_frame_is_recovered_from(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
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


def _check_one_sided_silence_recovers_once_the_direction_returns(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
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


def _check_a_receive_overrun_recovers_to_a_working_exchange(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    direction = pair.link.direction_from(pair.fake_a)
    direction.capacity = wire_frame(crc) // 2  # the far buffer cannot hold one whole frame

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


async def _measure_retention(pair: Pair) -> "tuple[int, float]":
    import gc

    # Three rounds per transaction, not one: a listen round is not always consumed by a completed
    # transaction, and a budget of exactly n+1 starves the last few transactions rather than
    # measuring them. Verified with the budget raised: 120/120 complete with zero errors logged in
    # both CRC modes, so the shortfall was the harness's, not the protocol's.
    listener = asyncio.create_task(_listen_rounds(pair, (_WARMUP + _MEASURED) * 3))
    payload = bytes(_PAYLOAD * 3)
    done = 0
    for _ in range(_WARMUP):  # every path taken at least once before the heap is sampled
        done += 1 if await pair.initiator.uart_set(1, payload) else 0
        _scrub(pair)
    # An ambient control first, yield-matched. Every test_*.py file runs as one process with one
    # task queue and MicroPython's asyncio has no parent/child tracking, so listeners parked by
    # earlier tests keep allocating whenever this one yields. A CRC yields once per byte, so a
    # CRC'd transaction hands those leftovers ~200x more wakeups than an idle sleep does - which is
    # why an idle control still charged 118 bytes/transaction to the protocol. This control repeats
    # the same CRC work over the same frame sizes, with no link involved, so what it measures is
    # exactly the scheduling churn a transaction provokes and nothing the protocol itself retains.
    gc.collect()
    idle_before = gc.mem_alloc()
    for _ in range(_MEASURED):
        await _yield_like_one_transaction(pair)
    gc.collect()
    ambient = gc.mem_alloc() - idle_before

    gc.collect()
    before = gc.mem_alloc()
    for _ in range(_MEASURED):
        done += 1 if await pair.initiator.uart_set(1, payload) else 0
        _scrub(pair)
    gc.collect()
    grew = max(0, (gc.mem_alloc() - before) - ambient) / _MEASURED
    listener.cancel()
    try:
        await listener
    except asyncio.CancelledError:  # expected; anything else is a real failure
        pass
    return done, grew


def _check_a_long_run_of_transactions_retains_no_memory(crc: "CrcMaker") -> None:
    # CLAUDE.md's memory-safety ladder at its most direct: a link running for weeks has no backstop
    # below the watchdog, so the steady state must not grow the heap. The fakes' recorders are muted
    # so the number is src/'s alone; hazard_pair(crc) is built out here (its asyncio.run() cannot nest).
    pair = hazard_pair(crc)
    for fake in (pair.fake_a, pair.fake_b):
        fake.log.append = lambda entry: None  # type: ignore[method-assign]
    completed, per_transaction = run(_measure_retention(pair), limit=120)
    assert completed == _WARMUP + _MEASURED, completed
    # A strict zero would be brittle against interpreter-internal caches; one frame of slack still
    # catches any real per-transaction retention long before it could matter on the target.
    assert per_transaction < wire_frame(crc), f"{per_transaction} bytes retained per transaction"


# ---------------------------------------------------------------------------
# Which error is reported, not merely that one was. Every test above this point asserts ErrCount;
# none asserts ErrNum, so a fault reporting the wrong code passes the whole suite. The catalog is
# the module's only diagnostic surface (SPECIFICATION.md Part J, errno 10-34), and on a link with
# no CRC it is the only way a bench session tells one failure from another.
# ---------------------------------------------------------------------------

_ERR_NO_ACK = 20
_ERR_READ_TIMEOUT = 22
_ERR_PAYLOAD_TOO_LARGE = 23
_ERR_SIZE_MISMATCH = 25
_ERR_REENTRANT = 27
_ERR_PEER_INITIATED = 31
_ERR_BAD_ARG = 34


def errnos(comm: UART_Comm) -> "list[int]":
    # Errors only. ErrNum holds errnos and wrnnos in one ring and they share the number space -
    # wrnno 10 is a resync, errno 10 is a bad payload_size - so ErrType is what tells them apart.
    # Every fault also resyncs, so the newest entry is almost always the resync warning.
    # Indexed rather than zip()ed: MicroPython's zip() has no strict= parameter to satisfy B905.
    entry = run(comm.get_error_counter())[comm.name]
    nums, kinds = entry["ErrNum"], entry["ErrType"]
    return [nums[i] for i in range(len(nums)) if kinds[i] == "E"]


def last_errno(comm: UART_Comm) -> int:
    codes = errnos(comm)
    return codes[-1] if codes else 0


def _check_a_silent_peer_reports_no_ack_not_a_generic_failure(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    pair.link.direction_from(pair.fake_b).silent = True
    assert run(pair.with_listener(pair.initiator.uart_set(0x02, b"x"), rounds=0), limit=10) is False
    assert last_errno(pair.initiator) == _ERR_NO_ACK, f"a silent peer reported errno {last_errno(pair.initiator)}"


def _check_a_listener_whose_frame_never_arrives_reports_a_read_timeout(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)

    async def scenario() -> None:
        await pair.responder.uart_listen()

    # Nothing is fed, and clear() cancels the parked read - the listener's own documented unstick.
    async def drive() -> None:
        listener = asyncio.create_task(scenario())
        await asyncio.sleep_ms(5)
        await pair.responder.clear()
        await asyncio.wait_for(listener, 5)

    run(drive(), limit=10)
    assert last_errno(pair.responder) == _ERR_READ_TIMEOUT


def _check_a_reentrant_call_reports_its_own_errno(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    pair.link.direction_from(pair.fake_b).silent = True

    async def scenario() -> None:
        first = asyncio.create_task(pair.initiator.uart_get(0x01))
        await asyncio.sleep_ms(2)
        assert await pair.initiator.uart_get(0x01) is None  # refused while the first holds the link
        await asyncio.wait_for(first, 5)

    run(scenario(), limit=20)
    # Read outside the coroutine: errnos() drives its own asyncio.run(), and nesting one inside a
    # running loop segfaults this interpreter rather than raising (CLAUDE.md's known segfault).
    assert _ERR_REENTRANT in errnos(pair.initiator), f"got {errnos(pair.initiator)}"


def _check_a_bad_argument_reports_errno_34_before_anything_reaches_the_wire(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    assert run(pair.initiator.uart_set(0x101, b"x"), limit=5) is False  # command id past one byte
    assert last_errno(pair.initiator) == _ERR_BAD_ARG
    assert pair.wire_from_initiator() == b"", "a refused argument still put bytes on the wire"


def _check_an_oversized_payload_reports_payload_too_large(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    # _CHUNKS_MAX is 255, so 254 data chunks is the ceiling; one byte past it must be refused.
    too_big = bytes(_PAYLOAD * 254 + 1)
    assert run(pair.initiator.uart_set(0x02, too_big), limit=20) is False
    assert last_errno(pair.initiator) == _ERR_PAYLOAD_TOO_LARGE
    assert pair.wire_from_initiator() == b"", "an oversized payload was partially sent before being refused"


def _check_a_peer_initiating_mid_transaction_reports_peer_initiated(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    # A data frame where an ACK is due: the one out-of-contract case the protocol names separately,
    # because there is no arbitration and it is the peer's violation rather than link noise.
    pair.fake_a.feed_rx(raw_frame(cmd=_CMD_GET, size=1, chunks=2, cur=1, crc=crc))
    assert run(pair.initiator.uart_get(0x01), limit=10) is None
    assert _ERR_PEER_INITIATED in errnos(pair.initiator), f"got {errnos(pair.initiator)}"


def _check_a_size_mismatch_against_an_expected_size_reports_it_distinctly(crc: "CrcMaker") -> None:
    pair = Pair(payload_size=_PAYLOAD, timeout=_TIMEOUT_MS, get_callback=echo_get(b"vv"), set_callback=accept_set())
    assert run(pair.setup()) is True
    # The answer is 2 bytes; the caller declared it expects 5. A wrong-length answer must be named,
    # not silently truncated or padded into something plausible.
    assert run(pair.with_listener(pair.initiator.uart_get(0x01, exp_size=5)), limit=10) is None
    assert last_errno(pair.initiator) == _ERR_SIZE_MISMATCH


# ---------------------------------------------------------------------------
# The three link fault knobs no test exercised: dropped bytes, duplicated bytes and delayed
# delivery. On rp2 a framing/parity/overrun fault never raises (C.3.2), so every electrical fault
# reaches this layer as exactly one of these three stream shapes - which makes them the whole
# observable surface of the physical layer, not exotic extras.
# ---------------------------------------------------------------------------


def _check_a_dropped_byte_mid_frame_recovers_to_a_working_exchange(crc: "CrcMaker") -> None:
    # A byte lost to a framing error or a full FIFO shortens the frame: the read cannot complete,
    # and recovery has to come from the timeout plus resync, not from the frame itself.
    pair = hazard_pair(crc)
    direction = pair.link.direction_from(pair.fake_b)
    direction.drop_indices = {3}  # inside the first answer frame's header
    assert run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=20) is None
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] > 0

    direction.drop_indices = set()
    run(pair.initiator.clear(), limit=10)
    run(pair.responder.clear(), limit=10)
    answer = run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=20)
    assert answer is not None and bytes(answer) == b"v", "the link never recovered after a dropped byte"


def _check_duplicated_bytes_on_the_wire_recover_to_a_working_exchange(crc: "CrcMaker") -> None:
    # A repeated byte is what a stuck line or a re-sent buffer looks like from here: it desynchronises
    # the fixed-size framing, so the next frame reads as garbage until a resync realigns it.
    pair = hazard_pair(crc)
    direction = pair.link.direction_from(pair.fake_b)
    direction.duplicate_next = 3
    run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=20)

    direction.duplicate_next = 0
    run(pair.initiator.clear(), limit=10)
    run(pair.responder.clear(), limit=10)
    answer = run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=20)
    assert answer is not None and bytes(answer) == b"v", "the link never recovered after duplicated bytes"


def _check_a_frame_delivered_in_two_fragments_still_assembles(crc: "CrcMaker") -> None:
    # The ordinary case at a real baud rate: a frame does not arrive atomically. The read loop must
    # keep waiting across the gap rather than treat a partial frame as a fault - this is the one of
    # the three that must NOT produce an error.
    pair = hazard_pair(crc)
    direction = pair.link.direction_from(pair.fake_b)

    async def scenario() -> "bytearray | None":
        listener = asyncio.create_task(pair.responder.uart_listen())
        direction.delay = True
        work = asyncio.create_task(pair.initiator.uart_get(0x01))
        await asyncio.sleep_ms(3)
        direction.delay = False
        pair.link.release_delayed()  # the held bytes land in one go, mid-transaction
        answer = await asyncio.wait_for(work, 5)
        await asyncio.wait_for(listener, 5)
        return answer

    answer = run(scenario(), limit=20)
    assert answer is not None and bytes(answer) == b"v"
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] == 0, (
        "a fragmented but complete frame was treated as a fault"
    )


# ---------------------------------------------------------------------------
# The integrity envelope. The deployed link runs with CRC_Pass - no CRC at all - so structural
# field validation is the *only* check (SPECIFICATION.md Part J). These tests pin exactly where
# that boundary falls, because "corruption is handled" is true of the header and false of the
# payload, and a bench session needs to know which.
# ---------------------------------------------------------------------------


def _check_a_corrupted_header_byte_is_caught_by_structural_validation(crc: "CrcMaker") -> None:
    # The CMD field: a flipped bit here makes the frame structurally impossible, and the receiver
    # rejects it without needing a CRC.
    pair = hazard_pair(crc)
    pair.link.direction_from(pair.fake_b).corrupt_indices = {_CMD: 0xFF}
    assert run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=20) is None
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] > 0


def _answer_payload_offset(marker: int = ord("v"), crc: "CrcMaker" = None) -> int:
    # corrupt_indices addresses a STREAM offset, not a frame offset, and the responder's stream
    # opens with the ACK to the GET before the answer train - so the payload byte's position is
    # found from a clean run rather than assumed.
    probe = hazard_pair(crc)
    assert run(probe.with_listener(probe.initiator.uart_get(0x01)), limit=20) is not None
    wire = probe.wire_from_responder()
    offset = wire.find(bytes([marker]), wire_frame(crc))  # past the ACK frame
    assert offset > 0, f"no answer payload byte found in the responder's wire log: {wire!r}"
    return offset


def _check_a_corrupted_payload_byte_is_delivered_undetected_without_a_crc(crc: "CrcMaker") -> None:
    # The other half of the same boundary, and the uncomfortable one: with no CRC configured, a bit
    # flip inside the payload passes every structural check and reaches the caller as good data.
    # This is a documented property of the deployed configuration, not a defect to fix here - it is
    # pinned so that enabling a CRC (the test below) is visibly the thing that changes it.
    offset = _answer_payload_offset(crc=crc)
    pair = hazard_pair(crc)
    pair.link.direction_from(pair.fake_b).corrupt_indices = {offset: 0xFF}
    answer = run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=20)
    assert answer is not None, "the frame was rejected - then this test no longer pins what it claims"
    assert bytes(answer) == bytes([ord("v") ^ 0xFF]), f"expected a corrupted byte, got {bytes(answer)!r}"
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] == 0, (
        "a payload corruption was somehow counted - the no-CRC envelope has changed"
    )


def _check_with_a_crc_configured_the_same_payload_corruption_is_caught(crc: "CrcMaker") -> None:
    # Same injection, CRC16 on the bus objects: now the frame fails verification and is rejected.
    # This is what makes the test above a statement about configuration rather than about the
    # protocol being unable to detect corruption at all.
    pair = Pair(
        payload_size=_PAYLOAD, timeout=_TIMEOUT_MS, get_callback=echo_get(b"v"), set_callback=accept_set(),
        crc_a=CRC16(), crc_b=CRC16(),
    )
    assert run(pair.setup()) is True
    # A byte inside the answer train, past the ACK frame. Which byte does not matter here and is
    # deliberately not pinned: the claim is that with a CRC every corruption in the frame is caught,
    # whereas the test above shows a payload byte specifically is not caught without one.
    pair.link.direction_from(pair.fake_b).corrupt_indices = {wire_frame(crc) + 7: 0xFF}
    assert run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=20) is None, (
        "a CRC-protected corruption was still delivered"
    )
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] > 0


def _check_a_receive_buffer_smaller_than_a_frame_is_refused_at_construction(crc: "CrcMaker") -> None:
    # The silent-tail-loss failure: a frame that does not fit rxbuf loses its end, and the result is
    # indistinguishable from a link fault. The module refuses the configuration instead (B17).
    from asy_uart_comm import ROLE_INITIATOR, UART_Comm
    from asy_uart_driver import UART as Driver
    too_small = Driver(0, tx_pin=0, rx_pin=1, rxbuf=32, txbuf=256, poll_wait_ms=1)
    comm = UART_Comm(too_small, ROLE_INITIATOR, payload_size=255, timeout=_TIMEOUT_MS, name="UART_TINY")
    assert comm._init_errno != 0, "an rxbuf below one whole frame was accepted"
    assert run(comm.setup()) is False, "a refused construction still opened its readiness gate"



# ---------------------------------------------------------------------------
# The mismatched-peer signature. The protocol's parameters are fixed by out-of-band agreement and
# never negotiated (SPECIFICATION.md Part J), so a pair configured differently is diagnosed rather
# than recovered. errno 32 is that diagnosis - bytes keep arriving and not one frame ever
# validates - and it is the signature the C-port reconciliation will most likely meet first
# (UART_C_PORT_CHANGELOG.md D2.5). Until now it was only ever reached by setting _blind_resyncs by
# hand, never by an actually mismatched peer.
# ---------------------------------------------------------------------------

_ERR_LINK_UNINTELLIGIBLE = 32


def _mismatched_responder(pair: Pair, payload_size: int) -> UART_Comm:
    # Same link, same wire, a responder that disagrees about the frame size. Every frame the
    # initiator sends is then the wrong length for it, which is exactly what a wrong payload_size,
    # a wrong baud rate or a different CRC algorithm all look like from the receiving end.
    return UART_Comm(
        pair.driver_b, ROLE_RESPONDER, payload_size=payload_size, timeout=pair.responder.timeout,
        get_callback=echo_get(b"v"), set_callback=accept_set(), name="UART_MISMATCH",
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
                await asyncio.wait_for(listener, 5)
            except asyncio.TimeoutError:
                listener.cancel()

    # The one configuration error the design cannot self-heal: it must fail, not deliver a
    # wrong-length payload as though it were right.
    assert run(scenario(), limit=60) is False
    assert errnos(pair.initiator), "a payload_size mismatch produced no logged error at all"


def _check_a_peer_that_never_produces_a_valid_frame_is_diagnosed(crc: "CrcMaker") -> None:
    pair = hazard_pair(crc)
    responder = _mismatched_responder(pair, _PAYLOAD + 8)
    assert run(responder.setup()) is True

    async def scenario() -> None:
        # Repeated attempts: the diagnostic deliberately waits for a streak before firing, so one
        # failed exchange must NOT trip it and several in a row must.
        for _ in range(4):
            listener = asyncio.create_task(responder.uart_listen())
            await pair.initiator.uart_set(0x02, b"nonsense")
            await responder.clear()
            try:
                await asyncio.wait_for(listener, 5)
            except asyncio.TimeoutError:
                listener.cancel()

    run(scenario(), limit=120)
    # KNOWN DEFECT, reported to the project owner rather than fixed here (CLAUDE.md's
    # flag-don't-silently-change rule): errno 32 does NOT fire in the scenario it exists for.
    # _resync() gates the diagnostic on `drained and self._valid_frames == 0`, but
    # readinto_until_complete() has already consumed the short frame's bytes while waiting for a
    # full-length one and discarded them on timeout - so _drain() finds an empty line and `drained`
    # is 0 on every resync (measured: (0, 0, 0) at each of five resyncs). The mismatched peer is
    # therefore reported only as a generic read timeout, errno 22.
    # This assertion pins the defect, not the desired behaviour: when the gate is fixed it flips,
    # which is the point - nothing about the current behaviour is silently blessed.
    codes = errnos(responder)
    assert _ERR_READ_TIMEOUT in codes, f"expected the generic timeout this currently reports: {codes}"
    assert _ERR_LINK_UNINTELLIGIBLE not in codes, (
        "errno 32 now fires against a mismatched peer - the defect is fixed, so invert this test "
        "to assert it is present and drop this comment"
    )


def _check_a_break_like_run_of_nulls_recovers_to_a_working_exchange(crc: "CrcMaker") -> None:
    # A line break, a stuck-low driver and a disconnected floating RX all reach this layer the same
    # way: a run of 0x00 bytes. rp2 never raises for it (C.3.2), so the only correct behaviour is to
    # treat it as garbage, resync past it, and keep working.
    pair = hazard_pair(crc)
    pair.fake_a.feed_rx(bytes(wire_frame(crc) * 3))
    run(pair.initiator.clear(), limit=20)
    answer = run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=30)
    assert answer is not None and bytes(answer) == b"v", "the link never recovered from a break-like null run"


# ---------------------------------------------------------------------------
# Recombined failure modes. Every fault above is injected alone, but a real degraded link does not
# fail one way at a time - a marginal connector drops bytes AND corrupts them AND stalls. These
# apply faults in pairs, because the interesting question is whether two recovery paths running
# over each other still converge, not whether each works in isolation.
# ---------------------------------------------------------------------------


async def _exchange_quietly(pair: Pair) -> "bytearray | None":
    # One GET with its listener, never raising out whatever the faults do to it.
    listener = asyncio.create_task(pair.responder.uart_listen())
    try:
        return await pair.initiator.uart_get(0x01)
    finally:
        await pair.responder.clear()
        try:
            await asyncio.wait_for(listener, 5)
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

    run(under_fault(), limit=120)

    for direction in (to_initiator, to_responder):
        direction.silent = False
        direction.drop_indices = set()
        direction.corrupt_indices = {}
        direction.truncate_after = None
        direction.duplicate_next = 0
        direction.capacity = 4096
    run(pair.initiator.clear(), limit=30)
    run(pair.responder.clear(), limit=30)

    recovered = False
    for _ in range(4):  # several attempts: a resync hold-off may still be running down
        answer = run(_exchange_quietly(pair), limit=60)
        if answer is not None and bytes(answer) == b"v":
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
    run(_exchange_quietly(pair), limit=60)
    to_initiator.silent = False
    to_initiator.corrupt_indices = {4: 0xFF}
    run(_exchange_quietly(pair), limit=60)
    to_initiator.corrupt_indices = {}
    run(pair.initiator.clear(), limit=30)
    run(pair.responder.clear(), limit=30)

    recovered = False
    for _ in range(4):
        answer = run(_exchange_quietly(pair), limit=60)
        if answer is not None and bytes(answer) == b"v":
            recovered = True
            break
    assert recovered, "the link never converged after silence, then corruption, then a clean line"


# ---------------------------------------------------------------------------
# Hammering the link on its own: sustained back-to-back transactions at the tier's maximum rate,
# with the heap watched throughout. A link deployed for weeks has no backstop below the watchdog
# (CLAUDE.md's memory-safety ladder), so "works once" and "works for an hour" are different claims.
# ---------------------------------------------------------------------------

_HAMMER_ROUNDS = 150


def _hammer_clean(crc: "CrcMaker") -> None:
    import gc

    pair = hazard_pair(crc)
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
            if i == _HAMMER_ROUNDS // 3:  # sample once the steady state is genuinely reached
                gc.collect()
                mid[0] = gc.mem_alloc()
        gc.collect()
        grew = gc.mem_alloc() - mid[0]
        listener.cancel()
        try:
            await listener
        except asyncio.CancelledError:  # expected
            pass
        return ok, grew

    mid = [0]
    ok, grew = run(hammer(), limit=300)
    assert ok == _HAMMER_ROUNDS, f"only {ok}/{_HAMMER_ROUNDS} hammered transactions completed"
    assert not errnos(pair.initiator), f"a clean link logged errors under sustained load: {errnos(pair.initiator)}"
    # Two thirds of the run after the sample point, so any per-transaction retention would show as
    # a multiple of a frame rather than as interpreter noise.
    assert grew < wire_frame(crc) * 4, f"{grew} bytes retained across {_HAMMER_ROUNDS} hammered transactions"


def _hammer_faulted(crc: "CrcMaker") -> None:
    # The same hammer with a fault running underneath it: the failure path is the one that
    # allocates hardest (resync, drain, backoff), so this is where an unbounded retry or a leak in
    # the recovery path would show.
    import gc

    pair = hazard_pair(crc)
    for fake in (pair.fake_a, pair.fake_b):
        fake.log.append = lambda entry: None  # type: ignore[method-assign]
    to_initiator = pair.link.direction_from(pair.fake_b)
    to_initiator.corrupt_indices = {2: 0xFF}

    async def burst(rounds: int) -> None:
        for _ in range(rounds):
            await pair.initiator.uart_get(0x01)  # each one fails; none may raise
            _scrub(pair)

    async def hammer() -> int:
        listener = asyncio.create_task(_listen_rounds(pair, 240))
        # The first fault allocates a fixed ~3.4kB - the log history's buffers and the resync
        # scratch, built once and reused. Measured constant at 10, 30, 60 and 120 failures, so it
        # is one-time cost rather than per-failure retention. The first burst absorbs it; only the
        # second is measured, which is what makes this a leak test rather than a startup test.
        await burst(30)
        gc.collect()
        before[0] = gc.mem_alloc()
        await burst(30)
        gc.collect()
        grew = gc.mem_alloc() - before[0]
        listener.cancel()
        try:
            await listener
        except asyncio.CancelledError:  # expected
            pass
        return grew

    before = [0]
    grew = run(hammer(), limit=300)
    assert grew < wire_frame(crc) * 2, f"{grew} bytes retained across a second 30-failure burst"

    to_initiator.corrupt_indices = {}
    run(pair.initiator.clear(), limit=30)
    run(pair.responder.clear(), limit=30)
    recovered = False
    for _ in range(4):
        answer = run(_exchange_quietly(pair), limit=60)
        if answer is not None and bytes(answer) == b"v":
            recovered = True
            break
    assert recovered, "a hammered, faulted link never recovered once the fault was cleared"


# ---------------------------------------------------------------------------
# Second-pass gaps: the three cases the systematic sweep over the general UART failure taxonomy
# found uncovered. Each is a field scenario rather than a theoretical one.
# ---------------------------------------------------------------------------


def _clean_ack_bytes(crc: "CrcMaker") -> int:
    # Bytes the responder puts on the wire for one clean 8-byte SET, so a test can truncate exactly
    # one frame short of the end instead of guessing the ACK count.
    probe = hazard_pair(crc)
    assert run(probe.with_listener(probe.initiator.uart_set(0x02, b"acted-on")), limit=20) is True
    total = len(probe.wire_from_responder())
    assert total >= wire_frame(crc) * 2, f"expected at least two ACK frames, saw {total} bytes"
    return total


def _check_a_lost_final_ack_is_reported_as_failure_though_the_peer_acted(crc: "CrcMaker") -> None:
    # The protocol's at-least-once seam, and the one a caller most needs to know about. The final
    # ACK is deferred until after the responder's total-size check (F2.4), so if it is lost the
    # responder has ALREADY accepted and delivered the whole train while the initiator reports
    # failure. A caller that retries on False must therefore tolerate the peer seeing it twice.
    # SPECIFICATION.md Part J states this is folded into failure; nothing pinned it until now.
    pair = hazard_pair(crc)
    delivered: list[bytes] = []
    # The payload is read off uart_listen()'s own ListenResult, not a message_callback: that
    # callback is dispatched by the owned _listen_loop(), which this test does not run.
    responder = UART_Comm(
        pair.driver_b, ROLE_RESPONDER, payload_size=_PAYLOAD, timeout=pair.responder.timeout,
        get_callback=echo_get(b"v"), set_callback=accept_set(), name="UART_LOSTACK",
    )
    assert run(responder.setup()) is True
    to_initiator = pair.link.direction_from(pair.fake_b)
    # Measured out here, never inside the coroutine below: _clean_ack_bytes() drives its own
    # asyncio.run(), and nesting one inside a running loop segfaults this interpreter rather than
    # raising (CLAUDE.md's known segfault cause).
    cut_after = _clean_ack_bytes(crc) - wire_frame(crc)

    async def scenario() -> bool:
        listener = asyncio.create_task(responder.uart_listen())
        # Drop the responder's last outgoing frame - its final ACK - and nothing else.
        to_initiator.truncate_after = cut_after
        try:
            return await pair.initiator.uart_set(0x02, b"acted-on")
        finally:
            await responder.clear()
            try:
                result = await asyncio.wait_for(listener, 5)
                if result.payload is not None:
                    delivered.append(bytes(result.payload))
            except asyncio.TimeoutError:
                listener.cancel()

    result = run(scenario(), limit=60)
    assert result is False, "a lost final ACK was reported as success"
    assert errnos(pair.initiator), "a lost final ACK produced no logged error"
    # The asymmetry itself: the responder did the work the initiator was told failed.
    assert delivered == [b"acted-on"], f"the responder did not actually receive the train: {delivered!r}"


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
                await asyncio.wait_for(listener, 5)
            except asyncio.TimeoutError:
                listener.cancel()

    run(cut_off_mid_train(), limit=60)

    # The peer returns as a brand-new instance: no UID history, no half-read frame, nothing.
    to_initiator.silent = False
    reborn = UART_Comm(
        pair.driver_b, ROLE_RESPONDER, payload_size=_PAYLOAD, timeout=pair.responder.timeout,
        get_callback=echo_get(b"v"), set_callback=accept_set(), name="UART_REBORN",
    )
    assert run(reborn.setup()) is True  # setup() drains whatever the old instance left behind
    run(pair.initiator.clear(), limit=30)

    recovered = False
    for _ in range(4):
        listener = asyncio.create_task(reborn.uart_listen())

        async def one(listener: "asyncio.Task[Any]" = listener) -> "bytearray | None":
            try:
                return await pair.initiator.uart_get(0x01)
            finally:
                await reborn.clear()
                try:
                    await asyncio.wait_for(listener, 5)
                except asyncio.TimeoutError:
                    listener.cancel()

        answer = run(one(), limit=60)
        if answer is not None and bytes(answer) == b"v":
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
    run(_exchange_quietly(pair), limit=60)

    to_initiator.truncate_after = None
    # Reconnection lands mid-frame: a partial frame's worth of bytes with no header at the front.
    pair.fake_a.feed_rx(bytes(range(wire_frame(crc) // 2)))
    run(pair.initiator.clear(), limit=30)

    recovered = False
    for _ in range(4):
        answer = run(_exchange_quietly(pair), limit=60)
        if answer is not None and bytes(answer) == b"v":
            recovered = True
            break
    assert recovered, "the link never recovered from a disconnect/reconnect mid-frame"


def _check_the_crc_appears_on_the_wire_big_endian_after_the_payload(crc: "CrcMaker") -> None:
    # Byte order is part of the wire contract, not an implementation detail: the C peer's own CRC is
    # appended in the platform's NATIVE order and is deliberately not wire-compatible with this one
    # (SPECIFICATION.md Part J, UART_C_PORT_CHANGELOG.md A7). If this silently changed, two
    # implementations would disagree in a way that looks exactly like a dead link.
    if crc is None:
        return  # nothing is appended without a CRC; the companion mode covers the other half
    pair = hazard_pair(crc)
    assert run(pair.with_listener(pair.initiator.uart_get(0x01)), limit=20) is not None
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


# CLAUDE.md's standing rule for any new stress/hammer test: it must pass under gc.threshold(-1),
# MicroPython's own real default, BEFORE it is ever run under the project's chosen 32768. A
# threshold is defense in depth on top of an already-safe design, never the fix for one that still
# needs a big contiguous allocation - so a hammer that only passes with proactive collection
# enabled is hiding exactly the defect the rule exists to surface. Both are run here, -1 first.
# gc.threshold() is process-global, so each body saves and restores it (the same shape
# test_asy_webserver_service.py's own H.3 pair uses).
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


# Every _check_* above takes the CRC mode and is registered here once per mode, so microtest
# reports "..._nocrc" and "..._crc16" separately and a failure names which configuration broke.
# Two checks are about one configuration by construction, not by omission: one pins that a payload
# corruption is undetectable WITHOUT a CRC, the other that it is caught WITH one. Running either in
# the opposite mode would assert the opposite of what it says.
_MODE_SPECIFIC = {
    "a_corrupted_payload_byte_is_delivered_undetected_without_a_crc": "nocrc",
    "with_a_crc_configured_the_same_payload_corruption_is_caught": "crc16",
}


def _register_both_crc_modes() -> None:
    for label, crc in CRC_MODES:
        for name, check in list(globals().items()):
            if not name.startswith("_check_"):
                continue
            stem = name[len("_check_") :]
            if _MODE_SPECIFIC.get(stem, label) != label:
                continue
            globals()[f"test_{stem}_{label}"] = _bind(check, crc)


def _bind(check: "Callable[[CrcMaker], None]", crc: "CrcMaker") -> "Callable[[], None]":
    def run_one() -> None:
        check(crc)

    return run_one


_register_both_crc_modes()


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
