"""scripts/_require_clean_hardware_run.sh with a stub `uv` on PATH: pytest runs once with the
run-record plugin, its exit code is kept, the log and record land in the evidence archive, and the
verdict (the real scripts/_hardware_verdict.py, whose rules test_hardware_verdict.py covers) decides."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_GREEN: "dict[str, object]" = {"nodeid": "tests_hardware/bench/test_smoke.py::test_it", "outcome": "passed", "when": "call", "reason": "", "markers": [], "user_properties": []}

# Logs every call (raw, so a missing --no-sync shows), writes the canned record where pytest was told to, and runs the
# real verdict. A call is matched with its --no-sync removed. In bash, so the verdict is the only interpreter a run
# starts; each logged line is JSON, its strings escaped for the backslash and quote the arguments here may hold.
_STUB_UV = r"""#!/usr/bin/env bash
raw=("$@")
args=("$@")
[ "${raw[1]-}" != --no-sync ] || args=("${raw[0]}" "${raw[@]:2}")
_json_str() {
    local s="${1//\\/\\\\}"
    printf '"%s"' "${s//\"/\\\"}"
}
_json_list() {
    local sep="" a
    printf '['
    for a in "$@"; do
        printf '%s' "$sep"
        _json_str "$a"
        sep=", "
    done
    printf ']'
}
{
    printf '{"argv": '
    _json_list "${args[@]}"
    printf ', "raw": '
    _json_list "${raw[@]}"
    printf ', "pythonpath": '
    _json_str "${PYTHONPATH-}"
    printf ', "evidence_dir": '
    if [ -n "${EVIDENCE_DIR+set}" ]; then _json_str "$EVIDENCE_DIR"; else printf 'null'; fi
    printf '}\n'
} >>"$STUB_CALLS"
case "${args[0]-} ${args[1]-}" in
"run scripts/_archive_evidence.py")
    mkdir -p "$STUB_EVIDENCE"
    echo "$STUB_EVIDENCE"
    exit 0
    ;;
"run pytest")
    record=""
    for a in "${args[@]}"; do
        if [[ "$a" == --run-record=* ]]; then
            record="${a#--run-record=}"
            break
        fi
    done
    [ -n "$record" ] || { echo "stub uv: pytest was given no --run-record=" >&2; exit 1; }
    cat "$STUB_RECORD" >"$record" || exit 1
    echo "canned pytest output"
    exit "$STUB_PYTEST_EXIT"
    ;;
"run scripts/_hardware_verdict.py")
    exec "$STUB_PYTHON" "${args[@]:1}"
    ;;
esac
exit 97
"""


def _markexprs(calls: "list[tuple[list[str], str]]") -> "list[str]":
    argv, _ = _pytest_call(calls)
    return [argv[i + 1] for i, arg in enumerate(argv) if arg == "-m"] + [arg[2:] for arg in argv if arg.startswith("-m") and arg != "-m"]


def _pytest_call(calls: "list[tuple[list[str], str]]") -> "tuple[list[str], str]":
    found = [c for c in calls if c[0][:2] == ["run", "pytest"]]
    assert len(found) == 1, f"pytest must run exactly once, saw {calls}"
    return found[0]


def _raw_calls(tmp_path: Path) -> "list[tuple[list[str], list[str], str | None]]":
    # (matched argv, argv as written, $EVIDENCE_DIR) per logged stub call: the raw form shows a missing --no-sync.
    calls = tmp_path / "calls.jsonl"
    entries = [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()] if calls.exists() else []
    return [(list(e["argv"]), list(e["raw"]), e["evidence_dir"]) for e in entries]


def _record(*tests: "dict[str, object]", exitstatus: int = 0) -> "dict[str, object]":
    return {"tests": list(tests), "collection": [], "deselected": [], "options": {}, "markexpr": "", "collect_only": False, "session_notes": [], "exitstatus": exitstatus}


def _run(repo_root: Path, tmp_path: Path, *args: str, record: "dict[str, object] | None" = None, pytest_exit: int = 0) -> "tuple[subprocess.CompletedProcess[str], list[tuple[list[str], str]]]":
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "uv"
    stub.write_text(_STUB_UV, encoding="utf-8")
    stub.chmod(0o755)
    (tmp_path / "canned.json").write_text(json.dumps(record if record is not None else _record(_GREEN)), encoding="utf-8")
    calls = tmp_path / "calls.jsonl"
    env = dict(
        os.environ,
        PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        STUB_CALLS=str(calls),
        STUB_EVIDENCE=str(tmp_path / "archive" / "run"),
        STUB_RECORD=str(tmp_path / "canned.json"),
        STUB_PYTEST_EXIT=str(pytest_exit),
        STUB_PYTHON=sys.executable,
    )
    result = subprocess.run(["/bin/bash", str(repo_root / "scripts" / "_require_clean_hardware_run.sh"), *args], capture_output=True, text=True, check=False, env=env, cwd=repo_root)
    logged: list[tuple[list[str], str]] = []
    for line in calls.read_text(encoding="utf-8").splitlines() if calls.exists() else []:
        call = json.loads(line)
        logged.append((call["argv"], call["pythonpath"]))
    return result, logged


_FLOOR = "not soak_duration and not multi_day_rollover"
_ARGS = ("--runner", "run_flash_hardware_suite", "--levels", "L0 L1 L2 L3", "--marker-floor", _FLOOR, "tests_hardware/flash")


def test_a_clean_run_exits_0_with_the_verdicts_block(repo_root: Path, tmp_path: Path) -> None:
    result, _ = _run(repo_root, tmp_path, *_ARGS)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "== Summary: run_flash_hardware_suite ==" in result.stdout
    assert "Levels: L0 L1 L2 L3" in result.stdout
    assert result.stdout.rstrip().splitlines()[-1] == "Exit code: 0"


def test_pytest_runs_once_with_the_record_plugin_and_the_callers_arguments_before_v(repo_root: Path, tmp_path: Path) -> None:
    _, calls = _run(repo_root, tmp_path, *_ARGS, "--allow-persistence-write", "-q")
    argv, pythonpath = _pytest_call(calls)
    assert pythonpath == "scripts", "the plugin is found on PYTHONPATH=scripts"
    assert argv[2:4] == ["-p", "_pytest_run_record"], argv
    assert argv[4] == f"--run-record={tmp_path / 'archive' / 'run' / 'run_record.json'}", argv
    assert argv[5:-1] == ["tests_hardware/flash", "--allow-persistence-write", "-q", "-m", _FLOOR], "the wrapper's own options must not reach pytest"
    assert argv[-1] == "-v", "-v comes after the caller's arguments"


@pytest.mark.parametrize(
    ("caller", "expected"),
    [
        ((), _FLOOR),
        (("-m", "bus"), f"({_FLOOR}) and (bus)"),
        (("-mbus or uart",), f"({_FLOOR}) and (bus or uart)"),
        (("-m", "bus", "-k", "x", "-m", "uart"), f"({_FLOOR}) and (uart)"),
    ],
    ids=["floor-only", "narrowed", "attached-form", "last-of-several"],
)
def test_a_callers_marker_expression_narrows_the_floor_and_never_replaces_it(repo_root: Path, tmp_path: Path, caller: "tuple[str, ...]", expected: str) -> None:
    # pytest keeps only the last -m it is given, so the wrapper passes exactly one: the floor, and the caller's last
    # expression inside it; the selection is printed, so the log names what ran.
    result, calls = _run(repo_root, tmp_path, *_ARGS, *caller)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _markexprs(calls) == [expected]
    assert f'== Marker selection: -m "{expected}"\n' in result.stdout, result.stdout
    assert f'== Marker selection: -m "{expected}"\n' in (tmp_path / "archive" / "run" / "pytest.log").read_text(encoding="utf-8")


def test_without_a_floor_the_callers_last_marker_expression_is_the_selection(repo_root: Path, tmp_path: Path) -> None:
    _, calls = _run(repo_root, tmp_path, "--runner", "r", "--levels", "L3", "tests_hardware/flash", "-m", "a", "-m", "b")
    assert _markexprs(calls) == ["b"]


@pytest.mark.parametrize("args", [("-m",), ("--marker-floor",)], ids=["caller-m", "floor"])
def test_a_marker_flag_without_its_expression_is_a_usage_error_before_any_run(repo_root: Path, tmp_path: Path, args: "tuple[str, ...]") -> None:
    head = ("--runner", "r", "--levels", "L3") if args == ("--marker-floor",) else _ARGS
    result, calls = _run(repo_root, tmp_path, *head, *args)
    assert result.returncode == 2, result.stdout + result.stderr
    assert f"error: {args[0]} needs " in result.stderr, result.stderr
    assert not calls, "a usage error must touch nothing"


def test_every_uv_call_runs_without_an_implicit_sync(repo_root: Path, tmp_path: Path) -> None:
    # A plain `uv run` syncs the whole dev group first, so a third-party fetch would sit inside a
    # hardware run and an outage would read as a hardware failure.
    _run(repo_root, tmp_path, *_ARGS)
    raw = [written for _argv, written, _dir in _raw_calls(tmp_path)]
    assert len(raw) == 3, raw
    unsynced = [argv for argv in raw if argv[:2] != ["run", "--no-sync"]]
    assert not unsynced, f"these uv calls may sync: {unsynced}"


def test_pytest_sees_the_evidence_directory_exported(repo_root: Path, tmp_path: Path) -> None:
    # the evidence helper writes a run's saved files beside its log and record.
    _run(repo_root, tmp_path, *_ARGS)
    seen = [evidence for argv, _raw, evidence in _raw_calls(tmp_path) if argv[:2] == ["run", "pytest"]]
    assert seen == [str(tmp_path / "archive" / "run")], seen


def test_the_log_and_the_record_land_in_the_evidence_archive(repo_root: Path, tmp_path: Path) -> None:
    result, calls = _run(repo_root, tmp_path, *_ARGS)
    assert ["run", "scripts/_archive_evidence.py", "--runner", "run_flash_hardware_suite", "--new-dir"] in [argv for argv, _ in calls]
    evidence = tmp_path / "archive" / "run"
    assert "canned pytest output" in (evidence / "pytest.log").read_text(encoding="utf-8")
    assert json.loads((evidence / "run_record.json").read_text(encoding="utf-8"))["tests"] == [_GREEN]
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
