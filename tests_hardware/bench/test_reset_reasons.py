"""Bench-tier automated tests: every reset code the firmware attributes, proven through GET /status's ResetReason after
the production boot serves - each test saves errcount and the raw FRAM first, reads the watchdog REASON bits, asserts
the half the reset kind fixes, and restores serving after. Code 1 (a power cut) is the manual power-cycle step's."""

import time
from typing import TYPE_CHECKING

import _load
import http_client
import pytest
import serial
from error_log_helpers import ErrcountEntry, code, get_errcount, save_errcount
from harness import DEVICE_SCRIPTS_DIR, SRC_DIR, fram_backed_logger_names, kick_after_reset, kick_then_reset, parse_facts, picotool, restore_board_to_serving, save_fram_raw, scratch_config_entries, wait_until

from buildgen.validate import _WDT_TIMEOUT_MS, module_int_const

if TYPE_CHECKING:
    from collections.abc import Callable

    from bench_control import BenchBridge
    from harness import Board
    from http_client import JSONObject

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_12_reset_reasons", "ci_suite._run_12_stack_exhaustion", "loop_end", "scenarios.an_escalation_entry_that_never_finishes_leaves_code_20_to_the_watchdog")

_SRC = "asy_system_service.py"
_RR = {name: module_int_const(SRC_DIR, _SRC, f"_RR_{name}") for name in ("UNKNOWN", "WATCHDOG", "TASK_BUDGET", "STACK_EXHAUSTED", "STARVE_ARM_FAILED", "COMMAND_INCOMPLETE", "BOOT_FAILURE", "LOOP_ENDED")}
_BOOT_DONE = module_int_const(SRC_DIR, _SRC, "BOOT_DONE")
_RR_INTERRUPTED = module_int_const(SRC_DIR, _SRC, "RR_INTERRUPTED")
_TASK_CHECK_TIME, _RESET_DELAY = module_int_const(SRC_DIR, _SRC, "_TASK_CHECK_TIME"), module_int_const(SRC_DIR, _SRC, "_RESET_DELAY")
_TIMER_BIT, _FORCED_BIT = 0x1, 0x2  # the watchdog's REASON bits 0-1, TIMER and FORCE (pico-sdk watchdog.h)
# Read after the serving boot: the exec's Ctrl-C and soft reset change no reset register (the bench's record).
_READ_REASON_BITS = "from machine import mem32\nprint('REASON_BITS', mem32[0x40058008] & 3)\n"
_SCRATCH_REMOVE = "import os\nif 'hwtest-scratch' in os.listdir():\n    for n in os.listdir('hwtest-scratch/'):\n        os.remove('hwtest-scratch/' + n)\n    os.rmdir('hwtest-scratch/')\n"
_SCRIPT_TIMEOUT_S = 120.0
_SERVING_TIMEOUT_S = 90.0
_SERVING_POLL_S = 2.0
_STATUS_TIMEOUT_S = 10.0
_LOSS_MARGIN_S = 2.0
_PICOTOOL_TIMEOUT_S = 30.0
_BOOT_PHASES = (1, 2, 3, 4, 5)  # asy_system_service.py's BOOT_CONSTRUCTION .. BOOT_NTP: a hang in each reads 10 + phase


def _attributed(board: "Board", dut_ip: str, expected: int, result_note: "Callable[[str], None]", context: str) -> int:
    # Asserts the reason, then reads the watchdog's REASON bits off the chip (the exec parks main.py) for the half checks,
    # once the board is on USB: a serving board can still be re-enumerating there, and the exec then fails (bench, 2026-11-11).
    reason = _system_status(dut_ip).get("ResetReason")
    wait_until(board.is_device_present, timeout_s=_SERVING_TIMEOUT_S, description=f"{context}: the board back on USB for the REASON bits read")
    bits = next((int(line.split()[1]) for line in board.exec(_READ_REASON_BITS).splitlines() if line.startswith("REASON_BITS ")), None)
    result_note(f"{context}: ResetReason {reason}, watchdog REASON bits {bits}")
    assert reason == expected, f"{context}: ResetReason reads {reason}, not {expected}; watchdog REASON bits {bits}"
    assert isinstance(bits, int), f"{context}: the chip's watchdog REASON bits were not read"
    return bits


def _evidence(board: "Board", bench: "BenchBridge", dut_ip: str, name: str) -> None:
    # Errcount and the raw FRAM before the reset under test; the dump's exec parks main.py, so serving is restored.
    save_errcount(dut_ip, name)
    save_fram_raw(board, name)
    restore_board_to_serving(board, bench, dut_ip)


def _round_holds_the_budget_entry(facts: "dict[str, object]") -> bool:
    # A round the script printed after the escalation's entry write: SYSTEM's RAM log there, the one place it lands.
    rounds = [value.get("system") for key, value in facts.items() if key.startswith("round_") and isinstance(value, dict)]
    return any(isinstance(log, dict) and ("E", code("E", "TASK_BUDGET_REBOOT")) in zip(log.get("ErrType", []), log.get("ErrNum", []), strict=False) for log in rounds)


def _system_status(dut_ip: str) -> "JSONObject":
    # The production boot's /status system block, once it serves (passive polling only).
    wait_until(lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_STATUS_TIMEOUT_S).status_code == 200, timeout_s=_SERVING_TIMEOUT_S, poll_interval_s=_SERVING_POLL_S, description="DUT serving /status after the reset")
    system = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_STATUS_TIMEOUT_S).json().get("system")
    assert isinstance(system, dict), f"/status carries no system block: {system!r}"
    return system


def _holds_its_boot_warning_alone(entry: "ErrcountEntry") -> bool:
    # A restarted log the boot after the cut erase gave one entry: SGP40's warning for the blanked backup.
    return entry["counter"] == 1 and [(h.get("type"), h.get("num")) for h in entry["history"] if h.get("type") != "N"] == [("W", code("W", "SGP_NO_BACKUP"))]


def _provoked(board: "Board", bench: "BenchBridge", script: str, *, hold_unread_s: "float | None" = None, **extras: object) -> "dict[str, object]":
    # The script's own reset, then the station kick once the board has left USB: the AP keeps a reset board's stale
    # entry for about 60 s, which blocks its rejoin past the serving wait (bench, 2026-11-06).
    output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / script, timeout_s=_SCRIPT_TIMEOUT_S, hold_unread_s=hold_unread_s, **extras)
    bench.kick_all_stations()
    return parse_facts(output, allow_missing_done=True)  # its facts come before the reset


def test_a_harness_hard_reset_reads_as_a_console_interrupt(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    try:
        _evidence(board, bench, dut_ip, "reset-reason-hard-reset")
        # mpremote's Ctrl-C ends main.py, whose entry records 21; its raw-REPL soft reset runs no main.py, and the
        # machine.reset() after it keeps both regions, so the boot reads 21 (tools/mpremote/mpremote/transport_serial.py:179-197).
        kick_then_reset(board, bench)
        bits = _attributed(board, dut_ip, _RR_INTERRUPTED, result_note, "harness hard reset")
        assert bits & _FORCED_BIT, f"a machine.reset() left the forced bit clear: {bits}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


def test_a_bootloader_reboot_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    try:
        _evidence(board, bench, dut_ip, "reset-reason-bootloader")
        answer = http_client.fetch(dut_ip, 80, "PUT", "/system", {"SystemCmd": "bootloader"}, timeout_s=_STATUS_TIMEOUT_S).json()
        replied = time.monotonic()
        assert answer.get("result") == {"SystemCmd": "Valid"}, f"the bootloader command was not accepted: {answer}"
        # The shutdown waits at most one supervisor pass, then the reset delay: the board leaves USB within that.
        bound = _TASK_CHECK_TIME + _RESET_DELAY + _LOSS_MARGIN_S
        gone = kick_after_reset(board, bench, bound)  # its stale AP-side entry would block the rejoin after BOOTSEL
        result_note(f"reply to USB loss: {gone - replied:.1f} s (bound {bound} s, watchdog {_WDT_TIMEOUT_MS} ms)")
        picotool(board, "reboot", timeout_s=_PICOTOOL_TIMEOUT_S)  # answers only a BOOTSEL device: no load, no flash write
        reason = _system_status(dut_ip).get("ResetReason")
        result_note(f"bootloader: ResetReason {reason}")
        # The bootrom's own reboot into BOOTSEL overwrites both scratch regions, so the boot after it reads 2, no record.
        assert reason == _RR["WATCHDOG"], f"the boot after BOOTSEL read {reason}, not {_RR['WATCHDOG']}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


@pytest.mark.parametrize("mode", ["escalate", "hold_console"])
def test_the_supervisor_escalation_reboot_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]", mode: str) -> None:
    # hold_console: the host holds the port open, reading nothing, while the task keeps dying - still the budget's reboot.
    # The script's log is RAM-only, so escalate reads its entry off the rounds; hold_console prints none, and the
    # entry is pinned by tests/test_asy_system_service.py::test_the_supervisor_escalates_past_the_failure_budget.
    try:
        _evidence(board, bench, dut_ip, f"reset-reason-escalation-{mode}")
        if mode == "hold_console":
            _provoked(board, bench, "system_service_restarts_a_real_dead_task.py", hold_unread_s=3 * _WDT_TIMEOUT_MS / 1000, mode=mode)
        else:
            facts = _provoked(board, bench, "system_service_restarts_a_real_dead_task.py", mode=mode)
            assert facts.get("mode") == mode and any(key.startswith("round_") for key in facts), f"the escalation reported no round before the reset: {facts}"
            assert "starter_calls" not in facts, f"the watch ended without the budget's reboot: {facts}"
            assert _round_holds_the_budget_entry(facts), f"no round before the reset holds SYSTEM's TASK_BUDGET_REBOOT entry: {facts}"
        bits = _attributed(board, dut_ip, _RR["TASK_BUDGET"], result_note, f"supervisor escalation ({mode})")
        assert bits & _FORCED_BIT, f"the budget's machine.reset() left the forced bit clear (a 2 would be the watchdog): {bits}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


def test_the_starved_watchdog_fallback_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    try:
        _evidence(board, bench, dut_ip, "reset-reason-starve-fallback")
        facts = _provoked(board, bench, "reboot_fallback_starves_the_watchdog.py")
        assert "failure" not in facts and isinstance(facts.get("pool_timers"), int), f"the fallback's premise failed: {facts}"
        bits = _attributed(board, dut_ip, _RR["STARVE_ARM_FAILED"], result_note, "starved-watchdog fallback")
        assert bits & _TIMER_BIT and not bits & _FORCED_BIT, f"a starvation reset must set the timer bit, never the forced one: {bits}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


def test_an_invalid_record_reads_as_unknown(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    try:
        _evidence(board, bench, dut_ip, "reset-reason-invalid-record")
        facts = _provoked(board, bench, "reset_code_invalid_record.py", STATE="invalid")
        assert isinstance(facts.get("invalid_record"), list), f"the script wrote no invalid record: {facts}"
        bits = _attributed(board, dut_ip, _RR["UNKNOWN"], result_note, "invalid record")
        assert bits & _FORCED_BIT, f"the script's machine.reset() left the forced bit clear: {bits}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


@pytest.mark.provokes_log(
    "the planted EIO cuts the erase, over a scratch-config boot that logs each config file not found; each boot after it"
    " reads the blanked SGP40 backup and warns once (owner, 2026-11-06) until the first backup the test waits for,"
    " undated while NTP is unsynced",
    *scratch_config_entries(),
    ("SGP40", "W", "SGP_NO_BACKUP"),
    ("SGP40", "W", "SGP_WRITTEN_NO_TS"),
)
def test_an_incomplete_command_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    try:
        before = get_errcount(dut_ip)
        _evidence(board, bench, dut_ip, "reset-reason-command-incomplete")
        facts = _provoked(board, bench, "reset_code_command_incomplete.py")
        assert facts.get("answer") == "Valid" and isinstance(facts.get("raised_at"), int), f"the erase never reached its failing unit: {facts}"
        assert "no_reset_after_ms" not in facts, f"the board outlived the cut erase: {facts}"
        reason = _system_status(dut_ip).get("ResetReason")  # no REASON read: the errcount below needs main.py serving
        result_note(f"erase cut by an EIO: ResetReason {reason}")
        assert reason == _RR["COMMAND_INCOMPLETE"], f"the cut erase read ResetReason {reason}, not {_RR['COMMAND_INCOMPLETE']}"
        after = get_errcount(dut_ip)  # before the dump, whose exec parks main.py
        wait_until(board.is_device_present, timeout_s=_SERVING_TIMEOUT_S, description="the cut erase's reset: the board back on USB for the FRAM dump")
        save_fram_raw(board, "reset-reason-command-incomplete-after")
        # The chunks are blanked before any unit is written: each FRAM-backed log restarted, or kept what it held.
        changed = [name for name in fram_backed_logger_names() if after[name]["history"] != before[name]["history"] and after[name]["counter"] >= before[name]["counter"] > 0 and not _holds_its_boot_warning_alone(after[name])]
        assert not changed, f"a log neither restarted nor kept its saved history across the cut erase: {changed}"
    finally:
        wait_until(board.is_device_present, timeout_s=_SERVING_TIMEOUT_S, description="the cut erase's reset: the board back on USB for the scratch removal")
        board.exec(_SCRATCH_REMOVE)
        restore_board_to_serving(board, bench, dut_ip)
        _load.wait_for_sgp40_backup(dut_ip)


@pytest.mark.parametrize("phase", _BOOT_PHASES)
@pytest.mark.provokes_log(
    "phases 3-5 hang after the setups of a boot over an empty scratch config, which logs each config file not found",
    *scratch_config_entries(),
)
def test_a_hang_in_boot_phase_p_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]", phase: int) -> None:
    try:
        _evidence(board, bench, dut_ip, f"reset-reason-boot-phase-{phase}")
        facts = _provoked(board, bench, "reset_code_boot_phase_hang.py", PHASE=str(phase))
        assert facts.get("marked_phase") == phase and "hang_returned_ms" not in facts, f"phase {phase}: the hang was not reached in its phase or the board outlived it: {facts}"
        bits = _attributed(board, dut_ip, _RR["BOOT_FAILURE"] + phase, result_note, f"hang in boot phase {phase} ({facts.get('callee')})")
        assert bits & _TIMER_BIT and not bits & _FORCED_BIT, f"phase {phase}: a starvation reset must set the timer bit, never the forced one: {bits}"
    finally:
        board.exec(_SCRATCH_REMOVE)
        restore_board_to_serving(board, bench, dut_ip)


@pytest.mark.parametrize("mode", ["reboot", "entry_held", "escape"])
@pytest.mark.provokes_log(
    "the recursing reader's TASK_RAISED and the supervisor's STACK_EXHAUSTED in SYSTEM",
    ("SYSTEM", "E", "TASK_RAISED"),
    ("SYSTEM", "E", "STACK_EXHAUSTED"),
    *scratch_config_entries(),
)
def test_a_c_stack_exhaustion_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]", mode: str) -> None:
    # The reader dies of the stack check's RuntimeError; a handler records the overflow and the supervisor's next pass
    # reboots with the stack code (F.1); its entry held, the code recorded, the watchdog's reset reads 20 - in "escape",
    # recorded by no handler, the dead-task entry writes it (SPECIFICATION.md F.1).
    try:
        _evidence(board, bench, dut_ip, f"reset-reason-stack-exhausted-{mode}")
        facts = _provoked(board, bench, "reset_code_stack_exhausted.py", mode=mode)
        assert "no_reset_after_ms" not in facts and "failure" not in facts, f"{mode}: the board outlived the stack exhaustion: {facts}"
        reset = facts.get("reset")
        if mode != "reboot":
            assert facts.get("held") is True and reset is None, f"the held entry write still let the reboot arm: {facts}"
            bits = _attributed(board, dut_ip, _RR["STACK_EXHAUSTED"], result_note, f"stack exhaustion in {facts.get('reader')}, its entry held ({mode})")
            assert bits & _TIMER_BIT and not bits & _FORCED_BIT, f"a held entry's reset must be the watchdog's, the timer bit set and never the forced one: {bits}"
        else:
            assert isinstance(reset, dict) and reset.get("code") == _RR["STACK_EXHAUSTED"] and reset.get("deaths"), f"the exhaustion did not end in the stack code's reboot: {facts}"
            bits = _attributed(board, dut_ip, _RR["STACK_EXHAUSTED"], result_note, f"stack exhaustion in {facts.get('reader')} (depths {reset.get('deaths')})")
            assert bits & _FORCED_BIT, f"the supervisor's machine.reset() left the forced bit clear: {bits}"
    finally:
        board.exec(_SCRATCH_REMOVE)
        restore_board_to_serving(board, bench, dut_ip)


def test_a_console_interrupt_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    # One Ctrl-C on a freshly opened port: the firmware drops to the REPL with its watchdog armed and the watchdog resets.
    try:
        _evidence(board, bench, dut_ip, "reset-reason-console-interrupt")
        with serial.Serial(board.device, 115200, timeout=1.0) as port:
            port.write(b"\x03")
        kick_after_reset(board, bench, _WDT_TIMEOUT_MS / 1000 + _LOSS_MARGIN_S)  # the reset's USB gap, about 320 ms
        bits = _attributed(board, dut_ip, _RR_INTERRUPTED, result_note, "console interrupt")
        assert bits & _TIMER_BIT and not bits & _FORCED_BIT, f"the interrupt's watchdog reset must set the timer bit, never the forced one: {bits}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


@pytest.mark.parametrize("kind", ["exception", "base"])
def test_a_loop_ended_by_an_exception_after_boot_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]", kind: str) -> None:
    # mpremote's Ctrl-C records 21, which the script's boot clears; its loop then ends by an OSError or a SystemExit at the
    # first wait after BOOT_DONE: the entry records 22 and resets the chip at once. Normal boot, no flash write.
    try:
        _evidence(board, bench, dut_ip, f"reset-reason-loop-end-{kind}")
        facts = _provoked(board, bench, "reset_code_loop_end.py", KIND=kind, BOOT_DONE=str(_BOOT_DONE))
        # No drop-off wait: the reset is immediate. Its phase fact may be lost in rp2's CDC queue, so only a wrong one
        # fails: 22 alone proves BOOT_DONE, written only then over a record the script's boot cleared (A.7).
        assert facts.get("raised_in_phase", _BOOT_DONE) == _BOOT_DONE, f"{kind}: the loop ended in another phase: {facts}"
        bits = _attributed(board, dut_ip, _RR["LOOP_ENDED"], result_note, f"loop ended by {kind}")
        assert bits & _FORCED_BIT and not bits & _TIMER_BIT, f"{kind}: the entry's machine.reset() must set the forced bit, never the timer one: {bits}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)
