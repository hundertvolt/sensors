#!/bin/bash
# U15 re-gate on 279b9d1 (U14 fix cherry-picked), staged around the U16 whole-tree run (gate_v8's legs, same worktrees and netns):
# now: lint+typecheck (wt-lint), twins dev (wt-tw2) and wozi (wt-tw1); once the U14 rerun prints "done": test.sh -1 (wt-u8)
# and 32768 (wt-u7g); npm after -1; four twins after 32768; last, the coverage verdict alone (gate_u15_cov/run.sh).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; C=279b9d1; G=$S/gate_u15b_main
R=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/tasks/bhczxajl3.output
co() { for w in "$@"; do git -C $S/$w checkout -q --detach $C || { echo "checkout failed $w"; exit 2; }; git -C $S/$w status --short | grep -v '^??' && { echo "dirty $w"; exit 2; }; done; }
t() { echo "$1 $(date +%T)"; }
twin() { ( cd $S/wt-tw$1 && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1; source .venv/bin/activate && scripts/run_digital_twin_ci.sh $2" > $G/tw_$2.log 2>&1; t "$2 rc=$?" ); }
co wt-lint wt-tw1 wt-tw2 wt-u7g
vmstat -t 10 > $G/vmstat.log & VM=$!
t start
( cd $S/wt-lint && source .venv/bin/activate && { scripts/lint.sh > $G/lint.log 2>&1; t "lint rc=$?"; rm -rf .mypy_cache; scripts/typecheck.sh > $G/typecheck_noargs.log 2>&1; t "typecheck noargs rc=$?"; rm -rf .mypy_cache; scripts/typecheck.sh src tests tests_hardware/device_scripts > $G/typecheck_ci.log 2>&1; t "typecheck ci rc=$?"; } ) &
twin 2 dev &
twin 1 wozi &
until grep -q '^done' $R; do sleep 15; done; t "u16 wholetree done"
co wt-u8 wt-tw3 wt-tw4 wt-tw5 wt-tw6
( cd $S/wt-u8 && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1 PYTEST_ADDOPTS=-rs; source .venv/bin/activate; scripts/test.sh" > $G/gc_default.log 2>&1; t "gc-1 rc=$?"
  unshare -n bash -c "ip link set lo up; source .venv/bin/activate; export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:\$PATH; npm test" > $G/npm_test.log 2>&1; t "npm rc=$?" ) &
( cd $S/wt-u7g && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1 PYTEST_ADDOPTS=-rs; source .venv/bin/activate; GC_THRESHOLD=32768 scripts/test.sh" > $G/gc_32768.log 2>&1; t "gc32768 rc=$?"
  twin 3 arzi & twin 4 klkizi & twin 5 schlafzi & twin 6 grkizi & wait ) &
wait $(jobs -p | grep -v "^$VM\$")
kill $VM; t "main done"
$S/gate_u15b_cov/run.sh
t done
