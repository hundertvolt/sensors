#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Automated version of the manual digital-twin on-demand walkthrough (the project owner's own
baseline/DebugLevel/PUT-persistence/fault-injection/soak passes, formerly run by hand only) -
drives `digital_twin/run_wozi_integration.py` as a real subprocess, over real HTTP, through a
sequence of real process restarts, and asserts every step. CPython/stdlib-only (no `uv sync`
needed) since it only orchestrates the MicroPython subprocess and speaks plain HTTP to it - the
code under test still only ever runs under the real MicroPython Unix-port interpreter.

Invoked by `scripts/run_digital_twin_ci.sh` (which owns the "clean" + "build" phases); this script
is the "test" phase. See `digital_twin/README.md`'s "Automated CI suite" section for the full
walkthrough this reproduces and why each phase exists.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "digital_twin"
FRAM_STATE_PATH = STATE_DIR / "fram_state.json"
SCD30_STATE_PATH = STATE_DIR / "scd30_state.json"
CONFIG_DIR = STATE_DIR / "config"
MICROPYPATH = "src:digital_twin:ext:frozen_modules:.frozen"
HOST = "127.0.0.1"
PORT = 18080  # a fixed, non-privileged, non-8080-default port - avoids colliding with a real
# manual `scripts/run_unix_port_integration.sh` run on the same machine.

# print_log.py's own per-module PrintLog `name=` values (src/*.py's `_NAME` constants) - a verbose
# (DebugLevel=5) log line is `print(name, *args)`, so a line *starting* with one of these plus a
# space is real per-module log output, not run_wozi_integration.py's own unconditional banner
# prints. Checked as a set (not all of them - some, like DNSSRV/NEOPIXEL, aren't guaranteed to log
# anything during this suite's short runs) to confirm verbose logging is genuinely flowing, not to
# pin every module's exact output.
_VERBOSE_LOG_PREFIXES = ("SYSTEM", "SGP40", "SCD30", "BMP3XX", "WEBSERVER", "NOTIFY", "WIFI", "NTP", "FRAM")

_FAILURES: list[str] = []


def _fail(msg: str) -> None:
    _FAILURES.append(msg)
    print(f"FAIL: {msg}", file=sys.stderr)


def _check(condition: bool, msg: str) -> None:
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


def _http(method: str, path: str, body: dict | None = None, timeout: float = 5.0) -> tuple[int, Any]:
    # "/" serves the static frozen_html stub (gzip bytes, not JSON - see asy_webserver_service.py's
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


def _wait_until_serving(proc: subprocess.Popen[str], timeout_s: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"digital twin subprocess exited early with code {proc.returncode} before ever serving")
        try:
            status, _ = _http("GET", "/", timeout=1.0)
            if status == 200:
                return
        except OSError:
            pass
        time.sleep(0.25)
    raise TimeoutError(f"digital twin never started serving on {HOST}:{PORT} within {timeout_s}s")


def _spawn(micropython_bin: str, extra_args: list[str], log_path: Path) -> subprocess.Popen[str]:
    env = dict(os.environ)
    env["MICROPYPATH"] = MICROPYPATH
    env["TZ"] = "UTC"
    log_file = open(log_path, "w")  # noqa: SIM115 - lifetime is the whole subprocess run, closed by caller
    cmd = [micropython_bin, "digital_twin/run_wozi_integration.py", "--host", HOST, "--port", str(PORT), *extra_args]
    print(f"== Launching: {' '.join(cmd)} (log: {log_path})")
    proc = subprocess.Popen(  # noqa: S603 - fixed, hardcoded argv, no shell, no untrusted input
        cmd,
        cwd=REPO_ROOT,
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    proc._log_file = log_file  # type: ignore[attr-defined]  # stashed only so _shutdown() below can close it
    return proc


def _shutdown(proc: subprocess.Popen[str], timeout_s: float = 15.0) -> int:
    # SIGINT, not SIGTERM/terminate(): run_wozi_integration.py's own graceful-shutdown path (FRAM/
    # SCD30 flush) only runs on KeyboardInterrupt (see that module's own __main__ block comment) -
    # a real SIGTERM would skip it entirely and lose this run's persisted state.
    if proc.poll() is None:
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5.0)
    log_file = getattr(proc, "_log_file", None)
    if log_file is not None:
        log_file.close()
    return proc.returncode if proc.returncode is not None else -1


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


def run_suite(micropython_bin: str, logs_dir: Path) -> int:
    logs_dir.mkdir(parents=True, exist_ok=True)

    # ---- Run 1: fresh boot, walk every GET endpoint, then PUT settings to carry forward. ----
    log1 = logs_dir / "run1_baseline.log"
    proc = _spawn(micropython_bin, [], log1)
    try:
        _wait_until_serving(proc)
        for path in ("/measurements", "/sensors", "/networking", "/system", "/notification", "/status", "/"):
            status, _ = _http("GET", path)
            _check(status == 200, f"Run 1: GET {path} -> 200")

        status, body = _http("PUT", "/system", {"DebugLevel": 5})
        _check(status == 200 and body.get("result", {}).get("DebugLevel") in ("Valid", "Unchanged"), "Run 1: PUT /system DebugLevel=5 accepted")
        status, body = _http("GET", "/system")
        _check(status == 200 and body.get("DebugLevel") == 5, "Run 1: GET /system reflects DebugLevel=5 immediately")

        status, body = _http("PUT", "/notification", {"WarnCO2": 1800})
        _check(status == 200 and body.get("result", {}).get("WarnCO2") in ("Valid", "Unchanged"), "Run 1: PUT /notification WarnCO2=1800 accepted")

        status, body = _http("PUT", "/sensors", {"SCD30": {"MeasInt": 4}})
        _check(status == 200 and body.get("result", {}).get("SCD30", {}).get("MeasInt") in ("Valid", "Unchanged"), "Run 1: PUT /sensors SCD30.MeasInt=4 accepted")

        status, body = _http("PUT", "/networking", {"Hostname": "ci-digital-twin"})
        _check(status == 200 and body.get("result", {}).get("Hostname") in ("Valid", "Unchanged"), "Run 1: PUT /networking Hostname accepted")

        status, body = _http("PUT", "/status", {"ResetErrors": True})
        _check(status == 200, "Run 1: PUT /status ResetErrors accepted")
    except Exception as exc:  # noqa: BLE001 - CI orchestration: surface any failure as a suite failure, not a crash
        _fail(f"Run 1 (baseline boot + settings): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(ec == 0, f"Run 1: clean shutdown (exit code {ec})")
    _check(FRAM_STATE_PATH.exists() and SCD30_STATE_PATH.exists(), "Run 1: FRAM/SCD30 state files were persisted to disk on shutdown")

    # ---- Run 2: reboot from persisted state - verbose logging from boot, settings survived. ----
    log2 = logs_dir / "run2_reboot_settings_persistence.log"
    proc = _spawn(micropython_bin, [], log2)
    try:
        _wait_until_serving(proc)
        status, body = _http("GET", "/system")
        _check(status == 200 and body.get("DebugLevel") == 5, "Run 2: DebugLevel=5 survived a real process restart (persistence of settings)")
        status, body = _http("GET", "/notification")
        _check(status == 200 and body.get("WarnCO2") == 1800, "Run 2: WarnCO2 survived a real process restart")
        status, body = _http("GET", "/sensors")
        _check(status == 200 and body.get("SCD30", {}).get("MeasInt") == 4, "Run 2: SCD30 MeasInt survived a real process restart")
        status, body = _http("GET", "/networking")
        _check(status == 200 and body.get("Hostname") == "ci-digital-twin", "Run 2: Hostname survived a real process restart")
        time.sleep(3.0)  # let a bootup/sensor-read cycle actually happen under the now-persisted DebugLevel=5
    except Exception as exc:  # noqa: BLE001
        _fail(f"Run 2 (reboot + settings persistence): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(ec == 0, f"Run 2: clean shutdown (exit code {ec})")
    log2_text = _read_log(log2)
    verbose_lines = _count_verbose_log_lines(log2_text)
    _check(verbose_lines >= 5, f"Run 2: bootup produced verbose (DebugLevel=5) log output from multiple modules ({verbose_lines} matching lines)")

    # ---- Run 3: reboot again, this time with bus fault injection, verbose logging still on. ----
    log3 = logs_dir / "run3_fault_injection.log"
    proc = _spawn(micropython_bin, ["--fault", "sgp40:writeto:8"], log3)
    try:
        _wait_until_serving(proc)
        status, body = _http("GET", "/measurements")
        _check(status == 200, "Run 3: GET /measurements still returns 200 despite an injected bus fault (graceful degradation)")
        _check(isinstance(body, dict) and "SGP40" in body, "Run 3: /measurements still reports the faulted sensor's key")
        time.sleep(3.0)  # let the faulted sensor's read cycle actually run and log the failure
        status, body = _http("GET", "/status")
        _check(status == 200, "Run 3: GET /status succeeds while a fault is active")
        sgp40_errcount = body.get("errcount", {}).get("SGP40", {}) if isinstance(body, dict) else {}
        _check(sgp40_errcount.get("counter", 0) > 0, f"Run 3: injected fault was recorded in SGP40's error counter ({sgp40_errcount!r})")
    except Exception as exc:  # noqa: BLE001
        _fail(f"Run 3 (fault injection + logging): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(ec == 0, f"Run 3: process did not crash despite the injected fault (exit code {ec})")
    log3_text = _read_log(log3)
    _check(_count_verbose_log_lines(log3_text) >= 5, "Run 3: bootup-with-fault also produced verbose log output")
    _check("SGP40" in log3_text, "Run 3: an SGP40-prefixed log line was actually printed while the fault was active")

    # ---- Run 4: reboot once more, no fault this time - proves the error record itself persisted. ----
    log4 = logs_dir / "run4_error_persistence.log"
    proc = _spawn(micropython_bin, [], log4)
    try:
        _wait_until_serving(proc)
        status, body = _http("GET", "/status")
        _check(status == 200, "Run 4: GET /status succeeds on a fresh, fault-free process")
        sgp40_errcount = body.get("errcount", {}).get("SGP40", {}) if isinstance(body, dict) else {}
        _check(sgp40_errcount.get("counter", 0) > 0, f"Run 4: SGP40's error count from Run 3 persisted across this reboot with no new fault present ({sgp40_errcount!r})")
    except Exception as exc:  # noqa: BLE001
        _fail(f"Run 4 (error persistence across reboot): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(ec == 0, f"Run 4: clean shutdown (exit code {ec})")

    # ---- Run 5: a genuinely fresh, clean boot dedicated to the soak check. ----
    _clean_state()
    log5 = logs_dir / "run5_soak.log"
    proc = _spawn(micropython_bin, ["--soak", "--soak-cycles", "20", "--duration", "0"], log5)
    try:
        ec = proc.wait(timeout=180.0)
        _check(ec == 0, f"Run 5: soak run completed cleanly (exit code {ec})")
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5.0)
        _fail("Run 5: soak run exceeded its 180s bound and was killed")
    finally:
        log_file = getattr(proc, "_log_file", None)
        if log_file is not None:
            log_file.close()
    log5_text = _read_log(log5)
    _check("soak summary" in log5_text, "Run 5: soak summary was printed")
    _check("PASS -" in log5_text, "Run 5: soak run reported PASS (no HTTP failures, watchdog never starved, memory trend within tolerance)")

    print()
    if _FAILURES:
        print(f"== digital-twin CI suite FAILED: {len(_FAILURES)} check(s) failed")
        for msg in _FAILURES:
            print(f"  - {msg}")
        return 1
    print("== digital-twin CI suite PASSED: every check succeeded")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--micropython-bin", required=True, help="path to the built MicroPython Unix-port binary")
    parser.add_argument("--logs-dir", default=str(REPO_ROOT / "digital_twin_ci_logs"), help="directory to write per-run subprocess logs into")
    args = parser.parse_args()

    _clean_state()
    return run_suite(args.micropython_bin, Path(args.logs_dir))


if __name__ == "__main__":
    sys.exit(main())
