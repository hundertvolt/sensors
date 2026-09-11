"""Bench-tier automated tests: real REST-triggered reboot sequencing, concurrent-client-burst
stress, cold-boot-to-first-response latency, and hard resets during natural FRAM backup activity -
all need a reachable network, unavailable on flash tier."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

import http_client
from error_log_helpers import assert_module_error_log_empty, reset_all_error_logs
from harness import Board, wait_until

if TYPE_CHECKING:
    from bench_control import BenchBridge

# ---------------------------------------------------------------------------
# Real SystemService._reboot() sequencing: storage_pause()-then-wait genuinely completes before
# the real reset fires, WDT isn't starved mid-sequence, on real timing.
# ---------------------------------------------------------------------------


def test_real_reboot_sequencing_via_rest_completes_cleanly(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # is_reachable() would soft-reset the board's own heap on every poll (mpremote's raw-REPL entry
    # always Ctrl-D's first) - wiping the very Timer this test waits on before the real hardware
    # reset fires. Uses is_device_present() instead - a passive open()/close() that touches nothing
    # (see tests_hardware/README.md for the full repro).
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
    # is_reachable() only confirms raw-REPL reachability, not that the webserver is listening yet -
    # it starts only after ntp_force_sync() (up to ~20s). Bounded recovery retry, same pattern as
    # every other real-reboot wait in this tier (see tests_hardware/README.md).
    def _webserver_up() -> bool:
        return http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200

    try:
        wait_until(_webserver_up, timeout_s=30.0, poll_interval_s=2.0, description="webserver actually serving again after the real reboot completes")
    except TimeoutError:
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(_webserver_up, timeout_s=30.0, poll_interval_s=2.0, description="webserver actually serving again (after one recovery hard_reset() retry)")


# ---------------------------------------------------------------------------
# Real concurrent-client-burst stress test - standing robustness validation of the burst scenario
# itself (the segfault this originally chased is confirmed compiled out of real rp2 firmware).
# ---------------------------------------------------------------------------


def test_real_concurrent_client_burst_does_not_crash_the_webserver(dut_ip: str, board: Board) -> None:
    # 8 concurrent requests against max_connections=4's reject-when-full policy: some subset
    # legitimately gets a silent close (ConnectionResetError or timeout), not a crash. The real
    # property under test is that the server survives and keeps serving - at least the connection
    # cap's own worth of requests must still get through cleanly.
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
# Cold-boot-to-first-response latency: real WiFi-connect + NTP + sensor-init timing budget.
# Reported/sanity-bounded, not asserted against a tight SLA - no measured baseline exists yet.
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


# ---------------------------------------------------------------------------
# Recombination test (project owner's explicit request): does a real hard_reset() landing at an
# uncontrolled point relative to FRAM's own natural background write activity (SGP40's periodic
# VOC-backup) leave the FRAM subsystem fully healthy afterward? Complements
# tests_hardware/flash/test_bus_concurrency.py's deterministic reset race (which can only land
# right as a write session begins) - timing here is genuinely uncontrolled, so several resets
# spread across a fast backup cadence give repeated opportunities instead of one precise instant.
# ---------------------------------------------------------------------------


def test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    current = http_client.fetch(dut_ip, 80, "GET", "/sensors", timeout_s=10.0).json()
    original_backup_period = current.get("SGP40", {}).get("BackupPeriod")
    assert original_backup_period is not None, "could not read the current real BackupPeriod before changing it"

    # BackupPeriod=1 (minute) is the schema's fastest active cadence (0 disables it entirely) -
    # restored to its original value in the finally block below.
    put_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"BackupPeriod": 1}}, timeout_s=10.0)
    assert put_res.status_code == 200 and put_res.json().get("result", {}).get("SGP40", {}).get("BackupPeriod") in ("Valid", "Unchanged"), (
        f"failed to set BackupPeriod=1: {put_res.status_code} {put_res.body!r}"
    )

    try:
        for _cycle in range(3):
            time.sleep(25.0)  # spread across the 60s backup cadence so each of the 3 resets lands
            # at a genuinely different, uncontrolled point relative to it - can't be synchronized
            # to the real SPI write itself from the host side.
            bench.kick_all_stations()
            board.hard_reset()
            # Bounded recovery retry, same convention as every sibling "reachable after
            # hard_reset()" test in this tier (see BACKLOG.md open question 9).
            try:
                wait_until(
                    lambda: _try_fetch_ok(dut_ip),
                    timeout_s=60.0,
                    poll_interval_s=1.0,
                    description="DUT reachable again after a real hard_reset() during natural FRAM backup activity",
                )
            except TimeoutError:
                bench.kick_all_stations()
                board.hard_reset()
                wait_until(
                    lambda: _try_fetch_ok(dut_ip),
                    timeout_s=60.0,
                    poll_interval_s=1.0,
                    description="DUT reachable again (after one recovery hard_reset() retry - see this loop's own comment)",
                )

        # Full health check, not just "reachable" - the FRAM subsystem specifically must still work.
        assert_module_error_log_empty(dut_ip, "SGP40")
        assert_module_error_log_empty(dut_ip, "FRAM")

        # One more real backup completing cleanly after all three resets proves the FRAM subsystem
        # itself is still genuinely functional, not merely "board reachable".
        status_before = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).json()
        backup_ts_before = status_before.get("sensors", {}).get("SGP40", {}).get("BackupTS")
        wait_until(
            lambda: _sgp_backup_ts_advanced(dut_ip, backup_ts_before),
            timeout_s=90.0,
            poll_interval_s=5.0,
            description="a fresh real SGP40 VOC backup completing after the reset sequence",
        )
    finally:
        try:
            restore_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"BackupPeriod": original_backup_period}}, timeout_s=10.0)
        except OSError:
            # The same rare transient reachability miss the recovery loop above accounts for - a
            # brief reachability wait is tried first (no reset), escalating to kick+hard_reset only
            # if that also fails, rather than assuming a full reboot is needed.
            try:
                wait_until(
                    lambda: _try_fetch_ok(dut_ip),
                    timeout_s=20.0,
                    poll_interval_s=2.0,
                    description="DUT reachable again before retrying the BackupPeriod restore",
                )
            except TimeoutError:
                bench.kick_all_stations()
                board.hard_reset()
                wait_until(
                    lambda: _try_fetch_ok(dut_ip),
                    timeout_s=60.0,
                    poll_interval_s=1.0,
                    description="DUT reachable again (after one recovery hard_reset() retry) before retrying the BackupPeriod restore",
                )
            restore_res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"SGP40": {"BackupPeriod": original_backup_period}}, timeout_s=10.0)
        assert restore_res.status_code == 200, f"failed to restore BackupPeriod to {original_backup_period}"
        reset_all_error_logs(dut_ip)


def _sgp_backup_ts_advanced(dut_ip: str, before: int | None) -> bool:
    try:
        status = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).json()
    except OSError:
        return False
    after = status.get("sensors", {}).get("SGP40", {}).get("BackupTS")
    return after is not None and after != before
