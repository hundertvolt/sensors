"""Structural invariants of scripts/test.sh that a plain run can't prove: the devices/*.toml glob
hazard is closed by ordering, and devices/zz_test_*.toml is a reserved live-tree fixture namespace.
Both are ordering/naming contracts, so they are asserted against the script's own source."""

import re
import subprocess
from pathlib import Path

_RESERVED_FIXTURE_PREFIX = "zz_test_"
_SWEEP_LINE = "rm -f devices/zz_test_*.toml"
_GENERATE_LINE = "uv run scripts/_generate_sensortask_modules.py"
# The `(` opening the subshell that backgrounds the pytest job - matched on the pytest invocation
# itself rather than the bare paren, which appears all over a shell script.
_PYTEST_LINE = "uv run pytest tests_scripts -q"


def _test_sh_text(repo_root: Path) -> str:
    return (repo_root / "scripts" / "test.sh").read_text()


def test_buildgen_generation_runs_before_the_pytest_job_is_backgrounded(repo_root: Path) -> None:
    # The race this ordering closes: scripts/_generate_sensortask_modules.py globs devices/*.toml,
    # while tests_scripts/test_build_website_sh.py's malformed-TOML case writes a throwaway
    # devices/zz_test_*.toml into the live tree for the length of one test (it cannot be given a
    # tmp_path tree - build_website.sh resolves devices/<device>.toml from the repo root). Generated
    # first, that file's brief existence is never observed; backgrounded first, a glob landing inside
    # that window exits 1 and aborts the whole run under `set -e`, naming a device nobody added.
    text = _test_sh_text(repo_root)
    generate_at = text.find(_GENERATE_LINE)
    pytest_at = text.find(_PYTEST_LINE)
    assert generate_at != -1, f"scripts/test.sh no longer runs {_GENERATE_LINE!r} - update this test with it"
    assert pytest_at != -1, f"scripts/test.sh no longer runs {_PYTEST_LINE!r} - update this test with it"
    assert generate_at < pytest_at, "scripts/test.sh must generate the buildgen device modules BEFORE backgrounding tests_scripts/ - see that block's own devices/*.toml race comment"


def test_stale_live_tree_fixtures_are_swept_before_anything_globs_devices(repo_root: Path) -> None:
    # The sweep covers the leak the ordering above cannot: the fixture test removes its file in
    # `finally`, which a SIGKILL (the pytest job is timeout-wrapped) defeats. A leaked file breaks
    # every later scripts/test.sh, scripts/typecheck.sh and twin run at the generation step, so the
    # sweep has to run ahead of that step, not merely somewhere in the script.
    text = _test_sh_text(repo_root)
    sweep_at = text.find(_SWEEP_LINE)
    assert sweep_at != -1, f"scripts/test.sh must sweep stale live-tree fixtures via {_SWEEP_LINE!r}"
    assert sweep_at < text.find(_GENERATE_LINE), "the devices/zz_test_*.toml sweep must run before the buildgen generation step that globs devices/*.toml"


def test_the_live_tree_fixture_test_uses_the_reserved_prefix(repo_root: Path) -> None:
    # The sweep above is only sound if every test that writes into the real devices/ directory names
    # its file inside the reserved namespace. Checked against the real source rather than trusting a
    # comment: a second such fixture added under some other name would be swept by nothing.
    text = (repo_root / "tests_scripts" / "test_build_website_sh.py").read_text()
    # Only paths that are actually WRITTEN count - the same `repo_root / "devices" / f"{device}.toml"`
    # expression is read-only all over tests_scripts/, and flagging those would make this guard fire
    # on a perfectly safe addition instead of on a real one.
    written = [(path_var, name_var) for path_var, name_var in re.findall(r'(\w+) = repo_root / "devices" / f"\{(\w+)\}\.toml"', text) if f"{path_var}.write_text(" in text]
    assert written, "test_build_website_sh.py no longer writes a devices/<device>.toml - update this test, or drop the sweep in scripts/test.sh if nothing writes there any more"
    for path_var, name_var in written:
        assigned = re.findall(rf'^\s*{name_var} = "([^"]+)"', text, re.MULTILINE)
        assert assigned, f"couldn't resolve the device name behind the written path {path_var!r}"
        for name in assigned:
            assert name.startswith(_RESERVED_FIXTURE_PREFIX), f"a fixture written into the live devices/ tree must be named {_RESERVED_FIXTURE_PREFIX}* so scripts/test.sh's sweep can reclaim it after a kill, got {name!r}"


def test_a_leaked_fixture_is_reclaimed_at_session_start_too(repo_root: Path) -> None:
    # The sweep in scripts/test.sh only helps runs that go through scripts/test.sh. conftest.py
    # reclaims the same namespace at pytest session start, which covers a direct `pytest
    # tests_scripts` run and - unlike any test that globs the live tree - cannot race the fixture
    # that legitimately creates one mid-session, because at session start nothing has created it yet.
    # Asserted structurally rather than by globbing devices/ here, for exactly that reason.
    conftest = (repo_root / "tests_scripts" / "conftest.py").read_text()
    assert "_reclaim_leaked_device_fixtures" in conftest, "conftest.py must reclaim leaked live-tree device fixtures at session start"
    assert 'glob("zz_test_*.toml")' in conftest, "the session-start reclamation must target the reserved namespace"
    assert "autouse=True" in conftest, "the reclamation fixture must be autouse - nothing requests it by name"


# ---------------------------------------------------------------------------
# TEST_PARALLELISM autodetection. Executed for real against stub interpreters rather than asserted
# structurally: the whole point of the probe is what it DOES on a slow host, and the bench Pi4 that
# motivated it (BACKLOG.md item 28) is not reachable from here.
# ---------------------------------------------------------------------------


def _run_detector(repo_root: Path, tmp_path: Path, probe_sleep_s: float) -> tuple[int, int, int, int]:
    """Runs scripts/test.sh's own _detect_parallelism() against a stub interpreter of chosen speed."""
    body = re.search(r"^_detect_parallelism\(\) \{.*?^\}", _test_sh_text(repo_root), re.DOTALL | re.MULTILINE)
    assert body is not None, "scripts/test.sh no longer defines _detect_parallelism() - update this test with it"
    stub = tmp_path / "stub_interpreter"
    stub.write_text(f"#!/bin/sh\nsleep {probe_sleep_s}\n")
    stub.chmod(0o755)
    script = tmp_path / "probe.sh"
    script.write_text(f'#!/usr/bin/env bash\nset -uo pipefail\nmicropython_bin="{stub}"\n{body.group(0)}\n_detect_parallelism\n')
    out = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=True).stdout.split()
    jobs, cores, multiplier, probe_ms = (int(v) for v in out)
    return jobs, cores, multiplier, probe_ms


def test_a_fast_host_keeps_the_original_four_times_multiplier(repo_root: Path, tmp_path: Path) -> None:
    jobs, cores, multiplier, probe_ms = _run_detector(repo_root, tmp_path, 0.0)
    assert multiplier == 4, f"a ~0ms probe must stay on the pre-autodetection 4x default (probe {probe_ms}ms)"
    assert jobs == cores * 4


def test_a_bench_pi4_class_host_drops_to_two_times(repo_root: Path, tmp_path: Path) -> None:
    # ~700ms is the class the real Pi4 lands in: 4 cores, but cores slow enough that 16 concurrent
    # Unix-port processes starve a twin test's real-time budget.
    jobs, cores, multiplier, _ = _run_detector(repo_root, tmp_path, 0.7)
    assert multiplier == 2
    assert jobs == cores * 2


def test_a_genuinely_slow_host_drops_to_one_times(repo_root: Path, tmp_path: Path) -> None:
    jobs, cores, multiplier, _ = _run_detector(repo_root, tmp_path, 1.0)
    assert multiplier == 1
    assert jobs == cores


def test_a_broken_probe_falls_back_to_the_previous_behaviour_rather_than_going_slow(repo_root: Path, tmp_path: Path) -> None:
    # A missing/unusable interpreter must not silently halve everyone's parallelism - the probe is an
    # optimisation, and its own failure is never allowed to change the answer from what it was before.
    body = re.search(r"^_detect_parallelism\(\) \{.*?^\}", _test_sh_text(repo_root), re.DOTALL | re.MULTILINE)
    assert body is not None
    script = tmp_path / "probe_broken.sh"
    script.write_text(f'#!/usr/bin/env bash\nset -uo pipefail\nmicropython_bin="{tmp_path}/does_not_exist"\n{body.group(0)}\n_detect_parallelism\n')
    out = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=True).stdout.split()
    assert int(out[2]) == 4, f"a broken probe must fall back to 4x, got {out}"


def test_the_env_override_still_wins_over_autodetection(repo_root: Path) -> None:
    # The documented escape hatch the bench Pi4 uses if the probe ever misjudges it.
    text = _test_sh_text(repo_root)
    override_at = text.find('if [ -n "${TEST_PARALLELISM:-}" ]; then')
    assert override_at != -1, "scripts/test.sh must still honour a TEST_PARALLELISM override"
    assert text.find("_detect_parallelism)", override_at) > override_at, "autodetection must sit in the else branch, never ahead of the override"
