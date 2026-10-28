"""Twin fake of the rp2 machine module: real-time Timer and WDT, static per-id I2C/SPI/UART objects wired to chip fakes
by configure_wiring(plan) (buildgen's per-device plan), rp2's Pin, mem_backup() and reset rules. Independent of
tests/machine.py; digital_twin/README.md has the fidelity table."""

import asyncio
import errno
import io
import json
import os
import select
import sys
import time
from array import array
from collections import deque

import _flash_stall
import _wall_clock
from _bmp3xx_chip import BMP3XXChip
from _fram_chip import FRAMChip
from _isl29125_chip import ISL29125Chip
from _scd30_chip import SCD30Chip
from _sgp40_chip import SGP40Chip
from _twin_common import COUNTER_CAP, LOG_MAXLEN, BoundedLog, fill_buffer, saturating_add

_SPI_DMA_MIN_SIZE = 32  # ports/rp2/machine_spi.c's own dma_min_size_threshold - see SPI._maybe_overrun()

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping
    from typing import Any, Literal, Protocol, TypedDict, overload

    from _mpy_shed.time_mp import _TicksMs
    from rp2 import DMA

    # Mirrors the keys this module reads of buildgen/twin_wiring.py's TwinWiringPlan: the twin cannot import buildgen.
    class _I2CAttachmentBase(TypedDict):
        driver: str
        address: int

    class _I2CAttachment(_I2CAttachmentBase, total=False):
        irq_pin: int

    class _SPIAttachment(TypedDict):
        driver: str
        max_size: int

    class _RandomSource(Protocol):
        def getrandbits(self, k: int) -> int: ...
        def randint(self, a: int, b: int) -> int: ...
        # Structural stand-in for the `random` module (the default) or a seeded random.Random.
        # Declares the union of what the wired chip fakes each ask for through their own narrower
        # _RandomSource, since configure_random_source() hands one object to all of them.
        def uniform(self, a: float, b: float) -> float: ...

    class _I2CDevice(Protocol):
        def handle_readfrom_into(self, nbytes: int) -> bytes: ...
        def handle_readfrom_mem(self, reg_addr: int, nbytes: int) -> bytes: ...
        # The four transaction shapes this bus forwards to a wired chip fake. Each fake implements only the subset its
        # real counterpart answers, and I2C.devices stays Any-valued so tests reach chip-specific state through it.
        def handle_writeto(self, data: bytes) -> None: ...
        def handle_writeto_mem(self, reg_addr: int, data: bytes) -> None: ...


_VALUE_LOG_MAXLEN = 64  # a line's value log: a chip-select toggles on every SPI transaction
_MEM32_LOG_MAXLEN = 64  # likewise for register accesses: a DMA reader reads UARTRSR at every fill-level read
_WIRE_LOG_MAXLEN = 4096  # bytes of a link direction's wire log kept; its `dropped` counts the rest
_WIRE_CHUNK = 512  # bytes per storage chunk of a wire log


class _WireLog:
    # The bytes a link direction delivered, kept the way BoundedLog keeps entries: up to `maxlen`, then
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
        self.dropped = saturating_add(self.dropped)

    def clear(self) -> None:
        self._chunks = []
        self._n = 0
        self._head = 0

    def extend(self, data: "bytes | bytearray") -> None:
        for byte in data:
            self.append(byte)


_NUM_BANK0_GPIOS = 30  # GPIO0-29, the numbers machine_pin_find() accepts (machine_pin.c:184-188); EXT_GPIO0-2 follow
_PIN_NAMES: "dict[str, int]" = {f"GPIO{n}": n for n in range(_NUM_BANK0_GPIOS)}  # CPU names, boards/make-pins.py:95-108
_PIN_NAMES.update({f"EXT_GPIO{n}": _NUM_BANK0_GPIOS + n for n in range(3)})
_PIN_NAMES.update({f"GP{n}": n for n in list(range(23)) + [26, 27, 28]})  # board names, boards/RPI_PICO_W/pins.csv
_PIN_NAMES.update({f"WL_GPIO{n}": _NUM_BANK0_GPIOS + n for n in range(3)})
_PIN_NAMES["LED"] = _NUM_BANK0_GPIOS  # LED,EXT_GPIO0
_OMITTED: int = object()  # type: ignore[assignment]  # an argument not given, told apart from an explicit None


def _absent_handler(_pin: "Pin") -> None:
    # Pin.irq()'s handler default: a call that names no argument is told apart from an explicit None (machine_pin.c:473).
    pass


def _build_i2c_chip(attachment: "_I2CAttachment") -> "Any":
    # Dispatches on the plan's driver string - the twin's hand-kept chip-fake catalog, the compared strings kept literal;
    # the chip Timers are simulation clocks, not rp2 alarms.
    global _current_scd30_chip
    driver = attachment["driver"]
    if driver == "scd30":
        chip = SCD30Chip(random_source=_random_source, rdy_pin=Pin(attachment["irq_pin"], mode=Pin.IN), timer_factory=_simulation_timer, state_path=_scd30_state_path)
        _current_scd30_chip = chip
        return chip
    if driver == "sgp40":
        return SGP40Chip(random_source=_random_source)
    if driver == "bmp3xx":
        return BMP3XXChip(random_source=_random_source)
    if driver == "isl29125":
        return ISL29125Chip(random_source=_random_source, int_pin=Pin(attachment["irq_pin"], mode=Pin.IN), timer_factory=_simulation_timer)
    raise ValueError(f"digital twin has no I2C chip fake for driver {driver!r} - add one to machine._build_i2c_chip()")


class Pin:
    # Configuration follows rp2's init helper: a Pin re-configured without pull loses its pull, value is applied
    # before an output mode, and every Pin(n) is one static object (ports/rp2/machine_pin.c v1.29.0).
    TEST_API = ("id", "mode", "pull", "alt", "simulate_edge", "set_external_level", "value_log", "reset_registry")
    IN = 0  # ports/rp2/machine_pin.h:34-37 (v1.29.0), as OUT, OPEN_DRAIN and ALT
    OUT = 1
    OPEN_DRAIN = 2
    ALT = 3
    ALT_I2C = 3  # GPIO_FUNC_I2C (pico-sdk structs/io_bank0.h:34; machine_pin.c:513)
    _ALT_SIO = 5  # GPIO_FUNC_SIO (io_bank0.h:36), rp2's alt default (machine_pin.c:247)
    PULL_UP = 1  # GPIO_PULL_UP / _DOWN (machine_pin.c:505-506)
    PULL_DOWN = 2
    IRQ_FALLING = 0x04  # GPIO_IRQ_EDGE_FALL / _RISE (machine_pin.c:507-508)
    IRQ_RISING = 0x08

    _registry: "dict[int, Pin]" = {}
    # Per GPIO id: the level the outside world puts on the line (twin-only test knob, default 1: the
    # bus pull-ups) and every level the code drove onto it.
    _external: "dict[int, int | Callable[[int, BoundedLog[int]], int]]" = {}
    _value_logs: "dict[int, BoundedLog[int]]" = {}
    _initialized: bool
    id: int

    def __init__(self, id: "int | str | Pin", mode: "int | None" = _OMITTED, pull: "int | None" = _OMITTED, *, value: object = _OMITTED, alt: int = _OMITTED) -> None:
        if not self._initialized:
            self.mode: int | None = None
            self.pull: int | None = None
            self.alt = self._ALT_SIO
            self._value = 0
            self._irq_handler: Callable[[Pin], None] | None = None
            self._irq_trigger = self.IRQ_FALLING | self.IRQ_RISING
            self._irq_hard = False
            self._initialized = True
        # rp2 configures when any argument beyond the id is given, None included (machine_pin.c:317-323).
        if mode is not _OMITTED or pull is not _OMITTED or value is not _OMITTED or alt is not _OMITTED:
            self.init(
                None if mode is _OMITTED else mode,
                None if pull is _OMITTED else pull,
                value=None if value is _OMITTED else value,
                alt=self._ALT_SIO if alt is _OMITTED else alt,
            )

    def __new__(cls, id: "int | str | Pin", *_args: object, **_kwargs: object) -> "Pin":
        number = cls._find(id)
        existing = cls._registry.get(number)
        if existing is not None:
            return existing
        instance = super().__new__(cls)
        instance._initialized = False
        instance.id = number
        cls._registry[number] = instance
        return instance

    def _drive(self, level: int) -> None:
        self._value = level
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
    def set_external_level(cls, id: int, level: "int | Callable[[int, BoundedLog[int]], int]") -> None:
        # Twin-only test knob: what the outside world drives onto line `id`; a callable is asked on every
        # read with (id, the line's value log), so a test can script a slave releasing SDA after k clocks.
        cls._external[id] = level

    def init(self, mode: "int | None" = None, pull: "int | None" = None, *, value: object = None, alt: int = _ALT_SIO) -> None:
        # machine_pin_obj_init_helper(), machine_pin.c:250-310: a None mode keeps the mode; value= is latched only by OUT
        # (before the mode applies) and OPEN_DRAIN (released when omitted); any other mode hands the pad to `alt`.
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
                    self._value = 1 if level is None else level
                elif level is not None and (mode == self.OUT or external):
                    self._value = level
                self.mode = mode
                self.alt = self._ALT_SIO
            else:
                if alt not in _pin_alts(self.id):
                    raise ValueError(f"invalid pin af: {alt}")
                self.mode = self.ALT
                self.alt = alt
        if not external:
            # Set unconditionally, None meaning no pull (machine_pin.c:300-306): rp2 keeps the PULL_UP/PULL_DOWN bits.
            self.pull = 0 if pull is None else pull & (self.PULL_UP | self.PULL_DOWN)

    def irq(self, handler: "Callable[[Pin], None] | None" = _absent_handler, trigger: int = _OMITTED, *, hard: object = _OMITTED) -> "Pin":
        # rp2 (machine_pin.c:464-476): an external pin raises first; a bare call returns the IRQ object (the Pin stands
        # in) unchanged; any argument replaces handler, trigger and hard outright.
        if self.id >= _NUM_BANK0_GPIOS:
            raise ValueError("expecting a regular GPIO Pin")
        if handler is _absent_handler and trigger is _OMITTED and hard is _OMITTED:
            return self
        self._irq_handler = None if handler is _absent_handler else handler
        self._irq_trigger = self.IRQ_FALLING | self.IRQ_RISING if trigger is _OMITTED else trigger
        self._irq_hard = hard is not _OMITTED and bool(hard)
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
        if self.mode == self.IN and ((self.pull or 0) & self.PULL_UP or self.id in Pin._external):
            return self._line()
        return self._value

    @classmethod
    def value_log(cls, id: int) -> "BoundedLog[int]":
        # Twin-only test knob: the last levels value()/on()/off()/toggle() drove onto line `id`, oldest first.
        log = cls._value_logs.get(id)
        if log is None:
            log = cls._value_logs[id] = BoundedLog(_VALUE_LOG_MAXLEN)
        return log


# One machine-wide set of peripheral registries: rp2's I2C/SPI/UART objects are static per id (machine_i2c.c:87).
_I2C_OBJECTS: "dict[int, I2C]" = {}
_SPI_OBJECTS: "dict[int, SPI]" = {}
_UART_OBJECTS: "dict[int, UART]" = {}


def _current_wiring_plan() -> "Mapping[str, object]":
    if _wiring_plan is None:
        raise RuntimeError("no wiring plan configured - call machine.configure_wiring(plan) before constructing a bus")
    return _wiring_plan


def _in_flight_queue() -> "deque[tuple[int, int]]":
    # Flag 1 = FLAG_CHECK_OVERFLOW: a full queue raises IndexError instead of silently dropping its oldest byte
    # (py/objdeque.c:40, 107-108).
    queue: deque[tuple[int, int]] = deque((), _UART_INFLIGHT_MAX, 1)  # type: ignore[call-overload]  # MicroPython's deque takes flags
    return queue


def _in_running_task() -> bool:
    # MicroPython's loop keeps its running task in asyncio.core's cur_task (extmod/asyncio/core.py:259, v1.29.0), read
    # without the RuntimeError current_task() allocates per call; any other asyncio answers through current_task().
    core = sys.modules.get("asyncio.core")
    if core is not None:
        return getattr(core, "cur_task", None) is not None
    try:
        asyncio.current_task()
    except RuntimeError:
        return False
    return True


_random_source: "_RandomSource | None" = None


_scd30_state_path: "str | None" = None
_current_scd30_chip: "SCD30Chip | None" = None


def _pin_alts(pin_id: int) -> "tuple[int, ...]":
    # The functions boards/rp2040_af.csv lists for the pin, AFn being GPIO_FUNC n: GPCK (8) only on GPIO20-25.
    return (1, 2, 3, 4, 5, 6, 7, 8, 9) if 20 <= pin_id <= 25 else (1, 2, 3, 4, 5, 6, 7, 9)


def _pin_number(pin: "Pin | int") -> int:
    return pin.id if isinstance(pin, Pin) else Pin._find(pin)


_wiring_plan: "Mapping[str, object] | None" = None


def _plan_table(name: str, section: object, key: str) -> object:
    # One entry of the plan's "buses" or "spi" table, None when absent; any other shape is a plan this twin cannot wire.
    # The caller reads the table with a constant key, so the wiring contract sees each key this twin reads.
    if not isinstance(section, dict):
        raise TypeError(f"wiring plan's {name!r} is not a table - see buildgen.twin_wiring.compute_twin_wiring()")
    return section.get(key)


# Every configure_*() hook runs before the buses it affects exist; a later call raises instead of silently doing nothing.
def _report_uncaught(exc: BaseException, *, hard: bool) -> None:
    # A callback's uncaught exception, printed as rp2 prints it: a hard one by mp_irq_dispatch() before its schedule stops
    # (shared/runtime/mpirq.c:91-92), a soft one by the scheduler's protected call (py/scheduler.c:115).
    if hard:
        print("Uncaught exception in IRQ callback handler")
    sys.print_exception(exc)


def _require_unconstructed(hook: str) -> None:
    if _I2C_OBJECTS or _SPI_OBJECTS or _UART_OBJECTS:
        raise RuntimeError(f"machine.{hook}() after a bus was constructed has no effect - call it before build_system(), or machine.reset_peripherals() first")


def _simulation_timer() -> "Timer":
    # The Timer a chip fake's own clock runs on: a simulation clock, not an rp2 alarm, so it never takes from the pool.
    return Timer(_pool=False)


def _valid_mem_backup_state(state: object) -> "tuple[int, int, int, list[list[int]]] | None":
    # (cause, REASON, CHIP_RESET, regions) of a state file flush_mem_backup() wrote, or None for any other shape.
    if not isinstance(state, dict):
        return None
    words = [state.get("cause"), state.get("watchdog_reason"), state.get("chip_reset")]
    regions = state.get("regions")
    if not isinstance(regions, list) or [len(r) if isinstance(r, list) else -1 for r in regions] != [len(r) for r in _REGIONS]:
        return None
    for value in words + [w for r in regions for w in r]:
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFFFFFFFF:
            return None
    return words[0], words[1], words[2], regions  # type: ignore[return-value]  # each checked an int above


def _wire_i2c_devices(bus_id: int) -> "dict[int, Any]":
    attachments: list[_I2CAttachment] = _plan_table("buses", _current_wiring_plan()["buses"], f"i2c{bus_id}") or []  # type: ignore[assignment]  # the plan's JSON shape
    return {attachment["address"]: _build_i2c_chip(attachment) for attachment in attachments}


def _wire_spi_device(bus_id: int) -> "FRAMChip | None":
    global _current_fram_chip
    attachment: _SPIAttachment | None = _plan_table("spi", _current_wiring_plan()["spi"], f"spi{bus_id}")  # type: ignore[assignment]  # the plan's JSON shape
    if attachment is None:
        return None
    max_size = attachment["max_size"]
    rdid = _FRAM_RDID_BY_MAX_SIZE.get(max_size)
    if rdid is None:
        raise ValueError(f"no FRAM RDID for size {max_size:#x} - add it to machine._FRAM_RDID_BY_MAX_SIZE")
    chip = FRAMChip(size=max_size, rdid_response=rdid, state_path=_fram_state_path)
    _current_fram_chip = chip
    return chip


def set_alarm_pool_free(n: int) -> None:
    # Test-only: lets an L2 test exhaust or refill rp2's alarm pool; silicon has no such call.
    global _ALARMS_FREE
    _ALARMS_FREE = n


class I2C:
    # One static object per bus id, as ports/rp2/machine_i2c.c:80-87 (v1.29.0): a re-construction re-initialises the
    # controller and keeps the wired chips, their queued faults and the log.
    TEST_API = ("id", "scl", "sda", "freq", "timeout", "deinit_called", "devices", "log", "nack_after", "unplug", "plug")
    _wired: bool

    def __init__(self, id: int, freq: int = 400000, *, scl: "Pin | int", sda: "Pin | int", timeout: int = 50000) -> None:
        scl_id, sda_id = _pin_number(scl), _pin_number(sda)
        if not (scl_id & 1 == 1 and (scl_id & 2) >> 1 == id):  # IS_VALID_SCL, machine_i2c.h:65
            raise ValueError("bad SCL pin")
        if not (sda_id & 1 == 0 and (sda_id & 2) >> 1 == id):  # IS_VALID_SDA, machine_i2c.h:66
            raise ValueError("bad SDA pin")
        if not self._wired:
            self.deinit_called = False
            self.log: BoundedLog[tuple[object, ...]] = BoundedLog(LOG_MAXLEN)
            self.devices = _wire_i2c_devices(id)  # public: tests reach a wired chip via i2c.devices[addr]
            # Twin-only test knob: address -> the ACK count the next write to it reports, a data or
            # register byte the chip NACKed (pico-sdk i2c.c:229-231); the chip takes none of that write.
            self.nack_after: dict[int, int] = {}
            self._pointers: dict[int, int] = {}  # per register chip: the register the next read starts at
            self._unplugged: dict[int, Any] = {}  # chips pulled off the bus by unplug(), kept for plug()
            self._wired = True
            _I2C_OBJECTS[id] = self
        # Every construction initialises (:105-115): the controller takes both pins, each with its pull-up.
        self.id = id
        self.scl = Pin(scl_id, Pin.ALT, Pin.PULL_UP, alt=Pin.ALT_I2C)
        self.sda = Pin(sda_id, Pin.ALT, Pin.PULL_UP, alt=Pin.ALT_I2C)
        self.freq = freq
        self.timeout = timeout
        self.log.append(("init", freq, timeout))

    def __new__(cls, id: int, *_args: object, **_kwargs: object) -> "I2C":
        existing = _I2C_OBJECTS.get(id)
        if existing is not None:
            return existing
        if id not in (0, 1):
            raise ValueError(f"I2C({id}) doesn't exist")  # machine_i2c.c:80-82
        bus = super().__new__(cls)
        bus._wired = False
        return bus

    def _device_or_nak(self, address: int, *, probe: bool = False) -> "_I2CDevice":
        # A zero-length write goes through soft I2C, where a NAK reads ENODEV (machine_i2c.c:127-145, extmod/machine_i2c.c:199-203).
        device: _I2CDevice | None = self.devices.get(address)
        if device is None:
            raise OSError(errno.ENODEV) if probe else OSError(errno.EIO, "no ACK from device")
        return device

    def _general_call(self, data: bytes, stop: bool) -> int:
        # The general call reaches only chips whose datasheet documents it (the SGP40, Table 17); no listener means no ACK.
        self.log.append(("writeto", 0x00, data, stop))
        listeners = [chip for chip in self.devices.values() if hasattr(chip, "handle_general_call")]
        if not listeners:
            raise OSError(errno.EIO, "no ACK from device")
        for chip in listeners:
            chip.handle_general_call(data)
        return len(data)

    def deinit(self) -> None:
        # Real rp2 I2C.deinit() exists only from 1.29, and even there the port's protocol slot is
        # NULL - a silent no-op leaving the peripheral and pins as they were (Part F.5). Every bus
        # operation keeps working here on purpose; the flag only records the call.
        self.deinit_called = True

    def plug(self, address: int) -> None:
        # Twin-only test knob: a sensor pulled and re-seated on a running unit - it powers up afresh, its pointer reset.
        if address not in self._unplugged:
            raise ValueError(f"no chip unplugged at 0x{address:02x}")
        chip = self._unplugged.pop(address)
        chip.power_cycle()
        self._pointers.pop(address, None)
        self.devices[address] = chip

    def readfrom_into(self, address: int, buf: "bytearray | memoryview", stop: bool = True) -> None:
        device = self._device_or_nak(address)
        nbytes = len(buf)
        register_chip = getattr(device, "REGISTER_ADDRSIZE", 0)
        data = device.handle_readfrom_mem(self._pointers.get(address, 0), nbytes) if register_chip else device.handle_readfrom_into(nbytes)
        fill_buffer(buf, data)
        self.log.append(("readfrom_into", address, data, stop))

    def readfrom_mem(self, address: int, memaddr: int, nbytes: int, *, addrsize: int = 8) -> bytes:
        device = self._device_or_nak(address)
        data = device.handle_readfrom_mem(memaddr, nbytes)
        self.log.append(("readfrom_mem", address, memaddr, nbytes, addrsize))
        return data

    def readfrom_mem_into(self, address: int, memaddr: int, buf: "bytearray | memoryview", *, addrsize: int = 8) -> None:
        # Delegates, so fault injection (--fault <chip>:readfrom_mem) and the bus log stay one
        # implementation regardless of which of the two read forms the driver under test calls.
        fill_buffer(buf, self.readfrom_mem(address, memaddr, len(buf), addrsize=addrsize))

    def scan(self) -> "list[int]":
        return sorted(self.devices)

    def unplug(self, address: int) -> None:
        # Twin-only test knob: a sensor pulled and re-seated on a running unit - until plug() it answers nothing.
        if address not in self.devices:
            raise ValueError(f"no chip wired at 0x{address:02x}")
        self._unplugged[address] = self.devices.pop(address)

    def writeto(self, address: int, buf: object, stop: bool = True) -> int:
        data = bytes(buf)  # type: ignore[call-overload]
        if address == 0x00:
            return self._general_call(data, stop)
        device = self._device_or_nak(address, probe=not data)
        acked = self.nack_after.pop(address, len(data))
        if acked < len(data):
            self.log.append(("writeto", address, data, stop))
            return acked
        # A chip declaring REGISTER_ADDRSIZE is register-addressed: address bytes plus payload are a
        # register write, address bytes alone set the pointer the next read starts at, nothing is the probe.
        n = getattr(device, "REGISTER_ADDRSIZE", 0) // 8
        try:
            if n and len(data) >= n:
                register = int.from_bytes(data[:n], "big")
                if len(data) > n:
                    device.handle_writeto_mem(register, data[n:])
                self._pointers[address] = register
            else:
                device.handle_writeto(data)
        except OSError as e:
            if data or e.errno == errno.ETIMEDOUT:
                raise
            raise OSError(errno.ENODEV) from None  # the probe's NAK, as an absent chip's
        self.log.append(("writeto", address, data, stop))
        return len(data)

    def writeto_mem(self, address: int, memaddr: int, buf: object, *, addrsize: int = 8) -> None:
        device = self._device_or_nak(address)
        device.handle_writeto_mem(memaddr, bytes(buf))  # type: ignore[call-overload]
        self.log.append(("writeto_mem", address, memaddr, bytes(buf), addrsize))  # type: ignore[call-overload]


_fram_state_path: "str | None" = None
_current_fram_chip: "FRAMChip | None" = None


def attach_crossover_jumper(fake_a: "UART", fake_b: "UART") -> "tuple[UARTLink, LinkPoller, LinkPoller]":
    # Models the dev bench's permanent GP0<->GP9 / GP1<->GP8 jumper (tests_hardware/README.md 'The dev
    # bench'): the twin's dev graph builds both ends but joins neither. The returned pollers are bounded
    # (CLAUDE.md's known CI hang).
    return UARTLink(fake_a, fake_b), LinkPoller(fake_a), LinkPoller(fake_b)


def bootloader() -> None:
    global bootloader_count, reset_cause_value, watchdog_reason_value
    bootloader_count = saturating_add(bootloader_count)
    reset_cause_value = WDT_RESET  # assumption: the fidelity table
    watchdog_reason_value = _REASON_FORCE
    raise SimulatedBootloaderEntryError("machine.bootloader() called - the twin does not actually restart the process")


# Keyed by size, the only chip fact a device TOML carries; pinned to asy_fram_driver._KNOWN_PRODUCT_IDS by
# tests/test_digital_twin_fram.py.
_FRAM_RDID_BY_MAX_SIZE: "dict[int, bytes]" = {
    0x2000: bytes([0x04, 0x7F, 0x03, 0x02]),  # MB85RS64V, datasheets/fram/MB85RS64V-DS501-00015-4v0-E.pdf p.10
    0x40000: bytes([0x04, 0x7F, 0x48, 0x03]),  # MB85RS2MTA, datasheets/fram/MB85RS2MTA-DS501-00032-3v0-E.pdf p.10
}


def configure_fram_state_path(path: "str | None") -> None:
    # Called once, before build_system() constructs spi0, by the twin's entry points (launch.py,
    # run_generic_integration.py) - src/ never calls this: zero twin-awareness in src/ (owner, 2026-09-26: 'zero artifacts
    # specifically added for testing'). None (the default) means "in-memory only, no persistence".
    _require_unconstructed("configure_fram_state_path")
    global _fram_state_path
    _fram_state_path = path


class SPI:
    # One static object per bus id, as ports/rp2/machine_spi.c:161-167 (v1.29.0): a re-construction re-applies every
    # setting, omitted ones at rp2's defaults, and keeps the wired chip.
    TEST_API = (
        "id", "sck", "mosi", "miso", "baudrate", "polarity", "phase", "bits", "firstbit", "deinit_called", "device", "log",
        "rx_overrun", "rx_overrun_remaining", "lose_power_after", "wire_time_us_per_byte",
    )  # fmt: skip
    MSB = 1  # pico-sdk SPI_MSB_FIRST/SPI_LSB_FIRST at the pinned submodule (hardware/spi.h:184-187)
    LSB = 0
    _wired: bool

    def __init__(
        self,
        id: int,
        baudrate: int = 1000000,
        *,
        polarity: int = 0,
        phase: int = 0,
        bits: int = 8,
        firstbit: int = MSB,
        sck: "Pin | int",
        mosi: "Pin | int",
        miso: "Pin | int | None" = None,
    ) -> None:
        # SPI0 takes GP0-7/16-23, SPI1 GP8-15/24-29; SCK, MOSI, MISO each on its own pin of four (machine_spi.c:88-95).
        sck_id, mosi_id = _pin_number(sck), _pin_number(mosi)
        miso_id = None if miso is None else _pin_number(miso)
        for role, number, low_bits in (("SCK", sck_id, 2), ("MOSI", mosi_id, 3), ("MISO", miso_id, 0)):
            if number is not None and not (number & 3 == low_bits and (number & 8) >> 3 == id):
                raise ValueError(f"bad {role} pin")
        if not self._wired:
            self.deinit_called = False
            self.log: BoundedLog[tuple[object, ...]] = BoundedLog(LOG_MAXLEN)
            self.device = _wire_spi_device(id)  # public: tests reach the wired chip via spi.device
            # 1.29 added an RX-overrun check to rp2's SPI transfer path, reached only by READING
            # 32+ bytes (Part F.5.2). Modelled here rather than on the chip's FaultInjector because
            # it belongs to the port, not the device: sticky, plus a counted transient form.
            self.rx_overrun = False
            self.rx_overrun_remaining = 0
            self._power_left: int | None = None  # lose_power_after()'s countdown; None: power stays on
            # Twin-only test knob: blocking wire time, so a long FRAM pass takes its real clock (8 us/byte at 1 MHz).
            self.wire_time_us_per_byte = 0
            self._wired = True
            _SPI_OBJECTS[id] = self
        if firstbit == self.LSB:
            raise NotImplementedError("LSB")  # rp2's hardware SPI is MSB-first only (:203-205)
        self.id = id
        self.sck = Pin(sck_id)
        self.mosi = Pin(mosi_id)
        self.miso = None if miso_id is None else Pin(miso_id)
        self.baudrate = baudrate
        self.polarity = polarity
        self.phase = phase
        self.bits = bits
        self.firstbit = firstbit
        self.log.append(("init", baudrate, polarity, phase, bits, firstbit))

    def __new__(cls, id: int, *_args: object, **_kwargs: object) -> "SPI":
        existing = _SPI_OBJECTS.get(id)
        if existing is not None:
            return existing
        if id not in (0, 1):
            raise ValueError(f"SPI({id}) doesn't exist")  # machine_spi.c:161-164
        bus = super().__new__(cls)
        bus._wired = False
        return bus

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

    def _read(self, buf: "bytearray | memoryview", write_value: int) -> None:
        self._maybe_overrun(len(buf))
        if self.device is not None:
            self.device.readinto(buf)
        else:
            fill_buffer(buf, b"")  # an undriven MISO reads 0x00 (fidelity table)
        self.log.append(("readinto", len(buf), write_value))

    def _transaction(self, nbytes: int) -> None:
        # One SPI transfer's twin-only effects: the armed power loss, then the blocking wire time.
        if self._power_left is not None:
            if self._power_left > 0:
                self._power_left -= 1
            else:
                raise SimulatedPowerLoss("power lost after the armed SPI transaction count")
        if self.wire_time_us_per_byte:
            time.sleep_us(nbytes * self.wire_time_us_per_byte)

    def _write(self, data: bytes) -> None:
        if self.device is not None:
            self.device.write(data)
        self.log.append(("write", data))

    def deinit(self) -> None:
        # Same NULL-slot no-op as I2C.deinit() above, and on rp2 SPI it has always been one
        # (SPECIFICATION.md Part F.5) - the flag only records that the call was forwarded.
        self.deinit_called = True

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

    def lose_power_after(self, k: int) -> None:
        # Twin-only test knob: the k+1-th transaction loses power, and every one after it.
        self._power_left = k

    def readinto(self, buf: "bytearray | memoryview", write_value: int = 0x00) -> None:
        self._transaction(len(buf))
        self._read(buf, write_value)

    def write(self, buf: object) -> None:
        data = bytes(buf)  # type: ignore[call-overload]
        self._transaction(len(data))
        self._write(data)

    def write_readinto(self, buffer_out: object, buffer_in: "bytearray | memoryview") -> None:
        if len(buffer_out) != len(buffer_in):  # type: ignore[arg-type]
            raise ValueError("buffers must be the same length")
        self._transaction(len(buffer_in))  # one full-duplex transfer: one count, one wire time
        self._write(bytes(buffer_out))  # type: ignore[call-overload]
        self._read(buffer_in, 0x00)



_UART_BITS_PER_BYTE = 10  # 8N1 on the wire: one start bit, eight data bits, one stop bit
# Claimed rp2.DMA channels by number: digital_twin/rp2.py registers here, so a UART finds the channel draining it.
_DMA_CHANNELS: "dict[int, DMA]" = {}
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
        self.dropped_delayed = 0  # bytes the delay knob could not hold: past the receiver's capacity
        self.pending = bytearray()  # held by the delay knob
        self.in_flight = _in_flight_queue()  # (due_us, byte)
        self.wire_log = _WireLog(_WIRE_LOG_MAXLEN)  # the newest bytes that reached the destination

    def byte_time_us(self) -> int:
        return (_UART_BITS_PER_BYTE * 1_000_000) // max(self.baudrate, 1)

    def record(self, byte: int) -> None:
        # Counts and logs a byte that reached the destination.
        self.delivered = saturating_add(self.delivered)
        self.wire_log.append(byte)

    def shape(self, data: bytes) -> bytearray:
        out = bytearray()
        for byte in data:
            offset = self.offered
            self.offered = saturating_add(self.offered)
            if self.silent:
                continue
            if self.truncate_after is not None and offset >= self.truncate_after:
                continue
            if offset in self.drop_indices:
                continue
            out.append(byte ^ self.corrupt_indices.get(offset, 0))
        return out


def configure_mem_backup_state_path(path: "str | None") -> None:
    # A present, valid state file is applied, then deleted: it describes one simulated reset, read by the launch after it.
    _require_unconstructed("configure_mem_backup_state_path")
    global _mem_backup_state_path, reset_cause_value, watchdog_reason_value, chip_reset_value
    _mem_backup_state_path = path or None
    if _mem_backup_state_path is None:
        return
    try:
        with open(_mem_backup_state_path) as f:
            state = json.load(f)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise  # a path that cannot be read is the runner's fault, never a power-on
        return  # a launch not preceded by a simulated reset is a power-on
    except ValueError as e:
        print(f"machine: mem_backup state file {_mem_backup_state_path} unreadable ({e}) - booting as a power-on")
        return
    fields = _valid_mem_backup_state(state)
    if fields is None:
        print(f"machine: mem_backup state file {_mem_backup_state_path} has the wrong shape - booting as a power-on")
        return
    reset_cause_value, watchdog_reason_value, chip_reset_value, regions = fields
    for index, words in enumerate(regions):
        for i, word in enumerate(words):
            _REGIONS[index][i] = word
    os.remove(_mem_backup_state_path)


def configure_random_source(source: "_RandomSource | None") -> None:
    # Every chip's value walk draws from `source` (launch.py's --seed); None leaves each on the un-seeded module.
    _require_unconstructed("configure_random_source")
    global _random_source
    _random_source = source


def configure_scd30_state_path(path: "str | None") -> None:
    # The SCD30's NVM-persisted settings file; None, the default, keeps them in memory only.
    _require_unconstructed("configure_scd30_state_path")
    global _scd30_state_path
    _scd30_state_path = path


def configure_wiring(plan: "Mapping[str, object]") -> None:
    # A plain dict in buildgen.twin_wiring.compute_twin_wiring()'s own shape, the board every later bus construction wires.
    _require_unconstructed("configure_wiring")
    global _wiring_plan
    if "buses" not in plan or "spi" not in plan:
        raise ValueError("wiring plan must be a dict with 'buses' and 'spi' keys - see buildgen.twin_wiring.compute_twin_wiring()'s own docstring for the shape")
    _wiring_plan = plan


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
        # Wire time is plain microseconds since construction, not raw ticks (the arithmetic below mixes it with byte
        # durations), read off _flash_stall's plain clock: no ticks_diff() spans the link's life, none ever wraps.
        self._stall_offset_us = _flash_stall.plain_us(time.ticks_us(), time.ticks_ms())  # wire time 0 on the plain clock
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
                due, byte = direction.in_flight.popleft()
                # A byte arriving inside a flash stall's window meets no running RX interrupt, whatever UARTIMSC says.
                irqs_off = bool(_flash_stall.windows) and _flash_stall.irqs_were_off(self._stall_offset_us + due)
                if irqs_off or not dest.imsc & _IMSC_RX_IRQ:
                    dest._route(byte, irqs_off=irqs_off)  # no interrupt: into a DMA ring or the FIFO
                    direction.record(byte)
                    continue
                if len(dest.rx_queue) >= direction.capacity:
                    direction.dropped_overrun = saturating_add(direction.dropped_overrun)
                    continue
                dest.rx_queue.append(byte)
                direction.record(byte)

    def _index(self, uart: "UART") -> int:
        return 0 if uart is self.endpoints[0] else 1

    def _now_us(self) -> int:
        # The offset plus a due time is the plain clock's time, where _flash_stall keeps its windows.
        return _flash_stall.plain_us(time.ticks_us(), time.ticks_ms()) - self._stall_offset_us

    def _schedule(self, index: int, direction: "_LinkDirection", data: bytearray) -> None:
        now = self._now_us()
        due = max(now, self._next_free_us[index])
        step = direction.byte_time_us()
        for byte in data:
            due += step
            # A full in-flight queue is a receive overrun by another name - counted and dropped, never raised into the driver.
            try:
                direction.in_flight.append((due, byte))
            except IndexError:
                direction.dropped_overrun = saturating_add(direction.dropped_overrun)
        self._next_free_us[index] = due

    def detach(self, uart: "UART") -> None:
        # Breaks the link for both ends at once: a half-attached link would deliver into an
        # endpoint nothing reads from, which is the mis-routing this exists to prevent.
        if uart not in self.endpoints:
            return
        for endpoint in self.endpoints:
            endpoint._link = None
        # Rebound rather than cleared: MicroPython's deque has no clear().
        self.a_to_b.in_flight = _in_flight_queue()
        self.b_to_a.in_flight = _in_flight_queue()

    def direction_from(self, uart: "UART") -> "_LinkDirection":
        if uart not in self.endpoints:
            raise ValueError("UART is not an endpoint of this link")
        return self.a_to_b if self._index(uart) == 0 else self.b_to_a

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
        # Test-only (no alternative: a synchronous assertion cannot await the wire): waits out the in-flight bytes' own
        # wire time, never inside a running task; the shared contract's fidelity seam (tests/_uart_link_contract.py).
        if _in_running_task():
            raise RuntimeError("settle() blocks the interpreter - call it from synchronous test code, outside asyncio.run()")
        deadline = 0
        for direction in (self.a_to_b, self.b_to_a):
            if direction.in_flight:
                deadline = max(deadline, direction.in_flight[-1][0] + 1)  # a byte's due time is its stop bit's end
        self._advance()
        while self.a_to_b.in_flight or self.b_to_a.in_flight:
            remaining = deadline - self._now_us()
            if remaining <= 0:
                self._advance()  # the deadline passed before this check (a loaded host): every byte is due now
                break
            time.sleep_us(remaining)
            self._advance()

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
            room = max(0, direction.capacity - len(direction.pending))
            direction.pending += shaped[:room]
            direction.dropped_delayed = saturating_add(direction.dropped_delayed, max(0, len(shaped) - room))
            return
        self._schedule(index, direction, shaped)


class UART(io.IOBase):
    # Held to tests/_uart_link_contract.py's semantics; ioctl() answers EINVAL to all but POLL as rp2 does
    # (machine_uart.c:694-697), so a real select.poll() never takes the fd path (extmod/modselect.c:252-266) - tests
    # still swap in a bounded poller. io.IOBase lets init() register it with a real select.poll().
    #
    # Receive model: with RXIM/RTIM set (every construction and init()) the RX interrupt moves each byte
    # into rx_queue, machine.UART's own buffer, as its wire time elapses. With both cleared, each byte goes
    # to a DMA channel draining this UART, else to the 32-byte FIFO, past which it sets OE and is lost.
    TEST_API = (
        "id", "tx", "rx", "baudrate", "bits", "parity", "stop", "rxbuf", "txbuf", "timeout", "timeout_char", "invert",
        "deinit_called", "rx_queue", "writable", "write_limit", "rx_api_calls", "rx_fifo_dropped", "rsr", "imsc", "dmacr",
        "would_have_blocked_bytes", "real_poll_queries", "plant_rx_error", "poll_mask", "ioctl",
    )  # fmt: skip
    _MP_STREAM_POLL = 3  # py/stream.h:39
    _DEFAULT_BUFFER_SIZE = 256  # ports/rp2/machine_uart.c:67-69, as MIN and MAX
    _MIN_BUFFER_SIZE = 32
    _MAX_BUFFER_SIZE = 32766
    _DEFAULT_BAUDRATE = 115200  # machine_uart.c:39
    _UART_INVERT_MASK = 3  # UART_INVERT_TX (1) | UART_INVERT_RX (2), machine_uart.c:82-84
    # Bytes a read asked for that had not arrived. On real hardware each one costs a synchronous
    # timeout_char wait inside the C read, never yielding to asyncio (SPECIFICATION.md Part F.5.8);
    # these fakes serve what they hold and return, so the stall is counted here instead of taken.
    would_have_blocked_bytes = 0
    # POLL requests a real select.poll() made of a UART fake: LinkPoller and the shared contract read poll_mask(), so
    # the after-each check fails any test leaving this above 0 (a real poll over a fake is CLAUDE.md's CI hang).
    real_poll_queries = 0
    rx_api_calls: int  # set by __new__ and stepped only through saturating_add(), so declared here for mypy
    rx_fifo_dropped: int

    def __init__(
        self,
        id: int,
        baudrate: int = -1,
        bits: int = -1,
        parity: "int | None" = -1,
        stop: int = -1,
        *,
        tx: "Pin | int | None" = None,
        rx: "Pin | int | None" = None,
        txbuf: int = -1,
        rxbuf: int = -1,
        timeout: int = -1,
        timeout_char: int = -1,
        invert: int = -1,
    ) -> None:
        # One static object per UART id, as ports/rp2/machine_uart.c:469 (v1.29.0); a re-construction re-initialises it,
        # its ring re-allocated empty at the default size (:470-473); an attached link stays (the jumper is wiring).
        self.rxbuf = self.txbuf = self._DEFAULT_BUFFER_SIZE
        self.rx_queue = bytearray()
        self.init(baudrate, bits, parity, stop, tx=tx, rx=rx, txbuf=txbuf, rxbuf=rxbuf, timeout=timeout, timeout_char=timeout_char, invert=invert)

    def __new__(cls, id: int, *_args: object, **_kwargs: object) -> "UART":
        existing = _UART_OBJECTS.get(id)
        if existing is not None:
            return existing
        if id not in (0, 1):
            raise ValueError(f"UART({id}) doesn't exist")
        uart: UART = super().__new__(cls)
        # machine_uart_obj[], machine_uart.c:130-137: baudrate 0 until a first init, 8N1, the bus's default pins.
        uart.id = id
        uart.baudrate, uart.bits, uart.parity, uart.stop = 0, 8, None, 1
        uart.tx, uart.rx = Pin((0, 4)[id]), Pin((1, 5)[id])
        uart.timeout = uart.timeout_char = uart.invert = 0
        uart.deinit_called = False
        uart.writable = True
        uart.write_limit = None
        uart._link = None
        uart.rx_api_calls = 0  # every any()/read()/readinto()/readline() and POLLIN poll: a DMA reader makes none
        uart.rx_fifo_dropped = 0  # bytes lost to a full FIFO, each also setting OE
        uart._reset_block()
        _UART_OBJECTS[id] = uart
        return uart

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

    def _channel(self) -> "DMA | None":
        if not self.dmacr & _DMACR_RXDMAE:
            return None
        for channel in _DMA_CHANNELS.values():
            if channel._accept(_UART_BASES[self.id], _RX_DREQ[self.id]):
                return channel
        return None

    def _count_overask(self, asked: int) -> None:
        if asked > len(self.rx_queue):
            UART.would_have_blocked_bytes = saturating_add(UART.would_have_blocked_bytes, asked - len(self.rx_queue))

    @classmethod
    def _for_data_register(cls, address: int) -> "UART | None":
        return _UART_OBJECTS.get(_UART_BASES.index(address)) if address in _UART_BASES else None

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

    def _route(self, byte: int, *, is_break: bool = False, irqs_off: bool = False) -> None:
        # One arrived byte: the interrupt takes it while unmasked, running and its buffer has room (it drops a break's
        # 0x00, machine_uart.c:163-176), else the DMA (only while RX is masked), else the FIFO.
        if self.imsc & _IMSC_RX_IRQ and not irqs_off and len(self.rx_queue) < self.rxbuf:
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
            self.rx_fifo_dropped = saturating_add(self.rx_fifo_dropped)

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
        self.rx_api_calls = saturating_add(self.rx_api_calls)
        self._update()
        return len(self.rx_queue)

    def deinit(self) -> None:
        # Real deinit() resets the UART block (uart_deinit()): every register back to its reset value.
        self.deinit_called = True
        self.imsc = 0
        self.dmacr = 0
        self.rsr = 0
        self._fifo = bytearray()  # the object stays registered: rp2's UART objects are static

    def init(
        self,
        baudrate: int = -1,
        bits: int = -1,
        parity: "int | None" = -1,
        stop: int = -1,
        *,
        tx: "Pin | int | None" = None,
        rx: "Pin | int | None" = None,
        **settings: int,
    ) -> None:
        # mp_machine_uart_init_helper(), machine_uart.c:261-455: each given setting in rp2's order, then uart_init()
        # (which re-enables the RX interrupts and both DREQs) when any was given or none ever was. `settings` takes
        # the int keywords txbuf, rxbuf, timeout, timeout_char and invert; any other raises as py/argcheck.c:129.
        txbuf, rxbuf, timeout = settings.pop("txbuf", -1), settings.pop("rxbuf", -1), settings.pop("timeout", -1)
        timeout_char, invert = settings.pop("timeout_char", -1), settings.pop("invert", -1)
        if settings:
            raise TypeError("extra keyword arguments given")
        given = (baudrate, bits, stop, txbuf, rxbuf, timeout, timeout_char, invert) != (-1,) * 8 or parity != -1 or tx is not None or rx is not None
        if baudrate > 0:
            self.baudrate = baudrate
        if bits > 0:
            self.bits = bits
        if parity != -1:
            self.parity = parity
        if stop > 0:
            self.stop = stop
        for role, pin, low_bits in (("TX", tx, 0), ("RX", rx, 1)):
            if pin is not None:
                number = _pin_number(pin)
                if not (number & 3 == low_bits and ((number + 4) & 8) >> 3 == self.id):  # IS_VALID_TX/RX, :73-78
                    raise ValueError(f"bad {role} pin")
                if role == "TX":
                    self.tx = Pin(number)
                else:
                    self.rx = Pin(number)
        if timeout >= 0:
            self.timeout = timeout
        if timeout_char >= 0:
            self.timeout_char = timeout_char
        if invert >= 0:
            if invert & ~self._UART_INVERT_MASK:
                raise ValueError("bad inversion mask")
            self.invert = invert
        if rxbuf > 0:
            if rxbuf > self._MAX_BUFFER_SIZE:
                raise ValueError("rxbuf too large")
            self.rxbuf = max(rxbuf, self._MIN_BUFFER_SIZE)
        if txbuf > 0:
            if txbuf > self._MAX_BUFFER_SIZE:
                raise ValueError("txbuf too large")
            self.txbuf = max(txbuf, self._MIN_BUFFER_SIZE)
        if given or self.baudrate == 0:
            if self.baudrate == 0:
                self.baudrate = self._DEFAULT_BAUDRATE
                self.timeout_char = 0
            self.timeout_char = max(self.timeout_char, 13000 // self.baudrate + 1)  # one 13-bit character (:406-410)
            self._reset_block()

    def ioctl(self, req: int, arg: int) -> int:
        if req != self._MP_STREAM_POLL:
            return -errno.EINVAL  # MP_STREAM_GET_FILENO included: rp2's answer (machine_uart.c:694-697)
        UART.real_poll_queries = saturating_add(UART.real_poll_queries)  # only a real select.poll() comes this way
        return self.poll_mask(arg)

    def plant_rx_error(self, bits: int) -> None:
        # Twin-only test knob: sets UARTRSR bits (OE 0x08, BE 0x04, FE 0x01); a break also receives one
        # 0x00 character (RP2040 datasheet 4.2.8, Table 426).
        self._update()
        self.rsr |= bits & 0x0F
        if bits & _RSR_BE:
            self._route(0, is_break=True)

    def poll_mask(self, mask: int) -> int:
        # Twin-only test knob: the POLL answer for the events in `mask`, what LinkPoller and the shared contract read.
        if mask & select.POLLIN:
            self.rx_api_calls = saturating_add(self.rx_api_calls)
        self._update()
        ready = 0
        if (mask & select.POLLIN) and self.rx_queue:
            ready |= select.POLLIN
        if (mask & select.POLLOUT) and self.writable:
            ready |= select.POLLOUT
        return ready

    def read(self, nbytes: int | None = None) -> bytes | None:
        self.rx_api_calls = saturating_add(self.rx_api_calls)
        self._update()
        self._count_overask(len(self.rx_queue) if nbytes is None else nbytes)
        n = len(self.rx_queue) if nbytes is None else min(nbytes, len(self.rx_queue))
        if n == 0:
            return None
        data = bytes(self.rx_queue[:n])
        self.rx_queue = self.rx_queue[n:]
        return data

    def readinto(self, buf: "bytearray | memoryview", nbytes: int | None = None) -> int | None:
        self.rx_api_calls = saturating_add(self.rx_api_calls)
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
        self.rx_api_calls = saturating_add(self.rx_api_calls)
        self._update()
        queued = len(self.rx_queue)
        idx = self.rx_queue.find(b"\n")
        if idx != -1 and (size < 0 or idx < size):
            end = idx + 1
        elif size < 0:
            end = queued
            UART.would_have_blocked_bytes = saturating_add(UART.would_have_blocked_bytes)
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
    # Bounded stand-in, never a real select.poll(): the fake's readiness must be scripted, not polled in real time
    # (CLAUDE.md "Known hang cause"); a real poll object can also segfault on its pollfds growth on the Unix port
    # (digital_twin/unix_port_poll_prewarm.py). As tests/machine.py's, it reads poll_mask() on every call.
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
        event = self._uart.poll_mask(self._mask)
        return [(None, event)] if event else []

    def register(self, obj: object, mask: int = 0) -> None:
        pass

    def unregister(self, obj: object) -> None:
        pass


_ALARM_POOL_SIZE = 16  # PICO_TIME_DEFAULT_ALARM_POOL_MAX_TIMERS (pico-sdk pico/time.h:352-362), SPECIFICATION.md F.1
_ALARMS_FREE = _ALARM_POOL_SIZE
_TIMER_MAX_SLEEP_MS = 0x1FFFFFFF  # one sleep_ms() step at most: rp2's ticks_add() refuses half its 2**30 period


def flush_fram() -> None:
    # Called once at shutdown by each twin entry point, never from src/: an explicit save, so a run costs the host one
    # state-file write (README "FRAM persistence").
    if _current_fram_chip is not None:
        _current_fram_chip.save_state()


class Timer:
    ONE_SHOT = 0
    PERIODIC = 1
    TEST_API = ("id", "mode", "callback", "period", "drop_next_soft_callbacks")  # rp2's Timer exposes none of them
    # Test-only: the next N soft callbacks of any Timer are lost, as while rp2's depth-8 scheduler queue is full
    # (ports/rp2/mpconfigport.h:131, py/scheduler.c:163-181, v1.29.0); off by default, reset_test_state() clears it.
    drop_next_soft_callbacks = 0

    def __init__(
        self,
        id: int = -1,
        *,
        mode: int = PERIODIC,
        callback: "Callable[[Timer], None] | None" = None,
        period: int = 0xFFFFFFFF,
        tick_hz: int = 1000,
        freq: "float | None" = None,
        hard: bool = False,
        _pool: bool = True,
    ) -> None:
        if id != -1:
            raise ValueError("Timer doesn't exist")  # only the soft timer exists (ports/rp2/machine_timer.c:127-129)
        self.id = id
        self.mode = mode
        self.callback: Callable[[Timer], None] | None = None
        self.period = period
        self._pool = _pool  # False: a chip fake's simulation clock, not an rp2 alarm - it never touches the pool
        self._has_alarm = False
        self._gen = 0
        self._task: asyncio.Task[None] | None = None
        self._period_us = 1
        self._hard = False
        # Spelled out rather than **kwargs-forwarded so the accepted settings are statically checked; any setting
        # runs init(), as machine_timer_make_new() does (:131-136), so a bare Timer() takes no alarm.
        if mode != self.PERIODIC or callback is not None or period != 0xFFFFFFFF or tick_hz != 1000 or freq is not None or hard:
            self.init(mode=mode, callback=callback, period=period, tick_hz=tick_hz, freq=freq, hard=hard)

    def _free_alarm(self) -> None:
        global _ALARMS_FREE
        if self._has_alarm:
            self._has_alarm = False
            _ALARMS_FREE += 1

    async def _run(self, gen: int) -> None:
        # The Unix-port asyncio schedules in ms (fidelity row). A soft callback's exception is printed by the scheduler
        # and the alarm re-arms (py/scheduler.c:115, machine_timer.c:50-60, v1.29.0); only a hard one stops.
        try:
            while True:
                remaining = max(1, self._period_us // 1000)
                while remaining > 0:
                    step = min(remaining, _TIMER_MAX_SLEEP_MS)
                    await asyncio.sleep_ms(step)
                    remaining -= step
                if self._gen != gen:
                    return  # a re-init() from inside the callback superseded this loop
                callback = self.callback
                if callback is not None and not self._hard and Timer.drop_next_soft_callbacks > 0:
                    # mpirq.c:105 ignores the full queue's refusal; the alarm re-arms anyway (machine_timer.c:50-60).
                    Timer.drop_next_soft_callbacks -= 1
                elif callback is not None:
                    try:
                        callback(self)
                    except Exception as e:  # a BaseException (the twin's reset, power loss) ends the loop
                        _report_uncaught(e, hard=self._hard)
                        if self._hard:
                            self._free_alarm()
                            return
                if self._gen != gen:
                    return
                if self.mode == self.ONE_SHOT:
                    self._free_alarm()
                    return
        except asyncio.CancelledError:
            if self._gen == gen:
                self._free_alarm()  # the harness cancelling a loop is a soft reset: its alarm is free again

    def deinit(self) -> None:
        # A callback that re-arms runs inside the superseded loop's task, which a MicroPython Task cannot cancel; the
        # bumped generation ends that loop after the callback returns.
        self._gen = (self._gen + 1) & COUNTER_CAP  # a masked sequence: only equality is ever asked of it
        if self._task is not None:
            try:
                is_own_callback = self._task is asyncio.current_task()
            except RuntimeError:  # no running event loop: a synchronous caller, never this Timer's own callback
                is_own_callback = False
            if not is_own_callback:
                self._task.cancel()
            self._task = None
        self._free_alarm()
        self.callback = None

    def init(
        self,
        *,
        mode: int = PERIODIC,
        callback: "Callable[[Timer], None] | None" = None,
        period: int = 0xFFFFFFFF,
        tick_hz: int = 1000,
        freq: "float | None" = None,
        hard: bool = False,
    ) -> None:
        global _ALARMS_FREE
        self.deinit()  # cancels a running schedule first, returning its alarm, as rp2's init() does (machine_timer.c:143-146)
        for value in (mode, period, tick_hz):  # then MP_ARG_INT on rp2 (:77-80): a float raises with nothing armed
            if not isinstance(value, int):
                raise TypeError("can't convert " + type(value).__name__ + " to int")
        self.mode = mode
        self.period = period
        self.callback = callback
        self._hard = hard
        self._period_us = max(1, int(1_000_000 / freq) if freq is not None else period * 1_000_000 // tick_hz)  # :88-103
        if self._pool:
            if _ALARMS_FREE <= 0:
                raise OSError(errno.ENOMEM)  # rp2 adds the alarm whether or not a callback is given (:107-110)
            _ALARMS_FREE -= 1
            self._has_alarm = True
        self._task = asyncio.get_event_loop().create_task(self._run(self._gen))


# RP2040 cap: 0xffffff / 2 / 1000 ms (ports/rp2/machine_wdt.c:32-38, v1.29.0, SPECIFICATION.md F.1); a larger timeout
# or any id but 0 raises ValueError, as rp2.
_WDT_TIMEOUT_MAX_MS = 8388


class WDT:
    TEST_API = ("id", "timeout", "feed_count", "would_have_triggered_count", "would_have_triggered_log", "feed_times")

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
        # Twin-only: an asyncio countdown since the last feed() that records a would-have-reset rather than acting, with
        # no disable API (a real armed WDT has none) - digital_twin/README.md 'WDT._arm()'s late-feed backstop'.
        self.would_have_triggered_count = 0
        self.would_have_triggered_log: BoundedLog[int] = BoundedLog(LOG_MAXLEN)  # feed_count at each notification
        # ticks_ms() of each feed, newest last: the gap checks of the ownership tests read it.
        self.feed_times: BoundedLog[_TicksMs] = BoundedLog(LOG_MAXLEN)
        self._on_would_trigger = on_would_trigger
        self._task: asyncio.Task[None] | None = None
        self._armed_at_ms: _TicksMs | None = None
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
        self.would_have_triggered_count = saturating_add(self.would_have_triggered_count)
        self.would_have_triggered_log.append(self.feed_count)
        if self._on_would_trigger is not None:
            self._on_would_trigger(self)

    def feed(self) -> None:
        self.feed_count = saturating_add(self.feed_count)
        self.feed_times.append(time.ticks_ms())
        self._arm()  # a real feed() resets the hardware countdown - restart ours the same way


class _Mem32:
    # machine.mem32: 32-bit peripheral register access (extmod/machine_mem.c). Models the two reset registers and the
    # UART blocks' UARTRSR/UARTECR, UARTIMSC and UARTDMACR of the live UART per id; any other address raises
    # ValueError ("not modelled"). Every access is recorded in `log` as ("read"|"write", address, value).
    def __init__(self) -> None:
        self.log: BoundedLog[tuple[str, int, int]] = BoundedLog(_MEM32_LOG_MAXLEN)

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
                uart = _UART_OBJECTS.get(uart_id)
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

def flush_mem_backup() -> None:
    # Called only by the runners' reset handler: carries the regions and both reset registers to the next launch.
    if _mem_backup_state_path is None:
        return
    state = {"cause": reset_cause_value, "watchdog_reason": watchdog_reason_value, "chip_reset": chip_reset_value, "regions": [list(r) for r in _REGIONS]}
    with open(_mem_backup_state_path, "w") as f:
        json.dump(state, f)


def flush_scd30() -> None:
    # Called once at shutdown by each twin entry point, never from src/: an explicit save, so a run costs the host one
    # state-file write (README "FRAM persistence").
    if _current_scd30_chip is not None:
        _current_scd30_chip.save_state()


# mem_backup(): rp2's two watchdog-scratch regions; they survive machine.reset() (carried to the next launch by the
# reset handler) and are cleared by power-on (v1.29.0 machine_mem_backup.c:36-40); the bootloader carry-over is an
# assumption (digital_twin/README.md fidelity table).
_mem_backup_state_path: "str | None" = None


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


def peripheral(name: str) -> "I2C | SPI | UART | None":
    # Twin-only: the one way the runner and tests reach a booted bus, never through a product wrapper's private attribute.
    for prefix, registry in (("i2c", _I2C_OBJECTS), ("spi", _SPI_OBJECTS), ("uart", _UART_OBJECTS)):
        if name.startswith(prefix) and name[len(prefix) :].isdigit():
            found: I2C | SPI | UART | None = registry.get(int(name[len(prefix) :]))
            return found
    raise ValueError(f"unknown peripheral name {name!r} - expected i2c<n>, spi<n> or uart<n>")


def power_on() -> None:
    # Twin-only test knob: a power cycle clears both regions, reports PWRON_RESET and leaves REASON 0, HAD_POR set.
    global reset_cause_value, watchdog_reason_value, chip_reset_value
    for region in _REGIONS:
        for i in range(len(region)):
            region[i] = 0
    reset_cause_value = PWRON_RESET
    watchdog_reason_value = 0
    chip_reset_value = _HAD_POR


def reset() -> None:
    # Real machine.reset() never returns; this twin cannot restart anything, so it raises instead. The counter
    # and the cause (rp2 resets through the watchdog) step first, so a harness catching the error can read both.
    global reset_count, reset_cause_value, watchdog_reason_value
    reset_count = saturating_add(reset_count)
    reset_cause_value = WDT_RESET
    watchdog_reason_value = _REASON_FORCE  # CHIP_RESET is left as it was: a watchdog reset clears no HAD_* bit
    raise SimulatedResetError("machine.reset() called - the twin does not actually restart the process")


_RTC_DEFAULT = (2021, 1, 1, 0, 0, 0)  # Y, M, D, h, m, s: rp2 starts the RTC at 2021-01-01 00:00:00 (ports/rp2/main.c:143)


class RTC:
    # One static peripheral (class-level state, as rp2). With the runner's wall clock installed (_wall_clock.py) a set
    # moves time.time()/gmtime() as on silicon (ports/rp2/machine_rtc.c:64-97, v1.29.0).
    TEST_API = ()
    _shared_datetime: "tuple[int, ...]" = _RTC_DEFAULT

    def __init__(self) -> None:
        pass  # rp2's RTC() takes no argument (machine_rtc.c:52)

    if TYPE_CHECKING:

        @overload
        def datetime(self, dt: None = None) -> "tuple[int, ...]": ...
        @overload
        def datetime(self, dt: "tuple[int, ...] | list[int]") -> None: ...

    def datetime(self, dt: "tuple[int, ...] | list[int] | None" = None) -> "tuple[int, ...] | None":
        # The getter recomputes the weekday and reads field 7 as 0; a set takes 8 fields and stores 6 (:66-96).
        clock = _wall_clock.installed()
        if dt is None:
            fields = clock.gmtime()[:6] if clock is not None else RTC._shared_datetime
            weekday = time.gmtime(_wall_clock.epoch_seconds(*fields))[6]
            return fields[0], fields[1], fields[2], weekday, fields[3], fields[4], fields[5], 0
        if len(dt) != 8:
            raise ValueError("tuple/list has wrong length")
        RTC._shared_datetime = (dt[0], dt[1], dt[2], dt[4], dt[5], dt[6])
        if clock is not None:
            clock.set_wall(_wall_clock.epoch_seconds(*RTC._shared_datetime))
        return None


class SimulatedRebootError(BaseException):
    # BaseException, not Exception: no product `except Exception` may survive a reset, and asyncio re-raises it out of the
    # running loop (extmod/asyncio/core.py:154, 194, v1.29.0) - the twin's reset ends the process as silicon's ends the program.
    pass


class SimulatedResetError(SimulatedRebootError):
    pass


class SimulatedBootloaderEntryError(SimulatedRebootError):
    pass


class SimulatedPowerLoss(BaseException):
    # Twin-only: SPI.lose_power_after() fired; a runner seeing it flushes FRAM/SCD30 state but never mem_backup (a
    # power-on clears it, machine_mem_backup.c:36-40).
    pass


reset_count = 0
bootloader_count = 0


def reset_cause() -> int:
    return reset_cause_value


def reset_peripherals() -> None:
    # Test-only: silicon never forgets its peripherals; test isolation needs it (owner, 2026-09-25: "Only if there is no
    # alternative, and keep tiny anyway"). Its DMA channels are freed too, as a soft reset's finalisers leave them.
    _I2C_OBJECTS.clear()
    _SPI_OBJECTS.clear()
    _UART_OBJECTS.clear()
    for channel in list(_DMA_CHANNELS.values()):
        channel.close()


def reset_test_state() -> None:
    # Test-only: restores every process-wide twin knob a test can change; each twin test file registers it with
    # microtest.after_each() (the twin never has tests/ on its path).
    global _wiring_plan, _random_source, _fram_state_path, _scd30_state_path, _mem_backup_state_path
    global _current_fram_chip, _current_scd30_chip, _ALARMS_FREE, reset_count, bootloader_count
    reset_peripherals()
    Pin.reset_registry()
    _wiring_plan = _random_source = _fram_state_path = _scd30_state_path = _mem_backup_state_path = None
    _current_fram_chip = None
    _current_scd30_chip = None
    _ALARMS_FREE = _ALARM_POOL_SIZE
    polled = UART.real_poll_queries
    UART.would_have_blocked_bytes = 0
    UART.real_poll_queries = 0
    Timer.drop_next_soft_callbacks = 0
    reset_count = 0
    bootloader_count = 0
    power_on()
    mem32.log.clear()
    _flash_stall.reset_test_state()
    RTC._shared_datetime = _RTC_DEFAULT
    _wall_clock.reset_test_state()
    if polled:
        raise AssertionError(f"a real select.poll() queried a UART fake {polled} times")
