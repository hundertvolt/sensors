#!/usr/bin/env bash
# L4: lower levels (scripts/_run_lower_levels.sh L4), then L3 as its own clean step, then
# tests_hardware/bench/ against a real board and WiFi bridge, with soak and the rollover wait
# excluded (each runs only through its own opt-in). Provisioning: tests_hardware/README.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

usage() {
    cat <<'USAGE'
Usage: scripts/run_bench_hardware_suite.sh [--skip-lower-levels] [pytest args]

Runs L0-L2 (scripts/_run_lower_levels.sh L4), then tests_hardware/flash/ (L3) as its own step, which
must pass before tests_hardware/bench/ (L4) runs; each step prints its summary block.
  --skip-lower-levels  skip L0-L2; for iterative debugging, never reported clean (exit 4)
  -h, --help           this text
Other arguments go to pytest. Test paths (arguments starting with tests_hardware/) go to the bench
step only and replace its tests_hardware/bench; every other argument goes to both steps (an option
whose value starts with tests_hardware/ is written --option=VALUE). Environment: MPREMOTE_DEVICE (the
board's serial device; default: the one MicroPython board found by its /dev/serial/by-id name),
BENCH_AP_PASSWORD (default: read from the bench bridge), PICO_TOOLCHAIN_DIR (default ~/pico-toolchain).
USAGE
}

skip_lower=0
args=()
paths=()
for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
        --skip-lower-levels) skip_lower=1 ;;
        tests_hardware/*) paths+=("$arg") ;;
        *) args+=("$arg") ;;
    esac
done
[ "${#paths[@]}" -gt 0 ] || paths=(tests_hardware/bench)

levels=("--levels" "L0 L1 L2 L3 L4")
if [ "$skip_lower" = 1 ]; then
    levels=("--levels" "L3 L4" "--not-clean-reason" "lower levels skipped: L0 L1 L2")
elif ! scripts/_run_lower_levels.sh L4; then
    echo "error: a lower level failed - no board was touched" >&2
    exit 1
fi

floor="not long_soak and not multi_day_rollover"
# The flash step has its own runner name, so its evidence keeps its own newest three.
scripts/_require_clean_hardware_run.sh --runner run_bench_hardware_suite_flash_step --levels "L3" tests_hardware/flash -m "$floor" "${args[@]}"
scripts/_require_clean_hardware_run.sh --runner run_bench_hardware_suite "${levels[@]}" "${paths[@]}" -m "$floor" "${args[@]}"
