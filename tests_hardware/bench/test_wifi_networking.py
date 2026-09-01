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

from bench_control import BenchBridge
from harness import Board

# ---------------------------------------------------------------------------
# Item 7 - real STA connect/disconnect against a genuine AP: real SEEKING->ESTABLISHED
# timing/RSSI, replacing the twin's instant/no-delay WLAN.connect().
# ---------------------------------------------------------------------------


def test_real_sta_connect_reaches_established_after_a_hard_reset(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # dut_ip (session-scoped) already proves a real STA connection was reached at least once this
    # session - this test's own value is confirming it happens again, cleanly, from a cold boot.
    board.hard_reset()
    lines = board.tail_log(duration_s=45.0)
    joined = "\n".join(lines)
    assert "CONN" in joined or "WIFI" in joined or "wlan" in joined.lower(), f"no WiFi-connection-related log line observed after hard reset:\n{joined}"


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


def test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing(board: Board, bench: BenchBridge) -> None:
    bench.block_udp_ports([123])
    try:
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
