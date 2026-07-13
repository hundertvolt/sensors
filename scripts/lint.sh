#!/usr/bin/env bash
# Ruff lint against improved-quality/ - the only directory this tooling checks right now (see
# pyproject.toml). Lint only: `ruff format` is deliberately not part of this toolchain, see
# pyproject.toml's [tool.ruff] comment. Assumes ruff is already installed and on PATH.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

ruff check improved-quality
