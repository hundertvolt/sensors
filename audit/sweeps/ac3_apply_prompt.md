# A-C3 apply brief: land the end-state findings in the M files and the register

A-C2 (`audit/order/WORK_ORDER.md`, `work_order.json`) and A-C3 (`audit/consolidation/AC3_O.md`, `AC3_R.md`, `AC3_S.md`)
are done. Each finding names the M-ID (or register block) to amend and gives the exact amendment text. This pass applies
them. Read `audit/sweeps/ac_prompt.md` for the change format and `audit/actions/AC_NOTES.md` (1-50). The most recent owner
decision in `PROJECT_AUDIT_PLAN.md` 3.2 wins. Accuracy before speed. Never read `arduino/`, never edit `ext/` or any file
outside your own targets, never run anything against real hardware, no git commits (the lead commits).

## Method

You own a set of target files (given in your task). Read all three AC3 files in full and collect every amendment, new
change, From completion, Blast-pointer fix and ledger disposition that lands in one of your files. For each:

1. Read the current text of the change first. A-C2 has since edited Unit and Depends slots and added an `## A-C2 order
   notes` table to most M files; never undo an A-C2 edit. If an amendment's anchor text no longer matches, apply its
   intent with the smallest edit and say so in your ledger row.
2. Apply the amendment text as given, and add a row to the M file's ledger naming the finding ID (e.g. "AC3 O-01").
3. New changes go after the file's highest number, in full ac_prompt format, with the ID the AC3 report proposes and the
   Unit WORK_ORDER.md places them in. Exception: AC3_R R-04's baseline-run change, written `M.PROC.R04` in WORK_ORDER.md,
   is `M.PROC.048`. AC3_R R-04's doc change and AC3_S S-13 are one change, `M.DOCS.109`.
4. Unit and Depends slots: change them only where a finding says so (e.g. AC3_R R-03's "— (no step)" for M.SRC_CORE.108),
   and only consistently with WORK_ORDER.md.
5. A finding you judge wrong against the current text: do not apply it; record why. A finding that needs an edit in a file
   you do not own: record a hand-off.
6. Permanent text never cites a temporary audit ID (G9/R12); the ledger rows and From slots are audit text and may.

## Output

`audit/consolidation/AC3_APPLIED_<n>.md` (your number): one row per finding part you handled (finding ID, M-ID or
register block, applied / adapted / new / declined, a short reason for the last three), then hand-offs and counts. Hand
back a short summary: counts, hand-offs, anything declined.
