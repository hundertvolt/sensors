#!/usr/bin/env bash
# Runs the tests/ suite under a real MicroPython Unix-port interpreter, not CPython/pytest
# (SPECIFICATION.md Part E.1's "Why not pytest"; Part E.3 for the runner), plus the backgrounded
# tests_scripts/ pytest tier. Builds the toolchain on first run and reuses the cache after.
#
# PICO_TOOLCHAIN_DIR relocates that cache; SKIP_APT=1 skips the system-package step. The build is
# `setup_toolchain.py setup`, which verifies all four artifacts together - there is no lighter
# Unix-port-only entry point (SPECIFICATION.md Part B).
#
# --coverage runs the same tests under build-settrace, the only variant compiled with
# MICROPY_PY_SYS_SETTRACE, and renders two reports (src/ and digital_twin/) from one raw dump.
# The whole pipeline, and why it needs its own binary: SPECIFICATION.md Parts E.5 and E.5.2.
#
# Also rebuilds frozen_modules/frozen_html.py before every run - the website placeholder every
# generated sensortask_<device>.py imports at module level. Why frozen_modules/ rather than
# .frozen/, which is a hardcoded MicroPython import sentinel: SPECIFICATION.md Part A.9.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# The Unix port's time.mktime() calls the host's real libc, which reads $TZ - unlike the rp2
# firmware's TZ-agnostic override - so src/'s time.mktime(time.gmtime()) idiom is only a no-op round
# trip under UTC. Not a production bug; CLAUDE.md's "Local test runs pin $TZ" has the account.
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

# One bounded sweep of the whole tests/_tmp tree before any test file runs, not a per-file one -
# SPECIFICATION.md Part E.1 has why it exists at all and why it is `rm -rf` rather than a
# MicroPython listdir loop.
rm -rf tests/_tmp

# Same reasoning, for the one test fixture that has to live in the real tree. What the reserved
# devices/zz_test_*.toml namespace is, what a leaked one breaks, and why this sweep must precede the
# generation step: SPECIFICATION.md Part E.1.
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

# TEST_PARALLELISM: how many test_*.py files run at once. Each file is its own Unix-port process
# with its own heap and its own fake-hardware state, so concurrency changes wall clock only - as
# long as the two per-file resources SPECIFICATION.md Part E.1 names stay disjoint.
#
# One hazard is NOT closed: a twin test asserting a real background transition inside a fixed budget
# measures host speed, so CPU starvation fails it while the code is healthy. Reproduced with twelve
# busy-loops and no parallel test processes at all - BACKLOG.md item 28 carries what is left.
#
# So the multiplier is autodetected from core SPEED, not core count: the same 4 cores are
# comfortable at 16 processes on a fast x86 host and starve a Pi4 (item 28 has the thresholds and
# the calibration). TEST_PARALLELISM overrides everything, which is the escape hatch if it misjudges.
#
# THIS BLOCK'S PLACEMENT IS LOAD-BEARING: it must stay ahead of the tests_scripts/ background
# launch, because the probe times a real process on a real host and would otherwise measure a
# saturated core set (391ms against 131-141ms idle). tests_scripts/test_test_sh.py asserts it.
#
# Oversubscribing is close to free because the suite is sleep-bound, not CPU-bound: `user` CPU time
# stayed flat across 4/8/16 while wall clock dropped 8m27s -> 3m45s. At 16 the binding constraint is
# the backgrounded pytest tier's own single-process runtime, so going further would need it split.
#
# "Sleep-bound" was measured as `user` time, which excludes the kernel - so keep it true: the whole
# run writes ~46MB and spends ~8.7s of system time today, and CLAUDE.md's rule against avoidable
# wear on the host's own disk is what retired the one file that made it ~10x that.
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
    # An unusable clock resolves to 0, never to whatever the arithmetic produces: a failed FIRST
    # `date` would otherwise leave probe_start at 0 and make probe_ms the epoch, picking the SLOWEST
    # branch from a failure that is meant to always pick the fastest.
    #
    # The -gt guards also absorb a `date` printing a literal "%N" rather than nanoseconds, which is
    # the realistic way to get here at all - GNU coreutils never fails outright.
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
# Clamped to >= 1: the dispatch loop blocks while running jobs >= max_parallel, so 0 or negative (a
# plausible "turn parallelism off" guess - 1 is what does that) spins `wait -n` forever without
# dispatching anything. A hang is what this script's standing backstops exist to rule out.
if ! [ "$max_parallel" -ge 1 ] 2>/dev/null; then
    echo "== TEST_PARALLELISM=${TEST_PARALLELISM:-} is not a positive integer - falling back to 1 (sequential)" >&2
    max_parallel=1
fi

# No static src/sensortask_<device>.py exists any more (SPECIFICATION.md Part L.2): each is
# generated fresh here into gitignored build/generated_src/, which MICROPYPATH below puts first so
# every static and dynamic import of one resolves to the fresh module.
#
# Runs BEFORE tests_scripts/ is backgrounded, not after - Part E.1 has the devices/*.toml race that
# ordering closes.
echo "== Generating buildgen device modules into build/generated_src/"
uv run scripts/_generate_sensortask_modules.py

# tests_scripts/ needs nothing from the setcap or frozen-module steps below: it is real CPython
# touching only pytest's tmp_path fixtures and OS-assigned free ports, never this repo's real
# build/generated_src/ or frozen_modules/ (tests_scripts/conftest.py's docstring).
#
# So it is backgrounded HERE, overlapping its own ~248s with essentially the whole rest of this
# script rather than serializing in front of it (SPECIFICATION.md Part E.1). It counts against
# max_parallel like any other job, not as an extra process on top of that budget.
#
# timeout-wrapped for the standing "hanging tests are never allowed" rule: a hung pytest would hold
# the final `wait` open forever and nothing else here would time it out. 1200s is ~5x its measured
# ~248s, so it fires only on a real hang; CI's timeout-minutes stays the outer backstop, not this.
#
# No retry, unlike the per-file loop - that one absorbs transient contention on a single file's
# budget, whereas a whole-suite pytest timeout is a real failure worth reporting as one.
#
# MUST stay behind the generation step above, which globs devices/*.toml - Part E.1's reserved
# zz_test_ namespace has the race. build_website.sh resolves devices/<device>.toml from the repo
# root, so that one test cannot be handed a tmp_path tree instead.
#
# Nothing else in the foreground re-globs devices/ once generation is done: the test loop reads the
# generated wiring plans, and build_website.sh below names one device explicitly.

echo "== Running tests_scripts/ (CPython-side build-tooling tests)"
tests_scripts_status_file="$(mktemp)"
tests_scripts_timeout_s="${TESTS_SCRIPTS_TIMEOUT_S:-1200}"
# Pre-declared empty and the trap armed HERE, before the background job exists: bash does not kill
# background jobs when the parent exits, and every step between here and the mktemp calls below can
# abort under `set -e`, leaving an orphaned pytest to re-open Part E.1's zz_test_ glob hazard.
#
# `rm -rf ""` is a harmless no-op for either dir before its mktemp has run, and tests_scripts_pid is
# cleared once the job is reaped, so this can never signal a recycled PID.
raw_dir=""
results_dir=""
tests_scripts_pid=""
tests_scripts_inner_pidfile="$(mktemp)"
# shellcheck disable=SC2329  # invoked indirectly, by the `trap _cleanup EXIT` below
_cleanup() {
    # Killing the subshell alone is not enough: its `timeout` child would be reparented and run out
    # its budget with pytest under it. The subshell records that pid, so both are signalled exactly,
    # with no dependency on pkill/procps that a --variant=minbase chroot lacks.
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

# One twin test reaches a real hotspot scenario that binds the real privileged port 53, which a
# non-root environment cannot do without this capability on the interpreter binary. Granted fresh
# every invocation, for the reason run_digital_twin_ci.sh's identical grant gives (xattrs).
echo "== Granting CAP_NET_BIND_SERVICE to $micropython_bin (needed for the real port-53 DNS server test)"
if [ "$(id -u)" -eq 0 ]; then
    setcap 'cap_net_bind_service=+ep' "$micropython_bin"
else
    sudo setcap 'cap_net_bind_service=+ep' "$micropython_bin"
fi

# A gitignored build artifact, rebuilt fresh every run - sub-second, no toolchain (Part A.9). Every
# generated device module does a module-level `import frozen_html`, so this has to exist on
# MICROPYPATH before the loop below, not only for the webserver-specific files.
echo "== Building frozen_modules/frozen_html.py"
scripts/build_frozen_html.sh

# A second, real-content frozen module beside the stub one (Part H.7), equally cheap. Its own
# distinct module name means it never collides with frozen_html's /html mount; only
# tests/test_website_build_integration.py imports it.
echo "== Building frozen_modules/frozen_website_wozi.py"
scripts/build_website.sh wozi frozen_modules/frozen_website_wozi.py

# tests_scripts/ is already running in the background, launched right after the toolchain check -
# nothing to do here. RUN_SLOW_FIRMWARE_BUILD stays unset for it, keeping the one real ARM firmware
# compile opt-in for local iteration; ci.yml's firmware-build-verify job is what sets it.

if [ "$coverage" = "1" ]; then
    raw_dir="$(mktemp -d)"
fi
# One shared results_dir regardless of --coverage: each parallel job writes its own PASS/FAIL here,
# since a background subshell cannot mutate a bash array the parent would see.
#
# Both dirs are cleaned by the single EXIT trap armed with the pytest job above - bash replaces an
# EXIT handler rather than stacking, so every cleanup has to live in that one trap.
results_dir="$(mktemp -d)"

failed=0
# Per-file timeout with two retries, plus stdbuf line buffering and -X heapsize=16M below. All
# three are standing backstops rather than fixes for any specific hang, and the heap value is a
# measured floor that must never be RAISED as a fix - SPECIFICATION.md Part E.3.1 has the history.
per_file_timeout_s="${PER_FILE_TIMEOUT_S:-240}"
# Per-file overrides for anything that outgrows the default - deliberately empty since the
# per-device splits, and deliberately not solved by raising everyone's default, which would make a
# genuine future hang 2-3x slower to detect. Measured figures: Part E.3.1.
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

# Runs one test file's timeout+retry loop and writes PASS/FAIL to status_file. Never returns
# nonzero itself - failure travels through the status file - so backgrounding it and reaping with
# `wait`/`wait -n` can never trip this script's own `set -e`.
run_test_file() {
    local test_file="$1"
    local status_file="$2"
    local tag cmd file_timeout_s attempt ec log_file
    tag="$(basename "$test_file" .py)"
    log_file="$results_dir/$tag.log"
    echo "== Running $test_file"
    # Every segment of MICROPYPATH below is load-bearing. ".frozen" explicitly, because
    # MICROPYPATH REPLACES the default sys.path rather than extending it, and that default is what
    # makes frozen-in modules resolvable - drop it and `import asyncio` breaks with no clue why.
    #
    # "frozen_modules" for the generated module's own `import frozen_html` (Part A.9 for why that
    # cannot be ".frozen" itself), and "build/generated_src" FIRST so a device module resolves to
    # the freshly generated one rather than any same-named file elsewhere on the path.
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
        # 2>&1 | sed, not two streams: these run concurrently, so per-line tagging is what keeps
        # a multi-file log readable. `set -o pipefail` makes the pipeline's status the interpreter's
        # own, so sed can never mask a real 124/1 from the command it pipes.
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

# Dispatch order: the fifteen heaviest files first, not alphabetical glob order. Glob order
# clusters same-prefix heavy files together, so they compete for the same few slots instead of
# overlapping with the ~60 sub-second files that could fill in around them (Part E.3.1's figures).
#
# Order within these fifteen barely matters - they are comparable magnitude; what matters is each
# grabbing a slot immediately. Hand-curated from one measurement run, so re-measure and update it
# if a new heavy file lands or one of these is split further.
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
    # Bound concurrency at max_parallel: reap one finished job before starting another. `|| true`
    # because a job body always returns 0 (run_test_file's own comment), so a nonzero `wait -n` can
    # only mean "no jobs left" - a harmless race, never a test failure to propagate.
    while [ "$(jobs -rp | wc -l)" -ge "$max_parallel" ]; do
        wait -n || true
    done
    status_file="$results_dir/$(basename "$test_file" .py).status"
    run_test_file "$test_file" "$status_file" &
done
wait || true
tests_scripts_pid=""  # reaped by the `wait` above - cleared so the EXIT trap can't signal a recycled PID

# The backgrounded tests_scripts/ job is reaped by the same unqualified `wait` above. Its status
# file is written in both branches, so a missing or empty read here is a bug rather than a
# legitimate "still running" - never treated as PASS by omission.
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

# Both `|| coverage_render_failed=1` rather than bare: under `set -e` a renderer failure would
# abort here with ITS exit code, which the caller cannot tell from a failed test. Coverage is a
# report and never gates, but the test result under this binary must (exit 3 below).
coverage_render_failed=0
if [ "$coverage" = "1" ]; then
    echo "== Rendering coverage report"
    uv run scripts/_render_coverage.py --raw-dir "$raw_dir" --src-dir src --html-dir htmlcov --xml-file coverage.xml --markdown-file coverage_summary.md || coverage_render_failed=1
    echo "== Rendering digital_twin/ coverage report"
    uv run scripts/_render_coverage.py --raw-dir "$raw_dir" --src-dir digital_twin --html-dir htmlcov_digital_twin --xml-file coverage_digital_twin.xml --markdown-file coverage_summary_digital_twin.md || coverage_render_failed=1
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
if [ "$tests_scripts_result" = "FAIL" ]; then
    failed=1
fi
if [ "$failed" -eq 0 ] && [ "$coverage_render_failed" -eq 0 ]; then
    echo "Result: ALL PASSED"
elif [ "$failed" -eq 0 ]; then
    echo "Result: TESTS PASSED, COVERAGE RENDERING FAILED"
else
    echo "Result: FAILED"
fi

# Three outcomes, three codes, because the caller acts differently on each: 1 = a test failed,
# 3 = every test passed and only the report could not be rendered, 0 = both fine. CI gates on 1
# and tolerates 3 (SPECIFICATION.md Part E.5.3); a test failure is never advisory.
if [ "$failed" -eq 0 ] && [ "$coverage_render_failed" -eq 1 ]; then
    exit 3
fi
exit "$failed"
