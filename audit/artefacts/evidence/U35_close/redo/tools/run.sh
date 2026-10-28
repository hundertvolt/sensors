#!/bin/bash
# run.sh WORKTREE LABEL COMMAND...: the lead's run inside its own network namespace, niced, with RUNS.md lines.
# The command runs under bash -c with the pinned uv, Node, the shared venv and offline uv; output to lead/LABEL.log.
[ -c /dev/null ] || exit 9
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
W="$1"
label="$2"
[ -n "$W" ] && [ -n "$label" ] || { echo "usage: run.sh WORKTREE LABEL COMMAND..."; exit 2; }
shift 2
L="$S/u35/lead"
NS="$S/u24/ns_xdg.sh"
NODE=/root/pico-toolchain/node/node-v24.22.1-linux-x64/bin
avail=$(df --output=avail -B1G / | tail -1 | tr -d ' ')
if [ "$avail" -lt 3 ]; then echo "disk: $avail GB available, below 3 GB - not starting"; exit 3; fi
PRE="export PATH=$S/uvenv/bin:$NODE:\$PATH UV_OFFLINE=1 UV_PROJECT_ENVIRONMENT=$S/wt-base/.venv; source $S/wt-base/.venv/bin/activate"
echo "| RUNNING $(date -u +%T) $(date -u +%F) | U35 lead $label pid $$ | $W | $* | $(date -u +%T) |" >> "$S/u21/RUNS.md"
t0=$(date +%s)
cd "$W" || exit 2
unshare -n "$NS" nice -n 19 bash -c "$PRE; $*" > "$L/$label.log" 2>&1
rc=$?
t1=$(date +%s)
echo "| done $(date -u +%H:%M) rc=$rc | U35 lead $label pid $$ |" >> "$S/u21/RUNS.md"
echo "$label rc=$rc wall=$((t1 - t0))s end=$(date -u +%T)" | tee -a "$L/runs.txt"
exit $rc
