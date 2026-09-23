"""Bench-tier measurement for the connection-scaling decision table
(REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md §8.3 rows 5, 7 and 8): what the board's heap looks
like while a full ceiling of connections is genuinely held open, and where its real wall is."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

import heap_map
import http_client
import pytest
from harness import MEMORY_ERROR_MARKERS, configured_max_connections, discover_max_connections, wait_until

if TYPE_CHECKING:
    from bench_control import BenchBridge
    from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
# microdot allocates max_content_length contiguously per connection (asy_webserver_service.py's own
# Request.max_content_length), so this is the block that has to be PLACEABLE N times over, not a
# fraction of total free. heap_map.placeable() counts exactly that - gaps_at_least() counts
# RUNS, so a single large free run reads as 1 however many buffers actually fit in it.
PER_CONNECTION_ALLOCATION = 2048
# The script's own window is 90s and it prints READY about 20s in; this bounds the hold, not it.
_HOLD_S = 55.0
# No connection can be held past the server's own outer_cap_s (15.0), and one that says nothing is
# closed after per_call_timeout_s (5.0) - measured on silicon at 5.4s plain, 15.1s while dripping
# (SPECIFICATION.md Part H.7.1). A full ceiling is therefore SUSTAINED by recycling, never held.
_DRIP_INTERVAL_S = 2.0
# Recycled well inside the 15s cap, and STAGGERED: workers started together would also expire
# together, so the live count would collapse to zero every 15s instead of staying at the ceiling.
_RECYCLE_S = 10.0
# Recycling means one worker is always between connections, so the count sits at ceiling or one
# below it. What makes the heap dumps a peak reading is that it is at the ceiling nearly always.
_MIN_FRACTION_AT_CEILING = 0.55


def _park_one_connection(dut_ip: str, live: list[int], lock: threading.Lock, stop: threading.Event, offset_s: float) -> None:
    """Holds one connection parked mid-request and recycles it before the firmware reclaims it, so
    the ceiling stays full. `stop` is what guarantees the worker cannot outlive its own test."""
    stop.wait(offset_s)  # stagger, so the whole set does not expire in lockstep
    while not stop.is_set():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        parked = False
        try:
            sock.connect((dut_ip, 80))
            # Headers only, no terminating blank line: the server is parked waiting for the rest,
            # which is what makes this a held connection rather than a completed request.
            sock.sendall(b"GET /sensors HTTP/1.1\r\nHost: dut\r\n")
            sock.setblocking(False)
            with lock:
                live[0] += 1
            parked = True
            recycle_at = time.monotonic() + _RECYCLE_S
            while not stop.is_set() and time.monotonic() < recycle_at:
                stop.wait(_DRIP_INTERVAL_S)
                sock.sendall(b"X-Pad: y\r\n")  # resets the per-call read timeout
                sock.recv(4096)  # readable at all means the server answered or closed: take a fresh one
                break
        except (BlockingIOError, TimeoutError):
            pass  # nothing to read, which is what a parked connection looks like
        except OSError:
            stop.wait(0.1)  # refused or reset - back off rather than spinning on a busy board
        finally:
            if parked:
                with lock:
                    live[0] -= 1
            sock.close()


def _hold_ceiling_open(dut_ip: str, ceiling: int, seconds: float, held_out: list[int]) -> None:
    """Sustains `ceiling` real connections parked mid-request for the whole window and records the
    count's own distribution, so the heap samples are provably taken at peak (5B rule 1). Driven
    from the host so nothing here shares the DUT's heap (Part E.9)."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:  # wait for the script's own boot to start serving
        try:
            if http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=3.0).status_code == 200:
                break
        except OSError:
            time.sleep(1.0)
    live = [0]
    lock = threading.Lock()
    stop = threading.Event()
    workers = [threading.Thread(target=_park_one_connection, args=(dut_ip, live, lock, stop, i * _RECYCLE_S / ceiling), daemon=True) for i in range(ceiling)]
    observed: list[int] = []
    try:
        for worker in workers:
            worker.start()
        time.sleep(_RECYCLE_S + 2.0)  # one full stagger cycle before the count is evidence
        while time.monotonic() < deadline:
            with lock:
                observed.append(live[0])
            time.sleep(0.25)
    finally:
        # Unconditional, and joined: a worker that outlives its test hammers the board for the rest
        # of the pytest session, which took down 37 unrelated tests once.
        stop.set()
        for worker in workers:
            worker.join(timeout=10.0)
    at_ceiling = sum(1 for count in observed if count >= ceiling)
    held_out.extend((min(observed, default=0), max(observed, default=0), at_ceiling, len(observed)))


def _restore_board_to_serving(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    """run_isolated() leaves main.py stopped, so the webserver is gone until a real hard reset. This
    is the only bench test that runs a device script, and without this every bench test after it
    fails on a refused connection."""
    bench.kick_all_stations()  # stale AP-side station entries stop the DUT reassociating (README)
    board.hard_reset()
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=90.0,
        poll_interval_s=3.0,
        description="DUT serving HTTP again after the device script left main.py stopped",
    )


def test_heap_at_peak_while_a_full_ceiling_is_held(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    ceiling = configured_max_connections()
    held_out: list[int] = []
    hammer = threading.Thread(target=_hold_ceiling_open, args=(dut_ip, ceiling, _HOLD_S, held_out), daemon=True)
    hammer.start()
    try:
        output = board.run_isolated(DEVICE_SCRIPTS / "heap_under_connection_ceiling.py", timeout_s=240.0)
    finally:
        hammer.join(timeout=_HOLD_S + 30.0)  # never leave the load generator running past this test
        holder_alive = hammer.is_alive()
        _restore_board_to_serving(board, bench, dut_ip)
    assert not holder_alive, "the connection holder is still running after its own test - it will hammer the board through every test that follows"

    assert not any(marker in output for marker in MEMORY_ERROR_MARKERS), f"the board logged an allocation failure while serving a full ceiling: {output[-2000:]}"
    # (min, max, samples at the ceiling, samples total), 4x a second. Recycling means one worker is
    # briefly between connections, so what makes this a peak reading is the FRACTION at the ceiling.
    assert len(held_out) == 4, f"the holder did not report a distribution: {held_out}"
    low, high, at_ceiling, total = held_out
    assert high >= ceiling, f"the count never reached the ceiling ({high} of {ceiling}) - the board did not admit a full set"
    assert total and at_ceiling / total >= _MIN_FRACTION_AT_CEILING, (
        f"the count was at the full ceiling for only {at_ceiling}/{total} samples (min {low}, max {high}) - "
        f"below the {_MIN_FRACTION_AT_CEILING:.0%} bar, so the heap dumps below are not a peak reading"
    )
    maps = heap_map.parse_labelled(output)
    assert len(maps) >= 3, f"expected an after_boot dump plus samples, got {sorted(maps)}"

    boot = maps["after_boot"]
    samples = [m for label, m in sorted(maps.items()) if label.startswith("t")]
    worst_run = min(m.largest_free_run for m in samples)
    worst_slots = min(m.placeable(PER_CONNECTION_ALLOCATION) for m in samples)
    print(
        f"[HW] ceiling={ceiling} held={low}-{high}, at ceiling {at_ceiling}/{total} | after boot: free={boot.free_bytes} "
        f"largest_free_run={boot.largest_free_run} placeable{PER_CONNECTION_ALLOCATION}B={boot.placeable(PER_CONNECTION_ALLOCATION)} "
        f"| at peak (worst of {len(samples)} samples): largest_free_run={worst_run} slots={worst_slots}",
    )
    # The one property worth asserting rather than reporting: the simultaneous demand must still be
    # placeable. A floor on the absolute bytes would be a guess; this is the actual requirement.
    assert worst_slots >= ceiling, (
        f"at peak the heap had room for only {worst_slots} more {PER_CONNECTION_ALLOCATION} B blocks "
        f"while holding {ceiling} connections - the simultaneous demand cannot be placed"
    )


@pytest.mark.over_provisioned_image
def test_report_the_boards_own_connection_wall(dut_ip: str) -> None:
    # Row 5 of the decision table, and the reason §5 needs only two images: this walks connections
    # upward at RUNTIME, so ONE deliberately over-provisioned build reports the board's real
    # capacity - whatever binds first, the PCB pool, the pbuf supply or the GC heap.
    configured = configured_max_connections()
    discovered = discover_max_connections(dut_ip, probe_limit=64)
    print(f"[HW] board admitted {discovered} simultaneous connections against a configured ceiling of {configured}")
    assert discovered >= 1, "the board admitted nothing at all"
    if discovered < configured:
        pytest.fail(
            f"THE WALL: the board admitted {discovered} of the {configured} its config allows - record this, "
            f"then use §6's LWIP_STATS image to see which pool ran out rather than inferring it",
        )
