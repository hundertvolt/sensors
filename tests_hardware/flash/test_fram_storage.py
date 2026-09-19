"""Flash-tier automated tests: real MB85RS64V SPI FRAM chip coverage (AsyFramManager/
asy_fram_driver) - a structurally different mechanism from test_reboot_persistence.py's
littlefs-backed config storage."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from harness import wait_until

if TYPE_CHECKING:
    from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
RESULT_RE = re.compile(r"^RESULT: (PASS|FAIL)(.*)$", re.MULTILINE)


def _run_and_assert_pass(board: Board, script_name: str, timeout_s: float, label: str) -> None:
    output = board.run_isolated(DEVICE_SCRIPTS / script_name, timeout_s=timeout_s)
    match = RESULT_RE.search(output)
    assert match is not None, f"device script printed no RESULT line - full output:\n{output}"
    assert match.group(1) == "PASS", f"{label} failed: {match.group(2).strip()}\nfull output:\n{output}"


# ---------------------------------------------------------------------------
# AsyFramManager/FRAM_SPI's own chunk write/read/CRC/dual-copy logic against the real chip.
# ---------------------------------------------------------------------------


def test_fram_chunk_write_read_roundtrips_against_the_real_chip(board: Board) -> None:
    _run_and_assert_pass(board, "fram_manager_roundtrip.py", timeout_s=30.0, label="FRAM chunk manager roundtrip")


# ---------------------------------------------------------------------------
# SGP40_Reader's real VOC-state FRAM backup/restore pathway ("FRAM backup working").
# ---------------------------------------------------------------------------


def test_sgp40_voc_state_backs_up_to_and_restores_from_the_real_chip(board: Board) -> None:
    # ~90s real runtime (60s to the first natural BackupPeriod trigger, plus restore-cycle margin)
    # - see the device script's own docstring; timeout is generous relative to that.
    _run_and_assert_pass(board, "sgp40_fram_backup_restore.py", timeout_s=150.0, label="SGP40 FRAM backup/restore")


# ---------------------------------------------------------------------------
# PrintLogHistoryStore's real FRAM-backed error/warning history ("FRAM error storage working").
# ---------------------------------------------------------------------------


def test_error_log_history_persists_in_the_real_chip_across_a_simulated_reboot(board: Board) -> None:
    _run_and_assert_pass(board, "fram_error_log_roundtrip.py", timeout_s=30.0, label="FRAM error log roundtrip")


def test_error_log_history_is_all_or_nothing_across_a_reset_raced_chunk_write(board: Board) -> None:
    # The other half of the claim above, which simulates a fresh boot in the SAME process and so
    # only ever shows the happy path. Losing the whole history to a reset landing mid-write is
    # accepted (owner, 2026-09-11; Part C.3.1); a PARTIAL restore never is, and is what this asserts.
    board.run_isolated_expect_reset(DEVICE_SCRIPTS / "fram_error_log_reset_race_seed_and_race.py", timeout_s=30.0)
    wait_until(board.is_reachable, timeout_s=30.0, poll_interval_s=1.0, description="board reachable again after the reset-raced error-log write")
    _run_and_assert_pass(board, "fram_error_log_reset_race_verify.py", timeout_s=60.0, label="FRAM error-log reset-race all-or-nothing check")


# ---------------------------------------------------------------------------
# The error log's boot window: a ResetErrors landing before a FRAM-backed logger has run its own
# pr.setup() must persist and survive that setup() (Part C.7). The same claim on the real chip
# that test_print_log.py, _sensortask_scenarios.py and the twin integration test make elsewhere.
# ---------------------------------------------------------------------------


def test_error_log_reset_during_the_boot_window_is_persisted_and_not_undone(board: Board) -> None:
    _run_and_assert_pass(board, "fram_error_log_reset_during_boot_window.py", timeout_s=60.0, label="FRAM error-log boot-window reset check")


# ---------------------------------------------------------------------------
# Bottom-level hardware function: the real WPEN|BP0|BP1 mechanism gates a real write AND a real
# read and can be cleared again. Reads being gated too is intended (Part A.4's FRAM entry) and is
# asserted identically at the mock and twin tiers.
#
# Flash-only, no bench counterpart, structurally (E.6.6 exception 2): get_write_protected()/
# set_write_protected() have no REST route at all - no PUT/GET a bench test could drive to reach it.
# ---------------------------------------------------------------------------


def test_write_protection_actually_gates_a_real_write_and_a_real_read(board: Board) -> None:
    _run_and_assert_pass(board, "fram_write_protect_roundtrip.py", timeout_s=30.0, label="FRAM write-protect roundtrip")


# ---------------------------------------------------------------------------
# The storage-pause gate (pause_permanent_storage()/AsyFramManager.set_pause()). The mock tier
# covers the clamp/re-arm/abort logic but fakes machine.Timer, so two claims are hardware-only:
# the ONE_SHOT auto-unpause really fires on an rp2 alarm pool, and a pause really stops the write.
# ---------------------------------------------------------------------------


def test_storage_pause_gates_the_real_chip_and_the_real_auto_unpause_timer_fires(board: Board) -> None:
    # ~20s of real waiting inside the script (the 2s/2s/6s auto-unpause windows plus margins, and
    # the exhausted-alarm-pool step's own window), so the timeout is generous relative to that
    # rather than to the script's negligible compute.
    _run_and_assert_pass(board, "fram_pause_unpause_and_gating.py", timeout_s=90.0, label="FRAM pause/unpause gating")


# ---------------------------------------------------------------------------
# The busy-status lockout: the real-hardware half of BACKLOG's SPI RX-overrun coverage. The
# overrun is a DMA timing condition no Python knob can induce on target, so this tests its
# consequence, which is inducible and is what actually protects a destructive-readout part.
# ---------------------------------------------------------------------------


def test_both_blocks_left_busy_lock_the_real_chunk_until_it_is_rewritten(board: Board) -> None:
    _run_and_assert_pass(board, "fram_busy_status_lockout.py", timeout_s=45.0, label="FRAM busy-status lockout")


# ---------------------------------------------------------------------------
# WP4/Topic 6: a shipped firmware asking for more FRAM than its own chip has must be caught before
# flash, not discovered as a silent boot-time console print nobody's watching. mpremote-only by
# design (owner's own decision) - no new /status field, this is a one-time build-validity fact.
# ---------------------------------------------------------------------------


def test_every_fram_wired_module_gets_a_real_chunk_after_a_full_system_build(board: Board) -> None:
    _run_and_assert_pass(board, "fram_capacity_after_full_system_build.py", timeout_s=60.0, label="FRAM capacity check")
