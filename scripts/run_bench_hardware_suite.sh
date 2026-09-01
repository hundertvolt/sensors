#!/usr/bin/env bash
# Runs tests_hardware/flash/ + tests_hardware/bench/ against a real board + WiFi bridge (bench is a
# strict superset of flash - HARDWARE_TEST_PLAN.md §3). See tests_hardware/README.md for
# provisioning. Passes through any extra pytest args (-k, -m, --only, etc).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

uv run pytest tests_hardware/flash tests_hardware/bench "$@"
