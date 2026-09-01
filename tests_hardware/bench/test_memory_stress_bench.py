"""Bench-tier automated test, Part 1 category D subset (tmp_hardware_test_candidates.md item 16,
moved here from flash - see tests_hardware/flash/test_memory_stress.py's own module docstring for
why: this candidate's own description needs "real firmware under HTTP soak traffic", which needs a
reachable network client, unavailable on flash tier).

Design note - why this doesn't sample gc.mem_free() directly the way the digital twin's own
recovery-peak-trend soak does (digital_twin/run_wozi_integration.py): doing that here would need
repeated harness.Board.exec() calls interleaved with the HTTP soak traffic, but exec() always
interrupts the live system first (see run_isolated()'s own docstring) - a KeyboardInterrupt into a
running asyncio.run() call does not resume on its own once the raw-REPL session ends, so repeated
sampling this way would permanently kill the live system partway through its own soak. Real HTTP
soak traffic is generated over WiFi only (http_client, never touching the serial console), in
parallel with a purely passive tail_log() watch for the two disqualifying symptoms genuinely
observable without disturbing anything: a MemoryError traceback, or an unexpected mid-soak reboot."""

from __future__ import annotations

import threading

import http_client
import pytest
from harness import Board


@pytest.mark.long_soak
def test_real_hardware_memory_does_not_leak_under_real_http_soak_traffic(board: Board, dut_ip: str, request: pytest.FixtureRequest) -> None:
    if not request.config.getoption("--run-long-soak"):
        pytest.skip("multi-minute+ real HTTP soak - pass --run-long-soak to actually run this")
    duration_s = request.config.getoption("--long-soak-seconds")
    stop = threading.Event()
    request_errors: list[str] = []

    def _hammer() -> None:
        paths = ("/measurements", "/sensors", "/status", "/networking")
        i = 0
        while not stop.is_set():
            path = paths[i % len(paths)]
            i += 1
            try:
                res = http_client.fetch(dut_ip, 80, "GET", path, timeout_s=5.0)
                if res.status_code != 200:
                    request_errors.append(f"GET {path} -> {res.status_code}")
            except OSError as exc:  # a real transient network hiccup during a long soak is expected sometimes
                request_errors.append(f"GET {path} -> {exc!r}")
            stop.wait(0.2)  # a modest, sustained request rate - not a flood (that's item 17's job)

    hammer_thread = threading.Thread(target=_hammer, daemon=True)
    hammer_thread.start()
    try:
        lines = board.tail_log(duration_s=duration_s)
    finally:
        stop.set()
        hammer_thread.join(timeout=10.0)

    joined = "\n".join(lines)
    crash_markers = [ln for ln in lines if "MemoryError" in ln or "Traceback" in ln]
    reboot_markers = [ln for ln in lines if "CFGMGR_" in ln or "FRAM SPI FRAM Driver Setup complete" in ln]
    assert not crash_markers, "observed a crash/MemoryError during the HTTP soak:\n" + "\n".join(crash_markers)
    assert not reboot_markers, "observed an unexpected mid-soak reboot (real memory exhaustion -> WDT reset?):\n" + "\n".join(reboot_markers) + f"\nfull log:\n{joined}"
    assert len(request_errors) < 5, f"too many failed/non-200 requests during the soak ({len(request_errors)}): {request_errors[:10]}"
