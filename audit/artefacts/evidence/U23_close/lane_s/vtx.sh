#!/bin/bash
# vtx.sh <log name> <vitest args...>: one vitest run in its own netns at nice 19 from wt-u23s; prints rc, wall, summary.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $S/wt-u23s || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
log=$1; shift
t0=$(date +%s.%N)
unshare -n $S/u22/api5/ns.sh nice -n 19 npx vitest run "$@" > "$S/u23/laneS/$log.log" 2>&1
rc=$?
echo "rc=$rc wall=$(echo "$(date +%s.%N) - $t0" | bc)"
grep -E 'Counts|Result:' "$S/u23/laneS/$log.log" | head -4
