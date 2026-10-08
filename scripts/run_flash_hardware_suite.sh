#!/usr/bin/env bash
# L3: runs every lower level (scripts/_run_lower_levels.sh L3), then tests_hardware/flash/ on a real
# board through _require_clean_hardware_run.sh, with soak and the rollover wait excluded (each runs
# only through its own opt-in). Provisioning: tests_hardware/README.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

usage() {
    cat <<'USAGE'
Usage: scripts/run_flash_hardware_suite.sh [--skip-lower-levels] [pytest args]

Runs L0-L2 (scripts/_run_lower_levels.sh L3), then tests_hardware/flash/ against the board on USB.
  --skip-lower-levels  run tests_hardware/flash/ only; for iterative debugging, never reported clean (exit 4)
  -h, --help           this text
Other arguments go to pytest. Environment: MPREMOTE_DEVICE (the board's serial device; default: the
one MicroPython board found by its /dev/serial/by-id name), PICO_TOOLCHAIN_DIR (default ~/pico-toolchain).
USAGE
}

skip_lower=0
args=()
for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
        --skip-lower-levels) skip_lower=1 ;;
        *) args+=("$arg") ;;
    esac
done

levels=("--levels" "L0 L1 L2 L3")
if [ "$skip_lower" = 1 ]; then
    levels=("--levels" "L3" "--not-clean-reason" "lower levels skipped: L0 L1 L2")
elif ! scripts/_run_lower_levels.sh L3; then
    echo "error: a lower level failed - no board was touched" >&2
    exit 1
fi

scripts/_require_clean_hardware_run.sh --runner run_flash_hardware_suite "${levels[@]}" tests_hardware/flash -m "not long_soak and not multi_day_rollover" "${args[@]}"
