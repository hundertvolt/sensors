"""tests_hardware/harness.py's mpremote wrapper against a scripted subprocess.run: a transient failure is retried only
while nothing reached the board, a started script or a live read is never re-run, a timeout interrupts the board, a
refused USB rebind is named, every call runs `uv run --no-sync`, and every live read goes through exec_live()."""

import ast
import subprocess
import sys
import time
from pathlib import Path

import pytest
import serial

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

import harness

from buildgen.validate import _WDT_TIMEOUT_MS

_TRANSIENT = "could not enter raw repl"
# mpremote v1.29.0 when it never enters the raw REPL: stdout carries its read as one bytes repr, or nothing, and stderr
# the error, a traceback from ensure_raw_repl() or exec's CommandError (tools/mpremote/mpremote/transport_serial.py:178-210, 270-295).
_RAW_REPL_TRACEBACK = 'Traceback (most recent call last):\n  File "mpremote/transport_serial.py", line 195, in enter_raw_repl\nmpremote.transport.TransportError: could not enter raw repl\n'
_RAW_REPL_COMMAND_ERROR = "mpremote: could not enter raw repl\n"
_NEVER_ENTERED = [("b''\n", _RAW_REPL_TRACEBACK), ("b'\\r\\nMicroPython v1.29.0 on 2026-09-10; Raspberry Pi Pico W with RP2040\\r\\n'\n", _RAW_REPL_TRACEBACK), ("b'w REPL; CTRL-B to exit\\r\\n'\n", _RAW_REPL_COMMAND_ERROR), ("", _RAW_REPL_COMMAND_ERROR)]
_TESTS_HARDWARE = Path(__file__).resolve().parent.parent / "tests_hardware"
_LIVE = "sys.modules"  # a snippet naming it reads the running firmware's modules, which only exec_live() keeps


class _Scripted:
    # subprocess.run's stand-in: each mpremote call takes the next (returncode, stdout, stderr); every argv recorded.
    def __init__(self, answers: "list[tuple[int, str, str]]") -> None:
        self.answers = answers
        self.argvs: list[list[str]] = []
        self.timeouts: list[object] = []

    def __call__(self, argv: "list[str]", **kwargs: object) -> "subprocess.CompletedProcess[str]":
        self.argvs.append(list(argv))
        self.timeouts.append(kwargs.get("timeout"))
        code, out, err = self.answers.pop(0)
        return subprocess.CompletedProcess(argv, code, out, err)

    def mpremote_args(self) -> "list[list[str]]":
        return [argv[argv.index("connect") + 2 :] for argv in self.argvs if "mpremote" in argv]


def _is_live_argument(node: ast.AST, parents: "dict[ast.AST, ast.AST]") -> bool:
    call = parents.get(node)
    return isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == "exec_live" and bool(call.args) and call.args[0] is node


def _live_read_findings(root: Path) -> "tuple[list[str], list[str]]":
    # Every string under root naming sys.modules (docstrings aside), and each one reaching the board other than as
    # exec_live()'s first argument, directly or through the module-level name it is bound to.
    trees = {path: ast.parse(path.read_text(encoding="utf-8")) for path in sorted(root.rglob("*.py"))}
    parents = {path: {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)} for path, tree in trees.items()}
    snippets: list[str] = []
    findings: list[str] = []
    bound: list[tuple[str, str]] = []
    for path, tree in trees.items():
        up = parents[path]
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Constant) and isinstance(node.value, str) and _LIVE in node.value):
                continue
            holder: ast.AST = node
            while isinstance(up.get(holder), ast.JoinedStr | ast.BinOp):
                holder = up[holder]
            owner = up.get(holder)
            if isinstance(owner, ast.Expr):
                continue
            label = f"{path.relative_to(root)}:{node.lineno}"
            snippets.append(label)
            target = owner.targets[0] if isinstance(owner, ast.Assign) and len(owner.targets) == 1 else owner.target if isinstance(owner, ast.AnnAssign) else None
            if _is_live_argument(holder, up):
                continue
            if isinstance(target, ast.Name) and owner in tree.body:
                bound.append((target.id, label))
            else:
                findings.append(f"{label}: a {_LIVE} snippet reaches the board other than through exec_live()")
    for name, label in bound:
        uses = [(path, n) for path, tree in trees.items() for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load)]
        findings.extend(f"{path.relative_to(root)}:{n.lineno}: {name} ({label}) reaches the board other than through exec_live()" for path, n in uses if not _is_live_argument(n, parents[path]))
        if not uses:
            findings.append(f"{label}: {name} is never passed to exec_live()")
    return snippets, findings


def _script(tmp_path: Path) -> Path:
    path = tmp_path / "probe.py"
    path.write_text("print('probe')\n", encoding="utf-8")
    return path


@pytest.fixture
def board(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> harness.Board:
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    monkeypatch.setattr(harness, "RENDERED_SCRIPTS_DIR", tmp_path / "rendered")
    return harness.Board(device=str(tmp_path / "ttyACM-pinned"))


@pytest.mark.parametrize(("stdout", "stderr"), _NEVER_ENTERED)
def test_a_transient_failure_before_anything_ran_is_retried_once_and_recorded(board: harness.Board, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stdout: str, stderr: str) -> None:
    run = _Scripted([(1, stdout, stderr), (0, "probe\n", ""), (0, "", "")])
    monkeypatch.setattr(subprocess, "run", run)
    assert board.run_isolated(_script(tmp_path)) == "probe\n"
    assert [args[0] for args in run.mpremote_args()] == ["exec", "exec", "soft-reset"]
    assert len(board.recovery_events) == 1 and _TRANSIENT in board.recovery_events[0], board.recovery_events


@pytest.mark.parametrize(("stdout", "stderr"), [("probe\nhalf a line", _TRANSIENT), ("probe\nb'half a line'\n", _RAW_REPL_TRACEBACK), ("b'probe'\nb'half a line'\n", _RAW_REPL_TRACEBACK)])
def test_a_transient_failure_after_the_script_printed_is_never_retried(board: harness.Board, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stdout: str, stderr: str) -> None:
    # Anything on stdout beyond mpremote's one echo of its read may be the script's own: that run is never repeated.
    run = _Scripted([(1, stdout, stderr)])
    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(harness.HardwareTestFailureError, match="half a line"):
        board.run_isolated(_script(tmp_path))
    assert len(run.argvs) == 1, "the started script was run twice"


def test_a_failed_trailing_soft_reset_raises_naming_it_and_never_reruns_the_script(board: harness.Board, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run = _Scripted([(0, "probe\n", ""), (1, "", "soft reset failed")])
    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(harness.HardwareTestFailureError, match=r"script completed \(output below\) but the trailing soft-reset failed.*\n.*probe"):
        board.run_isolated(_script(tmp_path))
    assert [args[0] for args in run.mpremote_args()] == ["exec", "soft-reset"]
    assert run.mpremote_args()[0][:2] == ["exec", "import machine; machine.WDT(timeout=8000)"]


def test_every_board_call_runs_uv_without_a_sync(board: harness.Board, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run = _Scripted([(0, "probe\n", ""), (0, "", ""), (0, "", ""), (0, "mpremote-ok\n", "")])
    monkeypatch.setattr(subprocess, "run", run)
    board.run_isolated(_script(tmp_path))
    board.hard_reset()
    assert board.is_reachable()
    assert all(argv[:4] == ["uv", "run", "--no-sync", "mpremote"] for argv in run.argvs), run.argvs


def test_a_timeout_interrupts_the_board_and_resets_it_before_raising(board: harness.Board, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def run(argv: "list[str]", **kwargs: object) -> "subprocess.CompletedProcess[str]":
        calls.append(argv[-1] if argv[-1] == "reset" else "run")
        if argv[-1] == "reset":
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise subprocess.TimeoutExpired(argv, 1.0)

    class Port:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> "Port":
            return self

        def __exit__(self, *_exc: object) -> None:
            pass

        def write(self, data: bytes) -> None:
            calls.append(f"write {data!r}")

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(serial, "Serial", Port)
    with pytest.raises(harness.HardwareTestFailureError, match="timed out"):
        board.run_isolated(_script(tmp_path), timeout_s=1.0)
    assert calls == ["run", "write b'\\x03\\x03'", "reset"]
    assert len(board.recovery_events) == 1 and "Ctrl-C x2 sent" in board.recovery_events[0] and "reset exit 0" in board.recovery_events[0]


def test_a_refused_usb_rebind_is_named_with_one_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    monkeypatch.setattr(harness, "_USB_GRACE_S", 0.0)
    monkeypatch.setattr(harness, "_usb_reset_device", lambda _device: (False, "unbind refused: sudo: a password is required"))
    run = _Scripted([(1, "", _TRANSIENT)])
    monkeypatch.setattr(subprocess, "run", run)
    board = harness.Board(device=str(tmp_path / "ttyACM-pinned"))
    with pytest.raises(harness.HardwareNotAvailableError, match=r"USB rebind recovery refused by sudo.*tests_hardware/README.md prerequisites"):
        board.exec("print(1)")
    assert len(board.recovery_events) == 1 and "unbind refused" in board.recovery_events[0]


def test_the_rebind_checks_each_sudo_tee_and_polls_the_state_it_waits_for(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # The unbind's wait ends when the driver link goes, the bind's when the tty node is back; neither is a fixed sleep.
    usb = tmp_path / "usb" / "1-1.4"
    interface = usb / "1-1.4:1.0"
    interface.mkdir(parents=True)
    (usb / "driver").mkdir()
    tty = tmp_path / "class_tty" / "ttyACM0"
    tty.mkdir(parents=True)
    (tty / "device").symlink_to(interface)
    node = tmp_path / "ttyACM0"
    node.write_text("", encoding="utf-8")
    sleeps: list[float] = []
    actions: list[str] = []

    def run(argv: "list[str]", **kwargs: object) -> "subprocess.CompletedProcess[str]":
        actions.append(argv[-1].rsplit("/", 1)[1])
        if actions[-1] == "unbind":
            (usb / "driver").rmdir()
            node.unlink()
        else:
            node.write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(harness, "_SYS_CLASS_TTY", tmp_path / "class_tty")
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(time, "sleep", sleeps.append)
    assert harness._usb_reset_device(str(node)) == (True, "unbind+bind of 1-1.4")
    assert actions == ["unbind", "bind"] and sleeps == []


def test_a_settle_poll_gives_up_at_its_bound_and_says_so(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    clock = [0.0]

    def sleep(seconds: float) -> None:
        clock[0] += seconds

    monkeypatch.setattr(time, "sleep", sleep)
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    assert harness._poll(lambda: False, 2.0) is False
    assert 2.0 <= clock[0] <= 2.0 + harness._USB_GRACE_POLL_S
    assert harness._poll(lambda: True, 2.0) is True


def test_an_expect_reset_run_that_never_reached_the_board_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # A reset is the expected end, but no output and a transient failure mean the script never started: not a reset.
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    monkeypatch.setattr(harness, "_USB_GRACE_S", 0.0)
    monkeypatch.setattr(harness, "_usb_reset_device", lambda _device: (False, "no /sys/class/tty/x/device to rebind"))
    monkeypatch.setattr(harness, "RENDERED_SCRIPTS_DIR", tmp_path / "rendered")
    for stdout, stderr in _NEVER_ENTERED:
        monkeypatch.setattr(subprocess, "run", _Scripted([(1, stdout, stderr)]))
        board = harness.Board(device=str(tmp_path / "ttyACM-pinned"))
        with pytest.raises(harness.HardwareTestFailureError, match="never reached the board"):
            board.run_isolated_expect_reset(_script(tmp_path))
    monkeypatch.setattr(subprocess, "run", _Scripted([(1, "FACT seeded=true\n", "device disconnected")]))
    assert board.run_isolated_expect_reset(_script(tmp_path)) == "FACT seeded=true\n"


def test_exec_live_resumes_before_its_exec_and_a_plain_exec_does_not(board: harness.Board, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _Scripted([(0, "LIVE\n", ""), (0, "FRESH\n", "")])
    monkeypatch.setattr(subprocess, "run", run)
    assert board.exec_live("print('LIVE')") == "LIVE\n"
    assert board.exec("print('FRESH')") == "FRESH\n"
    assert run.mpremote_args() == [["resume", "exec", "print('LIVE')"], ["exec", "print('FRESH')"]]


def test_exec_live_is_bounded_by_one_watchdog_period_and_refuses_a_longer_bound(board: harness.Board, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _Scripted([(0, "", ""), (0, "", "")])
    monkeypatch.setattr(subprocess, "run", run)
    window = _WDT_TIMEOUT_MS / 1000
    board.exec_live("pass")
    board.exec_live("pass", timeout_s=window / 2)
    assert run.timeouts == [window, window / 2]
    with pytest.raises(ValueError, match="watchdog"):
        board.exec_live("pass", timeout_s=window + 1)
    assert len(run.argvs) == 2, "a bound past the watchdog period still reached the board"


def test_exec_live_never_retries_even_a_failure_that_printed_nothing(board: harness.Board, monkeypatch: pytest.MonkeyPatch) -> None:
    run = _Scripted([(1, "", "failed to access /dev/ttyACM0 (it may be in use by another program)")])
    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(harness.HardwareTestFailureError, match="may be in use"):
        board.exec_live("pass")
    assert len(run.argvs) == 1 and board.recovery_events == [], board.recovery_events


def test_every_snippet_reading_the_running_firmwares_modules_reaches_the_board_through_exec_live() -> None:
    snippets, findings = _live_read_findings(_TESTS_HARDWARE)
    assert snippets, f"no {_LIVE} snippet under {_TESTS_HARDWARE}: the scan would pass on anything"
    assert not findings, "\n".join(findings)
