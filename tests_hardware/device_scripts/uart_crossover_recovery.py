"""Isolated-driver device script: the failure half of the crossover-jumper tier - one-sided silence
recovers within the specified window, and a deliberately mismatched payload_size fails loudly
rather than silently corrupting, which is the one configuration error the design cannot self-heal."""
# The fault knobs sit behind a small injector object (H5): the flash tier drives them through the
# peripherals themselves, and a future external injector implements the same three methods, so these
# bodies need no reshaping. Inline because `mpremote run` uploads exactly one file.

import asyncio

import machine

import asy_uart_driver
from asy_uart_comm import ROLE_INITIATOR, ROLE_RESPONDER, ListenResult, UART_Comm

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
# Mirrors sensortask_dev.py's own pair: 2ms while a transaction is in flight, 50ms while the line
# is idle. A bench run that used one rate would not be exercising the shipped configuration.
POLL_IDLE_MS = 50
BUF_BYTES = 512
_CMD_ECHO = 0x02
# Every wait below is bounded and feeds as it goes: a link that never answers parks the listener in
# uart_listen()'s one unbounded read, and waiting that out outlasts the watchdog, so an injected
# fault resets the board instead of naming the failing check (measured on unjumpered pins).
JOIN_STEP_MS = 100
JOIN_BUDGET_MS = 2000


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
    uart0 = asy_uart_driver.UART(0, 0, 1, baudrate=BAUDRATE, rxbuf=BUF_BYTES, txbuf=BUF_BYTES, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_IDLE_MS)
    uart1 = asy_uart_driver.UART(1, 8, 9, baudrate=BAUDRATE, rxbuf=BUF_BYTES, txbuf=BUF_BYTES, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_IDLE_MS)
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


async def _settled(wdt: "machine.WDT", task: "asyncio.Task[ListenResult]") -> bool:
    # Polls rather than asyncio.wait_for(): the watchdog has to be fed while waiting, and a bounded
    # poll is the only shape that both waits and feeds.
    for _ in range(JOIN_BUDGET_MS // JOIN_STEP_MS):
        if task.done():
            return True
        wdt.feed()
        await asyncio.sleep_ms(JOIN_STEP_MS)
    return task.done()


async def _exchange(wdt: "machine.WDT", responder: UART_Comm, work: "Coroutine[Any, Any, T]") -> "T":
    listener = asyncio.create_task(responder.uart_listen())
    try:
        return await work
    finally:
        wdt.feed()  # the transaction above has its own timeout/resync budget to spend first
        # clear() is the module's own documented unstick for a listener parked in that unbounded
        # read (SPECIFICATION.md Part J.5) - it cannot finish on its own once its frame never came.
        if not await _settled(wdt, listener):
            await responder.clear()
            if not await _settled(wdt, listener):
                listener.cancel()
                await _settled(wdt, listener)


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    failures = []

    uart0, uart1, initiator, responder = _build(PAYLOAD_SIZE)
    await initiator.setup()
    await responder.setup()
    injector = PeripheralInjector(uart1, 1, 8, 9)

    injector.silence()
    if await _exchange(wdt, responder, initiator.uart_set(_CMD_ECHO, b"lost")) is not False:
        failures.append("a transfer into a silent peer reported success")
    wdt.feed()

    injector.restore()
    await responder.clear()
    if await _exchange(wdt, responder, initiator.uart_set(_CMD_ECHO, b"back")) is not True:
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
    if await _exchange(wdt, responder, initiator.uart_set(_CMD_ECHO, b"mismatched")) is not False:
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
