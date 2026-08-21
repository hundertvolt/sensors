#!/usr/bin/env bash
# Dedicated entry point for the digital twin's "full Unix-port integration" run -
# digital_twin/run_wozi_integration.py, run against the real digital_twin buses under the real
# MicroPython Unix-port interpreter. Deliberately separate from scripts/test.sh: the twin needs its
# own MICROPYPATH ("src:digital_twin:ext:frozen_modules:.frozen") that never carries a "tests"
# segment (digital_twin/README.md's own "never together" rule - see that doc's "Swapping the twin
# in for a Unix-port run" section), and run_wozi_integration.py can run forever (no
# --duration - a real browser on this machine should be able to reach it), which
# would hang scripts/test.sh's own default tests/test_*.py glob loop if it were discovered there
# instead.
#
# "ext" is required here (unlike scripts/test.sh's own MICROPYPATH) because src/sensortask_wozi.py
# unconditionally imports vendored ext/microdot.py - every tests/test_*.py file that needs it works
# around scripts/test.sh's own ext-less MICROPYPATH with its own per-file
# sys.path.insert(0, "ext") (see e.g. tests/test_sensortask_wozi.py's own comment), but this is the
# real standalone entry point, not a test file, so it needs the real fix here instead. Found by
# actually running this script standalone for the first time (a manual baseline-verification pass) -
# every prior verification of this file went through the test-harness sys.path.insert() workaround
# instead, which silently masked the gap.
#
# Usage:
#   scripts/run_unix_port_integration.sh                        # just launch + serve forever, no flags
#   scripts/run_unix_port_integration.sh --soak                 # bounded automated soak run, then serves forever
#   scripts/run_unix_port_integration.sh --soak --duration 0    # same, but exits immediately after the soak
#   scripts/run_unix_port_integration.sh --fault sgp40:writeto  # manual fault-injection exploration
#   scripts/run_unix_port_integration.sh --host 0.0.0.0 --port 8080   # reachable from outside this machine
#
# Every flag forwards straight through to run_wozi_integration.py's own parse_args() - see that
# module's own docstring for the full list (--host/--port/--fram-state-path/--seed/--fault/
# --wifi-outcome/--soak/--soak-cycles/--duration). No flags given just launches the twin and serves
# forever (RunConfig's own defaults - localhost:8080), the same "reachable/observable" half of owner
# decision 7 a real rp2040 boot would give you - the automated soak assertion is a specialty, opted
# into via --soak (or --soak-cycles, which implies it), not part of the plain launch path.
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
MICROPYPATH="src:digital_twin:ext:frozen_modules:.frozen" "$micropython_bin" digital_twin/run_wozi_integration.py "$@"
