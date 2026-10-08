#!/bin/bash
# usage: run1.sh <test file basename> <mode: plain|gc|trace> <tag>
set -u
WT=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u20b
LOGS=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u20b_logs
f=$1; mode=$2; tag=$3
cd "$WT"
case $mode in
  plain) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="tests/$f";;
  gc) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="tests/_threshold_runner.py tests/$f 32768";;
  trace) BIN=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython; ARGS="tests/_coverage_runner.py tests/$f $LOGS/cov_${f%.py}_$tag.json";;
esac
out="$LOGS/${f%.py}_${mode}_${tag}.log"
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; cd $WT; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 600 $BIN -X heapsize=16M $ARGS" > "$out" 2>&1
rc=$?
end=$(date +%s.%N)
el=$(echo "$end - $start" | bc)
mem=$(grep -c -E 'MemoryError|memory allocation failed' "$out")
echo "$f $mode $tag rc=$rc time=${el}s memerr_lines=$mem summary: $(grep -E 'passed|failed' "$out" | tail -1)"
