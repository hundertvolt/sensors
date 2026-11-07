#!/bin/bash
# vt.sh <test file> <log name>: one vitest file in its own netns at nice 19 from wt-u23s; prints rc, wall, summary.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $S/wt-u23s || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
t0=$(date +%s.%N)
unshare -n $S/u22/api5/ns.sh nice -n 19 npx vitest run "$1" > "$S/u23/laneS/$2.log" 2>&1
rc=$?
t1=$(date +%s.%N)
echo "rc=$rc wall=$(echo "$t1 - $t0" | bc)"
grep -E '^ (FAIL|×)|✓|×|Counts|Result:' "$S/u23/laneS/$2.log" | grep -v '✓' | head -60
