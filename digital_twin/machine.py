"""Digital-twin fake `machine` module - real-time-firing `Timer`, I2C/SPI wired to per-address chip simulators via `configure_wiring()` (generic, buildgen-derived plan) or `configure_i2c_wiring()` (the "wozi"/"dev" legacy sugar), deliberately independent of `tests/machine.py`.
See `digital_twin/README.md`'s "What's here" section for the full wiring/`Pin`-identity account."""

import asyncio
import errno
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


# The two real devices' own wiring, in configure_wiring()'s own generic shape - kept as plain literal
# data (this module has no tomllib/buildgen under the MicroPython Unix port); devices/wozi.toml and
# dev.toml are the real source of truth, cross-checked in tests_scripts/test_buildgen_twin_wiring.py.
_LEGACY_WIRING_PLANS: "dict[str, dict[str, Any]]" = {
    "wozi": {
        "buses": {
            "i2c0": [{"driver": "scd30", "name_ext": "", "address": 0x61, "irq_pin": 8}],
            "i2c1": [
                {"driver": "sgp40", "name_ext": "", "address": 0x59},
                {"driver": "bmp3xx", "name_ext": "", "address": 0x77},
            ],
        },
        "spi": {"spi0": {"driver": "fram", "name_ext": "", "max_size": 0x2000}},
    },
    "dev": {
        "buses": {
            "i2c0": [{"driver": "bmp3xx", "name_ext": "", "address": 0x77}],
            "i2c1": [
                {"driver": "scd30", "name_ext": "", "address": 0x61, "irq_pin": 11},
                {"driver": "sgp40", "name_ext": "", "address": 0x59},
            ],
        },
        "spi": {"spi0": {"driver": "fram", "name_ext": "", "max_size": 0x40000}},
    },
}

_wiring_plan: "dict[str, Any]" = _LEGACY_WIRING_PLANS["wozi"]  # default for every caller that never
# calls configure_i2c_wiring()/configure_wiring() at all (e.g. run_wozi_integration.py's own main()).


def configure_wiring(plan: "dict[str, Any]") -> None:
    # Called once, before build_system()-equivalent code constructs i2c0/i2c1/spi0 - a plain dict in
    # buildgen.twin_wiring.compute_twin_wiring()'s own shape. Replaces the whole plan outright, the
    # same "last configure_*() call before construction wins" convention every hook here already uses.
    global _wiring_plan
    if "buses" not in plan or "spi" not in plan:
        raise ValueError("wiring plan must be a dict with 'buses' and 'spi' keys - see buildgen.twin_wiring.compute_twin_wiring()'s own docstring for the shape")
    _wiring_plan = plan


def configure_i2c_wiring(profile: str) -> None:
    # Called once, before build_system()-equivalent code constructs i2c0/i2c1, by whatever entry
    # point wants a non-default wiring (digital_twin/run_dev_integration.py's own main() calls this
    # with "dev"). Validated eagerly here rather than only inside configure_wiring() above, so a
    # typo surfaces immediately at the call site instead of silently NAKing every I2C transaction
    # later.
    if profile not in _LEGACY_WIRING_PLANS:
        raise ValueError(f"unknown I2C wiring profile {profile!r} - expected 'wozi' or 'dev'")
    configure_wiring(_LEGACY_WIRING_PLANS[profile])


def _build_i2c_chip(attachment: "dict[str, Any]") -> "Any":
    # Dispatches on the wiring plan's own "driver" string - the twin's own hand-maintained chip-fake
    # catalog (a genuinely new chip type still needs one hand-written, CLAUDE.md's named exception).
    # Return type is deliberately Any, not _I2CDevice: no single real chip fake implements all four
    # of that Protocol's methods, the same reason _wire_i2c_devices() below stays dict[int, Any].
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
    raise ValueError(f"digital twin has no I2C chip fake for driver {driver!r} - add one to machine._build_i2c_chip()")


def _wire_i2c_devices(bus_id: int) -> "dict[int, Any]":
    return {attachment["address"]: _build_i2c_chip(attachment) for attachment in _wiring_plan["buses"].get(f"i2c{bus_id}", [])}


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

# Real chip-model identity (the RDID bytes) isn't a TOML/DeviceModel fact - only max_size is - so
# it's keyed by size as the best available proxy (unique today: 8KB MB85RS64V vs 256KB MB85RS2MTA).
# Any size not listed falls back to FramChip's own default RDID (MB85RS64V's - wozi's own chip).
_FRAM_RDID_BY_MAX_SIZE: "dict[int, bytes]" = {_DEV_FRAM_SIZE: _DEV_FRAM_RDID}


def _wire_spi_device(bus_id: int) -> "FramChip | None":
    global _current_fram_chip
    attachment = _wiring_plan["spi"].get(f"spi{bus_id}")
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
