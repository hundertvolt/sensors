"""Test-only fake `machine` module for the unit tier: models the rp2 port's raw I2C/SPI/UART/Pin/Timer/RTC/WDT surface
(MicroPython v1.29.0), so the real drivers run against it (SPECIFICATION.md E.4). It also models rp2's zero-argument
`Timer()`, which the board stub lacks (B.15)."""

import errno
import io
import select
import time
from array import array

import microtest

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Any, ClassVar


_NUM_BANK0_GPIOS = 30  # pico-sdk rp2040 platform_defs.h:40: GPIO0-29, the ids machine_pin_find() accepts
# The WLAN chip's three GPIOs (CYW43_WL_GPIO_COUNT, boards/RPI_PICO_W/mpconfigboard.h:20): no number reaches them on
# rp2, only a name, so the fake keys their state by ids 30-32, past every number Pin() accepts.
_PIN_NAMES: "dict[str, int]" = {f"GPIO{n}": n for n in range(_NUM_BANK0_GPIOS)}  # CPU names, boards/make-pins.py:95-108
_PIN_NAMES.update({f"EXT_GPIO{n}": _NUM_BANK0_GPIOS + n for n in range(3)})
_PIN_NAMES.update({f"GP{n}": n for n in list(range(23)) + [26, 27, 28]})  # board names, boards/RPI_PICO_W/pins.csv
_PIN_NAMES.update({f"WL_GPIO{n}": _NUM_BANK0_GPIOS + n for n in range(3)})
_PIN_NAMES["LED"] = _NUM_BANK0_GPIOS  # LED,EXT_GPIO0
# Pin()'s default for an argument left out: rp2 tells an omitted argument from None by its count (machine_pin.c:317),
# so the fake compares identity with this one object. Typed int, so every parameter can take it as its default.
_OMITTED: int = object()  # type: ignore[assignment]


class _PinState:
    # One GPIO's configuration, shared by every Pin object naming it: rp2's pins are static table entries
    # (machine_pin_find(), machine_pin.c:188). mode and pull read None until a construction or init() sets them.
    def __init__(self) -> None:
        self.mode: int | None = None
        self.pull: int | None = None
        self.alt = Pin._ALT_SIO
        self.level = 0  # the output latch: what OUT drives, or OPEN_DRAIN's 0 = pull low, 1 = release
        self.irq_handler: Callable[[Pin], None] | None = None
        self.irq_trigger = Pin.IRQ_FALLING | Pin.IRQ_RISING
        self.irq_hard = False


class Pin:
    # Not modelled: the per-pin alternate-function table (any alt is taken), the pads' own power-on pulls, a
    # Pin's __call__/low()/high() forms. Tests read mode/pull/alt and the irq_* registration, which real Pin has no
    # attribute for.
    TEST_API = (
        "id", "mode", "pull", "alt", "irq_handler", "irq_hard", "irq_trigger", "set_external_level", "value_log",
        "reset_registry", "trigger_irq",
    )  # fmt: skip
    IN = 0  # ports/rp2/machine_pin.h:34-37 (v1.29.0), as OUT, OPEN_DRAIN and ALT
    OUT = 1
    OPEN_DRAIN = 2
    ALT = 3
    ALT_I2C = 3  # GPIO_FUNC_I2C (pico-sdk structs/io_bank0.h:34; machine_pin.c:513)
    _ALT_SIO = 5  # GPIO_FUNC_SIO (io_bank0.h:36), rp2's alt default (machine_pin.c:247)
    IRQ_FALLING = 0x04  # GPIO_IRQ_EDGE_FALL / _RISE (machine_pin.c:507-508)
    IRQ_RISING = 0x08
    PULL_UP = 1  # GPIO_PULL_UP / _DOWN (machine_pin.c:505-506)
    PULL_DOWN = 2

    # Per GPIO id, shared by every Pin object on it: its configuration, the level the outside world puts on the line
    # (test-only, default 1: the bus pull-ups) and every level the code drove onto it.
    _states: "ClassVar[dict[int, _PinState]]" = {}
    _external: "ClassVar[dict[int, int | Callable[[int, _CallLog], int]]]" = {}
    _value_logs: "ClassVar[dict[int, _CallLog]]" = {}

    def __init__(self, id: "int | str | Pin", mode: "int | None" = _OMITTED, pull: "int | None" = _OMITTED, *, value: object = _OMITTED, alt: int = _OMITTED) -> None:
        self.id = Pin._find(id)
        state = Pin._states.get(self.id)
        if state is None:
            state = Pin._states[self.id] = _PinState()
        self._state = state
        # rp2 configures when any argument beyond the id is given, None included (machine_pin.c:317-323).
        if mode is not _OMITTED or pull is not _OMITTED or value is not _OMITTED or alt is not _OMITTED:
            self.init(
                None if mode is _OMITTED else mode,
                None if pull is _OMITTED else pull,
                value=None if value is _OMITTED else value,
                alt=self._ALT_SIO if alt is _OMITTED else alt,
            )

    def _drive(self, level: int) -> None:
        self._state.level = level
        Pin.value_log(self.id).append(level)

    @staticmethod
    def _find(id: object) -> int:
        # machine_pin_find(), machine_pin.c:165-192: a Pin, a board then a CPU name, or a number below 30.
        if isinstance(id, Pin):
            return id.id
        if isinstance(id, str):
            number = _PIN_NAMES.get(id)
            if number is None:
                raise ValueError(f'unknown named pin "{id}"')
            return number
        if isinstance(id, int) and 0 <= id < _NUM_BANK0_GPIOS:
            return id
        raise ValueError("invalid pin")

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

    @property
    def alt(self) -> int:
        return self._state.alt

    def init(self, mode: "int | None" = None, pull: "int | None" = None, *, value: object = None, alt: int = _ALT_SIO) -> None:
        # machine_pin_obj_init_helper(), machine_pin.c:250-310: a None mode keeps the mode; value= is latched only by OUT
        # (before the mode applies) and OPEN_DRAIN (released when omitted); any other mode hands the pad to `alt`.
        state = self._state
        external = self.id >= _NUM_BANK0_GPIOS
        if external and pull is not None:
            raise ValueError("pulls are not supported for external pins")
        if external and alt != self._ALT_SIO:
            raise ValueError("alternate functions are not supported for external pins")
        level = None if value is None else (1 if value else 0)
        if mode is not None:
            if external and mode not in (self.IN, self.OUT):
                raise ValueError("only Pin.OUT and Pin.IN are supported for this pin")  # machine_pin_cyw43.c
            if mode in (self.IN, self.OUT, self.OPEN_DRAIN):
                if mode == self.OPEN_DRAIN:
                    state.level = 1 if level is None else level
                elif level is not None and (mode == self.OUT or external):
                    state.level = level
                state.mode = mode
                state.alt = self._ALT_SIO
            else:
                state.mode = self.ALT
                state.alt = alt
        if not external:
            # Set unconditionally, None meaning no pull (machine_pin.c:300-306): rp2 keeps the PULL_UP/PULL_DOWN bits.
            state.pull = 0 if pull is None else pull & (self.PULL_UP | self.PULL_DOWN)

    def irq(
        self,
        handler: "Callable[[Pin], None] | None" = None,
        trigger: int = IRQ_FALLING | IRQ_RISING,
        *,
        hard: bool = False,
    ) -> "Pin":
        # Real rp2 Pin.irq() replaces the GPIO's previous handler outright, fires on every matching edge until called
        # again, and returns the IRQ object (stood in for here by the Pin). trigger_irq() simulates one edge.
        state = self._state
        state.irq_handler = handler
        state.irq_trigger = trigger
        state.irq_hard = hard
        return self

    @property
    def irq_handler(self) -> "Callable[[Pin], None] | None":
        return self._state.irq_handler

    @property
    def irq_hard(self) -> bool:
        return self._state.irq_hard

    @property
    def irq_trigger(self) -> int:
        return self._state.irq_trigger

    @property
    def mode(self) -> "int | None":
        return self._state.mode

    def off(self) -> None:
        self._drive(0)

    def on(self) -> None:
        self._drive(1)

    @property
    def pull(self) -> "int | None":
        return self._state.pull

    @classmethod
    def reset_registry(cls) -> None:
        # Test-only: every GPIO back to its power-on state, with no planted level or value log.
        cls._states.clear()
        cls._external.clear()
        cls._value_logs.clear()

    def toggle(self) -> None:
        self._drive(0 if self._state.level else 1)

    def trigger_irq(self) -> None:
        # No real-hardware equivalent - fires the GPIO's registered handler once, standing in
        # for one real edge interrupt. No-op if irq() was never called or was disabled.
        handler = self._state.irq_handler
        if handler is not None:
            handler(self)

    def value(self, x: object = None) -> int | None:
        # Real rp2 Pin.value() reads the pad (gpio_get(), ports/rp2/machine_pin.c): an output reads what
        # it drives, an open-drain pin the wired-AND of its drive and the line. An input with no planted
        # level and no pull-up reads its own latch, the level a test sets through value(x).
        if x is not None:
            self._drive(1 if x else 0)
            return None
        state = self._state
        if state.mode == self.OPEN_DRAIN:
            return self._line() if state.level else 0
        if state.mode == self.ALT:
            return self._line()
        if state.mode == self.IN and ((state.pull or 0) & self.PULL_UP or self.id in Pin._external):
            return self._line()
        return state.level

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
_LOG_CHUNK = 256  # entries per storage chunk of a call log, so its storage never needs a block over 2 kB
_MEM32_LOG_MAXLEN = 64  # likewise for register accesses: a DMA reader reads UARTRSR at every fill-level read
_WIRE_LOG_MAXLEN = 4096  # bytes of a link direction's wire log kept; its `dropped` counts the rest
_WIRE_CHUNK = 512  # bytes per storage chunk of a wire log
_RX_INFLIGHT_MAX = 4096  # bytes waiting on the wire to a UART with its interrupt off; more is an overrun


class _CallLog:
    # A record that grows to `maxlen` entries, then overwrites its oldest in place: fixed occupancy once
    # full, so a long run neither exhausts the heap nor frees half of it at once (a swing a heap test reads
    # as retention). Reads - len(), iteration, [i], slices, == - see the entries oldest first.
    def __init__(self, maxlen: int = _LOG_MAXLEN) -> None:
        self.maxlen = maxlen
        self.dropped = 0  # assertable: a test reading the whole log can tell it is not the whole log
        self._chunks: list[list[Any]] = []
        self._n = 0
        self._head = 0  # once full: the slot holding the oldest entry

    def __contains__(self, entry: object) -> bool:
        return any(entry in chunk for chunk in self._chunks)

    def __eq__(self, other: object) -> bool:
        return self._ordered() == other

    def __getitem__(self, index: "int | slice") -> "Any":
        if isinstance(index, slice):
            return self._ordered()[index]
        position = index + self._n if index < 0 else index
        if not 0 <= position < self._n:
            raise IndexError("log index out of range")
        slot = (self._head + position) % self._n
        return self._chunks[slot // _LOG_CHUNK][slot % _LOG_CHUNK]

    def __iter__(self) -> "Iterator[Any]":
        return iter(self._ordered())

    def __len__(self) -> int:
        return self._n

    def _ordered(self) -> "list[Any]":
        flat = [entry for chunk in self._chunks for entry in chunk]
        return flat[self._head :] + flat[: self._head]

    def append(self, entry: object) -> None:
        # Stored in fixed-size chunks, so a long log never reallocates one large contiguous block (a full
        # one-list log doubled to 32 kB mid-run, which a fragmented coverage-build heap could not supply).
        if self._n < self.maxlen:
            if self._n % _LOG_CHUNK == 0:
                self._chunks.append([])
            self._chunks[-1].append(entry)
            self._n += 1
            return
        self._chunks[self._head // _LOG_CHUNK][self._head % _LOG_CHUNK] = entry
        self._head = (self._head + 1) % self.maxlen
        self.dropped += 1

    def clear(self) -> None:
        self._chunks = []
        self._n = 0
        self._head = 0

    def count(self, entry: object) -> int:
        return sum(chunk.count(entry) for chunk in self._chunks)


class _WireLog:
    # The bytes a link direction delivered, kept the way _CallLog keeps entries: up to `maxlen`, then
    # the oldest overwritten in place and counted in `dropped`; read oldest first (bytes(), [i], len()).
    def __init__(self, maxlen: int) -> None:
        self.maxlen = maxlen
        self.dropped = 0
        self._chunks: list[bytearray] = []  # fixed-size, so the log never reallocates one 4 kB block
        self._n = 0
        self._head = 0

    def __eq__(self, other: object) -> bool:
        return self._ordered() == other

    def __getitem__(self, index: int) -> int:
        position = index + self._n if index < 0 else index
        if not 0 <= position < self._n:
            raise IndexError("wire log index out of range")
        slot = (self._head + position) % self._n
        return self._chunks[slot // _WIRE_CHUNK][slot % _WIRE_CHUNK]

    def __iter__(self) -> "Iterator[int]":
        return iter(self._ordered())

    def __len__(self) -> int:
        return self._n

    def _ordered(self) -> bytearray:
        flat = bytearray().join(self._chunks)
        return flat[self._head :] + flat[: self._head]

    def append(self, byte: int) -> None:
        if self._n < self.maxlen:
            if self._n % _WIRE_CHUNK == 0:
                self._chunks.append(bytearray())
            self._chunks[-1].append(byte)
            self._n += 1
            return
        self._chunks[self._head // _WIRE_CHUNK][self._head % _WIRE_CHUNK] = byte
        self._head = (self._head + 1) % self.maxlen
        self.dropped += 1

    def clear(self) -> None:
        self._chunks = []
        self._n = 0
        self._head = 0

    def extend(self, data: "bytes | bytearray") -> None:
        for byte in data:
            self.append(byte)


# The ops each bus fake checks its fault queue on: a fault queued for any other op could never fire (rp2's I2C can raise
# on every transfer; its SPI only on a reading one, machine_spi.c:312-315).
_I2C_FAULT_OPS = ("readfrom_into", "writeto", "readfrom_mem", "writeto_mem")
_SPI_FAULT_OPS = ("readinto", "write_readinto")


def _queue_fault(faults: "dict[str, list[tuple[type[BaseException], tuple[object, ...], int | None, int | None]]]", ops: "tuple[str, ...]", entry: "tuple[str, type[BaseException], tuple[object, ...], int, int | None, int | None]") -> None:
    op, exc_type, args, times, match, address = entry
    if op not in ops:
        raise ValueError(f"{op!r} cannot raise on this bus (rp2): the fake checks only {ops}")
    if times < 1:
        raise ValueError("times must be at least 1")
    faults.setdefault(op, []).extend([(exc_type, args, match, address)] * times)


def _raise_queued(faults: "dict[str, list[tuple[type[BaseException], tuple[object, ...], int | None, int | None]]]", op: str, key: "int | None", address: "int | None") -> None:
    # The oldest queued fault this call matches raises, a fresh exception each time; the rest stay queued.
    queue = faults.get(op)
    if queue:
        for i, (exc_type, args, match, only) in enumerate(queue):
            if (match is None or match == key) and (only is None or only == address):
                del queue[i]
                raise exc_type(*args)


class I2C:
    # rp2's I2C raises OSError(EIO) on a NAK, a bus fault or a lost arbitration, OSError(ETIMEDOUT) on a held or
    # stretched SCL, and ENODEV only from a NAKed zero-length probe, the soft-I2C path (machine_i2c.c:127-145).
    # Not modelled: clock-stretch timing, arbitration loss, a BMP3xx-style address/data-pair burst write.
    #
    # One static object per id, as rp2's machine.I2C(id) (machine_i2c.c:50-53, 87): a re-construction re-initialises
    # the controller and keeps the devices, faults and log. reset_id() is a test's power-cycled controller.
    TEST_API = (
        "id", "scl", "sda", "freq", "timeout", "deinit_called", "deinit_count", "log", "registers", "read_queue",
        "read_queue_by_address", "nak_addresses", "attached", "busy", "raise_on_construct", "inject_fault", "pending",
        "register_device", "reset_id", "reset_registry", "short_ack",
    )  # fmt: skip
    _static: "ClassVar[dict[int, I2C]]" = {}
    raise_on_construct: "ClassVar[BaseException | None]" = None  # test-only: the next construction raises it, once
    _fresh: bool

    def __init__(self, id: int, *, scl: Pin, sda: Pin, freq: int = 400000, timeout: int = 50000) -> None:
        # freq and timeout take rp2's defaults on every construction with arguments (machine_i2c.c:37-38, 100-108).
        if self._fresh:
            self._fresh = False
            self.deinit_called = False
            self.deinit_count = 0
            self.log = _CallLog()
            self.registers: dict[tuple[int, int], bytearray] = {}  # register runs: a run's bytes are consecutive registers
            self.read_queue: list[bytes] = []  # its raw-transaction counterpart: readfrom_into() has no register to key off
            self.read_queue_by_address: dict[int, list[bytes]] = {}  # per-address queue, checked before the shared one
            self.nak_addresses: set[int] = set()  # convenience: EIO (no ACK) on every op to this address
            self.attached: set[int] = set()  # raw-command devices that answer a probe (a register device always does)
            self.busy = False  # convenience: ETIMEDOUT (bus/clock-stretch timeout) on every op, any address
            self._faults: dict[str, list[tuple[type[BaseException], tuple[object, ...], int | None, int | None]]] = {}
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
        if id not in (0, 1):
            raise ValueError(f"I2C({id}) doesn't exist")  # machine_i2c.c:82-84
        bus = cls._static.get(id)
        if bus is None:
            bus = super().__new__(cls)
            bus._fresh = True
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

    def _answers(self, address: int) -> bool:
        return address not in self.nak_addresses and (address in self.attached or self._addr_bytes(address) > 0)

    def _covering(self, address: int, register: int) -> int:
        # The byte at `register` inside a run that starts below it, else 0 (what an unseeded register reads here).
        best = -1
        value = 0
        for (addr, start), run in self.registers.items():
            if addr == address and best < start < register < start + len(run):
                best = start
                value = run[register - start]
        return value

    def _load(self, address: int, register: int, nbytes: int) -> bytes:
        # A burst reads consecutive registers (the pointer auto-increments, ISL29125 FN8424 p.8; BMP388 ds001 s.5).
        out = bytearray()
        while len(out) < nbytes:
            run = self.registers.get((address, register))
            take = bytes(run[: nbytes - len(out)]) if run else bytes([self._covering(address, register)])
            out += take
            register += len(take)
        return bytes(out)

    def _maybe_raise(self, op: str, address: int, key: int | None = None) -> None:
        if self.busy:
            raise OSError(errno.ETIMEDOUT, "bus busy / clock stretch timeout")
        if address in self.nak_addresses:
            raise OSError(errno.EIO, "no ACK from device")
        _raise_queued(self._faults, op, key, address)

    def _next_read_bytes(self, address: int, nbytes: int) -> bytes:
        per_address = self.read_queue_by_address.get(address)
        data = per_address.pop(0) if per_address else (self.read_queue.pop(0) if self.read_queue else b"")
        return (data + bytes(nbytes))[:nbytes]  # always exactly nbytes, zero-padded/truncated like real hw

    def _store(self, address: int, register: int, data: bytes) -> None:
        # A burst writes consecutive registers (ISL29125 FN8424 p.7): its own run, and the same bytes in every other
        # run covering them, so a later read from any start sees one register file.
        end = register + len(data)
        for (addr, start), run in self.registers.items():
            if addr == address and start != register:
                low, high = max(start, register), min(start + len(run), end)
                if low < high:
                    run[low - start : high - start] = data[low - register : high - register]
        own = self.registers.get((address, register))
        if own is not None and len(own) > len(data):
            own[: len(data)] = data
        else:
            self.registers[(address, register)] = bytearray(data)

    def deinit(self) -> None:
        # Real rp2 I2C.deinit() exists only from v1.29.0 and is a silent no-op even there - the port
        # leaves the .deinit slot NULL (SPECIFICATION.md Part F.5). So every bus operation keeps
        # working afterwards here too; the counters only record that the call was forwarded.
        self.deinit_called = True
        self.deinit_count += 1
        self.log.append(("deinit",))

    def inject_fault(self, op: str, exc_type: "type[BaseException]", *args: object, times: int = 1, match: int | None = None, address: int | None = None) -> None:
        # Test-only: the next `times` calls to `op` raise exc_type(*args), oldest fault first. match is the register a
        # register-device access names (the pointer for readfrom_into(), memaddr for *_mem); address filters the device.
        _queue_fault(self._faults, _I2C_FAULT_OPS, (op, exc_type, args, times, match, address))

    def pending(self, op: str) -> int:
        # Test-only: the faults still queued for `op`.
        return len(self._faults.get(op, ()))

    def readfrom_into(self, address: int, buf: object, stop: bool = True) -> None:
        nbytes = len(buf)  # type: ignore[arg-type]
        if self._addr_bytes(address):
            pointer = self._pointers.get(address, 0)
            self._maybe_raise("readfrom_into", address, pointer)
            data = self._load(address, pointer, nbytes)
        else:
            self._maybe_raise("readfrom_into", address)
            data = self._next_read_bytes(address, nbytes)
        buf[:] = data  # type: ignore[index]
        self.log.append(("readfrom_into", address, data, stop))

    def readfrom_mem(self, address: int, memaddr: int, nbytes: int, *, addrsize: int = 8) -> bytes:
        self._maybe_raise("readfrom_mem", address, memaddr)
        data = self._load(address, memaddr, nbytes)
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
        cls._static.pop(id, None)

    @classmethod
    def reset_registry(cls) -> None:
        cls._static.clear()

    def scan(self) -> list[int]:
        # extmod/machine_i2c.c:341-356: one zero-length probe per address 0x08-0x77, each kept when it returned 0, so a
        # NAK or a held bus shortens the list and nothing raises.
        self.log.append(("scan",))
        if self.busy:
            return []
        return [address for address in range(0x08, 0x78) if self._answers(address)]

    def short_ack(self, address: int, n: int) -> None:
        # Test-only: the next write to `address` reports only n bytes ACKed, as rp2's writeto() does for a
        # data byte the device NACKs (pico-sdk i2c.c:229-231), and the device keeps none of it.
        self._short_acks[address] = n

    def writeto(self, address: int, buf: object, stop: bool = True) -> int:
        data = bytes(buf)  # type: ignore[call-overload]
        if not data:
            # The probe: rp2's zero-length write takes the soft-I2C transfer, whose NAK is ENODEV (machine_i2c.c:127-145).
            if self.busy:
                raise OSError(errno.ETIMEDOUT, "bus busy / clock stretch timeout")
            _raise_queued(self._faults, "writeto", None, address)
            if not self._answers(address):
                raise OSError(errno.ENODEV, "no device at this address")
            self.log.append(("writeto", address, data, stop))
            return 0
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
                self._store(address, register, data[n:])
        return len(data)

    def writeto_mem(self, address: int, memaddr: int, buf: object, *, addrsize: int = 8) -> None:
        self._maybe_raise("writeto_mem", address, memaddr)
        self._store(address, memaddr, bytes(buf))  # type: ignore[call-overload]
        self.log.append(("writeto_mem", address, memaddr, bytes(buf), addrsize))  # type: ignore[call-overload]


_SPI_DMA_MIN_SIZE = 32  # ports/rp2/machine_spi.c:267 dma_min_size_threshold: a shorter transfer never takes DMA


class SPI:
    # SPI has no ACK/NAK, so write() cannot raise; a reading transfer of 32+ bytes takes the DMA path, whose RX-overrun
    # check raises OSError(EIO) (F.5.2) - modelled by rx_overrun and inject_fault(). read_queue primes what a read gets.
    # Not modelled: baudrate rounding, pin muxing rules, rp2's static object per id.
    TEST_API = (
        "id", "sck", "mosi", "miso", "baudrate", "polarity", "phase", "bits", "firstbit", "deinit_called", "deinit_count",
        "log", "read_queue", "rx_overrun", "rx_overrun_remaining", "inject_fault", "pending",
    )  # fmt: skip
    MSB = 1  # pico-sdk hardware/spi.h:184-187 SPI_MSB_FIRST, rp2's MICROPY_PY_MACHINE_SPI_MSB (mpconfigport.h:199-200)
    LSB = 0

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
        firstbit: int = MSB,
    ) -> None:
        if id not in (0, 1):
            raise ValueError(f"SPI({id}) doesn't exist")  # machine_spi.c:162-164
        if firstbit == self.LSB:
            raise NotImplementedError("LSB")  # machine_spi.c:202-203: rp2 implements MSB first only
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
        self._faults: dict[str, list[tuple[type[BaseException], tuple[object, ...], int | None, int | None]]] = {}
        self._opcode: int | None = None  # the command the last write() opened: the key a fault's match= names

    def _maybe_raise(self, op: str, nbytes: int, key: int | None = None) -> None:
        # A transfer below dma_min_size_threshold takes the blocking software path, which has no overrun check and
        # cannot raise (machine_spi.c:267-318): the overrun knobs and the fault queue alike wait for a long one.
        if nbytes < _SPI_DMA_MIN_SIZE:
            return
        if self.rx_overrun:
            raise OSError(errno.EIO, "SPI RX overrun")
        if self.rx_overrun_remaining > 0:
            self.rx_overrun_remaining -= 1
            raise OSError(errno.EIO, "SPI RX overrun")
        _raise_queued(self._faults, op, key, None)

    def _next_read_bytes(self, nbytes: int) -> bytes:
        data = self.read_queue.pop(0) if self.read_queue else b""
        return (data + bytes(nbytes))[:nbytes]  # always exactly nbytes, zero-padded/truncated like real hw

    def deinit(self) -> None:
        # Real rp2 machine.SPI.deinit() leaves the protocol's .deinit slot NULL: a silent no-op that neither
        # stops the peripheral nor releases the pins (Part F.5). This fake therefore leaves every bus
        # operation working afterwards; the counters only record that asy_spi_driver.py forwarded the call.
        self.deinit_called = True
        self.deinit_count += 1
        self.log.append(("deinit",))

    def init(
        self,
        baudrate: int = -1,
        *,
        polarity: int = -1,
        phase: int = -1,
        bits: int = -1,
        firstbit: int = -1,
    ) -> None:
        # Real rp2 SPI.init(): -1/omitted args leave the current setting untouched (ports/rp2/machine_spi.c:220-226,
        # no pins accepted here); LSB first raises as at construction (:255-256).
        if firstbit == self.LSB:
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

    def inject_fault(self, op: str, exc_type: "type[BaseException]", *args: object, times: int = 1, match: int | None = None) -> None:
        # Test-only: the next `times` reading transfers of 32+ bytes on `op` raise exc_type(*args), oldest first; match
        # is the opcode the last write() opened. A write fault is refused: a write-only transfer ignores the overrun.
        _queue_fault(self._faults, _SPI_FAULT_OPS, (op, exc_type, args, times, match, None))

    def pending(self, op: str) -> int:
        # Test-only: the faults still queued for `op`.
        return len(self._faults.get(op, ()))

    def readinto(self, buf: bytearray | memoryview, write_value: int = 0x00) -> None:
        self._maybe_raise("readinto", len(buf), self._opcode)
        data = self._next_read_bytes(len(buf))
        buf[:] = data
        self.log.append(("readinto", len(buf), write_value))

    def write(self, buf: object) -> None:
        data = bytes(buf)  # type: ignore[call-overload]
        self._opcode = data[0] if data else None
        self.log.append(("write", data))

    def write_readinto(self, buffer_out: object, buffer_in: bytearray | memoryview) -> None:
        # Real machine.SPI.write_readinto() (mp_machine_spi_write_readinto(), shared by hardware
        # and soft SPI): raises ValueError before any transfer if the two buffers' lengths differ.
        if len(buffer_out) != len(buffer_in):  # type: ignore[arg-type]
            raise ValueError("buffers must be the same length")
        out = bytes(buffer_out)  # type: ignore[call-overload]
        self._maybe_raise("write_readinto", len(buffer_in), out[0] if out else None)
        data = self._next_read_bytes(len(buffer_in))
        buffer_in[:] = data
        self.log.append(("write_readinto", out))


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
_DMACR_RXDMAE = 0x01  # UARTDMACR bit 0 (RP2040 datasheet 4.2.8, Table 439)
_DMACR_AT_INIT = 0x03  # pico-sdk uart_init() always enables both DREQs (uart.c:86-88)
_RX_FIFO_DEPTH = 32
_RX_DREQ = (21, 23)  # DREQ_UART0_RX, DREQ_UART1_RX (pico-sdk dreq.h)
_RX_UNPACED = float("inf")


class UART(io.IOBase):
    # Bounded stand-in, never a real select.poll(): the fake's readiness must be scripted, not polled in real time
    # (CLAUDE.md "Known hang cause"). io.IOBase gives it the C stream slot a driver's register() needs; reads answer
    # None (MP_EAGAIN) rather than raising and write() is the TX mirror, as rp2 does (Part F.5).
    #
    # Receive model: with RXIM/RTIM set (every construction and init()) the RX interrupt moves each byte
    # into rx_queue, machine.UART's own buffer, as delivered. With both cleared, bytes arrive at the line
    # rate on Timer.clock_ms and go to a DMA channel draining this UART, else to the 32-byte FIFO (OE).
    #
    # Not modelled: baudrate/bits/parity/stop validation, the CTS/RTS pins, hardware flow control.
    TEST_API = (
        "id", "tx", "rx", "baudrate", "bits", "parity", "stop", "rxbuf", "txbuf", "timeout", "timeout_char", "invert",
        "deinit_called", "deinit_count", "log", "rx_queue", "writable", "write_limit", "tx_pending_rounds", "rx_api_calls",
        "rx_rate", "rx_stall_ms", "rx_fifo_dropped", "rsr", "imsc", "dmacr", "would_have_blocked_bytes",
        "real_poll_queries", "feed_rx", "plant_rx_error", "poll_mask", "ioctl",
    )  # fmt: skip
    _MP_STREAM_POLL = 3  # py/stream.h:39
    _DEFAULT_BUFFER_SIZE = 256  # ports/rp2/machine_uart.c:67-69, as MIN and MAX
    _MIN_BUFFER_SIZE = 32
    _MAX_BUFFER_SIZE = 32766
    _UART_INVERT_MASK = 3  # UART_INVERT_TX (1) | UART_INVERT_RX (2), machine_uart.c:82-84
    # POLL requests a real select.poll() made of a UART fake: LinkPoller and the shared contract read poll_mask(), so
    # the after-each check fails any test leaving this above 0 (a real poll over a fake is CLAUDE.md's CI hang).
    real_poll_queries: "ClassVar[int]" = 0
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
        # make_new()/init_helper() validation in the source's own order (machine_uart.c:312-392 and :465: id, tx, rx,
        # invert, rxbuf, txbuf - which matters when several are invalid at once); a buffer below MIN_BUFFER_SIZE is raised to it.
        if id not in (0, 1):
            raise ValueError(f"UART({id}) doesn't exist")
        self._check_pin(id, tx, 0, "TX")
        self._check_pin(id, rx, 1, "RX")
        if invert & ~self._UART_INVERT_MASK:
            raise ValueError("bad inversion mask")
        rxbuf = self._buffer_size(rxbuf, "rxbuf")
        txbuf = self._buffer_size(txbuf, "txbuf")
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

    @classmethod
    def _buffer_size(cls, size: int, name: str) -> int:
        # rxbuf/txbuf as machine_uart.c:370-392 takes them: unset (<= 0) keeps the default, below 32 clamps, above refuses.
        if size <= 0:
            return cls._DEFAULT_BUFFER_SIZE
        if size > cls._MAX_BUFFER_SIZE:
            raise ValueError(f"{name} too large")
        return max(size, cls._MIN_BUFFER_SIZE)

    def _channel(self) -> "Any":
        if not self.dmacr & _DMACR_RXDMAE:
            return None
        for channel in _DMA_CHANNELS.values():
            if channel._accept(_UART_BASES[self.id], _RX_DREQ[self.id]):
                return channel
        return None

    @staticmethod
    def _check_pin(uart_id: int, pin: object, slot: int, name: str) -> None:
        # rp2040's rule (machine_uart.c:71-80, 314-323): a bank-0 GPIO, TX on pin 4k and RX on 4k+1, in its UART's
        # banks of eight (UART0 0-3, 12-19, 28-29; UART1 4-11, 20-27); mp_hal_get_pin_obj() refuses the WLAN pins.
        number = Pin._find(pin)
        if number >= _NUM_BANK0_GPIOS:
            raise ValueError("expecting a regular GPIO Pin")
        if number & 3 != slot or ((number + 4) & 8) >> 3 != uart_id:
            raise ValueError(f"bad {name} pin")

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

    def init(self, **settings: object) -> None:
        # Real UART.init(): re-runs uart_init() on the given settings, which re-enables the RX interrupts
        # and both DREQs (machine_uart.c:399-455; the ring buffers are kept); a new pin meets the same rule.
        for name, value in settings.items():
            if not hasattr(self, name) or name.startswith("_"):
                raise TypeError(f"unexpected keyword argument '{name}'")
            if name in ("tx", "rx"):
                self._check_pin(self.id, value, 0 if name == "tx" else 1, name.upper())
            setattr(self, name, value)
        self._reset_block()

    def ioctl(self, req: int, arg: int) -> int:
        # A real select.poll() first asks a stream for MP_STREAM_GET_FILENO (10) and on any non-error answer polls that fd
        # instead (extmod/modselect.c:252-266): rp2 answers EINVAL to all but POLL (machine_uart.c:694-697), and so does
        # this fake, so a real poll consults it and is counted rather than watching stdin.
        if req != self._MP_STREAM_POLL:
            return -errno.EINVAL
        UART.real_poll_queries += 1
        return self.poll_mask(arg)

    def plant_rx_error(self, bits: int) -> None:
        # Test-only: sets UARTRSR bits (OE 0x08, BE 0x04, FE 0x01); a break also receives one 0x00
        # character (RP2040 datasheet 4.2.8, Table 426).
        self._update()
        self.rsr |= bits & 0x0F
        if bits & _RSR_BE:
            self._route(0, is_break=True)

    def poll_mask(self, mask: int) -> int:
        # Test-only: the POLL answer for the events in `mask` (machine_uart.c:670-678), what LinkPoller and the contract read.
        if mask & select.POLLIN:
            self.rx_api_calls += 1
        self._update()
        ready = 0
        if (mask & select.POLLIN) and self.rx_queue:
            ready |= select.POLLIN
        if (mask & select.POLLOUT) and self.writable:
            ready |= select.POLLOUT
        return ready

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
    TEST_API = (
        "capacity", "silent", "drop_indices", "corrupt_indices", "truncate_after", "noise_before_next", "delay",
        "duplicate_next", "offered", "delivered", "dropped_overrun", "pending", "wire_log", "record", "shape",
    )  # fmt: skip  # wholly test-only: every public name

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
    # fault knobs. The fakes keep no concept of a frame: a write lands in the far side's
    # rx_queue and reads split where the reader asks. Never uses a real poll() - see LinkPoller.
    TEST_API = ("endpoints", "a_to_b", "b_to_a", "direction_from", "elapse", "release_delayed", "settle", "transmit")  # all
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
    # Bounded stand-in, never a real select.poll(): the fake's readiness must be scripted, not polled in real time
    # (CLAUDE.md "Known hang cause"). Installed by reassigning asy_uart_driver.UART.poller; reads poll_mask() each call.
    TEST_API = ("force_not_ready", "ipoll", "register", "unregister")  # wholly test-only
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
        event = self._uart.poll_mask(self._mask)
        return [(None, event)] if event else []

    def register(self, obj: object, mask: int = 0) -> None:
        pass

    def unregister(self, obj: object) -> None:
        pass


class Timer:
    # Not modelled: real time (a test fires a callback with trigger()), freq/tick_hz period maths, the 16-alarm pool.
    TEST_API = (
        "id", "all_timers", "raise_on_arm", "raise_on_arm_exc", "clock_ms", "arms", "trigger", "drop", "deinit_called",
        "callback", "period", "mode",
    )  # fmt: skip
    ONE_SHOT = 0
    PERIODIC = 1

    # Records every construction, so a test can assert the product reuses one preallocated Timer through init()
    # (SPECIFICATION.md F.1). Class-level, so it persists for the whole process: compare against a snapshot.
    all_timers: "ClassVar[list[Timer]]" = []

    # Test-only, off by default: real rp2 Timer.init() raises OSError(ENOMEM) on an exhausted alarm pool
    # (ports/rp2/machine_timer.c:107-110), and a bare Timer() never reaches that path at all.
    raise_on_arm = False
    # Which class init() then raises. src/ guards Timer.init() with `except (OSError, MemoryError)`,
    # a real alarm allocation being able to fail either way, so set this to MemoryError to prove the
    # sibling arm too. Both are class knobs the after-each reset restores.
    raise_on_arm_exc: "type[BaseException]" = OSError
    # A fake clock only tests advance; each init() records (clock_ms, period, mode) in its own `arms`, so a test
    # can read when the product armed a timer without patching any module's time source.
    clock_ms: "ClassVar[int]" = 0

    def __init__(
        self,
        id: int = -1,
        *,
        mode: "int | None" = None,
        callback: "Callable[[Timer], None] | None" = None,
        period: "int | None" = None,
        tick_hz: "int | None" = None,
        freq: "float | None" = None,
        hard: "bool | None" = None,
    ) -> None:
        # machine_timer.c:127-145: only the soft timer (-1) exists, and any keyword arms the timer at once.
        if id != -1:
            raise ValueError("Timer doesn't exist")
        self.id = id
        self.period = -1
        self.mode = self.PERIODIC
        self.callback: Callable[[Timer], None] | None = None
        self.deinit_called = False
        self.arms = _CallLog()  # (clock_ms, period, mode) per init(), the newest _LOG_MAXLEN
        if mode is not None or callback is not None or period is not None or tick_hz is not None or freq is not None or hard is not None:
            self.init(  # may raise OSError - propagates before this instance is registered
                mode=self.PERIODIC if mode is None else mode,
                callback=callback,
                period=-1 if period is None else period,
                tick_hz=1000 if tick_hz is None else tick_hz,
                freq=freq,
                hard=bool(hard),
            )
        Timer.all_timers.append(self)

    def deinit(self) -> None:
        self.callback = None
        self.deinit_called = True

    def drop(self) -> None:
        # One period elapsing with its soft callback lost to a full scheduler queue (Part F.1): a
        # ONE_SHOT never fires again, a PERIODIC simply fires next period.
        if self.mode == self.ONE_SHOT:
            self.callback = None

    def init(
        self,
        *,
        mode: int = PERIODIC,
        callback: "Callable[[Timer], None] | None" = None,
        period: int = -1,
        tick_hz: int = 1000,  # rp2's keyword, taken; the period maths is not modelled
        freq: "float | None" = None,  # likewise
        hard: bool = False,  # likewise: a callback here always runs where trigger() calls it
    ) -> None:
        # The keywords machine_timer_init_helper() takes (machine_timer.c:74-112); `period` keeps the value given.
        if Timer.raise_on_arm:
            if Timer.raise_on_arm_exc is OSError:
                raise OSError(errno.ENOMEM, "alarm pool exhausted")
            raise Timer.raise_on_arm_exc("simulated allocation failure")
        self.period = period
        self.mode = mode
        self.callback = callback
        self.deinit_called = False
        self.arms.append((Timer.clock_ms, period, mode))

    def trigger(self) -> None:
        # No real-hardware equivalent - lets test code fire a callback deterministically instead of
        # waiting on this fake's `period` (which is never actually scheduled against real time).
        # A ONE_SHOT is spent once its period elapses, as on rp2; a PERIODIC stays armed.
        callback = self.callback
        if self.mode == self.ONE_SHOT:
            self.callback = None
        if callback is not None:
            callback(self)


def _civil_seconds(year: int, month: int, day: int, hour: int, minute: int, second: int) -> int:
    # Seconds since 1970 by pure calendar arithmetic, as shared/timeutils' (no host mktime, which reads $TZ): an
    # out-of-range day carries over (2026-02-29 is 2026-03-01). Days from the civil date, March-based years.
    year -= 1 if month <= 2 else 0
    era = year // 400
    year_of_era = year - era * 400
    day_of_year = (153 * ((month + 9) % 12) + 2) // 5 + day - 1
    day_of_era = year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year
    return (era * 146097 + day_of_era - 719468) * 86400 + hour * 3600 + minute * 60 + second


_RTC_BOOT_SECONDS = _civil_seconds(2021, 1, 1, 0, 0, 0)  # what rp2's main() starts the RTC at (ports/rp2/main.c:143)


class RTC:
    # ports/rp2/machine_rtc.c:65-98: the setter takes exactly 8 fields and keeps seconds since the epoch (weekday and
    # subseconds ignored); the getter converts them back, the date normalised, the weekday recomputed (Monday 0),
    # subseconds 0. Not modelled: the clock advancing, and time.time() following a set.
    TEST_API = ("raise_exc",)
    raise_exc: "ClassVar[BaseException | None]" = None  # test-only fault injection, a class knob like Timer.raise_on_arm
    _seconds: "ClassVar[int]" = _RTC_BOOT_SECONDS  # class state: one peripheral, as rp2's singleton RTC (:48)

    def __init__(self) -> None:
        pass  # RTC() takes no argument (machine_rtc.c:52)

    def datetime(self, dt: "tuple[int, ...] | None" = None) -> "tuple[int, ...] | None":
        if RTC.raise_exc is not None:
            raise RTC.raise_exc
        if dt is None:
            tm = time.gmtime(RTC._seconds)  # the Unix port's gmtime() adds a ninth field, so index it
            return (tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0)
        fields = tuple(dt)
        if len(fields) != 8:
            raise ValueError("tuple/list has wrong length")  # mp_obj_get_array_fixed_n(), py/obj.c:473
        RTC._seconds = _civil_seconds(fields[0], fields[1], fields[2], fields[4], fields[5], fields[6])
        return None


_WDT_TIMEOUT_MAX_MS = 8388  # ports/rp2/machine_wdt.c:32-38: the RP2040's 24-bit counter, 0xffffff / 2 / 1000


class WDT:
    # Not modelled: the countdown itself (a missed feed resets nothing here), rp2's static WDT object.
    TEST_API = ("id", "timeout", "feed_count", "feed_times")

    def __init__(self, id: int = 0, timeout: int = 5000) -> None:
        # machine_wdt.c:47-57: only id 0 exists; the timeout goes through a uint32_t, so a negative one exceeds the cap.
        if id != 0:
            raise ValueError(f"WDT({id}) doesn't exist")
        if not 0 <= timeout <= _WDT_TIMEOUT_MAX_MS:
            raise ValueError(f"timeout exceeds {_WDT_TIMEOUT_MAX_MS}")
        self.id = id
        self.timeout = timeout
        self.feed_count = 0
        self.feed_times = _CallLog()  # time.ticks_ms() at each feed, the newest _LOG_MAXLEN: gaps between feeds read back

    def feed(self) -> None:
        self.feed_count += 1
        self.feed_times.append(time.ticks_ms())


class _Mem32:
    # machine.mem32: 32-bit peripheral register access (extmod/machine_mem.c). Models the two reset registers and the
    # UART blocks' UARTRSR/UARTECR, UARTIMSC and UARTDMACR of the latest UART per id; any other address raises
    # ValueError ("not modelled"). Every access is recorded in `log` as ("read"|"write", address, value).
    TEST_API = ("log",)

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
_WATCHDOG_REASON = 0x40058008  # WATCHDOG_BASE + 0x08: bit 0 TIMER, bit 1 FORCE (RP2040 datasheet 4.7.6, Table 548)
_CHIP_RESET = 0x40064008  # VREG_AND_CHIP_RESET_BASE + 0x8: bit 8 HAD_POR, 16 HAD_RUN, 20 HAD_PSM_RESTART (RP2040 datasheet 2.10.6)
_REASON_FORCE = 0x2  # watchdog_reboot(..., 0) sets the trigger bit (pico-sdk watchdog.c:65-66)
_HAD_POR = 0x100
# Test-only: what the two registers read, the power-on pair until power_on()/reset()/bootloader() move them.
watchdog_reason_value = 0
chip_reset_value = _HAD_POR


# rp2's reset causes (ports/rp2/modmachine.c:57-58, 65-66 at v1.29.0); reset_cause() answers the module value.
PWRON_RESET = 1
WDT_RESET = 3
reset_cause_value = PWRON_RESET
# rp2's two backup regions, scratch[0..3] and scratch[5..7] (ports/rp2/machine_mem_backup.c:38-41): one static
# view each, the same object on every call, kept across reset() as the watchdog scratch registers are.
_REGIONS = (array("I", [0, 0, 0, 0]), array("I", [0, 0, 0]))
_REGION_VIEWS = (memoryview(_REGIONS[0]), memoryview(_REGIONS[1]))


class SimulatedRebootError(BaseException):
    # Test-only, the twin's names: what reset()/bootloader() raise, since the real ones never return. A BaseException,
    # so no `except Exception` in the product swallows it; microtest reports one escaping a test as that test's FAIL.
    pass


class SimulatedResetError(SimulatedRebootError):
    pass


class SimulatedBootloaderEntryError(SimulatedRebootError):
    pass


# Real reset()/bootloader() never return: the fake records the call, sets the cause rp2 then reports (watchdog_reboot(),
# so WDT_RESET), and raises so no later line runs.
reset_count = 0
bootloader_count = 0


# The module's test-only names, beside each class's own TEST_API.
TEST_API = (
    "reset_count", "bootloader_count", "reset_cause_value", "watchdog_reason_value", "chip_reset_value", "power_on",
    "SimulatedRebootError", "SimulatedResetError", "SimulatedBootloaderEntryError", "reset_test_state",
)  # fmt: skip


def bootloader() -> None:
    global bootloader_count, reset_cause_value, watchdog_reason_value
    bootloader_count += 1
    reset_cause_value = WDT_RESET
    watchdog_reason_value = _REASON_FORCE
    raise SimulatedBootloaderEntryError("machine.bootloader() never returns")


def mem_backup(region: int = 0) -> "Any":
    # extmod/machine_mem.c:135-148: one region's view, or (for -1) a tuple of every region's; any other index
    # outside the table raises. Typed Any because the real answer's type depends on the argument.
    if region == -1:
        return _REGION_VIEWS
    if region < 0 or region >= len(_REGION_VIEWS):
        raise ValueError("invalid region")
    return _REGION_VIEWS[region]


def power_on() -> None:
    # Test-only: a power cycle clears both regions, reports PWRON_RESET and leaves REASON 0 with HAD_POR set.
    global reset_cause_value, watchdog_reason_value, chip_reset_value
    for region in _REGIONS:
        for i in range(len(region)):
            region[i] = 0
    reset_cause_value = PWRON_RESET
    watchdog_reason_value = 0
    chip_reset_value = _HAD_POR


def reset() -> None:
    global reset_count, reset_cause_value, watchdog_reason_value
    reset_count += 1
    reset_cause_value = WDT_RESET
    watchdog_reason_value = _REASON_FORCE  # CHIP_RESET is left as it was: a watchdog reset clears no HAD_* bit
    raise SimulatedResetError("machine.reset() never returns")


def reset_cause() -> int:
    return reset_cause_value


def reset_test_state() -> None:
    # Every process-wide knob back to its default after each test (registered below), lists cleared in place so a
    # reference product code holds stays valid; a real select.poll() over a UART fake fails the test it ran in.
    global reset_count, bootloader_count
    polled = UART.real_poll_queries
    Timer.all_timers.clear()
    Timer.raise_on_arm = False
    Timer.raise_on_arm_exc = OSError
    Timer.clock_ms = 0
    RTC.raise_exc = None
    RTC._seconds = _RTC_BOOT_SECONDS
    UART.would_have_blocked_bytes = 0
    UART.real_poll_queries = 0
    UART._live.clear()
    for channel in list(_DMA_CHANNELS.values()):
        channel.close()  # each claimed rp2.DMA channel's finaliser, as a soft reset runs it (rp2_dma.c:637-673)
    Pin.reset_registry()
    I2C.reset_registry()
    I2C.raise_on_construct = None
    mem32.log.clear()
    reset_count = 0
    bootloader_count = 0
    power_on()
    if polled:
        raise AssertionError(f"a real select.poll() queried a UART fake {polled} times")


microtest.after_each(reset_test_state)
