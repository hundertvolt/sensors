#!/usr/bin/env bash
# Ruff lint against src/ (fully-reviewed code - see CLAUDE.md), tests/ (their unit tests),
# digital_twin/ (the hardware simulator, SPECIFICATION.md Part A.10), and buildgen/ (the
# device-TOML generator, BUILD_CHAIN_PLAN.md's Session 3 - fresh code, starts under the full
# quality bar immediately per that doc's "Build/generator script quality bar" #10) - all four
# expected to stay fully clean. Lint only: `ruff format` is deliberately not part of this
# toolchain, see pyproject.toml's [tool.ruff] comment. Assumes ruff is already installed and on
# PATH.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

ruff check src tests digital_twin buildgen
