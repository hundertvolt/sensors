"""UARTLinkDriver: the bench exerciser's transfers, failure counts and banner across a real UARTComm pair in both
CRC modes, its task starters and its FRAM-backed log."""

import asyncio
import select

from _async_harness import cancel, run
from _error_codes import code
from _generated_tree import devices
from _src_const import src_bytes
from _uart_comm_harness import POLL_WAIT_MS, RUN_LIMIT_S, TIMEOUT_MS, PollRoundClock, awaited_with_listener, copied_out, transfer_limits
from _uart_comm_hazard_common import register_both_crc_modes
from machine import UART as FakeUART
from machine import LinkPoller, UARTLink
from rp2 import DMA

from asy_base_classes import COUNTER_CAP, RegionBuffer
from asy_print_log import LogConfig, PrintLogHistory, PrintLogHistoryStore, make_logger
from asy_uart_comm import ROLE_INITIATOR, ROLE_RESPONDER
from asy_uart_driver import UART
from asy_uart_link_driver import UARTLinkDriver

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import TypeVar

    from _uart_comm_hazard_common import CrcMaker

    from asy_base_classes import PieceBuffer
    from asy_crc_checks import CRCBase

    T = TypeVar("T")

PAYLOAD_SIZE = 8
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
_BANNER: bytes = src_bytes("src/asy_uart_link_driver.py", "_BANNER")


class Pair:
    # One initiator and one responder UARTLinkDriver across a real crossover link - the same
    # shape tests/_uart_comm_harness.py's own Pair uses for bare UARTComm objects, one layer up.
    def __init__(self, payload_size: int = PAYLOAD_SIZE, timeout: int = TIMEOUT_MS, crc: "CrcMaker" = None) -> None:
        # `crc` builds one CRC per bus (CRCBase carries state), so both ends agree; None leaves the buses without one.
        DMA.reset_registry()  # each link's ring holds two of the twelve channels: a later pair in one test frees them
        self.uart_a = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, crc=None if crc is None else crc())
        self.uart_b = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, crc=None if crc is None else crc())
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

    async def setup(self) -> bool:
        return await self.initiator.setup() and await self.responder.setup()

    async def with_listener(self, work: "Coroutine[object, object, T]", rounds: int = 1, *, listener_may_stall: bool = False) -> "T":
        # The harness's rule: a stalled responder fails the exchange unless the test declares it.
        listener = asyncio.create_task(self._listen_rounds(rounds))
        return await awaited_with_listener(work, listener, rounds, may_stall=listener_may_stall)

    async def _listen_rounds(self, rounds: int) -> None:
        for _ in range(rounds):
            await self.responder._comm.uart_listen()


async def build_pair(payload_size: int = PAYLOAD_SIZE, timeout: int = TIMEOUT_MS, crc: "CrcMaker" = None) -> Pair:
    pair = Pair(payload_size=payload_size, timeout=timeout, crc=crc)
    assert await pair.setup(), "Pair.setup() failed - both roles must be ready before the test's own assertions mean anything"
    return pair


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


def test_the_banner_names_its_mechanism_and_no_device() -> None:
    # The exerciser runs wherever a TOML wires uart_link: its bench banner names the jumper, never a board variant.
    names = devices()
    assert _BANNER and names, (_BANNER, names)  # an empty banner or no device would pass the check below vacuously
    assert [name for name in names if name.encode() in _BANNER] == [], _BANNER


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


def _check_unanswerable_command_id_is_rejected_not_crashed(crc: "CrcMaker") -> None:
    async def go() -> None:
        pair = await build_pair(crc=crc)
        answer = await pair.with_listener(pair.initiator._comm.uart_get(0x99))
        assert answer is None  # _get_callback returns (False, None) for an unknown command id

    run(go(), RUN_LIMIT_S)


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


def _refused_link(role: str) -> UARTLinkDriver:
    # A construction the protocol refuses (payload_size 0) on a bus polled as Pair's is, never a real select.poll().
    DMA.reset_registry()
    bus = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    bus.poller = LinkPoller(bus._uart, mask=select.POLLOUT)  # type: ignore[arg-type, assignment]
    return UARTLinkDriver(bus, role, limits=transfer_limits(payload_size=0), name_ext="refused")


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


def _check_get_error_counter_delegates_to_the_inner_comms_own_log(crc: "CrcMaker") -> None:
    # The _ModuleLike surface the generated boot list registers: this wrapper holds no error state
    # of its own, so its counter has to be the inner UARTComm's or a /status read reports zero.
    async def go() -> None:
        pair = await build_pair(crc=crc)
        await pair.initiator._comm.pr.err_s("bench-side fault", errno=7)
        assert await pair.initiator.get_error_counter() == await pair.initiator._comm.get_error_counter()
        assert 7 in (await pair.initiator.get_error_counter())[pair.initiator.name]["ErrNum"]

    run(go(), RUN_LIMIT_S)


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

    async def write_into(self, buf: RegionBuffer) -> bool:
        data = buf.get_data_buf()
        if data is None:
            return False
        self.buf[:] = data
        return True

    async def read_into(self, buf: RegionBuffer) -> bool:
        data = buf.get_data_buf()
        if data is None:
            return False
        data[:] = self.buf
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


# Every check that moves bytes runs with no CRC and with CRC16 (owner, 2026-09-30: "at every level that can reach it");
# the corruption case is CRC16's alone, and the banner and echo checks enter the poll-round clock themselves.
register_both_crc_modes(
    globals(),
    {"a_corrupted_frame_counts_one_failure_and_the_next_transfer_succeeds": "crc16"},
    ("banner_get_across_a_real_responder_via_get_callback", "echo_round_trip_across_a_real_responder_via_set_and_get_callbacks"),
)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
