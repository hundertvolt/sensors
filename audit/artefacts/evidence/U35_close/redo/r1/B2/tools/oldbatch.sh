#!/bin/bash
# oldbatch.sh FILE[@DEVICE]...: batch.sh's runs with the committed sources of oldsrc/ ahead of src/ (the red probe).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
MP=$S/tc-int/micropython/ports/unix/build-standard/micropython
export TZ=UTC MICROPYPATH=$S/u35r/r1/B2/oldsrc:build/generated_src:src:tests:frozen_modules:.frozen
for spec in "$@"; do
  f=${spec%@*}; d=""; [ "$spec" != "$f" ] && d=${spec#*@}
  out=$(env ${d:+TEST_DEVICE=$d} timeout 1200 $MP -X heapsize=16M "$f" 2>&1); r=$?
  echo "== $spec rc=$r: $(echo "$out" | grep -E '[0-9]+/[0-9]+ passed' | tail -1)"
  echo "$out" | grep '^FAIL' | head -20
done
