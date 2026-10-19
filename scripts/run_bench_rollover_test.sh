#!/usr/bin/env bash
# Builds the bench board's tick-offset test image (ticks wrap about 15 minutes after boot; owner, 2026-10-01) and runs
# only @pytest.mark.multi_day_rollover tests on it for about two hours, on top of a clean bench run. Never a soak,
# never bundled with a suite runner (owner, 2026-09-26); one flash cycle.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    cat <<'USAGE'
Usage: scripts/run_bench_rollover_test.sh [pytest args]

Builds the bench board's tick-offset test image (build/firmware-<device>-tickoffset.uf2), then runs only
the multi_day_rollover tests of tests_hardware/bench/ on it, on top of a clean bench run: it runs no
lower level itself. It builds and flashes the tick-offset test image, then about two hours of polls:
start it detached (tests_hardware/README.md).
Other arguments go to pytest; a -m you pass narrows the selection. Environment: BENCH_DEVICE (or
--bench-device NAME; default: the one devices/*.toml with [device] bench = true), MPREMOTE_DEVICE (the
board's serial device; default: the one MicroPython board found by its /dev/serial/by-id name),
BENCH_AP_PASSWORD (default: read from the bench bridge), PICO_TOOLCHAIN_DIR (default ~/pico-toolchain).
USAGE
    exit 0
fi

# The image is built for the board the session drives: a --bench-device passed for pytest names it here too.
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
    case "${args[i]}" in
        --bench-device) [ "$((i + 1))" -ge "${#args[@]}" ] || export BENCH_DEVICE="${args[i + 1]}" ;;
        --bench-device=*) export BENCH_DEVICE="${args[i]#--bench-device=}" ;;
    esac
done
# One retried sync before the image is built; every uv run after it is --no-sync.
if ! scripts/uv_sync_retried.sh; then
    echo "error: the retried uv sync failed - its output above names the cause; nothing reached the board" >&2
    exit 1
fi
# The bench device as the hardware tiers resolve it: an unknown, missing or doubled one fails here, naming why.
device="$(uv run --no-sync python -c 'import sys
sys.path.insert(0, "tests_hardware")
import harness
try:
    print(harness.bench_device())
except harness.HardwareNotAvailableError as e:
    sys.exit(f"error: {e}")')"
image="build/firmware-$device-tickoffset.uf2"
if ! uv run --no-sync scripts/build_firmware.py "$device" --tick-offset-test --output "$image"; then
    echo "error: the tick-offset test image for $device did not build - nothing reached the board" >&2
    exit 1
fi

scripts/_require_clean_hardware_run.sh --runner run_bench_rollover_test --levels "rollover (not a level)" --marker-floor "multi_day_rollover" tests_hardware/bench --allow-multi-day-rollover --allow-flash-cycle --rollover-image "$image" "$@"
