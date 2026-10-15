"""tests_hardware/harness.py's mpremote wrapper against a scripted subprocess.run: a transient failure is retried only
while nothing reached the board, a started script is never re-run, a failed trailing soft reset never re-runs it,
a timeout interrupts the board, a refused USB rebind is named, and every board call runs `uv run --no-sync`."""

import subprocess
import sys
import time
from pathlib import Path

import pytest
import serial

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

import harness

_TRANSIENT = "could not enter raw repl"


class _Scripted:
    # subprocess.run's stand-in: each mpremote call takes the next (returncode, stdout, stderr); every argv recorded.
    def __init__(self, answers: "list[tuple[int, str, str]]") -> None:
        self.answers = answers
        self.argvs: list[list[str]] = []

    def __call__(self, argv: "list[str]", **kwargs: object) -> "subprocess.CompletedProcess[str]":
        self.argvs.append(list(argv))
        code, out, err = self.answers.pop(0)
        return subprocess.CompletedProcess(argv, code, out, err)

    def mpremote_args(self) -> "list[list[str]]":
        return [argv[argv.index("connect") + 2 :] for argv in self.argvs if "mpremote" in argv]


def _script(tmp_path: Path) -> Path:
    path = tmp_path / "probe.py"
    path.write_text("print('probe')\n", encoding="utf-8")
    return path


@pytest.fixture
def board(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> harness.Board:
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    monkeypatch.setattr(harness, "RENDERED_SCRIPTS_DIR", tmp_path / "rendered")
    return harness.Board(device=str(tmp_path / "ttyACM-pinned"))


def test_a_transient_failure_before_anything_ran_is_retried_once_and_recorded(board: harness.Board, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run = _Scripted([(1, "", _TRANSIENT), (0, "probe\n", ""), (0, "", "")])
    monkeypatch.setattr(subprocess, "run", run)
    assert board.run_isolated(_script(tmp_path)) == "probe\n"
    assert [args[0] for args in run.mpremote_args()] == ["exec", "exec", "soft-reset"]
    assert len(board.recovery_events) == 1 and _TRANSIENT in board.recovery_events[0], board.recovery_events


def test_a_transient_failure_after_the_script_printed_is_never_retried(board: harness.Board, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run = _Scripted([(1, "probe\nhalf a line", _TRANSIENT)])
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
    monkeypatch.setattr(subprocess, "run", _Scripted([(1, "", _TRANSIENT)]))
    board = harness.Board(device=str(tmp_path / "ttyACM-pinned"))
    with pytest.raises(harness.HardwareTestFailureError, match="never reached the board"):
        board.run_isolated_expect_reset(_script(tmp_path))
    monkeypatch.setattr(subprocess, "run", _Scripted([(1, "FACT seeded=true\n", "device disconnected")]))
    assert board.run_isolated_expect_reset(_script(tmp_path)) == "FACT seeded=true\n"
