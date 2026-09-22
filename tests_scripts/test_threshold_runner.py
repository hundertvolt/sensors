"""tests/_threshold_runner.py is what makes CLAUDE.md's (f) stage runnable, and it is the one part
of that stage whose failure is invisible: a runner that quietly stopped applying the threshold would
leave CI's unit-tests-gc-threshold job just as green while measuring the (e) stage twice."""

import subprocess
from pathlib import Path

import pytest

_RUNNER = "tests/_threshold_runner.py"
_SHIPPED_THRESHOLD = 32768  # what buildgen emits into the generated boot entry (codegen.py)


def _probe(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "probe_case.py"
    path.write_text(body)
    return path


def _run(repo_root: Path, micropython_bin: Path, args: "list[str]") -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [str(micropython_bin), *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def test_the_runner_applies_the_threshold_it_was_given(repo_root: Path, micropython_bin: Path, tmp_path: Path) -> None:
    probe = _probe(tmp_path, "import gc\nprint('THRESHOLD', gc.threshold())\n")
    completed = _run(repo_root, micropython_bin, [_RUNNER, str(probe), str(_SHIPPED_THRESHOLD)])
    assert completed.returncode == 0, completed.stderr
    assert f"THRESHOLD {_SHIPPED_THRESHOLD}" in completed.stdout, f"the test file did not observe the threshold the runner was asked for: {completed.stdout!r}"


def test_the_same_file_run_directly_is_the_reactive_default(repo_root: Path, micropython_bin: Path, tmp_path: Path) -> None:
    # The control, and what makes the assertion above mean something: it is the RUNNER that changes
    # the threshold, not the interpreter's own build. -1 is MicroPython's own reactive default and
    # the (e) stage every plain scripts/test.sh run measures at.
    probe = _probe(tmp_path, "import gc\nprint('THRESHOLD', gc.threshold())\n")
    completed = _run(repo_root, micropython_bin, [str(probe)])
    assert completed.returncode == 0, completed.stderr
    assert "THRESHOLD -1" in completed.stdout, f"the plain run is no longer at the reactive default, so the two stages no longer differ: {completed.stdout!r}"


def test_the_threshold_is_set_before_the_test_file_body_runs(repo_root: Path, micropython_bin: Path, tmp_path: Path) -> None:
    # Ordering, not just the final value: a test file allocates while importing its own module under
    # test, and a threshold applied after that would leave the heaviest part of the file unmeasured.
    probe = _probe(tmp_path, "import gc\nassert gc.threshold() == 32768, gc.threshold()\nprint('ORDER ok')\n")
    completed = _run(repo_root, micropython_bin, [_RUNNER, str(probe), str(_SHIPPED_THRESHOLD)])
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert "ORDER ok" in completed.stdout


def test_the_test_files_own_name_is_main_so_its_entry_point_fires(repo_root: Path, micropython_bin: Path, tmp_path: Path) -> None:
    # Every tests/test_*.py file ends in a microtest.run() guarded on __name__ - without this the
    # runner would exec 85 files that define their tests and then run none of them, and still exit 0.
    probe = _probe(tmp_path, "print('NAME', __name__)\n")
    completed = _run(repo_root, micropython_bin, [_RUNNER, str(probe), "-1"])
    assert completed.returncode == 0, completed.stderr
    assert "NAME __main__" in completed.stdout


@pytest.mark.parametrize("code", [0, 1, 3])
def test_the_test_files_exit_code_reaches_the_caller(repo_root: Path, micropython_bin: Path, tmp_path: Path, code: int) -> None:
    # microtest.run() always exits explicitly (CLAUDE.md's known hang cause #2), so a swallowed
    # SystemExit would turn every failing file in the (f) stage into a pass.
    probe = _probe(tmp_path, f"import sys\nsys.exit({code})\n")
    completed = _run(repo_root, micropython_bin, [_RUNNER, str(probe), str(_SHIPPED_THRESHOLD)])
    assert completed.returncode == code, f"expected exit {code}, got {completed.returncode}:\n{completed.stderr}"


def test_a_bare_exit_with_no_args_is_a_pass(repo_root: Path, micropython_bin: Path, tmp_path: Path) -> None:
    # MicroPython's SystemExit carries .args, not CPython's .code, and a bare sys.exit() leaves it
    # empty - the branch the runner reads as 0 rather than tripping over an IndexError.
    probe = _probe(tmp_path, "import sys\nsys.exit()\n")
    completed = _run(repo_root, micropython_bin, [_RUNNER, str(probe), str(_SHIPPED_THRESHOLD)])
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
