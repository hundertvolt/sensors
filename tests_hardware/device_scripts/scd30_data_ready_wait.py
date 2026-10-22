"""Isolated-driver device script, read-only: waits up to three measurement intervals (plus a margin) for the SCD30's
data-ready flag (0x0202) through the driver's public read_measurement(), polling once a second and feeding the
watchdog; reports whether continuous measurement runs, never starts it (tests_hardware/scd30_prerequisite.py)."""

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
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# @tunable l3.scd30_data_ready_poll_ms = 1000
_POLL_MS = 1000
# @tunable l3.scd30_data_ready_wait_margin_s = 2
_MARGIN_S = 2


async def _main() -> None:
    wdt = arm()
    chip = next(instance for instance in BENCH["instances"].values() if instance["driver"] == "scd30")
    bus = BENCH["bus"][chip["bus"]]
    scd = SCD30_I2C(asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout")))
    try:
        await scd.setup()
        budget_ms = (3 * await scd.get_measurement_interval() + _MARGIN_S) * 1000
        waited_ms = 0
        measuring = False
        while not measuring and waited_ms < budget_ms:
            measuring = await scd.read_measurement()
            if not measuring:
                await fed_sleep_ms(wdt, _POLL_MS)
                waited_ms += _POLL_MS
        fact("measuring", measuring)
        fact("co2" if measuring else "waited_s", await scd.get_CO2() if measuring else waited_ms // 1000)
    except (OSError, RuntimeError, ValueError) as e:  # the bus, a CRC, or a reading the driver refused
        fact("error", repr(e))
    done()


asyncio.run(_main())
