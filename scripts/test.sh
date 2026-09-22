#!/usr/bin/env bash
# Runs the tests/ suite under a real MicroPython Unix-port interpreter (not CPython/pytest - see
# SPECIFICATION.md Part E.1's "Why not pytest"). Builds the toolchain on first
# run via `uv run toolchain/setup_toolchain.py` (plain `setup` - building/verifying the Unix port
# is just part of what `setup`/`test` already do, there's no separate `unix` subcommand, see
# SPECIFICATION.md Part B) if the Unix port binary isn't already there, then reuses the cached build
# on subsequent runs. This now also builds the RP2040 firmware/ARM toolchain/picotool as a side
# effect of `setup` doing all four of its verification checks together - heavier than building
# just the Unix port alone, but there's no lighter-weight entry point anymore now that Unix-port
# building lives inside `setup`/`test` rather than a standalone subcommand. Set PICO_TOOLCHAIN_DIR
# to relocate the cache, or SKIP_APT=1 if the required system packages (see
# toolchain/versions.toml) are already present.
#
# --coverage: runs the same tests under the OTHER of the two Unix port binaries - build-settrace,
# the only one compiled with MICROPY_PY_SYS_SETTRACE, the rig's being built deliberately without it
# (SPECIFICATION.md Part E.5.2) - with tests/_coverage_runner.py wrapping each test file to install a
# sys.settrace line tracer scoped to src/ and digital_twin/ and record which lines actually
# executed. The merged result is handed to scripts/_render_coverage.py (a separate, self-contained
# `uv run` script - coverage.py itself only runs under CPython, never under MicroPython) TWICE -
# once per --src-dir - to render two separate reports from the one shared raw dump: an HTML report
# (htmlcov/), a Cobertura XML report (coverage.xml, for e.g. Codecov), and a markdown summary
# (coverage_summary.md) for src/, plus the digital_twin/-suffixed equivalents
# (htmlcov_digital_twin/, coverage_digital_twin.xml, coverage_summary_digital_twin.md) for
# digital_twin/ - kept as two separate reports, not one combined one, since the two scopes have
# different maturity/gating expectations (see CLAUDE.md's "Code quality tooling"). See README.md's
# "Code quality tooling" for a usage example and SPECIFICATION.md Part E.5 for the full pipeline this is one
# stage of.
#
# Also (re)builds frozen_modules/frozen_html.py via scripts/build_frozen_html.sh before every run -
# the website-placeholder module (SPECIFICATION.md Part A.9), which every generated
# sensortask_<device>.py imports unconditionally at module level. Lives in its own frozen_modules/
# MICROPYPATH segment, not ".frozen/" - see build_frozen_html.sh's own comment for why that exact
# name can't hold a real, importable file (it's a hardcoded MicroPython sentinel, confirmed against
# py/builtinimport.c).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# The Unix port links the host's real libc time.h, so time.mktime()/time.gmtime()/time.localtime()
# observe whatever $TZ the calling shell happens to have - unlike the deployed rp2 firmware, whose
# ports/rp2/datetime_patch.c overrides mktime()/localtime_r() with shared/timeutils' pure,
# TZ-agnostic epoch arithmetic (confirmed directly against both C sources). src/'s
# "time.mktime(time.gmtime())" idiom (asy_fram_manager.py, system_service.py, and others) is a
# no-op round trip only under TZ=UTC - libc's mktime() otherwise reinterprets gmtime()'s
# already-UTC fields as local time and subtracts the zone offset, corrupting the "current UTC
# timestamp" idiom by a deterministic, non-flaky ~1-2 hours (confirmed by direct reproduction: a
# non-UTC $TZ makes tests/test_ntp_fram_system_integration.py's two live-clock assertions fail
# every time, not intermittently). Pinning TZ=UTC here makes every test run reproduce CI's
# GitHub-hosted-runner behavior (implicitly UTC) regardless of the developer's own machine.
export TZ=UTC

# Ahead of every sweep below, not after them: these two checks are pure argument validation, and
# a rejected invocation must leave the live tree exactly as it found it. tests_scripts/ runs a
# nested test.sh to prove the rejection, concurrently with 85 files holding tests/_tmp scratch.
coverage=0
for arg in "$@"; do
    case "$arg" in
        --coverage) coverage=1 ;;
        *)
            echo "Unknown argument: $arg (only --coverage is supported)" >&2
            exit 1
            ;;
    esac
done

# GC_THRESHOLD=32768 re-runs the MicroPython tier through tests/_threshold_runner.py with that
# gc.threshold() set, which is CLAUDE.md's (f) stage. Unset (the default) is the (e) stage: the
# interpreter's own reactive -1, where the design has to stand up on its own first.
if [ -n "${GC_THRESHOLD:-}" ]; then
    # Validated once here rather than 85 times inside the runner: an unparseable value would
    # otherwise surface as one ValueError traceback per test file, each retried twice, with the
    # actual mistake nowhere in the rolled-up summary.
    if [[ ! "$GC_THRESHOLD" =~ ^-?[0-9]+$ ]]; then
        echo "error: GC_THRESHOLD must be an integer - 32768 is what the firmware ships, -1 the reactive default - not '$GC_THRESHOLD'" >&2
        exit 1
    fi
    # Range as well as shape, on the FIRMWARE's 32-bit word rather than this 64-bit host's: a value
    # above it can match no shippable setting, and one past the host's own word raises OverflowError
    # inside the runner instead, once per file. Length first, so bash's own arithmetic can't overflow.
    if [ "${#GC_THRESHOLD}" -gt 11 ] || [ "$GC_THRESHOLD" -gt 2147483647 ] || [ "$GC_THRESHOLD" -lt -2147483648 ]; then
        echo "error: GC_THRESHOLD=$GC_THRESHOLD is outside the rp2040's own 32-bit machine word - any negative value means the reactive default (-1 by convention, see py/modgc.c) and the firmware ships 32768" >&2
        exit 1
    fi
    if [ "$coverage" = "1" ]; then
        # Said out loud rather than silently dropped: --coverage has its own runner, and a run that
        # ignores an explicitly set threshold must not look like one that honored it.
        echo "== note: --coverage uses its own runner, so GC_THRESHOLD=$GC_THRESHOLD is ignored for this run" >&2
    fi
fi

# One-time, bounded sweep of the WHOLE tests/_tmp tree, before any test file runs - not a
# per-file/per-prefix sweep. Every test_*.py file's own per-test scratch directories
# (tests/_tmp_scratch.py's TmpScratch) already wipe and re-remove their own subtree on every run
# regardless of this, so this line exists only to bound a long-lived local sandbox's own
# tests/_tmp against anything that accumulated there before that mechanism existed (or from a
# file that was killed - e.g. a segfault, see this file's own known-segfault-cause comment below -
# before its own teardown ran). A real `rm -rf`, not a MicroPython os.listdir() loop: it costs a
# constant, negligible amount of shell/kernel work regardless of how many entries have piled up,
# so it can't itself hit the MemoryError this replaces (see this repo's tests/_tmp_scratch.py and
# tests/test_tmp_scratch.py for the mechanism that MemoryError used to come from). A no-op on
# real CI, which always starts from a fresh checkout with no tests/_tmp to begin with.
rm -rf tests/_tmp

# Same "bound a long-lived local sandbox against a killed run's leftovers" reasoning as the sweep
# above, for the one test fixture that has to live in the real tree: tests_scripts/
# test_build_website_sh.py's malformed-TOML case writes devices/zz_test_<name>.toml and removes it
# in `finally`, which a SIGKILL (the pytest job below is timeout-wrapped) defeats. A leaked file
# there is not merely untidy - scripts/_generate_sensortask_modules.py globs devices/*.toml and
# exits 1 on the first BuildError, so under `set -e` it aborts THIS script, scripts/typecheck.sh and
# both twin runners outright, naming a device nobody added. `devices/zz_test_*.toml` is therefore a
# reserved namespace for live-tree test fixtures (both halves of that reservation, and this
# sweep's own placement ahead of the generation step, are asserted by tests_scripts/test_test_sh.py);
# a real device may never be named that way. No-op on CI, which always starts from a fresh checkout.
rm -f devices/zz_test_*.toml

toolchain_dir="${PICO_TOOLCHAIN_DIR:-$HOME/pico-toolchain}"
# Two variants, built together by setup_toolchain.py. The plain run takes the settrace-FREE one:
# compiling MICROPY_PY_SYS_SETTRACE in allocates a frame and a code object per call and per
# generator resume, inflating every allocation figure 4-5x (SPECIFICATION.md Part E.5.2).
unix_dir="$toolchain_dir/micropython/ports/unix"
if [ "$coverage" = "1" ]; then
    micropython_bin="$unix_dir/build-settrace/micropython"   # --coverage needs sys.settrace itself
    want_variant="settrace"
else
    micropython_bin="$unix_dir/build-standard/micropython"
    want_variant="plain"
fi

skip_apt_flag=()
if [ "${SKIP_APT:-0}" = "1" ]; then
    skip_apt_flag=(--skip-apt)
fi

# Asks the binary which variant it is instead of trusting its path. Always exits 0, reporting an
# unusable binary as such, so `set -e` never fires from inside the command substitution below.
unix_port_variant() {
    local probe=""
    probe="$("$1" -c 'import sys; print("settrace" if hasattr(sys, "settrace") else "plain")' 2>/dev/null)" || true
    case "$probe" in
        settrace | plain) echo "$probe" ;;
        *) echo "unusable" ;;
    esac
}

if [ ! -x "$micropython_bin" ]; then
    echo "MicroPython Unix port not found at $micropython_bin - building it now" >&2
    uv run toolchain/setup_toolchain.py setup --toolchain-dir "$toolchain_dir" "${skip_apt_flag[@]}"
elif [ "$(unix_port_variant "$micropython_bin")" != "$want_variant" ]; then
    # The path stopped identifying the variant when the two builds split: a toolchain dir predating
    # that has a build-standard still carrying settrace, and it is executable - so an existence
    # check passes and the plain suite would silently measure on the 4-5x inflated binary.
    echo "== $micropython_bin is not the '$want_variant' variant - rebuilding both Unix ports" >&2
    uv run toolchain/setup_toolchain.py setup --toolchain-dir "$toolchain_dir" "${skip_apt_flag[@]}"
fi

if [ ! -x "$micropython_bin" ]; then
    echo "error: $micropython_bin is still missing after setup - rebuild with --clean" >&2
    exit 1
fi
got_variant="$(unix_port_variant "$micropython_bin")"
if [ "$got_variant" != "$want_variant" ]; then
    echo "error: $micropython_bin reports itself as '$got_variant', not the '$want_variant' variant this run needs - rebuild with: uv run toolchain/setup_toolchain.py setup --clean" >&2
    exit 1
fi

# TEST_PARALLELISM: how many test_*.py files run at once. Each file is already a fully isolated
# Unix-port OS process (its own heap, its own machine.py-fake global state) with no shared memory
# with any other file's process, so running several concurrently changes wall-clock only, never
# behavior - EXCEPT for a THIRD hazard this list did not originally name, and which is NOT closed:
# a twin test asserting that a real background state transition completed within a fixed budget is
# measuring host speed, so CPU starvation can fail it while the code under test is healthy. Found on
# the bench Pi4 (2026-09-17): test_digital_twin_sensortask_integration.py's hotspot/DNS test fails
# with "real hotspot activation never started the real DNSServer task" under the full parallel suite,
# and - decisively - reproduces with twelve synthetic CPU busy-loops and NO parallel test processes
# at all, ruling out port contention and the chroot. Which file loses is non-deterministic; a second
# file (test_digital_twin_webserver_concurrency_dev.py) lost on one run. The default that produced it
# was a flat 4x core count, i.e. 16 concurrent Unix-port processes on that 4-core host, whose cores
# are far slower than the sandbox the 4x multiplier was measured on. Not reproducible here at the
# same nominal load, and GitHub's own runners have not hit it. The autodetection below is the first
# half of the answer (it drops that host to 2x); BACKLOG.md item 28 carries what is left - do not
# assume a failure in one of those files is a code bug before checking host load.
#
# The two hazards this list DID name stay disjoint, both re-audited by enumerating every file
# (2026-09-17, not spot-checked): TmpScratch
# keys (all 29 in the suite confirmed pairwise distinct - tests/_tmp_scratch.py's own docstring; the
# per-device split above gives each of its 12 new files its own key for exactly this reason) and
# real socket ports (each file's own fixed base range, with headroom over what it actually
# allocates - see e.g. tests/_webserver_concurrency_scenarios.py's own port-range comment). That
# audit found two violations the first pass had missed. One: test_asy_wifi_service.py and
# test_asy_dns_client.py both allocated from 54000, harmless while this loop was sequential, a real
# race once it wasn't. Two, the same hazard from outside the loop entirely: the whole 51000-57000
# tier sat INSIDE the OS ephemeral range (32768-60999, /proc/sys/net/ipv4/ip_local_port_range), so
# any concurrent ephemeral socket could be handed one of those exact ports - including
# tests_scripts/'s own _free_port(), which binds (host, 0) and now runs alongside this loop rather
# than in front of it. Both failure modes are silent rather than EADDRINUSE for UDP (see
# test_asy_wifi_service.py's own comment), i.e. an inexplicable timeout, not an error. Fixed by
# moving that whole tier below the ephemeral range, where the twin tier already sat. Bases now:
# 19100 / 19300 / 19400 / 19500+ / 19700+ (twin, TCP) and 21000 / 22000 / 23000 / 24000 / 25000 /
# 26000 / 27000 (udp_socket / captive_dns / ntp_client / dns_client / ntp_wifi_dns /
# ntp_fram_system / wifi_service). A new test file that binds a socket claims an unused base below
# 32768 - never a neighbour's, never inside the ephemeral range.
#
# The multiplier is AUTODETECTED from the host's real capability, not fixed at 4x, because 4x is
# safe on a fast host and demonstrably not safe on a slow one: the same 4 cores that make a
# GitHub-hosted runner comfortable at 16 concurrent processes make the bench Pi4 starve a twin
# test's real-time budget (BACKLOG.md item 28). Core COUNT cannot tell those two apart - both are
# 4-core - so the probe below measures core SPEED instead, by timing a fixed integer loop in the
# very interpreter the tests run under (the most honest proxy available, and ~135ms on a fast x86
# host). The thresholds are calibrated against that measurement, not guessed. TEST_PARALLELISM
# still overrides everything, which is what the bench Pi4 should use if the probe ever misjudges it.
#
# THIS WHOLE BLOCK'S PLACEMENT IS LOAD-BEARING: it must stay ahead of the tests_scripts/ background
# launch below. The probe times a real process on a real host, so it measures whatever that host is
# doing at the moment it runs - and once pytest is backgrounded, that includes a fully saturated
# core set. Measured directly on this project's own 4-core x86 sandbox (2026-09-18) while the probe
# still sat after the launch: 131-141ms across 8 idle samples, but 391ms in situ, i.e. 2x/8 jobs
# where the host genuinely warrants 4x/16. The misreading cost little wall clock there only because
# the backgrounded pytest tier (263s) was the binding constraint at both settings - 4m30.9s
# autodetected vs 4m26.6s pinned at 16 - but it was non-deterministic run to run, and a heavier
# moment crossing 900ms would have picked 1x, where the MicroPython loop does exceed that floor.
# Nothing between here and the launch is needed by the probe ($micropython_bin is resolved and
# built just above), and tests_scripts/test_test_sh.py asserts this ordering.
#
# The 4x branch preserves exactly the behaviour measured below, so nothing changes on a fast runner.
#
# Defaults to 4x the runner's own core count on a fast host, not 1x: measured directly on a 4-core sandbox
# (matching a GitHub-hosted ubuntu-latest runner's core count), total `user` CPU time across the
# whole suite stayed flat (~4m21s-4m27s) at TEST_PARALLELISM 4/8/16 while wall-clock dropped
# 8m27s -> 4m28s -> 3m45s - direct confirmation the suite is genuinely sleep-bound (real SPI
# CS-settle sleeping in asy_spi_driver.py dominates each build's cost, see the per-file-timeout
# comment above), not CPU-bound, so oversubscribing well past the physical core count is close to
# "free" concurrency here. At 16, the bottleneck shifts entirely to the backgrounded tests_scripts/
# job's own single-process pytest runtime (measured: 224s, matching the 3m44.855s total almost
# exactly) - going further would need tests_scripts/ itself parallelized (e.g. pytest-xdist) to see
# any more benefit, not attempted. Override downward (e.g. TEST_PARALLELISM=1 to run the test files
# themselves one at a time - not a full return to the old strictly-sequential behavior, since the
# backgrounded tests_scripts/ job holds that single slot until it finishes, so the first test file
# only starts once pytest is done - or a smaller multiple) if a future file is ever found to violate
# one of the two collision-safety assumptions above, or if a given runner's real memory/CPU-quota
# limits make 4x too aggressive.
#
# One caveat on "sleep-bound", since that was measured as `user` CPU time, which excludes the
# kernel, so a file doing heavy filesystem work would not show up in it at all. Nothing in the
# suite does today: the whole run writes ~46MB and spends ~8.7s of system time (measured directly,
# 2026-09-17). It used to be ~10x that, because tests/test_tmp_scratch.py created and removed
# 400,000 flat sibling directories in the shared tests/_tmp root on every run - ~396MB of writes
# and ~18.6s of system time by itself, serialized on one directory inode's own lock that every
# other file's TmpScratch construction also has to take. That test now asserts the invariant
# directly instead (see its own comment), which is both cheaper and stronger. Keep it that way:
# CLAUDE.md's hard rule on avoidable hardware wear covers the host's own disk, not just the
# target's flash, and a second file of that shape would contend with everything else here rather
# than overlap with it.
_detect_parallelism() {
    local cores quota period probe_start probe_end probe_ms multiplier
    cores="$(nproc 2>/dev/null || echo 4)"
    # A container's CPU quota bounds real parallelism far below what nproc reports (cgroup v2; v1
    # and "max" both fall through to the nproc value unchanged).
    if [ -r /sys/fs/cgroup/cpu.max ]; then
        read -r quota period < /sys/fs/cgroup/cpu.max || true
        if [ "${quota:-max}" != "max" ] && [ "${period:-0}" -gt 0 ] 2>/dev/null; then
            local quota_cores=$(( (quota + period - 1) / period ))
            [ "$quota_cores" -ge 1 ] && [ "$quota_cores" -lt "$cores" ] && cores="$quota_cores"
        fi
    fi
    # Speed probe. Never allowed to fail the run: any error, and we fall through to the fast-host
    # multiplier, i.e. exactly the previous behaviour.
    probe_start="$(date +%s%N 2>/dev/null || echo 0)"
    "$micropython_bin" -c 'x=0
for i in range(500000):
    x+=i' >/dev/null 2>&1 || true
    probe_end="$(date +%s%N 2>/dev/null || echo 0)"
    # An unusable clock resolves to 0, NOT to whatever the arithmetic happens to produce. Taking the
    # difference unguarded made the two clock-failure directions disagree: a failed SECOND date gave
    # a negative probe_ms (fast branch, as intended), but a failed FIRST one left probe_start at 0
    # and made probe_ms the epoch in milliseconds - the 1x branch, i.e. the slowest possible answer
    # from the failure the comment below promises is always the fastest. The -gt guards also absorb
    # a `date` that prints a literal "%N" instead of nanoseconds, which is the realistic way to get
    # here at all (GNU coreutils never fails outright).
    if [ "$probe_start" -gt 0 ] 2>/dev/null && [ "$probe_end" -gt "$probe_start" ] 2>/dev/null; then
        probe_ms=$(( (probe_end - probe_start) / 1000000 ))
    else
        probe_ms=0
    fi
    # A failed probe lands here too, and deliberately so: its probe_ms is <= 0, which picks the
    # fast-host multiplier, i.e. exactly the behaviour this autodetection replaced. Never silently
    # slower than before because the probe itself broke.
    if [ "$probe_ms" -le 250 ]; then
        multiplier=4            # fast host (measured: 131-141ms on this project's own x86 sandbox)
    elif [ "$probe_ms" -le 900 ]; then
        multiplier=2            # mid host - the bench Pi4's class; halves the oversubscription
    else                        # that starved a twin test's real-time budget at 4x
        multiplier=1
    fi
    echo "$(( cores * multiplier )) $cores $multiplier $probe_ms"
}
if [ -n "${TEST_PARALLELISM:-}" ]; then
    max_parallel="$TEST_PARALLELISM"
    echo "== Test parallelism: $max_parallel (TEST_PARALLELISM override)"
else
    read -r max_parallel _cores _multiplier _probe_ms < <(_detect_parallelism)
    echo "== Test parallelism: $max_parallel ($_cores usable cores x $_multiplier, interpreter speed probe ${_probe_ms}ms)"
fi
# Clamped to >= 1: the dispatch loop below blocks while the running-job count is >= max_parallel, so
# a 0 or negative value (a plausible "turn parallelism off" guess - 1 is what actually does that)
# makes that `wait -n || true` spin forever without ever dispatching a test. Confirmed directly, and
# a hang is exactly what this script's own standing backstops exist to rule out (CLAUDE.md).
if ! [ "$max_parallel" -ge 1 ] 2>/dev/null; then
    echo "== TEST_PARALLELISM=${TEST_PARALLELISM:-} is not a positive integer - falling back to 1 (sequential)" >&2
    max_parallel=1
fi

# No static src/sensortask_wozi.py/sensortask_dev.py exist any more (SPECIFICATION.md
# Part L.2) - every device's own sensortask_<device>.py is generated fresh here, via
# buildgen, into build/generated_src/ (gitignored - see scripts/_generate_sensortask_modules.py's
# own docstring for why NOT into src/ itself). tests/_sensortask_scenarios.py (dynamic __import__()
# per device) and every tests/test_digital_twin_*.py file that statically imports a sensortask_<device>
# module keep working unchanged: MICROPYPATH below puts this directory first, so `import
# sensortask_wozi` resolves to the freshly generated module.
#
# Runs BEFORE tests_scripts/ is backgrounded below, not after - see that block's own comment for
# the devices/*.toml race this ordering closes.
echo "== Generating buildgen device modules into build/generated_src/"
uv run scripts/_generate_sensortask_modules.py

# tests_scripts/ is genuinely independent of everything below this point - real CPython/pytest code
# (never MICROPYPATH/build/generated_src/frozen_modules-dependent, see tests_scripts/conftest.py's
# own docstring) that only ever touches pytest's own isolated tmp_path fixtures or OS-assigned free
# ports (test_digital_twin_generated_boot.py's own _free_port()), never this repo's real
# build/generated_src/ or frozen_modules/ - confirmed directly, no test file in tests_scripts/
# references either outside a tmp_path. So it needs nothing from the setcap/frozen_html/
# frozen_website steps below, and backgrounding it here - instead of the old placement
# right before the MicroPython test-file loop - overlaps its own real ~4-minute wall-clock (measured
# directly: 247.93s under pytest's own timer) with essentially the *entire* rest of this script
# rather than serializing in front of it. Counted the same as any other job against
# max_parallel/TEST_PARALLELISM above (it backgrounds itself the same way, into the same shell), not
# an extra unbounded process on top of that budget - same "everything here is a fully isolated OS
# process" reasoning the job-pool comment below already gives, just applied one job earlier.
#
# timeout-wrapped like every test file in the loop below, for the same standing "hanging tests are
# never allowed" reason (CLAUDE.md) - it was the one job in this pool without one, which mattered
# more once it moved here: a hung pytest holds the final `wait` open indefinitely, and nothing else
# in this script would ever time it out. No retry, unlike the per-file loop: that retry exists for
# transient runner contention on a single file's own budget, where a whole-suite pytest timeout is
# a real failure worth reporting as one. 1200s is ~5x its measured ~248s, so it only ever fires on
# a genuine hang, never on ordinary slowness. CI's own timeout-minutes stays the outer backstop,
# not the defense (see .github/workflows/ci.yml's own comment on that distinction).
#
# MUST stay behind the buildgen generation step above, which globs devices/*.toml: one
# tests_scripts/ test (test_build_website_sh.py's malformed-TOML case) writes a throwaway
# devices/zz_test_*.toml into the live tree and removes it again, and build_website.sh resolves
# devices/<device>.toml from the repo root, so it cannot be given a tmp_path tree instead. Generated
# first, that file's brief existence is never observed; backgrounded first, a glob landing inside
# that window aborts the whole run under `set -e` with a BuildError naming a device nobody added.
# Nothing else in the foreground re-globs devices/ once generation is done (the test loop reads the
# generated wiring-plan JSONs, and build_website.sh below names one device explicitly).

echo "== Running tests_scripts/ (CPython-side build-tooling tests)"
tests_scripts_status_file="$(mktemp)"
tests_scripts_timeout_s="${TESTS_SCRIPTS_TIMEOUT_S:-1200}"
# Pre-declared empty and the trap armed HERE, before the background job exists - not alongside the
# two mktemp -d calls further down. Bash does not kill its background jobs when the parent exits,
# and every step between this point and there (setcap, the two frozen-module builds) can abort under
# `set -e`: an orphaned pytest would then keep running for up to its own timeout and transiently
# write a devices/zz_test_*.toml into the live tree, re-opening the very glob hazard the generation
# ordering above closes. Both halves confirmed directly by reproducing the pattern: with no trap the
# inner `timeout` outlives the aborted parent, with this one it is gone. `rm -rf ""` is a harmless no-op for either dir before its mktemp has run,
# and tests_scripts_pid is cleared once the job is reaped so this can never signal a recycled PID.
raw_dir=""
results_dir=""
tests_scripts_pid=""
tests_scripts_inner_pidfile="$(mktemp)"
# shellcheck disable=SC2329  # invoked indirectly, by the `trap _cleanup EXIT` below
_cleanup() {
    # The subshell alone is not enough to kill: its `timeout` child would be reparented and keep
    # running (with pytest under it) for the rest of its own budget. The subshell therefore records
    # that child's pid, so both are signalled by pid - exact, and with no dependency on pkill/procps,
    # which a --variant=minbase chroot does not have. `timeout` forwards the signal to pytest
    # itself, so one SIGTERM takes the whole chain down.
    if [ -n "$tests_scripts_pid" ]; then
        inner="$(cat "$tests_scripts_inner_pidfile" 2>/dev/null || true)"
        if [ -n "$inner" ]; then
            kill "$inner" 2>/dev/null || true
        fi
        kill "$tests_scripts_pid" 2>/dev/null || true
    fi
    rm -rf "$raw_dir" "$results_dir" "$tests_scripts_status_file" "$tests_scripts_inner_pidfile"
}
trap _cleanup EXIT
(
    timeout --kill-after=10 "$tests_scripts_timeout_s" uv run pytest tests_scripts -q &
    inner_pid=$!
    echo "$inner_pid" >"$tests_scripts_inner_pidfile"
    if wait "$inner_pid"; then
        echo "PASS" >"$tests_scripts_status_file"
    else
        ec=$?
        if [ "$ec" -eq 124 ]; then
            echo "== tests_scripts/ exceeded ${tests_scripts_timeout_s}s - treating as a real failure instead of hanging the job" >&2
        fi
        echo "FAIL" >"$tests_scripts_status_file"
    fi
) &
tests_scripts_pid=$!

# tests/test_digital_twin_sensortask_integration.py's own hotspot/DNS test binds the real
# privileged port 53 (src/captive_dns.py's DNSServer) from a genuine, organically-triggered hotspot
# scenario - a GitHub Actions runner (or any non-root dev environment) can't bind that port without
# either running as root or holding this specific capability on the interpreter binary. Same
# mechanism, same "reapply every invocation" reasoning (GNU tar doesn't preserve xattrs, so a
# capability baked into a cached binary wouldn't survive the cache round-trip) as
# scripts/run_digital_twin_ci.sh's own identical grant for its own real-port-53 DNS proof.
echo "== Granting CAP_NET_BIND_SERVICE to $micropython_bin (needed for the real port-53 DNS server test)"
if [ "$(id -u)" -eq 0 ]; then
    setcap 'cap_net_bind_service=+ep' "$micropython_bin"
else
    sudo setcap 'cap_net_bind_service=+ep' "$micropython_bin"
fi

# frozen_modules/frozen_html.py (SPECIFICATION.md Part A.9) is a plain build artifact, never
# committed (see .gitignore) - regenerated fresh on every run, cheap (sub-second, no toolchain
# involved), unlike the Unix-port build above. src/sensortask_wozi.py does a module-level `import
# frozen_html`, so every test file that imports it (not just the webserver-specific ones) needs
# this to already exist on MICROPYPATH before the test loop below runs.
echo "== Building frozen_modules/frozen_html.py"
scripts/build_frozen_html.sh

# A second, real-content frozen module (SPECIFICATION.md Part H.7) alongside the html_stub one
# above - same "cheap, no toolchain involved" property, built fresh every run. Only
# tests/test_website_build_integration.py imports it (as `frozen_website_wozi`, its own distinct
# module name - see scripts/build_website.sh), so it never conflicts with frozen_html's own /html
# mount; every other test file is unaffected by its presence on MICROPYPATH.
echo "== Building frozen_modules/frozen_website_wozi.py"
scripts/build_website.sh wozi frozen_modules/frozen_website_wozi.py

# tests_scripts/ itself (CPython-side build-tooling tests: scripts/build_frozen_html.sh, scripts/
# build_website.sh, scripts/build_firmware.py - SPECIFICATION.md Part B.11's "fully verified"
# follow-up; see tests_scripts/conftest.py's own docstring for why these run under CPython/pytest
# rather than the MicroPython Unix port loop below) is already running in the background, launched
# right after the toolchain check above - nothing here. RUN_SLOW_FIRMWARE_BUILD is deliberately left
# unset for that run, so the one real (but cheap, ~1 minute with a warm toolchain) ARM firmware
# compile it gates stays opt-in for fast local iteration - .github/workflows/ci.yml's
# firmware-build-verify job is what actually sets it.

if [ "$coverage" = "1" ]; then
    raw_dir="$(mktemp -d)"
fi
# One shared results_dir regardless of --coverage: every parallel test-file job (below) writes its
# own PASS/FAIL status here instead of returning it as its own process exit code or mutating a
# shared bash array from a background subshell (which wouldn't be visible to the parent shell).
# Both dirs are cleaned by the single EXIT trap armed with the pytest job above - bash's `trap ...
# EXIT` replaces any previously registered EXIT handler outright rather than stacking, so every
# cleanup this script needs has to live in that one trap.
results_dir="$(mktemp -d)"

failed=0
# Per-file timeout with two retries (three attempts total), not just the job-level
# timeout-minutes in ci.yml. This dates from an earlier phase of the CI-hang investigation, when
# the leading theory was GitHub Actions runner-level contention; that theory was wrong (see
# CLAUDE.md's "CI hang investigation" note for the real root cause: 17 tests in
# test_asy_uart_driver.py relying on real select.poll() against a fake UART, fixed by swapping in
# _StepPoller). This timeout/retry, and the stdbuf line-buffering below, didn't fix the hang and
# aren't required for it (an isolation test with both reverted, running only the _StepPoller fix,
# passed 8/8 clean CI jobs) - they're kept as a standing "hanging is never allowed" backstop
# against any *future* hang, not as the fix for this one. 180s is a deliberate multiple of the
# slowest observed healthy file (test_asy_sgp40_driver.py's real-time FRAM backup/restore tests,
# ~90s worst case seen in CI) - generous enough to never false-positive-kill a legitimately slow
# file, while being far below the 30-minute job cap. Two retries absorb transient contention
# without ever failing the whole job for infra noise; a third consecutive timeout on the same
# file is treated as a real failure. --kill-after guarantees the process is gone even if SIGTERM
# alone doesn't land. Worst case for one stuck file is 3 * (180 + 10)s = ~9.5 minutes, still
# comfortably under the job cap even if it happens more than once in the same run.
#
# stdbuf -oL -eL forces line buffering instead of MicroPython's default full block buffering
# (4096 bytes) whenever stdout isn't a tty - true for any GH Actions step. Harmless and cheap to
# keep even though it turned out not to be what was causing the hang (see above); small,
# immediate, line-buffered writes are still a reasonable default for CI log output.
#
# -X heapsize=16M (default 2097152 = 2MB) - history of this value, most recent first:
#
# WP1+WP2 (CLAUDE.md's implicit-FRAM-wiring rule) made the former, monolithic
# tests/test_sensortask.py build all 6 real devices' full graphs repeatedly across ~330 test
# functions IN ONE PROCESS, pushing this from 8M to 32M (8M/16M both still failed with real
# MemoryErrors partway through that file at the time - 81/321 and 176/321 passed respectively).
# Fixed at the root, not worked around: splitting that file by device (six
# tests/test_sensortask_<device>.py files, 55 builds per process instead of 330 - see
# tests/_sensortask_scenarios.py's own docstring) let its own heaviest per-device file
# (tests/test_sensortask_dev.py) pass cleanly even at 4M in isolation.
#
# That alone didn't let this shared flag come down, though: a full-suite run at a lower value
# surfaced two OTHER, unrelated files that had never failed at 32M. Both were root-caused, not
# patched over with a gc.collect() call (forbidden as a stabilization tool in this codebase, and
# confirmed directly this session not to even work for one of the two - see git history around
# 2026-09-17 for the reverted attempt) or a per-file heap override (would only have hidden the
# same symptom, not fixed it):
#
# - tests/test_digital_twin_sensortask_integration.py had the exact same "many real devices' full
#   graphs in one process" shape the old test_sensortask.py did (its own "construction across
#   every real device" section: 18 real, socket-backed build_system() calls sharing one process
#   with this file's own ~11 wozi-only heavy tests). Fixed the same way: split that section out
#   into tests/_digital_twin_construction_scenarios.py + six
#   tests/test_digital_twin_construction_<device>.py files, cutting the worst case sharing one
#   process from ~29 real builds down to this file's own ~11.
#
# - tests/test_digital_twin_bus_hazard_concurrency.py's own dev-variant concurrent-bus-load
#   scenario is a genuinely different mechanism, confirmed by direct isolated bisection (no other
#   process running, so not a contention artifact): it reproducibly misses its own fixed 9-second
#   real-clock budget for real background sensor tasks to produce real data at 8M, in EVERY
#   isolated run, with no external contention needed at all - and a gc.collect() call placed right
#   before that budget starts had zero effect on the outcome (also confirmed directly, then
#   reverted). This is not an accumulation problem a split can fix (this file is already
#   deliberately wozi/dev-scoped, not parametrized across all 6 devices, specifically to avoid
#   the opposite problem - see that file's own docstring) - it is this specific test genuinely
#   needing more real-time margin against GC overhead at lower heap. Bisected cleanly in isolation:
#   fails at 8M, passes at 16M and every value tried above it. Not chased further into changing
#   this test's own real-time budget (run_seconds) - that changes what the test actually proves,
#   not a test-harness knob, and wasn't this session's call to make unilaterally.
#
# 16M is therefore the real, validated floor across every file in the suite as of this session,
# not a re-run of the same "guess and check the whole suite" approach that got 32M picked before
# - confirmed by an actual full-suite scripts/test.sh run at this value. This is a Unix-port-only
# test-harness setting - unrelated to the real rp2040's own RAM budget (SPECIFICATION.md Part
# F.1): real hardware only ever builds one device's own object graph once per boot, never several
# devices' worth of graphs repeatedly in one process - and every test file still runs under the
# same GC the real target uses either way.
per_file_timeout_s="${PER_FILE_TIMEOUT_S:-240}"
# Raised from 180 to 240 alongside the WP1 webserver-startup-race fix above:
# the real-socket concurrency scenarios now in tests/_webserver_concurrency_scenarios.py were, as
# one then-monolithic file, already the single heaviest in this suite (measured standalone: ~230s
# even before WP1, ~11s of that actual CPU time - the rest is those scenario bodies' own deliberate
# sleeps simulating realistic timeouts/flaky connections, not busy work), so it was already running
# close to the old 180s ceiling before this change. WP1 making webserver.pr real-FRAM-backed needed
# its own ~15-call-site wait bumped from 0.1s to a measured-safe 0.5s (see that module's own comment
# for why a polling readiness check made things worse, not better, and was reverted) - a real ~35s
# addition on top of an already-marginal baseline, not a large one, but 180s no longer had real
# margin. That "240s clears this file with room to spare" claim has since gone stale, corrected
# below.
#
# Per-file overrides for files that grew past the 240s default outright - not a hang, and not fixed
# by raising everyone's default (that would just make a genuine future hang 2-3x slower to detect
# for the other ~70 files that still comfortably fit in 240s). Empty as of the tests/test_sensortask_
# <device>.py / tests/test_digital_twin_webserver_concurrency_<device>.py split (see those two
# modules' own tests/_sensortask_scenarios.py / tests/_webserver_concurrency_scenarios.py library
# docstrings): the former monolithic files (447s/268s real, single-process, all 6 devices in one
# run) needed their own override; measured directly, not estimated, each split-out family's own
# per-device file runs in ~90s (sensortask_*) / ~45s (webserver_concurrency_*) standalone -
# comfortably inside the 240s default with real margin (re-measure and re-add an entry here if a
# future device/scenario addition ever pushes one back past it). Running all 6 of one family's
# files at once (the common case once TEST_PARALLELISM > 1, resolved above) took 114.8s / 59.5s wall-clock
# total, not 6x a single file's own time: almost all of each build's cost is real wall-clock SPI
# CS-settle sleeping (asy_spi_driver.py), not CPU work (measured: ~35s of user CPU time across the
# whole ~9-minute *sequential* 6-file sensortask run), so concurrent processes barely contend with
# each other even beyond the host's own core count.
declare -A per_file_timeout_overrides_s=()
max_attempts=3

# SPECIFICATION.md Part I.4(e): zero MemoryErrors, caught-and-logged included - a caught
# allocation failure is a design defect, not a passing result. The twin tier already asserts this
# on its own logs (_digital_twin_ci_suite.py); this is the same check for the tier (e)/(f) run in.
_flag_memory_errors() {
    local tag="$1" log_file="$2"
    # Both spellings, because src/'s degrade handlers log str(e) and not the class: a real caught
    # allocation failure prints "memory allocation failed, ..." (py/runtime.c:1692/1696) with no
    # "MemoryError" in it, so the class name alone only ever sees an UNCAUGHT traceback.
    local pattern="MemoryError|memory allocation failed"
    if grep -qE "$pattern" "$log_file" 2>/dev/null; then
        grep -m5 -E "$pattern" "$log_file" >"$results_dir/$tag.memerr"
    fi
}

# Runs one test_*.py file's own timeout+retry loop to completion and writes PASS/FAIL to
# status_file - never returns a nonzero exit status itself (failure is communicated through the
# status file, not the function's own return code), so backgrounding this behind `&` and reaping it
# with `wait`/`wait -n` below never trips this script's own `set -e`.
run_test_file() {
    local test_file="$1"
    local status_file="$2"
    local tag cmd file_timeout_s attempt ec log_file
    tag="$(basename "$test_file" .py)"
    log_file="$results_dir/$tag.log"
    echo "== Running $test_file"
    # .frozen must be included explicitly: MICROPYPATH replaces MicroPython's default sys.path
    # rather than extending it, and the default path is what makes frozen-in modules (asyncio
    # included) resolvable at all. Confirmed directly against the built interpreter - dropping
    # this breaks `import asyncio` for any async src/ file with no import error pointing at why.
    # frozen_modules must be included too - the generated sensortask_<device>.py's own `import
    # frozen_html` resolves there (see build_frozen_html.sh's comment for why it can't be
    # ".frozen" itself). build/generated_src listed first: makes `import sensortask_wozi`/
    # `sensortask_dev` resolve to the freshly buildgen-generated module built above, not any
    # same-named file that might otherwise be found elsewhere on this path.
    if [ "$coverage" = "1" ]; then
        cmd=(tests/_coverage_runner.py "$test_file" "$raw_dir/$tag.json")
    elif [ -n "${GC_THRESHOLD:-}" ]; then
        # CLAUDE.md's (f) stage: the same suite again with the value the firmware ships, layered on
        # a design that already passes at the reactive default. Never a substitute for that run.
        cmd=(tests/_threshold_runner.py "$test_file" "$GC_THRESHOLD")
    else
        cmd=("$test_file")
    fi
    file_timeout_s="${per_file_timeout_overrides_s[$test_file]:-$per_file_timeout_s}"
    for attempt in $(seq 1 "$max_attempts"); do
        # Truncated per attempt: only the attempt that decided this file's verdict is searched for
        # a MemoryError, so a timed-out earlier attempt's partial output cannot fail a passing file.
        : >"$log_file"
        # 2>&1 | sed, not two separate streams: several of these now run concurrently, and
        # per-line tagging (rather than relying on stdout/stderr ordering alone) is what keeps a
        # multi-file log human-readable. `set -o pipefail` (top of file) makes the pipeline's own
        # exit status the real interpreter's (timeout's) - sed itself only ever exits 0/nonzero on
        # its own unrelated failure, never masking a real 124/1 from the command it's piping.
        if MICROPYPATH="build/generated_src:src:tests:frozen_modules:.frozen" stdbuf -oL -eL timeout --kill-after=10 "$file_timeout_s" "$micropython_bin" -X heapsize=16M "${cmd[@]}" 2>&1 | sed -u "s/^/[$tag] /" | tee -a "$log_file"; then
            ec=0
        else
            ec=$?
        fi
        if [ "$ec" -eq 0 ]; then
            _flag_memory_errors "$tag" "$log_file"
            echo "PASS" >"$status_file"
            return 0
        elif [ "$ec" -eq 124 ] && [ "$attempt" -lt "$max_attempts" ]; then
            echo "== $test_file exceeded ${file_timeout_s}s on attempt $attempt/$max_attempts - retrying in case of transient runner contention" >&2
            continue
        else
            if [ "$ec" -eq 124 ]; then
                echo "== $test_file exceeded ${file_timeout_s}s on all $max_attempts attempts - treating as a real failure instead of hanging the job" >&2
            fi
            _flag_memory_errors "$tag" "$log_file"
            echo "FAIL" >"$status_file"
            return 0
        fi
    done
}

# Dispatch order: heaviest-known files first, not plain alphabetical glob order. The job pool
# below fills max_parallel slots in whatever order test_files lists them - alphabetical glob order
# clusters same-prefix heavy files together (all six tests/test_sensortask_<device>.py sort
# adjacent to each other, as do all six tests/test_digital_twin_webserver_concurrency_<device>.py
# plus tests/test_digital_twin_{bus_hazard_concurrency,sensortask_integration,uart_link}.py), so
# several of the suite's heaviest files end up competing for the same few slots at once instead of
# overlapping with the ~60 sub-second files that could otherwise fill in around them - confirmed
# directly (2026-09-17): running all 6 tests/test_sensortask_<device>.py files at once (their own
# natural glob-order cluster) took 114.8s wall-clock even though only one core's worth of real work
# is needed per slot. Measured standalone times for every tests/test_*.py file that same session,
# sorted descending - the fifteen heaviest, listed here so they each grab a slot immediately rather
# than queueing behind their own same-prefix siblings. Order among these fifteen doesn't matter
# much (they're comparable magnitude, ~50-116s each); what matters is each getting its own slot as
# early as possible. Hand-curated from that one measurement run, not dynamically computed - re-measure
# and update this list if the suite's file-cost distribution shifts meaningfully (a new heavy file
# added, or one of these split further the way the two originally-monolithic files already were).
_heavy_files_priority=(
    tests/test_digital_twin_bus_hazard_concurrency.py
    tests/test_sensortask_dev.py
    tests/test_asy_wifi_service.py
    tests/test_digital_twin_sensortask_integration.py
    tests/test_sensortask_wozi.py
    tests/test_uart_comm_hazard.py
    tests/test_asy_sgp40_driver.py
    tests/test_sensortask_schlafzi.py
    tests/test_sensortask_klkizi.py
    tests/test_sensortask_grkizi.py
    tests/test_sensortask_arzi.py
    tests/test_bus_hazard_generated.py
    tests/test_digital_twin_webserver_concurrency_dev.py
    tests/test_digital_twin_uart_link.py
    tests/test_digital_twin_webserver_concurrency_wozi.py
)
all_test_files=(tests/test_*.py)
declare -A _dispatched=()
test_files=()
for test_file in "${_heavy_files_priority[@]}"; do
    if [ -f "$test_file" ] && [ -z "${_dispatched[$test_file]:-}" ]; then
        test_files+=("$test_file")
        _dispatched[$test_file]=1
    fi
done
for test_file in "${all_test_files[@]}"; do
    if [ -z "${_dispatched[$test_file]:-}" ]; then
        test_files+=("$test_file")
        _dispatched[$test_file]=1
    fi
done

for test_file in "${test_files[@]}"; do
    # Bound concurrency at max_parallel: block here (reaping any one finished job with `wait -n`)
    # before starting a new one once that many are already running. `|| true` on both `wait -n`
    # calls below: a job's own function body always returns 0 (see run_test_file's own comment), so
    # a nonzero `wait -n` here can only mean "no background jobs left" (bash returns 127) - a
    # harmless race against this same loop's own job count check, never a real test failure to
    # propagate through `set -e`.
    while [ "$(jobs -rp | wc -l)" -ge "$max_parallel" ]; do
        wait -n || true
    done
    status_file="$results_dir/$(basename "$test_file" .py).status"
    run_test_file "$test_file" "$status_file" &
done
wait || true
tests_scripts_pid=""  # reaped by the `wait` above - cleared so the EXIT trap can't signal a recycled PID

# The tests_scripts/ background job (started before this loop, see the toolchain-check block
# above) is reaped by the same unqualified `wait` just above like any other job; its own status
# file is written unconditionally in both its PASS and FAIL branches, so a missing/empty read here
# would itself be a bug, not a legitimate "still running" state - never treated as PASS by omission.
tests_scripts_result="$(cat "$tests_scripts_status_file" 2>/dev/null)"
if [ "$tests_scripts_result" != "PASS" ]; then
    tests_scripts_result="FAIL"
fi

failed_files=()
memory_error_files=()
passed_count=0
for test_file in "${test_files[@]}"; do
    tag="$(basename "$test_file" .py)"
    status_file="$results_dir/$tag.status"
    if [ "$(cat "$status_file" 2>/dev/null)" = "PASS" ]; then
        passed_count=$((passed_count + 1))
    else
        failed=1
        failed_files+=("$test_file")
    fi
    # Independent of pass/fail: a file that degraded gracefully and passed is exactly the silent
    # case this exists for, and one that failed still names the allocation as the likelier cause.
    if [ -s "$results_dir/$tag.memerr" ]; then
        failed=1
        memory_error_files+=("$test_file")
    fi
done

if [ "$coverage" = "1" ]; then
    echo "== Rendering coverage report"
    uv run scripts/_render_coverage.py --raw-dir "$raw_dir" --src-dir src --html-dir htmlcov --xml-file coverage.xml --markdown-file coverage_summary.md
    echo "== Rendering digital_twin/ coverage report"
    uv run scripts/_render_coverage.py --raw-dir "$raw_dir" --src-dir digital_twin --html-dir htmlcov_digital_twin --xml-file coverage_digital_twin.xml --markdown-file coverage_summary_digital_twin.md
fi

# One rolled-up summary at the very end - each test_*.py file and tests_scripts/ already print
# their own pass/fail as they run, but nothing aggregated that across the whole suite before this;
# a failure earlier in a long run was otherwise easy to miss without scrolling back through the log.
total_files=$((passed_count + ${#failed_files[@]}))
echo ""
echo "== Test summary =="
echo "tests_scripts/ (CPython/pytest): $tests_scripts_result"
echo "tests/test_*.py (MicroPython Unix port): $passed_count/$total_files files passed"
if [ "${#failed_files[@]}" -gt 0 ]; then
    echo "Failed files:"
    for f in "${failed_files[@]}"; do
        echo "  - $f"
    done
fi
if [ "${#memory_error_files[@]}" -gt 0 ]; then
    echo "MemoryError seen (caught-and-logged counts too - SPECIFICATION.md Part I.4(e)):"
    for f in "${memory_error_files[@]}"; do
        echo "  - $f"
        sed "s/^/      /" "$results_dir/$(basename "$f" .py).memerr"
    done
fi
if [ "$failed" -eq 0 ] && [ "$tests_scripts_result" = "PASS" ]; then
    echo "Result: ALL PASSED"
else
    echo "Result: FAILED"
fi

if [ "$tests_scripts_result" = "FAIL" ]; then
    failed=1
fi
exit "$failed"
