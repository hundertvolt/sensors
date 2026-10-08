"""Flash-tier automated tests: real SCD30/BMP3xx/SGP40/ISL29125 (incl. VOC algorithm) reading
plausibility (sane datasheet bounds, not exact-reference calibration - see
tests_hardware/manual/manual_sensor_accuracy.py for the reference-calibrated variant)."""

import re
from pathlib import Path
from typing import TYPE_CHECKING

import isl29125_conformance
import pytest

if TYPE_CHECKING:
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("scd30", "sgp40", "bmp3xx", "isl29125", "isl29125_autorange")

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


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
# @tunable l3.sensor_accuracy_conformance_script_timeout_s = 120.0
_CONFORMANCE_SCRIPT_TIMEOUT_S = 120.0
# The script's fixed 600 s window plus the boot it runs first.
# @tunable l3.sensor_accuracy_sgp40_cadence_script_timeout_s = 660.0
_SGP40_CADENCE_SCRIPT_TIMEOUT_S = 660.0
CADENCE_RE = re.compile(r"^CADENCE cycles=(\d+) elapsed_ms=(\d+) lost=(-?\d+) max_gap_ms=(\d+) gaps_over_1500=(\d+)", re.MULTILINE)


def test_scd30_real_reading_is_within_datasheet_plausible_bounds(board: "Board") -> None:
    # ~60s real runtime (45s post-reset settle + up to 15s final poll - see the device script's own
    # docstring); timeout is generous relative to that.
    output = board.run_isolated(DEVICE_SCRIPTS / "scd30_plausibility_read.py", timeout_s=_SCD30_SCRIPT_TIMEOUT_S)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"SCD30 plausibility check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_bmp3xx_real_reading_is_within_datasheet_plausible_bounds(board: "Board") -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "bmp3xx_plausibility_read.py", timeout_s=_BMP3XX_SCRIPT_TIMEOUT_S)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"BMP3xx plausibility check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_sgp40_voc_algorithm_produces_plausible_and_stable_results(board: "Board") -> None:
    # ~90s real runtime (45s documented algorithm blackout + a sampling window) - see the device
    # script's own docstring; timeout is generous relative to that.
    output = board.run_isolated(DEVICE_SCRIPTS / "sgp40_voc_algorithm_quality.py", timeout_s=_SGP40_SCRIPT_TIMEOUT_S)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"SGP40/VOC algorithm quality check failed: {match.group(2).strip()}\nfull output:\n{output}"


@pytest.mark.long_soak
def test_sgp40_sample_cadence(board: "Board", request: pytest.FixtureRequest) -> None:
    # Ten minutes of the real dev task graph, read cycles counted: the figures are the deliverable (no pass
    # threshold, SPECIFICATION.md M.3), recorded from the CADENCE line; the window is fixed, whatever the tier.
    if request.config.getoption("--soak-tier") is None:
        pytest.skip("a fixed 600 s run of the whole task graph - run via scripts/run_bench_soak_tests.sh --tier short")
    output = board.run_isolated(DEVICE_SCRIPTS / "sgp40_sample_cadence.py", timeout_s=_SGP40_CADENCE_SCRIPT_TIMEOUT_S)
    match = CADENCE_RE.search(output)
    assert match is not None, f"device script printed no CADENCE line - full output:\n{output}"
    assert int(match.group(1)) > 0, f"no SGP40 read cycle in the window - full output:\n{output}"
    print(match.group(0))


def test_isl29125_real_reading_is_within_datasheet_plausible_bounds(board: "Board") -> None:
    # dev-only sensor (i2c1); ~15s worst-case wait window - see the device script's own docstring.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_plausibility_read.py", timeout_s=_ISL29125_SCRIPT_TIMEOUT_S)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"ISL29125 plausibility check failed: {match.group(2).strip()}\nfull output:\n{output}"


@pytest.mark.neopixel_sweep
def test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration(board: "Board", request: pytest.FixtureRequest) -> None:
    if not request.config.getoption("--allow-neopixel-sweep"):
        pytest.skip("needs the NeoPixel-aimed-at-the-ISL29125 rig physically set up - pass --allow-neopixel-sweep once it is (tests_hardware/README.md's rig section, recorded by the manual tier)")
    # Drives the board's own NeoPixel through 8 steady levels each way (16 holds) plus 6 more holds
    # in _config_mechanisms() - 22 holds x SETTLE_S=4.5s is ~99s of guaranteed settle alone, plus up
    # to MAX_WAIT_S=12s per hold for a fresh sample worst-case; timeout is generous relative to that.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_mechanism_envelope.py", timeout_s=_ENVELOPE_SCRIPT_TIMEOUT_S)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"ISL29125 mechanism envelope check failed: {match.group(2).strip()}\nfull output:\n{output}"


@pytest.mark.neopixel_sweep
def test_isl29125_survives_recombined_realistic_lighting_scenarios(board: "Board", request: pytest.FixtureRequest) -> None:
    if not request.config.getoption("--allow-neopixel-sweep"):
        pytest.skip("needs the NeoPixel-aimed-at-the-ISL29125 rig physically set up - pass --allow-neopixel-sweep once it is (tests_hardware/README.md's rig section, recorded by the manual tier)")
    # Ten recombined lighting scenarios driven through the board's own NeoPixel. The device
    # script's _scenarios() table sums to ~8.5 minutes of real segment time before per-scenario
    # baseline settles, so this is a deliberately long run, not a routine-speed one.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_lighting_scenarios.py", timeout_s=_SCENARIOS_SCRIPT_TIMEOUT_S)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"ISL29125 lighting-scenarios check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_isl29125_register_probe_matches_the_digital_twins_fake_chip(board: "Board") -> None:
    # Runs isl29125_mock_conformance_probe.py identically against the real chip and against the
    # twin's fake under the Unix port (run_probe_against_twin(), which needs that port built),
    # then diffs every protocol KEY=VALUE pair. PHYSICAL_KEYS excludes the light-dependent ones.
    real_output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_mock_conformance_probe.py", timeout_s=_CONFORMANCE_SCRIPT_TIMEOUT_S)
    real = isl29125_conformance.parse(real_output)
    assert real.get("DONE") == "1", f"the real-hardware probe did not run to completion - full output:\n{real_output}"
    twin = isl29125_conformance.run_probe_against_twin()
    divergences = isl29125_conformance.compare(real, twin)
    assert not divergences, "the digital twin's ISL29125 fake diverges from the real chip:\n" + "\n".join(divergences)
