"""Flash-tier-local fixtures. Currently just the SCD30 NVM-write-budget guard for the bus-hazard
test group - see scd30_same_device_rw_concurrency.py's own docstring for the real-hardware
constraint this exists to satisfy (project owner's explicit direction: the SCD30's own on-chip NVM
has a real write-wear budget, so this whole test group must never write it more than once per
pytest session)."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness import Board

_DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"


@pytest.fixture(scope="session")
def scd30_continuous_measurement_triggered(board: Board) -> None:
    """Runs scd30_same_device_rw_concurrency.py exactly once per pytest session - the one and only
    real NVM-persisted SCD30 write (set_ambient_pressure(), which doubles as "trigger continuous
    measurement") this whole bus-hazard test group ever issues. Continuous measurement, once
    triggered, is real on-chip NVM state that survives every subsequent separate `mpremote run`
    invocation for the rest of this session - every other flash-tier script that needs SCD30
    producing real fresh data depends on this fixture instead of triggering it again itself.

    Session-scoped (not function-scoped): pytest evaluates a fixture's dependents in an order that
    still only calls this fixture's own body once per session, no matter how many test functions
    across however many files declare a dependency on it - this is what keeps the real write count
    at exactly one regardless of how this test group grows over time."""
    output = board.run_isolated(_DEVICE_SCRIPTS / "scd30_same_device_rw_concurrency.py", timeout_s=90.0)
    assert "RESULT: PASS" in output, f"failed to trigger SCD30 continuous measurement (the one real NVM write this test group makes):\n{output}"
