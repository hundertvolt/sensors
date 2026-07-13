#!/usr/bin/env bash
# Runs mypy against improved-quality/ (see scripts/lint.sh / pyproject.toml for why that's the
# only directory in scope right now). Assumes mypy is already installed and on PATH; uses `uv`
# (assumed on PATH, same as toolchain/setup_toolchain.py) only to populate typings/, an isolated
# directory holding just the MicroPython stub package - see pyproject.toml's [tool.mypy] comments
# for why that has to stay separate from mypy's own venv.
#
# Bump the version pin below when toolchain/versions.toml's [micropython] ref changes.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

uv pip install --quiet --target typings "micropython-rp2-rpi_pico_w-stubs==1.28.*"

mypy
