"""Isolated-driver device script: SCD30 and SGP40 on one I2C bus interleave rather than serialise (SPECIFICATION.md
Part C.8's per-transaction bus lock), then two participant rungs mid-traffic: an SCD30 soft reset among the SGP40 and
ISL29125 reads, and the SGP40 heater-off among the SCD30 and ISL29125 reads. Reports facts; the host gives the verdict.
"""

import asyncio
import time

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
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# @tunable l3.bus_concurrency_cross_device_scd30_sgp40_sgp40_cycles = 6
_SGP40_CYCLES = 6
# @tunable l3.bus_concurrency_cross_device_scd30_sgp40_run_bound_s = 60.0
_RUN_BOUND_S = 60.0
# @tunable l3.bus_concurrency_cross_device_resume_s = 2.5
_SCD30_RESUME_S = 2.5
# @tunable l3.bus_concurrency_cross_device_sibling_step_ms = 15
_SIBLING_STEP_MS = 15
# @tunable l3.bus_concurrency_cross_device_rung_traffic_ms = 1000
_RUNG_TRAFFIC_MS = 1000


def _bus() -> asy_i2c_driver.I2C:
    chip = BENCH["instances"]["scd30"]
    bus = BENCH["bus"][chip["bus"]]
    return asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))


async def _main() -> None:
    wdt = arm()
    i2c = _bus()
    scd = SCD30_I2C(i2c)
    sgp = SGP40_I2C(i2c)
    isl = ISL29125_I2C(i2c)
    # The SCD30 measurement prerequisite is the session's `scd30_measuring` fixture; this script writes no NVM.
    await scd.setup()
    await sgp.setup()
    await isl.setup()
    await isl.configure(mode=BENCH["isl29125"]["mode_rgb"], range_fs=10000, resolution=16, threshold_interrupt=False)

    async def scd_read() -> "str | None":
        await scd.read_measurement()
        return None

    async def sgp_cycle() -> "str | None":
        await sgp.initialize()
        return None

    async def sgp_read() -> "str | None":
        raw = await sgp.measure_raw(temperature=25, relative_humidity=50)
        return None if raw is None or 0 <= raw <= 0xFFFF else f"raw={raw} outside the 16-bit range"

    # Interleave: SCD30 reads that start and end inside an SGP40 initialize() ran while its device session was open.
    scd_rec, sgp_rec = Record("scd30", windows=True), Record("sgp40", windows=True)
    stop = Stop()

    async def sgp_phase() -> None:
        await read_loop(sgp_cycle, _SGP40_CYCLES, 0, wdt, sgp_rec, Stop())
        stop.is_set = True

    await asyncio.wait_for(asyncio.gather(read_loop(scd_read, None, 0, wdt, scd_rec, stop), sgp_phase()), _RUN_BOUND_S)
    total, holding = interleaved(scd_rec, sgp_rec)
    fact("scd_reads", scd_rec.reads)
    fact("sgp_cycles", sgp_rec.reads)
    fact("sgp_cycles_planned", _SGP40_CYCLES)
    fact("interleaved_total", total)
    fact("windows_with_interleaving", holding)

    # Rung (a): the SCD30 soft reset (no NVM) among SGP40 and ISL29125 reads, then the time to its next measurement.
    reset_records = [Record("sgp40_during_reset"), Record("isl29125_during_reset")]
    stop = Stop()

    async def reset_phase() -> None:
        await fed_sleep_ms(wdt, _RUNG_TRAFFIC_MS)
        await scd.reset()
        await fed_sleep_ms(wdt, _RUNG_TRAFFIC_MS)
        stop.is_set = True

    await asyncio.wait_for(asyncio.gather(read_loop(sgp_read, None, _SIBLING_STEP_MS, wdt, reset_records[0], stop), read_loop(lambda: isl29125_counts_problem(isl), None, _SIBLING_STEP_MS, wdt, reset_records[1], stop), reset_phase()), _RUN_BOUND_S)
    fact("reset_sibling_errors", sum(r.total for r in reset_records))
    fact("reset_sibling_reads", sum(r.reads for r in reset_records))
    resume_rec = Record("scd30_after_reset")
    resumed_ms = None
    started = time.ticks_ms()
    while resumed_ms is None and time.ticks_diff(time.ticks_ms(), started) < 3 * int(_SCD30_RESUME_S * 1000):
        try:
            ready = await scd.read_measurement()
        except (OSError, RuntimeError, ValueError) as e:  # the bus, a CRC, or a reading the driver refused
            resume_rec.fail(repr(e))
            ready = False
        if ready:
            resumed_ms = time.ticks_diff(time.ticks_ms(), started)
        await fed_sleep_ms(wdt, _SIBLING_STEP_MS)
    fact("scd30_resumed", resumed_ms)
    fact("scd30_resume_bound_ms", int(_SCD30_RESUME_S * 1000))

    # Rung (b): the SGP40 heater-off (datasheet Table 14) among SCD30 and ISL29125 reads, then one SGP40 read.
    heater_records = [Record("scd30_during_heater_off"), Record("isl29125_during_heater_off")]
    stop = Stop()

    async def heater_phase() -> None:
        await fed_sleep_ms(wdt, _RUNG_TRAFFIC_MS)
        await sgp.turn_heater_off()
        await fed_sleep_ms(wdt, _RUNG_TRAFFIC_MS)
        stop.is_set = True

    await asyncio.wait_for(asyncio.gather(read_loop(scd_read, None, _SIBLING_STEP_MS, wdt, heater_records[0], stop), read_loop(lambda: isl29125_counts_problem(isl), None, _SIBLING_STEP_MS, wdt, heater_records[1], stop), heater_phase()), _RUN_BOUND_S)
    fact("heater_off_sibling_errors", sum(r.total for r in heater_records))
    fact("heater_off_sibling_reads", sum(r.reads for r in heater_records))
    fact("sgp_after_heater_off", await sgp.measure_raw(temperature=25, relative_humidity=50))
    report_errors([scd_rec, sgp_rec] + reset_records + [resume_rec] + heater_records)
    done()


asyncio.run(_main())
