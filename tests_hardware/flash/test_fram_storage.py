"""Flash-tier automated tests, gap fix found on a later audit pass (see tests_hardware/README.md's
"gaps found and closed" section): real MB85RS64V SPI FRAM chip coverage. Before this file, zero
automated real-hardware tests referenced AsyFramManager/asy_fram_driver at all - the pre-existing
reboot-persistence tests (flash/test_reboot_persistence.py) exercise config_manager's littlefs-
backed storage, a structurally different mechanism from this real external SPI chip."""

from __future__ import annotations

import re
from pathlib import Path

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
