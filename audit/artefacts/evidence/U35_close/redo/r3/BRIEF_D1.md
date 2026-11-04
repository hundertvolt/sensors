# R3 brief, phase B, lane D1: the proof reading (lead, 2026-11-04 16:21 UTC)

Read first: `S/u35r/r1/common_r1.md` (binding; labels start with `r3d1_`), `S/u35r/r3/ROWS.md` (phase A's table; your
rows are named below), `S/u35r/r3/ACTION_LIST.md` (the lead's decisions, binding), PLAN.md's R3 row
(`S/u35r/plan/PLAN.md`). Lane M runs the tests in `S/wt-r3` and plants faults there: never read `S/wt-r3`. Lane D2
reads the same tree for the tables and round 1.

- Read-only, in `S/wt-u35int` at `17688315` (the integration tree: change nothing there; its `build/generated_src`
  from 15:54 is current, so no rebuild). Static walks only, each through `S/u35/lead/run.sh`, seconds long: no test
  runner, no build, no port. A walk that writes into the tree (an `audit/b3/` file) writes into `S/u35r/r3/d1/`
  instead, and `git status` stays as you found it.
- Records go to `S/u35r/r3/d1/`, scratch to `S/u35r/r3/d1/ftmp/` (delete it before the hand-back). The working
  records are reading aids, short, never committed (the one exception to common_r1.md's "no matrices").
- The base for "changed" is `497b3eda` (the audit's R1 start) against `17688315`.

## Your rows (ROWS.md section 1)
1. OR16 (2): read R2's final gate summary's skip and deselect list once; a reason no longer true is a gap.
2. OR19: `redflags.py` and `review_rows.py` on the tree; a verdict for every flagged row whose test or target changed.
   A weak test is a gap (strengthened in place later, its goal kept).
3. OR25: `levels_walk.py` re-rendered; removed mechanisms drop out; an unmapped item is a gap.
4. OR26: `raising_walk.py` for the `src/` modules changed; hand verdicts for the new raise and call sites. A defect
   counts only with a reproduction: write the reproduction as a proposal; lane M runs it in the fix round.
5. OR37 and OR38: read every line R1 and R2 added in `src/`, `buildgen/`, `digital_twin/`, `scripts/`, `js/` and
   the test directories once, plus a whole-tree pattern scan (mass files, unbounded loops and retries, fixed ports,
   unguarded destructive host steps, leaked sockets, timers, tasks and temp dirs). A race needs a forced interleaving
   as its proof: propose it.
6. U35-37: each new `ns_seed_text` and `ns_allow_list` hit classed (a), (b) or (c); an (a) hit is listed for the owner.
7. R2's two carries (`run_digital_twin_ci.sh --only` reaching only the suite's runs; a missing `ss` printing "command
   not found"): two lines for the findings list.

## Gaps
You add nothing to the tree (ACTION_LIST item 3). Each gap: its evidence, the row, the proposed test or fix in one line.

## Hand-back
`S/u35r/r3/HANDBACK_D1.md` (first line "R3 lane D1 hand-back, written by the agent (<date -u>)"): per row met or
remaining with where; the gaps; the owner items; the two findings lines. Your final message: the path, five lines of
totals, and last "nothing of mine is running".
