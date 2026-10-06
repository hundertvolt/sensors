#!/usr/bin/env bash
# Runs ONLY @pytest.mark.long_soak tests at one named duration tier - an opt-in on top of the bench
# tier (owner, 2026-09-26), a dedicated invocation (owner's direction, 2026-09-04) the two general
# suite runners never bundle. Tier durations: tests_hardware/soak_tiers.py's SOAK_TIER_SECONDS.
#
# The ~12.4-day ticks_ms() rollover wait is NOT a long_soak test and no tier here runs it; it has
# its own --allow-multi-day-rollover-wait flag, to be invoked directly and on purpose
# (tests_hardware/README.md has the command).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

usage() {
    cat <<'USAGE'
Usage: scripts/run_bench_soak_tests.sh --tier {short,mid,long} [pytest args]

Runs only the long_soak tests of tests_hardware/flash/ and tests_hardware/bench/ at one tier, on top
of a clean bench run: it runs no lower level itself. Tier durations: tests_hardware/soak_tiers.py.
  --tier TIER  short, mid or long (required)
  -h, --help   this text
Other arguments go to pytest. Environment: MPREMOTE_DEVICE (the board's serial device; default: the
one MicroPython board found by its /dev/serial/by-id name), BENCH_AP_PASSWORD (default: read from the
bench bridge).
USAGE
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    usage
    exit 0
fi
if [ "${1:-}" != "--tier" ] || [ -z "${2:-}" ]; then
    usage >&2
    exit 2
fi
tier="$2"
shift 2

scripts/_require_clean_hardware_run.sh --runner run_bench_soak_tests --levels "soak duration $tier (not a level)" tests_hardware/flash tests_hardware/bench -m long_soak --soak-tier "$tier" "$@"
