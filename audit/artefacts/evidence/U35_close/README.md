# U35 preliminary evidence (2026-10-22)

A snapshot pushed before U35's close, at the owner's request, so the plan, the lead's records, the briefs and every
hand-back so far are not lost: masked as the close's own evidence is (the hotspot default, the bench LAN's third
octet). U35's close commit replaces this folder with its full evidence (lane and gate logs included).

## Second snapshot (2026-10-27): `redo/`

The container holding the work after `lead/` was reclaimed on 2026-10-26; the lost work was recovered and redone. At the
owner's request ("Whenever there is a close good opportunity, commit and push intermediate results. I don't want to
lose anything again.", 2026-10-27), `redo/` holds the redo's records: its plan (`REDO.md`), the briefs, every hand-back
(`handbacks_redo/`), the recovered owner rulings and hand-backs (`recovered/`), the lead's notes (`lane_plan.md.gz`,
LEAD NOTES through 290), the run register (`RUNS.md.gz`), the checklist, the owner-report and D3r/REC2 item lists, the
Q35 tables and the lead's run tools. Scanned before the push: no hotspot default, no LAN address, no credential
pattern. The tree around it is the integration head of the time, with the lanes merged so far; lane work not yet
merged is not in it, and the next snapshot carries it. Each later preliminary snapshot replaces `redo/` with the
records of its own time, scanned the same way.

## Thirteenth snapshot (2026-10-28): `scan/` and `redo/paused/`

On 2026-10-28 the owner paused all lanes ("Pause all tasks for now") and ordered a full scan of the audit against the
pre-audit state ("Now start a full scan what you find and report back to me once you finish."), then asked for it to
be pushed ("For now, document these findings in detail and push together with the current state."). `scan/` holds it:
`REPORT.md`, the consolidated report with the owner's mandate, what went wrong, the flash figures, the real gaps
confirmed in the pre-audit code, the code in doubt, the owner decisions it needs and the hardware-round list; the
seven parts it is built from (`A.md`-`D.md` firmware and buildgen, one row per change; `E.md` tests and tooling;
`F.md` docs and repo; `G.md` the audit's course); `L_flash.md`; and `repro/`, the reproduction scripts and their logs
(the pre-audit source they ran against came from `git archive 25caf528` and is not copied). `redo/paused/` holds the
three paused lanes' unmerged work as patches against their bases, committed and uncommitted together, so nothing is
lost; none of it is in the tree, merged or verified. Scanned before the push like `redo/`.

## Fourteenth snapshot (2026-10-28): `scan/DRIFT.md`

The owner asked how the drift evolved ("learn and understand how the drift evolved ... which effects it caused, and
how it could have been prevented.") and then for it to be pushed ("Push the analysis"). `scan/DRIFT.md` holds that
analysis: the course in numbers per unit, the mechanisms, why the first units stayed lean, the effects, where it
could have been caught, and the rules that would have prevented it. `scan/REPORT.md` carries one correction from it:
the flash share the audit used is about 61 % of the free space at the audit's own baseline, not "about half".

## Fifteenth snapshot (2026-10-28): `scan/PICTURE.md`

The owner asked for the project picture to be refined from the decisions taken together ("Every decision and request
I take is a puzzle piece of the big project picture and should fit. If it doesn't fit, we need to clarify."), answered
its three questions, and asked for it to be pushed ("document and push"). `scan/PICTURE.md` holds the picture: the
lines the owner's decisions draw, where the audit's results do not fit them, and the answers (the review page's "ok"
ticks stand; the Wi-Fi behaviour stands as decided; the FRAM per-owner seed stays). `scan/REPORT.md` records the same
answers in its sections 1, 3 and 6, with two website items corrected as the owner's own requests.

## Sixteenth snapshot (2026-10-28): `scan/scan2/`

The owner gave the cleanup's ground rules ("a verified finding or a taken decision stand for their own and are worth
keeping at least documented. ... Rare but real conditions staying in scope still shall be addressed - no regressions,
but more efficiency."; `scan/PICTURE.md` section 8), asked for a second pass over everything changed since the audit
started ("there might be more hidden or overlaid / higher dimensional occurrences you did not see yet"), and asked for
it to be pushed ("First, commit and push."). `scan/scan2/` holds it: `SCAN2.md`, the consolidated report (the
patterns, the finds, the removal closure, the keep list, the corrections and the resolved disagreements); its five
parts (`G1.md` core, storage, drivers and LED; `G2.md` network and UART; `G3.md` buildgen, generated code and the
website; `G4.md` the cross-module families and the closure; `G4b.md` the crosswalk of the four); the closure data
(`G4_closure.tsv`, `G4b_closure.tsv`); and the function census (`funcs.tsv`, `families.tsv`, made by
`tools/census.py` from `git archive` of the two commits, which are not copied). Nothing ran in the pass.
`scan/PICTURE.md` gains section 8 and withdraws M13; `scan/REPORT.md` records the owner's answers and the corrections.

## Seventeenth snapshot (2026-10-28): `scan/decrev/`

The owner asked for the decisions the agents took on the owner's behalf to be re-checked against the refined picture
("revisit the decisions you took on my behalf, and check if you would answer differently with the new knowledge. Only
check, and see them in a global context, also not contradicting each other, and document your findings.") and then
for the result to be pushed ("push the findings"). `scan/decrev/` holds it: `DECREV.md`, the consolidated report (the
verdict per decision, the different answers by kind, where what was built differs from the owner's words, agent text
credited to the owner, the different answers as one set, the corrections and the checks still owed); its eight parts
(`DR1.md` the review page; `DR2.md`-`DR6.md` the register's owner-review rows by unit range, `DR6.md` also the parked
changes and the redo's lead decisions; `DR7.md` SPECIFICATION.md Part N; `DR8.md` agent-tagged text elsewhere); the
crosswalk `DRX.md`; and `inputs/owner_words_lane_plan.md`, the owner's words that had been recorded only in the lead's
lane plan (the other inputs are copies of repo files and are not copied). `redo/recovered/` gains those words and the
morning of 2026-10-28; `redo/CHECKLIST.md` gains the rule that every owner word is recorded as it is given. Nothing
ran in the check.

## Eighteenth snapshot (2026-10-28): `redo/plan/`

The owner asked for a plan to repair the existing state, for the items that remain open from U35 to the end revised
with the new knowledge, and for how to implement it with a defined end and no cut in quality; then took its seven
decisions one by one and asked for a push ("do a push so we keep everything in any case"). `redo/plan/PLAN.md` holds
it: the target and the method (work from the current files, every difference from the pre-audit state mapped to a
reason, every change test first), the phases from the settling step to the final merge with their done-criteria, the
retired plans, what remains by phase, the way of working with its budgets, and the seven decisions with the owner's
words. `redo/int_history.txt.gz` lists the integration history's commits (messages and changed files, no source),
which stays local because its messages carry lane names. `redo/recovered/` and the lane plan gain the owner's words
of the decisions. Nothing ran; nothing in the plan has started.

## Nineteenth snapshot (2026-10-28): `redo/plancheck/`

The owner, worried that factual questions kept refining the plan's recommendations ("This is a clear sign that you
papered over important details"), asked for the plan to be revised so it holds no such glitches, with an independent
falsification as the final verification ("Revise our current plans, so they do not contain such glitches anymore. The
claim falsification check agent scan seems reasonable, too. Add this as a final verification and adapt the run counts
accordingly."), then for a push. `redo/plan/PLAN.md` is the checked plan. `redo/plancheck/` holds the evidence:
`R1.md` and `R0R2_rest.md` (the lead's check of every row: where it is, what governs it, who uses it, what the platform
does, how big it is), `CHANGES.md` (every change and its kind), the four falsification hand-backs under `falsify/`
(297 claims tried by agents that had the repository but not the lead's evidence: 5 refuted, 78 partly), the edit
scripts and the plan's backups before each step. Nothing ran on the product; nothing in the plan has started.

## Twentieth snapshot (2026-10-28): `redo/hw_handover/`

The owner asked for a hardware handover that uses the bench's free days with few tokens ("We have several days (aka 12h
stretches) we can use with the bench, so actually think of maximising the outcome of the few percent"; "The sessions
shall push regularly and dump all details into a single hand back file ... interruptible anytime without losses (max
10 minutes wait time)"). `redo/hw_handover/HANDOVER.md` is the run sheet, and `run_all.sh` the one runner. Day 1 saves
the FRAM on the current firmware, flashes a bare pinned MicroPython image, then runs short timing scripts, the chip
probes and hours of long runs that count rare events. Later days add long runs. `mp/` holds the board-side scripts,
`aggregate.py` and `handback.py` the host side. Every step lasts at most about 10 minutes, and the runner pushes
`HANDBACK.md` to its own bench branch. Nothing has run.
