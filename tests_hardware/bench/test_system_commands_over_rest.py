"""Bench-tier automated tests: the system commands over REST on the bench network - the config reset with its files
saved first and written back after, the FRAM erase with its evidence first, the near misses, and commands raced against
each other; each reads the board's log across the window through the shared markers and restores serving after."""

import threading
import time
from typing import TYPE_CHECKING

import _load
import evidence
import http_client
import pytest
from error_log_helpers import code, errcount_entry, get_errcount, save_errcount
from harness import DEVICE_SCRIPTS_DIR, MEMORY_ERROR_MARKERS, REPO_ROOT, SRC_DIR, HardwareTestFailureError, crash_lines, dut_hostname_candidates, fram_backed_logger_names, hotspot_password, kick_after_reset, observe_during, parse_facts, picotool, restore_board_to_serving, save_fram_raw, wait_until

from buildgen.validate import module_int_const

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from bench_control import BenchBridge
    from harness import Board, _Note
    from http_client import JSONObject, JSONValue

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_1_reformat_relaunch", "ci_suite._run_13_config_reset", "ci_suite._run_13_erase_fram", "ci_suite._run_13_near_misses", "scenarios.erasefram_concurrent_with_a_reboot_accepts_exactly_one", "scenarios.reboot_and_bootloader_at_once_accept_exactly_one", "scenarios.reset_errors_while_a_command_owns_the_reset_is_refused_and_clears_nothing")

_SRC = "asy_system_service.py"
_RR_WATCHDOG, _RR_REBOOT, _RR_CONFIG_RESET, _RR_FRAM_ERASED = (module_int_const(SRC_DIR, _SRC, name) for name in ("_RR_WATCHDOG", "_RR_REBOOT", "_RR_CONFIG_RESET", "_RR_FRAM_ERASED"))
_SAVED_SET = "config-files-before-reset.txt"  # the dump's verbatim output, under each run's evidence directory
# Whole-string equality is the dispatch's one check: each of these is one edit away from a command word.
_NEAR_MISSES = ("Reboot", "reboot ", "REBOOT", "erase", "erasefram!", "eraseFRAM", "resetConfig", "boot", "", "mempause1", 1, None)
_SHUTDOWN_WORDS = ("erasefram", "reboot", "bootloader")  # the commands that end in a reset of the board's own (or BOOTSEL)
_PUT_TIMEOUT_S = 10.0
_SERVING_TIMEOUT_S = 120.0
_SERVING_POLL_S = 2.0
_HOTSPOT_UP_S = 60.0
_PICOTOOL_TIMEOUT_S = 30.0
# The shutdown closes the listener once the supervisor parks, 0-2 s after the acceptance: a ResetErrors arriving later
# meets a closed socket, and the test reboots once more for it (agent, 2026-11-06).
_WINDOW_TRIES = 3


def _command(dut_ip: str, word: "JSONValue") -> str:
    answer = http_client.fetch(dut_ip, 80, "PUT", "/system", {"SystemCmd": word}, timeout_s=_PUT_TIMEOUT_S).json()
    result = answer.get("result")
    return str(result.get("SystemCmd")) if isinstance(result, dict) else f"no result: {answer}"


def _get(dut_ip: str, path: str) -> "JSONObject":
    return http_client.fetch(dut_ip, 80, "GET", path, timeout_s=_PUT_TIMEOUT_S).json()


def _join_hotspot(bench: "BenchBridge", ssid: str) -> None:
    # The rebooting DUT's hotspot joined once it is up: each attempt frees the radio and joins, retried to the bound.
    deadline = time.monotonic() + _HOTSPOT_UP_S
    while True:
        try:
            bench.join_dut_hotspot(ssid, hotspot_password())
        except HardwareTestFailureError:
            if time.monotonic() > deadline:
                raise
            time.sleep(_SERVING_POLL_S)
        else:
            return


def _kicked(board: "Board", bench: "BenchBridge", answers: "dict[str, str]") -> "tuple[dict[str, str], float]":
    # The answers by word and when they came, returned once a shutdown answered Valid has taken the board off USB (its
    # reset, or BOOTSEL) and the stale station entry that leaves is kicked; with no such answer, at once.
    replied = time.monotonic()
    if "Valid" in (answers.get(word) for word in _SHUTDOWN_WORDS):
        kick_after_reset(board, bench, _SERVING_TIMEOUT_S)
    return answers, replied


def _marked(lines: "list[str]", context: str) -> None:
    found = crash_lines(lines) + [line for line in lines if any(marker in line for marker in MEMORY_ERROR_MARKERS)]
    assert not found, f"{context}: a traceback or an allocation failure in the board's log:\n" + "\n".join(found)


def _newest_saved_set() -> "Path | None":
    # An aborted earlier run's saved files: the newest dump any run's evidence holds.
    saved = sorted((REPO_ROOT / "build" / "archive").rglob(_SAVED_SET.replace(".txt", "*.txt")), key=lambda p: p.stat().st_mtime)
    return saved[-1] if saved else None


def _race(dut_ip: str, words: "tuple[str, ...]") -> "dict[str, str]":
    # Every word PUT at once from its own thread; each answer by word, a failed request recorded as its answer.
    answers: dict[str, str] = {}

    def put(word: str) -> None:
        try:
            answers[word] = _command(dut_ip, word)
        except (OSError, http_client.HTTP_ERROR) as exc:
            answers[word] = f"request failed: {exc!r}"

    threads = [threading.Thread(target=put, args=(word,), name=f"race-{word}") for word in words]
    try:
        for thread in threads:
            thread.start()
    finally:
        for thread in threads:
            if thread.ident is not None:
                thread.join(_PUT_TIMEOUT_S * 2)
    return answers


def _serving_status(dut_ip: str, started: float, result_note: "Callable[[str], None]", context: str, boot_before: "JSONValue") -> "JSONObject":
    # The system block once a boot other than the one read before the command serves (the one the command has not reset
    # yet answers 200 too, with its old ResetReason), its reply-to-serving time recorded.
    wait_until(lambda: _system(dut_ip).get("BootSignature") != boot_before, timeout_s=_SERVING_TIMEOUT_S, poll_interval_s=_SERVING_POLL_S, description=f"a new boot serving after {context}")
    system = _system(dut_ip)
    result_note(f"{context}: serving {time.monotonic() - started:.1f} s after the reply; ResetReason {system.get('ResetReason')}")
    return system


def _system(dut_ip: str) -> "JSONObject":
    system = _get(dut_ip, "/status").get("system")
    assert isinstance(system, dict), f"/status carries no system block: {system!r}"
    return system


@pytest.mark.persistence_write
def test_config_reset_over_rest_brings_back_the_defaults(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "_Note") -> None:
    networking = _get(dut_ip, "/networking")
    save_errcount(dut_ip, "config-reset")
    saved: dict[str, object] = {}
    try:
        output = board.run_isolated(DEVICE_SCRIPTS_DIR / "config_files_dump.py")
        newest = _newest_saved_set()
        if not parse_facts(output)["files"] and newest is not None:
            # A board holding no config file is an aborted earlier run's: its newest saved set goes back first.
            result_note(f"no config file on the board: restored the saved set {newest} first", recovery=True)
            files = parse_facts(newest.read_text(encoding="utf-8"))["files"]
            assert isinstance(files, dict), f"the saved set {newest} holds no files fact"
            board.run_isolated(DEVICE_SCRIPTS_DIR / "config_files_restore.py", files=[f"{name}:{text}" for name, text in files.items()])
            output = board.run_isolated(DEVICE_SCRIPTS_DIR / "config_files_dump.py")
        files = parse_facts(output)["files"]
        assert isinstance(files, dict) and files, f"no config file to save before the reset: {files}"
        saved = files
        evidence.save_text(_SAVED_SET, output)
        restore_board_to_serving(board, bench, dut_ip)
        boot = _system(dut_ip).get("BootSignature")
        answer, lines = observe_during(board, lambda: _command(dut_ip, "resetconfig"))
        _marked(lines, "the config reset")
        assert answer == "Valid", f"resetconfig was answered {answer}"
        hostname = dut_hostname_candidates()[0]
        _join_hotspot(bench, hostname)
        wait_until(lambda: bool(bench.gateway_ip()), timeout_s=_HOTSPOT_UP_S, description="a lease and a gateway on the DUT's hotspot")
        gateway = bench.gateway_ip()
        system, net = _serving_status(gateway, time.monotonic(), result_note, "the config reset", boot), _get(gateway, "/networking")
        assert system.get("ResetReason") == _RR_CONFIG_RESET and system.get("ConfigFaults") == [], f"the reset read {system}"
        assert net.get("Hostname") == hostname and net.get("SSID") == "", f"the defaults did not come back: {net}"
        assert _get(gateway, "/system").get("DebugLevel") == 0, "DebugLevel is not its default 0 after the reset"
        after = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "config_files_dump.py"))["files"]
        assert isinstance(after, dict) and sorted(after) == sorted(saved), f"the reboot did not write every store's file once: {sorted(after) if isinstance(after, dict) else after}"
    finally:
        bench.leave_dut_hotspot_and_restore_bridge()
        try:
            if saved:
                restored = parse_facts(board.run_isolated(DEVICE_SCRIPTS_DIR / "config_files_restore.py", files=[f"{name}:{text}" for name, text in saved.items()]))
                assert restored.get("written") == sorted(saved), f"the restore wrote {restored.get('written')}, not {sorted(saved)}"
        finally:
            restore_board_to_serving(board, bench, dut_ip)
    back = _get(dut_ip, "/networking")
    assert (back.get("SSID"), back.get("Hostname")) == (networking.get("SSID"), networking.get("Hostname")), f"the restored board serves {back}, not {networking}"


def test_fram_erase_over_rest_blanks_every_error_log(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    save_errcount(dut_ip, "erase-over-rest")
    try:
        save_fram_raw(board, "erase-over-rest")
        restore_board_to_serving(board, bench, dut_ip)
        boot = _system(dut_ip).get("BootSignature")
        (answers, replied), lines = observe_during(board, lambda: _kicked(board, bench, {"erasefram": _command(dut_ip, "erasefram")}))
        _marked(lines, "the FRAM erase")
        assert answers["erasefram"] == "Valid", f"erasefram was answered {answers['erasefram']}"
        system = _serving_status(dut_ip, replied, result_note, "the FRAM erase", boot)
        # A 2 here is the watchdog having reset the board mid-sequence, never the erase's own reboot.
        assert system.get("ResetReason") == _RR_FRAM_ERASED, f"the erase's reboot read {system.get('ResetReason')}, not {_RR_FRAM_ERASED}"
        counts, owed = get_errcount(dut_ip), {name: (1, [("W", code("W", "SGP_NO_BACKUP"))]) for name in _load.instance_loggers("sgp40")}
        kept = {name: counts[name] for name in fram_backed_logger_names() if (counts[name]["counter"], [(h.get("type"), h.get("num")) for h in counts[name]["history"] if h.get("type") != "N"]) not in ((0, []), owed.get(name))}
        assert not kept, f"FRAM-backed logs not blank after the erase, each SGP40's W SGP_NO_BACKUP for its blank backup chunk aside: {kept}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


def test_reset_errors_after_an_accepted_reboot_is_refused_and_clears_nothing(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "_Note") -> None:
    # Saved before any ResetErrors (CLAUDE.md); one is sent only once the reboot answered Valid, inside its shutdown.
    before = get_errcount(dut_ip)
    save_errcount(dut_ip, "reset-errors-after-reboot")
    answer = ""
    try:
        for attempt in range(1, _WINDOW_TRIES + 1):
            boot = _system(dut_ip).get("BootSignature")
            assert _command(dut_ip, "reboot") == "Valid", "the reboot was not accepted, so no ResetErrors followed it"
            try:
                result = http_client.fetch(dut_ip, 80, "PUT", "/status", {"ResetErrors": True}, timeout_s=_PUT_TIMEOUT_S).json().get("result")
                answer = str(result.get("ResetErrors")) if isinstance(result, dict) else f"no result: {result}"
            except (OSError, http_client.HTTP_ERROR) as exc:
                result_note(f"try {attempt}: the ResetErrors reached a closed listener ({exc!r})", recovery=True)
            _answers, replied = _kicked(board, bench, {"reboot": "Valid"})
            system = _serving_status(dut_ip, replied, result_note, f"the reboot under a ResetErrors, try {attempt}", boot)
            assert system.get("ResetReason") == _RR_REBOOT, f"the reboot read {system.get('ResetReason')}, not {_RR_REBOOT}"
            if answer:
                break
        assert answer == "Failed", f"a ResetErrors after the accepted reboot answered {answer!r} (empty: none of {_WINDOW_TRIES} tries reached the listener), not 'Failed'"
        after = get_errcount(dut_ip)
        cleared = [name for name in fram_backed_logger_names() if errcount_entry(after, name)["counter"] < errcount_entry(before, name)["counter"]]
        assert not cleared, f"FRAM-backed logs the refused ResetErrors cleared across the reboot: {cleared}"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


def test_near_miss_action_words_do_nothing_over_rest(board: "Board", bench: "BenchBridge", dut_ip: str) -> None:
    try:
        before, settings = _get(dut_ip, "/status").get("system"), (_get(dut_ip, "/networking"), _get(dut_ip, "/system"))
        answers, lines = observe_during(board, lambda: [(word, _command(dut_ip, word)) for word in _NEAR_MISSES])
        _marked(lines, "the near misses")
        wrong = [(word, answer) for word, answer in answers if answer != "Invalid"]
        assert not wrong, f"near-miss words answered other than Invalid: {wrong}"
        after = _get(dut_ip, "/status").get("system")
        assert isinstance(before, dict) and isinstance(after, dict), "no system block in /status"
        assert int(str(after.get("SysUptime"))) > int(str(before.get("SysUptime"))), f"the uptime did not keep rising (a reboot?): {before.get('SysUptime')} -> {after.get('SysUptime')}"
        assert (_get(dut_ip, "/networking"), _get(dut_ip, "/system")) == settings, "a setting changed across the near misses"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


def test_erase_reboot_and_mempause_at_once(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    save_errcount(dut_ip, "erase-reboot-mempause")
    try:
        save_fram_raw(board, "erase-reboot-mempause")
        restore_board_to_serving(board, bench, dut_ip)
        boot = _system(dut_ip).get("BootSignature")
        (answers, replied), lines = observe_during(board, lambda: _kicked(board, bench, _race(dut_ip, ("erasefram", "reboot", "mempause"))))
        _marked(lines, "the raced commands")
        result_note(f"raced answers: {answers}")
        shutdown = sorted(answers[word] for word in ("erasefram", "reboot"))
        assert shutdown == ["Failed", "Valid"], f"exactly one shutdown command must win, the other answer Failed: {answers}"
        expected = _RR_FRAM_ERASED if answers["erasefram"] == "Valid" else _RR_REBOOT
        system = _serving_status(dut_ip, replied, result_note, "the raced commands", boot)
        assert system.get("ResetReason") == expected, f"one reset, attributed to the winner: read {system.get('ResetReason')}, expected {expected} ({answers})"
    finally:
        restore_board_to_serving(board, bench, dut_ip)


def test_reboot_and_bootloader_at_once(board: "Board", bench: "BenchBridge", dut_ip: str, result_note: "Callable[[str], None]") -> None:
    # No log tail here: a BOOTSEL win leaves no console to read until picotool's reboot; the errcount after is the read.
    save_errcount(dut_ip, "reboot-bootloader")
    try:
        boot = _system(dut_ip).get("BootSignature")
        answers, replied = _kicked(board, bench, _race(dut_ip, ("reboot", "bootloader")))
        result_note(f"raced answers: {answers}")
        assert sorted(answers.values()) == ["Failed", "Valid"], f"exactly one of reboot and bootloader must win: {answers}"
        if answers["bootloader"] == "Valid":
            picotool(board, "reboot", timeout_s=_PICOTOOL_TIMEOUT_S)  # answers only a BOOTSEL device: no load, no flash write
        expected = _RR_WATCHDOG if answers["bootloader"] == "Valid" else _RR_REBOOT  # BOOTSEL loses the record: 2
        system = _serving_status(dut_ip, replied, result_note, "the raced reboot and bootloader", boot)
        assert system.get("ResetReason") == expected, f"the winner's code {expected} not read: {system.get('ResetReason')} ({answers})"
    finally:
        restore_board_to_serving(board, bench, dut_ip)

