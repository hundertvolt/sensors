"""The one writer bus_concurrency_isl29125_write_vs_siblings.py cannot cover: the SCD30 itself, whose NVM carries a real
wear budget, so this is AND-gated behind --allow-persistence-write plus --allow-scd30-extra-write; it spends two SCD30
NVM writes (the offset and its restore) among the ISL29125 and SGP40 reads (SPECIFICATION.md Part C.8)."""

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
    from _shared.bus_reader_loops import Record, Stop, isl29125_counts_problem, overlapped, read_loop, report_errors
    from _shared.facts import done, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# @tunable l3.bus_concurrency_scd30_write_vs_siblings_sibling_step_ms = 15
_SIBLING_STEP_MS = 15
# @tunable l3.bus_concurrency_scd30_write_vs_siblings_after_write_s = 1.0
_AFTER_WRITE_S = 1.0
# @tunable l3.bus_concurrency_scd30_write_vs_siblings_run_bound_s = 60.0
_RUN_BOUND_S = 60.0
# The write waits until both siblings completed a read, then for an SGP40 round's head, both by this deadline.
# @tunable l3.bus_concurrency_scd30_write_vs_siblings_writer_delay_ms = 1000
_WRITER_DELAY_MS = 1000
# The offset the write sends, inside the schema's TempOffset range; the restore sends back what the chip held.
_WRITE_OFFSET_C = 4.0


async def _main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["scd30"]["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    scd = SCD30_I2C(i2c)
    isl = ISL29125_I2C(i2c)
    sgp = SGP40_I2C(i2c)
    await scd.setup()
    await isl.setup()
    await isl.configure(mode=BENCH["isl29125"]["mode_rgb"], range_fs=10000, resolution=16, threshold_interrupt=False)
    await sgp.setup()

    async def sgp_read() -> "str | None":
        await sgp.measure_raw(temperature=25, relative_humidity=50)
        return None

    isl_rec, sgp_rec, write_rec = Record("isl29125", windows=True), Record("sgp40", windows=True), Record("scd30_write", windows=True)
    stop = Stop()
    prior = None
    try:
        prior = await scd.get_temperature_offset()
    except (OSError, RuntimeError) as e:  # the bus or a CRC: nothing is written without the value to restore
        write_rec.fail(f"prior offset read: {e!r}")
    fact("prior_offset", prior)

    async def writer() -> None:
        deadline = time.ticks_add(time.ticks_ms(), _WRITER_DELAY_MS)
        while (isl_rec.reads == 0 or sgp_rec.reads == 0) and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            await fed_sleep_ms(wdt, _SIBLING_STEP_MS)
        # Then an SGP40 round's head: the write begins inside that sibling's session, ahead of its command, which then
        # waits on the bus (its CRC staging yields first, src/asy_crc_checks.py _crc()).
        was_in_flight = sgp_rec.in_flight
        while (was_in_flight or not sgp_rec.in_flight) and time.ticks_diff(deadline, time.ticks_ms()) > 0:
            was_in_flight = sgp_rec.in_flight
            await asyncio.sleep_ms(0)
        fact("write_in_sgp_round", sgp_rec.in_flight)  # read where the write begins: one the deadline sent outside a round shows
        start = time.ticks_ms()
        try:
            await scd.set_temperature_offset(_WRITE_OFFSET_C)  # owned writes: the offset, and its restore after the run
            end = time.ticks_ms()
            fact("write_done", time.ticks_diff(end, start))
            if write_rec.windows is not None:
                write_rec.windows.append((start, end))
        except (OSError, RuntimeError, ValueError) as e:
            fact("write_error", repr(e))
        await fed_sleep_ms(wdt, int(_AFTER_WRITE_S * 1000))
        stop.is_set = True

    if prior is None:
        fact("write_skipped", True)
        stop.is_set = True
    else:
        await asyncio.wait_for(asyncio.gather(read_loop(lambda: isl29125_counts_problem(isl), None, _SIBLING_STEP_MS, wdt, isl_rec, stop), read_loop(sgp_read, None, _SIBLING_STEP_MS, wdt, sgp_rec, stop), writer()), _RUN_BOUND_S)
        try:
            await scd.set_temperature_offset(prior)
            fact("restored", await scd.get_temperature_offset())
        except (OSError, RuntimeError, ValueError) as e:
            fact("restore_error", repr(e))
    fact("isl_reads", isl_rec.reads)
    fact("sgp_reads", sgp_rec.reads)
    fact("overlapped_reads", overlapped(write_rec, [isl_rec, sgp_rec]))
    report_errors([isl_rec, sgp_rec, write_rec])
    done()


asyncio.run(_main())
