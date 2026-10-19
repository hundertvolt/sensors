"""Bench-tier automated tests: every reset code the firmware attributes, proven through GET /status's ResetReason after
the production boot serves - each test saves errcount and the raw FRAM first, records ResetBits, asserts the watchdog
half the reset kind fixes, and restores serving after. Code 1 (a power cut) is the manual power-cycle step's."""

import subprocess
import time
from typing import TYPE_CHECKING

import http_client
import pytest
import serial
from error_log_helpers import code, get_errcount, save_errcount
from harness import DEVICE_SCRIPTS_DIR, SRC_DIR, HardwareTestFailureError, fram_backed_logger_names, kick_then_reset, parse_facts, restore_board_to_serving, save_fram_raw, wait_until

from buildgen.validate import _WDT_TIMEOUT_MS, module_int_const

if TYPE_CHECKING:
    from collections.abc import Callable

    from bench_control import BenchBridge
    from harness import Board
    from http_client import JSONObject

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_12_reset_reasons",)

_SRC = "asy_system_service.py"
_RR = {name: module_int_const(SRC_DIR, _SRC, f"_RR_{name}") for name in ("UNKNOWN", "WATCHDOG", "BOOTLOADER", "TASK_BUDGET", "STARVE_ARM_FAILED", "COMMAND_INCOMPLETE", "BOOT_FAILURE")}
_RR_INTERRUPTED = module_int_const(SRC_DIR, _SRC, "RR_INTERRUPTED")
_TASK_CHECK_TIME, _RESET_DELAY = module_int_const(SRC_DIR, _SRC, "_TASK_CHECK_TIME"), module_int_const(SRC_DIR, _SRC, "_RESET_DELAY")
_TIMER_BIT, _FORCED_BIT = 0x1, 0x2  # ResetBits' watchdog half: REASON bits 0-1, TIMER and FORCE (src/asy_system_service.py)
_SCRATCH_REMOVE = "import os\nif 'hwtest-scratch' in os.listdir():\n    for n in os.listdir('hwtest-scratch/'):\n        os.remove('hwtest-scratch/' + n)\n    os.rmdir('hwtest-scratch/')\n"
# @tunable l4.reset_reasons_script_timeout_s = 120.0
_SCRIPT_TIMEOUT_S = 120.0
# @tunable l4.reset_reasons_serving_timeout_s = 90.0
_SERVING_TIMEOUT_S = 90.0
# @tunable l4.reset_reasons_serving_poll_s = 2.0
_SERVING_POLL_S = 2.0
# @tunable l4.reset_reasons_status_timeout_s = 10.0
_STATUS_TIMEOUT_S = 10.0
# @tunable l4.reset_reasons_loss_margin_s = 2.0
_LOSS_MARGIN_S = 2.0
# @tunable l4.reset_reasons_picotool_timeout_s = 30.0
_PICOTOOL_TIMEOUT_S = 30.0
_BOOT_PHASES = (1, 2, 3, 4, 5)  # asy_system_service.py's BOOT_CONSTRUCTION .. BOOT_NTP: a hang in each reads 10 + phase


def _attributed(dut_ip: str, expected: int, result_note: "Callable[[str], None]", context: str) -> int:
    # Asserts the reason, records ResetBits and returns them for the watchdog-half checks.
    system = _system_status(dut_ip)
    reason, bits = system.get("ResetReason"), system.get("ResetBits")
    result_note(f"{context}: ResetReason {reason}, ResetBits {bits}")
    assert reason == expected, f"{context}: ResetReason reads {reason}, not {expected}; ResetBits {bits}"
    assert isinstance(bits, int), f"{context}: no integer ResetBits: {system}"
    return bits


def _evidence(board: "Board", bench: "BenchBridge", dut_ip: str, name: str) -> None:
    # Errcount and the raw FRAM before the reset under test; the dump's exec parks main.py, so serving is restored.
    save_errcount(dut_ip, name)
    save_fram_raw(board, name)
    restore_board_to_serving(board, bench, dut_ip)


def _system_status(dut_ip: str) -> "JSONObject":
    # The production boot's /status system block, once it serves (passive polling only).
    wait_until(lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_STATUS_TIMEOUT_S).status_code == 200, timeout_s=_SERVING_TIMEOUT_S, poll_interval_s=_SERVING_POLL_S, description="DUT serving /status after the reset")
    system = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_STATUS_TIMEOUT_S).json().get("system")
    assert isinstance(system, dict), f"/status carries no system block: {system!r}"
    return system


def test_a_harness_hard_reset_reads_as_watchdog_without_a_record(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    try:
        _evidence(board, bench, dut_ip, "reset-reason-hard-reset")
        kick_then_reset(board, bench)  # mpremote's machine.reset() after the station kick: no record written
        bits = _attributed(dut_ip, _RR["WATCHDOG"], result_note, "harness hard reset")
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
        wait_until(lambda: not board.is_device_present(), timeout_s=bound, description="the board leaving USB after the bootloader command")
        result_note(f"reply to USB loss: {time.monotonic() - replied:.1f} s (bound {bound} s, watchdog {_WDT_TIMEOUT_MS} ms)")
        reboot = subprocess.run(["sudo", "picotool", "reboot"], capture_output=True, text=True, timeout=_PICOTOOL_TIMEOUT_S, check=False)  # sudo and picotool from the bench host's PATH
        if reboot.returncode != 0:
            raise HardwareTestFailureError(f"picotool reboot found no BOOTSEL device (exit {reboot.returncode}):\n{reboot.stdout}\n{reboot.stderr}")
        system = _system_status(dut_ip)
        reason = system.get("ResetReason")
        result_note(f"bootloader: ResetReason {reason}, ResetBits {system.get('ResetBits')}")
        # A 2 or a 1 here is the bootrom's own watchdog reboot into BOOTSEL having overwritten the scratch registers.
        assert reason == _RR["BOOTLOADER"], f"the boot after BOOTSEL read {reason}, not {_RR['BOOTLOADER']} - a 2 or 1 means the bootrom's reboot lost the record; ResetBits {system.get('ResetBits')}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


@pytest.mark.parametrize("mode", ["escalate", "hold_console"])
def test_the_supervisor_escalation_reboot_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]", mode: str) -> None:
    # hold_console: the host holds the port open, reading nothing, while the task keeps dying - still the budget's reboot.
    try:
        _evidence(board, bench, dut_ip, f"reset-reason-escalation-{mode}")
        if mode == "hold_console":
            board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_service_restarts_a_real_dead_task.py", timeout_s=_SCRIPT_TIMEOUT_S, hold_unread_s=3 * _WDT_TIMEOUT_MS / 1000, mode=mode)
        else:
            facts = parse_facts(board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_service_restarts_a_real_dead_task.py", timeout_s=_SCRIPT_TIMEOUT_S, mode=mode), allow_missing_done=True)
            assert facts.get("mode") == mode and any(key.startswith("round_") for key in facts), f"the escalation reported no round before the reset: {facts}"
            assert "starter_calls" not in facts, f"the watch ended without the budget's reboot: {facts}"
        bits = _attributed(dut_ip, _RR["TASK_BUDGET"], result_note, f"supervisor escalation ({mode})")
        assert bits & _FORCED_BIT, f"the budget's machine.reset() left the forced bit clear (a 2 would be the watchdog): {bits}"
        logged = get_errcount(dut_ip)["SYSTEM"]["history"]
        assert any(entry.get("type") == "E" and entry.get("num") == code("E", "TASK_BUDGET_REBOOT") for entry in logged), f"SYSTEM holds no escalation entry: {logged}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


def test_the_starved_watchdog_fallback_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    try:
        _evidence(board, bench, dut_ip, "reset-reason-starve-fallback")
        facts = parse_facts(board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "reboot_fallback_starves_the_watchdog.py", timeout_s=_SCRIPT_TIMEOUT_S), allow_missing_done=True)
        assert "failure" not in facts and isinstance(facts.get("pool_timers"), int), f"the fallback's premise failed: {facts}"
        bits = _attributed(dut_ip, _RR["STARVE_ARM_FAILED"], result_note, "starved-watchdog fallback")
        assert bits & _TIMER_BIT and not bits & _FORCED_BIT, f"a starvation reset must set the timer bit, never the forced one: {bits}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


def test_an_invalid_record_reads_as_unknown(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    try:
        _evidence(board, bench, dut_ip, "reset-reason-invalid-record")
        facts = parse_facts(board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "reset_code_invalid_record.py", timeout_s=_SCRIPT_TIMEOUT_S, STATE="invalid"), allow_missing_done=True)
        assert isinstance(facts.get("invalid_record"), list), f"the script wrote no invalid record: {facts}"
        bits = _attributed(dut_ip, _RR["UNKNOWN"], result_note, "invalid record")
        assert bits & _FORCED_BIT, f"the script's machine.reset() left the forced bit clear: {bits}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


def test_an_incomplete_command_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    try:
        before = get_errcount(dut_ip)
        _evidence(board, bench, dut_ip, "reset-reason-command-incomplete")
        facts = parse_facts(board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "reset_code_command_incomplete.py", timeout_s=_SCRIPT_TIMEOUT_S), allow_missing_done=True)
        assert facts.get("answer") == "Valid" and isinstance(facts.get("raised_at"), int), f"the erase never reached its failing unit: {facts}"
        _attributed(dut_ip, _RR["COMMAND_INCOMPLETE"], result_note, "erase cut by an EIO")
        save_fram_raw(board, "reset-reason-command-incomplete-after")
        after = get_errcount(dut_ip)
        # The chunks are blanked before any unit is written: each FRAM-backed log restarted, or kept what it held.
        changed = [name for name in fram_backed_logger_names() if after[name]["history"] != before[name]["history"] and after[name]["counter"] >= before[name]["counter"] > 0]
        assert not changed, f"a log neither restarted nor kept its saved history across the cut erase: {changed}"
    finally:
        board.exec(_SCRATCH_REMOVE)
        restore_board_to_serving(board, bench, dut_ip)


@pytest.mark.parametrize("phase", _BOOT_PHASES)
def test_a_hang_in_boot_phase_p_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]", phase: int) -> None:
    try:
        _evidence(board, bench, dut_ip, f"reset-reason-boot-phase-{phase}")
        facts = parse_facts(board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "reset_code_boot_phase_hang.py", timeout_s=_SCRIPT_TIMEOUT_S, PHASE=str(phase)), allow_missing_done=True)
        assert facts.get("marked_phase") == phase and "hang_returned_ms" not in facts, f"phase {phase}: the hang was not reached in its phase or the board outlived it: {facts}"
        bits = _attributed(dut_ip, _RR["BOOT_FAILURE"] + phase, result_note, f"hang in boot phase {phase} ({facts.get('callee')})")
        assert bits & _TIMER_BIT and not bits & _FORCED_BIT, f"phase {phase}: a starvation reset must set the timer bit, never the forced one: {bits}"
    finally:
        board.exec(_SCRATCH_REMOVE)
        restore_board_to_serving(board, bench, dut_ip)


def test_a_c_stack_exhaustion_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    # src/ has no code of its own for a stack exhaustion: the reader dies of the stack check's RuntimeError on every
    # restart until the supervisor's budget reboots, so the attribution is the budget's (agent, 2026-10-14).
    try:
        _evidence(board, bench, dut_ip, "reset-reason-stack-exhausted")
        facts = parse_facts(board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "reset_code_stack_exhausted.py", timeout_s=_SCRIPT_TIMEOUT_S), allow_missing_done=True)
        reset = facts.get("reset")
        assert isinstance(reset, dict) and reset.get("code") == _RR["TASK_BUDGET"] and reset.get("deaths"), f"the exhaustion did not end in the budget's reboot: {facts}"
        bits = _attributed(dut_ip, _RR["TASK_BUDGET"], result_note, f"stack exhaustion in {facts.get('reader')} (depths {reset.get('deaths')})")
        assert bits & _FORCED_BIT, f"the budget's machine.reset() left the forced bit clear: {bits}"
    finally:
        board.exec(_SCRATCH_REMOVE)
        restore_board_to_serving(board, bench, dut_ip)


def test_a_console_interrupt_is_attributed(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    # One Ctrl-C on a freshly opened port: the firmware drops to the REPL with its watchdog armed and the watchdog resets.
    try:
        _evidence(board, bench, dut_ip, "reset-reason-console-interrupt")
        with serial.Serial(board.device, 115200, timeout=1.0) as port:
            port.write(b"\x03")
        wait_until(lambda: not board.is_device_present(), timeout_s=_WDT_TIMEOUT_MS / 1000 + _LOSS_MARGIN_S, description="the watchdog reset after a console interrupt")
        bits = _attributed(dut_ip, _RR_INTERRUPTED, result_note, "console interrupt")
        assert bits & _TIMER_BIT and not bits & _FORCED_BIT, f"the interrupt's watchdog reset must set the timer bit, never the forced one: {bits}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)
