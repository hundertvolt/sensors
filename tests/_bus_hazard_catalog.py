"""Generic, TOML-bus-membership-driven cross-sensor hazard scenarios (SPECIFICATION.md Part C.8)
plus the small per-I2C-driver adapter catalog they run against. Shared wire-frame helpers moved
here from test_bus_hazard_multi_device.py so both files build identical bytes."""

import asyncio
import struct
import time

import microtest
from _fast_sleep import FastAsyncSleep
from _src_const import src_int
from machine import I2C as FakeI2C
from machine import Pin

import asy_i2c_driver
from asy_bmp3xx_driver import BMP3XX_I2C
from asy_i2c_driver import I2C
from asy_isl29125_driver import ISL29125_I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterable

    from _twin_devices import I2CAttachment

_GENERAL_CALL_ADDR = 0x00
_TRANSFER_OPS = ("writeto", "readfrom_into", "readfrom_mem", "writeto_mem")  # the fake bus log's addressed transfers


# I2C spec reserved address ranges (0x00-0x07 general call, CBUS, reserved and Hs-mode; 0x78-0x7F 10-bit
# addressing and reserved), checked against every real occupant's TOML-declared address and by
# test_bus_hazard_multi_device.py against every promoted driver's own.
RESERVED_I2C_RANGES = ((0x00, 0x07), (0x78, 0x7F))


# ---------------------------------------------------------------------------
# Shared wire-frame construction helpers (moved from test_bus_hazard_multi_device.py - both files
# need byte-identical frames, so this is the one place that builds them).
# ---------------------------------------------------------------------------


# BMP3xx: a fixed, reproducible calibration/ADC dataset - the same one test_bus_hazard_multi_device.py used
# before this catalog absorbed it, and the same one test_asy_bmp3xx_driver.py uses - not re-deriving the
# compensation math here, only a deterministic known-good reading to detect a concurrency-torn read.
_BMP_CAL_RAW = struct.pack(
    "<HHbhhbbHHbbhbb",
    28617, 26074, -10, -3944, -10416, 26, 0, 30462, 120, 4, 0, 4285, 22, -60,
)
_BMP_ADC_P = 8300000
_BMP_ADC_T = 8500000
BMP_EXPECTED_TEMPERATURE = 28.460795242070162  # by hand: the formulae of BMP388 datasheet §9.1-9.2 over the planted bytes
_BMP_EXPECTED_PRESSURE_HPA = 713.765147356092


# Known-good values the seed helpers above feed back through a clean read - every _read_once_*
# below asserts against these, so a concurrent-write hazard that tears a read is actually caught.
_SCD_CO2 = 412.5
_SCD_TEMPERATURE = 23.4
_SCD_HUMIDITY = 45.6
_SGP_RAW = 0x8000
_ISL_COUNTS = (0x2000, 0x1800, 0x1000)


# ---------------------------------------------------------------------------
# Per-driver adapter: enough to construct, seed and drive one instance generically, without this module
# knowing which concrete driver it is. Only covers drivers that actually share a bus with another on some
# real device today; one with no bus-sharing neighbour is added the moment a device wires it alongside one.
# ---------------------------------------------------------------------------


class I2CHazardAdapter:
    # A plain class, not @dataclass - `dataclasses` has no stub in the MicroPython-target typeshed this file
    # checks under, and no driver or test module in src/tests/digital_twin imports it either; buildgen,
    # which is genuinely CPython-only, is the one place in this repo that uses it.
    def __init__(
        self,
        driver: str,
        construct: "Callable[[I2C, int], object]",  # (shared fake bus, this occupant's own address) -> driver instance
        seed: "Callable[[FakeI2C, int, int], None]",  # (fake bus, this occupant's own address, iteration count) -> queues/registers enough for that many clean reads
        read_once: "Callable[[object], Coroutine[object, object, None]]",  # one correctness-checked read cycle; raises on corruption
        exercise: "Callable[[object], Coroutine[object, object, None]]",  # sweeps this driver's own public API, for the address-sweep scenario
        default_address: "Callable[[I2C], int]",  # the address the driver binds when constructed with none
        *,
        write_once: "Callable[[object], Coroutine[object, object, None]] | None" = None,  # one safe, non-destructive config write, if this driver has one
        general_call: "Callable[[object], Coroutine[object, object, None]] | None" = None,  # a real I2C general-call broadcast this driver issues on its own, if any
    ) -> None:
        self.driver = driver
        self.construct = construct
        self.seed = seed
        self.read_once = read_once
        self.exercise = exercise
        self.default_address = default_address
        self.write_once = write_once
        self.general_call = general_call
        self.exercise_raises: tuple[type[BaseException], ...] = ()
        self.releases_bus_mid_read = False

    def declare(self, *, exercise_raises: "tuple[type[BaseException], ...]" = (), releases_bus_mid_read: bool = False) -> "I2CHazardAdapter":
        # What the driver declares beside its callables: what exercise() may raise on a bus seeded for reads only, and
        # whether a read cycle frees the bus between its command and its reply (a conversion wait).
        self.exercise_raises = exercise_raises
        self.releases_bus_mid_read = releases_bus_mid_read
        return self


# Every seed() attaches its address, so a raw-command chip answers its presence probe (tests/machine.py: rp2's probe
# of an absent address raises ENODEV), and leaves the chip ready for `iterations` clean reads.


def _seed_scd30(fake_bus: FakeI2C, address: int, iterations: int) -> None:
    # Keyed by address, not the shared fake_bus.read_queue: SCD30 speaks the same register-less, write-then-
    # read protocol shape SGP40 does, so when both share a bus their replies must not be pulled from one
    # address-agnostic FIFO - hence tests/machine.py's read_queue_by_address.
    fake_bus.attached.add(address)
    queue = fake_bus.read_queue_by_address.setdefault(address, [])
    for _ in range(iterations):
        queue.append(scd_register_frame(1))
        queue.append(scd_data_frame(_SCD_CO2, _SCD_TEMPERATURE, _SCD_HUMIDITY))


async def _read_once_scd30(instance: object) -> None:
    assert isinstance(instance, SCD30_I2C)
    await instance.read_measurement()
    co2 = await instance.get_CO2()
    assert co2 is not None and abs(co2 - _SCD_CO2) < 1e-6, f"a concurrent hazard corrupted SCD30's own read: {co2!r}, expected {_SCD_CO2!r}"


async def _write_once_scd30(instance: object) -> None:
    assert isinstance(instance, SCD30_I2C)
    await instance.set_temperature_offset(12.34)


# What each exercise may raise, declared and nothing else caught: a CRC check over frames seeded for the read
# cycle (SCD30, SGP40), the reset check the fake's register model cannot answer (ISL29125). BMP3XX raises nothing.
_SCD30_EXERCISE_RAISES: "tuple[type[BaseException], ...]" = (RuntimeError,)
_SGP40_EXERCISE_RAISES: "tuple[type[BaseException], ...]" = (RuntimeError,)
_ISL29125_EXERCISE_RAISES: "tuple[type[BaseException], ...]" = (RuntimeError,)
_BMP3XX_EXERCISE_RAISES: "tuple[type[BaseException], ...]" = ()


async def _exercise_scd30(instance: object) -> None:
    assert isinstance(instance, SCD30_I2C)
    for call in (
        instance.setup,
        instance.reset,
        instance.get_measurement_interval,
        instance.get_self_calibration_enabled,
        instance.get_ambient_pressure,
        instance.get_altitude,
        instance.get_temperature_offset,
        instance.get_forced_recalibration_reference,
        instance.get_config_snapshot,
        instance.read_measurement,
        instance.stop_continuous_measurement,
        lambda: instance.set_measurement_interval(5),
        lambda: instance.set_self_calibration_enabled(True),
        lambda: instance.set_ambient_pressure(1013),
        lambda: instance.set_altitude(100),
        lambda: instance.set_temperature_offset(1.0),
        lambda: instance.set_forced_recalibration_reference(500),
    ):
        try:
            await call()
        except _SCD30_EXERCISE_RAISES:
            pass


def _seed_sgp40(fake_bus: FakeI2C, address: int, iterations: int) -> None:
    # Keyed by address - see _seed_scd30's own comment for why (the two share a bus when a TOML puts them on one).
    fake_bus.attached.add(address)
    queue = fake_bus.read_queue_by_address.setdefault(address, [])
    for _ in range(iterations):
        queue.append(sgp_word(_SGP_RAW))


async def _read_once_sgp40(instance: object) -> None:
    assert isinstance(instance, SGP40_I2C)
    raw = await instance.measure_raw(temperature=25, relative_humidity=50)
    assert raw == _SGP_RAW, f"a concurrent hazard corrupted SGP40's own read: {raw!r}, expected {_SGP_RAW!r}"


async def _general_call_sgp40(instance: object) -> None:
    assert isinstance(instance, SGP40_I2C)
    await instance._reset()


async def _exercise_sgp40(instance: object) -> None:
    assert isinstance(instance, SGP40_I2C)
    for call in (
        instance.setup,
        instance.turn_heater_off,  # the participant rung's command: the sweep proves it touches 0x59 only
        instance.get_raw,
        lambda: instance.measure_raw(25, 50),
        lambda: instance.measure_index_and_raw(25, 50),
    ):
        try:
            await call()
        except _SGP40_EXERCISE_RAISES:
            pass


def _seed_isl29125(fake_bus: FakeI2C, address: int, iterations: int) -> None:
    # Register-addressed: one register model (device ID, CONFIG1-3, status, counts) serves any number of reads.
    del iterations
    fake_bus.attached.add(address)
    _ready_isl(fake_bus, address)


# The two whole CONFIG1-3 states a read may see: the seeded one, and the same after _write_once_isl29125's
# CONFIG2-3 burst (IR compensation adjust 20 = 0x14, FN8424 p.10 Table 8). Anything else is a torn snapshot.
_ISL_CONFIG_STATES = (bytes(3), bytes([0x00, 0x14, 0x00]))


async def _read_once_isl29125(instance: object) -> None:
    assert isinstance(instance, ISL29125_I2C)
    # The reader's cycle: STATUS, the 3-byte CONFIG snapshot, then the counts, each its own session block.
    await instance.read_status()
    config = await instance.get_config_snapshot()
    assert config in _ISL_CONFIG_STATES, f"a concurrent hazard tore ISL29125's CONFIG snapshot: {config!r}"
    counts = await instance.read_counts()
    assert counts == _ISL_COUNTS, f"a concurrent hazard corrupted ISL29125's own read: {counts!r}, expected {_ISL_COUNTS!r}"


async def _write_once_isl29125(instance: object) -> None:
    assert isinstance(instance, ISL29125_I2C)
    await instance.configure(ir_adjust=20)


async def _exercise_isl29125(instance: object) -> None:
    assert isinstance(instance, ISL29125_I2C)
    for call in (
        instance.setup,
        instance.reset,
        instance.get_device_id,
        instance.read_status,
        instance.clear_brownout,
        instance.read_counts,
        instance.get_config_snapshot,
        lambda: instance.configure(mode=0x05, range_fs=375, resolution=12),
        lambda: instance.set_thresholds(983, 55705),
    ):
        try:
            await call()
        except _ISL29125_EXERCISE_RAISES:
            pass


def _seed_bmp3xx(fake_bus: FakeI2C, address: int, iterations: int) -> None:
    # Register-addressed, as _seed_isl29125: the ready model with the calibration bytes BMP_EXPECTED_TEMPERATURE is from.
    del iterations
    fake_bus.attached.add(address)
    _ready_bmp(fake_bus, address)


async def _read_once_bmp3xx(instance: object) -> None:
    assert isinstance(instance, BMP3XX_I2C)
    # setup() is genuinely async (reads+parses real calibration registers) and I2CHazardAdapter's
    # own construct() is sync-only (matching every other adapter here) - primed lazily on this
    # occupant's own first read, exactly once, same as a real driver caller would do at boot.
    if not hasattr(instance, "_temp_calib"):
        await instance.setup()
    assert await instance.take_por_detected() is False, "BMP3xx reported a chip reset nobody issued"  # the reader's per-cycle EVENT read
    pressure, temperature = await instance.get_pressure_and_temperature()
    assert abs(pressure - _BMP_EXPECTED_PRESSURE_HPA) < 1e-6, f"a concurrent hazard corrupted BMP3xx's own pressure read: {pressure!r}, expected {_BMP_EXPECTED_PRESSURE_HPA!r}"
    assert abs(temperature - BMP_EXPECTED_TEMPERATURE) < 1e-6, f"a concurrent hazard corrupted BMP3xx's own temperature read: {temperature!r}, expected {BMP_EXPECTED_TEMPERATURE!r}"


async def _write_once_bmp3xx(instance: object) -> None:
    assert isinstance(instance, BMP3XX_I2C)
    # Volatile config register (datasheet-confirmed, see test_bus_hazard_multi_device.py's own
    # bmp3xx same-device-concurrency comment) - safe to exercise with no real-hardware write budget.
    await instance.set_pressure_oversampling(2)


async def _exercise_bmp3xx(instance: object) -> None:
    assert isinstance(instance, BMP3XX_I2C)
    for call in (
        instance.setup,
        instance.reset,
        instance.get_pressure,
        instance.get_temperature,
        instance.get_pressure_and_temperature,
        instance.get_pressure_altitude,
        instance.get_pressure_oversampling,
        instance.get_temperature_oversampling,
        instance.get_filter_coefficient,
        instance.get_config_snapshot,
        instance.take_por_detected,
        lambda: instance.set_pressure_oversampling(2),
        lambda: instance.set_temperature_oversampling(2),
        lambda: instance.set_filter_coefficient(3),
    ):
        try:
            await call()
        except _BMP3XX_EXERCISE_RAISES:
            pass


def _construct_bmp3xx(i2c: I2C, address: int) -> BMP3XX_I2C:
    bmp = BMP3XX_I2C(i2c, address=address)
    seed_bmp_ready(i2c, address)
    return bmp


# Each driver constructed with no address, read back through its own I2CDevice: what a TOML omitting one would get.
def _default_address_bmp3xx(i2c: I2C) -> int:
    return BMP3XX_I2C(i2c)._i2c_bmp3xx.i2c_device.device_address


def _default_address_scd30(i2c: I2C) -> int:
    return SCD30_I2C(i2c)._i2c_scd30.i2c_device.device_address


def _default_address_sgp40(i2c: I2C) -> int:
    return SGP40_I2C(i2c)._i2c_sgp40.i2c_device.device_address


def _default_address_isl29125(i2c: I2C) -> int:
    return ISL29125_I2C(i2c)._i2c_isl29125.i2c_device.device_address


# The three chips with a hard-wired address take none (SPECIFICATION.md K.3); `address` still keys the seeding.
def _construct_scd30(i2c: I2C, _address: int) -> SCD30_I2C:
    return SCD30_I2C(i2c)


def _construct_sgp40(i2c: I2C, _address: int) -> SGP40_I2C:
    return SGP40_I2C(i2c)


def _construct_isl29125(i2c: I2C, address: int) -> ISL29125_I2C:
    isl = ISL29125_I2C(i2c)
    seed_isl_ready(i2c, address)
    return isl


I2C_HAZARD_CATALOG: "dict[str, I2CHazardAdapter]" = {
    "scd30": I2CHazardAdapter("scd30", _construct_scd30, _seed_scd30, _read_once_scd30, _exercise_scd30, _default_address_scd30, write_once=_write_once_scd30).declare(exercise_raises=_SCD30_EXERCISE_RAISES),
    "sgp40": I2CHazardAdapter("sgp40", _construct_sgp40, _seed_sgp40, _read_once_sgp40, _exercise_sgp40, _default_address_sgp40, general_call=_general_call_sgp40).declare(exercise_raises=_SGP40_EXERCISE_RAISES, releases_bus_mid_read=True),
    "isl29125": I2CHazardAdapter("isl29125", _construct_isl29125, _seed_isl29125, _read_once_isl29125, _exercise_isl29125, _default_address_isl29125, write_once=_write_once_isl29125).declare(exercise_raises=_ISL29125_EXERCISE_RAISES),
    "bmp3xx": I2CHazardAdapter("bmp3xx", _construct_bmp3xx, _seed_bmp3xx, _read_once_bmp3xx, _exercise_bmp3xx, _default_address_bmp3xx, write_once=_write_once_bmp3xx).declare(exercise_raises=_BMP3XX_EXERCISE_RAISES),
}

# No SPI bus carries two occupants in any TOML (a wiring plan's SPI bus holds one attachment), so no adapter yet; a
# second occupant reaches the same actionable KeyError the I2C catalog raises.
SPI_HAZARD_CATALOG: "dict[str, object]" = {}


# ---------------------------------------------------------------------------
# One real bus occupant (an adapter bound to one constructed instance at one real address), and the
# generic cross-sensor scenarios that drive a whole bus's worth of them at once.
# ---------------------------------------------------------------------------


class BusOccupant:
    # Plain class, same reasoning as I2CHazardAdapter above.
    def __init__(self, adapter: I2CHazardAdapter, instance: object, address: int, i2c: I2C) -> None:
        self.adapter = adapter
        self.instance = instance
        self.address = address
        self.i2c = i2c  # the shared bus wrapper, for a scenario that drives the bus itself (a recovery)


def _bmp_data6(adc_p: int, adc_t: int) -> bytes:
    def triplet(v: int) -> bytes:
        return bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF])

    return triplet(adc_p) + triplet(adc_t)


def _ready_bmp(fake_bus: FakeI2C, address: int, chip_id: int = 0x50) -> None:
    # STATUS: cmd_rdy | drdy_press | drdy_temp; ERR_REG clear; EVENT clear - see test_asy_bmp3xx_driver.py's own
    # ready_bmp() for the same shape. The driver's burst reads ERR_REG, STATUS and the data as one file from 0x02.
    status = 0x10 | 0x60
    fake_bus.registers[(address, 0x03)] = bytearray([status])  # _REGISTER_STATUS
    fake_bus.registers[(address, 0x02)] = bytearray([0x00, status]) + _bmp_data6(_BMP_ADC_P, _BMP_ADC_T)  # _REGISTER_ERR to 0x09
    fake_bus.registers[(address, 0x10)] = bytearray([0x00])  # _REGISTER_EVENT, por_detected clear
    # _REGISTER_CHIPID: 0x50 (BMP384/388) by default, 0x60 (BMP390) on request - both documented IDs
    fake_bus.registers[(address, 0x00)] = bytearray([chip_id])
    fake_bus.registers[(address, 0x31)] = bytearray(_BMP_CAL_RAW)  # _REGISTER_CAL_DATA


def _ready_isl(fake_bus: FakeI2C, address: int) -> None:
    fake_bus.registers[(address, 0x00)] = bytearray([0x7D])  # device ID (p9, Table 2)
    fake_bus.registers[(address, 0x01)] = bytearray([0x00, 0x00, 0x00])  # CONFIG1-3, post-reset
    fake_bus.registers[(address, 0x08)] = bytearray([0x00])  # status, BOUTF already clear
    fake_bus.registers[(address, 0x09)] = bytearray(struct.pack("<HHH", 0x2000, 0x1800, 0x1000))


async def _run_general_call_vs_siblings_at_offset(fake_bus: FakeI2C, occupants: "list[BusOccupant]", iterations: int, offset: int) -> None:
    broadcasters = [occ for occ in occupants if occ.adapter.general_call is not None]
    others = [occ for occ in occupants if occ.adapter.general_call is None]
    for occ in others:
        occ.adapter.seed(fake_bus, occ.address, iterations)

    async def sibling_loop(occ: BusOccupant) -> None:
        for _ in range(iterations):
            await occ.adapter.read_once(occ.instance)
            await asyncio.sleep(0)

    async def broadcast_loop(occ: BusOccupant) -> None:
        assert occ.adapter.general_call is not None
        for _ in range(offset):
            await asyncio.sleep(0)
        await occ.adapter.general_call(occ.instance)

    await asyncio.gather(*(sibling_loop(occ) for occ in others), *(broadcast_loop(occ) for occ in broadcasters))

    assert any(entry[0] == "writeto" and entry[1] == _GENERAL_CALL_ADDR for entry in fake_bus.log), "the general call never fired - this scenario isn't exercising the hazard"


async def _run_own_write_vs_own_read_at_offset(fake_bus: FakeI2C, occ: BusOccupant, iterations: int, offset: int) -> None:
    assert occ.adapter.write_once is not None
    occ.adapter.seed(fake_bus, occ.address, iterations)
    reads_completed = 0
    write_completed = False

    async def reader_loop() -> None:
        nonlocal reads_completed
        for _ in range(iterations):
            await occ.adapter.read_once(occ.instance)
            reads_completed += 1
            await asyncio.sleep(0)

    async def writer_loop() -> None:
        nonlocal write_completed
        assert occ.adapter.write_once is not None
        for _ in range(offset):
            await asyncio.sleep(0)
        await occ.adapter.write_once(occ.instance)
        write_completed = True

    await asyncio.gather(reader_loop(), writer_loop())
    assert reads_completed == iterations, f"only {reads_completed}/{iterations} of {occ.adapter.driver}'s own reads completed"
    assert write_completed, f"{occ.adapter.driver}'s own concurrent write never completed"


async def _run_recovery_vs_siblings_at_offset(fake_bus: FakeI2C, occupants: "list[BusOccupant]", iterations: int, offset: int) -> None:
    # The recovery starts once every occupant has read once (first reads include setup waits), then
    # `offset` yields in; SDA stays held through all nine pulses, each release stretched five 1 ms
    # reads, so the clear spans ~50 ms - longer than any occupant's wait between its transfers.
    i2c = occupants[0].i2c
    for occ in occupants:
        occ.adapter.seed(fake_bus, occ.address, iterations)
    hold_sda_through_a_stretched_clear(i2c, pulses=i2c_const("_CLEAR_PULSES") + 1, stretch_reads=5)
    marks: list[int] = []
    warmed = [0]

    async def reader_loop(occ: BusOccupant) -> None:
        for i in range(iterations):
            await occ.adapter.read_once(occ.instance)
            if i == 0:
                warmed[0] += 1
            await asyncio.sleep(0)

    async def recovery() -> None:
        while warmed[0] < len(occupants):
            await asyncio.sleep(0)
        for _ in range(offset):
            await asyncio.sleep(0)
        status, mark = await recover_marking_the_clear(i2c)
        assert status == i2c_const("_REC_SDA_LOW") | i2c_const("_REC_SDA_STUCK"), f"the recovery did not clear the planted held SDA: status {status}"
        marks.append(mark)

    await asyncio.gather(*(reader_loop(occ) for occ in occupants), recovery())
    assert_no_transfer_inside_the_recovery(fake_bus, marks[0])


async def _run_write_vs_siblings_at_offset(fake_bus: FakeI2C, occupants: "list[BusOccupant]", driver: str, iterations: int, offset: int) -> None:
    # The occupant running `driver` writes once, `offset` yields into every sibling's read loop.
    writer = next(occ for occ in occupants if occ.adapter.driver == driver)
    readers = [occ for occ in occupants if occ is not writer]
    for occ in readers:
        occ.adapter.seed(fake_bus, occ.address, iterations)

    async def reader_loop(occ: BusOccupant) -> None:
        for _ in range(iterations):
            await occ.adapter.read_once(occ.instance)
            await asyncio.sleep(0)

    async def writer_loop(occ: BusOccupant) -> None:
        assert occ.adapter.write_once is not None
        for _ in range(offset):  # let the readers get exactly `offset` yields into their own loop first
            await asyncio.sleep(0)
        await occ.adapter.write_once(occ.instance)

    await asyncio.gather(*(reader_loop(occ) for occ in readers), writer_loop(writer))


def _touched_addresses(fake_bus: FakeI2C) -> "set[int]":
    return {entry[1] for entry in fake_bus.log if entry[0] in _TRANSFER_OPS}


def is_reserved(address: int) -> bool:
    return any(lo <= address <= hi for lo, hi in RESERVED_I2C_RANGES)


def adapter_for(driver: str) -> I2CHazardAdapter:
    adapter = I2C_HAZARD_CATALOG.get(driver)
    if adapter is None:
        raise KeyError(f"no bus-hazard catalog adapter for driver {driver!r} - add one to tests/_bus_hazard_catalog.py's I2C_HAZARD_CATALOG before this driver can get generated cross-sensor coverage")
    return adapter


def assert_no_transfer_inside_the_recovery(fake_bus: FakeI2C, mark: int) -> None:
    # From the clear's start to the re-construction, the bus log holds only the recovery's own entries.
    assert not fake_bus.log.dropped, "the bus log dropped entries: the window cannot be checked"
    after = fake_bus.log[mark:]
    inits = [i for i, entry in enumerate(after) if entry[0] == "init"]
    assert inits, "the recovery never re-constructed the controller"
    assert after[: inits[0]] == [("deinit",)], f"a transfer landed inside the recovery window: {after[: inits[0]]}"


def build_bus_occupants(i2c: I2C, attachments: "list[I2CAttachment]") -> "list[BusOccupant]":
    # One BusOccupant per `attachments` entry (buildgen.twin_wiring.compute_twin_wiring()'s own
    # per-bus list shape) - fails loud, not silently, if a real occupant has no catalog adapter yet.
    occupants = []
    for attachment in attachments:
        adapter = adapter_for(attachment["driver"])
        address = attachment["address"]
        occupants.append(BusOccupant(adapter, adapter.construct(i2c, address), address, i2c))
    return occupants


def crc8(data: bytes) -> int:
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def fake(i2c: I2C) -> FakeI2C:
    return i2c._i2c  # type: ignore[return-value]


def hold_sda_through_a_stretched_clear(i2c: I2C, pulses: int = 2, stretch_reads: int = 1, host_stall_ms: int = 0) -> None:
    # A slave holding SDA for `pulses` SCL pulses on a clock it stretches for `stretch_reads` reads per
    # release: a clear then yields (1 ms each) under the bus lock, where a sibling would cut in unguarded.
    # `host_stall_ms` blocks the interpreter inside the first SCL read: a host deschedule at the worst instant.
    scl_pin, sda_pin = i2c._args[1], i2c._args[2]
    stretch = [-1, 0]
    stall = [host_stall_ms]

    def scl_level(_pin: int, _log: object) -> int:
        if stall[0]:
            time.sleep_ms(stall[0])
            stall[0] = 0
        log = Pin.value_log(scl_pin)
        drives = len(log) + log.dropped  # the value log is a ring: its len() stops at its capacity
        if drives != stretch[0]:
            stretch[0], stretch[1] = drives, 0
        stretch[1] += 1
        return 1 if stretch[1] > stretch_reads else 0

    def sda_level(_pin: int, _log: object) -> int:
        return 1 if list(Pin.value_log(scl_pin)).count(1) >= pulses else 0

    Pin.set_external_level(scl_pin, scl_level)
    Pin.set_external_level(sda_pin, sda_level)


def i2c_const(name: str) -> int:
    # A folded const() of asy_i2c_driver.py (its recovery status bits, its clear's pulse count), read from its source.
    return src_int("src/asy_i2c_driver.py", name)


def make_i2c(port_id: int = 1) -> I2C:
    # A fresh static bus on every call, a test building several included (the per-test reset clears the bus and pin
    # registries only between tests), its construction entry dropped so the log holds only the scenario's own traffic.
    FakeI2C.reset_id(port_id)
    Pin.reset_registry()
    i2c = I2C(port_id, scl_pin=19, sda_pin=18, frequency=50000)
    fake(i2c).log.clear()
    return i2c


async def recover_marking_the_clear(i2c: I2C) -> "tuple[int, int]":
    # i2c.recover() on the poll-round clock, returning its status and the bus-log length when its clear
    # began (the bus lock held).
    mark = []
    real_clear = i2c._clear_locked

    async def marked() -> int:
        mark.append(len(fake(i2c).log))
        return await real_clear()

    i2c._clear_locked = marked  # type: ignore[method-assign]
    try:
        with PollRoundClock():
            status = await i2c.recover()
    finally:
        i2c._clear_locked = real_clear  # type: ignore[method-assign]
    return status, mark[0]


def scd_data_frame(co2: float, temperature: float, humidity: float) -> bytes:
    frame = bytearray()
    for value in (co2, temperature, humidity):
        raw = struct.pack(">f", value)
        msw, lsw = raw[0:2], raw[2:4]
        frame += msw + bytes([crc8(msw)]) + lsw + bytes([crc8(lsw)])
    return bytes(frame)


def scd_register_frame(value: int) -> bytes:
    payload = struct.pack(">H", value)
    return payload + bytes([crc8(payload)])


async def scenario_a_write_does_not_disturb_concurrent_sibling_reads(
    build_fresh_bus_and_occupants: "Callable[[], tuple[FakeI2C, list[BusOccupant]]]",
    writer: "str | None" = None,
    iterations: int = 6,
    offsets: "list[int] | None" = None,
) -> None:
    # An occupant's own config write concurrent with every sibling's read loop - the N-way form of the pairwise
    # cross-device tests, for `writer` or else every writer on the bus. Swept across timing offsets on fresh state
    # per (writer, offset): SPECIFICATION.md Part C.8 says why.
    offsets = list(range(iterations)) if offsets is None else offsets
    _fake_bus, occupants = build_fresh_bus_and_occupants()
    writers = [occ.adapter.driver for occ in occupants if occ.adapter.write_once is not None]
    if not writers:
        raise microtest.Skip("no occupant of this bus has a safe write")
    if writer is not None:
        assert writer in writers, f"{writer!r} is no writer on this bus: {writers}"
        writers = [writer]
    failures: list[str] = []
    for driver in writers:
        for offset in offsets:
            fake_bus, occupants = build_fresh_bus_and_occupants()
            try:
                await _run_write_vs_siblings_at_offset(fake_bus, occupants, driver, iterations, offset)
            except AssertionError as e:
                failures.append(f"{driver} writing, offset={offset}: {e}")
    assert not failures, f"{len(failures)}/{len(writers) * len(offsets)} (writer, offset) run(s) reproduced a hazard: {failures}"


async def scenario_all_occupants_concurrent_reads_stay_correct(fake_bus: FakeI2C, occupants: "list[BusOccupant]", iterations: int = 6) -> None:
    # Every real occupant of one bus reads concurrently, not pairwise - the "all sharers at once" half of SPECIFICATION.md
    # Part C.8. Each read_once() asserts its own correctness; a sibling inside each bus-releasing occupant's window, or on
    # a bus with none the switch-count floor, rules out silent full serialization.
    for occ in occupants:
        occ.adapter.seed(fake_bus, occ.address, iterations)

    async def loop(occ: BusOccupant) -> None:
        for _ in range(iterations):
            await occ.adapter.read_once(occ.instance)
            await asyncio.sleep(0)

    await asyncio.gather(*(loop(occ) for occ in occupants))

    addressed = [entry[1] for entry in fake_bus.log if entry[0] in _TRANSFER_OPS]
    flagged = [occ for occ in occupants if occ.adapter.releases_bus_mid_read]
    for occ in flagged if len(occupants) > 1 else ():
        assert sibling_inside_window(fake_bus.log, occ.address), f"no sibling transaction landed inside a {occ.adapter.driver} conversion window - the bus was held across the delay: {addressed}"
    if not flagged:
        switches = sum(1 for i in range(len(addressed) - 1) if addressed[i] != addressed[i + 1])
        assert switches >= len(occupants), f"only {switches} address switch(es) across {len(occupants)} occupants - looks fully/mostly serialized, not genuinely interleaved: {addressed}"


async def scenario_bus_recovery_does_not_disturb_concurrent_siblings(
    build_fresh_bus_and_occupants: "Callable[[], tuple[FakeI2C, list[BusOccupant]]]",
    iterations: int = 6,
    offsets: "list[int] | None" = None,
) -> None:
    # The bus rungs' hazard (SPECIFICATION.md Part C.8): i2c.recover() - a clear and a controller
    # re-construction under one bus-lock hold - lands at each timing offset of every occupant's read
    # loop; every read stays valid and no transfer runs inside the recovery.
    offsets = list(range(iterations)) if offsets is None else offsets
    failures: list[str] = []
    for offset in offsets:
        fake_bus, occupants = build_fresh_bus_and_occupants()
        try:
            await _run_recovery_vs_siblings_at_offset(fake_bus, occupants, iterations, offset)
        except AssertionError as e:
            failures.append(f"offset={offset}: {e}")
    assert not failures, f"{len(failures)}/{len(offsets)} timing offset(s) reproduced a hazard: {failures}"


async def scenario_each_occupant_never_touches_an_unexpected_address(attachments: "list[I2CAttachment]", iterations: int = 6) -> None:
    # Each driver's address sweep, generic: every occupant, alone and seeded on a private fake bus, runs its public API,
    # write and general call, and touches exactly its own address (and 0x00 for a broadcaster), never a reserved one;
    # an exercise raising before its first transfer fails.
    for attachment in attachments:
        driver = attachment["driver"]
        adapter = adapter_for(driver)
        address = attachment["address"]
        assert not is_reserved(address), f"{driver!r}'s own real address {address:#x} falls inside a reserved I2C range"
        i2c = make_i2c()
        instance = adapter.construct(i2c, address)
        adapter.seed(fake(i2c), address, iterations)
        with FastAsyncSleep():  # the sweep proves addresses, so a driver's datasheet waits cost no real time here
            try:
                await adapter.exercise(instance)
            except adapter.exercise_raises:
                pass
            if adapter.write_once is not None:
                await adapter.write_once(instance)
            if adapter.general_call is not None:
                await adapter.general_call(instance)
        touched = _touched_addresses(fake(i2c))
        expected = {address, _GENERAL_CALL_ADDR} if adapter.general_call is not None else {address}
        assert touched == expected, f"{driver!r}'s own sweep touched {sorted(touched)}, expected exactly {sorted(expected)}"


async def scenario_general_call_does_not_disturb_concurrent_siblings(
    build_fresh_bus_and_occupants: "Callable[[], tuple[FakeI2C, list[BusOccupant]]]",
    iterations: int = 6,
    offsets: "list[int] | None" = None,
) -> None:
    # A real general-call broadcast, the general-call reset the owner decided (owner, 2026-09-26; SPECIFICATION.md Part C.8), concurrent
    # with every non-broadcasting sibling's read loop, across swept timing offsets.
    offsets = list(range(iterations)) if offsets is None else offsets
    _fake_bus, occupants = build_fresh_bus_and_occupants()
    if not any(occ.adapter.general_call is not None for occ in occupants):
        raise microtest.Skip("no occupant broadcasts a general call")
    failures: list[str] = []
    for offset in offsets:
        fake_bus, occupants = build_fresh_bus_and_occupants()
        try:
            await _run_general_call_vs_siblings_at_offset(fake_bus, occupants, iterations, offset)
        except AssertionError as e:
            failures.append(f"offset={offset}: {e}")
    assert not failures, f"{len(failures)}/{len(offsets)} timing offset(s) reproduced a hazard: {failures}"


async def scenario_same_occupant_own_write_does_not_disturb_own_concurrent_read(
    build_fresh_bus_and_occupants: "Callable[[], tuple[FakeI2C, list[BusOccupant]]]",
    iterations: int = 6,
    offsets: "list[int] | None" = None,
) -> None:
    # Same-DEVICE hazard: an occupant's own config write concurrent with its OWN read loop must
    # never tear it. Proven through read_once()'s corruption assertion, not a per-driver wire-byte
    # parser, so it stays generic. Offsets swept as above (SPECIFICATION.md Part C.8).
    offsets = list(range(iterations)) if offsets is None else offsets
    _fake_bus, occupants = build_fresh_bus_and_occupants()
    writers = [occ.adapter.driver for occ in occupants if occ.adapter.write_once is not None]
    for driver in writers:
        failures: list[str] = []
        for offset in offsets:
            fake_bus, occupants = build_fresh_bus_and_occupants()
            occ = next(o for o in occupants if o.adapter.driver == driver)
            try:
                await _run_own_write_vs_own_read_at_offset(fake_bus, occ, iterations, offset)
            except AssertionError as e:
                failures.append(f"offset={offset}: {e}")
        assert not failures, f"{driver!r}: {len(failures)}/{len(offsets)} timing offset(s) reproduced a same-device hazard: {failures}"


def seed_bmp_ready(i2c: I2C, address: int = 0x77, chip_id: int = 0x50) -> None:
    _ready_bmp(fake(i2c), address, chip_id)


def seed_isl_ready(i2c: I2C, address: int = 0x44) -> None:
    # 0x44 matches ISL29125_I2C's own hard-wired default address (FN8424 p15, no address-select pin).
    _ready_isl(fake(i2c), address)


def sgp_word(value: int) -> bytes:
    payload = bytes([(value >> 8) & 0xFF, value & 0xFF])
    return payload + bytes([crc8(payload)])


def sibling_inside_window(log: "Iterable[tuple[object, ...]]", owner_addr: int) -> bool:
    # True once another address's transfer lands between one owner write and the owner's next read: one released
    # window, not every one.
    opened = sibling = False
    for entry in log:
        if entry[0] not in _TRANSFER_OPS:
            continue
        if entry[1] != owner_addr:
            sibling = sibling or opened
            continue
        if entry[0] == "readfrom_into" and opened and sibling:
            return True
        opened, sibling = entry[0] == "writeto", False
    return False


def spi_adapter_for(driver: str) -> object:
    adapter = SPI_HAZARD_CATALOG.get(driver)
    if adapter is None:
        raise KeyError(f"no bus-hazard catalog adapter for SPI driver {driver!r} - add one to tests/_bus_hazard_catalog.py's SPI_HAZARD_CATALOG before this driver can share an SPI bus")
    return adapter


class PollRoundClock:
    # asy_i2c_driver's clock while a planted slave stretches: advanced by each of its sleeps, and 1 us per read so a
    # wait that never yields still expires. The slave stretches for a count of reads, so on the wall clock a host
    # stall alone would expire the SCL-release bound and read as a held clock.
    def __enter__(self) -> "PollRoundClock":
        real_time, real_asyncio = asy_i2c_driver.time, asy_i2c_driver.asyncio
        self._saved = (real_time, real_asyncio)
        now = [0]

        class _Time:
            ticks_diff = staticmethod(real_time.ticks_diff)
            sleep_us = staticmethod(real_time.sleep_us)

            @staticmethod
            def ticks_us() -> int:
                now[0] += 1
                return now[0]

        class _Asyncio:
            Lock = real_asyncio.Lock
            sleep = staticmethod(real_asyncio.sleep)

            @staticmethod
            async def sleep_ms(ms: int) -> None:
                now[0] += ms * 1000
                await real_asyncio.sleep_ms(ms)

        asy_i2c_driver.time = _Time()  # type: ignore[assignment]
        asy_i2c_driver.asyncio = _Asyncio()  # type: ignore[assignment]
        return self

    def __exit__(self, *exc_info: object) -> None:
        asy_i2c_driver.time, asy_i2c_driver.asyncio = self._saved
