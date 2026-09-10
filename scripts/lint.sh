#!/usr/bin/env bash
# Ruff lint against every scope this project keeps fully clean: src/ (fully-reviewed code - see
# CLAUDE.md), tests/ (their unit tests), digital_twin/ (the hardware simulator, SPECIFICATION.md
# Part A.10), and the whole host-side build chain - buildgen/ (the device-TOML generator,
# BUILD_CHAIN_PLAN.md's Session 3), scripts/ and toolchain/ (the dev-tooling/build-environment
# scripts) and tests_scripts/ (their pytest suite). Lint only: `ruff format` is deliberately not
# part of this toolchain, see pyproject.toml's [tool.ruff] comment. Assumes ruff is already
# installed and on PATH.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

ruff check src tests digital_twin buildgen scripts toolchain tests_scripts
