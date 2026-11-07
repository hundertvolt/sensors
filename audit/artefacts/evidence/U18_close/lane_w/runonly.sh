#!/bin/bash
# usage: runonly.sh <module> <substrings> [overlay] - quick subset run, standard binary, GC default
WT=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u18w
SC=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u18w
MP="build/generated_src:src:tests:frozen_modules:.frozen"
if [ -n "${3:-}" ]; then MP="$3:$MP"; fi
cd "$WT"
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=\"$MP\" nice -n 19 timeout 300 /root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M $SC/only.py $1 $2" 2>&1
