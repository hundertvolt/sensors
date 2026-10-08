"""scripts/_hardware_verdict.py judges a hardware pytest run from its run record, never from grepped
output: canned records for each rule, one real pytest run per option spelling, and the gate map held
against what tests_hardware/conftest.py registers and what its marked tests check."""

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from _script_loader import load_script_module

_PERMANENT = "tests_hardware/bench/test_hotspot_role_reversal.py::test_spoofed_off_subnet_source_address_is_ignored"
_GREEN: "dict[str, object]" = {"nodeid": "tests_hardware/bench/test_smoke.py::test_it", "outcome": "passed", "when": "call", "reason": "", "markers": [], "user_properties": []}


@pytest.fixture(scope="module")
def verdict(repo_root: Path) -> ModuleType:
    return load_script_module(repo_root / "scripts" / "_hardware_verdict.py", "_hardware_verdict")


def _record(*tests: "dict[str, object]", collection: "list[dict[str, object]] | None" = None, deselected: "list[dict[str, object]] | None" = None, options: "dict[str, object] | None" = None, collect_only: bool = False, session_notes: "list[dict[str, object]] | None" = None, exitstatus: int = 0) -> "dict[str, object]":
    return {
        "tests": list(tests),
        "collection": collection or [],
        "deselected": deselected or [],
        "options": options or {},
        "markexpr": "",
        "collect_only": collect_only,
        "session_notes": session_notes or [],
        "exitstatus": exitstatus,
    }


def _skipped(nodeid: str, *markers: str, reason: str = "opt-in") -> "dict[str, object]":
    return {"nodeid": nodeid, "outcome": "skipped", "when": "setup", "reason": reason, "markers": list(markers), "user_properties": []}


def _judge(repo_root: Path, tmp_path: Path, record: "dict[str, object] | None", *extra: str, pytest_exit: int = 0) -> "subprocess.CompletedProcess[str]":
    path = tmp_path / "run_record.json"
    if record is not None:
        path.write_text(json.dumps(record))
    argv = ["--run-record", str(path), "--pytest-exit", str(pytest_exit), "--runner", "run_flash_hardware_suite", "--levels", "L3", *extra]
    return subprocess.run([sys.executable, str(repo_root / "scripts" / "_hardware_verdict.py"), *argv], capture_output=True, text=True, check=False, cwd=repo_root)


def _block(stdout: str) -> str:
    start = stdout.rfind("== Summary: run_flash_hardware_suite ==")
    assert start != -1, f"no summary block:\n{stdout}"
    return stdout[start:]


def _result(stdout: str) -> str:
    return next(ln for ln in _block(stdout).splitlines() if ln.startswith("Result:"))


def test_a_clean_run_passes_and_ends_with_the_block(repo_root: Path, tmp_path: Path) -> None:
    result = _judge(repo_root, tmp_path, _record(_GREEN))
    assert result.returncode == 0, result.stdout + result.stderr
    assert _result(result.stdout) == "Result: PASS"
    assert result.stdout.rstrip().splitlines()[-1] == "Exit code: 0", "nothing may follow the block"
    assert "Levels: L3" in _block(result.stdout)


def test_a_nonzero_pytest_exit_is_a_fail_propagated_unchanged(repo_root: Path, tmp_path: Path) -> None:
    result = _judge(repo_root, tmp_path, _record(_GREEN, exitstatus=2), pytest_exit=2)
    assert result.returncode == 2, "the caller must see pytest's own exit code, not a flattened 1"
    assert _result(result.stdout) == "Result: FAIL (pytest exited 2)", "pytest's 2 means interrupted, never this block's usage error"


def test_a_missing_record_is_a_fail_never_a_pass(repo_root: Path, tmp_path: Path) -> None:
    result = _judge(repo_root, tmp_path, None)
    assert result.returncode == 1
    assert "no verdict" in _block(result.stdout)


def test_an_unexpected_skip_fails_whatever_the_callers_verbosity(repo_root: Path, tmp_path: Path) -> None:
    # A caller's -q once hid every SKIPPED line from the grep that judged the run; the record has them all.
    record = _record(_GREEN, _skipped("tests_hardware/bench/test_smoke.py::test_other", reason="board unreachable"), options={"verbose": -1})
    result = _judge(repo_root, tmp_path, record)
    assert result.returncode == 1
    assert "test_other: unexpected skip: board unreachable" in _block(result.stdout)


def test_a_module_level_skip_fails(repo_root: Path, tmp_path: Path) -> None:
    record = _record(_GREEN, collection=[{"nodeid": "tests_hardware/flash/test_x.py", "outcome": "skipped", "reason": "no board"}])
    result = _judge(repo_root, tmp_path, record)
    assert result.returncode == 1
    assert "tests_hardware/flash/test_x.py: unexpected skip: no board" in _block(result.stdout)


def test_the_one_permanent_skip_is_accepted_by_its_exact_nodeid(repo_root: Path, tmp_path: Path) -> None:
    result = _judge(repo_root, tmp_path, _record(_GREEN, _skipped(_PERMANENT, reason="unconfirmed")))
    assert result.returncode == 0, result.stdout
    assert f"{_PERMANENT}: unconfirmed" in _block(result.stdout)


def test_a_name_containing_the_permanent_skip_no_longer_masks_itself(repo_root: Path, tmp_path: Path) -> None:
    # The grep this replaces matched names as substrings, so any test whose name contained a
    # whitelisted one was waved through.
    result = _judge(repo_root, tmp_path, _record(_GREEN, _skipped(_PERMANENT + "_again", reason="board unreachable")))
    assert result.returncode == 1
    assert "unexpected skip" in _block(result.stdout)


def _gate_cases() -> "list[tuple[str, str]]":
    verdict = load_script_module(Path(__file__).resolve().parent.parent / "scripts" / "_hardware_verdict.py", "_hardware_verdict")
    return sorted(verdict.GATE_OPTIONS.items())


@pytest.mark.parametrize(("marker", "dest"), _gate_cases())
def test_a_gate_skip_is_accepted_only_while_its_option_is_unset(repo_root: Path, tmp_path: Path, marker: str, dest: str) -> None:
    skipped = _skipped(f"tests_hardware/flash/test_x.py::test_{marker}", marker)
    unset = _judge(repo_root, tmp_path, _record(_GREEN, skipped, options={dest: None}))
    assert unset.returncode == 0, f"a {marker} skip must be accepted when {dest} is unset:\n{unset.stdout}"
    given = _judge(repo_root, tmp_path, _record(_GREEN, skipped, options={dest: "short" if dest == "soak_tier" else True}))
    assert given.returncode == 1, f"a {marker} test skipping although {dest} was given means the hardware went away"
    assert "skipped although" in _block(given.stdout)


def test_zero_passes_fail_even_with_nothing_else_wrong(repo_root: Path, tmp_path: Path) -> None:
    # pytest exits 0 for an all-skipped run: the ambiguity this verdict exists to close.
    result = _judge(repo_root, tmp_path, _record(_skipped(_PERMANENT)))
    assert result.returncode == 1
    assert "no test passed" in _block(result.stdout)


def test_a_session_recovery_note_is_not_a_pass(repo_root: Path, tmp_path: Path) -> None:
    session = [{"text": "stale credentials repaired", "recovery": True, "source": "dut_ip"}]
    result = _judge(repo_root, tmp_path, _record(_skipped(_PERMANENT), session_notes=session))
    assert result.returncode == 1, "a fixture's recovery is no test passing"
    assert "no test passed" in _block(result.stdout)


def test_runner_selection_is_reported_apart_from_the_wear_gate_with_no_flag_advice(repo_root: Path, tmp_path: Path) -> None:
    record = _record(_GREEN, deselected=[{"nodeid": "tests_hardware/flash/test_x.py::test_soak", "by": "runner selection", "markers": ["long_soak"]}])
    result = _judge(repo_root, tmp_path, record)
    assert result.returncode == 0, result.stdout
    assert "test_soak: by runner selection (-m), not covered by this run" in _block(result.stdout)
    assert "--allow-" not in result.stdout, "a -m exclusion cannot be selected by any --allow-* flag, so none is advised"


def test_wear_gate_deselections_name_their_flag_and_the_advice_names_only_those(repo_root: Path, tmp_path: Path) -> None:
    record = _record(_GREEN, deselected=[{"nodeid": "tests_hardware/flash/test_x.py::test_write", "by": "--allow-persistence-writes", "markers": ["persistence_write"]}])
    result = _judge(repo_root, tmp_path, record)
    assert result.returncode == 0, result.stdout
    assert "test_write: by wear gate --allow-persistence-writes, not covered by this run" in _block(result.stdout)
    advice = result.stdout[: result.stdout.rfind("== Summary:")]
    assert "--allow-persistence-writes" in advice
    assert "--allow-scd30-extra-write" not in advice


def test_a_recovery_pass_is_counted_apart_and_every_note_reaches_the_block(repo_root: Path, tmp_path: Path) -> None:
    recovered = dict(_GREEN, nodeid="tests_hardware/bench/test_x.py::test_flap", user_properties=[["recovery", "recovered via a fallback hard_reset()"], ["result_note", "graceful wait 150.0s"]])
    noted = dict(_GREEN, user_properties=[["result_note", "3 answered, 1 refused"]])
    session = [{"text": "stale credentials repaired", "recovery": True, "source": "dut_ip"}, {"text": "SSID list scanned", "recovery": False, "source": "joined_hotspot"}]
    result = _judge(repo_root, tmp_path, _record(noted, recovered, session_notes=session))
    block = _block(result.stdout)
    assert result.returncode == 0, result.stdout
    assert "passed 1" in block and "recovered 2" in block, block
    assert "test_flap: recovered via a fallback hard_reset()" in block
    assert "Notes: none" not in block, block
    for text in ("graceful wait 150.0s", "3 answered, 1 refused", "SSID list scanned", "stale credentials repaired"):
        assert text in block, f"note {text!r} did not reach the block:\n{block}"


def test_a_collect_only_run_is_not_a_run(repo_root: Path, tmp_path: Path) -> None:
    collected = {"nodeid": _GREEN["nodeid"], "outcome": None, "when": None, "reason": "", "markers": [], "user_properties": []}
    result = _judge(repo_root, tmp_path, _record(collected, collect_only=True))
    assert result.returncode == 0, result.stdout
    assert _result(result.stdout) == "Result: NOT A RUN (collection only)"


def test_a_not_clean_reason_turns_a_passing_run_into_exit_4(repo_root: Path, tmp_path: Path) -> None:
    result = _judge(repo_root, tmp_path, _record(_GREEN), "--not-clean-reason", "lower levels skipped: L0 L1 L2")
    assert result.returncode == 4
    assert _result(result.stdout) == "Result: NOT CLEAN (lower levels skipped: L0 L1 L2)"


def test_a_not_clean_reason_never_hides_a_failure(repo_root: Path, tmp_path: Path) -> None:
    record = _record(_GREEN, _skipped("tests_hardware/flash/test_x.py::test_y", reason="board gone"))
    result = _judge(repo_root, tmp_path, record, "--not-clean-reason", "lower levels skipped: L0 L1 L2")
    assert result.returncode == 1
    assert _result(result.stdout).startswith("Result: FAIL")


def test_a_usage_error_exits_2(repo_root: Path) -> None:
    result = subprocess.run([sys.executable, str(repo_root / "scripts" / "_hardware_verdict.py"), "--runner", "x"], capture_output=True, text=True, check=False)
    assert result.returncode == 2


# ---------------------------------------------------------------------------
# The record reads an option by its parsed value, so both command-line spellings judge alike: a
# real pytest run over a stub suite whose skip-gated test is skipped while its option is given.
# ---------------------------------------------------------------------------

_STUB_CONFTEST = """
import pytest

def pytest_addoption(parser):
    parser.addoption("--soak-tier", default=None)
"""
_STUB_TEST = """
import pytest

def test_green():
    pass

@pytest.mark.long_soak
def test_soak():
    pytest.skip("the board went away")
"""


@pytest.mark.parametrize("spelling", [["--soak-tier=short"], ["--soak-tier", "short"]])
def test_both_spellings_of_an_option_read_alike(repo_root: Path, tmp_path: Path, spelling: "list[str]") -> None:
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "conftest.py").write_text(_STUB_CONFTEST)
    (suite / "test_stub.py").write_text(_STUB_TEST)
    record = tmp_path / "run_record.json"
    env = dict(os.environ, PYTHONPATH=str(repo_root / "scripts"))
    ran = subprocess.run([sys.executable, "-m", "pytest", "-p", "_pytest_run_record", f"--run-record={record}", "-p", "no:cacheprovider", "-W", "ignore::pytest.PytestUnknownMarkWarning", str(suite), *spelling], capture_output=True, text=True, check=False, cwd=tmp_path, env=env)
    assert record.is_file(), ran.stdout + ran.stderr
    result = subprocess.run([sys.executable, str(repo_root / "scripts" / "_hardware_verdict.py"), "--run-record", str(record), "--pytest-exit", str(ran.returncode), "--runner", "run_flash_hardware_suite", "--levels", "L3"], capture_output=True, text=True, check=False)
    assert result.returncode == 1, f"{spelling}: a long_soak skip with --soak-tier given must fail:\n{result.stdout}"
    assert "skipped although --soak-tier was given" in _block(result.stdout)


# ---------------------------------------------------------------------------
# The gate map against tests_hardware/: every gate is a registered option, every marked test reads
# its own option, and the permanent skip names a test that exists.
# ---------------------------------------------------------------------------


def _conftest_option_dests(repo_root: Path) -> "dict[str, str]":
    # flag -> argparse dest, for every option tests_hardware/conftest.py registers.
    tree = ast.parse((repo_root / "tests_hardware" / "conftest.py").read_text())
    flags = [node.args[0].value for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "addoption" and node.args and isinstance(node.args[0], ast.Constant)]
    return {str(flag): str(flag).lstrip("-").replace("-", "_") for flag in flags}


def _marked_tests(repo_root: Path, markers: "set[str]") -> "dict[str, list[tuple[str, str]]]":
    # marker -> [(test name, its source)] for every tests_hardware test carrying it.
    found: dict[str, list[tuple[str, str]]] = {m: [] for m in markers}
    for path in sorted((repo_root / "tests_hardware").rglob("test_*.py")):
        source = path.read_text()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for dec in node.decorator_list:
                    target = dec.func if isinstance(dec, ast.Call) else dec
                    if isinstance(target, ast.Attribute) and target.attr in found:
                        found[target.attr].append((node.name, ast.get_source_segment(source, node) or ""))
    return found


def test_every_gate_is_an_option_tests_hardware_registers(repo_root: Path, verdict: ModuleType) -> None:
    dests = set(_conftest_option_dests(repo_root).values())
    missing = {marker: dest for marker, dest in verdict.GATE_OPTIONS.items() if dest not in dests}
    assert not missing, f"gates whose option tests_hardware/conftest.py does not register: {missing}"


def test_every_skip_gated_marker_is_in_the_gate_map(repo_root: Path, verdict: ModuleType) -> None:
    # A marker registered as "skipped unless <flag>" but absent from the map would make every
    # default run fail on that test's skip, for a reason nothing explains.
    text = (repo_root / "tests_hardware" / "conftest.py").read_text()
    skip_gated = set(re.findall(r'"markers", "(\w+): [^"]*skipped unless', text))
    assert skip_gated, "no skip-gated marker found in tests_hardware/conftest.py - the scan has stopped seeing them"
    assert skip_gated == set(verdict.GATE_OPTIONS), f"conftest's skip-gated markers {sorted(skip_gated)} differ from the verdict's gate map {sorted(verdict.GATE_OPTIONS)}"


def test_every_skip_gated_test_really_checks_its_own_flag(repo_root: Path, verdict: ModuleType) -> None:
    # The marker alone gates nothing: each test skips itself by reading its own option. A marker
    # without that body check runs unasked, costing light programs or a real reflash.
    flag_of = {dest: flag for flag, dest in _conftest_option_dests(repo_root).items()}
    ungated = {marker: [name for name, body in tests if flag_of[verdict.GATE_OPTIONS[marker]] not in body] for marker, tests in _marked_tests(repo_root, set(verdict.GATE_OPTIONS)).items()}
    assert not {k: v for k, v in ungated.items() if v}, f"marked but never actually gated - these would run unasked: {ungated}"


def test_the_permanent_skip_names_a_test_that_exists(repo_root: Path, verdict: ModuleType) -> None:
    for nodeid in verdict.PERMANENT_SKIPS:
        path, name = nodeid.split("::")
        names = {n.name for n in ast.walk(ast.parse((repo_root / path).read_text())) if isinstance(n, ast.FunctionDef)}
        assert name in names, f"{nodeid} no longer exists - its permanent skip would silently stop applying"
