#!/bin/bash
# ts_time.sh <worktree> <outdir>: tests_scripts as test.sh runs it (generated modules first), with junit per-test times.
W=$1; O=$2; mkdir -p $O; cd $W || exit 2
unshare -n bash -c "ip link set lo up; export UV_OFFLINE=1; source .venv/bin/activate
  python scripts/_generate_sensortask_modules.py > $O/gen.log 2>&1 || exit 3
  s=\$(date +%s); PYTHONPATH=scripts uv run pytest tests_scripts -q -p no:cacheprovider --junitxml=$O/junit.xml --durations=40 > $O/pytest.log 2>&1; rc=\$?
  echo \"rc=\$rc wall=\$(( \$(date +%s) - s ))s\" > $O/result.txt"
