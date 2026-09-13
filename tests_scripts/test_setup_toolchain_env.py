"""Tests toolchain/setup_toolchain.py's `env` subcommand (tiered generic/flash/bench dev
environment setup) in isolation: the pure-Python detection/idempotency/argument-parsing logic,
mocked against fake /sys trees and a fake run() - never real hardware, sudo, or network."""

# dev_legacy/README.md defines what "flash"/"bench" mean and holds the manual nmcli recipe this
# automates. End-to-end real-hardware behavior (USB auto-detection against a real board, the bridge
# and AP actually working) is proven on the real bench unit instead - the same "real thing, not
# stubs" split SPECIFICATION.md Part E.1 draws for the interpreter.

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import NoReturn

import pytest
from _script_loader import load_script_module


@pytest.fixture(scope="session")
def setup_toolchain(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "toolchain" / "setup_toolchain.py", "setup_toolchain")


@pytest.fixture
def recorded_run(monkeypatch: pytest.MonkeyPatch, setup_toolchain: ModuleType) -> list[list[str]]:
    """Replaces module.run with a recorder returning "" by default - lets a test inspect exactly
    which commands would have been executed without running any of them for real."""
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> str:
        calls.append(cmd)
        return ""

    monkeypatch.setattr(setup_toolchain, "run", fake_run)
    return calls


# --- USB serial device detection -------------------------------------------------------------


def _make_usb_tty(tmp_path: Path, sys_tty_dir: Path, dev_dir: Path, tty_name: str, id_vendor: str, *, create_dev_node: bool = True) -> None:
    """Builds a minimal fake /sys/class/tty/<tty_name>/device -> .../<usb-device>/idVendor tree,
    mirroring the real kernel layout closely enough for detect_pico_serial_devices() to walk."""
    usb_device_dir = tmp_path / "sys_bus" / f"usb-device-{tty_name}"
    usb_interface_dir = usb_device_dir / f"{tty_name}:1.0"
    usb_interface_dir.mkdir(parents=True)
    (usb_device_dir / "idVendor").write_text(f"{id_vendor}\n")

    tty_dir = sys_tty_dir / tty_name
    tty_dir.mkdir(parents=True)
    os.symlink(usb_interface_dir, tty_dir / "device")

    if create_dev_node:
        dev_dir.mkdir(parents=True, exist_ok=True)
        (dev_dir / tty_name).write_text("")


def test_detect_pico_serial_devices_matches_only_the_pico_vendor_id(tmp_path: Path, setup_toolchain: ModuleType) -> None:
    sys_tty_dir = tmp_path / "sys" / "class" / "tty"
    dev_dir = tmp_path / "dev"
    _make_usb_tty(tmp_path, sys_tty_dir, dev_dir, "ttyACM0", setup_toolchain.PICO_USB_VENDOR_ID)
    _make_usb_tty(tmp_path, sys_tty_dir, dev_dir, "ttyUSB0", "1a86")  # unrelated CH340 adapter

    found = setup_toolchain.detect_pico_serial_devices(sys_tty_dir=sys_tty_dir, dev_dir=dev_dir)

    assert found == [dev_dir / "ttyACM0"]


def test_detect_pico_serial_devices_ignores_a_matching_vendor_with_no_dev_node(tmp_path: Path, setup_toolchain: ModuleType) -> None:
    # A /sys entry can exist with the device already unplugged/racing - only a device that also
    # has a live /dev node is usable.
    sys_tty_dir = tmp_path / "sys" / "class" / "tty"
    dev_dir = tmp_path / "dev"
    _make_usb_tty(tmp_path, sys_tty_dir, dev_dir, "ttyACM0", setup_toolchain.PICO_USB_VENDOR_ID, create_dev_node=False)

    found = setup_toolchain.detect_pico_serial_devices(sys_tty_dir=sys_tty_dir, dev_dir=dev_dir)

    assert found == []


def test_detect_pico_serial_devices_returns_empty_list_when_sys_tty_dir_missing(tmp_path: Path, setup_toolchain: ModuleType) -> None:
    found = setup_toolchain.detect_pico_serial_devices(sys_tty_dir=tmp_path / "no-such-dir", dev_dir=tmp_path / "dev")
    assert found == []


def test_resolve_pico_device_prefers_explicit_override(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain, "detect_pico_serial_devices", lambda: pytest.fail("should not auto-detect"))
    assert setup_toolchain.resolve_pico_device("/dev/ttyACM7") == setup_toolchain.Path("/dev/ttyACM7")


def test_resolve_pico_device_auto_detects_single_match(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    expected = setup_toolchain.Path("/dev/ttyACM0")
    monkeypatch.setattr(setup_toolchain, "detect_pico_serial_devices", lambda: [expected])
    assert setup_toolchain.resolve_pico_device(None) == expected


def test_resolve_pico_device_raises_on_no_match(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain, "detect_pico_serial_devices", list)
    with pytest.raises(setup_toolchain.SetupError, match="no Raspberry Pi USB serial device found"):
        setup_toolchain.resolve_pico_device(None)


def test_resolve_pico_device_raises_on_ambiguous_match(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    candidates = [setup_toolchain.Path("/dev/ttyACM0"), setup_toolchain.Path("/dev/ttyACM1")]
    monkeypatch.setattr(setup_toolchain, "detect_pico_serial_devices", lambda: candidates)
    with pytest.raises(setup_toolchain.SetupError, match="multiple Raspberry Pi USB serial devices"):
        setup_toolchain.resolve_pico_device(None)


# --- dialout group membership ------------------------------------------------------------------


class _FakeGrEntry:
    def __init__(self, members: list[str]) -> None:
        self.gr_mem = members


def test_ensure_dialout_group_skip_flag_does_nothing(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setattr(setup_toolchain.grp, "getgrnam", lambda name: pytest.fail("should not check group"))
    setup_toolchain.ensure_dialout_group(skip=True)
    assert recorded_run == []


def test_ensure_dialout_group_already_member_does_not_call_usermod(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setenv("USER", "bench-user")
    monkeypatch.setattr(setup_toolchain.grp, "getgrnam", lambda name: _FakeGrEntry(["bench-user"]))
    setup_toolchain.ensure_dialout_group(skip=False)
    assert recorded_run == []


def test_ensure_dialout_group_not_member_calls_usermod(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setenv("USER", "bench-user")
    monkeypatch.setattr(setup_toolchain.grp, "getgrnam", lambda name: _FakeGrEntry([]))
    setup_toolchain.ensure_dialout_group(skip=False)
    assert recorded_run == [["sudo", "usermod", "-aG", "dialout", "bench-user"]]


def test_ensure_dialout_group_raises_if_no_dialout_group_exists(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setenv("USER", "bench-user")

    def raise_key_error(name: str) -> NoReturn:
        raise KeyError(name)

    monkeypatch.setattr(setup_toolchain.grp, "getgrnam", raise_key_error)
    with pytest.raises(setup_toolchain.SetupError, match="no 'dialout' group exists"):
        setup_toolchain.ensure_dialout_group(skip=False)


# --- NetworkManager presence ---------------------------------------------------------------------


def test_ensure_network_manager_no_op_when_nmcli_already_present(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name: "/usr/bin/nmcli")
    monkeypatch.setattr(setup_toolchain, "ensure_apt_packages", lambda packages, skip: pytest.fail("should not install"))
    setup_toolchain.ensure_network_manager(skip_apt=False)


def test_ensure_network_manager_installs_when_missing(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    which_results = iter([None, "/usr/bin/nmcli"])  # missing, then present after "install"
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name: next(which_results))
    monkeypatch.setattr(setup_toolchain, "ensure_apt_packages", lambda packages, skip: calls.append((packages, skip)))
    setup_toolchain.ensure_network_manager(skip_apt=False)
    assert calls == [([setup_toolchain.NETWORK_MANAGER_APT_PACKAGE], False)]


def test_ensure_network_manager_raises_if_still_missing_after_install(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name: None)
    monkeypatch.setattr(setup_toolchain, "ensure_apt_packages", lambda packages, skip: None)
    with pytest.raises(setup_toolchain.SetupError, match="nmcli still not found"):
        setup_toolchain.ensure_network_manager(skip_apt=False)


def test_ensure_iproute2_no_op_when_ip_already_present(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name: "/usr/sbin/ip")
    monkeypatch.setattr(setup_toolchain, "ensure_apt_packages", lambda packages, skip: pytest.fail("should not install"))
    setup_toolchain.ensure_iproute2(skip_apt=False)


def test_ensure_iproute2_installs_when_missing(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    which_results = iter([None, "/usr/sbin/ip"])
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name: next(which_results))
    monkeypatch.setattr(setup_toolchain, "ensure_apt_packages", lambda packages, skip: calls.append((packages, skip)))
    setup_toolchain.ensure_iproute2(skip_apt=False)
    assert calls == [([setup_toolchain.IPROUTE2_APT_PACKAGE], False)]


def test_ensure_iproute2_raises_if_still_missing_after_install(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name: None)
    monkeypatch.setattr(setup_toolchain, "ensure_apt_packages", lambda packages, skip: None)
    with pytest.raises(setup_toolchain.SetupError, match="'ip' command still not found"):
        setup_toolchain.ensure_iproute2(skip_apt=False)


# --- uplink / free WiFi interface detection ------------------------------------------------------


def test_detect_uplink_interface_parses_ip_route_get(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        setup_toolchain, "run",
        lambda cmd, cwd=None, check=True, env=None: "1.1.1.1 via 10.0.0.1 dev eth0 src 10.0.0.5 uid 0\n    cache\n",
    )
    assert setup_toolchain.detect_uplink_interface() == "eth0"


def test_detect_uplink_interface_raises_when_unparseable(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain, "run", lambda cmd, cwd=None, check=True, env=None: "nonsense output\n")
    with pytest.raises(setup_toolchain.SetupError, match="could not determine the default-route"):
        setup_toolchain.detect_uplink_interface()


def test_detect_free_wifi_interface_single_candidate(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        setup_toolchain, "run",
        lambda cmd, cwd=None, check=True, env=None: "eth0:ethernet\nwlan0:wifi\nlo:loopback\n",
    )
    assert setup_toolchain.detect_free_wifi_interface(exclude="eth0") == "wlan0"


def test_detect_free_wifi_interface_raises_when_none_found(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain, "run", lambda cmd, cwd=None, check=True, env=None: "eth0:ethernet\n")
    with pytest.raises(setup_toolchain.SetupError, match="no free WiFi adapter found"):
        setup_toolchain.detect_free_wifi_interface(exclude="eth0")


def test_detect_free_wifi_interface_raises_when_ambiguous(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        setup_toolchain, "run",
        lambda cmd, cwd=None, check=True, env=None: "eth0:ethernet\nwlan0:wifi\nwlan1:wifi\n",
    )
    with pytest.raises(setup_toolchain.SetupError, match="multiple candidate WiFi adapters"):
        setup_toolchain.detect_free_wifi_interface(exclude="eth0")


# --- bench AP credentials + idempotent bridge creation --------------------------------------------


def test_get_interface_mac_parses_real_ip_link_show_output(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    def fake_run(cmd: list[str], cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> str:
        recorded_run.append(cmd)
        assert cmd == ["ip", "-o", "link", "show", "eth0"]
        return "2: eth0    <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP mode DEFAULT group default qlen 1000\\    link/ether d8:3a:dd:28:ea:5a brd ff:ff:ff:ff:ff:ff"

    monkeypatch.setattr(setup_toolchain, "run", fake_run)

    assert setup_toolchain.get_interface_mac("eth0") == "d8:3a:dd:28:ea:5a"


def test_get_interface_mac_raises_when_no_mac_found(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setattr(setup_toolchain, "run", lambda cmd, cwd=None, check=True, env=None: "")

    with pytest.raises(setup_toolchain.SetupError, match="eth0"):
        setup_toolchain.get_interface_mac("eth0")


def test_generate_bench_ap_credentials_are_fresh_and_random(setup_toolchain: ModuleType) -> None:
    ssid1, password1 = setup_toolchain.generate_bench_ap_credentials()
    ssid2, password2 = setup_toolchain.generate_bench_ap_credentials()
    assert ssid1.startswith("sensors-bench-")
    assert ssid1 != ssid2
    assert password1 != password2
    assert len(password1) >= 12


def _fake_run_for_existing_bridge(recorded_run: list[list[str]], channel: str = "6", eth_iface: str = "eth0", bridge_mac: str = "aa:bb:cc:dd:ee:ff", real_mac: str = "aa:bb:cc:dd:ee:ff") -> Callable[..., str]:
    r"""A field-aware fake_run() for ensure_bench_bridge()'s "already exists" branch - dispatches
    each of its three distinct `nmcli -g` queries (channel, interface-name, bridge MAC) plus the
    `ip -o link show` real-MAC lookup by their actual field/command, rather than one blanket
    return value for every `nmcli -g` call regardless of which field it asked for (which used to
    let get_interface_mac() silently receive "6\n" as an interface name and swallow the
    resulting SetupError - never actually exercising the mismatch-detection logic this fixture
    now models directly).

    Models `nmcli -g`'s own ':' escaping faithfully: it returns 'D8\:3A\:...' unless `--escape no`
    is passed. Not modelling that is exactly how the MAC check shipped unconditionally broken - the
    fake handed back a plain 'aa:bb:cc:dd:ee:ff' no real nmcli would ever produce, so the comparison
    passed here while never once matching on real hardware. Keeping the escaping modelled is what
    makes the no-warning test below a genuine regression guard on `--escape no` staying put."""

    def fake_run(cmd: list[str], cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> str:
        recorded_run.append(cmd)
        if cmd[:4] == ["ip", "-o", "link", "show"]:
            return f"2: {eth_iface}    link/ether {real_mac} brd ff:ff:ff:ff:ff:ff"
        if cmd[0] != "nmcli" or "-g" not in cmd:
            return ""
        escaped = not any(cmd[i:i + 2] == ["--escape", "no"] for i in range(len(cmd) - 1))
        field = cmd[cmd.index("-g") + 1]
        value = {
            "802-11-wireless.channel": channel,
            "connection.interface-name": eth_iface,
            "bridge.mac-address": bridge_mac,
        }.get(field)
        if value is None:
            return ""
        return f"{value.replace(':', chr(92) + ':') if escaped else value}\n"

    return fake_run


def test_ensure_bench_bridge_reuses_existing_ap_without_recreating(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    # ensure_br_netfilter(), the channel self-heal check, and the MAC-mismatch check now all run
    # unconditionally on every call (see ensure_bench_bridge()'s own docstring) - channel and MAC
    # are stubbed already-correct so neither self-heal/warning branch (covered separately below)
    # also fires here.
    monkeypatch.setattr(setup_toolchain, "bench_ap_exists", lambda: True)
    monkeypatch.setattr(setup_toolchain, "existing_bench_ap_ssid", lambda: "sensors-bench-abc123")
    monkeypatch.setattr(setup_toolchain, "run", _fake_run_for_existing_bridge(recorded_run))

    ssid = setup_toolchain.ensure_bench_bridge("eth0", "wlan0", None, None)

    assert ssid == "sensors-bench-abc123"
    joined = [" ".join(c) for c in recorded_run]
    # no bridge/AP recreation - nothing that would add a new connection profile or rewrite its
    # WiFi security settings
    assert not any("connection add" in c for c in joined)
    assert not any("wifi-sec.psk" in c for c in joined)


def test_ensure_bench_bridge_self_heals_wrong_channel(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setattr(setup_toolchain, "bench_ap_exists", lambda: True)
    monkeypatch.setattr(setup_toolchain, "existing_bench_ap_ssid", lambda: "sensors-bench-abc123")
    monkeypatch.setattr(setup_toolchain, "run", _fake_run_for_existing_bridge(recorded_run, channel="13"))  # a bridge created before the channel-pinning fix

    setup_toolchain.ensure_bench_bridge("eth0", "wlan0", None, None)

    joined = [" ".join(c) for c in recorded_run]
    assert any("connection modify br0-wifi-ap 802-11-wireless.channel 6" in c for c in joined)
    assert any(c == "sudo nmcli connection up br0-wifi-ap" for c in joined)


def test_ensure_bench_bridge_no_channel_repair_when_already_pinned(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setattr(setup_toolchain, "bench_ap_exists", lambda: True)
    monkeypatch.setattr(setup_toolchain, "existing_bench_ap_ssid", lambda: "sensors-bench-abc123")
    monkeypatch.setattr(setup_toolchain, "run", _fake_run_for_existing_bridge(recorded_run, channel="6"))

    setup_toolchain.ensure_bench_bridge("eth0", "wlan0", None, None)

    joined = [" ".join(c) for c in recorded_run]
    assert not any("802-11-wireless.channel 6" in c and "modify" in c for c in joined)


def test_ensure_bench_bridge_warns_without_auto_repairing_mac_mismatch(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]], capsys: pytest.CaptureFixture[str]) -> None:
    # REAL FINDING, 2026-09-04 bench Pi4 lockout incident (see CLAUDE.md's "Hard rules"): a bridge
    # created before the MAC-pinning fix (or whose MAC has since drifted) must be flagged, never
    # silently auto-repaired - cycling a live bridge's MAC risks the exact same SSH-drop class of
    # incident this check exists to prevent.
    monkeypatch.setattr(setup_toolchain, "bench_ap_exists", lambda: True)
    monkeypatch.setattr(setup_toolchain, "existing_bench_ap_ssid", lambda: "sensors-bench-abc123")
    monkeypatch.setattr(
        setup_toolchain,
        "run",
        _fake_run_for_existing_bridge(recorded_run, bridge_mac="11:11:11:11:11:11", real_mac="aa:bb:cc:dd:ee:ff"),
    )

    setup_toolchain.ensure_bench_bridge("eth0", "wlan0", None, None)

    joined = [" ".join(c) for c in recorded_run]
    assert not any("bridge.mac-address" in c and "modify" in c for c in joined)  # never auto-repaired
    captured_out = capsys.readouterr().out
    assert "WARNING" in captured_out
    assert "11:11:11:11:11:11" in captured_out
    assert "aa:bb:cc:dd:ee:ff" in captured_out


def test_ensure_bench_bridge_no_warning_when_mac_already_matches(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]], capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(setup_toolchain, "bench_ap_exists", lambda: True)
    monkeypatch.setattr(setup_toolchain, "existing_bench_ap_ssid", lambda: "sensors-bench-abc123")
    monkeypatch.setattr(
        setup_toolchain,
        "run",
        _fake_run_for_existing_bridge(recorded_run, bridge_mac="aa:bb:cc:dd:ee:ff", real_mac="aa:bb:cc:dd:ee:ff"),
    )

    setup_toolchain.ensure_bench_bridge("eth0", "wlan0", None, None)

    assert "WARNING" not in capsys.readouterr().out


def test_ensure_br_netfilter_loads_module_and_persists_config(setup_toolchain: ModuleType, recorded_run: list[list[str]]) -> None:
    setup_toolchain.ensure_br_netfilter()

    joined = [" ".join(c) for c in recorded_run]
    assert any(c == "sudo modprobe br_netfilter" for c in joined)
    assert any("sysctl -w net.bridge.bridge-nf-call-iptables=1" in c for c in joined)
    assert any("sensors-bench-br-netfilter.conf" in c and "modules-load.d" in c for c in joined)
    assert any("sensors-bench-br-netfilter.conf" in c and "sysctl.d" in c for c in joined)


def _fake_run_with_real_eth0_mac(recorded_run: list[list[str]], mac: str = "aa:bb:cc:dd:ee:ff") -> Callable[..., str]:
    r"""A fake_run() that also answers ensure_bench_bridge()'s get_interface_mac(uplink_iface)
    lookup realistically, mirroring a real `ip -o link show eth0` line closely enough for
    get_interface_mac()'s own `link/ether\s+(\S+)` regex to match - the plain recorded_run
    fixture's blanket "" default doesn't, which is exactly what made these two tests fail for
    real once get_interface_mac() was added (confirmed directly against a real CI run,
    2026-09-04): SetupError propagated uncaught through the bridge-creation path instead of
    exercising it."""

    def fake_run(cmd: list[str], cwd: Path | None = None, check: bool = True, env: dict[str, str] | None = None) -> str:
        recorded_run.append(cmd)
        if cmd[:4] == ["ip", "-o", "link", "show"]:
            return f"2: eth0    link/ether {mac} brd ff:ff:ff:ff:ff:ff"
        return ""

    return fake_run


def test_ensure_bench_bridge_creates_with_explicit_credentials_when_missing(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setattr(setup_toolchain, "bench_ap_exists", lambda: False)
    monkeypatch.setattr(setup_toolchain, "run", _fake_run_with_real_eth0_mac(recorded_run))

    ssid = setup_toolchain.ensure_bench_bridge("eth0", "wlan0", "my-test-ssid", "my-test-password")

    assert ssid == "my-test-ssid"
    joined = [" ".join(c) for c in recorded_run]
    assert any("connection add type bridge" in c and "br0" in c for c in joined)
    # REAL FINDING, 2026-09-04 bench Pi4 lockout incident: the bridge's own MAC must be pinned to
    # the uplink interface's real hardware MAC before anything is brought up - see
    # ensure_bench_bridge()'s own docstring and CLAUDE.md's "Hard rules".
    assert any(c == "sudo nmcli connection modify br0 bridge.mac-address aa:bb:cc:dd:ee:ff" for c in joined)
    assert any("connection add type ethernet" in c and "eth0" in c for c in joined)
    assert any("connection add type wifi" in c and "wlan0" in c and "my-test-ssid" in c for c in joined)
    assert any("wifi-sec.pmf disable" in c for c in joined)  # load-bearing cyw43439 tuning
    assert any(c == "sudo nmcli connection up br0-eth0" for c in joined)
    assert any(c == "sudo nmcli connection up br0-wifi-ap" for c in joined)
    # the MAC pin must happen before the bridge slave/uplink is ever brought up, not after
    mac_pin_index = joined.index("sudo nmcli connection modify br0 bridge.mac-address aa:bb:cc:dd:ee:ff")
    eth_up_index = joined.index("sudo nmcli connection up br0-eth0")
    assert mac_pin_index < eth_up_index


def test_ensure_bench_bridge_generates_credentials_when_none_given(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setattr(setup_toolchain, "bench_ap_exists", lambda: False)
    monkeypatch.setattr(setup_toolchain, "generate_bench_ap_credentials", lambda: ("generated-ssid", "generated-pw"))
    monkeypatch.setattr(setup_toolchain, "run", _fake_run_with_real_eth0_mac(recorded_run))

    ssid = setup_toolchain.ensure_bench_bridge("eth0", "wlan0", None, None)

    assert ssid == "generated-ssid"
    joined = [" ".join(c) for c in recorded_run]
    assert any("generated-ssid" in c for c in joined)
    assert any("generated-pw" in c for c in joined)
    assert any(c == "sudo nmcli connection modify br0 bridge.mac-address aa:bb:cc:dd:ee:ff" for c in joined)


# --- project dependency install (uv sync / npm ci) -------------------------------------------------


def test_run_project_dependency_install_skips_npm_when_flag_set(setup_toolchain: ModuleType, tmp_path: Path, recorded_run: list[list[str]]) -> None:
    (tmp_path / "package.json").write_text("{}")
    setup_toolchain.run_project_dependency_install(tmp_path, skip_npm=True)
    assert recorded_run == [["uv", "sync"]]


def test_run_project_dependency_install_skips_npm_when_no_package_json(setup_toolchain: ModuleType, tmp_path: Path, recorded_run: list[list[str]]) -> None:
    setup_toolchain.run_project_dependency_install(tmp_path, skip_npm=False)
    assert recorded_run == [["uv", "sync"]]


def test_run_project_dependency_install_skips_npm_when_not_on_path(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    (tmp_path / "package.json").write_text("{}")
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name: None)
    setup_toolchain.run_project_dependency_install(tmp_path, skip_npm=False)
    assert recorded_run == [["uv", "sync"]]


def test_run_project_dependency_install_runs_npm_ci_when_available(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    (tmp_path / "package.json").write_text("{}")
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name: "/usr/bin/npm")
    setup_toolchain.run_project_dependency_install(tmp_path, skip_npm=False)
    assert recorded_run == [["uv", "sync"], ["npm", "ci"]]


# --- CLI wiring ---------------------------------------------------------------------------------


def _run_cli(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "toolchain/setup_toolchain.py", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_env_help_lists_all_three_tiers(repo_root: Path) -> None:
    result = _run_cli(repo_root, ["env", "--help"])
    assert result.returncode == 0
    assert "{generic,flash,bench}" in result.stdout


def test_cli_env_requires_tier(repo_root: Path) -> None:
    result = _run_cli(repo_root, ["env"])
    assert result.returncode != 0
    assert "--tier" in result.stderr


def test_cli_env_rejects_unknown_tier(repo_root: Path) -> None:
    result = _run_cli(repo_root, ["env", "--tier", "nope"])
    assert result.returncode != 0
    assert "invalid choice" in result.stderr
