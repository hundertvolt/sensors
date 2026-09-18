"""Shared /status errcount helpers for fault-injection tests: reset before a test, confirm a
provoked fault produced the expected error/warning entry, then reset again. Shape: GET /status ->
{"errcount": {"<ModuleName>": {"counter": int, "history": [...]}}} - see SPECIFICATION.md Part A.7."""

from __future__ import annotations

from typing import Any

import http_client

# MEASURED on the dev bench board, 2026-09-17, 21 FRAM-backed chunks: 6.32s idle with real
# accumulated history, 6.4-7.0s repeated, and 11.58s with three concurrent GET /status workers. Cost
# is fixed PER CHUNK (~305ms), not per history entry - clearing 21 full chunks costs the same as 21
# empty ones. The server aborts any request at its own 15.0s outer_cap_s, so a legitimate reset can
# never exceed that; this sits well above it rather than just above (as the loopback-only twin suite
# does) to absorb real WiFi latency on the abort's own close, which the twin has none of. Below the
# cap - the 10.0s this used to be - a slow-but-legitimate reset reads as a client timeout and gets
# misdiagnosed as a network fault; it failed a bench test on its first statement for exactly that.
# Gates ~70 call sites across all 8 bench test files.
_RESET_ERRORS_TIMEOUT_S = 30.0


def reset_all_error_logs(dut_ip: str) -> None:
    res = http_client.fetch(dut_ip, 80, "PUT", "/status", {"ResetErrors": True}, timeout_s=_RESET_ERRORS_TIMEOUT_S)
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
