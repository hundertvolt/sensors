"""Shared harness for the UART_Comm tests: two real instances over tests/machine.py's crossover
link, driven as concurrent tasks the way the dev bench drives them across its jumper.
Kept out of the test files themselves so the mock and hazard tiers build the pair identically."""

import asyncio

from machine import UART as FakeUART
from machine import LinkPoller, UARTLink

from asy_uart_comm import ROLE_INITIATOR, ROLE_RESPONDER, UART_Comm
from asy_uart_driver import UART

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, Protocol, TypeVar

    T = TypeVar("T")

    # Every protocol callback is (cmd_id) -> (valid, value), sync or async, so the result is either
    # the pair or a coroutine yielding it - `object` says exactly that. A Protocol rather than a
    # Callable alias, so it matches asy_uart_comm.py's named-parameter form structurally.
    class CommCallback(Protocol):
        def __call__(self, cmd_id: int) -> object: ...

PAYLOAD_SIZE = 8
TIMEOUT_MS = 100
POLL_WAIT_MS = 1


def run(coro: "Coroutine[Any, Any, T]", limit: int = 10) -> "T":
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
        **comm_kwargs: "Any",
    ) -> None:
        self.driver_a = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS)
        self.driver_b = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS)
        self.fake_a = fake_of(self.driver_a)
        self.fake_b = fake_of(self.driver_b)
        self.link = UARTLink(self.fake_a, self.fake_b)
        # A bounded stand-in, never a real select.poll(): the Unix port does not re-evaluate a
        # Python object's ioctl() after registration (CLAUDE.md's known CI hang).
        self.driver_a.poller = LinkPoller(self.fake_a)  # type: ignore[assignment]
        self.driver_b.poller = LinkPoller(self.fake_b)  # type: ignore[assignment]
        self.initiator = UART_Comm(
            self.driver_a, ROLE_INITIATOR, payload_size=payload_size, timeout=timeout, name="UART_A", **comm_kwargs,
        )
        self.responder = UART_Comm(
            self.driver_b,
            ROLE_RESPONDER,
            payload_size=payload_size,
            timeout=timeout,
            get_callback=get_callback,
            set_callback=set_callback,
            name="UART_B",
            **comm_kwargs,
        )

    async def setup(self) -> bool:
        return await self.initiator.setup() and await self.responder.setup()

    def wire_from_initiator(self) -> bytes:
        return bytes(self.link.direction_from(self.fake_a).wire_log)

    def wire_from_responder(self) -> bytes:
        return bytes(self.link.direction_from(self.fake_b).wire_log)

    async def with_listener(self, work: "Coroutine[Any, Any, T]", rounds: int = 1) -> "T":
        # Runs the responder's listen loop alongside the initiator's call: a stop-and-wait exchange
        # only progresses when both ends are scheduled. The initiator returning does not mean the
        # responder is done, so the listener is awaited out and cancelled only if it truly stalls.
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
                except asyncio.CancelledError:  # expected; anything else is a real failure
                    pass

    async def _listen_rounds(self, rounds: int) -> None:
        for _ in range(rounds):
            await self.responder.uart_listen()


async def build_pair(**kwargs: "Any") -> Pair:
    pair = Pair(**kwargs)
    await pair.setup()
    return pair


def frames(wire: bytes, frame_size: int) -> "list[bytes]":
    return [wire[i : i + frame_size] for i in range(0, len(wire), frame_size)]


def echo_get(payload: "bytes | bytearray | None") -> "CommCallback":
    def callback(cmd_id: int) -> "tuple[bool, bytes | bytearray | None]":
        return True, payload

    return callback


def accept_set(exp_size: "int | None" = None) -> "CommCallback":
    def callback(cmd_id: int) -> "tuple[bool, int | None]":
        return True, exp_size

    return callback
