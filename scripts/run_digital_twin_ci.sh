#!/usr/bin/env bash
# L2 for one device: archives that device's previous logs, builds its site and generated modules, runs
# scripts/_digital_twin_ci_suite.py at both GC stages, then the host-side scenario harness at both, and exits with the
# worst result. Reference: digital_twin/README.md "Automated CI suite"; ci.yml runs it per device, GC stage and part.
#
# Archive: the previous run's logs and state (digital_twin_ci_logs/<device>/) move into
# build/archive/digital_twin_ci_<device>/ (last three kept); nothing is deleted.
set -euo pipefail
usage_line="Usage: scripts/run_digital_twin_ci.sh <device> [--gc-threshold -1|32768] [--part suite|harness] [--only RUN,...] [--repeat N]"
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    cat <<EOF
$usage_line
Runs scripts/_digital_twin_ci_suite.py for one devices/<device>.toml, Run 3 again on a CRC16-derived
TOML for a device wiring a uart_link pair (the suite part), then scripts/_digital_twin_scenarios.py (the
harness part), and exits with the worst result. Each runs at both GC stages, -1 then 32768, or with
--gc-threshold at that one only; --part runs one part only (one CI job per device, stage and part).
--only and --repeat go to the suite's own options of those names (diagnosis).

Environment:
  PICO_TOOLCHAIN_DIR   toolchain cache (default: ~/pico-toolchain)
  SKIP_APT=1           skip the system-package step of a toolchain build (default: 0)
EOF
    exit 0
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."

_usage_error() {
    printf '%s\n%s\n' "$1" "$usage_line" >&2
    exit 2
}

# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_devices.sh
[ "$#" -ge 1 ] || _usage_error "error: no device given"
require_device "$1"
device="$1"
shift
stages=(-1 32768)  # Part I.4(e): -1 first, then the chosen threshold
stage_args=()
parts=(suite harness)
suite_args=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        --gc-threshold | --part | --only | --repeat) [ "$#" -ge 2 ] || _usage_error "error: $1 needs a value" ;;
        *) _usage_error "error: unknown argument '$1'" ;;
    esac
    case "$1:$2" in
        --gc-threshold:-1 | --gc-threshold:32768) stages=("$2"); stage_args=(--gc-threshold "$2") ;;
        --part:suite | --part:harness) parts=("$2") ;;
        --only:* | --repeat:*) suite_args+=("$1" "$2") ;;
        *) _usage_error "error: $1 does not take '$2'" ;;
    esac
    shift 2
done
runs_part() { [[ " ${parts[*]} " == *" $1 "* ]]; }

# The suite's twins bind the product's ports 53 (Run 7's captive DNS) and 18080: one suite holds them at a
# time, and a second exits 1 here, before anything is built (CLAUDE.md). The one EXIT trap releases them.
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_port_lock.sh
trap port_lock_release_all EXIT
port_lock_take 53 scripts/run_digital_twin_ci.sh
port_lock_take 18080 scripts/run_digital_twin_ci.sh

export TZ=UTC  # same reasoning as scripts/test.sh's own identical export.

uv run --no-sync scripts/_archive_evidence.py --runner "digital_twin_ci_$device" "digital_twin_ci_logs/$device"

# The one Unix-port probe (scripts/_unix_port.sh): a missing or stale binary is rebuilt here, and the shared
# toolchain lock it takes is held while every twin below runs.
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_unix_port.sh
unix_port_ensure standard
micropython_bin="$(unix_port_bin standard)"

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

# Every device's module, wiring plan and API reference are generated fresh into build/generated_src/ (Part L.2).
echo "== Generating buildgen device modules + wiring plans into build/generated_src/"
uv run --no-sync scripts/_generate_sensortask_modules.py

# Port 53's UDP holders, printed before and after the twins: a socket there without SO_REUSEADDR fails the twins'
# captive DNS bind (DNSSRV E INIT), and only the runner itself can name its process.
port_53_holders() {
    echo "== UDP port 53 holders ($1):"
    if [ "$(id -u)" -eq 0 ]; then ss -H -uanp 'sport = :53' || true; else sudo -n ss -H -uanp 'sport = :53' || ss -H -uan 'sport = :53' || true; fi
}
port_53_holders "before the twins"

logs="digital_twin_ci_logs/$device"
worst=0
record() { if [ "$1" -gt "$worst" ]; then worst=$1; fi; }

if runs_part suite; then
    echo "== Running digital-twin automated CI suite (device: $device)"
    rc=0; uv run --no-sync scripts/_digital_twin_ci_suite.py --micropython-bin "$micropython_bin" --device "$device" --logs-dir "$logs" "${stage_args[@]}" "${suite_args[@]}" || rc=$?; record "$rc"

    # A device wiring a uart_link pair runs Run 3's link cell again with both ends on CRC16 (owner, 2026-09-30, paraphrase:
    # L2 builds the pair in both modes); the derived TOML must name crc16 exactly once per link and no other crc.
    if grep -q '^driver = "uart_link"' "devices/$device.toml"; then
        derived="$logs/crc16/$device.toml"
        mkdir -p "$(dirname "$derived")"
        sed '/^driver = "uart_link"$/a crc = "crc16"' "devices/$device.toml" > "$derived"
        links=$(grep -c '^driver = "uart_link"$' "$derived")
        if [ "$(grep -c '^crc = "crc16"$' "$derived")" -ne "$links" ] || [ "$(grep -c '^crc = ' "$derived")" -ne "$links" ]; then
            echo "error: $derived does not name crc16 exactly once per uart_link instance" >&2
            record 1
        else
            echo "== Running Run 3 on the CRC16-derived $derived"
            rc=0; uv run --no-sync scripts/_digital_twin_ci_suite.py --micropython-bin "$micropython_bin" --device "$device" --device-toml "$derived" --only 3 --logs-dir "$logs/crc16" "${stage_args[@]}" || rc=$?; record "$rc"
        fi
    fi
fi

if runs_part harness; then
    echo "== Running the host-side scenario harness (device: $device)"
    for stage in "${stages[@]}"; do
        rc=0; uv run --no-sync scripts/_digital_twin_scenarios.py --micropython-bin "$micropython_bin" --device "$device" --gc-threshold "$stage" --exclusive-port-53 --logs-dir "$logs/scenarios/gc_threshold_${stage/-/neg}" || rc=$?; record "$rc"
    done
fi
port_53_holders "after the twins"
exit "$worst"
