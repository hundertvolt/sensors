"""Flash-tier tests of the real SPI FRAM chip (FRAMManager/asy_fram_driver): a mechanism separate from
test_reboot_persistence.py's flash-filesystem config storage. Each device script reports facts; the verdict is here."""

import secrets
from typing import TYPE_CHECKING

import pytest
from error_log_helpers import code
from harness import DEVICE_SCRIPTS_DIR, fram_backed_logger_names, parse_facts, wait_until

if TYPE_CHECKING:
    from collections.abc import Callable

    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("fram", "construction", "fram_crash_points", "ci_suite._run_5b_error_log_restore_is_all_or_nothing", "ci_suite._run_5c_storage_paused_shutdown_never_loses_the_error_log")

# @tunable l3.fram_storage_short_script_timeout_s = 30.0
_SHORT_SCRIPT_TIMEOUT_S = 30.0
# @tunable l3.fram_storage_backup_script_timeout_s = 150.0
_BACKUP_SCRIPT_TIMEOUT_S = 150.0
# @tunable l3.fram_storage_reachable_timeout_s = 30.0
_REACHABLE_TIMEOUT_S = 30.0
# @tunable l3.fram_storage_reachable_poll_s = 1.0
_REACHABLE_POLL_S = 1.0
# @tunable l3.fram_storage_script_timeout_s = 60.0
_SCRIPT_TIMEOUT_S = 60.0
# @tunable l3.fram_storage_pause_script_timeout_s = 90.0
_PAUSE_SCRIPT_TIMEOUT_S = 90.0
# @tunable l3.fram_storage_lockout_script_timeout_s = 45.0
_LOCKOUT_SCRIPT_TIMEOUT_S = 45.0
_TEST_BAND = (code("E", "TEST_SEED_A"), code("E", "TEST_SEED_B"), code("E", "TEST_SEED_C"))  # every seed script's codes
_SEQUENCES = 3 ** 3  # the reset-race nonce picks one of the test band's three-code sequences
_AFTER_RACE = code("E", "TEST_SEED_C")  # the verify phase's post-recovery entry


def _cleared(entry: object) -> bool:
    return isinstance(entry, dict) and entry.get("ErrCount") == 0 and all(t == "N" for t in entry.get("ErrType", ["?"]))


def _kept(codes: "list[int]") -> "list[int]":
    # The history the newest-entry rule leaves (SPECIFICATION.md Part C.7.1): a repeat of the newest code takes no slot.
    kept: list[int] = []
    for num in codes:
        if not kept or kept[-1] != num:
            kept.append(num)
    return kept


def _run(board: "Board", script: str, timeout_s: float) -> "dict[str, object]":
    return parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / script, timeout_s=timeout_s))


# ---------------------------------------------------------------------------
# FRAMManager/FRAM_SPI's own chunk write/read/CRC/dual-copy logic against the real chip.
# ---------------------------------------------------------------------------


def test_fram_chunk_write_read_roundtrips_against_the_real_chip(board: "Board", result_note: "Callable[[str], None]") -> None:
    facts = _run(board, "fram_manager_roundtrip.py", _SHORT_SCRIPT_TIMEOUT_S)
    result_note(f"FRAM part RDID {facts.get('rdid')}")
    for key in ("setup", "allocated", "cleared_first", "written", "read_ok", "matches", "cleared_last"):
        assert facts.get(key) is True, f"chunk round trip: {key} is {facts.get(key)!r}; facts {facts}"


# ---------------------------------------------------------------------------
# SGP40_Reader's real VOC-state FRAM backup/restore pathway ("FRAM backup working").
# ---------------------------------------------------------------------------


def test_sgp40_voc_state_backs_up_to_and_restores_from_the_real_chip(board: "Board") -> None:
    # Up to ~85 s on the board (the first 1 min BackupPeriod trigger, then the restore), fed in steps.
    facts = _run(board, "sgp40_fram_backup_restore.py", _BACKUP_SCRIPT_TIMEOUT_S)
    assert facts.get("backup_written") is True, f"reader1 never completed a backup within the wait: {facts}"
    assert facts.get("restored_from") is not None, f"the fresh reader restored no backup: {facts}"
    assert facts.get("restored_state_matches") is True, f"the restored backup is not the one reader1 wrote: {facts}"
    assert facts.get("cleared_last") is True, f"the VOC-state chunk was not cleared after the run: {facts}"


# ---------------------------------------------------------------------------
# PrintLogHistoryStore's real FRAM-backed error/warning history ("FRAM error storage working").
# ---------------------------------------------------------------------------


def test_error_log_history_persists_in_the_real_chip_across_a_simulated_reboot(board: "Board") -> None:
    facts = _run(board, "fram_error_log_roundtrip.py", _SHORT_SCRIPT_TIMEOUT_S)
    assert facts.get("restored") is True, f"the fresh logger did not initialise from the chip: {facts}"
    nums, types = facts.get("err_num"), facts.get("err_type")
    assert facts.get("err_count") == 1, f"restored ErrCount is not 1: {facts}"
    assert isinstance(nums, list) and isinstance(types, list) and [(n, t) for n, t in zip(nums, types, strict=True) if t != "N"] == [(facts.get("seed"), "E")], f"the history holds not exactly the seeded entry: {facts}"
    assert facts.get("seed") in _TEST_BAND, f"the seed is no test-band code: {facts}"
    assert facts.get("cleared_last") is True, f"the seeded entry survived the run: {facts}"


@pytest.mark.parametrize("seam", [1, 2, 3, 4, 5])
def test_error_log_history_is_all_or_nothing_across_a_reset_raced_chunk_write(board: "Board", result_note: "Callable[[str], None]", seam: int) -> None:
    # The reset lands right after transfer `seam` of the chunk write's five: status byte 1 and 2 BUSY, payload+CRC,
    # status byte 1 and 2 IDLE (tests/test_asy_fram_manager.py pins the sequence).
    nonce = secrets.randbelow(_SEQUENCES)
    seed = [_TEST_BAND[0] + (nonce // 3**i) % 3 for i in range(3)]
    raced = _TEST_BAND[0] + nonce % 3
    out = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "fram_error_log_reset_race_seed_and_race.py", timeout_s=_SHORT_SCRIPT_TIMEOUT_S, SEAM=seam, NONCE=nonce)
    seeded = parse_facts(out, allow_missing_done=True).get("seeded")
    assert "SEEDED" in out and f"LANDED seam={seam}" in out, f"the reset did not land on seam {seam}:\n{out}"
    assert isinstance(seeded, dict) and seeded.get("ErrCount") == 3, f"the seed phase did not seed three entries before racing: {seeded!r}"
    wait_until(board.is_reachable, timeout_s=_REACHABLE_TIMEOUT_S, poll_interval_s=_REACHABLE_POLL_S, description="board reachable again after the reset-raced error-log write")
    facts = _run(board, "fram_error_log_reset_race_verify.py", _SCRIPT_TIMEOUT_S)
    assert facts.get("setup") is True and facts.get("initialized") is True, f"seam {seam}: the verify's store did not set up from the chip, so an empty history proves nothing: {facts}"
    # The only three outcomes a reset mid-write may leave: losing the whole history is accepted (owner, 2026-09-11; Part
    # C.3.1), a partial or garbled restore never is.
    accepted = {"empty": ([], 0), "seeded": (_kept(seed), 3), "raced": (_kept([*seed, raced]), 4)}
    reached = next((name for name, (history, count) in accepted.items() if facts.get("recovered") == history and facts.get("err_count") == count), None)
    result_note(f"seam {seam}, nonce {nonce}: {reached} ({facts.get('recovered')})")
    assert reached is not None, f"seam {seam}: the restored history is neither intact nor cleanly empty (accepted {accepted}): {facts}"
    assert facts.get("warnings") == 0, f"seam {seam}: the restored history grew warning entries: {facts}"
    recovered = facts.get("recovered")
    assert isinstance(recovered, list) and facts.get("tail") == _kept([*recovered, _AFTER_RACE]), f"seam {seam}: the chunk did not take a fresh entry after the reset: {facts}"
    assert facts.get("cleared_last") is True, f"seam {seam}: the chunk was not cleared after the verify: {facts}"


# ---------------------------------------------------------------------------
# The error log's boot window: a ResetErrors landing before a FRAM-backed logger has run its own
# pr.setup() must persist and survive that setup() (Part C.7). The same claim on the real chip
# that test_asy_print_log.py, _sensortask_scenarios.py and the twin integration test make elsewhere.
# ---------------------------------------------------------------------------


def test_error_log_reset_during_the_boot_window_is_persisted_and_not_undone(board: "Board") -> None:
    facts = _run(board, "fram_error_log_reset_during_boot_window.py", _SCRIPT_TIMEOUT_S)
    assert facts.get("seeded_count") == 3, f"could not seed a three-entry history to reset against: {facts}"
    assert facts.get("reset_persisted") is True, f"the reset write never reached the chip: {facts}"
    assert _cleared(facts.get("after")), f"setup() restored the pre-reset history over a persisted reset: {facts}"
    assert _cleared(facts.get("persisted")), f"the chip still holds the pre-reset history: {facts}"
    assert facts.get("cleared_last") is True, f"the chunk was not cleared after the run: {facts}"


# ---------------------------------------------------------------------------
# Bottom-level hardware function: the real WPEN|BP0|BP1 mechanism gates a real write AND a real
# read and can be cleared again. Reads being gated too is intended (Part A.4's FRAM entry) and is
# asserted identically at the mock and twin tiers.
#
# Flash-only, no bench counterpart (E.6.6 row `fram-write-protect-no-rest`): get_write_protected()/
# set_write_protected() have no REST route at all - no PUT/GET a bench test could drive to reach it.
# ---------------------------------------------------------------------------


def test_write_protection_actually_gates_a_real_write_and_a_real_read(board: "Board") -> None:
    facts = _run(board, "fram_write_protect_roundtrip.py", _SHORT_SCRIPT_TIMEOUT_S)
    assert facts.get("failure") is None, f"write protection: {facts.get('failure')}; facts {facts}"
    for key in ("blocked_write", "blocked_read", "data_survived", "cleared_last"):
        assert facts.get(key) is True, f"write protection: {key} is {facts.get(key)!r}; facts {facts}"
    assert facts.get("left_protected") is False, f"the chip was left write-protected: {facts}"


# ---------------------------------------------------------------------------
# The storage-pause gate (pause_permanent_storage()/FRAMManager.set_pause()). The mock tier covers the
# clamp/re-arm/abort logic but fakes machine.Timer, so two claims are hardware-only: the auto-unpause
# deadline is met on the real uptime tick, and a pause really stops the write.
# ---------------------------------------------------------------------------


def test_storage_pause_gates_the_real_chip_and_the_real_auto_unpause_timer_fires(board: "Board", result_note: "Callable[[str], None]") -> None:
    # ~20 s of real waiting inside the script (the 2/2/6 s windows plus margins and the exhausted-pool step's own).
    facts = _run(board, "fram_pause_unpause_and_gating.py", _PAUSE_SCRIPT_TIMEOUT_S)
    skipped = facts.get("skipped")
    if isinstance(skipped, dict) and skipped.get("total"):
        result_note(f"pause gating: checks skipped for a premise that did not hold: {skipped}")
    for key in ("failures", "hog_deinit_failures"):
        record = facts.get(key)
        assert isinstance(record, dict) and record.get("total") == 0, f"pause gating: {key} {record}; facts {facts}"
    assert facts.get("cleared_last") is True and facts.get("ts_cleared_last") is True, f"a chunk was not cleared after the run: {facts}"


# ---------------------------------------------------------------------------
# The FRAM command hold: the longest stretch a chunk operation holds the loop without yielding stays
# under one UART poll floor (SPECIFICATION.md F.5.8, J.6). Wire time is silicon-only, so no twin leg.
# ---------------------------------------------------------------------------


def test_fram_command_hold_stays_under_the_uart_poll_floor(board: "Board", result_note: "Callable[[str], None]") -> None:
    facts = _run(board, "fram_command_hold_timing.py", _SHORT_SCRIPT_TIMEOUT_S)
    write_us, read_us, hold_us = facts.get("write_us"), facts.get("read_us"), facts.get("hold_us")
    floor_us, budget_us = facts.get("uart_floor_us"), facts.get("block_hold_budget_us")
    assert facts.get("command_ok") is True and facts.get("block_ok") is True, f"a timed command reported a failure status: {facts}"
    assert isinstance(write_us, int) and isinstance(read_us, int) and isinstance(floor_us, int), f"the timings are missing: {facts}"
    result_note(f"FRAM hold: write {write_us} us, read {read_us} us, block {hold_us} us (floor {floor_us} us, budget {budget_us} us)")
    assert max(write_us, read_us) <= floor_us, f"the longest non-yielding stretch {max(write_us, read_us)} us passes the UART poll floor {floor_us} us: {facts}"
    assert isinstance(hold_us, int) and isinstance(budget_us, int) and hold_us <= budget_us, f"the block hold {hold_us} us passes its budget {budget_us} us: {facts}"


# ---------------------------------------------------------------------------
# The busy-status lockout: the real-hardware half of the SPI RX-overrun coverage. The overrun is a
# DMA timing condition no Python knob can induce on target, so this tests its consequence, which is
# inducible and is what actually protects a destructive-readout part.
# ---------------------------------------------------------------------------


def test_both_blocks_left_busy_lock_the_real_chunk_until_it_is_rewritten(board: "Board") -> None:
    facts = _run(board, "fram_busy_status_lockout.py", _LOCKOUT_SCRIPT_TIMEOUT_S)
    for key in ("baseline_ok", "forced_busy", "locked_read_none", "error_logged", "recovered", "cleared_last"):
        assert facts.get(key) is True, f"busy-status lockout: {key} is {facts.get(key)!r}; facts {facts}"


# ---------------------------------------------------------------------------
# A firmware asking for more FRAM than its chip has is caught before flash, never as a boot-time console line nobody
# watches; mpremote-only by design, a one-time build-validity fact (owner, 2026-09-16).
# ---------------------------------------------------------------------------


def test_every_fram_wired_module_gets_a_real_chunk_after_a_full_system_build(board: "Board", result_note: "Callable[[str], None]") -> None:
    facts = _run(board, "fram_capacity_after_full_system_build.py", _SCRIPT_TIMEOUT_S)
    expected = fram_backed_logger_names()
    found, ram_only = facts.get("found_fram_loggers"), facts.get("ram_only")
    assert facts.get("fram_present") is True, f"the build constructed no FRAM manager: {facts}"
    assert isinstance(found, list) and isinstance(ram_only, list), f"the logger facts are missing: {facts}"
    missing, extra = sorted(set(expected) - set(found)), sorted(set(found) - set(expected))
    assert not missing and not extra, f"FRAM-backed loggers differ from buildgen's set: missing {missing}, extra {extra}; facts {facts}"
    # A logger buildgen leaves out of its set is RAM-only in the build itself, no degraded fallback.
    degraded = [name for name in ram_only if str(name).split(".")[-1] in expected]
    assert not degraded, f"loggers buildgen backs with FRAM fell back to RAM: {degraded}; facts {facts}"
    result_note(f"FRAM allocated {facts.get('allocated_size')} of {facts.get('size')} B; RAM-only by design: {ram_only}")
