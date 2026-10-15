# Supervisor double await (SF-U11-08)

`double_await.py` drives `SystemService._supervise()` with a starter whose task always dies, until the restart
budget escalates, and records each `_log_dead_task` call. Run from a worktree root with
`MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen`.
- `run_wt-u11rc.log`: the tree before the fix (d1f3878 + test fixes). The escalating pass breaks before emptying the
  slot; the next pass awaits the same ended task again ("again armed True") and the Unix port segfaults (exit 139):
  the first await had raced asyncio's queued handler call, `core.py` left `t.data` None, the second await raised `None`.
- `run_wt-u11h.log`: the fixed tree (17ee05b). Each ended task is logged once; exit 0.
`upstream_note.md`: the MicroPython `extmod/asyncio/core.py` analysis, a minimal repro and a possible upstream fix
(no issue filed; filing is the owner's decision).
