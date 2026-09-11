"""Async wrapper around machine.UART: select.poll-driven non-blocking read/write, lock-scoped via
base_classes.Lockable so a read/write exchange runs atomically under `async with`. Optional
per-instance CRC framing (crc_checks.py's CRC_Base family) plus a pluggable frame codec (framing_codecs.py) on read_until_complete/readinto_until_complete/write/writefrom.
"""
# Whoever wires it in: GPIO24/25 and GPIO28/29 fall inside a UART pin-mux group and are
# wireless-reserved on Pico W - picking either pair for tx_pin/rx_pin silently collides with WiFi.
#
# A hardware-level framing/parity/overrun fault on rp2 never raises (see SPECIFICATION.md C.3.2) -
# every method here returns a plain None/False sentinel instead, never raises.

import asyncio
import select
import time

from machine import UART as _UART
from machine import Pin
from micropython import const

from base_classes import Lockable
from crc_checks import CRC_Base, CRC_Pass
from framing_codecs import Framing_Base, Framing_Pass

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Literal

_LF = const(0x0A)  # b"\n"[0] - readline_until_complete's own-line terminator

# How long cancel_read_timeout() waits for its request to be acknowledged before reporting the
# un-acknowledged case instead of waiting on. A healthy holder acknowledges within one poll round;
# only a genuinely wedged one reaches this bound, and it is what makes the call provably terminating.
_CANCEL_ACK_TIMEOUT_MS = const(1000)


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
        framing: Framing_Base | None = None,
    ) -> None:
        self._uart: _UART | None = None
        self.poller: select.poll | None = None
        super().__init__()
        self.poll_wait_ms = poll_wait_ms
        # A cancel request is latched (self.cancel) and acknowledged by publishing the request
        # number it served. Two monotonic counters rather than an Event: an acknowledgement stays
        # visible to every waiting canceller at once, and a second request can never re-clear one
        # that a first canceller has not yet observed.
        self.cancel = False
        self.cancel_unacknowledged = 0  # bumped when a holder never acknowledged within the bound
        self._cancel_req = 0
        self._cancel_ack = 0
        self.crc = CRC_Pass() if crc is None else crc
        # Write order is build -> CRC -> encode -> delimiter, read order the exact reverse, so the
        # CRC keeps its position underneath the codec. The pass-through default emits byte-for-byte
        # what this driver emitted before the codec existed; selecting a delimited one is a wire
        # change (UART_C_PORT_CHANGELOG.md A11), agreed out of band like baudrate itself.
        self.framing = Framing_Pass() if framing is None else framing
        self._skip_to_delimiter = False
        self.init(port_id, tx_pin, rx_pin, baudrate, bits, parity, stop, rxbuf, txbuf, timeout, timeout_char, invert)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> "Literal[False]":
        # Acknowledging here, and not only from inside ready()'s loop, is what makes
        # cancel_read_timeout() terminating: a request can land while the lock is held with no
        # ready() in flight (during crc.check()'s own per-byte yields, or between two reads), and
        # leaving the locked region is the last point at which it can still be honoured.
        self._ack_cancel()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

    def _ack_cancel(self) -> None:
        # Consumes a latched request exactly once. Never called speculatively: acknowledgement
        # means the read path has genuinely left the loop, so nothing reads after it.
        if self.cancel:
            self.cancel = False
            self._cancel_ack = self._cancel_req

    def resync_framing(self) -> None:
        # B2.2: after a resync the read path is somewhere inside a frame, so the bytes up to the
        # next delimiter are a fragment - discarded, never decoded, since a delimiter means "end of
        # something" and only the one after it bounds a whole frame. Inert for an undelimited codec.
        self._skip_to_delimiter = self.framing.is_delimited()

    def _active_uart(self) -> "_UART | None":
        # Shared entry guard for every read/write method - None unless called inside `async with
        # self:` on a live bus. Kept deliberately, unlike SPIDevice/I2CDevice: cancel_read_timeout()
        # infers "a read is in flight" purely from asy_lock.locked() - a lock-less caller is invisible to it.
        if not self.asy_lock.locked():
            return None
        return self._uart

    async def _write_all(self, uart: "_UART", buf: bytearray | memoryview) -> bool:
        # rp2 uart.write() can short-write instead of raising - retries with whatever's left until
        # the whole buffer is out or a real failure gives up, the write-side counterpart of
        # read_until_complete()'s own retry-until-done loop. The view is re-sliced only once a
        # short write has actually happened (B3.1): a complete write - the normal case - then costs
        # no memoryview allocation at all, and a degraded link is where allocation is least welcome.
        sent = 0
        total = len(buf)
        view = memoryview(buf)
        while sent < total:
            if not await self.ready(select.POLLOUT):
                return False
            n = uart.write(view if sent == 0 else view[sent:])
            if n is None:
                return False
            sent += n
        return True

    async def _read_delimited(
        self, uart: "_UART", buf: bytearray, nbytes: int, start_timeout_ms: int, timeout_ms: int,
    ) -> int | None:
        # Reads one delimiter-terminated frame into buf, decodes it in place and verifies its CRC.
        # One byte per readinto() on purpose: a wider read would swallow the head of the *next*
        # frame, which a stream cannot hand back. Bounded by the codec's own worst-case encoded
        # length (B2.1), so a peer that never sends a delimiter fails the read instead of blocking it.
        delimiter = self.framing.delimiter()
        if delimiter is None:
            return None
        bound = self.framing.max_encoded(nbytes)
        timeout = start_timeout_ms  # wait time for the first message part
        view = memoryview(buf)
        size = 0
        while True:
            if size >= bound:
                return None  # no delimiter within a whole worst-case frame: a decode failure
            got = uart.readinto(view[size : size + 1], 1)
            if got is None or got == 0:
                if not await self.ready(select.POLLIN, timeout_ms=timeout):
                    return None  # ready() timed out or was cancelled
                timeout = timeout_ms  # once started, use the regular timeout for the remaining parts
                continue
            timeout = timeout_ms
            if buf[size] != delimiter:
                size += 1
                continue
            if self._skip_to_delimiter:  # B2.2: the fragment a resync landed in the middle of
                self._skip_to_delimiter = False
                size = 0
                continue
            if size == 0:  # B2.3: two delimiters in a row - an empty frame is skipped, never surfaced
                continue
            break
        decoded = await self.framing.decode_from(buf, size)
        if decoded is None:
            return None
        return await self.crc.check_from(buf, size=decoded)

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
        # The _UART(...) below must stay a *construction*, never self._uart.init(...): rp2's
        # deinit() unroots the RX/TX ring buffers without clearing the pointers to them, and only
        # make_new() repairs that - see SPECIFICATION.md Part F.5.7.
        self.deinit()
        # Kept as plain attributes because machine.UART exposes neither back: a protocol layer
        # above has to size its own frames against the real receive buffer and the real baud rate
        # (a frame that does not fit rxbuf loses its tail silently), and cannot ask the peripheral.
        self.rxbuf = rxbuf
        self.baudrate = baudrate
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

    def deinit(self) -> bool:
        # machine.UART.deinit() actually turns off the hardware bus, not just drops the Python
        # reference - confirmed never to raise itself, unlike poller.unregister() below.
        # Returns True if the poller was cleanly unregistered (or there was nothing to unregister),
        # False if unregister() itself raised - this class has no logger of its own (every method
        # here is a plain sentinel-return, never-raises primitive per the module docstring), so a
        # caller that wants to log a failed teardown reads this return value with its own logger
        # once this driver is actually wired in (SPECIFICATION.md Part C.7's silent-failure-masking
        # convention - previously a bare `pass` with no signal at all, even once a real caller exists).
        if self._uart is None:
            return True
        ok = True
        if self.poller is not None:
            try:
                self.poller.unregister(self._uart)
            except (OSError, MemoryError):
                ok = False
        self._uart.deinit()
        self._uart = None
        self.poller = None
        return ok

    async def cancel_read_timeout(self, timeout_ms: int = _CANCEL_ACK_TIMEOUT_MS) -> bool:
        # Lets another task abort this instance's in-flight ready()/read wait from the outside -
        # e.g. to interrupt a stuck listen before resyncing. False means "nothing was in flight"
        # (the lock is not held), which is what lets a caller decide to take the lock and drain
        # itself; True means a cancel is outstanding, acknowledged or not, so the caller must not.
        if not self.asy_lock.locked():  # nothing to cancel if not in use
            return False
        self._cancel_req += 1
        my_req = self._cancel_req
        self.cancel = True
        t0 = time.ticks_ms()
        while self._cancel_ack < my_req:
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                self.cancel_unacknowledged += 1  # a wedged holder; the request stays latched
                return True
            await asyncio.sleep_ms(self.poll_wait_ms)
        return True

    async def ready(self, mask: int, timeout_ms: int = -1) -> bool:
        # Busy-polls ipoll(0), yielding via sleep_ms(poll_wait_ms), until mask is satisfied, a
        # cancel is requested, or timeout_ms elapses (<=0 waits forever). Defensive against a
        # concurrent deinit() nulling self.poller mid-loop.
        if self._uart is None or self.poller is None:
            return False
        t0 = time.ticks_ms()
        while True:
            if self.poller is None:  # a concurrent deinit() can null this mid-loop
                return False  # type: ignore[unreachable]  # mypy can't see the mutation
            # Checked before polling, and never cleared on entry: a request that arrived between
            # two reads must abort the next one rather than be erased by it, and a latched cancel
            # outranks readiness so that nothing is read after the acknowledgement.
            if self.cancel:
                self._ack_cancel()
                return False
            try:
                res = self.poller.ipoll(0)
                for _, event in res:
                    if event & mask:
                        return True
                if (timeout_ms > 0) and (time.ticks_diff(time.ticks_ms(), t0) > timeout_ms):
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
        self, nbytes: int, start_timeout_ms: int = -1, timeout_ms: int = -1,
    ) -> bytearray | None:
        # Reads exactly nbytes (+ CRC, if configured) across as many ready()/read() rounds as it
        # takes, then verifies/strips the trailing CRC in one go.
        uart = self._active_uart()
        if uart is None:
            return None
        nbytes += self.crc.length()
        if self.framing.is_delimited():
            try:
                buf = bytearray(self.framing.max_encoded(nbytes))
            except (MemoryError, OverflowError):
                return None
            size = await self._read_delimited(uart, buf, nbytes, start_timeout_ms, timeout_ms)
            if size is None:
                return None
            return bytearray(buf[0:size])
        timeout = start_timeout_ms  # wait time for the first message part
        msg = bytearray()
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
        except MemoryError:  # check()'s own bytearr[0:n] slice allocates a fresh copy
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
        self, buf: bytearray, nbytes: int, start_timeout_ms: int = -1, timeout_ms: int = -1,
    ) -> int | None:
        # readinto() counterpart of read_until_complete(): fills buf in place instead of
        # allocating a new bytearray per call.
        uart = self._active_uart()
        if uart is None:
            return None
        nbytes += self.crc.length()
        if self.framing.is_delimited():
            if self.framing.max_encoded(nbytes) > len(buf):
                return None  # B2.5: the caller's buffer must hold the worst-case encoded frame
            return await self._read_delimited(uart, buf, nbytes, start_timeout_ms, timeout_ms)
        timeout = start_timeout_ms  # wait time for the first message part
        size = 0
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
                except MemoryError:  # unbounded across rounds, unlike read_until_complete()'s nbytes cap
                    return None
                # `msg and` guards msg[-1]: readline() ready via poll can still return b"" (e.g. a
                # zero-length read), which would otherwise index an empty bytearray and raise.
                if msg and msg[-1] == _LF:  # trailing \n means the line is actually complete
                    break
                timeout = timeout_ms  # once started, use the regular timeout for the remaining parts
            else:
                return None  # ready() timed out or was cancelled
        return msg

    async def write(self, msg: bytearray) -> bool:  # write msg (+ CRC, if configured), retrying until it's all sent
        uart = self._active_uart()
        if uart is None:
            return False
        try:
            framed = await self.crc.add(msg)  # add()'s own bytearr + crc_b allocates a fresh copy
        except MemoryError:
            return False
        if framed is None:
            return False
        encoded = await self.framing.encode_into(framed, len(framed))
        if encoded is None:
            return False
        return await self._write_all(uart, encoded)

    async def writefrom(self, buf: bytearray, size: int) -> bool:  # write buf's first size bytes (+ CRC), retrying until it's all sent
        # buf belongs to this call for its duration - the caller must not mutate it until the call
        # returns (B3.4). This instance's own uses are already serialized by the session lock.
        uart = self._active_uart()
        if uart is None:
            return False
        if size < 0 or size + self.crc.length() > len(buf):
            return False  # B3.2: a short buffer is never a partial transfer reported as success
        crcsize = await self.crc.add_into(buf, size)
        if crcsize is None:
            return False
        encoded = await self.framing.encode_into(buf, crcsize)
        if encoded is None:
            return False
        return await self._write_all(uart, encoded)
