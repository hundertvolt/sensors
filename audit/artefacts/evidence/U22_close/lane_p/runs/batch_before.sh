#!/bin/bash
# The before tree only: real copies of the device test files, so their own directory (sys.path[0]) is the scratch tests/.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
OUT=$S/u22p_runs/batch_before_summary.txt
: > $OUT
for st in e f cov; do
  for d in wozi dev arzi grkizi klkizi schlafzi; do
    name=test_sensortask_$d
    BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
    case $st in
      e) ARGS="tests/$name.py";;
      f) ARGS="tests/_threshold_runner.py tests/$name.py 32768";;
      cov) BIN=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython; ARGS="tests/_coverage_runner.py tests/$name.py $S/u22p_runs/cov_before2_$name.json";;
    esac
    log=$S/u22p_runs/batch2_before_${st}_$name.log
    cd $S/u22p_before
    start=$(date +%s.%N)
    unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 $BIN -X heapsize=16M $ARGS" > $log 2>&1
    rc=$?
    wall=$(echo "$(date +%s.%N) - $start" | bc)
    me=$(grep -c -i "MemoryError\|memory allocation failed" $log)
    f4=$(grep -c "notification_state_says_why" $log)
    echo "before $st $name rc=$rc wall=${wall}s memerr_lines=$me f4_lines=$f4 $(tail -1 $log)" >> $OUT
  done
done
echo "BATCH DONE $(date +%H:%M:%S)" >> $OUT
