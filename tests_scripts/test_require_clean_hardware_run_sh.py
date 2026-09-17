"""Drives scripts/_require_clean_hardware_run.sh's verdict logic against canned pytest output, via a
stub `uv` on PATH. Its whole job is deciding whether a real-hardware run was genuinely clean, and
every branch of that decision is invisible to any run this session is allowed to make."""

import os
import subprocess
from pathlib import Path

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


def test_a_gated_skip_is_accepted_without_its_flag_and_rejected_with_it(repo_root: Path, tmp_path: Path) -> None:
    # The contextual half of the whitelist, and the easiest to break by promoting an entry to
    # unconditional: passing --allow-flash-cycle and STILL getting a skip means the hardware went
    # away mid-run, which is exactly what this script exists to refuse to call clean.
    log = f"{_GREEN_LINE}\ntests_hardware/flash/test_reflash.py::test_real_uf2_reflash_and_boot_smoke_test SKIPPED (opt-in)\n{_SUMMARY}\n"
    assert _run(repo_root, tmp_path, log).returncode == 0
    assert _run(repo_root, tmp_path, log, "--allow-flash-cycle").returncode == 1


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
