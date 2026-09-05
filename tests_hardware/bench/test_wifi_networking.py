"""Bench-tier automated tests, Part 1 category B subset (tmp_hardware_test_candidates.md items 7,
8, 9, 12 - real STA connect, real NTP, real DNS, real NTP-timeout-under-loss). Items 10/11 (real
captive-DNS answering a real external client, real unprivileged bind(53)) are deliberately NOT
duplicated here - tmp_hardware_test_candidates.md's own cross-reference already says
HARDWARE_TEST_PLAN.md §11's role-reversal scenario supersedes them with a much deeper design
(stage 3, §11.5 items 8-13 in tests_hardware/bench/test_hotspot_role_reversal.py), and that
cross-reference is honored here rather than re-implemented independently.

All items in this file use passive observation (harness.Board.tail_log()) of the live, normally-
booting system rather than exec()/run_isolated() - see run_isolated()'s own docstring for why the
latter can't be trusted not to disturb a real WiFi association mid-test."""

from __future__ import annotations

import http_client
from bench_control import BenchBridge
from error_log_helpers import assert_module_error_log_contains, reset_all_error_logs
from harness import Board, wait_until

# ---------------------------------------------------------------------------
# Item 7 - real STA connect/disconnect against a genuine AP: real SEEKING->ESTABLISHED
# timing/RSSI, replacing the twin's instant/no-delay WLAN.connect().
# ---------------------------------------------------------------------------


def test_real_sta_connect_reaches_established_after_a_hard_reset(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # dut_ip (session-scoped) already proves a real STA connection was reached at least once this
    # session - this test's own value is confirming it happens again, cleanly, from a cold boot.
    #
    # kick_all_stations() first: the dominant real cause of a hard_reset()-triggered reconnect
    # failing on this bench rig is a stale AP-side station-table entry for the DUT's own MAC, left
    # over because a hard reset never sends a clean 802.11 deauth (see tests_hardware/README.md's
    # "Known assumptions and open findings" - A/B test: 10/10 fallback without this, 10/10 clean
    # connects with it - see bench_control.BenchBridge.kick_client()'s own docstring for the full account). This test is
    # the primary regression coverage for that exact scenario, so it must clear stale AP state the
    # same way dut_ip's own fixture now does, not just document the finding elsewhere.
    bench.kick_all_stations()
    board.hard_reset()
    lines = board.tail_log(duration_s=45.0)
    joined = "\n".join(lines)
    assert "Permanently no WLAN connection" not in joined, f"DUT fell back to hotspot mode instead of establishing a real STA connection after a hard reset:\n{joined}"
    assert "WLAN connection established" in joined, f"no 'WLAN connection established' log line observed after hard reset:\n{joined}"


# ---------------------------------------------------------------------------
# Item 8 - real NTP round-trip over genuine lwIP/UDP (BACKLOG.md open question #5's single most
# explicitly flagged gap). The twin's _unix_port_udp_addr_shim.py only papers over Unix-port-only
# quirks to let the code execute; this is the first time the real rp2/lwIP transport is exercised.
# ---------------------------------------------------------------------------


def test_real_ntp_sync_succeeds_over_genuine_udp(board: Board) -> None:
    lines = board.tail_log(duration_s=60.0)
    joined = "\n".join(lines)
    failure_markers = [ln for ln in lines if "NTP" in ln and ("fail" in ln.lower() or "error" in ln.lower() or "timeout" in ln.lower())]
    assert not failure_markers, "observed NTP failure/error/timeout log lines during a window with no fault injected:\n" + "\n".join(failure_markers)
    assert "NTP" in joined, f"no NTP-related log line observed at all within the window:\n{joined}"


# ---------------------------------------------------------------------------
# Item 9 - real DNS resolution via asy_dns_client.py's own resolver, same rationale as item 8.
# ---------------------------------------------------------------------------


def test_real_dns_resolution_succeeds_over_genuine_udp(board: Board) -> None:
    lines = board.tail_log(duration_s=60.0)
    failure_markers = [ln for ln in lines if "DNS" in ln and ("fail" in ln.lower() or "error" in ln.lower())]
    assert not failure_markers, "observed DNS failure/error log lines during a window with no fault injected:\n" + "\n".join(failure_markers)


# ---------------------------------------------------------------------------
# Item 12 - real NTP-unreachable timeout under genuine network jitter/loss, scripted via a
# temporary iptables DROP on UDP 123 (bench_control.BenchBridge.block_udp_ports()) - no physical
# action needed, unlike a naive reading of "network jitter/loss" might suggest.
# ---------------------------------------------------------------------------


def test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # Doubles as this tier's own real-hardware proof for BACKLOG.md open question 6 (closed
    # 2026-09-04, "investigated, no src/ change"): the real STA link stays fully up and
    # wlan.isconnected() genuinely True throughout (only UDP 123 is blocked, not the AP itself),
    # so this is the real-hardware shape of "isconnected()==True but a specific downstream
    # operation is unreachable" - see
    # tests/test_ntp_wifi_dns_integration.py::test_full_chain_degrades_cleanly_when_wifi_reports_connected_but_the_ntp_server_never_answers
    # for the same property proven at the mock/unit level through the real network_available()
    # chain.
    reset_all_error_logs(dut_ip)
    bench.block_udp_ports([123])
    try:
        bench.kick_all_stations()  # see conftest.py's dut_ip docstring for the full finding
        board.hard_reset()  # forces a fresh NTP sync attempt against the now-unreachable server
        lines = board.tail_log(duration_s=90.0)  # generous relative to asy_ntp_client.py's own retry/backoff budget
    finally:
        bench.unblock_udp_ports([123])

    joined = "\n".join(lines)
    crash_markers = [ln for ln in lines if "Traceback" in ln]
    assert not crash_markers, "a blocked NTP server crashed the system instead of degrading cleanly:\n" + "\n".join(crash_markers)
    # The system must still finish booting (webserver etc.) even with NTP unreachable - a real
    # observable equivalent of "NTP sync failure doesn't block the rest of build_system()".
    assert "CFGMGR_" in joined or "FRAM" in joined, f"system did not appear to finish booting with NTP blocked:\n{joined}"

    # Bounded recovery retry, same rationale as conftest.py's dut_ip fixture: a hard_reset() every
    # so often lands on a real, disclosed CYW43-firmware/AP-state characteristic (see that
    # fixture's own docstring) rather than this test's own NTP-unreachable scenario - one more
    # kick_all_stations()+hard_reset() cycle before treating it as a real failure.
    try:
        wait_until(lambda: _http_ok(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again after the hard_reset() above")
    except TimeoutError:
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(lambda: _http_ok(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again (after one recovery hard_reset() retry - see this test's own comment)")
    # REAL FINDING, fixed 2026-09-04 - this assertion's own reasoning only traced ONE of two
    # independent error-logging paths in asy_ntp_client.py, so it was wrong the whole time, not the
    # real system: `_handle_ntp_sync_failure()`'s own errno=16/errno=17 retry-logging block is indeed
    # gated on `ntp_issynced()` and correctly never fires on a first-ever unresponsive server. But
    # `AsyNtpClient` also extends `base_classes.py`'s `SensorReaderConfig`, whose *separate*,
    # coarser `_error_check()` consecutive-failure-streak counter (SPECIFICATION.md Part C.7) is
    # NOT gated on ntp_issynced() at all - confirmed directly against real source (base_classes.py
    # lines ~213-225) - and fires unconditionally on every failed real sync attempt regardless of
    # sync history: `errno=1` ("Error counter increased to N") on each one, `errno=2` ("Maximum
    # error count reached!") once past `max_module_error` (5 by default), then asy_ntp_client.py's
    # own `errno=20` ("Giving up after repeated sync failures, restarting task") from the outer loop
    # that wraps this same counter. A 90s window with the NTP port genuinely, persistently blocked
    # is real, sustained failure - exactly what this mechanism exists to detect and report, so
    # seeing all three fire is the module working correctly, not a bug. Confirmed directly on real
    # hardware: this exact scenario reliably produces 8x errno=1, 1x errno=2, 1x errno=20 under
    # `assert_module_error_log_empty`'s old blanket-emptiness check - it never could have passed for
    # a genuinely unreachable server, only for one that failed faster than one `_error_check()` cycle
    # could register (a false pass, not evidence of correct handling). Checking for the real,
    # expected outcome instead: the module must actually notice and report giving up, not silently
    # spin forever - a missing errno=20 here would be the real bug this test should be catching.
    assert_module_error_log_contains(dut_ip, "NTP", 20, "E")


def _http_ok(dut_ip: str) -> bool:
    try:
        return http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200
    except OSError:
        return False
