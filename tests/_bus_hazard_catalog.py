"""Generic, TOML-bus-membership-driven cross-sensor hazard scenarios plus the small per-I2C-driver
adapter catalog they run against (BUS_HAZARD_TEST_GENERATION_REQUIREMENTS.md). Shared wire-frame
helpers moved here from test_bus_hazard_multi_device.py so both files build identical bytes."""

import asyncio
import struct

from machine import I2C as FakeI2C

from asy_i2c_driver import I2C
from asy_isl29125_driver import ISL29125_I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any

_GENERAL_CALL_ADDR = 0x00

# ---------------------------------------------------------------------------
# Shared wire-frame construction helpers (moved from test_bus_hazard_multi_device.py - both files
# need byte-identical frames, so this is the one place that builds them).
# ---------------------------------------------------------------------------


def make_i2c(port_id: int = 1) -> I2C:
    return I2C(port_id, scl_pin=19, sda_pin=18, frequency=50000)


def fake(i2c: I2C) -> FakeI2C:
    return i2c._i2c  # type: ignore[return-value]


def crc8(data: bytes) -> int:
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def sgp_word(value: int) -> bytes:
    payload = bytes([(value >> 8) & 0xFF, value & 0xFF])
    return payload + bytes([crc8(payload)])


def scd_register_frame(value: int) -> bytes:
    payload = struct.pack(">H", value)
    return payload + bytes([crc8(payload)])


def scd_data_frame(co2: float, temperature: float, humidity: float) -> bytes:
    frame = bytearray()
    for value in (co2, temperature, humidity):
        raw = struct.pack(">f", value)
        msw, lsw = raw[0:2], raw[2:4]
        frame += msw + bytes([crc8(msw)]) + lsw + bytes([crc8(lsw)])
    return bytes(frame)


def seed_isl_ready(i2c: I2C, address: int = 0x44) -> None:
    # 0x44 matches ISL29125_I2C's own hard-wired default address (FN8424 p15, no address-select pin).
    fake(i2c).registers[(address, 0x00)] = bytearray([0x7D])  # device ID (p9, Table 2)
    fake(i2c).registers[(address, 0x01)] = bytearray([0x00, 0x00, 0x00])  # CONFIG1-3, post-reset
    fake(i2c).registers[(address, 0x08)] = bytearray([0x00])  # status, BOUTF already clear
    fake(i2c).registers[(address, 0x09)] = bytearray(struct.pack("<HHH", 0x2000, 0x1800, 0x1000))


# Known-good values the seed helpers above feed back through a clean read - every _read_once_*
# below asserts against these, so a concurrent-write hazard that tears a read is actually caught.
_SCD_CO2 = 412.5
_SCD_TEMPERATURE = 23.4
_SCD_HUMIDITY = 45.6
_SGP_RAW = 0x8000
_ISL_COUNTS = (0x2000, 0x1800, 0x1000)


# ---------------------------------------------------------------------------
# Per-driver adapter: enough to construct/seed/drive one instance generically, without any of this
# module knowing which concrete driver it is. Only covers drivers that actually share a bus with
# another driver on some real device today (BUS_HAZARD_TEST_GENERATION_REQUIREMENTS.md's own
# dev/i2c1 scoping) - bmp3xx never does, so it isn't in I2C_HAZARD_CATALOG yet; add it the same way
# the moment a device wires it alongside another I2C driver.
# ---------------------------------------------------------------------------


class I2CHazardAdapter:
    # A plain class, not @dataclass - `dataclasses` has no stub in the MicroPython-target typeshed
    # this file type-checks under (custom_typeshed_dir) and no real driver/test module anywhere in
    # src/tests/digital_twin imports it either; buildgen (genuinely CPython-only) is the only place
    # dataclasses is used in this repo, confirmed by grep before adding a second, incompatible one.
    def __init__(
        self,
        driver: str,
        construct: "Callable[[I2C, int], Any]",  # (shared fake bus, this occupant's own address) -> driver instance
        seed: "Callable[[FakeI2C, int, int], None]",  # (fake bus, this occupant's own address, iteration count) -> queues/registers enough for that many clean reads
        read_once: "Callable[[Any], Coroutine[Any, Any, None]]",  # one correctness-checked read cycle; raises on corruption
        exercise: "Callable[[Any], Coroutine[Any, Any, None]]",  # sweeps this driver's own public API, for the address-sweep scenario
        write_once: "Callable[[Any], Coroutine[Any, Any, None]] | None" = None,  # one safe, non-destructive config write, if this driver has one
        general_call: "Callable[[Any], Coroutine[Any, Any, None]] | None" = None,  # a real I2C general-call broadcast this driver issues on its own, if any
    ) -> None:
        self.driver = driver
        self.construct = construct
        self.seed = seed
        self.read_once = read_once
        self.exercise = exercise
        self.write_once = write_once
        self.general_call = general_call


def _seed_scd30(fake_bus: FakeI2C, address: int, iterations: int) -> None:
    # Keyed by address, not the shared fake_bus.read_queue: SCD30 speaks the same register-less,
    # write-then-read protocol shape SGP40 does, so when both share a bus (dev's real i2c1) their
    # replies must not be pulled from one shared, address-agnostic FIFO (tests/machine.py's
    # read_queue_by_address, added for exactly this - see its own comment).
    queue = fake_bus.read_queue_by_address.setdefault(address, [])
    for _ in range(iterations):
        queue.append(scd_register_frame(1))
        queue.append(scd_data_frame(_SCD_CO2, _SCD_TEMPERATURE, _SCD_HUMIDITY))


async def _read_once_scd30(instance: "Any") -> None:
    await instance.read_measurement()
    co2 = await instance.get_CO2()
    assert co2 is not None and abs(co2 - _SCD_CO2) < 1e-6, f"a concurrent hazard corrupted SCD30's own read: {co2!r}, expected {_SCD_CO2!r}"


async def _write_once_scd30(instance: "Any") -> None:
    await instance.set_temperature_offset(12.34)


async def _exercise_scd30(instance: "Any") -> None:
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
        except Exception:  # only the addresses touched matter for this sweep, not success
            pass


def _seed_sgp40(fake_bus: FakeI2C, address: int, iterations: int) -> None:
    # Keyed by address - see _seed_scd30's own comment for why (the two share a bus on dev).
    queue = fake_bus.read_queue_by_address.setdefault(address, [])
    for _ in range(iterations):
        queue.append(sgp_word(_SGP_RAW))


async def _read_once_sgp40(instance: "Any") -> None:
    raw = await instance.measure_raw(temperature=25, relative_humidity=50)
    assert raw == _SGP_RAW, f"a concurrent hazard corrupted SGP40's own read: {raw!r}, expected {_SGP_RAW!r}"


async def _general_call_sgp40(instance: "Any") -> None:
    await instance._reset()


async def _exercise_sgp40(instance: "Any") -> None:
    for call in (
        instance.setup,  # includes one initialize() -> _reset() call, hence GENERAL_CALL_ADDR being allowed below
        instance.get_raw,
        lambda: instance.measure_raw(25, 50),
        lambda: instance.measure_index_and_raw(25, 50),
    ):
        try:
            await call()
        except Exception:  # see _exercise_scd30's own comment
            pass


def _seed_isl29125(fake_bus: FakeI2C, address: int, iterations: int) -> None:
    # Register-addressed, not queue-based (see seed_isl_ready()) - a fixed register snapshot stays
    # valid across any number of reads, so this adapter's own seed is a deliberate no-op; the real
    # seeding happens once, at construction time, via seed_isl_ready() below.
    del fake_bus, address, iterations


async def _read_once_isl29125(instance: "Any") -> None:
    counts = await instance.read_counts()
    assert counts == _ISL_COUNTS, f"a concurrent hazard corrupted ISL29125's own read: {counts!r}, expected {_ISL_COUNTS!r}"


async def _write_once_isl29125(instance: "Any") -> None:
    await instance.configure(ir_adjust=20)


async def _exercise_isl29125(instance: "Any") -> None:
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
        except Exception:  # see _exercise_scd30's own comment
            pass


def _construct_scd30(i2c: I2C, address: int) -> SCD30_I2C:
    return SCD30_I2C(i2c, address=address)


def _construct_sgp40(i2c: I2C, address: int) -> SGP40_I2C:
    return SGP40_I2C(i2c, address=address)


def _construct_isl29125(i2c: I2C, address: int) -> ISL29125_I2C:
    isl = ISL29125_I2C(i2c, address=address)
    seed_isl_ready(i2c, address)
    return isl


I2C_HAZARD_CATALOG: "dict[str, I2CHazardAdapter]" = {
    "scd30": I2CHazardAdapter("scd30", _construct_scd30, _seed_scd30, _read_once_scd30, _exercise_scd30, write_once=_write_once_scd30),
    "sgp40": I2CHazardAdapter("sgp40", _construct_sgp40, _seed_sgp40, _read_once_sgp40, _exercise_sgp40, general_call=_general_call_sgp40),
    "isl29125": I2CHazardAdapter("isl29125", _construct_isl29125, _seed_isl29125, _read_once_isl29125, _exercise_isl29125, write_once=_write_once_isl29125),
}


# ---------------------------------------------------------------------------
# One real bus occupant (an adapter bound to one constructed instance at one real address), and the
# generic cross-sensor scenarios that drive a whole bus's worth of them at once.
# ---------------------------------------------------------------------------


class BusOccupant:
    # Plain class, same reasoning as I2CHazardAdapter above.
    def __init__(self, adapter: I2CHazardAdapter, instance: "Any", address: int) -> None:
        self.adapter = adapter
        self.instance = instance
        self.address = address


def build_bus_occupants(i2c: I2C, attachments: "list[dict[str, Any]]") -> "list[BusOccupant]":
    """One BusOccupant per `attachments` entry (buildgen.twin_wiring.compute_twin_wiring()'s own
    per-bus list shape) - fails loud, not silently, if a real occupant has no catalog adapter yet."""
    occupants = []
    for attachment in attachments:
        driver = attachment["driver"]
        adapter = I2C_HAZARD_CATALOG.get(driver)
        if adapter is None:
            raise KeyError(f"no bus-hazard catalog adapter for driver {driver!r} - add one to tests/_bus_hazard_catalog.py's I2C_HAZARD_CATALOG before this driver can get generated cross-sensor coverage")
        address = attachment["address"]
        occupants.append(BusOccupant(adapter, adapter.construct(i2c, address), address))
    return occupants


def _touched_addresses(fake_bus: FakeI2C) -> "set[int]":
    return {entry[1] for entry in fake_bus.log if entry[0] in ("writeto", "readfrom_into", "readfrom_mem", "writeto_mem")}


async def scenario_all_occupants_concurrent_reads_stay_correct(fake_bus: FakeI2C, occupants: "list[BusOccupant]", iterations: int = 6) -> None:
    """Every real occupant of one bus reads concurrently, not pairwise - the "all sharers at once"
    half of BUS_HAZARD_TEST_GENERATION_REQUIREMENTS.md Section 0. Each read_once() already asserts
    its own correctness; the switch-count floor below additionally rules out silent full
    serialization (same `>= occupant count` bar test_bus_hazard_multi_device.py's own pairwise
    tests already use, generalized from their hardcoded 2)."""
    for occ in occupants:
        occ.adapter.seed(fake_bus, occ.address, iterations)

    async def loop(occ: BusOccupant) -> None:
        for _ in range(iterations):
            await occ.adapter.read_once(occ.instance)
            await asyncio.sleep(0)

    await asyncio.gather(*(loop(occ) for occ in occupants))

    addressed = [entry[1] for entry in fake_bus.log if entry[0] in ("writeto", "readfrom_into", "readfrom_mem", "writeto_mem")]
    switches = sum(1 for i in range(len(addressed) - 1) if addressed[i] != addressed[i + 1])
    assert switches >= len(occupants), f"only {switches} address switch(es) across {len(occupants)} occupants - looks fully/mostly serialized, not genuinely interleaved: {addressed}"


async def scenario_a_write_does_not_disturb_concurrent_sibling_reads(fake_bus: FakeI2C, occupants: "list[BusOccupant]", iterations: int = 6) -> None:
    """One occupant's own config write lands concurrently with every sibling's own read loop - the
    N-way generalization of the existing cross-device pairwise "both stay correct" tests. A no-op
    (not a skip) if nothing on this bus has a safe write to exercise."""
    writers = [occ for occ in occupants if occ.adapter.write_once is not None]
    if not writers:
        return
    writer = writers[0]
    readers = [occ for occ in occupants if occ is not writer]
    for occ in readers:
        occ.adapter.seed(fake_bus, occ.address, iterations)

    async def reader_loop(occ: BusOccupant) -> None:
        for _ in range(iterations):
            await occ.adapter.read_once(occ.instance)
            await asyncio.sleep(0)

    async def writer_loop(occ: BusOccupant) -> None:
        assert occ.adapter.write_once is not None
        await asyncio.sleep(0)  # let the readers get partway into their first cycle first
        await occ.adapter.write_once(occ.instance)

    await asyncio.gather(*(reader_loop(occ) for occ in readers), writer_loop(writer))


async def scenario_general_call_does_not_disturb_concurrent_siblings(fake_bus: FakeI2C, occupants: "list[BusOccupant]", iterations: int = 6) -> None:
    """A real general-call broadcast (SPECIFICATION.md Part C.8's known structural gap) fired
    concurrently with every non-broadcasting sibling's own read loop. A no-op if no real occupant
    of this bus ever issues one."""
    broadcasters = [occ for occ in occupants if occ.adapter.general_call is not None]
    if not broadcasters:
        return
    others = [occ for occ in occupants if occ.adapter.general_call is None]
    for occ in others:
        occ.adapter.seed(fake_bus, occ.address, iterations)

    async def sibling_loop(occ: BusOccupant) -> None:
        for _ in range(iterations):
            await occ.adapter.read_once(occ.instance)
            await asyncio.sleep(0)

    async def broadcast_loop(occ: BusOccupant) -> None:
        assert occ.adapter.general_call is not None
        await asyncio.sleep(0)
        await occ.adapter.general_call(occ.instance)

    await asyncio.gather(*(sibling_loop(occ) for occ in others), *(broadcast_loop(occ) for occ in broadcasters))

    assert any(entry[0] == "writeto" and entry[1] == _GENERAL_CALL_ADDR for entry in fake_bus.log), "the general call never fired - this scenario isn't exercising the hazard"


async def scenario_each_occupant_never_touches_an_unexpected_address(attachments: "list[dict[str, Any]]") -> None:
    """Automatic inclusion of Section 0's "sensor-specific" address sweep: every real occupant of a
    bus, freshly constructed alone on its own private fake bus (this check is inherently per-driver,
    not a joint one - see BUS_HAZARD_TEST_GENERATION_REQUIREMENTS.md Section 3's own catalog note),
    must never touch any address but its own, except a documented general call."""
    for attachment in attachments:
        driver = attachment["driver"]
        adapter = I2C_HAZARD_CATALOG.get(driver)
        if adapter is None:
            raise KeyError(f"no bus-hazard catalog adapter for driver {driver!r} - add one to tests/_bus_hazard_catalog.py's I2C_HAZARD_CATALOG before this driver can get generated cross-sensor coverage")
        address = attachment["address"]
        i2c = make_i2c()
        instance = adapter.construct(i2c, address)
        try:
            await adapter.exercise(instance)
        except Exception:  # only the addresses touched matter for this sweep, not success
            pass
        touched = _touched_addresses(fake(i2c))
        allowed = {address, _GENERAL_CALL_ADDR} if adapter.general_call is not None else {address}
        assert touched <= allowed, f"{driver!r} touched unexpected address(es) during its own sweep: {touched - allowed}"
