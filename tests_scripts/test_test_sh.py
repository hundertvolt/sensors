"""Structural invariants of scripts/test.sh that a plain run can't prove: the devices/*.toml glob
hazard is closed by ordering, and devices/zz_test_*.toml is a reserved live-tree fixture namespace.
Both are ordering/naming contracts, so they are asserted against the script's own source."""

import os
import re
import shutil
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
# Bounds on the subprocesses below: a nested scripts/test.sh run or probe, and a bash snippet.
# @tunable l0.test_sh_nested_run_timeout_s = 60
_NESTED_RUN_TIMEOUT_S = 60
# @tunable l0.test_sh_snippet_timeout_s = 30
_SNIPPET_TIMEOUT_S = 30


def _test_sh_text(repo_root: Path) -> str:
    return (repo_root / "scripts" / "test.sh").read_text()


def test_buildgen_generation_runs_before_the_pytest_job_is_backgrounded(repo_root: Path) -> None:
    # The race this ordering closes: the generator globs devices/*.toml, while the malformed-TOML
    # test writes a throwaway one into the live tree for the length of one test - it cannot use a
    # tmp_path tree, build_website.sh resolving from the repo root.

    # Generated first, that file's brief existence is never seen; backgrounded first, a glob
    # landing in that window exits 1 and aborts the run under `set -e`, naming a device nobody
    # added.
    text = _test_sh_text(repo_root)
    generate_at = text.find(_GENERATE_LINE)
    pytest_at = text.find(_PYTEST_LINE)
    assert generate_at != -1, f"scripts/test.sh no longer runs {_GENERATE_LINE!r} - update this test with it"
    assert pytest_at != -1, f"scripts/test.sh no longer runs {_PYTEST_LINE!r} - update this test with it"
    assert generate_at < pytest_at, "scripts/test.sh must generate the buildgen device modules BEFORE backgrounding tests_scripts/ - see that block's own devices/*.toml race comment"


def test_stale_live_tree_fixtures_are_swept_before_anything_globs_devices(repo_root: Path) -> None:
    # The sweep covers the leak the ordering cannot: the fixture removes its file in `finally`,
    # which a SIGKILL defeats, and a leaked file then breaks every later test.sh, typecheck.sh
    # and twin run at the generation step - so the sweep must run ahead of that step.
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
    # test.sh's sweep only helps runs that go through test.sh, so conftest.py reclaims the same
    # namespace at pytest session start - covering a direct run, and unable to race the fixture
    # that legitimately creates one, since nothing has at session start.
    conftest = (repo_root / "tests_scripts" / "conftest.py").read_text()
    assert "_reclaim_leaked_device_fixtures" in conftest, "conftest.py must reclaim leaked live-tree device fixtures at session start"
    assert 'glob("zz_test_*.toml")' in conftest, "the session-start reclamation must target the reserved namespace"
    assert "autouse=True" in conftest, "the reclamation fixture must be autouse - nothing requests it by name"


# ---------------------------------------------------------------------------
# TEST_PARALLELISM autodetection. Executed for real rather than asserted structurally: the point of
# the probe is what it DOES on a slow host, and no slow host is reachable from here. The band
# choice runs against a stubbed clock - see _run_detector_with_uptime.
# ---------------------------------------------------------------------------


def _run_detector(repo_root: Path, tmp_path: Path, probe_sleep_s: float) -> tuple[int, int, int, int]:
    # Runs scripts/test.sh's own _detect_parallelism() against a stub interpreter of chosen speed.
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


def _run_detector_with_uptime(repo_root: Path, tmp_path: Path, elapsed_ms: int, *, uptime_readable: bool = True, stepped_date: bool = False) -> tuple[tuple[int, int, int, int], str]:
    # Same detector, with /proc/uptime replaced by a canned file the stub interpreter advances by
    # exactly elapsed_ms, so probe_ms is set rather than measured. A sleeping stub cannot carry the band
    # assertions: beside the MicroPython tier, a mid-band 0.7s stub read 919-963ms on 2026-09-22.
    body = re.search(r"^_detect_parallelism\(\) \{.*?^\}", _test_sh_text(repo_root), re.DOTALL | re.MULTILINE)
    assert body is not None, "scripts/test.sh no longer defines _detect_parallelism() - update this test with it"
    case_dir = tmp_path / f"uptime_{elapsed_ms}"
    case_dir.mkdir()
    uptime = case_dir / "uptime"
    start_cs = 100_000
    if uptime_readable:
        uptime.write_text(f"{start_cs // 100}.{start_cs % 100:02d} 4000.00\n")
    end_cs = start_cs + elapsed_ms // 10
    stub = case_dir / "stub_interpreter"
    stub.write_text(f'#!/bin/sh\n[ -f "{uptime}" ] && echo "{end_cs // 100}.{end_cs % 100:02d} 4000.10" >"{uptime}"\nexit 0\n')
    stub.chmod(0o755)
    # Asserted rather than assumed: a no-op replacement would time the host's real uptime instead.
    redirected = body.group(0).replace("/proc/uptime", str(uptime))
    assert redirected != body.group(0), "scripts/test.sh no longer reads /proc/uptime - update this redirection with it"
    path = os.environ.get("PATH", "/usr/bin:/bin")
    if stepped_date:
        # A realtime clock stepped by an hour between any two reads, as an NTP correction would.
        bin_dir = case_dir / "bin"
        bin_dir.mkdir()
        (bin_dir / "date").write_text('#!/bin/sh\nc="$0.calls"\nn=$(cat "$c" 2>/dev/null || echo 0)\nn=$((n + 1)); echo "$n" > "$c"\necho $((n * 3600000000000))\n')
        (bin_dir / "date").chmod(0o755)
        path = f"{bin_dir}:{path}"
    script = case_dir / "probe.sh"
    script.write_text(f'#!/usr/bin/env bash\nset -uo pipefail\nmicropython_bin="{stub}"\n{redirected}\n_detect_parallelism\n')
    done = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, env=dict(os.environ, PATH=path), check=True)
    jobs, cores, multiplier, probe_ms = (int(v) for v in done.stdout.split())
    return (jobs, cores, multiplier, probe_ms), done.stderr


@pytest.mark.parametrize(
    ("probe_ms", "expected"),
    [(10, 4), (250, 4), (260, 2), (900, 2), (910, 1)],
)
def test_each_speed_band_picks_its_own_multiplier(repo_root: Path, tmp_path: Path, probe_ms: int, expected: int) -> None:
    # Both inclusive edges and the next 10ms step past each (the uptime clock's resolution): 250/900
    # are compared with -le, and an edge silently flipping to -lt is the realistic way to break this.
    # 2x is the bench Pi4's class - 4 cores, but slow enough that 16 processes starve a twin test.
    (jobs, cores, multiplier, measured), _ = _run_detector_with_uptime(repo_root, tmp_path, probe_ms)
    assert measured == probe_ms, f"the uptime stub did not take effect: asked for {probe_ms}ms, detector measured {measured}ms"
    assert multiplier == expected, f"a {probe_ms}ms probe must pick {expected}x"
    assert jobs == cores * expected


def test_a_stepped_realtime_clock_leaves_the_band_unchanged(repo_root: Path, tmp_path: Path) -> None:
    # The probe times a monotonic clock: a wall-clock step during the probe (NTP, a suspended VM)
    # must not move the reading, which a `date +%s%N` difference would turn into hours.
    (_, _, multiplier, measured), _ = _run_detector_with_uptime(repo_root, tmp_path, 130, stepped_date=True)
    assert (measured, multiplier) == (130, 4), f"a stepped realtime clock changed the probe: {measured}ms, {multiplier}x"


def test_an_unreadable_uptime_file_runs_at_one_times_and_says_so(repo_root: Path, tmp_path: Path) -> None:
    (_, _, multiplier, _), stderr = _run_detector_with_uptime(repo_root, tmp_path, 130, uptime_readable=False)
    assert multiplier == 1, "a probe with no clock must fall to the safe 1x setting"
    assert "== speed probe failed - running at 1x" in stderr


def test_a_zero_reading_is_a_failed_probe(repo_root: Path, tmp_path: Path) -> None:
    # No real run of the probe takes under one 10ms tick, so a zero reading is a clock fault.
    (_, _, multiplier, _), stderr = _run_detector_with_uptime(repo_root, tmp_path, 0)
    assert multiplier == 1
    assert "== speed probe failed - running at 1x" in stderr


def test_a_genuinely_slow_host_drops_to_one_times_on_the_real_clock(repo_root: Path, tmp_path: Path) -> None:
    # The one band test kept on the REAL clock, and the only one that can be: load can only make
    # the reading larger, which keeps a 1.2s stub inside the same >900ms band it is asserting.
    # The 4x and 2x bands have a load-sensitive ceiling, which is what the stubbed clock above is for.
    jobs, cores, multiplier, probe_ms = _run_detector(repo_root, tmp_path, 1.2)
    assert multiplier == 1, f"a genuinely slow host must drop to 1x (probe {probe_ms}ms)"
    assert jobs == cores


def _run_detector_with_cgroup(repo_root: Path, tmp_path: Path, cpu_max: str) -> tuple[int, int, int, int]:
    # Same probe, with the cgroup v2 quota file redirected at a canned one - the real
    # /sys/fs/cgroup/cpu.max is whatever this run happens to sit in and cannot be varied.
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
    # Runs the real override/clamp block with _detect_parallelism() stubbed to a known answer.
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


def test_a_broken_probe_runs_at_one_times_and_says_so(repo_root: Path, tmp_path: Path) -> None:
    # A probe that cannot run says nothing about the host, so it takes the setting known never to
    # starve a slow one; the line on stderr keeps the slower run from going unexplained.
    body = re.search(r"^_detect_parallelism\(\) \{.*?^\}", _test_sh_text(repo_root), re.DOTALL | re.MULTILINE)
    assert body is not None
    script = tmp_path / "probe_broken.sh"
    script.write_text(f'#!/usr/bin/env bash\nset -uo pipefail\nmicropython_bin="{tmp_path}/does_not_exist"\n{body.group(0)}\n_detect_parallelism\n')
    done = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=True)
    assert int(done.stdout.split()[2]) == 1, f"a broken probe must fall to 1x, got {done.stdout.split()}"
    assert "== speed probe failed - running at 1x" in done.stderr


def test_the_speed_probe_runs_before_the_pytest_job_loads_the_host(repo_root: Path) -> None:
    # The placement bug this pins (2026-09-18): the probe timed a real process, but sat after
    # the tests_scripts/ launch, measuring a host pytest already saturated - 131-141ms idle
    # against 391ms in situ, 8 jobs where 16 was warranted, non-deterministic run to run.

    # The band tests above cannot see it: they stub the clock precisely BECAUSE this tier is not
    # idle - it runs alongside the whole MicroPython tier - so only the ordering can, hence
    # asserting it here.
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
# _cleanup(), the EXIT trap. A regression test for a real defect: bash does not kill background
# jobs when the parent exits, so an abort before the final `wait` orphaned it for up to 1200s,
# re-opening the glob hazard. Driven against real processes - the question is whether one dies.
# ---------------------------------------------------------------------------


def _cleanup_body(repo_root: Path) -> str:
    # scripts/test.sh's own _cleanup(), source text only - comments stripped, since this function's
    # own comment names the very mechanisms (pkill) the checks below require it not to USE.
    body = re.search(r"^_cleanup\(\) \{.*?^\}", _test_sh_text(repo_root), re.DOTALL | re.MULTILINE)
    assert body is not None, "scripts/test.sh no longer defines _cleanup() - update this test with it"
    return body.group(0)


def _without_comments(shell_source: str) -> str:
    return "\n".join(line for line in shell_source.splitlines() if not line.lstrip().startswith("#"))


def _run_cleanup_probe(repo_root: Path, tmp_path: Path, *, arm_trap: bool) -> bool:
    # Reproduces the launch-then-abort pattern; returns True if the inner child survived. Output
    # is discarded, not piped: a captured pipe is inherited by the background job, so the parent's
    # exit would not be observable until that job ended - which is the survival being measured.
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
    done = subprocess.run(["/bin/bash", str(script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=_NESTED_RUN_TIMEOUT_S)
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


# ---------------------------------------------------------------------------
# The Unix-port variant check. Once build-standard stopped being the settrace build (Part E.5.2),
# the path no longer identifies the binary - and a ~/pico-toolchain predating the split holds an
# executable build-standard that still carries the flag, which an existence check accepts.
# ---------------------------------------------------------------------------


def _variant_of(repo_root: Path, tmp_path: Path, binary: Path) -> str:
    # Runs scripts/test.sh's own unix_port_variant() against one binary, whatever it is.
    body = re.search(r"^unix_port_variant\(\) \{.*?^\}", _test_sh_text(repo_root), re.DOTALL | re.MULTILINE)
    assert body is not None, "scripts/test.sh no longer defines unix_port_variant() - update this test with it"
    script = tmp_path / "variant.sh"
    script.write_text(f'#!/usr/bin/env bash\nset -euo pipefail\n{body.group(0)}\nunix_port_variant "{binary}"\n')
    return subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=True).stdout.strip()


def test_the_test_rig_binary_reports_itself_as_the_settrace_free_variant(repo_root: Path, tmp_path: Path, micropython_bin: Path) -> None:
    # The real artifact, not a stub: this is the one assertion that would catch build-standard
    # silently going back to carrying the flag, which is what the 4-5x inflation rides on.
    assert _variant_of(repo_root, tmp_path, micropython_bin) == "plain"


def test_the_coverage_binary_reports_itself_as_the_settrace_variant(repo_root: Path, tmp_path: Path, micropython_bin: Path) -> None:
    settrace_bin = micropython_bin.parent.parent / "build-settrace" / "micropython"
    if not settrace_bin.is_file():
        pytest.fail(f"the --coverage variant is not built at {settrace_bin} - setup_toolchain.py setup builds both")
    assert _variant_of(repo_root, tmp_path, settrace_bin) == "settrace"


def test_an_unusable_binary_is_reported_as_such_rather_than_as_the_plain_variant(repo_root: Path, tmp_path: Path) -> None:
    # The failure mode that matters: "plain" here would make a broken binary look like the right
    # one, and the run would go on to fail 85 files with no word about why.
    broken = tmp_path / "micropython"
    broken.write_text("#!/bin/sh\nexit 1\n")
    broken.chmod(0o755)
    assert _variant_of(repo_root, tmp_path, broken) == "unusable"
    assert _variant_of(repo_root, tmp_path, tmp_path / "does_not_exist") == "unusable"


def test_a_binary_whose_frozen_asyncio_is_missing_is_unusable_not_plain(repo_root: Path, tmp_path: Path, micropython_bin: Path) -> None:
    # An interrupted two-pass build leaves a runnable binary without frozen asyncio, which every test
    # file then dies on. Stood in for by the real binary with sys.path cleared: frozen modules
    # resolve through its ".frozen" entry, while the builtin sys still imports.
    no_asyncio = tmp_path / "micropython"
    no_asyncio.write_text(f'#!/usr/bin/env bash\nexec "{micropython_bin}" -c "import sys; sys.path.clear()\n$2"\n')
    no_asyncio.chmod(0o755)
    assert _variant_of(repo_root, tmp_path, no_asyncio) == "unusable"


def test_a_wrong_variant_triggers_a_rebuild_rather_than_running_on_it(repo_root: Path) -> None:
    text = _test_sh_text(repo_root)
    # Structural, because the real branch shells out to a multi-minute toolchain build: what has to
    # hold is that a variant mismatch reaches setup at all, and that the run dies if it still fails.
    assert re.search(r'elif \[ "\$\(unix_port_variant "\$micropython_bin"\)" != "\$want_variant" \]; then\n(?:.*\n)*?\s*uv run toolchain/setup_toolchain\.py setup', text), (
        "a build-standard that is the wrong variant must trigger the same setup rebuild a missing one does"
    )
    assert re.search(r'got_variant="\$\(unix_port_variant "\$micropython_bin"\)"\nif \[ "\$got_variant" != "\$want_variant" \]; then\n(?:.*\n)*?\s*exit 1', text), (
        "after the rebuild the variant must be re-checked and the run must exit, never fall through onto the wrong binary"
    )


def test_a_non_integer_gc_threshold_is_rejected_before_anything_is_built(repo_root: Path) -> None:
    # Validated once, up front: unchecked it reaches int() inside _threshold_runner.py and fails
    # every one of the 85 files with a traceback, each retried, naming the real mistake nowhere.
    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts" / "test.sh")],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "GC_THRESHOLD": "32k"},
        cwd=repo_root,
        timeout=_NESTED_RUN_TIMEOUT_S,
        check=False,
    )
    assert completed.returncode == 2, f"expected a fast rejection, got {completed.returncode}:\n{completed.stdout[-2000:]}\n{completed.stderr[-2000:]}"
    assert "GC_THRESHOLD must be an integer" in completed.stderr


@pytest.mark.parametrize("value", ["999999999999999999999", "-999999999999999999999"])
def test_an_out_of_range_gc_threshold_is_rejected_too(repo_root: Path, value: str) -> None:
    # A well-formed integer no shippable setting can match: past the host's own word it reaches the
    # runner and raises OverflowError per file - the same 255-traceback run the shape check
    # prevents, which the shape check alone does not catch.
    completed = subprocess.run(
        ["/bin/bash", str(repo_root / "scripts" / "test.sh")],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "GC_THRESHOLD": value},
        cwd=repo_root,
        timeout=_NESTED_RUN_TIMEOUT_S,
        check=False,
    )
    assert completed.returncode == 2, f"expected a fast rejection, got {completed.returncode}:\n{completed.stdout[-2000:]}\n{completed.stderr[-2000:]}"
    assert "outside the rp2040's own 32-bit machine word" in completed.stderr


def _gc_threshold_check(repo_root: Path, tmp_path: Path, value: str) -> "subprocess.CompletedProcess[str]":
    # Runs scripts/test.sh's GC_THRESHOLD validation block alone, extracted from the real source -
    # not the whole script, since an ACCEPTED value carries on into the live-tree sweeps while this
    # file's tests run concurrently with 85 test files holding scratch dirs under tests/_tmp.
    text = _test_sh_text(repo_root)
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith('if [ -n "${GC_THRESHOLD:-}"')), None)
    assert start is not None, "scripts/test.sh no longer validates GC_THRESHOLD - update this test with it"
    end = next(i for i in range(start, len(lines)) if lines[i] == "fi")
    script = tmp_path / "check.sh"
    script.write_text("#!/usr/bin/env bash\nset -euo pipefail\ncoverage=0\n" + "\n".join(lines[start : end + 1]) + "\n")
    return subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "GC_THRESHOLD": value}, check=False)


@pytest.mark.parametrize("value", ["2147483648", "-2147483649"])
def test_the_first_value_past_each_edge_is_rejected_on_range_alone(repo_root: Path, tmp_path: Path, value: str) -> None:
    # 10 and 11 digits, so the length guard passes both and only the comparison rejects them. This
    # HOST would accept either - its own machine word is 64-bit and gc.threshold() raises
    # OverflowError only near 2^63 (measured) - so the bound asserted here is the rp2040's.
    completed = _gc_threshold_check(repo_root, tmp_path, value)
    assert completed.returncode == 2, f"GC_THRESHOLD={value} must be rejected on range: {completed.stdout!r} {completed.stderr!r}"
    assert "outside the rp2040's own 32-bit machine word" in completed.stderr


@pytest.mark.parametrize("value", ["-1", "32768", "0", "2147483647", "-2147483648"])
def test_the_values_the_project_actually_uses_are_accepted(repo_root: Path, tmp_path: Path, value: str) -> None:
    # The false-positive direction for both checks above. -1 is the (e) stage, 32768 is what the
    # firmware ships; the rest are the range check's own inclusive edges, where any negative value
    # means the reactive default (py/modgc.c maps every one of them to (size_t)-1).
    completed = _gc_threshold_check(repo_root, tmp_path, value)
    assert completed.returncode == 0, f"GC_THRESHOLD={value} must pass validation: {completed.stderr!r}"
    assert completed.stderr == "", f"GC_THRESHOLD={value} must pass silently: {completed.stderr!r}"


def test_argument_validation_happens_before_anything_in_the_live_tree_is_touched(repo_root: Path) -> None:
    # Ordering, and a real race until 2026-09-22: the rejection tests above run a nested test.sh
    # while tests_scripts/ is itself backgrounded alongside 85 files whose TmpScratch dirs live
    # under tests/_tmp - so a nested run that swept before validating deleted them mid-test.
    text = _test_sh_text(repo_root)
    validate_at = text.find('if [ -n "${GC_THRESHOLD:-}"')
    args_at = text.find("coverage=0")
    timeouts_at = text.find("_require_seconds TESTS_SCRIPTS_TIMEOUT_S")
    parallelism_at = text.find("error: TEST_PARALLELISM must be a positive integer")
    assert validate_at != -1 and args_at != -1 and timeouts_at != -1 and parallelism_at != -1, "scripts/test.sh no longer parses arguments or validates GC_THRESHOLD, the timeouts and TEST_PARALLELISM - update this test with it"
    for sweep in ("rm -rf tests/_tmp", _SWEEP_LINE):
        sweep_at = text.find(sweep)
        assert sweep_at != -1, f"scripts/test.sh no longer sweeps via {sweep!r}"
        assert args_at < sweep_at, f"argument parsing must reject an unknown flag before {sweep!r} mutates the live tree"
        assert validate_at < sweep_at, f"GC_THRESHOLD validation must run before {sweep!r} mutates the live tree"
        assert timeouts_at < sweep_at, f"the timeout validation must run before {sweep!r} mutates the live tree"
        assert parallelism_at < sweep_at, f"the TEST_PARALLELISM validation must run before {sweep!r} mutates the live tree"


def _nested_run_with_sentinels(repo_root: Path, tmp_path: Path, args: list[str], env: dict[str, str], key: str) -> tuple["subprocess.CompletedProcess[str]", bool, bool]:
    # Runs a nested scripts/test.sh with sentinels in both sweep targets, on a scratch key of the
    # caller's own; returns the run and whether each sentinel survived.
    scratch = repo_root / "tests" / "_tmp" / f"zz_test_sh_{key}_sentinel"
    scratch.mkdir(parents=True, exist_ok=True)
    sentinel = scratch / "in_use.txt"
    sentinel.write_text("held by a concurrently running test file\n")
    fixture = repo_root / "devices" / f"zz_test_{key}_sentinel.toml"
    fixture.write_text("# swept by scripts/test.sh's reserved-namespace sweep\n")
    try:
        completed = subprocess.run(
            ["/bin/bash", str(repo_root / "scripts" / "test.sh"), *args],
            capture_output=True,
            text=True,
            env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), **env},
            cwd=repo_root,
            timeout=_NESTED_RUN_TIMEOUT_S,
            check=False,
        )
        return completed, sentinel.is_file(), fixture.is_file()
    finally:
        # ignore_errors, because the failure a caller reports IS the tree being gone: a strict
        # teardown would raise FileNotFoundError and bury the assertion that explains why.
        fixture.unlink(missing_ok=True)
        shutil.rmtree(scratch, ignore_errors=True)


@pytest.mark.parametrize(
    ("args", "env", "message"),
    [
        ([], {"GC_THRESHOLD": "32k"}, "GC_THRESHOLD must be an integer"),
        (["--bogus"], {}, "error: unknown argument --bogus (scripts/test.sh --help)"),
        ([], {"PER_FILE_TIMEOUT_S": "0"}, "error: PER_FILE_TIMEOUT_S must be a positive integer number of seconds, not '0'"),
        ([], {"PER_FILE_TIMEOUT_S": "-5"}, "PER_FILE_TIMEOUT_S must be a positive integer number of seconds"),
        ([], {"PER_FILE_TIMEOUT_S": "abc"}, "PER_FILE_TIMEOUT_S must be a positive integer number of seconds"),
        ([], {"TESTS_SCRIPTS_TIMEOUT_S": "0"}, "error: TESTS_SCRIPTS_TIMEOUT_S must be a positive integer number of seconds, not '0'"),
        ([], {"TEST_PARALLELISM": "0"}, "error: TEST_PARALLELISM must be a positive integer, not '0'"),
        ([], {"TEST_PARALLELISM": "-1"}, "error: TEST_PARALLELISM must be a positive integer, not '-1'"),
        ([], {"TEST_PARALLELISM": "abc"}, "error: TEST_PARALLELISM must be a positive integer, not 'abc'"),
        ([], {"TEST_PARALLELISM": "1.5"}, "error: TEST_PARALLELISM must be a positive integer, not '1.5'"),
    ],
)
def test_a_rejected_invocation_exits_2_and_leaves_the_live_tree_untouched(repo_root: Path, tmp_path: Path, args: list[str], env: dict[str, str], message: str) -> None:
    # The same invariant end to end rather than by source order. Exit 2 for every usage or setting
    # error (SPECIFICATION.md E.10); 0 for a timeout would silently switch `timeout` off.
    key = re.sub(r"[^a-z0-9]+", "_", " ".join([*args, *(f"{k} {v}" for k, v in env.items())]).lower()).strip("_")
    completed, scratch_kept, fixture_kept = _nested_run_with_sentinels(repo_root, tmp_path, args, env, f"reject_{key}")
    assert completed.returncode == 2, f"expected a rejection, got {completed.returncode}: {completed.stderr[-2000:]}"
    assert message in completed.stderr
    assert scratch_kept, "a rejected run wiped tests/_tmp, which concurrently running test files are using for scratch"
    assert fixture_kept, "a rejected run swept devices/zz_test_*.toml, which it never got far enough to need"


def test_help_prints_every_option_and_variable_and_touches_nothing(repo_root: Path, tmp_path: Path) -> None:
    completed, scratch_kept, fixture_kept = _nested_run_with_sentinels(repo_root, tmp_path, ["--help"], {}, "help")
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("Usage: scripts/test.sh")
    for name, default in (("--coverage", ""), ("PICO_TOOLCHAIN_DIR", "~/pico-toolchain"), ("SKIP_APT", "0"), ("PER_FILE_TIMEOUT_S", "240"), ("TESTS_SCRIPTS_TIMEOUT_S", "1200"), ("TEST_PARALLELISM", "detected"), ("GC_THRESHOLD", "unset")):
        line = next((line for line in completed.stdout.splitlines() if name in line), None)
        assert line is not None, f"--help does not name {name}"
        assert default in line, f"--help gives no default for {name}: {line!r}"
    assert scratch_kept, "--help swept tests/_tmp"
    assert fixture_kept, "--help swept devices/zz_test_*.toml"


# ---------------------------------------------------------------------------
# The MemoryError gate. SPECIFICATION.md Part I.4(e) requires zero MemoryErrors from the suite,
# caught-and-logged included; the twin tier asserted that on its own logs and this tier - the one
# the (e)/(f) stages actually run in - had no equivalent, so a degrade-and-pass went by in silence.
# ---------------------------------------------------------------------------


def _flag_markers(repo_root: Path, tmp_path: Path, output: str | None, path_prefix: Path | None = None) -> tuple[str, str]:
    # Runs scripts/test.sh's own _flag_memory_errors() over one file's captured output (None: no log
    # at all) with only results_dir set; returns its .memerr and .noverdict markers' text.
    body = re.search(r"^_flag_memory_errors\(\) \{.*?^\}", _test_sh_text(repo_root), re.DOTALL | re.MULTILINE)
    assert body is not None, "scripts/test.sh no longer defines _flag_memory_errors() - update this test with it"
    results = tmp_path / "results"
    results.mkdir(exist_ok=True)
    log = tmp_path / "case.log"
    if output is not None:
        log.write_text(output)
    script = tmp_path / "flag.sh"
    script.write_text(f'#!/usr/bin/env bash\nset -euo pipefail\nresults_dir="{results}"\n{body.group(0)}\n_flag_memory_errors case "{log}"\n')
    path = f"{path_prefix}:{os.environ['PATH']}" if path_prefix else os.environ["PATH"]
    subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=True, env={**os.environ, "PATH": path})
    memerr, noverdict = results / "case.memerr", results / "case.noverdict"
    return (memerr.read_text() if memerr.exists() else "", noverdict.read_text() if noverdict.exists() else "")


def _flag(repo_root: Path, tmp_path: Path, output: str) -> str:
    memerr, noverdict = _flag_markers(repo_root, tmp_path, output)
    assert noverdict == "", noverdict
    return memerr


def test_a_missing_log_is_no_verdict_rather_than_clean(repo_root: Path, tmp_path: Path) -> None:
    # The gate fails closed: a log it cannot read is a file it cannot vouch for.
    memerr, noverdict = _flag_markers(repo_root, tmp_path, None)
    assert memerr == ""
    assert "missing or unreadable - no verdict" in noverdict


def test_a_grep_error_is_no_verdict_rather_than_clean(repo_root: Path, tmp_path: Path) -> None:
    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir()
    grep = stub_bin / "grep"
    grep.write_text("#!/bin/sh\nexit 2\n")
    grep.chmod(0o755)
    memerr, noverdict = _flag_markers(repo_root, tmp_path, "[test_x] 3/3 passed, 0 failed, 0 skipped\n", stub_bin)
    assert memerr == ""
    assert "grep exited 2" in noverdict


def test_a_caught_and_logged_memory_error_is_flagged(repo_root: Path, tmp_path: Path) -> None:
    # The whole point: this file's own tests all passed. A degrade path that allocated, failed,
    # logged it and carried on is a design defect, not a green result.
    flagged = _flag(repo_root, tmp_path, "[test_x] 12/12 passed\n[test_x] WARN sgp40 setup: MemoryError\n")
    assert "MemoryError" in flagged, "a MemoryError in a passing file's output must be flagged"


def test_the_real_caught_and_degraded_form_is_flagged_though_it_never_says_memoryerror(repo_root: Path, tmp_path: Path) -> None:
    # This is what src/ actually emits: pr.err("...", e) prints str(e), and the interpreter's own
    # message carries no class name (verified against the built binary). A gate looking only for
    # "MemoryError" sees uncaught tracebacks and misses every caught degrade - the silent case.
    flagged = _flag(repo_root, tmp_path, "[test_x] 12/12 passed\n[test_x] BMP3XX Could not start timer: memory allocation failed, allocating 2048 bytes\n")
    assert "memory allocation failed" in flagged, "a degrade handler logging only str(e) must still be flagged"


def test_the_heap_is_locked_wording_is_flagged_too(repo_root: Path, tmp_path: Path) -> None:
    # py/runtime.c raises MemoryError with two different messages; both begin "memory allocation
    # failed", which is why the pattern matches that prefix rather than either full wording.
    flagged = _flag(repo_root, tmp_path, "[test_x] WARN flush: memory allocation failed, heap is locked\n")
    assert "heap is locked" in flagged


def test_a_clean_run_is_not_flagged(repo_root: Path, tmp_path: Path) -> None:
    # The false-positive direction, and why the gate is affordable: measured over a full 85-file
    # run, the suite's own output contains neither pattern once.
    assert _flag(repo_root, tmp_path, "[test_x] 12/12 passed\n[test_x] PASS test_allocates_a_buffer\n") == ""


def test_the_suites_own_injected_allocation_failures_do_not_trip_the_gate(repo_root: Path, tmp_path: Path) -> None:
    # 15 tests/ sites raise MemoryError("simulated allocation failure") on purpose to prove a
    # degrade path. That wording is deliberately not the interpreter's, so the widened pattern
    # still distinguishes a test's own injection from a real allocation failure on this host.
    assert _flag(repo_root, tmp_path, "[test_x] NTP Could not start NTP timer: simulated allocation failure\n") == ""


def test_the_flag_records_the_offending_lines_not_just_the_fact(repo_root: Path, tmp_path: Path) -> None:
    # A bare "this file had one" would send the reader back through a 400,000-line log to find it.
    flagged = _flag(repo_root, tmp_path, "[test_x] noise\n[test_x] ERR fram chunk alloc: MemoryError: memory allocation failed\n")
    assert "memory allocation failed" in flagged


def test_the_gate_is_wired_into_the_run_and_into_the_verdict(repo_root: Path) -> None:
    text = _test_sh_text(repo_root)
    # Structural, because the real path is an 85-file run: what has to hold is that each file's
    # output is captured, that both of run_test_file()'s exits are flagged, and that a flag reaches
    # the summary AND the exit status - a report nobody's CI gates on is not a gate.
    assert 'sed -u "s/^/[$tag] /" | tee -a "$log_file"' in text, "each file's tagged output must be captured for the gate to search"
    assert text.count('_flag_memory_errors "$tag" "$log_file"') == 2, "both the PASS and the FAIL exit of run_test_file() must flag, so a degraded pass is caught too"
    assert re.search(r'if \[ -s "\$results_dir/\$tag\.memerr" \]; then\n\s*failed=1', text), "a flagged file must set failed=1, not merely print"
    assert "MemoryError seen" in text, "the summary must name the files, so a long log does not have to be re-read"


# --- the failure annotations (the only channel off the runner that is not the raw log) -------------


def _annotation_detail_line(repo_root: Path) -> str:
    # The one line with real logic in the annotation block: it folds a failing file's captured
    # output into a single GitHub-escaped annotation body. Extracted rather than reimplemented, for
    # the same reason _verdict_block() is.
    match = re.search(r'^\s*annotation_detail="\$\(\{ tail.*$', _test_sh_text(repo_root), re.MULTILINE)
    assert match is not None, "scripts/test.sh no longer builds an annotation body from a failing file's log"
    return match.group(0).strip()


def _run_annotation_detail(repo_root: Path, tmp_path: Path) -> tuple[int, str]:
    script = tmp_path / "detail.sh"
    script.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f'results_dir="{tmp_path}"\nannotation_tag="test_x"\n'
        f'{_annotation_detail_line(repo_root)}\necho "::error title=tests/test_x.py::$annotation_detail"\n',
    )
    done = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=False, timeout=_SNIPPET_TIMEOUT_S)
    return done.returncode, done.stdout


def test_a_failing_file_s_own_output_survives_into_one_annotation(repo_root: Path, tmp_path: Path) -> None:
    (tmp_path / "test_x.memerr").write_text("")
    (tmp_path / "test_x.log").write_text("[test_x] 50% done\n[test_x] AssertionError: boom\n")
    code, out = _run_annotation_detail(repo_root, tmp_path)
    assert code == 0, out
    line = out.strip()
    # GitHub reads an annotation as one line and `%` as the start of an escape, so both have to be
    # encoded or everything past the first newline is silently dropped.
    assert "\n" not in line, line
    assert "50%25 done" in line, line
    assert line.endswith("AssertionError: boom%0A"), line


def test_a_missing_log_cannot_abort_the_summary_the_annotation_is_part_of(repo_root: Path, tmp_path: Path) -> None:
    # `set -e` plus a failing command substitution would kill the run before it printed its verdict,
    # which is the one thing a diagnostic aid must never do.
    code, out = _run_annotation_detail(repo_root, tmp_path)
    assert code == 0, out
    assert out.strip() == "::error title=tests/test_x.py::", out


def test_every_way_the_suite_goes_red_gets_an_annotation_and_only_under_actions(repo_root: Path) -> None:
    text = _test_sh_text(repo_root)
    # Three independent ways this script reports red - a failing file, a file that only logged an
    # allocation failure, the pytest tier - plus the count of whatever the 10-per-step cap withheld.
    assert text.count("::error title=") == 4, "each of the three red outcomes needs its own annotation, plus the overflow count"
    assert text.count('if [ -n "${GITHUB_ACTIONS:-}" ]') == 1, "a local run must not print workflow commands at all"
    assert _annotation_block(repo_root).count("::error title=") == 4, "every annotation must be emitted from the one GITHUB_ACTIONS-gated block"


def _memerr_detail_line(repo_root: Path) -> str:
    # The allocation-failure annotation's body line, extracted exactly as _annotation_detail_line()
    # extracts the failing-file one: the same escaping, but over the .memerr marker, read whole.
    match = re.search(r'^\s*annotation_detail="\$\(\{ cat.*\.memerr.*$', _test_sh_text(repo_root), re.MULTILINE)
    assert match is not None, "scripts/test.sh no longer builds an annotation body from a file's .memerr marker"
    return match.group(0).strip()


def _run_memerr_detail(repo_root: Path, tmp_path: Path) -> tuple[int, str]:
    script = tmp_path / "memerr_detail.sh"
    script.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f'results_dir="{tmp_path}"\nannotation_tag="test_x"\n'
        f'{_memerr_detail_line(repo_root)}\nprintf "%s" "$annotation_detail"\n',
    )
    done = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=False, timeout=_SNIPPET_TIMEOUT_S)
    return done.returncode, done.stdout


def test_an_allocation_failure_marker_survives_into_one_escaped_annotation(repo_root: Path, tmp_path: Path) -> None:
    (tmp_path / "test_x.memerr").write_text("a 50% b\nc\n")
    code, out = _run_memerr_detail(repo_root, tmp_path)
    assert code == 0, out
    assert out == "a 50%25 b%0Ac%0A", out


def test_a_missing_memerr_marker_cannot_abort_the_summary_either(repo_root: Path, tmp_path: Path) -> None:
    code, out = _run_memerr_detail(repo_root, tmp_path)
    assert code == 0, out
    assert out == "", out


def _annotation_block(repo_root: Path) -> str:
    # The whole GITHUB_ACTIONS-gated annotation block: from its gate to the first top-level `fi`.
    match = re.search(r'^if \[ -n "\$\{GITHUB_ACTIONS:-\}" \]; then\n.*?^fi$', _test_sh_text(repo_root), re.MULTILINE | re.DOTALL)
    assert match is not None, "scripts/test.sh no longer emits its annotations from one top-level GITHUB_ACTIONS block"
    return match.group(0)


def _run_annotation_block(repo_root: Path, tmp_path: Path, failed: int, memory: int, *, pytest_failed: bool) -> list[str]:
    failed_files = [f"tests/test_f{i}.py" for i in range(failed)]
    memory_files = [f"tests/test_m{i}.py" for i in range(memory)]
    for name in failed_files + memory_files:
        tag = Path(name).stem
        (tmp_path / f"{tag}.log").write_text(f"[{tag}] boom\n")
        (tmp_path / f"{tag}.memerr").write_text(f"[{tag}] memory allocation failed\n")
    script = tmp_path / "block.sh"
    script.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nGITHUB_ACTIONS=true\n"
        f'results_dir="{tmp_path}"\ntests_scripts_result="{"FAIL" if pytest_failed else "PASS"}"\n'
        f"failed_files=({' '.join(failed_files)})\nmemory_error_files=({' '.join(memory_files)})\n"
        f"{_annotation_block(repo_root)}\n",
    )
    done = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=True, timeout=_SNIPPET_TIMEOUT_S)
    return [line for line in done.stdout.splitlines() if line.startswith("::error")]


def test_the_annotations_never_pass_github_s_ten_per_step_cap_and_the_pytest_tier_s_comes_first(repo_root: Path, tmp_path: Path) -> None:
    # GitHub drops every error annotation past the tenth in a step, so the one naming a whole tier
    # must not be the one lost behind a long list of files, and the files past the cap are counted.
    lines = _run_annotation_block(repo_root, tmp_path, failed=9, memory=3, pytest_failed=True)
    assert len(lines) == 10, lines
    assert lines[0].startswith("::error title=tests_scripts/ (CPython/pytest)::"), lines
    assert [line.split("::")[1] for line in lines[1:9]] == [f"error title=tests/test_f{i}.py" for i in range(8)], lines
    assert lines[9].startswith("::error title=and 4 more::4 further"), lines


def test_a_run_under_the_cap_gets_every_annotation_and_no_overflow_line(repo_root: Path, tmp_path: Path) -> None:
    lines = _run_annotation_block(repo_root, tmp_path, failed=2, memory=1, pytest_failed=False)
    assert [line.split("::")[1] for line in lines] == ["error title=tests/test_f0.py", "error title=tests/test_f1.py", "error title=tests/test_m0.py (allocation failure)"], lines
    assert "[test_m0] memory allocation failed%0A" in lines[2], lines


def test_an_all_green_run_under_actions_prints_no_annotation_at_all(repo_root: Path, tmp_path: Path) -> None:
    assert _run_annotation_block(repo_root, tmp_path, failed=0, memory=0, pytest_failed=False) == []


# --- the summary block and the exit codes (SPECIFICATION.md E.10, E.5.3) ----------------------------


def _verdict_tail(repo_root: Path) -> str:
    # scripts/test.sh from its summary-block source line to the end: the collector, the renders,
    # the annotations, the archive and the exit. Extracted rather than reimplemented, so a rewrite of
    # the logic has to keep mapping the outcomes onto the block and the codes.
    text = _test_sh_text(repo_root)
    return text[text.index("source scripts/_summary_block.sh") :].rstrip("\n")


def _fake_repo(repo_root: Path, tmp_path: Path) -> Path:
    # A stand-in repo root holding the helpers the tail calls, so its archive lands under tmp_path.
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    for name in ("_summary_block.sh", "_summary_block.py", "_archive_evidence.py"):
        shutil.copy(repo_root / "scripts" / name, root / "scripts" / name)
    return root


_GREEN_RECORD = '{"tests": [{"nodeid": "tests_scripts/test_a.py::test_a", "outcome": "passed", "when": "call", "reason": "", "markers": [], "user_properties": []}], "collection": [], "deselected": [], "options": {}, "markexpr": "", "collect_only": false, "session_notes": [], "exitstatus": 0}'


def _run_tail(repo_root: Path, tmp_path: Path, jobs: dict[str, tuple[str | None, str | None, str | None]], *, pytest_status: str = "PASS", record: str | None = _GREEN_RECORD, coverage: int = 0, render_fails: bool = False, extra: dict[str, str] | None = None) -> tuple[int, str, Path]:
    # Runs the verdict tail over a fixture results dir: jobs maps a test file to its (status, log,
    # memerr) contents, None meaning that file is absent; extra plants further result files.
    root = _fake_repo(repo_root, tmp_path)
    results = tmp_path / "results"
    results.mkdir()
    for test_file, (status, log, memerr) in jobs.items():
        tag = Path(test_file).stem
        for suffix, content in (("status", status), ("log", log), ("memerr", memerr)):
            if content is not None:
                (results / f"{tag}.{suffix}").write_text(content)
    for name, content in (extra or {}).items():
        (results / name).write_text(content)
    status_file = tmp_path / "pytest.status"
    status_file.write_text(pytest_status + "\n")
    if record is not None:
        (results / "tests_scripts.json").write_text(record)
    stub_bin = tmp_path / "stub_bin"
    stub_bin.mkdir()
    # The renderer is the only `uv run` the tail makes that the fixture stands in for.
    (stub_bin / "uv").write_text(f'#!/usr/bin/env bash\nif [ "$2" = "scripts/_render_coverage.py" ]; then exit {1 if render_fails else 0}; fi\nexec {shutil.which("uv")} "$@"\n')
    (stub_bin / "uv").chmod(0o755)
    files = " ".join(jobs)
    script = tmp_path / "tail.sh"
    script.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f'test_files=({files})\nresults_dir="{results}"\nraw_dir="{tmp_path}/raw"\ncoverage={coverage}\n'
        f'tests_scripts_status_file="{status_file}"\nevidence_archived=0\n'
        f"{_verdict_tail(repo_root)}\n",
    )
    env = {**os.environ, "PATH": f"{stub_bin}:{os.environ['PATH']}", "GIT_CEILING_DIRECTORIES": str(tmp_path)}
    for name in ("GITHUB_ACTIONS", "GC_THRESHOLD"):
        env.pop(name, None)
    done = subprocess.run(["/bin/bash", str(script)], cwd=root, env=env, capture_output=True, text=True, check=False, timeout=120)
    return done.returncode, done.stdout, root


def _block(out: str) -> str:
    return out[out.index("== Summary: scripts/test.sh ==") :]


def _passing(tag: str, count: str = "3/3 passed, 0 failed, 0 skipped") -> tuple[str, str, None]:
    return ("PASS\n", f"[{tag}] PASS test_a\n[{tag}] {count}\n", None)


def test_a_retried_a_crashed_and_an_allocation_flagged_file_render_the_block(repo_root: Path, tmp_path: Path) -> None:
    jobs: dict[str, tuple[str | None, str | None, str | None]] = {
        "tests/test_ok.py": _passing("test_ok", "4/5 passed, 0 failed, 1 skipped"),
        "tests/test_retried.py": ("RETRIED-PASS 2/3\n", "[test_retried] 2/2 passed, 0 failed, 0 skipped\n", None),
        "tests/test_crashed.py": ("FAIL\n", "[test_crashed] PASS test_a\n[test_crashed] Segmentation fault\n", None),
        "tests/test_digital_twin_mem.py": ("PASS\n", "[test_digital_twin_mem] 1/1 passed, 0 failed, 0 skipped\n", "[test_digital_twin_mem] memory allocation failed\n"),
    }
    code, out, root = _run_tail(repo_root, tmp_path, jobs)
    assert code == 1, out
    block = _block(out)
    assert block.endswith("Result: FAIL\nExit code: 1\n"), block
    assert "\nCounts (files): passed 1 · failed 2 · skipped 0 · deselected 0 · retried 1 · recovered 0 · vacuous 0\n" in block
    assert "\nCounts (tests): passed 7 · failed 0 · skipped 1 · deselected 0 · retried 0 · recovered 0 · vacuous 0\n" in block
    assert "\nCounts (tests_scripts tests): passed 1 · failed 0 · skipped 0 · deselected 0 · retried 0 · recovered 0 · vacuous 0\n" in block
    assert "  - tests/test_crashed.py: failed; no test count (crashed or killed)\n" in block
    assert "  - tests/test_digital_twin_mem.py: MemoryError seen\n" in block
    assert "Passed only on retry:\n  - tests/test_retried.py (attempt 2/3)\n" in block
    assert "Levels: L0 PASS · L1 FAIL · L2 FAIL (tests/test_digital_twin_*.py only; run_digital_twin_ci.sh not run)\n" in block
    assert "GC stage: -1 (reactive default)\n" in block
    assert "root-cause item: test_retried needed attempt 2/3 - record it as a root-cause item" in out[: out.index(block)]
    runs = list((root / "build" / "archive" / "test_sh").iterdir())
    assert len(runs) == 1
    archived = sorted(p.name for p in runs[0].iterdir())
    assert archived == ["summary.txt", "test_crashed.log", "test_digital_twin_mem.log", "test_digital_twin_mem.memerr", "test_retried.log"], archived
    assert (runs[0] / "summary.txt").read_text() == block


def test_a_green_run_passes_and_archives_the_block_only(repo_root: Path, tmp_path: Path) -> None:
    code, out, root = _run_tail(repo_root, tmp_path, {"tests/test_ok.py": _passing("test_ok")})
    assert code == 0, out
    assert _block(out).endswith("Result: PASS\nExit code: 0\n")
    (run,) = (root / "build" / "archive" / "test_sh").iterdir()
    assert [p.name for p in run.iterdir()] == ["summary.txt"]


@pytest.mark.parametrize(
    ("status", "log", "reason"),
    [
        (None, "[test_x] 1/1 passed, 0 failed, 0 skipped\n", "no verdict"),
        ("", "[test_x] 1/1 passed, 0 failed, 0 skipped\n", "no verdict"),
        ("PASS\n", None, "no test count (crashed or killed)"),
        ("FAIL\n", "[test_x] 1/3 passed, 2 failed, 0 skipped\n", "2 of 3 tests failed"),
    ],
)
def test_a_missing_verdict_or_count_is_a_failure(repo_root: Path, tmp_path: Path, status: str | None, log: str | None, reason: str) -> None:
    code, out, _ = _run_tail(repo_root, tmp_path, {"tests/test_x.py": (status, log, None)})
    assert code == 1, out
    assert f"  - tests/test_x.py: {reason}" in _block(out)


def test_a_no_verdict_marker_from_the_memory_gate_fails_the_file(repo_root: Path, tmp_path: Path) -> None:
    code, out, _ = _run_tail(repo_root, tmp_path, {"tests/test_x.py": _passing("test_x")}, extra={"test_x.noverdict": "memory gate: grep exited 2\n"})
    assert code == 1, out
    assert "  - tests/test_x.py: no verdict (per-file log missing or unreadable)" in _block(out)


@pytest.mark.parametrize(
    ("pytest_status", "record", "reason"),
    [
        ("FAIL", _GREEN_RECORD, "pytest exited nonzero or timed out"),
        ("PASS", None, "1 failed (listed above)"),
        ("PASS", "{garbled", "1 failed (listed above)"),
    ],
)
def test_the_pytest_tier_fails_on_its_exit_or_a_missing_record(repo_root: Path, tmp_path: Path, pytest_status: str, record: str | None, reason: str) -> None:
    code, out, _ = _run_tail(repo_root, tmp_path, {"tests/test_ok.py": _passing("test_ok")}, pytest_status=pytest_status, record=record)
    assert code == 1, out
    block = _block(out)
    assert "Levels: L0 FAIL · L1 PASS" in block
    assert f"  - tests_scripts/ (pytest): {reason}" in block
    if record != _GREEN_RECORD:
        assert "tests_scripts.json: no verdict (run record missing or unreadable)\n" in out[: out.index(block)]


def test_the_pytest_tiers_skips_and_deselections_are_named_with_their_reasons(repo_root: Path, tmp_path: Path) -> None:
    record = _GREEN_RECORD.replace('"collection": []', '"collection": [{"nodeid": "tests_scripts/test_b.py", "outcome": "skipped", "reason": "needs a toolchain"}]')
    record = record.replace('"deselected": []', '"deselected": [{"nodeid": "tests_scripts/test_c.py::test_c", "by": "runner selection", "markers": []}]')
    code, out, _ = _run_tail(repo_root, tmp_path, {"tests/test_ok.py": _passing("test_ok")}, record=record)
    assert code == 0, out
    before = out[: out.index("== Summary: scripts/test.sh ==")]
    assert "tests_scripts/ skipped:\n  - tests_scripts/test_b.py: needs a toolchain\n" in before
    assert "tests_scripts/ deselected:\n  - tests_scripts/test_c.py::test_c: runner selection\n" in before
    assert "\nCounts (tests_scripts tests): passed 1 · failed 0 · skipped 1 · deselected 1 ·" in _block(out)


def test_the_pytest_tiers_notes_reach_the_block_and_its_recoveries_are_named_and_counted(repo_root: Path, tmp_path: Path) -> None:
    record = _GREEN_RECORD.replace('"user_properties": []', '"user_properties": [["result_note", "3 answered, 1 refused"]]')
    recovered = '{"nodeid": "tests_scripts/test_r.py::test_r", "outcome": "passed", "when": "call", "reason": "", "markers": [], "user_properties": [["recovery", "rebuilt the toolchain"]]}'
    record = record.replace('"tests": [', f'"tests": [{recovered}, ')
    record = record.replace('"session_notes": []', '"session_notes": [{"text": "bench idle", "recovery": false, "source": "bench"}]')
    code, out, _ = _run_tail(repo_root, tmp_path, {"tests/test_ok.py": _passing("test_ok")}, record=record)
    assert code == 0, out
    block = _block(out)
    assert "\nNotes:\n  - tests_scripts/test_a.py::test_a: 3 answered, 1 refused\n  - session (bench): bench idle\nChecked nothing: none\n" in block, block
    assert "tests_scripts/ recovered:\n  - tests_scripts/test_r.py::test_r: rebuilt the toolchain\n" in out[: out.index(block)]
    assert "\nCounts (tests_scripts tests): passed 1 · failed 0 · skipped 0 · deselected 0 · retried 0 · recovered 1 · vacuous 0\n" in block


def test_a_renderer_failure_alone_exits_three_rather_than_one(repo_root: Path, tmp_path: Path) -> None:
    code, out, _ = _run_tail(repo_root, tmp_path, {"tests/test_ok.py": _passing("test_ok")}, coverage=1, render_fails=True)
    assert code == 3, "tests passing with only the report broken must be distinguishable from a test failure"
    block = _block(out)
    assert block.endswith("Result: PASS (coverage report not rendered)\nExit code: 3\n")
    assert "GC stage: coverage run (settrace)\n" in block


def test_a_test_failure_outranks_a_renderer_failure(repo_root: Path, tmp_path: Path) -> None:
    # Both broken: the caller must hear about the test, since that is the one that gates.
    code, out, _ = _run_tail(repo_root, tmp_path, {"tests/test_x.py": ("FAIL\n", None, None)}, coverage=1, render_fails=True)
    assert code == 1
    assert _block(out).endswith("Result: FAIL\nExit code: 1\n")


def test_nothing_follows_the_block_on_stdout(repo_root: Path, tmp_path: Path) -> None:
    _, out, _ = _run_tail(repo_root, tmp_path, {"tests/test_ok.py": _passing("test_ok")})
    assert out.endswith("Exit code: 0\n")
    assert out.count("== Summary: scripts/test.sh ==") == 1


def _run_file_job(repo_root: Path, tmp_path: Path, first_attempt: str, later_attempts: str) -> Path:
    # Runs scripts/test.sh's own run_test_file() for one fixture test file over a stub interpreter whose
    # first call runs `first_attempt` and every later one `later_attempts` (bash); returns results_dir.
    text = _test_sh_text(repo_root)
    bodies = [re.search(rf"^{name}\(\) \{{.*?^\}}", text, re.DOTALL | re.MULTILINE) for name in ("_flag_memory_errors", "run_test_file")]
    assert all(bodies), "scripts/test.sh no longer defines _flag_memory_errors() and run_test_file()"
    calls = tmp_path / "calls"
    stub = tmp_path / "micropython"
    stub.write_text(f'#!/usr/bin/env bash\necho x >>"{calls}"\nif [ "$(wc -l <"{calls}")" -eq 1 ]; then\n{first_attempt}\nelse\n{later_attempts}\nfi\n')
    stub.chmod(0o755)
    results = tmp_path / "results"
    results.mkdir()
    script = tmp_path / "run.sh"
    script.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f'results_dir="{results}"\ncoverage=0\nmicropython_bin="{stub}"\nper_file_timeout_s=1\nmax_attempts=3\n'
        "declare -A per_file_timeout_overrides_s=()\n"
        + "\n".join(b.group(0) for b in bodies if b)
        + f'\nrun_test_file tests/test_x.py "{results}/test_x.status"\n',
    )
    done = subprocess.run(["/bin/bash", str(script)], capture_output=True, text=True, check=False, timeout=120)
    assert done.returncode == 0, done.stderr
    return results


def _job_files(results: Path) -> tuple[str | None, str | None, str | None]:
    # The (status, log, memerr) a run_test_file() job left, in _run_tail()'s jobs form.
    return tuple(  # type: ignore[return-value]
        (results / f"test_x.{suffix}").read_text() if (results / f"test_x.{suffix}").exists() else None for suffix in ("status", "log", "memerr")
    )


def test_a_pass_after_a_timeout_is_retried_pass_not_pass(repo_root: Path, tmp_path: Path) -> None:
    # A stub interpreter that hangs on its first call and passes on its second: the retry backstop
    # stays, and the file is reported as RETRIED-PASS 2/3 - a root-cause item, never a plain PASS.
    results = _run_file_job(repo_root, tmp_path, "sleep 30", 'echo "1/1 passed, 0 failed, 0 skipped"')
    assert (results / "test_x.status").read_text() == "RETRIED-PASS 2/3\n"


def test_an_allocation_failure_in_a_timed_out_attempt_fails_the_file_its_retry_passes(repo_root: Path, tmp_path: Path) -> None:
    # Every attempt's output stays in the job log, so the memory gate reads the timed-out attempt
    # too: its caught allocation failure fails the file instead of vanishing into RETRIED-PASS.
    first = 'echo "BMP3XX Could not start timer: memory allocation failed, allocating 2048 bytes"\nsleep 30'
    results = _run_file_job(repo_root, tmp_path, first, 'echo "1/1 passed, 0 failed, 0 skipped"')
    assert "memory allocation failed" in (results / "test_x.memerr").read_text()
    code, out, _ = _run_tail(repo_root, tmp_path / "tail", {"tests/test_x.py": _job_files(results)})
    block = _block(out)
    assert code == 1, out
    assert "Failed:\n  - tests/test_x.py: MemoryError seen; passed on attempt 2/3\n" in block, block
    assert "Passed only on retry: none\n" in block


def test_a_skipped_test_is_named_in_the_block_with_its_reason_once(repo_root: Path, tmp_path: Path) -> None:
    # microtest's per-test SKIP line reaches the block as a Skipped: item, not only the per-file log;
    # a timed-out attempt that printed it too must not list it twice.
    skip = 'echo "SKIP test_y: needs a board"'
    results = _run_file_job(repo_root, tmp_path, f"{skip}\nsleep 30", f'{skip}\necho "1/2 passed, 0 failed, 1 skipped"')
    code, out, _ = _run_tail(repo_root, tmp_path / "tail", {"tests/test_x.py": _job_files(results)})
    block = _block(out)
    assert "Skipped:\n  - tests/test_x.py::test_y: needs a board\nDeselected:" in block, block
    assert "\nCounts (tests): passed 1 · failed 0 · skipped 1 ·" in block
    assert code == 0, out


def test_an_aborted_run_archives_its_logs_before_the_trap_removes_scratch(repo_root: Path, tmp_path: Path) -> None:
    root = _fake_repo(repo_root, tmp_path)
    results = tmp_path / "results"
    results.mkdir()
    (results / "test_x.log").write_text("[test_x] boom\n")
    script = tmp_path / "abort.sh"
    script.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        f'raw_dir=""\nresults_dir="{results}"\ntests_scripts_status_file="{tmp_path}/status"\n'
        f'tests_scripts_pid=""\ntests_scripts_inner_pidfile="{tmp_path}/pid"\nevidence_archived=0\n'
        f"{_cleanup_body(repo_root)}\ntrap _cleanup EXIT\nfalse\n",
    )
    done = subprocess.run(["/bin/bash", str(script)], cwd=root, capture_output=True, text=True, check=False, timeout=120)
    assert done.returncode != 0
    assert not results.exists(), "scratch must still be removed"
    (run,) = (root / "build" / "archive" / "test_sh").iterdir()
    assert (run / "results" / "test_x.log").read_text() == "[test_x] boom\n"


def test_both_renderer_calls_tolerate_their_own_failure(repo_root: Path) -> None:
    # Under `set -euo pipefail` a bare call aborts the script with the RENDERER's exit code, which
    # the caller cannot tell from a failed test - so the split above would be unreachable.
    text = _without_comments(_test_sh_text(repo_root))
    renders = [line for line in text.splitlines() if "_render_coverage.py" in line]
    assert len(renders) == 2, "expected exactly the src/ and digital_twin/ render calls"
    for line in renders:
        assert line.rstrip().endswith("|| coverage_render_failed=1"), f"unguarded renderer call: {line.strip()}"


def test_ci_gates_the_coverage_reruns_test_result_but_not_its_report(repo_root: Path) -> None:
    # Anchored inside the unit-tests-coverage JOB, not on the step name: the web tier has a step
    # called "Run unit tests with coverage" too, and that one is advisory by design.
    workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text()
    rest = workflow[workflow.index("\n  unit-tests-coverage:") + 1 :]
    next_job = re.search(r"\n  [a-z][\w-]*:\n", rest)
    job = rest[: next_job.start()] if next_job else rest
    step = job[job.index("- name: Run unit tests with coverage"):]
    step = step[: step.index("- name: Add coverage summary")]
    assert "continue-on-error" not in step, "the coverage rerun's test result must gate - that is the whole point of exit 3"
    assert 'if [ "$status" -eq 3 ]' in step, "CI must tolerate exit 3, or a broken renderer turns the job red"
    assert "scripts/test.sh --coverage" in step
    # The other half of the split: a red test result must not also swallow the report that rendered.
    reports = job[job.index("- name: Add coverage summary"):]
    assert reports.count("always() &&") == 6, "every report step in this job must publish even on a red test result"
