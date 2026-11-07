# runs.py start <key> <worktree-desc> <command-desc> | done <key> <result>: OF-129 print agent's RUNS.md lines.
import sys, time
p = "/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u21/RUNS.md"
now = time.strftime("%H:%M:%S", time.gmtime())
if sys.argv[1] == "start":
    key, wt, cmd = sys.argv[2], sys.argv[3], sys.argv[4]
    with open(p, "rb") as f:  # a file left without a final newline must not swallow this line, nor this one the next
        f.seek(-1, 2)
        lead = "" if f.read(1) == b"\n" else "\n"
    with open(p, "a") as f:
        f.write(f"{lead}| RUNNING {now} 2026-10-13 | OF-129 print agent [{key}] | {wt} | {cmd} | {now} |\n")
else:
    key, res = sys.argv[2], sys.argv[3]
    lines = open(p).read().split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith("| RUNNING ") and f"OF-129 print agent [{key}]" in lines[i]:
            lines[i] = lines[i].replace("| RUNNING ", f"| done {now} {res}; was ", 1)
            break
    else:
        sys.exit("no line for " + key)
    open(p, "w").write("\n".join(lines))
