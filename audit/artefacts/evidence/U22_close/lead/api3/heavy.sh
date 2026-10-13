#!/usr/bin/env bash
# Lead merged-tree preview on wt-u22api @ 6d23c7d: the files whose combination is new after the W/P/T merges, both GC
# stages, then dev's before/after timing (P's open gap) at 32768 and settrace. Sequential, nice 19, unshare -n each.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u22/api3; P=/root/pico-toolchain/micropython/ports/unix
MPP='build/generated_src:src:tests:frozen_modules:.frozen'
run() { # name dir binary args...
  local n=$1 d=$2 b=$3; shift 3; local t0=$(date +%s.%N)
  unshare -n bash -c "ip link set lo up; cd '$d' && TZ=UTC MICROPYPATH='$MPP' nice -n 19 timeout 300 $P/$b/micropython -X heapsize=16M $*" > "$O/h_$n.log" 2>&1; local rc=$?
  printf '%s rc=%s %.1fs memerr=%s %s\n' "$n" "$rc" "$(echo "$(date +%s.%N) - $t0" | bc)" "$(grep -c -E 'MemoryError|memory allocation failed' "$O/h_$n.log")" "$(tail -1 "$O/h_$n.log" | cut -c1-100)" >> "$O/heavy_summary.txt"
}
: > "$O/heavy_summary.txt"
A=$S/wt-u22api
for f in test_asy_wifi_service test_neopixel_wifi_integration test_setter_microdot_integration test_digital_twin_network_neopixel test_digital_twin_wifi_modes test_digital_twin_sensortask_integration test_sensortask_wozi test_sensortask_dev test_sensortask_arzi test_sensortask_grkizi test_sensortask_klkizi test_sensortask_schlafzi; do
  run "e_$f" "$A" build-standard "tests/$f.py"
  run "f_$f" "$A" build-standard "tests/_threshold_runner.py tests/$f.py 32768"
done
F=$S/wt-u22fold
run "before_f_test_sensortask_dev" "$F" build-standard "tests/_threshold_runner.py tests/test_sensortask_dev.py 32768"
run "before_cov_test_sensortask_dev" "$F" build-settrace "tests/_coverage_runner.py tests/test_sensortask_dev.py $O/cov_before_dev.json"
run "after_cov_test_sensortask_dev" "$A" build-settrace "tests/_coverage_runner.py tests/test_sensortask_dev.py $O/cov_after_dev.json"
echo DONE >> "$O/heavy_summary.txt"
