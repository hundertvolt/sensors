#!/bin/bash
# usage: probe.sh <device> <overlay dir or "none">
SP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
WT=$SP/wt-u19s
OV=$2
if [ "$OV" = none ]; then MP="build/generated_src:src:tests:frozen_modules:.frozen"; else MP="$OV:build/generated_src:src:tests:frozen_modules:.frozen"; fi
unshare -n bash -c "ip link set lo up; cd $WT; TZ=UTC MICROPYPATH='$MP' nice -n 19 timeout 300 /root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M $SP/u19s_tools/probe/probe_sensors_get.py $1"
