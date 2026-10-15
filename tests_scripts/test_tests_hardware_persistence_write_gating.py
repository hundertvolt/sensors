"""Verifies tests_hardware/conftest.py's persistence-write gating: --allow-persistence-write is the
single global permission for any limited-endurance write (SCD30 NVM and the RP2040 flash filesystem
alike), --allow-scd30-extra-write only narrows further. Real --collect-only run, no hardware."""

import json
import os
import subprocess
import sys
from pathlib import Path

_TARGET = "tests_hardware/flash/test_bus_concurrency.py"
# The SCD30 read-while-write test owns its NVM write; the extra-write test owns two more.
_OWNED_TEST = "test_scd30_same_device_read_write_concurrency"
_EXTRA_TEST = "test_scd30_config_write_does_not_disturb_concurrent_sibling_reads"
_NON_SCD30_TEST = "test_bmp3xx_same_device_read_write_concurrency"
# They depend on the SCD30 measuring - a shared prerequisite, never a write of their own - so they run by default.
_SCD30_DEPENDENTS = (
    "test_same_device_concurrent_sessions_never_corrupt_each_other",
    "test_cross_device_concurrent_sessions_genuinely_interleave",
    "test_sgp40_general_call_reset_does_not_corrupt_concurrent_scd30_and_isl29125_transactions",
    "test_isl29125_cross_device_concurrency_with_its_i2c1_neighbours",
    "test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads",
)


def _collect(repo_root: Path, *extra_args: str, target: str = _TARGET, env: "dict[str, str] | None" = None) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", target, "--collect-only", "-q", *extra_args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, f"collection itself failed:\n{result.stdout}\n{result.stderr}"
    return result.stdout


def test_no_flags_deselects_every_real_persistence_write_test_but_keeps_the_rest(repo_root: Path) -> None:
    output = _collect(repo_root)
    assert _OWNED_TEST not in output, "the SCD30 read-while-write test ran without --allow-persistence-write"
    assert _EXTRA_TEST not in output, "extra-write SCD30 test ran without either flag"
    assert _NON_SCD30_TEST in output, "a test with no SCD30 write dependency was wrongly deselected"
    assert "2 deselected" in output, f"expected exactly 2 deselected (the two tests owning an SCD30 write):\n{output}"
    missing = [name for name in _SCD30_DEPENDENTS if name not in output]
    assert not missing, f"deselected though they only need the SCD30 measuring, a shared prerequisite: {missing}"


def test_global_flag_alone_runs_the_routine_group_but_not_the_extra_test(repo_root: Path) -> None:
    output = _collect(repo_root, "--allow-persistence-write")
    assert _OWNED_TEST in output, "--allow-persistence-write must let the owned SCD30 write run"
    assert _EXTRA_TEST not in output, "the extra-write test must still deselect without --allow-scd30-extra-write"
    assert "1 deselected" in output, f"expected exactly 1 deselected (only the extra-write test):\n{output}"


def test_extra_flag_alone_without_the_global_flag_still_deselects_everything(repo_root: Path) -> None:
    # The AND-gate itself: --allow-scd30-extra-write must never substitute for --allow-persistence-write.
    output = _collect(repo_root, "--allow-scd30-extra-write")
    assert _OWNED_TEST not in output, "--allow-scd30-extra-write alone must not grant the global write permission"
    assert _EXTRA_TEST not in output, "the extra-write test must not run without --allow-persistence-write too"
    assert "2 deselected" in output, f"expected the same 2 deselected as the no-flags case:\n{output}"


def test_both_flags_runs_every_real_persistence_write_test(repo_root: Path) -> None:
    output = _collect(repo_root, "--allow-persistence-write", "--allow-scd30-extra-write")
    assert _OWNED_TEST in output
    assert _EXTRA_TEST in output
    assert "deselected" not in output, f"expected zero deselections with both flags passed:\n{output}"


# ---------------------------------------------------------------------------
# The bench tier joined this gate once it stopped being SCD30-only: every config-persisting PUT
# writes the RP2040's flash filesystem, the same finite-endurance class. Counted rather than
# spot-checked, since a misplaced marker fails silently in both directions.
# ---------------------------------------------------------------------------

_BENCH = "tests_hardware/bench"


def _nodeids(output: str) -> "set[str]":
    return {line for line in output.splitlines() if "::" in line}


def test_the_bench_tier_deselects_exactly_its_persistence_writers_by_default(repo_root: Path) -> None:
    gated = _collect(repo_root, target=_BENCH)
    both = _collect(repo_root, "--allow-persistence-write", "--allow-scd30-extra-write", target=_BENCH)
    assert "deselected" in gated, f"the bench tier deselected nothing by default:\n{gated}"
    assert "deselected" not in both, f"both flags must leave the bench tier fully selected:\n{both}"
    # The global flag alone leaves out exactly the bench's SCD30 extra-write tests: the AND-gate, read by marker.
    still_gated = _nodeids(both) - _nodeids(_collect(repo_root, "--allow-persistence-write", target=_BENCH))
    extra = _nodeids(_collect(repo_root, "--allow-persistence-write", "--allow-scd30-extra-write", "-m", "scd30_extra_write", target=_BENCH))
    assert still_gated and still_gated == extra, f"--allow-persistence-write alone left out {sorted(still_gated)}, the scd30_extra_write tests are {sorted(extra)}"


def test_the_dispatch_only_fields_are_not_treated_as_persistence_writes(repo_root: Path) -> None:
    # ResetVOC/Calibrate carry `dispatch=true` in their own @web schema tag and are never in
    # ConfigManager's cache, so a test whose only PUT is one of those spends no flash cycle and must
    # stay selected by default. test_memory_stress_bench.py is exactly that case.
    gated = _collect(repo_root, target=_BENCH)
    assert "test_real_hardware_survives_max_speed_hammer_load_without_memoryerror_or_reboot" in gated, "a ResetVOC-only test must not be gated - it persists nothing"


_FLASH = "tests_hardware/flash"


def test_the_flash_tier_gates_its_config_writing_reboot_tests_too(repo_root: Path) -> None:
    # The counted assertions above target ONE file and cannot see a marker elsewhere in the tier. The hard-reset test
    # writes real config from its device script, a flash cycle, nothing to do with SCD30; the boot check writes nothing
    # (its script only reads), so it runs by default. Named rather than counted, a count breaking on every addition.
    gated = _collect(repo_root, target=_FLASH)
    ungated = _collect(repo_root, "--allow-persistence-write", target=_FLASH)
    name = "test_config_value_survives_a_genuine_hard_reset"
    assert name not in gated, f"{name} writes real config to flash and must be deselected without --allow-persistence-write"
    assert name in ungated, f"{name} must run once --allow-persistence-write is passed"
    assert "test_boot_import_mechanism_actually_boots_the_real_system" in gated, "the boot check writes nothing and must run by default"


# Reads each deselected item's user_properties at the moment the conftest hands it to pytest, so the
# property is checked here and the run record that carries it is checked on its own.
_DESELECTION_PROBE = """
import json

def pytest_deselected(items):
    for item in items:
        print("DESELECTED_BY " + json.dumps([item.nodeid, [list(p) for p in item.user_properties if p[0] == "deselected_by"]]))
"""


def _deselected_by(repo_root: Path, tmp_path: Path, *extra_args: str) -> "dict[str, list[str]]":
    (tmp_path / "_deselection_probe.py").write_text(_DESELECTION_PROBE)
    env = dict(os.environ, PYTHONPATH=f"{tmp_path}{os.pathsep}{os.environ.get('PYTHONPATH', '')}")
    output = _collect(repo_root, "-p", "_deselection_probe", "-s", *extra_args, target=_TARGET, env=env)
    found: dict[str, list[str]] = {}
    for line in output.splitlines():
        if line.startswith("DESELECTED_BY "):
            nodeid, props = json.loads(line[len("DESELECTED_BY ") :])
            found[nodeid.rsplit("::", 1)[-1]] = [flag for _, flag in props]
    return found


def test_every_wear_gate_deselection_carries_the_flag_that_would_select_it(repo_root: Path, tmp_path: Path) -> None:
    # The run record tells a wear-gate deselection apart from a runner's -m exclusion only through
    # this tag: an untagged one would read as "runner selection" and its advice would name no flag.
    tags = _deselected_by(repo_root, tmp_path)
    assert sorted(tags) == sorted([_OWNED_TEST, _EXTRA_TEST]), f"expected the 2 persistence_write deselections, probe saw {sorted(tags)}"
    # One tag each, the global flag first: without it no flag of this gate selects anything.
    assert all(flags == ["--allow-persistence-write"] for flags in tags.values()), tags


def test_the_extra_write_deselection_names_its_own_flag_once_the_global_one_is_given(repo_root: Path, tmp_path: Path) -> None:
    tags = _deselected_by(repo_root, tmp_path, "--allow-persistence-write")
    assert tags == {_EXTRA_TEST: ["--allow-scd30-extra-write"]}, tags
