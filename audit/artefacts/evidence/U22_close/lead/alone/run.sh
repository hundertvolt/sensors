#!/bin/bash
# run.sh: CPU vs wall of the new twin file alone, then the lwIP file alone at both stages, on 8386afa (wt-u8).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
O=$S/u22/cpu
cd $S/wt-u8 || exit 2
git rev-parse --short HEAD > $O/head.txt
MP=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
LW=/root/pico-toolchain/micropython/ports/unix/build-lwip/micropython
MPP=build/generated_src:src:tests:frozen_modules:.frozen
NS=$S/u22/api5/ns.sh
{ time unshare -n $NS env TZ=UTC MICROPYPATH="$MPP" timeout 300 $MP -X heapsize=16M tests/test_digital_twin_wifi_modes.py ; } > $O/wifi_modes_m1.log 2>&1
echo "rc=$?" >> $O/wifi_modes_m1.log
for i in 1 2 3; do
  { time unshare -n $NS env TZ=UTC MICROPYPATH="$MPP" timeout 300 $LW -X heapsize=16M tests/lwip_host/test_modlwip_eagain.py ; } > $O/lwip_m1_$i.log 2>&1
  echo "rc=$?" >> $O/lwip_m1_$i.log
  { time unshare -n $NS env TZ=UTC MICROPYPATH="$MPP" timeout 300 $LW -X heapsize=16M tests/_threshold_runner.py tests/lwip_host/test_modlwip_eagain.py 32768 ; } > $O/lwip_32768_$i.log 2>&1
  echo "rc=$?" >> $O/lwip_32768_$i.log
done
echo done > $O/DONE
