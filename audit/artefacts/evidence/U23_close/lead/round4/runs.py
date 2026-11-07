# runs.py add <key> <worktree> <what> | done <key> <result>: one RUNS.md line per run of the round-4 agent.
import sys, time
p = "/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u21/RUNS.md"
now = time.strftime("%H:%M:%S", time.gmtime())
if sys.argv[1] == "add":
    key, wt, what = sys.argv[2:5]
    with open(p, "a") as f:
        f.write(f"| RUNNING {now} 2026-10-13 | round-4 agent [{key}] | {wt} | {what} | {now} |\n")
else:
    key, res = sys.argv[2:4]
    lines = open(p).read().split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("| RUNNING ") and f"round-4 agent [{key}]" in lines[i]:
            lines[i] = lines[i].replace("| RUNNING ", f"| done {now} {res}; was ", 1)
            break
    else:
        sys.exit("no line")
    open(p, "w").write("\n".join(lines))
