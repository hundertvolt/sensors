#!/usr/bin/env bash
# Ruff lint against improved-quality/ (WIP refactor target) and src/ (fully-reviewed files moved
# out of improved-quality/ once done - see CLAUDE.md) and tests/ (their unit tests). Lint only:
# `ruff format` is deliberately not part of this toolchain, see pyproject.toml's [tool.ruff]
# comment. Assumes ruff is already installed and on PATH.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

ruff check improved-quality src tests
