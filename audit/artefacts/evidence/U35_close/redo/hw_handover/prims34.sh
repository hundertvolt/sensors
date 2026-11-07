#!/bin/bash
# prims34.sh: I2C fault injection (mp/big/prims3.py) and the concurrent DMA/IRQ users under a host UDP flood
# (mp/big/prims4.py), run from the repository root with the board free; each ends in a hard reset and a push.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
L=$H/logs/prims34_$(date -u +%Y%m%d).log
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}
MPC=scripts/mpremote_connect.sh
MNT=$PWD/build/mountstage/mpy
push() {
  git add -f "$L" && git commit -q -m "Bench campaign: $1, $(date -u '+%F %H:%M') UTC [skip ci]" -- "$L" || return 0
  for w in 2 4 8 16; do git push -q origin "HEAD:refs/heads/$BRANCH" && return 0; sleep $w; done
}
settle() { timeout 15 $MPC reset >/dev/null 2>&1; sleep 4; for _ in $(seq 1 60); do timeout 15 $MPC exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done; echo "board not back" >> "$L"; return 1; }
echo "### prims3 $(date -u +%T)" >> "$L"
timeout 240 $MPC mount "$MNT" run "$H/mp/big/prims3.py" >> "$L" 2>&1; echo "rc=$? $(date -u +%T)" >> "$L"
settle; push "I2C fault injection"
echo "### prims4 $(date -u +%T)" >> "$L"
timeout 300 $MPC mount "$MNT" run "$H/mp/big/prims4.py" >> "$L" 2>&1 &
for _ in $(seq 1 200); do grep -q '^FLOOD_START' "$L" && break; sleep 1; done
ip=$(grep '^FLOOD_START' "$L" | tail -1 | sed 's/.*IP=//' | tr -d '\r')
[ -n "$ip" ] && python3 - "$ip" >> "$L" 2>&1 <<'EOF'
import socket, sys, time
ip = sys.argv[1]; s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setblocking(False)
payload = bytes(range(200)); res = []
for label, rate, secs in (("rate_200pps", 200, 13), ("rate_1000pps", 1000, 13), ("unthrottled", 0, 13)):
    sent = echoed = 0; t_end = time.time() + secs; nxt = time.time()
    while time.time() < t_end:
        if rate == 0 or time.time() >= nxt:
            try: s.sendto(payload, (ip, 5005)); sent += 1
            except BlockingIOError: pass
            nxt += 1 / rate if rate else 0
        try:
            while True: s.recv(512); echoed += 1
        except BlockingIOError: pass
    time.sleep(0.3)
    try:
        while True: s.recv(512); echoed += 1
    except BlockingIOError: pass
    res.append("%s sent=%d echoed=%d" % (label, sent, echoed))
print("SUM prims4_host", "; ".join(res))
EOF
wait
echo "rc=$? $(date -u +%T)" >> "$L"
settle; push "concurrent DMA users under a UDP flood"
