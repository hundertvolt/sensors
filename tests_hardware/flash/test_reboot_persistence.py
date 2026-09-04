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
# Item 14, corrected scope: this bench only ever flashes the new, refactored `src/` build (`dev`,
# via boot_entry/dev_boot.py frozen as the literal name "main.py" - see SPECIFICATION.md Part
# B.11/F.1) - never the legacy deployed codebase's `modules/_boot.py`/`import sensortask.py`
# mechanism BACKLOG.md's open question #1 is actually about (that question targets the *currently
# deployed* 1.26 firmware specifically, per CLAUDE.md's hard rule against touching/testing it blind,
# and was separately resolved by tracing the pinned 1.28 source directly - see BACKLOG.md item 1).
# What this test actually verifies, and can: a genuine hard reset on real hardware brings the whole
# refactored application layer (ConfigManager/FRAM setup, not just the bare interpreter) back up
# cleanly - the real-hardware equivalent of "the frozen boot chain's own import machinery resolves
# and sensortask_dev.build_system() actually runs," which no twin/mock backend can prove.
# ---------------------------------------------------------------------------


def test_boot_import_mechanism_actually_boots_the_real_system(board: Board) -> None:
    # REAL FINDING: this bench's board is deliberately left at its own production-quiet
    # DebugLevel=0 (print_log.py's _LOG_OFF) between sessions, which unconditionally suppresses
    # every pr.one()-level boot-chatter line (`_LOG_ONCE`, level 3) this check looks for -
    # confirmed directly against real source (print_log.py's `one()`), not assumed. A first real
    # run against a DebugLevel=0 board failed here for exactly this reason, not a real boot
    # regression. Raise DebugLevel for the one hard_reset() this test needs, then always restore it
    # to 0 afterward (`finally`) - see the two device_scripts' own docstrings for the full design.
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
        # write_config() only persists to disk - it does not push the new value into the already-
        # running system's live debug-level registry (that push is REST PUT's own _set_dict_cfg()
        # job, not exercised here). One more real hard_reset() makes the restored 0 genuinely live
        # again, not just correct-on-disk-until-the-next-reboot - "soft/hard resets are free and
        # unlimited" per this tier's own design (HARDWARE_TEST_PLAN.md §6.2), so this costs nothing.
        restore_output = board.run_isolated(DEVICE_SCRIPTS / "system_debug_level_restore_after_boot_log_check.py")
        ok, detail = _parse_result(restore_output)
        assert ok, f"failed to restore DebugLevel to 0 after the boot check - board may be left non-default: {detail}\nfull output:\n{restore_output}"
        board.hard_reset()
        wait_until(board.is_reachable, timeout_s=30.0, poll_interval_s=1.0, description="board reachable again after restoring DebugLevel=0")
