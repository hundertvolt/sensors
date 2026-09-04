#!/usr/bin/env bash
# Runs tests_hardware/flash/ + tests_hardware/bench/ against a real board + WiFi bridge (bench is a
# strict superset of flash - HARDWARE_TEST_PLAN.md §3). See tests_hardware/README.md for
# provisioning. Passes through any extra pytest args (-k, -m, --only, etc).
# Requires a genuinely clean result (no unexpected skips, no failures) - see
# _require_clean_hardware_run.sh's own comment for why a plain exit-code check isn't enough here.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

scripts/_require_clean_hardware_run.sh tests_hardware/flash tests_hardware/bench "$@"
