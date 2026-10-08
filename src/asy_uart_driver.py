"""Async wrapper around machine.UART: receives through a DMA ring off the UART FIFO and writes through its
TX ring, lock-scoped via asy_base_classes.Lockable so an exchange runs atomically under `async with`.
Optional per-instance CRC framing (asy_crc_checks.py) plus a pluggable frame codec (asy_framing_codecs.py)."""
# Whoever wires it in: GPIO24/25 (UART1) and GPIO28/29 (UART0) are valid pin-mux pairs, but the Pico
# W datasheet (p.8) hands GPIO23/24/25/29 to the wireless chip, so each pair has a taken half.
#
# A receive overrun, framing error or break fails the read in progress (C.3.2). Every method returns a sentinel,
# but readline_until_complete() lets its pieces' MemoryError through: its cap bounds them (J.8).

import asyncio
import select
import time
from array import array

from machine import UART as _UART
from machine import Pin, mem32
from micropython import const
from rp2 import DMA
from uctypes import addressof

from asy_base_classes import COUNTER_CAP, Lockable, PieceBuffer
from asy_crc_checks import CRCBase, CRCPass
from asy_framing_codecs import FramingBase, FramingPass

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Literal

    from asy_print_log import PrintLogHistory

_LF = const(0x0A)  # b"\n"[0] - readline_until_complete's own-line terminator

# How long cancel_read_timeout() waits for its request to be acknowledged before reporting the
# un-acknowledged case instead of waiting on. A healthy holder acknowledges within one poll round;
# only a genuinely wedged one reaches this bound, and it is what makes the call provably terminating.
# @tunable uart.cancel_ack_timeout_ms = 1000
_CANCEL_ACK_TIMEOUT_MS = const(1000)

# How many bytes _read_delimited() consumes between yields. It must read one byte per call (a wider
# read would swallow the next frame's head), so yielding per byte would cost a task switch every
# ~87us of wire time at 115200 baud; 16 bounds the loop's hold at ~1.4ms instead.
# @tunable uart.delimited_yield_bytes = 16
_DELIMITED_YIELD_BYTES = const(16)
_SEQ_HALF = const(0x20000000)  # half the 2**30 sequence space: a distance below it is "behind"
# The catalog code (buildgen/error_catalog.json) the capped readline logs through its caller's log: no logger here.
_ERR_UART_TRANSFER_CAP = const(93)

# Receives through a DMA ring, so a flash write that holds interrupts off (a sector erase, up to 400 ms) loses no
# byte; machine.UART's own receive path is kept off the FIFO (owner, 2026-10-05). Ring sizes are the powers of two
# the DMA's RING_SIZE field wraps (RP2040 datasheet 2.5.7); machine.UART keeps its minimum buffer (machine_uart.c).
_RX_RING_MIN = const(2)
_RX_RING_MAX = const(32768)
_UART_MIN_RXBUF = const(32)
# The data channel's transfer count: a multiple of every ring size, and below 2**30 so DMA.count stays a small int.
_RX_RELOAD = const(0x20000000)
_RX_POS_MASK = const(0x1FFFFFFF)

# UART registers (RP2040 datasheet 4.2.8, Table 425), each a literal: rp2 peripheral addresses are above the
# small-int range, so an address computed at run time would allocate a big int on every access.
_UART0_DR = const(0x40034000)
_UART0_RSR = const(0x40034004)
_UART0_IMSC = const(0x40034038)
_UART0_DMACR = const(0x40034048)
_UART1_DR = const(0x40038000)
_UART1_RSR = const(0x40038004)
_UART1_IMSC = const(0x40038038)
_UART1_DMACR = const(0x40038048)
_DREQ_UART0_RX = const(21)  # RP2040 datasheet 2.5.3.1
_DREQ_UART1_RX = const(23)
_IMSC_RX = const(0x50)  # RXIM (bit 4) | RTIM (bit 6), Table 435
_DMACR_RXDMAE = const(0x01)  # Table 439
# OE, FE and BE each mean a received byte is not what was sent: each fails the frame (Table 427).
# PE stays out of the mask: no link configures parity, so the bit carries nothing.
_RSR_ERRORS = const(0x0D)
_DMA_BASE = const(0x50000000)  # each channel's TRANS_COUNT trigger alias sits at 0x40 * channel + 0x1C (2.5.7)
_DMA_CH_STRIDE = const(0x40)
_DMA_TRANS_COUNT_TRIG = const(0x1C)


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
        # @tunable uart.rxbuf_default = 256
        rxbuf: int = 256,
        # @tunable uart.txbuf_default = 256
        txbuf: int = 256,
        timeout: int = 0,
        timeout_char: int = 1,
        invert: int = 0,
        # @tunable uart.rx_ring_default = 512
        rx_ring: int = 512,
        # @tunable uart.poll_wait_ms_default = 2
        poll_wait_ms: int = 2,
        # @tunable uart.poll_idle_ms_default = 50
        poll_idle_ms: int = 50,
        crc: CRCBase | None = None,
        framing: FramingBase | None = None,
    ) -> None:
        self._uart: _UART | None = None
        self.poller: select.poll | None = None
        super().__init__()
        self.poll_wait_ms = poll_wait_ms
        # The rate a deadline-less wait polls at: it stops an idle listener costing a task switch
        # every poll_wait_ms forever, and it bounds how late a frame's first byte is noticed, so it
        # belongs well under the peer's reply timeout.
        self.poll_idle_ms = poll_idle_ms
        # A cancel request is latched and acknowledged by publishing the request number it served: two
        # sequences rather than an Event, masked to COUNTER_CAP and compared by distance, so one
        # acknowledgement stays visible to every waiting canceller.
        self._cancel = False
        self.cancel_unacknowledged = 0  # bumped when a holder never acknowledged within the bound
        self._cancel_req = 0
        self._cancel_ack = 0
        # Bytes a failed *_until_complete() read consumed and dropped: a wrap-by-design count (masked to
        # COUNTER_CAP) a caller compares, never a total.
        self.discarded_bytes = 0
        self.crc = CRCPass() if crc is None else crc
        # Write order is build -> CRC -> encode -> delimiter, read the exact reverse, so the CRC
        # keeps its position underneath the codec. The pass-through default is byte-for-byte what
        # this driver emitted before; selecting a delimited one is a wire change (changelog A11).
        self.framing = FramingPass() if framing is None else framing
        self._skip_to_delimiter = False
        # The receive ring and its two DMA channels exist from setup_rx_ring() on, for the program's life.
        self._ring: memoryview | None = None
        self._rx_word: array[int] | None = None
        self._rx_dma: DMA | None = None
        self._rx_reload: DMA | None = None
        self._rx_pos = 0  # bytes consumed, modulo the data channel's reload count
        self._rx_overrun_pending = False
        self.rx_overruns = 0  # laps and UART receive errors, wrapped at COUNTER_CAP
        self.rx_ring_refusal = ""  # why the last setup_rx_ring() failed: "no bus", "ring size", "allocation", "DMA channel"
        self.init(port_id, tx_pin, rx_pin, baudrate, bits, parity, stop, rxbuf, txbuf, timeout, timeout_char, invert, rx_ring)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> "Literal[False]":
        # Acknowledging here, not only inside ready()'s loop, is what makes cancel_read_timeout()
        # terminating: a request can land while the lock is held with no ready() in flight, and
        # leaving the locked region is the last point at which it can still be honoured.
        self._ack_cancel()
        return await super().__aexit__(exc_type, exc_val, exc_tb)

    def _ack_cancel(self) -> None:
        # Consumes a latched request exactly once. Never called speculatively: acknowledgement
        # means the read path has genuinely left the loop, so nothing reads after it.
        if self._cancel:
            self._cancel = False
            self._cancel_ack = self._cancel_req

    def _active_uart(self) -> _UART | None:
        # Shared entry guard for every read/write method - None unless called inside `async with
        # self:` on a live bus. Kept deliberately, unlike SPIDevice/I2CDevice: cancel_read_timeout()
        # infers "a read is in flight" purely from session_lock.locked() - a lock-less caller is invisible to it.
        if not self.session_lock.locked():
            return None
        return self._uart

    def _arm_rx(self) -> None:
        # (Re)starts reception into the ring at its first byte. The reload channel is set up first, so the data
        # channel's first completion already finds it; an error flag left from before is not this stream's, so it
        # is cleared once the data channel has taken over the FIFO.
        data, reload, ring = self._rx_dma, self._rx_reload, self._ring
        if data is None or reload is None or ring is None:
            return
        data.active(False)
        reload.active(False)
        bits = 1
        while (1 << bits) < len(ring):
            bits += 1
        reload.config(
            read=self._rx_word, write=_DMA_BASE + data.channel * _DMA_CH_STRIDE + _DMA_TRANS_COUNT_TRIG, count=1,
            ctrl=reload.pack_ctrl(inc_read=False, inc_write=False),
        )
        data.config(
            read=self._reg_dr, write=ring, count=_RX_RELOAD, trigger=True,
            ctrl=data.pack_ctrl(size=0, inc_read=False, inc_write=True, ring_sel=True, ring_size=bits, treq_sel=self._dreq, chain_to=reload.channel),
        )
        mem32[self._reg_rsr] = 0  # UARTECR: any write clears OE, BE, PE and FE
        self._rx_pos = 0
        self._rx_overrun_pending = False

    def _buffered(self, want: int) -> int:
        # Every read goes through here: clamped to the ring's fill level, so no read ever waits for a byte that
        # has not arrived (F.5.8), and never below zero. -1 reports a receive overrun once, to the read that sees
        # it, and drops whatever is unread by then: the frame the overrun hit fails whole.
        level = self._rx_level()
        if level < 0:
            self._rx_overrun_pending = False
            data = self._rx_dma
            if data is not None:
                try:
                    self._rx_drop(data)
                except (OSError, ValueError):  # a closed channel: nothing left to drop
                    pass
            return -1
        return min(max(want, 0), level)

    def _count_discarded(self, n: int) -> None:
        # masked to COUNTER_CAP by a conditional wrap, never add-then-mask
        if n > 0:
            d = self.discarded_bytes
            self.discarded_bytes = d + n if d <= COUNTER_CAP - n else d - (COUNTER_CAP - n) - 1

    def _line_failed(self, line: PieceBuffer | None, size: int) -> None:
        # A readline that fails part-way: what it had copied is dropped and counted (a dropped line counted as it went).
        if line is not None:
            self._count_discarded(size)

    async def _read_delimited(
        self, buf: bytearray, nbytes: int, start_timeout_ms: int, timeout_ms: int,
    ) -> int | None:
        # Reads one delimiter-terminated frame into buf, decodes in place and verifies its CRC. One
        # byte at a time on purpose: the bytes after the delimiter are the next frame's head and stay
        # in the ring. Bounded by the codec's worst-case length.
        delimiter = self.framing.delimiter()
        if delimiter is None:
            return None
        bound = self.framing.max_encoded(nbytes)
        timeout = start_timeout_ms  # wait time for the first message part
        size = 0
        consumed = 0
        while True:
            if size >= bound:
                self._count_discarded(consumed)
                return None  # no delimiter within a whole worst-case frame: a decode failure
            got = self._buffered(1)
            if got < 0:
                self._count_discarded(consumed)
                return None  # a receive overrun fails the frame
            if not got:
                if not await self.ready(select.POLLIN, timeout_ms=timeout):
                    self._count_discarded(consumed)
                    return None  # ready() timed out or was cancelled
                timeout = timeout_ms  # once started, use the regular timeout for the remaining parts
                continue
            if self._rx_copy(buf, size, 1) < 0:
                self._count_discarded(consumed)
                return None
            timeout = timeout_ms
            consumed += 1
            if not consumed % _DELIMITED_YIELD_BYTES:  # every consumed byte counts, skipped ones included:
                await asyncio.sleep_ms(0)  # this loop never reaches ready()'s own yield while bytes are buffered
                if self.poller is None:  # a deinit() during the yield
                    self._count_discarded(consumed)
                    return None
            if buf[size] != delimiter:
                size += 1
                continue
            if self._skip_to_delimiter:  # the fragment a resync landed in the middle of
                self._skip_to_delimiter = False
                size = 0
                continue
            if size == 0:  # two delimiters in a row - an empty frame is skipped, never surfaced
                continue
            break
        decoded = await self.framing.decode_from(buf, size)
        if decoded is None:
            self._count_discarded(consumed)
            return None
        checked = await self.crc.check_from(buf, size=decoded)
        if checked is None:
            self._count_discarded(consumed)
        return checked

    def _rx_copy(self, dest: bytearray | memoryview | None, start: int, n: int) -> int:
        # Copies n buffered bytes into dest[start:] by index - no slice, no allocation - and consumes them (dest
        # None: consumed only). Checked again after the copy: a lap during it overwrote bytes already copied.
        ring, data = self._ring, self._rx_dma
        if ring is None or data is None:
            return -1
        mask = len(ring) - 1
        pos = self._rx_pos
        if dest is not None:
            for i in range(n):
                dest[start + i] = ring[(pos + i) & mask]
        try:
            lapped = ((_RX_RELOAD - data.count - pos) & _RX_POS_MASK) > len(ring)
        except (OSError, ValueError):  # a closed channel: nothing copied can be trusted
            return -1
        if lapped:
            self._rx_discard(data)
            return -1
        self._rx_pos = (pos + n) & _RX_POS_MASK
        return n

    def _rx_copy_line(self, line: PieceBuffer | None, offset: int, n: int) -> int:
        # _rx_copy() into the line's pieces from offset, piece by piece; a dropped line (None) is consumed uncopied.
        if line is None:
            return self._rx_copy(None, 0, n)
        base = 0
        left = n
        for piece in line.pieces():
            end = base + len(piece)
            if left and offset < end:
                k = min(left, end - offset)
                if self._rx_copy(piece, offset - base, k) < 0:
                    self._count_discarded(n - left)  # this round's pieces already consumed
                    return -1
                offset += k
                left -= k
            base = end
        return -1 if left else n

    def _rx_discard(self, data: DMA) -> None:
        # A lap or a UART receive error: everything unread is dropped and counted, so the frame it belonged to
        # fails as J.7's receive overrun and the caller resyncs.
        mem32[self._reg_rsr] = 0
        self._rx_drop(data)
        n = self.rx_overruns
        self.rx_overruns = n + 1 if n < COUNTER_CAP else 0

    def _rx_drop(self, data: DMA) -> None:
        self._rx_pos = (_RX_RELOAD - data.count) & _RX_POS_MASK  # the consumer catches up: nothing is unread

    def _rx_level(self) -> int:
        # Bytes received and not yet read, from TRANS_COUNT alone: WRITE_ADDR reads wrong during ring transfers
        # (RP2040-E12). -1 is a receive overrun (a lap, or OE/FE/BE in UARTRSR), pending until a read reports it.
        if self._rx_overrun_pending:
            return -1
        ring, data = self._ring, self._rx_dma
        if ring is None or data is None or self._uart is None:
            return 0
        try:
            level = (_RX_RELOAD - data.count - self._rx_pos) & _RX_POS_MASK
            if level > len(ring) or mem32[self._reg_rsr] & _RSR_ERRORS:
                self._rx_discard(data)
                self._rx_overrun_pending = True
                return -1
        except (OSError, ValueError):  # a closed channel reads as a silent line: readers time out at the poll
            return 0  # rates instead of failing at once, which would spin a listener and log every round
        return level

    def _rx_line_len(self, level: int) -> int:
        # The buffered bytes up to and including the first LF, else all of them.
        ring = self._ring
        if ring is None:
            return 0
        mask = len(ring) - 1
        pos = self._rx_pos
        for i in range(level):
            if ring[(pos + i) & mask] == _LF:
                return i + 1
        return level

    def _rx_peek(self, i: int) -> int:
        # The i-th buffered byte, unconsumed; -1 without a ring.
        ring = self._ring
        if ring is None:
            return -1
        return ring[(self._rx_pos + i) & (len(ring) - 1)]

    async def _write_all(self, uart: _UART, buf: bytearray | memoryview, timeout_ms: int) -> bool:
        # Write only into an empty TX ring, at most txbuf bytes: POLLOUT means one free byte, and a longer
        # write waits per byte inside machine.UART.write() (F.5.8). rp2 can still short-write, so the rest is
        # retried; the view is re-sliced only then, so a frame that fits allocates no slice.
        sent = 0
        total = len(buf)
        view = memoryview(buf)
        t0 = time.ticks_ms()
        while sent < total:
            wait = -1
            if timeout_ms > 0:  # the whole write's deadline: a TX that never drains fails it (<= 0 waits on)
                wait = timeout_ms - time.ticks_diff(time.ticks_ms(), t0)
                if wait <= 0:
                    return False
            if not await self.ready(select.POLLOUT, timeout_ms=wait):
                return False
            if not uart.txdone():
                await asyncio.sleep_ms(self.poll_wait_ms)
                continue
            chunk = min(total - sent, self._txbuf)
            n = uart.write(view if sent == 0 and chunk == total else view[sent : sent + chunk])
            if n is None:
                return False
            sent += n
        return True

    async def cancel_read_timeout(self, timeout_ms: int = _CANCEL_ACK_TIMEOUT_MS) -> bool:
        # Lets another task abort this instance's in-flight ready()/read wait from the outside.
        # False means "nothing was in flight" (the lock is free), which is what lets a caller take
        # the lock and drain itself; True means a cancel is outstanding, so it must not.
        if not self.session_lock.locked():  # nothing to cancel if not in use
            return False
        # Wrap-by-design sequences stepped by a conditional wrap, never `+ 1` then masked, so no intermediate
        # leaves the small-int range; compared by distance or equality only.
        self._cancel_req = self._cancel_req + 1 if self._cancel_req < COUNTER_CAP else 0
        my_req = self._cancel_req
        self._cancel = True
        t0 = time.ticks_ms()
        while 0 < ((my_req - self._cancel_ack) & COUNTER_CAP) < _SEQ_HALF:
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                n = self.cancel_unacknowledged  # a wedged holder; the request stays latched
                self.cancel_unacknowledged = n + 1 if n < COUNTER_CAP else 0
                return True
            await asyncio.sleep_ms(self.poll_wait_ms)
        return True

    def deinit(self) -> bool:
        # machine.UART.deinit() turns the hardware bus off and never raises; poller.unregister()
        # can, and False is returned only in that case - this class has no logger of its own, so the
        # caller logs a failed teardown with its own (SPECIFICATION.md Part C.7).
        if self._uart is None:
            return True
        ok = True
        if self._rx_dma is not None and self._rx_reload is not None:
            try:  # stopped, never closed: init() re-arms them on the same ring
                self._rx_dma.active(False)
                self._rx_reload.active(False)
            except (OSError, ValueError):
                ok = False
        if self.poller is not None:
            try:
                self.poller.unregister(self._uart)
            except (MemoryError, OSError):
                ok = False
        self._uart.deinit()
        self._uart = None
        self.poller = None
        return ok

    def init(
        self,
        port_id: int,
        tx_pin: int,
        rx_pin: int,
        baudrate: int = 9600,
        bits: int = 8,
        parity: int | None = None,
        stop: int = 1,
        # @tunable uart.rxbuf_default = 256
        rxbuf: int = 256,
        # @tunable uart.txbuf_default = 256
        txbuf: int = 256,
        timeout: int = 0,
        timeout_char: int = 1,
        invert: int = 0,
        # @tunable uart.rx_ring_default = 512
        rx_ring: int = 512,
    ) -> None:
        # deinit() first so re-init cannot leak a claimed peripheral, pins or a stale poll
        # registration, as asy_spi_driver.py/asy_i2c_driver.py do. The _UART(...) below must stay a
        # construction, never self._uart.init(...): only make_new() re-roots the ring buffers (F.5.7).
        if self._ring is not None and rx_ring != len(self._ring):
            raise ValueError("rx_ring is fixed once the ring is allocated")
        self.deinit()
        # Kept as plain attributes because machine.UART exposes none of them back: a protocol layer
        # above sizes its frames against the receive buffer and the baud rate, and _write_all() bounds
        # each write by the TX ring's size.
        self.rxbuf = rxbuf
        self.baudrate = baudrate
        self._txbuf = txbuf
        self.rx_ring = rx_ring
        uart1 = port_id == 1
        self._reg_dr = _UART1_DR if uart1 else _UART0_DR
        self._reg_rsr = _UART1_RSR if uart1 else _UART0_RSR
        self._reg_imsc = _UART1_IMSC if uart1 else _UART0_IMSC
        self._reg_dmacr = _UART1_DMACR if uart1 else _UART0_DMACR
        self._dreq = _DREQ_UART1_RX if uart1 else _DREQ_UART0_RX
        self._uart = _UART(
            port_id,
            baudrate=baudrate,
            tx=Pin(tx_pin),
            rx=Pin(rx_pin),
            bits=bits,
            parity=parity,
            stop=stop,
            rxbuf=_UART_MIN_RXBUF,
            txbuf=txbuf,
            timeout=timeout,
            timeout_char=timeout_char,
            invert=invert,
        )
        # Every construction enables the RX interrupts, whose handler drains the FIFO the ring reads: masked
        # first, before anything allocates, so no collection widens the window. uart_init() sets RXDMAE too;
        # it is set here as well, since the ring depends on it and a deinit() resets the block (clearing it).
        mem32[self._reg_imsc] = mem32[self._reg_imsc] & ~_IMSC_RX
        mem32[self._reg_dmacr] = mem32[self._reg_dmacr] | _DMACR_RXDMAE
        self.poller = select.poll()
        self.poller.register(self._uart, select.POLLOUT)
        if self._ring is not None:
            # A re-init restarts the stream: a byte the handler took before the mask fails the next read
            # as an overrun, so the caller resyncs instead of reading a frame with a hole in it.
            self._arm_rx()
            self._rx_overrun_pending = True

    async def read(self, nbytes: int | None = None, timeout_ms: int = -1) -> bytes | None:
        uart = self._active_uart()
        if uart is None:
            return None
        if not await self.ready(select.POLLIN, timeout_ms=timeout_ms):
            return None
        want = self._buffered(self.rxbuf if nbytes is None else nbytes)
        if want <= 0:
            return None
        try:
            out = bytearray(want)
            if self._rx_copy(out, 0, want) < 0:
                return None
            return bytes(out)
        except MemoryError:
            return None

    async def read_until_complete(
        self, nbytes: int, start_timeout_ms: int = -1, timeout_ms: int = -1,
    ) -> bytearray | None:
        # Reads exactly nbytes (+ CRC, if configured) across as many ready()/copy rounds as it
        # takes, then verifies/strips the trailing CRC in one go.
        uart = self._active_uart()
        if uart is None or nbytes < 0:
            return None  # a negative size is refused, as writefrom() refuses one
        if nbytes == 0:
            return bytearray()
        nbytes += self.crc.length()
        try:
            msg = bytearray(self.framing.max_encoded(nbytes) if self.framing.is_delimited() else nbytes)
        except (MemoryError, OverflowError):
            return None
        if self.framing.is_delimited():
            size = await self._read_delimited(msg, nbytes, start_timeout_ms, timeout_ms)
            if size is None:
                return None
            return bytearray(msg[0:size])
        timeout = start_timeout_ms  # wait time for the first message part
        size = 0
        while size < nbytes:
            if not await self.ready(select.POLLIN, timeout_ms=timeout):
                self._count_discarded(size)
                return None  # ready() timed out or was cancelled
            want = self._buffered(nbytes - size)
            if want < 0:
                self._count_discarded(size)
                return None  # a receive overrun fails the frame
            if not want:  # ready without a buffered byte: yield rather than spin on ready()
                await asyncio.sleep_ms(self.poll_wait_ms)
                continue
            if self._rx_copy(msg, size, want) < 0:
                self._count_discarded(size)
                return None
            size += want
            timeout = timeout_ms  # once started, use the regular timeout for the remaining parts
        try:
            checked = await self.crc.check(msg)
        except MemoryError:  # check()'s own bytearr[0:n] slice allocates a fresh copy
            checked = None
        if checked is None:
            self._count_discarded(size)
        return checked

    async def readinto(self, buf: bytearray, nbytes: int | None = None, timeout_ms: int = -1) -> int | None:
        uart = self._active_uart()
        if uart is None:
            return None
        if not await self.ready(select.POLLIN, timeout_ms=timeout_ms):
            return None
        want = self._buffered(len(buf) if nbytes is None else min(nbytes, len(buf)))
        if want <= 0:
            return None
        n = self._rx_copy(buf, 0, want)
        return n if n > 0 else None

    async def readinto_until_complete(
        self, buf: bytearray, nbytes: int, start_timeout_ms: int = -1, timeout_ms: int = -1,
    ) -> int | None:
        # readinto() counterpart of read_until_complete(): fills buf in place instead of
        # allocating a new bytearray per call.
        uart = self._active_uart()
        if uart is None or nbytes < 0:
            return None  # a negative size is refused, as writefrom() refuses one
        if nbytes == 0:
            return 0
        nbytes += self.crc.length()
        if self.framing.is_delimited():
            if self.framing.max_encoded(nbytes) > len(buf):
                return None  # the caller's buffer must hold the worst-case encoded frame
            return await self._read_delimited(buf, nbytes, start_timeout_ms, timeout_ms)
        timeout = start_timeout_ms  # wait time for the first message part
        size = 0
        if nbytes > len(buf):
            return None
        while size < nbytes:
            if not await self.ready(select.POLLIN, timeout_ms=timeout):
                self._count_discarded(size)
                return None  # ready() timed out or was cancelled
            want = self._buffered(nbytes - size)
            if want < 0:
                self._count_discarded(size)
                return None  # a receive overrun fails the frame
            if not want:  # see read_until_complete()'s own comment - yield, never spin
                await asyncio.sleep_ms(self.poll_wait_ms)
                continue
            if self._rx_copy(buf, size, want) < 0:
                self._count_discarded(size)
                return None
            size += want
            timeout = timeout_ms  # once started, use the regular timeout for the remaining parts
        checked = await self.crc.check_from(buf, size=size)
        if checked is None:
            self._count_discarded(size)
        return checked

    async def readline(self, timeout_ms: int = -1) -> bytes | None:
        # Read from the ring by index, never through the FIFO API: up to the first LF among the buffered bytes.
        uart = self._active_uart()
        if uart is None:
            return None
        if not await self.ready(select.POLLIN, timeout_ms=timeout_ms):
            return None
        want = self._buffered(self.rxbuf)
        if want <= 0:
            return None
        n = self._rx_line_len(want)
        try:
            out = bytearray(n)
            if self._rx_copy(out, 0, n) < 0:
                return None
            return bytes(out)
        except MemoryError:
            return None

    async def readline_until_complete(
        self, max_bytes: int, chunk_bytes: int, log: "PrintLogHistory", start_timeout_ms: int = -1, timeout_ms: int = -1,
    ) -> PieceBuffer | None:
        # No CRC framing here: newline-terminated text. The line lands in pieces of at most chunk_bytes, copied by
        # index; one over max_bytes is read to its end, dropped, counted in discarded_bytes and logged once.
        uart = self._active_uart()
        if uart is None or max_bytes < 1 or chunk_bytes < 1:
            return None
        line: PieceBuffer | None = PieceBuffer(max_bytes, chunk_bytes)
        timeout = start_timeout_ms  # wait time for the first message part
        size = 0  # the line's length so far, saturated at COUNTER_CAP once it is being dropped
        while True:
            if not await self.ready(select.POLLIN, timeout_ms=timeout):
                self._line_failed(line, size)  # ready() timed out or was cancelled
                return None
            want = self._buffered(self.rxbuf)
            if want < 0:
                self._line_failed(line, size)  # a receive overrun fails the line
                return None
            if not want:  # see read_until_complete()'s own comment
                await asyncio.sleep_ms(self.poll_wait_ms)
                continue
            n = self._rx_line_len(want)
            ended = self._rx_peek(n - 1) == _LF
            if line is not None and size + n > max_bytes:
                self._count_discarded(size)  # over the cap: the pieces go, the rest is consumed uncopied
                line = None
            if self._rx_copy_line(line, size, n) < 0:
                self._line_failed(line, size)
                return None
            if line is None:
                self._count_discarded(n)
            size = size + n if size <= COUNTER_CAP - n else COUNTER_CAP
            if ended:
                break
            timeout = timeout_ms  # once started, use the regular timeout for the remaining parts
        if line is None:
            await log.err_s("UART line over the cap, discarded:", size, errno=_ERR_UART_TRANSFER_CAP)
            return None
        return line if line.trim(size) else None

    async def ready(self, mask: int, timeout_ms: int = -1) -> bool:
        # Polls until mask is satisfied, a cancel is requested, or timeout_ms elapses (<=0 waits forever),
        # sleeping between rounds: POLLIN from the ring's fill level, POLLOUT from the TX ring through
        # ipoll(0). Defensive against a concurrent deinit() nulling self.poller mid-loop.
        if self._uart is None or self.poller is None:
            return False
        # A deadline-less wait is an idle listener; one with a deadline is inside a transaction
        # whose latency budget is that deadline. Polling both at poll_wait_ms is what made an idle
        # responder cost a third of the event loop with nothing on the wire at all (F.5.9).
        wait_ms = self.poll_wait_ms if timeout_ms > 0 else self.poll_idle_ms
        t0 = time.ticks_ms()
        while True:
            if self.poller is None:  # a concurrent deinit() can null this mid-loop
                return False  # type: ignore[unreachable]  # mypy can't see the mutation
            # Checked before polling, and never cleared on entry: a request that arrived between
            # two reads must abort the next one rather than be erased by it, and a latched cancel
            # outranks readiness so that nothing is read after the acknowledgement.
            if self._cancel:
                self._ack_cancel()
                return False
            try:
                got = 0
                if mask & select.POLLIN and self._rx_level():  # an overrun (-1) is ready too: the read reports it
                    got |= select.POLLIN
                if mask & select.POLLOUT:
                    for _, event in self.poller.ipoll(0):
                        got |= event
                if got & mask:
                    break
                if (timeout_ms > 0) and (time.ticks_diff(time.ticks_ms(), t0) > timeout_ms):
                    return False
                await asyncio.sleep_ms(wait_ms)
            except (MemoryError, OSError, OverflowError, TypeError):
                # TypeError: a malformed mask/timeout_ms; callers' excepts wrap only the UART call.
                # OverflowError: a wait beyond the ticks range - asyncio.sleep_ms() raises it for a delta >= 2**29 ms.
                return False
        # The one yield every read loop relies on: readiness is reported with no await of its own,
        # so a caller looping ready()->read()->ready() over a frame still in flight would hold the
        # event loop for the whole transmission - the clamp above alone made that worse (F.5.8).
        await asyncio.sleep_ms(0)
        # A deinit() during the yield must not hand the caller a dead UART (its RX ring is unrooted, F.5.7).
        return self.poller is not None

    def resync_framing(self) -> None:
        # After a resync the read path is somewhere inside a frame, so the bytes up to the
        # next delimiter are a fragment - discarded, never decoded, since a delimiter means "end of
        # something" and only the one after it bounds a whole frame. Inert for an undelimited codec.
        self._skip_to_delimiter = self.framing.is_delimited()

    def setup_rx_ring(self) -> bool:
        # Allocates the ring once - twice its size, so a naturally aligned window always fits - and arms its two
        # DMA channels; the link's setup() calls it once. False leaves nothing armed: no bus, a size the DMA
        # cannot wrap, a failed allocation, no free channel, or a refused channel configuration.
        if self._ring is not None:
            return True
        size = self.rx_ring
        if self._uart is None:
            self.rx_ring_refusal = "no bus"
            return False
        if not (_RX_RING_MIN <= size <= _RX_RING_MAX) or size & (size - 1):
            self.rx_ring_refusal = "ring size"
            return False
        data = reload = None
        try:
            mem = bytearray(2 * size)
            start = -addressof(mem) & (size - 1)
            self._ring = memoryview(mem)[start : start + size]
            self._rx_word = array("I", (_RX_RELOAD,))
            data = DMA()
            reload = DMA()
            self._rx_dma, self._rx_reload = data, reload
            self._arm_rx()
        except (MemoryError, OSError, ValueError) as e:
            for channel in (data, reload):
                if channel is not None:
                    channel.close()
            self._ring = self._rx_word = self._rx_dma = self._rx_reload = None
            self.rx_ring_refusal = "allocation" if isinstance(e, MemoryError) else "DMA channel"
            return False
        self.rx_ring_refusal = ""
        return True

    async def write(self, msg: bytearray, timeout_ms: int = -1) -> bool:  # write msg (+ CRC, if configured), retrying until it's all sent
        uart = self._active_uart()
        if uart is None:
            return False
        # A zero-length payload is sent as nothing: no receiver can verify a CRC-only frame.
        if not msg:
            return True
        try:
            framed = await self.crc.add(msg)  # add()'s own bytearr + crc_b allocates a fresh copy
        except MemoryError:
            return False
        if framed is None:
            return False
        encoded = await self.framing.encode_into(framed, len(framed))
        if encoded is None:
            return False
        return await self._write_all(uart, encoded, timeout_ms)

    async def writefrom(self, buf: bytearray, size: int, timeout_ms: int = -1) -> bool:  # write buf's first size bytes (+ CRC), retrying until it's all sent
        # buf belongs to this call for its duration - the caller must not mutate it until the call
        # returns. This instance's own uses are already serialized by the session lock.
        uart = self._active_uart()
        if uart is None:
            return False
        if size < 0 or size + self.crc.length() > len(buf):
            return False  # a short buffer is never a partial transfer reported as success
        if size == 0:
            return True
        crcsize = await self.crc.add_into(buf, size)
        if crcsize is None:
            return False
        encoded = await self.framing.encode_into(buf, crcsize)
        if encoded is None:
            return False
        return await self._write_all(uart, encoded, timeout_ms)
