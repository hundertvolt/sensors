# B8 owner questions, queued (lead, 2026-11-03)

From the B8 draft (`ACTION_LIST_DRAFT.md`, rows named). Each is checked by the lead against the tree and the rulings
file before it is asked; asked one at a time, in prose, after the B7 `State` question is answered.

1. O1 (rows 6-7): the boot entry prints the loop's ending exception at every DebugLevel (`codegen.py:871`), against
   the level-0 rule. Draft: drop the print, reset reason 22 stays the trace. Also the no-autostart start line (OR86).
2. O2a (row 12): the page build-date stamp (656fc82f). Draft: remove.
3. O2b (row 13): the "returned no JSON object" banner (9bf22747). Draft: restore the pre-audit check.
4. O2c (row 14): a saturated error counter shown as "65535+" (9bf22747). Draft: keep.
5. O2d (row 15): double stripes for Invalid/Failed Apply results (9bf22747). Draft: keep.

Not asked (records found by the draft, to verify): `BuildDate` (OR43.a (2), owner "yes" 2026-09-26); `ResetBits` and
`ConfigUnpersisted` rows (B2, owner "(a), remove both", 2026-11-02 21:11).

B7's item 7 (owner, 2026-11-03 20:35 UTC) takes the whole notification status group, the TS row's label "Last Cycle
Time" and its format included: the draft's row 14 note on that row falls to B7.
O1 answered (owner, 2026-11-03 20:40 UTC): "drop the traceback print and keep the start line, as you
recommended": rows 6 and 7 as the draft recommends.
O2a answered (owner, 2026-11-03 20:43 UTC): "Remove it": row 12 removes the stamp.
O2b answered (owner, 2026-11-03 20:45 UTC): "Yes, restore": row 13 restores the pre-audit check.
O2c answered (owner, 2026-11-03 20:47 UTC): "Yes, that was a good addition, keep it": row 14 keeps it.
O2d answered (owner, 2026-11-03 20:53 UTC): "No, don't keep it, ... color alone is fine.": row 15
restores the solid stripes (`25caf528:html/style.css:325-346`). All six questions answered.
