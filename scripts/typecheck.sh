#!/usr/bin/env bash
# Runs mypy against improved-quality/ (see scripts/lint.sh / pyproject.toml for why that's the
# only directory in scope right now). Assumes mypy is already installed and on PATH; uses `uv`
# (assumed on PATH, same as toolchain/setup_toolchain.py) only to populate typings/, an isolated
# directory holding just the MicroPython stub package - see pyproject.toml's [tool.mypy] comments
# for why that has to stay separate from mypy's own venv.
#
# The MicroPython firmware version lives in exactly one place: toolchain/versions.toml's
# [micropython] ref. The stub package version below is derived from it, not a separate hand-kept
# pin - see derive_firmware_version() below. Requires python3 >= 3.11 (tomllib), same requirement
# toolchain/setup_toolchain.py already has for parsing this same file.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

derive_firmware_version() {
    python3 <<'PYEOF'
import re
import sys
import tomllib

versions_path = "toolchain/versions.toml"

try:
    with open(versions_path, "rb") as f:
        versions = tomllib.load(f)
except OSError as e:
    print(f"error: couldn't read {versions_path}: {e}", file=sys.stderr)
    sys.exit(1)
except tomllib.TOMLDecodeError as e:
    print(f"error: {versions_path} isn't valid TOML: {e}", file=sys.stderr)
    sys.exit(1)

try:
    ref = versions["micropython"]["ref"]
except KeyError:
    print(f"error: {versions_path} has no [micropython] ref key", file=sys.stderr)
    sys.exit(1)

match = re.fullmatch(r"v?(\d+\.\d+\.\d+)", ref)
if not match:
    print(
        f"error: {versions_path}'s micropython ref {ref!r} isn't a plain vX.Y.Z tag - can't "
        "derive a matching MicroPython stub package version from it automatically",
        file=sys.stderr,
    )
    sys.exit(1)

print(match.group(1))
PYEOF
}

firmware_version="$(derive_firmware_version)"
stub_package="micropython-rp2-rpi_pico_w-stubs==${firmware_version}.*"

if ! uv pip install --quiet --target typings "$stub_package"; then
    cat >&2 <<EOF
error: couldn't install $stub_package.

The micropython-stubs project (https://github.com/josverl/micropython-stubs) may not have
published stubs for firmware $firmware_version yet - stub releases can lag a new MicroPython
release - or the RPI_PICO_W board stub package may not exist for it. Check available versions at
https://pypi.org/project/micropython-rp2-rpi_pico_w-stubs/#history

This needs a manual decision (e.g. wait for upstream stubs, or hold
toolchain/versions.toml's [micropython] ref back to a version with published stubs) - there is no
automatic fallback.
EOF
    exit 1
fi

mypy
