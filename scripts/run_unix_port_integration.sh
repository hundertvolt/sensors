#!/usr/bin/env bash
# Manual twin launch of one device: digital_twin/run_generic_integration.py under the real Unix port, separate from
# scripts/test.sh (owner, 2026-08-13). With no further flags it serves on localhost:8080 forever (owner, 2026-08-13:
# browser-reachable, escalation watchable), its chip state and config persisting in digital_twin/.
#
# Its MICROPYPATH is the twin layout of scripts/micropypath.toml: ext/ because every generated sensortask_<device>.py
# imports vendored ext/microdot.py, and no tests/ (digital_twin/README.md's "never together" rule).
#
# Usage: scripts/run_unix_port_integration.sh --device <name> [flags forwarded to the twin]
#   e.g. --fault sgp40:writeto, --host 0.0.0.0 --port 8080 (reachable from outside).
#
# --device is this script's own required flag (a devices/*.toml stem but the zz_test_ fixtures, not forwarded);
# every other flag goes to run_generic_integration.py, whose --help lists them. The host-side soak is
# scripts/_digital_twin_ci_suite.py's Run 11 (SPECIFICATION.md "Driver/DUT process separation").
set -euo pipefail
usage_line="Usage: scripts/run_unix_port_integration.sh --device <name> [flags forwarded to the twin]"
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    cat <<EOF
$usage_line
Launches digital_twin/run_generic_integration.py for one device, a devices/<name>.toml, under the
real Unix port; with no further flags it serves on localhost:8080 until stopped, its chip state and
config kept in digital_twin/ across runs. Every flag but --device goes to run_generic_integration.py
(its own --help lists them, the state paths among them). It fails at once while another suite holds port 53.

Environment:
  PICO_TOOLCHAIN_DIR   toolchain cache (default: ~/pico-toolchain)
  SKIP_APT=1           skip the system-package step of a toolchain build (default: 0)
EOF
    exit 0
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."

export TZ=UTC  # same reasoning as scripts/test.sh's own identical export, which has the account.

# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_devices.sh
_usage_error() {
    local devices
    devices="$(derived_devices)" || devices=""
    printf '%s\n%s\nvalid devices: %s\n' "$1" "$usage_line" "${devices//$'\n'/ }" >&2
    exit 2
}

device=""
device_given=0
forward_args=()
while [ $# -gt 0 ]; do
    case "$1" in
        --device)
            [ $# -ge 2 ] || _usage_error "error: --device needs a device name"
            device_given=1
            device="$2"
            shift 2
            ;;
        *)
            forward_args+=("$1")
            shift
            ;;
    esac
done
[ "$device_given" = "1" ] || _usage_error "error: --device is required"
require_device "$device"

# The twin's captive DNS server binds the product's port 53: one suite holds it at a time, and a second
# exits 1 here, before anything is built (CLAUDE.md). The one EXIT trap releases it.
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_port_lock.sh
trap port_lock_release_all EXIT
port_lock_take 53 scripts/run_unix_port_integration.sh

# The one Unix-port probe (scripts/_unix_port.sh): a missing or stale binary is rebuilt here, and the shared
# toolchain lock it takes is held while the twin serves.
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_unix_port.sh
unix_port_ensure standard
micropython_bin="$(unix_port_bin standard)"

# The twin's captive DNS server binds the real privileged port 53, which a non-root environment cannot do
# without this capability on the interpreter binary. Granted fresh every invocation, for the reason
# scripts/run_digital_twin_ci.sh's identical block gives.
echo "== Granting CAP_NET_BIND_SERVICE to $micropython_bin (needed for the real port-53 DNS server)"
if [ "$(id -u)" -eq 0 ]; then
    setcap 'cap_net_bind_service=+ep' "$micropython_bin"
else
    sudo setcap 'cap_net_bind_service=+ep' "$micropython_bin"
fi

site="build/generated_html/$device"
echo "== Building the real $device website into $site/frozen_html.py"
scripts/build_website.sh "$device" "$site/frozen_html.py"

echo "== Generating buildgen device modules + wiring plans into build/generated_src/"
uv run --no-sync scripts/_generate_sensortask_modules.py

module="sensortask_${device}"
wiring_plan="build/generated_src/${module}_wiring_plan.json"
twin_path="$(micropypath twin)"
# The device's own built site in place of frozen_modules/, so scripts/test.sh's frozen_modules/ is never touched.
twin_path="${twin_path/frozen_modules/$site}"
echo "== Running digital_twin/run_generic_integration.py (device: $device)"
MICROPYPATH="$twin_path" "$micropython_bin" digital_twin/run_generic_integration.py --module "$module" --wiring-plan "$wiring_plan" --device "$device" "${forward_args[@]}"
