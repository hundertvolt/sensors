# CO4: conformance, U13's open cells and U15-U18 (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then `S/u35r/briefs/co3_recovery_rungs_rest.md` (its rules and the lead's decisions stand, CO2's included), then
CO3's hand-back `S/u35r/handbacks_redo/CO3.md` (the state, the open cells, its map of test names for U15).
Worktree `S/wt-u35conf2`, branch `audit/u35-conf2` at CO3's head (clean). Logs in `S/u35/laneB/co4/`.

## The lead's review of CO3 (binding)
- e6408055 and 04cdd831 are kept. Its plant and first runs outside the namespace break CHECKLIST 12 (named); every
  run goes through the wrapper.
- U13's held-line rows (a bus held at power-up, a held SCL; R3, R4): the twin can plant a held line, so their L2 is
  a twin test, not "open". Write them.

## Items, in order (commit per table, each green at both stages)
1. U13's open cells, the held-line twin tests included; U10's still-open cells where a twin test can close them.
2. U15, U16, U17, U18, in that order, under co1's rules. A defect: co1's item 3 rules; a fix outside the files co1
   allows is not yours, hand it back. The UART rows (U17) wait on an owner decision about PieceBuffer catches at
   asy_uart_comm.py's GET/SET sites: cell them on today's code, and mark the two sites "pending owner".
3. Seams: at about 80 tool calls, commit what is green and hand back with the tables and cells left.

## Hand-back (the file, per redo_common)
Commits; cells by table, before and after; every defect with its red-first test; every still-open cell with its
reason; your new tests by name; any question for the owner in prose with a recommendation; last line
"nothing of mine is running".
