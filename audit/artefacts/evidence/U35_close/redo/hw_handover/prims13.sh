#!/bin/bash
# prims13.sh: real flash writes under live TCP (mp/big/prims13.py) with the host's TCP load and capture
# (prims13_host.py); board lines stamped with the host clock; then the watchdog reason and the markers, and a push.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
B=$H/mp/big
L=$H/logs/prims13_$(date -u +%Y%m%d).log
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}
MPC=scripts/mpremote_connect.sh
MNT=$PWD/build/mountstage/mpy
up() { for _ in $(seq 1 60); do timeout 15 $MPC resume exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done; echo "board not back" >> "$L"; return 1; }
up || exit 1
echo "### prims13 $(date -u +%T)" >> "$L"
(timeout 150 $MPC mount "$MNT" run "$B/prims13.py" 2>&1 | python3 -u -c 'import sys,time
for l in sys.stdin: print("%.3f %s" % (time.time(), l), end="", flush=True)' >> "$L") &
bp=$!
for _ in $(seq 1 90); do grep -q ' READY IP=' "$L" && break; sleep 1; done
ip=$(grep ' READY IP=' "$L" | tail -1 | sed 's/.*READY IP=\([0-9.]*\).*/\1/')
[ -n "$ip" ] && [ "$ip" != 0.0.0.0 ] && sudo -n "${SCAPY_PY:?the scapy venv python}" "$H/prims13_host.py" "$ip" 27 >> "$L" 2>&1
echo "host rc=$? $(date -u +%T)" >> "$L"
wait $bp; echo "rc=$? $(date -u +%T)" >> "$L"
sleep 2; up && timeout 15 $MPC resume run "$B/resets_read.py" >> "$L" 2>&1
timeout 15 $MPC resume exec "import os; print('SUM prims13 probe_left', [n for n in os.listdir('/') if n.startswith('u35')])" >> "$L" 2>&1
timeout 15 $MPC reset >/dev/null 2>&1; sleep 4; up
git add -f "$L" "$B/prims13.py" "$H/prims13_host.py" "$H/prims13.sh" && git commit -q -m "Bench campaign: real flash writes under TCP, $(date -u '+%F %H:%M') UTC [skip ci]" -- "$L" "$B/prims13.py" "$H/prims13_host.py" "$H/prims13.sh"
for w in 2 4 8 16; do git push -q origin "HEAD:refs/heads/$BRANCH" && break; sleep $w; done
