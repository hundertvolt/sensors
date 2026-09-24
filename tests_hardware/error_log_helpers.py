"""Shared /status errcount helpers for fault-injection tests: reset before a test, confirm a
provoked fault produced the expected error/warning entry, then reset again. Shape: GET /status ->
{"errcount": {"<ModuleName>": {"counter": int, "history": [...]}}} - see SPECIFICATION.md Part A.7."""

from __future__ import annotations

from typing import Any

import http_client

# Above the server's own 15.0s outer_cap_s, not below it: a legitimate sweep can never exceed the
# cap, and the 10.0s this used to be made a slow-but-legitimate reset read as a network fault. The
# headroom absorbs real WiFi latency the loopback twin has none of. Measurements: BACKLOG item 24.
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


def assert_module_error_log_clean(
    dut_ip: str, module_name: str, allowed_warnings: tuple[int, ...] = (), allowed_errors: tuple[int, ...] = (),
) -> None:
    """Nothing in the log's history beyond the entries named - unlike a zero counter, no race
    against a module whose normal operation logs a legitimate warning. `allowed_errors` is for a
    test whose documented outcome is an ERROR (torn writes provoked, then recovery asserted)."""
    entry = get_errcount(dut_ip).get(module_name, {})
    history = entry.get("history", [])
    unexpected = [
        h for h in history
        if (h.get("type") == "E" and h.get("num") not in allowed_errors)
        or (h.get("type") == "W" and h.get("num") not in allowed_warnings)
    ]
    assert not unexpected, (
        f"{module_name!r} logged {unexpected!r} - only warnings {allowed_warnings!r} and errors "
        f"{allowed_errors!r} are expected here; full entry: {entry!r}"
    )


def assert_module_error_log_contains(dut_ip: str, module_name: str, num: int, kind: str) -> None:
    """Kind is "E" (err_s()) or "W" (wrn_s())."""
    counts = get_errcount(dut_ip)
    entry = counts.get(module_name)
    assert entry is not None, f"{module_name!r} not present in /status errcount at all: {counts!r}"
    history = entry.get("history", [])
    assert any(h.get("num") == num and h.get("type") == kind for h in history), f"{module_name!r} error log does not contain the expected {kind}{num}: history={history!r}"


def assert_no_module_logged_a_new_error(dut_ip: str, before: dict[str, Any], context: str) -> None:
    """Every FRAM-backed module's counter, not one named module's. A full-ceiling burst starves the
    heap for the whole graph, so an allocation failure it provokes can surface in SGP40, SCD30,
    SYSTEM or any other logger - checking only WEBSERVER would miss exactly the all-sides case."""
    after = get_errcount(dut_ip)
    grew = {
        name: (before.get(name, {}).get("counter", 0), entry.get("counter", 0))
        for name, entry in after.items()
        if entry.get("counter", 0) > before.get(name, {}).get("counter", 0)
    }
    assert not grew, f"{context}: these modules logged new errors during the burst (before, after): {grew!r}; full log: {after!r}"
