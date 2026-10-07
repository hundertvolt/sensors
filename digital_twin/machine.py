"""Digital-twin fake `machine` module - real-time-firing `Timer`, I2C/SPI wired to per-address chip simulators via `configure_wiring()` (generic, buildgen-derived plan) or `configure_i2c_wiring()` (the "wozi"/"dev" legacy sugar), deliberately independent of `tests/machine.py`.
See `digital_twin/README.md`'s "What's here" section for the full wiring/`Pin`-identity account."""

import asyncio
import errno
import io
import json
import select
import time
from array import array
from collections import deque

_SPI_DMA_MIN_SIZE = 32  # ports/rp2/machine_spi.c's own dma_min_size_threshold - see SPI._maybe_overrun()
_LOG_MAXLEN = 200  # I2C.log/SPI.log's own bound - see digital_twin/README.md for the real memory
# leak this avoids; same "keep last N" convention asy_print_log.py's own PrintLogHistory uses.

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Any, Literal, Protocol, overload

    from _fram_chip import FramChip  # lazy-imported at runtime inside _wire_spi_device()

    class _RandomSource(Protocol):
        # Structural stand-in for the `random` module (the default) or a seeded random.Random.
        # Declares the union of what the wired chip fakes each ask for through their own narrower
        # _RandomSource, since configure_random_source() hands one object to all of them.
        def uniform(self, a: float, b: float) -> float: ...
        def randint(self, a: int, b: int) -> int: ...
        def getrandbits(self, k: int) -> int: ...

    class _I2CDevice(Protocol):
        # The four transaction shapes this bus forwards to a wired chip fake. Each fake implements
        # only the subset its real counterpart answers (I2C.devices stays Any-valued so tests can
        # still reach chip-specific state), so this describes the bus's expectation, not a guarantee.
        def handle_writeto(self, data: bytes) -> None: ...
        def handle_readfrom_into(self, nbytes: int) -> bytes: ...
        def handle_readfrom_mem(self, reg_addr: int, nbytes: int) -> bytes: ...
        def handle_writeto_mem(self, reg_addr: int, data: bytes) -> None: ...


_VALUE_LOG_MAXLEN = 64  # a line's value log: a chip-select toggles on every SPI transaction
_MEM32_LOG_MAXLEN = 64  # likewise for register accesses: a DMA reader reads UARTRSR at every fill-level read
_WIRE_LOG_MAXLEN = 4096  # bytes of a link direction's wire log kept; its `dropped` counts the rest
_WIRE_CHUNK = 512  # bytes per storage chunk of a wire log


class _BoundedLog:
    # A record that grows to `maxlen` entries, then overwrites its oldest in place: fixed occupancy once
    # full, so a long run neither grows the heap nor frees half of it at once (a swing a heap test reads
    # as retention). Reads - len(), iteration, [i], slices, == - see the entries oldest first.
    def __init__(self, maxlen: int = _LOG_MAXLEN) -> None:
        self.maxlen = maxlen
        self.dropped = 0
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
    # The bytes a link direction delivered, kept the way _BoundedLog keeps entries: up to `maxlen`, then
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


class Pin:
    IN = 0
    OUT = 1
    OPEN_DRAIN = 2  # ports/rp2/machine_pin.h:34-37 (v1.29.0), as IN/OUT/ALT
    ALT = 3
    ALT_I2C = 3  # GPIO_FUNC_I2C (pico-sdk io_bank0.h; machine_pin.c:513)
    _ALT_SIO = 5  # GPIO_FUNC_SIO, rp2's alt default (machine_pin.c:247)
    # Real rp2 values (ports/rp2/machine_pin.c at v1.29.0: GPIO_PULL_UP 1, GPIO_PULL_DOWN 2).
    PULL_UP = 1
    PULL_DOWN = 2
    IRQ_FALLING = 0x04
    IRQ_RISING = 0x08

    _registry: "dict[int, Pin]" = {}
    # Per GPIO id: the level the outside world puts on the line (twin-only test knob, default 1: the
    # bus pull-ups) and every level the code drove onto it.
    _external: "dict[int, int | Callable[[int, _BoundedLog], int]]" = {}
    _value_logs: "dict[int, _BoundedLog]" = {}
    _initialized: bool

    def __init__(self, id: int, mode: int = -1, pull: int = -1, *, value: object = None, alt: int = _ALT_SIO) -> None:
        if not self._initialized:
            self.id = id
            self.mode = -1
            self.pull = -1
            self.alt = self._ALT_SIO
            self._value = 0
            self._irq_handler: Callable[[Pin], None] | None = None
            self._irq_trigger = self.IRQ_FALLING | self.IRQ_RISING
            self._irq_hard = False
            self._initialized = True
        # Re-binding to an already-registered physical pin applies init()-style settings
        # (leave-unchanged-if-omitted) without wiping the pin's current electrical state.
        self.init(mode, pull, value=value, alt=alt)

    def __new__(cls, id: int, *_args: object, **_kwargs: object) -> "Pin":
        if not isinstance(id, int):
            raise TypeError("Pin id must be an int")
        if not (0 <= id <= 28):
            raise ValueError("invalid pin")
        existing = cls._registry.get(id)
        if existing is not None:
            return existing
        instance = super().__new__(cls)
        instance._initialized = False
        cls._registry[id] = instance
        return instance

    def _drive(self, level: int) -> None:
        self._value = level
        Pin.value_log(self.id).append(level)

    def _line(self) -> int:
        level = Pin._external.get(self.id, 1)
        if callable(level):
            level = level(self.id, Pin.value_log(self.id))
        return 1 if level else 0

    @classmethod
    def set_external_level(cls, id: int, level: "int | Callable[[int, _BoundedLog], int]") -> None:
        # Twin-only test knob: what the outside world drives onto line `id`; a callable is asked on every
        # read with (id, the line's value log), so a test can script a slave releasing SDA after k clocks.
        cls._external[id] = level

    def init(self, mode: int = -1, pull: int = -1, *, value: object = None, alt: int = _ALT_SIO) -> None:
        # value= sets the level before the mode applies (machine_pin.c:264-287), and OPEN_DRAIN given no
        # value is released (mphalport.h:158-168); an omitted/-1 mode or pull leaves the setting as it is.
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
        # Test-only: real GPIO pins never "reset" between test functions the way this registry
        # needs to for isolation - mirrors tests/machine.py's own Timer.all_timers.clear() convention.
        cls._registry.clear()
        cls._external.clear()
        cls._value_logs.clear()

    def simulate_edge(self, new_value: object) -> None:
        # Twin-only test knob: an outside transition on the line (it sets the line level and the latch),
        # firing the handler only when the level read changes in the direction irq() listens for.
        old = self.value()
        level = 1 if new_value else 0
        self._value = level
        Pin._external[self.id] = level
        new = self.value()
        if old == new:
            return
        edge = self.IRQ_RISING if new else self.IRQ_FALLING
        if (self._irq_trigger & edge) and self._irq_handler is not None:
            self._irq_handler(self)

    def toggle(self) -> None:
        self._drive(0 if self._value else 1)

    def value(self, x: object = None) -> "int | None":
        # rp2 reads the pad: an output what it drives, an open-drain pin the wired-AND of its drive and
        # the line. An input with no planted level and no pull-up reads its latch, which simulate_edge()
        # sets too, so a chip's RDY/INT edge reaches a driver that reads its pin.
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
    def value_log(cls, id: int) -> "_BoundedLog":
        # Twin-only test knob: the last levels value()/on()/off()/toggle() drove onto line `id`, oldest first.
        log = cls._value_logs.get(id)
        if log is None:
            log = cls._value_logs[id] = _BoundedLog(_VALUE_LOG_MAXLEN)
        return log


_random_source: "_RandomSource | None" = None


def configure_random_source(source: "_RandomSource | None") -> None:
    # The same module-level hook as configure_fram_state_path() below, applied to value walks: called
    # once before i2c0/i2c1 are constructed, by an entry point wanting every chip's walk to share one
    # seeded random.Random (launch.py's --seed). None leaves each chip on the un-seeded module.
    global _random_source
    _random_source = source


_scd30_state_path: "str | None" = None
_current_scd30_chip: "Any | None" = None


def configure_scd30_state_path(path: "str | None") -> None:
    # configure_fram_state_path()'s pattern applied to the SCD30's NVM-persisted settings rather
    # than FRAM contents. Called once by the entry point, before anything constructs i2c0; None,
    # the default, means in-memory only.
    global _scd30_state_path
    _scd30_state_path = path


def flush_scd30() -> None:
    # Called once, in a try/finally around asyncio.run(main()), alongside flush_fram() - see
    # _scd30_chip.py's own module docstring for what is/isn't persisted and why.
    if _current_scd30_chip is not None:
        _current_scd30_chip.save_state()


_wiring_plan: "dict[str, Any] | None" = None  # None until configure_wiring()/configure_i2c_wiring()
# runs, or a bus is actually constructed - see _current_wiring_plan() below.


def configure_wiring(plan: "dict[str, Any]") -> None:
    # Called once, before build_system()-equivalent code constructs i2c0/i2c1/spi0 - a plain dict in
    # buildgen.twin_wiring.compute_twin_wiring()'s own shape. Replaces the whole plan outright, the
    # same "last configure_*() call before construction wins" convention every hook here already uses.
    global _wiring_plan
    if "buses" not in plan or "spi" not in plan:
        raise ValueError("wiring plan must be a dict with 'buses' and 'spi' keys - see buildgen.twin_wiring.compute_twin_wiring()'s own docstring for the shape")
    _wiring_plan = plan
    _I2C_OBJECTS.clear()  # a new wiring is a new board: the next I2C(id) wires fresh chips
    for channel in list(_DMA_CHANNELS.values()):
        channel.close()  # and its DMA channels are free, as a soft reset's finalisers leave them


def configure_i2c_wiring(profile: str) -> None:
    # Legacy sugar over configure_wiring(), kept for tests: no real entry point calls it, since
    # run_generic_integration.py passes a full wiring-plan dict. Called once, before anything
    # constructs i2c0/i2c1.

    # It loads the profile's own generated wiring plan, derived from devices/<profile>.toml, so
    # the TOML stays the only source of truth - never a hand-typed literal. Validated eagerly
    # here so a typo surfaces at the call site instead of NAKing every later transaction.
    if profile not in ("wozi", "dev"):
        raise ValueError(f"unknown I2C wiring profile {profile!r} - expected 'wozi' or 'dev'")
    with open(f"build/generated_src/sensortask_{profile}_wiring_plan.json") as f:
        configure_wiring(json.load(f))


def _current_wiring_plan() -> "dict[str, Any]":
    # Lazily defaults to wozi's generated plan the first time a caller constructs a bus without
    # configuring wiring, matching the old eager default exactly - but loaded on first use, since
    # this file must stay importable before build/generated_src/ exists.
    if _wiring_plan is None:
        configure_i2c_wiring("wozi")
    return _wiring_plan  # type: ignore[return-value]  # configure_i2c_wiring() above always sets it


def _build_i2c_chip(attachment: "dict[str, Any]") -> "Any":
    # Dispatches on the wiring plan's "driver" string - the twin's hand-maintained chip-fake
    # catalog, a new chip type still needing one written. The return type is Any rather than
    # _I2CDevice because no single fake implements all four of that Protocol's methods.
    global _current_scd30_chip
    driver = attachment["driver"]
    if driver == "scd30":
        from _scd30_chip import Scd30Chip

        chip = Scd30Chip(rdy_pin=Pin(attachment["irq_pin"], mode=Pin.IN), random_source=_random_source, state_path=_scd30_state_path)
        _current_scd30_chip = chip
        return chip
    if driver == "sgp40":
        from _sgp40_chip import Sgp40Chip

        return Sgp40Chip(random_source=_random_source)
    if driver == "bmp3xx":
        from _bmp3xx_chip import Bmp3xxChip

        return Bmp3xxChip(random_source=_random_source)
    if driver == "isl29125":
        from _isl29125_chip import Isl29125Chip

        return Isl29125Chip(random_source=_random_source, int_pin=Pin(attachment["irq_pin"], mode=Pin.IN))
    raise ValueError(f"digital twin has no I2C chip fake for driver {driver!r} - add one to machine._build_i2c_chip()")


def _wire_i2c_devices(bus_id: int) -> "dict[int, Any]":
    return {attachment["address"]: _build_i2c_chip(attachment) for attachment in _current_wiring_plan()["buses"].get(f"i2c{bus_id}", [])}


_I2C_OBJECTS: "dict[int, I2C]" = {}


class I2C:
    # One static object per bus id, as ports/rp2/machine_i2c.c:50-53, 87 (v1.29.0): a re-construction
    # re-initialises the controller and keeps the wired chips, their queued faults and the log, until a
    # configure_*wiring() call starts a new board.
    _wired: bool

    def __init__(self, id: int, *, scl: Pin, sda: Pin, freq: int = 400000, timeout: int = 50000) -> None:
        if not self._wired:
            self.deinit_called = False
            self.log: deque[tuple[Any, ...]] = deque((), _LOG_MAXLEN)
            self.devices = _wire_i2c_devices(id)  # public: tests reach a wired chip via i2c.devices[addr]
            # Twin-only test knob: address -> the ACK count the next write to it reports, a data or
            # register byte the chip NACKed (pico-sdk i2c.c:229-231); the chip takes none of that write.
            self.nack_after: dict[int, int] = {}
            self._pointers: dict[int, int] = {}  # per register chip: the register the next read starts at
            self._wired = True
            _I2C_OBJECTS[id] = self  # after wiring: a lazy first configure_i2c_wiring() clears the table
        self.id = id
        self.scl = scl
        self.sda = sda
        self.freq = freq
        self.timeout = timeout
        self.log.append(("init", freq, timeout))

    def __new__(cls, id: int, *_args: object, **_kwargs: object) -> "I2C":
        existing = _I2C_OBJECTS.get(id)
        if existing is not None:
            return existing
        bus = super().__new__(cls)
        bus._wired = False
        return bus

    def _device_or_nak(self, address: int) -> "_I2CDevice":
        device: _I2CDevice | None = self.devices.get(address)
        if device is None:
            raise OSError(errno.EIO, "no ACK from device")
        return device

    def deinit(self) -> None:
        # Real rp2 I2C.deinit() exists only from 1.29, and even there the port's protocol slot is
        # NULL - a silent no-op leaving the peripheral and pins as they were (Part F.5). Every bus
        # operation keeps working here on purpose; the flag only records the call.
        self.deinit_called = True

    def readfrom_into(self, address: int, buf: object, stop: bool = True) -> None:
        device = self._device_or_nak(address)
        nbytes = len(buf)  # type: ignore[arg-type]
        register_chip = getattr(device, "REGISTER_ADDRSIZE", 0)
        data = device.handle_readfrom_mem(self._pointers.get(address, 0), nbytes) if register_chip else device.handle_readfrom_into(nbytes)
        buf[:] = data  # type: ignore[index]
        self.log.append(("readfrom_into", address, data, stop))

    def readfrom_mem(self, address: int, memaddr: int, nbytes: int, *, addrsize: int = 8) -> bytes:
        device = self._device_or_nak(address)
        data = device.handle_readfrom_mem(memaddr, nbytes)
        self.log.append(("readfrom_mem", address, memaddr, nbytes, addrsize))
        return data

    def readfrom_mem_into(self, address: int, memaddr: int, buf: object, *, addrsize: int = 8) -> None:
        # Delegates, so fault injection (--fault <chip>:readfrom_mem) and the bus log stay one
        # implementation regardless of which of the two read forms the driver under test calls.
        buf[:] = self.readfrom_mem(address, memaddr, len(buf), addrsize=addrsize)  # type: ignore[index,arg-type]

    def scan(self) -> "list[int]":
        return sorted(self.devices.keys())

    def writeto(self, address: int, buf: object, stop: bool = True) -> int:
        data = bytes(buf)  # type: ignore[call-overload]
        if address == 0x00:  # general call - every device may listen, tolerate silently
            self.log.append(("writeto", address, data, stop))
            return len(data)
        device = self._device_or_nak(address)
        acked = self.nack_after.pop(address, len(data))
        if acked < len(data):
            self.log.append(("writeto", address, data, stop))
            return acked
        # A chip declaring REGISTER_ADDRSIZE is register-addressed: address bytes plus payload are a
        # register write, address bytes alone set the pointer the next read starts at, nothing is the probe.
        n = getattr(device, "REGISTER_ADDRSIZE", 0) // 8
        if n and len(data) >= n:
            register = int.from_bytes(data[:n], "big")
            if len(data) > n:
                device.handle_writeto_mem(register, data[n:])
            self._pointers[address] = register
        else:
            device.handle_writeto(data)
        self.log.append(("writeto", address, data, stop))
        return len(data)

    def writeto_mem(self, address: int, memaddr: int, buf: object, *, addrsize: int = 8) -> None:
        device = self._device_or_nak(address)
        device.handle_writeto_mem(memaddr, bytes(buf))  # type: ignore[call-overload]
        self.log.append(("writeto_mem", address, memaddr, bytes(buf), addrsize))  # type: ignore[call-overload]


_fram_state_path: "str | None" = None
_current_fram_chip: "Any | None" = None


def configure_fram_state_path(path: "str | None") -> None:
    # Called once, before build_system() constructs spi0, by the twin's entry points (launch.py, run_generic_integration.py) -
    # src/ never calls this: zero twin-awareness in src/ (owner, 2026-09-26: 'zero artifacts specifically added for testing').
    # None (the default) means "in-memory only, no persistence".
    global _fram_state_path
    _fram_state_path = path


def flush_fram() -> None:
    # Called once, in a try/finally around asyncio.run(main()), by whatever entry point Step 5
    # writes - see _fram_chip.py's own module docstring for why this must be explicit rather than
    # a self-registered signal/atexit handler.
    if _current_fram_chip is not None:
        _current_fram_chip.save_state()


_DEV_FRAM_SIZE = 0x40000  # MB85RS2MTA, 256KB - sensortask_dev.py's own FRAMManager(spi0, 5, max_size=0x40000, ...)
_DEV_FRAM_RDID = bytes([0x04, 0x7F, 0x48, 0x03])  # manufacturer=Fujitsu, cont_code, product ID 0x4803 - asy_fram_driver.py's own _KNOWN_PRODUCT_IDS[0x40000], datasheets/fram/MB85RS2MTA-DS501-00032-3v0-E.pdf p.10

# Real chip-model identity (the RDID bytes) isn't a TOML/DeviceModel fact - only max_size is - so
# it's keyed by size as the best available proxy (unique today: 8KB MB85RS64V vs 256KB MB85RS2MTA).
# Any size not listed falls back to FramChip's own default RDID (MB85RS64V's - wozi's own chip).
_FRAM_RDID_BY_MAX_SIZE: "dict[int, bytes]" = {_DEV_FRAM_SIZE: _DEV_FRAM_RDID}


def _wire_spi_device(bus_id: int) -> "FramChip | None":
    global _current_fram_chip
    attachment = _current_wiring_plan()["spi"].get(f"spi{bus_id}")
    if attachment is None:
        return None
    from _fram_chip import FramChip

    max_size = attachment["max_size"]
    chip = FramChip(size=max_size, state_path=_fram_state_path, rdid_response=_FRAM_RDID_BY_MAX_SIZE.get(max_size))
    _current_fram_chip = chip
    return chip


class SPI:
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
        self.log: deque[tuple[Any, ...]] = deque((), _LOG_MAXLEN)
        self.device = _wire_spi_device(id)  # public: tests reach the wired chip via spi.device
        # 1.29 added an RX-overrun check to rp2's SPI transfer path, reached only by READING
        # 32+ bytes (Part F.5.2). Modelled here rather than on the chip's FaultInjector because
        # it belongs to the port, not the device: sticky, plus a counted transient form.
        self.rx_overrun = False
        self.rx_overrun_remaining = 0

    def init(
        self,
        baudrate: int = -1,
        *,
        polarity: int = -1,
        phase: int = -1,
        bits: int = -1,
        firstbit: int = -1,
    ) -> None:
        if firstbit == self.LSB:
            raise NotImplementedError("LSB")  # real rp2 hardware SPI is MSB-first only
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

    def deinit(self) -> None:
        # Same NULL-slot no-op as I2C.deinit() above, and on rp2 SPI it has always been one
        # (SPECIFICATION.md Part F.5) - the flag only records that the call was forwarded.
        self.deinit_called = True

    def write(self, buf: object) -> None:
        data = bytes(buf)  # type: ignore[call-overload]
        if self.device is not None:
            self.device.write(data)
        self.log.append(("write", data))

    def readinto(self, buf: "bytearray | memoryview", write_value: int = 0x00) -> None:
        self._maybe_overrun(len(buf))
        if self.device is not None:
            self.device.readinto(buf)
        else:
            buf[:] = bytes(len(buf))
        self.log.append(("readinto", len(buf), write_value))

    def _maybe_overrun(self, nbytes: int) -> None:
        # Below DMA_MIN_SIZE_THRESHOLD (32 in ports/rp2/machine_spi.c) a transfer takes the
        # blocking software path, which has no overrun check - so a short read never raises here.
        if nbytes < _SPI_DMA_MIN_SIZE:
            return
        if self.rx_overrun:
            raise OSError(errno.EIO, "SPI RX overrun")
        if self.rx_overrun_remaining > 0:
            self.rx_overrun_remaining -= 1
            raise OSError(errno.EIO, "SPI RX overrun")

    def write_readinto(self, buffer_out: object, buffer_in: "bytearray | memoryview") -> None:
        if len(buffer_out) != len(buffer_in):  # type: ignore[arg-type]
            raise ValueError("buffers must be the same length")
        self.write(buffer_out)
        self.readinto(buffer_in)



_UART_BITS_PER_BYTE = 10  # 8N1 on the wire: one start bit, eight data bits, one stop bit
# Claimed rp2.DMA channels by number: digital_twin/rp2.py registers here, so a UART finds the channel draining it.
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
# Bytes that have been written but whose wire time has not elapsed yet. Must comfortably exceed a
# whole stop-and-wait exchange's worth of frames: an ACK still in flight when the next frame is
# written would otherwise overflow this and truncate that frame mid-transmission.
_UART_INFLIGHT_MAX = 4096


class _LinkDirection:
    # One direction of a UARTLink. Same knobs and same semantics as tests/machine.py's own
    # _LinkDirection (both are held to tests/_uart_link_contract.py); the difference is fidelity -
    # this one schedules delivery by real wire time instead of depositing synchronously.
    def __init__(self, capacity: int, baudrate: int) -> None:
        self.capacity = capacity
        self.baudrate = baudrate
        self.silent = False
        self.drop_indices: set[int] = set()
        self.corrupt_indices: dict[int, int] = {}
        self.truncate_after: int | None = None
        self.noise_before_next = bytearray()
        self.delay = False
        self.duplicate_next = 0
        self.offered = 0
        self.delivered = 0
        self.dropped_overrun = 0
        self.pending = bytearray()  # held by the delay knob
        self.in_flight: deque[tuple[int, int]] = deque((), _UART_INFLIGHT_MAX)  # (due_us, byte)
        self.wire_log = _WireLog(_WIRE_LOG_MAXLEN)  # the newest bytes that reached the destination

    def record(self, byte: int) -> None:
        # Counts and logs a byte that reached the destination.
        self.delivered += 1
        self.wire_log.append(byte)

    def byte_time_us(self) -> int:
        return (_UART_BITS_PER_BYTE * 1_000_000) // max(self.baudrate, 1)

    def shape(self, data: bytes) -> bytearray:
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


def attach_crossover_jumper(fake_a: "UART", fake_b: "UART") -> "tuple[UARTLink, LinkPoller, LinkPoller]":
    # Models the dev bench's permanent GP0<->GP9 / GP1<->GP8 jumper (tests_hardware/README.md 'The dev
    # bench'): the twin's dev graph builds both ends but joins neither. The returned pollers are bounded,
    # a real select.poll() never re-evaluating a Python object's ioctl() (CLAUDE.md's known CI hang).
    return UARTLink(fake_a, fake_b), LinkPoller(fake_a), LinkPoller(fake_b)


class UARTLink:
    # Byte-level crossover between two UART fakes: one FIFO per direction, the mock link's fault
    # knobs, plus real wire time - a byte becomes readable only once its transmission would have
    # finished at the configured baud rate, so a drain or cooldown cannot pass wrongly.
    def __init__(self, uart_a: "UART", uart_b: "UART", capacity_a_to_b: int | None = None, capacity_b_to_a: int | None = None) -> None:
        if uart_a._link is not None or uart_b._link is not None:
            raise ValueError("UART already attached to a link")
        if uart_a is uart_b:
            raise ValueError("a link needs two distinct endpoints")
        self.endpoints = (uart_a, uart_b)
        self.a_to_b = _LinkDirection(uart_b.rxbuf if capacity_a_to_b is None else capacity_a_to_b, uart_a.baudrate)
        self.b_to_a = _LinkDirection(uart_a.rxbuf if capacity_b_to_a is None else capacity_b_to_a, uart_b.baudrate)
        # Wire time is a plain microsecond offset from this epoch via ticks_diff(), not raw ticks:
        # the arithmetic below mixes it with byte durations and ticks values are opaque. A run
        # longer than ticks_us()' period would need re-anchoring; no test comes close.
        self._epoch_us = time.ticks_us()
        self._next_free_us = [0, 0]  # per direction: when the wire is idle again
        uart_a._link = self
        uart_b._link = self

    def _advance(self) -> None:
        # Moves every byte whose wire time has elapsed into the destination FIFO. Called from each
        # endpoint's own read path, so time only ever advances as the consumer actually runs.
        now = self._now_us()
        for index, direction in ((0, self.a_to_b), (1, self.b_to_a)):
            dest = self.endpoints[1 - index]
            while direction.in_flight and direction.in_flight[0][0] <= now:
                _due, byte = direction.in_flight.popleft()
                if not dest.imsc & _IMSC_RX_IRQ:
                    dest._route(byte)  # no interrupt: into a DMA ring or the FIFO
                    direction.record(byte)
                    continue
                if len(dest.rx_queue) >= direction.capacity:
                    direction.dropped_overrun += 1
                    continue
                dest.rx_queue.append(byte)
                direction.record(byte)

    def _index(self, uart: "UART") -> int:
        return 0 if uart is self.endpoints[0] else 1

    def _now_us(self) -> int:
        return time.ticks_diff(time.ticks_us(), self._epoch_us)

    def _schedule(self, index: int, direction: "_LinkDirection", data: bytearray) -> None:
        now = self._now_us()
        due = max(now, self._next_free_us[index])
        step = direction.byte_time_us()
        for byte in data:
            due += step
            # A full in-flight queue is a receive overrun by another name - counted and dropped, never
            # raised into the driver. Checked here: a full MicroPython deque drops its OLDEST entry silently.
            if len(direction.in_flight) >= _UART_INFLIGHT_MAX:
                direction.dropped_overrun += 1
            else:
                direction.in_flight.append((due, byte))
        self._next_free_us[index] = due

    def detach(self, uart: "UART") -> None:
        # Breaks the link for both ends at once: a half-attached link would deliver into an
        # endpoint nothing reads from, which is the mis-routing this exists to prevent.
        if uart not in self.endpoints:
            return
        for endpoint in self.endpoints:
            endpoint._link = None
        # Rebound rather than cleared: MicroPython's deque has no clear().
        self.a_to_b.in_flight = deque((), _UART_INFLIGHT_MAX)
        self.b_to_a.in_flight = deque((), _UART_INFLIGHT_MAX)

    def direction_from(self, uart: "UART") -> "_LinkDirection":
        if uart not in self.endpoints:
            raise ValueError("UART is not an endpoint of this link")
        return self.a_to_b if self._index(uart) == 0 else self.b_to_a

    def direction_to(self, uart: "UART") -> "_LinkDirection":
        if uart not in self.endpoints:
            raise ValueError("UART is not an endpoint of this link")
        return self.b_to_a if self._index(uart) == 0 else self.a_to_b

    def elapse(self, ms: int) -> None:
        # Fidelity seam for the shared contract's DMA checks: real wire time passes, nothing awaits.
        time.sleep_ms(ms)
        self._advance()

    def release_delayed(self) -> int:
        released = 0
        for index, direction in ((0, self.a_to_b), (1, self.b_to_a)):
            if not direction.pending:
                continue
            data = direction.pending
            direction.pending = bytearray()
            released += len(data)
            self._schedule(index, direction, data)
        return released

    def settle(self) -> None:
        # Blocks until every in-flight byte has landed - the fidelity seam the shared contract
        # calls so a synchronous assertion does not race the wire (tests/_uart_link_contract.py).
        while self.a_to_b.in_flight or self.b_to_a.in_flight:
            self._advance()
            if self.a_to_b.in_flight or self.b_to_a.in_flight:
                time.sleep_us(self.a_to_b.byte_time_us() + 1)

    def transmit(self, src: "UART", data: bytes) -> None:
        index = self._index(src)
        direction = self.direction_from(src)
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
        self._schedule(index, direction, shaped)


class UART(io.IOBase):
    # Independent of tests/machine.py's own UART (see this module's docstring) but held to the same
    # semantics by tests/_uart_link_contract.py. io.IOBase lets init() register it with a real
    # select.poll(); tests still swap .poller for a bounded stand-in (CLAUDE.md's known hang cause).
    #
    # Receive model: with RXIM/RTIM set (every construction and init()) the RX interrupt moves each byte
    # into rx_queue, machine.UART's own buffer, as its wire time elapses. With both cleared, each byte goes
    # to a DMA channel draining this UART, else to the 32-byte FIFO, past which it sets OE and is lost.
    _MP_STREAM_POLL = 3  # py/stream.h
    _MAX_BUFFER_SIZE = 32766
    _UART_INVERT_MASK = 3

    # One live instance per peripheral id. Real machine.UART() re-inits the peripheral rather than
    # refusing, so a second instance on one id supersedes the first; the twin deinits and detaches
    # the loser so it cannot keep delivering to a stale peer - the mis-routing this models.
    _live: "dict[int, UART]" = {}
    superseded = 0  # how many instances have been displaced this way, for a test to assert on
    # Bytes a read asked for that had not arrived. On real hardware each one costs a synchronous
    # timeout_char wait inside the C read, never yielding to asyncio (SPECIFICATION.md Part F.5.8);
    # these fakes serve what they hold and return, so the stall is counted here instead of taken.
    would_have_blocked_bytes = 0

    def __init__(
        self,
        id: int,
        *,
        tx: "Pin",
        rx: "Pin",
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
        if id not in (0, 1):
            raise ValueError(f"UART({id}) doesn't exist")
        if invert & ~self._UART_INVERT_MASK:
            raise ValueError("bad inversion mask")
        if rxbuf > self._MAX_BUFFER_SIZE:
            raise ValueError("rxbuf too large")
        if txbuf > self._MAX_BUFFER_SIZE:
            raise ValueError("txbuf too large")
        previous = UART._live.get(id)
        if previous is not None:
            previous._supersede()
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
        self.rx_queue = bytearray()
        self.writable = True
        self.write_limit: int | None = None
        self._link: UARTLink | None = None
        self.rx_api_calls = 0  # every any()/read()/readinto()/readline() and POLLIN poll: a DMA reader makes none
        self.rx_fifo_dropped = 0  # bytes lost to a full FIFO, each also setting OE
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

    def _pump(self) -> None:
        if self._link is not None:
            self._link._advance()

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

    def _supersede(self) -> None:
        # Displaced by a newer instance on the same peripheral id: detached from its link so no
        # byte can reach it or leave it afterwards, and marked deinit'd so a stale reference is
        # visibly dead rather than quietly half-alive.
        link = self._link
        if link is not None:
            link.detach(self)
        self._link = None
        self.deinit_called = True
        UART.superseded += 1

    def _update(self) -> None:
        # Lands what the FIFO holds where it now belongs, then every byte whose wire time has elapsed.
        fifo, self._fifo = self._fifo, bytearray()
        for byte in fifo:
            self._route(byte)
        self._pump()

    def any(self) -> int:
        # Real machine.UART.any() drains the RX FIFO before counting, so it never under-reports
        # what a preceding POLLIN saw - _update() is this fake's equivalent, and omitting it would
        # make asy_uart_driver's read clamp (which calls this) starve on a link with bytes in it.
        self.rx_api_calls += 1
        self._update()
        return len(self.rx_queue)

    def deinit(self) -> None:
        # Real deinit() resets the UART block (uart_deinit()): every register back to its reset value.
        self.deinit_called = True
        self.imsc = 0
        self.dmacr = 0
        self.rsr = 0
        self._fifo = bytearray()
        if UART._live.get(self.id) is self:
            del UART._live[self.id]

    def feed_rx(self, data: bytes) -> None:
        self.rx_queue += data

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
        # Twin-only test knob: sets UARTRSR bits (OE 0x08, BE 0x04, FE 0x01); a break also receives one
        # 0x00 character (RP2040 datasheet 4.2.8, Table 426).
        self._update()
        self.rsr |= bits & 0x0F
        if bits & _RSR_BE:
            self._route(0, is_break=True)

    def read(self, nbytes: int | None = None) -> bytes | None:
        self.rx_api_calls += 1
        self._update()
        self._count_overask(len(self.rx_queue) if nbytes is None else nbytes)
        n = len(self.rx_queue) if nbytes is None else min(nbytes, len(self.rx_queue))
        if n == 0:
            return None
        data = bytes(self.rx_queue[:n])
        self.rx_queue = self.rx_queue[n:]
        return data

    def readinto(self, buf: "bytearray | memoryview", nbytes: int | None = None) -> int | None:
        self.rx_api_calls += 1
        self._update()
        self._count_overask(len(buf) if nbytes is None else min(nbytes, len(buf)))
        n = len(buf) if nbytes is None else min(nbytes, len(buf))
        n = min(n, len(self.rx_queue))
        if n == 0:
            return None
        buf[:n] = self.rx_queue[:n]
        self.rx_queue = self.rx_queue[n:]
        return n

    def readline(self, size: int = -1) -> bytes | None:
        # Clamped to any() like every counted read: readline() reads byte by byte up to a newline or
        # `size`, each missing byte a blocking wait; with no size and no newline buffered, the C read
        # still waits for the one byte past the buffer.
        self.rx_api_calls += 1
        self._update()
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
        self.rx_queue = self.rx_queue[end:]
        return data

    def txdone(self) -> bool:
        # The link schedules each byte at once: nothing waits in a TX FIFO (machine_uart.c:510-514).
        return True

    def write(self, buf: object) -> int | None:
        data = bytes(buf)  # type: ignore[call-overload]
        if self.write_limit is not None:
            data = data[: self.write_limit]
            if not data:
                return None
        if self._link is not None:
            self._link.transmit(self, data)
        return len(data)


class LinkPoller:
    # Bounded select.poll() stand-in, identical in behaviour to tests/machine.py's own - see
    # digital_twin/unix_port_poll_prewarm.py for the modselect.c segfault a real poll object over
    # a non-fd stream can hit here.
    def __init__(self, uart: "UART", not_ready_calls: int = 0, mask: int = select.POLLIN | select.POLLOUT) -> None:
        self._uart = uart
        self._not_ready = not_ready_calls
        self._mask = mask  # what a real poll asks the stream for: the events the driver registered

    def force_not_ready(self, calls: int) -> None:
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

    def __init__(
        self, id: int = -1, *, period: int = -1, mode: int = PERIODIC, callback: "Callable[[Timer], None] | None" = None,
    ) -> None:
        self.id = id
        self.period = -1
        self.mode = self.PERIODIC
        self.callback: Callable[[Timer], None] | None = None
        self._task: asyncio.Task[None] | None = None
        # Spelled out rather than **kwargs-forwarded so the accepted settings are statically
        # checked; the guard keeps real machine_timer_make_new()'s "init helper only runs when the
        # constructor was actually given settings" behavior for a bare Timer().
        if period != -1 or mode != self.PERIODIC or callback is not None:
            self.init(period=period, mode=mode, callback=callback)

    def init(
        self, *, period: int = -1, mode: int = PERIODIC, callback: "Callable[[Timer], None] | None" = None,
    ) -> None:
        self.deinit()  # cancel any previously-armed schedule before re-arming
        self.period = period
        self.mode = mode
        self.callback = callback
        if callback is not None and period >= 0:
            self._task = asyncio.get_event_loop().create_task(self._run())

    async def _run(self) -> None:
        try:
            while True:
                await asyncio.sleep_ms(self.period)
                if self.callback is not None:
                    self.callback(self)
                if self.mode == self.ONE_SHOT:
                    return
        except asyncio.CancelledError:
            pass

    def deinit(self) -> None:
        if self._task is not None:
            try:
                is_own_callback = self._task is asyncio.current_task()
            except RuntimeError:  # no running event loop (e.g. a synchronous test calling deinit()
                # directly, outside asyncio.run()) - definitely not this Timer's own callback either way.
                is_own_callback = False
            if not is_own_callback:
                self._task.cancel()
            # Self-rearming from inside the callback is valid - real hardware just reprograms
            # the alarm pool - but a Task cannot cancel itself in MicroPython. Skip the
            # self-cancel: the old task returns on its own right after this callback does.
            self._task = None
        self.callback = None


_WDT_TIMEOUT_MAX_MS = 8388  # RP2040 hard cap: 0xffffff / 2 / 1000 (ports/rp2/machine_wdt.c) - see
# SPECIFICATION.md Part F.1, read from the pinned v1.29.0 source rather than guessed - 1.29 added
# a separate RP2350 branch, but the RP2040 cap is unchanged. A timeout above it raises
# ValueError, as does any id but 0, which is all rp2 implements. Both matched here.


class WDT:
    def __init__(
        self, id: int = 0, timeout: int = 5000, *, on_would_trigger: "Callable[[WDT], None] | None" = None,
    ) -> None:
        if id != 0:
            raise ValueError(f"WDT({id}) doesn't exist")
        if timeout > _WDT_TIMEOUT_MAX_MS:
            raise ValueError(f"timeout exceeds {_WDT_TIMEOUT_MAX_MS}")
        self.id = id
        self.timeout = timeout
        self.feed_count = 0
        # Twin-only: real hardware can never be asked "would you have reset by now". An asyncio
        # countdown since the last feed() that records rather than acts, with no disable API - a real
        # armed WDT has none either, and the task dies with its loop (digital_twin/README.md).
        self.would_have_triggered_count = 0
        # feed_count observed at each notification - ad-hoc introspection aid, same shape as
        # I2C.log/SPI.log above (see _LOG_MAXLEN's own comment): grows for the life of the process
        # on every would-have-triggered notification, so bounded the same way.
        self.would_have_triggered_log: deque[int] = deque((), _LOG_MAXLEN)
        self._on_would_trigger = on_would_trigger
        self._task: asyncio.Task[None] | None = None
        self._armed_at_ms: Any | None = None  # an opaque ticks_ms() value, not a plain int
        self._arm()

    def _arm(self) -> None:
        # A feed() can arrive after a real --hang has already blown past the previous deadline (see
        # digital_twin/README.md's "WDT._arm()'s late-feed backstop") - credit that already-elapsed
        # window before cancelling it away, since real hardware can't un-reset itself retroactively.
        now = time.ticks_ms()
        if self._armed_at_ms is not None:
            elapsed = time.ticks_diff(now, self._armed_at_ms)
            if elapsed >= self.timeout:
                self._record_would_trigger()
        if self._task is not None:
            self._task.cancel()
        self._armed_at_ms = now
        self._task = asyncio.get_event_loop().create_task(self._countdown())

    async def _countdown(self) -> None:
        try:
            while True:
                await asyncio.sleep_ms(self.timeout)
                self._record_would_trigger()
        except asyncio.CancelledError:
            pass

    def _record_would_trigger(self) -> None:
        global watchdog_reason_value
        watchdog_reason_value = _REASON_TIMER  # the reset a starved watchdog would make reads REASON TIMER
        self.would_have_triggered_count += 1
        self.would_have_triggered_log.append(self.feed_count)
        if self._on_would_trigger is not None:
            self._on_would_trigger(self)

    def feed(self) -> None:
        self.feed_count += 1
        self._arm()  # a real feed() resets the hardware countdown - restart ours the same way


class _Mem32:
    # machine.mem32: 32-bit peripheral register access (extmod/machine_mem.c). Models the two reset registers and the
    # UART blocks' UARTRSR/UARTECR, UARTIMSC and UARTDMACR of the live UART per id; any other address raises
    # ValueError ("not modelled"). Every access is recorded in `log` as ("read"|"write", address, value).
    def __init__(self) -> None:
        self.log = _BoundedLog(_MEM32_LOG_MAXLEN)

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
_REASON_TIMER = 0x1
_HAD_POR = 0x100
# Twin-only test knob: what the two registers read, the power-on pair until power_on()/reset()/bootloader() move them.
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

if TYPE_CHECKING:
    # -1 is also an int: mypy's documented form for a Literal overload ahead of its wider sibling.
    @overload
    def mem_backup(region: "Literal[-1]") -> "tuple[memoryview, memoryview]": ...  # type: ignore[overload-overlap]
    @overload
    def mem_backup(region: int = 0) -> memoryview: ...


def mem_backup(region: int = 0) -> "memoryview | tuple[memoryview, memoryview]":
    # extmod/machine_mem.c:135-148: one region's view, or (for -1) a tuple of every region's; any other index
    # outside the table raises.
    if region == -1:
        return _REGION_VIEWS
    if region < 0 or region >= len(_REGION_VIEWS):
        raise ValueError("invalid region")
    return _REGION_VIEWS[region]


def reset_cause() -> int:
    return reset_cause_value


def power_on() -> None:
    # Twin-only test knob: a power cycle clears both regions, reports PWRON_RESET and leaves REASON 0, HAD_POR set.
    global reset_cause_value, watchdog_reason_value, chip_reset_value
    for region in _REGIONS:
        for i in range(len(region)):
            region[i] = 0
    reset_cause_value = PWRON_RESET
    watchdog_reason_value = 0
    chip_reset_value = _HAD_POR


class RTC:
    # One physical peripheral - class-level shared state, matches real singleton hardware (and
    # tests/machine.py's own identical convention).
    _shared_datetime: "tuple[int, ...]" = (2000, 1, 1, 0, 0, 0, 0, 0)

    def __init__(self, id: int = 0) -> None:
        self.id = id

    def datetime(self, dt: "tuple[int, ...] | None" = None) -> "tuple[int, ...]":
        # Return type matches typings/machine.pyi's own RTC.datetime signature (always `Tuple`,
        # not Optional) even on the set path, where real hardware returns nothing meaningful -
        # simplifies the common get-after-set call pattern without a getter/setter @overload split.
        if dt is None:
            return RTC._shared_datetime
        RTC._shared_datetime = tuple(dt)
        return RTC._shared_datetime


class SimulatedRebootError(Exception):
    # Base class for both twin-only reboot exceptions below - lets a Step 5 harness catch either
    # kind uniformly (`except SimulatedRebootError:`) or distinguish them when it needs to.
    pass


class SimulatedResetError(SimulatedRebootError):
    pass


class SimulatedBootloaderEntryError(SimulatedRebootError):
    pass


reset_count = 0
bootloader_count = 0


def reset() -> None:
    # Real machine.reset() never returns; this twin cannot restart anything, so it raises instead. The counter
    # and the cause (rp2 resets through the watchdog) step first, so a harness catching the error can read both.
    global reset_count, reset_cause_value, watchdog_reason_value
    reset_count += 1
    reset_cause_value = WDT_RESET
    watchdog_reason_value = _REASON_FORCE  # CHIP_RESET is left as it was: a watchdog reset clears no HAD_* bit
    raise SimulatedResetError("machine.reset() called - the twin does not actually restart the process")


def bootloader() -> None:
    global bootloader_count, reset_cause_value, watchdog_reason_value
    bootloader_count += 1
    reset_cause_value = WDT_RESET
    watchdog_reason_value = _REASON_FORCE
    raise SimulatedBootloaderEntryError("machine.bootloader() called - the twin does not actually restart the process")
