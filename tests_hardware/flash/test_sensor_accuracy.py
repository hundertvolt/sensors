"""Flash-tier automated tests: real SCD30/BMP3xx/SGP40/ISL29125 (incl. VOC algorithm) reading
plausibility (sane datasheet bounds, not exact-reference calibration - see
tests_hardware/manual/manual_sensor_accuracy.py for the reference-calibrated variant), plus the
ISL29125 mock-conformance diff that keeps the digital twin honest against the real part."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import isl29125_conformance
import pytest

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
    # Needs a lit bench: the device script fails on a reading below its own room-light floor
    # rather than silently passing in the dark (a covered sensor reads a legitimate ~0 lx).
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_plausibility_read.py", timeout_s=60.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"ISL29125 plausibility check failed: {match.group(2).strip()}\nfull output:\n{output}"


def test_the_isl29125_mock_answers_the_bus_exactly_as_the_real_chip_does(board: Board) -> None:
    """The twin's chip fake is only worth trusting while it still matches real silicon.

    Runs one register-level probe against the real part and the identical probe against
    digital_twin/_isl29125_chip.py, then diffs every protocol key. Illumination-dependent keys are
    excluded by value and covered through the probe's own derived yes/no keys instead.
    """
    real = isl29125_conformance.parse(
        board.run_isolated(DEVICE_SCRIPTS / "isl29125_mock_conformance_probe.py", timeout_s=180.0),
    )
    assert real.get("DONE") == "1", f"the probe did not run to completion on real hardware: {real!r}"
    twin = isl29125_conformance.run_probe_against_twin()
    divergences = isl29125_conformance.compare(real, twin)
    assert not divergences, "the ISL29125 mock no longer matches the real chip:\n  " + "\n  ".join(divergences)


@pytest.mark.neopixel_sweep
def test_isl29125_survives_recombined_realistic_lighting_scenarios(board: Board, request: pytest.FixtureRequest) -> None:
    """Ten recombined lighting scenarios - the module's resilience proof, not a calibration test.

    Colours and mixtures, slopes from sunrise-slow to flash-instant, rising and falling, arbitrary
    start and end levels, pauses, an oscillation crossing both hysteresis-band edges and a dwell
    staying inside it, and a constant "ambient" channel under a moving one. Every scenario asserts
    a MINIMUM engagement as well as a ceiling, so none can pass without exercising what it targets
    (see tests_hardware/README.md - an earlier version did exactly that).
    """
    # Same physical prerequisite as the envelope and the sweep - the LED must reach the sensor.
    if not request.config.getoption("--allow-neopixel-sweep"):
        pytest.skip("needs the NeoPixel-aimed-at-the-sensor rig physically set up - pass --allow-neopixel-sweep once it is (tests_hardware/README.md)")

    # ~9 minutes of real light programs; the timeout is generous relative to that.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_lighting_scenarios.py", timeout_s=900.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"ISL29125 lighting scenarios failed: {match.group(2).strip()}\nfull output:\n{output}"


@pytest.mark.neopixel_sweep
def test_isl29125_mechanisms_hold_across_the_whole_illumination_envelope(board: Board, request: pytest.FixtureRequest) -> None:
    """Every mechanism the module has, driven across the light range the board's own LED can make.

    Ascending and descending steady levels from ambient to hard saturation, asserting only
    structural and relative properties - never absolute lux. Covers: a live read chain at every
    level, HSB/RGB coherence, monotonic response, both ranges used, hysteresis without chatter,
    the return to the low range, fixed-range pinning, 12-bit vs 16-bit agreement on one scene,
    ISLResetCal, the saturation detector firing at full white (W14), the interrupt actually
    carrying the range decisions rather than the periodic fallback (no W15), and no errors at all.
    """
    # Same physical prerequisite as the sweep below - the LED has to actually reach the sensor.
    if not request.config.getoption("--allow-neopixel-sweep"):
        pytest.skip("needs the NeoPixel-aimed-at-the-sensor rig physically set up - pass --allow-neopixel-sweep once it is (tests_hardware/README.md)")

    # ~18 steady holds at 4.5s each plus settling; the timeout is generous relative to that.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_mechanism_envelope.py", timeout_s=300.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"ISL29125 mechanism envelope failed: {match.group(2).strip()}\nfull output:\n{output}"


@pytest.mark.neopixel_sweep
def test_isl29125_autorange_sweep_driven_by_the_boards_own_neopixel(board: Board, request: pytest.FixtureRequest) -> None:
    # Gated because it needs physical geometry, not because it is slow or destructive: the board's
    # own WS2812 has to actually illuminate the sensor, through both ranges and across the switch
    # point, with ambient light excluded. A routine bench run cannot assume that rig is set up, and
    # a run without it fails for a reason that has nothing to do with the driver.
    if not request.config.getoption("--allow-neopixel-sweep"):
        pytest.skip("needs the NeoPixel-aimed-at-the-sensor rig physically set up - pass --allow-neopixel-sweep once it is (tests_hardware/README.md)")

    # Three 24s ramps plus settling; the timeout is generous relative to that.
    output = board.run_isolated(DEVICE_SCRIPTS / "isl29125_autorange_sweep.py", timeout_s=180.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"ISL29125 auto-range sweep failed: {match.group(2).strip()}\nfull output:\n{output}"
