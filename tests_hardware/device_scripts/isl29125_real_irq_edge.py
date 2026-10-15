"""Isolated-driver device script: a genuine falling edge on the ISL29125's INT pin drives a read faster than the
periodic fallback. Also measures the two questions no document answers - whether a CONFIG1 write restarts the
conversion, and whether PRST counts RGB cycles or single-channel integrations. Reports facts; the host decides."""

import asyncio
import time

import machine
from machine import Pin
from neopixel import NeoPixel

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_I2C, ISL29125_Reader

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

# A 30 s trigger affords the largest PRST (8 RGB cycles, ~2424 ms at 16 bit) plus the 2-cycle settle, ~3030 ms worst
# case; 6 s is still 5x under the periodic fallback, so a reading inside it means the INT line.
# @tunable l3.isl29125_real_irq_edge_fast_path_deadline_s = 6.0
_FAST_PATH_DEADLINE_S = 6.0
_TRIGGER_S = 30  # deliberately long: only a real interrupt can beat it
_CYCLE_MS_16BIT = 303  # 3 x tINT, tINT = 101 ms typical (FN8424 p.3)
_CHANNEL_MS_16BIT = 101
_PERSIST = 4  # the PRST setting the unit question is timed at (FN8424 p.11 Table 12)
# @tunable l3.isl29125_real_irq_edge_int_poll_ms = 50
_INT_POLL_MS = 50
# @tunable l3.isl29125_real_irq_edge_fast_path_poll_ms = 100
_FAST_PATH_POLL_MS = 100
# @tunable l3.isl29125_real_irq_edge_cycle_margin_ms = 50
_CYCLE_MARGIN_MS = 50
# @tunable l3.isl29125_real_irq_edge_int_poll_tries = 30
_INT_POLL_TRIES = 30
# A WS2812 latches its last value; the dark scene needs this long to reach the part before the first conversion.
# @tunable l3.isl29125_real_irq_edge_dark_settle_ms = 300
_DARK_SETTLE_MS = 300


async def _config1_restart(isl: ISL29125_I2C, wdt: machine.WDT) -> "dict[str, object]":
    # FN8424 p.10 Table 7: an I2C write to 0x01 with SYNC = 0 starts the ADC. If the restart is real the data registers
    # hold the previous cycle's values until a whole cycle has passed; the waits are the experiment, so they stay fixed.
    await isl.configure(mode=BENCH["isl29125"]["mode_rgb"], range_fs=10000, resolution=16, threshold_interrupt=False)
    await fed_sleep_ms(wdt, 2 * _CYCLE_MS_16BIT)
    before = await isl.read_counts()
    await isl.configure(range_fs=375)  # a real CONFIG1 write
    immediately = await isl.read_counts()
    await fed_sleep_ms(wdt, _CYCLE_MS_16BIT + _CYCLE_MARGIN_MS)
    after_one_cycle = await isl.read_counts()
    return {"restarted": immediately == before and after_one_cycle != immediately, "before": before, "immediately": immediately, "after_one_cycle": after_one_cycle}


async def _fast_path(i2c: asy_i2c_driver.I2C, wdt: machine.WDT) -> "dict[str, object]":
    # The real fast path through the real reader: with a 30 s periodic interval, a reading inside the deadline can
    # only have come from the interrupt.
    reader = ISL29125_Reader(i2c, BENCH["instances"]["isl29125"]["irq_pin"], trigger_s=_TRIGGER_S, max_module_error=999)
    reader.cfgmgr.valid = True
    # Seeded from the driver's own schema (command-only entries have no default and are skipped), never a hand list.
    reader.cfgmgr._cache = {field[0]: field[2] for field in reader.get_cfg_schema() if field[2] is not None}
    reader.cfgmgr._cache["SampleInterval"] = _TRIGGER_S
    reader.cfgmgr._cache["AutoRangeDwell"] = 0.0  # no switch-down suppression while the INT edge is under test
    reader.start_timer()
    tasks = (reader.start_asy_trigger(), reader.start_asy_read())
    start = time.ticks_ms()
    lux_ms = None
    while lux_ms is None and time.ticks_diff(time.ticks_ms(), start) < int(_FAST_PATH_DEADLINE_S * 1000):
        if (await reader.get_data()).Lux is not None:
            lux_ms = time.ticks_diff(time.ticks_ms(), start)
        await fed_sleep_ms(wdt, _FAST_PATH_POLL_MS)
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
    return {"fast_path_ms": lux_ms, "deadline_ms": int(_FAST_PATH_DEADLINE_S * 1000), "trigger_s": _TRIGGER_S, "died": died}


async def _persist_unit(isl: ISL29125_I2C, pin: machine.Pin, wdt: machine.WDT) -> "dict[str, object]":
    # FN8424 p.11 Table 12 names PRST's unit an "integration cycle" without saying one channel (~101 ms) or one R-G-B
    # cycle (~303 ms); INTSEL picks one channel, converted once per RGB cycle, so it should be cycles - timed here.
    await isl.configure(mode=BENCH["isl29125"]["mode_rgb"], range_fs=375, resolution=16, threshold_interrupt=True, persist=_PERSIST)
    await isl.set_thresholds(0, 1)  # any light at all is above the window
    await isl.read_status()  # destructive: clears a flag already standing
    start = time.ticks_ms()
    fired_ms = None
    for _ in range(_INT_POLL_TRIES):
        if pin.value() == 0:
            fired_ms = time.ticks_diff(time.ticks_ms(), start)
            break
        await fed_sleep_ms(wdt, _INT_POLL_MS)
    await isl.read_status()  # releases the line again
    per_cycle_ms, per_channel_ms = _PERSIST * _CYCLE_MS_16BIT, _PERSIST * _CHANNEL_MS_16BIT
    unit = None if fired_ms is None else "rgb_cycles" if abs(fired_ms - per_cycle_ms) < abs(fired_ms - per_channel_ms) else "channel_integrations"
    return {"unit": unit, "fired_ms": fired_ms, "rgb_cycles_ms": per_cycle_ms, "channel_integrations_ms": per_channel_ms}


async def _main() -> None:
    wdt = arm()
    # Parked dark first: mpremote run leaves the pixel wherever the WiFi signalling last wrote it (often full white,
    # ~2000 lx here), and a static mid-band scene crosses no threshold.
    np = NeoPixel(Pin(BENCH["instances"]["neopixel"]["pin"], Pin.OUT), n=1)
    try:
        np[0] = (0, 0, 0)
        np.write()
        await fed_sleep_ms(wdt, _DARK_SETTLE_MS)
        bus = BENCH["bus"][BENCH["instances"]["isl29125"]["bus"]]
        i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
        isl = ISL29125_I2C(i2c)
        await isl.setup()
        pin = machine.Pin(BENCH["instances"]["isl29125"]["irq_pin"], mode=machine.Pin.IN, pull=machine.Pin.PULL_UP)
        fact("config1_restart", await _config1_restart(isl, wdt))
        fact("persist_unit", await _persist_unit(isl, pin, wdt))
        for key, value in (await _fast_path(i2c, wdt)).items():
            fact(key, value)
    finally:
        np[0] = (0, 0, 0)
        np.write()
    done()


asyncio.run(_main())
