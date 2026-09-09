"""Host-side (CPython) harness primitives for the flash/bench real-hardware test tier. Drives a
real board over `mpremote` and, for bench, real `nmcli`/`iw` calls against the bridge host - never
under the MicroPython Unix port. See tests_hardware/README.md for how to run this tier.
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import serial

REPO_ROOT = Path(__file__).resolve().parent.parent

# Same NetworkManager connection names toolchain/setup_toolchain.py's ensure_bench_bridge() uses -
# kept in exact sync with that module rather than re-derived, since a bench rig set up by `env
# --tier bench` is what every bench test assumes is already there.
BENCH_BRIDGE_CONN = "br0"
BENCH_ETH_CONN = "br0-eth0"
BENCH_AP_CONN = "br0-wifi-ap"


def _usb_reset_device(device: str) -> bool:
    """Unbind/rebind `device`'s USB device from the kernel `usb` driver - same effect as a
    physical unplug/replug, recovering a wedged raw-REPL-entry state seen on this bench (see
    tests_hardware/README.md). Returns True if a reset was attempted (caller should retry after a
    settle delay), False if the device path couldn't be resolved. Needs root."""
    name = Path(device).name  # e.g. "ttyACM0"
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
        subprocess.run(["sudo", "tee", "/sys/bus/usb/drivers/usb/unbind"], input=usb_id, capture_output=True, text=True, timeout=10.0)
        time.sleep(2.0)
        subprocess.run(["sudo", "tee", "/sys/bus/usb/drivers/usb/bind"], input=usb_id, capture_output=True, text=True, timeout=10.0)
        time.sleep(3.0)
    except (subprocess.TimeoutExpired, OSError):
        return False
    return True


class HardwareNotAvailable(RuntimeError):
    """Raised when a real board/bench isn't reachable. conftest.py's fixtures turn this into a
    skip, not a failure, so this tier stays collectible with nothing attached."""


class HardwareTestFailure(AssertionError):
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
        except Exception as exc:  # noqa: BLE001 - a probe against real hardware/network can raise transiently; only the final timeout below is fatal
            last_exc = exc
        time.sleep(poll_interval_s)
    try:
        if check_fn():
            return True
    except Exception as exc:  # noqa: BLE001 - same as above, one last attempt right at the deadline
        last_exc = exc
    detail = f" (last error: {last_exc!r})" if last_exc is not None else ""
    raise TimeoutError(f"timed out after {timeout_s}s waiting for: {description}{detail}")


@dataclass
class MpremoteResult:
    returncode: int
    stdout: str
    stderr: str


class Board:
    """Wraps `uv run mpremote connect <device> ...`, the one generic isolated-driver mechanism,
    so individual test files never shell out to mpremote themselves. Also where
    `machine.bootloader()` re-flash and hard-reset live, for tests_hardware/flash/test_toolchain_flash_boot.py."""

    def __init__(self, device: str | None = None, default_timeout_s: float = 60.0) -> None:
        self.device = device or os.environ.get("MPREMOTE_DEVICE", "/dev/ttyACM0")
        self.default_timeout_s = default_timeout_s

    def _mpremote(self, *args: str, timeout_s: float | None = None, allow_recovery: bool = True) -> MpremoteResult:
        """Runs one `uv run mpremote connect <device> ...` call, retrying past known transient
        USB-settle-race connection failures right after a prior mpremote subprocess exits (see
        tests_hardware/README.md). `allow_recovery=False` (is_reachable()'s own use) skips the
        retry, so polling for a real, expected disconnect gets the honest state, not a masked one."""
        cmd = ["uv", "run", "mpremote", "connect", self.device, *args]
        transient_markers = ("may be in use by another program", "could not enter raw repl", "could not open")
        grace_deadline = time.monotonic() + 10.0
        usb_reset_attempted = False
        while True:
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=REPO_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=timeout_s or self.default_timeout_s,
                )
            except FileNotFoundError as exc:
                raise HardwareNotAvailable(f"uv/mpremote not on PATH: {exc}") from exc
            except subprocess.TimeoutExpired as exc:
                raise HardwareTestFailure(f"mpremote {' '.join(args)} timed out after {timeout_s or self.default_timeout_s}s") from exc
            transient = proc.returncode != 0 and any(marker in proc.stderr.lower() for marker in transient_markers)
            if not transient or not allow_recovery:
                return MpremoteResult(proc.returncode, proc.stdout, proc.stderr)
            if time.monotonic() < grace_deadline:
                time.sleep(0.5)
                continue
            # The 10s settle-wait grace window above is sometimes not enough - this bench's USB
            # device can wedge into indefinite raw-REPL-entry failure until unbound/rebound (see
            # tests_hardware/README.md). Escalate once, never more than once per call.
            if not usb_reset_attempted:
                usb_reset_attempted = True
                if _usb_reset_device(self.device):
                    grace_deadline = time.monotonic() + 10.0
                    continue
            return MpremoteResult(proc.returncode, proc.stdout, proc.stderr)

    def is_reachable(self) -> bool:
        # allow_recovery=False: report the honest, current state - a caller may be deliberately
        # polling for an expected "no" (e.g. waiting to observe a real reboot). This method always
        # Ctrl-C's/soft-resets the device on raw-REPL entry, so never poll it against a live,
        # already-running system - use is_device_present() instead (see README for the finding).
        try:
            result = self._mpremote("exec", "print('mpremote-ok')", timeout_s=10.0, allow_recovery=False)
        except (HardwareNotAvailable, HardwareTestFailure):
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
            raise HardwareTestFailure(f"mpremote exec {expr!r} failed (exit {result.returncode}):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result.stdout

    def run_isolated(self, script_path: str | Path, *, soft_reset_after: bool = True, timeout_s: float | None = None) -> str:
        """Isolated-driver mode: `mpremote run <script>` interrupts the auto-started system into
        raw REPL to run `script_path` against real frozen `src/` drivers - always soft-resets on
        entry and re-arms the watchdog first; never leaves `main.py` running (see
        tests_hardware/README.md for the full findings this is built on)."""
        args = ["exec", "import machine; machine.WDT(timeout=8000)", "run", str(script_path)]
        if soft_reset_after:
            args.append("soft-reset")
        result = self._mpremote(*args, timeout_s=timeout_s)
        if result.returncode != 0:
            # See exec()'s own comment: a device-side traceback lands on mpremote's stdout, not
            # stderr - both are included here for the same reason.
            raise HardwareTestFailure(f"mpremote run {script_path} failed (exit {result.returncode}):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
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
            raise HardwareTestFailure(f"mpremote soft-reset failed (exit {result.returncode}):\n{result.stderr}")

    def hard_reset(self) -> None:
        """The `reset` shortcut (DTR-line hardware reset, never a flash) - used for genuine
        full-boot-cycle tests (config-survives-reboot, cold-boot timing) where a soft reset
        wouldn't exercise the real boot path."""
        result = self._mpremote("reset", timeout_s=15.0)
        if result.returncode != 0:
            raise HardwareTestFailure(f"mpremote reset failed (exit {result.returncode}):\n{result.stderr}")

    def enter_bootloader(self) -> None:
        """`machine.bootloader()` triggered remotely - drops the board into BOOTSEL mode for
        picotool to re-flash. Counts as a flash cycle if followed by a picotool write - not
        called by any routine test, only the explicit re-provisioning helper in test_toolchain_flash_boot.py."""
        # exec(), not run_isolated(): the device never comes back to answer a chained soft-reset
        # once dropped into the bootloader - a non-zero/timeout exit here is expected, not a failure.
        self._mpremote("exec", "import machine; machine.bootloader()", timeout_s=10.0)

    def tail_log(self, duration_s: float, baudrate: int = 115200) -> list[str]:
        """Passively captures whatever the live, auto-booted system prints over `duration_s`
        seconds without interrupting it - unlike exec()/run_isolated() (see tests_hardware/README.md
        for why those always Ctrl-C first). Retries a transient post-hard_reset() USB-settle
        read/open failure within a bounded grace window before raising HardwareNotAvailable."""
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
                return lines
            except serial.SerialException as exc:
                if time.monotonic() >= grace_deadline:
                    raise HardwareNotAvailable(f"could not read {self.device} for passive log tailing: {exc}") from exc
                time.sleep(0.5)
        return lines
