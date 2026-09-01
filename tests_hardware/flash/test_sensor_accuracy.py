"""Flash-tier automated test, Part 1 category F (tmp_hardware_test_candidates.md item 21): real
SCD30 CO2/temperature/humidity plausibility (sane bounds, not exact-reference calibration - see
tests_hardware/manual/manual_sensor_accuracy.py's item 9/10 for the reference-calibrated
variant that needs a human-supplied known-good reading)."""

from __future__ import annotations

import re
from pathlib import Path

from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def test_scd30_real_reading_is_within_datasheet_plausible_bounds(board: Board) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / "scd30_plausibility_read.py", timeout_s=60.0)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"SCD30 plausibility check failed: {match.group(2).strip()}\nfull output:\n{output}"
