"""Serving at MicroPython's own gc default (HEAP_FRAGMENTATION_MEASUREMENTS.md archive §7R.3, fixed per
SPECIFICATION.md Part I.3): the contiguous block each data source and route needs, and a sweep of
concurrent requests up past the ceiling with the heap read idle, under load and after."""

import re
import socket
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import _load
import heap_map
import http_client
import pytest
from harness import MEMORY_ERROR_MARKERS, configured_max_connections, get_routes, parse_facts, restore_board_to_serving, wait_for_script_server

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bench_control import BenchBridge
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("webserver_concurrency", "sensortask_integration", "poll_prewarm")

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
# Every registered JSON GET route, plus the page and the largest static file it fetches next (a static mount, not a
# REST route).
_PATHS = (*get_routes(), "/", "/js/app.js")
# @tunable l4.serving_heap_at_default_gc_rounds = 12
_ROUNDS = 12
# @tunable l4.network_resilience_slot_release_wait_s = 1.0
_ROUND_SETTLE_S = 1.0  # a slot outlives the response its client holds (Part I.6)
# @tunable l4.serving_heap_at_default_gc_level_gap_s = 3.0
_LEVEL_GAP_S = 3.0  # between levels - under the device script's own 10 s quiet-to-leave
# @tunable l4.serving_heap_at_default_gc_pre_idle_s = 30.0
_PRE_IDLE_S = 30.0  # the device starts dumping 20 s into its own boot: this leaves ~4 idle dumps first
# Fixed, the worst route needs 320-336 B (board and 32-bit twin); pre-fix needs were 512-1,536 B.
# Between rungs 24 (measures 384-400 B) and 32 (512 B), so the measured rung cannot flip the
# verdict either way (SPECIFICATION.md Part I.3).
# @tunable l4.serving_heap_at_default_gc_max_route_need = 480
_MAX_ROUTE_NEED = 480


# @tunable l4.serving_heap_at_default_gc_connect_timeout_s = 30.0
_CONNECT_TIMEOUT_S = 30.0
# @tunable l4.serving_heap_at_default_gc_barrier_timeout_s = 30.0
_BARRIER_TIMEOUT_S = 30.0
# @tunable l4.serving_heap_at_default_gc_burst_join_s = 60.0
_BURST_JOIN_S = 60.0
# @tunable l4.serving_heap_at_default_gc_need_script_timeout_s = 300.0
_NEED_SCRIPT_TIMEOUT_S = 300.0
# @tunable l4.serving_heap_at_default_gc_serving_script_timeout_s = 900.0
_SERVING_SCRIPT_TIMEOUT_S = 900.0
# @tunable l4.serving_heap_at_default_gc_driver_join_s = 90.0
_DRIVER_JOIN_S = 90.0


@pytest.mark.provokes_log(
    "each probe runs on heaps shaped below its need, over a scratch-config boot that logs CONFIG_LOST: a streamed source"
    " that fails there logs CALLBACK, a config read logs its module's CHIP_GET or config-read entry, and a history write"
    " whose own buffers do not fit logs LOG_RAM_ONLY",
    ("WEBSERVER", "E", "CALLBACK"),
    ("WEBSERVER", "E", "LOG_RAM_ONLY"),
    ("SYSTEM", "W", "CONFIG_LOST"),
    ("BMP3XX", "E", "CHIP_GET"),
    ("ISL29125", "E", "CHIP_GET"),
    ("SCD30", "E", "CHIP_GET"),
    ("BMP3XX", "E", "CFG_GET_RAISED"),
    ("ISL29125", "E", "CFG_GET_RAISED"),
    ("SCD30", "E", "CFG_GET_RAISED"),
    ("SGP40", "E", "CFG_GET_RAISED"),
    ("WIFI", "E", "CFG_GET_RAISED"),
    ("NTP", "E", "CFG_GET_RAISED"),
    ("NOTIFY", "E", "CFG_GET_RAISED"),
    ("BMP3XX", "E", "CFG_CALLBACK_RAISED"),
    ("ISL29125", "E", "CFG_CALLBACK_RAISED"),
    ("WIFI", "E", "CFG_CALLBACK_RAISED"),
)
@pytest.mark.ends_unreachable
def test_every_source_and_route_fits_a_small_free_run(isolated_board: "Board", result_note: "_load.Note") -> None:
    # No network. The device script shapes the heap so no free run exceeds S, for rising S, and
    # runs each data source and whole GET route on it; the host reduces that to each one's need.
    output = isolated_board.run_isolated(DEVICE_SCRIPTS / "allocation_need_per_source.py", timeout_s=_NEED_SCRIPT_TIMEOUT_S)
    facts = parse_facts(output)
    at = _stage(facts)
    assert facts.get("index_handlers") == 1, f"{at}: the app registers {facts.get('index_handlers')!r} GET handlers for '/', so the page probe measured not exactly one"
    need = heap_map.parse_allocation_need(output)
    churn = facts.get("churn")
    assert need and isinstance(churn, dict), f"{at}: the script printed no probe results ({facts})"
    assert set(need) == set(churn) and len(need) == facts.get("probes"), f"{at}: the sieve measured {sorted(need)}, the churn pass {sorted(churn)}, of {facts.get('probes')} probes"
    for probe, size in sorted(need.items(), key=lambda kv: -(kv[1] if kv[1] is not None else 1 << 30)):
        result_note(f"{at}: need {probe}: largest free run {size} B, churn {churn.get(probe)} B")
    too_big = {probe: size for probe, size in need.items() if size is None or size > _MAX_ROUTE_NEED}
    assert not too_big, f"{at}: these need a larger contiguous block than a loaded heap keeps (Part I.3): {too_big}"


@pytest.mark.provokes_log(
    "its levels run two past the ceiling, whose refusals trace HTTP_REFUSED",
    ("WEBSERVER", "W", "HTTP_REFUSED"),
    ("WEBSERVER", "W", "HTTP_PEER_RESET"),
)
@pytest.mark.ends_unreachable
def test_serving_sweep_at_the_reactive_default(isolated_board: "Board", dut_ip: str, result_note: "_load.Note") -> None:
    # Ascending levels up past the configured ceiling, on one boot: the realistic case is a running
    # device whose heap carries every earlier burst. The bar is I.4(e): not one allocation failure.
    ceiling = configured_max_connections()
    levels = list(range(4, ceiling + 3, 2))
    tallies: dict[int, dict[str, int]] = {}
    stop = threading.Event()
    driver = threading.Thread(target=sweep_levels, args=(dut_ip, levels, stop, tallies), name="sweep-driver")
    try:
        driver.start()
        output = isolated_board.run_isolated(DEVICE_SCRIPTS / "serving_at_default_gc.py", timeout_s=_SERVING_SCRIPT_TIMEOUT_S)
    finally:
        stop.set()
        alive = _load.join([driver], _DRIVER_JOIN_S)
    assert not alive, "the load driver is still running after its own test - it would hammer every test that follows"
    facts = parse_facts(output)
    at = _stage(facts)
    assert facts.get("webserver_built") is True, f"{at}: main() had built no webserver by the end of the boot wait: {facts}"
    assert "phases_incomplete" not in facts, f"{at}: the script never saw a full idle/load/idle cycle: {facts.get('phases_incomplete')}"
    maps = heap_map.parse_labelled(output)
    for label, m in sorted(maps.items()):
        result_note(f"{at}: {label:>7} free={m.free_bytes} largest_free_run={m.largest_free_run} runs={len(m.free_runs)} placeable256={m.placeable(256)} placeable2048={m.placeable(2048)}")
    for n in levels:
        result_note(f"{at}: N={n} (ceiling {ceiling}): {tallies.get(n)}")
    failures = [int(size) for size in re.findall(r"memory allocation failed, allocating (\d+)", output)]
    result_note(f"{at}: allocation failures: {len(failures)} sizes={sorted(set(failures))}, failure maps {facts.get('failure_maps')}")
    assert tallies.keys() == set(levels), f"{at}: the driver did not finish every level: {tallies}"
    assert not any(marker in output for marker in MEMORY_ERROR_MARKERS), f"{at}: allocation failure while serving (I.4(e)): {output[-2500:]}"
    for n in levels:
        served = tallies[n].get("200", 0)
        refused = tallies[n].get("refused", 0)
        admitted = min(n, ceiling) * _ROUNDS
        assert served == admitted and served + refused == n * _ROUNDS, f"{at}: N={n}: {tallies[n]} - expected {admitted} served, the rest refused cleanly"


def _burst(dut_ip: str, n: int) -> list[str]:
    barrier = threading.Barrier(n, timeout=_BARRIER_TIMEOUT_S)
    outcomes = ["unset"] * n
    threads = [threading.Thread(target=_one_request, args=(dut_ip, _PATHS[i % len(_PATHS)], barrier, outcomes, i), name=f"burst-{i}") for i in range(n)]
    try:
        for thread in threads:
            thread.start()
    finally:
        alive = _load.join(threads, _BURST_JOIN_S)
    assert not alive, f"{alive} outlived its burst"
    return outcomes


def _one_request(dut_ip: str, path: str, barrier: threading.Barrier, outcomes: list[str], index: int) -> None:
    # One real socket, body DRAINED rather than materialised - the drain rule, so the host measures
    # the board and never its own buffering (tests/test_digital_twin_http_client.py).
    try:
        sock = socket.create_connection((dut_ip, 80), timeout=_CONNECT_TIMEOUT_S)
    except OSError as e:
        outcomes[index] = f"connect:{type(e).__name__}"
        barrier.abort()
        return
    try:
        barrier.wait()
        sock.sendall(f"GET {path} HTTP/1.0\r\nHost: dut\r\nConnection: close\r\n\r\n".encode())
        received = b""
        while b"\r\n\r\n" not in received and (chunk := sock.recv(256)):
            received += chunk
        if not received.startswith(b"HTTP/"):
            outcomes[index] = "refused"
            return
        head, _, body = received.partition(b"\r\n\r\n")
        body_len = len(body)
        while chunk := sock.recv(1024):
            body_len += len(chunk)
        # A body cut off after the 200 went out is not a served request: every route sends its length.
        lengths = [line.split(b":", 1)[1].strip() for line in head.split(b"\r\n") if line.lower().startswith(b"content-length:")]
        verdict = "-unframed" if not lengths else "" if lengths[0] == str(body_len).encode() else "-truncated"
        status = head.split(b" ")
        outcomes[index] = (status[1].decode(errors="replace") if len(status) > 1 else "malformed") + verdict
    except (OSError, threading.BrokenBarrierError) as e:
        outcomes[index] = "refused" if http_client.is_ceiling_close(e) else f"io:{type(e).__name__}"
    finally:
        sock.close()


def _stage(facts: "dict[str, object]") -> str:
    # The GC stage the script measured at, which every assertion and report names.
    stage = facts.get("gc_threshold")
    assert isinstance(stage, int), f"the script reported no gc_threshold fact: {facts}"
    return f"at GC_THRESHOLD={stage}"


@pytest.fixture(scope="module")
def isolated_board(board: "Board", bench: "BenchBridge", dut_ip: str) -> "Iterator[Board]":
    # Both tests stop main.py; the board is put back ONCE, after the last of them, not per test.
    yield board
    restore_board_to_serving(board, bench, dut_ip)


def sweep_levels(dut_ip: str, levels: list[int], stop: threading.Event, tallies: dict[int, dict[str, int]]) -> None:
    # Waits for the device script's own boot, idles, then _ROUNDS bursts per level in ascending
    # order. `stop` guarantees it cannot outlive its test - a driver that did took 37 tests down once.
    if not wait_for_script_server(dut_ip, stop, "/networking") or stop.wait(_PRE_IDLE_S):
        return
    for n in levels:
        tally = tallies.setdefault(n, {})
        for _ in range(_ROUNDS):
            if stop.is_set():
                return
            for outcome in _burst(dut_ip, n):
                tally[outcome] = tally.get(outcome, 0) + 1
            stop.wait(_ROUND_SETTLE_S)
        stop.wait(_LEVEL_GAP_S)
