#!/bin/bash
# run_probe.sh <worktree> <test file> <out log> [32768]: one MicroPython test file in a loopback-only netns, at -1 or 32768.
ip link set lo up
cd "$1" || exit 2
B=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
if [ "$4" = 32768 ]; then
    TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen "$B" -X heapsize=16M tests/_threshold_runner.py "$2" 32768 > "$3" 2>&1
else
    TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen "$B" -X heapsize=16M "$2" > "$3" 2>&1
fi
echo "rc=$?" >> "$3"
