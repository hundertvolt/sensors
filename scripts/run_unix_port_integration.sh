#!/usr/bin/env bash
# Dedicated entry point for the digital twin's full Unix-port integration run:
# digital_twin/run_generic_integration.py against the real twin buses under the real MicroPython
# Unix-port interpreter, for any real device (--device; SPECIFICATION.md Part L.4).
#
# Deliberately separate from scripts/test.sh (owner, 2026-08-13): the twin needs its own MICROPYPATH
# with no "tests" segment (digital_twin/README.md's "never together" rule), and this run can serve
# forever with no --duration, which would hang that script's own test-file loop.
#
# That path needs "ext", unlike scripts/test.sh's, because every generated sensortask_<device>.py
# imports vendored ext/microdot.py - a test file works around the ext-less path with its own
# sys.path.insert, the real entry point needs the real fix.
#
# "build/generated_src" is there because no static src/sensortask_*.py exists any more (Part L.2):
# both the module and its wiring plan are generated fresh below.
#
# Usage: scripts/run_unix_port_integration.sh --device <name> [flags forwarded to the twin]
#   e.g. --fault sgp40:writeto, --host 0.0.0.0 --port 8080 (reachable from outside).
#
# --device is this script's own required flag (a devices/*.toml stem but the zz_test_ fixtures, not
# forwarded) and picks which generated module/wiring plan to boot; every other flag goes straight
# through to run_generic_integration.py's parse_args(), whose docstring has the full list.
#
# Without --device it prints the usage and the valid device names; with no further flags the device
# serves on localhost:8080 forever (owner, 2026-08-13: browser-reachable, escalation watchable), its chip
# state and config kept in digital_twin/ across runs (owner, 2026-08-13: "a persistent file inside digital_twin/").
#
# No --soak flag: the HTTP+memory-trend soak check is host-side, scripts/_digital_twin_ci_suite.py's
# Run 11 (SPECIFICATION.md "Driver/DUT process separation").
set -euo pipefail
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    cat <<'EOF'
Usage: scripts/run_unix_port_integration.sh --device <name> [flags forwarded to the twin]
Launches digital_twin/run_generic_integration.py for one device, a devices/<name>.toml, under the
real Unix port; with no further flags it serves on localhost:8080 until stopped, its chip state and
config kept in digital_twin/ across runs. Every flag but --device goes to run_generic_integration.py
(its own --help lists them, the state paths among them).

Environment:
  PICO_TOOLCHAIN_DIR   toolchain cache (default: ~/pico-toolchain)
  SKIP_APT=1           skip the system-package step of a toolchain build (default: 0)
EOF
    exit 0
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."

export TZ=UTC  # same reasoning as scripts/test.sh's own identical export, which has the account.

usage_line="Usage: scripts/run_unix_port_integration.sh --device <name> [flags forwarded to the twin]"
devices=()
for toml in devices/*.toml; do
    name="$(basename "$toml" .toml)"
    if [[ "$name" != zz_test_* ]] && [ -f "$toml" ]; then
        devices+=("$name")
    fi
done
_usage_error() {
    printf '%s\n%s\nvalid devices: %s\n' "$1" "$usage_line" "${devices[*]-}" >&2
    exit 2
}

device=""
device_given=0
forward_args=()
while [ $# -gt 0 ]; do
    case "$1" in
        --device)
            device_given=1
            device="${2:-}"
            shift $(($# > 1 ? 2 : 1))
            ;;
        *)
            forward_args+=("$1")
            shift
            ;;
    esac
done
if [ "$device_given" = "0" ]; then
    _usage_error "error: --device is required"
elif [ -z "$device" ]; then
    _usage_error "error: --device needs a device name"
elif [[ " ${devices[*]-} " != *" $device "* ]]; then
    _usage_error "error: unknown device '$device'"
fi

# The twin's captive DNS server binds the product's port 53: one suite holds it at a time, and a second
# exits 1 here, before anything is built (CLAUDE.md). The EXIT trap releases it.
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_port_lock.sh
trap port_lock_release_all EXIT
port_lock_take 53 scripts/run_unix_port_integration.sh

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

# The twin's CaptiveDNS binds the real privileged port 53, which a non-root environment cannot do
# without this capability on the interpreter binary. Granted fresh every invocation, for the reason
# scripts/run_digital_twin_ci.sh's identical block gives.
echo "== Granting CAP_NET_BIND_SERVICE to $micropython_bin (needed for the real port-53 DNS server)"
if [ "$(id -u)" -eq 0 ]; then
    setcap 'cap_net_bind_service=+ep' "$micropython_bin"
else
    sudo setcap 'cap_net_bind_service=+ep' "$micropython_bin"
fi

echo "== Building the real $device website into frozen_modules/frozen_html.py"
scripts/build_website.sh "$device"

echo "== Generating buildgen device modules + wiring plans into build/generated_src/"
uv run scripts/_generate_sensortask_modules.py

module="sensortask_${device}"
wiring_plan="build/generated_src/${module}_wiring_plan.json"
echo "== Running digital_twin/run_generic_integration.py (device: $device)"
MICROPYPATH="build/generated_src:src:digital_twin:ext:frozen_modules:.frozen" "$micropython_bin" digital_twin/run_generic_integration.py --module "$module" --wiring-plan "$wiring_plan" --device "$device" "${forward_args[@]}"
