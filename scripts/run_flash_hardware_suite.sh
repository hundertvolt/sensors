#!/usr/bin/env bash
# Runs tests_hardware/flash/ against a real board over mpremote (HARDWARE_TEST_PLAN.md §6.3) - see
# tests_hardware/README.md for provisioning. Passes through any extra pytest args (-k, -m, --only, etc).
# Requires a genuinely clean result (no unexpected skips, no failures) - see
# _require_clean_hardware_run.sh's own comment for why a plain exit-code check isn't enough here.
# Always excludes long_soak/multi_day_rollover tests, unconditionally - those need their own
# deliberate, dedicated invocation (scripts/run_bench_soak_tests.sh, or a direct
# --allow-multi-day-rollover-wait run), never bundled into this general suite run even if a caller
# passes --soak-tier/--allow-multi-day-rollover-wait by mistake.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

scripts/_require_clean_hardware_run.sh tests_hardware/flash -m "not long_soak and not multi_day_rollover" "$@"
