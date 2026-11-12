#!/bin/bash
# t1.sh FILE... : each test file at the -1 stage only (red checks); FAIL lines and the summary.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
MP=$S/tc-int/micropython/ports/unix/build-standard/micropython
export TZ=UTC MICROPYPATH=${MPATH:-build/generated_src:src:tests:frozen_modules:.frozen}
for f in "$@"; do
  out=$(timeout 900 "$MP" -X heapsize=16M "$f" 2>&1); rc=$?
  echo "== $f rc=$rc: $(printf '%s\n' "$out" | grep -E '[0-9]+/[0-9]+ passed' | tail -1)"
  printf '%s\n' "$out" | grep -E -A4 '^(FAIL|ABORT)' | head -60
done
