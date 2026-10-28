#!/usr/bin/env bash
# usage: hammer.sh <label> <binary> <stage: e|f> [extra MicroPython file args...]; runs the lwIP host hammer once, logs to u21s_runs/<label>.log
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
label="$1"; bin="$2"; stage="$3"; file="${4:-tests/lwip_host/test_modlwip_eagain.py}"
if [ "$stage" = "f" ]; then args=(tests/_threshold_runner.py "$file" 32768); else args=("$file"); fi
echo "| running | lane S (fg) $$ | wt-u21s | lwIP host run $label ($stage stage, $(basename "$(dirname "$bin")")) | $(date -u +%T) |" >> $S/u21/RUNS.md
cd $S/wt-u21s
echo "loadavg at start: $(cat /proc/loadavg); flock holders: $(pgrep -fa 'flock /tmp/sensors-audit-toolchain.lock' | grep -v pgrep | sed 's/ .*toolchain-dir / dir /' | tr '\n' ';')" > $S/u21s_runs/$label.load
start=$(date +%s.%N)
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen nice -n 19 timeout 300 '$bin' -X heapsize=16M ${args[*]}" > $S/u21s_runs/$label.log 2>&1
rc=$?
end=$(date +%s.%N)
wall=$(echo "$end - $start" | bc)
sed -i "s/^| running | lane S (fg) $$ |/| done rc=$rc wall=${wall}s $(date -u +%T) | lane S (fg) $$ |/" $S/u21/RUNS.md
echo "loadavg at end: $(cat /proc/loadavg)" >> $S/u21s_runs/$label.load
echo "rc=$rc wall=${wall}s" >> $S/u21s_runs/$label.log
cat $S/u21s_runs/$label.load
tail -25 $S/u21s_runs/$label.log
