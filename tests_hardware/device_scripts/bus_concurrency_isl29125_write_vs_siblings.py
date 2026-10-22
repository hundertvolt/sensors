"""Isolated-driver device script: the real-hardware counterpart to the mock tier's
scenario_a_write_does_not_disturb_concurrent_sibling_reads, with the ISL29125's volatile configure() as the writer
across _WRITE_DELAYS_MS. Why delays, not yields: SPECIFICATION.md Part C.8. Reports facts; the host gives the verdict.
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
    from _shared.bus_reader_loops import Record, Stop, read_loop, report_errors
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Varied, not a fixed cadence: 5 ms is back-to-back with a sibling's transaction, 120 ms is mid another sibling's
# read; cycled so every run covers the whole spread rather than whichever phase natural jitter lands on.
# @tunable l3.bus_concurrency_isl29125_write_vs_siblings_write_delays_ms = 5
_WRITE_DELAYS_MS = (5, 15, 40, 80, 120)
# @tunable l3.bus_concurrency_isl29125_write_vs_siblings_delay_repeats = 2
_DELAY_REPEATS = 2
_WRITE_CYCLES = len(_WRITE_DELAYS_MS) * _DELAY_REPEATS
# @tunable l3.bus_concurrency_isl29125_write_vs_siblings_sibling_step_ms = 15
_SIBLING_STEP_MS = 15
# @tunable l3.bus_concurrency_isl29125_write_vs_siblings_run_bound_s = 60.0
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

    async def sgp_read() -> "str | None":
        raw = await sgp.measure_raw(temperature=25, relative_humidity=50)
        return None if raw is None or 0 <= raw <= 0xFFFF else f"raw={raw} outside the 16-bit range - a torn word"

    scd_rec, sgp_rec, write_rec = Record("scd30"), Record("sgp40"), Record("isl29125_configure", windows=True)
    stop = Stop()

    async def writer() -> None:
        for i in range(_WRITE_CYCLES):
            delay_ms = _WRITE_DELAYS_MS[i % len(_WRITE_DELAYS_MS)]
            await asyncio.sleep_ms(delay_ms)  # the systematically varied offset for this cycle
            start = time.ticks_ms()
            try:
                await isl.configure(ir_adjust=10 + i)
            except Exception as e:  # recorded; the host gives the verdict
                write_rec.fail(f"write {i} at {delay_ms} ms: {type(e).__name__}: {e}")
            else:
                write_rec.reads += 1
                if write_rec.windows is not None:
                    write_rec.windows.append((start, time.ticks_ms()))
            wdt.feed()
        stop.is_set = True

    await asyncio.wait_for(asyncio.gather(read_loop(scd_read, None, _SIBLING_STEP_MS, wdt, scd_rec, stop), read_loop(sgp_read, None, _SIBLING_STEP_MS, wdt, sgp_rec, stop), writer()), _RUN_BOUND_S)
    fact("write_count", write_rec.reads)
    fact("write_cycles_planned", _WRITE_CYCLES)
    fact("isl_windows", write_rec.windows)
    fact("scd_reads", scd_rec.reads)
    fact("sgp_reads", sgp_rec.reads)
    report_errors([scd_rec, sgp_rec, write_rec])
    done()


asyncio.run(_main())
