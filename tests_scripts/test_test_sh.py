"""Structural invariants of scripts/test.sh that a plain run can't prove: the devices/*.toml glob
hazard is closed by ordering, and devices/zz_test_*.toml is a reserved live-tree fixture namespace.
Both are ordering/naming contracts, so they are asserted against the script's own source."""

import re
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest
from _script_loader import load_script_module

if TYPE_CHECKING:
    from collections.abc import Callable

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


def _run_detector_with_cgroup(repo_root: Path, tmp_path: Path, cpu_max: str) -> tuple[int, int, int, int]:
    """Same probe, with the cgroup v2 quota file redirected at a canned one - the real
    /sys/fs/cgroup/cpu.max is whatever this run happens to sit in and cannot be varied."""
    body = re.search(r"^_detect_parallelism\(\) \{.*?^\}", _test_sh_text(repo_root), re.DOTALL | re.MULTILINE)
    assert body is not None
    cpu_file = tmp_path / "cpu.max"
    cpu_file.write_text(cpu_max)
    stub = tmp_path / "fast_interpreter"
    stub.write_text("#!/bin/sh\nexit 0\n")
    stub.chmod(0o755)
    # Asserted rather than assumed: a silent no-op replacement would leave the probe reading the real
    # /sys/fs/cgroup/cpu.max of whatever this run sits in, and every case below would test the host.
    redirected = body.group(0).replace("/sys/fs/cgroup/cpu.max", str(cpu_file))
    assert redirected != body.group(0), "scripts/test.sh no longer reads /sys/fs/cgroup/cpu.max - update this redirection with it"
    script = tmp_path / "probe_cgroup.sh"
    script.write_text(f'#!/usr/bin/env bash\nset -uo pipefail\nmicropython_bin="{stub}"\n{redirected}\n_detect_parallelism\n')
    jobs, cores, multiplier, probe_ms = (int(v) for v in subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=True).stdout.split())
    return jobs, cores, multiplier, probe_ms


def test_a_cpu_quota_below_the_core_count_clamps_the_job_count(repo_root: Path, tmp_path: Path) -> None:
    # nproc reports the HOST's cores inside a quota-limited container, so an unclamped 4x would
    # oversubscribe a 1-core slice sixteen-fold - the same starvation the multiplier exists to avoid,
    # arriving from the other direction. 100000/100000 is one core's worth.
    _jobs, cores, _multiplier, _probe = _run_detector_with_cgroup(repo_root, tmp_path, "100000 100000\n")
    assert cores == 1, f"a one-core quota must clamp the usable core count, got {cores}"


def test_a_fractional_quota_rounds_up_rather_than_down_to_zero(repo_root: Path, tmp_path: Path) -> None:
    # Half a core is still a core to run on; rounding down would yield 0 usable cores and, with the
    # multiplier applied, a job count of 0 - which is the value the >= 1 clamp below exists to catch.
    _jobs, cores, _multiplier, _probe = _run_detector_with_cgroup(repo_root, tmp_path, "50000 100000\n")
    assert cores == 1


def test_an_unlimited_or_malformed_quota_leaves_the_core_count_alone(repo_root: Path, tmp_path: Path) -> None:
    # cgroup v1 hosts, and an unconstrained v2 one, must read exactly as they did before the clamp.
    unlimited = _run_detector_with_cgroup(repo_root, tmp_path, "max 100000\n")[1]
    malformed = _run_detector_with_cgroup(repo_root, tmp_path, "not-a-number 0\n")[1]
    assert unlimited == malformed >= 1, f"neither an unlimited nor a malformed cpu.max may change the core count ({unlimited} vs {malformed})"


def _resolved_parallelism(repo_root: Path, tmp_path: Path, env_value: str | None) -> int:
    """Runs the real override/clamp block with _detect_parallelism() stubbed to a known answer."""
    text = _test_sh_text(repo_root)
    start = text.index('if [ -n "${TEST_PARALLELISM:-}" ]; then')
    end = text.index("    max_parallel=1\nfi\n", start) + len("    max_parallel=1\nfi\n")
    script = tmp_path / "resolve.sh"
    script.write_text('#!/usr/bin/env bash\nset -uo pipefail\n_detect_parallelism() { echo "8 4 2 300"; }\n' + text[start:end] + 'echo "RESOLVED=$max_parallel"\n')
    env = {"PATH": "/usr/bin:/bin"} | ({} if env_value is None else {"TEST_PARALLELISM": env_value})
    out = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=True, env=env).stdout
    return int(out.rsplit("RESOLVED=", 1)[1].strip())


def test_an_unset_or_empty_override_uses_the_detected_value(repo_root: Path, tmp_path: Path) -> None:
    # Empty is not zero: `-n ""` is false, so an exported-but-blank variable means "autodetect", not
    # "sequential". Pinned because the clamp below would otherwise look like the branch handling it.
    assert _resolved_parallelism(repo_root, tmp_path, None) == 8
    assert _resolved_parallelism(repo_root, tmp_path, "") == 8


def test_a_zero_or_negative_override_falls_back_to_sequential_instead_of_hanging(repo_root: Path, tmp_path: Path) -> None:
    # Not cosmetic: the dispatch loop blocks while the running count is >= max_parallel, so 0 makes
    # `wait -n || true` spin forever without dispatching anything. A hang is precisely what
    # CLAUDE.md's standing backstop forbids, and "turn parallelism off" is a plausible reason to try 0.
    for value in ("0", "-1", "abc", "2.5"):
        assert _resolved_parallelism(repo_root, tmp_path, value) == 1, f"TEST_PARALLELISM={value!r} must clamp to 1, not hang the dispatch loop"


def test_a_valid_override_is_honoured_verbatim(repo_root: Path, tmp_path: Path) -> None:
    assert _resolved_parallelism(repo_root, tmp_path, "3") == 3


def test_a_broken_probe_falls_back_to_the_previous_behaviour_rather_than_going_slow(repo_root: Path, tmp_path: Path) -> None:
    # A missing/unusable interpreter must not silently halve everyone's parallelism - the probe is an
    # optimisation, and its own failure is never allowed to change the answer from what it was before.
    body = re.search(r"^_detect_parallelism\(\) \{.*?^\}", _test_sh_text(repo_root), re.DOTALL | re.MULTILINE)
    assert body is not None
    script = tmp_path / "probe_broken.sh"
    script.write_text(f'#!/usr/bin/env bash\nset -uo pipefail\nmicropython_bin="{tmp_path}/does_not_exist"\n{body.group(0)}\n_detect_parallelism\n')
    out = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=True).stdout.split()
    assert int(out[2]) == 4, f"a broken probe must fall back to 4x, got {out}"


def test_the_speed_probe_runs_before_the_pytest_job_loads_the_host(repo_root: Path) -> None:
    # The placement bug this pins, found 2026-09-18: the probe timed a real process on a real host,
    # but sat 262 lines AFTER the tests_scripts/ background launch - so it measured the host with
    # pytest already saturating every core, not the host's own capability. Measured on this
    # project's 4-core x86 sandbox: 131-141ms across 8 idle samples versus 391ms in situ, i.e. 2x/8
    # jobs where the host warrants 4x/16, and non-deterministic run to run. Every unit test in this
    # section runs the extracted function in isolation on an idle machine, so none of them can see
    # this - only the ordering can, which is why it is asserted here rather than left to a comment.
    text = _test_sh_text(repo_root)
    probe_at = text.find("_detect_parallelism() {")
    resolved_at = text.find('if [ -n "${TEST_PARALLELISM:-}" ]; then')
    pytest_at = text.find(_PYTEST_LINE)
    assert probe_at != -1 and resolved_at != -1, "scripts/test.sh no longer resolves the parallelism here - update this test with it"
    assert pytest_at != -1, f"scripts/test.sh no longer runs {_PYTEST_LINE!r} - update this test with it"
    assert resolved_at < pytest_at, "scripts/test.sh must resolve TEST_PARALLELISM BEFORE backgrounding tests_scripts/ - the speed probe otherwise measures that job's own CPU load instead of the host"


def test_the_env_override_still_wins_over_autodetection(repo_root: Path) -> None:
    # The documented escape hatch the bench Pi4 uses if the probe ever misjudges it.
    text = _test_sh_text(repo_root)
    override_at = text.find('if [ -n "${TEST_PARALLELISM:-}" ]; then')
    assert override_at != -1, "scripts/test.sh must still honour a TEST_PARALLELISM override"
    assert text.find("_detect_parallelism)", override_at) > override_at, "autodetection must sit in the else branch, never ahead of the override"


# ---------------------------------------------------------------------------
# _cleanup() - the EXIT trap. Regression test for a real defect: bash does not kill its background
# jobs when the parent exits, so an abort between the pytest launch and the final `wait` orphaned
# the job for up to its own 1200s timeout - and that orphan transiently writes a
# devices/zz_test_*.toml into the live tree, re-opening the very glob hazard the ordering closes.
# Driven against real processes, because the whole question is whether a child actually dies.
# ---------------------------------------------------------------------------


def _cleanup_body(repo_root: Path) -> str:
    """scripts/test.sh's own _cleanup(), source text only - comments stripped, since this function's
    own comment names the very mechanisms (pkill) the checks below require it not to USE."""
    body = re.search(r"^_cleanup\(\) \{.*?^\}", _test_sh_text(repo_root), re.DOTALL | re.MULTILINE)
    assert body is not None, "scripts/test.sh no longer defines _cleanup() - update this test with it"
    return body.group(0)


def _without_comments(shell_source: str) -> str:
    return "\n".join(line for line in shell_source.splitlines() if not line.lstrip().startswith("#"))


def _run_cleanup_probe(repo_root: Path, tmp_path: Path, *, arm_trap: bool) -> bool:
    """Reproduces the launch-then-abort pattern; returns True if the inner child survived. Output
    is discarded, not piped: a captured pipe is inherited by the background job, so the parent's
    exit would not be observable until that job ended - which is the survival being measured."""
    pidfile = tmp_path / "inner.pid"
    # A second copy, outside the set the trap removes: _cleanup() deletes its own pidfile, so the
    # armed arm would otherwise leave the probe with no pid left to ask about.
    observed = tmp_path / "observed.pid"
    script = tmp_path / "abort.sh"
    trap_line = "trap _cleanup EXIT" if arm_trap else ":"
    script.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f'raw_dir=""\nresults_dir=""\ntests_scripts_status_file="{tmp_path}/status"\n'
        f'tests_scripts_pid=""\ntests_scripts_inner_pidfile="{pidfile}"\n'
        f"{_cleanup_body(repo_root)}\n{trap_line}\n"
        f'( sleep 120 & inner=$!; echo "$inner" >"{observed}"; echo "$inner" >"$tests_scripts_inner_pidfile"; wait $inner ) >/dev/null 2>&1 &\n'
        "tests_scripts_pid=$!\n"
        'until [ -s "$tests_scripts_inner_pidfile" ]; do sleep 0.05; done\n'
        "false  # the abort under test: `set -e` takes the parent down mid-run\n",
    )
    done = subprocess.run(["/bin/bash", str(script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=60)
    assert done.returncode != 0, "the probe parent must actually abort - otherwise neither arm proves anything"
    inner = observed.read_text().strip()
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if subprocess.run(["/bin/kill", "-0", inner], capture_output=True, check=False).returncode != 0:
            return False  # reaped by the trap
        time.sleep(0.1)
    subprocess.run(["/bin/kill", "-9", inner], capture_output=True, check=False)
    return True


def test_without_the_trap_the_background_child_outlives_an_aborted_run(repo_root: Path, tmp_path: Path) -> None:
    # Establishes the defect is real rather than theoretical - without this arm, the next test
    # proves nothing (a child that would have died anyway looks like a working cleanup).
    assert _run_cleanup_probe(repo_root, tmp_path, arm_trap=False) is True


def test_the_exit_trap_kills_the_background_child_on_an_aborted_run(repo_root: Path, tmp_path: Path) -> None:
    assert _run_cleanup_probe(repo_root, tmp_path, arm_trap=True) is False


def test_the_cleanup_reaches_the_inner_child_without_needing_pkill(repo_root: Path) -> None:
    # procps is absent from a --variant=minbase chroot, so the cleanup records the inner pid and
    # signals it directly. A reintroduced pkill would work here but silently no-op there.
    cleanup = _without_comments(_cleanup_body(repo_root))
    assert "pkill" not in cleanup, "cleanup must not depend on pkill - a minbase chroot has no procps"
    assert "pgrep" not in cleanup, "same reason as pkill: procps is absent from a minbase chroot"
    assert "tests_scripts_inner_pidfile" in cleanup, "cleanup must signal the recorded inner pid"


def test_the_reaped_pid_is_cleared_so_the_trap_cannot_signal_a_recycled_one(repo_root: Path) -> None:
    text = _test_sh_text(repo_root)
    wait_at = text.find("\nwait || true\n")
    assert wait_at != -1, "the dispatch loop's final `wait` is gone - update this test with it"
    assert 'tests_scripts_pid=""' in text[wait_at:wait_at + 300], "the pid must be cleared right after it is reaped"


# ---------------------------------------------------------------------------
# conftest.py's own session-start reclamation. The structural check above pins that it exists and
# targets the reserved namespace; this drives the real function against a throwaway tree, because
# what matters is WHICH files it deletes - a glob one character wider would reclaim a real device.
# ---------------------------------------------------------------------------


def test_the_session_start_reclamation_deletes_only_the_reserved_namespace(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The biting half: `devices/` holds the real per-device TOMLs the whole build chain reads, and
    # this fixture runs unconditionally on every `pytest tests_scripts` invocation. A widened glob
    # would delete a committed device and only surface a build directory later.
    devices = tmp_path / "devices"
    devices.mkdir()
    leaked = devices / "zz_test_broken.toml"
    real = devices / "dev.toml"
    lookalike = devices / "zz_tests_not_ours.toml"
    for path in (leaked, real, lookalike):
        path.write_text("# fixture\n")

    conftest = load_script_module(repo_root / "tests_scripts" / "conftest.py", "_tests_scripts_conftest_under_test")
    monkeypatch.setattr(conftest, "REPO_ROOT", tmp_path)
    cast("Callable[[], None]", conftest._reclaim_leaked_device_fixtures.__wrapped__)()

    assert not leaked.exists(), "a leaked zz_test_*.toml must be reclaimed at session start"
    assert real.exists(), "the reclamation must never touch a real device TOML"
    assert lookalike.exists(), "the reclamation must not widen past the zz_test_ prefix"


def test_the_session_start_reclamation_is_a_no_op_on_a_clean_tree(repo_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The common case, and the one that must not raise: it runs before every single test in this
    # suite, so an exception here (a missing devices/ directory included) fails everything at once.
    conftest = load_script_module(repo_root / "tests_scripts" / "conftest.py", "_tests_scripts_conftest_under_test")
    monkeypatch.setattr(conftest, "REPO_ROOT", tmp_path)
    cast("Callable[[], None]", conftest._reclaim_leaked_device_fixtures.__wrapped__)()  # no devices/ at all
    (tmp_path / "devices").mkdir()
    cast("Callable[[], None]", conftest._reclaim_leaked_device_fixtures.__wrapped__)()  # empty devices/
