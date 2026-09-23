"""Host-side (CPython) harness primitives for the flash/bench real-hardware test tier. Drives a
real board over `mpremote` and, for bench, real `nmcli`/`iw` calls against the bridge host - never
under the MicroPython Unix port. See tests_hardware/README.md for how to run this tier.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import serial

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

# For `import setup_toolchain` below - the same bare-sibling shape as that module's own
# `import micropython_overrides` (host_typecheck.ini's own account of why both need a path slot).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "toolchain"))
import setup_toolchain
from setup_toolchain import detect_pico_serial_devices

REPO_ROOT = Path(__file__).resolve().parent.parent

# SPECIFICATION.md Part I.4(e)'s bar, as the board's own log shows it. BOTH spellings: src/'s
# degrade handlers log str(e), so a real caught allocation failure reads "memory allocation
# failed, ..." (py/runtime.c) and the class name appears only in an UNCAUGHT traceback.
MEMORY_ERROR_MARKERS = ("MemoryError", "memory allocation failed")

def configured_max_connections(device: str = "dev") -> int:
    """The admission ceiling this repo's config would build for `device` - its own
    [device].max_connections, else WebserverService's own default. It describes the TREE, not
    necessarily the image on the board, so a test that cares asserts the two agree."""
    sys.path.insert(0, str(REPO_ROOT))
    import tomllib

    from buildgen.validate import webserver_init_default

    with (REPO_ROOT / "devices" / f"{device}.toml").open("rb") as f:
        table = tomllib.load(f)["device"]
    ceiling = table.get("max_connections")
    return int(ceiling) if ceiling is not None else webserver_init_default(REPO_ROOT / "src", "max_connections")


def discover_max_connections(host: str, port: int = 80, probe_limit: int = 64, settle_s: float = 1.0, dwell_s: float = 0.3) -> int:
    """The ceiling the BOARD actually holds, found by holding connections open one at a time until
    one is refused. The only figure that is silicon's own rather than the tree's, and the one a
    raised lwIP PCB count has to be confirmed against (SPECIFICATION.md Part B.14.2)."""
    import socket
    import time

    # `dwell_s` must stay well under the server's own per-call read timeout, because an admitted
    # connection that says nothing is closed with a 400 once that fires - so a slow walk frees
    # slots as fast as it takes them and never reaches the ceiling (SPECIFICATION.md Part H.7.1).
    time.sleep(settle_s)  # _serve()'s slot release outlives the response (Part I.6), so start clean
    held: list[socket.socket] = []
    started = time.monotonic()
    try:
        for admitted in range(probe_limit):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(dwell_s)
            sock.connect((host, port))
            held.append(sock)
            try:
                payload = sock.recv(4096)
            except ConnectionResetError:
                _assert_probe_held(held[:-1], started)
                return admitted  # refused by reset: this one did not get a slot
            except TimeoutError:
                continue  # held open, as an admitted connection with nothing to say should be
            if payload == b"":
                _assert_probe_held(held[:-1], started)
                return admitted  # refused without a response: this one did not get a slot
            raise AssertionError(f"connection {admitted} against {host} answered {payload[:40]!r} instead of being held open - the walk outran the server's own idle timeout, so this reading is not a ceiling (see discover_max_connections's own note)")
        raise AssertionError(f"no connection was refused within {probe_limit} attempts against {host} - the ceiling is higher than this probe looks, or admission is not bounded at all")
    finally:
        for sock in held:
            sock.close()
        _wait_for_slots_to_drain(host, port)


def _wait_for_slots_to_drain(host: str, port: int, timeout_s: float = 10.0) -> None:
    """Block until the board admits a connection again. A slot is released in _serve()'s finally,
    AFTER the writer close is awaited, so it outlives the client's own close by ~0.8s here - and a
    caller that measured the ceiling has just filled every one of them."""
    import socket

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.3)
        try:
            sock.connect((host, port))
            sock.recv(4096)  # a refusal answers immediately; an admitted connection times out
        except (TimeoutError, BlockingIOError):
            return  # held open, so a slot was free: the board is serveable again
        except OSError:
            pass  # refused or unreachable, both meaning "not yet"
        finally:
            sock.close()
        time.sleep(0.1)
    raise AssertionError(f"{host}:{port} never admitted a connection again within {timeout_s}s of the probe releasing its own - the slots did not drain")


def _assert_probe_held(admitted_socks: list[Any], started: float) -> None:
    """Every connection the probe counted must still be open at the moment the refusal landed,
    or they were never held simultaneously and the count is an artefact of the walk's own pace."""
    for index, sock in enumerate(admitted_socks):
        sock.settimeout(0.05)
        try:
            payload = sock.recv(4096)
        except (TimeoutError, BlockingIOError):
            continue  # still open with nothing to say, which is what an admitted connection does
        except ConnectionResetError:
            payload = b"<reset>"
        raise AssertionError(f"connection {index} was no longer held ({payload[:40]!r}) {time.monotonic() - started:.2f}s into the walk - the count is not a simultaneous ceiling")


# Read from the module that CREATES these NetworkManager connections rather than copied, so a
# rename there cannot leave the bench tier looking for a rig nobody built - its skip gate
# deselects rather than fails, which is exactly the way that goes unnoticed.
BENCH_BRIDGE_CONN = setup_toolchain.BENCH_BRIDGE_CONN
BENCH_ETH_CONN = setup_toolchain.BENCH_ETH_CONN
BENCH_AP_CONN = setup_toolchain.BENCH_AP_CONN


def _usb_reset_device(device: str) -> bool:
    """Unbind/rebind `device`'s USB device from the kernel `usb` driver - same effect as a
    physical unplug/replug, recovering a wedged raw-REPL-entry state (see tests_hardware/README.md).
    Returns True if a reset was attempted, False if the device path couldn't be resolved."""
    # .resolve() first: `device` is normally the /dev/serial/by-id symlink resolve_board_device()
    # returns, and that name has no /sys/class/tty entry - without this the whole unbind/rebind
    # recovery below silently no-ops (returns False) on the default device path.
    name = Path(device).resolve().name  # e.g. "ttyACM0"
    sys_tty_device = Path("/sys/class/tty") / name / "device"
    if not sys_tty_device.exists():
        return False
    # The tty device node's own symlink target is the USB *interface* (e.g. .../1-1.4:1.0); the USB
    # *device* one level up is what actually needs unbinding - its own directory name is the real
    # bus-port ID ("1-1.4").
    resolved = sys_tty_device.resolve()
    usb_device_dir = resolved.parent
    usb_id = usb_device_dir.name
    try:
        subprocess.run(["sudo", "tee", "/sys/bus/usb/drivers/usb/unbind"], input=usb_id, capture_output=True, text=True, timeout=10.0, check=False)
        time.sleep(2.0)
        subprocess.run(["sudo", "tee", "/sys/bus/usb/drivers/usb/bind"], input=usb_id, capture_output=True, text=True, timeout=10.0, check=False)
        time.sleep(3.0)
    except (subprocess.TimeoutExpired, OSError):
        return False
    return True


class HardwareNotAvailableError(RuntimeError):
    """Raised when a real board/bench isn't reachable - conftest.py turns it into a skip, so this
    tier stays collectible with nothing attached. resolve_board_device()'s ambiguous-hardware raise
    is the deliberate exception: two attached boards must error naming both, never skip."""


class HardwareTestFailureError(AssertionError):
    """Raised for a genuine real-hardware assertion failure - deliberately a plain AssertionError
    subclass so pytest reports it like any other failed assertion, not a framework-level error."""


def wait_until(
    check_fn: Callable[[], bool],
    timeout_s: float,
    poll_interval_s: float = 1.0,
    description: str = "condition",
) -> bool:
    """Bounded poll-until-condition wait, test-harness-only (never used to change src/'s own real
    timing - SPECIFICATION.md Part F.3). Polls `check_fn()` until truthy or `timeout_s` elapses,
    treating a raising check as not-yet-ready; always returns True or raises TimeoutError."""
    deadline = time.monotonic() + timeout_s
    last_exc: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            if check_fn():
                return True
        except Exception as exc:
            last_exc = exc
        time.sleep(poll_interval_s)
    try:
        if check_fn():
            return True
    except Exception as exc:
        last_exc = exc
    detail = f" (last error: {last_exc!r})" if last_exc is not None else ""
    raise TimeoutError(f"timed out after {timeout_s}s waiting for: {description}{detail}")


@dataclass
class MpremoteResult:
    returncode: int
    stdout: str
    stderr: str


_BOARD_BY_ID_GLOB = "usb-MicroPython_Board_in_FS_mode_*-if00"
# Returned when no Pico-family board is attached at all: a path that cannot exist, so the `board`
# fixture's own is_reachable() probe fails and SKIPS (this tier stays collectible with nothing
# attached) without mpremote ever opening some other device's port to find that out.
_NO_BOARD_DEVICE = "/dev/no-pico-serial-device-detected"
# Bounded for the same reason the USB unbind/rebind escalation below is: a node that keeps
# vanishing and reappearing under an alternating name would otherwise extend the grace window
# forever, and no single subprocess timeout breaks out of _mpremote()'s own loop.
_MAX_DEVICE_REBINDS = 2


def _stable_name_for(dev_path: Path, by_id_dir: Path) -> str:
    """The `/dev/serial/by-id` symlink pointing at `dev_path`, or `dev_path` itself if none does.
    Matching by target rather than by name drops the old hardcoded product string, so a board whose
    USB descriptor reads differently still resolves to a stable name."""
    if by_id_dir.is_dir():
        for link in sorted(by_id_dir.iterdir()):
            if link.resolve() == dev_path.resolve():
                return str(link)
    return str(dev_path)


def resolve_board_device(
    by_id_dir: Path = Path("/dev/serial/by-id"),
    sys_tty_dir: Path = Path("/sys/class/tty"),
    dev_dir: Path = Path("/dev"),
) -> str:
    """The board's current serial node, found by setup_toolchain.py's vendor-ID detection (never a
    bare ttyACM scan, which could pick the bench's Arduino) and named by its by-id symlink, which
    survives the re-enumeration a hard reset causes. Two matches is a hard error, not sorted()[0]."""
    candidates = detect_pico_serial_devices(sys_tty_dir, dev_dir)
    if not candidates and by_id_dir.is_dir():
        candidates = [link.resolve() for link in sorted(by_id_dir.glob(_BOARD_BY_ID_GLOB))]
    if len(candidates) > 1:
        names = ", ".join(str(c) for c in candidates)
        raise HardwareNotAvailableError(
            f"multiple Raspberry Pi USB serial devices found ({names}) - pass --device or set "
            "MPREMOTE_DEVICE to pick one explicitly, rather than have the suite guess which board to drive",
        )
    if not candidates:
        return _NO_BOARD_DEVICE
    return _stable_name_for(candidates[0], by_id_dir)


class Board:
    """Wraps `uv run mpremote connect <device> ...`, the one generic isolated-driver mechanism,
    so individual test files never shell out to mpremote themselves. Also where
    `machine.bootloader()` re-flash and hard-reset live, for tests_hardware/flash/test_toolchain_flash_boot.py."""

    def __init__(self, device: str | None = None, default_timeout_s: float = 60.0) -> None:
        self._pinned_device = device or os.environ.get("MPREMOTE_DEVICE")
        self.device = self._pinned_device or resolve_board_device()
        self.default_timeout_s = default_timeout_s

    def _rebind_device_if_moved(self) -> bool:
        """Re-resolves the serial node when the current one has vanished; True if it moved. A hard
        reset re-enumerates the CDC-ACM device with no index guarantee (observed ttyACM0 -> ttyACM1
        mid-suite). An explicitly pinned device is never second-guessed."""
        if self._pinned_device is not None or Path(self.device).exists():
            return False
        rebound = resolve_board_device()
        if rebound == self.device:
            return False
        self.device = rebound
        return True

    def _mpremote(self, *args: str, timeout_s: float | None = None, allow_recovery: bool = True) -> MpremoteResult:
        """Runs one `uv run mpremote connect <device> ...` call, retrying past known transient
        USB-settle-race connection failures (see tests_hardware/README.md). `allow_recovery=False`
        (is_reachable()'s own use) skips retry, so a real expected disconnect isn't masked."""
        cmd = ["uv", "run", "mpremote", "connect", self.device, *args]
        transient_markers = ("may be in use by another program", "could not enter raw repl", "could not open")
        grace_deadline = time.monotonic() + 10.0
        usb_reset_attempted = False
        rebinds_left = _MAX_DEVICE_REBINDS
        while True:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=timeout_s or self.default_timeout_s,
                    check=False,
                )
            except FileNotFoundError as exc:
                raise HardwareNotAvailableError(f"uv/mpremote not on PATH: {exc}") from exc
            except subprocess.TimeoutExpired as exc:
                raise HardwareTestFailureError(f"mpremote {' '.join(args)} timed out after {timeout_s or self.default_timeout_s}s") from exc
            transient = proc.returncode != 0 and any(marker in proc.stderr.lower() for marker in transient_markers)
            if not transient or not allow_recovery:
                return MpremoteResult(proc.returncode, proc.stdout, proc.stderr)
            if time.monotonic() < grace_deadline:
                time.sleep(0.5)
                continue
            # The 10s settle-wait grace window above is sometimes not enough - this bench's USB
            # device can wedge into indefinite raw-REPL-entry failure until unbound/rebound (see
            # tests_hardware/README.md). Escalate once, never more than once per call.
            if rebinds_left > 0 and self._rebind_device_if_moved():
                rebinds_left -= 1
                # The node moved under us (re-enumeration after a reset) - retry on the new one
                # before escalating to a USB unbind/rebind, which would not have helped.
                cmd = ["uv", "run", "mpremote", "connect", self.device, *args]
                grace_deadline = time.monotonic() + 10.0
                continue
            if not usb_reset_attempted:
                usb_reset_attempted = True
                if _usb_reset_device(self.device):
                    grace_deadline = time.monotonic() + 10.0
                    continue
            return MpremoteResult(proc.returncode, proc.stdout, proc.stderr)

    def is_reachable(self) -> bool:
        # allow_recovery=False: report the honest current state, since a caller may be polling
        # for an expected "no" while waiting out a real reboot. Raw-REPL entry always Ctrl-C's the
        # device, so never poll this against a live system - is_device_present() is for that.
        try:
            result = self._mpremote("exec", "print('mpremote-ok')", timeout_s=10.0, allow_recovery=False)
        except (HardwareNotAvailableError, HardwareTestFailureError):
            return False
        return result.returncode == 0 and "mpremote-ok" in result.stdout

    def is_device_present(self) -> bool:
        """Passive, non-disruptive USB-presence check - opens/closes the CDC-ACM serial port
        without writing a byte, unlike is_reachable()'s raw-REPL entry (see its comment).
        Correctly reports False during a hard_reset()'s USB re-enumeration window."""
        try:
            probe = serial.Serial(self.device, baudrate=115200, timeout=0.2)
        except (OSError, serial.SerialException):
            return False
        probe.close()
        return True

    def exec(self, expr: str, timeout_s: float | None = None) -> str:
        """`mpremote exec "<expr>"` - like run_isolated(), this always interrupts whatever's
        running first (see tail_log()'s docstring), then evaluates `expr` in a fresh raw-REPL
        session. Never use for passive live-system observation - use tail_log() instead."""
        result = self._mpremote("exec", expr, timeout_s=timeout_s)
        if result.returncode != 0:
            # Both streams included: a device-side traceback prints on mpremote's stdout, not
            # stderr, and would otherwise be silently dropped.
            raise HardwareTestFailureError(f"mpremote exec {expr!r} failed (exit {result.returncode}):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result.stdout

    def run_isolated(self, script_path: str | Path, *, soft_reset_after: bool = True, timeout_s: float | None = None, allow_recovery: bool = True) -> str:
        """Isolated-driver mode: `mpremote run <script>` against the real frozen src/ drivers,
        re-arming the watchdog first, never leaving main.py running (tests_hardware/README.md).
        allow_recovery=False when the disconnect IS the outcome - else the 10s grace is measured."""
        args = ["exec", "import machine; machine.WDT(timeout=8000)", "run", str(script_path)]
        if soft_reset_after:
            args.append("soft-reset")
        result = self._mpremote(*args, timeout_s=timeout_s, allow_recovery=allow_recovery)
        if result.returncode != 0:
            # See exec()'s own comment: a device-side traceback lands on mpremote's stdout, not
            # stderr - both are included here for the same reason.
            raise HardwareTestFailureError(f"mpremote run {script_path} failed (exit {result.returncode}):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result.stdout

    def run_isolated_expect_reset(self, script_path: str | Path, timeout_s: float | None = None) -> None:
        """Like run_isolated(), but for a script that deliberately triggers a real machine.reset()
        mid-run - the device disappearing is the expected, successful outcome, not a failure.
        Re-arms the watchdog first; caller must wait_until(is_device_present) then issue a fresh call."""
        self._mpremote("exec", "import machine; machine.WDT(timeout=8000)", "run", str(script_path), timeout_s=timeout_s)
        # Deliberately ignore the return code/output - see this method's own docstring.

    def soft_reset(self) -> None:
        result = self._mpremote("soft-reset", timeout_s=15.0)
        if result.returncode != 0:
            raise HardwareTestFailureError(f"mpremote soft-reset failed (exit {result.returncode}):\n{result.stderr}")

    def hard_reset(self) -> None:
        """The `reset` shortcut (DTR-line hardware reset, never a flash) - used for genuine
        full-boot-cycle tests (config-survives-reboot, cold-boot timing) where a soft reset
        wouldn't exercise the real boot path."""
        result = self._mpremote("reset", timeout_s=15.0)
        if result.returncode != 0:
            raise HardwareTestFailureError(f"mpremote reset failed (exit {result.returncode}):\n{result.stderr}")

    def enter_bootloader(self) -> None:
        """`machine.bootloader()` triggered remotely - drops the board into BOOTSEL mode for
        picotool to re-flash. Counts as a flash cycle if followed by a picotool write - not
        called by any routine test, only the explicit re-provisioning helper in test_toolchain_flash_boot.py."""
        # exec(), not run_isolated(): the device never comes back to answer a chained soft-reset
        # once dropped into the bootloader - a non-zero/timeout exit here is expected, not a failure.
        self._mpremote("exec", "import machine; machine.bootloader()", timeout_s=10.0)

    def tail_log(self, duration_s: float, baudrate: int = 115200) -> list[str]:
        """Passively captures what the live system prints over `duration_s`, without interrupting
        it (unlike exec()/run_isolated(), which always Ctrl-C first - see tests_hardware/README.md).
        Retries a transient post-hard_reset() USB-settle failure before raising HardwareNotAvailableError."""
        grace_deadline = time.monotonic() + 10.0
        overall_deadline = time.monotonic() + duration_s
        lines: list[str] = []
        while True:
            try:
                with serial.Serial(self.device, baudrate, timeout=0.5) as port:
                    while time.monotonic() < overall_deadline:
                        raw = port.readline()
                        if raw:
                            lines.append(raw.decode("utf-8", errors="replace").rstrip("\r\n"))
            except serial.SerialException as exc:
                if time.monotonic() >= grace_deadline:
                    raise HardwareNotAvailableError(f"could not read {self.device} for passive log tailing: {exc}") from exc
                time.sleep(0.5)
            else:
                return lines
