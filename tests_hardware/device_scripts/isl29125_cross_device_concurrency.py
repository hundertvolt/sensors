"""Isolated-driver device script: the ISL29125 interleaves with the two devices sharing its I2C bus rather than
serialising behind either - the standing cross-device requirement, real-hardware tier. Counts ISL29125 reads that
complete inside an SGP40 device-session window; reports facts, the host gives the verdict."""

import asyncio

import asy_i2c_driver
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
    from _shared.bus_reader_loops import Record, Stop, interleaved, isl29125_counts_problem, read_loop, report_errors
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# @tunable l3.isl29125_cross_device_concurrency_sgp40_cycles = 6
_SGP40_CYCLES = 6
# @tunable l3.isl29125_cross_device_concurrency_sibling_step_ms = 20
_SIBLING_STEP_MS = 20
# @tunable l3.isl29125_cross_device_concurrency_run_bound_s = 60.0
_RUN_BOUND_S = 60.0


async def _main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["isl29125"]["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    isl = ISL29125_I2C(i2c)
    scd = SCD30_I2C(i2c)
    sgp = SGP40_I2C(i2c)
    await isl.setup()
    await isl.configure(mode=BENCH["isl29125"]["mode_rgb"], range_fs=10000, resolution=16, threshold_interrupt=False)
    # The SCD30 measurement prerequisite is the session's `scd30_measuring` fixture; this script writes no NVM.
    await scd.setup()
    await sgp.setup()

    async def scd_read() -> "str | None":
        await scd.read_measurement()
        return None

    async def sgp_cycle() -> "str | None":
        await sgp.initialize()
        return None

    isl_rec, scd_rec, sgp_rec = Record("isl29125", windows=True), Record("scd30"), Record("sgp40", windows=True)
    stop = Stop()

    async def sgp_phase() -> None:
        await read_loop(sgp_cycle, _SGP40_CYCLES, 0, wdt, sgp_rec, Stop())
        stop.is_set = True

    loops = (read_loop(lambda: isl29125_counts_problem(isl), None, _SIBLING_STEP_MS, wdt, isl_rec, stop), read_loop(scd_read, None, _SIBLING_STEP_MS, wdt, scd_rec, stop), sgp_phase())
    await asyncio.wait_for(asyncio.gather(*loops), _RUN_BOUND_S)
    total, holding = interleaved(isl_rec, sgp_rec)
    fact("isl_reads", isl_rec.reads)
    fact("scd_reads", scd_rec.reads)
    fact("sgp_cycles", sgp_rec.reads)
    fact("sgp_cycles_planned", _SGP40_CYCLES)
    fact("interleaved", total)
    fact("windows_with_interleaving", holding)
    report_errors([isl_rec, scd_rec, sgp_rec])
    done()


asyncio.run(_main())
