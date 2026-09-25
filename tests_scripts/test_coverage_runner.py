"""tests/_coverage_runner.py is tests/_threshold_runner.py's older sibling and shares its whole
SystemExit contract, but had no test of its own: a swallowed exit code would leave every failing
file in a --coverage run reported as a pass, and the raw dump is what the reports are built from."""

import json
import subprocess
from pathlib import Path

import pytest

_RUNNER = "tests/_coverage_runner.py"


def _probe(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "probe_case.py"
    path.write_text(body)
    return path


@pytest.fixture
def settrace_bin(micropython_bin: Path) -> Path:
    # NOT the rig binary: this runner installs sys.settrace, and build-standard is deliberately
    # built without MICROPY_PY_SYS_SETTRACE (SPECIFICATION.md Part E.5.2). Asking the rig for it
    # raises AttributeError, which is exactly what --coverage's own separate binary exists for.
    path = micropython_bin.parent.parent / "build-settrace" / "micropython"
    if not path.is_file():
        pytest.skip(f"the --coverage variant is not built at {path} - setup_toolchain.py setup builds both")
    return path


def _run(repo_root: Path, micropython_bin: Path, probe: Path, out: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [str(micropython_bin), _RUNNER, str(probe), str(out)],
        cwd=repo_root,
        env={"MICROPYPATH": "build/generated_src:src:tests:frozen_modules:.frozen", "TZ": "UTC"},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.mark.parametrize("code", [0, 1, 3])
def test_the_test_files_exit_code_reaches_the_caller(repo_root: Path, settrace_bin: Path, tmp_path: Path, code: int) -> None:
    # scripts/test.sh reads this process's status to decide the file's PASS/FAIL, in a --coverage
    # run exactly as in a plain one, so a swallowed code turns a red suite green.
    completed = _run(repo_root, settrace_bin, _probe(tmp_path, f"import sys\nsys.exit({code})\n"), tmp_path / "raw.json")
    assert completed.returncode == code, f"expected exit {code}, got {completed.returncode}:\n{completed.stderr}"


def test_a_bare_exit_with_no_args_is_a_pass(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    # MicroPython's SystemExit carries .args, not CPython's .code; a bare sys.exit() leaves it empty.
    completed = _run(repo_root, settrace_bin, _probe(tmp_path, "import sys\nsys.exit()\n"), tmp_path / "raw.json")
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"


def test_the_raw_dump_is_written_even_for_a_failing_file(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    # A red file's coverage still counts: the dump is written after the SystemExit is handled, so
    # a suite with one failure does not silently lose that file's lines from the report.
    out = tmp_path / "raw.json"
    completed = _run(repo_root, settrace_bin, _probe(tmp_path, "import sys\nsys.exit(1)\n"), out)
    assert completed.returncode == 1
    assert out.is_file(), "the raw dump must exist even when the test file failed"
    assert isinstance(json.loads(out.read_text()), dict)


def test_an_uncaught_exception_in_the_test_file_is_not_reported_as_a_pass(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    # Only SystemExit is caught, on purpose: a file dying at import time must still fail its run.
    completed = _run(repo_root, settrace_bin, _probe(tmp_path, "raise RuntimeError('boom before any test ran')\n"), tmp_path / "raw.json")
    assert completed.returncode != 0, f"a file that raised must not exit 0:\n{completed.stdout}\n{completed.stderr}"
    # Combined: the Unix port prints an uncaught traceback to STDOUT (verified directly), which
    # scripts/test.sh merges with 2>&1 before reading - see test_threshold_runner.py's own note.
    assert "RuntimeError" in completed.stdout + completed.stderr, f"the real cause must reach the log: {completed.stdout!r} {completed.stderr!r}"


def test_only_the_traced_prefixes_are_recorded(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    # The scoping claim in the runner's own header: a test file's own body and the runner itself
    # stay untraced, so the report describes src/ and digital_twin/ and nothing else.
    out = tmp_path / "raw.json"
    probe = _probe(tmp_path, "import math_helpers\nmath_helpers.dew_point(20.0, 50.0)\nimport sys\nsys.exit(0)\n")
    completed = _run(repo_root, settrace_bin, probe, out)
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    recorded = json.loads(out.read_text())
    assert recorded, "calling into src/ recorded nothing, so the tracer is not attached at all"
    assert all(name.startswith(("src/", "digital_twin/")) for name in recorded), f"untraced files leaked into the dump: {sorted(recorded)}"
    assert not any(str(probe) in name for name in recorded), "the test file's own body must stay untraced"
