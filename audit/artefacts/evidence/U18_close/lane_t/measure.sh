#!/bin/bash
# usage: measure.sh <label> <file...>   (run from the worktree root)
label=$1; shift
out=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u18t_work/$label
mkdir -p "$out"
STD=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
SET=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython
MP="build/generated_src:src:tests:frozen_modules:.frozen"
for f in "$@"; do
  base=$(basename "$f" .py)
  for mode in e f cov; do
    case $mode in
      e) cmd=("$STD" -X heapsize=16M "$f");;
      f) cmd=("$STD" -X heapsize=16M tests/_threshold_runner.py "$f" 32768);;
      cov) cmd=("$SET" -X heapsize=16M tests/_coverage_runner.py "$f" "$out/${base}_cov.json");;
    esac
    log="$out/${base}_${mode}.log"
    start=$(date +%s.%N)
    unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=$MP nice -n 19 timeout 600 ${cmd[*]}" > "$log" 2>&1
    rc=$?
    end=$(date +%s.%N)
    t=$(echo "$end - $start" | bc)
    summ=$(grep -E "[0-9]+/[0-9]+ passed" "$log" | tail -1)
    mem=$(grep -c -E "MemoryError|memory allocation failed" "$log")
    printf "%s\t%s\trc=%s\t%.1fs\tmem=%s\t%s\n" "$base" "$mode" "$rc" "$t" "$mem" "$summ" | tee -a "$out/summary.tsv"
  done
done
