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

## Twenty-first snapshot (2026-11-02): `redo/bench/`

The bench campaign ran on 2026-10-28/29 (branch `claude/u35-bench-campaign`). The owner asked for it to be read in
("Read this in and understand it."), folded into the plan ("Fold into the plan now.") and its open questions researched
("Try to answer the other deep detail questions by proper research"). `redo/bench/READING_20261029.md` is the reading,
`redo/bench/RESEARCH_20261102.md` the research; `redo/plan/PLAN.md` carries both (its previous state is
`PLAN_before_bench.md`), and `redo/plancheck/CHANGES.md` lists every change with the owner's words behind it.

## Twenty-second snapshot (2026-11-02): the plan rewritten and checked

The owner asked for the finishing plan to return to the spirit of the audit's first units ("rewrite the plan, and
target that we are done with 50...60% of weekly budget") and then for its final check ("Now ensure the plan is
complete, consistent, according to our discussions, coherent and correct."). `redo/plan/PLAN.md` is the rewritten
plan; its previous state is `PLAN_before_rewrite.md`. `redo/plancheck/final/` holds the version checked
(`PLAN_as_checked.md`) and the two independent checks (`C1.md`, completeness; `C2.md`, falsification);
`redo/plancheck/CHANGES.md` lists every change with the owner's words behind it.

## Twenty-third snapshot (2026-11-02): R0, settling

The owner's go-ahead for R0 ("Go ahead with R0, and resume watching CI"). `redo/r0/BASELINE.md` is the "before" column
of every later report; `redo/r0/R0_CHECKS.md` holds the three checks that decide items of the firmware batches;
`redo/knowledge/` starts the knowledge list, `redo/findings/` the findings list (empty); `redo/tools/review_hunks.py`
is the throwaway review aid of the plan's section 2, step 4. The tree drops the twin record's committed copy and its
staleness test, and this snapshot runs the full CI.

## Twenty-fourth snapshot (2026-11-02): R0's CI fix

The owner's go-ahead ("And fix CI right now."). The first full CI run, on the twenty-third snapshot, was green on 45 of
46 jobs; the coverage job failed one test whose exact-zero byte check cannot hold on the settrace binary. The test now
checks bytes on the settrace-free binary only. `redo/r0/R0_CHECKS.md`'s last section has the root cause and the fix,
`redo/r0/BASELINE.md` the CI time per job (`redo/r0/ci/jobs.tsv`). The owner also confirmed the exception-handler
guard ("That's okay."). This snapshot runs the full CI.

## Twenty-fifth snapshot (2026-11-03): R1's first unit, logging and the catalog

The plan's first R1 unit, on the owner's standing go-ahead (2026-11-02: "keep rolling with our agreed scheme on
parallelism"). The logger records a C-stack overflow at its own entry, so 118 of 123 per-handler calls went; DebugLevel
0 prints nothing, the four logger-less layers printing through the logger their builder hands them (owner, 2026-11-02:
"There must be a mode which is really silent on the console, ever. That's level 0."); the RAM-only log entry, the
pre-setup merge, the level setter's refusal and six retired catalog rows went. `redo/r1/` holds the unit's action list,
brief and hand-back, the falsification's brief and result, and the lead's check of each refutation
(`redo/r1/B1/FALSIFY_VERIFIED.md`): the guard test was narrowed, the memory gate's tests boot at warning level, and the
construction window on the board went to the owner. `redo/r1/B2/` holds the next unit's action list and brief.

## Twenty-sixth snapshot (2026-11-03): R1's second unit, reset codes and `/status`

The plan's second R1 unit, on the same standing go-ahead. Code 4 and the reset-register reads went; the bootloader
records code 9; the command gate refuses once a reset is due; the escalation writes its entry, then resets. Logging an
allocation failure is a plain `err()` (owner, 2026-11-03: "Yes keep it simple"); what a module logs while it is built
stays unprinted and unkept (owner: "Leave that."); the newest-entry slot rule stays (owner: "Keep as is.").
`redo/r1/B2/` holds the action list, brief, hand-back, review, the falsification's brief and result, the lead's check of
each refutation (`FALSIFY_VERIFIED.md`) and the gate (`GATE.md`). `redo/r1/CARRY_LATER.md` lists what later units take
over; `redo/r1/B4/` and `redo/r1/B5/` hold the next two units' action lists and briefs (buses and sensors; network, with
the owner's fixed 60 s NTP retry while unsynced).

## Twenty-seventh snapshot (2026-11-03): R1's third and fourth units, buses, sensors and network

The plan's B4 (buses and sensors) and B5 (network) units, run side by side on the same standing go-ahead, merged
together. Both go back to their pre-audit forms where nothing proved the audit's form good; NTP retries every 60 s while
unsynced (owner, 2026-11-03: "Then let's actually take 1 minute"). Each unit's falsification found misses (a tick during
an NTP attempt starting the next one, the JSON pieces' memory check weakened, hardware-tier and harness checks left
behind, the VOC uptime cap off the C reference); a fix round closed them before the merge. `redo/r1/B4/` and
`redo/r1/B5/` hold each unit's action list, brief, hand-back with its fix round, review, falsification brief and result,
the lead's check of each refutation (`FALSIFY_VERIFIED.md`) and the fix brief; `redo/r1/B45/` the merged head's gate and
sizes; `redo/r1/MERGE_B4B5_NOTES.md` the one merge conflict. The Stull (2011) paper moved to the private datasheets
repository (owner, 2026-11-03). `redo/r1/B3/` and `redo/r1/B6/` hold the next two units' action lists with their drafts
and briefs (storage; UART), started after this gate.

## Twenty-eighth snapshot (2026-11-03): the twin CI suite's ResetErrors check

CI on the twenty-seventh snapshot failed one check in nine of the ten non-dev twin suite jobs: Run 5c wanted every
recorded error source empty right after a ResetErrors, but an SGP40 on FRAM logs its blank-chunk warning (W65) at its
first restore after the reboot, and on those devices that restore can land after the reset. The check now admits exactly
that one warning for an SGP40 and nothing else; test-only, no firmware byte changes. `redo/r1/B45/GATE.md` records the
failure and the fix.

## Twenty-ninth snapshot (2026-11-03): R1's fifth and sixth units, storage and UART

The plan's B3 (storage) and B6 (UART) units, run side by side on the same standing go-ahead, merged together. Both go
back to their pre-audit forms where nothing proved the audit's form good: no lost-chip detection or bus-down status for
the FRAM, no sender cap, write deadline or zero-length guards on the UART. The FRAM's SPI clock is 8 MHz (owner,
2026-11-02: "Then let's take the 8mhz as initially suggested"); the UART receive ring stops its two DMA channels without
the hang the bench found (2026-10-29); the overrun warning W57 goes (one entry per fault); the CRC's pass-mode bounds
stay, since a delimited UART read hands it a decoded size of 0. Each falsification found misses (doc sentences on the
overrun bit and the sender cap, three texts still timed for the 1 MHz clock, one of them a flash-tier test's mid-erase
reset points, and a twin CI check counting console lines its console-off run never prints); the lead fixed them before
the merge, and the merged gate caught that check's own test still unstubbed for the status read the fix added (fixed on
the merged head). `redo/r1/B3/` and `redo/r1/B6/` hold each unit's action list, brief, hand-back, review, falsification
brief and result and the lead's check of each refutation (`FALSIFY_VERIFIED.md`); `redo/r1/B36/` the merged head's gate
and sizes; `redo/r1/MERGE_B3B6_NOTES.md` the trial merge. Gates now run one at a time on this 4-core host: the two
units' gates side by side failed wall-clock bounds that all held alone.
