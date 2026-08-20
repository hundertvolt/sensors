#!/usr/bin/env bash
# CI entry point for the digital twin's automated clean/build/test cycle - the on-demand manual
# walkthrough (fresh boot, every GET/PUT endpoint, DebugLevel=5 verbose logging, bus fault
# injection, settings/error persistence across a real reboot, soak) turned into an automated,
# CI-gating check. See digital_twin/README.md's "Automated CI suite" section for the full
# reference and SPECIFICATION.md's "any new module joins the twin" rule this exists to enforce.
#
# Clean: wipes any leftover digital_twin/*.json state files and digital_twin/config/ before
# starting, so every run (CI or local) begins from a genuinely blank twin - not just relying on a
# GitHub-hosted runner's own fresh-VM-per-job property. scripts/_digital_twin_ci_suite.py itself
# repeats this at the very start of its own run() for the same reason (defense in depth - this
# script's clean step and that one's are deliberately redundant, not "either/or").
#
# Build: builds the MicroPython Unix port (if not already cached - same
# $PICO_TOOLCHAIN_DIR/SKIP_APT convention as scripts/test.sh and
# scripts/run_unix_port_integration.sh) and frozen_modules/frozen_html.py. Must succeed before any
# test phase can run - a build failure here fails the job immediately via `set -e`, before
# scripts/_digital_twin_ci_suite.py ever launches a twin subprocess.
#
# Test: hands off to scripts/_digital_twin_ci_suite.py (a self-contained `uv run` CPython script,
# not MicroPython - it only orchestrates the MicroPython subprocess and speaks plain HTTP to it),
# which drives digital_twin/run_wozi_integration.py through five real subprocess runs and asserts
# every step. Exit code propagates straight through to this script's own exit code.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

export TZ=UTC  # same reasoning as scripts/test.sh's own identical export.

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

echo "== Building frozen_modules/frozen_html.py"
scripts/build_frozen_html.sh

echo "== Running digital-twin automated CI suite"
uv run scripts/_digital_twin_ci_suite.py --micropython-bin "$micropython_bin" --logs-dir "digital_twin_ci_logs"
