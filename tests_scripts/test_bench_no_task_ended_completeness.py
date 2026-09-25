"""Every bench test that injects a network fault also asserts no task ended under it - "no
Traceback" alone passed the NTP give-up that restarted a task a minute and rebooted every four
(SPECIFICATION.md C.7.2). Plus the helper's own contract, against a faked /status."""

import ast
import sys
from pathlib import Path

import pytest

_TESTS_HARDWARE = Path(__file__).resolve().parents[1] / "tests_hardware"
sys.path.insert(0, str(_TESTS_HARDWARE))
import error_log_helpers  # noqa: E402  (the sys.path line above is what makes it importable)

# BenchBridge calls that put a real fault on the DUT's network. kick_all_stations() is absent on
# purpose: it is the reconnect nudge every hard_reset() test uses, not a fault.
_FAULT_INJECTORS = frozenset({"ap_down", "inject_network_degradation", "block_udp_ports", "redirect_udp_port_to_local", "start_udp_source_capture"})
# Calls that satisfy the check: the helper itself, or a helper that runs it before a reset.
_CHECKERS = frozenset({"assert_no_task_ended", "_restore_ssid_over"})
_EXEMPT = {
    # ap_down() here only frees the bench radio to join the DUT's own hotspot - the DUT sees no fault.
    "test_repeated_associate_disassociate_cycles_dont_wedge_the_dhcp_server": "ap_down() is join mechanics, not a fault",
    "test_rapid_associate_disassociate_churn_doesnt_wedge_station_management": "ap_down() is join mechanics, not a fault",
}


def _fault_tests() -> "list[tuple[str, str, bool]]":
    found = []
    for path in sorted((_TESTS_HARDWARE / "bench").glob("test_*.py")):
        for fn in ast.parse(path.read_text()).body:
            if not (isinstance(fn, ast.FunctionDef) and fn.name.startswith("test_")):
                continue
            calls = [n.func for n in ast.walk(fn) if isinstance(n, ast.Call)]
            attrs = {f.attr for f in calls if isinstance(f, ast.Attribute)}
            names = {f.id for f in calls if isinstance(f, ast.Name)}
            if attrs & _FAULT_INJECTORS:
                found.append((path.name, fn.name, bool(names & _CHECKERS)))
    return found


def test_the_scan_finds_the_known_fault_tests() -> None:
    # Guards the scan itself: an AST shape change must not quietly turn this into zero checks.
    names = {name for _file, name, _ok in _fault_tests()}
    assert "test_real_wifi_outage_and_recovery_while_in_normal_sta_mode" in names
    assert "test_ntp_server_sends_garbage_instead_of_a_valid_response" in names
    assert len(names) >= 15


def test_every_fault_injecting_bench_test_asserts_no_task_ended() -> None:
    missing = [f"{file}::{name}" for file, name, ok in _fault_tests() if not ok and name not in _EXEMPT]
    assert not missing, "these bench tests inject a network fault but never call assert_no_task_ended(): " + ", ".join(missing)


def test_every_exemption_still_names_a_real_fault_test() -> None:
    names = {name for _file, name, _ok in _fault_tests()}
    assert set(_EXEMPT) <= names, f"stale exemptions: {sorted(set(_EXEMPT) - names)}"


@pytest.mark.parametrize(
    ("system_entry", "passes"),
    [
        ({"counter": 0, "history": []}, True),
        (None, True),  # a board whose SYSTEM never logged anything reports no entry at all
        ({"counter": 1, "history": [{"num": 1, "type": "W"}]}, False),  # "Task ended - attempting restart"
        ({"counter": 1, "history": [{"num": 5, "type": "E"}]}, False),  # a task ended with an exception
        ({"counter": 1, "history": [{"num": 4, "type": "E"}]}, False),  # the budget rebooted the board
    ],
)
def test_assert_no_task_ended_reads_the_system_log(monkeypatch: pytest.MonkeyPatch, system_entry: "dict[str, object] | None", passes: bool) -> None:  # noqa: FBT001
    errcount = {"NTP": {"counter": 3, "history": []}}  # other modules' failures are not this check's business
    if system_entry is not None:
        errcount["SYSTEM"] = system_entry
    monkeypatch.setattr(error_log_helpers, "get_errcount", lambda _ip: errcount)
    if passes:
        error_log_helpers.assert_no_task_ended("10.0.0.2", "ctx")
    else:
        with pytest.raises(AssertionError, match="ctx: a task ended"):
            error_log_helpers.assert_no_task_ended("10.0.0.2", "ctx")
