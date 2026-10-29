#!/bin/bash
# uart_diag.sh: why the mounted UART scripts reset the board (2026-10-29): reset cause after a plain run, then the three
# unfinished scripts with arm() swapped for a no-op watchdog; run from the repository root once run_all.sh has stopped.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
L=$H/logs
HB=$H/HANDBACK.md
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}
DAY=$(date -u +%Y%m%d)
MPC=scripts/mpremote_connect.sh
MNT=$PWD/build/mountstage/mpy
D=build/device_scripts
LOG=$L/uart_diag_$DAY.log

handback() {
  python3 "$H/handback.py" "$L" "$HB" "$DAY" || return 1
  git add -f "$HB" && git commit -q -m "Bench campaign hand-back (UART diagnosis), $(date -u '+%F %H:%M') UTC [skip ci]" -- "$HB" || return 0
  for w in 2 4 8 16; do git push -q origin "HEAD:refs/heads/$BRANCH" && return 0; sleep $w; done
}
up() {
  for _ in $(seq 1 "${1:-60}"); do timeout 15 $MPC exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done
  echo "board not back" >> "$LOG"; return 1
}
cause() { up 90 && timeout 15 $MPC exec "import machine; print('SUM uart_diag reset_cause', machine.reset_cause())" >> "$LOG" 2>&1; }
run() {  # run LABEL SCRIPT
  echo "### $1 $(date -u +%H:%M:%S)" >> "$LOG"
  timeout 600 $MPC mount "$MNT" run "$2" >> "$LOG" 2>&1
  echo "rc=$? $(date -u +%H:%M:%S)" >> "$LOG"
  grep -q '^DONE' <(awk -v t="### $1 " 'index($0,t)==1{f=1;next} /^### /{f=0} f' "$LOG") && echo "SUM uart_diag $1 done" >> "$LOG" || { echo "SUM uart_diag $1 no_done" >> "$LOG"; cause; }
  timeout 15 $MPC reset >/dev/null 2>&1; sleep 3; up 90
}
nowdt() {  # the rendered script with arm() returning a no-op watchdog
  python3 - "$1" "$2" <<'PY'
import sys
s = open(sys.argv[1]).read()
old = "def arm() -> machine.WDT:\n    return machine.WDT(timeout=_WDT_TIMEOUT_MS)"
assert old in s
s = s.replace(old, "class _NoWDT:\n    def feed(self): pass\n\ndef arm():\n    print('FACT nowdt=true')\n    return _NoWDT()")
open(sys.argv[2], "w").write(s)
PY
}

while pgrep -f '^bash audit/.*run_all.sh' >/dev/null; do sleep 10; done
rm -f "$H/STOP"
up 60 || exit 1
cause
run idle_poll_rate_plain "$D/uart_idle_poll_rate.py"
for s in uart_idle_poll_rate uart_crossover_recovery_none uart_crossover_recovery_crc16 uart_dma_ring_interrupts_off_none uart_dma_ring_interrupts_off_crc16; do
  nowdt "$D/$s.py" "$D/${s}_nowdt.py" && run "${s}_nowdt" "$D/${s}_nowdt.py"
  handback
done
handback
left=$(( ($(date -u -d '17:30' +%s) - $(date -u +%s)) / 3600 ))
[ ! -f "$H/STOP" ] && [ "$left" -ge 1 ] && HOURS=$left setsid nohup bash "$H/run_all.sh" day > /dev/null 2>&1 < /dev/null &
