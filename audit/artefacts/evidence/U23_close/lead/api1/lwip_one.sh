#!/bin/bash
# lwip_one.sh <tag> [32768]: the lwIP host file alone on build-lwip in its own netns (wt-u23api), at -1 or 32768.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $S/wt-u23api || exit 2
LW=/root/pico-toolchain/micropython/ports/unix/build-lwip/micropython
MPP=build/generated_src:src:tests:frozen_modules:.frozen
if [ "${2:-}" = 32768 ]; then cmd=(tests/_threshold_runner.py tests/lwip_host/test_modlwip_eagain.py 32768); else cmd=(tests/lwip_host/test_modlwip_eagain.py); fi
unshare -n $S/u22/api5/ns.sh env TZ=UTC MICROPYPATH="$MPP" nice -n 19 timeout 300 $LW -X heapsize=16M "${cmd[@]}" > $S/u23/api1/lwip_$1.log 2>&1
echo "rc=$?" >> $S/u23/api1/lwip_$1.log
