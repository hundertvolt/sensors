#!/bin/bash
# heavy.sh: count heavy processes on the host (vitest, pytest, micropython, mypy, tsc, eslint runs), and list them.
ps -eo pid,etime,args | grep -E 'node .*vitest|micropython|python[0-9.]* .*-m pytest|python[0-9.]* .*pytest|bin/mypy|tsc |eslint' | grep -v -E 'grep|heavy.sh| timeout |/bin/bash|sh -c|npm exec|unshare|ns.sh| nice ' > /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u23/lead2/heavy.now
echo "heavy=$(wc -l < /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u23/lead2/heavy.now)"
cut -c1-160 /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u23/lead2/heavy.now
