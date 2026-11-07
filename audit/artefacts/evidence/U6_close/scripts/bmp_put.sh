set -u
cd "$1"
rm -rf digital_twin/config
MICROPYPATH="build/generated_src:src:digital_twin:ext:build/generated_html/dev:.frozen" TZ=UTC /root/pico-toolchain/micropython/ports/unix/build-standard/micropython digital_twin/run_generic_integration.py --module sensortask_dev --wiring-plan $PWD/build/generated_src/sensortask_dev_wiring_plan.json --device dev --host 127.0.0.1 --port 8099 --fram-state-path "" --scd30-state-path "" > $2/twin_out.log 2> $2/twin_err.log &
P=$!
for i in $(seq 1 60); do curl -s -o /dev/null http://127.0.0.1:8099/sensors && break; sleep 0.5; done
echo "GET:"; curl -s http://127.0.0.1:8099/sensors | python3 -c 'import json,sys; print(json.load(sys.stdin)["BMP3XX"])'
for v in 0 1 2 1; do
  echo "PUT PressOvers=$v"; curl -s -w ' [%{http_code} %{time_total}s]\n' -X PUT -H 'Content-Type: application/json' -d "{\"BMP3XX\": {\"PressOvers\": $v}}" --max-time 30 http://127.0.0.1:8099/sensors
done
kill -INT $P; wait $P
