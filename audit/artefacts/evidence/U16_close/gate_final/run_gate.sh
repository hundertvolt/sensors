#!/bin/bash
# U16 re-gate on d58b8dd (lead fixes + the U15 fix): gate_v8 NOCOV (lint/typecheck, test.sh both stages, six twins, npm), then the coverage verdict alone in wt-cov.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; C=d58b8dd; G=$S/gate_u16b
NOCOV=1 $S/gate_v8.sh $C $G/main
git -C $S/wt-cov checkout -q --detach $C || exit 2; git -C $S/wt-cov status --short | grep -v '^??' && { echo dirty; exit 2; }
vmstat -t 10 > $G/vmstat_cov.log & V=$!; t0=$(date +%s)
( cd $S/wt-cov && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1 PYTEST_ADDOPTS=-rs; source .venv/bin/activate; scripts/test.sh --coverage" > $G/coverage.log 2>&1 ); rc=$?
kill $V; echo "coverage rc=$rc $(( $(date +%s)-t0 ))s $(date +%T)"; echo "all done $(date +%T)"
