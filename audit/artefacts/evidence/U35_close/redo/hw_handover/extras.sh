#!/bin/bash
# extras.sh: the bare-image measurements added on 2026-10-29 (REPORT 7 items 1 and 10, BACKLOG's idle poll rate), run
# from the repository root while run_all.sh is not running; logs and the hand-back push follow run_all.sh's scheme.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
L=$H/logs
HB=$H/HANDBACK.md
TC=${PICO_TOOLCHAIN_DIR:-$HOME/pico-toolchain}
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}
DAY=$(date -u +%Y%m%d)
MPC=scripts/mpremote_connect.sh

handback() {
  python3 "$H/handback.py" "$L" "$HB" "$DAY" || return 1
  git add -f "$HB" && git commit -q -m "Bench campaign hand-back (extras), $(date -u '+%F %H:%M') UTC [skip ci]" -- "$HB" || return 0
  for w in 2 4 8 16; do git push -q origin "HEAD:refs/heads/$BRANCH" && return 0; sleep $w; done
  echo "push failed; HANDBACK.md is committed locally" >&2
}

up() {
  for _ in $(seq 1 "${1:-60}"); do timeout 15 $MPC exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done
  echo "board not back after ${1:-60} s" | tee -a "$L/stop_$DAY.log" >&2
  return 1
}

run() {  # run NAME SCRIPT TIMEOUT_S
  echo "== $1 $(date -u +%H:%M:%S)" >> "$L/$1_$DAY.log"
  timeout "$3" $MPC run "$2" >> "$L/$1_$DAY.log" 2>&1
  echo "rc=$? $(date -u +%H:%M:%S)" >> "$L/$1_$DAY.log"
}

idle_poll() {  # the board script, and the host timing queries once it prints READY
  run idle_poll "$H/mp/idle_poll.py" 400 &
  for _ in $(seq 1 300); do grep -q '^READY' "$L/idle_poll_$DAY.log" 2>/dev/null && break; sleep 1; done
  local ip
  ip=$(grep '^IP=' "$L/idle_poll_$DAY.log" | tail -1 | cut -d= -f2 | tr -d '\r')
  [ -n "$ip" ] && python3 - "$ip" >> "$L/idle_poll_host_$DAY.log" 2>&1 <<'EOF'
import random, socket, statistics, sys, time
ip = sys.argv[1]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(2.0)
def rtt(tag):
    t = time.perf_counter(); s.sendto(tag, (ip, 53))
    try:
        while s.recv(512) != tag: pass
        return (time.perf_counter() - t) * 1000
    except OSError:
        return None
time.sleep(1)
for label, lo, hi, n in (("after_silence", 2.0, 4.0, 25), ("busy_10ms_gap", 0.01, 0.01, 40)):
    got, lost = [], 0
    for i in range(n):
        time.sleep(random.uniform(lo, hi))
        r = rtt(b"%s%d" % (label.encode(), i))
        got.append(r) if r is not None else None
        lost += r is None
    got.sort()
    print("SUM idle_poll_host %s n=%d lost=%d min_ms=%.1f median_ms=%.1f p90_ms=%.1f max_ms=%.1f" % (label, n, lost, got[0], statistics.median(got), got[int(len(got) * 0.9) - 1], got[-1]) if got else "SUM idle_poll_host %s all lost" % label)
time.sleep(3)
t = time.perf_counter()
for i in range(5): s.sendto(b"burst%d" % i, (ip, 53))
times = []
try:
    while len(times) < 5: s.recv(512); times.append((time.perf_counter() - t) * 1000)
except OSError:
    pass
print("SUM idle_poll_host burst_of_5 answered=%d reply_ms=%s" % (len(times), [round(x, 1) for x in times]))
EOF
  wait
}

listener_close() {  # tests_hardware's prepared script, rendered with the flashed bare image's own lwIP pool addresses
  local script
  script=$(uv run --no-sync python - "$TC" <<'EOF'
import sys
from pathlib import Path
sys.path[:0] = ["tests_hardware", "toolchain"]
from harness import configured_max_connections, elf_symbols, render_device_script
build = Path(sys.argv[1]) / "micropython/ports/rp2/build-RPI_PICO_W"
symbols = elf_symbols(build / "firmware.elf")
pools = {}
for name, pool in (("listen", "TCP_PCB_LISTEN"), ("conn", "TCP_PCB")):
    desc, base, tab = (symbols[s] for s in (f"memp_{pool}", f"memp_memory_{pool}_base", f"memp_tab_{pool}"))
    assert desc[1] == 12, desc
    pools[name] = {"desc": desc[0], "base": base[0], "bytes": base[1], "tab": tab[0]}
print(render_device_script(Path("tests_hardware/device_scripts/listener_close_leaves_the_pcb_pools.py"), pools=pools, backlog=configured_max_connections() + 1))
EOF
)
  [ -f "$script" ] || { echo "render failed: $script" >> "$L/listener_close_$DAY.log"; return 1; }
  run listener_close "$script" 300
}

up 30 || exit 1
for s in ${STEPS:-cstack idle_poll listener_close}; do  # listener_close last: its watchdog stays armed
  [ -f "$H/STOP" ] && break
  case $s in
    cstack) run cstack "$H/mp/cstack_await.py" 300 ;;
    i2c) run i2c_rerun "$H/mp/i2c_timing.py" 300 ;;
    scd30) run scd30_state "$H/mp/scd30_state.py" 900 ;;
    *) $s ;;
  esac
  up 60 || { timeout 15 $MPC reset >/dev/null 2>&1; up 120 || break; }
  handback
done
handback
