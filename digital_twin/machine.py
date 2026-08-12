"""Digital-twin fake `machine` module (FINAL_WIRING_PLAN.md's Step 3): the same raw I2C/SPI
bus-transaction mocking boundary tests/machine.py establishes for unit tests, but built for a
different purpose - a Step 5 Unix-port integration run that should behave like it's attached to
real hardware. Deliberately NOT tests/machine.py and does not import it (owner instruction) - a
separate module with a separate goal: real-time-firing Timer (asyncio-task-scheduled, not manual
.trigger()) and I2C/SPI buses wired to per-address chip simulators (_sgp40_chip.py/_scd30_chip.py/
_bmp3xx_chip.py/_fram_chip.py) that answer with randomized-but-plausible, datasheet-range values.

Bus wiring mirrors src/sensortask_wozi.py's real build_system() construction exactly (the "wozi"
variant only, per FINAL_WIRING_PLAN.md's prototype scope - confirmed directly against that file's
own i2c0/i2c1/spi0 construction lines): i2c0 (id=0) carries the SCD30 at 0x61 with its RDY pin on
GPIO 8; i2c1 (id=1) carries the SGP40 at 0x59 and BMP3xx at 0x77; spi0 (id=0) carries the FRAM chip.
Any other bus id/address combination NAKs, matching a real bus with only these devices on it - the
opposite default from tests/machine.py's open-bus-unless-explicitly-NAKed model, since a twin
standing in for real hardware should behave like a real bus with a fixed, known set of devices on
it, not an unbounded fixture a test primes per call. The one exception is the general-call address
(0x00): always tolerated silently, matching a real bus where any device may (or may not) be
listening for it - see SGP40's own general-call reset write.

Pin identity is shared by id (Pin(8) constructed twice returns the same underlying pin state) -
real GPIO pins are one fixed physical resource, and this twin's SCD30 chip fake needs to drive the
exact same Pin object src/asy_scd30_driver.py's own SCD30_Reader.__init__ constructs independently
via Pin(irq_pin, mode=Pin.IN), regardless of construction order.
"""

import asyncio
import errno

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any


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

    def __new__(cls, id: int, *args: object, **kwargs: object) -> "Pin":
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

    def __init__(self, id: int, mode: int = -1, pull: int = -1, *, value: "Any" = None) -> None:
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


_random_source: "Any | None" = None


def configure_random_source(source: "Any | None") -> None:
    # Same module-level-hook pattern as configure_fram_state_path() below, applied to sensor value
    # walks instead of FRAM persistence: called once, before build_system()-equivalent code
    # constructs i2c0/i2c1, by whatever entry point wants every wired chip's value walk to share one
    # seeded random.Random (digital_twin/launch.py's own --seed flag). None (the default) means
    # every chip falls back to its own un-seeded `random` module, exactly as before this existed.
    global _random_source
    _random_source = source


def _wire_i2c_devices(id: int) -> "dict[int, Any]":
    if id == 0:
        from _scd30_chip import Scd30Chip

        return {0x61: Scd30Chip(rdy_pin=Pin(8, mode=Pin.IN), random_source=_random_source)}
    if id == 1:
        from _bmp3xx_chip import Bmp3xxChip
        from _sgp40_chip import Sgp40Chip

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
        self.log: list[tuple] = []
        self.devices = _wire_i2c_devices(id)  # public: tests reach a wired chip via i2c.devices[addr]

    def deinit(self) -> None:
        self.deinit_called = True

    def scan(self) -> "list[int]":
        return sorted(self.devices.keys())

    def _device_or_nak(self, address: int) -> "Any":
        device = self.devices.get(address)
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
        return data  # type: ignore[no-any-return]  # device is duck-typed (Any), see _device_or_nak

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


def _wire_spi_device(id: int) -> "Any | None":
    global _current_fram_chip
    if id == 0:
        from _fram_chip import FramChip

        chip = FramChip(state_path=_fram_state_path)
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
        self.log: list[tuple] = []
        self.device = _wire_spi_device(id)  # public: tests reach the wired chip via spi.device

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
        self.deinit_called = True

    def write(self, buf: object) -> None:
        data = bytes(buf)  # type: ignore[call-overload]
        if self.device is not None:
            self.device.write(data)
        self.log.append(("write", data))

    def readinto(self, buf: "bytearray | memoryview", write_value: int = 0x00) -> None:
        if self.device is not None:
            self.device.readinto(buf)
        else:
            buf[:] = bytes(len(buf))
        self.log.append(("readinto", len(buf), write_value))

    def write_readinto(self, buffer_out: object, buffer_in: "bytearray | memoryview") -> None:
        if len(buffer_out) != len(buffer_in):  # type: ignore[arg-type]
            raise ValueError("buffers must be the same length")
        self.write(buffer_out)
        self.readinto(buffer_in)


class Timer:
    ONE_SHOT = 0
    PERIODIC = 1

    def __init__(self, id: int = -1, **kwargs: "Any") -> None:
        self.id = id
        self.period = -1
        self.mode = self.PERIODIC
        self.callback: Callable[[Timer], None] | None = None
        self._task: asyncio.Task | None = None
        if kwargs:
            self.init(**kwargs)

    def init(
        self, *, period: int = -1, mode: int = PERIODIC, callback: "Callable[[Timer], None] | None" = None
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
            self._task.cancel()
            self._task = None
        self.callback = None


_WDT_TIMEOUT_MAX_MS = 8388  # RP2040 hard cap: 0xffffff / 2 / 1000 (ports/rp2/machine_wdt.c) - see
# SPECIFICATION.md Part F.1. Confirmed directly against the pinned v1.28.0 source (not guessed):
# WDT(timeout=N) for N above this raises ValueError("timeout exceeds 8388"); WDT(id != 0) raises
# ValueError too ("WDT(%d) doesn't exist") - rp2 only ever implements id 0. Both matched here.


class WDT:
    def __init__(
        self, id: int = 0, timeout: int = 5000, *, on_would_trigger: "Callable[[WDT], None] | None" = None
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
        # cleanup story (FINAL_WIRING_PLAN.md's Step 3 section has the full design writeup).
        self.would_have_triggered_count = 0
        self.would_have_triggered_log: list[int] = []  # feed_count observed at each notification
        self._on_would_trigger = on_would_trigger
        self._task: asyncio.Task | None = None
        self._arm()

    def _arm(self) -> None:
        if self._task is not None:
            self._task.cancel()
        self._task = asyncio.get_event_loop().create_task(self._countdown())

    async def _countdown(self) -> None:
        try:
            while True:
                await asyncio.sleep_ms(self.timeout)
                self.would_have_triggered_count += 1
                self.would_have_triggered_log.append(self.feed_count)
                if self._on_would_trigger is not None:
                    self._on_would_trigger(self)
        except asyncio.CancelledError:
            pass

    def feed(self) -> None:
        self.feed_count += 1
        self._arm()  # a real feed() resets the hardware countdown - restart ours the same way


class RTC:
    # One physical peripheral - class-level shared state, matches real singleton hardware (and
    # tests/machine.py's own identical convention).
    _shared_datetime: tuple = (2000, 1, 1, 0, 0, 0, 0, 0)

    def __init__(self, id: int = 0) -> None:
        self.id = id

    def datetime(self, dt: "tuple | None" = None) -> "tuple":
        # Return type matches typings/machine.pyi's own RTC.datetime signature (always `Tuple`,
        # not Optional) even on the set path, where real hardware returns nothing meaningful -
        # simplifies the common get-after-set call pattern without a getter/setter @overload split.
        if dt is None:
            return RTC._shared_datetime
        RTC._shared_datetime = tuple(dt)
        return RTC._shared_datetime


class SimulatedReboot(Exception):
    # Base class for both twin-only reboot exceptions below - lets a Step 5 harness catch either
    # kind uniformly (`except SimulatedReboot:`) or distinguish them when it needs to.
    pass


class SimulatedReset(SimulatedReboot):
    pass


class SimulatedBootloaderEntry(SimulatedReboot):
    pass


reset_count = 0
bootloader_count = 0


def reset() -> None:
    # Real machine.reset() never returns - it restarts the whole device. This twin can't do that
    # (it would just kill the test/Step-5 process), so it raises instead: the counter below still
    # increments first (useful even though the call "never returns" on real hardware either - a
    # harness catching the exception can still inspect "how many times did this happen"), then
    # SimulatedReset propagates to whatever caller is meant to observe "a reboot happened here".
    global reset_count
    reset_count += 1
    raise SimulatedReset("machine.reset() called - the twin does not actually restart the process")


def bootloader() -> None:
    global bootloader_count
    bootloader_count += 1
    raise SimulatedBootloaderEntry("machine.bootloader() called - the twin does not actually restart the process")
