"""Resilience proof: the ISL29125 under recombined realistic lighting - colours and mixtures, sunrise-slow to
flash-instant, arbitrary start and end levels, holds, threshold oscillation and a constant ambient under a moving
channel. Reports each scenario's figures and its log; the host gives the verdict, never on absolute lux."""

import asyncio
import time

from machine import Pin
from neopixel import NeoPixel

import asy_i2c_driver
from asy_isl29125_driver import ISL29125, ISL29125_Reader

# @include _shared/facts.py
# @include _shared/watchdog.py
# @include _shared/isl_error_log.py

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import machine
    from _shared.facts import done, errors, fact
    from _shared.isl_error_log import log_record
    from _shared.watchdog import arm, fed_sleep_ms
    from bench_facts import BenchFacts

BENCH: "BenchFacts" = {}  # rendered by tests_hardware/harness.py

# The NeoPixel is driven raw on purpose: NeopixelDriver's steady white and 0->peak->0 triangle cannot express an
# arbitrary start, end, pause, step or per-channel waveform; nothing else contends for the pixel in an isolated run.

# Measured on the covered rig: the low range holds rising to level 6 (~197 lx), the high takes over at 8 (~300 lx);
# falling, high holds to 3 (~112 lx), low takes back at 2 (~76 lx) - levels 2..8 sit inside the hysteresis band.
_BAND_BELOW = 1  # comfortably under the falling edge
_BAND_ABOVE = 12  # comfortably over the rising edge
# @tunable l3.isl29125_lighting_scenarios_switch_hold_s = 8.0
_SWITCH_HOLD_S = 8.0  # the derived 2 cycles + settle + a 1 s sample interval, with margin
# @tunable l3.isl29125_lighting_scenarios_sample_ms = 300
_SAMPLE_MS = 300  # reader polling; the reader itself produces a fresh sample about once a second
# @tunable l3.isl29125_lighting_scenarios_settle_s = 4.0
_SETTLE_S = 4.0
# @tunable l3.isl29125_lighting_scenarios_max_sample_gap_s = 8.0
_MAX_SAMPLE_GAP_S = 8.0  # a longer stall means the read chain died, not that the light moved slowly
_BASELINE_LEVEL = 20
# @tunable l3.isl29125_lighting_scenarios_baseline_tol = 0.35
_BASELINE_TOL = 0.35  # return-to-baseline: the same light must read the same after any scenario
# @tunable l3.isl29125_lighting_scenarios_park_stable_samples = 3
_PARK_STABLE_SAMPLES = 3  # consecutive same-range samples that count as "the entry range has settled"
# @tunable l3.isl29125_lighting_scenarios_park_timeout_s = 20.0
_PARK_TIMEOUT_S = 20.0
# @tunable l3.isl29125_lighting_scenarios_min_samples = 3
_MIN_SAMPLES = 3
# @tunable l3.isl29125_lighting_scenarios_min_span_ratio = 100.0
_MIN_SPAN_RATIO = 100.0
# Five periodic-path range decisions in a row raise ISL_PERIODIC_ONLY: fewer switches than that in a run could not.
# @tunable isl29125.periodic_only_warn_at = 5
_PERIODIC_ONLY_WARN_AT = 5
W_ISL_PERIODIC_ONLY = 32  # buildgen/error_catalog.json: five range decisions by the periodic path only
_FAILURES_KEPT = 12  # the per-sample invariant failures kept beside their total


async def _drive(rig: "Rig", segments: "list[tuple[str, tuple[int, int, int], tuple[int, int, int], float]]") -> None:
    # Runs one light program while sampling continuously. shape is step | ramp | hold.
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
            await fed_sleep_ms(rig.wdt, _SAMPLE_MS)
            elapsed = time.ticks_diff(time.ticks_ms(), begin)
        if shape == "ramp":
            rig.write(end)


class Rig:
    # Owns the pixel and the reader and keeps one scenario's running figures. A new sample is a newly stored reading
    # (object identity, never the 1 s TS); a range switch is any change of RangeAct between two polls.

    def __init__(self, pixel: NeoPixel, reader: ISL29125_Reader, wdt: "machine.WDT") -> None:
        self._pixel = pixel
        self.reader = reader
        self.wdt = wdt
        self.rgb = (0, 0, 0)
        self.failures_total = 0
        self.failures_first: list[str] = []
        self.total_switches = 0  # across every scenario: reset_scenario() leaves it alone
        self.last_data: object = None
        self.last_range: int | None = None
        # One scenario's figures, typed here and set by reset_scenario().
        self.label = ""
        self.samples = self.switches = self.max_gap_ms = 0
        self.ranges_used: list[int] = []
        self.lux_min = self.lux_max = 0.0
        self.last_sample_ms = time.ticks_ms()
        self.reset_scenario("")

    def check(self, condition: object, message: str) -> None:
        if not condition:
            self.failures_total += 1
            if len(self.failures_first) < _FAILURES_KEPT:
                self.failures_first.append(message)

    def observe(self, data: ISL29125) -> None:
        # Per-poll range transitions and per-sample invariants, kept as figures: memory stays flat however long a
        # scenario runs (SPECIFICATION.md Part I).
        if data.RangeAct is not None:
            if self.last_range is not None and data.RangeAct != self.last_range:
                self.switches += 1
                self.total_switches += 1
            self.last_range = data.RangeAct
            if data.RangeAct not in self.ranges_used:
                self.ranges_used.append(data.RangeAct)
        if data.Lux is None or data is self.last_data:
            return
        self.last_data = data
        self.samples += 1
        now = time.ticks_ms()
        self.max_gap_ms = max(self.max_gap_ms, time.ticks_diff(now, self.last_sample_ms))
        self.last_sample_ms = now
        self.lux_min = min(self.lux_min, data.Lux)
        self.lux_max = max(self.lux_max, data.Lux)
        label = f"{self.label}@rgb{self.rgb}"
        self.check(data.Lux >= 0.0, f"{label}: Lux={data.Lux!r} is negative")
        self.check(data.RangeAct in (375, 10000), f"{label}: RangeAct={data.RangeAct!r} is neither real range")
        for name, value in (("Red", data.Red), ("Green", data.Green), ("Blue", data.Blue), ("Bri", data.Bri), ("Sat", data.Sat)):
            self.check(value is not None and 0.0 <= value <= 1.0, f"{label}: {name}={value!r} outside the normalised 0-1 domain")
        self.check(data.Hue is not None and 0.0 <= data.Hue < 360.0, f"{label}: Hue={data.Hue!r} outside [0, 360)")
        if data.Red is not None and data.Green is not None and data.Blue is not None and data.Bri is not None:
            peak = max(data.Red, data.Green, data.Blue)
            self.check(abs(data.Bri - peak) <= 1e-6, f"{label}: Bri={data.Bri!r} != max(R,G,B)={peak!r}")

    def reset_scenario(self, label: str) -> None:
        self.label = label
        self.samples = 0
        self.switches = 0
        self.ranges_used = []
        self.max_gap_ms = 0
        self.lux_min, self.lux_max = 1e9, -1.0
        self.last_sample_ms = time.ticks_ms()

    def write(self, rgb: "tuple[int, int, int]") -> None:
        self.rgb = rgb
        self._pixel[0] = rgb
        self._pixel.write()


def _lerp(start: "tuple[int, int, int]", end: "tuple[int, int, int]", frac: float) -> "tuple[int, int, int]":
    return (
        int(start[0] + (end[0] - start[0]) * frac),
        int(start[1] + (end[1] - start[1]) * frac),
        int(start[2] + (end[2] - start[2]) * frac),
    )


async def _park(rig: Rig, rgb: "tuple[int, int, int]") -> bool:
    # The entry range before a scenario starts counting; False if it never settled on one. Not rig.observe(): a switch
    # made getting into position is not the scenario's own and must not land in its switch budget.
    rig.write(rgb)
    last: int | None = None
    seen: object = None
    run = 0
    deadline = time.ticks_add(time.ticks_ms(), int(_PARK_TIMEOUT_S * 1000))
    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        data = await rig.reader.get_data()
        if data.RangeAct is not None and data is not seen:
            seen = data
            run = run + 1 if data.RangeAct == last else 1
            last = data.RangeAct
            if run >= _PARK_STABLE_SAMPLES:
                rig.last_data, rig.last_range = data, data.RangeAct  # observe() starts from here
                return True
        await fed_sleep_ms(rig.wdt, _SAMPLE_MS)
    return False


async def _run_scenario(rig: Rig, spec: "tuple[str, tuple[int, int, int], list[tuple[str, tuple[int, int, int], tuple[int, int, int], float]], int, int, bool]") -> "dict[str, object]":
    # One scenario from a range it chose (inside the band either range is stable), its figures and its own log.
    name, entry, segments, min_switches, max_switches, both_ranges = spec
    parked = await _park(rig, entry)
    rig.reset_scenario(name)
    await rig.reader.reset_error_counter()
    await _drive(rig, segments)
    return {
        "parked": parked, "samples": rig.samples, "switches": rig.switches, "min_switches": min_switches, "max_switches": max_switches,
        "both_ranges": both_ranges, "ranges_used": rig.ranges_used, "lux": [rig.lux_min, rig.lux_max], "max_gap_ms": rig.max_gap_ms,
        "log": log_record(await rig.reader.get_error_counter(), rig.reader.name),
    }


def _scenarios() -> "list[tuple[str, tuple[int, int, int], list[tuple[str, tuple[int, int, int], tuple[int, int, int], float]], int, int, bool]]":
    # Rows: name, entry_light, segments, min_switches, max_switches, must_use_both_ranges; entry_light
    # is parked and settled BEFORE counting, so a budget measures only its own program. Levels come
    # from the rig's MEASURED hysteresis band - tests_hardware/README.md has the table and holds.
    dark, below, inside, full = (0, 0, 0), 1, 5, 255
    lo, hi, sh = _BAND_BELOW, _BAND_ABOVE, _SWITCH_HOLD_S
    return [
        # Slow, sunrise-like. Starting range comes from the declared entry light, not from a dark
        # pre-roll segment inside the program: an inherited range is how the first version of this
        # file passed while proving nothing, and _park() now rules that out for every scenario.
        ("sunrise_white_slow", dark, [
            ("ramp", dark, (full, full, full), 55.0),
        ], 1, 4, True),
        ("sunset_white_slow", (full, full, full), [
            ("hold", (full, full, full), (full, full, full), 5.0),
            ("ramp", (full, full, full), dark, 55.0), ("hold", dark, dark, sh),
        ], 1, 4, True),
        # Medium, dimmer-like, non-zero start and end, paused mid-way, warm mixture.
        ("dimmer_warm_mid", dark, [
            ("ramp", dark, (60, 26, 0), 14.0),
            ("hold", (60, 26, 0), (60, 26, 0), 5.0), ("ramp", (60, 26, 0), (2, 1, 0), 14.0),
            ("hold", (2, 1, 0), (2, 1, 0), sh), ("ramp", (2, 1, 0), (120, 52, 0), 14.0),
        ], 2, 6, True),
        # Fast, bulb-turn-on-like, with holds long enough at both ends for the decision to land.
        ("bulb_fast_on_off", dark, [
            ("ramp", dark, (full, full, full), 1.0),
            ("hold", (full, full, full), (full, full, full), sh),
            ("ramp", (full, full, full), dark, 1.0), ("hold", dark, dark, sh),
            ("ramp", dark, (30, 30, 30), 1.5), ("hold", (30, 30, 30), (30, 30, 30), 6.0),
        ], 2, 8, True),
        # Instantaneous steps, flash-like, between arbitrary levels and pure colours.
        ("flash_steps", dark, [
            ("step", dark, (full, full, full), sh),
            ("step", dark, (below, below, below), sh), ("step", dark, (full, 0, 0), 6.0),
            ("step", dark, (0, 0, full), 6.0), ("step", dark, (inside, inside, inside), 6.0),
        ], 2, 10, True),
        # Oscillation that genuinely crosses BOTH edges of the band - this is the chatter test.
        ("threshold_oscillation_crossing", dark, [
            ("hold", (lo, lo, lo), (lo, lo, lo), sh), ("step", dark, (hi, hi, hi), sh),
            ("step", dark, (lo, lo, lo), sh), ("step", dark, (hi, hi, hi), sh),
            ("step", dark, (lo, lo, lo), sh), ("step", dark, (hi, hi, hi), sh),
        ], 4, 12, True),
        # The complement, and the more important half: light that moves a lot but stays INSIDE the
        # band must produce NO switch at all. This is what hysteresis is for.
        ("hysteresis_band_dwell_no_chatter", dark, [
            ("hold", (inside, inside, inside), (inside, inside, inside), 6.0),
            ("step", dark, (4, 4, 4), 5.0), ("step", dark, (6, 6, 6), 5.0),
            ("step", dark, (3, 3, 3), 5.0), ("step", dark, (6, 6, 6), 5.0),
            ("ramp", (3, 3, 3), (6, 6, 6), 8.0), ("ramp", (6, 6, 6), (3, 3, 3), 8.0),
        ], 0, 0, False),
        # A constant "ambient" channel with a moving "dynamic" one on top of it.
        ("ambient_blue_plus_dynamic_red", dark, [
            ("hold", (0, 0, 10), (0, 0, 10), 6.0), ("ramp", (0, 0, 10), (150, 0, 10), 18.0),
            ("hold", (150, 0, 10), (150, 0, 10), 6.0), ("ramp", (150, 0, 10), (0, 0, 10), 18.0),
        ], 0, 6, False),
        # Single colours and two-colour mixtures at one commanded level.
        ("colour_walk_constant_level", dark, [
            ("step", dark, (60, 0, 0), 5.0), ("step", dark, (0, 60, 0), 5.0),
            ("step", dark, (0, 0, 60), 5.0), ("step", dark, (60, 60, 0), 5.0),
            ("step", dark, (0, 60, 60), 5.0), ("step", dark, (60, 0, 60), 5.0),
            ("step", dark, (60, 60, 60), 5.0),
        ], 0, 8, False),
        # Mixed mode: every shape, overlapping sub-ranges, never returning to zero mid-scenario.
        ("mixed_mode_overlapping", dark, [
            ("step", dark, (3, 3, 3), 5.0),
            ("ramp", (3, 3, 3), (25, 10, 40), 10.0), ("hold", (25, 10, 40), (25, 10, 40), 5.0),
            ("step", dark, (200, 200, 60), 6.0), ("ramp", (200, 200, 60), (8, 30, 8), 12.0),
            ("hold", (8, 30, 8), (8, 30, 8), 5.0), ("ramp", (8, 30, 8), (140, 140, 140), 9.0),
            ("step", dark, (below, below, below), sh),
        ], 2, 10, True),
    ]


async def _settled(rig: Rig, rgb: "tuple[int, int, int]") -> "float | None":
    # Parks at one colour, waits out the settle, and returns the lux of the first sample stored after it.
    rig.write(rgb)
    begin = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), begin) < int(_SETTLE_S * 1000):
        rig.observe(await rig.reader.get_data())
        await fed_sleep_ms(rig.wdt, _SAMPLE_MS)
    stale = await rig.reader.get_data()
    begin = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), begin) < int(_MAX_SAMPLE_GAP_S * 1000):
        data = await rig.reader.get_data()
        lux: float | None = data.Lux
        if data is not stale and lux is not None:
            return lux
        await fed_sleep_ms(rig.wdt, _SAMPLE_MS)
    return None


async def _main() -> None:
    wdt = arm()
    chip = BENCH["instances"]["isl29125"]
    bus = BENCH["bus"][chip["bus"]]
    i2c = asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"], frequency=bus["frequency"], timeout=bus.get("timeout"))
    reader = ISL29125_Reader(i2c, chip["irq_pin"], max_module_error=999)
    reader.cfgmgr.valid = True
    # Seeded from the driver's own schema (command-only fields have no default), never a hand-copied list.
    reader.cfgmgr._cache = {field[0]: field[2] for field in reader.get_cfg_schema() if field[2] is not None}
    reader.cfgmgr._cache["AutoRangeDwell"] = 0.0  # no switch-down suppression: the scenarios drive the range loop on purpose
    pixel = NeoPixel(Pin(BENCH["instances"]["neopixel"]["pin"], Pin.OUT), n=1)
    try:
        reader.start_timer()
        tasks = [reader.start_asy_trigger(), reader.start_asy_read()]
        rig = Rig(pixel, reader, wdt)
        rig.write((0, 0, 0))
        await fed_sleep_ms(wdt, _SAMPLE_MS)
        # The baseline after every scenario: identical light must still read the same (a wedged range or stuck state).
        baselines = [await _settled(rig, (_BASELINE_LEVEL, _BASELINE_LEVEL, _BASELINE_LEVEL))]
        span = [1e9, -1.0]
        for spec in _scenarios():
            figures = await _run_scenario(rig, spec)
            fact("scenario_" + spec[0], figures)
            span = [min(span[0], rig.lux_min), max(span[1], rig.lux_max)]
            baselines.append(await _settled(rig, (_BASELINE_LEVEL, _BASELINE_LEVEL, _BASELINE_LEVEL)))
        fact("baselines", baselines)
        fact("span", span)
        fact("total_switches", rig.total_switches)
        errors("sample_failures", rig.failures_total, rig.failures_first)
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
        fact("bounds", {"min_samples": _MIN_SAMPLES, "max_sample_gap_ms": int(_MAX_SAMPLE_GAP_S * 1000), "baseline_tol": _BASELINE_TOL, "min_span_ratio": _MIN_SPAN_RATIO, "periodic_only_warn_at": _PERIODIC_ONLY_WARN_AT, "periodic_only": W_ISL_PERIODIC_ONLY})
    finally:
        pixel[0] = (0, 0, 0)
        pixel.write()
    done()


asyncio.run(_main())
