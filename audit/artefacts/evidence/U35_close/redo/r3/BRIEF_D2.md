# R3 brief, phase B, lane D2: the tables and round 1's preparation (lead, 2026-11-04 16:21 UTC)

Read first: `S/u35r/r1/common_r1.md` (binding; labels start with `r3d2_`), `S/u35r/r3/ROWS.md` (phase A's table; your
rows are named below), `S/u35r/r3/ACTION_LIST.md` (the lead's decisions, binding), PLAN.md's R3 and round 1 rows
(`S/u35r/plan/PLAN.md`). Lane M runs the tests in `S/wt-r3` and plants faults there: never read `S/wt-r3`. Lane D1
reads the same tree for the proof rows.

- Read-only, in `S/wt-u35int` at `17688315` (the integration tree: change nothing there). No run is needed; if one
  is, it is a static walk of seconds through `S/u35/lead/run.sh`, with no test runner, build or port.
- Records go to `S/u35r/r3/d2/`, scratch to `S/u35r/r3/d2/ftmp/` (delete it before the hand-back). The tables are
  reading aids: one line per cell, a test name or a reason in a few words, never committed (the one exception to
  common_r1.md's "no matrices").
- Datasheets: `/home/user/datasheets/` (read-only; see common_r1.md). Cite the document, page and table; never
  copy datasheet text into `d2/` (a PDF text dump goes to `d2/ftmp/` only).
- The base for "changed" is `497b3eda` (the audit's R1 start) against `17688315`.

## Your rows (ROWS.md sections 1 and 2)
1. OR41 with U35-09: the actor × shared-resource table, each cell a reason or an existing test; U35-09's
   recombination × level row. A real interaction with no test anywhere is a gap.
2. OR49: one cell per finite resource (ROWS.md lists them), a test or a reason. Lane M adds A1's test; cite it as
   "A1 (lane M)".
3. U35-52: `audit/b3/conformance.md`'s rung rows; drop the rungs R1 removed, re-check the rest against today's tests.
4. The bus-hazard rule for B3's, B4's and B6's bus-facing changes: three kinds × four tiers, named from the files.
5. The wear table: each hardware test that writes the flash file system or the SCD30 NVM, or reflashes, marked owned
   or prerequisite, with its marker; a wrong marker is a gap. Its sum is round 1's wear budget.
6. P1: round 1's run sheet, in order, each item with its expected outcome and wear (BACKLOG's owed entries, PLAN's
   round 1 list, the carries ROWS.md names). A stale BACKLOG entry is listed, not edited.
7. P4: the desk check that the production-mode bench test runs on the frozen image (the bench's
   `ImportError: frozen_html` on the mounted entry).
8. P7: the chip facts (ROWS.md) against the final drivers' waits and defaults.
9. P8: the hardware facts R1 relied on against the datasheets; a fact with no datasheet here is marked so.

## Gaps
You add nothing to the tree (ACTION_LIST item 3). Each gap: its evidence, the row, the proposed test or fix in one line.

## Hand-back
`S/u35r/r3/HANDBACK_D2.md` (first line "R3 lane D2 hand-back, written by the agent (<date -u>)"): per row met or
remaining with where; the gaps; round 1's sheet path and its wear sum. Your final message: the path, five lines of
totals, and last "nothing of mine is running".
