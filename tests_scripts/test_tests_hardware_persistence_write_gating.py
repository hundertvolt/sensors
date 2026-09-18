"""Verifies tests_hardware/conftest.py's persistence-write gating: --allow-persistence-writes is the
single global permission for any limited-endurance write (SCD30 NVM and the RP2040 flash filesystem
alike), --allow-scd30-extra-write only narrows further. Real --collect-only run, no hardware."""

import subprocess
import sys
from pathlib import Path

_TARGET = "tests_hardware/flash/test_bus_concurrency.py"
_ROUTINE_TEST = "test_same_device_concurrent_sessions_never_corrupt_each_other"
_EXTRA_TEST = "test_scd30_config_write_does_not_disturb_concurrent_sibling_reads"
_NON_SCD30_TEST = "test_bmp3xx_same_device_read_write_concurrency"


def _collect(repo_root: Path, *extra_args: str, target: str = _TARGET) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", target, "--collect-only", "-q", *extra_args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"collection itself failed:\n{result.stdout}\n{result.stderr}"
    return result.stdout


def test_no_flags_deselects_every_real_persistence_write_test_but_keeps_the_rest(repo_root: Path) -> None:
    output = _collect(repo_root)
    assert _ROUTINE_TEST not in output, "routine-group SCD30 write test ran without --allow-persistence-writes"
    assert _EXTRA_TEST not in output, "extra-write SCD30 test ran without either flag"
    assert _NON_SCD30_TEST in output, "a test with no SCD30 write dependency was wrongly deselected"
    assert "7 deselected" in output, f"expected exactly 7 deselected (every persistence_write-marked test):\n{output}"


def test_global_flag_alone_runs_the_routine_group_but_not_the_extra_test(repo_root: Path) -> None:
    output = _collect(repo_root, "--allow-persistence-writes")
    assert _ROUTINE_TEST in output, "--allow-persistence-writes must let the routine group run"
    assert _EXTRA_TEST not in output, "the extra-write test must still deselect without --allow-scd30-extra-write"
    assert "1 deselected" in output, f"expected exactly 1 deselected (only the extra-write test):\n{output}"


def test_extra_flag_alone_without_the_global_flag_still_deselects_everything(repo_root: Path) -> None:
    # The AND-gate itself: --allow-scd30-extra-write must never substitute for --allow-persistence-writes.
    output = _collect(repo_root, "--allow-scd30-extra-write")
    assert _ROUTINE_TEST not in output, "--allow-scd30-extra-write alone must not grant the global write permission"
    assert _EXTRA_TEST not in output, "the extra-write test must not run without --allow-persistence-writes too"
    assert "7 deselected" in output, f"expected the same 7 deselected as the no-flags case:\n{output}"


def test_both_flags_runs_every_real_persistence_write_test(repo_root: Path) -> None:
    output = _collect(repo_root, "--allow-persistence-writes", "--allow-scd30-extra-write")
    assert _ROUTINE_TEST in output
    assert _EXTRA_TEST in output
    assert "deselected" not in output, f"expected zero deselections with both flags passed:\n{output}"


# ---------------------------------------------------------------------------
# The bench tier joined this gate when it stopped being SCD30-only: every config-persisting PUT
# writes the RP2040's own flash filesystem through config_manager.py's json.dump(), which is the
# same finite-endurance class the SCD30's NVM is in. Counted, not just spot-checked, because the
# failure mode of a mis-placed marker is silent - a test that writes but is not marked spends real
# wear on a routine pass, and one marked that does not write silently loses coverage.
# ---------------------------------------------------------------------------

_BENCH = "tests_hardware/bench"


def test_the_bench_tier_deselects_exactly_its_persistence_writers_by_default(repo_root: Path) -> None:
    gated = _collect(repo_root, target=_BENCH)
    ungated = _collect(repo_root, "--allow-persistence-writes", target=_BENCH)
    assert "deselected" in gated, f"the bench tier deselected nothing by default:\n{gated}"
    assert "deselected" not in ungated, f"--allow-persistence-writes must leave the bench tier fully selected:\n{ungated}"


def test_the_dispatch_only_fields_are_not_treated_as_persistence_writes(repo_root: Path) -> None:
    # SGPResetVOC/ISLCalibrate carry `dispatch=true` in their own @web schema tag and are never in
    # ConfigManager's cache, so a test whose only PUT is one of those spends no flash cycle and must
    # stay selected by default. test_memory_stress_bench.py is exactly that case.
    gated = _collect(repo_root, target=_BENCH)
    assert "test_real_hardware_survives_max_speed_hammer_load_without_memoryerror_or_reboot" in gated, "a SGPResetVOC-only test must not be gated - it persists nothing"


_FLASH = "tests_hardware/flash"


def test_the_flash_tier_gates_its_config_writing_reboot_tests_too(repo_root: Path) -> None:
    # The counted assertions above target ONE file, so they cannot see a marker placed anywhere else
    # in the tier. These two write real config through ConfigManager.write_config() from their own
    # device scripts (reboot_persist_write.py, system_debug_level_raise_for_boot_log_check.py) - a
    # flash cycle each, and nothing to do with SCD30, which is exactly the class this gate grew to
    # cover. Named rather than counted: a count breaks on every unrelated test added to the tier.
    gated = _collect(repo_root, target=_FLASH)
    ungated = _collect(repo_root, "--allow-persistence-writes", target=_FLASH)
    for name in ("test_config_value_survives_a_genuine_hard_reset", "test_boot_import_mechanism_actually_boots_the_real_system"):
        assert name not in gated, f"{name} writes real config to flash and must be deselected without --allow-persistence-writes"
        assert name in ungated, f"{name} must run once --allow-persistence-writes is passed"
