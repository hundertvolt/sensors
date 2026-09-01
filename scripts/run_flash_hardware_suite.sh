#!/usr/bin/env bash
# Runs tests_hardware/flash/ against a real board over mpremote (HARDWARE_TEST_PLAN.md §6.3) - see
# tests_hardware/README.md for provisioning. Passes through any extra pytest args (-k, -m, --only, etc).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

uv run pytest tests_hardware/flash "$@"
