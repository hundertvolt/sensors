"""Isolated-driver device script: three concurrent SGP40_I2C.measure_raw() calls on one instance, each with its own
temperature/humidity (SPECIFICATION.md Part C.8). Silicon proves the serialisation only: the chip CRC-checks what an
overwriting caller also wrote, so the payload each session sends is the mock and twin tiers'. Reports the ticks."""

import asyncio

import asy_i2c_driver
from asy_sgp40_driver import SGP40_I2C

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from _shared.facts import done, errors, fact
    from _shared.watchdog import arm
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Three distinct (degC, %RH) inputs inside the datasheet's Table 10 range, the same three the mock and twin tiers send.
_SESSIONS = ((25, 50), (10, 30), (35, 80))
# @tunable l3.sgp40_same_device_concurrent_sessions_run_bound_s = 5.0
_RUN_BOUND_S = 5.0


async def _main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["sgp40"]["bus"]]
    sgp = SGP40_I2C(asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout")))
    await sgp.setup()
    wdt.feed()
    failures: list[str] = []

    async def session(temperature: int, relative_humidity: int) -> "int | None":
        try:
            return await sgp.measure_raw(temperature=temperature, relative_humidity=relative_humidity)
        except (OSError, RuntimeError) as e:  # the bus or a CRC: that session's answer is missing, the others still count
            failures.append(f"{temperature} C/{relative_humidity} %: {e!r}")
            return None

    ticks = await asyncio.wait_for(asyncio.gather(*(session(t, rh) for t, rh in _SESSIONS)), _RUN_BOUND_S)
    wdt.feed()
    fact("ticks", list(ticks))
    errors("errors", len(failures), failures)
    done()


asyncio.run(_main())
