"""The L3/L4 runners with every callee stubbed (scripts/test.sh, the twin CI runner, npm, uv): every lower level runs
first and a failing one stops before any board is touched, the device loop is derived, a skipped lower level is never
clean, bench runs flash as its own step, a caller's -m narrows each floor; the soak and rollover runs stand alone."""

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from _script_loader import load_script_module

_COPIED = (
    "scripts/run_flash_hardware_suite.sh",
    "scripts/run_bench_hardware_suite.sh",
    "scripts/run_bench_soak_tests.sh",
    "scripts/run_manual_hardware_tests.sh",
    "scripts/mpremote_connect.sh",
    "scripts/run_bench_rollover_test.sh",
    "scripts/_run_lower_levels.sh",
    "scripts/_devices.sh",
    "scripts/_require_clean_hardware_run.sh",
    "scripts/uv_sync_retried.sh",
    "scripts/_hardware_verdict.py",
    "scripts/_archive_evidence.py",
    "scripts/_summary_block.py",
    "tests_hardware/soak_durations.py",
)
_BENCH = "fixture-bench-device"
_FLOOR = "not soak_duration and not multi_day_rollover"

# One stub for every external command, in bash so a call starts no interpreter: logs the call as written (NUL-separated,
# the argument count first), fails when told to, for `uv run pytest` writes a canned run record where asked, runs the
# real archive, verdict and plain `python`, and answers the bench-device lookup as harness.bench_device() does.
_STUB = """#!/bin/bash
python=@PYTHON@
name="${0##*/}"
printf '%s\\0' "$name" "${GC_THRESHOLD-}" "$#" "$@" >>"${STUB_CALLS:?}" || exit 1
if [ "$name" != uv ]; then
    fail="STUB_FAIL_${name//[.-]/_}"
    exit "${!fail-0}"
fi
args=("$@")
[ "${2-}" != --no-sync ] || args=("$1" "${@:3}")
[ "${args[0]-}" != sync ] || exit "${STUB_FAIL_SYNC-0}"
[ "${args[0]-}" = run ] || exit 0
case "${args[1]-}" in
    pytest)
        record="" outcome=passed status=0
        for arg in "${args[@]}"; do
            case "$arg" in --run-record=*) [ -n "$record" ] || record="${arg#*=}" ;; esac
            if [ -n "${STUB_FAIL_PYTEST_ON-}" ] && [ "$arg" = "$STUB_FAIL_PYTEST_ON" ]; then outcome=failed status=1; fi
        done
        [ -n "$record" ] || { echo "error: the stub pytest got no --run-record=" >&2; exit 1; }
        printf '{"tests": [{"nodeid": "tests_hardware/x.py::test_x", "outcome": "%s", "when": "call", "reason": "", "markers": [], "user_properties": []}], "collection": [], "deselected": [], "options": {}, "markexpr": "", "collect_only": false, "session_notes": [], "exitstatus": %d}' "$outcome" "$status" >"$record"
        exit "$status" ;;
    scripts/_hardware_verdict.py | scripts/_archive_evidence.py) exec "$python" "${args[@]:1}" ;;
    python)
        if [ "${args[2]-}" = -c ] && [[ "${args[3]-}" == *"import harness"* ]]; then
            [ -z "${STUB_FAIL_BENCH_LOOKUP-}" ] || { echo "error: no device TOML sets [device] bench = true" >&2; exit 1; }
            echo "${BENCH_DEVICE:-${STUB_BENCH_DEVICE:?}}"
            exit 0
        fi
        exec "$python" "${args[@]:2}" ;;
    scripts/build_firmware.py) [ -z "${STUB_FAIL_BUILD-}" ] || { echo "error: the stub build failed" >&2; exit 1; } ;;
esac
exit 0
"""


def _archives(tree: Path) -> "dict[str, list[str]]":
    # build/archive/<name>/ -> the evidence each run directory holds, oldest run first.
    root = tree / "build" / "archive"
    return {d.name: [",".join(sorted(f.name for f in run.iterdir())) for run in sorted(d.iterdir())] for d in sorted(root.iterdir())} if root.is_dir() else {}


def _assert_synced_first(uv_calls: "list[list[str]]") -> None:
    # The retried sync (scripts/uv_sync_retried.sh) before any uv run, and no uv run that may sync on its own.
    assert uv_calls and uv_calls[0] == ["sync", "--locked"], f"the run's first uv call is the retried sync: {uv_calls}"
    stray = [argv for argv in uv_calls if argv != ["sync", "--locked"] and argv[:2] != ["run", "--no-sync"]]
    assert not stray, f"these uv calls may sync: {stray}"


def _block(stdout: str) -> str:
    return stdout[stdout.rfind("== Summary: ") :]


def _calls_written(tree: Path) -> "list[tuple[str, list[str], str]]":
    # The stub's log, oldest call first: (command, its arguments as written, GC_THRESHOLD).
    log = tree / "calls.log"
    fields = log.read_text(encoding="utf-8").split("\0")[:-1] if log.exists() else []
    calls: list[tuple[str, list[str], str]] = []
    at = 0
    while at < len(fields):
        end = at + 3 + int(fields[at + 2])
        assert end <= len(fields), f"a truncated call in the stub's log: {fields[at:]}"
        calls.append((fields[at], fields[at + 3 : end], fields[at + 1]))
        at = end
    return calls


def _devices(tree: Path) -> "list[str]":
    return sorted(p.stem for p in (tree / "devices").glob("*.toml") if not p.stem.startswith("zz_test_"))


def _lower(calls: "list[tuple[str, list[str], str]]") -> "list[str]":
    # The lower-level calls in order, each as one readable token.
    names = {"test.sh": "test.sh", "npm": "npm", "run_digital_twin_ci.sh": "twin"}
    return [f"{names[cmd]}{':' + gc if gc else ''}{':' + ' '.join(argv) if argv else ''}" for cmd, argv, gc in calls if cmd in names]


def _markexprs(calls: "list[tuple[str, list[str], str]]") -> "list[list[str]]":
    # Each pytest call's marker expressions, both spellings: pytest keeps only the last, so each call must carry one.
    steps = [argv for cmd, argv, _ in calls if cmd == "uv" and argv[:2] == ["run", "pytest"]]
    return [[argv[i + 1] for i, arg in enumerate(argv) if arg == "-m"] + [arg[2:] for arg in argv if arg.startswith("-m") and arg != "-m"] for argv in steps]


def _pytest_targets(calls: "list[tuple[str, list[str], str]]") -> "list[list[str]]":
    return [[a for a in argv if a.startswith("tests_hardware/")] for cmd, argv, _ in calls if cmd == "uv" and argv[:2] == ["run", "pytest"]]


def _rollover_image(device: str) -> str:
    return f"build/firmware-{device}-tickoffset.uf2"


def _run(tree: Path, script: str, *args: str, **env_extra: str) -> "tuple[subprocess.CompletedProcess[str], list[tuple[str, list[str], str]]]":
    # The script's result and every stub call it made, uv's matched without --no-sync.
    calls = tree / "calls.log"
    calls.unlink(missing_ok=True)
    env = dict(os.environ, PATH=f"{tree / 'bin'}{os.pathsep}{os.environ['PATH']}", STUB_CALLS=str(calls), STUB_BENCH_DEVICE=_BENCH)
    for name in ("GC_THRESHOLD", "BENCH_DEVICE"):
        env.pop(name, None)
    env.update(env_extra)
    result = subprocess.run(["/bin/bash", str(tree / "scripts" / script), *args], capture_output=True, text=True, check=False, env=env, cwd=tree, timeout=120)
    logged = [(cmd, raw[:1] + raw[2:] if cmd == "uv" and raw[1:2] == ["--no-sync"] else raw, gc) for cmd, raw, gc in _calls_written(tree)]
    return result, logged


def _uv_calls_written(tree: Path) -> "list[list[str]]":
    return [raw for cmd, raw, _ in _calls_written(tree) if cmd == "uv"]


@pytest.fixture(scope="module")
def runner_template(repo_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    # The runners and their real helpers in a git work tree of their own, built and committed once for the module.
    root = tmp_path_factory.mktemp("runner_template") / "repo"
    for rel in _COPIED:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo_root / rel, root / rel)
    shutil.copytree(repo_root / "devices", root / "devices")
    (root / "devices" / "zz_test_leaked.toml").write_text("# a leaked test fixture, never a device\n", encoding="utf-8")
    stub = _STUB.replace("@PYTHON@", shlex.quote(sys.executable))
    for rel in ("scripts/test.sh", "scripts/run_digital_twin_ci.sh", "bin/npm", "bin/uv", "bin/sleep"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(stub, encoding="utf-8")
        (root / rel).chmod(0o755)
    git = shutil.which("git") or "git"
    # The host's git config never reaches the scratch repository: a signing hook there fails the commit.
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    subprocess.run([git, "init", "-q"], cwd=root, env=env, check=True)
    subprocess.run([git, "add", "-A"], cwd=root, env=env, check=True)
    subprocess.run([git, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "tree"], cwd=root, env=env, check=True)
    return root


@pytest.fixture
def tree(runner_template: Path, tmp_path: Path) -> Path:
    # Each test's own copy of the template, its history included: no run sees another's archive or call log.
    root = tmp_path / "repo"
    shutil.copytree(runner_template, root, symlinks=True)
    return root


def test_the_flash_runner_runs_every_lower_level_first_in_order(tree: Path) -> None:
    result, calls = _run(tree, "run_flash_hardware_suite.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert _lower(calls) == ["test.sh", "test.sh:32768", "npm:test", *(f"twin:{d}" for d in _devices(tree))]
    assert _pytest_targets(calls) == [["tests_hardware/flash"]]
    assert "Levels: L0 L1 L2 L3" in _block(result.stdout)
    # A plain `uv run` builds the whole dev group first, so a third-party outage would read as a
    # board fault: the run syncs first, retried, and every uv run inside it passes --no-sync.
    _assert_synced_first(_uv_calls_written(tree))


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
    assert pytest_argv[-5:] == ["-k", "smoke", "-m", _FLOOR, "-v"], "the caller's arguments, then the one marker selection, then -v"


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
    _run(tree, "run_bench_soak_tests.sh", "--duration", "short")
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
    assert all(argv[-5:] == ["-k", "smoke", "-m", _FLOOR, "-v"] for argv in steps), "options reach both steps"


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
    result, calls = _run(tree, "run_bench_soak_tests.sh", "--duration", "short")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not _lower(calls), "soak sits on top of a clean bench run; it reruns nothing below"
    assert "Levels: soak duration short (not a level)" in _block(result.stdout)


def test_the_soak_runner_selects_its_marker_and_passes_its_duration(tree: Path) -> None:
    _, calls = _run(tree, "run_bench_soak_tests.sh", "--duration", "mid", "-k", "x")
    argv = next(argv for cmd, argv, _ in calls if cmd == "uv" and argv[:2] == ["run", "pytest"])
    assert argv[argv.index("-m") + 1] == "soak_duration", argv
    assert argv[argv.index("--soak-duration") + 1] == "mid", argv


def test_the_soak_runner_without_a_duration_is_a_usage_error(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_soak_tests.sh")
    assert result.returncode == 2, result.stdout + result.stderr
    assert not calls


@pytest.mark.parametrize(("script", "steps"), [("run_flash_hardware_suite.sh", 1), ("run_bench_hardware_suite.sh", 2)])
def test_every_runner_step_excludes_the_soak_and_rollover_markers(tree: Path, repo_root: Path, script: str, steps: int) -> None:
    # Each marker the floor names is one tests_hardware/markers.py registers: an unknown name would select nothing away.
    _, calls = _run(tree, script, "--skip-lower-levels")
    floors = [argv[argv.index("-m") + 1] for cmd, argv, _ in calls if cmd == "uv" and argv[:2] == ["run", "pytest"]]
    assert floors == [_FLOOR] * steps, floors
    registered = load_script_module(repo_root / "tests_hardware" / "markers.py", "markers_for_the_runner_floor").MARKERS
    named = {word for word in floors[0].split() if word not in {"not", "and", "or"}}
    assert named <= set(registered), f"the floor names markers no conftest registers: {sorted(named - set(registered))}"


_RUNS = {
    "flash": ("run_flash_hardware_suite.sh", ("--skip-lower-levels",), _FLOOR, 1),
    "bench": ("run_bench_hardware_suite.sh", ("--skip-lower-levels",), _FLOOR, 2),
    "soak": ("run_bench_soak_tests.sh", ("--duration", "short"), "soak_duration", 1),
    "rollover": ("run_bench_rollover_test.sh", (), "multi_day_rollover", 1),
}


@pytest.mark.parametrize("run", sorted(_RUNS))
@pytest.mark.parametrize(("caller", "narrowed"), [((), "{floor}"), (("-m", "bus"), "({floor}) and (bus)"), (("-mbus or uart", "-k", "x", "-m", "uart"), "({floor}) and (uart)")], ids=["floor", "narrowed", "last-of-several"])
def test_a_callers_marker_expression_narrows_each_runners_floor(tree: Path, run: str, caller: "tuple[str, ...]", narrowed: str) -> None:
    # A caller's -m never replaces the floor: soak and the rollover wait stay out of the suite runners, and the opt-in
    # runners select only their own marker, whatever -m is passed.
    script, args, floor, steps = _RUNS[run]
    result, calls = _run(tree, script, *args, *caller)
    assert _markexprs(calls) == [[narrowed.format(floor=floor)]] * steps, result.stdout + result.stderr


@pytest.mark.parametrize("run", sorted(_RUNS))
def test_each_runners_floor_names_only_registered_markers(repo_root: Path, run: str) -> None:
    # An unregistered name in -m selects nothing and fails nothing, so a floor naming one would silently run no test.
    registered = load_script_module(repo_root / "tests_hardware" / "markers.py", f"markers_for_the_{run}_floor").MARKERS
    named = {word for word in _RUNS[run][2].split() if word not in {"not", "and", "or"}}
    assert named and named <= set(registered), f"the {run} floor names markers no conftest registers: {sorted(named - set(registered))}"


def test_the_soak_runner_refuses_an_unknown_duration_naming_the_valid_ones(tree: Path, repo_root: Path) -> None:
    result, calls = _run(tree, "run_bench_soak_tests.sh", "--duration", "forever")
    durations = sorted(load_script_module(repo_root / "tests_hardware" / "soak_durations.py", "soak_durations_for_the_runner").SOAK_DURATION_SECONDS)
    assert result.returncode == 2, result.stdout + result.stderr
    assert f"error: unknown duration 'forever' - valid durations: {' '.join(durations)}" in result.stderr, result.stderr
    assert not _pytest_targets(calls) and not [c for c in calls if c[1][:2] == ["run", "scripts/_archive_evidence.py"]], calls


def test_the_soak_runners_usage_names_exactly_the_durations_it_accepts(tree: Path, repo_root: Path) -> None:
    result, _ = _run(tree, "run_bench_soak_tests.sh", "--help")
    durations = sorted(load_script_module(repo_root / "tests_hardware" / "soak_durations.py", "soak_durations_for_the_usage").SOAK_DURATION_SECONDS)
    synopsis = result.stdout.splitlines()[0]
    assert sorted(synopsis[synopsis.index("{") + 1 : synopsis.index("}")].split(",")) == durations, synopsis


def test_the_soak_runners_duration_without_a_name_is_a_usage_error(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_soak_tests.sh", "--duration")
    assert (result.returncode, calls) == (2, []), result.stdout + result.stderr
    assert "error: --duration needs a duration name" in result.stderr


def test_the_rollover_runner_builds_its_image_then_runs_only_the_rollover_round_on_it(tree: Path) -> None:
    result, calls = _run(tree, "run_bench_rollover_test.sh")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not _lower(calls), "the rollover round sits on top of a clean bench run; it reruns nothing below"
    uv = [argv for cmd, argv, _ in calls if cmd == "uv"]
    build = ["run", "scripts/build_firmware.py", _BENCH, "--tick-offset-test", "--output", _rollover_image(_BENCH)]
    pytest_at = next(i for i, argv in enumerate(uv) if argv[:2] == ["run", "pytest"])
    assert uv.index(build) < pytest_at, uv
    argv = uv[pytest_at]
    assert _pytest_targets(calls) == [["tests_hardware/bench"]]
    assert {"--allow-multi-day-rollover", "--allow-flash-cycle"} <= set(argv), argv
    assert argv[argv.index("--rollover-image") + 1] == _rollover_image(_BENCH), argv
    assert "Levels: rollover (not a level)" in _block(result.stdout)
    _assert_synced_first(_uv_calls_written(tree))


@pytest.mark.parametrize("args", [("--bench-device", "fixture-other-device"), ("--bench-device=fixture-other-device",)], ids=["separate", "attached"])
def test_the_rollover_image_is_built_for_the_board_pytest_is_told_to_drive(tree: Path, args: "tuple[str, ...]") -> None:
    result, calls = _run(tree, "run_bench_rollover_test.sh", *args)
    assert result.returncode == 0, result.stdout + result.stderr
    builds = [argv for cmd, argv, _ in calls if cmd == "uv" and argv[:2] == ["run", "scripts/build_firmware.py"]]
    assert [argv[2] for argv in builds] == ["fixture-other-device"], builds
    pytest_argv = next(argv for cmd, argv, _ in calls if cmd == "uv" and argv[:2] == ["run", "pytest"])
    assert pytest_argv[pytest_argv.index("--rollover-image") + 1] == _rollover_image("fixture-other-device")


@pytest.mark.parametrize(("failing", "builds"), [("STUB_FAIL_BUILD", 1), ("STUB_FAIL_BENCH_LOOKUP", 0)], ids=["build", "bench-device"])
def test_a_failed_rollover_preparation_exits_1_before_the_board_is_touched(tree: Path, failing: str, builds: int) -> None:
    result, calls = _run(tree, "run_bench_rollover_test.sh", **{failing: "1"})
    assert result.returncode == 1, result.stdout + result.stderr
    assert len([c for c in calls if c[1][:2] == ["run", "scripts/build_firmware.py"]]) == builds, calls
    assert not _pytest_targets(calls) and not [c for c in calls if c[1][:2] == ["run", "scripts/_archive_evidence.py"]], calls
    assert "error: " in result.stderr, result.stderr


def test_the_manual_runner_syncs_first_then_starts_the_runner_unsynced(tree: Path) -> None:
    manual = tree / "tests_hardware" / "manual" / "__main__.py"
    manual.parent.mkdir(parents=True, exist_ok=True)
    manual.write_text("import sys\nprint('manual runner', *sys.argv[1:])\n", encoding="utf-8")
    result, _ = _run(tree, "run_manual_hardware_tests.sh", "--list")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "manual runner --list" in result.stdout
    assert _uv_calls_written(tree) == [["sync", "--locked"], ["run", "--no-sync", "python", "tests_hardware/manual/__main__.py", "--list"]]


@pytest.mark.parametrize(("script", "args"), [("run_manual_hardware_tests.sh", ("--list",)), ("run_bench_rollover_test.sh", ())], ids=["manual", "rollover"])
def test_a_sync_failing_every_attempt_exits_1_before_anything_else(tree: Path, script: str, args: "tuple[str, ...]") -> None:
    # uv's own failure code is 2, which these runners' exit codes reserve for a usage error.
    result, calls = _run(tree, script, *args, STUB_FAIL_SYNC="2")
    assert result.returncode == 1, result.stdout + result.stderr
    assert [cmd for cmd, _, _ in calls if cmd != "sleep"] == ["uv"] * 3 and _uv_calls_written(tree) == [["sync", "--locked"]] * 3, calls
    assert "error: the retried uv sync failed" in result.stderr, result.stderr


@pytest.mark.parametrize(("args", "named"), [((), "a hardware level is required"), (("L5",), "unknown level 'L5'"), (("L3", "L4"), "one level only")], ids=["none", "unknown", "two"])
def test_the_lower_levels_refuse_anything_but_one_hardware_level_before_running(tree: Path, args: "tuple[str, ...]", named: str) -> None:
    result, calls = _run(tree, "_run_lower_levels.sh", *args)
    assert (result.returncode, calls) == (2, []), result.stdout + result.stderr
    assert f"error: {named}" in result.stderr, result.stderr


@pytest.mark.parametrize("script", ["_require_clean_hardware_run.sh", "run_bench_rollover_test.sh", "run_bench_soak_tests.sh", "run_manual_hardware_tests.sh", "mpremote_connect.sh", "typecheck.sh"])
def test_every_uv_run_line_in_the_script_carries_no_sync(repo_root: Path, script: str) -> None:
    # The source form of the rule, so a branch the stubbed runs above never take is covered too.
    lines = [line.strip() for line in (repo_root / "scripts" / script).read_text(encoding="utf-8").splitlines() if "uv run" in line and not line.lstrip().startswith("#")]
    assert lines, f"{script} has no uv run line - the scan has stopped seeing them"
    assert all("uv run --no-sync " in line for line in lines), lines


@pytest.mark.parametrize("script", ["run_flash_hardware_suite.sh", "run_bench_hardware_suite.sh", "run_bench_soak_tests.sh", "run_bench_rollover_test.sh", "run_manual_hardware_tests.sh", "_run_lower_levels.sh"])
def test_help_prints_usage_and_runs_nothing(tree: Path, script: str) -> None:
    result, calls = _run(tree, script, "--help")
    assert result.returncode == 0, result.stderr
    assert "Usage:" in result.stdout
    assert not calls, f"--help must have no side effect, saw {calls}"
