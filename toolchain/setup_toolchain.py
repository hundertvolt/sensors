#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Single-command installer/updater for the MicroPython RP2040/Pico W firmware build environment
(MicroPython + matching pico-sdk/picotool + ARM cross-toolchain) plus the host-side Unix port the
tests run on. Invocations: README.md's quick-start; the full picture: SPECIFICATION.md Part B."""

import argparse
import contextlib
import fcntl
import grp
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import IO, NoReturn, TypedDict, cast

import tomllib

# The same explicit sys.path convention scripts/build_firmware.py uses for its toolchain/
# siblings: needed so this resolves both when run directly (which puts its own directory on
# sys.path) and when loaded through tests_scripts/_script_loader.py, which does not.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import micropython_overrides

MICROPYTHON_URL = "https://github.com/micropython/micropython.git"
PICO_SDK_URL = "https://github.com/raspberrypi/pico-sdk.git"
PICOTOOL_URL = "https://github.com/raspberrypi/picotool.git"

# The single module used throughout run_verification_sequence()'s chain - one source of truth,
# rather than separate throwaway samples per step. RESULT lets callers prove the import produced
# an actual value, not just that it didn't crash.
FROZEN_VERIFY_MODULE = "frozen_verify_test"
FROZEN_VERIFY_PY = """\
import sys
import json

assert 2 + 3 == 5
assert "-".join(str(x) for x in range(3)) == "0-1-2"
assert json.dumps({"a": 1}) == '{"a": 1}'

try:
    1 / 0
except ZeroDivisionError:
    pass
else:
    raise SystemExit("expected ZeroDivisionError")

RESULT = "FROZEN_VERIFY_OK: " + sys.implementation.name
"""


class SetupError(RuntimeError):
    pass


# A fixed, deterministic PATH and a small allowlist of ambient variables - never the caller's raw
# environment, so nothing in their shell/profile can silently change what gets built or with what
# (SPECIFICATION.md Part B.4).
BUILD_ENV_ALLOWLIST = ("HOME", "USER", "LOGNAME", "TERM", "TMPDIR")
BUILD_ENV_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# LANG/LC_ALL are forced to C.UTF-8, not passed through: build failure detection greps build
# output for literal English "error:"/"warning:", which a translated gettext locale could evade
# (SPECIFICATION.md Part B.7).
BUILD_ENV_LOCALE = "C.UTF-8"

# On top of the base allowlist, git/apt calls - and the rp2 "submodules" target, which fetches
# and configures - need whatever proxy/CA configuration this machine requires. Named explicitly
# rather than inherited wholesale, so it stays only ever these variables.
NETWORK_ENV_EXTRA = (
    "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy",
    "NO_PROXY", "no_proxy", "ALL_PROXY", "all_proxy",
    "SSL_CERT_FILE", "GIT_SSL_CAINFO", "CURL_CA_BUNDLE", "REQUESTS_CA_BUNDLE",
)


# The three budgets every subprocess runs under (SPECIFICATION.md Part N): a short query or probe, a
# step that downloads from a third party, and a compile or install.
# @tunable tool.remote_query_timeout_s = 120
_REMOTE_QUERY_TIMEOUT_S = 120
# @tunable tool.network_step_timeout_s = 1800
_NETWORK_STEP_TIMEOUT_S = 1800
# @tunable tool.build_step_timeout_s = 3600
_BUILD_STEP_TIMEOUT_S = 3600
_STOP_GRACE_S = 5.0  # a stopped command's time to exit on SIGTERM before SIGKILL


# @tunable tool.uv_sync_attempts = 3
NETWORK_ATTEMPTS = 3  # mirrors the retried uv sync of ci.yml and the toolchain action: a momentary outage is not a failed install


class MicropythonPin(TypedDict):
    ref: str


class ToolchainPin(TypedDict):
    board: str
    apt_packages: list[str]


class Versions(TypedDict):
    micropython: MicropythonPin
    toolchain: ToolchainPin
    lwip: dict[str, int]


VERSIONS_PATH = Path(__file__).parent / "versions.toml"


# @tunable tool.apt_acquire_timeout_s = 30
APT_ACQUIRE_TIMEOUT_S = 30


# One apt download attempt's limit: three of them, their pauses and a bounded list update stay well inside
# a CI job's own limit, and each streams its output, so the last line names a stalled mirror.
# @tunable tool.apt_step_timeout_s = 150
_APT_STEP_TIMEOUT_S = 150
_APT_SUDO_HINT = (
    "if sudo refused --preserve-env, add the proxy variables to env_keep (see the commented example in "
    "/etc/sudoers), or install the packages by hand and pass --skip-apt"
)


# mode, object type, sha - the three fields of a `git ls-tree` line before the tab-separated path.
LS_TREE_FIELDS_BEFORE_PATH = 3


PICOTOOL_INSTALL_PREFIX = "/usr/local"


# The Unix-port build flavours and what each backs. The plain test rig is settrace-FREE: with
# MICROPY_PY_SYS_SETTRACE compiled in, py/vm.c allocates a frame and a code object per call and per
# generator resume, inflating every allocation figure 4-5x (SPECIFICATION.md Part E.5.2).
UNIX_BUILD_DIR = "build-standard"
UNIX_SETTRACE_BUILD_DIR = "build-settrace"
# the lwIP host build: the real patched modlwip over loopback lwIP (SPECIFICATION.md B.14)
UNIX_LWIP_BUILD_DIR = "build-lwip"
CURRENT_UNIX_BUILD_DIRS = (UNIX_BUILD_DIR, UNIX_SETTRACE_BUILD_DIR, UNIX_LWIP_BUILD_DIR)


# The frozen test module lives in its own subdirectory of the tempdir created by
# run_verification_sequence(), never directly alongside the generated manifest.py files - see
# write_freeze_manifest() for why that separation matters.
FROZEN_MODULE_SUBDIR = "frozen_module"


# What a toolchain directory was built from, written last by `setup` and `test`: a directory without
# one is incomplete or was interrupted, which scripts/test.sh and scripts/build_firmware.py act on.
TOOLCHAIN_RECORD = "toolchain-record.json"
TOOLCHAIN_LOCK = ".toolchain.lock"
_TOOLCHAIN_SOURCE_DIR = Path(__file__).resolve().parent


class ToolchainRecord(TypedDict):
    pinned_ref: str
    built_ref: str
    micropython_commit: str
    pico_sdk_commit: str | None
    pico_sdk_describe: str | None
    picotool_tag: str | None
    picotool_version: str | None
    board: str
    lwip: dict[str, int]
    input_sha256: dict[str, str]
    compilers: dict[str, str]
    unix_binaries: list[str]
    recorded_utc: str


NODE_RECORD = "node-record.json"


class NodeRecord(TypedDict):
    major: str
    tarball: str
    sha256: str


# Printed after a build of any ref other than the one this tree was verified against.
_PLATFORM_RECHECK_NOTICE = (
    "\nMicroPython {new} is not the version this tree was verified against ({old}). Before anything built from it "
    'is trusted, run the platform re-check (CLAUDE.md "Platform target"; SPECIFICATION.md Part F\'s checklist): every '
    "Part F fact and upstream file:line citation, each override anchor and its mechanism (SPECIFICATION.md B.14), "
    "the heap-map parser anchor, the stub version (scripts/typecheck.sh), and every ruled-out item again."
)
_PIN_MOVED_NOTICE = "versions.toml now pins {new}: the pin moves only on the owner's call (owner, 2026-09-26) - revert it unless that call was made."


REPO_ROOT = Path(__file__).resolve().parent.parent

# Vendor 2e8a narrows to Raspberry Pi devices, the MicroPython by-id name to a board running
# MicroPython - a debug probe shares the vendor ID.
PICO_USB_VENDOR_ID = "2e8a"
BOARD_BY_ID_GLOB = "usb-MicroPython_Board_in_FS_mode_*-if00"


# Every command a tier runs that a minimal host may lack, with its package: curl fetches Node; the bench
# row is what the bridge set-up and bench_control.py run (`timeout` wraps the tcpdump capture).
_TIER_COMMANDS: dict[str, tuple[tuple[str, str], ...]] = {
    "generic": (("curl", "curl"),),
    "bench": (
        ("nmcli", "network-manager"), ("ip", "iproute2"), ("iptables", "iptables"), ("sysctl", "procps"), ("modprobe", "kmod"),
        ("iw", "iw"), ("tc", "iproute2"), ("tcpdump", "tcpdump"), ("timeout", "coreutils"),
    ),
}


# What the bench tier runs under sudo unattended, each with an argument that only prints a version.
_BENCH_SUDO_COMMANDS = ("nmcli", "iw", "iptables", "tc", "tee", "picotool", "timeout", "systemd-run", "systemctl")
_SUDO_PROBE_ARGUMENT = {"tc": "-V", "picotool": "version"}


# `nmcli -t -f DEVICE,TYPE` prints exactly the two requested colon-separated fields per line.
NMCLI_DEVICE_STATUS_FIELDS = 2


# Connection names match tests_hardware/README.md's manual nmcli recipe exactly, so a bridge/AP
# created by that recipe by hand is recognized as "already configured" here too, and vice versa.
BENCH_BRIDGE_CONN = "br0"
BENCH_ETH_CONN = "br0-eth0"
BENCH_AP_CONN = "br0-wifi-ap"


# The window the recovery timer gives a bridge change, and how long br0 may take to forward afterwards
# (SPECIFICATION.md B.13 measured about 30 s to a DHCP lease).
# @tunable tool.bench_bridge_recovery_arm_s = 300
_BRIDGE_RECOVERY_ARM_S = 300
# @tunable tool.bench_bridge_up_poll_s = 90
_BRIDGE_UP_POLL_S = 90
_BRIDGE_POLL_STEP_S = 2


# curl's own --max-time per Node download; run() allows each the same plus a slack, so curl's own
# message names a stall before the hard stop does.
# @tunable tool.node_shasums_timeout_s = 60
_NODE_SHASUMS_TIMEOUT_S = 60
# @tunable tool.node_tarball_timeout_s = 600
_NODE_TARBALL_TIMEOUT_S = 600
_CURL_SLACK_S = 30
_SHASUMS_LINE_FIELDS = 2  # "<sha256>  <filename>"


@contextlib.contextmanager
def _armed_recovery(uplink_iface: str, restore_profile: str | None, window_s: int) -> Iterator[None]:
    # SPECIFICATION.md B.13's dead-man's switch around a bridge change: verified armed before the change,
    # disarmed once it succeeded, left armed when it fails - then it is the host's own way back.
    unit = f"sensors-bench-recovery-{os.getpid()}"
    env = build_env()
    run(["sudo", "systemd-run", f"--unit={unit}", f"--on-active={window_s}", "/bin/bash", "-c", _recovery_script(restore_profile)], env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    if _timer_state(unit) != "active":
        raise SetupError(f"the bench recovery timer {unit} did not arm - no bridge change was made")
    fires_at = time.strftime("%H:%M:%S", time.localtime(time.time() + window_s))
    restores = f"restores {restore_profile!r} on {uplink_iface}" if restore_profile else f"tears the bridge down (no profile was active on {uplink_iface})"
    try:
        yield
    except BaseException:
        log(f"bridge change failed - the recovery timer {unit} {restores} at {fires_at}; do not disarm it until the host is reachable")
        raise
    run(["sudo", "systemctl", "stop", f"{unit}.timer", f"{unit}.service"], check=False, env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    if _timer_state(unit) == "active":
        raise SetupError(f"the bench recovery timer {unit} is still armed after the change succeeded - stop it: sudo systemctl stop {unit}.timer")


def _build_unix_variant(micropython_dir: Path, jobs: int, *, make_vars: dict[str, str], build_dir_name: str, label: str, frozen_manifest: Path | None = None) -> Path:
    # The build body every Unix-port build flavour shares: a clean build dir, the build and its
    # diagnostics, then the proof that the safe SIGINT path was compiled in (Part B.14.1).
    log(f"Building the MicroPython Unix port ({label})")
    unix_dir = micropython_dir / "ports" / "unix"
    build_dir = unix_dir / build_dir_name
    if build_dir.exists():
        shutil.rmtree(build_dir)
    make_cmd = ["make", f"-j{jobs}", *(f"{key}={value}" for key, value in make_vars.items())]
    if frozen_manifest is not None:
        make_cmd.append(f"FROZEN_MANIFEST={frozen_manifest}")
    out = run(make_cmd, cwd=unix_dir, env=build_env(), timeout_s=_BUILD_STEP_TIMEOUT_S)
    _fail_on_build_diagnostics(out, "Unix port build")

    binary = build_dir / "micropython"
    if not binary.exists():
        raise SetupError(f"Unix port build did not produce {binary}")
    micropython_overrides.verify_unix_kbd_intr_in_build(unix_dir, make_vars, build_dir_name, env=build_env())
    version_out = run([str(binary), "-c", "import sys; print(sys.implementation)"], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    print(f"Built: {version_out.strip()}")
    return binary


def _checked_picotool(binary: Path, version_out: str, tier: str) -> str:
    # picotool's own `version` prints a line when it was built without libusb (picotool main.cpp), and such
    # a picotool cannot flash; the fixed PATH must also find this binary first. Returns the version line.
    if "compiled without USB support" in version_out:
        message = "picotool was built without USB support - install libusb-1.0-0-dev (in versions.toml's apt_packages) and re-run setup; flashing needs it"
        if tier in ("flash", "bench"):
            raise SetupError(message)
        log(f"WARNING: {message}")
    found = shutil.which("picotool", path=BUILD_ENV_PATH)
    if found is not None and Path(found) != binary:
        log(f"WARNING: {found} comes before {binary} on PATH - a bare `picotool` runs that one; remove it")
    return _first_line(version_out)


def _fail_on_build_diagnostics(out: str, what: str) -> None:
    # A tool can print an error and still exit 0; every build here is also warning-free, so either
    # word in the output fails it (the locale is forced to C.UTF-8 for this grep, build_env()).
    if re.search(r"\berror:", out, re.IGNORECASE):
        raise SetupError(f"{what} reported an error (see log above)")
    if re.search(r"\bwarning:", out, re.IGNORECASE):
        raise SetupError(f"{what} produced warnings (see log above) - every build is warning-free; see SPECIFICATION.md B.7")


def _first_line(text: str) -> str:
    return text.strip().splitlines()[0] if text.strip() else ""


def _keeps_terminal(cmd: list[str], *, terminal: bool) -> bool:
    # sudo asks for a password only on the controlling terminal, which a new session lacks: a command
    # run through sudo, or one that calls it itself (terminal=True), stays in the caller's session.
    return terminal or cmd[0] == "sudo"


def _merge_make_vars(*parts: dict[str, str]) -> dict[str, str]:
    # One make line from several overrides' variables: two setting the same one would leave whichever
    # comes last silently winning, so that is refused by name.
    merged: dict[str, str] = {}
    for part in parts:
        for key, value in part.items():
            if key in merged:
                raise SetupError(f"two build overrides both set {key} ({merged[key]!r} and {value!r}) - each make variable has one owner in toolchain/micropython_overrides.py (SPECIFICATION.md B.14)")
            merged[key] = value
    return merged


def _node_release(major: str, env: dict[str, str]) -> tuple[str, str]:
    # This host's release file name and its sha256, from ONE fetch of the pinned major's SHASUMS: the
    # patch version moves, and two fetches could straddle a release, leaving the name without a hash.
    machine = os.uname().machine
    arch = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "x64"}.get(machine)
    if arch is None:
        raise SetupError(f"no official Node build for this architecture ({machine}) - install Node {major} by hand")
    url = f"https://nodejs.org/dist/latest-v{major}.x/SHASUMS256.txt"
    sums = run_retried(["curl", "-fsSL", "--max-time", str(_NODE_SHASUMS_TIMEOUT_S), url], env=env, timeout_s=_NODE_SHASUMS_TIMEOUT_S + _CURL_SLACK_S)
    suffix = f"-linux-{arch}.tar.xz"
    for line in sums.splitlines():
        parts = line.split()
        if len(parts) == _SHASUMS_LINE_FIELDS and parts[1].startswith("node-v") and parts[1].endswith(suffix):
            if not re.fullmatch(r"[0-9a-f]{64}", parts[0]):
                raise SetupError(f"{url} lists {parts[1]} with a malformed sha256 ({line.strip()!r}) - retry later")
            return parts[1], parts[0]
    raise SetupError(f"no linux-{arch} build listed for Node {major} at {url} - install Node {major} by hand or retry later")


def _outdated_leftovers(toolchain_dir: Path) -> list[tuple[Path, str]]:
    # What only this installer's own earlier versions made: Unix build dirs and override dirs it no longer
    # writes, and Node trees other than the recorded one. ports/rp2/build-* is not its to judge.
    unix_dir = toolchain_dir / "micropython" / "ports" / "unix"
    found = [(p, "a Unix build flavour no longer built") for p in sorted(unix_dir.glob("build-*")) if p.name not in CURRENT_UNIX_BUILD_DIRS]
    overrides_dir = toolchain_dir / "build_overrides"
    if overrides_dir.is_dir():
        found += [(p, "an override no longer applied") for p in sorted(overrides_dir.iterdir()) if p.name not in micropython_overrides.CURRENT_OVERRIDE_DIRS]
    node_root = toolchain_dir / "node"
    trees = sorted(node_root.glob("node-v*-linux-*"))
    node_record = _read_node_record(node_root)
    if node_record is None:
        if trees:
            log(f"no node/node-record.json in {toolchain_dir} - Node trees kept until the next Node install records the one in use")
        return found
    current = node_record["tarball"].removesuffix(".tar.xz")
    return found + [(p, f"a Node tree superseded by {current}") for p in trees if p.name != current]


def _picotool_version(binary: Path) -> str:
    return run([str(binary), "version"], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)


def _raise_terminated(signum: int, _frame: object) -> NoReturn:
    raise SystemExit(128 + signum)


def _read_node_record(node_root: Path) -> NodeRecord | None:
    try:
        data = json.loads((node_root / NODE_RECORD).read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or set(data) != NodeRecord.__required_keys__:
        return None
    return cast("NodeRecord", data)


def _read_usb_id_vendor(tty_name: str, sys_tty_dir: Path) -> str | None:
    # Walks up from <sys_tty_dir>/<name>/device (a USB *interface* node) to find the
    # idVendor file on its parent USB *device* node - pure /sys introspection, no lsusb/udevadm
    # binary needed (neither is guaranteed present on a minimal host).
    device_link = sys_tty_dir / tty_name / "device"
    if not device_link.exists():
        return None
    node = device_link.resolve()
    for candidate in (node, *node.parents):
        vendor_file = candidate / "idVendor"
        if vendor_file.exists():
            return vendor_file.read_text().strip()
    return None


def _recovery_script(restore_profile: str | None) -> str:
    # SPECIFICATION.md B.13's idempotent teardown, then the uplink's own profile back up when it had one;
    # built in memory at each arm from the profile read at run time, never a file.
    names = (BENCH_AP_CONN, BENCH_ETH_CONN, BENCH_BRIDGE_CONN)
    steps = [f"nmcli connection down {name} || true" for name in names] + [f"nmcli connection delete {name} || true" for name in names]
    if restore_profile is not None:
        quoted = shlex.quote(restore_profile)
        steps += [f"nmcli connection modify {quoted} autoconnect yes connection.autoconnect-priority 0", f"nmcli connection up {quoted}"]
    return "; ".join(steps)


def _redact(text: str, secrets: tuple[str, ...]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stop(proc: "subprocess.Popen[str]", *, own_session: bool) -> None:
    # SIGTERM, then SIGKILL after the grace: to the command's whole session when it has its own (its
    # stragglers too), else to the command alone - sudo passes a SIGTERM on to the command it runs.
    def send(sig: signal.Signals) -> None:
        with contextlib.suppress(ProcessLookupError):
            if own_session:
                os.killpg(proc.pid, sig)
            else:
                proc.send_signal(sig)

    send(signal.SIGTERM)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=_STOP_GRACE_S)
    if own_session or proc.returncode is None:
        send(signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=_STOP_GRACE_S)


@contextlib.contextmanager
def _stop_commands_on_termination() -> Iterator[None]:
    # SIGTERM and SIGHUP become SystemExit, as SIGINT becomes KeyboardInterrupt, so run() stops a command
    # running in its own session on the way out instead of leaving it to work on without the lock.
    previous = {sig: signal.signal(sig, _raise_terminated) for sig in (signal.SIGTERM, signal.SIGHUP)}
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, signal.SIG_DFL if handler is None else handler)


def _stream_output(stream: IO[str], lines: list[str], secrets: tuple[str, ...]) -> None:
    # The reader thread: each line is kept for the caller and shown at once, so a stalled step is
    # named by the last line it printed rather than by a log that appears only when it ends.
    for line in stream:
        lines.append(line)
        print(_redact(line, secrets), end="", flush=True)


def _sudo_prefix(env: dict[str, str]) -> list[str]:
    # sudo's env_reset drops the proxy and CA variables a privileged download needs; --preserve-env keeps
    # exactly the ones present, so a proxy URL (which can carry credentials) never appears in argv.
    names = [name for name in ("DEBIAN_FRONTEND", *NETWORK_ENV_EXTRA) if name in env]
    return ["sudo", f"--preserve-env={','.join(names)}"] if names else ["sudo"]


def _timer_state(unit: str) -> str:
    return run(["systemctl", "is-active", f"{unit}.timer"], check=False, env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S).strip()


def _toolchain_record(micropython_dir: Path, versions: Versions, versions_path: Path, *, built_ref: str | None) -> ToolchainRecord:
    # The record as a verification left the directory; what only `setup` derives (pico-sdk, picotool)
    # starts as None for the caller to fill. built_ref None means the checkout's own `git describe`.
    def probe(cmd: list[str], cwd: Path | None = None) -> str:
        return _first_line(run(cmd, cwd=cwd, env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S))

    return {
        "pinned_ref": versions["micropython"]["ref"],
        "built_ref": built_ref if built_ref is not None else probe(["git", "describe", "--tags", "--always"], micropython_dir),
        "micropython_commit": probe(["git", "rev-parse", "HEAD"], micropython_dir),
        "pico_sdk_commit": None,
        "pico_sdk_describe": None,
        "picotool_tag": None,
        "picotool_version": None,
        "board": versions["toolchain"]["board"],
        "lwip": dict(versions["lwip"]),
        "input_sha256": {
            "versions.toml": _sha256(versions_path),
            "setup_toolchain.py": _sha256(_TOOLCHAIN_SOURCE_DIR / "setup_toolchain.py"),
            "micropython_overrides.py": _sha256(_TOOLCHAIN_SOURCE_DIR / "micropython_overrides.py"),
        },
        "compilers": {name: probe([name, "--version"]) for name in ("arm-none-eabi-gcc", "gcc")},
        "unix_binaries": list(CURRENT_UNIX_BUILD_DIRS),
        "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _uplink_profile(uplink_iface: str) -> str | None:
    # The NetworkManager profile active on the uplink before anything changes: what the recovery restores.
    out = run(["nmcli", "--escape", "no", "-g", "GENERAL.CONNECTION", "device", "show", uplink_iface], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    return out.strip() or None


def _versions_defect(path: Path, table: str, key: str, value: object, kind: str) -> SetupError:
    problem = "is missing" if value is None else f"must be {kind}"
    return SetupError(f"{path}: [{table}] {key} {problem} - see SPECIFICATION.md B.3")


def _versions_table(data: dict[str, object], path: Path, name: str) -> dict[str, object]:
    table = data.get(name)
    if not isinstance(table, dict):
        problem = "is missing" if table is None else "must be a table"
        raise SetupError(f"{path}: [{name}] {problem} - see SPECIFICATION.md B.3")
    return table


def _wait_for_bridge_route() -> None:
    # `nmcli connection up` succeeding is not forwarding yet (B.13 step 4), so the change is done only
    # once br0 holds an address and carries the default route; polled, never a fixed sleep.
    deadline = time.monotonic() + _BRIDGE_UP_POLL_S
    while True:
        address = run(["ip", "-o", "-4", "addr", "show", BENCH_BRIDGE_CONN], check=False, env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
        route = run(["ip", "-o", "route", "get", "1.1.1.1"], check=False, env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
        if re.search(r"\binet\s", address) and re.search(rf"\bdev {BENCH_BRIDGE_CONN}\b", route):
            return
        if time.monotonic() >= deadline:
            raise SetupError(f"{BENCH_BRIDGE_CONN} got no address/default route within {_BRIDGE_UP_POLL_S} s")
        time.sleep(_BRIDGE_POLL_STEP_S)


def _write_json(path: Path, data: object) -> None:
    # Through a temporary file and a rename, so a run killed mid-write leaves no half file; the
    # toolchain lock makes the one temporary name safe.
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def get_interface_mac(iface: str) -> str:
    # The real, permanent hardware MAC of an interface, straight from the kernel - never a
    # NetworkManager-synthesized or bridge-inherited one. Why pinning `bridge.mac-address` to it
    # matters: ensure_bench_bridge()'s own note, and CLAUDE.md's "Hard rules".
    out = run(["ip", "-o", "link", "show", iface], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    match = re.search(r"link/ether\s+(\S+)", out)
    if not match:
        raise SetupError(f"could not determine the hardware MAC address of interface {iface!r}")
    return match.group(1)


def is_sha(ref: str) -> bool:
    # True for a raw commit hash rather than a tag/branch name. The two need different checkout
    # handling: `git fetch --tags` always reaches a tag, but an arbitrary commit may not be reachable
    # that way and has to be fetched by its hash.
    return bool(re.fullmatch(r"[0-9a-f]{7,40}", ref))


def apt_options() -> list[str]:
    # A stalled mirror otherwise holds apt, and a CI job, until its own time limit: each fetch gives up after the
    # timeout and is retried, the attempt count the one every retried network step shares.
    timeout = str(APT_ACQUIRE_TIMEOUT_S)
    return ["-o", f"Acquire::Retries={NETWORK_ATTEMPTS - 1}", "-o", f"Acquire::http::Timeout={timeout}", "-o", f"Acquire::https::Timeout={timeout}"]


def bench_ap_exists() -> bool:
    out = run(["nmcli", "-t", "-f", "NAME", "connection", "show"], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    return BENCH_AP_CONN in out.splitlines()


def build_and_install_picotool(picotool_dir: Path, pico_sdk_dir: Path, jobs: int, *, tag: str, previous_record: "ToolchainRecord | None", tier: str) -> str:
    # Builds and installs picotool, unless the last recorded setup installed this very tag and the binary
    # there still reports it: then no cmake and no sudo. Returns the installed picotool's version line.
    picotool_binary = Path(PICOTOOL_INSTALL_PREFIX) / "bin" / "picotool"
    if previous_record is not None and previous_record["picotool_tag"] == tag and picotool_binary.exists():
        version_out = _picotool_version(picotool_binary)
        if re.match(rf"picotool v{re.escape(tag)}\b", version_out):
            log(f"picotool {tag} already installed in {PICOTOOL_INSTALL_PREFIX} - not rebuilt")
            return _checked_picotool(picotool_binary, version_out, tier)
    log(f"Building and installing picotool (against pico-sdk at {pico_sdk_dir})")
    build_dir = picotool_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    env = build_env()
    # Pinned explicitly (not left to whatever cmake's own default resolves to) so the
    # install location is deterministic regardless of ambient cmake config/env state.
    run(
        ["cmake", "..", f"-DPICO_SDK_PATH={pico_sdk_dir}", f"-DCMAKE_INSTALL_PREFIX={PICOTOOL_INSTALL_PREFIX}"],
        cwd=build_dir,
        env=env,
        timeout_s=_BUILD_STEP_TIMEOUT_S,
    )
    run(["make", f"-j{jobs}"], cwd=build_dir, env=env, timeout_s=_BUILD_STEP_TIMEOUT_S)
    run(["sudo", "make", "install"], cwd=build_dir, env=env, timeout_s=_BUILD_STEP_TIMEOUT_S)
    if not picotool_binary.exists():
        raise SetupError(f"picotool install did not produce {picotool_binary}")
    # Invoked by absolute path, not a bare "picotool" PATH lookup — a stray picotool
    # installed elsewhere on PATH (a different version, an unrelated package) must not
    # be able to shadow the one just built for this pico-sdk.
    version = _checked_picotool(picotool_binary, _picotool_version(picotool_binary), tier)
    print(f"Installed: {version}")
    return version


def build_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in BUILD_ENV_ALLOWLIST}
    env["PATH"] = BUILD_ENV_PATH
    env["LANG"] = BUILD_ENV_LOCALE
    env["LC_ALL"] = BUILD_ENV_LOCALE
    return env


def build_firmware(micropython_dir: Path, board: str, jobs: int, frozen_manifest: Path | None = None, *, toolchain_dir: Path | None = None, lwip_macros: dict[str, int] | None = None, tick_offset_test: bool = False) -> Path:
    # Builds the RP2 firmware, optionally with an extra FROZEN_MANIFEST=. Always applies and then proves
    # the lwIP-options and modlwip_eagain overrides (SPECIFICATION.md B.14); lwip_macros defaults to
    # versions.toml's [lwip], toolchain_dir to micropython_dir's parent.
    rp2_dir = micropython_dir / "ports" / "rp2"
    if lwip_macros is None:
        lwip_macros = load_lwip_macros()
    overrides_dir = (toolchain_dir if toolchain_dir is not None else micropython_dir.parent) / "build_overrides"
    # The tick-offset TEST image puts its patched header ahead of the port's and builds in its own
    # directory, so no release build ever reuses one of its objects; every build proves which it is.
    tick_vars: dict[str, str] = {}
    extra_include_dirs: tuple[Path, ...] = ()
    if tick_offset_test:
        tick_vars = micropython_overrides.apply_tick_offset_override(micropython_dir, overrides_dir, board=board)
        extra_include_dirs = (overrides_dir / micropython_overrides.TICK_OFFSET_DIR_NAME,)
    make_vars = _merge_make_vars(
        micropython_overrides.apply_lwip_connection_counts_override(micropython_dir, overrides_dir, board, lwip_macros, extra_include_dirs=extra_include_dirs),
        micropython_overrides.apply_modlwip_eagain_override(micropython_dir, overrides_dir),
        tick_vars,
    )
    build_dir = rp2_dir / make_vars.get("BUILD", f"build-{board}")
    if tick_offset_test and build_dir.name == f"build-{board}":
        raise SetupError(f"the tick-offset test image would build in {build_dir}, the release build's own directory - its override must name another BUILD (SPECIFICATION.md B.14)")
    label = f"frozen manifest {frozen_manifest}" if frozen_manifest else "board manifest, pinned lwIP options"
    log(f"Building firmware for BOARD={board} ({label}{', TICK-OFFSET TEST IMAGE' if tick_offset_test else ''})")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    make_cmd = ["make", f"-j{jobs}", *(f"{key}={value}" for key, value in make_vars.items())]
    if frozen_manifest is not None:
        make_cmd.append(f"FROZEN_MANIFEST={frozen_manifest}")
    out = run(make_cmd, cwd=rp2_dir, env=build_env(), timeout_s=_BUILD_STEP_TIMEOUT_S)
    _fail_on_build_diagnostics(out, "firmware build")

    uf2 = build_dir / "firmware.uf2"
    if not uf2.exists():
        raise SetupError(f"firmware build did not produce {uf2}")
    # After the build, not before: a generated file that was written but never compiled in would
    # otherwise ship a firmware that silently differs from what was asked for.
    micropython_overrides.verify_lwip_macros_in_build(build_dir, lwip_macros)
    micropython_overrides.verify_modlwip_eagain_in_build(build_dir, micropython_dir, Path(make_vars["USER_C_MODULES"]) / micropython_overrides.MODLWIP_COPY_NAME)
    micropython_overrides.verify_tick_offset_in_build(build_dir, expected=tick_offset_test)
    return uf2


def build_mpy_cross(micropython_dir: Path, jobs: int) -> Path:
    log("Building mpy-cross")
    mpy_cross_dir = micropython_dir / "mpy-cross"
    env = build_env()
    out = run(["make", f"-j{jobs}"], cwd=mpy_cross_dir, env=env, timeout_s=_BUILD_STEP_TIMEOUT_S)
    _fail_on_build_diagnostics(out, "mpy-cross build")
    binary = mpy_cross_dir / "build" / "mpy-cross"
    if not binary.exists():
        raise SetupError("mpy-cross build did not produce build/mpy-cross")
    version_out = run([str(binary), "--version"], env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    print(f"Built: {version_out.strip()}")
    return binary


def build_unix_lwip_port(micropython_dir: Path, toolchain_dir: Path, jobs: int) -> Path:
    # The lwIP host build flavour: the patched modlwip.c the firmware runs, over loopback lwIP, proven
    # after the build to be that copy and the socket module (SPECIFICATION.md B.14).
    make_vars = micropython_overrides.apply_unix_lwip_host_override(micropython_dir, toolchain_dir / "build_overrides", load_lwip_macros())
    binary = _build_unix_variant(micropython_dir, jobs, make_vars=make_vars, build_dir_name=UNIX_LWIP_BUILD_DIR, label="the lwIP host build, the patched modlwip over loopback lwIP")
    micropython_overrides.verify_unix_lwip_host_in_build(binary.parent, micropython_dir, binary, env=build_env())
    return binary


def build_unix_port(micropython_dir: Path, toolchain_dir: Path, jobs: int, frozen_manifest: Path | None = None, *, settrace: bool = False) -> Path:
    # Builds one Unix-port build flavour; needs mpy-cross, takes frozen_manifest like build_firmware().
    # settrace=False is the test rig, True is --coverage's own binary. Always applies
    # apply_unix_kbd_intr_override() for the safe SIGINT path (Part B.14.1).
    flavour = "settrace, for --coverage" if settrace else "settrace-free, the test rig"
    make_vars = micropython_overrides.apply_unix_kbd_intr_override(micropython_dir, toolchain_dir / "build_overrides")
    # BUILD= only for a non-default build flavour: the Makefile's own `BUILD ?= build-$(VARIANT)`
    # already lands the settrace-free rig in build-standard, which every other script resolves.
    if settrace:
        make_vars = _merge_make_vars(make_vars, {"CFLAGS_EXTRA": "-DMICROPY_PY_SYS_SETTRACE=1", "BUILD": UNIX_SETTRACE_BUILD_DIR})
    return _build_unix_variant(
        micropython_dir, jobs, make_vars=make_vars, build_dir_name=UNIX_SETTRACE_BUILD_DIR if settrace else UNIX_BUILD_DIR,
        label=f"{flavour}, with the frozen verification module" if frozen_manifest else flavour, frozen_manifest=frozen_manifest,
    )


def check_passwordless_sudo(commands: tuple[str, ...]) -> None:
    # The installer writes no sudoers file: it checks and names what is missing (agent, 2026-09-30;
    # owner-reviewed, 2026-10-02). `sudo -k -n` fails at once where a password would be asked, a cached one
    # ignored (it would expire before the unattended run); a rule for other arguments fails it too. Root passes.
    if os.geteuid() == 0:
        return
    refused = []
    for name in commands:
        path = shutil.which(name, path=BUILD_ENV_PATH)
        try:
            if path is None:
                raise SetupError(f"{name} not found")
            run(["sudo", "-k", "-n", path, _SUDO_PROBE_ARGUMENT.get(name, "--version")], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
        except SetupError:
            refused.append(name)
    if refused:
        raise SetupError(
            f"passwordless sudo missing or restricted to other arguments for: {', '.join(refused)} - the bench tier runs them "
            "unattended; see tests_hardware/README.md Prerequisites for the sudoers line",
        )


def checkout_ref(repo: Path, ref: str) -> None:
    env = network_env()
    run_retried(["git", "fetch", "--quiet", "--tags", "--force", "origin"], cwd=repo, env=env, timeout_s=_NETWORK_STEP_TIMEOUT_S)
    if is_sha(ref):
        try:
            run(["git", "checkout", "--quiet", ref], cwd=repo, env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
        except SetupError:
            # The commit wasn't already present locally (e.g. a pico-sdk pin from a
            # MicroPython ref we haven't built before) — fetch it directly by hash.
            pass
        else:
            return
        run_retried(["git", "fetch", "--quiet", "origin", ref], cwd=repo, env=env, timeout_s=_NETWORK_STEP_TIMEOUT_S)
        run(["git", "checkout", "--quiet", "FETCH_HEAD"], cwd=repo, env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    else:
        run(["git", "checkout", "--quiet", ref], cwd=repo, env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)


def clean_build_dirs(toolchain_dir: Path, board: str) -> None:
    # Wipes every build-artifact directory but no git clone, so the setup that follows rebuilds
    # from scratch without re-cloning multi-gigabyte trees. The firmware/Unix-port/picotool steps
    # already clear their own; this extends that to mpy-cross's build/, which nothing else clears.
    log("Cleaning all build-artifact directories")
    unix_dir = toolchain_dir / "micropython" / "ports" / "unix"
    targets = [
        toolchain_dir / "picotool" / "build",
        toolchain_dir / "micropython" / "mpy-cross" / "build",
        toolchain_dir / "micropython" / "ports" / "rp2" / f"build-{board}",
        *(unix_dir / name for name in CURRENT_UNIX_BUILD_DIRS),
    ]
    for target in targets:
        if target.exists():
            print(f"Removing {target}")
            shutil.rmtree(target)
        else:
            print(f"(nothing to clean at {target})")


def clean_frozen_verification_build_dirs(toolchain_dir: Path, board: str) -> None:
    # Step 7: removes the two outputs the frozen-bytecode verification chain (steps 4-6) leaves -
    # the Unix port and RP2 firmware carrying the frozen test module, neither of which is kept. Leaves
    # mpy-cross/build and picotool alone: those are real deliverables, not verification artifacts.
    log("Cleaning up the frozen-bytecode verification build artifacts")
    targets = [
        toolchain_dir / "micropython" / "ports" / "rp2" / f"build-{board}",
        # UNIX_BUILD_DIR only: the verification chain builds the default build flavour, never the others,
        # so removing those here would delete a real deliverable instead of an artifact.
        toolchain_dir / "micropython" / "ports" / "unix" / UNIX_BUILD_DIR,
    ]
    for target in targets:
        if target.exists():
            print(f"Removing {target}")
            shutil.rmtree(target)
        else:
            print(f"(nothing to clean at {target})")


def clone_full(url: str, dest: Path) -> None:
    # Deliberately a full clone, not `--depth 1`: a shallow clone only has one ref's history,
    # which breaks the *update* path (fetch + checkout some other arbitrary ref later) — and
    # updating in place, not just installing once, is a first-class requirement here.
    if dest.exists():
        raise SetupError(f"{dest} already exists - a new clone is made only where nothing is (ensure_repo_at_ref() updates an existing one)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # A failed attempt's partial clone is this call's own, so it goes before the retry; after the last
    # attempt it stays, and the next run names it (ensure_repo_at_ref()).
    run_retried(
        ["git", "clone", "--quiet", url, str(dest)], env=network_env(), timeout_s=_NETWORK_STEP_TIMEOUT_S,
        before_retry=lambda: shutil.rmtree(dest, ignore_errors=True),
    )


def cross_compile_frozen_verify_test(mpy_cross_binary: Path, test_file: Path) -> Path:
    # Step 3: cross-compiles the test file standalone (invoking mpy-cross directly, not via a
    # manifest's freeze()) to prove mpy-cross itself works, independently of the freeze/build
    # pipeline exercised by steps 4 and 6.
    log("Cross-compiling the verification test file to prove mpy-cross works standalone")
    run([str(mpy_cross_binary), str(test_file)], env=build_env(), timeout_s=_BUILD_STEP_TIMEOUT_S)
    compiled = test_file.with_suffix(".mpy")
    if not compiled.exists() or compiled.stat().st_size == 0:
        raise SetupError(f"mpy-cross did not produce a non-empty {compiled.name}")
    print(f"Produced {compiled.name} ({compiled.stat().st_size} bytes)")
    return compiled


def delete_toolchain_record(toolchain_dir: Path) -> None:
    (toolchain_dir / TOOLCHAIN_RECORD).unlink(missing_ok=True)


def derive_pico_sdk_commit(micropython_dir: Path, mpy_ref: str) -> str:
    # Never chosen independently - read straight out of MicroPython's own submodule pin at
    # lib/pico-sdk, which is the commit the firmware actually compiles against. This is what makes
    # "only pin MicroPython" (versions.toml) possible instead of two hand-tracked versions.
    out = run(["git", "ls-tree", mpy_ref, "lib/pico-sdk"], cwd=micropython_dir, env=network_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    # git ls-tree prints one line shaped "160000 commit <sha>\tlib/pico-sdk"
    fields = out.split()
    if len(fields) < LS_TREE_FIELDS_BEFORE_PATH:
        raise SetupError(f"could not find lib/pico-sdk submodule pin for {mpy_ref}")
    return fields[2]


def derive_picotool_ref(pico_sdk_dir: Path, pico_sdk_commit: str) -> tuple[str, str]:
    # pico-sdk accepts a picotool of its own major version and at least its picotool_VERSION_REQUIRED (pico-sdk
    # tools/CMakeLists.txt; picotool's SameMajorVersion config file); an older same-major or another major fails the build. The
    # newest tag sharing pico-sdk's major.minor is this installer's own narrower choice (agent, 2026-09-22), always inside that range.
    described = run(["git", "describe", "--tags", pico_sdk_commit], cwd=pico_sdk_dir, env=network_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S).strip()
    match = re.match(r"^(\d+)\.(\d+)\.", described)
    if not match:
        raise SetupError(f"could not parse major.minor from pico-sdk tag {described!r}")
    major, minor = match.group(1), match.group(2)

    out = run_retried(["git", "ls-remote", "--tags", PICOTOOL_URL], env=network_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    candidates = []
    for line in out.splitlines():
        m = re.search(rf"refs/tags/({major}\.{minor}\.\d+)$", line)
        if m:
            candidates.append(m.group(1))
    if not candidates:
        raise SetupError(f"no picotool tag found matching pico-sdk major.minor {major}.{minor}")
    candidates.sort(key=lambda v: tuple(int(x) for x in v.split(".")))
    return candidates[-1], described


def detect_free_wifi_interface(exclude: str) -> str:
    # A WiFi adapter not already acting as the uplink - requires exactly one candidate for the
    # same reason resolve_pico_device() does: an ambiguous pick is a hard error, not a guess.
    out = run(["nmcli", "-t", "-f", "DEVICE,TYPE", "device", "status"], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    candidates = []
    for line in out.strip().splitlines():
        fields = line.split(":")
        if len(fields) != NMCLI_DEVICE_STATUS_FIELDS:
            continue
        device, dtype = fields
        if dtype == "wifi" and device != exclude:
            candidates.append(device)
    if not candidates:
        raise SetupError(f"no free WiFi adapter found (excluding uplink interface {exclude!r}) - pass --wifi-iface explicitly")
    if len(candidates) > 1:
        raise SetupError(f"multiple candidate WiFi adapters found ({', '.join(candidates)}) - pass --wifi-iface to pick one explicitly")
    return candidates[0]


def detect_pico_serial_devices(sys_tty_dir: Path = Path("/sys/class/tty"), dev_dir: Path = Path("/dev")) -> list[Path]:
    # Every <dev_dir>/ttyACM*/ttyUSB* whose USB idVendor (read under sys_tty_dir) matches
    # PICO_USB_VENDOR_ID. Order is sorted-by-name for determinism, not connection order.
    # sys_tty_dir/dev_dir default to the real /sys and /dev but are overridable for tests.
    if not sys_tty_dir.is_dir():
        return []
    found = []
    for entry in sorted(sys_tty_dir.iterdir(), key=lambda p: p.name):
        if not (entry.name.startswith("ttyACM") or entry.name.startswith("ttyUSB")):
            continue
        if _read_usb_id_vendor(entry.name, sys_tty_dir) == PICO_USB_VENDOR_ID:
            dev_path = dev_dir / entry.name
            if dev_path.exists():
                found.append(dev_path)
    return found


def detect_uplink_interface() -> str:
    # The network interface currently carrying the default route - i.e. "has internet" -
    # parsed from `ip route get`, which reports the real interface the kernel would actually
    # route a packet through rather than just reading static config.
    out = run(["ip", "-o", "route", "get", "1.1.1.1"], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    match = re.search(r"\bdev\s+(\S+)", out)
    if not match:
        raise SetupError("could not determine the default-route (uplink) network interface - pass --uplink-iface explicitly")
    return match.group(1)


def ensure_apt_packages(packages: list[str], *, skip: bool) -> None:
    if skip:
        log("Skipping apt package install (--skip-apt)")
        return
    log("Installing/checking system packages")
    env = {**network_env(), "DEBIAN_FRONTEND": "noninteractive"}
    apt_get = [*_sudo_prefix(env), "apt-get", *apt_options()]
    # Non-fatal: unrelated third-party sources some environments have configured (PPAs etc.)
    # may be blocked or broken without affecting the main archive packages we actually need.
    try:
        run([*apt_get, "update"], check=False, env=env, timeout_s=_APT_STEP_TIMEOUT_S)
    except SetupError as exc:
        log(f"apt-get update did not finish ({exc}) - going on with the package lists already on this host")
    # Only the download is retried: it never reaches dpkg, so no retry can kill dpkg mid-configure (that
    # leaves the package database interrupted until `dpkg --configure -a`). The install then reads the cache.
    install = ["install", "-y", "--no-install-recommends", *packages]
    try:
        run_retried([*apt_get, "install", "--download-only", *install[1:]], env=env, timeout_s=_APT_STEP_TIMEOUT_S)
        run([*apt_get, *install], env=env, timeout_s=_BUILD_STEP_TIMEOUT_S)
    except SetupError as exc:
        raise SetupError(f"{exc} - {_APT_SUDO_HINT}") from exc


def ensure_bench_bridge(uplink_iface: str | None, wifi_iface: str | None, ssid: str | None, password: str | None) -> str:
    # Idempotent: an existing br0-wifi-ap is reported, never recreated, but br_netfilter and the
    # fixed 2.4GHz channel are re-enforced regardless since it could be missing either. A bridge MAC
    # mismatch is flagged, never auto-repaired (SPECIFICATION.md Part B.13).
    ensure_br_netfilter()

    if bench_ap_exists():
        current_ssid = existing_bench_ap_ssid()
        log(f"Bench WiFi bridge already configured ({BENCH_AP_CONN!r}, SSID {current_ssid!r}) - reusing, not recreating")
        eth_iface = run(["nmcli", "-g", "connection.interface-name", "connection", "show", BENCH_ETH_CONN], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S).strip()
        # Self-heal a bridge created before the channel-pinning fix above (e.g. auto-selected
        # channel 13) - a genuinely idempotent re-run must actually converge on the fixed
        # configuration, not just skip past it because a bridge of some kind already exists.
        current_channel = run(["nmcli", "-g", "802-11-wireless.channel", "connection", "show", BENCH_AP_CONN], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S).strip()
        if current_channel != "6":
            log(f"Bench AP channel is {current_channel!r}, not the fixed 6 - repairing under an armed recovery timer")
            with _armed_recovery(eth_iface, None, _BRIDGE_RECOVERY_ARM_S):
                run(["sudo", "nmcli", "connection", "modify", BENCH_AP_CONN, "802-11-wireless.channel", "6"], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
                run(["sudo", "nmcli", "connection", "up", BENCH_AP_CONN], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
                _wait_for_bridge_route()
        # A synthesized (unpinned) bridge MAC can drift, silently orphaning the router's static
        # DHCP reservation (SPECIFICATION.md Part B.13). Flag-only: repairing a live bridge's MAC
        # risks cycling the interface this SSH session depends on, so it needs a human decision.
        try:
            real_mac = get_interface_mac(eth_iface)
        except SetupError:
            real_mac = ""
        # `--escape no` is load-bearing: `nmcli -g` escapes every ':' as '\:', so a MAC never
        # compares equal to the plain one `ip -o link show` gives. Without it this warns on a
        # correctly-pinned bridge, and the remedy it prints cycles a live one (Part B.13).
        bridge_mac = run(["nmcli", "--escape", "no", "-g", "bridge.mac-address", "connection", "show", BENCH_BRIDGE_CONN], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S).strip()
        if real_mac and bridge_mac.lower() != real_mac.lower():
            log(
                f"WARNING: bridge {BENCH_BRIDGE_CONN!r}'s MAC ({bridge_mac or 'unset/synthesized'}) does not "
                f"match {eth_iface!r}'s real hardware MAC ({real_mac}) - a router DHCP reservation keyed to "
                f"the old MAC will drift on the next lease renewal. Not auto-repairing; fix by hand when "
                f"convenient, ideally at a moment SSH access loss is acceptable: arm SPECIFICATION.md B.13's "
                f"recovery timer first, then sudo nmcli connection modify {BENCH_BRIDGE_CONN} bridge.mac-address "
                f"{real_mac} && sudo nmcli connection up {BENCH_ETH_CONN}",
            )
        return current_ssid

    # $BENCH_AP_PASSWORD (run_env()) or a generated one: a throwaway password used once, passed plainly on
    # the one `nmcli connection modify` that sets it (owner, 2026-10-02); secrets= keeps it out of the
    # echoed command, and only a generated one is printed, once.
    generated_ssid, generated_password = generate_bench_ap_credentials()
    ssid = ssid or generated_ssid
    show_password = password is None
    password = password or generated_password
    # Interface auto-detection only runs here, when actually creating a bridge - callers that
    # already confirmed a bridge exists (the branch above) never reach this, so a second WiFi
    # adapter added to the host later can't make detection ambiguous for a no-op re-run.
    if uplink_iface is None:
        uplink_iface = detect_uplink_interface()
    if wifi_iface is None:
        wifi_iface = detect_free_wifi_interface(exclude=uplink_iface)

    log(f"Creating bench WiFi bridge: {uplink_iface} (uplink) + {wifi_iface} (hosted AP, SSID {ssid!r})")
    env = build_env()
    restore_profile = _uplink_profile(uplink_iface)
    with _armed_recovery(uplink_iface, restore_profile, _BRIDGE_RECOVERY_ARM_S):
        run(["sudo", "nmcli", "connection", "add", "type", "bridge", "ifname", BENCH_BRIDGE_CONN, "con-name", BENCH_BRIDGE_CONN], env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
        # Pinned to the uplink's real hardware MAC before the bridge ever comes up, never a synthesized
        # one: a synthesized MAC can drift across the bridge's lifetime and silently orphan the router's
        # static DHCP reservation (2026-09-04 bench Pi4 lockout incident, CLAUDE.md's "Hard rules").
        uplink_mac = get_interface_mac(uplink_iface)
        run(["sudo", "nmcli", "connection", "modify", BENCH_BRIDGE_CONN, "bridge.mac-address", uplink_mac], env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
        run(
            ["sudo", "nmcli", "connection", "add", "type", "ethernet", "ifname", uplink_iface,
             "master", BENCH_BRIDGE_CONN, "con-name", BENCH_ETH_CONN, "slave-type", "bridge"],
            env=env,
            timeout_s=_REMOTE_QUERY_TIMEOUT_S,
        )
        # Real finding: left on auto, NetworkManager picked channel 13, which the Pico W's cyw43439 did
        # not associate with reliably - repeated "WLAN access point not found" failures, clean STA
        # connects immediately on channel 6. 12-13 are EU-only and not supported by every firmware.
        run(
            ["sudo", "nmcli", "connection", "add", "type", "wifi", "ifname", wifi_iface, "con-name", BENCH_AP_CONN,
             "ssid", ssid, "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg", "802-11-wireless.channel", "6",
             "master", BENCH_BRIDGE_CONN, "slave-type", "bridge"],
            env=env,
            timeout_s=_REMOTE_QUERY_TIMEOUT_S,
        )
        run(
            ["sudo", "nmcli", "connection", "modify", BENCH_AP_CONN,
             "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password,
             "wifi-sec.proto", "rsn", "wifi-sec.pairwise", "ccmp", "wifi-sec.group", "ccmp",
             "wifi-sec.pmf", "disable"],
            env=env,
            timeout_s=_REMOTE_QUERY_TIMEOUT_S,
            secrets=(password,),
        )
        run(["sudo", "nmcli", "connection", "up", BENCH_ETH_CONN], env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
        run(["sudo", "nmcli", "connection", "up", BENCH_AP_CONN], env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
        _wait_for_bridge_route()
    if show_password:
        print(f"Bench AP created - SSID: {ssid}  password: {password}")
        print("Save this password now: a later idempotent run will report the SSID again, but never re-prints the password.")
    else:
        print(f"Bench AP created - SSID: {ssid} (password from $BENCH_AP_PASSWORD)")
    return ssid


def ensure_br_netfilter() -> None:
    # Idempotent: loads br_netfilter and sets net.bridge.bridge-nf-call-iptables=1 - without it bridged
    # traffic bypasses iptables and bench_control.py's fault injection silently does nothing. Host-kernel
    # state, so it runs whether or not the bridge profile exists.
    env = build_env()
    run(["sudo", "modprobe", "br_netfilter"], env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    run(["sudo", "sysctl", "-w", "net.bridge.bridge-nf-call-iptables=1"], env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    persisted = {
        Path("/etc/modules-load.d/sensors-bench-br-netfilter.conf"): "br_netfilter\n",
        Path("/etc/sysctl.d/99-sensors-bench-br-netfilter.conf"): "net.bridge.bridge-nf-call-iptables=1\n",
    }
    for path, line in persisted.items():
        # Straight from stdin, so no temporary file exists to be left behind; tee echoes the line back.
        run(["sudo", "tee", str(path)], stdin_text=line, env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
        run(["sudo", "chmod", "644", str(path)], env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    log(f"br_netfilter loaded and net.bridge.bridge-nf-call-iptables=1 set, persisted via {', '.join(map(str, persisted))}")


def ensure_commands(pairs: tuple[tuple[str, str], ...], *, skip_apt: bool) -> None:
    # Looked up on the PATH every step runs with; the missing ones' packages are installed together.
    def missing() -> list[tuple[str, str]]:
        return [(cmd, pkg) for cmd, pkg in pairs if shutil.which(cmd, path=BUILD_ENV_PATH) is None]

    absent = missing()
    if not absent:
        return
    names = ", ".join(f"'{cmd}'" for cmd, _ in absent)
    packages = list(dict.fromkeys(pkg for _, pkg in absent))
    if skip_apt:
        raise SetupError(f"{names} not on PATH and --skip-apt is set - install {', '.join(packages)} by hand")
    log(f"{names} not on PATH - installing {', '.join(packages)}")
    ensure_apt_packages(packages, skip=False)
    still = missing()
    if still:
        raise SetupError(f"{', '.join(f'{cmd!r}' for cmd, _ in still)} still not on PATH after installing {', '.join(dict.fromkeys(pkg for _, pkg in still))}")


def ensure_dialout_group(*, skip: bool) -> None:
    # Non-root USB serial access needs group membership, not a one-off chmod - see README.md's
    # "Real hardware access" section. Idempotent: does nothing if already a member.
    if skip:
        log("Skipping dialout group check (--skip-apt)")
        return
    user = os.environ.get("USER") or os.environ.get("LOGNAME")
    if not user:
        raise SetupError("cannot determine the current user (USER/LOGNAME unset) to check dialout group membership")
    try:
        dialout_members = grp.getgrnam("dialout").gr_mem
    except KeyError:
        raise SetupError("no 'dialout' group exists on this system - is this a supported Linux host?") from None
    if user in dialout_members:
        log(f"{user} is already in the dialout group")
        return
    log(f"Adding {user} to the dialout group (needed for non-root USB serial access)")
    run(["sudo", "usermod", "-aG", "dialout", user], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    print("NOTE: group membership only takes effect after logging out and back in (or `newgrp dialout`).")


def ensure_node(toolchain_dir: Path, repo_root: Path, *, skip_apt: bool) -> Path | None:
    # Installs the .nvmrc-pinned Node into the managed toolchain directory and returns its bin dir;
    # None when a matching Node is already on PATH. Deliberately not an apt package - see README.md's
    # "Website tooling" for why, and for what a matching Node on PATH means.
    major = pinned_node_major(repo_root)
    if major is None:
        log("No .nvmrc - leaving Node to the caller")
        return None
    if node_on_path_matches(major):
        log(f"Node {major}.x already on PATH - using it")
        return None

    ensure_commands(_TIER_COMMANDS["generic"], skip_apt=skip_apt)
    node_root = toolchain_dir / "node"
    env = network_env()
    tarball, expected = _node_release(major, env)
    record: NodeRecord = {"major": major, "tarball": tarball, "sha256": expected}
    target = node_root / tarball.removesuffix(".tar.xz")
    bindir = target / "bin"
    if (bindir / "node").exists():
        log(f"Node already installed at {target}")
        _write_json(node_root / NODE_RECORD, record)
        return bindir

    log(f"Installing Node {major}.x ({tarball}) into {node_root}")
    # Unpacked aside and renamed into place whole: a run killed mid-unpack leaves no tree that a later
    # run would take for installed. The staging name never matches the leftover clean-up's node-v* glob.
    staging = node_root / f".{tarball}.partial"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    url = f"https://nodejs.org/dist/latest-v{major}.x/{tarball}"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / tarball
        run_retried(["curl", "-fsSL", "--max-time", str(_NODE_TARBALL_TIMEOUT_S), "-o", str(archive), url], env=env, timeout_s=_NODE_TARBALL_TIMEOUT_S + _CURL_SLACK_S)
        # Checked against the same SHASUMS the name came from, before anything is unpacked: this is a
        # binary landing on a bench that flashes firmware.
        actual = _sha256(archive)
        if actual != expected:
            raise SetupError(f"Node tarball checksum mismatch: expected {expected}, got {actual} - nothing was unpacked; retry, or install Node {major} by hand")
        run(["tar", "-xJf", str(archive), "-C", str(staging)], env=env, timeout_s=_BUILD_STEP_TIMEOUT_S)
    unpacked = staging / target.name
    if not (unpacked / "bin" / "node").exists():
        raise SetupError(f"Node install did not produce {target.name}/bin/node (unpacked in {staging})")
    if target.exists():
        shutil.rmtree(target)  # an earlier run's half-made tree: it never reached bin/node
    os.replace(unpacked, target)
    shutil.rmtree(staging)
    _write_json(node_root / NODE_RECORD, record)
    log(f"Node installed: {bindir}")
    return bindir


def ensure_playwright_browser(repo_root: Path, env: dict[str, str] | None, *, skip_apt: bool) -> None:
    # Vitest drives a real Chromium, not jsdom (SPECIFICATION.md Part H), so `npm ci` alone leaves
    # `npm test` unable to start. Only the OS-level libraries need root, hence the separate
    # `install-deps` call; non-fatal throughout, so a Python-only machine still finishes `env`.
    log("Installing the Playwright Chromium build vitest runs against")
    # try/except rather than check=False: run() returns stdout either way, so an exception is the
    # only signal it gives - and this must stay non-fatal without silently swallowing a failure.
    try:
        run(["npx", "playwright", "install", "chromium"], cwd=repo_root, env=env, timeout_s=_NETWORK_STEP_TIMEOUT_S)
    except SetupError as exc:
        log(f"Playwright browser install failed ({exc}) - `npm test` will not run until it succeeds")
        return
    if skip_apt:
        log("Skipping Playwright OS dependencies (--skip-apt) - already present on a normal desktop/CI image")
        return
    try:
        # terminal=True: as a non-root user, playwright runs sudo itself, which asks on the terminal.
        run(["npx", "playwright", "install-deps", "chromium"], cwd=repo_root, env=env, timeout_s=_NETWORK_STEP_TIMEOUT_S, terminal=True)
    except SetupError as exc:
        log(f"Playwright OS dependencies not installed ({exc}) - install them by hand if `npm test` cannot start")


def ensure_repo_at_ref(url: str, dest: Path, ref: str) -> None:
    # Clone-or-update: the same call handles both "doesn't exist yet" (setup) and "already
    # exists, may be pinned to something else" (update) — there's no separate update codepath.
    if not dest.exists():
        log(f"Cloning {url} -> {dest}")
        clone_full(url, dest)
    else:
        # An interrupted clone has no HEAD yet: named, never deleted - a full clone is costly to
        # repeat and the directory may hold local work.
        incomplete = SetupError(f"{dest} is not a complete clone (an interrupted clone?) - remove it and re-run setup")
        if not (dest / ".git").exists():
            raise incomplete
        try:
            run(["git", "rev-parse", "--verify", "HEAD"], cwd=dest, env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
        except SetupError:
            raise incomplete from None
        log(f"Updating existing clone at {dest}")
    checkout_ref(dest, ref)


def existing_bench_ap_ssid() -> str:
    out = run(["nmcli", "-g", "802-11-wireless.ssid", "connection", "show", BENCH_AP_CONN], env=build_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    return out.strip()


def fetch_rp2_submodules(micropython_dir: Path, board: str) -> None:
    log(f"Fetching submodules needed for BOARD={board}")
    rp2_dir = micropython_dir / "ports" / "rp2"
    # Needs network_env(), not build_env(): this Makefile target both fetches submodules
    # over git and runs a preliminary cmake configure pass, so it needs the deterministic
    # PATH *and* real network/proxy access at the same time.
    run_retried(["make", f"BOARD={board}", "submodules"], cwd=rp2_dir, env=network_env(), timeout_s=_NETWORK_STEP_TIMEOUT_S)


def fetch_unix_submodules(micropython_dir: Path) -> None:
    log("Fetching submodules needed for the Unix port")
    unix_dir = micropython_dir / "ports" / "unix"
    # Unlike ports/rp2's "submodules" target, this one is pure git (axtls/berkeley-db/libffi
    # submodule checkouts) with no internal cmake configure pass. MICROPY_PY_LWIP=1 adds lib/lwip
    # for the lwIP host build (extmod/extmod.mk).
    run_retried(["make", "submodules", "MICROPY_PY_LWIP=1"], cwd=unix_dir, env=network_env(), timeout_s=_NETWORK_STEP_TIMEOUT_S)


def generate_bench_ap_credentials() -> tuple[str, str]:
    # A fresh, random, test-only SSID/password per bridge creation - never a fixed default, never a
    # committed one (CLAUDE.md credential rule; tests_hardware/README.md's recipe).
    ssid = f"sensors-bench-{secrets.token_hex(3)}"
    password = secrets.token_urlsafe(12)
    return ssid, password


def latest_stable_micropython_ref() -> str:
    # Backs --latest. The only hand-tracked version is the MicroPython ref (versions.toml), so
    # "upgrade everything" reduces to writing the newest tag back there and letting
    # derive_pico_sdk_commit()/derive_picotool_ref() do the rest.
    out = run_retried(["git", "ls-remote", "--tags", MICROPYTHON_URL], env=network_env(), timeout_s=_REMOTE_QUERY_TIMEOUT_S)
    candidates = []
    for line in out.splitlines():
        m = re.search(r"refs/tags/(v\d+\.\d+(?:\.\d+)?)$", line)
        if m:
            tag = m.group(1)
            parts = tuple(int(x) for x in tag[1:].split("."))
            candidates.append((parts, tag))
    if not candidates:
        raise SetupError("could not find any stable MicroPython release tags")
    candidates.sort()
    return candidates[-1][1]


def load_lwip_macros(path: Path = VERSIONS_PATH) -> dict[str, int]:
    # versions.toml's [lwip] table - the single source of truth for the firmware's lwIP options,
    # so one file drives a build and the connection-scaling sweep is reproducible rather than a
    # sequence of hand edits (SPECIFICATION.md Part B.14.2).
    return dict(load_versions(path)["lwip"])


def load_versions(path: Path) -> Versions:
    # versions.toml as a typed table: the first missing key or wrong type is named with its file and
    # table, so a hand edit fails here rather than as a KeyError deep inside a build. The [lwip]
    # values are validate_lwip_macros()'s to check, at the build that applies them.
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SetupError(f"{path} cannot be read ({exc}) - see SPECIFICATION.md B.3") from exc
    ref = _versions_table(data, path, "micropython").get("ref")
    if not isinstance(ref, str) or not ref:
        raise _versions_defect(path, "micropython", "ref", ref, "a non-empty string")
    toolchain = _versions_table(data, path, "toolchain")
    board = toolchain.get("board")
    if not isinstance(board, str) or not board:
        raise _versions_defect(path, "toolchain", "board", board, "a non-empty string")
    packages = toolchain.get("apt_packages")
    if not isinstance(packages, list) or not all(isinstance(name, str) for name in packages):
        raise _versions_defect(path, "toolchain", "apt_packages", packages, "a list of strings")
    lwip = _versions_table(data, path, "lwip")
    return {"micropython": {"ref": ref}, "toolchain": {"board": board, "apt_packages": packages}, "lwip": cast("dict[str, int]", lwip)}


def log(msg: str) -> None:
    print(f"\n== {msg}", flush=True)


def main() -> int:
    toolchain_dir_default = Path(os.environ.get("PICO_TOOLCHAIN_DIR", Path.home() / "pico-toolchain"))

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--toolchain-dir",
        type=Path,
        default=toolchain_dir_default,
        help="Directory holding the micropython/pico-sdk/picotool source trees (default: $PICO_TOOLCHAIN_DIR or ~/pico-toolchain)",
    )
    common.add_argument("--jobs", type=int, default=os.cpu_count() or 4, help="Parallel make jobs")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command")

    setup_parser = subparsers.add_parser(
        "setup", parents=[common], help="Install or update the toolchain (default if no subcommand given)",
    )
    setup_parser.add_argument("--micropython-ref", help="Build this MicroPython ref instead of the pin, without changing versions.toml (an off-pin build: the platform re-check applies before trusting it)")
    setup_parser.add_argument("--latest", action="store_true", help="Pin versions.toml to the newest stable MicroPython tag (a pin move: the owner's call, and the platform re-check follows)")
    setup_parser.add_argument("--skip-apt", action="store_true", help="Skip installing system/apt packages")
    setup_parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe all build-artifact directories (picotool/build, mpy-cross/build, ports/rp2/build-<board>, "
        "and every Unix-port build flavour (ports/unix/build-standard, build-settrace, build-lwip)) before "
        "building, without re-cloning the git sources -- brings the toolchain back to a from-scratch build state",
    )

    subparsers.add_parser(
        "test",
        parents=[common],
        help="Re-verify an already-installed toolchain with no network/apt access — the CI-friendly check",
    )

    env_parser = subparsers.add_parser(
        "env",
        parents=[common],
        help="Set up a tiered dev environment (generic/flash/bench) - project deps, toolchain, and "
        "(flash/bench) real-hardware access - see README.md's environment-tiers table",
    )
    env_parser.add_argument("--tier", required=True, choices=("generic", "flash", "bench"), help="Environment tier to set up")
    env_parser.add_argument("--micropython-ref", help="Build this MicroPython ref instead of the pin, without changing versions.toml (an off-pin build: the platform re-check applies before trusting it)")
    env_parser.add_argument("--latest", action="store_true", help="Pin versions.toml to the newest stable MicroPython tag (a pin move: the owner's call, and the platform re-check follows)")
    env_parser.add_argument("--skip-apt", action="store_true", help="Skip apt packages, dialout group, and network-manager install (all steps needing sudo)")
    env_parser.add_argument("--skip-npm", action="store_true", help="Skip npm ci even if package.json is present")
    env_parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe all build-artifact directories before building, without re-cloning the git sources",
    )
    env_parser.add_argument("--device", help="[flash/bench] explicit serial device path, skips USB vendor-ID auto-detection")
    env_parser.add_argument("--uplink-iface", help="[bench] explicit uplink (internet-bearing) network interface, skips auto-detection")
    env_parser.add_argument("--wifi-iface", help="[bench] explicit WiFi adapter to host the AP on, skips auto-detection")
    env_parser.add_argument("--ssid", help="[bench] explicit AP SSID - only used when creating a new bridge, ignored if one already exists")

    board_parser = subparsers.add_parser("board", help="Print the resolved MicroPython board's serial path")
    board_parser.add_argument("--device", help="explicit serial device path (else $MPREMOTE_DEVICE, else the one detected board)")

    # Backward/convenience compat: `setup_toolchain.py [--some-setup-flag ...]` (no subcommand)
    # still means "setup", so existing invocations and muscle memory keep working.
    argv = sys.argv[1:]
    if argv and argv[0] not in ("setup", "test", "env", "board", "-h", "--help"):
        argv = ["setup", *argv]
    elif not argv:
        argv = ["setup"]
    args = parser.parse_args(argv)
    if args.command == "board":
        # Reads /sys and /dev only: no lock, no versions.toml, and stdout carries nothing but the path.
        print(resolve_pico_device(args.device))
        return 0

    # One lock around the whole command: run_env() runs run_setup() and then writes <toolchain>/node,
    # and a second flock() on a new descriptor would make this process refuse itself.
    with _stop_commands_on_termination(), toolchain_lock(args.toolchain_dir.expanduser().resolve()):
        versions_path = VERSIONS_PATH
        versions = load_versions(versions_path)
        if args.command == "test":
            return run_test(args, versions)
        if args.command == "env":
            return run_env(args, versions_path, versions)
        return run_setup(args, versions_path, versions)


def network_env() -> dict[str, str]:
    env = build_env()
    for key in NETWORK_ENV_EXTRA:
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def node_on_path_matches(major: str) -> bool:
    node = shutil.which("node")
    if node is None:
        return False
    try:  # the resolved absolute path, not "node" - a partial executable path here would resolve
        # against whatever PATH happens to hold when this runs.
        version = subprocess.run([node, "--version"], capture_output=True, text=True, check=True, timeout=_REMOTE_QUERY_TIMEOUT_S).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return version.strip().lstrip("v").split(".")[0] == major


def pinned_node_major(repo_root: Path) -> str | None:
    # The Node major this project pins, read from .nvmrc - the same file README tells a human to
    # point `nvm use` at, so there is exactly one pin rather than a second one living here.
    nvmrc = repo_root / ".nvmrc"
    if not nvmrc.exists():
        return None
    major = nvmrc.read_text().strip().lstrip("v")
    return major.split(".")[0] if major else None


def print_verification_summary(board: str, mpy_cross_binary: Path, unix_binary: Path) -> int:
    log("All verification checks passed")
    print(f"  1-3. mpy-cross built and cross-compiled the verification test file standalone: {mpy_cross_binary}")
    print("  4-5. Unix port built with the test file frozen in, and the frozen module ran with the expected result")
    print(f"  6. {board} firmware built with the same test file frozen in (build-only, zero errors/warnings)")
    print("  7. Frozen-bytecode verification build artifacts cleaned up")
    print(f"  8. Vanilla Unix port rebuilt as the standing test rig: {unix_binary}")
    others = ", ".join(str(unix_binary.parent.parent / name / "micropython") for name in (UNIX_SETTRACE_BUILD_DIR, UNIX_LWIP_BUILD_DIR))
    print(f"     The settrace build flavour for --coverage and the lwIP host build flavour, each proven post-build: {others}")
    return 0


def read_toolchain_record(toolchain_dir: Path) -> ToolchainRecord | None:
    # None for a missing, unreadable or incomplete record: that toolchain was never verified as recorded.
    try:
        data = json.loads((toolchain_dir / TOOLCHAIN_RECORD).read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or set(data) != ToolchainRecord.__required_keys__:
        return None
    return cast("ToolchainRecord", data)


def remove_outdated_leftovers(toolchain_dir: Path) -> None:
    # Each removal is printed with its reason; a leftover resolving outside the toolchain directory (a
    # symlink) is reported and kept, so nothing outside it is ever touched.
    root = toolchain_dir.resolve()
    for path, why in _outdated_leftovers(toolchain_dir):
        if not path.resolve().is_relative_to(root):
            log(f"WARNING: not removing {path} ({why}): it resolves outside {toolchain_dir}")
            continue
        print(f"Removing outdated {path} ({why})")
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()


def resolve_board_serial(by_id_dir: Path = Path("/dev/serial/by-id"), sys_tty_dir: Path = Path("/sys/class/tty"), dev_dir: Path = Path("/dev")) -> list[Path]:
    # Every /dev/serial/by-id link with MicroPython's own USB name whose live tty reports vendor 2e8a,
    # sorted; the by-id path survives the re-enumeration a hard reset causes. With /sys unreadable, the
    # MicroPython name alone decides, as the bench harness does.
    if not by_id_dir.is_dir():
        return []
    links = sorted(by_id_dir.glob(BOARD_BY_ID_GLOB))
    if not sys_tty_dir.is_dir():
        return links
    found = []
    for link in links:
        tty = link.resolve().name
        if tty.startswith(("ttyACM", "ttyUSB")) and (dev_dir / tty).exists() and _read_usb_id_vendor(tty, sys_tty_dir) == PICO_USB_VENDOR_ID:
            found.append(link)
    return found


def resolve_pico_device(explicit: str | None) -> Path:
    # --device, then $MPREMOTE_DEVICE, then exactly one detected board; none or several is a hard
    # error naming both ways to choose, never a guess at which board to drive.
    chosen = explicit or os.environ.get("MPREMOTE_DEVICE")
    if chosen:
        return Path(chosen)
    candidates = resolve_board_serial()
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise SetupError("no MicroPython board found (USB vendor 2e8a with a /dev/serial/by-id/usb-MicroPython_… link) - plug it in, or pass --device / set MPREMOTE_DEVICE")
    names = ", ".join(str(c) for c in candidates)
    raise SetupError(f"multiple MicroPython boards found ({names}) - pass --device or set MPREMOTE_DEVICE to pick one")


def run(cmd: list[str], cwd: Path | None = None, *, check: bool = True, env: dict[str, str] | None = None, timeout_s: float, stdin_text: str | None = None, secrets: tuple[str, ...] = (), terminal: bool = False) -> str:
    # Runs cmd with its output streamed, never showing a secret, and returns that output. timeout_s is
    # required, so no step waits forever on a stalled third party; the command's own session lets a
    # timeout or an interrupted installer stop everything it started (_keeps_terminal() says when not).
    shown = _redact(" ".join(cmd), secrets)
    print(f"$ {shown}" + (f"   (cwd={cwd})" if cwd else ""), flush=True)
    own_session = not _keeps_terminal(cmd, terminal=terminal)
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL if stdin_text is None else subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", start_new_session=own_session,
    )
    lines: list[str] = []
    reader = threading.Thread(target=_stream_output, args=(cast("IO[str]", proc.stdout), lines, secrets), daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout_s
    finished = False
    try:
        if stdin_text is not None and proc.stdin is not None:
            # A short text into an empty pipe is taken whole without blocking; a command that exits
            # unread breaks the pipe, and its exit status says why.
            with contextlib.suppress(BrokenPipeError):
                proc.stdin.write(stdin_text)
                proc.stdin.close()
        proc.wait(timeout=timeout_s)
        reader.join(max(0.0, deadline - time.monotonic()))
        finished = not reader.is_alive()  # else something it started still holds its output open
    except subprocess.TimeoutExpired:
        pass
    finally:
        if not finished:
            _stop(proc, own_session=own_session)
            reader.join(_STOP_GRACE_S)
    if not finished:
        raise SetupError(f"timed out after {timeout_s:g} s: {shown} - a stalled download, mirror or build; check connectivity and any proxy, then re-run (limits: SPECIFICATION.md Part N)")
    if check and proc.returncode != 0:
        raise SetupError(f"command failed (exit {proc.returncode}): {shown}")
    return "".join(lines)


def run_env(args: argparse.Namespace, versions_path: Path, versions: Versions) -> int:
    # Tiered dev-environment setup, each tier a strict superset of the one before it: generic
    # (project deps + the firmware/Unix-port toolchain), flash (+ USB serial access and a real board),
    # bench (+ a WiFi bridge/AP on this host). Per-tier detail: README.md's environment-tiers table.
    run_setup(args, versions_path, versions, tier=args.tier)
    run_project_dependency_install(REPO_ROOT, args.toolchain_dir.expanduser().resolve(), skip_npm=args.skip_npm, skip_apt=args.skip_apt)

    if args.tier == "generic":
        log("Generic environment ready: Python/Node deps installed, firmware/Unix-port toolchain verified")
        return 0

    ensure_dialout_group(skip=args.skip_apt)
    device = resolve_pico_device(args.device)
    log(f"Flash environment ready: {device} reachable via scripts/mpremote_connect.sh")
    if args.tier == "flash":
        return 0

    ensure_commands(_TIER_COMMANDS["bench"], skip_apt=args.skip_apt)
    check_passwordless_sudo(_BENCH_SUDO_COMMANDS)
    # Always call ensure_bench_bridge() - it already handles the already-exists case itself, so
    # there's exactly one place this logic lives, not a separate short-circuit that could drift.
    ssid = ensure_bench_bridge(args.uplink_iface, args.wifi_iface, args.ssid, os.environ.get("BENCH_AP_PASSWORD") or None)
    log(f"Bench environment ready: bridge {BENCH_BRIDGE_CONN!r} up, hosted AP SSID {ssid!r}")
    return 0


def run_frozen_verify_on_unix(unix_binary: Path) -> None:
    # Step 5: imports the frozen module *by name*, with no source .py file anywhere on disk for
    # the interpreter to find - the only way this can succeed is if the module was actually baked
    # into the binary as frozen bytecode, not merely compiled and left on disk somewhere.
    log("Importing the frozen verification module inside the Unix port and checking its result")
    out = run(
        [str(unix_binary), "-c", f"import {FROZEN_VERIFY_MODULE}; print({FROZEN_VERIFY_MODULE}.RESULT)"],
        env=build_env(),
        timeout_s=_REMOTE_QUERY_TIMEOUT_S,
    )
    if "FROZEN_VERIFY_OK" not in out:
        raise SetupError("frozen verification module did not produce the expected result (see log above)")
    print(out.strip())


def run_project_dependency_install(repo_root: Path, toolchain_dir: Path, *, skip_npm: bool, skip_apt: bool) -> None:
    # The Python (`uv sync`) and website (`npm ci`) dev-tooling installs every tier needs. Runs with
    # env=None (inherit the caller's), unlike every other subprocess here: build_env()'s fixed PATH
    # would hide the caller's own uv/npm install.
    log("Installing Python project dependencies (uv sync)")
    run_retried(["uv", "sync"], cwd=repo_root, env=None, timeout_s=_NETWORK_STEP_TIMEOUT_S)
    if skip_npm:
        log("Skipping npm ci (--skip-npm)")
        return
    if not (repo_root / "package.json").exists():
        log("No package.json found - skipping npm ci")
        return
    # Installs the pinned Node when the host has none, rather than the soft skip that left the
    # web tier silently unrunnable on the bench Pi4. Not gated on --skip-apt - no system package,
    # no sudo, just a tarball into the managed toolchain dir; --skip-npm is that gate.
    node_bin = ensure_node(toolchain_dir, repo_root, skip_apt=skip_apt)
    env = None
    if node_bin is not None:
        env = dict(os.environ)
        env["PATH"] = f"{node_bin}{os.pathsep}{env.get('PATH', '')}"
    elif shutil.which("npm") is None:
        log("npm not found and no Node could be installed - skipping npm ci")
        return
    node = str(node_bin / "node") if node_bin is not None else shutil.which("node")
    if node is not None:
        log(f"Node in use: {node} {_first_line(run([node, '--version'], env=env, timeout_s=_REMOTE_QUERY_TIMEOUT_S))}")
    log("Installing website tooling dependencies (npm ci)")
    run(["npm", "ci"], cwd=repo_root, env=env, timeout_s=_NETWORK_STEP_TIMEOUT_S)
    ensure_playwright_browser(repo_root, env, skip_apt=skip_apt)


# @tunable tool.uv_sync_backoff_step_s = 10.0
def run_retried(cmd: list[str], cwd: Path | None = None, *, env: dict[str, str] | None = None, timeout_s: float, secrets: tuple[str, ...] = (), attempts: int = NETWORK_ATTEMPTS, backoff_s: float = 10.0, before_retry: Callable[[], None] | None = None) -> str:
    # run(), retried with a growing pause, for a step that downloads from a third party; after the last
    # attempt the SetupError names the step and the fix. before_retry clears what a failed attempt left.
    for attempt in range(1, attempts):
        try:
            return run(cmd, cwd=cwd, env=env, timeout_s=timeout_s, secrets=secrets)
        except SetupError as e:
            log(f"{e} - attempt {attempt}/{attempts}, retrying in {attempt * backoff_s:.0f}s")
            if before_retry is not None:
                before_retry()
            time.sleep(attempt * backoff_s)
    try:
        return run(cmd, cwd=cwd, env=env, timeout_s=timeout_s, secrets=secrets)
    except SetupError as e:
        raise SetupError(f"{e} - all {attempts} attempts failed: check connectivity and any proxy, then re-run") from e


def run_setup(args: argparse.Namespace, versions_path: Path, versions: Versions, *, tier: str = "setup") -> int:
    # Install or update - the steps are "How it works" in SPECIFICATION.md Part B.3. There is no
    # separate update branch: ensure_repo_at_ref() clones if missing and fetches otherwise, so
    # re-running against an existing --toolchain-dir *is* the update.
    pinned = versions["micropython"]["ref"]
    if args.latest and args.micropython_ref is not None:
        raise SetupError("--latest and --micropython-ref are exclusive")
    mpy_ref = args.micropython_ref or pinned
    moved_from = None
    if args.latest:
        mpy_ref = latest_stable_micropython_ref()
        if mpy_ref == pinned:
            log(f"--latest: already on the newest stable tag ({pinned}) - {versions_path} unchanged")
        else:
            log(f"--latest resolved to MicroPython {mpy_ref}; updating {versions_path}")
            write_micropython_ref(versions_path, mpy_ref)
            versions = load_versions(versions_path)
            moved_from = pinned
            print(_PIN_MOVED_NOTICE.format(new=mpy_ref))  # now, since a build that fails below leaves it moved

    board = versions["toolchain"]["board"]
    apt_packages = versions["toolchain"]["apt_packages"]

    toolchain_dir = args.toolchain_dir.expanduser().resolve()
    toolchain_dir.mkdir(parents=True, exist_ok=True)
    micropython_dir = toolchain_dir / "micropython"
    pico_sdk_dir = toolchain_dir / "pico-sdk"
    picotool_dir = toolchain_dir / "picotool"

    print(f"Toolchain directory: {toolchain_dir}")
    print(f"MicroPython ref: {mpy_ref}")
    print(f"Board: {board}")

    # Dropped before anything here changes: the checkout moves long before the verification, and a
    # record outliving an interrupted run would describe binaries the checkout no longer matches.
    previous_record = read_toolchain_record(toolchain_dir)
    delete_toolchain_record(toolchain_dir)
    if args.clean:
        clean_build_dirs(toolchain_dir, board)

    ensure_apt_packages(apt_packages, skip=args.skip_apt)

    log(f"Preparing MicroPython at {mpy_ref}")
    ensure_repo_at_ref(MICROPYTHON_URL, micropython_dir, mpy_ref)

    pico_sdk_commit = derive_pico_sdk_commit(micropython_dir, mpy_ref)
    log(f"MicroPython {mpy_ref} pins pico-sdk commit {pico_sdk_commit}")
    ensure_repo_at_ref(PICO_SDK_URL, pico_sdk_dir, pico_sdk_commit)
    run_retried(["git", "submodule", "update", "--init", "lib/mbedtls"], cwd=pico_sdk_dir, env=network_env(), timeout_s=_NETWORK_STEP_TIMEOUT_S)

    picotool_ref, pico_sdk_describe = derive_picotool_ref(pico_sdk_dir, pico_sdk_commit)
    log(f"Matching picotool tag: {picotool_ref}")
    ensure_repo_at_ref(PICOTOOL_URL, picotool_dir, picotool_ref)

    picotool_version = build_and_install_picotool(picotool_dir, pico_sdk_dir, args.jobs, tag=picotool_ref, previous_record=previous_record, tier=tier)
    fetch_rp2_submodules(micropython_dir, board)
    fetch_unix_submodules(micropython_dir)

    mpy_cross_binary, unix_binary = run_verification_sequence(micropython_dir, toolchain_dir, board, args.jobs)

    status = print_verification_summary(board, mpy_cross_binary, unix_binary)
    record = _toolchain_record(micropython_dir, versions, versions_path, built_ref=mpy_ref)
    record["pico_sdk_commit"] = pico_sdk_commit
    record["pico_sdk_describe"] = pico_sdk_describe
    record["picotool_tag"] = picotool_ref
    record["picotool_version"] = picotool_version
    write_toolchain_record(toolchain_dir, record)
    remove_outdated_leftovers(toolchain_dir)
    if mpy_ref != pinned:
        print(_PLATFORM_RECHECK_NOTICE.format(new=mpy_ref, old=pinned))
    if moved_from is not None:
        print(_PIN_MOVED_NOTICE.format(new=mpy_ref))  # again under the re-check notice, at the end of the log
    return status


def run_test(args: argparse.Namespace, versions: Versions) -> int:
    # Re-verify an existing install, offline: just run_verification_sequence() again against
    # whatever is already checked out — see the module docstring and SPECIFICATION.md Part B.3's "How it
    # works" for why apt/git network access is never needed here.
    board = versions["toolchain"]["board"]
    toolchain_dir = args.toolchain_dir.expanduser().resolve()
    micropython_dir = toolchain_dir / "micropython"
    rp2_dir = micropython_dir / "ports" / "rp2"

    if not (micropython_dir / "mpy-cross").is_dir() or not rp2_dir.is_dir():
        raise SetupError(
            f"no toolchain found at {toolchain_dir} — run `setup` first "
            f"(e.g. `uv run toolchain/setup_toolchain.py setup`)",
        )

    log(f"Testing existing toolchain at {toolchain_dir} (offline: no apt/git network access)")
    print(f"Board: {board}")

    # Deliberately touches neither apt, git remotes, nor the pico-sdk/picotool derivation: it
    # re-verifies what is already checked out, so it is fast, reproducible and offline - `setup`
    # provisions once, `test` is the repeatable gate. Submodules are assumed already fetched.
    previous = read_toolchain_record(toolchain_dir)
    delete_toolchain_record(toolchain_dir)
    mpy_cross_binary, unix_binary = run_verification_sequence(micropython_dir, toolchain_dir, board, args.jobs)

    status = print_verification_summary(board, mpy_cross_binary, unix_binary)
    record = _toolchain_record(micropython_dir, versions, VERSIONS_PATH, built_ref=None)
    if previous is not None and previous["micropython_commit"] == record["micropython_commit"]:
        # What only `setup` derives still holds while the checkout it was derived for is unchanged.
        record["built_ref"] = previous["built_ref"]
        record["pico_sdk_commit"] = previous["pico_sdk_commit"]
        record["pico_sdk_describe"] = previous["pico_sdk_describe"]
        record["picotool_tag"] = previous["picotool_tag"]
        record["picotool_version"] = previous["picotool_version"]
    write_toolchain_record(toolchain_dir, record)
    remove_outdated_leftovers(toolchain_dir)
    return status


def run_verification_sequence(micropython_dir: Path, toolchain_dir: Path, board: str, jobs: int) -> tuple[Path, Path]:
    # The 8-step frozen-bytecode verification chain, each step gating the next (SPECIFICATION.md
    # Part B.6 has the full account, including why no separate vanilla RP2 build is also kept).
    with tempfile.TemporaryDirectory() as tmp:
        test_dir = Path(tmp)

        test_file = write_frozen_verify_test(test_dir)
        mpy_cross_binary = build_mpy_cross(micropython_dir, jobs)
        cross_compile_frozen_verify_test(mpy_cross_binary, test_file)

        unix_manifest = test_dir / "manifest_unix.py"
        write_freeze_manifest(unix_manifest, "variants/manifest.py")
        unix_binary = build_unix_port(micropython_dir, toolchain_dir, jobs, frozen_manifest=unix_manifest)
        run_frozen_verify_on_unix(unix_binary)

        rp2_manifest = test_dir / "manifest_rp2.py"
        write_freeze_manifest(rp2_manifest, f"boards/{board}/manifest.py")
        build_firmware(micropython_dir, board, jobs, frozen_manifest=rp2_manifest, toolchain_dir=toolchain_dir)
        # test_dir (the test module + both manifests) is removed automatically once this
        # "with" block exits - nothing further to clean up for those.

    clean_frozen_verification_build_dirs(toolchain_dir, board)

    unix_binary = build_unix_port(micropython_dir, toolchain_dir, jobs)  # vanilla rebuild: the real test rig
    # Second, separate binary, into its own build dir: --coverage needs sys.settrace, and compiling
    # it in costs every OTHER run 4-5x on allocation figures, so the two cannot share one build.
    build_unix_port(micropython_dir, toolchain_dir, jobs, settrace=True)
    # Third: the lwIP host build, the only one that runs the firmware's patched modlwip.
    build_unix_lwip_port(micropython_dir, toolchain_dir, jobs)

    return mpy_cross_binary, unix_binary


@contextlib.contextmanager
def toolchain_lock(toolchain_dir: Path) -> Iterator[None]:
    # One setup, test or firmware build per toolchain directory: a second fails at once naming the
    # first, never waits (a waiting run could hang). The OS drops the lock with a dying holder, so it
    # never goes stale; the directory is created first, so a first setup can take it.
    toolchain_dir.mkdir(parents=True, exist_ok=True)
    with (toolchain_dir / TOOLCHAIN_LOCK).open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.seek(0)
            holder = lock.read().strip() or "unknown"
            raise SetupError(f"another setup or firmware build (pid {holder}) is using {toolchain_dir} - wait for it to finish, or use another --toolchain-dir") from None
        lock.seek(0)
        lock.truncate()
        lock.write(f"{os.getpid()}\n")
        lock.flush()
        yield


def write_freeze_manifest(manifest_path: Path, port_manifest_relpath: str) -> None:
    # Mirrors this repo's manifest convention (legacy/firmware/python/Manifest/manifest.py): the
    # port's own manifest, then freeze FROZEN_MODULE_SUBDIR. freeze() resolves relative to this file, so
    # manifest_path is written as a sibling of that subdir - never inside it, never freezing itself.
    manifest_path.write_text(
        f'include("$(PORT_DIR)/{port_manifest_relpath}")\nfreeze("{FROZEN_MODULE_SUBDIR}")\n',
    )


def write_frozen_verify_test(test_dir: Path) -> Path:
    # Step 1 of run_verification_sequence(): the one .py file cross-compiled/frozen/imported at
    # every later step - see FROZEN_VERIFY_PY.
    module_dir = test_dir / FROZEN_MODULE_SUBDIR
    module_dir.mkdir()
    test_file = module_dir / f"{FROZEN_VERIFY_MODULE}.py"
    test_file.write_text(FROZEN_VERIFY_PY)
    return test_file


def write_micropython_ref(path: Path, ref: str) -> None:
    # Rewrites the one `ref = "..."` line, through a checked copy and a rename: a missing, doubled or
    # misplaced line is refused with the file untouched, since the pin moves only on purpose.
    text = path.read_text()
    new_text, count = re.subn(r'(?m)^ref = "[^"\n]*"$', f'ref = "{ref}"', text)
    if count == 0:
        raise SetupError(f'{path} has no `ref = "…"` line under [micropython] - nothing was written; restore the line (see SPECIFICATION.md B.3) and re-run')
    if count > 1:
        raise SetupError(f'{path} has {count} `ref = "…"` lines - the pin must be exactly one; remove the extra ones and re-run')
    candidate = path.with_name(f"{path.name}.tmp")
    candidate.write_text(new_text)
    try:
        written = load_versions(candidate)["micropython"]["ref"]
    except SetupError:
        written = None
    if written != ref:
        candidate.unlink()
        raise SetupError(f'{path}: its one `ref = "…"` line is not the [micropython] ref - nothing was written; move it under [micropython] (see SPECIFICATION.md B.3) and re-run')
    os.replace(candidate, path)


def write_toolchain_record(toolchain_dir: Path, record: ToolchainRecord) -> None:
    _write_json(toolchain_dir / TOOLCHAIN_RECORD, record)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (SetupError, micropython_overrides.OverrideError) as exc:  # both name their own cause and fix
        print(f"\nFAILED: {exc}", file=sys.stderr)
        sys.exit(1)
