#!/usr/bin/env bash
# Runs tests/ under the real MicroPython Unix port (one process per test file, per derived device for PER_DEVICE files),
# the lwIP host files, the host-side twin scenario harness per derived device, and the backgrounded tests_scripts/
# pytest tier; ends with the SPECIFICATION.md E.10 summary block.
#
# --coverage runs the same files under build-settrace, the only build flavour compiled with MICROPY_PY_SYS_SETTRACE,
# and renders src/, digital_twin/, the generated modules and the host build chain (E.5, E.5.2).
#
# Rebuilds frozen_modules/frozen_html.py from the first derived device every run (A.9 for why not .frozen/).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# The Unix port's time.mktime() calls the host's real libc, which reads $TZ - unlike the rp2
# firmware's TZ-agnostic override - so src/'s time.mktime(time.gmtime()) idiom is only a no-op round
# trip under UTC. Not a production bug; CLAUDE.md's "Local test runs pin $TZ" has the account.
export TZ=UTC

usage() {
    cat <<'EOF'
Usage: scripts/test.sh [--coverage]
Runs tests/ under the MicroPython Unix port, one process per file, plus the backgrounded
tests_scripts/ pytest tier, and ends with the summary block (SPECIFICATION.md E.10).

Options:
  --coverage    run under build-settrace and render the coverage reports
  -h, --help    print this help and exit

Environment:
  PICO_TOOLCHAIN_DIR        toolchain cache (default: ~/pico-toolchain)
  SKIP_APT=1                skip the system-package step of a toolchain build (default: 0)
  PER_FILE_TIMEOUT_S        per-file timeout, a positive integer of seconds (default: 240)
  TESTS_SCRIPTS_TIMEOUT_S   tests_scripts/ timeout, a positive integer of seconds (default: 1200)
  TEST_PARALLELISM          test files run at once (default: detected from core count and speed)
  GC_THRESHOLD              gc.threshold() for every test file, e.g. 32768 (default: unset, the reactive -1)

Exit codes: 0 every test passed; 1 a test failed or an allocation failure was seen; 2 a usage or
setting error; 3 (--coverage only) every test passed and only a coverage report failed to render.
EOF
}

# Ahead of every sweep below, not after them: these checks are pure argument validation, and
# a rejected invocation must leave the live tree exactly as it found it. tests_scripts/ runs a nested
# test.sh to prove the rejection, concurrently with every test file holding tests/_tmp scratch.
coverage=0
for arg in "$@"; do
    case "$arg" in
        --coverage) coverage=1 ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown argument $arg (scripts/test.sh --help)" >&2
            exit 2
            ;;
    esac
done

# GC_THRESHOLD=32768 re-runs the MicroPython tier through tests/_threshold_runner.py with that
# gc.threshold() set, which is CLAUDE.md's (f) stage. Unset (the default) is the (e) stage: the
# interpreter's own reactive -1, where the design has to stand up on its own first.
if [ -n "${GC_THRESHOLD:-}" ]; then
    # Validated once here rather than once per test file inside the runner: an unparseable value would
    # otherwise surface as one ValueError traceback per test file, each retried twice, with the
    # actual mistake nowhere in the rolled-up summary.
    if [[ ! "$GC_THRESHOLD" =~ ^-?[0-9]+$ ]]; then
        echo "error: GC_THRESHOLD must be an integer - 32768 is what the firmware ships, -1 the reactive default - not '$GC_THRESHOLD'" >&2
        exit 2
    fi
    # Range as well as shape, on the FIRMWARE's 32-bit word rather than this 64-bit host's: a value
    # above it can match no shippable setting, and one past the host's own word raises OverflowError
    # inside the runner instead, once per file. Length first, so bash's own arithmetic can't overflow.
    if [ "${#GC_THRESHOLD}" -gt 11 ] || [ "$GC_THRESHOLD" -gt 2147483647 ] || [ "$GC_THRESHOLD" -lt -2147483648 ]; then
        echo "error: GC_THRESHOLD=$GC_THRESHOLD is outside the rp2040's own 32-bit machine word - any negative value means the reactive default (-1 by convention, see py/modgc.c) and the firmware ships 32768" >&2
        exit 2
    fi
    if [ "$coverage" = "1" ]; then
        # Said out loud rather than silently dropped: --coverage has its own runner, and a run that
        # ignores an explicitly set threshold must not look like one that honored it.
        echo "== note: --coverage uses its own runner, so GC_THRESHOLD=$GC_THRESHOLD is ignored for this run" >&2
    fi
fi

# Both timeouts are checked here, before any sweep: 0 would disable `timeout` altogether (coreutils),
# turning the standing hang backstop off without a word.
# @tunable runner.per_file_timeout_s = 240
per_file_timeout_s="${PER_FILE_TIMEOUT_S:-240}"
# @tunable runner.tests_scripts_timeout_s = 1200
tests_scripts_timeout_s="${TESTS_SCRIPTS_TIMEOUT_S:-1200}"
# A timeout is retried twice, every per-file job, scenario job and the pytest tier alike, and nothing else (E.3.1).
# @tunable runner.per_file_attempts = 3
max_attempts=3
_require_seconds() {
    if [[ ! "$2" =~ ^[1-9][0-9]{0,5}$ ]]; then
        echo "error: $1 must be a positive integer number of seconds, not '$2'" >&2
        exit 2
    fi
}
_require_seconds PER_FILE_TIMEOUT_S "$per_file_timeout_s"
_require_seconds TESTS_SCRIPTS_TIMEOUT_S "$tests_scripts_timeout_s"
# Empty means autodetect; 0, negative or a non-integer would leave the dispatch loop dispatching nothing.
if [ -n "${TEST_PARALLELISM:-}" ] && [[ ! "$TEST_PARALLELISM" =~ ^[1-9][0-9]*$ ]]; then
    echo "error: TEST_PARALLELISM must be a positive integer, not '$TEST_PARALLELISM'" >&2
    exit 2
fi

# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_port_lock.sh
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_devices.sh
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_unix_port.sh

# The one EXIT trap, armed before anything it removes exists: bash does not kill background jobs when the parent
# exits, and any later step can abort under `set -e`, leaving an orphaned pytest to re-open Part E.1's zz_test_ glob
# hazard. Every name it reads is declared here, empty until its step runs (`rm -rf ""` is a no-op).
raw_dir=""
results_dir=""
tests_scripts_status_file=""
tests_scripts_inner_pidfile=""
tests_scripts_pid=""
evidence_archived=0
# shellcheck disable=SC2329  # invoked indirectly, by the `trap _cleanup EXIT` below
_cleanup() {
    # Every background job still running (`jobs -rp`, so never a reaped, recycled pid) and the timeout each runs, by
    # its recorded pid and group (timeout leads one): a killed subshell's timeout child would be reparented and run
    # out its budget. No pkill/procps either, which a --variant=minbase chroot lacks.
    local pid running groups="" left signalled=" " sig=TERM pids=()
    # @tunable runner.kill_after_s = 10
    local kill_after_s=10
    local deadline=$((SECONDS + 2 * kill_after_s))
    running=" $(jobs -rp | tr '\n' ' ')"
    if [ -n "$tests_scripts_pid" ] && [[ "$running" == *" $tests_scripts_pid "* ]]; then
        groups="$(cat "$tests_scripts_inner_pidfile" 2>/dev/null || true)"
    fi
    # Waited for until none is left (a zombie awaiting its reaper counts as gone), so port 53 below is never released
    # under a test still holding it; timeout's own --kill-after is the hard stop, this loop's SIGKILL the backstop.
    while :; do
        left=""
        # One pid per line from each source, read into an array; a line that is not a pid (an empty one) is passed over.
        mapfile -t pids <<<"$(jobs -rp; printf '%s\n' "$groups"; [ -z "$results_dir" ] || cat "$results_dir"/*.attempt_pid 2>/dev/null || true)"
        for pid in "${pids[@]}"; do
            if [[ ! "$pid" =~ ^[1-9][0-9]*$ ]] || [ ! -r "/proc/$pid/stat" ] || [[ "$(cat "/proc/$pid/stat" 2>/dev/null || true)" == *") Z "* ]]; then
                continue
            fi
            left+=" $pid"
            if [[ "$signalled" != *" $pid "* ]] || [ "$sig" = KILL ]; then
                kill -s "$sig" -- "$pid" "-$pid" 2>/dev/null || true
                signalled+="$pid "
            fi
        done
        if [ -z "$left" ]; then
            break
        fi
        if [ "$SECONDS" -ge "$deadline" ] && [ "$sig" = TERM ]; then
            echo "== background jobs still running $((2 * kill_after_s))s after the stop:$left - killing them" >&2
            sig=KILL
        fi
        sleep 0.1
    done
    wait 2>/dev/null || true
    # A run that ended before its own archive step (an abort under `set -e`) moves every log it has
    # into build/archive/test_sh/ first; if even that fails, the results dir is kept and named.
    if [ -n "$results_dir" ] && [ -d "$results_dir" ] && [ "${evidence_archived:-0}" = "0" ]; then
        if uv run scripts/_archive_evidence.py --runner test_sh "$results_dir" >&2; then
            evidence_archived=1
        else
            echo "== the per-file logs could not be archived - kept in $results_dir" >&2
            results_dir=""
        fi
    fi
    rm -rf "$raw_dir" "$results_dir" "$tests_scripts_status_file" "$tests_scripts_inner_pidfile"
    port_lock_release_all
}
trap _cleanup EXIT

# Port 53 is the product's, bound by the twin tests: one suite holds it at a time and a second exits 1
# here, before anything is swept or built (CLAUDE.md); the EXIT trap above releases it.
port_lock_take 53 scripts/test.sh

# The previous coverage reports are evidence too: moved into build/archive/test_sh_coverage/ (the
# newest three runs kept), never overwritten in place.
if [ "$coverage" = "1" ]; then
    uv run scripts/_archive_evidence.py --runner test_sh_coverage htmlcov htmlcov_digital_twin htmlcov_generated htmlcov_host coverage_summary.md coverage_summary_digital_twin.md coverage_summary_generated.md coverage_summary_host.md
fi

# One bounded sweep of the whole tests/_tmp tree before any test file runs, not a per-file one -
# SPECIFICATION.md Part E.1 has why it exists at all and why it is `rm -rf` rather than a
# MicroPython listdir loop.
rm -rf tests/_tmp

# Same reasoning for the test fixtures that live in the real tree (a nested run's sentinel, the device-websites skip
# case). What the reserved devices/zz_test_*.toml namespace is and why this sweep precedes the generation step:
# SPECIFICATION.md Part E.1.
rm -f devices/zz_test_*.toml

# Every binary comes from the one Unix-port probe (scripts/_unix_port.sh), by the build flavour it reports: a missing or
# wrong one, or a stale toolchain record, runs one setup (its exclusive lock fails a concurrent build fast), then this
# run holds the lock shared. tests_scripts/' twins boot build-standard, the settrace-free rig, in both modes (E.5.2).
if [ "$coverage" = "1" ]; then
    unix_port_ensure standard settrace  # --coverage needs sys.settrace itself
    micropython_bin="$(unix_port_bin settrace)"
    lwip_bin=""
else
    # The lwIP host files run on the third build, the standard flavour over loopback lwIP (SPECIFICATION.md B.14).
    unix_port_ensure standard lwip
    micropython_bin="$(unix_port_bin standard)"
    lwip_bin="$(unix_port_bin lwip)"
fi
unit_micropypath="$(micropypath unit)"

# TEST_PARALLELISM: how many test_*.py files run at once. Each file is its own Unix-port process
# with its own heap and its own fake-hardware state, so concurrency changes wall clock only - as
# long as the two per-file resources SPECIFICATION.md Part E.1 names stay disjoint.
#
# One hazard is NOT closed: a twin test asserting a real background transition inside a fixed budget
# measures host speed, so CPU starvation fails it while the code is healthy. Reproduced with twelve
# busy-loops and no parallel test processes at all; the probe below is what keeps a slow host clear.
#
# So the multiplier is autodetected from core SPEED, not core count: the same 4 cores are
# comfortable at 16 processes on a fast x86 host and starve a slow one (bands: README.md's
# TEST_PARALLELISM entry). TEST_PARALLELISM overrides everything, the escape hatch if it misjudges.
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
    local cores quota period up_start="" up_end="" probe_iterations probe_ms=0 multiplier failed=0
    # @tunable runner.nproc_fallback = 4
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
    # Speed probe, timed on /proc/uptime (CLOCK_BOOTTIME: monotonic, 10ms steps), so a wall-clock step
    # cannot move it and the bands keep measuring interpreter start to exit. Integer arithmetic on the
    # two-decimal fields; 10# keeps a leading zero from reading as octal.
    { read -r up_start _ </proc/uptime; } 2>/dev/null || failed=1
    # @tunable runner.probe_iterations = 500000
    probe_iterations=500000
    "$micropython_bin" -c "x=0
for i in range($probe_iterations):
    x+=i" >/dev/null 2>&1 || failed=1
    { read -r up_end _ </proc/uptime; } 2>/dev/null || failed=1
    if [ "$failed" -eq 0 ] && [[ "$up_start" =~ ^[0-9]+\.[0-9]{2}$ && "$up_end" =~ ^[0-9]+\.[0-9]{2}$ ]]; then
        probe_ms=$(( (10#${up_end/./} - 10#${up_start/./}) * 10 ))
    fi
    # A failed probe (no clock, an interpreter that did not run, no time elapsed) says nothing about
    # the host, so it takes 1x, the setting known never to starve a slow one, and says so.
    if [ "$probe_ms" -le 0 ]; then
        echo "== speed probe failed - running at 1x" >&2
        multiplier=1
    # @tunable runner.band_fast_ms = 250
    elif [ "$probe_ms" -le 250 ]; then
        # @tunable runner.mult_fast = 4
        multiplier=4            # fast host (measured: 131-141ms on this project's own x86 sandbox)
    # @tunable runner.band_mid_ms = 900
    elif [ "$probe_ms" -le 900 ]; then
        # @tunable runner.mult_mid = 2
        multiplier=2            # mid host - the bench Pi4's class; halves the oversubscription
    else                        # that starved a twin test's real-time budget at 4x
        multiplier=1
    fi
    echo "$(( cores * multiplier )) $cores $multiplier $probe_ms"
}
# A --coverage run is CPU-bound, not sleep-bound: settrace turns a 0.4 s file into 72 s of CPU, so the
# oversubscription above queued CI's files for a core past the per-file timeout. One file per usable core.
_coverage_parallelism() {
    local jobs="$1" cores="$2" multiplier="$3"
    if [ "$multiplier" -gt 1 ]; then
        jobs="$cores"
        multiplier=1
    fi
    echo "$jobs $multiplier"
}
if [ -n "${TEST_PARALLELISM:-}" ]; then
    max_parallel="$TEST_PARALLELISM"
    echo "== Test parallelism: $max_parallel (TEST_PARALLELISM override)"
else
    read -r max_parallel _cores _multiplier _probe_ms < <(_detect_parallelism)
    if [ "$coverage" = "1" ]; then
        read -r max_parallel _multiplier < <(_coverage_parallelism "$max_parallel" "$_cores" "$_multiplier")
    fi
    echo "== Test parallelism: $max_parallel ($_cores usable cores x $_multiplier, interpreter speed probe ${_probe_ms}ms)"
fi
# Clamped to >= 1 as a backstop behind the validation above: the dispatch loop blocks while running
# jobs >= max_parallel, so 0 or negative would spin `wait -n` forever without dispatching anything.
if ! [ "$max_parallel" -ge 1 ] 2>/dev/null; then
    echo "== TEST_PARALLELISM=${TEST_PARALLELISM:-} is not a positive integer - falling back to 1 (sequential)" >&2
    max_parallel=1
fi

# The derived devices (scripts/_devices.sh), read once, before the tests_scripts/ tier can plant its zz_test_ fixtures:
# the PER_DEVICE jobs, the scenario harness jobs and the site build all take this one list.
devices_text="$(derived_devices)"
mapfile -t devices <<<"$devices_text"
site_device="${devices[0]}"

# Generated fresh into build/generated_src/ (SPECIFICATION.md L.2), which the unit MICROPYPATH puts first.
# It runs before tests_scripts/ is backgrounded: that tier creates and deletes zz_test_ device fixtures, and the
# generator globs devices/*.toml, so generating first keeps every fixture out of the generated tree.
echo "== Generating buildgen device modules into build/generated_src/"
uv run scripts/_generate_sensortask_modules.py

# Every twin boot binds privileged ports (its NTP responder's 123, a hotspot's DNS 53), the tests_scripts/ tier's twins
# too, so the grant comes before that tier, for the build it boots (build-standard) and this run's own interpreter; fresh
# every invocation, for the reason run_digital_twin_ci.sh's identical grant gives (xattrs).
cap_bins=("$(unix_port_bin standard)")
[ "$micropython_bin" = "${cap_bins[0]}" ] || cap_bins+=("$micropython_bin")
for cap_bin in "${cap_bins[@]}"; do
    echo "== Granting CAP_NET_BIND_SERVICE to $cap_bin (the twins' NTP responder and DNS server bind ports 123 and 53)"
    if [ "$(id -u)" -eq 0 ]; then
        setcap 'cap_net_bind_service=+ep' "$cap_bin"
    else
        sudo setcap 'cap_net_bind_service=+ep' "$cap_bin"
    fi
done

# tests_scripts/ needs nothing from the frozen-module steps below: it is real CPython touching only
# pytest's tmp_path fixtures and OS-assigned free ports, never this repo's real build/generated_src/
# or frozen_modules/ (tests_scripts/conftest.py's docstring).
#
# So it is backgrounded HERE, overlapping its own run with essentially the whole rest of this
# script rather than serializing in front of it (SPECIFICATION.md Part E.1). It counts against
# max_parallel like any other job, not as an extra process on top of that budget.
#
# timeout-wrapped for the standing "hanging tests are never allowed" rule: a hung pytest would hold the final `wait`
# open forever. Its 1200 s is a hang backstop over the tier's measured 698 s (2026-10-15, either GC stage, beside the
# MicroPython tier; CI's figure: Part N, runner.tests_scripts_timeout_s); CI's timeout-minutes stays the outer one.
#
# The timeout retry rule (E.3.1): a timed-out run is retried like a timed-out file, up to max_attempts in all, and a
# pass after a retry is RETRIED-PASS; any other exit fails at once.
#
# MUST stay behind the generation step above, which globs devices/*.toml - Part E.1's reserved
# zz_test_ namespace has the race: the tier writes its live-tree fixtures there for the length of one test.
#
# Nothing else in the foreground re-globs devices/ once generation is done but build_device_websites.sh below, which
# drops the zz_test_ fixtures, the only TOMLs the tier writes; every other step takes the device list read above.

echo "== Running tests_scripts/ (CPython-side build-tooling tests)"
# Created before the pytest job, which writes its run record, status and pid into it. One shared results_dir
# regardless of --coverage: each parallel job writes its own status here, since a background subshell
# cannot mutate a bash array the parent would see.
results_dir="$(mktemp -d)"
tests_scripts_status_file="$results_dir/tests_scripts.status"
tests_scripts_inner_pidfile="$results_dir/tests_scripts.pid"
(
    # _run_with_retries' attempts without its memory gate: this tier is CPython, and a failing check whose own text names
    # a marker, as test_summary_block.py's do, prints it in its traceback. Each attempt's timeout pid is the one the EXIT
    # trap kills; the record is removed first, so the summary reads the last attempt's.
    for ((attempt = 1; attempt <= max_attempts; attempt++)); do
        rm -f "$results_dir/tests_scripts.json"
        attempt_start=$SECONDS
        # --coverage runs this same tier under coverage.py over the host build chain, report-only: its data
        # stays in results_dir for the render step at the end, and the test result is the tier's own.
        if [ "$coverage" = "1" ]; then
            # @tunable runner.kill_after_s = 10
            PYTHONPATH=scripts timeout --kill-after=10 "$tests_scripts_timeout_s" uv run coverage run --data-file="$results_dir/host.coverage" "--source=buildgen,scripts,toolchain" -m pytest tests_scripts -q -p _pytest_run_record --run-record="$results_dir/tests_scripts.json" &
        else
            # @tunable runner.kill_after_s = 10
            PYTHONPATH=scripts timeout --kill-after=10 "$tests_scripts_timeout_s" uv run pytest tests_scripts -q -p _pytest_run_record --run-record="$results_dir/tests_scripts.json" &
        fi
        inner_pid=$!
        echo "$inner_pid" >"$tests_scripts_inner_pidfile"
        ec=0
        wait "$inner_pid" || ec=$?
        rm -f "$tests_scripts_inner_pidfile"
        if [ "$ec" -eq 0 ]; then
            if [ "$attempt" -eq 1 ]; then
                echo "PASS" >"$tests_scripts_status_file"
            else
                echo "RETRIED-PASS $attempt/$max_attempts" >"$tests_scripts_status_file"
            fi
            exit 0
        fi
        # 124, or --kill-after's SIGKILL (137) past the bound, is a timeout, exactly as _run_with_retries reads it.
        if [ "$ec" -ne 124 ] && { [ "$ec" -ne 137 ] || [ $((SECONDS - attempt_start)) -lt "$tests_scripts_timeout_s" ]; }; then
            break
        fi
        if [ "$attempt" -lt "$max_attempts" ]; then
            echo "== tests_scripts/ exceeded ${tests_scripts_timeout_s}s on attempt $attempt/$max_attempts - retrying in case of transient runner contention" >&2
        else
            echo "== tests_scripts/ exceeded ${tests_scripts_timeout_s}s on all $max_attempts attempts - treating as a real failure instead of hanging the job" >&2
        fi
    done
    echo "FAIL" >"$tests_scripts_status_file"
) &
tests_scripts_pid=$!

# _build_sites: every generated sensortask_<device>.py imports frozen_html at module level, so the unit tier needs one
# site on its path; any derived device serves, so the first is built and no device is named here (Part A.9). The
# scenario harness boots each device on its own site, build/generated_html/<device>/, so a plain run builds those too.
_build_sites() {
    echo "== Building frozen_modules/frozen_html.py (the $site_device website, the first derived device)"
    scripts/build_website.sh "$site_device"
    if [ "$coverage" = "0" ]; then
        echo "== Building every derived device's website into build/generated_html/ (the scenario harness boots each)"
        scripts/build_device_websites.sh
    fi
}
_build_sites

# tests_scripts/ was backgrounded after the generation step above; RUN_SLOW_FIRMWARE_BUILD stays unset for it,
# keeping the one real ARM firmware compile opt-in for local iteration; ci.yml's firmware-build-verify job sets it.

if [ "$coverage" = "1" ]; then
    raw_dir="$(mktemp -d)"
fi
# Both dirs are cleaned by the one EXIT trap armed before the port lock - bash replaces an EXIT handler
# rather than stacking, so every cleanup has to live in that one trap.

# Per-file timeout with two retries, plus stdbuf line buffering and -X heapsize=16M below. All
# three are standing backstops rather than fixes for any specific hang, and the heap value is a
# measured floor, never raised as a fix (SPECIFICATION.md E.3.1). The timeout is validated above.
#
# Per-file overrides for anything that outgrows the default - no test file has one since the per-device splits, and
# none is solved by raising everyone's default, which would make a genuine future hang 2-3x slower to detect. The
# scenario harness has its own: one job boots a twin per scenario (measured figures: Part E.3.1 and Part N).
declare -A per_file_timeout_overrides_s=()
# @tunable runner.scenarios_timeout_s = 2555
per_file_timeout_overrides_s[scenarios]=2555

# SPECIFICATION.md Part I.4(e): zero MemoryErrors, caught-and-logged included - a caught
# allocation failure is a design defect, not a passing result. The twin tier already asserts this
# on its own logs (_digital_twin_ci_suite.py); this is the same check for the tier (e)/(f) run in.
_flag_memory_errors() {
    local tag="$1" log_file="$2" rc=0
    # Both spellings, because src/'s degrade handlers log str(e) and not the class: a real caught
    # allocation failure prints "memory allocation failed, ..." (py/runtime.c:1692/1696) with no
    # "MemoryError" in it, so the class name alone only ever sees an UNCAUGHT traceback.
    local pattern="MemoryError|memory allocation failed"
    # Fails closed: a log it cannot read, or a grep error (exit 2+), is no verdict - never "clean".
    if [ ! -r "$log_file" ]; then
        echo "memory gate: per-file log $log_file missing or unreadable - no verdict" >"$results_dir/$tag.noverdict"
        return 0
    fi
    grep -qE "$pattern" "$log_file" || rc=$?
    if [ "$rc" -eq 0 ]; then
        grep -m5 -E "$pattern" "$log_file" >"$results_dir/$tag.memerr" || echo "memory gate: a marker matched in $log_file but its lines could not be copied" >"$results_dir/$tag.memerr"
    elif [ "$rc" -ge 2 ]; then
        echo "memory gate: grep exited $rc reading $log_file - no verdict" >"$results_dir/$tag.noverdict"
    fi
}

# _job_tag <job>: a job's tag, its file's basename then "[<device>]" for one device's job of a PER_DEVICE file;
# each job's status, log and markers in $results_dir are named by it.
_job_tag() {
    local test_file="${1%%\[*}"
    printf '%s%s' "$(basename "$test_file" .py)" "${1:${#test_file}}"
}

# _run_with_retries <tag> <what> <status_file> <timeout_s> <after> <command...>: one job's timeout+retry loop, writing
# PASS, RETRIED-PASS <k>/<n> or FAIL to status_file; <after> runs after every attempt with the tag, the log and the
# attempt number. Never returns nonzero itself, so backgrounding a job and reaping it with `wait -n` cannot trip `set -e`.
_run_with_retries() {
    local tag="$1" what="$2" status_file="$3" timeout_s="$4" after="$5" attempt attempt_start ec log_file attempt_pidfile
    shift 5
    log_file="$results_dir/$tag.log"
    # The EXIT trap's stop: it signals the running attempt's timeout through this pid file; the job then ends rather
    # than start another attempt (the trap runs once the attempt's pipeline is done, sed and tee included).
    attempt_pidfile="$results_dir/$tag.attempt_pid"
    trap 'rm -f "$attempt_pidfile"; exit 143' TERM
    # Truncated once per job: the memory gate reads every attempt's output, a timed-out one included (CLAUDE.md memory rule).
    : >"$log_file"
    for ((attempt = 1; attempt <= max_attempts; attempt++)); do
        # Each attempt opens with this line, so the summary reads its counts and skips from the deciding one.
        echo "[$tag] == attempt $attempt/$max_attempts" >>"$log_file"
        attempt_start=$SECONDS
        # 2>&1 | sed, not two streams: these run concurrently, so per-line tagging is what keeps
        # a multi-file log readable. `set -o pipefail` makes the pipeline's status the command's
        # own, so sed can never mask a real 124/1 from the command it pipes.
        #
        # SIGINT first (delivered at a safe point, SPECIFICATION.md B.14.1; microtest's ABORT line names the hung test), and
        # --kill-after the hard stop. timeout signals its child, then its group, and a second SIGINT still pending makes the
        # port exit(1) at once (unix_mphal.c): its child is a shell catching it, so the command gets one. The pid is timeout's.
        # @tunable runner.kill_after_s = 10
        if (echo "$BASHPID" >"$attempt_pidfile" && exec stdbuf -oL -eL timeout -s INT --kill-after=10 "$timeout_s" bash -c 'trap : INT; "$@"; exit' bash "$@") 2>&1 | sed -u "s/^/[$tag] /" | tee -a "$log_file"; then
            ec=0
        else
            ec=$?
        fi
        rm -f "$attempt_pidfile"
        "$after" "$tag" "$log_file" "$attempt"
        if [ "$ec" -eq 0 ]; then
            _flag_memory_errors "$tag" "$log_file"
            # A pass that needed a retry is reported apart, a root-cause item (E.3.1), never a plain PASS.
            if [ "$attempt" -eq 1 ]; then
                echo "PASS" >"$status_file"
            else
                echo "RETRIED-PASS $attempt/$max_attempts" >"$status_file"
            fi
            return 0
        elif [ "$ec" -eq 124 ] || { [ "$ec" -eq 137 ] && [ $((SECONDS - attempt_start)) -ge "$timeout_s" ]; }; then
            if [ "$ec" -eq 137 ]; then
                # Caught the interrupt and ran on: the hard stop's SIGKILL exits 137, not timeout's 124 - a timeout all the same.
                echo "== $what did not end on the timeout's interrupt - killed by --kill-after on attempt $attempt/$max_attempts" >&2
            fi
            if [ "$attempt" -lt "$max_attempts" ]; then
                echo "== $what exceeded ${timeout_s}s on attempt $attempt/$max_attempts - retrying in case of transient runner contention" >&2
                continue
            fi
            echo "== $what exceeded ${timeout_s}s on all $max_attempts attempts - treating as a real failure instead of hanging the job" >&2
        fi
        _flag_memory_errors "$tag" "$log_file"
        echo "FAIL" >"$status_file"
        return 0
    done
}

# _append_twin_logs <tag> <log_file> <attempt>: every twin log of this attempt joins the job's log, so the memory gate
# reads the twins' output too; the attempt's directory is kept, numbered (the harness empties a scenario's on a rerun).
# shellcheck disable=SC2329  # invoked by name, as _run_with_retries' after-attempt hook
_append_twin_logs() {
    local tag="$1" log_file="$2" attempt="$3" twin_log
    [ -d "$scenario_logs_dir" ] || return 0
    while IFS= read -r -d '' twin_log; do
        echo "[$tag] == twin log ${twin_log#"$scenario_logs_dir"/} (attempt $attempt)" >>"$log_file"
        sed "s/^/[$tag] /" "$twin_log" >>"$log_file" || echo "[$tag] == twin log $twin_log could not be read" >>"$log_file"
    done < <(find "$scenario_logs_dir" -type f -name '*.log' -print0 | LC_ALL=C sort -z)
    mv "$scenario_logs_dir" "$scenario_logs_dir.attempt$attempt" || echo "[$tag] == the attempt's logs stay in $scenario_logs_dir" >>"$log_file"
}

# shellcheck disable=SC2329  # invoked by name, as _run_with_retries' after-attempt hook
_no_twin_logs() {
    return 0
}

# run_test_file <test_file> <status_file> [<device>] [<binary>] (default $micropython_bin): one test file's job on the
# unit MICROPYPATH (scripts/micropypath.toml); a device runs the file with TEST_DEVICE set to it.
run_test_file() {
    local test_file="$1" status_file="$2" device="${3:-}" binary="${4:-$micropython_bin}" runner cmd
    echo "== Running $test_file"
    # Every segment of the unit layout is load-bearing. ".frozen" explicitly, because MICROPYPATH
    # REPLACES the default sys.path rather than extending it, and that default is what makes
    # frozen-in modules resolvable - drop it and `import asyncio` breaks with no clue why.
    #
    # "frozen_modules" for the generated module's own `import frozen_html` (Part A.9 for why that
    # cannot be ".frozen" itself), and "build/generated_src" FIRST so a device module resolves to
    # the freshly generated one rather than any same-named file elsewhere on the path.
    if [ "$coverage" = "1" ]; then
        runner=(tests/_coverage_runner.py "$test_file" "$raw_dir/$(_job_tag "$test_file${device:+[$device]}").json")
    elif [ -n "${GC_THRESHOLD:-}" ]; then
        # CLAUDE.md's (f) stage: the same suite again with the value the firmware ships, layered on
        # a design that already passes at the reactive default. Never a substitute for that run.
        runner=(tests/_threshold_runner.py "$test_file" "$GC_THRESHOLD")
    else
        runner=("$test_file")
    fi
    # @tunable l1.unix_heapsize = 16M
    cmd=(env -u TEST_DEVICE "MICROPYPATH=$unit_micropypath" ${device:+"TEST_DEVICE=$device"} "$binary" -X heapsize=16M "${runner[@]}")
    _run_with_retries "$(_job_tag "$test_file${device:+[$device]}")" "$test_file" "$status_file" "${per_file_timeout_overrides_s[$test_file]:-$per_file_timeout_s}" _no_twin_logs "${cmd[@]}"
}

# run_scenarios_job <device> <status_file>: the host-side twin scenario harness for one device at this run's GC stage,
# on shared port 53 (the DNS scenarios deselected and listed: several devices' jobs run at once), its outcomes in a
# run record the summary reads. Its twins boot build-standard; port 53's lock passes to it through the owner chain.
run_scenarios_job() {
    local device="$1" status_file="$2"
    scenario_logs_dir="$results_dir/scenarios_$device"
    echo "== Running the scenario harness for $device"
    _run_with_retries "scenarios[$device]" "the scenario harness for $device" "$status_file" "${per_file_timeout_overrides_s[scenarios]}" _append_twin_logs \
        uv run scripts/_digital_twin_scenarios.py --device "$device" --micropython-bin "$micropython_bin" --logs-dir "$scenario_logs_dir" --gc-threshold "${GC_THRESHOLD:--1}" --shared-port-53 --run-record "$results_dir/scenarios_$device.json"
}

# Dispatch order: the heaviest files first, not alphabetical glob order. Glob order
# clusters same-prefix heavy files together, so they compete for the same few slots instead of
# overlapping with the ~60 sub-second files that could fill in around them (Part E.3.1's figures).
#
# Order within them barely matters - they are comparable magnitude; what matters is each
# grabbing a slot immediately. Hand-curated from one measurement run, so re-measure and update it
# if a new heavy file lands or one of these is split further.
_heavy_files_priority=(
    tests/test_digital_twin_bus_hazard_concurrency.py
    tests/test_sensortask.py
    tests/test_uart_comm_hazard.py
    tests/test_digital_twin_wifi_modes.py
    tests/test_digital_twin_uart_link.py
    tests/test_bus_hazard_generated.py
    tests/test_asy_uart_comm.py
    tests/test_digital_twin_sensortask_integration.py
    tests/test_digital_twin_isl29125_autorange.py
    tests/test_digital_twin_construction.py
)
# A name that no longer exists stops the run: a silently skipped entry would leave the order stale unnoticed.
_check_heavy_list() {
    local test_file
    for test_file in "${_heavy_files_priority[@]}"; do
        if [[ "$test_file" != tests/test_*.py ]] || [ ! -f "$test_file" ]; then
            echo "scripts/test.sh: heavy-file list names $test_file, which does not exist - update _heavy_files_priority" >&2
            exit 2
        fi
    done
}
_check_heavy_list
all_test_files=(tests/test_*.py)
declare -A _dispatched=()
test_files=()
for test_file in "${_heavy_files_priority[@]}"; do
    if [ -z "${_dispatched[$test_file]:-}" ]; then
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
# The lwIP host files go last, each on $lwip_bin; --coverage runs none of them (they exercise C code,
# which line coverage cannot see) and lists them as skipped instead.
lwip_host_files=()
for test_file in tests/lwip_host/test_*.py; do
    if [ -f "$test_file" ]; then
        lwip_host_files+=("$test_file")
    fi
done
if [ "$coverage" = "0" ]; then
    test_files+=("${lwip_host_files[@]}")
fi
# One scenario harness job per derived device, dispatched first (each is the longest job of the run); --coverage runs
# none and lists them as skipped. A file whose own line reads `PER_DEVICE = True` runs once per derived device.
job_list=()
if [ "$coverage" = "0" ]; then
    for device in "${devices[@]}"; do
        job_list+=("scenarios[$device]")
    done
fi
for test_file in "${test_files[@]}"; do
    marker=0
    grep -qx 'PER_DEVICE = True' "$test_file" || marker=$?
    if [ "$marker" -ge 2 ]; then  # fails closed, as the memory gate does: an unread file is no verdict on its marker
        echo "error: cannot read $test_file for its PER_DEVICE marker" >&2
        exit 1
    elif [ "$marker" -eq 0 ]; then
        for device in "${devices[@]}"; do
            job_list+=("${test_file}[$device]")
        done
    else
        job_list+=("$test_file")
    fi
done

for job in "${job_list[@]}"; do
    # Bound concurrency at max_parallel: reap one finished job before starting another. `|| true`
    # because a job body always returns 0 (run_test_file's own comment), so a nonzero `wait -n` can
    # only mean "no jobs left" - a harmless race, never a test failure to propagate.
    while [ "$(jobs -rp | wc -l)" -ge "$max_parallel" ]; do
        wait -n || true
    done
    test_file="${job%%\[*}"
    device="${job:${#test_file}}"
    device="${device#\[}"
    status_file="$results_dir/$(_job_tag "$job").status"
    if [ "$test_file" = "scenarios" ]; then
        run_scenarios_job "${device%]}" "$status_file" &
        continue
    fi
    binary="$micropython_bin"
    if [[ "$test_file" == tests/lwip_host/* ]]; then
        binary="$lwip_bin"
    fi
    run_test_file "$test_file" "$status_file" "${device%]}" "$binary" &
done
wait || true
tests_scripts_pid=""  # reaped by the `wait` above - cleared so the EXIT trap can't signal a recycled PID

# ---------------------------------------------------------------------------------------------
# The verdict: every job's status, log and run record read into the SPECIFICATION.md E.10 summary
# block, the last thing printed. Each job's own output above stays the place to read a failure.
# ---------------------------------------------------------------------------------------------
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_summary_block.sh
summary_unit files

# _failing_tests <tag> <failed>, the deciding attempt on stdin: " (FAIL <test>: <its first failure line>; ...)" in
# microtest's own FAIL or ABORT line form, at most five, then "+N more" for the closing line's failures left unnamed.
# Prints nothing when no such line is found, so the count alone stands as before.
_failing_tests() {
    awk -v p="[$1] " -v failed="$2" -v cap=5 '
        function keep(detail) { if (pending != "") { n++; if (n <= cap) out = out (n > 1 ? "; " : "") pending (detail != "" ? " " detail : ""); pending = "" } }
        index($0, p) != 1 { next }
        { line = substr($0, length(p) + 1); sub(/[ \t\r]+$/, "", line) }
        line ~ /^(FAIL|ABORT) [A-Za-z_][A-Za-z0-9_]*:$/ { keep(""); pending = line; next }
        pending == "" { next }
        line ~ /^(PASS|SKIP) / || line ~ /^[0-9]+\/[0-9]+ passed, / { keep(""); next }
        line == "Traceback (most recent call last):" || line ~ /^  File / { next }
        { keep(line) }
        END {
            keep("")
            shown = n < cap ? n : cap
            if (shown > 0 && failed - shown > 0) out = out "; +" (failed - shown) " more"
            if (shown > 0) printf " (%s)", out
        }'
}

# _scenario_outcomes <record>: the scenario harness's run record, one "<outcome>\t<name>\t<reason>" line per scenario;
# fails on a missing or unreadable record, which its caller turns into no verdict.
_scenario_outcomes() {
    uv run python -c 'import json, sys
for o in json.load(open(sys.argv[1], encoding="utf-8")):
    print(o["outcome"], o["name"], " ".join(str(o["reason"]).split()), sep="\t")' "$1"
}

# _scenario_counts <tag>, the outcomes on stdin: "<passed> <failed> <skipped> <deselected> <what failed>", the last the
# file reason's form: "N of M scenarios failed", then the first five failing ones with their reasons.
_scenario_counts() {
    local outcome name reason passed=0 failed=0 skipped=0 deselected=0 named=""
    while IFS=$'\t' read -r outcome name reason; do
        case "$outcome" in
            passed) passed=$((passed + 1)) ;;
            failed)
                failed=$((failed + 1))
                [ "$failed" -gt 5 ] || named+="${named:+; }FAIL $name: $reason"
                ;;
            skipped) skipped=$((skipped + 1)) ;;
            deselected) deselected=$((deselected + 1)) ;;
        esac
    done
    named="${named:+ ($named$([ "$failed" -le 5 ] || printf '; +%s more' "$((failed - 5))"))}"
    printf '%s %s %s %s %s of %s scenarios failed%s\n' "$passed" "$failed" "$skipped" "$deselected" "$failed" "$((passed + failed))" "$named"
}

_join_reasons() {
    local out="$1" reason
    shift
    for reason in "$@"; do
        out+="; $reason"
    done
    printf '%s' "$out"
}

_level_verdict() {
    if [ "$1" -ne 0 ]; then
        printf 'FAIL'
    elif [ "$2" -gt 0 ]; then
        printf 'PASS (retried %s)' "$2"
    else
        printf 'PASS'
    fi
}

failed=0
failed_files=()
memory_error_files=()
evidence_files=()
tests_passed=0
tests_failed=0
tests_skipped=0
tests_deselected=0
declare -A level_failed=([L1]=0 [L2]=0) level_retried=([L1]=0 [L2]=0)
for job in "${job_list[@]}"; do
    test_file="$job"
    tag="$(_job_tag "$job")"
    level="L1"
    if [[ "$tag" == test_digital_twin_* || "$tag" == scenarios\[* ]]; then
        level="L2"
    fi
    status="$(cat "$results_dir/$tag.status" 2>/dev/null || true)"
    log_file="$results_dir/$tag.log"
    # The deciding attempt's lines: everything after the log's last attempt line, the whole log without one.
    deciding="$(awk -v m="[$tag] == attempt " 'index($0, m) == 1 { buf = ""; next } { buf = buf $0 "\n" } END { printf "%s", buf }' "$log_file" 2>/dev/null || true)"
    # Its microtest closing line; a log without one crashed or was killed.
    count_line="$(awk -v p="[$tag] " 'index($0, p) == 1 && substr($0, length(p) + 1) ~ /^[0-9]+\/[0-9]+ passed, [0-9]+ failed, [0-9]+ skipped/ { last = $0 } END { printf "%s", last }' <<<"$deciding")"
    reasons=()
    scenario_outcomes=""
    if [[ "$tag" == scenarios\[* ]]; then
        # The harness prints no microtest closing line: its counts are its run record's, one test per scenario.
        if scenario_outcomes="$(_scenario_outcomes "$results_dir/scenarios_${tag:10:-1}.json" 2>/dev/null)"; then
            read -r scenario_passed scenario_failed scenario_skipped scenario_deselected file_failed_tests < <(_scenario_counts <<<"$scenario_outcomes")
            tests_passed=$((tests_passed + scenario_passed))
            tests_failed=$((tests_failed + scenario_failed))
            tests_skipped=$((tests_skipped + scenario_skipped))
            tests_deselected=$((tests_deselected + scenario_deselected))
        else
            scenario_outcomes=""
            file_failed_tests="failed"
            reasons+=("no verdict (run record missing or unreadable)")
        fi
    elif [[ "$count_line" =~ ([0-9]+)/([0-9]+)\ passed,\ ([0-9]+)\ failed,\ ([0-9]+)\ skipped ]]; then
        tests_passed=$((tests_passed + BASH_REMATCH[1]))
        tests_failed=$((tests_failed + BASH_REMATCH[3]))
        tests_skipped=$((tests_skipped + BASH_REMATCH[4]))
        file_failed_tests="${BASH_REMATCH[3]} of ${BASH_REMATCH[2]} tests failed"
        if [ "${BASH_REMATCH[3]}" -gt 0 ]; then
            file_failed_tests+="$(_failing_tests "$tag" "${BASH_REMATCH[3]}" <<<"$deciding")"
        fi
    else
        file_failed_tests="failed"
        reasons+=("no test count (crashed or killed)")
    fi
    # A missing or empty status is a missing verdict, never a pass by omission.
    case "$status" in
        PASS | "RETRIED-PASS "*) ;;
        FAIL) reasons=("$file_failed_tests" "${reasons[@]}") ;;
        *) reasons=("no verdict" "${reasons[@]}") ;;
    esac
    if [ -s "$results_dir/$tag.noverdict" ]; then
        reasons+=("no verdict (per-file log missing or unreadable)")
    fi
    if [ "${#reasons[@]}" -gt 0 ]; then
        failed=1
        failed_files+=("$test_file")
    fi
    # Independent of pass/fail: a file that degraded gracefully and passed is exactly the silent
    # case this exists for, and one that failed still names the allocation as the likelier cause.
    if [ -s "$results_dir/$tag.memerr" ]; then
        failed=1
        memory_error_files+=("$test_file")
        reasons+=("MemoryError seen")
    fi
    # A failed file that also needed a retry keeps that fact in its reason rather than losing it.
    if [ "${#reasons[@]}" -gt 0 ] && [[ "$status" == "RETRIED-PASS "* ]]; then
        reasons+=("passed on attempt ${status#RETRIED-PASS }")
    fi
    if [ "${#reasons[@]}" -gt 0 ]; then
        level_failed[$level]=1
        evidence_files+=("$log_file" "$results_dir/$tag.memerr" "$results_dir/$tag.noverdict")
        summary_add failed "$test_file" "$(_join_reasons "${reasons[@]}")"
    elif [ "$status" != "PASS" ]; then
        level_retried[$level]=$((level_retried[$level] + 1))
        evidence_files+=("$log_file")
        summary_add retried "$test_file" "${status#RETRIED-PASS }"
        echo "root-cause item: $tag needed attempt ${status#RETRIED-PASS } - record it as a root-cause item"
    else
        summary_add passed "$test_file"
    fi
    # Each microtest SKIP line of the deciding attempt is named with its reason, not only counted.
    while IFS= read -r skip_line; do
        if [[ "$skip_line" =~ ^"[$tag] SKIP "([^:]+):\ ?(.*)$ ]]; then
            summary_add skipped "$test_file::${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
        fi
    done < <(printf '%s\n' "$deciding" | grep -F "[$tag] SKIP " || true)
    # A scenario the harness did not run is named with its reason: a driver the device does not wire, or one its
    # shared port 53 deselects (run_digital_twin_ci.sh holds the port and runs those).
    while IFS=$'\t' read -r outcome name reason; do
        case "$outcome" in
            skipped) summary_add skipped "$test_file::$name" "$reason" ;;
            deselected) summary_add deselected "$test_file::$name" "runner selection: $reason" ;;
        esac
    done <<<"$scenario_outcomes"
done
if [ "$coverage" = "1" ]; then
    for test_file in "${lwip_host_files[@]}"; do
        summary_add skipped "$test_file" "not run under --coverage (the plain pass runs them)"
    done
    for device in "${devices[@]}"; do
        summary_add skipped "scenarios[$device]" "not run under --coverage (the plain pass runs them)"
    done
fi

# The backgrounded tests_scripts/ job is reaped by the same unqualified `wait` above. Its status
# file is written in both branches, and its run record (scripts/_pytest_run_record.py) carries the
# counts: a missing or unreadable either one is no verdict, never a PASS by omission.
tests_scripts_record="$results_dir/tests_scripts.json"
tests_scripts_result="$(cat "$tests_scripts_status_file" 2>/dev/null || true)"
l0_reasons=()
case "$tests_scripts_result" in
    PASS | "RETRIED-PASS "*) ;;
    *) l0_reasons+=("pytest exited nonzero or timed out") ;;
esac
# One helper start reads the record for every listing below (a uv start costs about 0.3 s of environment lookup),
# each listing opened by a "<RS><name>" line; an unreadable record leaves them all empty, which is no verdict.
l0_listings="$(uv run python - "$tests_scripts_record" 2>/dev/null <<'PYEOF'
import sys
sys.path.insert(0, "scripts")
import _summary_block
for listing in ("failed", "skipped", "deselected", "recovered", "notes", "counts"):
    print(f"\x1e{listing}", flush=True)
    _summary_block.main(["--from-run-record", sys.argv[1], *(["--counts-only"] if listing == "counts" else ["--list", listing])])
PYEOF
)" || l0_listings=""
_l0_listing() {
    printf '%s\n' "$l0_listings" | awk -v want=$'\x1e'"$1" 'index($0, "\036") == 1 { on = ($0 == want); next } on'
}
# Its failed, skipped, deselected and recovered tests are named here, each with its reason, since the
# block counts files: a skip is counted and named, never only a dot in pytest's -q line.
l0_recovered=0
for kind in failed skipped deselected recovered; do
    listing="$(_l0_listing "$kind")"
    if [ -n "$listing" ]; then
        echo "tests_scripts/ $kind:"
        printf '%s\n' "$listing" | sed -e 's/\t/: /' -e 's/^/  - /'
        [ "$kind" != "recovered" ] || l0_recovered="$(printf '%s\n' "$listing" | wc -l)"
    fi
done
l0_counts="$(_l0_listing counts)"
if [[ "$l0_counts" =~ ^([0-9]+)\ ([0-9]+)\ ([0-9]+)\ ([0-9]+)$ ]]; then
    summary_counts_line "tests_scripts tests" "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}" 0 "$l0_recovered" 0
    if [ "${BASH_REMATCH[2]}" -ne 0 ]; then
        l0_reasons+=("${BASH_REMATCH[2]} failed (listed above)")
    fi
else
    l0_reasons+=("no verdict (run record missing or unreadable)")
fi
# Its result and session notes go into the block's Notes: list.
while IFS=$'\t' read -r note_name note_text; do
    summary_note "$note_name" "$note_text"
done < <(_l0_listing notes)
# A pass that needed a retry is reported apart, as a retried file is: a root-cause item, never a plain PASS.
l0_retried=0
if [ "${#l0_reasons[@]}" -gt 0 ]; then
    [[ "$tests_scripts_result" != "RETRIED-PASS "* ]] || l0_reasons+=("passed on attempt ${tests_scripts_result#RETRIED-PASS }")
    tests_scripts_result="FAIL"
    failed=1
    evidence_files+=("$tests_scripts_record")
    summary_add failed "tests_scripts/ (pytest)" "$(_join_reasons "${l0_reasons[@]}")"
elif [ "$tests_scripts_result" != "PASS" ]; then
    l0_retried=1
    evidence_files+=("$tests_scripts_record")
    summary_add retried "tests_scripts/ (pytest)" "${tests_scripts_result#RETRIED-PASS }"
    echo "root-cause item: tests_scripts/ needed attempt ${tests_scripts_result#RETRIED-PASS } - record it as a root-cause item"
fi
summary_counts_line tests "$tests_passed" "$tests_failed" "$tests_skipped" "$tests_deselected" 0 0 0
l2_scope="tests/test_digital_twin_*.py and the scenario harness"
[ "$coverage" = "0" ] || l2_scope="tests/test_digital_twin_*.py only"
summary_levels "L0 $(_level_verdict "$([ "$tests_scripts_result" = "FAIL" ] && printf 1 || printf 0)" "$l0_retried") · L1 $(_level_verdict "${level_failed[L1]}" "${level_retried[L1]}") · L2 $(_level_verdict "${level_failed[L2]}" "${level_retried[L2]}") ($l2_scope; run_digital_twin_ci.sh not run)"
if [ "$coverage" = "1" ]; then
    summary_gc_stage "coverage run (settrace)"
elif [ -n "${GC_THRESHOLD:-}" ]; then
    summary_gc_stage "$GC_THRESHOLD"
else
    summary_gc_stage "-1 (reactive default)"
fi

# Each `|| coverage_render_failed=1` rather than bare: under `set -e` a renderer failure would
# abort here with ITS exit code, which the caller cannot tell from a failed test. Coverage is a
# report and never gates, but the test result under this binary must (exit 3 below).
coverage_render_failed=0
if [ "$coverage" = "1" ]; then
    echo "== Rendering coverage report"
    uv run scripts/_render_coverage.py --raw-dir "$raw_dir" --src-dir src --html-dir htmlcov --markdown-file coverage_summary.md || coverage_render_failed=1
    echo "== Rendering digital_twin/ coverage report"
    uv run scripts/_render_coverage.py --raw-dir "$raw_dir" --src-dir digital_twin --html-dir htmlcov_digital_twin --markdown-file coverage_summary_digital_twin.md || coverage_render_failed=1
    echo "== Rendering the generated modules' coverage report"
    uv run scripts/_render_coverage.py --raw-dir "$raw_dir" --src-dir build/generated_src --html-dir htmlcov_generated --markdown-file coverage_summary_generated.md || coverage_render_failed=1
    echo "== Rendering the host build chain's coverage report (buildgen/, scripts/, toolchain/)"
    uv run coverage html --data-file="$results_dir/host.coverage" -d htmlcov_host || coverage_render_failed=1
    uv run coverage report --data-file="$results_dir/host.coverage" --format=markdown >coverage_summary_host.md || coverage_render_failed=1
fi

if [ "${#memory_error_files[@]}" -gt 0 ]; then
    echo "MemoryError seen (caught-and-logged counts too - SPECIFICATION.md Part I.4(e)):"
    for f in "${memory_error_files[@]}"; do
        echo "  - $f"
        sed "s/^/      /" "$results_dir/$(_job_tag "$f").memerr"
    done
fi
# A workflow-command annotation is the only channel that carries a failing file's own output off
# the runner without reading the raw log, which GitHub serves from a storage host some environments
# cannot reach at all - and it puts the failure on the PR page for a human too.
if [ -n "${GITHUB_ACTIONS:-}" ]; then
    # GitHub keeps only 10 error annotations per step: the pytest tier's goes first, per-file ones
    # stop at 8, and a last one counts the rest, so nothing past the cap vanishes without a trace.
    if [ "$tests_scripts_result" = "FAIL" ]; then
        echo "::error title=tests_scripts/ (CPython/pytest)::the pytest tier failed - its own output is in this step's log, above the summary"
    fi
    annotations_left=8
    annotations_withheld=0
    for f in "${failed_files[@]}"; do
        if [ "$annotations_left" -eq 0 ]; then
            annotations_withheld=$((annotations_withheld + 1))
            continue
        fi
        annotation_tag="$(_job_tag "$f")"
        annotation_detail="$({ tail -n 40 "$results_dir/$annotation_tag.log" 2>/dev/null || true; } | sed -e 's/%/%25/g' -e 's/\r$//' | awk '{printf "%s%%0A", $0}')"
        echo "::error title=$f::$annotation_detail"
        annotations_left=$((annotations_left - 1))
    done
    for f in "${memory_error_files[@]}"; do
        if [ "$annotations_left" -eq 0 ]; then
            annotations_withheld=$((annotations_withheld + 1))
            continue
        fi
        annotation_tag="$(_job_tag "$f")"
        annotation_detail="$({ cat "$results_dir/$annotation_tag.memerr" 2>/dev/null || true; } | sed -e 's/%/%25/g' -e 's/\r$//' | awk '{printf "%s%%0A", $0}')"
        echo "::error title=$f (allocation failure)::$annotation_detail"
        annotations_left=$((annotations_left - 1))
    done
    if [ "$annotations_withheld" -gt 0 ]; then
        echo "::error title=and $annotations_withheld more::$annotations_withheld further failing-file annotation(s) withheld at GitHub's 10-per-step cap - the step log's summary names every file"
    fi
fi

# Three outcomes, three codes, because the caller acts differently on each: 1 = a test failed,
# 3 = every test passed and only the report could not be rendered, 0 = both fine. CI gates on 1
# and tolerates 3 (SPECIFICATION.md Part E.5.3); a test failure is never advisory.
exit_code=0
if [ "$failed" -ne 0 ]; then
    exit_code=1
elif [ "$coverage_render_failed" -ne 0 ]; then
    exit_code=3
fi

# The deciding logs of every failed, no-verdict, allocation-flagged and retried file, plus the
# block itself, move into build/archive/test_sh/<ts>/ (newest three kept); a green run keeps the
# block only. Archived before the block is printed, so nothing follows it on stdout.
#
# summary_print returns the code it printed (a failed item never leaves with 0 or 3); exit with it.
summary_status=0
summary_text="$(summary_print "scripts/test.sh" "$exit_code")" || summary_status=$?
printf '%s\n' "$summary_text" >"$results_dir/summary.txt"
if evidence_dir="$(uv run scripts/_archive_evidence.py --runner test_sh "${evidence_files[@]}" "$results_dir/summary.txt")"; then
    evidence_archived=1
    echo "== Evidence archived in $evidence_dir"
else
    echo "== the evidence could not be archived - kept in $results_dir" >&2
    results_dir=""
fi
printf '%s\n' "$summary_text"
exit "$summary_status"
