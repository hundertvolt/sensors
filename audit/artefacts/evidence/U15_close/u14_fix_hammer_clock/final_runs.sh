#!/bin/bash
# The verdict runs on the final file, one interpreter at a time, nice 19, network-namespaced.
cd /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u14fix || exit 1
STD=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
TRC=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython
MP=build/generated_src:src:tests:frozen_modules:.frozen
OUT=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u14fix/evidence/final
one() { # name, then the command
    name=$1; shift; s=$(date +%s)
    TZ=UTC nice -n 19 unshare -n "$@" > $OUT/$name.log 2>&1; rc=$?
    mem=$(grep -c -i -E "MemoryError|memory allocation failed" $OUT/$name.log)
    echo "$name rc=$rc $(( $(date +%s)-s ))s memerr_lines=$mem | $(tail -1 $OUT/$name.log)"
}
for i in 1 2 3; do one gcdefault_$i env MICROPYPATH=$MP $STD -X heapsize=16M tests/test_uart_comm_hazard.py; done
for i in 1 2 3; do one gc32768_$i env MICROPYPATH=$MP $STD -X heapsize=16M tests/_threshold_runner.py tests/test_uart_comm_hazard.py 32768; done
for i in 1 2 3; do one coverage_$i env MICROPYPATH=$MP $TRC -X heapsize=16M tests/_coverage_runner.py tests/test_uart_comm_hazard.py $OUT/coverage_$i.json; done
one oldclock_gcdefault env MICROPYPATH=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u14fix/oldclock:$MP $STD -X heapsize=16M /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u14fix/oldclock/test_uart_comm_hazard.py
one oldclock_coverage env MICROPYPATH=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u14fix/oldclock:$MP $TRC -X heapsize=16M tests/_coverage_runner.py /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u14fix/oldclock/test_uart_comm_hazard.py $OUT/oldclock_coverage.json
echo ALLDONE
