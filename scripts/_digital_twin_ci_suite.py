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
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "digital_twin"
FRAM_STATE_PATH = STATE_DIR / "fram_state.json"
SCD30_STATE_PATH = STATE_DIR / "scd30_state.json"
CONFIG_DIR = STATE_DIR / "config"
GENERATED_SRC_DIR = REPO_ROOT / "build" / "generated_src"
# build/generated_src first: no static src/sensortask_wozi.py exists any more
# (SPECIFICATION.md Part L.2) - scripts/run_digital_twin_ci.sh generates it
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
# happen to equal `driver.upper()`, but this is NOT a general rule (CLAUDE.md/SPECIFICATION.md Part L.3
# both warn against assuming that - e.g. NotificationCoordinator's own _NAME is "NOTIFY", not
# "NOTIFICATION") - this table is the verified, narrow exception for exactly these four bus-attached,
# fault-injectable drivers, not instance_name()/`_NAME` resolution reused generically.
_DRIVER_ERRCOUNT_NAME = {"scd30": "SCD30", "sgp40": "SGP40", "bmp3xx": "BMP3XX", "fram": "FRAM"}
# Which bus-attached drivers produce a real /measurements reading (Run 4's "came back after being
# faulted" check) vs which Run 4 asserts came back at 0.
#
# That second set is NOT "the ones whose error log is in-memory" - it used to be named and described
# that way and the claim was simply false. SCD30/SGP40/BMP3XX are ALL FRAM-backed (each is
# constructed with fram=fram - see build/generated_src/sensortask_<device>.py, and CLAUDE.md's
# FRAM-backed-subset list), so none of them is in-memory-only by design. What actually makes
# SCD30/BMP3XX reset to 0 here is narrower and entirely situational: Run 3 faults `fram:write`, so
# the chip is dead for the whole run and nothing they logged could ever reach it. The property this
# set asserts is therefore "with FRAM faulted, nothing persisted", not "these logs never persist" -
# a real but much weaker claim, and one nothing currently re-checks against a HEALTHY chip. SGP40 is
# excluded because Run 5b/5c give it that stronger, chip-healthy treatment; SCD30/BMP3XX have no
# equivalent, which is a genuine coverage gap recorded in BACKLOG.md rather than papered over here.
# "fram" is deliberately absent too, despite its own error log genuinely being in-memory-only
# (AsyFramManager.pr is a plain PrintLogHistory, no fram= kwarg - confirmed directly): Run 3's own
# `fram:write` fault can leave the persisted chip's chunk status byte stuck mid-write ("torn"), and
# the dual-block+CRC self-healing read every other FRAM-backed module's own restore goes through
# (asy_fram_manager.py's _read_chunk()) correctly detects and logs that as a genuine, fresh "FRAM"-
# level error/warning on Run 4's very next boot - confirmed directly: the exact same history Run 3
# itself already asserted was recorded reappears unchanged on Run 4's fresh process. Not old data
# surviving (a real regression would be BMP3XX/SCD30 failing too, and they correctly show 0), and not
# a defect - self-healing detecting real torn state IS the FRAM driver working as designed, the same
# reasoning that already excludes SGP40's own history from an assertion here for the identical root
# cause (see this function's own comment below).
_MEASUREMENT_DRIVERS = frozenset({"scd30", "sgp40", "bmp3xx"})
_NO_PERSIST_WHEN_FRAM_FAULTED = frozenset({"scd30", "bmp3xx"})
_PERSISTED_ERROR_MODULES = ("SGP40",)  # the only fault-injectable module whose reboot persistence
# is actually PROVEN here, not the only one that has it - SCD30/BMP3XX are FRAM-backed too and
# simply have no equivalent chip-healthy check (see above, and BACKLOG.md).
# Used by Run 5b/5c. WIFI's own top-level error log is FRAM-backed too (WP1's
# implicit-FRAM-wiring rule, CLAUDE.md/SPECIFICATION.md Part A.7 - AsyConnTime passes fram=fram
# through to SensorReader.__init__ same as every other FRAM-wired module's own self.pr), so it
# follows the same all-or-nothing abrupt-restart guarantee - checked separately (Run 8), not via
# ctx.drivers, since it isn't bus-fault-injectable (no chip fake of its own).

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

# PUT /status {"ResetErrors": true} (asy_webserver_service.py's _put_status()) sequentially calls
# reset_error_counter() on every registered error source, and each FRAM-backed one's own reset()
# does a real, non-negligible FRAM write (print_log.py's PrintLogHistoryStore._write()) - not the
# single fixed-cost op the suite's other requests are. WP1/WP2/WP3 grew the FRAM-backed subset to
# 10+ entries on `dev` specifically (every CFGMGR_* logger, WIFI/NTP/WEBSERVER/SYSTEM, SGP40/BMP3XX,
# plus dev's own two uart_link instances that no other device carries - CLAUDE.md's FRAM-backed-
# subset list), so it exceeds _http()'s plain 5.0s default. Confirmed directly: the first two CI runs
# on `dev` both failed with the exact same two checks (Run 1's and Run 5c's own ResetErrors PUT, at
# both gc.threshold passes, 4 failures total) and no others - not a boot-time or wifi/fram-assertion
# flake, a genuine per-request timeout on this one heavier-than-usual call.
#
# The value is DERIVED from the server's own per-request cap, not chosen freely: a client timeout at
# or above that cap can never actually fire, because the server aborts the request first. An earlier
# flat 20.0 here was exactly that - inert, and misleading about the real budget, since it also sat
# above the 15s the real web UI gives up at (js/poll-manager.js's DEFAULT_TIMEOUT_MS). Sitting just
# ABOVE the cap is deliberate: the suite then observes the server's own abort, which is diagnosable,
# rather than a bare client-side timeout that says only "something took too long". What is still
# missing is an explicit elapsed-time budget well below the cap - this timeout is a backstop, not a
# performance assertion, and the suite is blind to the whole 5-15s band (BACKLOG.md item 24).
#
# Real hardware has since measured the call itself (dev bench board, 2026-09-17, 21 chunks): 6.32s
# idle, 11.58s with three concurrent GET /status workers - see BACKLOG.md item 24. That is BELOW the
# twin's own 8.151s for the same device, so the twin is not the optimistic end of this comparison.
# It also settles a recommendation made from that session, which was to keep a flat 20.0 here: the
# concern behind it (the budget must clear a call that really can take 11.6s) is already satisfied,
# because the value below is above the server's own cap and the server aborts anything slower at
# 15.0s - a legitimate reset cannot reach 17s in the first place. The bench tier keeps a larger
# value for a reason the twin does not share: real WiFi latency on the abort's own close.
_SERVER_OUTER_CAP_S = 15.0  # mirrors asy_webserver_service.py's own outer_cap_s default - keep in sync
_RESET_ERRORS_TIMEOUT_S = _SERVER_OUTER_CAP_S + 2.0  # loopback: no WiFi close latency to absorb
# The BUDGET, as opposed to the timeout above: a timeout only catches a call that never finished, so
# without this the suite was blind to the whole band between "normal" and the cap. Sized from both
# real datasets rather than picked: the twin's own worst observed `dev` sweep is 8.259s (5 reps,
# 21 chunks) and real hardware is 6.32s idle / 11.58s under three concurrent readers, so 80% of the
# cap sits ~45% above anything legitimate ever measured while still tripping well before the server
# would abort. In chunk terms - the regression this actually guards against - `dev` would need ~10
# more FRAM-backed sources to breach it, which is about what WP1/WP2/WP3 added between them. Only
# checked on the idle path the suite actually drives; it runs no concurrent readers during a reset.
_RESET_ERRORS_BUDGET_S = _SERVER_OUTER_CAP_S * 0.8

# Run 11 (soak) - moved host-side from digital_twin/run_generic_integration.py's own now-retired
# _soak() (SPECIFICATION.md's "Driver/DUT process separation" Part, 2026-09-14): this suite now
# drives every soak request itself, over real HTTP, the same way Runs 1-10 already do via _http()
# below, instead of delegating request-driving to the twin's own in-process HTTP client - the
# client's own allocation/CPU work no longer shares the DUT's heap, ever.
_SOAK_ENDPOINTS = ("/measurements", "/sensors", "/networking", "/system", "/notification", "/status", "/")
# 40 (wozi's own original calibration) genuinely isn't enough warmup for `dev` specifically - its
# two extra wired uart_link instances (devices/dev.toml; wozi has none) mean more one-time,
# post-boot settling (module-level caches/config-derived structures populated once, the same
# asymptotically-decaying-then-flat shape wozi's own boot already shows on a smaller scale, not a
# real unbounded leak - confirmed directly, 2026-09-14: gc.mem_free() plateaus for both devices
# given enough idle wall-clock time after boot, wozi's own curve flattening well inside 40 cycles'
# worth of real time, dev's own needing roughly 2.5x that before it does too, reproduced with the
# uart_link exercise/listen tasks fully disabled - so this is boot settling proportional to module
# count, not UART traffic). 100 gives every device, not just wozi, real wall-clock room to finish
# settling before the measured window starts, so the trend check measures a genuine plateau instead
# of an in-progress one-time settle.
_SOAK_WARMUP_CYCLES = 100
_SOAK_CYCLES = 20
# The one thing this move genuinely can't take host-side: gc.mem_free() only exists inside the
# twin's own heap, and deliberately has no REST route. digital_twin/run_generic_integration.py's
# --mem-sample-interval-ms arms a trivial background task there (_mem_sampler()) that prints one
# "MEM_SAMPLE <time.time()> <gc.mem_free()>" line per interval, decoupled from request handling -
# this suite reads those lines back out of the twin's own captured log the same way it already
# reads watchdog.would_have_triggered_count (_would_have_triggered_count() below), never by calling
# back into the twin process. 25ms is dense enough that even a fast warmup+cycles pass (a few
# hundred ms of loopback HTTP) still yields plenty of samples for a meaningful quarter split - the
# sampler itself costs one gc.collect()+print() per interval, cheap enough that a short interval
# costs nothing measurable.
_MEM_SAMPLE_INTERVAL_MS = 25
# _MEM_TREND_*: originally calibrated (run_wozi_integration.py, since retired) from five
# independent 100-cycle soaks - 25-sample first/last quarters - trend deltas of +2623, +796, -410,
# +1729, -116 bytes: max magnitude 2623, scattered around zero (evidence against a real leak, not
# the absence of variance). That calibration's own flat 8192-byte tolerance (~3.1x that magnitude)
# was ported forward (2026-09-14, the host-side move) as `8192 * sqrt(25/quarter)`, on the
# assumption a trend's standard error shrinks with 1/sqrt(quarter_size) the way it would for
# independent samples. It doesn't: real CI kept tripping this past the scaled tolerance - a
# different device each time - and a same-tree local investigation (2026-09-14) both reproduced it
# directly (two independent wozi boots in a row, 3298/2854 and 4361/2847 bytes, well past the
# scaled tolerance) and measured why. Sliding a 206-sample window (this suite's own real
# _SOAK_CYCLES=20 quarter size) across a region already 20+ real seconds past all post-boot
# settling - genuinely flat, confirmed by eye against the raw MEM_SAMPLE trace - the trend
# statistic's own empirical standard deviation came in at 1496-1964 bytes: 3.4-4.5x larger than
# the `sqrt(25/quarter)` formula's IID assumption predicts at this quarter size, because
# consecutive 25ms `gc.mem_free()` samples are heavily autocorrelated (the same reactive-GC-paced
# heap barely moves between two adjacent 25ms readings), so more samples buys far less real
# noise reduction than independent-sample statistics assume. The formula was tightening fastest
# exactly where it needed to be loosest.
# Fixed by grounding the tolerance in each attempt's own observed noise, not a historical constant
# extrapolated through a scaling law that doesn't hold: _mem_trend() below measures the spread
# *within* each quarter separately (decoupled from the early-vs-late difference the trend itself
# measures, so a genuine leak's own decline doesn't inflate the very tolerance meant to catch it)
# and sets the tolerance as a generous multiple of that. Self-calibrating per device/run/quarter
# size - no magic constant to keep re-deriving as the soak's own shape changes - and, per the same
# 2026-09-14 measurement, comfortably covers the observed worst case (5889 bytes) with room left.
_MEM_TREND_TOLERANCE_SD_MULTIPLIER = 3.0

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
    gc_threshold: int  # passed to every spawned run_generic_integration.py subprocess via
    # --gc-threshold - CLAUDE.md's/SPECIFICATION.md Part I.4(e)'s standing rule (sharpened
    # 2026-09-14 from "new stress/hammer tests" to every test, digital-twin runs included): the
    # WHOLE suite must pass clean under MicroPython's own real gc.threshold(-1) default before it's
    # ever run again with the project's chosen gc.threshold(32768) - main() runs run_suite() twice,
    # once per value, never once with a single hardcoded threshold.


# Sharpened memory-safety discipline (CLAUDE.md, SPECIFICATION.md Part I.4(e), 2026-09-14): every
# OK/FAIL line is tagged with which gc.threshold() pass produced it, set once per run_suite() call -
# every one of the ~14 run functions below stays untouched, no per-message edits needed.
_CURRENT_PASS_LABEL = ""


def _fail(msg: str) -> None:
    full_msg = f"{_CURRENT_PASS_LABEL}{msg}"
    _FAILURES.append(full_msg)
    print(f"FAIL: {full_msg}", file=sys.stderr)


def _check(*, condition: bool, msg: str) -> None:
    if not condition:
        _fail(msg)
    else:
        print(f"OK: {_CURRENT_PASS_LABEL}{msg}")


def _check_no_memory_error_in_log(log_path: Path, run_label: str) -> None:
    # SPECIFICATION.md Part I.4(e) (sharpened 2026-09-14): zero MemoryErrors, caught-and-logged
    # included - a caught allocation failure that merely avoided a crash is still a design defect,
    # not a passing result. Checked for every run's log, not only the soak test's own HTTP-level
    # failures list, since a MemoryError can just as well be logged by src/'s own catch-and-degrade
    # handlers (SPECIFICATION.md Part I.4(a)/(b)) during any run, not only under soak-style hammering.
    log_text = _read_log(log_path)
    _check(
        condition="MemoryError" not in log_text,
        msg=f"{run_label}: log contains zero MemoryErrors (caught-and-logged counts as a failure too)",
    )


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
    # entry["counter"] (PrintLogHistory's own ErrCount) increments on both errors ("E") AND
    # warnings ("W") pushed into the same history - a driver's own "recovered after N failures"
    # notice is itself a "W" entry (see e.g. src/asy_sgp40_driver.py's own read-loop recovery path),
    # so a real recovery can bump "counter" without any NEW failure. Counting one specific type's
    # history entries (default "E") is the actual "did N of THIS kind of event happen" signal this
    # suite needs - WIFI's own scripted connect failures are "W"-typed (asy_wifi_service.py's
    # conn_fail_to_hotspot uses wrn_s(), not err_s()), so Run 8 passes type_char="W".
    history = entry.get("history", [])
    return sum(1 for item in history if isinstance(item, dict) and item.get("type") == type_char)


def _errcount(name: str) -> dict[str, Any]:
    # TOLERANT: answers {} for any /status read it could not parse, because the polling helpers below
    # call this in a loop and a transient non-200 during boot must retry, not abort. That tolerance
    # is a hazard at an assertion site: {} reads as counter 0 with an empty history, so any check
    # whose EXPECTED value is 0 would hold just as happily against a server that answered nothing.
    # Assertions must use _errcount_required() below instead - the split is what stops that mistake
    # being reachable at all, rather than a rule each new call site has to remember.
    status, body = _http("GET", "/status")
    if status != _HTTP_OK or not isinstance(body, dict):
        return {}
    entry = body.get("errcount", {}).get(name, {})
    return entry if isinstance(entry, dict) else {}


def _errcount_required(name: str) -> dict[str, Any]:
    # STRICT: for assertion sites. Raises rather than returning {}, so an unreadable /status becomes
    # the enclosing run function's own `except Exception` -> _fail() instead of a silent pass. Every
    # registered error source is present in errcount whether or not it ever logged, so a missing
    # entry is always a real failure and never an empty log.
    entry = _errcount(name)
    if not entry:
        raise RuntimeError(f"GET /status did not yield a readable errcount entry for {name!r} - the server answered nothing usable, so no assertion about its counter would mean anything")
    return entry


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


def _wait_for_error_type_count(name: str, target: int, timeout_s: float, type_char: str = "E") -> dict[str, Any]:
    # Same "poll, never guess a sleep" reasoning as _wait_for_errcount_above(), but keyed on one
    # specific type's count _error_type_count() extracts rather than the raw counter (which a "W"
    # recovery notice also bumps). A fixed sleep here encodes a host-speed assumption: on this
    # project's own bench Pi4 a bounded 3-fault SGP40 run needs ~8s to record all three and settle,
    # where an x86 CI runner needs ~2s, so a 6s sleep passes there and samples mid-sequence here.
    deadline = time.monotonic() + timeout_s
    entry: dict[str, Any] = {}
    while time.monotonic() < deadline:
        entry = _errcount(name)
        if _error_type_count(entry, type_char) >= target:
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
        # Applied to every run this suite spawns, not only the soak test - CLAUDE.md's/
        # SPECIFICATION.md Part I.4(e)'s sharpened standing rule (2026-09-14) covers the whole
        # suite, digital-twin runs alike, not just "new stress/hammer tests". main() runs the whole
        # suite twice, once per RunContext.gc_threshold value.
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
    # Best-effort /proc introspection (Linux-only, exactly what every CI runner and dev box here
    # already is) for a process that ignored SIGINT for `timeout_s` seconds - `wchan` in particular
    # names the kernel function the process is actually blocked in (e.g. "do_poll" vs
    # "hrtimer_nanosleep" vs "do_futex"), which tells a real syscall-level wait apart from a wedged
    # heap or a runaway CPU-bound loop without needing a debugger attached. Never allowed to raise -
    # this is diagnostic-only, and a missing/unreadable /proc entry (process just exited, non-Linux,
    # permission quirk) must not itself fail the suite or mask the real timeout.
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
            # Never diagnosed before (see this suite's own module-level rationale for why this
            # block exists): capture what the wedged process was actually doing before killing it,
            # so a recurrence is self-diagnosing from the CI job log alone instead of leaving only
            # "exit code -9" behind.
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
            proc.wait(timeout=5.0)
    ec = proc.returncode if proc.returncode is not None else -1
    _close_log_and_check_memory_safety(proc, run_label)
    return ec


def _wait_exit(proc: subprocess.Popen[str], run_label: str, timeout_s: float) -> int:
    # For bounded (--duration N) runs that exit on their own - no signal needed or wanted.
    try:
        ec = proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5.0)
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
    # digital_twin/run_generic_integration.py's own _mem_sampler() (armed via
    # --mem-sample-interval-ms) prints "MEM_SAMPLE <time.time()> <gc.mem_free()>" once per
    # interval - the same captured-log-line pattern _would_have_triggered_count() above already
    # uses for the twin's other internal-only value. Malformed/foreign lines are skipped rather
    # than raising, matching _would_have_triggered_count()'s own tolerance for a partial log.
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
        _check(condition=status == _HTTP_OK and body.get("SCD30", {}).get("MeasInt") == _TEST_SCD30_MEAS_INT, msg="Run 2: SCD30 MeasInt survived a real process restart")
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
        ec = _shutdown(proc, "Run 3")
        _check(condition=ec == 0, msg=f"Run 3: process survived the sustained bus-fault matrix without crashing (exit code {ec})")
    wdt3 = _would_have_triggered_count(_read_log(log3))
    _check(condition=wdt3 == 0, msg=f"Run 3: watchdog never starved under sustained-but-bounded bus errors (would_have_triggered_count={wdt3!r})")


def _run_4_bus_fault_persistence_sweep(ctx: RunContext) -> None:
    # ---- Run 4: reboot fault-free after Run 3's matrix - what must reset, and that every faulted
    # bus actually comes back. Whichever of SCD30/BMP3XX this device actually has are in-memory-only
    # by design and must read back 0 (SPECIFICATION.md Part A.7); that direction is deterministic
    # and is what this run proves. ----
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
    #
    # FRAM's own error log is excluded from the reset-to-0 sweep below for the same root cause, one
    # layer down (see _NO_PERSIST_WHEN_FRAM_FAULTED's own comment): Run 3's `fram:write` fault can leave
    # a chunk's status byte torn mid-write, and the dual-block+CRC self-healing read every other
    # FRAM-backed module's restore goes through then correctly detects and logs that as a genuine,
    # fresh "FRAM"-level entry on this very run's own boot - not persisted data, and not a defect.
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


def _run_5_recovery_after_bounded_fault(ctx: RunContext) -> None:
    # ---- Run 5: clean boot, a small BOUNDED fault (not sustained) - proves recovery, the other
    # half of the self-healing story Run 3 alone can't show (it only proves "doesn't crash while
    # still broken", not "comes back once the fault clears"). SGP40 is present on every real device
    # (SPECIFICATION.md Part L.3), so this run needs no device-conditional logic at all. ----
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
        ec = _shutdown(proc, "Run 5")
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
        ec = _shutdown(proc, "Run 5b")
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
        ec = _shutdown(proc, "Run 5c-a")
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
        # Every real device wires SGP40's compensation source to SCD30 (devices/*.toml); a
        # compensation read racing SCD30's cold-start after this fresh boot used to log a real,
        # spurious E18/W14 pair for that ordinary startup timing (SPECIFICATION.md Part C.14.2,
        # fixed 2026-09-12 - found via this exact check racing that timing). Fixed at the source now, so
        # this sleep is no longer covering that up; kept as a plain settle window so the check below
        # stays about ResetErrors actually clearing the log, not about racing any boot-time read.
        time.sleep(3.0)
        # The restored history must not be a read-only relic: a ResetErrors PUT has to clear it on
        # the chip. Deliberately issued after the poll above confirmed setup() ran, so this checks
        # the ordinary case; a reset issued *before* setup() is covered separately (Part C.7
        # - it persists straight away now and the later setup() must not undo it).
        status = _put_reset_errors_timed("Run 5c")
        _check(condition=status == _HTTP_OK, msg=f"Run 5c: PUT /status ResetErrors accepted (status {status})")
        entry = _errcount_required("SGP40")
        _check(condition=_error_type_count(entry) == 0, msg=f"Run 5c: the restored history was actually cleared by ResetErrors, not just masked ({entry!r})")
    except Exception as exc:
        _fail(f"Run 5c (history survived the commanded reboot): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 5c-b")
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
        ec = _shutdown(proc, "Run 6")
        _check(condition=ec == 0, msg=f"Run 6: clean shutdown (exit code {ec})")


def _run_7_wifi_hotspot_dns(ctx: RunContext) -> None:
    # ---- Run 7: reboot with scripted repeated STA-connect failures ("no access point found") -
    # real-world WiFi fault. Drives the real STA -> hotspot fallback state machine
    # (conn_fail_to_hotspot=5 real scripted failures), starts the real DNSServer, and confirms it
    # actually answers a real UDP DNS query - not just that the internal state flipped. WiFi/NTP/
    # SystemService are mandatory infrastructure on every real device (never a [[instance]] entry,
    # SPECIFICATION.md Part L.3's device TOML schema), so this run needs no device-conditional logic.
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
        ec = _shutdown(proc, "Run 7")
        _check(condition=ec == 0, msg=f"Run 7: process survived the WiFi hotspot-fallback transition without crashing (exit code {ec})")


def _run_8_wifi_persistence_and_configure_ntp(ctx: RunContext) -> None:
    # ---- Run 8: reboot fault-free - WIFI's own persistence-correctness check, plus configure an
    # unreachable NTP host (persisted) for Run 9.
    #
    # WIFI's own top-level error log is FRAM-backed (WP1's implicit-FRAM-wiring rule - see
    # _PERSISTED_ERROR_MODULES's own comment above), so - like SGP40's Run 5b - it follows the
    # all-or-nothing abrupt-restart guarantee, never a guaranteed-reset-to-0: Run 7's own shutdown
    # is the same ordinary _shutdown() (SIGINT) every run uses, which can still catch a FRAM chunk
    # write in flight even after the REST-visible counter has already updated (Run 5b's own finding
    # - the counter and the physical write are separate, not atomic). This used to assert
    # counter==0 under a stale, pre-WP1 in-memory-only assumption that real CI never actually
    # exercised until WP1/WP2 finally went through it (confirmed stale, not a design ambiguity: the
    # fram=fram wiring and CLAUDE.md's own FRAM-backed-subset list both already state the current,
    # intended behavior). ----
    log8 = ctx.logs_dir / "run8_wifi_persistence_and_configure_ntp.log"
    proc = _spawn(ctx, [], log8)
    try:
        _wait_until_serving(proc)
        # Poll tolerantly, then re-read STRICTLY before asserting: this is the one check whose
        # expected set admits 0, so the poller's own {}-on-unreadable return would satisfy it.
        _wait_for_error_type_count("WIFI", _WIFI_SCRIPTED_FAILURES, timeout_s=30.0, type_char="W")
        entry = _errcount_required("WIFI")
        restored = _error_type_count(entry, type_char="W")
        _check(condition=restored in (0, _WIFI_SCRIPTED_FAILURES), msg=f"Run 8: WIFI's FRAM-backed history came back all-or-nothing after an abrupt restart - never a partial {restored}-entry remnant ({entry!r})")
        # 192.0.2.1: RFC 5737 TEST-NET-1, guaranteed non-routable - a deliberate, reproducible
        # "unreachable" address rather than relying on incidental CI sandbox network policy.
        status, body = _http("PUT", "/networking", {"NTP_Host": "192.0.2.1"})
        _check(condition=status == _HTTP_OK and body.get("result", {}).get("NTP_Host") in ("Valid", "Unchanged"), msg="Run 8: PUT /networking NTP_Host (unreachable) accepted")
    except Exception as exc:
        _fail(f"Run 8 (WIFI persistence check + configure unreachable NTP): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 8")
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
        ec = _shutdown(proc, "Run 9")
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
        ec = _wait_exit(proc, "Run 10", timeout_s=45.0)
        _check(condition=ec == 0, msg=f"Run 10: process survived a genuinely wedged bus and exited cleanly (exit code {ec})")
    except Exception as exc:
        _fail(f"Run 10 (watchdog hang backstop): {exc!r}")
        _wait_exit(proc, "Run 10", timeout_s=5.0)
    wdt10 = _would_have_triggered_count(_read_log(log10))
    _check(condition=wdt10 is not None and wdt10 >= 1, msg=f"Run 10: the watchdog backstop actually engaged for a genuinely wedged bus (would_have_triggered_count={wdt10!r})")


@dataclass
class _SoakAttempt:
    """One independent boot's worth of Run 11 raw results - http_failures/wdt/shutdown_ec are
    never retried on (see _run_11_soak() below), only trend_result's own tolerance check is."""

    http_failures: list[str]
    wdt_count: int | None
    shutdown_ec: int
    samples: list[int]
    trend_result: tuple[float, float, int, float, float] | None


def _run_11_soak_attempt(ctx: RunContext, log_path: Path, attempt_label: str) -> _SoakAttempt:
    # ---- Run 11: a genuinely fresh, clean boot dedicated to the soak check - driven entirely from
    # THIS process, exactly like Runs 1-10 (SPECIFICATION.md's "Driver/DUT process separation" Part,
    # 2026-09-14): warmup + cycle requests go out over real HTTP via _http() below, never through
    # the twin's own in-process client. The one thing that genuinely can't move host-side -
    # gc.mem_free(), which only exists inside the twin's own heap - is armed via
    # --mem-sample-interval-ms and read back from the twin's own captured log after the fact (see
    # _parse_mem_samples()'s own comment). Driven at ctx.gc_threshold like every other run in this
    # suite - see main()'s own comment for why the whole suite executes once per gc.threshold()
    # value, in order. ----
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
                    http_failures.append(f"{attempt_label} warmup: GET {path} -> {e!r}")
        cycles_start = time.time()
        for cycle in range(_SOAK_CYCLES):
            for path in _SOAK_ENDPOINTS:
                try:
                    status, _ = _http("GET", path)
                except (OSError, http.client.HTTPException) as e:
                    http_failures.append(f"{attempt_label} cycle {cycle}: GET {path} -> {e!r}")
                    continue
                if status != _HTTP_OK:
                    http_failures.append(f"{attempt_label} cycle {cycle}: GET {path} -> {status}")
        cycles_end = time.time()
    except Exception as exc:  # CI orchestration: surface any failure as a suite failure, not a crash
        http_failures.append(f"{attempt_label}: {exc!r}")
    finally:
        ec = _shutdown(proc, f"Run 11 ({attempt_label})")

    wdt_count = _would_have_triggered_count(_read_log(log_path))
    samples: list[int] = []
    trend_result = None
    if cycles_start is not None and cycles_end is not None:
        log_text = _read_log(log_path)
        samples = [free for ts, free in _parse_mem_samples(log_text) if cycles_start <= ts <= cycles_end]
        if len(samples) // 4 >= 1:
            trend_result = _mem_trend(samples)
    return _SoakAttempt(http_failures=http_failures, wdt_count=wdt_count, shutdown_ec=ec, samples=samples, trend_result=trend_result)


def _report_soak_attempt(attempt: _SoakAttempt, label: str) -> bool:
    """Prints/_check()s everything about one attempt except the trend-vs-tolerance verdict itself
    (the caller decides that, since it's the one thing _run_11_soak() below may retry past). Returns
    whether every non-trend aspect of this attempt was clean - a false here means _run_11_soak()
    must not retry (an HTTP/watchdog/shutdown failure is never the environment-noise this retry
    exists to absorb, SPECIFICATION.md Part E.7/E.8 - only the trend check itself is)."""
    for failure in attempt.http_failures:
        print(f"FAIL: Run 11: {failure}")
    total_requests = (_SOAK_WARMUP_CYCLES + _SOAK_CYCLES) * len(_SOAK_ENDPOINTS)
    _check(condition=not attempt.http_failures, msg=f"Run 11 ({label}): {total_requests} soak requests across every endpoint produced zero HTTP failures ({len(attempt.http_failures)} found)")
    _check(condition=attempt.wdt_count == 0, msg=f"Run 11 ({label}): watchdog never starved across the soak (would_have_triggered_count={attempt.wdt_count!r})")
    _check(condition=attempt.shutdown_ec == 0, msg=f"Run 11 ({label}): clean shutdown (exit code {attempt.shutdown_ec})")
    _check(condition=len(attempt.samples) // 4 >= 1, msg=f"Run 11 ({label}): enough MEM_SAMPLE lines in the cycles window to compute a memory trend ({len(attempt.samples)} samples)")
    return not attempt.http_failures and attempt.wdt_count == 0 and attempt.shutdown_ec == 0 and attempt.trend_result is not None


def _run_11_soak(ctx: RunContext) -> None:
    # Defense in depth on top of _mem_trend()'s own self-calibrated tolerance (see
    # _MEM_TREND_TOLERANCE_SD_MULTIPLIER's module-level comment for the real root cause this
    # addresses directly), not a substitute for it: a live process's own reactive-GC-paced heap,
    # sampled on a wall-clock timer and correlated back to a host-side window by timestamp, is still
    # a genuinely noisy measurement even once correctly calibrated. One retry, a second fully
    # independent clean boot, tells a residual bad draw apart from a real leak the same way every
    # other guard in this suite is required to justify itself (E.8's "a guard is only established by
    # removing what it guards and watching it fail"): a transient reading essentially never repeats
    # past tolerance twice in a row, a genuine unbounded leak (the failure mode this check exists to
    # catch) reliably does. Never retries an HTTP/watchdog/shutdown failure - those aren't this
    # measurement's own known noise source, and finding one ends the run immediately.
    attempt1 = _run_11_soak_attempt(ctx, ctx.logs_dir / "run11_soak.log", "attempt 1")
    clean1 = _report_soak_attempt(attempt1, "attempt 1")
    if not clean1 or attempt1.trend_result is None:
        return  # a real HTTP/watchdog/shutdown/sample-count failure - already reported, no retry
    trend1, tolerance1, quarter1, early1, late1 = attempt1.trend_result
    print(
        f"Run 11 (attempt 1) memory trend: min={min(attempt1.samples)} max={max(attempt1.samples)} "
        f"early_avg={early1:.0f} late_avg={late1:.0f} trend={trend1:.0f} tolerance={tolerance1:.0f} "
        f"quarter_size={quarter1} samples={len(attempt1.samples)}",
    )
    if trend1 <= tolerance1:
        _check(condition=True, msg=f"Run 11: gc.mem_free() trend ({trend1:.0f} bytes decline) within the {tolerance1:.0f}-byte tolerance (quarter_size={quarter1})")
        return

    print(f"Run 11: attempt 1's memory trend ({trend1:.0f} bytes) exceeded its {tolerance1:.0f}-byte tolerance - retrying once with a fresh, independent boot before failing (Part E.7/E.8's documented per-runner noise vs. a genuine leak)")
    attempt2 = _run_11_soak_attempt(ctx, ctx.logs_dir / "run11_soak_retry.log", "attempt 2 (retry)")
    clean2 = _report_soak_attempt(attempt2, "attempt 2 (retry)")
    if not clean2 or attempt2.trend_result is None:
        return  # a real HTTP/watchdog/shutdown/sample-count failure on the retry - already reported
    trend2, tolerance2, quarter2, early2, late2 = attempt2.trend_result
    print(
        f"Run 11 (attempt 2 (retry)) memory trend: min={min(attempt2.samples)} max={max(attempt2.samples)} "
        f"early_avg={early2:.0f} late_avg={late2:.0f} trend={trend2:.0f} tolerance={tolerance2:.0f} "
        f"quarter_size={quarter2} samples={len(attempt2.samples)}",
    )
    _check(
        condition=trend2 <= tolerance2,
        msg=(
            f"Run 11: gc.mem_free() trend within tolerance on a fresh independent boot after attempt 1's own "
            f"{trend1:.0f}-byte reading exceeded its {tolerance1:.0f}-byte tolerance (attempt 2: {trend2:.0f} bytes "
            f"decline, {tolerance2:.0f}-byte tolerance, quarter_size={quarter2}) - a real leak reproduces on both "
            f"independent boots, this one didn't"
        ),
    )


def _mem_trend(samples: list[int]) -> tuple[float, float, int, float, float] | None:
    # Pure trend-vs-tolerance arithmetic, split out from _run_11_soak() so it's unit-testable
    # without a live subprocess/HTTP server (tests_scripts/test_digital_twin_ci_suite_soak.py).
    # Returns (trend, tolerance, quarter_size, early_avg, late_avg), or None if there aren't at
    # least 4 samples (the caller's own _check() above already reports that case).
    quarter = len(samples) // 4
    if quarter < 1:
        return None
    early = samples[:quarter]
    late = samples[-quarter:]
    early_avg = sum(early) / len(early)
    late_avg = sum(late) / len(late)
    trend = early_avg - late_avg  # positive: memory declined between quarters
    # Tolerance is this attempt's own noise level, not a historical constant - see
    # _MEM_TREND_TOLERANCE_SD_MULTIPLIER's own module-level comment for the 2026-09-14 measurement
    # behind why. Each quarter's own internal spread (never the early-vs-late difference itself,
    # which is exactly what a genuine leak would inflate - measuring noise from the same statistic
    # a real leak moves would make the tolerance loosen precisely when it most needs to hold) stands
    # in for the trend statistic's true standard error, which a `sqrt(quarter_size)` correction
    # under real, heavily autocorrelated gc.mem_free() sampling does not reach.
    quarter_noise = max(statistics.pstdev(early), statistics.pstdev(late)) if quarter > 1 else 0.0
    tolerance = _MEM_TREND_TOLERANCE_SD_MULTIPLIER * quarter_noise
    return trend, tolerance, quarter, early_avg, late_avg


def run_suite(ctx: RunContext) -> None:
    # Runs the whole 12-top-level-run (14 real subprocess) sequence once, at ctx.gc_threshold - see
    # main() for why this whole function runs twice, not just Run 11. Doesn't tally/print
    # pass-or-fail on its own any more (main() does that once, after both passes) - _FAILURES is
    # shared, deliberately, so a single combined report names every failure from either pass.
    global _CURRENT_PASS_LABEL
    _CURRENT_PASS_LABEL = f"[gc.threshold={ctx.gc_threshold}] "
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

    base_ctx = RunContext(
        micropython_bin=args.micropython_bin,
        logs_dir=Path(args.logs_dir),  # overridden per pass below
        device=args.device,
        module=module,
        wiring_plan_path=wiring_plan_path,
        drivers=_drivers_in_plan(plan),
        gc_threshold=-1,  # overridden per pass below
    )

    # Runs the WHOLE suite twice, not just Run 11 - CLAUDE.md's/SPECIFICATION.md Part I.4(e)'s
    # standing rule, sharpened 2026-09-14 from "new stress/hammer tests" to every test, digital-twin
    # runs included: the suite must pass clean under gc.threshold(-1) (MicroPython's own real
    # reactive-only default, zero MemoryErrors anywhere - caught-and-logged included) BEFORE it's
    # ever run again with the project's chosen gc.threshold(32768) (I.4(f): defense in depth on an
    # already-safe design, never itself the reason a run passes). Order matters; -1 goes first. Two
    # separate log subdirectories so a failure's own logs from either pass are never overwritten by
    # the other.
    for gc_threshold, subdir in ((-1, "gc_threshold_neg1"), (32768, "gc_threshold_32768")):
        ctx = replace(base_ctx, logs_dir=base_ctx.logs_dir / subdir, gc_threshold=gc_threshold)
        _clean_state()
        run_suite(ctx)

    print()
    if _FAILURES:
        print(f"== digital-twin CI suite FAILED ({args.device}): {len(_FAILURES)} check(s) failed")
        for msg in _FAILURES:
            print(f"  - {msg}")
        return 1
    print(f"== digital-twin CI suite PASSED ({args.device}): every check succeeded at both gc.threshold(-1) and gc.threshold(32768)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
