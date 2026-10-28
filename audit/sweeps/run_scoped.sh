#!/usr/bin/env bash
# Scoped tests for one work-order step: each named tests/test_*.py file at both GC stages, with exactly the command
# scripts/test.sh's run_test_file uses (MICROPYPATH, heap, TZ, timeout); tests_scripts/ and tests_js/ files via their own
# runners. Port-binding, so it takes the audit port lock. Usage: run_scoped.sh <test file> ...
set -uo pipefail
cd "$(git rev-parse --show-toplevel)"
export TZ=UTC
mp="${PICO_TOOLCHAIN_DIR:-$HOME/pico-toolchain}/micropython/ports/unix/build-standard/micropython"
exec 9>/tmp/sensors-audit-ports.lock
flock 9
uv run -q scripts/_generate_sensortask_modules.py >/dev/null || { echo "generation failed"; exit 1; }
fail=0
py=() js=()
for f in "$@"; do
    case "$f" in
        tests_scripts/*) py+=("$f") ;;
        tests_js/*) js+=("$f") ;;
        tests/test_*.py)
            for stage in default 32768; do
                if [ "$stage" = default ]; then cmd=("$f"); else cmd=(tests/_threshold_runner.py "$f" 32768); fi
                out="$(MICROPYPATH="build/generated_src:src:tests:frozen_modules:.frozen" stdbuf -oL -eL timeout --kill-after=10 240 "$mp" -X heapsize=16M "${cmd[@]}" 2>&1)"
                ec=$?
                if [ $ec -ne 0 ] || grep -qE "MemoryError|memory allocation failed" <<<"$out"; then
                    echo "FAIL [$stage] $f (exit $ec)"; tail -25 <<<"$out"; fail=1
                else
                    echo "PASS [$stage] $f: $(grep -E 'passed' <<<"$out" | tail -1)"
                fi
            done ;;
        *) echo "skip (not a test file): $f" ;;
    esac
done
if [ ${#py[@]} -gt 0 ]; then uv run pytest -q "${py[@]}" || fail=1; fi
if [ ${#js[@]} -gt 0 ]; then npx vitest run "${js[@]}" || fail=1; fi
exit $fail
