# Concurrency limits (owner feedback 2026-10-08: "overdone the parallelism ... keep a tight eye on not creating such races again")

Binding for the rest of the audit, lead and every agent. Read before starting any run or agent.
Owner, 2026-10-08, on the paused ramp-up: "No need to completely refrain from parallel work. Just more careful."
The limits below are that care; work inside them runs in parallel. During a gate, writing records (no process
started, no file in a gate worktree touched) is allowed.

## Agents
1. At most 3 agents at once. Before launching, the lead writes the agent's file set into RUNS.md and checks it is disjoint
   from every other running agent's set and from the lead's own pending edits (`comm -12` on the sorted lists).
2. A lane that reported done is not resumed for a fix round. A side finding goes into the scan record or the open
   findings for its later unit. The lead fixes it in this unit only if it blocks the gate.
3. An agent leaves no background process behind. Its hand-back names every run it started and confirms each exited.

## Runs
4. One run at a time per worktree. `tests/_tmp/<key>` is shared by every copy of a test file in a worktree, so two runs
   of one file in one worktree corrupt each other (ROOT_CAUSE.md, U19 and U20 lead evidence). Parallel stages run in
   separate worktrees.
5. Every port-binding run (scripts/test.sh, MicroPython files that serve HTTP or DNS, npm test, twins) runs in its own
   `unshare -n` namespace. Two suites never share one namespace.
6. CPU: outside a gate, at most 4 heavy processes on the host at once (4 cores), counted across the lead and every
   agent. A gate runs only gate_v10.sh's layout (each run its own worktree and netns; three load-bounded phases, since
   gate_v9's single phase pushed dev's 32768 file past 240 s on 2026-10-08 with 108 s alone), and while it runs nothing
   else does: no lead run, no edit in a gate worktree, and at most one file-only agent (no test, build or tool
   process; writes disjoint from the gate's), entered in RUNS.md.
7. Every background run is entered in RUNS.md (pid, worktree, command, start) when started and struck when it exits.
   Before every owner report and before ending a turn: `ps` shows only what RUNS.md lists.
8. No edit in a worktree while a run reads it (seen 2026-10-08: the lead edited two twin files mid-run of the pytest
   tier; that run counts only as a preview). Edit in another worktree, or wait for the run to end.
9. Kill by pid only. A run that dies under load is root-caused, never retried away.
