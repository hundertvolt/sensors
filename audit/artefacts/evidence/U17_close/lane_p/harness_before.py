"""Shared harness for the UARTComm tests: two real instances over tests/machine.py's crossover
link, driven as concurrent tasks the way the dev bench drives them across its jumper.
Kept out of the test files themselves so the mock and hazard tiers build the pair identically."""

import asyncio
import select
import time

from machine import UART as FakeUART
from machine import LinkPoller, UARTLink
from rp2 import DMA

import asy_uart_comm
import asy_uart_driver
from asy_uart_comm import DEFAULT_LIMITS, ROLE_INITIATOR, ROLE_RESPONDER, ResponderCallbacks, TransferLimits, UARTComm
from asy_uart_driver import UART

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, Protocol, TypeVar

    from asy_base_classes import PieceBuffer
    from asy_crc_checks import CRCBase

    T = TypeVar("T")

    # Every protocol callback is (cmd_id) -> (valid, value), sync or async, so the result is either
    # the pair or a coroutine yielding it - `object` says exactly that. A Protocol rather than a
    # Callable alias, so it matches asy_uart_comm.py's named-parameter form structurally.
    class CommCallback(Protocol):
        def __call__(self, cmd_id: int) -> object: ...

    class MessageCallback(Protocol):
        def __call__(self, cmd_id: int, cmd: int, payload: "PieceBuffer | None") -> object: ...

PAYLOAD_SIZE = 8
# @tunable l1.uart_comm_harness_timeout_ms = 100
TIMEOUT_MS = 100
# @tunable l1.uart_comm_harness_poll_wait_ms = 1
POLL_WAIT_MS = 1
# @tunable l1.uart_comm_harness_run_limit_s = 10
RUN_LIMIT_S = 10
# @tunable l1.uart_comm_harness_listener_drain_s = 5
LISTENER_DRAIN_S = 5


def run(coro: "Coroutine[Any, Any, T]", limit: int = RUN_LIMIT_S) -> "T":
    # Every test is bounded: a protocol wedge must surface as a fast FAIL, never as a hung file.
    return asyncio.run(asyncio.wait_for(coro, limit))


def fake_of(driver: UART) -> FakeUART:
    return driver._uart  # type: ignore[return-value]


class Pair:
    # One initiator and one responder across a crossover link, plus the link itself so a test can
    # reach its fault knobs and its wire log.
    def __init__(
        self,
        payload_size: int = PAYLOAD_SIZE,
        timeout: int = TIMEOUT_MS,
        get_callback: "CommCallback | None" = None,
        set_callback: "CommCallback | None" = None,
        message_callback: "MessageCallback | None" = None,
        crc_a: "CRCBase | None" = None,
        crc_b: "CRCBase | None" = None,
        limits: "TransferLimits | None" = None,
        **comm_kwargs: "Any",
    ) -> None:
        # crc_a/crc_b are per-bus, not per-Comm: the CRC sits on the UART object below the protocol
        # and is invisible to it (SPECIFICATION.md Part J). Both ends must agree, so a test that
        # passes only one models a mismatched pair rather than a protected link.
        DMA.reset_registry()  # no per-test reset exists, and each link's ring holds two of the twelve channels
        self.driver_a = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, crc=crc_a)
        self.driver_b = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, crc=crc_b)
        self.fake_a = fake_of(self.driver_a)
        self.fake_b = fake_of(self.driver_b)
        self.link = UARTLink(self.fake_a, self.fake_b)
        self.fake_a.rx_rate = self.fake_b.rx_rate = float("inf")  # bytes land at once, not on the fake clock
        # A bounded stand-in, never a real select.poll(): the Unix port does not re-evaluate a
        # Python object's ioctl() after registration (CLAUDE.md's known CI hang). Only TX polls.
        self.driver_a.poller = LinkPoller(self.fake_a, mask=select.POLLOUT)  # type: ignore[assignment]
        self.driver_b.poller = LinkPoller(self.fake_b, mask=select.POLLOUT)  # type: ignore[assignment]
        # A test needing other receive limits passes one limits, which then carries its frame and timeout too.
        limits = limits if limits is not None else transfer_limits(payload_size=payload_size, timeout=timeout)
        self.initiator = UARTComm(self.driver_a, ROLE_INITIATOR, limits=limits, name="UART_A", **comm_kwargs)
        self.responder = UARTComm(
            self.driver_b,
            ROLE_RESPONDER,
            limits=limits,
            callbacks=ResponderCallbacks(get_callback, set_callback, message_callback),
            name="UART_B",
            **comm_kwargs,
        )

    async def setup(self) -> bool:
        return await self.initiator.setup() and await self.responder.setup()

    def wire_from_initiator(self) -> bytes:
        return bytes(self.link.direction_from(self.fake_a).wire_log)

    def wire_from_responder(self) -> bytes:
        return bytes(self.link.direction_from(self.fake_b).wire_log)

    async def with_listener(self, work: "Coroutine[Any, Any, T]", rounds: int = 1, *, listener_may_stall: bool = False) -> "T":
        # Runs the responder's listen loop alongside the initiator's call: a stop-and-wait exchange
        # only progresses when both ends are scheduled. A listener still short of its rounds after the
        # drain fails the exchange, unless the test declares the stall (a frame it cut on purpose).
        listener = asyncio.create_task(self._listen_rounds(rounds))
        return await awaited_with_listener(work, listener, rounds, may_stall=listener_may_stall)

    async def _listen_rounds(self, rounds: int) -> None:
        for _ in range(rounds):
            await self.responder.uart_listen()


async def build_pair(**kwargs: "Any") -> Pair:
    pair = Pair(**kwargs)
    await pair.setup()
    return pair


def frames(wire: bytes, frame_size: int) -> "list[bytes]":
    return [wire[i : i + frame_size] for i in range(0, len(wire), frame_size)]


def copied_out(received: "PieceBuffer | None") -> "bytes | None":
    # A train received without a caller's buffer arrives as a PieceBuffer, which has no __eq__: tests compare
    # its bytes through this one copy-out.
    if received is None:
        return None
    dest = bytearray(len(received))
    assert received.copy_into(dest), "copy_into() refused a destination of the buffer's own length"
    return bytes(dest)


def transfer_limits(
    payload_size: int = PAYLOAD_SIZE,
    timeout: int = TIMEOUT_MS,
    chunk_bytes: int = DEFAULT_LIMITS.chunk_bytes,
    max_transfer_bytes: int = DEFAULT_LIMITS.max_transfer_bytes,
) -> TransferLimits:
    # UARTComm takes its limits as one TransferLimits: a test names only the fields it changes, the rest
    # being this harness's frame and timeout and the module's receive defaults.
    return TransferLimits(payload_size, timeout, chunk_bytes, max_transfer_bytes)


class PollRoundClock:
    # The UART modules' deadlines on a clock only they advance: by each of their sleeps, and 1 ms per read so a wait
    # that never yields still expires. On the wall clock a host stall expires a reply budget: a clean run loses a
    # transaction, and one still recovering when the heap is sampled reads as retention (agent, 2026-10-07).
    def __init__(self, stall_after: int = 0, stall_ms: int = 0) -> None:
        self._stall = [0, stall_after, stall_ms, 0]  # countdown (0 = idle), its start, the stall, whether it fired
        self._saved: tuple[Any, Any, Any, Any] | None = None

    def __enter__(self) -> "PollRoundClock":
        self._saved = (asy_uart_comm.time, asy_uart_comm.asyncio, asy_uart_driver.time, asy_uart_driver.asyncio)
        now: list[Any] = [time.ticks_ms()]  # the real value: deadlines stored before entry stay comparable
        stall = self._stall

        class _Time:
            ticks_add = staticmethod(time.ticks_add)
            ticks_diff = staticmethod(time.ticks_diff)

            @staticmethod
            def ticks_ms() -> int:
                now[0] = time.ticks_add(now[0], 1)
                return int(now[0])

        class _Asyncio:
            # Only what the two modules use at run time: a new attribute there fails here until it is added.
            Lock = asyncio.Lock
            get_event_loop = staticmethod(asyncio.get_event_loop)

            @staticmethod
            async def sleep_ms(ms: int) -> None:
                now[0] = time.ticks_add(now[0], ms)
                await asyncio.sleep_ms(ms)
                if stall[0] > 0:
                    stall[0] -= 1
                    if stall[0] == 0 and stall[2]:
                        time.sleep_ms(stall[2])  # the whole interpreter blocked: a host deschedule
                        stall[3] = 1

        asy_uart_driver.asyncio = asy_uart_comm.asyncio = _Asyncio()  # type: ignore[assignment]
        asy_uart_driver.time = asy_uart_comm.time = _Time()  # type: ignore[assignment]
        return self

    def __exit__(self, *exc_info: object) -> None:
        assert self._saved is not None
        asy_uart_comm.time, asy_uart_comm.asyncio, asy_uart_driver.time, asy_uart_driver.asyncio = self._saved
        self._saved = None

    def arm(self) -> None:
        # Counts down to the one planted stall: stall_after sleeps on, the whole interpreter blocks for stall_ms.
        self._stall[0], self._stall[3] = self._stall[1], 0

    def disarm(self) -> bool:
        # True when the planted stall fired between arm() and here, or when none was planted.
        self._stall[0] = 0
        return not self._stall[2] or self._stall[3] == 1


def echo_get(payload: "bytes | bytearray | None") -> "CommCallback":
    def callback(cmd_id: int) -> "tuple[bool, bytes | bytearray | None]":
        return True, payload

    return callback


def accept_set(exp_size: "int | None" = None) -> "CommCallback":
    def callback(cmd_id: int) -> "tuple[bool, int | None]":
        return True, exp_size

    return callback


async def awaited_with_listener(work: "Coroutine[Any, Any, T]", listener: "asyncio.Task[None]", rounds: int, *, may_stall: bool) -> "T":
    # The initiator's own failure wins: a stall behind it is its consequence, never reported over it.
    try:
        result = await work
    except BaseException:
        await _drain_listener(listener)
        raise
    if not await _drain_listener(listener) and not may_stall:
        msg = f"the responder's listener did not finish its {rounds} round(s) within {LISTENER_DRAIN_S} s"
        raise AssertionError(msg)
    return result


async def _drain_listener(listener: "asyncio.Task[None]") -> bool:
    # True when the listener finished its rounds; a stalled one is cancelled and reported as False.
    try:
        await asyncio.wait_for(listener, LISTENER_DRAIN_S)
    except asyncio.TimeoutError:
        listener.cancel()
        try:
            await listener
        except asyncio.CancelledError:  # expected; anything else is a real failure
            pass
        return False
    return True
