#!/bin/bash
# b4x_two_stages.sh [DEVICE] TESTFILE...: each test file at GC -1 and at 32768, full output; RC and memory-marker lines last.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
BIN=$S/tc-int/micropython/ports/unix/build-standard/micropython
rc=0
for f in "$@"; do
  for stage in -1 32768; do
    if [ "$stage" = -1 ]; then args=("$f"); else args=(tests/_threshold_runner.py "$f" 32768); fi
    out=$(TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen "$BIN" -X heapsize=16M "${args[@]}" 2>&1); r=$?
    echo "$out" | grep -v '^PASS'
    m=$(echo "$out" | grep -c -i -e 'MemoryError' -e 'memory allocation failed')
    echo "FILE $f STAGE $stage RC=$r MEM=$m"
    [ "$r" = 0 ] && [ "$m" = 0 ] || rc=1
  done
done
exit $rc
