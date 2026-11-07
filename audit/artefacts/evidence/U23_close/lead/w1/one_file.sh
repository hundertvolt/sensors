#!/bin/bash
# one_file.sh <test file>: run one MicroPython test file at gc -1 then 32768 (never both at once), each in its own netns,
# from wt-u23api; logs under u23/w1/mp/, one verdict line per stage appended to u23/w1/mp/verdicts.txt.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/w1/mp
f=${1:?file}; tag=$(basename "$f" .py)
cd $S/wt-u23api || exit 2
B=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
[[ "$f" == tests/lwip_host/* ]] && B=/root/pico-toolchain/micropython/ports/unix/build-lwip/micropython
for stage in m1 t32768; do
  if [ $stage = m1 ]; then cmd=("$f"); else cmd=(tests/_threshold_runner.py "$f" 32768); fi
  log=$O/$tag.$stage.log; t0=$(date +%s.%N)
  unshare -n $S/u22/api5/ns.sh env TZ=UTC MICROPYPATH="build/generated_src:src:tests:frozen_modules:.frozen" nice -n 19 timeout --kill-after=10 300 "$B" -X heapsize=16M "${cmd[@]}" > "$log" 2>&1
  rc=$?; wall=$(python3 -c "import sys;print(f'{float(sys.argv[2])-float(sys.argv[1]):.1f}')" $t0 $(date +%s.%N))
  sum=$(grep -E '^[0-9]+/[0-9]+ passed' "$log" | tail -1)
  mem=$(grep -c -E 'MemoryError|memory allocation failed' "$log")
  v=FAIL; if [ -n "$sum" ] && [ "$mem" = 0 ] && [ "$rc" = 0 ]; then n=${sum%%/*}; r=${sum#*/}; r=${r%% *}; [ "$n" = "$r" ] && v=PASS; fi
  echo "$v $f $stage rc=$rc wall=${wall}s mem=$mem [$sum]" >> $O/verdicts.txt
done
