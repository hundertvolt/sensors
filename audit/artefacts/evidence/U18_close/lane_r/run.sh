#!/bin/bash
# usage: run.sh <mode: std|thr|cov> <test file> [label]
WT=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u18r
OUT=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u18r
MODE=$1; F=$2; LABEL=${3:-run}
EXTRA_PATH=${EXTRA_PATH:-}
cd "$WT" || exit 9
MP="build/generated_src:src:tests:frozen_modules:.frozen"
[ -n "$EXTRA_PATH" ] && MP="$EXTRA_PATH:$MP"
case $MODE in
  std) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="$F";;
  thr) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="tests/_threshold_runner.py $F 32768";;
  cov) BIN=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython; ARGS="tests/_coverage_runner.py $F $OUT/cov_$LABEL.json";;
esac
LOG=$OUT/${LABEL}_${MODE}.log
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='$MP' nice -n 19 timeout 300 $BIN -X heapsize=16M $ARGS" > "$LOG" 2>&1
rc=$?
end=$(date +%s.%N)
el=$(echo "$end - $start" | bc)
mem=$(grep -c -E 'MemoryError|memory allocation failed' "$LOG")
echo "$MODE $F rc=$rc elapsed=${el}s memmarkers=$mem log=$LOG"
tail -3 "$LOG"
