#!/bin/bash
# run.sh <label> <tree: pre|head> <script> <log>: one reproduction in the namespace, logged in RUNS.md
label=$1; tree=$2; script=$3; log=$4
if [ "$tree" = pre ]; then MP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35r/scan/work_C/pre/tests:/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35r/scan/work_C/pre/src:.frozen; else MP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u35int/build/generated_src:/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u35int/src:/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u35int/tests:.frozen; fi
cmd="unshare -n /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u24/ns_xdg.sh nice -n 19 env MICROPYPATH=$MP /root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M $script"
cd /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35r/scan/work_C
$cmd > "$log" 2>&1 &
pid=$!
echo "| RUNNING $(date -u +%H:%M:%S) $(date -u +%Y-%m-%d) | U35 scan C $label pid $pid | /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35r/scan/work_C | $cmd | $(date -u +%H:%M:%S) |" >> /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u21/RUNS.md
wait $pid; rc=$?
echo "| done $(date -u +%H:%M) rc=$rc | U35 scan C $label pid $pid |" >> /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u21/RUNS.md
echo "rc=$rc"
