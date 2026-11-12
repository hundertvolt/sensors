#!/bin/bash
# bigq.sh: rp2 primitives beyond UART (2026-10-29): DMA channels across a soft reset, what each reset kind keeps, SPI/gc/
# lwIP/DNS limits; queued behind prims.sh, a commit and push after every step, then the long loop until 17:30 UTC.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd); L=$H/logs; HB=$H/HANDBACK.md; DAY=$(date -u +%Y%m%d)
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}; MPC=scripts/mpremote_connect.sh; MNT=$PWD/build/mountstage/mpy
B=$H/mp/big; LOG=$L/bigq_$DAY.log; T=$L/.bigq; mkdir -p "$T"
push() {
  python3 "$H/handback.py" "$L" "$HB" "$DAY" >/dev/null || return 1
  git add -f "$HB" && git commit -q -m "Bench campaign hand-back (rp2 primitives: $1), $(date -u '+%F %H:%M') UTC [skip ci]" -- "$HB" || return 0
  for w in 2 4 8 16; do git push -q origin "HEAD:refs/heads/$BRANCH" && return 0; sleep $w; done
}
up() { for _ in $(seq 1 90); do timeout 15 $MPC exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done; echo "board not back" >> "$LOG"; return 1; }
step() { echo "### $1 $(date -u +%H:%M:%S)" >> "$LOG"; shift; timeout "$@" >> "$LOG" 2>&1; echo "rc=$? $(date -u +%H:%M:%S)" >> "$LOG"; }
readback() { timeout 15 $MPC resume exec "import machine; print('SUM bigq reset_cause', machine.reset_cause())" >> "$LOG" 2>&1; }

while pgrep -f 'prims.sh$' >/dev/null; do sleep 10; done
if pgrep -f '^bash (/.*/)?audit/.*run_all.sh' >/dev/null; then touch "$H/STOP"; while pgrep -f '^bash (/.*/)?audit/.*run_all.sh' >/dev/null; do sleep 10; done; fi
rm -f "$H/STOP"; up || exit 1
for mode in leave deinit; do
  sed "s/^MODE = .*/MODE = \"$mode\"/" "$B/dma_ring_leave.py" > "$T/leave_$mode.py"
  step "dma_soft $mode: the ring script" 120 $MPC mount "$MNT" run "$T/leave_$mode.py"
  step "dma_soft $mode: soft reset, then the dump" 40 $MPC run "$B/dma_dump.py"
  sleep 10; up; readback
  timeout 15 $MPC reset >/dev/null 2>&1; sleep 4; up
done
push "DMA across a soft reset"
for kind in reset soft wdt; do
  sed "s/^KIND = .*/KIND = \"$kind\"/" "$B/resets.py" > "$T/resets_$kind.py"
  step "resets $kind" 20 $MPC run "$T/resets_$kind.py"
  sleep 5; up
  timeout 15 $MPC resume run "$B/resets_read.py" >> "$LOG" 2>&1
done
timeout 15 $MPC reset >/dev/null 2>&1; sleep 4; up
push "reset kinds"
step "prims2" 300 $MPC run "$B/prims2.py"
timeout 15 $MPC reset >/dev/null 2>&1; sleep 4; up
push "SPI, gc, sockets, DNS"
left=$(( ($(date -u -d '17:30' +%s) - $(date -u +%s)) / 3600 ))
[ ! -f "$H/STOP" ] && [ "$left" -ge 1 ] && HOURS=$left setsid nohup bash "$H/run_all.sh" day > /dev/null 2>&1 < /dev/null &
