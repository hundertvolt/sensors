#!/bin/bash
# Sequential device-file timing: after (wt-u22p @ 7b548af) and before (scratch: the merge base's scenario library).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
OUT=$S/u22p_runs/batch_summary.txt
: > $OUT
run() {  # tree stage name label
  tree=$1; st=$2; name=$3; label=$4
  BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
  case $st in
    e) ARGS="tests/$name.py";;
    f) ARGS="tests/_threshold_runner.py tests/$name.py 32768";;
    cov) BIN=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython; ARGS="tests/_coverage_runner.py tests/$name.py $S/u22p_runs/cov_${label}_$name.json";;
  esac
  log=$S/u22p_runs/batch_${label}_${st}_$name.log
  cd $tree
  start=$(date +%s.%N)
  unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 $BIN -X heapsize=16M $ARGS" > $log 2>&1
  rc=$?
  wall=$(echo "$(date +%s.%N) - $start" | bc)
  me=$(grep -c -i "MemoryError\|memory allocation failed" $log)
  echo "$label $st $name rc=$rc wall=${wall}s memerr_lines=$me $(tail -1 $log)" >> $OUT
}
for st in e f cov; do
  for d in wozi dev arzi grkizi klkizi schlafzi; do run $S/wt-u22p $st test_sensortask_$d after; done
done
for st in e f; do
  for n in test_bus_hazard_generated test_ticks_rollover test_reset_call_site_invariant; do run $S/wt-u22p $st $n after; done
done
for st in e f cov; do
  for d in wozi dev arzi grkizi klkizi schlafzi; do run $S/u22p_before $st test_sensortask_$d before; done
done
echo "BATCH DONE $(date +%H:%M:%S)" >> $OUT
