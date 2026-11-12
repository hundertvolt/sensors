#!/bin/bash
# t1.sh FILE [DEVICE]: one MicroPython test file at stage e only (a red probe).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
export TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen
[ -n "$2" ] && export TEST_DEVICE=$2
timeout 900 $S/tc-int/micropython/ports/unix/build-standard/micropython -X heapsize=16M "$1" 2>&1 | grep -v '^PASS' | tail -${TAILN:-30}
