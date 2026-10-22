#!/bin/bash
# run1.sh <worktree> <outdir> <files...>: each file at gc -1 then 32768, sequentially, in one netns.
W=$1; O=$2; shift 2; mkdir -p $O; cd $W
B=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
for f in "$@"; do n=$(basename $f .py)
  for st in d t; do
    if [ $st = d ]; then cmd="$f"; else cmd="tests/_threshold_runner.py $f 32768"; fi
    s=$(date +%s.%N)
    unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen nice -n 19 timeout 600 $B -X heapsize=16M $cmd" > $O/${n}_$st.log 2>&1; rc=$?
    e=$(date +%s.%N); echo "$n $st rc=$rc $(echo "$e - $s" | bc) s $(tail -1 $O/${n}_$st.log | cut -c1-80) mem=$(grep -c -E 'MemoryError|memory allocation failed' $O/${n}_$st.log)" >> $O/summary.txt
  done
done
echo done >> $O/summary.txt
