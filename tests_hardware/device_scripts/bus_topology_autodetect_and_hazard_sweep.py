"""Isolated-driver device script: scans every I2C bus the bench TOML declares, sweeps the known and the reserved
addresses, runs the self-hazard broadcast-vs-read check for a lone known device, then the controller rung (recover())
among every discovered device's reads and the SGP40 heater-off before a sibling read. Reports facts only."""

import asyncio
import errno

import asy_i2c_driver
from asy_bmp3xx_driver import BMP3XX_I2C
from asy_isl29125_driver import ISL29125_I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/bus_reader_loops.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import machine
    from _shared.bus_reader_loops import Drivers, Seen, device_reader
    from _shared.facts import _ERRORS_KEPT, done, errors, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

    Reader = Callable[[], Awaitable[str | None]]

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_GENERAL_CALL_ADDRESS = 0x00  # I2C-bus specification 3.1.13: the general call
_RESERVED_RANGES = ((0x00, 0x07), (0x78, 0x7F))  # I2C-bus specification Table 4: reserved addresses
_OTHER_RESERVED = [a for lo, hi in _RESERVED_RANGES for a in range(lo, hi + 1) if a != _GENERAL_CALL_ADDRESS]
# @tunable l3.bus_topology_autodetect_and_hazard_sweep_broadcast_step_s = 0.2
_BROADCAST_STEP_S = 0.2
# @tunable l3.bus_topology_autodetect_and_hazard_sweep_run_bound_s = 30.0
_RUN_BOUND_S = 30.0
# @tunable l3.bus_topology_autodetect_and_hazard_sweep_self_reads = 8
_SELF_READS = 8
# @tunable l3.bus_topology_autodetect_and_hazard_sweep_broadcasts = 3
_BROADCASTS = 3


class _Sweep(Seen):
    # What the sweep saw beside the device reads' own findings: unexpected exceptions (bounded) and the EIOs among
    # the drivers' transfers.
    def __init__(self) -> None:
        super().__init__()
        self.total = 0
        self.first: list[str] = []
        self.write_eio = 0

    def caught(self, where: str, e: Exception) -> str:
        if isinstance(e, OSError) and e.errno == errno.EIO:
            self.write_eio += 1
        return f"{where}: {type(e).__name__}: {e}"

    def fail(self, message: str) -> None:
        self.total += 1
        if len(self.first) < _ERRORS_KEPT:
            self.first.append(message)


def _probe(i2c: "asy_i2c_driver.I2C", address: int) -> "str | bool":
    # The zero-length write I2CDevice._probe_for_device() uses, soft I2C on rp2: True on an ACK, False on the address NAK
    # (ENODEV, machine_i2c.c:127-145, extmod/machine_i2c.c:199-203), else what happened: a timeout is a bus fault.
    try:
        i2c.writeto(address, b"")
    except OSError as e:
        if e.errno == errno.ENODEV:
            return False
        return f"a bus fault, not a NAK: {type(e).__name__}: {e}"
    except Exception as e:  # anything but the bus's own error is a finding
        return f"{type(e).__name__}: {e}"
    return True


async def _read_checked(name: str, read: "Reader", sweep: _Sweep) -> bool:
    try:
        problem = await read()
    except Exception as e:  # recorded; the host gives the verdict
        sweep.fail(sweep.caught(name, e))
        return False
    if problem is not None:
        sweep.fail(f"{name}: {problem}")
    return problem is None


async def _recover_among_reads(i2c: "asy_i2c_driver.I2C", readers: "dict[str, Reader]", sweep: _Sweep) -> "tuple[int, int]":
    # The controller rung on a healthy bus, issued while every discovered device reads: (its status, sibling failures).
    before = sweep.total
    status = [0]

    async def rung() -> None:
        await asyncio.sleep(0)
        status[0] = await i2c.recover()

    await asyncio.wait_for(asyncio.gather(rung(), *(_read_checked(f"{label} beside recover()", read, sweep) for label, read in readers.items())), _RUN_BOUND_S)
    return status[0], sweep.total - before


async def _self_hazard(i2c: "asy_i2c_driver.I2C", label: str, read: "Reader", sweep: _Sweep) -> "dict[str, object]":
    # A lone known device read repeatedly while general-call broadcasts race the reads: the clean reads and the
    # broadcasts that reached the bus, the NAKed among them.
    clean = [0]
    sent = {"broadcasts": 0, "naks": 0}

    async def reads() -> None:
        for i in range(_SELF_READS):
            clean[0] += 1 if await _read_checked(f"{label} self-hazard read {i}", read, sweep) else 0
            await asyncio.sleep(0)

    async def broadcasts() -> None:
        for _ in range(_BROADCASTS):
            try:
                i2c.writeto(_GENERAL_CALL_ADDRESS, b"\x06")
            except OSError as e:  # rp2: EIO for a transfer the bus aborted (a NAK), ETIMEDOUT otherwise (machine_i2c.c:150-155)
                if e.errno != errno.EIO:
                    sweep.fail(sweep.caught(f"{label} self-hazard broadcast", e))
                    await asyncio.sleep(_BROADCAST_STEP_S)
                    continue
                sent["naks"] += 1  # on the wire, taken by no device: the lone device ignores the general call
            sent["broadcasts"] += 1
            await asyncio.sleep(_BROADCAST_STEP_S)

    await asyncio.wait_for(asyncio.gather(reads(), broadcasts()), _RUN_BOUND_S)
    return {"device": label, "clean_reads": clean[0], "planned": _SELF_READS, "broadcasts": sent["broadcasts"], "naks": sent["naks"], "broadcasts_planned": _BROADCASTS}


async def _sweep_bus(bus_id: str, sweep: _Sweep, wdt: "machine.WDT", found: "dict[str, dict[str, object]]") -> None:
    # One bus: scan, the known and reserved address sweep, the self-hazard check, the recover() rung, the heater-off.
    bus = BENCH["bus"][bus_id]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    known = {address: label for label, address in BENCH["addresses"].items()}
    scan = i2c.scan() or []
    reserved_hits = []
    for address in sorted(known) + _OTHER_RESERVED:
        outcome = _probe(i2c, address)
        if isinstance(outcome, str):
            sweep.fail(f"{bus_id}: probing {address:#04x} misbehaved: {outcome}")
        elif outcome and address in _OTHER_RESERVED:
            reserved_hits.append(address)
    found["addresses"][bus_id] = scan
    found["unknown_addresses"][bus_id] = [a for a in scan if a not in known]
    found["reserved_hits"][bus_id] = reserved_hits
    wdt.feed()
    readers: dict[str, Reader] = {}
    drivers = Drivers(SCD30_I2C, BMP3XX_I2C, SGP40_I2C, ISL29125_I2C)
    for address in [a for a in scan if a in known]:
        try:
            read = await device_reader(BENCH, known[address], i2c, sweep, drivers)
        except Exception as e:  # a setup() that fails is the sweep's finding, not the script's end
            sweep.fail(sweep.caught(f"{known[address]} setup()", e))
            read = None
        if read is not None:
            readers[known[address]] = read
        await asyncio.sleep(0)
    if len(readers) == 1:
        label, read = next(iter(readers.items()))
        found["self_hazard"][bus_id] = await _self_hazard(i2c, label, read, sweep)
    wdt.feed()
    if readers:
        status, sibling_errors = await _recover_among_reads(i2c, readers, sweep)
        found["recover_status"][bus_id] = status
        found["recover_sibling_errors"][bus_id] = sibling_errors
    sgp_label = next((label for label in readers if BENCH["instances"][label]["driver"] == "sgp40"), None)
    siblings = [label for label in readers if label != sgp_label]
    if sgp_label is not None and siblings:
        # The SGP40 heater-off (datasheet Table 14), then one read of a sibling on the same bus.
        await SGP40_I2C(i2c).turn_heater_off()
        found["heater_off_ok"][bus_id] = await _read_checked(f"{siblings[0]} after the SGP40 heater-off", readers[siblings[0]], sweep)
    wdt.feed()


async def _main() -> None:
    wdt = arm()
    sweep = _Sweep()
    keys = ("addresses", "unknown_addresses", "reserved_hits", "self_hazard", "recover_status", "recover_sibling_errors", "heater_off_ok")
    found: dict[str, dict[str, object]] = {key: {} for key in keys}
    for bus_id in sorted(b for b in BENCH["bus"] if b.startswith("i2c")):
        await _sweep_bus(bus_id, sweep, wdt, found)
    for key in keys:
        fact(key, found[key])
    fact("write_eio", sweep.write_eio)
    fact("por_after_setup", sweep.por_after_setup)
    fact("isl_divergences", sweep.isl_divergences)
    errors("errors", sweep.total, sweep.first)
    done()


asyncio.run(_main())
