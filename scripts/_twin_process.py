"""Twin-process helpers shared by the L2 suite and the host-side scenario harness: launch the twin runner as a
subprocess, wait for it, end it, read its log and its machine-read lines, and speak HTTP to it. CPython,
stdlib only; every check stays with its caller, these only report what they saw."""

import contextlib
import json
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.client import HTTPConnection, HTTPException
from pathlib import Path
from typing import IO, NamedTuple, TypeAlias

import tomllib

JSONValue: TypeAlias = bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"] | None
JSONObject: TypeAlias = dict[str, JSONValue]

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER = "digital_twin/run_generic_integration.py"
LAYOUT_FILE = REPO_ROOT / "scripts" / "micropypath.toml"
# The twin gate's copy of the four-gate marker set (CLAUDE.md), kept equal by test_memory_error_gate_agreement.py.
MEMORY_ERROR_MARKERS = ("MemoryError", "memory allocation failed")

# The runner's own exit codes (digital_twin/run_generic_integration.py), pinned equal by an L0 test.
EXIT_SIMULATED_RESET = 3
EXIT_SIMULATED_BOOTLOADER = 4
EXIT_SIMULATED_POWER_LOSS = 5
EXIT_SUITE_TIMEOUT = -256  # wait_exit()'s own give-up: no exit code or signal death can read as it
_EXIT_NAMES = {0: "a clean exit", EXIT_SIMULATED_RESET: "a simulated reset", EXIT_SIMULATED_BOOTLOADER: "a simulated bootloader entry", EXIT_SIMULATED_POWER_LOSS: "a simulated power loss", EXIT_SUITE_TIMEOUT: "no exit before the caller's deadline"}

# @tunable l2.kill_reap_timeout_s = 5.0
_KILL_REAP_TIMEOUT_S = 5.0  # the wait for a SIGKILLed twin to be reaped
# A feed gap above this share of the armed watchdog timeout is a near reset; a run that starves it on purpose skips the check.
# @tunable l2.feed_gap_share_max = 0.75
FEED_GAP_SHARE_MAX = 0.75
# @tunable l2.serving_poll_s = 0.25
_SERVING_POLL_S = 0.25
# @tunable l2.serving_probe_timeout_s = 1.0
_SERVING_PROBE_TIMEOUT_S = 1.0
_LOG_TAIL_LINES = 20


def _twin_layout() -> str:
    # The twin layout of the one MICROPYPATH definition: build/generated_src first, where every device module is generated.
    value = tomllib.loads(LAYOUT_FILE.read_text(encoding="utf-8")).get("twin")
    if isinstance(value, str):
        return value
    raise ValueError(f'{LAYOUT_FILE} has no twin = "..." layout')


TWIN_MICROPYPATH = _twin_layout()


@dataclass(frozen=True)
class TwinLaunch:
    # What every launch of one device's twin shares: the interpreter, the generated module and its plan, where it serves.
    micropython_bin: str
    module: str
    wiring_plan: Path
    device: str
    host: str
    port: int
    gc_threshold: int
    micropypath: str = TWIN_MICROPYPATH


@dataclass
class TwinRun:
    # One launched twin: its process, the log it writes and whether this module killed it.
    proc: "subprocess.Popen[str]"
    log_path: Path
    log_file: IO[str]
    device: str
    state_dir: Path
    killed: bool = False


class StatePaths(NamedTuple):
    # The four persistent-state locations a launch hands the runner, all inside one state directory.
    fram: Path
    scd30: Path
    mem_backup: Path
    config_dir: Path


class UartCounts(NamedTuple):
    # One uart_link instance's counters; the line's overruns= is asy_uart_driver.UART.rx_overruns, ring laps and
    # receive errors together, named so here.
    transfers: int
    failures: int
    rx_laps_and_errors: int


@dataclass(frozen=True)
class ShutdownLine:
    # The runner's one shutdown line, field by field, and the largest free heap block of the GC summary printed before it.
    would_have_triggered_count: int
    feed_count: int
    largest_feed_gap_ms: int
    wdt_timeout_ms: int
    mem_backup_r0: tuple[int, ...]
    public_destinations_refused: int
    flash_stall_longest_ms: int
    largest_free_block_bytes: int
    uart: dict[str, UartCounts] = field(default_factory=dict)


class ResetLine(NamedTuple):
    # The runner's "machine reset:" line, printed when a simulated reset or bootloader entry ended the run.
    kind: str
    reset_count: int
    bootloader_count: int


_SHUTDOWN_RE = re.compile(r"\] shutdown: (.*)$")
_SHUTDOWN_INTS = ("would_have_triggered_count", "feed_count", "largest_feed_gap_ms", "wdt_timeout_ms", "public_destinations_refused", "flash_stall_longest_ms", "gc_block_bytes")
_MAX_FREE_RE = re.compile(r"\bmax free sz: (\d+)\s*$")  # micropython.mem_info()'s GC summary, in heap blocks (py/gc.c)
_UART_RE = re.compile(r"^(\w+):transfers=(-?\d+),failures=(-?\d+),overruns=(-?\d+)$")
_MEM_BACKUP_WORDS = 4
_RESET_RE = re.compile(r"\] machine reset: kind=(reset|bootloader) reset_count=(\d+) bootloader_count=(\d+)\s*$")


def _close(run: TwinRun) -> None:
    if run.proc.stdin is not None and not run.proc.stdin.closed:
        with contextlib.suppress(OSError):
            run.proc.stdin.close()
    run.log_file.close()


def _int_field(fields: dict[str, str], name: str) -> int:
    if name not in fields:
        raise ValueError(f"the shutdown line carries no {name}= field")
    try:
        return int(fields[name])
    except ValueError:
        raise ValueError(f"the shutdown line's {name}={fields[name]!r} is not an integer") from None


def _proc_diagnostic_fields(pid: int) -> dict[str, str]:
    # Best-effort /proc read of a process that ignored SIGINT (its state, RSS, the kernel wait it sits in and where the
    # kernel holds SIGINT); never raises, since it only adds detail to a failure already being reported.
    fields: dict[str, str] = {}
    proc_dir = Path(f"/proc/{pid}")
    with contextlib.suppress(OSError):
        for line in (proc_dir / "status").read_text(encoding="utf-8").splitlines():
            if line.startswith(("State:", "VmRSS:", "Threads:", "SigPnd:", "ShdPnd:", "SigBlk:", "SigIgn:", "SigCgt:")):
                key, _, value = line.partition(":")
                fields[key] = value.strip()
    with contextlib.suppress(OSError):
        fields["wchan"] = (proc_dir / "wchan").read_text(encoding="utf-8").strip() or "(running)"
    with contextlib.suppress(OSError, KeyError, ValueError):
        fields["SIGINT"] = _sigint_state(fields, proc_dir)
    return fields


def _sigint_state(fields: dict[str, str], proc_dir: Path) -> str:
    # Pending (to a thread or the process), blocked in how many threads, ignored, caught: a signal the kernel still
    # holds reads apart from one it delivered to the interpreter's handler.
    bit = 1 << (signal.SIGINT - 1)
    states = [name for name, keys in (("pending", ("SigPnd", "ShdPnd")), ("ignored", ("SigIgn",)), ("caught", ("SigCgt",))) if any(int(fields[key], 16) & bit for key in keys)]
    masks = [int(line.partition(":")[2], 16) for status in sorted(proc_dir.glob("task/*/status")) for line in status.read_text(encoding="utf-8").splitlines() if line.startswith("SigBlk:")]
    states.insert(int(states[:1] == ["pending"]), f"blocked in {sum(1 for mask in masks if mask & bit)} of {len(masks)} threads")
    return ", ".join(states)


def _uart_counts(tokens: list[str]) -> dict[str, UartCounts]:
    found: dict[str, UartCounts] = {}
    for token in tokens:
        match = _UART_RE.match(token)
        if match is None:
            raise ValueError(f"the shutdown line's uart={token!r} is not <instance>:transfers=<n>,failures=<n>,overruns=<n>")
        key = match.group(1)
        if key in found:
            raise ValueError(f"the shutdown line names uart instance {key} twice")
        found[key] = UartCounts(int(match.group(2)), int(match.group(3)), int(match.group(4)))
    return found


def errcount_entry(status: int, body: JSONValue, name: str) -> JSONObject:
    # One source's entry, tolerant: {} for anything unusable, for polls that must retry through boot.
    if status != HTTPStatus.OK or not isinstance(body, dict):
        return {}
    table = body.get("errcount")
    entry = table.get(name) if isinstance(table, dict) else None
    return entry if isinstance(entry, dict) else {}


def errcount_table(status: int, body: JSONValue) -> dict[str, JSONObject]:
    # The whole errcount table of one GET /status answer, strict: an unusable answer raises.
    if status != HTTPStatus.OK or not isinstance(body, dict):
        raise RuntimeError(f"GET /status did not yield a readable body (status {status}) - no sweep over its errcount table would mean anything")
    table = body.get("errcount")
    if not isinstance(table, dict) or not table:
        raise RuntimeError(f"GET /status carried no usable errcount table ({table!r})")
    return {name: entry for name, entry in table.items() if isinstance(entry, dict)}


def exit_reason(code: int, *, killed: bool = False) -> str:
    # What an exit code says happened; a negative one is a signal death unless this module sent that signal.
    if code < 0 and code != EXIT_SUITE_TIMEOUT:
        if killed and code == -signal.SIGKILL:
            return "killed by the caller after it ignored SIGINT"
        try:
            name = signal.Signals(-code).name
        except ValueError:
            name = "unknown"
        return f"the interpreter was killed by signal {-code} ({name}) - a crash, not a failed check"
    return _EXIT_NAMES.get(code, f"exit code {code}")


def feed_gap_verdict(line: ShutdownLine) -> str | None:
    # None while the largest gap between two feeds stays within FEED_GAP_SHARE_MAX of the run's armed timeout.
    if line.largest_feed_gap_ms <= FEED_GAP_SHARE_MAX * line.wdt_timeout_ms:
        return None
    return f"the largest feed gap {line.largest_feed_gap_ms} ms is above {FEED_GAP_SHARE_MAX:.0%} of the {line.wdt_timeout_ms} ms watchdog timeout - a supervisor pass came near a reset"


def http(method: str, host: str, port: int, path: str, body: JSONValue = None, timeout_s: float = 5.0) -> tuple[int, JSONValue]:
    # The parsed JSON body, keyed off the real Content-Type: "/" serves the gzip site, which parses to None.
    conn = HTTPConnection(host, port, timeout=timeout_s)
    try:
        headers = {}
        payload = b""
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=payload, headers=headers)
        res = conn.getresponse()
        raw = res.read()
        parsed: JSONValue = json.loads(raw) if raw and "json" in res.getheader("Content-Type", "") else None
        return res.status, parsed
    finally:
        conn.close()


def log_from(log_path: Path, offset: int) -> str:
    # The log's text from a character offset on, for a check that reads only what one step produced.
    return read_log(log_path)[offset:]


def log_memory_verdict(log_path: Path) -> str | None:
    # None for a readable, non-empty log carrying neither marker; otherwise why it gives no clean verdict.
    try:
        text = log_path.read_text(errors="replace", encoding="utf-8")
    except OSError as exc:
        return f"log {log_path} missing or unreadable, no memory verdict ({exc!r})"
    if not text:
        return f"log {log_path} is empty, no memory verdict"
    for number, line in enumerate(text.splitlines(), 1):
        for marker in MEMORY_ERROR_MARKERS:
            if marker in line:
                return f"log {log_path} line {number} carries {marker!r}: {line.strip()}"
    return None


def log_tail(run: TwinRun, lines: int = _LOG_TAIL_LINES) -> str:
    return "\n".join(read_log(run.log_path).splitlines()[-lines:])


def parse_machine_reset_line(log_text: str) -> ResetLine | None:
    # The "machine reset:" line, or None when the run did not end by a simulated reset.
    for line in log_text.splitlines():
        match = _RESET_RE.search(line)
        if match is not None:
            return ResetLine(match.group(1), int(match.group(2)), int(match.group(3)))
    return None


def parse_shutdown_line(log_text: str) -> ShutdownLine | None:
    # None when no shutdown line was printed (a crash before the runner's finally); a malformed one raises.
    log_lines = log_text.splitlines()
    found = [(index, m.group(1)) for index, m in enumerate(map(_SHUTDOWN_RE.search, log_lines)) if m is not None]
    if not found:
        return None
    if len(found) > 1:
        raise ValueError(f"the log carries {len(found)} shutdown lines, the runner prints one")
    index, text = found[0]
    max_free = _MAX_FREE_RE.search(log_lines[index - 1]) if index > 0 else None
    if max_free is None:
        raise ValueError("the shutdown line follows no GC summary ending in max free sz: <blocks> - the runner prints micropython.mem_info() right before it")
    text = text.replace("mem_backup: r0=", "mem_backup_r0=")
    fields: dict[str, str] = {}
    uart_tokens: list[str] = []
    for token in text.split():
        name, sep, value = token.partition("=")
        if not sep:
            raise ValueError(f"the shutdown line's token {token!r} is not name=value")
        if name == "uart":
            uart_tokens.append(value)
        else:
            fields[name] = value
    if "mem_backup_r0" not in fields:
        raise ValueError("the shutdown line carries no mem_backup: r0= field")
    words = fields["mem_backup_r0"].split(",")
    try:
        r0 = tuple(int(word, 16) for word in words)
    except ValueError:
        raise ValueError(f"the shutdown line's mem_backup r0={fields['mem_backup_r0']!r} is not hex words") from None
    if len(r0) != _MEM_BACKUP_WORDS:
        raise ValueError(f"the shutdown line's mem_backup r0 holds {len(r0)} words, not {_MEM_BACKUP_WORDS}")
    ints = {name: _int_field(fields, name) for name in _SHUTDOWN_INTS}
    return ShutdownLine(
        would_have_triggered_count=ints["would_have_triggered_count"], feed_count=ints["feed_count"], largest_feed_gap_ms=ints["largest_feed_gap_ms"],
        wdt_timeout_ms=ints["wdt_timeout_ms"], mem_backup_r0=r0, public_destinations_refused=ints["public_destinations_refused"],
        flash_stall_longest_ms=ints["flash_stall_longest_ms"], largest_free_block_bytes=int(max_free.group(1)) * ints["gc_block_bytes"],
        uart=_uart_counts(uart_tokens),
    )


def read_log(log_path: Path) -> str:
    # "" for a log that does not exist; log_memory_verdict() is the fail-closed reader.
    try:
        return log_path.read_text(errors="replace", encoding="utf-8")
    except FileNotFoundError:
        return ""


def send_line(run: TwinRun, line: str) -> None:
    # One trigger line on the twin's stdin, read by the runner's --test-* instrumentation.
    if run.proc.stdin is None:
        raise RuntimeError(f"{run.device}'s twin has no stdin pipe to send {line!r} on")
    run.proc.stdin.write(line + "\n")
    run.proc.stdin.flush()


def shutdown(run: TwinRun, label: str, timeout_s: float = 15.0) -> int:
    # SIGINT, never SIGTERM: only the runner's KeyboardInterrupt path flushes its persisted state. A twin
    # that ignores it is described (/proc fields, log tail), then killed, and run.killed says so.
    if run.proc.poll() is None:
        run.proc.send_signal(signal.SIGINT)
        start = time.monotonic()
        try:
            run.proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            print(f"DIAG: {label}: SIGINT ignored for {elapsed:.1f}s (timeout={timeout_s}s), about to SIGKILL pid={run.proc.pid} - /proc fields: {_proc_diagnostic_fields(run.proc.pid) or '(unavailable)'}")
            print(f"DIAG: {label}: last {_LOG_TAIL_LINES} log lines before SIGKILL:\n{log_tail(run)}")
            run.proc.kill()
            run.killed = True
            run.proc.wait(timeout=_KILL_REAP_TIMEOUT_S)
    _close(run)
    return run.proc.returncode if run.proc.returncode is not None else EXIT_SUITE_TIMEOUT


def spawn(launch: TwinLaunch, *, state_dir: Path, log_path: Path, args: "tuple[str, ...] | list[str]" = ()) -> TwinRun:
    # Every state path goes inside state_dir, so a launch never writes the manual run's defaults in digital_twin/.
    paths = state_paths(state_dir)
    paths.config_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, MICROPYPATH=launch.micropypath, TZ="UTC")
    cmd = [
        launch.micropython_bin, RUNNER, "--module", launch.module, "--wiring-plan", str(launch.wiring_plan), "--device", launch.device,
        "--host", launch.host, "--port", str(launch.port), "--fram-state-path", str(paths.fram), "--scd30-state-path", str(paths.scd30),
        "--mem-backup-state-path", str(paths.mem_backup), "--config-dir", str(paths.config_dir) + "/", "--gc-threshold", str(launch.gc_threshold), *args,
    ]
    print(f"== Launching: {' '.join(cmd)} (log: {log_path})")
    log_file = log_path.open("w", encoding="utf-8")  # closed by shutdown()/wait_exit(), which end the process first
    proc = subprocess.Popen(cmd, cwd=REPO_ROOT, env=env, stdin=subprocess.PIPE, stdout=log_file, stderr=subprocess.STDOUT, text=True)
    return TwinRun(proc=proc, log_path=log_path, log_file=log_file, device=launch.device, state_dir=state_dir)


def state_paths(state_dir: Path) -> StatePaths:
    return StatePaths(state_dir / "fram_state.json", state_dir / "scd30_state.json", state_dir / "mem_backup_state.json", state_dir / "config")


def wait_exit(run: TwinRun, timeout_s: float) -> int:
    # For a run that ends by itself (--duration, a reset): EXIT_SUITE_TIMEOUT once the deadline passes.
    try:
        code = run.proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        run.proc.kill()
        run.killed = True
        run.proc.wait(timeout=_KILL_REAP_TIMEOUT_S)
        code = EXIT_SUITE_TIMEOUT
    _close(run)
    return code


def wait_until_serving(run: TwinRun, host: str, port: int, timeout_s: float = 20.0) -> None:
    # Polls GET / until it answers 200; a twin that exits first raises with its exit reason.
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        code = run.proc.poll()
        if code is not None:
            raise RuntimeError(f"the twin exited before ever serving: {exit_reason(code)} (exit code {code})")
        with contextlib.suppress(OSError, HTTPException):
            status, _ = http("GET", host, port, "/", timeout_s=_SERVING_PROBE_TIMEOUT_S)
            if status == HTTPStatus.OK:
                return
        time.sleep(_SERVING_POLL_S)
    raise TimeoutError(f"the twin never started serving on {host}:{port} within {timeout_s}s")
