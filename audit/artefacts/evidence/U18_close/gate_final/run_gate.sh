#!/bin/bash
# gate_v8.sh <commit> <outdir>: gate_v7, with NOCOV=1 leaving wt-cov alone (its leg then runs separately). gate_v7: gate_v6 with the coverage leg started after the 32768 run, beside the four twins:
# at t0 it shared a saturated host (100% CPU) and its timing-exposed checks timed out (OF-33). gate_v6: + --coverage in wt-cov (CI's
# unit-tests-coverage leg, the only settrace run; 8d44fd1 went red there only). gate_v5: gate_v3 with lint+typecheck in their own worktree wt-lint (typecheck.sh regenerates
# build/generated_src, which raced test.sh in wt-u8). t0: lint+typecheck (wt-lint), test.sh at -1 (wt-u8)
# and 32768 (wt-u7g), the two longest twins (dev, wozi); npm after the -1 run (shares wt-u8); the other four twins
# after the 32768 run. Each run in its own worktree + netns. vmstat samples CPU every 10 s.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; C=$1; G=$2; mkdir -p $G
WTS="wt-lint"; [ -n "$NOCOV" ] || WTS="wt-cov $WTS"
for w in $WTS wt-u8 wt-u7g wt-tw1 wt-tw2 wt-tw3 wt-tw4 wt-tw5 wt-tw6; do git -C $S/$w checkout -q --detach $C || { echo "checkout failed in $w"; exit 2; }; git -C $S/$w status --short | grep -v '^??' && { echo "dirty $w"; exit 2; }; done
vmstat -n 10 > $G/vmstat.log & VM=$!
t() { echo "$1 $(date +%T)"; }
twin() { ( cd $S/wt-tw$1 && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1; source .venv/bin/activate && scripts/run_digital_twin_ci.sh $2" > $G/tw_$2.log 2>&1; t "$2 rc=$?" ); }
t start
( cd $S/wt-lint && source .venv/bin/activate && { scripts/lint.sh > $G/lint.log 2>&1; t "lint rc=$?"; rm -rf .mypy_cache; scripts/typecheck.sh > $G/typecheck_noargs.log 2>&1; t "typecheck noargs rc=$?"; rm -rf .mypy_cache; scripts/typecheck.sh src tests tests_hardware/device_scripts > $G/typecheck_ci.log 2>&1; t "typecheck ci rc=$?"; } ) &
( cd $S/wt-u8 && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1 PYTEST_ADDOPTS=-rs; source .venv/bin/activate; scripts/test.sh" > $G/gc_default.log 2>&1; t "gc-1 rc=$?"
  unshare -n bash -c "ip link set lo up; source .venv/bin/activate; export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:\$PATH; npm test" > $G/npm_test.log 2>&1; t "npm rc=$?" ) &
( cd $S/wt-u7g && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1 PYTEST_ADDOPTS=-rs; source .venv/bin/activate; GC_THRESHOLD=32768 scripts/test.sh" > $G/gc_32768.log 2>&1; t "gc32768 rc=$?"
  [ -n "$NOCOV" ] || ( cd $S/wt-cov && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1 PYTEST_ADDOPTS=-rs; source .venv/bin/activate; scripts/test.sh --coverage" > $G/coverage.log 2>&1; t "coverage rc=$?" ) &
  twin 3 arzi & twin 4 klkizi & twin 5 schlafzi & twin 6 grkizi & wait ) &
twin 2 dev &
twin 1 wozi &
wait $(jobs -p | grep -v "^$VM\$")
kill $VM; t done
