#!/usr/bin/env bash
# Runs only @pytest.mark.soak_duration tests at one named duration - an opt-in on top of the bench
# tier (owner, 2026-09-26), a dedicated invocation (owner's direction, 2026-09-04) the two general
# suite runners never bundle. Durations: tests_hardware/soak_durations.py's SOAK_DURATION_SECONDS.
#
# The tick-rollover round is not a soak_duration test and no duration here runs it; it has its own
# --allow-multi-day-rollover flag, to be invoked directly and on purpose (tests_hardware/README.md).
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
Other arguments go to pytest. Environment: MPREMOTE_DEVICE (the board's serial device; default: the
one MicroPython board found by its /dev/serial/by-id name), BENCH_AP_PASSWORD (default: read from the
bench bridge).
USAGE
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    usage
    exit 0
fi
if [ "${1:-}" != "--duration" ] || [ -z "${2:-}" ]; then
    usage >&2
    exit 2
fi
duration="$2"
shift 2

scripts/_require_clean_hardware_run.sh --runner run_bench_soak_tests --levels "soak duration $duration (not a level)" tests_hardware/flash tests_hardware/bench -m soak_duration --soak-duration "$duration" "$@"
