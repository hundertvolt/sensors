"""Bench-tier automated tests for real WiFi outage/flap, NTP/DNS servers answering with garbage
(BACKLOG.md open question #5), the webserver's max_connections=4 ceiling, malformed REST requests,
and slowloris/abrupt disconnects - DHCP-client flakiness is deliberately out of scope (see BACKLOG.md).
"""

from __future__ import annotations

import http.client
import json
import socket
import threading
import time
from typing import TYPE_CHECKING

import http_client
import ntp_probe
import pytest
from error_log_helpers import (
    assert_module_error_log_contains,
    assert_module_error_log_empty,
    get_errcount,
    reset_all_error_logs,
)
from harness import Board, HardwareTestFailureError, wait_until
from rogue_udp_responder import RogueUdpResponder

if TYPE_CHECKING:
    from bench_control import BenchBridge

# ---------------------------------------------------------------------------
# WiFi outage or flap inside an already-established STA connection. Per
# _on_sta_disconnected(), that case takes the safe "retry in 60s" branch and never increments
# connection_failures or reaches hotspot fallback - read out of the source, not assumed.
# ---------------------------------------------------------------------------


def test_real_wifi_outage_and_recovery_while_in_normal_sta_mode(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    bench.ap_down()
    try:
        # No assertion here that the DUT notices within any particular window - the real behavior
        # (per asy_wifi_service.py above) is a 60s retry cadence with no upper bound on how long the
        # outage itself lasts, so a brief outage is a fully realistic, low-risk window to inject.
        time.sleep(15.0)
    finally:
        bench.ap_up()
        bench.kick_all_stations()  # clears any stale AP-side entry - see this module's own finding below

    # The CYW43 firmware can report associated while the link is dead, and neither
    # kick_all_stations() nor the retry logic reliably clears it (tests_hardware/README.md). A
    # fallback hard_reset() is a genuine pass per CLAUDE.md; the notes below record which ran.
    recovered_via_hard_reset = False
    recovery_started = time.monotonic()
    try:
        wait_until(
            lambda: _sta_reconnected(dut_ip),
            timeout_s=150.0,
            poll_interval_s=5.0,
            description="DUT to re-establish its real STA connection after the bridge AP comes back up",
        )
        print(f"RESULT NOTE: recovered gracefully in {time.monotonic() - recovery_started:.1f}s (bench.ap_up() to first reachable /status)")
    except TimeoutError:
        recovered_via_hard_reset = True
        graceful_wait_s = time.monotonic() - recovery_started
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable again after a recovery hard_reset() (see this test's own comment)")
        print(f"RESULT NOTE: recovered via a fallback hard_reset() - the graceful established-connection retry did not clear this real CYW43-firmware characteristic within {graceful_wait_s:.1f}s")

    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after a real WiFi outage and recovery"
    if not recovered_via_hard_reset:
        _assert_wifi_log_has_only_benign_ap_not_found_warning(dut_ip)


def test_real_wifi_flaps_repeatedly_without_wedging_the_system(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    for _cycle in range(3):
        bench.ap_down()
        time.sleep(3.0)  # short relative to the 60s retry cadence above - the DUT is still mid-wait, not yet retrying
        bench.ap_up()
        time.sleep(3.0)
    # kick_all_stations() once, after the last flap - see test_real_wifi_outage_and_recovery_while_
    # in_normal_sta_mode's own comment for the full finding (a real, disclosed CYW43-firmware-level
    # gap, not fully explained or fixed by this alone).
    bench.kick_all_stations()

    # Same hard_reset()-fallback-is-a-real-pass pattern as test_real_wifi_outage_and_recovery_
    # while_in_normal_sta_mode above, same reason - see that test's own comment.
    recovered_via_hard_reset = False
    recovery_started = time.monotonic()
    try:
        wait_until(
            lambda: _sta_reconnected(dut_ip),
            timeout_s=150.0,
            poll_interval_s=5.0,
            description="DUT to re-establish its real STA connection after repeated AP flapping",
        )
        print(f"RESULT NOTE: recovered gracefully in {time.monotonic() - recovery_started:.1f}s (last bench.ap_up() to first reachable /status)")
    except TimeoutError:
        recovered_via_hard_reset = True
        graceful_wait_s = time.monotonic() - recovery_started
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable again after a recovery hard_reset() (see this test's own comment)")
        print(f"RESULT NOTE: recovered via a fallback hard_reset() - the graceful established-connection retry did not clear this real CYW43-firmware characteristic within {graceful_wait_s:.1f}s")

    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after repeated real WiFi flapping"
    if not recovered_via_hard_reset:
        _assert_wifi_log_has_only_benign_ap_not_found_warning(dut_ip)  # same reasoning as the single-outage test above


def _assert_wifi_log_has_only_benign_ap_not_found_warning(dut_ip: str) -> None:
    """Tolerates exactly one benign "WLAN access point not found" warning (wrnno=5) after a
    graceful recovery - a real, correctly-logged transient condition from an active retry poll
    landing mid-outage, not a bug (see tests_hardware/README.md). Anything else still fails."""
    entry = get_errcount(dut_ip).get("WIFI", {})
    history = entry.get("history", [])
    # "N" entries are print_log.py's own "nothing recorded" padding (get_log()'s own encoding) -
    # always present, filling out the fixed-size ring, and not a real log line at all.
    unexpected = [h for h in history if h.get("type") != "N" and not (h.get("type") == "W" and h.get("num") == 5)]
    assert not unexpected, f"WIFI error log had unexpected entries beyond the known-benign wrnno=5: {unexpected!r} (full: {entry!r})"


def _sta_reconnected(dut_ip: str) -> bool:
    try:
        return http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Real loss, latency, corruption, duplication and reordering via inject_network_degradation() -
# perturbing real packets, unlike the binary block/redirect faults elsewhere here. The parameter
# ranges come from researched real-world WiFi figures (tests_hardware/README.md).
# ---------------------------------------------------------------------------


def test_real_operations_survive_and_recover_under_sustained_packet_loss_and_latency(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    bench.inject_network_degradation(loss_pct=30, delay_ms=150, jitter_ms=50)
    try:
        # Under sustained 30% loss and 150ms(+/-50ms) latency any individual request may
        # legitimately fail; the property is that a bounded retry loop still gets through. 90s is
        # generous against a handful of client retries at those figures.
        wait_until(
            lambda: _sta_reconnected(dut_ip),
            timeout_s=90.0,
            poll_interval_s=3.0,
            description="DUT still eventually reachable over REST under sustained packet loss/latency",
        )
    finally:
        bench.clear_network_degradation()

    joined = "\n".join(board.tail_log(duration_s=5.0))  # a brief passive window, purely for the crash check below
    crash_markers = [ln for ln in joined.splitlines() if "Traceback" in ln]
    assert not crash_markers, "sustained packet loss/latency crashed the system instead of degrading cleanly:\n" + "\n".join(crash_markers)

    # Full recovery once the degradation clears - back to fast, reliable responses, not left in some
    # lingering half-degraded state (e.g. a retry loop that only backs off and never resets).
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description="DUT fully recovered (fast, reliable REST) after network degradation cleared",
    )
    reset_all_error_logs(dut_ip)  # never leave a deliberately-provoked fault in the live error history


def test_real_operations_unaffected_by_light_realistic_wifi_congestion(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # The "everyday" end of the researched range (30ms delay, 20ms jitter, 0.5-5% loss) - unlike
    # the sustained/severe test above, requests here should just succeed first try, with no
    # special retry tolerance needed.
    reset_all_error_logs(dut_ip)
    bench.inject_network_degradation(loss_pct=2, delay_ms=30, jitter_ms=20)
    try:
        for _ in range(5):
            res = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0)
            assert res.status_code == 200, f"a plain GET /status failed under light, realistic WiFi congestion (2% loss/30ms delay): {res.status_code} {res.body!r}"
            time.sleep(1.0)
    finally:
        bench.clear_network_degradation()
    assert_module_error_log_empty(dut_ip, "NTP")


def test_real_operations_survive_real_packet_corruption(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # Unlike the rogue-responder tests below, corrupt() flips a random bit inside an otherwise-real
    # packet (a radio-level bit error) - real UDP/TCP checksums should catch and drop/retransmit
    # it, which is exactly the property this test confirms rather than assumes.
    reset_all_error_logs(dut_ip)
    bench.inject_network_degradation(corrupt_pct=5)
    try:
        wait_until(
            lambda: _sta_reconnected(dut_ip),
            timeout_s=60.0,
            poll_interval_s=3.0,
            description="DUT still eventually reachable over REST under real packet corruption",
        )
    finally:
        bench.clear_network_degradation()

    joined = "\n".join(board.tail_log(duration_s=5.0))
    crash_markers = [ln for ln in joined.splitlines() if "Traceback" in ln]
    assert not crash_markers, "real packet corruption crashed the system instead of the checksum layer cleanly dropping it:\n" + "\n".join(crash_markers)

    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description="DUT fully recovered after packet corruption cleared",
    )
    reset_all_error_logs(dut_ip)


def test_real_operations_survive_duplicated_and_reordered_packets(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # A real duplicated/out-of-order UDP delivery - checks whether a duplicate or late reply ever
    # gets mismatched against a different, later pending request. `reorder` needs an existing
    # `delay` to be meaningful (man tc-netem) - the light delay here is for that, not as its own stressor.
    reset_all_error_logs(dut_ip)
    bench.inject_network_degradation(delay_ms=20, duplicate_pct=10, reorder_pct=25)
    try:
        wait_until(
            lambda: _sta_reconnected(dut_ip),
            timeout_s=60.0,
            poll_interval_s=3.0,
            description="DUT still reachable over REST under real duplicated/reordered packets",
        )
    finally:
        bench.clear_network_degradation()

    joined = "\n".join(board.tail_log(duration_s=5.0))
    crash_markers = [ln for ln in joined.splitlines() if "Traceback" in ln]
    assert not crash_markers, "duplicated/reordered packets crashed the system instead of being handled cleanly:\n" + "\n".join(crash_markers)

    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200,
        timeout_s=30.0,
        poll_interval_s=2.0,
        description="DUT fully recovered after duplication/reordering cleared",
    )
    reset_all_error_logs(dut_ip)


@pytest.mark.persistence_write
def test_ntp_recovers_via_its_own_retry_timer_after_a_transient_outage_with_no_reboot(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # The real-hardware form of test_asy_ntp_client.py's retry-after-one-dropped-request test:
    # the retry timer alone recovers, with no reboot. A guaranteed block_udp_ports() rather than
    # netem loss, so the outage outlasts _NTP_CONN_TIMEOUT (5s) but clears inside the 15s retry.
    get_before = http_client.fetch(dut_ip, 80, "GET", "/networking", timeout_s=10.0)
    assert get_before.status_code == 200, f"GET /networking failed: {get_before.status_code} {get_before.body!r}"
    original_host = get_before.json()["NTP_Host"]

    def _synced() -> bool:
        status = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).json()
        return status.get("networking", {}).get("NtpSynced") is True

    # dut_ip only waits for HTTP reachability, not specifically for NTP sync to finish - confirmed
    # directly (NtpLastSyncAge showed sync completing only ~12s after dut_ip returned), so this is
    # a real precondition worth waiting for, not asserting instantly.
    wait_until(_synced, timeout_s=30.0, poll_interval_s=2.0, description="test precondition: DUT to report NTP-synced before this test's own transient-outage fault starts")
    reset_all_error_logs(dut_ip)

    bench.block_udp_ports([123])
    try:
        # Re-triggers a real resync without a reboot: PUT-ing NTP_Host back to its current value
        # still fires post_asy_fct, which runs if ANY field in the call validated (the garbage-
        # NTP_Host test below has the full account).
        put_res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"NTP_Host": original_host}, timeout_s=10.0)
        assert put_res.status_code == 200 and put_res.json()["result"].get("NTP_Host") in ("Valid", "Unchanged"), f"re-triggering PUT /networking NTP_Host={original_host!r} was rejected: {put_res.status_code} {put_res.body!r}"
        time.sleep(8.0)  # longer than the real 5s fetch timeout, so this attempt genuinely fails, not just races a lucky window
    finally:
        bench.unblock_udp_ports([123])

    # Cleared well before the real 15s retry interval elapses - the retry timer's own next attempt
    # must land on a genuinely clear network and succeed, with no hard_reset() anywhere in this test.
    wait_until(_synced, timeout_s=20.0, poll_interval_s=1.0, description="NTP resynced via its own retry timer after a transient (not sustained) outage, with no reboot")
    reset_all_error_logs(dut_ip)  # the one deliberately-provoked failed attempt above did legitimately log something - never leave that in the live error history


# ---------------------------------------------------------------------------
# NTP/DNS servers answering with garbage rather than being unreachable (BACKLOG open question 5).
# test_wifi_networking.py covers a dropped server; these two redirect the real port to a local
# rogue responder via redirect_udp_port_to_local(), which its own docstring marks unverified.
# ---------------------------------------------------------------------------

_ROGUE_LOCAL_PORT_NTP = 42123
_ROGUE_LOCAL_PORT_DNS = 42153
_GARBAGE_PAYLOAD = b"this is not a valid NTP or DNS wire-format packet, on purpose"


def test_ntp_server_sends_garbage_instead_of_a_valid_response(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    with RogueUdpResponder(_ROGUE_LOCAL_PORT_NTP, _GARBAGE_PAYLOAD):
        bench.redirect_udp_port_to_local(123, _ROGUE_LOCAL_PORT_NTP)
        try:
            bench.kick_all_stations()  # see conftest.py's dut_ip docstring for the full finding
            board.hard_reset()  # forces a fresh NTP sync attempt against the now-rogue server
            lines = board.tail_log(duration_s=90.0)  # generous relative to asy_ntp_client.py's own retry/backoff budget
        finally:
            bench.clear_udp_port_redirect(123, _ROGUE_LOCAL_PORT_NTP)

    joined = "\n".join(lines)
    crash_markers = [ln for ln in lines if "Traceback" in ln]
    assert not crash_markers, "a garbage NTP response crashed the system instead of being rejected cleanly:\n" + "\n".join(crash_markers)
    assert "CFGMGR_" in joined or "FRAM" in joined, f"system did not appear to finish booting with a garbage-answering NTP server:\n{joined}"
    # Read from the live tail_log, not the REST errcount history, whose fixed 10-entry window a
    # full 90s of garbage evicts. "Invalid NTP time received!" is the string because it fires for
    # either rejection branch this 63-byte payload can hit (errno 14 or 15).
    assert "Invalid NTP time received!" in joined, f"no sign of a rejected NTP sync attempt observed - the garbage payload may not have reached the DUT at all:\n{joined}"

    # Bounded recovery retry - see test_wifi_networking.py's own equivalent comment.
    try:
        wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again after the hard_reset() above")
    except TimeoutError:
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again (after one recovery hard_reset() retry)")
    reset_all_error_logs(dut_ip)  # never leave a deliberately-provoked fault in the live error history


def test_dns_server_sends_garbage_instead_of_a_valid_response(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    with RogueUdpResponder(_ROGUE_LOCAL_PORT_DNS, _GARBAGE_PAYLOAD):
        bench.redirect_udp_port_to_local(53, _ROGUE_LOCAL_PORT_DNS)
        try:
            bench.kick_all_stations()  # see conftest.py's dut_ip docstring for the full finding
            board.hard_reset()  # forces a fresh DNS resolution attempt against the now-rogue server
            lines = board.tail_log(duration_s=90.0)
        finally:
            bench.clear_udp_port_redirect(53, _ROGUE_LOCAL_PORT_DNS)

    joined = "\n".join(lines)
    crash_markers = [ln for ln in lines if "Traceback" in ln]
    assert not crash_markers, "a garbage DNS response crashed the system instead of being rejected cleanly:\n" + "\n".join(crash_markers)
    assert "CFGMGR_" in joined or "FRAM" in joined, f"system did not appear to finish booting with a garbage-answering DNS server:\n{joined}"

    # Bounded recovery retry - see test_wifi_networking.py's own equivalent comment.
    try:
        wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again after the hard_reset() above")
    except TimeoutError:
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again (after one recovery hard_reset() retry)")
    # No standalone DNS-client error log exists (resolve_ipv4() is a plain function, no
    # PrintLogHistory of its own) - a garbage reply fails the same sanity checks as no reply at
    # all, so resolve_ipv4() exhausts every server and lands on "NTP" module's own errno=12.
    try:
        assert_module_error_log_contains(dut_ip, "NTP", 12, "E")
    finally:
        reset_all_error_logs(dut_ip)


# ---------------------------------------------------------------------------
# Connected-socket source-address filtering (BACKLOG open question 5), which the garbage-response
# tests cannot reach: DNAT+conntrack rewrites the reply's source back first. So capture the DUT's
# ephemeral port with tcpdump and answer it from this host's own IP - no raw sockets needed.
# ---------------------------------------------------------------------------

_NTP_SPOOF_INJECTED_UNIX_TIME = 2524608000  # 2050-01-01T00:00:00Z - decades from any real "now", safely inside _parse_ntp_reply()'s own 2025-2100 plausibility window


def test_ntp_connected_socket_rejects_a_reply_from_an_unexpected_source(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # A connect()'d client socket that only accepts datagrams from its true peer must silently drop
    # a reply from anywhere else - checkable via GET /status's UtcTime, since an accepted reply's
    # crafted Transmit Timestamp (2050-01-01) directly sets the RTC (asy_ntp_client.py's _parse_ntp_reply()).
    get_before = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0)
    assert get_before.status_code == 200, f"GET /status failed: {get_before.status_code} {get_before.body!r}"
    year_before = get_before.json()["system"]["UtcTime"]["year"]
    assert 2020 < year_before < 2049, f"DUT's own UtcTime is already outside a sane pre-test range, can't use it as this test's own signal: {year_before}"

    reset_all_error_logs(dut_ip)
    try:
        # Bounded retry of the whole capture attempt: this bench's known ~1-in-3 reachability
        # hiccup (BACKLOG.md open question 9) can land a hard_reset() in hotspot fallback instead,
        # sending no STA-side UDP traffic for tcpdump to see.
        dut_ephemeral_port = None
        attempts_made = 0
        for _attempt in range(3):
            attempts_made += 1
            capture = bench.start_udp_source_capture(dut_ip, 123)
            bench.kick_all_stations()  # see conftest.py's dut_ip docstring for the full finding
            board.hard_reset()  # forces a fresh NTP sync attempt, giving this capture a request to observe
            dut_ephemeral_port = bench.read_captured_udp_source_port(capture, timeout_s=55.0)  # generous relative to asy_ntp_client.py's own retry/backoff budget - see test_wifi_networking.py's equivalent comment
            if dut_ephemeral_port is not None:
                break
        assert dut_ephemeral_port is not None, f"never observed a real NTP request from the DUT across {attempts_made} hard_reset() attempts - nothing to inject a reply against"

        spoofed_reply = ntp_probe.build_reply(_NTP_SPOOF_INJECTED_UNIX_TIME)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as spoof_sock:
            spoof_sock.sendto(spoofed_reply, (dut_ip, dut_ephemeral_port))

        time.sleep(3.0)  # generous relative to _parse_ntp_reply()'s own synchronous RTC().datetime() write, if it were ever reached
        get_after = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0)
        assert get_after.status_code == 200, f"GET /status failed: {get_after.status_code} {get_after.body!r}"
        year_after = get_after.json()["system"]["UtcTime"]["year"]
        assert year_after != 2050, f"the DUT's RTC was set to this test's own spoofed reply's injected date (2050-01-01) - AsyUDPSocket accepted a reply from an unexpected source on a connected socket:\n{get_after.body!r}"
    finally:
        # Always runs, even on a failed assertion above - this test's own last hard_reset() must
        # never leave the DUT unreachable or its error history dirty for whatever runs next.
        try:
            wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again after the hard_reset() above")
        except TimeoutError:
            bench.kick_all_stations()
            board.hard_reset()
            wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again (after one recovery hard_reset() retry)")
        reset_all_error_logs(dut_ip)


# ---------------------------------------------------------------------------
# A config-level NTP fault rather than a network-level one: PUT a garbage NTP_Host on a live
# link, watch the DNS failure degrade cleanly, restore, confirm recovery. Starting already-synced
# is the point - it reaches _handle_ntp_sync_failure()'s ntp_issynced() branch, which nothing did.
# ---------------------------------------------------------------------------

# RFC 2606 reserves .invalid specifically so it can never resolve to a real address - a genuine,
# permanent DNS-resolution failure, not a flaky "might resolve to something on some networks" guess.
_GARBAGE_NTP_HOST = "this-host-will-never-resolve.invalid"


@pytest.mark.persistence_write
def test_garbage_ntp_host_via_rest_config_degrades_and_recovers_cleanly(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    get_before = http_client.fetch(dut_ip, 80, "GET", "/networking", timeout_s=10.0)
    assert get_before.status_code == 200, f"GET /networking failed: {get_before.status_code} {get_before.body!r}"
    original_host = get_before.json()["NTP_Host"]
    # An earlier run aborted before its own restore leaves the board already on the garbage value.
    # The PUT below is then reported "Unchanged" and fires no post_asy_fct, so name that cause here
    # rather than let it surface as "rejected at the schema level", which it would not have been.
    assert original_host != _GARBAGE_NTP_HOST, f"the board is already on {_GARBAGE_NTP_HOST!r} - an earlier run aborted before restoring; put NTP_Host back before rerunning"

    try:
        reset_all_error_logs(dut_ip)
        put_res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"NTP_Host": _GARBAGE_NTP_HOST}, timeout_s=10.0)
        assert put_res.status_code == 200, f"PUT /networking NTP_Host={_GARBAGE_NTP_HOST!r} failed: {put_res.status_code} {put_res.body!r}"
        # _VAL_NH bounds string length (3-1024) and nothing else, so a syntactically garbage but
        # length-valid host is accepted as "Valid". The failure surfaces later, in the DNS
        # resolution that this field's own post_asy_fct triggers.
        assert put_res.json()["result"].get("NTP_Host") == "Valid", f"garbage NTP_Host was rejected at the schema level, not what this test means to exercise: {put_res.json()!r}"

        # post_asy_fct resyncs asynchronously, so poll for the DNS failure to land:
        # _resolve_ntp_server() logs "No valid NTP server:" at errno=12 - the same path the
        # network-level garbage-response test hits, reached by a bad hostname instead.
        wait_until(
            lambda: _ntp_error_log_contains(dut_ip, 12),
            timeout_s=30.0,
            poll_interval_s=2.0,
            description="NTP module to log errno=12 (No valid NTP server) for the garbage NTP_Host",
        )
        # The rest of the system must stay fully healthy throughout - a bad NTP host degrading
        # gracefully means exactly this, not just "the error got logged".
        assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive while NTP_Host was garbage"
    finally:
        # Restore the real, original NTP_Host regardless of outcome - this PUT mutates the board's
        # real, persisted config on a shared bench rig.
        reset_all_error_logs(dut_ip)
        restore_res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"NTP_Host": original_host}, timeout_s=10.0)
        assert restore_res.status_code == 200, f"failed to restore original NTP_Host {original_host!r}: {restore_res.status_code} {restore_res.body!r}"
        # "Unchanged" counts as restored, as in _restore_ssid_over() and the sensor-config files:
        # if the body failed before its PUT landed the board is still on original_host, and
        # insisting on "Valid" would replace the real failure with a cleanup assertion.
        assert restore_res.json()["result"].get("NTP_Host") in ("Valid", "Unchanged"), f"restoring the original NTP_Host was rejected: {restore_res.json()!r}"

    # Recovery: the restore PUT fires post_asy_fct too, and that resync must succeed. Read from
    # NtpSynced under GET /status's nested "networking" object - GET /networking is config schema
    # only and has no such field, which was a real test bug (tests_hardware/README.md).
    def _synced() -> bool:
        status = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).json()
        return status.get("networking", {}).get("NtpSynced") is True

    # hard_reset() fallback is a defensive measure against a rare real WiFi hiccup - a resync is
    # expected well inside the first 30s in the overwhelming majority of runs; needing this
    # fallback at all is worth a second look, not an expected outcome.
    try:
        wait_until(_synced, timeout_s=30.0, poll_interval_s=2.0, description=f"NTP to report synced again after restoring a real NTP_Host ({original_host!r})")
    except TimeoutError:
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(_synced, timeout_s=120.0, poll_interval_s=3.0, description=f"NTP to report synced again (after one recovery hard_reset() retry, real NTP_Host={original_host!r})")
    assert_module_error_log_empty(dut_ip, "NTP")


def _ntp_error_log_contains(dut_ip: str, errno: int) -> bool:
    entry = get_errcount(dut_ip).get("NTP")
    if entry is None:
        return False
    return any(h.get("num") == errno and h.get("type") == "E" for h in entry.get("history", []))


# ---------------------------------------------------------------------------
# A real-format SSID no AP here broadcasts; _VAL_SSID bounds length only, the same gap as
# NTP_Host. It aims to finish inside the ~50s before hotspot fallback takes dut_ip away, and when
# jitter blows that budget it joins the DUT's own hotspot instead - a recovery path is a pass.
# ---------------------------------------------------------------------------

_GARBAGE_SSID = "wozi-test-net-does-not-exist"  # <=32 chars (_VAL_SSID's own cap) - real 2.4GHz-legal SSID format/length, just not broadcast by anything on this bench
_HOTSPOT_PASSWORD = "12345678"  # hardcoded in src/asy_wifi_service.py's _configure_hotspot_ap()


@pytest.mark.persistence_write
def test_garbage_ssid_via_rest_config_is_handled_gracefully(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    get_before = http_client.fetch(dut_ip, 80, "GET", "/networking", timeout_s=10.0)
    assert get_before.status_code == 200, f"GET /networking failed: {get_before.status_code} {get_before.body!r}"
    original_ssid = get_before.json()["SSID"]
    original_hostname = get_before.json()["Hostname"]
    # Same as the garbage-NTP_Host test above: an aborted earlier run leaves the board already on
    # the garbage SSID, making the PUT below "Unchanged" - no reconnect_wifi() post_fct fires, and
    # the failure would blame schema validation for what is a board-state problem.
    assert original_ssid != _GARBAGE_SSID, f"the board is already on {_GARBAGE_SSID!r} - an earlier run aborted before restoring; put SSID back before rerunning"

    reset_all_error_logs(dut_ip)
    put_res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"SSID": _GARBAGE_SSID}, timeout_s=10.0)
    assert put_res.status_code == 200, f"PUT /networking SSID={_GARBAGE_SSID!r} failed: {put_res.status_code} {put_res.body!r}"
    # Length/type-only schema (see this test's own module comment above) - accepted as "Valid"
    # here; the real failure only surfaces later, from the actual (real, over-the-air) connect
    # attempt asy_wifi_service.py's own reconnect_wifi() post_fct triggers.
    assert put_res.json()["result"].get("SSID") == "Valid", f"garbage SSID was rejected at the schema level, not what this test means to exercise: {put_res.json()!r}"

    # Passive observation only - no exec()/is_reachable(), which disturb a live system
    # (harness.py). One real STAT_NO_AP_FOUND cycle logged and handled cleanly is enough, over a
    # short window, to leave margin against the hotspot-fallback budget above.
    lines = board.tail_log(duration_s=15.0)
    joined = "\n".join(lines)
    assert "Traceback" not in joined, f"a real unreachable SSID crashed the system instead of degrading cleanly:\n{joined}"
    assert "WLAN access point not found" in joined, f"no real STAT_NO_AP_FOUND cycle observed for a genuinely nonexistent SSID:\n{joined}"

    # dut_ip cannot come back while the garbage SSID is configured - a reconnect is impossible by
    # construction, not merely unlikely - so this snapshot check is correct rather than racy about
    # whether the DUT has started its connection_failures streak toward hotspot fallback.
    if http_client_is_ok(dut_ip):
        # Happy path: still reachable over the normal bridge network - restore directly. Not
        # actually expected to trigger (see comment above), kept only as a defensive fallback.
        bench.kick_all_stations()  # the coming reconnect is a genuine machine-level association - see conftest.py's dut_ip docstring
        _restore_ssid_over(dut_ip, original_ssid)
    else:
        # Fallback: once the DUT reaches hotspot fallback, restore over its own AP, as
        # test_hotspot_role_reversal.py's fixture does. Polls is_ssid_visible() generously rather
        # than sleeping, since this path arrives indirectly with no moment zero to measure from.

        # ap_down() through join_dut_hotspot() stays in this try/finally so a timeout here
        # cannot strand the bridge AP down.
        try:
            bench.ap_down()  # is_ssid_visible() needs the radio free to scan - see its own docstring
            wait_until(
                lambda: bench.is_ssid_visible(original_hostname),
                timeout_s=60.0,
                poll_interval_s=2.0,
                description=f"DUT's own hotspot ({original_hostname!r}) to become scannable",
            )
            # A freshly-started AP's beacon interval means is_ssid_visible()==True doesn't
            # guarantee nmcli's own internal rescan sees it a moment later - retry the join
            # (ap_down() is idempotent, see its own docstring).
            for attempt in range(3):
                try:
                    bench.join_dut_hotspot(original_hostname, _HOTSPOT_PASSWORD, timeout_s=45.0)
                    break
                except HardwareTestFailureError:
                    if attempt == 2:
                        raise
                    time.sleep(3.0)
            wait_until(lambda: bool(bench.gateway_ip()), timeout_s=45.0, poll_interval_s=2.0, description="DHCP lease on the DUT's own hotspot")
            gateway_ip = bench.gateway_ip()
            wait_until(lambda: http_client_is_ok(gateway_ip), timeout_s=30.0, poll_interval_s=2.0, description="DUT REST reachable over its own hotspot")
            _restore_ssid_over(gateway_ip, original_ssid)
        finally:
            bench.leave_dut_hotspot_and_restore_bridge()
        bench.kick_all_stations()

    # "Mode" lives in GET /status's nested "networking" object, not in GET /networking, which is
    # config schema only. Reading the wrong one was a test bug that could never pass whatever the
    # DUT did; tests_hardware/README.md has what it was misattributed to.
    def _reconnected_over_bridge() -> bool:
        return bool(http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).json()["networking"].get("Mode") == "STA")

    try:
        wait_until(_reconnected_over_bridge, timeout_s=60.0, poll_interval_s=3.0, description=f"Mode to return to 'STA' after restoring the real SSID ({original_ssid!r})")
    except TimeoutError:
        # Genuine fallback, matching this tier's established "a recovery path counts as a pass"
        # convention - not expected to trigger now that the check above is actually correct, but a
        # real reconnect could still, in principle, occasionally need a nudge.
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(_reconnected_over_bridge, timeout_s=60.0, poll_interval_s=3.0, description="Mode to return to 'STA' after a hard_reset() recovery attempt")
    reset_all_error_logs(dut_ip)  # the fallback path above can log its own transient WIFI history (e.g. one more STAT_NO_AP_FOUND while still mid-fallback) that isn't this test's own concern


def http_client_is_ok(host: str) -> bool:
    try:
        return http_client.fetch(host, 80, "GET", "/status", timeout_s=5.0).status_code == 200
    except OSError:
        return False


def _restore_ssid_over(host: str, original_ssid: str) -> None:
    reset_all_error_logs(host)
    restore_res = http_client.fetch(host, 80, "PUT", "/networking", {"SSID": original_ssid}, timeout_s=10.0)
    assert restore_res.status_code == 200, f"failed to restore original SSID {original_ssid!r}: {restore_res.status_code} {restore_res.body!r}"
    assert restore_res.json()["result"].get("SSID") in ("Valid", "Unchanged"), f"restoring the original SSID was rejected: {restore_res.json()!r}"


# ---------------------------------------------------------------------------
# The real connection ceiling (max_connections=4, one below lwIP's MEMP_NUM_TCP_PCB=5) degrading
# cleanly at and above the limit, which test_end_to_end_timing.py's burst never holds enough slots
# to reach. _open_conns increments on accept, so a bare connect() already occupies a slot.
# ---------------------------------------------------------------------------

_MAX_CONNECTIONS = 4


def test_connections_at_and_above_the_real_socket_limit_degrade_cleanly(dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    # The preceding PUT /status closing client-side doesn't mean the RP2040's own asyncio has run
    # _serve()'s finally block and decremented _open_conns yet - without this settle, the 4 "held"
    # sockets below start from a nonzero baseline, shifting every slot by one (confirmed directly).
    time.sleep(1.0)
    held: list[socket.socket] = []
    extra: socket.socket | None = None
    try:
        for _ in range(_MAX_CONNECTIONS):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((dut_ip, 80))
            held.append(sock)
        # A completed TCP connect() does not mean the accept loop has run _serve() and bumped
        # _open_conns yet, and under load that lag can admit the 5th connection into the app
        # layer. A real race, so the retry below uses a fresh socket rather than a longer sleep.
        time.sleep(2.0)

        for attempt in range(3):
            if extra is not None:
                extra.close()
            extra = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            extra.settimeout(10.0)
            # A bare connect() still succeeds at the kernel's accept queue even though _serve()
            # rejects it the moment its task runs: reject-when-full closes the writer without
            # ever composing a response.
            extra.connect((dut_ip, 80))
            # That close does not always surface as a clean FIN: depending on kernel TCP state
            # it can be an RST instead. Both mean "closed without writing a response", and src/
            # does not choose which, so this accepts either rather than only the empty read.
            try:
                response = extra.recv(4096)
            except ConnectionResetError:
                response = b""
            if response == b"":
                break
            last_response = response
            if attempt < 2:
                time.sleep(1.0)  # let the previous "extra" connection's own quick error-response cleanup (_open_conns.decrement()) actually complete
        assert response == b"", f"a connection above the real {_MAX_CONNECTIONS}-connection ceiling was not rejected after 3 attempts: got {last_response!r}"
    finally:
        for sock in held:
            sock.close()
        if extra is not None:
            extra.close()

    # Once the held connections release their slots, the server must serve normally again.
    # Closing 5 sockets near-simultaneously can transiently reset a brand-new connection right
    # after (ConnectionResetError) - wait_until() retries past that instead of asserting instantly.
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=15.0,
        poll_interval_s=1.0,
        description="webserver serving normally again after the connection-limit burst cleared",
    )
    # _serve()'s own reject-when-full branch (confirmed directly): "silently close, no accept, no
    # response ever written" - no pr.err_s()/wrn_s() call anywhere on that path, so a real rejection
    # at the connection ceiling is expected to leave WEBSERVER's own error/warning log untouched.
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


# ---------------------------------------------------------------------------
# Nonsense GET/PUT requests over the normal network; test_hotspot_role_reversal.py's check is
# hotspot-only, GET-only and asserts no response shape. None of these mutate persisted config -
# a schema-rejected field is "Invalid" and never reaches write_config().
# ---------------------------------------------------------------------------


def test_get_nonsense_path_is_shaped_404_over_the_normal_network(dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    res = http_client.fetch(dut_ip, 80, "GET", "/this/path/does/not/exist", timeout_s=10.0)
    assert res.status_code == 404, f"GET to a nonsense path did not return 404: {res.status_code} {res.body!r}"
    body = res.json()
    assert body["res"] == "ERR" and body["code"] == 404, f"404 response was not shaped as expected: {body!r}"
    # _shaped_error_handler() (confirmed directly) only ever builds a response - no pr.err_s()/
    # wrn_s() call at all, so a routine 404 must not show up as an error/warning.
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


def test_put_malformed_raw_request_is_rejected_cleanly_over_the_normal_network(dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    # http_client.fetch() can only ever send well-formed JSON (json.dumps()) - genuinely malformed
    # JSON syntax and an oversized body both need a raw socket to actually produce.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(10.0)
        sock.connect((dut_ip, 80))
        body = b"{not valid json"
        request = f"PUT /sensors HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode() + body
        sock.sendall(request)
        response = b""
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
        except TimeoutError:
            pass
    # microdot's send() writes the status line as the literal "HTTP/1.0 {code} {reason}\r\n".
    # Malformed JSON is an application-level error (make_response(1), _body_as_dict()'s
    # contract), so the HTTP status is still 200 rather than a transport-level 4xx.
    assert response.startswith(b"HTTP/1.0 200"), f"malformed JSON PUT did not get a clean HTTP 200 app-level error envelope: {response!r}"
    assert b'"res":"ERR"' in response or b'"res": "ERR"' in response, f"malformed JSON PUT did not produce the expected ERR envelope: {response!r}"

    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after a malformed raw PUT request"
    # _body_as_dict() returning None (confirmed directly) just makes _put_sensors() return
    # ar.make_response(1) - no pr.err_s()/wrn_s() call anywhere on that path either.
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


def test_put_oversized_body_is_rejected_with_413_over_the_normal_network(dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    # max_content_length defaults to 2048 (asy_webserver_service.py) - well past that, on a field
    # name real drivers never register, so nothing here could accidentally validate as real config.
    # Over max_body_length too, now they are bound, so the body is never read (SPECIFICATION I.6).
    oversized = {"BMP3XX": {"Nonsense" + "x" * 5000: 1}}
    res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", oversized, timeout_s=10.0)
    assert res.status_code == 413, f"an oversized PUT body was not rejected with 413: {res.status_code} {res.body!r}"
    # Rejected entirely inside vendored, unmodified ext/microdot.py before this project's own route
    # handler (or its pr) is ever reached - nothing of ours could have logged anything here.
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


# ---------------------------------------------------------------------------
# The request-body cap on real hardware, over real WiFi. tests/test_asy_webserver_service.py's
# F.2b pins "an oversized body is never READ" directly, by counting the readexactly() sizes the
# server asks its reader for. Over the wire that is not observable, so these mirror it on the one
# thing that is: WHO answered. 413 comes from vendored microdot before any handler runs; 200 can
# only come from the handler, which means the body was buffered and dispatched. Full account of
# why both caps had to move together: SPECIFICATION.md Part I.6.
# ---------------------------------------------------------------------------

_BODY_CAP = 2048  # asy_webserver_service.py's max_content_length, now bound to max_body_length too
_OLD_CONTENT_CAP = 4096  # what it was before Part I.6; the 2048..4096 band is the discriminator
_SCHEMA_MAX_BODY = 1312  # largest schema-permitted PUT body, dominated by NTP_Host's 1024 (I.6)


def _sized_sensors_body(total_bytes: int) -> dict[str, dict[str, str]]:
    """A PUT /sensors body of exactly total_bytes, under a sensor key no driver registers.

    Unknown keys are ignored silently, so nothing validates, persists or logs: the size is the
    whole subject, and that is what keeps every test below outside the persistence_write gate."""
    envelope = len(json.dumps({"HWTESTNoSuchSensor": {"Padding": ""}}).encode())
    body = {"HWTESTNoSuchSensor": {"Padding": "x" * (total_bytes - envelope)}}
    assert len(json.dumps(body).encode()) == total_bytes, "padding arithmetic drifted from json.dumps()"
    return body


def _put_sized(dut_ip: str, total_bytes: int, timeout_s: float = 10.0) -> int:
    return http_client.fetch(dut_ip, 80, "PUT", "/sensors", _sized_sensors_body(total_bytes), timeout_s=timeout_s).status_code


def test_put_body_cap_boundary_is_exact_over_the_normal_network(dut_ip: str) -> None:
    # "none above" and "all above" in their sharpest form: one byte apart, on real hardware.
    # microdot's Request.create() compares with <=, so the cap itself must still be served.
    reset_all_error_logs(dut_ip)
    assert _put_sized(dut_ip, _BODY_CAP) == 200, "a body of exactly max_content_length was rejected - the cap must be inclusive"
    assert _put_sized(dut_ip, _BODY_CAP - 1) == 200, "a body one byte under the cap was rejected"
    assert _put_sized(dut_ip, _BODY_CAP + 1) == 413, "a body one byte over the cap was not rejected with 413"
    # A 413 is raised inside vendored microdot before this project's own handler or its pr is
    # reached, so nothing of ours can have logged anything on either side of the boundary.
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


def test_put_the_band_that_used_to_be_accepted_is_now_rejected_over_the_normal_network(dut_ip: str) -> None:
    # The one check that can tell this firmware from the previous one. Before Part I.6 the content
    # cap was 4096 and max_body_length was microdot's own 16 KB, so a 3000 B body was buffered AND
    # accepted; the whole 2048..16384 band was buffered before any 413. Now it is refused unread.
    reset_all_error_logs(dut_ip)
    midband = (_BODY_CAP + _OLD_CONTENT_CAP) // 2
    assert _put_sized(dut_ip, midband) == 413, f"a {midband} B body was not rejected - the old 4096 B content cap looks still in place"
    assert _put_sized(dut_ip, _OLD_CONTENT_CAP) == 413, "a body at the OLD content cap was accepted - this firmware predates Part I.6"
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


def test_the_largest_body_any_schema_can_produce_still_fits_under_the_cap(dut_ip: str) -> None:
    # The direction that matters when a cap is LOWERED: the regression would be refusing something
    # legitimate. 1312 B is the largest body any route's own schema can produce, so a real maximal
    # config push must still be served - 1.56x headroom, derived in tests_scripts/ and asserted here.
    reset_all_error_logs(dut_ip)
    assert _SCHEMA_MAX_BODY < _BODY_CAP, "the schema maximum no longer fits under the cap - Part I.6's premise has moved"
    assert _put_sized(dut_ip, _SCHEMA_MAX_BODY) == 200, f"the largest schema-permitted body ({_SCHEMA_MAX_BODY} B) was rejected"
    # And the real field that dominates that maximum, not just padding. ONE character over
    # _VAL_NH's own 3..1024 bound, so the handler marks it Invalid and nothing is written: at
    # exactly 1024 it is valid, and an accepted NTP_Host is a flash write this test must not own.
    res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"NTP_Host": "z" * 1025}, timeout_s=10.0)
    assert res.status_code == 200, f"a body carrying a maximal NTP_Host was rejected at the TRANSPORT level, which is the cap's doing: {res.status_code} {res.body!r}"
    assert res.json()["result"].get("NTP_Host") == "Invalid", f"a 1025-char NTP_Host was not marked Invalid, so it may have PERSISTED: {res.body!r}"


def test_put_a_mixed_stream_of_body_sizes_is_handled_each_on_its_own_merits(dut_ip: str) -> None:
    # Interleaved, so a rejection cannot leave the next acceptance mis-parsed on a connection the
    # server closed early, and an acceptance cannot let the next oversized one through.
    reset_all_error_logs(dut_ip)
    sizes = [128, _BODY_CAP * 2, 700, _BODY_CAP + 1, _BODY_CAP, 64, _OLD_CONTENT_CAP]
    for size in sizes:
        expected = 200 if size <= _BODY_CAP else 413
        status = _put_sized(dut_ip, size)
        assert status == expected, f"a {size} B body answered {status}, expected {expected}"
    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after a mixed-size PUT stream"
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


# A connection the server refuses at its own ceiling, whose shape src/ does not choose.
# test_connections_at_and_above_the_real_socket_limit_degrade_cleanly above accepts FIN or RST for
# exactly this reason: _serve()'s reject-when-full branch closes without ever writing a response.
_CEILING_CLOSE = (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, http.client.BadStatusLine)


def _is_ceiling_close(exc: BaseException) -> bool:
    # urllib wraps the transport error in URLError.reason; http.client.RemoteDisconnected is a
    # subclass of both ConnectionResetError and BadStatusLine, so it is covered by the tuple.
    return isinstance(exc, _CEILING_CLOSE) or isinstance(getattr(exc, "reason", None), _CEILING_CLOSE)


def test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status(dut_ip: str) -> None:
    """The multi-buffer shape that motivated Part I.6, asserted on what the body cap actually owns.

    max_connections bodies can be in flight at once, so the simultaneous contiguous demand is that
    many buffers - bounded by connections x 2048 now, connections x 16384 while the band was open."""
    reset_all_error_logs(dut_ip)
    # The same settle the connection-ceiling test above takes, and for the same reason: _serve()
    # releases its slot in a finally that runs after _close_writer(), so the PUT just made can
    # still hold one. Without it the workers start against 3 free slots, not 4.
    time.sleep(1.0)
    sizes = [512, _BODY_CAP * 2, _BODY_CAP, _OLD_CONTENT_CAP, 64, _BODY_CAP + 1, 900, _BODY_CAP * 2] * 3
    answered: dict[int, int] = {}
    refused: dict[int, str] = {}
    other: dict[int, str] = {}
    results_lock = threading.Lock()

    def worker(index: int, size: int) -> None:
        try:
            status = _put_sized(dut_ip, size, timeout_s=30.0)
        except Exception as exc:  # the worker's job is to report, never to raise into the harness
            bucket = refused if _is_ceiling_close(exc) else other
            with results_lock:
                bucket[index] = f"{type(exc).__name__}: {exc}"
            return
        with results_lock:
            answered[index] = status

    threads = [threading.Thread(target=worker, args=(i, size)) for i, size in enumerate(sizes)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60.0)
        assert not t.is_alive(), "a worker thread never finished within 60s - possible real deadlock under concurrent mixed-body load"

    # This opens 24 connections against max_connections=4, so most of them are refused at the
    # ceiling by design (queue F10 measured ~25%, at every body size including 64 B). A refusal is
    # not a body-cap result, so it is counted, not failed - but ONLY a refusal.
    assert not other, f"{len(other)} worker(s) failed for a reason that is not the connection ceiling: {dict(list(other.items())[:8])}"
    wrong = {i: answered[i] for i, size in enumerate(sizes) if i in answered and answered[i] != (200 if size <= _BODY_CAP else 413)}
    assert not wrong, f"{len(wrong)} of {len(answered)} answered PUTs got the WRONG status under concurrency: {dict(list(wrong.items())[:8])}"

    # Anti-vacuity, from the server's own documented capacity rather than a measured rate: a run
    # where nearly everything was refused proves nothing about the cap, and one that never saw
    # both verdicts never exercised the boundary it exists to check.
    statuses = list(answered.values())
    assert len(statuses) >= _MAX_CONNECTIONS, f"only {len(statuses)} of {len(sizes)} PUTs were answered at all - too few to say anything about the cap ({len(refused)} refused)"
    assert 200 in statuses and 413 in statuses, f"the run never saw both verdicts, so the cap was never exercised under concurrency: {sorted(set(statuses))}"

    # Still healthy afterwards: a body the server refused to buffer must cost it nothing. The 24
    # workers' slots are still draining through _serve()'s finally, so a single-shot check here is
    # refused at the ceiling - same wait_until() the connection-ceiling test above uses for that lag.
    wait_until(
        lambda: http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200,
        timeout_s=15.0,
        poll_interval_s=1.0,
        description="webserver serving normally again after the concurrent mixed-body load cleared",
    )
    assert_module_error_log_empty(dut_ip, "WEBSERVER")
    print(f"RESULT NOTE: {len(answered)} answered, {len(refused)} refused at the connection ceiling, 0 answered wrongly")


def test_put_nonsense_field_values_are_marked_invalid_not_crashed(dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    # Wrong type, out-of-range, and an entirely unknown sensor key, all in one real REST call -
    # asy_bmp3xx_driver.py's own _VAL_POV only accepts _OSR_SETTINGS=(1,2,4,8,16,32).
    res = http_client.fetch(
        dut_ip,
        80,
        "PUT",
        "/sensors",
        {
            "BMP3XX": {"PressOvers": "banana", "FiltCoeff": 999},
            "TotallyUnknownSensor": {"Whatever": 1},
        },
        timeout_s=10.0,
    )
    assert res.status_code == 200, f"a syntactically valid but nonsensical PUT body crashed the request instead of being marked Invalid: {res.status_code} {res.body!r}"
    body = res.json()
    bmp_result = body["result"].get("BMP3XX", {})
    assert bmp_result.get("PressOvers") == "Invalid", f"a wrong-typed field was not marked Invalid: {bmp_result!r}"
    assert bmp_result.get("FiltCoeff") == "Invalid", f"an out-of-range field was not marked Invalid: {bmp_result!r}"
    assert "TotallyUnknownSensor" not in body["result"], f"an entirely unknown sensor key was not silently ignored: {body['result']!r}"

    # Nothing above should have changed anything real - confirm the server is still fully healthy.
    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after nonsense PUT field values"

    # A rejected key logs errno=12 on its own separate "CFGMGR_<NAME>" logger, not "BMP3XX" itself
    # (config_manager.py's write_config()) - in-RAM only, but still real and REST-visible.
    try:
        errcount = get_errcount(dut_ip)
        cfgmgr_entry = errcount.get("CFGMGR_BMP3XX", {})
        assert cfgmgr_entry.get("counter") == 2, f"expected exactly 2 type/range validation errors on CFGMGR_BMP3XX (one per rejected field), got: {cfgmgr_entry!r}"
        assert_module_error_log_contains(dut_ip, "CFGMGR_BMP3XX", 12, "E")
    finally:
        reset_all_error_logs(dut_ip)


# ---------------------------------------------------------------------------
# Stale/slowloris-paced/abruptly-broken connections. _serve()'s outer asyncio.wait_for(...,
# outer_cap_s=15.0) is what bounds a Slowloris-paced client that never completes its request.
# ---------------------------------------------------------------------------


def test_slowloris_style_partial_request_is_reclaimed_by_the_outer_timeout(dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(30.0)  # generous relative to production's own outer_cap_s=15.0
        sock.connect((dut_ip, 80))
        sock.sendall(b"GET /status HTTP/1.1\r\nHost: x\r\n")
        # A real Slowloris pace, not one long stall: _TimeoutStreamProxy gives each readline()
        # its own per_call_timeout_s=5.0. One header line every 3s keeps each call under that
        # while the 18s total passes outer_cap_s=15.0, which is the timeout under test.
        try:
            for i in range(6):
                sock.sendall(f"X-Pad-{i}: 1\r\n".encode())
                time.sleep(3.0)
        except OSError:
            pass  # the server may have already closed the connection once the outer cap fired
        try:
            response = sock.recv(4096)
        except OSError:
            response = b""
    assert response == b"", f"a genuinely Slowloris-paced request (no single stall over 5s, 18s cumulative) was not reclaimed by the outer timeout: {response!r}"

    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after a slowloris-style trickle-fed request"
    # _serve()'s outer wait_for(outer_cap_s) timeout logs wrnno=2 - this test's pacing avoids ever
    # triggering the (also wrnno=2) per-call timeout path instead, so the wrnno is unambiguous here.
    try:
        assert_module_error_log_contains(dut_ip, "WEBSERVER", 2, "W")
    finally:
        reset_all_error_logs(dut_ip)


def test_abrupt_disconnect_mid_response_does_not_hang_the_server(dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0)
    sock.connect((dut_ip, 80))
    sock.sendall(b"GET /measurements HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
    sock.recv(1)  # read exactly one byte of the response, then abandon the connection entirely
    sock.close()  # a real client vanishing mid-response (SO_LINGER default: a plain RST/FIN, not a clean shutdown)

    # The server must still be healthy for the *next* client - an fd/task leak from the abandoned
    # connection above would otherwise only surface as a slow, cumulative degradation over many
    # such events, not an immediate, obvious failure of this one check alone.
    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after a client disconnected abruptly mid-response"
    # No hard assertion on WEBSERVER's error log: whether the server is still mid-write when this
    # RST lands (wrnno=3) is a genuine timing race, not deterministic - asserting either way risks flakiness.
    reset_all_error_logs(dut_ip)  # hygiene regardless of which way the race went
