"""Tests scripts/_twin_process.py's spawn() for any runner: a caller's TEST_TWIN_HOST never reaches the twin (twin_env()),
and the pinned interpreter interns a launch string longer than any path (its qstr length width, F.7 row 32)."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts._twin_process as twin_process

# Past PATH_MAX (4096 on Linux): no launch string can be longer, where one length byte allowed 255.
_LONG = 4097


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


def test_a_callers_twin_host_never_reaches_the_twin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # TEST_TWIN_HOST is scripts/test.sh's address for each of its own jobs. A caller's would bind the twin's servers there,
    # off the 127.0.0.1 where spawn()'s callers (the CI suite's Run 7, the scenario harness) query its captive DNS.
    monkeypatch.setenv("TEST_TWIN_HOST", "127.0.0.77")
    envs: list[object] = []
    _spawn(monkeypatch, tmp_path, envs=envs)
    assert len(envs) == 1 and isinstance(envs[0], dict), envs
    assert "TEST_TWIN_HOST" not in envs[0], f"the caller's TEST_TWIN_HOST={envs[0]['TEST_TWIN_HOST']!r} reached the twin's environment"
    assert envs[0]["MICROPYPATH"] == twin_process.TWIN_MICROPYPATH and envs[0]["TZ"] == "UTC", envs[0]


def test_the_pinned_interpreter_starts_with_a_launch_string_longer_than_any_path(micropython_bin: Path) -> None:
    # Every argument from the script on is interned at start; one length byte killed the port past 255 ("FATAL: uncaught NLR").
    done = subprocess.run([str(micropython_bin), "-c", "print('started')", "a" * _LONG], capture_output=True, text=True, timeout=60, check=False)
    assert (done.returncode, done.stdout.strip()) == (0, "started"), done
