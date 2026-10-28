"""tests_scripts/conftest.py fails a test that reaches pytest.exit() instead of letting it end the session: without the
guard, every later test goes unrun with one trailing line to show it (a bench conftest under test did exactly that,
cutting 314 tests off a whole-tier run)."""

import os
import subprocess
import sys
from pathlib import Path

_PROBE = """import pytest


def test_a_reaches_exit():
    pytest.exit("probe exit")


def test_b_runs_after_it():
    assert True
"""
# Loads the real conftest's three runtest wrappers as a plugin, so the probe runs against them and nothing else.
_PLUGIN = """import os
from pathlib import Path

from _script_loader import load_script_module

_module = load_script_module(Path(os.environ["GUARD_CONFTEST"]), "tests_scripts_conftest_under_test")
pytest_runtest_setup = _module.pytest_runtest_setup
pytest_runtest_call = _module.pytest_runtest_call
pytest_runtest_teardown = _module.pytest_runtest_teardown
"""
# @tunable l0.session_exit_guard_timeout_s = 60
_RUN_TIMEOUT_S = 60


def _pytest(tmp_path: Path, repo_root: Path, *plugin: str) -> "subprocess.CompletedProcess[str]":
    (tmp_path / "test_probe.py").write_text(_PROBE, encoding="utf-8")
    (tmp_path / "guard_plugin.py").write_text(_PLUGIN, encoding="utf-8")
    (tmp_path / "none.ini").write_text("[pytest]\n", encoding="utf-8")
    env = {"PYTHONPATH": os.pathsep.join((str(tmp_path), str(repo_root / "tests_scripts"))), "GUARD_CONFTEST": str(repo_root / "tests_scripts" / "conftest.py"), "PATH": os.environ["PATH"]}
    argv = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", str(tmp_path), "-c", str(tmp_path / "none.ini"), *plugin, str(tmp_path / "test_probe.py")]
    return subprocess.run(argv, cwd=tmp_path, env=env, capture_output=True, text=True, timeout=_RUN_TIMEOUT_S, check=False)


def test_without_the_guard_an_exit_ends_the_session_with_the_next_test_unrun(tmp_path: Path, repo_root: Path) -> None:
    # The control: what the guard exists for, so a pytest that stopped ending sessions this way shows here first.
    result = _pytest(tmp_path, repo_root)
    assert result.returncode == 2, f"{result.stdout}\n{result.stderr}"
    assert "probe exit" in result.stdout
    assert "passed" not in result.stdout.splitlines()[-1], result.stdout


def test_with_the_guard_the_exiting_test_fails_and_the_next_one_runs(tmp_path: Path, repo_root: Path) -> None:
    result = _pytest(tmp_path, repo_root, "-p", "guard_plugin")
    assert result.returncode == 1, f"{result.stdout}\n{result.stderr}"
    assert "1 failed, 1 passed" in result.stdout.splitlines()[-1], result.stdout
    assert "pytest.exit() inside a test ends the session with every later test unrun: probe exit" in result.stdout
