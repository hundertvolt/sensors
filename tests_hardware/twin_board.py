"""Board's API over the digital twin: each run renders the script as the harness renders it for silicon and runs it
under the MicroPython Unix port through digital_twin/run_device_script.py, at the GC stage the board was made with.
No retry and no recovery: a twin run that fails is the instrument's own failure (digital_twin/README.md)."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import harness
import tomllib
from harness import REPO_ROOT, HardwareNotAvailableError, HardwareTestFailureError

from buildgen.twin_wiring import compute_twin_wiring
from buildgen.validate import build_model
from scripts._twin_process import _QSTR_MAX_BYTES, EXIT_SIMULATED_BOOTLOADER, EXIT_SIMULATED_RESET, _uninternable

RUNNER = "digital_twin/run_device_script.py"
PLAN_DIR = REPO_ROOT / "build" / "twin_board"
# The interpreter and heap scripts/test.sh runs the twin with (the standard build, -X heapsize=16M).
_HEAP_SIZE = "16M"
_EXIT_WATCHDOG_STARVED = 6  # run_device_script.py's own: the script starved the watchdog silicon would have reset on
_DEFAULT_TIMEOUT_S = 60.0
_PROBE_TIMEOUT_S = 60.0  # scripts/_unix_port.sh answers from the filesystem and one interpreter start
# The twin's MICROPYPATH, from its one definition.
_TWIN_LAYOUT = tomllib.loads((REPO_ROOT / "scripts" / "micropypath.toml").read_text(encoding="utf-8"))["twin"]


def _plan(device: str) -> Path:
    # The device's twin wiring plan, as buildgen derives it for the twin's machine.configure_wiring(); one file per
    # device, rewritten whenever its content changes.
    path = PLAN_DIR / f"{device}_plan.json"
    text = json.dumps(compute_twin_wiring(build_model(harness.device_toml(device), REPO_ROOT / "src")), sort_keys=True)
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        PLAN_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return path


def _refused(done: "subprocess.CompletedProcess[str]", what: str) -> FileNotFoundError:
    return FileNotFoundError(done.stderr.strip() or f"scripts/_unix_port.sh {what} exited {done.returncode}")


def _unix_port(*args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(["/bin/bash", str(REPO_ROOT / "scripts" / "_unix_port.sh"), *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=_PROBE_TIMEOUT_S, check=False)  # argv from repo paths, no shell


class TwinBoard:
    # Board's public names and signatures (tests_scripts/test_twin_board.py pins the parity). The board's FRAM, SCD30
    # state and filesystem (each run's working directory) live in one directory per TwinBoard, kept across its runs as
    # silicon keeps them across a reset: a script's config and scratch files never land in the checkout.

    def __init__(self, default_timeout_s: float = _DEFAULT_TIMEOUT_S, *, gc_threshold: int = -1) -> None:
        self.device = harness.bench_device()  # the device render_device_script() renders for, so plan and facts agree
        self.default_timeout_s = default_timeout_s
        self.gc_threshold = gc_threshold
        self.recovery_events: list[str] = []  # stays empty: the twin retries nothing
        self._state = tempfile.TemporaryDirectory(prefix="twin_board_")
        self._last_output: list[str] = []

    def _run(self, script: Path, timeout_s: "float | None", *, expect_reset: bool) -> str:
        # A launch the interpreter would die on before the runner starts fails first; then a missing build, or one of
        # another build flavour, raises naming the probe's own fix.
        args = [str(REPO_ROOT / RUNNER), str(_plan(self.device)), str(Path(script).resolve()), "--gc-threshold", str(self.gc_threshold), "--state-dir", self._state.name]
        env = dict(os.environ, MICROPYPATH=twin_micropypath(), TZ="UTC")
        uninternable = _uninternable(args, env)
        if uninternable:
            raise HardwareTestFailureError(f"twin run of {script.name} was not started: {', '.join(uninternable)} - the Unix port interns each as a qstr of at most {_QSTR_MAX_BYTES} bytes and dies before the runner starts")
        done = _unix_port("check", "standard")
        if done.returncode != 0:
            raise _refused(done, "check standard")
        binary = Path(done.stdout.strip())
        filesystem = Path(self._state.name) / "fs"
        filesystem.mkdir(exist_ok=True)
        argv = [str(binary), "-X", f"heapsize={_HEAP_SIZE}", *args]
        timeout = timeout_s or self.default_timeout_s
        try:
            proc = subprocess.run(argv, cwd=filesystem, env=env, capture_output=True, text=True, timeout=timeout, check=False)  # argv from repo paths, no shell
        except subprocess.TimeoutExpired as exc:
            raise HardwareTestFailureError(f"twin run of {script.name} timed out after {timeout}s") from exc
        output = proc.stdout + proc.stderr
        self._last_output = output.splitlines()
        if proc.returncode == 0 or (expect_reset and proc.returncode in (EXIT_SIMULATED_RESET, EXIT_SIMULATED_BOOTLOADER)):
            return output
        what = "starved the watchdog" if proc.returncode == _EXIT_WATCHDOG_STARVED else f"failed (exit {proc.returncode})"
        raise HardwareTestFailureError(f"twin run of {script.name} at gc.threshold({self.gc_threshold}) {what}:\n{output}")

    def is_device_present(self) -> bool:
        return True

    def is_reachable(self) -> bool:
        return True

    def enter_bootloader(self) -> None:
        raise HardwareNotAvailableError("the twin has no bootloader: a reflash needs silicon")

    def exec(self, expr: str, timeout_s: "float | None" = None) -> str:
        # The expression run as a one-line script in a fresh twin process, as `mpremote exec` runs it in a fresh REPL.
        script = PLAN_DIR / "exec.py"
        PLAN_DIR.mkdir(parents=True, exist_ok=True)
        script.write_text(expr + "\n", encoding="utf-8")
        return self._run(script, timeout_s, expect_reset=False)

    def hard_reset(self) -> None:
        # Nothing runs between twin runs: every run starts a fresh process, as a reset would leave the board.
        return

    def run_isolated(self, script_path: "str | Path", *, soft_reset_after: bool = True, timeout_s: "float | None" = None, allow_recovery: bool = True, **extras: object) -> str:
        # soft_reset_after and allow_recovery have nothing to act on: the process ends with the script, and no run retries.
        del soft_reset_after, allow_recovery
        return self._run(harness.render_device_script(Path(script_path), **extras), timeout_s, expect_reset=False)

    def run_isolated_expect_reset(self, script_path: "str | Path", *, timeout_s: "float | None" = None, hold_unread_s: "float | None" = None, **extras: object) -> str:
        # The twin's machine.reset() ends the run with the runner's reset code, the output it printed returned; nothing
        # holds a console here, so hold_unread_s changes nothing but the return, "" as on silicon.
        output = self._run(harness.render_device_script(Path(script_path), **extras), timeout_s, expect_reset=True)
        return "" if hold_unread_s is not None else output

    def tail_log(self, duration_s: float, baudrate: int = 115200) -> "list[str]":
        # The last run's output, handed out once as a passive tail sees each line once; a twin board prints only while a
        # script runs, so a later tail reads nothing until the next run.
        del duration_s, baudrate
        lines, self._last_output = self._last_output, []
        return lines


def twin_micropypath() -> str:
    # The twin's one MICROPYPATH with each directory made absolute, so a run works from the board's own filesystem;
    # ".frozen" stays as it is, the interpreter's token for its frozen modules (asyncio among them), not a directory.
    return ":".join(entry if entry == ".frozen" else str(REPO_ROOT / entry) for entry in _TWIN_LAYOUT.split(":"))


def unix_port_binary() -> Path:
    # Where scripts/_unix_port.sh puts the standard build scripts/test.sh runs the twin with; it may not be built yet.
    done = _unix_port("unix_port_bin", "standard")
    if done.returncode != 0:
        raise _refused(done, "unix_port_bin standard")
    return Path(done.stdout.strip())
