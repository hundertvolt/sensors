#!/bin/bash
# both.sh FILE[@DEVICE]...: each file at stage e and at 32768, one summary line each (cwd = worktree).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
MP=$S/tc-int/micropython/ports/unix/build-standard/micropython
export TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen
rc=0
for spec in "$@"; do
  f=${spec%@*}; d=""; [ "$spec" != "$f" ] && d=${spec#*@}
  for stage in e f; do
    if [ $stage = e ]; then args=("$f"); else args=(tests/_threshold_runner.py "$f" 32768); fi
    out=$(env ${d:+TEST_DEVICE=$d} timeout 1200 $MP -X heapsize=16M "${args[@]}" 2>&1); r=$?
    echo "== $spec [$stage] rc=$r: $(echo "$out" | grep -E '[0-9]+/[0-9]+ passed' | tail -1)"
    if [ $r -ne 0 ]; then rc=1; echo "$out" | grep -E '^FAIL' | head -10; fi
    echo "$out" | grep -E 'MemoryError|memory allocation failed' | head -3
  done
done
echo "both rc=$rc"; exit $rc
