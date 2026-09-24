#!/usr/bin/env bash
# Runs ONLY @pytest.mark.long_soak tests against a real board + WiFi bridge, at one named duration
# tier - a deliberate, dedicated invocation (owner's direction, 2026-09-04) that the two general
# suite runners never bundle. Tier durations: tests_hardware/conftest.py's SOAK_TIER_SECONDS.
#
# Usage: scripts/run_bench_soak_tests.sh --tier {short,mid,long} [extra pytest args]
#
# The ~12.4-day ticks_ms() rollover wait is NOT a long_soak test and no tier here runs it; it has
# its own --allow-multi-day-rollover-wait flag, to be invoked directly and on purpose
# (tests_hardware/README.md has the command).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "${1:-}" != "--tier" ] || [ -z "${2:-}" ]; then
    echo "Usage: $0 --tier {short,mid,long} [extra pytest args]" >&2
    echo "See tests_hardware/conftest.py's SOAK_TIER_SECONDS for what each tier actually runs for." >&2
    exit 2
fi
tier="$2"
shift 2

scripts/_require_clean_hardware_run.sh tests_hardware/flash tests_hardware/bench -m long_soak --soak-tier "$tier" "$@"
