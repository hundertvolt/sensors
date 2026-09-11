#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Automated version of the manual digital-twin on-demand walkthrough - drives `digital_twin/run_generic_integration.py` as a real subprocess, over real HTTP/UDP, through a sequence of real process restarts, and asserts every step. Device-generic (BUILD_CHAIN_PLAN.md's Session 6.2): `--device` selects which real `devices/<device>.toml`-derived module + wiring plan to boot, defaulting to `wozi`. The bus-fault matrix (Run 3/4) is derived from that device's own wiring plan, never a hardcoded driver list - a device without `bmp3xx` (4 of the 6 real devices) simply never faults/checks it.
CPython/stdlib-only (the code under test still only ever runs under the real MicroPython Unix-port interpreter); invoked by `scripts/run_digital_twin_ci.sh` (which owns "clean"/"build", and the per-device `buildgen` generation step this suite's own `--device` depends on) as its "test" phase, once per device via CI's own `strategy.matrix` (see `.github/workflows/ci.yml`'s `digital-twin-e2e` job).
Full walkthrough and rationale: `digital_twin/README.md`'s "Automated CI suite" section."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import signal
import socket
import struct
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "digital_twin"
FRAM_STATE_PATH = STATE_DIR / "fram_state.json"
SCD30_STATE_PATH = STATE_DIR / "scd30_state.json"
CONFIG_DIR = STATE_DIR / "config"
GENERATED_SRC_DIR = REPO_ROOT / "build" / "generated_src"
# build/generated_src first: no static src/sensortask_wozi.py exists any more
# (BUILD_CHAIN_PLAN.md's Session 6 finish criterion) - scripts/run_digital_twin_ci.sh generates it
# (and every other real device's module + wiring plan, Session 6.2) fresh, via buildgen, into this
# gitignored directory before this suite ever runs.
MICROPYPATH = "build/generated_src:src:digital_twin:ext:frozen_modules:.frozen"
HOST = "127.0.0.1"
PORT = 18080  # a fixed, non-privileged, non-8080-default port - avoids colliding with a real
# manual `scripts/run_unix_port_integration.sh` run on the same machine.
DNS_PORT = 53  # captive_dns.py's DNSServer binds ("0.0.0.0", 53) unconditionally, real port only.

# print_log.py's own per-module PrintLog `name=` values (src/*.py's `_NAME` constants) - a verbose
# (DebugLevel=5) log line is `print(name, *args)`, so a line *starting* with one of these plus a
# space is real per-module log output, not run_generic_integration.py's own unconditional banner
# prints. Checked as a set (not all of them - some, like DNSSRV/NEOPIXEL, aren't guaranteed to log
# anything during this suite's short runs) to confirm verbose logging is genuinely flowing, not to
# pin every module's exact output. Includes BMP3XX even though 4 of the 6 real devices never
# construct that driver at all - harmless, since a prefix simply never matches on those devices'
# logs; not worth conditioning on ctx.drivers for a set membership check this loose.
_VERBOSE_LOG_PREFIXES = ("SYSTEM", "SGP40", "SCD30", "BMP3XX", "WEBSERVER", "NOTIFY", "WIFI", "NTP", "FRAM")

# Bus-fault-matrix knowledge, keyed by TOML `driver` identity (buildgen.twin_wiring's own vocabulary
# - matches devices/*.toml's `driver = "..."` values, e.g. "scd30") rather than each driver's own
# REST/error-log `_NAME` constant. Real per-driver facts, true for every device that happens to
# carry that driver - not per-device facts - so these tables stay fixed; what varies per device is
# only *which* of these drivers are actually present, derived from that device's own wiring plan
# (RunContext.drivers) rather than hardcoded here.
_BUS_FAULT_OPS = {  # the real bus-level call each driver's own bus access goes through - confirmed
    # directly against each driver's own read/write call sites, not guessed from the chip's API.
    "scd30": "writeto",
    "sgp40": "writeto",
    "bmp3xx": "readfrom_mem",
    "fram": "write",
}
_BUS_FAULT_ERROR_COUNT = 500  # sustained/high-repeat-count - see Run 3's own comment for why.
# Driver -> its own REST/error-log `_NAME` constant - confirmed directly against
# src/asy_scd30_driver.py/asy_sgp40_driver.py/asy_bmp3xx_driver.py/asy_fram_manager.py: all four
# happen to equal `driver.upper()`, but this is NOT a general rule (CLAUDE.md/BUILD_CHAIN_PLAN.md
# both warn against assuming that - e.g. NotificationCoordinator's own _NAME is "NOTIFY", not
# "NOTIFICATION") - this table is the verified, narrow exception for exactly these four bus-attached,
# fault-injectable drivers, not instance_name()/`_NAME` resolution reused generically.
_DRIVER_ERRCOUNT_NAME = {"scd30": "SCD30", "sgp40": "SGP40", "bmp3xx": "BMP3XX", "fram": "FRAM"}
# Which bus-attached drivers produce a real /measurements reading (Run 4's "came back after being
# faulted" check) vs which keep their error log FRAM-persisted (survives a reboot by design,
# SPECIFICATION.md Part A.7) rather than in-memory-only (must reset to 0 across a reboot, Run 4's
# other check) - both are real per-driver facts, not per-device ones.
_MEASUREMENT_DRIVERS = frozenset({"scd30", "sgp40", "bmp3xx"})
_IN_MEMORY_ERROR_DRIVERS = frozenset({"scd30", "bmp3xx", "fram"})
_PERSISTED_ERROR_MODULES = ("SGP40",)  # only fault-injectable module whose error log survives a
# reboot; used by Run 5b/5c. WIFI is also in-memory-only (SPECIFICATION.md Part A.7) but isn't
# bus-fault-injectable (no chip fake of its own) - checked separately (Run 8), not via ctx.drivers.

# The one HTTP status every endpoint in this suite is expected to answer with - a non-200 anywhere
# is a suite failure, never an alternative success path.
_HTTP_OK = 200

# The settings run 1 PUTs and every later run reads back unchanged (the persistence checks), the
# thresholds the log/error-count assertions compare against, and the scripted fault counts handed
# to run_generic_integration.py's own --fault/--wifi-outcome flags. Named here so the value a run
# INJECTS and the value its assertion EXPECTS can never drift apart.
_TEST_DEBUG_LEVEL = 5
_TEST_WARN_CO2 = 1800
_TEST_SCD30_MEAS_INT = 4
_MIN_VERBOSE_LOG_LINES = 5
_SGP40_BOUNDED_FAULT_COUNT = 3
_WIFI_SCRIPTED_FAILURES = 5  # asy_wifi_service.py's conn_fail_to_hotspot - the failure count that trips hotspot fallback

# A fixed, recognizable DNS transaction ID, so a real answer from the captive DNSServer can be told
# apart from an echo of the query itself; the header prefix is _try_dns_query()'s own ">HH" unpack.
_DNS_QUERY_ID = 0x1234
_DNS_RESPONSE_HEADER_LEN = 4

_FAILURES: list[str] = []


@dataclass(frozen=True)
class RunContext:
    """Everything a single device's run of this suite needs, computed once in main() - which real
    MicroPython Unix-port binary to launch, which generated module/wiring-plan pair to boot it
    against, and which bus-attached drivers that device's own wiring plan actually declares (so the
    bus-fault matrix below never has to hardcode "wozi/dev have bmp3xx, the other four don't")."""

    micropython_bin: str
    logs_dir: Path
    device: str
    module: str
    wiring_plan_path: Path
    drivers: frozenset[str]


def _fail(msg: str) -> None:
    _FAILURES.append(msg)
    print(f"FAIL: {msg}", file=sys.stderr)


def _check(*, condition: bool, msg: str) -> None:
    if not condition:
        _fail(msg)
    else:
        print(f"OK: {msg}")


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


def _error_type_count(entry: dict[str, Any]) -> int:
    # entry["counter"] (PrintLogHistory's own ErrCount) increments on both errors ("E") AND
    # warnings ("W") pushed into the same history - a driver's own "recovered after N failures"
    # notice is itself a "W" entry (see e.g. src/asy_sgp40_driver.py's own read-loop recovery path),
    # so a real recovery can bump "counter" without any NEW failure. Counting "E"-typed history
    # entries specifically is the actual "did more real errors happen" signal this suite needs.
    history = entry.get("history", [])
    return sum(1 for item in history if isinstance(item, dict) and item.get("type") == "E")


def _errcount(name: str) -> dict[str, Any]:
    status, body = _http("GET", "/status")
    if status != _HTTP_OK or not isinstance(body, dict):
        return {}
    entry = body.get("errcount", {}).get(name, {})
    return entry if isinstance(entry, dict) else {}


def _mem_paused() -> bool | None:
    # system_service.py's own permanent-storage pause, as GET /status reports it. None means the
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
        time.sleep(0.5)
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
        time.sleep(1.0)
    return entry


def _wait_for_error_type_count(name: str, target: int, timeout_s: float) -> dict[str, Any]:
    # Same "poll, never guess a sleep" reasoning as _wait_for_errcount_above(), but keyed on the
    # "E"-typed count _error_type_count() extracts rather than the raw counter (which a "W" recovery
    # notice also bumps). A fixed sleep here encodes a host-speed assumption: on this project's own
    # bench Pi4 a bounded 3-fault SGP40 run needs ~8s to record all three and settle, where an x86
    # CI runner needs ~2s, so a 6s sleep passes there and samples mid-sequence here.
    deadline = time.monotonic() + timeout_s
    entry: dict[str, Any] = {}
    while time.monotonic() < deadline:
        entry = _errcount(name)
        if _error_type_count(entry) >= target:
            return entry
        time.sleep(1.0)
    return entry


def _wait_until_serving(proc: subprocess.Popen[str], timeout_s: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"digital twin subprocess exited early with code {proc.returncode} before ever serving")
        try:
            status, _ = _http("GET", "/", timeout=1.0)
            if status == _HTTP_OK:
                return
        except OSError:
            pass
        time.sleep(0.25)
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
        # run_generic_integration.py's own RunConfig defaults these to None (in-memory only) -
        # unlike run_wozi_integration.py's/run_dev_integration.py's own hardcoded defaults, so this
        # suite's persistence-across-a-real-reboot checks (Run 2, Run 4, Run 5b/5c) need them
        # supplied explicitly, pointed at the same fixed paths _clean_state() wipes.
        "--fram-state-path", str(FRAM_STATE_PATH),
        "--scd30-state-path", str(SCD30_STATE_PATH),
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


def _shutdown(proc: subprocess.Popen[str], timeout_s: float = 15.0) -> int:
    # SIGINT, not SIGTERM/terminate(): run_generic_integration.py's own graceful-shutdown path
    # (FRAM/SCD30 flush) only runs on KeyboardInterrupt (see that module's own __main__ block
    # comment) - a real SIGTERM would skip it entirely and lose this run's persisted state.
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5.0)
    log_file = getattr(proc, "ci_log_file", None)
    if log_file is not None:
        log_file.close()
    return proc.returncode if proc.returncode is not None else -1


def _wait_exit(proc: subprocess.Popen[str], timeout_s: float) -> int:
    # For bounded (--duration N) runs that exit on their own - no signal needed or wanted.
    try:
        ec = proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5.0)
        ec = -1
    log_file = getattr(proc, "ci_log_file", None)
    if log_file is not None:
        log_file.close()
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


def _wait_for_dns_answer(host: str, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _try_dns_query(host):
            return True
        time.sleep(0.5)
    return False


def _bus_fault_drivers(ctx: RunContext) -> list[str]:
    # Sorted, deterministic subset of ctx.drivers this suite actually knows how to fault/check -
    # every real device's own bus-attached driver set (scd30/sgp40/fram always; bmp3xx only on
    # wozi/dev) is covered by _BUS_FAULT_OPS today, so this is currently a no-op filter, but stays
    # a filter (not a bare ctx.drivers sort) so a future bus-attached driver this suite hasn't been
    # taught to fault yet is silently skipped here rather than KeyError-ing in Run 3/4.
    return sorted(d for d in ctx.drivers if d in _BUS_FAULT_OPS)


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

        status, body = _http("PUT", "/sensors", {"SCD30": {"MeasInt": _TEST_SCD30_MEAS_INT}})
        _check(condition=status == _HTTP_OK and body.get("result", {}).get("SCD30", {}).get("MeasInt") in ("Valid", "Unchanged"), msg=f"Run 1: PUT /sensors SCD30.MeasInt={_TEST_SCD30_MEAS_INT} accepted")

        status, body = _http("PUT", "/networking", {"Hostname": "ci-digital-twin"})
        _check(condition=status == _HTTP_OK and body.get("result", {}).get("Hostname") in ("Valid", "Unchanged"), msg="Run 1: PUT /networking Hostname accepted")

        status, body = _http("PUT", "/status", {"ResetErrors": True})
        _check(condition=status == _HTTP_OK, msg="Run 1: PUT /status ResetErrors accepted")
    except Exception as exc:  # CI orchestration: surface any failure as a suite failure, not a crash
        _fail(f"Run 1 (baseline boot + settings): {exc!r}")
    finally:
        ec = _shutdown(proc)
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
        _check(condition=status == _HTTP_OK and body.get("SCD30", {}).get("MeasInt") == _TEST_SCD30_MEAS_INT, msg="Run 2: SCD30 MeasInt survived a real process restart")
        status, body = _http("GET", "/networking")
        _check(condition=status == _HTTP_OK and body.get("Hostname") == "ci-digital-twin", msg="Run 2: Hostname survived a real process restart")
        time.sleep(3.0)  # let a bootup/sensor-read cycle actually happen under the now-persisted DebugLevel=5
    except Exception as exc:
        _fail(f"Run 2 (reboot + settings persistence): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(condition=ec == 0, msg=f"Run 2: clean shutdown (exit code {ec})")
    verbose_lines = _count_verbose_log_lines(_read_log(log2))
    _check(condition=verbose_lines >= _MIN_VERBOSE_LOG_LINES, msg=f"Run 2: bootup produced verbose (DebugLevel={_TEST_DEBUG_LEVEL}) log output from multiple modules ({verbose_lines} matching lines)")


def _run_3_sustained_bus_fault_matrix(ctx: RunContext) -> None:
    # ---- Run 3: reboot with a sustained/high-repeat-count ("permanent") bus-fault matrix across
    # every bus-level error-counted module this DEVICE actually has (derived from ctx.drivers, never
    # a hardcoded list - a device without bmp3xx simply never faults/checks it here) at once -
    # proves the system keeps logging/counting every failure AND the watchdog never starves under
    # sustained failure (bounded, immediately-raised errors, not an indefinite hang - see this
    # file's own module docstring and digital_twin/_fault_injection.py's for why that distinction
    # matters here). ----
    log3 = ctx.logs_dir / "run3_sustained_bus_fault_matrix.log"
    fault_drivers = _bus_fault_drivers(ctx)
    fault_args: list[str] = []
    for driver in fault_drivers:
        fault_args += ["--fault", f"{driver}:{_BUS_FAULT_OPS[driver]}:{_BUS_FAULT_ERROR_COUNT}"]
    proc = _spawn(ctx, fault_args, log3)
    try:
        _wait_until_serving(proc)
        # Wait for every faulted module to have recorded a real error, rather than sleeping a
        # guessed interval and hoping: "the fault has actually been exercised" is a real event to
        # wait for, and a fixed sleep here encodes the same host-speed assumption that made the old
        # Run 4 check flaky (an x86 CI runner gets through several read cycles in the time this
        # bench Pi4 manages one). Keyed on "E"-typed entries, never the raw counter - a "W" recovery
        # notice bumps that too, so `counter > 0` could be satisfied without the fault ever landing.
        errcount_names = [_DRIVER_ERRCOUNT_NAME[d] for d in fault_drivers]
        faulted = {name: _wait_for_error_type_count(name, 1, timeout_s=45.0) for name in errcount_names}
        for path in ("/measurements", "/sensors", "/status"):
            status, _ = _http("GET", path)
            _check(condition=status == _HTTP_OK, msg=f"Run 3: GET {path} still returns 200 under a sustained bus-fault matrix (graceful degradation)")
        for name, entry in faulted.items():
            _check(condition=_error_type_count(entry) > 0, msg=f"Run 3: {name}'s injected sustained fault was recorded as a real error, not just a warning ({entry!r})")
    except Exception as exc:
        _fail(f"Run 3 (sustained bus-fault matrix): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(condition=ec == 0, msg=f"Run 3: process survived the sustained bus-fault matrix without crashing (exit code {ec})")
    wdt3 = _would_have_triggered_count(_read_log(log3))
    _check(condition=wdt3 == 0, msg=f"Run 3: watchdog never starved under sustained-but-bounded bus errors (would_have_triggered_count={wdt3!r})")


def _run_4_bus_fault_persistence_sweep(ctx: RunContext) -> None:
    # ---- Run 4: reboot fault-free after Run 3's matrix - what must reset, and that every faulted
    # bus actually comes back. Whichever of SCD30/BMP3XX/FRAM this device actually has are
    # in-memory-only by design and must read back 0 (SPECIFICATION.md Part A.7); that direction is
    # deterministic and is what this run proves. ----
    #
    # This run deliberately does NOT assert that SGP40's FRAM-backed history survived Run 3 - it
    # cannot. Run 3's own matrix faults `fram:write` (when this device has a fram instance, which
    # every real device does), so the chip is unwritable for that whole run and nothing SGP40 logs
    # there can ever reach it. The check that used to stand here (`counter > 0`) was unsound twice
    # over: `counter` counts "W" as well as "E", so it was only ever satisfied by a FRESH warning
    # from this run's own boot rather than by anything persisted, and waiting on that warning is a
    # host-speed race (it lands before the sample on an x86 CI runner, after it on the bench Pi4 -
    # measured). Losing FRAM-backed history when the FRAM itself was unavailable is accepted
    # behavior, not a defect (project owner's call, 2026-09-11): no recovery scheme is wanted for a
    # reboot that catches the chip mid-operation. The real persistence claim is proven in Run 5b
    # instead, where the chip is healthy and the outcome is deterministic on any host.
    log4 = ctx.logs_dir / "run4_bus_fault_persistence_sweep.log"
    proc = _spawn(ctx, [], log4)
    try:
        _wait_until_serving(proc)
        fault_drivers = _bus_fault_drivers(ctx)
        for driver in fault_drivers:
            if driver not in _IN_MEMORY_ERROR_DRIVERS:
                continue  # WIFI's own reset check is Run 8, after its own fault run (Run 7)
            name = _DRIVER_ERRCOUNT_NAME[driver]
            entry = _errcount(name)
            _check(condition=entry.get("counter", 0) == 0, msg=f"Run 4: {name}'s error count correctly did NOT persist across reboot (in-memory-only by design) ({entry!r})")
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
        ec = _shutdown(proc)
        _check(condition=ec == 0, msg=f"Run 4: clean shutdown (exit code {ec})")


def _run_5_recovery_after_bounded_fault(ctx: RunContext) -> None:
    # ---- Run 5: clean boot, a small BOUNDED fault (not sustained) - proves recovery, the other
    # half of the self-healing story Run 3 alone can't show (it only proves "doesn't crash while
    # still broken", not "comes back once the fault clears"). SGP40 is present on every real device
    # (BUILD_CHAIN_PLAN.md's Session 2), so this run needs no device-conditional logic at all. ----
    _clean_state()
    log5 = ctx.logs_dir / "run5_recovery_after_bounded_fault.log"
    proc = _spawn(ctx, ["--fault", f"sgp40:writeto:{_SGP40_BOUNDED_FAULT_COUNT}"], log5)
    try:
        _wait_until_serving(proc)
        # Poll rather than sleep a guessed interval: the fault is exhausted when the third "E"
        # lands, which is a real event to wait for, not a wall-clock duration to assume.
        entry = _wait_for_error_type_count("SGP40", _SGP40_BOUNDED_FAULT_COUNT, timeout_s=30.0)
        errors_after_exhaustion = _error_type_count(entry)
        _check(condition=errors_after_exhaustion == _SGP40_BOUNDED_FAULT_COUNT, msg=f"Run 5: SGP40's bounded fault ({_SGP40_BOUNDED_FAULT_COUNT} failures) was fully recorded, no more ({entry!r})")
        time.sleep(3.0)  # a few more cycles past exhaustion - real ("E") errors should NOT keep climbing
        # (a "W" recovery notice may legitimately appear here - see _error_type_count()'s own comment)
        entry2 = _errcount("SGP40")
        _check(condition=_error_type_count(entry2) == errors_after_exhaustion, msg=f"Run 5: SGP40's real error count stopped climbing once the fault cleared (recovery) ({entry2!r})")
        status, body = _http("GET", "/measurements")
        sgp40_reading = body.get("SGP40", {}) if status == _HTTP_OK and isinstance(body, dict) else {}
        _check(condition=status == _HTTP_OK and bool(sgp40_reading), msg=f"Run 5: SGP40 measurements resumed after recovery ({sgp40_reading!r})")
    except Exception as exc:
        _fail(f"Run 5 (recovery after a bounded fault): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(condition=ec == 0, msg=f"Run 5: clean shutdown (exit code {ec})")


def _run_5b_error_log_restore_is_all_or_nothing(ctx: RunContext) -> None:
    # ---- Run 5b: reboot straight onto Run 5's state, fault-free. Run 5 left exactly
    # _SGP40_BOUNDED_FAULT_COUNT "E" entries on a HEALTHY chip, write-through (print_log.py's
    # _store_err() writes on every push - no deferred flush to race), so they SHOULD come back. But
    # Run 5 shut down abruptly, and an abrupt shutdown can catch a chunk write in flight: both
    # status bytes are set to _STATUS_BUSY before the payload is touched, so an interrupted write
    # leaves them there, PrintLogHistoryStore.setup()'s _read() then fails, and its _write() fallback
    # stores the empty ring. Measured here at roughly 1 abrupt restart in 8.
    #
    # That loss is accepted behavior, not a defect (project owner's call, 2026-09-11): no recovery
    # scheme is wanted for a reboot that catches the chip mid-operation. So this run asserts the
    # invariant that does hold unconditionally - the restore is ALL-OR-NOTHING, never partial and
    # never garbled, which is the dual-block + CRC + busy-flag protocol's actual job. Run 5c below
    # covers the case that must never lose anything. Mirrored at the mock tier
    # (tests/test_fram_integration.py) and on real silicon (tests_hardware/flash/test_fram_storage.py).
    #
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
            entry = _wait_for_error_type_count(name, _SGP40_BOUNDED_FAULT_COUNT, timeout_s=30.0)
            restored = _error_type_count(entry)
            _check(condition=restored in (0, _SGP40_BOUNDED_FAULT_COUNT), msg=f"Run 5b: {name}'s FRAM-backed history came back all-or-nothing after an abrupt restart - never a partial {restored}-entry remnant ({entry!r})")
            if restored:
                _check(condition=entry.get("counter", 0) >= restored, msg=f"Run 5b: {name}'s restored error COUNT is consistent with the {restored} restored entries, not left behind ({entry!r})")
    except Exception as exc:
        _fail(f"Run 5b (error-log restore is all-or-nothing): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(condition=ec == 0, msg=f"Run 5b: clean shutdown (exit code {ec})")


def _run_5c_storage_paused_shutdown_never_loses_the_error_log(ctx: RunContext) -> None:
    # ---- Run 5c: the case that must NEVER lose anything - a commanded reboot. Production's own
    # system_service._reboot() pauses permanent storage before it resets, precisely so no FRAM chunk
    # operation can be in flight across the restart; `PUT /system {"SystemCmd": "mempause"}` is that
    # same pause, reachable over REST. With it held, none of _write()/_read()/clear() can start, so
    # no status byte can be left at _STATUS_BUSY and the restore is deterministic - measured 20/20
    # here against roughly 1-in-8 loss for the unpaused abrupt shutdown Run 5b covers.
    #
    # This is what makes the pair sound: Run 5b alone would pass even if persistence never worked at
    # all (an empty ring satisfies all-or-nothing), which is exactly the hole the old Run 4 check had. ----
    _clean_state()
    log5c_a = ctx.logs_dir / "run5c_a_record_then_pause_storage.log"
    proc = _spawn(ctx, ["--fault", f"sgp40:writeto:{_SGP40_BOUNDED_FAULT_COUNT}"], log5c_a)
    try:
        _wait_until_serving(proc)
        entry = _wait_for_error_type_count("SGP40", _SGP40_BOUNDED_FAULT_COUNT, timeout_s=30.0)
        _check(condition=_error_type_count(entry) == _SGP40_BOUNDED_FAULT_COUNT, msg=f"Run 5c: SGP40 recorded all {_SGP40_BOUNDED_FAULT_COUNT} bounded failures before the commanded reboot ({entry!r})")
        status, _ = _http("PUT", "/system", {"SystemCmd": "mempause"})
        _check(condition=status == _HTTP_OK, msg=f"Run 5c: PUT /system mempause accepted (status {status})")
        paused = _wait_for_mem_paused(expected=True, timeout_s=15.0)
        _check(condition=paused, msg="Run 5c: storage actually reported paused before the shutdown, not just a 200")
        time.sleep(2.0)  # let anything already in flight finish - nothing new can start while paused
    except Exception as exc:
        _fail(f"Run 5c (record then pause storage): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(condition=ec == 0, msg=f"Run 5c: clean shutdown after the storage pause (exit code {ec})")

    log5c_b = ctx.logs_dir / "run5c_b_history_survived_the_commanded_reboot.log"
    proc = _spawn(ctx, [], log5c_b)
    try:
        _wait_until_serving(proc)
        entry = _wait_for_error_type_count("SGP40", _SGP40_BOUNDED_FAULT_COUNT, timeout_s=30.0)
        restored = _error_type_count(entry)
        _check(condition=restored == _SGP40_BOUNDED_FAULT_COUNT, msg=f"Run 5c: SGP40's {_SGP40_BOUNDED_FAULT_COUNT} errors survived a reboot taken with storage paused - the one case that must never lose them ({restored} found, {entry!r})")
        _check(condition=entry.get("counter", 0) >= _SGP40_BOUNDED_FAULT_COUNT, msg=f"Run 5c: SGP40's persisted error COUNT was restored too, not just the history ring ({entry!r})")
        _check(condition=_mem_paused() is False, msg="Run 5c: the storage pause did NOT survive the reboot (it is RAM-only by design)")
        # The restored history must not be a read-only relic: a ResetErrors PUT has to clear it on
        # the chip. Deliberately issued after the poll above confirmed setup() ran, so this checks
        # the ordinary case; a reset issued *before* setup() is covered separately (Part C.7
        # - it persists straight away now and the later setup() must not undo it).
        status, _ = _http("PUT", "/status", {"ResetErrors": True})
        _check(condition=status == _HTTP_OK, msg=f"Run 5c: PUT /status ResetErrors accepted (status {status})")
        entry = _errcount("SGP40")
        _check(condition=_error_type_count(entry) == 0, msg=f"Run 5c: the restored history was actually cleared by ResetErrors, not just masked ({entry!r})")
    except Exception as exc:
        _fail(f"Run 5c (history survived the commanded reboot): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(condition=ec == 0, msg=f"Run 5c: clean shutdown (exit code {ec})")


def _run_6_configure_ssid(ctx: RunContext) -> None:
    # ---- Run 6: clean boot, configure a real SSID (persisted) for Run 7's WiFi test below - a
    # real configured SSID, not the "SSID==''" unconfigured shortcut, is needed for a genuine
    # STA-connect-failure cycle (matches tests/test_digital_twin_sensortask_integration.py's own
    # in-process precedent for this same distinction). ----
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
        ec = _shutdown(proc)
        _check(condition=ec == 0, msg=f"Run 6: clean shutdown (exit code {ec})")


def _run_7_wifi_hotspot_dns(ctx: RunContext) -> None:
    # ---- Run 7: reboot with scripted repeated STA-connect failures ("no access point found") -
    # real-world WiFi fault. Drives the real STA -> hotspot fallback state machine
    # (conn_fail_to_hotspot=5 real scripted failures), starts the real DNSServer, and confirms it
    # actually answers a real UDP DNS query - not just that the internal state flipped. WiFi/NTP/
    # SystemService are mandatory infrastructure on every real device (never a [[instance]] entry,
    # BUILD_CHAIN_PLAN.md's device TOML schema), so this run needs no device-conditional logic.
    #
    # Only possible because of digital_twin/_unix_port_udp_addr_shim.py: BACKLOG.md's "Real-hardware
    # verification gap for asy_udp_socket.py/captive_dns.py" entry root-caused three separate
    # Unix-port-only socket quirks (a plain (host, port) tuple rejected by bind()/connect()/sendto(),
    # and recvfrom() returning a raw sockaddr struct instead of the (str, int) shape production code
    # expects) that made a real UDP round trip impossible under this harness before that shim existed
    # - all three correct, required behavior for real rp2 hardware, so src/ itself stays untouched;
    # the shim works around them entirely from twin-side code, applied by
    # run_generic_integration.py's own main() before anything constructs a socket. ----
    log7 = ctx.logs_dir / "run7_wifi_hotspot_dns.log"
    proc = _spawn(
        ctx,
        ["--wifi-outcome", "no_ap"] * _WIFI_SCRIPTED_FAILURES,
        log7,
    )
    try:
        _wait_until_serving(proc)
        # Waits for the FULL scripted failure count (conn_fail_to_hotspot=5), not just > 0 (the
        # very first failure) - hotspot activation, and therefore the DNSServer, doesn't start
        # until the 5th one. Waiting for all 5 here first, then giving the DNS check its own
        # separate budget, is more robust than one long guessed timeout covering both phases -
        # a real CI runner observed needing well over the first attempt's combined budget.
        entry = _wait_for_errcount_above("WIFI", _WIFI_SCRIPTED_FAILURES - 1, timeout_s=90.0)
        _check(condition=entry.get("counter", 0) >= _WIFI_SCRIPTED_FAILURES, msg=f"Run 7: all {_WIFI_SCRIPTED_FAILURES} repeated WiFi connect failures drove real hotspot fallback and were recorded in WIFI's error counter ({entry!r})")
        # 30s originally timed out twice in a row on real GitHub Actions runners even after the
        # errcount-wait fix above landed and was confirmed working - turned out to be a red herring:
        # the real cause was scripts/run_digital_twin_ci.sh's interpreter binary lacking
        # CAP_NET_BIND_SERVICE, so DNSServer's bind() to privileged port 53 was silently failing and
        # no timeout length would ever have fixed it (see digital_twin/README.md's "Automated CI
        # suite" run 7 entry for the full account). Left at 90s with a 0.5s retry cadence (see
        # _wait_for_dns_answer) anyway, now that the real fix is in - this is a hotspot-fallback
        # path, not a hot one, so the extra slack costs nothing when the answer arrives early.
        answered = _wait_for_dns_answer(HOST, timeout_s=90.0)
        _check(condition=answered, msg="Run 7: the real captive DNSServer answered a real UDP DNS query after WiFi hotspot fallback")
        status, _ = _http("GET", "/status")
        _check(condition=status == _HTTP_OK, msg="Run 7: webserver stayed reachable throughout the WiFi hotspot-fallback transition")
    except Exception as exc:
        _fail(f"Run 7 (WiFi hotspot fallback + DNS): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(condition=ec == 0, msg=f"Run 7: process survived the WiFi hotspot-fallback transition without crashing (exit code {ec})")


def _run_8_wifi_persistence_and_configure_ntp(ctx: RunContext) -> None:
    # ---- Run 8: reboot fault-free - WIFI's own persistence-correctness check (in-memory-only,
    # should reset to 0), plus configure an unreachable NTP host (persisted) for Run 9. ----
    log8 = ctx.logs_dir / "run8_wifi_persistence_and_configure_ntp.log"
    proc = _spawn(ctx, [], log8)
    try:
        _wait_until_serving(proc)
        entry = _errcount("WIFI")
        _check(condition=entry.get("counter", 0) == 0, msg=f"Run 8: WIFI's error count correctly did NOT persist across reboot (in-memory-only by design) ({entry!r})")
        # 192.0.2.1: RFC 5737 TEST-NET-1, guaranteed non-routable - a deliberate, reproducible
        # "unreachable" address rather than relying on incidental CI sandbox network policy.
        status, body = _http("PUT", "/networking", {"NTP_Host": "192.0.2.1"})
        _check(condition=status == _HTTP_OK and body.get("result", {}).get("NTP_Host") in ("Valid", "Unchanged"), msg="Run 8: PUT /networking NTP_Host (unreachable) accepted")
    except Exception as exc:
        _fail(f"Run 8 (WIFI persistence check + configure unreachable NTP): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(condition=ec == 0, msg=f"Run 8: clean shutdown (exit code {ec})")


def _run_9_ntp_unreachable(ctx: RunContext) -> None:
    # ---- Run 9: reboot with NTP permanently unreachable - the other "network connections" real-
    # world case. The system must stay fully healthy (webserver reachable) despite NTP never
    # succeeding, not just eventually. ----
    log9 = ctx.logs_dir / "run9_ntp_unreachable.log"
    proc = _spawn(ctx, [], log9)
    try:
        _wait_until_serving(proc)
        time.sleep(7.0)  # past _NTP_FETCH_TIMEOUT_MS=5000 (every generated sensortask_<device>
        # module shares this constant, mandatory infra - system_service.py) - NTP should have
        # given up by now
        status, _ = _http("GET", "/system")
        _check(condition=status == _HTTP_OK, msg="Run 9: webserver stayed fully healthy with NTP permanently unreachable")
    except Exception as exc:
        _fail(f"Run 9 (NTP unreachable): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(condition=ec == 0, msg=f"Run 9: clean shutdown (exit code {ec})")


def _run_10_watchdog_hang_backstop(ctx: RunContext) -> None:
    # ---- Run 10: the dedicated hang case - a real, blocking (not asyncio) time.sleep() inside a
    # chip fake's handler, genuinely freezing the whole interpreter past the 8000ms WDT window, to
    # prove the (simulated) watchdog backstop itself actually engages - the one thing sustained-but-
    # bounded errors (Run 3) cannot demonstrate. See digital_twin/_fault_injection.py's own module
    # docstring for why this - and only this - is what real hardware's "genuinely wedged bus"
    # scenario requires (SPECIFICATION.md Part F.2, CLAUDE.md's own settled "hardware watchdog is
    # the accepted backstop" rule). --duration 15, not 0: since BMP3xx/SCD30 gained FRAM-backed
    # error logging, SGP40's own first bus access queues behind theirs on the shared FRAM SPI bus,
    # so the hang can fire well after webserver readiness - --duration 0 raced that and sometimes
    # exited before the hang ever fired at all. See digital_twin/README.md's "WDT._arm()'s
    # late-feed backstop" for the full account (this and that fix were found together). SGP40 is
    # present on every real device, so this run needs no device-conditional logic. ----
    _clean_state()
    log10 = ctx.logs_dir / "run10_watchdog_hang_backstop.log"
    proc = _spawn(ctx, ["--hang", "sgp40:writeto:12", "--duration", "15"], log10)
    try:
        ec = _wait_exit(proc, timeout_s=45.0)
        _check(condition=ec == 0, msg=f"Run 10: process survived a genuinely wedged bus and exited cleanly (exit code {ec})")
    except Exception as exc:
        _fail(f"Run 10 (watchdog hang backstop): {exc!r}")
        _wait_exit(proc, timeout_s=5.0)
    wdt10 = _would_have_triggered_count(_read_log(log10))
    _check(condition=wdt10 is not None and wdt10 >= 1, msg=f"Run 10: the watchdog backstop actually engaged for a genuinely wedged bus (would_have_triggered_count={wdt10!r})")


def _run_11_soak(ctx: RunContext) -> None:
    # ---- Run 11: a genuinely fresh, clean boot dedicated to the soak check. --soak/--soak-cycles
    # (BUILD_CHAIN_PLAN.md's Session 6.2) is now supported directly by run_generic_integration.py,
    # ported verbatim from run_wozi_integration.py's/run_dev_integration.py's own machinery. ----
    _clean_state()
    log11 = ctx.logs_dir / "run11_soak.log"
    proc = _spawn(ctx, ["--soak", "--soak-cycles", "20", "--duration", "0"], log11)
    try:
        ec = proc.wait(timeout=180.0)
        _check(condition=ec == 0, msg=f"Run 11: soak run completed cleanly (exit code {ec})")
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5.0)
        _fail("Run 11: soak run exceeded its 180s bound and was killed")
    finally:
        log_file = getattr(proc, "ci_log_file", None)
        if log_file is not None:
            log_file.close()
    log11_text = _read_log(log11)
    _check(condition="soak summary" in log11_text, msg="Run 11: soak summary was printed")
    _check(condition="PASS -" in log11_text, msg="Run 11: soak run reported PASS (no HTTP failures, watchdog never starved, memory trend within tolerance)")


def run_suite(ctx: RunContext) -> int:
    ctx.logs_dir.mkdir(parents=True, exist_ok=True)

    _run_1_baseline(ctx)
    _run_2_reboot_settings_persistence(ctx)
    _run_3_sustained_bus_fault_matrix(ctx)
    _run_4_bus_fault_persistence_sweep(ctx)
    _run_5_recovery_after_bounded_fault(ctx)
    _run_5b_error_log_restore_is_all_or_nothing(ctx)
    _run_5c_storage_paused_shutdown_never_loses_the_error_log(ctx)
    _run_6_configure_ssid(ctx)
    _run_7_wifi_hotspot_dns(ctx)
    _run_8_wifi_persistence_and_configure_ntp(ctx)
    _run_9_ntp_unreachable(ctx)
    _run_10_watchdog_hang_backstop(ctx)
    _run_11_soak(ctx)

    print()
    if _FAILURES:
        print(f"== digital-twin CI suite FAILED ({ctx.device}): {len(_FAILURES)} check(s) failed")
        for msg in _FAILURES:
            print(f"  - {msg}")
        return 1
    print(f"== digital-twin CI suite PASSED ({ctx.device}): every check succeeded")
    return 0


def _drivers_in_plan(plan: dict[str, Any]) -> frozenset[str]:
    # The set of bus-attached `driver` identities (buildgen.twin_wiring's own vocabulary) this
    # device's own wiring plan actually declares - e.g. {"scd30", "sgp40", "fram"} for a device
    # without bmp3xx, {"scd30", "sgp40", "bmp3xx", "fram"} for wozi/dev. Neopixel/notification never
    # appear here (GPIO-pin-only, not bus-attached - buildgen.twin_wiring.compute_twin_wiring()'s
    # own scope), which is fine: this suite's bus-fault matrix only ever targets bus-attached drivers.
    names: set[str] = set()
    for attachments in plan["buses"].values():
        for attachment in attachments:
            names.add(attachment["driver"])
    for attachment in plan["spi"].values():
        names.add(attachment["driver"])
    return frozenset(names)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--micropython-bin", required=True, help="path to the built MicroPython Unix-port binary")
    parser.add_argument("--device", default="wozi", help="which devices/<device>.toml-generated module to drive this suite against (default: wozi)")
    parser.add_argument("--logs-dir", default=str(REPO_ROOT / "digital_twin_ci_logs"), help="directory to write per-run subprocess logs into")
    args = parser.parse_args()

    module = f"sensortask_{args.device}"
    wiring_plan_path = GENERATED_SRC_DIR / f"{module}_wiring_plan.json"
    if not wiring_plan_path.exists():
        print(
            f"error: {wiring_plan_path} not found - run scripts/_generate_sensortask_modules.py "
            f"first (scripts/run_digital_twin_ci.sh already does this)",
            file=sys.stderr,
        )
        return 1
    plan = json.loads(wiring_plan_path.read_text())

    ctx = RunContext(
        micropython_bin=args.micropython_bin,
        logs_dir=Path(args.logs_dir),
        device=args.device,
        module=module,
        wiring_plan_path=wiring_plan_path,
        drivers=_drivers_in_plan(plan),
    )

    _clean_state()
    return run_suite(ctx)


if __name__ == "__main__":
    sys.exit(main())
