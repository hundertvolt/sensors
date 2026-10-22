"""Bench-tier automated tests: the UART crossover link under the full production HTTP stack and
concurrent API load - the realistic deployed condition, where link work and request handling have
to coexist rather than each merely work alone (SPECIFICATION.md Part E.6)."""

import ast
import threading
import time
from typing import TYPE_CHECKING

import _load
import http_client
import pytest
from error_log_helpers import assert_no_task_ended, errcount_entry, get_errcount, reset_all_error_logs
from harness import DEVICE_SCRIPTS_DIR, SRC_DIR, parse_facts, restore_board_to_serving, wait_for_script_server, wait_until

if TYPE_CHECKING:
    from bench_control import BenchBridge
    from harness import Board
    from http_client import JSONObject

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("uart_link", "uart_load")

# GET only: every worker below hits a read-only endpoint, so nothing here can persist to flash in a
# loop. A PUT belongs in this tier only where it is documented command-only and never persisted.
# @tunable l4.uart_link_under_api_load_get_workers = 2
_GET_WORKERS = 2
# @tunable l4.uart_link_under_api_load_get_iterations = 10
_GET_ITERATIONS_PER_WORKER = 10
# Generous next to a single request's own budget, but far below the point at which a stalled link
# would look like a slow one: the claim is coexistence, not a latency number.
# @tunable l4.uart_link_under_api_load_request_budget_s = 15.0
_REQUEST_BUDGET_S = 15.0
# The echo test's readers' answered floor: of the 3 readers x 30 reads it sends, a third, since the script's own boot
# and handover eat into the window the readers run in.
# @tunable l4.uart_link_under_api_load_echo_min_answered = 30
_ECHO_MIN_ANSWERED = 30
# @tunable l4.uart_link_under_api_load_echo_readers = 3
_ECHO_READERS = 3
# @tunable l4.uart_link_under_api_load_echo_iterations = 30
_ECHO_ITERATIONS = 30

# @tunable l4.uart_link_under_api_load_join_timeout_s = 120.0
_JOIN_TIMEOUT_S = 120.0
# @tunable l4.uart_link_under_api_load_probe_timeout_s = 10.0
_PROBE_TIMEOUT_S = 10.0
# @tunable l4.uart_link_under_api_load_wait_timeout_s = 30.0
_WAIT_TIMEOUT_S = 30.0
# @tunable l4.uart_link_under_api_load_wait_poll_s = 2.0
_WAIT_POLL_S = 2.0
# @tunable l4.uart_link_under_api_load_short_join_timeout_s = 60.0
_SHORT_JOIN_TIMEOUT_S = 60.0
# @tunable l4.uart_link_under_api_load_burst_workers = 6
_BURST_WORKERS = 6
# @tunable l4.uart_link_under_api_load_echo_script_timeout_s = 240.0
_ECHO_SCRIPT_TIMEOUT_S = 240.0
# The hazard run (owner, 2026-10-21, asked "Leave the UART hazards under API load untested?": "b - system shall be
# proven stable unter max load allover"): 208 s at dev's 1000 ms reply budget on the twin's driven clock; the bound
# leaves silicon's own load room (agent, 2026-10-21).
# @tunable l4.uart_link_under_api_load_hazard_run_timeout_s = 600.0
_HAZARD_RUN_TIMEOUT_S = 600.0
_TOML_HINT = "check the bench device's TOML still declares its uart_link instances and this build used it"


def test_the_link_stays_healthy_while_the_api_is_hammered(board: "Board", dut_ip: str, request: pytest.FixtureRequest) -> None:
    check_link_healthy_under_load(dut_ip, request.node.name)


def test_real_transfers_complete_while_the_api_is_hammered(board: "Board", dut_ip: str) -> None:
    check_transfers_under_load(dut_ip)


def test_an_api_overload_does_not_corrupt_the_link_or_the_reverse(board: "Board", dut_ip: str, request: pytest.FixtureRequest) -> None:
    check_overload_does_not_corrupt(dut_ip, request.node.name)


def test_a_multi_chunk_set_echoes_intact_under_serving_load(board: "Board", bench: "BenchBridge", dut_ip: str) -> None:
    # The serving board's own initiator SETs and GETs a three-chunk echo while the host loads its API: every echo intact,
    # the exerciser's own transfers failing none meanwhile, and the readers answered.
    load = _load.Load()
    stop = threading.Event()
    driver = threading.Thread(target=_echo_load, args=(dut_ip, stop, load), name="echo-load")
    try:
        driver.start()
        output = board.run_isolated(DEVICE_SCRIPTS_DIR / "uart_link_echo_under_serving_load.py", timeout_s=_ECHO_SCRIPT_TIMEOUT_S)
    finally:
        stop.set()
        alive = _load.join([driver], 2 * _JOIN_TIMEOUT_S)  # the readers' own bounded join runs inside it
        restore_board_to_serving(board, bench, dut_ip)
    assert not alive, f"{alive} still running after the echo test - it would load every test that follows"
    facts = parse_facts(output)
    assert facts.get("initiator_found") is True, f"the script found no initiating uart_link instance - {_TOML_HINT}: {facts}"
    assert facts.get("load_seen") is True, f"the host's load never reached the script's webserver, so nothing ran under load: {facts}"
    assert facts.get("intact") == facts.get("total"), f"echoes came back damaged or missing under load: {facts}"
    before, after = facts.get("before"), facts.get("after")
    assert isinstance(before, dict) and isinstance(after, dict) and after.get("Failures") == before.get("Failures"), f"the exerciser's own transfers failed during the echoes: {before!r} -> {after!r}"
    assert len(load.answered) >= _ECHO_MIN_ANSWERED, f"only {len(load.answered)} reads answered during the echoes, below {_ECHO_MIN_ANSWERED}: {load.failures[:5]}"
    assert not load.findings, f"torn reads during the echoes: {load.findings[:10]}"


def test_a_hazard_run_under_the_readers_load_reports_every_verdict(board: "Board", dut_ip: str, request: pytest.FixtureRequest) -> None:
    check_hazard_run_under_load(dut_ip, request.node.name)


def _assert_link_logs_empty(dut_ip: str, context: str) -> None:
    counts = get_errcount(dut_ip)
    for name in _uart_modules():
        entry = errcount_entry(counts, name)
        assert entry["counter"] == 0, f"{name} logged errors {context}: {entry!r}"


def _burst_get(dut_ip: str, completed: "list[int]") -> None:
    try:
        completed.append(http_client.fetch(dut_ip, 80, "GET", "/measurements", timeout_s=_REQUEST_BUDGET_S).status_code)
    except (OSError, http_client.HTTP_ERROR):  # a rejected connection under a deliberate overload is an accepted outcome
        return


def _echo_load(dut_ip: str, stop: threading.Event, load: _load.Load) -> None:
    # Once the script's own server answers (main.py's gone quiet first), the readers load it, joined here; nothing if
    # it never does. A reader still running at the bound is a finding: it would load every test that follows.
    try:
        if not wait_for_script_server(dut_ip, stop):
            load.failure("the echo script's own server never answered")
            return
    except AssertionError as e:  # main.py's server outlasting the handover: recorded, never a dead thread's warning
        load.failure(str(e))
        return
    with _load.readers(_ECHO_READERS, dut_ip, load, iterations=_ECHO_ITERATIONS, timeout_s=_REQUEST_BUDGET_S, join_s=_JOIN_TIMEOUT_S) as alive:
        pass
    if alive:
        load.finding(f"{alive} still running after the echo load")


def _gets_until(dut_ip: str, path: str, worker_id: int, stop: threading.Event, load: _load.Load) -> None:
    # One worker: GET `path` back to back until `stop` is set, each as _timed_gets() sends it.
    i = 0
    while not stop.is_set():
        _timed_get(dut_ip, path, f"worker {worker_id} iter {i}", load)
        i += 1


def _hammer(dut_ip: str, path: str) -> _load.Load:
    # _GET_WORKERS timed workers on `path`, joined on every path; the record they filled.
    load = _load.Load()
    threads: list[threading.Thread] = []
    try:
        for worker_id in range(_GET_WORKERS):
            thread = threading.Thread(target=_timed_gets, args=(dut_ip, path, worker_id, load), name=f"get-{worker_id}")
            threads.append(thread)
            thread.start()
    finally:
        alive = _load.join(threads, _JOIN_TIMEOUT_S)
    assert not alive, f"{alive} never finished within {_JOIN_TIMEOUT_S:g}s - possible real deadlock under load"
    return load


def _hazard_fields() -> "list[tuple[str, list[int]]]":
    # Each swept field and its values, read from src/asy_uart_link_driver.py's text as the board runs them.
    for node in ast.parse((SRC_DIR / "asy_uart_link_driver.py").read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and [getattr(target, "id", None) for target in node.targets] == ["_HAZARD_FIELDS"]:
            return [(name, list(values)) for name, _offset, values in ast.literal_eval(node.value)]
    pytest.fail("src/asy_uart_link_driver.py defines no _HAZARD_FIELDS")


def _hazard_findings(last: "JSONObject") -> "list[str]":
    # The run's facts judged as the twin judges them: one of two initiations completes, the crossing SET fails and the
    # link recovers, and each swept value is ACKed exactly when J.3/J.4 accept it (tests_hardware/flash/test_uart_crossover.py).
    cmd_set, uid_max = _load.src_number("asy_uart_comm.py", "CMD_SET"), _load.src_number("asy_uart_comm.py", "_UID_MAX")
    legal = {"cmd": lambda v: v == cmd_set, "size": lambda v: v == 1, "chunks": lambda v: v >= 2, "cur_chunk": lambda v: v == 1, "uid": lambda v: v <= uid_max}
    attempts = range(1, int(_load.src_number("asy_uart_link_driver.py", "_HAZARD_RECOVERY_ATTEMPTS")) + 1)
    findings: list[str] = []
    two = last.get("TwoInitiations")
    if two not in ([True, False], [False, True]):  # None: an initiation raised, logged at its task's top
        findings.append(f"two initiations at once were not one completion and one refusal: {two!r}")
    crossing = last.get("Crossed")
    if not (isinstance(crossing, list) and len(crossing) == 4 and crossing[:2] == [True, False] and crossing[2] in attempts and crossing[3] is True):
        findings.append(f"the SET crossing the peer's answer did not fail and recover within {len(attempts)} attempts: {crossing!r}")
    expected = [[name, [legal[name](value) for value in values], True] for name, values in _hazard_fields()]
    if last.get("FieldSweep") != expected:
        findings.append(f"the field sweep's ACKs against J.3/J.4 (None: its raw write failed), or the clean exchange after each field: {last.get('FieldSweep')!r}, not {expected!r}")
    return findings


def _hazard_report(dut_ip: str) -> "JSONObject":
    # The initiator's hazard report: the one /status "sensors" entry carrying Runs, Pending and Last.
    sensors: JSONObject = _load.as_object(_load.get_object(dut_ip, "/status", _REQUEST_BUDGET_S).get("sensors"), "GET /status sensors")
    reports = [entry for entry in sensors.values() if isinstance(entry, dict) and {"Runs", "Pending", "Last"} <= entry.keys()]
    if len(reports) != 1:
        pytest.fail(f"this firmware exposes {len(reports)} hazard reports, not one ({sorted(sensors)}) - {_TOML_HINT}")
    return reports[0]


def _hazard_run_ended(dut_ip: str, runs: int) -> bool:
    report = _hazard_report(dut_ip)
    return report.get("Runs") == runs + 1 and report.get("Pending") is False


def _link_counters(dut_ip: str) -> "dict[str, int]":
    # The link's own progress, read through /status's "sensors" registration list: without it the only observable is
    # an error counter, and an idle link and a healthy one both leave that at zero.
    sensors: JSONObject = _load.as_object(_load.get_object(dut_ip, "/status", _REQUEST_BUDGET_S).get("sensors"), "GET /status sensors")
    link = sensors.get("UARTLINK")
    if not isinstance(link, dict) or not all(isinstance(link.get(key), int) for key in ("Transfers", "Failures")):
        pytest.fail(f"this firmware exposes no UARTLINK maintenance entry with Transfers/Failures ({link!r}) - {_TOML_HINT}")
    return {key: int(value) for key, value in link.items() if isinstance(value, int) and not isinstance(value, bool)}


def _require_uart_modules(dut_ip: str) -> None:
    # The link exists only in a firmware carrying asy_uart_comm, which the bench TOML's uart_link instances pull in.
    present = get_errcount(dut_ip)
    missing = [name for name in _uart_modules() if name not in present]
    if missing:
        pytest.fail(f"this firmware exposes no {', '.join(missing)} error source - {_TOML_HINT}")


def _timed_get(dut_ip: str, path: str, label: str, load: _load.Load) -> None:
    # One GET of `path`, answered within the request budget or recorded as a failure, never raised.
    started = time.monotonic()
    try:
        res = http_client.fetch(dut_ip, 80, "GET", path, timeout_s=_REQUEST_BUDGET_S)
    except (OSError, http_client.HTTP_ERROR) as e:
        load.failure(f"{label}: {type(e).__name__}: {e}")
        return
    elapsed = time.monotonic() - started
    if res.status_code != 200 or elapsed > _REQUEST_BUDGET_S:
        load.failure(f"{label}: GET {path} answered {res.status_code} in {elapsed:.1f}s")
    else:
        load.answered.append(1)


def _timed_gets(dut_ip: str, path: str, worker_id: int, load: _load.Load) -> None:
    # One worker: GET `path` repeatedly, each answer within the request budget; a failure is recorded, never raised.
    for i in range(_GET_ITERATIONS_PER_WORKER):
        _timed_get(dut_ip, path, f"worker {worker_id} iter {i}", load)


def _uart_modules() -> "list[str]":
    # The bench TOML's uart_link instances' loggers: their errcount keys, as the generated definitions name them.
    names = _load.instance_loggers("uart_link")
    if not names:
        pytest.fail(f"the bench device declares no uart_link instance - {_TOML_HINT}")
    return names


def check_hazard_run_under_load(dut_ip: str, reason: str) -> None:
    # PUT /status's dispatch-only UartHazards starts one run while readers GET /status until it ends: every verdict as
    # the twin judges it, every read answered, the echo resumed with no failure counted, no webserver error and no task ended.
    _require_uart_modules(dut_ip)
    reset_all_error_logs(dut_ip, reason)
    runs = _hazard_report(dut_ip).get("Runs")
    assert isinstance(runs, int), f"the hazard report counts no runs: {runs!r}"
    before = _link_counters(dut_ip)
    load = _load.Load()
    stop = threading.Event()
    threads = [threading.Thread(target=_gets_until, args=(dut_ip, "/status", n, stop, load), name=f"hazard-get-{n}") for n in range(_ECHO_READERS)]
    try:
        for thread in threads:
            thread.start()
        put = http_client.fetch(dut_ip, 80, "PUT", "/status", {"UartHazards": True}, timeout_s=_REQUEST_BUDGET_S)
        assert put.status_code == 200 and put.json().get("result") == {"UartHazards": "Valid"}, f"PUT /status did not start the hazard run: {put.status_code} {put.body[:120]!r}"
        wait_until(lambda: _hazard_run_ended(dut_ip, runs), timeout_s=_HAZARD_RUN_TIMEOUT_S, poll_interval_s=_WAIT_POLL_S, description="the hazard run's end under the readers' load")
    finally:
        stop.set()
        alive = _load.join(threads, _JOIN_TIMEOUT_S)
    assert not alive, f"{alive} never finished within {_JOIN_TIMEOUT_S:g}s - possible real deadlock under load"
    assert not load.failures, f"{len(load.failures)} API issue(s) during the hazard run: {'; '.join(load.failures[:10])}"
    last = _hazard_report(dut_ip).get("Last")
    assert isinstance(last, dict), f"the ended hazard run left no facts: {last!r}"
    findings = _hazard_findings(last)
    assert not findings, "; ".join(findings)
    ended = _link_counters(dut_ip)
    wait_until(lambda: _link_counters(dut_ip)["Transfers"] > ended["Transfers"], timeout_s=_WAIT_TIMEOUT_S, poll_interval_s=_WAIT_POLL_S, description="the echo resuming after the hazard run")
    after = _link_counters(dut_ip)
    assert after["Failures"] == before["Failures"], f"the hazard run counted into the echo's failures: {before!r} -> {after!r}"
    web = errcount_entry(get_errcount(dut_ip), "WEBSERVER")
    assert web["counter"] == 0, f"the webserver logged errors under the hazard run: {web!r}"
    assert_no_task_ended(dut_ip, "UART hazard run under API load")


def check_link_healthy_under_load(dut_ip: str, reason: str) -> None:
    # Both sides have their own budget, and neither may be met by starving the other: the API side on latency and
    # status, the link side on its own error counters, where a transfer that timed out under load would show.
    _require_uart_modules(dut_ip)
    reset_all_error_logs(dut_ip, reason)
    load = _hammer(dut_ip, "/status")
    assert not load.failures, f"{len(load.failures)} issue(s) under concurrent API load: {'; '.join(load.failures[:10])}"
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_WAIT_TIMEOUT_S, poll_interval_s=_WAIT_POLL_S, description="webserver serving normally again after the concurrent UART-load test")
    _assert_link_logs_empty(dut_ip, "while the API was under load")
    assert_no_task_ended(dut_ip, "UART link under API load")


def check_overload_does_not_corrupt(dut_ip: str, reason: str) -> None:
    # The failure direction of the same claim: a burst past the server's comfortable concurrency degrades requests,
    # never the link - and the link's own recovery never shows up as a request failure either.
    _require_uart_modules(dut_ip)
    reset_all_error_logs(dut_ip, reason)
    completed: list[int] = []
    threads: list[threading.Thread] = []
    try:
        for n in range(_BURST_WORKERS):
            thread = threading.Thread(target=_burst_get, args=(dut_ip, completed), name=f"burst-{n}")
            threads.append(thread)
            thread.start()
    finally:
        alive = _load.join(threads, _SHORT_JOIN_TIMEOUT_S)
    assert not alive, f"{alive} never finished within {_SHORT_JOIN_TIMEOUT_S:g}s"
    assert 200 in completed, f"no request survived the burst at all: {completed!r}"
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_WAIT_TIMEOUT_S, poll_interval_s=_WAIT_POLL_S, description="webserver serving normally again after the burst")
    _assert_link_logs_empty(dut_ip, "under an API overload")
    assert_no_task_ended(dut_ip, "UART link under an API overload")


def check_transfers_under_load(dut_ip: str) -> None:
    # A transfer completes while the API is hammered: the counters read once at the instant the last worker joined,
    # since a transfer that lands only after the load is not the property.
    _require_uart_modules(dut_ip)
    before = _link_counters(dut_ip)
    load = _hammer(dut_ip, "/measurements")
    after = _link_counters(dut_ip)
    assert not load.failures, f"{len(load.failures)} API issue(s) while the link was running: {'; '.join(load.failures[:10])}"
    moved = after["Transfers"] - before["Transfers"]
    assert moved > 0, f"no transfer completed across the jumper during the API load: {before!r} -> {after!r}"
    assert after["Failures"] == before["Failures"], f"{after['Failures'] - before['Failures']} transfer(s) failed while the API was hammered: {before!r} -> {after!r}"
