#!/bin/bash
# vt.sh <tree> <key> <vitest file...>: one vitest run in its own netns at nice 19, logged and entered in RUNS.md.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/round4
tree=$1; key=$2; shift 2
cd "$tree" || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
python3 $O/runs.py add "$key" "$(basename "$tree") @ $(git -C $S/wt-u23L rev-parse --short HEAD)" "vitest run $* (own unshare -n, nice 19) > u23/round4/$key.log"
t0=$(date +%s)
unshare -n $S/u22/api5/ns.sh nice -n 19 npx vitest run "$@" > "$O/$key.log" 2>&1
rc=$?
res="rc=$rc $(( $(date +%s) - t0 ))s $(grep -E 'Tests +[0-9]' "$O/$key.log" | tail -1 | sed 's/\x1b\[[0-9;]*m//g' | tr -s ' ')"
python3 $O/runs.py done "$key" "$res"
echo "$key $res"
