#!/bin/bash
R=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u18k_runs
mkdir -p $R/broad2
LIST="$(cat $R/broad_list.txt) tests/test_asy_neopixel_driver.py tests/test_asy_notification_service.py tests/test_asy_isl29125_driver.py tests/test_asy_uart_driver.py tests/test_digital_twin_network_neopixel.py"
for stage in thr std; do
  for f in $LIST; do b=$(basename $f .py); echo "== $stage $b $($R/run1.sh $stage $f $R/broad2/${b}_$stage.log | tr '\n' ' ')"; done
done
for f in tests/test_asy_sgp40_driver.py tests/test_fram_integration.py; do b=$(basename $f .py); echo "== cov $b $($R/run1.sh cov $f $R/broad2/${b}_cov.log | tr '\n' ' ')"; done
echo DONE
