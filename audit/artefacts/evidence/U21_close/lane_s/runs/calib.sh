#!/usr/bin/env bash
# usage: calib.sh <label> <stage: e|f>; the calibration runner on u21tc-s's build-lwip, load logged.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
label="$1"; stage="$2"; bin=$S/u21tc-s/micropython/ports/unix/build-lwip/micropython
extra=""; [ "$stage" = "f" ] && extra=32768
echo "| running | lane S (fg) $$ | wt-u21s | lwIP host calibration $label ($stage stage) | $(date -u +%T) |" >> $S/u21/RUNS.md
holders="$(pgrep -fa 'flock /tmp/sensors-audit-toolchain.lock' | grep -v pgrep | grep -o 'u21tc-[a-z]*\|pytest .*-k real' | sort -u | tr '\n' ' ')"
echo "loadavg at start: $(cat /proc/loadavg); flock holders/waiters: ${holders:-none}" > $S/u21s_runs/$label.load
cd $S/wt-u21s
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen nice -n 19 timeout 300 '$bin' -X heapsize=16M $S/u21/s_probe/calibrate.py $extra" > $S/u21s_runs/$label.log 2>&1
rc=$?
echo "loadavg at end: $(cat /proc/loadavg)" >> $S/u21s_runs/$label.load
sed -i "s/^| running | lane S (fg) $$ |/| done rc=$rc $(date -u +%T) | lane S (fg) $$ |/" $S/u21/RUNS.md
cat $S/u21s_runs/$label.log $S/u21s_runs/$label.load; echo "rc=$rc"
