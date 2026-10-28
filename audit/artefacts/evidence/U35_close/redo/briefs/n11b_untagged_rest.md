# N11b: the remaining untagged waits (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/n11_untagged_waits.md` (your task; its items 1 and 2
and its proof apply) and `n11_launch.md` (its scope boundary and load rules stand), and the hand-back
`S/u35r/handbacks_redo/N11.md`. Worktree `S/wt-u35n11`, branch `audit/u35-n11` at 9bbb5930 (clean). Logs in
`S/u35/laneN/n11b/`; N11's in `S/u35/laneN/n11/` (its tools/, scans, AST comparisons, measure scripts and wrapper).

## The lead's review of N11 (binding)
- 26af8dad, 3e30cd19 and 9bbb5930 are kept as written: the identity probe and its planted collection; 15 + 9
  constants, each with its tag and row, AST-identical; the measured Basis; the register bites.
- The real-time values in the run_generic_integration test that the scanner cannot see are owed by N.1's rule, like
  any other: `_serve_until(0.2, ...)` (waited out), the timer periods, the `range(100)` poll count, the
  `_LOOP_LAG_REPORT_MS` settings and the `_test_loop_lag` intervals. Class each one; a tuned one gets its constant,
  tag and row. `_serve_until(30.0, ...)` is a bound: class it as one.
- Name the scanner's blind spot (a value that reaches a wait through a call or an assignment) in your hand-back
  with the shapes it misses. Do not change the scanner (it is N10's lane tool, not a repo check).

## Items, in order
1. The rgi values above, in one commit.
2. Your 38 remaining candidates (N11.md's table), by candidate count, committed per file group green.
3. The timing pairs owed for every changed file, base a42de8b5 against head, back to back at both stages, once mc_cov
   has its done line in RUNS.md. Check uptime and the process list before each pair against CHECKLIST 12, and record
   both. Another lane (CMr1f) also times its own files: one pair at a time is yours.
The 8 candidates in CMr1e's (now CMr1f's) files stay unread and unchanged until that lane is merged.

## Notes
File edits with the Edit or Write tool. A deletion is its own Bash call. Every run through your own run wrapper (copy
N11's), RUNS.md lines naming `U35 lane N11b`. Commit subject `U35 lane N11b: <summary>`, the two trailers; do not
push. A refused command stops you. Count your tool calls; at 80 commit what is green and hand back at a seam with the
remaining list. Hand-back as N11's, plus the scanner's blind-spot shapes; last line "nothing of mine is running".
