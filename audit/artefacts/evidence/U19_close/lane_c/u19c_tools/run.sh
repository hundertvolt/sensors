#!/bin/bash
# usage: run.sh <tests/test_x.py> <e|f|cov> <label>
set -u
WT=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u19c
LOG=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u19c_logs
f=$1; mode=$2; label=$3
base=$(basename "$f" .py)
out="$LOG/${base}_${mode}_${label}.txt"
cd "$WT" || exit 9
case $mode in
  e) bin=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; args="$f";;
  f) bin=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; args="tests/_threshold_runner.py $f 32768";;
  cov) bin=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython; args="tests/_coverage_runner.py $f $LOG/${base}_${label}_cov.json";;
esac
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; cd $WT; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 $bin -X heapsize=16M $args" > "$out" 2>&1
rc=$?
end=$(date +%s.%N)
el=$(echo "$end - $start" | bc)
mem=$(grep -c -E 'MemoryError|memory allocation failed' "$out")
echo "$base $mode $label rc=$rc time=${el}s memhits=$mem last: $(tail -1 "$out")"
