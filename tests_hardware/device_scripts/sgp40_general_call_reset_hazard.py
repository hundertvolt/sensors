"""Isolated-driver device script: real-hardware regression test for the SGP40 general-call reset hazard
(SPECIFICATION.md Part C.8) - concurrent SCD30 and ISL29125 reads against repeated SGP40 initialize() cycles, each
ending in the general-call broadcast. Reports what it saw; the host checks no corruption and advancing CO2."""

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
    from _shared.bus_reader_loops import Record, Stop, isl29125_counts_problem, read_loop, report_errors, scd30_reading_problem
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# @tunable l3.sgp40_general_call_reset_hazard_reset_cycles = 8
_SGP40_RESET_CYCLES = 8
# @tunable l3.sgp40_general_call_reset_hazard_sibling_step_ms = 15
_SIBLING_STEP_MS = 15
# @tunable l3.sgp40_general_call_reset_hazard_run_bound_s = 90.0
_RUN_BOUND_S = 90.0


async def _main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["sgp40"]["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    scd = SCD30_I2C(i2c)
    sgp = SGP40_I2C(i2c)
    isl = ISL29125_I2C(i2c)
    # The SCD30 measurement prerequisite is the session's `scd30_measuring` fixture; this script writes no NVM.
    await scd.setup()
    await sgp.setup()
    await isl.setup()
    await isl.configure(mode=BENCH["isl29125"]["mode_rgb"], range_fs=10000, resolution=16, threshold_interrupt=False)
    distinct_co2: set[float] = set()

    async def scd_read() -> "str | None":
        problem = await scd30_reading_problem(scd, BENCH["bounds"])
        co2 = await scd.get_CO2()
        if co2 is not None:
            distinct_co2.add(co2)
        return problem

    async def sgp_cycle() -> "str | None":
        await sgp.initialize()  # the production path: it ends with _reset()'s general-call broadcast
        return None

    scd_rec, isl_rec, sgp_rec = Record("scd30"), Record("isl29125"), Record("sgp40")
    stop = Stop()

    async def sgp_phase() -> None:
        await read_loop(sgp_cycle, _SGP40_RESET_CYCLES, 0, wdt, sgp_rec, Stop())
        stop.is_set = True

    await asyncio.wait_for(asyncio.gather(read_loop(scd_read, None, 0, wdt, scd_rec, stop), read_loop(lambda: isl29125_counts_problem(isl), None, _SIBLING_STEP_MS, wdt, isl_rec, stop), sgp_phase()), _RUN_BOUND_S)
    fact("sgp_completed", sgp_rec.reads)
    fact("sgp_cycles_planned", _SGP40_RESET_CYCLES)
    fact("scd_completed", scd_rec.reads)
    fact("isl_completed", isl_rec.reads)
    fact("distinct_co2_count", len(distinct_co2))
    report_errors([scd_rec, isl_rec, sgp_rec])
    done()


asyncio.run(_main())
