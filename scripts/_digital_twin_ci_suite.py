#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Automated version of the manual digital-twin on-demand walkthrough - drives `digital_twin/run_generic_integration.py` as a real subprocess, over real HTTP/UDP, through a sequence of real process restarts, and asserts every step. Device-generic (SPECIFICATION.md Part L.4): `--device` selects which real `devices/<device>.toml`-derived module + wiring plan to boot, defaulting to `wozi`. The bus-fault matrix (Run 3/4) is derived from that device's own wiring plan, never a hardcoded driver list - a device without `bmp3xx` (4 of the 6 real devices) simply never faults/checks it.
CPython/stdlib-only (the code under test still only ever runs under the real MicroPython Unix-port interpreter); invoked by `scripts/run_digital_twin_ci.sh` (which owns "clean"/"build", and the per-device `buildgen` generation step this suite's own `--device` depends on) as its "test" phase, once per device via CI's own `strategy.matrix` (see `.github/workflows/ci.yml`'s `digital-twin-e2e` job).
Full walkthrough and rationale: `digital_twin/README.md`'s "Automated CI suite" section."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import signal
import socket
import statistics
import struct
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

# The repo root is appended, so tests/ resolves as a namespace package and no tests/ fake shadows a host module.
sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts._summary_block import Summary
from tests._error_codes import code

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "digital_twin"
FRAM_STATE_PATH = STATE_DIR / "fram_state.json"
SCD30_STATE_PATH = STATE_DIR / "scd30_state.json"
CONFIG_DIR = STATE_DIR / "config"
GENERATED_SRC_DIR = REPO_ROOT / "build" / "generated_src"
# build/generated_src first: no static sensortask_<device>.py exists any more (Part L.2).
# run_digital_twin_ci.sh regenerates every device's module and wiring plan through buildgen into
# this gitignored directory before the suite runs.
MICROPYPATH = "build/generated_src:src:digital_twin:ext:frozen_modules:.frozen"
HOST = "127.0.0.1"
PORT = 18080  # a fixed, non-privileged, non-8080-default port - avoids colliding with a real
# manual `scripts/run_unix_port_integration.sh` run on the same machine.
DNS_PORT = 53  # asy_captive_dns.py's CaptiveDNS binds ("0.0.0.0", 53) unconditionally, real port only.
_NTP_UNREACHABLE_HOST = "192.0.2.1"  # RFC 5737 TEST-NET-1, never answers: Run 8 configures it, Run 9 watches it
_NTP_PORT = 123

# Per-module PrintLog `name=` values. A verbose log line is `print(name, *args)`, so a line
# starting with one of these plus a space is real module output, not the runner's own banners.

# A loose set on purpose - some modules are not guaranteed to log at all in these short runs - so
# it confirms verbose logging is flowing rather than pinning any module's output. BMP3XX stays
# even where no device wires it: an unmatched prefix costs nothing.
_VERBOSE_LOG_PREFIXES = ("SYSTEM", "SGP40", "SCD30", "BMP3XX", "WEBSERVER", "NOTIFY", "WIFI", "NTP", "FRAM")

# Bus-fault-matrix knowledge keyed by TOML `driver` identity, not by each driver's own _NAME.
# These are per-driver facts, true of every device carrying that driver, so the tables are fixed;
# what varies is only which drivers a device wires, read from its own wiring plan.
_BUS_FAULT_OPS = {  # the real bus-level call each driver's own bus access goes through - confirmed
    # directly against each driver's own read/write call sites, not guessed from the chip's API.
    "scd30": "writeto",
    "sgp40": "writeto",
    "bmp3xx": "readfrom_mem",
    "isl29125": "readfrom_mem",  # every periodic read is get_register_struct() -> readfrom_mem
    "fram": "write",
}
# @tunable l2.ntp_unreachable_watch_s = 90.0
_NTP_UNREACHABLE_WATCH_S = 90.0  # Run 9 - past the old NTP give-up (~60s), see that run
# @tunable l2.bus_fault_error_count = 500
_BUS_FAULT_ERROR_COUNT = 500  # sustained/high-repeat-count - see Run 3's own comment for why.
# Driver to its own REST/error-log `_NAME`, read from each driver's source. They all happen to
# equal driver.upper() here, which is NOT a general rule - NotificationService's is "NOTIFY",
# not "NOTIFICATION" (Part L.3). A verified narrow table, never generic _NAME resolution.
_DRIVER_ERRCOUNT_NAME = {"scd30": "SCD30", "sgp40": "SGP40", "bmp3xx": "BMP3XX", "isl29125": "ISL29125", "fram": "FRAM"}
# The registered error sources not FRAM-backed, exempt from Run 5c's loss sweep: FRAMManager's own log (the store
# cannot persist its failures through itself) and CFGMGR_SCD30 (RAM-only, owner, 2026-09-29: 'no extra FRAM chunk').
# _sensortask_scenarios.py pins the same set from the real object graph.
_IN_MEMORY_ONLY_ERROR_SOURCES = frozenset({"FRAM", "CFGMGR_SCD30"})
# Which bus-attached drivers produce a real /measurements reading (Run 4's "came back after being
# faulted" check) vs which Run 4 asserts came back at 0.
#
# The second set means "with FRAM faulted, nothing persisted", NOT "these logs are in-memory" -
# what it was once wrongly named for. SGP40 and "fram" are each absent for their own separate
# reason; digital_twin/README.md has both accounts in full.
_MEASUREMENT_DRIVERS = frozenset({"scd30", "sgp40", "bmp3xx", "isl29125"})
_NO_PERSIST_WHEN_FRAM_FAULTED = frozenset({"scd30", "bmp3xx", "isl29125"})
_PERSISTED_ERROR_MODULES = ("SGP40",)  # Run 5b's own abrupt-restart subject, not a claim about
# who has persistence: Run 5b reboots straight onto Run 5's state, and Run 5 faults only SGP40.
# Run 5c proves the chip-healthy half for every bus-attached driver, via its own sweep set.

# WIFI's own log is FRAM-backed too, under the implicit-FRAM-wiring rule, so it follows the same
# all-or-nothing abrupt-restart guarantee - checked separately in Run 8 rather than through
# ctx.drivers, since it is not bus-fault-injectable and has no chip fake.

# The one HTTP status every endpoint in this suite is expected to answer with - a non-200 anywhere
# is a suite failure, never an alternative success path.
_HTTP_OK = 200

# The settings Run 1 PUTs and every later run reads back, the thresholds the assertions compare
# against, and the scripted fault counts handed to --fault/--wifi-outcome. Named here so the
# value a run INJECTS and the value its assertion EXPECTS cannot drift apart.
_TEST_DEBUG_LEVEL = 5
_TEST_WARN_CO2 = 1800
_TEST_SCD30_MEAS_INT = 4
_MIN_VERBOSE_LOG_LINES = 5
# @tunable l2.bounded_fault_count = 3
_BOUNDED_FAULT_COUNT = 3  # injected bus failures per bounded-fault run - SGP40's alone in Run
# 5/5b, then one link per bus-attached driver in Run 5c. Not device- or driver-specific, and
# deliberately small: each one ends the driver's read task, and three is the supervisor's budget.
# @tunable l2.wifi_scripted_failures = 5
_WIFI_SCRIPTED_FAILURES = 5  # asy_wifi_service.py's conn_fail_to_hotspot - the failure count that trips hotspot fallback
# The five identical verdicts spend ONE history slot (the newest-entry rule, asy_print_log.py) and count five;
# the fifth's fallback to the hotspot persists its own WLAN_TO_HOTSPOT warning in a second slot (Part C.7.1).
_WIFI_PERSISTED_WARNINGS = 2
_WIFI_PERSISTED_EVENTS = _WIFI_SCRIPTED_FAILURES + 1  # the counter: five failures, then the fallback

# ResetErrors resets every source at once, each FRAM-backed one still paying its own chunk write, so it
# far exceeds _http()'s 5s default. The value below is derived from the server's own _DEFAULT_OUTER_CAP_S;
# README.md has the derivation and SPECIFICATION.md Part C.7 the real-hardware measurements.
# @tunable web.outer_cap_s = 15.0
_SERVER_OUTER_CAP_S = 15.0  # mirrors asy_webserver_service.py's _DEFAULT_OUTER_CAP_S - keep in sync
# @tunable l2.reset_errors_timeout_margin_s = 2.0
_RESET_ERRORS_TIMEOUT_S = _SERVER_OUTER_CAP_S + 2.0  # loopback: no WiFi close latency to absorb
# The BUDGET rather than the timeout above, which only catches a call that never finished. Sized
# from both datasets - twin 8.259s worst, hardware 6.32s idle and 11.58s under load - so 80% of
# the cap sits ~45% above anything legitimate, and dev needs ~10 more sources to breach it.
# @tunable l2.reset_errors_budget_ratio = 0.8
_RESET_ERRORS_BUDGET_S = _SERVER_OUTER_CAP_S * 0.8

# Run 11 (soak), moved host-side from the twin's own retired _soak() ("Driver/DUT process
# separation"): this suite drives every soak request over real HTTP as Runs 1-10 do, so the
# client's allocation and CPU work never shares the DUT's heap.
_SOAK_ENDPOINTS = ("/measurements", "/sensors", "/networking", "/system", "/notification", "/status", "/")
# 100, not wozi's original 40: dev's two extra uart_link instances mean more one-time post-boot
# settling, so the trend check would otherwise measure an in-progress settle rather than a
# plateau. digital_twin/README.md has the measurement.
# @tunable l2.soak_warmup_cycles = 100
_SOAK_WARMUP_CYCLES = 100
# @tunable l2.soak_cycles = 20
_SOAK_CYCLES = 20
# The one thing that move could not take host-side: gc.mem_free() lives in the twin's heap and
# has no REST route, so --mem-sample-interval-ms prints a MEM_SAMPLE line per interval and this
# suite scrapes them from the captured log, as it already does the watchdog counter.

# 25ms is dense enough that even a fast pass yields plenty of samples for a quarter split, and
# one gc.collect()+print() per interval costs nothing measurable.
# @tunable l2.mem_sample_interval_ms = 25
_MEM_SAMPLE_INTERVAL_MS = 25
# The tolerance is grounded in each run's own observed noise rather than a historical
# constant scaled by a law that does not hold here - consecutive 25ms gc.mem_free() samples are
# heavily autocorrelated. digital_twin/README.md has the measurement and what it replaced.
# @tunable l2.mem_trend_tolerance_sd_multiplier = 3.0
_MEM_TREND_TOLERANCE_SD_MULTIPLIER = 3.0

# Wait budgets and poll steps, one per purpose. Each wait polls for its condition and returns early;
# the two fixed sleeps wait for an absence, which no probe can observe.
# @tunable l2.error_count_wait_s = 30.0
_ERROR_COUNT_WAIT_S = 30.0  # an error-log entry a fault or a restore has to land
# @tunable l2.first_fault_wait_s = 45.0
_FIRST_FAULT_WAIT_S = 45.0  # a faulted driver's first "E" entry after its boot
# @tunable l2.long_wait_s = 90.0
_LONG_WAIT_S = 90.0  # a bounded fault settling, and WiFi falling back to the hotspot and its DNS
# @tunable l2.mem_paused_wait_s = 15.0
_MEM_PAUSED_WAIT_S = 15.0
# @tunable l2.hang_run_exit_wait_s = 45.0
_HANG_RUN_EXIT_WAIT_S = 45.0  # Run 10's --duration 15 run, hung bus call included
# @tunable l2.failed_run_exit_wait_s = 5.0
_FAILED_RUN_EXIT_WAIT_S = 5.0
# @tunable l2.past_exhaustion_wait_s = 3.0
_PAST_EXHAUSTION_WAIT_S = 3.0  # a few read cycles past a bounded fault, for errors that must not climb
# @tunable l2.in_flight_settle_s = 2.0
_IN_FLIGHT_SETTLE_S = 2.0  # lets work already in flight finish once storage is paused
# @tunable l2.errcount_poll_s = 1.0
_ERRCOUNT_POLL_S = 1.0
# @tunable l2.mem_paused_poll_s = 0.5
_MEM_PAUSED_POLL_S = 0.5
# @tunable l2.serving_poll_s = 0.25
_SERVING_POLL_S = 0.25
# @tunable l2.serving_probe_timeout_s = 1.0
_SERVING_PROBE_TIMEOUT_S = 1.0
# @tunable l2.dns_poll_s = 0.5
_DNS_POLL_S = 0.5
# @tunable l2.kill_reap_timeout_s = 5.0
_KILL_REAP_TIMEOUT_S = 5.0  # the wait for a SIGKILLed twin to be reaped
# @tunable l2.concurrent_get_join_margin_s = 5.0
_JOIN_MARGIN_S = 5.0  # past a burst's own timeout, so a thread is joined only once its request gave up
# @tunable l2.slot_release_wait_s = 1.0
_SLOT_RELEASE_WAIT_S = 1.0  # a readiness probe would occupy a max_connections slot, the property under test

# A fixed, recognizable DNS transaction ID, so a real answer from CaptiveDNS can be told
# apart from an echo of the query itself; the header prefix is _try_dns_query()'s own ">HH" unpack.
_DNS_QUERY_ID = 0x1234
_DNS_RESPONSE_HEADER_LEN = 4

_FAILURES: list[str] = []
# Every check also lands in the SPECIFICATION.md E.10 summary block main() prints, named with its
# pass label; a pass that recorded no check at all is counted as having checked nothing.
_SUMMARY = Summary("scripts/_digital_twin_ci_suite.py", unit="checks")
_CHECKS_PER_PASS: dict[str, int] = {}


@dataclass(frozen=True)
class RunContext:
    # Everything one device's run of this suite needs, computed once in main(): which Unix-port
    # binary to launch, which generated module/wiring-plan pair to boot, and which bus-attached
    # drivers that device declares - so the fault matrix never hardcodes who has a bmp3xx.

    micropython_bin: str
    logs_dir: Path
    device: str
    module: str
    wiring_plan_path: Path
    drivers: frozenset[str]
    gc_threshold: int  # passed to every spawned run_generic_integration.py subprocess via
    # --gc-threshold, under Part I.4(e)'s standing rule: the WHOLE suite must pass clean at
    # MicroPython's own gc.threshold(-1) before it is run again at the project's chosen 32768.
    # main() therefore runs run_suite() twice, once per value, never once with one hardcoded.


# Sharpened memory-safety discipline (CLAUDE.md, SPECIFICATION.md Part I.4(e), 2026-09-14): every
# OK/FAIL line is tagged with which gc.threshold() pass produced it, set once per run_suite() call -
# every one of the 14 run functions below stays untouched, no per-message edits needed.
_CURRENT_PASS_LABEL = ""


def _record(kind: str, full_msg: str) -> None:
    _SUMMARY.add(kind, full_msg)
    _CHECKS_PER_PASS[_CURRENT_PASS_LABEL] = _CHECKS_PER_PASS.get(_CURRENT_PASS_LABEL, 0) + 1


def _fail(msg: str) -> None:
    full_msg = f"{_CURRENT_PASS_LABEL}{msg}"
    _FAILURES.append(full_msg)
    _record("failed", full_msg)
    print(f"FAIL: {full_msg}", file=sys.stderr)


def _check(*, condition: bool, msg: str) -> None:
    if not condition:
        _fail(msg)
    else:
        _record("passed", f"{_CURRENT_PASS_LABEL}{msg}")
        print(f"OK: {_CURRENT_PASS_LABEL}{msg}")


# Both spellings of the same event: those handlers log str(e), not the class, so a real caught
# allocation failure prints "memory allocation failed, ..." (py/runtime.c:1692/1696) with no
# "MemoryError" anywhere - the class name alone only ever sees an UNCAUGHT traceback.
_MEMORY_ERROR_MARKERS = ("MemoryError", "memory allocation failed")
# @tunable l2.ceiling_rounds = 3
_CEILING_ROUNDS = 3  # back-to-back, so a leaked slot or a pool that only fills over time shows up


def _check_no_memory_error_in_log(log_path: Path, run_label: str) -> None:
    # Part I.4(e): zero MemoryErrors, caught-and-logged included, a caught allocation failure
    # being a design defect rather than a passing result. Checked on every run's log, not only
    # the soak's, since src/'s catch-and-degrade handlers can log one during any run.
    try:
        log_text = log_path.read_text(errors="replace")
    except OSError as exc:  # fails closed: a log it cannot read is no verdict, never a clean one
        _fail(f"{run_label}: log {log_path} missing or unreadable, no memory verdict ({exc!r})")
        return
    _check(
        condition=not any(marker in log_text for marker in _MEMORY_ERROR_MARKERS),
        msg=f"{run_label}: log contains zero MemoryErrors (caught-and-logged counts as a failure too)",
    )


def _configured_max_connections(device: str) -> int:
    # The admission ceiling this tree builds for `device`, read by buildgen's own helper - so raising
    # a device's ceiling makes this run drive more concurrency instead of a stale literal.
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))  # buildgen sits beside scripts/, as for _generate_sensortask_modules.py
    from buildgen.validate import device_max_connections  # noqa: PLC0415 - needs the path entry above

    return device_max_connections(REPO_ROOT / "devices" / f"{device}.toml", REPO_ROOT / "src")


def _concurrent_get(paths: list[str], timeout: float = 30.0) -> list[object]:
    # One real socket per request, all in flight together from THIS process, behind a barrier so the
    # burst is truly simultaneous. Each result is (status, parsed JSON body), or the error's repr.
    results: list[object] = [None] * len(paths)
    barrier = threading.Barrier(len(paths))

    def one(index: int, path: str) -> None:
        try:
            barrier.wait(timeout=timeout)
            results[index] = _http("GET", path, timeout=timeout)
        except (OSError, ValueError, http.client.HTTPException, threading.BrokenBarrierError) as exc:  # ValueError: a malformed JSON body
            results[index] = repr(exc)

    threads = [threading.Thread(target=one, args=(i, path)) for i, path in enumerate(paths)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=timeout + _JOIN_MARGIN_S)
    return results


def _describe_results(results: list[object]) -> list[object]:
    # Status and body type only: a full ceiling of /sensors bodies would bury which one failed.
    return [(r[0], type(r[1]).__name__) if isinstance(r, tuple) else r for r in results]


def _clean_state() -> None:
    print("== Clean: removing any leftover digital-twin state (fresh start)")
    for path in (FRAM_STATE_PATH, SCD30_STATE_PATH):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    if CONFIG_DIR.exists():
        for entry in CONFIG_DIR.iterdir():
            entry.unlink()
        CONFIG_DIR.rmdir()


def _http(method: str, path: str, body: dict[str, Any] | None = None, timeout: float = 5.0) -> tuple[int, Any]:
    # "/" serves the real, static website (gzip bytes, not JSON - see asy_webserver_service.py's
    # own generic "/" route) - only the REST endpoints return a JSON body, so parsing is keyed off
    # the real Content-Type header rather than assumed for every path.
    conn = http.client.HTTPConnection(HOST, PORT, timeout=timeout)
    try:
        headers = {}
        payload = b""
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=payload, headers=headers)
        res = conn.getresponse()
        raw = res.read()
        content_type = res.getheader("Content-Type", "")
        parsed = json.loads(raw) if raw and "json" in content_type else None
        return res.status, parsed
    finally:
        conn.close()


def _put_reset_errors_timed(run_label: str) -> int:
    # The one request with a real elapsed-time budget (_RESET_ERRORS_BUDGET_S above). Returns the
    # HTTP status so callers keep asserting that themselves; the budget check is made here so both
    # call sites get it without either having to remember to.
    started = time.monotonic()
    status, _ = _http("PUT", "/status", {"ResetErrors": True}, timeout=_RESET_ERRORS_TIMEOUT_S)
    elapsed = time.monotonic() - started
    _check(
        condition=elapsed < _RESET_ERRORS_BUDGET_S,
        msg=f"{run_label}: the ResetErrors sweep finished inside its {_RESET_ERRORS_BUDGET_S:.1f}s budget ({elapsed:.2f}s, {elapsed / _SERVER_OUTER_CAP_S * 100:.0f}% of the server's own {_SERVER_OUTER_CAP_S:.1f}s cap)",
    )
    return status


def _error_type_count(entry: dict[str, Any], type_char: str = "E") -> int:
    # entry["counter"] counts errors AND warnings in one history, and a "recovered after N
    # failures" notice is itself a "W" - so a recovery bumps it with no new failure. Counting one
    # type's entries is the real "did N of THIS happen" signal; WIFI's are "W", hence Run 8.
    history = entry.get("history", [])
    return sum(1 for item in history if isinstance(item, dict) and item.get("type") == type_char)


def _failure_events(entry: dict[str, Any]) -> int:
    # asy_print_log.py's newest-entry rule folds a repeated code into one slot while "counter" counts
    # every call, so a failure is a counter step not backed by a "W" slot (exact while no warning repeats).
    counter = entry.get("counter", 0)
    return (counter if isinstance(counter, int) else 0) - _error_type_count(entry, "W")


def _link_failures(before: dict[str, Any], after: dict[str, Any]) -> int:
    # One process's own failures: a boot-time warning folded into an older slot before it cancels out.
    return _failure_events(after) - _failure_events(before)


def _non_empty_slots(entry: dict[str, Any]) -> list[tuple[Any, Any]]:
    return [(item.get("type"), item.get("num")) for item in entry.get("history", []) if isinstance(item, dict) and item.get("type") != "N"]


def _restore_is_all_or_nothing(written: dict[str, Any], restored: dict[str, Any]) -> bool:
    # Whole: the written ring and at least its count came back, newer slots only after it (this boot's
    # own). Nothing: no "E" slot survived, only what this boot logged itself. Else partial or garbled.
    slots, kept = _non_empty_slots(restored), _non_empty_slots(written)
    whole = slots[: len(kept)] == kept and all(kind != "E" for kind, _ in slots[len(kept) :]) and restored.get("counter", 0) >= written.get("counter", 0)
    return whole or all(kind != "E" for kind, _ in slots)


def _wait_for_failure_events(name: str, target: int, timeout_s: float) -> dict[str, Any]:
    # _wait_for_error_type_count()'s poll, keyed on failure events rather than history slots.
    deadline = time.monotonic() + timeout_s
    entry: dict[str, Any] = {}
    while time.monotonic() < deadline:
        entry = _errcount(name)
        if _failure_events(entry) >= target:
            return entry
        time.sleep(_ERRCOUNT_POLL_S)
    return entry


def _errcount(name: str) -> dict[str, Any]:
    # TOLERANT: answers {} for a /status it could not parse, since the polling helpers call it in
    # a loop and a transient non-200 during boot must retry. Assertions take _errcount_required()
    # instead - {} reads as counter 0 - a split that makes the mistake unreachable.
    status, body = _http("GET", "/status")
    if status != _HTTP_OK or not isinstance(body, dict):
        return {}
    entry = body.get("errcount", {}).get(name, {})
    return entry if isinstance(entry, dict) else {}


def _errcount_required(name: str) -> dict[str, Any]:
    # STRICT, for assertion sites: raises rather than returning {}, so an unreadable /status
    # becomes the caller's _fail() instead of a silent pass. Every registered source appears in
    # errcount whether or not it logged, so a missing entry is always a real failure.
    entry = _errcount(name)
    if not entry:
        raise RuntimeError(f"GET /status did not yield a readable errcount entry for {name!r} - the server answered nothing usable, so no assertion about its counter would mean anything")
    return entry


def _errcount_all() -> dict[str, dict[str, Any]]:
    # The whole errcount table from ONE /status read, for the sweeps that compare every registered
    # source across a reboot. A per-name loop would read a different /status per row and could not
    # tell a real loss from two reads straddling a fresh entry. Strict like _errcount_required().
    status, body = _http("GET", "/status")
    if status != _HTTP_OK or not isinstance(body, dict):
        raise RuntimeError(f"GET /status did not yield a readable body (status {status}) - no sweep over its errcount table would mean anything")
    table = body.get("errcount", {})
    if not isinstance(table, dict) or not table:
        raise RuntimeError(f"GET /status carried no usable errcount table ({table!r})")
    return {name: entry for name, entry in table.items() if isinstance(entry, dict)}


def _wait_for_error_counts_to_settle(names: list[str], timeout_s: float, samples: int = 3, interval_s: float = 2.0) -> dict[str, int]:
    # A bounded fault is exhausted when its drivers stop adding failures - observable, not a
    # wall-clock guess - so this samples until consecutive reads agree for every name. A snapshot
    # taken mid-fault would read as a persistence failure when nothing was lost.
    deadline = time.monotonic() + timeout_s
    agreed = 0
    previous: dict[str, int] = {}
    current: dict[str, int] = {}
    while time.monotonic() < deadline:
        table = _errcount_all()
        current = {name: _failure_events(table.get(name, {})) for name in names}
        agreed = agreed + 1 if current == previous else 0
        if agreed >= samples - 1:
            return current
        previous = current
        time.sleep(interval_s)
    raise RuntimeError(f"bounded-fault error counts never settled within {timeout_s}s - last read {current!r}, the one before {previous!r}")


def _mem_paused() -> bool | None:
    # asy_system_service.py's own permanent-storage pause, as GET /status reports it. None means the
    # field wasn't readable at all, which is not the same answer as False.
    status, body = _http("GET", "/status")
    if status != _HTTP_OK or not isinstance(body, dict):
        return None
    system = body.get("system", {})
    return system.get("MemPaused") if isinstance(system, dict) else None


def _wait_for_mem_paused(*, expected: bool, timeout_s: float) -> bool:
    # The pause is applied from a REST handler onto the FRAM manager, so a 200 on the PUT is not by
    # itself proof the flag is up - poll the real reported state rather than assume it followed.
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _mem_paused() is expected:
            return True
        time.sleep(_MEM_PAUSED_POLL_S)
    return False


def _wait_for_errcount_above(name: str, floor: int, timeout_s: float) -> dict[str, Any]:
    # Polls /status until `name`'s error counter climbs above `floor`, or times out - used instead
    # of a fixed sleep for state-machine transitions (e.g. WiFi hotspot fallback) with real, but
    # not perfectly predictable, wall-clock timing.
    deadline = time.monotonic() + timeout_s
    entry: dict[str, Any] = {}
    while time.monotonic() < deadline:
        entry = _errcount(name)
        if entry.get("counter", 0) > floor:
            return entry
        time.sleep(_ERRCOUNT_POLL_S)
    return entry


def _wait_for_error_type_count(name: str, target: int, timeout_s: float, type_char: str = "E") -> dict[str, Any]:
    # _wait_for_errcount_above()'s poll-never-sleep reasoning, keyed on one type's count rather
    # than the raw counter a "W" also bumps. A fixed sleep encodes a host-speed assumption: the
    # bench Pi4 needs ~8s where an x86 runner needs ~2s, so 6s passes there and samples here.
    deadline = time.monotonic() + timeout_s
    entry: dict[str, Any] = {}
    while time.monotonic() < deadline:
        entry = _errcount(name)
        if _error_type_count(entry, type_char) >= target:
            return entry
        time.sleep(_ERRCOUNT_POLL_S)
    return entry


def _wait_until_serving(proc: subprocess.Popen[str], timeout_s: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"digital twin subprocess exited early with code {proc.returncode} before ever serving")
        try:
            status, _ = _http("GET", "/", timeout=_SERVING_PROBE_TIMEOUT_S)
            if status == _HTTP_OK:
                return
        except OSError:
            pass
        time.sleep(_SERVING_POLL_S)
    raise TimeoutError(f"digital twin never started serving on {HOST}:{PORT} within {timeout_s}s")


def _spawn(ctx: RunContext, extra_args: list[str], log_path: Path) -> subprocess.Popen[str]:
    env = dict(os.environ)
    env["MICROPYPATH"] = MICROPYPATH
    env["TZ"] = "UTC"
    log_file = open(log_path, "w")  # lifetime is the whole subprocess run, closed by caller
    cmd = [
        ctx.micropython_bin,
        "digital_twin/run_generic_integration.py",
        "--module", ctx.module,
        "--wiring-plan", str(ctx.wiring_plan_path),
        "--device", ctx.device,
        "--host", HOST,
        "--port", str(PORT),
        # RunConfig defaults these to None (in-memory only), unlike the retired per-device entry
        # points, so this suite's persistence-across-a-reboot checks supply them explicitly,
        # pointed at the same fixed paths _clean_state() wipes.
        "--fram-state-path", str(FRAM_STATE_PATH),
        "--scd30-state-path", str(SCD30_STATE_PATH),
        # Applied to every run this suite spawns, not only the soak: Part I.4(e)'s rule covers
        # the whole suite, not just stress tests. main() runs it twice, once per
        # RunContext.gc_threshold value.
        "--gc-threshold", str(ctx.gc_threshold),
        *extra_args,
    ]
    print(f"== Launching: {' '.join(cmd)} (log: {log_path})")
    # Fixed argv assembled just above from the repo's own paths and this suite's own literal
    # flags; shell=False, no untrusted input. S603 exemption is central, see pyproject.toml.
    proc = subprocess.Popen(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    proc.ci_log_file = log_file  # type: ignore[attr-defined]  # stashed only so _shutdown() below can close it
    return proc


def _close_log_and_check_memory_safety(proc: subprocess.Popen[str], run_label: str) -> None:
    # Shared by _shutdown()/_wait_exit() below - every spawned run's log gets this check, not only
    # the soak test's own HTTP-level failures list (SPECIFICATION.md Part I.4(e), sharpened
    # 2026-09-14: zero MemoryErrors, caught-and-logged included, for every run).
    log_file = getattr(proc, "ci_log_file", None)
    if log_file is None:
        return
    log_path = Path(log_file.name)
    log_file.close()
    _check_no_memory_error_in_log(log_path, run_label)


def _proc_diagnostic_fields(pid: int) -> dict[str, str]:
    # Best-effort /proc introspection for a process that ignored SIGINT: `wchan` names the kernel
    # function it is blocked in, which separates a real syscall wait from a wedged heap or a
    # runaway loop with no debugger attached. Linux-only, which every runner here is.

    # Never allowed to raise - diagnostic only, so a missing or unreadable /proc entry must not
    # fail the suite or mask the real timeout.
    fields: dict[str, str] = {}
    proc_dir = Path(f"/proc/{pid}")
    try:
        status_text = (proc_dir / "status").read_text()
        for line in status_text.splitlines():
            if line.startswith(("State:", "VmRSS:")):
                key, _, value = line.partition(":")
                fields[key] = value.strip()
    except OSError:
        pass
    try:
        fields["wchan"] = (proc_dir / "wchan").read_text().strip() or "(running)"
    except OSError:
        pass
    return fields


def _shutdown(proc: subprocess.Popen[str], run_label: str, timeout_s: float = 15.0) -> int:
    # SIGINT, not SIGTERM/terminate(): run_generic_integration.py's own graceful-shutdown path
    # (FRAM/SCD30 flush) only runs on KeyboardInterrupt (see that module's own __main__ block
    # comment) - a real SIGTERM would skip it entirely and lose this run's persisted state.
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        start = time.monotonic()
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            # Capture what the wedged process was doing before killing it, so a recurrence is
            # self-diagnosing from the CI job log alone rather than leaving only "exit code -9" -
            # which is all this ever left behind before.
            elapsed = time.monotonic() - start
            diag = _proc_diagnostic_fields(proc.pid)
            log_file = getattr(proc, "ci_log_file", None)
            tail = ""
            if log_file is not None:
                tail = "\n".join(_read_log(Path(log_file.name)).splitlines()[-20:])
            print(
                f"DIAG: {run_label}: SIGINT ignored for {elapsed:.1f}s (timeout={timeout_s}s), "
                f"about to SIGKILL pid={proc.pid} - /proc fields: {diag or '(unavailable)'}",
            )
            if tail:
                print(f"DIAG: {run_label}: last 20 log lines before SIGKILL:\n{tail}")
            proc.kill()
            proc.wait(timeout=_KILL_REAP_TIMEOUT_S)
    ec = proc.returncode if proc.returncode is not None else -1
    _close_log_and_check_memory_safety(proc, run_label)
    return ec


def _wait_exit(proc: subprocess.Popen[str], run_label: str, timeout_s: float) -> int:
    # For bounded (--duration N) runs that exit on their own - no signal needed or wanted.
    try:
        ec = proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=_KILL_REAP_TIMEOUT_S)
        ec = -1
    _close_log_and_check_memory_safety(proc, run_label)
    return ec


def _read_log(log_path: Path) -> str:
    try:
        return log_path.read_text(errors="replace")
    except FileNotFoundError:
        return ""


def _count_verbose_log_lines(log_text: str) -> int:
    count = 0
    for line in log_text.splitlines():
        for prefix in _VERBOSE_LOG_PREFIXES:
            if line.startswith(prefix + " "):
                count += 1
                break
    return count


def _would_have_triggered_count(log_text: str) -> int | None:
    # run_generic_integration.py's own unconditional shutdown line (see main()'s finally block) -
    # "...shutdown: would_have_triggered_count=N". Returns None if the line was never printed
    # (e.g. the process crashed before reaching its own finally block).
    for line in log_text.splitlines():
        if "would_have_triggered_count=" in line:
            try:
                return int(line.rsplit("=", 1)[1].strip())
            except ValueError:
                return None
    return None


_MEM_SAMPLE_LINE_FIELD_COUNT = 3  # "MEM_SAMPLE", the timestamp, the byte count


def _parse_mem_samples(log_text: str) -> list[tuple[float, int]]:
    # The twin's _mem_sampler() prints one MEM_SAMPLE line per interval - the same captured-log
    # pattern _would_have_triggered_count() already reads for its own internal-only value.
    # Malformed lines are skipped rather than raising, matching that function's tolerance.
    samples: list[tuple[float, int]] = []
    for line in log_text.splitlines():
        if not line.startswith("MEM_SAMPLE "):
            continue
        parts = line.split()
        if len(parts) != _MEM_SAMPLE_LINE_FIELD_COUNT:
            continue
        try:
            samples.append((float(parts[1]), int(parts[2])))
        except ValueError:
            continue
    return samples


def _build_dns_query(query_id: int = _DNS_QUERY_ID, qname: str = "example.com") -> bytes:
    header = struct.pack(">HHHHHH", query_id, 0x0100, 1, 0, 0, 0)  # ID, flags(RD), QDCOUNT=1
    question = b"".join(bytes([len(part)]) + part.encode() for part in qname.split("."))
    question += b"\x00" + struct.pack(">HH", 1, 1)  # root label, QTYPE=A, QCLASS=IN
    return header + question


def _try_dns_query(host: str, timeout: float = 1.0) -> bool:
    query = _build_dns_query()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(query, (host, DNS_PORT))
        data, _addr = sock.recvfrom(512)
        if len(data) < _DNS_RESPONSE_HEADER_LEN:
            return False
        resp_id, flags = struct.unpack(">HH", data[:4])
        return resp_id == _DNS_QUERY_ID and bool(flags & 0x8000)  # QR bit set = a real response, not an echo
    except OSError:
        return False
    finally:
        sock.close()


def _route_leaves_host(host: str, port: int) -> bool:
    # A UDP connect() sends nothing: it is the route lookup the twin's own UDPSocket makes on this same host, and
    # it fails (ENETUNREACH) where no route leaves - a network namespace holding only lo, for one.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect((host, port))
        except OSError:
            return False
    return True


def _ntp_unreachable_verdict(nums: list[Any], *, route: bool) -> tuple[bool, str]:
    # Run 9's check: a request that leaves this host goes unanswered (NTP_NO_REPLY); with no route out the send
    # itself fails (NTP_NOT_SENT). Exactly the one the route predicts is logged, never the other.
    expected, other = ("NTP_NO_REPLY", "NTP_NOT_SENT") if route else ("NTP_NOT_SENT", "NTP_NO_REPLY")
    why = "a route to it leaves this host, so the request goes out unanswered" if route else "no route to it leaves this host, so the request is never sent"
    ok = code("E", expected) in nums and code("E", other) not in nums
    return ok, f"Run 9: NTP logged errno {code('E', expected)} ({expected}), not {other}, for {_NTP_UNREACHABLE_HOST}: {why} (history {nums})"


def _wait_for_dns_answer(host: str, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _try_dns_query(host):
            return True
        time.sleep(_DNS_POLL_S)
    return False


def _bus_fault_drivers(ctx: RunContext) -> list[str]:
    # The sorted subset of ctx.drivers this suite knows how to fault. Every real device's set is
    # covered today, so it filters nothing - but it stays a filter so an untaught driver is
    # skipped rather than raising KeyError in Run 3/4.

    # That skip is SILENT, and it has cost real coverage: the ISL29125 arrived with its own
    # fault-capable fake and sat outside every run here until 2026-09-18. A new bus-attached
    # driver joins _BUS_FAULT_OPS/_DRIVER_ERRCOUNT_NAME/_MEASUREMENT_DRIVERS in the same change.
    return sorted(d for d in ctx.drivers if d in _BUS_FAULT_OPS)


def _healthy_store_fault_drivers(ctx: RunContext) -> list[str]:
    # Run 5c's own sweep set: every bus-fault-injectable driver this device wires EXCEPT the store
    # itself. Faulting `fram` is precisely what voids the chip-healthy premise Run 5c exists to
    # prove, which is why Run 3's matrix (which does fault it) can never stand in for this one.
    return [driver for driver in _bus_fault_drivers(ctx) if driver != "fram"]


def _run_1_baseline(ctx: RunContext) -> None:
    # ---- Run 1: fresh boot, walk every GET endpoint, PUT settings to carry forward. ----
    log1 = ctx.logs_dir / "run1_baseline.log"
    proc = _spawn(ctx, [], log1)
    try:
        _wait_until_serving(proc)
        for path in ("/measurements", "/sensors", "/networking", "/system", "/notification", "/status", "/"):
            status, _ = _http("GET", path)
            _check(condition=status == _HTTP_OK, msg=f"Run 1: GET {path} -> 200")

        status, body = _http("PUT", "/system", {"DebugLevel": _TEST_DEBUG_LEVEL})
        _check(condition=status == _HTTP_OK and body.get("result", {}).get("DebugLevel") in ("Valid", "Unchanged"), msg=f"Run 1: PUT /system DebugLevel={_TEST_DEBUG_LEVEL} accepted")
        status, body = _http("GET", "/system")
        _check(condition=status == _HTTP_OK and body.get("DebugLevel") == _TEST_DEBUG_LEVEL, msg=f"Run 1: GET /system reflects DebugLevel={_TEST_DEBUG_LEVEL} immediately")

        status, body = _http("PUT", "/notification", {"WarnCO2": _TEST_WARN_CO2})
        _check(condition=status == _HTTP_OK and body.get("result", {}).get("WarnCO2") in ("Valid", "Unchanged"), msg=f"Run 1: PUT /notification WarnCO2={_TEST_WARN_CO2} accepted")

        status, body = _http("PUT", "/sensors", {"SCD30": {"MeasInterval": _TEST_SCD30_MEAS_INT}})
        _check(condition=status == _HTTP_OK and body.get("result", {}).get("SCD30", {}).get("MeasInterval") in ("Valid", "Unchanged"), msg=f"Run 1: PUT /sensors SCD30.MeasInterval={_TEST_SCD30_MEAS_INT} accepted")

        status, body = _http("PUT", "/networking", {"Hostname": "ci-digital-twin"})
        _check(condition=status == _HTTP_OK and body.get("result", {}).get("Hostname") in ("Valid", "Unchanged"), msg="Run 1: PUT /networking Hostname accepted")

        status = _put_reset_errors_timed("Run 1")
        _check(condition=status == _HTTP_OK, msg="Run 1: PUT /status ResetErrors accepted")
    except Exception as exc:  # CI orchestration: surface any failure as a suite failure, not a crash
        _fail(f"Run 1 (baseline boot + settings): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 1")
        _check(condition=ec == 0, msg=f"Run 1: clean shutdown (exit code {ec})")
    _check(condition=FRAM_STATE_PATH.exists() and SCD30_STATE_PATH.exists(), msg="Run 1: FRAM/SCD30 state files were persisted to disk on shutdown")


def _run_2_reboot_settings_persistence(ctx: RunContext) -> None:
    # ---- Run 2: reboot from persisted state - verbose logging from boot, settings survived. ----
    log2 = ctx.logs_dir / "run2_reboot_settings_persistence.log"
    proc = _spawn(ctx, [], log2)
    try:
        _wait_until_serving(proc)
        status, body = _http("GET", "/system")
        _check(condition=status == _HTTP_OK and body.get("DebugLevel") == _TEST_DEBUG_LEVEL, msg=f"Run 2: DebugLevel={_TEST_DEBUG_LEVEL} survived a real process restart (persistence of settings)")
        status, body = _http("GET", "/notification")
        _check(condition=status == _HTTP_OK and body.get("WarnCO2") == _TEST_WARN_CO2, msg="Run 2: WarnCO2 survived a real process restart")
        status, body = _http("GET", "/sensors")
        _check(condition=status == _HTTP_OK and body.get("SCD30", {}).get("MeasInterval") == _TEST_SCD30_MEAS_INT, msg="Run 2: SCD30 MeasInterval survived a real process restart")
        status, body = _http("GET", "/networking")
        _check(condition=status == _HTTP_OK and body.get("Hostname") == "ci-digital-twin", msg="Run 2: Hostname survived a real process restart")
        time.sleep(3.0)  # let a bootup/sensor-read cycle actually happen under the now-persisted DebugLevel=5
    except Exception as exc:
        _fail(f"Run 2 (reboot + settings persistence): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 2")
        _check(condition=ec == 0, msg=f"Run 2: clean shutdown (exit code {ec})")
    verbose_lines = _count_verbose_log_lines(_read_log(log2))
    _check(condition=verbose_lines >= _MIN_VERBOSE_LOG_LINES, msg=f"Run 2: bootup produced verbose (DebugLevel={_TEST_DEBUG_LEVEL}) log output from multiple modules ({verbose_lines} matching lines)")


def _run_3_sustained_bus_fault_matrix(ctx: RunContext) -> None:
    # ---- Run 3: reboot with a sustained bus-fault matrix across every bus-level error-counted
    # module this device wires, from ctx.drivers rather than a list. Proves the system keeps
    # logging and that the watchdog survives sustained immediately-raised errors. ----
    log3 = ctx.logs_dir / "run3_sustained_bus_fault_matrix.log"
    fault_drivers = _bus_fault_drivers(ctx)
    fault_args: list[str] = []
    for driver in fault_drivers:
        fault_args += ["--fault", f"{driver}:{_BUS_FAULT_OPS[driver]}:{_BUS_FAULT_ERROR_COUNT}"]
    proc = _spawn(ctx, fault_args, log3)
    try:
        _wait_until_serving(proc)
        # Wait for every faulted module to have recorded a real error rather than sleeping a
        # guess: a fixed sleep encodes the host-speed assumption that made the old Run 4 flaky.
        # Keyed on "E" entries, never the raw counter, which a "W" recovery notice also bumps.
        errcount_names = [_DRIVER_ERRCOUNT_NAME[d] for d in fault_drivers]
        faulted = {name: _wait_for_error_type_count(name, 1, timeout_s=_FIRST_FAULT_WAIT_S) for name in errcount_names}
        for path in ("/measurements", "/sensors", "/status"):
            status, _ = _http("GET", path)
            _check(condition=status == _HTTP_OK, msg=f"Run 3: GET {path} still returns 200 under a sustained bus-fault matrix (graceful degradation)")
        for name, entry in faulted.items():
            _check(condition=_error_type_count(entry) > 0, msg=f"Run 3: {name}'s injected sustained fault was recorded as a real error, not just a warning ({entry!r})")
    except Exception as exc:
        _fail(f"Run 3 (sustained bus-fault matrix): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 3")
        _check(condition=ec == 0, msg=f"Run 3: process survived the sustained bus-fault matrix without crashing (exit code {ec})")
    wdt3 = _would_have_triggered_count(_read_log(log3))
    _check(condition=wdt3 == 0, msg=f"Run 3: watchdog never starved under sustained-but-bounded bus errors (would_have_triggered_count={wdt3!r})")


def _run_4_bus_fault_persistence_sweep(ctx: RunContext) -> None:
    # ---- Run 4: reboot fault-free after Run 3's matrix - what must reset, and that every
    # faulted bus comes back. With FRAM faulted throughout Run 3, the swept drivers must read
    # back 0, which is deterministic and is what this run proves. ----

    # It deliberately does NOT assert that SGP40's history survived Run 3, which it cannot: that
    # run faults `fram:write`, so nothing logged there ever reached the chip. Losing history when
    # the chip was unavailable is accepted (owner, 2026-09-11), and Run 5b proves the real claim.

    # The `counter > 0` check that once stood here was unsound twice over: counter includes "W",
    # so only a FRESH warning from this boot satisfied it, and waiting on that warning is a
    # host-speed race - it lands before the sample on x86 and after it on the bench Pi4.

    # FRAM's own log is excluded from the reset-to-0 sweep below for the same root cause a layer
    # down: Run 3's fault can leave a chunk torn, and the self-healing read correctly logs that
    # as a fresh FRAM entry on this boot - not persisted data, and not a defect.
    log4 = ctx.logs_dir / "run4_bus_fault_persistence_sweep.log"
    proc = _spawn(ctx, [], log4)
    try:
        _wait_until_serving(proc)
        fault_drivers = _bus_fault_drivers(ctx)
        for driver in fault_drivers:
            if driver not in _NO_PERSIST_WHEN_FRAM_FAULTED:
                continue  # WIFI's own reset check is Run 8, after its own fault run (Run 7)
            name = _DRIVER_ERRCOUNT_NAME[driver]
            entry = _errcount_required(name)
            _check(condition=entry.get("counter", -1) == 0, msg=f"Run 4: {name}'s error count correctly did NOT persist across reboot (FRAM was faulted dead for all of Run 3, so nothing it logged could reach the chip) ({entry!r})")
        # Every bus Run 3 faulted must be live again, not merely answering 200 with stale state -
        # this is the recovery half of Run 3's story, and the one claim about SGP40 here that does
        # not depend on what did or didn't reach the FRAM.
        status, body = _http("GET", "/measurements")
        readings = body if status == _HTTP_OK and isinstance(body, dict) else {}
        for driver in fault_drivers:
            if driver not in _MEASUREMENT_DRIVERS:
                continue
            name = _DRIVER_ERRCOUNT_NAME[driver]
            _check(condition=bool(readings.get(name)), msg=f"Run 4: {name} produces real readings again after a run in which every bus (FRAM included) was faulted throughout ({readings.get(name)!r})")
    except Exception as exc:
        _fail(f"Run 4 (bus-fault persistence-correctness sweep): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 4")
        _check(condition=ec == 0, msg=f"Run 4: clean shutdown (exit code {ec})")


def _run_5_recovery_after_bounded_fault(ctx: RunContext) -> dict[str, Any]:
    # ---- Run 5: clean boot with a small BOUNDED fault, proving recovery - the half Run 3 cannot
    # show, since it only proves the system survives while still broken. SGP40 is on every real
    # device (Part L.3), so this needs no device-conditional logic. ----
    _clean_state()
    log5 = ctx.logs_dir / "run5_recovery_after_bounded_fault.log"
    proc = _spawn(ctx, ["--fault", f"sgp40:writeto:{_BOUNDED_FAULT_COUNT}"], log5)
    entry2: dict[str, Any] = {}
    try:
        _wait_until_serving(proc)
        # Poll rather than sleep a guessed interval: the fault is exhausted when the third failure
        # lands, which is a real event to wait for, not a wall-clock duration to assume.
        entry = _wait_for_failure_events("SGP40", _BOUNDED_FAULT_COUNT, timeout_s=_ERROR_COUNT_WAIT_S)
        errors_after_exhaustion = _failure_events(entry)
        _check(condition=errors_after_exhaustion == _BOUNDED_FAULT_COUNT, msg=f"Run 5: SGP40's bounded fault ({_BOUNDED_FAULT_COUNT} failures) was fully recorded, no more ({entry!r})")
        time.sleep(_PAST_EXHAUSTION_WAIT_S)  # a few more cycles past exhaustion - real ("E") errors should NOT keep climbing
        # (a "W" recovery notice may legitimately appear here - _failure_events() discounts it)
        entry2 = _errcount("SGP40")
        _check(condition=_failure_events(entry2) == errors_after_exhaustion, msg=f"Run 5: SGP40's real error count stopped climbing once the fault cleared (recovery) ({entry2!r})")
        status, body = _http("GET", "/measurements")
        sgp40_reading = body.get("SGP40", {}) if status == _HTTP_OK and isinstance(body, dict) else {}
        _check(condition=status == _HTTP_OK and bool(sgp40_reading), msg=f"Run 5: SGP40 measurements resumed after recovery ({sgp40_reading!r})")
    except Exception as exc:
        _fail(f"Run 5 (recovery after a bounded fault): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 5")
        _check(condition=ec == 0, msg=f"Run 5: clean shutdown (exit code {ec})")
    return entry2


def _run_5b_error_log_restore_is_all_or_nothing(ctx: RunContext, written: dict[str, Any]) -> None:
    # ---- Run 5b: reboot straight onto Run 5's state, fault-free. Run 5 left exactly
    # _BOUNDED_FAULT_COUNT failures on a healthy chip, written through on every push, so they
    # SHOULD come back.

    # But Run 5 shut down abruptly, which can catch a chunk write in flight: both status bytes go
    # to _STATUS_BUSY before the payload is touched, so an interrupted write leaves them there,
    # the restore read fails and its fallback stores the empty ring. Roughly 1 restart in 8.

    # That loss is accepted (owner, 2026-09-11), so this asserts what holds unconditionally: the
    # restore is ALL-OR-NOTHING, the dual-block+CRC+busy-flag protocol's actual job. Run 5c
    # covers the case that must never lose anything; mirrored at the mock and flash tiers.

    # A timing race cannot make this fail spuriously: the poll returns either the fully restored ring
    # or a still-empty one (setup()'s restore is a single history.extend(), never observable half
    # done), and both satisfy the invariant. ----
    log5b = ctx.logs_dir / "run5b_error_log_restore_is_all_or_nothing.log"
    proc = _spawn(ctx, [], log5b)
    try:
        _wait_until_serving(proc)
        for name in _PERSISTED_ERROR_MODULES:
            # The webserver answers well before the FRAM-backed loggers finish their own setup(),
            # and that setup() IS the restore - so poll for it rather than sampling immediately,
            # the same host-speed trap the old Run 4 check fell into, one layer down.
            entry = _wait_for_error_type_count(name, _error_type_count(written), timeout_s=_ERROR_COUNT_WAIT_S)
            _check(condition=_restore_is_all_or_nothing(written, entry), msg=f"Run 5b: {name}'s FRAM-backed history came back all-or-nothing after an abrupt restart - Run 5's ring and count or no error at all, never a partial remnant (wrote {written!r}, restored {entry!r})")
    except Exception as exc:
        _fail(f"Run 5b (error-log restore is all-or-nothing): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 5b")
        _check(condition=ec == 0, msg=f"Run 5b: clean shutdown (exit code {ec})")


def _run_5c_storage_paused_shutdown_never_loses_the_error_log(ctx: RunContext) -> None:
    # ---- Run 5c: the case that must NEVER lose anything, a commanded reboot. _reboot() pauses
    # permanent storage first so no chunk operation is in flight, and mempause is that same pause
    # over REST - so no status byte is left busy and the restore is deterministic, 20/20 measured.

    # This is what makes the pair sound: Run 5b alone would pass even if persistence never worked at
    # all (an empty ring satisfies all-or-nothing), which is exactly the hole the old Run 4 check had.
    #
    # Device-wide since 2026-09-18: every bus-fault-injectable driver this device wires gets its
    # own chip-healthy fault link, and the final reboot then checks the whole errcount table.
    #
    # One fault per PROCESS, chained onto the previous link's state: three at once exhaust the
    # task-restart budget and the device reboots itself mid-run, which is not the commanded
    # reboot under test (Part C.4.1). Chaining also makes each link its own restore check. ----
    _clean_state()
    drivers = _healthy_store_fault_drivers(ctx)
    recorded: dict[str, int] = {}
    snapshot_table: dict[str, dict[str, Any]] = {}
    for driver in drivers:
        name = _DRIVER_ERRCOUNT_NAME[driver]
        before_link = snapshot_table.get(name, {})
        log5c_a = ctx.logs_dir / f"run5c_a_{driver}_record_then_pause_storage.log"
        proc = _spawn(ctx, ["--fault", f"{driver}:{_BUS_FAULT_OPS[driver]}:{_BOUNDED_FAULT_COUNT}"], log5c_a)
        try:
            _wait_until_serving(proc)
            for earlier, expected in recorded.items():
                found = _error_type_count(_errcount_required(earlier))
                _check(condition=found == expected, msg=f"Run 5c: {earlier}'s {expected} chip-healthy error(s) were still on the chip when {name}'s own fault link booted ({found} found)")
            _wait_for_error_type_count(name, 1, timeout_s=_FIRST_FAULT_WAIT_S)
            # Snapshot only once the bounded fault has stopped producing entries. Taken mid-fault,
            # it would be compared after the reboot against entries that landed after it, and a run
            # that lost nothing at all would read as a persistence failure.
            settled = _wait_for_error_counts_to_settle([name], timeout_s=_LONG_WAIT_S)
            _check(condition=settled[name] > 0, msg=f"Run 5c: {name}'s bounded fault was recorded as a real error against a HEALTHY store ({settled!r})")
            if name == "SGP40":
                sgp40 = _errcount_required(name)
                _check(condition=_link_failures(before_link, sgp40) == _BOUNDED_FAULT_COUNT, msg=f"Run 5c: SGP40 recorded all {_BOUNDED_FAULT_COUNT} bounded failures and no more before the commanded reboot (before {before_link!r}, after {sgp40!r})")
            snapshot_table = _errcount_all()
            snapshot_errors = _error_type_count(snapshot_table.get(name, {}))
            status, _ = _http("PUT", "/system", {"SystemCmd": "mempause"})
            _check(condition=status == _HTTP_OK, msg=f"Run 5c: PUT /system mempause accepted before {name}'s reboot (status {status})")
            paused = _wait_for_mem_paused(expected=True, timeout_s=_MEM_PAUSED_WAIT_S)
            _check(condition=paused, msg=f"Run 5c: storage actually reported paused before {name}'s shutdown, not just a 200")
            time.sleep(_IN_FLIGHT_SETTLE_S)  # let anything already in flight finish - nothing new can start while paused
            at_pause = _error_type_count(_errcount_required(name))
            _check(condition=at_pause == snapshot_errors, msg=f"Run 5c: nothing more was logged for {name} between the snapshot and the storage pause, so the snapshot is what the chip actually holds ({snapshot_errors} snapshot, {at_pause} at the pause)")
            recorded[name] = snapshot_errors
        except Exception as exc:
            _fail(f"Run 5c ({driver}: record then pause storage): {exc!r}")
        finally:
            ec = _shutdown(proc, f"Run 5c-a ({driver})")
            _check(condition=ec == 0, msg=f"Run 5c: clean shutdown after {name}'s storage pause (exit code {ec})")

    log5c_b = ctx.logs_dir / "run5c_b_history_survived_the_commanded_reboot.log"
    proc = _spawn(ctx, [], log5c_b)
    try:
        _wait_until_serving(proc)
        _wait_for_error_type_count("SGP40", recorded.get("SGP40", 1), timeout_s=_ERROR_COUNT_WAIT_S)
        restored_table = _errcount_all()
        for name, expected in recorded.items():
            entry = restored_table.get(name, {})
            restored = _error_type_count(entry)
            _check(condition=restored == expected, msg=f"Run 5c: {name}'s {expected} chip-healthy error(s) survived a reboot taken with storage paused - the one case that must never lose them ({restored} found, {entry!r})")
            _check(condition=entry.get("counter", 0) >= expected, msg=f"Run 5c: {name}'s persisted error COUNT was restored too, not just the history ring ({entry!r})")
        # Every OTHER registered source in the same breath - the ones with no fault-injection seam
        # (SYSTEM/NOTIFY/NTP/WEBSERVER/DNSSRV, every FRAM-backed CFGMGR_*, dev's two uart_link instances). A
        # fresh entry from THIS boot is legitimate, so the claim is "nothing was lost", not equality.
        for name, before in snapshot_table.items():
            if name in recorded or name in _IN_MEMORY_ONLY_ERROR_SOURCES:
                continue
            had = _error_type_count(before)
            now = _error_type_count(restored_table.get(name, {}))
            _check(condition=now >= had, msg=f"Run 5c: {name} kept the {had} error(s) it had logged before the commanded reboot ({now} found, {restored_table.get(name)!r})")
        _check(condition=sorted(restored_table) == sorted(snapshot_table), msg=f"Run 5c: the reboot registered exactly the same error sources, so no row silently dropped out of this sweep (before {sorted(snapshot_table)!r}, after {sorted(restored_table)!r})")
        _check(condition=_mem_paused() is False, msg="Run 5c: the storage pause did NOT survive the reboot (it is RAM-only by design)")
        # Every device wires SGP40's compensation source to SCD30, and a read racing SCD30's
        # cold start used to log a spurious E18/W14 pair (Part C.14.2, fixed 2026-09-12). Now
        # only a settle window, keeping the check below about ResetErrors and not a boot read.
        time.sleep(3.0)
        # The restored history must not be a read-only relic: ResetErrors has to clear it on the
        # chip, for every swept source at once. Issued after the poll confirmed setup() ran, so
        # this is the ordinary case; a reset issued BEFORE setup() is covered separately (C.7).
        status = _put_reset_errors_timed("Run 5c")
        _check(condition=status == _HTTP_OK, msg=f"Run 5c: PUT /status ResetErrors accepted (status {status})")
        cleared_table = _errcount_all()
        for name in recorded:
            entry = cleared_table.get(name, {})
            _check(condition=_error_type_count(entry) == 0, msg=f"Run 5c: {name}'s restored history was actually cleared by ResetErrors, not just masked ({entry!r})")
    except Exception as exc:
        _fail(f"Run 5c (history survived the commanded reboot): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 5c-b")
        _check(condition=ec == 0, msg=f"Run 5c: clean shutdown (exit code {ec})")


def _run_6_configure_ssid(ctx: RunContext) -> None:
    # ---- Run 6: clean boot, configuring a real persisted SSID for Run 7. A genuine
    # STA-connect-failure cycle needs a real SSID, not the unconfigured empty-string shortcut -
    # the same distinction the in-process twin integration test makes. ----
    _clean_state()
    log6 = ctx.logs_dir / "run6_configure_ssid.log"
    proc = _spawn(ctx, [], log6)
    try:
        _wait_until_serving(proc)
        status, body = _http("PUT", "/networking", {"SSID": "digital-twin-test-ssid"})
        _check(condition=status == _HTTP_OK and body.get("result", {}).get("SSID") in ("Valid", "Unchanged"), msg="Run 6: PUT /networking SSID accepted")
    except Exception as exc:
        _fail(f"Run 6 (configure SSID for WiFi test): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 6")
        _check(condition=ec == 0, msg=f"Run 6: clean shutdown (exit code {ec})")


def _run_7_wifi_hotspot_dns(ctx: RunContext) -> None:
    # ---- Run 7: reboot with scripted repeated STA-connect failures. Drives the real hotspot
    # fallback state machine, then confirms the real CaptiveDNS answers a real UDP query rather
    # than merely that internal state flipped. Mandatory infrastructure, so no device logic.

    # Only possible because of _unix_port_udp_addr_shim.py, which works around three Unix-port
    # socket quirks that made a real UDP round trip impossible here - all three correct behavior
    # for real rp2 hardware, so src/ stays untouched and the shim is entirely twin-side. ----
    log7 = ctx.logs_dir / "run7_wifi_hotspot_dns.log"
    proc = _spawn(
        ctx,
        ["--wifi-outcome", "no_ap"] * _WIFI_SCRIPTED_FAILURES,
        log7,
    )
    try:
        _wait_until_serving(proc)
        # Waits for the FULL scripted failure count, not just the first: hotspot activation, and
        # so the CaptiveDNS, only starts on the fifth. Waiting for all five and then giving DNS
        # its own budget beats one guessed timeout covering both phases, as a real runner showed.
        entry = _wait_for_errcount_above("WIFI", _WIFI_PERSISTED_EVENTS - 1, timeout_s=_LONG_WAIT_S)
        _check(condition=entry.get("counter", 0) >= _WIFI_PERSISTED_EVENTS, msg=f"Run 7: all {_WIFI_SCRIPTED_FAILURES} repeated WiFi connect failures drove real hotspot fallback, and both they and the fallback were recorded in WIFI's error counter ({entry!r})")
        logged = _error_type_count(entry, type_char="W")
        _check(condition=logged == _WIFI_PERSISTED_WARNINGS, msg=f"Run 7: those {_WIFI_SCRIPTED_FAILURES} identical verdicts spent one history slot, not one each, and the fallback one more ({_WIFI_PERSISTED_WARNINGS}) - the ring still holds what preceded the outage ({entry!r})")
        # 30s timed out twice on real runners even after the errcount-wait fix, and the cause
        # was a red herring: the interpreter lacked CAP_NET_BIND_SERVICE, so the bind to port 53
        # silently failed and no timeout would have helped (README.md's run 7 entry).

        # Left at 90s with the real fix in: this is a fallback path, not a hot one, so the slack
        # costs nothing when the answer arrives early.
        answered = _wait_for_dns_answer(HOST, timeout_s=_LONG_WAIT_S)
        _check(condition=answered, msg="Run 7: the real CaptiveDNS answered a real UDP DNS query after WiFi hotspot fallback")
        status, _ = _http("GET", "/status")
        _check(condition=status == _HTTP_OK, msg="Run 7: webserver stayed reachable throughout the WiFi hotspot-fallback transition")
    except Exception as exc:
        _fail(f"Run 7 (WiFi hotspot fallback + DNS): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 7")
        _check(condition=ec == 0, msg=f"Run 7: process survived the WiFi hotspot-fallback transition without crashing (exit code {ec})")


def _run_8_wifi_persistence_and_configure_ntp(ctx: RunContext) -> None:
    # ---- Run 8: reboot fault-free - WIFI's own persistence-correctness check, plus configure an
    # unreachable NTP host (persisted) for Run 9.
    #
    # WIFI's own log is FRAM-backed under the implicit-FRAM-wiring rule, so like SGP40's Run 5b
    # it follows the all-or-nothing abrupt-restart guarantee rather than resetting to 0: Run 7's
    # ordinary SIGINT shutdown can still catch a chunk write after the counter has updated.

    # This once asserted counter==0, under a pre-WP1 in-memory-only assumption real CI never
    # exercised until WP1/WP2 went through it - stale, not ambiguous. ----
    log8 = ctx.logs_dir / "run8_wifi_persistence_and_configure_ntp.log"
    proc = _spawn(ctx, [], log8)
    try:
        _wait_until_serving(proc)
        # Poll tolerantly, then re-read STRICTLY before asserting: this is the one check whose
        # expected set admits 0, so the poller's own {}-on-unreadable return would satisfy it.
        _wait_for_error_type_count("WIFI", _WIFI_PERSISTED_WARNINGS, timeout_s=_ERROR_COUNT_WAIT_S, type_char="W")
        entry = _errcount_required("WIFI")
        restored = _error_type_count(entry, type_char="W")
        _check(condition=restored in (0, _WIFI_PERSISTED_WARNINGS), msg=f"Run 8: WIFI's FRAM-backed history came back all-or-nothing after an abrupt restart - never a partial {restored}-entry remnant ({entry!r})")
        _check(condition=entry.get("counter", 0) in (0, _WIFI_PERSISTED_EVENTS), msg=f"Run 8: and the counter came back with it, still naming all {_WIFI_SCRIPTED_FAILURES} attempts and the fallback rather than the slots they share ({entry!r})")
        # RFC 5737 TEST-NET-1: no server answers it, a reproducible "unreachable" host rather than incidental
        # sandbox network policy; whether a route carries the request out decides Run 9's code (_route_leaves_host()).
        status, body = _http("PUT", "/networking", {"NTPHost": _NTP_UNREACHABLE_HOST})
        _check(condition=status == _HTTP_OK and body.get("result", {}).get("NTPHost") in ("Valid", "Unchanged"), msg="Run 8: PUT /networking NTPHost (unreachable) accepted")
    except Exception as exc:
        _fail(f"Run 8 (WIFI persistence check + configure unreachable NTP): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 8")
        _check(condition=ec == 0, msg=f"Run 8: clean shutdown (exit code {ec})")


def _run_9_ntp_unreachable(ctx: RunContext) -> None:
    # ---- Run 9: reboot with NTP permanently unreachable. The webserver must stay healthy, and the
    # NTP task must handle it in place (SPECIFICATION.md Part C.7.2): a task that ends costs SYSTEM a
    # restart, and three of those used to reboot the device about every four minutes. ----
    log9 = ctx.logs_dir / "run9_ntp_unreachable.log"
    proc = _spawn(ctx, [], log9)
    try:
        _wait_until_serving(proc)
        system_before = _errcount_required("SYSTEM").get("counter", 0)
        # 90s: the old five-failure streak ended the task after about 60s of 10s-tick attempts, so
        # a regression shows here without waiting out the whole old reboot cycle.
        time.sleep(_NTP_UNREACHABLE_WATCH_S)
        status, _ = _http("GET", "/system")
        _check(condition=status == _HTTP_OK, msg="Run 9: webserver stayed fully healthy with NTP permanently unreachable")
        ntp = _errcount_required("NTP")
        nums = [item.get("num") for item in ntp.get("history", []) if isinstance(item, dict)]
        ok, msg = _ntp_unreachable_verdict(nums, route=_route_leaves_host(_NTP_UNREACHABLE_HOST, _NTP_PORT))
        _check(condition=ok, msg=msg)
        system_after = _errcount_required("SYSTEM").get("counter", 0)
        _check(condition=system_after == system_before, msg=f"Run 9: no task ended and was restarted while NTP failed (SYSTEM counter {system_before} -> {system_after})")
    except Exception as exc:
        _fail(f"Run 9 (NTP unreachable): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 9")
        _check(condition=ec == 0, msg=f"Run 9: clean shutdown (exit code {ec})")


def _run_10_watchdog_hang_backstop(ctx: RunContext) -> None:
    # ---- Run 10: the dedicated hang case - a real blocking sleep inside a chip fake, freezing
    # the interpreter past the WDT window to prove the simulated backstop engages, which Run 3's
    # bounded errors cannot. _fault_injection.py says why only this models a wedged bus.

    # --duration 15, not 0: SGP40's first bus access now queues behind BMP3xx's and SCD30's own
    # FRAM startup I/O, so the hang can fire well after readiness and 0 sometimes exited first.
    # README.md's "WDT._arm() late-feed backstop" has the account - both were found together. ----
    _clean_state()
    log10 = ctx.logs_dir / "run10_watchdog_hang_backstop.log"
    proc = _spawn(ctx, ["--hang", "sgp40:writeto:12", "--duration", "15"], log10)
    try:
        ec = _wait_exit(proc, "Run 10", timeout_s=_HANG_RUN_EXIT_WAIT_S)
        _check(condition=ec == 0, msg=f"Run 10: process survived a genuinely wedged bus and exited cleanly (exit code {ec})")
    except Exception as exc:
        _fail(f"Run 10 (watchdog hang backstop): {exc!r}")
        _wait_exit(proc, "Run 10", timeout_s=_FAILED_RUN_EXIT_WAIT_S)
    wdt10 = _would_have_triggered_count(_read_log(log10))
    _check(condition=wdt10 is not None and wdt10 >= 1, msg=f"Run 10: the watchdog backstop actually engaged for a genuinely wedged bus (would_have_triggered_count={wdt10!r})")


def _run_11b_full_ceiling_concurrency(ctx: RunContext) -> None:
    # ---- Run 11b: the admission ceiling under real simultaneous load, driven from THIS process: a
    # client sharing the DUT's heap measures its own buffers, not the firmware's (Part E.9; an
    # in-process attempt proved it, HEAP_FRAGMENTATION_MEASUREMENTS.md archive §9). ----
    _clean_state()
    try:  # a ceiling that cannot be read fails this run, never the whole suite and its later passes
        ceiling = _configured_max_connections(ctx.device)
    except Exception as exc:  # CI orchestration, the same as this run's own catch below
        _fail(f"Run 11b (full-ceiling concurrency): cannot read the device's ceiling: {exc!r}")
        return
    log11b = ctx.logs_dir / "run11b_full_ceiling_concurrency.log"
    proc = _spawn(ctx, [], log11b)
    try:
        _wait_until_serving(proc)
        # The heaviest real endpoints, not the cheapest: /sensors and /status both grow with the
        # device's own module count and are the two that stream (Part I.3).
        endpoints = ("/sensors", "/status", "/measurements", "/networking", "/system")
        for round_index in range(_CEILING_ROUNDS):
            # A slot is released in _serve()'s finally, AFTER the close is awaited, so it outlives the
            # response the client already holds (Part H.7.1) - round 0's too: the readiness probe's own
            # connection is still counted right after _wait_until_serving(), refusing one of a full burst.
            time.sleep(_SLOT_RELEASE_WAIT_S)
            results = _concurrent_get([endpoints[i % len(endpoints)] for i in range(ceiling)])
            # Every one of them, with a parsed JSON object: this burst IS the ceiling, so anything
            # short means the device cannot serve what its own config admits.
            served = sum(1 for r in results if isinstance(r, tuple) and r[0] == _HTTP_OK and isinstance(r[1], dict))
            _check(
                condition=served == ceiling,
                msg=f"Run 11b round {round_index}: all {ceiling} simultaneous connections served 200 with a parsed JSON body (got {served}; {_describe_results(results)})",
            )
        # Still healthy afterwards, so a burst that merely postponed its damage is still caught.
        status, _ = _http("GET", "/status")
        _check(condition=status == _HTTP_OK, msg="Run 11b: still serving after the ceiling bursts")
    except Exception as exc:  # CI orchestration: surface any failure as a suite failure, not a crash
        _fail(f"Run 11b (full-ceiling concurrency): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 11b")
        _check(condition=ec == 0, msg=f"Run 11b: clean shutdown (exit code {ec})")


@dataclass
class _SoakRun:
    # One boot's Run 11 raw results.

    http_failures: list[str]
    wdt_count: int | None
    shutdown_ec: int
    samples: list[int]
    trend_result: tuple[float, float, int, float, float] | None


def _run_11_soak_boot(ctx: RunContext, log_path: Path) -> _SoakRun:
    # ---- Run 11: a fresh clean boot for the soak check, driven entirely from THIS process like
    # Runs 1-10 ("Driver/DUT process separation") - warmup and cycle requests go over real HTTP,
    # never through the twin's own client.

    # The one thing that cannot move host-side, gc.mem_free(), is armed via
    # --mem-sample-interval-ms and read back from the captured log. Driven at ctx.gc_threshold
    # like every other run. ----
    _clean_state()
    proc = _spawn(ctx, ["--mem-sample-interval-ms", str(_MEM_SAMPLE_INTERVAL_MS)], log_path)
    http_failures: list[str] = []
    cycles_start: float | None = None
    cycles_end: float | None = None
    try:
        _wait_until_serving(proc)
        for _ in range(_SOAK_WARMUP_CYCLES):
            for path in _SOAK_ENDPOINTS:
                try:
                    _http("GET", path)
                except (OSError, http.client.HTTPException) as e:
                    # A real soak run must record a genuine allocation/transport failure as one
                    # more failure, never let it abort the whole run before every other endpoint
                    # and cycle has had its own chance to run.
                    http_failures.append(f"warmup: GET {path} -> {e!r}")
        cycles_start = time.time()
        for cycle in range(_SOAK_CYCLES):
            for path in _SOAK_ENDPOINTS:
                try:
                    status, _ = _http("GET", path)
                except (OSError, http.client.HTTPException) as e:
                    http_failures.append(f"cycle {cycle}: GET {path} -> {e!r}")
                    continue
                if status != _HTTP_OK:
                    http_failures.append(f"cycle {cycle}: GET {path} -> {status}")
        cycles_end = time.time()
    except Exception as exc:  # CI orchestration: surface any failure as a suite failure, not a crash
        http_failures.append(repr(exc))
    finally:
        ec = _shutdown(proc, "Run 11")

    wdt_count = _would_have_triggered_count(_read_log(log_path))
    samples: list[int] = []
    trend_result = None
    if cycles_start is not None and cycles_end is not None:
        log_text = _read_log(log_path)
        samples = [free for ts, free in _parse_mem_samples(log_text) if cycles_start <= ts <= cycles_end]
        if len(samples) // 4 >= 1:
            trend_result = _mem_trend(samples)
    return _SoakRun(http_failures=http_failures, wdt_count=wdt_count, shutdown_ec=ec, samples=samples, trend_result=trend_result)


def _run_11_soak(ctx: RunContext) -> None:
    # One boot, one verdict: a second boot never covers this one's failing trend (owner, 2026-09-26:
    # 'A retry or a longer timeout never counts as a race fix'). The self-calibrated tolerance is
    # what separates a leak from a noisy reactive-GC heap sampled on a timer.
    run = _run_11_soak_boot(ctx, ctx.logs_dir / "run11_soak.log")
    for failure in run.http_failures:
        print(f"FAIL: Run 11: {failure}")
    total_requests = (_SOAK_WARMUP_CYCLES + _SOAK_CYCLES) * len(_SOAK_ENDPOINTS)
    _check(condition=not run.http_failures, msg=f"Run 11: {total_requests} soak requests across every endpoint produced zero HTTP failures ({len(run.http_failures)} found)")
    _check(condition=run.wdt_count == 0, msg=f"Run 11: watchdog never starved across the soak (would_have_triggered_count={run.wdt_count!r})")
    _check(condition=run.shutdown_ec == 0, msg=f"Run 11: clean shutdown (exit code {run.shutdown_ec})")
    _check(condition=len(run.samples) // 4 >= 1, msg=f"Run 11: enough MEM_SAMPLE lines in the cycles window to compute a memory trend ({len(run.samples)} samples)")
    if run.trend_result is None:
        return  # too few samples - the check above already failed it
    trend, tolerance, quarter, early, late = run.trend_result
    print(
        f"Run 11 memory trend: min={min(run.samples)} max={max(run.samples)} "
        f"early_avg={early:.0f} late_avg={late:.0f} trend={trend:.0f} tolerance={tolerance:.0f} "
        f"quarter_size={quarter} samples={len(run.samples)}",
    )
    _check(condition=trend <= tolerance, msg=f"Run 11: gc.mem_free() trend ({trend:.0f} bytes decline) within the {tolerance:.0f}-byte tolerance (quarter_size={quarter})")


def _mem_trend(samples: list[int]) -> tuple[float, float, int, float, float] | None:
    # Pure trend-vs-tolerance arithmetic, split out of _run_11_soak() so it is unit-testable
    # without a live subprocess. Returns (trend, tolerance, quarter_size, early_avg, late_avg),
    # or None below four samples, which the caller's own _check() already reports.
    quarter = len(samples) // 4
    if quarter < 1:
        return None
    early = samples[:quarter]
    late = samples[-quarter:]
    early_avg = sum(early) / len(early)
    late_avg = sum(late) / len(late)
    trend = early_avg - late_avg  # positive: memory declined between quarters
    # Tolerance is this run's own noise level, not a historical constant. Each quarter's
    # INTERNAL spread stands in for the trend's true standard error - never the early-vs-late
    # difference, which a genuine leak inflates, loosening the tolerance just when it must hold.
    quarter_noise = max(statistics.pstdev(early), statistics.pstdev(late)) if quarter > 1 else 0.0
    tolerance = _MEM_TREND_TOLERANCE_SD_MULTIPLIER * quarter_noise
    return trend, tolerance, quarter, early_avg, late_avg


def run_suite(ctx: RunContext) -> None:
    # Runs the whole 14-run sequence (Runs 1-11 plus 5b, 5c, 11b) once at ctx.gc_threshold; main() says why the
    # whole function runs twice. It tallies nothing itself - _FAILURES is shared on purpose, so
    # main() prints one combined report naming every failure from either pass.
    global _CURRENT_PASS_LABEL
    _CURRENT_PASS_LABEL = f"[gc.threshold={ctx.gc_threshold}] "
    _CHECKS_PER_PASS[_CURRENT_PASS_LABEL] = 0
    ctx.logs_dir.mkdir(parents=True, exist_ok=True)

    # An exception that ends a pass early is recorded in the block before it propagates.
    try:
        _run_1_baseline(ctx)
        _run_2_reboot_settings_persistence(ctx)
        _run_3_sustained_bus_fault_matrix(ctx)
        _run_4_bus_fault_persistence_sweep(ctx)
        run5_entry = _run_5_recovery_after_bounded_fault(ctx)
        _run_5b_error_log_restore_is_all_or_nothing(ctx, run5_entry)
        _run_5c_storage_paused_shutdown_never_loses_the_error_log(ctx)
        _run_6_configure_ssid(ctx)
        _run_7_wifi_hotspot_dns(ctx)
        _run_8_wifi_persistence_and_configure_ntp(ctx)
        _run_9_ntp_unreachable(ctx)
        _run_10_watchdog_hang_backstop(ctx)
        _run_11_soak(ctx)
        _run_11b_full_ceiling_concurrency(ctx)
    except BaseException as exc:
        _SUMMARY.add("failed", f"{_CURRENT_PASS_LABEL}suite aborted: {type(exc).__name__}: {exc}")
        raise
    if _CHECKS_PER_PASS[_CURRENT_PASS_LABEL] == 0:
        _SUMMARY.add("vacuous", f"pass {_CURRENT_PASS_LABEL.strip()}")


def _drivers_in_plan(plan: dict[str, Any]) -> frozenset[str]:
    # The bus-attached `driver` identities this device's wiring plan declares - {"scd30",
    # "sgp40", "fram"} for a device without bmp3xx, and so on. Neopixel and notification never
    # appear, being GPIO-only, which is fine: the fault matrix targets bus-attached drivers.
    names: set[str] = set()
    for attachments in plan["buses"].values():
        for attachment in attachments:
            names.add(attachment["driver"])
    for attachment in plan["spi"].values():
        names.add(attachment["driver"])
    return frozenset(names)


def main() -> int:
    global _SUMMARY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--micropython-bin", required=True, help="path to the built MicroPython Unix-port binary")
    parser.add_argument("--device", default="wozi", help="which devices/<device>.toml-generated module to drive this suite against (default: wozi)")
    parser.add_argument("--logs-dir", default=str(REPO_ROOT / "digital_twin_ci_logs"), help="directory to write per-run subprocess logs into")
    args = parser.parse_args()

    # The block is printed on every exit, an exception's included; its code is the one returned.
    _SUMMARY = Summary("scripts/_digital_twin_ci_suite.py", unit="checks", levels=f"L2 ({args.device})", gc_stage="both")
    exit_code = 1
    try:
        exit_code = _run_both_passes(args)
    finally:
        exit_code = _SUMMARY.print(exit_code)
    return exit_code


def _run_both_passes(args: argparse.Namespace) -> int:
    module = f"sensortask_{args.device}"
    wiring_plan_path = GENERATED_SRC_DIR / f"{module}_wiring_plan.json"
    if not wiring_plan_path.exists():
        hint = "run scripts/_generate_sensortask_modules.py first (scripts/run_digital_twin_ci.sh already does this)"
        print(f"error: {wiring_plan_path} not found - {hint}", file=sys.stderr)
        _SUMMARY.add("failed", f"wiring plan {wiring_plan_path} missing", hint)
        return 1
    plan = json.loads(wiring_plan_path.read_text())

    base_ctx = RunContext(
        micropython_bin=args.micropython_bin,
        logs_dir=Path(args.logs_dir),  # overridden per pass below
        device=args.device,
        module=module,
        wiring_plan_path=wiring_plan_path,
        drivers=_drivers_in_plan(plan),
        gc_threshold=-1,  # overridden per pass below
    )

    # Runs the WHOLE suite twice, not just Run 11 (Part I.4(e)): it must pass clean at
    # MicroPython's own gc.threshold(-1), with zero MemoryErrors anywhere, BEFORE running again
    # at the chosen 32768, which is defense in depth and never itself why a run passes.

    # Order matters, -1 first, and each pass logs into its own subdirectory so a failure's logs
    # are never overwritten by the other.
    # @tunable gc.threshold_bytes = 32768
    for gc_threshold, subdir in ((-1, "gc_threshold_neg1"), (32768, "gc_threshold_32768")):
        ctx = replace(base_ctx, logs_dir=base_ctx.logs_dir / subdir, gc_threshold=gc_threshold)
        _clean_state()
        run_suite(ctx)

    print()
    return 1 if _FAILURES or _SUMMARY.failed else 0


if __name__ == "__main__":
    sys.exit(main())
