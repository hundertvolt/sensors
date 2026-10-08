#!/bin/bash
# usage: simrun.sh <test file> [sim|nosim]  - per-test timing, optional sim dir ahead of src
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $S/wt-u18i
pre=""
[ "$2" = "sim" ] && pre="$S/u18i/sim:"
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='${pre}build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 /root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M $S/u18i/timed.py $1" 2>&1
echo "rc=$?"
