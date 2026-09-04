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
from harness import Board, HardwareTestFailure, wait_until
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

    # REAL FINDING, not fully explained by AP-side stale state alone (confirmed directly against
    # real hardware, with the project owner's own prior field observation matching): the CYW43
    # firmware appears to attempt reconnection *internally* on a real link disruption without
    # reliably surfacing that through `wlan.isconnected()`/`wlan.status()` - the only signals
    # `asy_wifi_service.py`'s own `_wlan_isconnected_or_false()` has to work with (confirmed
    # directly: it's a bare pass-through to `wlan.isconnected()`, no independent reachability
    # check anywhere in that module). Observed directly: `iw station dump` showed the DUT
    # continuously "associated: yes" with a multi-hundred-second connected-time spanning an entire
    # `ap_down()`/`ap_up()` outage, while a real `arping` probe got zero responses and the webserver
    # was genuinely unreachable - i.e. the link *looked* fine to both sides' bookkeeping while
    # actually being dead, and neither `kick_all_stations()` above nor `_on_sta_disconnected()`'s
    # own retry logic (which never fires if `isconnected()` never reports False) reliably clears it.
    # This is a real, disclosed architectural gap worth a project-owner conversation about whether
    # `asy_wifi_service.py` should add an independent reachability check - not something to fix
    # blind here.
    #
    # By project-owner direction, this test's own "recovery" isn't limited to the graceful
    # established-connection retry path: a real `hard_reset()` (a genuine chip power-cycle,
    # confirmed to reliably clear this specific CYW43-firmware characteristic) is itself an
    # accepted, real recovery mechanism in this codebase (the same standing "hardware watchdog is
    # the accepted backstop" principle CLAUDE.md already applies to a wedged I2C bus, applied here
    # to a wedged WiFi link) - so this test treats reconnecting via a fallback hard_reset() as a
    # genuine pass, not a failure, while still recording which path was actually taken so a
    # consistently-graceful vs. consistently-needs-hard_reset() pattern stays visible over time
    # rather than silently blurred together.
    recovered_via_hard_reset = False
    try:
        wait_until(
            lambda: _sta_reconnected(dut_ip),
            timeout_s=150.0,
            poll_interval_s=5.0,
            description="DUT to re-establish its real STA connection after the bridge AP comes back up",
        )
    except TimeoutError:
        recovered_via_hard_reset = True
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable again after a recovery hard_reset() (see this test's own comment)")
        print("RESULT NOTE: recovered via a fallback hard_reset() - the graceful established-connection retry did not clear this real CYW43-firmware characteristic within 150s")

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
    try:
        wait_until(
            lambda: _sta_reconnected(dut_ip),
            timeout_s=150.0,
            poll_interval_s=5.0,
            description="DUT to re-establish its real STA connection after repeated AP flapping",
        )
    except TimeoutError:
        recovered_via_hard_reset = True
        bench.kick_all_stations()
        board.hard_reset()
        wait_until(lambda: _sta_reconnected(dut_ip), timeout_s=60.0, poll_interval_s=3.0, description="DUT reachable again after a recovery hard_reset() (see this test's own comment)")
        print("RESULT NOTE: recovered via a fallback hard_reset() - the graceful established-connection retry did not clear this real CYW43-firmware characteristic within 150s")

    assert http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).status_code == 200, "webserver unresponsive after repeated real WiFi flapping"
    if not recovered_via_hard_reset:
        _assert_wifi_log_has_only_benign_ap_not_found_warning(dut_ip)  # same reasoning as the single-outage test above


def _assert_wifi_log_has_only_benign_ap_not_found_warning(dut_ip: str) -> None:
    """REAL FINDING, fixed 2026-09-04: both WiFi-outage tests above used to assert the WIFI error/
    warning log stays completely empty after a graceful (non-hard_reset()) recovery, reasoning that
    `_on_sta_disconnected()`'s ESTABLISHED branch (see either test's own docstring) calls only
    `pr.evt()` - true, but that's only ONE of the paths a real outage can take. `_run_sta_mode()`'s
    own outer loop (`wifi_refresh_sec`=5s cadence) calls `_attempt_sta_connect()` ->
    `_poll_sta_connect_status()` independently of that 60s sleep whenever a poll happens to observe
    `isconnected()` as False - and if that active retry's own 5s sub-poll window lands while the
    real AP is still down, `wlan.status()` genuinely returns `STAT_NO_AP_FOUND`, correctly logging
    `wrn_s("WLAN access point not found", wrnno=5)` (confirmed directly against real source,
    src/asy_wifi_service.py's `_poll_sta_connect_status()`). Confirmed on real hardware: a genuine
    15s outage reliably produced exactly this one warning even on a fully graceful recovery - a
    correct, accurate report of a real transient condition, not a bug. Tolerate that one specific
    warning; anything else (any error, or a different warning) still fails this check."""
    entry = get_errcount(dut_ip).get("WIFI", {})
    history = entry.get("history", [])
    # "N" entries are print_log.py's own "nothing recorded" padding (get_log()'s own encoding) -
    # always present, filling out the fixed-size ring, and not a real log line at all.
    unexpected = [h for h in history if h.get("type") not in ("N",) and not (h.get("type") == "W" and h.get("num") == 5)]
    assert not unexpected, f"WIFI error log had unexpected entries beyond the known-benign wrnno=5: {unexpected!r} (full: {entry!r})"


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
            bench.kick_all_stations()  # see conftest.py's dut_ip docstring for the full finding
            board.hard_reset()  # forces a fresh NTP sync attempt against the now-rogue server
            lines = board.tail_log(duration_s=90.0)  # generous relative to asy_ntp_client.py's own retry/backoff budget
        finally:
            bench.clear_udp_port_redirect(123, _ROGUE_LOCAL_PORT_NTP)

    joined = "\n".join(lines)
    crash_markers = [ln for ln in lines if "Traceback" in ln]
    assert not crash_markers, "a garbage NTP response crashed the system instead of being rejected cleanly:\n" + "\n".join(crash_markers)
    assert "CFGMGR_" in joined or "FRAM" in joined, f"system did not appear to finish booting with a garbage-answering NTP server:\n{joined}"
    # REAL FINDING, fixed: asy_ntp_client.py's own _parse_ntp_reply() does log "Malformed NTP
    # response, treating as no response:", errno=15 for a too-short/unparseable reply (confirmed
    # directly against that method's own source) - but checking for it via the REST /status
    # errcount history afterward is unreliable: that history is a fixed 10-entry rolling window
    # (print_log.py's PrintLogHistory), and a full 90s of continued garbage responses generates
    # many more than 10 error events (each retry also logs its own generic errno=1/2/20
    # bookkeeping - base_classes.py's shared error-counter convention, "Error counter increased
    # to"/"Maximum error count reached"/"Giving up after repeated sync failures") - confirmed
    # directly: the specific errno=15 entries get evicted by later retries within the same 90s
    # window before this test ever gets to check. The live log text captured above has no such
    # limit - checking it directly for the real, distinctive printed line is unambiguous.
    # REAL FINDING, fixed: this test's own _GARBAGE_PAYLOAD is 63 bytes - long enough for
    # _parse_ntp_reply()'s msg[40:44] transmit-timestamp slice to succeed structurally (NTP's
    # minimum packet size is 48 bytes; the malformed/too-short path needs a reply shorter than the
    # 44 bytes that slice needs), so it doesn't raise IndexError/hit the "Malformed NTP response"
    # (errno=15) branch at all - confirmed directly, on real hardware, once redirect_udp_port_to_
    # local() actually started reaching the DUT (see this file's own br_netfilter finding).
    # Instead, the arbitrary ASCII bytes landing in the timestamp field produce an out-of-range
    # value, correctly hitting "Implausible NTP time, rejecting:" (errno=14) instead - an equally
    # valid "garbage rejected cleanly" outcome, just a different validation branch than the
    # original guess assumed. _handle_ntp_sync_failure()'s own "Invalid NTP time received!" fires
    # for either branch (and for a genuine no-response timeout too), so checking for it is the
    # robust, payload-shape-independent way to confirm a real sync attempt was made and rejected -
    # not pinned to which specific validation path this particular payload happens to hit.
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
# A config-level NTP fault, not a network-level one (project-owner suggestion): with a completely
# normal, already-connected WiFi link, PUT a garbage NTP_Host via the real REST API, confirm the
# real DNS-resolution failure this causes is handled cleanly (not a crash), then PUT a real,
# sensible host back and confirm NTP actually recovers. This exercises a different code path than
# the two DNS/NTP tests above: those force a *fresh boot* (hard_reset()) with an already-bad
# server, so `_handle_ntp_sync_failure()`'s own `if await self.ntp_issynced():` guard is never
# reached (confirmed directly, that method's own module comment: the block is gated on a *re*-sync
# failure after a prior successful sync). This test starts from a real, already-synced state
# (dut_ip only ever returns once NTP has had a real chance to sync), so a bad `NTP_Host` here is a
# genuine re-sync failure - the other branch of that same guard, previously untested.
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

    # Recovery: once a real, resolvable host is configured again, the next forced resync
    # (post_asy_fct fires on this restore PUT too, per handle_set_cmd()'s "fires if ANY field in
    # this call validated" rule - already confirmed directly, HARDWARE_TEST_PLAN.md §11.6) must
    # actually succeed - checked via NtpSynced, not just "no error logged" (a sync that silently
    # never re-attempted would otherwise look identical to one that attempted and failed silently).
    #
    # REAL FINDING, fixed 2026-09-04 - this test could never pass at all, not just "flaky": NtpSynced
    # is not a field of GET /networking (that endpoint returns the config schema only - SSID/PW/
    # NTP_Host/etc.) - it's only ever exposed under GET /status's nested "networking" status object
    # (sensortask_dev.py/sensortask_wozi.py's own _networking_status(), wired in via
    # status_sources={"networking": _networking_status}). The old check read
    # `GET /networking`'s response `.get("NtpSynced")`, which is always `None` regardless of real
    # sync state, so `_synced()` could structurally never return True - every prior run of this test
    # was guaranteed to exhaust both the 30s wait and the 120s post-hard_reset() retry, no matter how
    # healthy the real WiFi/NTP link actually was. This is the exact same category of bug
    # tests_hardware/README.md's "Lesson from a since-fixed test bug" entry already documents and
    # fixed once for a sibling test's "Mode" field - never applied here until now. Confirmed directly
    # on real hardware: querying GET /status right after this exact PUT sequence showed
    # `networking.NtpSynced: true` with `NtpLastSyncAge` well under a minute - the resync mechanism
    # itself, and the real WiFi link, were both fine the whole time. The "WiFi reconnect flakiness"
    # explanation this comment used to carry (attributing the timeout to BACKLOG.md open question 6)
    # was itself a misdiagnosis built on a check that could never succeed in the first place - don't
    # re-attribute a future real, structural failure here to WiFi flakiness without first confirming
    # this fixed check is what's actually being used.
    def _synced() -> bool:
        status = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=10.0).json()
        return status.get("networking", {}).get("NtpSynced") is True

    # The hard_reset() fallback below (mirroring every other real-reboot test in this tier's own
    # bounded-retry pattern) is kept as a genuine defensive measure against a real, if rare, WiFi
    # hiccup - but its own timing (120s, and the "observed a real successful sync land at ~84s of
    # WiFi uptime" reasoning that used to justify it) was measured against the broken check above
    # and is therefore not trustworthy evidence of anything; kept as a reasonable, not
    # measurement-derived, bound. With the check now actually correct, a real resync is expected to
    # land well inside the first 30s in the overwhelming majority of runs - a run that needs this
    # fallback at all is worth a second look, not an expected/tolerated outcome.
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
# Malicious-but-schema-valid REST config value #2: a real-format SSID that no AP on this bench
# broadcasts. asy_wifi_service.py's own _VAL_SSID schema (("SSID", "str", "", 0, 32, None)) only
# bounds length, same gap as _VAL_NH's NTP_Host above - any 0-32 char string passes.
#
# Aims to stop short of the real hotspot-fallback transition (asy_wifi_service.py's
# _register_sta_connection_failure(), reached after conn_fail_to_hotspot=5 consecutive
# STAT_NO_AP_FOUND failures, ~50s at this service's own wifi_refresh_sec=5s cadence) - once the DUT
# actually switches to AP/hotspot mode its own IP changes and dut_ip stops being reachable at all,
# so this test's own value (a real STAT_NO_AP_FOUND cycle degrading gracefully: no crash, REST stays
# responsive) is already fully observable well before that.
#
# REAL FINDING: that ~50s budget is tighter than it looks and was blown at least once in practice -
# real per-attempt timing jitter (this test's own reset_all_error_logs()/PUT/GET round trips, plus
# the connect attempts themselves) can push the sequence into hotspot fallback anyway. When that
# happens, REST-restoring the original SSID over dut_ip is impossible until the DUT is reachable
# again - exactly the scenario tests_hardware/bench/test_hotspot_role_reversal.py exists to handle
# (bench temporarily joins the DUT's own hotspot) - so this test falls back to that same mechanism
# rather than assuming the happy path, matching this tier's established "a recovery path counts as
# a pass, not a failure" convention (test_network_resilience.py's own WiFi-outage tests, harness.py's
# hard_reset()-fallback pattern).
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
        # that instead, exactly like test_hotspot_role_reversal.py's own joined_hotspot fixture.
        #
        # REAL FINDING #1: unlike that fixture (which forces hotspot mode itself via SSID="" and
        # then sleeps a fixed 2s margin before joining), this path reaches hotspot mode indirectly
        # (the real connection_failures streak, ~30-50s from the garbage-SSID PUT above - this
        # test's own 15s tail_log observation above already ate into that budget) and has no
        # equivalent "moment zero" to sleep a fixed margin after - a join attempted right as
        # "Permanently no WLAN connection - activating hotspot!" is logged can race
        # asy_wifi_service.py's own _configure_hotspot_ap() actually bringing the radio up, failing
        # with nmcli's own "Wi-Fi network could not be found." Fixed by polling
        # bench.is_ssid_visible() (a real scan) with a generous budget instead of guessing a short
        # fixed delay - see that method's own docstring for the full account.
        #
        # REAL FINDING #2: everything from ap_down() through join_dut_hotspot() must be inside the
        # SAME try/finally as the rest of this branch, not just the join-and-restore steps after
        # it - confirmed directly: an earlier version left ap_down()/is_ssid_visible() outside the
        # try, so a real is_ssid_visible() timeout (finding #1, before it was fixed) raised past
        # this whole branch with the bridge AP left down and never restored, turning one flaky
        # timeout into a fully stranded bench needing manual recovery.
        try:
            bench.ap_down()  # is_ssid_visible() needs the radio free to scan - see its own docstring
            wait_until(
                lambda: bench.is_ssid_visible(original_hostname),
                timeout_s=60.0,
                poll_interval_s=2.0,
                description=f"DUT's own hotspot ({original_hostname!r}) to become scannable",
            )
            # REAL FINDING #3: is_ssid_visible() being True one moment doesn't guarantee
            # `nmcli device wifi connect`'s own internal (re)scan sees it a moment later - a
            # freshly-started AP's beacon interval means visibility can still be intermittent right
            # after it first appears. Confirmed directly: a join attempted immediately after a
            # successful is_ssid_visible() check still failed once with nmcli's "Wi-Fi network
            # could not be found." ap_down() is idempotent (see its own docstring) so retrying the
            # whole join here is safe.
            for attempt in range(3):
                try:
                    bench.join_dut_hotspot(original_hostname, _HOTSPOT_PASSWORD, timeout_s=45.0)
                    break
                except HardwareTestFailure:
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

    # REAL FINDING #4 - a genuine test bug, not a hardware issue (the whole "several-minutes-to-
    # never reconnects" saga chased at length before finding this): `GET /networking` returns ONLY
    # the WiFi settings-group's own fields (SSID/PW/Country/Hostname/NTP_Host/...) -
    # asy_webserver_service.py's own _get_networking() = _get_settings_flat("networking") iterates
    # self._settings[...] (SettingsGroup registrations) only, never the status_sources dict. "Mode"
    # is exclusively a field of `GET /status`'s nested "networking" object
    # (sensortask_wozi.py's _networking_status()), confirmed directly by querying both endpoints on
    # real hardware. An earlier version of this check called
    # `http_client.fetch(dut_ip, 80, "GET", "/networking", ...).json().get("Mode")` - a field that
    # endpoint never has - so it was unconditionally `None`, and `None == "STA"` is always False:
    # this check could never pass, regardless of how long the DUT had actually been reconnected or
    # how large a timeout was given (up to 900s tried). The DUT itself was reconnecting normally the
    # entire time - confirmed directly, repeatedly: `iw dev wlan0 station dump` and a real HTTP
    # `GET /status` both showed a long-stable, fully healthy connection immediately after this test's
    # own check had already given up and raised TimeoutError. Multiple earlier (wrong) theories
    # chased at length before finding this - a CYW43 "phantom disconnect" state, accumulated bench/
    # NetworkManager state, dut_ip fixture churn carryover - are real, separately-confirmed
    # mechanisms in general (see tests_hardware/README.md's "Known assumptions and open findings"),
    # but were not what was actually happening in this specific test; none of the "fixes" tried for them (multiple hard_reset()
    # retries, a settle delay, a full physical power-cycle of both this Pi4 and the DUT) had any
    # effect, which in hindsight makes sense since the check itself could never have passed regardless.
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
    # REAL FINDING, fixed: reset_all_error_logs()'s own PUT /status closes cleanly from the
    # client's side (urllib's `with urlopen(...)` context manager) the instant this call returns,
    # but that doesn't mean the RP2040's own single-core MicroPython asyncio has already run
    # _serve()'s finally block and decremented _open_conns for that connection yet - confirmed
    # directly: without a settle here, this test consistently (not just occasionally) fails,
    # because its own 4 "held" sockets below start from an _open_conns baseline that isn't
    # actually 0 yet, shifting every slot by one for the rest of the test (a bounded retry around
    # the "extra" connection alone - see below - can't fix this, since the 4 held sockets are
    # never reopened between attempts). A clean, timing-isolated repro of this whole sequence
    # without any reset_all_error_logs() call at all succeeded first-try, confirming this call is
    # exactly the missing settle point, not a deeper protocol-level issue.
    time.sleep(1.0)
    held: list[socket.socket] = []
    extra: socket.socket | None = None
    try:
        for _ in range(_MAX_CONNECTIONS):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            sock.connect((dut_ip, 80))
            held.append(sock)
        # REAL FINDING, fixed: a real TCP connect() completing (the kernel's own 3-way handshake)
        # does not mean the RP2040's own single-core MicroPython asyncio accept loop has already
        # run _serve() and incremented _open_conns for that connection yet - those are two
        # different events, and the second can lag under real load (WiFi driver work, sensor
        # tasks). Confirmed directly: a fixed settle isn't a reliable bound either way (0.5s and
        # 2.0s both reproduced the same failure at least once, but a clean, timing-isolated repro
        # of this exact sequence also succeeded first-try at 2.0s) - the "extra" (5th) connection
        # sometimes gets admitted into the real Microdot app layer (a genuine "400 bad request" -
        # this test never sends a valid HTTP request on it - not the expected silent reject)
        # because the accept loop hadn't caught up to all 4 held connections yet. This is a genuine
        # timing race, not a hard invariant violation, so - matching this tier's established
        # pattern for real hardware timing races elsewhere (e.g. joined_hotspot's own bounded
        # retry around join_dut_hotspot()) - a bounded retry with a fresh "extra" socket each time
        # is the principled fix, not chasing an ever-larger fixed sleep.
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
    # REAL FINDING, fixed: closing 5 real sockets near-simultaneously (this test's own finally
    # block above) can transiently reset a brand new connection attempted immediately afterward
    # (ConnectionResetError, unhandled by a bare fetch()) - the same class of real accept-loop-lag
    # timing this test already accounts for elsewhere (see the settle comments above). wait_until()
    # already treats a raising check_fn as "not yet ready, retry" per its own docstring, so this
    # gives the server a real chance to settle rather than asserting on the very next instant.
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
