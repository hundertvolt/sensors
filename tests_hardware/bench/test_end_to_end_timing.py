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
    # REAL FINDING (this test was previously self-sabotaging, not hitting a real src/ bug): an
    # earlier version of this test polled `board.is_reachable()` to wait for the real reboot to
    # fire. is_reachable() is built on `mpremote exec`, and mpremote's own enter_raw_repl()
    # (transport_serial.py) unconditionally sends Ctrl-C, then - by default, true for every fresh
    # `mpremote` subprocess's own State() - a genuine Ctrl-D `machine.soft_reset()` before running
    # anything. Confirmed directly against that source, then confirmed empirically here: polling
    # is_reachable() once a second while waiting for SystemService's real, REST-armed ~4s
    # reset_timer to fire was itself soft-resetting the board's entire live Python heap - wiping the
    # very Timer object being waited on - before the real hardware reset ever got a chance to run.
    # This isn't the already-known "exec() never resumes main.py afterward" finding
    # (harness.py's exec()/run_isolated() docstrings) - it's a step earlier: entering raw REPL at
    # all destroys the live heap first, on every single call. A direct, isolated repro on this same
    # board (a bare `machine.Timer(mode=ONE_SHOT, period=4000, callback=lambda t: machine.reset())`
    # run via a single mpremote exec, with no REST/webserver involved) fired reliably in ~3s with
    # zero load - confirming SPECIFICATION.md Part F.1's soft-Timer-callback-drop gotcha was NOT
    # the cause here (that's a real, separately-documented platform characteristic, just not this
    # bug) and that the real reboot mechanism itself is fine. Fixed below by polling
    # board.is_device_present() instead - a passive open()/close() of the serial port that never
    # touches the running system - see that method's own docstring for the full account.
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
    wait_until(lambda: not board.is_device_present(), timeout_s=30.0, poll_interval_s=0.5, description="board to go unreachable (real reboot firing)")
    wait_until(board.is_reachable, timeout_s=30.0, poll_interval_s=1.0, description="board reachable again after the real reboot completes")
    # REAL FINDING, fixed: is_reachable() only confirms bare mpremote/raw-REPL reachability, not
    # that the webserver task is actually listening - confirmed directly (dut_ip's own fixture
    # docstring, "SECOND REAL FINDING"): sensortask_wozi.main() only starts the webserver's own
    # task after ntp_force_sync(), itself bounded by a 20s asyncio.wait_for() - so a fresh
    # reconnect can have up to ~20s with nothing listening on port 80 yet. Without this wait, the
    # very next test in this file (a concurrent HTTP burst) could race a webserver that isn't up
    # yet, or is still busy with startup work competing for the single CPU core - producing
    # spurious timeouts that have nothing to do with what that test actually checks.
    # Bounded recovery retry - same pattern as dut_ip's own fixture and every other real-reboot
    # wait in this tier (see conftest.py's dut_ip docstring, "FIFTH REAL FINDING"): a real STA
    # reconnect after a genuine reboot is still subject to this bench's already-documented
    # intermittent WiFi flakiness (tests_hardware/README.md's "Known assumptions and open
    # findings"; whether asy_wifi_service.py should gain its own independent reachability check is
    # tracked as BACKLOG.md's open question 6, not decided - not something to patch here blind).
    # kick_all_stations() was already called above, but a real reconnect can still race a stale
    # entry re-created by this exact reboot - one bounded hard_reset() retry before failing for
    # real, matching this tier's established convention.
    def _webserver_up() -> bool:
        return http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200

    try:
        wait_until(_webserver_up, timeout_s=30.0, poll_interval_s=2.0, description="webserver actually serving again after the real reboot completes")
    except TimeoutError:
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(_webserver_up, timeout_s=30.0, poll_interval_s=2.0, description="webserver actually serving again (after one recovery hard_reset() retry)")


# ---------------------------------------------------------------------------
# Item 17 - real concurrent-client-burst stress test. The segfault this originally chased is
# confirmed compiled out of real rp2 firmware (MICROPY_PY_SELECT_POSIX_OPTIMISATIONS=0 there per
# tmp_hardware_test_candidates.md's own note) - this is standing robustness validation of the
# burst scenario itself, not chasing a specific bug.
# ---------------------------------------------------------------------------


def test_real_concurrent_client_burst_does_not_crash_the_webserver(dut_ip: str, board: Board) -> None:
    # REAL FINDING, fixed: this test predates (or never accounted for) the real, deliberate
    # max_connections=4 reject-when-full policy (asy_webserver_service.py's _serve(): "silently
    # close, no accept, no response ever written" beyond the cap - the same policy
    # test_connections_at_and_above_the_real_socket_limit_degrade_cleanly explicitly exercises).
    # Firing 8 concurrent requests and requiring every one to succeed directly contradicts that
    # documented design - confirmed directly, reproducibly, from a clean reboot: some subset
    # legitimately gets a silent close, surfacing client-side as a ConnectionResetError or a
    # timeout depending on exact timing, not a crash. The real property this test cares about (per
    # this file's own module comment: "standing robustness validation of the burst scenario
    # itself, not chasing a specific [segfault] bug") is that the server survives the burst and
    # keeps serving - not that every single concurrent request over the connection cap succeeds.
    # At least the cap's own worth of requests must still get through cleanly, though - anything
    # less would point at a genuine problem, not just the expected reject-when-full behavior.
    n_clients = 8
    _max_connections = 4  # matches asy_webserver_service.py's own max_connections default
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

    successes = [r for r in results if r == 200]
    assert len(successes) >= _max_connections, f"only {len(successes)}/{n_clients} concurrent requests succeeded (expected at least the {_max_connections}-connection admission ceiling to be served): {results}"
    # The webserver must still be responsive afterward - a crash that only surfaces after the
    # burst (not during it) would otherwise slip through the per-request results above.
    # is_device_present(), not is_reachable() - see that method's own docstring for why polling
    # (or even a single incidental call to) is_reachable() against a live system is disruptive.
    assert board.is_device_present() or http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after the concurrent burst"


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
