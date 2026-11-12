#!/bin/bash
# The B2 gate, once, on the finished change: the unit tier at both GC stages, dev's twin suite and harness at both, the web tier.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
export PICO_TOOLCHAIN_DIR=$S/tc-int
step() { echo "== STEP $1 start $(date -u +%T)"; shift; "$@"; echo "== STEP rc=$? end $(date -u +%T)"; }
step unit-1 scripts/test.sh
step unit-32768 env GC_THRESHOLD=32768 scripts/test.sh
step twin-suite-1 scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part suite
step twin-harness-1 scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part harness
step twin-suite-32768 scripts/run_digital_twin_ci.sh dev --gc-threshold 32768 --part suite
step twin-harness-32768 scripts/run_digital_twin_ci.sh dev --gc-threshold 32768 --part harness
step npm-lint npm run lint
step npm-typecheck npm run typecheck
step npm-unit npm run test:unit
