#!/bin/bash
# heavy.sh: count heavy processes on the host and list them (mine marked by the wt-u23o cwd is not visible here).
ps -eo pid,etime,args | grep -E 'node .*vitest|ports/unix/build-[a-z]*/micropython|python[0-9.]* .*-m pytest|python[0-9.]* .*pytest|bin/mypy|tsc |eslint' | grep -v -E 'grep|heavy.sh|runs.py|^ *[0-9]+ +[0-9:-]+ (timeout|nice|unshare|/bin/bash|bash|sh) ' > /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u23/of111/heavy.now
echo "heavy=$(wc -l < /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u23/of111/heavy.now)"
cut -c1-170 /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u23/of111/heavy.now
