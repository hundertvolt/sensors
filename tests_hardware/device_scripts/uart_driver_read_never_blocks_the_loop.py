"""Isolated-driver device script: the shipped asy_uart_driver read path must never hold the asyncio loop for a frame
still arriving (SPECIFICATION.md Part F.5.8). Times the driver's own synchronous ring copies against an unclamped
machine.UART read of the same frame (the control), and reports the facts; the host test judges."""

import asyncio
import gc
import select
import time

from machine import UART, Pin

import asy_uart_driver
from asy_print_log import DEFAULT_LOG, make_logger

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    import machine
    from _mpy_shed.time_mp import _TicksMs
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts, BusFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

FRAME = 53  # one whole framed frame at the protocol's default payload_size of 48 (J.6)
# @tunable l3.uart_driver_read_never_blocks_the_loop_trials = 5
_TRIALS = 5
# @tunable l3.uart_read_never_blocks_the_loop_span_fraction = 3
_SPAN_FRACTION = 3  # one synchronous call may take a third of the frame's wire time
# @tunable l3.uart_driver_read_never_blocks_the_loop_start_timeout_ms = 500
_START_TIMEOUT_MS = 500
# @tunable l3.uart_driver_read_never_blocks_the_loop_read_timeout_ms = 200
_READ_TIMEOUT_MS = 200
# @tunable l3.uart_driver_read_never_blocks_the_loop_raw_deadline_ms = 500
_RAW_DEADLINE_MS = 500
# @tunable l3.uart_driver_read_never_blocks_the_loop_idle_window_ms = 20
_IDLE_WINDOW_MS = 20
# The ticker is running before the first byte leaves: a deadline on its first recorded turn, not a fixed sleep.
# @tunable l3.uart_driver_read_never_blocks_the_loop_ticker_start_ms = 50
_TICKER_START_MS = 50
_CHAR_TIMEOUT_MS = 1  # machine.UART's timeout_char as the driver constructs it: a raw read waits per missing byte
_LINE_CHUNK_BYTES = 16  # the readline leg's piece size: several pieces per line
_LF = 0x0A
# A quiet line for this long ends a drain: whatever an earlier arm left on the wire has arrived and gone.
# @tunable l3.uart_driver_read_never_blocks_the_loop_drain_quiet_ms = 20
_DRAIN_QUIET_MS = 20


class _CopyTimer:
    # Stands in for the driver's ring copy, the one synchronous stretch a read makes, and keeps the longest call.
    def __init__(self, inner: "Callable[[bytearray | memoryview | None, int, int], int]") -> None:
        self._inner = inner
        self.worst_us = 0

    def __call__(self, dest: "bytearray | memoryview | None", start: int, n: int) -> int:
        t0 = time.ticks_us()
        got = self._inner(dest, start, n)
        self.worst_us = max(self.worst_us, time.ticks_diff(time.ticks_us(), t0))
        return got


class Ticker:
    # The loop's own view: a gap is one reader stretch plus two scheduler passes, reported, not asserted (F.5.8).
    def __init__(self) -> None:
        self.worst_us = 0
        self.turns = 0
        self.running = True

    async def run(self) -> None:
        last = time.ticks_us()
        while self.running:
            await asyncio.sleep_ms(0)
            now = time.ticks_us()
            self.worst_us = max(self.worst_us, time.ticks_diff(now, last))
            self.turns += 1
            last = now

    async def started(self) -> bool:
        deadline = time.ticks_add(time.ticks_ms(), _TICKER_START_MS)
        while not self.turns and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            await asyncio.sleep_ms(0)
        self.worst_us = 0
        return self.turns > 0


async def _control(wdt: "machine.WDT", writer: UART, bus: "BusFacts", frame: bytes) -> None:
    # The pre-fix shape on the receiving UART before the driver takes it over: read the moment the first byte lands,
    # for the whole frame, so the call waits out the rest of its wire time.
    wdt.feed()
    raw = _uart(bus)
    poller = select.poll()
    poller.register(raw, select.POLLIN)
    buf = bytearray(FRAME)
    ticker = Ticker()
    task = asyncio.create_task(ticker.run())
    await ticker.started()
    writer.write(frame)
    span = None
    if _first_byte(poller, time.ticks_add(time.ticks_ms(), _RAW_DEADLINE_MS)):
        t0 = time.ticks_us()
        raw.readinto(buf, FRAME)
        span = time.ticks_diff(time.ticks_us(), t0)
    ticker.running = False
    await task
    poller.unregister(raw)
    fact("control_span_us", span)
    fact("control_gap_us", ticker.worst_us)


async def _drain(drv: "asy_uart_driver.UART") -> None:
    # Everything still arriving from an earlier arm is read off before the next frame is sent.
    async with drv:
        while await drv.read(None, timeout_ms=_DRAIN_QUIET_MS) is not None:
            await asyncio.sleep_ms(0)


def _first_byte(poller: "select.poll", deadline: "_TicksMs") -> bool:
    # A busy wait on purpose, never a yield: a yield would let more of the frame arrive and shrink the control's stall.
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if any(ev & select.POLLIN for _, ev in poller.ipoll(0)):
            return True
    return False


async def _idle_gap() -> int:
    ticker = Ticker()
    task = asyncio.create_task(ticker.run())
    await asyncio.sleep_ms(_IDLE_WINDOW_MS)
    ticker.running = False
    await task
    return ticker.worst_us


async def _readline_leg(wdt: "machine.WDT", writer: UART, drv: "asy_uart_driver.UART", timer: _CopyTimer) -> None:
    # One newline-terminated frame through readline_until_complete(), its pieces copied by the same timed ring copy.
    wdt.feed()
    await _drain(drv)
    line = bytes(0x20 + (i % 0x5E) for i in range(FRAME - 1)) + bytes([_LF])
    timer.worst_us = 0
    writer.write(line)
    async with drv:
        got = await drv.readline_until_complete(FRAME, _LINE_CHUNK_BYTES, make_logger(DEFAULT_LOG, "UART_LINE"), start_timeout_ms=_START_TIMEOUT_MS, timeout_ms=_READ_TIMEOUT_MS)
    intact = got is not None and len(got) == FRAME
    offset = 0
    for piece in got.pieces() if got is not None else ():
        intact = intact and bytes(piece) == line[offset : offset + len(piece)]
        offset += len(piece)
    fact("readline_span_us", timer.worst_us)
    fact("readline_intact", intact)


async def _trial(wdt: "machine.WDT", writer: UART, drv: "asy_uart_driver.UART", frame: bytes) -> "tuple[int, int, int, bool]":
    # One frame through the driver: the ring's fill level at its first readiness, the read itself, the loop's gap.
    wdt.feed()
    await _drain(drv)
    gc.collect()  # before the window: no collection lands inside it
    buf = bytearray(FRAME)
    ticker = Ticker()
    task = asyncio.create_task(ticker.run())
    await ticker.started()
    t0 = time.ticks_us()
    writer.write(frame)
    txcopy = time.ticks_diff(time.ticks_us(), t0)
    async with drv:
        level = drv._rx_level() if await drv.ready(select.POLLIN, timeout_ms=_START_TIMEOUT_MS) else -1
        got = await drv.readinto_until_complete(buf, FRAME, start_timeout_ms=_START_TIMEOUT_MS, timeout_ms=_READ_TIMEOUT_MS)
    ticker.running = False
    await task
    return level, txcopy, ticker.worst_us, got == FRAME and bytes(buf) == frame


def _uart(bus: "BusFacts") -> UART:
    return UART(bus["id"], baudrate=bus["baudrate"], tx=Pin(bus["tx_pin"]), rx=Pin(bus["rx_pin"]), rxbuf=bus["rxbuf"], txbuf=bus["txbuf"], timeout=0, timeout_char=_CHAR_TIMEOUT_MS)


async def main() -> None:
    wdt = arm()
    sender = BENCH["bus"][BENCH["instances"]["uart_link_init"]["bus"]]
    receiver = BENCH["bus"][BENCH["instances"]["uart_link_resp"]["bus"]]
    wire_us = FRAME * 10 * 1000000 // receiver["baudrate"]
    fact("frame", FRAME)
    fact("wire_us", wire_us)
    fact("span_max_us", wire_us // _SPAN_FRACTION)
    writer = _uart(sender)
    frame = bytes(range(FRAME))
    gc.collect()
    fact("idle_gap_us", await _idle_gap())
    await _control(wdt, writer, receiver, frame)
    drv = asy_uart_driver.UART(
        receiver["id"], receiver["tx_pin"], receiver["rx_pin"], baudrate=receiver["baudrate"], rxbuf=receiver["rxbuf"], txbuf=receiver["txbuf"],
        rx_ring=receiver["rx_ring"], poll_wait_ms=receiver["poll_wait_ms"], poll_idle_ms=receiver["poll_idle_ms"],
    )
    fact("ring_setup", drv.setup_rx_ring())
    timer = _CopyTimer(drv._rx_copy)
    drv._rx_copy = timer  # type: ignore[method-assign]  # a timing wrapper stands in for the ring copy (test double)
    levels, copies, gaps, intact = [], [], [], []
    for _ in range(_TRIALS):
        level, txcopy, gap, ok = await _trial(wdt, writer, drv, frame)
        levels.append(level)
        copies.append(txcopy)
        gaps.append(gap)
        intact.append(ok)
    fact("driver_span_us", timer.worst_us)
    fact("first_ready_bytes", max(levels))
    fact("txcopy_us", max(copies))
    fact("driver_gap_us", max(gaps))
    fact("intact", intact)
    await _readline_leg(wdt, writer, drv, timer)
    drv.deinit()
    writer.deinit()
    done()


asyncio.run(main())
