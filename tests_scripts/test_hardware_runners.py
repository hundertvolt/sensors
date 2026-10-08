"""The L3/L4 runners with every callee stubbed (scripts/test.sh, the twin CI runner, npm, uv): every
lower level runs first and a failing one stops before any board is touched, the device loop comes
from devices/*.toml, a skipped lower level is never clean, and bench runs flash as its own step."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_COPIED = (
    "scripts/run_flash_hardware_suite.sh",
    "scripts/run_bench_hardware_suite.sh",
    "scripts/run_bench_soak_tests.sh",
    "scripts/run_manual_hardware_tests.sh",
    "scripts/mpremote_connect.sh",
    "scripts/_run_lower_levels.sh",
    "scripts/_require_clean_hardware_run.sh",
    "scripts/_hardware_verdict.py",
    "scripts/_archive_evidence.py",
    "scripts/_summary_block.py",
    "tests_hardware/run_scopes.py",
)

# One stub for every external command: logs the call, fails when told to, for `uv run pytest` writes
# a canned run record (failing ones on request) where asked, and runs the real archive and verdict.
_STUB = """#!{python}
import json, os, subprocess, sys
name = os.path.basename(sys.argv[0])
args = sys.argv[1:]
with open(os.environ["STUB_CALLS"], "a") as calls:
    calls.write(json.dumps({{"cmd": name, "argv": args, "gc": os.environ.get("GC_THRESHOLD", "")}}) + "\\n")
if name == "uv":
    if args[:2] == ["run", "pytest"]:
        record = next(a.split("=", 1)[1] for a in args if a.startswith("--run-record="))
        failing = os.environ.get("STUB_FAIL_PYTEST_ON", "")
        outcome = "failed" if failing and failing in args else "passed"
        test = {{"nodeid": "tests_hardware/x.py::test_x", "outcome": outcome, "when": "call", "reason": "", "markers": [], "user_properties": []}}
        with open(record, "w") as out:
            json.dump({{"tests": [test], "collection": [], "deselected": [], "options": {{}}, "markexpr": "", "collect_only": False, "session_notes": [], "exitstatus": 0 if outcome == "passed" else 1}}, out)
        sys.exit(0 if outcome == "passed" else 1)
    if args[:2] in (["run", "scripts/_hardware_verdict.py"], ["run", "scripts/_archive_evidence.py"]):
        sys.exit(subprocess.call([sys.executable, *args[1:]]))
    sys.exit(0)
sys.exit(int(os.environ.get("STUB_FAIL_" + name.replace(".", "_").replace("-", "_"), "0")))
"""


@pytest.fixture
def tree(repo_root: Path, tmp_path: Path) -> Path:
    # A throwaway copy of the runners and their real helpers, in its own git work tree.
    root = tmp_path / "repo"
    for rel in _COPIED:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo_root / rel, root / rel)
    shutil.copytree(repo_root / "devices", root / "devices")
    (root / "devices" / "zz_test_leaked.toml").write_text("# a leaked test fixture, never a device\n")
    stub = _STUB.format(python=sys.executable)
    for rel in ("scripts/test.sh", "scripts/run_digital_twin_ci.sh", "bin/npm", "bin/uv"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(stub)
        (root / rel).chmod(0o755)
    git = shutil.which("git") or "git"
    # The host's git config never reaches the scratch repository: a signing hook there fails the commit.
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    subprocess.run([git, "init", "-q"], cwd=root, env=env, check=True)
    subprocess.run([git, "add", "-A"], cwd=root, env=env, check=True)
    subprocess.run([git, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "tree"], cwd=root, env=env, check=True)
    return root


def _run(tree: Path, script: str, *args: str, **env_extra: str) -> "tuple[subprocess.CompletedProcess[str], list[tuple[str, list[str], str]]]":
    calls = tree / "calls.jsonl"
    calls.unlink(missing_ok=True)
    env = dict(os.environ, PATH=f"{tree / 'bin'}{os.pathsep}{os.environ['PATH']}", STUB_CALLS=str(calls), **env_extra)
    env.pop("GC_THRESHOLD", None)
    result = subprocess.run(["/bin/bash", str(tree / "scripts" / script), *args], capture_output=True, text=True, check=False, env=env, cwd=tree, timeout=120)
    logged: list[tuple[str, list[str], str]] = []
    for line in calls.read_text().splitlines() if calls.exists() else []:
        call = json.loads(line)
        logged.append((call["cmd"], call["argv"], call["gc"]))
    return result, logged


def _devices(tree: Path) -> "list[str]":
    return sorted(p.stem for p in (tree / "devices").glob("*.toml") if not p.stem.startswith("zz_test_"))


def _lower(calls: "list[tuple[str, list[str], str]]") -> "list[str]":
    # The lower-level calls in order, each as one readable token.
    names = {"test.sh": "test.sh", "npm": "npm", "run_digital_twin_ci.sh": "twin"}
    return [f"{names[cmd]}{':' + gc if gc else ''}{':' + ' '.join(argv) if argv else ''}" for cmd, argv, gc in calls if cmd in names]


def _pytest_targets(calls: "list[tuple[str, list[str], str]]") -> "list[list[str]]":
    return [[a for a in argv if a.startswith("tests_hardware/")] for cmd, argv, _ in calls if cmd == "uv" and argv[:2] == ["run", "pytest"]]


def _archives(tree: Path) -> "dict[str, list[str]]":
    # build/archive/<name>/ -> the evidence each run directory holds, oldest run first.
    root = tree / "build" / "archive"
    return {d.name: [",".join(sorted(f.name for f in run.iterdir())) for run in sorted(d.iterdir())] for d in sorted(root.iterdir())} if root.is_dir() else {}


def _block(stdout: str) -> str:
    return stdout[stdout.rfind("== Summary: ") :]


def test_the_flash_runner_runs_every_lower_level_first_in_order(tree: Path) -> None:
    result, calls = _run(tree, "run_flash_hardware_suite.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _lower(calls) == ["test.sh", "test.sh:32768", "npm:test", *(f"twin:{d}" for d in _devices(tree))]
    assert _pytest_targets(calls) == [["tests_hardware/flash"]]
    assert "Levels: L0 L1 L2 L3" in _block(result.stdout)


def test_the_device_loop_is_derived_and_skips_leaked_test_fixtures(tree: Path) -> None:
    _, calls = _run(tree, "run_flash_hardware_suite.sh")
    twins = [argv for cmd, argv, _ in calls if cmd == "run_digital_twin_ci.sh"]
    assert twins == [[d] for d in _devices(tree)], twins
    assert len(twins) >= 2, "the device loop must come from devices/*.toml"


@pytest.mark.parametrize("failing", ["test_sh", "npm", "run_digital_twin_ci_sh"])
def test_a_failing_lower_level_stops_before_any_board_is_touched(tree: Path, failing: str) -> None:
    result, calls = _run(tree, "run_flash_hardware_suite.sh", **{f"STUB_FAIL_{failing}": "1"})
    assert result.returncode == 1, result.stdout + result.stderr
    assert not _pytest_targets(calls), "no pytest-on-hardware call may follow a failed lower level"
    assert not [c for c in calls if c[1][:2] == ["run", "scripts/_archive_evidence.py"]]


def test_skipping_the_lower_levels_is_never_clean(tree: Path) -> None:
    result, calls = _run(tree, "run_flash_hardware_suite.sh", "--skip-lower-levels", "-k", "smoke")
    block = _block(result.stdout)
    assert result.returncode == 4, result.stdout + result.stderr
    assert not _lower(calls)
    assert "Result: NOT CLEAN (lower levels skipped: L0 L1 L2)" in block
    assert "Levels: L3" in block, "the block names only the levels that ran"
    pytest_argv = next(argv for cmd, argv, _ in calls if cmd == "uv" and argv[:2] == ["run", "pytest"])
    assert "--skip-lower-levels" not in pytest_argv
    assert pytest_argv[-3:] == ["-k", "smoke", "-v"]


def test_skipping_the_lower_levels_keeps_a_failure_a_failure(tree: Path) -> None:
    result, _ = _run(tree, "run_flash_hardware_suite.sh", "--skip-lower-levels", STUB_FAIL_PYTEST_ON="tests_hardware/flash")
    assert result.returncode == 1, result.stdout


def test_the_bench_runner_runs_flash_then_bench_as_two_steps(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_hardware_suite.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _lower(calls)[:3] == ["test.sh", "test.sh:32768", "npm:test"]
    assert _pytest_targets(calls) == [["tests_hardware/flash"], ["tests_hardware/bench"]]
    assert result.stdout.count("== Summary: run_bench_hardware_suite_flash_step ==") == 1, "each step prints its block"
    assert result.stdout.count("== Summary: run_bench_hardware_suite ==") == 1
    assert "Levels: L0 L1 L2 L3 L4" in _block(result.stdout), "the final block is the bench step's"


def test_each_hardware_step_keeps_its_own_three_runs(tree: Path) -> None:
    # Two bench runs make two flash-step and two bench-step archives: none may prune another, and a
    # soak or flash run beside them archives under its own runner too.
    for _ in range(2):
        result, _ = _run(tree, "run_bench_hardware_suite.sh")
        assert result.returncode == 0, result.stdout + result.stderr
    _run(tree, "run_bench_soak_tests.sh", "--tier", "short")
    _run(tree, "run_flash_hardware_suite.sh")
    evidence = "pytest.log,run_record.json"
    assert _archives(tree) == {
        "run_bench_hardware_suite": [evidence] * 2,
        "run_bench_hardware_suite_flash_step": [evidence] * 2,
        "run_bench_soak_tests": [evidence],
        "run_flash_hardware_suite": [evidence],
    }


def test_the_bench_runner_gives_test_paths_to_the_bench_step_only(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_hardware_suite.sh", "tests_hardware/bench/test_x.py", "-k", "smoke", "tests_hardware/bench/test_y.py::test_z")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _pytest_targets(calls) == [["tests_hardware/flash"], ["tests_hardware/bench/test_x.py", "tests_hardware/bench/test_y.py::test_z"]]
    steps = [argv for cmd, argv, _ in calls if cmd == "uv" and argv[:2] == ["run", "pytest"]]
    assert all(argv[-3:] == ["-k", "smoke", "-v"] for argv in steps), "options reach both steps"


def test_the_bench_runners_usage_states_where_its_arguments_go(tree: Path) -> None:
    result, _ = _run(tree, "run_bench_hardware_suite.sh", "--help")
    text = " ".join(result.stdout.split())
    assert "Test paths (arguments starting with tests_hardware/) go to the bench step only and replace its tests_hardware/bench" in text
    assert "every other argument goes to both steps" in text


def test_a_failing_flash_step_stops_the_bench_runner_before_the_bench_level(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_hardware_suite.sh", STUB_FAIL_PYTEST_ON="tests_hardware/flash")
    assert result.returncode == 1
    assert _pytest_targets(calls) == [["tests_hardware/flash"]]


def test_the_bench_runner_without_lower_levels_is_not_clean(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_hardware_suite.sh", "--skip-lower-levels")
    assert result.returncode == 4, result.stdout
    assert not _lower(calls)
    assert "Levels: L3 L4" in _block(result.stdout)


def test_the_soak_runner_runs_no_lower_level_and_names_its_duration(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_soak_tests.sh", "--tier", "short")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not _lower(calls), "soak sits on top of a clean bench run; it reruns nothing below"
    assert "Levels: soak duration short (not a level)" in _block(result.stdout)


def test_the_soak_runner_without_a_duration_is_a_usage_error(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_soak_tests.sh")
    assert result.returncode == 2
    assert not calls


@pytest.mark.parametrize("script", ["run_flash_hardware_suite.sh", "run_bench_hardware_suite.sh", "run_bench_soak_tests.sh", "run_manual_hardware_tests.sh", "mpremote_connect.sh"])
def test_help_prints_usage_and_runs_nothing(tree: Path, script: str) -> None:
    result, calls = _run(tree, script, "--help")
    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout
    assert not calls, f"--help must have no side effect, saw {calls}"


# ---------------------------------------------------------------------------
# A scoped bench run (owner, 2026-10-08: "only test MQTT (and whatever is affected by your changes) on the
# bench"): the scope's own tests on both steps, its write permission named, never reported clean.
# ---------------------------------------------------------------------------


def _scope(tree: Path, name: str, part: str) -> "list[str]":
    listed = subprocess.run([sys.executable, str(tree / "tests_hardware" / "run_scopes.py"), name, part], capture_output=True, text=True, check=True)
    return listed.stdout.split()


def test_a_scoped_bench_run_gives_each_step_only_its_scopes_tests(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_hardware_suite.sh", "--scope", "mqtt", "--allow-persistence-writes-to=networking/mqtt")
    assert result.returncode == 4, result.stdout + result.stderr
    assert _lower(calls)[:3] == ["test.sh", "test.sh:32768", "npm:test"], "a scope narrows the hardware steps, never the lower levels"
    assert _pytest_targets(calls) == [_scope(tree, "mqtt", "flash"), _scope(tree, "mqtt", "bench")]
    steps = [argv for cmd, argv, _ in calls if cmd == "uv" and argv[:2] == ["run", "pytest"]]
    assert all("--allow-persistence-writes-to=networking/mqtt" in argv for argv in steps), "the scoped permission reaches both steps"
    block = _block(result.stdout)
    assert "== Summary: run_bench_hardware_suite_scope_mqtt ==" in block
    assert "Levels: L0 L1 L2 L3 L4, scope mqtt" in block
    assert "Result: NOT CLEAN (scope mqtt: " in block, block
    assert "== Summary: run_bench_hardware_suite_scope_mqtt_flash_step ==" in result.stdout, "the flash step archives apart from a full run's"


def test_a_scoped_run_refuses_the_global_write_flag_before_any_level_runs(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_hardware_suite.sh", "--scope=mqtt", "--allow-persistence-writes")
    assert result.returncode == 2, result.stdout + result.stderr
    expected = "--allow-persistence-writes-to=" + ",".join(_scope(tree, "mqtt", "writes"))
    assert expected in result.stderr, "the refusal names the scoped flag, with the scope's own groups, to use instead"
    assert not calls, f"nothing may run before the refusal, saw {calls}"


@pytest.mark.parametrize("extra", [["--scope", "nonesuch"], ["--scope", "mqtt", "tests_hardware/bench/test_x.py"], ["--scope"]])
def test_a_bad_scope_is_a_usage_error_before_any_level_runs(tree: Path, extra: "list[str]") -> None:
    result, calls = _run(tree, "run_bench_hardware_suite.sh", *extra)
    assert result.returncode == 2, result.stdout + result.stderr
    assert not calls, f"nothing may run before a usage error, saw {calls}"


def test_a_scoped_run_without_the_lower_levels_names_both_reasons(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_hardware_suite.sh", "--skip-lower-levels", "--scope", "mqtt")
    assert result.returncode == 4, result.stdout
    assert not _lower(calls)
    assert "Result: NOT CLEAN (lower levels skipped: L0 L1 L2; scope mqtt: " in _block(result.stdout)
