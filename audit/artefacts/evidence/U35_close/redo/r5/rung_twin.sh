#!/bin/bash
# rung_twin.sh STAGE DEVICE FILE: one test file at GC stage -1 or 32768 (TEST_DEVICE set when DEVICE is not "-").
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
MP=$S/tc-int/micropython/ports/unix/build-standard/micropython
stage=$1; dev=$2; f=$3
[ "$dev" != "-" ] && export TEST_DEVICE=$dev
export TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen
if [ "$stage" = "-1" ]; then "$MP" -X heapsize=16M "$f"; else "$MP" -X heapsize=16M tests/_threshold_runner.py "$f" 32768; fi
rc=$?
echo "RUNG_RESULT stage=$stage dev=$dev file=$f rc=$rc"
exit $rc
