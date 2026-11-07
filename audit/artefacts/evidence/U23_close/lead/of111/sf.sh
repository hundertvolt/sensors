#!/bin/bash
# sf.sh <phase> <stage e|f> <label> <script> [args...]: like one.sh, for a scratch driver script.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/of111
phase=$1; stage=$2; label=$3; shift 3; MP=/root/pico-toolchain/micropython/ports/unix
cd $S/wt-u23o || exit 2
case $stage in
  e) cmd=("$MP/build-standard/micropython" -X heapsize=16M "$@") ;;
  f) cmd=("$MP/build-standard/micropython" -X heapsize=16M tests/_threshold_runner.py "$@" 32768) ;;
esac
key="$phase-$stage-$label"; log="$O/logs/${phase}_${stage}_$label.txt"
python3 $O/runs.py start "$key" "wt-u23o @ $(git rev-parse --short HEAD)+wip" "$label ($stage, $phase): ${*##*/}, own unshare -n, TZ=UTC, nice 19 > u23/of111/logs"
start=$(date +%s.%N)
TZ=UTC MICROPYPATH="${PREFIX:+$PREFIX:}build/generated_src:src:tests:frozen_modules:.frozen" unshare -n $S/u22/api5/ns.sh nice -n 19 timeout 300 "${cmd[@]}" > "$log" 2>&1
rc=$?
wall=$(python3 -c "import time; print(f'{time.time() - $start:.1f}')")
mem=$(grep -c -E "MemoryError|memory allocation failed" "$log")
summary=$(grep -E "[0-9]+/[0-9]+ passed" "$log" | tail -1)
printf '%s\t%s\t%s\trc=%s\t%ss\tmem=%s\t%s\n' "$phase" "$label" "$stage" "$rc" "$wall" "$mem" "$summary" >> $O/results.tsv
python3 $O/runs.py done "$key" "rc=$rc ${wall}s mem=$mem ($summary)"
echo "$phase $label $stage rc=$rc ${wall}s mem=$mem $summary"
