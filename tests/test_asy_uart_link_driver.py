"""UARTLinkDriver: the bench exerciser's transfers, failure counts and banner across a real UARTComm pair in both
CRC modes, its task starters and its FRAM-backed log."""

import asyncio
import json
import select
import sys
import time

# scripts/test.sh's MICROPYPATH excludes ext/, so the real vendored ext/microdot.py the status route is built on needs
# this, as in tests/test_asy_webserver_service.py.
sys.path.insert(0, "ext")

from _async_harness import cancel, run
from _cancel_sweep import assert_unlocked, cancel_at_each_await
from _error_codes import code
from _fake_time import DrivenTime
from _fast_sleep import FastAsyncSleep
from _generated_tree import devices, require_fresh
from _src_const import src_bytes, src_int
from _twin_devices import bus_keywords, device_with, wiring_plan
from _uart_comm_harness import POLL_WAIT_MS, RUN_LIMIT_S, TIMEOUT_MS, PollRoundClock, awaited_with_listener, copied_out, transfer_limits
from _uart_comm_hazard_common import register_both_crc_modes
from _write_counters import WriteCountingOpen
from machine import UART as FakeUART
from machine import LinkPoller, UARTLink
from microdot import Microdot
from rp2 import DMA

import asy_config_manager
import asy_uart_comm
import asy_uart_driver
import asy_uart_link_driver
import asy_webserver_service
from asy_base_classes import COUNTER_CAP, PieceBuffer, RegionBuffer
from asy_config_manager import FAILED, INVALID, VALID
from asy_crc_checks import CRC16
from asy_print_log import LogConfig, PrintLogHistory, PrintLogHistoryStore, make_logger
from asy_uart_comm import CMD_SET, ROLE_INITIATOR, ROLE_RESPONDER
from asy_uart_driver import UART
from asy_uart_link_driver import UARTLinkDriver
from asy_webserver_service import RouteSources, ServingLimits, WebserverService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import TypedDict, TypeVar

    from _uart_comm_hazard_common import CrcMaker

    from asy_base_classes import JsonDict
    from asy_crc_checks import CRCBase

    T = TypeVar("T")

    class PollRates(TypedDict, total=False):
        # The poll keywords a UART construction passes; one it leaves out is the driver's own default.
        poll_wait_ms: int
        poll_idle_ms: int

PAYLOAD_SIZE = 8
_HARNESS_RATES: "PollRates" = {"poll_wait_ms": POLL_WAIT_MS, "poll_idle_ms": POLL_WAIT_MS}
# @tunable l1.asy_uart_link_driver_round_poll_s = 0.005
_ROUND_POLL_S = 0.005
# @tunable l1.asy_uart_link_driver_ticker_step_ms = 1
_TICKER_STEP_MS = 1
# @tunable l1.asy_uart_link_driver_task_end_rounds = 200
_TASK_END_ROUNDS = 200
# One host deschedule longer than the reply budget, planted at the second UART sleep: on the wall clock it expires a
# wait before the peer runs and a correct exchange fails; on the poll-round clock it cannot (SPECIFICATION.md Part J.7).
_STALL_AFTER = 2
_STALL_MS = TIMEOUT_MS + 10
# Counts past one exercise round's turns: the later ones cancel inside the loop's real 1 s period sleep.
_ROUND_SWEEP_TURNS = 40
_BANNER: bytes = src_bytes("src/asy_uart_link_driver.py", "_BANNER")


class Pair:
    # One initiator and one responder UARTLinkDriver across a real crossover link - the same
    # shape tests/_uart_comm_harness.py's own Pair uses for bare UARTComm objects, one layer up.
    def __init__(self, payload_size: int = PAYLOAD_SIZE, timeout: int = TIMEOUT_MS, crc: "CrcMaker" = None, rates: "tuple[PollRates, PollRates] | None" = None) -> None:
        # `crc` builds one CRC per bus (CRCBase carries state), so both ends agree; None leaves the buses without one.
        # `rates` polls the initiator's bus and the responder's as given; None polls both at the harness's POLL_WAIT_MS.
        rates_a, rates_b = rates if rates is not None else (_HARNESS_RATES, _HARNESS_RATES)
        DMA.reset_registry()  # each link's ring holds two of the twelve channels: a later pair in one test frees them
        self.uart_a = UART(0, tx_pin=0, rx_pin=1, crc=None if crc is None else crc(), **rates_a)
        self.uart_b = UART(1, tx_pin=8, rx_pin=9, crc=None if crc is None else crc(), **rates_b)
        self.fake_a: FakeUART = self.uart_a._uart  # type: ignore[assignment]
        self.fake_b: FakeUART = self.uart_b._uart  # type: ignore[assignment]
        self.link = UARTLink(self.fake_a, self.fake_b)
        self.fake_a.rx_rate = self.fake_b.rx_rate = float("inf")  # bytes land at once, not on the fake clock
        # Bounded stand-in, never a real select.poll(): the fake's readiness must be scripted, not polled in real time (CLAUDE.md "Known hang cause").
        # Only TX polls.
        self.uart_a.poller = LinkPoller(self.fake_a, mask=select.POLLOUT)  # type: ignore[assignment]
        self.uart_b.poller = LinkPoller(self.fake_b, mask=select.POLLOUT)  # type: ignore[assignment]
        limits = transfer_limits(payload_size=payload_size, timeout=timeout)
        self.initiator = UARTLinkDriver(self.uart_a, ROLE_INITIATOR, limits=limits, name_ext="init")
        self.responder = UARTLinkDriver(self.uart_b, ROLE_RESPONDER, limits=limits, name_ext="resp")

    async def _listen_rounds(self, rounds: int) -> None:
        for _ in range(rounds):
            await self.responder._comm.uart_listen()

    async def setup(self) -> bool:
        return await self.initiator.setup() and await self.responder.setup()

    async def with_listener(self, work: "Coroutine[object, object, T]", rounds: int = 1, *, listener_may_stall: bool = False) -> "T":
        # The harness's rule: a stalled responder fails the exchange unless the test declares it.
        listener = asyncio.create_task(self._listen_rounds(rounds))
        return await awaited_with_listener(work, listener, rounds, may_stall=listener_may_stall)


def _check_a_corrupted_frame_counts_one_failure_and_the_next_transfer_succeeds(crc: "CrcMaker") -> None:
    # One byte of the banner answer flipped on the wire: the CRC rejects its frame, the round counts one failure,
    # and the next round's answer arrives intact and counts a transfer.
    async def go() -> None:
        probe = await build_pair(crc=crc)
        await _one_exercise_round(probe)
        wire = bytes(probe.link.direction_from(probe.fake_b).wire_log)
        offset = wire.find(_BANNER[:4])  # the answer's first payload byte, wherever the train puts it
        assert offset > 0 and (probe.initiator._transfers, probe.initiator._failures) == (1, 0), wire
        pair = await build_pair(crc=crc)
        pair.link.direction_from(pair.fake_b).corrupt_indices = {offset: 0xFF}
        await _one_exercise_round(pair)
        assert (pair.initiator._transfers, pair.initiator._failures) == (0, 1)
        pair.link.direction_from(pair.fake_b).corrupt_indices = {}
        await _one_exercise_round(pair)
        assert (pair.initiator._transfers, pair.initiator._failures) == (1, 1)

    run(go(), RUN_LIMIT_S)


def test_name_resolution_matches_instance_name_convention() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    plain = UARTLinkDriver(driver, ROLE_INITIATOR)
    assert plain.name == "UART"
    extended = UARTLinkDriver(driver, ROLE_INITIATOR, name_ext="init")
    assert extended.name == "UART_init"
    assert extended.pr.name == "UART_init"


def test_initiator_task_starters_include_exercise_loop() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    initiator = UARTLinkDriver(driver, ROLE_INITIATOR)
    starters = initiator.get_task_starters()
    assert starters == [initiator.start_asy_exercise], starters  # UARTComm's own list is empty for an initiator - see its own get_task_starters()

    async def start_and_end() -> None:  # a starter makes its task inside the loop, as start_tasks() calls it
        await cancel(starters[0]())

    run(start_and_end(), RUN_LIMIT_S)


def test_responder_task_starters_are_the_listen_loop_only() -> None:
    driver = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)

    def get_cb(cmd_id: int) -> "tuple[bool, bytes | None]":
        return False, None

    def set_cb(cmd_id: int) -> "tuple[bool, int | None]":
        return False, None

    responder = UARTLinkDriver(driver, ROLE_RESPONDER)
    responder._get_callback = get_cb  # type: ignore[method-assign]
    responder._set_callback = set_cb  # type: ignore[method-assign]
    starters = responder.get_task_starters()
    assert starters == [responder._comm.start_asy_listen], starters  # the listen loop, not an exercise loop

    async def start_and_end() -> None:
        await cancel(starters[0]())

    run(start_and_end(), RUN_LIMIT_S)


def test_the_readiness_flag_follows_the_inner_setup() -> None:
    # False until setup() succeeds; a failed setup (no bus, refused at construction) leaves it False.
    pair = Pair()
    before = pair.initiator.initialized
    assert run(pair.initiator.setup(), RUN_LIMIT_S) is True
    assert (before, pair.initiator.initialized) == (False, True)
    refused = UARTLinkDriver(None, ROLE_INITIATOR, limits=transfer_limits(payload_size=PAYLOAD_SIZE, timeout=TIMEOUT_MS), name_ext="none")
    assert run(refused.setup(), RUN_LIMIT_S) is False
    assert refused.initialized is False


def test_timer_starters_are_always_empty() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    initiator = UARTLinkDriver(driver, ROLE_INITIATOR)
    assert initiator.get_timer_starters() == []


def test_get_error_sources_and_loggers_delegate_to_inner_comm() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    initiator = UARTLinkDriver(driver, ROLE_INITIATOR)
    assert initiator.get_error_sources() == [initiator._comm]
    assert initiator.get_loggers() == [initiator._comm.pr]


def test_get_link_status_starts_at_zero() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    initiator = UARTLinkDriver(driver, ROLE_INITIATOR)
    status = run(initiator.get_link_status(), RUN_LIMIT_S)
    assert status == {"Transfers": 0, "Failures": 0}


def test_reset_error_counter_leaves_the_link_counters() -> None:
    # ResetErrors clears error state only: the published counts are "since boot" (SPECIFICATION.md Part D.10).
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    initiator = UARTLinkDriver(driver, ROLE_INITIATOR)
    initiator._transfers = 5
    initiator._failures = 2
    run(initiator.pr.err_s("bench-side fault", errno=7), RUN_LIMIT_S)
    assert 7 in run(initiator.get_error_counter(), RUN_LIMIT_S)[initiator.name]["ErrNum"]
    assert run(initiator.reset_error_counter(), RUN_LIMIT_S) is True
    assert (initiator._transfers, initiator._failures) == (5, 2)
    after = run(initiator.get_error_counter(), RUN_LIMIT_S)[initiator.name]
    assert (after["ErrCount"], 7 in after["ErrNum"]) == (0, False)


def test_reset_error_counter_answers_the_comms_own_result() -> None:
    # The link's history lives in its UARTComm: a failed history write there is this reset's answer.
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    initiator = UARTLinkDriver(driver, ROLE_INITIATOR)

    async def refused() -> bool:
        return False

    initiator._comm.reset_error_counter = refused  # type: ignore[method-assign]
    assert run(initiator.reset_error_counter(), RUN_LIMIT_S) is False


def _check_a_crossing_whose_uid_aliases_the_peers_ack_fails_as_peer_initiated(crc: "CrcMaker") -> None:
    # The other outcome: with the SET's first uid the raw GET's own 0, the GET's ACK confirms it and the peer's answer
    # lands where the next ACK is due. The SET still fails and the link still recovers.
    pair = Pair(crc=crc, rates=_SHIPPED_RATES)
    errnos = _recorded_errnos(pair.initiator._comm)
    assert run(pair.setup(), RUN_LIMIT_S), "Pair.setup() failed"
    link = pair.initiator
    bus = link._uart
    assert bus is not None
    link._comm._uid = _UID_MAX  # the uid before 0: the SET's first frame goes out as uid 0
    got: list[object] = []

    async def go(clock: DrivenTime) -> None:
        listen = pair.responder._comm.start_asy_listen()

        async def crossing() -> None:
            got.append(await link._cross_both_ends(bytearray(link._frame + bus.crc.length())))

        task = asyncio.create_task(crossing())
        await clock.run_until(task.done, _HAZARD_RUN_VIRTUAL_MS)
        listen.cancel()
        await clock.run_until(listen.done, 0)

    asy_uart_link_driver.time = time  # type: ignore[attr-defined]
    try:
        with DrivenTime(asy_uart_driver, asy_uart_comm, asy_uart_link_driver, sleeps=True) as clock:
            run(go(clock), RUN_LIMIT_S)
    finally:
        del asy_uart_link_driver.time  # type: ignore[attr-defined]
    assert got and got[0] == [True, False, 1, True], f"the aliased crossing did not fail once and recover at the first try: {got}"
    assert errnos == [code("E", "UART_PEER_INITIATED")], f"the aliased crossing's fault is not the peer's answer where an ACK was due: {errnos}"


def _check_a_hazard_run_reports_every_verdict_then_returns_to_the_echo(crc: "CrcMaker") -> None:
    # The live shape: the responder's own listen loop and the initiator's exercise loop, the request between two rounds.
    pair = Pair(crc=crc, rates=_SHIPPED_RATES)
    errnos, peer = _recorded_errnos(pair.initiator._comm), _recorded_errnos(pair.responder._comm)
    assert run(pair.setup(), RUN_LIMIT_S), "Pair.setup() failed"  # on the real clock: inside the block nothing would advance it

    async def go(clock: DrivenTime) -> "tuple[int, JsonDict]":
        link = pair.initiator
        tasks = (pair.responder._comm.start_asy_listen(), link.start_asy_exercise())
        await clock.run_until(lambda: link._transfers == 1, _EXERCISE_PERIOD_MS)
        assert link.request_hazard_run() is True
        elapsed = await clock.run_until(lambda: link._hazard_runs == 1 and not link._hazard_pending, _HAZARD_RUN_VIRTUAL_MS)
        await clock.run_until(lambda: link._transfers == 2, _EXERCISE_PERIOD_MS)
        assert link._failures == 0, f"the hazard run counted into the link's failures, or the echo did not return: {link._failures}"
        report = await link.get_hazard_report()
        for task in tasks:
            task.cancel()
        await clock.run_until(lambda: tasks[0].done() and tasks[1].done(), 0)
        return elapsed, report

    # DrivenTime swaps each module's `time` and `asyncio`; this module reads only asyncio, so it lends a `time` for the block.
    asy_uart_link_driver.time = time  # type: ignore[attr-defined]
    try:
        with DrivenTime(asy_uart_driver, asy_uart_comm, asy_uart_link_driver, sleeps=True) as clock:
            elapsed, report = run(go(clock), RUN_LIMIT_S)
    finally:
        del asy_uart_link_driver.time  # type: ignore[attr-defined]
    json.dumps(report)  # the report is what a status read serialises
    assert report["Runs"] == 1 and report["Pending"] is False, report
    last = report["Last"]
    assert isinstance(last, dict), report
    two = last["TwoInitiations"]
    assert two in _ONE_COMPLETION, f"two initiations at once were not one completion and one refusal: {last}"
    crossing = last["Crossed"]
    assert isinstance(crossing, list) and len(crossing) == 4, last
    wrote, crossed, attempts, recovered = crossing
    assert wrote is True and crossed is False, f"the SET crossing the peer's answer did not fail: {crossing}"
    # The peer ACKs the raw GET (uid 0) where the SET's ACK is due, a stale uid refused as no ACK (J.3), and finds the SET
    # where its own ACK is due, as peer-initiated. No fault follows: the first recovery try is clean.
    assert errnos == [code("E", "UART_REENTRANT"), code("E", "UART_NO_ACK")], f"not the refusal and the crossing's stale ACK alone: {errnos}"
    assert peer[:1] == [code("E", "UART_PEER_INITIATED")], f"the peer did not log the crossing as peer-initiated: {peer}"
    assert recovered is True and attempts in range(1, _HAZARD_RECOVERY_ATTEMPTS + 1), f"the link did not recover within {_HAZARD_RECOVERY_ATTEMPTS} attempts: {crossing}"
    fields = asy_uart_link_driver._HAZARD_FIELDS
    sweep = last["FieldSweep"]
    assert isinstance(sweep, list) and len(sweep) == len(fields), f"the field sweep left a field out: {sweep}"
    for entry, expected in zip(sweep, _expected_sweep(fields)):
        assert entry == expected, f"the ACKs against J.3/J.4 per value (None: its raw write failed), or the clean exchange after them: {entry}, not {expected}"
    assert 0 < elapsed <= _HAZARD_RUN_VIRTUAL_MS, f"the hazard run took {elapsed} virtual ms, its bound {_HAZARD_RUN_VIRTUAL_MS}"


def _check_a_persisted_fault_during_a_transfer_does_not_stall_other_tasks(crc: "CrcMaker") -> None:
    # WP3's blocking-latency requirement: the FRAM-backed log path must not introduce a blocking wait anywhere the
    # "never blocks the asyncio loop, not even in a wait state" rule covers. asy_uart_comm.py is unchanged
    # here and the fake chunk's methods are coroutines, so this proves no regression.
    async def go() -> None:
        pair = await build_pair(crc=crc)
        pair.initiator._comm.pr = make_logger(LogConfig(_FakeFramManager(), 10, None), "UART_fram_test")
        ticks = 0

        async def ticker() -> None:
            nonlocal ticks
            while True:
                ticks += 1
                await asyncio.sleep_ms(_TICKER_STEP_MS)

        background = asyncio.create_task(ticker())
        try:
            # No responder listening: a real fault, which _fault() reports through the FRAM-backed
            # pr - exactly the new path this test exists to exercise.
            answer = await pair.initiator._comm.uart_get(0x01)
        finally:
            background.cancel()
            try:
                await background
            except asyncio.CancelledError:
                pass
        assert answer is None
        assert ticks > 2, "the ticker made no progress while a FRAM-backed fault was being reported"

    run(go(), RUN_LIMIT_S)


def _check_a_raw_write_that_fails_in_the_sweep_reads_as_no_verdict(crc: "CrcMaker") -> None:
    # A planted failed raw write for an illegal value reads None, never the "not ACKed" that value is expected to give,
    # so the judge counts it; the legal value after it is still ACKed and the link recovers.
    pair = Pair(crc=crc, rates=_SHIPPED_RATES)
    assert run(pair.setup(), RUN_LIMIT_S), "Pair.setup() failed"
    link = pair.initiator
    bus = link._uart
    assert bus is not None
    real_write = link._write_raw
    written: list[int] = []

    async def planted(frame: bytearray) -> bool:
        written.append(frame[1])
        return len(written) > 1 and await real_write(frame)

    link._write_raw = planted  # type: ignore[method-assign]
    fields = (("cmd", 1, (0x00, CMD_SET)),)
    got: list[object] = []

    async def go(clock: DrivenTime) -> None:
        listen = pair.responder._comm.start_asy_listen()

        async def sweep() -> None:
            got.append(await link._sweep_fields(bytearray(link._frame + bus.crc.length()), bytearray(link._frame + bus.crc.length())))

        task = asyncio.create_task(sweep())
        await clock.run_until(task.done, _HAZARD_RUN_VIRTUAL_MS)
        listen.cancel()
        await clock.run_until(listen.done, 0)

    swept = asy_uart_link_driver._HAZARD_FIELDS
    asy_uart_link_driver._HAZARD_FIELDS = fields  # type: ignore[assignment]  # one illegal value, then the legal one
    asy_uart_link_driver.time = time  # type: ignore[attr-defined]
    try:
        with DrivenTime(asy_uart_driver, asy_uart_comm, asy_uart_link_driver, sleeps=True) as clock:
            run(go(clock), RUN_LIMIT_S)
    finally:
        del asy_uart_link_driver.time  # type: ignore[attr-defined]
        asy_uart_link_driver._HAZARD_FIELDS = swept
    assert written == [0x00, CMD_SET], f"the sweep did not write the planted value, then the legal one: {written}"
    assert got == [[["cmd", [None, True], True]]] and got[0] != _expected_sweep(fields), f"the failed raw write did not read as no verdict: {got}"


def test_the_banner_names_its_mechanism_and_no_device() -> None:
    # The exerciser runs wherever a TOML wires uart_link: its bench banner names the jumper, never a board variant.
    names = devices()
    assert _BANNER and names, (_BANNER, names)  # an empty banner or no device would pass the check below vacuously
    assert [name for name in names if name.encode() in _BANNER] == [], _BANNER


def _check_banner_get_across_a_real_responder_via_get_callback(crc: "CrcMaker") -> None:
    # Exercises _get_callback end to end, over a real crossover link - the actual bench banner
    # exchange (SPECIFICATION.md Part A.7 step 13b), not a synthetic stand-in callback.
    async def go() -> None:
        pair = await build_pair(crc=crc)
        with PollRoundClock(stall_after=_STALL_AFTER, stall_ms=_STALL_MS) as clock:
            clock.arm()
            answer = await pair.with_listener(pair.initiator._comm.uart_get(0x01))
            assert clock.disarm(), "the planted stall never fired inside the exchange"
        assert copied_out(answer) == _BANNER

    run(go(), RUN_LIMIT_S)


def _check_echo_round_trip_across_a_real_responder_via_set_and_get_callbacks(crc: "CrcMaker") -> None:
    # SET then GET the same command id (0x02, ECHO) - exercising _set_callback/_message_callback's storage
    # and _get_callback's read-back, exactly as tests_hardware/device_scripts/uart_crossover_exchange.py
    # does against real hardware.
    #
    # Drives the responder through its real get_task_starters() listen-loop task rather than a bare
    # uart_listen() round, _message_callback - where _last_echo is written - only ever being invoked by that
    # loop.
    async def go() -> None:
        pair = await build_pair(crc=crc)
        listener = pair.responder.get_task_starters()[0]()
        try:
            with PollRoundClock(stall_after=_STALL_AFTER, stall_ms=_STALL_MS) as clock:
                clock.arm()
                ok = await pair.initiator._comm.uart_set(0x02, b"hello")
                assert clock.disarm(), "the planted stall never fired inside the exchange"
                answer = await pair.initiator._comm.uart_get(0x02)
            assert ok is True
            assert copied_out(answer) == b"hello"
        finally:
            listener.cancel()
            try:
                await listener
            except asyncio.CancelledError:
                pass

    run(go(), RUN_LIMIT_S)


def test_the_echo_answers_a_get_from_its_stored_pieces_without_a_copy() -> None:
    # Structural, never by filling the heap: a stored echo at the receive cap is answered as its own pieces, so the
    # callback allocates no bytearray and nothing a GET costs is peer-sized (J.8).
    pair = run(build_pair(), RUN_LIMIT_S)
    comm = pair.responder._comm
    stored = PieceBuffer(comm._max_transfer_bytes, comm._chunk_bytes)
    pair.responder._message_callback(0x02, CMD_SET, stored)
    sizes: list[int] = []

    def recording(*args: object) -> bytearray:
        made = bytearray(*args)
        sizes.append(len(made))
        return made

    asy_uart_link_driver.bytearray = recording  # type: ignore[attr-defined]
    try:
        valid, payload = pair.responder._get_callback(0x02)
    finally:
        del asy_uart_link_driver.bytearray  # type: ignore[attr-defined]
    assert sizes == [], sizes
    assert valid is True
    assert payload is stored


def _check_exercise_loop_counts_a_failure_when_nothing_answers(crc: "CrcMaker") -> None:
    # No responder listening at all - a real timeout, not a synthetic failure, and counted by the
    # loop itself rather than inferred from uart_get()'s return value.
    async def go() -> None:
        pair = await build_pair(crc=crc)
        await _one_exercise_round(pair, listen=False)
        assert (pair.initiator._transfers, pair.initiator._failures) == (0, 1)

    run(go(), RUN_LIMIT_S)


def test_exercise_loop_compares_a_same_length_answer_byte_for_byte() -> None:
    # Guard: the comparison scratch is reused every round, so a stale banner left in it must not pass a wrong answer.
    async def go() -> None:
        pair = await build_pair()
        pair.initiator._banner_check[:] = _BANNER
        pair.responder._comm._get_callback = lambda _cmd_id: (True, _BANNER[:-1] + b"x")  # the same length, one byte off
        await _one_exercise_round(pair)
        assert (pair.initiator._transfers, pair.initiator._failures) == (0, 1)

    run(go(), RUN_LIMIT_S)


def test_the_transfer_count_stops_at_the_counter_cap() -> None:
    async def go() -> None:
        pair = await build_pair()
        pair.initiator._transfers = COUNTER_CAP
        await _one_exercise_round(pair)
        assert (pair.initiator._transfers, pair.initiator._failures) == (COUNTER_CAP, 0)

    run(go(), RUN_LIMIT_S)


def test_the_failure_count_stops_at_the_counter_cap() -> None:
    async def go() -> None:
        pair = await build_pair()
        pair.initiator._failures = COUNTER_CAP
        await _one_exercise_round(pair, listen=False)
        assert (pair.initiator._transfers, pair.initiator._failures) == (0, COUNTER_CAP)

    run(go(), RUN_LIMIT_S)


def _check_exercise_loop_counts_a_transfer_for_a_correct_banner_answer(crc: "CrcMaker") -> None:
    # Drives the real loop, rather than calling uart_get() and incrementing the counter in the
    # test: the loop's own "answered AND with the right payload" decision is the thing under test,
    # and nothing exercised it before - it is what the bench reads the link's health off.
    async def go() -> None:
        pair = await build_pair(crc=crc)
        with PollRoundClock(stall_after=_STALL_AFTER, stall_ms=_STALL_MS) as clock:
            clock.arm()
            await _one_exercise_round(pair)
            assert clock.disarm(), "the planted stall never fired inside the exchange"
        assert (pair.initiator._transfers, pair.initiator._failures) == (1, 0)

    run(go(), RUN_LIMIT_S)


def _check_exercise_loop_counts_a_wrong_payload_as_a_failure_not_a_transfer(crc: "CrcMaker") -> None:
    # The biting half: a responder that answers, but with something else. Counting this as a
    # transfer would report a healthy link while the jumper carried the wrong bytes.
    async def go() -> None:
        pair = await build_pair(crc=crc)
        pair.initiator._transfers = 0
        pair.responder._comm._get_callback = lambda _cmd_id: (True, b"not-the-banner")  # a plain attribute, read per uart_listen() call
        await _one_exercise_round(pair)
        assert (pair.initiator._transfers, pair.initiator._failures) == (0, 1)

    run(go(), RUN_LIMIT_S)


def _check_get_error_counter_delegates_to_the_inner_comms_own_log(crc: "CrcMaker") -> None:
    # The _ModuleLike surface the generated boot list registers: this wrapper holds no error state
    # of its own, so its counter has to be the inner UARTComm's or a /status read reports zero.
    async def go() -> None:
        pair = await build_pair(crc=crc)
        await pair.initiator._comm.pr.err_s("bench-side fault", errno=7)
        assert await pair.initiator.get_error_counter() == await pair.initiator._comm.get_error_counter()
        assert 7 in (await pair.initiator.get_error_counter())[pair.initiator.name]["ErrNum"]

    run(go(), RUN_LIMIT_S)


def test_a_refused_construction_ends_every_task_for_both_roles() -> None:
    # The initiator's exercise loop ends like the responder's listen loop, so the supervisor's restart
    # escalation reaches a reboot for a link that cannot come up (SPECIFICATION.md Part C.7.2).
    for role in (ROLE_INITIATOR, ROLE_RESPONDER):
        driver = _refused_link(role)
        assert run(driver.setup(), RUN_LIMIT_S) is False
        assert driver.initialized is False
        done = run(_rounds_until_done(driver), RUN_LIMIT_S)
        assert done == [True], f"{role}: tasks done {done}"
        errnos = run(driver.get_error_counter(), RUN_LIMIT_S)[driver.name]["ErrNum"]
        assert code("E", "UART_PAYLOAD_SIZE") in errnos, f"{role}: {errnos}"
        assert code("E", "NOT_INIT") not in errnos, f"{role}: {errnos}"


def test_cancelling_an_exercise_round_at_each_await_leaves_the_bus_unlocked() -> None:
    # The exercise loop cancelled after 0, 1, 2, ... turns on a fresh pair, the responder's listen cancelled with it, every
    # UART sleep a bare yield: both ends come back free, and a round counts once its GET has returned, never on a cancel.
    current: list[Pair] = []
    returned = [0]
    inside = [False]
    held, counted = [0], [0]

    async def build() -> Pair:
        pair = await build_pair()
        real_get = pair.initiator._comm.uart_get

        async def counted_get(get_id: int, exp_size: "int | None" = None) -> "PieceBuffer | None":
            answer = await real_get(get_id, exp_size)
            returned[0] += 1
            return answer

        pair.initiator._comm.uart_get = counted_get  # type: ignore[method-assign]
        current[:] = [pair]
        returned[0], inside[0] = 0, False
        return pair

    async def turn() -> None:
        await asyncio.sleep(0)
        inside[0] = current[0].uart_a.session_lock.locked() or current[0].uart_b.session_lock.locked()

    def invariants(pair: Pair) -> None:
        held[0] += inside[0]
        counted[0] += returned[0]
        for end in (pair.initiator, pair.responder):
            assert end._comm._busy is False, end.name + " is still marked busy"
            assert end._comm._in_resync is False, end.name + " is still inside a resync"
        assert_unlocked(initiator=pair.uart_a.session_lock, responder=pair.uart_b.session_lock)
        counts = (pair.initiator._transfers, pair.initiator._failures)
        assert counts == (returned[0], 0), f"counted (transfers, failures) {counts} with the GET returned {returned[0]} time(s)"

    async def exercise_round(pair: Pair) -> None:
        # The loop never ends by itself, so every count ends in a cancel; the peer goes with it, never drained.
        peer = asyncio.create_task(pair.responder._comm.uart_listen())
        try:
            await pair.initiator._exercise_loop()
        finally:
            peer.cancel()
            try:
                await peer
            except asyncio.CancelledError:  # expected; anything else is a real failure
                pass

    with PollRoundClock() as clock:
        clock.pace(real=False)
        cancel_at_each_await(build, exercise_round, invariants, max_steps=_ROUND_SWEEP_TURNS, turn=turn, endless=True)
    assert held[0] > 0, f"no cancel in {_ROUND_SWEEP_TURNS} turns landed with a session lock held"
    assert counted[0] > 0, f"no cancel in {_ROUND_SWEEP_TURNS} turns landed after the round's GET returned"


# ---------------------------------------------------------------------------
# The hazard mode (owner, 2026-10-21, asked "Leave the UART hazards under API load untested?": "b - system shall be
# proven stable unter max load allover"): one dispatch-only request, one bounded run, then the echo again.
# ---------------------------------------------------------------------------

_UID_MAX = src_int("src/asy_uart_comm.py", "_UID_MAX")
_EXERCISE_PERIOD_MS = src_int("src/asy_uart_link_driver.py", "_EXERCISE_PERIOD_MS")
_HAZARD_RECOVERY_ATTEMPTS = src_int("src/asy_uart_link_driver.py", "_HAZARD_RECOVERY_ATTEMPTS")
# The first-chunk boundary values J.3/J.4 accept, as the bench host judges them (tests_hardware/flash/test_uart_crossover.py).
_LEGAL = {"cmd": lambda v: v == CMD_SET, "size": lambda v: v == 1, "chunks": lambda v: v >= 2, "cur_chunk": lambda v: v == 1, "uid": lambda v: v <= _UID_MAX}
_ONE_COMPLETION = ([True, False], [False, True])  # two initiations at once: one completes, one is refused, either order


def _check_unanswerable_command_id_is_rejected_not_crashed(crc: "CrcMaker") -> None:
    async def go() -> None:
        pair = await build_pair(crc=crc)
        answer = await pair.with_listener(pair.initiator._comm.uart_get(0x99))
        assert answer is None  # _get_callback returns (False, None) for an unknown command id

    run(go(), RUN_LIMIT_S)


def _shipped_rates() -> "tuple[PollRates, PollRates]":
    # Each end's poll rates on the device wiring the link, read from its generated bus constructions (buildgen writes
    # them from its TOML). Defined here, out of D.15's order, because the constant below calls it at import.
    require_fresh()
    device = device_with("uart_link")
    pair = wiring_plan(device)["uart"]
    assert pair is not None, f"{device} wires uart_link but its plan names no UART pair"
    found: list[PollRates] = []
    for bus in (pair["initiator_bus"], pair["responder_bus"]):
        passed = bus_keywords(device, bus)
        rates: PollRates = {}
        if "poll_wait_ms" in passed:
            rates["poll_wait_ms"] = passed["poll_wait_ms"]
        if "poll_idle_ms" in passed:
            rates["poll_idle_ms"] = passed["poll_idle_ms"]
        found.append(rates)
    return found[0], found[1]


# The hazard runs poll as the firmware wiring the link ships, never at a rate no device uses (agent, 2026-10-27).
_SHIPPED_RATES = _shipped_rates()
# From the request to the run's end on the driven clock, exact on any host: the measured figure in both CRC modes at
# _SHIPPED_RATES, with no margin (agent, 2026-10-27).
# @tunable l1.asy_uart_link_driver_hazard_run_virtual_ms = 22440
_HAZARD_RUN_VIRTUAL_MS = 22440


def test_an_initiation_that_raises_is_logged_and_reads_as_no_verdict() -> None:
    # A planted uart_set() raising in the second of two initiations at once: its task's top logs it, its verdict is None,
    # and the judge reads the pair as no completion and refusal.
    link = UARTLinkDriver(UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS), ROLE_INITIATOR)
    calls: list[object] = []

    async def planted(set_id: int, payload: object = None) -> bool:
        calls.append(payload)
        if len(calls) == 2:
            raise ValueError("planted initiation fault")
        return True

    link._comm.uart_set = planted  # type: ignore[method-assign]
    two = run(link._two_initiations(), RUN_LIMIT_S)
    assert two == [True, None] and two not in _ONE_COMPLETION, f"the raising initiation did not read as no verdict: {two}"
    logged = run(link.get_error_counter(), RUN_LIMIT_S)[link.name]
    assert logged["ErrCount"] == 1 and code("E", "UNEXPECTED") in logged["ErrNum"], f"the raise was not logged once at its task's top: {logged}"


def _expected_sweep(fields: "tuple[tuple[str, int, tuple[int, ...]], ...]") -> "list[object]":
    # The field sweep's verdicts J.3/J.4 give: each value ACKed exactly when legal, then one clean exchange per field.
    return [[name, [_LEGAL[name](value) for value in values], True] for name, _offset, values in fields]


def test_each_recovery_try_first_waits_one_window() -> None:
    # The peer's backoff, timeout and resync pass before every try: each uart_set() follows one more window-long sleep,
    # and an unanswered link gives up after its last try.
    link = UARTLinkDriver(UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS), ROLE_INITIATOR)
    fast = FastAsyncSleep()
    owner: list[object] = []
    seen: list[int] = []

    async def unanswered(set_id: int, payload: object = None) -> bool:
        owner.append(asyncio.current_task())
        seen.append(len(fast.ms_of(owner[0])))
        return False

    link._comm.uart_set = unanswered  # type: ignore[method-assign]
    with fast:
        attempts, recovered = run(link._recover(), RUN_LIMIT_S)
    assert (attempts, recovered) == (_HAZARD_RECOVERY_ATTEMPTS, False), (attempts, recovered)
    assert seen == list(range(1, _HAZARD_RECOVERY_ATTEMPTS + 1)), f"window sleeps before each try: {seen}"
    assert fast.ms_of(owner[0]) == [link._window_ms] * _HAZARD_RECOVERY_ATTEMPTS, fast.ms_of(owner[0])


def test_a_hazard_run_is_requested_only_on_a_ready_initiator_and_one_at_a_time() -> None:
    async def go() -> None:
        pair = Pair()
        assert await pair.initiator.get_hazard_report() == {"Runs": 0, "Pending": False, "Last": None}, "a fresh link reports a hazard run"
        assert pair.initiator.request_hazard_run() is False, "a hazard run was accepted before setup()"
        assert await pair.setup()
        assert pair.responder.request_hazard_run() is False, "the responder accepted a hazard run: only the initiating end drives one"
        assert pair.initiator.request_hazard_run() is True, "a ready initiator refused a hazard run"
        assert pair.initiator.request_hazard_run() is False, "a second request was accepted while one run is pending"
        assert await pair.initiator.get_hazard_report() == {"Runs": 0, "Pending": True, "Last": None}

    run(go(), RUN_LIMIT_S)


async def _one_exercise_round(pair: Pair, *, listen: bool = True) -> None:
    # Drives the initiator's _exercise_loop() through exactly one counted round, then stops it. The round ends
    # when uart_get() has returned: the loop counts with no await before its period's sleep, and a counter at
    # its cap never moves, so the counters cannot mark it.
    comm = pair.initiator._comm
    real_get = comm.uart_get
    returned = [0]

    async def counted_get(get_id: int, exp_size: "int | None" = None) -> "PieceBuffer | None":
        answer = await real_get(get_id, exp_size)
        returned[0] += 1
        return answer

    comm.uart_get = counted_get  # type: ignore[method-assign]
    listener = asyncio.create_task(pair._listen_rounds(1)) if listen else None
    loop_task = asyncio.create_task(pair.initiator._exercise_loop())
    try:
        while not returned[0]:
            await asyncio.sleep(_ROUND_POLL_S)
    finally:
        for task in (loop_task, listener):
            if task is None:
                continue
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


def _recorded_errnos(comm: "asy_uart_comm.UARTComm") -> "list[int]":
    # Every error number one end's comm reports, in order (its log keeps only the latest few): each fault logs
    # through _err, so hooking _err alone counts it once.
    errnos: list[int] = []
    real_err = comm._err

    async def err(errno: int, *args: object) -> None:
        errnos.append(errno)
        await real_err(errno, *args)

    comm._err = err  # type: ignore[method-assign]
    return errnos


def _refused_link(role: str) -> UARTLinkDriver:
    # A construction the protocol refuses (payload_size 0) on a bus polled as Pair's is, never a real select.poll().
    DMA.reset_registry()
    bus = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    bus.poller = LinkPoller(bus._uart, mask=select.POLLOUT)  # type: ignore[arg-type, assignment]
    return UARTLinkDriver(bus, role, limits=transfer_limits(payload_size=0), name_ext="refused")


class _Body:
    # A request carrying a JSON body, all _put_status() reads of one.
    def __init__(self, body: "JsonDict") -> None:
        self.json = body


async def _rounds_until_done(driver: UARTLinkDriver) -> "list[bool]":
    # Starts every task the driver's starters return and counts poll rounds on the shared clock until all
    # are done; any still running after the bound is cancelled and reported as not done.
    with PollRoundClock():
        tasks = [start() for start in driver.get_task_starters()]
        for _ in range(_TASK_END_ROUNDS):
            if all(task.done() for task in tasks):
                break
            await asyncio.sleep_ms(POLL_WAIT_MS)
        done = [task.done() for task in tasks]
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    return done


def _status_service(link: "UARTLinkDriver | None") -> WebserverService:
    # The webserver as a generated module wires it on dev, the hazard command registered on /status's PUT.
    routes = RouteSources([], {}, None, None, (), None, None, None, (), ())
    service = WebserverService(Microdot(), routes, ServingLimits(2048, 256, 2, None, 5.0, 15.0, "127.0.0.1", 0), _uptime_s)
    if link is not None:
        service.add_status_command("UartHazards", link.request_hazard_run)
    return service


def test_a_status_put_starts_one_hazard_run_answers_each_outcome_and_writes_nothing() -> None:
    # Dispatch-only: Valid when the run is taken, Failed while one is pending, Invalid for anything but true or on a device
    # wiring no link; no write reaches the flash, so the persistence-write gate stays untouched.
    async def go() -> None:
        pair = Pair()
        assert await pair.setup()
        service = _status_service(pair.initiator)
        bare = _status_service(None)
        with WriteCountingOpen(asy_config_manager) as cfg, WriteCountingOpen(asy_webserver_service) as web, WriteCountingOpen(asy_uart_link_driver) as own:
            answers = []
            for svc, value in ((service, False), (service, True), (service, True), (bare, True)):
                answers.append((await svc._put_status(_Body({"UartHazards": value})))["result"])  # type: ignore[arg-type]  # the body alone is read: no socket behind it
            report = await pair.initiator.get_hazard_report()
        assert answers == [{"UartHazards": INVALID}, {"UartHazards": VALID}, {"UartHazards": FAILED}, {"UartHazards": INVALID}], answers
        assert report == {"Runs": 0, "Pending": True, "Last": None}, report
        assert (cfg.writes, web.writes, own.writes) == (0, 0, 0), f"the hazard command wrote to the flash: {(cfg.writes, web.writes, own.writes)}"

    run(go(), RUN_LIMIT_S)


async def _uptime_s() -> int:
    return 0


# ---------------------------------------------------------------------------
# Optional FRAM support: UARTLinkDriver forwards log=/logger= into UARTComm, whose FRAM-backed
# history is unit-tested in test_asy_uart_comm.py. Covered here: the forwarding, the default, the
# allocation-failure fallback, the logger reach-through and a reboot roundtrip.
# ---------------------------------------------------------------------------


class _FakeFramChunk:
    # One chunk's bytes, moved through the real RegionBuffer asy_print_log's _FramChunk Protocol names.
    def __init__(self) -> None:
        self.buf = bytearray(64)
        self._buffer = RegionBuffer(64)

    def get_buffer(self) -> RegionBuffer:
        return self._buffer

    async def read_into(self, buf: RegionBuffer) -> bool:
        data = buf.get_data_buf()
        if data is None:
            return False
        data[:] = self.buf
        return True

    async def write_into(self, buf: RegionBuffer) -> bool:
        data = buf.get_data_buf()
        if data is None:
            return False
        self.buf[:] = data
        return True


class _FakeFramManager:
    def __init__(self, chunk: "_FakeFramChunk | None" = None, *, fail: bool = False) -> None:
        self._chunk = chunk if chunk is not None else _FakeFramChunk()
        self._fail = fail

    def get_chunk(self, size: int, crc: "CRCBase | None" = None, verify: int = 0, check_length: int = 8, *, owner: str) -> "_FakeFramChunk | None":
        if self._fail:
            return None  # the real allocator's refusal: no room left on the chip
        return self._chunk

    def get_pause(self) -> bool:
        return False


def test_a_fram_log_config_lands_entries_in_the_managers_chunk() -> None:
    async def go() -> None:
        fram = _FakeFramManager()
        driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
        initiator = UARTLinkDriver(driver, ROLE_INITIATOR, log=LogConfig(fram, 10, None))
        assert isinstance(initiator.pr, PrintLogHistoryStore)
        assert initiator.pr.fram is fram._chunk
        await initiator.setup()
        await initiator.pr.err_s("boom", errno=7)
        second = make_logger(LogConfig(fram, 10, None), "UART")
        await second.setup()
        assert list(second.history)[-1] == 7

    run(go(), RUN_LIMIT_S)


def test_the_default_log_stays_ram_only() -> None:
    # The default (no log=) stays a RAM-only history.
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    initiator = UARTLinkDriver(driver, ROLE_INITIATOR)
    assert isinstance(initiator.pr, PrintLogHistory)
    assert not isinstance(initiator.pr, PrintLogHistoryStore)


def test_fram_allocation_failure_degrades_to_ram_only_not_a_crash() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    initiator = UARTLinkDriver(driver, ROLE_INITIATOR, log=LogConfig(_FakeFramManager(fail=True), 10, None))
    assert isinstance(initiator.pr, PrintLogHistoryStore)
    assert initiator.pr.fram is None


def test_logger_kwarg_reaches_through_to_an_already_built_sibling_logger() -> None:
    # The other half of UARTComm's own reach-through (asy_uart_comm.py) - own chunk vs. sharing an
    # upstream instantiator's logger - now reachable through this wrapper too.
    driver_a = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    driver_b = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    owner = UARTLinkDriver(driver_a, ROLE_INITIATOR, log=LogConfig(_FakeFramManager(), 10, None))
    shared = UARTLinkDriver(driver_b, ROLE_RESPONDER, logger=owner.pr)
    assert shared.pr is owner.pr


def test_fram_backed_error_history_survives_a_simulated_reboot() -> None:
    async def go() -> None:
        chunk = _FakeFramChunk()
        fram = _FakeFramManager(chunk)

        driver1 = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
        before = UARTLinkDriver(driver1, ROLE_INITIATOR, log=LogConfig(fram, 10, None))
        await before.setup()
        await before.pr.err_s("boom", errno=1)

        driver2 = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
        after = UARTLinkDriver(driver2, ROLE_INITIATOR, log=LogConfig(fram, 10, None))
        await after.setup()
        assert after.pr._err_count == before.pr._err_count
        assert list(after.pr.history) == list(before.pr.history)

    run(go(), RUN_LIMIT_S)


async def build_pair(payload_size: int = PAYLOAD_SIZE, timeout: int = TIMEOUT_MS, crc: "CrcMaker" = None) -> Pair:
    pair = Pair(payload_size=payload_size, timeout=timeout, crc=crc)
    assert await pair.setup(), "Pair.setup() failed - both roles must be ready before the test's own assertions mean anything"
    return pair


# Every check that moves bytes runs with no CRC and with CRC16 (owner, 2026-09-30: "at every level that can reach it");
# the corruption case is CRC16's alone, and the banner and echo checks enter the poll-round clock themselves.
register_both_crc_modes(
    globals(),
    {"a_corrupted_frame_counts_one_failure_and_the_next_transfer_succeeds": "crc16"},
    (
        "a_crossing_whose_uid_aliases_the_peers_ack_fails_as_peer_initiated",
        "a_hazard_run_reports_every_verdict_then_returns_to_the_echo",
        "a_raw_write_that_fails_in_the_sweep_reads_as_no_verdict",
        "banner_get_across_a_real_responder_via_get_callback",
        "echo_round_trip_across_a_real_responder_via_set_and_get_callbacks",
    ),
)



def test_a_hazard_run_sends_every_raw_frame_without_a_copy() -> None:
    # Each raw frame goes out of one buffer with room for its CRC (writefrom()), never through write()'s CRC copy,
    # which costs one allocation per frame; the run's verdicts, and so its bytes on the wire, are the CRC16 check's.
    added: list[int] = []
    real_add = CRC16.add

    async def counted(self: "CRCBase", bytearr: bytearray, init: "int | None" = None) -> "bytearray | None":
        added.append(len(bytearr))
        return await real_add(self, bytearr, init)

    CRC16.add = counted  # type: ignore[method-assign]  # the class, so every bus's CRC counts
    try:
        _check_a_hazard_run_reports_every_verdict_then_returns_to_the_echo(CRC16)
    finally:
        CRC16.add = real_add  # type: ignore[method-assign]
    assert added == [], f"{len(added)} raw frames copied for their CRC"


def test_an_echo_get_before_any_echo_set_answers_valid_and_empty() -> None:
    DMA.reset_registry()
    driver = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    responder = UARTLinkDriver(driver, ROLE_RESPONDER)
    assert responder._get_callback(src_int("src/asy_uart_link_driver.py", "_CMD_ECHO")) == (True, b"")


def test_a_double_initiation_cancelled_at_its_first_await_leaves_no_transaction_behind() -> None:
    # The cancel is forwarded to the first initiation, so the second, scheduled but not awaited yet, is what the finally
    # cancels: left alone it would run a whole transaction against the silent responder.
    pair = Pair()
    assert run(pair.setup(), RUN_LIMIT_S) is True
    comm = pair.initiator._comm

    async def scenario() -> bool:
        outer = asyncio.create_task(pair.initiator._two_initiations())
        await asyncio.sleep_ms(0)  # the outer task runs to `await first`; neither initiation has run yet
        outer.cancel()
        try:
            await outer
        except asyncio.CancelledError:
            pass
        await asyncio.sleep_ms(POLL_WAIT_MS)  # a leftover initiation is now inside its transaction
        return comm._busy

    assert run(scenario(), RUN_LIMIT_S) is False


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
