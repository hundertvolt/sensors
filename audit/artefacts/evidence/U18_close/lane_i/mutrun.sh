#!/bin/bash
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $S/wt-u18i
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='$2:build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 /root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M $S/u18i/timed.py $1" 2>&1
