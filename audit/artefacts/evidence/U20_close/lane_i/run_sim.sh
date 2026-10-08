#!/bin/bash
# usage: run_sim.sh <outdir> <label> <stage gc-1|gc32768> files...
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
WT=$S/wt-u20i
out="$1"; label="$2"; stage="$3"; shift 3
MP=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
mkdir -p "$out"
cd "$WT" || exit 2
for f in "$@"; do
  base=$(basename "$f" .py)
  log="$out/${label}_${base}_${stage}.log"
  case $stage in
    gc-1) cmd="$MP -X heapsize=16M $f" ;;
    gc32768) cmd="$MP -X heapsize=16M tests/_threshold_runner.py $f 32768" ;;
  esac
  start=$(date +%s.%N)
  unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='$S/u20i_sim/gen:$S/u20i_sim/src:build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 600 $cmd" > "$log" 2>&1
  rc=$?
  secs=$(echo "$(date +%s.%N) - $start" | bc)
  passed=$(grep -c '^PASS ' "$log"); failed=$(grep -c '^FAIL ' "$log"); mem=$(grep -c 'MemoryError\|memory allocation failed' "$log")
  echo "$label $base $stage rc=$rc secs=$secs pass=$passed fail=$failed mem=$mem tail=$(tail -1 "$log" | cut -c1-120)" | tee -a "$out/summary.txt"
done
