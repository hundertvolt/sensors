"""Shared /status errcount helpers for fault-injection tests: reset before a test, confirm a
provoked fault produced the expected error/warning entry, then reset again. Shape: GET /status ->
{"errcount": {"<ModuleName>": {"counter": int, "history": [...]}}} - see SPECIFICATION.md Part A.7."""

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


def assert_module_error_log_clean(dut_ip: str, module_name: str, allowed_warnings: tuple[int, ...] = ()) -> None:
    """No errors at all, and no warnings beyond the ones explicitly named.

    Stricter than assert_module_error_log_empty() where it matters (it reads the history rather
    than a counter) and deliberately looser where an empty log is not a property the module can
    actually offer: a module whose normal operation includes a legitimate warning cannot be held to
    a zero counter without the test becoming a race against that warning. Same distinction
    isl29125_mechanism_envelope.py already draws on-device ("logged real ERRORS, not just warnings").
    """
    entry = get_errcount(dut_ip).get(module_name, {})
    history = entry.get("history", [])
    unexpected = [h for h in history if h.get("type") == "E" or (h.get("type") == "W" and h.get("num") not in allowed_warnings)]
    assert not unexpected, f"{module_name!r} logged {unexpected!r} - only warnings {allowed_warnings!r} are expected here; full entry: {entry!r}"


def assert_module_error_log_contains(dut_ip: str, module_name: str, num: int, kind: str) -> None:
    """Kind is "E" (err_s()) or "W" (wrn_s())."""
    counts = get_errcount(dut_ip)
    entry = counts.get(module_name)
    assert entry is not None, f"{module_name!r} not present in /status errcount at all: {counts!r}"
    history = entry.get("history", [])
    assert any(h.get("num") == num and h.get("type") == kind for h in history), f"{module_name!r} error log does not contain the expected {kind}{num}: history={history!r}"
