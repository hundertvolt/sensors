#!/usr/bin/env bash
# Every non-type lint pass in one place: ruff over src/ (fully-reviewed code - see CLAUDE.md),
# tests/ (their unit tests), and digital_twin/ (the hardware simulator, SPECIFICATION.md Part A.10),
# plus shellcheck over scripts/ and actionlint over the GitHub Actions workflows. All expected to
# stay fully clean. Lint only: `ruff format` is deliberately not part of this toolchain, see
# pyproject.toml's [tool.ruff] comment. Assumes `uv sync` has been run and its venv is active -
# ruff/shellcheck/actionlint all install from pyproject.toml's [dependency-groups].
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

status=0

ruff check src tests digital_twin || status=1

# scripts/ only, deliberately NOT the four legacy build-*.sh at the repo root: those belong to the
# same pre-refactor generation as python//modules/ and are out of lint scope by the same standing
# decision (they carry 28 findings of their own, including no shebang at all - see BACKLOG.md).
shellcheck scripts/*.sh || status=1

# Catches workflow expression/context typos that otherwise only surface as a broken CI run.
actionlint || status=1

exit "$status"
