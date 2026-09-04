#!/usr/bin/env bash
# Runs tests_hardware/flash/ against a real board over mpremote (HARDWARE_TEST_PLAN.md §6.3) - see
# tests_hardware/README.md for provisioning. Passes through any extra pytest args (-k, -m, --only, etc).
# Requires a genuinely clean result (no unexpected skips, no failures) - see
# _require_clean_hardware_run.sh's own comment for why a plain exit-code check isn't enough here.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

scripts/_require_clean_hardware_run.sh tests_hardware/flash "$@"
