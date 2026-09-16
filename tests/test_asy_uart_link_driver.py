import asyncio

from machine import UART as FakeUART
from machine import LinkPoller, UARTLink

from asy_uart_comm import ROLE_INITIATOR, ROLE_RESPONDER
from asy_uart_driver import UART
from asy_uart_link_driver import UartLinkExerciser
from print_log import make_logger

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
# WP3 - optional FRAM support (was wrongly, deliberately excluded). UART_Comm's own fram=/logger=
# reach-through already existed (asy_uart_comm.py) and is unit-tested by the digital-twin FRAM-order
# check; what's new here is exclusively UartLinkExerciser's own forwarding, so that's what these
# cover - functionality, the no-fram= regression, the allocation-failure fallback, the logger=
# reach-through, and a reboot-survival roundtrip, mirroring test_asy_notification_service.py's own
# test_fram_backed_variant_survives_a_reboot() for the same class of claim.
# ---------------------------------------------------------------------------


class _FakeFramChunk:
    def __init__(self) -> None:
        self.buf = bytearray(64)

    def get_buffer(self) -> "_FakeFramChunk":
        return self

    def get_data_buf(self) -> bytearray:
        return self.buf

    async def write_into(self, buf: "_FakeFramChunk", *, override_pause: bool = False) -> bool:
        self.buf[:] = buf.get_data_buf()
        return True

    async def read_into(self, buf: "_FakeFramChunk", *, override_pause: bool = False) -> bool:
        buf.get_data_buf()[:] = self.buf
        return True


class _FakeFramManager:
    def __init__(self, chunk: "_FakeFramChunk | None" = None, *, fail: bool = False) -> None:
        self._chunk = chunk if chunk is not None else _FakeFramChunk()
        self._fail = fail

    def get_chunk(self, size: int, crc: "CRC_Base | None" = None, verify: int = 0, check_length: int = 8) -> "_FakeFramChunk":
        if self._fail:
            raise OSError("no room left on this fake chip")
        return self._chunk


def test_fram_kwarg_gives_the_instance_its_own_fram_backed_logger() -> None:
    from print_log import PrintLogHistoryStore

    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    initiator = UartLinkExerciser(driver, ROLE_INITIATOR, fram=_FakeFramManager())  # type: ignore[arg-type]
    assert isinstance(initiator.pr, PrintLogHistoryStore)
    assert initiator.pr.fram is not None


def test_no_fram_kwarg_stays_ram_only_exactly_as_before_wp3() -> None:
    # Regression: the pre-WP3 default (no fram=) must be byte-for-byte unaffected.
    from print_log import PrintLogHistory, PrintLogHistoryStore

    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    initiator = UartLinkExerciser(driver, ROLE_INITIATOR)
    assert isinstance(initiator.pr, PrintLogHistory)
    assert not isinstance(initiator.pr, PrintLogHistoryStore)


def test_fram_allocation_failure_degrades_to_ram_only_not_a_crash() -> None:
    from print_log import PrintLogHistoryStore

    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    initiator = UartLinkExerciser(driver, ROLE_INITIATOR, fram=_FakeFramManager(fail=True))  # type: ignore[arg-type]
    assert isinstance(initiator.pr, PrintLogHistoryStore)
    assert initiator.pr.fram is None


def test_logger_kwarg_reaches_through_to_an_already_built_sibling_logger() -> None:
    # The other half of UART_Comm's own reach-through (asy_uart_comm.py) - own chunk vs. sharing an
    # upstream instantiator's logger - now reachable through this wrapper too.
    driver_a = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
    driver_b = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS)
    owner = UartLinkExerciser(driver_a, ROLE_INITIATOR, fram=_FakeFramManager())  # type: ignore[arg-type]
    shared = UartLinkExerciser(driver_b, ROLE_RESPONDER, logger=owner.pr)
    assert shared.pr is owner.pr


def test_fram_backed_error_history_survives_a_simulated_reboot() -> None:
    async def go() -> None:
        chunk = _FakeFramChunk()
        fram = _FakeFramManager(chunk)

        driver1 = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
        before = UartLinkExerciser(driver1, ROLE_INITIATOR, fram=fram)  # type: ignore[arg-type]
        await before.setup()
        await before.pr.err_s("boom", errno=1)

        driver2 = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
        after = UartLinkExerciser(driver2, ROLE_INITIATOR, fram=fram)  # type: ignore[arg-type]
        await after.setup()
        assert after.pr.err_count == before.pr.err_count
        assert list(after.pr.history) == list(before.pr.history)

    run(go())


def test_a_persisted_fault_during_a_transfer_does_not_stall_other_tasks() -> None:
    # WP3's own blocking-latency requirement: the new fram= path must not introduce a blocking wait
    # anywhere the "never blocks the asyncio loop, not even in a wait state" rule (CLAUDE.md) covers.
    # asy_uart_comm.py itself is unchanged by this WP - every err_s()/_fault() call site already
    # awaited, and the fake FRAM chunk's write_into()/read_into() above are themselves coroutines -
    # so this proves the wiring didn't regress that invariant, not that the invariant was newly built.
    async def go() -> None:
        pair = await build_pair()
        pair.initiator._comm.pr = make_logger(_FakeFramManager(), name="UART_fram_test")
        ticks = 0

        async def ticker() -> None:
            nonlocal ticks
            while True:
                ticks += 1
                await asyncio.sleep_ms(1)

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

    run(go())


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
