"""Flash-tier automated tests: the UART message protocol across the bench board's permanent UART crossover jumper -
real timing, real peripheral behaviour and real poll latency, the three things no fake reproduces (SPECIFICATION.md
Parts E.6 and J.7), each crossover script with no CRC and with CRC16 over the same jumper."""

import sys
from pathlib import Path
from typing import Protocol

import bench_facts
import pytest
from harness import DEVICE_SCRIPTS_DIR, MEMORY_ERROR_MARKERS, Board, bench_device, parse_facts

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from buildgen.validate import module_int_const
from tests._error_codes import code


class _ResultNote(Protocol):
    # The root conftest's result_note fixture.
    def __call__(self, text: str, *, recovery: bool = False) -> None: ...


COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("uart_link", "machine_uart", "uart_comm_hazard", "uart_field_sweep")

# Every script imports asy_uart_comm, which the bench device's TOML uart_link instances pull in through
# asy_uart_link_driver.py. A build lacking the module fails these tests, never skips them: the guard names the cause.
_MISSING_MODULE = "ImportError: no module named 'asy_uart_comm'"
_CRC_MODES = ("none", "crc16")
_SRC = Path(__file__).resolve().parents[2] / "src"
_CMD_SET = module_int_const(_SRC, "asy_uart_comm.py", "CMD_SET")
_UID_MAX = module_int_const(_SRC, "asy_uart_comm.py", "_UID_MAX")
# A first-chunk SET's verdict per field (J.3/J.4), the rule tests/test_digital_twin_uart_field_sweep.py checks at L2.
_LEGAL = {"cmd": lambda v: v == _CMD_SET, "size": lambda v: v == 1, "chunks": lambda v: v >= 2, "cur_chunk": lambda v: v == 1, "uid": lambda v: v <= _UID_MAX}
_FLASH_WINDOW_MAX_US = 400000  # W25Q16JV tSE max: the longest interrupts-off stretch the ring must hold (the script's own)
_RING_LINK_TRANSACTIONS = 5

# @tunable l3.uart_crossover_script_timeout_s = 120.0
_SCRIPT_TIMEOUT_S = 120.0
# @tunable l3.uart_crossover_long_script_timeout_s = 180.0
_LONG_SCRIPT_TIMEOUT_S = 180.0
# Sized from the twin run (12 s with the stalled-TX settle): four hazard classes, the boundary set at 300 ms a verdict.
# @tunable l3.uart_crossover_hazards_timeout_s = 120.0
_HAZARDS_TIMEOUT_S = 120.0


def _clean_counts(facts: "dict[str, object]") -> None:
    counts = _dict(facts["error_counts"])
    dirty = {name: entry for name, entry in counts.items() if _dict(entry)["count"]}
    assert not dirty, f"errors counted on a clean link: {dirty}"


def _codes(log: object) -> "list[int]":
    # The error numbers a log_record() fact holds.
    return [entry[1] for entry in _list(_dict(log)["entries"]) if isinstance(entry, list) and isinstance(entry[1], int)]


def _dict(value: object) -> "dict[str, object]":
    assert isinstance(value, dict), value
    return value


def _int(value: object) -> int:
    assert isinstance(value, int) and not isinstance(value, bool), value
    return value


def _list(value: object) -> "list[object]":
    assert isinstance(value, list), value
    return value


def _ring_holds_the_flash_window() -> None:
    # The receiving bus's ring against what a continuous sender puts in it during the longest flash window.
    facts = bench_facts.build(bench_device())
    bus = _dict(_dict(facts["bus"])[str(_dict(_dict(facts["instances"])["uart_link_resp"])["bus"])])
    ring, baudrate = bus["rx_ring"], bus["baudrate"]
    assert isinstance(ring, int) and isinstance(baudrate, int), bus
    need = _FLASH_WINDOW_MAX_US * (baudrate // 10) // 1000000
    if ring < need:
        pytest.fail(f"the bench TOML's rx_ring {ring} B cannot hold the {_FLASH_WINDOW_MAX_US // 1000} ms flash window ({need} B at {baudrate} baud): size it in the device TOML")


def _run_or_fail(board: Board, script: str, timeout_s: float, *, crc_mode: str = "none", state: "str | None" = None) -> "dict[str, object]":
    # The script's facts; an allocation failure anywhere in its output fails the test whatever the facts say.
    path = DEVICE_SCRIPTS_DIR / script
    try:
        output = board.run_isolated(path, timeout_s=timeout_s, CRC_MODE=crc_mode) if state is None else board.run_isolated(path, timeout_s=timeout_s, CRC_MODE=crc_mode, STATE=state)
    except Exception as e:  # HardwareTestFailureError carries the device-side traceback in its text
        if _MISSING_MODULE in str(e):
            pytest.fail("this firmware does not contain asy_uart_comm - the bench device's TOML uart_link instances normally pull it in, so check how this firmware was built")
        raise
    marked = [line for line in output.splitlines() if any(marker in line for marker in MEMORY_ERROR_MARKERS)]
    assert not marked, f"{script} printed an allocation failure:\n" + "\n".join(marked)
    return parse_facts(output)


@pytest.mark.parametrize("crc_mode", _CRC_MODES)
def test_get_and_set_and_a_multi_chunk_train_cross_the_jumper(board: Board, crc_mode: str) -> None:
    # One Python instance as initiator and one as responder interoperating is a required property of this protocol, and
    # the jumper is where it is physically true; the maximum train each way, and an over-cap train refused unallocated.
    facts = _run_or_fail(board, "uart_crossover_exchange.py", _SCRIPT_TIMEOUT_S, crc_mode=crc_mode)
    assert facts["crc_mode"] == crc_mode, facts
    _setup_ok(facts)
    for key in ("get_answer_ok", "set_ok", "empty_set_ok", "max_set_ok", "max_set_intact", "max_get_intact"):
        assert facts[key] is True, f"{key} failed across the jumper ({facts['train_bytes']}-byte train, {facts['max_train_bytes']}-byte maximum): {facts}"
    _clean_counts(facts)
    assert facts["capped_setup"] is True and facts["over_cap_refused"] is True, f"the over-cap train was not refused: {facts}"
    assert _codes(facts["over_cap_log"]) == [code("E", "UART_TRANSFER_CAP")], f"the refusal was not logged exactly once: {facts['over_cap_log']}"
    assert facts["largest_block_after"] == facts["largest_block_before"], f"the refused train moved the largest free block: {facts['largest_block_before']} -> {facts['largest_block_after']}"


@pytest.mark.parametrize("crc_mode", _CRC_MODES)
def test_silence_and_desync_recover_within_the_resync_bound_and_a_mismatch_fails_loudly(board: Board, crc_mode: str) -> None:
    # The two faults the link recovers from, timed against the protocol's resync bound, and a payload_size mismatch,
    # which no peer negotiates (J.6): it fails with a logged error rather than delivering a wrong-length payload.
    facts = _run_or_fail(board, "uart_crossover_recovery.py", _LONG_SCRIPT_TIMEOUT_S, crc_mode=crc_mode)
    assert facts["crc_mode"] == crc_mode, facts
    _setup_ok(facts)
    _setup_ok(facts, "mismatch_setup")
    bound = facts["resync_bound_ms"]
    assert isinstance(bound, int), facts
    for case in ("silence", "desync"):
        recovery = facts[f"{case}_recovery_ms"]
        assert facts[f"{case}_failed"] is True, f"a transfer during the {case} fault reported success: {facts}"
        assert isinstance(recovery, int) and recovery <= bound, f"the link did not recover from {case} within the resync bound of {bound} ms (src/asy_uart_comm.py's consts): {recovery}"
    assert set(_codes(facts["desync_log"])) & {code("E", "UART_NO_ACK"), code("E", "UART_FRAME_INVALID")}, f"the desync left no frame or ACK error: {facts['desync_log']}"
    assert facts["system_task_exceptions"] == [], f"a task ended with an exception under the faults: {facts['system_task_exceptions']}"
    assert facts["mismatch_failed"] is True, f"a payload_size mismatch was not detected: {facts}"
    assert _codes(facts["mismatch_log"]), f"a payload_size mismatch produced no logged error at all: {facts['mismatch_log']}"


def test_the_shipped_driver_never_holds_the_loop_for_a_frame_still_arriving(board: Board) -> None:
    # SPECIFICATION.md Part F.5.8 through asy_uart_driver itself: readiness comes before the whole frame is in the ring
    # (the hazard's precondition), the driver's own synchronous copies stay short, and the unclamped control stalls.
    facts = _run_or_fail(board, "uart_driver_read_never_blocks_the_loop.py", _SCRIPT_TIMEOUT_S)
    span_max, first, frame = facts["span_max_us"], facts["first_ready_bytes"], facts["frame"]
    assert isinstance(span_max, int) and isinstance(first, int) and isinstance(frame, int), facts
    assert facts["ring_setup"] is True, facts
    assert 0 <= first < frame, f"the driver first reported readiness with {first} of {frame} bytes in the ring - this board does not show the hazard"
    for key in ("driver_span_us", "readline_span_us"):
        span = facts[key]
        assert isinstance(span, int) and span <= span_max, f"{key}: one of the driver's own copies took {span} us, over the {span_max} us bound (wire time {facts['wire_us']} us)"
    control = facts["control_span_us"]
    assert isinstance(control, int) and control >= span_max, f"the unclamped control read took only {control} us - the measurement is not exercising the stall"
    assert all(_list(facts["intact"])) and facts["readline_intact"] is True, f"a frame did not arrive intact through the driver: {facts}"


def test_an_idle_listener_polls_at_the_idle_rate_not_the_transaction_rate(board: Board) -> None:
    # SPECIFICATION.md Part F.5.9. Counted, never timed: a poll-round count is a property of the code, while throughput
    # on this board moves with heap state (Part E.7).
    facts = _run_or_fail(board, "uart_idle_poll_rate.py", _LONG_SCRIPT_TIMEOUT_S)
    _setup_ok(facts)
    fast = min(_int(n) for n in _list(facts["fast_rounds"]))
    idle = max(_int(n) for n in _list(facts["idle_rounds"]))
    expected, factor, ratio = _int(facts["expected_idle_rounds"]), _int(facts["expected_rounds_factor"]), _int(facts["min_ratio"])
    assert not any(_list(facts["listener_cancelled"])), f"a listener outlived comm.clear() and was cancelled (fast, idle, fast, idle): {facts['listener_cancelled']}"
    assert idle, "an idle listener performed no poll rounds at all - it is not waiting where this test thinks"
    assert fast // idle >= ratio, f"the idle rate cut poll rounds only {fast // idle}x ({fast} -> {idle}), under the {ratio}x floor"
    # A listener that stopped polling would pass the ratio too, and never notice a frame: the rate tracks poll_idle_ms.
    assert expected // factor <= idle <= expected * factor, f"the idle listener polled {idle} times in {facts['sample_ms']} ms, not near the expected {expected}"


@pytest.mark.parametrize("crc_mode", _CRC_MODES)
def test_comm_hazards_are_serialised_refused_or_recovered(board: Board, crc_mode: str, result_note: _ResultNote) -> None:
    # H1a two initiations on one instance, H1b clear()/cancel_read_timeout() racing a transaction, H2 both ends
    # transmitting (out of contract, J.2), H3 the first-chunk boundary values, and a stalled TX whose cause is recorded.
    facts = _run_or_fail(board, "uart_comm_hazards.py", _HAZARDS_TIMEOUT_S, crc_mode=crc_mode)
    assert facts["crc_mode"] == crc_mode, facts
    _setup_ok(facts)
    h1a = _dict(facts["h1a"])
    assert sorted(result is True for result in _list(h1a["results"])) == [False, True], f"two initiations at once were not one completion and one refusal: {h1a}"
    assert code("E", "UART_REENTRANT") in _codes(h1a["log"]), f"the second initiation was not refused as re-entrant: {h1a['log']}"
    assert h1a["frames_seen"] and h1a["frames_whole"] == h1a["frames_seen"], f"the responder read a frame that did not parse whole: {h1a}"
    for race in _list(facts["h1b"]):
        assert _dict(race)["next_ok"] is True, f"the transaction after a racing call did not succeed: {race}"
    h2 = _dict(facts["h2"])
    assert h2["failed"] is True and code("E", "UART_PEER_INITIATED") in _codes(h2["log"]), f"a crossing GET was not logged as peer-initiated: {h2}"
    assert h2["recovered"] is True, f"the link did not recover within two attempts after both ends transmitted: {h2}"
    wrong = [(sweep["field"], value, accepted) for sweep in map(_dict, _list(facts["h3"])) for value, accepted in map(_list, _list(sweep["verdicts"])) if accepted != _LEGAL[str(sweep["field"])](value)]
    assert not wrong, f"boundary values answered against J.3/J.4 (field, value, ACKed): {wrong}"
    assert all(_dict(sweep)["clean_after"] is True for sweep in _list(facts["h3"])), f"a clean exchange after a field's sweep failed: {facts['h3']}"
    stalled = _dict(facts["stalled_tx"])
    result_note(f"stalled TX (crc {crc_mode}): failed {stalled['failed']}, logged {_codes(stalled['log'])}, recovered in {stalled['attempts']}")
    assert stalled["failed"] is True and stalled["recovered"] is True, f"the stalled TX did not fail cleanly and recover within two attempts: {stalled}"


@pytest.mark.parametrize("crc_mode", _CRC_MODES)
def test_the_link_keeps_transferring_while_every_other_subsystem_is_busy(board: Board, crc_mode: str) -> None:
    # The realistic worst case for a stop-and-wait link sharing one core, asserted both ways: the link keeps progressing
    # with echo-checked multi-chunk SETs, and it did not do so by starving anything else.
    facts = _run_or_fail(board, "uart_link_under_concurrent_system_load.py", _LONG_SCRIPT_TIMEOUT_S, crc_mode=crc_mode)
    assert facts["crc_mode"] == crc_mode and facts["gc_threshold"] == -1, facts
    _setup_ok(facts)
    bounds = _dict(facts["bounds"])
    transfers, worst = _int(facts["transfers"]), _int(facts["worst_rtt_ms"])
    assert transfers >= _int(bounds["min_transfers"]), f"only {transfers} transfers completed under load, under the {bounds['min_transfers']} floor"
    assert facts["link_failures"] == 0, f"{facts['link_failures']} transfer(s) failed while the rest of the system was busy"
    assert worst <= _int(bounds["max_rtt_ms"]), f"worst round trip {worst} ms under load, past {bounds['max_rtt_ms']} ms (timeout {facts['timeout_ms']} ms)"
    assert facts["set_total"] and facts["echo_intact"] == facts["set_total"], f"echo SETs did not come back intact: {facts['echo_mismatch']}"
    _clean_counts(facts)
    load = _dict(facts["load"])
    starved = {name: n for name, n in load.items() if name not in ("i2c_errors", "fram_absent") and not n}
    assert not starved, f"a subsystem was starved by the link: {starved}"
    assert load["fram_absent"] == 0, f"the FRAM went unanswered {load['fram_absent']} time(s) under the load"
    assert _dict(facts["alloc_failures"])["total"] == 0, f"a churn allocation failed: {facts['alloc_failures']}"
    third, end = _int(facts["heap_at_third"]), _int(facts["heap_at_end"])
    assert not third or end - third <= _int(bounds["heap_growth_max_bytes"]), f"the heap grew {end - third} bytes over the last two thirds of the run"


def _setup_ok(facts: "dict[str, object]", key: str = "setup") -> None:
    setup = facts[key]
    assert setup is True or (isinstance(setup, dict | list) and all(setup.values() if isinstance(setup, dict) else setup)), f"a setup() was refused: {setup}"


@pytest.mark.parametrize("crc_mode", _CRC_MODES)
def test_no_frame_is_lost_while_interrupts_are_off(board: Board, crc_mode: str, result_note: _ResultNote) -> None:
    # Interrupts held off for the flash windows while the other UART streams through DMA: within the ring's bound no
    # frame is lost and no overrun shows; past it the overrun is reported and every frame after the resync is intact.
    _ring_holds_the_flash_window()
    facts = _run_or_fail(board, "uart_dma_ring_interrupts_off.py", _LONG_SCRIPT_TIMEOUT_S, crc_mode=crc_mode)
    _setup_ok(facts)
    result_note(f"heap {facts['heap']}")
    bound = facts["ring_bound_us"]
    assert isinstance(bound, int), facts
    for window in map(_dict, _list(facts["windows"])):
        assert window["streamed"] is True, f"the sender's DMA stream did not finish: {window}"
        window_us = window["window_us"]
        assert isinstance(window_us, int), window
        if window_us < bound:
            assert window["frames_intact"] == window["frames_sent"] and window["uartrsr_oe"] is False and window["overrun_detected"] == 0, f"a frame was lost within the ring's {bound} us bound: {window}"
        else:
            assert isinstance(window["overrun_detected"], int) and window["overrun_detected"] >= 1, f"no overrun reported past the ring's {bound} us bound: {window}"
            assert window["after_intact"] == window["after_sent"], f"frames after the overrun's resync were not intact: {window}"
    rxdmae = _dict(facts["rxdmae_window"])
    assert rxdmae["oe_set"] is True and rxdmae["first_failed"] is True and rxdmae["next_ok"] is True, f"the RXDMAE-off overrun did not fail one transaction and recover: {rxdmae}"


@pytest.mark.parametrize("crc_mode", _CRC_MODES)
def test_a_soft_reset_during_traffic_leaves_no_running_ring(board: Board, crc_mode: str) -> None:
    # The harness's trailing soft reset lands while frames stream into the ring; afterwards the same DMA channels are
    # free and a fresh buffer stays untouched (the rp2.DMA finaliser and soft reset, ports/rp2/rp2_dma.c at v1.29.0).
    before = _run_or_fail(board, "uart_dma_ring_interrupts_off.py", _SCRIPT_TIMEOUT_S, crc_mode=crc_mode, state="soft_reset")
    _setup_ok(before)
    after = _run_or_fail(board, "uart_dma_ring_interrupts_off.py", _SCRIPT_TIMEOUT_S, crc_mode=crc_mode, state="after_soft_reset")
    assert after["channels_free"] == before["channels"], f"the DMA channels the ring held were not free after the soft reset: {before['channels']} -> {after['channels_free']}"
    assert after["streamed"] is True and after["ring_untouched"] is True, f"memory was written after the soft reset: {after}"
    board.hard_reset()


@pytest.mark.parametrize("crc_mode", _CRC_MODES)
def test_a_break_mid_frame_fails_that_transaction_only(board: Board, crc_mode: str, result_note: _ResultNote) -> None:
    facts = _run_or_fail(board, "uart_dma_ring_interrupts_off.py", _SCRIPT_TIMEOUT_S, crc_mode=crc_mode, state="break")
    _setup_ok(facts)
    broken = _dict(facts["break"])
    # 0 here: DMA reads leave UARTRSR's FE and BE unset, so the frame fails only by CRC or length (C.3.2).
    result_note(f"break (crc {crc_mode}): rsr_error_counted {broken['rsr_error_counted']}")
    assert broken["first_ok"] is True and broken["break_frame_failed"] is True and broken["next_frame_ok"] is True, f"a break did not fail exactly its own transaction: {broken}"


@pytest.mark.persistence_write
@pytest.mark.parametrize("crc_mode", _CRC_MODES)
def test_a_real_config_write_during_traffic_loses_no_frame(board: Board, crc_mode: str, result_note: _ResultNote) -> None:
    # One owned flash write: a scratch config flush, the flash driver's own interrupts-off window, during the stream.
    facts = _run_or_fail(board, "uart_dma_ring_interrupts_off.py", _LONG_SCRIPT_TIMEOUT_S, crc_mode=crc_mode, state="config_write")
    _setup_ok(facts)
    written = _dict(facts["config_write"])
    result_note(f"config flush {written['flush_us']} us")
    assert written["streamed"] is True and written["frames_intact"] == written["frames_sent"] and written["uartrsr_oe"] is False, f"a frame was lost across a real flash write: {written}"


@pytest.mark.persistence_write
@pytest.mark.parametrize("crc_mode", _CRC_MODES)
def test_link_transactions_during_config_writes_are_recorded(board: Board, crc_mode: str, result_note: _ResultNote) -> None:
    # Five owned flash writes, one per transaction: a crossing fails visibly, never corrupts; the figures fill F.3.
    facts = _run_or_fail(board, "uart_dma_ring_interrupts_off.py", _LONG_SCRIPT_TIMEOUT_S, crc_mode=crc_mode, state="config_write_link")
    _setup_ok(facts)
    link = _dict(facts["config_write_link"])
    result_note(f"transactions failed {link['transactions_failed']}, flushes {link['flush_us']} us")
    assert _int(link["transactions_ok"]) + _int(link["transactions_failed"]) == _RING_LINK_TRANSACTIONS, link
    assert link["wrong_payloads"] == 0, f"a transaction crossing a flash write delivered a wrong payload: {link}"
