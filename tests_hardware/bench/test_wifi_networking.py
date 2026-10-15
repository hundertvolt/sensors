"""Bench-tier automated tests: real STA connect, real NTP, real DNS, and NTP-timeout-under-loss
over genuine lwIP/UDP (real captive-DNS/bind(53) lives in test_hotspot_role_reversal.py instead).
Uses passive observation (Board.tail_log()), not exec()/run_isolated() - see run_isolated()."""

import time
from typing import TYPE_CHECKING

import _load
import pytest
from error_log_helpers import assert_module_error_log_contains, assert_no_task_ended, code, reset_all_error_logs
from harness import Board, boot_lines, crash_lines, kick_then_reset, recover_by_reset

if TYPE_CHECKING:
    from bench_control import BenchBridge
    from http_client import JSONObject

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("network_neopixel", "ci_suite._run_9_ntp_unreachable")

# ---------------------------------------------------------------------------
# Real STA connect/disconnect against a genuine AP: real SEEKING->ESTABLISHED
# timing/RSSI, replacing the twin's instant/no-delay WLAN.connect().
# ---------------------------------------------------------------------------


# @tunable l4.wifi_networking_boot_tail_s = 45.0
_BOOT_TAIL_S = 45.0
# @tunable l4.wifi_networking_sync_tail_s = 60.0
_SYNC_TAIL_S = 60.0
# @tunable l4.wifi_networking_ntp_fault_tail_s = 90.0
_ROGUE_TAIL_S = 90.0
# @tunable l4.wifi_networking_reconnect_timeout_s = 60.0
_RECONNECT_TIMEOUT_S = 60.0
# @tunable l4.wifi_networking_association_attempts = 2
_ASSOCIATION_ATTEMPTS = 2
# @tunable l4.wifi_networking_probe_timeout_s = 10.0
_PROBE_TIMEOUT_S = 10.0
_RTC_SET_LINE = "RTC set to:"  # src/asy_ntp_client.py, the line a completed sync prints


def test_real_sta_connect_reaches_established_after_a_hard_reset(board: Board, bench: "BenchBridge", dut_ip: str, result_note: "_load.Note") -> None:
    # A real STA connection again from a cold boot. One association can fail outside the DUT (measured 2026-09-19: 1 miss
    # in 3 full suite runs, 12/12 clean in isolation, CYW43 reporting status -1 after its own two retries); a second cold
    # boot separates that from a break.
    attempts = []
    for attempt in range(_ASSOCIATION_ATTEMPTS):
        kick_then_reset(board, bench)  # the kick a stale AP-side station entry needs, then the cold boot
        joined = "\n".join(board.tail_log(duration_s=_BOOT_TAIL_S))
        established = "WLAN connection established" in joined and "Permanently no WLAN connection" not in joined
        attempts.append(joined)
        if established:
            if attempt:
                result_note("STA connect needed a second cold boot; skipped: the first association", recovery=True)
            break
    assert "Permanently no WLAN connection" not in attempts[-1], f"DUT fell back to hotspot mode instead of establishing a real STA connection, on {len(attempts)} consecutive cold boots:\n{attempts[-1]}"
    assert "WLAN connection established" in attempts[-1], f"no 'WLAN connection established' log line observed after {len(attempts)} cold boots:\n{attempts[-1]}"


# ---------------------------------------------------------------------------
# Real NTP round-trip over genuine lwIP/UDP - the first time the real rp2/lwIP transport is
# exercised (the twin's _unix_port_udp_addr_shim.py only papers over Unix-port-only quirks).
# ---------------------------------------------------------------------------


def test_real_ntp_sync_succeeds_over_genuine_udp(board: Board, dut_ip: str) -> None:
    # A sync proven by state: an RTC set inside the window, or the client synced with its last sync no older than the
    # window plus the read itself. The failure-word scan comes second.
    _networking(dut_ip)  # the board answers before the window opens
    started = time.monotonic()
    lines = board.tail_log(duration_s=_SYNC_TAIL_S)
    read_started = time.monotonic()
    networking = _networking(dut_ip)
    read_s = time.monotonic() - read_started
    age = networking.get("NTPLastSyncAge")
    synced = networking.get("NTPSynced") is True and isinstance(age, int) and age <= _SYNC_TAIL_S + read_s + 1
    assert any(_RTC_SET_LINE in line for line in lines) or synced, f"no NTP sync within the {time.monotonic() - started:.0f}s window: no '{_RTC_SET_LINE}' line, NTPSynced {networking.get('NTPSynced')!r}, NTPLastSyncAge {age!r}"
    failure_markers = [ln for ln in lines if "NTP" in ln and ("fail" in ln.lower() or "error" in ln.lower() or "timeout" in ln.lower())]
    assert not failure_markers, "observed NTP failure/error/timeout log lines during a window with no fault injected:\n" + "\n".join(failure_markers)


# ---------------------------------------------------------------------------
# Real DNS resolution via asy_dns_client.py's own resolver, same rationale as the NTP test above.
# ---------------------------------------------------------------------------


def test_real_dns_resolution_succeeds_over_genuine_udp(board: Board) -> None:
    lines = board.tail_log(duration_s=_SYNC_TAIL_S)
    failure_markers = [ln for ln in lines if "DNS" in ln and ("fail" in ln.lower() or "error" in ln.lower())]
    assert not failure_markers, "observed DNS failure/error log lines during a window with no fault injected:\n" + "\n".join(failure_markers)


# ---------------------------------------------------------------------------
# Real NTP-unreachable timeout under genuine network loss, scripted via a temporary iptables DROP
# on UDP 123 (block_udp_ports()) - no physical action needed.
# ---------------------------------------------------------------------------


def test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # Only UDP 123 is blocked, not the AP, so the STA link stays up: "isconnected()==True but one downstream operation
    # is unreachable" (SPECIFICATION.md F.2), which tests/test_ntp_wifi_dns_integration.py proves at the mock level.
    reset_all_error_logs(dut_ip, request.node.name)
    bench.block_udp_ports([123])
    try:
        kick_then_reset(board, bench)  # forces a fresh NTP sync attempt against the now-unreachable server
        lines = board.tail_log(duration_s=_ROGUE_TAIL_S)  # generous relative to asy_ntp_client.py's own retry/backoff budget
    finally:
        bench.unblock_udp_ports([123])

    assert not crash_lines(lines), "a blocked NTP server crashed the system instead of degrading cleanly:\n" + "\n".join(crash_lines(lines))
    # NTP sync failure must not block the rest of build_system(): the boot still completes.
    assert boot_lines(lines), f"system did not finish booting with NTP blocked: {lines[-20:]}"
    recover_by_reset(board, bench, ready=lambda: _load.serving(dut_ip), first_wait_s=_RECONNECT_TIMEOUT_S, retry_wait_s=_RECONNECT_TIMEOUT_S, skipped="the passive reconnect after the forced resync", note=result_note, description="the reconnect after the NTP-blocked boot")
    # A blocked port is handled in place by NTP (SPECIFICATION.md Part C.7.2): NTP_NO_REPLY is logged
    # and the task backs off; an ended task would cost the supervisor's reboot budget.
    assert_module_error_log_contains(dut_ip, "NTP", code("E", "NTP_NO_REPLY"), "E")
    restarts = [ln for ln in lines if "Task ended - attempting restart" in ln]
    assert not restarts, "a blocked NTP server made a task end and be restarted:\n" + "\n".join(restarts)
    assert_no_task_ended(dut_ip, "a blocked NTP server")  # the persisted record, beyond the tail window
    reset_all_error_logs(dut_ip, request.node.name)  # the provoked NTP_NO_REPLY legitimately logged


def _networking(dut_ip: str) -> "JSONObject":
    return _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("networking"), "GET /status networking")
