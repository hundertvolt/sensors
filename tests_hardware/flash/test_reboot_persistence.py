"""Flash-tier reboot tests: a genuine `hard_reset()` (a raw-REPL `machine.reset()`, a real MCU reset that re-runs the
frozen `main.py`), observed passively so the boot path runs undisturbed."""

from typing import TYPE_CHECKING

import pytest
from harness import DEVICE_SCRIPTS_DIR, boot_lines, crash_lines, parse_facts, wait_for_boot, wait_until

if TYPE_CHECKING:
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_2_reboot_settings_persistence",)

# One exec when the read phase never ran: the test-only file goes, absent or not.
_REMOVE_MARKER_FILE = "import os\ntry:\n  os.remove('config_HWTEST_REBOOT.cfg')\nexcept OSError:\n  pass"
# @tunable l3.reboot_persistence_reachable_timeout_s = 30.0
_REACHABLE_TIMEOUT_S = 30.0
# @tunable l3.reboot_persistence_reachable_poll_s = 1.0
_REACHABLE_POLL_S = 1.0
# @tunable l3.reboot_persistence_boot_log_tail_s = 20.0
_BOOT_LOG_TIMEOUT_S = 20.0


# A config value written through the real ConfigManager survives a genuine reset.
@pytest.mark.persistence_write
def test_config_value_survives_a_genuine_hard_reset(board: "Board") -> None:
    read = False
    try:
        written = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "reboot_persist_write.py"))
        assert written.get("flushed") is True and "leftover_remove_errno" not in written, f"the pre-reboot write did not reach flash: {written}"
        board.hard_reset()
        # The next step enters the raw REPL anyway, so an active reachability poll costs the boot nothing here.
        wait_until(board.is_reachable, timeout_s=_REACHABLE_TIMEOUT_S, poll_interval_s=_REACHABLE_POLL_S, description="board reachable again after hard_reset()")
        read = True
        facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "reboot_persist_read.py"))
        assert facts.get("valid") is True and facts.get("marker") == facts.get("expected"), f"the marker did not survive the reset: {facts}"
    finally:
        if not read:
            board.exec(_REMOVE_MARKER_FILE)
            board.hard_reset()


# This bench flashes only the generated boot entry, frozen as "main.py", never the legacy
# `legacy/firmware/modules/_boot.py` mechanism that CLAUDE.md's `_boot.py` rule describes. A real
# hard reset must bring the whole application layer back - ConfigManager/FRAM, not just the interpreter.
def test_boot_import_mechanism_actually_boots_the_real_system(board: "Board") -> None:
    board.hard_reset()
    lines = wait_for_boot(board, _BOOT_LOG_TIMEOUT_S)
    assert boot_lines(lines) and not crash_lines(lines), "the generated boot entry's startup lines did not arrive cleanly after a genuine hard reset:\n" + "\n".join(lines)
