"""Flash-tier tests: real SCD30/BMP3xx/SGP40/ISL29125 readings (the VOC algorithm included) against plausibility bounds,
not a reference calibration (tests_hardware/manual/manual_sensor_accuracy.py is that), plus the ISL29125 envelope and
lighting scenarios, the SGP40 cadence soak and the SCD30's float32 FRC window. Scripts report facts; tests decide."""

import math
from itertools import pairwise
from typing import Protocol

import pytest
from harness import DEVICE_SCRIPTS_DIR, Board, parse_facts
from plausibility_bounds import BOUNDS


class _ResultNote(Protocol):
    # The root conftest's result_note fixture.
    def __call__(self, text: str, *, recovery: bool = False) -> None: ...


COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("scd30", "sgp40", "bmp3xx", "isl29125", "isl29125_autorange")

# @tunable l3.sensor_accuracy_scd30_script_timeout_s = 100.0
_SCD30_SCRIPT_TIMEOUT_S = 100.0
# @tunable l3.sensor_accuracy_bmp3xx_script_timeout_s = 60.0
_BMP3XX_SCRIPT_TIMEOUT_S = 60.0
# @tunable l3.sensor_accuracy_sgp40_script_timeout_s = 150.0
_SGP40_SCRIPT_TIMEOUT_S = 150.0
# @tunable l3.sensor_accuracy_isl29125_script_timeout_s = 30.0
_ISL29125_SCRIPT_TIMEOUT_S = 30.0
# @tunable l3.sensor_accuracy_envelope_script_timeout_s = 420.0
_ENVELOPE_SCRIPT_TIMEOUT_S = 420.0
# @tunable l3.sensor_accuracy_scenarios_script_timeout_s = 900.0
_SCENARIOS_SCRIPT_TIMEOUT_S = 900.0
# The script's fixed 600 s window plus the boot it runs first.
# @tunable l3.sensor_accuracy_sgp40_cadence_script_timeout_s = 660.0
_SGP40_CADENCE_SCRIPT_TIMEOUT_S = 660.0
_RANGES = (375, 10000)  # the ISL29125's two full scales, FN8424 p.10 Table 5
_CCT_SPAN_K = (2000.0, 12500.0)  # source: McCamy (1992)'s usable span, the formula the driver's CCT uses
_FRC_SCRIPT = "scd30_plausibility_read.py"
_FRC_MODE = "frc_window"
# The window's figures from the float32 sums may differ from the double-precision ones by at most this, relative.
# @tunable l3.sensor_accuracy_frc_sum_rel_max = 0.001
_FRC_SUM_REL_MAX = 0.001


def _dict(value: object) -> "dict[str, object]":
    assert isinstance(value, dict), f"a fact that should be a table: {value!r}"
    return value


def _envelope_problems(facts: "dict[str, object]") -> "list[str]":
    # The envelope's verdicts over its reported samples and setting results, each bound the script's own.
    bounds = _dict(facts["bounds"])
    up, down = facts["up"], facts["down"]
    assert isinstance(up, list) and isinstance(down, list), facts
    found = [f"no sample at level {s}" for s in up + down if s is None]
    samples = [_dict(s) for s in up + down if s is not None]
    found += [p for s in samples for p in _incoherent(s, f"level {s['level']}")]
    rising = [_dict(s) for s in up if s is not None]
    found += [f"level {a['level']}->{b['level']}: lux dropped {a['lux']}->{b['lux']} as the light rose" for a, b in pairwise(rising) if _num(b["lux"]) <= _num(a["lux"]) * _num(bounds["min_step_ratio"])]
    if len(rising) >= 2 and _num(rising[-1]["lux"]) <= _num(rising[0]["lux"]) * _num(bounds["min_span_ratio"]):
        found.append(f"the envelope only spanned {rising[0]['lux']}->{rising[-1]['lux']} lux - the LED never really moved the sensor")
    ranges = [s["range"] for s in samples]
    found += [f"the {r} lx range was never used across the envelope" for r in _RANGES if r not in ranges]
    if not rising or rising[-1]["range"] != _RANGES[1] or not down or down[-1] is None or _dict(down[-1])["range"] != _RANGES[0]:
        found.append("full white did not end on the high range, or ambient did not return to the low one")
    switches = sum(1 for a, b in pairwise(ranges) if a != b)
    if switches > _num(bounds["max_switches"]):
        found.append(f"{switches} range switches across one up-and-down envelope - the hysteresis is chattering")
    return found


def _frc_expected(samples: int, thresholds: "dict[str, object]", interval_s: int) -> "tuple[dict[str, float], int]":
    # The script's synthetic series summed in double precision, and the verdict asy_scd30_driver.py's _frc_close()
    # reaches from those sums (4 ready, 3 noisy, 2 drifting): the reference the float32 sums are held against.
    co2 = [800.0 + (i * 7) % 21 - 10 for i in range(samples)]
    d = [value - co2[0] for value in co2]
    sums = {"d": math.fsum(d), "d2": math.fsum(x * x for x in d), "id": math.fsum(i * x for i, x in enumerate(d))}
    n = float(samples)
    s_i, s_ii = n * (n - 1) / 2, (n - 1) * n * (2 * n - 1) / 6
    sxx, sxy, syy = s_ii - s_i * s_i / n, sums["id"] - s_i * sums["d"] / n, sums["d2"] - sums["d"] ** 2 / n
    rate = abs(sxy / sxx) * 60 / interval_s
    noise = math.sqrt(max(0.0, syy - sxy * sxy / sxx) / (n - 2))
    verdict = 2 if rate > _num(thresholds["rate"]) else 3 if noise > _num(thresholds["noise"]) else 4
    return sums, verdict


def _incoherent(sample: "dict[str, object]", label: str) -> "list[str]":
    # An ISL29125 sample's normalised RGB/HSB and range: in their domains, and Bri equal to max(R, G, B) by construction.
    rgb, hsb = sample["rgb"], sample["hsb"]
    assert isinstance(rgb, list) and isinstance(hsb, list), sample
    found = [f"{label}: {name}={value!r} outside 0-1" for name, value in zip(("Red", "Green", "Blue", "Sat", "Bri"), [*rgb, *hsb[1:]], strict=True) if not (isinstance(value, float | int) and 0.0 <= value <= 1.0)]
    hue = hsb[0]
    if not (isinstance(hue, float | int) and 0.0 <= hue < 360.0):
        found.append(f"{label}: Hue={hue!r} outside [0, 360)")
    if sample["range"] not in _RANGES:
        found.append(f"{label}: RangeAct={sample['range']!r} is neither real range")
    if not found and abs(_num(hsb[2]) - max(_num(c) for c in rgb)) > 1e-6:
        found.append(f"{label}: Bri={hsb[2]!r} != max(R,G,B) of {rgb} - HSB inconsistent with RGB")
    return found


def test_scd30_real_reading_is_within_datasheet_plausible_bounds(board: Board, scd30_measuring: str) -> None:
    # ~60 s on the board: the 45 s post-reset settle and up to 15 s of polling.
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "scd30_plausibility_read.py", timeout_s=_SCD30_SCRIPT_TIMEOUT_S))
    assert facts["died"] == [], f"a reader task died: {facts['died']}"
    assert facts["co2"] is not None, f"no CO2 reading within the wait window after {facts['polls']} polls"
    problems = [p for p in (_within("co2_ppm", facts["co2"]), _within("humidity_rh", facts["humidity"]), _within("scd30_temp_c", facts["temperature"])) if p]
    assert not problems, "; ".join(problems)


def _log_problems(record: object, label: str, periodic_only: object) -> "list[str]":
    # A log with no error entry, no ISL_PERIODIC_ONLY warning, and a history that still holds every entry it counted.
    log = _dict(record)
    entries = log["entries"]
    assert isinstance(entries, list), log
    found = [f"{label}: logged error {entry}" for entry in entries if entry[0] == "E"]
    found += [f"{label}: ISL_PERIODIC_ONLY logged - the interrupt is not carrying the range decisions" for entry in entries if entry == ["W", periodic_only]]
    if len(entries) >= _num(log["slots"]) and _num(log["count"]) > len(entries):
        found.append(f"{label}: {log['count']} log calls past a full {log['slots']}-slot history - entries were lost, so no-error cannot be claimed")
    return found


def test_scd30_frc_window_sums_hold_in_float32(board: Board, result_note: _ResultNote) -> None:
    # The FRC readiness accumulation over FRCWindow's 3600 s maximum, run by the driver in the board's float32; no
    # SCD30 command is sent, so nothing is written.
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / _FRC_SCRIPT, timeout_s=_SCD30_SCRIPT_TIMEOUT_S, mode=_FRC_MODE))
    samples, interval = int(_num(facts["frc_samples"])), int(_num(facts["frc_interval_s"]))
    expected, verdict = _frc_expected(samples, _dict(facts["frc_thresholds"]), interval)
    measured = _dict(facts["frc_sums"])
    errors = {key: abs(_num(measured[key]) - value) / max(abs(value), 1.0) for key, value in expected.items()}
    result_note(f"frc float32 sums {measured} vs double {expected}: relative errors {errors}")
    assert facts["frc_verdict"] == verdict, f"the float32 window reached verdict {facts['frc_verdict']}, the double-precision one {verdict}"
    assert all(error <= _FRC_SUM_REL_MAX for error in errors.values()), f"float32 FRC sums drift past {_FRC_SUM_REL_MAX}: {errors}"


def test_bmp3xx_real_reading_is_within_datasheet_plausible_bounds(board: Board) -> None:
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "bmp3xx_plausibility_read.py", timeout_s=_BMP3XX_SCRIPT_TIMEOUT_S))
    assert facts["died"] == [], f"a reader task died: {facts['died']}"
    assert facts["pressure"] is not None, f"no pressure reading within the wait window after {facts['polls']} polls"
    problems = [p for p in (_within("pressure_hpa", facts["pressure"]), _within("bmp3xx_temp_c", facts["temperature"]), _within("pressure_hpa", facts["sea_level_pressure"])) if p]
    assert not problems, "; ".join(problems)


def test_sgp40_voc_algorithm_produces_plausible_and_stable_results(board: Board) -> None:
    # ~90 s on the board: the algorithm's 45 s blackout and a sampling window.
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "sgp40_voc_algorithm_quality.py", timeout_s=_SGP40_SCRIPT_TIMEOUT_S))
    assert facts["died"] is None, f"the read task died: {facts['died']}"
    samples = facts["samples"]
    assert isinstance(samples, list) and samples and all(isinstance(s, list) and None not in s for s in samples), f"a post-blackout sample had no VOC or raw value: {samples}"
    problems = [p for voc, raw in samples for p in (_within("voc_index", voc), _within("voc_raw_ticks", raw)) if p]
    assert not problems, "; ".join(problems)
    voc = [s[0] for s in samples]
    assert len(set(voc)) > 1, f"all {len(voc)} post-blackout VOC samples were {voc[0]} - the algorithm looks frozen"
    assert _num(facts["max_step_jump"]) <= _num(facts["max_step_jump_bound"]), f"a single-step VOC jump of {facts['max_step_jump']} (bound {facts['max_step_jump_bound']}): {voc}"


@pytest.mark.soak_duration
def test_sgp40_sample_cadence(board: Board, request: pytest.FixtureRequest, result_note: _ResultNote) -> None:
    # Ten minutes of the bench device's task graph over a scratch config, read cycles counted: the figures are the
    # deliverable (no pass threshold, SPECIFICATION.md M.3), and the window is fixed whatever the duration.
    if request.config.getoption("--soak-duration") is None:
        pytest.skip("a fixed 600 s run of the whole task graph - run scripts/run_bench_soak_tests.sh --duration short")
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "sgp40_sample_cadence.py", timeout_s=_SGP40_CADENCE_SCRIPT_TIMEOUT_S))
    assert facts["built"] is True and facts["timers_started"] is True, f"the system did not come up: {facts}"
    result_note(" ".join(f"{key}={facts[key]}" for key in ("cycles", "elapsed_ms", "lost", "max_gap_ms", "gaps_over_1500", "backup_period_min")))
    assert _num(facts["cycles"]) > 0, "no SGP40 read cycle in the window"


def test_isl29125_real_reading_is_within_datasheet_plausible_bounds(board: Board) -> None:
    # The board lights its own scene from the NeoPixel and parks it dark on the way out.
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "isl29125_plausibility_read.py", timeout_s=_ISL29125_SCRIPT_TIMEOUT_S))
    assert facts["died"] == [], f"a reader task died: {facts['died']}"
    assert facts["fresh"] == 2, f"no reading converted after the scene was lit ({facts['fresh']} fresh in {facts['polls']} polls)"
    lux = facts["lux"]
    problems = [p for p in (_within("lux", lux),) if p] + _incoherent({"rgb": facts["rgb"], "hsb": facts["hsb"], "range": facts["range_act"]}, "lit scene")
    assert _num(lux) >= _num(facts["room_light_min_lux"]), f"Lux={lux} below {facts['room_light_min_lux']} with the board lighting itself - a covered or faulty sensor"
    cct = facts["cct"]
    if cct is not None:  # None below the low-light floor; only an out-of-span number is a failure
        assert _CCT_SPAN_K[0] <= _num(cct) <= _CCT_SPAN_K[1], f"CCT={cct} K outside McCamy's span {_CCT_SPAN_K}"
    assert not problems, "; ".join(problems)


def _num(value: object) -> float:
    assert isinstance(value, int | float) and not isinstance(value, bool), f"a fact that should be a number: {value!r}"
    return float(value)


def _scenario_problems(name: str, figures: "dict[str, object]", bounds: "dict[str, object]") -> "list[str]":
    # One scenario against its own declared switch budget and the run's sample bounds.
    found = [] if figures["parked"] is True else [f"{name}: the entry light never settled on one range"]
    switches = _num(figures["switches"])
    if not _num(figures["min_switches"]) <= switches <= _num(figures["max_switches"]):
        found.append(f"{name}: {switches:.0f} range switches, expected {figures['min_switches']}..{figures['max_switches']}")
    if _num(figures["samples"]) < _num(bounds["min_samples"]) or _num(figures["max_gap_ms"]) > _num(bounds["max_sample_gap_ms"]):
        found.append(f"{name}: {figures['samples']} samples, {figures['max_gap_ms']} ms gap - the read chain stalled")
    used = figures["ranges_used"]
    if figures["both_ranges"] is True and not (isinstance(used, list) and len(used) == len(_RANGES)):
        found.append(f"{name}: only range(s) {used} used - the light never crossed the hysteresis band")
    return found + [p for p in _log_problems(figures["log"], name, bounds["periodic_only"]) if "ISL_PERIODIC_ONLY" not in p]


@pytest.mark.neopixel_sweep
@pytest.mark.persistence_write
def test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration(board: Board, request: pytest.FixtureRequest, result_note: _ResultNote) -> None:
    # Seven flash writes to a scratch config file (the range/resolution pushes), removed after.
    if not request.config.getoption("--allow-neopixel-sweep"):
        pytest.skip("needs the NeoPixel-aimed-at-the-ISL29125 rig - pass --allow-neopixel-sweep once it is set up (tests_hardware/README.md's rig section)")
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "isl29125_mechanism_envelope.py", timeout_s=_ENVELOPE_SCRIPT_TIMEOUT_S))
    assert facts["died"] == [], f"a task died: {facts['died']}"
    bounds = _dict(facts["bounds"])
    problems = _envelope_problems(facts)
    if facts["overrange_at_full"] is not True:
        problems.append("Overrange is not set at full white - the saturation detector never fired")
    problems += _log_problems(facts["ascending_log"], "ascending leg", bounds["periodic_only"]) + _log_problems(facts["full_log"], "whole run", bounds["periodic_only"])
    fixed, depth, continuity, calibrate = (_dict(facts[key]) for key in ("fixed_range", "bit_depth", "continuity", "calibrate"))
    pushes = {"fixed": fixed["pinned"], "fixed restore": fixed["restored"], "12-bit": depth["pushed_12"], "16-bit": depth["pushed_16"], "low pin": continuity["pinned_low"], "high pin": continuity["pinned_high"], "continuity restore": continuity["restored"], "Calibrate": calibrate["pushed"]}
    problems += [f"the {name} push was not accepted" for name, ok in pushes.items() if ok is not True]
    problems += [f"fixed range at {where}: {_dict(fixed[where]).get('range')}" for where in ("ambient", "bright") if fixed[where] is None or _dict(fixed[where])["range"] != _RANGES[1]]
    at_12, at_16 = _dict(depth["at_12"]), _dict(depth["at_16"])
    rel = abs(_num(at_12["lux"]) - _num(at_16["lux"])) / _num(at_16["lux"])
    low, high = _dict(continuity["low"]), _dict(continuity["high"])
    step = abs(_num(high["lux"]) - _num(low["lux"])) / _num(low["lux"]) if _num(low["lux"]) > 0 else math.inf
    result_note(f"12 vs 16 bit {rel:.3f}, cross-range step {step:.3f}, measured gain ratio {calibrate['measured_ratio']}")
    if rel >= _num(bounds["bit_depth_rel_max"]):
        problems.append(f"12-bit and 16-bit disagree by {rel * 100:.1f}% on one scene - the 12->16 bit shift looks wrong")
    if (low["range"], high["range"]) != _RANGES or step >= _num(bounds["max_range_step"]):
        problems.append(f"the same light reads {low['lux']} lx on {low['range']} and {high['lux']} lx on {high['range']} ({step * 100:.1f}%) - the range gain correction is not applied")
    if calibrate["calibrating"] is not True or calibrate["applied_after"] != calibrate["applied_before"]:
        problems.append(f"the calibration run did not start, or changed the applied ratio: {calibrate}")
    assert not problems, "; ".join(problems)


def _within(name: str, value: object) -> "str | None":
    # None when `value` lies inside BOUNDS[name], else what is wrong with the bound's source quoted.
    low, high, source = BOUNDS[name]
    return None if isinstance(value, int | float) and low <= value <= high else f"{name}={value!r} outside [{low}, {high}] ({source})"


@pytest.mark.neopixel_sweep
def test_isl29125_survives_recombined_realistic_lighting_scenarios(board: Board, request: pytest.FixtureRequest, result_note: _ResultNote) -> None:
    # Ten recombined scenarios through the board's own NeoPixel, ~8.5 minutes of segments before the baseline settles.
    if not request.config.getoption("--allow-neopixel-sweep"):
        pytest.skip("needs the NeoPixel-aimed-at-the-ISL29125 rig - pass --allow-neopixel-sweep once it is set up (tests_hardware/README.md's rig section)")
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "isl29125_lighting_scenarios.py", timeout_s=_SCENARIOS_SCRIPT_TIMEOUT_S))
    assert facts["died"] == [], f"a task died: {facts['died']}"
    bounds = _dict(facts["bounds"])
    scenarios = {key.removeprefix("scenario_"): _dict(value) for key, value in facts.items() if key.startswith("scenario_")}
    problems = [p for name, figures in scenarios.items() for p in _scenario_problems(name, figures, bounds)]
    # ISL_PERIODIC_ONLY's run of five lives in driver state across scenarios, so it is asserted once per run.
    periodic = [name for name, figures in scenarios.items() if any("ISL_PERIODIC_ONLY" in p for p in _log_problems(figures["log"], name, bounds["periodic_only"]))]
    if periodic:
        problems.append(f"ISL_PERIODIC_ONLY logged during {periodic} - the interrupt is not carrying the range decisions")
    if _num(facts["total_switches"]) < _num(bounds["periodic_only_warn_at"]):
        problems.append(f"only {facts['total_switches']} range switches in the whole run - too few for ISL_PERIODIC_ONLY to be able to fire")
    baselines = facts["baselines"]
    assert isinstance(baselines, list) and baselines and baselines[0] is not None, f"no baseline reference: {baselines}"
    tol = _num(bounds["baseline_tol"])
    problems += [f"baseline {i}: {b} lux vs reference {baselines[0]}" for i, b in enumerate(baselines) if b is None or abs(_num(b) - _num(baselines[0])) / _num(baselines[0]) > tol]
    span = facts["span"]
    assert isinstance(span, list), facts
    if _num(span[1]) <= _num(span[0]) * _num(bounds["min_span_ratio"]):
        problems.append(f"the scenario set only spanned {span[0]}..{span[1]} lux")
    failures = _dict(facts["sample_failures"])
    if failures["total"] != 0:
        problems.append(f"{failures['total']} per-sample invariant failure(s), first: {failures['first']}")
    result_note(f"scenarios={len(scenarios)} span={span} total_switches={facts['total_switches']}")
    assert len(scenarios) >= 1, "no scenario reported"
    assert not problems, "; ".join(problems)
