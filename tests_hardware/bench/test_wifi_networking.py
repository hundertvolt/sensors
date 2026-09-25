"""Bench-tier automated tests: real STA connect, real NTP, real DNS, and NTP-timeout-under-loss
over genuine lwIP/UDP (real captive-DNS/bind(53) lives in test_hotspot_role_reversal.py instead).
Uses passive observation (Board.tail_log()), not exec()/run_isolated() - see run_isolated()."""

from __future__ import annotations

from typing import TYPE_CHECKING

import http_client
from error_log_helpers import assert_module_error_log_contains, assert_no_task_ended, reset_all_error_logs
from harness import Board, wait_until

if TYPE_CHECKING:
    from bench_control import BenchBridge

# ---------------------------------------------------------------------------
# Item 7 - real STA connect/disconnect against a genuine AP: real SEEKING->ESTABLISHED
# timing/RSSI, replacing the twin's instant/no-delay WLAN.connect().
# ---------------------------------------------------------------------------


def test_real_sta_connect_reaches_established_after_a_hard_reset(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # dut_ip (session-scoped) already proves a real STA connection was reached once this session -
    # this test's own value is confirming it happens again, cleanly, from a cold boot.
    #
    # kick_all_stations() first: a stale AP-side station-table entry for the DUT's MAC is the
    # dominant cause of a hard_reset()-triggered reconnect failing here - see kick_client()'s own
    # docstring. This is the primary regression coverage for that exact scenario.
    #
    # One real association can fail for reasons outside the DUT (measured 2026-09-19: 1 miss in 3
    # full suite runs, 12/12 clean in isolation, CYW43 reporting status -1 after the firmware's own
    # two retries). A second cold boot separates that from a break, which fails both - queue F13.
    attempts = []
    for attempt in range(2):
        bench.kick_all_stations()
        board.hard_reset()
        joined = "\n".join(board.tail_log(duration_s=45.0))
        established = "WLAN connection established" in joined and "Permanently no WLAN connection" not in joined
        attempts.append(joined)
        if established:
            if attempt:
                print("RESULT NOTE: STA connect needed a second cold boot - one association was missed")
            break
    assert "Permanently no WLAN connection" not in attempts[-1], f"DUT fell back to hotspot mode instead of establishing a real STA connection, on {len(attempts)} consecutive cold boots:\n{attempts[-1]}"
    assert "WLAN connection established" in attempts[-1], f"no 'WLAN connection established' log line observed after {len(attempts)} cold boots:\n{attempts[-1]}"


# ---------------------------------------------------------------------------
# Real NTP round-trip over genuine lwIP/UDP - the first time the real rp2/lwIP transport is
# exercised (the twin's _unix_port_udp_addr_shim.py only papers over Unix-port-only quirks).
# ---------------------------------------------------------------------------


def test_real_ntp_sync_succeeds_over_genuine_udp(board: Board) -> None:
    lines = board.tail_log(duration_s=60.0)
    joined = "\n".join(lines)
    failure_markers = [ln for ln in lines if "NTP" in ln and ("fail" in ln.lower() or "error" in ln.lower() or "timeout" in ln.lower())]
    assert not failure_markers, "observed NTP failure/error/timeout log lines during a window with no fault injected:\n" + "\n".join(failure_markers)
    assert "NTP" in joined, f"no NTP-related log line observed at all within the window:\n{joined}"


# ---------------------------------------------------------------------------
# Real DNS resolution via asy_dns_client.py's own resolver, same rationale as the NTP test above.
# ---------------------------------------------------------------------------


def test_real_dns_resolution_succeeds_over_genuine_udp(board: Board) -> None:
    lines = board.tail_log(duration_s=60.0)
    failure_markers = [ln for ln in lines if "DNS" in ln and ("fail" in ln.lower() or "error" in ln.lower())]
    assert not failure_markers, "observed DNS failure/error log lines during a window with no fault injected:\n" + "\n".join(failure_markers)


# ---------------------------------------------------------------------------
# Real NTP-unreachable timeout under genuine network loss, scripted via a temporary iptables DROP
# on UDP 123 (block_udp_ports()) - no physical action needed.
# ---------------------------------------------------------------------------


def test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # This tier's real-hardware proof for BACKLOG open question 6: only UDP 123 is blocked, not
    # the AP, so the STA link stays up - "isconnected()==True but one downstream operation is
    # unreachable", which tests/test_ntp_wifi_dns_integration.py proves at the mock level.
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

    # Bounded recovery retry, same rationale as conftest.py's dut_ip fixture: a hard_reset()
    # occasionally lands on a real, disclosed CYW43-firmware/AP-state characteristic rather than
    # this test's own scenario - one more retry cycle before treating it as a real failure.
    try:
        wait_until(lambda: _http_ok(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again after the hard_reset() above")
    except TimeoutError:
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(lambda: _http_ok(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again (after one recovery hard_reset() retry - see this test's own comment)")
    # A blocked port is routine for NTP (SPECIFICATION.md Part C.7.2): errno 21 (no reply) is logged
    # and the task backs off in place - it must never end and cost the supervisor's reboot budget.
    assert_module_error_log_contains(dut_ip, "NTP", 21, "E")
    restarts = [ln for ln in lines if "Task ended - attempting restart" in ln]
    assert not restarts, "a blocked NTP server made a task end and be restarted:\n" + "\n".join(restarts)
    assert_no_task_ended(dut_ip, "a blocked NTP server")  # the persisted record, beyond the tail window


def _http_ok(dut_ip: str) -> bool:
    try:
        return http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200
    except OSError:
        return False
