#!/bin/bash
# The three changed files: -1 and 32768 through the real runners, then the coverage runner; <=4 at a time.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; W=$S/wt-u13int; V=$S/u13fix
U=/root/pico-toolchain/micropython/ports/unix
cd $W
run() { # tag binary args...
  local tag=$1 bin=$2; shift 2; local t0=$(date +%s)
  unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen timeout 900 $bin -X heapsize=16M $*" > $V/logs/f_$tag.log 2>&1
  echo "$tag rc=$? $(( $(date +%s)-t0 ))s $(grep -E '[0-9]+/[0-9]+ passed' $V/logs/f_$tag.log | tail -1) ME=$(grep -cE 'MemoryError|memory allocation failed' $V/logs/f_$tag.log)"
}
F1=tests/test_digital_twin_uart_link.py; F2=tests/test_bus_hazard_multi_device.py; F3=tests/test_bus_hazard_generated.py
run uart_m1 $U/build-standard/micropython $F1 &
run uart_gc $U/build-standard/micropython tests/_threshold_runner.py $F1 32768 &
run multi_m1 $U/build-standard/micropython $F2 &
run multi_gc $U/build-standard/micropython tests/_threshold_runner.py $F2 32768 &
wait
run gen_m1 $U/build-standard/micropython $F3 &
run gen_gc $U/build-standard/micropython tests/_threshold_runner.py $F3 32768 &
run multi_cov $U/build-settrace/micropython tests/_coverage_runner.py $F2 $V/logs/cov_multi.json &
run gen_cov $U/build-settrace/micropython tests/_coverage_runner.py $F3 $V/logs/cov_gen.json &
wait
run uart_cov $U/build-settrace/micropython tests/_coverage_runner.py $F1 $V/logs/cov_uart.json
