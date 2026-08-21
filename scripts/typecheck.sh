#!/usr/bin/env bash
# Runs mypy against src/, tests/, and digital_twin/ (pyproject.toml's [tool.mypy] `files` - see
# scripts/lint.sh for the same scope). Pass explicit paths (e.g. `scripts/typecheck.sh src tests`)
# to check only those instead - used by CI's lint-and-typecheck job to gate on just src/tests/,
# leaving digital_twin/ to its own dedicated second pass below (see .github/workflows/ci.yml).
# Assumes mypy is already installed and on PATH; uses
# `uv` (assumed on PATH, same as toolchain/setup_toolchain.py) only to populate typings/, an
# isolated directory holding just the MicroPython stub package - see pyproject.toml's [tool.mypy]
# comments for why that has to stay separate from mypy's own venv.
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

try:
    import tomllib
except ModuleNotFoundError:
    print(
        f"error: this needs python3 >= 3.11 (tomllib, stdlib since 3.11) to parse "
        f"toolchain/versions.toml - the python3 on PATH is {sys.version.split()[0]}. "
        "Activate a venv built against a newer interpreter (see pyproject.toml's "
        "requires-python) or install one, then retry.",
        file=sys.stderr,
    )
    sys.exit(1)

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

# Extra args (if any) override pyproject.toml's [tool.mypy] `files` for this invocation - e.g.
# CI's lint-and-typecheck job passes `src tests` to gate on just that scope, without changing
# what a plain `scripts/typecheck.sh` checks locally (see .github/workflows/ci.yml).
main_status=0
mypy "$@" || main_status=$?

# digital_twin/'s own type-check is a SEPARATE mypy invocation, always run regardless of "$@" -
# see digital_twin/typecheck.ini's own docstring and pyproject.toml's [tool.mypy] exclude comment
# for why: mypy resolves each bare `machine`/`network`/`neopixel` module name to exactly one file
# per run, so digital_twin/'s own fakes and the real board stubs can never both be checked
# correctly in the single main invocation above. digital_twin/ is a fully-reviewed,
# freely-editable scope (CLAUDE.md), same as src/tests/ above, so any finding here is real and
# must fail the script, in CI exactly as much as locally - no tolerance for pre-existing debt.
twin_status=0
mypy --config-file digital_twin/typecheck.ini digital_twin tests/test_digital_twin_*.py || twin_status=$?
if [ "$twin_status" -ne 0 ]; then
    echo "error: digital_twin/typecheck.ini's dedicated pass found real findings - this scope is expected to stay fully clean." >&2
fi

if [ "$main_status" -ne 0 ] || [ "$twin_status" -ne 0 ]; then
    exit 1
fi
