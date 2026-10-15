#!/usr/bin/env bash
# mypy in three passes - [tool.mypy]'s files, digital_twin/typecheck.ini, host_typecheck.ini - plus two single-file
# checks; why three: CLAUDE.md "Code quality tooling". Stubs install into typings/ at the exact pins of
# toolchain/versions.toml [stubs] (SPECIFICATION.md B.15).
set -euo pipefail
usage="Usage: scripts/typecheck.sh [PATH ...] - extra paths narrow the main pass for a local run; CI passes exactly its files (tests_scripts/test_lint_type_scopes.py checks)"
for arg in "$@"; do
    case "$arg" in
        -h | --help)
            echo "$usage"
            exit 0
            ;;
        -*)
            echo "error: unknown option $arg - $usage" >&2
            exit 2
            ;;
    esac
done
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_require_venv.sh
require_project_venv mypy
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_require_python.sh
require_python311
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_summary_block.sh
summary_unit checks

# Every exit prints the summary block: a step that aborts the run (set -e) is named by its stage.
stage=""
# shellcheck disable=SC2329  # invoked indirectly, by the `trap _finish EXIT` below
_finish() {
    local code=$?
    if [ "$code" -ne 0 ] && [ -n "$stage" ]; then
        summary_add failed "$stage" "exited $code"
    fi
    summary_print "scripts/typecheck.sh" "$code" || code=$?
    exit "$code"
}
trap _finish EXIT
_stage_passed() {
    summary_add passed "$stage"
    stage=""
}

# ---- stub pins block ----
# The two exact stub releases of versions.toml's [stubs], each checked against [micropython] ref: a stub version moves
# with every MicroPython bump, so a pin of another X.Y.Z is refused rather than installed.
derive_stub_pins() {
    python3 - <<'PYEOF'
import re
import sys
import tomllib

path = "toolchain/versions.toml"
try:
    with open(path, "rb") as f:
        versions = tomllib.load(f)
    ref = versions["micropython"]["ref"]
    stubs = versions["stubs"]
except (OSError, tomllib.TOMLDecodeError, KeyError, TypeError) as e:
    print(f"error: {path} has no readable [micropython] ref and [stubs] table ({e!r}) - see SPECIFICATION.md B.15", file=sys.stderr)
    sys.exit(1)
match = re.fullmatch(r"v?(\d+\.\d+\.\d+)", str(ref))
if not match:
    print(f"error: {path}'s [micropython] ref {ref!r} isn't a plain vX.Y.Z tag - no stub release can be checked against it", file=sys.stderr)
    sys.exit(1)
release = match.group(1)
pins = []
for key in ("board", "stdlib"):
    pin = stubs.get(key) if isinstance(stubs, dict) else None
    if not isinstance(pin, str) or not re.fullmatch(re.escape(release) + r"(\.post\d+)?", pin):
        print(f"error: {path}'s [stubs] {key} = {pin!r} does not belong to [micropython] ref {ref} - set it to the {release} stub release you verified, and move [stubs] with every [micropython] ref change (SPECIFICATION.md B.15)", file=sys.stderr)
        sys.exit(1)
    pins.append(pin)
print(release, *pins)
PYEOF
}

stage="stub pins"
pins="$(derive_stub_pins)"
read -r firmware_version board_pin stdlib_pin <<<"$pins"
_stage_passed
# ---- end of the stub pins block ----

# ---- stub install block ----
stage="stub install"
stub_spec="micropython-rp2-rpi_pico_w-stubs==$board_pin micropython-stdlib-stubs==$stdlib_pin"
# typings/ is this script's own gitignored tree: an install recorded under another spec, or under none,
# is wiped first, so a version change never overlays an older install.
stub_spec_file="typings/.stub-spec"
if [ -e typings ] && [ "$(head -n 1 "$stub_spec_file" 2>/dev/null || true)" != "$stub_spec" ]; then
    rm -rf typings
fi
# Dropped before the install and written after its check, so a failed or killed install leaves none.
rm -f "$stub_spec_file"
if ! uv pip install --quiet --target typings "micropython-rp2-rpi_pico_w-stubs==$board_pin" "micropython-stdlib-stubs==$stdlib_pin"; then
    cat >&2 <<EOF
error: couldn't install $stub_spec.

The micropython-stubs project (https://github.com/josverl/micropython-stubs) may not have published
these releases for firmware $firmware_version - stub releases can lag a new MicroPython release. Check
https://pypi.org/project/micropython-rp2-rpi_pico_w-stubs/#history and
https://pypi.org/project/micropython-stdlib-stubs/#history

This needs a manual decision (e.g. wait for upstream stubs, or hold toolchain/versions.toml's
[micropython] ref and [stubs] back to a version with published stubs) - there is no automatic fallback.
EOF
    exit 1
fi
# Each package's one dist-info directory names the version uv installed: it must be the pin, exactly.
installed=()
for package_pin in "micropython_rp2_rpi_pico_w_stubs $board_pin" "micropython_stdlib_stubs $stdlib_pin"; do
    read -r package pin <<<"$package_pin"
    found=()
    for dist_info in typings/"$package"-*.dist-info; do
        if [ -d "$dist_info" ]; then
            version="${dist_info#typings/"$package"-}"
            found+=("${version%.dist-info}")
        fi
    done
    if [ "${#found[@]}" -ne 1 ] || [ "${found[0]}" != "$pin" ]; then
        echo "error: typings/ holds ${package} ${found[*]:-nothing} where versions.toml pins $pin - remove typings/ and re-run" >&2
        exit 1
    fi
    installed+=("$pin")
done
echo "== MicroPython stubs: board ${installed[0]}, stdlib ${installed[1]} (for firmware $firmware_version)"
printf '%s\n%s\n' "$stub_spec" "${installed[*]}" >"$stub_spec_file"
_stage_passed
# ---- end of the stub install block ----

# ---- stub repairs block ----
# Two verified stub defects repaired in the stub tree, never by `type: ignore` in our code (CLAUDE.md "Code quality
# tooling"). A fixed upstream makes a repair a no-op; a moved tree fails it (SPECIFICATION.md F.5.5).
stage="stub repairs"
_moved() {
    echo "error: the installed stub tree moved ($1 missing) - re-verify the $2 repair against the new layout (SPECIFICATION.md F.5.5)" >&2
    exit 1
}
[ -d typings/stdlib/asyncio ] || _moved typings/stdlib/asyncio/ "asyncio Future"
[ -f typings/stdlib/_asyncio.pyi ] || _moved typings/stdlib/_asyncio.pyi "asyncio Future"
if [ ! -e typings/stdlib/asyncio/futures.pyi ]; then
    grep -q '^class _Future' typings/stdlib/_asyncio.pyi || _moved "class _Future in typings/stdlib/_asyncio.pyi" "asyncio Future"
    printf '%s\n' 'from _asyncio import _Future as Future' >typings/stdlib/asyncio/futures.pyi
fi
# Line-ending agnostic: that stub ships CRLF.
builtins_stub="typings/stdlib/builtins.pyi"
[ -f "$builtins_stub" ] || _moved "$builtins_stub" NotImplemented
if grep -q '^# NotImplemented: _NotImplementedType' "$builtins_stub"; then
    sed -i 's/^# \(NotImplemented: _NotImplementedType\)/\1/' "$builtins_stub"
elif ! grep -q '^NotImplemented:' "$builtins_stub"; then
    _moved "NotImplemented in $builtins_stub" NotImplemented
fi
_stage_passed
# ---- end of the stub repairs block ----

# The main pass checks the generated device modules and boot entries as sources, and the twin pass resolves
# sensortask_<device> from the same directory, so it is generated first.
stage="module generation"
echo "== Generating buildgen device modules into build/generated_src/"
uv run --no-sync scripts/_generate_sensortask_modules.py
_stage_passed

# Every run always runs; each is recorded as its own check, and any failure fails the script.
failed=0
_record() {
    local name="$1" detail="$2"
    shift 2
    if "$@"; then
        summary_add passed "$name" "$detail"
    else
        summary_add failed "$name" "$detail"
        echo "error: the $name ($detail) found real findings - every scope is expected to stay fully clean." >&2
        failed=1
    fi
}

# Extra args narrow the main pass for a local run; CI passes exactly `files` (tests_scripts/test_lint_type_scopes.py
# checks).
_record "main pass" "pyproject.toml [tool.mypy]" mypy "$@"
# mypy resolves each bare machine/network/neopixel name to one file per run, so the twin's own fakes and the board
# stubs can never both be right in one pass: the twin pass takes its files from its ini.
_record "twin pass" "digital_twin/typecheck.ini" mypy --config-file digital_twin/typecheck.ini
# The host-CPython scopes need mypy's real typeshed, which the main pass replaces (host_typecheck.ini's header).
_record "host pass" "host_typecheck.ini" mypy --config-file host_typecheck.ini
# Each of these is a second file of a module name another file of its pass holds (network, conftest), so it is
# checked alone, where nothing else of that name is in the run.
_record "bench conftest check" "host_typecheck.ini" mypy --config-file host_typecheck.ini tests_hardware/bench/conftest.py
_record "network check" "pyproject.toml [tool.mypy]" mypy tests/network.py
_record "conftest check" "host_typecheck.ini" mypy --config-file host_typecheck.ini tests_scripts/conftest.py

if [ "$failed" -ne 0 ]; then
    exit 1
fi
exit 0
