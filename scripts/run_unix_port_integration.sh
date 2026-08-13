#!/usr/bin/env bash
# Dedicated entry point for FINAL_WIRING_PLAN.md's Step 5 ("full Unix-port integration") -
# digital_twin/run_wozi_integration.py, run against the real digital_twin buses under the real
# MicroPython Unix-port interpreter. Deliberately separate from scripts/test.sh: the twin needs its
# own MICROPYPATH ("src:digital_twin:frozen_modules:.frozen") that never carries a "tests" segment
# (digital_twin/README.md's own "never together" rule - see that doc's "Swapping the twin in for a
# Unix-port run (Step 5)" section), and run_wozi_integration.py can run forever (no --duration -
# owner decision 3, a real browser on this machine should be able to reach it), which would hang
# scripts/test.sh's own default tests/test_*.py glob loop if it were discovered there instead.
#
# Usage:
#   scripts/run_unix_port_integration.sh                        # bounded automated soak run, default flags
#   scripts/run_unix_port_integration.sh --duration 0            # same, but exits immediately after the soak
#   scripts/run_unix_port_integration.sh --fault sgp40:writeto   # manual fault-injection exploration
#   scripts/run_unix_port_integration.sh --host 0.0.0.0 --port 8080   # reachable from outside this machine
#
# Every flag forwards straight through to run_wozi_integration.py's own parse_args() - see that
# module's own docstring for the full list (--host/--port/--fram-state-path/--seed/--fault/
# --wifi-outcome/--soak-cycles/--duration). No flags given still runs the automated soak check
# (RunConfig's own defaults - localhost:8080, 20 soak cycles) and then serves forever, matching
# "both" halves of owner decision 7 (automated assertion now, still reachable/observable after).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

export TZ=UTC  # same reasoning as scripts/test.sh's own identical export - see that script's own
# comment for the full time.mktime(time.gmtime()) non-UTC-host explanation.

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

echo "== Running digital_twin/run_wozi_integration.py"
MICROPYPATH="src:digital_twin:frozen_modules:.frozen" "$micropython_bin" digital_twin/run_wozi_integration.py "$@"
