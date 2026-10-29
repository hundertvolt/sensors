#!/bin/bash
# held.sh: the triage's held-back unattended items (FINDINGS_20261029.md), run from the repository root once run_all.sh
# has stopped; every step ends with a hard reset (an armed watchdog cannot be stopped) and a hand-back push.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
L=$H/logs
HB=$H/HANDBACK.md
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}
DAY=$(date -u +%Y%m%d)
MPC=scripts/mpremote_connect.sh
MNT=$PWD/build/mountstage/mpy

handback() {
  python3 "$H/handback.py" "$L" "$HB" "$DAY" || return 1
  git add -f "$HB" && git commit -q -m "Bench campaign hand-back (held-back items), $(date -u '+%F %H:%M') UTC [skip ci]" -- "$HB" || return 0
  for w in 2 4 8 16; do git push -q origin "HEAD:refs/heads/$BRANCH" && return 0; sleep $w; done
}

up() {
  for _ in $(seq 1 "${1:-60}"); do timeout 15 $MPC exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done
  echo "board not back after ${1:-60} s" | tee -a "$L/stop_$DAY.log" >&2
  return 1
}

run() {  # run NAME SCRIPT TIMEOUT_S [mount]
  echo "== $1 $(date -u +%H:%M:%S)" >> "$L/$1_$DAY.log"
  if [ "${4:-}" = mount ]; then
    timeout "$3" $MPC mount "$MNT" run "$2" >> "$L/$1_$DAY.log" 2>&1
  else
    timeout "$3" $MPC run "$2" >> "$L/$1_$DAY.log" 2>&1
  fi
  echo "rc=$? $(date -u +%H:%M:%S)" >> "$L/$1_$DAY.log"
}

render() {  # render SCRIPT KEY=VALUE...: the harness's rendering with extras
  local s=$1
  shift
  uv run --no-sync python - "$s" "$@" <<'EOF'
import sys
from pathlib import Path
sys.path.insert(0, "tests_hardware")
from harness import render_device_script
extras = dict(a.split("=", 1) for a in sys.argv[2:])
out = render_device_script(Path("tests_hardware/device_scripts") / sys.argv[1], **extras)
dest = out.with_name(out.stem + "".join("_" + v for v in extras.values()) + ".py")
dest.write_text(out.read_text())
print(dest)
EOF
}

settle() {  # hard reset, then wait for the board
  timeout 15 $MPC reset >/dev/null 2>&1
  sleep 3
  up 90
}

while pgrep -f '^bash audit/.*run_all.sh' >/dev/null; do sleep 10; done
rm -f "$H/STOP"
up 60 || exit 1
run misc_raw "$H/mp/misc_raw.py" 60
settle && handback
# SDA held across a reset: arm (the board resets itself), then check and clear before any other I2C step
run sda_hold "$H/mp/sda_hold.py" 30
up 90 && sed 's/^MODE = .*/MODE = "check"/' "$H/mp/sda_hold.py" > "$L/sda_check.py" && run sda_hold "$L/sda_check.py" 60
settle && handback
run wifi_switch "$H/mp/wifi_switch.py" 300
settle && handback
run crc_voc "$H/mp/crc_voc.py" 120 mount
settle && handback
for spec in "uart_crossover_exchange.py CRC_MODE=none" "uart_crossover_exchange.py CRC_MODE=crc16" \
    "uart_crossover_recovery.py CRC_MODE=none" "uart_crossover_recovery.py CRC_MODE=crc16" \
    "uart_driver_read_never_blocks_the_loop.py" "uart_idle_poll_rate.py" \
    "uart_comm_hazards.py CRC_MODE=none" "uart_comm_hazards.py CRC_MODE=crc16" \
    "uart_dma_ring_interrupts_off.py CRC_MODE=none" "uart_dma_ring_interrupts_off.py CRC_MODE=crc16" \
    "uart_dma_ring_interrupts_off.py CRC_MODE=none STATE=break" "uart_dma_ring_interrupts_off.py CRC_MODE=crc16 STATE=break"; do
  [ -f "$H/STOP" ] && break
  read -r -a a <<< "$spec"
  script=$(render "${a[@]}") || { echo "render failed: $spec" >> "$L/uart_mount_$DAY.log"; continue; }
  echo "### $spec" >> "$L/uart_mount_$DAY.log"
  run uart_mount "$script" 600 mount
  settle || break
  handback
done
handback
# then the long loop until 17:30 UTC, the end of this 12-hour stretch, if at least an hour is left
left=$(( ($(date -u -d '17:30' +%s) - $(date -u +%s)) / 3600 ))
[ ! -f "$H/STOP" ] && [ "$left" -ge 1 ] && HOURS=$left setsid nohup bash "$H/run_all.sh" day > /dev/null 2>&1 < /dev/null &
