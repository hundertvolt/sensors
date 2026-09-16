"""Flash-tier-local fixtures: the SCD30 NVM-write-budget guard for the bus-hazard test group - the
SCD30's on-chip NVM has a real write-wear budget, so this test group writes it at most once per
pytest session, and only when --allow-scd30-writes is passed (see tests_hardware/conftest.py)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from harness import Board

_DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"


@pytest.fixture(scope="session")
def scd30_continuous_measurement_triggered(board: Board, request: pytest.FixtureRequest) -> None:
    """Runs scd30_same_device_rw_concurrency.py once per pytest session - the one real NVM-persisted
    SCD30 write (set_ambient_pressure(), doubling as "trigger continuous measurement") this test
    group issues. Session-scoped so every other dependent reuses it instead of repeating the write."""
    if not request.config.getoption("--allow-scd30-writes"):
        # Every real dependent test must carry @pytest.mark.scd30_write, which
        # tests_hardware/conftest.py's pytest_collection_modifyitems() deselects before this fixture
        # could ever run without the flag - reaching here means a test forgot the marker, not that
        # real hardware did anything wrong. Fails loudly rather than silently spending the write.
        raise RuntimeError(
            "scd30_continuous_measurement_triggered was invoked without --allow-scd30-writes - the "
            "requesting test is missing @pytest.mark.scd30_write, so it wasn't deselected by "
            "tests_hardware/conftest.py's pytest_collection_modifyitems() as it should have been.",
        )
    output = board.run_isolated(_DEVICE_SCRIPTS / "scd30_same_device_rw_concurrency.py", timeout_s=90.0)
    assert "RESULT: PASS" in output, f"failed to trigger SCD30 continuous measurement (the one real NVM write this test group makes):\n{output}"
