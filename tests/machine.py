"""Test-only fake `machine` module: mocks only the raw I2C/SPI bus-transaction level (per SPECIFICATION.md Part E.4's mocking boundary) so the real drivers' own logic runs for real against it. Only implements what src/'s own imports need.
`Timer` is also why this file has to exist beyond I2C/SPI mocking: it's what makes `from machine import Timer` resolve under mypy's `src tests` scope (see BACKLOG.md's "Timer mypy resolution" finding)."""

import errno
import io
import select

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, ClassVar


class Pin:
    IN = 0
    OUT = 1
    # Real rp2 values (confirmed against ports/rp2/machine_pin.c: IRQ_RISING maps to the pico-sdk's
    # GPIO_IRQ_EDGE_RISE=0x08, IRQ_FALLING to GPIO_IRQ_EDGE_FALL=0x04) - asy_scd30_driver.py only
    # ever passes these back opaquely to irq(), but matching the real bit values costs nothing.
    IRQ_FALLING = 0x04
    IRQ_RISING = 0x08

    def __init__(self, id: int, mode: int = -1, pull: int = -1, *, value: object = None) -> None:
        # Real rp2 Pin() raises for a genuinely invalid id (confirmed against ports/rp2/
        # machine_pin.c: TypeError for a non-int identifier, ValueError for one outside the
        # RP2040's real GPIO0-28 range) - validated here (previously not at all) since this is a
        # real, documented "one-time setup, allowed to raise" contract multiple drivers'
        # docstrings claim, that had no test anywhere actually exercising it.
        if not isinstance(id, int):
            raise TypeError("Pin id must be an int")
        if not (0 <= id <= 28):
            raise ValueError("invalid pin")
        self.id = id
        self.mode = mode
        self.pull = pull
        # Real rp2 Pin(): an initial value= is applied via the same path value() already uses -
        # only meaningful for an OUT-mode pin, but the real constructor doesn't validate that
        # either (it's silently inert on an IN pin), so this fake doesn't validate it either.
        self._value = 0 if value is None else (1 if value else 0)
        self._irq_handler: Callable[[Pin], None] | None = None
        self._irq_trigger = self.IRQ_FALLING | self.IRQ_RISING
        self._irq_hard = False

    def init(self, mode: int = -1, pull: int = -1) -> None:
        # Real machine.Pin.init(): omitted/-1 args leave the current setting untouched.
        if mode != -1:
            self.mode = mode

    def value(self, x: object = None) -> int | None:
        # Real rp2 Pin.value(): reads back gpio_get() even for an OUT pin (confirmed against
        # ports/rp2/machine_pin.c) - not "undefined" the way the cross-port docs hedge.
        if x is None:
            return self._value
        self._value = 1 if x else 0
        return None

    def on(self) -> None:
        self._value = 1

    def off(self) -> None:
        self._value = 0

    def toggle(self) -> None:
        self._value = 0 if self._value else 1

    def irq(
        self,
        handler: "Callable[[Pin], None] | None" = None,
        trigger: int = IRQ_FALLING | IRQ_RISING,
        *,
        hard: bool = False,
    ) -> "Pin":
        # Real rp2 Pin.irq() (confirmed against ports/rp2/machine_pin.c): a second call replaces
        # the previous handler/trigger outright rather than stacking, and the real return value is
        # the IRQ object itself - this fake stands in for that with the Pin instance, since nothing
        # in this codebase inspects what irq() returns. The real handler fires on every matching
        # edge until irq() is called again (handler=None or trigger=0 disables it), never just once;
        # trigger_irq() below is how test code simulates one such edge deterministically, the same
        # role Timer.trigger() plays for the fake Timer above.
        self._irq_handler = handler
        self._irq_trigger = trigger
        self._irq_hard = hard
        return self

    def trigger_irq(self) -> None:
        # No real-hardware equivalent - fires the currently-registered handler once, standing in
        # for one real edge interrupt. No-op if irq() was never called or was disabled.
        if self._irq_handler is not None:
            self._irq_handler(self)


class I2C:
    # Real RP2040 I2C error codes (confirmed against ports/rp2/machine_i2c.c, not guessed): the
    # hardware I2C driver only ever raises OSError(errno.EIO) - covers a NAK/no response and any
    # other general bus fault, which is also what a real multi-master arbitration loss would
    # surface as on this port - or OSError(errno.ETIMEDOUT), the Pico SDK's own bus-busy/
    # clock-stretch timeout. There is no distinct errno for "arbitration lost" on this port; both
    # fold into one of the two above. nak_addresses/busy below model exactly those two conditions.
    #
    # Registers are a plain dict of (address, reg_addr) -> bytearray, seeded directly by a test
    # via .registers before exercising get_bits/set_bits/get_register_struct/set_register_struct
    # - a real round trip through readfrom_mem/writeto_mem, not a canned return value.
    #
    # read_queue is the raw-transaction counterpart (readfrom_into has no register address to key
    # off of - a driver issuing its own command bytes via writeto() then reading a reply via
    # readfrom_into(), e.g. asy_sgp40_driver.py's word-oriented protocol): a FIFO of byte strings a
    # test primes before each expected readfrom_into() call, mirroring SPI's own read_queue below.
    def __init__(self, id: int, *, scl: Pin, sda: Pin, freq: int = 400000, timeout: int = 50000) -> None:
        self.id = id
        self.scl = scl
        self.sda = sda
        self.freq = freq
        self.timeout = timeout
        self.deinit_called = False
        self.deinit_count = 0
        self.log: list[tuple[Any, ...]] = []
        self.registers: dict[tuple[int, int], bytearray] = {}
        self.read_queue: list[bytes] = []
        self.nak_addresses: set[int] = set()  # convenience: EIO (no ACK) on every op to this address
        self.busy = False  # convenience: ETIMEDOUT (bus/clock-stretch timeout) on every op, any address
        self._faults: dict[str, list[Exception]] = {}  # op name -> FIFO queue, one exception per matching call

    def inject_fault(self, op: str, exc: Exception, times: int = 1) -> None:
        # Queues `exc` to be raised on the next `times` calls to the named op (readfrom_into,
        # writeto, readfrom_mem, writeto_mem, or scan) - lets a test fail one specific step of a
        # multi-step operation (e.g. the read half of write_then_readinto) without affecting the
        # others, modeling a transfer interrupted partway through.
        self._faults.setdefault(op, []).extend([exc] * times)

    def _maybe_raise(self, op: str, address: int) -> None:
        if self.busy:
            raise OSError(errno.ETIMEDOUT, "bus busy / clock stretch timeout")
        if address in self.nak_addresses:
            raise OSError(errno.EIO, "no ACK from device")
        queue = self._faults.get(op)
        if queue:
            raise queue.pop(0)

    def deinit(self) -> None:
        # Real rp2 machine.I2C.deinit() exists only from MicroPython 1.29 on, and even there the
        # port leaves the protocol's .deinit slot NULL - it is a silent no-op that neither stops
        # the peripheral nor releases the pins (SPECIFICATION.md Part F.5). This fake therefore
        # deliberately leaves every bus operation working afterwards, exactly like real hardware;
        # the counters below only record that asy_i2c_driver.py forwarded the call.
        self.deinit_called = True
        self.deinit_count += 1
        self.log.append(("deinit",))

    def scan(self) -> list[int]:
        self.log.append(("scan",))
        if self.busy:
            raise OSError(errno.ETIMEDOUT, "bus busy / clock stretch timeout")
        queue = self._faults.get("scan")
        if queue:
            raise queue.pop(0)
        return sorted({addr for addr, _ in self.registers} - self.nak_addresses)

    def _next_read_bytes(self, nbytes: int) -> bytes:
        data = self.read_queue.pop(0) if self.read_queue else b""
        return (data + bytes(nbytes))[:nbytes]  # always exactly nbytes, zero-padded/truncated like real hw

    def readfrom_into(self, address: int, buf: object, stop: bool = True) -> None:
        self._maybe_raise("readfrom_into", address)
        data = self._next_read_bytes(len(buf))  # type: ignore[arg-type]
        buf[:] = data  # type: ignore[index]
        self.log.append(("readfrom_into", address, data, stop))

    def writeto(self, address: int, buf: object, stop: bool = True) -> int:
        self._maybe_raise("writeto", address)
        data = bytes(buf)  # type: ignore[call-overload]
        self.log.append(("writeto", address, data, stop))
        return len(data)

    def readfrom_mem(self, address: int, memaddr: int, nbytes: int, *, addrsize: int = 8) -> bytes:
        self._maybe_raise("readfrom_mem", address)
        stored = bytes(self.registers.get((address, memaddr), bytearray(nbytes)))
        data = (stored + bytes(nbytes))[:nbytes]  # always exactly nbytes, zero-padded/truncated like real hw
        self.log.append(("readfrom_mem", address, memaddr, nbytes, addrsize))
        return data

    def writeto_mem(self, address: int, memaddr: int, buf: object, *, addrsize: int = 8) -> None:
        self._maybe_raise("writeto_mem", address)
        self.registers[(address, memaddr)] = bytearray(buf)  # type: ignore[call-overload]
        self.log.append(("writeto_mem", address, memaddr, bytes(buf), addrsize))  # type: ignore[call-overload]


# ports/rp2/machine_spi.c's own `dma_min_size_threshold`: a transfer shorter than this never
# touches DMA, so it can never hit the RX-overrun check MicroPython 1.29 added there.
_SPI_DMA_MIN_SIZE = 32


class SPI:
    # Real RP2040 SPI error behavior (confirmed against extmod/machine_spi.c and ports/rp2/
    # machine_spi.c at v1.29.0, not guessed): SPI has no ACK/NAK concept, so write() genuinely
    # cannot raise. A *reading* transfer of 32+ bytes takes the DMA path, where MicroPython 1.29
    # added an RX-overrun check that raises OSError(EIO) - modeled by rx_overrun/inject_fault() below,
    # this fake's counterpart to I2C's nak_addresses/busy. write_readinto() also raises ValueError
    # on mismatched lengths - see its own comment. Full analysis: SPECIFICATION.md Part F.5.
    #
    # No registers/addressing (SPI has none) - a test primes what readinto()/write_readinto()
    # "receive" from the simulated downstream device via read_queue, a FIFO of byte strings.
    MSB = 0
    LSB = 1

    def __init__(
        self,
        id: int,
        *,
        sck: Pin,
        mosi: Pin,
        miso: Pin,
        baudrate: int = 1000000,
        polarity: int = 0,
        phase: int = 0,
        bits: int = 8,
        firstbit: int = 0,
    ) -> None:
        self.id = id
        self.sck = sck
        self.mosi = mosi
        self.miso = miso
        self.baudrate = baudrate
        self.polarity = polarity
        self.phase = phase
        self.bits = bits
        self.firstbit = firstbit
        self.deinit_called = False
        self.deinit_count = 0
        self.log: list[tuple[Any, ...]] = []
        self.read_queue: list[bytes] = []
        self.rx_overrun = False  # convenience: EIO on every DMA-path read, like I2C's `busy`
        self.rx_overrun_remaining = 0  # counted counterpart: N transient overruns, then the bus recovers
        self._faults: dict[str, list[Exception]] = {}  # op name -> FIFO queue, one exception per matching call

    def init(
        self,
        baudrate: int = -1,
        *,
        polarity: int = -1,
        phase: int = -1,
        bits: int = -1,
        firstbit: int = -1,
    ) -> None:
        # Real rp2 SPI.init(): -1/omitted args leave the current setting untouched (confirmed
        # against ports/rp2/machine_spi.c's allowed_args table - no "pins" kwarg accepted here,
        # only baudrate/polarity/phase/bits/firstbit).
        if firstbit == self.LSB:
            # Real rp2 hardware SPI only implements MSB-first (confirmed: machine_spi_init()'s
            # own `if (self->firstbit == SPI_LSB_FIRST) mp_raise_NotImplementedError(...)`).
            raise NotImplementedError("LSB")
        if baudrate != -1:
            self.baudrate = baudrate
        if polarity != -1:
            self.polarity = polarity
        if phase != -1:
            self.phase = phase
        if bits != -1:
            self.bits = bits
        if firstbit != -1:
            self.firstbit = firstbit
        self.log.append(("init", baudrate, polarity, phase, bits, firstbit))

    def inject_fault(self, op: str, exc: Exception, times: int = 1) -> None:
        # Same shape as I2C.inject_fault() above: queues `exc` for the next `times` calls to the
        # named op (readinto or write_readinto). write() is deliberately not injectable - the real
        # write-only path has no failure mode to model.
        self._faults.setdefault(op, []).extend([exc] * times)

    def _maybe_raise(self, op: str, nbytes: int) -> None:
        # DMA_MIN_SIZE_THRESHOLD is 32 in ports/rp2/machine_spi.c - a shorter transfer uses the
        # blocking software path, which has no overrun check and so cannot raise. Both knobs are
        # gated on that, so a 1-byte status-register read stays immune however they are set;
        # inject_fault()'s queue below is deliberately not, so a test can still target any call.
        if nbytes >= _SPI_DMA_MIN_SIZE:
            if self.rx_overrun:
                raise OSError(errno.EIO, "SPI RX overrun")
            if self.rx_overrun_remaining > 0:
                self.rx_overrun_remaining -= 1
                raise OSError(errno.EIO, "SPI RX overrun")
        queue = self._faults.get(op)
        if queue:
            raise queue.pop(0)

    def deinit(self) -> None:
        # Real rp2 machine.SPI.deinit() leaves the protocol's .deinit slot NULL: a silent no-op
        # that neither stops the peripheral nor releases the pins (SPECIFICATION.md Part F.5).
        # This fake therefore deliberately leaves every bus operation working afterwards, exactly
        # like real hardware; the counters only record that asy_spi_driver.py forwarded the call.
        self.deinit_called = True
        self.deinit_count += 1
        self.log.append(("deinit",))

    def _next_read_bytes(self, nbytes: int) -> bytes:
        data = self.read_queue.pop(0) if self.read_queue else b""
        return (data + bytes(nbytes))[:nbytes]  # always exactly nbytes, zero-padded/truncated like real hw

    def write(self, buf: object) -> None:
        self.log.append(("write", bytes(buf)))  # type: ignore[call-overload]

    def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        self._maybe_raise("readinto", len(buf))
        data = self._next_read_bytes(len(buf))
        buf[:] = data
        self.log.append(("readinto", len(buf), write_value))

    def write_readinto(self, buffer_out: object, buffer_in: bytearray | memoryview) -> None:
        # Real machine.SPI.write_readinto() (mp_machine_spi_write_readinto(), shared by hardware
        # and soft SPI): raises ValueError before any transfer if the two buffers' lengths differ.
        if len(buffer_out) != len(buffer_in):  # type: ignore[arg-type]
            raise ValueError("buffers must be the same length")
        self._maybe_raise("write_readinto", len(buffer_in))
        data = self._next_read_bytes(len(buffer_in))
        buffer_in[:] = data
        self.log.append(("write_readinto", bytes(buffer_out)))  # type: ignore[call-overload]


class UART(io.IOBase):
    # UART is a different shape from I2C/SPI above: it's the first fake here a driver actually
    # registers with real select.poll() (asy_uart_driver.py's ready()), not just calls methods on
    # directly. Confirmed against py/stream.h/extmod/modselect.c: select.poll().register() requires
    # the object's C-level *type* to carry MicroPython's stream protocol slot - a plain `class Foo:`
    # can't satisfy this, register() raises OSError immediately otherwise. io.IOBase is the
    # documented builtin base that carries this slot, dispatching its C-level ioctl callback back
    # into a Python-level ioctl(self, req, arg) override - so UART subclasses it instead of a plain
    # class. req == 3 is MP_STREAM_POLL; the expected return is the subset of arg's requested bits
    # (select.POLLIN/POLLOUT) that are currently ready - not a bool. Real UART read/readinto/
    # readline return None on no data available (MP_EAGAIN, not a raised exception, confirmed via
    # ports/rp2/machine_uart.c and py/stream.c); this fake matches that. write() is the mirror-image
    # TX case - real mp_machine_uart_write() can return fewer bytes than given (a genuine short
    # write) or None (if its per-byte timeout hits before writing anything) - see write()'s own
    # comment for how this fake models both via write_limit.
    #
    # rx_queue is a test-fed FIFO of "received" bytes; writable gates POLLOUT readiness so a test
    # can simulate a stalled/full TX path. Beyond __init__'s own real-hardware parameter validation
    # and write()'s own write_limit, there's no further fault injection - unlike I2C, real UART
    # read/readinto/readline can't raise or short-transfer, so there's nothing to inject there.
    _MP_STREAM_POLL = 3  # py/stream.h
    _MIN_BUFFER_SIZE = 32
    _MAX_BUFFER_SIZE = 32766
    _UART_INVERT_MASK = 3  # UART_INVERT_TX (1) | UART_INVERT_RX (2)

    def __init__(
        self,
        id: int,
        *,
        tx: Pin,
        rx: Pin,
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
        # Real mp_machine_uart_make_new()/init_helper() validation (confirmed against
        # ports/rp2/machine_uart.c, v1.29.0 - real numeric constants, not guessed), in the same
        # order the real source checks it (id, then invert, then rxbuf, then txbuf - matters for
        # which exception surfaces first when more than one field is invalid at once). A value below
        # MIN_BUFFER_SIZE (32) silently clamps up instead of raising - not modeled here since it
        # doesn't affect the raise/no-raise contract this fake needs. baudrate/bits/stop have no
        # raising validation in real source either - a non-positive value is silently ignored
        # (keeps the previous/hardware default) rather than rejected - so this fake doesn't validate
        # them either. **Deliberately not modeled**: real hardware also validates that tx/rx are
        # GPIO pins actually muxable to the *chosen* UART peripheral's TX/RX role - that table lives
        # in the RP2040 silicon datasheet, which isn't in this repo's datasheets/ folder (only the
        # Pico W *board* datasheet is); the mapping was found via public web search, not the
        # authoritative datasheet PDF, so it isn't encoded here as a raise condition - flagged per
        # CLAUDE.md rather than silently assumed. The existing generic Pin(id) range check
        # (0 <= id <= 28) still applies before a pin ever reaches UART(), since asy_uart_driver.py's
        # own init() always constructs Pin(tx_pin)/Pin(rx_pin) first.
        if id not in (0, 1):
            raise ValueError(f"UART({id}) doesn't exist")
        if invert & ~self._UART_INVERT_MASK:
            raise ValueError("bad inversion mask")
        if rxbuf > self._MAX_BUFFER_SIZE:
            raise ValueError("rxbuf too large")
        if txbuf > self._MAX_BUFFER_SIZE:
            raise ValueError("txbuf too large")
        self.id = id
        self.tx = tx
        self.rx = rx
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop = stop
        self.rxbuf = rxbuf
        self.txbuf = txbuf
        self.timeout = timeout
        self.timeout_char = timeout_char
        self.invert = invert
        self.deinit_called = False
        self.deinit_count = 0
        self.log: list[tuple[Any, ...]] = []
        self.rx_queue = bytearray()
        self.writable = True
        self.write_limit: int | None = None  # test-only: caps bytes accepted per write() call - see write()
        self._link: "UARTLink | None" = None  # set by UARTLink() - see its own docstring

    def feed_rx(self, data: bytes) -> None:  # test helper: queue bytes as if received over the wire
        self.rx_queue += data

    def ioctl(self, req: int, arg: int) -> int:
        if req != self._MP_STREAM_POLL:
            return 0
        ready = 0
        if (arg & select.POLLIN) and self.rx_queue:
            ready |= select.POLLIN
        if (arg & select.POLLOUT) and self.writable:
            ready |= select.POLLOUT
        return ready

    def deinit(self) -> None:
        self.deinit_called = True
        self.deinit_count += 1
        self.log.append(("deinit",))

    def read(self, nbytes: int | None = None) -> bytes | None:
        n = len(self.rx_queue) if nbytes is None else min(nbytes, len(self.rx_queue))
        if n == 0:  # real UART: None on no data available, matches MP_EAGAIN (see module docstring)
            return None
        data = bytes(self.rx_queue[:n])
        self.rx_queue = self.rx_queue[n:]  # MicroPython bytearray has no slice-delete, unlike CPython
        self.log.append(("read", n))
        return data

    def readinto(self, buf: bytearray | memoryview, nbytes: int | None = None) -> int | None:
        n = len(buf) if nbytes is None else min(nbytes, len(buf))
        n = min(n, len(self.rx_queue))
        if n == 0:
            return None
        buf[:n] = self.rx_queue[:n]
        self.rx_queue = self.rx_queue[n:]  # MicroPython bytearray has no slice-delete, unlike CPython
        self.log.append(("readinto", n))
        return n

    def readline(self) -> bytes | None:
        if not self.rx_queue:
            return None
        idx = self.rx_queue.find(b"\n")
        end = len(self.rx_queue) if idx == -1 else idx + 1
        data = bytes(self.rx_queue[:end])
        self.rx_queue = self.rx_queue[end:]  # MicroPython bytearray has no slice-delete, unlike CPython
        self.log.append(("readline", len(data)))
        return data

    def write(self, buf: object) -> int | None:
        # Real rp2 uart.write() can accept fewer bytes than given (its own internal per-byte
        # timeout hit after some progress - returns that count) or none at all before that timeout
        # (returns None, matching MP_EAGAIN) - confirmed against ports/rp2/machine_uart.c's own
        # internal write loop, not guessed. write_limit (None by default = accept everything, the
        # normal case) lets a test model either: 0 simulates a total send failure, and a positive
        # count less than len(buf) simulates a genuine short write a caller must retry.
        data = bytes(buf)  # type: ignore[call-overload]
        if self.write_limit is not None:
            data = data[: self.write_limit]
            if not data:
                return None
        self.log.append(("write", data))
        if self._link is not None:
            self._link.transmit(self, data)  # the far side's rx_queue, via this direction's knobs
        return len(data)


class _LinkDirection:
    # One direction of a UARTLink: the fault knobs plus the counters and wire log that make each
    # knob's effect assertable (A3.1 - every knob is an explicit schedule, never unseeded
    # randomness). Offsets in drop_indices/corrupt_indices are stream offsets within this
    # direction, counted over every byte offered to it, not per write() call.
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity  # far-side FIFO bound; overflow drops the newest bytes
        self.silent = False  # one-sided silence
        self.drop_indices: "set[int]" = set()
        self.corrupt_indices: "dict[int, int]" = {}  # stream offset -> xor mask, length-preserving
        self.truncate_after: int | None = None  # cut this direction's stream after N offered bytes
        self.noise_before_next = bytearray()  # injected once, ahead of the next delivery
        self.delay = False  # hold delivered bytes until UARTLink.release_delayed()
        self.duplicate_next = 0  # repeat this many of the next delivered bytes
        self.offered = 0
        self.delivered = 0
        self.dropped_overrun = 0
        self.pending = bytearray()  # held by delay
        self.wire_log = bytearray()  # every byte that actually reached the destination FIFO

    def shape(self, data: bytes) -> bytearray:
        # Applies the per-byte knobs in a fixed order - truncation bounds the stream, dropping
        # removes bytes, corruption only rewrites them (A3.4: separate, composable, attributable).
        out = bytearray()
        for byte in data:
            offset = self.offered
            self.offered += 1
            if self.silent:
                continue
            if self.truncate_after is not None and offset >= self.truncate_after:
                continue
            if offset in self.drop_indices:
                continue
            out.append(byte ^ self.corrupt_indices.get(offset, 0))
        return out


class UARTLink:
    # Byte-level crossover between two UART fakes - one independent FIFO per direction, each with
    # its own fault knobs (A1/A3). The fakes keep no concept of a frame: a write is appended to the
    # far side's rx_queue and reads split wherever the reader asks. Never registers anything with a
    # real select.poll() - use LinkPoller below (A1.2).
    def __init__(self, uart_a: "UART", uart_b: "UART", capacity_a_to_b: int | None = None, capacity_b_to_a: int | None = None) -> None:
        if uart_a._link is not None or uart_b._link is not None:
            raise ValueError("UART already attached to a link")
        if uart_a is uart_b:
            raise ValueError("a link needs two distinct endpoints")
        self.endpoints = (uart_a, uart_b)
        # Default each direction's bound to the *destination's* own rxbuf: that is what really
        # drops a frame's tail on hardware, which is the failure C2.9/C2.10 exist for.
        self.a_to_b = _LinkDirection(uart_b.rxbuf if capacity_a_to_b is None else capacity_a_to_b)
        self.b_to_a = _LinkDirection(uart_a.rxbuf if capacity_b_to_a is None else capacity_b_to_a)
        uart_a._link = self
        uart_b._link = self

    def _index(self, uart: "UART") -> int:
        return 0 if uart is self.endpoints[0] else 1

    def direction_from(self, uart: "UART") -> "_LinkDirection":
        # Raises rather than returning None for a foreign endpoint, so every caller can use the
        # result directly - the same "a test fake validates its own inputs" stance Pin() takes.
        if uart not in self.endpoints:
            raise ValueError("UART is not an endpoint of this link")
        return self.a_to_b if self._index(uart) == 0 else self.b_to_a

    def direction_to(self, uart: "UART") -> "_LinkDirection":
        if uart not in self.endpoints:
            raise ValueError("UART is not an endpoint of this link")
        return self.b_to_a if self._index(uart) == 0 else self.a_to_b

    def _deposit(self, direction: "_LinkDirection", dest: "UART", data: bytearray) -> None:
        room = direction.capacity - len(dest.rx_queue)
        if room < len(data):
            direction.dropped_overrun += len(data) - max(room, 0)
            data = data[: max(room, 0)]
        if not data:
            return
        dest.rx_queue += data
        direction.wire_log += data
        direction.delivered += len(data)

    def transmit(self, src: "UART", data: bytes) -> None:
        direction = self.direction_from(src)
        dest = self.endpoints[1 - self._index(src)]
        shaped = direction.shape(data)
        if direction.duplicate_next > 0 and shaped:
            n = min(direction.duplicate_next, len(shaped))
            shaped += shaped[:n]
            direction.duplicate_next -= n
        if direction.noise_before_next and shaped:
            shaped = direction.noise_before_next + shaped
            direction.noise_before_next = bytearray()
        if direction.delay:
            direction.pending += shaped
            return
        self._deposit(direction, dest, shaped)

    def settle(self) -> None:
        # Fidelity seam for the shared contract (tests/_uart_link_contract.py): this model
        # delivers synchronously, so there is nothing to wait for. The twin's own link overrides
        # it with a real wire-time wait.
        return

    def release_delayed(self) -> int:
        # Flushes both directions' held bytes and reports how many were released - the
        # deterministic stand-in for "the wire got around to it" (A3.1).
        released = 0
        for index, direction in ((0, self.a_to_b), (1, self.b_to_a)):
            if not direction.pending:
                continue
            data = direction.pending
            direction.pending = bytearray()
            released += len(data)
            self._deposit(direction, self.endpoints[1 - index], data)
        return released


class LinkPoller:
    # Bounded select.poll() stand-in for one UART fake, re-querying its ioctl() on every call
    # (A2.2). Installed by reassigning asy_uart_driver.UART.poller after construction, keeping
    # src/ free of a testability seam. Never wraps a real select.poll(): the Unix port does not
    # re-evaluate a Python object's ioctl() after register(), which is CLAUDE.md's known CI hang.
    def __init__(self, uart: "UART", not_ready_calls: int = 0) -> None:
        self._uart = uart
        self._not_ready = not_ready_calls

    def force_not_ready(self, calls: int) -> None:  # A2.3: makes the timeout paths reachable
        self._not_ready = calls

    def ipoll(self, _timeout_ms: int = 0) -> "list[tuple[None, int]]":
        if self._not_ready > 0:
            self._not_ready -= 1
            return []
        event = self._uart.ioctl(UART._MP_STREAM_POLL, select.POLLIN | select.POLLOUT)
        return [(None, event)] if event else []

    def register(self, obj: object, mask: int = 0) -> None:
        pass

    def unregister(self, obj: object) -> None:
        pass


class Timer:
    ONE_SHOT = 0
    PERIODIC = 1

    # Class-level registry, not per-instance: records every real Timer() *construction*, so a test
    # can assert none happened (e.g. system_service.py's _timer_sequencer() reusing one preallocated
    # Timer via .init() instead - SPECIFICATION.md Part F.1). Tests must clear this between test
    # functions (all_timers.clear()) since it otherwise persists across the whole process lifetime.
    all_timers: "ClassVar[list[Timer]]" = []

    # Test-only fault injection, off by default: real rp2 Timer.init() calls
    # alarm_pool_add_alarm_in_us() and raises OSError(ENOMEM) if the alarm pool is exhausted
    # (confirmed directly against ports/rp2/machine_timer.c, v1.29.0) - a bare Timer() with no
    # args never hits this path at all (real machine_timer_make_new() only calls the init helper
    # when args/kwargs are actually given), matching the `if kwargs` gate below. Tests must reset
    # this to False afterward - it's a shared class attribute, not per-instance.
    raise_on_arm = False
    # Which exception class init() raises when raise_on_arm is True - defaults to the real
    # alarm-pool-exhaustion OSError above. Every call site in src/ guards Timer.init() with
    # `except (OSError, MemoryError)` (a real alarm allocation can fail either way on real
    # hardware); override this to MemoryError before setting raise_on_arm = True to prove that
    # sibling arm is handled too, then reset both back to their defaults afterward - shared class
    # attribute, not per-instance, same as raise_on_arm itself.
    raise_on_arm_exc: "type[BaseException]" = OSError

    def __init__(self, id: int = -1, **kwargs: "Any") -> None:
        self.id = id
        self.period = -1
        self.mode = self.PERIODIC
        self.callback: Callable[[Timer], None] | None = None
        self.deinit_called = False
        if kwargs:
            self.init(**kwargs)  # may raise OSError - propagates before this instance is registered
        Timer.all_timers.append(self)

    def init(self, *, period: int = -1, mode: int = PERIODIC, callback: "Callable[[Timer], None] | None" = None) -> None:
        if Timer.raise_on_arm:
            if Timer.raise_on_arm_exc is OSError:
                raise OSError(errno.ENOMEM, "alarm pool exhausted")
            raise Timer.raise_on_arm_exc("simulated allocation failure")
        self.period = period
        self.mode = mode
        self.callback = callback
        self.deinit_called = False

    def deinit(self) -> None:
        self.callback = None
        self.deinit_called = True

    def trigger(self) -> None:
        # No real-hardware equivalent - lets test code fire a callback deterministically instead of
        # waiting on this fake's `period` (which is never actually scheduled against real time).
        if self.callback is not None:
            self.callback(self)


class RTC:
    # Minimal fake for asy_ntp_client.py's RTC().datetime((...)) call: stores/returns whatever
    # 8-tuple it's given, no validation - confirmed directly against the real
    # ports/rp2/machine_rtc.c (v1.29.0) that the real setter reads all 8 elements but only ever
    # uses indices 0/1/2/4/5/6 (year/month/day/hour/minute/second); index 3 (weekday) is extracted
    # and never used/validated/written anywhere - so there's no real weekday-validity behavior for
    # this fake to model in the first place (see BACKLOG.md for the fuller history: an earlier,
    # web-search-only pass on this file mistakenly flagged the weekday value as possibly
    # significant/validated upstream, since corrected against the actual source).
    # State is class-level, not per-instance: real RTC is one physical peripheral - every RTC()
    # call (the real class takes no useful constructor args on rp2) refers to the same hardware,
    # so a test must be able to construct a fresh RTC() after the fact and still read back what an
    # earlier RTC() instance set, exactly like the real singleton would.
    raise_exc: "Exception | None" = None  # test-only fault injection, shared class attribute like Timer.raise_on_arm
    _shared_datetime: "tuple[int, ...]" = (2000, 1, 1, 0, 0, 0, 0, 0)

    def __init__(self, id: int = 0) -> None:
        self.id = id

    def datetime(self, dt: "tuple[int, ...] | None" = None) -> "tuple[int, ...] | None":
        if RTC.raise_exc is not None:
            raise RTC.raise_exc
        if dt is None:
            return RTC._shared_datetime
        RTC._shared_datetime = tuple(dt)
        return None


class WDT:
    def __init__(self, id: int = 0, timeout: int = 5000) -> None:
        self.id = id
        self.timeout = timeout
        self.feed_count = 0

    def feed(self) -> None:
        self.feed_count += 1


# Real machine.reset()/machine.bootloader() reset the MCU and never return at all - this fake just
# records the call so a test can assert a reboot was triggered, instead of ending the test process.
reset_count = 0
bootloader_count = 0


def reset() -> None:
    global reset_count
    reset_count += 1


def bootloader() -> None:
    global bootloader_count
    bootloader_count += 1
