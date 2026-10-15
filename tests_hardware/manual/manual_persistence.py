"""Manual tests, an execution mode of L4 (manual/runner.py): genuine power loss, which neither reset mechanism of the
automated tiers reproduces - what the bench board's FRAM (its part read from the bench TOML at run time), its flash
filesystem and the SCD30's NVM keep across a supply cut, and what a cut in the middle of a write or a command leaves."""

import ast
import re
from typing import TYPE_CHECKING

from error_log_helpers import get_errcount, save_errcount
from harness import DEVICE_SCRIPTS_DIR, SRC_DIR, Board, device_toml, fram_backed_logger_names, parse_facts, save_fram_raw, wait_until
from runner import confirm, confirm_pass, countdown, dut_ip, observe, print_instruction, put_by_hand, record_assertion, register, rest_get

if TYPE_CHECKING:
    from http_client import JSONObject, JSONValue

from buildgen.validate import module_int_const

# @tunable l4.manual_persistence_power_cut_window_s = 20
_POWER_CUT_WINDOW_S = 20
# @tunable l4.manual_persistence_power_off_s = 10
_POWER_OFF_S = 10
# @tunable l4.manual_persistence_serving_timeout_s = 120.0
_SERVING_TIMEOUT_S = 120.0
# @tunable l4.manual_persistence_script_timeout_s = 180.0
_SCRIPT_TIMEOUT_S = 180.0
_POWER_ON_BIT = 0x100  # ResetBits' CHIP_RESET HAD_POR (src/asy_system_service.py's _CHIP_RESET_BITS)
_RUN_BIT = 0x10000  # ResetBits' CHIP_RESET HAD_RUN
_MID_WRITE_ROUNDS = 3
_RR_POWER_ON, _RR_REBOOT = (module_int_const(SRC_DIR, "asy_system_service.py", name) for name in ("_RR_POWER_ON", "_RR_REBOOT"))
# The running firmware's attribution, read over USB: after a cut config reset the board may serve on its hotspot only.
_READ_REASON = "import sys\nm = [v for k, v in sys.modules.items() if k.startswith('sensortask_') and getattr(v, 'sysfunct', None) is not None]\nprint('REASON', m[0].sysfunct.get_reset_reason() if m else None)\n"


def _boot_sends_continuous_measurement() -> bool:
    # Whether src/asy_scd30_driver.py's setup() reaches the 0x0010 command, read from the source at execution.
    tree = ast.parse((SRC_DIR / "asy_scd30_driver.py").read_text(encoding="utf-8"))
    calls = {fn.name: {n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "") for n in ast.walk(fn) if isinstance(n, ast.Call)} for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)}
    names = {fn.name for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef) and any(isinstance(n, ast.Name) and n.id == "_CMD_CONTINUOUS_MEASUREMENT" for n in ast.walk(fn))}
    grown = True
    while grown:
        reaching = {name for name, called in calls.items() if called & names}
        grown = not reaching <= names
        names |= reaching
    return "setup" in names


def _fram_part() -> str:
    # The bench board's FRAM part, from the comment line its TOML carries under the fram instance.
    match = re.search(r'driver = "fram"[^\[]*?#\s*(MB85\w+)', device_toml().read_text(encoding="utf-8"))
    return match.group(1) if match else "the FRAM part its TOML names"


def _get(path: str, module: str, field: str) -> "JSONValue":
    block = rest_get(path).get(module)
    assert isinstance(block, dict), f"GET {path} carries no {module} entry"
    return block.get(field)


def _power_cycle(context: str) -> "JSONObject":
    # The genuine cut: power off for a while, back on, then the board serving again; its attribution recorded.
    amb_before = _get("/sensors", "SCD30", "AmbPres")
    print_instruction(f"Now physically remove the board's power (unplug USB or the bench supply - NOT a reset button). You have {_POWER_CUT_WINDOW_S:g} seconds.")
    countdown(_POWER_CUT_WINDOW_S, "Cut power to the board now")
    countdown(_POWER_OFF_S, "Keep power off")
    print_instruction("Now restore power.")
    confirm("Press Enter once power is restored")
    return _served_after_power(context, amb_before)


def _served_after_power(context: str, amb_before: object) -> "JSONObject":
    wait_until(lambda: bool(rest_get("/status")), timeout_s=_SERVING_TIMEOUT_S, description=f"the DUT serving after the power cut ({context})")
    system = rest_get("/status").get("system")
    assert isinstance(system, dict), "GET /status carries no system block"
    bits = system.get("ResetBits")
    amb_after = _get("/sensors", "SCD30", "AmbPres")
    sends = "sends" if _boot_sends_continuous_measurement() else "does not send"
    print_instruction(f"{context}: ResetReason {system.get('ResetReason')}, ResetBits {bits} (power-on bit {_POWER_ON_BIT}); SCD30 AmbPres {amb_before} -> {amb_after}, and the product's boot {sends} 0x0010.")
    record_assertion()
    assert system.get("ResetReason") == _RR_POWER_ON, f"{context}: the boot after the cut read ResetReason {system.get('ResetReason')}, not {_RR_POWER_ON}"
    return system


def _write_word(path: str, field: str, value: "JSONValue", module: str = "") -> str:
    # One field written by the operator, flat (/notification, /system) or under its module (/sensors); the word reported.
    return put_by_hand(path, {module: {field: value}} if module else {field: value})


@register(
    "real_fram_persistence_across_power_cycle",
    "Cut power to the board after the SGP40's FRAM-backed algorithm backup has been written, then restore it: the boot restores that backup (GET /status's SGP40 RestoreTS equals the BackupTS read before) - the bench FRAM's dual-copy and CRC contents across a genuine supply loss.",
    "[USB+WiFi][MANUAL]",
)
def test_real_fram_persistence_across_power_cycle() -> None:
    print_instruction(f"The bench board's FRAM is the {_fram_part()} (its datasheet under datasheets/fram/).")
    backup = _get("/status", "sensors", "SGP40")
    assert isinstance(backup, dict), f"GET /status carries no SGP40 maintenance block: {backup}"
    print_instruction(f"SGP40 BackupTS now {backup.get('BackupTS')} (None until the first backup period has passed: wait for one, then rerun).")
    record_assertion()
    assert backup.get("BackupTS"), "no SGP40 backup written yet - there is nothing FRAM-backed to carry across the cut"
    _power_cycle("SGP40 backup")
    restored = _get("/status", "sensors", "SGP40")
    assert isinstance(restored, dict) and restored.get("RestoreTS") == backup.get("BackupTS"), f"the boot restored {restored}, not the backup of {backup.get('BackupTS')}"
    confirm_pass(f"RestoreTS {restored.get('RestoreTS')} equals the BackupTS read before the cut - confirm? [y/N]")


@register(
    "real_flash_config_across_power_cycle",
    "A flash filesystem write (the notification module's config_NOTIFY.cfg) across a genuine power cut: WarnCO2 read, changed, the board's power cut and restored, read back, then put back to its prior value.",
    "[USB+WiFi][MANUAL]",
)
def test_real_flash_config_across_power_cycle() -> None:
    prior = rest_get("/notification").get("WarnCO2")
    changed = int(str(prior)) + 1
    print_instruction(f"WarnCO2 reads {prior}; you write {changed} (one flash filesystem write) and put {prior} back after (one more).")
    confirm("Press Enter to spend that write")
    record_assertion()
    assert _write_word("/notification", "WarnCO2", changed) == "Valid", "the WarnCO2 write was not answered Valid"
    _power_cycle("WarnCO2")
    after = rest_get("/notification").get("WarnCO2")
    restored = _write_word("/notification", "WarnCO2", prior)
    assert after == changed and restored in ("Valid", "Unchanged"), f"WarnCO2 read {after} after the cut (wrote {changed}); restoring {prior} answered {restored}"
    confirm_pass()


@register(
    "real_scd30_nvm_persistence_across_power_cycle",
    "The SCD30's own NVM across a genuine power cut: MeasInterval read, set to a different value, power cut and restored (the SCD30 too), read back, then put back - two SCD30 NVM writes, stated before they run.",
    "[USB+WiFi][MANUAL]",
)
def test_real_scd30_nvm_persistence_across_power_cycle() -> None:
    prior = _get("/sensors", "SCD30", "MeasInterval")
    changed = int(str(prior)) + 1
    print_instruction(f"MeasInterval reads {prior}; you set {changed} and put {prior} back after: two SCD30 NVM writes.")
    confirm("Press Enter to spend them")
    record_assertion()
    assert _write_word("/sensors", "MeasInterval", changed, "SCD30") == "Valid", "setting MeasInterval was not answered Valid"
    _power_cycle("SCD30 MeasInterval")
    after = _get("/sensors", "SCD30", "MeasInterval")
    restored = _write_word("/sensors", "MeasInterval", prior, "SCD30")
    assert after == changed and restored in ("Valid", "Unchanged"), f"MeasInterval read {after} after the cut (set {changed}); restoring {prior} answered {restored}"
    confirm_pass()


@register(
    "genuine_power_loss_mid_config_write",
    "Cut USB power while a scratch config file is being rewritten (config_write_loop_scratch.py prints WROTE <n> <value> after each write), three times: the read-back finds the file parsing and holding the last reported value or the one before, never a truncated or mixed file.",
    "[USB][MANUAL]",
)
def test_genuine_power_loss_mid_config_write() -> None:
    board = Board()
    for scratch in ("config_write_loop_scratch.py", "config_scratch_readback.py"):
        record_assertion()
        assert (DEVICE_SCRIPTS_DIR / scratch).is_file(), f"device_scripts/{scratch} is not in this tree yet"
    for n in range(1, _MID_WRITE_ROUNDS + 1):
        print_instruction(f"Round {n}/{_MID_WRITE_ROUNDS}: the script spends up to 20 scratch flash writes and one removal. Cut USB power while its WROTE lines arrive.")
        confirm("Press Enter to start it, your hand on the USB cable")
        output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "config_write_loop_scratch.py", timeout_s=_SCRIPT_TIMEOUT_S)
        written = [line.split()[2] for line in output.splitlines() if line.startswith("WROTE ")]
        parse_facts(output, allow_missing_done=True)
        print_instruction("Restore power.")
        confirm("Press Enter once power is restored")
        _served_after_power(f"round {n}", None)
        facts = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "config_scratch_readback.py"))
        print_instruction(f"Written before the cut: {written[-2:]}; read back: {facts}")
        confirm_pass("Does the file parse and hold the last reported value or the one before? [y/N]")


@register(
    "power_loss_during_the_shutdown_commands",
    "Cut power 2.5-4.0 s after erasefram is answered, then after resetconfig is (the config files saved first and written back after): each FRAM-backed history comes back old or empty, the board boots, nothing is left half-done.",
    "[USB+WiFi][MANUAL]",
)
def test_power_loss_during_the_shutdown_commands() -> None:
    board = Board()
    before = get_errcount(dut_ip())
    save_errcount(dut_ip(), "manual-erase-power-cut")
    save_fram_raw(board, "manual-erase-power-cut")
    board.hard_reset()
    wait_until(lambda: bool(rest_get("/status")), timeout_s=_SERVING_TIMEOUT_S, description="the DUT serving after the evidence dump")
    confirm("Press Enter to send erasefram, your hand on the USB cable")
    record_assertion()
    assert _write_word("/system", "SystemCmd", "erasefram") == "Valid", "erasefram was not answered Valid"
    countdown(3, "Cut power at the end of this count (2.5-4.0 s after the answer)")
    countdown(_POWER_OFF_S, "Keep power off, then restore it")
    confirm("Press Enter once power is restored")
    _served_after_power("erasefram cut", None)
    after = get_errcount(dut_ip())
    torn = [name for name in fram_backed_logger_names() if after[name]["history"] != before[name]["history"] and after[name]["counter"] >= before[name]["counter"] > 0]
    assert not torn, f"logs neither old nor restarted after the cut erase: {torn}"
    saved = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "config_files_dump.py"))["files"]
    assert isinstance(saved, dict) and saved, f"no config file saved before the config reset: {saved}"
    board.hard_reset()
    wait_until(lambda: bool(rest_get("/status")), timeout_s=_SERVING_TIMEOUT_S, description="the DUT serving after the config dump")
    confirm("Press Enter to send resetconfig, your hand on the USB cable")
    assert _write_word("/system", "SystemCmd", "resetconfig") == "Valid", "resetconfig was not answered Valid"
    countdown(3, "Cut power at the end of this count (2.5-4.0 s after the answer)")
    countdown(_POWER_OFF_S, "Keep power off, then restore it")
    confirm("Press Enter once power is restored and the board has booted (it may serve its hotspot only)")
    reason = next((line.split()[1] for line in board.exec(_READ_REASON).splitlines() if line.startswith("REASON ")), None)
    print_instruction(f"resetconfig cut: ResetReason {reason} (read over USB). Next: config_files_restore.py rewrites the saved config files once, one flash write per file.")
    confirm("Press Enter to write them back")
    restored = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "config_files_restore.py", files=[f"{name}:{text}" for name, text in saved.items()]))
    board.hard_reset()
    assert reason == str(_RR_POWER_ON) and restored.get("written") == sorted(saved), f"ResetReason {reason} after the cut; the restore wrote {restored.get('written')}"
    confirm_pass("Is the board serving on the bench network again with its saved settings? [y/N]")


@register(
    "power_loss_mid_scd30_nvm_write",
    "Cut power while the SCD30's interval is being rewritten (scd30_argument_reaction.py, STATE interval_write_loop: up to 21 SCD30 NVM writes, the 20 changes and the restore): the SCD30 answers after the boot and MeasInterval reads the last value written or the one before, never another.",
    "[USB+WiFi][MANUAL]",
)
def test_power_loss_mid_scd30_nvm_write() -> None:
    board = Board()
    prior = _get("/sensors", "SCD30", "MeasInterval")
    print_instruction(f"MeasInterval reads {prior}. The script spends up to 21 SCD30 NVM writes (20 changes and the restore). Cut USB power while its WROTE lines arrive.")
    confirm("Press Enter to start it, your hand on the USB cable")
    output = board.run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "scd30_argument_reaction.py", timeout_s=_SCRIPT_TIMEOUT_S, STATE="interval_write_loop")
    parse_facts(output, allow_missing_done=True)
    written = [int(line.split()[2]) for line in output.splitlines() if line.startswith("WROTE ")]
    print_instruction("Restore power.")
    confirm("Press Enter once power is restored")
    _served_after_power("SCD30 interval loop", None)
    ts = _get("/measurements", "SCD30", "TS")
    countdown(3 * int(str(prior)), "Waiting three measurement intervals for a fresh SCD30 reading")
    after = _get("/sensors", "SCD30", "MeasInterval")
    record_assertion()
    assert _get("/measurements", "SCD30", "TS") != ts, "the SCD30 gave no fresh reading within three intervals"
    assert after in written[-2:], f"MeasInterval reads {after}, neither of the last two written {written[-2:]}"
    restored = _write_word("/sensors", "MeasInterval", prior, "SCD30")
    assert restored in ("Valid", "Unchanged"), f"putting MeasInterval {prior} back answered {restored} (one more NVM write)"
    confirm_pass()


@register(
    "run_pin_reset_keeps_or_clears_the_record",
    "Whether mem_backup() survives a RUN-pin reset: reset_code_invalid_record.py writes a valid record (code 3) and waits; the operator grounds RUN briefly; ResetReason 3 after the boot means it survives, 1 or 0 that it does not, and ResetBits should show the RUN bit.",
    "[USB+WiFi][MANUAL]",
)
def test_run_pin_reset_keeps_or_clears_the_record() -> None:
    if observe("Can you reach the board's RUN pin? Answer 'yes', or 'not run' to record that it was not:") != "yes":
        return
    print_instruction("When you press Enter the script writes the record and waits 60 s: within that, connect RUN to GND briefly.")
    confirm("Press Enter to start it")
    output = Board().run_isolated_expect_reset(DEVICE_SCRIPTS_DIR / "reset_code_invalid_record.py", timeout_s=_SCRIPT_TIMEOUT_S, STATE="valid_record_wait")
    facts = parse_facts(output, allow_missing_done=True)
    wait_until(lambda: bool(rest_get("/status")), timeout_s=_SERVING_TIMEOUT_S, description="the DUT serving after the RUN-pin reset")
    system = rest_get("/status").get("system")
    assert isinstance(system, dict), "GET /status carries no system block"
    reason, bits = system.get("ResetReason"), system.get("ResetBits")
    survives = "survives" if reason == _RR_REBOOT else "does not survive"
    print_instruction(f"ResetReason {reason}, ResetBits {bits} (RUN bit {_RUN_BIT}): mem_backup() {survives} a RUN-pin reset; script facts {facts}.")
    record_assertion()
    assert "run_not_pressed" not in facts, "RUN was not pressed within the script's wait"
    confirm_pass("Record those two figures in the round's notes - done? [y/N]")
