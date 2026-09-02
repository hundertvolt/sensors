"""Bench-tier automated tests, Part 1 category G (tmp_hardware_test_candidates.md items 17, 22)
plus item 15 (moved here from flash - see tests_hardware/flash/test_reboot_persistence.py's own
module docstring for why: item 15's own description needs a real REST call to trigger the reboot,
which needs a reachable network, unavailable on flash tier)."""

from __future__ import annotations

import threading
import time

import http_client
from bench_control import BenchBridge
from harness import Board, wait_until

# ---------------------------------------------------------------------------
# Item 15 - real SystemService._reboot() sequencing: storage_pause()-then-wait genuinely completes
# before the real reset fires, WDT isn't starved mid-sequence, on real timing.
# ---------------------------------------------------------------------------


def test_real_reboot_sequencing_via_rest_completes_cleanly(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    res = http_client.fetch(dut_ip, 80, "PUT", "/system", {"SystemCmd": "reboot"})
    assert res.status_code == 200, f"PUT /system SystemCmd=reboot failed: {res.status_code} {res.body!r}"
    assert res.json()["result"]["SystemCmd"] == "Valid", f"reboot command was rejected: {res.json()!r}"
    # kick_all_stations() before the real reboot fires - this is a genuine machine.reset() under the
    # hood, subject to the same stale-AP-station-table finding as every other real reboot in this
    # tier (see conftest.py's dut_ip docstring for the full account).
    bench.kick_all_stations()

    # The real reset_timer fires after SystemService's own configured delay (not this test's to
    # assume a specific value for) - poll for the board actually going unreachable, then coming
    # back, rather than sleeping a guessed duration.
    wait_until(lambda: not board.is_reachable(), timeout_s=60.0, poll_interval_s=1.0, description="board to go unreachable (real reboot firing)")
    wait_until(board.is_reachable, timeout_s=30.0, poll_interval_s=1.0, description="board reachable again after the real reboot completes")


# ---------------------------------------------------------------------------
# Item 17 - real concurrent-client-burst stress test. The segfault this originally chased is
# confirmed compiled out of real rp2 firmware (MICROPY_PY_SELECT_POSIX_OPTIMISATIONS=0 there per
# tmp_hardware_test_candidates.md's own note) - this is standing robustness validation of the
# burst scenario itself, not chasing a specific bug.
# ---------------------------------------------------------------------------


def test_real_concurrent_client_burst_does_not_crash_the_webserver(dut_ip: str, board: Board) -> None:
    n_clients = 8
    results: list[int | str] = [0] * n_clients

    def _client(i: int) -> None:
        try:
            res = http_client.fetch(dut_ip, 80, "GET", "/measurements", timeout_s=10.0)
            results[i] = res.status_code
        except OSError as exc:
            results[i] = repr(exc)

    threads = [threading.Thread(target=_client, args=(i,)) for i in range(n_clients)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15.0)

    failures = [r for r in results if r != 200]
    assert not failures, f"{len(failures)}/{n_clients} concurrent requests failed or errored: {results}"
    # The webserver must still be responsive afterward - a crash that only surfaces after the
    # burst (not during it) would otherwise slip through the per-request results above.
    assert board.is_reachable() or http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after the concurrent burst"


# ---------------------------------------------------------------------------
# Item 22 - cold-boot-to-first-response latency: real WiFi-connect + NTP + sensor-init timing
# budget. Reported/sanity-bounded rather than asserted against a tight SLA - no measured real-
# hardware baseline exists yet to validate a tighter bound against (flagged, not guessed).
# ---------------------------------------------------------------------------


def test_cold_boot_to_first_http_response_latency_is_sane(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # kick_all_stations() first - see conftest.py's dut_ip docstring for the full stale-AP-station-
    # table finding this real hard_reset() would otherwise be exposed to.
    bench.kick_all_stations()
    board.hard_reset()
    start = time.monotonic()
    wait_until(
        lambda: _try_fetch_ok(dut_ip),
        timeout_s=120.0,  # generous sanity ceiling, not a validated tight budget - see this test's own docstring
        poll_interval_s=1.0,
        description="first successful HTTP response after a cold boot",
    )  # raises TimeoutError with context on its own if never reached - nothing further to assert here
    elapsed_s = time.monotonic() - start
    print(f"cold-boot-to-first-response latency: {elapsed_s:.1f}s")  # reported for a human to eyeball against future runs - no asserted threshold yet


def _try_fetch_ok(dut_ip: str) -> bool:
    try:
        return http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200
    except OSError:
        return False
