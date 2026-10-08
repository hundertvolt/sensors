"""Tests toolchain/setup_toolchain.py in isolation: run()'s limits, streaming and redaction on real
short commands, the toolchain lock and record on temporary directories, everything else against fake
/sys trees and a fake run() - never real hardware, sudo, apt or network."""

# README.md's tier table defines 'flash' and 'bench'; tests_hardware/README.md holds the manual nmcli
# recipe this automates. End-to-end behavior - USB detection, the bridge and AP working - is proven
# on the real bench unit instead, the same real-thing-not-stubs split Part E.1 draws.

import argparse
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType
from typing import NoReturn, Protocol

import pytest
import tomllib
from _script_loader import load_script_module


@pytest.fixture(scope="session")
def setup_toolchain(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "toolchain" / "setup_toolchain.py", "setup_toolchain")


# Read before any test runs, for the one test that reads the pinned checkout (never writes it): every
# test itself sees a temporary toolchain directory and HOME.
_REAL_TOOLCHAIN_DIR = Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain"))
# Everything the installer runs that can install, fetch, build, need root or change the host.
_SHIMMED = (
    "sudo", "apt-get", "apt", "dpkg", "git", "make", "cmake", "curl", "npm", "npx", "uv", "picotool", "nmcli",
    "systemd-run", "systemctl", "usermod", "modprobe", "sysctl", "iptables", "tc", "iw", "ip", "arm-none-eabi-gcc", "gcc",
)


@pytest.fixture(autouse=True)
def _no_real_side_effects(setup_toolchain: ModuleType, request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> Path:
    # A test whose code under test goes wrong must fail here, never set up a real toolchain: a temporary
    # toolchain dir and HOME, and failing shims first on both the inherited PATH and the installer's own
    # fixed BUILD_ENV_PATH (build_env()/network_env() never read the inherited one), children included.
    shims = tmp_path_factory.mktemp("shims")
    for name in _SHIMMED:
        shim = shims / name
        shim.write_text(f'#!/bin/sh\necho "{request.node.nodeid}: {name} is shimmed out of the L0 tier" >&2\nexit 97\n')
        shim.chmod(0o755)
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(home / "pico-toolchain"))
    monkeypatch.setenv("PATH", f"{shims}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(setup_toolchain, "BUILD_ENV_PATH", f"{shims}{os.pathsep}{setup_toolchain.BUILD_ENV_PATH}")
    monkeypatch.setattr(setup_toolchain, "PICOTOOL_INSTALL_PREFIX", str(home / "usr-local"))
    return shims


def test_the_guard_stops_a_real_step_on_every_path(setup_toolchain: ModuleType) -> None:
    # The guard's own proof: a fetch reached through the installer's fixed PATH, and one through the
    # inherited PATH, both end on the shim.
    with pytest.raises(setup_toolchain.SetupError, match=r"command failed \(exit 97\): git --version"):
        setup_toolchain.run(["git", "--version"], env=setup_toolchain.network_env(), timeout_s=30)
    with pytest.raises(setup_toolchain.SetupError, match=r"command failed \(exit 97\): sudo apt-get update"):
        setup_toolchain.run(["sudo", "apt-get", "update"], timeout_s=30)


@pytest.fixture
def recorded_run(monkeypatch: pytest.MonkeyPatch, setup_toolchain: ModuleType) -> list[list[str]]:
    # Replaces module.run with a recorder returning "" by default - lets a test inspect exactly
    # which commands would have been executed without running any of them for real.
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], cwd: Path | None = None, *, check: bool = True, env: dict[str, str] | None = None, **_kwargs: object) -> str:
        calls.append(cmd)
        return ""

    monkeypatch.setattr(setup_toolchain, "run", fake_run)
    return calls


class _FakeRun:
    # A recording stand-in for run(): every call's argv and keywords, answered by the longest matching argv
    # prefix - a string, an exception to raise, or a list of those used one per call (the last repeats).
    def __init__(self, answers: "dict[tuple[str, ...], object] | None" = None) -> None:
        self.calls: list[dict[str, object]] = []
        self.answers = answers or {}

    def __call__(self, cmd: list[str], cwd: Path | None = None, **kwargs: object) -> str:
        self.calls.append({"cmd": cmd, "cwd": cwd, **kwargs})
        matches = [prefix for prefix in self.answers if tuple(cmd[: len(prefix)]) == prefix]
        if not matches:
            return ""
        answer = self.answers[max(matches, key=len)]
        if isinstance(answer, list):
            answer = answer.pop(0) if len(answer) > 1 else answer[0]
        if isinstance(answer, BaseException):
            raise answer
        return str(answer)

    def argvs(self) -> list[list[str]]:
        return [cast_argv(call["cmd"]) for call in self.calls]


def cast_argv(value: object) -> list[str]:
    assert isinstance(value, list)
    return [str(arg) for arg in value]


# --- USB serial device detection -------------------------------------------------------------


def _make_usb_tty(tmp_path: Path, sys_tty_dir: Path, dev_dir: Path, tty_name: str, id_vendor: str, *, create_dev_node: bool = True) -> None:
    # Builds a minimal fake /sys/class/tty/<tty_name>/device -> .../<usb-device>/idVendor tree,
    # mirroring the real kernel layout closely enough for detect_pico_serial_devices() to walk.
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


_MICROPYTHON_BY_ID = "usb-MicroPython_Board_in_FS_mode_e6614c311b7e6f35-if00"


def _by_id_link(by_id_dir: Path, name: str, target: Path) -> Path:
    by_id_dir.mkdir(parents=True, exist_ok=True)
    link = by_id_dir / name
    os.symlink(target, link)
    return link


def test_the_board_is_the_micropython_by_id_link_on_a_2e8a_node(tmp_path: Path, setup_toolchain: ModuleType) -> None:
    # A debug probe reports vendor 2e8a too: only the link MicroPython's own USB name gives counts.
    sys_tty_dir, dev_dir, by_id = tmp_path / "sys" / "class" / "tty", tmp_path / "dev", tmp_path / "by-id"
    _make_usb_tty(tmp_path, sys_tty_dir, dev_dir, "ttyACM0", setup_toolchain.PICO_USB_VENDOR_ID)
    _make_usb_tty(tmp_path, sys_tty_dir, dev_dir, "ttyACM1", setup_toolchain.PICO_USB_VENDOR_ID)
    _by_id_link(by_id, "usb-Raspberry_Pi_Debug_Probe__CMSIS-DAP__E6633861A3-if01", dev_dir / "ttyACM1")
    board = _by_id_link(by_id, _MICROPYTHON_BY_ID, dev_dir / "ttyACM0")
    assert setup_toolchain.resolve_board_serial(by_id_dir=by_id, sys_tty_dir=sys_tty_dir, dev_dir=dev_dir) == [board]


def test_a_micropython_link_on_another_vendor_is_not_the_board(tmp_path: Path, setup_toolchain: ModuleType) -> None:
    sys_tty_dir, dev_dir, by_id = tmp_path / "sys" / "class" / "tty", tmp_path / "dev", tmp_path / "by-id"
    _make_usb_tty(tmp_path, sys_tty_dir, dev_dir, "ttyUSB0", "1a86")
    _by_id_link(by_id, _MICROPYTHON_BY_ID, dev_dir / "ttyUSB0")
    assert setup_toolchain.resolve_board_serial(by_id_dir=by_id, sys_tty_dir=sys_tty_dir, dev_dir=dev_dir) == []


def test_without_a_readable_sys_the_micropython_link_alone_names_the_board(tmp_path: Path, setup_toolchain: ModuleType) -> None:
    dev_dir, by_id = tmp_path / "dev", tmp_path / "by-id"
    dev_dir.mkdir()
    (dev_dir / "ttyACM0").write_text("")
    board = _by_id_link(by_id, _MICROPYTHON_BY_ID, dev_dir / "ttyACM0")
    assert setup_toolchain.resolve_board_serial(by_id_dir=by_id, sys_tty_dir=tmp_path / "no-sys", dev_dir=dev_dir) == [board]


def test_resolve_pico_device_takes_device_then_mpremote_device_before_detecting(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain, "resolve_board_serial", lambda: pytest.fail("should not auto-detect"))
    monkeypatch.setenv("MPREMOTE_DEVICE", "/dev/ttyACM9")
    assert setup_toolchain.resolve_pico_device("/dev/ttyACM7") == Path("/dev/ttyACM7")
    assert setup_toolchain.resolve_pico_device(None) == Path("/dev/ttyACM9")


def test_resolve_pico_device_auto_detects_single_match(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MPREMOTE_DEVICE", raising=False)
    expected = Path("/dev/serial/by-id") / _MICROPYTHON_BY_ID
    monkeypatch.setattr(setup_toolchain, "resolve_board_serial", lambda: [expected])
    assert setup_toolchain.resolve_pico_device(None) == expected


def test_resolve_pico_device_raises_on_no_match(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MPREMOTE_DEVICE", raising=False)
    monkeypatch.setattr(setup_toolchain, "resolve_board_serial", list)
    with pytest.raises(setup_toolchain.SetupError, match=r"no MicroPython board found \(USB vendor 2e8a .*pass --device / set MPREMOTE_DEVICE"):
        setup_toolchain.resolve_pico_device(None)


def test_resolve_pico_device_raises_on_ambiguous_match(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MPREMOTE_DEVICE", raising=False)
    candidates = [Path("/dev/serial/by-id/a"), Path("/dev/serial/by-id/b")]
    monkeypatch.setattr(setup_toolchain, "resolve_board_serial", lambda: candidates)
    with pytest.raises(setup_toolchain.SetupError, match=r"multiple MicroPython boards found \(/dev/serial/by-id/a, /dev/serial/by-id/b\)"):
        setup_toolchain.resolve_pico_device(None)


def test_the_installer_and_the_bench_harness_look_for_one_board_name(setup_toolchain: ModuleType, repo_root: Path) -> None:
    # tests_hardware/harness.py still carries its own copy of the glob; until it reads this one, they must agree.
    harness = load_script_module(repo_root / "tests_hardware" / "harness.py", "harness")
    assert setup_toolchain.BOARD_BY_ID_GLOB == harness._BOARD_BY_ID_GLOB


def test_board_prints_the_resolved_path_without_a_lock_or_a_versions_read(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("MPREMOTE_DEVICE", raising=False)
    monkeypatch.setattr(setup_toolchain, "resolve_board_serial", lambda: [Path("/dev/serial/by-id") / _MICROPYTHON_BY_ID])
    monkeypatch.setattr(setup_toolchain, "toolchain_lock", lambda toolchain_dir: pytest.fail("board took the toolchain lock"))
    monkeypatch.setattr(setup_toolchain, "load_versions", lambda path: pytest.fail("board read versions.toml"))
    monkeypatch.setattr(sys, "argv", ["setup_toolchain.py", "board"])
    capsys.readouterr()
    assert setup_toolchain.main() == 0
    assert capsys.readouterr().out == f"/dev/serial/by-id/{_MICROPYTHON_BY_ID}\n", "a shell caller reads stdout as the path"


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


# --- the commands each tier runs: one table ---------------------------------------------------------


def _commands_present(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, present: set[str]) -> list[str | None]:
    # shutil.which() answering from `present`; returns the PATH each lookup was asked on.
    paths: list[str | None] = []

    def which(name: str, path: str | None = None) -> str | None:
        paths.append(path)
        return f"/usr/bin/{name}" if name in present else None

    monkeypatch.setattr(setup_toolchain.shutil, "which", which)
    return paths


def test_present_commands_install_nothing_and_are_looked_up_on_the_build_path(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    bench = setup_toolchain._TIER_COMMANDS["bench"]
    paths = _commands_present(setup_toolchain, monkeypatch, {cmd for cmd, _ in bench})
    monkeypatch.setattr(setup_toolchain, "ensure_apt_packages", lambda packages, *, skip: pytest.fail("installed a present command"))
    setup_toolchain.ensure_commands(bench, skip_apt=False)
    assert set(paths) == {setup_toolchain.BUILD_ENV_PATH}


def test_missing_commands_are_installed_together(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    present = {"nmcli", "iptables", "sysctl", "modprobe", "tcpdump", "timeout"}
    _commands_present(setup_toolchain, monkeypatch, present)
    installs: list[list[str]] = []

    def install(packages: list[str], *, skip: bool) -> None:
        installs.append(packages)
        present.update({"ip", "iw", "tc"})

    monkeypatch.setattr(setup_toolchain, "ensure_apt_packages", install)
    setup_toolchain.ensure_commands(setup_toolchain._TIER_COMMANDS["bench"], skip_apt=False)
    assert installs == [["iproute2", "iw"]], "one install, each package once"


def test_a_command_still_missing_after_its_install_is_named(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    _commands_present(setup_toolchain, monkeypatch, set())
    monkeypatch.setattr(setup_toolchain, "ensure_apt_packages", lambda packages, *, skip: None)
    with pytest.raises(setup_toolchain.SetupError, match="'curl' still not on PATH after installing curl"):
        setup_toolchain.ensure_commands(setup_toolchain._TIER_COMMANDS["generic"], skip_apt=False)


def test_a_missing_command_under_skip_apt_says_what_to_install(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    _commands_present(setup_toolchain, monkeypatch, {"nmcli", "ip", "iptables", "sysctl", "modprobe", "tc", "timeout"})
    monkeypatch.setattr(setup_toolchain, "ensure_apt_packages", lambda packages, *, skip: pytest.fail("installed under --skip-apt"))
    with pytest.raises(setup_toolchain.SetupError, match="'iw', 'tcpdump' not on PATH and --skip-apt is set - install iw, tcpdump by hand"):
        setup_toolchain.ensure_commands(setup_toolchain._TIER_COMMANDS["bench"], skip_apt=True)


# --- passwordless sudo for what the bench tier runs unattended ------------------------------------------


def test_the_sudo_probe_passes_when_every_command_runs_without_a_password(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain.os, "geteuid", lambda: 1000)
    _commands_present(setup_toolchain, monkeypatch, set(setup_toolchain._BENCH_SUDO_COMMANDS))
    fake = _FakeRun()
    monkeypatch.setattr(setup_toolchain, "run", fake)
    setup_toolchain.check_passwordless_sudo(setup_toolchain._BENCH_SUDO_COMMANDS)
    probes = {argv[3]: argv for argv in fake.argvs()}
    assert set(probes) == {f"/usr/bin/{name}" for name in setup_toolchain._BENCH_SUDO_COMMANDS}
    # -k: a password cached a minute ago would pass a plain -n probe and expire before the unattended run.
    assert probes["/usr/bin/tc"] == ["sudo", "-k", "-n", "/usr/bin/tc", "-V"]
    assert probes["/usr/bin/picotool"] == ["sudo", "-k", "-n", "/usr/bin/picotool", "version"]
    assert probes["/usr/bin/nmcli"] == ["sudo", "-k", "-n", "/usr/bin/nmcli", "--version"]


def test_the_sudo_probe_names_only_the_refused_command(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain.os, "geteuid", lambda: 1000)
    _commands_present(setup_toolchain, monkeypatch, set(setup_toolchain._BENCH_SUDO_COMMANDS))
    refused = setup_toolchain.SetupError("command failed (exit 1): sudo -n /usr/bin/iw --version")
    monkeypatch.setattr(setup_toolchain, "run", _FakeRun({("sudo", "-k", "-n", "/usr/bin/iw"): refused}))
    with pytest.raises(setup_toolchain.SetupError, match=r"passwordless sudo missing or restricted to other arguments for: iw - .*tests_hardware/README.md Prerequisites") as raised:
        setup_toolchain.check_passwordless_sudo(setup_toolchain._BENCH_SUDO_COMMANDS)
    assert "nmcli" not in str(raised.value)


def test_root_needs_no_sudo_probe(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setattr(setup_toolchain.os, "geteuid", lambda: 0)
    setup_toolchain.check_passwordless_sudo(setup_toolchain._BENCH_SUDO_COMMANDS)
    assert recorded_run == []


def test_the_bench_tier_checks_commands_then_sudo_then_builds_the_bridge(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    steps: list[str] = []

    def step(name: str, result: object = None) -> object:
        steps.append(name)
        return result

    monkeypatch.setenv("BENCH_AP_PASSWORD", "throwaway-psk")
    monkeypatch.setattr(setup_toolchain, "run_setup", lambda args, versions_path, versions, *, tier: step(f"setup:{tier}", 0))
    monkeypatch.setattr(setup_toolchain, "run_project_dependency_install", lambda *_args, **_kwargs: steps.append("deps"))
    monkeypatch.setattr(setup_toolchain, "ensure_dialout_group", lambda *, skip: steps.append("dialout"))
    monkeypatch.setattr(setup_toolchain, "resolve_pico_device", lambda device: step("device", Path("/dev/ttyACM0")))
    monkeypatch.setattr(setup_toolchain, "ensure_commands", lambda pairs, *, skip_apt: steps.append(f"commands:{len(pairs)}"))
    monkeypatch.setattr(setup_toolchain, "check_passwordless_sudo", lambda commands: steps.append("sudo"))
    monkeypatch.setattr(setup_toolchain, "ensure_bench_bridge", lambda uplink, wifi, ssid, password: step(f"bridge:{password}", "ssid"))
    args = argparse.Namespace(
        tier="bench", toolchain_dir=tmp_path, skip_npm=True, skip_apt=True, device=None, uplink_iface=None, wifi_iface=None, ssid=None,
        micropython_ref=None, latest=False, clean=False, jobs=1,
    )
    assert setup_toolchain.run_env(args, setup_toolchain.VERSIONS_PATH, setup_toolchain.load_versions(setup_toolchain.VERSIONS_PATH)) == 0
    bench_commands = len(setup_toolchain._TIER_COMMANDS["bench"])
    assert steps == ["setup:bench", "deps", "dialout", "device", f"commands:{bench_commands}", "sudo", "bridge:throwaway-psk"]


# --- uplink / free WiFi interface detection ------------------------------------------------------


def test_detect_uplink_interface_parses_ip_route_get(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        setup_toolchain, "run",
        lambda cmd, cwd=None, **_kwargs: "1.1.1.1 via 10.0.0.1 dev eth0 src 10.0.0.5 uid 0\n    cache\n",
    )
    assert setup_toolchain.detect_uplink_interface() == "eth0"


def test_detect_uplink_interface_raises_when_unparseable(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain, "run", lambda cmd, cwd=None, **_kwargs: "nonsense output\n")
    with pytest.raises(setup_toolchain.SetupError, match="could not determine the default-route"):
        setup_toolchain.detect_uplink_interface()


def test_detect_free_wifi_interface_single_candidate(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        setup_toolchain, "run",
        lambda cmd, cwd=None, **_kwargs: "eth0:ethernet\nwlan0:wifi\nlo:loopback\n",
    )
    assert setup_toolchain.detect_free_wifi_interface(exclude="eth0") == "wlan0"


def test_detect_free_wifi_interface_raises_when_none_found(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain, "run", lambda cmd, cwd=None, **_kwargs: "eth0:ethernet\n")
    with pytest.raises(setup_toolchain.SetupError, match="no free WiFi adapter found"):
        setup_toolchain.detect_free_wifi_interface(exclude="eth0")


def test_detect_free_wifi_interface_raises_when_ambiguous(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        setup_toolchain, "run",
        lambda cmd, cwd=None, **_kwargs: "eth0:ethernet\nwlan0:wifi\nwlan1:wifi\n",
    )
    with pytest.raises(setup_toolchain.SetupError, match="multiple candidate WiFi adapters"):
        setup_toolchain.detect_free_wifi_interface(exclude="eth0")


# --- bench AP credentials + idempotent bridge creation --------------------------------------------


def test_get_interface_mac_parses_ip_link_show_output(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    def fake_run(cmd: list[str], cwd: Path | None = None, *, check: bool = True, env: dict[str, str] | None = None, **_kwargs: object) -> str:
        recorded_run.append(cmd)
        assert cmd == ["ip", "-o", "link", "show", "eth0"]
        return "2: eth0    <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP mode DEFAULT group default qlen 1000\\    link/ether 00:00:5e:00:53:01 brd ff:ff:ff:ff:ff:ff"

    monkeypatch.setattr(setup_toolchain, "run", fake_run)

    assert setup_toolchain.get_interface_mac("eth0") == "00:00:5e:00:53:01"


def test_get_interface_mac_raises_when_no_mac_found(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setattr(setup_toolchain, "run", lambda cmd, cwd=None, **_kwargs: "")

    with pytest.raises(setup_toolchain.SetupError, match="eth0"):
        setup_toolchain.get_interface_mac("eth0")


def test_generate_bench_ap_credentials_are_fresh_and_random(setup_toolchain: ModuleType) -> None:
    ssid1, password1 = setup_toolchain.generate_bench_ap_credentials()
    ssid2, password2 = setup_toolchain.generate_bench_ap_credentials()
    assert ssid1.startswith("sensors-bench-")
    assert ssid1 != ssid2
    assert password1 != password2
    assert len(password1) >= 12


class _RunLike(Protocol):
    def __call__(self, cmd: list[str], cwd: Path | None = None, **kwargs: object) -> str: ...


# The answers a bridge change's own checks read: the recovery timer armed then gone, br0 with an address
# and the default route through it.
_ARMED_THEN_GONE = ("active", "inactive")
_BR0_ADDRESS = "5: br0    inet 192.0.2.10/24 brd 192.0.2.255 scope global dynamic br0"
_BR0_ROUTE = "1.1.1.1 via 192.0.2.1 dev br0 src 192.0.2.10 uid 1000"


def _fake_run_for_existing_bridge(recorded_run: list[list[str]], channel: str = "6", eth_iface: str = "eth0", bridge_mac: str = "aa:bb:cc:dd:ee:ff", real_mac: str = "aa:bb:cc:dd:ee:ff") -> _RunLike:
    # A field-aware fake_run() for ensure_bench_bridge()'s "already exists" branch: each `nmcli -g`
    # query and the `ip -o link show` lookup answered by its actual field, and `nmcli -g`'s own ':'
    # escaping modelled - without either, the MAC check passes here while never matching on hardware.
    timer_states = list(_ARMED_THEN_GONE)

    def fake_run(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
        recorded_run.append(cmd)
        if cmd[:4] == ["ip", "-o", "link", "show"]:
            return f"2: {eth_iface}    link/ether {real_mac} brd ff:ff:ff:ff:ff:ff"
        if cmd[:2] == ["systemctl", "is-active"]:
            return timer_states.pop(0) if len(timer_states) > 1 else timer_states[0]
        if cmd[:5] == ["ip", "-o", "-4", "addr", "show"]:
            return _BR0_ADDRESS
        if cmd[:4] == ["ip", "-o", "route", "get"]:
            return _BR0_ROUTE
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
    # ensure_br_netfilter(), the channel self-heal and the MAC-mismatch check all run on every
    # call now. Channel and MAC are stubbed already-correct here, so neither of those branches -
    # covered separately below - fires as well.
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
    # Cycling the AP can drop the host: the repair runs under its own armed recovery timer, disarmed
    # only once br0 is forwarding again.
    arm = next(i for i, c in enumerate(joined) if "systemd-run" in c)
    modify = joined.index("sudo nmcli connection modify br0-wifi-ap 802-11-wireless.channel 6")
    up = joined.index("sudo nmcli connection up br0-wifi-ap")
    route = max(i for i, c in enumerate(joined) if c.startswith("ip -o route get"))
    stop = next(i for i, c in enumerate(joined) if "systemctl stop" in c)
    assert arm < modify < up < route < stop


def test_ensure_bench_bridge_no_channel_repair_when_already_pinned(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    monkeypatch.setattr(setup_toolchain, "bench_ap_exists", lambda: True)
    monkeypatch.setattr(setup_toolchain, "existing_bench_ap_ssid", lambda: "sensors-bench-abc123")
    monkeypatch.setattr(setup_toolchain, "run", _fake_run_for_existing_bridge(recorded_run, channel="6"))

    setup_toolchain.ensure_bench_bridge("eth0", "wlan0", None, None)

    joined = [" ".join(c) for c in recorded_run]
    assert not any("802-11-wireless.channel 6" in c and "modify" in c for c in joined)
    assert not any("systemd-run" in c for c in joined), "nothing changes, so nothing is armed"


def test_ensure_bench_bridge_warns_without_auto_repairing_mac_mismatch(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]], capsys: pytest.CaptureFixture[str]) -> None:
    # From the 2026-09-04 bench Pi4 lockout (CLAUDE.md's hard rules): a bridge created before the
    # MAC-pinning fix, or whose MAC has drifted, must be flagged and never auto-repaired -
    # cycling a live bridge's MAC risks the same SSH-drop this check exists to prevent.
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
    assert "arm SPECIFICATION.md B.13's recovery timer first" in " ".join(captured_out.split())


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


def test_br_netfilter_persists_through_tee_with_no_temporary_file(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeRun()
    monkeypatch.setattr(setup_toolchain, "run", fake)
    setup_toolchain.ensure_br_netfilter()
    argvs = [" ".join(argv) for argv in fake.argvs()]
    assert argvs[:2] == ["sudo modprobe br_netfilter", "sudo sysctl -w net.bridge.bridge-nf-call-iptables=1"]
    tees = [(call["cmd"], call["stdin_text"]) for call in fake.calls if "tee" in cast_argv(call["cmd"])]
    assert tees == [
        (["sudo", "tee", "/etc/modules-load.d/sensors-bench-br-netfilter.conf"], "br_netfilter\n"),
        (["sudo", "tee", "/etc/sysctl.d/99-sensors-bench-br-netfilter.conf"], "net.bridge.bridge-nf-call-iptables=1\n"),
    ]
    assert "sudo chmod 644 /etc/sysctl.d/99-sensors-bench-br-netfilter.conf" in argvs
    assert not any(tempfile.gettempdir() in argv for argv in argvs), "nothing is staged in a temporary file that a failure could leave behind"
    assert all(call["env"] == setup_toolchain.build_env() for call in fake.calls)


_DOC_MAC = "00:00:5e:00:53:01"  # RFC 7042's documentation block


def _creation_fake(*, profile: str = "Wired connection 1", timer_states: "tuple[str, ...]" = _ARMED_THEN_GONE, address: str = _BR0_ADDRESS) -> _FakeRun:
    # What ensure_bench_bridge()'s creation path reads: the uplink's MAC and active profile, the recovery
    # timer's state, and br0's address and route once it is up.
    return _FakeRun({
        ("ip", "-o", "link", "show"): f"2: eth0    link/ether {_DOC_MAC} brd ff:ff:ff:ff:ff:ff",
        ("nmcli", "--escape", "no", "-g", "GENERAL.CONNECTION", "device", "show"): f"{profile}\n",
        ("systemctl", "is-active"): list(timer_states),
        ("ip", "-o", "-4", "addr", "show"): address,
        ("ip", "-o", "route", "get"): _BR0_ROUTE,
    })


def _create_bridge(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, fake: _FakeRun, ssid: str | None, password: str | None) -> str:
    monkeypatch.setattr(setup_toolchain, "bench_ap_exists", lambda: False)
    monkeypatch.setattr(setup_toolchain, "run", fake)
    monkeypatch.setattr(setup_toolchain.time, "sleep", lambda _s: None)
    return str(setup_toolchain.ensure_bench_bridge("eth0", "wlan0", ssid, password))


def test_a_new_bridge_is_built_under_an_armed_recovery_timer(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    fake = _creation_fake()
    assert _create_bridge(setup_toolchain, monkeypatch, fake, "my-test-ssid", "my-test-password") == "my-test-ssid"
    joined = [" ".join(argv) for argv in fake.argvs()]
    arm = next(i for i, c in enumerate(joined) if c.startswith("sudo systemd-run --unit=sensors-bench-recovery-"))
    first_add = next(i for i, c in enumerate(joined) if "connection add" in c)
    # The MAC pin before anything comes up (2026-09-04 bench Pi4 lockout), and the timer disarmed only
    # after br0 holds an address and the default route.
    mac_pin = joined.index(f"sudo nmcli connection modify br0 bridge.mac-address {_DOC_MAC}")
    eth_up = joined.index("sudo nmcli connection up br0-eth0")
    ap_up = joined.index("sudo nmcli connection up br0-wifi-ap")
    route = max(i for i, c in enumerate(joined) if c.startswith("ip -o route get"))
    stop = next(i for i, c in enumerate(joined) if c.startswith("sudo systemctl stop sensors-bench-recovery-"))
    assert arm < first_add < mac_pin < eth_up < ap_up < route < stop
    assert any("connection add type wifi" in c and "wlan0" in c and "my-test-ssid" in c for c in joined)
    assert any("wifi-sec.pmf disable" in c for c in joined)  # load-bearing cyw43439 tuning


def test_the_bench_password_is_in_one_modify_and_never_shown(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # A throwaway password used once, passed plainly on that one command line; secrets= keeps it out of
    # the echoed command, and one taken from $BENCH_AP_PASSWORD is never printed.
    fake = _creation_fake()
    _create_bridge(setup_toolchain, monkeypatch, fake, "my-test-ssid", "my-test-password")
    holding = [call for call in fake.calls if any("my-test-password" in arg for arg in cast_argv(call["cmd"]))]
    assert len(holding) == 1
    argv = cast_argv(holding[0]["cmd"])
    assert argv[:5] == ["sudo", "nmcli", "connection", "modify", "br0-wifi-ap"]
    assert argv[argv.index("wifi-sec.psk") + 1] == "my-test-password"
    assert holding[0]["secrets"] == ("my-test-password",)
    assert not any("my-test-password" in str(call.get("stdin_text")) for call in fake.calls)
    assert not any(argv[3:4] == ["edit"] for argv in fake.argvs())
    out = capsys.readouterr().out
    assert "my-test-password" not in out
    assert "(password from $BENCH_AP_PASSWORD)" in out


def test_a_generated_bench_password_is_printed_once(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(setup_toolchain, "generate_bench_ap_credentials", lambda: ("generated-ssid", "generated-pw"))
    fake = _creation_fake()
    assert _create_bridge(setup_toolchain, monkeypatch, fake, None, None) == "generated-ssid"
    assert sum(any("generated-pw" in arg for arg in argv) for argv in fake.argvs()) == 1
    out = capsys.readouterr().out
    assert out.count("generated-pw") == 1
    assert "Save this password now" in out


def test_an_explicit_ssid_is_kept_when_the_password_is_generated(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain, "generate_bench_ap_credentials", lambda: ("generated-ssid", "generated-pw"))
    assert _create_bridge(setup_toolchain, monkeypatch, _creation_fake(), "my-test-ssid", None) == "my-test-ssid"


def test_a_bridge_that_never_forwards_leaves_the_recovery_timer_armed(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(setup_toolchain, "_BRIDGE_UP_POLL_S", 0)
    fake = _creation_fake(address="")
    with pytest.raises(setup_toolchain.SetupError, match="br0 got no address/default route within 0 s"):
        _create_bridge(setup_toolchain, monkeypatch, fake, "my-test-ssid", "my-test-password")
    assert not any("systemctl stop" in " ".join(argv) for argv in fake.argvs()), "the host's own way back was disarmed"
    assert "do not disarm it until the host is reachable" in capsys.readouterr().out


def test_no_bridge_change_is_made_when_the_recovery_timer_did_not_arm(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _creation_fake(timer_states=("inactive",))
    with pytest.raises(setup_toolchain.SetupError, match="did not arm - no bridge change was made"):
        _create_bridge(setup_toolchain, monkeypatch, fake, "my-test-ssid", "my-test-password")
    assert not any("connection add" in " ".join(argv) for argv in fake.argvs())


def _recovery_script(fake: _FakeRun) -> str:
    arm = next(argv for argv in fake.argvs() if "systemd-run" in argv)
    return arm[arm.index("-c") + 1]


def test_the_recovery_script_restores_the_uplinks_own_profile_quoted(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _creation_fake(profile="Wired connection 1")
    _create_bridge(setup_toolchain, monkeypatch, fake, "my-test-ssid", "my-test-password")
    script = _recovery_script(fake)
    assert "nmcli connection delete br0-wifi-ap || true" in script
    assert "nmcli connection up 'Wired connection 1'" in script


def test_with_no_uplink_profile_the_recovery_script_only_tears_down(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _creation_fake(profile="")
    _create_bridge(setup_toolchain, monkeypatch, fake, "my-test-ssid", "my-test-password")
    script = _recovery_script(fake)
    assert "nmcli connection delete br0 || true" in script
    assert "connection up" not in script


def test_the_bench_suite_derives_the_connection_names_from_this_module(setup_toolchain: ModuleType, repo_root: Path) -> None:
    # tests_hardware/harness.py re-exports these three for the bench tier, and must READ them from
    # here rather than carry its own literals: a rename would otherwise leave the bench tier looking
    # for a connection nobody creates, and its skip gate deselects rather than fails.
    harness_path = repo_root / "tests_hardware" / "harness.py"
    harness_src = harness_path.read_text()
    harness = load_script_module(harness_path, "harness")
    for attr in ("BENCH_BRIDGE_CONN", "BENCH_ETH_CONN", "BENCH_AP_CONN"):
        assert f"{attr} = setup_toolchain.{attr}" in harness_src, (
            f"tests_hardware/harness.py declares {attr} itself instead of reading it from this module - "
            "`env --tier bench` could then build a rig the bench tests cannot find"
        )
        assert getattr(harness, attr) == getattr(setup_toolchain, attr)


# --- project dependency install (uv sync / npm ci) -------------------------------------------------


def test_run_project_dependency_install_skips_npm_when_flag_set(setup_toolchain: ModuleType, tmp_path: Path, recorded_run: list[list[str]]) -> None:
    (tmp_path / "package.json").write_text("{}")
    setup_toolchain.run_project_dependency_install(tmp_path, tmp_path, skip_npm=True, skip_apt=True)
    assert recorded_run == [["uv", "sync"]]


def test_run_project_dependency_install_skips_npm_when_no_package_json(setup_toolchain: ModuleType, tmp_path: Path, recorded_run: list[list[str]]) -> None:
    setup_toolchain.run_project_dependency_install(tmp_path, tmp_path, skip_npm=False, skip_apt=True)
    assert recorded_run == [["uv", "sync"]]


def test_run_project_dependency_install_skips_npm_when_none_can_be_installed(
    setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]],
) -> None:
    # No .nvmrc to pin a version and no npm on PATH: nothing to install and nothing to run, so the
    # soft skip is still the right outcome - it is only the *silent* skip on a pinned repo that was wrong.
    (tmp_path / "package.json").write_text("{}")
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name: None)
    setup_toolchain.run_project_dependency_install(tmp_path, tmp_path, skip_npm=False, skip_apt=True)
    assert recorded_run == [["uv", "sync"]]


def test_run_project_dependency_install_runs_npm_ci_when_available(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    (tmp_path / "package.json").write_text("{}")
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name: f"/usr/bin/{name}")
    setup_toolchain.run_project_dependency_install(tmp_path, tmp_path, skip_npm=False, skip_apt=True)
    # The Node in use is named by its own --version, whichever install it is.
    assert recorded_run == [["uv", "sync"], ["/usr/bin/node", "--version"], ["npm", "ci"], ["npx", "playwright", "install", "chromium"]]


def _flaky_run(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, failures: int) -> "tuple[list[list[str]], list[float]]":
    # run() failing its first `failures` calls the way a 502 from a release download does, then succeeding.
    calls: list[list[str]] = []
    pauses: list[float] = []

    def fake_run(cmd: list[str], cwd: Path | None = None, *, check: bool = True, env: dict[str, str] | None = None, **_kwargs: object) -> str:
        calls.append(cmd)
        if len(calls) <= failures:
            raise setup_toolchain.SetupError(f"command failed (exit 1): {' '.join(cmd)}")
        return ""

    monkeypatch.setattr(setup_toolchain, "run", fake_run)
    monkeypatch.setattr(setup_toolchain.time, "sleep", pauses.append)
    return calls, pauses


def test_uv_sync_rides_out_a_transient_download_failure(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls, pauses = _flaky_run(setup_toolchain, monkeypatch, failures=2)
    setup_toolchain.run_project_dependency_install(tmp_path, tmp_path, skip_npm=True, skip_apt=True)
    assert calls == [["uv", "sync"]] * 3
    assert pauses == [10.0, 20.0]


def test_uv_sync_still_fails_loudly_once_every_attempt_failed(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls, pauses = _flaky_run(setup_toolchain, monkeypatch, failures=3)
    with pytest.raises(setup_toolchain.SetupError, match="uv sync"):
        setup_toolchain.run_project_dependency_install(tmp_path, tmp_path, skip_npm=True, skip_apt=True)
    assert len(calls) == setup_toolchain.NETWORK_ATTEMPTS == 3
    assert pauses == [10.0, 20.0]  # no pause after the last attempt


def test_uv_sync_that_succeeds_first_time_never_pauses(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls, pauses = _flaky_run(setup_toolchain, monkeypatch, failures=0)
    setup_toolchain.run_project_dependency_install(tmp_path, tmp_path, skip_npm=True, skip_apt=True)
    assert (calls, pauses) == ([["uv", "sync"]], [])


# --- the pinned Node install (.nvmrc) --------------------------------------------------------


def test_pinned_node_major_reads_nvmrc(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    (tmp_path / ".nvmrc").write_text("22\n")
    assert setup_toolchain.pinned_node_major(tmp_path) == "22"
    (tmp_path / ".nvmrc").write_text("v20.11.1\n")
    assert setup_toolchain.pinned_node_major(tmp_path) == "20"


def test_pinned_node_major_is_none_without_an_nvmrc(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    assert setup_toolchain.pinned_node_major(tmp_path) is None


def test_ensure_node_defers_to_a_matching_node_already_on_path(
    setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]],
) -> None:
    # The installer exists to make a bare machine work, never to override a correct Node the caller
    # already manages (nvm, a system install, CI's own setup-node).
    (tmp_path / ".nvmrc").write_text("22\n")
    monkeypatch.setattr(setup_toolchain, "node_on_path_matches", lambda major: True)
    assert setup_toolchain.ensure_node(tmp_path, tmp_path, skip_apt=True) is None
    assert recorded_run == []


def test_ensure_node_does_nothing_without_a_pin(setup_toolchain: ModuleType, tmp_path: Path, recorded_run: list[list[str]]) -> None:
    assert setup_toolchain.ensure_node(tmp_path, tmp_path, skip_apt=True) is None
    assert recorded_run == []


def test_ensure_node_reuses_an_already_installed_tree(
    setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]],
) -> None:
    # Idempotence: a second `env` run must not re-download a Node that is already extracted.
    (tmp_path / ".nvmrc").write_text("22\n")
    monkeypatch.setattr(setup_toolchain, "node_on_path_matches", lambda major: False)
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name, path=None: f"/usr/bin/{name}")
    monkeypatch.setattr(setup_toolchain, "_node_release", lambda major, env: ("node-v22.0.0-linux-arm64.tar.xz", "a" * 64))
    bindir = tmp_path / "node" / "node-v22.0.0-linux-arm64" / "bin"
    bindir.mkdir(parents=True)
    (bindir / "node").write_text("#!/bin/sh\n")
    assert setup_toolchain.ensure_node(tmp_path, tmp_path, skip_apt=True) == bindir
    assert recorded_run == [], "an already-installed Node was re-downloaded"
    # Recorded even when reused, so the tree in use is known to the leftover clean-up from now on.
    assert json.loads((tmp_path / "node" / "node-record.json").read_text()) == {"major": "22", "tarball": "node-v22.0.0-linux-arm64.tar.xz", "sha256": "a" * 64}


# --- CLI wiring ---------------------------------------------------------------------------------


def _main_refusing_to_run(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, argv: list[str]) -> int:
    # main() in-process on a temporary toolchain, every runner and the lock refusing: for what the parser
    # alone settles, so a parser that wrongly takes a command line fails here, never sets anything up.
    for runner in ("run_env", "run_setup", "run_test", "toolchain_lock"):
        monkeypatch.setattr(setup_toolchain, runner, lambda *_args, **_kwargs: pytest.fail("the command line was accepted"))
    monkeypatch.setattr(sys, "argv", ["setup_toolchain.py", *argv, *(["--toolchain-dir", str(tmp_path)] if argv[:1] in (["env"], ["setup"]) and "--help" not in argv else [])])
    with pytest.raises(SystemExit) as exited:
        setup_toolchain.main()
    return int(exited.value.code or 0)


def test_cli_env_help_lists_all_three_tiers(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert _main_refusing_to_run(setup_toolchain, monkeypatch, tmp_path, ["env", "--help"]) == 0
    assert "{generic,flash,bench}" in capsys.readouterr().out


def test_cli_env_requires_tier(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert _main_refusing_to_run(setup_toolchain, monkeypatch, tmp_path, ["env"]) != 0
    assert "--tier" in capsys.readouterr().err


def test_cli_env_rejects_unknown_tier(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert _main_refusing_to_run(setup_toolchain, monkeypatch, tmp_path, ["env", "--tier", "nope"]) != 0
    assert "invalid choice" in capsys.readouterr().err


# --- apt against a stalled mirror ----------------------------------------------------------------


def test_every_apt_call_times_out_and_retries_a_stalled_fetch(setup_toolchain: ModuleType, recorded_run: list[list[str]]) -> None:
    # A stalled mirror held CI's firmware jobs in this step until their 15-minute limit; each fetch now gives up after
    # the timeout and is retried, the attempt count the one every retried network step shares.
    setup_toolchain.ensure_apt_packages(["gcc-arm-none-eabi"], skip=False)
    timeout = str(setup_toolchain.APT_ACQUIRE_TIMEOUT_S)
    expected = ["-o", f"Acquire::Retries={setup_toolchain.NETWORK_ATTEMPTS - 1}", "-o", f"Acquire::http::Timeout={timeout}", "-o", f"Acquire::https::Timeout={timeout}"]
    apt_calls = [cmd for cmd in recorded_run if "apt-get" in cmd]
    assert len(apt_calls) == 3, recorded_run  # the list update, the download, the install from the cache
    for cmd in apt_calls:
        at = cmd.index("apt-get") + 1
        assert cmd[at : at + len(expected)] == expected, cmd


# --- run(): every command bounded, streamed and redacted ---------------------------------------------


def _alive(pid: int) -> bool:
    # Whether a process still runs; a zombie waiting for its reaper runs nothing, so it counts as gone.
    try:
        state = Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[0]
    except FileNotFoundError:
        return False
    return state != "Z"


def _gone_within(pid: int, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    return not _alive(pid)


_BACKGROUNDED_SLEEP = ["sh", "-c", 'sleep 30 & echo $! > "$1"; wait', "sh"]


def test_run_ends_a_stalled_command_with_its_whole_process_group(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    # The grandchild stands in for a git transport or a compiler a stalled step leaves behind: it must
    # not outlive the step's limit, or it keeps writing into a toolchain whose lock is already free.
    pid_file = tmp_path / "grandchild.pid"
    started = time.monotonic()
    with pytest.raises(setup_toolchain.SetupError, match=r"timed out after 0\.5 s: sh -c"):
        setup_toolchain.run([*_BACKGROUNDED_SLEEP, str(pid_file)], timeout_s=0.5)
    assert time.monotonic() - started < 7
    assert _gone_within(int(pid_file.read_text()), 5), "the grandchild outlived its step's limit"


class _FlagOnLine:
    # A stdout stand-in that creates `flag` once `line` was written to it. The command below waits for
    # that flag, so it can only finish if its first line reached stdout while it was still running.
    def __init__(self, line: str, flag: Path) -> None:
        self.line, self.flag, self.text = line, flag, ""

    def write(self, text: str) -> int:
        self.text += text
        if self.line in self.text:
            self.flag.touch()
        return len(text)

    def flush(self) -> None:
        pass


def test_run_streams_each_line_while_the_command_still_runs(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A stalled mirror must be named by the last line it printed, not by a log that only appears at exit.
    flag = tmp_path / "seen"
    out = _FlagOnLine("first", flag)
    monkeypatch.setattr(sys, "stdout", out)
    waits_for_flag = ["sh", "-c", 'echo first; while [ ! -e "$1" ]; do sleep 0.05; done; echo second', "sh", str(flag)]
    assert setup_toolchain.run(waits_for_flag, timeout_s=10) == "first\nsecond\n"
    assert out.text.index("first") < out.text.index("second")


def test_run_never_shows_a_secret_but_returns_it(setup_toolchain: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
    returned = setup_toolchain.run(["sh", "-c", 'echo "psk=$1"', "sh", "hunter2"], timeout_s=10, secrets=("hunter2",))
    assert returned == "psk=hunter2\n", "callers parse what a command printed, so the returned text keeps it"
    shown = capsys.readouterr().out
    assert "hunter2" not in shown
    assert '$ sh -c echo "psk=$1" sh ***' in shown
    assert "psk=***" in shown


def test_run_feeds_stdin_text_to_the_command(setup_toolchain: ModuleType) -> None:
    assert setup_toolchain.run(["cat"], timeout_s=10, stdin_text="br_netfilter\n") == "br_netfilter\n"


def test_run_names_a_failed_command_and_check_false_returns_its_output(setup_toolchain: ModuleType) -> None:
    with pytest.raises(setup_toolchain.SetupError, match=r"command failed \(exit 3\): sh -c"):
        setup_toolchain.run(["sh", "-c", "echo out; exit 3"], timeout_s=10)
    assert setup_toolchain.run(["sh", "-c", "echo out; exit 3"], check=False, timeout_s=10) == "out\n"


def test_a_command_that_may_ask_for_a_password_keeps_the_terminal(setup_toolchain: ModuleType) -> None:
    # sudo reads a password only from the controlling terminal, which a new session does not have.
    assert setup_toolchain._keeps_terminal(["sudo", "apt-get", "update"], terminal=False)
    assert setup_toolchain._keeps_terminal(["npx", "playwright", "install-deps", "chromium"], terminal=True)
    assert not setup_toolchain._keeps_terminal(["git", "clone", "--quiet", "u", "d"], terminal=False)


def test_only_a_terminal_command_shares_the_callers_process_group(setup_toolchain: ModuleType) -> None:
    probe = [sys.executable, "-c", "import os; print(os.getpgrp())"]
    assert int(setup_toolchain.run(probe, timeout_s=30, terminal=True)) == os.getpgrp()
    assert int(setup_toolchain.run(probe, timeout_s=30)) != os.getpgrp()


_RUN_THEN_WAIT_FOR_A_SIGNAL = """import sys
sys.path.insert(0, sys.argv[1])
import setup_toolchain as st
with st._stop_commands_on_termination():
    st.run(["sh", "-c", 'sleep 30 & echo $! > "$1"; wait', "sh", sys.argv[2]], timeout_s=60)
"""


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGHUP, signal.SIGINT])
def test_a_signalled_installer_takes_its_running_command_down_with_it(repo_root: Path, tmp_path: Path, sig: signal.Signals) -> None:
    # A command in its own session misses the signal sent to the installer's group (Ctrl-C, timeout(1), a
    # cancelled job), so the installer stops it on its way out instead of leaving it running unlocked.
    pid_file = tmp_path / "grandchild.pid"
    script = [sys.executable, "-c", _RUN_THEN_WAIT_FOR_A_SIGNAL, str(repo_root / "toolchain"), str(pid_file)]
    proc = subprocess.Popen(script, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 30
    while not (pid_file.exists() and pid_file.read_text().strip()) and time.monotonic() < deadline:
        time.sleep(0.05)
    proc.send_signal(sig)
    _, err = proc.communicate(timeout=30)
    assert proc.returncode != 0, err
    assert _gone_within(int(pid_file.read_text()), 10), f"the command survived its installer's {sig.name}"


def test_run_retried_hands_every_attempt_the_same_env_limit_and_secrets(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, object]] = []

    def fake_run(cmd: list[str], cwd: Path | None = None, **kwargs: object) -> str:
        seen.append(kwargs)
        if len(seen) < setup_toolchain.NETWORK_ATTEMPTS:
            raise setup_toolchain.SetupError("command failed (exit 128): git clone")
        return "ok"

    monkeypatch.setattr(setup_toolchain, "run", fake_run)
    monkeypatch.setattr(setup_toolchain.time, "sleep", lambda _s: None)
    env = {"PATH": "/usr/bin", "HTTPS_PROXY": "http://proxy.invalid:3128"}
    assert setup_toolchain.run_retried(["git", "clone", "u", "d"], env=env, timeout_s=42, secrets=("tok",)) == "ok"
    assert seen == [{"env": env, "timeout_s": 42, "secrets": ("tok",)}] * 3


def test_the_last_failed_attempt_names_the_step_and_the_fix(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    _flaky_run(setup_toolchain, monkeypatch, failures=3)
    with pytest.raises(setup_toolchain.SetupError, match=r"git fetch.*all 3 attempts failed.*re-run"):
        setup_toolchain.run_retried(["git", "fetch"], timeout_s=1)


def test_node_on_path_matches_treats_a_hung_probe_as_no_match(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # A node that never answers --version must not hold the installer forever.
    def hung(cmd: list[str], **kwargs: object) -> NoReturn:
        assert kwargs.get("timeout") == setup_toolchain._REMOTE_QUERY_TIMEOUT_S
        raise subprocess.TimeoutExpired(cmd, 1)

    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name: "/usr/bin/node")
    monkeypatch.setattr(setup_toolchain.subprocess, "run", hung)
    assert setup_toolchain.node_on_path_matches("22") is False


# --- versions.toml as a typed table ------------------------------------------------------------------

_VALID_VERSIONS = '[micropython]\nref = "v1.29.0"\n\n[toolchain]\nboard = "RPI_PICO_W"\napt_packages = ["git"]\n\n[lwip]\nTCP_MSS = 800\n'


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (_VALID_VERSIONS.replace('ref = "v1.29.0"\n', ""), r"\[micropython\] ref is missing"),
        (_VALID_VERSIONS.replace('ref = "v1.29.0"', 'ref = ""'), r"\[micropython\] ref must be a non-empty string"),
        (_VALID_VERSIONS.replace('board = "RPI_PICO_W"\n', ""), r"\[toolchain\] board is missing"),
        (_VALID_VERSIONS.replace('apt_packages = ["git"]', 'apt_packages = "git"'), r"\[toolchain\] apt_packages must be a list of strings"),
        (_VALID_VERSIONS.partition("[lwip]")[0], r"\[lwip\] is missing"),
        ('[micropython\nref = "v1.29.0"\n', r"cannot be read"),
    ],
)
def test_load_versions_names_the_file_and_its_first_defect(setup_toolchain: ModuleType, tmp_path: Path, text: str, message: str) -> None:
    path = tmp_path / "versions.toml"
    path.write_text(text)
    with pytest.raises(setup_toolchain.SetupError, match=message) as raised:
        setup_toolchain.load_versions(path)
    assert str(path) in str(raised.value)


def test_load_versions_names_a_file_it_cannot_open(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    with pytest.raises(setup_toolchain.SetupError, match="cannot be read") as raised:
        setup_toolchain.load_versions(tmp_path)  # a directory
    assert str(tmp_path) in str(raised.value)


def test_the_pinned_versions_file_loads_as_tomllib_reads_it(setup_toolchain: ModuleType, repo_root: Path) -> None:
    path = repo_root / "toolchain" / "versions.toml"
    with path.open("rb") as f:
        raw = tomllib.load(f)
    expected = {
        "micropython": {"ref": raw["micropython"]["ref"]},
        "toolchain": {"board": raw["toolchain"]["board"], "apt_packages": raw["toolchain"]["apt_packages"]},
        "lwip": raw["lwip"],
    }
    assert setup_toolchain.load_versions(path) == expected


# --- one lock per toolchain directory ----------------------------------------------------------------


def _lock_held(setup_toolchain: ModuleType, toolchain_dir: Path) -> bool:
    # Whether any open file holds the toolchain lock: flock() on a fresh descriptor conflicts even
    # with one held by this same process.
    with (toolchain_dir / setup_toolchain.TOOLCHAIN_LOCK).open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(f, fcntl.LOCK_UN)
        return False


_HOLD_THE_LOCK = """import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import setup_toolchain as st
with st.toolchain_lock(Path(sys.argv[2])):
    print("held", flush=True)
    sys.stdin.read()
"""


def test_a_second_run_on_one_toolchain_fails_at_once_naming_the_first(setup_toolchain: ModuleType, repo_root: Path, tmp_path: Path) -> None:
    toolchain_dir = tmp_path / "toolchain"
    holder = subprocess.Popen(
        [sys.executable, "-c", _HOLD_THE_LOCK, str(repo_root / "toolchain"), str(toolchain_dir)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline() == "held\n"
        with pytest.raises(setup_toolchain.SetupError, match=rf"another setup or firmware build \(pid {holder.pid}\) is using {toolchain_dir} - wait"), setup_toolchain.toolchain_lock(toolchain_dir):
            pytest.fail("a second holder got the lock")
    finally:
        holder.kill()  # no clean release: the OS must drop the lock with its holder
        holder.communicate(timeout=10)
    with setup_toolchain.toolchain_lock(toolchain_dir):
        assert _lock_held(setup_toolchain, toolchain_dir)
    assert not _lock_held(setup_toolchain, toolchain_dir)


def test_the_lock_creates_its_toolchain_directory(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    toolchain_dir = tmp_path / "not" / "there" / "yet"
    with setup_toolchain.toolchain_lock(toolchain_dir):
        assert (toolchain_dir / setup_toolchain.TOOLCHAIN_LOCK).read_text().strip() == str(os.getpid())


def test_main_runs_a_test_under_the_lock(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    held: list[bool] = []

    def fake_run_test(args: argparse.Namespace, versions: object) -> int:
        held.append(_lock_held(setup_toolchain, tmp_path))
        return 0

    monkeypatch.setattr(setup_toolchain, "run_test", fake_run_test)
    monkeypatch.setattr(sys, "argv", ["setup_toolchain.py", "test", "--toolchain-dir", str(tmp_path)])
    assert setup_toolchain.main() == 0
    assert held == [True]
    assert not _lock_held(setup_toolchain, tmp_path)


def test_main_env_holds_one_lock_across_setup_and_the_node_install(
    setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]],
) -> None:
    # run_env() runs run_setup() and then ensure_node(), which writes <toolchain>/node: one lock for the
    # whole command, so neither step can take a second one and refuse its own process.
    held: dict[str, bool] = {}

    def fake_run_setup(args: argparse.Namespace, versions_path: Path, versions: object, **_kwargs: object) -> int:
        held["setup"] = _lock_held(setup_toolchain, tmp_path)
        return 0

    def fake_ensure_node(toolchain_dir: Path, repo_root: Path, **_kwargs: object) -> None:
        held["node"] = _lock_held(setup_toolchain, tmp_path)

    monkeypatch.setattr(setup_toolchain, "run_setup", fake_run_setup)
    monkeypatch.setattr(setup_toolchain, "ensure_node", fake_ensure_node)
    monkeypatch.setattr(sys, "argv", ["setup_toolchain.py", "env", "--tier", "generic", "--skip-apt", "--toolchain-dir", str(tmp_path)])
    assert setup_toolchain.main() == 0
    assert held == {"setup": True, "node": True}


# --- the toolchain record ------------------------------------------------------------------------------


def _a_record() -> dict[str, object]:
    return {
        "pinned_ref": "v1.29.0",
        "built_ref": "v1.29.0",
        "micropython_commit": "d" * 40,
        "pico_sdk_commit": "b" * 40,
        "pico_sdk_describe": "2.3.0",
        "picotool_tag": "2.3.1",
        "picotool_version": "picotool v2.3.1 (Linux, GNU-13.3.0, Release)",
        "board": "RPI_PICO_W",
        "lwip": {"TCP_MSS": 800},
        "input_sha256": {"versions.toml": "c" * 64},
        "compilers": {"gcc": "gcc (Ubuntu 13.3.0-6ubuntu2~24.04) 13.3.0"},
        "unix_binaries": ["build-standard", "build-settrace", "build-lwip"],
        "recorded_utc": "2026-10-08T00:00:00Z",
    }


def test_the_toolchain_record_round_trips_every_key(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    record = _a_record()
    setup_toolchain.write_toolchain_record(tmp_path, record)
    assert setup_toolchain.read_toolchain_record(tmp_path) == record
    assert list(json.loads((tmp_path / setup_toolchain.TOOLCHAIN_RECORD).read_text())) == sorted(record)
    assert [p.name for p in tmp_path.iterdir()] == [setup_toolchain.TOOLCHAIN_RECORD], "the write left its temporary file behind"


@pytest.mark.parametrize("text", [None, "{not json", "[]", '{"board": "RPI_PICO_W"}'])
def test_a_missing_or_malformed_record_reads_as_none(setup_toolchain: ModuleType, tmp_path: Path, text: str | None) -> None:
    # Anything but a complete record means a toolchain nobody verified: the consumers then rebuild or refuse.
    if text is not None:
        (tmp_path / setup_toolchain.TOOLCHAIN_RECORD).write_text(text)
    assert setup_toolchain.read_toolchain_record(tmp_path) is None


def _fake_toolchain_dir(root: Path) -> Path:
    # Just enough of a toolchain for run_test()'s own presence check.
    toolchain_dir = root / "toolchain"
    (toolchain_dir / "micropython" / "mpy-cross").mkdir(parents=True)
    (toolchain_dir / "micropython" / "ports" / "rp2").mkdir(parents=True)
    return toolchain_dir


_PROBE_ANSWERS = {
    ("git", "rev-parse", "HEAD"): "d" * 40 + "\n",
    ("git", "describe", "--tags", "--always"): "v1.29.0\n",
    ("arm-none-eabi-gcc", "--version"): "arm-none-eabi-gcc (15:13.2.rel1-2) 13.2.1 20231009\nCopyright (C) 2023\n",
    ("gcc", "--version"): "gcc (Ubuntu 13.3.0-6ubuntu2~24.04) 13.3.0\nCopyright (C) 2023\n",
    ("git", "submodule", "update", "--init", "lib/mbedtls"): "",
}


def _answer_record_probes(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
        return _PROBE_ANSWERS[tuple(cmd)]

    monkeypatch.setattr(setup_toolchain, "run", fake_run)


def _expected_input_hashes(repo_root: Path) -> dict[str, str]:
    toolchain = repo_root / "toolchain"
    return {name: hashlib.sha256((toolchain / name).read_bytes()).hexdigest() for name in ("versions.toml", "setup_toolchain.py", "micropython_overrides.py")}


def test_an_interrupted_test_run_leaves_no_record(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toolchain_dir = _fake_toolchain_dir(tmp_path)
    setup_toolchain.write_toolchain_record(toolchain_dir, _a_record())  # an earlier run's

    def interrupted(*_args: object) -> NoReturn:
        raise setup_toolchain.SetupError("Unix port build reported an error (see log above)")

    monkeypatch.setattr(setup_toolchain, "run_verification_sequence", interrupted)
    versions = setup_toolchain.load_versions(setup_toolchain.VERSIONS_PATH)
    with pytest.raises(setup_toolchain.SetupError, match="Unix port build"):
        setup_toolchain.run_test(argparse.Namespace(toolchain_dir=toolchain_dir, jobs=1), versions)
    assert not (toolchain_dir / setup_toolchain.TOOLCHAIN_RECORD).exists()


def test_a_test_run_records_what_it_verified(setup_toolchain: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toolchain_dir = _fake_toolchain_dir(tmp_path)
    monkeypatch.setattr(setup_toolchain, "run_verification_sequence", lambda *_args: (Path("mpy-cross"), Path("micropython")))
    _answer_record_probes(setup_toolchain, monkeypatch)
    versions = setup_toolchain.load_versions(setup_toolchain.VERSIONS_PATH)
    assert setup_toolchain.run_test(argparse.Namespace(toolchain_dir=toolchain_dir, jobs=1), versions) == 0
    record = setup_toolchain.read_toolchain_record(toolchain_dir)
    assert record is not None
    assert record["unix_binaries"] == ["build-standard", "build-settrace", "build-lwip"]
    assert (record["pinned_ref"], record["built_ref"], record["micropython_commit"]) == (versions["micropython"]["ref"], "v1.29.0", "d" * 40)
    assert (record["board"], record["lwip"]) == (versions["toolchain"]["board"], versions["lwip"])
    # Offline, with no earlier record: nothing was derived, so nothing is claimed.
    assert [record[key] for key in ("pico_sdk_commit", "pico_sdk_describe", "picotool_tag", "picotool_version")] == [None] * 4
    assert record["compilers"] == {"arm-none-eabi-gcc": "arm-none-eabi-gcc (15:13.2.rel1-2) 13.2.1 20231009", "gcc": "gcc (Ubuntu 13.3.0-6ubuntu2~24.04) 13.3.0"}
    assert record["input_sha256"] == _expected_input_hashes(repo_root)


def test_an_offline_test_run_keeps_what_the_setup_before_it_derived(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toolchain_dir = _fake_toolchain_dir(tmp_path)
    earlier = _a_record() | {"built_ref": "d" * 7}  # an off-pin setup of this very commit
    setup_toolchain.write_toolchain_record(toolchain_dir, earlier)
    monkeypatch.setattr(setup_toolchain, "run_verification_sequence", lambda *_args: (Path("mpy-cross"), Path("micropython")))
    _answer_record_probes(setup_toolchain, monkeypatch)
    setup_toolchain.run_test(argparse.Namespace(toolchain_dir=toolchain_dir, jobs=1), setup_toolchain.load_versions(setup_toolchain.VERSIONS_PATH))
    record = setup_toolchain.read_toolchain_record(toolchain_dir)
    assert record is not None
    for key in ("built_ref", "pico_sdk_commit", "pico_sdk_describe", "picotool_tag", "picotool_version"):
        assert record[key] == earlier[key], key


def test_a_test_run_on_a_moved_checkout_claims_nothing_it_did_not_derive(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The earlier setup derived pico-sdk and picotool for another commit; carried over, they would be stale.
    toolchain_dir = _fake_toolchain_dir(tmp_path)
    setup_toolchain.write_toolchain_record(toolchain_dir, _a_record() | {"micropython_commit": "e" * 40, "built_ref": "v1.28.0"})
    monkeypatch.setattr(setup_toolchain, "run_verification_sequence", lambda *_args: (Path("mpy-cross"), Path("micropython")))
    _answer_record_probes(setup_toolchain, monkeypatch)
    setup_toolchain.run_test(argparse.Namespace(toolchain_dir=toolchain_dir, jobs=1), setup_toolchain.load_versions(setup_toolchain.VERSIONS_PATH))
    record = setup_toolchain.read_toolchain_record(toolchain_dir)
    assert record is not None
    assert record["built_ref"] == "v1.29.0", "the checkout's own describe, not the earlier setup's ref"
    assert [record[key] for key in ("pico_sdk_commit", "pico_sdk_describe", "picotool_tag", "picotool_version")] == [None] * 4


def test_a_setup_run_drops_the_old_record_before_moving_the_checkout(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The checkout moves long before the verification starts: a record kept until then would describe
    # binaries the checkout no longer matches, should the run die in between.
    toolchain_dir = tmp_path / "toolchain"
    toolchain_dir.mkdir()
    setup_toolchain.write_toolchain_record(toolchain_dir, _a_record())
    record_seen: list[object] = []
    monkeypatch.setattr(setup_toolchain, "ensure_repo_at_ref", lambda url, dest, ref: record_seen.append(setup_toolchain.read_toolchain_record(toolchain_dir)))
    monkeypatch.setattr(setup_toolchain, "derive_pico_sdk_commit", lambda micropython_dir, ref: "b" * 40)
    monkeypatch.setattr(setup_toolchain, "derive_picotool_ref", lambda pico_sdk_dir, commit: ("2.3.1", "2.3.0"))
    monkeypatch.setattr(setup_toolchain, "build_and_install_picotool", lambda *_args, **_kwargs: "picotool v2.3.1 (Linux, GNU-13.3.0, Release)")
    monkeypatch.setattr(setup_toolchain, "fetch_rp2_submodules", lambda *_args: None)
    monkeypatch.setattr(setup_toolchain, "fetch_unix_submodules", lambda *_args: None)
    monkeypatch.setattr(setup_toolchain, "run_verification_sequence", lambda *_args: (Path("mpy-cross"), Path("micropython")))
    _answer_record_probes(setup_toolchain, monkeypatch)
    versions = setup_toolchain.load_versions(setup_toolchain.VERSIONS_PATH)
    args = argparse.Namespace(micropython_ref=None, latest=False, toolchain_dir=toolchain_dir, clean=False, skip_apt=True, jobs=1)
    assert setup_toolchain.run_setup(args, setup_toolchain.VERSIONS_PATH, versions) == 0
    assert record_seen == [None, None, None], "a record outlived the moment its checkout moved"
    record = setup_toolchain.read_toolchain_record(toolchain_dir)
    assert record is not None
    derived = [record[key] for key in ("built_ref", "pico_sdk_commit", "pico_sdk_describe", "picotool_tag", "picotool_version")]
    assert derived == [versions["micropython"]["ref"], "b" * 40, "2.3.0", "2.3.1", "picotool v2.3.1 (Linux, GNU-13.3.0, Release)"]


# --- build diagnostics -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("output", "message"),
    [
        ("main.c:1:1: error: expected ';'\n", "mpy-cross build reported an error"),
        ("main.c:1:1: warning: unused variable\n", "mpy-cross build produced warnings .* every build is warning-free"),
    ],
)
def test_build_mpy_cross_fails_on_a_diagnostic_even_at_exit_0(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: str, message: str) -> None:
    monkeypatch.setattr(setup_toolchain, "run", lambda cmd, cwd=None, **_kwargs: output if cmd[0] == "make" else "")
    with pytest.raises(setup_toolchain.SetupError, match=message):
        setup_toolchain.build_mpy_cross(tmp_path, 1)


def test_build_mpy_cross_returns_its_binary_after_a_clean_build(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    binary = tmp_path / "mpy-cross" / "build" / "mpy-cross"
    binary.parent.mkdir(parents=True)
    binary.write_text("")
    monkeypatch.setattr(setup_toolchain, "run", lambda cmd, cwd=None, **_kwargs: "CC main.c\n" if cmd[0] == "make" else "MicroPython v1.29.0\n")
    assert setup_toolchain.build_mpy_cross(tmp_path, 1) == binary


def test_two_overrides_setting_one_make_variable_are_refused(setup_toolchain: ModuleType) -> None:
    # Two overrides both claiming a variable would leave the last one silently winning on the make line.
    assert setup_toolchain._merge_make_vars({"BOARD": "RPI_PICO_W"}, {"USER_C_MODULES": "/x"}) == {"BOARD": "RPI_PICO_W", "USER_C_MODULES": "/x"}
    with pytest.raises(setup_toolchain.SetupError, match="BOARD_DIR"):
        setup_toolchain._merge_make_vars({"BOARD_DIR": "/a"}, {"BOARD_DIR": "/b"})


def test_a_firmware_build_names_the_manifest_it_was_given(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # scripts/build_firmware.py hands every device image its own manifest: the log names that file, never
    # the installer's frozen verification module, and the readback gets the override's own copy.
    micropython_dir = tmp_path / "micropython"
    build_dir = micropython_dir / "ports" / "rp2" / "build-RPI_PICO_W"
    modules_dir = tmp_path / "build_overrides" / "modlwip_eagain"

    def fake_run(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
        build_dir.mkdir(parents=True, exist_ok=True)
        (build_dir / "firmware.uf2").write_bytes(b"")
        return ""

    overrides = setup_toolchain.micropython_overrides
    readbacks: list[tuple[object, ...]] = []
    monkeypatch.setattr(setup_toolchain, "run", fake_run)
    monkeypatch.setattr(overrides, "apply_lwip_connection_counts_override", lambda *_args, **_kwargs: {"BOARD": "RPI_PICO_W"})
    monkeypatch.setattr(overrides, "apply_modlwip_eagain_override", lambda *_args, **_kwargs: {"USER_C_MODULES": str(modules_dir)})
    monkeypatch.setattr(overrides, "verify_lwip_macros_in_build", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(overrides, "verify_modlwip_eagain_in_build", lambda *args, **_kwargs: readbacks.append(args))
    monkeypatch.setattr(overrides, "verify_tick_offset_in_build", lambda *_args, **_kwargs: None)
    manifest = tmp_path / "manifest.py"
    assert setup_toolchain.build_firmware(micropython_dir, "RPI_PICO_W", 2, frozen_manifest=manifest, toolchain_dir=tmp_path, lwip_macros={}) == build_dir / "firmware.uf2"
    shown = capsys.readouterr().out
    assert f"frozen manifest {manifest}" in shown
    assert "frozen verification module" not in shown
    assert readbacks == [(build_dir, micropython_dir, modules_dir / overrides.MODLWIP_COPY_NAME)]


def test_the_summary_names_all_three_unix_binaries(setup_toolchain: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    unix_dir = tmp_path / "ports" / "unix"
    setup_toolchain.print_verification_summary("RPI_PICO_W", tmp_path / "mpy-cross", unix_dir / "build-standard" / "micropython")
    shown = capsys.readouterr().out
    for name in setup_toolchain.CURRENT_UNIX_BUILD_DIRS:
        assert str(unix_dir / name / "micropython") in shown, name


# --- apt: a bounded list update, a retried download, one install from the cache -------------------


def _only_these_network_variables(monkeypatch: pytest.MonkeyPatch, setup_toolchain: ModuleType, **values: str) -> None:
    for name in setup_toolchain.NETWORK_ENV_EXTRA:
        monkeypatch.delenv(name, raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def test_apt_keeps_the_proxy_in_the_environment_through_sudo(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # sudo's env_reset would drop the proxy a download needs; --preserve-env names exactly what to keep, and the
    # proxy URL (which can carry credentials) travels in the environment, never in argv.
    _only_these_network_variables(monkeypatch, setup_toolchain, HTTPS_PROXY="http://user:pw@proxy.invalid:3128", SSL_CERT_FILE="/etc/ca.pem")
    fake = _FakeRun()
    monkeypatch.setattr(setup_toolchain, "run", fake)
    setup_toolchain.ensure_apt_packages(["git", "cmake"], skip=False)
    sudo = ["sudo", "--preserve-env=DEBIAN_FRONTEND,HTTPS_PROXY,SSL_CERT_FILE", "apt-get", *setup_toolchain.apt_options()]
    tail = ["-y", "--no-install-recommends", "git", "cmake"]
    assert fake.argvs() == [[*sudo, "update"], [*sudo, "install", "--download-only", *tail], [*sudo, "install", *tail]]
    budgets = [call["timeout_s"] for call in fake.calls]
    assert budgets == [setup_toolchain._APT_STEP_TIMEOUT_S, setup_toolchain._APT_STEP_TIMEOUT_S, setup_toolchain._BUILD_STEP_TIMEOUT_S]
    assert fake.calls[0]["check"] is False, "an unrelated broken source must not stop the install"
    for call in fake.calls:
        env = call["env"]
        assert isinstance(env, dict)
        assert (env["HTTPS_PROXY"], env["SSL_CERT_FILE"], env["DEBIAN_FRONTEND"]) == ("http://user:pw@proxy.invalid:3128", "/etc/ca.pem", "noninteractive")
        assert not any("proxy.invalid" in arg for arg in cast_argv(call["cmd"]))


def test_apt_without_proxy_variables_preserves_only_the_frontend(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    _only_these_network_variables(monkeypatch, setup_toolchain)
    fake = _FakeRun()
    monkeypatch.setattr(setup_toolchain, "run", fake)
    setup_toolchain.ensure_apt_packages(["git"], skip=False)
    assert {tuple(argv[:2]) for argv in fake.argvs()} == {("sudo", "--preserve-env=DEBIAN_FRONTEND")}


def test_a_stalled_download_is_retried_but_the_install_never_is(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # Only the download is retried, and it never reaches dpkg: a retry that killed dpkg mid-configure would leave
    # the host's package database interrupted until someone runs `dpkg --configure -a`.
    timed_out = setup_toolchain.SetupError("timed out after 150 s: apt-get install --download-only")
    fake = _FakeRun({("sudo",): ""})
    calls: list[list[str]] = []

    def stalls_twice(cmd: list[str], cwd: Path | None = None, **kwargs: object) -> str:
        calls.append(cmd)
        if "--download-only" in cmd and sum("--download-only" in c for c in calls) < setup_toolchain.NETWORK_ATTEMPTS:
            raise timed_out
        return fake(cmd, cwd, **kwargs)

    monkeypatch.setattr(setup_toolchain, "run", stalls_twice)
    monkeypatch.setattr(setup_toolchain.time, "sleep", lambda _s: None)
    setup_toolchain.ensure_apt_packages(["git"], skip=False)
    assert sum("--download-only" in c for c in calls) == setup_toolchain.NETWORK_ATTEMPTS
    assert sum("install" in c and "--download-only" not in c for c in calls) == 1


def test_a_failed_install_runs_once_and_names_the_ways_out(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    failed = setup_toolchain.SetupError("command failed (exit 100): sudo apt-get install")
    fake = _FakeRun()

    def install_fails(cmd: list[str], cwd: Path | None = None, **kwargs: object) -> str:
        if "install" in cmd and "--download-only" not in cmd:
            fake(cmd, cwd, **kwargs)
            raise failed
        return fake(cmd, cwd, **kwargs)

    monkeypatch.setattr(setup_toolchain, "run", install_fails)
    with pytest.raises(setup_toolchain.SetupError, match=r"exit 100.*env_keep.*--skip-apt"):
        setup_toolchain.ensure_apt_packages(["git"], skip=False)
    assert sum("install" in argv and "--download-only" not in argv for argv in fake.argvs()) == 1


def test_a_stalled_list_update_is_logged_and_the_install_goes_on(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    fake = _FakeRun({("sudo",): [setup_toolchain.SetupError("timed out after 150 s: sudo apt-get update"), ""]})
    monkeypatch.setattr(setup_toolchain, "run", fake)
    setup_toolchain.ensure_apt_packages(["git"], skip=False)
    assert len(fake.calls) == 3
    assert "apt-get update did not finish" in capsys.readouterr().out


# --- clones, fetches and submodules: retried, an interrupted clone named --------------------------------


def test_a_failed_clone_attempt_leaves_nothing_for_the_retry(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = tmp_path / "micropython"
    existed_before: list[bool] = []

    def partial_twice(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
        existed_before.append(dest.exists())
        (dest / ".git").mkdir(parents=True)
        if len(existed_before) < setup_toolchain.NETWORK_ATTEMPTS:
            raise setup_toolchain.SetupError("command failed (exit 128): git clone")
        return ""

    monkeypatch.setattr(setup_toolchain, "run", partial_twice)
    monkeypatch.setattr(setup_toolchain.time, "sleep", lambda _s: None)
    setup_toolchain.clone_full("https://example.invalid/micropython.git", dest)
    assert existed_before == [False] * setup_toolchain.NETWORK_ATTEMPTS


def test_clone_full_refuses_a_directory_that_is_already_there(setup_toolchain: ModuleType, tmp_path: Path, recorded_run: list[list[str]]) -> None:
    # Its retry removes what a failed attempt created; a directory that was already there is never its to remove.
    dest = tmp_path / "micropython"
    dest.mkdir()
    (dest / "work.txt").write_text("mine")
    with pytest.raises(setup_toolchain.SetupError, match="already exists"):
        setup_toolchain.clone_full("https://example.invalid/micropython.git", dest)
    assert (dest / "work.txt").read_text() == "mine"
    assert recorded_run == []


@pytest.mark.parametrize("left_behind", [[".git", "partial.c"], ["partial.c"]])
def test_an_interrupted_clone_is_named_and_left_alone(setup_toolchain: ModuleType, tmp_path: Path, left_behind: list[str]) -> None:
    # A real git against a fabricated clone with no HEAD (or no .git at all): never fetched into, never deleted.
    dest = tmp_path / "micropython"
    dest.mkdir()
    (dest / "partial.c").write_text("x")
    if ".git" in left_behind:
        (dest / ".git").mkdir()
    with pytest.raises(setup_toolchain.SetupError, match=r"is not a complete clone \(an interrupted clone\?\) - remove it and re-run setup"):
        setup_toolchain.ensure_repo_at_ref("https://example.invalid/micropython.git", dest, "v1.29.0")
    assert sorted(p.name for p in dest.iterdir()) == left_behind


def test_every_network_step_rides_out_one_failed_attempt(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sha = "0123456789abcdef0123456789abcdef01234567"
    network_steps = [
        ["git", "fetch", "--quiet", "--tags", "--force", "origin"],
        ["git", "fetch", "--quiet", "origin", sha],
        ["make", "BOARD=RPI_PICO_W", "submodules"],
        ["make", "submodules", "MICROPY_PY_LWIP=1"],
        ["git", "ls-remote", "--tags", setup_toolchain.MICROPYTHON_URL],
        ["git", "ls-remote", "--tags", setup_toolchain.PICOTOOL_URL],
    ]
    answers = {"ls-remote": "abc\trefs/tags/v1.29.0\nabd\trefs/tags/2.3.1\n", "describe": "2.3.0\n"}
    calls: list[list[str]] = []

    def fails_first_network_attempt(cmd: list[str], cwd: Path | None = None, **_kwargs: object) -> str:
        first = cmd not in calls
        calls.append(cmd)
        if cmd in network_steps and first:
            raise setup_toolchain.SetupError(f"command failed (exit 128): {' '.join(cmd)}")
        if cmd[:3] == ["git", "checkout", "--quiet"] and cmd[3] == sha:
            raise setup_toolchain.SetupError("command failed (exit 1): the commit is not here yet")
        return answers.get(cmd[1], "")

    monkeypatch.setattr(setup_toolchain, "run", fails_first_network_attempt)
    monkeypatch.setattr(setup_toolchain.time, "sleep", lambda _s: None)
    setup_toolchain.checkout_ref(tmp_path, sha)
    setup_toolchain.fetch_rp2_submodules(tmp_path, "RPI_PICO_W")
    setup_toolchain.fetch_unix_submodules(tmp_path)
    assert setup_toolchain.latest_stable_micropython_ref() == "v1.29.0"
    assert setup_toolchain.derive_picotool_ref(tmp_path, "b" * 40) == ("2.3.1", "2.3.0")
    for argv in network_steps:
        assert calls.count(argv) == 2, argv


# --- the MicroPython pin: written only as one exact line -------------------------------------------------

_PINNED = '# a comment\n[micropython]\nref = "v1.29.0"\n\n[toolchain]\nboard = "RPI_PICO_W"\napt_packages = ["git"]\n\n[lwip]\nTCP_MSS = 800\n'


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (_PINNED.replace('ref = "v1.29.0"\n', ""), r'has no `ref = "…"` line under \[micropython\] - nothing was written'),
        (_PINNED.replace('ref = "v1.29.0"\n', 'ref = "v1.29.0"\nref = "v1.28.0"\n'), r'has 2 `ref = "…"` lines - the pin must be exactly one'),
        (_PINNED.replace('ref = "v1.29.0"\n', "").replace('board = "RPI_PICO_W"\n', 'board = "RPI_PICO_W"\nref = "v1.29.0"\n'), r"\[micropython\]"),
    ],
)
def test_the_pin_writer_refuses_a_missing_duplicate_or_misplaced_ref(setup_toolchain: ModuleType, tmp_path: Path, text: str, message: str) -> None:
    path = tmp_path / "versions.toml"
    path.write_text(text)
    with pytest.raises(setup_toolchain.SetupError, match=message):
        setup_toolchain.write_micropython_ref(path, "v1.30.0")
    assert path.read_text() == text, "a refused write changed the file"
    assert [p.name for p in tmp_path.iterdir()] == ["versions.toml"]


def test_the_pin_writer_changes_the_one_ref_line_and_nothing_else(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    path = tmp_path / "versions.toml"
    path.write_text(_PINNED)
    setup_toolchain.write_micropython_ref(path, "v1.30.0")
    assert path.read_text() == _PINNED.replace('ref = "v1.29.0"', 'ref = "v1.30.0"')
    assert [p.name for p in tmp_path.iterdir()] == ["versions.toml"]


# --- a moved or off-pin build announces the platform re-check ---------------------------------------------


def _quiet_setup(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    # Every step of run_setup() that would touch the network, apt, sudo or a compiler, stubbed.
    monkeypatch.setattr(setup_toolchain, "ensure_repo_at_ref", lambda url, dest, ref: None)
    monkeypatch.setattr(setup_toolchain, "derive_pico_sdk_commit", lambda micropython_dir, ref: "b" * 40)
    monkeypatch.setattr(setup_toolchain, "derive_picotool_ref", lambda pico_sdk_dir, commit: ("2.3.1", "2.3.0"))
    monkeypatch.setattr(setup_toolchain, "build_and_install_picotool", lambda *_args, **_kwargs: "picotool v2.3.1 (Linux, GNU-13.3.0, Release)")
    monkeypatch.setattr(setup_toolchain, "fetch_rp2_submodules", lambda *_args: None)
    monkeypatch.setattr(setup_toolchain, "fetch_unix_submodules", lambda *_args: None)
    monkeypatch.setattr(setup_toolchain, "run_verification_sequence", lambda *_args: (Path("mpy-cross"), Path("micropython")))
    _answer_record_probes(setup_toolchain, monkeypatch)


def _setup_args(toolchain_dir: Path, *, latest: bool = False, micropython_ref: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(micropython_ref=micropython_ref, latest=latest, toolchain_dir=toolchain_dir, clean=False, skip_apt=True, jobs=1)


def _pinned_copy(tmp_path: Path, repo_root: Path) -> Path:
    path = tmp_path / "versions.toml"
    path.write_text((repo_root / "toolchain" / "versions.toml").read_text())
    return path


def test_latest_on_the_newest_tag_already_writes_nothing_and_says_nothing(setup_toolchain: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    path = _pinned_copy(tmp_path, repo_root)
    before = path.read_text()
    pinned = setup_toolchain.load_versions(path)["micropython"]["ref"]
    _quiet_setup(setup_toolchain, monkeypatch)
    monkeypatch.setattr(setup_toolchain, "latest_stable_micropython_ref", lambda: pinned)
    setup_toolchain.run_setup(_setup_args(tmp_path / "toolchain", latest=True), path, setup_toolchain.load_versions(path))
    assert path.read_text() == before
    out = capsys.readouterr().out
    assert "already on the newest stable tag" in out
    assert "platform re-check" not in out


def test_latest_on_a_newer_tag_moves_the_pin_and_names_the_re_check(setup_toolchain: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    path = _pinned_copy(tmp_path, repo_root)
    pinned = setup_toolchain.load_versions(path)["micropython"]["ref"]
    _quiet_setup(setup_toolchain, monkeypatch)
    monkeypatch.setattr(setup_toolchain, "latest_stable_micropython_ref", lambda: "v9.9.9")
    assert setup_toolchain.run_setup(_setup_args(tmp_path / "toolchain", latest=True), path, setup_toolchain.load_versions(path)) == 0
    assert setup_toolchain.load_versions(path)["micropython"]["ref"] == "v9.9.9"
    out = capsys.readouterr().out
    assert f"MicroPython v9.9.9 is not the version this tree was verified against ({pinned})" in out
    assert "versions.toml now pins v9.9.9: the pin moves only on the owner's call" in out
    record = setup_toolchain.read_toolchain_record(tmp_path / "toolchain")
    assert record is not None
    assert (record["pinned_ref"], record["built_ref"]) == ("v9.9.9", "v9.9.9")


def test_an_off_pin_build_names_the_re_check_and_leaves_the_pin(setup_toolchain: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    path = _pinned_copy(tmp_path, repo_root)
    before = path.read_text()
    pinned = setup_toolchain.load_versions(path)["micropython"]["ref"]
    _quiet_setup(setup_toolchain, monkeypatch)
    assert setup_toolchain.run_setup(_setup_args(tmp_path / "toolchain", micropython_ref="v1.28.0"), path, setup_toolchain.load_versions(path)) == 0
    assert path.read_text() == before
    out = capsys.readouterr().out
    assert f"MicroPython v1.28.0 is not the version this tree was verified against ({pinned})" in out
    assert "now pins" not in out
    record = setup_toolchain.read_toolchain_record(tmp_path / "toolchain")
    assert record is not None
    assert (record["pinned_ref"], record["built_ref"]) == (pinned, "v1.28.0"), "an off-pin directory stays detectable"


def test_latest_and_an_explicit_ref_are_exclusive(setup_toolchain: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _pinned_copy(tmp_path, repo_root)
    _quiet_setup(setup_toolchain, monkeypatch)
    monkeypatch.setattr(setup_toolchain, "latest_stable_micropython_ref", lambda: pytest.fail("resolved a tag for a refused command line"))
    with pytest.raises(setup_toolchain.SetupError, match="--latest and --micropython-ref are exclusive"):
        setup_toolchain.run_setup(_setup_args(tmp_path / "toolchain", latest=True, micropython_ref="v1.28.0"), path, setup_toolchain.load_versions(path))


# --- Node: one SHASUMS fetch, a checked download, a recorded tree ---------------------------------------

_NODE_TARBALL_BYTES = b"not really a node tarball"
_NODE_SHA = hashlib.sha256(_NODE_TARBALL_BYTES).hexdigest()
_NODE_SUMS = f"{'1' * 64}  node-v22.5.1-linux-arm64.tar.xz\n{_NODE_SHA}  node-v22.5.1-linux-x64.tar.xz\n{'2' * 64}  node-v22.5.1-linux-x64.tar.gz\n"


def _on_x64(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(setup_toolchain.os, "uname", lambda: os.uname_result(("Linux", "host", "6.8", "#1", "x86_64")))


def test_node_release_comes_from_one_shasums_fetch(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    _on_x64(setup_toolchain, monkeypatch)
    fake = _FakeRun({("curl",): _NODE_SUMS})
    monkeypatch.setattr(setup_toolchain, "run", fake)
    assert setup_toolchain._node_release("22", {}) == ("node-v22.5.1-linux-x64.tar.xz", _NODE_SHA)
    assert fake.argvs() == [["curl", "-fsSL", "--max-time", "60", "https://nodejs.org/dist/latest-v22.x/SHASUMS256.txt"]]


@pytest.mark.parametrize(
    ("sums", "message"),
    [
        (f"{'1' * 64}  node-v22.5.1-linux-arm64.tar.xz\n", r"no linux-x64 build listed for Node 22 at https://nodejs\.org/dist/latest-v22\.x/SHASUMS256\.txt"),
        ("notahash  node-v22.5.1-linux-x64.tar.xz\n", r"malformed sha256 .*notahash"),
    ],
)
def test_a_shasums_list_without_a_usable_line_is_named(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, sums: str, message: str) -> None:
    _on_x64(setup_toolchain, monkeypatch)
    monkeypatch.setattr(setup_toolchain, "run", _FakeRun({("curl",): sums}))
    with pytest.raises(setup_toolchain.SetupError, match=message):
        setup_toolchain._node_release("22", {})


def _node_download_fake(tmp_path: Path, payload: bytes) -> _FakeRun:
    # curl: the SHASUMS text, or `payload` written where -o says; tar: the tree it would unpack.
    fake = _FakeRun({("curl",): _NODE_SUMS})

    def downloading(cmd: list[str], cwd: Path | None = None, **kwargs: object) -> str:
        if cmd[0] == "curl" and "-o" in cmd:
            Path(cmd[cmd.index("-o") + 1]).write_bytes(payload)
        if cmd[0] == "tar":
            bindir = Path(cmd[cmd.index("-C") + 1]) / "node-v22.5.1-linux-x64" / "bin"
            bindir.mkdir(parents=True)
            (bindir / "node").write_text("#!/bin/sh\n")
        return fake(cmd, cwd, **kwargs)

    fake.wrapped = downloading  # type: ignore[attr-defined]
    return fake


def _prepare_node_install(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: bytes) -> _FakeRun:
    (tmp_path / ".nvmrc").write_text("22\n")
    _on_x64(setup_toolchain, monkeypatch)
    monkeypatch.setattr(setup_toolchain, "node_on_path_matches", lambda major: False)
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name, path=None: f"/usr/bin/{name}")
    fake = _node_download_fake(tmp_path, payload)
    monkeypatch.setattr(setup_toolchain, "run", fake.wrapped)  # type: ignore[attr-defined]
    return fake


def test_a_node_install_checks_the_download_and_records_the_tree(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _prepare_node_install(setup_toolchain, tmp_path, monkeypatch, _NODE_TARBALL_BYTES)
    bindir = setup_toolchain.ensure_node(tmp_path, tmp_path, skip_apt=True)
    assert bindir == tmp_path / "node" / "node-v22.5.1-linux-x64" / "bin"
    assert sum("SHASUMS256.txt" in " ".join(argv) for argv in fake.argvs()) == 1, "the list the name and hash come from is fetched once"
    record = json.loads((tmp_path / "node" / "node-record.json").read_text())
    assert record == {"major": "22", "tarball": "node-v22.5.1-linux-x64.tar.xz", "sha256": _NODE_SHA}


def test_a_node_download_that_fails_its_checksum_is_never_unpacked(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _prepare_node_install(setup_toolchain, tmp_path, monkeypatch, b"tampered")
    with pytest.raises(setup_toolchain.SetupError, match="checksum mismatch"):
        setup_toolchain.ensure_node(tmp_path, tmp_path, skip_apt=True)
    assert not any(argv[0] == "tar" for argv in fake.argvs())
    assert not (tmp_path / "node" / "node-record.json").exists()


def test_a_node_install_asks_for_curl_before_downloading(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded_run: list[list[str]]) -> None:
    (tmp_path / ".nvmrc").write_text("22\n")
    monkeypatch.setattr(setup_toolchain, "node_on_path_matches", lambda major: False)
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name, path=None: None)
    with pytest.raises(setup_toolchain.SetupError, match="'curl' not on PATH and --skip-apt is set - install curl by hand"):
        setup_toolchain.ensure_node(tmp_path, tmp_path, skip_apt=True)
    assert recorded_run == []


# --- picotool: built only when its tag changed; a USB-less or shadowed one named --------------------------

# picotool 2.3.1's own `version` output (main.cpp's version_command), and the line it adds without libusb.
_PICOTOOL_VERSION_LINE = "picotool v2.3.1 (Linux, GNU-13.3.0, Release)"
_NO_USB = "\nThis version of picotool was compiled without USB support. Some commands are not available.\n"


def _installed_picotool(setup_toolchain: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, version_out: str, *, first_on_path: str | None = None) -> _FakeRun:
    prefix = tmp_path / "usr-local"
    binary = prefix / "bin" / "picotool"
    binary.parent.mkdir(parents=True)
    binary.write_text("")
    (tmp_path / "picotool").mkdir()
    monkeypatch.setattr(setup_toolchain, "PICOTOOL_INSTALL_PREFIX", str(prefix))
    monkeypatch.setattr(setup_toolchain.shutil, "which", lambda name, path=None: first_on_path or str(binary))
    fake = _FakeRun({(str(binary), "version"): version_out})
    monkeypatch.setattr(setup_toolchain, "run", fake)
    return fake


def _build_picotool(setup_toolchain: ModuleType, tmp_path: Path, previous: object, tier: str = "setup") -> str:
    return str(setup_toolchain.build_and_install_picotool(tmp_path / "picotool", tmp_path / "pico-sdk", 1, tag="2.3.1", previous_record=previous, tier=tier))


def test_a_current_picotool_is_not_rebuilt(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # So a re-run of any tier, and scripts/test.sh's automatic setup, need no root for picotool.
    fake = _installed_picotool(setup_toolchain, monkeypatch, tmp_path, _PICOTOOL_VERSION_LINE + "\n")
    assert _build_picotool(setup_toolchain, tmp_path, _a_record()) == _PICOTOOL_VERSION_LINE
    assert not any(argv[0] in ("cmake", "make", "sudo") for argv in fake.argvs())
    assert "picotool 2.3.1 already installed in" in capsys.readouterr().out


@pytest.mark.parametrize("previous", [None, _a_record() | {"picotool_tag": "2.3.0"}])
def test_a_new_picotool_tag_is_built_and_installed(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, previous: object) -> None:
    fake = _installed_picotool(setup_toolchain, monkeypatch, tmp_path, _PICOTOOL_VERSION_LINE + "\n")
    _build_picotool(setup_toolchain, tmp_path, previous)
    assert [argv[0] for argv in fake.argvs()][:3] == ["cmake", "make", "sudo"]
    assert ["sudo", "make", "install"] in fake.argvs()


@pytest.mark.parametrize("tier", ["flash", "bench", "generic", "setup"])
def test_a_usb_less_picotool_is_refused_where_it_must_flash(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tier: str) -> None:
    _installed_picotool(setup_toolchain, monkeypatch, tmp_path, _PICOTOOL_VERSION_LINE + _NO_USB)
    if tier in ("flash", "bench"):  # the tiers that flash a board
        with pytest.raises(setup_toolchain.SetupError, match=r"picotool was built without USB support - install libusb-1\.0-0-dev"):
            _build_picotool(setup_toolchain, tmp_path, _a_record(), tier)
        return
    _build_picotool(setup_toolchain, tmp_path, _a_record(), tier)
    assert "WARNING: picotool was built without USB support" in capsys.readouterr().out


def test_a_picotool_earlier_on_the_path_is_named(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _installed_picotool(setup_toolchain, monkeypatch, tmp_path, _PICOTOOL_VERSION_LINE + "\n", first_on_path="/usr/local/sbin/picotool")
    _build_picotool(setup_toolchain, tmp_path, _a_record())
    out = " ".join(capsys.readouterr().out.split())
    assert "WARNING: /usr/local/sbin/picotool comes before" in out
    assert str(tmp_path / "usr-local" / "bin" / "picotool") in out


def test_setup_hands_picotool_the_previous_record_and_its_tier(setup_toolchain: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Read before setup drops the record, or the "already installed" check could never see it.
    toolchain_dir = tmp_path / "toolchain"
    toolchain_dir.mkdir()
    setup_toolchain.write_toolchain_record(toolchain_dir, _a_record())
    path = _pinned_copy(tmp_path, repo_root)
    _quiet_setup(setup_toolchain, monkeypatch)
    seen: dict[str, object] = {}
    monkeypatch.setattr(setup_toolchain, "build_and_install_picotool", lambda *_args, **kwargs: seen.update(kwargs) or _PICOTOOL_VERSION_LINE)
    setup_toolchain.run_setup(_setup_args(toolchain_dir), path, setup_toolchain.load_versions(path), tier="flash")
    assert seen == {"tag": "2.3.1", "previous_record": _a_record(), "tier": "flash"}


# --- the installer's own outdated leftovers -------------------------------------------------------------


def _leftover_tree(root: Path) -> Path:
    toolchain_dir = root / "toolchain"
    for name in ("build-standard", "build-settrace", "build-lwip", "build-coverage"):
        (toolchain_dir / "micropython" / "ports" / "unix" / name).mkdir(parents=True)
    (toolchain_dir / "micropython" / "ports" / "rp2" / "build-OTHER").mkdir(parents=True)
    for name in ("unix_kbd_intr_variant", "old_override"):
        (toolchain_dir / "build_overrides" / name).mkdir(parents=True)
    for name in ("node-v22.1.0-linux-x64", "node-v22.2.0-linux-x64"):
        (toolchain_dir / "node" / name).mkdir(parents=True)
    return toolchain_dir


def _tree(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def test_setup_removes_only_its_own_outdated_leftovers(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    toolchain_dir = _leftover_tree(tmp_path)
    (toolchain_dir / "node" / "node-record.json").write_text(json.dumps({"major": "22", "tarball": "node-v22.2.0-linux-x64.tar.xz", "sha256": "a" * 64}))
    before = _tree(toolchain_dir)
    setup_toolchain.remove_outdated_leftovers(toolchain_dir)
    gone = sorted(set(before) - set(_tree(toolchain_dir)))
    assert gone == ["build_overrides/old_override", "micropython/ports/unix/build-coverage", "node/node-v22.1.0-linux-x64"]


def test_without_a_node_record_no_node_tree_is_removed(setup_toolchain: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Every npm test on this host may run on the one Node there: unrecorded, none is the installer's to judge.
    toolchain_dir = _leftover_tree(tmp_path)
    setup_toolchain.remove_outdated_leftovers(toolchain_dir)
    assert sorted(p.name for p in (toolchain_dir / "node").iterdir()) == ["node-v22.1.0-linux-x64", "node-v22.2.0-linux-x64"]
    assert "no node/node-record.json" in capsys.readouterr().out


def test_a_leftover_linking_outside_the_toolchain_is_kept(setup_toolchain: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    toolchain_dir = _leftover_tree(tmp_path)
    outside = tmp_path / "someone-elses"
    outside.mkdir()
    (outside / "keep.txt").write_text("x")
    os.symlink(outside, toolchain_dir / "build_overrides" / "linked_override")
    setup_toolchain.remove_outdated_leftovers(toolchain_dir)
    assert (toolchain_dir / "build_overrides" / "linked_override").is_symlink()
    assert (outside / "keep.txt").read_text() == "x"
    assert "resolves outside" in capsys.readouterr().out


def test_the_current_names_are_the_ones_the_builds_write(setup_toolchain: ModuleType, tmp_path: Path) -> None:
    # Read from what each apply_*() writes against the pinned checkout (into tmp_path, the checkout only
    # read), not from the tuples: a renamed override would otherwise make setup delete its own output.
    overrides = setup_toolchain.micropython_overrides
    micropython_dir = _REAL_TOOLCHAIN_DIR / "micropython"
    if not (micropython_dir / "ports" / "rp2").is_dir():
        pytest.fail(f"no MicroPython checkout at {micropython_dir} - run toolchain/setup_toolchain.py setup first")
    out = tmp_path / "build_overrides"
    lwip = setup_toolchain.load_lwip_macros()
    board = setup_toolchain.load_versions(setup_toolchain.VERSIONS_PATH)["toolchain"]["board"]
    overrides.apply_unix_kbd_intr_override(micropython_dir, out)
    overrides.apply_lwip_connection_counts_override(micropython_dir, out, board, lwip)
    overrides.apply_modlwip_eagain_override(micropython_dir, out)
    host = overrides.apply_unix_lwip_host_override(micropython_dir, out, lwip)
    tick = overrides.apply_tick_offset_override(micropython_dir, out, board=board)
    assert sorted(p.name for p in out.iterdir()) == sorted(overrides.CURRENT_OVERRIDE_DIRS)
    assert host["BUILD"] == setup_toolchain.UNIX_LWIP_BUILD_DIR, "the lwIP host build lands where setup and scripts/test.sh look"
    assert tick["BUILD"] == f"build-{board}-tickoffset"


# --- the command line ------------------------------------------------------------------------------------


def test_cli_env_has_no_password_option(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # An explicit PSK comes from $BENCH_AP_PASSWORD, never from a command line another user's ps can read.
    assert _main_refusing_to_run(setup_toolchain, monkeypatch, tmp_path, ["env", "--tier", "bench", "--password", "x"]) == 2
    assert "unrecognized arguments: --password x" in capsys.readouterr().err


def test_cli_help_names_the_pin_rules_and_every_build_flavour(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("COLUMNS", "1000")  # argparse wraps help at the terminal width, hyphenated words included
    assert _main_refusing_to_run(setup_toolchain, monkeypatch, tmp_path, ["setup", "--help"]) == 0
    text = " ".join(capsys.readouterr().out.split())
    assert "a pin move: the owner's call, and the platform re-check follows" in text
    assert "an off-pin build: the platform re-check applies before trusting it" in text
    assert "ports/unix/build-standard, build-settrace, build-lwip" in text


def test_node_is_unpacked_aside_and_renamed_into_place_whole(setup_toolchain: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A run killed mid-unpack must leave no tree that looks installed: a later run would reuse it half-made.
    fake = _prepare_node_install(setup_toolchain, tmp_path, monkeypatch, _NODE_TARBALL_BYTES)
    stale = tmp_path / "node" / "node-v22.5.1-linux-x64"
    (stale / "lib").mkdir(parents=True)  # an earlier run's half-unpacked tree, bin/node never reached
    bindir = setup_toolchain.ensure_node(tmp_path, tmp_path, skip_apt=True)
    tar = next(argv for argv in fake.argvs() if argv[0] == "tar")
    assert Path(tar[tar.index("-C") + 1]) != tmp_path / "node", "unpacked straight into the place a later run trusts"
    assert bindir is not None and (bindir / "node").exists()
    assert not (stale / "lib").exists(), "the half-made tree was kept beside the new one"
    assert sorted(p.name for p in (tmp_path / "node").iterdir()) == ["node-record.json", "node-v22.5.1-linux-x64"]


def test_a_moved_pin_is_announced_even_when_the_build_fails(setup_toolchain: ModuleType, repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    # versions.toml changed the moment --latest wrote it; a failed build must not hide that.
    path = _pinned_copy(tmp_path, repo_root)
    _quiet_setup(setup_toolchain, monkeypatch)
    monkeypatch.setattr(setup_toolchain, "latest_stable_micropython_ref", lambda: "v9.9.9")

    def fails(*_args: object) -> NoReturn:
        raise setup_toolchain.SetupError("firmware build reported an error (see log above)")

    monkeypatch.setattr(setup_toolchain, "run_verification_sequence", fails)
    with pytest.raises(setup_toolchain.SetupError, match="firmware build"):
        setup_toolchain.run_setup(_setup_args(tmp_path / "toolchain", latest=True), path, setup_toolchain.load_versions(path))
    assert "versions.toml now pins v9.9.9: the pin moves only on the owner's call" in capsys.readouterr().out
