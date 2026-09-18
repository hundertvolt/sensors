"""Drives scripts/_require_clean_hardware_run.sh's verdict logic against canned pytest output, via a
stub `uv` on PATH, and holds the two sides of its skip-gating contract to each other: what the script
whitelists, and what tests_hardware/ actually marks and gates. All of it is invisible to any run this
session is allowed to make."""

import ast
import os
import re
import subprocess
from pathlib import Path

import pytest

# Which opt-in flag each skip-gating marker belongs to. persistence_write/scd30_extra_write are
# deliberately absent: they DESELECT rather than skip, which is invisible to this script by design
# (the verdict reports the deselected count instead) - see the script's own header.
_SKIP_GATES = {
    "flash_cycle": "--allow-flash-cycle",
    "long_soak": "--soak-tier",
    "multi_day_rollover": "--allow-multi-day-rollover-wait",
    "neopixel_sweep": "--allow-neopixel-sweep",
}


def _whitelisted_by_flag(repo_root: Path) -> "dict[str, set[str]]":
    """The script's own contextual whitelist, parsed back out of it: {flag: {test name, ...}}."""
    text = (repo_root / "scripts" / "_require_clean_hardware_run.sh").read_text()
    flag_of_var = dict(re.findall(r'\[ "\$arg" = "(--[a-z-]+)" \] && (\w+)=1', text))
    by_flag: dict[str, set[str]] = {flag: set() for flag in flag_of_var}
    var_to_flag = {var: flag for flag, var in flag_of_var.items()}
    for var, block in re.findall(r'if \[ "\$(\w+)" = 0 \]; then(.*?)\nfi', text, re.DOTALL):
        if var in var_to_flag:
            by_flag[var_to_flag[var]].update(re.findall(r'"(test_\w+)"', block))
    return by_flag


def _marked_tests(repo_root: Path) -> "dict[str, set[str]]":
    """Every tests_hardware/ test function carrying one of the skip-gating markers, by marker."""
    found: dict[str, set[str]] = {marker: set() for marker in _SKIP_GATES}
    for path in sorted((repo_root / "tests_hardware").rglob("test_*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                if isinstance(target, ast.Attribute) and target.attr in found:
                    found[target.attr].add(node.name)
    return found

_GREEN_LINE = "tests_hardware/bench/test_smoke.py::test_it PASSED  [100%]"
_SUMMARY = "==== 1 passed in 1.23s ===="


def _run(repo_root: Path, tmp_path: Path, log: str, *args: str, pytest_exit: int = 0) -> subprocess.CompletedProcess[str]:
    """Runs the real script with `uv` replaced by a stub that replays `log` and exits pytest_exit."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    (tmp_path / "canned.log").write_text(log)
    stub = bin_dir / "uv"
    stub.write_text(f'#!/bin/sh\ncat "{tmp_path}/canned.log"\nexit {pytest_exit}\n')
    stub.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return subprocess.run(
        ["/bin/bash", str(repo_root / "scripts" / "_require_clean_hardware_run.sh"), "tests_hardware/bench", *args],
        capture_output=True, text=True, check=False, env=env, cwd=repo_root,
    )


def test_a_clean_run_with_nothing_deselected_says_so_explicitly(repo_root: Path, tmp_path: Path) -> None:
    result = _run(repo_root, tmp_path, f"{_GREEN_LINE}\n{_SUMMARY}\n")
    assert result.returncode == 0, result.stderr
    assert "nothing deselected" in result.stdout


def test_a_gated_run_names_the_deselected_count_rather_than_only_saying_clean(repo_root: Path, tmp_path: Path) -> None:
    # The regression this exists for: deselection is invisible to every skip/pass check in the
    # script, so a third of the bench tier silently not running exited 0 with an unqualified "OK".
    result = _run(repo_root, tmp_path, f"{_GREEN_LINE}\n==== 48 passed, 23 deselected in 9.9s ====\n")
    assert result.returncode == 0, result.stderr
    assert "23 deselected" in result.stdout
    assert "does NOT" in result.stdout, "the verdict must state that the deselected tests were not covered"
    assert "--allow-persistence-writes" in result.stdout, "the verdict must name the flag that would cover them"


def test_the_summary_line_wins_over_an_earlier_deselected_mention(repo_root: Path, tmp_path: Path) -> None:
    # pytest prints its own "N deselected" during collection as well as in the final summary, and
    # the two differ whenever a `-m` expression narrows further mid-run. `tail -1` picks the
    # authoritative one; a `head -1` refactor would report a stale count as the verdict.
    log = f"collected 71 items / 23 deselected / 48 selected\n{_GREEN_LINE}\n==== 43 passed, 5 deselected in 9.9s ====\n"
    verdict = _run(repo_root, tmp_path, log).stdout.split("cover them")[0].rsplit("OK:", 1)[-1]
    assert "5 deselected" in verdict, "the verdict must report the summary line's count"
    assert "23 deselected" not in verdict, "a head -1 refactor would report the stale collection-time count"


def test_an_unexpected_skip_fails_the_run(repo_root: Path, tmp_path: Path) -> None:
    log = f"{_GREEN_LINE}\ntests_hardware/bench/test_smoke.py::test_other SKIPPED (board unreachable)\n{_SUMMARY}\n"
    result = _run(repo_root, tmp_path, log)
    assert result.returncode == 1
    assert "unexpected test skip" in result.stderr
    assert "test_other" in result.stderr


def test_the_one_known_permanent_skip_is_accepted(repo_root: Path, tmp_path: Path) -> None:
    log = f"{_GREEN_LINE}\ntests_hardware/bench/test_hotspot_role_reversal.py::test_spoofed_off_subnet_source_address_is_ignored SKIPPED (unconfirmed)\n{_SUMMARY}\n"
    result = _run(repo_root, tmp_path, log)
    assert result.returncode == 0, result.stderr


def _gate_cases() -> "list[tuple[str, str]]":
    # Built from the script itself, so a gate added there without a case here cannot go unexercised.
    return sorted((flag, name) for flag, names in _whitelisted_by_flag(Path(__file__).resolve().parent.parent).items() for name in names)


@pytest.mark.parametrize(("flag", "test_name"), _gate_cases())
def test_a_gated_skip_is_accepted_without_its_flag_and_rejected_with_it(repo_root: Path, tmp_path: Path, flag: str, test_name: str) -> None:
    # The contextual half of the whitelist, and the easiest to break by promoting an entry to
    # unconditional: passing the flag and STILL getting a skip means the hardware went away mid-run,
    # which is exactly what this script exists to refuse to call clean. Parametrized over every gated
    # name rather than one representative - each entry is hand-written in the script and one of them
    # was genuinely missing (see the completeness test below for how that failed).
    log = f"{_GREEN_LINE}\ntests_hardware/flash/test_x.py::{test_name} SKIPPED (opt-in)\n{_SUMMARY}\n"
    assert _run(repo_root, tmp_path, log).returncode == 0, f"{test_name} must be an accepted skip when {flag} is absent"
    assert _run(repo_root, tmp_path, log, flag).returncode == 1, f"{test_name} skipping despite {flag} must fail the run"


def test_every_skip_gated_test_is_whitelisted_under_its_own_flag(repo_root: Path) -> None:
    # The gap this closes cost nothing to write and can only otherwise be found by spending bench
    # time: a marker-gated test absent from the script's list skips in every default run, is not
    # recognised, and turns a genuinely clean bench suite into "FAILED: unexpected test skip".
    # test_real_hardware_survives_extended_max_speed_hammer_load_with_fram_diagnostics_preserved was
    # exactly that until 2026-09-18 - marked long_soak, never whitelisted.
    whitelisted = _whitelisted_by_flag(repo_root)
    missing = {
        marker: sorted(names - whitelisted.get(_SKIP_GATES[marker], set()))
        for marker, names in _marked_tests(repo_root).items()
        if names - whitelisted.get(_SKIP_GATES[marker], set())
    }
    assert not missing, f"skip-gated tests the verdict script would reject as unexpected skips: {missing}"


def test_every_skip_gated_test_really_checks_its_own_flag(repo_root: Path) -> None:
    # The marker alone gates nothing: tests_hardware/conftest.py deselects only the persistence
    # pair, so each of these tests skips itself by reading its own option. A marker added without
    # that body check fails in the expensive direction - the test RUNS on a bench that was never
    # opted in, driving ~10 minutes of light programs or a real reflash nobody asked for.
    ungated: dict[str, list[str]] = {}
    for path in sorted((repo_root / "tests_hardware").rglob("test_*.py")):
        source = path.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for dec in node.decorator_list:
                target = dec.func if isinstance(dec, ast.Call) else dec
                if not isinstance(target, ast.Attribute) or target.attr not in _SKIP_GATES:
                    continue
                body = ast.get_source_segment(source, node) or ""
                if _SKIP_GATES[target.attr] not in body:
                    ungated.setdefault(target.attr, []).append(node.name)
    assert not ungated, f"marked but never actually gated - these would run unasked: {ungated}"


def test_the_whitelist_carries_no_name_that_no_longer_exists(repo_root: Path) -> None:
    # The other drift direction. A dead entry is not immediately harmful, but it silently stops
    # covering the renamed test, whose own skip then fails the run for a reason nothing explains.
    marked = _marked_tests(repo_root)
    known_permanent = {"test_spoofed_off_subnet_source_address_is_ignored"}  # unconditional, not marker-gated
    for marker, flag in _SKIP_GATES.items():
        stale = _whitelisted_by_flag(repo_root).get(flag, set()) - marked[marker] - known_permanent
        assert not stale, f"{flag}'s whitelist names {sorted(stale)}, which carry no @pytest.mark.{marker} any more"


def test_an_all_skipped_run_with_zero_passes_fails(repo_root: Path, tmp_path: Path) -> None:
    # pytest exits 0 for an all-skipped run, which is the ambiguity the whole script exists to close.
    result = _run(repo_root, tmp_path, "==== 71 skipped in 0.4s ====\n")
    assert result.returncode == 1
    assert "zero real passes" in result.stderr


def test_a_literal_zero_passed_does_not_satisfy_the_real_pass_check(repo_root: Path, tmp_path: Path) -> None:
    # Defensive, and the reason the pattern is [1-9][0-9]* rather than [0-9]+: pytest does not print
    # "0 passed" today, but a plugin or a future summary format that did would turn this guard - the
    # last thing standing between an empty run and an "OK: clean" verdict - into a no-op.
    result = _run(repo_root, tmp_path, "==== 0 passed, 71 skipped in 0.4s ====\n")
    assert result.returncode == 1
    assert "zero real passes" in result.stderr


def test_a_nonzero_pytest_exit_is_propagated_unchanged(repo_root: Path, tmp_path: Path) -> None:
    result = _run(repo_root, tmp_path, "==== 1 failed in 1.0s ====\n", pytest_exit=2)
    assert result.returncode == 2, "the caller must see pytest's own exit code, not a flattened 1"


def test_a_collect_only_invocation_skips_the_accounting_entirely(repo_root: Path, tmp_path: Path) -> None:
    # A no-hardware collection pass legitimately has zero passes and zero skips; running the
    # accounting against it would make the documented "collectible with nothing attached" check fail.
    result = _run(repo_root, tmp_path, "collected 71 items\n", "--collect-only")
    assert result.returncode == 0, result.stderr
    assert "OK:" not in result.stdout, "a collect-only run must not claim a clean hardware verdict"
