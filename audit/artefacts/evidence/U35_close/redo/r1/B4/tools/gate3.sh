#!/bin/bash
# The rest after the continuation's wrapper hit its time limit at unit-32768's end: the five scenario jobs at -1 the
# port-53 lock lost, dev's twin suite and harness at both GC stages, the web tier.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
export PICO_TOOLCHAIN_DIR=$S/tc-int
step() { echo "== STEP $1 start $(date -u +%T)"; shift; "$@"; echo "== STEP rc=$? end $(date -u +%T)"; }
step scenarios-1 bash $S/u35r/r1/B4/tools/scen1.sh arzi grkizi klkizi schlafzi wozi
step twin-suite-1 scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part suite
step twin-harness-1 scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part harness
step twin-suite-32768 scripts/run_digital_twin_ci.sh dev --gc-threshold 32768 --part suite
step twin-harness-32768 scripts/run_digital_twin_ci.sh dev --gc-threshold 32768 --part harness
step npm-lint npm run lint
step npm-typecheck npm run typecheck
step npm-unit npm run test:unit
