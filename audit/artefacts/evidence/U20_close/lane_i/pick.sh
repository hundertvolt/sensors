#!/bin/bash
# pick.sh <stage gc-1|gc32768> <device> names...
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
stage=$1; shift
MP=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
cd $S/wt-u20i
if [ "$stage" = gc32768 ]; then cmd="$MP -X heapsize=16M tests/_threshold_runner.py $S/u20i_runs/probe_scripts/pick.py 32768"; else cmd="$MP -X heapsize=16M $S/u20i_runs/probe_scripts/pick.py"; fi
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 900 $cmd $*"
