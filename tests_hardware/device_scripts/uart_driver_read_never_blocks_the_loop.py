"""Isolated-driver device script: the shipped asy_uart_driver read path must never hold the asyncio
loop for a frame still arriving (SPECIFICATION.md Part F.5.8). Asserts on the driver's own synchronous
UART calls - F.5.8's honest measure - against an unclamped read of the same frame as the control."""

import asyncio
import gc
import select
import time

import machine
from machine import UART, Pin

import asy_uart_driver

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    _Reader = Callable[[asy_uart_driver.UART, bytearray], Awaitable[int | None]]

BAUDRATE = 115200
FRAME = 53  # one whole framed frame at the bench's payload_size=48, as uart_read_never_blocks_the_loop.py
TRIALS = 5
POLL_WAIT_MS = 2  # mirrors sensortask_dev.py's own transaction rate
_WIRE_US = FRAME * 10 * 1000000 // BAUDRATE
_SPAN_MAX_US = _WIRE_US // 3  # one synchronous call: the raw-UART script's own bound
_raw: "list[UART]" = []  # the driver's real UART, kept for draining and the unclamped control
_control_span = [0]


class _TimedUart:
    # Stands in for the driver's machine.UART, so the calls its own clamp makes are the ones timed.
    def __init__(self, inner: "UART") -> None:
        self._inner = inner
        self.worst_us = 0

    def _timed(self, fn: "Callable[..., object]", *args: object) -> object:
        t0 = time.ticks_us()
        result = fn(*args)
        self.worst_us = max(self.worst_us, time.ticks_diff(time.ticks_us(), t0))
        return result

    def any(self) -> object:
        return self._timed(self._inner.any)

    def readinto(self, *args: object) -> object:
        return self._timed(self._inner.readinto, *args)

    def read(self, *args: object) -> object:
        return self._timed(self._inner.read, *args)

    def deinit(self) -> None:
        self._inner.deinit()


class Ticker:
    # The loop's own view, printed only: a gap is one reader stretch plus two scheduler passes, and
    # scheduler noise (the IDLE line) makes it too unsteady to assert on - F.5.8 says the same.
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


async def _driver_read(drv: "asy_uart_driver.UART", buf: bytearray) -> int | None:
    async with drv:  # every read method refuses outside the lock (_active_uart())
        return await drv.readinto_until_complete(buf, FRAME, start_timeout_ms=500, timeout_ms=200)


async def _unclamped_read(drv: "asy_uart_driver.UART", buf: bytearray) -> int | None:
    # The pre-fix shape on the same peripheral, read the moment the first byte lands (as the raw
    # script does): a yield first would let part of the frame arrive and shrink the control's stall.
    async with drv:
        poller = select.poll()
        poller.register(_raw[0], select.POLLIN)
        deadline = time.ticks_add(time.ticks_ms(), 500)
        while not any(ev & select.POLLIN for _, ev in poller.ipoll(0)):
            if time.ticks_diff(deadline, time.ticks_ms()) < 0:
                return None
        t0 = time.ticks_us()
        got = _raw[0].readinto(buf, FRAME)
        _control_span[0] = max(_control_span[0], time.ticks_diff(time.ticks_us(), t0))
        return got


async def _trial(wdt: "machine.WDT", writer: "UART", drv: "asy_uart_driver.UART", reader: "_Reader", frame: bytes) -> "tuple[int, int, bool]":
    wdt.feed()
    while _raw[0].any():
        _raw[0].read()
    gc.collect()  # no collection may land inside the measured window
    buf = bytearray(FRAME)
    ticker = Ticker()
    tick_task = asyncio.create_task(ticker.run())
    await asyncio.sleep_ms(5)  # the ticker is running before the first byte leaves
    writer.write(frame)  # the copy into txbuf costs ~1.3 ms itself, so it stays outside the window
    await asyncio.sleep_ms(0)
    ticker.worst_us = 0
    got = await reader(drv, buf)
    ticker.running = False
    await tick_task
    return ticker.worst_us, ticker.turns, got == FRAME and bytes(buf) == frame


async def _idle_gap() -> int:
    ticker = Ticker()
    tick_task = asyncio.create_task(ticker.run())
    await asyncio.sleep_ms(20)
    ticker.running = False
    await tick_task
    return ticker.worst_us


async def main() -> None:
    wdt = machine.WDT(timeout=8000)
    writer = UART(0, baudrate=BAUDRATE, tx=Pin(0), rx=Pin(1), rxbuf=512, txbuf=512, timeout=0, timeout_char=1)
    drv = asy_uart_driver.UART(1, 8, 9, baudrate=BAUDRATE, rxbuf=512, txbuf=512, poll_wait_ms=POLL_WAIT_MS)
    frame = bytes(range(FRAME))
    if drv._uart is None:
        print("RESULT: FAIL the driver has no UART")
        return
    _raw.append(drv._uart)
    timed = _TimedUart(drv._uart)
    drv._uart = timed  # type: ignore[assignment]
    gc.collect()
    print(f"IDLE ticker worst gap {await _idle_gap()}us with nothing on the wire")
    driver_worst = 0
    control_worst = 0
    span_worst = 0
    failures = []
    for i in range(TRIALS):
        timed.worst_us = 0
        worst, turns, ok = await _trial(wdt, writer, drv, _driver_read, frame)
        driver_worst = max(driver_worst, worst)
        span_worst = max(span_worst, timed.worst_us)
        if not ok:
            failures.append(f"trial {i}: the driver did not deliver the frame intact")
        worst, _, _ = await _trial(wdt, writer, drv, _unclamped_read, frame)
        control_worst = max(control_worst, worst)
        print(f"TRIAL {i} driver_worst_span={span_worst}us driver_worst_gap={driver_worst}us driver_turns={turns} control_worst_gap={control_worst}us")
    drv.deinit()
    writer.deinit()

    if _control_span[0] < _SPAN_MAX_US:
        failures.append(f"the unclamped control read took only {_control_span[0]}us - the measurement is not exercising the stall")
    if span_worst > _SPAN_MAX_US:
        failures.append(f"one of the driver's own UART calls took {span_worst}us, over the {_SPAN_MAX_US}us bound")
    if failures:
        print("RESULT: FAIL " + "; ".join(failures))
    else:
        print(
            f"RESULT: PASS shipped driver's longest UART call {span_worst}us vs unclamped {_control_span[0]}us (bound {_SPAN_MAX_US}us, "
            f"wire time {_WIRE_US}us); loop gaps, not asserted: driver {driver_worst}us, unclamped {control_worst}us",
        )


asyncio.run(main())
