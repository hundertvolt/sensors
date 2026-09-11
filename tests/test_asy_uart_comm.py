"""Unit tests for src/asy_uart_comm.py, phases C-F of UART_PROMOTION_REQUIREMENTS.md: construction
and readiness, frame build/validate/ACK, the acknowledged exchange and its recovery, and the
transaction layer. The comm-hazard tier lives in test_uart_comm_hazard.py (H1)."""

import asyncio

from _uart_comm_harness import PAYLOAD_SIZE, TIMEOUT_MS, Pair, accept_set, build_pair, echo_get, frames, run
from machine import LinkPoller

from asy_uart_comm import (
    ROLE_INITIATOR,
    ROLE_RESPONDER,
    ListenResult,
    UART_Comm,
)
from asy_uart_driver import UART

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any

_SRC = "src/asy_uart_comm.py"

_CMD_ACK = 0x01
_CMD_GET = 0x02
_CMD_SET = 0x04
_UID = 0
_CMD = 1
_SIZE = 2
_CHUNKS = 3
_CUR = 4
_PAYLOAD = 5
_FRAME = 5 + PAYLOAD_SIZE


def make_comm(**kwargs: "Any") -> UART_Comm:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=1)
    driver.poller = LinkPoller(driver._uart)  # type: ignore[assignment,arg-type]
    params: dict[str, Any] = {"payload_size": PAYLOAD_SIZE, "timeout": TIMEOUT_MS}
    params.update(kwargs)
    role = params.pop("role", ROLE_INITIATOR)
    bus = params.pop("uart", driver)
    return UART_Comm(bus, role, **params)


# ===========================================================================
# Phase C - module foundation
# ===========================================================================
# C2 - constructor, parameter validation, readiness gate


def test_valid_construction_sets_the_gate_only_after_setup() -> None:
    comm = make_comm()
    assert comm.initialized is False  # C2.6: nothing is usable before setup()
    assert run(comm.setup()) is True
    assert comm.initialized is True


def test_payload_size_boundaries_are_accepted_and_refused() -> None:
    # C2.1: SIZE/CHUNKS are single bytes and a zero-width payload cannot carry the command id.
    for good in (1, 255):
        comm = make_comm(payload_size=good, uart=UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=1, rxbuf=2048))
        assert comm._init_errno == 0, f"payload_size {good} should be legal"
    for bad in (0, 256, -1):
        comm = make_comm(payload_size=bad)
        assert comm._init_errno != 0, f"payload_size {bad} should be refused"
        assert run(comm.setup()) is False


def test_payload_size_is_never_silently_clamped() -> None:
    # A clamp turns a loud configuration error into a link that desyncs intermittently in the
    # field - the one fault J.6 says the self-healing design cannot heal.
    comm = make_comm(payload_size=500)
    assert comm.payload_size == 500  # kept as given, and refused; not quietly rewritten to 255
    assert comm.initialized is False


def test_non_positive_timeout_is_refused() -> None:
    for bad in (0, -1):
        assert make_comm(timeout=bad)._init_errno != 0


def test_timeout_below_the_gc_pause_floor_is_refused() -> None:
    # C2.4: below this a routine collection pause reads as a link fault, and the link resyncs
    # continuously under memory pressure for no reason.
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=10)
    driver.poller = LinkPoller(driver._uart)  # type: ignore[assignment,arg-type]
    assert UART_Comm(driver, ROLE_INITIATOR, payload_size=8, timeout=30)._init_errno != 0
    assert UART_Comm(driver, ROLE_INITIATOR, payload_size=8, timeout=200)._init_errno == 0


def test_invalid_role_is_refused_and_has_no_default() -> None:
    assert make_comm(role="listener")._init_errno != 0
    assert make_comm(role=ROLE_INITIATOR)._init_errno == 0
    assert make_comm(role=ROLE_RESPONDER, get_callback=echo_get(b""), set_callback=accept_set())._init_errno == 0


def test_a_none_bus_is_recorded_distinctly_and_never_raises() -> None:
    # C2.7: otherwise every call returns a sentinel with no explanation of which thing was wrong.
    comm = make_comm(uart=None)
    assert comm._init_errno != 0
    assert run(comm.setup()) is False
    assert run(comm.uart_set(1, b"x")) is False
    assert run(comm.uart_get(1)) is None
    run(comm.clear())  # must not raise even with no bus at all


def test_construction_performs_no_bus_call() -> None:
    # C2.8: an allocate-only constructor, so construction can never hang outside any supervisor.
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=1)
    driver.poller = LinkPoller(driver._uart)  # type: ignore[assignment,arg-type]
    before = len(driver._uart.log)  # type: ignore[union-attr]
    UART_Comm(driver, ROLE_INITIATOR, payload_size=PAYLOAD_SIZE, timeout=TIMEOUT_MS)
    assert len(driver._uart.log) == before  # type: ignore[union-attr]


def test_maximum_payload_size_against_the_default_rxbuf_is_refused() -> None:
    # C2.9: 5 + 255 = 260 bytes against the driver's own 256-byte default rxbuf, so the maximum
    # legal payload_size overruns it outright - a frame that never completes, indistinguishable
    # from a link fault unless it is caught at construction.
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=1)  # rxbuf defaults to 256
    driver.poller = LinkPoller(driver._uart)  # type: ignore[assignment,arg-type]
    refused = UART_Comm(driver, ROLE_INITIATOR, payload_size=255, timeout=TIMEOUT_MS)
    assert refused._init_errno != 0
    roomy = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=1, rxbuf=1024)
    roomy.poller = LinkPoller(roomy._uart)  # type: ignore[assignment,arg-type]
    assert UART_Comm(roomy, ROLE_INITIATOR, payload_size=255, timeout=TIMEOUT_MS)._init_errno == 0


def test_rxbuf_too_small_for_one_poll_interval_is_refused() -> None:
    # C2.10: at 115200 baud a 20ms poll interval admits ~230 bytes, so a 64-byte rxbuf loses the
    # tail of anything sustained even though a single frame would fit.
    driver = UART(0, tx_pin=0, rx_pin=1, baudrate=115200, poll_wait_ms=20, rxbuf=64)
    driver.poller = LinkPoller(driver._uart)  # type: ignore[assignment,arg-type]
    assert UART_Comm(driver, ROLE_INITIATOR, payload_size=8, timeout=TIMEOUT_MS)._init_errno != 0


def test_every_public_method_is_gated_before_setup() -> None:
    # C2.6: operating on unallocated state must return the method's own sentinel, never raise.
    comm = make_comm()
    assert run(comm.uart_set(1, b"a")) is False
    assert run(comm.uart_set_into(1, bytearray(2), 2)) is False
    assert run(comm.uart_set_stream(1, 4, lambda chunk, buf: 0)) is False
    assert run(comm.uart_get(1)) is None
    assert run(comm.uart_get_into(1, bytearray(4))) is None
    assert run(comm.uart_get_stream(1, lambda chunk, buf: True)) is None
    assert run(comm.uart_listen()) == ListenResult(None, None, None)


# C3 - logger injection, name, errno catalog


def test_logger_injection_uses_both_routes() -> None:
    own = make_comm(name="UART_X")
    assert own.name == "UART_X"
    assert own.pr.name == own.name  # G2.1: registration keys on one and the history on the other
    shared = make_comm(logger=own.pr)
    assert shared.pr is own.pr  # the AsyFramManager-style reach-through


def test_get_error_counter_returns_the_shared_envelope() -> None:
    comm = make_comm(name="UART_X")
    log = run(comm.get_error_counter())
    assert "UART_X" in log
    entry = log["UART_X"]
    assert "ErrCount" in entry
    assert "ErrNum" in entry
    assert "ErrType" in entry


def test_reset_clears_the_history_and_the_streak_state() -> None:
    # C5.5: a reset the caller expects to be total must not leave the escalate-once state behind.
    comm = make_comm(name="UART_X")
    run(comm._err(19, "synthetic"))
    comm._valid_frames = 5
    comm._blind_resyncs = 2
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] > 0
    run(comm.reset_error_counter())
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] == 0
    assert comm._last_errno == 0
    assert comm._blind_resyncs == 0


def test_a_repeated_identical_fault_stops_persisting() -> None:
    # C3.8: a link failing once a second would otherwise write FRAM once a second and bury every
    # other module's entries under one repeated code. Exactly two entries per fault episode - the
    # transition in and the transition back out - never one per occurrence.
    comm = make_comm(name="UART_X")
    run(comm._err(19, "first"))
    after_first = run(comm.get_error_counter())["UART_X"]["ErrCount"]
    assert after_first == 1
    for _ in range(20):
        run(comm._err(19, "again"))
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] == after_first  # the transition only
    run(comm._note_valid_frame())  # the link recovers: the episode's closing entry
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] == after_first + 1
    run(comm._err(20, "a different fault"))
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] == after_first + 2


def test_a_single_transient_fault_leaves_one_entry_not_a_pair() -> None:
    # The closing entry is worth persisting only when the fault was actually repeating; a lone
    # transient must not cost two slots in a bounded history.
    comm = make_comm(name="UART_X")
    run(comm._err(19, "one-off"))
    run(comm._note_valid_frame())
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] == 1


def test_every_declared_errno_is_inside_the_published_range() -> None:
    # C3.7: /status must never show a number the catalog cannot explain, so the ranges are checked
    # mechanically against the source rather than by review.
    with open(_SRC) as handle:
        source = handle.read()
    err_min, err_max, wrn_min, wrn_max = 10, 33, 10, 14
    for line in source.split("\n"):
        stripped = line.strip()
        for prefix, low, high in (("_ERR_", err_min, err_max), ("_WRN_", wrn_min, wrn_max)):
            if not stripped.startswith(prefix) or "const(" not in stripped or "_MIN" in stripped or "_MAX" in stripped:
                continue
            value = int(stripped.split("const(")[1].split(")")[0])
            assert low <= value <= high, f"{stripped} is outside the declared {prefix} range"


def test_no_errno_literal_bypasses_the_catalog() -> None:
    # The other half of C3.7: an errno= that is a bare number rather than a catalog name would
    # pass the range sweep above while being invisible to it.
    with open(_SRC) as handle:
        source = handle.read()
    for keyword in ("errno=", "wrnno="):
        for part in source.split(keyword)[1:]:
            value = part.split(")")[0].split(",")[0].strip()
            assert value.startswith(("_ERR_", "_WRN_", "errno", "self.")), f"{keyword}{value} is not a catalog name"


# C4 - frame buffers and scratch allocation


def test_tx_and_rx_buffers_are_separate() -> None:
    # C4.2: one shared buffer means a received frame overwrites the frame being acknowledged.
    comm = make_comm()
    tx = comm._tx.get_buf()
    rx = comm._rx.get_buf()
    assert tx is not None
    assert rx is not None
    assert tx is not rx
    tx[0] = 0x11
    rx[0] = 0x22
    assert tx[0] == 0x11


def test_a_failed_buffer_allocation_degrades_every_entry_point() -> None:
    # C4.1: LockableBuffer returns None rather than raising, and every consumer's first act is to
    # check for it.
    comm = make_comm()
    run(comm.setup())
    comm._tx.buf = None
    comm._rx.buf = None
    assert run(comm.uart_set(1, b"x")) is False
    assert run(comm.uart_get(1)) is None


def test_padding_is_zero_filled_from_the_preallocated_buffer() -> None:
    # C4.3: leaving the remainder unwritten transmits the previous frame's payload remnants - a
    # real data leak between unrelated messages.
    comm = make_comm()
    assert comm._prepare_tx(1, _CMD_SET, 2, 2, b"\xaa" * PAYLOAD_SIZE, PAYLOAD_SIZE) is True
    assert comm._prepare_tx(2, _CMD_SET, 2, 2, b"\xbb", 1) is True
    buf = comm._tx.get_buf()
    assert buf is not None
    assert buf[_PAYLOAD] == 0xBB
    assert bytes(buf[_PAYLOAD + 1 : _PAYLOAD + PAYLOAD_SIZE]) == bytes(PAYLOAD_SIZE - 1)


def test_payload_size_is_immutable_after_construction() -> None:
    comm = make_comm()
    assert not hasattr(comm, "set_payload_size")  # C4.5: no setter exists


# C5/C6 - lifecycle, starters, listen loop


def test_starter_lists_match_the_role() -> None:
    # C5.4: an initiator exposing a listen task would mean both ends initiate, and the protocol
    # has no arbitration for that.
    initiator = make_comm(role=ROLE_INITIATOR)
    responder = make_comm(role=ROLE_RESPONDER, get_callback=echo_get(b""), set_callback=accept_set())
    assert initiator.get_task_starters() == []
    assert len(responder.get_task_starters()) == 1
    assert initiator.get_timer_starters() == []
    assert responder.get_timer_starters() == []  # E3.1/E3.2: no machine.Timer anywhere


def test_the_module_constructs_no_timer_at_all() -> None:
    # E3's whole point: a soft one-shot Timer callback can be silently dropped, and the flag it
    # would have set is then never set - the legacy module's permanent hang. Asserted against the
    # source because "there is no Timer" is a structural property, not an observable behaviour.
    with open(_SRC) as handle:
        code = [line.split("#")[0] for line in handle.read().split("\n")]
    assert not any("Timer(" in line or "machine" in line for line in code)


def test_setup_drains_a_partial_frame_left_over_from_before() -> None:
    # C5.6: a peer mid-train, or one that outlived this side's reset, leaves bytes in the driver's
    # rxbuf. A boot-time drain is not a fault and must not be counted.
    pair = Pair(get_callback=echo_get(b"ok"), set_callback=accept_set())
    pair.fake_b.feed_rx(b"\x01\x02\x03")  # a partial frame, as if the peer was mid-transmission
    assert run(pair.responder.setup()) is True
    assert pair.fake_b.rx_queue == bytearray()
    # Not counted: an entry here would land in the FRAM history on every boot of a live link,
    # indistinguishable from a real fault - which is the one diagnostic a reboot does not erase.
    assert run(pair.responder.get_error_counter())["UART_B"]["ErrCount"] == 0


def test_a_responder_without_callbacks_is_refused_at_construction() -> None:
    # C6.2: every GET and SET would be unanswerable, discovered only when the peer first asks.
    assert make_comm(role=ROLE_RESPONDER)._init_errno != 0
    assert make_comm(role=ROLE_RESPONDER, get_callback=echo_get(b""))._init_errno != 0


def test_the_listen_loop_backs_off_on_a_dead_link_and_resets_after_success() -> None:
    # C6.3/C6.4: a zero-delay retry is captive_dns.py's measured recovery storm; a backoff that
    # never resets leaves a recovered link throttled at the cap forever.
    comm = make_comm(role=ROLE_RESPONDER, get_callback=echo_get(b""), set_callback=accept_set())
    assert comm._backoff_initial_ms == TIMEOUT_MS // 2
    assert comm._backoff_max_ms == TIMEOUT_MS * 5
    assert comm._backoff_max_ms > comm._backoff_initial_ms


def test_the_listen_loop_survives_a_raising_callback() -> None:
    # C6.6: uart_listen() is contracted never to raise, but a contract is not an enforcement.
    def explode(cmd_id: int) -> "tuple[bool, Any]":
        raise ValueError("callback blew up")

    pair = Pair(get_callback=explode, set_callback=accept_set())
    assert run(pair.setup()) is True

    async def scenario() -> bool:
        loop = asyncio.create_task(pair.responder._listen_loop())
        got = await pair.initiator.uart_get(7)
        await asyncio.sleep_ms(20)
        alive = not loop.done()
        loop.cancel()
        return alive and got is None

    assert run(scenario(), limit=10) is True


# ===========================================================================
# Phase D - frame layer
# ===========================================================================


def test_header_fields_land_at_their_documented_offsets() -> None:
    comm = make_comm()
    assert comm._prepare_tx(0x2A, _CMD_SET, 3, 2, b"\x01\x02", 2) is True
    buf = comm._tx.get_buf()
    assert buf is not None
    assert buf[_UID] == 0x2A
    assert buf[_CMD] == _CMD_SET
    assert buf[_SIZE] == 2
    assert buf[_CHUNKS] == 3
    assert buf[_CUR] == 2
    assert bytes(buf[_PAYLOAD : _PAYLOAD + 2]) == b"\x01\x02"


def test_out_of_range_header_fields_are_rejected_not_truncated() -> None:
    # D1.1: struct.pack() truncates silently on this platform, so an out-of-range CHUNKS would
    # become a plausible wrong value instead of an error.
    comm = make_comm()
    assert comm._prepare_tx(0xFF, _CMD_SET, 2, 1, b"\x01", 1) is False  # UID 0xFF is never emitted
    assert comm._prepare_tx(1, 0x03, 2, 1, b"\x01", 1) is False  # not a real command
    assert comm._prepare_tx(1, _CMD_SET, 256, 1, b"\x01", 1) is False
    assert comm._prepare_tx(1, _CMD_SET, 2, 3, b"\x01", 1) is False  # cur_chunk beyond chunks


def test_a_payload_longer_than_the_region_is_rejected() -> None:
    comm = make_comm()
    assert comm._prepare_tx(1, _CMD_SET, 2, 2, b"x" * (PAYLOAD_SIZE + 1), PAYLOAD_SIZE + 1) is False


def test_size_always_matches_the_bytes_actually_copied() -> None:
    # D1.3: a SIZE passed independently of the copy lets the peer read padding as payload.
    comm = make_comm()
    assert comm._prepare_tx(1, _CMD_SET, 2, 2, b"\x01\x02", 4) is False  # claims more than it has


def test_the_uid_cycle_covers_every_legal_value_and_never_0xff() -> None:
    # D3.1: the 0xFE -> 0 wrap is a deliberate off-by-one barrier and keeps the UID space exactly
    # as large as the longest train, so no UID repeats inside one transfer.
    from asy_uart_comm import _next_uid

    seen = []
    uid = 0
    for _ in range(255):
        seen.append(uid)
        uid = _next_uid(uid)
    assert uid == 0  # wrapped exactly once
    assert sorted(seen) == list(range(255))
    assert 0xFF not in seen


def test_the_next_uid_prediction_is_correct_at_the_wrap_boundary() -> None:
    # D3.2: a bare +1 mispredicts precisely here, once every 255 frames.
    from asy_uart_comm import _next_uid

    assert _next_uid(0xFD) == 0xFE
    assert _next_uid(0xFE) == 0


def build_frame(uid: int = 1, cmd: int = _CMD_SET, size: int = 1, chunks: int = 2, cur: int = 1, payload: bytes = b"\x07") -> bytearray:
    frame = bytearray(_FRAME)
    frame[_UID] = uid
    frame[_CMD] = cmd
    frame[_SIZE] = size
    frame[_CHUNKS] = chunks
    frame[_CUR] = cur
    frame[_PAYLOAD : _PAYLOAD + len(payload)] = payload
    return frame


def test_validation_accepts_every_legal_frame_shape() -> None:
    comm = make_comm()
    assert comm._validate(build_frame(), _CMD_SET, 1, None, None) == 0
    assert comm._validate(build_frame(cmd=_CMD_GET, chunks=1), _CMD_GET, 1, None, None) == 0
    assert comm._validate(build_frame(cmd=_CMD_ACK, size=0, chunks=1, cur=1), _CMD_ACK, 1, 1, 1) == 0
    full = build_frame(size=PAYLOAD_SIZE, chunks=3, cur=2, uid=2)
    assert comm._validate(full, _CMD_SET, 2, 3, 2) == 0


def test_a_multi_bit_command_is_rejected_rather_than_falling_through() -> None:
    # D4.1: today's bitmask test lets 0x03 and 0x06 pass validation and then match no dispatch
    # branch, so a malformed frame is silently mishandled instead of rejected.
    comm = make_comm()
    for bad in (0x03, 0x06, 0x00, 0x07):
        assert comm._validate(build_frame(cmd=bad), _CMD_SET, 1, None, None) != 0


def test_a_changed_chunks_total_is_rejected() -> None:
    # D4.2: otherwise a peer truncates a transfer mid-train by re-declaring the total, and the
    # receiver reports success on partial data.
    comm = make_comm()
    assert comm._validate(build_frame(size=PAYLOAD_SIZE, chunks=2, cur=2, uid=2), _CMD_SET, 2, 3, 2) != 0


def test_a_stale_data_chunk_is_rejected_by_its_uid() -> None:
    # D4.3: invisible before - only ACKs were UID-checked.
    comm = make_comm()
    assert comm._validate(build_frame(size=PAYLOAD_SIZE, chunks=3, cur=2, uid=9), _CMD_SET, 2, 3, 2) != 0


def test_a_first_chunk_with_the_wrong_size_is_rejected() -> None:
    # D4.4: else the command id is silently read from a padding byte, usually 0.
    comm = make_comm()
    assert comm._validate(build_frame(size=0), _CMD_SET, 1, None, None) != 0
    assert comm._validate(build_frame(size=2), _CMD_SET, 1, None, None) != 0


def test_a_short_middle_chunk_is_rejected() -> None:
    # D4.5: the payload is silently corrupted, and the length still adds up if a later chunk
    # compensates.
    comm = make_comm()
    assert comm._validate(build_frame(size=PAYLOAD_SIZE - 1, chunks=4, cur=2, uid=2), _CMD_SET, 2, 4, 2) != 0


def test_an_empty_chunk_is_legal_only_as_a_two_chunk_trains_last() -> None:
    # D4.6: an empty middle chunk must not be misread as a genuinely empty payload.
    comm = make_comm()
    assert comm._validate(build_frame(size=0, chunks=2, cur=2, uid=2), _CMD_SET, 2, 2, 2) == 0
    assert comm._validate(build_frame(size=0, chunks=3, cur=3, uid=3), _CMD_SET, 3, 3, 3) != 0


def test_a_set_declaring_a_single_chunk_is_rejected() -> None:
    # D4.7: no data chunk exists to acknowledge, and a conforming sender floors at 2.
    comm = make_comm()
    assert comm._validate(build_frame(chunks=1, cur=1), _CMD_SET, 1, None, None) != 0


def test_a_zero_chunk_train_is_rejected() -> None:
    comm = make_comm()
    assert comm._validate(build_frame(chunks=0, cur=1), _CMD_SET, 1, None, None) != 0


def test_a_malformed_ack_is_rejected() -> None:
    # D4.9: a malformed ACK accepted as valid confirmation is worse than no ACK at all.
    comm = make_comm()
    assert comm._validate(build_frame(cmd=_CMD_ACK, size=1, chunks=1, cur=1), _CMD_ACK, 1, 1, 1) != 0
    assert comm._validate(build_frame(cmd=_CMD_ACK, size=0, chunks=2, cur=1), _CMD_ACK, 1, 1, 1) != 0
    assert comm._validate(build_frame(cmd=_CMD_ACK, size=0, chunks=1, cur=1, uid=9), _CMD_ACK, 1, 1, 1) != 0


def test_a_frame_of_the_wrong_kind_is_rejected_at_each_read_site() -> None:
    # D4.10/D4.11: a data frame where an ACK is due, or a GET arriving at an initiator, is the
    # peer's violation and must be visible as such.
    comm = make_comm()
    assert comm._validate(build_frame(cmd=_CMD_SET), _CMD_ACK, 1, 1, 1) != 0
    assert comm._validate(build_frame(cmd=_CMD_GET, chunks=1), _CMD_ACK, 1, 1, 1) != 0
    assert comm._validate(build_frame(cmd=_CMD_ACK, size=0, chunks=1), _CMD_SET, 1, None, None) != 0


def test_validation_never_raises_on_a_short_or_missing_buffer() -> None:
    # D4.12: an exception escaping a module contracted never to raise.
    comm = make_comm()
    assert comm._validate(None, _CMD_SET, 1, None, None) != 0
    assert comm._validate(bytearray(2), _CMD_SET, 1, None, None) != 0
    assert comm._validate(bytearray(0), _CMD_SET, 1, None, None) != 0


def test_a_received_uid_of_0xff_is_rejected() -> None:
    # D3.3: out of contract - a conforming peer never sends it.
    comm = make_comm()
    assert comm._validate(build_frame(uid=0xFF), _CMD_SET, 1, None, None) != 0


def test_the_ack_frame_is_byte_exact() -> None:
    # D5: the protocol's only positive signal, so its shape is asserted rather than assumed.
    pair = Pair(get_callback=echo_get(b""), set_callback=accept_set())
    assert run(pair.setup()) is True

    async def scenario() -> None:
        async with pair.driver_b as device:
            await pair.responder._send_ack(device, 0x42)

    run(scenario())
    pair.link.settle()
    ack = pair.wire_from_responder()
    assert len(ack) == _FRAME
    assert ack[_UID] == 0x42
    assert ack[_CMD] == _CMD_ACK
    assert ack[_SIZE] == 0
    assert ack[_CHUNKS] == 1
    assert ack[_CUR] == 1
    assert bytes(ack[_PAYLOAD:]) == bytes(PAYLOAD_SIZE)


def test_an_ack_is_sent_even_while_the_write_hold_off_is_active() -> None:
    # D5.2/E3.4: if the hold-off gated ACKs too, both sides would back off simultaneously and the
    # link would stall with neither at fault.
    pair = Pair(get_callback=echo_get(b""), set_callback=accept_set())
    assert run(pair.setup()) is True
    pair.responder._hold_off_writes()

    async def scenario() -> bool:
        async with pair.driver_b as device:
            return await pair.responder._send_ack(device, 0x07)

    assert run(scenario()) is True
    pair.link.settle()
    assert len(pair.wire_from_responder()) == _FRAME


# ===========================================================================
# Phase E - exchange layer
# ===========================================================================


def test_a_clean_write_round_trip_is_acknowledged() -> None:
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set(3, b"hi"))) is True


def test_a_missing_ack_bounds_the_wait_and_resyncs() -> None:
    # E1.1: without the bound the sender waits forever; with it, the failure is reported and both
    # sides quiesce so the next transfer starts on a clean frame boundary.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.link.direction_from(pair.fake_b).silent = True  # the responder's ACKs never arrive
    assert run(pair.with_listener(pair.initiator.uart_set(3, b"hi")), limit=15) is False
    assert pair.initiator._holdoff_active is True  # the hold-off that follows a resync


def test_a_write_that_never_reaches_the_peer_fails_the_same_way() -> None:
    # E1.5: indistinguishable from a lost ACK at this layer, and the distinction is not invented.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.link.direction_from(pair.fake_a).silent = True
    assert run(pair.with_listener(pair.initiator.uart_set(3, b"hi")), limit=15) is False


def test_a_stale_ack_uid_is_rejected() -> None:
    # E1.2: the UID space is exactly as large as the longest train, so no UID repeats inside one
    # transfer and a stale ACK can never be mistaken for the current one.
    comm = make_comm()
    ack = build_frame(cmd=_CMD_ACK, size=0, chunks=1, cur=1, uid=5)
    assert comm._validate(ack, _CMD_ACK, 1, 1, 5) == 0
    assert comm._validate(ack, _CMD_ACK, 1, 1, 6) != 0


def test_a_lost_final_ack_reports_failure_while_the_receiver_reports_success() -> None:
    # E1.6/decision 10: the two-generals case, folded into failure by decision. There is no
    # retransmission to hang a third state on and a caller could not act differently anyway.
    def remember(cmd_id: int) -> "tuple[bool, int | None]":
        return True, None

    pair = Pair(get_callback=echo_get(b""), set_callback=remember)
    assert run(pair.setup()) is True
    # b"abc" is a two-chunk train, so the responder emits exactly two ACKs: one for the command
    # header and the deferred final one. Cutting the direction after the first is deterministic -
    # a watcher task racing the wire log would not be.
    pair.link.direction_from(pair.fake_b).truncate_after = _FRAME

    async def scenario() -> "tuple[bool, ListenResult]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        sent = await pair.initiator.uart_set(3, b"abc")
        return sent, await asyncio.wait_for(listener, 10)

    sent, result = run(scenario(), limit=25)
    assert sent is False  # the sender cannot know, so it reports failure
    assert result.cmd_id == 3  # the receiver genuinely has the data
    assert bytes(result.payload) == b"abc"


def test_the_write_hold_off_uses_a_deadline_and_expires() -> None:
    # E3: a deadline cannot be dropped the way a soft one-shot Timer callback can.
    comm = make_comm()
    run(comm.setup())
    # Sampled into locals and asserted together: asserting the same attribute's identity twice in
    # sequence narrows it to a literal and makes the rest of the test statically unreachable.
    before = comm._holdoff_active
    comm._hold_off_writes()
    during = comm._holdoff_active
    run(asyncio.wait_for(comm._await_write_gate(), 5))
    after = comm._holdoff_active
    assert (before, during, after) == (False, True, False)  # expired by time, not by a callback


def test_the_hold_off_window_derives_from_timeout() -> None:
    # E3.6/changelog A4: both constants are 1.5 x timeout and neither is hardcoded, because a peer
    # draining for less transmits into the other's drain window.
    assert make_comm(timeout=100)._resync_window_ms() == 150
    assert make_comm(timeout=400)._resync_window_ms() == 600


def test_the_hold_off_deadline_survives_the_ticks_rollover() -> None:
    # E3.3: a raw now - t0 subtraction is wrong at the 2**30 ms rollover - a fault that appears
    # once per uptime period and cannot be found by waiting for it.
    import time

    comm = make_comm()
    comm._holdoff_active = True
    comm._holdoff_deadline = time.ticks_add(time.ticks_ms(), -1)  # just past, across any boundary
    run(asyncio.wait_for(comm._await_write_gate(), 2))
    assert comm._holdoff_active is False


def test_listening_clears_the_hold_off() -> None:
    # E3.5: if the peer is requesting something it is definitely up again - the one documented
    # reset besides the deadline itself.
    pair = run(build_pair(get_callback=echo_get(b"v"), set_callback=accept_set()))
    pair.responder._hold_off_writes()
    assert run(pair.with_listener(pair.initiator.uart_get(9))) is not None
    assert pair.responder._holdoff_active is False


def test_the_drain_ends_once_the_line_is_quiet() -> None:
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.fake_a.feed_rx(b"garbage bytes")

    async def scenario() -> int:
        async with pair.driver_a as device:
            return await pair.initiator._drain(device)

    assert run(scenario(), limit=10) == len(b"garbage bytes")


def test_the_drain_is_bounded_against_a_peer_that_never_stops() -> None:
    # E4.1: the legacy module's unbounded `while True` never sees quiet against a stuck sender.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))

    async def flood() -> None:
        while True:
            pair.fake_a.feed_rx(b"\xff" * 32)
            await asyncio.sleep_ms(1)

    async def scenario() -> bool:
        flooder = asyncio.create_task(flood())
        try:
            async with pair.driver_a as device:
                await asyncio.wait_for(pair.initiator._drain(device), 10)
        finally:
            flooder.cancel()
        return True

    assert run(scenario(), limit=20) is True  # terminates at the bound instead of looping forever


def test_the_drain_reads_into_the_scratch_buffer() -> None:
    # E4.2: read() would allocate per round, on exactly the degraded link where the heap is most
    # fragmented. Asserted on what the fake was asked to do.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.fake_a.log.clear()
    pair.fake_a.feed_rx(b"xyz")

    async def scenario() -> None:
        async with pair.driver_a as device:
            await pair.initiator._drain(device)

    run(scenario(), limit=10)
    kinds = {entry[0] for entry in pair.fake_a.log}
    assert "read" not in kinds
    assert "readinto" in kinds


def test_a_resync_is_not_re_entrant() -> None:
    # E4.3: a fault during a resync continues the drain, it never starts a second one.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.initiator._in_resync = True

    async def scenario() -> None:
        async with pair.driver_a as device:
            await pair.initiator._resync(device)

    run(scenario(), limit=10)
    assert pair.initiator._holdoff_active is False  # the nested call did nothing at all


def test_every_public_entry_point_converges_on_its_own_sentinel() -> None:
    # E4.6: a caller must never believe a failed transfer succeeded.
    pair = run(build_pair(get_callback=echo_get(b"v"), set_callback=accept_set()))
    pair.link.direction_from(pair.fake_b).silent = True  # nothing ever answers
    assert run(pair.initiator.uart_set(1, b"x"), limit=15) is False
    assert run(pair.initiator.uart_get(1), limit=15) is None
    assert run(pair.initiator.uart_get_into(1, bytearray(16)), limit=15) is None
    assert run(pair.initiator.uart_set_into(1, bytearray(4), 4), limit=15) is False


def test_clear_cancels_first_and_drains_exactly_once() -> None:
    # E5.1/E5.3: taking the lock before attempting the cancel deadlocks against the very listener
    # this exists to free, and two drains double the recovery time for no benefit.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    drains = []
    original = pair.responder._drain

    async def counting_drain(device: UART) -> int:
        drains.append(1)
        return await original(device)

    pair.responder._drain = counting_drain  # type: ignore[method-assign]

    async def scenario() -> None:
        listener = asyncio.create_task(pair.responder.uart_listen())
        await asyncio.sleep_ms(10)  # let it park in the unbounded read, holding the bus lock
        await asyncio.wait_for(pair.responder.clear(), 10)
        listener.cancel()

    run(scenario(), limit=20)
    assert len(drains) == 1


def test_clear_with_nothing_in_flight_takes_the_lock_and_drains() -> None:
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.fake_a.feed_rx(b"leftovers")
    run(pair.initiator.clear(), limit=10)
    assert pair.fake_a.rx_queue == bytearray()


# ===========================================================================
# Phase F - transaction layer
# ===========================================================================


def test_a_payload_less_command_still_produces_two_chunks() -> None:
    # F1: even a payload-less command has one data chunk to acknowledge, so it is confirmed end to
    # end rather than merely heard.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set(5, None))) is True
    sent = frames(pair.wire_from_initiator(), _FRAME)
    assert len(sent) == 2
    assert sent[0][_CHUNKS] == 2
    assert sent[0][_SIZE] == 1
    assert sent[0][_PAYLOAD] == 5
    assert sent[1][_SIZE] == 0


def test_the_wire_log_of_a_multi_chunk_set_is_byte_exact() -> None:
    payload = bytes(range(PAYLOAD_SIZE + 3))  # spans two data chunks
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set(0x11, payload))) is True
    sent = frames(pair.wire_from_initiator(), _FRAME)
    assert len(sent) == 3
    assert [f[_CHUNKS] for f in sent] == [3, 3, 3]  # constant across the whole train
    assert [f[_CUR] for f in sent] == [1, 2, 3]
    assert [f[_SIZE] for f in sent] == [1, PAYLOAD_SIZE, 3]
    assert sent[1][_PAYLOAD : _PAYLOAD + PAYLOAD_SIZE] == payload[:PAYLOAD_SIZE]
    assert sent[2][_PAYLOAD : _PAYLOAD + 3] == payload[PAYLOAD_SIZE:]
    uids = [f[_UID] for f in sent]
    assert len(set(uids)) == 3  # a fresh UID per frame, none repeated within the train


def test_chunk_counts_at_the_payload_size_boundaries() -> None:
    comm = make_comm()
    assert comm._chunk_count(0) == 2
    assert comm._chunk_count(PAYLOAD_SIZE - 1) == 2
    assert comm._chunk_count(PAYLOAD_SIZE) == 2
    assert comm._chunk_count(PAYLOAD_SIZE + 1) == 3
    assert comm._chunk_count(254 * PAYLOAD_SIZE) == 255  # the largest legal train
    assert comm._chunk_count(254 * PAYLOAD_SIZE + 1) is None  # F1.1: rejected, never mis-declared


def test_an_oversize_payload_is_rejected_before_the_first_frame() -> None:
    # F1.1: never partially sent - a half-delivered train is worse than a refused one.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    too_big = bytes(254 * PAYLOAD_SIZE + 1)
    assert run(pair.initiator.uart_set(1, too_big), limit=15) is False
    assert pair.wire_from_initiator() == b""


def test_a_missing_ack_at_each_train_position_aborts_and_resyncs() -> None:
    # F1.3: nothing is re-sent - that is the design, not a gap.
    # A PAYLOAD_SIZE + 1 payload is a three-chunk train, so the responder emits three ACKs: the
    # command header's, the middle chunk's, and the deferred final one. Each is dropped in turn by
    # cutting the responder's direction after exactly that many whole frames.
    for kept_acks in (0, 1, 2):
        pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
        pair.link.direction_from(pair.fake_b).truncate_after = kept_acks * _FRAME
        result = run(pair.with_listener(pair.initiator.uart_set(1, bytes(PAYLOAD_SIZE + 1))), limit=25)
        assert result is False, f"a train losing the ACK after {kept_acks} should fail"
        assert pair.initiator._holdoff_active is True, "every abort quiesces the link"


def test_a_multi_chunk_payload_arrives_byte_identical() -> None:
    got: list[Any] = []

    def remember(cmd_id: int) -> "tuple[bool, int | None]":
        return True, None

    payload = bytes((i * 7) & 0xFF for i in range(PAYLOAD_SIZE * 3 + 2))
    pair = Pair(get_callback=echo_get(b""), set_callback=remember)
    assert run(pair.setup()) is True

    async def scenario() -> ListenResult:
        listener = asyncio.create_task(pair.responder.uart_listen())
        sent = await pair.initiator.uart_set(0x21, payload)
        result = await asyncio.wait_for(listener, 5)
        got.append(sent)
        return result

    result = run(scenario(), limit=20)
    assert got == [True]
    assert result.cmd_id == 0x21
    assert bytes(result.payload) == payload


def test_all_three_expected_size_modes() -> None:
    # F2: don't care, exactly empty, exactly N - enforced incrementally and finally.
    for exp, payload, ok in ((None, b"abc", True), (0, b"", True), (3, b"abc", True), (4, b"abc", False), (0, b"abc", False)):
        pair = Pair(get_callback=echo_get(b""), set_callback=accept_set(exp))
        assert run(pair.setup()) is True

        async def scenario(data: bytes = payload, link: Pair = pair) -> bool:
            listener = asyncio.create_task(link.responder.uart_listen())
            sent = await link.initiator.uart_set(1, data)
            await asyncio.wait_for(listener, 8)
            return sent

        assert run(scenario(), limit=25) is ok, f"exp_size={exp} payload={payload!r}"


def test_an_empty_payload_is_a_distinct_outcome_from_failure() -> None:
    # F2.5/decision 9: None means failure and a zero-length result means genuinely empty; if the
    # two ever collapse, a caller cannot tell an empty answer from a dead link.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    answer = run(pair.with_listener(pair.initiator.uart_get(4)))
    assert answer is not None
    assert len(answer) == 0


def test_an_expected_size_the_train_could_never_deliver_is_rejected_early() -> None:
    # F2.8: the transfer is doomed the moment CHUNKS is known, so it does not run to completion
    # first.
    comm = make_comm()
    assert comm._dest_size(2, PAYLOAD_SIZE) == PAYLOAD_SIZE
    assert comm._dest_size(2, PAYLOAD_SIZE + 1) is None
    assert comm._dest_size(3, -1) == 2 * PAYLOAD_SIZE


def test_a_get_round_trip_returns_the_answer() -> None:
    payload = bytes(range(PAYLOAD_SIZE + 2))
    pair = run(build_pair(get_callback=echo_get(payload), set_callback=accept_set()))
    answer = run(pair.with_listener(pair.initiator.uart_get(0x33)))
    assert answer is not None
    assert bytes(answer) == payload


def test_the_get_answer_echoes_the_requested_command_id() -> None:
    # F3.1: otherwise the initiator accepts an answer to a question it never asked.
    pair = run(build_pair(get_callback=echo_get(b"v"), set_callback=accept_set()))
    run(pair.with_listener(pair.initiator.uart_get(0x44)))
    answer = frames(pair.wire_from_responder(), _FRAME)
    headers = [f for f in answer if f[_CMD] == _CMD_SET and f[_CUR] == 1]
    assert headers
    assert headers[0][_PAYLOAD] == 0x44


def test_a_rejected_get_callback_reports_a_distinct_outcome() -> None:
    # F3.3: withhold the answer, resync, and tell the responder's own caller which command was
    # refused - not silently nothing.
    def refuse(cmd_id: int) -> "tuple[bool, Any]":
        return False, None

    pair = Pair(get_callback=refuse, set_callback=accept_set())
    assert run(pair.setup()) is True

    async def scenario() -> "tuple[bytearray | None, ListenResult]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        answer = await pair.initiator.uart_get(0x55)
        return answer, await asyncio.wait_for(listener, 10)

    answer, result = run(scenario(), limit=25)
    assert answer is None
    assert result.cmd_id is None
    assert result.cmd == _CMD_GET  # which kind was refused is still reported


def test_uart_listen_returns_the_namedtuple_on_every_path() -> None:
    # F4.1: a bare None makes a caller's three-way unpack raise inside a module contracted never
    # to raise.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    refused = run(pair.initiator.uart_listen())  # wrong role
    assert isinstance(refused, tuple)
    assert len(refused) == 3
    assert refused.cmd_id is None


def test_both_sync_and_async_callbacks_work() -> None:
    async def async_get(cmd_id: int) -> "tuple[bool, bytes]":
        await asyncio.sleep_ms(1)
        return True, b"async"

    pair = run(build_pair(get_callback=async_get, set_callback=accept_set()))
    answer = run(pair.with_listener(pair.initiator.uart_get(1)))
    assert answer is not None
    assert bytes(answer) == b"async"


def test_a_callback_returning_the_wrong_shape_is_treated_like_a_raise() -> None:
    # F4.3: a TypeError on unpacking is the same escape by another route.
    comm = make_comm()
    assert comm._pair(None) is None
    assert comm._pair(42) is None
    assert comm._pair((True,)) is None
    assert comm._pair((True, b"x", 3)) is None
    assert comm._pair(("yes", b"x")) is None  # a truthy non-bool is not a validity flag
    assert comm._pair((True, b"x")) == (True, b"x")


def test_a_callback_returning_a_non_buffer_payload_is_rejected() -> None:
    # F4.3 again: the payload's type is part of the return shape, so a str here must not reach
    # the frame builder.
    def wrong_type(cmd_id: int) -> "tuple[bool, Any]":
        return True, "not a buffer"

    pair = Pair(get_callback=wrong_type, set_callback=accept_set())
    assert run(pair.setup()) is True

    async def scenario() -> "bytearray | None":
        listener = asyncio.create_task(pair.responder.uart_listen())
        answer = await pair.initiator.uart_get(1)
        await asyncio.wait_for(listener, 10)
        return answer

    assert run(scenario(), limit=25) is None


def test_a_callback_asking_for_an_impossible_size_is_rejected() -> None:
    # F4.4: otherwise it propagates into the sizing and allocates nonsense.
    for bad in (-5, 255 * PAYLOAD_SIZE * 4):
        pair = Pair(get_callback=echo_get(b""), set_callback=accept_set(bad))
        assert run(pair.setup()) is True

        async def scenario(link: Pair = pair) -> bool:
            listener = asyncio.create_task(link.responder.uart_listen())
            sent = await link.initiator.uart_set(1, b"ab")
            await asyncio.wait_for(listener, 10)
            return sent

        assert run(scenario(), limit=25) is False, f"exp_size {bad} should be refused"


def test_a_re_entrant_callback_is_refused_instead_of_deadlocking() -> None:
    # F4.9: asyncio.Lock is not reentrant, so a callback that calls back in would await a lock its
    # own caller holds - the task deadlocks with the bus held and nothing times out, because
    # nothing is waiting on the wire. The bounded run() here is what proves it is not merely slow.
    pair = Pair(get_callback=echo_get(b""), set_callback=accept_set())
    assert run(pair.setup()) is True
    outcome: list[Any] = []

    async def reentrant(cmd_id: int) -> "tuple[bool, bytes]":
        outcome.append(await pair.responder.uart_set(9, b"nested"))
        return True, b"v"

    pair.responder.get_callback = reentrant

    async def scenario() -> "bytearray | None":
        listener = asyncio.create_task(pair.responder.uart_listen())
        answer = await pair.initiator.uart_get(1)
        await asyncio.wait_for(listener, 10)
        return answer

    run(scenario(), limit=25)
    assert outcome == [False]  # refused with a sentinel, never awaited into a deadlock


def test_the_role_gate_refuses_the_wrong_direction() -> None:
    # F5.1: the lock is released between listen calls, so an application could otherwise interleave
    # an initiation into a responder's loop and cause exactly the simultaneous initiation the
    # design has no arbitration for.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.responder.uart_set(1, b"x")) is False
    assert run(pair.responder.uart_get(1)) is None
    assert run(pair.initiator.uart_listen()).cmd_id is None


def test_a_responder_still_answers_a_get_while_the_role_gate_is_active() -> None:
    # F5.2: the answer runs through the internal unlocked SET path. If the gate blocked it too, a
    # responder could never answer anything and the protocol would simply stop working.
    pair = run(build_pair(get_callback=echo_get(b"answer"), set_callback=accept_set()))
    assert run(pair.responder.uart_set(1, b"x")) is False  # the gate is genuinely active
    answer = run(pair.with_listener(pair.initiator.uart_get(1)))
    assert answer is not None
    assert bytes(answer) == b"answer"


def test_the_role_is_immutable_after_construction() -> None:
    comm = make_comm()
    assert not hasattr(comm, "set_role")  # F5.4


def test_both_halves_of_each_pair_move_identical_bytes() -> None:
    # F6.1: a zero-copy path that exists for reads but not writes is worse than neither, because
    # it looks complete.
    payload = bytes(range(PAYLOAD_SIZE + 1))
    via_convenience = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(via_convenience.with_listener(via_convenience.initiator.uart_set(2, payload))) is True
    via_into = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(via_into.with_listener(via_into.initiator.uart_set_into(2, bytearray(payload), len(payload)))) is True
    assert via_convenience.wire_from_initiator() == via_into.wire_from_initiator()

    by_value = run(build_pair(get_callback=echo_get(payload), set_callback=accept_set()))
    answer = run(by_value.with_listener(by_value.initiator.uart_get(2)))
    by_buffer = run(build_pair(get_callback=echo_get(payload), set_callback=accept_set()))
    dest = bytearray(PAYLOAD_SIZE * 4)
    written = run(by_buffer.with_listener(by_buffer.initiator.uart_get_into(2, dest)))
    assert answer is not None
    assert written == len(payload)
    assert bytes(answer) == bytes(dest[:written])


def test_an_into_destination_that_is_too_small_is_refused() -> None:
    # F6.2/F2.9: checked before the first data ACK, so nothing is overrun and nothing is reported
    # as success.
    pair = run(build_pair(get_callback=echo_get(bytes(PAYLOAD_SIZE * 2)), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_get_into(1, bytearray(2))), limit=20) is None


def test_an_into_destination_of_none_returns_the_sentinel() -> None:
    # F6.3: a failed LockableBuffer hands its owner None; an AttributeError here would be the
    # worst possible moment for one.
    comm = make_comm()
    run(comm.setup())
    assert run(comm.uart_get_into(1, None)) is None


def test_a_payload_can_be_streamed_from_a_pull_callback() -> None:
    # F7: what makes "large payloads over little buffers" true rather than half-true - the whole
    # payload never exists in RAM at either end.
    source = bytes((i * 3) & 0xFF for i in range(PAYLOAD_SIZE * 2 + 3))
    got: list[Any] = []

    def pull(chunk: int, buf: memoryview) -> int:
        start = (chunk - 2) * PAYLOAD_SIZE
        part = source[start : start + len(buf)]
        buf[: len(part)] = part
        return len(part)

    def remember(cmd_id: int) -> "tuple[bool, int | None]":
        return True, len(source)

    pair = Pair(get_callback=echo_get(b""), set_callback=remember)
    assert run(pair.setup()) is True

    async def scenario() -> ListenResult:
        listener = asyncio.create_task(pair.responder.uart_listen())
        got.append(await pair.initiator.uart_set_stream(0x60, len(source), pull))
        return await asyncio.wait_for(listener, 10)

    result = run(scenario(), limit=25)
    assert got == [True]
    assert bytes(result.payload) == source


def test_a_payload_can_be_streamed_into_a_push_callback() -> None:
    source = bytes(range(PAYLOAD_SIZE * 2))
    chunks_seen: list[bytes] = []

    def push(chunk: int, buf: memoryview) -> bool:
        chunks_seen.append(bytes(buf))
        return True

    pair = run(build_pair(get_callback=echo_get(source), set_callback=accept_set()))
    written = run(pair.with_listener(pair.initiator.uart_get_stream(1, push)))
    assert written == len(source)
    assert b"".join(chunks_seen) == source


def test_a_pull_callback_short_filling_a_non_final_chunk_aborts_locally() -> None:
    # F7.1: the peer would reject it anyway (D4.5), but the fault is this side's and must be
    # caught before anything is sent.
    def stingy(chunk: int, buf: memoryview) -> int:
        return 1  # always one byte, however much the chunk needs

    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set_stream(1, PAYLOAD_SIZE * 2, stingy)), limit=20) is False


def test_a_pull_callback_returning_a_wrong_shape_is_guarded() -> None:
    # F7.4: the same escape as F4.2/F4.3, so it gets the same guard.
    def wrong(chunk: int, buf: memoryview) -> str:
        return "lots"

    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set_stream(1, 4, wrong)), limit=20) is False


def test_a_push_callback_failing_mid_train_aborts() -> None:
    # F7.3: half the payload is stored otherwise, with the caller none the wiser.
    def refuse_second(chunk: int, buf: memoryview) -> bool:
        return chunk < 3

    pair = run(build_pair(get_callback=echo_get(bytes(PAYLOAD_SIZE * 3)), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_get_stream(1, refuse_second)), limit=20) is None


def test_a_streamed_total_size_must_be_declared() -> None:
    # F7.6: CHUNKS has to be in chunk 1, so an unknown length is out of scope by design.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.initiator.uart_set_stream(1, -1, lambda chunk, buf: 0)) is False


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
