"""Isolated-driver device script: the SCD30 same-device concurrency proof every device gets (owner, 2026-09-03;
SPECIFICATION.md Part C.8): a reader against a concurrent ambient-pressure write that re-sends the value the chip
reports, so its one NVM write leaves the setting unchanged. Reports facts; the host gives the verdict."""

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
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# @tunable l3.scd30_same_device_rw_concurrency_read_iterations = 40
_READ_ITERATIONS = 40
# The measurement interval survives setup()'s soft reset, so data-ready rises while the registers still hold the
# first unsettled conversion (a stuck CO2 on every early read); a few intervals of consumed reads clear it.
# @tunable l3.scd30_same_device_rw_concurrency_settle_s = 12.0
_SETTLE_S = 12.0
# @tunable l3.scd30_same_device_rw_concurrency_settle_step_s = 0.5
_SETTLE_STEP_S = 0.5
# @tunable l3.scd30_same_device_rw_concurrency_run_bound_s = 60.0
_RUN_BOUND_S = 60.0
# The write waits until the reader completed its first read, at most this long (a deadline, never a head start).
# @tunable l3.scd30_same_device_rw_concurrency_writer_delay_s = 0.2
_WRITER_DELAY_S = 0.2
# @tunable l3.scd30_same_device_rw_concurrency_writer_poll_ms = 10
_WRITER_POLL_MS = 10


async def _main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["scd30"]["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    scd = SCD30_I2C(i2c)
    await scd.setup()  # a soft reset: operating state only, no NVM write

    async def consume() -> "str | None":
        await scd.read_measurement()
        return None

    # Discarded on purpose (see _SETTLE_S): a read, not a sleep, because only a read clears data-ready.
    settle = Record("scd30_settle")
    await read_loop(consume, int(_SETTLE_S / _SETTLE_STEP_S), int(_SETTLE_STEP_S * 1000), wdt, settle, Stop())
    fact("settle_failures", settle.total)

    async def read() -> "str | None":
        return await scd30_reading_problem(scd, BENCH["bounds"])

    reader_rec = Record("scd30_reader")

    async def writer() -> None:
        waited_ms = 0
        while reader_rec.reads + reader_rec.total == 0 and waited_ms < _WRITER_DELAY_S * 1000:
            await fed_sleep_ms(wdt, _WRITER_POLL_MS)
            waited_ms += _WRITER_POLL_MS
        _kind, _default, low, high, special = BENCH["scd30_schema"]["AmbPres"]
        try:
            prior = await scd.get_ambient_pressure()
        except (OSError, RuntimeError) as e:  # the bus or a CRC: nothing is sent without the value to re-send
            fact("write_skipped", repr(e))
            return
        if prior != special and not (isinstance(low, int) and isinstance(high, int) and low <= prior <= high):
            fact("write_skipped", prior)
            return
        try:
            await scd.set_ambient_pressure(prior)  # the owned NVM write: the value the chip already holds
            fact("ambient_sent", prior)
        except (OSError, RuntimeError, ValueError) as e:
            fact("write_error", repr(e))
        fact("write_done", True)

    await asyncio.wait_for(asyncio.gather(read_loop(read, _READ_ITERATIONS, 0, wdt, reader_rec, Stop()), writer()), _RUN_BOUND_S)
    fact("read_completed", reader_rec.reads + reader_rec.total)
    fact("reads_planned", _READ_ITERATIONS)
    report_errors([reader_rec])
    done()


asyncio.run(_main())
