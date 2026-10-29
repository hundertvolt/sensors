#!/bin/bash
# prims7.sh: mp/big/prims7.py per power-save mode and target port under a ramped host UDP storm, then a paced RTT probe,
# the reset-surviving markers, and a push.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
L=$H/logs/prims7_$(date -u +%Y%m%d).log
MPC=scripts/mpremote_connect.sh
up() { for _ in $(seq 1 60); do timeout 15 $MPC resume exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done; echo "board not back" >> "$L"; return 1; }
for case in ${CASES:-"fw True" "fw False" "performance True" "powersave True"}; do
  read -r pm bound <<< "$case"
  up || exit 1
  sed -e "s/^PM = .*/PM = \"$pm\"/" -e "s/^BOUND = .*/BOUND = $bound/" "$H/mp/big/prims7.py" > "$H/logs/prims7_case.py"
  n=$(grep -c '^FLOOD_START' "$L" 2>/dev/null); n=${n:-0}
  echo "### prims7 $pm bound=$bound $(date -u +%T)" >> "$L"
  timeout 120 $MPC run "$H/logs/prims7_case.py" >> "$L" 2>&1 &
  for _ in $(seq 1 60); do [ "$(grep -c '^FLOOD_START' "$L")" -gt "$n" ] && break; sleep 1; done
  line=$(grep '^FLOOD_START' "$L" | tail -1 | tr -d '\r'); ip=$(sed 's/.*IP=\([^ ]*\).*/\1/' <<< "$line"); port=$(sed 's/.*PORT=//' <<< "$line")
  [ -n "$ip" ] && python3 - "$ip" "$port" >> "$L" 2>&1 <<'PY'
import socket, statistics, sys, time
ip, port = sys.argv[1], int(sys.argv[2]); s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setblocking(False); p = bytes(200)
for i in range(600): s.sendto(p, (ip, port)); time.sleep(0.005)
sent = 600; t_end = time.time() + 8
while time.time() < t_end:
    try: s.sendto(p, (ip, port)); sent += 1
    except BlockingIOError: pass
    try:
        while True: s.recv(512)
    except BlockingIOError: pass
time.sleep(4); s.settimeout(1.0); rtts = []
try:
    while True: s.recv(512)
except OSError: pass
for i in range(20):
    tag = b"rtt%d" % i; t = time.perf_counter(); s.sendto(tag, (ip, 5005))
    try:
        while s.recv(512) != tag: pass
        rtts.append((time.perf_counter() - t) * 1000)
    except OSError: pass
    time.sleep(0.2)
print("SUM prims7_host storm sent=%d port=%d; paced rtt answered %d/20 median_ms %s max_ms %s" % (sent, port, len(rtts), round(statistics.median(rtts), 1) if rtts else None, round(max(rtts), 1) if rtts else None))
PY
  wait; echo "rc=$? $(date -u +%T)" >> "$L"
  sleep 2; up && timeout 15 $MPC resume run "$H/mp/big/resets_read.py" >> "$L" 2>&1
  timeout 15 $MPC reset >/dev/null 2>&1; sleep 4
done
up
git add -f "$L" && git commit -q -m "Bench campaign: a UDP storm against power-save mode and port, $(date -u '+%F %H:%M') UTC [skip ci]" -- "$L" && git push -q origin HEAD:refs/heads/claude/u35-bench-campaign
