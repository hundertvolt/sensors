#!/bin/bash
# usage: measure.sh <tree> <outdir> <modes: plain,gc,cov> <test files...>
# Runs each test file at the requested modes, serially, at nice 19, in its own network namespace.
TREE=$1; OUT=$2; MODES=$3; shift 3
MP=/root/pico-toolchain/micropython/ports/unix
mkdir -p "$OUT"
cd "$TREE" || exit 1
for f in "$@"; do
  base=$(basename "$f" .py)
  for mode in ${MODES//,/ }; do
    case $mode in
      plain) bin=$MP/build-standard/micropython; args="$f";;
      gc) bin=$MP/build-standard/micropython; args="tests/_threshold_runner.py $f 32768";;
      cov) bin=$MP/build-settrace/micropython; args="tests/_coverage_runner.py $f $OUT/${base}.cov.json";;
    esac
    log="$OUT/${base}.${mode}.log"
    start=$(date +%s.%N)
    unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 900 $bin -X heapsize=16M $args" > "$log" 2>&1
    rc=$?
    end=$(date +%s.%N)
    el=$(echo "$end - $start" | bc)
    summ=$(grep -E '[0-9]+/[0-9]+ passed|FAIL' "$log" | tail -1)
    mem=$(grep -c -E 'MemoryError|memory allocation failed' "$log")
    echo "$base $mode rc=$rc elapsed=${el}s mem_markers=$mem :: $summ" | tee -a "$OUT/summary.txt"
  done
done
