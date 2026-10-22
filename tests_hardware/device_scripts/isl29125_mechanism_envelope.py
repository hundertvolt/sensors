"""The ISL29125 module's mechanisms across the whole illumination envelope the board's own NeoPixel can produce -
ambient, both ranges, the switch point, cross-range continuity, saturation, fixed range, both resolutions and the
calibration trigger - over a scratch config file. Reports every sample and setting result; the host gives the verdict.
"""

import asyncio
import errno
import os
import time

import asy_base_classes
import asy_i2c_driver
from asy_config_manager import UNCHANGED, VALID
from asy_isl29125_driver import ISL29125, ISL29125_Reader
from asy_neopixel_driver import NeopixelDriver

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/isl_error_log.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.facts import done, fact
    from _shared.isl_error_log import log_record
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# Steady levels, ascending: ambient only, then up through the range switch into hard saturation.
_LEVELS = (0, 2, 4, 8, 16, 40, 100, 255)
# SampleInterval 1 s, the fixed 2-cycle settle and slack for a switch to land; then a sample stored after it.
# @tunable l3.isl29125_mechanism_envelope_settle_s = 4.5
_SETTLE_S = 4.5
# @tunable l3.isl29125_mechanism_envelope_max_wait_s = 12.0
_MAX_WAIT_S = 12.0
# One up and one down is ideal; chatter would be dozens.
# @tunable l3.isl29125_mechanism_envelope_max_switches = 4
_MAX_SWITCHES = 4
_OVERLAP_LEVEL = 4  # ~150 lx on this rig: ~40 % of the low range's full scale, so both ranges can represent it
# A relative bound on the gain step, not a calibration claim: the ratio band 20-34 around 26.67 leaves ~25 % at worst.
# @tunable l3.isl29125_mechanism_envelope_max_range_step = 0.25
_MAX_RANGE_STEP = 0.25
# @tunable l3.isl29125_mechanism_envelope_poll_ms = 200
_POLL_MS = 200
# @tunable l3.isl29125_mechanism_envelope_min_step_ratio = 0.75
_MIN_STEP_RATIO = 0.75
# @tunable l3.isl29125_mechanism_envelope_min_span_ratio = 10.0
_MIN_SPAN_RATIO = 10.0
# @tunable l3.isl29125_mechanism_envelope_bit_depth_rel_max = 0.5
_BIT_DEPTH_REL_MAX = 0.5
W_ISL_PERIODIC_ONLY = 32  # buildgen/error_catalog.json: five range decisions by the periodic path only
# A scratch file: _set_dict_cfg() persists through write_config(), which would stamp the seeded cache over the
# production config_ISL29125.cfg; removed first (an aborted run's leftover) and on every way out.
_SCRATCH_FILE = "config_HWTEST_ISL29125.cfg"


async def _config_mechanisms(pixel: NeopixelDriver, reader: ISL29125_Reader, wdt: "machine.WDT") -> None:
    # Fixed range pinned at both ends; 12- and 16-bit on one scene (the 12->16 bit shift applied); one stationary
    # light read on each range in turn (the honest gain-step measurement); the calibration trigger.
    fixed: dict[str, object] = {"pinned": await _push(reader, {"RangeAuto": False, "Range": 10000})}
    fixed["ambient"] = _sample(0, await _hold(pixel, reader, wdt, 0))
    fixed["bright"] = _sample(255, await _hold(pixel, reader, wdt, 255))
    fixed["restored"] = await _push(reader, {"RangeAuto": True})
    fact("fixed_range", fixed)
    depth: dict[str, object] = {"pushed_12": await _push(reader, {"Resolution": 12})}
    depth["at_12"] = _sample(16, await _hold(pixel, reader, wdt, 16))
    depth["pushed_16"] = await _push(reader, {"Resolution": 16})
    depth["at_16"] = _sample(16, await _hold(pixel, reader, wdt, 16))
    fact("bit_depth", depth)
    continuity: dict[str, object] = {"pinned_low": await _push(reader, {"RangeAuto": False, "Range": 375})}
    continuity["low"] = _sample(_OVERLAP_LEVEL, await _hold(pixel, reader, wdt, _OVERLAP_LEVEL))
    continuity["pinned_high"] = await _push(reader, {"Range": 10000})
    continuity["high"] = _sample(_OVERLAP_LEVEL, await _hold(pixel, reader, wdt, _OVERLAP_LEVEL))
    continuity["restored"] = await _push(reader, {"RangeAuto": True})
    fact("continuity", continuity)
    applied_before = reader._gain_ratio
    pushed = await _push(reader, {"Calibrate": True})
    fact("calibrate", {"pushed": pushed, "calibrating": reader._calibrating, "measured_ratio": reader._measured_ratio(), "applied_before": applied_before, "applied_after": reader._gain_ratio})


async def _envelope(pixel: NeopixelDriver, reader: ISL29125_Reader, wdt: "machine.WDT") -> None:
    pixel.off()
    await fed_sleep_ms(wdt, _POLL_MS)
    fact("reset_error_counter", await reader.reset_error_counter())  # the envelope's own log, apart from setup noise
    fact("up", await _sweep(pixel, reader, wdt, _LEVELS))
    # Overrange is a live measurement field; ISL_PERIODIC_ONLY stays a log check, which one leg cannot reach (a guard).
    fact("overrange_at_full", (await reader.get_data()).Overrange)
    fact("ascending_log", log_record(await reader.get_error_counter(), reader.name))
    fact("down", await _sweep(pixel, reader, wdt, tuple(reversed(_LEVELS))))
    await _config_mechanisms(pixel, reader, wdt)
    fact("full_log", log_record(await reader.get_error_counter(), reader.name))


async def _hold(pixel: NeopixelDriver, reader: ISL29125_Reader, wdt: "machine.WDT", level: int) -> "ISL29125 | None":
    # One steady level (the overlay path, never a ramp), the settle, then the first sample stored after it: a new TS
    # (the clock is set valid below), so no sample converted before the level changed is ever taken.
    pixel._overlay_bri = level
    if level:
        pixel.on()
    else:
        pixel.off()
    await fed_sleep_ms(wdt, int(_SETTLE_S * 1000))
    stale = (await reader.get_data()).TS
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < int(_MAX_WAIT_S * 1000):
        data = await reader.get_data()
        if data.Lux is not None and stale != data.TS:
            return data
        await fed_sleep_ms(wdt, _POLL_MS)
    return None


async def _push(reader: ISL29125_Reader, values: "dict[str, object]") -> bool:
    # A config push through the reader, every field answered VALID or UNCHANGED: its result is checked, never dropped.
    results = await reader._set_dict_cfg(values, reader.get_cfg_schema())  # type: ignore[arg-type]
    return all(results.get(key) in (VALID, UNCHANGED) for key in values)


def _sample(level: int, data: "ISL29125 | None") -> "dict[str, object] | None":
    if data is None:
        return None
    return {"level": level, "lux": data.Lux, "range": data.RangeAct, "rgb": [data.Red, data.Green, data.Blue], "hsb": [data.Hue, data.Sat, data.Bri]}


async def _sweep(pixel: NeopixelDriver, reader: ISL29125_Reader, wdt: "machine.WDT", levels: "tuple[int, ...]") -> "list[dict[str, object] | None]":
    samples = []
    for level in levels:
        samples.append(_sample(level, await _hold(pixel, reader, wdt, level)))
    return samples


async def _main() -> None:
    wdt = arm()
    try:
        os.remove(_SCRATCH_FILE)
    except OSError as e:
        if e.errno != errno.ENOENT:
            fact("leftover_errno", e.errno)
    chip = BENCH["instances"]["isl29125"]
    bus = BENCH["bus"][chip["bus"]]
    reader = None
    pixel = NeopixelDriver(BENCH["instances"]["neopixel"]["pin"])
    try:
        i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
        reader = ISL29125_Reader(i2c, chip["irq_pin"], max_module_error=999)
        reader.cfgmgr._config_file = _SCRATCH_FILE
        reader.cfgmgr.valid = True
        # Seeded from the driver's own schema (command-only fields have no default), never a hand-copied list.
        reader.cfgmgr._cache = {field[0]: field[2] for field in reader.get_cfg_schema() if field[2] is not None}
        reader.cfgmgr._cache["AutoRangeDwell"] = 0.0  # no switch-down suppression: the sweep drives the range loop on purpose
        # TS tells a new sample from a re-read one only once the clock is valid (Part G.2); no NTP runs here.
        asy_base_classes.set_utc_valid()
        reader.start_timer()
        tasks = [pixel.start_asy_overlay(), pixel.start_asy_signal(), reader.start_asy_trigger(), reader.start_asy_read()]
        try:
            await _envelope(pixel, reader, wdt)
        finally:
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
            fact("died", died)
            fact("bounds", {"min_step_ratio": _MIN_STEP_RATIO, "min_span_ratio": _MIN_SPAN_RATIO, "max_switches": _MAX_SWITCHES, "max_range_step": _MAX_RANGE_STEP, "bit_depth_rel_max": _BIT_DEPTH_REL_MAX, "periodic_only": W_ISL_PERIODIC_ONLY})
    finally:
        pixel.off()
        asy_base_classes.set_utc_valid(valid=False)  # the clock state this script set is its own
        if reader is not None:
            await reader.cfgmgr.flush_pending()
        try:
            os.remove(_SCRATCH_FILE)
        except OSError as e:  # no push ever reached flash: nothing to remove
            if e.errno != errno.ENOENT:
                fact("scratch_remove_errno", e.errno)
    done()


asyncio.run(_main())
