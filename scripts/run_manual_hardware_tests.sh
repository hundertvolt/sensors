#!/usr/bin/env bash
# Runs the manual execution mode of L3/L4 (tests_hardware/manual/, SPECIFICATION.md Part E.6):
# interactive, never invoked by pytest, structurally separate from the automated runners.
# Flags (--list, --only <name>) and prerequisites: tests_hardware/README.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    cat <<'USAGE'
Usage: scripts/run_manual_hardware_tests.sh [--list | --only <name>]

Runs every [MANUAL] test of tests_hardware/manual/ interactively, ending with the summary block.
Flags --list, --only <name>: see tests_hardware/README.md. Environment: MPREMOTE_DEVICE (the board's
serial device; default: the one MicroPython board found by its /dev/serial/by-id name).
USAGE
    exit 0
fi

uv run python tests_hardware/manual/__main__.py "$@"
