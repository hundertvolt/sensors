"""Shared /status errcount helpers for fault-injection tests across this tier - the project owner's
own standing policy: reset before a test, confirm any deliberately-provoked fault actually produced
the expected error/warning entry (not just "the system didn't crash"), then reset again so a real
bench rig's live error history isn't left showing a test's own faults.

Shape reference (asy_webserver_service.py's own `_shape_errcount_entry()` - NOT the same shape as
print_log.py's raw `get_log()`, which several device_scripts/ files consume directly instead):
    GET /status -> {"errcount": {"<ModuleName>": {"counter": int, "history": [{"num": int, "type": "E"|"W"|"N"}, ...]}, ...}}
"type" is "E" (an err_s() call) or "W" (a wrn_s() call) - print_log.py's own PrintLogHistory.get_log()
encoding. Module names are each module's own `.name` (asy_webserver_service.py's `_index_by_name()`) -
e.g. "WIFI", "NTP", "BMP3XX", "CFGMGR_BMP3XX" (a *separate* entry from "BMP3XX" itself - every
ConfigManager instance registers its own, always in-RAM only, config_manager.py's own
`PrintLogHistory(name="CFGMGR_"+name)` never takes a fram= argument at all, confirmed directly).

Not every module's log is FRAM-backed (SPECIFICATION.md Part A.7's 7-chunk enumeration is the
complete list - every ConfigManager's own "CFGMGR_*" log, plus WIFI/NTP themselves, are always
in-RAM only, confirmed directly against sensortask_wozi.py's own construction calls: neither
AsyConnTime() nor AsyNtpClient() is ever passed fram=). These helpers check the same real,
REST-exposed value either way - the durability difference doesn't change what a live check can
observe, only whether it would still be there after a real reboot."""

from __future__ import annotations

from typing import Any

import http_client


def reset_all_error_logs(dut_ip: str) -> None:
    res = http_client.fetch(dut_ip, 80, "PUT", "/status", {"ResetErrors": True}, timeout_s=10.0)
    assert res.status_code == 200 and res.json().get("res") == "OK", f"failed to reset error logs via PUT /status: {res.status_code} {res.body!r}"


def get_errcount(dut_ip: str) -> dict[str, Any]:
    res = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0)
    assert res.status_code == 200, f"GET /status failed: {res.status_code} {res.body!r}"
    result: dict[str, Any] = res.json()["errcount"]
    return result


def assert_module_error_log_empty(dut_ip: str, module_name: str) -> None:
    entry = get_errcount(dut_ip).get(module_name, {})
    counter = entry.get("counter", 0)
    assert counter == 0, f"{module_name!r} error log was not empty as expected (counter={counter}): {entry!r}"


def assert_module_error_log_nonempty(dut_ip: str, module_name: str) -> None:
    entry = get_errcount(dut_ip).get(module_name, {})
    counter = entry.get("counter", 0)
    assert counter > 0, f"{module_name!r} error log was unexpectedly empty after a deliberately-provoked fault: {entry!r}"


def assert_module_error_log_contains(dut_ip: str, module_name: str, num: int, kind: str) -> None:
    """kind is "E" (err_s()) or "W" (wrn_s())."""
    counts = get_errcount(dut_ip)
    entry = counts.get(module_name)
    assert entry is not None, f"{module_name!r} not present in /status errcount at all: {counts!r}"
    history = entry.get("history", [])
    assert any(h.get("num") == num and h.get("type") == kind for h in history), f"{module_name!r} error log does not contain the expected {kind}{num}: history={history!r}"
