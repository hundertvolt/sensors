"""Verifies tests_hardware/conftest.py's persistence-write gating: --allow-persistence-writes permits every
limited-endurance write, --allow-persistence-writes-to only the named groups, --allow-scd30-extra-write
narrows further on top of either. Real --collect-only run, no hardware."""

import json
import os
import subprocess
import sys
from pathlib import Path

_TARGET = "tests_hardware/flash/test_bus_concurrency.py"
_ROUTINE_TEST = "test_same_device_concurrent_sessions_never_corrupt_each_other"
_EXTRA_TEST = "test_scd30_config_write_does_not_disturb_concurrent_sibling_reads"
_NON_SCD30_TEST = "test_bmp3xx_same_device_read_write_concurrency"


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
# The bench tier joined this gate once it stopped being SCD30-only: every config-persisting PUT
# writes the RP2040's flash filesystem, the same finite-endurance class. Counted rather than
# spot-checked, since a misplaced marker fails silently in both directions.
# ---------------------------------------------------------------------------

_BENCH = "tests_hardware/bench"


def test_the_bench_tier_deselects_exactly_its_persistence_writers_by_default(repo_root: Path) -> None:
    gated = _collect(repo_root, target=_BENCH)
    ungated = _collect(repo_root, "--allow-persistence-writes", target=_BENCH)
    assert "deselected" in gated, f"the bench tier deselected nothing by default:\n{gated}"
    assert "deselected" not in ungated, f"--allow-persistence-writes must leave the bench tier fully selected:\n{ungated}"


def test_the_dispatch_only_fields_are_not_treated_as_persistence_writes(repo_root: Path) -> None:
    # ResetVOC/Calibrate carry `dispatch=true` in their own @web schema tag and are never in
    # ConfigManager's cache, so a test whose only PUT is one of those spends no flash cycle and must
    # stay selected by default. test_memory_stress_bench.py is exactly that case.
    gated = _collect(repo_root, target=_BENCH)
    assert "test_real_hardware_survives_max_speed_hammer_load_without_memoryerror_or_reboot" in gated, "a ResetVOC-only test must not be gated - it persists nothing"


_FLASH = "tests_hardware/flash"


def test_the_flash_tier_gates_its_config_writing_reboot_tests_too(repo_root: Path) -> None:
    # The counted assertions above target ONE file and cannot see a marker elsewhere in the tier.
    # These two write real config from their own device scripts - a flash cycle each, nothing to
    # do with SCD30. Named rather than counted, a count breaking on every unrelated addition.
    gated = _collect(repo_root, target=_FLASH)
    ungated = _collect(repo_root, "--allow-persistence-writes", target=_FLASH)
    for name in ("test_config_value_survives_a_genuine_hard_reset", "test_boot_import_mechanism_actually_boots_the_real_system"):
        assert name not in gated, f"{name} writes real config to flash and must be deselected without --allow-persistence-writes"
        assert name in ungated, f"{name} must run once --allow-persistence-writes is passed"


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
    assert len(tags) == 7, f"expected the 7 persistence_write deselections, probe saw {sorted(tags)}"
    # One tag each, the global flag first: without it no flag of this gate selects anything.
    assert all(flags == ["--allow-persistence-writes"] for flags in tags.values()), tags


def test_the_extra_write_deselection_names_its_own_flag_once_the_global_one_is_given(repo_root: Path, tmp_path: Path) -> None:
    tags = _deselected_by(repo_root, tmp_path, "--allow-persistence-writes")
    assert tags == {_EXTRA_TEST: ["--allow-scd30-extra-write"]}, tags


# ---------------------------------------------------------------------------
# The scoped permission (owner, 2026-10-08: "it makes absolutely no sense globally enable persistence writes,
# as writing the scd30 for mqtt tests is nonsense, so scope it correctly"): a group's writes run, no other's.
# ---------------------------------------------------------------------------

_MQTT = "tests_hardware/bench/test_mqtt_broker_faults.py"
_MQTT_WRITER = "test_the_broker_is_found_by_the_bench_hosts_local_name"


def test_a_scoped_permission_runs_its_own_groups_writes(repo_root: Path) -> None:
    gated = _collect(repo_root, target=_MQTT)
    scoped = _collect(repo_root, "--allow-persistence-writes-to=networking/mqtt", target=_MQTT)
    assert _MQTT_WRITER not in gated
    assert _MQTT_WRITER in scoped, f"--allow-persistence-writes-to=networking/mqtt must select the MQTT writer:\n{scoped}"
    assert "deselected" not in scoped, scoped


def test_a_scoped_permission_leaves_every_other_groups_writes_deselected(repo_root: Path, tmp_path: Path) -> None:
    # Under the MQTT permission the SCD30's NVM stays out of reach; each deselection names the group that would select it.
    output = _collect(repo_root, "--allow-persistence-writes-to=networking/mqtt")
    assert _ROUTINE_TEST not in output and _EXTRA_TEST not in output
    assert "7 deselected" in output, output
    tags = _deselected_by(repo_root, tmp_path, "--allow-persistence-writes-to=networking/mqtt")
    assert set(tags) and all(flags == ["--allow-persistence-writes-to=sensors/SCD30"] for flags in tags.values()), tags


def test_the_scd30_group_runs_the_routine_writes_and_the_extra_flag_still_narrows(repo_root: Path) -> None:
    scoped = _collect(repo_root, "--allow-persistence-writes-to=sensors/SCD30")
    assert _ROUTINE_TEST in scoped and _EXTRA_TEST not in scoped
    assert "1 deselected" in scoped, scoped
    both = _collect(repo_root, "--allow-persistence-writes-to=sensors/SCD30", "--allow-scd30-extra-write")
    assert "deselected" not in both, both


def test_groups_combine_by_comma_and_by_repetition(repo_root: Path) -> None:
    for args in (["--allow-persistence-writes-to=networking/mqtt,sensors/SCD30"], ["--allow-persistence-writes-to=networking/mqtt", "--allow-persistence-writes-to=sensors/SCD30"]):
        output = _collect(repo_root, *args, _MQTT)  # both modules: the SCD30 group's and the MQTT one's
        assert _MQTT_WRITER in output and _ROUTINE_TEST in output, f"{args}:\n{output}"
        assert "1 deselected" in output, f"{args}: only the extra-write test stays out:\n{output}"


def test_an_unknown_group_is_a_usage_error_not_a_silent_deselection(repo_root: Path) -> None:
    # A typo would otherwise deselect the very test the run was meant to permit, and read as a wear gate.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", _MQTT, "--collect-only", "-q", "--allow-persistence-writes-to=networking/mqqt"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4, f"expected pytest's usage-error exit 4:\n{result.stdout}\n{result.stderr}"
    assert "no such group ['networking/mqqt']" in result.stdout + result.stderr
