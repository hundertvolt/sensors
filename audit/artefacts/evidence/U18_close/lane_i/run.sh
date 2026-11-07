#!/bin/bash
# usage: run.sh <test file rel> <mode: std|thr|cov> <logtag>
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $S/wt-u18i || exit 2
f=$1; mode=$2; tag=$3
base=$(basename $f .py)
log=$S/u18i/logs/${tag}_${base}_${mode}.log
mkdir -p $S/u18i/logs
case $mode in
  std) bin=build-standard; args="$f";;
  thr) bin=build-standard; args="tests/_threshold_runner.py $f 32768";;
  cov) bin=build-settrace; args="tests/_coverage_runner.py $f $S/u18i/cov_${base}.json";;
esac
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 /root/pico-toolchain/micropython/ports/unix/$bin/micropython -X heapsize=16M $args" > $log 2>&1
rc=$?
end=$(date +%s.%N)
el=$(echo "$end - $start" | bc)
summary=$(grep -E "passed|failed" $log | tail -1)
mem=$(grep -c -E "MemoryError|memory allocation failed" $log)
echo "$tag $base $mode rc=$rc t=${el}s mem=$mem :: $summary" | tee -a $S/u18i/logs/summary.txt
