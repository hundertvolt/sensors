#!/bin/bash
# t.sh FILE [DEVICE]: one MicroPython test file at both GC stages (run inside run.sh's shell, cwd = worktree).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
MP=$S/tc-int/micropython/ports/unix/build-standard/micropython
f=$1
export TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen
[ -n "$2" ] && export TEST_DEVICE=$2
rc=0
echo "### $f stage e"; timeout 900 $MP -X heapsize=16M "$f" 2>&1 | tail -${TAILN:-15}; r=${PIPESTATUS[0]}; [ $r -ne 0 ] && rc=$r
echo "### $f stage f"; timeout 900 $MP -X heapsize=16M tests/_threshold_runner.py "$f" 32768 2>&1 | tail -${TAILN:-15}; r=${PIPESTATUS[0]}; [ $r -ne 0 ] && rc=$r
echo "t.sh rc=$rc"; exit $rc
