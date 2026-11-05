#!/bin/bash
# The B4 gate, once, on the finished change: rebuild, lint, the three typecheck passes, the unit tier at both GC
# stages, dev's twin suite and harness at both, the web tier.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
W=$S/wt-b4
export PICO_TOOLCHAIN_DIR=$S/tc-int
step() { echo "== STEP $1 start $(date -u +%T)"; shift; "$@"; echo "== STEP rc=$? end $(date -u +%T)"; }
step rebuild bash $S/u23/rebuild.sh $W
step lint bash $S/u35/lead/lint_direct.sh
ln -s $S/shared/typings $W/typings
step mypy-main mypy --cache-dir=/dev/null
step mypy-host mypy --cache-dir=/dev/null --config-file host_typecheck.ini
step mypy-twin mypy --cache-dir=/dev/null --config-file digital_twin/typecheck.ini
rm /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-b4/typings
step unit-1 scripts/test.sh
step unit-32768 env GC_THRESHOLD=32768 scripts/test.sh
step twin-suite-1 scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part suite
step twin-harness-1 scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part harness
step twin-suite-32768 scripts/run_digital_twin_ci.sh dev --gc-threshold 32768 --part suite
step twin-harness-32768 scripts/run_digital_twin_ci.sh dev --gc-threshold 32768 --part harness
step npm-lint npm run lint
step npm-typecheck npm run typecheck
step npm-unit npm run test:unit
