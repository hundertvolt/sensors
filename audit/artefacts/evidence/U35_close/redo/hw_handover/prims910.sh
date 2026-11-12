#!/bin/bash
# prims910.sh: the UART receive line held low or glitched (mp/big/prims9.py), then an edge storm on the sensor interrupt
# lines (mp/big/prims10.py), each followed by the watchdog reason and the reset-surviving markers, then a push.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
B=$H/mp/big
L=$H/logs/prims910_$(date -u +%Y%m%d).log
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}
MPC=scripts/mpremote_connect.sh
MNT=$PWD/build/mountstage/mpy
push() {
  git add -f "$L" "$B/prims9.py" "$B/prims10.py" "$H/prims910.sh" && git commit -q -m "Bench campaign: $1, $(date -u '+%F %H:%M') UTC [skip ci]" -- "$L" "$B/prims9.py" "$B/prims10.py" "$H/prims910.sh" || return 0
  for w in 2 4 8 16; do git push -q origin "HEAD:refs/heads/$BRANCH" && return 0; sleep $w; done
}
up() { for _ in $(seq 1 60); do timeout 15 $MPC resume exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done; echo "board not back" >> "$L"; return 1; }
settle() { timeout 15 $MPC reset >/dev/null 2>&1; sleep 4; up; }
up || exit 1
for s in ${SCRIPTS:-prims9 prims10}; do
  echo "### $s $(date -u +%T)" >> "$L"
  timeout 180 $MPC mount "$MNT" run "$B/$s.py" >> "$L" 2>&1; echo "rc=$? $(date -u +%T)" >> "$L"
  sleep 2; up && timeout 15 $MPC resume run "$B/resets_read.py" >> "$L" 2>&1
  settle; push "$s"
done
