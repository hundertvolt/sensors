#!/usr/bin/env bash
# status_timing.sh OUT: one bounded run of status_timing.py with 3 readers on /status for 60 s, then the closing kicked reset. No flash write.
H=/home/nico/programming/sensors-bench/audit/artefacts/evidence/U35_close/redo/hw_round1
source $H/logs/round1.env
OUT=$1
: > "$OUT"
timeout -k 5 300 /home/nico/programming/sensors-bench/.venv/bin/mpremote connect /dev/ttyACM0 run $H/heap_probe/status_timing.py >> "$OUT" 2>&1 &
M=$!
for _ in $(seq 1 120); do grep -aq LOAD_NOW "$OUT" && break; kill -0 $M 2>/dev/null || break; sleep 1; done
if grep -aq LOAD_NOW "$OUT"; then python3 $H/heap_probe/status_load.py 3 60 /status; else echo "no LOAD_NOW"; tail -5 "$OUT" | cut -c1-200; fi
for _ in $(seq 1 60); do grep -aq '^DONE' "$OUT" && break; sleep 1; done
kill $M 2>/dev/null; wait $M 2>/dev/null
echo "memfails $(grep -acE 'memory allocation failed|MemoryError' "$OUT")"
uv run --no-sync python $H/reset_and_kick.py
