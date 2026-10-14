#!/usr/bin/env bash
# CI entry point for the digital twin's automated clean/build/test cycle - the manual walkthrough
# turned into a CI-gating check. Full reference: digital_twin/README.md's "Automated CI suite" and
# SPECIFICATION.md Part A.10.
#
# Usage: scripts/run_digital_twin_ci.sh <device> [--gc-threshold -1|32768] [--part suite|harness]
# Device-generic since Part L.4: ci.yml's digital-twin-e2e job runs this once per real device, GC stage and part via
# its own strategy.matrix, so each is attributable on its own; without the options, both stages and parts run here.
#
# The suite keeps each pass's state under its logs directory and archives it before every fresh start.
#
# Build needs the Unix port (same $PICO_TOOLCHAIN_DIR/SKIP_APT convention as scripts/test.sh) and
# the real production website for $device, via build_website.sh, where each part's twins read it. `set -e`
# fails the job here before any twin subprocess launches.
#
# Test hands off to scripts/_digital_twin_ci_suite.py (CPython, driving run_generic_integration.py over
# HTTP through $device's own generated module), then a uart_link device's Run 3 again on a CRC16-derived
# TOML, then the host-side scenario harness, each at the stage given. Every step runs; the exit is the worst.
set -euo pipefail
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    cat <<'EOF'
Usage: scripts/run_digital_twin_ci.sh <device> [--gc-threshold -1|32768] [--part suite|harness]
Runs scripts/_digital_twin_ci_suite.py for one devices/<device>.toml, Run 3 again on a CRC16-derived
TOML for a device wiring a uart_link pair (the suite part), then scripts/_digital_twin_scenarios.py (the
harness part), and exits with the worst result. Each runs at both GC stages, -1 then 32768, or with
--gc-threshold at that one only; --part runs one part only (one CI job per device, stage and part).

Environment:
  PICO_TOOLCHAIN_DIR   toolchain cache (default: ~/pico-toolchain)
  SKIP_APT=1           skip the system-package step of a toolchain build (default: 0)
EOF
    exit 0
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."

device="${1:-}"
stages=(-1 32768)  # Part I.4(e): -1 first, then the chosen threshold
stage_args=()
parts=(suite harness)
shift || true
while [ "$#" -gt 0 ]; do
    case "$1:${2:-}" in
        --gc-threshold:-1 | --gc-threshold:32768) stages=("$2"); stage_args=(--gc-threshold "$2") ;;
        --part:suite | --part:harness) parts=("$2") ;;
        *)
            echo "usage: scripts/run_digital_twin_ci.sh <device> [--gc-threshold -1|32768] [--part suite|harness]" >&2
            exit 2
            ;;
    esac
    shift 2
done
runs_part() { [[ " ${parts[*]} " == *" $1 "* ]]; }
if [ -z "$device" ] || [ ! -f "devices/$device.toml" ]; then
    known=""
    for toml in devices/*.toml; do known="$known $(basename "$toml" .toml)"; done
    echo "usage: scripts/run_digital_twin_ci.sh <device> - one of:$known" >&2
    exit 2
fi

# The suite's twins bind the product's ports 53 (Run 7's captive DNS) and 18080: one suite holds them at a
# time, and a second exits 1 here, before anything is built (CLAUDE.md). The EXIT trap releases them.
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_port_lock.sh
trap port_lock_release_all EXIT
port_lock_take 53 scripts/run_digital_twin_ci.sh
port_lock_take 18080 scripts/run_digital_twin_ci.sh

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

# Run 7's and the harness's port-53 DNS server binds the real privileged port, which a non-root runner
# cannot do without this capability on the interpreter binary. Granted fresh every invocation
# because a cached toolchain archive does not carry xattrs (digital_twin/README.md has the account).
echo "== Granting CAP_NET_BIND_SERVICE to $micropython_bin (needed for Run 7's and the harness's real port-53 DNS server)"
if [ "$(id -u)" -eq 0 ]; then
    setcap 'cap_net_bind_service=+ep' "$micropython_bin"
else
    sudo setcap 'cap_net_bind_service=+ep' "$micropython_bin"
fi

# Each part's twins boot the site it builds: the suite's frozen_modules/, the harness's own per-device copy.
if runs_part suite; then
    echo "== Building the real $device website into frozen_modules/frozen_html.py"
    scripts/build_website.sh "$device"
fi
if runs_part harness; then
    echo "== Building the real $device website into build/generated_html/$device/frozen_html.py"
    scripts/build_website.sh "$device" "build/generated_html/$device/frozen_html.py"
fi

# No static src/sensortask_*.py exists any more (SPECIFICATION.md Part L.2), so every device's
# module + wiring plan is generated fresh here into build/generated_src/ (gitignored).
# Where that resolves from: _digital_twin_ci_suite.py's own MICROPYPATH constant.
echo "== Generating buildgen device modules + wiring plans into build/generated_src/"
uv run scripts/_generate_sensortask_modules.py

worst=0
record() { if [ "$1" -gt "$worst" ]; then worst=$1; fi; }

if runs_part suite; then
    echo "== Running digital-twin automated CI suite (device: $device)"
    rc=0; uv run scripts/_digital_twin_ci_suite.py --micropython-bin "$micropython_bin" --device "$device" --logs-dir "digital_twin_ci_logs" "${stage_args[@]}" || rc=$?; record "$rc"

    # A device wiring a uart_link pair runs Run 3's link cell again with both ends on CRC16 (owner, 2026-09-30, paraphrase:
    # L2 builds the pair in both modes); the derived TOML must name crc16 exactly once per link and no other crc.
    if grep -q '^driver = "uart_link"' "devices/$device.toml"; then
        derived="digital_twin_ci_logs/crc16/$device.toml"
        mkdir -p "$(dirname "$derived")"
        sed '/^driver = "uart_link"$/a crc = "crc16"' "devices/$device.toml" > "$derived"
        links=$(grep -c '^driver = "uart_link"$' "$derived")
        if [ "$(grep -c '^crc = "crc16"$' "$derived")" -ne "$links" ] || [ "$(grep -c '^crc = ' "$derived")" -ne "$links" ]; then
            echo "error: $derived does not name crc16 exactly once per uart_link instance" >&2
            record 1
        else
            echo "== Running Run 3 on the CRC16-derived $derived"
            rc=0; uv run scripts/_digital_twin_ci_suite.py --micropython-bin "$micropython_bin" --device "$device" --device-toml "$derived" --only 3 --logs-dir "digital_twin_ci_logs/crc16" "${stage_args[@]}" || rc=$?; record "$rc"
        fi
    fi
fi

if runs_part harness; then
    echo "== Running the host-side scenario harness (device: $device)"
    for stage in "${stages[@]}"; do
        rc=0; uv run scripts/_digital_twin_scenarios.py --micropython-bin "$micropython_bin" --device "$device" --gc-threshold "$stage" --exclusive-port-53 --logs-dir "digital_twin_ci_logs/scenarios/gc_threshold_${stage/-/neg}" || rc=$?; record "$rc"
    done
fi
exit "$worst"
