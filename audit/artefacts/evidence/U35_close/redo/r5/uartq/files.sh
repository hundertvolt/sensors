#!/bin/bash
# files.sh FILE...: each named tests/ module at stage e, then stage f; one summary line per run.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
rc=0
for f in "$@"; do
  for g in e f; do
    out=$(timeout 1800 "$S/u35r/r5/uartq/t.sh" $g "$f" 2>&1); r=$?
    echo "== $f $g rc=$r: $(echo "$out" | grep -E '[0-9]+/[0-9]+ passed' | tail -1)"
    echo "$out" | grep -E "^(FAIL|ABORT)" -A12 | head -60
    echo "$out" | grep -nE "MemoryError|memory allocation failed" | head -5
    [ $r -ne 0 ] && rc=1
  done
done
exit $rc
