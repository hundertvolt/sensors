#!/bin/bash
# Each plant on a fresh copy of the two src files, both ladder tests via run_one.py, nice 19, own netns.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; P=$S/u15plant; T=$P/tree
B=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
for plant in none P1_no_heater_off P2_rung_per_reader P3_no_bus_clear; do
  cp $S/wt-u15int/src/asy_sgp40_driver.py $S/wt-u15int/src/asy_base_classes.py $T/src/
  [ $plant = none ] || python3 $P/plants.py $T $plant
  for t in test_a_sustained_fault_on_one_twin_chip_climbs_to_the_bus_clear_and_recovers_once_cleared test_two_failing_readers_on_one_bus_run_each_bus_rung_once; do
    ( cd $T && nice -n 19 unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen timeout 600 $B -X heapsize=16M $S/u13fix/run_one.py $T/tests/test_digital_twin_bus_hazard_concurrency.py $t" > $P/logs/${plant}_${t:0:30}.log 2>&1 )
    echo "$plant ${t:0:40} :: $(grep -E '^(PASS|FAIL)' $P/logs/${plant}_${t:0:30}.log | cut -c1-260) $(grep -cE 'Traceback|TimeoutError' $P/logs/${plant}_${t:0:30}.log)"
  done
done
cp $S/wt-u15int/src/asy_sgp40_driver.py $S/wt-u15int/src/asy_base_classes.py $T/src/
