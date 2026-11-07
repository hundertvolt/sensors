#!/bin/bash
# usage: run.sh <test file rel path> <e|f|cov> <logname> [overlay dir]
SP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
WT=$SP/wt-u18n
T=$1; MODE=$2; LOG=$SP/u18n/logs/$3; OVL=$4
MP="build/generated_src:src:tests:frozen_modules:.frozen"
if [ -n "$OVL" ]; then MP="$OVL:$MP"; fi
TARGET=$T
if [ -n "$OVL" ]; then TARGET="$SP/u18n/ovl_run.py $(basename $T .py)"; fi
case $MODE in
  e) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="$TARGET";;
  f) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="tests/_threshold_runner.py $T 32768"; [ -n "$OVL" ] && ARGS="$TARGET 32768";;
  cov) BIN=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython; ARGS="tests/_coverage_runner.py $T $SP/u18n/logs/$3.cov.json";;
esac
cd $WT
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; cd $WT; TZ=UTC MICROPYPATH='$MP' nice -n 19 timeout 600 $BIN -X heapsize=16M $ARGS" > $LOG 2>&1
rc=$?
end=$(date +%s.%N)
echo "rc=$rc elapsed=$(echo "$end - $start" | bc)" | tee -a $LOG
tail -3 $LOG | head -2
grep -c "MemoryError\|memory allocation failed" $LOG | sed 's/^/memerr_lines=/'
