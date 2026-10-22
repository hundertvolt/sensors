"""tests_hardware/bench_control.py against a scripted subprocess.run: every restore proves its injection absent by
state, a failed listing or capture raises naming the tool, a killed run's leftovers are cleared and reported, the single
radio never scans while it hosts the AP nor re-activates an active one; no module touches the host's own access path."""

import ast
import io
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

import bench_control
from bench_control import FAULT_COMMENT, ROLE_REVERSAL_CLIENT_CONN, BenchBridge
from harness import BENCH_AP_CONN, BENCH_BRIDGE_CONN, BENCH_ETH_CONN, HardwareTestFailureError

TESTS_HARDWARE = Path(__file__).resolve().parent.parent / "tests_hardware"

_RULE = f"-A FORWARD -p udp -m udp --dport 123 -m comment --comment {FAULT_COMMENT} -j DROP"
_NAT_RULE = f"-A PREROUTING -p udp -m udp --dport 53 -m comment --comment {FAULT_COMMENT} -j DNAT --to-destination 127.0.0.1:5353"
_ACCESS_NAMES = ("BENCH_BRIDGE_CONN", "BENCH_ETH_CONN", "bench_control.BENCH_ETH_CONN", "harness.BENCH_BRIDGE_CONN")


class _Capture:
    # A finished `sudo timeout ... tcpdump -c 1` process: what it printed on each stream and how it exited.
    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = returncode
        self.stderr = io.StringIO(stderr)
        self.stdout = io.StringIO(stdout)

    def wait(self, timeout: float) -> int:
        del timeout
        return self.returncode


class _Host:
    # The bench host's commands: each argv answered by the first matching rule, every argv recorded in order.
    def __init__(self, rules: "dict[str, tuple[int, str, str]]") -> None:
        self.rules = rules
        self.argvs: list[str] = []

    def __call__(self, argv: "list[str]", **kwargs: object) -> "subprocess.CompletedProcess[str]":
        line = " ".join(argv)
        self.argvs.append(line)
        for key, (code, out, err) in self.rules.items():
            if key in line:
                return subprocess.CompletedProcess(argv, code, out, err)
        return subprocess.CompletedProcess(argv, 0, "", "")


def _access_path_calls(source: str) -> "list[str]":
    # Every _nmcli(...) call handed the host's own access-path connection, by constant or by its literal name.
    names = {BENCH_BRIDGE_CONN, BENCH_ETH_CONN}
    return [
        f"line {node.lineno}: {ast.unparse(node)}"
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and ast.unparse(node.func).endswith("_nmcli")
        for arg in node.args
        if ast.unparse(arg) in _ACCESS_NAMES or (isinstance(arg, ast.Constant) and arg.value in names) or ast.unparse(arg).endswith(".eth_conn")
    ]


def test_a_failed_delete_with_the_rule_gone_is_a_clean_restore(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, host = _bridge(monkeypatch, {"-D FORWARD": (1, "", "iptables: Bad rule"), "-S FORWARD": (0, "-P FORWARD ACCEPT\n", "")})
    bridge.unblock_udp_ports([123])
    assert [a for a in host.argvs if "iptables" in a][-1].endswith("-S FORWARD")


def test_a_failed_delete_with_the_rule_still_listed_raises_naming_it(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, _host = _bridge(monkeypatch, {"-D FORWARD": (1, "", "iptables: Bad rule"), "-S FORWARD": (0, f"-P FORWARD ACCEPT\n{_RULE}\n", "")})
    with pytest.raises(HardwareTestFailureError, match=r"restore left a FORWARD rule in place: .*--dport 123"):
        bridge.unblock_udp_ports([123])


def test_a_rule_for_another_port_does_not_fail_this_ports_restore(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, _host = _bridge(monkeypatch, {"-D FORWARD": (1, "", "Bad rule"), "-S FORWARD": (0, f"{_RULE.replace('--dport 123', '--dport 1234')}\n", "")})
    bridge.unblock_udp_ports([123])


def test_a_failing_listing_raises_naming_sudo_and_the_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, _host = _bridge(monkeypatch, {"-D PREROUTING": (1, "", "Bad rule"), "-S PREROUTING": (1, "", "sudo: a password is required")})
    with pytest.raises(HardwareTestFailureError, match=r"iptables -t nat -S PREROUTING failed \(sudo rule or iptables missing\?\)"):
        bridge.clear_udp_port_redirect(53, 5353)


def test_a_netem_left_after_a_failed_delete_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, _host = _bridge(monkeypatch, {"qdisc del": (2, "", "RTNETLINK answers: Operation not permitted"), "qdisc show": (0, "qdisc noqueue 0: dev lo root refcnt 2\nqdisc netem 8001: dev wlan1 root refcnt 2 limit 1000 loss 5%\n", "")})
    with pytest.raises(HardwareTestFailureError, match="restore left a netem qdisc on wlan1"):
        bridge.clear_network_degradation()


def test_a_failed_qdisc_delete_with_no_netem_left_is_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, _host = _bridge(monkeypatch, {"qdisc del": (2, "", "Cannot delete qdisc with handle of zero"), "qdisc show": (0, "qdisc noqueue 0: dev wlan1 root refcnt 2\nqdisc netem 8001: dev wlan10 root refcnt 2 loss 5%\n", "")})
    bridge.clear_network_degradation()


def test_the_source_port_block_is_undone_and_proven_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, host = _bridge(monkeypatch, {"-D FORWARD": (1, "", "Bad rule"), "-S FORWARD": (0, f"{_RULE.replace('--dport', '--sport')}\n", "")})
    bridge.block_udp_ports_from([123])
    assert any("-A FORWARD -p udp --sport 123 -j DROP -m comment --comment " + FAULT_COMMENT in a for a in host.argvs)
    with pytest.raises(HardwareTestFailureError, match="--sport 123"):
        bridge.unblock_udp_ports_from([123])


def test_clear_leftovers_removes_only_this_projects_rules_and_reports_each(monkeypatch: pytest.MonkeyPatch) -> None:
    foreign = "-A FORWARD -p tcp -m tcp --dport 22 -j ACCEPT"
    bridge, host = _bridge(
        monkeypatch,
        {
            "-S FORWARD": (0, f"-P FORWARD ACCEPT\n{foreign}\n{_RULE}\n", ""),
            "-S PREROUTING": (0, f"-P PREROUTING ACCEPT\n{_NAT_RULE}\n", ""),
            "qdisc show": (0, "qdisc netem 8001: dev wlan1 root refcnt 2 loss 5%\n", ""),
            "show --active": (0, "br0\n", ""),
            "connection show": (0, f"br0\n{bench_control.ROLE_REVERSAL_CLIENT_CONN}\n", ""),
        },
    )
    removed = bridge.clear_leftovers()
    assert removed == [
        f"iptables {_RULE}",
        f"iptables -t nat {_NAT_RULE}",
        "tc: netem root qdisc on wlan1",
        f"nmcli: profile {bench_control.ROLE_REVERSAL_CLIENT_CONN}",
        f"nmcli: {bridge.ap_conn} was down, brought up",
    ]
    deletes = [a for a in host.argvs if " -D " in a]
    assert deletes == [f"sudo iptables -D {_RULE[3:]}", f"sudo iptables -t nat -D {_NAT_RULE[3:]}"]
    assert not any("22" in a for a in deletes) and not any(bridge.eth_conn in a for a in host.argvs)


def test_clear_leftovers_on_a_clean_host_removes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, _host = _bridge(monkeypatch, {"show --active": (0, f"{BENCH_AP_CONN}\n", ""), "connection show": (0, "br0\n", "")})
    assert bridge.clear_leftovers() == []


def test_a_scan_while_the_ap_is_up_raises_before_scanning(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, host = _bridge(monkeypatch, {"show --active": (0, f"{BENCH_AP_CONN}\n", "")})
    with pytest.raises(HardwareTestFailureError, match="while the bench AP is up - the single radio cannot scan"):
        bridge.is_ssid_visible("SensorStationX")
    assert not any("--rescan" in a for a in host.argvs)


def test_a_scan_with_the_ap_down_scans(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, _host = _bridge(monkeypatch, {"show --active": (0, "br0\n", ""), "--rescan": (0, "OtherNet\nSensorStationX\n", "")})
    assert bridge.is_ssid_visible("SensorStationX") is True


def _bridge(monkeypatch: pytest.MonkeyPatch, rules: "dict[str, tuple[int, str, str]]") -> "tuple[BenchBridge, _Host]":
    host = _Host({"interface-name": (0, "wlan1\n", ""), "qdisc show": (0, "qdisc noqueue 0: dev wlan1 root refcnt 2\n", ""), **rules})
    monkeypatch.setattr(subprocess, "run", host)
    return BenchBridge(), host


def test_the_access_path_guard_sees_a_synthetic_offender() -> None:
    assert _access_path_calls('_nmcli("connection", "down", BENCH_ETH_CONN)\n') == ["line 1: _nmcli('connection', 'down', BENCH_ETH_CONN)"]


@pytest.mark.parametrize("module", sorted(p for p in TESTS_HARDWARE.rglob("*.py") if "device_scripts" not in p.parts), ids=lambda p: str(p.relative_to(TESTS_HARDWARE)))
def test_no_hardware_module_hands_the_hosts_access_path_to_nmcli(module: Path) -> None:
    # The bridge and its ethernet slave are the session's own way in; only the installer's armed dead-man's switch may
    # touch them (CLAUDE.md), never a test.
    assert _access_path_calls(module.read_text(encoding="utf-8")) == [], module.name


def test_bringing_the_ap_up_leaves_an_active_ap_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    # `connection up` on an active profile re-activates it, dropping every station on it - the DUT included.
    bridge, host = _bridge(monkeypatch, {"show --active": (0, f"{BENCH_AP_CONN}\n", "")})
    bridge.ap_up()
    assert not any("connection up" in a for a in host.argvs), host.argvs


def test_bringing_an_inactive_ap_up_activates_it(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, host = _bridge(monkeypatch, {"show --active": (0, "br0\n", "")})
    bridge.ap_up()
    assert [a for a in host.argvs if "connection up" in a] == [f"sudo nmcli connection up {BENCH_AP_CONN}"]


def test_leaving_the_dut_hotspot_deletes_the_client_profile_and_leaves_the_ap_down(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, host = _bridge(monkeypatch, {"show --active": (0, "br0\n", "")})
    bridge.leave_dut_hotspot()
    assert f"sudo nmcli connection delete {ROLE_REVERSAL_CLIENT_CONN}" in host.argvs
    assert not any("connection up" in a for a in host.argvs), host.argvs


def test_a_failed_profile_delete_with_the_profile_gone_is_a_clean_leave(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, _host = _bridge(monkeypatch, {"connection delete": (10, "", "Error: unknown connection"), "connection show": (0, "br0\n", "")})
    bridge.leave_dut_hotspot()


def test_a_failed_profile_delete_with_the_profile_still_listed_raises_naming_it(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, _host = _bridge(monkeypatch, {"connection delete": (4, "", "Error: not authorized"), "connection show": (0, f"br0\n{ROLE_REVERSAL_CLIENT_CONN}\n", "")})
    with pytest.raises(HardwareTestFailureError, match=f"{ROLE_REVERSAL_CLIENT_CONN}.*still listed.*not authorized"):
        bridge.leave_dut_hotspot()


def test_restoring_the_bridge_after_the_hotspot_deletes_then_brings_the_inactive_ap_up(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge, host = _bridge(monkeypatch, {"show --active": (0, "br0\n", "")})
    bridge.leave_dut_hotspot_and_restore_bridge()
    steps = [a for a in host.argvs if "connection delete" in a or "connection up" in a]
    assert steps == [f"sudo nmcli connection delete {ROLE_REVERSAL_CLIENT_CONN}", f"sudo nmcli connection up {BENCH_AP_CONN}"]


def test_the_udp_capture_keeps_tcpdumps_error_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def popen(argv: "list[str]", **kwargs: object) -> _Capture:
        seen.update(kwargs, argv=argv)
        return _Capture(0, "", "")

    bridge, _host = _bridge(monkeypatch, {})
    monkeypatch.setattr(subprocess, "Popen", popen)
    bridge.start_udp_source_capture("192.0.2.57", 123)
    assert seen["stderr"] is subprocess.PIPE and seen["stdout"] is subprocess.PIPE


@pytest.mark.parametrize(("returncode", "line", "port"), [(0, "14:35:23.753510 IP 192.0.2.57.55718 > 198.51.100.123.123: NTPv3\n", 55718), (124, "", None)])
def test_a_capture_that_ran_returns_its_port_or_none_at_its_timeout(monkeypatch: pytest.MonkeyPatch, returncode: int, line: str, port: "int | None") -> None:
    bridge, _host = _bridge(monkeypatch, {})
    assert bridge.read_captured_udp_source_port(_Capture(returncode, line, "listening on wlan1\n"), timeout_s=1.0) == port  # type: ignore[arg-type]


@pytest.mark.parametrize(("returncode", "stderr"), [(1, "sudo: a password is required"), (127, "sudo: tcpdump: command not found"), (1, "tcpdump: wlan1: No such device exists")])
def test_a_capture_that_never_started_raises_naming_tcpdump_and_why(monkeypatch: pytest.MonkeyPatch, returncode: int, stderr: str) -> None:
    # A refused sudo or a missing tcpdump reads as "nothing captured" unless its exit and error stream are read.
    bridge, _host = _bridge(monkeypatch, {})
    with pytest.raises(HardwareTestFailureError, match="tcpdump") as info:
        bridge.read_captured_udp_source_port(_Capture(returncode, "", stderr), timeout_s=1.0)  # type: ignore[arg-type]
    assert stderr in str(info.value) and f"exit {returncode}" in str(info.value)


def test_a_qdisc_listing_without_the_interface_raises_rather_than_reading_as_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    # Every interface carries a root qdisc, so a listing naming none for it is a changed format or a wrong interface -
    # read as "no netem", it would pass a leftover fault off as a clean host.
    bridge, _host = _bridge(monkeypatch, {"qdisc show": (0, "qdisc netem 8001: dev wlan10 root refcnt 2 loss 5%\n", "")})
    with pytest.raises(HardwareTestFailureError, match="listed no qdisc on wlan1"):
        bridge.clear_leftovers()
