#!/bin/bash
# prims6.sh: mp/big/prims6.py under a 15 s unthrottled host UDP flood, then the reset-surviving markers, then a push.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
L=$H/logs/prims6_$(date -u +%Y%m%d).log
MPC=scripts/mpremote_connect.sh
up() { for _ in $(seq 1 60); do timeout 15 $MPC resume exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done; echo "board not back" >> "$L"; return 1; }
up || exit 1
echo "### prims6 $(date -u +%T)" >> "$L"
timeout 150 $MPC run "$H/mp/big/prims6.py" >> "$L" 2>&1 &
for _ in $(seq 1 60); do grep -q '^FLOOD_START' "$L" && break; sleep 1; done
ip=$(grep '^FLOOD_START' "$L" | tail -1 | sed 's/.*IP=//' | tr -d '\r')
[ -n "$ip" ] && python3 - "$ip" >> "$L" 2>&1 <<'PY'
import socket, sys, time
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setblocking(False); sent = 0; t_end = time.time() + 15; p = bytes(200)
while time.time() < t_end:
    try: s.sendto(p, (sys.argv[1], 5005)); sent += 1
    except BlockingIOError: pass
    try:
        while True: s.recv(512)
    except BlockingIOError: pass
print("SUM prims6_host unthrottled_15s sent=%d" % sent)
PY
wait; echo "rc=$? $(date -u +%T)" >> "$L"
sleep 2; up && timeout 15 $MPC resume run "$H/mp/big/resets_read.py" >> "$L" 2>&1
timeout 15 $MPC reset >/dev/null 2>&1; sleep 4; up
git add -f "$L" && git commit -q -m "Bench campaign: what a UDP flood leaves behind, $(date -u '+%F %H:%M') UTC [skip ci]" -- "$L" && git push -q origin HEAD:refs/heads/claude/u35-bench-campaign
