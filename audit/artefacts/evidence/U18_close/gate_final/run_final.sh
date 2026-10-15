#!/bin/bash
# U18 final head 675356e (the NTP resync-age test's read moved onto its stepped clock): test.sh at -1 (wt-u8), then the
# coverage leg alone (wt-cov); lint + both typecheck scopes ran beside the uptime sweep (run_lint.sh). The 32768 stage and the six twins
# ran green on 6bd84cf, whose tree differs only in that test file (run at both stages and both uptimes on 675356e).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; C=675356e; G=$S/evidence_stage_u18/gate_final/final_$C; mkdir -p $G
for w in wt-u8 wt-cov; do git -C $S/$w checkout -q --detach $C || { echo "checkout failed in $w"; exit 2; }; git -C $S/$w status --short | grep -v '^??' && { echo "dirty $w"; exit 2; }; done
t() { echo "$1 $(date +%T)" >> $G/gate_times.txt; }
t start
vmstat -n 10 > $G/vmstat.log & VM=$!
( cd $S/wt-u8 && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1 PYTEST_ADDOPTS=-rs; source .venv/bin/activate; scripts/test.sh" > $G/gc_default.log 2>&1; t "gc-1 rc=$?" ) &
wait $(jobs -p | grep -v "^$VM\$")
s=$(date +%s)
( cd $S/wt-cov && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1 PYTEST_ADDOPTS=-rs; source .venv/bin/activate; scripts/test.sh --coverage" > $G/coverage.log 2>&1; t "coverage rc=$? $(( $(date +%s) - s ))s" )
kill $VM; t done
