# U35 recovery verification V5: every open finding and carried item, and which must land in U35 (lead, 2026-10-26)

Read `S/u35r/briefs/verify.md` first (why, sources, rules); this brief replaces only "Your job".

The owner (2026-10-26): "Firmware really complete, don't push fixes to future units". Until now a finding in a product
file was routed to the next unit holding the file (U36, U37), and a U36 row carried its route only. That routing is
over for firmware: every open finding that a change to the firmware can settle lands in U35. A finding that only
silicon evidence can settle stays with its hardware round, named as such.

## Your job
1. `audit/sweeps/open_findings.md` at 656fc82 (`S/wt-base`): every row whose state is not closed. For each: its site
   re-checked in the tree (does the defect still exist at 656fc82? cite the line), its class, and one verdict:
   `FIRMWARE` (a change in `src/`, buildgen's templates, the generated modules, `html/`, `js/` or anything that ships in
   the image settles it), `TEST/TOOL` (tests, scripts, digital_twin, CI), `DOC`, `HW` (only silicon can settle it: which
   measurement), `CLOSED-IN-TREE` (already fixed at 656fc82: the evidence), or `OWNER` (it needs an owner decision:
   which, and whether it was already asked or answered, with the quote).
2. The rows REC1 added or changed (`S/u35/handbacks/REC1_final.md`; its commit befa1aa is lost), the items
   `S/u35/close_items.md` and `S/u35/lead_todo.md` carry, the carried items in LEAD NOTES 104-118 (REC2's list in
   LEAD NOTES 112, the D3 lines in 113 and 116, the "W6 lead items" around lane_plan.md:850-870), and the findings the
   lost blocks raised (`S/u35r/recovered/lead_notes_119_148.md` and `S/u35r/recovered/handbacks/`): each one, with the
   same verdicts, and whether open_findings.md at 656fc82 has a row for it (`NO ROW` if not).
3. For every `FIRMWARE` and `TEST/TOOL` item: the file it changes and whether a recovered brief already plans it
   (`S/u35r/recovered/briefs/blocks_f.md` F1-F3, the others), or `NO PLAN`.
Write the table to `S/u35r/verify/V5.md`, then hand back at most 60 lines: counts per verdict; every FIRMWARE item in
one line (id, site, planned or NO PLAN); every OWNER item with its question; every NO ROW item; the contradictions;
last line "nothing of mine is running".
