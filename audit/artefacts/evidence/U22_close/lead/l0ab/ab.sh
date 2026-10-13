#!/bin/bash
# ab.sh: the tests_scripts tier on U21's tree (wt-u21api, 895268c) and U22's (wt-u8, 8386afa) at once, same venv and
# flags, each in its own netns, --durations=80: which tests grew between the two gates.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
O=$S/u22/l0ab
PY=$S/wt-u8/.venv/bin/python
NS=$S/u22/api5/ns.sh
run() { local tree=$1 tag=$2; ( cd "$tree" && git rev-parse --short HEAD > "$O/$tag.head" && { time PYTHONPATH=scripts unshare -n "$NS" env TZ=UTC "$PY" -m pytest tests_scripts -q -p no:cacheprovider --durations=80 ; } > "$O/$tag.log" 2>&1; echo "rc=$?" >> "$O/$tag.log" ); }
run $S/wt-u21api u21 & A=$!
run $S/wt-u8 u22 & B=$!
wait $A $B
echo done > $O/DONE
