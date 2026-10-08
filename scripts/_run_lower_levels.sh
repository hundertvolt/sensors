#!/usr/bin/env bash
# Runs every level below a hardware level, in order, on a recorded commit (SPECIFICATION.md E.6.1):
# scripts/test.sh at both GC stages, npm test, then scripts/run_digital_twin_ci.sh per device. Stops
# at the first failure with exit 1, before any board is touched. Sequential: these suites bind ports.
set -euo pipefail

if [ "$#" -ne 1 ] || { [ "$1" != "L3" ] && [ "$1" != "L4" ]; }; then
    echo "Usage: scripts/_run_lower_levels.sh <L3|L4> - every level below it, stopping at the first failure" >&2
    exit 2
fi
target="$1"
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# A status git cannot report reads as dirty: the run is never claimed for a commit it may not match.
LOWER_LEVELS_COMMIT="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
LOWER_LEVELS_DIRTY=1
if porcelain="$(git status --porcelain 2>/dev/null)" && [ -z "$porcelain" ]; then
    LOWER_LEVELS_DIRTY=0
fi
export LOWER_LEVELS_COMMIT LOWER_LEVELS_DIRTY
echo "== Lower levels for $target on commit $LOWER_LEVELS_COMMIT (uncommitted changes: $([ "$LOWER_LEVELS_DIRTY" = 1 ] && echo yes || echo no))"

_step() {
    local name="$1" rc=0
    shift
    echo "== $name"
    "$@" || rc=$?
    echo "== $name: exit $rc"
    if [ "$rc" -ne 0 ]; then
        echo "== $name failed - stopping before $target, no hardware touched" >&2
        exit 1
    fi
}

_step "scripts/test.sh" scripts/test.sh
_step "GC_THRESHOLD=32768 scripts/test.sh" env GC_THRESHOLD=32768 scripts/test.sh
_step "npm test" npm test
# Every derived device: each devices/*.toml except the reserved zz_test_ fixtures.
for toml in devices/*.toml; do
    device="$(basename "$toml" .toml)"
    if [[ "$device" == zz_test_* ]]; then
        continue
    fi
    _step "scripts/run_digital_twin_ci.sh $device" scripts/run_digital_twin_ci.sh "$device"
done
echo "== Lower levels for $target: all passed"
