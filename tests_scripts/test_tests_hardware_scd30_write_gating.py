"""Verifies tests_hardware/conftest.py's SCD30 write-gating: --allow-scd30-writes is the single
global permission for any real SCD30 write, and --allow-scd30-extra-write only narrows that further
(AND-gated), never substitutes for it. Drives a real --collect-only subprocess - needs no hardware."""

import subprocess
import sys
from pathlib import Path

_TARGET = "tests_hardware/flash/test_bus_concurrency.py"
_ROUTINE_TEST = "test_same_device_concurrent_sessions_never_corrupt_each_other"
_EXTRA_TEST = "test_scd30_config_write_does_not_disturb_concurrent_sibling_reads"
_NON_SCD30_TEST = "test_bmp3xx_same_device_read_write_concurrency"


def _collect(repo_root: Path, *extra_args: str) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", _TARGET, "--collect-only", "-q", *extra_args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"collection itself failed:\n{result.stdout}\n{result.stderr}"
    return result.stdout


def test_no_flags_deselects_every_real_scd30_write_test_but_keeps_the_rest(repo_root: Path) -> None:
    output = _collect(repo_root)
    assert _ROUTINE_TEST not in output, "routine-group SCD30 write test ran without --allow-scd30-writes"
    assert _EXTRA_TEST not in output, "extra-write SCD30 test ran without either flag"
    assert _NON_SCD30_TEST in output, "a test with no SCD30 write dependency was wrongly deselected"
    assert "7 deselected" in output, f"expected exactly 7 deselected (every scd30_write-marked test):\n{output}"


def test_global_flag_alone_runs_the_routine_group_but_not_the_extra_test(repo_root: Path) -> None:
    output = _collect(repo_root, "--allow-scd30-writes")
    assert _ROUTINE_TEST in output, "--allow-scd30-writes must let the routine group run"
    assert _EXTRA_TEST not in output, "the extra-write test must still deselect without --allow-scd30-extra-write"
    assert "1 deselected" in output, f"expected exactly 1 deselected (only the extra-write test):\n{output}"


def test_extra_flag_alone_without_the_global_flag_still_deselects_everything(repo_root: Path) -> None:
    # The AND-gate itself: --allow-scd30-extra-write must never substitute for --allow-scd30-writes.
    output = _collect(repo_root, "--allow-scd30-extra-write")
    assert _ROUTINE_TEST not in output, "--allow-scd30-extra-write alone must not grant the global write permission"
    assert _EXTRA_TEST not in output, "the extra-write test must not run without --allow-scd30-writes too"
    assert "7 deselected" in output, f"expected the same 7 deselected as the no-flags case:\n{output}"


def test_both_flags_runs_every_real_scd30_write_test(repo_root: Path) -> None:
    output = _collect(repo_root, "--allow-scd30-writes", "--allow-scd30-extra-write")
    assert _ROUTINE_TEST in output
    assert _EXTRA_TEST in output
    assert "deselected" not in output, f"expected zero deselections with both flags passed:\n{output}"
