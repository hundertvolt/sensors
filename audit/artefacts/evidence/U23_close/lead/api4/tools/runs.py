#!/usr/bin/env python3
"""runs.py start <worktree> <what> -> prints tag; runs.py done <tag> <status>: edit the matching RUNS.md line."""
import sys, time
P = "/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u21/RUNS.md"
if sys.argv[1] == "start":
    t = time.strftime("%H:%M:%S")
    tag = f"RUNNING {t} 2026-10-13"
    with open(P, "a") as f:
        f.write(f"| {tag} | lead helper (fg) | {sys.argv[2]} | {sys.argv[3]} | {t} |\n")
    print(t)
else:
    t, status = sys.argv[2], sys.argv[3]
    old = f"| RUNNING {t} 2026-10-13 | lead helper"
    lines = open(P).read().split("\n")
    n = [i for i, l in enumerate(lines) if l.startswith(old)]
    assert len(n) == 1, n
    lines[n[0]] = lines[n[0]].replace(f"| RUNNING {t} 2026-10-13 |", f"| {status}; was {t} 2026-10-13 |", 1)
    open(P, "w").write("\n".join(lines))
