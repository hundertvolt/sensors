#!/usr/bin/env bash
# probe_run.sh TAG THRESHOLD READERS LOAD_S PATH: one bounded heap probe; console to probe_TAG.out in the scratchpad.
SP=/tmp/claude-1000/-home-nico-programming-sensors/df4ef362-6c60-42fd-8808-45490a5e4ce4/scratchpad
source /home/nico/programming/sensors-bench/audit/artefacts/evidence/U35_close/redo/hw_round1/logs/round1.env
TAG=$1 TH=$2 R=$3 D=$4 P=$5 CH=${6:-0} SH=${7:-0}
sed "s/^THRESHOLD = None/THRESHOLD = $TH/; s/^END_S = 240/END_S = $((D+90))/; s/^CHUNK = 0/CHUNK = $CH/; s/^SHARE_MS = 0/SHARE_MS = $SH/" $SP/heap_probe.py > $SP/heap_probe_$TAG.py
OUT=$SP/probe_$TAG.out
timeout -k 5 $((D+170)) /home/nico/programming/sensors-bench/.venv/bin/mpremote connect /dev/ttyACM0 run $SP/heap_probe_$TAG.py > $OUT 2>&1 &
M=$!
for i in $(seq 1 110); do grep -q LOAD_NOW $OUT 2>/dev/null && break; kill -0 $M 2>/dev/null || break; sleep 1; done
if grep -q LOAD_NOW $OUT; then
  for i in $(seq 1 60); do curl -s -m 3 -o /dev/null http://$DUT_IP/measurements && break; sleep 1; done
  python3 $SP/status_load.py $R $D $P
else echo "no LOAD_NOW"; tail -5 $OUT | cut -c1-200; fi
for i in $(seq 1 60); do grep -aq "^DONE" $OUT && break; sleep 1; done; pkill -P $M; kill $M 2>/dev/null; wait $M 2>/dev/null
grep -aE '^HEAP (BASELINE|END)|^DONE' $OUT | cut -c1-110
echo fails $(grep -ac '^HEAP FAIL' $OUT)
python3 $SP/heapmap.py $OUT | grep -E '^(BASELINE|FAIL_FLUSH1 |END)' | cut -c1-120
