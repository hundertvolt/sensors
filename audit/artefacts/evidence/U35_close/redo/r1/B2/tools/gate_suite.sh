#!/bin/bash
# The twin suite at both GC stages, after the fresh-boot checker's fix (the gate's only red steps).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
export PICO_TOOLCHAIN_DIR=$S/tc-int
step() { echo "== STEP $1 start $(date -u +%T)"; shift; "$@"; echo "== STEP rc=$? end $(date -u +%T)"; }
step twin-suite-1 scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part suite
step twin-suite-32768 scripts/run_digital_twin_ci.sh dev --gc-threshold 32768 --part suite
