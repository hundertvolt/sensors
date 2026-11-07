#!/bin/bash
# Runs lane B's MicroPython test files at gc.threshold -1 and 32768, each in its own network namespace.
cd "$(dirname "$0")/wt-u15b" || exit 1
OUT=../u15b_runs; mkdir -p "$OUT"
MP=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
for f in "$@"; do
  for stage in -1 32768; do
    if [ "$stage" = -1 ]; then target="tests/$f.py"; else target="tests/_threshold_runner.py tests/$f.py 32768"; fi
    unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 900 $MP -X heapsize=16M $target" > "$OUT/$f.$stage.txt" 2>&1
    echo "$f [$stage] rc=$? $(tail -1 "$OUT/$f.$stage.txt") mem=$(grep -c 'MemoryError\|memory allocation failed' "$OUT/$f.$stage.txt")"
  done
done
