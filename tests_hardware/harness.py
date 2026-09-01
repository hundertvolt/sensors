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

    def _mpremote(self, *args: str, timeout_s: float | None = None) -> MpremoteResult:
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
        failure still surfaces on the first attempt."""
        cmd = ["uv", "run", "mpremote", "connect", self.device, *args]
        transient_markers = ("may be in use by another program", "could not enter raw repl", "could not open")
        grace_deadline = time.monotonic() + 10.0
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
            if transient and time.monotonic() < grace_deadline:
                time.sleep(0.5)
                continue
            return MpremoteResult(proc.returncode, proc.stdout, proc.stderr)

    def is_reachable(self) -> bool:
        try:
            result = self._mpremote("exec", "print('mpremote-ok')", timeout_s=10.0)
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
        sitting at the raw-REPL prompt (not auto-running main.py) once this call returns; with it
        (the default), the board is handed back to its normal auto-booted state before the next
        test. Soft resets are free/unlimited either way - only flashing is capped.

        NEEDS VERIFICATION ON FIRST REAL RUN: whether the *implicit* entry soft-reset above
        re-executes `modules/_boot.py`/`boot.py`/`main.py` the way a genuine power-on or
        `hard_reset()` does, or whether raw-REPL mode suppresses that normal auto-run sequence
        (the conventional mpremote/rshell/ampy assumption, but not independently confirmed against
        this project's own pinned MicroPython source as of this writing). Tests that need to
        observe the *real* boot sequence (tests_hardware/flash/test_reboot_persistence.py's boot-
        import check) deliberately use `hard_reset()` + `tail_log()` instead of this method, to
        sidestep the question rather than depend on an unverified answer to it."""
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
