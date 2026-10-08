#!/bin/bash
# U15 coverage verdict on 279b9d1 (U15 integration head with the U14 fix) alone, own dir; gate_v8 NOCOV runs after as its own command.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; G=$S/gate_u15b_cov; C=279b9d1
git -C $S/wt-cov checkout -q --detach $C || exit 2; git -C $S/wt-cov status --short | grep -v '^??' && { echo dirty; exit 2; }
vmstat -t 10 > $G/vmstat.log & V=$!
t0=$(date +%s)
( cd $S/wt-cov && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1 PYTEST_ADDOPTS=-rs; source .venv/bin/activate; scripts/test.sh --coverage" > $G/coverage.log 2>&1 ); rc=$?
kill $V
echo "coverage rc=$rc $(( $(date +%s)-t0 ))s $(date +%T)"
