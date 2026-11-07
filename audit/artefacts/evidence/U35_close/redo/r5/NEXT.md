# R5 next steps (lead, 2026-11-07 17:58 UTC; weekly use at 99 %)
- int `audit/u35-int` b412d1b3 (specfund merged). Snapshot 48 carries it and every record to FINDINGS 12.107.
- bfix running in S/wt-bfix (branch audit/bfix from 18e9d59c; brief r5/BRIEF_BFIX.md): if the container is lost,
  rerun it from the brief. CRC yield change waits for the chip read (owner declined it for now).
- stretch running (read-only, r5/BRIEF_STRETCH.md): the 104-122 ms /status stretch and the 41 ms VOC step.
- After bfix merges: one unit for the owner's five (FINDINGS 12.107) plus STRETCH.md's two identical-result fixes (12.108); then the limit-row corrections of LEVELS_2 (P9).
- Owed to the owner: the hotspot password's doc copies (SPEC 3 lines, audit plan 1, ~20 audit files): remove?
- Owed: the completeness pass and prevention check (12.107); the free-heap wrap-up (web.chunk_bytes margin 1.0-2.2x).
- Bench off until the owner restarts it; the fix image and the CRC chip read wait for it.
