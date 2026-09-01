"""Flash-tier automated tests, Part 1 category C (tmp_hardware_test_candidates.md items 13-14) -
real reboot/persistence via a genuine `hard_reset()` (mpremote's DTR-based `reset`, the closest
real-hardware equivalent to a power-cycle without actually pulling power - see Part 2's
manual_persistence.py for genuine power-loss instead). Deliberately uses hard_reset()
+ tail_log(), never run_isolated()/exec(), for anything that needs to observe the *real* boot
sequence - see harness.Board.run_isolated()'s own docstring for why an isolated-driver call's
implicit soft-reset can't be trusted to exercise the same boot.py/main.py path a real reboot does.

Item 15 (SystemService._reboot() sequencing) moved to tests_hardware/bench/test_end_to_end_timing.py:
a real, closable gap found while writing this file, not part of the original candidate list's own
framing - see that file's own module docstring for the finding. The candidate list tagged item 15
[USB] (flash tier, no network), but its own description says "triggered via a REST call" - REST
needs HTTP needs a reachable network, which flash tier's own definition (HARDWARE_TEST_PLAN.md §2.3:
"flash - generic + real USB serial access to a board. No network") explicitly excludes. Flagged and
fixed here rather than silently building a test that can't actually run as tagged."""

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
# Item 14 - modules/_boot.py's `import sensortask.py` (literal .py in the import statement)
# mechanism, BACKLOG.md open question #1. Read-only observation, never modifies _boot.py itself -
# CLAUDE.md explicitly forbids "fixing" that line blind without this exact real-hardware evidence.
# ---------------------------------------------------------------------------


def test_boot_import_mechanism_actually_boots_the_real_system(board: Board) -> None:
    board.hard_reset()
    # Passive observation only (tail_log(), never exec()/run_isolated()) - a real reboot's own
    # boot.py/main.py sequence must run completely undisturbed for this to mean anything. If
    # `import sensortask.py` silently failed (the plausible-looking ModuleNotFoundError
    # BACKLOG.md's open question #1 worries about), none of sensortask_wozi's own startup log
    # lines would ever appear - this is the empirical answer that question has been missing.
    lines = board.tail_log(duration_s=20.0)
    joined = "\n".join(lines)
    assert "CFGMGR_" in joined or "FRAM" in joined, (
        "no sensortask_wozi startup log lines observed after a genuine hard reset - "
        f"modules/_boot.py's `import sensortask.py` may not be resolving on this real hardware/firmware build.\n"
        f"captured log:\n{joined}"
    )
