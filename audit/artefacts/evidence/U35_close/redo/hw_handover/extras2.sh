#!/bin/bash
# extras2.sh: further zero-wear device scripts over the mount (2026-10-29), queued behind uart_diag.sh: no full-system
# build, no SCD30 driver, no FRAM manager; a run without DONE is repeated once with the no-op watchdog.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
L=$H/logs
HB=$H/HANDBACK.md
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}
DAY=$(date -u +%Y%m%d)
MPC=scripts/mpremote_connect.sh
MNT=$PWD/build/mountstage/mpy
LOG=$L/extras2_$DAY.log

handback() {
  python3 "$H/handback.py" "$L" "$HB" "$DAY" || return 1
  git add -f "$HB" && git commit -q -m "Bench campaign hand-back (extras2), $(date -u '+%F %H:%M') UTC [skip ci]" -- "$HB" || return 0
  for w in 2 4 8 16; do git push -q origin "HEAD:refs/heads/$BRANCH" && return 0; sleep $w; done
}
up() { for _ in $(seq 1 "${1:-60}"); do timeout 15 $MPC exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done; return 1; }
render() {
  uv run --no-sync python - "$1" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "tests_hardware")
from harness import render_device_script
print(render_device_script(Path("tests_hardware/device_scripts") / sys.argv[1]))
PY
}
nowdt() {
  python3 - "$1" "$2" <<'PY'
import sys
s = open(sys.argv[1]).read()
old = "def arm() -> machine.WDT:\n    return machine.WDT(timeout=_WDT_TIMEOUT_MS)"
s = s.replace(old, "class _NoWDT:\n    def feed(self): pass\n\ndef arm():\n    print('FACT nowdt=true')\n    return _NoWDT()")
open(sys.argv[2], "w").write(s)
PY
}
run() {  # run LABEL SCRIPT: DONE or not, then a hard reset
  echo "### $1 $(date -u +%H:%M:%S)" >> "$LOG"
  timeout 900 $MPC mount "$MNT" run "$2" > "$L/.e2_cur" 2>&1
  echo "rc=$? $(date -u +%H:%M:%S)" >> "$L/.e2_cur"
  cat "$L/.e2_cur" >> "$LOG"
  timeout 15 $MPC reset >/dev/null 2>&1; sleep 3; up 90
  grep -q '^DONE' "$L/.e2_cur"
}

# uart_diag.sh removes STOP once run_all.sh ends; set it again so uart_diag does not relaunch the loop, then wait it out
while [ ! -f "$L/uart_diag_$DAY.log" ]; do sleep 10; done
sleep 20; touch "$H/STOP"
while pgrep -f 'uart_diag.sh$' >/dev/null; do sleep 10; done
rm -f "$H/STOP"
up 60 || exit 1
for s in float_boundary_2pow24 timer_alarm_pool_exhaustion unretrieved_task_exception_handler system_service_restarts_a_real_dead_task \
    bmp3xx_conformance_probe sgp40_conformance_probe isl29125_real_irq_edge isl29125_mechanism_envelope \
    wifi_country_code_reaction loop_lag_under_combined_load sgp40_voc_algorithm_quality isl29125_lighting_scenarios; do
  [ -f "$H/STOP" ] && break
  f=$(render "$s.py") || { echo "### $s render failed" >> "$LOG"; continue; }
  run "$s" "$f" || { nowdt "$f" "${f%.py}_nowdt.py"; run "${s}_nowdt" "${f%.py}_nowdt.py"; }
  handback
done
handback
left=$(( ($(date -u -d '17:30' +%s) - $(date -u +%s)) / 3600 ))
[ ! -f "$H/STOP" ] && [ "$left" -ge 1 ] && HOURS=$left setsid nohup bash "$H/run_all.sh" day > /dev/null 2>&1 < /dev/null &
