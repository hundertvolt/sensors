"""scripts/_require_clean_hardware_run.sh with a stub `uv` on PATH: pytest runs once with the
run-record plugin, its exit code is kept, the log and record land in the evidence archive, and the
verdict (the real scripts/_hardware_verdict.py, whose rules test_hardware_verdict.py covers) decides."""

import json
import os
import subprocess
import sys
from pathlib import Path

_GREEN: "dict[str, object]" = {"nodeid": "tests_hardware/bench/test_smoke.py::test_it", "outcome": "passed", "when": "call", "reason": "", "markers": [], "user_properties": []}

# Logs every call, writes the canned record where pytest was told to, and runs the real verdict.
_STUB_UV = """#!{python}
import json, os, subprocess, sys
args = sys.argv[1:]
with open(os.environ["STUB_CALLS"], "a") as calls:
    calls.write(json.dumps({{"argv": args, "pythonpath": os.environ.get("PYTHONPATH", "")}}) + "\\n")
if args[:2] == ["run", "scripts/_archive_evidence.py"]:
    os.makedirs(os.environ["STUB_EVIDENCE"], exist_ok=True)
    print(os.environ["STUB_EVIDENCE"])
    sys.exit(0)
if args[:2] == ["run", "pytest"]:
    record = next(a.split("=", 1)[1] for a in args if a.startswith("--run-record="))
    with open(record, "w") as out, open(os.environ["STUB_RECORD"]) as canned:
        out.write(canned.read())
    print("canned pytest output")
    sys.exit(int(os.environ["STUB_PYTEST_EXIT"]))
if args[:2] == ["run", "scripts/_hardware_verdict.py"]:
    sys.exit(subprocess.call([sys.executable, *args[1:]]))
sys.exit(97)
"""


def _record(*tests: "dict[str, object]", exitstatus: int = 0) -> "dict[str, object]":
    return {"tests": list(tests), "collection": [], "deselected": [], "options": {}, "markexpr": "", "collect_only": False, "session_notes": [], "exitstatus": exitstatus}


def _run(repo_root: Path, tmp_path: Path, *args: str, record: "dict[str, object] | None" = None, pytest_exit: int = 0) -> "tuple[subprocess.CompletedProcess[str], list[tuple[list[str], str]]]":
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "uv"
    stub.write_text(_STUB_UV.format(python=sys.executable))
    stub.chmod(0o755)
    (tmp_path / "canned.json").write_text(json.dumps(record if record is not None else _record(_GREEN)))
    calls = tmp_path / "calls.jsonl"
    env = dict(
        os.environ,
        PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        STUB_CALLS=str(calls),
        STUB_EVIDENCE=str(tmp_path / "archive" / "run"),
        STUB_RECORD=str(tmp_path / "canned.json"),
        STUB_PYTEST_EXIT=str(pytest_exit),
    )
    result = subprocess.run(["/bin/bash", str(repo_root / "scripts" / "_require_clean_hardware_run.sh"), *args], capture_output=True, text=True, check=False, env=env, cwd=repo_root)
    logged: list[tuple[list[str], str]] = []
    for line in calls.read_text().splitlines() if calls.exists() else []:
        call = json.loads(line)
        logged.append((call["argv"], call["pythonpath"]))
    return result, logged


def _pytest_call(calls: "list[tuple[list[str], str]]") -> "tuple[list[str], str]":
    found = [c for c in calls if c[0][:2] == ["run", "pytest"]]
    assert len(found) == 1, f"pytest must run exactly once, saw {calls}"
    return found[0]


_ARGS = ("--runner", "run_flash_hardware_suite", "--levels", "L0 L1 L2 L3", "tests_hardware/flash", "-m", "not long_soak")


def test_a_clean_run_exits_0_with_the_verdicts_block(repo_root: Path, tmp_path: Path) -> None:
    result, _ = _run(repo_root, tmp_path, *_ARGS)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "== Summary: run_flash_hardware_suite ==" in result.stdout
    assert "Levels: L0 L1 L2 L3" in result.stdout
    assert result.stdout.rstrip().splitlines()[-1] == "Exit code: 0"


def test_pytest_runs_once_with_the_record_plugin_and_the_callers_arguments_before_v(repo_root: Path, tmp_path: Path) -> None:
    _, calls = _run(repo_root, tmp_path, *_ARGS, "-q")
    argv, pythonpath = _pytest_call(calls)
    assert pythonpath == "scripts", "the plugin is found on PYTHONPATH=scripts"
    assert argv[2:4] == ["-p", "_pytest_run_record"], argv
    assert argv[4] == f"--run-record={tmp_path / 'archive' / 'run' / 'run_record.json'}", argv
    assert argv[5:-1] == ["tests_hardware/flash", "-m", "not long_soak", "-q"], "the wrapper's own options must not reach pytest"
    assert argv[-1] == "-v", "-v comes after the caller's arguments"


def test_the_log_and_the_record_land_in_the_evidence_archive(repo_root: Path, tmp_path: Path) -> None:
    result, calls = _run(repo_root, tmp_path, *_ARGS)
    assert ["run", "scripts/_archive_evidence.py", "--runner", "run_flash_hardware_suite", "--new-dir"] in [argv for argv, _ in calls]
    evidence = tmp_path / "archive" / "run"
    assert "canned pytest output" in (evidence / "pytest.log").read_text()
    assert json.loads((evidence / "run_record.json").read_text())["tests"] == [_GREEN]
    assert "canned pytest output" in result.stdout, "the pytest output still reaches the terminal"


def test_the_archive_is_named_after_the_runner_sanitised(repo_root: Path, tmp_path: Path) -> None:
    # Each runner keeps its own newest three: a shared name let one runner's runs prune another's.
    result, calls = _run(repo_root, tmp_path, "--runner", "Bench-Step 2", *_ARGS[2:])
    assert ["run", "scripts/_archive_evidence.py", "--runner", "bench_step_2", "--new-dir"] in [argv for argv, _ in calls]
    assert "== Summary: Bench-Step 2 ==" in result.stdout, "the block keeps the runner's own name"


def test_the_verdict_gets_the_record_the_exit_code_the_runner_and_the_levels(repo_root: Path, tmp_path: Path) -> None:
    _, calls = _run(repo_root, tmp_path, *_ARGS, "--x")
    verdict = [argv for argv, _ in calls if argv[:2] == ["run", "scripts/_hardware_verdict.py"]]
    record = str(tmp_path / "archive" / "run" / "run_record.json")
    assert verdict == [["run", "scripts/_hardware_verdict.py", "--run-record", record, "--pytest-exit", "0", "--runner", "run_flash_hardware_suite", "--levels", "L0 L1 L2 L3"]], verdict


def test_a_nonzero_pytest_exit_is_propagated_unchanged(repo_root: Path, tmp_path: Path) -> None:
    result, _ = _run(repo_root, tmp_path, *_ARGS, record=_record(exitstatus=2), pytest_exit=2)
    assert result.returncode == 2, "the caller must see pytest's own exit code, not a flattened 1"


def test_a_failing_verdict_fails_the_wrapper_although_pytest_exited_0(repo_root: Path, tmp_path: Path) -> None:
    skipped: dict[str, object] = {"nodeid": "tests_hardware/bench/test_smoke.py::test_other", "outcome": "skipped", "when": "setup", "reason": "board unreachable", "markers": [], "user_properties": []}
    result, _ = _run(repo_root, tmp_path, *_ARGS, record=_record(_GREEN, skipped))
    assert result.returncode == 1
    assert "unexpected skip: board unreachable" in result.stdout


def test_a_not_clean_reason_reaches_the_verdict(repo_root: Path, tmp_path: Path) -> None:
    result, _ = _run(repo_root, tmp_path, "--not-clean-reason", "lower levels skipped: L0 L1 L2", *_ARGS)
    assert result.returncode == 4, result.stdout + result.stderr
    assert "Result: NOT CLEAN (lower levels skipped: L0 L1 L2)" in result.stdout


def test_a_missing_runner_or_levels_is_a_usage_error_before_any_run(repo_root: Path, tmp_path: Path) -> None:
    result, calls = _run(repo_root, tmp_path, "--levels", "L3", "tests_hardware/flash")
    assert result.returncode == 2
    assert not calls, "a usage error must touch nothing"


def test_help_prints_usage_and_runs_nothing(repo_root: Path, tmp_path: Path) -> None:
    result, calls = _run(repo_root, tmp_path, "--help")
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert not calls
