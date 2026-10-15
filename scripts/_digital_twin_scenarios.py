#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Host-side L2 scenarios: each boots the device's generated graph in the twin (digital_twin/run_generic_integration.py)
and drives it from this CPython process over HTTP, the runner's stdout lines and its --test- flags - no request is built
in the DUT heap. Run order is (shared group, name): the scenarios that may share run first, then each on its own boot."""

import argparse
import ast
import contextlib
import gzip
import json
import os
import shutil
import socket
import struct
import sys
import threading
import time
from dataclasses import dataclass, field, replace
from http import HTTPStatus
from http.client import HTTPConnection, HTTPException
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, TypeVar

# The repo root is appended, so buildgen and the shared twin helpers resolve; nothing here imports from tests/.
sys.path.append(str(Path(__file__).resolve().parent.parent))
from buildgen.buildspec import BUS_ATTACHED_DRIVERS
from buildgen.model import instance_label, load_device
from buildgen.validate import device_max_connections, module_float_const, module_int_const
from scripts._port_lock import PortHeldError, port_lock
from scripts._summary_block import Summary

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

from scripts._twin_process import (
    TWIN_MICROPYPATH,
    JSONObject,
    JSONValue,
    TwinLaunch,
    TwinRun,
    errcount_table,
    exit_reason,
    feed_gap_verdict,
    log_from,
    log_memory_verdict,
    parse_machine_reset_line,
    parse_shutdown_line,
    read_log,
    send_line,
    shutdown,
    spawn,
    state_paths,
    wait_exit,
    wait_until_serving,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
GENERATED_SRC_DIR = REPO_ROOT / "build" / "generated_src"
SITES_DIR = REPO_ROOT / "build" / "generated_html"
HOST = "127.0.0.1"
_BAND_OWNER = "_digital_twin_scenarios"  # this harness's row of the port-band table (tests/_port_bands.py), read as data
_DNS_PORT = 53
_LOCK_RUNNER = "scripts/_digital_twin_scenarios.py"
_USAGE_EXIT = 2
_EXIT_FAIL = 1
_WEBSERVER = "asy_webserver_service.py"
_SYSTEM = "asy_system_service.py"
_SENSOR_NAMES = {"scd30": "SCD30", "sgp40": "SGP40", "bmp3xx": "BMP3XX", "isl29125": "ISL29125"}  # /measurements keys
_REFUSAL_ERRORS = (ConnectionResetError, BrokenPipeError, ConnectionAbortedError)  # RemoteDisconnected is one of them
_SHARED_DIR = "shared_boots"  # the shared twins' logs and state, beside the scenarios' own directories
_TCP_LISTEN = "0A"  # the LISTEN state in /proc/net/tcp (include/net/tcp_states.h)

# @tunable l2.scenario_request_timeout_s = 10.0
_REQUEST_TIMEOUT_S = 10.0
# @tunable l2.scenario_serving_timeout_s = 30.0
_SERVING_TIMEOUT_S = 30.0
# @tunable l2.scenario_line_poll_s = 0.05
_LINE_POLL_S = 0.05
# @tunable l2.scenario_conn_status_interval_ms = 20
_CONN_STATUS_INTERVAL_MS = 20  # the runner's CONN_SLOTS period: dense enough that a drain is seen within a few polls
# @tunable l2.scenario_fault_status_interval_ms = 100
_FAULT_STATUS_INTERVAL_MS = 100
# @tunable l2.scenario_drain_wait_s = 10.0
_DRAIN_WAIT_S = 10.0  # a slot outlives its response until its close completes (Part H.7.1)
# @tunable l2.scenario_still_serving_s = 5.0
_STILL_SERVING_S = 5.0
# @tunable l2.scenario_flaky_hold_s = 0.05
_FLAKY_HOLD_S = 0.05  # how long a flaky client keeps its partial request open before it hangs up
# @tunable l2.scenario_slow_put_s = 1.0
_SLOW_PUT_S = 1.0  # a slow but healthy PUT's pause between its two halves
# @tunable l2.scenario_stall_ms = 200
_STALL_MS = 200  # the stalled loop's length, past one SYN retry's worth of arrivals queued
# @tunable l2.scenario_watchdog_window_s = 8.5
_WATCHDOG_WINDOW_S = 8.5  # past the 8,000 ms watchdog: a hang's window is the property under test, so it is waited out
# @tunable l2.scenario_refusal_feed_s = 10.0
_REFUSAL_FEED_S = 10.0  # a refused command never stops the feed: watched past one watchdog period
# @tunable l2.scenario_commanded_reset_margin_s = 10.0
_COMMANDED_RESET_MARGIN_S = 10.0
# @tunable l2.scenario_pause_countdown_s = 15.0
_PAUSE_COUNTDOWN_S = 15.0
# @tunable l2.scenario_hotspot_wait_s = 90.0
_HOTSPOT_WAIT_S = 90.0  # five scripted connect failures, then the hotspot and its DNS server
# @tunable l2.scenario_uart_load_s = 20.0
_UART_LOAD_S = 20.0  # the concurrent-load window
# @tunable l2.scenario_uart_load_faults = 3
_UART_LOAD_FAULTS = 3  # SGP40 measure reads failed under the UART load: logged and persisted, below any restart
_SGP40_MEASURE_RAW = 0x260F  # the command whose following read the fault matches, so setup stays healthy
# The silicon floor for the largest block after the full system build (heap_headroom_after_full_system_build.py's
# factor times heap_bounds.py's worst-case allocation), read as data: the load must not fragment the heap below it.
_HEADROOM_SCRIPT = ("tests_hardware/device_scripts", "heap_headroom_after_full_system_build.py", "_WORST_CASE_FACTOR")
_WORST_CASE = ("tests_hardware", "heap_bounds.py", "WORST_CASE_ALLOCATION")
# @tunable web.connections_per_page_load = 2
_CONNECTIONS_PER_PAGE_LOAD = 2  # the real post-inlining footprint of one page load (Part H.7)
_WIFI_SCRIPTED_FAILURES = 5  # asy_wifi_service.py's conn_fail_to_hotspot
_SSID = "digital-twin-test-ssid"
_GMT_OFFSET_DEFAULT = 3600  # the GMTOffset default, which a write of it would answer "Unchanged"
_TEST_WARN_CO2 = 1800  # a WarnCO2 the defaults do not hold
_DNS_UDP_MAX = 512  # RFC 1035's UDP message limit
_SITE_MIN_BYTES = 1000  # a whole page or bundle, not a truncated or empty body
_ISL_RESOLUTIONS = (12, 16)  # asy_isl29125_driver.py's _RESOLUTIONS


class RefusedError(Exception):
    # A clean refusal at the ceiling: the connection reset or closed before any response byte - nothing else is one.
    pass


_SCENARIO_ERRORS = (AssertionError, RefusedError, OSError, HTTPException, ValueError, TypeError, RuntimeError)  # a verdict, never the run's


class Answer(NamedTuple):
    status: int
    headers: "dict[str, str]"
    body: bytes


class Outcome(NamedTuple):
    name: str
    outcome: str  # passed, failed, skipped or deselected
    reason: str


@dataclass(frozen=True)
class Scenario:
    # One registered scenario: its body, its goal (the docstring's first line) and when it runs. `shared`: it may run on
    # a twin the scenario before it used, its own boot having no arguments but the slot lines, persisting no setting,
    # sending no system command and planting no state; `moves`: the error sources it may move there.
    name: str
    body: "Callable[[Context], None]"
    goal: str
    family: str  # the twin-scenario family: a ported scenario's origin file stem, without test_digital_twin_
    drivers: "tuple[str, ...]" = ()
    needs_exclusive_port_53: bool = False
    needs_site: bool = False
    shared: bool = False
    moves: "tuple[str, ...]" = ()


SCENARIOS: "dict[str, Scenario]" = {}


def scenario(name: str, *, family: str, drivers: "tuple[str, ...]" = (), needs_exclusive_port_53: bool = False, needs_site: bool = False, shared: bool = False, moves: "tuple[str, ...]" = ()) -> "Callable[[Callable[[Context], None]], Callable[[Context], None]]":
    # Registers a scenario under `name` in `family`; a body without a goal docstring, a name taken twice, no family, or
    # moved error sources stated by a scenario on its own boot (no idle check reads them) refuses at import.
    def register(body: "Callable[[Context], None]") -> "Callable[[Context], None]":
        goal = (body.__doc__ or "").strip().splitlines()
        if not goal or not goal[0].strip():
            raise ValueError(f"scenario {name!r} has no goal docstring")
        if name in SCENARIOS:
            raise ValueError(f"scenario {name!r} is registered twice")
        if not family.isidentifier():
            raise ValueError(f"scenario {name!r} names no family ({family!r})")
        if moves and not shared:
            raise ValueError(f"scenario {name!r} states moved error sources but runs on its own boot")
        SCENARIOS[name] = Scenario(name, body, goal[0].strip(), family, tuple(drivers), needs_exclusive_port_53, needs_site, shared, tuple(moves))
        return body

    return register


class Twin:
    # One booted twin: its run, its port and the readers of its log's machine lines.
    def __init__(self, run: TwinRun, port: int) -> None:
        self.run = run
        self.port = port
        self.exit_claimed = False  # a scenario that commands the exit checks it itself
        self.starves_watchdog = False  # a scenario that stops the feed itself judges the watchdog's outcome

    def conn_slots(self, timeout_s: float = _DRAIN_WAIT_S) -> "tuple[int, int]":
        # The newest CONN_SLOTS line printed from now on: (open connections, listen backlog).
        line = self.wait_line("CONN_SLOTS ", self.mark(), timeout_s)
        if line is None:
            raise AssertionError("the twin printed no CONN_SLOTS line - boot it with --test-conn-status-interval-ms")
        fields = dict(part.split("=", 1) for part in line.split()[1:])
        return int(fields["open"]), int(fields["backlog"])

    def drained(self, timeout_s: float = _DRAIN_WAIT_S) -> bool:
        # The service's own admission counter back at zero, read from its CONN_SLOTS lines.
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self.conn_slots(timeout_s)[0] == 0:
                return True
        return False

    def mark(self) -> int:
        return len(read_log(self.run.log_path))

    def trigger(self, name: str) -> None:
        send_line(self.run, name)

    def wait_line(self, text: str, since: int, timeout_s: float) -> "str | None":
        # The first log line holding `text` printed after the `since` offset, or None by the deadline.
        deadline = time.monotonic() + timeout_s
        while True:
            for line in log_from(self.run.log_path, since).splitlines():
                if text in line:
                    return line
            if time.monotonic() >= deadline or self.run.proc.poll() is not None:
                return None
            time.sleep(_LINE_POLL_S)


@dataclass
class Context:
    # One scenario's run of one device: what it boots and where its logs and state go.
    device: str
    micropython_bin: str
    gc_threshold: int
    logs_dir: Path
    instances: "tuple[tuple[str, str, str], ...]"  # (key, driver, name_ext) of every bus-attached instance
    ports: "Iterator[int]"
    hostname: str
    boots: int = 0
    failures: "list[str]" = field(default_factory=list)
    shared: "SharedBoot | None" = None

    @contextlib.contextmanager
    def boot(self, *args: str, state_dir: "Path | None" = None) -> "Iterator[Twin]":
        # A twin on a fresh port of this device's band, fresh state unless given, shut down in finally; its log
        # passes the memory gate and refused no public destination, or the scenario fails naming why. A sharing
        # scenario's one boot is the shared twin instead, which outlives it.
        self.boots += 1
        if self.shared is not None:
            if args not in ((), _CONN) or state_dir is not None or self.boots > 1:
                raise RuntimeError(f"a sharing scenario's boot {self.boots} asked for {args!r}, state {state_dir}: it boots once, with no arguments but the slot lines")
            yield self.shared.acquire()
            return
        port = next(self.ports)
        state = state_dir or self.logs_dir / f"state_{self.boots:02d}"
        launch = TwinLaunch(self.micropython_bin, f"sensortask_{self.device}", GENERATED_SRC_DIR / f"sensortask_{self.device}_wiring_plan.json", self.device, HOST, port, self.gc_threshold, _micropypath(self.device))
        run = spawn(launch, state_dir=state, log_path=self.logs_dir / f"twin_{self.boots:02d}.log", args=args)
        twin = Twin(run, port)
        try:
            wait_until_serving(run, HOST, port, _SERVING_TIMEOUT_S)
            yield twin
        finally:
            if run.proc.poll() is None:
                code = shutdown(run, f"{self.device} twin {self.boots}")
                if code != 0 or run.killed:
                    self.failures.append(f"twin {self.boots}: the SIGINT shutdown ended {exit_reason(code, killed=run.killed)} (exit code {code})")
                elif parse_shutdown_line(read_log(run.log_path)) is None:
                    self.failures.append(f"twin {self.boots}: a clean shutdown printed no shutdown line")
            elif not twin.exit_claimed:
                code = wait_exit(run, 0)
                self.failures.append(f"twin {self.boots} ended on its own mid-scenario: {exit_reason(code)} (exit code {code})")
            self.check_log(twin)

    def ceiling(self) -> int:
        return device_max_connections(REPO_ROOT / "devices" / f"{self.device}.toml", SRC_DIR)

    def check_log(self, twin: Twin) -> None:
        verdict = log_memory_verdict(twin.run.log_path)
        if verdict is not None:
            self.failures.append(verdict)
        line = parse_shutdown_line(read_log(twin.run.log_path))
        if line is not None and line.public_destinations_refused != 0:
            self.failures.append(f"twin {self.boots} refused {line.public_destinations_refused} public destination(s)")
        gap = feed_gap_verdict(line) if line is not None and not twin.starves_watchdog else None
        if gap is not None:
            self.failures.append(f"twin {self.boots}: {gap}")

    @property
    def drivers(self) -> "set[str]":
        return {driver for _key, driver, _ext in self.instances}

    @property
    def sensors(self) -> "set[str]":
        return {_SENSOR_NAMES[d] for d in self.drivers if d in _SENSOR_NAMES}


@dataclass
class SharedBoot:
    # The twin consecutive sharing scenarios run on: booted by the first that asks, idle-checked after each, shut down
    # after a failure or at the group's end, so the next sharing scenario boots a fresh one.
    ctx: Context  # the boot's own: its logs, state and shutdown verdict
    stack: contextlib.ExitStack = field(default_factory=contextlib.ExitStack)
    twin: "Twin | None" = None
    counters: "dict[str, int]" = field(default_factory=dict)
    names: "list[str]" = field(default_factory=list)
    reported: int = 0

    def acquire(self) -> Twin:
        if self.twin is None:
            twin = self.stack.enter_context(self.ctx.boot(*_CONN))
            self.counters = {name: _counter(entry) for name, entry in _error_table(twin.port).items()}
            self.twin = twin
        return self.twin

    def idle_problems(self, item: Scenario) -> "list[str]":
        # The twin as a fresh boot would leave the next scenario: running, every slot free, the accept queue empty,
        # no memory marker, and no error count moved since the scenario before but those `item` states.
        twin = self.twin
        if twin is None or twin.run.proc.poll() is not None:
            return ["the twin is no longer running"]
        problems: list[str] = []
        if not twin.drained():
            problems.append(f"a connection slot was still held after {_DRAIN_WAIT_S}s")
        deadline = time.monotonic() + _DRAIN_WAIT_S
        while (queued := _accept_queue(twin.port)) != 0 and time.monotonic() < deadline:
            time.sleep(_LINE_POLL_S)
        if queued != 0:
            problems.append(f"no socket listens on port {twin.port}" if queued is None else f"{queued} connection(s) still in the accept queue after {_DRAIN_WAIT_S}s")
        # Read once every slot is back: a connection's own log entry lands before its slot is released.
        table = _error_table(twin.port)
        counters = {name: _counter(entry) for name, entry in table.items()}
        moved = {name: (self.counters.get(name), counters.get(name)) for name in sorted(set(self.counters) | set(counters)) if self.counters.get(name) != counters.get(name)}
        unstated = {name: (*move, _newest_entries(table.get(name, {}))) for name, move in moved.items() if name not in item.moves}
        if unstated:
            problems.append(f"moved error counts it does not state (before, after, newest entries): {unstated}")
        verdict = log_memory_verdict(twin.run.log_path)
        if verdict is not None:
            problems.append(verdict)
        self.counters = counters
        return problems

    def release(self, item: Scenario, *, failed: bool, last: bool) -> "list[str]":
        # After one sharing scenario: its idle check unless it failed, then the shutdown a failure or the group's end
        # calls for; returns what failed, the idle check naming the scenario and the shutdown the boot's scenarios.
        self.names.append(item.name)
        problems: list[str] = []
        if self.twin is not None and not failed:
            try:
                problems = [f"idle check after {item.name}: {p}" for p in self.idle_problems(item)]
            except _SCENARIO_ERRORS as exc:
                problems = [f"idle check after {item.name}: {type(exc).__name__}: {exc}"]
        if failed or problems or last:
            self.stack.close()  # the boot's SIGINT shutdown and log gate, into self.ctx.failures
            self.twin = None
        problems += [f"shared boot {self.ctx.boots} ({', '.join(self.names)}): {f}" for f in self.ctx.failures[self.reported :]]
        self.reported = len(self.ctx.failures)
        if self.twin is None:
            self.names = []
        return problems


def _get_routes() -> "tuple[str, ...]":
    # The GET paths of the service's one route table, ROUTES, read by ast: a route it gains is driven with no edit here.
    tree = ast.parse((SRC_DIR / _WEBSERVER).read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "ROUTES" and isinstance(node.value, ast.Tuple):
            routes = [elt.elts[1].value for elt in node.value.elts if isinstance(elt, ast.Tuple) and isinstance(elt.elts[0], ast.Constant) and elt.elts[0].value == "GET" and isinstance(elt.elts[1], ast.Constant)]
            return tuple(str(r) for r in routes if r != "/")
    raise RuntimeError(f"src/{_WEBSERVER} defines no ROUTES table")


@scenario("above_max_connections_all_flaky_survives", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _above_max_all_flaky(ctx: Context) -> None:
    """Twice the ceiling of flaky connections leaves the server serving."""
    with ctx.boot() as twin:
        _together(ctx.ceiling() * 2, lambda _i: _flaky(twin.port))
        _still_serving(twin.port)


@scenario("above_max_connections_mixed_healthy_and_flaky_at_least_one_healthy_succeeds", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _above_max_mixed(ctx: Context) -> None:
    """A full ceiling each of healthy and flaky connections: at least one healthy is served, and the server lives."""
    with ctx.boot() as twin:
        ceiling = ctx.ceiling()
        results = _together(ceiling * 2, lambda i: _status_of(twin.port, "/measurements") if i < ceiling else _flaky(twin.port))
        _expect(results[:ceiling].count(HTTPStatus.OK) >= 1, f"no healthy request served: {_statuses(results)}")
        _expect(all(r in (HTTPStatus.OK, "rejected") for r in results[:ceiling]), f"healthy answers: {_statuses(results)}")
        _still_serving(twin.port)


def _accept_queue(port: int) -> "int | None":
    # The kernel's accept queue of the socket listening on `port` (a LISTEN row's rx_queue in /proc/net/tcp*), or
    # None when nothing listens there.
    for table in (Path("/proc/net/tcp"), Path("/proc/net/tcp6")):
        with contextlib.suppress(FileNotFoundError):
            for row in table.read_text(encoding="utf-8").splitlines()[1:]:
                fields = row.split()
                if fields[3] == _TCP_LISTEN and int(fields[1].rsplit(":", 1)[1], 16) == port:
                    return int(fields[4].split(":")[1], 16)
    return None


@scenario("every_admitted_connection_is_actually_served_a_complete_correct_response", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _all_admitted_are_really_served(ctx: Context) -> None:
    """Three full-ceiling rounds over every GET route: each answer complete, equal to an uncontended one, in bounded time."""
    with ctx.boot(*_CONN) as twin:
        routes = _get_routes()
        reference = {path: _json(_request(twin.port, "GET", path)) for path in routes}
        ceiling = ctx.ceiling()
        for round_index in range(3):
            _expect(twin.drained(), f"round {round_index}: the previous round's slots never came back")

            def one(i: int) -> "tuple[str, int, float, JSONValue]":
                path = routes[i % len(routes)]
                started = time.monotonic()
                answer = _request(twin.port, "GET", path)
                return path, answer.status, time.monotonic() - started, _json(answer)

            results = _together(ceiling, one)
            for result in results:
                if result is None or isinstance(result, Exception):
                    raise AssertionError(f"round {round_index}: a request raised or never finished: {result!r}")
                path, status, elapsed, body = result
                _expect(status == HTTPStatus.OK and isinstance(body, dict) and bool(body), f"round {round_index}: {path} answered {status} {body!r}")
                expected = reference[path] if path in _STATIC_VALUE_ROUTES else _key_tree(reference[path])
                got = body if path in _STATIC_VALUE_ROUTES else _key_tree(body)
                _expect(got == expected, f"round {round_index}: {path} under load differs from its uncontended answer")
                _expect(elapsed < _REQUEST_TIMEOUT_S, f"round {round_index}: {path} took {elapsed:.1f}s - admitted but not served in useful time")
        _still_serving(twin.port)


@scenario("a_full_ceiling_of_real_page_loads_is_served_without_truncation", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _all_admitted_page_loads_complete(ctx: Context) -> None:
    """A full ceiling of page loads gets the page byte-identical to one uncontended load."""
    with ctx.boot(*_CONN) as twin:
        reference = _request(twin.port, "GET", "/")
        _expect(reference.status == HTTPStatus.OK and len(reference.body) > 0, f"the uncontended load answered {reference.status}, {len(reference.body)} bytes")
        _expect(twin.drained(), "the reference load's own slot never came back")
        tabs = max(2, ctx.ceiling() // _CONNECTIONS_PER_PAGE_LOAD)
        bodies = _together(tabs * 2, lambda _i: _request(twin.port, "GET", "/").body)
        sizes = [len(b) if isinstance(b, bytes) else repr(b) for b in bodies]
        _expect(all(b == reference.body for b in bodies), f"a concurrent page load differs - uncontended {len(reference.body)} bytes, under load {sizes}")
        _still_serving(twin.port)


@scenario("all_flaky_connections_dont_wedge_the_server", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _all_flaky(ctx: Context) -> None:
    """A full ceiling of flaky connections leaves the server serving."""
    with ctx.boot() as twin:
        _together(ctx.ceiling(), lambda _i: _flaky(twin.port))
        _still_serving(twin.port)


@scenario("api_burst_at_the_ceiling_during_bus_load", family="bus_hazard_concurrency", shared=True)
def _api_burst_during_bus_load(ctx: Context) -> None:
    """A full ceiling of GETs over every route lands while every sensor task is on its bus: all admitted and served."""
    with ctx.boot(*_CONN) as twin:
        for name in ctx.sensors:
            _expect(_wait_reading(twin.port, name), f"{name} never read, so its task is not on the bus yet")
        _expect(twin.drained(), "the readiness probe's slot never came back")
        routes = _get_routes()
        results = _together(ctx.ceiling(), lambda i: _status_of(twin.port, routes[i % len(routes)]))
        _expect(results == [HTTPStatus.OK] * ctx.ceiling(), f"the device refused what its own ceiling admits: {_statuses(results)}")


@scenario("the_accept_queue_is_never_shallower_than_the_admission_ceiling", family="webserver_concurrency")
def _backlog_covers_the_ceiling(ctx: Context) -> None:
    """A full ceiling arriving while the loop is stalled all reaches the server: the listen backlog covers the ceiling."""
    with ctx.boot(*_CONN, "--test-stall-loop-ms", str(_STALL_MS)) as twin:
        ceiling = ctx.ceiling()
        _open_now, backlog = twin.conn_slots()
        _expect(backlog >= ceiling, f"listen backlog {backlog} is shallower than the ceiling {ceiling}")
        _expect(twin.drained(), "the readiness probe's slot never came back")
        since = twin.mark()
        twin.trigger("STALL_TRIGGER")
        time.sleep(_STALL_MS / 2000)  # half the stall: past the runner's stdin poll, so the loop is stopped
        clients = []
        try:
            for _ in range(ceiling):
                client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                clients.append(client)
                client.setblocking(False)
                with contextlib.suppress(BlockingIOError):
                    client.connect((HOST, twin.port))  # EINPROGRESS: the kernel finishes the handshake during the stall
            _expect("STALL" not in log_from(twin.run.log_path, since), "the stall ended before the burst arrived - it proves nothing")
            _expect(twin.wait_line("STALL", since, _DRAIN_WAIT_S) is not None, "the stall never ran")
            deadline = time.monotonic() + _DRAIN_WAIT_S
            reached = 0
            while time.monotonic() < deadline and reached < ceiling:
                reached = twin.conn_slots()[0]
            _expect(reached == ceiling, f"{reached} of a {ceiling}-arrival burst reached the server - the rest waited out a dropped SYN")
        finally:
            for client in clients:
                client.close()
        _expect(twin.drained(), "the burst's slots never came back")


def _band(device: str) -> "tuple[int, int]":
    # The device's block of this harness's port band: its index in the generated devices times an even share,
    # the split tests/_port_bands.py's band_for_device() makes (pinned equal by an L0 test).
    tree = ast.parse((REPO_ROOT / "tests" / "_port_bands.py").read_text(encoding="utf-8"))
    bands = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "BANDS")
    first, last, _protocol = bands[_BAND_OWNER]
    devices = generated_devices()
    size = (last - first + 1) // len(devices)
    start = first + devices.index(device) * size
    return start, start + size - 1


@scenario("connections_beyond_max_connections_are_rejected_cleanly_not_crashed", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _beyond_max_rejected_cleanly(ctx: Context) -> None:
    """Twice the ceiling at once: at least a ceiling's worth served, the rest only cleanly refused, still serving."""
    with ctx.boot(*_CONN) as twin:
        _expect(twin.drained(), "the readiness probe's slot never came back")
        ceiling = ctx.ceiling()
        results = _together(ceiling * 2, lambda _i: _status_of(twin.port, "/measurements"))
        # The first `ceiling` arrivals are admitted and served; no refusal is asserted, since admitted connections
        # finish and free their slots within the burst, so it never exceeds the free slots by a full ceiling.
        _expect(results.count(HTTPStatus.OK) >= ceiling, f"fewer than {ceiling} served: {_statuses(results)}")
        _expect(all(r in (HTTPStatus.OK, "rejected") for r in results), f"an answer other than 200 or a clean refusal: {_statuses(results)}")
        _still_serving(twin.port)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True, type=_device, help="the generated device to boot")
    toolchain = Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain"))
    parser.add_argument("--micropython-bin", default=str(toolchain / "micropython" / "ports" / "unix" / "build-standard" / "micropython"))
    parser.add_argument("--logs-dir", type=Path, help="where each scenario's logs and state go (default: digital_twin_ci_logs/scenarios/<device>)")
    parser.add_argument("--gc-threshold", type=int, default=-1, help="gc.threshold() of every twin booted (default -1)")
    parser.add_argument("--only", type=_run_selection, help="run only these scenarios, comma-separated")
    ports = parser.add_mutually_exclusive_group()
    ports.add_argument("--exclusive-port-53", action="store_true", help="run the DNS scenarios too; the caller holds port 53's lock")
    ports.add_argument("--shared-port-53", action="store_true", help="deselect the DNS scenarios (the default)")
    parser.add_argument("--run-record", type=Path, help="write each scenario's outcome as JSON here")
    return parser


_T = TypeVar("_T")


@scenario("a_real_bus_fault_degrades_to_a_clean_response_not_a_crash", family="sensortask_integration", drivers=("sgp40",))
def _bus_fault_degrades(ctx: Context) -> None:
    """A sustained SGP40 write fault, consumed by real reads, degrades GET /measurements to null fields, never a 500."""
    sgp40 = next(key for key, driver, _ext in ctx.instances if driver == "sgp40")
    times = 1000
    with ctx.boot("--fault", f"{sgp40}:writeto:{times}", "--test-fault-status-interval-ms", str(_FAULT_STATUS_INTERVAL_MS)) as twin:
        deadline = time.monotonic() + _DRAIN_WAIT_S
        consumed = False
        while time.monotonic() < deadline and not consumed:
            line = twin.wait_line("FAULT_PENDING", twin.mark(), _DRAIN_WAIT_S) or ""
            pending = next((int(t.split("=")[1]) for t in line.split()[1:] if t.startswith(f"{sgp40}:writeto=")), times)
            consumed = pending < times and _counter(_errcount(twin.port, "SGP40")) >= 1
        _expect(consumed, "the injected writes were never consumed by a real read before the GET")
        answer = _request(twin.port, "GET", "/measurements")
        _expect(answer.status == HTTPStatus.OK, f"GET /measurements answered {answer.status} under the fault, never a 500")
        block = _object(answer).get("SGP40")
        _expect(isinstance(block, dict) and all(v is None for k, v in block.items() if k != "TS"), f"SGP40's degraded fields are not all null: {block!r}")
        _expect(_counter(_errcount(twin.port, "SGP40")) >= 1, "SGP40's error count holds no entry")


@scenario("a_connection_still_closing_holds_its_slot_after_its_client_has_the_whole_response", family="webserver_concurrency")
def _closing_connection_holds_its_slot(ctx: Context) -> None:
    """With every close held, a ceiling of clients holding whole responses still counts every slot and refuses one more."""
    with ctx.boot(*_CONN, "--test-hold-closing-slot") as twin:
        ceiling = ctx.ceiling()
        # The release is one-shot, so the readiness probe's own held close stays counted and the burst fills the rest.
        _expect(twin.wait_line("SLOT_HELD", 0, _DRAIN_WAIT_S) is not None, "the readiness probe's close was never held")
        probe = twin.conn_slots()[0]
        _expect(0 < probe < ceiling, f"the readiness probe holds {probe} of {ceiling} slots")
        results = _together(ceiling - probe, lambda _i: _request(twin.port, "GET", "/status"))
        _expect(all(isinstance(r, Answer) and r.status == HTTPStatus.OK and _object(r) for r in results), f"held-close answers: {_statuses(results)}")
        held = twin.conn_slots()[0]
        _expect(held == ceiling, f"every response is out but no close finished; all {ceiling} slots must still count, got {held}")
        _expect(_status_of(twin.port, "/measurements") == "rejected", "a request past the held slots was not refused")
        since = twin.mark()
        twin.trigger("SLOT_RELEASE")
        _expect(twin.wait_line("SLOT_RELEASED", since, _DRAIN_WAIT_S) is not None, "the runner never released the held closes")
        _expect(twin.drained(), "the slots never came back once the closes finished")
        _still_serving(twin.port)


@scenario("a_command_right_after_the_first_answer_resets_cleanly", family="system_commands")
def _command_in_the_boot_window(ctx: Context) -> None:
    """A reboot, a config reset and an erase sent at a boot's first answer each end in their reset, the watchdog fed."""
    for cmd, code_name in (("reboot", "_RR_REBOOT"), ("resetconfig", "_RR_CONFIG_RESET"), ("erasefram", "_RR_FRAM_ERASED")):
        state = ctx.logs_dir / f"state_window_{cmd}"
        with ctx.boot(state_dir=state) as twin:
            if cmd == "erasefram":
                _save_fram_evidence(ctx, twin, f"window_{cmd}")
            _expect(_system_cmd(twin.port, cmd) == "Valid", f"{cmd} in the boot window did not answer Valid")
            _exits_with(twin, 3, f"{cmd} in the boot window")
        reason = _reason_after(ctx, state)
        _expect(reason == _src_int(_SYSTEM, code_name), f"{cmd} in the boot window: the relaunch reads ResetReason {reason!r}")


def _commanded_reset_deadline_s() -> float:
    # The controlled shutdown's first step may wait one supervisor period, then the reset's own delay.
    return _src_int(_SYSTEM, "_RESET_DELAY") + _src_int(_SYSTEM, "_TASK_CHECK_TIME") + _COMMANDED_RESET_MARGIN_S


def _config_write(port: int, index: int) -> "tuple[int, JSONValue]":
    # A real stored write: GMTOffset is the NTP client's config-backed field, NTP being in every device's mandatory
    # set; a distinct value per call, the default answering "Unchanged".
    answer = _request(port, "PUT", "/system", {"GMTOffset": _GMT_OFFSET_DEFAULT + 60 * (index + 1)})
    return answer.status, _result(answer, "GMTOffset")


def _counter(entry: JSONValue) -> int:
    value = entry.get("counter") if isinstance(entry, dict) else None
    return value if isinstance(value, int) else -1


def _definitions_text(device: str) -> str:
    return (GENERATED_SRC_DIR / "definitions" / f"{device}.json").read_text(encoding="utf-8")


def _device(text: str) -> str:
    if text not in generated_devices():
        raise argparse.ArgumentTypeError(f"{text!r} is not a generated device {generated_devices()!r} - run scripts/_generate_sensortask_modules.py")
    return text


def _dns_query(qname: str = "captive.example") -> bytes:
    header = struct.pack(">HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0)  # ID, RD, one question
    labels = b"".join(bytes([len(p)]) + p.encode() for p in qname.split("."))
    return header + labels + b"\x00" + struct.pack(">HH", 1, 1)  # QTYPE A, QCLASS IN


@scenario("connections_at_each_count_from_one_to_max_connections_all_succeed", family="webserver_concurrency", shared=True)
def _each_count_up_to_max(ctx: Context) -> None:
    """Every count from one to the ceiling is admitted in full, each round starting from zero open slots."""
    with ctx.boot(*_CONN) as twin:
        for n in range(1, ctx.ceiling() + 1):
            _expect(twin.drained(), f"round {n}: the previous round's slots never came back")
            results = _together(n, lambda _i: _status_of(twin.port, "/measurements"))
            _expect(results.count(HTTPStatus.OK) == n, f"{n} at once: {_statuses(results)}")


@scenario("erasefram_concurrent_with_a_reboot_accepts_exactly_one", family="system_commands", drivers=("fram",))
def _erase_and_reboot(ctx: Context) -> None:
    """An erase concurrent with a reboot: exactly one Valid, the other Failed, the exit code the winner's."""
    _two_at_once(ctx, "erasefram", "reboot", "erase_reboot")


@scenario("erasefram_on_a_silent_chip_stops_short_and_the_device_feeds_on", family="system_commands", drivers=("fram",))
def _erase_silent_chip(ctx: Context) -> None:
    """An erase against a chip that answers nothing is refused or stops at once; either way the watchdog is fed."""
    state = ctx.logs_dir / "state_silent"
    with ctx.boot("--fault", "fram:silent", state_dir=state) as twin:
        _save_fram_evidence(ctx, twin, "silent")
        word = _system_cmd(twin.port, "erasefram")
        escalated = False
        if word == "Failed":  # refused by the preflight: nothing starts, the device serves and feeds on
            deadline = time.monotonic() + _REFUSAL_FEED_S
            while time.monotonic() < deadline and twin.run.proc.poll() is None:
                time.sleep(_LINE_POLL_S)
            escalated = twin.run.proc.poll() is not None  # the dead chip's own supervisor escalation, not the command
            if escalated:
                _exits_with(twin, 3, "the silent chip's escalation after a refused erase")
            else:
                _still_serving(twin.port)
        else:
            _expect(word == "Valid", f"erasefram on a silent chip answered {word!r}")
            _exits_with(twin, 3, "erasefram on a silent chip")
    if word == "Failed":
        line = parse_shutdown_line(read_log(twin.run.log_path))
        _expect(line is not None and line.would_have_triggered_count == 0, f"the watchdog starved after a refused erase ({line!r})")
        reason = _reason_after(ctx, state) if escalated else None
        _expect(not escalated or reason == _src_int(_SYSTEM, "_RR_TASK_BUDGET"), f"the reset after a refused erase reads ResetReason {reason!r}, not the escalation's")
        return
    reason = _reason_after(ctx, state)
    _expect(reason == _src_int(_SYSTEM, "_RR_COMMAND_INCOMPLETE"), f"an erase that could not finish reads ResetReason {reason!r}")


def _errcount(port: int, name: str) -> JSONObject:
    entry = errcount_table(HTTPStatus.OK, _status(port)).get(name)
    if entry is None:
        raise AssertionError(f"GET /status lists no {name} error source")
    return entry


def _error_table(port: int) -> "dict[str, JSONObject]":
    # Every error source's entry from one GET /status, strict: an unusable answer raises.
    return errcount_table(HTTPStatus.OK, _status(port))


@scenario("every_get_endpoint_is_reachable_over_real_http_and_shaped_correctly", family="sensortask_integration", shared=True)
def _every_get_endpoint(ctx: Context) -> None:
    """Every GET route answers 200 in its published shape, the settings routes with the device's own defaults."""
    with ctx.boot() as twin:
        for path in ("/measurements", "/sensors"):
            answer = _request(twin.port, "GET", path)
            _expect(answer.status == HTTPStatus.OK, f"GET {path} answered {answer.status}")
            _not_self_wrapped(_json(answer), ctx.sensors)
        networking = _object(_request(twin.port, "GET", "/networking"))
        expected = {"SSID": "", "PW": "********", "Country": "DE", "Hostname": ctx.hostname, "HotspotPW": "********", "LEDWifiOn": True, "NTPHost": _responder_host(), "NTPOffset": 0, "NTPInterval": 12, "DNSFallback": ""}
        _expect(networking == expected, f"GET /networking {networking!r}, expected {expected!r}")
        system = _object(_request(twin.port, "GET", "/system"))
        build = system.pop("build", None)
        _expect(system == {"DebugLevel": 0, "GMTOffset": _GMT_OFFSET_DEFAULT, "DSTOffset": 3600}, f"GET /system {system!r}")
        _expect(isinstance(build, dict) and all(isinstance(build.get(k), str) and build[k] for k in ("FirmwareVersion", "WebsiteVersion", "BuildDate")), f"GET /system build {build!r}")
        notification = _object(_request(twin.port, "GET", "/notification"))
        _expect((notification.get("WarnCO2"), notification.get("WarnVOC"), notification.get("WarnHum")) == (1600, 350, 65.0), f"GET /notification {notification!r}")
        _expect(set(_status(twin.port)) == {"networking", "system", "notification", "sensors", "errcount"}, "GET /status's top-level blocks")


@scenario("existing_connections_survive_an_overflow_burst_untouched", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _existing_survive_overflow(ctx: Context) -> None:
    """Slow but healthy connections holding half the slots finish with 200 through an overflow burst, which is refused."""
    with ctx.boot(*_CONN) as twin:
        _expect(twin.drained(), "the readiness probe's slot never came back")
        ceiling = ctx.ceiling()
        slow_count = max(2, ceiling // 2)
        slow_results: list[object] = [None] * slow_count
        slow = [threading.Thread(target=lambda i=i: slow_results.__setitem__(i, _slow_put(twin.port, _SLOW_PUT_S))) for i in range(slow_count)]
        for thread in slow:
            thread.start()
        time.sleep(0.3)  # the slow connections open and start reading; their slots are held from here
        # Held connections keep their slots, so this burst exceeds the free slots by a full ceiling: a refusal is due.
        overflow = _together(ceiling - slow_count + ceiling, lambda _i: _status_of(twin.port, "/measurements"))
        for thread in slow:
            thread.join(timeout=_REQUEST_TIMEOUT_S + _SLOW_PUT_S)
        _expect(overflow.count("rejected") >= 1, f"no refusal past the free slots: {_statuses(overflow)}")
        _expect(all(r in (HTTPStatus.OK, "rejected") for r in overflow), f"overflow answers: {_statuses(overflow)}")
        _expect(slow_results == [HTTPStatus.OK] * slow_count, f"a slow connection was disturbed: {slow_results}")


# The boot flag of every scenario that counts slots: the runner's CONN_SLOTS lines.
_CONN = ("--test-conn-status-interval-ms", str(_CONN_STATUS_INTERVAL_MS))


def _exits_with(twin: Twin, expected: int, what: str) -> None:
    twin.exit_claimed = True
    code = wait_exit(twin.run, _commanded_reset_deadline_s())
    _expect(code == expected, f"{what}: {exit_reason(expected)} expected, got {exit_reason(code, killed=twin.run.killed)} (exit code {code})")
    line = parse_shutdown_line(read_log(twin.run.log_path))
    _expect(line is not None and line.would_have_triggered_count == 0, f"{what}: the watchdog starved ({line!r})")


def _expect(condition: object, msg: str) -> None:
    # One assertion of a scenario: the first that fails ends it, named.
    if not condition:
        raise AssertionError(msg)


def _flaky(port: int) -> None:
    # A real connection sending an incomplete request line on purpose, then hanging up: the reclaim path a lossy
    # network or a killed browser tab triggers.
    with socket.create_connection((HOST, port), timeout=_REQUEST_TIMEOUT_S) as sock:
        sock.sendall(b"GET / HTTP/1.1\r\n")
        time.sleep(_FLAKY_HOLD_S)


@scenario("connection_count_fluctuating_in_real_time_server_stays_healthy", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _fluctuating_real_time(ctx: Context) -> None:
    """Healthy and flaky arrivals staggered over real time, health checked during the fluctuation and after."""
    with ctx.boot() as twin:
        plan = [(i * 0.15, "healthy" if i % 3 != 1 else "flaky") for i in range(6)] + [(2 * 0.15 + 0.02, "flaky"), (5 * 0.15 + 0.02, "flaky")]
        results: list[object] = []

        def wave(index: int) -> object:
            delay, kind = plan[index]
            time.sleep(delay)
            if kind == "flaky":
                _flaky(twin.port)
                return None
            return _status_of(twin.port, "/measurements")

        def health(_index: int) -> object:
            for _ in range(4):
                time.sleep(0.25)
                _still_serving(twin.port, timeout_s=3.0)
            return "healthy"

        results = _together(len(plan) + 1, lambda i: wave(i) if i < len(plan) else health(i))
        _expect(results[-1] == "healthy", f"a health check during the fluctuation failed: {results[-1]!r}")
        answers = [r for r, (_d, kind) in zip(results, plan, strict=False) if kind == "healthy"]
        _expect(answers.count(HTTPStatus.OK) >= 1 and all(r in (HTTPStatus.OK, "rejected") for r in answers), f"staggered answers: {_statuses(answers)}")
        _still_serving(twin.port)


def _fresh_dir(path: Path) -> Path:
    # A scenario's or the shared boots' directory, emptied of this run's own scratch from an earlier run.
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def _group(body: JSONObject, name: str) -> JSONObject:
    group = body.get(name)
    if not isinstance(group, dict):
        raise TypeError(f"GET /status carries no {name!r} block ({group!r})")
    return group


def _gunzip(answer: Answer) -> bytes:
    _expect(answer.headers.get("Content-Encoding") == "gzip", f"the site answered with encoding {answer.headers.get('Content-Encoding')!r}")
    return gzip.decompress(answer.body)


@scenario("high_concurrency_burst_at_historical_segfault_repro_scale_survives", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _high_concurrency_burst(ctx: Context) -> None:
    """Five bursts at the scale that once crashed the Unix port: only 200s and clean refusals, serving after each."""
    with ctx.boot() as twin:
        for _round in range(5):  # repeated: the original bug was a race, not an every-time failure
            results = _together(max(12, ctx.ceiling() * 3), lambda _i: _status_of(twin.port, "/measurements"))
            _expect(all(r in (HTTPStatus.OK, "rejected") for r in results), f"burst answers: {_statuses(results)}")
            _still_serving(twin.port)


def _holds_port_53() -> bool:
    # The caller above holds port 53's lock (scripts/_port_lock.sh hands its holders down by environment).
    return str(_DNS_PORT) in os.environ.get("SENSORS_PORT_LOCKS_HELD", "").split()


def _hostname(device: str) -> str:
    model = load_device(REPO_ROOT / "devices" / f"{device}.toml")
    table = model.doc.get("device")
    hostname = table.get("hostname") if isinstance(table, dict) else None
    return hostname if isinstance(hostname, str) else ""


def _hotspot(twin: Twin) -> bool:
    deadline = time.monotonic() + _HOTSPOT_WAIT_S
    while time.monotonic() < deadline:
        if _request(twin.port, "GET", "/generate_204").status == HTTPStatus.FOUND:
            return True
        time.sleep(0.25)
    return False


@scenario("wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server", family="sensortask_integration", needs_exclusive_port_53=True)
def _hotspot_dns(ctx: Context) -> None:
    """Five STA failures drive the hotspot: its DNS server answers an A query with the AP's address, unknown paths redirect."""
    with ctx.boot(*(["--wifi-outcome", "no_ap"] * _WIFI_SCRIPTED_FAILURES)) as twin:
        _request(twin.port, "PUT", "/networking", {"SSID": _SSID})
        deadline = time.monotonic() + _HOTSPOT_WAIT_S
        answer = b""
        while time.monotonic() < deadline and not answer:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(1.0)
                sock.sendto(_dns_query(), (HOST, _DNS_PORT))
                with contextlib.suppress(OSError):
                    answer = sock.recv(1024)
        _expect(bool(answer), "the hotspot's DNS server never answered a query from this host (an off-subnet source is dropped by design)")
        networking = _group(_status(twin.port), "networking")
        _expect(len(answer) <= _DNS_UDP_MAX and answer[:2] == b"\x12\x34" and bool(answer[2] & 0x80), f"the DNS reply is no answer to the query ({len(answer)} bytes)")
        _expect(socket.inet_ntoa(answer[-4:]) == networking.get("IPv4"), f"the A record {socket.inet_ntoa(answer[-4:])} is not the AP's {networking.get('IPv4')!r}")
        redirect = _request(twin.port, "GET", "/generate_204")
        _expect(redirect.status == HTTPStatus.FOUND and redirect.headers.get("Location") == "/", f"/generate_204 in the hotspot answered {redirect.status}")


@scenario("a_hung_shutdown_step_is_ended_by_the_watchdog", family="system_commands")
def _hung_shutdown_steps(ctx: Context) -> None:
    """Each controlled-shutdown step hung from outside: the command answers Valid, no reset follows, the watchdog engages."""
    for step, cmd in _HANG_STEPS:
        if step == "S5erase" and "fram" not in ctx.drivers:
            continue
        with ctx.boot("--test-shutdown-hang", step) as twin:
            twin.starves_watchdog = True
            _expect(twin.wait_line(f"HANG {step}", 0, _DRAIN_WAIT_S) is not None, f"{step}: the runner never armed the hang")
            if step == "S1":  # hung once the supervisor's next pass meets the ended task, which the runner's HUNG line marks
                met = twin.wait_line("HUNG S1", 0, _src_int(_SYSTEM, "_TASK_CHECK_TIME") + _COMMANDED_RESET_MARGIN_S)
                _expect(met is not None, "S1: the supervisor's next pass never met the ended task")
            if cmd == "erasefram":
                _save_fram_evidence(ctx, twin, f"hang_{step}")
            since = twin.mark()
            _expect(_system_cmd(twin.port, cmd) == "Valid", f"{step}: {cmd} did not answer Valid")
            # The step is reached by the reset deadline at the latest; the watchdog engaging within the window past it, with
            # no reset first, is the property under test, so the step ends when the runner prints the engagement.
            engaged = twin.wait_line("WATCHDOG_WOULD_TRIGGER", since, _commanded_reset_deadline_s() + _WATCHDOG_WINDOW_S)
            _expect(twin.run.proc.poll() is None, f"{step}: the device reset although the step hung ({exit_reason(twin.run.proc.returncode or 0)})")
            _expect(engaged is not None, f"{step} ({cmd}): the watchdog did not engage within the reset deadline and its window")
        line = parse_shutdown_line(read_log(twin.run.log_path))
        _expect(line is not None and line.would_have_triggered_count >= 1, f"{step} ({cmd}): the watchdog never engaged ({line!r})")
        _expect(parse_machine_reset_line(read_log(twin.run.log_path)) is None, f"{step} ({cmd}): a reset ran past a hung step")


def _instances(device: str) -> "tuple[tuple[str, str, str], ...]":
    model = load_device(REPO_ROOT / "devices" / f"{device}.toml")
    return tuple(sorted((instance_label(spec.key), spec.driver, spec.name_ext) for spec in model.instances.values() if spec.driver in BUS_ATTACHED_DRIVERS))


@scenario("isl29125_config_put_during_get_loops", family="webserver_requests", drivers=("isl29125",))
def _isl29125_put_during_gets(ctx: Context) -> None:
    """GET /sensors loops on three connections while one PUT changes ISL29125's Resolution: each answer before or after, never a mix."""
    with ctx.boot() as twin:
        before = _object(_request(twin.port, "GET", "/sensors")).get("ISL29125")
        _expect(isinstance(before, dict) and before.get("Resolution") in _ISL_RESOLUTIONS, f"ISL29125's settings {before!r}")
        current = before.get("Resolution") if isinstance(before, dict) else None
        target = next(r for r in _ISL_RESOLUTIONS if r != current)
        stop = threading.Event()

        def reader(_i: int) -> "list[JSONValue]":
            seen: list[JSONValue] = []
            while not stop.is_set():
                seen.append(_object(_request(twin.port, "GET", "/sensors")).get("ISL29125"))
            return seen

        results: list[object] = [None] * 3
        loops = [threading.Thread(target=_record_into, args=(results, i, reader)) for i in range(3)]
        for loop in loops:
            loop.start()
        time.sleep(0.5)
        word = _result(_request(twin.port, "PUT", "/sensors", {"ISL29125": {"Resolution": target}}), "ISL29125", "Resolution")
        time.sleep(0.5)
        stop.set()
        for loop in loops:
            loop.join(timeout=_REQUEST_TIMEOUT_S)
        after = _object(_request(twin.port, "GET", "/sensors")).get("ISL29125")
        _expect(word == "Valid" and isinstance(after, dict) and after.get("Resolution") == target, f"the PUT answered {word!r}, the settings read {after!r}")
        _expect(all(isinstance(r, list) and r for r in results), f"a GET loop raised or never read: {_statuses(results)}")
        seen = [block for r in results if isinstance(r, list) for block in r]
        _expect(bool(seen) and all(block in (before, after) for block in seen), f"a GET saw a mixed ISL29125 block: {[b for b in seen if b not in (before, after)][:2]!r}")


def _json(answer: Answer) -> JSONValue:
    # The body as strict JSON: a duplicate key or a non-finite constant raises, as the firmware's own reader would.
    def no_duplicates(pairs: "list[tuple[str, JSONValue]]") -> JSONObject:
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise ValueError(f"duplicate key in {keys}")
        return dict(pairs)

    def no_constant(name: str) -> JSONValue:
        raise ValueError(f"non-JSON constant {name}")

    parsed: JSONValue = json.loads(answer.body, object_pairs_hook=no_duplicates, parse_constant=no_constant)
    return parsed


def _key_tree(value: JSONValue) -> JSONValue:
    # The nested key sets of a JSON value: what a burst answer must match when its values move with time.
    if isinstance(value, dict):
        return {key: _key_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_key_tree(item) for item in value]
    return None


def _link_roles(device: str) -> "dict[str, str]":
    # Each uart_link instance's role by its key, as its TOML states it.
    model = load_device(REPO_ROOT / "devices" / f"{device}.toml")
    return {instance_label(spec.key): str(spec.fields.get("role", "")) for spec in model.instances.values() if spec.driver == "uart_link"}


@scenario("get_measurements_and_sensors_are_reachable_and_shaped_correctly", family="sensortask_integration", shared=True)
def _measurements_and_sensors_shape(ctx: Context) -> None:
    """GET /measurements and /sensors answer 200, each sensor's block its own fields, never wrapped under its name."""
    with ctx.boot() as twin:
        for path in ("/measurements", "/sensors"):
            answer = _request(twin.port, "GET", path)
            _expect(answer.status == HTTPStatus.OK, f"GET {path} answered {answer.status}")
            _not_self_wrapped(_json(answer), ctx.sensors)


@scenario("mempause_over_real_http_reaches_the_real_fram_manager", family="sensortask_integration", drivers=("fram",))
def _mempause(ctx: Context) -> None:
    """The mempause command over REST answers Valid and GET /status then reports storage paused."""
    with ctx.boot() as twin:
        _expect(_group(_status(twin.port), "system").get("MemPaused") is False, "storage reads paused before the command")
        _expect(_system_cmd(twin.port, "mempause") == "Valid", "mempause did not answer Valid")
        _expect(_group(_status(twin.port), "system").get("MemPaused") is True, "GET /status does not report the pause")


_STATIC_VALUE_ROUTES = ("/networking", "/system", "/notification", "/sensors")  # nothing writes them during the burst


@scenario("mempause_then_reboot_unpauses_on_the_relaunch", family="system_commands", drivers=("fram",))
def _mempause_then_reboot(ctx: Context) -> None:
    """A reboot taken with storage paused answers Valid and the relaunch runs unpaused, its reason the REST reboot."""
    state = ctx.logs_dir / "state_mempause"
    with ctx.boot(state_dir=state) as twin:
        _expect(_system_cmd(twin.port, "mempause") == "Valid", "mempause did not answer Valid")
        _expect(_system_cmd(twin.port, "reboot") == "Valid", "reboot with storage paused did not answer Valid")
        _exits_with(twin, 3, "reboot with storage paused")
    with ctx.boot(state_dir=state) as twin:
        system = _group(_status(twin.port), "system")
        _expect(system.get("MemPaused") is False and system.get("ResetReason") == _src_int(_SYSTEM, "_RR_REBOOT"), f"the relaunch reads {system!r}")


def _micropypath(device: str) -> str:
    # The twin layout with its frozen_modules entry replaced by the device's own built site.
    return TWIN_MICROPYPATH.replace("frozen_modules", f"build/generated_html/{device}")


@scenario("mixed_healthy_and_flaky_connections_dont_wedge_the_server", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _mixed_healthy_and_flaky(ctx: Context) -> None:
    """Half healthy, half flaky connections filling the ceiling: every healthy one is served and the server lives."""
    with ctx.boot(*_CONN) as twin:
        _expect(twin.drained(), "the readiness probe's slot never came back")
        ceiling = ctx.ceiling()
        healthy = ceiling - ceiling // 2
        results = _together(ceiling, lambda i: _status_of(twin.port, "/measurements") if i < healthy else _flaky(twin.port))
        _expect(results[:healthy] == [HTTPStatus.OK] * healthy, f"healthy beside flaky: {_statuses(results)}")
        _still_serving(twin.port)


@scenario("realistic_mixed_traffic_above_the_connection_ceiling_degrades_gracefully", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _mixed_traffic_above_ceiling(ctx: Context) -> None:
    """One tab past the ceiling beside OpenHAB's polling: only 200s and clean refusals, at least one served, serving after."""
    with ctx.boot() as twin:
        tabs = ctx.ceiling() // _CONNECTIONS_PER_PAGE_LOAD + 1
        results = _together(tabs + 1, lambda i: _page_load(twin.port) if i < tabs else _openhab_poll(twin.port))
        flat = [r for group in results if isinstance(group, list) for r in group]
        _expect(len(flat) == 2 * (tabs + 1), f"a group raised: {_statuses(results)}")
        _expect(flat.count(HTTPStatus.OK) >= 1 and all(r in (HTTPStatus.OK, "rejected") for r in flat), f"answers: {flat}")
        _still_serving(twin.port)


@scenario("multiple_browser_like_sessions_concurrently_all_succeed", family="webserver_concurrency", shared=True)
def _multiple_browser_sessions(ctx: Context) -> None:
    """As many browser tabs as the ceiling admits load at once, every request of every tab served."""
    with ctx.boot(*_CONN) as twin:
        _expect(twin.drained(), "the readiness probe's slot never came back")
        tabs = max(2, ctx.ceiling() // _CONNECTIONS_PER_PAGE_LOAD)
        results = _together(tabs, lambda _i: _page_load(twin.port))
        _expect(all(r == [HTTPStatus.OK, HTTPStatus.OK] for r in results), f"tab answers: {_statuses(results)}")



@scenario("n_healthy_concurrent_connections_up_to_max_connections_all_succeed", family="webserver_concurrency", shared=True)
def _n_healthy_up_to_max(ctx: Context) -> None:
    """A full ceiling of healthy simultaneous requests is admitted and answered in full, never refused."""
    with ctx.boot(*_CONN) as twin:
        _expect(twin.drained(), "the readiness probe's slot never came back")
        ceiling = ctx.ceiling()
        results = _together(ceiling, lambda _i: _status_of(twin.port, "/measurements"))
        _expect(results.count(HTTPStatus.OK) == ceiling, f"{ceiling} healthy requests: {_statuses(results)}")


@scenario("negative_content_length_is_refused", family="webserver_requests", shared=True, moves=("WEBSERVER",))
def _negative_content_length(ctx: Context) -> None:
    """A PUT declaring Content-Length -1 with a 3,000-byte body answers 400 and allocates nothing; the device serves on."""
    with ctx.boot() as twin, socket.create_connection((HOST, twin.port), timeout=_REQUEST_TIMEOUT_S) as sock:
        sock.sendall(b"PUT /networking HTTP/1.1\r\nHost: twin\r\nContent-Type: application/json\r\nContent-Length: -1\r\n\r\n" + b"x" * 3000)
        line = sock.makefile("rb").readline()
        _expect(line.split()[1:2] == [b"400"], f"the negative length answered {line!r}")
        _still_serving(twin.port)


def _newest_entries(entry: JSONObject, count: int = 2) -> "list[JSONValue]":
    # The newest non-empty history slots of one error source, (type, num) each, for a failure message.
    history = entry.get("history")
    slots = [(h.get("type"), h.get("num")) for h in history if isinstance(h, dict) and h.get("type") != "N"] if isinstance(history, list) else []
    return [list(slot) for slot in slots[-count:]]


def _not_self_wrapped(payload: JSONValue, expected: "set[str]") -> None:
    # GET /measurements and /sensors carry each sensor's fields directly, not wrapped a second time under its own name.
    _expect(isinstance(payload, dict) and set(payload) >= expected, f"sensor blocks {sorted(payload) if isinstance(payload, dict) else payload!r}, expected at least {sorted(expected)}")
    for name in expected:
        fields = payload[name] if isinstance(payload, dict) else None
        _expect(isinstance(fields, dict) and bool(fields) and name not in fields, f"{name}'s block is self-wrapped or empty: {fields!r}")


def _object(answer: Answer) -> JSONObject:
    parsed = _json(answer)
    if not isinstance(parsed, dict):
        raise TypeError(f"expected a JSON object, got {parsed!r}")
    return parsed


@scenario("realistic_mixed_openhab_polling_and_browser_session_concurrently", family="webserver_concurrency", shared=True)
def _openhab_and_browser(ctx: Context) -> None:
    """OpenHAB polling two endpoints beside open tabs, together filling the ceiling: every request served."""
    with ctx.boot(*_CONN) as twin:
        _expect(twin.drained(), "the readiness probe's slot never came back")
        tabs = max(1, ctx.ceiling() // _CONNECTIONS_PER_PAGE_LOAD - 1)
        results = _together(tabs + 1, lambda i: _page_load(twin.port) if i < tabs else _openhab_poll(twin.port))
        _expect(all(r == [HTTPStatus.OK, HTTPStatus.OK] for r in results), f"answers: {_statuses(results)}")


def _openhab_poll(port: int) -> "list[int | str]":
    # One OpenHAB polling cycle: two concurrent GETs of two REST endpoints.
    out = _together(2, lambda i: _status_of(port, ("/measurements", "/status")[i]))
    return [r if isinstance(r, (int, str)) else repr(r) for r in out]


def _page_load(port: int) -> "list[int | str]":
    # One browser tab's page-load burst: the page and its one bundle, concurrently (Part H.7).
    out = _together(_CONNECTIONS_PER_PAGE_LOAD, lambda i: _status_of(port, ("/", "/js/app.js")[i]))
    return [r if isinstance(r, (int, str)) else repr(r) for r in out]


@scenario("put_pause_time_round_trips_and_counts_down_over_real_http", family="sensortask_integration")
def _pause_time_counts_down(ctx: Context) -> None:
    """PauseTime answers Valid, is no flat setting, and counts down monotonically to zero on GET /status."""
    with ctx.boot() as twin:
        answer = _request(twin.port, "PUT", "/notification", {"PauseTime": 3})
        _expect(_object(answer).get("result") == {"PauseTime": "Valid"}, f"PUT PauseTime answered {answer.body!r}")
        _expect("PauseTime" not in _object(_request(twin.port, "GET", "/notification")), "PauseTime is a live value, never a flat setting")
        first = _group(_status(twin.port), "notification").get("PauseTime")
        _expect(isinstance(first, int) and first > 0, f"PauseTime read {first!r} right after the PUT")
        last, deadline = first, time.monotonic() + _PAUSE_COUNTDOWN_S
        while time.monotonic() < deadline:
            time.sleep(0.5)
            current = _group(_status(twin.port), "notification").get("PauseTime")
            _expect(isinstance(current, int) and isinstance(last, int) and current <= last, f"PauseTime rose from {last!r} to {current!r}")
            last = current
            if current == 0:
                return
        raise AssertionError(f"PauseTime never reached 0 within {_PAUSE_COUNTDOWN_S}s (last {last!r})")


@scenario("realistic_mixed_polling_and_a_concurrent_real_config_write", family="webserver_concurrency")
def _polling_and_config_write(ctx: Context) -> None:
    """OpenHAB polling beside real config writes filling the ceiling: every GET served, every write Valid."""
    with ctx.boot(*_CONN) as twin:
        _expect(twin.drained(), "the readiness probe's slot never came back")
        writes = max(2, ctx.ceiling() - 2)
        results = _together(writes + 1, lambda i: _config_write(twin.port, i) if i < writes else _openhab_poll(twin.port))
        _expect(results[-1] == [HTTPStatus.OK, HTTPStatus.OK], f"polling beside writes: {results[-1]!r}")
        _expect(results[:writes] == [(HTTPStatus.OK, "Valid")] * writes, f"writes: {_statuses(results[:writes])}")
        _still_serving(twin.port)


@scenario("put_round_trips_through_a_real_twin_backed_driver_over_real_http", family="sensortask_integration")
def _put_round_trips(ctx: Context) -> None:
    """PUT /notification WarnCO2 answers Valid, reads back over GET and lands in the module's config file."""
    with ctx.boot() as twin:
        answer = _request(twin.port, "PUT", "/notification", {"WarnCO2": _TEST_WARN_CO2})
        _expect(answer.status == HTTPStatus.OK and _object(answer).get("result") == {"WarnCO2": "Valid"}, f"PUT answered {answer.status} {answer.body!r}")
        _expect(_object(_request(twin.port, "GET", "/notification")).get("WarnCO2") == _TEST_WARN_CO2, "GET /notification does not read the write back")
        stored = json.loads((state_paths(twin.run.state_dir).config_dir / "config_NOTIFY.cfg").read_text(encoding="utf-8"))
        _expect(stored.get("WarnCO2") == _TEST_WARN_CO2, f"config_NOTIFY.cfg holds {stored!r}")


def _reason_after(ctx: Context, state: Path) -> JSONValue:
    with ctx.boot(state_dir=state) as twin:
        return _group(_status(twin.port), "system").get("ResetReason")


@scenario("reboot_and_bootloader_at_once_accept_exactly_one", family="system_commands")
def _reboot_and_bootloader(ctx: Context) -> None:
    """A reboot and a bootloader entry at once: exactly one Valid, the other Failed, the exit code the winner's."""
    _two_at_once(ctx, "reboot", "bootloader", "reboot_bootloader")


def _record_into(results: "list[object]", index: int, call: "Callable[[int], object]") -> None:
    # A thread body: the call's return, or the exception it raised, lands in results[index] - never lost.
    try:
        results[index] = call(index)
    except Exception as exc:  # recorded; the scenario judges each result
        results[index] = exc


@scenario("refusal_at_the_ceiling_is_counted", family="webserver_requests", shared=True, moves=("WEBSERVER",))
def _refusal_counted(ctx: Context) -> None:
    """Every connection refused at a full ceiling adds exactly one to /status HTTPDropped."""
    with ctx.boot(*_CONN) as twin:
        _expect(twin.drained(), "the readiness probe's slot never came back")
        before = _group(_status(twin.port), "networking").get("HTTPDropped")
        _expect(twin.drained(), "the HTTPDropped read's slot never came back")
        # Slow but healthy holders: one that hung up unserved would be a drop of its own.
        ceiling = ctx.ceiling()
        held: list[object] = [None] * ceiling
        holders = [threading.Thread(target=_record_into, args=(held, i, lambda _i: _slow_put(twin.port, _SLOW_PUT_S))) for i in range(ceiling)]
        for thread in holders:
            thread.start()
        deadline = time.monotonic() + _DRAIN_WAIT_S
        while (full := twin.conn_slots()[0] >= ceiling) is False and time.monotonic() < deadline:
            pass
        refused = sum(1 for _ in range(2) if _status_of(twin.port, "/measurements") == "rejected")
        for thread in holders:
            thread.join(timeout=_REQUEST_TIMEOUT_S + _SLOW_PUT_S)
        _expect(full and refused >= 1, f"no connection was refused at a full ceiling (full {full}, refused {refused})")
        _expect(held == [HTTPStatus.OK] * ceiling, f"a holder was not served: {_statuses(held)}")
        _expect(twin.drained(), "the held slots never came back")
        after = _group(_status(twin.port), "networking").get("HTTPDropped")
        # Exact: HTTPDropped sums the last 24 hours in hourly bins, and this twin has run far less than 23 hours.
        _expect(isinstance(before, int) and after == before + refused, f"HTTPDropped {before!r} -> {after!r} after {refused} refusal(s)")


_INLINED_OPEN = '<script type="application/json" id="inlined-definitions">'  # scripts/_stage_website.py's own marker


def _request(port: int, method: str, path: str, body: JSONValue = None, *, timeout_s: float = _REQUEST_TIMEOUT_S, raw: "bytes | None" = None, headers: "dict[str, str] | None" = None) -> Answer:
    # One request on its own connection. A reset or close before any response byte raises RefusedError; a connect
    # refusal (no listener) and every later error propagate.
    conn = HTTPConnection(HOST, port, timeout=timeout_s)
    try:
        conn.connect()
        send_headers = dict(headers or {})
        payload = raw if raw is not None else (json.dumps(body).encode() if body is not None else b"")
        if body is not None and raw is None:
            send_headers["Content-Type"] = "application/json"
        try:
            conn.request(method, path, body=payload, headers=send_headers)
            res = conn.getresponse()
        except _REFUSAL_ERRORS as exc:
            raise RefusedError(repr(exc)) from exc
        data = res.read()
        return Answer(res.status, dict(res.getheaders()), data)
    finally:
        conn.close()


@scenario("reset_errors_over_real_http_is_not_undone_by_a_fram_loggers_later_setup", family="sensortask_integration", drivers=("sgp40",))
def _reset_errors_not_undone(ctx: Context) -> None:
    """A ResetErrors at the first answer of a boot is not undone when the FRAM loggers restore their history afterwards."""
    state = ctx.logs_dir / "state_shared"
    sgp40 = next(key for key, driver, _ext in ctx.instances if driver == "sgp40")
    with ctx.boot("--fault", f"{sgp40}:writeto:1", state_dir=state) as twin:
        deadline = time.monotonic() + _SERVING_TIMEOUT_S
        while time.monotonic() < deadline and not (logged := any(h.get("type") == "E" for h in _errcount(twin.port, "SGP40").get("history", []) if isinstance(h, dict))):  # type: ignore[union-attr]
            time.sleep(0.25)
        _expect(logged, "the injected write fault never logged an SGP40 error, so there is no history to reset")
    with ctx.boot(state_dir=state) as twin:
        answer = _request(twin.port, "PUT", "/status", {"ResetErrors": True}, timeout_s=30.0)
        _expect(answer.status == HTTPStatus.OK, f"ResetErrors at the first answer answered {answer.status}")
        _expect(_wait_reading(twin.port, "SGP40"), "SGP40 never read, so its logger's setup never ran")
        entry = _errcount(twin.port, "SGP40")
        errors = [h for h in entry.get("history", []) if isinstance(h, dict) and h.get("type") == "E"]  # type: ignore[union-attr]
        _expect(_counter(entry) == 0 and not errors, f"the restore brought the pre-reset history back over a reset that answered 200: {entry!r}")


def _responder_host() -> str:
    # The NTP host the runner writes for its local responder (digital_twin/unixport/_offline_ntp_config.py), read by ast.
    tree = ast.parse((REPO_ROOT / "digital_twin" / "unixport" / "_offline_ntp_config.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "_RESPONDER_HOST":
            return str(ast.literal_eval(node.value))
    raise RuntimeError("_offline_ntp_config.py defines no _RESPONDER_HOST")


def _result(answer: Answer, *keys: str) -> JSONValue:
    # The result word of one PUT field, by its key path under "result".
    node: JSONValue = _object(answer).get("result")
    for key in keys:
        node = node.get(key) if isinstance(node, dict) else None
    return node


def _run_one(item: Scenario, ctx: Context, *, group_ends: bool = True) -> Outcome:
    # One scenario's verdict; on a shared boot its idle check, and the shutdown its failure or the group's end needs.
    started = time.monotonic()
    if item.needs_site and not (SITES_DIR / ctx.device / "frozen_html.py").is_file():
        ctx.failures.append(f"build/generated_html/{ctx.device} is not built - run scripts/build_device_websites.sh")
    else:
        try:
            item.body(ctx)
        except _SCENARIO_ERRORS as exc:  # one scenario's verdict, never the run's
            ctx.failures.insert(0, f"{type(exc).__name__}: {exc}")
    if ctx.shared is not None:
        ctx.failures.extend(ctx.shared.release(item, failed=bool(ctx.failures), last=group_ends))
    elapsed = time.monotonic() - started
    if ctx.failures:
        return Outcome(item.name, "failed", "; ".join(ctx.failures) + f" ({elapsed:.1f}s)")
    return Outcome(item.name, "passed", f"{elapsed:.1f}s")


def _run_scenarios(args: argparse.Namespace, summary: Summary) -> int:
    # The selected scenarios in run order, each outcome recorded; the summary block printed on every exit.
    logs_dir = args.logs_dir or REPO_ROOT / "digital_twin_ci_logs" / "scenarios" / args.device
    first, last = _band(args.device)
    ports = iter(range(first, last + 1))
    outcomes: list[Outcome] = []
    exit_code = _EXIT_FAIL
    shared: SharedBoot | None = None
    try:
        ordered = run_order(select(args.device, args.only, exclusive_port_53=args.exclusive_port_53))
        group_ends = {group[-1] for group in shared_groups(ordered)}
        for item, why_not in ordered:
            if why_not is not None:
                kind, reason = why_not.split(": ", 1)
                outcomes.append(Outcome(item.name, kind, reason))
                continue
            scenario_dir = _fresh_dir(logs_dir / item.name)
            ctx = Context(args.device, args.micropython_bin, args.gc_threshold, scenario_dir, _instances(args.device), ports, _hostname(args.device))
            if item.shared:
                shared = shared or SharedBoot(replace(ctx, logs_dir=_fresh_dir(logs_dir / _SHARED_DIR), failures=[]))
                ctx.shared = shared
            print(f"== {item.name}: {item.goal}", flush=True)
            outcome = _run_one(item, ctx, group_ends=item.name in group_ends)
            print(f"{outcome.outcome.upper()}: {item.name} - {outcome.reason}", flush=True)
            outcomes.append(outcome)
        for outcome in outcomes:
            summary.add(outcome.outcome, outcome.name, outcome.reason if outcome.outcome != "passed" else "")
        if args.run_record is not None:
            args.run_record.write_text(json.dumps([o._asdict() for o in outcomes], indent=2), encoding="utf-8")
        exit_code = _EXIT_FAIL if any(o.outcome == "failed" for o in outcomes) or not any(o.outcome == "passed" for o in outcomes) else 0
    finally:
        if shared is not None:
            shared.stack.close()  # a run cut short leaves no twin behind
        exit_code = summary.print(exit_code)
    return exit_code


def _run_selection(text: str) -> frozenset[str]:
    names = frozenset(part.strip() for part in text.split(",") if part.strip())
    unknown = sorted(names - set(SCENARIOS))
    if not names or unknown:
        raise argparse.ArgumentTypeError(f"unknown scenario(s) {unknown or [text]!r}")
    return names


def _save_fram_evidence(ctx: Context, twin: Twin, label: str) -> None:
    # Before any erasefram: the errcount table over REST and a copy of the FRAM state file (CLAUDE.md's FRAM-log rule).
    evidence = ctx.logs_dir / f"fram_evidence_{label}"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "errcount.json").write_text(json.dumps(_status(twin.port).get("errcount"), indent=2), encoding="utf-8")
    fram = state_paths(twin.run.state_dir).fram
    if fram.exists():
        shutil.copy2(fram, evidence / fram.name)


@scenario("sensors_put_round_trips_a_real_scd30_field_over_real_http", family="sensortask_integration", drivers=("scd30",))
def _sensors_put_scd30(ctx: Context) -> None:
    """PUT /sensors SCD30 MeasInterval answers Valid through the SCD30 reader's own schema."""
    with ctx.boot() as twin:
        answer = _request(twin.port, "PUT", "/sensors", {"SCD30": {"MeasInterval": 4}})
        _expect(answer.status == HTTPStatus.OK and _object(answer).get("result") == {"SCD30": {"MeasInterval": "Valid"}}, f"PUT answered {answer.status} {answer.body!r}")


@scenario("a_full_ceiling_of_concurrent_request_bodies_is_answered_correctly", family="webserver_concurrency")
def _simultaneous_bodies(ctx: Context) -> None:
    """A full ceiling of real writes, then bodies at the cap answered, then one byte over refused with 413 or a reset."""
    with ctx.boot(*_CONN) as twin:
        ceiling = ctx.ceiling()
        _expect(twin.drained(), "the readiness probe's slot never came back")
        writes = _together(ceiling, lambda i: _config_write(twin.port, i))
        _expect(writes == [(HTTPStatus.OK, "Valid")] * ceiling, f"writes: {_statuses(writes)}")
        cap = _src_int(_WEBSERVER, "_DEFAULT_MAX_CONTENT_LENGTH")
        padding = cap - len(json.dumps({"NTPHost": ""}))

        def sized(nbytes: int) -> "int | str":
            try:
                answer = _request(twin.port, "PUT", "/networking", {"NTPHost": "x" * nbytes})
            except RefusedError:
                return "rejected"  # a 413 over a body it never read can arrive as a reset
            if answer.status == HTTPStatus.OK:
                word = _result(answer, "NTPHost")
                return answer.status if word == "Invalid" else f"200 {word!r}"  # the padded host is out of range
            return answer.status

        _expect(twin.drained(), "the first burst's slots never came back")
        at_cap = _together(ceiling, lambda _i: sized(padding))
        _expect(at_cap == [HTTPStatus.OK] * ceiling, f"bodies at the cap: {_statuses(at_cap)}")
        _expect(twin.drained(), "the at-cap burst's slots never came back")
        over = _together(ceiling, lambda _i: sized(padding + 1))
        _expect(all(r in (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "rejected") for r in over), f"bodies one byte over: {_statuses(over)}")
        _still_serving(twin.port)


@scenario("real_website_inlined_definitions_matches_the_booted_devices_own", family="real_website_integration", needs_site=True, shared=True)
def _site_definitions(ctx: Context) -> None:
    """The page inlines the booted device's own generated definitions verbatim; no separate definitions route exists."""
    with ctx.boot() as twin:
        unmatched = _request(twin.port, "GET", "/definitions.json")  # 404, or in the unconfigured hotspot the redirect
        _expect(unmatched.status == HTTPStatus.NOT_FOUND or (unmatched.status == HTTPStatus.FOUND and unmatched.headers.get("Location") == "/"), f"/definitions.json answered {unmatched.status}: a separate route again")
        body = _gunzip(_request(twin.port, "GET", "/")).decode()
        start = body.index(_INLINED_OPEN) + len(_INLINED_OPEN)
        inlined = body[start : body.index("</script>", start)]
        _expect(inlined == _definitions_text(ctx.device).replace("<", "\\u003c"), f"the inlined definitions are not {ctx.device}'s own")



@scenario("a_full_ceiling_of_concurrent_real_page_loads_all_serve_the_real_website", family="real_website_integration", needs_site=True, shared=True)
def _site_full_ceiling(ctx: Context) -> None:
    """The ceiling's worth of real page loads at once: every tab gets the whole page and bundle, identical for all."""
    with ctx.boot(*_CONN) as twin:
        _expect(twin.drained(), "the readiness probe's slot never came back")
        tabs = max(1, ctx.ceiling() // _CONNECTIONS_PER_PAGE_LOAD)

        def tab(_i: int) -> "tuple[int, int]":
            pair = _together(_CONNECTIONS_PER_PAGE_LOAD, lambda j: len(_gunzip(_request(twin.port, "GET", ("/", "/js/app.js")[j]))))
            if not all(isinstance(n, int) for n in pair):
                raise AssertionError(f"a request of the tab failed: {pair!r}")
            return int(str(pair[0])), int(str(pair[1]))

        sizes = _together(tabs, tab)
        _expect(all(isinstance(s, tuple) and s[0] > _SITE_MIN_BYTES and s[1] > _SITE_MIN_BYTES for s in sizes), f"tab sizes {_statuses(sizes)}")
        _expect(len(set(sizes)) == 1, f"the tabs got different content: {sizes}")


@scenario("real_website_put_to_unmatched_path_in_hotspot_mode_still_405", family="real_website_integration", needs_site=True, shared=True)
def _site_hotspot_put_405(ctx: Context) -> None:
    """A PUT to an unmatched path answers 405 in the hotspot too - never a hang, a redirect or a crash."""
    with ctx.boot() as twin:
        _expect(_hotspot(twin), "the unconfigured device never ran its hotspot")
        answer = _request(twin.port, "PUT", "/generate_204", {})
        _expect(answer.status == HTTPStatus.METHOD_NOT_ALLOWED, f"PUT /generate_204 answered {answer.status}")


@scenario("real_website_hotspot_mode_redirects_unmatched_path_to_root", family="real_website_integration", needs_site=True, shared=True)
def _site_hotspot_redirect(ctx: Context) -> None:
    """A device with no station configured runs its hotspot, where an unmatched path redirects to the page."""
    with ctx.boot() as twin:
        _expect(_hotspot(twin), "the unconfigured device never redirected an unmatched path")
        redirect = _request(twin.port, "GET", "/generate_204")
        _expect(redirect.headers.get("Location") == "/", f"the redirect points to {redirect.headers.get('Location')!r}")


@scenario("real_website_hotspot_mode_still_serves_real_index_and_real_api_route", family="real_website_integration", needs_site=True, shared=True)
def _site_hotspot_serves(ctx: Context) -> None:
    """In the hotspot the real page and the real API still answer: the redirect fires only for unmatched paths."""
    with ctx.boot() as twin:
        _expect(_hotspot(twin), "the unconfigured device never ran its hotspot")
        _expect(b"Sensor Station" in _gunzip(_request(twin.port, "GET", "/")), "the hotspot redirected the real page")
        _expect(set(_object(_request(twin.port, "GET", "/measurements"))) == ctx.sensors, "the hotspot shadowed /measurements")


@scenario("real_website_dynamic_hotspot_toggle_switches_redirect_behavior_live", family="real_website_integration", needs_site=True)
def _site_hotspot_toggle(ctx: Context) -> None:
    """One live server follows the phase at request time: hotspot redirects, a station attempt does not, the hotspot again."""
    with ctx.boot(*(["--wifi-outcome", "no_ap"] * _WIFI_SCRIPTED_FAILURES)) as twin:
        _expect(_hotspot(twin), "the unconfigured device never ran its hotspot")
        _request(twin.port, "PUT", "/networking", {"SSID": _SSID})  # credentials: a fresh station attempt
        deadline = time.monotonic() + _HOTSPOT_WAIT_S
        seen_seeking = False
        while time.monotonic() < deadline and not seen_seeking:
            seen_seeking = _request(twin.port, "GET", "/generate_204").status == HTTPStatus.NOT_FOUND
        _expect(seen_seeking, "the station attempt never stopped the redirect")
        _expect(_hotspot(twin), "five failed station attempts never brought the hotspot back")



@scenario("real_website_production_js_entry_is_served_not_the_prototype", family="real_website_integration", needs_site=True, shared=True)
def _site_js(ctx: Context) -> None:
    """The served app bundle is the production entry, not the mock prototype."""
    with ctx.boot() as twin:
        body = _gunzip(_request(twin.port, "GET", "/js/app.js"))
        _expect(b"installMockFetch" not in body and b"definitions.json" in body, "the served js/app.js is the prototype")



@scenario("real_website_static_mount_never_shadows_a_real_api_route", family="real_website_integration", needs_site=True, shared=True)
def _site_never_shadows(ctx: Context) -> None:
    """With the real site mounted, GET /measurements still answers the device's own sensor blocks."""
    with ctx.boot() as twin:
        blocks = _object(_request(twin.port, "GET", "/measurements"))
        _expect(set(blocks) == ctx.sensors, f"/measurements carries {sorted(blocks)}, the device's sensors are {sorted(ctx.sensors)}")


@scenario("real_website_root_serves_the_actual_production_index_html", family="real_website_integration", needs_site=True, shared=True)
def _site_root(ctx: Context) -> None:
    """GET / serves the device's real production index.html, gzip-encoded."""
    with ctx.boot() as twin:
        body = _gunzip(_request(twin.port, "GET", "/"))
        _expect(b"Sensor Station" in body, "the served index.html is not the production page")


def _slow_put(port: int, delay_s: float) -> int:
    # A harmless PUT (an empty /system body) trickled in two halves, so it stays in flight for `delay_s`.
    with socket.create_connection((HOST, port), timeout=_REQUEST_TIMEOUT_S + delay_s) as sock:
        body = b"{}"
        head = f"PUT /system HTTP/1.1\r\nHost: twin\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n".encode()
        sock.sendall(head + body[:1])
        time.sleep(delay_s)
        sock.sendall(body[1:])
        line = sock.makefile("rb").readline()
    return int(line.split()[1])


def _src_int(filename: str, name: str) -> int:
    return module_int_const(SRC_DIR, filename, name)


@scenario("a_slot_freed_by_a_stale_connections_timeout_accepts_a_new_connection", family="webserver_concurrency", shared=True, moves=("WEBSERVER",))
def _stale_slot_reclaimed(ctx: Context) -> None:
    """A full ceiling of silent connections refuses the next; once the server's own cap reclaims them it serves again."""
    with ctx.boot(*_CONN) as twin:
        _expect(twin.drained(), "the readiness probe's slot never came back")
        hanging = [socket.create_connection((HOST, twin.port), timeout=_REQUEST_TIMEOUT_S) for _ in range(ctx.ceiling())]
        try:
            time.sleep(0.2)
            _expect(_status_of(twin.port, "/measurements") == "rejected", "a request past a full ceiling of held slots was not refused")
            outer_cap = module_float_const(SRC_DIR, _WEBSERVER, "_DEFAULT_OUTER_CAP_S")
            _still_serving(twin.port, timeout_s=outer_cap + _STILL_SERVING_S)
        finally:
            for sock in hanging:
                sock.close()


@scenario("static_site_is_served_over_real_http", family="sensortask_integration", shared=True)
def _static_site_served(ctx: Context) -> None:
    """GET / serves the device's site, behind every API route."""
    with ctx.boot() as twin:
        answer = _request(twin.port, "GET", "/")
        _expect(answer.status == HTTPStatus.OK and len(answer.body) > 0, f"GET / answered {answer.status}, {len(answer.body)} bytes")


def _status(port: int) -> JSONObject:
    answer = _request(port, "GET", "/status")
    if answer.status != HTTPStatus.OK:
        raise AssertionError(f"GET /status answered {answer.status}")
    return _object(answer)


def _status_of(port: int, path: str) -> "int | str":
    # A status, or "rejected" for a clean refusal at the ceiling.
    try:
        return _request(port, "GET", path).status
    except RefusedError:
        return "rejected"


def _statuses(results: "Sequence[object]") -> "list[object]":
    return [r if isinstance(r, (int, str, tuple, list)) else repr(r) for r in results]


_HANG_STEPS = (("S1", "reboot"), ("S2", "reboot"), ("S3", "reboot"), ("S4", "reboot"), ("S6", "reboot"), ("S6", "bootloader"), ("S5reset", "resetconfig"), ("S5erase", "erasefram"))


def _still_serving(port: int, timeout_s: float = _STILL_SERVING_S) -> None:
    # Retries only a clean refusal (the ceiling's close lag); any other error raises at once, and a budget run out
    # raises naming the last refusal.
    deadline = time.monotonic() + timeout_s
    last = "no attempt"
    while True:
        try:
            status = _request(port, "GET", "/measurements").status
            if status == HTTPStatus.OK:
                return
            last = f"status {status}"
        except RefusedError as exc:
            last = f"refused ({exc})"
        if time.monotonic() >= deadline:
            raise AssertionError(f"the twin stopped serving: {last} after {timeout_s}s")
        time.sleep(0.1)


def _system_cmd(port: int, cmd: str) -> JSONValue:
    return _result(_request(port, "PUT", "/system", {"SystemCmd": cmd}), "SystemCmd")


def _together(count: int, call: "Callable[[int], _T]", timeout_s: float = 60.0) -> "list[_T | Exception | None]":
    # `count` calls from as many threads behind one barrier, so the burst is truly simultaneous; each result is the
    # call's return, the exception it raised, or None for a call still running past the join.
    results: list[_T | Exception | None] = [None] * count
    barrier = threading.Barrier(count)

    def one(index: int) -> None:
        try:
            barrier.wait(timeout=timeout_s)
            results[index] = call(index)
        except Exception as exc:  # recorded per call; the scenario judges each result
            results[index] = exc

    threads = [threading.Thread(target=one, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=timeout_s + 5.0)
    return results


def _two_at_once(ctx: Context, first: str, second: str, label: str) -> None:
    # Two commands from two threads at once: exactly one Valid, the other Failed, the exit the winner's.
    with ctx.boot(state_dir=ctx.logs_dir / f"state_{label}") as twin:
        if "erasefram" in (first, second):
            _save_fram_evidence(ctx, twin, label)
        words = _together(2, lambda i: _system_cmd(twin.port, (first, second)[i]))
        _expect(sorted(map(str, words)) == ["Failed", "Valid"], f"{first} and {second} at once answered {words!r}")
        winner = (first, second)[words.index("Valid")]
        _exits_with(twin, 4 if winner == "bootloader" else 3, f"{first} and {second} at once ({winner} won)")


def _uart_load(ctx: Context, twin: Twin) -> None:
    # A hammer one past the ceiling on /status and stored config PUTs every half second, each a flash write, for the window.
    stop = threading.Event()
    puts: list[object] = []

    def hammer(_i: int) -> int:
        served = 0
        while not stop.is_set():
            served += _status_of(twin.port, "/status") == HTTPStatus.OK
        return served

    def flusher(_i: int) -> int:
        index = 0
        while not stop.is_set():  # each a stored change, so each a config flush and its flash stall
            try:
                puts.append(_config_write(twin.port, index % 30)[1])
            except RefusedError:  # the hammer holds the ceiling: a clean refusal, sent again
                time.sleep(_LINE_POLL_S)
                continue
            index += 1
            time.sleep(0.5)
        return index

    hammers = ctx.ceiling() + 1
    results: list[object] = [None] * (hammers + 1)
    threads = [threading.Thread(target=_record_into, args=(results, i, hammer if i < hammers else flusher)) for i in range(hammers + 1)]
    for thread in threads:
        thread.start()
    time.sleep(_UART_LOAD_S)
    stop.set()
    for thread in threads:
        thread.join(timeout=_REQUEST_TIMEOUT_S * 2)
    _expect(all(isinstance(r, int) for r in results) and sum(int(str(r)) for r in results[:hammers]) > 0, f"a load thread raised or never ran: {_statuses(results)}")
    _expect(bool(puts) and all(word in ("Valid", "Unchanged") for word in puts), f"config PUTs under load answered {puts!r}")


def _uart_load_round(ctx: Context, hold: int, *, stall_max: bool) -> int:
    # One boot under the load at one stall time; returns its longest flash stall. A typical stall never reaches the link
    # timeout, so nothing fails, and it carries the over-cap offer; a maximum one may outlast it (counted, J.5).
    sgp40 = next((key for key, driver, _ext in ctx.instances if driver == "sgp40"), None)
    fault = ("--fault", f"{sgp40}:readfrom_into:{_UART_LOAD_FAULTS}:{_SGP40_MEASURE_RAW:04X}") if sgp40 and "fram" in ctx.drivers else ()
    stall = "maximum" if stall_max else "typical"
    links = {key: ext for key, driver, ext in ctx.instances if driver == "uart_link"}
    initiators = sorted(key for key, role in _link_roles(ctx.device).items() if role == "initiator")
    with ctx.boot(*_CONN, *fault, "--test-flash-stall-max" if stall_max else "--test-uart-over-cap") as twin:
        _uart_load(ctx, twin)
        if fault:
            _expect(_counter(_errcount(twin.port, "SGP40")) >= 1, f"{stall} stall: the FRAM-log fault never logged, so no log write ran under the load")
        if not stall_max:
            offers = [line.split()[1:] for line in log_from(twin.run.log_path, 0).splitlines() if line.startswith("UART_OVER_CAP ")]
            _expect(sorted(offers) == [[key, "refused"] for key in initiators], f"the over-cap offers ended {offers}, not one refusal per initiating link {initiators}")
            refusals = {_src_int("asy_uart_comm.py", name) for name in ("_ERR_UART_PAYLOAD_TOO_LARGE", "_ERR_UART_TRANSFER_CAP")}
            for key in initiators:
                entry = _errcount(twin.port, f"UART_{links[key]}")
                history = entry.get("history")
                logged = [item for item in (history if isinstance(history, list) else []) if isinstance(item, dict) and item.get("type") == "E" and item.get("num") in refusals]
                _expect(len(logged) == 1, f"{key}: the refused over-cap train logged {len(logged)} time(s), not once ({entry!r})")
    line = parse_shutdown_line(read_log(twin.run.log_path))
    if line is None:
        raise AssertionError(f"{stall} stall: the twin printed no shutdown line")
    _expect(set(line.uart) == set(links), f"the shutdown line names links {sorted(line.uart)}, the device wires {sorted(links)}")
    _expect(0 < line.flash_stall_longest_ms <= hold, f"{stall} stall: the longest flash stall {line.flash_stall_longest_ms} ms is outside (0, {hold}]")
    for key, counts in line.uart.items():
        _expect(counts.rx_laps_and_errors == 0, f"{stall} stall, {key}: {counts.rx_laps_and_errors} ring laps or receive errors under load")
        _expect(stall_max or counts.failures == 0, f"{key}: {counts.failures} failed transfer(s) for stalls shorter than the link timeout")
    _expect(max(c.transfers for c in line.uart.values()) > 0, f"{stall} stall: no link exercised under load: {line.uart}")
    floor = module_int_const(REPO_ROOT / _HEADROOM_SCRIPT[0], *_HEADROOM_SCRIPT[1:]) * module_int_const(REPO_ROOT / _WORST_CASE[0], *_WORST_CASE[1:])
    # The floor is a layout claim, which the threshold stage carries (SPECIFICATION.md I.4(f)): at -1 the reactive collect
    # scatters the run's survivors over the twin's whole heap (11,872-30,080 B largest of 870 KB free, 752 KB at 32768), so
    # that stage prints the block and asserts nothing on it (agent, 2026-10-15).
    print(f"{stall} stall: the largest free block after the load is {line.largest_free_block_bytes} B (floor {floor} B at the threshold stage)")
    _expect(ctx.gc_threshold == -1 or line.largest_free_block_bytes >= floor, f"{stall} stall: the largest free block {line.largest_free_block_bytes} B after the load is below the {floor} B floor")
    return line.flash_stall_longest_ms


@scenario("uart_ring_under_concurrent_load", family="uart_load", drivers=("uart_link",))
def _uart_ring_under_load(ctx: Context) -> None:
    """Both links exercise through a ceiling hammer, FRAM-log writes and config flushes at the typical then the maximum flash stall: no overrun, a train past the cap refused once, the heap unfragmented."""
    hold = _src_int("asy_uart_comm.py", "_FLASH_HOLD_MAX_MS")
    typical = _uart_load_round(ctx, hold, stall_max=False)
    longest = _uart_load_round(ctx, hold, stall_max=True)
    _expect(longest > typical, f"the maximum stall's longest flush {longest} ms is no longer than the typical {typical} ms: the flag did not reach the stall")


def _wait_reading(port: int, name: str, timeout_s: float = _SERVING_TIMEOUT_S) -> bool:
    # A module's /measurements block carries a value: its read task has run, so its setup did.
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        block = _object(_request(port, "GET", "/measurements")).get(name)
        if isinstance(block, dict) and any(v is not None for k, v in block.items() if k != "TS"):
            return True
        time.sleep(0.25)
    return False


def main(argv: "list[str] | None" = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.exclusive_port_53 and not _holds_port_53():
        print("error: --exclusive-port-53 needs port 53's lock held by the caller (scripts/run_digital_twin_ci.sh takes it)", file=sys.stderr)
        return _USAGE_EXIT
    summary = Summary("scripts/_digital_twin_scenarios.py", unit="scenarios", levels=f"L2 ({args.device})", gc_stage=str(args.gc_threshold))
    try:
        # Every boot's captive DNS binds port 53: held for the whole run, or passed when a runner above holds it.
        with port_lock(_DNS_PORT, _LOCK_RUNNER):
            return _run_scenarios(args, summary)
    except PortHeldError as exc:
        print(f"error: {exc}", file=sys.stderr)
        summary.add("failed", f"port {_DNS_PORT}", str(exc))
        return summary.print(_EXIT_FAIL)


def generated_devices() -> "list[str]":
    # Every device buildgen generated a wiring plan for, by name.
    prefix, suffix = "sensortask_", "_wiring_plan.json"
    return sorted(p.name[len(prefix) : -len(suffix)] for p in GENERATED_SRC_DIR.glob(f"{prefix}*{suffix}"))


def run_order(chosen: "list[tuple[Scenario, str | None]]") -> "list[tuple[Scenario, str | None]]":
    # (shared group, name): the sharing scenarios that run come first, so they run on one twin, then the rest; each
    # part keeps the registry's order, the file's D.15 one.
    return sorted(chosen, key=lambda pair: not (pair[0].shared and pair[1] is None))


def select(device: str, only: "frozenset[str] | None", *, exclusive_port_53: bool) -> "list[tuple[Scenario, str | None]]":
    # Every registered scenario with why it does not run (None: it runs): a driver the device does not wire, a
    # shared port 53, or not named by --only.
    drivers = {driver for _key, driver, _ext in _instances(device)}
    chosen: list[tuple[Scenario, str | None]] = []
    for item in SCENARIOS.values():
        if only is not None and item.name not in only:
            continue
        missing = [d for d in item.drivers if d not in drivers]
        if missing:
            chosen.append((item, f"skipped: device wires no {', '.join(missing)}"))
        elif item.needs_exclusive_port_53 and not exclusive_port_53:
            chosen.append((item, "deselected: needs exclusive port 53 - run_digital_twin_ci.sh runs it"))
        else:
            chosen.append((item, None))
    return chosen


def shared_groups(ordered: "list[tuple[Scenario, str | None]]") -> "list[list[str]]":
    # The runs of consecutive sharing scenarios among those that run, by name: each group runs on one twin.
    groups: list[list[str]] = []
    previous = False
    for item, why_not in ordered:
        if why_not is not None:
            continue
        if item.shared and not previous:
            groups.append([])
        if item.shared:
            groups[-1].append(item.name)
        previous = item.shared
    return groups


if __name__ == "__main__":
    raise SystemExit(main())
