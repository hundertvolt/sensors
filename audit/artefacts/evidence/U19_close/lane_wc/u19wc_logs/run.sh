#!/bin/bash
# usage: run.sh <binary: standard|settrace> <stage: e|f|cov> <test file> <log>
cd /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u19wc
bin=/root/pico-toolchain/micropython/ports/unix/build-$1/micropython
case "$2" in
  e) args="$3" ;;
  f) args="tests/_threshold_runner.py $3 32768" ;;
  cov) args="tests/_coverage_runner.py $3 /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u19wc_logs/cov.json" ;;
esac
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 $bin -X heapsize=16M $args" > "$4" 2>&1
rc=$?
end=$(date +%s.%N)
echo "exit=$rc wall=$(echo "$end - $start" | bc) s" >> "$4"
