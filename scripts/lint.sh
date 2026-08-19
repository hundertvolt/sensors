#!/usr/bin/env bash
# Ruff lint against improved-quality/ (WIP refactor target), src/ (fully-reviewed files moved out
# of improved-quality/ once done - see CLAUDE.md), tests/ (their unit tests), and digital_twin/
# (the hardware simulator, SPECIFICATION.md Part A.10; unlike improved-quality/, this scope is
# expected to stay fully clean, same as src/). Lint only: `ruff format` is deliberately not part
# of this toolchain, see pyproject.toml's [tool.ruff] comment. Assumes ruff is already installed
# and on PATH.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

ruff check improved-quality src tests digital_twin
