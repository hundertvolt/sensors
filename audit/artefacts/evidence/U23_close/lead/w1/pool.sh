#!/bin/bash
# pool.sh: run every file in u23/w1/mp_files.txt but the lwIP one through one_file.sh, at most CAP at once, where
# CAP = 4 minus the step-3 scripts still running (pids in u23/w1/step3.pids); heavy files first. Then lwIP alone.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; W=$S/u23/w1
heavy="tests/test_digital_twin_bus_hazard_concurrency.py tests/test_sensortask_dev.py tests/test_asy_wifi_service.py tests/test_digital_twin_sensortask_integration.py tests/test_sensortask_wozi.py tests/test_uart_comm_hazard.py tests/test_asy_sgp40_driver.py tests/test_sensortask_schlafzi.py tests/test_sensortask_klkizi.py tests/test_sensortask_grkizi.py tests/test_sensortask_arzi.py tests/test_digital_twin_real_website_integration.py tests/test_asy_webserver_service.py"
order=()
for f in $heavy; do grep -qx "$f" $W/mp_files.txt && order+=("$f"); done
while read -r f; do [[ " ${order[*]} " == *" $f "* ]] || [[ "$f" == tests/lwip_host/* ]] || order+=("$f"); done < $W/mp_files.txt
step3_alive() { local n=0 p; for p in $(cat $W/step3.pids 2>/dev/null); do kill -0 "$p" 2>/dev/null && n=$((n+1)); done; echo $n; }
for f in "${order[@]}"; do
  while :; do cap=$((4 - $(step3_alive))); [ "$(jobs -rp | wc -l)" -lt "$cap" ] && break; sleep 2; done
  $W/one_file.sh "$f" &
done
wait
while [ "$(step3_alive)" -gt 0 ]; do sleep 5; done
for f in $(grep '^tests/lwip_host/' $W/mp_files.txt); do $W/one_file.sh "$f"; done
echo "pool done $(date +%H:%M:%S)" >> $W/mp/verdicts.txt
