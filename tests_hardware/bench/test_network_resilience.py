"""Bench-tier tests for real WiFi outage and flap (owner, 2026-09-01), NTP/DNS servers answering garbage
(SPECIFICATION.md F.1, UDP on rp2/lwIP), the admission ceiling on silicon, malformed requests and slowloris. DHCP is
not fault-injected: a documented known limitation (owner, 2026-09-26; tests_hardware/README.md)."""

import itertools
import json
import re
import socket
import struct
import threading
import time
from typing import TYPE_CHECKING

import _load
import http_client
import ntp_probe
import pytest
import serial
from error_log_helpers import (
    ErrcountEntry,
    assert_module_error_log_clean,
    assert_module_error_log_contains,
    assert_module_error_log_empty,
    assert_no_module_logged_a_new_error,
    assert_no_task_ended,
    code,
    errcount_entry,
    get_errcount,
    reset_all_error_logs,
)
from harness import (
    HELD_PAD_LINE,
    HELD_REQUEST_LINE,
    SRC_DIR,
    Board,
    HardwareTestFailureError,
    bench_device,
    boot_lines,
    configured_max_connections,
    crash_lines,
    device_toml,
    discover_max_connections,
    get_routes,
    hotspot_password,
    kick_then_reset,
    observe_during,
    recover_by_reset,
    schema_default,
    wait_until,
)
from rogue_udp_responder import RogueUdpResponder

from buildgen.definitions import definitions_for_toml

if TYPE_CHECKING:
    from bench_control import BenchBridge
    from http_client import JSONObject

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("webserver_concurrency", "sensortask_integration", "poll_prewarm", "ci_suite._run_8_wifi_persistence_and_configure_ntp", "ci_suite._run_11b_full_ceiling_concurrency")

# ---------------------------------------------------------------------------
# WiFi outage or flap inside an already-established STA connection. Per
# _on_sta_disconnected(), that case takes the safe "retry in 60s" branch and never increments
# _connection_failures or reaches hotspot fallback - read out of the source, not assumed.
# ---------------------------------------------------------------------------


# @tunable l4.network_resilience_outage_s = 15.0
_OUTAGE_S = 15.0
# @tunable l4.network_resilience_outage_reconnect_timeout_s = 150.0
_OUTAGE_RECONNECT_TIMEOUT_S = 150.0
# @tunable l4.network_resilience_reconnect_timeout_s = 60.0
_RECONNECT_TIMEOUT_S = 60.0
# @tunable l4.network_resilience_reconnect_poll_s = 3.0
_RECONNECT_POLL_S = 3.0
# @tunable l4.network_resilience_probe_timeout_s = 10.0
_PROBE_TIMEOUT_S = 10.0
# @tunable l4.network_resilience_flap_step_s = 3.0
_FLAP_STEP_S = 3.0
# @tunable l4.network_resilience_flap_cycles = 3
_FLAP_CYCLES = 3
# @tunable l4.network_resilience_degraded_reconnect_timeout_s = 90.0
_DEGRADED_RECONNECT_TIMEOUT_S = 90.0
# @tunable l4.network_resilience_wait_timeout_s = 30.0
_WAIT_TIMEOUT_S = 30.0
# @tunable l4.network_resilience_wait_poll_s = 2.0
_WAIT_POLL_S = 2.0
# @tunable l4.network_resilience_probe_spacing_s = 1.0
_PROBE_SPACING_S = 1.0
# @tunable l4.network_resilience_ntp_resync_timeout_s = 20.0
_NTP_RESYNC_TIMEOUT_S = 20.0
# @tunable l4.network_resilience_quick_poll_s = 1.0
_QUICK_POLL_S = 1.0
# @tunable l4.wifi_networking_ntp_fault_tail_s = 90.0
_ROGUE_TAIL_S = 90.0
# @tunable l4.bench_control_udp_capture_timeout_s = 55.0
_UDP_CAPTURE_TIMEOUT_S = 55.0
# @tunable l4.network_resilience_rtc_write_wait_s = 3.0
_RTC_WRITE_WAIT_S = 3.0
# @tunable l4.network_resilience_ntp_resync_after_reset_timeout_s = 120.0
_NTP_RESYNC_AFTER_RESET_TIMEOUT_S = 120.0
# @tunable l4.network_resilience_no_ap_tail_s = 15.0
_NO_AP_TAIL_S = 15.0
# @tunable l4.hotspot_role_reversal_join_hotspot_timeout_s = 45.0
_JOIN_HOTSPOT_TIMEOUT_S = 45.0
# @tunable l4.hotspot_role_reversal_dhcp_timeout_s = 45.0
_DHCP_TIMEOUT_S = 45.0
# @tunable l4.hotspot_role_reversal_dhcp_poll_s = 2.0
_DHCP_POLL_S = 2.0
# @tunable l4.network_resilience_slot_release_wait_s = 1.0
_SLOT_RELEASE_WAIT_S = 1.0
# @tunable l4.network_resilience_raw_socket_timeout_s = 10.0
_RAW_SOCKET_TIMEOUT_S = 10.0
# @tunable l4.network_resilience_held_admit_wait_s = 2.0
_HELD_ADMIT_WAIT_S = 2.0
# @tunable l4.network_resilience_admitted_silence_s = 1.0
_ADMITTED_SILENCE_S = 1.0
# @tunable l4.network_resilience_quick_recovery_timeout_s = 15.0
_QUICK_RECOVERY_TIMEOUT_S = 15.0
# @tunable l4.network_resilience_loaded_fetch_timeout_s = 30.0
_LOADED_FETCH_TIMEOUT_S = 30.0
# @tunable l4.network_resilience_storm_join_s = 60.0
_STORM_JOIN_S = 60.0
# @tunable l4.network_resilience_slowloris_socket_timeout_s = 30.0
_SLOWLORIS_SOCKET_TIMEOUT_S = 30.0
# @tunable l4.network_resilience_trickle_step_s = 3.0
_TRICKLE_STEP_S = 3.0
# @tunable l4.network_resilience_burst_join_s = 40.0
_BURST_JOIN_S = 40.0
# @tunable l4.network_resilience_served_elapsed_max_s = 30.0
_SERVED_ELAPSED_MAX_S = 30.0
# @tunable l4.network_resilience_degraded_get_count = 5
_DEGRADED_GET_COUNT = 5
# @tunable l4.network_resilience_join_attempts = 3
_JOIN_ATTEMPTS = 3
# @tunable l4.network_resilience_over_ceiling_attempts = 3
_OVER_CEILING_ATTEMPTS = 3
# @tunable l4.network_resilience_capture_attempts = 3
_CAPTURE_ATTEMPTS = 3
# @tunable l4.network_resilience_storm_repeat_min = 3
_STORM_REPEAT_MIN = 3
# @tunable l4.network_resilience_ntp_block_margin_s = 10.0
_NTP_BLOCK_MARGIN_S = 10.0
# @tunable l4.network_resilience_no_reconnect_tail_s = 5.0
_NO_RECONNECT_TAIL_S = 5.0
_NTP = "asy_ntp_client.py"
_WIFI = "asy_wifi_service.py"
_WEBSERVER = "asy_webserver_service.py"
# The two traced ways a connection ends at the ceiling: the refusal itself, and a client resetting one it gave up on.
_CEILING_TRACES = (code("W", "HTTP_REFUSED"), code("W", "HTTP_PEER_RESET"))


def test_real_wifi_outage_and_recovery_while_in_normal_sta_mode(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    bench.ap_down()
    try:
        # No assertion that the DUT notices within any particular window: the established-connection branch retries
        # every 60 s with no bound on the outage, so a brief outage is a realistic, low-risk window to inject.
        time.sleep(_OUTAGE_S)
    finally:
        bench.ap_up()
        bench.kick_all_stations()  # no stale AP-side station entry may outlive the outage
    _assert_recovered(board, bench, dut_ip, result_note, "a real WiFi outage", "bench.ap_up()")
    assert_no_task_ended(dut_ip, "real WiFi outage")  # on the reset path too: FRAM keeps SYSTEM


def test_real_wifi_flaps_repeatedly_without_wedging_the_system(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    try:
        for _cycle in range(_FLAP_CYCLES):
            bench.ap_down()
            time.sleep(_FLAP_STEP_S)  # short against the 60 s retry cadence: the DUT is still mid-wait, not yet retrying
            bench.ap_up()
            time.sleep(_FLAP_STEP_S)
    finally:
        bench.ap_up()  # a flap cut short by a failure must not leave the bench AP down
    bench.kick_all_stations()
    _assert_recovered(board, bench, dut_ip, result_note, "repeated real WiFi flapping", "the last bench.ap_up()")
    assert_no_task_ended(dut_ip, "repeated real WiFi flapping")


# ---------------------------------------------------------------------------
# Real loss, latency, corruption, duplication and reordering via inject_network_degradation(). A synced NTP client
# attempts nothing until NTPInterval hours have passed (src/asy_ntp_client.py _refresh_loop()), so no NTP exchange
# falls inside these windows: each test proves REST reachability under its impairment, and is named so.
# ---------------------------------------------------------------------------


def test_rest_stays_reachable_and_recovers_under_sustained_packet_loss_and_latency(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest) -> None:
    # Under 30% loss and 150 ms (+/-50 ms) latency any one request may fail; a bounded retry loop still gets through.
    reset_all_error_logs(dut_ip, request.node.name)
    _impaired(board, bench, dut_ip, _DEGRADED_RECONNECT_TIMEOUT_S, loss_pct=30, delay_ms=150, jitter_ms=50)
    assert_no_task_ended(dut_ip, "sustained packet loss and latency")
    reset_all_error_logs(dut_ip, request.node.name)  # no provoked fault stays in the live history


def test_rest_answers_first_try_under_light_realistic_wifi_congestion(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest) -> None:
    # The everyday end of the researched range (30 ms delay, 20 ms jitter, 2% loss): every request succeeds first try.
    reset_all_error_logs(dut_ip, request.node.name)

    def window() -> None:
        bench.inject_network_degradation(loss_pct=2, delay_ms=30, jitter_ms=20)
        try:
            for _ in range(_DEGRADED_GET_COUNT):
                res = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_PROBE_TIMEOUT_S)
                assert res.status_code == 200, f"a plain GET /status failed under light, realistic WiFi congestion: {res.status_code} {res.body[:200]!r}"
                time.sleep(_PROBE_SPACING_S)
        finally:
            bench.clear_network_degradation()

    _result, lines = observe_during(board, window)
    assert not crash_lines(lines), f"light congestion crashed the system: {crash_lines(lines)}"
    assert_no_task_ended(dut_ip, "light WiFi congestion")
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


def test_rest_stays_reachable_and_recovers_under_real_packet_corruption(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest) -> None:
    # corrupt flips a random bit inside a real packet (a radio-level bit error): UDP/TCP checksums drop it and TCP
    # retransmits, which is the property confirmed here rather than assumed.
    reset_all_error_logs(dut_ip, request.node.name)
    _impaired(board, bench, dut_ip, _RECONNECT_TIMEOUT_S, corrupt_pct=5)
    assert_no_task_ended(dut_ip, "real packet corruption")
    reset_all_error_logs(dut_ip, request.node.name)


def test_rest_stays_reachable_under_duplicated_and_reordered_packets(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest) -> None:
    # A duplicated or late reply matched to a later request would be a fault; reorder needs a delay to act on (tc-netem).
    reset_all_error_logs(dut_ip, request.node.name)
    _impaired(board, bench, dut_ip, _RECONNECT_TIMEOUT_S, delay_ms=20, duplicate_pct=10, reorder_pct=25)
    assert_no_task_ended(dut_ip, "duplicated and reordered packets")
    reset_all_error_logs(dut_ip, request.node.name)


def test_ntp_recovers_by_its_own_retry_timer_after_a_transient_outage(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # A synced client attempts nothing for hours and an unchanged NTPHost PUT fires no post function
    # (src/asy_api_response.py): the reset under the block makes the boot's sync fail, and the client's own retry timer,
    # never another reset, resyncs once the block - one retry period plus a margin - lifts.
    networking = _load.get_object(dut_ip, "/networking", _PROBE_TIMEOUT_S)
    res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"NTPHost": networking.get("NTPHost")}, timeout_s=_PROBE_TIMEOUT_S)
    word = _load.as_object(res.json().get("result"), "result").get("NTPHost")
    assert res.status_code == 200 and word == "Unchanged", f"an NTPHost PUT of its current value answered {word!r}: something was written"
    reset_all_error_logs(dut_ip, request.node.name)
    block_s = _ntp_retry_period_s() + _NTP_BLOCK_MARGIN_S
    bench.block_udp_ports([123])
    try:
        _load.reset_and_wait(board, bench, dut_ip, timeout_s=_RECONNECT_TIMEOUT_S)
        blocked_until = time.monotonic() + block_s
        # The no-reply entry, never NTPSynced false: every boot starts unsynced, so only the entry proves the block met
        # an attempt.
        wait_until(lambda: _load._ntp_error_log_contains(dut_ip, code("E", "NTP_NO_REPLY")), timeout_s=block_s, poll_interval_s=_QUICK_POLL_S, description="an NTP attempt meeting the block (NTP_NO_REPLY)")
        time.sleep(max(blocked_until - time.monotonic(), 0.0))
    finally:
        bench.unblock_udp_ports([123])
    started = time.monotonic()
    wait_until(lambda: _load.ntp_synced(dut_ip), timeout_s=_NTP_RESYNC_TIMEOUT_S + block_s, poll_interval_s=_QUICK_POLL_S, description="NTP resynced by its own retry timer after the block, with no further reset")
    result_note(f"NTP resynced {time.monotonic() - started:.1f}s after the block lifted")
    assert_no_task_ended(dut_ip, "transient NTP outage")
    reset_all_error_logs(dut_ip, request.node.name)  # the provoked failed attempt legitimately logged


# ---------------------------------------------------------------------------
# NTP/DNS servers answering garbage rather than being unreachable (SPECIFICATION.md F.1, UDP on rp2/lwIP); delivery
# and its limits: tests_hardware/README.md 'What the network-fault injections reach'.
# ---------------------------------------------------------------------------

# 48 bytes, the NTP packet the client receives into (src/asy_ntp_client.py _NTP_PACKET_LEN), and still no valid NTP
# header: its first byte's mode is 7 (private), never the server mode 4 the parser accepts.
_GARBAGE_PAYLOAD = b"\xff" + b"not an NTP or DNS wire-format packet, on purpose"[:47]


def test_ntp_server_sends_garbage_instead_of_a_valid_response(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    lines, answered = _garbage_window(board, bench, dut_ip, 123)
    assert answered.get(dut_ip, 0) >= 1, f"the injection never reached the DUT: the rogue NTP responder answered {answered!r}, never {dut_ip}"
    assert not crash_lines(lines), f"a garbage NTP response crashed the system instead of being rejected cleanly: {crash_lines(lines)}"
    assert boot_lines(lines), f"the board did not finish booting with a garbage-answering NTP server: {lines[-20:]}"
    _reconnected_after_forced_resync(board, bench, dut_ip, result_note)
    rejected = (code("E", "NTP_MALFORMED"), code("E", "NTP_IMPLAUSIBLE"))
    entry = errcount_entry(get_errcount(dut_ip), "NTP")
    assert any(h.get("type") == "E" and h.get("num") in rejected for h in entry["history"]) or "Invalid NTP time received!" in "\n".join(lines), f"no rejected NTP reply (NTP_MALFORMED/NTP_IMPLAUSIBLE) after {answered} garbage answers: {entry!r}"
    assert_no_task_ended(dut_ip, f"{_ROGUE_TAIL_S:g}s of garbage NTP replies")
    reset_all_error_logs(dut_ip, request.node.name)


def test_dns_server_sends_garbage_instead_of_a_valid_response(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    lines, answered = _garbage_window(board, bench, dut_ip, 53)
    # A garbage DNS reply and silence log the same NTP code, so the responder's own count is what proves delivery.
    assert answered.get(dut_ip, 0) >= 1, f"the injection never reached the DUT: the rogue DNS responder answered {answered!r}, never {dut_ip}"
    assert not crash_lines(lines), f"a garbage DNS response crashed the system instead of being rejected cleanly: {crash_lines(lines)}"
    assert boot_lines(lines), f"the board did not finish booting with a garbage-answering DNS server: {lines[-20:]}"
    _reconnected_after_forced_resync(board, bench, dut_ip, result_note)
    try:
        # resolve_ipv4() keeps no log of its own: a garbage reply fails its checks like silence, so NTP logs NTP_DNS.
        assert_module_error_log_contains(dut_ip, "NTP", code("E", "NTP_DNS"), "E")
        assert_no_task_ended(dut_ip, f"{_ROGUE_TAIL_S:g}s of garbage DNS replies")
    finally:
        reset_all_error_logs(dut_ip, request.node.name)


# ---------------------------------------------------------------------------
# Connected-socket source-address filtering (SPECIFICATION.md F.1, UDP on rp2/lwIP), which the garbage tests cannot
# reach: conntrack rewrites the reply's source. The real reply is held back, the DUT's port captured with tcpdump, and
# a reply answered from this host's own address (tests_hardware/README.md 'Known assumptions and open findings').
# ---------------------------------------------------------------------------

_NTP_SPOOF_INJECTED_UNIX_TIME = 2524608000  # 2050-01-01T00:00:00Z - inside _parse_ntp_reply()'s 2025-2100 plausibility window
_SPOOF_YEAR = time.gmtime(_NTP_SPOOF_INJECTED_UNIX_TIME).tm_year


def test_ntp_connected_socket_rejects_a_reply_from_an_unexpected_source(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # A connect()'d client socket takes datagrams from its true peer only: a spoof it took would set the RTC to its
    # Transmit Timestamp (2050-01-01), readable as GET /status's UTCTime.
    year_before = _utc_year(dut_ip)
    assert year_before is not None, "GET /status's UTCTime is null: the DUT has not synced NTP yet, so its clock is no signal for this test"
    assert year_before < _SPOOF_YEAR - 1, f"the DUT's own UTCTime year {year_before} leaves no room to tell the spoof's {_SPOOF_YEAR} apart"
    reset_all_error_logs(dut_ip, request.node.name)
    deadline_s = _fetch_timeout_s()
    bench.block_udp_ports_from([123])  # the real reply held back: the spoof is the only answer the waiting socket gets
    try:
        port, captured_at = _capture_dut_ntp_port(board, bench, dut_ip, result_note)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as spoof_sock:
            spoof_sock.sendto(ntp_probe.build_reply(_NTP_SPOOF_INJECTED_UNIX_TIME), (dut_ip, port))
        delay_s = time.monotonic() - captured_at
        result_note(f"spoof sent {delay_s:.2f}s after the captured request")
        assert delay_s < deadline_s, f"the spoof left {delay_s:.2f}s after the request, past the client's {deadline_s}s reply timeout - it landed on no waiting socket"
        time.sleep(_RTC_WRITE_WAIT_S)  # past _parse_ntp_reply()'s synchronous RTC write, were it ever reached
        wait_until(lambda: _load.serving(dut_ip), timeout_s=_RECONNECT_TIMEOUT_S, poll_interval_s=_RECONNECT_POLL_S, description="DUT reachable after the capture reset")
        year_after = _utc_year(dut_ip)  # None = not synced, still not the spoof's year
        assert year_after != _SPOOF_YEAR, f"the DUT's RTC took the spoofed reply's {_SPOOF_YEAR} - a connected socket accepted a reply from an unexpected source"
        assert_no_task_ended(dut_ip, "a spoofed NTP reply")
    finally:
        bench.unblock_udp_ports_from([123])
    recover_by_reset(board, bench, ready=lambda: _load.ntp_synced(dut_ip), first_wait_s=_NTP_RESYNC_AFTER_RESET_TIMEOUT_S, retry_wait_s=_NTP_RESYNC_AFTER_RESET_TIMEOUT_S, skipped="the normal sync after the held-back reply, without a reset", note=result_note, description="the normal NTP sync after the spoof test")
    reset_all_error_logs(dut_ip, request.node.name)


# ---------------------------------------------------------------------------
# A config-level NTP fault rather than a network-level one (owner, 2026-09-02): PUT a garbage NTPHost on a live link,
# watch the DNS failure degrade cleanly, restore, confirm recovery. Starting synced reaches
# _handle_ntp_sync_failure()'s ntp_issynced() branch, which nothing else does.
# ---------------------------------------------------------------------------

# RFC 2606 reserves .invalid so it can never resolve: a genuine, permanent DNS-resolution failure.
_GARBAGE_NTP_HOST = "this-host-will-never-resolve.invalid"


@pytest.mark.persistence_write
def test_garbage_ntp_host_via_rest_config_degrades_and_recovers_cleanly(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    original_host = _load.get_object(dut_ip, "/networking", _PROBE_TIMEOUT_S).get("NTPHost")
    if original_host == _GARBAGE_NTP_HOST:
        # An aborted earlier run left the garbage value: its PUT below would answer "Unchanged" and fire nothing.
        default = schema_default(_NTP, "NTPHost")
        assert isinstance(default, str), f"src/{_NTP} NTPHost defaults to {default!r}, no host name"
        original_host = default
        _load._repair_leftover(dut_ip, "/networking", {"NTPHost": original_host})
        _repair_target_note(result_note, "NTPHost")
    try:
        reset_all_error_logs(dut_ip, request.node.name)
        res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"NTPHost": _GARBAGE_NTP_HOST}, timeout_s=_PROBE_TIMEOUT_S)
        # _VAL_NTP_HOST bounds the length and the RFC 1035 label shape, so this host is "Valid"; the failure is the DNS
        # resolution its post function triggers.
        assert _load.as_object(res.json().get("result"), "result").get("NTPHost") == "Valid", f"garbage NTPHost was rejected at the schema level, not what this test exercises: {res.body!r}"
        # A resolver answers NXDOMAIN for .invalid (RFC 6761 section 6.4), which NTP persists as its own code.
        wait_until(lambda: _load._ntp_error_log_contains(dut_ip, code("E", "NTP_DNS_NXDOMAIN")), timeout_s=_WAIT_TIMEOUT_S, poll_interval_s=_WAIT_POLL_S, description="NTP to log NTP_DNS_NXDOMAIN for the garbage NTPHost")
        # Degrading cleanly means the rest stays healthy, not merely that the error got logged.
        assert _load.serving(dut_ip), "webserver unresponsive while NTPHost was garbage"
        assert_no_task_ended(dut_ip, "a garbage NTPHost")
    finally:
        reset_all_error_logs(dut_ip, request.node.name)
        restore = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"NTPHost": original_host}, timeout_s=_PROBE_TIMEOUT_S)
        # "Unchanged" counts as restored: a body that failed before its PUT landed leaves the original in place.
        assert _load.as_object(restore.json().get("result"), "result").get("NTPHost") in ("Valid", "Unchanged"), f"restoring the original NTPHost was rejected: {restore.body!r}"
    noted = _load.Noted(result_note)
    recover_by_reset(board, bench, ready=lambda: _load.ntp_synced(dut_ip), first_wait_s=_WAIT_TIMEOUT_S, retry_wait_s=_NTP_RESYNC_AFTER_RESET_TIMEOUT_S, skipped="NTP resync after the restore PUT without a reset", note=noted, description=f"the NTP resync after restoring {original_host!r}")
    if not noted.recovered:
        assert_module_error_log_empty(dut_ip, "NTP")


# ---------------------------------------------------------------------------
# A real-format SSID no AP here broadcasts; _VAL_SSID bounds only its length and bytes, the same gap as NTPHost. Once
# it is stored the DUT can never reconnect over the bridge, so the restore always goes over the DUT's own hotspot.
# ---------------------------------------------------------------------------

_GARBAGE_SSID = "bench-test-net-does-not-exist"


@pytest.mark.persistence_write
def test_garbage_ssid_via_rest_config_is_handled_gracefully(board: Board, bench: "BenchBridge", dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    ssid_bound = _load.field_schema(_WIFI, "SSID")[3]
    assert isinstance(ssid_bound, int) and len(_GARBAGE_SSID.encode()) <= ssid_bound, f"{_GARBAGE_SSID!r} exceeds _VAL_SSID's {ssid_bound}-byte bound: it would be refused, not stored"
    networking = _load.get_object(dut_ip, "/networking", _PROBE_TIMEOUT_S)
    original_ssid, hostname = networking.get("SSID"), str(networking.get("Hostname"))
    restore_target = original_ssid
    if original_ssid == _GARBAGE_SSID:
        restore_target = bench.ap_ssid()  # the SSID a bench DUT must hold
        _repair_target_note(result_note, "SSID")
    stored = False
    reset_all_error_logs(dut_ip, request.node.name)
    try:
        res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"SSID": _GARBAGE_SSID}, timeout_s=_PROBE_TIMEOUT_S)
        word = _load.as_object(res.json().get("result"), "result").get("SSID")
        stored = word in ("Valid", "Unchanged")
        assert word == "Valid" or original_ssid == _GARBAGE_SSID, f"garbage SSID was rejected at the schema level, not what this test exercises: {res.body!r}"
        # Passive observation only: one real STAT_NO_AP_FOUND cycle, logged and handled, inside the hotspot budget.
        lines = board.tail_log(duration_s=_NO_AP_TAIL_S)
        assert not crash_lines(lines), f"a real unreachable SSID crashed the system instead of degrading cleanly: {crash_lines(lines)}"
        assert any("WLAN access point not found" in line for line in lines), f"no real STAT_NO_AP_FOUND cycle observed for a nonexistent SSID: {lines[-20:]}"
    finally:
        if stored:
            _restore_over_hotspot(board, bench, hostname, str(restore_target), request.node.name, result_note)
    # The STA mode is GET /status's networking.Mode with the board reachable over the bridge, never a /networking field.
    recover_by_reset(board, bench, ready=lambda: _load.sta_mode(dut_ip), first_wait_s=_RECONNECT_TIMEOUT_S, retry_wait_s=_RECONNECT_TIMEOUT_S, skipped="the passive STA reconnect after the SSID restore", note=result_note, description=f"the STA reconnect after restoring {restore_target!r}")
    assert_no_task_ended(dut_ip, "the STA reconnect after a garbage SSID")  # the hotspot phase was checked before its restore
    reset_all_error_logs(dut_ip, request.node.name)  # the restore path can log one more STAT_NO_AP_FOUND mid-fallback


# ---------------------------------------------------------------------------
# The real connection ceiling (max_connections, three below lwIP's own MEMP_NUM_TCP_PCB) degrading
# cleanly at and above the limit, which test_end_to_end_timing.py's burst never holds enough slots
# to reach. _open_conns increments on accept, so a bare connect() already occupies a slot.
# ---------------------------------------------------------------------------

_MAX_CONNECTIONS = configured_max_connections()  # the build's own ceiling, never a restated literal


def test_connections_at_and_above_the_real_socket_limit_degrade_cleanly(dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    # The PUT /status just made closes client-side before _serve()'s finally releases its slot (Part I.6): settle first.
    time.sleep(_SLOT_RELEASE_WAIT_S)
    held: list[socket.socket] = []
    outcomes: list[bytes] = []
    try:
        # Each held socket sends a request line and is padded before every attempt: silent past the 5 s per-call
        # timeout, each would be answered and log HTTP_CALL_TIMEOUT.
        for _ in range(_MAX_CONNECTIONS):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(_RAW_SOCKET_TIMEOUT_S)
            sock.connect((dut_ip, 80))
            sock.sendall(HELD_REQUEST_LINE)
            held.append(sock)
        time.sleep(_HELD_ADMIT_WAIT_S)  # each held connection's _serve() has run and counted it before the first attempt
        for attempt in range(_OVER_CEILING_ATTEMPTS):
            outcomes.append(_extra_outcome(dut_ip, held))
            if attempt < _OVER_CEILING_ATTEMPTS - 1:
                time.sleep(_SLOT_RELEASE_WAIT_S)  # the refused connection's own cleanup completes before the next
    finally:
        for sock in held:
            sock.close()
    result_note(f"above-ceiling attempts: {[o[:40] for o in outcomes]}")
    admitted = [o for o in outcomes if o]
    assert not admitted, f"{len(admitted)} of {_OVER_CEILING_ATTEMPTS} connections above the real {_MAX_CONNECTIONS}-connection ceiling were admitted: {admitted}"
    # Closing the ceiling's sockets at once can reset a brand-new connection right after: retried until it serves.
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_QUICK_RECOVERY_TIMEOUT_S, poll_interval_s=_QUICK_POLL_S, description="webserver serving normally again after the connection-limit burst cleared")
    _assert_ceiling_traced(dut_ip, len(outcomes), "above the ceiling")
    assert_no_task_ended(dut_ip, "client misbehaviour")


# ---------------------------------------------------------------------------
# Nonsense GET/PUT requests over the normal network; test_hotspot_role_reversal.py's check is
# hotspot-only, GET-only and asserts no response shape. None of these mutate persisted config -
# a schema-rejected field is "Invalid" and never reaches write_config().
# ---------------------------------------------------------------------------


def test_get_nonsense_path_is_shaped_404_over_the_normal_network(dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    res = http_client.fetch(dut_ip, 80, "GET", "/this/path/does/not/exist", timeout_s=_PROBE_TIMEOUT_S)
    assert res.status_code == 404, f"GET to a nonsense path did not return 404: {res.status_code} {res.body!r}"
    body = res.json()
    assert body.get("res") == "ERR" and body.get("code") == 404, f"404 response was not shaped as expected: {body!r}"
    # _shaped_error_handler() only builds a response - no logger call: a routine 404 is no error or warning.
    assert_module_error_log_empty(dut_ip, "WEBSERVER")
    assert_no_task_ended(dut_ip, "client misbehaviour")


def test_put_malformed_raw_request_is_rejected_cleanly_over_the_normal_network(dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    # fetch() only ever sends well-formed JSON: malformed JSON syntax needs a raw socket.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(_RAW_SOCKET_TIMEOUT_S)
        sock.connect((dut_ip, 80))
        body = b"{not valid json"
        sock.sendall(f"PUT /sensors HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode() + body)
        response = _read_until_closed(sock)
    # microdot writes the status line as "HTTP/1.0 {code} {reason}"; malformed JSON is an application-level error
    # (make_response(1), _body_as_dict()'s contract), so the HTTP status is still 200 with an ERR envelope.
    assert response.startswith(b"HTTP/1.0 200"), f"malformed JSON PUT did not get a clean HTTP 200 app-level error envelope: {response!r}"
    assert b'"res":"ERR"' in response or b'"res": "ERR"' in response, f"malformed JSON PUT did not produce the expected ERR envelope: {response!r}"
    assert _load.serving(dut_ip), "webserver unresponsive after a malformed raw PUT request"
    assert_module_error_log_empty(dut_ip, "WEBSERVER")  # _put_sensors() answers make_response(1) with no logger call
    assert_no_task_ended(dut_ip, "client misbehaviour")


def test_put_oversized_body_is_rejected_with_413_over_the_normal_network(dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    # Well past the cap, on a field name no driver registers, so nothing here could validate as real config; over
    # max_body_length too, so the body is never read (SPECIFICATION.md I.6).
    oversized: JSONObject = {"BMP3XX": {"Nonsense" + "x" * (2 * _body_cap()): 1}}
    res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", oversized, timeout_s=_PROBE_TIMEOUT_S)
    assert res.status_code == 413, f"an oversized PUT body was not rejected with 413: {res.status_code} {res.body!r}"
    # Rejected inside vendored ext/microdot.py before this project's route handler or its logger is reached.
    assert_module_error_log_empty(dut_ip, "WEBSERVER")
    assert_no_task_ended(dut_ip, "client misbehaviour")


# ---------------------------------------------------------------------------
# The request-body cap over real WiFi. The unit tier's F.2b counts readexactly() sizes, which the wire
# cannot show, so these ask WHO answered: 413 is microdot's, before any handler; 200 only the handler's,
# so the body was buffered and dispatched. Why both caps moved together: SPECIFICATION.md Part I.6.
# ---------------------------------------------------------------------------

_OLD_CONTENT_CAP = 4096  # the cap before SPECIFICATION.md I.6; the 2048..4096 band is the discriminator


def test_put_body_cap_boundary_is_exact_over_the_normal_network(dut_ip: str, request: pytest.FixtureRequest) -> None:
    # One byte apart on real hardware; microdot's Request.create() compares with <=, so the cap itself is served.
    reset_all_error_logs(dut_ip, request.node.name)
    cap = _body_cap()
    assert _put_sized(dut_ip, cap) == 200, "a body of exactly max_content_length was rejected - the cap must be inclusive"
    assert _put_sized(dut_ip, cap - 1) == 200, "a body one byte under the cap was rejected"
    assert _put_sized(dut_ip, cap + 1) == 413, "a body one byte over the cap was not rejected with 413"
    assert_module_error_log_empty(dut_ip, "WEBSERVER")  # a 413 is microdot's, raised before our handler or logger
    assert_no_task_ended(dut_ip, "client misbehaviour")


def test_put_the_band_that_used_to_be_accepted_is_now_rejected_over_the_normal_network(dut_ip: str, request: pytest.FixtureRequest) -> None:
    # The check that tells this firmware from the previous one: before Part I.6 a 3000 B body was buffered and answered 200.
    reset_all_error_logs(dut_ip, request.node.name)
    midband = (_body_cap() + _OLD_CONTENT_CAP) // 2
    assert _put_sized(dut_ip, midband) == 413, f"a {midband} B body was not rejected - the old 4096 B content cap looks still in place"
    assert _put_sized(dut_ip, _OLD_CONTENT_CAP) == 413, "a body at the OLD content cap was accepted - this firmware predates Part I.6"
    assert_module_error_log_empty(dut_ip, "WEBSERVER")
    assert_no_task_ended(dut_ip, "client misbehaviour")


def test_the_largest_body_any_schema_can_produce_still_fits_under_the_cap(dut_ip: str, request: pytest.FixtureRequest) -> None:
    # Lowering a cap risks refusing something legitimate: the largest body the bench build's own schemas can produce
    # (derived from its definitions, as tests_scripts/test_request_body_cap_headroom.py derives it) is still served.
    reset_all_error_logs(dut_ip, request.node.name)
    largest = _load.largest_put_body()
    assert largest < _body_cap(), f"the schema maximum {largest} B no longer fits under the cap - Part I.6's premise has moved"
    assert _put_sized(dut_ip, largest) == 200, f"the largest schema-permitted body ({largest} B) was rejected"
    # And the largest string field any schema permits: one character over _VAL_NTP_HOST's bound (RFC 1035), so the
    # handler marks it Invalid and nothing is written - at the bound itself it would be a flash write this test must not own.
    host_max = _load.field_schema(_NTP, "NTPHost")[3]
    assert isinstance(host_max, int), f"_VAL_NTP_HOST declares no int length bound: {host_max!r}"
    res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"NTPHost": "z" * (host_max + 1)}, timeout_s=_PROBE_TIMEOUT_S)
    assert res.status_code == 200, f"a body carrying a maximal NTPHost was rejected at the TRANSPORT level, which is the cap's doing: {res.status_code} {res.body!r}"
    assert _load.as_object(res.json().get("result"), "result").get("NTPHost") == "Invalid", f"an over-bound NTPHost was not marked Invalid, so it may have PERSISTED: {res.body!r}"


# @tunable l4.cap_binding_answer_s = 2.0
_CAP_BINDING_ANSWER_S = 2.0
# @tunable l4.cap_binding_close_margin_s = 5.0
_CLOSE_MARGIN_S = 5.0
_MIN_SOCKET_WAIT_S = 0.001  # a zero timeout would make the socket non-blocking, never a last short wait


def test_an_oversized_body_is_refused_before_it_is_read(dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # The cap binds before the body: Content-Length one over the cap and no body byte is answered 413 at once, while at
    # the cap the server waits for a body that never comes and reclaims the connection at its per-call timeout.
    reset_all_error_logs(dut_ip, request.node.name)
    cap = _body_cap()
    per_call_s = _load.src_number(_WEBSERVER, "_DEFAULT_PER_CALL_TIMEOUT_S")
    assert per_call_s > _CAP_BINDING_ANSWER_S, f"the answer window {_CAP_BINDING_ANSWER_S}s must stay under the per-call timeout {per_call_s}s"
    free_before = _mem_free(dut_ip)
    answers: dict[int, bytes] = {}
    closed_after: float | None = None
    for length in (cap + 1, cap):
        with socket.create_connection((dut_ip, 80), timeout=_RAW_SOCKET_TIMEOUT_S) as sock:
            # A head declaring `length` body bytes, and not one of them sent.
            sock.sendall(f"PUT /sensors HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: {length}\r\n\r\n".encode())
            sent_at = time.monotonic()
            answers[length] = _answer_within(sock, _CAP_BINDING_ANSWER_S)
            if length == cap:
                closed_after = _closed_after(sock, sent_at, per_call_s + _CLOSE_MARGIN_S)
    assert answers[cap + 1].startswith(b"HTTP/1.0 413"), f"Content-Length {cap + 1} with no body was not answered 413 within {_CAP_BINDING_ANSWER_S}s: {answers[cap + 1]!r}"
    assert answers[cap] == b"<silent>", f"Content-Length {cap} was answered before its body arrived: {answers[cap]!r}"
    assert closed_after is not None, f"the server held a body-less request at the cap past {per_call_s + _CLOSE_MARGIN_S}s"
    free_after = _mem_free(dut_ip)
    result_note(f"MemFree {free_before} -> {free_after} B; the at-cap connection closed after {closed_after:.1f}s")
    assert abs(free_before - free_after) < cap, f"MemFree moved by {free_before - free_after} B across a refused body, as much as the cap {cap} B"
    assert_module_error_log_clean(dut_ip, "WEBSERVER", allowed_warnings=(code("W", "HTTP_CALL_TIMEOUT"), code("W", "HTTP_BAD_HEAD")))
    assert_no_task_ended(dut_ip, "client misbehaviour")


def test_put_a_mixed_stream_of_body_sizes_is_handled_each_on_its_own_merits(dut_ip: str, request: pytest.FixtureRequest) -> None:
    # Interleaved, so a rejection cannot leave the next acceptance mis-parsed, nor an acceptance let an oversized one by.
    reset_all_error_logs(dut_ip, request.node.name)
    cap = _body_cap()
    for size in [128, cap * 2, 700, cap + 1, cap, 64, _OLD_CONTENT_CAP]:
        expected = 200 if size <= cap else 413
        status = _put_sized(dut_ip, size)
        assert status == expected, f"a {size} B body answered {status}, expected {expected}"
    assert _load.serving(dut_ip), "webserver unresponsive after a mixed-size PUT stream"
    assert_module_error_log_empty(dut_ip, "WEBSERVER")
    assert_no_task_ended(dut_ip, "client misbehaviour")


def test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status(dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # max_connections bodies can be in flight at once, so the simultaneous contiguous demand is that many buffers - the
    # multi-buffer shape that motivated Part I.6, asserted on what the body cap owns.
    reset_all_error_logs(dut_ip, request.node.name)
    time.sleep(_SLOT_RELEASE_WAIT_S)  # the PUT just made can still hold a slot: _serve() releases it after the close
    cap = _body_cap()
    # Repeated well past the build's ceiling however high it is raised, so the storm overloads admission.
    sizes = [512, cap * 2, cap, _OLD_CONTENT_CAP, 64, cap + 1, 900, cap * 2] * max(_STORM_REPEAT_MIN, _MAX_CONNECTIONS)
    outcomes: dict[str, dict[int, int | str]] = {"answered": {}, "refused": {}, "other": {}}
    lock = threading.Lock()
    threads: list[threading.Thread] = []
    try:
        for i, size in enumerate(sizes):
            thread = threading.Thread(target=_sized_worker, args=(dut_ip, i, size, outcomes, lock), name=f"put-{i}")
            threads.append(thread)
            thread.start()
    finally:
        alive = _load.join(threads, _STORM_JOIN_S)
    assert not alive, f"{len(alive)} worker(s) never finished within {_STORM_JOIN_S:g}s - possible real deadlock under concurrent mixed-body load"
    answered, refused, other = outcomes["answered"], outcomes["refused"], outcomes["other"]
    # Most are refused at the ceiling, its reject-when-full (measured ~25% on 2026-09-22, at every size including 64 B): a refusal
    # is counted, not failed - but ONLY a refusal.
    assert not other, f"{len(other)} worker(s) failed for a reason that is not the connection ceiling: {dict(list(other.items())[:8])}"
    wrong = {i: status for i, status in answered.items() if status != (200 if sizes[i] <= cap else 413)}
    assert not wrong, f"{len(wrong)} of {len(answered)} answered PUTs got the WRONG status under concurrency: {dict(list(wrong.items())[:8])}"
    statuses = list(answered.values())
    # Anti-vacuity from the server's documented capacity: too few answers prove nothing, and both verdicts must appear.
    assert len(statuses) >= _MAX_CONNECTIONS, f"only {len(statuses)} of {len(sizes)} PUTs were answered at all - too few to say anything about the cap ({len(refused)} refused)"
    assert 200 in statuses and 413 in statuses, f"the run never saw both verdicts, so the cap was never exercised under concurrency: {sorted(set(map(str, statuses)))}"
    wait_until(lambda: _load.serving(dut_ip), timeout_s=_QUICK_RECOVERY_TIMEOUT_S, poll_interval_s=_QUICK_POLL_S, description="webserver serving normally again after the concurrent mixed-body load cleared")
    _assert_ceiling_traced(dut_ip, len(refused), "the concurrent mixed-body storm")
    assert_no_task_ended(dut_ip, "client misbehaviour")
    result_note(f"{len(answered)} answered, {len(refused)} refused at the connection ceiling, 0 answered wrongly")


def test_put_nonsense_field_values_are_marked_invalid_not_crashed(board: Board, dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    # Wrong type, out of range and an unknown sensor key in one REST call: _VAL_PRES_OVERS accepts only _OSR_SETTINGS.
    res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", {"BMP3XX": {"PresOvers": "banana", "FiltCoeff": 999}, "TotallyUnknownSensor": {"Whatever": 1}}, timeout_s=_PROBE_TIMEOUT_S)
    assert res.status_code == 200, f"a syntactically valid but nonsensical PUT body crashed the request instead of being marked Invalid: {res.status_code} {res.body!r}"
    body = res.json()
    result = _load.as_object(body.get("result"), "result")
    bmp_result = _load.as_object(result.get("BMP3XX"), "result.BMP3XX")
    assert bmp_result.get("PresOvers") == "Invalid", f"a wrong-typed field was not marked Invalid: {bmp_result!r}"
    assert bmp_result.get("FiltCoeff") == "Invalid", f"an out-of-range field was not marked Invalid: {bmp_result!r}"
    assert isinstance(body["result"], dict) and "TotallyUnknownSensor" not in body["result"], f"an entirely unknown sensor key was not silently ignored: {result!r}"
    assert _load.serving(dut_ip), "webserver unresponsive after nonsense PUT field values"
    try:
        # A rejected key logs BAD_ARG on its own CFGMGR_<NAME> logger, not the sensor's (write_config()).
        entry = errcount_entry(get_errcount(dut_ip), "CFGMGR_BMP3XX")
        assert entry["counter"] == 2, f"expected exactly 2 type/range validation errors on CFGMGR_BMP3XX (one per rejected field), got: {entry!r}"
        assert_module_error_log_contains(dut_ip, "CFGMGR_BMP3XX", code("E", "BAD_ARG"), "E")
        assert_no_task_ended(dut_ip, "nonsense sensor values")
        # A radio value within the schema's character count but past its byte bound (C.7.4): two UTF-8 bytes per "ä".
        host_bound, ssid_bound = _load.field_schema(_WIFI, "Hostname")[3], _load.field_schema(_WIFI, "SSID")[3]
        assert isinstance(host_bound, int) and isinstance(ssid_bound, int), f"_VAL_HOSTNAME/_VAL_SSID declare no int length bound: {host_bound!r}, {ssid_bound!r}"
        reset_all_error_logs(dut_ip, request.node.name)
        mode = _load.mode(dut_ip)
        res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"Hostname": "ä" * host_bound}, timeout_s=_PROBE_TIMEOUT_S)
        assert _load.as_object(res.json().get("result"), "result").get("Hostname") == "Invalid", f"a {2 * host_bound}-byte Hostname was not refused: {res.body!r}"
        _assert_radio_refusal_traced(board, dut_ip, "Hostname", mode)
        reset_all_error_logs(dut_ip, request.node.name)
        res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"SSID": "ä" * ssid_bound}, timeout_s=_PROBE_TIMEOUT_S)
        assert _load.as_object(res.json().get("result"), "result").get("SSID") == "Invalid", f"a {2 * ssid_bound}-byte SSID was not refused: {res.body!r}"
        _assert_radio_refusal_traced(board, dut_ip, "SSID", mode)
        assert_no_task_ended(dut_ip, "nonsense field values")
    finally:
        reset_all_error_logs(dut_ip, request.node.name)


# ---------------------------------------------------------------------------
# Stale/slowloris-paced/abruptly-broken connections. _serve()'s outer asyncio.wait_for(...,
# outer_cap_s=15.0) is what bounds a Slowloris-paced client that never completes its request.
# ---------------------------------------------------------------------------


def test_slowloris_style_partial_request_is_reclaimed_by_the_outer_timeout(dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(_SLOWLORIS_SOCKET_TIMEOUT_S)  # over the server's outer_cap_s
        sock.connect((dut_ip, 80))
        sock.sendall(b"GET /status HTTP/1.1\r\nHost: x\r\n")
        # One header line every 3 s keeps each readline() under its per-call timeout (HTTP_CALL_TIMEOUT never fires)
        # while the 18 s total passes outer_cap_s, the timeout under test.
        try:
            for i in range(6):
                sock.sendall(f"X-Pad-{i}: 1\r\n".encode())
                time.sleep(_TRICKLE_STEP_S)
        except OSError:
            pass  # the server may have closed the connection once the outer cap fired
        try:
            response = sock.recv(4096)
        except OSError:
            response = b""
    assert response == b"", f"a genuinely Slowloris-paced request (no single stall over 5s, 18s cumulative) was not reclaimed by the outer timeout: {response!r}"
    assert _load.serving(dut_ip), "webserver unresponsive after a slowloris-style trickle-fed request"
    try:
        assert_module_error_log_contains(dut_ip, "WEBSERVER", code("W", "HTTP_REQUEST_CAP"), "W")
        assert_no_task_ended(dut_ip, "a slowloris-paced request")
    finally:
        reset_all_error_logs(dut_ip, request.node.name)


def test_abrupt_disconnect_mid_response_does_not_hang_the_server(dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(_RAW_SOCKET_TIMEOUT_S)
        sock.connect((dut_ip, 80))
        sock.sendall(b"GET /measurements HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        sock.recv(1)  # one byte of the response, then the client vanishes (a plain close, no clean shutdown)
    # A leaked fd or task would degrade over many such events; the next client must be served now.
    assert _load.serving(dut_ip), "webserver unresponsive after a client disconnected abruptly mid-response"
    # Whether the server is still mid-write when the close lands (HTTP_SOCKET_ERROR) is a real race, so WEBSERVER is
    # not judged here; no task ending holds either way.
    assert_no_task_ended(dut_ip, "an abrupt mid-response disconnect")
    reset_all_error_logs(dut_ip, request.node.name)


# ---------------------------------------------------------------------------
# The connection ceiling the BOARD actually holds, versus the one this tree configures. The only
# check in the repo that can confirm a raised lwIP MEMP_NUM_TCP_PCB really took effect on silicon -
# nothing in the twin can, it has no lwIP at all (SPECIFICATION.md Part B.14.2).
# ---------------------------------------------------------------------------


def test_the_board_holds_exactly_the_connection_ceiling_this_tree_configures(dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    discovered = discover_max_connections(dut_ip)
    configured = configured_max_connections()
    # Equal, not merely at least: fewer means lwIP ran out of PCBs below the application ceiling (the wall,
    # SPECIFICATION.md H.7); more means the image on the board is not the one this tree describes.
    assert discovered == configured, f"the board admitted {discovered} simultaneous connections, this tree configures {configured} (fewer: lwIP's MEMP_NUM_TCP_PCB exhausted below the ceiling; more: an older image)"
    _assert_ceiling_traced(dut_ip, 1, "the ceiling walk")  # the walk ends on its one refusal
    assert_no_task_ended(dut_ip, "client misbehaviour")


# ---------------------------------------------------------------------------
# Admission is not service. A ceiling the stack accepts but cannot push produces 200s with truncated
# bodies, or responses that arrive minutes late - both of which a status-code check passes. These
# two are the silicon half of the twin's own scenarios of the same name.
# ---------------------------------------------------------------------------


def test_a_full_ceiling_of_concurrent_requests_is_each_served_a_complete_body(dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    ceiling = configured_max_connections()
    # Every registered JSON GET route; the streamed ones (get_routes(streams=True)) are the ones a stack out of buffers
    # truncates, and urllib refuses a body short of its Content-Length.
    paths = get_routes()
    references = {path: _keys(dut_ip, path, _LOADED_FETCH_TIMEOUT_S) for path in paths}
    before = get_errcount(dut_ip)
    results = ["unset"] * ceiling
    time.sleep(_SLOT_RELEASE_WAIT_S)  # a slot is released after _serve() awaits the close, so it outlives the response (Part I.6)
    threads: list[threading.Thread] = []
    try:
        for i in range(ceiling):
            path = paths[i % len(paths)]
            thread = threading.Thread(target=_ceiling_client, args=(dut_ip, path, references[path], results, i), name=f"ceiling-{i}")
            threads.append(thread)
            thread.start()
    finally:
        alive = _load.join(threads, _BURST_JOIN_S)
    assert not alive, f"{alive} never finished within {_BURST_JOIN_S:g}s"
    # Every one, not "at least the ceiling": this burst IS the ceiling, so a refusal means the board cannot serve what it admits.
    failed = [r for r in results if r != "ok"]
    assert not failed, f"{len(failed)} of a {ceiling}-wide burst at the configured ceiling were refused, truncated, changed shape or late (streamed: {get_routes(streams=True)}): {failed}"
    time.sleep(_SLOT_RELEASE_WAIT_S)  # the burst's slots outlive their responses (Part I.6)
    assert_module_error_log_empty(dut_ip, "WEBSERVER")
    assert_no_task_ended(dut_ip, "client misbehaviour")
    # Every sensor task always runs on silicon, so a full-ceiling burst starves the heap for the whole graph.
    assert_no_module_logged_a_new_error(dut_ip, before, f"a {ceiling}-wide burst at the configured ceiling")


def test_a_concurrent_page_load_is_byte_identical_to_an_uncontended_one(dut_ip: str, request: pytest.FixtureRequest) -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    # ext/microdot.py streams a file in send_file_buffer_size chunks, so a stack out of buffers truncates rather than failing.
    reference = http_client.fetch(dut_ip, 80, "GET", "/", timeout_s=_LOADED_FETCH_TIMEOUT_S)
    assert reference.status_code == 200 and reference.body, f"the index page is unavailable uncontended - nothing to compare against: {reference.status_code}"
    time.sleep(_SLOT_RELEASE_WAIT_S)  # its own slot outlives the response it already returned (Part I.6)
    tabs = max(2, configured_max_connections() // 2)  # 2 connections per real page load, post-inlining
    sizes: list[int | str] = [0] * (tabs * 2)
    threads: list[threading.Thread] = []
    try:
        for i in range(tabs * 2):
            thread = threading.Thread(target=_index_load, args=(dut_ip, reference.body, sizes, i), name=f"index-{i}")
            threads.append(thread)
            thread.start()
    finally:
        alive = _load.join(threads, _BURST_JOIN_S)
    assert not alive, f"{alive} never finished within {_BURST_JOIN_S:g}s"
    assert set(sizes) == {len(reference.body)}, f"a concurrent page load was truncated or refused - uncontended the index is {len(reference.body)} bytes, under {tabs * 2} concurrent loads it was {sizes}"
    time.sleep(_SLOT_RELEASE_WAIT_S)  # the burst filled the ceiling and its slots outlive their responses (Part I.6)
    assert_module_error_log_empty(dut_ip, "WEBSERVER")
    assert_no_task_ended(dut_ip, "client misbehaviour")


# ---------------------------------------------------------------------------
# The owner's OpenHAB case (owner, 2026-08-25): two polled endpoints plus a website open for manual calibration, all
# served for two minutes - a named instance of the contract that any client mix filling the ceiling is served.
# ---------------------------------------------------------------------------

# @tunable l4.openhab_poll_interval_s = 5.0
_OPENHAB_POLL_INTERVAL_S = 5.0
# @tunable l4.openhab_window_s = 120.0
_OPENHAB_WINDOW_S = 120.0
_ASSET = re.compile(r'(?:src|href)="([^"#:?]+)"')


def test_openhab_case_two_pollers_and_an_open_website_are_all_served(dut_ip: str, board: Board, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    reset_all_error_logs(dut_ip, request.node.name)
    boot_before = _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("system"), "GET /status system").get("BootSignature")
    index = http_client.fetch(dut_ip, 80, "GET", "/", timeout_s=_PROBE_TIMEOUT_S)
    assert index.status_code == 200, f"the index page is unavailable: {index.status_code}"
    assets = ["/", *sorted({"/" + a.lstrip("./") for a in _ASSET.findall(index.body.decode("utf-8", "replace"))})]
    poll_route, poll_s = _website_routes(bench_device())
    latencies: dict[str, list[float]] = {}
    failures: list[str] = []
    stop = threading.Event()
    clients = [(["/measurements"], _OPENHAB_POLL_INTERVAL_S), (["/status"], _OPENHAB_POLL_INTERVAL_S), (assets, _OPENHAB_WINDOW_S), ([poll_route], poll_s)]

    def window() -> None:
        threads: list[threading.Thread] = []
        try:
            for n, (paths, interval_s) in enumerate(clients):
                thread = threading.Thread(target=_openhab_client, args=(dut_ip, paths, interval_s, stop, latencies, failures), name=f"openhab-{n}")
                threads.append(thread)
                thread.start()
            stop.wait(_OPENHAB_WINDOW_S)
        finally:
            stop.set()
            alive = _load.join(threads, _BURST_JOIN_S)
        assert not alive, f"{alive} never finished after the OpenHAB window"

    _result, lines = observe_during(board, window)
    assert not failures, f"{len(failures)} OpenHAB-case request(s) were refused or incomplete: {failures[:10]}"
    assert not crash_lines(lines), f"a crash over the OpenHAB window: {crash_lines(lines)}"
    assert _load.serving(dut_ip), "/status not serving at once after the OpenHAB window"
    boot_after = _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("system"), "GET /status system").get("BootSignature")
    assert boot_after == boot_before, f"the board rebooted during the OpenHAB case: {boot_before!r} -> {boot_after!r}"
    assert_no_task_ended(dut_ip, "the OpenHAB case")
    result_note("OpenHAB latency per route (s, max/median): " + ", ".join(f"{p} {max(v):.2f}/{sorted(v)[len(v) // 2]:.2f}" for p, v in sorted(latencies.items())))


# ---------------------------------------------------------------------------
# Console output with a host that holds the USB port open and never reads (owner, 2026-10-02: behind the persistence
# flag): the adversarial-client load of the L1 console test replayed over HTTP must never starve the watchdog.
# ---------------------------------------------------------------------------

# @tunable l4.console_starvation_load_s = 60.0
_CONSOLE_LOAD_S = 60.0
# @tunable l4.console_starvation_slowloris_clients = 6
_CONSOLE_SLOWLORIS = 6
_LINGER_RESET = struct.pack("ii", 1, 0)  # SO_LINGER on with a zero timeout: the close sends an RST (socket(7))


@pytest.mark.persistence_write
def test_console_output_with_a_non_reading_usb_host_never_starves_the_watchdog(board: Board, dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    def adversary(kind: str, stop: threading.Event, seen: "list[str]") -> None:
        # One misbehaving client kind, repeated until stopped: slowloris, a refused head, a truncated body, a reset.
        while not stop.is_set():
            try:
                with socket.create_connection((dut_ip, 80), timeout=_RAW_SOCKET_TIMEOUT_S) as sock:
                    if kind == "slowloris":
                        sock.sendall(b"GET /status HTTP/1.1\r\n")
                        while not stop.wait(_TRICKLE_STEP_S):
                            sock.sendall(b"X-Pad: 1\r\n")
                    elif kind == "bad-head":
                        sock.sendall(b"\x00\x01 not a request line\r\n\r\n")
                    elif kind == "truncated":  # 64 body bytes declared, fewer sent: no handler ever runs
                        sock.sendall(b'PUT /sensors HTTP/1.1\r\nContent-Length: 64\r\n\r\n{"HWTESTNoSuch')
                    else:
                        sock.sendall(b"GET /measurements HTTP/1.1\r\n\r\n")
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, _LINGER_RESET)
                    seen.append(kind)
            except OSError as exc:  # a refusal at the ceiling is part of the load
                seen.append(f"{kind}: {type(exc).__name__}")
            stop.wait(_PROBE_SPACING_S)

    system_before = _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("system"), "GET /status system")
    res = http_client.fetch(dut_ip, 80, "PUT", "/system", {"DebugLevel": 0}, timeout_s=_PROBE_TIMEOUT_S)
    assert _load.as_object(res.json().get("result"), "result").get("DebugLevel") == "Valid", f"DebugLevel 0 was refused: {res.body!r}"
    seen: list[str] = []
    stop = threading.Event()
    threads: list[threading.Thread] = []
    port = serial.Serial(board.device, dsrdtr=False)  # held open, DTR asserted, never read: the console's output backs up
    try:
        port.dtr = True
        kinds = ["slowloris"] * _CONSOLE_SLOWLORIS + ["bad-head", "truncated", "reset", "reset"]
        for n, kind in enumerate(kinds):
            thread = threading.Thread(target=adversary, args=(kind, stop, seen), name=f"adversary-{n}")
            threads.append(thread)
            thread.start()
        stop.wait(_CONSOLE_LOAD_S)
    finally:
        stop.set()
        alive = _load.join(threads, _SLOWLORIS_SOCKET_TIMEOUT_S)
        port.close()
        restore = http_client.fetch(dut_ip, 80, "PUT", "/system", {"DebugLevel": 5}, timeout_s=_PROBE_TIMEOUT_S)
        assert _load.as_object(restore.json().get("result"), "result").get("DebugLevel") == "Valid", f"restoring DebugLevel 5 was refused: {restore.body!r}"
    assert not alive, f"{alive} adversary client(s) never finished"
    system_after = _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("system"), "GET /status system")
    result_note(f"{len(seen)} adversarial connections over {_CONSOLE_LOAD_S:g}s; SysUptime {system_before.get('SysUptime')} -> {system_after.get('SysUptime')}")
    assert system_after.get("BootSignature") == system_before.get("BootSignature") and system_after.get("ResetReason") == system_before.get("ResetReason"), f"the board reset under a non-reading console host: {system_before!r} -> {system_after!r}"


# ---------------------------------------------------------------------------
# A flash write holds interrupts off (an erase of a 4 KB sector, up to 400 ms): the CYW43 link must survive two of them
# under a fast /status poll, and what the closed firmware drops meanwhile is recorded.
# ---------------------------------------------------------------------------

# @tunable l4.flash_stall_poll_s = 0.05
_FLASH_STALL_POLL_S = 0.05
# @tunable l4.flash_stall_window_s = 5.0
_FLASH_STALL_WINDOW_S = 5.0


@pytest.mark.persistence_write
def test_a_flash_write_holding_interrupts_off_keeps_the_wifi_link(dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    current = _load.get_object(dut_ip, "/notification", _PROBE_TIMEOUT_S).get("WarnCO2")
    assert isinstance(current, int), f"GET /notification carries no int WarnCO2: {current!r}"
    wifi_before: ErrcountEntry = errcount_entry(get_errcount(dut_ip), "WIFI")
    polls: list[tuple[float, JSONObject | None]] = []
    stop = threading.Event()
    poller = threading.Thread(target=_link_poller, args=(dut_ip, stop, polls), name="link-poller")
    try:
        poller.start()
        res = http_client.fetch(dut_ip, 80, "PUT", "/notification", {"WarnCO2": current + 1}, timeout_s=_PROBE_TIMEOUT_S)
        assert _load.as_object(res.json().get("result"), "result").get("WarnCO2") == "Valid", f"WarnCO2 {current + 1} was refused: {res.body!r}"
        stop.wait(_FLASH_STALL_WINDOW_S)  # the deferred flush runs inside this window
    finally:
        restore = http_client.fetch(dut_ip, 80, "PUT", "/notification", {"WarnCO2": current}, timeout_s=_PROBE_TIMEOUT_S)
        stop.wait(_FLASH_STALL_WINDOW_S)
        stop.set()
        alive = _load.join([poller], _WAIT_TIMEOUT_S)
        assert _load.as_object(restore.json().get("result"), "result").get("WarnCO2") == "Valid", f"restoring WarnCO2 {current} was refused: {restore.body!r}"
    assert not alive, "the link poller never finished"
    answered = [(t, n) for t, n in polls if n is not None]
    lost = len(polls) - len(answered)
    gaps = [b[0] - a[0] for a, b in itertools.pairwise(answered)]
    result_note(f"{len(answered)} answered polls, {lost} lost, longest gap {max(gaps, default=0.0):.2f}s across the two flash writes")
    assert answered, "no /status poll was answered across the two flash writes"
    assert all(n.get("Connected") is True for _t, n in answered), f"the link reported disconnected during a flash write: {[n for _t, n in answered if n.get('Connected') is not True][:3]}"
    uptimes = [n.get("WifiUptime") for _t, n in answered]
    counted = [u for u in uptimes if isinstance(u, int)]
    assert counted == uptimes and counted == sorted(counted), f"WifiUptime reset (or went missing) during a flash write: {uptimes}"
    wifi_after = errcount_entry(get_errcount(dut_ip), "WIFI")
    assert wifi_after["counter"] == wifi_before["counter"], f"WIFI logged during the flash writes: {wifi_before!r} -> {wifi_after!r}"


def _answer_within(sock: socket.socket, wait_s: float) -> bytes:
    # What the server sends within `wait_s`: its bytes, b"<closed>" for a close, b"<silent>" for nothing.
    sock.settimeout(wait_s)
    try:
        return sock.recv(4096) or b"<closed>"
    except TimeoutError:
        return b"<silent>"


def _assert_ceiling_traced(dut_ip: str, refusals: int, context: str) -> None:
    # Reject-when-full closes without a response and traces one HTTP_REFUSED entry per refusal (SPECIFICATION.md H.7):
    # exactly those two codes in WEBSERVER, and HTTPDropped holding at least the refusals the clients saw.
    assert_module_error_log_clean(dut_ip, "WEBSERVER", allowed_warnings=_CEILING_TRACES)
    dropped = _http_dropped(dut_ip)
    assert dropped >= refusals, f"{context}: HTTPDropped is {dropped}, fewer than the {refusals} refusal(s) the clients saw"


def _assert_radio_refusal_traced(board: Board, dut_ip: str, field: str, mode_before: object) -> None:
    # The refusal's WIFI entry, no reconnect (no connect line over a short tail, Mode unchanged) and the board serving.
    assert_module_error_log_contains(dut_ip, "WIFI", code("E", "BAD_ARG"), "E")
    lines = board.tail_log(duration_s=_NO_RECONNECT_TAIL_S)
    assert not [line for line in lines if "WLAN connection" in line], f"a refused {field} still triggered a reconnect: {lines}"
    assert _load.mode(dut_ip) == mode_before, f"Mode moved from {mode_before!r} after a refused {field}"


def _assert_recovered(board: Board, bench: "BenchBridge", dut_ip: str, result_note: "_load.Note", description: str, since: str) -> None:
    # The CYW43 firmware can report associated while the link is dead, and neither the kick nor the retry clears it
    # (tests_hardware/README.md): one reported reset is the recovery, and the benign-warning check runs only without it.
    noted = _load.Noted(result_note)
    started = time.monotonic()
    recover_by_reset(board, bench, ready=lambda: _load.serving(dut_ip), first_wait_s=_OUTAGE_RECONNECT_TIMEOUT_S, retry_wait_s=_RECONNECT_TIMEOUT_S, skipped="_assert_wifi_log_has_only_benign_outage_warnings", note=noted, description=description)
    if not noted.recovered:
        result_note(f"recovered gracefully in {time.monotonic() - started:.1f}s ({since} to the first reachable /status)")
        _assert_wifi_log_has_only_benign_outage_warnings(dut_ip)


def _assert_wifi_log_has_only_benign_outage_warnings(dut_ip: str) -> None:
    # An outage logs AP-not-found from a retry poll mid-outage and the handshake failure cyw43 reports when the AP drops
    # mid-handshake (SPECIFICATION.md C.7.1, the WIFI row); the password never changes here.
    entry = errcount_entry(get_errcount(dut_ip), "WIFI")
    benign = (code("W", "WLAN_NO_AP"), code("W", "WLAN_AUTH_FAILED"))
    unexpected = [h for h in entry["history"] if h.get("type") != "N" and not (h.get("type") == "W" and h.get("num") in benign)]
    assert not unexpected, f"WIFI logged beyond the outage's benign WLAN_NO_AP/WLAN_AUTH_FAILED {benign}: {unexpected!r} (full: {entry!r})"


def _body_cap() -> int:
    # ServingLimits' shipped max_content_length, now bound to max_body_length too.
    return int(_load.src_number(_WEBSERVER, "_DEFAULT_MAX_CONTENT_LENGTH"))


def _capture_dut_ntp_port(board: Board, bench: "BenchBridge", dut_ip: str, result_note: "_load.Note") -> "tuple[int, float]":
    # The DUT's ephemeral NTP source port and when it was captured, each reset forcing a fresh request; a capture that saw
    # nothing (the reset landed in hotspot fallback, BACKLOG.md open question 9) is retried, each retry reported.
    for attempt in range(1, _CAPTURE_ATTEMPTS + 1):
        capture = bench.start_udp_source_capture(dut_ip, 123)
        kick_then_reset(board, bench)
        port = bench.read_captured_udp_source_port(capture, timeout_s=_UDP_CAPTURE_TIMEOUT_S)
        if port is not None:
            return port, time.monotonic()
        if attempt < _CAPTURE_ATTEMPTS:
            result_note(f"capture attempt {attempt} saw no NTP request; retried with a fresh reset", recovery=True)
    raise AssertionError(f"never observed a real NTP request from the DUT across {_CAPTURE_ATTEMPTS} resets - nothing to inject a reply against")


def _ceiling_client(dut_ip: str, path: str, reference: "frozenset[str]", results: "list[str]", index: int) -> None:
    started = time.monotonic()
    try:
        keys = _keys(dut_ip, path, _LOADED_FETCH_TIMEOUT_S)
        elapsed = time.monotonic() - started
        results[index] = "ok" if keys == reference and elapsed < _SERVED_ELAPSED_MAX_S else f"{path}: keys {sorted(keys ^ reference)} differ or {elapsed:.1f}s"
    except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError) as exc:
        # A truncated body is the case under test: it lands in results with its path, never as a dead thread.
        results[index] = f"{path}: {exc!r}"


def _closed_after(sock: socket.socket, since: float, bound_s: float) -> "float | None":
    # Seconds from `since` until the server closed `sock`, None while it was still open at `bound_s`.
    sock.settimeout(max(bound_s - (time.monotonic() - since), _MIN_SOCKET_WAIT_S))
    try:
        while sock.recv(4096):
            pass
    except TimeoutError:
        return None
    except ConnectionResetError:
        pass
    return time.monotonic() - since


def _extra_outcome(dut_ip: str, held: list[socket.socket]) -> bytes:
    # One connection above the held ceiling: b"" when refused (a FIN, or an RST once request bytes arrived), else what
    # it got - silent past the short wait means admitted.
    _pad(held)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as extra:
        extra.settimeout(_RAW_SOCKET_TIMEOUT_S)
        extra.connect((dut_ip, 80))  # the kernel's accept queue takes it even though _serve() rejects it at once
        extra.settimeout(_ADMITTED_SILENCE_S)
        try:
            return extra.recv(4096)
        except ConnectionResetError:
            return b""
        except TimeoutError:
            return b"<held open: admitted>"


def _fetch_timeout_s() -> float:
    # The client's reply timeout: NtpTiming.fetch_timeout_ms, which buildgen/codegen.py writes into the device module.
    return _load.buildgen_number("codegen.py", "_NTP_FETCH_TIMEOUT_MS") / 1000


def _garbage_window(board: Board, bench: "BenchBridge", dut_ip: str, port: int) -> "tuple[list[str], dict[str, int]]":
    # A rogue responder on the port the OS picked, the DUT's `port` redirected to it, a reset forcing a fresh exchange,
    # and the log tailed; the redirect is cleared on every path.
    with RogueUdpResponder(_GARBAGE_PAYLOAD) as responder:
        bench.redirect_udp_port_to_local(port, responder.port)
        try:
            kick_then_reset(board, bench)  # forces a fresh exchange against the now-rogue server
            lines = board.tail_log(duration_s=_ROGUE_TAIL_S)  # past the client's retry and backoff budget
        finally:
            bench.clear_udp_port_redirect(port, responder.port)
        return lines, dict(responder.answered_from)


def _http_dropped(dut_ip: str) -> int:
    # GET /status's HTTPDropped: the connections dropped in the last 24 hours, so a burst's own refusals all count.
    dropped = _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("networking"), "GET /status networking").get("HTTPDropped")
    assert isinstance(dropped, int) and not isinstance(dropped, bool), f"GET /status carries no HTTPDropped count: {dropped!r}"
    return dropped


def _impaired(board: Board, bench: "BenchBridge", dut_ip: str, reachable_within_s: float, **impairment: float) -> None:
    # Inject, REST reachable under it, clear, fully recovered - the whole window watched for a crash, then WEBSERVER;
    # each caller asserts no task ended itself.
    def window() -> None:
        bench.inject_network_degradation(**impairment)
        try:
            wait_until(lambda: _load.serving(dut_ip), timeout_s=reachable_within_s, poll_interval_s=_RECONNECT_POLL_S, description=f"REST reachable under {impairment}")
        finally:
            bench.clear_network_degradation()
        wait_until(lambda: _load.serving(dut_ip), timeout_s=_WAIT_TIMEOUT_S, poll_interval_s=_WAIT_POLL_S, description=f"REST fast and reliable again after {impairment} cleared")

    _result, lines = observe_during(board, window)
    assert not crash_lines(lines), f"{impairment} crashed the system instead of degrading cleanly: {crash_lines(lines)}"
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


def _index_load(dut_ip: str, reference: bytes, sizes: "list[int | str]", index: int) -> None:
    try:
        res = http_client.fetch(dut_ip, 80, "GET", "/", timeout_s=_LOADED_FETCH_TIMEOUT_S)
        sizes[index] = len(res.body) if res.status_code == 200 and res.body == reference else f"status {res.status_code}, {len(res.body)} B, differs"
    except (OSError, http_client.HTTP_ERROR) as exc:
        sizes[index] = repr(exc)


def _keys(dut_ip: str, path: str, timeout_s: float) -> "frozenset[str]":
    # One GET's parsed object's key set; urllib raises on a body short of its Content-Length (a truncated stream).
    res = http_client.fetch(dut_ip, 80, "GET", path, timeout_s=timeout_s)
    assert res.status_code == 200, f"{path} answered {res.status_code}"
    return frozenset(res.json())


def _link_poller(dut_ip: str, stop: threading.Event, polls: "list[tuple[float, JSONObject | None]]") -> None:
    # GET /status every _FLASH_STALL_POLL_S: (time, its networking object), or None for a poll the link dropped.
    while not stop.is_set():
        try:
            networking: JSONObject | None = _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("networking"), "GET /status networking")
        except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError):
            networking = None
        polls.append((time.monotonic(), networking))
        stop.wait(_FLASH_STALL_POLL_S)


def _mem_free(dut_ip: str) -> int:
    free = _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("system"), "GET /status system").get("MemFree")
    assert isinstance(free, int), f"GET /status carries no MemFree: {free!r}"
    return free


def _ntp_retry_period_s() -> float:
    # The unsynced client's first retry step: its default interval, rounded up to the check tick it is counted on.
    return max(_load.src_number(_NTP, "_DEFAULT_RETRY_S"), _load.src_number(_NTP, "_NTP_CHECK_INTERV"))


def _openhab_client(dut_ip: str, paths: "list[str]", interval_s: float, stop: threading.Event, latencies: "dict[str, list[float]]", failures: "list[str]") -> None:
    # One client polling `paths` in turn every `interval_s` until stopped: each answer a complete 200, JSON parsed where
    # JSON, its latency recorded; a refusal or anything else is a failure.
    while not stop.is_set():
        for path in paths:
            started = time.monotonic()
            try:
                res = http_client.fetch(dut_ip, 80, "GET", path, timeout_s=_LOADED_FETCH_TIMEOUT_S)
                if res.status_code != 200:
                    failures.append(f"{path}: {res.status_code}")
                elif res.headers.get("Content-Type", "").startswith("application/json"):
                    res.json()
            except (OSError, http_client.HTTP_ERROR, ValueError, TypeError) as exc:
                failures.append(f"{path}: {exc!r}")
                continue
            latencies.setdefault(path, []).append(time.monotonic() - started)
        stop.wait(interval_s)


def _pad(held: list[socket.socket]) -> None:
    for index, sock in enumerate(held):
        try:
            sock.sendall(HELD_PAD_LINE)  # resets its per-call read timeout, as the ceiling probe does
        except OSError as exc:
            raise AssertionError(f"held connection {index} of {len(held)} was closed ({exc!r}) - the ceiling was not free when the test began") from exc


def _put_sized(dut_ip: str, total_bytes: int, timeout_s: float = _PROBE_TIMEOUT_S) -> int:
    return http_client.fetch(dut_ip, 80, "PUT", "/sensors", _sized_sensors_body(total_bytes), timeout_s=timeout_s).status_code


def _read_until_closed(sock: socket.socket) -> bytes:
    # Everything the server sends until it closes, or until the socket's timeout (the caller's to judge).
    response = b""
    try:
        while chunk := sock.recv(4096):
            response += chunk
    except TimeoutError:
        pass
    return response


def _reconnected_after_forced_resync(board: Board, bench: "BenchBridge", dut_ip: str, result_note: "_load.Note") -> None:
    recover_by_reset(board, bench, ready=lambda: _load.serving(dut_ip), first_wait_s=_RECONNECT_TIMEOUT_S, retry_wait_s=_RECONNECT_TIMEOUT_S, skipped="the passive reconnect after the forced resync", note=result_note, description="the forced resync against a rogue server")


def _repair_target_note(result_note: "_load.Note", what: str) -> None:
    result_note(f"repaired a leftover garbage {what} from an aborted run", recovery=True)


def _restore_over_hotspot(board: Board, bench: "BenchBridge", hostname: str, target_ssid: str, reason: str, result_note: "_load.Note") -> None:
    # The DUT's hotspot opens once its streak fails: the bench radio, freed, scans for it, joins (the first join is
    # retried once through a reported reset), takes a lease and PUTs the SSID back; the bridge returns on every path.
    try:
        bench.ap_down()
        wait_until(lambda: bench.is_ssid_visible(hostname), timeout_s=_RECONNECT_TIMEOUT_S, poll_interval_s=_WAIT_POLL_S, description=f"the DUT's own hotspot ({hostname!r}) to become scannable")
        recover_by_reset(board, bench, ready=lambda: _try_join(bench, hostname), first_wait_s=_JOIN_ATTEMPTS * _JOIN_HOTSPOT_TIMEOUT_S, retry_wait_s=_JOIN_ATTEMPTS * _JOIN_HOTSPOT_TIMEOUT_S, skipped="the first join attempt", note=result_note, description="joining the DUT's hotspot")
        wait_until(lambda: bool(bench.gateway_ip()), timeout_s=_DHCP_TIMEOUT_S, poll_interval_s=_DHCP_POLL_S, description="DHCP lease on the DUT's own hotspot")
        gateway_ip = bench.gateway_ip()
        wait_until(lambda: _load.serving(gateway_ip), timeout_s=_WAIT_TIMEOUT_S, poll_interval_s=_WAIT_POLL_S, description="DUT REST reachable over its own hotspot")
        _restore_ssid_over(gateway_ip, target_ssid, reason)
    finally:
        bench.leave_dut_hotspot_and_restore_bridge()
    bench.kick_all_stations()


def _restore_ssid_over(host: str, original_ssid: str, reason: str) -> None:
    # Checked before any reset erases it, over whichever address still reaches the DUT.
    assert_no_task_ended(host, "a garbage SSID")
    reset_all_error_logs(host, reason)
    restore = http_client.fetch(host, 80, "PUT", "/networking", {"SSID": original_ssid}, timeout_s=_PROBE_TIMEOUT_S)
    assert restore.status_code == 200, f"failed to restore original SSID {original_ssid!r}: {restore.status_code} {restore.body!r}"
    assert _load.as_object(restore.json().get("result"), "result").get("SSID") in ("Valid", "Unchanged"), f"restoring the original SSID was rejected: {restore.body!r}"


def _sized_sensors_body(total_bytes: int) -> "JSONObject":
    # A PUT /sensors body of exactly total_bytes, under a sensor key no driver registers. Unknown keys are ignored
    # silently, so nothing validates, persists or logs: the size is the whole subject.
    envelope = len(json.dumps({"HWTESTNoSuchSensor": {"Padding": ""}}).encode())
    body: JSONObject = {"HWTESTNoSuchSensor": {"Padding": "x" * (total_bytes - envelope)}}
    assert len(json.dumps(body).encode()) == total_bytes, "padding arithmetic drifted from json.dumps()"
    return body


def _sized_worker(dut_ip: str, index: int, size: int, outcomes: "dict[str, dict[int, int | str]]", lock: threading.Lock) -> None:
    # One PUT of `size`, its outcome filed under answered, refused (at the ceiling) or other; never raised.
    try:
        status: int | str = _put_sized(dut_ip, size, timeout_s=_LOADED_FETCH_TIMEOUT_S)
        bucket = "answered"
    except (OSError, http_client.HTTP_ERROR) as exc:
        status, bucket = f"{type(exc).__name__}: {exc}", "refused" if http_client.is_ceiling_close(exc) else "other"
    with lock:
        outcomes[bucket][index] = status


def _try_join(bench: "BenchBridge", ssid: str) -> bool:
    try:
        bench.join_dut_hotspot(ssid, hotspot_password(), timeout_s=_JOIN_HOTSPOT_TIMEOUT_S)
    except HardwareTestFailureError:
        return False
    return True


def _utc_year(dut_ip: str) -> "int | None":
    # GET /status's UTCTime year; None while the board has not synced (UTCTime is null then).
    utc = _load.as_object(_load.get_object(dut_ip, "/status", _PROBE_TIMEOUT_S).get("system"), "GET /status system").get("UTCTime")
    if utc is None:
        return None
    year = _load.as_object(utc, "GET /status system.UTCTime").get("Year")
    assert isinstance(year, int), f"UTCTime carries no Year: {utc!r}"
    return year


def _website_routes(device: str) -> "tuple[str, float]":
    # The route the page polls on landing and its interval, from the generated definitions the website itself reads.
    definitions = json.loads(json.dumps(definitions_for_toml(device_toml(device), SRC_DIR)))
    landing = definitions["landingSection"]
    section = next(s for s in definitions["sections"] if s["key"] == landing)
    return str(section["rest"]["get"]), float(section.get("pollIntervalMs") or definitions["defaultPollIntervalMs"]) / 1000
