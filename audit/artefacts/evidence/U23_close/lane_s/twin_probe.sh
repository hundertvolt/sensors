#!/bin/bash
# twin_probe.sh <device>: boots one twin as the live commands do (port 19490), runs the PUT probes below, stops it, prints its output.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $S/wt-u23s || exit 2
d=$1; P=19490; B=http://127.0.0.1:$P
rm -rf digital_twin/config
MICROPYPATH="build/generated_src:src:digital_twin:ext:build/generated_html/$d:.frozen" TZ=UTC nice -n 19 /root/pico-toolchain/micropython/ports/unix/build-standard/micropython digital_twin/run_generic_integration.py --module sensortask_$d --wiring-plan build/generated_src/sensortask_${d}_wiring_plan.json --device $d --host 127.0.0.1 --port $P --fram-state-path "" --scd30-state-path "" > /tmp/twin_probe_$d.log 2>&1 &
pid=$!
for i in $(seq 1 80); do curl -s -o /dev/null $B/ && break; sleep 0.25; done
sleep 3
echo "--- ResetErrors"; curl -s -X PUT -H 'Content-Type: application/json' -d '{"ResetErrors": true}' $B/status; echo
echo "--- page-like traffic: 6 parallel, then sequential"
curl -s -o /dev/null --parallel --parallel-max 6 $B/ $B/js/app.js $B/status $B/system $B/measurements $B/status
for u in / /js/app.js /status /system /measurements /sensors /status; do curl -s -o /dev/null $B$u; done
sleep 1
echo "--- errcount nonzero"; curl -s $B/status | python3 -c "import json,sys; e=json.load(sys.stdin)['errcount']; print({k:(v.get('counter'), v.get('history')) for k,v in e.items() if isinstance(v,dict) and v.get('counter')})"
kill -INT $pid; wait $pid
echo "--- twin output (grep)"; grep -nE 'WEBSERVER|Web|HTTP|conn' /tmp/twin_probe_$d.log | head -20
rm -f /tmp/twin_probe_$d.log; rm -rf digital_twin/config
