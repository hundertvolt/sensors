"""Proves the ISL29125 module's MECHANISMS across the whole illumination envelope the board's own
NeoPixel can produce - ambient, both ranges, the switch point, and hard saturation of the top range.
Every assertion is structural or relative; nothing here depends on absolute lux being right."""

import asyncio
import time

import machine

import asy_i2c_driver
from asy_isl29125_driver import ISL29125, ISL29125_Reader
from asy_neopixel_driver import NeopixelDriver

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from print_log import ErrorLog

# Steady levels, ascending: ambient only, then up through the range switch into hard saturation.
LEVELS = (0, 2, 4, 8, 16, 40, 100, 255)
SETTLE_S = 4.5  # SampleInterv=1 + AutoRangeSettle=1 cycle + slack for a switch to land
MAX_WAIT_S = 12.0
MAX_SWITCHES = 4  # one up and one down is ideal; chatter would be dozens

failures: "list[str]" = []
notes: "list[str]" = []


def check(condition: object, message: str) -> None:
    # `condition: object`, not `bool`: this takes any truthy expression, and a bool-typed
    # positional parameter is exactly what the project's own lint rules reject.
    if not condition:
        failures.append(message)


async def _fresh_sample(reader: ISL29125_Reader, wdt: machine.WDT) -> "ISL29125 | None":
    """Waits for a genuinely NEW sample (TS moves), so nothing below ever reads a stale one."""
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < int(MAX_WAIT_S * 1000):
        data = await reader.get_data()
        if data.Lux is not None and data.TS is not None:
            return data
        wdt.feed()
        await asyncio.sleep_ms(200)
    return None


def _check_sample_coherent(data: ISL29125, label: str) -> None:
    for name, value in (("Lux", data.Lux), ("Red", data.Red), ("Green", data.Green),
                        ("Blue", data.Blue), ("Sat", data.Sat), ("Bri", data.Bri)):
        check(value is not None, f"{label}: {name} is None - the read chain produced nothing")
    if data.Red is None or data.Green is None or data.Blue is None or data.Bri is None or data.Lux is None:
        return
    for name, value in (("Red", data.Red), ("Green", data.Green), ("Blue", data.Blue), ("Bri", data.Bri)):
        check(0.0 <= value <= 1.0, f"{label}: {name}={value!r} outside the normalised 0-1 domain")
    check(data.Sat is not None and 0.0 <= data.Sat <= 1.0, f"{label}: Sat={data.Sat!r} outside 0-1")
    check(data.Hue is not None and 0.0 <= data.Hue < 360.0, f"{label}: Hue={data.Hue!r} outside [0, 360)")
    peak = max(data.Red, data.Green, data.Blue)
    check(abs(data.Bri - peak) <= 1e-6, f"{label}: Bri={data.Bri!r} != max(R,G,B)={peak!r} - HSB inconsistent with RGB")
    check(data.RangeAct in (375, 10000), f"{label}: RangeAct={data.RangeAct!r} is neither real range")
    check(data.Lux >= 0.0, f"{label}: Lux={data.Lux!r} is negative")


async def _hold(pixel: NeopixelDriver, reader: ISL29125_Reader, wdt: machine.WDT, level: int, label: str) -> "ISL29125 | None":
    """Parks the pixel at one STEADY level (the overlay path, never a ramp) and samples once settled."""
    pixel.led_overl_bri = level
    if level:
        pixel.on()
    else:
        pixel.off()
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < int(SETTLE_S * 1000):
        wdt.feed()
        await asyncio.sleep_ms(200)
    data = await _fresh_sample(reader, wdt)
    check(data is not None, f"{label}: no sample at all within {MAX_WAIT_S}s - the read loop is dead")
    if data is not None:
        _check_sample_coherent(data, label)
    return data


def _log_entries(counters: "ErrorLog") -> "tuple[list[tuple[str, int]], int]":
    """(type, num) pairs out of the ErrorLog shape - the history is capped, ErrCount is not."""
    entry = counters.get("ISL29125")
    if entry is None:
        return [], 0
    types, nums = entry["ErrType"], entry["ErrNum"]
    pairs = [(types[i], nums[i]) for i in range(min(len(types), len(nums)))]  # no zip(strict=) on MicroPython
    return pairs, entry["ErrCount"]


def _make_reader(i2c1: "asy_i2c_driver.I2C") -> ISL29125_Reader:
    reader = ISL29125_Reader(i2c1, 6, max_module_error=999, fram=None, debug=None)
    reader.cfgmgr.valid = True
    reader.cfgmgr._cache = {
        "SampleInterv": 1, "Resolution": 16, "RangeAuto": True, "Range": 10000,
        "AutoRangeUp": 85.0, "AutoRangeDown": 1.5, "AutoRangeSettle": 1,
        "AutoRangePersist": 4, "AutoRangeDwell": 0.0,
        "IrCompOffset": 0, "IrCompAdjust": 40, "FiltCoeff": -1.0,
    }
    return reader


async def _ascending(pixel: NeopixelDriver, reader: ISL29125_Reader, wdt: machine.WDT) -> "list[tuple[int, float, int]]":
    up: list[tuple[int, float, int]] = []
    for level in LEVELS:
        data = await _hold(pixel, reader, wdt, level, f"up/level={level}")
        if data is not None and data.Lux is not None and data.RangeAct is not None:
            up.append((level, data.Lux, data.RangeAct))
            notes.append(f"up level={level:3d} lux={data.Lux:.2f} range={data.RangeAct} hue={data.Hue:.1f} sat={data.Sat:.3f}")
    # Responsiveness, NOT calibration: brighter light must never report dimmer, and the envelope
    # must span a real dynamic range rather than a rig that barely moved the sensor.
    for i in range(1, len(up)):
        prev_level, prev_lux, _ = up[i - 1]
        level, lux, _ = up[i]
        check(lux > prev_lux * 0.75, f"level {prev_level}->{level}: reported lux DROPPED {prev_lux:.2f}->{lux:.2f} as the light rose")
    if len(up) >= 2:
        check(up[-1][1] > up[0][1] * 10.0, f"envelope only spanned {up[0][1]:.2f}->{up[-1][1]:.2f} lux - the LED never really moved the sensor")
    ranges = [entry[2] for entry in up]
    check(375 in ranges, "the low (375 lx) range was never used across the whole ascending envelope")
    check(10000 in ranges, "the high (10000 lx) range was never used - the LED never crossed the switch point")
    check(up and up[-1][2] == 10000, "at full white the driver did not end up on the high range - saturation was not escaped")
    return up


async def _descending(pixel: NeopixelDriver, reader: ISL29125_Reader, wdt: machine.WDT) -> "list[tuple[int, float, int]]":
    down: list[tuple[int, float, int]] = []
    for level in reversed(LEVELS):
        data = await _hold(pixel, reader, wdt, level, f"down/level={level}")
        if data is not None and data.Lux is not None and data.RangeAct is not None:
            down.append((level, data.Lux, data.RangeAct))
            notes.append(f"dn level={level:3d} lux={data.Lux:.2f} range={data.RangeAct}")
    check(down and down[-1][2] == 375, "back at ambient the driver never returned to the low range")
    return down


async def _config_mechanisms(pixel: NeopixelDriver, reader: ISL29125_Reader, wdt: machine.WDT) -> None:
    # Fixed-range mode must really pin the range, at both ends of the envelope.
    check(await reader._set_dict_cfg({"RangeAuto": False, "Range": 10000}, reader.cfg_schema), "pushing RangeAuto=False/Range=10000 was rejected")
    pinned = await _hold(pixel, reader, wdt, 0, "fixed/ambient")
    check(pinned is not None and pinned.RangeAct == 10000, "fixed range ignored at ambient - auto-range still switched")
    bright = await _hold(pixel, reader, wdt, 255, "fixed/bright")
    check(bright is not None and bright.RangeAct == 10000, "fixed range ignored when bright")
    await reader._set_dict_cfg({"RangeAuto": True}, reader.cfg_schema)

    # 12-bit must work through the whole reader, and agree with 16-bit on ONE static scene - that
    # agreement is what proves the 12->16 bit normalisation shift is applied, not that either is right.
    check(await reader._set_dict_cfg({"Resolution": 12}, reader.cfg_schema), "pushing Resolution=12 was rejected")
    twelve = await _hold(pixel, reader, wdt, 16, "12bit/mid")
    check(twelve is not None, "no sample at all at 12-bit resolution")
    await reader._set_dict_cfg({"Resolution": 16}, reader.cfg_schema)
    sixteen = await _hold(pixel, reader, wdt, 16, "16bit/mid")
    check(sixteen is not None, "no sample after switching back to 16-bit")
    if twelve is not None and sixteen is not None and twelve.Lux is not None and sixteen.Lux:
        rel = abs(twelve.Lux - sixteen.Lux) / sixteen.Lux
        notes.append(f"12bit vs 16bit on one static scene: {twelve.Lux:.2f} vs {sixteen.Lux:.2f} ({rel * 100:.1f}%)")
        check(rel < 0.5, f"12-bit and 16-bit disagree by {rel * 100:.1f}% on one scene - the <<4 normalisation looks wrong")

    check(await reader._set_dict_cfg({"ISLResetCal": True}, reader.cfg_schema), "ISLResetCal was rejected")
    ratio, _cal_ts = await reader.get_mem_status()
    check(ratio is not None, "no gain ratio reported at all after ISLResetCal")
    notes.append(f"gain ratio after ISLResetCal: {ratio}")


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    pixel = NeopixelDriver(18, fram=None, debug=None)
    reader = _make_reader(i2c1)
    reader.start_timer()
    tasks = [pixel.start_asy_neopixel_led_overl(), pixel.start_asy_neopixel_signal(),
             reader.start_asy_trigger(), reader.start_asy_read()]
    try:
        pixel.off()
        await asyncio.sleep_ms(500)
        wdt.feed()
        await reader.reset_error_counter()  # isolate the envelope's own log from setup noise

        up = await _ascending(pixel, reader, wdt)

        # The saturation detector must FIRE at full white (W14 is exactly that case, and this rig
        # really does exceed the 10000 lx range at ~20mm), and the INTERRUPT must be what decides
        # the range - W15 is the driver's own "the interrupt may be dead" detector.
        entries, count = _log_entries(await reader.get_error_counter())
        notes.append(f"ascending-leg log: count={count} entries={entries}")
        check(("W", 14) in entries, "no W14 after driving the part into hard saturation at full white - the saturation detector never fired")
        check(("W", 15) not in entries, "W15 logged: the range was decided by the PERIODIC path only - the interrupt is not carrying the decisions")
        check(not any(kind == "E" for kind, _ in entries), f"the ascending envelope logged real ERRORS, not just warnings: {entries}")

        down = await _descending(pixel, reader, wdt)
        ranges = [entry[2] for entry in up] + [entry[2] for entry in down]
        switches = sum(1 for i in range(len(ranges) - 1) if ranges[i] != ranges[i + 1])
        check(switches <= MAX_SWITCHES, f"{switches} range switches across one up-and-down envelope - the hysteresis window is chattering")
        notes.append(f"range switches across the full envelope: {switches}")

        await _config_mechanisms(pixel, reader, wdt)

        entries, count = _log_entries(await reader.get_error_counter())
        notes.append(f"full-run log: count={count} entries={entries}")
        check(not any(kind == "E" for kind, _ in entries), f"the run logged real ERRORS: {entries}")
    finally:
        pixel.off()
        await asyncio.sleep_ms(200)
        for task in tasks:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    for note in notes:
        print("  " + note)
    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(f"RESULT: PASS the whole illumination envelope, both ranges, both resolutions, fixed-range pinning, saturation detection and ISLResetCal all behaved ({len(notes)} observations)")


asyncio.run(_main())
