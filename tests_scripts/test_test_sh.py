"""Structural invariants of scripts/test.sh that a plain run can't prove: the devices/*.toml glob
hazard is closed by ordering, and devices/zz_test_*.toml is a reserved live-tree fixture namespace.
Both are ordering/naming contracts, so they are asserted against the script's own source."""

import re
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
