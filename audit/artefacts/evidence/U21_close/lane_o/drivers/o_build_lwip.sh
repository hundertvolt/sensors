#!/bin/bash
cd /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad || exit 99
log=$1
start=$(date +%s)
echo "pid=$$ start=$(date -u +%H:%M:%S) head=$(git -C /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u21o rev-parse --short HEAD)+uncommitted" > "$log"
PICO_TOOLCHAIN_DIR=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u21tc-o flock /tmp/sensors-audit-toolchain.lock nice -n 19 /home/user/sensors/.venv/bin/python -u /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u21/o_build_lwip.py /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u21o /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u21tc-o >> "$log" 2>&1
rc=$?
echo "rc=$rc elapsed=$(( $(date +%s) - start ))s end=$(date -u +%H:%M:%S)" >> "$log"
exit $rc
