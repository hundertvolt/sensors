"""Resilience proof: the ISL29125 module under realistic, recombined lighting - colours and
mixtures, slopes from sunrise-slow to flash-instant, rising and falling, starting and ending at
arbitrary levels, held mid-way, oscillating across the range-switch threshold, and a constant
"ambient" channel under a moving one. Structural/relative assertions only, never absolute lux."""

import asyncio
import time

import machine
from machine import Pin
from neopixel import NeoPixel

import asy_i2c_driver
from asy_isl29125_driver import ISL29125, ISL29125_Reader

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from print_log import ErrorLog

# The NeoPixel is driven RAW here on purpose: NeopixelDriver's own API offers a steady white
# (led_overl_bri + on()) and a 0->peak->0 triangle (request_signal), neither of which can express
# an arbitrary start level, end level, pause, step or per-channel waveform. Nothing else contends
# for the pixel in an isolated run, so no arbitration is being bypassed in practice.
_PIN_PIXEL = 18
# Measured on the covered rig (tests_hardware/README.md): rising, the low range holds to level 6
# (~197 lx) and the high range takes over at level 8 (~300 lx); falling, the high range holds to
# level 3 (~112 lx) and the low range takes back over at level 2 (~76 lx). So levels 2..8 sit
# INSIDE the hysteresis band and cannot force a switch in either direction.
_BAND_BELOW = 1  # comfortably under the falling edge
_BAND_ABOVE = 12  # comfortably over the rising edge
_SWITCH_HOLD_S = 8.0  # AutoRangePersist=4 cycles + settle + a 1s sample interval, with margin
_STEP_MS = 100  # light-program update period; a "step" shape lands inside one of these
_SAMPLE_MS = 300  # reader polling; the reader itself produces a fresh sample about once a second
_SETTLE_S = 4.0
_MAX_SAMPLE_GAP_S = 8.0  # a longer stall means the read chain died, not that light moved slowly
_BASELINE_LEVEL = 20
_BASELINE_TOL = 0.35  # return-to-baseline: same light must read the same after ANY scenario

failures: "list[str]" = []
notes: "list[str]" = []


def check(condition: object, message: str) -> None:
    if not condition:
        failures.append(message)


def _lerp(start: "tuple[int, int, int]", end: "tuple[int, int, int]", frac: float) -> "tuple[int, int, int]":
    return (
        int(start[0] + (end[0] - start[0]) * frac),
        int(start[1] + (end[1] - start[1]) * frac),
        int(start[2] + (end[2] - start[2]) * frac),
    )


class Rig:
    """Owns the pixel and the reader, and keeps the running per-sample verdict for one scenario."""

    def __init__(self, pixel: NeoPixel, reader: ISL29125_Reader, wdt: machine.WDT) -> None:
        self.pixel = pixel
        self.reader = reader
        self.wdt = wdt
        self.rgb = (0, 0, 0)
        self.samples = 0
        self.switches = 0
        self.ranges_used: list[int] = []
        self.last_range: int | None = None
        self.last_ts: object = None
        self.last_sample_ms = time.ticks_ms()
        self.max_gap_ms = 0
        self.lux_min = 1e9
        self.lux_max = -1.0
        self.label = ""

    def write(self, rgb: "tuple[int, int, int]") -> None:
        self.rgb = rgb
        self.pixel[0] = rgb
        self.pixel.write()

    def reset_scenario(self, label: str) -> None:
        self.label = label
        self.samples = 0
        self.switches = 0
        self.ranges_used = []
        self.last_range = None
        self.max_gap_ms = 0
        self.lux_min, self.lux_max = 1e9, -1.0
        self.last_sample_ms = time.ticks_ms()

    def observe(self, data: ISL29125) -> None:
        """Per-sample invariants, checked as the sample arrives - no full trace is retained, so
        memory stays flat however long a scenario runs (SPECIFICATION.md Part I)."""
        if data.Lux is None or data.TS is None or self.last_ts == data.TS:
            return
        self.last_ts = data.TS
        self.samples += 1
        now = time.ticks_ms()
        gap = time.ticks_diff(now, self.last_sample_ms)
        self.max_gap_ms = max(self.max_gap_ms, gap)
        self.last_sample_ms = now
        self.lux_min = min(self.lux_min, data.Lux)
        self.lux_max = max(self.lux_max, data.Lux)
        label = f"{self.label}@rgb{self.rgb}"
        check(data.Lux >= 0.0, f"{label}: Lux={data.Lux!r} is negative")
        check(data.RangeAct in (375, 10000), f"{label}: RangeAct={data.RangeAct!r} is neither real range")
        for name, value in (("Red", data.Red), ("Green", data.Green), ("Blue", data.Blue), ("Bri", data.Bri), ("Sat", data.Sat)):
            check(value is not None and 0.0 <= value <= 1.0, f"{label}: {name}={value!r} outside the normalised 0-1 domain")
        check(data.Hue is not None and 0.0 <= data.Hue < 360.0, f"{label}: Hue={data.Hue!r} outside [0, 360)")
        if data.Red is not None and data.Green is not None and data.Blue is not None and data.Bri is not None:
            peak = max(data.Red, data.Green, data.Blue)
            check(abs(data.Bri - peak) <= 1e-6, f"{label}: Bri={data.Bri!r} != max(R,G,B)={peak!r}")
        if data.RangeAct is not None and data.RangeAct not in self.ranges_used:
            self.ranges_used.append(data.RangeAct)
        if self.last_range is not None and data.RangeAct != self.last_range:
            self.switches += 1
        self.last_range = data.RangeAct


async def _drive(rig: Rig, segments: "list[tuple[str, tuple[int, int, int], tuple[int, int, int], float]]") -> None:
    """Runs one light program while sampling continuously. shape is step | ramp | hold."""
    for shape, start, end, duration_s in segments:
        total_ms = int(duration_s * 1000)
        if shape == "step":
            rig.write(end)
        elif shape == "hold":
            rig.write(start)
        elapsed = 0
        begin = time.ticks_ms()
        while elapsed < total_ms:
            if shape == "ramp":
                rig.write(_lerp(start, end, min(1.0, elapsed / total_ms)))
            rig.observe(await rig.reader.get_data())
            rig.wdt.feed()
            await asyncio.sleep_ms(_SAMPLE_MS)
            elapsed = time.ticks_diff(time.ticks_ms(), begin)
        if shape == "ramp":
            rig.write(end)


async def _settled(rig: Rig, rgb: "tuple[int, int, int]") -> "ISL29125 | None":
    """Parks at one colour, waits out the settle, and returns one fresh sample."""
    rig.write(rgb)
    begin = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), begin) < int(_SETTLE_S * 1000):
        rig.observe(await rig.reader.get_data())
        rig.wdt.feed()
        await asyncio.sleep_ms(_SAMPLE_MS)
    data = await rig.reader.get_data()
    return data if data.Lux is not None else None


def _log_entries(counters: "ErrorLog") -> "list[tuple[str, int]]":
    entry = counters.get("ISL29125")
    if entry is None:
        return []
    types, nums = entry["ErrType"], entry["ErrNum"]
    return [(types[i], nums[i]) for i in range(min(len(types), len(nums)))]


async def _run_scenario(rig: Rig, spec: "tuple[str, list[tuple[str, tuple[int, int, int], tuple[int, int, int], float]], int, int, bool]") -> None:
    name, segments, min_switches, max_switches, both_ranges = spec
    rig.reset_scenario(name)
    await rig.reader.reset_error_counter()
    await _drive(rig, segments)
    entries = _log_entries(await rig.reader.get_error_counter())
    errors = [pair for pair in entries if pair[0] == "E"]
    check(not errors, f"{name}: the module logged real ERRORS: {errors}")
    check(rig.samples >= 3, f"{name}: only {rig.samples} samples arrived - the read chain stalled")
    check(rig.max_gap_ms <= int(_MAX_SAMPLE_GAP_S * 1000), f"{name}: {rig.max_gap_ms}ms between samples - the read chain stalled mid-scenario")
    check(rig.switches <= max_switches, f"{name}: {rig.switches} range switches (limit {max_switches}) - chattering")
    # The other half, and the one a passing run can otherwise hide: a scenario built to exercise
    # the range switch must ACTUALLY have exercised it, or it proved nothing.
    check(rig.switches >= min_switches, f"{name}: only {rig.switches} range switches, expected at least {min_switches} - the scenario never engaged the mechanism it targets")
    if both_ranges:
        check(len(rig.ranges_used) == 2, f"{name}: only range(s) {rig.ranges_used} were used - the light never crossed the hysteresis band")
    notes.append(f"{name}: samples={rig.samples} switches={rig.switches} ranges={rig.ranges_used} lux={rig.lux_min:.1f}..{rig.lux_max:.1f} max_gap={rig.max_gap_ms}ms")


async def _baseline(rig: Rig, tag: str, reference: "list[float]") -> None:
    """The resilience check that matters most: identical light must still read the same after
    whatever the previous scenario did. Catches a driver wedged in a range, or stuck state."""
    data = await _settled(rig, (_BASELINE_LEVEL, _BASELINE_LEVEL, _BASELINE_LEVEL))
    check(data is not None and data.Lux is not None, f"baseline after {tag}: no reading at all")
    if data is None or data.Lux is None:
        return
    if not reference:
        reference.append(data.Lux)
        notes.append(f"baseline reference established: {data.Lux:.2f} lux")
        return
    rel = abs(data.Lux - reference[0]) / reference[0]
    check(rel <= _BASELINE_TOL, f"baseline after {tag}: {data.Lux:.2f} lux vs reference {reference[0]:.2f} ({rel * 100:.0f}% off) - the module did not return to a consistent state")


def _scenarios() -> "list[tuple[str, list[tuple[str, tuple[int, int, int], tuple[int, int, int], float]], int, int, bool]]":
    """(name, segments, min_switches, max_switches, must_use_both_ranges).

    Levels are chosen against the MEASURED hysteresis band on this rig (tests_hardware/README.md):
    the low range holds up to level 6 rising, the high range down to level 3 falling, so levels
    2..8 are inside the band and only a level <= 1 or >= 8 can force a switch. Holds that must
    produce a switch are >= _SWITCH_HOLD_S, because AutoRangePersist=4 cycles plus the settle plus
    a 1s sample interval is the real latency of a decision.
    """
    dark, below, inside, full = (0, 0, 0), 1, 5, 255
    lo, hi, sh = _BAND_BELOW, _BAND_ABOVE, _SWITCH_HOLD_S
    return [
        # Slow, sunrise-like. The dark pre-roll is what makes the starting range deterministic:
        # without it the scenario inherits the high range from the preceding baseline and the low
        # range is never touched at all (which is exactly how the first version of this file
        # passed while proving nothing).
        ("sunrise_white_slow", [
            ("hold", dark, dark, sh), ("ramp", dark, (full, full, full), 55.0),
        ], 1, 4, True),
        ("sunset_white_slow", [
            ("hold", (full, full, full), (full, full, full), 5.0),
            ("ramp", (full, full, full), dark, 55.0), ("hold", dark, dark, sh),
        ], 1, 4, True),
        # Medium, dimmer-like, non-zero start and end, paused mid-way, warm mixture.
        ("dimmer_warm_mid", [
            ("hold", dark, dark, sh), ("ramp", dark, (60, 26, 0), 14.0),
            ("hold", (60, 26, 0), (60, 26, 0), 5.0), ("ramp", (60, 26, 0), (2, 1, 0), 14.0),
            ("hold", (2, 1, 0), (2, 1, 0), sh), ("ramp", (2, 1, 0), (120, 52, 0), 14.0),
        ], 2, 6, True),
        # Fast, bulb-turn-on-like, with holds long enough at both ends for the decision to land.
        ("bulb_fast_on_off", [
            ("hold", dark, dark, sh), ("ramp", dark, (full, full, full), 1.0),
            ("hold", (full, full, full), (full, full, full), sh),
            ("ramp", (full, full, full), dark, 1.0), ("hold", dark, dark, sh),
            ("ramp", dark, (30, 30, 30), 1.5), ("hold", (30, 30, 30), (30, 30, 30), 6.0),
        ], 2, 8, True),
        # Instantaneous steps, flash-like, between arbitrary levels and pure colours.
        ("flash_steps", [
            ("hold", dark, dark, sh), ("step", dark, (full, full, full), sh),
            ("step", dark, (below, below, below), sh), ("step", dark, (full, 0, 0), 6.0),
            ("step", dark, (0, 0, full), 6.0), ("step", dark, (inside, inside, inside), 6.0),
        ], 2, 10, True),
        # Oscillation that genuinely crosses BOTH edges of the band - this is the chatter test.
        ("threshold_oscillation_crossing", [
            ("hold", (lo, lo, lo), (lo, lo, lo), sh), ("step", dark, (hi, hi, hi), sh),
            ("step", dark, (lo, lo, lo), sh), ("step", dark, (hi, hi, hi), sh),
            ("step", dark, (lo, lo, lo), sh), ("step", dark, (hi, hi, hi), sh),
        ], 4, 12, True),
        # The complement, and the more important half: light that moves a lot but stays INSIDE the
        # band must produce NO switch at all. This is what hysteresis is for.
        ("hysteresis_band_dwell_no_chatter", [
            ("hold", (inside, inside, inside), (inside, inside, inside), 6.0),
            ("step", dark, (4, 4, 4), 5.0), ("step", dark, (6, 6, 6), 5.0),
            ("step", dark, (3, 3, 3), 5.0), ("step", dark, (6, 6, 6), 5.0),
            ("ramp", (3, 3, 3), (6, 6, 6), 8.0), ("ramp", (6, 6, 6), (3, 3, 3), 8.0),
        ], 0, 0, False),
        # A constant "ambient" channel with a moving "dynamic" one on top of it.
        ("ambient_blue_plus_dynamic_red", [
            ("hold", (0, 0, 10), (0, 0, 10), 6.0), ("ramp", (0, 0, 10), (150, 0, 10), 18.0),
            ("hold", (150, 0, 10), (150, 0, 10), 6.0), ("ramp", (150, 0, 10), (0, 0, 10), 18.0),
        ], 0, 6, False),
        # Single colours and two-colour mixtures at one commanded level.
        ("colour_walk_constant_level", [
            ("step", dark, (60, 0, 0), 5.0), ("step", dark, (0, 60, 0), 5.0),
            ("step", dark, (0, 0, 60), 5.0), ("step", dark, (60, 60, 0), 5.0),
            ("step", dark, (0, 60, 60), 5.0), ("step", dark, (60, 0, 60), 5.0),
            ("step", dark, (60, 60, 60), 5.0),
        ], 0, 8, False),
        # Mixed mode: every shape, overlapping sub-ranges, never returning to zero mid-scenario.
        ("mixed_mode_overlapping", [
            ("hold", dark, dark, sh), ("step", dark, (3, 3, 3), 5.0),
            ("ramp", (3, 3, 3), (25, 10, 40), 10.0), ("hold", (25, 10, 40), (25, 10, 40), 5.0),
            ("step", dark, (200, 200, 60), 6.0), ("ramp", (200, 200, 60), (8, 30, 8), 12.0),
            ("hold", (8, 30, 8), (8, 30, 8), 5.0), ("ramp", (8, 30, 8), (140, 140, 140), 9.0),
            ("step", dark, (below, below, below), sh),
        ], 2, 10, True),
    ]


async def _main() -> None:
    wdt = machine.WDT(timeout=8000)
    i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000, timeout=200000)
    pixel = NeoPixel(Pin(_PIN_PIXEL, Pin.OUT), 1)
    reader = ISL29125_Reader(i2c1, 6, max_module_error=999, fram=None, debug=None)
    reader.cfgmgr.valid = True
    reader.cfgmgr._cache = {
        "SampleInterv": 1, "Resolution": 16, "RangeAuto": True, "Range": 10000,
        "AutoRangeUp": 85.0, "AutoRangeDown": 1.5, "AutoRangeSettle": 1,
        "AutoRangePersist": 4, "AutoRangeDwell": 0.0,
        "IrCompOffset": 0, "IrCompAdjust": 40, "FiltCoeff": -1.0,
    }
    reader.start_timer()
    tasks = [reader.start_asy_trigger(), reader.start_asy_read()]
    rig = Rig(pixel, reader, wdt)
    reference: list[float] = []
    span_lo, span_hi = 1e9, -1.0
    try:
        rig.write((0, 0, 0))
        await asyncio.sleep_ms(500)
        wdt.feed()
        await _baseline(rig, "start", reference)
        for spec in _scenarios():
            await _run_scenario(rig, spec)
            span_lo, span_hi = min(span_lo, rig.lux_min), max(span_hi, rig.lux_max)
            await _baseline(rig, spec[0], reference)
        # Collectively the scenarios must have covered a real dynamic range, not one corner of it.
        check(span_hi > span_lo * 100.0, f"the scenario set only spanned {span_lo:.1f}..{span_hi:.1f} lux - the brightness range was not really covered")
        notes.append(f"combined span across every scenario: {span_lo:.1f}..{span_hi:.1f} lux")
    finally:
        pixel[0] = (0, 0, 0)
        pixel.write()
        for task in tasks:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    for note in notes:
        print("  " + note)
    if failures:
        shown = failures[:12]
        print(f"RESULT: FAIL ({len(failures)} findings) {'; '.join(shown)}")
    else:
        print(f"RESULT: PASS {len(_scenarios())} recombined lighting scenarios - colours, mixtures, slow/medium/fast slopes, steps, pauses, threshold oscillation and an ambient+dynamic split - all handled with no stuck state ({len(notes)} observations)")


asyncio.run(_main())
