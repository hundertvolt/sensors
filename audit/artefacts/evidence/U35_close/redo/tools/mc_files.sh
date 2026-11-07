#!/bin/bash
# mc_files.sh OUTDIR FILE[:DEVICE]...: each MicroPython test file at -1 and 32768 with the shared binary, one at a time.
OUT="$1"; shift; mkdir -p "$OUT"
B=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
for spec in "$@"; do
  f="${spec%%:*}"; d=""; [ "$spec" != "$f" ] && d="${spec#*:}"
  for st in -1 32768; do
    tag="$(basename "$f" .py)${d:+_$d}_$st"
    if [ "$st" = -1 ]; then args="$f"; else args="tests/_threshold_runner.py $f 32768"; fi
    t0=$(date +%s.%N)
    if [ -n "$d" ]; then env TEST_DEVICE="$d" TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen $B -X heapsize=16M $args > "$OUT/$tag.log" 2>&1
    else env -u TEST_DEVICE TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen $B -X heapsize=16M $args > "$OUT/$tag.log" 2>&1; fi
    rc=$?; t1=$(date +%s.%N)
    m=$(grep -c -E 'MemoryError|memory allocation failed' "$OUT/$tag.log")
    printf '%s rc=%s %.1fs markers=%s %s\n' "$tag" "$rc" "$(echo "$t1 - $t0" | bc)" "$m" "$(grep -E 'passed|failed' "$OUT/$tag.log" | tail -1)" >> "$OUT/summary.txt"
  done
done
