#!/bin/bash
# prims5.sh: the driver's bus clear under injected faults (mp/big/prims5.py), then prims4's concurrent-DMA run split by
# variant, each followed by the watchdog reason and the reset-surviving progress markers read before any hard reset.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
B=$H/mp/big
L=$H/logs/prims5_$(date -u +%Y%m%d).log
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}
MPC=scripts/mpremote_connect.sh
MNT=$PWD/build/mountstage/mpy
push() {
  git add -f "$L" && git commit -q -m "Bench campaign: $1, $(date -u '+%F %H:%M') UTC [skip ci]" -- "$L" || return 0
  for w in 2 4 8 16; do git push -q origin "HEAD:refs/heads/$BRANCH" && return 0; sleep $w; done
}
up() { for _ in $(seq 1 60); do timeout 15 $MPC resume exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done; echo "board not back" >> "$L"; return 1; }
settle() { timeout 15 $MPC reset >/dev/null 2>&1; sleep 4; up; }
flood() {
  for _ in $(seq 1 200); do grep -q '^FLOOD_START' "$L" && break; pgrep -f 'prims4_full' >/dev/null || return; sleep 1; done
  ip=$(grep '^FLOOD_START' "$L" | tail -1 | sed 's/.*IP=//' | tr -d '\r')
  [ -n "$ip" ] && python3 - "$ip" >> "$L" 2>&1 <<'PY'
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
PY
}
echo "### prims5 $(date -u +%T)" >> "$L"
timeout 120 $MPC mount "$MNT" run "$B/prims5.py" >> "$L" 2>&1; echo "rc=$? $(date -u +%T)" >> "$L"
settle; push "the I2C bus clear under injected faults"
for v in no_wifi no_uart no_fram full; do
  sed "s/^VARIANT = .*/VARIANT = \"$v\"/" "$B/prims4.py" > "$H/logs/prims4_$v.py"
  echo "### prims4 $v $(date -u +%T)" >> "$L"
  timeout 240 $MPC mount "$MNT" run "$H/logs/prims4_$v.py" >> "$L" 2>&1 &
  [ "$v" = full ] && flood
  wait; echo "rc=$? $(date -u +%T)" >> "$L"
  sleep 2; up && timeout 15 $MPC resume run "$B/resets_read.py" >> "$L" 2>&1
  settle; push "concurrent DMA users, variant $v"
done
