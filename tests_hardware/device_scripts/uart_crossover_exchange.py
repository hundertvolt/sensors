"""Isolated-driver device script: a real GET, a real SET, a three-chunk train, a train of the TOML's max_transfer_bytes
each way and an over-cap train refused, across the bench board's UART crossover jumper - J.7's self-compatibility
on silicon, in the CRC mode the host passes. Facts out; the host test judges."""
# Constructs the two instances directly, never through the generated device module's task graph: no flash write
# (C.8), and both loggers stay RAM-only.

import asyncio
import gc
import time

import asy_uart_driver
from asy_crc_checks import CRC16
from asy_uart_comm import DEFAULT_LIMITS, ROLE_INITIATOR, ROLE_RESPONDER, ResponderCallbacks, TransferLimits, UARTComm

# @include _shared/facts.py
# @include _shared/watchdog.py

# @include _shared/settle.py
# @include _shared/heap_probe.py
# @include _shared/isl_error_log.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import TypeVar

    import machine
    from _shared.facts import done, fact
    from _shared.heap_probe import largest_block
    from _shared.isl_error_log import log_record
    from _shared.settle import settled
    from _shared.watchdog import arm
    from bench_facts import BenchFacts, BusFacts

    from asy_base_classes import PieceBuffer

    T = TypeVar("T")

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Explicit, never inherited: the largest-block reads around the over-cap refusal run at MicroPython's own reactive
# default, the (e) stage, whatever threshold an earlier run left.
gc.threshold(-1)

PAYLOAD_SIZE = 48  # the protocol's default frame, agreed out of band (J.6)
TIMEOUT_MS = 1000
_CMD_BANNER = 0x01
_CMD_ECHO = 0x02
_CMD_MAX = 0x03
_BANNER = b"crossover-ok"
# Three data chunks: a real multi-frame train's chunk indexing and UID progression, without a minute of wire time.
_TRAIN_BYTES = PAYLOAD_SIZE * 2 + 7


def _driver(bus: "BusFacts", crc: "CRC16 | None") -> "asy_uart_driver.UART":
    return asy_uart_driver.UART(
        bus["id"], bus["tx_pin"], bus["rx_pin"], baudrate=bus["baudrate"], rxbuf=bus["rxbuf"], txbuf=bus["txbuf"], rx_ring=bus["rx_ring"],
        poll_wait_ms=bus["poll_wait_ms"], poll_idle_ms=bus["poll_idle_ms"], crc=crc,
    )


async def _fed(wdt: "machine.WDT", work: "Coroutine[object, object, T]") -> "T":
    # The maximum train runs for seconds: awaited as a task, the watchdog fed while it does.
    task = asyncio.create_task(work)
    while not task.done():
        await settled(wdt, task)
    return await task


class _Responder:
    # The responder's callbacks: the banner, an echo SET with no destination, and the maximum train each way.
    def __init__(self, max_bytes: int, seed: int) -> None:
        self.max_bytes, self.seed = max_bytes, seed
        self.answer = bytearray(_pattern(seed, i) for i in range(max_bytes))  # the GET answer must be one buffer
        self.max_set_intact = False

    def get(self, cmd_id: int) -> "tuple[bool, bytes | bytearray | None]":
        if cmd_id == _CMD_BANNER:
            return True, _BANNER
        if cmd_id == _CMD_MAX:
            return True, self.answer
        return False, None

    def message(self, cmd_id: int, cmd: int, payload: "PieceBuffer | None") -> None:
        if cmd_id == _CMD_MAX:
            self.max_set_intact = _intact(payload, self.max_bytes, self.seed)

    def set(self, cmd_id: int) -> "tuple[bool, int | None]":
        return cmd_id in (_CMD_ECHO, _CMD_MAX), None


def _intact(answer: "PieceBuffer | None", size: int, seed: int) -> bool:
    # Piece by piece against the regenerated pattern: no copy the size of the train.
    if answer is None or len(answer) != size:
        return False
    offset = 0
    for piece in answer.pieces():
        for j in range(len(piece)):
            if piece[j] != _pattern(seed, offset + j):
                return False
        offset += len(piece)
    return offset == size


async def _over_cap(wdt: "machine.WDT", initiator: UARTComm, uart1: "asy_uart_driver.UART") -> None:
    # The TOML's cap is the protocol's own maximum, which no CHUNKS byte can exceed, so the refusal is shown against a
    # responder capped one chunk short of a three-chunk train: refused before its ACK, logged once, nothing allocated.
    limits = TransferLimits(PAYLOAD_SIZE, TIMEOUT_MS, DEFAULT_LIMITS.chunk_bytes, PAYLOAD_SIZE * 2)
    capped = UARTComm(uart1, ROLE_RESPONDER, limits=limits, callbacks=ResponderCallbacks(lambda _c: (False, None), lambda _c: (True, None), None), name="UART_CAP")
    fact("capped_setup", await capped.setup())
    payload = bytes(_TRAIN_BYTES)
    listener = asyncio.create_task(capped.uart_listen())
    await asyncio.sleep_ms(0)  # parked on its read before the heap is read
    before = largest_block()
    refused = await _fed(wdt, initiator.uart_set(_CMD_ECHO, payload))
    after = largest_block()
    if not await settled(wdt, listener):
        await capped.clear()
        await settled(wdt, listener)
    fact("largest_block_before", before)
    fact("largest_block_after", after)
    fact("over_cap_refused", refused is False)
    fact("over_cap_log", log_record(await capped.get_error_counter(), capped.name))


def _pattern(seed: int, i: int) -> int:
    return (seed + i * 7) & 0xFF


async def _main() -> None:
    wdt = arm()
    mode = BENCH.get("CRC_MODE", "none")
    fact("crc_mode", mode)
    fact("gc_threshold", gc.threshold())
    bus0 = BENCH["bus"][BENCH["instances"]["uart_link_init"]["bus"]]
    bus1 = BENCH["bus"][BENCH["instances"]["uart_link_resp"]["bus"]]
    max_bytes = bus1["max_transfer_bytes"]
    limits = TransferLimits(PAYLOAD_SIZE, TIMEOUT_MS, DEFAULT_LIMITS.chunk_bytes, max_bytes)
    callbacks = _Responder(max_bytes, time.ticks_diff(time.ticks_ms(), 0) & 0xFF)
    uart0 = _driver(bus0, CRC16() if mode == "crc16" else None)
    uart1 = _driver(bus1, CRC16() if mode == "crc16" else None)
    initiator = UARTComm(uart0, ROLE_INITIATOR, limits=limits, name="UART_INIT")
    responder = UARTComm(uart1, ROLE_RESPONDER, limits=limits, callbacks=ResponderCallbacks(callbacks.get, callbacks.set, callbacks.message), name="UART_RESP")
    setups = {"initiator": await initiator.setup(), "responder": await responder.setup()}
    fact("setup", setups)
    if all(setups.values()):
        listener = responder.start_asy_listen()  # the shipped listen loop answers every exchange below
        scratch = bytearray(len(_BANNER))
        answer = await _fed(wdt, initiator.uart_get(_CMD_BANNER))
        fact("get_answer_ok", answer is not None and len(answer) == len(_BANNER) and answer.copy_into(scratch) and scratch == _BANNER)
        fact("set_ok", await _fed(wdt, initiator.uart_set(_CMD_ECHO, bytes((i * 11) & 0xFF for i in range(_TRAIN_BYTES)))))
        fact("train_bytes", _TRAIN_BYTES)
        fact("empty_set_ok", await _fed(wdt, initiator.uart_set(_CMD_ECHO, None)))
        fact("max_train_bytes", max_bytes)
        fact("max_set_ok", await _fed(wdt, initiator.uart_set(_CMD_MAX, callbacks.answer)))
        fact("max_set_intact", callbacks.max_set_intact)
        fact("max_get_intact", _intact(await _fed(wdt, initiator.uart_get(_CMD_MAX)), max_bytes, callbacks.seed))
        counts = {}
        for comm in (initiator, responder):  # no await inside a comprehension on MicroPython
            counts[comm.name] = log_record(await comm.get_error_counter(), comm.name)
        fact("error_counts", counts)
        listener.cancel()
        await settled(wdt, listener)
        await _over_cap(wdt, initiator, uart1)
    uart0.deinit()
    uart1.deinit()
    done()


asyncio.run(_main())
