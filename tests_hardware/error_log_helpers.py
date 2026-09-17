"""Shared /status errcount helpers for fault-injection tests: reset before a test, confirm a
provoked fault produced the expected error/warning entry, then reset again. Shape: GET /status ->
{"errcount": {"<ModuleName>": {"counter": int, "history": [...]}}} - see SPECIFICATION.md Part A.7."""

from __future__ import annotations

from typing import Any

import http_client


# 17.0s, not the 10.0s the GET below uses: this PUT resets every registered error source
# sequentially and each FRAM-backed one pays a real FRAM write, so on `dev` (10+ such sources since
# WP1/WP2/WP3) it is by far the heaviest request the bench suite makes - and unlike the GET it is
# nowhere near a fixed cost. Sits just above the server's own 15.0s per-request cap
# (asy_webserver_service.py's outer_cap_s) for the same reason scripts/_digital_twin_ci_suite.py
# gives: below it, a slow-but-legitimate reset reads as a client timeout and gets misdiagnosed as a
# network fault; above it, the server's own abort surfaces instead and is diagnosable.
def reset_all_error_logs(dut_ip: str) -> None:
    res = http_client.fetch(dut_ip, 80, "PUT", "/status", {"ResetErrors": True}, timeout_s=17.0)
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
    """Kind is "E" (err_s()) or "W" (wrn_s())."""
    counts = get_errcount(dut_ip)
    entry = counts.get(module_name)
    assert entry is not None, f"{module_name!r} not present in /status errcount at all: {counts!r}"
    history = entry.get("history", [])
    assert any(h.get("num") == num and h.get("type") == kind for h in history), f"{module_name!r} error log does not contain the expected {kind}{num}: history={history!r}"
