"""Flash-tier automated tests: real MB85RS64V SPI FRAM chip coverage (AsyFramManager/
asy_fram_driver) - a structurally different mechanism from test_reboot_persistence.py's
littlefs-backed config storage."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

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


# ---------------------------------------------------------------------------
# Bottom-level hardware function: the real WPEN|BP0|BP1 write-protect mechanism actually gates a
# real write and can be cleared again - not just "can a chunk be written at all".
# ---------------------------------------------------------------------------


def test_write_protection_actually_gates_a_real_write(board: Board) -> None:
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
