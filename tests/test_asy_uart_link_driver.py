import asyncio

from machine import UART as FakeUART
from machine import LinkPoller, UARTLink

from asy_uart_comm import ROLE_INITIATOR, ROLE_RESPONDER
from asy_uart_driver import UART
from asy_uart_link_driver import UartLinkExerciser
from print_log import PrintLogHistoryStore

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    from crc_checks import CRC_Base

    T = TypeVar("T")

PAYLOAD_SIZE = 8
TIMEOUT_MS = 100
POLL_WAIT_MS = 1


def run(coro: "Coroutine[Any, Any, T]", limit: int = 10) -> "T":
    # Every test is bounded: a wedge must surface as a fast FAIL, never as a hung test file.
    return asyncio.run(asyncio.wait_for(coro, limit))


class Pair:
    # One initiator and one responder UartLinkExerciser across a real crossover link - the same
    # shape tests/_uart_comm_harness.py's own Pair uses for bare UART_Comm objects, one layer up.
    def __init__(self, payload_size: int = PAYLOAD_SIZE, timeout: int = TIMEOUT_MS) -> None:
        self.uart_a = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
        self.uart_b = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS)
        self.fake_a: FakeUART = self.uart_a._uart  # type: ignore[assignment]
        self.fake_b: FakeUART = self.uart_b._uart  # type: ignore[assignment]
        self.link = UARTLink(self.fake_a, self.fake_b)
        # A bounded stand-in, never a real select.poll() - CLAUDE.md's known CI-hang cause.
        self.uart_a.poller = LinkPoller(self.fake_a)  # type: ignore[assignment]
        self.uart_b.poller = LinkPoller(self.fake_b)  # type: ignore[assignment]
        self.initiator = UartLinkExerciser(self.uart_a, ROLE_INITIATOR, payload_size=payload_size, timeout=timeout, name_ext="init")
        self.responder = UartLinkExerciser(self.uart_b, ROLE_RESPONDER, payload_size=payload_size, timeout=timeout, name_ext="resp")

    async def setup(self) -> bool:
        return await self.initiator.setup() and await self.responder.setup()

    async def with_listener(self, work: "Coroutine[Any, Any, T]", rounds: int = 1) -> "T":
        listener = asyncio.create_task(self._listen_rounds(rounds))
        try:
            return await work
        finally:
            try:
                await asyncio.wait_for(listener, 5)
            except asyncio.TimeoutError:
                listener.cancel()
                try:
                    await listener
                except asyncio.CancelledError:
                    pass

    async def _listen_rounds(self, rounds: int) -> None:
        for _ in range(rounds):
            await self.responder._comm.uart_listen()


async def build_pair(payload_size: int = PAYLOAD_SIZE, timeout: int = TIMEOUT_MS) -> Pair:
    pair = Pair(payload_size=payload_size, timeout=timeout)
    await pair.setup()
    return pair


def test_name_resolution_matches_instance_name_convention() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    plain = UartLinkExerciser(driver, ROLE_INITIATOR)
    assert plain.name == "UART"
    extended = UartLinkExerciser(driver, ROLE_INITIATOR, name_ext="init")
    assert extended.name == "UART_init"
    assert extended.pr.name == "UART_init"


def test_initiator_task_starters_include_exercise_loop() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    initiator = UartLinkExerciser(driver, ROLE_INITIATOR)
    starters = initiator.get_task_starters()
    assert len(starters) == 1  # UART_Comm's own list is empty for an initiator - see its own get_task_starters()
    task = starters[0]()
    task.cancel()


def test_responder_task_starters_are_the_listen_loop_only() -> None:
    driver = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS)

    def get_cb(cmd_id: int) -> "tuple[bool, bytes | None]":
        return False, None

    def set_cb(cmd_id: int) -> "tuple[bool, int | None]":
        return False, None

    responder = UartLinkExerciser(driver, ROLE_RESPONDER)
    responder._get_callback = get_cb  # type: ignore[method-assign]
    responder._set_callback = set_cb  # type: ignore[method-assign]
    starters = responder.get_task_starters()
    assert len(starters) == 1  # the listen loop, not an exercise loop
    task = starters[0]()
    task.cancel()


def test_timer_starters_are_always_empty() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    initiator = UartLinkExerciser(driver, ROLE_INITIATOR)
    assert initiator.get_timer_starters() == []


def test_get_error_sources_and_loggers_delegate_to_inner_comm() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    initiator = UartLinkExerciser(driver, ROLE_INITIATOR)
    assert initiator.get_error_sources() == [initiator._comm]
    assert initiator.get_loggers() == [initiator._comm.pr]


def test_get_link_status_starts_at_zero() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    initiator = UartLinkExerciser(driver, ROLE_INITIATOR)
    status = run(initiator.get_link_status())
    assert status == {"Transfers": 0, "Failures": 0}


def test_reset_error_counter_also_resets_link_counters() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    initiator = UartLinkExerciser(driver, ROLE_INITIATOR)
    initiator.transfers = 5
    initiator.failures = 2
    run(initiator.reset_error_counter())
    assert initiator.transfers == 0
    assert initiator.failures == 0


def test_exercise_loop_one_round_against_a_real_responder_banner() -> None:
    async def go() -> None:
        pair = await build_pair()
        answer = await pair.with_listener(pair.initiator._comm.uart_get(0x01))
        assert answer is not None and bytes(answer) == b"dev-uart-crossover"
        pair.initiator.transfers += 1
        assert pair.initiator.transfers == 1

    run(go())


def test_banner_get_across_a_real_responder_via_get_callback() -> None:
    # Exercises _get_callback end to end, over a real crossover link - the actual bench banner
    # exchange (SPECIFICATION.md Part A.7 step 13b), not a synthetic stand-in callback.
    async def go() -> None:
        pair = await build_pair()
        answer = await pair.with_listener(pair.initiator._comm.uart_get(0x01))
        assert answer is not None
        assert bytes(answer) == b"dev-uart-crossover"

    run(go())


def test_echo_round_trip_across_a_real_responder_via_set_and_get_callbacks() -> None:
    # SET then GET the same command id (0x02, ECHO) - exercises _set_callback/_message_callback's
    # storage and _get_callback's read-back, exactly as tests_hardware/device_scripts/
    # uart_crossover_exchange.py does against real hardware. Drives the responder through its own
    # real get_task_starters() listen-loop task (not a bare uart_listen() round, unlike this file's
    # other tests/Pair.with_listener()): _message_callback - where _last_echo is actually written -
    # is only ever invoked by that loop, never by a raw uart_listen() call.
    async def go() -> None:
        pair = await build_pair()
        listener = pair.responder.get_task_starters()[0]()
        try:
            ok = await pair.initiator._comm.uart_set(0x02, b"hello")
            assert ok is True
            answer = await pair.initiator._comm.uart_get(0x02)
            assert answer is not None
            assert bytes(answer) == b"hello"
        finally:
            listener.cancel()
            try:
                await listener
            except asyncio.CancelledError:
                pass

    run(go())


def test_unanswerable_command_id_is_rejected_not_crashed() -> None:
    async def go() -> None:
        pair = await build_pair()
        answer = await pair.with_listener(pair.initiator._comm.uart_get(0x99))
        assert answer is None  # _get_callback returns (False, None) for an unknown command id

    run(go())


def test_exercise_loop_counts_a_failure_when_nothing_answers() -> None:
    # No responder listening at all - a real timeout, not a synthetic failure.
    async def go() -> None:
        pair = await build_pair()
        answer = await pair.initiator._comm.uart_get(0x01)  # no with_listener() - nothing answers
        assert answer is None

    run(go())


# ---------------------------------------------------------------------------
# WP3: fram=/logger= forwarding into UART_Comm's own already-correct construction (SPECIFICATION.md
# Part J.9/C.14). UartLinkExerciser adds no logging behavior of its own - these tests cover the
# forwarding itself, not UART_Comm's own fram=/logger= handling (already covered by
# tests/test_asy_uart_comm.py).
# ---------------------------------------------------------------------------


class _FakeFramChunk:
    def __init__(self) -> None:
        self.buf = bytearray(64)
        self.fail_writes = 0  # simulates a transient FRAM write hiccup - see the resilience test below

    def get_buffer(self) -> "_FakeFramChunk":
        return self

    def get_data_buf(self) -> bytearray:
        return self.buf

    async def write_into(self, buf: "_FakeFramChunk", *, override_pause: bool = False) -> bool:
        if self.fail_writes > 0:
            self.fail_writes -= 1
            return False
        self.buf[:] = buf.get_data_buf()
        return True

    async def read_into(self, buf: "_FakeFramChunk", *, override_pause: bool = False) -> bool:
        buf.get_data_buf()[:] = self.buf
        return True


class _FakeFramManager:
    def __init__(self, chunk: "_FakeFramChunk") -> None:
        self.chunk = chunk

    def get_chunk(self, size: int, crc: "CRC_Base | None" = None, verify: int = 0, check_length: int = 8) -> "_FakeFramChunk":
        return self.chunk


class _RaisingFramManager:
    # Models a real allocator whose FRAM chip never came up - PrintLogHistoryStore.__init__ wraps
    # this call broadly (print_log.py's own module docstring), so construction must not crash.
    def get_chunk(self, size: int, crc: "CRC_Base | None" = None, verify: int = 0, check_length: int = 8) -> "_FakeFramChunk":
        raise OSError("synthetic FRAM allocation failure")


def test_default_construction_stays_ram_only_like_before() -> None:
    # Regression pin: with no fram=/logger= passed (every existing call site, including every
    # generated device today except dev.toml's own two instances), behavior is byte-for-byte what
    # it was before this wiring existed - a plain, in-memory-only PrintLogHistory.
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    exerciser = UartLinkExerciser(driver, ROLE_INITIATOR)
    assert type(exerciser.pr).__name__ == "PrintLogHistory"
    assert not hasattr(exerciser.pr, "fram")


def test_fram_backed_variant_survives_a_reboot() -> None:
    # Own-chunk path: errno history persists through a simulated FRAM write/read cycle, mirroring
    # every other fram_target-wirable driver's own reboot test (e.g. test_asy_neopixel_driver.py's
    # test_fram_backed_variant_survives_a_reboot).
    chunk = _FakeFramChunk()
    fram = _FakeFramManager(chunk)
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    exerciser1 = UartLinkExerciser(driver, ROLE_INITIATOR, fram=fram)  # type: ignore[arg-type]
    assert type(exerciser1.pr).__name__ == "PrintLogHistoryStore"

    async def scenario1() -> None:
        await exerciser1.pr.setup()  # FRAM persistence is inert until setup() runs
        await exerciser1.pr.err_s("boom", errno=1)

    run(scenario1())

    driver2 = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS)
    exerciser2 = UartLinkExerciser(driver2, ROLE_RESPONDER, fram=fram)  # type: ignore[arg-type]

    async def scenario2() -> None:
        await exerciser2.pr.setup()

    run(scenario2())
    assert exerciser2.pr.err_count == exerciser1.pr.err_count


def test_fram_allocation_failure_falls_back_to_ram_only_without_crashing() -> None:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    exerciser = UartLinkExerciser(driver, ROLE_INITIATOR, fram=_RaisingFramManager())  # type: ignore[arg-type]
    assert isinstance(exerciser.pr, PrintLogHistoryStore)  # allocation attempted...
    assert exerciser.pr.fram is None  # ...but degraded to RAM-only, not crashed
    run(exerciser.pr.err_s("still logs, just not durably", errno=1))
    assert exerciser.pr.err_count == 1


def test_a_transient_fram_write_failure_does_not_break_logging_or_transfers() -> None:
    # Resilience: a write hiccup mid-operation must not crash the exerciser or the link it wraps -
    # print_log.py's own broad exception guard plus PrintLogHistoryStore._write()'s bool return are
    # what make this safe; this test proves it end to end through UartLinkExerciser's own forwarding.
    chunk = _FakeFramChunk()
    chunk.fail_writes = 1
    fram = _FakeFramManager(chunk)
    driver_a = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    driver_b = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS)
    fake_a: FakeUART = driver_a._uart  # type: ignore[assignment]
    fake_b: FakeUART = driver_b._uart  # type: ignore[assignment]
    UARTLink(fake_a, fake_b)
    driver_a.poller = LinkPoller(fake_a)  # type: ignore[assignment]
    driver_b.poller = LinkPoller(fake_b)  # type: ignore[assignment]
    initiator = UartLinkExerciser(driver_a, ROLE_INITIATOR)
    responder = UartLinkExerciser(driver_b, ROLE_RESPONDER, fram=fram)  # type: ignore[arg-type]

    async def go() -> None:
        assert await initiator.setup() and await responder.setup()
        await responder._comm.pr.err_s("first write fails", errno=1)  # swallowed, returns False internally
        listener = asyncio.create_task(responder._comm.uart_listen())
        try:
            answer = await initiator._comm.uart_get(0x01)
        finally:
            await asyncio.wait_for(listener, 5)
        assert answer is not None and bytes(answer) == b"dev-uart-crossover"  # the link itself is unaffected

    run(go())


def test_logger_reach_through_shares_the_upstream_pr_object() -> None:
    driver_a = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    driver_b = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS)
    upstream = UartLinkExerciser(driver_a, ROLE_INITIATOR, name_ext="up")
    downstream = UartLinkExerciser(driver_b, ROLE_RESPONDER, name_ext="down", logger=upstream.pr)
    assert downstream.pr is upstream.pr  # the AsyFramManager-style reach-through (base_classes.py's own precedent)
    assert downstream.name == "UART_down"  # its own identity is independent of the shared logger's own name
    assert downstream.get_loggers() == [upstream.pr]


def test_fram_and_logger_are_mutually_exclusive_logger_wins() -> None:
    # Both wired at once is not a schema requirement to reject (buildgen.validate.py adds no such
    # check today) - UART_Comm's own make_logger()-vs-logger precedence already resolves it: the
    # reach-through wins and the fram= chunk is never touched. Pinned here so a change to that
    # precedence is a deliberate decision, not a silent behavior change for this wrapper.
    chunk = _FakeFramChunk()
    fram = _FakeFramManager(chunk)
    upstream_driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    upstream = UartLinkExerciser(upstream_driver, ROLE_INITIATOR, name_ext="up")
    driver = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS)
    exerciser = UartLinkExerciser(driver, ROLE_RESPONDER, name_ext="down", fram=fram, logger=upstream.pr)  # type: ignore[arg-type]
    assert exerciser.pr is upstream.pr
    assert not hasattr(exerciser.pr, "fram")  # upstream's own plain, in-memory PrintLogHistory


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
