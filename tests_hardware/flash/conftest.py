"""Flash-tier-local fixtures: the SCD30 NVM-write-budget guard for the bus-hazard test group - the
SCD30's on-chip NVM has a real write-wear budget, so this test group writes it at most once per
pytest session, and only under a write permission covering sensors/SCD30 (see tests_hardware/conftest.py)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from persistence_groups import writes_permitted

if TYPE_CHECKING:
    from harness import Board

_DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
_SCD30_GROUP = "sensors/SCD30"  # the store this fixture's one NVM write lands in


# @tunable l3.conftest_scd30_rw_script_timeout_s = 90.0
_SCD30_RW_SCRIPT_TIMEOUT_S = 90.0


@pytest.fixture(scope="session")
def scd30_continuous_measurement_triggered(board: Board, request: pytest.FixtureRequest) -> None:
    # Runs scd30_same_device_rw_concurrency.py once per pytest session - the one real NVM-persisted
    # SCD30 write (set_ambient_pressure(), doubling as "trigger continuous measurement") this test
    # group issues. Session-scoped so every other dependent reuses it instead of repeating the write.
    if not writes_permitted((_SCD30_GROUP,), request.config):
        # Every dependent test must carry @pytest.mark.persistence_write("sensors/SCD30"), which conftest.py's
        # pytest_collection_modifyitems() deselects before this fixture could run unpermitted. So reaching
        # here means a test forgot the marker or the group: fail loudly rather than spend the write.
        raise RuntimeError(
            f"scd30_continuous_measurement_triggered was invoked without a write permission covering {_SCD30_GROUP} - "
            f"the requesting test is missing @pytest.mark.persistence_write({_SCD30_GROUP!r}), so it wasn't deselected by "
            "tests_hardware/conftest.py's pytest_collection_modifyitems() as it should have been.",
        )
    output = board.run_isolated(_DEVICE_SCRIPTS / "scd30_same_device_rw_concurrency.py", timeout_s=_SCD30_RW_SCRIPT_TIMEOUT_S)
    assert "RESULT: PASS" in output, f"failed to trigger SCD30 continuous measurement (the one real NVM write this test group makes):\n{output}"
