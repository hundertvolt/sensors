#!/usr/bin/env bash
# Runs mypy against pyproject.toml's [tool.mypy] `files` scope, plus two further invocations that
# always run regardless of "$@" (digital_twin/typecheck.ini, host_typecheck.ini). Why three passes
# rather than one: CLAUDE.md's "Code quality tooling", and each config's own header.
#
# Pass explicit paths to narrow the main pass only - CI's lint-and-typecheck job does that.
# Assumes mypy is on PATH; `uv` is used only to populate typings/, the isolated MicroPython stub
# directory SPECIFICATION.md Part B.15 explains.
#
# The firmware version lives in exactly one place, toolchain/versions.toml's [micropython] ref; the
# stub version below is derived from it rather than pinned again (derive_firmware_version()).
# Requires python3 >= 3.11 for tomllib, as setup_toolchain.py already does.
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

# Two verified regressions in micropython-stdlib-stubs 1.29.0.post1/.post2, repaired at the stub
# tree rather than papered over with `type: ignore` in our own code, which is correct on the real
# interpreter both times. What each defect is: CLAUDE.md's "Code quality tooling".
#
# Each repair is conditional on the defect still being present AND on its target file sitting where
# it expects, so a fixed upstream or a restructured tree makes it a silent no-op rather than a
# failure. The NotImplemented substitution is line-ending agnostic: that stub ships CRLF.
asyncio_futures="typings/stdlib/asyncio/futures.pyi"
if [ -d "typings/stdlib/asyncio" ] && [ ! -e "$asyncio_futures" ]; then
    printf '%s\n' 'from _asyncio import _Future as Future' > "$asyncio_futures"
fi
builtins_stub="typings/stdlib/builtins.pyi"
if [ -f "$builtins_stub" ] && grep -q '^# NotImplemented: _NotImplementedType' "$builtins_stub"; then
    sed -i 's/^# \(NotImplemented: _NotImplementedType\)/\1/' "$builtins_stub"
fi

# heap_headroom_after_full_system_build.py is the main pass's sole static `import sensortask_dev`,
# and no hand-written copy exists in src/ any more (Part L.2) - so build/generated_src/, this pass's
# own mypy_path entry, has to be populated first, exactly as scripts/test.sh needs it too.
echo "== Generating buildgen device modules into build/generated_src/ (for import resolution)"
uv run scripts/_generate_sensortask_modules.py

# Extra args (if any) override pyproject.toml's [tool.mypy] `files` for this invocation - e.g.
# CI's lint-and-typecheck job passes `src tests` to gate on just that scope, without changing
# what a plain `scripts/typecheck.sh` checks locally (see .github/workflows/ci.yml).
main_status=0
mypy "$@" || main_status=$?

# A SEPARATE invocation, always run regardless of "$@": mypy resolves each bare `machine`/`network`/
# `neopixel` name to one file per run, so the twin's own fakes and the real board stubs can never
# both be right in one pass (digital_twin/typecheck.ini's docstring has it).
#
# The twin is a fully-reviewed scope like src/ and tests/, so a finding here is real and fails the
# script, in CI exactly as much as locally.
twin_status=0
mypy --config-file digital_twin/typecheck.ini digital_twin tests/test_digital_twin_*.py || twin_status=$?
if [ "$twin_status" -ne 0 ]; then
    echo "error: digital_twin/typecheck.ini's dedicated pass found real findings - this scope is expected to stay fully clean." >&2
fi

# The host-CPython scopes need a THIRD invocation for the twin's reason again: the main pass
# replaces mypy's typeshed with the MicroPython stubs, which carry no `ast`/`pathlib`/`tomllib`, so
# every stdlib import there would read as missing. Always run; host_typecheck.ini's header has it.
host_status=0
mypy --config-file host_typecheck.ini || host_status=$?
if [ "$host_status" -ne 0 ]; then
    echo "error: host_typecheck.ini's dedicated pass found real findings - this scope is expected to stay fully clean." >&2
fi

if [ "$main_status" -ne 0 ] || [ "$twin_status" -ne 0 ] || [ "$host_status" -ne 0 ]; then
    exit 1
fi
