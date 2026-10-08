#!/usr/bin/env bash
# usage: matrix.sh <tree> <prefix> <out>
tree="$1"; prefix="$2"; out="$3"; R="$(dirname "$0")"
for f in run_generic_integration real_website_integration uart_link sensortask_integration bus_hazard_concurrency; do
  for stage in std thr cov; do
    line=$("$R/run1.sh" "$tree" "$stage" "tests/test_digital_twin_$f.py" "$R/${prefix}_${f}_${stage}.log")
    echo "$prefix $f $stage $line" >> "$out"
  done
done
echo DONE >> "$out"
