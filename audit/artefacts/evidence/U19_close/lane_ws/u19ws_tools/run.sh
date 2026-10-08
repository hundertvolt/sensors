#!/bin/bash
# usage: run.sh <mode: e|f|cov> <testfile> <logname> [overlay_dir]
# Runs one test file from the WS worktree at nice 19, in its own network namespace.
set -u
WT=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u19ws
T=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u19ws_tools
mode=$1; tf=$2; log=$T/logs/$3; ov=${4:-}
MP="build/generated_src:src:tests:frozen_modules:.frozen"
[ -n "$ov" ] && MP="$ov:$MP"
RUNNER=""
[ -n "$ov" ] && RUNNER="$ov/_ov_runner.py"
case $mode in
  oe) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="$RUNNER $tf";;
  of) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="$RUNNER $tf 32768";;
  ocov) BIN=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython; ARGS="$ov/_ov_cov_runner.py $tf $T/logs/$3.cov.json";;
  e) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="$tf";;
  f) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="tests/_threshold_runner.py $tf 32768";;
  cov) BIN=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython; ARGS="tests/_coverage_runner.py $tf $T/logs/$3.cov.json";;
esac
cd $WT
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=$MP nice -n 19 timeout 600 $BIN -X heapsize=16M $ARGS" > $log 2>&1
rc=$?
end=$(date +%s.%N)
echo "rc=$rc elapsed=$(echo "$end - $start" | bc)" >> $log
tail -3 $log
