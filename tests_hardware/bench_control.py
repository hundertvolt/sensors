"""Bench-host (CPython, via `nmcli`) control primitives: fault injection against the DUT's
uplink, and the role-reversal flip where the bridge's radio joins the DUT's own hotspot as a
client. Shares connection names with toolchain/setup_toolchain.py's ensure_bench_bridge().
"""

import contextlib
import re
import subprocess
from typing import TYPE_CHECKING

from harness import BENCH_AP_CONN, BENCH_ETH_CONN, HardwareNotAvailableError, HardwareTestFailureError

if TYPE_CHECKING:
    from collections.abc import Iterable

# A distinct, obviously-temporary connection name for the role-reversal client profile - never
# reused for anything else, and always torn down (nmcli connection delete) once the scenario ends,
# so a crashed test run never leaves a stray profile behind to confuse the next one.
ROLE_REVERSAL_CLIENT_CONN = "sensors-bench-dut-client-tmp"
# The comment every injected iptables rule carries: what clear_leftovers() finds and a restore proves absent.
FAULT_COMMENT = "sensors-bench-fault-injection"
# The (table, chain) pairs this module injects rules into.
_INJECTION_CHAINS = (("filter", "FORWARD"), ("nat", "PREROUTING"))
# GNU timeout's exit status when it ended the command (coreutils `timeout` manual): a capture that saw no packet.
_TIMEOUT_ENDED_EXIT = 124


# @tunable l4.bench_control_nmcli_timeout_s = 30.0
_NMCLI_TIMEOUT_S = 30.0
# @tunable l4.bench_control_nmcli_short_timeout_s = 15.0
_NMCLI_SHORT_TIMEOUT_S = 15.0
# @tunable l4.bench_control_cmd_timeout_s = 10.0
_CMD_TIMEOUT_S = 10.0
# @tunable l4.bench_control_udp_capture_timeout_s = 55.0
_UDP_CAPTURE_TIMEOUT_S = 55.0
# @tunable l4.bench_control_join_hotspot_timeout_s = 30.0
_JOIN_HOTSPOT_TIMEOUT_S = 30.0
# @tunable l4.bench_control_tcpdump_timeout_s = 60
_TCPDUMP_TIMEOUT_S = 60
# @tunable l4.bench_control_capture_wait_floor_s = 5.0
_CAPTURE_WAIT_FLOOR_S = 5.0


def _delete_rule(table: str, chain: str, spec: "list[str]", what: str) -> None:
    # iptables -D of one rule; a failed -D passes only when the chain's listing proves no rule of this project's
    # comment and this port is left. The listing failing (sudo, the tool) or the rule still there raises, named.
    proc = _run(["sudo", "iptables", *_table_args(table), "-D", chain, *spec])
    if proc.returncode == 0:
        return
    left = [rule for rule in _listed_rules(table, chain) if f"--comment {FAULT_COMMENT}" in rule and what in f"{rule} "]
    if left:
        raise HardwareTestFailureError(f"restore left a {chain} rule in place: {left[0]} (iptables -D failed: {proc.stderr.strip()})")


class BenchBridge:
    def __init__(self, ap_conn: str = BENCH_AP_CONN, eth_conn: str = BENCH_ETH_CONN) -> None:
        self.ap_conn = ap_conn
        self.eth_conn = eth_conn

    def _ap_active(self) -> bool:
        return self.ap_conn in _nmcli("-t", "-f", "NAME", "connection", "show", "--active", timeout_s=_NMCLI_SHORT_TIMEOUT_S).splitlines()

    def is_configured(self) -> bool:
        try:
            out = _nmcli("-t", "-f", "NAME", "connection", "show", timeout_s=_NMCLI_SHORT_TIMEOUT_S)
        except (HardwareNotAvailableError, HardwareTestFailureError):
            return False
        return self.ap_conn in out.splitlines()

    def is_ssid_visible(self, ssid: str) -> bool:
        # A real, fresh (`--rescan yes`) scan for `ssid` on the AP radio - confirms a DUT-hosted hotspot is beaconing
        # before joining it. Requires ap_down() first: the single radio cannot scan while it hosts the AP, so a call
        # with the AP up raises rather than scanning.
        if self._ap_active():
            raise HardwareTestFailureError("is_ssid_visible() called while the bench AP is up - the single radio cannot scan")
        iface = self.wifi_iface()
        output = _nmcli("-t", "-f", "SSID", "device", "wifi", "list", "ifname", iface, "--rescan", "yes", timeout_s=_NMCLI_SHORT_TIMEOUT_S)
        return ssid in output.splitlines()

    def ap_down(self) -> None:
        # Workaround: nmcli's "connection down" errors on an inactive connection ("is not an active connection");
        # that one error is taken as already down, once per call. Remove if nmcli makes down idempotent.
        try:
            _nmcli("connection", "down", self.ap_conn)
        except HardwareTestFailureError as e:
            if "is not an active connection" not in str(e):
                raise

    # -- fault injection: attacking the DUT's *uplink* (the bridge is the AP the DUT connects to) --

    def ap_password(self) -> str:
        # The real, current WPA2 PSK for this bridge's AP - needs `--show-secrets` (nmcli
        # withholds it otherwise, even as root; ap_ssid()'s plain `-g` query doesn't need this).
        # Lets conftest.py's `dut_ip` fixture recover stale DUT WiFi credentials automatically.
        return _nmcli("--show-secrets", "--escape", "no", "-g", "802-11-wireless-security.psk", "connection", "show", self.ap_conn).strip()

    def ap_ssid(self) -> str:
        # Workaround: nmcli -g escapes ':' as '\:', so an SSID/PSK holding one would reach the DUT with stray
        # backslashes; `--escape no` on every SSID/PSK read, nothing else. Remove if nmcli -g stops escaping.
        return _nmcli("--escape", "no", "-g", "802-11-wireless.ssid", "connection", "show", self.ap_conn).strip()

    def ap_up(self) -> None:
        # An AP already active is left alone: `connection up` on an active profile re-activates it, dropping every
        # station on it, the DUT included.
        if not self._ap_active():
            _nmcli("connection", "up", self.ap_conn)

    def block_udp_ports(self, ports: "Iterable[int]", comment: str = FAULT_COMMENT) -> None:
        # Scoped, temporary iptables DROP rules on the bridge's FORWARD chain for the given UDP destination ports (53
        # DNS, 123 NTP): unreachable servers without touching the DUT's flash. Paired with unblock_udp_ports().
        for port in ports:
            _run_iptables(["-A", "FORWARD", "-p", "udp", "--dport", str(port), "-j", "DROP", "-m", "comment", "--comment", comment])

    def block_udp_ports_from(self, ports: "Iterable[int]", comment: str = FAULT_COMMENT) -> None:
        # Holds a real server's reply back: DROPs forwarded UDP whose SOURCE port is in `ports` (123: an NTP reply), so
        # a spoof sent meanwhile is the only answer the DUT's waiting socket gets. Paired with unblock_udp_ports_from().
        for port in ports:
            _run_iptables(["-A", "FORWARD", "-p", "udp", "--sport", str(port), "-j", "DROP", "-m", "comment", "--comment", comment])

    def clear_leftovers(self) -> "list[str]":
        # A killed earlier run's network state, removed and reported one line each: every iptables rule carrying
        # FAULT_COMMENT, a netem root qdisc on the AP radio, the role-reversal profile, a down AP. Network state only -
        # never a log or an archive, never BENCH_BRIDGE_CONN/BENCH_ETH_CONN (the host's own access path).
        removed = []
        for table, chain in _INJECTION_CHAINS:
            for rule in _listed_rules(table, chain):
                if f"--comment {FAULT_COMMENT}" in rule:
                    _run_iptables([*_table_args(table), "-D", *rule.split()[1:]])
                    removed.append(f"iptables {' '.join([*_table_args(table), rule])}")
        iface = self.wifi_iface()
        if "netem" in _qdisc_listing(iface):
            _run_tc(["qdisc", "del", "dev", iface, "root"])
            removed.append(f"tc: netem root qdisc on {iface}")
        if ROLE_REVERSAL_CLIENT_CONN in _nmcli("-t", "-f", "NAME", "connection", "show", timeout_s=_NMCLI_SHORT_TIMEOUT_S).splitlines():
            _nmcli("connection", "delete", ROLE_REVERSAL_CLIENT_CONN)
            removed.append(f"nmcli: profile {ROLE_REVERSAL_CLIENT_CONN}")
        if not self._ap_active():
            self.ap_up()
            removed.append(f"nmcli: {self.ap_conn} was down, brought up")
        return removed

    def clear_network_degradation(self) -> None:
        # Reverts to the interface's own default qdisc; safe when inject_network_degradation() was never reached, since
        # a failed del passes only once `tc qdisc show` proves no netem is left.
        iface = self.wifi_iface()
        proc = _run(["sudo", "tc", "qdisc", "del", "dev", iface, "root"])
        if proc.returncode != 0 and "netem" in _qdisc_listing(iface):
            raise HardwareTestFailureError(f"restore left a netem qdisc on {iface}: tc qdisc del failed ({proc.stderr.strip()})")

    def clear_udp_port_redirect(self, port: int, local_port: int, comment: str = FAULT_COMMENT) -> None:
        # Safe when redirect_udp_port_to_local() was never reached, absence proven as unblock_udp_ports() proves it.
        _delete_rule("nat", "PREROUTING", ["-p", "udp", "--dport", str(port), "-j", "DNAT", "--to-destination", f"127.0.0.1:{local_port}", "-m", "comment", "--comment", comment], f"--dport {port} ")

    def gateway_ip(self, iface: str | None = None) -> str:
        # The DUT's own IP as seen by the bench radio while it's a client of the DUT's hotspot -
        # the address every stage-3+ REST/DNS check talks to. IP4.GATEWAY is a plain address, not
        # CIDR-suffixed, so no `.split("/")` is needed here.
        iface = iface or self.wifi_iface()
        out = _nmcli("-g", "IP4.GATEWAY", "device", "show", iface).strip()
        if not out:
            raise HardwareTestFailureError(f"{iface} has no IPv4 gateway - DHCP lease not (yet) obtained")
        return out

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
        # Real packet loss/latency/corruption/duplication/reordering via `tc netem` on
        # `wifi_iface()` only (doesn't affect eth0/br0). Uses `qdisc replace`, not `add` - a second
        # call replaces prior impairments rather than stacking with them.
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

    def join_dut_hotspot(self, ssid: str, password: str, *, timeout_s: float = _JOIN_HOTSPOT_TIMEOUT_S) -> None:
        # Stops hosting `br0-wifi-ap` and joins the DUT's own hotspot as a client, via a fresh
        # temporary connection profile bound to the same radio. Deletes any leftover profile of the
        # same name first - a stale one makes a retry fail more confusingly (see tests_hardware/README.md).
        iface = self.wifi_iface()
        self.ap_down()
        with contextlib.suppress(HardwareTestFailureError):  # no leftover profile from an earlier call - nothing to clean up
            _nmcli("connection", "delete", ROLE_REVERSAL_CLIENT_CONN)
        _nmcli(
            "device", "wifi", "connect", ssid, "password", password,
            "ifname", iface, "name", ROLE_REVERSAL_CLIENT_CONN,
            timeout_s=timeout_s,
        )

    def kick_all_stations(self) -> None:
        # kick_client()'s workaround for every station associated now, not an assumed single DUT MAC; called right
        # before a reset that expects a genuine STA reconnect (harness.kick_then_reset()).
        iface = self.wifi_iface()
        for mac in bench_associated_station_macs(iface):
            self.kick_client(mac)

    def kick_client(self, mac_address: str) -> None:
        # Workaround: a stale AP-side station entry survives the DUT's reset and blocks its reassociation
        # (tests_hardware/README.md traps); one `iw station del` per station before each reset. Remove when a round
        # records no stale-entry reconnect failure.
        iface = self.wifi_iface()
        proc = subprocess.run(["sudo", "iw", "dev", iface, "station", "del", mac_address], capture_output=True, text=True, timeout=_CMD_TIMEOUT_S, check=False)
        if proc.returncode != 0:
            raise HardwareTestFailureError(f"iw dev {iface} station del {mac_address} failed: {proc.stderr.strip()}")

    def leave_dut_hotspot(self) -> None:
        # Deletes the temporary client profile and leaves the AP down, for a stage the DUT must not rejoin the bridge
        # in. A failed delete passes only once the profile listing proves it gone (never joined, or already dropped).
        try:
            _nmcli("connection", "delete", ROLE_REVERSAL_CLIENT_CONN)
        except HardwareTestFailureError as e:
            if ROLE_REVERSAL_CLIENT_CONN in _nmcli("-t", "-f", "NAME", "connection", "show", timeout_s=_NMCLI_SHORT_TIMEOUT_S).splitlines():
                raise HardwareTestFailureError(f"{ROLE_REVERSAL_CLIENT_CONN} is still listed after its delete failed: {e}") from e

    def leave_dut_hotspot_and_restore_bridge(self) -> None:
        # leave_dut_hotspot(), then the bridge's own AP back up.
        self.leave_dut_hotspot()
        self.ap_up()

    def own_ip_on(self, iface: str | None = None) -> str:
        # The bench radio's own DHCP-leased IP while joined to the DUT's hotspot. The DUT's own
        # IP is the AP's gateway address, not derived here - see gateway_ip(). Defends against
        # nmcli's CIDR-suffixed output (e.g. "192.168.1.5/24") via `.split("/")`.
        iface = iface or self.wifi_iface()
        out = _nmcli("-g", "IP4.ADDRESS", "device", "show", iface).strip()
        if not out:
            raise HardwareTestFailureError(f"{iface} has no IPv4 address - DHCP lease not (yet) obtained")
        return out.split("/")[0].splitlines()[0]

    def read_captured_udp_source_port(self, proc: subprocess.Popen[str], timeout_s: float = _UDP_CAPTURE_TIMEOUT_S) -> int | None:
        # Blocks for the one packet line start_udp_source_capture()'s tcpdump is watching for: its `src_port`, or None
        # when `timeout` ended a capture that saw nothing. Any other failed exit (a refused sudo, a missing tcpdump or
        # interface) raises with tcpdump's own error stream.
        try:
            line = proc.stdout.readline() if proc.stdout is not None else ""
        finally:
            proc.wait(timeout=max(timeout_s, _CAPTURE_WAIT_FLOOR_S))
        if proc.returncode not in (0, _TIMEOUT_ENDED_EXIT):
            stderr = proc.stderr.read().strip() if proc.stderr is not None else ""
            raise HardwareTestFailureError(f"sudo tcpdump capture failed (exit {proc.returncode}): {stderr}")
        # e.g. "14:35:23.753510 IP 192.0.2.57.55718 > 198.51.100.123.123: NTPv3, ..." - the source token's own
        # trailing ".<port>" (tcpdump -nn's numeric host.port notation; RFC 5737 documentation addresses).
        match = re.search(r"IP\s+(\S+)\s*>", line)
        if match is None or "." not in match.group(1):
            return None
        return int(match.group(1).rsplit(".", 1)[1])

    # -- role reversal: the bridge's one radio temporarily becomes the DUT's own hotspot client --
    # Sequential flip, not simultaneous AP+client - the bench Pi4 has a single WiFi radio (owner, 2026-09-01).

    def redirect_udp_port_to_local(self, port: int, local_port: int, comment: str = FAULT_COMMENT) -> None:
        # Redirects UDP traffic for `port` to a local rogue responder on 127.0.0.1:<local_port> -
        # simulates a garbage-response server, unlike block_udp_ports()'s "silently unreachable"
        # fault (BACKLOG.md open question #5). A standard `nat` PREROUTING DNAT-to-loopback pattern.
        _run_iptables(["-t", "nat", "-A", "PREROUTING", "-p", "udp", "--dport", str(port), "-j", "DNAT", "--to-destination", f"127.0.0.1:{local_port}", "-m", "comment", "--comment", comment])

    def start_udp_source_capture(self, src_host: str, dst_port: int, iface: str | None = None) -> subprocess.Popen[str]:
        # Workaround: DNAT to 127.0.0.1 does not deliver to a local socket on this bench (route_localnet 0), so a
        # `tcpdump -c 1` reads the DUT's port instead; one capture per test. Remove if the redirect delivers locally.
        target_iface = iface or self.wifi_iface()
        return subprocess.Popen(
            ["sudo", "timeout", str(_TCPDUMP_TIMEOUT_S), "tcpdump", "-i", target_iface, "-nn", "-l", "-c", "1", "udp", "and", "src", "host", src_host, "and", "dst", "port", str(dst_port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def unblock_udp_ports(self, ports: "Iterable[int]", comment: str = FAULT_COMMENT) -> None:
        # Safe when block_udp_ports() was never reached: a -D that finds nothing passes only once the chain's listing
        # proves the rule absent (_delete_rule()).
        for port in ports:
            _delete_rule("filter", "FORWARD", ["-p", "udp", "--dport", str(port), "-j", "DROP", "-m", "comment", "--comment", comment], f"--dport {port} ")

    def unblock_udp_ports_from(self, ports: "Iterable[int]", comment: str = FAULT_COMMENT) -> None:
        for port in ports:
            _delete_rule("filter", "FORWARD", ["-p", "udp", "--sport", str(port), "-j", "DROP", "-m", "comment", "--comment", comment], f"--sport {port} ")

    def wifi_iface(self) -> str:
        # The physical WiFi adapter hosting `br0-wifi-ap`, read from the connection profile
        # itself rather than duplicating auto-detection logic (see toolchain/setup_toolchain.py's
        # detect_free_wifi_interface(), which chose it at `env --tier bench` setup time).
        out = _nmcli("-g", "connection.interface-name", "connection", "show", self.ap_conn)
        iface = out.strip()
        if not iface:
            raise HardwareTestFailureError(f"{self.ap_conn!r} has no interface-name set - was it created by ensure_bench_bridge()?")
        return iface


def _listed_rules(table: str, chain: str) -> "list[str]":
    # `iptables [-t table] -S chain`: one "-A <chain> ..." line per rule. A listing that fails raises - without it no
    # restore can prove anything absent.
    proc = _run(["sudo", "iptables", *_table_args(table), "-S", chain])
    if proc.returncode != 0:
        raise HardwareTestFailureError(f"sudo iptables {' '.join([*_table_args(table), '-S', chain])} failed (sudo rule or iptables missing?): {proc.stderr.strip()}")
    return [line for line in proc.stdout.splitlines() if line.startswith(f"-A {chain} ")]


def _nmcli(*args: str, timeout_s: float = _NMCLI_TIMEOUT_S) -> str:
    try:
        proc = subprocess.run(["sudo", "nmcli", *args], capture_output=True, text=True, timeout=timeout_s, check=False)
    except FileNotFoundError as exc:
        raise HardwareNotAvailableError(f"nmcli not on PATH: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise HardwareTestFailureError(f"nmcli {' '.join(args)} timed out after {timeout_s}s") from exc
    if proc.returncode != 0:
        raise HardwareTestFailureError(f"nmcli {' '.join(args)} failed (exit {proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout


def _qdisc_listing(iface: str) -> str:
    # The qdiscs on `iface`: every interface's listed once, its lines kept (each names its interface after the dev
    # keyword). Every interface carries a root qdisc, so none listed for it is a changed format or a wrong name.
    proc = _run(["sudo", "tc", "qdisc", "show"])
    if proc.returncode != 0:
        raise HardwareTestFailureError(f"sudo tc qdisc show failed (sudo rule or tc missing?): {proc.stderr.strip()}")
    listing = "".join(line for line in proc.stdout.splitlines(keepends=True) if f" dev {iface} " in f"{line.rstrip()} ")
    if not listing:
        raise HardwareTestFailureError(f"tc qdisc show listed no qdisc on {iface}:\n{proc.stdout}")
    return listing


def _run(argv: "list[str]") -> "subprocess.CompletedProcess[str]":
    return subprocess.run(argv, capture_output=True, text=True, timeout=_CMD_TIMEOUT_S, check=False)


def _run_iptables(args: "list[str]") -> None:
    proc = _run(["sudo", "iptables", *args])
    if proc.returncode != 0:
        raise HardwareTestFailureError(f"iptables {' '.join(args)} failed: {proc.stderr.strip()}")


def _run_tc(args: "list[str]") -> None:
    proc = _run(["sudo", "tc", *args])
    if proc.returncode != 0:
        raise HardwareTestFailureError(f"tc {' '.join(args)} failed: {proc.stderr.strip()}")


def _table_args(table: str) -> "list[str]":
    return [] if table == "filter" else ["-t", table]


def bench_associated_station_macs(iface: str) -> list[str]:
    # MAC addresses currently associated to `iface` while it's hosting the AP (`iw dev <iface>
    # station dump`) - used by kick_client() callers to find a real MAC, and to confirm the DUT's
    # own station list reflects reality.
    proc = subprocess.run(["iw", "dev", iface, "station", "dump"], capture_output=True, text=True, timeout=_CMD_TIMEOUT_S, check=False)
    if proc.returncode != 0:
        raise HardwareTestFailureError(f"iw dev {iface} station dump failed: {proc.stderr.strip()}")
    return [line.split()[1] for line in proc.stdout.splitlines() if line.startswith("Station")]
