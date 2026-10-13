#!/bin/bash
# run.sh <label> <log> <cmd...>: logs a RUNS.md line before the run, runs it at nice 19 from wt-u23c, marks it done.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
label=$1; log=$2; shift 2
start=$(date '+%H:%M:%S')
tag="lane C (fg) | wt-u23c @ $(git -C $S/wt-u23c rev-parse --short HEAD)+edits | $label"
echo "| RUNNING $start 2026-10-13 | $tag | $start |" >> $S/u21/RUNS.md
cd $S/wt-u23c || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
t0=$(date +%s)
"$@" > "$log" 2>&1
rc=$?
wall=$(( $(date +%s) - t0 ))
python3 - "$S/u21/RUNS.md" "$start" "$tag" "$rc" "$wall" <<'PY'
import sys
path, start, tag, rc, wall = sys.argv[1:]
lines = open(path).read().split("\n")
old = f"| RUNNING {start} 2026-10-13 | {tag} | {start} |"
for i, l in enumerate(lines):
    if l == old:
        lines[i] = f"| done rc={rc} wall {wall} s; was {start} 2026-10-13 | {tag} | {start} |"
open(path, "w").write("\n".join(lines))
PY
echo "rc=$rc wall=${wall}s"
exit $rc
