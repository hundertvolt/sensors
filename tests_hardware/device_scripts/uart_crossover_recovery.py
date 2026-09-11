"""Isolated-driver device script: the failure half of the crossover-jumper tier - one-sided silence
recovers within the specified window, and a deliberately mismatched payload_size fails loudly
rather than silently corrupting, which is the one configuration error the design cannot self-heal."""
# The fault knobs sit behind a small injector object (H5): the flash tier drives them through the
# peripherals themselves, and a future external injector implements the same three methods, so these
# bodies need no reshaping. Inline because `mpremote run` uploads exactly one file.

import asyncio

import machine

import asy_uart_driver
from asy_uart_comm import ROLE_INITIATOR, ROLE_RESPONDER, UART_Comm

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

PAYLOAD_SIZE = 48
TIMEOUT_MS = 1000
BAUDRATE = 115200
POLL_WAIT_MS = 2
BUF_BYTES = 512
_CMD_ECHO = 0x02


class PeripheralInjector:
    # The flash-tier adapter: faults are produced with the real peripherals. silence() turns the
    # responder's UART off, so its traffic genuinely stops arriving rather than being filtered in
    # software; desync() re-inits it at a baud rate the other end does not share.
    def __init__(self, driver: "asy_uart_driver.UART", port_id: int, tx: int, rx: int) -> None:
        self._driver = driver
        self._port_id = port_id
        self._tx = tx
        self._rx = rx

    def _reinit(self, baudrate: int) -> None:
        self._driver.init(
            self._port_id, self._tx, self._rx, baudrate=baudrate, rxbuf=BUF_BYTES, txbuf=BUF_BYTES,
        )

    def silence(self) -> None:
        self._driver.deinit()

    def desync(self) -> None:
        self._reinit(BAUDRATE // 4)

    def restore(self) -> None:
        self._reinit(BAUDRATE)


def get_callback(cmd_id: int) -> "tuple[bool, bytes | None]":
    return True, b"v"


def set_callback(cmd_id: int) -> "tuple[bool, int | None]":
    return (cmd_id == _CMD_ECHO), None


def _build(payload_size_b: int) -> "tuple[asy_uart_driver.UART, asy_uart_driver.UART, UART_Comm, UART_Comm]":
    uart0 = asy_uart_driver.UART(0, 0, 1, baudrate=BAUDRATE, rxbuf=BUF_BYTES, txbuf=BUF_BYTES, poll_wait_ms=POLL_WAIT_MS)
    uart1 = asy_uart_driver.UART(1, 8, 9, baudrate=BAUDRATE, rxbuf=BUF_BYTES, txbuf=BUF_BYTES, poll_wait_ms=POLL_WAIT_MS)
    initiator = UART_Comm(uart0, ROLE_INITIATOR, payload_size=PAYLOAD_SIZE, timeout=TIMEOUT_MS, name="UART_INIT")
    responder = UART_Comm(
        uart1,
        ROLE_RESPONDER,
        payload_size=payload_size_b,
        timeout=TIMEOUT_MS,
        get_callback=get_callback,
        set_callback=set_callback,
        name="UART_RESP",
    )
    return uart0, uart1, initiator, responder


async def _exchange(responder: UART_Comm, work: "Coroutine[Any, Any, T]") -> "T":
    listener = asyncio.create_task(responder.uart_listen())
    try:
        return await work
    finally:
        try:
            await asyncio.wait_for(listener, 12)
        except asyncio.TimeoutError:
            listener.cancel()


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    failures = []

    uart0, uart1, initiator, responder = _build(PAYLOAD_SIZE)
    await initiator.setup()
    await responder.setup()
    injector = PeripheralInjector(uart1, 1, 8, 9)

    injector.silence()
    if await _exchange(responder, initiator.uart_set(_CMD_ECHO, b"lost")) is not False:
        failures.append("a transfer into a silent peer reported success")
    wdt.feed()

    injector.restore()
    await responder.clear()
    if await _exchange(responder, initiator.uart_set(_CMD_ECHO, b"back")) is not True:
        failures.append("the link did not recover after the peer returned")
    wdt.feed()
    uart0.deinit()
    uart1.deinit()

    # A mismatched payload_size is agreed out of band and never negotiated, so it cannot be
    # recovered from - only diagnosed. What must be true is that it fails, loudly, rather than
    # delivering a wrong-length payload as if it were right.
    uart0, uart1, initiator, responder = _build(PAYLOAD_SIZE + 8)
    await initiator.setup()
    await responder.setup()
    if await _exchange(responder, initiator.uart_set(_CMD_ECHO, b"mismatched")) is not False:
        failures.append("a payload_size mismatch was not detected")
    counts = await initiator.get_error_counter()
    if "UART_INIT" not in counts or not counts["UART_INIT"]["ErrCount"]:
        failures.append("a payload_size mismatch produced no logged error at all")
    uart0.deinit()
    uart1.deinit()

    if failures:
        print("RESULT: FAIL " + "; ".join(failures))
    else:
        print("RESULT: PASS one-sided silence recovered; payload_size mismatch failed loudly")


asyncio.run(_main())
