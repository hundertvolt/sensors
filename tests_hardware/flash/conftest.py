"""Flash-tier-local fixtures: the SCD30 NVM-write-budget guard for the bus-hazard test group - the
SCD30's on-chip NVM has a real write-wear budget, so this test group writes it at most once per
pytest session."""

from __future__ import annotations

from pathlib import Path

import pytest
from harness import Board

_DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"


@pytest.fixture(scope="session")
def scd30_continuous_measurement_triggered(board: Board) -> None:
    """Runs scd30_same_device_rw_concurrency.py once per pytest session - the one real NVM-persisted
    SCD30 write (set_ambient_pressure(), doubling as "trigger continuous measurement") this test
    group issues. Session-scoped so every other dependent reuses it instead of repeating the write."""
    output = board.run_isolated(_DEVICE_SCRIPTS / "scd30_same_device_rw_concurrency.py", timeout_s=90.0)
    assert "RESULT: PASS" in output, f"failed to trigger SCD30 continuous measurement (the one real NVM write this test group makes):\n{output}"
