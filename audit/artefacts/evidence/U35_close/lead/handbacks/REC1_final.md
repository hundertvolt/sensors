REC1 hand-back (U35 records, first part). Commit `befa1aa` on audit/u35-rec in S/wt-u35rec, on `a81a65a`. Not pushed. Nothing uncommitted.

**Files written**
- `audit/sweeps/scan_runs/20261022_U35_close.md` (new, 420 lines). It has U34's sections. All 179 steps are listed by number: 85 applied, 10 applied in part, 64 check-only, 5 landed, 1 parked, and 14 owned whole by a later block (B2 2, T4 5, D3 7). It also covers the rulings, the scan per class, the modes, the call counts, gate 1 (its three reds with causes and fixes) and CI on U34's squash. Line numbers are at `a81a65a`, stated once.
- `audit/REGISTER.md`: the `| U35 |` unit row now has state `<W10>`. 20 rows follow U34's CI row (now :792-:811), covering everything the brief lists. The LEAD NOTES 111 row is recorded as an agent decision the owner accepted.
- `audit/sweeps/open_findings.md`: 27 rows edited, 21 new (OF-240 to OF-260).
- `S/u35/close/assemble.sh`: syntax-checked only, not run.
- `S/u35/close/squash_msg_draft.txt`: lines at most 100 characters, no audit IDs.
- Every placeholder sits on its own line or cell.

**Findings rows by unit**
- Closed, or settled as accepted:
  - OF-02, OF-05, OF-32, OF-79, OF-81, OF-144, OF-167, OF-180, OF-197, OF-206, OF-207, OF-211, OF-221, OF-226, OF-229, OF-231, and OF-215's stage 3.
  - OF-225 as an accepted degradation (Z `447ae0b`); OF-236 as no regression.
  - New OF-240 (Q `e50f813`).
- In part: OF-60, OF-199, OF-212, OF-233, OF-237.
- Moved:
  - To U36: OF-200, OF-214, and OF-237's residue.
  - OF-181's follow-up to U37.
- New rows by target:
  - U36, route only: OF-241, 242, 243, 245, 248, 249, 250, 252.
  - U37: OF-246, 247, 251.
  - U35 by the fallback rule: OF-244.
  - C: OF-260.
  - Held for later blocks: OF-253 and OF-258 (`<T4>`), OF-254 and OF-255 (`<G3>`), OF-259 (`<D3>`).
  - Withdrawn: OF-256 (`_finish_write()`) and OF-257.

**Agent decisions touching a flash or SCD30-NVM write (CHECKLIST 24)**
- Already answered by the owner:
  - R-9 with P3's slices (LEAD NOTES 46), P4's write-then-rename (52) and the "kept" verdict in 85: all overturned by the 06:32 decision (86).
  - The boot write under the config lock: "1. is good." (88).
- Listed for the owner as questions:
  - (a) Z's sync `_write_file()` helper (101).
  - (b) H2's `_PREREQUISITE_DEVICE_SCRIPTS` row, `50e22ab` (53).
  - (c) D.3's SCD30 exception, `4f44af1` (104).
  - (d) J's SCD30 send pins (103).
  - (e) The hazard command is dispatch-only (12); it avoids a write rather than adding one.

**Left for REC2 beyond the placeholders**
- The OF-71, OF-150, OF-149 and OF-188 rows are unchanged; REC2 updates them after B2 and T4.
- REGISTER :691 ("firmware final at U35's end") is marked `<W10>`.
- Run assemble.sh with the final logs. `evidence_README.md` is not written yet; the script copies it if present.
- Re-check line numbers on the final head.

**Not settled**
- Harness counts are missing for 21 blocks (V7, V9, V10, D2a-e, K1-5, Z, M, O, J, G1a-c, the screening review).
- `G2_final.md` now holds the gate block's G2 (`43d1a6b`). Lane G's own G2 hand-back (`7d7c594`) is gone; LEAD NOTES 70 records it.
- Some check-only verdicts rest on P2.2's list of which lane checks each step, not on each block confirming it. Steps 75, 78, 91, 92 and 98 are checked by no lane.
- OF-260: I can't tell whether the lead dropped that W6 item on purpose.
- OF-242 is routed by `asy_uart_driver.py` (to U36).
- The squash draft's meaning changes come from commit bodies that say "meaning change". Bodies that state one in other words may have been missed.

**Checks:** citations, decision_vocabulary and legacy_paths under `nice -n 19`: 24 passed, rc 0. The one warning is the uninitialised datasheets submodule. Both RUNS.md lines are written.

nothing of mine is running