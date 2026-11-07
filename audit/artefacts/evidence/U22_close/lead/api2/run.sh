#!/usr/bin/env bash
# Lead checks on wt-u22api @ P final: ruff, mypy x4, L0 subset, MP spot files at both stages. Sequential, nice 19.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; W=$S/wt-u22api; O=$S/u22/api2; V=/home/user/sensors/.venv/bin; MP=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
cd "$W" || exit 1
[ -e typings ] || ln -s $S/wt-u8/typings typings
r() { local n=$1; shift; local t0=$(date +%s.%N); "$@" > "$O/$n.log" 2>&1; local rc=$?; printf '%s rc=%s %.1fs %s\n' "$n" "$rc" "$(echo "$(date +%s.%N) - $t0" | bc)" "$(tail -1 "$O/$n.log" | cut -c1-120)" >> "$O/summary.txt"; }
: > "$O/summary.txt"
r ruff nice -n 19 $V/ruff check .
r mypy_noargs nice -n 19 $V/mypy --cache-dir=/dev/null
r mypy_ci nice -n 19 $V/mypy --cache-dir=/dev/null src tests tests_hardware/device_scripts
r mypy_twin nice -n 19 $V/mypy --cache-dir=/dev/null --config-file digital_twin/typecheck.ini digital_twin tests/test_digital_twin_*.py
r mypy_host nice -n 19 $V/mypy --cache-dir=/dev/null --config-file host_typecheck.ini
for f in test_buildgen_definitions test_error_catalog test_mypy_any_baseline test_citations test_decision_vocabulary test_comment_block_cap test_code_conventions test_tunables_register test_memory_error_gate_agreement test_lint_ceilings test_host_annotations test_import_placement test_legacy_paths test_fault_or_warning_never_both; do
  r "py_$f" env PYTHONPATH=scripts nice -n 19 $V/python -m pytest -q -p no:cacheprovider "tests_scripts/$f.py"
done
for f in test_neopixel_wifi_integration test_notification_sgp40_integration test_notification_scd30_integration test_asy_notification_service test_asy_neopixel_driver test_readiness_gates; do
  r "mp_e_$f" unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 $MP -X heapsize=16M tests/$f.py"
  r "mp_f_$f" unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 $MP -X heapsize=16M tests/_threshold_runner.py tests/$f.py 32768"
done
grep -l -E 'MemoryError|memory allocation failed' "$O"/mp_*.log > "$O/memerr_files.txt"; echo "memerr files: $(wc -l < "$O/memerr_files.txt")" >> "$O/summary.txt"
rm -f typings
echo DONE >> "$O/summary.txt"
