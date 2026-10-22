#!/bin/bash
# usage: runtests.sh <outfile> test_a test_b ...  (run from the worktree)
out=$1; shift
: > "$out"
MP=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
for t in "$@"; do
  for stage in plain gc; do
    if [ $stage = plain ]; then args="tests/$t.py"; else args="tests/_threshold_runner.py tests/$t.py 32768"; fi
    start=$(date +%s)
    res=$(unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen nice -n 19 timeout 900 $MP -X heapsize=16M $args" 2>&1)
    rc=$?
    summary=$(echo "$res" | grep -E 'passed,' | tail -1)
    mem=$(echo "$res" | grep -c -E 'MemoryError|memory allocation failed')
    fails=$(echo "$res" | grep -E '^FAIL' | tr '\n' ' ')
    echo "$t [$stage] rc=$rc $(( $(date +%s)-start ))s :: $summary :: mem=$mem :: $fails" >> "$out"
    if [ $rc -ne 0 ] || [ "$mem" != 0 ]; then echo "$res" | tail -40 > "$out.$t.$stage.log"; fi
  done
done
echo DONE >> "$out"
