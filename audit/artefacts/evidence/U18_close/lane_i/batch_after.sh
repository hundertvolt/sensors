#!/bin/bash
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
tag=${1:-after}
for f in test_readiness_gates test_neopixel_wifi_integration test_setter_microdot_integration test_ntp_wifi_dns_integration test_ntp_fram_system_integration; do
  for m in std thr cov; do
    $S/u18i/run.sh tests/$f.py $m $tag
  done
done
echo DONE-$tag >> $S/u18i/logs/summary.txt
