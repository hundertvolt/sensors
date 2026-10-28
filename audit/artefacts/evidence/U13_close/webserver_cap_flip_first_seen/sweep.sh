#!/bin/bash
# Runs every tests/test_*.py once per GC stage, one at a time; one result line per file and stage.
cd /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u13i
OUT=$1; shift
: > $OUT
MP=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
for f in "$@"; do
  for stage in -1 32768; do
    if [ "$stage" = -1 ]; then cmd=($MP -X heapsize=16M $f); else cmd=($MP -X heapsize=16M tests/_threshold_runner.py $f $stage); fi
    log=$(TZ=UTC MICROPYPATH="build/generated_src:src:tests:frozen_modules:.frozen" nice -n 19 timeout 300 "${cmd[@]}" 2>&1); rc=$?
    summary=$(echo "$log" | grep -E '^[0-9]+/[0-9]+ passed' | tail -1)
    mem=$(echo "$log" | grep -c -E 'MemoryError|memory allocation failed')
    fails=$(echo "$log" | grep '^FAIL' | tr '\n' ' ')
    echo "$f stage=$stage rc=$rc mem=$mem ${summary:-NO-SUMMARY} $fails" >> $OUT
  done
done
echo DONE >> $OUT
