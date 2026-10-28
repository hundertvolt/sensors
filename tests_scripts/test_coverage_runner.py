"""tests/_coverage_runner.py is tests/_threshold_runner.py's older sibling and shares its whole
SystemExit contract, but had no test of its own: a swallowed exit code would leave every failing
file in a --coverage run reported as a pass, and the raw dump is what the reports are built from."""

import ast
import fcntl
import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import tomllib
from _devices import DEVICE_NAMES
from _script_loader import load_script_module

if TYPE_CHECKING:
    from collections.abc import Callable

_RUNNER = "tests/_coverage_runner.py"
# The unit layout scripts/test.sh runs every file on, from its one definition.
_UNIT = tomllib.loads((Path(__file__).resolve().parent.parent / "scripts" / "micropypath.toml").read_text(encoding="utf-8"))["unit"]
# @tunable l0.coverage_runner_timeout_s = 60
_RUN_TIMEOUT_S = 60


def _grew(completed: "subprocess.CompletedProcess[str]") -> list[str]:
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    return [line for line in completed.stdout.splitlines() if line.startswith("GREW ")]


def _outcome_of(fixture: "Callable[[Path], Path]", argument: Path) -> BaseException:
    # Caught as BaseException: a pytest.skip() escaping here would otherwise skip this very test,
    # turning the check for "never a skip" into one more silent skip.
    try:
        fixture(argument)
    except BaseException as exc:
        return exc
    pytest.fail(f"{argument} raised nothing")


def _probe(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "probe_case.py"
    path.write_text(body, encoding="utf-8")
    return path


def _plant_binary(toolchain: Path, flavour: str, *, reports: str) -> None:
    binary = toolchain / "micropython" / "ports" / "unix" / f"build-{flavour}" / "micropython"
    binary.parent.mkdir(parents=True)
    binary.write_text(f"#!/bin/sh\necho {reports}\n", encoding="utf-8")
    binary.chmod(0o755)


def test_a_missing_unix_port_fails_rather_than_skipping(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A skip reads as a pass in every summary, so a suite run against an unbuilt toolchain would
    # report green while checking nothing: the missing interpreter is a failure naming its build step.
    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(tmp_path))
    conftest = load_script_module(repo_root / "tests_scripts" / "conftest.py", "_tests_scripts_conftest_under_test")
    outcome = _outcome_of(lambda _: next(conftest.micropython_bin.__wrapped__()), tmp_path)
    assert isinstance(outcome, pytest.fail.Exception), f"a missing Unix port must fail, not {type(outcome).__name__}: {outcome}"
    assert str(outcome) == f"error: no MicroPython Unix port at {tmp_path}/micropython/ports/unix/build-standard/micropython - build it with: uv run toolchain/setup_toolchain.py setup"


def test_a_binary_of_another_flavour_fails_the_suite_naming_it(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # build-standard carrying settrace would measure every allocation 4-5x inflated (SPECIFICATION.md E.5.2).
    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(tmp_path))
    _plant_binary(tmp_path, "standard", reports="settrace")
    conftest = load_script_module(repo_root / "tests_scripts" / "conftest.py", "_tests_scripts_conftest_under_test")
    outcome = _outcome_of(lambda _: next(conftest.micropython_bin.__wrapped__()), tmp_path)
    assert isinstance(outcome, pytest.fail.Exception), outcome
    assert "reports itself as the 'settrace' build flavour, not 'standard'" in str(outcome)


def test_the_suite_holds_the_toolchain_lock_shared_and_refuses_while_a_setup_holds_it(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A setup removes and rebuilds the binaries the tier's twins boot: while the session holds the lock shared a setup
    # is refused at once, and a setup already holding it fails the session's first use of the binary, naming it.
    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(tmp_path))
    _plant_binary(tmp_path, "standard", reports="standard")
    conftest = load_script_module(repo_root / "tests_scripts" / "conftest.py", "_tests_scripts_conftest_under_test")
    held = conftest.micropython_bin.__wrapped__()
    assert next(held) == tmp_path / "micropython" / "ports" / "unix" / "build-standard" / "micropython"
    with (tmp_path / ".toolchain.lock").open("a", encoding="utf-8") as setup:
        with pytest.raises(BlockingIOError):
            fcntl.flock(setup, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held.close()
        fcntl.flock(setup, fcntl.LOCK_EX | fcntl.LOCK_NB)
        setup.write("4242\n")
        setup.flush()
        outcome = _outcome_of(lambda _: next(conftest.micropython_bin.__wrapped__()), tmp_path)
    assert isinstance(outcome, pytest.fail.Exception), outcome
    assert "is in use by a setup or firmware build (pid 4242," in str(outcome), outcome


def test_a_missing_coverage_build_fails_rather_than_skipping(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PICO_TOOLCHAIN_DIR", str(tmp_path))
    this_file = load_script_module(repo_root / "tests_scripts" / "test_coverage_runner.py", "_coverage_runner_tests_under_test")
    outcome = _outcome_of(this_file.settrace_bin.__wrapped__, tmp_path)
    assert isinstance(outcome, pytest.fail.Exception), f"a missing --coverage build must fail, not {type(outcome).__name__}: {outcome}"
    assert str(outcome).startswith("the --coverage build flavour is not usable: error: no MicroPython Unix port at "), outcome
    assert "setup_toolchain.py setup" in str(outcome)


def _run(repo_root: Path, micropython_bin: Path, probe: Path, out: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [str(micropython_bin), _RUNNER, str(probe), str(out)],
        cwd=repo_root,
        env={"MICROPYPATH": _UNIT, "TZ": "UTC"},
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
    assert isinstance(json.loads(out.read_text(encoding="utf-8")), dict)


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
    recorded = json.loads(out.read_text(encoding="utf-8"))
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


@pytest.fixture
def settrace_bin(micropython_bin: Path) -> Path:
    # NOT the rig binary: this runner installs sys.settrace, and build-standard is deliberately built without
    # MICROPY_PY_SYS_SETTRACE (SPECIFICATION.md Part E.5.2); the probe names the build flavour that has it. Taking the
    # rig first holds the toolchain lock for the session, as every user of the Unix port does.
    del micropython_bin
    done = subprocess.run(["/bin/bash", "scripts/_unix_port.sh", "check", "settrace"], cwd=Path(__file__).resolve().parent.parent, capture_output=True, text=True, timeout=_RUN_TIMEOUT_S, check=False)
    if done.returncode != 0:
        pytest.fail(f"the --coverage build flavour is not usable: {done.stderr.strip() or f'scripts/_unix_port.sh check settrace exited {done.returncode}'}")
    return Path(done.stdout.strip())


def test_lines_run_for_the_first_time_leave_the_collected_heap_where_it_was(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    # Tests measure their own heap under this runner, so recording must not allocate: lines first run inside a
    # measured span store into tables sized at start. The first measured span carries a one-time cost with or without
    # a tracer (up to 128 B, 2026-10-07), so a warm-up span absorbs it; the per-line dict grew 416 B on the second.
    out, probe = tmp_path / "raw.json", _probe(tmp_path, _FIRST_TOUCH_PROBE)
    untraced = _grew(subprocess.run([str(settrace_bin), str(probe)], cwd=repo_root, env={"MICROPYPATH": _UNIT, "TZ": "UTC"}, capture_output=True, text=True, timeout=_RUN_TIMEOUT_S, check=False))
    traced = _grew(_run(repo_root, settrace_bin, probe, out))
    assert len(untraced) == 1, untraced
    assert traced == untraced, f"recording the measured span's new lines moved the collected heap: {traced} traced against {untraced} untraced"
    recorded = json.loads(out.read_text(encoding="utf-8"))["src/math_helpers.py"]
    source = (repo_root / "src" / "math_helpers.py").read_text(encoding="utf-8").splitlines()
    wet_bulb = next(n for n, text in enumerate(source, 1) if text.startswith("def wet_bulb_temperature("))
    assert any(n > wet_bulb for n in recorded), "the lines first run inside the measured span are missing from the dump"
    assert max(recorded) <= len(source), f"a recorded line lies past the file's end: {max(recorded)} > {len(source)}"


_CALLS_PROBE = """import sys
import time


def callee():
    return 1


start = time.ticks_us()
for _ in range(40000):
    callee()
print("CALLS", time.ticks_diff(time.ticks_us(), start))
sys.exit(0)
"""


def _calls_us(completed: "subprocess.CompletedProcess[str]") -> int:
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    return next(int(line.split()[1]) for line in completed.stdout.splitlines() if line.startswith("CALLS "))


def test_a_run_of_calls_under_the_tracer_never_rescans_the_heap(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    # This build allocates a multi-block frame and code object per call, and py/gc.c starts a search after the last
    # single-block allocation only, so a run of calls rescans everything it allocated: 40,000 untraced calls took 2.0 s
    # against 43-72 ms traced (2026-10-14). Equal or slower traced means the tracer stopped keeping the search short.
    probe = _probe(tmp_path, _CALLS_PROBE)
    env = {"MICROPYPATH": _UNIT, "TZ": "UTC"}
    heap = ["-X", "heapsize=16M"]  # scripts/test.sh's heap: the rescan is bounded by the heap, not by the test
    untraced = _calls_us(subprocess.run([str(settrace_bin), *heap, str(probe)], cwd=repo_root, env=env, capture_output=True, text=True, timeout=_RUN_TIMEOUT_S, check=False))
    traced = _calls_us(subprocess.run([str(settrace_bin), *heap, _RUNNER, str(probe), str(tmp_path / "raw.json")], cwd=repo_root, env=env, capture_output=True, text=True, timeout=_RUN_TIMEOUT_S, check=False))
    assert traced * 4 < untraced, f"40,000 traced calls took {traced} us against {untraced} us untraced: the tracer no longer keeps the allocator's search short"


def test_every_traced_file_gets_its_line_table_up_front(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    # A file without a table records through the allocating fallback; subdirectories count (digital_twin/unixport/).
    source = (repo_root / _RUNNER).read_text(encoding="utf-8")
    assert source.count("sys.exit(_run())") == 1, "the runner's entry line moved - update this probe"
    lister = tmp_path / "list_tables.py"
    lister.write_text(source.replace("sys.exit(_run())", "print(json.dumps(sorted(_line_tables())))"), encoding="utf-8")
    completed = subprocess.run([str(settrace_bin), str(lister)], cwd=repo_root, env={"MICROPYPATH": ".frozen:tests"}, capture_output=True, text=True, timeout=_RUN_TIMEOUT_S, check=False)  # tests/: the runner's _untraced
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    expected = sorted(p.relative_to(repo_root).as_posix() for prefix in ("src", "digital_twin", "build/generated_src") for p in (repo_root / prefix).rglob("*.py"))
    assert json.loads(completed.stdout) == expected


def test_the_trace_functions_close_over_nothing(repo_root: Path) -> None:
    # The tracer runs on every traced line, and MicroPython heap-allocates a closure call's argument array once its
    # closed-over values plus arguments pass five (py/objclosure.c): one nested trace function with one more captured
    # name made whole coverage runs 2.6x slower (2026-10-07). Module-level functions capture nothing.
    tree = ast.parse((repo_root / _RUNNER).read_text(encoding="utf-8"))
    scopes = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
    nested = [getattr(inner, "name", "<lambda>") for outer in ast.walk(tree) if isinstance(outer, scopes) for inner in ast.walk(outer) if inner is not outer and isinstance(inner, scopes)]
    assert not nested, f"{_RUNNER} defines functions inside functions, each a closure on the per-line path: {nested}"


def test_a_file_that_never_reaches_microtests_exit_fails_and_still_dumps(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    out, probe = tmp_path / "raw.json", _probe(tmp_path, "import math_helpers\nmath_helpers.dew_point(20.0, 50.0)\n")
    completed = _run(repo_root, settrace_bin, probe, out)
    assert completed.returncode == 1, f"{completed.stdout}\n{completed.stderr}"
    assert f"runner: {probe} ended without microtest's exit - no trailer, or it never ran" in completed.stdout
    assert "src/math_helpers.py" in json.loads(out.read_text(encoding="utf-8"))


def test_a_raising_top_level_fails_and_its_lines_are_still_dumped(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    out, probe = tmp_path / "raw.json", _probe(tmp_path, "import math_helpers\nmath_helpers.dew_point(20.0, 50.0)\nraise RuntimeError('import-time failure')\n")
    completed = _run(repo_root, settrace_bin, probe, out)
    assert completed.returncode == 1, f"{completed.stdout}\n{completed.stderr}"
    assert "RuntimeError" in completed.stdout + completed.stderr
    assert "src/math_helpers.py" in json.loads(out.read_text(encoding="utf-8")), "the lines run before the escape were lost"


def test_an_exit_with_a_message_is_a_failure_not_a_crash_of_the_runner(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    out = tmp_path / "raw.json"
    completed = _run(repo_root, settrace_bin, _probe(tmp_path, "import sys\nsys.exit('gave up')\n"), out)
    assert completed.returncode == 1, f"{completed.stdout}\n{completed.stderr}"
    assert out.is_file()


def test_a_generated_device_modules_lines_are_traced(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    # build/generated_src/ is measured like src/: a device module imported by a test reaches the dump.
    out, module = tmp_path / "raw.json", f"sensortask_{DEVICE_NAMES[0]}"
    probe = _probe(tmp_path, f"import sys\nsys.path.insert(0, 'ext')\nimport {module}\nsys.exit(0)\n")  # microdot is in ext/, as the libraries add it
    completed = _run(repo_root, settrace_bin, probe, out)
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert f"build/generated_src/{module}.py" in json.loads(out.read_text(encoding="utf-8"))


# The C-stack tests' shape: a recursion reaches the interpreter's limit inside the trace callback, and every line after
# it runs untraced (py/profile.c:168-173 leaves the callback's is-executing flag set, py/vm.c:161-185 then skips).
_DEATH_PROBE = """import sys

ns = {}
exec(compile("def before():\\n    return 1\\n", "src/<before>", "exec"), ns)
ns["before"]()


def deep(n):
    return deep(n + 1)


def exhaust():
    try:
        deep(0)
    except RuntimeError:
        pass


CALL
exec(compile("after = 2\\n", "src/<after>", "exec"), {})
ENDING
"""


@pytest.mark.parametrize("ending", ["sys.exit(0)", "sys.exit(1)", "raise ValueError('after the end of tracing')", ""])
def test_a_raise_inside_the_trace_callback_leaves_a_note_naming_the_last_traced_line(repo_root: Path, settrace_bin: Path, tmp_path: Path, ending: str) -> None:
    # Nothing else says so: the file's own result stands, and the lines are still dumped, on every ending.
    out = tmp_path / "raw.json"
    completed = _run(repo_root, settrace_bin, _probe(tmp_path, _DEATH_PROBE.replace("CALL", "exhaust()").replace("ENDING", ending)), out)
    assert completed.returncode == (0 if ending == "sys.exit(0)" else 1), f"{completed.stdout}\n{completed.stderr}"
    assert json.loads(out.read_text(encoding="utf-8")) == {"src/<before>": [1, 2]}, "src/<after> traced, or the runner's own probe reached the dump"
    note = "runner: tracing ended after src/<before>:2 - every traced line the file ran after it is missing from its coverage"
    assert (tmp_path / "raw.json.incomplete").read_text(encoding="utf-8") == note + "\n"
    assert note in completed.stdout


def test_a_file_whose_tracer_lives_to_the_end_leaves_no_note(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    out = tmp_path / "raw.json"
    probe = _probe(tmp_path, "import math_helpers\nmath_helpers.dew_point(20.0, 50.0)\nimport sys\nsys.exit(0)\n")
    completed = _run(repo_root, settrace_bin, probe, out)
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert not (tmp_path / "raw.json.incomplete").exists(), (tmp_path / "raw.json.incomplete").read_text(encoding="utf-8")
    assert sorted(json.loads(out.read_text(encoding="utf-8"))) == ["src/math_helpers.py"], "the runner's own probe reached the dump"
    assert "tracing ended" not in completed.stdout


def test_a_call_run_through_untraced_keeps_the_rest_of_the_file_traced(repo_root: Path, settrace_bin: Path, tmp_path: Path) -> None:
    out = tmp_path / "raw.json"
    body = "from _untraced import untraced\n" + _DEATH_PROBE.replace("CALL", "untraced(exhaust)").replace("ENDING", "sys.exit(0)")
    completed = _run(repo_root, settrace_bin, _probe(tmp_path, body), out)
    assert completed.returncode == 0, f"{completed.stdout}\n{completed.stderr}"
    assert json.loads(out.read_text(encoding="utf-8")) == {"src/<before>": [1, 2], "src/<after>": [1]}
    assert not (tmp_path / "raw.json.incomplete").exists()
