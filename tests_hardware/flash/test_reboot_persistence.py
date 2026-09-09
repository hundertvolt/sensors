"""Flash-tier automated tests: real reboot/persistence via a genuine `hard_reset()` (mpremote's
DTR-based reset, the closest real equivalent to a power-cycle without pulling power). Uses
hard_reset()+tail_log(), not run_isolated()/exec(), so the real boot.py/main.py path runs undisturbed."""

from __future__ import annotations

import re
from pathlib import Path

from harness import Board, wait_until

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def _parse_result(output: str) -> tuple[bool, str]:
    match = RESULT_RE.search(output)
    if match is None:
        raise AssertionError(f"device script printed no RESULT line - full output:\n{output}")
    return match.group(1) == "PASS", match.group(2).strip()


# ---------------------------------------------------------------------------
# Item 13 - config.json (a real ConfigManager-backed file) survives a genuine reboot.
# ---------------------------------------------------------------------------


def test_config_value_survives_a_genuine_hard_reset(board: Board) -> None:
    write_output = board.run_isolated(DEVICE_SCRIPTS / "reboot_persist_write.py")
    ok, detail = _parse_result(write_output)
    assert ok, f"pre-reboot write failed: {detail}\nfull output:\n{write_output}"

    board.hard_reset()
    wait_until(board.is_reachable, timeout_s=30.0, poll_interval_s=1.0, description="board reachable again after hard_reset()")

    read_output = board.run_isolated(DEVICE_SCRIPTS / "reboot_persist_read.py")
    ok, detail = _parse_result(read_output)
    assert ok, f"post-reboot read failed: {detail}\nfull output:\n{read_output}"


# ---------------------------------------------------------------------------
# This bench only ever flashes the refactored `src/` build (dev_boot.py frozen as "main.py") - never
# the legacy `modules/_boot.py` mechanism BACKLOG.md's open question #1 covers. Verifies a genuine
# hard reset brings the whole refactored application layer (ConfigManager/FRAM, not just the bare
# interpreter) back up cleanly - no twin/mock backend can prove this.
# ---------------------------------------------------------------------------


def test_boot_import_mechanism_actually_boots_the_real_system(board: Board) -> None:
    # This bench's board is left at production-quiet DebugLevel=0 between sessions, which suppresses
    # the pr.one()-level boot-chatter lines this check looks for - raise DebugLevel for the one
    # hard_reset() this test needs, then always restore it to 0 afterward (`finally`).
    raise_output = board.run_isolated(DEVICE_SCRIPTS / "system_debug_level_raise_for_boot_log_check.py")
    ok, detail = _parse_result(raise_output)
    assert ok, f"failed to raise DebugLevel before the boot check: {detail}\nfull output:\n{raise_output}"

    try:
        board.hard_reset()
        # Passive observation only (tail_log(), never exec()/run_isolated()) from here on - a real
        # reboot's own boot.py/main.py sequence must run completely undisturbed for this to mean
        # anything.
        lines = board.tail_log(duration_s=20.0)
        joined = "\n".join(lines)
        assert "CFGMGR_" in joined or "FRAM" in joined, (
            "no sensortask_dev startup log lines observed after a genuine hard reset (with DebugLevel "
            "raised, so this isn't the known DebugLevel=0 suppression) - the frozen boot chain's "
            "import machinery may not be resolving on this real hardware/firmware build.\n"
            f"captured log:\n{joined}"
        )
    finally:
        # write_config() only persists to disk, not the live debug-level registry - one more real
        # hard_reset() makes the restored 0 genuinely live again, not just correct-on-disk.
        restore_output = board.run_isolated(DEVICE_SCRIPTS / "system_debug_level_restore_after_boot_log_check.py")
        ok, detail = _parse_result(restore_output)
        assert ok, f"failed to restore DebugLevel to 0 after the boot check - board may be left non-default: {detail}\nfull output:\n{restore_output}"
        board.hard_reset()
        wait_until(board.is_reachable, timeout_s=30.0, poll_interval_s=1.0, description="board reachable again after restoring DebugLevel=0")
