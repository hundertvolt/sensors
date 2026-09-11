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
    # The other half of the claim above: that one simulates a fresh boot with a new manager object
    # in the SAME process, so it never actually restarts and can only ever show the happy path.
    # A real reset landing mid-chunk-write is the case that matters, and losing the whole history to
    # it is accepted behavior (project owner's call, 2026-09-11 - no recovery scheme wanted): an
    # interrupted write leaves a status byte at _STATUS_BUSY, PrintLogHistoryStore.setup()'s _read()
    # then fails, and its _write() fallback stores the empty ring. Measured in the digital twin at
    # roughly 1 abrupt restart in 8. What must never happen - and is what this asserts on silicon -
    # is a PARTIAL or garbled restore, which would mean the dual-block + CRC + busy-flag protocol
    # had failed at its actual job. Chunk-level counterpart to test_bus_concurrency.py's own
    # raw-driver test_fram_hard_reset_race_during_write_and_recovery.
    board.run_isolated_expect_reset(DEVICE_SCRIPTS / "fram_error_log_reset_race_seed_and_race.py", timeout_s=30.0)
    wait_until(board.is_reachable, timeout_s=30.0, poll_interval_s=1.0, description="board reachable again after the reset-raced error-log write")
    _run_and_assert_pass(board, "fram_error_log_reset_race_verify.py", timeout_s=60.0, label="FRAM error-log reset-race all-or-nothing check")


# ---------------------------------------------------------------------------
# The error log's own boot window: a ResetErrors landing before a FRAM-backed logger has run its
# own pr.setup() must still be persisted, and must survive that setup() (BACKLOG.md #16). Mirrored
# at the mock tier (tests/test_print_log.py, tests/test_sensortask_wozi.py) and the twin tier
# (tests/test_digital_twin_sensortask_integration.py); this is the same claim on the real chip.
# ---------------------------------------------------------------------------


def test_error_log_reset_during_the_boot_window_is_persisted_and_not_undone(board: Board) -> None:
    _run_and_assert_pass(board, "fram_error_log_reset_during_boot_window.py", timeout_s=60.0, label="FRAM error-log boot-window reset check")


# ---------------------------------------------------------------------------
# Bottom-level hardware function: the real WPEN|BP0|BP1 write-protect mechanism actually gates a
# real write AND a real read, and can be cleared again - not just "can a chunk be written at all".
# Reads being gated too is intended, accepted behavior (SPECIFICATION.md Part A.4's FRAM entry),
# asserted identically at the mock and twin tiers.
# ---------------------------------------------------------------------------


def test_write_protection_actually_gates_a_real_write_and_a_real_read(board: Board) -> None:
    _run_and_assert_pass(board, "fram_write_protect_roundtrip.py", timeout_s=30.0, label="FRAM write-protect roundtrip")


# ---------------------------------------------------------------------------
# The storage-pause gate (system_service.pause_permanent_storage()/AsyFramManager.set_pause()).
# The mock tier already covers the clamp/re-arm/abort-on-arm-failure logic exhaustively, but it
# fakes machine.Timer - so "the real ONE_SHOT auto-unpause actually fires on an rp2 alarm pool" and
# "a pause genuinely stops the bus write reaching the chip" are both hardware-only claims.
# ---------------------------------------------------------------------------


def test_storage_pause_gates_the_real_chip_and_the_real_auto_unpause_timer_fires(board: Board) -> None:
    # ~20s of real waiting inside the script (the 2s/2s/6s auto-unpause windows plus margins, and
    # the exhausted-alarm-pool step's own window), so the timeout is generous relative to that
    # rather than to the script's negligible compute.
    _run_and_assert_pass(board, "fram_pause_unpause_and_gating.py", timeout_s=90.0, label="FRAM pause/unpause gating")


# ---------------------------------------------------------------------------
# The busy-status lockout: the real-hardware half of the SPI RX-overrun coverage BACKLOG.md tracks.
# The overrun itself is a DMA timing condition no Python-level knob can induce on target, so this
# tests its consequence instead - which IS inducible, and is the behaviour that actually protects a
# destructive-readout part. Mock and twin tiers already cover it; this closes the hardware tier.
# ---------------------------------------------------------------------------


def test_both_blocks_left_busy_lock_the_real_chunk_until_it_is_rewritten(board: Board) -> None:
    _run_and_assert_pass(board, "fram_busy_status_lockout.py", timeout_s=45.0, label="FRAM busy-status lockout")
