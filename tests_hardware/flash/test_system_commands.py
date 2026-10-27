"""Flash-tier automated tests: the system commands on the bench board over USB, through the webserver's dispatch into
the generated callback over a scratch config dir - the deletes, the erase and its feed gaps, the refusals and states, a
hung step, a reset mid-erase and the bootloader; each saves the FRAM evidence first, then reads the attribution."""

import json
import subprocess
import time
from typing import TYPE_CHECKING

import pytest
from error_log_helpers import code
from harness import DEVICE_SCRIPTS_DIR, MEMORY_ERROR_MARKERS, SRC_DIR, HardwareTestFailureError, fram_backed_logger_names, parse_facts, save_fram_raw, wait_for_boot, wait_until

from buildgen.validate import _WDT_TIMEOUT_MS, module_int_const

if TYPE_CHECKING:
    from collections.abc import Callable

    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_13_system_commands",)

_SCRATCH = "hwtest-scratch/"  # every command script's scratch config directory
# One exec after a scratch build that ended in a reset: the directory's files, then the directory (absent: nothing).
_REMOVE_SCRATCH = "import os\nif 'hwtest-scratch' in os.listdir():\n    for n in os.listdir('hwtest-scratch/'):\n        os.remove('hwtest-scratch/' + n)\n    os.rmdir('hwtest-scratch/')\n"
# The running firmware's attribution and every logger, read through exec_live() once its boot is done (its Ctrl-C ends
# main.py; the armed watchdog or the test's closing hard reset, whichever comes first, restarts it). The scratch listing rides along.
_READ_AFTER_BOOT = (
    "import asyncio, json, os, sys\n"
    "m = [v for k, v in sys.modules.items() if k.startswith('sensortask_') and getattr(v, 'sysfunct', None) is not None]\n"
    "async def logs():\n"
    "    out = {}\n"
    "    for s in m[0]._collect_error_sources():\n"
    "        out.update(await s.get_error_counter())\n"
    "    return out\n"
    "scratch = os.listdir('hwtest-scratch/') if 'hwtest-scratch' in os.listdir() else None\n"
    "print('AFTER ' + json.dumps({'reason': m[0].sysfunct.get_reset_reason(), 'bits': m[0].sysfunct.get_reset_bits(), 'logs': asyncio.run(logs()), 'scratch': scratch} if m else None))\n"
)
_SEED = (code("E", "TEST_SEED_A"), code("E", "TEST_SEED_B"), code("E", "TEST_SEED_C"))  # the erase script's ring
_RR_REBOOT, _RR_BOOTLOADER, _RR_CONFIG_RESET, _RR_FRAM_ERASED, _RR_COMMAND_INCOMPLETE = (module_int_const(SRC_DIR, "asy_system_service.py", name) for name in ("_RR_REBOOT", "_RR_BOOTLOADER", "_RR_CONFIG_RESET", "_RR_FRAM_ERASED", "_RR_COMMAND_INCOMPLETE"))
# The erase's own feed cadence: one feed per 256 B unit or chunk, each well under this (agent, 2026-10-14).
# @tunable l3.system_commands_erase_feed_gap_max_ms = 100
_ERASE_FEED_GAP_MAX_MS = 100
# @tunable l3.system_commands_script_timeout_s = 90.0
_SCRIPT_TIMEOUT_S = 90.0
# @tunable l3.system_commands_refusal_script_timeout_s = 120.0
_REFUSAL_SCRIPT_TIMEOUT_S = 120.0
# @tunable l3.system_commands_boot_timeout_s = 60.0
_BOOT_TIMEOUT_S = 60.0
# @tunable l3.system_commands_present_timeout_s = 30.0
_PRESENT_TIMEOUT_S = 30.0
# @tunable l3.system_commands_picotool_timeout_s = 30.0
_PICOTOOL_TIMEOUT_S = 30.0
_MID_ERASE_RESETS_MS = (200, 1000, 2000)  # inside the 256 KB erase, about 2.2 s at the 1 MHz bus
# The shutdown's four step lines, in the order SPECIFICATION.md Part A.8 runs them.
_STEP_LINES = ("Shutdown: supervisor stopped", "Shutdown: config stores closed and flushed", "Shutdown: storage quiesced", "Shutdown: supervised tasks stopped")


def _after_boot(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]") -> "dict[str, object] | None":
    # The production boot's attribution and logs; None on the twin, which boots no production image after a reset.
    if request.config.getoption("--twin"):
        result_note("twin run: no production boot follows the reset - the after-boot half is silicon's")
        return None
    wait_until(board.is_device_present, timeout_s=_PRESENT_TIMEOUT_S, description="board back on USB after the command's reset")
    wait_for_boot(board, _BOOT_TIMEOUT_S)
    output = board.exec_live(_READ_AFTER_BOOT)
    line = next((ln for ln in output.splitlines() if ln.startswith("AFTER ")), None)
    assert line is not None, f"the board printed no AFTER line:\n{output}"
    after = json.loads(line[len("AFTER ") :])
    assert isinstance(after, dict), f"no running sensortask_* module with a SystemService after the boot:\n{output}"
    result_note(f"after the boot: ResetReason {after.get('reason')}, ResetBits {after.get('bits')}")
    return after


def _attributed_reset(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]", run: "tuple[str, dict[str, object]]", script: str, expected: int) -> None:
    # A state run's reset armed with the command's own code, no feed gap reaching the watchdog, the boot reading it.
    facts = _reset_facts(*run, script, "state run")
    assert facts.get("state") != "mempause" or facts.get("mempause") == "Valid", f"{script}: the storage pause was refused, so the run reset unpaused: {facts}"
    reset = facts.get("reset")
    assert isinstance(reset, dict) and reset.get("code") == expected, f"{script}: the reset armed {reset}, not code {expected}: {facts}"
    assert isinstance(reset.get("max_gap_ms"), int) and reset["max_gap_ms"] < _WDT_TIMEOUT_MS, f"{script}: a feed gap reached the watchdog: {reset}"
    result_note(f"{script} {facts.get('state')}: {reset}")
    after = _after_boot(board, request, result_note)
    if after is not None:
        assert after.get("reason") == expected, f"{script} {facts.get('state')}: the boot read {after.get('reason')}, not {expected}: {after}"


def _clean(output: str, script: str) -> None:
    failed = [line for line in output.splitlines() if any(marker in line for marker in MEMORY_ERROR_MARKERS)]
    assert not failed, f"{script} reported an allocation failure:\n" + "\n".join(failed)


def _reset_facts(output: str, facts: "dict[str, object]", script: str, context: str) -> "dict[str, object]":
    # A command script's facts streamed before its reset: the command answered Valid, and no early end.
    _clean(output, script)
    assert "failure" not in facts and "no_reset_after_ms" not in facts, f"{script} {context}: no reset ended the run: {facts}\n{output}"
    assert facts.get("answer") == "Valid", f"{script} {context}: the command was not accepted: {facts}"
    return facts


def _restart(board: "Board") -> None:
    # The closing hard reset after the scratch cleanup's exec, waited out passively.
    board.hard_reset()
    wait_until(board.is_device_present, timeout_s=_PRESENT_TIMEOUT_S, description="board back on USB after the closing hard reset")


def _seeds(logs: "dict[str, object]") -> "dict[str, list[int]]":
    # Per logger, the test-band seed codes its history holds, oldest first.
    found: dict[str, list[int]] = {}
    for name, entry in logs.items():
        if isinstance(entry, dict):
            pairs = zip(entry.get("ErrType", []), entry.get("ErrNum", []), strict=True)
            found[name] = [num for kind, num in pairs if kind == "E" and num in _SEED]
    return found


@pytest.mark.persistence_write
def test_config_reset_deletes_every_config_file_and_reboots(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]") -> None:
    save_fram_raw(board, "config-reset")
    before = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "config_files_dump.py"))["files"]
    assert isinstance(before, dict), f"no production config dump: {before}"
    try:
        output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_command_config_reset.py", timeout_s=_SCRIPT_TIMEOUT_S)
        facts = _reset_facts(output, parse_facts(output, allow_missing_done=True), "system_command_config_reset.py", "idle")
        scratch = facts.get("scratch_files")
        production = sorted(name for name in before if not name.startswith("config_HWTEST_"))
        assert isinstance(scratch, list) and scratch and facts.get("damaged") in scratch, f"the scratch build wrote no store file to damage: {facts}"
        # Every booted board holds each store's file (its setup writes an absent one); the twin's root holds none.
        assert not production or scratch == production, f"the scratch build wrote {scratch}, the production store set is {production}: {facts}"
        after = _after_boot(board, request, result_note)
        if after is None:
            return
        assert after.get("scratch") == [], f"files survived the config reset in {_SCRATCH}, the damaged one included: {after.get('scratch')}"
        assert after.get("reason") == _RR_CONFIG_RESET, f"the config reset's reboot read {after.get('reason')}, not {_RR_CONFIG_RESET}: {after}"
        kept = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "config_files_dump.py"))["files"]
        assert kept == before, "a production config file changed across the scratch config reset"
    finally:
        board.exec(_REMOVE_SCRATCH)
        _restart(board)


def test_fram_erase_blanks_the_chip_and_every_logger_restarts_empty(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]") -> None:
    save_fram_raw(board, "before-erase")
    try:
        output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_command_fram_erase.py", timeout_s=_SCRIPT_TIMEOUT_S, STATE="idle")
        facts = _reset_facts(output, parse_facts(output, allow_missing_done=True), "system_command_fram_erase.py", "idle")
        erase, reset, layout = facts.get("erase"), facts.get("reset"), facts.get("layout")
        assert isinstance(erase, dict) and isinstance(reset, dict) and isinstance(layout, dict), f"the erase reported no figures: {facts}"
        result_note(f"erase {erase.get('ms')} ms, largest feed gap inside it {erase.get('max_gap_ms')} ms; {reset.get('feeds')} feeds, largest gap {reset.get('max_gap_ms')} ms")
        assert erase.get("ok") is True and reset.get("code") == _RR_FRAM_ERASED, f"the erase or its attribution failed: {facts}"
        assert facts.get("seeded") == sorted(fram_backed_logger_names()), f"the seeded loggers are not buildgen's FRAM-backed set: {facts.get('seeded')}"
        assert isinstance(erase.get("max_gap_ms"), int) and erase["max_gap_ms"] < _ERASE_FEED_GAP_MAX_MS, f"a feed gap inside the erase reached {erase.get('max_gap_ms')} ms: {erase}"
        assert isinstance(reset.get("max_gap_ms"), int) and reset["max_gap_ms"] < _WDT_TIMEOUT_MS, f"a feed gap reached {reset.get('max_gap_ms')} ms, past the watchdog: {reset}"
        after = _after_boot(board, request, result_note)
        if after is None:
            return
        assert after.get("reason") == _RR_FRAM_ERASED, f"the erase's reboot read {after.get('reason')}, not {_RR_FRAM_ERASED}: {after}"
        logs = after.get("logs")
        assert isinstance(logs, dict), f"no logs after the boot: {after}"
        kept = {name: seeds for name, seeds in _seeds(logs).items() if seeds}
        assert not kept, f"seeded history survived the erase: {kept}"
        dump = save_fram_raw(board, "after-erase")
        stray = _stray_bytes(dump.path.read_text(encoding="utf-8"), int(str(layout.get("allocated"))))
        assert not stray, f"non-zero FRAM above the {layout.get('allocated')} B chunk layout after the erase: {stray[:5]}"
    finally:
        board.exec(_REMOVE_SCRATCH)
        _restart(board)


def test_refused_commands_change_nothing_and_never_stop_the_feed(board: "Board") -> None:
    save_fram_raw(board, "refusals")
    try:
        output = board.run_isolated(DEVICE_SCRIPTS_DIR / "system_command_fram_erase.py", timeout_s=_REFUSAL_SCRIPT_TIMEOUT_S, STATE="refusals")
        _clean(output, "system_command_fram_erase.py")
        facts = parse_facts(output)
        near = facts.get("near_misses")
        assert isinstance(near, list) and near and all(answer == "Invalid" for _word, answer in near), f"a near-miss word was not answered Invalid: {near}"
        assert facts.get("protect") is True and facts.get("protected_answer") == "Failed", f"the erase of a write-protected chip was not refused: {facts}"
        assert facts.get("survived_unfed_ms") is not None and facts.get("unprotect") is True, f"the board did not run on unfed past the refusal, or the chip stayed protected: {facts}"
    finally:
        board.exec(_REMOVE_SCRATCH)
        _restart(board)


def _stray_bytes(dump_text: str, allocated: int) -> "list[str]":
    # The raw dump's lines holding a non-zero byte above the build's chunk layout (an all-zero piece is never printed).
    stray: list[str] = []
    for line in dump_text.splitlines():
        if line.startswith("FRAM "):
            _tag, address, data = line.split()
            if any(bytes.fromhex(data)[max(0, allocated - int(address, 16)) :]):
                stray.append(address)
    return stray


@pytest.mark.parametrize("state", ["loads", "mempause"])
def test_an_erase_with_a_write_and_a_bus_session_in_flight_or_a_pause_still_resets_attributed(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]", state: str) -> None:
    save_fram_raw(board, f"erase-{state}")
    try:
        output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_command_fram_erase.py", timeout_s=_SCRIPT_TIMEOUT_S, STATE=state)
        _attributed_reset(board, request, result_note, (output, parse_facts(output, allow_missing_done=True)), "system_command_fram_erase.py", _RR_FRAM_ERASED)
    finally:
        board.exec(_REMOVE_SCRATCH)
        _restart(board)


def test_a_reboot_with_storage_paused_still_resets_attributed(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]") -> None:
    save_fram_raw(board, "reboot-mempause")
    try:
        output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_command_reboot.py", timeout_s=_SCRIPT_TIMEOUT_S, COMMAND="reboot", STATE="mempause")
        _attributed_reset(board, request, result_note, (output, parse_facts(output, allow_missing_done=True)), "system_command_reboot.py", _RR_REBOOT)
    finally:
        board.exec(_REMOVE_SCRATCH)
        _restart(board)


@pytest.mark.persistence_write
@pytest.mark.parametrize("command", ["resetconfig", "reboot"])
def test_a_hung_shutdown_step_ends_in_a_watchdog_reset(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]", command: str) -> None:
    # A fed hang never resets and the 4 s reset timer arms only after the hung step: a reset read as "command incomplete"
    # is the watchdog's, since only the record written as the command passed the gate holds that code (the run cannot time the loss).
    save_fram_raw(board, f"hang-{command}")
    try:
        started = time.monotonic()
        output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_command_hang.py", timeout_s=_SCRIPT_TIMEOUT_S, COMMAND=command)
        elapsed = time.monotonic() - started
        _clean(output, "system_command_hang.py")
        facts = parse_facts(output, allow_missing_done=True)
        hang = next((line for line in output.splitlines() if line.startswith("HANG ")), None)
        assert facts.get("answer") == "Valid" and hang is not None, f"{command}: the command or its hang never ran: {facts}\n{output}"
        assert "no_reset_after_ms" not in facts and "failure" not in facts, f"{command}: the board outlived the hang: {facts}"
        result_note(f"{command}: run {elapsed:.1f} s, the hang entered {hang.split()[1]} ms into the script")
        after = _after_boot(board, request, result_note)
        if after is not None:
            assert after.get("reason") == _RR_COMMAND_INCOMPLETE, f"{command}: the hang's reset read {after.get('reason')}, not {_RR_COMMAND_INCOMPLETE} (the watchdog after acceptance): {after}"
    finally:
        board.exec(_REMOVE_SCRATCH)
        _restart(board)


@pytest.mark.parametrize("after_ms", _MID_ERASE_RESETS_MS)
def test_a_reset_mid_erase_leaves_every_chunk_old_or_blank(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]", after_ms: int) -> None:
    save_fram_raw(board, f"mid-erase-{after_ms}")
    try:
        output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_command_fram_erase.py", timeout_s=_SCRIPT_TIMEOUT_S, STATE=f"reset_after_{after_ms}")
        _clean(output, "system_command_fram_erase.py")
        facts = parse_facts(output, allow_missing_done=True)
        assert "ERASE START" in output.splitlines() and "erase" not in facts, f"the reset did not land inside the erase: {facts}\n{output}"
        after = _after_boot(board, request, result_note)
        if after is None:
            return
        logs = after.get("logs")
        assert isinstance(logs, dict), f"no logs after the boot: {after}"
        torn = {name: seeds for name, seeds in _seeds(logs).items() if seeds and seeds[-len(_SEED) :] != list(_SEED)}
        result_note(f"reset {after_ms} ms into the erase: kept {sorted(n for n, s in _seeds(logs).items() if s)}")
        assert not torn, f"a chunk holds neither its seeded ring nor nothing after a reset {after_ms} ms into the erase: {torn}"
    finally:
        board.exec(_REMOVE_SCRATCH)
        # The cut erase leaves seeded rings behind: one whole erase blanks them, so no test-band entry outlives the test.
        if not request.config.getoption("--twin"):
            _restart(board)
            board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_command_fram_erase.py", timeout_s=_SCRIPT_TIMEOUT_S, STATE="idle")
            board.exec(_REMOVE_SCRATCH)
        _restart(board)


def test_bootloader_command_shuts_down_then_enters_bootsel(board: "Board", request: pytest.FixtureRequest, result_note: "Callable[[str], None]") -> None:
    save_fram_raw(board, "bootloader")
    try:
        output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "system_command_reboot.py", timeout_s=_SCRIPT_TIMEOUT_S, COMMAND="bootloader", STATE="idle")
        facts = _reset_facts(output, parse_facts(output, allow_missing_done=True), "system_command_reboot.py", "bootloader")
        steps = [next((n for n, line in enumerate(output.splitlines()) if step in line), -1) for step in _STEP_LINES]
        assert -1 not in steps and steps == sorted(steps), f"the shutdown's step lines are missing or out of order ({steps}):\n{output}"
        reset = facts.get("reset")
        assert isinstance(reset, dict) and reset.get("code") == _RR_BOOTLOADER, f"the bootloader command armed {reset}: {facts}"
        result_note(f"bootloader: {reset}")
        if request.config.getoption("--twin"):
            return
        # picotool answers only a BOOTSEL device: its reboot proves the bootloader was entered; no load, no flash write.
        reboot = subprocess.run(["sudo", "picotool", "reboot"], capture_output=True, text=True, timeout=_PICOTOOL_TIMEOUT_S, check=False)  # sudo and picotool from the bench host's PATH
        if reboot.returncode != 0:
            raise HardwareTestFailureError(f"picotool reboot found no BOOTSEL device (exit {reboot.returncode}):\n{reboot.stdout}\n{reboot.stderr}")
        after = _after_boot(board, request, result_note)
        assert after is not None and after.get("reason") == _RR_BOOTLOADER, f"the boot after BOOTSEL read {after}, not {_RR_BOOTLOADER}"
    finally:
        board.exec(_REMOVE_SCRATCH)
        _restart(board)
