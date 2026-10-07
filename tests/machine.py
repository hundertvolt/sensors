"""Test-only fake `machine` module: mocks only the raw I2C/SPI bus-transaction level (per SPECIFICATION.md Part E.4's mocking boundary) so the real drivers' own logic runs for real against it. Only implements what src/'s own imports need.
`Timer` is also why this file has to exist beyond I2C/SPI mocking: it's what makes `from machine import Timer` resolve under mypy's `src tests` scope (see BACKLOG.md's "Timer mypy resolution" finding)."""

import errno
import io
import select
from array import array

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Any, ClassVar


class Pin:
    IN = 0
    OUT = 1
    OPEN_DRAIN = 2  # ports/rp2/machine_pin.h:34-37 (v1.29.0), as IN/OUT/ALT
    ALT = 3
    ALT_I2C = 3  # GPIO_FUNC_I2C (pico-sdk io_bank0.h; machine_pin.c:513)
    _ALT_SIO = 5  # GPIO_FUNC_SIO, rp2's alt default (machine_pin.c:247)
    # Real rp2 values (confirmed against ports/rp2/machine_pin.c: IRQ_RISING maps to the pico-sdk's
    # GPIO_IRQ_EDGE_RISE=0x08, IRQ_FALLING to GPIO_IRQ_EDGE_FALL=0x04) - asy_scd30_driver.py only
    # ever passes these back opaquely to irq(), but matching the real bit values costs nothing.
    IRQ_FALLING = 0x04
    IRQ_RISING = 0x08
    # Real rp2 values (ports/rp2/machine_pin.c at v1.29.0: GPIO_PULL_UP 1, GPIO_PULL_DOWN 2).
    # asy_isl29125_driver.py is the first driver to need one - its INT line is open-drain and needs
    # a pull-up; SCD30's RDY is push-pull, which is why nothing needed these before.
    PULL_UP = 1
    PULL_DOWN = 2

    # Per GPIO id, shared by every Pin object on it: the level the outside world puts on the line
    # (test-only, default 1: the bus pull-ups) and every level the code drove onto it.
    _external: "ClassVar[dict[int, int | Callable[[int, _CallLog], int]]]" = {}
    _value_logs: "ClassVar[dict[int, _CallLog]]" = {}

    def __init__(self, id: int, mode: int = -1, pull: int = -1, *, value: object = None, alt: int = _ALT_SIO) -> None:
        # Real rp2 Pin() raises for an invalid id: TypeError for a non-int, ValueError outside
        # GPIO0-28. Modelled because several drivers' docstrings claim a "one-time setup, allowed to
        # raise" contract that nothing exercised.
        if not isinstance(id, int):
            raise TypeError("Pin id must be an int")
        if not (0 <= id <= 28):
            raise ValueError("invalid pin")
        self.id = id
        self.mode = -1
        self.pull = -1
        self.alt = self._ALT_SIO
        self._value = 0
        self._irq_handler: Callable[[Pin], None] | None = None
        self._irq_trigger = self.IRQ_FALLING | self.IRQ_RISING
        self._irq_hard = False
        self.init(mode, pull, value=value, alt=alt)

    def _drive(self, level: int) -> None:
        self._value = level
        Pin.value_log(self.id).append(level)

    def _line(self) -> int:
        level = Pin._external.get(self.id, 1)
        if callable(level):
            level = level(self.id, Pin.value_log(self.id))
        return 1 if level else 0

    @classmethod
    def set_external_level(cls, id: int, level: "int | Callable[[int, _CallLog], int]") -> None:
        # Test-only: what the outside world drives onto line `id`; a callable is asked on every read
        # with (id, the line's value log), so a test can script a slave releasing SDA after k clocks.
        cls._external[id] = level

    def init(self, mode: int = -1, pull: int = -1, *, value: object = None, alt: int = _ALT_SIO) -> None:
        # Real machine.Pin.init(): an omitted/-1 mode or pull leaves the setting untouched; value= sets
        # the level before the mode applies (machine_pin.c:264-287), and OPEN_DRAIN given no value is
        # released (mphalport.h:158-168). The latch is not checked against the mode, as on rp2.
        if value is not None:
            self._value = 1 if value else 0
        elif mode == self.OPEN_DRAIN:
            self._value = 1
        if mode != -1:
            self.mode = mode
        if mode == self.ALT:
            self.alt = alt
        if pull != -1:
            self.pull = pull

    def irq(
        self,
        handler: "Callable[[Pin], None] | None" = None,
        trigger: int = IRQ_FALLING | IRQ_RISING,
        *,
        hard: bool = False,
    ) -> "Pin":
        # Real rp2 Pin.irq() replaces the previous handler outright rather than stacking, fires on
        # every matching edge until called again, and returns the IRQ object (stood in for here by
        # the Pin, which nothing inspects). trigger_irq() simulates one edge, as Timer.trigger() does.
        self._irq_handler = handler
        self._irq_trigger = trigger
        self._irq_hard = hard
        return self

    def off(self) -> None:
        self._drive(0)

    def on(self) -> None:
        self._drive(1)

    @classmethod
    def reset_registry(cls) -> None:
        # Test-only: forget every planted level and value log, as a fresh board would have none.
        cls._external.clear()
        cls._value_logs.clear()

    def toggle(self) -> None:
        self._drive(0 if self._value else 1)

    def trigger_irq(self) -> None:
        # No real-hardware equivalent - fires the currently-registered handler once, standing in
        # for one real edge interrupt. No-op if irq() was never called or was disabled.
        if self._irq_handler is not None:
            self._irq_handler(self)

    def value(self, x: object = None) -> int | None:
        # Real rp2 Pin.value() reads the pad (gpio_get(), ports/rp2/machine_pin.c): an output reads what
        # it drives, an open-drain pin the wired-AND of its drive and the line. An input with no planted
        # level and no pull-up reads its own latch, the level a test sets through value(x).
        if x is not None:
            self._drive(1 if x else 0)
            return None
        if self.mode == self.OPEN_DRAIN:
            return self._line() if self._value else 0
        if self.mode == self.ALT:
            return self._line()
        if self.mode == self.IN and (self.pull == self.PULL_UP or self.id in Pin._external):
            return self._line()
        return self._value

    @classmethod
    def value_log(cls, id: int) -> "_CallLog":
        # Test-only: the last levels value()/on()/off()/toggle() drove onto line `id`, oldest first.
        log = cls._value_logs.get(id)
        if log is None:
            log = cls._value_logs[id] = _CallLog(_VALUE_LOG_MAXLEN)
        return log


_LOG_MAXLEN = 4096  # entries kept per fake call log; see _CallLog for why it is bounded at all
# A line's value log keeps far fewer: a chip-select toggles on every SPI transaction, and a longer log
# would itself be a growing allocation inside the boot whose heap placement tests measure.
_VALUE_LOG_MAXLEN = 64
_MEM32_LOG_MAXLEN = 64  # likewise for register accesses: a DMA reader reads UARTRSR at every fill-level read
_WIRE_LOG_MAXLEN = 4096  # bytes of a link direction's wire log kept; its `dropped` counts the rest
_RX_INFLIGHT_MAX = 4096  # bytes waiting on the wire to a UART with its interrupt off; more is an overrun


class _CallLog:
    # A record that grows to `maxlen` entries, then overwrites its oldest in place: fixed occupancy once
    # full, so a long run neither exhausts the heap nor frees half of it at once (a swing a heap test reads
    # as retention). Reads - len(), iteration, [i], slices, == - see the entries oldest first.
    def __init__(self, maxlen: int = _LOG_MAXLEN) -> None:
        self.maxlen = maxlen
        self.dropped = 0  # assertable: a test reading the whole log can tell it is not the whole log
        self._items: list[Any] = []
        self._head = 0  # once full: the slot holding the oldest entry

    def __contains__(self, entry: object) -> bool:
        return entry in self._items

    def __eq__(self, other: object) -> bool:
        return self._ordered() == other

    def __getitem__(self, index: "int | slice") -> "Any":
        if isinstance(index, slice):
            return self._ordered()[index]
        n = len(self._items)
        position = index + n if index < 0 else index
        if not 0 <= position < n:
            raise IndexError("log index out of range")
        return self._items[(self._head + position) % n]

    def __iter__(self) -> "Iterator[Any]":
        return iter(self._ordered())

    def __len__(self) -> int:
        return len(self._items)

    def _ordered(self) -> "list[Any]":
        return self._items[self._head :] + self._items[: self._head]

    def append(self, entry: object) -> None:
        if len(self._items) < self.maxlen:
            self._items.append(entry)
            return
        self._items[self._head] = entry
        self._head = (self._head + 1) % self.maxlen
        self.dropped += 1

    def clear(self) -> None:
        self._items = []
        self._head = 0

    def count(self, entry: object) -> int:
        return self._items.count(entry)


class _WireLog:
    # The bytes a link direction delivered, kept the way _CallLog keeps entries: up to `maxlen`, then
    # the oldest overwritten in place and counted in `dropped`; read oldest first (bytes(), [i], len()).
    def __init__(self, maxlen: int) -> None:
        self.maxlen = maxlen
        self.dropped = 0
        self._items = bytearray()
        self._head = 0

    def __eq__(self, other: object) -> bool:
        return self._ordered() == other

    def __getitem__(self, index: int) -> int:
        n = len(self._items)
        position = index + n if index < 0 else index
        if not 0 <= position < n:
            raise IndexError("wire log index out of range")
        return self._items[(self._head + position) % n]

    def __iter__(self) -> "Iterator[int]":
        return iter(self._ordered())

    def __len__(self) -> int:
        return len(self._items)

    def _ordered(self) -> bytearray:
        return self._items[self._head :] + self._items[: self._head]

    def append(self, byte: int) -> None:
        if len(self._items) < self.maxlen:
            self._items.append(byte)
            return
        self._items[self._head] = byte
        self._head = (self._head + 1) % self.maxlen
        self.dropped += 1

    def clear(self) -> None:
        self._items = bytearray()
        self._head = 0

    def extend(self, data: "bytes | bytearray") -> None:
        for byte in data:
            self.append(byte)


class I2C:
    # rp2's I2C raises only OSError(EIO) - a NAK, a general bus fault, or a lost arbitration, which
    # has no errno of its own here - or OSError(ETIMEDOUT) for bus-busy/clock-stretch. nak_addresses
    # and busy below model exactly those two.
    #
    # An id reset_id() registered is one static object, as rp2's machine.I2C(id) (machine_i2c.c:50-53,
    # 87): a re-construction re-initialises the controller and keeps the devices, faults and log. An id
    # never registered builds a fresh bus at every construction, so tests without a reset share nothing.
    _static: "ClassVar[dict[int, I2C | None]]" = {}
    raise_on_construct: "ClassVar[BaseException | None]" = None  # test-only: the next construction raises it, once
    _fresh: bool

    def __init__(self, id: int, *, scl: Pin, sda: Pin, freq: int = 400000, timeout: int = 50000) -> None:
        if self._fresh:
            self._fresh = False
            self.deinit_called = False
            self.deinit_count = 0
            self.log = _CallLog()
            self.registers: dict[tuple[int, int], bytearray] = {}  # a real round trip through register writes and reads
            self.read_queue: list[bytes] = []  # its raw-transaction counterpart: readfrom_into() has no register to key off
            self.read_queue_by_address: dict[int, list[bytes]] = {}  # opt-in per-address queue, checked
            # before the shared one above - needed once two raw-word-protocol devices, with no register to key
            # off, were driven concurrently on one bus (dev's i2c1 SCD30+SGP40). Empty by default.
            self.nak_addresses: set[int] = set()  # convenience: EIO (no ACK) on every op to this address
            self.busy = False  # convenience: ETIMEDOUT (bus/clock-stretch timeout) on every op, any address
            self._faults: dict[str, list[tuple[BaseException, int | None]]] = {}  # op -> FIFO of (exception, match)
            self._addrsizes: dict[int, int] = {}  # register_device(): address -> register-address bits
            self._pointers: dict[int, int] = {}  # per register device: the register the next read starts at
            self._short_acks: dict[int, int] = {}  # short_ack(): address -> the next write's ACK count
        self.id = id
        self.scl = scl
        self.sda = sda
        self.freq = freq
        self.timeout = timeout
        self.log.append(("init", freq, timeout))

    def __new__(cls, id: int, *_args: object, **_kwargs: object) -> "I2C":
        pending = cls.raise_on_construct
        if pending is not None:
            cls.raise_on_construct = None
            raise pending
        bus = cls._static.get(id)
        if bus is None:
            bus = super().__new__(cls)
            bus._fresh = True
            if id in cls._static:
                cls._static[id] = bus
        return bus

    def _addr_bytes(self, address: int) -> int:
        # Register-address bytes of a register device, 0 for a raw-command one.
        size = self._addrsizes.get(address)
        if size is not None:
            return size // 8
        for addr, _reg in self.registers:
            if addr == address:
                return 1
        return 0

    def _maybe_raise(self, op: str, address: int, key: int | None = None) -> None:
        if self.busy:
            raise OSError(errno.ETIMEDOUT, "bus busy / clock stretch timeout")
        if address in self.nak_addresses:
            raise OSError(errno.EIO, "no ACK from device")
        queue = self._faults.get(op)
        if queue:
            for i, (exc, match) in enumerate(queue):
                if match is None or match == key:
                    del queue[i]
                    raise exc

    def _next_read_bytes(self, address: int, nbytes: int) -> bytes:
        per_address = self.read_queue_by_address.get(address)
        data = per_address.pop(0) if per_address else (self.read_queue.pop(0) if self.read_queue else b"")
        return (data + bytes(nbytes))[:nbytes]  # always exactly nbytes, zero-padded/truncated like real hw

    def deinit(self) -> None:
        # Real rp2 I2C.deinit() exists only from 1.29 and is a silent no-op even there - the port
        # leaves the .deinit slot NULL (SPECIFICATION.md Part F.5). So every bus operation keeps
        # working afterwards here too; the counters only record that the call was forwarded.
        self.deinit_called = True
        self.deinit_count += 1
        self.log.append(("deinit",))

    def inject_fault(self, op: str, exc: BaseException, times: int = 1, *, match: int | None = None) -> None:
        # Queues `exc` to be raised on the next `times` calls to the named op (readfrom_into, writeto,
        # readfrom_mem, writeto_mem or scan) whose key equals `match` (None: any call). The key is the
        # register pointer of a register device (for a read, the one the last address write set), else None.
        self._faults.setdefault(op, []).extend([(exc, match)] * times)

    def readfrom_into(self, address: int, buf: object, stop: bool = True) -> None:
        nbytes = len(buf)  # type: ignore[arg-type]
        if self._addr_bytes(address):
            pointer = self._pointers.get(address, 0)
            self._maybe_raise("readfrom_into", address, pointer)
            data = (bytes(self.registers.get((address, pointer), b"")) + bytes(nbytes))[:nbytes]
        else:
            self._maybe_raise("readfrom_into", address)
            data = self._next_read_bytes(address, nbytes)
        buf[:] = data  # type: ignore[index]
        self.log.append(("readfrom_into", address, data, stop))

    def readfrom_mem(self, address: int, memaddr: int, nbytes: int, *, addrsize: int = 8) -> bytes:
        self._maybe_raise("readfrom_mem", address, memaddr)
        stored = bytes(self.registers.get((address, memaddr), bytearray(nbytes)))
        data = (stored + bytes(nbytes))[:nbytes]  # always exactly nbytes, zero-padded/truncated like real hw
        self.log.append(("readfrom_mem", address, memaddr, nbytes, addrsize))
        return data

    def readfrom_mem_into(self, address: int, memaddr: int, buf: object, *, addrsize: int = 8) -> None:
        # Delegates, so the fault hook, the log entry and the stored-register semantics stay one
        # implementation - a test faulting "readfrom_mem" keeps working whichever form the driver calls.
        buf[:] = self.readfrom_mem(address, memaddr, len(buf), addrsize=addrsize)  # type: ignore[index,arg-type]

    def register_device(self, address: int, addrsize: int = 8) -> None:
        # Test-only: `address` is register-addressed - writeto() of address bytes plus payload is a register
        # write, an address-only write sets the pointer readfrom_into() reads from. An address that already
        # holds a `registers` entry is one too (8-bit); every other address keeps the raw read queue.
        self._addrsizes[address] = addrsize

    @classmethod
    def reset_id(cls, id: int) -> None:
        # Test-only: a power-cycled controller and devices - the next I2C(id) builds a fresh bus, which
        # every later construction of that id returns until the next reset.
        cls._static[id] = None

    @classmethod
    def reset_registry(cls) -> None:
        cls._static.clear()

    def scan(self) -> list[int]:
        self.log.append(("scan",))
        self._maybe_raise("scan", -1)
        return sorted({addr for addr, _ in self.registers} - self.nak_addresses)

    def short_ack(self, address: int, n: int) -> None:
        # Test-only: the next write to `address` reports only n bytes ACKed, as rp2's writeto() does for a
        # data byte the device NACKs (pico-sdk i2c.c:229-231), and the device keeps none of it.
        self._short_acks[address] = n

    def writeto(self, address: int, buf: object, stop: bool = True) -> int:
        data = bytes(buf)  # type: ignore[call-overload]
        n = self._addr_bytes(address)
        register = int.from_bytes(data[:n], "big") if n and len(data) >= n else None
        self._maybe_raise("writeto", address, register)
        self.log.append(("writeto", address, data, stop))
        acked = self._short_acks.pop(address, len(data))
        if acked < len(data):
            return acked
        if register is not None:
            self._pointers[address] = register
            if len(data) > n:
                self.registers[(address, register)] = bytearray(data[n:])
        return len(data)

    def writeto_mem(self, address: int, memaddr: int, buf: object, *, addrsize: int = 8) -> None:
        self._maybe_raise("writeto_mem", address, memaddr)
        self.registers[(address, memaddr)] = bytearray(buf)  # type: ignore[call-overload]
        self.log.append(("writeto_mem", address, memaddr, bytes(buf), addrsize))  # type: ignore[call-overload]


# ports/rp2/machine_spi.c's own `dma_min_size_threshold`: a transfer shorter than this never
# touches DMA, so it can never hit the RX-overrun check MicroPython 1.29 added there.
_SPI_DMA_MIN_SIZE = 32


class SPI:
    # SPI has no ACK/NAK, so write() cannot raise; a *reading* transfer of 32+ bytes takes the DMA
    # path, whose 1.29 RX-overrun check raises OSError(EIO) - modelled by rx_overrun/inject_fault()
    # (SPECIFICATION.md Part F.5). No addressing either: read_queue primes what a transfer receives.
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
        self.log = _CallLog()
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
        # DMA_MIN_SIZE_THRESHOLD is 32 in ports/rp2/machine_spi.c - a shorter transfer takes the blocking
        # software path, which has no overrun check and cannot raise. Both knobs are gated on that, so a
        # 1-byte read stays immune however they are set; inject_fault()'s queue deliberately is not.
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
        # Real rp2 machine.SPI.deinit() leaves the protocol's .deinit slot NULL: a silent no-op that neither
        # stops the peripheral nor releases the pins (Part F.5). This fake therefore leaves every bus
        # operation working afterwards; the counters only record that asy_spi_driver.py forwarded the call.
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


# Claimed rp2.DMA channels by number: tests/rp2.py registers here, so a UART can find the channel draining it.
_DMA_CHANNELS: "dict[int, Any]" = {}
_UART_BASES = (0x40034000, 0x40038000)  # UART0/UART1 register blocks; UARTDR at offset 0 (RP2040 datasheet 4.2.8)
_UARTRSR = 0x004  # read as UARTRSR, written as UARTECR (any write clears the four error bits)
_UARTIMSC = 0x038
_UARTDMACR = 0x048
_RSR_OE = 0x08  # datasheet Table 427: overrun; BE 0x04, PE 0x02, FE 0x01
_RSR_BE = 0x04
_IMSC_RX_IRQ = 0x50  # RXIM | RTIM (Table 435)
_IMSC_AT_INIT = 0x70  # TXIM | RXIM | RTIM: pico-sdk uart_set_irqs_enabled(), machine_uart.c:455
_DMACR_RXDMAE = 0x01
_DMACR_AT_INIT = 0x03  # pico-sdk uart_init() always enables both DREQs (uart.c:86-88)
_RX_FIFO_DEPTH = 32
_RX_DREQ = (21, 23)  # DREQ_UART0_RX, DREQ_UART1_RX (pico-sdk dreq.h)
_RX_UNPACED = float("inf")


class UART(io.IOBase):
    # The one fake a driver registers with a real select.poll(), which needs the C-level stream slot
    # only io.IOBase carries - a plain class makes register() raise. Reads answer None (MP_EAGAIN)
    # rather than raising, as rp2 does; write() is the TX mirror. Full analysis: Part F.5.
    #
    # Receive model: with RXIM/RTIM set (every construction and init()) the RX interrupt moves each byte
    # into rx_queue, machine.UART's own buffer, as delivered. With both cleared, bytes arrive at the line
    # rate on Timer.clock_ms and go to a DMA channel draining this UART, else to the 32-byte FIFO (OE).
    _MP_STREAM_POLL = 3  # py/stream.h
    _MIN_BUFFER_SIZE = 32
    _MAX_BUFFER_SIZE = 32766
    _UART_INVERT_MASK = 3  # UART_INVERT_TX (1) | UART_INVERT_RX (2)
    _live: "ClassVar[dict[int, UART]]" = {}  # the latest construction per id: what mem32 and the DMA reach
    # Bytes a read asked for that had not arrived. On real hardware each one costs a synchronous
    # timeout_char wait inside the C read, never yielding to asyncio (SPECIFICATION.md Part F.5.8);
    # these fakes serve what they hold and return, so the stall is counted here instead of taken.
    would_have_blocked_bytes = 0

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
        # Real make_new()/init_helper() validation against ports/rp2/machine_uart.c v1.29.0, in the
        # source's own order (id, invert, rxbuf, txbuf - which matters when several are invalid at
        # once). Not modeled, none of them raising: the MIN_BUFFER_SIZE clamp, baudrate/bits/stop, pins (A.6).
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
        self.log = _CallLog()
        self.rx_queue = bytearray()
        self.writable = True
        self.write_limit: int | None = None  # test-only: caps bytes accepted per write() call - see write()
        self._link: UARTLink | None = None  # set by UARTLink() - see its own docstring
        self.tx_pending_rounds = 0  # test-only: txdone() answers False this many calls first
        self.rx_api_calls = 0  # every any()/read()/readinto()/readline() and POLLIN poll: a DMA reader makes none
        self.rx_rate = 0.0  # test-only: arrival bytes/ms with the interrupt off; 0 is the line rate, inf unpaced
        self.rx_stall_ms = 0  # test-only: the next register read first lets this many ms of arrivals land
        self.rx_fifo_dropped = 0  # bytes lost to a full FIFO, each also setting OE
        self.rsr = 0
        self._inbound = bytearray()  # on the wire, not yet arrived
        self._fifo = bytearray()
        self._rx_clock = 0
        self._rx_credit = 0.0
        self._reset_block()
        UART._live[id] = self

    def _set_register(self, offset: int, value: int) -> None:
        self._update()
        if offset == _UARTRSR:
            self.rsr = 0
        elif offset == _UARTIMSC:
            self.imsc = value & 0x7FF
        elif offset == _UARTDMACR:
            self.dmacr = value & 0x07
        else:
            raise ValueError(f"UART register offset 0x{offset:03x} not modelled")
        self._update()

    def _arrive(self, data: "bytes | bytearray") -> int:
        # Bytes put on the wire towards this UART with its interrupt off: they land over time. Returns how
        # many the wire took; past _RX_INFLIGHT_MAX the rest are an overrun the caller counts.
        if not self._inbound:
            self._rx_clock = Timer.clock_ms
            self._rx_credit = 0.0
        taken = min(len(data), _RX_INFLIGHT_MAX - len(self._inbound))
        self._inbound += data[:taken]
        return taken

    def _channel(self) -> "Any":
        if not self.dmacr & _DMACR_RXDMAE:
            return None
        for channel in _DMA_CHANNELS.values():
            if channel._accept(_UART_BASES[self.id], _RX_DREQ[self.id]):
                return channel
        return None

    def _count_overask(self, asked: int) -> None:
        if asked > len(self.rx_queue):
            UART.would_have_blocked_bytes += asked - len(self.rx_queue)

    @classmethod
    def _for_data_register(cls, address: int) -> "UART | None":
        return cls._live.get(_UART_BASES.index(address)) if address in _UART_BASES else None

    def _register(self, offset: int) -> int:
        self._update()
        if offset == _UARTRSR:
            return self.rsr
        if offset == _UARTIMSC:
            return self.imsc
        if offset == _UARTDMACR:
            return self.dmacr
        raise ValueError(f"UART register offset 0x{offset:03x} not modelled")

    def _reset_block(self) -> None:
        # What uart_init() leaves: interrupts and both DREQs enabled, no errors, an empty FIFO.
        self.imsc = _IMSC_AT_INIT
        self.dmacr = _DMACR_AT_INIT
        self.rsr = 0
        self._fifo = bytearray()

    def _route(self, byte: int, *, is_break: bool = False) -> None:
        # One arrived byte: the interrupt takes it while unmasked and its buffer has room (it drops a break's
        # 0x00, machine_uart.c:163-176), else the DMA, else the FIFO.
        if self.imsc & _IMSC_RX_IRQ and len(self.rx_queue) < self.rxbuf:
            if not is_break:
                self.rx_queue.append(byte)
            return
        channel = None if self.imsc & _IMSC_RX_IRQ else self._channel()
        if channel is not None:
            channel._push(byte)
        elif len(self._fifo) < _RX_FIFO_DEPTH:
            self._fifo.append(byte)
        else:
            self.rsr |= _RSR_OE
            self.rx_fifo_dropped += 1

    def _update(self) -> None:
        # Lands the bytes whose arrival time has come on Timer.clock_ms, after whatever the FIFO holds.
        fifo, self._fifo = self._fifo, bytearray()
        for byte in fifo:
            self._route(byte)
        if not self._inbound:
            return
        now = Timer.clock_ms
        rate = self.rx_rate or self.baudrate / 10_000  # 8N1: ten bit times a byte
        if rate == _RX_UNPACED:
            n = len(self._inbound)
        else:
            elapsed = now - self._rx_clock + self.rx_stall_ms
            self._rx_credit += max(elapsed, 0) * rate
            n = min(int(self._rx_credit), len(self._inbound))
            self._rx_credit -= n
        self._rx_clock = now
        self.rx_stall_ms = 0
        arrived = self._inbound[:n]
        self._inbound = self._inbound[n:]  # MicroPython bytearray has no slice-delete, unlike CPython
        if not self._inbound:
            self._rx_credit = 0.0
        for byte in arrived:
            self._route(byte)

    def any(self) -> int:
        # Real machine.UART.any(): bytes already in the RX ring. asy_uart_driver clamps every
        # counted read to it, because the real peripheral would otherwise wait out timeout_char
        # per not-yet-arrived byte synchronously, without ever yielding to asyncio.
        self.rx_api_calls += 1
        self._update()  # rp2 drains the RX FIFO into its buffer first (machine_uart.c:505, :604)
        self._update()  # rp2 drains the RX FIFO into its buffer first (machine_uart.c:505, :604)
        return len(self.rx_queue)

    def deinit(self) -> None:
        # Real deinit() resets the UART block (uart_deinit()): every register back to its reset value.
        self.deinit_called = True
        self.deinit_count += 1
        self.log.append(("deinit",))
        self.imsc = 0
        self.dmacr = 0
        self.rsr = 0
        self._fifo = bytearray()

    def feed_rx(self, data: bytes) -> None:  # test helper: queue bytes as if received over the wire
        if self.imsc & _IMSC_RX_IRQ:
            self.rx_queue += data
        elif self._arrive(data) < len(data):
            raise ValueError("feed_rx() beyond the bytes the wire can hold")

    def init(self, **settings: "Any") -> None:
        # Real UART.init(): re-runs uart_init() on the given settings, which re-enables the RX interrupts
        # and both DREQs (machine_uart.c:399-455; the ring buffers are kept).
        for name, value in settings.items():
            if not hasattr(self, name) or name.startswith("_"):
                raise TypeError(f"unexpected keyword argument '{name}'")
            setattr(self, name, value)
        self._reset_block()

    def ioctl(self, req: int, arg: int) -> int:
        if req != self._MP_STREAM_POLL:
            return 0
        if arg & select.POLLIN:
            self.rx_api_calls += 1
        self._update()
        ready = 0
        if (arg & select.POLLIN) and self.rx_queue:
            ready |= select.POLLIN
        if (arg & select.POLLOUT) and self.writable:
            ready |= select.POLLOUT
        return ready

    def plant_rx_error(self, bits: int) -> None:
        # Test-only: sets UARTRSR bits (OE 0x08, BE 0x04, FE 0x01); a break also receives one 0x00
        # character (RP2040 datasheet 4.2.8, Table 426).
        self._update()
        self.rsr |= bits & 0x0F
        if bits & _RSR_BE:
            self._route(0, is_break=True)

    def read(self, nbytes: int | None = None) -> bytes | None:
        self.rx_api_calls += 1
        self._update()  # rp2 drains the RX FIFO into its buffer first (machine_uart.c:505, :604)
        self._count_overask(len(self.rx_queue) if nbytes is None else nbytes)
        n = len(self.rx_queue) if nbytes is None else min(nbytes, len(self.rx_queue))
        if n == 0:  # real UART: None on no data available, matches MP_EAGAIN (see module docstring)
            return None
        data = bytes(self.rx_queue[:n])
        self.rx_queue = self.rx_queue[n:]  # MicroPython bytearray has no slice-delete, unlike CPython
        self.log.append(("read", n))
        return data

    def readinto(self, buf: bytearray | memoryview, nbytes: int | None = None) -> int | None:
        self.rx_api_calls += 1
        self._count_overask(len(buf) if nbytes is None else min(nbytes, len(buf)))
        n = len(buf) if nbytes is None else min(nbytes, len(buf))
        n = min(n, len(self.rx_queue))
        if n == 0:
            return None
        buf[:n] = self.rx_queue[:n]
        self.rx_queue = self.rx_queue[n:]  # MicroPython bytearray has no slice-delete, unlike CPython
        self.log.append(("readinto", n))
        return n

    def readline(self, size: int = -1) -> bytes | None:
        # Clamped to any() like every counted read: readline() reads byte by byte up to a newline or
        # `size`, each missing byte a blocking wait; with no size and no newline buffered, the C read
        # still waits for the one byte past the buffer.
        self.rx_api_calls += 1
        self._update()  # rp2 drains the RX FIFO into its buffer first (machine_uart.c:505, :604)
        queued = len(self.rx_queue)
        idx = self.rx_queue.find(b"\n")
        if idx != -1 and (size < 0 or idx < size):
            end = idx + 1
        elif size < 0:
            end = queued
            UART.would_have_blocked_bytes += 1
        else:
            end = min(size, queued)
            self._count_overask(size)
        if end == 0:
            return None
        data = bytes(self.rx_queue[:end])
        self.rx_queue = self.rx_queue[end:]  # MicroPython bytearray has no slice-delete, unlike CPython
        self.log.append(("readline", len(data)))
        return data

    def txdone(self) -> bool:
        # Real UART.txdone(): True once the TX ring, the FIFO and the line are idle (machine_uart.c:510-514).
        if self.tx_pending_rounds > 0:
            self.tx_pending_rounds -= 1
            return False
        return True

    def write(self, buf: object) -> int | None:
        # Real rp2 uart.write() can accept fewer bytes than given (its per-byte timeout hit after
        # some progress) or none at all (None, MP_EAGAIN). write_limit models both - 0 for a total
        # send failure, a positive count below len(buf) for a short write a caller must retry.
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
    # knob assertable - every knob is an explicit schedule, never randomness. Offsets in
    # drop_indices/corrupt_indices are stream offsets within this direction, not per write() call.
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity  # far-side FIFO bound; overflow drops the newest bytes
        self.silent = False  # one-sided silence
        self.drop_indices: set[int] = set()
        self.corrupt_indices: dict[int, int] = {}  # stream offset -> xor mask, length-preserving
        self.truncate_after: int | None = None  # cut this direction's stream after N offered bytes
        self.noise_before_next = bytearray()  # injected once, ahead of the next delivery
        self.delay = False  # hold delivered bytes until UARTLink.release_delayed()
        self.duplicate_next = 0  # repeat this many of the next delivered bytes
        self.offered = 0
        self.delivered = 0
        self.dropped_overrun = 0
        self.pending = bytearray()  # held by delay
        self.wire_log = _WireLog(_WIRE_LOG_MAXLEN)  # the newest bytes that reached the destination

    def record(self, data: "bytes | bytearray") -> None:
        # Counts and logs bytes that reached the destination.
        self.delivered += len(data)
        self.wire_log.extend(data)

    def shape(self, data: bytes) -> bytearray:
        # Applies the per-byte knobs in a fixed order - truncation bounds the stream, dropping
        # removes bytes, corruption only rewrites them (separate, composable, attributable).
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
    # Byte-level crossover between two UART fakes - one independent FIFO per direction with its own
    # fault knobs (A1/A3). The fakes keep no concept of a frame: a write lands in the far side's
    # rx_queue and reads split where the reader asks. Never uses a real poll() - see LinkPoller.
    def __init__(self, uart_a: "UART", uart_b: "UART", capacity_a_to_b: int | None = None, capacity_b_to_a: int | None = None) -> None:
        if uart_a._link is not None or uart_b._link is not None:
            raise ValueError("UART already attached to a link")
        if uart_a is uart_b:
            raise ValueError("a link needs two distinct endpoints")
        self.endpoints = (uart_a, uart_b)
        # Default each direction's bound to the *destination's* own rxbuf: that is what really
        # drops a frame's tail on hardware, which is the failure J.6's rxbuf floors exist for.
        self.a_to_b = _LinkDirection(uart_b.rxbuf if capacity_a_to_b is None else capacity_a_to_b)
        self.b_to_a = _LinkDirection(uart_a.rxbuf if capacity_b_to_a is None else capacity_b_to_a)
        uart_a._link = self
        uart_b._link = self

    def _deposit(self, direction: "_LinkDirection", dest: "UART", data: bytearray) -> None:
        if data and not dest.imsc & _IMSC_RX_IRQ:
            taken = dest._arrive(data)  # no interrupt: the bytes land over time, in a DMA ring or the FIFO
            direction.dropped_overrun += len(data) - taken
            direction.record(data[:taken])
            return
        room = direction.capacity - len(dest.rx_queue)
        if room < len(data):
            direction.dropped_overrun += len(data) - max(room, 0)
            data = data[: max(room, 0)]
        if not data:
            return
        dest.rx_queue += data
        direction.record(data)

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

    def elapse(self, ms: int) -> None:
        # Fidelity seam for the shared contract's DMA checks: this model's arrivals follow Timer.clock_ms.
        Timer.clock_ms += ms

    def release_delayed(self) -> int:
        # Flushes both directions' held bytes and reports how many were released - the
        # deterministic stand-in for "the wire got around to it".
        released = 0
        for index, direction in ((0, self.a_to_b), (1, self.b_to_a)):
            if not direction.pending:
                continue
            data = direction.pending
            direction.pending = bytearray()
            released += len(data)
            self._deposit(direction, self.endpoints[1 - index], data)
        return released

    def settle(self) -> None:
        # Fidelity seam for the shared contract (tests/_uart_link_contract.py): this model
        # delivers synchronously, so there is nothing to wait for. The twin's own link overrides
        # it with a real wire-time wait.
        return

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


class LinkPoller:
    # Bounded select.poll() stand-in for one UART fake, re-querying its ioctl() every call.
    # Installed by reassigning asy_uart_driver.UART.poller, keeping src/ free of a testability seam.
    # Never wraps a real select.poll(): the port never re-checks ioctl() - CLAUDE.md's known CI hang.
    def __init__(self, uart: "UART", not_ready_calls: int = 0, mask: int = select.POLLIN | select.POLLOUT) -> None:
        self._uart = uart
        self._not_ready = not_ready_calls
        self._mask = mask  # what a real poll asks the stream for: the events the driver registered

    def force_not_ready(self, calls: int) -> None:  # makes the timeout paths reachable
        self._not_ready = calls

    def ipoll(self, _timeout_ms: int = 0) -> "list[tuple[None, int]]":
        if self._not_ready > 0:
            self._not_ready -= 1
            return []
        event = self._uart.ioctl(UART._MP_STREAM_POLL, self._mask)
        return [(None, event)] if event else []

    def register(self, obj: object, mask: int = 0) -> None:
        pass

    def unregister(self, obj: object) -> None:
        pass


class Timer:
    ONE_SHOT = 0
    PERIODIC = 1

    # Records every construction, so a test can assert the product reuses one preallocated Timer through init()
    # (SPECIFICATION.md F.1). Class-level, so it persists for the whole process: compare against a snapshot.
    all_timers: "ClassVar[list[Timer]]" = []

    # Test-only, off by default: real rp2 Timer.init() raises OSError(ENOMEM) on an exhausted alarm
    # pool, and a bare Timer() never reaches that path at all - hence the `if kwargs` gate below.
    # A shared class attribute, so a test must reset it afterward.
    raise_on_arm = False
    # Which class init() then raises. src/ guards Timer.init() with `except (OSError, MemoryError)`,
    # a real alarm allocation being able to fail either way, so set this to MemoryError to prove the
    # sibling arm too. Shared class attribute as well; reset both.
    raise_on_arm_exc: "type[BaseException]" = OSError
    # A fake clock only tests advance; each init() records (clock_ms, period, mode) in its own `arms`, so a test
    # can read when the product armed a timer without patching any module's time source.
    clock_ms: "ClassVar[int]" = 0

    def __init__(self, id: int = -1, **kwargs: "Any") -> None:
        self.id = id
        self.period = -1
        self.mode = self.PERIODIC
        self.callback: Callable[[Timer], None] | None = None
        self.deinit_called = False
        self.arms = _CallLog()  # (clock_ms, period, mode) per init(), the newest _LOG_MAXLEN
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
        self.arms.append((Timer.clock_ms, period, mode))

    def deinit(self) -> None:
        self.callback = None
        self.deinit_called = True

    def trigger(self) -> None:
        # No real-hardware equivalent - lets test code fire a callback deterministically instead of
        # waiting on this fake's `period` (which is never actually scheduled against real time).
        # A ONE_SHOT is spent once its period elapses, as on rp2; a PERIODIC stays armed.
        callback = self.callback
        if self.mode == self.ONE_SHOT:
            self.callback = None
        if callback is not None:
            callback(self)

    def drop(self) -> None:
        # One period elapsing with its soft callback lost to a full scheduler queue (Part F.1): a
        # ONE_SHOT never fires again, a PERIODIC simply fires next period.
        if self.mode == self.ONE_SHOT:
            self.callback = None


class RTC:
    # Stores whatever 8-tuple it is given, unvalidated: the real rp2 setter uses only indices
    # 0/1/2/4/5/6, extracting weekday and never writing it, so there is no validity behaviour to
    # model (BACKLOG.md has the history of an earlier pass getting this wrong).
    raise_exc: "Exception | None" = None  # test-only fault injection, shared class attribute like Timer.raise_on_arm
    # Class-level, not per-instance: one physical peripheral, so a freshly constructed RTC() must
    # read back what an earlier instance set, exactly as the real singleton does.
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


class _Mem32:
    # machine.mem32: 32-bit peripheral register access (extmod/machine_mem.c). Models the two reset registers and the
    # UART blocks' UARTRSR/UARTECR, UARTIMSC and UARTDMACR of the latest UART per id; any other address raises
    # ValueError ("not modelled"). Every access is recorded in `log` as ("read"|"write", address, value).
    def __init__(self) -> None:
        self.log = _CallLog(_MEM32_LOG_MAXLEN)

    def __getitem__(self, address: int) -> int:
        if address == _WATCHDOG_REASON:
            value = watchdog_reason_value
        elif address == _CHIP_RESET:
            value = chip_reset_value
        else:
            uart, offset = self._uart_at(address)
            value = uart._register(offset)
        self.log.append(("read", address, value))
        return value

    def __setitem__(self, address: int, value: int) -> None:
        uart, offset = self._uart_at(address)
        self.log.append(("write", address, value))
        uart._set_register(offset, value & 0xFFFFFFFF)

    @staticmethod
    def _uart_at(address: int) -> "tuple[UART, int]":
        for uart_id, base in enumerate(_UART_BASES):
            if base <= address < base + 0x1000:
                uart = UART._live.get(uart_id)
                if uart is None:
                    raise ValueError(f"mem32: UART{uart_id} not constructed")
                return uart, address - base
        raise ValueError(f"mem32 address 0x{address:08x} not modelled")


mem32 = _Mem32()
_WATCHDOG_REASON = 0x40058008  # bit 0 TIMER, bit 1 FORCE (pico-sdk hardware/regs/watchdog.h)
_CHIP_RESET = 0x40064008  # bit 8 HAD_POR, bit 16 HAD_RUN, bit 20 HAD_PSM_RESTART (vreg_and_chip_reset.h)
_REASON_FORCE = 0x2  # watchdog_reboot(..., 0) sets the trigger bit (pico-sdk watchdog.c:65-66)
_HAD_POR = 0x100
# Test-only: what the two registers read, the power-on pair until power_on()/reset()/bootloader() move them.
watchdog_reason_value = 0
chip_reset_value = _HAD_POR


# rp2's reset causes (ports/rp2/modmachine.c:57-58 at v1.29.0); reset_cause() answers the module value.
PWRON_RESET = 1
WDT_RESET = 3
reset_cause_value = PWRON_RESET
# rp2's two backup regions, scratch[0..3] and scratch[5..7] (ports/rp2/machine_mem_backup.c:38-41): one static
# view each, the same object on every call, kept across reset() as the watchdog scratch registers are.
_REGIONS = (array("I", [0, 0, 0, 0]), array("I", [0, 0, 0]))
_REGION_VIEWS = (memoryview(_REGIONS[0]), memoryview(_REGIONS[1]))


def mem_backup(region: int = 0) -> "Any":
    # extmod/machine_mem.c:135-148: one region's view, or (for -1) a tuple of every region's; any other index
    # outside the table raises. Typed Any because the real answer's type depends on the argument.
    if region == -1:
        return _REGION_VIEWS
    if region < 0 or region >= len(_REGION_VIEWS):
        raise ValueError("invalid region")
    return _REGION_VIEWS[region]


def reset_cause() -> int:
    return reset_cause_value


def power_on() -> None:
    # Test-only: a power cycle clears both regions, reports PWRON_RESET and leaves REASON 0 with HAD_POR set.
    global reset_cause_value, watchdog_reason_value, chip_reset_value
    for region in _REGIONS:
        for i in range(len(region)):
            region[i] = 0
    reset_cause_value = PWRON_RESET
    watchdog_reason_value = 0
    chip_reset_value = _HAD_POR


# Real machine.reset()/machine.bootloader() reset the MCU and never return at all - this fake records the call
# and the cause rp2 then reports (watchdog_reboot(), so WDT_RESET), instead of ending the test process.
reset_count = 0
bootloader_count = 0


def reset() -> None:
    global reset_count, reset_cause_value, watchdog_reason_value
    reset_count += 1
    reset_cause_value = WDT_RESET
    watchdog_reason_value = _REASON_FORCE  # CHIP_RESET is left as it was: a watchdog reset clears no HAD_* bit


def bootloader() -> None:
    global bootloader_count, reset_cause_value, watchdog_reason_value
    bootloader_count += 1
    reset_cause_value = WDT_RESET
    watchdog_reason_value = _REASON_FORCE
