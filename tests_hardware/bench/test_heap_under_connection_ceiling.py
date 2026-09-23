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
from harness import MEMORY_ERROR_MARKERS, configured_max_connections, discover_max_connections

if TYPE_CHECKING:
    from harness import Board

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
# microdot allocates max_content_length contiguously per connection (asy_webserver_service.py's own
# Request.max_content_length), so this is the block that has to be PLACEABLE N times over, not a
# fraction of total free. heap_map.gaps_at_least() counts exactly that.
PER_CONNECTION_ALLOCATION = 2048
# The script's own window is 90s and it prints READY about 20s in; this bounds the hold, not it.
_HOLD_S = 55.0


def _hold_ceiling_open(dut_ip: str, ceiling: int, seconds: float, held_out: list[int]) -> None:
    """Opens and keeps `ceiling` real connections, each mid-request, for the whole window. Driven
    from the host so nothing here competes with the DUT's own heap (SPECIFICATION.md Part E.9)."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:  # wait for the script's own boot to start serving
        try:
            if http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=3.0).status_code == 200:
                break
        except OSError:
            time.sleep(1.0)
    held: list[socket.socket] = []
    try:
        for _ in range(ceiling):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            try:
                sock.connect((dut_ip, 80))
            except OSError:
                sock.close()
                break
            # Headers only, no terminating blank line: the server is parked waiting for the rest,
            # which is what makes this a held connection rather than a completed request.
            sock.sendall(b"GET /sensors HTTP/1.1\r\nHost: dut\r\n")
            held.append(sock)
        held_out.append(len(held))
        while time.monotonic() < deadline:
            time.sleep(0.5)
    finally:
        for sock in held:
            sock.close()


def test_heap_at_peak_while_a_full_ceiling_is_held(board: Board, dut_ip: str) -> None:
    # UNTESTED ON HARDWARE as written (no board was reachable from the session that wrote it) - run
    # it late in the sitting, and expect the READY/IP handshake to be the part that needs a fix.
    ceiling = configured_max_connections()
    held_out: list[int] = []
    hammer = threading.Thread(target=_hold_ceiling_open, args=(dut_ip, ceiling, _HOLD_S, held_out), daemon=True)
    hammer.start()
    output = board.run_isolated(DEVICE_SCRIPTS / "heap_under_connection_ceiling.py", timeout_s=240.0)
    hammer.join(timeout=30.0)

    assert not any(marker in output for marker in MEMORY_ERROR_MARKERS), f"the board logged an allocation failure while serving a full ceiling: {output[-2000:]}"
    assert held_out and held_out[0] == ceiling, f"only {held_out} of {ceiling} connections were held open - the measurement below is not a full-ceiling reading"
    maps = heap_map.parse_labelled(output)
    assert len(maps) >= 3, f"expected an after_boot dump plus samples, got {sorted(maps)}"

    boot = maps["after_boot"]
    samples = [m for label, m in sorted(maps.items()) if label.startswith("t")]
    worst_run = min(m.largest_free_run for m in samples)
    worst_slots = min(m.gaps_at_least(PER_CONNECTION_ALLOCATION) for m in samples)
    print(
        f"[HW] ceiling={ceiling} held={held_out[0]} | after boot: free={boot.free_bytes} "
        f"largest_free_run={boot.largest_free_run} slots>={PER_CONNECTION_ALLOCATION}B={boot.gaps_at_least(PER_CONNECTION_ALLOCATION)} "
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
