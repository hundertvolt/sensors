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
for test_file in tests/test_*.py; do
    echo "== Running $test_file"
    # .frozen must be included explicitly: MICROPYPATH replaces MicroPython's default sys.path
    # rather than extending it, and the default path is what makes frozen-in modules (asyncio
    # included) resolvable at all. Confirmed directly against the built interpreter - dropping
    # this breaks `import asyncio` for any async src/ file with no import error pointing at why.
    if [ "$coverage" = "1" ]; then
        raw_out="$raw_dir/$(basename "$test_file" .py).json"
        if ! MICROPYPATH="src:tests:.frozen" "$micropython_bin" tests/_coverage_runner.py "$test_file" "$raw_out"; then
            failed=1
        fi
    else
        if ! MICROPYPATH="src:tests:.frozen" "$micropython_bin" "$test_file"; then
            failed=1
        fi
    fi
done

if [ "$coverage" = "1" ]; then
    echo "== Rendering coverage report"
    uv run scripts/_render_coverage.py --raw-dir "$raw_dir" --src-dir src --html-dir htmlcov --xml-file coverage.xml --markdown-file coverage_summary.md
fi

exit "$failed"
