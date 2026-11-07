#!/bin/bash
# The gate's continuation after the unit-1 reds were fixed: the cheap checks again, unit-1's failing scenario jobs at
# -1 (its fixed MicroPython files ran at both stages through t.sh), then every step unit-1's stop left unrun.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
W=$S/wt-b4
export PICO_TOOLCHAIN_DIR=$S/tc-int
MP=$S/tc-int/micropython/ports/unix/build-standard/micropython
step() { echo "== STEP $1 start $(date -u +%T)"; shift; "$@"; echo "== STEP rc=$? end $(date -u +%T)"; }
scen() {
    local rc=0 d
    for d in arzi dev grkizi klkizi schlafzi wozi; do
        uv run --no-sync scripts/_digital_twin_scenarios.py --device "$d" --micropython-bin "$MP" --logs-dir "$S/b4work/scen1/$d" --gc-threshold -1 --shared-port-53 > "$S/b4work/scen1_$d.log" 2>&1 &
    done
    for d in arzi dev grkizi klkizi schlafzi wozi; do wait -n || rc=1; done
    grep -h 'FAILED\|Result:' $S/b4work/scen1_*.log
    return $rc
}
step rebuild bash $S/u23/rebuild.sh $W
step lint bash $S/u35/lead/lint_direct.sh
ln -s $S/shared/typings $W/typings
step mypy-main mypy --cache-dir=/dev/null
step mypy-host mypy --cache-dir=/dev/null --config-file host_typecheck.ini
step mypy-twin mypy --cache-dir=/dev/null --config-file digital_twin/typecheck.ini
rm /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-b4/typings
step scenarios-1 scen
step unit-32768 env GC_THRESHOLD=32768 scripts/test.sh
step twin-suite-1 scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part suite
step twin-harness-1 scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part harness
step twin-suite-32768 scripts/run_digital_twin_ci.sh dev --gc-threshold 32768 --part suite
step twin-harness-32768 scripts/run_digital_twin_ci.sh dev --gc-threshold 32768 --part harness
step npm-lint npm run lint
step npm-typecheck npm run typecheck
step npm-unit npm run test:unit
