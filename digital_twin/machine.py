"""Digital-twin fake `machine` module - real-time-firing `Timer`, I2C/SPI wired to per-address chip
simulators (see `configure_i2c_wiring()`), deliberately independent of `tests/machine.py`.
See `digital_twin/README.md`'s "What's here" section for the full wiring/`Pin`-identity account."""

import asyncio
import errno
import io
import select
import time
from collections import deque

_SPI_DMA_MIN_SIZE = 32  # ports/rp2/machine_spi.c's own dma_min_size_threshold - see SPI._maybe_overrun()
_LOG_MAXLEN = 200  # I2C.log/SPI.log's own bound - see digital_twin/README.md for the real memory
# leak this avoids; same "keep last N" convention print_log.py's own PrintLogHistory uses.

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, Protocol

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


class Pin:
    IN = 0
    OUT = 1
    IRQ_FALLING = 0x04
    IRQ_RISING = 0x08

    _registry: "dict[int, Pin]" = {}
    _initialized: bool

    @classmethod
    def reset_registry(cls) -> None:
        # Test-only: real GPIO pins never "reset" between test functions the way this registry
        # needs to for isolation - mirrors tests/machine.py's own Timer.all_timers.clear() convention.
        cls._registry.clear()

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

    def __init__(self, id: int, mode: int = -1, pull: int = -1, *, value: object = None) -> None:
        if self._initialized:
            # Re-binding to an already-registered physical pin - apply init()-style settings
            # (leave-unchanged-if-omitted) without wiping the pin's current electrical state.
            self.init(mode, pull)
            if value is not None:
                self.value(value)
            return
        self.id = id
        self.mode = mode
        self.pull = pull
        self._value = 0 if value is None else (1 if value else 0)
        self._irq_handler: Callable[[Pin], None] | None = None
        self._irq_trigger = self.IRQ_FALLING | self.IRQ_RISING
        self._irq_hard = False
        self._initialized = True

    def init(self, mode: int = -1, pull: int = -1) -> None:
        if mode != -1:
            self.mode = mode
        if pull != -1:
            self.pull = pull

    def value(self, x: object = None) -> "int | None":
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
        self._irq_handler = handler
        self._irq_trigger = trigger
        self._irq_hard = hard
        return self

    def simulate_edge(self, new_value: object) -> None:
        # Twin-only: drives a real electrical transition, firing the registered handler only if
        # the transition direction matches what irq() was told to listen for - unlike
        # tests/machine.py's own trigger_irq() (fires unconditionally; deterministic unit tests
        # don't need edge-direction fidelity), a twin standing in for real hardware does.
        old = self._value
        self._value = 1 if new_value else 0
        if old == self._value:
            return
        rising = old == 0 and self._value == 1
        edge = self.IRQ_RISING if rising else self.IRQ_FALLING
        if (self._irq_trigger & edge) and self._irq_handler is not None:
            self._irq_handler(self)


_random_source: "_RandomSource | None" = None


def configure_random_source(source: "_RandomSource | None") -> None:
    # Same module-level-hook pattern as configure_fram_state_path() below, applied to sensor value
    # walks instead of FRAM persistence: called once, before build_system()-equivalent code
    # constructs i2c0/i2c1, by whatever entry point wants every wired chip's value walk to share one
    # seeded random.Random (digital_twin/launch.py's own --seed flag). None (the default) means
    # every chip falls back to its own un-seeded `random` module, exactly as before this existed.
    global _random_source
    _random_source = source


_scd30_state_path: "str | None" = None
_current_scd30_chip: "Any | None" = None


def configure_scd30_state_path(path: "str | None") -> None:
    # Same module-level-hook pattern as configure_fram_state_path() above, applied to the SCD30's
    # own NVM-persisted settings instead of FRAM contents - called once, before build_system()-
    # equivalent code constructs i2c0, by whatever entry point Step 5 writes. None (the default)
    # means "in-memory only, no persistence".
    global _scd30_state_path
    _scd30_state_path = path


def flush_scd30() -> None:
    # Called once, in a try/finally around asyncio.run(main()), alongside flush_fram() - see
    # _scd30_chip.py's own module docstring for what is/isn't persisted and why.
    if _current_scd30_chip is not None:
        _current_scd30_chip.save_state()


_i2c_wiring_profile = "wozi"  # dev's variant flips which bus carries which sensors (and SCD30's
# own IRQ pin) relative to wozi - same module-level-hook pattern as configure_random_source()/
# configure_fram_state_path() above. Default "wozi" keeps every existing caller unchanged.


def configure_i2c_wiring(profile: str) -> None:
    # Called once, before build_system()-equivalent code constructs i2c0/i2c1, by whatever entry
    # point wants a non-default wiring (digital_twin/run_dev_integration.py's own main() calls this
    # with "dev"). Validated eagerly here rather than only inside _wire_i2c_devices() below, so a
    # typo surfaces immediately at the call site instead of silently NAKing every I2C transaction
    # later.
    if profile not in ("wozi", "dev"):
        raise ValueError(f"unknown I2C wiring profile {profile!r} - expected 'wozi' or 'dev'")
    global _i2c_wiring_profile
    _i2c_wiring_profile = profile


def _wire_i2c_devices(bus_id: int) -> "dict[int, Any]":
    global _current_scd30_chip
    from _bmp3xx_chip import Bmp3xxChip
    from _scd30_chip import Scd30Chip
    from _sgp40_chip import Sgp40Chip

    if _i2c_wiring_profile == "dev":
        # dev_legacy/README.md's wiring table: i2c0 (bus_id=0) carries BMP3xx alone; i2c1 (bus_id=1)
        # carries SCD30 (IRQ/RDY=GPIO11) + SGP40 sharing the bus - the reverse pairing from wozi's
        # own layout below.
        if bus_id == 0:
            return {0x77: Bmp3xxChip(random_source=_random_source)}
        if bus_id == 1:
            chip = Scd30Chip(rdy_pin=Pin(11, mode=Pin.IN), random_source=_random_source, state_path=_scd30_state_path)
            _current_scd30_chip = chip
            return {0x61: chip, 0x59: Sgp40Chip(random_source=_random_source)}
        return {}

    # "wozi" (default): i2c0 (bus_id=0) carries SCD30 alone (IRQ/RDY=GPIO8); i2c1 (bus_id=1) carries
    # SGP40 + BMP3xx sharing the bus.
    if bus_id == 0:
        chip = Scd30Chip(rdy_pin=Pin(8, mode=Pin.IN), random_source=_random_source, state_path=_scd30_state_path)
        _current_scd30_chip = chip
        return {0x61: chip}
    if bus_id == 1:
        return {0x59: Sgp40Chip(random_source=_random_source), 0x77: Bmp3xxChip(random_source=_random_source)}
    return {}


class I2C:
    def __init__(self, id: int, *, scl: Pin, sda: Pin, freq: int = 400000, timeout: int = 50000) -> None:
        self.id = id
        self.scl = scl
        self.sda = sda
        self.freq = freq
        self.timeout = timeout
        self.deinit_called = False
        self.log: deque[tuple[Any, ...]] = deque((), _LOG_MAXLEN)
        self.devices = _wire_i2c_devices(id)  # public: tests reach a wired chip via i2c.devices[addr]

    def deinit(self) -> None:
        # Real rp2 machine.I2C.deinit() only exists from MicroPython 1.29 on, and even there the
        # port's .deinit protocol slot is NULL - a silent no-op that leaves the peripheral and its
        # pins exactly as they were (SPECIFICATION.md Part F.5). Every bus operation below stays
        # working afterwards on purpose; the flag only records that the call was forwarded.
        self.deinit_called = True

    def scan(self) -> "list[int]":
        return sorted(self.devices.keys())

    def _device_or_nak(self, address: int) -> "_I2CDevice":
        device: _I2CDevice | None = self.devices.get(address)
        if device is None:
            raise OSError(errno.EIO, "no ACK from device")
        return device

    def writeto(self, address: int, buf: object, stop: bool = True) -> int:
        data = bytes(buf)  # type: ignore[call-overload]
        if address == 0x00:  # general call - every device may listen, tolerate silently
            self.log.append(("writeto", address, data, stop))
            return len(data)
        device = self._device_or_nak(address)
        device.handle_writeto(data)
        self.log.append(("writeto", address, data, stop))
        return len(data)

    def readfrom_into(self, address: int, buf: object, stop: bool = True) -> None:
        device = self._device_or_nak(address)
        data = device.handle_readfrom_into(len(buf))  # type: ignore[arg-type]
        buf[:] = data  # type: ignore[index]
        self.log.append(("readfrom_into", address, data, stop))

    def readfrom_mem(self, address: int, memaddr: int, nbytes: int, *, addrsize: int = 8) -> bytes:
        device = self._device_or_nak(address)
        data = device.handle_readfrom_mem(memaddr, nbytes)
        self.log.append(("readfrom_mem", address, memaddr, nbytes, addrsize))
        return data

    def writeto_mem(self, address: int, memaddr: int, buf: object, *, addrsize: int = 8) -> None:
        device = self._device_or_nak(address)
        device.handle_writeto_mem(memaddr, bytes(buf))  # type: ignore[call-overload]
        self.log.append(("writeto_mem", address, memaddr, bytes(buf), addrsize))  # type: ignore[call-overload]


_fram_state_path: "str | None" = None
_current_fram_chip: "Any | None" = None


def configure_fram_state_path(path: "str | None") -> None:
    # Called once, before build_system() constructs spi0, by whatever entry point Step 5 writes -
    # src/ itself never calls this (zero twin-awareness anywhere in src/, per this step's own
    # finish criteria). None (the default) means "in-memory only, no persistence".
    global _fram_state_path
    _fram_state_path = path


def flush_fram() -> None:
    # Called once, in a try/finally around asyncio.run(main()), by whatever entry point Step 5
    # writes - see _fram_chip.py's own module docstring for why this must be explicit rather than
    # a self-registered signal/atexit handler.
    if _current_fram_chip is not None:
        _current_fram_chip.save_state()


_DEV_FRAM_SIZE = 0x40000  # MB85RS2MTA, 256KB - sensortask_dev.py's own AsyFramManager(spi0, 5, max_size=0x40000, ...)
_DEV_FRAM_RDID = bytes([0x04, 0x7F, 0x48, 0x03])  # manufacturer=Fujitsu, cont_code, product ID 0x4803 - asy_fram_driver.py's own _KNOWN_PRODUCT_IDS[0x40000], datasheets/fram/MB85RS2MTA-DS501-00032-3v0-E.pdf p.10


def _wire_spi_device(bus_id: int) -> "FramChip | None":
    global _current_fram_chip
    if bus_id == 0:
        from _fram_chip import FramChip

        # Mirrors _wire_i2c_devices()'s own profile branch above - see digital_twin/README.md's
        # "What's here" section for the real chip-identity bug this fixed.
        chip = (
            FramChip(size=_DEV_FRAM_SIZE, state_path=_fram_state_path, rdid_response=_DEV_FRAM_RDID)
            if _i2c_wiring_profile == "dev"
            else FramChip(state_path=_fram_state_path)
        )
        _current_fram_chip = chip
        return chip
    return None


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
        # MicroPython 1.29 added an RX-overrun check to rp2's SPI transfer path, reached only by
        # *reading* transfers of 32+ bytes (SPECIFICATION.md Part F.5.2). Modelled here rather
        # than on the chip's own FaultInjector because it is a property of the port, not the
        # device: sticky, plus a counted form for a transient glitch the bus recovers from.
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
        self.wire_log = bytearray()

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


class UARTLink:
    # Twin-fidelity byte-level crossover between two UART fakes: one FIFO per direction, the same
    # fault knobs as the mock link, plus real wire time - a byte only becomes readable once its
    # transmission would actually have finished at the configured baud rate. That is what keeps a
    # timing-dependent recovery (drain, cooldown) from passing for the wrong reason (A4.3).
    def __init__(self, uart_a: "UART", uart_b: "UART", capacity_a_to_b: int | None = None, capacity_b_to_a: int | None = None) -> None:
        if uart_a._link is not None or uart_b._link is not None:
            raise ValueError("UART already attached to a link")
        if uart_a is uart_b:
            raise ValueError("a link needs two distinct endpoints")
        self.endpoints = (uart_a, uart_b)
        self.a_to_b = _LinkDirection(uart_b.rxbuf if capacity_a_to_b is None else capacity_a_to_b, uart_a.baudrate)
        self.b_to_a = _LinkDirection(uart_a.rxbuf if capacity_b_to_a is None else capacity_b_to_a, uart_b.baudrate)
        # Wire time is kept as a plain microsecond offset from one epoch captured here, via
        # ticks_diff(), rather than as raw ticks values: the arithmetic below mixes it with byte
        # durations, and ticks values are opaque. A twin run longer than ticks_us()' own period
        # would need re-anchoring; no test comes close.
        self._epoch_us = time.ticks_us()
        self._next_free_us = [0, 0]  # per direction: when the wire is idle again
        uart_a._link = self
        uart_b._link = self

    def _index(self, uart: "UART") -> int:
        return 0 if uart is self.endpoints[0] else 1

    def direction_from(self, uart: "UART") -> "_LinkDirection":
        if uart not in self.endpoints:
            raise ValueError("UART is not an endpoint of this link")
        return self.a_to_b if self._index(uart) == 0 else self.b_to_a

    def direction_to(self, uart: "UART") -> "_LinkDirection":
        if uart not in self.endpoints:
            raise ValueError("UART is not an endpoint of this link")
        return self.b_to_a if self._index(uart) == 0 else self.a_to_b

    def _now_us(self) -> int:
        return time.ticks_diff(time.ticks_us(), self._epoch_us)

    def _schedule(self, index: int, direction: "_LinkDirection", data: bytearray) -> None:
        now = self._now_us()
        due = max(now, self._next_free_us[index])
        step = direction.byte_time_us()
        for byte in data:
            due += step
            try:
                direction.in_flight.append((due, byte))
            except IndexError:
                # A full in-flight queue is a receive overrun by another name - counted and
                # dropped, never raised into the driver, which real hardware never does either.
                direction.dropped_overrun += 1
        self._next_free_us[index] = due

    def _advance(self) -> None:
        # Moves every byte whose wire time has elapsed into the destination FIFO. Called from each
        # endpoint's own read path, so time only ever advances as the consumer actually runs.
        now = self._now_us()
        for index, direction in ((0, self.a_to_b), (1, self.b_to_a)):
            dest = self.endpoints[1 - index]
            while direction.in_flight and direction.in_flight[0][0] <= now:
                _due, byte = direction.in_flight.popleft()
                if len(dest.rx_queue) >= direction.capacity:
                    direction.dropped_overrun += 1
                    continue
                dest.rx_queue.append(byte)
                direction.wire_log.append(byte)
                direction.delivered += 1

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


class UART(io.IOBase):
    # Twin UART, deliberately independent of tests/machine.py's own (see this module's docstring)
    # but held to the same semantics by tests/_uart_link_contract.py. io.IOBase is what lets
    # asy_uart_driver.py's init() register it with a real select.poll() without raising; tests
    # still reassign .poller to a bounded stand-in afterwards, since the Unix port never
    # re-evaluates a Python object's ioctl() after registration (CLAUDE.md's known hang cause).
    _MP_STREAM_POLL = 3  # py/stream.h
    _MAX_BUFFER_SIZE = 32766
    _UART_INVERT_MASK = 3

    # One live instance per peripheral id. Real machine.UART() on this port re-inits the
    # peripheral rather than refusing, so constructing another instance on the same id supersedes
    # the first - and the twin makes that explicit: the superseded object is deinit'd and detached
    # from any link, so it cannot silently keep delivering to a stale peer while the new one
    # believes it owns the bus. That silent mis-routing is the failure this models (A4.2).
    _live: "dict[int, UART]" = {}
    superseded = 0  # how many instances have been displaced this way, for a test to assert on

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
        UART._live[id] = self

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

    def _pump(self) -> None:
        if self._link is not None:
            self._link._advance()

    def ioctl(self, req: int, arg: int) -> int:
        if req != self._MP_STREAM_POLL:
            return 0
        self._pump()
        ready = 0
        if (arg & select.POLLIN) and self.rx_queue:
            ready |= select.POLLIN
        if (arg & select.POLLOUT) and self.writable:
            ready |= select.POLLOUT
        return ready

    def feed_rx(self, data: bytes) -> None:
        self.rx_queue += data

    def deinit(self) -> None:
        self.deinit_called = True
        if UART._live.get(self.id) is self:
            del UART._live[self.id]

    def read(self, nbytes: int | None = None) -> bytes | None:
        self._pump()
        n = len(self.rx_queue) if nbytes is None else min(nbytes, len(self.rx_queue))
        if n == 0:
            return None
        data = bytes(self.rx_queue[:n])
        self.rx_queue = self.rx_queue[n:]
        return data

    def readinto(self, buf: "bytearray | memoryview", nbytes: int | None = None) -> int | None:
        self._pump()
        n = len(buf) if nbytes is None else min(nbytes, len(buf))
        n = min(n, len(self.rx_queue))
        if n == 0:
            return None
        buf[:n] = self.rx_queue[:n]
        self.rx_queue = self.rx_queue[n:]
        return n

    def readline(self) -> bytes | None:
        self._pump()
        if not self.rx_queue:
            return None
        idx = self.rx_queue.find(b"\n")
        end = len(self.rx_queue) if idx == -1 else idx + 1
        data = bytes(self.rx_queue[:end])
        self.rx_queue = self.rx_queue[end:]
        return data

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
    def __init__(self, uart: "UART", not_ready_calls: int = 0) -> None:
        self._uart = uart
        self._not_ready = not_ready_calls

    def force_not_ready(self, calls: int) -> None:
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
            # Self-rearming from within its own callback is valid (real rp2 hardware just
            # reprograms the alarm pool), but asyncio.Task.cancel() can't cancel its own running
            # task (MicroPython raises RuntimeError) - skip the self-cancel; the old task is about
            # to return/loop on its own right after this callback returns anyway.
            self._task = None
        self.callback = None


_WDT_TIMEOUT_MAX_MS = 8388  # RP2040 hard cap: 0xffffff / 2 / 1000 (ports/rp2/machine_wdt.c) - see
# SPECIFICATION.md Part F.1. Confirmed directly against the pinned v1.29.0 source (not guessed;
# 1.29 added a separate 16777ms RP2350 branch, but the RP2040 cap is unchanged):
# WDT(timeout=N) for N above this raises ValueError("timeout exceeds 8388"); WDT(id != 0) raises
# ValueError too ("WDT(%d) doesn't exist") - rp2 only ever implements id 0. Both matched here.


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
        # Twin-only: real hardware can never be asked "would you have reset by now" - an internal
        # asyncio-task-scheduled countdown (mirrors Timer's own mechanism above) that tracks time
        # since the last feed() and records, rather than acts on, a would-have-reset event. No
        # public "disable" API - real hardware genuinely can't disable an armed WDT either, and this
        # task dies naturally when its owning asyncio.run() event loop closes, matching Timer's own
        # cleanup story (see digital_twin/README.md for the full design writeup).
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

    def _record_would_trigger(self) -> None:
        self.would_have_triggered_count += 1
        self.would_have_triggered_log.append(self.feed_count)
        if self._on_would_trigger is not None:
            self._on_would_trigger(self)

    async def _countdown(self) -> None:
        try:
            while True:
                await asyncio.sleep_ms(self.timeout)
                self._record_would_trigger()
        except asyncio.CancelledError:
            pass

    def feed(self) -> None:
        self.feed_count += 1
        self._arm()  # a real feed() resets the hardware countdown - restart ours the same way


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
    # Real machine.reset() never returns - it restarts the whole device. This twin can't do that
    # (it would just kill the test/Step-5 process), so it raises instead: the counter below still
    # increments first (useful even though the call "never returns" on real hardware either - a
    # harness catching the exception can still inspect "how many times did this happen"), then
    # SimulatedResetError propagates to whatever caller is meant to observe "a reboot happened here".
    global reset_count
    reset_count += 1
    raise SimulatedResetError("machine.reset() called - the twin does not actually restart the process")


def bootloader() -> None:
    global bootloader_count
    bootloader_count += 1
    raise SimulatedBootloaderEntryError("machine.bootloader() called - the twin does not actually restart the process")
