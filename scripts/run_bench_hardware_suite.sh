#!/usr/bin/env bash
# L4: lower levels (scripts/_run_lower_levels.sh L4), then L3 as its own clean step, then
# tests_hardware/bench/ against a real board and WiFi bridge, with soak and the rollover wait
# excluded (each runs only through its own opt-in). Provisioning: tests_hardware/README.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

usage() {
    cat <<'USAGE'
Usage: scripts/run_bench_hardware_suite.sh [--skip-lower-levels] [--scope NAME] [pytest args]

Runs L0-L2 (scripts/_run_lower_levels.sh L4), then tests_hardware/flash/ (L3) as its own step, which
must pass before tests_hardware/bench/ (L4) runs; each step prints its summary block.
  --skip-lower-levels  skip L0-L2; for iterative debugging, never reported clean (exit 4)
  --scope NAME         run only the flash and bench tests tests_hardware/run_scopes.py lists for NAME, the
                       ones one change reaches; never reported clean (exit 4), never with test paths, and
                       never with the global --allow-persistence-writes (name the groups instead:
                       --allow-persistence-writes-to=GROUP)
  -h, --help           this text
Other arguments go to pytest. Test paths (arguments starting with tests_hardware/) go to the bench
step only and replace its tests_hardware/bench; every other argument goes to both steps (an option
whose value starts with tests_hardware/ is written --option=VALUE). Environment: MPREMOTE_DEVICE (the
board's serial device; default: the one MicroPython board found by its /dev/serial/by-id name),
BENCH_AP_PASSWORD (default: read from the bench bridge), PICO_TOOLCHAIN_DIR (default ~/pico-toolchain).
USAGE
}

skip_lower=0
scope=""
args=()
paths=()
while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --skip-lower-levels) skip_lower=1 ;;
        --scope)
            [ $# -ge 2 ] || { echo "error: --scope needs a name" >&2; exit 2; }
            scope="$2"
            shift ;;
        --scope=*) scope="${1#--scope=}" ;;
        tests_hardware/*) paths+=("$1") ;;
        *) args+=("$1") ;;
    esac
    shift
done
[ "${#paths[@]}" -gt 0 ] || [ -n "$scope" ] || paths=(tests_hardware/bench)

# A scope is resolved before any level runs, so a bad name or a forbidden argument costs nothing.
flash_paths=(tests_hardware/flash)
runner="run_bench_hardware_suite"
scope_label=""
reasons=()
if [ -n "$scope" ]; then
    if [ "${#paths[@]}" -gt 0 ]; then
        echo "error: --scope $scope selects its own tests; give it no test paths" >&2
        exit 2
    fi
    listed_flash="$(python3 tests_hardware/run_scopes.py "$scope" flash)" || exit 2
    listed_bench="$(python3 tests_hardware/run_scopes.py "$scope" bench)" || exit 2
    writes="$(python3 tests_hardware/run_scopes.py "$scope" writes | paste -sd, -)"
    for arg in "${args[@]}"; do
        if [ "$arg" = "--allow-persistence-writes" ]; then
            echo "error: a scoped run never takes the global --allow-persistence-writes; pass --allow-persistence-writes-to=$writes, the groups scope $scope writes" >&2
            exit 2
        fi
    done
    mapfile -t flash_paths <<< "$listed_flash"
    mapfile -t paths <<< "$listed_bench"
    runner="run_bench_hardware_suite_scope_${scope}"
    scope_label=", scope $scope"
    reasons+=("scope $scope: ${#flash_paths[@]} flash and ${#paths[@]} bench selections a change reaches, not the whole of either tier")
fi

level_text="L0 L1 L2 L3 L4"
if [ "$skip_lower" = 1 ]; then
    level_text="L3 L4"
    reasons=("lower levels skipped: L0 L1 L2" "${reasons[@]}")
elif ! scripts/_run_lower_levels.sh L4; then
    echo "error: a lower level failed - no board was touched" >&2
    exit 1
fi
levels=("--levels" "$level_text$scope_label")
if [ "${#reasons[@]}" -gt 0 ]; then
    reason="${reasons[0]}"
    for more in "${reasons[@]:1}"; do
        reason+="; $more"
    done
    levels+=("--not-clean-reason" "$reason")
fi

floor="not long_soak and not multi_day_rollover"
# The flash step has its own runner name, so its evidence keeps its own newest three.
scripts/_require_clean_hardware_run.sh --runner "${runner}_flash_step" --levels "L3$scope_label" "${flash_paths[@]}" -m "$floor" "${args[@]}"
scripts/_require_clean_hardware_run.sh --runner "$runner" "${levels[@]}" "${paths[@]}" -m "$floor" "${args[@]}"
