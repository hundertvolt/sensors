#!/bin/bash
# prims.sh: run mp/prims.py once the board is free (after extras2.sh; stops a relaunched run_all.sh at its slice end)
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd); L=$H/logs; DAY=$(date -u +%Y%m%d); MPC=scripts/mpremote_connect.sh
while pgrep -f 'extras2.sh$' >/dev/null; do sleep 10; done
if pgrep -f '^bash (/.*/)?audit/.*run_all.sh' >/dev/null; then touch "$H/STOP"; while pgrep -f '^bash (/.*/)?audit/.*run_all.sh' >/dev/null; do sleep 10; done; fi
rm -f "$H/STOP"
timeout 15 $MPC reset >/dev/null 2>&1; sleep 4
echo "== prims $(date -u +%H:%M:%S)" >> "$L/prims_$DAY.log"
timeout 180 $MPC run "$H/mp/prims.py" >> "$L/prims_$DAY.log" 2>&1; echo "rc=$?" >> "$L/prims_$DAY.log"
timeout 15 $MPC reset >/dev/null 2>&1; sleep 4
python3 "$H/handback.py" "$L" "$H/HANDBACK.md" "$DAY"
left=$(( ($(date -u -d '17:30' +%s) - $(date -u +%s)) / 3600 ))
[ "$left" -ge 1 ] && HOURS=$left setsid nohup bash "$H/run_all.sh" day > /dev/null 2>&1 < /dev/null &
