"""Serving at MicroPython's own gc default (HEAP_FRAGMENTATION_MEASUREMENTS.md §7R.3, fixed per
SPECIFICATION.md Part I.3): the contiguous block each data source and route needs, and a sweep of
concurrent requests up past the ceiling with the heap read idle, under load and after."""

from __future__ import annotations

import re
import socket
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import heap_map
import http_client
import pytest
from harness import MEMORY_ERROR_MARKERS, configured_max_connections, wait_until

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bench_control import BenchBridge
    from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
# The sitting's own load shape - both streaming endpoints, the page, and the rest - plus the script
# every page load fetches next, the largest static file the device serves.
_PATHS = ("/status", "/sensors", "/", "/measurements", "/networking", "/system", "/js/app.js")
_ROUNDS = 12
_ROUND_SETTLE_S = 1.0  # a slot outlives the response its client holds (Part I.6)
_LEVEL_GAP_S = 3.0  # between levels - under the device script's own 10 s quiet-to-leave
_PRE_IDLE_S = 30.0  # the device starts dumping 20 s into its own boot: this leaves ~4 idle dumps first
# Fixed, the worst route needs 320-336 B (board and 32-bit twin); pre-fix needs were 512-1,536 B.
# Between rungs 24 (measures 384-400 B) and 32 (512 B), so the measured rung cannot flip the
# verdict either way (SPECIFICATION.md Part I.3).
_MAX_ROUTE_NEED = 480


def _one_request(dut_ip: str, path: str, barrier: threading.Barrier, outcomes: list[str], index: int) -> None:
    """One real socket, body DRAINED rather than materialised - the drain rule, so the host measures
    the board and never its own buffering (tests/test_digital_twin_http_client.py)."""
    try:
        sock = socket.create_connection((dut_ip, 80), timeout=30.0)
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
        lengths = [line.split(b":", 1)[1] for line in head.split(b"\r\n") if line.lower().startswith(b"content-length:")]
        verdict = "-unframed" if not lengths else "" if int(lengths[0]) == body_len else "-truncated"
        outcomes[index] = head.split(b" ")[1].decode() + verdict
    except (OSError, threading.BrokenBarrierError) as e:
        outcomes[index] = "refused" if isinstance(e, ConnectionResetError) else f"io:{type(e).__name__}"
    finally:
        sock.close()


def _burst(dut_ip: str, n: int) -> list[str]:
    barrier = threading.Barrier(n, timeout=30.0)
    outcomes = ["unset"] * n
    threads = [threading.Thread(target=_one_request, args=(dut_ip, _PATHS[i % len(_PATHS)], barrier, outcomes, i)) for i in range(n)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60.0)
    assert not any(thread.is_alive() for thread in threads), "a request thread outlived its burst"
    return outcomes


def _wait_serving(dut_ip: str, stop: threading.Event, timeout_s: float = 120.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline and not stop.is_set():
        try:
            if http_client.fetch(dut_ip, 80, "GET", "/networking", timeout_s=3.0).status_code == 200:
                return True
        except OSError:
            stop.wait(1.0)
    return False


def sweep_levels(dut_ip: str, levels: list[int], stop: threading.Event, tallies: dict[int, dict[str, int]]) -> None:
    """Waits for the device script's own boot, idles, then _ROUNDS bursts per level in ascending
    order. `stop` guarantees it cannot outlive its test - a driver that did took 37 tests down once."""
    if not _wait_serving(dut_ip, stop) or stop.wait(_PRE_IDLE_S):
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


def _restore_board_to_serving(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    """run_isolated() leaves main.py stopped; every later bench test needs the webserver back."""
    bench.kick_all_stations()  # stale AP-side station entries stop the DUT reassociating (README)
    board.hard_reset()
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=90.0,
        poll_interval_s=3.0,
        description="DUT serving HTTP again after the device scripts left main.py stopped",
    )


@pytest.fixture(scope="module")
def isolated_board(board: Board, bench: BenchBridge, dut_ip: str) -> Iterator[Board]:
    # Both tests stop main.py; the board is put back ONCE, after the last of them, not per test.
    yield board
    _restore_board_to_serving(board, bench, dut_ip)


def test_every_source_and_route_fits_a_small_free_run(isolated_board: Board) -> None:
    # No network. The device script shapes the heap so no free run exceeds S, for rising S, and
    # runs each data source and whole GET route on it; the host reduces that to each one's need.
    output = isolated_board.run_isolated(DEVICE_SCRIPTS / "allocation_need_per_source.py", timeout_s=300.0)
    assert "RESULT: PASS" in output, output[-2000:]
    need = heap_map.parse_allocation_need(output)
    churn = {m.group(1): int(m.group(2)) for m in re.finditer(r"^CHURN (\S+) (\d+)", output, re.MULTILINE)}
    assert need, "the script printed no probe results"
    for probe, size in sorted(need.items(), key=lambda kv: -(kv[1] if kv[1] is not None else 1 << 30)):
        print(f"[HW] need {probe}: largest free run {size} B, churn {churn.get(probe)} B")
    too_big = {probe: size for probe, size in need.items() if size is None or size > _MAX_ROUTE_NEED}
    assert not too_big, f"these need a larger contiguous block than a loaded heap keeps (Part I.3): {too_big}"


def test_serving_sweep_at_the_reactive_default(isolated_board: Board, dut_ip: str) -> None:
    # Ascending levels up past the configured ceiling, on one boot: the realistic case is a running
    # device whose heap carries every earlier burst. The bar is I.4(e): not one allocation failure.
    ceiling = configured_max_connections()
    levels = list(range(4, ceiling + 3, 2))
    tallies: dict[int, dict[str, int]] = {}
    stop = threading.Event()
    driver = threading.Thread(target=sweep_levels, args=(dut_ip, levels, stop, tallies), daemon=True)
    driver.start()
    try:
        output = isolated_board.run_isolated(DEVICE_SCRIPTS / "serving_at_default_gc.py", timeout_s=900.0)
    finally:
        stop.set()
        driver.join(timeout=90.0)
    assert not driver.is_alive(), "the load driver is still running after its own test - it would hammer every test that follows"
    assert "RESULT: PASS" in output, output[-2000:]
    assert "PHASES_INCOMPLETE" not in output, f"the script never saw a full idle/load/idle cycle: {output[-1500:]}"
    maps = heap_map.parse_labelled(output)
    for label, m in sorted(maps.items()):
        print(f"[HW] {label:>7} free={m.free_bytes} largest_free_run={m.largest_free_run} runs={len(m.free_runs)} placeable256={m.placeable(256)} placeable2048={m.placeable(2048)}")
    for n in levels:
        print(f"[HW] N={n} (ceiling {ceiling}): {tallies.get(n)}")
    failures = [int(size) for size in re.findall(r"memory allocation failed, allocating (\d+)", output)]
    print(f"[HW] allocation failures: {len(failures)} sizes={sorted(set(failures))}")
    assert tallies.keys() == set(levels), f"the driver did not finish every level: {tallies}"
    assert not any(marker in output for marker in MEMORY_ERROR_MARKERS), f"allocation failure while serving (I.4(e)): {output[-2500:]}"
    for n in levels:
        served = tallies[n].get("200", 0)
        refused = tallies[n].get("refused", 0)
        admitted = min(n, ceiling) * _ROUNDS
        assert served == admitted and served + refused == n * _ROUNDS, f"N={n}: {tallies[n]} - expected {admitted} served, the rest refused cleanly"
