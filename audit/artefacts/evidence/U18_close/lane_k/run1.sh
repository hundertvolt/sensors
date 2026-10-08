#!/bin/bash
# usage: run1.sh <stage: std|thr|cov> <test file rel> <outfile>
SP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $SP/wt-u18k || exit 9
stage=$1; f=$2; out=$3
case $stage in
  std) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="$f";;
  thr) BIN=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython; ARGS="tests/_threshold_runner.py $f 32768";;
  cov) BIN=/root/pico-toolchain/micropython/ports/unix/build-settrace/micropython; ARGS="tests/_coverage_runner.py $f $SP/u18k_runs/cov_$(basename $f .py).json";;
esac
unshare -n bash -c "ip link set lo up; export TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen'; s=\$(date +%s.%N); nice -n 19 timeout 300 $BIN -X heapsize=16M $ARGS > $out 2>&1; rc=\$?; e=\$(date +%s.%N); echo \"rc=\$rc time=\$(echo \"\$e - \$s\" | bc)\""
echo "summary: $(tail -1 $out)"; echo "memgate: $(grep -c -E 'MemoryError|memory allocation failed' $out)"
