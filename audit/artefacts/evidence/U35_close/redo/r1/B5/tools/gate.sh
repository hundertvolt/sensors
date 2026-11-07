#!/bin/bash
# The B5 gate, once, on the finished change: lint and the three mypy passes, the unit tier at both GC stages,
# dev's twin suite and harness at both, the hardware tier's collection, the web tier.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
export PICO_TOOLCHAIN_DIR=$S/tc-int
step() { echo "== STEP $1 start $(date -u +%T)"; shift; "$@"; echo "== STEP rc=$? end $(date -u +%T)"; }
step lint $S/u35/lead/lint_direct.sh
step mypy-main mypy --cache-dir=/dev/null
step mypy-host mypy --cache-dir=/dev/null --config-file host_typecheck.ini
step mypy-twin mypy --cache-dir=/dev/null --config-file digital_twin/typecheck.ini
step unit-1 scripts/test.sh
step unit-32768 env GC_THRESHOLD=32768 scripts/test.sh
step twin-suite-1 scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part suite
step twin-harness-1 scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part harness
step twin-suite-32768 scripts/run_digital_twin_ci.sh dev --gc-threshold 32768 --part suite
step twin-harness-32768 scripts/run_digital_twin_ci.sh dev --gc-threshold 32768 --part harness
step hw-collect python -m pytest -q --collect-only tests_hardware
step npm-lint npm run lint
step npm-typecheck npm run typecheck
step npm-unit npm run test:unit
