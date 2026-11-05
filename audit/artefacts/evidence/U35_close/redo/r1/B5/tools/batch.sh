#!/bin/bash
# batch.sh FILE[@DEVICE]...: stage-e runs of several MicroPython test files, one summary line each (cwd = worktree).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
MP=$S/tc-int/micropython/ports/unix/build-standard/micropython
export TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen
rc=0
for spec in "$@"; do
  f=${spec%@*}; d=""; [ "$spec" != "$f" ] && d=${spec#*@}
  out=$(env ${d:+TEST_DEVICE=$d} timeout 1200 $MP -X heapsize=16M "$f" 2>&1); r=$?
  echo "== $spec rc=$r: $(echo "$out" | grep -E '[0-9]+/[0-9]+ passed' | tail -1)"
  if [ $r -ne 0 ]; then rc=1; echo "$out" | grep -v '^PASS' | grep -B2 -A12 'FAIL\|Error\|Traceback' | head -60; fi
done
echo "batch rc=$rc"; exit $rc
