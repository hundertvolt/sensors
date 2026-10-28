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
