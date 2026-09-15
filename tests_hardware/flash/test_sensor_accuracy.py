"""Flash-tier automated tests: real SCD30/BMP3xx/SGP40/ISL29125 (incl. VOC algorithm) reading
plausibility (sane datasheet bounds, not exact-reference calibration - see
tests_hardware/manual/manual_sensor_accuracy.py for the reference-calibrated variant)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import isl29125_conformance

if TYPE_CHECKING:
    from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def test_scd30_real_reading_is_within_datasheet_plausible_bounds(board: Board) -> None:
    # ~60s real runtime (45s post-reset settle + up to 15s final poll - see the device script's own
    # docstring); timeout is generous relative to that.
    output = board.run_isolated(DEVICE_SCRIPTS / "scd30_plausibility_read.py", timeout_s=100.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"SCD30 plausibility check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_bmp3xx_real_reading_is_within_datasheet_plausible_bounds(board: Board) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "bmp3xx_plausibility_read.py", timeout_s=60.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"BMP3xx plausibility check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_sgp40_voc_algorithm_produces_plausible_and_stable_results(board: Board) -> None:
    # ~90s real runtime (45s documented algorithm blackout + a sampling window) - see the device
    # script's own docstring; timeout is generous relative to that.
    output = board.run_isolated(DEVICE_SCRIPTS / "sgp40_voc_algorithm_quality.py", timeout_s=150.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"SGP40/VOC algorithm quality check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_isl29125_real_reading_is_within_datasheet_plausible_bounds(board: Board) -> None:
    # dev-only sensor (i2c1); ~15s worst-case wait window - see the device script's own docstring.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_plausibility_read.py", timeout_s=30.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"ISL29125 plausibility check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration(board: Board) -> None:
    # Drives the board's own NeoPixel through 8 steady levels each way (16 holds) plus 6 more holds
    # in _config_mechanisms() - 22 holds x SETTLE_S=4.5s is ~99s of guaranteed settle alone, plus up
    # to MAX_WAIT_S=12s per hold for a fresh sample worst-case; timeout is generous relative to that.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_mechanism_envelope.py", timeout_s=420.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"ISL29125 mechanism envelope check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_isl29125_survives_recombined_realistic_lighting_scenarios(board: Board) -> None:
    # Ten recombined lighting scenarios (colours, mixtures, slow/medium/fast slopes, steps, holds,
    # threshold oscillation) driven through the board's own NeoPixel - real segment durations alone
    # sum to ~8.5 minutes (see the device script's own _scenarios() table), plus per-scenario
    # baseline settles; this is a genuinely long real-hardware run, not a routine-pass-speed one.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_lighting_scenarios.py", timeout_s=900.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"ISL29125 lighting-scenarios check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_isl29125_register_probe_matches_the_digital_twins_fake_chip(board: Board) -> None:
    # Runs device_scripts/isl29125_mock_conformance_probe.py IDENTICALLY against the real chip
    # (here) and against digital_twin/_isl29125_chip.py under the MicroPython Unix port
    # (isl29125_conformance.run_probe_against_twin(), which needs that port already built - see
    # tests_hardware/README.md's prerequisites), then diffs every protocol-level KEY=VALUE pair -
    # illumination-dependent keys are excluded via PHYSICAL_KEYS, not compared as absolute values.
    real_output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_mock_conformance_probe.py", timeout_s=120.0)
    real = isl29125_conformance.parse(real_output)
    assert real.get("DONE") == "1", f"the real-hardware probe did not run to completion - full output:\n{real_output}"
    twin = isl29125_conformance.run_probe_against_twin()
    divergences = isl29125_conformance.compare(real, twin)
    assert not divergences, "the digital twin's ISL29125 fake diverges from the real chip:\n" + "\n".join(divergences)
