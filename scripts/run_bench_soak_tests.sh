#!/usr/bin/env bash
# Runs ONLY @pytest.mark.long_soak tests against a real board + WiFi bridge, for exactly one named
# duration tier - a deliberate, dedicated invocation (project owner's own explicit direction,
# 2026-09-04), never bundled into run_flash_hardware_suite.sh/run_bench_hardware_suite.sh (both of
# which explicitly exclude long_soak tests, always - see tests_hardware/conftest.py's own
# SOAK_TIER_SECONDS for the three tier durations).
#
# Usage: scripts/run_bench_soak_tests.sh --tier {short,mid,long} [extra pytest args]
#
# The one real, fixed ~12.4-day wait (time.ticks_ms()'s 2**30 rollover) is NOT a long_soak test and
# is NOT run by this script - it has its own separate --allow-multi-day-rollover-wait flag, deliberately
# never bundled with any of these tiers (see tests_hardware/flash/test_bus_electrical_timing.py's
# own test_ticks_ms_real_2pow30_rollover). Run that one directly, on purpose, if a session genuinely
# intends a multi-day wait: `uv run pytest tests_hardware/flash --allow-multi-day-rollover-wait -k
# test_ticks_ms_real_2pow30_rollover`.
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
