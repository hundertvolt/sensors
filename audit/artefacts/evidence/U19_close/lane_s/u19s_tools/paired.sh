#!/bin/bash
# Paired before/after timing of one test file at one stage: before = HEAD's test + driver via an overlay dir.
# usage: paired.sh <test basename> <driver basename> <stage e|f> <passes>
set -u
SP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
WT=$SP/wt-u19s
OV=$SP/u19s_tools/overlay_head
LOGS=$SP/u19s_logs
t=$1; drv=$2; stage=$3; passes=$4
mkdir -p "$OV"
git -C "$WT" show "HEAD:tests/$t.py" > "$OV/$t.py"
git -C "$WT" show "HEAD:src/$drv.py" > "$OV/$drv.py"
STD=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
for pass in $(seq 1 "$passes"); do
  if [ "$stage" = f ]; then target="tests/_threshold_runner.py $OV/$t.py 32768"; else target="$OV/$t.py"; fi
  s=$(date +%s.%N)
  unshare -n bash -c "ip link set lo up; cd $WT; TZ=UTC MICROPYPATH='$OV:build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 $STD -X heapsize=16M $target" > "$LOGS/paired_before_${t}_${stage}_$pass.txt" 2>&1
  e=$(date +%s.%N)
  echo "before $t $stage pass$pass $(echo "$e - $s" | bc)s $(tail -1 "$LOGS/paired_before_${t}_${stage}_$pass.txt") load: $(cut -d' ' -f1 /proc/loadavg)"
  "$SP/u19s_tools/run.sh" "$stage" "$t" "paired_after$pass"
done
