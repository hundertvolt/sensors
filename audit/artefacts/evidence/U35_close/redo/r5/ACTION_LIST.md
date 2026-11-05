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
