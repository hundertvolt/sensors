#!/bin/bash
# t.sh FILE... : each test file at both GC stages (-1 and 32768) in the current worktree; summary lines only.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
MP=$S/tc-int/micropython/ports/unix/build-standard/micropython
export TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen
for f in "$@"; do
  for st in e f; do
    if [ $st = e ]; then out=$(timeout 900 "$MP" -X heapsize=16M "$f" 2>&1); rc=$?
    else out=$(timeout 900 "$MP" -X heapsize=16M tests/_threshold_runner.py "$f" 32768 2>&1); rc=$?; fi
    mem=$(printf '%s\n' "$out" | grep -c -E 'MemoryError|memory allocation failed')
    echo "== $f [$st] rc=$rc mem=$mem: $(printf '%s\n' "$out" | grep -E '[0-9]+/[0-9]+ passed' | tail -1)"
    printf '%s\n' "$out" | grep -E '^(FAIL|ERROR)|AssertionError|Traceback' | head -20
  done
done
