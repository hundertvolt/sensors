#!/bin/bash
# one.sh <phase> <stage e|f|cov> <test_x>: one MicroPython test file in wt-u23o, own netns, TZ=UTC, nice 19; appends
# phase, file, stage, rc, wall, memory-marker count and the summary line to results.tsv. RUNS.md line around it.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/of111
phase=$1; stage=$2; t=$3; MP=/root/pico-toolchain/micropython/ports/unix
WT=${WT:-$S/wt-u23o}; LANE=${LANE:-a}
cd "$WT" || exit 2
case $stage in
  e) cmd=("$MP/build-standard/micropython" -X heapsize=16M "tests/$t.py") ;;
  f) cmd=("$MP/build-standard/micropython" -X heapsize=16M tests/_threshold_runner.py "tests/$t.py" 32768) ;;
  cov) cmd=("$MP/build-settrace/micropython" -X heapsize=16M tests/_coverage_runner.py "tests/$t.py" "$O/cov_${LANE}_$t.json") ;;
esac
key="$phase-$stage-$t-$LANE"; log="$O/logs/${phase}_${stage}_$t.txt"
python3 $O/runs.py start "$key" "$(basename $WT) (wt-u23o @ 202a118 + staged; wt2 its file copy)" "$t ($stage, $phase), own unshare -n, TZ=UTC, nice 19 > u23/of111/logs"
start=$(date +%s.%N)
TZ=UTC MICROPYPATH="${PREFIX:+$PREFIX:}build/generated_src:src:tests:frozen_modules:.frozen" unshare -n $S/u22/api5/ns.sh nice -n 19 timeout 300 "${cmd[@]}" > "$log" 2>&1
rc=$?
wall=$(python3 -c "import time; print(f'{time.time() - $start:.1f}')")
mem=$(grep -c -E "MemoryError|memory allocation failed" "$log")
summary=$(grep -E "[0-9]+/[0-9]+ passed" "$log" | tail -1)
printf '%s\t%s\t%s\trc=%s\t%ss\tmem=%s\t%s\n' "$phase" "$t" "$stage" "$rc" "$wall" "$mem" "$summary" >> $O/results.tsv
python3 $O/runs.py done "$key" "rc=$rc ${wall}s mem=$mem ($summary)"
echo "$phase $t $stage rc=$rc ${wall}s mem=$mem $summary"
