"""Isolated-driver device script: the SCD30 device-session lock serialises two concurrent multi-transaction sequences
against the same device (real-hardware counterpart to SPECIFICATION.md Part C.8). Both paths are CRC-8 protected, so
interleaving corruption trips a CRC or NAK rather than succeeding silently. Reports facts; the host gives the verdict.
"""

import asyncio

import asy_i2c_driver
from asy_scd30_driver import SCD30_I2C

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/bus_reader_loops.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.bus_reader_loops import Record, Stop, read_loop, report_errors, scd30_reading_problem
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# @tunable l3.bus_concurrency_same_device_scd30_reader_iterations = 120
_READER_ITERATIONS = 120
# @tunable l3.bus_concurrency_same_device_scd30_snapshotter_iterations = 40
_SNAPSHOTTER_ITERATIONS = 40
# setup()'s soft reset leaves the measurement interval running, so data-ready rises on the first unsettled conversion;
# scd30_same_device_rw_concurrency.py consumes it the same way.
# @tunable l3.scd30_same_device_rw_concurrency_settle_s = 12.0
_SETTLE_S = 12.0
# @tunable l3.scd30_same_device_rw_concurrency_settle_step_s = 0.5
_SETTLE_STEP_S = 0.5
# @tunable l3.bus_concurrency_same_device_scd30_run_bound_s = 90.0
_RUN_BOUND_S = 90.0


async def _main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["scd30"]["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    scd = SCD30_I2C(i2c)
    # The SCD30 measurement prerequisite is the session's `scd30_measuring` fixture; this script writes nothing.
    await scd.setup()

    async def consume() -> "str | None":
        await scd.read_measurement()
        return None

    settle = Record("scd30_settle")
    await read_loop(consume, int(_SETTLE_S / _SETTLE_STEP_S), int(_SETTLE_STEP_S * 1000), wdt, settle, Stop())
    fact("settle_failures", settle.total)

    def off_schema(field: str, value: int) -> "str | None":
        _kind, _default, low, high, _special = BENCH["scd30_schema"][field]
        return None if isinstance(low, int) and isinstance(high, int) and low <= value <= high else f"{field}={value} outside its schema range [{low}, {high}]"

    async def read() -> "str | None":
        return await scd30_reading_problem(scd, BENCH["bounds"])

    async def snapshot() -> "str | None":
        _offset, interval, _ambient, _altitude, frc, _self_cal = await scd.get_config_snapshot()
        return off_schema("MeasInterval", interval) or off_schema("ForceCalRef", frc)

    reader_rec, snapshot_rec = Record("scd30_reader"), Record("scd30_snapshotter")
    await asyncio.wait_for(asyncio.gather(read_loop(read, _READER_ITERATIONS, 0, wdt, reader_rec, Stop()), read_loop(snapshot, _SNAPSHOTTER_ITERATIONS, 0, wdt, snapshot_rec, Stop())), _RUN_BOUND_S)
    fact("reader_completed", reader_rec.reads + reader_rec.total)
    fact("reader_planned", _READER_ITERATIONS)
    fact("snapshot_completed", snapshot_rec.reads + snapshot_rec.total)
    fact("snapshot_planned", _SNAPSHOTTER_ITERATIONS)
    report_errors([reader_rec, snapshot_rec])
    done()


asyncio.run(_main())
