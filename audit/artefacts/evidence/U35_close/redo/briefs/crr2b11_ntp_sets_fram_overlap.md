# CRr2b11: the NTP sets, the twin drain's FRAM entries, the overlap (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then `S/u35r/briefs/crr2b10_console_outage_overlap.md` (its rules and item 3), then CRr2b10's hand-back
`S/u35r/handbacks_redo/CRr2b10.md` (the state). Worktree `S/wt-u35crr2b`, branch `audit/u35-crr2b` at 93c2dcbb (clean).
Logs in `S/u35/laneC/crr2b11/`; CRr2b10's scripts are in `S/u35/laneC/crr2b10/`.

## The lead's review of CRr2b10 (binding)
- 950c3a83 and fc6f42a6 are kept. The lead added 93c2dcbb: E NTP_RETRIES in both sets of the outage and flap tests,
  on CRr2b10's bite case 8 and its reading of the false-positive path. Provocation sets are allow-lists: only the
  lead edits them. You prove; the lead edits.

## Items, in order
1. Re-run CRr2b10's bites_ntp.py on 93c2dcbb: case 8's own window now passes, and nothing else moved. Then, for every
   other provokes_log set that names an NTP entry (test_bus_concurrency_under_api_load.py's two, test_network_resilience.py's
   blocked-port and spoof tests, test_wifi_networking.py's blocked-port test), find every NTP entry the window can
   reach, NTP_RETRIES included (window length against the chain bound, and the false-positive path). For each entry
   missing from a set: its source line, the path, and a bite on a fake board showing the window failing. Do not edit
   the sets; hand the proposals back.
2. Root-cause the twin drain's E FRAM_STATUS_BYTE and W FRAM_BLOCK_INVALID at 32768. "Most likely" is not a cause.
   - Run the drain on a fresh state dir at both stages: the entries are absent, or they are not, with the rings dumped.
   - Then boot over a state dir left by a run killed mid-flight, the way CRr2b10's first run died, and show the
     entries appear.
   - Name the mechanism from the code: which write was torn, and which check logs each code.
   - Then decide: is it the firmware's correct report of a torn write that a crash on silicon would also leave, or
     is it a defect (an entry with no torn write, or a torn write the design says cannot happen)? A defect follows
     redo_common's defect rules.
3. CRr2b10's item 3: the overlap fix in its two sibling scripts, and the HTTP bench counterpart of the ISL test
   (crr2b2 item 3), under that brief's rules.

## Hand-back (the file, per redo_common)
Commits; the bites; the set proposals with lines; the FRAM root cause with evidence; item 3's result; any question
for the owner in prose with a recommendation; last line "nothing of mine is running".
