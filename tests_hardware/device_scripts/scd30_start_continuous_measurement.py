"""Isolated-driver device script, the flash tier's one possible SCD30 NVM write: reads the 0x0010 ambient-pressure word
back and re-sends it once - the continuous-measurement start, so a valid setting is kept. The driver refuses a value
outside 0 or 700..1400 mbar before any send; a non-zero value overwrites altitude compensation (Interface Description 1.4.1)."""

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
    arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "scd30")
    bus = BENCH["bus"][chip["bus"]]
    scd = SCD30_I2C(asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout")))
    sent = False
    try:
        await scd.setup()
        ambient = await scd.get_ambient_pressure()
        fact("ambient", ambient)
        try:
            await scd.set_ambient_pressure(ambient)
            sent = True
        except ValueError:  # the driver's own range check, before any bus traffic: nothing was sent
            fact("invalid_readback", ambient)
    except (OSError, RuntimeError) as e:  # the bus or a CRC; the host never retries after this script ran
        fact("error", repr(e))
    fact("sent", sent)
    done()


asyncio.run(_main())
