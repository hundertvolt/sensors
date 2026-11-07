#!/bin/bash
# run_all.sh all|day|summary: the bench campaign (HANDOVER.md), run from the repository root. Every step lasts at most
# about 10 minutes; `touch <this folder>/STOP` ends the run after the current step, and every exit pushes HANDBACK.md.
set -uo pipefail
[ -c /dev/null ] || exit 1
H=$(cd "$(dirname "$0")" && pwd)
L=$H/logs
HB=$H/HANDBACK.md
mkdir -p "$L" && chmod 700 "$L"
TC=${PICO_TOOLCHAIN_DIR:-$HOME/pico-toolchain}
UF2=$TC/micropython/ports/rp2/build-RPI_PICO_W/firmware.uf2
HOURS=${HOURS:-10}  # the long phase's length; no slice starts that would overrun it
SLICE_S=${SLICE_S:-540}  # one long script's run: with its start-up, under 10 minutes
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}
DAY=$(date -u +%Y%m%d)
MPC=scripts/mpremote_connect.sh

stopping() { [ -f "$H/STOP" ]; }

handback() {  # rebuilds HANDBACK.md and pushes it to the bench branch, with up to four retries
  python3 "$H/handback.py" "$L" "$HB" "$DAY" || return 1
  git add -f "$HB" && git commit -q -m "Bench campaign hand-back, $(date -u '+%F %H:%M') UTC [skip ci]" -- "$HB" || return 0
  local w=2
  for _ in 1 2 3 4 5; do
    git push -q origin "HEAD:refs/heads/$BRANCH" && return 0
    sleep $w
    w=$((w * 2))
  done
  echo "push failed; HANDBACK.md is committed locally" >&2
}

on_exit() {
  handback
  rm -f "$H/STOP"
}

up() {  # waits up to $1 s for the board to answer a RAM-only exec
  for _ in $(seq 1 "${1:-60}"); do
    timeout 15 $MPC exec "print('up')" >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "board not back after ${1:-60} s" | tee -a "$L/stop_$DAY.log" >&2
  return 1
}

run() {  # run NAME SCRIPT TIMEOUT_S: one script under `mpremote run`, appended to logs/NAME_DAY.log
  echo "== $1 $(date -u +%H:%M:%S)" >> "$L/$1_$DAY.log"
  timeout "$3" $MPC run "$2" >> "$L/$1_$DAY.log" 2>&1
  echo "rc=$? $(date -u +%H:%M:%S)" >> "$L/$1_$DAY.log"
}

render() {  # the harness's rendering of one device script (bench facts and includes inlined); prints its path
  uv run --no-sync python -c "import sys; sys.path.insert(0, 'tests_hardware'); from pathlib import Path
from harness import render_device_script; print(render_device_script(Path('tests_hardware/device_scripts/$1')))"
}

step() {  # one step of at most about 10 minutes, then the hand-back pushed; a STOP file ends the run first
  stopping && { echo "STOP found: ending before $1" | tee -a "$L/stop_$DAY.log"; exit 0; }
  "$@"
  local rc=$?
  handback
  return $rc
}

evidence() {  # on the image now on the board, before anything else: the FRAM's raw contents, read only
  up 20 && run fram_raw_dump_before "$(render fram_raw_dump.py)" 600
}

build() {  # pinned MicroPython plus the project's two lwIP overrides, no frozen project code
  uv run --no-sync python -c "import sys; sys.path.insert(0, 'toolchain'); from pathlib import Path; import setup_toolchain as st
d = Path('$TC'); print(st.build_firmware(d / 'micropython', 'RPI_PICO_W', 4, None, toolchain_dir=d))" > "$L/build_$DAY.log" 2>&1
  local rc=$?
  echo "build rc=$rc $(ls -l "$UF2" 2>&1)" >> "$L/build_$DAY.log"
  return $rc
}

flash() {  # one flash cycle: bootloader, then picotool, retried while no BOOTSEL device is enumerated yet
  [ -f "$UF2" ] || { echo "no $UF2" >> "$L/flash_$DAY.log"; return 1; }
  timeout 15 $MPC bootloader >> "$L/flash_$DAY.log" 2>&1
  for i in 1 2 3 4 5; do
    sleep 3
    sudo picotool load -x -v "$UF2" >> "$L/flash_$DAY.log" 2>&1 && break
    echo "picotool attempt $i failed" >> "$L/flash_$DAY.log"
  done
  up 60 || return 1
  timeout 15 $MPC exec "import os, sys; print('SUM image', sys.implementation, os.uname().version); print('SUM fs_root', os.listdir('/'))" >> "$L/flash_$DAY.log" 2>&1
}

resets() {  # each reset kind armed, then read back after the board returns
  local base=$H/mp/reset_probe.py k
  run reset_initial "$base" 30
  for k in machine_reset soft_reset wdt_1000 wdt_4000 wdt_8388 bootloader; do
    sed "s/^MODE = .*/MODE = \"arm_$k\"/" "$base" > "$L/arm.py"
    run "reset_$k" "$L/arm.py" 20
    [ "$k" = bootloader ] && { sleep 3; sudo picotool reboot >> "$L/reset_${k}_$DAY.log" 2>&1; }
    up 60 || return 1
    run "reset_$k" "$base" 30
  done
}

net() {  # the host's one connection to the board, once the script prints READY
  run net "$H/mp/net_timing.py" 300 &
  for _ in $(seq 1 240); do grep -q '^READY' "$L/net_$DAY.log" 2>/dev/null && break; sleep 1; done
  local ip
  ip=$(grep -m1 '^IP=' "$L/net_$DAY.log" | cut -d= -f2 | tr -d '\r')
  [ -n "$ip" ] && curl -s -m 10 "http://$ip:8080/" > /dev/null
  wait
}

day1() {
  local s
  step evidence || exit 1
  step build || exit 1
  step flash || exit 1
  step resets
  step run runtime "$H/mp/runtime_timing.py" 600
  step run uart "$H/mp/uart_timing.py" 420
  step run i2c "$H/mp/i2c_timing.py" 300
  step run fram "$H/mp/fram_spi_timing.py" 300
  step net
  for s in bmp3xx_conformance_probe fram_conformance_probe isl29125_mock_conformance_probe scd30_conformance_probe \
      sgp40_conformance_probe timer_alarm_pool_exhaustion scheduler_saturation_drop wifi_country_code_reaction; do
    step run "probe_$s" "$(render $s.py)" 300
  done
}

long() {  # the long scripts in rotation until HOURS have passed; GC threshold alternates per round; a push every 3 runs
  local end=$(($(date +%s) + ${HOURS%.*} * 3600)) round=0 n=0 s gc
  while :; do
    gc=-1
    [ $((round % 2)) = 1 ] && gc=32768
    for s in i2c fram uart runtime net neopixel; do
      [ $(($(date +%s) + SLICE_S + 120)) -gt "$end" ] && return 0
      stopping && { echo "STOP found: ending before long_$s" | tee -a "$L/stop_$DAY.log"; exit 0; }
      sed -e "s/^DUR_S = .*/DUR_S = $SLICE_S/" -e "s/^GC = .*/GC = $gc/" "$H/mp/long_$s.py" > "$L/long_$s.py"
      run "long_$s" "$L/long_$s.py" $((SLICE_S + 120))
      if ! up 60; then
        timeout 15 $MPC reset >/dev/null 2>&1
        up 120 || { echo "board unresponsive after long_$s: needs a power cycle" >> "$L/stop_$DAY.log"; exit 1; }
      fi
      n=$((n + 1))
      [ $((n % 3)) = 0 ] && handback
    done
    round=$((round + 1))
  done
}

case "${1:-}" in
  all | day)
    rm -f "$H/STOP"
    if ! git rev-parse --abbrev-ref HEAD | grep -qx "$BRANCH"; then  # continue the bench branch where it exists
      if git fetch -q origin "$BRANCH" 2>/dev/null; then git checkout -q -B "$BRANCH" FETCH_HEAD; else git checkout -q -B "$BRANCH"; fi
    fi
    trap 'exit 130' INT TERM
    trap on_exit EXIT
    [ "$1" = all ] && day1
    up 30 && step run quick "$H/mp/quick_platform.py" 120
    long
    ;;
  summary) sed -n '1,/^## Day /p' "$HB" ;;
  *) echo "usage: $0 all|day|summary" >&2; exit 2 ;;
esac
