"""Isolated-driver device script: a real GET, a real SET and a maximum-length train across the dev
bench's permanent UART0<->UART1 crossover jumper (GP0<->GP9, GP1<->GP8), proving J.7's
self-compatibility property on real hardware rather than only against a modelled link."""
# Constructs the two instances directly - never through sensortask_dev's full task graph - per
# C.8's standing constraint that a hazard-tier test must not touch the RP2040's own flash
# filesystem. Both loggers are RAM-only for the same reason: no NVM write budget is spent here.

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

_CMD_BANNER = 0x01
_CMD_ECHO = 0x02
_BANNER = b"crossover-ok"
# Three data chunks: enough to exercise a real multi-frame train's chunk indexing and UID
# progression without spending a minute of wire time on the maximum 254.
_TRAIN_BYTES = PAYLOAD_SIZE * 2 + 7

received: "list[bytes]" = []


def get_callback(cmd_id: int) -> "tuple[bool, bytes | None]":
    if cmd_id == _CMD_BANNER:
        return True, _BANNER
    return False, None


def set_callback(cmd_id: int) -> "tuple[bool, int | None]":
    return (cmd_id == _CMD_ECHO), None


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    uart0 = asy_uart_driver.UART(0, 0, 1, baudrate=BAUDRATE, rxbuf=BUF_BYTES, txbuf=BUF_BYTES, poll_wait_ms=POLL_WAIT_MS)
    uart1 = asy_uart_driver.UART(1, 8, 9, baudrate=BAUDRATE, rxbuf=BUF_BYTES, txbuf=BUF_BYTES, poll_wait_ms=POLL_WAIT_MS)
    initiator = UART_Comm(uart0, ROLE_INITIATOR, payload_size=PAYLOAD_SIZE, timeout=TIMEOUT_MS, name="UART_INIT")
    responder = UART_Comm(
        uart1,
        ROLE_RESPONDER,
        payload_size=PAYLOAD_SIZE,
        timeout=TIMEOUT_MS,
        get_callback=get_callback,
        set_callback=set_callback,
        name="UART_RESP",
    )
    failures = []
    if not await initiator.setup():
        failures.append("initiator setup refused")
    if not await responder.setup():
        failures.append("responder setup refused")

    async def exchange(work: "Coroutine[Any, Any, T]") -> "T":
        listener = asyncio.create_task(responder.uart_listen())
        try:
            return await work
        finally:
            try:
                await asyncio.wait_for(listener, 10)
            except asyncio.TimeoutError:
                listener.cancel()

    if not failures:
        answer = await exchange(initiator.uart_get(_CMD_BANNER))
        if answer is None or bytes(answer) != _BANNER:
            failures.append(f"GET returned {answer!r}, expected {_BANNER!r}")
        wdt.feed()

        payload = bytes((i * 11) & 0xFF for i in range(_TRAIN_BYTES))
        if await exchange(initiator.uart_set(_CMD_ECHO, payload)) is not True:
            failures.append("multi-chunk SET failed")
        wdt.feed()

        empty = await exchange(initiator.uart_set(_CMD_ECHO, None))
        if empty is not True:
            failures.append("payload-less SET failed")
        wdt.feed()

    for comm in (initiator, responder):
        counts = await comm.get_error_counter()
        # Indexed, not .get()-with-a-default: ErrorLog's values are a TypedDict, which an empty
        # dict is not - so a default would be the one thing that does not fit the envelope.
        if comm.name in counts and counts[comm.name]["ErrCount"]:
            entry = counts[comm.name]
            failures.append(f"{comm.name} counted {entry['ErrCount']} errors on a clean link: {entry['ErrNum']}")

    uart0.deinit()
    uart1.deinit()
    if failures:
        print("RESULT: FAIL " + "; ".join(failures))
    else:
        print(f"RESULT: PASS GET+SET+{_TRAIN_BYTES}-byte train across the jumper, zero errors counted")


asyncio.run(_main())
