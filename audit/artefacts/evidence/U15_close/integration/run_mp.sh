#!/usr/bin/env bash
# usage: run_mp.sh <test_basename> <stage: -1|32768>
set -u
W=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u15int
N=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u15int_notes
B=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
t=$1; st=$2
if [ "$st" = "-1" ]; then target="tests/$t.py"; else target="tests/_threshold_runner.py tests/$t.py $st"; fi
log=$N/mp_${t}_gc${st}.log
cd $W
nice -n 19 unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen timeout 900 stdbuf -oL -eL $B -X heapsize=16M $target" > $log 2>&1
ec=$?
me=$(grep -cE "MemoryError|memory allocation failed" $log)
echo "$t gc=$st exit=$ec memerr=$me :: $(grep -E '[0-9]+/[0-9]+ (passed|tests)' $log | tail -1)"
