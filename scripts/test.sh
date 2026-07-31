#!/usr/bin/env bash
# Runs the tests/ suite under a real MicroPython Unix-port interpreter (not CPython/pytest - see
# BACKLOG.md's "Self-contained venv via uv" testing requirement). Builds the toolchain on first
# run via `uv run toolchain/setup_toolchain.py` (plain `setup` - building/verifying the Unix port
# is just part of what `setup`/`test` already do, there's no separate `unix` subcommand, see
# toolchain/README.md) if the Unix port binary isn't already there, then reuses the cached build
# on subsequent runs. This now also builds the RP2040 firmware/ARM toolchain/picotool as a side
# effect of `setup` doing all four of its verification checks together - heavier than building
# just the Unix port alone, but there's no lighter-weight entry point anymore now that Unix-port
# building lives inside `setup`/`test` rather than a standalone subcommand. Set PICO_TOOLCHAIN_DIR
# to relocate the cache, or SKIP_APT=1 if the required system packages (see
# toolchain/versions.toml) are already present.
#
# --coverage: runs the same tests, under the same Unix port binary (it's always built with
# MICROPY_PY_SYS_SETTRACE=1 - see build_unix_port() - so there's no separate coverage-only
# interpreter to build), but with tests/_coverage_runner.py wrapping each test file to install a
# sys.settrace line tracer scoped to src/ and record which lines actually executed. The merged
# result is handed to scripts/_render_coverage.py (a separate, self-contained `uv run` script -
# coverage.py itself only runs under CPython, never under MicroPython) to render an HTML report
# (htmlcov/), a Cobertura XML report (coverage.xml, for e.g. Codecov), and a markdown summary
# (coverage_summary.md). See README.md's "Code quality tooling" for a usage example and
# tests/README.md for the full pipeline this is one stage of.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

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

toolchain_dir="${PICO_TOOLCHAIN_DIR:-$HOME/pico-toolchain}"
micropython_bin="$toolchain_dir/micropython/ports/unix/build-standard/micropython"

if [ ! -x "$micropython_bin" ]; then
    echo "MicroPython Unix port not found at $micropython_bin - building it now" >&2
    skip_apt_flag=()
    if [ "${SKIP_APT:-0}" = "1" ]; then
        skip_apt_flag=(--skip-apt)
    fi
    uv run toolchain/setup_toolchain.py setup --toolchain-dir "$toolchain_dir" "${skip_apt_flag[@]}"
fi

raw_dir=""
if [ "$coverage" = "1" ]; then
    raw_dir="$(mktemp -d)"
    trap 'rm -rf "$raw_dir"' EXIT
fi

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
per_file_timeout_s="${PER_FILE_TIMEOUT_S:-180}"
max_attempts=3
for test_file in tests/test_*.py; do
    echo "== Running $test_file"
    # .frozen must be included explicitly: MICROPYPATH replaces MicroPython's default sys.path
    # rather than extending it, and the default path is what makes frozen-in modules (asyncio
    # included) resolvable at all. Confirmed directly against the built interpreter - dropping
    # this breaks `import asyncio` for any async src/ file with no import error pointing at why.
    if [ "$coverage" = "1" ]; then
        raw_out="$raw_dir/$(basename "$test_file" .py).json"
        cmd=(tests/_coverage_runner.py "$test_file" "$raw_out")
    else
        cmd=("$test_file")
    fi
    for attempt in $(seq 1 "$max_attempts"); do
        if MICROPYPATH="src:tests:.frozen" stdbuf -oL -eL timeout --kill-after=10 "$per_file_timeout_s" "$micropython_bin" "${cmd[@]}"; then
            ec=0
        else
            ec=$?
        fi
        if [ "$ec" -eq 0 ]; then
            break
        elif [ "$ec" -eq 124 ] && [ "$attempt" -lt "$max_attempts" ]; then
            echo "== $test_file exceeded ${per_file_timeout_s}s on attempt $attempt/$max_attempts - retrying in case of transient runner contention" >&2
            continue
        else
            if [ "$ec" -eq 124 ]; then
                echo "== $test_file exceeded ${per_file_timeout_s}s on all $max_attempts attempts - treating as a real failure instead of hanging the job" >&2
            fi
            failed=1
            break
        fi
    done
done

if [ "$coverage" = "1" ]; then
    echo "== Rendering coverage report"
    uv run scripts/_render_coverage.py --raw-dir "$raw_dir" --src-dir src --html-dir htmlcov --xml-file coverage.xml --markdown-file coverage_summary.md
fi

exit "$failed"
