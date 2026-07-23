"""Async wrapper around machine.UART: select.poll-driven non-blocking read/write (MicroPython's
asyncio has no built-in UART-readiness primitive), lock-scoped via base_classes.Lockable so a whole
read/write exchange runs atomically under `async with`. Optional per-instance CRC framing
(crc_checks.py's CRC_Base family) adds/verifies a trailing CRC on read_until_complete/
readinto_until_complete/write/writefrom.

Not currently wired into any live caller in this codebase - python/IndividualDrivers/asy_uart_comm.py
(its one existing consumer) is its own separate promotion, out of scope here. Whoever does wire this
in: see BACKLOG.md for a Pico W GPIO23/24/25/29 wiring hazard worth knowing about first.

Contract: every method but __init__()/init() returns its documented None/False sentinel, never
raises - init() may raise ValueError for a bad pin/buffer/port_id, matching the other src/ drivers.
write()/writefrom() retry until the whole buffer is sent, since real uart.write() can short-write.

See BACKLOG.md's `asy_uart_driver.py -> src/` entries for the full verification rationale.
"""

import asyncio
import select
import time

from machine import UART as _UART
from machine import Pin
from micropython import const

from base_classes import Lockable
from crc_checks import CRC_Base, CRC_Pass

_LF = const(0x0A)  # b"\n"[0] - readline_until_complete's own-line terminator


class UART(Lockable):
    def __init__(
        self,
        port_id: int,
        tx_pin: int,
        rx_pin: int,
        baudrate: int = 9600,
        bits: int = 8,
        parity: int | None = None,
        stop: int = 1,
        rxbuf: int = 256,
        txbuf: int = 256,
        timeout: int = 0,
        timeout_char: int = 1,
        invert: int = 0,
        poll_wait_ms: int = 20,
        crc: CRC_Base | None = None,
    ) -> None:
        self._uart: _UART | None = None
        self.poller: select.poll | None = None
        super().__init__()
        self.poll_wait_ms = poll_wait_ms
        self.cancel = False
        self.cancelled = asyncio.Event()
        self.crc = CRC_Pass() if crc is None else crc
        self.init(port_id, tx_pin, rx_pin, baudrate, bits, parity, stop, rxbuf, txbuf, timeout, timeout_char, invert)

    def init(
        self,
        port_id: int,
        tx_pin: int,
        rx_pin: int,
        baudrate: int = 9600,
        bits: int = 8,
        parity: int | None = None,
        stop: int = 1,
        rxbuf: int = 256,
        txbuf: int = 256,
        timeout: int = 0,
        timeout_char: int = 1,
        invert: int = 0,
    ) -> None:
        # deinit() first so re-init can't leak a claimed peripheral/pins or a stale poll
        # registration - matches asy_spi_driver.py's/asy_i2c_driver.py's own init() pattern.
        self.deinit()
        self._uart = _UART(
            port_id,
            baudrate=baudrate,
            tx=Pin(tx_pin),
            rx=Pin(rx_pin),
            bits=bits,
            parity=parity,
            stop=stop,
            rxbuf=rxbuf,
            txbuf=txbuf,
            timeout=timeout,
            timeout_char=timeout_char,
            invert=invert,
        )
        self.poller = select.poll()
        self.poller.register(self._uart, select.POLLIN | select.POLLOUT)

    def deinit(self) -> None:
        # machine.UART.deinit() actually turns off the hardware bus, not just drops the Python
        # reference - confirmed never to raise itself, unlike poller.unregister() below, whose
        # wrap is defensive against an upstream corner case - see BACKLOG.md for both.
        if self._uart is not None:
            if self.poller is not None:
                try:
                    self.poller.unregister(self._uart)
                except (OSError, MemoryError):
                    pass
            self._uart.deinit()
            self._uart = None
            self.poller = None

    def _active_uart(self) -> "_UART | None":
        # Shared entry guard for every read/write method - None unless called inside `async with
        # self:` on a live bus. Returns the narrowed UART (not bool) so mypy's None-narrowing works.
        # See BACKLOG.md for why the lock check is kept here, unlike SPIDevice/I2CDevice.
        if not self.asy_lock.locked():
            return None
        return self._uart

    async def cancel_read_timeout(self) -> bool:
        # Lets another task abort this instance's in-flight ready()/read wait from the outside -
        # e.g. asy_uart_comm.py's clear() uses this to interrupt a stuck listen before resyncing.
        if not self.asy_lock.locked():  # nothing to cancel if not in use
            return False
        self.cancel = True
        await self.cancelled.wait()
        return True

    async def ready(self, mask: int, timeout_ms: int = -1) -> bool:
        # Busy-polls ipoll(0), yielding via sleep_ms(poll_wait_ms), until mask is satisfied, a
        # cancel is requested, or timeout_ms elapses (<=0 waits forever). Defensive against a
        # concurrent deinit() nulling self.poller mid-loop - see BACKLOG.md.
        if self._uart is None or self.poller is None:
            return False
        self.cancel = False
        self.cancelled.clear()
        t0 = time.ticks_ms()
        while True:
            if self.poller is None:  # a concurrent deinit() can null this mid-loop
                return False  # type: ignore[unreachable]  # mypy can't see the mutation
            try:
                res = self.poller.ipoll(0)
                for _, event in res:
                    if event & mask:
                        return True
                if self.cancel or ((timeout_ms > 0) and (time.ticks_diff(time.ticks_ms(), t0) > timeout_ms)):
                    self.cancel = False
                    self.cancelled.set()
                    return False
                await asyncio.sleep_ms(self.poll_wait_ms)
            except (OSError, MemoryError, TypeError):
                # TypeError: a malformed mask/timeout_ms - not caught by callers' own except
                # clauses, since those only wrap the real UART call, not this await.
                return False

    async def read(self, nbytes: int | None = None, timeout_ms: int = -1) -> bytes | None:
        uart = self._active_uart()
        if uart is None:
            return None
        if not await self.ready(select.POLLIN, timeout_ms=timeout_ms):
            return None
        if nbytes is None:
            return uart.read()
        return uart.read(nbytes)

    async def read_until_complete(
        self, nbytes: int, start_timeout_ms: int = -1, timeout_ms: int = -1
    ) -> bytearray | None:
        # Reads exactly nbytes (+ CRC, if configured) across as many ready()/read() rounds as it
        # takes, then verifies/strips the trailing CRC in one go.
        uart = self._active_uart()
        if uart is None:
            return None
        timeout = start_timeout_ms  # wait time for the first message part
        msg = bytearray()
        nbytes += self.crc.length()
        while len(msg) < nbytes:
            if await self.ready(select.POLLIN, timeout_ms=timeout):
                add = uart.read(nbytes - len(msg))
                if add is None:
                    return None
                try:
                    msg += add
                except MemoryError:
                    return None
                timeout = timeout_ms  # once started, use the regular timeout for the remaining parts
            else:
                return None  # ready() timed out or was cancelled
        try:
            return await self.crc.check(msg)
        except MemoryError:  # check()'s own bytearr[0:n] slice allocates a fresh copy - see BACKLOG.md
            return None

    async def readinto(self, buf: bytearray, nbytes: int | None = None, timeout_ms: int = -1) -> int | None:
        uart = self._active_uart()
        if uart is None:
            return None
        if not await self.ready(select.POLLIN, timeout_ms=timeout_ms):
            return None
        if nbytes is None:
            return uart.readinto(buf)
        return uart.readinto(buf, nbytes)

    async def readinto_until_complete(
        self, buf: bytearray, nbytes: int, start_timeout_ms: int = -1, timeout_ms: int = -1
    ) -> int | None:
        # readinto() counterpart of read_until_complete(): fills buf in place instead of
        # allocating a new bytearray per call.
        uart = self._active_uart()
        if uart is None:
            return None
        timeout = start_timeout_ms  # wait time for the first message part
        size = 0
        nbytes += self.crc.length()
        if nbytes > len(buf):
            return None
        buf_mv = memoryview(buf)
        while size < nbytes:
            if await self.ready(select.POLLIN, timeout_ms=timeout):
                nb = uart.readinto(buf_mv[size:], nbytes - size)
                if nb is None:
                    return None
                size += nb
                timeout = timeout_ms  # once started, use the regular timeout for the remaining parts
            else:
                return None  # ready() timed out or was cancelled
        return await self.crc.check_from(buf, size=size)

    async def readline(self, timeout_ms: int = -1) -> bytes | None:
        uart = self._active_uart()
        if uart is None:
            return None
        if not await self.ready(select.POLLIN, timeout_ms=timeout_ms):
            return None
        return uart.readline()

    async def readline_until_complete(self, start_timeout_ms: int = -1, timeout_ms: int = -1) -> bytearray | None:
        # No CRC framing here (unlike the other *_until_complete methods) - readline() is for
        # text-style, newline-terminated messages, matching the original driver's own scope.
        uart = self._active_uart()
        if uart is None:
            return None
        timeout = start_timeout_ms  # wait time for the first message part
        msg = bytearray()
        while True:
            if await self.ready(select.POLLIN, timeout_ms=timeout):
                add = uart.readline()  # reads until b"\n" or the buffer runs empty
                if add is None:
                    return None
                try:
                    msg += add
                except MemoryError:  # unbounded across rounds, unlike read_until_complete()'s nbytes cap - see BACKLOG.md
                    return None
                # `msg and` guards msg[-1]: readline() ready via poll can still return b"" (e.g. a
                # zero-length read), which would otherwise index an empty bytearray and raise.
                if msg and msg[-1] == _LF:  # trailing \n means the line is actually complete
                    break
                timeout = timeout_ms  # once started, use the regular timeout for the remaining parts
            else:
                return None  # ready() timed out or was cancelled
        return msg

    async def _write_all(self, uart: "_UART", buf: bytearray | memoryview) -> bool:
        # rp2 uart.write() can short-write instead of raising (see BACKLOG.md) - retries with
        # whatever's left until the whole buffer is out or a real failure gives up, the write-side
        # counterpart of read_until_complete()'s own retry-until-done loop.
        sent = 0
        total = len(buf)
        view = memoryview(buf)
        while sent < total:
            if not await self.ready(select.POLLOUT):
                return False
            n = uart.write(view[sent:])
            if n is None:
                return False
            sent += n
        return True

    async def write(self, msg: bytearray) -> bool:  # write msg (+ CRC, if configured), retrying until it's all sent
        uart = self._active_uart()
        if uart is None:
            return False
        try:
            framed = await self.crc.add(msg)  # add()'s own bytearr + crc_b allocates a fresh copy - see BACKLOG.md
        except MemoryError:
            return False
        if framed is None:
            return False
        return await self._write_all(uart, framed)

    async def writefrom(self, buf: bytearray, size: int) -> bool:  # write buf's first size bytes (+ CRC), retrying until it's all sent
        uart = self._active_uart()
        if uart is None:
            return False
        crcsize = await self.crc.add_into(buf, size)
        if crcsize is None:
            return False
        return await self._write_all(uart, memoryview(buf)[0:crcsize])
