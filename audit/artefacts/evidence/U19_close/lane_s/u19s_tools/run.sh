#!/bin/bash
# usage: run.sh <mode: e|f|cov> <test basename without .py> <tag>
set -u
SP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
WT=$SP/wt-u19s
LOGS=$SP/u19s_logs
mode=$1; t=$2; tag=$3
out=$LOGS/${tag}_${t}_${mode}.txt
cd "$WT" || exit 9
STD=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
SET=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython
case $mode in
  e) cmd="$STD -X heapsize=16M tests/$t.py";;
  f) cmd="$STD -X heapsize=16M tests/_threshold_runner.py tests/$t.py 32768";;
  cov) cmd="$SET -X heapsize=16M tests/_coverage_runner.py tests/$t.py $LOGS/${tag}_${t}_cov.json";;
esac
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; cd $WT; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 $cmd" > "$out" 2>&1
rc=$?
end=$(date +%s.%N)
el=$(echo "$end - $start" | bc)
me=$(grep -c -E 'MemoryError|memory allocation failed' "$out")
echo "$tag $t $mode rc=$rc time=${el}s memerr_lines=$me last: $(tail -1 "$out")"
