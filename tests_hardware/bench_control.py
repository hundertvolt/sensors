"""Bench-host (CPython, via `nmcli`) control primitives: fault injection against the DUT's
uplink, and the role-reversal flip where the bridge's radio joins the DUT's own hotspot as a
client. Shares connection names with toolchain/setup_toolchain.py's ensure_bench_bridge().
"""

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
        """The physical WiFi adapter hosting `br0-wifi-ap`, read from the connection profile
        itself rather than duplicating auto-detection logic (see toolchain/setup_toolchain.py's
        detect_free_wifi_interface(), which chose it at `env --tier bench` setup time)."""
        out = _nmcli("-g", "connection.interface-name", "connection", "show", self.ap_conn)
        iface = out.strip()
        if not iface:
            raise HardwareTestFailure(f"{self.ap_conn!r} has no interface-name set - was it created by ensure_bench_bridge()?")
        return iface

    def ap_ssid(self) -> str:
        return _nmcli("-g", "802-11-wireless.ssid", "connection", "show", self.ap_conn).strip()

    def ap_password(self) -> str:
        """The real, current WPA2 PSK for this bridge's AP - needs `--show-secrets` (nmcli
        withholds it otherwise, even as root; ap_ssid()'s plain `-g` query doesn't need this).
        Lets conftest.py's `dut_ip` fixture recover stale DUT WiFi credentials automatically."""
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
        """Forcibly clears one associated station's table entry by MAC via `iw` (this bench's AP
        has no per-client kick command). Fixes the dominant cause of WiFi reconnection flakiness -
        a stale AP-side entry surviving a hard_reset() power-cycle (see tests_hardware/README.md)."""
        iface = self.wifi_iface()
        proc = subprocess.run(["sudo", "iw", "dev", iface, "station", "del", mac_address], capture_output=True, text=True, timeout=10.0)
        if proc.returncode != 0:
            raise HardwareTestFailure(f"iw dev {iface} station del {mac_address} failed: {proc.stderr.strip()}")

    def kick_all_stations(self) -> None:
        """Clears every currently-associated station's table entry on this AP interface - call
        immediately before a real hard_reset() that expects a genuine STA reconnect (see
        kick_client()). Clears whatever is actually there, not just an assumed single DUT MAC."""
        iface = self.wifi_iface()
        for mac in bench_associated_station_macs(iface):
            self.kick_client(mac)

    def block_udp_ports(self, ports: Iterable[int], comment: str = "sensors-bench-fault-injection") -> None:
        """Scoped, temporary iptables DROP rules on the bridge's OUTPUT/FORWARD chains for the
        given UDP ports (53 DNS, 123 NTP) - simulates network jitter/loss without touching the
        DUT's flash. Always paired with unblock_udp_ports() in a test's own teardown."""
        for port in ports:
            _run_iptables(["-A", "FORWARD", "-p", "udp", "--dport", str(port), "-j", "DROP", "-m", "comment", "--comment", comment])

    def unblock_udp_ports(self, ports: Iterable[int], comment: str = "sensors-bench-fault-injection") -> None:
        for port in ports:
            # -D removes one matching rule per call - safe to call even if block_udp_ports() was
            # never actually reached (e.g. an earlier assertion in the same test failed first).
            _run_iptables(["-D", "FORWARD", "-p", "udp", "--dport", str(port), "-j", "DROP", "-m", "comment", "--comment", comment], allow_missing=True)

    def redirect_udp_port_to_local(self, port: int, local_port: int, comment: str = "sensors-bench-fault-injection") -> None:
        """Redirects UDP traffic for `port` to a local rogue responder on 127.0.0.1:<local_port> -
        simulates a garbage-response server, unlike block_udp_ports()'s "silently unreachable"
        fault (BACKLOG.md open question #5). A standard `nat` PREROUTING DNAT-to-loopback pattern."""
        _run_iptables(["-t", "nat", "-A", "PREROUTING", "-p", "udp", "--dport", str(port), "-j", "DNAT", "--to-destination", f"127.0.0.1:{local_port}", "-m", "comment", "--comment", comment])

    def clear_udp_port_redirect(self, port: int, local_port: int, comment: str = "sensors-bench-fault-injection") -> None:
        # iptables -D matches on the exact rule spec, same as unblock_udp_ports() above - allow_missing
        # so this is always safe to call even if redirect_udp_port_to_local() was never reached.
        _run_iptables(["-t", "nat", "-D", "PREROUTING", "-p", "udp", "--dport", str(port), "-j", "DNAT", "--to-destination", f"127.0.0.1:{local_port}", "-m", "comment", "--comment", comment], allow_missing=True)

    def start_udp_source_capture(self, src_host: str, dst_port: int, iface: str | None = None) -> subprocess.Popen[str]:
        """Starts a real `tcpdump -c 1` on `iface`, filtered to the first UDP datagram from
        `src_host` to `dst_port` - works around a local-delivery gap in redirect_udp_port_to_local()
        (see tests_hardware/README.md). Pair with read_captured_udp_source_port()."""
        target_iface = iface or self.wifi_iface()
        return subprocess.Popen(
            ["sudo", "timeout", "60", "tcpdump", "-i", target_iface, "-nn", "-l", "-c", "1", "udp", "and", "src", "host", src_host, "and", "dst", "port", str(dst_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

    def read_captured_udp_source_port(self, proc: subprocess.Popen[str], timeout_s: float = 55.0) -> int | None:
        """Blocks for the one packet line start_udp_source_capture()'s tcpdump is watching for,
        returning `src_port` - or None if nothing matched within `timeout_s` (bounded either way
        by the process's own `-c 1`/`timeout 60`)."""
        try:
            line = proc.stdout.readline() if proc.stdout is not None else ""  # type: ignore[union-attr]
        finally:
            proc.wait(timeout=max(timeout_s, 5.0))
        # e.g. "14:35:23.753510 IP 192.168.85.57.55718 > 162.159.200.123.123: NTPv3, ..." - the
        # source token's own trailing ".<port>" (tcpdump -nn's own numeric host.port notation).
        match = re.search(r"IP\s+(\S+)\s*>", line)
        if match is None or "." not in match.group(1):
            return None
        return int(match.group(1).rsplit(".", 1)[1])

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
        """Real packet loss/latency/corruption/duplication/reordering via `tc netem` on
        `wifi_iface()` only (doesn't affect eth0/br0). Uses `qdisc replace`, not `add` - a second
        call replaces prior impairments rather than stacking with them."""
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
        # Reverts to the interface's own default qdisc - allow_missing so this is safe to call
        # even if inject_network_degradation() was never reached.
        iface = self.wifi_iface()
        _run_tc(["qdisc", "del", "dev", iface, "root"], allow_missing=True)

    # -- role reversal: the bridge's one radio temporarily becomes the DUT's own hotspot client --
    # Sequential flip, not simultaneous AP+client - the bench Pi4 has a single WiFi radio.

    def is_ssid_visible(self, ssid: str) -> bool:
        """A real, fresh (`--rescan yes`) scan for `ssid` on the AP radio - confirms a DUT-hosted
        hotspot is actually beaconing before joining it, instead of racing a fixed sleep. Requires
        ap_down() already called - this single-radio bench can't scan while still hosting an AP."""
        iface = self.wifi_iface()
        output = _nmcli("-t", "-f", "SSID", "device", "wifi", "list", "ifname", iface, "--rescan", "yes", timeout_s=15.0)
        return ssid in output.splitlines()

    def join_dut_hotspot(self, ssid: str, password: str, *, timeout_s: float = 30.0) -> None:
        """Stops hosting `br0-wifi-ap` and joins the DUT's own hotspot as a client, via a fresh
        temporary connection profile bound to the same radio. Deletes any leftover profile of the
        same name first - a stale one makes a retry fail more confusingly (see tests_hardware/README.md)."""
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
        """The bench radio's own DHCP-leased IP while joined to the DUT's hotspot. The DUT's own
        IP is the AP's gateway address, not derived here - see gateway_ip(). Defends against
        nmcli's CIDR-suffixed output (e.g. "192.168.1.5/24") via `.split("/")`."""
        iface = iface or self.wifi_iface()
        out = _nmcli("-g", "IP4.ADDRESS", "device", "show", iface).strip()
        if not out:
            raise HardwareTestFailure(f"{iface} has no IPv4 address - DHCP lease not (yet) obtained")
        return out.split("/")[0].splitlines()[0]

    def gateway_ip(self, iface: str | None = None) -> str:
        """The DUT's own IP as seen by the bench radio while it's a client of the DUT's hotspot -
        the address every stage-3+ REST/DNS check talks to. IP4.GATEWAY is a plain address, not
        CIDR-suffixed, so no `.split("/")` is needed here."""
        iface = iface or self.wifi_iface()
        out = _nmcli("-g", "IP4.GATEWAY", "device", "show", iface).strip()
        if not out:
            raise HardwareTestFailure(f"{iface} has no IPv4 gateway - DHCP lease not (yet) obtained")
        return out

    def leave_dut_hotspot_and_restore_bridge(self) -> None:
        """Tears down the temporary client profile and brings `br0-wifi-ap` back up. Tolerant of
        the profile already being gone (e.g. the DUT's own reconnect_wifi() already dropped the
        association) - restoring the bridge is what matters, not who noticed first."""
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
    station dump`) - used by kick_client() callers to find a real MAC, and to confirm the DUT's
    own station list reflects reality."""
    proc = subprocess.run(["iw", "dev", iface, "station", "dump"], capture_output=True, text=True, timeout=10.0)
    if proc.returncode != 0:
        raise HardwareTestFailure(f"iw dev {iface} station dump failed: {proc.stderr.strip()}")
    return [line.split()[1] for line in proc.stdout.splitlines() if line.startswith("Station")]


def wait_for_link_local_teardown(iface: str, timeout_s: float = 10.0) -> None:
    """Best-effort settle delay after ap_down()/connection deletion - nmcli's "down" completes
    once the D-Bus call returns, not once the kernel fully tears down IP state, and the
    immediately-following wifi-connect call was found racy without this."""
    time.sleep(min(2.0, timeout_s))
