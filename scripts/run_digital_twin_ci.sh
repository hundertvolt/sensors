#!/usr/bin/env bash
# CI entry point for the digital twin's automated clean/build/test cycle - the manual walkthrough
# turned into a CI-gating check. Full reference: digital_twin/README.md's "Automated CI suite" and
# SPECIFICATION.md Part A.10.
#
# Usage: scripts/run_digital_twin_ci.sh [device]   (default: wozi)
# Device-generic since Part L.4: ci.yml's digital-twin-e2e job runs this once per real device via
# its own strategy.matrix, so each device's 14-run suite is attributable on its own.
#
# Clean wipes leftover digital_twin/*.json state and digital_twin/config/ so every run starts blank
# - deliberately redundant with _digital_twin_ci_suite.py's own identical clean, not either/or.
#
# Build needs the Unix port (same $PICO_TOOLCHAIN_DIR/SKIP_APT convention as scripts/test.sh) and
# the real production website for $device, via build_website.sh rather than build_frozen_html.sh's
# html_stub default. `set -e` fails the job here before any twin subprocess launches.
#
# Test hands off to scripts/_digital_twin_ci_suite.py - CPython, orchestrating the MicroPython
# subprocess over plain HTTP - which drives run_generic_integration.py through $device's own
# generated module and propagates its exit code straight through.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

device="${1:-wozi}"

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

# Run 7's captive-portal DNSServer binds the real privileged port 53, which a non-root runner
# cannot do without this capability on the interpreter binary. Granted fresh every invocation
# because a cached toolchain archive does not carry xattrs (digital_twin/README.md has the account).
echo "== Granting CAP_NET_BIND_SERVICE to $micropython_bin (needed for Run 7's real port-53 DNS server)"
if [ "$(id -u)" -eq 0 ]; then
    setcap 'cap_net_bind_service=+ep' "$micropython_bin"
else
    sudo setcap 'cap_net_bind_service=+ep' "$micropython_bin"
fi

echo "== Building the real $device website into frozen_modules/frozen_html.py"
scripts/build_website.sh "$device"

# No static src/sensortask_*.py exists any more (SPECIFICATION.md Part L.2), so every device's
# module + wiring plan is generated fresh here into build/generated_src/ (gitignored).
# Where that resolves from: _digital_twin_ci_suite.py's own MICROPYPATH constant.
echo "== Generating buildgen device modules + wiring plans into build/generated_src/"
uv run scripts/_generate_sensortask_modules.py

echo "== Running digital-twin automated CI suite (device: $device)"
uv run scripts/_digital_twin_ci_suite.py --micropython-bin "$micropython_bin" --device "$device" --logs-dir "digital_twin_ci_logs"
