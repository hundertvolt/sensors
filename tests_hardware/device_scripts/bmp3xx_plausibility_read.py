"""Isolated-driver device script: one real BMP3xx reading through BMP3XX_Reader, reported for the host to check
against plausibility_bounds.py. Primes reader.cfgmgr from the driver's own schema (no flash I/O) - see
tests_hardware/README.md's device-script cfgmgr-priming note."""

import asyncio

import asy_i2c_driver
from asy_bmp3xx_driver import BMP3XX_Reader

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

# @tunable l3.bmp3xx_plausibility_read_poll_s = 0.5
_POLL_S = 0.5
# @tunable l3.bmp3xx_plausibility_read_poll_tries = 30
_POLL_TRIES = 30


async def _main() -> None:
    wdt = arm()
    bus = BENCH["bus"][BENCH["instances"]["bmp3xx"]["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    reader = BMP3XX_Reader(i2c, BENCH["addresses"]["bmp3xx"], max_module_error=999)
    # Primed in RAM, never reader.cfgmgr.setup(): no flash file I/O, and a schema field added later cannot leave a stale default.
    reader.cfgmgr.valid = True
    reader.cfgmgr._cache = {field[0]: field[2] for field in reader.get_cfg_schema() if field[2] is not None}
    reader.start_timer()  # the 1 s base tick the shared divider (_trigger_loop(), Part C.9) turns into read events
    tasks = (reader.start_asy_trigger(), reader.start_asy_read())
    data = await reader.get_data()
    polls = 0
    while data.Pres is None and polls < _POLL_TRIES:  # a forced-mode conversion takes ~130 ms at most
        await fed_sleep_ms(wdt, int(_POLL_S * 1000))
        data = await reader.get_data()
        polls += 1
    died = []
    for task in tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception as e:  # a task that died on its own is a fact the host fails on
            died.append(repr(e))
        await asyncio.sleep(0)
    reader.stop_timer()
    fact("pressure", data.Pres)
    fact("temperature", data.Temp)
    fact("sea_level_pressure", data.SLPres)
    fact("polls", polls)
    fact("died", died)
    done()


asyncio.run(_main())
