# runs.py start <key> <worktree-desc> <command-desc> | done <key> <result>: OF-111 agent's RUNS.md lines.
import sys, time
p = "/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u21/RUNS.md"
now = time.strftime("%H:%M:%S", time.gmtime())
if sys.argv[1] == "start":
    key, wt, cmd = sys.argv[2], sys.argv[3], sys.argv[4]
    with open(p) as f:
        ends = f.read().endswith("\n")
    with open(p, "a") as f:  # one whole newline-terminated line, so no later append joins it
        f.write(("" if ends else "\n") + f"| RUNNING {now} 2026-10-13 | OF-111 agent [{key}] | {wt} | {cmd} | {now} |\n")
else:
    key, res = sys.argv[2], sys.argv[3]
    lines = open(p).read().split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("| RUNNING ") and f"OF-111 agent [{key}]" in lines[i]:
            lines[i] = lines[i].replace("| RUNNING ", f"| done {now} {res}; was ", 1)
            break
    else:
        sys.exit("no line for " + key)
    text = "\n".join(lines)
    open(p, "w").write(text if text.endswith("\n") else text + "\n")  # every line, the last included, ends in "\n"
