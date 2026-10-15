"""Isolated-driver device script: the failure half of the crossover-jumper tier - one-sided silence and a baud desync
each fail a transfer and recover within the protocol's resync bound (timed), and a mismatched payload_size fails
loudly rather than silently corrupting, the one configuration error the design cannot self-heal."""
# The UART fault catalog is mock-only (no injection hardware will be bought, owner, 2026-09-22); this injector
# reaches the two faults the bench can make: silence and a baud mismatch.

import asyncio
import time

import asy_uart_driver
from asy_crc_checks import CRC16
from asy_uart_comm import DEFAULT_LIMITS, ROLE_INITIATOR, ROLE_RESPONDER, ResponderCallbacks, TransferLimits, UARTComm

# @include _shared/facts.py
# @include _shared/watchdog.py

# @include _shared/settle.py
# @include _shared/isl_error_log.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine

    import machine
    from _shared.facts import done, fact
    from _shared.isl_error_log import log_record
    from _shared.settle import settled
    from _shared.watchdog import arm
    from bench_facts import BenchFacts, BusFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

PAYLOAD_SIZE = 48  # the protocol's default frame, agreed out of band (J.6)
TIMEOUT_MS = 1000
_CMD_ECHO = 0x02
_DESYNC_DIVISOR = 4  # the responder re-initialised at a quarter of the line's baud rate
# The transfer the recovery is timed to: retried, fed, until it succeeds or the bound and one more timeout have passed.
_RECOVERY_RETRY_MS = 100


class PeripheralInjector:
    # Faults made with the real peripherals: silence() turns the responder's UART off, so its traffic stops arriving
    # rather than being filtered in software; desync() re-inits it at a baud rate the other end does not share. The
    # driver's init() re-applies the DMA receive set-up itself (RX interrupts masked, RXDMAE set, the ring re-armed).
    def __init__(self, driver: "asy_uart_driver.UART", bus: "BusFacts") -> None:
        self._driver = driver
        self._bus = bus

    def _reinit(self, baudrate: int) -> None:
        bus = self._bus
        self._driver.init(bus["id"], bus["tx_pin"], bus["rx_pin"], baudrate=baudrate, rxbuf=bus["rxbuf"], txbuf=bus["txbuf"], rx_ring=bus["rx_ring"])

    def desync(self) -> None:
        self._reinit(self._bus["baudrate"] // _DESYNC_DIVISOR)

    def restore(self) -> None:
        self._reinit(self._bus["baudrate"])

    def silence(self) -> None:
        self._driver.deinit()


def _build(payload_size_b: int) -> "tuple[asy_uart_driver.UART, asy_uart_driver.UART, UARTComm, UARTComm]":
    mode = BENCH.get("CRC_MODE", "none")
    drivers = []
    for label in ("uart_link_init", "uart_link_resp"):
        bus = BENCH["bus"][BENCH["instances"][label]["bus"]]
        drivers.append(asy_uart_driver.UART(
            bus["id"], bus["tx_pin"], bus["rx_pin"], baudrate=bus["baudrate"], rxbuf=bus["rxbuf"], txbuf=bus["txbuf"], rx_ring=bus["rx_ring"],
            poll_wait_ms=bus["poll_wait_ms"], poll_idle_ms=bus["poll_idle_ms"], crc=CRC16() if mode == "crc16" else None,
        ))
    initiator = UARTComm(drivers[0], ROLE_INITIATOR, limits=TransferLimits(PAYLOAD_SIZE, TIMEOUT_MS, DEFAULT_LIMITS.chunk_bytes, DEFAULT_LIMITS.max_transfer_bytes), name="UART_INIT")
    responder = UARTComm(
        drivers[1], ROLE_RESPONDER, limits=TransferLimits(payload_size_b, TIMEOUT_MS, DEFAULT_LIMITS.chunk_bytes, DEFAULT_LIMITS.max_transfer_bytes),
        callbacks=ResponderCallbacks(get_callback, set_callback, None), name="UART_RESP",
    )
    return drivers[0], drivers[1], initiator, responder


async def _faults(wdt: "machine.WDT") -> None:
    uart0, uart1, initiator, responder = _build(PAYLOAD_SIZE)
    try:
        fact("setup", {"initiator": await initiator.setup(), "responder": await responder.setup()})
        injector = PeripheralInjector(uart1, BENCH["bus"][BENCH["instances"]["uart_link_resp"]["bus"]])
        injector.silence()
        fact("silence_failed", await _transfer(wdt, responder, initiator.uart_set(_CMD_ECHO, b"lost")) is False)
        fact("silence_recovery_ms", await _recovery_ms(wdt, initiator, responder, injector))
        await initiator.reset_error_counter()
        injector.desync()
        fact("desync_failed", await _transfer(wdt, responder, initiator.uart_set(_CMD_ECHO, b"skew")) is False)
        fact("desync_log", log_record(await initiator.get_error_counter(), initiator.name))
        fact("desync_recovery_ms", await _recovery_ms(wdt, initiator, responder, injector))
    finally:
        uart0.deinit()
        uart1.deinit()


async def _mismatch(wdt: "machine.WDT") -> None:
    # A payload_size is agreed out of band and never negotiated, so a mismatch is only diagnosed: it must fail, loudly,
    # rather than deliver a wrong-length payload as if it were right.
    uart0, uart1, initiator, responder = _build(PAYLOAD_SIZE + 8)
    try:
        fact("mismatch_setup", {"initiator": await initiator.setup(), "responder": await responder.setup()})
        fact("mismatch_failed", await _transfer(wdt, responder, initiator.uart_set(_CMD_ECHO, b"mismatched")) is False)
        fact("mismatch_log", log_record(await initiator.get_error_counter(), initiator.name))
    finally:
        uart0.deinit()
        uart1.deinit()


async def _recovery_ms(wdt: "machine.WDT", initiator: UARTComm, responder: UARTComm, injector: PeripheralInjector) -> "int | None":
    # From restore() to the first transfer that succeeds, retried until the resync bound and one timeout have passed.
    start = time.ticks_ms()
    injector.restore()
    await responder.clear()
    while time.ticks_diff(time.ticks_ms(), start) < BENCH["resync_bound_ms"] + TIMEOUT_MS:
        if await _transfer(wdt, responder, initiator.uart_set(_CMD_ECHO, b"back")):
            return time.ticks_diff(time.ticks_ms(), start)
        await asyncio.sleep_ms(_RECOVERY_RETRY_MS)
    return None


async def _transfer(wdt: "machine.WDT", responder: UARTComm, work: "Coroutine[object, object, bool]") -> bool:
    # One transfer against a listener started for it; the listener is joined with clear() as the documented unstick
    # for a read whose frame never came (SPECIFICATION.md Part J.5), then cancelled if even that fails.
    listener = asyncio.create_task(responder.uart_listen())
    task = asyncio.create_task(work)
    while not task.done():
        await settled(wdt, task)
    if not await settled(wdt, listener):
        await responder.clear()
        if not await settled(wdt, listener):
            listener.cancel()
            await settled(wdt, listener)
    return await task


def get_callback(cmd_id: int) -> "tuple[bool, bytes | None]":
    return True, b"v"


def set_callback(cmd_id: int) -> "tuple[bool, int | None]":
    return (cmd_id == _CMD_ECHO), None


async def _main() -> None:
    wdt = arm()
    raised: list[str] = []  # an exception a task ended with under the faults: none is the system's half of the result
    asyncio.get_event_loop().set_exception_handler(lambda _loop, context: raised.append(repr(context.get("exception"))))
    fact("crc_mode", BENCH.get("CRC_MODE", "none"))
    fact("resync_bound_ms", BENCH["resync_bound_ms"])
    await _faults(wdt)
    await _mismatch(wdt)
    fact("system_task_exceptions", raised)
    done()


asyncio.run(_main())
