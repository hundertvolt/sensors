#!/usr/bin/env bash
# Runs only @pytest.mark.soak_duration tests at one named duration - an opt-in on top of the bench tier (owner,
# 2026-09-26) that the general runners never bundle (owner's direction, 2026-09-04). Durations:
# tests_hardware/soak_durations.py; the tick-rollover round is not a soak: scripts/run_bench_rollover_test.sh.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

usage() {
    cat <<'USAGE'
Usage: scripts/run_bench_soak_tests.sh --duration {short,mid,long} [pytest args]

Runs only the soak_duration tests of tests_hardware/flash/ and tests_hardware/bench/ for one named
duration, on top of a clean bench run: it runs no lower level itself. Durations:
tests_hardware/soak_durations.py.
  --duration NAME  short, mid or long (required)
  -h, --help       this text
Other arguments go to pytest; a -m you pass narrows the selection to the soak_duration tests matching
it. Environment: MPREMOTE_DEVICE (the board's serial device; default: the one MicroPython board found
by its /dev/serial/by-id name), BENCH_AP_PASSWORD (default: read from the bench bridge).
USAGE
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    usage
    exit 0
fi
if [ "${1:-}" != "--duration" ]; then
    echo "error: the first argument must be --duration NAME" >&2
    usage >&2
    exit 2
fi
if [ -z "${2:-}" ]; then
    echo "error: --duration needs a duration name" >&2
    usage >&2
    exit 2
fi
duration="$2"
shift 2
# The names are soak_durations.py's own, read rather than copied: an unknown one fails here, before the wrapper.
names="$(uv run --no-sync python -c 'import sys; sys.path.insert(0, "tests_hardware"); from soak_durations import SOAK_DURATION_SECONDS; print(" ".join(sorted(SOAK_DURATION_SECONDS)))')"
read -r -a durations <<<"$names"
known=0
for name in "${durations[@]}"; do
    [ "$name" != "$duration" ] || known=1
done
if [ "$known" = 0 ]; then
    echo "error: unknown duration '$duration' - valid durations: ${durations[*]}" >&2
    usage >&2
    exit 2
fi

scripts/_require_clean_hardware_run.sh --runner run_bench_soak_tests --levels "soak duration $duration (not a level)" --marker-floor "soak_duration" tests_hardware/flash tests_hardware/bench --soak-duration "$duration" "$@"
