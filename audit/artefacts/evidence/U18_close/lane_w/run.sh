#!/bin/bash
# usage: run.sh <mode: e|f|cov> <test file rel path> <outfile> [overlay dir]
# Runs one MicroPython test file from the lane-W worktree in its own network namespace.
set -u
WT=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u18w
SC=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u18w
mode=$1; file=$2; out=$3; ov=${4:-}
MP="build/generated_src:src:tests:frozen_modules:.frozen"
if [ -n "$ov" ]; then MP="$ov:$MP"; fi
STD=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
TR=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython
case $mode in
  e) cmd="$STD -X heapsize=16M $file";;
  f) cmd="$STD -X heapsize=16M tests/_threshold_runner.py $file 32768";;
  cov) cmd="$TR -X heapsize=16M tests/_coverage_runner.py $file $SC/cov.json";;
esac
cd "$WT"
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=\"$MP\" nice -n 19 timeout 300 $cmd" > "$out" 2>&1
rc=$?
end=$(date +%s.%N)
el=$(echo "$end - $start" | bc)
echo "rc=$rc elapsed=${el}s mode=$mode file=$file"
tail -n 3 "$out"
grep -c -E 'MemoryError|memory allocation failed' "$out" | sed 's/^/memory-marker-lines: /'
