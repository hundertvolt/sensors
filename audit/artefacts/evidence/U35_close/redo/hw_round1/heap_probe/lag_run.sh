#!/usr/bin/env bash
# lag_run.sh READERS LOAD_S: one bounded lag_probe.py session under /status load; console to lag_out.txt in the scratchpad. No flash write.
SP=/tmp/claude-1000/-home-nico-programming-sensors/df4ef362-6c60-42fd-8808-45490a5e4ce4/scratchpad
source /home/nico/programming/sensors-bench/audit/artefacts/evidence/U35_close/redo/hw_round1/logs/round1.env
R=$1 D=$2 OUT=$SP/lag_out_r$R.txt
timeout -k 5 420 /home/nico/programming/sensors-bench/.venv/bin/mpremote connect /dev/ttyACM0 run $SP/lag_probe.py > $OUT 2>&1 &
M=$!
for i in $(seq 1 240); do grep -aq LOAD_NOW $OUT 2>/dev/null && break; kill -0 $M 2>/dev/null || break; sleep 1; done
if grep -aq LOAD_NOW $OUT; then python3 $SP/status_load.py $R $D /status; else echo "no LOAD_NOW"; tail -5 $OUT | cut -c1-200; fi
for i in $(seq 1 90); do grep -aq "^DONE" $OUT && break; sleep 1; done
pkill -P $M; kill $M 2>/dev/null; wait $M 2>/dev/null
grep -aE '^LAG|^DONE' $OUT | cut -c1-200
echo "uart_errors $(grep -ac 'UART error' $OUT) resyncs $(grep -ac 'Resyncing' $OUT) memfails $(grep -acE 'memory allocation failed' $OUT)"
