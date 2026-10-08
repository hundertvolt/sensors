#!/bin/bash
# usage: scen.sh <tree> <device> <scenario names...>
TREE=$1; shift
cd "$TREE" || exit 1
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 600 /root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u19i/tools/run_scen.py $*"
