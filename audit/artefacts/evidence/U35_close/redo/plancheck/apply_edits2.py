import sys
path = sys.argv[1]
text = open(path).read()
def rep(old, new):
    global text
    n = text.count(old)
    assert n == 1, (n, old[:80])
    text = text.replace(old, new)

rep("""- the twelve items of `REPORT.md` 7;
- the FRAM log's W29 history, read before anything is flashed (decision 3, item 4: knowledge only);
- the owner's owed rows (the DMA ring proof, reset reasons 21, 22 and 10+phase, the first unfed watchdog stretch,
  dev's receive-ring peak).""",
"""- `REPORT.md` 7's items 3, 4, 5, 7, 8 and 10, with the optional 12;
- item 11, the owner's owed rows (the DMA ring proof, reset reasons 21, 22 and 10+phase, the first unfed watchdog
  stretch, dev's receive-ring peak);
- the FRAM log's W29 history, read before anything is flashed (decision 3, item 4: knowledge only).
Items 1, 2, 6 and 9 are not run: the owner's decisions of 2026-10-28 settled what they were to decide (the C-stack
reboot stays; the lost-FRAM chain goes and the mempause deadline stays, "No measurement"; NP-5 is reverted).""")

rep("""9. Unforeseen decisions take the smallest change. Each is recorded and shown in the next batch report.""",
"""9. Unforeseen decisions take the smallest change. Each is recorded and shown in the next batch report.
10. **The five checks, before anything is written or shown** (owner, 2026-10-28: "Revise our current plans, so they do
    not contain such glitches anymore."). A ledger row, a finding, a recommendation or an answer to the owner carries
    its evidence, and changes before it is used when the evidence does not hold:
    - where it is: the file and line now and at `25caf528`;
    - what governs it: the pre-audit specification and the owner's rows and rulings, quoted;
    - who uses it: a search over firmware, website, build chain, device files, tests, twin and docs;
    - what the platform does: the pinned MicroPython, Microdot or lwIP source, never a report or memory;
    - how big it is: counted from git, never described.
11. **Falsification as the final verification** (owner, 2026-10-28: "The claim falsification check agent scan seems
    reasonable, too. Add this as a final verification and adapt the run counts accordingly."). The plan check ends
    with independent agents that get the plan's claims and the repository, without the lead's evidence or reasoning,
    and try to refute each claim. The lead verifies every refutation at the source before it changes the plan.""")

rep("""| phase | lane runs (cap) | wall-clock hours (estimate) |
|---|---|---|
| R0 settling | 0 | about 1 |""",
"""| phase | lane runs (cap) | wall-clock hours (estimate) |
|---|---|---|
| P the plan check, before R0 (2026-10-28) | 5 (its falsification agents) | about 2 |
| R0 settling | 0 | 1.5-2 |""")
rep("""| **total before round 1** | **26** | **31-44** |""", """| **total before round 1** | **31** | **33-47** |""")
rep("""These are estimates, not measurements.""",
"""P and R0 were added or corrected by the plan check: P's own runs, and R0's twin-record edits, Unix-port run and twelve
baseline builds (a firmware build takes about a minute on a built toolchain). These are estimates, not measurements.""")

rep("""   - **Decided (owner, 2026-10-28): "A".** Each budget at the top of its estimate: R0 1 h; R1 25 h, 12 runs; R2 8 h,
     6 runs; R3 10 h, 8 runs; R4 12 h, 8 runs; R5 5 h, 4 runs; the last round and D 4 h, 2 runs. A stop with a report
     at 80 % of either; hours count from a phase's go-ahead, without time waiting for the owner.""",
"""   - **Decided (owner, 2026-10-28): "A".** Each budget at the top of its estimate: R0 1 h; R1 25 h, 12 runs; R2 8 h,
     6 runs; R3 10 h, 8 runs; R4 12 h, 8 runs; R5 5 h, 4 runs; the last round and D 4 h, 2 runs. A stop with a report
     at 80 % of either; hours count from a phase's go-ahead, without time waiting for the owner.
   - Applied by the same rule after the plan check: R0 2 h (its estimate is now 1.5-2 h); the plan check 22 h and 5
     runs, the runs added for its falsification agents (owner, 2026-10-28: "adapt the run counts accordingly").""")
open(path, "w").write(text)
print("ok")
