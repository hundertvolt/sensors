#!/bin/bash
# prims11.sh: clients that vanish mid-request (prims11_host.py, scapy on br0, sudo) against a hardened-shape HTTP server on
# the board (mp/big/prims11.py); then the watchdog reason and the reset-surviving markers, and a push.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
B=$H/mp/big
L=$H/logs/prims11_$(date -u +%Y%m%d).log
PY=${SCAPY_PY:?the scapy venv python}
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}
MPC=scripts/mpremote_connect.sh
MNT=$PWD/build/mountstage/mpy
up() { for _ in $(seq 1 60); do timeout 15 $MPC resume exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done; echo "board not back" >> "$L"; return 1; }
up || exit 1
echo "### prims11 $(date -u +%T)" >> "$L"
timeout 700 $MPC mount "$MNT" run "$B/prims11.py" >> "$L" 2>&1 &
bp=$!
for _ in $(seq 1 120); do grep -q '^READY IP=' "$L" && break; sleep 1; done
ip=$(grep '^READY IP=' "$L" | tail -1 | sed 's/READY IP=\([0-9.]*\).*/\1/')
[ -n "$ip" ] && [ "$ip" != 0.0.0.0 ] && sudo -n "$PY" "$H/prims11_host.py" "$ip" >> "$L" 2>&1
echo "host rc=$? $(date -u +%T)" >> "$L"
wait $bp; echo "rc=$? $(date -u +%T)" >> "$L"
sleep 2; up && timeout 15 $MPC resume run "$B/resets_read.py" >> "$L" 2>&1
timeout 15 $MPC reset >/dev/null 2>&1; sleep 4; up
git add -f "$L" "$B/prims11.py" "$H/prims11_host.py" "$H/prims11.sh" && git commit -q -m "Bench campaign: vanishing clients, $(date -u '+%F %H:%M') UTC [skip ci]" -- "$L" "$B/prims11.py" "$H/prims11_host.py" "$H/prims11.sh"
for w in 2 4 8 16; do git push -q origin "HEAD:refs/heads/$BRANCH" && break; sleep $w; done
