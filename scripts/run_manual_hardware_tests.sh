#!/usr/bin/env bash
# Runs the manual real-hardware test tier (tests_hardware/manual/, HARDWARE_TEST_PLAN.md §7) -
# structurally separate from the automated suites above, never invoked by pytest. Interactive: prints
# instructions and waits for operator confirmation. Pass --list to see every registered test without
# running any, or --only <name> to run just one.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

uv run python tests_hardware/manual/__main__.py "$@"
