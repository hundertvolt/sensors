"""Isolated-driver device script: one real ISL29125 reading through ISL29125_Reader with the board lighting its own
scene from the NeoPixel (parked dark on every exit), reported for the host to check against plausibility_bounds.py
and the HSB/CCT coherence rules. Primes reader.cfgmgr from the driver's own schema (no flash I/O)."""

import asyncio

from machine import Pin
from neopixel import NeoPixel

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_Reader

# @include _shared/facts.py
# @include _shared/watchdog.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.facts import done, fact
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

_SELF_LIGHT_LEVEL = 20  # ~750 lx at this geometry: inside range 1, far from clipping
# Lit by the board itself, anything this dark is a real fault rather than a dark bench.
# @tunable l3.isl29125_plausibility_read_room_light_min_lux = 5.0
_ROOM_LIGHT_MIN_LUX = 5.0
# @tunable l3.isl29125_plausibility_read_poll_s = 0.5
_POLL_S = 0.5
# @tunable l3.isl29125_plausibility_read_poll_tries = 30
_POLL_TRIES = 30
# A sample stored after the pixel write may have integrated partly unlit; the second one after it never has.
_FRESH_SAMPLES = 2


async def _read_lit(reader: ISL29125_Reader, wdt: "machine.WDT") -> "dict[str, object]":
    # The reader's tasks until the second sample stored after the scene was lit; returns what that sample holds.
    reader.start_timer()  # the 1 s base tick and the falling-edge INT handler
    tasks = (reader.start_asy_trigger(), reader.start_asy_read())
    last = await reader.get_data()
    fresh = polls = 0
    while fresh < _FRESH_SAMPLES and polls < _POLL_TRIES:
        await fed_sleep_ms(wdt, int(_POLL_S * 1000))
        data = await reader.get_data()
        if data is not last and data.Lux is not None:
            fresh += 1
            last = data
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
    return {"lux": last.Lux, "rgb": [last.Red, last.Green, last.Blue], "hsb": [last.Hue, last.Sat, last.Bri], "cct": last.CCT, "range_act": last.RangeAct, "fresh": fresh, "polls": polls, "died": died}


async def _main() -> None:
    wdt = arm()
    # The board lights its own scene: trusting the bench made the result depend on which test ran before it.
    np = NeoPixel(Pin(BENCH["instances"]["neopixel"]["pin"], Pin.OUT), n=1)
    try:
        np[0] = (_SELF_LIGHT_LEVEL, _SELF_LIGHT_LEVEL, _SELF_LIGHT_LEVEL)
        np.write()
        chip = BENCH["instances"]["isl29125"]
        bus = BENCH["bus"][chip["bus"]]
        i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
        reader = ISL29125_Reader(i2c, chip["irq_pin"], max_module_error=999)
        # Primed in RAM from the driver's own schema (command-only fields have no default), never cfgmgr.setup().
        reader.cfgmgr.valid = True
        reader.cfgmgr._cache = {field[0]: field[2] for field in reader.get_cfg_schema() if field[2] is not None}
        for key, value in (await _read_lit(reader, wdt)).items():
            fact(key, value)
        fact("room_light_min_lux", _ROOM_LIGHT_MIN_LUX)
    finally:
        np[0] = (0, 0, 0)  # the next script gets a known-dark bench
        np.write()
    done()


asyncio.run(_main())
