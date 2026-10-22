#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""L2 system suite: boots one derived device's generated graph in the twin (digital_twin/run_generic_integration.py) as
a subprocess, driving it over HTTP/UDP through real restarts at gc.threshold -1, then 32768; its fault matrix comes from
the device's wiring plan. Run by scripts/run_digital_twin_ci.sh; see digital_twin/README.md "Automated CI suite"."""

import argparse
import http.client
import json
import os
import shutil
import socket
import statistics
import struct
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import tomllib

if TYPE_CHECKING:
    from collections.abc import Callable

# The repo root is appended, so tests/ resolves as a namespace package and no tests/ fake shadows a host module.
sys.path.append(str(Path(__file__).resolve().parent.parent))
from buildgen.buildspec import BUS_ATTACHED_DRIVERS
from buildgen.model import instance_label, load_device
from buildgen.validate import device_max_connections_by_name, module_float_const, module_int_const
from scripts._port_lock import PortHeldError, port_lock
from scripts._summary_block import Summary
from scripts._twin_process import (
    EXIT_SIMULATED_BOOTLOADER,
    EXIT_SIMULATED_RESET,
    TWIN_MICROPYPATH,
    JSONObject,
    JSONValue,
    ShutdownLine,
    TwinLaunch,
    TwinRun,
    errcount_entry,
    errcount_table,
    exit_reason,
    feed_gap_verdict,
    log_memory_verdict,
    log_tail,
    parse_machine_reset_line,
    parse_shutdown_line,
    read_log,
    shutdown,
    spawn,
    state_paths,
    wait_exit,
    wait_until_serving,
)
from scripts._twin_process import (
    MEMORY_ERROR_MARKERS as _MEMORY_ERROR_MARKERS,
)
from scripts._twin_process import (
    http as twin_http,
)
from tests._error_codes import code

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
# run_digital_twin_ci.sh regenerates every device's module and wiring plan through buildgen into
# this gitignored directory before the suite runs.
GENERATED_SRC_DIR = REPO_ROOT / "build" / "generated_src"
GENERATOR = REPO_ROOT / "scripts" / "_generate_sensortask_modules.py"
HOST = "127.0.0.1"
PORT = 18080  # a fixed, non-privileged, non-8080-default port - avoids colliding with a real
# manual `scripts/run_unix_port_integration.sh` run on the same machine.
DNS_PORT = 53  # asy_captive_dns.py's CaptiveDNS binds ("0.0.0.0", 53) unconditionally, real port only.
_LOCK_RUNNER = "scripts/_digital_twin_ci_suite.py"
_NTP_UNREACHABLE_HOST = "192.0.2.1"  # RFC 5737 TEST-NET-1, never answers: Run 8 configures it, Run 9 watches it
_NTP_PORT = 123
_CAP_NET_BIND_SERVICE = 10  # linux/capability.h
_VFS_CAP_FLAGS_EFFECTIVE = 0x1  # the security.capability xattr's effective bit (linux/capability.h)

# Per-module PrintLog `name=` values. A verbose log line is `print(name, *args)`, so a line
# starting with one of these plus a space is real module output, not the runner's own banners.
# A loose set on purpose: it confirms verbose logging flows rather than pinning any module's output.
_VERBOSE_LOG_PREFIXES = ("SYSTEM", "SGP40", "SCD30", "BMP3XX", "WEBSERVER", "NOTIFY", "WIFI", "NTP", "FRAM")

# The fault matrix, keyed by TOML `driver` and applied to every instance the device wires. Run 3's sustained
# fault per driver: the writes every I2C driver's setup and reads go through, FRAM gone (`silent`: zeros, its bytes
# kept, the one FRAM failure the port can produce) and a UART link going quiet.
_SUSTAINED_FAULT = {"scd30": "writeto", "sgp40": "writeto", "bmp3xx": "writeto", "isl29125": "writeto", "fram": "silent", "uart_link": "silent"}
# Run 3's FRAM write ceiling: a persisted-log chunk write takes 627-700 ms on silicon under load, one block at a time
# device-wide (SPECIFICATION.md's rate.persisted_log row), so a storm persists at most one entry per 627 ms.
_PERSISTED_LOG_CHUNK_WRITE_MS = 627
# Run 5c's chain: one bounded fault per chip on its periodic bus call, read through each driver's own call sites.
_BOUNDED_FAULT = {"scd30": "writeto", "sgp40": "writeto", "bmp3xx": "readfrom_mem", "isl29125": "readfrom_mem"}
# Run 5: SGP40's measure-raw read only (the read after the 0x260F command), so setup and the heater-off rung stay healthy.
_RUN_5_FAULT_OP = "readfrom_into"
_SGP40_MEASURE_RAW = 0x260F
# Run 12's stack-exhaustion cell: one read op per driver, each a queued fault the twin raises a C-stack overflow from.
_STACK_FAULT_READ_OP = {"scd30": "readfrom_into", "sgp40": "readfrom_into", "bmp3xx": "readfrom_mem", "isl29125": "readfrom_mem", "fram": "readinto"}
_READ_CYCLES = 2  # Run 5's observed SGP40 read cycles past the spent fault
# Each failed read cycle logs the driver's READ and the base class's STREAK (asy_base_classes.py _error_check()),
# two counter steps per injected fault, and nothing else an E: those two are Run 5's only E codes.
_EVENTS_PER_FAILED_READ = 2
_RUN_5_ERRORS = ("READ", "STREAK")
_TIME_FIELDS = 8  # rp2's time tuple: year, month, mday, hour, minute, second, weekday, yearday
# Run 10: one bounded hang per driver, each in its own process; a hang freezes the whole interpreter whichever
# bus call it sits in, so one representative op per driver proves the backstop.
_HANG_MATRIX = {"scd30": "writeto", "sgp40": "writeto", "bmp3xx": "writeto", "isl29125": "writeto", "fram": "readinto"}
_SAME_FREEZE = "a hang freezes the interpreter whichever bus call it sits in; Run 10 hangs one representative op per driver"
_LEFT_OUT = {
    ("bmp3xx", "fault", "writeto_mem"): "a configuration write; its failure path is tests/test_asy_bmp3xx_driver.py's and tests/test_digital_twin_bmp3xx.py's",
    ("isl29125", "fault", "writeto_mem"): "a configuration write; its failure path is tests/test_digital_twin_isl29125.py's",
    ("isl29125", "fault", "int_stuck_high"): "a persistent INT mode; tests/test_digital_twin_isl29125_autorange.py drives it",
    ("scd30", "fault", "readfrom_into"): "the read half of SCD30's one bus session; tests/test_asy_scd30_driver.py and tests/test_digital_twin_scd30.py cover it",
    ("sgp40", "fault", "general_call"): "sent only by bus recovery; tests/test_digital_twin_sgp40.py covers the reset",
    ("fram", "fault", "readinto"): "a failed chunk read takes the store's self-healing path, tests/test_asy_fram_manager.py and tests/test_digital_twin_fram.py",
    ("fram", "fault", "wren"): "a dropped write-enable; tests/test_digital_twin_fram.py drives it",
    ("bmp3xx", "hang", "readfrom_mem"): _SAME_FREEZE,
    ("bmp3xx", "hang", "writeto_mem"): _SAME_FREEZE,
    ("isl29125", "hang", "readfrom_mem"): _SAME_FREEZE,
    ("isl29125", "hang", "writeto_mem"): _SAME_FREEZE,
    ("scd30", "hang", "readfrom_into"): _SAME_FREEZE,
    ("sgp40", "hang", "readfrom_into"): _SAME_FREEZE,
    ("fram", "hang", "write"): _SAME_FREEZE,
    ("wlan", "fault", "*"): "every WLAN raise_on method is tests/test_asy_wifi_service.py's; Run 7 drives connect outcomes by --wifi-outcome",
    ("uart_link", "fault", "bounded"): "drop, corrupt and truncate are tests/test_digital_twin_uart_link.py's; Run 3 carries uart_link:silent",
}
# @tunable l2.ntp_unreachable_watch_s = 90.0
_NTP_UNREACHABLE_WATCH_S = 90.0  # Run 9's bound - past the old NTP give-up (~60s), see that run
# The attempts the NTP backoff (10 s, doubling) makes inside that bound, measured failing at ~4, 22 and 62 s of
# serving, the next at ~142 s: Run 9's watch ends once that many failed (agent, 2026-10-15).
# @tunable l2.ntp_unreachable_failures = 3
_NTP_UNREACHABLE_FAILURES = 3
# @tunable l2.bus_fault_error_count = 500
_BUS_FAULT_ERROR_COUNT = 500  # sustained/high-repeat-count - see Run 3's own comment for why.
# Driver to its own REST/error-log `_NAME`, read from each driver's source and pinned to it by an L0 test; an
# instance's name appends "_<name_ext>" (instance_name()). Not driver.upper(): uart_link's is "UART".
_DRIVER_ERRCOUNT_NAME = {"scd30": "SCD30", "sgp40": "SGP40", "bmp3xx": "BMP3XX", "isl29125": "ISL29125", "fram": "FRAM", "uart_link": "UART"}
# The registered error sources not FRAM-backed, exempt from Run 5c's loss sweep: FRAMManager's own log (the store
# cannot persist its failures through itself) and CFGMGR_SCD30 (RAM-only, owner, 2026-09-29: 'no extra FRAM chunk').
# _sensortask_scenarios.py pins the same set from the real object graph.
_IN_MEMORY_ONLY_ERROR_SOURCES = frozenset({"FRAM", "CFGMGR_SCD30"})
# Which bus-attached drivers produce a real /measurements reading (Run 4's "came back after being faulted" check)
# vs which Run 4 asserts came back at 0: with FRAM gone in Run 3 nothing they logged persisted. SGP40 and "fram" are
# each absent for their own reason; digital_twin/README.md has both accounts in full.
_MEASUREMENT_DRIVERS = frozenset({"scd30", "sgp40", "bmp3xx", "isl29125"})
_NO_PERSIST_WHEN_FRAM_FAULTED = frozenset({"scd30", "bmp3xx", "isl29125"})
# Run 5b's own abrupt-restart subject, not a claim about who has persistence: Run 5b reboots straight onto Run 5's
# state, and Run 5 faults only SGP40. Run 5c proves the chip-healthy half for every bus-attached driver.
_PERSISTED_ERROR_MODULES = ("SGP40",)

# The one HTTP status every endpoint in this suite is expected to answer with - a non-200 anywhere
# is a suite failure, never an alternative success path.
_HTTP_OK = 200

# The settings Run 1 PUTs and every later run reads back, the thresholds the assertions compare
# against, and the scripted fault counts handed to --fault/--wifi-outcome. Named here so the
# value a run INJECTS and the value its assertion EXPECTS cannot drift apart.
_TEST_DEBUG_LEVEL = 5
_TEST_WARN_CO2 = 1800
_TEST_SCD30_MEAS_INT = 4
_TEST_SSID = "digital-twin-test-ssid"
_MIN_VERBOSE_LOG_LINES = 5
# @tunable l2.bounded_fault_count = 3
_BOUNDED_FAULT_COUNT = 3  # injected bus failures per bounded-fault run - SGP40's measure reads in Run 5/5b, then
# one link per chip instance in Run 5c; each injected fault fails one SGP40 measure read, and three exhaust the
# supervisor's restart budget elsewhere, which is why the count stays this small.
# @tunable l2.wifi_scripted_failures = 5
_WIFI_SCRIPTED_FAILURES = 5  # asy_wifi_service.py's conn_fail_to_hotspot - the failure count that trips hotspot fallback
# The five identical verdicts spend ONE history slot (the central newest-entry rule, asy_print_log.py) and count
# five; the fifth's fallback to the hotspot persists its own WLAN_TO_HOTSPOT warning in a second slot (Part C.7.1).
_WIFI_PERSISTED_WARNINGS = 2
_WIFI_PERSISTED_EVENTS = _WIFI_SCRIPTED_FAILURES + 1  # the counter: five failures, then the fallback
# Run 5's allowed warnings: the recovery ladder's two rungs and SGP40's own storage warnings (a blank chip's first
# restore warns "No backup found"), each by catalog name, so a renumbering cannot leave a stale literal here.
_RUN_5_ALLOWED_WARNINGS = ("DEVICE_RECOVERY", "BUS_RECOVERY", "SGP_RESTORED_NO_TS", "SGP_BACKUP_AGE", "SGP_WRITTEN_NO_TS", "SGP_NO_BACKUP")
# Run 13's near misses of the system-command words: whole-string equality only, so each must be refused.
_SYSTEM_CMD_NEAR_MISSES = ("Reboot", "reboot ", " reboot", "REBOOT", "reboo", "eraseFRAM", "reset", "")
# The four step lines of a controlled shutdown, S1-S4 (asy_system_service.py's _shutdown_sequence()), and S5's prefix.
_SHUTDOWN_STEP_LINES = ("Shutdown: supervisor stopped", "Shutdown: config stores closed and flushed", "Shutdown: storage quiesced", "Shutdown: supervised tasks stopped")
_SHUTDOWN_S5_PREFIXES = ("Shutdown: resetconfig", "Shutdown: erasefram")

# ResetErrors resets every source at once, each FRAM-backed one still paying its own chunk write, so it
# far exceeds _http()'s 5s default. The value below is derived from the server's own _DEFAULT_OUTER_CAP_S;
# README.md has the derivation and SPECIFICATION.md Part C.7 the real-hardware measurements.
# @tunable web.outer_cap_s = 15.0
_SERVER_OUTER_CAP_S = 15.0  # mirrors asy_webserver_service.py's _DEFAULT_OUTER_CAP_S - keep in sync
# @tunable l2.reset_errors_timeout_margin_s = 2.0
_RESET_ERRORS_TIMEOUT_S = _SERVER_OUTER_CAP_S + 2.0  # loopback: no WiFi close latency to absorb
# The BUDGET rather than the timeout above, which only catches a call that never finished. Sized from both datasets -
# twin 8.259s worst, hardware 6.32s idle and 11.58s under load - so 80% of the cap sits ~45% above anything legitimate,
# and a device wiring the most FRAM-backed sources still leaves ~10 before the budget.
# @tunable l2.reset_errors_budget_ratio = 0.8
_RESET_ERRORS_BUDGET_S = _SERVER_OUTER_CAP_S * 0.8

# Run 11 (soak), host-side ("Driver/DUT process separation"): every soak request goes over real HTTP, so the client's
# allocation and CPU work never shares the DUT's heap; each cycle walks every GET route the device serves and the site.
# @tunable l2.soak_warmup_cycles = 100
_SOAK_WARMUP_CYCLES = 100
# The warm-up ends once no cycle sets a new MEM_SAMPLE floor for this many cycles, the bound above: a device with more
# instances settles longer after boot, and a trend taken mid-settle would read as a leak (digital_twin/README.md).
# @tunable l2.soak_plateau_cycles = 20
_SOAK_PLATEAU_CYCLES = 20
# @tunable l2.soak_cycles = 20
_SOAK_CYCLES = 20
# gc.mem_free() lives in the twin's heap with no REST route, so --mem-sample-interval-ms prints a MEM_SAMPLE
# line per interval and this suite scrapes them from the captured log; 25ms yields plenty of samples for a
# quarter split, and one gc.collect()+print() per interval costs nothing measurable.
# @tunable l2.mem_sample_interval_ms = 25
_MEM_SAMPLE_INTERVAL_MS = 25
# The tolerance is grounded in each run's own observed noise rather than a historical
# constant scaled by a law that does not hold here - consecutive 25ms gc.mem_free() samples are
# heavily autocorrelated. digital_twin/README.md has the measurement and what it replaced.
# @tunable l2.mem_trend_tolerance_sd_multiplier = 3.0
_MEM_TREND_TOLERANCE_SD_MULTIPLIER = 3.0

# Wait budgets and poll steps, one per purpose. Each wait polls for its condition and returns early;
# the fixed sleeps wait for an absence, which no probe can observe.
# @tunable l2.error_count_wait_s = 30.0
_ERROR_COUNT_WAIT_S = 30.0  # an error-log entry a fault or a restore has to land
# @tunable l2.first_fault_wait_s = 45.0
_FIRST_FAULT_WAIT_S = 45.0  # a faulted driver's first "E" entry after its boot
# @tunable l2.long_wait_s = 90.0
_LONG_WAIT_S = 90.0  # a bounded fault settling, and WiFi falling back to the hotspot and its DNS
# @tunable l2.escalation_wait_s = 120.0
_ESCALATION_WAIT_S = 120.0  # the supervisor's escalation, then its reset: Run 3's restart budget spent, Run 12's stack overflow
# @tunable l2.ntp_first_sync_wait_s = 60.0
_NTP_FIRST_SYNC_WAIT_S = 60.0  # a station link's first sync against the twin's local NTP responder
# @tunable l2.read_cycle_wait_s = 30.0
_READ_CYCLE_WAIT_S = 30.0  # two observed SGP40 read cycles after Run 5's fault is spent
# @tunable l2.hang_run_exit_wait_s = 45.0
_HANG_RUN_EXIT_WAIT_S = 45.0  # Run 10's --duration 15 run, hung bus call included
# @tunable l2.failed_run_exit_wait_s = 5.0
_FAILED_RUN_EXIT_WAIT_S = 5.0
# A commanded reset runs the controlled shutdown, whose first step may wait one supervisor period, then the
# reset's own delay; the margin covers the twin's scheduling on a loaded host.
# @tunable l2.commanded_reset_margin_s = 10.0
_COMMANDED_RESET_MARGIN_S = 10.0
# @tunable l2.verbose_poll_s = 0.5
_VERBOSE_POLL_S = 0.5
# @tunable l2.errcount_poll_s = 1.0
_ERRCOUNT_POLL_S = 1.0
# @tunable l2.dns_poll_s = 0.5
_DNS_POLL_S = 0.5
# @tunable l2.concurrent_get_join_margin_s = 5.0
_JOIN_MARGIN_S = 5.0  # past a burst's own timeout, so a thread is joined only once its request gave up
# @tunable l2.slot_release_wait_s = 1.0
_SLOT_RELEASE_WAIT_S = 1.0  # a readiness probe would occupy a max_connections slot, the property under test

# A fixed, recognizable DNS transaction ID, so a real answer from CaptiveDNS can be told
# apart from an echo of the query itself; the header prefix is _try_dns_query()'s own ">HH" unpack.
_DNS_QUERY_ID = 0x1234
_DNS_RESPONSE_HEADER_LEN = 4
_DNS_BIND_ERROR_TEXT = "Captive DNS socket could not bind port 53."  # asy_captive_dns.py's own error line

# The run names --only takes, in run_suite()'s order, and the run each consumes the state or result of.
RUN_NAMES = ("1", "2", "3", "4", "5", "5b", "5c", "6", "7", "8", "9", "10", "11", "11b", "12", "13")
_PRODUCERS = {"2": "1", "4": "3", "5b": "5", "7": "6", "8": "7", "9": "8"}
_USAGE_EXIT = 2

_FAILURES: list[str] = []
# Every check also lands in the SPECIFICATION.md E.10 summary block main() prints, named with its
# pass label; a pass that recorded no check at all is counted as having checked nothing.
_SUMMARY = Summary("scripts/_digital_twin_ci_suite.py", unit="checks")
_CHECKS_PER_PASS: dict[str, int] = {}


class Instance(NamedTuple):
    # One bus-attached instance the device wires: its --fault/--hang key, its driver and its TOML name_ext.
    key: str
    driver: str
    name_ext: str

    @property
    def errcount_name(self) -> str:
        base = _DRIVER_ERRCOUNT_NAME[self.driver]
        return f"{base}_{self.name_ext}" if self.name_ext else base


@dataclass(frozen=True)
class RunContext:
    # Everything one device's pass of this suite needs, computed once in main(): which Unix-port binary to launch,
    # which generated module/wiring-plan pair to boot and the instances that device wires (the fault matrix's rows).
    micropython_bin: str
    logs_dir: Path
    device: str
    module: str
    wiring_plan_path: Path
    instances: tuple[Instance, ...]
    gc_threshold: int  # every spawned run at it: the WHOLE suite passes at -1 before it runs again at 32768 (Part I.4(e))
    routes: tuple[str, ...]  # every GET route the device serves, from its API reference
    hostname: str = ""
    micropypath: str = TWIN_MICROPYPATH

    @property
    def runs_dir(self) -> Path:
        # Evidence a run keeps beside its log, outside the state archive: an errcount read before a ResetErrors clears it.
        return self.logs_dir / "runs"

    @property
    def state_dir(self) -> Path:
        # The pass's own persistent state, never digital_twin/'s manual defaults; _archive_state() is its one clearing point.
        return self.logs_dir / "state"


# Sharpened memory-safety discipline (CLAUDE.md, SPECIFICATION.md Part I.4(e), 2026-09-14): every
# OK/FAIL line is tagged with which gc.threshold() pass produced it, set once per run_suite() call,
# so no run function needs a per-message edit.
_CURRENT_PASS_LABEL = ""
# @tunable l2.ceiling_rounds = 3
_CEILING_ROUNDS = 3  # back-to-back, so a leaked slot or a pool that only fills over time shows up


_MEM_SAMPLE_LINE_FIELD_COUNT = 3  # "MEM_SAMPLE", the ticks_ms stamp, the byte count


@dataclass
class _SoakRun:
    # One boot's Run 11 raw results.

    http_failures: list[str]
    wdt_count: int | None
    shutdown_ec: int
    samples: list[int]
    trend_result: tuple[float, float, int, float, float] | None
    requests: int  # warm-up and measured cycles together


def _get_routes(reference: Path) -> tuple[str, ...]:
    # Every GET route of a device's API reference (buildgen/api_reference.py's output), in its order.
    document = json.loads(reference.read_text(encoding="utf-8"))
    routes = document.get("routes") if isinstance(document, dict) else None
    if not isinstance(routes, list) or not routes:
        raise ValueError(f"{reference} lists no routes")
    return tuple(str(r["path"]) for r in routes if isinstance(r, dict) and r.get("method") == "GET")


def _archive_state(ctx: RunContext, label: str) -> None:
    # The one clearing point: a non-empty state directory moves to state_archive/NN_before_<label>/ and an empty one
    # takes its place - nothing is deleted, so the FRAM image and logs of every earlier run stay readable.
    state = ctx.state_dir
    if state.exists() and any(state.iterdir()):
        archive = ctx.logs_dir / "state_archive"
        archive.mkdir(parents=True, exist_ok=True)
        number = sum(1 for _ in archive.iterdir()) + 1
        target = archive / f"{number:02d}_before_{label.replace(' ', '_')}"
        print(f"== Archiving {state} to {target}")
        state.rename(target)
    state.mkdir(parents=True, exist_ok=True)


def _boot_entries(table: dict[str, JSONObject]) -> list[tuple[str, JSONValue, JSONValue]]:
    # Every E and W slot of one errcount table as (module, type, num), in the table's order: what a boot logged.
    return [(name, kind, num) for name, entry in table.items() for kind, num in _error_codes(entry) if kind in ("E", "W")]


def _build_dns_query(query_id: int = _DNS_QUERY_ID, qname: str = "example.com") -> bytes:
    header = struct.pack(">HHHHHH", query_id, 0x0100, 1, 0, 0, 0)  # ID, flags(RD), QDCOUNT=1
    question = b"".join(bytes([len(part)]) + part.encode() for part in qname.split("."))
    question += b"\x00" + struct.pack(">HH", 1, 1)  # root label, QTYPE=A, QCLASS=IN
    return header + question


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--micropython-bin", required=True, help="path to the built MicroPython Unix-port binary")
    parser.add_argument("--device", required=True, help="which devices/<device>.toml-generated module to drive this suite against")
    parser.add_argument("--logs-dir", help="directory to write per-run subprocess logs and each pass's state into (default: digital_twin_ci_logs/<device>)")
    parser.add_argument("--only", type=_run_selection, help=f"run only these runs, comma-separated: {', '.join(RUN_NAMES)} (diagnosis)")
    parser.add_argument("--repeat", type=_positive_int, default=1, help="run the selection this many times per pass, each in fresh state (diagnosis)")
    parser.add_argument("--gc-threshold", type=int, choices=(-1, 32768), help="run only this GC stage's pass (default: -1, then 32768)")
    parser.add_argument("--device-toml", type=Path, help="generate this TOML's module into <logs-dir>/generated/ and boot that instead")
    return parser


def _check(*, condition: bool, msg: str) -> None:
    if not condition:
        _fail(msg)
    else:
        _record("passed", f"{_CURRENT_PASS_LABEL}{msg}")
        print(f"OK: {_CURRENT_PASS_LABEL}{msg}")


def _check_crc16_links(ctx: RunContext) -> None:
    # A --device-toml pass on a CRC16-derived TOML: the generated module builds every link bus with crc=CRC16().
    source = (ctx.wiring_plan_path.parent / f"{ctx.module}.py").read_text(encoding="utf-8")
    buses = [line.strip() for line in source.splitlines() if "= asy_uart_driver.UART(" in line]
    _check(condition=bool(buses) and all("crc=CRC16()" in line for line in buses), msg=f"Run 3: every link bus of the derived module is built with crc=CRC16() ({buses!r})")


def _check_exit(run: TwinRun, ec: int, run_label: str) -> None:
    # A negative exit the suite did not cause is a crash, reported as one with the log tail, beside the caller's check;
    # a stop file the twin never acted on fails too, though the SIGINT fallback then ended the run cleanly.
    if ec < 0 and not run.killed:
        _fail(f"{run_label}: {exit_reason(ec, killed=run.killed)}; last log lines:\n{log_tail(run)}")
    if run.stop_ignored:
        _fail(f"{run_label}: the twin never acted on its stop file, so only the SIGINT fallback ended it; last log lines:\n{log_tail(run)}")


def _check_no_memory_error_in_log(log_path: Path, run_label: str) -> None:
    # Part I.4(e) on every run's log, a caught-and-logged allocation failure included; fails closed on a
    # missing, empty or unreadable log, which gives no verdict at all.
    verdict = log_memory_verdict(log_path)
    _check(condition=verdict is None, msg=f"{run_label}: log carries none of {_MEMORY_ERROR_MARKERS}" + (f" - {verdict}" if verdict else ""))


def _check_quiet_boot(label: str, spawned_at: float, keep: Path, expected: "tuple[tuple[str, str, str], ...]" = ()) -> None:
    # One /status read, its errcount kept at keep, whose E and W slots are exactly expected ((module, type, catalog
    # name), no tolerance list); read before the boot's own first background warning can land (_quiet_boot_deadline_s()).
    status, body = _http("GET", "/status")
    age_s = time.monotonic() - spawned_at
    table = errcount_table(status, body)
    keep.parent.mkdir(parents=True, exist_ok=True)
    keep.write_text(json.dumps(table, indent=1) + "\n", encoding="utf-8")
    deadline_s = _quiet_boot_deadline_s()
    _check(condition=age_s < deadline_s, msg=f"{label}: the errcount was read {age_s:.1f}s after the spawn, before a boot's own first background warning can land ({deadline_s:.0f}s)")
    found = _boot_entries(table)
    wanted = [(name, kind, code(kind, entry)) for name, kind, entry in expected]
    named = "exactly " + ", ".join(f"{name}'s {kind} {entry}" for name, kind, entry in expected) if expected else "no E and no W entry"
    _check(condition=found == wanted, msg=f"{label}: the boot logged {named} (kept in {keep}: {found!r})")


def _check_run_log(run: TwinRun, run_label: str, *, starves_watchdog: bool) -> None:
    # Every launch's log: no memory marker; on its shutdown line, no public destination refused (product code leaving
    # the loopback and TEST-NET ranges) and no feed gap near the watchdog timeout, unless the run starves it on purpose.
    _check_no_memory_error_in_log(run.log_path, run_label)
    line = _shutdown_line(run.log_path, run_label)
    if line is not None:
        _check(condition=line.public_destinations_refused == 0, msg=f"{run_label}: no public destination was refused (public_destinations_refused={line.public_destinations_refused})")
        gap = feed_gap_verdict(line)
        if not starves_watchdog:
            _check(condition=gap is None, msg=f"{run_label}: no feed gap came near the watchdog timeout" + (f" - {gap}" if gap else f" (largest {line.largest_feed_gap_ms} ms of {line.wdt_timeout_ms} ms)"))


def _commanded_reset(ctx: RunContext, proc: TwinRun, cmd: str, label: str, expected_exit: int) -> int:
    # Sends one system command, expects "Valid", then the reset exit inside the controlled shutdown's deadline.
    try:
        word = _put_system_cmd(cmd)
        _check(condition=word == "Valid", msg=f"{label}: PUT /system {cmd} answered Valid ({word!r})")
    except Exception as exc:
        _fail(f"{label}: PUT /system {cmd}: {exc!r}")
    ec = _wait_exit(proc, label, timeout_s=_commanded_reset_deadline_s())
    _check(condition=ec == expected_exit, msg=f"{label}: {cmd} ended the process with {exit_reason(expected_exit)} within {_commanded_reset_deadline_s():.0f}s ({exit_reason(ec, killed=proc.killed)}, exit code {ec})")
    wdt = _would_have_triggered_count(proc.log_path, label)
    _check(condition=wdt == 0, msg=f"{label}: the watchdog never starved through {cmd}'s controlled shutdown (would_have_triggered_count={wdt!r})")
    del ctx
    return ec


def _commanded_reset_deadline_s() -> float:
    # A commanded reset runs the controlled shutdown (its first step may wait one supervisor period), then the delay.
    return _src_int("asy_system_service.py", "_RESET_DELAY") + _src_int("asy_system_service.py", "_TASK_CHECK_TIME") + _COMMANDED_RESET_MARGIN_S


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


def _config_files(ctx: RunContext) -> dict[str, str]:
    # The pass's config directory, file name to text: what the product wrote there.
    config_dir = state_paths(ctx.state_dir).config_dir
    return {p.name: p.read_text(errors="replace", encoding="utf-8") for p in sorted(config_dir.glob("config_*.cfg"))} if config_dir.exists() else {}


def _configured_max_connections(device: str) -> int:
    # The admission ceiling this tree builds for `device`, read by buildgen's own helper - so raising
    # a device's ceiling makes this run drive more concurrency instead of a stale literal.
    return device_max_connections_by_name(device)


def _count_verbose_log_lines(log_text: str) -> int:
    count = 0
    for line in log_text.splitlines():
        for prefix in _VERBOSE_LOG_PREFIXES:
            if line.startswith(prefix + " "):
                count += 1
                break
    return count


def _counter(entry: JSONValue) -> int:
    # An errcount entry's counter, or -1 for an entry or counter that is not there, which no assertion reads as 0.
    value = entry.get("counter") if isinstance(entry, dict) else None
    return value if isinstance(value, int) else -1


def _damage_config(ctx: RunContext) -> tuple[str, str]:
    # One file as bytes that are not JSON, one with a key out of range, one missing a key; returns the two whose
    # damage is a config fault (the missing key is a repair only), by their store names.
    config_dir = state_paths(ctx.state_dir).config_dir
    (config_dir / "config_NOTIFY.cfg").write_bytes(b"\xff not json {")
    system = json.loads((config_dir / "config_SYSTEM.cfg").read_text(encoding="utf-8"))
    system["DebugLevel"] = 99  # its schema admits 0-5
    (config_dir / "config_SYSTEM.cfg").write_text(json.dumps(system), encoding="utf-8")
    wifi = json.loads((config_dir / "config_WIFI.cfg").read_text(encoding="utf-8"))
    wifi.pop("Country")
    (config_dir / "config_WIFI.cfg").write_text(json.dumps(wifi), encoding="utf-8")
    return "NOTIFY", "SYSTEM"


def _describe_results(results: list[object]) -> list[object]:
    # Status and body type only: a full ceiling of /sensors bodies would bury which one failed.
    return [(r[0], type(r[1]).__name__) if isinstance(r, tuple) else r for r in results]


def _errcount(name: str) -> JSONObject:
    # TOLERANT: answers {} for a /status it could not parse, since the polling helpers call it in
    # a loop and a transient non-200 during boot must retry. Assertions take _errcount_required()
    # instead - {} reads as counter 0 - a split that makes the mistake unreachable.
    status, body = _http("GET", "/status")
    return errcount_entry(status, body, name)


def _errcount_all() -> dict[str, JSONObject]:
    # The whole errcount table from ONE /status read, for the sweeps that compare every registered source across a
    # reboot: a per-name loop could not tell a real loss from two reads straddling a fresh entry. Strict.
    status, body = _http("GET", "/status")
    return errcount_table(status, body)


def _errcount_required(name: str) -> JSONObject:
    # STRICT, for assertion sites: raises rather than returning {}, so an unreadable /status
    # becomes the caller's _fail() instead of a silent pass. Every registered source appears in
    # errcount whether or not it logged, so a missing entry is always a real failure.
    entry = _errcount(name)
    if not entry:
        raise RuntimeError(f"GET /status did not yield a readable errcount entry for {name!r} - the server answered nothing usable, so no assertion about its counter would mean anything")
    return entry


def _error_codes(entry: JSONObject) -> list[tuple[JSONValue, JSONValue]]:
    # The (type, num) of every non-empty history slot, in order, read strictly: a missing or malformed history raises.
    history = entry["history"]
    if not isinstance(history, list) or not all(isinstance(item, dict) for item in history):
        raise TypeError(f"the errcount history {history!r} is not a list of slots")
    return [(item["type"], item["num"]) for item in history if isinstance(item, dict) and item["type"] != "N"]


def _error_type_count(entry: JSONObject, type_char: str = "E") -> int:
    # entry["counter"] counts errors AND warnings in one history, and a "recovered after N
    # failures" notice is itself a "W" - so a recovery bumps it with no new failure. Counting one
    # type's entries is the real "did N of THIS happen" signal; WIFI's are "W", hence Run 8.
    history = entry.get("history")
    return sum(1 for item in (history if isinstance(history, list) else []) if isinstance(item, dict) and item.get("type") == type_char)


def _fail(msg: str) -> None:
    full_msg = f"{_CURRENT_PASS_LABEL}{msg}"
    _FAILURES.append(full_msg)
    _record("failed", full_msg)
    print(f"FAIL: {full_msg}", file=sys.stderr)


def _failure_events(entry: JSONObject) -> int:
    # asy_print_log.py's newest-entry rule folds a repeated code into one slot while "counter" counts every call,
    # so a failure is a counter step not backed by a "W" slot (exact while no warning repeats); -1 without a counter.
    return _counter(entry) - _error_type_count(entry, "W")


def _fault_instances(ctx: RunContext, table: "dict[str, str]") -> list[Instance]:
    # The device's instances whose driver `table` names, sorted by key. A driver absent from every table is caught
    # by the L0 matrix and catalog tests, never skipped here in silence.
    return [inst for inst in ctx.instances if inst.driver in table]


def _field(body: JSONValue, *keys: str) -> JSONValue:
    # The value at `keys` down an answer's nested objects, or None where a level is no object or lacks the key.
    node = body
    for key in keys:
        node = node.get(key) if isinstance(node, dict) else None
    return node


def _generate_from_toml(device_toml: Path, out_dir: Path) -> bool:
    # --device-toml: the TOML's module, plan and references generated into out_dir by the repo's own generator.
    out_dir.mkdir(parents=True, exist_ok=True)
    done = subprocess.run([sys.executable, str(GENERATOR), "--device-toml", str(device_toml), "--out-dir", str(out_dir)], cwd=REPO_ROOT, check=False)
    return done.returncode == 0


def _has_net_bind_capability(binary: str, getxattr: "Callable[[str, str], bytes]" = os.getxattr) -> bool:
    # The interpreter's file capability (the security.capability xattr getcap reads): CAP_NET_BIND_SERVICE permitted
    # and effective, which Run 7's captive DNS needs to bind port 53. A binary without the xattr has none.
    try:
        raw = getxattr(binary, "security.capability")
    except OSError:
        return False
    if len(raw) < struct.calcsize("<III"):
        return False
    magic, permitted, _inheritable = struct.unpack_from("<III", raw)
    return bool(magic & _VFS_CAP_FLAGS_EFFECTIVE) and bool(permitted & (1 << _CAP_NET_BIND_SERVICE))


def _healthy_store_fault_instances(ctx: RunContext) -> list[Instance]:
    # Run 5c's chain: every chip instance but the store itself, whose fault would void the chip-healthy premise.
    return _fault_instances(ctx, _BOUNDED_FAULT)


def _http(method: str, path: str, body: JSONObject | None = None, timeout: float = 5.0) -> tuple[int, JSONValue]:
    return twin_http(method, HOST, PORT, path, body, timeout_s=timeout)


def _link_crc_modes(device_toml: Path) -> list[str]:
    # The crc mode each uart_link instance of a TOML names ("none" when it names none).
    model = load_device(device_toml)
    return [str(spec.fields.get("crc", "none")) for spec in model.instances.values() if spec.driver == "uart_link"]


def _link_failures(before: JSONObject, after: JSONObject) -> int:
    # One process's own failures: a boot-time warning folded into an older slot before it cancels out.
    return _failure_events(after) - (_failure_events(before) if before else 0)


def _logs_dir(args: argparse.Namespace) -> Path:
    # --logs-dir, else the device's own directory, so two devices' runs never mix their logs or state.
    return Path(args.logs_dir) if args.logs_dir else REPO_ROOT / "digital_twin_ci_logs" / args.device


def _mem_paused() -> bool | None:
    # asy_system_service.py's own permanent-storage pause, as GET /status reports it. None means the
    # field wasn't readable at all, which is not the same answer as False.
    status, body = _http("GET", "/status")
    paused = _field(body, "system", "MemPaused") if status == _HTTP_OK else None
    return paused if isinstance(paused, bool) else None


def _mem_samples_from(log_path: Path, start: int) -> list[tuple[int, int]]:
    # The MEM_SAMPLE lines starting at or after byte offset start, each with its offset; [] for a missing log.
    try:
        with log_path.open("rb") as log:
            log.seek(start)
            return _parse_mem_samples(log.read(), base=start)
    except FileNotFoundError:
        return []


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


def _non_empty_slots(entry: JSONObject) -> list[tuple[JSONValue, JSONValue]]:
    history = entry.get("history")
    return [(item.get("type"), item.get("num")) for item in (history if isinstance(history, list) else []) if isinstance(item, dict) and item.get("type") != "N"]


def _ntp_unreachable_verdict(nums: list[JSONValue], *, route: bool) -> tuple[bool, str]:
    # Run 9's check: a request that leaves this host goes unanswered (NTP_NO_REPLY); with no route out the send
    # itself fails (NTP_NOT_SENT). Exactly the one the route predicts is logged, never the other.
    expected, other = ("NTP_NO_REPLY", "NTP_NOT_SENT") if route else ("NTP_NOT_SENT", "NTP_NO_REPLY")
    why = "a route to it leaves this host, so the request goes out unanswered" if route else "no route to it leaves this host, so the request is never sent"
    ok = code("E", expected) in nums and code("E", other) not in nums
    return ok, f"Run 9: NTP logged errno {code('E', expected)} ({expected}), not {other}, for {_NTP_UNREACHABLE_HOST}: {why} (history {nums})"


def _parse_mem_samples(log: bytes, base: int = 0) -> list[tuple[int, int]]:
    # The twin's _mem_sampler() lines as (byte offset of the line, free bytes), offsets counted from base; a malformed
    # line is skipped, and so is an unterminated last one, which the twin may still be writing.
    samples: list[tuple[int, int]] = []
    offset = base
    for line in log.splitlines(keepends=True):
        start, offset = offset, offset + len(line)
        parts = line.split()
        if not line.endswith(b"\n") or len(parts) != _MEM_SAMPLE_LINE_FIELD_COUNT or parts[0] != b"MEM_SAMPLE":
            continue
        try:
            int(parts[1])  # the sampler's ticks_ms stamp, diagnostics only: no clock enters the window
            samples.append((start, int(parts[2])))
        except ValueError:
            continue
    return samples


def _plan_instances(device_toml: Path) -> tuple[Instance, ...]:
    # Every bus-attached instance the device TOML declares, by its fault key, read by buildgen's own loader.
    model = load_device(device_toml)
    found = [Instance(instance_label(spec.key), spec.driver, spec.name_ext) for spec in model.instances.values() if spec.driver in BUS_ATTACHED_DRIVERS]
    return tuple(sorted(found))


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {value}")
    return value


def _put_reset_errors_timed(run_label: str) -> int:
    # The one request with a real elapsed-time budget (_RESET_ERRORS_BUDGET_S above). Returns the
    # HTTP status so callers keep asserting that themselves; the budget and the answer word are checked
    # here, so both call sites get them: "Failed" is a store whose cleared state was not written.
    started = time.monotonic()
    status, body = _http("PUT", "/status", {"ResetErrors": True}, timeout=_RESET_ERRORS_TIMEOUT_S)
    elapsed = time.monotonic() - started
    _check(
        condition=elapsed < _RESET_ERRORS_BUDGET_S,
        msg=f"{run_label}: the ResetErrors sweep finished inside its {_RESET_ERRORS_BUDGET_S:.1f}s budget ({elapsed:.2f}s, {elapsed / _SERVER_OUTER_CAP_S * 100:.0f}% of the server's own {_SERVER_OUTER_CAP_S:.1f}s cap)",
    )
    result = body.get("result") if isinstance(body, dict) else None
    word = result.get("ResetErrors") if isinstance(result, dict) else None
    _check(condition=word == "Valid", msg=f"{run_label}: PUT /status ResetErrors answered Valid, every log's cleared state written ({word!r})")
    return status


def _put_system_cmd(cmd: JSONValue) -> str | None:
    # A system command's answer word, or None for a reply that carried none.
    status, body = _http("PUT", "/system", {"SystemCmd": cmd})
    if status != _HTTP_OK or not isinstance(body, dict):
        return None
    result = body.get("result")
    word = result.get("SystemCmd") if isinstance(result, dict) else None
    return word if isinstance(word, str) else None


def _quiet_boot_deadline_s() -> float:
    # A boot's own first error-count move, SGP40's untimestamped-backup warning, comes no earlier than the scenarios'
    # shared-boot deadline after the spawn; one source for both readers of that background.
    return module_float_const(REPO_ROOT / "scripts", "_digital_twin_scenarios.py", "_SHARED_BOOT_DEADLINE_S")


def _real_reading(reading: object) -> bool:
    # A measurement that carries a value: a driver's fields stay null until its first good read, so an all-null
    # block is no reading at all, however truthy the dict holding it.
    return isinstance(reading, dict) and any(value is not None for key, value in reading.items() if key != "TS")


def _record(kind: str, full_msg: str) -> None:
    _SUMMARY.add(kind, full_msg)
    _CHECKS_PER_PASS[_CURRENT_PASS_LABEL] = _CHECKS_PER_PASS.get(_CURRENT_PASS_LABEL, 0) + 1


def _relaunch_reason(ctx: RunContext, log_name: str, label: str, expected: int, *, system_entry: str | None = None, interrupt: bool = False) -> None:
    # Boots on the same state and checks the reset reason the product read at boot (and, given its catalog name, the one
    # SYSTEM entry that reset logged), then shuts down on its stop file, or by SIGINT with interrupt=True.
    proc = _spawn(ctx, [], ctx.logs_dir / log_name)
    try:
        _wait_until_serving(proc)
        reason = _status_field("system", "ResetReason")
        _check(condition=reason == expected, msg=f"{label}: ResetReason reads {expected} ({reason!r})")
        if system_entry is not None:
            codes = _error_codes(_errcount_required("SYSTEM"))
            _check(condition=codes.count(("E", code("E", system_entry))) == 1, msg=f"{label}: SYSTEM's history holds one {system_entry} entry ({codes!r})")
    except Exception as exc:
        _fail(f"{label}: {exc!r}")
    finally:
        ec = _shutdown(proc, label, interrupt=interrupt)
        _check(condition=ec == 0, msg=f"{label}: clean shutdown (exit code {ec})")


def _reset_code(name: str) -> int:
    return _src_int("asy_system_service.py", name)


def _restore_is_all_or_nothing(written: JSONObject, restored: JSONObject) -> bool:
    # Whole: the written ring and at least its count came back, newer slots only after it (this boot's
    # own). Nothing: no "E" slot survived, only what this boot logged itself. Else partial or garbled.
    slots, kept = _non_empty_slots(restored), _non_empty_slots(written)
    whole = slots[: len(kept)] == kept and all(kind != "E" for kind, _ in slots[len(kept) :]) and _counter(restored) >= max(_counter(written), 0)
    return whole or all(kind != "E" for kind, _ in slots)


def _route_leaves_host(host: str, port: int) -> bool:
    # A UDP connect() sends nothing: it is the route lookup the twin's own UDPSocket makes on this same host, and
    # it fails (ENETUNREACH) where no route leaves - a network namespace holding only lo, for one.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect((host, port))
        except OSError:
            return False
    return True


def _run_10_watchdog_hang_backstop(ctx: RunContext) -> None:
    # ---- Run 10: one real blocking sleep per instance (_HANG_MATRIX), each in a fresh process, freezing the interpreter
    # past the WDT window to prove the simulated backstop engages, which Run 3's raised errors cannot. A run ends on the
    # runner's WATCHDOG_WOULD_TRIGGER line; --duration 15 bounds one whose hang fires late, behind startup I/O. ----
    for inst in _fault_instances(ctx, _HANG_MATRIX):
        _archive_state(ctx, f"run10 {inst.key}")
        label = f"Run 10 ({inst.key})"
        log10 = ctx.logs_dir / f"run10_watchdog_hang_backstop_{inst.key}.log"
        proc = _spawn(ctx, ["--hang", f"{inst.key}:{_HANG_MATRIX[inst.driver]}:12", "--duration", "15"], log10)
        deadline = time.monotonic() + _HANG_RUN_EXIT_WAIT_S
        engaged = _wait_for_log_line(proc, "WATCHDOG_WOULD_TRIGGER", _HANG_RUN_EXIT_WAIT_S)
        remaining = max(0.0, deadline - time.monotonic())
        ec = _shutdown(proc, label, starves_watchdog=True) if engaged else _wait_exit(proc, label, timeout_s=remaining, starves_watchdog=True)
        _check(condition=ec == 0, msg=f"{label}: process survived a genuinely wedged bus and exited cleanly (exit code {ec})")
        wdt10 = _would_have_triggered_count(log10, label)
        _check(condition=wdt10 is not None and wdt10 >= 1, msg=f"{label}: the watchdog backstop actually engaged for a genuinely wedged bus (would_have_triggered_count={wdt10!r})")


def _run_11_soak(ctx: RunContext) -> None:
    # One boot, one verdict: a second boot never covers this one's failing trend (owner, 2026-09-26:
    # 'A retry or a longer timeout never counts as a race fix'). The self-calibrated tolerance is
    # what separates a leak from a noisy reactive-GC heap sampled on a timer.
    run = _run_11_soak_boot(ctx, ctx.logs_dir / "run11_soak.log")
    for failure in run.http_failures:
        print(f"FAIL: Run 11: {failure}")
    _check(condition=not run.http_failures, msg=f"Run 11: {run.requests} soak requests across every endpoint produced zero HTTP failures ({len(run.http_failures)} found)")
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


def _run_11_soak_boot(ctx: RunContext, log_path: Path) -> _SoakRun:
    # ---- Run 11: a fresh clean boot for the soak check, driven entirely from THIS process like the other runs
    # ("Driver/DUT process separation"); gc.mem_free(), the one value that cannot move host-side, is armed via
    # --mem-sample-interval-ms and read back from the captured log, at ctx.gc_threshold like every other run. ----
    _archive_state(ctx, "run11")
    proc = _spawn(ctx, ["--mem-sample-interval-ms", str(_MEM_SAMPLE_INTERVAL_MS)], log_path)
    endpoints = (*ctx.routes, "/")
    http_failures: list[str] = []
    warmed = 0
    window: tuple[int, int] | None = None  # the cycles' span of the log, in bytes: file order is emission order
    try:
        _wait_until_serving(proc)
        warmed = _soak_warm_up(log_path, endpoints, http_failures)
        cycles_start = log_path.stat().st_size
        for cycle in range(_SOAK_CYCLES):
            for path in endpoints:
                try:
                    status, _ = _http("GET", path)
                except (OSError, http.client.HTTPException) as e:
                    http_failures.append(f"cycle {cycle}: GET {path} -> {e!r}")
                    continue
                if status != _HTTP_OK:
                    http_failures.append(f"cycle {cycle}: GET {path} -> {status}")
        window = (cycles_start, log_path.stat().st_size)
    except Exception as exc:  # CI orchestration: surface any failure as a suite failure, not a crash
        http_failures.append(repr(exc))
    finally:
        ec = _shutdown(proc, "Run 11")

    wdt_count = _would_have_triggered_count(log_path, "Run 11")
    samples: list[int] = []
    trend_result = None
    if window is not None:
        samples = [free for offset, free in _mem_samples_from(log_path, window[0]) if offset < window[1]]
        if len(samples) // 4 >= 1:
            trend_result = _mem_trend(samples)
    return _SoakRun(http_failures=http_failures, wdt_count=wdt_count, shutdown_ec=ec, samples=samples, trend_result=trend_result, requests=(warmed + _SOAK_CYCLES) * len(endpoints))


def _run_11b_full_ceiling_concurrency(ctx: RunContext) -> None:
    # ---- Run 11b: the admission ceiling under real simultaneous load, driven from THIS process: a
    # client sharing the DUT's heap measures its own buffers, not the firmware's (Part E.9; an
    # in-process attempt proved it, HEAP_FRAGMENTATION_MEASUREMENTS.md archive §9). ----
    _archive_state(ctx, "run11b")
    try:  # a ceiling that cannot be read fails this run, never the whole suite and its later passes
        ceiling = _configured_max_connections(ctx.device)
    except Exception as exc:  # CI orchestration, the same as this run's own catch below
        _fail(f"Run 11b (full-ceiling concurrency): cannot read the device's ceiling: {exc!r}")
        return
    log11b = ctx.logs_dir / "run11b_full_ceiling_concurrency.log"
    proc = _spawn(ctx, [], log11b)
    try:
        _wait_until_serving(proc)
        endpoints = ctx.routes  # every GET route the device serves, the streaming /sensors and /status among them (Part I.3)
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


def _run_12_reset_reasons(ctx: RunContext) -> None:
    # ---- Run 12: the reset reasons reachable at L2. A fresh boot reads power-on; bootloader exits as a bootloader entry,
    # its relaunch reads its code and clears the record; a SIGINT relaunch reads power-on; a C-stack overflow reboots with
    # 20. The task budget's escalation is Run 4's, the REST reboot Run 5c's, 7 and 8 Run 13's. ----
    _archive_state(ctx, "run12")
    proc = _spawn(ctx, [], ctx.logs_dir / "run12_a_power_on_then_bootloader.log")
    try:
        _wait_until_serving(proc)
        reason = _status_field("system", "ResetReason")
        _check(condition=reason == _reset_code("_RR_POWER_ON"), msg=f"Run 12: a fresh boot reads the power-on code {_reset_code('_RR_POWER_ON')} ({reason!r})")
    except Exception as exc:
        _fail(f"Run 12 (power-on): {exc!r}")
    _commanded_reset(ctx, proc, "bootloader", "Run 12 (bootloader)", EXIT_SIMULATED_BOOTLOADER)
    reset = parse_machine_reset_line(read_log(proc.log_path))
    _check(condition=reset is not None and reset.kind == "bootloader", msg=f"Run 12: the runner's machine reset line names the bootloader entry ({reset!r})")
    log_b = ctx.logs_dir / "run12_b_after_bootloader.log"
    _relaunch_reason(ctx, log_b.name, "Run 12 (after bootloader)", _reset_code("_RR_BOOTLOADER"), interrupt=True)  # what the SIGINT relaunch follows
    line = _shutdown_line(log_b, "Run 12 (after bootloader)")
    _check(condition=line is not None and line.mem_backup_r0 == (0, 0, 0, 0), msg=f"Run 12: the boot that read the bootloader record cleared it (mem_backup r0 {line.mem_backup_r0 if line else None!r})")
    _relaunch_reason(ctx, "run12_c_sigint_relaunch.log", "Run 12 (SIGINT relaunch)", _reset_code("_RR_POWER_ON"))
    _run_12_stack_exhaustion(ctx)


def _run_12_stack_exhaustion(ctx: RunContext) -> None:
    # A C-stack overflow raised in one read of the plan's first bus device: the handler that catches it records it, the
    # supervisor reboots at its next pass with the watchdog fed, and the relaunch reads code 20 and SYSTEM's one entry.
    inst = _stack_fault_instance(json.loads(ctx.wiring_plan_path.read_text(encoding="utf-8")))
    if inst is None:
        _SUMMARY.add("skipped", f"{_CURRENT_PASS_LABEL}Run 12 (stack exhaustion)", f"{ctx.device} wires no bus driver")
        return
    label = f"Run 12 (stack exhaustion in {inst.key})"
    proc = _spawn(ctx, ["--fault", f"{inst.key}:{_STACK_FAULT_READ_OP[inst.driver]}:stack"], ctx.logs_dir / "run12_d_stack_exhaustion.log")
    ec = _wait_exit(proc, label, timeout_s=_ESCALATION_WAIT_S)
    _check(condition=ec == EXIT_SIMULATED_RESET, msg=f"{label}: the supervisor reset the device ({exit_reason(ec, killed=proc.killed)}, exit code {ec})")
    wdt = _would_have_triggered_count(proc.log_path, label)
    _check(condition=wdt == 0, msg=f"{label}: the watchdog never starved before the reset (would_have_triggered_count={wdt!r})")
    _relaunch_reason(ctx, "run12_e_after_stack_exhaustion.log", f"{label} relaunch", _reset_code("_RR_STACK_EXHAUSTED"), system_entry="STACK_EXHAUSTED")


def _run_13_config_reset(ctx: RunContext) -> dict[str, str]:
    # resetconfig: every config file is deleted unread, the relaunch writes each at its defaults, Hostname is the
    # TOML's, reason 7; returns the defaults the first fresh boot wrote, which the damaged-file cell compares with.
    _archive_state(ctx, "run13 resetconfig")
    proc = _spawn(ctx, [], ctx.logs_dir / "run13_a_resetconfig.log")
    defaults: dict[str, str] = {}
    try:
        _wait_until_serving(proc)
        defaults = _config_files(ctx)
        status, _ = _http("PUT", "/networking", {"Hostname": "ci-before-reset"})
        _check(condition=status == _HTTP_OK and bool(defaults), msg=f"Run 13: a fresh boot wrote its config files and took a Hostname change ({sorted(defaults)!r})")
    except Exception as exc:
        _fail(f"Run 13 (resetconfig setup): {exc!r}")
    _commanded_reset(ctx, proc, "resetconfig", "Run 13 (resetconfig)", EXIT_SIMULATED_RESET)
    left = _config_files(ctx)
    _check(condition=not left, msg=f"Run 13: resetconfig left no config_*.cfg in the run's config directory ({sorted(left)!r})")
    proc = _spawn(ctx, [], ctx.logs_dir / "run13_b_after_resetconfig.log")
    try:
        _wait_until_serving(proc)
        reason = _status_field("system", "ResetReason")
        _check(condition=reason == _reset_code("_RR_CONFIG_RESET"), msg=f"Run 13: ResetReason reads the config-reset code {_reset_code('_RR_CONFIG_RESET')} ({reason!r})")
        status, body = _http("GET", "/networking")
        _check(condition=status == _HTTP_OK and _field(body, "Hostname") == ctx.hostname, msg=f"Run 13: Hostname is the TOML's {ctx.hostname!r} again ({_field(body, 'Hostname')!r})")
        faults = _status_field("system", "ConfigFaults")
        _check(condition=faults == [], msg=f"Run 13: ConfigFaults is empty after resetconfig ({faults!r})")
        rewritten = _config_files(ctx)
        _check(condition=rewritten == defaults, msg=f"Run 13: the relaunch wrote every config file at its defaults, the same set a fresh boot writes ({sorted(rewritten)!r})")
    except Exception as exc:
        _fail(f"Run 13 (after resetconfig): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 13 (after resetconfig)")
        _check(condition=ec == 0, msg=f"Run 13 (after resetconfig): clean shutdown (exit code {ec})")
    return defaults


def _run_13_damaged_config(ctx: RunContext, defaults: dict[str, str]) -> None:
    # A launch over damaged files lists the two faults (the missing key is a repair only) and rewrites all three at
    # their defaults; resetconfig then deletes every file unread and the relaunch shows no fault.
    faulty = _damage_config(ctx)
    proc = _spawn(ctx, [], ctx.logs_dir / "run13_c_damaged_config.log")
    try:
        _wait_until_serving(proc)
        faults = _status_field("system", "ConfigFaults")
        _check(condition=sorted(faults) == sorted(faulty) if isinstance(faults, list) else False, msg=f"Run 13: ConfigFaults names the unparseable and the out-of-range file only, never the missing key's ({faults!r})")
        repaired = _config_files(ctx)
        _check(condition=repaired == defaults, msg=f"Run 13: the boot rewrote the three damaged files at their defaults ({sorted(k for k in repaired if repaired.get(k) != defaults.get(k))!r} differ)")
    except Exception as exc:
        _fail(f"Run 13 (damaged config): {exc!r}")
    _commanded_reset(ctx, proc, "resetconfig", "Run 13 (resetconfig over faults)", EXIT_SIMULATED_RESET)
    proc = _spawn(ctx, [], ctx.logs_dir / "run13_d_after_second_resetconfig.log")
    try:
        _wait_until_serving(proc)
        faults = _status_field("system", "ConfigFaults")
        _check(condition=faults == [] and _config_files(ctx) == defaults, msg=f"Run 13: after resetconfig the relaunch shows no config fault and every file at its defaults ({faults!r})")
    except Exception as exc:
        _fail(f"Run 13 (after the second resetconfig): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 13 (after the second resetconfig)")
        _check(condition=ec == 0, msg=f"Run 13 (after the second resetconfig): clean shutdown (exit code {ec})")


def _run_13_erase_fram(ctx: RunContext) -> None:
    # erasefram: FRAM evidence saved first (CLAUDE.md's FRAM-log rule, the twin case), then every FRAM-backed
    # counter reads 0 on the relaunch and the reason is 8. One bounded fault on the first chip plants the entry it clears.
    _archive_state(ctx, "run13 erasefram")
    chips = _healthy_store_fault_instances(ctx)
    if not chips:
        _fail(f"Run 13 (erasefram setup): {ctx.device} wires no chip to plant the erase's entry on")
        return
    chip, fault = chips[0], f"{chips[0].key}:{_BOUNDED_FAULT[chips[0].driver]}:1"
    proc = _spawn(ctx, ["--fault", fault], ctx.logs_dir / "run13_e_erasefram.log")
    try:
        _wait_until_serving(proc)
        entry = _wait_for_error_type_count(chip.errcount_name, 1, timeout_s=_FIRST_FAULT_WAIT_S, run=proc)
        _check(condition=_error_type_count(entry) >= 1 and _counter(entry) > 0, msg=f"Run 13: the planted {fault} logged {chip.errcount_name}'s own entry for the erase to clear within {_FIRST_FAULT_WAIT_S:.0f}s ({entry!r})")
        _save_fram_evidence(ctx, "run13 erasefram")
    except Exception as exc:
        _fail(f"Run 13 (erasefram setup): {exc!r}")
    _commanded_reset(ctx, proc, "erasefram", "Run 13 (erasefram)", EXIT_SIMULATED_RESET)
    proc = _spawn(ctx, [], ctx.logs_dir / "run13_f_after_erasefram.log")
    try:
        _wait_until_serving(proc)
        reason = _status_field("system", "ResetReason")
        _check(condition=reason == _reset_code("_RR_FRAM_ERASED"), msg=f"Run 13: ResetReason reads the FRAM-erase code {_reset_code('_RR_FRAM_ERASED')} ({reason!r})")
        after = _errcount_all()
        kept = {name: entry.get("counter", -1) for name, entry in after.items() if name not in _IN_MEMORY_ONLY_ERROR_SOURCES and entry.get("counter", -1) != 0}
        _check(condition=not kept, msg=f"Run 13: every FRAM-backed error count reads 0 after erasefram ({kept!r} did not)")
    except Exception as exc:
        _fail(f"Run 13 (after erasefram): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 13 (after erasefram)")
        _check(condition=ec == 0, msg=f"Run 13 (after erasefram): clean shutdown (exit code {ec})")


def _run_13_near_misses(ctx: RunContext) -> None:
    # Every near miss of a command word answers Invalid and the device keeps serving: its uptime still rises.
    _archive_state(ctx, "run13 near misses")
    proc = _spawn(ctx, [], ctx.logs_dir / "run13_i_near_misses.log")
    try:
        _wait_until_serving(proc)
        started = _status_field("system", "SysUptime")
        answers = {repr(cmd): _put_system_cmd(cmd) for cmd in (*_SYSTEM_CMD_NEAR_MISSES, 1)}
        _check(condition=all(word == "Invalid" for word in answers.values()), msg=f"Run 13: every near miss of a command word answered Invalid ({answers!r})")
        deadline = time.monotonic() + _ERROR_COUNT_WAIT_S
        uptime = started
        while uptime == started and time.monotonic() < deadline:
            time.sleep(_ERRCOUNT_POLL_S)
            uptime = _status_field("system", "SysUptime")
        _check(condition=isinstance(uptime, int) and isinstance(started, int) and uptime > started, msg=f"Run 13: the device kept serving after the near misses (SysUptime {started!r} -> {uptime!r})")
    except Exception as exc:
        _fail(f"Run 13 (near misses): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 13 (near misses)")
        _check(condition=ec == 0, msg=f"Run 13 (near misses): clean shutdown (exit code {ec})")
    wdt = _would_have_triggered_count(proc.log_path, "Run 13 (near misses)")
    _check(condition=wdt == 0, msg=f"Run 13 (near misses): the watchdog never starved (would_have_triggered_count={wdt!r})")


def _run_13_reboot_sequence(ctx: RunContext, cmd: str, expected_exit: int, reason_name: str) -> None:
    # reboot or bootloader at the event log level: the S1-S4 step lines in order and no S5, the reset line, then a
    # relaunch keeping DebugLevel (a reboot deletes nothing) and every FRAM history a superset of its pre-command one.
    _archive_state(ctx, f"run13 {cmd}")
    label = f"Run 13 ({cmd})"
    proc = _spawn(ctx, [], ctx.logs_dir / f"run13_g_{cmd}.log")
    level = _src_int("asy_print_log.py", "_LOG_EVENT")
    before: dict[str, JSONObject] = {}
    try:
        _wait_until_serving(proc)
        status, _ = _http("PUT", "/system", {"DebugLevel": level})
        _check(condition=status == _HTTP_OK, msg=f"{label}: PUT /system DebugLevel={level} accepted, so the step lines print")
        before = _errcount_all()
    except Exception as exc:
        _fail(f"{label} setup: {exc!r}")
    _commanded_reset(ctx, proc, cmd, label, expected_exit)
    log_text = read_log(proc.log_path)
    steps = _shutdown_step_lines(log_text)
    _check(condition=steps == list(_SHUTDOWN_STEP_LINES), msg=f"{label}: the run log shows the four step lines S1-S4 in order and no S5 ({steps!r})")
    reset = parse_machine_reset_line(log_text)
    kind = "bootloader" if expected_exit == EXIT_SIMULATED_BOOTLOADER else "reset"
    _check(condition=reset is not None and reset.kind == kind, msg=f"{label}: the runner's machine reset line names kind={kind} ({reset!r})")
    proc = _spawn(ctx, [], ctx.logs_dir / f"run13_h_after_{cmd}.log")
    try:
        _wait_until_serving(proc)
        reason = _status_field("system", "ResetReason")
        _check(condition=reason == _reset_code(reason_name), msg=f"{label}: the relaunch reads ResetReason {_reset_code(reason_name)} ({reason!r})")
        status, body = _http("GET", "/system")
        _check(condition=status == _HTTP_OK and _field(body, "DebugLevel") == level, msg=f"{label}: DebugLevel {level} survived the {cmd} ({body!r})")
        after = _errcount_all()
        lost = [name for name, entry in before.items() if name not in _IN_MEMORY_ONLY_ERROR_SOURCES and _non_empty_slots(after.get(name, {}))[: len(_non_empty_slots(entry))] != _non_empty_slots(entry)]
        _check(condition=not lost, msg=f"{label}: every FRAM-backed history came back a superset of its pre-command one ({lost!r} did not)")
    except Exception as exc:
        _fail(f"{label} relaunch: {exc!r}")
    finally:
        ec = _shutdown(proc, f"{label} relaunch")
        _check(condition=ec == 0, msg=f"{label} relaunch: clean shutdown (exit code {ec})")


def _run_13_system_commands(ctx: RunContext) -> None:
    # ---- Run 13: the system commands end to end, each cell in fresh state: resetconfig (and over damaged files),
    # erasefram, the near misses, reboot and bootloader through the controlled shutdown. The command states and the
    # hang per step are the scenario harness's. ----
    defaults = _run_13_config_reset(ctx)
    if defaults:
        _run_13_damaged_config(ctx, defaults)
    _run_13_erase_fram(ctx)
    _run_13_near_misses(ctx)
    _run_13_reboot_sequence(ctx, "reboot", EXIT_SIMULATED_RESET, "_RR_REBOOT")
    _run_13_reboot_sequence(ctx, "bootloader", EXIT_SIMULATED_BOOTLOADER, "_RR_BOOTLOADER")


def _run_1_baseline(ctx: RunContext) -> None:
    # ---- Run 1: fresh boot, walk every GET endpoint, and nothing logged (kept in runs/ before the reset). With no
    # station link yet the device has never synced its clock, so both time fields read null. Its reformat relaunch
    # PUTs the settings later runs carry forward. ----
    log1 = ctx.logs_dir / "run1_baseline.log"
    spawned_at = time.monotonic()
    proc = _spawn(ctx, [], log1)
    try:
        _wait_until_serving(proc)
        for path in (*ctx.routes, "/"):
            status, _ = _http("GET", path)
            _check(condition=status == _HTTP_OK, msg=f"Run 1: GET {path} -> 200")
        _check_quiet_boot("Run 1", spawned_at, ctx.runs_dir / "run1_errcount.json")
        times = (_status_field("system", "UTCTime"), _status_field("system", "LocalTime"))
        _check(condition=times == (None, None), msg=f"Run 1: UTCTime and LocalTime are null before the first NTP sync ({times!r})")

        status = _put_reset_errors_timed("Run 1")
        _check(condition=status == _HTTP_OK, msg="Run 1: PUT /status ResetErrors accepted")
    except Exception as exc:  # CI orchestration: surface any failure as a suite failure, not a crash
        _fail(f"Run 1 (baseline boot): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 1")
        _check(condition=ec == 0, msg=f"Run 1: clean shutdown (exit code {ec})")
    paths = state_paths(ctx.state_dir)
    _check(condition=paths.fram.exists() and paths.scd30.exists(), msg="Run 1: FRAM/SCD30 state files were persisted to disk on shutdown")
    _run_1_reformat_relaunch(ctx)


def _run_1_reformat_relaunch(ctx: RunContext) -> None:
    # Run 1's second boot on an emptied config directory beside the kept FRAM state, as a reformatted filesystem leaves
    # a unit: SYSTEM logs exactly one W CONFIG_LOST (kept in runs/ before the reset), then the settings Run 2 reads are PUT.
    label = "Run 1 (reformat relaunch)"
    config_dir = state_paths(ctx.state_dir).config_dir
    try:
        shutil.rmtree(config_dir)
        config_dir.mkdir()
    except OSError as exc:
        _fail(f"{label}: emptying {config_dir} failed: {exc!r}")
        return
    spawned_at = time.monotonic()
    proc = _spawn(ctx, [], ctx.logs_dir / "run1_reformat_relaunch.log")
    try:
        _wait_until_serving(proc)
        _check_quiet_boot(label, spawned_at, ctx.runs_dir / "run1_reformat_errcount.json", (("SYSTEM", "W", "CONFIG_LOST"),))

        status, body = _http("PUT", "/system", {"DebugLevel": _TEST_DEBUG_LEVEL})
        _check(condition=status == _HTTP_OK and _field(body, "result", "DebugLevel") in ("Valid", "Unchanged"), msg=f"Run 1: PUT /system DebugLevel={_TEST_DEBUG_LEVEL} accepted")
        status, body = _http("GET", "/system")
        _check(condition=status == _HTTP_OK and _field(body, "DebugLevel") == _TEST_DEBUG_LEVEL, msg=f"Run 1: GET /system reflects DebugLevel={_TEST_DEBUG_LEVEL} immediately")

        status, body = _http("PUT", "/notification", {"WarnCO2": _TEST_WARN_CO2})
        _check(condition=status == _HTTP_OK and _field(body, "result", "WarnCO2") in ("Valid", "Unchanged"), msg=f"Run 1: PUT /notification WarnCO2={_TEST_WARN_CO2} accepted")

        status, body = _http("PUT", "/sensors", {"SCD30": {"MeasInterval": _TEST_SCD30_MEAS_INT}})
        _check(condition=status == _HTTP_OK and _field(body, "result", "SCD30", "MeasInterval") in ("Valid", "Unchanged"), msg=f"Run 1: PUT /sensors SCD30.MeasInterval={_TEST_SCD30_MEAS_INT} accepted")

        status, body = _http("PUT", "/networking", {"Hostname": "ci-digital-twin"})
        _check(condition=status == _HTTP_OK and _field(body, "result", "Hostname") in ("Valid", "Unchanged"), msg="Run 1: PUT /networking Hostname accepted")

        status = _put_reset_errors_timed(label)
        _check(condition=status == _HTTP_OK, msg=f"{label}: PUT /status ResetErrors accepted")
    except Exception as exc:  # CI orchestration: surface any failure as a suite failure, not a crash
        _fail(f"{label} + settings: {exc!r}")
    finally:
        ec = _shutdown(proc, label)
        _check(condition=ec == 0, msg=f"{label}: clean shutdown (exit code {ec})")


def _run_2_reboot_settings_persistence(ctx: RunContext) -> None:
    # ---- Run 2: reboot from persisted state - verbose logging from boot, settings survived. ----
    log2 = ctx.logs_dir / "run2_reboot_settings_persistence.log"
    proc = _spawn(ctx, [], log2)
    verbose_lines = 0
    try:
        _wait_until_serving(proc)
        status, body = _http("GET", "/system")
        _check(condition=status == _HTTP_OK and _field(body, "DebugLevel") == _TEST_DEBUG_LEVEL, msg=f"Run 2: DebugLevel={_TEST_DEBUG_LEVEL} survived a real process restart (persistence of settings)")
        status, body = _http("GET", "/notification")
        _check(condition=status == _HTTP_OK and _field(body, "WarnCO2") == _TEST_WARN_CO2, msg="Run 2: WarnCO2 survived a real process restart")
        status, body = _http("GET", "/sensors")
        _check(condition=status == _HTTP_OK and _field(body, "SCD30", "MeasInterval") == _TEST_SCD30_MEAS_INT, msg="Run 2: SCD30 MeasInterval survived a real process restart")
        status, body = _http("GET", "/networking")
        _check(condition=status == _HTTP_OK and _field(body, "Hostname") == "ci-digital-twin", msg="Run 2: Hostname survived a real process restart")
        verbose_lines = _wait_for_verbose_lines(log2, _MIN_VERBOSE_LOG_LINES, _ERROR_COUNT_WAIT_S)  # the value is in the log
    except Exception as exc:
        _fail(f"Run 2 (reboot + settings persistence): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 2")
        _check(condition=ec == 0, msg=f"Run 2: clean shutdown (exit code {ec})")
    _check(condition=verbose_lines >= _MIN_VERBOSE_LOG_LINES, msg=f"Run 2: bootup produced verbose (DebugLevel={_TEST_DEBUG_LEVEL}) log output from multiple modules ({verbose_lines} matching lines)")


def _run_3_sustained_bus_fault_matrix(ctx: RunContext) -> None:
    # ---- Run 3: the combined-fault escalation cell. Every instance this device wires boots with its sustained fault
    # (_SUSTAINED_FAULT); each faulted module records a real error while the process lives, then the supervisor's
    # restart budget runs out and the device resets itself - a simulated reset, never a crash or a starved watchdog. ----
    log3 = ctx.logs_dir / "run3_sustained_bus_fault_matrix.log"
    faulted = _fault_instances(ctx, _SUSTAINED_FAULT)
    fault_args: list[str] = []
    for inst in faulted:
        op = _SUSTAINED_FAULT[inst.driver]
        fault_args += ["--fault", f"{inst.key}:{op}" if op == "silent" else f"{inst.key}:{op}:{_BUS_FAULT_ERROR_COUNT}"]
    started = time.monotonic()
    proc = _spawn(ctx, fault_args, log3)
    seen: dict[str, JSONObject] = {}
    ec = -1
    try:
        _wait_until_serving(proc)
        # Keyed on "E" entries, never the raw counter a "W" recovery notice also bumps; each poll stops at the reset.
        for inst in faulted:
            seen[inst.errcount_name] = _wait_for_error_type_count(inst.errcount_name, 1, timeout_s=_FIRST_FAULT_WAIT_S, run=proc)
        for name, entry in seen.items():
            _check(condition=_error_type_count(entry) > 0, msg=f"Run 3: {name}'s injected sustained fault was recorded as a real error while the process lived ({entry!r})")
    except Exception as exc:
        _fail(f"Run 3 (sustained bus-fault matrix): {exc!r}")
    finally:
        ec = _wait_exit(proc, "Run 3", timeout_s=_ESCALATION_WAIT_S)
    window_ms = (time.monotonic() - started) * 1000
    _check(condition=ec == EXIT_SIMULATED_RESET, msg=f"Run 3: the device reset itself under the combined faults ({exit_reason(ec, killed=proc.killed)}, exit code {ec})")
    reset = parse_machine_reset_line(read_log(log3))
    _check(condition=reset is not None and reset.kind == "reset" and reset.reset_count == 1, msg=f"Run 3: the runner's machine reset line names one reset ({reset!r})")
    wdt3 = _would_have_triggered_count(log3, "Run 3")
    _check(condition=wdt3 == 0, msg=f"Run 3: watchdog never starved under the sustained faults (would_have_triggered_count={wdt3!r})")
    # The ceiling is window / 627 ms x 2: each persisted entry writes both block copies of its chunk (agent, 2026-10-21).
    # The chip is silent, so its landed count stays 0: the data phases and WRENs issued to it are what the product sent,
    # a write being at most two WRENs (the driver's one latch retry, asy_fram_driver.py _enable_write()).
    ceiling = int(window_ms // _PERSISTED_LOG_CHUNK_WRITE_MS) * 2
    line = _shutdown_line(log3, "Run 3")
    writes = line.fram_writes + line.fram_silent_writes if line is not None else None
    _check(condition=writes is not None and writes <= ceiling, msg=f"Run 3: the FRAM chip's {writes!r} writes, landed or issued while silent, stay within the persisted-log rate, {ceiling} over the {window_ms:.0f} ms run")
    attempts = -(-line.fram_silent_wrens // 2) if line is not None else None
    _check(condition=attempts is not None and attempts <= ceiling, msg=f"Run 3: the {attempts!r} FRAM write attempts its silent chip saw (WRENs / 2) stay within the persisted-log rate, {ceiling} over the {window_ms:.0f} ms run")


def _run_4_bus_fault_persistence_sweep(ctx: RunContext) -> None:
    # ---- Run 4: relaunch fault-free on Run 3's state: the reset reason is the escalation, the boot cleared the reset
    # record, nothing logged while FRAM was gone persisted, every bus is live. FRAM's own log is out of the 0 sweep: a
    # chip that answered zeros for a whole run is found blank, and the self-healing read logs that afresh. ----
    log4 = ctx.logs_dir / "run4_bus_fault_persistence_sweep.log"
    proc = _spawn(ctx, [], log4)
    try:
        _wait_until_serving(proc)
        reason = _status_field("system", "ResetReason")
        expected = _reset_code("_RR_TASK_BUDGET")
        _check(condition=reason == expected, msg=f"Run 4: ResetReason is the supervisor's escalation code {expected} after Run 3's reset ({reason!r})")
        for inst in _fault_instances(ctx, _SUSTAINED_FAULT):
            if inst.driver not in _NO_PERSIST_WHEN_FRAM_FAULTED:
                continue  # WIFI's own reset check is Run 8, after its own fault run (Run 7)
            entry = _errcount_required(inst.errcount_name)
            _check(condition=entry.get("counter", -1) == 0, msg=f"Run 4: {inst.errcount_name}'s error count correctly did NOT persist across reboot (FRAM was gone for all of Run 3, so nothing it logged could reach the chip) ({entry!r})")
        for inst in _fault_instances(ctx, _SUSTAINED_FAULT):
            if inst.driver in _MEASUREMENT_DRIVERS:
                reading = _wait_for_reading(inst.errcount_name, _ERROR_COUNT_WAIT_S)
                _check(condition=_real_reading(reading), msg=f"Run 4: {inst.errcount_name} produces real readings again after a run in which every bus (FRAM included) was faulted throughout ({reading!r})")
    except Exception as exc:
        _fail(f"Run 4 (bus-fault persistence-correctness sweep): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 4")
        _check(condition=ec == 0, msg=f"Run 4: clean shutdown (exit code {ec})")
    line = _shutdown_line(log4, "Run 4")
    _check(condition=line is not None and line.mem_backup_r0 == (0, 0, 0, 0), msg=f"Run 4: the boot that read the reset record cleared it (mem_backup r0 {line.mem_backup_r0 if line else None!r})")


def _run_5_recovery_after_bounded_fault(ctx: RunContext) -> JSONObject:
    # ---- Run 5: fresh boot with a small BOUNDED fault on SGP40's measure reads only, proving recovery - the half
    # Run 3 cannot show. A station link is configured so the clock syncs and each read carries a timestamp; the
    # failure count must then stay put across two observed read cycles. Runs where the device wires an SGP40 (C.8). ----
    sgp40 = next((inst for inst in ctx.instances if inst.driver == "sgp40"), None)
    if sgp40 is None:
        _SUMMARY.add("skipped", f"{_CURRENT_PASS_LABEL}Run 5/5b", f"{ctx.device} wires no SGP40")
        return {}
    _archive_state(ctx, "run5")
    log5 = ctx.logs_dir / "run5_recovery_after_bounded_fault.log"
    proc = _spawn(ctx, ["--fault", f"{sgp40.key}:{_RUN_5_FAULT_OP}:{_BOUNDED_FAULT_COUNT}:{_SGP40_MEASURE_RAW:04X}"], log5)
    name = sgp40.errcount_name
    final: JSONObject = {}
    try:
        _wait_until_serving(proc)
        status, body = _http("PUT", "/networking", {"SSID": _TEST_SSID})
        _check(condition=status == _HTTP_OK and _field(body, "result", "SSID") in ("Valid", "Unchanged"), msg="Run 5: PUT /networking SSID accepted, so the clock can sync")
        expected_events = _BOUNDED_FAULT_COUNT * _EVENTS_PER_FAILED_READ
        entry = _wait_for_failure_events(name, expected_events, timeout_s=_ERROR_COUNT_WAIT_S)
        failures = _failure_events(entry)
        _check(condition=failures == expected_events, msg=f"Run 5: {name}'s bounded fault ({_BOUNDED_FAULT_COUNT} failed reads, {expected_events} failure events) was fully recorded, no more ({entry!r})")
        entry = _errcount_required(name)
        codes = _error_codes(entry)
        allowed_w = {code("W", w) for w in _RUN_5_ALLOWED_WARNINGS}
        _check(condition={num for kind, num in codes if kind == "E"} == {code("E", e) for e in _RUN_5_ERRORS} and all(num in allowed_w for kind, num in codes if kind == "W"), msg=f"Run 5: {name}'s E codes are exactly its measure-read failure and the streak, every W a ladder rung or a storage warning ({codes!r})")
        _check(condition=_wait_for_ntp_sync(_NTP_FIRST_SYNC_WAIT_S), msg="Run 5: NTP synced against the twin's local responder once the station link came up")
        cycles = _wait_for_sgp40_reads(_READ_CYCLES, timeout_s=_READ_CYCLE_WAIT_S)
        final = _errcount_required(name)
        _check(condition=cycles >= _READ_CYCLES and _failure_events(final) == failures, msg=f"Run 5: {name}'s failure count stayed put across {cycles} observed read cycles once the fault was spent (recovery) ({final!r})")
        reading = _wait_for_reading(name, _ERROR_COUNT_WAIT_S)
        _check(condition=_real_reading(reading), msg=f"Run 5: {name} measurements resumed after recovery ({reading!r})")
    except Exception as exc:
        _fail(f"Run 5 (recovery after a bounded fault): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 5")
        _check(condition=ec == 0, msg=f"Run 5: clean shutdown (exit code {ec})")
    return final


def _run_5b_error_log_restore_is_all_or_nothing(ctx: RunContext, written: JSONObject) -> None:
    # ---- Run 5b: reboot straight onto Run 5's state, fault-free. Run 5 shut down abruptly, which can catch a chunk
    # write in flight and lose the ring (owner, 2026-09-26, accepted: "an abrupt reset mid-write may lose a module's
    # whole FRAM history, all-or-nothing, never partial or garbled"), so the restored history is [] or Run 5's exactly. ----
    if not written:
        return  # Run 5 recorded its skip, or failed before it read an entry
    log5b = ctx.logs_dir / "run5b_error_log_restore_is_all_or_nothing.log"
    proc = _spawn(ctx, [], log5b)
    try:
        _wait_until_serving(proc)
        for name in _PERSISTED_ERROR_MODULES:
            # The webserver answers before the FRAM-backed loggers finish setup(), and setup() IS the restore.
            entry = _wait_for_error_type_count(name, _error_type_count(written), timeout_s=_ERROR_COUNT_WAIT_S)
            entry = entry or _errcount_required(name)
            restored, kept = _error_codes(entry), _error_codes(written)
            whole = restored == kept and _counter(entry) >= max(_counter(written), 0)
            nothing = restored == [] or all(kind != "E" for kind, _ in restored)
            _check(condition=whole or nothing, msg=f"Run 5b: {name}'s FRAM-backed history came back all-or-nothing after an abrupt restart - Run 5's exact ring and count or none of it (wrote {written!r}, restored {entry!r})")
    except Exception as exc:
        _fail(f"Run 5b (error-log restore is all-or-nothing): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 5b")
        _check(condition=ec == 0, msg=f"Run 5b: clean shutdown (exit code {ec})")


def _run_5c_storage_paused_shutdown_never_loses_the_error_log(ctx: RunContext) -> None:
    # ---- Run 5c: a commanded reboot, the case that loses nothing at all: the product's controlled shutdown
    # drains FRAM, then stops every task, then resets. One bounded fault per chip instance, one per PROCESS, each
    # link chained onto the previous link's state (three at once would exhaust the restart budget, Part C.4.1). ----
    _archive_state(ctx, "run5c")
    recorded: dict[str, int] = {}
    snapshot_table: dict[str, JSONObject] = {}
    for inst in _healthy_store_fault_instances(ctx):
        name = inst.errcount_name
        before_link = snapshot_table.get(name, {})
        log5c_a = ctx.logs_dir / f"run5c_a_{inst.key}_record_then_reboot.log"
        proc = _spawn(ctx, ["--fault", f"{inst.key}:{_BOUNDED_FAULT[inst.driver]}:{_BOUNDED_FAULT_COUNT}"], log5c_a)
        ec = -1
        try:
            _wait_until_serving(proc)
            for earlier, expected in recorded.items():
                found = _error_type_count(_errcount_required(earlier))
                _check(condition=found == expected, msg=f"Run 5c: {earlier}'s {expected} chip-healthy error(s) were still on the chip when {name}'s own fault link booted ({found} found)")
            _wait_for_error_type_count(name, 1, timeout_s=_FIRST_FAULT_WAIT_S)
            # Snapshot only once the bounded fault stopped producing entries: a mid-fault snapshot would be compared
            # after the reboot against entries that landed after it, and a lossless run would read as a loss.
            settled = _wait_for_error_counts_to_settle([name], timeout_s=_LONG_WAIT_S)
            _check(condition=settled[name] > 0, msg=f"Run 5c: {name}'s bounded fault was recorded as a real error against a HEALTHY store ({settled!r})")
            if inst.driver == "sgp40":
                sgp40 = _errcount_required(name)
                _check(condition=_link_failures(before_link, sgp40) == _BOUNDED_FAULT_COUNT, msg=f"Run 5c: {name} recorded all {_BOUNDED_FAULT_COUNT} bounded failures and no more before the commanded reboot (before {before_link!r}, after {sgp40!r})")
            snapshot_table = _errcount_all()
            recorded[name] = _error_type_count(snapshot_table.get(name, {}))
            word = _put_system_cmd("reboot")
            _check(condition=word == "Valid", msg=f"Run 5c: PUT /system reboot answered Valid before {name}'s relaunch ({word!r})")
        except Exception as exc:
            _fail(f"Run 5c ({inst.key}: record then reboot): {exc!r}")
        finally:
            ec = _wait_exit(proc, f"Run 5c-a ({inst.key})", timeout_s=_commanded_reset_deadline_s())
        _check(condition=ec == EXIT_SIMULATED_RESET, msg=f"Run 5c: the commanded reboot reset the device after {name}'s link ({exit_reason(ec, killed=proc.killed)}, exit code {ec})")

    log5c_b = ctx.logs_dir / "run5c_b_history_survived_the_commanded_reboot.log"
    proc = _spawn(ctx, [], log5c_b)
    try:
        _wait_until_serving(proc)
        reason = _status_field("system", "ResetReason")
        _check(condition=reason == _reset_code("_RR_REBOOT"), msg=f"Run 5c: ResetReason is the REST reboot's code {_reset_code('_RR_REBOOT')} ({reason!r})")
        for name, expected in recorded.items():
            _wait_for_error_type_count(name, expected, timeout_s=_ERROR_COUNT_WAIT_S)
        restored_table = _errcount_all()
        for name, expected in recorded.items():
            entry = restored_table.get(name, {})
            restored = _error_type_count(entry)
            _check(condition=restored == expected, msg=f"Run 5c: {name}'s {expected} chip-healthy error(s) survived a commanded reboot - the one case that must never lose them ({restored} found, {entry!r})")
            _check(condition=_counter(entry) >= expected, msg=f"Run 5c: {name}'s persisted error COUNT was restored too, not just the history ring ({entry!r})")
        # Every OTHER registered source in the same breath (SYSTEM/NOTIFY/NTP/WEBSERVER/DNSSRV, every FRAM-backed
        # CFGMGR_*, every uart_link instance). A fresh entry from THIS boot is legitimate: "nothing was lost".
        for name, before in snapshot_table.items():
            if name in recorded or name in _IN_MEMORY_ONLY_ERROR_SOURCES:
                continue
            had = _error_type_count(before)
            now = _error_type_count(restored_table.get(name, {}))
            _check(condition=now >= had, msg=f"Run 5c: {name} kept the {had} error(s) it had logged before the commanded reboot ({now} found, {restored_table.get(name)!r})")
        _check(condition=sorted(restored_table) == sorted(snapshot_table), msg=f"Run 5c: the reboot registered exactly the same error sources, so no row silently dropped out of this sweep (before {sorted(snapshot_table)!r}, after {sorted(restored_table)!r})")
        _check(condition=_mem_paused() is False, msg="Run 5c: the shutdown's storage pause did NOT survive the reboot (it is RAM-only by design)")
        # The restored history must not be a read-only relic: ResetErrors clears it on the chip, every source at once.
        status = _put_reset_errors_timed("Run 5c")
        _check(condition=status == _HTTP_OK, msg=f"Run 5c: PUT /status ResetErrors accepted (status {status})")
        cleared_table = _errcount_all()
        for name in recorded:
            entry = cleared_table.get(name, {})
            _check(condition=_error_type_count(entry) == 0 and entry.get("counter", -1) == 0, msg=f"Run 5c: {name}'s restored history was actually cleared by ResetErrors, not just masked ({entry!r})")
    except Exception as exc:
        _fail(f"Run 5c (history survived the commanded reboot): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 5c-b")
        _check(condition=ec == 0, msg=f"Run 5c: clean shutdown (exit code {ec})")


def _run_6_configure_ssid(ctx: RunContext) -> None:
    # ---- Run 6: clean boot, configuring a real persisted SSID for Run 7. A genuine STA-connect-failure cycle needs
    # a real SSID, not the unconfigured empty-string shortcut. ----
    _archive_state(ctx, "run6")
    log6 = ctx.logs_dir / "run6_configure_ssid.log"
    proc = _spawn(ctx, [], log6)
    try:
        _wait_until_serving(proc)
        status, body = _http("PUT", "/networking", {"SSID": _TEST_SSID})
        _check(condition=status == _HTTP_OK and _field(body, "result", "SSID") in ("Valid", "Unchanged"), msg="Run 6: PUT /networking SSID accepted")
    except Exception as exc:
        _fail(f"Run 6 (configure SSID for WiFi test): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 6")
        _check(condition=ec == 0, msg=f"Run 6: clean shutdown (exit code {ec})")


def _run_7_wifi_hotspot_dns(ctx: RunContext) -> None:
    # ---- Run 7: reboot with scripted repeated STA-connect failures, driving the real hotspot fallback, then a real
    # UDP query the real CaptiveDNS answers - possible only through _unix_port_udp_addr_shim.py, which works around
    # three Unix-port socket quirks twin-side. Port 53 needs the interpreter's CAP_NET_BIND_SERVICE, checked first. ----
    if not _has_net_bind_capability(ctx.micropython_bin):
        _fail(f"Run 7: the interpreter lacks CAP_NET_BIND_SERVICE: Run 7's DNS server cannot bind port 53 ({ctx.micropython_bin})")
        return
    log7 = ctx.logs_dir / "run7_wifi_hotspot_dns.log"
    proc = _spawn(ctx, ["--wifi-outcome", "no_ap"] * _WIFI_SCRIPTED_FAILURES, log7)
    try:
        _wait_until_serving(proc)
        # Waits for the FULL scripted failure count: hotspot activation, and so the CaptiveDNS, starts on the fifth.
        entry = _wait_for_errcount_above("WIFI", _WIFI_PERSISTED_EVENTS - 1, timeout_s=_LONG_WAIT_S)
        _check(condition=_counter(entry) >= _WIFI_PERSISTED_EVENTS, msg=f"Run 7: all {_WIFI_SCRIPTED_FAILURES} repeated WiFi connect failures drove real hotspot fallback, and both they and the fallback were recorded in WIFI's error counter ({entry!r})")
        logged = _error_type_count(entry, type_char="W")
        _check(condition=logged == _WIFI_PERSISTED_WARNINGS, msg=f"Run 7: those {_WIFI_SCRIPTED_FAILURES} identical verdicts spent one history slot, not one each, and the fallback one more ({_WIFI_PERSISTED_WARNINGS}) - the ring still holds what preceded the outage ({entry!r})")
        answered = _wait_for_dns_answer(HOST, timeout_s=_LONG_WAIT_S)
        bind_failed = _DNS_BIND_ERROR_TEXT in read_log(log7) or code("E", "INIT") in [num for kind, num in _error_codes(_errcount_required("DNSSRV")) if kind == "E"]
        _check(condition=answered, msg="Run 7: the real CaptiveDNS answered a real UDP DNS query after WiFi hotspot fallback" + ("" if answered else f" - {'the DNS server logged its port-53 bind failure' if bind_failed else 'no bind failure was logged'}"))
        status, _ = _http("GET", "/status")
        _check(condition=status == _HTTP_OK, msg="Run 7: webserver stayed reachable throughout the WiFi hotspot-fallback transition")
    except Exception as exc:
        _fail(f"Run 7 (WiFi hotspot fallback + DNS): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 7")
        _check(condition=ec == 0, msg=f"Run 7: process survived the WiFi hotspot-fallback transition without crashing (exit code {ec})")


def _run_8_wifi_persistence_and_configure_ntp(ctx: RunContext) -> None:
    # ---- Run 8: reboot fault-free - WIFI's own persistence check (FRAM-backed, so all-or-nothing after Run 7's
    # abrupt restart, like SGP40's Run 5b), the station link's first NTP sync with both time fields present, and an
    # unreachable NTP host configured (persisted) for Run 9. ----
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
        _check(condition=entry.get("counter", -1) in (0, _WIFI_PERSISTED_EVENTS), msg=f"Run 8: and the counter came back with it, still naming all {_WIFI_SCRIPTED_FAILURES} attempts and the fallback rather than the slots they share ({entry!r})")
        synced = _wait_for_ntp_sync(_NTP_FIRST_SYNC_WAIT_S)
        _check(condition=synced, msg=f"Run 8: NTP synced against the twin's local responder within {_NTP_FIRST_SYNC_WAIT_S:.0f}s of the station link")
        times = (_status_field("system", "UTCTime"), _status_field("system", "LocalTime"))
        _check(condition=all(isinstance(t, dict) and len(t) == _TIME_FIELDS for t in times), msg=f"Run 8: UTCTime and LocalTime are both present after the first NTP sync, each the 8-field time ({times!r})")
        # RFC 5737 TEST-NET-1: no server answers it, a reproducible "unreachable" host rather than incidental
        # sandbox network policy; whether a route carries the request out decides Run 9's code (_route_leaves_host()).
        status, body = _http("PUT", "/networking", {"NTPHost": _NTP_UNREACHABLE_HOST})
        _check(condition=status == _HTTP_OK and _field(body, "result", "NTPHost") in ("Valid", "Unchanged"), msg="Run 8: PUT /networking NTPHost (unreachable) accepted")
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
        system_before = _counter(_errcount_required("SYSTEM"))
        # Past every attempt the backoff makes within the old give-up's reach, then one supervisor pass: the time a task
        # that ended on the last failure takes to be restarted, an absence no probe can observe.
        failed = _failure_events(_wait_for_failure_events("NTP", _NTP_UNREACHABLE_FAILURES, timeout_s=_NTP_UNREACHABLE_WATCH_S))
        time.sleep(_src_int("asy_system_service.py", "_TASK_CHECK_TIME") + _COMMANDED_RESET_MARGIN_S)
        _check(condition=failed >= _NTP_UNREACHABLE_FAILURES, msg=f"Run 9: NTP failed {failed} time(s) within the {_NTP_UNREACHABLE_WATCH_S:.0f}s watch, every attempt its backoff schedules there")
        status, _ = _http("GET", "/system")
        _check(condition=status == _HTTP_OK, msg="Run 9: webserver stayed fully healthy with NTP permanently unreachable")
        nums = [num for _kind, num in _error_codes(_errcount_required("NTP"))]
        ok, msg = _ntp_unreachable_verdict(nums, route=_route_leaves_host(_NTP_UNREACHABLE_HOST, _NTP_PORT))
        _check(condition=ok, msg=msg)
        system_after = _counter(_errcount_required("SYSTEM"))
        _check(condition=system_after == system_before >= 0, msg=f"Run 9: no task ended and was restarted while NTP failed (SYSTEM counter {system_before} -> {system_after})")
    except Exception as exc:
        _fail(f"Run 9 (NTP unreachable): {exc!r}")
    finally:
        ec = _shutdown(proc, "Run 9")
        _check(condition=ec == 0, msg=f"Run 9: clean shutdown (exit code {ec})")


def _run_both_passes(args: argparse.Namespace) -> int:
    generated_dir, micropypath, logs_dir = GENERATED_SRC_DIR, TWIN_MICROPYPATH, _logs_dir(args)
    device_toml = REPO_ROOT / "devices" / f"{args.device}.toml"
    if args.device_toml is not None:
        device_toml = args.device_toml.resolve()
        generated_dir = logs_dir.resolve() / "generated"
        if not _generate_from_toml(device_toml, generated_dir):
            _SUMMARY.add("failed", f"generation from {device_toml} failed", "see the generator's output above")
            return 1
        micropypath = f"{generated_dir}:{TWIN_MICROPYPATH}"
    module = f"sensortask_{device_toml.stem}"
    wiring_plan_path = generated_dir / f"{module}_wiring_plan.json"
    if not wiring_plan_path.exists():
        hint = "run scripts/_generate_sensortask_modules.py first (scripts/run_digital_twin_ci.sh already does this)"
        print(f"error: {wiring_plan_path} not found - {hint}", file=sys.stderr)
        _SUMMARY.add("failed", f"wiring plan {wiring_plan_path} missing", hint)
        return 1
    reference = generated_dir / "api" / f"{device_toml.stem}.json"
    if not reference.exists():
        hint = "the generator writes it beside the wiring plan: run scripts/_generate_sensortask_modules.py"
        print(f"error: {reference} not found - {hint}", file=sys.stderr)
        _SUMMARY.add("failed", f"API reference {reference} missing", hint)
        return 1
    base_ctx = RunContext(
        micropython_bin=args.micropython_bin,
        logs_dir=logs_dir,  # overridden per pass below
        device=args.device,
        module=module,
        wiring_plan_path=wiring_plan_path,
        instances=_plan_instances(device_toml),
        gc_threshold=-1,  # overridden per pass below
        routes=_get_routes(reference),
        hostname=_toml_hostname(device_toml),
        micropypath=micropypath,
    )
    crc16 = args.device_toml is not None and "crc16" in _link_crc_modes(device_toml)
    # The WHOLE suite runs twice (Part I.4(e)): clean at MicroPython's own gc.threshold(-1), zero MemoryErrors anywhere,
    # BEFORE again at the chosen 32768, which is defense in depth and never itself why a run passes. -1 first; each
    # pass logs into its own subdirectory, so a failure's logs are never overwritten by the other.
    # @tunable gc.threshold_bytes = 32768
    stages = ((-1, "gc_threshold_neg1"), (32768, "gc_threshold_32768"))
    for gc_threshold, subdir in stages:
        if args.gc_threshold is not None and gc_threshold != args.gc_threshold:
            continue
        for repeat in range(args.repeat):
            logs_dir = base_ctx.logs_dir / subdir / (f"repeat_{repeat + 1:02d}" if args.repeat > 1 else "")
            ctx = replace(base_ctx, logs_dir=logs_dir, gc_threshold=gc_threshold)
            run_suite(ctx, args.only)
            if crc16:
                _check_crc16_links(ctx)

    print()
    return 1 if _FAILURES or _SUMMARY.failed else 0


def _run_selection(text: str) -> frozenset[str]:
    # --only's value: run names as RUN_NAMES lists them; an unknown name, or a run without the run it consumes, is a
    # usage error (exit 2), never a selection that silently checks less.
    names = frozenset(part.strip() for part in text.split(",") if part.strip())
    unknown = sorted(names - set(RUN_NAMES))
    if not names or unknown:
        raise argparse.ArgumentTypeError(f"unknown run name(s) {unknown or [text]!r} - expected some of {', '.join(RUN_NAMES)}")
    orphans = sorted(f"{name} needs {_PRODUCERS[name]}" for name in names if name in _PRODUCERS and _PRODUCERS[name] not in names)
    if orphans:
        raise argparse.ArgumentTypeError(f"{'; '.join(orphans)} - a run reads the state the run before it leaves")
    return names


def _save_fram_evidence(ctx: RunContext, label: str) -> None:
    # Before any erasefram: the errcount table over REST and a copy of the FRAM state file, into the archive.
    evidence = ctx.logs_dir / "fram_evidence" / label.replace(" ", "_")
    evidence.mkdir(parents=True, exist_ok=True)
    status, body = _http("GET", "/status")
    (evidence / "errcount.json").write_text(json.dumps({"status": status, "errcount": body.get("errcount") if isinstance(body, dict) else None}, indent=2), encoding="utf-8")
    fram = state_paths(ctx.state_dir).fram
    if fram.exists():
        shutil.copy2(fram, evidence / fram.name)


def _shutdown(run: TwinRun, run_label: str, timeout_s: float = 15.0, *, starves_watchdog: bool = False, interrupt: bool = False) -> int:
    ec = shutdown(run, run_label, timeout_s, interrupt=interrupt)
    _check_exit(run, ec, run_label)
    _check_run_log(run, run_label, starves_watchdog=starves_watchdog)
    return ec


def _shutdown_line(log_path: Path, run_label: str) -> ShutdownLine | None:
    # The runner's shutdown line, or None (no line, or a malformed one, which fails the run naming why).
    try:
        return parse_shutdown_line(read_log(log_path))
    except ValueError as exc:
        _fail(f"{run_label}: the runner's shutdown line is malformed: {exc}")
        return None


def _shutdown_step_lines(log_text: str) -> list[str]:
    # The controlled shutdown's step lines in log order, each by the step text it carries.
    steps = (*_SHUTDOWN_STEP_LINES, *_SHUTDOWN_S5_PREFIXES)
    return [step for line in log_text.splitlines() for step in steps if f"SYSTEM {step}" in line]


def _soak_warm_up(log_path: Path, endpoints: tuple[str, ...], http_failures: list[str]) -> int:
    # Warm-up cycles until no cycle has set a new MEM_SAMPLE floor for _SOAK_PLATEAU_CYCLES cycles, at most
    # _SOAK_WARMUP_CYCLES; a cycle that printed no sample counts toward neither. Returns the cycles run.
    floor: int | None = None
    held = 0
    for cycle in range(_SOAK_WARMUP_CYCLES):
        offset = log_path.stat().st_size
        for path in endpoints:
            try:
                _http("GET", path)
            except (OSError, http.client.HTTPException) as e:  # one more failure, never an abort of the cycles
                http_failures.append(f"warmup: GET {path} -> {e!r}")
        samples = [free for _offset, free in _mem_samples_from(log_path, offset)]
        if samples:
            held = 0 if floor is None or min(samples) < floor else held + 1
            floor = min(samples) if floor is None else min(floor, *samples)
        if held >= _SOAK_PLATEAU_CYCLES:
            return cycle + 1
    return _SOAK_WARMUP_CYCLES


def _spawn(ctx: RunContext, extra_args: list[str], log_path: Path) -> TwinRun:
    # Every run at ctx.gc_threshold, and every state path inside the pass's own state directory.
    launch = TwinLaunch(ctx.micropython_bin, ctx.module, ctx.wiring_plan_path, ctx.device, HOST, PORT, ctx.gc_threshold, ctx.micropypath)
    return spawn(launch, state_dir=ctx.state_dir, log_path=log_path, args=extra_args)


def _src_int(filename: str, name: str) -> int:
    # A product constant read from its source by buildgen's own reader, never a copy that could drift.
    return module_int_const(SRC_DIR, filename, name)


def _stack_fault_instance(plan: "dict[str, JSONValue]") -> Instance | None:
    # Run 12's stack subject: the plan's first attachment, I2C buses in plan order before SPI, whose driver has a read op.
    buses = plan.get("buses")
    spi = plan.get("spi")
    attached = [*(a for bus in (buses.values() if isinstance(buses, dict) else ()) if isinstance(bus, list) for a in bus), *(spi.values() if isinstance(spi, dict) else ())]
    for a in attached:
        if isinstance(a, dict) and a.get("driver") in _STACK_FAULT_READ_OP:
            driver, name_ext = str(a["driver"]), str(a.get("name_ext") or "")
            return Instance(instance_label((driver, name_ext)), driver, name_ext)
    return None


def _status_field(group: str, key: str) -> object:
    # One field of GET /status, strict: an unreadable answer raises rather than reading as a value.
    status, body = _http("GET", "/status")
    block = _field(body, group)
    if status != _HTTP_OK or not isinstance(block, dict):
        raise RuntimeError(f"GET /status gave no readable {group!r} block (status {status})")
    if key not in block:
        raise RuntimeError(f"GET /status's {group!r} block carries no {key!r}")
    return block[key]


def _toml_hostname(device_toml: Path) -> str:
    with device_toml.open("rb") as f:
        device = tomllib.load(f).get("device", {})
    hostname = device.get("hostname") if isinstance(device, dict) else None
    return hostname if isinstance(hostname, str) else ""


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


def _wait_exit(run: TwinRun, run_label: str, timeout_s: float, *, starves_watchdog: bool = False) -> int:
    ec = wait_exit(run, timeout_s)
    _check_exit(run, ec, run_label)
    _check_run_log(run, run_label, starves_watchdog=starves_watchdog)
    return ec


def _wait_for_dns_answer(host: str, timeout_s: float) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _try_dns_query(host):
            return True
        time.sleep(_DNS_POLL_S)
    return False


def _wait_for_errcount_above(name: str, floor: int, timeout_s: float) -> JSONObject:
    # Polls /status until `name`'s error counter climbs above `floor`, or times out - used instead
    # of a fixed sleep for state-machine transitions (e.g. WiFi hotspot fallback) with real, but
    # not perfectly predictable, wall-clock timing.
    deadline = time.monotonic() + timeout_s
    while True:  # read at least once: the entry returned at the deadline is the last one read
        entry = _errcount(name)
        if _counter(entry) > floor or time.monotonic() >= deadline:
            return entry
        time.sleep(_ERRCOUNT_POLL_S)


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


def _wait_for_error_type_count(name: str, target: int, timeout_s: float, type_char: str = "E", run: "TwinRun | None" = None) -> JSONObject:
    # _wait_for_errcount_above()'s poll-never-sleep reasoning, keyed on one type's count rather than the raw counter
    # a "W" also bumps; given the run, the poll stops once its process has exited.
    deadline = time.monotonic() + timeout_s
    entry: JSONObject = {}
    while True:  # read at least once: the entry returned at the deadline or the exit is the last one read
        entry = _errcount(name) or entry
        if _error_type_count(entry, type_char) >= target or time.monotonic() >= deadline or (run is not None and run.proc.poll() is not None):
            return entry
        time.sleep(_ERRCOUNT_POLL_S)


def _wait_for_failure_events(name: str, target: int, timeout_s: float) -> JSONObject:
    # _wait_for_error_type_count()'s poll, keyed on failure events rather than history slots.
    deadline = time.monotonic() + timeout_s
    while True:  # read at least once: the entry returned at the deadline is the last one read
        entry = _errcount(name)
        if _failure_events(entry) >= target or time.monotonic() >= deadline:
            return entry
        time.sleep(_ERRCOUNT_POLL_S)


def _wait_for_log_line(run: TwinRun, text: str, timeout_s: float) -> bool:
    # Polls the run's log for a line holding `text` until the deadline or its process's exit, read once more after it.
    deadline = time.monotonic() + timeout_s
    while True:
        exited = run.proc.poll() is not None
        if any(text in line for line in read_log(run.log_path).splitlines()):
            return True
        if exited or time.monotonic() >= deadline:
            return False
        time.sleep(_VERBOSE_POLL_S)


def _wait_for_ntp_sync(timeout_s: float) -> bool:
    # NTPSynced turns true once a station link synced against the twin's local responder.
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        status, body = _http("GET", "/status")
        networking = body.get("networking") if status == _HTTP_OK and isinstance(body, dict) else None
        if isinstance(networking, dict) and networking.get("NTPSynced") is True:
            return True
        time.sleep(_ERRCOUNT_POLL_S)
    return False


def _wait_for_reading(name: str, timeout_s: float) -> object:
    # Polls GET /measurements until `name`'s block carries a value, or the deadline; returns the last block read.
    deadline = time.monotonic() + timeout_s
    reading: object = None
    while time.monotonic() < deadline:
        status, body = _http("GET", "/measurements")
        reading = body.get(name) if status == _HTTP_OK and isinstance(body, dict) else None
        if _real_reading(reading):
            return reading
        time.sleep(_VERBOSE_POLL_S)
    return reading


def _wait_for_sgp40_reads(count: int, timeout_s: float) -> int:
    # SGP40's measurement timestamp advancing `count` times is `count` observed read cycles; returns how many were seen.
    deadline = time.monotonic() + timeout_s
    seen: list[object] = []
    while time.monotonic() < deadline and len(seen) <= count:
        status, body = _http("GET", "/measurements")
        reading = body.get("SGP40") if status == _HTTP_OK and isinstance(body, dict) else None
        stamp = reading.get("TS") if isinstance(reading, dict) else None
        if stamp is not None and (not seen or stamp != seen[-1]):
            seen.append(stamp)
        time.sleep(_VERBOSE_POLL_S)
    return max(0, len(seen) - 1)


def _wait_for_verbose_lines(log_path: Path, minimum: int, timeout_s: float) -> int:
    # Polls the run's own log until it holds `minimum` verbose lines, or the deadline; returns the count seen.
    deadline = time.monotonic() + timeout_s
    count = _count_verbose_log_lines(read_log(log_path))
    while count < minimum and time.monotonic() < deadline:
        time.sleep(_VERBOSE_POLL_S)
        count = _count_verbose_log_lines(read_log(log_path))
    return count


def _wait_until_serving(run: TwinRun, timeout_s: float = 20.0) -> None:
    wait_until_serving(run, HOST, PORT, timeout_s)


def _would_have_triggered_count(log_path: Path, run_label: str) -> int | None:
    # The runner's shutdown line's watchdog count; None when no line was printed (a crash before the runner's finally).
    line = _shutdown_line(log_path, run_label)
    return None if line is None else int(line.would_have_triggered_count)


def main() -> int:
    global _SUMMARY
    args = _build_parser().parse_args()
    # The block is printed on every exit, an exception's included; its code is the one returned.
    stage = "both" if args.gc_threshold is None else str(args.gc_threshold)
    _SUMMARY = Summary("scripts/_digital_twin_ci_suite.py", unit="checks", levels=f"L2 ({args.device})", gc_stage=stage)
    exit_code = 1
    try:
        # The product's fixed ports, Run 7's captive DNS and every run's listener: passed when the runner holds them.
        with port_lock(DNS_PORT, _LOCK_RUNNER), port_lock(PORT, _LOCK_RUNNER):
            exit_code = _run_both_passes(args)
    except PortHeldError as exc:
        print(f"error: {exc}", file=sys.stderr)
        _SUMMARY.add("failed", "the product's fixed ports", str(exc))
    finally:
        exit_code = _SUMMARY.print(exit_code)
    return exit_code


def run_suite(ctx: RunContext, only: "frozenset[str] | None" = None) -> None:
    # Runs every run of RUN_NAMES (or the --only selection) once at ctx.gc_threshold; main() says why the whole
    # function runs twice. It tallies nothing itself - _FAILURES is shared on purpose, so main() prints one
    # combined report naming every failure from either pass.
    global _CURRENT_PASS_LABEL
    _CURRENT_PASS_LABEL = f"[gc.threshold={ctx.gc_threshold}] "
    _CHECKS_PER_PASS[_CURRENT_PASS_LABEL] = 0
    ctx.logs_dir.mkdir(parents=True, exist_ok=True)
    _archive_state(ctx, "pass start")
    print(f"== Left out of the fault matrix, each with its reason: {json.dumps({':'.join(key): reason for key, reason in _LEFT_OUT.items()}, indent=1)}")

    def chosen(name: str) -> bool:
        return only is None or name in only

    # An exception that ends a pass early is recorded in the block before it propagates.
    try:
        if chosen("1"):
            _run_1_baseline(ctx)
        if chosen("2"):
            _run_2_reboot_settings_persistence(ctx)
        if chosen("3"):
            _run_3_sustained_bus_fault_matrix(ctx)
        if chosen("4"):
            _run_4_bus_fault_persistence_sweep(ctx)
        run5_entry = _run_5_recovery_after_bounded_fault(ctx) if chosen("5") else {}
        if chosen("5b"):
            _run_5b_error_log_restore_is_all_or_nothing(ctx, run5_entry)
        if chosen("5c"):
            _run_5c_storage_paused_shutdown_never_loses_the_error_log(ctx)
        if chosen("6"):
            _run_6_configure_ssid(ctx)
        if chosen("7"):
            _run_7_wifi_hotspot_dns(ctx)
        if chosen("8"):
            _run_8_wifi_persistence_and_configure_ntp(ctx)
        if chosen("9"):
            _run_9_ntp_unreachable(ctx)
        if chosen("10"):
            _run_10_watchdog_hang_backstop(ctx)
        if chosen("11"):
            _run_11_soak(ctx)
        if chosen("11b"):
            _run_11b_full_ceiling_concurrency(ctx)
        if chosen("12"):
            _run_12_reset_reasons(ctx)
        if chosen("13"):
            _run_13_system_commands(ctx)
    except BaseException as exc:
        _SUMMARY.add("failed", f"{_CURRENT_PASS_LABEL}suite aborted: {type(exc).__name__}: {exc}")
        raise
    if _CHECKS_PER_PASS[_CURRENT_PASS_LABEL] == 0:
        _SUMMARY.add("vacuous", f"pass {_CURRENT_PASS_LABEL.strip()}")


if __name__ == "__main__":
    raise SystemExit(main())
