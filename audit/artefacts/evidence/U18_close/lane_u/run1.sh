#!/bin/bash
# usage: run1.sh <mode: e|f|s> <test file rel> <log> [extra MICROPYPATH prefix]
WT=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u18u
MP=/root/pico-toolchain/micropython/ports/unix
mode=$1; f=$2; log=$3; pre=$4
cd "$WT"
MPP="build/generated_src:src:tests:frozen_modules:.frozen"
[ -n "$pre" ] && MPP="$pre:$MPP"
case $mode in
  e) cmd="$MP/build-standard/micropython -X heapsize=16M $f";;
  f) cmd="$MP/build-standard/micropython -X heapsize=16M tests/_threshold_runner.py $f 32768";;
  s) cmd="$MP/build-settrace/micropython -X heapsize=16M tests/_coverage_runner.py $f /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u18u/cov.json";;
esac
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='$MPP' nice -n 19 timeout 300 $cmd" > "$log" 2>&1
rc=$?
end=$(date +%s.%N)
el=$(echo "$end - $start" | bc)
echo "rc=$rc elapsed=${el}s mode=$mode file=$f" | tee -a "$log"
grep -c "MemoryError\|memory allocation failed" "$log" | sed 's/^/memmarkers=/'
tail -3 "$log"
