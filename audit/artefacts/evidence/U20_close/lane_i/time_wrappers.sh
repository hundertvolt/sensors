#!/bin/bash
# usage: time_wrappers.sh <tree> <outdir> <label> [devices...]
tree="$1"; out="$2"; label="$3"; shift 3
devices="${*:-arzi dev grkizi klkizi schlafzi wozi}"
MP=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
MPS=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython
mkdir -p "$out"
cd "$tree" || exit 2
for d in $devices; do
  f="tests/test_sensortask_${d}.py"
  for stage in gc-1 gc32768 settrace; do
    log="$out/${label}_${d}_${stage}.log"
    case $stage in
      gc-1) cmd="$MP -X heapsize=16M $f" ;;
      gc32768) cmd="$MP -X heapsize=16M tests/_threshold_runner.py $f 32768" ;;
      settrace) cmd="$MPS -X heapsize=16M tests/_coverage_runner.py $f $out/${label}_${d}_cov.json" ;;
    esac
    start=$(date +%s.%N)
    unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 600 $cmd" > "$log" 2>&1
    rc=$?
    end=$(date +%s.%N)
    secs=$(echo "$end - $start" | bc)
    passed=$(grep -c '^PASS ' "$log"); failed=$(grep -c '^FAIL ' "$log")
    mem=$(grep -c 'MemoryError\|memory allocation failed' "$log")
    echo "$label $d $stage rc=$rc secs=$secs pass=$passed fail=$failed mem=$mem tail=$(tail -1 "$log" | cut -c1-120)" | tee -a "$out/summary.txt"
  done
done
