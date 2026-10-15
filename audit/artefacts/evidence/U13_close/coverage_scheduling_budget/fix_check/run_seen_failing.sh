#!/bin/bash
# Seen-failing-first: each guard on the variant (old clock) and on the fix, same harness; network-isolated.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; W=$S/wt-u13int; V=$S/u13fix
B=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
cd $W
one() { # tag file test
  unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen timeout 600 $B -X heapsize=16M $V/run_one.py $2 $3" > $V/logs/seen_$1.log 2>&1; echo "$1 rc=$? $(grep -E '^(PASS|FAIL)' $V/logs/seen_$1.log | cut -c1-300)"
}
T1=test_a_host_stall_inside_a_stretched_clear_does_not_read_as_a_held_clock
T2=test_a_maximum_length_train_completes_and_still_yields
one i2c_variant $V/var_i2c/test_bus_hazard_multi_device.py $T1 &
one i2c_fixed $W/tests/test_bus_hazard_multi_device.py $T1 &
one uart_variant $V/var_uart/test_digital_twin_uart_link.py $T2 &
one uart_fixed $W/tests/test_digital_twin_uart_link.py $T2 &
wait
