"""Isolated-driver device script, read-only: the SCD30's measurement interval (0x4600) after the driver's setup (a soft
reset, no NVM write) on the bench board's SCD30 bus - the first step of the flash tier's prerequisite
(tests_hardware/scd30_prerequisite.py). A failed read is a fact; nothing is sent."""

import asyncio

import asy_i2c_driver
from asy_scd30_driver import SCD30_I2C

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py


async def _main() -> None:
    arm()  # setup()'s soft reset waits 2 s: well inside one watchdog period
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "scd30")
    bus = BENCH["bus"][chip["bus"]]
    scd = SCD30_I2C(asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout")))
    try:
        await scd.setup()
        fact("interval", await scd.get_measurement_interval())
    except (OSError, RuntimeError) as e:  # the bus or the CRC: the host sends nothing without an interval
        fact("error", repr(e))
    done()


asyncio.run(_main())
