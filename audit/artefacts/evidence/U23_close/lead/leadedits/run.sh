#!/bin/bash
# run.sh <tag> <desc> <cmd...>: RUNS.md line (lead edits, fg), run cmd in wt-u23L into leadedits/<tag>.log, close the line.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; R=$S/u21/RUNS.md; O=$S/u23/leadedits
tag=$1; desc=$2; shift 2
cd $S/wt-u23L || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
st=$(date -u +%H:%M:%S); id="LE-$tag-$st"; head=$(git rev-parse --short HEAD); dirty=$(git status --porcelain --untracked-files=no | grep -q . && echo "+edits")
echo "| RUNNING $st 2026-10-13 [$id] | lead edits (fg) | wt-u23L @ $head$dirty | $desc, nice 19 | $st |" >> $R
t0=$(date +%s); "$@" > $O/$tag.log 2>&1; rc=$?; w=$(( $(date +%s) - t0 ))
python3 - "$R" "$id" "$rc" "$w" <<'PY'
import sys
p, i, rc, w = sys.argv[1:]
s = open(p).read().splitlines(True)
for k, l in enumerate(s):
    if f"[{i}]" in l:
        s[k] = l.replace(f"| RUNNING ", f"| done rc={rc} wall {w} s; was ", 1).replace(f" [{i}]", "")
open(p, "w").write("".join(s))
PY
echo "$tag rc=$rc wall=${w}s"
