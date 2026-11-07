#!/bin/bash
# usage: mp.sh <stage: e|f|cov> <test file name e.g. test_asy_neopixel_driver> [label] [netns]
set -u
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
WT=$S/wt-u22p
OUT=$S/u22p_runs
stage=$1; name=$2; label=${3:-run}; ns=${4:-}
cd "$WT"
BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
case $stage in
  e) ARGS="tests/$name.py";;
  f) ARGS="tests/_threshold_runner.py tests/$name.py 32768";;
  cov) BIN=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython; ARGS="tests/_coverage_runner.py tests/$name.py $OUT/cov_$name.json";;
esac
log=$OUT/${name}_${stage}_${label}.log
start=$(date +%s.%N)
if [ -n "$ns" ]; then
  unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 $BIN -X heapsize=16M $ARGS" > "$log" 2>&1
else
  TZ=UTC MICROPYPATH="build/generated_src:src:tests:frozen_modules:.frozen" nice -n 19 timeout 300 $BIN -X heapsize=16M $ARGS > "$log" 2>&1
fi
rc=$?
end=$(date +%s.%N)
wall=$(echo "$end - $start" | bc)
me=$(grep -c -i "MemoryError\|memory allocation failed" "$log")
echo "$name $stage $label rc=$rc wall=${wall}s memerr_lines=$me $(tail -1 "$log")"
