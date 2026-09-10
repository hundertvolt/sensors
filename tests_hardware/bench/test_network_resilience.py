"""Bench-tier automated tests for real WiFi outage/flap, NTP/DNS servers answering with garbage
(BACKLOG.md open question #5), the webserver's max_connections=4 ceiling, malformed REST requests,
and slowloris/abrupt disconnects - DHCP-client flakiness is deliberately out of scope (see BACKLOG.md).
"""

from __future__ import annotations

import socket
import time
from typing import TYPE_CHECKING

import http_client
import ntp_probe
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
# WiFi outage/flap while already in a real, established STA connection. Per
# src/asy_wifi_service.py's _on_sta_disconnected(), an established-connection disconnect takes the
# safe "retry in 60s" branch - it never increments connection_failures or reaches hotspot
# fallback, confirmed directly before designing these two tests around it.
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

    # REAL FINDING: the CYW43 firmware can appear associated (isconnected()==True, iw showing
    # "associated: yes") while the link is actually dead - neither kick_all_stations() nor
    # _on_sta_disconnected()'s own retry logic reliably clears this (see tests_hardware/README.md
    # for the full evidence; a disclosed architectural gap, not fixed blind here). By project-owner
    # direction, a fallback hard_reset() counts as a genuine pass (CLAUDE.md's WiFi-backstop
    # principle) - which path was actually taken is still recorded via the RESULT NOTE prints below.
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
# Real packet loss/latency/corruption/duplication/reordering (bench_control.py's
# inject_network_degradation()) - perturbs real packets on a real link, unlike the binary
# block/redirect fault injection elsewhere in this file. Parameter ranges are grounded in
# researched real-world WiFi figures, not arbitrary - see tests_hardware/README.md.
# ---------------------------------------------------------------------------


def test_real_operations_survive_and_recover_under_sustained_packet_loss_and_latency(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    bench.inject_network_degradation(loss_pct=30, delay_ms=150, jitter_ms=50)
    try:
        # Under real, sustained 30% loss + 150ms(+/-50ms) latency, any *individual* request may
        # legitimately time out or fail outright - the property under test is that a bounded retry
        # loop still eventually gets through, not that every single request succeeds. 90s is
        # generous relative to a handful of client-side retries at these loss/latency figures.
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


def test_ntp_recovers_via_its_own_retry_timer_after_a_transient_outage_with_no_reboot(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    # Real-hardware form of tests/test_asy_ntp_client.py's retry-after-one-dropped-request test:
    # proves the retry-timer mechanism itself (no reboot) recovers from one transient outage.
    # block_udp_ports() (a guaranteed full block) is used, not netem loss, so the outage reliably
    # outlasts _NTP_CONN_TIMEOUT (5s) while clearing well inside _NTP_RETRY_INTERV (15s).
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
        # Re-triggers a real resync attempt without a reboot - PUT-ing NTP_Host back to its own
        # current value still fires post_asy_fct ("fires if ANY field in this call validated" -
        # already confirmed directly, see test_garbage_ntp_host_via_rest_config_degrades_and_
        # recovers_cleanly's own comment for the full account).
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
# NTP/DNS servers answering with real garbage, not just being unreachable - BACKLOG.md's open
# question #5. test_wifi_networking.py's own test_real_ntp_handles_a_genuinely_unreachable_server_
# without_crashing already covers a *dropped* NTP server (block_udp_ports); these two are its
# "answers, but with garbage" counterpart, redirecting the real port to a local rogue responder
# instead (bench_control.py's redirect_udp_port_to_local(), flagged there as unverified on a first
# real run - see that method's own docstring).
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
    # Checked via the live tail_log text, not the REST errcount history, which is a fixed
    # 10-entry rolling window that a full 90s of garbage responses evicts (see
    # tests_hardware/README.md). Checks for "Invalid NTP time received!" specifically because it
    # fires for either real rejection branch this 63-byte payload can hit (errno=14 or 15) -
    # payload-shape-independent, not pinned to which branch this particular payload happens to hit.
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
# Connected-socket source-address filtering (BACKLOG.md open question #5) - the garbage-response
# tests above never actually exercise this, since DNAT+conntrack rewrites the reply's source back
# to the real server before the DUT sees it. This test instead captures the DUT's real ephemeral
# source port via tcpdump (see bench_control.start_udp_source_capture()) and sends a spoofed reply
# straight at it from this host's own real IP, with the DUT's real request left alone - no
# IP spoofing/raw sockets needed, since the DUT is this plain sendto()'s real destination.
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
# A config-level NTP fault, not a network-level one: PUT a garbage NTP_Host over REST on an
# already-connected link, confirm the resulting DNS failure degrades cleanly, then restore and
# confirm recovery. Unlike the DNS/NTP tests above (which force a fresh boot with an already-bad
# server), this starts already-synced, exercising the previously-untested re-sync-failure branch
# of `_handle_ntp_sync_failure()`'s `if await self.ntp_issynced():` guard.
# ---------------------------------------------------------------------------

# RFC 2606 reserves .invalid specifically so it can never resolve to a real address - a genuine,
# permanent DNS-resolution failure, not a flaky "might resolve to something on some networks" guess.
_GARBAGE_NTP_HOST = "this-host-will-never-resolve.invalid"


def test_garbage_ntp_host_via_rest_config_degrades_and_recovers_cleanly(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    get_before = http_client.fetch(dut_ip, 80, "GET", "/networking", timeout_s=10.0)
    assert get_before.status_code == 200, f"GET /networking failed: {get_before.status_code} {get_before.body!r}"
    original_host = get_before.json()["NTP_Host"]

    try:
        reset_all_error_logs(dut_ip)
        put_res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"NTP_Host": _GARBAGE_NTP_HOST}, timeout_s=10.0)
        assert put_res.status_code == 200, f"PUT /networking NTP_Host={_GARBAGE_NTP_HOST!r} failed: {put_res.status_code} {put_res.body!r}"
        # _VAL_NH's own schema (asy_ntp_client.py) only bounds string length (3-1024) - it has no
        # hostname-format validation, so a syntactically-garbage-but-length-valid host is accepted
        # as "Valid" here; the real failure only surfaces later, from the actual DNS resolution
        # attempt ntp_force_sync() (this field's own post_asy_fct) triggers.
        assert put_res.json()["result"].get("NTP_Host") == "Valid", f"garbage NTP_Host was rejected at the schema level, not what this test means to exercise: {put_res.json()!r}"

        # post_asy_fct fires the real resync asynchronously - poll for the real DNS-resolution
        # failure to land (asy_ntp_client.py's own _resolve_ntp_server(): resolve_ipv4() failing
        # logs "No valid NTP server:", errno=12 - the same real code path/errno the network-level
        # DNS-garbage-response test above exercises, just reached via a bad hostname instead of a
        # bad response).
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
        assert restore_res.json()["result"].get("NTP_Host") == "Valid", f"restoring the original NTP_Host was rejected: {restore_res.json()!r}"

    # Recovery: the next forced resync (post_asy_fct fires on this restore PUT too) must actually
    # succeed - checked via NtpSynced under GET /status's nested "networking" object, not
    # GET /networking (config schema only, no NtpSynced field - see tests_hardware/README.md for
    # the since-fixed test bug this replaced, the same category as the "Mode" field fix below).
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
# A real-format SSID that no AP on this bench broadcasts - _VAL_SSID's schema only bounds length
# (0-32 chars), same gap as NTP_Host above. Aims to stay short of the ~50s hotspot-fallback
# transition (dut_ip stops being reachable once the DUT switches to AP mode), but real timing
# jitter can blow that budget - if it does, this test falls back to joining the DUT's own hotspot
# (test_hotspot_role_reversal.py's mechanism), matching this tier's "a recovery path is a pass" convention.
# ---------------------------------------------------------------------------

_GARBAGE_SSID = "wozi-test-net-does-not-exist"  # <=32 chars (_VAL_SSID's own cap) - real 2.4GHz-legal SSID format/length, just not broadcast by anything on this bench
_HOTSPOT_PASSWORD = "12345678"  # hardcoded in src/asy_wifi_service.py's _configure_hotspot_ap()


def test_garbage_ssid_via_rest_config_is_handled_gracefully(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    get_before = http_client.fetch(dut_ip, 80, "GET", "/networking", timeout_s=10.0)
    assert get_before.status_code == 200, f"GET /networking failed: {get_before.status_code} {get_before.body!r}"
    original_ssid = get_before.json()["SSID"]
    original_hostname = get_before.json()["Hostname"]

    reset_all_error_logs(dut_ip)
    put_res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"SSID": _GARBAGE_SSID}, timeout_s=10.0)
    assert put_res.status_code == 200, f"PUT /networking SSID={_GARBAGE_SSID!r} failed: {put_res.status_code} {put_res.body!r}"
    # Length/type-only schema (see this test's own module comment above) - accepted as "Valid"
    # here; the real failure only surfaces later, from the actual (real, over-the-air) connect
    # attempt asy_wifi_service.py's own reconnect_wifi() post_fct triggers.
    assert put_res.json()["result"].get("SSID") == "Valid", f"garbage SSID was rejected at the schema level, not what this test means to exercise: {put_res.json()!r}"

    # Passive observation only (no exec()/is_reachable() - see harness.py's own findings on why
    # polling those against a live system is disruptive): confirm at least one real STAT_NO_AP_FOUND
    # cycle is logged and handled cleanly - a short window, to leave margin against the hotspot-
    # fallback budget above.
    lines = board.tail_log(duration_s=15.0)
    joined = "\n".join(lines)
    assert "Traceback" not in joined, f"a real unreachable SSID crashed the system instead of degrading cleanly:\n{joined}"
    assert "WLAN access point not found" in joined, f"no real STAT_NO_AP_FOUND cycle observed for a genuinely nonexistent SSID:\n{joined}"

    # dut_ip (the bench-bridge-DHCP-assigned address) cannot become reachable again while the
    # garbage SSID is still configured - a real reconnect to it is impossible by construction, not
    # just unlikely - so a plain snapshot check here is a correct (not racy) way to decide the DUT
    # has necessarily started its real connection_failures streak toward hotspot fallback.
    if http_client_is_ok(dut_ip):
        # Happy path: still reachable over the normal bridge network - restore directly. Not
        # actually expected to trigger (see comment above), kept only as a defensive fallback.
        bench.kick_all_stations()  # the coming reconnect is a genuine machine-level association - see conftest.py's dut_ip docstring
        _restore_ssid_over(dut_ip, original_ssid)
    else:
        # Fallback: join the DUT's own AP once it reaches real hotspot fallback, to restore over
        # that instead (like test_hotspot_role_reversal.py's joined_hotspot fixture). Polls
        # is_ssid_visible() with a generous budget rather than a fixed delay, since this path
        # reaches hotspot mode indirectly with no "moment zero" to sleep a margin after (see
        # tests_hardware/README.md). ap_down() through join_dut_hotspot() stays inside this same
        # try/finally so a timeout here can't strand the bridge AP down.
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

    # "Mode" is a field of GET /status's nested "networking" object, not GET /networking (config
    # schema only) - a since-fixed test bug that made this check structurally unable to pass
    # regardless of real DUT health (see tests_hardware/README.md for the full account, including
    # the other, real mechanisms this was originally misattributed to).
    def _reconnected_over_bridge() -> bool:
        return http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).json()["networking"].get("Mode") == "STA"

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
# The real webserver connection ceiling (max_connections=4, one slot below lwIP's
# MEMP_NUM_TCP_PCB=5) actually degrades cleanly at and above the limit - unlike
# test_end_to_end_timing.py's light-concurrency burst test, which never holds enough slots open at
# once. _open_conns increments the instant a TCP connection is accepted (before any byte is read),
# so a bare connect() with nothing sent already occupies a real slot.
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
        # A completed TCP connect() doesn't mean the RP2040's own accept loop has run _serve() and
        # incremented _open_conns yet - can lag under real load, occasionally admitting the "extra"
        # (5th) connection into the app layer instead of rejecting it. A genuine timing race, so a
        # bounded retry with a fresh socket (below) is used, not an ever-larger fixed sleep.
        time.sleep(2.0)

        for attempt in range(3):
            if extra is not None:
                extra.close()
            extra = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            extra.settimeout(10.0)
            # A bare connect() can still succeed at the TCP/kernel level (the accept queue) even
            # though the real server-side _serve() task rejects it as soon as its own task runs -
            # reject-when-full closes the writer without ever composing a response
            # (asy_webserver_service.py's own _serve(): "silently close, no accept, no response
            # ever written").
            extra.connect((dut_ip, 80))
            # REAL FINDING, fixed: a silent reject-when-full close doesn't always surface as a
            # clean FIN (an empty recv()) - confirmed directly: sometimes it's a real RST instead
            # (ConnectionResetError), depending on kernel-level TCP state when the server side
            # closes. Both are the same underlying "closed without ever writing an HTTP response"
            # outcome from the app's own reject-when-full path - src/ doesn't control which one
            # the TCP stack picks, so this test must accept either, not just the FIN/empty-read
            # shape.
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
# Nonsense GET/PUT requests over the *normal* network (the existing check in
# test_hotspot_role_reversal.py is hotspot-mode-only, GET-only, and doesn't assert response shape).
# None of these mutate persisted config: a schema-rejected field is marked "Invalid" and never
# reaches ConfigManager.write_config() (base_classes.py's push-callback gate).
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
    # ext/microdot.py's send() writes the status line as the fixed literal "HTTP/1.0 {code}
    # {reason}\r\n" (confirmed directly) - malformed JSON is an *application*-level error
    # (api_response.make_response(1), asy_webserver_service.py's own _body_as_dict() contract), so
    # the real HTTP status is still 200, not a transport-level 4xx.
    assert response.startswith(b"HTTP/1.0 200"), f"malformed JSON PUT did not get a clean HTTP 200 app-level error envelope: {response!r}"
    assert b'"res":"ERR"' in response or b'"res": "ERR"' in response, f"malformed JSON PUT did not produce the expected ERR envelope: {response!r}"

    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after a malformed raw PUT request"
    # _body_as_dict() returning None (confirmed directly) just makes _put_sensors() return
    # ar.make_response(1) - no pr.err_s()/wrn_s() call anywhere on that path either.
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


def test_put_oversized_body_is_rejected_with_413_over_the_normal_network(dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    # max_content_length defaults to 4096 (asy_webserver_service.py) - well past that, on a field
    # name real drivers never register, so nothing here could accidentally validate as real config.
    oversized = {"BMP3XX": {"Nonsense" + "x" * 5000: 1}}
    res = http_client.fetch(dut_ip, 80, "PUT", "/sensors", oversized, timeout_s=10.0)
    assert res.status_code == 413, f"an oversized PUT body was not rejected with 413: {res.status_code} {res.body!r}"
    # Rejected entirely inside vendored, unmodified ext/microdot.py before this project's own route
    # handler (or its pr) is ever reached - nothing of ours could have logged anything here.
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


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
        # A genuine Slowloris pace, not one long stall: _TimeoutStreamProxy wraps each readline()
        # in its own per_call_timeout_s=5.0, so a single stall over 5s would hit that instead.
        # Trickling one header line every 3s keeps each readline() under 5s while the 18s
        # cumulative total exceeds outer_cap_s=15.0 - reaching the outer timeout specifically.
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
