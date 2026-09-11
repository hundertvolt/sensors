#!/usr/bin/env bash
# Dedicated entry point for the digital twin's "full Unix-port integration" run -
# digital_twin/run_generic_integration.py, run against the real digital_twin buses under the real
# MicroPython Unix-port interpreter, for any real device (--device, default wozi;
# BUILD_CHAIN_PLAN.md's Session 6.2 - this script used to hardcode run_wozi_integration.py, now
# retired along with run_dev_integration.py in favor of this one generic entry point). Deliberately
# separate from scripts/test.sh: the twin needs its own MICROPYPATH
# ("build/generated_src:src:digital_twin:ext:frozen_modules:.frozen") that never carries a "tests"
# segment (digital_twin/README.md's own "never together" rule - see that doc's "Swapping the twin
# in for a Unix-port run" section), and run_generic_integration.py can run forever (no --duration -
# a real browser on this machine should be able to reach it), which would hang scripts/test.sh's
# own default tests/test_*.py glob loop if it were discovered there instead.
#
# "ext" is required here (unlike scripts/test.sh's own MICROPYPATH) because every generated
# sensortask_<device>.py unconditionally imports vendored ext/microdot.py - every tests/test_*.py
# file that needs it works around scripts/test.sh's own ext-less MICROPYPATH with its own per-file
# sys.path.insert(0, "ext") (see e.g. tests/test_sensortask_wozi.py's own comment), but this is the
# real standalone entry point, not a test file, so it needs the real fix here instead. Found by
# actually running this script standalone for the first time (a manual baseline-verification pass) -
# every prior verification of this file went through the test-harness sys.path.insert() workaround
# instead, which silently masked the gap.
#
# "build/generated_src" is required for the same reason scripts/test.sh needs it: no static
# src/sensortask_*.py exists any more (BUILD_CHAIN_PLAN.md's Session 6 finish criterion) - both the
# device's module and its wiring plan are generated fresh below, via buildgen, into this gitignored
# directory instead.
#
# Usage:
#   scripts/run_unix_port_integration.sh                        # just launch wozi + serve forever, no flags
#   scripts/run_unix_port_integration.sh --device dev            # same, for the dev bench variant
#   scripts/run_unix_port_integration.sh --soak                 # bounded automated soak run, then serves forever
#   scripts/run_unix_port_integration.sh --soak --duration 0    # same, but exits immediately after the soak
#   scripts/run_unix_port_integration.sh --fault sgp40:writeto  # manual fault-injection exploration
#   scripts/run_unix_port_integration.sh --host 0.0.0.0 --port 8080   # reachable from outside this machine
#
# --device (this script's own flag, one of wozi/dev/arzi/klkizi/grkizi/schlafzi - not forwarded)
# picks which devices/<device>.toml-generated module/wiring plan to boot. Every other flag forwards
# straight through to run_generic_integration.py's own parse_args() - see that module's own
# docstring for the full list (--host/--port/--fram-state-path/--seed/--fault/--wifi-outcome/
# --soak/--soak-cycles/--duration). No flags given just launches wozi and serves forever
# (RunConfig's own defaults - localhost:8080), the same "reachable/observable" half of owner
# decision 7 a real rp2040 boot would give you - the automated soak assertion is a specialty, opted
# into via --soak (or --soak-cycles, which implies it), not part of the plain launch path.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

export TZ=UTC  # same reasoning as scripts/test.sh's own identical export - see that script's own
# comment for the full time.mktime(time.gmtime()) non-UTC-host explanation.

device="wozi"
forward_args=()
while [ $# -gt 0 ]; do
    case "$1" in
        --device)
            device="$2"
            shift 2
            ;;
        *)
            forward_args+=("$1")
            shift
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

# run_generic_integration.py's own DNSServer (src/captive_dns.py) binds the real privileged port
# 53; a non-root dev environment can't bind that without either running as root or holding this
# specific capability on the interpreter binary. Applied fresh every invocation, not assumed to
# survive from a prior run - see scripts/run_digital_twin_ci.sh's identical block for why baking
# this into the toolchain build itself wouldn't be reliable (xattrs, where capabilities live,
# don't survive a cached/restored toolchain's tar round-trip).
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
