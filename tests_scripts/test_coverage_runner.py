"""tests/_coverage_runner.py is tests/_threshold_runner.py's older sibling and shares its whole
SystemExit contract, but had no test of its own: a swallowed exit code would leave every failing
file in a --coverage run reported as a pass, and the raw dump is what the reports are built from."""

import ast
import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from _script_loader import load_script_module

if TYPE_CHECKING:
    from collections.abc import Callable

_RUNNER = "tests/_coverage_runner.py"
# @tunable l0.coverage_runner_timeout_s = 60
_RUN_TIMEOUT_S = 60


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
        pytest.fail(f"the --coverage variant is not built at {path} - setup_toolchain.py setup builds both")
    return path


def _outcome_of(fixture: "Callable[[Path], Path]", argument: Path) -> BaseException:
    # Caught as BaseException: a pytest.skip() escaping here would otherwise skip this very test,
    # turning the check for "never a skip" into one more silent skip.
    with pytest.raises(BaseException) as caught:
        fixture(argument)
    return caught.value


def test_a_missing_unix_port_fails_rather_than_skipping(repo_root: Path, tmp_path: Path) -> None:
    # A skip reads as a pass in every summary, so a suite run against an unbuilt toolchain would
    # report green while checking nothing: the missing interpreter is a failure naming its build step.
    conftest = load_script_module(repo_root / "tests_scripts" / "conftest.py", "_tests_scripts_conftest_under_test")
    outcome = _outcome_of(conftest.micropython_bin.__wrapped__, tmp_path / "micropython")
    assert isinstance(outcome, pytest.fail.Exception), f"a missing Unix port must fail, not {type(outcome).__name__}: {outcome}"
    assert "setup_toolchain.py setup" in str(outcome)


def test_a_missing_coverage_build_fails_rather_than_skipping(repo_root: Path, tmp_path: Path) -> None:
    this_file = load_script_module(repo_root / "tests_scripts" / "test_coverage_runner.py", "_coverage_runner_tests_under_test")
    rig = tmp_path / "ports" / "unix" / "build-standard" / "micropython"
    outcome = _outcome_of(this_file.settrace_bin.__wrapped__, rig)
    assert isinstance(outcome, pytest.fail.Exception), f"a missing --coverage build must fail, not {type(outcome).__name__}: {outcome}"
    assert "setup_toolchain.py setup builds both" in str(outcome)


def _run(repo_root: Path, micropython_bin: Path, probe: Path, out: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [str(micropython_bin), _RUNNER, str(probe), str(out)],
        cwd=repo_root,
        env={"MICROPYPATH": "build/generated_src:src:tests:frozen_modules:.frozen", "TZ": "UTC"},
        capture_output=True,
        text=True,
        timeout=_RUN_TIMEOUT_S,
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


_FIRST_TOUCH_PROBE = """import gc
import sys
import math_helpers


def warm_up():
    for _ in range(3):
        math_helpers.abs_humidity(20.0, 50.0)
        math_helpers.cct_mccamy(0.31, 0.32)
        math_helpers.chromaticity_xy(1.0, 2.0, 3.0)
        math_helpers.ema_step(1.0, 2.0, 0.5)


def first_run():
    for _ in range(3):
        math_helpers.pressure_at_height(1013.0, 100.0, 15.0)
        math_helpers.rel_humidity(20.0, 8.0)
        math_helpers.rgb_to_hsb(10.0, 20.0, 30.0)
        math_helpers.rgb_to_xyz(10.0, 20.0, 30.0)
        math_helpers.wet_bulb_temperature(20.0, 50.0)


def measured(span):
    gc.collect()
    before = gc.mem_alloc()
    span()
    gc.collect()
    return gc.mem_alloc() - before


math_helpers.dew_point(20.0, 50.0)
measured(warm_up)
print("GREW", measured(first_run))
sys.exit(0)
"""


def _grew(completed: "subprocess.CompletedProcess[str]") -> list[str]:
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    return [line for line in completed.stdout.splitlines() if line.startswith("GREW ")]


def test_lines_run_for_the_first_time_leave_the_collected_heap_where_it_was(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    # Tests measure their own heap under this runner, so recording must not allocate: lines first run inside a
    # measured span store into tables sized at start. The first measured span carries a one-time cost with or without
    # a tracer (up to 128 B, 2026-10-07), so a warm-up span absorbs it; the per-line dict grew 416 B on the second.
    out, probe = tmp_path / "raw.json", _probe(tmp_path, _FIRST_TOUCH_PROBE)
    untraced = _grew(subprocess.run([str(settrace_bin), str(probe)], cwd=repo_root, env={"MICROPYPATH": "build/generated_src:src:tests:frozen_modules:.frozen", "TZ": "UTC"}, capture_output=True, text=True, timeout=_RUN_TIMEOUT_S, check=False))
    traced = _grew(_run(repo_root, settrace_bin, probe, out))
    assert len(untraced) == 1, untraced
    assert traced == untraced, f"recording the measured span's new lines moved the collected heap: {traced} traced against {untraced} untraced"
    recorded = json.loads(out.read_text())["src/math_helpers.py"]
    source = (repo_root / "src" / "math_helpers.py").read_text().splitlines()
    wet_bulb = next(n for n, text in enumerate(source, 1) if text.startswith("def wet_bulb_temperature("))
    assert any(n > wet_bulb for n in recorded), "the lines first run inside the measured span are missing from the dump"
    assert max(recorded) <= len(source), f"a recorded line lies past the file's end: {max(recorded)} > {len(source)}"


def test_every_traced_file_gets_its_line_table_up_front(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    # A file without a table records through the allocating fallback; subdirectories count (digital_twin/unixport/).
    source = (repo_root / _RUNNER).read_text()
    assert source.count("sys.exit(_run())") == 1, "the runner's entry line moved - update this probe"
    lister = tmp_path / "list_tables.py"
    lister.write_text(source.replace("sys.exit(_run())", "print(json.dumps(sorted(_line_tables())))"))
    completed = subprocess.run([str(settrace_bin), str(lister)], cwd=repo_root, env={"MICROPYPATH": ".frozen"}, capture_output=True, text=True, timeout=_RUN_TIMEOUT_S, check=False)
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    expected = sorted(p.relative_to(repo_root).as_posix() for prefix in ("src", "digital_twin") for p in (repo_root / prefix).rglob("*.py"))
    assert json.loads(completed.stdout) == expected


def test_the_trace_functions_close_over_nothing(repo_root: Path) -> None:
    # The tracer runs on every traced line, and MicroPython heap-allocates a closure call's argument array once its
    # closed-over values plus arguments pass five (py/objclosure.c): one nested trace function with one more captured
    # name made whole coverage runs 2.6x slower (2026-10-07). Module-level functions capture nothing.
    tree = ast.parse((repo_root / _RUNNER).read_text())
    scopes = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
    nested = [getattr(inner, "name", "<lambda>") for outer in ast.walk(tree) if isinstance(outer, scopes) for inner in ast.walk(outer) if inner is not outer and isinstance(inner, scopes)]
    assert not nested, f"{_RUNNER} defines functions inside functions, each a closure on the per-line path: {nested}"
