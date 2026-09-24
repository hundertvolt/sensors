#!/usr/bin/env bash
# Runs the manual real-hardware tier (tests_hardware/manual/, SPECIFICATION.md Part E.6): interactive,
# never invoked by pytest, structurally separate from the automated suites.
# Flags (--list, --only <name>) and prerequisites: tests_hardware/README.md.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

uv run python tests_hardware/manual/__main__.py "$@"
