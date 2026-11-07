#!/bin/bash
# usage: run.sh <mode:std|thr|cov> <testfile> <logname>
W=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u18c
L=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u18c_logs
MP=/root/pico-toolchain/micropython/ports/unix
mode=$1; f=$2; log=$L/$3
cd $W
case $mode in
  std) cmd="$MP/build-standard/micropython -X heapsize=16M $f";;
  thr) cmd="$MP/build-standard/micropython -X heapsize=16M tests/_threshold_runner.py $f 32768";;
  cov) cmd="$MP/build-settrace/micropython -X heapsize=16M tests/_coverage_runner.py $f $L/cov.json";;
esac
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 $cmd" > $log 2>&1
rc=$?
end=$(date +%s.%N)
echo "rc=$rc elapsed=$(echo "$end - $start" | bc)s" >> $log
tail -3 $log
grep -c -E 'MemoryError|memory allocation failed' $log | sed 's/^/memgate_hits=/'
