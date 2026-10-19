"""Bench-tier role reversal: the bench radio joins the DUT's own hotspot and tests its AP, DHCP, captive DNS and REST
role from a real external client (untestable in the digital twin). The credential stage runs last by destructive_last,
the flip back is a test of its own, and the fixture's teardown repeats it only when that test did not get it done."""

import contextlib
import dataclasses
import os
import socket
import subprocess
import sys
import time
from typing import TYPE_CHECKING

import _load
import dns_probe
import http_client
import pytest
import tomllib
import website_identity
from bench_control import ROLE_REVERSAL_CLIENT_CONN, BenchBridge
from error_log_helpers import assert_module_error_log_clean, assert_module_error_log_empty, assert_no_task_ended, code, errcount_entry, get_errcount, reset_all_error_logs
from harness import REPO_ROOT, Board, HardwareTestFailureError, device_toml, get_routes, hotspot_password, recover_by_reset, wait_until
from soak_durations import SOAK_DURATION_SECONDS

if TYPE_CHECKING:
    from collections.abc import Iterator

    from http_client import JSONObject

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("real_website_integration", "sensortask_integration", "wifi_modes", "ci_suite._run_6_configure_ssid", "ci_suite._run_7_wifi_hotspot_dns")

pytestmark = pytest.mark.role_reversal


# @tunable l4.hotspot_role_reversal_join_attempts = 5
_JOIN_ATTEMPTS = 5
# @tunable l4.hotspot_role_reversal_join_hotspot_timeout_s = 45.0
_JOIN_HOTSPOT_TIMEOUT_S = 45.0
# @tunable l4.hotspot_role_reversal_hotspot_scan_timeout_s = 30.0
_HOTSPOT_SCAN_TIMEOUT_S = 30.0
# @tunable l4.hotspot_role_reversal_hotspot_scan_poll_s = 2.0
_HOTSPOT_SCAN_POLL_S = 2.0
# @tunable l4.hotspot_role_reversal_probe_timeout_s = 10.0
_PROBE_TIMEOUT_S = 10.0
# @tunable l4.hotspot_role_reversal_dhcp_timeout_s = 45.0
_DHCP_TIMEOUT_S = 45.0
# @tunable l4.hotspot_role_reversal_dhcp_poll_s = 2.0
_DHCP_POLL_S = 2.0
# @tunable l4.hotspot_role_reversal_restore_put_timeout_s = 15.0
_RESTORE_PUT_TIMEOUT_S = 15.0
# @tunable l4.hotspot_role_reversal_flip_back_timeout_s = 90.0
_FLIP_BACK_TIMEOUT_S = 90.0
# @tunable l4.hotspot_role_reversal_flip_back_poll_s = 3.0
_FLIP_BACK_POLL_S = 3.0
# @tunable l4.hotspot_role_reversal_recovery_timeout_s = 30.0
_RECOVERY_TIMEOUT_S = 30.0
# @tunable l4.hotspot_role_reversal_reassoc_visible_timeout_s = 15.0
_REASSOC_VISIBLE_TIMEOUT_S = 15.0
# @tunable l4.hotspot_role_reversal_reassoc_visible_poll_s = 1.0
_REASSOC_VISIBLE_POLL_S = 1.0
# @tunable l4.hotspot_role_reversal_reassociate_cycles = 3
_REASSOCIATE_CYCLES = 3
# @tunable l4.hotspot_role_reversal_dns_flood_s = 3.0
_DNS_FLOOD_S = 3.0
# @tunable l4.hotspot_role_reversal_dns_flood_step_s = 0.05
_DNS_FLOOD_STEP_S = 0.05
# @tunable l4.hotspot_role_reversal_dns_recovery_timeout_s = 8.0
_DNS_RECOVERY_TIMEOUT_S = 8.0
# @tunable l4.hotspot_role_reversal_raw_socket_timeout_s = 10.0
_RAW_SOCKET_TIMEOUT_S = 10.0
# @tunable l4.hotspot_role_reversal_spoof_capture_s = 5.0
_SPOOF_CAPTURE_S = 5.0
# @tunable l4.hotspot_role_reversal_link_advance_timeout_s = 30.0
_LINK_ADVANCE_TIMEOUT_S = 30.0
# Added to each wait derived from the Wi-Fi service's own timeline: the bench's scan cadence, a link loss noticed late.
# @tunable l4.hotspot_role_reversal_derived_wait_margin_s = 30.0
_DERIVED_WAIT_MARGIN_S = 30.0
_WIFI = "asy_wifi_service.py"
# The AP's DHCP server is MicroPython's shared/netutils/dhcpserver.c (v1.29.0): it leases the server's own first three
# octets and a last octet 16 + n, n < 8 (dhcpserver.h:31-32, dhcpserver.c:238).
_DHCPS_BASE_IP = 16  # source: shared/netutils/dhcpserver.h DHCPS_BASE_IP
_DHCPS_MAX_IP = 8  # source: shared/netutils/dhcpserver.h DHCPS_MAX_IP
_SPOOF_SOURCE = "203.0.113.5"  # RFC 5737 TEST-NET-3, the only kind of source tests_hardware/spoof_udp.py forges
_SPOOF_SOURCE_PORT = 40000
_QTYPE_AAAA = 28  # RFC 3596 section 2.1
_WARN_CO2_PROBES = (1700, 1750)  # a value that differs from the board's, whichever of the two it holds
_STRANDED = "the DUT is stranded in hotspot mode with an empty SSID: restore it over the serial console (tests_hardware/README.md, the role-reversal repair)"


@dataclasses.dataclass
class _JoinRecord:
    # What joined_hotspot saw while it set the scenario up, and what the flip back saw: the stage tests read it rather
    # than restating that the fixture succeeded. link holds GET /status's UARTLINK counters by moment.
    original_ssid: str = ""
    seen_ssid: str = ""
    password: str = ""
    associate_s: float = -1.0
    link: "dict[str, JSONObject | None]" = dataclasses.field(default_factory=dict)
    switch_s: "dict[str, float]" = dataclasses.field(default_factory=dict)
    ssid_restored: bool = False
    flipped_back: bool = False


_RECORD = _JoinRecord()


# ---------------------------------------------------------------------------
# Stage 0 - precondition, each fact joined_hotspot recorded named by a test of its own.
# ---------------------------------------------------------------------------


def test_dut_enters_hotspot_mode_after_ssid_cleared(joined_hotspot: str) -> None:
    # The hotspot mode is GET /status's networking.Mode over the hotspot link; /networking carries no mode field.
    assert _load.mode(joined_hotspot) == "AP", f"the DUT does not report its hotspot mode over its own hotspot: Mode {_load.mode(joined_hotspot)!r}"


def test_hotspot_ssid_matches_configured_hostname(hotspot_ssid: str, joined_hotspot: str) -> None:
    assert _RECORD.seen_ssid == hotspot_ssid, f"the scan found {_RECORD.seen_ssid!r}, not the DUT's Hostname {hotspot_ssid!r}"


def test_the_dut_accepts_the_toml_hotspot_password(joined_hotspot: str) -> None:
    # The join succeeded with the recorded password; that it is the schema's and the TOML's is tests_scripts' check.
    assert _RECORD.password == hotspot_password(), "the fixture joined with a password other than the bench TOML's hotspot_password"


# ---------------------------------------------------------------------------
# Stage 1 - association.
# ---------------------------------------------------------------------------


def test_bench_radio_associates_within_bounded_window(joined_hotspot: str) -> None:
    assert 0.0 <= _RECORD.associate_s <= _JOIN_HOTSPOT_TIMEOUT_S, f"the successful join took {_RECORD.associate_s:.1f}s, past {_JOIN_HOTSPOT_TIMEOUT_S}s"


# ---------------------------------------------------------------------------
# Stage 2 - DHCP: MicroPython's C DHCP server (shared/netutils/dhcpserver.c), compiled into the firmware - no project code.
# ---------------------------------------------------------------------------


def test_bench_radio_receives_a_valid_dhcp_lease(bench: "BenchBridge", joined_hotspot: str) -> None:
    ip = bench.own_ip_on()
    parts = ip.split(".")
    assert len(parts) == 4 and all(p.isdigit() for p in parts), f"own_ip_on() returned something that doesn't look like an IPv4 address: {ip!r}"


def test_leased_ip_falls_within_the_aps_own_subnet(bench: "BenchBridge", joined_hotspot: str) -> None:
    own, gw = bench.own_ip_on().split("."), joined_hotspot.split(".")
    assert own[:3] == gw[:3] and _DHCPS_BASE_IP <= int(own[3]) < _DHCPS_BASE_IP + _DHCPS_MAX_IP, f"leased {'.'.join(own)} is not one of the server's {'.'.join(gw[:3])}.{_DHCPS_BASE_IP}..{_DHCPS_BASE_IP + _DHCPS_MAX_IP - 1} (gateway {joined_hotspot})"


def test_repeated_associate_disassociate_cycles_dont_wedge_the_dhcp_server(bench: "BenchBridge", hotspot_ssid: str, joined_hotspot: str, result_note: "_load.Note") -> None:
    # Fault injection against the DHCP server: three reassociate cycles, each confirming a lease. The radio leaves the
    # hotspot with the bridge's AP left down, so its scan sees the hotspot without an AP re-activation in between.
    for cycle in range(_REASSOCIATE_CYCLES):
        bench.leave_dut_hotspot()
        wait_until(lambda: bench.is_ssid_visible(hotspot_ssid), timeout_s=_REASSOC_VISIBLE_TIMEOUT_S, poll_interval_s=_REASSOC_VISIBLE_POLL_S, description=f"DUT hotspot {hotspot_ssid!r} visible again on reassociate cycle {cycle}")
        _join_dut_hotspot_with_reverify_retry(bench, hotspot_ssid, hotspot_password(), result_note)
        wait_until(lambda: _on_dut_hotspot(bench), timeout_s=_DHCP_TIMEOUT_S, poll_interval_s=_DHCP_POLL_S, description=f"DHCP lease on reassociate cycle {cycle}")


# ---------------------------------------------------------------------------
# Stage 3 - captive DNS (src/asy_captive_dns.py).
# ---------------------------------------------------------------------------


def test_arbitrary_hostname_resolves_to_the_aps_own_ip(joined_hotspot: str) -> None:
    response = dns_probe.query(joined_hotspot, "www.example.com")
    assert response is not None, f"no DNS response from {joined_hotspot}:53 for an arbitrary hostname"
    assert dns_probe.extract_answer_ip(response) == joined_hotspot, f"DNS answer didn't point back at the AP's own IP {joined_hotspot}"


def test_devices_own_hostname_resolves_the_same_way(joined_hotspot: str, hotspot_ssid: str) -> None:
    # src/asy_captive_dns.py answers every query identically regardless of the queried name - the
    # device's own real Hostname must not be special-cased differently from an arbitrary one.
    response = dns_probe.query(joined_hotspot, hotspot_ssid)
    assert response is not None
    assert dns_probe.extract_answer_ip(response) == joined_hotspot


def test_genuine_root_domain_query_is_answered_correctly(joined_hotspot: str) -> None:
    # A root query (QNAME = the zero-length root label alone) - the `_parsed_ok` real-vs-malformed
    # distinction src/asy_captive_dns.py's own code comments call out.
    txn_id = b"\x99\x99"
    header = txn_id + bytes([0x01, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    question = b"\x00" + bytes([0, 1, 0, 1])  # root label, then QTYPE=A QCLASS=IN packed as raw bytes
    response = dns_probe.query(joined_hotspot, "", raw_query=header + question)
    assert response is not None, "no response to a genuine root-domain query"
    assert dns_probe.extract_answer_ip(response) == joined_hotspot


def test_an_aaaa_query_gets_an_empty_answer(joined_hotspot: str) -> None:
    # An A or ANY query gets the A record, any other type NOERROR with no answer (RFC 2308 2.2, src/asy_captive_dns.py).
    response = dns_probe.query(joined_hotspot, "", raw_query=dns_probe.build_query("www.example.com", qtype=_QTYPE_AAAA)[0])
    assert response is not None, "no response to an AAAA query - the captive DNS must answer it, with no record"
    assert dns_probe.answer_count(response) == 0, f"an AAAA query got {dns_probe.answer_count(response)} answer record(s), not the empty NODATA answer: {response!r}"


def test_malformed_truncated_packet_is_silently_dropped(joined_hotspot: str, request: pytest.FixtureRequest) -> None:
    # Fewer than 12 header bytes: response() returns None, and its path logs an event (pr.evt()), never an error.
    reset_all_error_logs(joined_hotspot, request.node.name)
    response = dns_probe.query(joined_hotspot, "", raw_query=b"\x01\x02\x03")
    assert response is None, f"expected no response to a malformed/truncated packet, got {response!r}"
    assert_module_error_log_empty(joined_hotspot, "DNSSRV")


def test_spoofed_off_subnet_source_address_is_ignored(bench: "BenchBridge", joined_hotspot: str) -> None:
    # A well-formed query forged from an off-subnet documentation address: the radio sees no packet from the DUT to it
    # over the capture window, and a legitimate query from the bench radio is still answered.
    query = dns_probe.build_query("www.example.com")[0]
    capture = subprocess.Popen(  # argv from constants and the bridge's own interface name, no shell
        ["sudo", "-n", "timeout", str(_SPOOF_CAPTURE_S), "tcpdump", "-i", bench.wifi_iface(), "-nn", "-l", "src", "host", joined_hotspot, "and", "dst", "host", _SPOOF_SOURCE],  # sudo from PATH, as bench_control runs it
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # tcpdump says "listening on" once attached: a spoof sent before that would be answered unseen.
        listening = capture.stderr.readline() if capture.stderr is not None else ""
        assert "listening on" in listening, f"the capture never started: {listening!r}"
        sent = subprocess.run(  # argv from constants and this interpreter, no shell
            ["sudo", "-n", sys.executable, str(REPO_ROOT / "tests_hardware" / "spoof_udp.py"), "--src", _SPOOF_SOURCE, "--dst", joined_hotspot, "--sport", str(_SPOOF_SOURCE_PORT), "--dport", "53", "--payload-hex", query.hex()],  # sudo from PATH
            capture_output=True,
            text=True,
            timeout=_RAW_SOCKET_TIMEOUT_S,
            check=False,
        )
        assert sent.returncode == 0, f"the spoofed query was never sent (exit {sent.returncode}): {sent.stderr.strip()}"
        seen, errors = capture.communicate(timeout=_SPOOF_CAPTURE_S + _RAW_SOCKET_TIMEOUT_S)
    finally:
        if capture.poll() is None:
            capture.kill()
            capture.wait()
    assert capture.returncode in (0, 124), f"the capture failed (exit {capture.returncode}): {errors.strip()}"  # 124: timeout(1) ended it
    assert not seen.strip(), f"the DUT answered a query forged from off-subnet {_SPOOF_SOURCE}: {seen.strip()}"
    response = dns_probe.query(joined_hotspot, "www.example.com")
    assert response is not None and dns_probe.extract_answer_ip(response) == joined_hotspot, "a legitimate query went unanswered after the spoofed one"
    assert_no_task_ended(joined_hotspot, "a spoofed off-subnet DNS query")


def test_dns_flood_leaves_captive_dns_serving_and_it_recovers(joined_hotspot: str) -> None:
    # A garbage-but-present UDP payload still yields a real (data, addr) from recvfrom(), so this
    # flood takes the same pr.evt()-only path a normal query does, never the recv-failure backoff
    # branch. What it proves is robustness under flood and recovery after, not the backoff curve.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        deadline = time.monotonic() + _DNS_FLOOD_S
        while time.monotonic() < deadline:
            sock.sendto(b"\x00\x01\x02", (joined_hotspot, 53))
            time.sleep(_DNS_FLOOD_STEP_S)
    response = dns_probe.query(joined_hotspot, "recovery-check.example", timeout_s=_DNS_RECOVERY_TIMEOUT_S)
    assert response is not None, "no response to a legitimate query shortly after a malformed-packet flood - backoff may not be recovering"
    assert dns_probe.extract_answer_ip(response) == joined_hotspot


# ---------------------------------------------------------------------------
# Stage 4 - REST surface over the hotspot link.
# ---------------------------------------------------------------------------


def test_every_get_endpoint_reachable_and_shaped_over_the_hotspot_link(joined_hotspot: str) -> None:
    for path in get_routes(json_only=False):  # every registered GET route, the page included
        res = http_client.fetch(joined_hotspot, 80, "GET", path, timeout_s=_PROBE_TIMEOUT_S)
        assert res.status_code == 200, f"GET {path} over the hotspot link -> {res.status_code}"


@pytest.mark.persistence_write
def test_representative_put_round_trips_over_the_hotspot_link(joined_hotspot: str) -> None:
    # /notification's WarnCO2 over a real wireless hotspot link, a value differing from the board's and the board's own
    # restored after; /networking's radio fields are the credential stage's.
    current = _load.get_object(joined_hotspot, "/notification", _PROBE_TIMEOUT_S).get("WarnCO2")
    value = _WARN_CO2_PROBES[1] if current == _WARN_CO2_PROBES[0] else _WARN_CO2_PROBES[0]
    try:
        res = http_client.fetch(joined_hotspot, 80, "PUT", "/notification", {"WarnCO2": value}, timeout_s=_PROBE_TIMEOUT_S)
        assert _load.as_object(res.json().get("result"), "result").get("WarnCO2") == "Valid", f"WarnCO2 {value} over the hotspot link was not taken: {res.status_code} {res.body!r}"
    finally:
        restore = http_client.fetch(joined_hotspot, 80, "PUT", "/notification", {"WarnCO2": current}, timeout_s=_PROBE_TIMEOUT_S)
        assert _load.as_object(restore.json().get("result"), "result").get("WarnCO2") in ("Valid", "Unchanged"), f"restoring WarnCO2 {current!r} was refused: {restore.body!r}"


def test_real_static_website_content_serves_over_the_hotspot_link(joined_hotspot: str, bench_device_name: str) -> None:
    # The same real property test_digital_twin_real_website_integration.py already proves for the
    # twin (SPECIFICATION.md Part A.9), now over real hardware/RF.
    res = http_client.fetch(joined_hotspot, 80, "GET", "/", timeout_s=_PROBE_TIMEOUT_S)
    assert res.status_code == 200
    website_identity.assert_page_is_this_devices_build(res, "the hotspot link", device=bench_device_name)


def test_nonsense_path_redirects_to_root_over_the_hotspot_link(joined_hotspot: str, request: pytest.FixtureRequest) -> None:
    # The hotspot-mode counterpart to test_network_resilience.py's STA-mode 404 test. A raw socket, not
    # http_client.fetch(): urllib follows the 3xx and hides the 302/Location under test.
    reset_all_error_logs(joined_hotspot, request.node.name)
    with socket.create_connection((joined_hotspot, 80), timeout=_RAW_SOCKET_TIMEOUT_S) as sock:
        sock.sendall(b"GET /generate_204 HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        response = b""
        try:
            while chunk := sock.recv(4096):
                response += chunk
        except TimeoutError:
            pass
    assert response.startswith((b"HTTP/1.0 302", b"HTTP/1.1 302")), f"GET to a nonsense path over the hotspot link did not return 302: {response!r}"
    assert b"Location: /\r\n" in response or b"location: /\r\n" in response, f"redirect Location header was not '/': {response!r}"
    assert_module_error_log_empty(joined_hotspot, "WEBSERVER")  # a routine redirect logs nothing


def test_put_to_nonsense_path_is_405_not_a_redirect_over_the_hotspot_link(joined_hotspot: str, request: pytest.FixtureRequest) -> None:
    # A non-GET to an unmatched path resolves to 405 inside Microdot's routing, before _StaticRoutes.serve() is reached,
    # so the redirect fallback cannot leak into an unrelated error path. The hotspot<->STA toggle is not repeated here:
    # Part A.5, and ~15-30s per cycle.
    reset_all_error_logs(joined_hotspot, request.node.name)
    res = http_client.fetch(joined_hotspot, 80, "PUT", "/generate_204", {}, timeout_s=_PROBE_TIMEOUT_S)
    assert res.status_code == 405, f"PUT to a nonsense path over the hotspot link did not return 405: {res.status_code} {res.body!r}"
    assert_module_error_log_empty(joined_hotspot, "WEBSERVER")


# ---------------------------------------------------------------------------
# Stage 5 - client-side fault injection against the DUT's server role.
# ---------------------------------------------------------------------------


def test_malformed_http_request_over_real_wireless_degrades_cleanly(joined_hotspot: str, request: pytest.FixtureRequest) -> None:
    # A head the server refuses: answered with a 400-class status line or closed, never left hanging; its one traced
    # drop is W HTTP_BAD_HEAD and HTTPDropped counts it.
    reset_all_error_logs(joined_hotspot, request.node.name)
    with socket.create_connection((joined_hotspot, 80), timeout=_RAW_SOCKET_TIMEOUT_S) as sock:
        sock.sendall(b"NOT A REAL HTTP REQUEST\r\n\r\n")
        try:
            answer = sock.recv(4096)
        except TimeoutError:
            pytest.fail(f"the server neither answered nor closed a malformed request within {_RAW_SOCKET_TIMEOUT_S:g} s")
        except ConnectionResetError:
            answer = b""
    assert answer == b"" or answer.startswith((b"HTTP/1.0 4", b"HTTP/1.1 4")), f"a malformed request got neither a 400-class status line nor a close: {answer[:80]!r}"
    assert _load.serving(joined_hotspot), "webserver unresponsive after a malformed request over real wireless"
    assert_module_error_log_clean(joined_hotspot, "WEBSERVER", allowed_warnings=(code("W", "HTTP_BAD_HEAD"),))
    dropped = _load.as_object(_load.get_object(joined_hotspot, "/status", _PROBE_TIMEOUT_S).get("networking"), "GET /status networking").get("HTTPDropped")
    assert isinstance(dropped, int) and dropped >= 1, f"the refused head is not counted in HTTPDropped: {dropped!r}"


def test_rapid_associate_disassociate_churn_doesnt_wedge_station_management(bench: "BenchBridge", hotspot_ssid: str, joined_hotspot: str, result_note: "_load.Note") -> None:
    # The DHCP cycles' leave-with-the-AP-down and scan, without waiting for a lease: station management, not DHCP.
    for cycle in range(_REASSOCIATE_CYCLES):
        bench.leave_dut_hotspot()
        wait_until(lambda: bench.is_ssid_visible(hotspot_ssid), timeout_s=_REASSOC_VISIBLE_TIMEOUT_S, poll_interval_s=_REASSOC_VISIBLE_POLL_S, description=f"DUT hotspot {hotspot_ssid!r} visible again on churn cycle {cycle}")
        _join_dut_hotspot_with_reverify_retry(bench, hotspot_ssid, hotspot_password(), result_note)
    wait_until(lambda: _on_dut_hotspot(bench), timeout_s=_DHCP_TIMEOUT_S, poll_interval_s=_DHCP_POLL_S, description="a lease after the churn")
    assert _load.serving(bench.gateway_ip()), "webserver unresponsive after rapid associate/disassociate churn"


# ---------------------------------------------------------------------------
# Stage 6 - the credential stage, run after every other test of this module by destructive_last (the conftest's
# ordering), then the flip back as a test of its own; the fixture's teardown finds that work done.
# ---------------------------------------------------------------------------


@pytest.mark.destructive_last
def test_invalid_credentials_rejected_without_triggering_reconnect(bench: "BenchBridge", joined_hotspot: str) -> None:
    # post_fct (the /networking group's reconnect hook) fires if any field validates; a PW one short of _VAL_PW's lower
    # bound is rejected, so nothing persists and nothing reconnects.
    pw_min = _load.field_schema(_WIFI, "PW")[2]
    assert isinstance(pw_min, int) and pw_min > 1, f"_VAL_PW declares no usable lower bound: {pw_min!r}"
    res = http_client.fetch(joined_hotspot, 80, "PUT", "/networking", {"PW": "x" * (pw_min - 1)}, timeout_s=_PROBE_TIMEOUT_S)
    assert _load.as_object(res.json().get("result"), "result").get("PW") == "Invalid", f"a {pw_min - 1}-character password was not refused: {res.status_code} {res.body!r}"
    assert bench.gateway_ip() == joined_hotspot, "DUT appears to have reconnected after a PUT that should have been entirely rejected"


@pytest.mark.destructive_last
@pytest.mark.persistence_write
def test_a_wrong_password_over_the_hotspot_reopens_the_hotspot(bench: "BenchBridge", joined_hotspot: str, hotspot_ssid: str, result_note: "_load.Note") -> None:
    # A credentials change lands in the fresh-boot state (owner, 2026-10-08, paraphrase): its streak fails (a wrong key, the
    # bench AP down while the radio is the DUT's client) and the hotspot opens once more. One owned flash write; the next test restores it.
    password = os.environ.get("BENCH_AP_PASSWORD") or bench.ap_password()
    wrong = ("y" if password[0] == "x" else "x") + password[1:]  # well-formed: the same length, inside _VAL_PW's bounds
    before = _wifi_log(joined_hotspot)
    res = http_client.fetch(joined_hotspot, 80, "PUT", "/networking", {"SSID": bench.ap_ssid(), "PW": wrong}, timeout_s=_PROBE_TIMEOUT_S)
    put_at = time.monotonic()
    assert res.status_code == 200 and res.json().get("result") == {"SSID": "Valid", "PW": "Valid"}, f"the wrong-password PUT was not taken: {res.status_code} {res.body!r}"
    left_bound_s = _load.src_number(_WIFI, "_WIFI_REFRESH_S") + _load.src_number(_WIFI, "_RECONNECT_CALLER_GRACE_S") + _DERIVED_WAIT_MARGIN_S
    wait_until(lambda: not _on_dut_hotspot(bench), timeout_s=left_bound_s, poll_interval_s=_DHCP_POLL_S, description="the DUT to leave its hotspot for the fresh streak")
    reopen_s = max(put_at + _streak_bound_s() - time.monotonic(), 0.0)
    wait_until(lambda: bench.is_ssid_visible(hotspot_ssid), timeout_s=reopen_s, poll_interval_s=_HOTSPOT_SCAN_POLL_S, description=f"the DUT's hotspot ({hotspot_ssid!r}) to reopen after the failed fresh streak")
    _join_dut_hotspot_with_reverify_retry(bench, hotspot_ssid, hotspot_password(), result_note)
    wait_until(lambda: bench.gateway_ip() == joined_hotspot, timeout_s=_DHCP_TIMEOUT_S, poll_interval_s=_DHCP_POLL_S, description="a lease on the reopened hotspot")
    gained = _gained_entries(before, _wifi_log(joined_hotspot))
    to_hotspot, silent = ("W", code("W", "WLAN_TO_HOTSPOT")), ("W", code("W", "WLAN_SILENT"))
    assert gained.count(to_hotspot) == 1 and silent not in gained, f"expected one more WLAN_TO_HOTSPOT and no WLAN_SILENT in WIFI's history, gained {gained!r}"


@pytest.mark.destructive_last
@pytest.mark.persistence_write
def test_real_credentials_put_succeeds_and_confirms_accepted_values(bench: "BenchBridge", joined_hotspot: str, hotspot_ssid: str) -> None:
    # bench.ap_password() reads the real PSK (nmcli --show-secrets; BENCH_AP_PASSWORD overrides it): this PUT puts the
    # network back, so the flip back needs no SSID restore of its own (tests_hardware/README.md).
    password = os.environ.get("BENCH_AP_PASSWORD") or bench.ap_password()
    ssid = bench.ap_ssid()
    res = http_client.fetch(joined_hotspot, 80, "PUT", "/networking", {"SSID": ssid, "PW": password, "Hostname": hotspot_ssid}, timeout_s=_PROBE_TIMEOUT_S)
    assert res.status_code == 200, f"the real-credentials PUT failed: {res.status_code} {res.body!r}"
    result = _load.as_object(res.json().get("result"), "result")
    # "Unchanged" is a correct answer for a field that already holds the value: either acceptance is a pass.
    accepted = {"Valid", "Unchanged"}
    assert result.get("SSID") in accepted and result.get("PW") in accepted, f"real credential PUT was not accepted: {result!r}"
    _RECORD.ssid_restored = ssid == _RECORD.original_ssid


@pytest.mark.destructive_last
@pytest.mark.soak_duration
@pytest.mark.persistence_write
def test_a_second_failed_streak_goes_silent_and_links_on_a_later_attempt(bench: "BenchBridge", joined_hotspot: str, hotspot_ssid: str, dut_ip: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # The second failed streak goes silent and a later attempt links (owner, 2026-10-08, paraphrase), on the preceding test's stored
    # credentials with the bench AP still down. Writes nothing: persistence_write is the AND-gate on that test's write; about
    # two hotspot_time_min windows long, it runs in a soak whose duration covers them, with the module whole.
    window_s = _wifi_settings()[1] * 60.0
    duration = request.config.getoption("--soak-duration")
    if duration is None or SOAK_DURATION_SECONDS[duration] < 2 * window_s:
        pytest.skip(f"about two hotspot windows long ({2 * window_s:.0f} s): runs with --soak-duration covering them, --allow-persistence-write and the module whole")
    refresh_s = _load.src_number(_WIFI, "_WIFI_REFRESH_S")
    grace_s = _load.src_number(_WIFI, "_RECONNECT_CALLER_GRACE_S")
    restored = False
    try:
        assert _RECORD.ssid_restored, "needs test_real_credentials_put_succeeds_and_confirms_accepted_values's write in the same run: on stage 0's empty SSID the unit returns to its hotspot every window"
        started = time.monotonic()
        wait_until(lambda: not _on_dut_hotspot(bench), timeout_s=refresh_s + grace_s + _DERIVED_WAIT_MARGIN_S, poll_interval_s=_DHCP_POLL_S, description="the DUT to leave its hotspot for the fresh streak")
        wait_until(lambda: bench.is_ssid_visible(hotspot_ssid), timeout_s=max(started + _streak_bound_s() - time.monotonic(), 0.0), poll_interval_s=_HOTSPOT_SCAN_POLL_S, description=f"the DUT's hotspot ({hotspot_ssid!r}) to reopen after the failed fresh streak")
        _join_dut_hotspot_with_reverify_retry(bench, hotspot_ssid, hotspot_password(), result_note)
        wait_until(lambda: bench.gateway_ip() == joined_hotspot, timeout_s=_DHCP_TIMEOUT_S, poll_interval_s=_DHCP_POLL_S, description="a lease on the reopened hotspot")
        before = _wifi_log(joined_hotspot)
        # A BenchBridge over the client profile: its ap_down() is a user deactivation, which NetworkManager blocks from
        # autoconnecting again (nmcli(1), "connection down"), so the radio stays off the DUT's hotspot and the bench AP down.
        BenchBridge(ap_conn=ROLE_REVERSAL_CLIENT_CONN).ap_down()
        window_end_at = time.monotonic() + window_s  # the window arms at the DUT's first stations check without a client
        wait_until(lambda: time.monotonic() >= window_end_at and not bench.is_ssid_visible(hotspot_ssid), timeout_s=window_s + 2 * refresh_s + grace_s + _DERIVED_WAIT_MARGIN_S, poll_interval_s=_HOTSPOT_SCAN_POLL_S, description="the hotspot window to end with no client")
        try:
            wait_until(lambda: bench.is_ssid_visible(hotspot_ssid), timeout_s=_streak_bound_s() + _HOTSPOT_SCAN_TIMEOUT_S, poll_interval_s=_HOTSPOT_SCAN_POLL_S, description="the hotspot to reopen after the second streak")
        except TimeoutError:
            pass  # closed through the second streak and one more scan window: the silent mode
        else:
            pytest.fail("the DUT's hotspot came back after its second failed streak instead of the silent mode")
        bench.ap_up()
        restored = True
        up_at = time.monotonic()
        relink_s = window_s + _load.src_number(_WIFI, "_STA_CONNECT_POLL_ITERS") * _load.src_number(_WIFI, "_STA_CONNECT_POLL_S") + refresh_s + _DERIVED_WAIT_MARGIN_S
        wait_until(lambda: _load.sta_mode(dut_ip), timeout_s=relink_s, poll_interval_s=_FLIP_BACK_POLL_S, description="the silent DUT to link on a later attempt once the bench AP is back, with no reset")
        assert_no_task_ended(dut_ip, "the second failed streak, the silent mode and its later link")
        result_note(f"silent mode: relinked {time.monotonic() - up_at:.0f} s after the bench AP came back (one silent period is {window_s:.0f} s)")
        gained = _gained_entries(before, _wifi_log(dut_ip))
        silent, give_up = ("W", code("W", "WLAN_SILENT")), ("E", code("E", "WLAN_GIVE_UP"))
        assert gained.count(silent) == 1 and give_up not in gained, f"expected one WLAN_SILENT slot and no WLAN_GIVE_UP in WIFI's history, gained {gained!r}"
    finally:
        # The bench AP back on every path, and left alone once up: NetworkManager takes an active profile down before it
        # activates it again (NetworkManager's nm-manager.c, _internal_activate_device()), which would drop the relinked DUT.
        if not restored:
            bench.leave_dut_hotspot_and_restore_bridge()


@pytest.mark.destructive_last
def test_the_role_flips_back_and_the_board_is_sta_connected_on_the_bridge(board: Board, bench: "BenchBridge", joined_hotspot: str, dut_ip: str, result_note: "_load.Note") -> None:
    # No STA-phase field is added to /networking (owner, 2026-09-26: 'It seems to be unreachable by definition.'): a
    # reachable board on the bridge network is STA-connected by definition, read as GET /status's networking.Mode.
    if not _RECORD.flipped_back:
        _flip_back(board, bench, joined_hotspot, dut_ip, result_note)
    assert _load.sta_mode(dut_ip), f"the DUT is not back on the bridge in STA mode after the flip back: {dut_ip}"
    ssid = _load.get_object(dut_ip, "/networking", _PROBE_TIMEOUT_S).get("SSID")
    assert ssid == _RECORD.original_ssid, f"the DUT holds SSID {ssid!r} after the flip back, not stage 0's {_RECORD.original_ssid!r}"
    assert_no_task_ended(dut_ip, "the role flip back")


@pytest.mark.destructive_last
def test_the_uart_link_across_the_mode_switch_is_recorded(joined_hotspot: str, dut_ip: str, result_note: "_load.Note") -> None:
    # What each WLAN mode switch cost the UART link (F.3's switch stall): the failures it added and its span, recorded;
    # asserted only that transfers advance again after each switch.
    if not _load.instance_loggers("uart_link"):
        pytest.skip("the bench device wires no uart_link instance")
    assert _RECORD.flipped_back, "the flip back did not complete, so the second switch has no record"
    points = {name: _RECORD.link.get(name) for name in ("before", "joined", "before back", "back")}
    for name, counters in points.items():
        result_note(f"UARTLINK {name}: {counters}")
    result_note(f"switch spans: {', '.join(f'{k} {v:.1f}s' for k, v in _RECORD.switch_s.items())}")
    before, joined, back = points["before"], points["joined"], points["back"]
    assert before is not None and joined is not None and back is not None, f"a link read is missing: {points}"
    assert _int(joined, "Transfers") > _int(before, "Transfers"), f"no transfer advanced across the switch to the hotspot: {before} -> {joined}"
    wait_until(lambda: _int(_link_counters(dut_ip) or {}, "Transfers") > _int(back, "Transfers"), timeout_s=_LINK_ADVANCE_TIMEOUT_S, poll_interval_s=_HOTSPOT_SCAN_POLL_S, description="the link's transfers advancing after the switch back to STA")


def _flip_back(board: Board, bench: "BenchBridge", gateway_ip: str, dut_ip: str, note: "_load.Note") -> None:
    # Stage 7 - the SSID back over the hotspot, the only link left to the DUT, unless the credential stage already
    # restored it; a refused or unreachable restore raises. Stage 8 - the bridge back, the DUT on it in STA mode.
    try:  # a record only: an unreachable hotspot here is the restore's to report, below
        _RECORD.link["before back"] = _link_counters(gateway_ip)
    except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError):
        _RECORD.link["before back"] = None
    started = time.monotonic()
    if not _RECORD.ssid_restored:
        try:
            _restore_hotspot_ssid(gateway_ip)
        except HardwareTestFailureError:
            bench.leave_dut_hotspot_and_restore_bridge()
            raise
    bench.leave_dut_hotspot_and_restore_bridge()
    # A failed reconnect reopens the DUT's hotspot once, then after its window one more streak, then the silent mode
    # retrying once per hotspot_time_min (Part A.4): one reported reset instead of waiting that out, a second raises.
    recover_by_reset(board, bench, ready=lambda: _load.sta_mode(dut_ip), first_wait_s=_FLIP_BACK_TIMEOUT_S, retry_wait_s=_RECOVERY_TIMEOUT_S, skipped="the passive STA reconnect after the flip back, or the silent mode's next attempt", note=note, description="role flip back")
    _RECORD.switch_s["back to STA"] = time.monotonic() - started
    _RECORD.link["back"] = _link_counters(dut_ip)
    _RECORD.flipped_back = True


def _gained_entries(before: "tuple[int, list[tuple[str, int]]]", after: "tuple[int, list[tuple[str, int]]]") -> "list[tuple[str, int]]":
    # The entries a module's history gained between two reads. It is a fixed-length window that each new code shifts by
    # one slot (a repeat of the newest spends none), so the gain is the smallest shift, within the counter's growth, that
    # lines the two reads up; a read that no shift continues (a reset in between) fails rather than guess.
    (count_before, old), (count_after, new) = before, after
    for shift in range(min(count_after - count_before, len(new)) + 1):
        if new[: len(new) - shift] == old[shift:]:
            return new[len(new) - shift :]
    raise HardwareTestFailureError(f"the history does not continue the earlier read: {old!r} -> {new!r} (counter {count_before} -> {count_after})")


def _int(counters: "JSONObject", key: str) -> int:
    value = counters.get(key)
    assert isinstance(value, int) and not isinstance(value, bool), f"UARTLINK.{key} is {value!r}, no count"
    return value


def _join_dut_hotspot_with_reverify_retry(bench: "BenchBridge", ssid: str, password: str, note: "_load.Note", *, attempts: int = _JOIN_ATTEMPTS) -> float:
    # nmcli's own rescan can miss a hotspot is_ssid_visible() just saw; at most _JOIN_ATTEMPTS joins, each retry reported
    # through `note`; remove when a round records no re-verify retry. Returns the seconds the successful join took.
    for attempt in range(1, attempts + 1):
        started = time.monotonic()
        try:
            bench.join_dut_hotspot(ssid, password, timeout_s=_JOIN_HOTSPOT_TIMEOUT_S)
        except HardwareTestFailureError as exc:
            if attempt == attempts:
                raise
            note(f"join attempt {attempt} of {ssid!r} failed ({exc}); re-verified its visibility and retried", recovery=True)
            with contextlib.suppress(TimeoutError):  # the next join's own failure or success is the real signal either way
                wait_until(lambda: bench.is_ssid_visible(ssid), timeout_s=_HOTSPOT_SCAN_TIMEOUT_S, poll_interval_s=_HOTSPOT_SCAN_POLL_S, description=f"DUT's own hotspot ({ssid!r}) to be freshly scannable again before retrying the join")
            continue
        return time.monotonic() - started
    raise HardwareTestFailureError(f"no join of {ssid!r} in {attempts} attempts")  # unreachable: the last failure re-raises


def _link_counters(host: str) -> "JSONObject | None":
    # GET /status's UARTLINK counters on a bench device wiring uart_link instances, None on one that wires none.
    if not _load.instance_loggers("uart_link"):
        return None
    sensors = _load.as_object(_load.get_object(host, "/status", _PROBE_TIMEOUT_S).get("sensors"), "GET /status sensors")
    return _load.as_object(sensors.get("UARTLINK"), "GET /status sensors.UARTLINK")


def _on_dut_hotspot(bench: "BenchBridge") -> bool:
    try:
        return bool(bench.gateway_ip())
    except HardwareTestFailureError:  # no lease: the association is gone
        return False


def _restore_hotspot_ssid(gateway_ip: str) -> None:
    # Stage 0's SSID PUT back over the DUT's hotspot, the only link left to it; refused or unreachable, it raises.
    try:
        res = http_client.fetch(gateway_ip, 80, "PUT", "/networking", {"SSID": _RECORD.original_ssid}, timeout_s=_RESTORE_PUT_TIMEOUT_S)
        word = _load.as_object(res.json().get("result"), "result").get("SSID")
    except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError) as exc:
        raise HardwareTestFailureError(f"the SSID restore over the hotspot never reached the DUT ({exc!r}) - {_STRANDED}") from exc
    if word not in ("Valid", "Unchanged"):
        raise HardwareTestFailureError(f"the SSID restore over the hotspot was refused: {res.status_code} {res.body!r} - {_STRANDED}")
    _RECORD.ssid_restored = True


def _streak_bound_s() -> float:
    # A reconnect trigger to the hotspot beaconing again, on the Wi-Fi service's own timeline: the trigger seen within one
    # refresh, its grace, the switch to STA and the settle, each failed attempt's poll and refresh, the switch back.
    fails, _window_min = _wifi_settings()
    refresh = _load.src_number(_WIFI, "_WIFI_REFRESH_S")
    switch = _load.src_number(_WIFI, "_WLAN_DOWN_SETTLE_S") + _load.src_number(_WIFI, "_WLAN_DEINIT_SETTLE_S") + _load.src_number(_WIFI, "_WLAN_MODE_SETTLE_S")
    poll = _load.src_number(_WIFI, "_STA_CONNECT_POLL_ITERS") * _load.src_number(_WIFI, "_STA_CONNECT_POLL_S")
    return refresh + _load.src_number(_WIFI, "_RECONNECT_CALLER_GRACE_S") + switch + _load.src_number(_WIFI, "_RECONNECT_SETTLE_S") + fails * (poll + refresh) + switch + _DERIVED_WAIT_MARGIN_S


def _unstrand(bench: "BenchBridge", hotspot_ssid: str, note: "_load.Note") -> None:
    # A setup that failed after stage 0's PUT: the cleared SSID is persisted, so the DUT is reached over its hotspot
    # (bounded) and the SSID put back; the bridge returns on every path, and a failure raises naming the repair.
    try:
        if not _on_dut_hotspot(bench):
            bench.ap_down()
            wait_until(lambda: bench.is_ssid_visible(hotspot_ssid), timeout_s=_HOTSPOT_SCAN_TIMEOUT_S, poll_interval_s=_HOTSPOT_SCAN_POLL_S, description=f"the DUT's hotspot ({hotspot_ssid!r}) for the SSID restore")
            _join_dut_hotspot_with_reverify_retry(bench, hotspot_ssid, hotspot_password(), note)
            wait_until(lambda: _on_dut_hotspot(bench), timeout_s=_DHCP_TIMEOUT_S, poll_interval_s=_DHCP_POLL_S, description="a lease on the DUT's hotspot for the SSID restore")
        _restore_hotspot_ssid(bench.gateway_ip())
        note("the setup failed after stage 0: the SSID was restored over the DUT's hotspot", recovery=True)
    except (OSError, http_client.HTTP_ERROR, ValueError, TypeError, AssertionError, TimeoutError, HardwareTestFailureError) as exc:
        raise HardwareTestFailureError(f"the setup failed after stage 0 and the SSID restore failed too ({exc!r}) - {_STRANDED}") from exc
    finally:
        bench.leave_dut_hotspot_and_restore_bridge()


def _wifi_log(host: str) -> "tuple[int, list[tuple[str, int]]]":
    entry = errcount_entry(get_errcount(host), "WIFI")
    return entry["counter"], [(str(h.get("type")), int(str(h.get("num", 0)))) for h in entry["history"]]


def _wifi_settings() -> "tuple[int, int]":
    # conn_fail_to_hotspot and hotspot_time_min of the device the bench runs, read from the tree as
    # harness.configured_max_connections() reads its ceiling: the waits assume the board runs this tree's build.
    with device_toml().open("rb") as f:
        settings = tomllib.load(f)["device"]
    return int(settings["conn_fail_to_hotspot"]), int(settings["hotspot_time_min"])


@pytest.fixture(scope="module")
def hotspot_ssid(board: Board, dut_ip: str) -> str:
    # The DUT's current Hostname, read over the bridge before anything flips: the SSID its hotspot will carry.
    hostname = _load.get_object(dut_ip, "/networking", _PROBE_TIMEOUT_S).get("Hostname")
    assert isinstance(hostname, str) and hostname, f"GET /networking returned no Hostname to derive the hotspot SSID from: {hostname!r}"
    return hostname


@pytest.fixture(scope="module")
def joined_hotspot(board: Board, bench: "BenchBridge", dut_ip: str, hotspot_ssid: str, session_note: "_load.SessionNote") -> "Iterator[str]":
    # Stages 0-2 in setup, stages 7-8 in teardown, module-scoped (each join or leave is a real ~15-30 s association);
    # yields the DUT's gateway IP. Its persisting writes stay unmarked: CLAUDE.md's owns-vs-reached-through rule.
    def note(text: str, *, recovery: bool = False) -> None:
        session_note(text, recovery=recovery, source="joined_hotspot")

    # Stage 0 - hotspot mode forced: the SSID it clears is read first, since the cleared one is persisted and only this
    # fixture's restore (or the flip-back test's) brings the board back.
    original_ssid = _load.get_object(dut_ip, "/networking", _PROBE_TIMEOUT_S).get("SSID")
    assert isinstance(original_ssid, str) and original_ssid, f"GET /networking returned no SSID to restore later - refusing to clear it: {original_ssid!r}"
    _RECORD.original_ssid = original_ssid
    _RECORD.link["before"] = _link_counters(dut_ip)
    res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"SSID": ""}, timeout_s=_PROBE_TIMEOUT_S)
    assert res.status_code == 200 and _load.as_object(res.json().get("result"), "result").get("SSID") == "Valid", f"PUT /networking SSID='' failed: {res.status_code} {res.body!r}"
    put_at = time.monotonic()
    try:
        # Stage 1 - association: the hotspot's beacon lags the PUT, so a real scan is polled, the radio freed for it.
        bench.ap_down()
        wait_until(lambda: bench.is_ssid_visible(hotspot_ssid), timeout_s=_HOTSPOT_SCAN_TIMEOUT_S, poll_interval_s=_HOTSPOT_SCAN_POLL_S, description=f"DUT's own hotspot ({hotspot_ssid!r}) to become scannable")
        _RECORD.seen_ssid = hotspot_ssid
        _RECORD.password = hotspot_password()
        _RECORD.associate_s = _join_dut_hotspot_with_reverify_retry(bench, hotspot_ssid, _RECORD.password, note)
        # Stage 2 - DHCP, then the first answer over the hotspot.
        wait_until(lambda: _on_dut_hotspot(bench), timeout_s=_DHCP_TIMEOUT_S, poll_interval_s=_DHCP_POLL_S, description="bench radio DHCP lease + gateway on the DUT hotspot")
        gateway_ip = bench.gateway_ip()
        wait_until(lambda: _load.serving(gateway_ip), timeout_s=_DHCP_TIMEOUT_S, poll_interval_s=_DHCP_POLL_S, description="the DUT answering over its hotspot")
        _RECORD.switch_s["to hotspot"] = time.monotonic() - put_at
        _RECORD.link["joined"] = _link_counters(gateway_ip)
    except Exception:
        _unstrand(bench, hotspot_ssid, note)
        raise

    yield gateway_ip

    if not _RECORD.flipped_back:
        _flip_back(board, bench, gateway_ip, dut_ip, note)
    assert_no_task_ended(dut_ip, "the role reversal and its flip back")  # SYSTEM is FRAM-backed: a reset keeps it
