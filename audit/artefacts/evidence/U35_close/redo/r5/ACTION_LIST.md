# R5 lead action list (2026-11-05)

1. Lane A (closure rows with no round-1 wait and no owner input), brief `BRIEF_R5A.md`, hand-back `HANDBACK_R5A.md`:
   `audit/r5a` 843eb19d (+51/-250). Reviewed: removals and pointers only, the two empty pending lists and their
   stale-entry halves gone, no secret in the added text (hash check), A.11 row 8 lost only a dead BACKLOG pointer.
2. Lead follow-up 8daca22b: F4's header narrowed (per-CS-cycle allocation; a few bytes per setup pass, R3 plants
   118-125); five dead BACKLOG pointers in tests/ comments; 2 citation and 4 vocabulary allow-list rows deleted (they
   matched only removed sentences). Checks r5L_chk3: citations, vocabulary, comment cap 675 passed; lint rc=0.
3. Merge into int after the R4 gate (not during it). Left for later units: F9/B01/U02 (Any baselines, allow-lists),
   U01 (dependency check), B06 (golden fixture), the 40 rows waiting on round 1, the 6 owner rows; BACKLOG's numbering
   paragraph (item 2 alone) goes to the owner with the R5 items.
4. FINDINGS 12.6 classified (b + a firmware deviation from F.2's rung rule). Owner 12:04 UTC: "Option A" - fix before
   the final image; the bench holds `run 3` until the fix is on the bench branch. Fix unit started on `S/wt-rung`
   (`audit/rung` from 3c402f85), brief `BRIEF_RUNG.md`; then the lead's gate, a falsification check, the merge into
   int, the cherry-pick onto the bench branch, pushed only when the bench asks and pulls at once.
5. Rung fix reviewed (one counter, one mark; the re-mark line correctly gone); falsification held; the lead fixed the
   comment ("entered", within 120 columns) and the SPEC bus-recovery sentence (9c365a27). int at 5f763f25; the gate
   (`rungL_gate`) waits for the heavy slot behind proof run 1's fast gate. Not taken: the twin test asserting which
   reader ran which rung (the mock tests pin it). Then: cherry-pick onto the bench branch, pushed when the bench asks.
