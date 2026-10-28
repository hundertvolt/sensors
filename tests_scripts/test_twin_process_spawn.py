"""Tests scripts/_twin_process.py's spawn() for any runner: a string the Unix port interns before the runner starts and
cannot (an argument, the runner's directory, a MICROPYPATH entry) is refused before anything is created, naming it and
the limit, the pinned interpreter's own boundary; a caller's TEST_TWIN_HOST never reaches the twin (twin_env())."""

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts._twin_process as twin_process

_LIMIT = twin_process._QSTR_MAX_BYTES
_OVER = "x" * (_LIMIT + 1)


def _spawn(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, device: str = "fixture-device", state_dir: "Path | None" = None, args: "tuple[str, ...]" = (), micropypath: str = twin_process.TWIN_MICROPYPATH, envs: "list[object] | None" = None) -> "list[list[str]]":
    # One spawn() over a recording Popen stub: the commands it would have started (and into envs, each one's environment),
    # its log closed again.
    started: list[list[str]] = []

    def popen(cmd: "list[str]", **kw: object) -> object:
        started.append(cmd)
        if envs is not None:
            envs.append(kw["env"])
        return SimpleNamespace(pid=0)

    monkeypatch.setattr(subprocess, "Popen", popen)
    launch = twin_process.TwinLaunch("/nonexistent/micropython", "sensortask_fixture", tmp_path / "plan.json", device, "127.0.0.1", 20000, -1, micropypath)
    run = twin_process.spawn(launch, state_dir=state_dir or tmp_path / "state", log_path=tmp_path / "twin.log", args=args)
    run.log_file.close()
    return started


@pytest.mark.parametrize(
    ("where", "named"),
    [
        ("device", "--device's value (256 bytes)"),
        ("multibyte device", "--device's value (256 bytes)"),
        ("state path", "--fram-state-path's value"),
        ("caller's argument", "--fault's value (256 bytes)"),
        ("micropypath entry", "MICROPYPATH entry 1 (256 bytes)"),
        ("home-relative entry without HOME", "MICROPYPATH entry 2 (258 bytes)"),
        ("runner's directory", "the runner's directory (264 bytes)"),
    ],
)
def test_a_string_the_interpreter_cannot_intern_is_refused_before_anything_starts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, where: str, named: str) -> None:
    # Each of these kills the interpreter before the runner's first line ("FATAL: uncaught NLR", exit 1), which read as a
    # twin that "exited before ever serving"; a byte count, not characters, is what the interpreter measures.
    device, state_dir, micropypath = "fixture-device", tmp_path / "state", twin_process.TWIN_MICROPYPATH
    args: tuple[str, ...] = ()
    if where == "device":
        device = _OVER
    elif where == "multibyte device":
        device = "\u00e9" * ((_LIMIT + 1) // 2)
    elif where == "state path":
        state_dir = tmp_path / ("s" * (_LIMIT - 10))
    elif where == "caller's argument":
        args = ("--fault", _OVER)
    elif where == "micropypath entry":
        micropypath = f"{_OVER}:src"
    elif where == "home-relative entry without HOME":
        monkeypatch.delenv("HOME", raising=False)
        micropypath = f"src:~/{_OVER}"
    else:
        monkeypatch.setattr(twin_process, "REPO_ROOT", Path("/" + "r" * 250))
    with pytest.raises(ValueError, match="the twin was not started") as refused:
        _spawn(monkeypatch, tmp_path, device=device, state_dir=state_dir, args=args, micropypath=micropypath)
    assert named in str(refused.value) and f"a qstr of at most {_LIMIT} bytes" in str(refused.value), refused.value
    assert sorted(path.name for path in tmp_path.iterdir()) == [], "spawn() created state or a log before refusing"


def test_a_string_at_the_limit_or_one_the_interpreter_expands_still_starts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The boundary's other side: 255 bytes everywhere, and a ~/ entry the interpreter builds from $HOME, never interns.
    monkeypatch.setenv("HOME", "/home/fixture")
    at_limit = "x" * _LIMIT
    started = _spawn(monkeypatch, tmp_path, device=at_limit, args=("--fault", at_limit), micropypath=f"{at_limit}:~/{_OVER}:src")
    assert len(started) == 1 and started[0][started[0].index("--device") + 1] == at_limit, started


def test_a_callers_twin_host_never_reaches_the_twin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # TEST_TWIN_HOST is scripts/test.sh's address for each of its own jobs. A caller's would bind the twin's servers there,
    # off the 127.0.0.1 where spawn()'s callers (the CI suite's Run 7, the scenario harness) query its captive DNS.
    monkeypatch.setenv("TEST_TWIN_HOST", "127.0.0.77")
    envs: list[object] = []
    _spawn(monkeypatch, tmp_path, envs=envs)
    assert len(envs) == 1 and isinstance(envs[0], dict), envs
    assert "TEST_TWIN_HOST" not in envs[0], f"the caller's TEST_TWIN_HOST={envs[0]['TEST_TWIN_HOST']!r} reached the twin's environment"
    assert envs[0]["MICROPYPATH"] == twin_process.TWIN_MICROPYPATH and envs[0]["TZ"] == "UTC", envs[0]


def test_the_limit_is_the_pinned_interpreters_own(micropython_bin: Path) -> None:
    # The named limit read against the interpreter itself: an argument of that many bytes starts, one byte more kills it.
    outcomes = [subprocess.run([str(micropython_bin), "-c", "print('started')", "a" * size], capture_output=True, text=True, timeout=60, check=False) for size in (_LIMIT, _LIMIT + 1)]
    assert [(done.returncode, done.stdout.strip()) for done in outcomes] == [(0, "started"), (1, "")], outcomes
    assert "FATAL: uncaught NLR" in outcomes[1].stderr, outcomes[1].stderr


def test_the_check_names_the_directory_of_the_script_it_is_given(tmp_path: Path) -> None:
    # Any launcher's own script, not only spawn()'s runner: an absolute one taken as given, its real directory named.
    base = os.path.realpath(tmp_path)
    script = Path(base, "d" * (_LIMIT - len(os.fsencode(base))), "run.py")
    named = twin_process._uninternable([str(script), "--x", "1"], {"MICROPYPATH": "src"})
    assert named == [f"argument 0 ({len(os.fsencode(str(script)))} bytes)", f"the runner's directory ({_LIMIT + 1} bytes)"], named
