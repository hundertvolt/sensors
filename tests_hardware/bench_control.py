"""Bench-host (CPython, via NetworkManager's `nmcli`) control primitives for the two bench-only
capability adapters HARDWARE_TEST_PLAN.md §4 calls for: real fault injection against the DUT's
*uplink* (BenchBridge's fault-injection methods) and the role-reversal flip where the bridge's one
WiFi radio temporarily becomes a *client* of the DUT's own hotspot instead (BenchBridge's
role-reversal methods, see HARDWARE_TEST_PLAN.md §11). Connection names (`br0`/`br0-eth0`/
`br0-wifi-ap`) and the idempotent-bridge assumption are shared with
toolchain/setup_toolchain.py's ensure_bench_bridge() - this module never creates or destroys that
bridge, only temporarily suspends and restores its AP leg (`br0-wifi-ap`) around a role-reversal
window, or perturbs it in place for fault injection."""

from __future__ import annotations

import re
import subprocess
import time
from collections.abc import Iterable

from harness import BENCH_AP_CONN, BENCH_ETH_CONN, HardwareNotAvailable, HardwareTestFailure

# A distinct, obviously-temporary connection name for the role-reversal client profile - never
# reused for anything else, and always torn down (nmcli connection delete) once the scenario ends,
# so a crashed test run never leaves a stray profile behind to confuse the next one.
ROLE_REVERSAL_CLIENT_CONN = "sensors-bench-dut-client-tmp"


def _nmcli(*args: str, timeout_s: float = 30.0) -> str:
    try:
        proc = subprocess.run(["sudo", "nmcli", *args], capture_output=True, text=True, timeout=timeout_s)
    except FileNotFoundError as exc:
        raise HardwareNotAvailable(f"nmcli not on PATH: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise HardwareTestFailure(f"nmcli {' '.join(args)} timed out after {timeout_s}s") from exc
    if proc.returncode != 0:
        raise HardwareTestFailure(f"nmcli {' '.join(args)} failed (exit {proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout


class BenchBridge:
    def __init__(self, ap_conn: str = BENCH_AP_CONN, eth_conn: str = BENCH_ETH_CONN) -> None:
        self.ap_conn = ap_conn
        self.eth_conn = eth_conn

    def is_configured(self) -> bool:
        try:
            out = _nmcli("-t", "-f", "NAME", "connection", "show", timeout_s=15.0)
        except (HardwareNotAvailable, HardwareTestFailure):
            return False
        return self.ap_conn in out.splitlines()

    def wifi_iface(self) -> str:
        """The physical WiFi adapter hosting `br0-wifi-ap`, read back from the connection profile
        itself rather than duplicating auto-detection logic - see toolchain/setup_toolchain.py's
        own detect_free_wifi_interface() for how it was originally chosen at `env --tier bench`
        setup time; this just asks NetworkManager what it decided."""
        out = _nmcli("-g", "connection.interface-name", "connection", "show", self.ap_conn)
        iface = out.strip()
        if not iface:
            raise HardwareTestFailure(f"{self.ap_conn!r} has no interface-name set - was it created by ensure_bench_bridge()?")
        return iface

    def ap_ssid(self) -> str:
        return _nmcli("-g", "802-11-wireless.ssid", "connection", "show", self.ap_conn).strip()

    def ap_password(self) -> str:
        """The real, current WPA2 PSK for this bridge's own AP. Unlike ap_ssid()'s plain `-g`
        query, a secrets field needs `--show-secrets` - nmcli withholds it otherwise even under
        root (confirmed directly on a real bench bridge, 2026-09-04: a plain `-g` query for this
        same field returns empty even as root; `--show-secrets` returns the real stored PSK). This
        is what lets conftest.py's `dut_ip` fixture recover a DUT with stale WiFi credentials fully
        automatically, entirely from inside a bench test run, without a human manually re-supplying
        a password that `ensure_bench_bridge()` only ever prints once, at creation time."""
        return _nmcli("--show-secrets", "-g", "802-11-wireless-security.psk", "connection", "show", self.ap_conn).strip()

    # -- fault injection: attacking the DUT's *uplink* (the bridge is the AP the DUT connects to) --

    def ap_down(self) -> None:
        # Idempotent: nmcli's own "connection down" errors ("not an active connection") if called
        # a second time while already down - a real finding from a retry loop around
        # join_dut_hotspot() (which calls this internally) needing to call ap_down() again after an
        # earlier attempt in the same loop already took it down but failed a later step.
        try:
            _nmcli("connection", "down", self.ap_conn)
        except HardwareTestFailure as e:
            if "is not an active connection" not in str(e):
                raise

    def ap_up(self) -> None:
        _nmcli("connection", "up", self.ap_conn)

    def rotate_ap_password(self, new_password: str) -> None:
        """Forces a real auth failure for any already-associated client (the DUT included) on its
        next (re)connect attempt - a genuine credential-rotation fault, not a link-down one."""
        _nmcli("connection", "modify", self.ap_conn, "wifi-sec.psk", new_password)
        _nmcli("connection", "up", self.ap_conn)

    def kick_client(self, mac_address: str) -> None:
        """Forcibly clears one associated station's table entry by MAC, via `iw` (NetworkManager's
        AP-mode backend - confirmed on this bench host to be its own internal `wpa_supplicant`, not
        a separate `hostapd` process - has no per-client kick command of its own). Syntax confirmed
        directly against real `iw 6.7`'s own `iw help` output ("dev <devname> station del <MAC
        address>").

        CONFIRMED EFFECTIVE on real hardware (a real-hardware A/B test - see tests_hardware/README.md's
        "Known assumptions and open findings"): this is the fix for the dominant real cause of this bench unit's WiFi reconnection
        flakiness - a stale AP-side station-table entry for the DUT's MAC, left over because a
        `hard_reset()` (a real power-cycle, no clean 802.11 deauth) never tells the AP the station
        is gone. 10/10 trials fell back to hotspot mode with the stale entry left in place; 10/10
        trials connected cleanly once this method cleared it first. See `kick_all_stations()` below
        for the actual call site pattern - not a clean 802.11 deauth exchange with the DUT itself
        (irrelevant here: the DUT is about to be power-cycled anyway), only a forced clear of the
        AP's own stale bookkeeping."""
        iface = self.wifi_iface()
        proc = subprocess.run(["sudo", "iw", "dev", iface, "station", "del", mac_address], capture_output=True, text=True, timeout=10.0)
        if proc.returncode != 0:
            raise HardwareTestFailure(f"iw dev {iface} station del {mac_address} failed: {proc.stderr.strip()}")

    def kick_all_stations(self) -> None:
        """Clears every currently-associated station's table entry on this bridge's own AP
        interface - the actual mitigation call site for the real WiFi-reconnection-flakiness fix
        (see kick_client()'s own docstring). Call this immediately before a real hard_reset() that
        expects the DUT to re-establish a genuine STA connection afterward. On this dedicated bench
        rig every entry is expected to be the DUT's own MAC, but this clears whatever is actually
        there rather than assuming - a second, unexpected MAC would be a real surprise worth its
        own investigation, not silently ignored."""
        iface = self.wifi_iface()
        for mac in bench_associated_station_macs(iface):
            self.kick_client(mac)

    def block_udp_ports(self, ports: Iterable[int], comment: str = "sensors-bench-fault-injection") -> None:
        """Scoped, temporary iptables DROP rules on the bridge's own OUTPUT/FORWARD chains for the
        given UDP ports (53 DNS, 123 NTP) - simulates real network jitter/loss without touching the
        DUT's flash. Always paired with unblock_udp_ports() in a test's own finally/fixture
        teardown; never left in place across tests."""
        for port in ports:
            _run_iptables(["-A", "FORWARD", "-p", "udp", "--dport", str(port), "-j", "DROP", "-m", "comment", "--comment", comment])

    def unblock_udp_ports(self, ports: Iterable[int], comment: str = "sensors-bench-fault-injection") -> None:
        for port in ports:
            # -D removes one matching rule per call - safe to call even if block_udp_ports() was
            # never actually reached (e.g. an earlier assertion in the same test failed first).
            _run_iptables(["-D", "FORWARD", "-p", "udp", "--dport", str(port), "-j", "DROP", "-m", "comment", "--comment", comment], allow_missing=True)

    def redirect_udp_port_to_local(self, port: int, local_port: int, comment: str = "sensors-bench-fault-injection") -> None:
        """Redirects UDP traffic destined for `port` (as forwarded through this bridge) to a local
        rogue responder on 127.0.0.1:<local_port> on the bench host itself, instead of letting it
        reach the real upstream server - simulates a real NTP/DNS server answering with garbage
        rather than block_udp_ports()'s own "silently unreachable" fault (BACKLOG.md's open
        question #5, "real-hardware verification gap for asy_udp_socket.py/captive_dns.py" -
        garbage-response robustness specifically, not just unreachability, had no coverage before
        rogue_udp_responder.py/this method). A standard `nat` table PREROUTING DNAT-to-loopback
        pattern.

        NEEDS VERIFICATION ON FIRST REAL RUN: unlike block_udp_ports()'s plain FORWARD-chain DROP
        (already an established, trusted pattern in this file), this session's sandbox has no
        systemd/D-Bus to run a real NetworkManager-managed bridge against and confirm this DNAT
        combination live (same caveat as own_ip_on()/gateway_ip() above). Scoped to the `nat` table
        PREROUTING chain with no interface filter, mirroring block_udp_ports()'s own "only DUT
        traffic transits this chain in practice on this dedicated bench rig" scoping assumption -
        see that method's own comment."""
        _run_iptables(["-t", "nat", "-A", "PREROUTING", "-p", "udp", "--dport", str(port), "-j", "DNAT", "--to-destination", f"127.0.0.1:{local_port}", "-m", "comment", "--comment", comment])

    def clear_udp_port_redirect(self, port: int, local_port: int, comment: str = "sensors-bench-fault-injection") -> None:
        # iptables -D matches on the exact rule spec, same as unblock_udp_ports() above - allow_missing
        # so this is always safe to call even if redirect_udp_port_to_local() was never reached.
        _run_iptables(["-t", "nat", "-D", "PREROUTING", "-p", "udp", "--dport", str(port), "-j", "DNAT", "--to-destination", f"127.0.0.1:{local_port}", "-m", "comment", "--comment", comment], allow_missing=True)

    def inject_network_degradation(
        self,
        *,
        loss_pct: float | None = None,
        delay_ms: float | None = None,
        jitter_ms: float = 0.0,
        corrupt_pct: float | None = None,
        duplicate_pct: float | None = None,
        reorder_pct: float | None = None,
    ) -> None:
        """Real packet loss/latency/corruption/duplication/reordering (`tc netem`), the genuine
        remaining gap `block_udp_ports()`/`redirect_udp_port_to_local()` above don't cover: those
        two are binary (a port is either fully reachable or fully blocked/redirected) or a wholesale
        substitution (a rogue responder's own fabricated reply) - this instead perturbs *real*
        packets on a real link, closer to actual real-world WiFi/radio conditions (see this class's
        own module-level note on the researched, real-world-grounded parameter ranges used by
        `test_network_resilience.py`'s own callers of this method). `corrupt_pct` flips a random bit
        inside an otherwise-real packet (a real radio-level bit error, distinct from a rogue
        responder's wholly fabricated payload); `duplicate_pct`/`reorder_pct` model a real
        duplicated or out-of-order UDP delivery (`reorder` needs `delay_ms` set to be meaningful per
        `man tc-netem` - without an existing delay there's nothing for a reordered packet to
        overtake). Applied to `wifi_iface()` specifically (the AP-side radio only, `wlan0` on this
        bench host) - confirmed directly, 2026-09-04: a `tc qdisc` on this interface leaves
        `eth0`/`br0` completely untouched (their own qdiscs, and this host's own outbound/SSH
        connectivity through them, are unaffected either way), the same narrow "only the DUT-facing
        radio" scoping every other fault-injection method in this class already uses. Uses `qdisc
        replace`, not `add` - `wlan0` already has a real default root qdisc (`fq_codel` on this
        host) before this ever runs, and `add` fails outright against an existing root qdisc. At
        least one impairment must be given; all may be combined in the one underlying `netem` qdisc
        (a second, unpaired `inject_*` call would silently *replace* the first's degradation, not
        stack with it - matching plain `tc` semantics, not layered like the iptables rules above)."""
        if loss_pct is None and delay_ms is None and corrupt_pct is None and duplicate_pct is None and reorder_pct is None:
            raise ValueError("inject_network_degradation() needs at least one impairment")
        netem_args = []
        if delay_ms is not None:
            netem_args += ["delay", f"{delay_ms}ms"]
            if jitter_ms:
                netem_args.append(f"{jitter_ms}ms")
        if loss_pct is not None:
            netem_args += ["loss", f"{loss_pct}%"]
        if corrupt_pct is not None:
            netem_args += ["corrupt", f"{corrupt_pct}%"]
        if duplicate_pct is not None:
            netem_args += ["duplicate", f"{duplicate_pct}%"]
        if reorder_pct is not None:
            netem_args += ["reorder", f"{reorder_pct}%"]
        iface = self.wifi_iface()
        _run_tc(["qdisc", "replace", "dev", iface, "root", "netem", *netem_args])

    def clear_network_degradation(self) -> None:
        # `qdisc del ... root` reverts the interface to its own kernel-assigned default qdisc
        # (confirmed directly: back to fq_codel on this host, byte-identical to its state before
        # inject_network_degradation() ever ran) - allow_missing so this is always safe to call even
        # if inject_network_degradation() was never reached (e.g. an earlier assertion failed first).
        iface = self.wifi_iface()
        _run_tc(["qdisc", "del", "dev", iface, "root"], allow_missing=True)

    # -- role reversal: the bridge's one radio temporarily becomes the DUT's own hotspot client --
    # See HARDWARE_TEST_PLAN.md §11.2 for why this is a sequential flip, not simultaneous AP+client
    # (the bench Rpi4 has a single WiFi radio, confirmed directly by the project owner).

    def is_ssid_visible(self, ssid: str) -> bool:
        """A real, fresh (`--rescan yes`) scan for `ssid` on the same radio `br0-wifi-ap`/
        join_dut_hotspot() use - lets a caller confirm a DUT-hosted hotspot has actually started
        beaconing before attempting to join it. REAL FINDING this exists to fix: a DUT reaching
        hotspot fallback organically (via its own real connection-failure streak, not a caller-
        forced `SSID=""`) gives no "moment zero" to sleep a fixed margin after - a join attempted
        right as the DUT's own log line announces the switch can still race
        asy_wifi_service.py's own _configure_hotspot_ap() actually bringing the radio up, failing
        with nmcli's "Wi-Fi network could not be found." Poll this (see harness.wait_until) instead
        of guessing a fixed delay.

        Requires `ap_down()` already called - this single-radio bench (HARDWARE_TEST_PLAN.md
        §11.2) can't scan for other networks while still hosting br0-wifi-ap as an AP itself, the
        same reason join_dut_hotspot() below calls ap_down() before its own connect attempt."""
        iface = self.wifi_iface()
        output = _nmcli("-t", "-f", "SSID", "device", "wifi", "list", "ifname", iface, "--rescan", "yes", timeout_s=15.0)
        return ssid in output.splitlines()

    def join_dut_hotspot(self, ssid: str, password: str, *, timeout_s: float = 30.0) -> None:
        """Stops hosting `br0-wifi-ap` and joins the DUT's own hotspot as a client instead, via a
        fresh, clearly-named temporary connection profile. `nmcli device wifi connect` handles
        scan+associate+DHCP in one call; the explicit `wifi_iface()` binds it to the same physical
        radio `br0-wifi-ap` was using, never guessing which adapter to use. Callers reaching hotspot
        mode organically (not via a self-forced `SSID=""`) should confirm is_ssid_visible() first -
        see that method's own docstring.

        REAL FINDING: idempotent against a stale profile from an earlier failed call - `nmcli
        device wifi connect ... name <same name>` doesn't always cleanly recreate an existing
        profile of that name from scratch; a profile left behind by an earlier failed attempt (e.g.
        one that failed after nmcli had already written a partial profile) can make a later retry
        fail differently and more confusingly (observed directly: "802-11-wireless-security.key-
        mgmt: property is missing" on a retry, instead of the original failure repeating) - deleting
        any leftover profile of the same name first guarantees every call starts from the same
        clean state, matching leave_dut_hotspot_and_restore_bridge()'s own tolerant delete."""
        iface = self.wifi_iface()
        self.ap_down()
        try:
            _nmcli("connection", "delete", ROLE_REVERSAL_CLIENT_CONN)
        except HardwareTestFailure:
            pass  # no leftover profile from an earlier call - fine, nothing to clean up
        _nmcli(
            "device", "wifi", "connect", ssid, "password", password,
            "ifname", iface, "name", ROLE_REVERSAL_CLIENT_CONN,
            timeout_s=timeout_s,
        )

    def own_ip_on(self, iface: str | None = None) -> str:
        """The bench radio's own DHCP-leased IP while joined to the DUT's hotspot - confirms stage 2
        of HARDWARE_TEST_PLAN.md §11.4 (a real lease was actually obtained), and is also how the
        harness would reach the DUT's own webserver during stages 3-6 (the DUT's own IP is the AP's
        gateway address, not derived from this call - see gateway_ip()).

        NEEDS VERIFICATION ON FIRST REAL RUN: `nmcli -g IP4.ADDRESS device show <iface>`'s exact
        output shape (CIDR-suffixed, e.g. "192.168.1.5/24") is well-established, long-stable nmcli
        behavior, but this session's sandbox has no systemd/D-Bus to actually run NetworkManager
        against and confirm live (unlike `device wifi connect`'s own syntax below, verified directly
        against real `nmcli --help` output in this same session). The `.split("/")` defends against
        the CIDR suffix either way, so a wrong assumption here would show up as an outright parse
        failure, not a silent wrong value - but flagged rather than claimed fully confirmed."""
        iface = iface or self.wifi_iface()
        out = _nmcli("-g", "IP4.ADDRESS", "device", "show", iface).strip()
        if not out:
            raise HardwareTestFailure(f"{iface} has no IPv4 address - DHCP lease not (yet) obtained")
        return out.split("/")[0].splitlines()[0]

    def gateway_ip(self, iface: str | None = None) -> str:
        """The DUT's own IP as seen by the bench radio while it's a client of the DUT's hotspot -
        the address every stage-3+ REST/DNS check in HARDWARE_TEST_PLAN.md §11.5 talks to. Same
        "needs verification on first real run" caveat as own_ip_on() above - IP4.GATEWAY is not
        CIDR-suffixed (a plain address, not a subnet), so no `.split("/")` is needed here, but the
        field's exact presence/emptiness-while-no-lease behavior is equally unconfirmed live."""
        iface = iface or self.wifi_iface()
        out = _nmcli("-g", "IP4.GATEWAY", "device", "show", iface).strip()
        if not out:
            raise HardwareTestFailure(f"{iface} has no IPv4 gateway - DHCP lease not (yet) obtained")
        return out

    def leave_dut_hotspot_and_restore_bridge(self) -> None:
        """Stage 7 of HARDWARE_TEST_PLAN.md §11.4: tears down the temporary client profile and
        brings `br0-wifi-ap` back up. Deliberately tolerant of the temporary profile already being
        gone (e.g. the DUT's own reconnect_wifi() already dropped the association from its side) -
        the bridge coming back up is what matters, not whether the client side noticed first."""
        try:
            _nmcli("connection", "delete", ROLE_REVERSAL_CLIENT_CONN)
        except HardwareTestFailure:
            pass  # already gone/never came up - fine, restoring the bridge below is what matters
        self.ap_up()


def _run_iptables(args: list[str], *, allow_missing: bool = False) -> None:
    proc = subprocess.run(["sudo", "iptables", *args], capture_output=True, text=True, timeout=10.0)
    if proc.returncode != 0 and not allow_missing:
        raise HardwareTestFailure(f"iptables {' '.join(args)} failed: {proc.stderr.strip()}")


def _run_tc(args: list[str], *, allow_missing: bool = False) -> None:
    proc = subprocess.run(["sudo", "tc", *args], capture_output=True, text=True, timeout=10.0)
    if proc.returncode != 0 and not allow_missing:
        raise HardwareTestFailure(f"tc {' '.join(args)} failed: {proc.stderr.strip()}")


_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")


def is_valid_mac(value: str) -> bool:
    return bool(_MAC_RE.match(value))


def bench_associated_station_macs(iface: str) -> list[str]:
    """MAC addresses currently associated to `iface` while it's hosting the AP (`iw dev <iface>
    station dump`) - used by kick_client() callers to find a real MAC to target, and by the
    "rapid associate/disassociate churn" test (HARDWARE_TEST_PLAN.md §11.5 item 18) to confirm the
    DUT's own station list reflects reality."""
    proc = subprocess.run(["iw", "dev", iface, "station", "dump"], capture_output=True, text=True, timeout=10.0)
    if proc.returncode != 0:
        raise HardwareTestFailure(f"iw dev {iface} station dump failed: {proc.stderr.strip()}")
    return [line.split()[1] for line in proc.stdout.splitlines() if line.startswith("Station")]


def wait_for_link_local_teardown(iface: str, timeout_s: float = 10.0) -> None:
    """Best-effort settle delay after ap_down()/connection deletion - nmcli's own "down" command
    returns once the D-Bus call completes, not once the kernel has fully torn down the interface's
    IP state; a few real-world runs found the immediately-following device-wifi-connect call racy
    without this. Deliberately a bounded sleep, not a wait_until(): there's no clean boolean signal
    to poll for interface teardown completion via nmcli alone."""
    time.sleep(min(2.0, timeout_s))
