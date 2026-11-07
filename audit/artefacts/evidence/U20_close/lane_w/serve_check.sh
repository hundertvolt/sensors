#!/usr/bin/env bash
# usage: serve_check.sh <tree> <device> <log>   (run inside unshare -n)
# Boots one generated device through the twin runner, waits for "Serving forever", serves 12 s past it
# (one 8 s WDT period and then some, so a starved supervisor would show), then SIGINTs and reads the shutdown line.
tree="$1"; device="$2"; log="$3"
cd "$tree" || exit 99
ip link set lo up
rm -rf digital_twin/config
start=$(date +%s)
env TZ=UTC MICROPYPATH="build/generated_src:src:digital_twin:ext:frozen_modules:.frozen" nice -n 19 \
  /root/pico-toolchain/micropython/ports/unix/build-standard/micropython digital_twin/run_generic_integration.py \
  --module "sensortask_$device" --wiring-plan "build/generated_src/sensortask_${device}_wiring_plan.json" \
  --device "$device" --host 127.0.0.1 --port 18080 > "$log" 2>&1 &
pid=$!
for _ in $(seq 1 240); do
  grep -q 'Serving forever' "$log" && break
  kill -0 "$pid" 2>/dev/null || break
  sleep 0.5
done
served=$(( $(date +%s) - start ))
if grep -q 'Serving forever' "$log"; then
  sleep 12
  kill -INT "$pid"
fi
for _ in $(seq 1 60); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
kill -0 "$pid" 2>/dev/null && { echo "still alive after SIGINT, killing" >> "$log"; kill -KILL "$pid"; }
wait "$pid"; ec=$?
echo "device=$device serving_after_s=$served exit=$ec" >> "$log"
grep -E 'Serving forever|shutdown:|interrupted|device=' "$log"
