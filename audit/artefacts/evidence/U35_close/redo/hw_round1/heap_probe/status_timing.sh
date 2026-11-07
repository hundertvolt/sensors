#!/usr/bin/env bash
# status_timing.sh OUT [READERS]: one bounded run of status_timing.py with READERS (default 3) on /status for 60 s, then the closing kicked reset. No flash write.
H=/home/nico/programming/sensors-bench/audit/artefacts/evidence/U35_close/redo/hw_round1
source $H/logs/round1.env
OUT=$1
READERS=${2:-3}
: > "$OUT"
timeout -k 5 300 /home/nico/programming/sensors-bench/.venv/bin/mpremote connect "$(ls /dev/serial/by-id/*MicroPython*)" run $H/heap_probe/status_timing.py >> "$OUT" 2>&1 &
M=$!
for _ in $(seq 1 120); do grep -aq LOAD_NOW "$OUT" && break; kill -0 $M 2>/dev/null || break; sleep 1; done
if grep -aq LOAD_NOW "$OUT"; then python3 $H/heap_probe/status_load.py "$READERS" 60 /status; else echo "no LOAD_NOW"; tail -5 "$OUT" | cut -c1-200; fi
for _ in $(seq 1 60); do grep -aq '^DONE' "$OUT" && break; sleep 1; done
kill $M 2>/dev/null; wait $M 2>/dev/null
echo "memfails $(grep -acE 'memory allocation failed|MemoryError' "$OUT")"
cd /home/nico/programming/sensors-bench && .venv/bin/python tests_hardware/kick_then_reset.py
