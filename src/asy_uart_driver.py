"""Async wrapper around machine.UART: select.poll-driven non-blocking read/write (MicroPython's
asyncio has no built-in UART-readiness primitive - the same problem asy_udp_socket.py solves for
sockets), lock-scoped via base_classes.Lockable so a whole read/write exchange runs atomically
under `async with`. Optional per-instance CRC framing (crc_checks.py's CRC_Base family) adds/
verifies a trailing CRC on read_until_complete/readinto_until_complete/write/writefrom.

Not currently wired into any live caller in this codebase - python/IndividualDrivers/asy_uart_comm.py
(its one existing consumer) is its own separate promotion, out of scope here.

Contract: every method other than __init__/init() returns its documented None/False sentinel -
never raises - for a non-hardware failure (bus not initialized/deinitialized, called outside
`async with`, a poll/read timeout, a failed CRC check). Confirmed via ports/rp2/machine_uart.c and
py/stream.c (checked from v1.18 through the current 1.28.0 pin) that a real UART fault (timeout,
framing/parity/overrun error) surfaces as MP_EAGAIN -> None from the underlying stream read/write,
never as a raised exception - unlike asy_i2c_driver.py, where a real NAK/timeout is allowed to
propagate as OSError. __init__()/init() are the exception, allowed to raise ValueError for a bad
pin/baudrate/bits/parity/stop/buffer-size combination, matching asy_spi_driver.py's/
asy_i2c_driver.py's own __init__ pattern. UART.flush() (not used by this file) is a different case -
MicroPython raises OSError(ETIMEDOUT) from it on a real timeout, unlike the methods wrapped here.
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
        # machine.UART.deinit() actually turns off the hardware bus - not just dropping the
        # Python reference, which would leave the peripheral/pins claimed.
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
        # Shared entry guard for every read/write method below: returns the live machine.UART
        # only if called inside `async with self:` (asy_lock held) on a not-deinitialized bus,
        # None otherwise - the same sentinel every caller already returns for "can't operate".
        # Returning the narrowed value (not just a bool) keeps mypy's None-narrowing working
        # through a local variable, the same way asy_i2c_driver.py's/asy_spi_driver.py's own
        # inline `if self._i2c is None: return None` checks do.
        # Unlike SPIDevice/I2CDevice, which trust the caller here, the lock check is load-bearing
        # for UART specifically: cancel_read_timeout() infers "is a read genuinely in flight" from
        # asy_lock.locked() alone, called from a *different* task than the one doing the read - a
        # lock-less caller would be invisible to it, silently breaking cancellation.
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
        # Busy-polls ipoll(0), yielding via sleep_ms(poll_wait_ms) each cycle, until mask is
        # satisfied, cancel_read_timeout() requests a cancel, or timeout_ms elapses (<=0 waits
        # forever).
        if self._uart is None or self.poller is None:
            return False
        self.cancel = False
        self.cancelled.clear()
        t0 = time.ticks_ms()
        while True:
            res = self.poller.ipoll(0)
            for _, event in res:
                if event & mask:
                    return True
            if self.cancel or ((timeout_ms > 0) and (time.ticks_diff(time.ticks_ms(), t0) > timeout_ms)):
                self.cancel = False
                self.cancelled.set()
                return False
            await asyncio.sleep_ms(self.poll_wait_ms)

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
                msg += add
                timeout = timeout_ms  # once started, use the regular timeout for the remaining parts
            else:
                return None  # ready() timed out or was cancelled
        return await self.crc.check(msg)

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
                msg += add
                # `msg and` guards msg[-1]: readline() ready via poll can still return b"" (e.g. a
                # zero-length read), which would otherwise index an empty bytearray and raise.
                if msg and msg[-1] == _LF:  # trailing \n means the line is actually complete
                    break
                timeout = timeout_ms  # once started, use the regular timeout for the remaining parts
            else:
                return None  # ready() timed out or was cancelled
        return msg

    async def write(self, msg: bytearray) -> bool:  # write msg (+ CRC, if configured) once ready
        uart = self._active_uart()
        if uart is None:
            return False
        framed = await self.crc.add(msg)
        if framed is None:
            return False
        if not await self.ready(select.POLLOUT):
            return False
        uart.write(framed)  # rp2 stream write: can short-write, never raises (see module docstring)
        return True

    async def writefrom(self, buf: bytearray, size: int) -> bool:  # write buf's first size bytes (+ CRC) in place
        uart = self._active_uart()
        if uart is None:
            return False
        crcsize = await self.crc.add_into(buf, size)
        if crcsize is None:
            return False
        if not await self.ready(select.POLLOUT):
            return False
        uart.write(memoryview(buf)[0:crcsize])
        return True
