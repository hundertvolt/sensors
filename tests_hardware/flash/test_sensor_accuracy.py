"""Flash-tier automated tests: real SCD30/BMP3xx/SGP40/ISL29125 (incl. VOC algorithm) reading
plausibility (sane datasheet bounds, not exact-reference calibration - see
tests_hardware/manual/manual_sensor_accuracy.py for the reference-calibrated variant)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

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
