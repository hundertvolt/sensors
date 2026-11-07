#!/bin/bash
# U17 final head 9817530: lint + both typecheck scopes (wt-lint), then the coverage verdict (wt-cov).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; G=$S/gate_u17b; C=9817530
t() { echo "$1 $(date +%T)"; }
for w in wt-lint wt-cov; do git -C $S/$w checkout -q --detach $C || exit 2; git -C $S/$w status --short | grep -v '^??' && { echo dirty $w; exit 2; }; done
( cd $S/wt-lint && source .venv/bin/activate && { scripts/lint.sh > $G/lint.log 2>&1; t "lint rc=$?"; rm -rf .mypy_cache; scripts/typecheck.sh > $G/typecheck_noargs.log 2>&1; t "typecheck noargs rc=$?"; rm -rf .mypy_cache; scripts/typecheck.sh src tests tests_hardware/device_scripts > $G/typecheck_ci.log 2>&1; t "typecheck ci rc=$?"; } )
t0=$(date +%s)
( cd $S/wt-cov && unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1 PYTEST_ADDOPTS=-rs; source .venv/bin/activate; scripts/test.sh --coverage" > $G/coverage.log 2>&1 ); t "coverage rc=$? $(( $(date +%s)-t0 ))s"
