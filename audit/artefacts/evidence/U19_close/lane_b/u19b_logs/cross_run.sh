#!/bin/bash
# Runs each named tests/ file once at gc stage -1 in its own network namespace; one summary line per file.
cd /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u19b || exit 1
L=../u19b_logs/cross
mkdir -p $L
MP=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
for f in "$@"; do
  s=$(date +%s.%N)
  unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 600 $MP -X heapsize=16M tests/$f.py" > $L/$f.txt 2>&1
  rc=$?
  echo "$f rc=$rc t=$(echo "$(date +%s.%N) - $s" | bc) $(tail -1 $L/$f.txt) mem=$(grep -c -E 'MemoryError|memory allocation failed' $L/$f.txt)" >> $L/summary.txt
done
echo DONE >> $L/summary.txt
