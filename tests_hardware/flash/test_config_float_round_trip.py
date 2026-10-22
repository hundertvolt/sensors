"""Flash-tier: every float config field's stored form is idempotent on the board's single-precision floats, and a
repeat write after a reload from flash answers "Unchanged" (SPECIFICATION.md C.5). The float fields reach the device
script through the rendered bench facts, read from the src/ schemas, never copied by hand."""

from typing import TYPE_CHECKING

import pytest
from harness import DEVICE_SCRIPTS_DIR, parse_facts

if TYPE_CHECKING:
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_2_reboot_settings_persistence",)

# @tunable l3.config_float_round_trip_script_timeout_s = 60.0
_SCRIPT_TIMEOUT_S = 60.0


@pytest.mark.persistence_write
def test_config_floats_round_trip_unchanged(board: "Board") -> None:
    facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "config_float_round_trip.py", timeout_s=_SCRIPT_TIMEOUT_S))
    fields = facts.get("fields")
    assert isinstance(fields, int) and fields > 0, f"no float field reached the script: {facts}"
    assert "leftover_remove_errno" not in facts and "remove_errno" not in facts, f"the scratch file could not be removed: {facts}"
    bad = facts.get("non_idempotent")
    assert isinstance(bad, dict) and bad.get("total") == 0, f"stored forms not idempotent on the board's floats: {bad}"
    owned = facts.get("owned_write")
    assert isinstance(owned, dict) and owned.get("ok") is True and owned.get("validity") == "Valid", f"the owned write was not accepted as Valid: {owned}"
    assert facts.get("reloaded") is True, f"the manager rebuilt from the file did not set up: {facts}"
    assert facts.get("repeat_validity") == "Unchanged", f"the repeat write after the reload answered {facts.get('repeat_validity')}, not Unchanged: {facts}"
