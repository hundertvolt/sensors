#!/bin/bash
# The unit's check list: each file at both GC stages, the held-line file per device, then the planted break.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
T=$S/u35r/r5/rung_twin.sh
for stage in -1 32768; do
  for f in tests/test_asy_base_classes.py tests/test_asy_i2c_driver.py tests/test_asy_scd30_driver.py tests/test_asy_isl29125_driver.py tests/test_digital_twin_bus_hazard_concurrency.py tests/test_digital_twin_hot_replug.py; do
    $T $stage - $f
  done
  for d in dev wozi arzi; do $T $stage $d tests/test_digital_twin_held_i2c_line.py; done
done
echo "PLANT: the controller rung's rebuild check removed"
TZ=UTC MICROPYPATH=$S/u35r/r5/plant:build/generated_src:src:tests:frozen_modules:.frozen $S/tc-int/micropython/ports/unix/build-standard/micropython -X heapsize=16M tests/test_asy_base_classes.py | grep -E "^FAIL|AssertionError|passed,"
