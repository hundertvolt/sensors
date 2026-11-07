#!/bin/bash
# pool.sh: the 9 step-4 files through one_file.sh (-1 then 32768 each), heavy first; at most CAP at once, where CAP = 4
# minus the step-3 scripts still alive (pids in u23/api5/step3.pids), and a start only while the host runs < 4 heavy.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; W=$S/u23/api5
order=(tests/test_sensortask_dev.py tests/test_asy_wifi_service.py tests/test_sensortask_wozi.py tests/test_sensortask_schlafzi.py tests/test_sensortask_klkizi.py tests/test_sensortask_grkizi.py tests/test_sensortask_arzi.py tests/test_asy_webserver_service.py tests/test_asy_system_service.py)
step3_alive() { local n=0 p; for p in $(cat $W/step3.pids 2>/dev/null); do kill -0 "$p" 2>/dev/null && n=$((n+1)); done; echo $n; }
host_heavy() { echo $(( $(pgrep -cx micropython) + $(pgrep -cf -- '-m pytest') + $(pgrep -cf 'bin/vitest run') + $(pgrep -cf 'bin/mypy ') + $(pgrep -cf 'node .*(eslint|tsc)( |$)') )); }
for f in "${order[@]}"; do
  while :; do cap=$((4 - $(step3_alive))); [ "$(jobs -rp | wc -l)" -lt "$cap" ] && [ "$(host_heavy)" -lt 4 ] && break; sleep 2; done
  $W/one_file.sh "$f" &
  sleep 3
done
wait
echo "pool done $(date +%H:%M:%S)" >> $W/mp/verdicts.txt
