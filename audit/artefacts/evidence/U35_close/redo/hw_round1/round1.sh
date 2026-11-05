#!/bin/bash
# round1.sh list | run FROM [TO] | summary: round 1's run sheet (HANDOVER.md), from the repository root. Each step's
# boundary is a breakpoint; `touch <this folder>/STOP` ends a run after its step, and every exit pushes HANDBACK.md.
# The step bodies are called through the STEPS table's last field, which shellcheck cannot follow.
# shellcheck disable=SC2329
set -uo pipefail
[ -c /dev/null ] || exit 1
H=$(cd "$(dirname "$0")" && pwd)
ME=$H/round1.sh
HM=$(dirname "$H")/hw_handover/mp
L=$H/logs
HB=$H/HANDBACK.md
BRANCH=${BENCH_BRANCH:-claude/u35-bench-campaign}
MPC=scripts/mpremote_connect.sh
UF2=build/firmware-dev.uf2
SLICE_S=${SLICE_S:-540}  # one FRAM slice: with its start-up, under 10 minutes (October's)
FLOOR="not soak_duration and not multi_day_rollover"
HOTSPOT=tests_hardware/bench/test_hotspot_role_reversal.py
DUTARG=()
[ -z "${DUT_IP:-}" ] || DUTARG=(--dut-ip "$DUT_IP")

STEPS=(  # id|name|minutes|FC|FS owned|NVM|FS prerequisite|stop|needs|command; the sheet's rows, the rollover last
  # (rows 6 and 16 are the /status read after every step; row 14 is the owner's, HANDOVER.md)
  "1|evidence|5|0|0|0|0|end|DUT_IP for /status|evidence"
  "2|host_env|30|0|0|0|0|end|-|host"
  "3|final_image|35|1|0|0|0|fc|-|final_image"
  "4a|lower_levels|180|0|0|0|0|host|-|scripts/_run_lower_levels.sh L3"
  "4b|flash_tier|120|0|0|1|136|pytest|-|flash_tier"
  "5|bench_tier|180|0|0|0|66|pytest|-|bench"
  "7|gated|120|0|122|13|0|pytest|NeoPixel rig|gated"
  "8|flash_cycles|90|5|0|0|0|fc|LWIP_CONTROL_IMAGE|flash_cycles"
  "9|crc16_hazards|10|0|0|0|0|pytest|-|hazards"
  "10a|soak_short|30|0|0|0|8|pytest|-|soak short --deselect=$HOTSPOT"
  "10b|hotspot_case_b|60|0|4|0|2|pytest|-|hotspot_b"
  "10m|soak_mid|75|0|0|0|8|pytest|-|soak mid --deselect=$HOTSPOT"
  "10c|soak_long_clock_stretch|380|0|0|0|0|pytest|-|soak long -k test_scd30_real_clock_stretch_never_exceeds_the_configured_timeout"
  "10d|soak_long_core_headroom|380|0|0|0|0|pytest|-|soak long -k test_single_core_timing_headroom_holds_under_normal_full_task_load"
  "10e|soak_long_bus_triggers|380|0|0|0|0|pytest|-|soak long -k test_bus_triggers_keep_their_minimum_spacing"
  "10f|soak_long_hammer|380|0|0|0|0|pytest|-|soak long -k test_real_hardware_survives_extended_max_speed_hammer_load_with_fram_diagnostics_preserved"
  "10g|soak_long_http_S4|380|0|0|0|0|pytest|-|soak long -k test_http_soak_stays_live"
  "10h|soak_long_frc_baseline|380|0|0|0|0|pytest|-|soak long -k test_scd30_frc_readiness_baseline"
  "11|fram_8mhz|125|0|0|0|0|slice|FRAM_HOURS (2)|fram"
  "12a|boot_stretch|3|0|0|0|0|end|step 1 evidence|mpc boot_stretch_final.py 120"
  "12b|ring_peak|13|0|0|0|0|end|step 1 evidence|mpc ring_peak_final.py 720"
  "12c|dns_idle_poll|5|0|0|0|0|end|stored Wi-Fi config|dns_idle"
  "12d|reset_errors_budget|6|0|0|0|0|end|DUT_IP, step 1 evidence|reset_errors"
  "12e|general_call_per_chip|2|0|0|0|0|end|-|mp $HM/general_call_per_chip.py 60"
  "12f|held_sda_resets|8|0|0|0|0|end|DUT_IP; owner: scope optional|held_sda"
  "13|country_scan|3|0|0|0|0|end|owner: AP on channel 13, CH13=1|country"
  "16b|bmp3xx_probe|3|0|0|0|0|end|owner: power cycle, then rerun|probe bmp3xx_conformance_probe.py"
  "15|rollover|170|2|0|0|0|fc|-|rollover"
)

stopping() { [ -f "$H/STOP" ]; }
saved() { grep -q '^DONE' "$L/1.log" 2>/dev/null; }  # step 1's raw FRAM dump finished
py() { python3 "$H/round1.py" "$@"; }
flash_tier() { scripts/run_flash_hardware_suite.sh --skip-lower-levels "${DUTARG[@]}" "$@"; }
soak() { scripts/run_bench_soak_tests.sh --duration "$@" "${DUTARG[@]}"; }
hazards() { flash_tier -k "test_comm_hazards_are_serialised_refused_or_recovered and crc16"; }
probe() { mp "$(render "$1")" 120; }

up() {  # waits up to $1 s for the board to answer a RAM-only exec (October's)
  for _ in $(seq 1 "$1"); do timeout 15 "$MPC" exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done
  echo "board not back after $1 s"
  return 1
}

mp() {  # one script under `mpremote run` once the board answers; it succeeded when it printed DONE
  up 60 || return 1
  timeout "$2" "$MPC" run "$1" 2>&1 | tee "$L/mp.out"
  echo "rc=${PIPESTATUS[0]} $(date -u +%T)"
  grep -q '^DONE' "$L/mp.out"
}

mpc() {  # an October script that boots or resets the product: CONFIRM (and any further -e) by sed, after step 1
  saved || { echo "SUM refused: step 1's raw FRAM dump is not in logs/1.log"; return 1; }
  sed -e 's/^CONFIRM = False/CONFIRM = True/' "${@:3}" "$HM/$1" > "$L/$1"
  mp "$L/$1" "$2"
}

render() {  # the harness's rendering of one device script (bench facts and includes inlined); prints its path
  uv run --no-sync python -c "import sys; sys.path.insert(0, 'tests_hardware'); from pathlib import Path
from harness import render_device_script; print(render_device_script(Path('tests_hardware/device_scripts/$1')))"
}

flash() {  # one flash cycle of the final image (October's): the bootloader, then picotool until BOOTSEL is there
  timeout 15 "$MPC" bootloader
  for i in 1 2 3 4 5; do sleep 3; sudo picotool load -x -v "$UF2" && return 0; echo "picotool attempt $i failed"; done
  return 1
}

evidence() {  # row 1: /status if the product answers (it touches nothing), then the raw FRAM on the image as found
  py get status 5 "$L/status_before.json"
  timeout 600 "$MPC" run "$(render fram_raw_dump.py)"; echo "rc=$?"
  saved
}

host() {  # row 2: env --tier bench once more (no password or SSID line reaches the log), then the apt packages
  uv run toolchain/setup_toolchain.py env --tier bench 2>&1 | grep -ivE 'password|ssid|psk'
  local rc=${PIPESTATUS[0]} pk
  mapfile -t pk < <(uv run --no-sync python -c 'import tomllib; print(*tomllib.load(open("toolchain/versions.toml", "rb"))["toolchain"]["apt_packages"], sep="\n")')
  # shellcheck disable=SC2016
  dpkg-query -W -f '${Package} ${Version}\n' "${pk[@]}"
  return "$rc"
}

final_image() {  # row 3: the final dev image built and flashed (FC 1), then /system's BuildDate against its record
  uv run --no-sync scripts/build_firmware.py dev 2>&1 | tail -n 40
  [ "${PIPESTATUS[0]}" = 0 ] && flash && py get system 180 "${UF2%.uf2}.json"
}

bench() {  # the bench runner's own L4 line: the runner re-runs L3 under set -e and stops at step 4b's known FAILs
  scripts/_require_clean_hardware_run.sh --runner run_bench_hardware_suite --levels L4 --marker-floor "$FLOOR" \
    --not-clean-reason "L0-L2 ran in step 4a, L3 in step 4b" tests_hardware/bench "${DUTARG[@]}" "$@"
}

gated() {  # row 7: the gated tests alone; the hotspot module's owned writes run once, whole, in step 10b
  local g=(--allow-persistence-write --allow-scd30-extra-write --allow-neopixel-sweep -m "persistence_write or scd30_extra_write or neopixel_sweep")
  flash_tier "${g[@]}"
  stopping || bench "${g[@]}" --deselect="$HOTSPOT"
}

flash_cycles() {  # row 8, FC 1 + 2 + 2: without LWIP_CONTROL_IMAGE the unpatched send-stall test is deselected
  local c=(--allow-flash-cycle -m flash_cycle) x=(--deselect=tests_hardware/bench/test_modlwip_send_stall.py::test_send_stall_on_the_unpatched_image)
  [ -z "${LWIP_CONTROL_IMAGE:-}" ] || x=(--lwip-control-image "$LWIP_CONTROL_IMAGE")
  [ -n "${LWIP_CONTROL_IMAGE:-}" ] || echo "NOTE LWIP_CONTROL_IMAGE unset: test_send_stall_on_the_unpatched_image deselected, owed"
  flash_tier "${c[@]}"
  stopping || bench "${c[@]}" "${x[@]}"
}

hotspot_b() {  # row 10's case (b) as BACKLOG states it, the module whole: the soak runner's floor would run (b) alone
  scripts/_require_clean_hardware_run.sh --runner run_bench_soak_tests_hotspot --levels "soak duration long (not a level)" \
    "$HOTSPOT" --soak-duration long --allow-persistence-write "${DUTARG[@]}"
}

fram() {  # row 11's 10 h at 8 MHz as SLICE_S slices for FRAM_HOURS (whole hours), STOP read between slices
  local end=$(($(date +%s) + ${FRAM_HOURS:-2} * 3600))
  sed "s/^DUR_S = .*/DUR_S = $SLICE_S/" "$HM/long_fram.py" > "$L/long_fram.py"
  while [ $(($(date +%s) + SLICE_S + 120)) -le "$end" ] && ! stopping; do
    mp "$L/long_fram.py" $((SLICE_S + 120)) || up 120 || return 1
  done
}

dns_idle() {  # row 12c: the board's half, then the host's queries once it prints READY (October's net())
  local ip
  up 60 || return 1
  : > "$L/12c.board"
  timeout 300 "$MPC" run "$HM/dns_idle_poll.py" > "$L/12c.board" 2>&1 &
  for _ in $(seq 1 150); do grep -q '^READY' "$L/12c.board" && break; sleep 1; done
  ip=$(grep -m1 '^IP=' "$L/12c.board" | cut -d= -f2 | tr -d '\r')
  [ -z "$ip" ] || python3 "$HM/host_dns_query_timing.py" "$ip"
  wait
  cat "$L/12c.board"
}

reset_errors() {  # row 12d: "wipe" answered without a prompt, only once step 1's evidence exists; the logs read first
  if ! saved || [ -z "${DUT_IP:-}" ]; then echo "SUM reset_errors refused: no step 1 evidence or no DUT_IP"; return 1; fi
  py get status 180 && echo wipe | python3 "$HM/host_reset_errors_timing.py" "$DUT_IP"
}

held_sda() {  # row 12f: SDA held, then each reset kind; /status and /sensors once the product serves again
  local m
  for m in machine_reset watchdog; do
    mpc held_sda_reset.py 60 -e "s/^MODE = .*/MODE = \"$m\"/"
    py get status 180 && py get sensors 30
  done
}

country() {  # row 13: only with CH13=1, the owner's access point on channel 13 in range
  [ "${CH13:-0}" = 1 ] || { echo "NOTE country scan skipped: CH13=1 not set"; return 0; }
  mp "$HM/country_scan.py" 120
}

rollover() {  # row 15: the tick-offset image's two hours (FC 1), then the final image back unless it already runs
  scripts/run_bench_rollover_test.sh "${DUTARG[@]}"
  py get system 180 "${UF2%.uf2}.json" || { flash && py get system 180 "${UF2%.uf2}.json"; }
}

handback() {  # rebuilds HANDBACK.md and pushes it to the bench branch, with October's retries
  printf '%s\n' "${STEPS[@]}" | py handback "$L" "$HB" || return 1
  git add -f "$HB" && git commit -q -m "Round 1 bench hand-back, $(date -u '+%F %H:%M') UTC [skip ci]" -- "$HB" || return 0
  local w=2
  for _ in 1 2 3 4 5; do git push -q origin "HEAD:refs/heads/$BRANCH" && return 0; sleep "$w"; w=$((w * 2)); done
  echo "push failed; HANDBACK.md is committed locally" >&2
}

interrupt() {  # SIGINT once per pid: each pytest in the step's session (its summary still prints), or a host step's session
  local p ps=-$1
  [ "$2" = host ] || ps=$(pgrep -s "$1" -f bin/pytest)
  for p in $ps; do case "$SENT" in *" $p "*) ;; *) kill -INT -- "$p"; SENT="$SENT$p " ;; esac; done
}

step() {  # one step in its own session, so a terminal's Ctrl-C reaches only this runner; STOP read every 10 s
  local id=$1 kind=$2 log=$L/$1.log t0 pid rc
  SENT=" "
  t0=$(date +%s)
  echo "== step $id start $(date -u '+%F %T') $t0" >> "$log"
  setsid bash "$ME" _body "$id" >> "$log" 2>&1 < /dev/null &
  pid=$!
  while kill -0 "$pid" 2>/dev/null; do
    sleep 10
    case "$kind" in pytest | host) ! stopping || interrupt "$pid" "$kind" ;; esac
  done
  wait "$pid"
  rc=$?
  echo "== step $id end rc=$rc $(date -u '+%F %T') $(($(date +%s) - t0))s" >> "$log"
  [ -z "${DUT_IP:-}" ] || { echo "== read-across: GET /status after step $id"; py get status 180; } >> "$log" 2>&1
  handback
}

index() {  # a step id's position in STEPS
  local i
  for i in "${!STEPS[@]}"; do [ "${STEPS[i]%%|*}" = "$1" ] && { echo "$i"; return 0; }; done
  return 1
}

list() {  # each step: id, name, expected time, the sheet's wear maxima, how a STOP ends it, what it needs
  local r id name min fc fs nvm pre stop needs
  printf '%-4s %-24s %5s %3s %4s %4s %4s  %-6s %s\n' step name time FC FS NVM pre stop needs
  for r in "${STEPS[@]}"; do
    IFS='|' read -r id name min fc fs nvm pre stop needs _ <<< "$r"
    printf '%-4s %-24s %2dh%02d %3s %4s %4s %4s  %-6s %s\n' "$id" "$name" $((min / 60)) $((min % 60)) "$fc" "$fs" "$nvm" "$pre" "$stop" "$needs"
  done
  echo "FS/pre: flash-filesystem writes owned/prerequisite (the sheet's maxima). stop: pytest = SIGINT to its pytest, host ="
  echo "SIGINT to the step, both at once; fc = holds a flash cycle, never interrupted; end, slice = at its or a slice's end."
}

run_range() {  # continues the fetched bench branch, then runs the inclusive range FROM..TO in table order
  local a b i id kind
  if ! a=$(index "${1:-}") || ! b=$(index "${2:-${1:-}}") || [ "$a" -gt "$b" ]; then usage; return 2; fi
  if [ "$(git rev-parse --abbrev-ref HEAD)" = "$BRANCH" ]; then
    git pull -q --ff-only origin "$BRANCH" || echo "pull failed: continuing the local $BRANCH" >&2
  else
    { git fetch -q origin "$BRANCH" && git checkout -q -B "$BRANCH" FETCH_HEAD; } || return 1
  fi
  mkdir -p "$L" && chmod 700 "$L"
  rm -f "$H/STOP"
  scripts/uv_sync_retried.sh > "$L/sync.out" 2>&1 || { cat "$L/sync.out"; return 1; }
  trap 'touch "$H/STOP"; handback' INT TERM HUP
  trap 'handback; rm -f "$H/STOP"' EXIT
  for ((i = a; i <= b; i++)); do
    IFS='|' read -r id _ _ _ _ _ _ kind _ <<< "${STEPS[i]}"
    stopping && { echo "$(date -u '+%F %T') STOP found: ending before step $id" >> "$L/runner.log"; exit 0; }
    step "$id" "$kind"
  done
}

usage() { echo "usage: $0 list | run FROM [TO] (TO defaults to FROM) | summary" >&2; return 2; }

main() {
  case "${1:-}" in
    list) list ;;
    summary) if [ -f "$HB" ]; then sed -n '1,/^## Logs/p' "$HB"; else echo "no hand-back yet"; fi ;;
    run) shift; run_range "$@" ;;
    _body) local r cmd; r=${STEPS[$(index "$2")]}; read -ra cmd <<< "${r##*|}"; "${cmd[@]}" ;;
    *) usage ;;
  esac
}
main "$@"; exit $?
