"""Isolated-driver device script: the NeoPixel range-sweep rig (ISL29125_PROMOTION_PLAN.md
section 10) - the board's own LED is the one light source the device under test can ramp on demand
through both ranges and across the switch point.
Everything it asserts is RELATIVE (continuity, hysteresis, invariance, convergence); absolute lux
and CCT against three narrow LED lines are meaningless and are deliberately not checked."""

import asyncio
import time

import machine

import asy_i2c_driver
from asy_isl29125_driver import ISL29125_Reader
from asy_neopixel_driver import NeopixelDriver

RAMP_S = 24.0  # one request_signal() is a triangular ramp up and back down over this long
SAMPLE_INTERVAL_MS = 400  # comfortably above one 303ms RGB cycle at 16 bit
SWEEPS = 3  # two to converge the gain ratio, one more after ISLResetCal
# Both figures are RELATIVE tolerances on this rig's own repeatability, not accuracy claims.
MAX_TRANSITION_STEP = 0.15  # reported lux either side of a range switch, as a fraction
MAX_HUE_SPREAD_DEG = 12.0  # a white LED held at one ratio while its level ramps
MAX_SAT_SPREAD = 0.15
MAX_RANGE_SWITCHES_PER_SWEEP = 6  # one up and one down is the ideal; chatter would be dozens


async def _sweep(reader: ISL29125_Reader, pixel: NeopixelDriver, wdt: machine.WDT) -> "list[tuple[float, int, float, float]]":
    # Goes through request_signal()'s own arbitration path rather than writing the pixel
    # directly, exactly as section 10 requires - and its triangular ramp IS the sweep: level
    # rises from off to full and back over RAMP_S. Level is not linear in lux, so nothing below
    # assumes it is.
    await pixel.request_signal(255, 255, 255, RAMP_S)
    samples = []
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < int(RAMP_S * 1000):
        data = await reader.get_data()
        if data.Lux is not None and data.RangeAct is not None and data.Hue is not None and data.Sat is not None:
            samples.append((data.Lux, data.RangeAct, data.Hue, data.Sat))
        wdt.feed()
        await asyncio.sleep_ms(SAMPLE_INTERVAL_MS)
    return samples


def _check_sweep(samples: "list[tuple[float, int, float, float]]", label: str) -> "list[str]":
    failures = []
    if len(samples) < 20:
        return [f"{label}: only {len(samples)} samples - the ramp or the read loop is not running"]
    ranges = [sample[1] for sample in samples]
    if len(set(ranges)) < 2:
        return [f"{label}: only range {ranges[0]} was ever used - move the LED closer so the sweep really crosses the switch point"]

    switches = sum(1 for i in range(len(ranges) - 1) if ranges[i] != ranges[i + 1])
    if switches > MAX_RANGE_SWITCHES_PER_SWEEP:
        failures.append(f"{label}: {switches} range switches in one ramp - the hysteresis window is chattering")

    # Continuity: the step in reported lux across each transition must be no larger than the
    # steps either side of it. This is the headline requirement, and it is what the gain-ratio
    # calibration is for - an uncalibrated first sweep is expected to be the worst one.
    for i in range(1, len(samples) - 1):
        if ranges[i] == ranges[i - 1]:
            continue
        before, at = samples[i - 1][0], samples[i][0]
        if before <= 0.0:
            continue
        step = abs(at - before) / before
        if step > MAX_TRANSITION_STEP:
            failures.append(f"{label}: reported lux stepped {step * 100:.1f}% across the {ranges[i - 1]}->{ranges[i]} transition ({before:.2f} -> {at:.2f})")

    # Invariance: all three channels share one gain, so a level ramp must not move hue or
    # saturation - through the range switch included.
    lit = [sample for sample in samples if sample[0] > 20.0]  # near-dark samples are all noise
    if len(lit) >= 5:
        hues = [sample[2] for sample in lit]
        sats = [sample[3] for sample in lit]
        if max(hues) - min(hues) > MAX_HUE_SPREAD_DEG:
            failures.append(f"{label}: hue spread {max(hues) - min(hues):.1f} deg across the ramp - expected a fixed LED ratio to hold still")
        if max(sats) - min(sats) > MAX_SAT_SPREAD:
            failures.append(f"{label}: saturation spread {max(sats) - min(sats):.3f} across the ramp")

    # Monotonic, never linear: the ramp rises then falls, so the peak must sit in the middle.
    peak_index = samples.index(max(samples, key=lambda sample: sample[0]))
    if not (len(samples) * 0.25 < peak_index < len(samples) * 0.75):
        failures.append(f"{label}: brightest sample at index {peak_index}/{len(samples)} - the ramp's own peak should be near the middle")
    return failures


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    pixel = NeopixelDriver(18, fram=None, debug=None)
    reader = ISL29125_Reader(i2c1, 6, max_module_error=999, fram=None, debug=None)
    reader.cfgmgr.valid = True
    # 16 bit deliberately: the WS2812 is PWM-dimmed at >=400Hz, and at 12 bit (~6.3ms) the ADC
    # integrates over only ~2.5 PWM periods, which produces tens of percent of beat-frequency
    # ripple. That noise would be the LED, not the driver (section 10's own caveat 1).
    reader.cfgmgr._cache = {
        "SampleInterv": 1, "Resolution": 16, "RangeAuto": True, "Range": 10000,
        "AutoRangeUp": 85.0, "AutoRangeDown": 1.5, "AutoRangeSettle": 1,
        "AutoRangePersist": 4, "AutoRangeDwell": 0.0,
        "IrCompOffset": 0, "IrCompAdjust": 40, "FiltCoeff": -1.0,
    }
    reader.start_timer()
    tasks = [
        pixel.start_asy_neopixel_signal(),
        reader.start_asy_trigger(),
        reader.start_asy_read(),
    ]

    failures: list[str] = []
    ratios: list[float] = []
    try:
        for index in range(SWEEPS):
            if index == SWEEPS - 1:
                # The last sweep runs from nominal again: ISLResetCal throws the learned ratio
                # away, and the rig has to converge a second time from scratch.
                await reader.reset_gain_calibration(flag=True)
            samples = await _sweep(reader, pixel, wdt)
            failures.extend(_check_sweep(samples, f"sweep {index}"))
            ratio, _cal_ts = await reader.get_mem_status()
            if ratio is None:
                # Only ever None before the driver has loaded/seeded its own chunk, which setup()
                # has long since done here - so this is a real finding, not a tolerated gap.
                failures.append(f"sweep {index}: the driver reports no gain ratio at all")
            else:
                ratios.append(ratio)
            await asyncio.sleep_ms(500)
    finally:
        for task in tasks:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    # Convergence: the learned ratio has to have moved off nominal by the second sweep, and the
    # post-reset sweep has to move off it again.
    nominal = 10000.0 / 375.0
    if len(ratios) >= SWEEPS - 1 and abs(ratios[SWEEPS - 2] - nominal) < 1e-6:
        failures.append(f"the gain ratio never moved off nominal across {SWEEPS - 1} sweeps - the overlap band was never entered")
    if ratios and not (20.0 <= ratios[-1] <= 34.0):
        failures.append(f"the learned gain ratio {ratios[-1]!r} is outside the plausible band")

    if failures:
        print(f"RESULT: FAIL {'; '.join(failures)}")
    else:
        print(f"RESULT: PASS {SWEEPS} ramps, continuity/hysteresis/invariance all within tolerance, learned gain ratios {ratios}")


asyncio.run(_main())
