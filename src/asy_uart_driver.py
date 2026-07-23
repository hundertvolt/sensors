"""Async wrapper around machine.UART: select.poll-driven non-blocking read/write (MicroPython's
asyncio has no built-in UART-readiness primitive - the same problem asy_udp_socket.py solves for
sockets), lock-scoped via base_classes.Lockable so a whole read/write exchange runs atomically
under `async with`. Optional per-instance CRC framing (crc_checks.py's CRC_Base family) adds/
verifies a trailing CRC on read_until_complete/readinto_until_complete/write/writefrom.

Not currently wired into any live caller in this codebase - python/IndividualDrivers/asy_uart_comm.py
(its one existing consumer) is its own separate promotion, out of scope here.

Contract: every method other than __init__/init() returns its documented None/False sentinel -
never raises - for a non-hardware failure (bus not initialized/deinitialized, called outside
`async with`, a poll/read timeout, a failed CRC check, or a MemoryError while assembling/framing a
message - see below). Confirmed via ports/rp2/machine_uart.c and py/stream.c (checked from v1.18
through the current 1.28.0 pin) that a real UART fault (timeout, framing/parity/overrun error)
surfaces as MP_EAGAIN -> None from the underlying stream read/write, never as a raised exception -
unlike asy_i2c_driver.py, where a real NAK/timeout is allowed to propagate as OSError. Also
confirmed there that UART.deinit() itself never raises (safe to call more than once), so it needs
no defensive wrapping here beyond the None-guard already required to call it at all.

__init__()/init() are the exception, allowed to raise ValueError for a bad pin/baudrate/bits/
parity/stop/buffer-size/port_id combination (mp_machine_uart_init_helper()/
mp_machine_uart_make_new()), matching asy_spi_driver.py's/asy_i2c_driver.py's own __init__
pattern - a misconfigured bus should fail loudly once at boot, not silently produce a
permanently-nonfunctional driver. init()'s select.poll().register() call is covered by this same
one-time-setup allowance: it raises unless the registered object's C-level type carries
MicroPython's stream protocol slot (confirmed against extmod/modselect.c) - unreachable with a
real machine.UART instance, but the allowance is documented for completeness rather than silently
assumed. See BACKLOG.md for why callers of this driver must be prepared to catch these at
construction time. UART.flush() (not used by this file) is a different operational-call case -
MicroPython raises OSError(ETIMEDOUT) from it on a real timeout, unlike the methods wrapped here.

MemoryError guarding: read_until_complete()/readline_until_complete()'s own bytearray accumulation
(`msg += add`), and crc_checks.py's CRC_Base.add()/check() (which allocate a fresh buffer
proportional to the message they're framing/verifying - see crc_checks.py's own docstring, which
documents a "never raises for invalid input" contract that doesn't extend to a MemoryError from
this internal allocation), are wrapped in try/except MemoryError at their call sites in this file
and folded into the same None/False sentinel every other operational failure already uses -
readline_until_complete() in particular has no caller-supplied size cap the way
read_until_complete()/readinto_until_complete() do, so an unterminated line from a real external
peer could otherwise grow msg without bound. Matches asy_udp_socket.py's own precedent of wrapping
its raw I/O calls in MemoryError alongside OSError. readinto_until_complete()/writefrom() need no
equivalent guard: their CRC counterparts (check_from()/add_into()) work in place via memoryview
into a caller-owned buffer, with no incremental allocation of their own.
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
        # Python reference, which would leave the peripheral/pins claimed. Confirmed against
        # ports/rp2/machine_uart.c that deinit() itself never raises and is safe to call more than
        # once, so it needs no try/except of its own here (unlike poller.unregister() below, whose
        # wrap is defensive against a documented-but-currently-unimplemented upstream TODO - see
        # BACKLOG.md).
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
        # Shared entry guard for every read/write method below - None unless called inside
        # `async with self:` on a not-deinitialized bus. Returns the narrowed machine.UART (not
        # just a bool) so mypy's None-narrowing still works through the resulting local variable.
        # See BACKLOG.md for why the lock check itself is kept, unlike SPIDevice/I2CDevice.
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
        # forever). Matches asy_udp_socket.py's own ready() defensive shape (see BACKLOG.md): a
        # concurrent deinit() can null self.poller mid-loop, and MemoryError/OSError are real,
        # if rare, possibilities on a device meant to run unattended for years.
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
        except MemoryError:  # check()'s own bytearr[0:n] slice allocates a fresh copy - see module docstring
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
                except MemoryError:  # unbounded across rounds, unlike read_until_complete()'s nbytes cap - see module docstring
                    return None
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
        try:
            framed = await self.crc.add(msg)  # add()'s own bytearr + crc_b allocates a fresh copy - see module docstring
        except MemoryError:
            return False
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
