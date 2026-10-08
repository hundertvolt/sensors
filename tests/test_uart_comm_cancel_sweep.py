"""Mock-tier comm-hazard sweep for the UART protocol (SPECIFICATION.md Part J.5, J.7): a transaction cancelled or
cleared at any await leaves the instance free and the peer recovering through J.5. The rest of the tier, the reboot
case among it, is test_uart_comm_hazard.py; both share _uart_comm_hazard_common.py."""

import asyncio

from _uart_comm_harness import Pair, PollRoundClock, copied_out, run
from _uart_comm_hazard_common import _EXCHANGE_LIMIT_S, _PAYLOAD, _STEP_BOUND_S, hazard_pair, register_both_crc_modes

import asy_uart_comm
from asy_uart_comm import UARTComm

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from _uart_comm_hazard_common import CrcMaker

_SWEEP_PAYLOAD = bytes(range(1, _PAYLOAD * 2 + 1))  # three chunks of distinct bytes: a misplaced one cannot pass


class _Stepper:
    # Parks the work task at its k-th await through the UART modules' own sleep, so the watcher acts at exactly
    # that await; k = 0 parks nothing and only counts. The CRC's per-byte yields are not steps: between two of
    # the modules' awaits they change no protocol state.
    def __init__(self, k: int) -> None:
        assert asy_uart_comm.asyncio is not asyncio, "the sweep patches the poll-round clock's namespace, never asyncio"
        self.k = k
        self.count = 0
        self.finished = False
        self.finished_first = False  # finished before the watcher acted: the sweep's end
        self.task: asyncio.Task[None] | None = None
        self.reached = asyncio.Event()
        self.release = asyncio.Event()
        self._sleep = asy_uart_comm.asyncio.sleep_ms
        asy_uart_comm.asyncio.sleep_ms = self._stepped  # type: ignore[assignment]

    async def _stepped(self, ms: int) -> None:
        if asyncio.current_task() is self.task:
            self.count += 1
            if self.count == self.k:
                self.reached.set()
                await self.release.wait()
        await self._sleep(ms)

    def detach(self) -> None:
        asy_uart_comm.asyncio.sleep_ms = self._sleep

    async def track(self, work: "Coroutine[object, object, object]") -> None:
        try:
            await work
            self.finished = True
        finally:
            self.reached.set()


def _assert_free(comm: UARTComm) -> None:
    clock = asy_uart_comm.time
    assert comm._busy is False, f"{comm.name} is still marked busy"
    assert comm._in_resync is False, f"{comm.name} is still marked inside a resync"
    assert comm._uart is not None and comm._uart.session_lock.locked() is False, f"{comm.name}'s session lock is still held"
    if comm._holdoff_active:
        remaining = clock.ticks_diff(comm._holdoff_deadline, clock.ticks_ms())
        assert 0 < remaining <= comm._resync_window_ms(), f"{comm.name}'s hold-off has {remaining} ms left"


async def _cancel_at(pair: Pair, stepper: _Stepper, work: "Coroutine[object, object, object]", peer: "Coroutine[object, object, None]", *, cancel: bool) -> None:
    # The watcher: at the work's k-th await it cancels the work, or clears the responder and lets the work go on.
    offered = _offered(pair)
    peer_task = asyncio.create_task(peer)
    work_task = asyncio.create_task(stepper.track(work))
    stepper.task = work_task
    await stepper.reached.wait()
    stepper.finished_first = stepper.finished
    if not stepper.finished and stepper.k:
        if cancel:
            work_task.cancel()
        else:
            await pair.responder.clear()
        stepper.release.set()
    try:
        await work_task
    except asyncio.CancelledError:
        if not cancel:
            raise
    await _end_peer(pair, peer_task, offered)


async def _end_peer(pair: Pair, task: "asyncio.Task[None]", offered: int) -> None:
    # A listener no byte reached since `offered` is parked without a deadline: clear() is its documented unstick.
    # Any other task is inside a transaction and ends on its own deadline.
    if not task.done() and _offered(pair) == offered:
        await pair.responder.clear()
    await asyncio.wait_for(task, _STEP_BOUND_S)


def _error_count(comm: UARTComm) -> int:
    return int(run(comm.get_error_counter())[comm.name]["ErrCount"])


def _get_with_listener(pair: Pair) -> bool:
    async def exchange() -> bytes | None:
        offered = _offered(pair)
        listener = asyncio.create_task(_listen_recording(pair, []))
        answer = await pair.initiator.uart_get(1)
        await _end_peer(pair, listener, offered)
        return copied_out(answer)

    return run(exchange(), limit=_EXCHANGE_LIMIT_S) == _SWEEP_PAYLOAD


async def _listen_recording(pair: Pair, delivered: "list[bytes | None]") -> None:
    result = await pair.responder.uart_listen()
    if result.cmd_id is not None:
        delivered.append(copied_out(result.payload))


def _offered(pair: Pair) -> int:
    return pair.link.direction_from(pair.fake_a).offered


def _pull(chunk: int, buf: memoryview) -> int:
    # Chunk 2 carries the first payload bytes: chunk 1 is the command id.
    start = (chunk - 2) * _PAYLOAD
    part = _SWEEP_PAYLOAD[start : start + len(buf)]
    buf[0 : len(part)] = part
    return len(part)


def _restarted_listener_answers(pair: Pair) -> bool:
    # The supervisor's restart path: a fresh listen task from the starter, cancelled once it answered or not.
    async def exchange() -> bool:
        task = pair.responder.start_asy_listen()
        try:
            return copied_out(await pair.initiator.uart_get(1)) == _SWEEP_PAYLOAD
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:  # expected
                pass

    return run(exchange(), limit=_EXCHANGE_LIMIT_S) is True


def _set_with_listener(pair: Pair) -> bool:
    delivered: list[bytes | None] = []

    async def exchange() -> bool:
        offered = _offered(pair)
        listener = asyncio.create_task(_listen_recording(pair, delivered))
        sent = await pair.initiator.uart_set(1, _SWEEP_PAYLOAD)
        await _end_peer(pair, listener, offered)
        return sent

    return run(exchange(), limit=_EXCHANGE_LIMIT_S) is True and delivered == [_SWEEP_PAYLOAD]


def _sweep(
    crc: "CrcMaker",
    make_work: "Callable[[Pair, list[bytes | None]], tuple[Coroutine[object, object, object], Coroutine[object, object, None]]]",
    *,
    cancel: bool,
    recover: "Callable[[Pair], bool]",
) -> None:
    # make_work returns the work and the coroutine running beside it; a fresh pair per k, built at synchronous
    # scope. The sweep ends at the first k the work finishes before; twice the clean run's awaits is its ceiling.
    with PollRoundClock() as clock:
        k = 0
        clean = -1
        while True:
            # timeout_for(), never a bare _TIMEOUT_MS: on a slow host a waiter gains a poll round at each per-byte CRC
            # yield of its peer, 79 virtual ms for one CRC16 reply at that limit, which 30 ms does not cover (Part J.7).
            pair = hazard_pair(crc, answer=_SWEEP_PAYLOAD)
            delivered: list[bytes | None] = []
            work, peer = make_work(pair, delivered)
            stepper = _Stepper(k)
            # The clean run (k = 0) yields where it would sleep, so it takes every poll round a host could add: twice
            # its awaits bounds each later run on any host, a slow one included (Part J.7).
            clock.pace(real=k > 0)
            try:
                run(_cancel_at(pair, stepper, work, peer, cancel=cancel), limit=_EXCHANGE_LIMIT_S)
            finally:
                clock.pace(real=True)
                stepper.detach()
            if k == 0:
                assert stepper.finished, "the uncancelled work did not finish"
                clean = stepper.count
            elif stepper.finished_first:
                return
            assert k <= 2 * clean, f"step {k} is past twice the clean run's {clean} awaits: a wait that never ends"
            for comm in (pair.initiator, pair.responder):
                _assert_free(comm)
            for attempt in range(2):
                before = _error_count(pair.initiator)
                if recover(pair):
                    break
                assert attempt == 0, f"no recovery within two transactions after step {k}"
                assert _error_count(pair.initiator) > before, f"the failed recovery after step {k} logged nothing"
            k += 1


def _check_cancelling_a_set_at_every_await_leaves_both_ends_consistent(crc: "CrcMaker") -> None:
    def work(pair: Pair, delivered: "list[bytes | None]") -> "tuple[Coroutine[object, object, object], Coroutine[object, object, None]]":
        return pair.initiator.uart_set(1, _SWEEP_PAYLOAD), _listen_recording(pair, delivered)

    _sweep(crc, work, cancel=True, recover=_set_with_listener)


def _check_cancelling_a_get_at_every_await_leaves_both_ends_consistent(crc: "CrcMaker") -> None:
    def work(pair: Pair, delivered: "list[bytes | None]") -> "tuple[Coroutine[object, object, object], Coroutine[object, object, None]]":
        return pair.initiator.uart_get(1), _listen_recording(pair, delivered)

    _sweep(crc, work, cancel=True, recover=_get_with_listener)


def _check_cancelling_a_set_stream_at_every_await_leaves_both_ends_consistent(crc: "CrcMaker") -> None:
    def work(pair: Pair, delivered: "list[bytes | None]") -> "tuple[Coroutine[object, object, object], Coroutine[object, object, None]]":
        return pair.initiator.uart_set_stream(1, len(_SWEEP_PAYLOAD), _pull), _listen_recording(pair, delivered)

    _sweep(crc, work, cancel=True, recover=_set_with_listener)


def _check_cancelling_a_listener_at_every_await_leaves_it_restartable(crc: "CrcMaker") -> None:
    async def peer(pair: Pair) -> None:
        await pair.initiator.uart_set(1, _SWEEP_PAYLOAD)

    def work(pair: Pair, delivered: "list[bytes | None]") -> "tuple[Coroutine[object, object, object], Coroutine[object, object, None]]":
        return _listen_recording(pair, delivered), peer(pair)

    _sweep(crc, work, cancel=True, recover=_restarted_listener_answers)


def _check_clear_at_every_await_leaves_the_transaction_whole_or_failed(crc: "CrcMaker") -> None:
    outcomes: list[tuple[object, list[bytes | None]]] = []

    async def recorded(pair: Pair, delivered: "list[bytes | None]") -> None:
        outcomes.append((await pair.initiator.uart_set(1, _SWEEP_PAYLOAD), delivered))

    def work(pair: Pair, delivered: "list[bytes | None]") -> "tuple[Coroutine[object, object, object], Coroutine[object, object, None]]":
        return recorded(pair, delivered), _listen_recording(pair, delivered)

    _sweep(crc, work, cancel=False, recover=_set_with_listener)
    assert outcomes, "the sweep ran no transaction"
    for sent, delivered in outcomes:
        assert sent in (True, False), f"a cleared transaction returned {sent!r}"
        # Whole: the peer holds exactly the payload. A False may still have been delivered (the lost-final-ACK seam).
        assert not sent or delivered == [_SWEEP_PAYLOAD], f"a transaction reported whole delivered {delivered!r}"
        assert delivered in ([], [_SWEEP_PAYLOAD]), f"a cleared transaction delivered part of its payload: {delivered!r}"


# Every sweep enters the poll-round clock itself: its clean run takes the clock's round-robin pacing (_sweep).
_OWN_CLOCK = (
    "cancelling_a_set_at_every_await_leaves_both_ends_consistent",
    "cancelling_a_get_at_every_await_leaves_both_ends_consistent",
    "cancelling_a_set_stream_at_every_await_leaves_both_ends_consistent",
    "cancelling_a_listener_at_every_await_leaves_it_restartable",
    "clear_at_every_await_leaves_the_transaction_whole_or_failed",
)
register_both_crc_modes(globals(), {}, _OWN_CLOCK)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
