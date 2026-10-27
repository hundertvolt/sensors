# CO3: conformance, U10's last cells and U13-U18 (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then `S/u35r/briefs/co2_recovery_rungs_rest.md` (its rules and the lead's decisions stand), then CO2's hand-back
`S/u35r/handbacks_redo/CO2.md` (the state, and its map of existing tests for U13's rows). `co1_recovery_rungs.md`
items 2-4 when a rule is unclear. Worktree `S/wt-u35conf2`, branch `audit/u35-conf2` at 780d2c62 (clean). Logs in
`S/u35/laneB/co3/`.

## The lead's review of CO2 (binding)
- 780d2c62 is kept. The six unverdicted review rows from the CMr1 merge go to lane BR4, not to you; until they are
  done review.md cannot render, so leave the render and name your new tests in the hand-back.
- The timer-pool test that bites only as the run's real-time TimeoutError: give it a bounded wait of its own so a
  failure names its claim, and re-bite it.

## Items, in order (commit per table, each green at both stages)
1. U10's open cells (CO2.md lists them; `_init_*()` R2 closes with U15's rows).
2. U13, U15, U16, U17, U18, in that order. A defect: co1's item 3 rules; a fix outside the files co1 allows is not
   yours, hand it back.
3. Seams: at about 80 tool calls, commit what is green and hand back with the tables and cells left.

## Hand-back (the file, per redo_common)
Commits; cells by table, before and after; every defect with its red-first test; every still-open cell with its
reason; your new tests by name; any question for the owner in prose with a recommendation; last line
"nothing of mine is running".
