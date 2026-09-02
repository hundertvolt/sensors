"""Host-side (CPython) harness primitives for the flash/bench real-hardware test tier.

Runs under `uv run pytest tests_hardware` on the *host*, driving a real board over `mpremote`
(mirroring scripts/mpremote_connect.sh's own `uv run mpremote connect <device>` invocation) and,
for bench, real `nmcli`/`iw` calls against the bridge host - never under the MicroPython Unix port
(unlike tests/, see SPECIFICATION.md Part E.1). See HARDWARE_TEST_PLAN.md §4/§6 for the design this
implements and tests_hardware/README.md for how to actually run this tier.
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
    """Unbind then rebind `device`'s underlying USB device from the kernel's generic `usb` driver -
    the same effect a physical unplug/replug would have, without needing physical access. Resolves
    the real USB bus-port ID (e.g. "1-1.4") from `/sys/class/tty/<name>/device`'s own symlink
    target, rather than hardcoding one - this must work on whatever port the board is actually
    plugged into, not just this bench's own current wiring. Returns True if the reset was actually
    attempted (the caller should retry after a settle delay), False if the device path couldn't be
    resolved (e.g. `device` doesn't exist at all - a real HardwareNotAvailable case the caller's own
    subsequent mpremote attempt will surface properly).

    Confirmed directly, real hardware: this specific bench's USB connection to the board has, more
    than once, wedged into a state where raw-REPL entry fails indefinitely (not just for the usual
    few-hundred-ms settle window) until the USB device is unbound/rebound this way - physically
    unplugging and replugging the cable has the exact same recovering effect, this just does it in
    software. Needs root (writing to `/sys/bus/usb/drivers/usb/{unbind,bind}`), consistent with
    every other real-hardware-control call in this tier already requiring `sudo`."""
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
    """Raised when a real board/bench isn't reachable. Tests catch this via the pytest fixtures in
    conftest.py (which turn it into a skip, not a failure) - this tier is meant to be collected and
    read even when no hardware is attached (e.g. in the dedicated session's first review pass
    before the physical rig exists), never to error out at collection time."""


class HardwareTestFailure(AssertionError):
    """Raised for a genuine real-hardware assertion failure - deliberately a plain AssertionError
    subclass so pytest reports it like any other failed assertion, not a framework-level error."""


def wait_until(
    check_fn: Callable[[], bool],
    timeout_s: float,
    poll_interval_s: float = 1.0,
    description: str = "condition",
) -> bool:
    """Bounded poll-until-condition wait, test-harness-only - see HARDWARE_TEST_PLAN.md §11.3 for
    why this exists and why it must never be answered by changing src/'s own real timing instead
    (SPECIFICATION.md Part F.3's "don't stall timing-sensitive work" principle - real product
    behavior with its own reasons, not something a test's convenience should edit).

    Polls `check_fn()` every `poll_interval_s` until it returns truthy or `timeout_s` elapses. A
    `check_fn` that raises (e.g. a real HTTP fetch against a device mid-reconnect) is treated as
    "not yet ready" and retried, not a fatal error - only the *final* timeout is fatal, and it
    raises TimeoutError naming what was being waited for and how long was allowed, never a bare
    `assert wait_until(...)` with no context. Always returns True or raises - it never returns
    False, so a caller never needs to re-wrap the result in its own assert."""
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
    """Wraps `uv run mpremote connect <device> ...` - the one generic isolated-driver mechanism
    HARDWARE_TEST_PLAN.md §4 calls for ("run this snippet against real hardware, capture its
    printed result"), implemented once so individual test files never shell out to mpremote
    themselves. Also the one place `machine.bootloader()`-driven re-flash and hard-reset live, for
    the toolchain/boot tests in tests_hardware/flash/test_toolchain_flash_boot.py."""

    def __init__(self, device: str | None = None, default_timeout_s: float = 60.0) -> None:
        self.device = device or os.environ.get("MPREMOTE_DEVICE", "/dev/ttyACM0")
        self.default_timeout_s = default_timeout_s

    def _mpremote(self, *args: str, timeout_s: float | None = None, allow_recovery: bool = True) -> MpremoteResult:
        """REAL FINDING: right after any mpremote subprocess exits (most commonly a `reset`), the
        very next `uv run mpremote connect <device> ...` call can transiently fail to establish a
        fresh connection - a genuine OS/USB-level race (the just-exited process's own file
        descriptor/tty claim, or the device's own raw-REPL state, hasn't fully settled yet), not a
        real "someone else has the port open" condition or a real device-side problem. Confirmed
        directly, repeatedly, on real hardware, in at least two different observed shapes: "failed
        to access <device> (it may be in use by another program)" and "could not enter raw repl" -
        both purely connection-establishment failures, distinct from a real error surfaced *after*
        a connection was actually established (e.g. a real Python traceback from a bad script,
        which must still be reported immediately, not masked by retrying). This is the same class
        of transient USB-settle race tail_log() already retries around for its own "device reports
        readiness to read but returned no data" symptom. Retried here, at the lowest common layer
        every public method goes through, rather than duplicated per caller - matched by phrase
        rather than blanket-retrying every nonzero exit, specifically so a genuine on-device
        failure still surfaces on the first attempt.

        REAL FINDING, `allow_recovery=False` added: the retry/USB-reset recovery below cannot
        distinguish "a flaky USB glitch, not a real device state" from "the device is genuinely,
        expectedly unreachable right now" - a real reboot's own multi-second USB re-enumeration
        window produces the *exact same* transient-marker error text a flaky glitch would.
        Confirmed directly: `is_reachable()` used inside a `wait_until(lambda: not board.
        is_reachable(), ...)` poll (waiting to *observe* a real reboot actually happening) was
        having its own genuine, expected unreachable window fully absorbed by this recovery logic
        before ever surfacing as a `False` return, making the poll never see the disconnect at all
        within its own timeout. `is_reachable()` below passes `allow_recovery=False` for exactly
        this reason - it must report the *honest, current* connection state immediately, never
        retrying past a real transient failure, so both `True`- and `False`-polling callers get a
        result they can actually trust."""
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
            # REAL FINDING: the plain 10s settle-wait grace window above is sometimes not enough -
            # confirmed directly, repeatedly, on real hardware: this specific USB device can wedge
            # into a state where raw-REPL entry keeps failing indefinitely, not just transiently,
            # until the USB device is actually unbound and rebound from its kernel driver (the same
            # effect physically unplugging/replugging the cable would have). One such escalation is
            # attempted here, once, before finally giving up - confirmed to reliably clear this
            # exact symptom in-session. Never attempted more than once per _mpremote() call (a
            # second failure after this means something more is genuinely wrong, not just a slow
            # USB settle).
            if not usb_reset_attempted:
                usb_reset_attempted = True
                if _usb_reset_device(self.device):
                    grace_deadline = time.monotonic() + 10.0
                    continue
            return MpremoteResult(proc.returncode, proc.stdout, proc.stderr)

    def is_reachable(self) -> bool:
        # allow_recovery=False - see _mpremote()'s own docstring for why: this method's whole
        # contract is reporting the honest, current connection state, including a real transient
        # "no" a caller is deliberately polling to observe (e.g. waiting for a real reboot to
        # actually happen) - it must never retry past that.
        try:
            result = self._mpremote("exec", "print('mpremote-ok')", timeout_s=10.0, allow_recovery=False)
        except (HardwareNotAvailable, HardwareTestFailure):
            return False
        return result.returncode == 0 and "mpremote-ok" in result.stdout

    def exec(self, expr: str, timeout_s: float | None = None) -> str:
        """`mpremote exec "<expr>"` - like run_isolated(), this ALWAYS interrupts whatever's
        currently running first (confirmed directly against mpremote's own source, see
        tail_log()'s docstring for the full finding) before evaluating `expr` in a fresh raw-REPL
        session. Never use this to observe a live, auto-booted system without disturbing it - use
        tail_log() for that instead. This method is for the isolated-driver-mode cases that want a
        single expression rather than a whole script file (run_isolated()'s job)."""
        result = self._mpremote("exec", expr, timeout_s=timeout_s)
        if result.returncode != 0:
            # Include both streams: a real device-side traceback from a raw-REPL script prints
            # over the same muxed serial channel mpremote surfaces as its own stdout, not stderr -
            # an earlier version of this method only included stderr and silently dropped the one
            # piece of output that actually explains a real failure (confirmed directly: several
            # early real-hardware runs showed "failed (exit 1):" with nothing after it).
            raise HardwareTestFailure(f"mpremote exec {expr!r} failed (exit {result.returncode}):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result.stdout

    def run_isolated(self, script_path: str | Path, *, soft_reset_after: bool = True, timeout_s: float | None = None) -> str:
        """Isolated-driver mode (HARDWARE_TEST_PLAN.md §6.2): `mpremote run <script>` interrupts
        the auto-started system into the raw REPL and runs `script_path`, which imports the real
        frozen `src/` driver modules directly.

        Load-bearing mechanism, confirmed against real mpremote 1.29.0 source
        (mpremote/main.py's `State._auto_soft_reset = True` by default, mpremote/
        transport_serial.py's `enter_raw_repl(soft_reset=True)`), not assumed: since each call
        here is a brand-new `uv run mpremote` subprocess, raw-REPL entry ALWAYS performs an
        implicit soft reset (Ctrl-D) on its way in, regardless of `soft_reset_after` - there is no
        way to run an isolated-driver script against the *exact* still-warm state the live system
        was in at the moment of interrupt; every isolated-driver call starts from a freshly
        soft-reset interpreter. `soft_reset_after` instead controls a *second*, trailing
        `soft-reset` chained as this same invocation's next_command: without it, the board is left
        sitting at the raw-REPL prompt once this call returns; with it (the default), the
        connection returns to an idle **friendly**-REPL prompt instead. Soft resets are
        free/unlimited either way - only flashing is capped.

        RESOLVED against real hardware (bench Pi4 session, see REAL_HARDWARE_RUN_LOG.md's Phase 2
        "Fifth, foundational real finding" and tests_hardware/conftest.py's own `dut_ip` fixture
        docstring): a trailing `soft-reset` does **not** hand the board back to its normal
        auto-booted state, and does **not** re-execute `modules/_boot.py`/`boot.py`/`main.py`.
        Confirmed against the pinned MicroPython C source (`ports/rp2/main.c`): entering raw REPL
        sets `pyexec_mode_kind` to `RAW_REPL`; the soft-reset boot path only re-runs `main.py`
        when that's `FRIENDLY_REPL`. A trailing soft-reset returns to an idle friendly-REPL
        *prompt* only - it does not retroactively make the already-completed soft-reset's own boot
        sequence re-check that condition, so `main.py` stays stopped regardless of
        `soft_reset_after`. Confirmed empirically too (an A/B test: bare `exec`, `exec ...
        soft-reset`, and `run <script> soft-reset` all left the board completely silent
        afterward - no `main.py` output at all). **Only a genuine `hard_reset()` resumes the live
        system** - `run_isolated()`/`exec()` must never be used when a caller needs `main.py` to
        keep running afterward (`dut_ip` used to get this wrong; see its own docstring for the
        fix). Tests that need to observe the *real* boot sequence
        (tests_hardware/flash/test_reboot_persistence.py's boot-import check) correctly use
        `hard_reset()` + `tail_log()` instead of this method, for exactly this reason."""
        args = ["run", str(script_path)]
        if soft_reset_after:
            args.append("soft-reset")
        result = self._mpremote(*args, timeout_s=timeout_s)
        if result.returncode != 0:
            # See exec()'s own comment: a device-side traceback lands on mpremote's stdout, not
            # stderr - both are included here for the same reason.
            raise HardwareTestFailure(f"mpremote run {script_path} failed (exit {result.returncode}):\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result.stdout

    def soft_reset(self) -> None:
        result = self._mpremote("soft-reset", timeout_s=15.0)
        if result.returncode != 0:
            raise HardwareTestFailure(f"mpremote soft-reset failed (exit {result.returncode}):\n{result.stderr}")

    def hard_reset(self) -> None:
        """The `reset` shortcut (DTR-line hardware reset, never a flash) - used for genuine
        full-boot-cycle tests (Part 1 item 13's config.json-survives-a-reboot check, item 22's
        cold-boot timing) where a soft reset wouldn't exercise the real boot path."""
        result = self._mpremote("reset", timeout_s=15.0)
        if result.returncode != 0:
            raise HardwareTestFailure(f"mpremote reset failed (exit {result.returncode}):\n{result.stderr}")

    def enter_bootloader(self) -> None:
        """`machine.bootloader()` triggered remotely - drops an already-running board into BOOTSEL
        mode for picotool to then re-flash (HARDWARE_TEST_PLAN.md §6.1's "every subsequent
        flash-equivalent" path). Counts as a flash cycle if actually followed by a picotool write -
        deliberately not called by any routine test, only the explicit re-provisioning helper in
        tests_hardware/flash/test_toolchain_flash_boot.py."""
        # exec(), not run_isolated(): the device deliberately never comes back to answer a
        # soft-reset chained onto the same invocation once it's dropped into the USB mass-storage
        # bootloader - a non-zero/timeout exit here is the *expected* shape of a successful call,
        # not a failure, so this bypasses exec()'s own raise-on-nonzero behavior.
        self._mpremote("exec", "import machine; machine.bootloader()", timeout_s=10.0)

    def tail_log(self, duration_s: float, baudrate: int = 115200) -> list[str]:
        """Passively captures whatever the live, auto-booted system prints on its own (real
        print_log output, WDT/reboot lines, ...) over `duration_s` seconds, WITHOUT interrupting
        it - genuine "live-system mode" observation (HARDWARE_TEST_PLAN.md §6.2), as opposed to
        `exec()`/`run_isolated()`.

        Load-bearing finding, confirmed directly against the real mpremote 1.29.0 source
        (mpremote/transport_serial.py's `enter_raw_repl()`), not assumed: `mpremote exec`/`run`
        BOTH unconditionally write `\\r\\x03` (Ctrl-C, "interrupt any running program") before
        doing anything else, regardless of `mpremote resume` or any soft-reset flag - `resume`
        only skips the *following* Ctrl-D soft-reset, not this initial interrupt. So neither
        exec() nor run_isolated() can ever be used for passive live-system observation; this
        method instead opens the serial port directly via pyserial (already an mpremote
        dependency), the same way `mpremote repl`'s own "friendly REPL" attaches - reading
        whatever the device is already writing, entering no REPL mode and sending nothing.

        A real `hard_reset()` (or a genuine power-on) makes the RP2040 re-enumerate its own USB
        CDC-ACM device, which the host can take up to a couple of seconds to settle -
        `mpremote reset` itself returns as soon as it has issued the DTR pulse, without waiting for
        that re-enumeration to finish, so opening (or even an early read on an already-open) the
        port can transiently fail with "device reports readiness to read but returned no data" even
        though the board is fine. Confirmed directly on real hardware, and confirmed the transient
        window isn't limited to the initial open() call alone: an open can succeed against a
        not-yet-fully-settled device node and then the very first readline() hits the same error.
        Both the open and any read are therefore retried (reopening each time, since a failed read
        can leave the port in a bad state) within a bounded grace window from when this method was
        first called; a failure still happening once that grace window has elapsed is a real
        HardwareNotAvailable, same as before - this tier's own "the board should already be up and
        stable before observation starts" boundary, not something to paper over indefinitely."""
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
