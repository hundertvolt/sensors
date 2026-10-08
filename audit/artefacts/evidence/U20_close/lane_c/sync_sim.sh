#!/bin/bash
# Copies lane C's worktree into a scratch simulation tree and overlays stand-ins for the parallel
# lanes' WIP contracts (K1, S1, B1, P1 per lane plan section 3). Never touches the worktree itself.
set -euo pipefail
SP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
WT=$SP/wt-u20c
SIM=$SP/u20c/sim
rm -rf "$SIM"
mkdir -p "$SIM"
tar -C "$WT" -cf - --exclude=./.git --exclude=./audit --exclude=./arduino --exclude=./legacy --exclude=./datasheets --exclude=./build --exclude=./node_modules --exclude='*/__pycache__' . | tar -C "$SIM" -xf -
mkdir -p "$SIM/build/generated_src"
ln -s "$SP/wt-u8/typings" "$SIM/typings"
/home/user/sensors/.venv/bin/python "$SP/u20c/overlay.py" "$SIM"
cd "$SIM" && git init -q && git add -A >/dev/null 2>&1 && echo "sim git index ready"
