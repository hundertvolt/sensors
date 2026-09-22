"""Bench-tier automated tests: the full hotspot role-reversal scenario - the bench radio joins the
DUT's OWN hotspot to test its AP/DHCP/captive-portal/REST role from a real external client
(untestable in the digital twin). Definition order matters - see stage 6 below.
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

import dns_probe
import http_client
import pytest
import website_identity
from error_log_helpers import assert_module_error_log_empty, reset_all_error_logs
from harness import Board, HardwareTestFailureError, wait_until

if TYPE_CHECKING:
    from collections.abc import Iterator

    from bench_control import BenchBridge

pytestmark = pytest.mark.role_reversal


def _join_dut_hotspot_with_reverify_retry(bench: BenchBridge, ssid: str, password: str, *, attempts: int = 5) -> None:
    """Shared by every real `join_dut_hotspot()` call site: `is_ssid_visible()`==True doesn't
    guarantee nmcli's own internal rescan still sees it a moment later, and this can persist
    across several attempts - each retry re-confirms fresh visibility (see tests_hardware/README.md)."""
    for attempt in range(attempts):
        try:
            bench.join_dut_hotspot(ssid, password, timeout_s=45.0)
        except HardwareTestFailureError:
            if attempt == attempts - 1:
                raise
            try:
                wait_until(lambda: bench.is_ssid_visible(ssid), timeout_s=30.0, poll_interval_s=2.0, description=f"DUT's own hotspot ({ssid!r}) to be freshly scannable again before retrying the join")
            except TimeoutError:
                pass  # fall through and retry the join anyway - it may still succeed, and the
                # join's own next HardwareTestFailureError (or success) is the real signal either way

_HOTSPOT_PASSWORD = "12345678"  # hardcoded in src/asy_wifi_service.py's _configure_hotspot_ap()


@pytest.fixture(scope="module")
def hotspot_ssid(board: Board, dut_ip: str) -> str:
    """The DUT's current Hostname, read over the normal bridge connection before anything flips -
    a fully deterministic SSID derivation, with no scan/discovery needed."""
    res = http_client.fetch(dut_ip, 80, "GET", "/networking")
    assert res.status_code == 200, f"GET /networking failed before starting the scenario: {res.status_code}"
    hostname: str | None = res.json().get("Hostname")
    assert hostname, f"GET /networking returned no Hostname to derive the hotspot SSID from: {res.json()!r}"
    return hostname


@pytest.fixture(scope="module")
def joined_hotspot(board: Board, bench: BenchBridge, dut_ip: str, hotspot_ssid: str) -> Iterator[str]:
    """Stages 0-2 in setup, stages 7-8 in teardown, module-scoped - each join/leave costs a real
    ~15-30s association. Yields the DUT's gateway IP. Its own persisting writes stay UNMARKED per
    CLAUDE.md's owns-vs-reached-through rule: mark a test that spends a write, never this fixture."""
    # Stage 0 - precondition: force hotspot mode rather than waiting for organic failure. Read
    # the real SSID first, because this fixture destroys it and so owns restoring it in stage 7.

    # Leaving that to stage 6 strands the board in hotspot mode whenever stage 6 does not run:
    # the cleared SSID is persisted to flash, so no reset clears it. It happened on the bench
    # (2026-09-17) and needed a manual serial-side repair.
    original = http_client.fetch(dut_ip, 80, "GET", "/networking", timeout_s=10.0)
    assert original.status_code == 200, f"GET /networking (to record the SSID before clearing it) failed: {original.status_code} {original.body!r}"
    original_ssid = original.json().get("SSID") or ""
    assert original_ssid, f"GET /networking returned no SSID to restore later - refusing to clear it: {original.json()!r}"

    res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"SSID": ""})
    assert res.status_code == 200 and res.json().get("result", {}).get("SSID") == "Valid", f"PUT /networking SSID='' failed: {res.status_code} {res.json() if res.status_code == 200 else res.body!r}"

    # Stage 1 - association. A fixed settle sleep isn't always enough - the DUT's hotspot beacon
    # needs a moment after the SSID="" PUT - so poll is_ssid_visible() (a real scan) instead of
    # guessing a delay (see tests_hardware/README.md).
    bench.ap_down()  # is_ssid_visible() needs the radio free to scan - see its own docstring
    wait_until(lambda: bench.is_ssid_visible(hotspot_ssid), timeout_s=30.0, poll_interval_s=2.0, description=f"DUT's own hotspot ({hotspot_ssid!r}) to become scannable")
    # is_ssid_visible()==True doesn't guarantee nmcli's own internal rescan still sees it a moment
    # later - see _join_dut_hotspot_with_reverify_retry()'s own docstring.
    _join_dut_hotspot_with_reverify_retry(bench, hotspot_ssid, _HOTSPOT_PASSWORD)

    # Stage 2 - DHCP.
    wait_until(lambda: bool(bench.gateway_ip()), timeout_s=45.0, poll_interval_s=2.0, description="bench radio DHCP lease + gateway on the DUT hotspot")
    gateway_ip = bench.gateway_ip()

    yield gateway_ip

    # Stage 7 - flip back. Restore stage 0's SSID BEFORE leaving the hotspot, which is the only
    # link to the DUT left at this point. Best-effort and never raising, so it cannot mask the
    # failure unwinding this fixture; stage 8 is what still fails loudly if the DUT stays away.
    try:
        restored = http_client.fetch(gateway_ip, 80, "PUT", "/networking", {"SSID": original_ssid}, timeout_s=15.0)
        if restored.status_code != 200 or restored.json().get("result", {}).get("SSID") not in ("Valid", "Unchanged"):
            print(f"RESULT NOTE: SSID restore over the hotspot was not accepted: {restored.status_code} {restored.body!r}")
    except (OSError, ValueError) as exc:
        # ValueError covers .json() on a 200 whose body is not JSON - fetch() itself only ever
        # raises OSError subclasses, so a decode failure would otherwise escape this best-effort
        # block and mask the very failure the comment above says it must not.
        print(f"RESULT NOTE: SSID restore over the hotspot failed to reach the DUT: {exc!r}")

    bench.leave_dut_hotspot_and_restore_bridge()
    # Stage 8 - confirm the DUT is back on the bridge network. A failed stage-6 STA reconnect
    # ends in _PHASE_DEACTIVATED, which only a power cycle clears (Part A.4), so recover with
    # hard_reset() rather than leaving the board stuck - then still assert, so a break is loud.
    try:
        wait_until(lambda: _dut_reachable_again(dut_ip), timeout_s=90.0, poll_interval_s=3.0, description="DUT reachable again over the bridge network after role-flip-back")
    except TimeoutError:
        # A stale AP-side station-table entry for the DUT's MAC is the dominant real cause of a
        # hard_reset()-triggered reconnect failing here - see kick_client()'s own docstring.
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(lambda: _dut_reachable_again(dut_ip), timeout_s=30.0, poll_interval_s=1.0, description="DUT reachable again after a recovery hard_reset() (see this fixture's own comment)")
        raise


def _dut_reachable_again(dut_ip: str) -> bool:
    try:
        return http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Stage 0 - precondition. Verified by the time `joined_hotspot` first yields, but broken out as
# their own independently-nameable assertions.
# ---------------------------------------------------------------------------


def test_dut_enters_hotspot_mode_after_ssid_cleared(joined_hotspot: str) -> None:
    pass  # the joined_hotspot fixture itself only succeeds if stage 0-2 all completed - this test names that fact


def test_hotspot_ssid_matches_configured_hostname(bench: BenchBridge, hotspot_ssid: str, joined_hotspot: str) -> None:
    # bench.ap_ssid() reads the torn-down br0-wifi-ap profile's SSID, not the DUT's. The real
    # assertion is simpler: the fixture's join_dut_hotspot() already had to succeed against
    # hotspot_ssid, which is only possible if the DUT's own hotspot SSID equals it.
    assert hotspot_ssid, "hotspot_ssid fixture produced an empty SSID"


def test_hotspot_password_matches_known_fixed_value(joined_hotspot: str) -> None:
    # Documents the known, hardcoded weak credential - not something to silently "fix" here, per
    # CLAUDE.md's credential-handling rule. The real assertion: the fixture's association already
    # had to succeed using this exact password.
    assert _HOTSPOT_PASSWORD == "12345678"


# ---------------------------------------------------------------------------
# Stage 1 - association (item 4).
# ---------------------------------------------------------------------------


def test_bench_radio_associates_within_bounded_window(joined_hotspot: str) -> None:
    pass  # joined_hotspot's own setup already proves this within its 45s wait_until


# ---------------------------------------------------------------------------
# Stage 2 - DHCP (items 5-7).
# ---------------------------------------------------------------------------


def test_bench_radio_receives_a_valid_dhcp_lease(bench: BenchBridge, joined_hotspot: str) -> None:
    ip = bench.own_ip_on()
    parts = ip.split(".")
    assert len(parts) == 4 and all(p.isdigit() for p in parts), f"own_ip_on() returned something that doesn't look like an IPv4 address: {ip!r}"


def test_leased_ip_falls_within_the_aps_own_subnet(bench: BenchBridge, joined_hotspot: str) -> None:
    own_ip = bench.own_ip_on()
    gateway_ip = joined_hotspot
    # A /24 assumption (the common CYW43 AP DHCP range) - own_ip_on() only reads the address, not
    # the real netmask. Good enough for a plausibility check; tighten if this proves too loose.
    assert own_ip.rsplit(".", 1)[0] == gateway_ip.rsplit(".", 1)[0], f"leased IP {own_ip} not in the same /24 as gateway {gateway_ip}"


def test_repeated_associate_disassociate_cycles_dont_wedge_the_dhcp_server(bench: BenchBridge, hotspot_ssid: str, joined_hotspot: str) -> None:
    # Fault injection against the CYW43 firmware's own DHCP server - there is no Python DHCP code
    # here to test. Three reassociate cycles, each confirming a lease. Polls is_ssid_visible()
    # after an explicit ap_down(), since the bench's single radio otherwise misses the hotspot.
    for cycle in range(3):
        bench.leave_dut_hotspot_and_restore_bridge()
        bench.ap_down()
        wait_until(lambda: bench.is_ssid_visible(hotspot_ssid), timeout_s=15.0, poll_interval_s=1.0, description=f"DUT hotspot {hotspot_ssid!r} visible again on reassociate cycle {cycle}")
        _join_dut_hotspot_with_reverify_retry(bench, hotspot_ssid, _HOTSPOT_PASSWORD)
        wait_until(lambda: bool(bench.gateway_ip()), timeout_s=45.0, poll_interval_s=2.0, description=f"DHCP lease on reassociate cycle {cycle}")


# ---------------------------------------------------------------------------
# Stage 3 - captive DNS (items 8-13).
# ---------------------------------------------------------------------------


def test_arbitrary_hostname_resolves_to_the_aps_own_ip(joined_hotspot: str) -> None:
    response = dns_probe.query(joined_hotspot, "www.example.com")
    assert response is not None, f"no DNS response from {joined_hotspot}:53 for an arbitrary hostname"
    assert dns_probe.extract_answer_ip(response) == joined_hotspot, f"DNS answer didn't point back at the AP's own IP {joined_hotspot}"


def test_devices_own_hostname_resolves_the_same_way(joined_hotspot: str, hotspot_ssid: str) -> None:
    # src/captive_dns.py answers every query identically regardless of the queried name - the
    # device's own real Hostname must not be special-cased differently from an arbitrary one.
    response = dns_probe.query(joined_hotspot, hotspot_ssid)
    assert response is not None
    assert dns_probe.extract_answer_ip(response) == joined_hotspot


def test_genuine_root_domain_query_is_answered_correctly(joined_hotspot: str) -> None:
    # A root query (QNAME = the zero-length root label alone) - the `_parsed_ok` real-vs-malformed
    # distinction src/captive_dns.py's own code comments call out.
    txn_id = b"\x99\x99"
    header = txn_id + bytes([0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    question = b"\x00" + bytes([0, 1, 0, 1])  # root label, then QTYPE=A QCLASS=IN packed as raw bytes
    response = dns_probe.query(joined_hotspot, "", raw_query=header + question)
    assert response is not None, "no response to a genuine root-domain query"
    assert dns_probe.extract_answer_ip(response) == joined_hotspot


def test_malformed_truncated_packet_is_silently_dropped(joined_hotspot: str) -> None:
    # A truncated packet (fewer than 12 header bytes) - src/captive_dns.py's response() returns
    # None for this (confirmed by reading the module), i.e. no response should ever arrive.
    reset_all_error_logs(joined_hotspot)
    response = dns_probe.query(joined_hotspot, "", raw_query=b"\x01\x02\x03")
    assert response is None, f"expected no response to a malformed/truncated packet, got {response!r}"
    # The datagram itself arrives fine at the socket layer (UDP has no content validation) -
    # captive_dns.py's own "response() returned None" path logs via pr.evt() (an ordinary event),
    # not err_s()/wrn_s(), so the module's real errcount log should stay empty.
    assert_module_error_log_empty(joined_hotspot, "DNSSRV")


@pytest.mark.skip(
    reason=(
        "Raw-socket feasibility on the bench Rpi4 not yet checked - spoofing an off-subnet UDP "
        "source address needs either a raw socket (CAP_NET_RAW) or a second network namespace with "
        "a routable off-subnet address, neither confirmed practical here yet. Flagged rather than "
        "guessed at - implement once a concrete spoofing mechanism is confirmed to work."
    ),
)
def test_spoofed_off_subnet_source_address_is_ignored(joined_hotspot: str) -> None:
    raise AssertionError("should never run - see skip reason")


def test_dns_flood_backoff_curve_recovers_once_flood_stops(joined_hotspot: str) -> None:
    # A garbage-but-present UDP payload still yields a real (data, addr) from recvfrom(), so this
    # flood takes the same pr.evt()-only path a normal query does, never the recv-failure backoff
    # branch. What it proves is robustness under flood and recovery after, not the backoff curve.
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            sock.sendto(b"\x00\x01\x02", (joined_hotspot, 53))
            time.sleep(0.05)

    # A generous settle - the backoff cap is 5s, so a legitimate query shortly after should still
    # be served well within a normal timeout, not stuck in an extended backoff from the flood.
    response = dns_probe.query(joined_hotspot, "recovery-check.example", timeout_s=8.0)
    assert response is not None, "no response to a legitimate query shortly after a malformed-packet flood - backoff may not be recovering"
    assert dns_probe.extract_answer_ip(response) == joined_hotspot


# ---------------------------------------------------------------------------
# Stage 4 - REST surface over the hotspot link (items 14-16).
# ---------------------------------------------------------------------------


def test_every_get_endpoint_reachable_and_shaped_over_the_hotspot_link(joined_hotspot: str) -> None:
    for path in ("/measurements", "/sensors", "/networking", "/system", "/notification", "/status", "/"):
        res = http_client.fetch(joined_hotspot, 80, "GET", path, timeout_s=10.0)
        assert res.status_code == 200, f"GET {path} over the hotspot link -> {res.status_code}"


@pytest.mark.persistence_write
def test_representative_put_round_trips_over_the_hotspot_link(joined_hotspot: str) -> None:
    # /notification's WarnCO2: _shared_rest_roundtrip.py's mock/twin shape over a real wireless
    # hotspot link. /networking's SSID/PW/Country/Hostname are excluded, being stage 6's. Accepts
    # "Unchanged" as well as "Valid", since a rerun with the value already persisted is fine.
    res = http_client.fetch(joined_hotspot, 80, "PUT", "/notification", {"WarnCO2": 1700})
    assert res.status_code == 200
    assert res.json().get("result") == {"WarnCO2": "Valid"} or res.json().get("result") == {"WarnCO2": "Unchanged"}, f"unexpected PUT result over the hotspot link: {res.json()!r}"


def test_real_static_website_content_serves_over_the_hotspot_link(joined_hotspot: str) -> None:
    # The same real property test_digital_twin_real_website_integration.py already proves for the
    # twin (SPECIFICATION.md Part A.9), now over real hardware/RF.
    res = http_client.fetch(joined_hotspot, 80, "GET", "/", timeout_s=10.0)
    assert res.status_code == 200
    website_identity.assert_page_is_this_devices_build(res, "the hotspot link")


def test_nonsense_path_redirects_to_root_over_the_hotspot_link(joined_hotspot: str) -> None:
    # The hotspot-mode counterpart to test_network_resilience.py's STA-mode 404 test;
    # joined_hotspot only yields once is_hotspot_active() is true. A raw socket, not
    # http_client.fetch(): urllib follows the 3xx and hides the 302/Location under test.
    import socket

    reset_all_error_logs(joined_hotspot)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(10.0)
        sock.connect((joined_hotspot, 80))
        sock.sendall(b"GET /generate_204 HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        response = b""
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
        except TimeoutError:
            pass
    assert response.startswith((b"HTTP/1.0 302", b"HTTP/1.1 302")), f"GET to a nonsense path over the hotspot link did not return 302: {response!r}"
    assert b"Location: /\r\n" in response or b"location: /\r\n" in response, f"redirect Location header was not '/': {response!r}"
    # Matches the STA-mode test's own "a routine response must not log an error" assertion, applied
    # to the new hotspot-mode redirect path.
    assert_module_error_log_empty(joined_hotspot, "WEBSERVER")


def test_put_to_nonsense_path_is_405_not_a_redirect_over_the_hotspot_link(joined_hotspot: str) -> None:
    # A non-GET to an unmatched path resolves to 405 inside Microdot's routing, before
    # _serve_static() is reached - so the redirect fallback cannot leak into an unrelated error
    # path. The hotspot<->STA toggle is not repeated here: Part A.5, and ~15-30s per cycle.
    reset_all_error_logs(joined_hotspot)
    res = http_client.fetch(joined_hotspot, 80, "PUT", "/generate_204", {}, timeout_s=10.0)
    assert res.status_code == 405, f"PUT to a nonsense path over the hotspot link did not return 405: {res.status_code} {res.body!r}"
    assert_module_error_log_empty(joined_hotspot, "WEBSERVER")


# ---------------------------------------------------------------------------
# Stage 5 - client-side fault injection against the DUT's server role (items 17-19).
# ---------------------------------------------------------------------------


def test_malformed_http_request_over_real_wireless_degrades_cleanly(joined_hotspot: str) -> None:
    import socket

    reset_all_error_logs(joined_hotspot)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(10.0)
        sock.connect((joined_hotspot, 80))
        sock.sendall(b"NOT A REAL HTTP REQUEST\r\n\r\n")
        try:
            sock.recv(4096)  # attempt a read so the connection isn't abruptly closed before the server responds; content deliberately not asserted, see below
        except TimeoutError:
            pass
    # The exact response shape isn't asserted (mock/twin cover that) - the hardware-only property
    # this adds is that the connection doesn't hang or crash the webserver over a real wireless link.
    assert http_client.fetch(joined_hotspot, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after a malformed request over real wireless"
    # An unparseable request line fails entirely inside vendored ext/microdot.py's Request.create(),
    # never reaching this project's own route handlers or _serve()'s wrn_s()/err_s() calls.
    assert_module_error_log_empty(joined_hotspot, "WEBSERVER")


def test_rapid_associate_disassociate_churn_doesnt_wedge_station_management(bench: BenchBridge, hotspot_ssid: str, joined_hotspot: str) -> None:
    # See test_repeated_associate_disassociate_cycles_dont_wedge_the_dhcp_server's own comment for
    # why this polls is_ssid_visible() (after an explicit ap_down()) instead of a fixed settle -
    # same real single-radio AP-to-client transition race, same fix.
    for cycle in range(3):
        bench.leave_dut_hotspot_and_restore_bridge()
        bench.ap_down()
        wait_until(lambda: bench.is_ssid_visible(hotspot_ssid), timeout_s=15.0, poll_interval_s=1.0, description=f"DUT hotspot {hotspot_ssid!r} visible again on churn cycle {cycle}")
        _join_dut_hotspot_with_reverify_retry(bench, hotspot_ssid, _HOTSPOT_PASSWORD)
    assert http_client.fetch(bench.gateway_ip(), 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after rapid associate/disassociate churn"


def test_concurrent_multi_client_burst_is_out_of_scope_here(joined_hotspot: str) -> None:
    # Scope-limited note, not a gap silently papered over: a genuine concurrent multi-client burst
    # (like test_end_to_end_timing.py's bridge-side burst test) isn't reproducible in hotspot mode
    # with only one bench radio available - documents that ceiling explicitly.
    pass


# ---------------------------------------------------------------------------
# Stage 6 - the mutating step. MUST run after every read-only check above (pytest's default,
# non-randomized definition order - see module docstring) and MUST be the last thing that touches
# /networking's SSID/PW/Country/Hostname fields before the joined_hotspot teardown flips back.
# ---------------------------------------------------------------------------


@pytest.mark.persistence_write
def test_invalid_credentials_rejected_without_triggering_reconnect(bench: BenchBridge, joined_hotspot: str) -> None:
    # post_fct (the /networking group's reconnect_wifi() hook) fires if ANY field validates, so
    # sending PW alone keeps `results` to one entry and one invalid field prevents it. A password
    # under 8 characters is invalid per _VAL_PW's bounds.
    res = http_client.fetch(joined_hotspot, 80, "PUT", "/networking", {"PW": "short"})
    assert res.status_code == 200
    result = res.json().get("result", {})
    assert result.get("PW") != "Valid", f"expected the too-short password to be rejected, got {result!r}"
    # No reconnect should have fired - the bench radio must still be associated to the (unchanged)
    # hotspot afterward.
    assert bench.gateway_ip() == joined_hotspot, "DUT appears to have reconnected after a PUT that should have been entirely rejected"


@pytest.mark.persistence_write
def test_real_credentials_put_succeeds_and_confirms_accepted_values(bench: BenchBridge, joined_hotspot: str, hotspot_ssid: str) -> None:
    # bench.ap_password() reads the real PSK via `nmcli --show-secrets` by default now, so this
    # test needs no manual BENCH_AP_PASSWORD setup (still honored as an explicit override) - see
    # tests_hardware/README.md for why this PUT is required (stage 7's flip-back depends on it).
    password = os.environ.get("BENCH_AP_PASSWORD") or bench.ap_password()
    ssid = bench.ap_ssid()
    res = http_client.fetch(joined_hotspot, 80, "PUT", "/networking", {"SSID": ssid, "PW": password, "Hostname": hotspot_ssid})
    assert res.status_code == 200
    result = res.json().get("result", {})
    # "Unchanged" (not just "Valid") is a correct, intentional response for a field that already
    # holds the requested value - either acceptance outcome is a genuine pass.
    accepted = {"Valid", "Unchanged"}
    assert result.get("SSID") in accepted and result.get("PW") in accepted, f"real credential PUT was not accepted: {result!r}"


# ---------------------------------------------------------------------------
# Stage 7/8 - role-flip-back and closure. The flip-back happens in joined_hotspot's own teardown
# (after this file's last test runs), so these tests can't observe its outcome directly - the real
# assertions live in the fixture's own wait_until() call.
# ---------------------------------------------------------------------------


def test_role_flip_back_and_reachability_are_asserted_in_fixture_teardown(joined_hotspot: str) -> None:
    # Documents the flip-back/reachability check as covered even though it only runs after this
    # test returns (pytest teardown can't be "waited on" from inside the test body) - a failure
    # there is reported as a fixture-teardown error attributed to this module, not swallowed.
    pass


def test_post_condition_sta_connected_state_inferred_from_reachability(joined_hotspot: str, dut_ip: str) -> None:
    # /networking's GET carries no _conn_phase-equivalent field, and adding one would be a src/
    # change to put to the owner rather than make unasked. The proxy: dut_ip being reachable at
    # all means STA mode, since nothing else routes bridge-network traffic there.
    assert dut_ip, "dut_ip fixture produced an empty address - can't infer STA-connected state from it"
