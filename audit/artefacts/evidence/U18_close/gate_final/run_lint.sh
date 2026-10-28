#!/bin/bash
# U18 final head 675356e: lint + both typecheck scopes in wt-lint (light and deterministic, so run beside the uptime sweep).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; C=675356e; G=$S/evidence_stage_u18/gate_final/final_$C; mkdir -p $G
git -C $S/wt-lint checkout -q --detach $C || exit 2; git -C $S/wt-lint status --short | grep -v '^??' && { echo "dirty wt-lint"; exit 2; }
t() { echo "$1 $(date +%T)" >> $G/gate_times.txt; }
cd $S/wt-lint && source .venv/bin/activate
scripts/lint.sh > $G/lint.log 2>&1; t "lint rc=$?"
rm -rf .mypy_cache; scripts/typecheck.sh > $G/typecheck_noargs.log 2>&1; t "typecheck noargs rc=$?"
rm -rf .mypy_cache; scripts/typecheck.sh src tests tests_hardware/device_scripts > $G/typecheck_ci.log 2>&1; t "typecheck ci rc=$?"
