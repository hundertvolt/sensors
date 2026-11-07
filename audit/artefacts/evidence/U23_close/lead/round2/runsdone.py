# runsdone.py <pattern> <result>: mark the last RUNNING line containing <pattern> as done.
import sys
p = "/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u21/RUNS.md"
pat, res = sys.argv[1], sys.argv[2]
lines = open(p).read().split("\n")
for i in range(len(lines) - 1, -1, -1):
    if "RUNNING" in lines[i] and pat in lines[i] and "lead edits 2" in lines[i]:
        lines[i] = lines[i].replace("| RUNNING ", "| done " + res + "; was ", 1)
        break
else:
    sys.exit("no line")
open(p, "w").write("\n".join(lines))
