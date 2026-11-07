# CO2: conformance, the rest of the rung tables (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back), then
`S/u35r/briefs/co1_recovery_rungs.md` (its items 2-4 and Notes are your rules), then CO1's hand-back
`S/u35r/handbacks_redo/CO1.md` (the state). Worktree and branch: given in your launch message (on the integration
head, which carries CO1's three commits and the CMr1 test-side work). Logs in `S/u35/laneB/co2/`.

## The lead's review of CO1 (binding)
- 1aed8126, c1b55e87 and 2e6ea0cd are kept. The fix (recoveries stepped on entry, before the bus-lock wait) is right.
- CO1's question 2 is the lead's call, decided (agent, 2026-10-27): a rung cancelled during its lock wait counts as
  run, accepted. Proof to cite: reader tasks are cancelled only by the shutdown sequence (src/asy_system_service.py,
  the `t.cancel()` loop after "Shutdown: storage quiesced"), after which the unit resets, so no later rung is lost.
  Re-locate the line on your head.
- CO1's question 1 is the lead's call, decided (agent, 2026-10-27): kept as designed. `_init_failed()` states "the
  setup attempt starts its own episode"; two concurrent setup failures each run one controller rebuild, serialized
  by the bus lock, bounded by the restart budget, each warning tied to a real failed setup. Not a defect. Close the
  `_init_*()` R3/R4 race-free cell with that proof (an L2 test that pins it, below).

## Items, in order (commit per table, each green)
1. U10's open cells (CO1.md lists them). The L2 test for a reader's setup failure into `_init_failed()` goes in
   tests/test_digital_twin_bus_hazard_concurrency.py's ladder section, as its own test; lane CMr1h edits the same
   file's SCD30 and erase tests beside you, so touch nothing else in it. Re-triage the FRAM verify_present row (it
   now has a product caller on the chip-loss path) against the U16 rows. Refresh review.md's render so the new
   CO1 test has its row.
2. U13, U15, U16, U17, U18, in that order, under co1's rules. A defect: co1's item 3 rules; a fix outside the
   files co1 allows is not yours, hand it back.
3. Seams: at about 80 tool calls, commit what is green and hand back with the tables and cells left.

## Hand-back (the file, per redo_common)
Commits; cells by table, before and after; every defect with its red-first test; every still-open cell with its
reason; any question for the owner in prose with a recommendation; last line "nothing of mine is running".
