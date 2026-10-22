"""Bench-tier automated tests: real firmware memory behavior under HTTP soak traffic (needs a reachable network,
unavailable on flash tier) - load over WiFi, tail_log()-watched for a MemoryError or a mid-soak reboot - and the
loop-lag script's event-loop lag under the same load on every route (SPECIFICATION.md Part F.3)."""

import threading
from typing import TYPE_CHECKING

import _load
import http_client
import pytest
from error_log_helpers import assert_no_task_ended, errcount_entry, get_errcount, reset_all_error_logs, save_errcount
from harness import DEVICE_SCRIPTS_DIR, MEMORY_ERROR_MARKERS, SRC_DIR, bench_device, boot_lines, configured_max_connections, crash_lines, device_toml, fram_backed_logger_names, get_routes, parse_facts, restore_board_to_serving, wait_for_script_server, wait_until
from soak_durations import SOAK_DURATION_SECONDS

from buildgen.model import load_device
from buildgen.validate import smallest_hard_consumer

if TYPE_CHECKING:
    from bench_control import BenchBridge
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("webserver_concurrency", "sensortask_integration", "poll_prewarm", "ci_suite._run_11_soak", "loop_lag")

# max_connections GET threads at true max speed (unlike the modest soak below) plus 1 thread PUTting SGP40.ResetVOC
# every 3s - the request density that originally found real MemoryErrors within 45s; 120s needs no soak flag.
# @tunable l4.memory_stress_bench_hammer_duration_s = 120.0
_HAMMER_DURATION_S = 120.0
_HAMMER_PATHS = tuple(get_routes())  # every registered JSON GET route
_HAMMER_THREAD_COUNT = configured_max_connections()  # the build's own ceiling: the hammer saturates admission
# @tunable l4.memory_stress_bench_fetch_timeout_s = 5.0
_FETCH_TIMEOUT_S = 5.0
# @tunable l4.memory_stress_bench_join_timeout_s = 10.0
_JOIN_TIMEOUT_S = 10.0
# @tunable l4.memory_stress_bench_voc_reset_interval_s = 3.0
_VOC_RESET_INTERVAL_S = 3.0
# Readers' answered requests, the writer's never counted: writer starvation is accepted degradation (owner, 2026-09-28).
# @tunable l4.memory_stress_bench_min_answered = 100
_MIN_ANSWERED = 100
# @tunable l4.memory_stress_bench_soak_request_step_s = 0.2
_SOAK_REQUEST_STEP_S = 0.2
# Failed soak requests as a share of those sent, so the bound scales with the chosen duration.
# @tunable l4.soak_request_failure_rate = 0.001
_SOAK_REQUEST_FAILURE_RATE = 0.001
# @tunable l4.memory_stress_bench_recovery_timeout_s = 30.0
_RECOVERY_TIMEOUT_S = 30.0
# @tunable l4.memory_stress_bench_recovery_poll_s = 1.0
_RECOVERY_POLL_S = 1.0
# The lag script's own 30 s window plus the shipped boot on the board's own config, its WiFi connect included.
# @tunable l4.memory_stress_bench_loop_lag_script_timeout_s = 90.0
_LOOP_LAG_SCRIPT_TIMEOUT_S = 90.0


class _Hammer:
    # One hammer run's record: readers' answered requests, in all and per route, the writer's PUTs answered 200, every
    # failure, and the MemFree each answered /status carried.
    def __init__(self) -> None:
        self.answered = 0
        self.served: dict[str, int] = {}
        self.accepted = 0
        self.errors: list[str] = []
        self.mem_free: list[int] = []
        self.lock = threading.Lock()


def test_real_hardware_survives_max_speed_hammer_load_without_memoryerror_or_reboot(board: "Board", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    save_errcount(dut_ip, request.node.name)  # what the board logged before this test is evidence (CLAUDE.md)
    reset_all_error_logs(dut_ip, request.node.name)
    lines, record = _run_max_speed_hammer_load(board, dut_ip, _HAMMER_DURATION_S)
    _assert_no_crash_or_reboot(lines, "max-speed hammer load")
    # Answered means processed and answered with a 200 under load, which a wedged server cannot fake.
    assert record.answered >= _MIN_ANSWERED, f"too few reads answered during the hammer load ({record.answered} ok, {len(record.errors)} rejected/errored) - server may have wedged"
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_RECOVERY_TIMEOUT_S, poll_interval_s=_RECOVERY_POLL_S, description="GET /status serving again after the hammer")
    assert_no_task_ended(dut_ip, "max-speed hammer load")
    result_note(f"{record.answered} reads answered, {record.accepted} ResetVOC writes accepted, {len(record.errors)} refused; MemFree floor {min(record.mem_free, default=-1)} B over {len(record.mem_free)} /status answers")
    reset_all_error_logs(dut_ip, request.node.name)


@pytest.mark.soak_duration
def test_real_hardware_survives_extended_max_speed_hammer_load_with_fram_diagnostics_preserved(board: "Board", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # The hammer above over a named soak duration (mid = 600s matches the one real WDT_RESET observed); captures the
    # FRAM-backed errcount in the assertion message before any clear (CLAUDE.md).
    duration = request.config.getoption("--soak-duration")
    if duration is None:
        pytest.skip("real extended max-speed hammer load - run via scripts/run_bench_soak_tests.sh --duration mid (600s, matching the original WDT-reset investigation's own duration)")
    save_errcount(dut_ip, request.node.name)
    reset_all_error_logs(dut_ip, request.node.name)
    lines, record = _run_max_speed_hammer_load(board, dut_ip, SOAK_DURATION_SECONDS[duration])
    counts = get_errcount(dut_ip)
    logged = {name: entry for name in fram_backed_logger_names(bench_device()) if (entry := errcount_entry(counts, name))["counter"] > 0}
    try:
        _assert_no_crash_or_reboot(lines, "the extended max-speed hammer load")
        assert_no_task_ended(dut_ip, "extended max-speed hammer load")
        assert not logged, f"a FRAM-backed module logged a real error during the hammer load - real diagnostic evidence, captured before any cleanup: {logged!r}"
        assert record.answered >= _MIN_ANSWERED, f"too few reads answered during the hammer load ({record.answered} ok, {len(record.errors)} rejected/errored) - server may have wedged"
        result_note(f"{record.answered} reads answered, {record.accepted} ResetVOC writes accepted over {SOAK_DURATION_SECONDS[duration]:g}s; MemFree floor {min(record.mem_free, default=-1)} B")
    finally:
        reset_all_error_logs(dut_ip, request.node.name)  # only after the assertions above reported any FRAM-backed history


@pytest.mark.soak_duration
def test_http_soak_stays_live(board: "Board", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    duration = request.config.getoption("--soak-duration")
    if duration is None:
        pytest.skip("real HTTP soak over one named duration - run via scripts/run_bench_soak_tests.sh --duration {short,mid,long}")
    save_errcount(dut_ip, request.node.name)  # the board's log before this test is evidence, saved before the clear
    reset_all_error_logs(dut_ip, request.node.name)  # the task-end check below counts from here
    stop = threading.Event()
    request_errors: list[str] = []
    sent: list[int] = []

    def soak_reader() -> None:
        i = 0
        while not stop.is_set():
            path = _HAMMER_PATHS[i % len(_HAMMER_PATHS)]
            i += 1
            sent.append(1)
            try:
                res = http_client.fetch(dut_ip, 80, "GET", path, timeout_s=_FETCH_TIMEOUT_S)
                if res.status_code != 200:
                    request_errors.append(f"GET {path} -> {res.status_code}")
            except (OSError, http_client.HTTP_ERROR) as exc:  # a real transient network hiccup during a long soak is expected sometimes
                request_errors.append(f"GET {path} -> {exc!r}")
            stop.wait(_SOAK_REQUEST_STEP_S)  # a modest, sustained request rate - not a flood (the hammer above is the flood)

    reader = threading.Thread(target=soak_reader, name="soak-reader")
    try:
        reader.start()
        lines = board.tail_log(duration_s=SOAK_DURATION_SECONDS[duration])
    finally:
        stop.set()
        alive = _load.join([reader], _JOIN_TIMEOUT_S)
    assert not alive, "the soak reader never finished"
    _assert_no_crash_or_reboot(lines, "the HTTP soak")
    assert_no_task_ended(dut_ip, "the HTTP soak")
    result_note(f"{len(request_errors)} of {len(sent)} soak requests failed over {SOAK_DURATION_SECONDS[duration]:g}s")
    assert len(request_errors) <= _SOAK_REQUEST_FAILURE_RATE * len(sent), f"too many failed/non-200 requests during the soak ({len(request_errors)} of {len(sent)}): {request_errors[:10]}"


def test_loop_lag_under_http_load_on_every_route_stays_under_the_smallest_hard_consumer(board: "Board", bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # The loop-lag script's main() on the board's own config, its server on the board's address, under the hammer's
    # readers on every route: the twin scenario's load and evidence, beside the script's lag, main() and FRAM facts.
    save_errcount(dut_ip, request.node.name)  # its main() writes production FRAM chunks: the board's log is saved first
    record = _Hammer()
    stuck: list[str] = []
    stop = threading.Event()
    driver = threading.Thread(target=_lag_load, args=(dut_ip, stop, record, stuck), name="lag-load")
    try:
        driver.start()
        output = board.run_isolated(DEVICE_SCRIPTS_DIR / "loop_lag_under_combined_load.py", timeout_s=_LOOP_LAG_SCRIPT_TIMEOUT_S, mode="production")
    finally:
        stop.set()
        alive = _load.join([driver], 2 * _JOIN_TIMEOUT_S)  # the readers' own bounded join runs inside it
        restore_board_to_serving(board, bench, dut_ip)
    assert not alive and not stuck, f"{alive + stuck} still running after the loop-lag load - it would load every test that follows"
    allocation = [line for line in output.splitlines() if any(marker in line for marker in MEMORY_ERROR_MARKERS)]
    assert not allocation, "the loop-lag script reported an allocation failure, caught or not:\n" + "\n".join(allocation)
    facts = parse_facts(output)
    bound_us = smallest_hard_consumer(load_device(device_toml()), SRC_DIR).ms * 1000  # the flash test's and the twin scenario's one source
    lag_max, lag_p99 = facts.get("lag_max_us"), facts.get("lag_p99_us")
    result_note(f"loop lag under HTTP load: max {lag_max} us, p99 {lag_p99} us over {facts.get('samples')} samples (bound {bound_us} us); {record.answered} reads answered, per route {record.served}")
    unserved = [route for route in _HAMMER_PATHS if not record.served.get(route)]
    assert _HAMMER_PATHS and not unserved, f"GET routes never served under the load: {unserved} of {len(_HAMMER_PATHS)} routes; {record.errors[:5]}"
    assert facts.get("main_running") is True, f"the shipped main() ended inside the window: {facts}"
    writes = facts.get("fram_writes")
    assert facts.get("fram_write_failures") == 0 and isinstance(writes, int) and writes > 0, f"the FRAM load did not run cleanly: {facts}"
    assert isinstance(lag_max, int) and lag_max <= bound_us, f"the loop lagged {lag_max} us, past the {bound_us} us smallest hard consumer: {facts}"


def _assert_no_crash_or_reboot(lines: "list[str]", what: str) -> None:
    # The soak gate: either allocation marker covers a load that allocated, failed, logged it and carried on (the board
    # never prints the class name for a caught one); a crash line adds a traceback, a boot line a reboot mid-load.
    allocation = [line for line in lines if any(marker in line for marker in MEMORY_ERROR_MARKERS)]
    assert not allocation, f"observed an allocation failure during {what}, caught or not:\n" + "\n".join(allocation)
    assert not crash_lines(lines), f"observed a crash during {what}:\n" + "\n".join(crash_lines(lines))
    assert not boot_lines(lines), f"observed an unexpected reboot during {what} (real memory exhaustion -> WDT reset?):\n" + "\n".join(boot_lines(lines))


def _lag_load(dut_ip: str, stop: threading.Event, record: _Hammer, stuck: "list[str]") -> None:
    # Once the script's own server answers (main.py's gone quiet first), the hammer's readers load it until `stop`: the
    # twin scenario's load. Nothing runs if it never answers; a reader outliving its join is named in `stuck`.
    try:
        if not wait_for_script_server(dut_ip, stop):
            record.errors.append("the loop-lag script's own server never answered")
            return
    except AssertionError as e:  # main.py's server outlasting the handover: recorded, never a dead thread's warning
        record.errors.append(str(e))
        return
    threads = _readers(dut_ip, stop, record)
    try:
        for thread in threads:
            thread.start()
        stop.wait(_LOOP_LAG_SCRIPT_TIMEOUT_S)
    finally:
        stuck.extend(_load.join(threads, _JOIN_TIMEOUT_S))


def _readers(dut_ip: str, stop: threading.Event, record: _Hammer) -> "list[threading.Thread]":
    # The ceiling of readers, unstarted, each cycling every JSON GET route from its own offset until `stop`: every 200
    # counted, per route too, and each answered /status's MemFree kept.
    def get_hammer(thread_index: int) -> None:
        i = thread_index
        while not stop.is_set():
            path = _HAMMER_PATHS[i % len(_HAMMER_PATHS)]
            i += 1
            try:
                res = http_client.fetch(dut_ip, 80, "GET", path, timeout_s=_FETCH_TIMEOUT_S)
                free = _load.as_object(res.json().get("system"), "system").get("MemFree") if path == "/status" and res.status_code == 200 else None
            except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError) as exc:
                # A reset at max_connections is the server's reject-when-full, not a fault (SPECIFICATION.md H.7).
                with record.lock:
                    record.errors.append(f"GET {path} -> {exc!r}")
                continue
            with record.lock:
                if res.status_code == 200:
                    record.answered += 1
                    record.served[path] = record.served.get(path, 0) + 1
                    if isinstance(free, int):
                        record.mem_free.append(free)
                else:
                    record.errors.append(f"GET {path} -> {res.status_code}")

    return [threading.Thread(target=get_hammer, args=(i,), name=f"hammer-{i}") for i in range(_HAMMER_THREAD_COUNT)]


def _run_max_speed_hammer_load(board: "Board", dut_ip: str, duration_s: float) -> "tuple[list[str], _Hammer]":
    stop = threading.Event()
    record = _Hammer()

    def reset_voc_periodically() -> None:
        while not stop.wait(_VOC_RESET_INTERVAL_S):
            try:
                res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"ResetVOC": True}}, timeout_s=_FETCH_TIMEOUT_S)
            except (OSError, http_client.HTTP_ERROR) as exc:
                with record.lock:
                    record.errors.append(f"PUT /sensors ResetVOC -> {exc!r}")
                continue
            with record.lock:
                if res.status_code == 200:
                    record.accepted += 1
                else:
                    record.errors.append(f"PUT /sensors ResetVOC -> {res.status_code}")

    threads = [*_readers(dut_ip, stop, record), threading.Thread(target=reset_voc_periodically, name="voc-resets")]
    try:
        for thread in threads:
            thread.start()
        lines = board.tail_log(duration_s=duration_s)
    finally:
        stop.set()
        alive = _load.join(threads, _JOIN_TIMEOUT_S)
    assert not alive, f"{alive} still running after the hammer"
    return lines, record
