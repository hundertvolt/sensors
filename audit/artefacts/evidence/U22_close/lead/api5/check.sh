#!/usr/bin/env bash
# Lead checks on wt-u22api with the gate1 fixes (uncommitted): ruff (8 scopes), mypy x4, collect-only, then the WHOLE
# tests_scripts tier (not a subset) beside the changed twin file at both GC stages, then the generic-runner twin file.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; W=$S/wt-u22api; O=$S/u22/api5; V=/home/user/sensors/.venv/bin
MP=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
MPP="build/generated_src:src:tests:frozen_modules:.frozen"
cd "$W" || exit 1
[ -e typings ] || ln -s $S/wt-u8/typings typings
r() { local n=$1; shift; local t0; t0=$(date +%s.%N); "$@" > "$O/$n.log" 2>&1; local rc=$?; printf '%s rc=%s %.1fs %s\n' "$n" "$rc" "$(echo "$(date +%s.%N) - $t0" | bc)" "$(tail -1 "$O/$n.log" | cut -c1-120)" >> "$O/summary.txt"; }
: > "$O/summary.txt"
r ruff nice -n 19 $V/ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts
r mypy_noargs nice -n 19 $V/mypy --cache-dir=/dev/null
r mypy_ci nice -n 19 $V/mypy --cache-dir=/dev/null src tests tests_hardware/device_scripts
r mypy_twin nice -n 19 $V/mypy --cache-dir=/dev/null --config-file digital_twin/typecheck.ini digital_twin tests/test_digital_twin_*.py
r mypy_host nice -n 19 $V/mypy --cache-dir=/dev/null --config-file host_typecheck.ini
r collect_hw nice -n 19 $V/python -m pytest -q -p no:cacheprovider --collect-only tests_hardware
r pytest_all unshare -n /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u22/api5/ns.sh env PYTHONPATH=scripts nice -n 19 $V/python -m pytest -q -p no:cacheprovider tests_scripts &
r twin_e unshare -n /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u22/api5/ns.sh env TZ=UTC MICROPYPATH="$MPP" nice -n 19 timeout 300 $MP -X heapsize=16M tests/test_digital_twin_wifi_modes.py &
r twin_f unshare -n /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u22/api5/ns.sh env TZ=UTC MICROPYPATH="$MPP" nice -n 19 timeout 300 $MP -X heapsize=16M tests/_threshold_runner.py tests/test_digital_twin_wifi_modes.py 32768 &
wait
r generic_e unshare -n /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u22/api5/ns.sh env TZ=UTC MICROPYPATH="$MPP" nice -n 19 timeout 300 $MP -X heapsize=16M tests/test_digital_twin_run_generic_integration.py
r generic_f unshare -n /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u22/api5/ns.sh env TZ=UTC MICROPYPATH="$MPP" nice -n 19 timeout 300 $MP -X heapsize=16M tests/_threshold_runner.py tests/test_digital_twin_run_generic_integration.py 32768
rm -f typings
echo DONE >> "$O/summary.txt"
