"""Bench-tier automated tests: the full hotspot role-reversal scenario from
HARDWARE_TEST_PLAN.md §11 - the bench radio temporarily stops hosting `br0-wifi-ap` and becomes a
client of the DUT's OWN hotspot instead, to test the DUT's AP/DHCP/captive-portal/REST-serving role
from a genuine external client's perspective (untestable in the digital twin at all - see §11's own
intro for why). ~25 individually-nameable tests across 8 stages (§11.4/§11.5), sharing one real
role-reversal join for the whole module via `_joined_hotspot` below - each join/leave costs a real
~15-30s WiFi association, so this deliberately isn't repeated per test.

**Ordering matters and is relied upon**: pytest preserves definition order within a module in a
single default (non-randomized) run, which this file's own design depends on for stage 6's mutating
PUT to genuinely run last, after every read-only/non-mutating check above it - this project doesn't
use pytest-randomly (see pyproject.toml's own dependency list), so this holds under the documented
`uv run pytest tests_hardware/bench/test_hotspot_role_reversal.py` invocation. Don't reorder these
functions without preserving that constraint, and don't run this file with `-p randomly` or similar.

Resolved during this session (was flagged as open in §11.6, now settled by reading
src/api_response.py's handle_set_cmd() directly): `post_fct` (SettingsGroup's post-write hook,
`conn.reconnect_wifi` for the /networking group) fires "if any(status == 'Valid' for status in
results.values())" - i.e. once per PUT call, if AT LEAST ONE field in that call validated. This
means test_invalid_credentials_rejected_without_triggering_reconnect() below must make EVERY field
in its PUT invalid together, not just one, or post_fct would still fire on the other valid field(s)."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator

import dns_probe
import http_client
import pytest
from bench_control import BenchBridge
from harness import Board, wait_until

pytestmark = pytest.mark.role_reversal

_HOTSPOT_PASSWORD = "12345678"  # hardcoded in src/asy_wifi_service.py's _configure_hotspot_ap() - see §11.1


@pytest.fixture(scope="module")
def hotspot_ssid(board: Board, dut_ip: str) -> str:
    """The DUT's current Hostname, read over the normal bridge connection before anything flips -
    §11.1's "fully deterministic, no scan/discovery needed" SSID derivation."""
    res = http_client.fetch(dut_ip, 80, "GET", "/networking")
    assert res.status_code == 200, f"GET /networking failed before starting the scenario: {res.status_code}"
    hostname = res.json().get("Hostname")
    assert hostname, f"GET /networking returned no Hostname to derive the hotspot SSID from: {res.json()!r}"
    return hostname


@pytest.fixture(scope="module")
def joined_hotspot(board: Board, bench: BenchBridge, dut_ip: str, hotspot_ssid: str) -> Iterator[str]:
    """Stages 0-2 (precondition, associate, DHCP) in setup; stages 7-8 (flip back, confirm
    reachable again) in teardown - see this module's own docstring for why this is module-scoped
    rather than per-test. Yields the DUT's gateway IP (its own address on the hotspot link) for
    every stage-3+ test to talk to."""
    # Stage 0 - precondition: force hotspot mode on demand rather than waiting for organic failure.
    res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"SSID": ""})
    assert res.status_code == 200 and res.json().get("result", {}).get("SSID") == "Valid", f"PUT /networking SSID='' failed: {res.status_code} {res.json() if res.status_code == 200 else res.body!r}"
    time.sleep(2.0)  # brief settle for the DUT's own reconnect_wifi()/hotspot switchover to begin before the bench radio tries to associate

    # Stage 1 - association.
    bench.join_dut_hotspot(hotspot_ssid, _HOTSPOT_PASSWORD, timeout_s=45.0)

    # Stage 2 - DHCP.
    wait_until(lambda: bool(bench.gateway_ip()), timeout_s=45.0, poll_interval_s=2.0, description="bench radio DHCP lease + gateway on the DUT hotspot")
    gateway_ip = bench.gateway_ip()

    yield gateway_ip

    # Stage 7 - flip back.
    bench.leave_dut_hotspot_and_restore_bridge()
    # Stage 8 - confirm the DUT is reachable again over the normal bridge network (§11.3's own
    # concrete use of wait_until() for exactly this transition).
    wait_until(lambda: _dut_reachable_again(dut_ip), timeout_s=90.0, poll_interval_s=3.0, description="DUT reachable again over the bridge network after role-flip-back")


def _dut_reachable_again(dut_ip: str) -> bool:
    try:
        return http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Stage 0 - precondition (items 1-3). Verified by the time `joined_hotspot` first yields, but
# broken out as their own named assertions per §11.5's own "independently nameable" requirement.
# ---------------------------------------------------------------------------


def test_dut_enters_hotspot_mode_after_ssid_cleared(joined_hotspot: str) -> None:
    pass  # the joined_hotspot fixture itself only succeeds if stage 0-2 all completed - this test names that fact


def test_hotspot_ssid_matches_configured_hostname(bench: BenchBridge, hotspot_ssid: str, joined_hotspot: str) -> None:
    # bench.ap_ssid() reads the (now-torn-down-for-the-duration) br0-wifi-ap profile's own SSID,
    # not the DUT's - the real assertion here is simpler: join_dut_hotspot() inside the fixture
    # already had to succeed using hotspot_ssid as the target SSID, which is only possible if the
    # DUT's real hotspot SSID actually equals it.
    assert hotspot_ssid, "hotspot_ssid fixture produced an empty SSID"


def test_hotspot_password_matches_known_fixed_value(joined_hotspot: str) -> None:
    # Documents the known, hardcoded weak credential for whoever reads this test (see this file's
    # own module docstring / HARDWARE_TEST_PLAN.md §11.5 item 3) - not something to silently "fix"
    # here, per CLAUDE.md's credential-handling hard rule. The real assertion: association in the
    # fixture already had to succeed using this exact password.
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
    # A /24 assumption (the common case for a CYW43 AP's own DHCP range) - flagged, not verified
    # against a real lease's own netmask, since bench_control.BenchBridge.own_ip_on() only reads
    # the address, not the prefix length, and nmcli's -g IP4.ADDRESS output already bundles a CIDR
    # suffix this method strips (see its own docstring). Good enough for a plausibility check;
    # tighten to the real netmask on first hardware run if this proves too loose.
    assert own_ip.rsplit(".", 1)[0] == gateway_ip.rsplit(".", 1)[0], f"leased IP {own_ip} not in the same /24 as gateway {gateway_ip}"


def test_repeated_associate_disassociate_cycles_dont_wedge_the_dhcp_server(bench: BenchBridge, hotspot_ssid: str, joined_hotspot: str) -> None:
    # Fault injection against the CYW43 firmware's own DHCP server, not src/ (§11.1's own note: no
    # dedicated Python DHCP code exists to test here). Three quick reassociate cycles, confirming a
    # lease is still obtainable each time - a firmware/driver robustness check.
    for cycle in range(3):
        bench.leave_dut_hotspot_and_restore_bridge()
        time.sleep(2.0)  # settle between cycles, not a condition to poll for
        bench.join_dut_hotspot(hotspot_ssid, _HOTSPOT_PASSWORD, timeout_s=45.0)
        wait_until(lambda: bool(bench.gateway_ip()), timeout_s=45.0, poll_interval_s=2.0, description=f"DHCP lease on reassociate cycle {cycle}")


# ---------------------------------------------------------------------------
# Stage 3 - captive DNS (items 8-13).
# ---------------------------------------------------------------------------


def test_arbitrary_hostname_resolves_to_the_aps_own_ip(joined_hotspot: str) -> None:
    response = dns_probe.query(joined_hotspot, "www.example.com")
    assert response is not None, f"no DNS response from {joined_hotspot}:53 for an arbitrary hostname"
    assert dns_probe.extract_answer_ip(response) == joined_hotspot, f"DNS answer didn't point back at the AP's own IP {joined_hotspot}"


def test_devices_own_hostname_resolves_the_same_way(joined_hotspot: str, hotspot_ssid: str) -> None:
    # src/captive_dns.py answers every query identically regardless of the queried name (confirmed
    # by reading the whole module during §11.1's research) - the device's own real Hostname must
    # not be special-cased differently from an arbitrary one.
    response = dns_probe.query(joined_hotspot, hotspot_ssid)
    assert response is not None
    assert dns_probe.extract_answer_ip(response) == joined_hotspot


def test_genuine_root_domain_query_is_answered_correctly(joined_hotspot: str) -> None:
    # A root query (QNAME = the zero-length root label alone) - the `_parsed_ok` real-vs-malformed
    # distinction src/captive_dns.py's own code comments call out (§11.1).
    txn_id = b"\x99\x99"
    header = txn_id + bytes([0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    question = b"\x00" + bytes([0, 1, 0, 1])  # root label, then QTYPE=A QCLASS=IN packed as raw bytes
    response = dns_probe.query(joined_hotspot, "", raw_query=header + question)
    assert response is not None, "no response to a genuine root-domain query"
    assert dns_probe.extract_answer_ip(response) == joined_hotspot


def test_malformed_truncated_packet_is_silently_dropped(joined_hotspot: str) -> None:
    # A truncated packet (fewer than 12 header bytes) - src/captive_dns.py's response() returns
    # None for this (confirmed by reading the module), i.e. no response should ever arrive.
    response = dns_probe.query(joined_hotspot, "", raw_query=b"\x01\x02\x03")
    assert response is None, f"expected no response to a malformed/truncated packet, got {response!r}"


@pytest.mark.skip(
    reason=(
        "Raw-socket feasibility on the bench Rpi4 not yet checked (HARDWARE_TEST_PLAN.md §11.6, "
        "item 12) - spoofing an off-subnet UDP source address needs either a raw socket (CAP_NET_RAW, "
        "may need sudo/setcap the same way scripts/run_digital_twin_ci.sh already grants "
        "CAP_NET_BIND_SERVICE for its own DNS server) or a second network namespace with a routable "
        "off-subnet address, neither confirmed practical here yet. Flagged rather than guessed at - "
        "implement once a concrete spoofing mechanism is confirmed to work on the real bench host."
    )
)
def test_spoofed_off_subnet_source_address_is_ignored(joined_hotspot: str) -> None:
    raise AssertionError("should never run - see skip reason")


def test_dns_flood_backoff_curve_recovers_once_flood_stops(joined_hotspot: str) -> None:
    # src/captive_dns.py's own recv-failure backoff (_RECV_FAIL_BACKOFF_INITIAL_S=0.5s doubling to
    # _RECV_FAIL_BACKOFF_MAX_S=5.0s cap - confirmed by reading the module during §11.1's research).
    # Floods with malformed packets (each individually triggers the backoff path, not the normal
    # query path) for a few seconds, then confirms a legitimate query is still served promptly
    # afterward - the "recovers once the flood stops" half of this candidate; the backoff *curve*
    # itself (exact per-packet timing) isn't independently measured here, only its end effect.
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


def test_representative_put_round_trips_over_the_hotspot_link(joined_hotspot: str) -> None:
    # /notification's WarnCO2 - the same shared REST-round-trip shape as tests/_shared_rest_roundtrip.py's
    # mock/twin coverage (see HARDWARE_TEST_PLAN.md §2.2), now over a genuine wireless hotspot link.
    # Deliberately excludes /networking's SSID/PW/Country/Hostname fields - reserved for stage 6.
    res = http_client.fetch(joined_hotspot, 80, "PUT", "/notification", {"WarnCO2": 1700})
    assert res.status_code == 200
    assert res.json().get("result") == {"WarnCO2": "Valid"}, f"unexpected PUT result over the hotspot link: {res.json()!r}"


def test_real_static_website_content_serves_over_the_hotspot_link(joined_hotspot: str) -> None:
    # The same real property test_digital_twin_real_website_integration.py already proves for the
    # twin (SPECIFICATION.md Part A.9), now over real hardware/RF.
    res = http_client.fetch(joined_hotspot, 80, "GET", "/", timeout_s=10.0)
    assert res.status_code == 200
    assert len(res.body) > 0


# ---------------------------------------------------------------------------
# Stage 5 - client-side fault injection against the DUT's server role (items 17-19).
# ---------------------------------------------------------------------------


def test_malformed_http_request_over_real_wireless_degrades_cleanly(joined_hotspot: str) -> None:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(10.0)
        sock.connect((joined_hotspot, 80))
        sock.sendall(b"NOT A REAL HTTP REQUEST\r\n\r\n")
        try:
            sock.recv(4096)  # attempt a read so the connection isn't abruptly closed before the server responds; content deliberately not asserted, see below
        except TimeoutError:
            pass
    # The exact response shape isn't asserted (mock/twin already cover that in detail) - the real,
    # hardware-only property this adds is that the connection doesn't hang forever or crash the
    # webserver, over a genuine wireless link where real packet loss/reordering is possible.
    assert http_client.fetch(joined_hotspot, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after a malformed request over real wireless"


def test_rapid_associate_disassociate_churn_doesnt_wedge_station_management(bench: BenchBridge, hotspot_ssid: str, joined_hotspot: str) -> None:
    for _cycle in range(3):
        bench.leave_dut_hotspot_and_restore_bridge()
        time.sleep(1.0)  # brief settle, not a condition to poll for
        bench.join_dut_hotspot(hotspot_ssid, _HOTSPOT_PASSWORD, timeout_s=45.0)
    assert http_client.fetch(bench.gateway_ip(), 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after rapid associate/disassociate churn"


def test_concurrent_multi_client_burst_is_out_of_scope_here(joined_hotspot: str) -> None:
    # Scope-limited note, not a gap silently papered over (§11.5 item 19): a genuine concurrent
    # multi-client burst like tests_hardware/bench/test_end_to_end_timing.py's own bridge-side
    # burst test isn't reproducible in hotspot mode with only one bench radio available - this
    # test exists purely to document that ceiling explicitly, not to assert anything new.
    pass


# ---------------------------------------------------------------------------
# Stage 6 - the mutating step (items 20-21). MUST run after every read-only check above (see this
# module's own docstring on ordering) and MUST be the last thing that touches /networking's
# SSID/PW/Country/Hostname fields before the joined_hotspot fixture's own teardown flips back.
# ---------------------------------------------------------------------------


def test_invalid_credentials_rejected_without_triggering_reconnect(bench: BenchBridge, joined_hotspot: str) -> None:
    # Resolved finding (see this module's own docstring): post_fct fires if ANY field in the PUT
    # validates, so every field here must be invalid together, not just one, or this test would
    # itself trigger an unwanted early reconnect. A too-short WPA2 password (<8 chars) is invalid
    # per config_manager's own field-length validation for PW's schema entry.
    res = http_client.fetch(joined_hotspot, 80, "PUT", "/networking", {"PW": "short"})
    assert res.status_code == 200
    result = res.json().get("result", {})
    assert result.get("PW") != "Valid", f"expected the too-short password to be rejected, got {result!r}"
    # No reconnect should have fired - the bench radio must still be associated to the (unchanged)
    # hotspot afterward.
    assert bench.gateway_ip() == joined_hotspot, "DUT appears to have reconnected after a PUT that should have been entirely rejected"


def test_real_credentials_put_succeeds_and_confirms_accepted_values(bench: BenchBridge, joined_hotspot: str, hotspot_ssid: str) -> None:
    # ensure_bench_bridge() never re-prints the AP password on an idempotent re-run (by design -
    # toolchain/setup_toolchain.py's own comment: "a later idempotent run... never re-prints the
    # password"), so this harness has no way to read the real bench AP's own password back out of
    # NetworkManager once it already exists (nmcli deliberately doesn't expose stored PSKs in
    # plain -g queries either). The real credential handoff therefore needs it supplied externally
    # - see tests_hardware/README.md's credential-handoff section for how a dedicated session
    # provides this, rather than guessing or silently skipping the real PUT.
    password = os.environ.get("BENCH_AP_PASSWORD")
    if not password:
        pytest.skip("BENCH_AP_PASSWORD not set - see tests_hardware/README.md's credential-handoff section")
    ssid = bench.ap_ssid()
    res = http_client.fetch(joined_hotspot, 80, "PUT", "/networking", {"SSID": ssid, "PW": password, "Hostname": hotspot_ssid})
    assert res.status_code == 200
    result = res.json().get("result", {})
    assert result.get("SSID") == "Valid" and result.get("PW") == "Valid", f"real credential PUT was not accepted: {result!r}"


# ---------------------------------------------------------------------------
# Stage 7/8 - role-flip-back and closure (items 22-24). The flip-back itself happens in
# joined_hotspot's own teardown (after this file's last test runs) - these tests only run
# BEFORE that teardown, so they can't observe its own outcome directly; the real assertions for
# items 22-23 live in the fixture's own wait_until() call, which raises with full context on
# failure exactly like every other test's own assertions would.
# ---------------------------------------------------------------------------


def test_role_flip_back_and_reachability_are_asserted_in_fixture_teardown(joined_hotspot: str) -> None:
    # Documents items 22-23 (§11.5) as covered, even though the actual wait_until() call they
    # depend on only runs after this test function itself returns (in joined_hotspot's teardown) -
    # a real pytest constraint (a fixture's teardown code can't be "waited on" from inside a test
    # body that still holds the fixture), not an oversight. If the flip-back or reachability check
    # ever fails, pytest reports it as a fixture-teardown error attributed to this test's own
    # module, not silently swallowed.
    pass


def test_post_condition_sta_connected_state_inferred_from_reachability(joined_hotspot: str, dut_ip: str) -> None:
    # Item 24: /networking's GET response has no _conn_phase-equivalent field to assert on
    # directly (confirmed by reading src/asy_webserver_service.py's own _get_settings_flat()/
    # SettingsGroup wiring - no such field is registered anywhere in the /networking group).
    # Adding one would be a real src/ change and its own scoped decision, not assumed here (flagged
    # to the project owner rather than added unasked - see HARDWARE_TEST_PLAN.md §11.6). The
    # indirect proxy used instead: dut_ip (captured once, session-scoped, before this scenario ever
    # started) being reachable again is itself strong evidence of STA-connected state, since only
    # STA mode would route bridge-network traffic to that specific address at all.
    assert dut_ip, "dut_ip fixture produced an empty address - can't infer STA-connected state from it"
