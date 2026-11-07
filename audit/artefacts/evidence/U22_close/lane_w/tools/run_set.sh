#!/bin/bash
# run_set.sh <stage e|f> <outdir> <files...>: runs each MicroPython test file once, sequentially, nice 19, own netns.
SP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $SP/wt-u22w || exit 2
stage=$1; out=$2; shift 2
mkdir -p "$out"
for f in "$@"; do
  name=$(basename "$f" .py)
  if [ "$stage" = f ]; then args="tests/_threshold_runner.py $f 32768"; else args="$f"; fi
  S=$(date +%s.%N)
  unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 /root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M $args" > "$out/${name}_$stage.log" 2>&1
  rc=$?
  E=$(date +%s.%N)
  printf '%s %s rc=%s wall=%.1f :: %s :: mem=%s unretrieved=%s\n' "$stage" "$name" "$rc" "$(echo "$E - $S" | bc)" "$(grep -E 'passed,' "$out/${name}_$stage.log" | tail -1)" "$(grep -c -i 'MemoryError\|memory allocation failed' "$out/${name}_$stage.log")" "$(grep -c 'UNRETRIEVED' "$out/${name}_$stage.log")" >> "$out/summary.txt"
done
echo "SET DONE $stage" >> "$out/summary.txt"
