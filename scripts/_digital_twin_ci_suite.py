#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Automated version of the manual digital-twin on-demand walkthrough (the project owner's own
baseline/DebugLevel/PUT-persistence/fault-injection/soak passes, formerly run by hand only) -
drives `digital_twin/run_wozi_integration.py` as a real subprocess, over real HTTP, through a
sequence of real process restarts, and asserts every step. CPython/stdlib-only (no `uv sync`
needed) since it only orchestrates the MicroPython subprocess and speaks plain HTTP/UDP to it - the
code under test still only ever runs under the real MicroPython Unix-port interpreter.

Invoked by `scripts/run_digital_twin_ci.sh` (which owns the "clean" + "build" phases); this script
is the "test" phase. See `digital_twin/README.md`'s "Automated CI suite" section for the full
walkthrough this reproduces and why each phase exists, including which error-counted modules are
FRAM-persisted vs. in-memory-only by design (SPECIFICATION.md Part A.7) - and why "permanent" bus
failures never starve the (simulated) watchdog under the current architecture, versus the one
dedicated case (`--hang`) that actually can.
"""

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
DNS_PORT = 53  # captive_dns.py's DNSServer binds ("0.0.0.0", 53) unconditionally, real port only.

# print_log.py's own per-module PrintLog `name=` values (src/*.py's `_NAME` constants) - a verbose
# (DebugLevel=5) log line is `print(name, *args)`, so a line *starting* with one of these plus a
# space is real per-module log output, not run_wozi_integration.py's own unconditional banner
# prints. Checked as a set (not all of them - some, like DNSSRV/NEOPIXEL, aren't guaranteed to log
# anything during this suite's short runs) to confirm verbose logging is genuinely flowing, not to
# pin every module's exact output.
_VERBOSE_LOG_PREFIXES = ("SYSTEM", "SGP40", "SCD30", "BMP3XX", "WEBSERVER", "NOTIFY", "WIFI", "NTP", "FRAM")

# Which error-counted modules (SPECIFICATION.md Part A.7's FRAM chunk list) are FRAM-persisted
# (survive a real reboot by design) vs. in-memory-only (deliberately reset every reboot) - the
# ones this suite actually fault-injects and can therefore check both directions for. SYSTEM/
# NEOPIXEL/NOTIFY are also FRAM-persisted but aren't independently fault-injectable via --fault (no
# bus-level chip fake of their own), so they're out of this suite's scope - see
# digital_twin/README.md for the full account.
_PERSISTED_ERROR_MODULES = ("SGP40",)
_IN_MEMORY_ERROR_MODULES = ("SCD30", "BMP3XX", "FRAM", "WIFI")

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
    if status != 200 or not isinstance(body, dict):
        return {}
    entry = body.get("errcount", {}).get(name, {})
    return entry if isinstance(entry, dict) else {}


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


def _wait_exit(proc: subprocess.Popen[str], timeout_s: float) -> int:
    # For bounded (--duration N) runs that exit on their own - no signal needed or wanted.
    try:
        ec = proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5.0)
        ec = -1
    log_file = getattr(proc, "_log_file", None)
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
    # run_wozi_integration.py's own unconditional shutdown line (see main()'s finally block) -
    # "...shutdown: would_have_triggered_count=N". Returns None if the line was never printed
    # (e.g. the process crashed before reaching its own finally block).
    for line in log_text.splitlines():
        if "would_have_triggered_count=" in line:
            try:
                return int(line.rsplit("=", 1)[1].strip())
            except ValueError:
                return None
    return None


def _build_dns_query(query_id: int = 0x1234, qname: str = "example.com") -> bytes:
    header = struct.pack(">HHHHHH", query_id, 0x0100, 1, 0, 0, 0)  # ID, flags(RD), QDCOUNT=1
    question = b"".join(bytes([len(part)]) + part.encode() for part in qname.split("."))
    question += b"\x00" + struct.pack(">HH", 1, 1)  # root label, QTYPE=A, QCLASS=IN
    return header + question


def _try_dns_query(host: str, timeout: float = 2.0) -> bool:
    query = _build_dns_query()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(query, (host, DNS_PORT))
        data, _addr = sock.recvfrom(512)
        if len(data) < 4:
            return False
        resp_id, flags = struct.unpack(">HH", data[:4])
        return resp_id == 0x1234 and bool(flags & 0x8000)  # QR bit set = a real response, not an echo
    except OSError:
        return False
    finally:
        sock.close()


def _wait_for_dns_answer(host: str, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _try_dns_query(host):
            return True
        time.sleep(1.0)
    return False


def run_suite(micropython_bin: str, logs_dir: Path) -> int:
    logs_dir.mkdir(parents=True, exist_ok=True)

    # ---- Run 1: fresh boot, walk every GET endpoint, PUT settings to carry forward. ----
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
    verbose_lines = _count_verbose_log_lines(_read_log(log2))
    _check(verbose_lines >= 5, f"Run 2: bootup produced verbose (DebugLevel=5) log output from multiple modules ({verbose_lines} matching lines)")

    # ---- Run 3: reboot with a sustained/high-repeat-count ("permanent") bus-fault matrix across
    # every bus-level error-counted module at once - proves the system keeps logging/counting every
    # failure AND the watchdog never starves under sustained failure (bounded, immediately-raised
    # errors, not an indefinite hang - see this file's own module docstring and
    # digital_twin/_fault_injection.py's for why that distinction matters here). ----
    log3 = logs_dir / "run3_sustained_bus_fault_matrix.log"
    proc = _spawn(
        micropython_bin,
        ["--fault", "scd30:writeto:500", "--fault", "sgp40:writeto:500", "--fault", "bmp3xx:readfrom_mem:500", "--fault", "fram:write:500"],
        log3,
    )
    try:
        _wait_until_serving(proc)
        time.sleep(6.0)  # let every faulted sensor's own read cycle actually run several times
        for path in ("/measurements", "/sensors", "/status"):
            status, _ = _http("GET", path)
            _check(status == 200, f"Run 3: GET {path} still returns 200 under a sustained bus-fault matrix (graceful degradation)")
        for name in ("SCD30", "SGP40", "BMP3XX", "FRAM"):
            entry = _errcount(name)
            _check(entry.get("counter", 0) > 0, f"Run 3: {name}'s injected sustained fault was recorded in its error counter ({entry!r})")
    except Exception as exc:  # noqa: BLE001
        _fail(f"Run 3 (sustained bus-fault matrix): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(ec == 0, f"Run 3: process survived the sustained bus-fault matrix without crashing (exit code {ec})")
    wdt3 = _would_have_triggered_count(_read_log(log3))
    _check(wdt3 == 0, f"Run 3: watchdog never starved under sustained-but-bounded bus errors (would_have_triggered_count={wdt3!r})")

    # ---- Run 4: reboot fault-free - persistence-correctness sweep for every module Run 3 faulted.
    # SGP40 is FRAM-backed (should persist); SCD30/BMP3XX/FRAM are in-memory-only by design (should
    # reset to 0) - SPECIFICATION.md Part A.7. Both directions are real, checkable design claims. ----
    log4 = logs_dir / "run4_bus_fault_persistence_sweep.log"
    proc = _spawn(micropython_bin, [], log4)
    try:
        _wait_until_serving(proc)
        for name in _PERSISTED_ERROR_MODULES:
            entry = _errcount(name)
            _check(entry.get("counter", 0) > 0, f"Run 4: {name}'s error count persisted across reboot as designed (FRAM-backed) ({entry!r})")
        for name in ("SCD30", "BMP3XX", "FRAM"):  # WIFI's own reset check is Run 8, after its own fault run (Run 7)
            entry = _errcount(name)
            _check(entry.get("counter", 0) == 0, f"Run 4: {name}'s error count correctly did NOT persist across reboot (in-memory-only by design) ({entry!r})")
    except Exception as exc:  # noqa: BLE001
        _fail(f"Run 4 (bus-fault persistence-correctness sweep): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(ec == 0, f"Run 4: clean shutdown (exit code {ec})")

    # ---- Run 5: clean boot, a small BOUNDED fault (not sustained) - proves recovery, the other
    # half of the self-healing story Run 3 alone can't show (it only proves "doesn't crash while
    # still broken", not "comes back once the fault clears"). ----
    _clean_state()
    log5 = logs_dir / "run5_recovery_after_bounded_fault.log"
    proc = _spawn(micropython_bin, ["--fault", "sgp40:writeto:3"], log5)
    try:
        _wait_until_serving(proc)
        time.sleep(6.0)  # comfortably more than 3 SGP40 read cycles (~1Hz) - the fault should be exhausted by now
        entry = _errcount("SGP40")
        errors_after_exhaustion = _error_type_count(entry)
        _check(errors_after_exhaustion == 3, f"Run 5: SGP40's bounded fault (3 failures) was fully recorded, no more ({entry!r})")
        time.sleep(3.0)  # a few more cycles past exhaustion - real ("E") errors should NOT keep climbing
        # (a "W" recovery notice may legitimately appear here - see _error_type_count()'s own comment)
        entry2 = _errcount("SGP40")
        _check(_error_type_count(entry2) == errors_after_exhaustion, f"Run 5: SGP40's real error count stopped climbing once the fault cleared (recovery) ({entry2!r})")
        status, body = _http("GET", "/measurements")
        sgp40_reading = body.get("SGP40", {}) if status == 200 and isinstance(body, dict) else {}
        _check(status == 200 and bool(sgp40_reading), f"Run 5: SGP40 measurements resumed after recovery ({sgp40_reading!r})")
    except Exception as exc:  # noqa: BLE001
        _fail(f"Run 5 (recovery after a bounded fault): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(ec == 0, f"Run 5: clean shutdown (exit code {ec})")

    # ---- Run 6: clean boot, configure a real SSID (persisted) for Run 7's WiFi test below - a
    # real configured SSID, not the "SSID==''" unconfigured shortcut, is needed for a genuine
    # STA-connect-failure cycle (matches tests/test_digital_twin_sensortask_integration.py's own
    # in-process precedent for this same distinction). ----
    _clean_state()
    log6 = logs_dir / "run6_configure_ssid.log"
    proc = _spawn(micropython_bin, [], log6)
    try:
        _wait_until_serving(proc)
        status, body = _http("PUT", "/networking", {"SSID": "digital-twin-test-ssid"})
        _check(status == 200 and body.get("result", {}).get("SSID") in ("Valid", "Unchanged"), "Run 6: PUT /networking SSID accepted")
    except Exception as exc:  # noqa: BLE001
        _fail(f"Run 6 (configure SSID for WiFi test): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(ec == 0, f"Run 6: clean shutdown (exit code {ec})")

    # ---- Run 7: reboot with scripted repeated STA-connect failures ("no access point found") -
    # real-world WiFi fault. Drives the real STA -> hotspot fallback state machine
    # (conn_fail_to_hotspot=5 real scripted failures), starts the real DNSServer, and confirms it
    # actually answers a real UDP DNS query - not just that the internal state flipped.
    #
    # Only possible because of digital_twin/_unix_port_udp_addr_shim.py: BACKLOG.md's "Real-hardware
    # verification gap for asy_udp_socket.py/captive_dns.py" entry root-caused three separate
    # Unix-port-only socket quirks (a plain (host, port) tuple rejected by bind()/connect()/sendto(),
    # and recvfrom() returning a raw sockaddr struct instead of the (str, int) shape production code
    # expects) that made a real UDP round trip impossible under this harness before that shim existed
    # - all three correct, required behavior for real rp2 hardware, so src/ itself stays untouched;
    # the shim works around them entirely from twin-side code, applied by
    # run_wozi_integration.py's own main() before anything constructs a socket. ----
    log7 = logs_dir / "run7_wifi_hotspot_dns.log"
    proc = _spawn(
        micropython_bin,
        ["--wifi-outcome", "no_ap", "--wifi-outcome", "no_ap", "--wifi-outcome", "no_ap", "--wifi-outcome", "no_ap", "--wifi-outcome", "no_ap"],
        log7,
    )
    try:
        _wait_until_serving(proc)
        entry = _wait_for_errcount_above("WIFI", 0, timeout_s=40.0)
        _check(entry.get("counter", 0) > 0, f"Run 7: repeated WiFi connect failures drove real hotspot fallback and were recorded in WIFI's error counter ({entry!r})")
        # Generous: _wait_for_errcount_above() above returns as soon as WIFI's counter is > 0 - the
        # very FIRST scripted failure, not all 5 - so hotspot activation (conn_fail_to_hotspot=5,
        # wifi_refresh_sec=5 between attempts) hasn't necessarily even started by the time this
        # wait begins. Observed ~30-34s from cold boot to a real answered query in manual testing.
        answered = _wait_for_dns_answer(HOST, timeout_s=50.0)
        _check(answered, "Run 7: the real captive DNSServer answered a real UDP DNS query after WiFi hotspot fallback")
        status, _ = _http("GET", "/status")
        _check(status == 200, "Run 7: webserver stayed reachable throughout the WiFi hotspot-fallback transition")
    except Exception as exc:  # noqa: BLE001
        _fail(f"Run 7 (WiFi hotspot fallback + DNS): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(ec == 0, f"Run 7: process survived the WiFi hotspot-fallback transition without crashing (exit code {ec})")

    # ---- Run 8: reboot fault-free - WIFI's own persistence-correctness check (in-memory-only,
    # should reset to 0), plus configure an unreachable NTP host (persisted) for Run 9. ----
    log8 = logs_dir / "run8_wifi_persistence_and_configure_ntp.log"
    proc = _spawn(micropython_bin, [], log8)
    try:
        _wait_until_serving(proc)
        entry = _errcount("WIFI")
        _check(entry.get("counter", 0) == 0, f"Run 8: WIFI's error count correctly did NOT persist across reboot (in-memory-only by design) ({entry!r})")
        # 192.0.2.1: RFC 5737 TEST-NET-1, guaranteed non-routable - a deliberate, reproducible
        # "unreachable" address rather than relying on incidental CI sandbox network policy.
        status, body = _http("PUT", "/networking", {"NTP_Host": "192.0.2.1"})
        _check(status == 200 and body.get("result", {}).get("NTP_Host") in ("Valid", "Unchanged"), "Run 8: PUT /networking NTP_Host (unreachable) accepted")
    except Exception as exc:  # noqa: BLE001
        _fail(f"Run 8 (WIFI persistence check + configure unreachable NTP): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(ec == 0, f"Run 8: clean shutdown (exit code {ec})")

    # ---- Run 9: reboot with NTP permanently unreachable - the other "network connections" real-
    # world case. The system must stay fully healthy (webserver reachable) despite NTP never
    # succeeding, not just eventually. ----
    log9 = logs_dir / "run9_ntp_unreachable.log"
    proc = _spawn(micropython_bin, [], log9)
    try:
        _wait_until_serving(proc)
        time.sleep(7.0)  # past _NTP_FETCH_TIMEOUT_MS=5000 (sensortask_wozi.py) - NTP should have given up by now
        status, _ = _http("GET", "/system")
        _check(status == 200, "Run 9: webserver stayed fully healthy with NTP permanently unreachable")
    except Exception as exc:  # noqa: BLE001
        _fail(f"Run 9 (NTP unreachable): {exc!r}")
    finally:
        ec = _shutdown(proc)
        _check(ec == 0, f"Run 9: clean shutdown (exit code {ec})")

    # ---- Run 10: the dedicated hang case - a real, blocking (not asyncio) time.sleep() inside a
    # chip fake's handler, genuinely freezing the whole interpreter past the 8000ms WDT window, to
    # prove the (simulated) watchdog backstop itself actually engages - the one thing sustained-but-
    # bounded errors (Run 3) cannot demonstrate. See digital_twin/_fault_injection.py's own module
    # docstring for why this - and only this - is what real hardware's "genuinely wedged bus"
    # scenario requires (SPECIFICATION.md Part F.2, CLAUDE.md's own settled "hardware watchdog is
    # the accepted backstop" rule). --duration 0 exits as soon as _wait_until_serving() succeeds,
    # which itself is delayed by the hang - no signal needed. ----
    _clean_state()
    log10 = logs_dir / "run10_watchdog_hang_backstop.log"
    proc = _spawn(micropython_bin, ["--hang", "sgp40:writeto:12", "--duration", "0"], log10)
    try:
        # Deliberately NOT _wait_until_serving() here: --duration 0 exits as soon as its own
        # internal _wait_until_serving() succeeds, which races this external check for the socket
        # - by the time this process's own HTTP poll could land, the twin subprocess may already be
        # past that point and mid-shutdown (confirmed by direct reproduction). The only outcomes
        # that actually matter are "did it exit cleanly" and "did the log show the backstop fired",
        # both checked below without needing serving to still be observable from outside.
        ec = _wait_exit(proc, timeout_s=30.0)
        _check(ec == 0, f"Run 10: process survived a genuinely wedged bus and exited cleanly (exit code {ec})")
    except Exception as exc:  # noqa: BLE001
        _fail(f"Run 10 (watchdog hang backstop): {exc!r}")
        _wait_exit(proc, timeout_s=5.0)
    wdt10 = _would_have_triggered_count(_read_log(log10))
    _check(wdt10 is not None and wdt10 >= 1, f"Run 10: the watchdog backstop actually engaged for a genuinely wedged bus (would_have_triggered_count={wdt10!r})")

    # ---- Run 11: a genuinely fresh, clean boot dedicated to the soak check. ----
    _clean_state()
    log11 = logs_dir / "run11_soak.log"
    proc = _spawn(micropython_bin, ["--soak", "--soak-cycles", "20", "--duration", "0"], log11)
    try:
        ec = proc.wait(timeout=180.0)
        _check(ec == 0, f"Run 11: soak run completed cleanly (exit code {ec})")
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5.0)
        _fail("Run 11: soak run exceeded its 180s bound and was killed")
    finally:
        log_file = getattr(proc, "_log_file", None)
        if log_file is not None:
            log_file.close()
    log11_text = _read_log(log11)
    _check("soak summary" in log11_text, "Run 11: soak summary was printed")
    _check("PASS -" in log11_text, "Run 11: soak run reported PASS (no HTTP failures, watchdog never starved, memory trend within tolerance)")

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
