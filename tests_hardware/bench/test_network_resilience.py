"""Bench-tier automated tests, gap fix found via a direct project-owner audit question about
networking robustness against the real API/website/internals: real WiFi outage/flap while already
connected, real NTP/DNS servers answering with garbage instead of being merely unreachable
(BACKLOG.md's open question #5), the real webserver's own max_connections=4 ceiling actually
degrading cleanly at/above that limit, real GET/PUT nonsense requests over the *normal* network (the
pre-existing malformed-request check in test_hotspot_role_reversal.py is hotspot-mode-only and
GET-only), and slowloris-style/abruptly-broken connections. See this file's own per-test docstrings
for the exact real source each design decision is grounded against.

Deliberately NOT covered here, and why: DHCP flakiness/slowness/rubbish responses. The DUT's DHCP
*client* behavior is entirely inside MicroPython's own lwIP network stack (no project code of this
repo's own runs it - confirmed by there being no DHCP-handling code anywhere in src/), so it's the
same "outside this project's own code, real backstop elsewhere" bucket CLAUDE.md already places
I2C-bus-wedge recovery in. Unlike ap_down()/ap_up() (fully reversible via nmcli in seconds) or the
UDP-port redirects below (a plain iptables rule, trivially removed), the bench bridge's own DHCP
server is NetworkManager's managed dnsmasq instance with no exposed per-request delay/corruption
knob - standing up a custom rogue DHCP responder to fake one risks leaving the DUT without any valid
lease at all, in a way nothing in this tier could then recover from short of physical intervention
(unlike the hotspot role-reversal scenario's own disclosed permanent-WLAN-deactivation risk, which
at least clears with a plain hard_reset()). Flagged as a deliberate scope decision, not silently
skipped."""

from __future__ import annotations

import socket
import time

import http_client
from bench_control import BenchBridge
from error_log_helpers import (
    assert_module_error_log_contains,
    assert_module_error_log_empty,
    get_errcount,
    reset_all_error_logs,
)
from harness import Board, wait_until
from rogue_udp_responder import RogueUdpResponder

# ---------------------------------------------------------------------------
# WiFi outage / flap while already in a real, established STA connection.
#
# Grounded against src/asy_wifi_service.py's own _on_sta_disconnected(): once _conn_phase is
# _PHASE_STA_ESTABLISHED (which it necessarily already is here - the dut_ip fixture only ever
# returns once a real STA connection was reached), a disconnect takes the "retrying previously
# successful connection in one minute" branch - a plain 60s-interval retry loop that never
# increments connection_failures and never reaches the hotspot-fallback path at all. This is a
# structurally different, safer branch than the "never-yet-connected" one HARDWARE_TEST_PLAN.md
# §11's role-reversal scenario exercises - confirmed directly, not assumed, before designing these
# two tests around it (an outage this size could otherwise have risked tripping that scenario's own
# disclosed permanent-WLAN-deactivation risk, which does not apply here).
# ---------------------------------------------------------------------------


def test_real_wifi_outage_and_recovery_while_in_normal_sta_mode(bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    bench.ap_down()
    try:
        # No assertion here that the DUT notices within any particular window - the real behavior
        # (per asy_wifi_service.py above) is a 60s retry cadence with no upper bound on how long the
        # outage itself lasts, so a brief outage is a fully realistic, low-risk window to inject.
        time.sleep(15.0)
    finally:
        bench.ap_up()

    # The 60s retry cadence means a real reconnect can take a while - generous relative to that,
    # not a guess. dut_ip's own fixture-level polling already validates this same signal shape.
    wait_until(
        lambda: _sta_reconnected(dut_ip),
        timeout_s=150.0,
        poll_interval_s=5.0,
        description="DUT to re-establish its real STA connection after the bridge AP comes back up",
    )
    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after a real WiFi outage and recovery"
    # _on_sta_disconnected()'s ESTABLISHED branch (see this section's own docstring) calls only
    # pr.evt() - never err_s()/wrn_s() - so a real outage-and-recovery this size is expected to
    # leave WIFI's own error/warning log completely untouched, not just "no crash".
    assert_module_error_log_empty(dut_ip, "WIFI")


def test_real_wifi_flaps_repeatedly_without_wedging_the_system(bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    for _cycle in range(3):
        bench.ap_down()
        time.sleep(3.0)  # short relative to the 60s retry cadence above - the DUT is still mid-wait, not yet retrying
        bench.ap_up()
        time.sleep(3.0)

    wait_until(
        lambda: _sta_reconnected(dut_ip),
        timeout_s=150.0,
        poll_interval_s=5.0,
        description="DUT to re-establish its real STA connection after repeated AP flapping",
    )
    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after repeated real WiFi flapping"
    assert_module_error_log_empty(dut_ip, "WIFI")  # same reasoning as the single-outage test above


def _sta_reconnected(dut_ip: str) -> bool:
    try:
        return http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=5.0).status_code == 200
    except OSError:
        return False


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
            board.hard_reset()  # forces a fresh NTP sync attempt against the now-rogue server
            lines = board.tail_log(duration_s=90.0)  # generous relative to asy_ntp_client.py's own retry/backoff budget
        finally:
            bench.clear_udp_port_redirect(123, _ROGUE_LOCAL_PORT_NTP)

    joined = "\n".join(lines)
    crash_markers = [ln for ln in lines if "Traceback" in ln]
    assert not crash_markers, "a garbage NTP response crashed the system instead of being rejected cleanly:\n" + "\n".join(crash_markers)
    assert "CFGMGR_" in joined or "FRAM" in joined, f"system did not appear to finish booting with a garbage-answering NTP server:\n{joined}"

    wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again after the hard_reset() above")
    # asy_ntp_client.py's own _parse_ntp_reply(): a too-short/unparseable reply lands in the
    # `except (IndexError, OverflowError, ValueError, OSError)` branch - "Malformed NTP response,
    # treating as no response:", errno=15 - confirmed directly against that method's own source,
    # not assumed. "NTP" is asy_ntp_client.py's own _NAME.
    try:
        assert_module_error_log_contains(dut_ip, "NTP", 15, "E")
    finally:
        reset_all_error_logs(dut_ip)  # never leave a deliberately-provoked fault in the live error history


def test_dns_server_sends_garbage_instead_of_a_valid_response(board: Board, bench: BenchBridge, dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    with RogueUdpResponder(_ROGUE_LOCAL_PORT_DNS, _GARBAGE_PAYLOAD):
        bench.redirect_udp_port_to_local(53, _ROGUE_LOCAL_PORT_DNS)
        try:
            board.hard_reset()  # forces a fresh DNS resolution attempt against the now-rogue server
            lines = board.tail_log(duration_s=90.0)
        finally:
            bench.clear_udp_port_redirect(53, _ROGUE_LOCAL_PORT_DNS)

    joined = "\n".join(lines)
    crash_markers = [ln for ln in lines if "Traceback" in ln]
    assert not crash_markers, "a garbage DNS response crashed the system instead of being rejected cleanly:\n" + "\n".join(crash_markers)
    assert "CFGMGR_" in joined or "FRAM" in joined, f"system did not appear to finish booting with a garbage-answering DNS server:\n{joined}"

    wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable over REST again after the hard_reset() above")
    # There is no standalone DNS-client error log to check: asy_dns_client.py's resolve_ipv4() is a
    # plain function (no PrintLogHistory of its own), called directly from asy_ntp_client.py's
    # _resolve_ntp_server() - confirmed directly. A garbage DNS reply fails _parse_response()'s own
    # sanity checks (too short/wrong transaction ID/QR unset) the same as no reply at all, so
    # resolve_ipv4() exhausts every server (including the real 8.8.8.8/1.1.1.1 fallbacks - this
    # redirect matches on --dport 53 regardless of destination, so those are caught too) and returns
    # None, landing on "NTP" module's own errno=12 ("No valid NTP server") - not a garbage-specific
    # code, since resolve_ipv4() itself never distinguishes "no answer" from "answer I can't parse".
    try:
        assert_module_error_log_contains(dut_ip, "NTP", 12, "E")
    finally:
        reset_all_error_logs(dut_ip)


# ---------------------------------------------------------------------------
# The real webserver connection ceiling (asy_webserver_service.py's WebserverService(max_connections=4),
# one slot of margin below the confirmed lwIP MEMP_NUM_TCP_PCB=5 rp2-port ceiling) actually degrades
# cleanly at and above the limit - not just under light concurrency (test_end_to_end_timing.py's own
# 8-client burst test never holds connections open long enough to occupy more than a couple of real
# slots at once, since every response completes and closes almost immediately).
#
# _open_conns is incremented the instant a TCP connection is accepted (_serve()'s own first line,
# before any byte is read) - a bare connect() with nothing sent yet already occupies a real slot,
# which is what lets this test hold exactly 4 slots open deterministically.
# ---------------------------------------------------------------------------

_MAX_CONNECTIONS = 4


def test_connections_at_and_above_the_real_socket_limit_degrade_cleanly(dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    held: list[socket.socket] = []
    extra: socket.socket | None = None
    try:
        for _ in range(_MAX_CONNECTIONS):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((dut_ip, 80))
            held.append(sock)
        time.sleep(0.5)  # let the server-side accept loop actually process each connection - well
        # under per_call_timeout_s=5.0, so none of the held connections is reclaimed before the check below

        extra = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        extra.settimeout(10.0)
        # A bare connect() can still succeed at the TCP/kernel level (the accept queue) even though
        # the real server-side _serve() task rejects it as soon as its own task runs - reject-when-
        # full closes the writer without ever composing a response (asy_webserver_service.py's own
        # _serve(): "silently close, no accept, no response ever written").
        extra.connect((dut_ip, 80))
        response = extra.recv(4096)
        assert response == b"", f"a connection above the real {_MAX_CONNECTIONS}-connection ceiling was not rejected: got {response!r}"
    finally:
        for sock in held:
            sock.close()
        if extra is not None:
            extra.close()

    # Once the held connections release their slots, the server must serve normally again.
    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after the connection-limit burst cleared"
    # _serve()'s own reject-when-full branch (confirmed directly): "silently close, no accept, no
    # response ever written" - no pr.err_s()/wrn_s() call anywhere on that path, so a real rejection
    # at the connection ceiling is expected to leave WEBSERVER's own error/warning log untouched.
    assert_module_error_log_empty(dut_ip, "WEBSERVER")


# ---------------------------------------------------------------------------
# Nonsense GET/PUT requests over the *normal* network (the pre-existing malformed-request check in
# test_hotspot_role_reversal.py is hotspot-mode-only, GET-only, and doesn't assert response shape).
# Grounded against asy_webserver_service.py's own _body_as_dict()/_ERROR_SHAPES/_shaped_error_handler
# and base_classes.py's _set_dict_cfg() - see this module's own docstring for the exact envelope
# each case below produces. None of these mutate any real persisted config: a schema-rejected field
# is marked "Invalid" and never reaches ConfigManager.write_config() at all (base_classes.py's own
# `if results.get(key) != "Valid": continue` push-callback gate).
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

    # config_manager.py's own write_config(): a type/range-rejected key logs "- Type / range error
    # in <key> - skipping!", errno=12, on *that module's own* "CFGMGR_<NAME>" logger (confirmed
    # directly) - a separate registration from "BMP3XX" itself (asy_webserver_service.py's own
    # _collect_error_sources() registers both bmp_reader and bmp_reader.cfgmgr independently).
    # Always in-RAM only (ConfigManager's own PrintLogHistory(name=...) never takes fram=), but
    # still real and REST-visible while the system is running, which is all this checks.
    try:
        errcount = get_errcount(dut_ip)
        cfgmgr_entry = errcount.get("CFGMGR_BMP3XX", {})
        assert cfgmgr_entry.get("counter") == 2, f"expected exactly 2 type/range validation errors on CFGMGR_BMP3XX (one per rejected field), got: {cfgmgr_entry!r}"
        assert_module_error_log_contains(dut_ip, "CFGMGR_BMP3XX", 12, "E")
    finally:
        reset_all_error_logs(dut_ip)


# ---------------------------------------------------------------------------
# Stale/slowloris-paced/abruptly-broken connections. Grounded against asy_webserver_service.py's
# own _serve(): the outer asyncio.wait_for(..., outer_cap_s) (production default 15.0s, confirmed
# not overridden by sensortask_wozi.py's own WebserverService() call) is specifically what bounds a
# Slowloris-paced client that never completes its own request - see that method's own comment on
# the asyncio.TimeoutError branch.
# ---------------------------------------------------------------------------


def test_slowloris_style_partial_request_is_reclaimed_by_the_outer_timeout(dut_ip: str) -> None:
    reset_all_error_logs(dut_ip)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(30.0)  # generous relative to production's own outer_cap_s=15.0
        sock.connect((dut_ip, 80))
        sock.sendall(b"GET /status HTTP/1.1\r\nHost: x\r\n")
        # A genuine Slowloris pace, not a single long stall: asy_webserver_service.py's own
        # _TimeoutStreamProxy (confirmed directly, its own module comment) wraps each individual
        # readline() in its own per_call_timeout_s=5.0 wait_for - a single stall over 5s hits *that*
        # timeout first, which Microdot's own handle_request() silently absorbs and recovers from by
        # writing its own ordinary response (a genuinely different, separately-real outcome, not
        # what this test means to exercise). Trickling one extra header line every 3s instead keeps
        # every individual readline() well under 5s each, while the cumulative time across 6 of them
        # (18s) exceeds outer_cap_s=15.0 - this is what actually reaches the *outer*
        # asyncio.wait_for(handle_request(...), outer_cap_s) backstop, exactly the "Slowloris-paced
        # client no single per-call timeout alone would catch" case that mechanism's own comment names.
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
    # _serve()'s own `except asyncio.TimeoutError as e: await self.pr.wrn_s("Connection reclaimed
    # (timed out):", e, wrnno=2)` (confirmed directly) - the outer wait_for(outer_cap_s) itself
    # timing out. Same wrnno as _TimeoutStreamProxy._bounded()'s own per-call-timeout log call, by
    # coincidence of both sharing wrnno=2 - not load-bearing for this test either way, since this
    # design specifically avoids ever triggering the per-call path at all.
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
    # No hard assertion on WEBSERVER's error log here, deliberately: _serve()'s own `except OSError
    # as e: await self.pr.wrn_s("Connection reclaimed (socket error):", e, wrnno=3)` (confirmed
    # directly) is the real path a broken-pipe write would land on, but whether the server is still
    # mid-write when this RST actually lands is a genuine timing race, not a deterministic outcome -
    # /measurements is small enough that the DUT may well have already finished writing and closed
    # cleanly on its own before the RST arrives, in which case wrnno=3 legitimately never fires. Not
    # asserted either way to avoid a flaky test; the reachability check above is this test's real
    # assertion, matching the same "no error/warning" outcome if the race goes that way.
    reset_all_error_logs(dut_ip)  # hygiene regardless of which way the race went
