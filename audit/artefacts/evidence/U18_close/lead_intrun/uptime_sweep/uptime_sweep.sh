#!/bin/bash
# uptime_sweep.sh <worktree> <outdir>: every tests/test_*.py at a fresh-boot uptime (30 s), then at 10^8 s; 4 files at a time, each once per pass.
W=$1; O=$2; R=$(dirname "$0"); mkdir -p $O
for up in 30 100000000; do
  mkdir -p $O/up$up
  ls $W/tests/test_*.py | xargs -n1 basename | xargs -P4 -I{} sh -c "unshare -n python3 $R/timens_run.py $up bash $R/run_probe.sh $W tests/{} $O/up$up/{}.log"
  for f in $O/up$up/*.log; do printf '%s %s mem=%s\n' "$(basename $f .py.log)" "$(grep -E '^\[?[a-z_]*\]? ?[0-9]+/[0-9]+ passed|[0-9]+/[0-9]+ passed' $f | tail -1 | grep -oE '[0-9]+/[0-9]+ passed, [0-9]+ failed')" "$(grep -cE 'MemoryError|memory allocation failed' $f)"; done > $O/up$up.summary
done
echo done > $O/done
