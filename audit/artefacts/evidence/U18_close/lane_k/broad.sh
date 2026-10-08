#!/bin/bash
R=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u18k_runs
mkdir -p $R/broad
for f in $(cat $R/broad_list.txt); do b=$(basename $f .py); echo "== $b $($R/run1.sh std $f $R/broad/$b.log | tr '\n' ' ')"; done
echo DONE
