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

    # -- fault injection: attacking the DUT's *uplink* (the bridge is the AP the DUT connects to) --

    def ap_down(self) -> None:
        _nmcli("connection", "down", self.ap_conn)

    def ap_up(self) -> None:
        _nmcli("connection", "up", self.ap_conn)

    def rotate_ap_password(self, new_password: str) -> None:
        """Forces a real auth failure for any already-associated client (the DUT included) on its
        next (re)connect attempt - a genuine credential-rotation fault, not a link-down one."""
        _nmcli("connection", "modify", self.ap_conn, "wifi-sec.psk", new_password)
        _nmcli("connection", "up", self.ap_conn)

    def kick_client(self, mac_address: str) -> None:
        """Best-effort deauth of one associated station by MAC, via `iw` (NetworkManager's own AP
        mode has no per-client kick command). Syntax confirmed directly against real `iw 6.7`'s own
        `iw help` output ("dev <devname> station del <MAC address>") during this session's re-audit -
        still needs verification on first real-hardware run whether the hostapd-backed AP
        NetworkManager creates actually *honors* it (see HARDWARE_TEST_PLAN.md §9's "not yet
        verified" list; the command syntax being right doesn't guarantee the effect is)."""
        iface = self.wifi_iface()
        proc = subprocess.run(["sudo", "iw", "dev", iface, "station", "del", mac_address], capture_output=True, text=True, timeout=10.0)
        if proc.returncode != 0:
            raise HardwareTestFailure(f"iw dev {iface} station del {mac_address} failed: {proc.stderr.strip()}")

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

    # -- role reversal: the bridge's one radio temporarily becomes the DUT's own hotspot client --
    # See HARDWARE_TEST_PLAN.md §11.2 for why this is a sequential flip, not simultaneous AP+client
    # (the bench Rpi4 has a single WiFi radio, confirmed directly by the project owner).

    def join_dut_hotspot(self, ssid: str, password: str, *, timeout_s: float = 30.0) -> None:
        """Stops hosting `br0-wifi-ap` and joins the DUT's own hotspot as a client instead, via a
        fresh, clearly-named temporary connection profile. `nmcli device wifi connect` handles
        scan+associate+DHCP in one call; the explicit `wifi_iface()` binds it to the same physical
        radio `br0-wifi-ap` was using, never guessing which adapter to use."""
        iface = self.wifi_iface()
        self.ap_down()
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
