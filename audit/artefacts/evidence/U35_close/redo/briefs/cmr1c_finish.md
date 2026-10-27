# CMr1c: finish CMr1b's uncommitted device-pick work (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/cmr1b_device_picks_rest.md` (your task; its parent
`cmr1_device_picks.md` and its owner rule apply) and CMr1b's hand-back `S/u35r/handbacks_redo/CMr1b.md`. Worktree
`S/wt-u35cmr1b`, branch `audit/u35-cmr1b` at 52f691dc: CMr1b's work is there UNCOMMITTED. Logs in
`S/u35/laneC/cmr1c/`; CMr1b's in `S/u35/laneC/cmr1b/` (times.txt, its batch logs, its scratch trees under trees/).

## Why CMr1b stopped (binding for you)
A safety classifier refused its command `timeout 100 tail --pid=... -f /dev/null; awk ... times.txt | column -t`. It was
correctly not retried, and it is not yours to run in any form: never a `tail --pid` wait, never a chained wait plus
read. Read a log with one plain read (cat, grep, awk on the file alone, or the Read tool), one command at a time. Its
three batches had ended before you start (the lead waited for them). If any command is refused, stop at once and hand
back; never retry it in any form.

## What to do
1. Review CMr1b's diff yourself (`git diff`); keep what is right, fix what is not, say which.
2. Read its batches' results (times.txt and the logs): the three red variants (each defect shown first as its failure),
   bus_hazard at both stages, fram/clock_jump/ntp/hot_replug base and head at both stages, the integration and NeoPixel
   files base and head back to back. Root-cause any red; never call it a flake.
   The lead's read of times.txt after the batches ended: `w_w2_ntp` failed 2 of 16 at both stages (base52 16/16), so
   item 1's ntp edit is red until you root-cause it; and w2's widened files about double their time (clock_jump 25 ->
   49 s, ntp 34 -> 54 s, hot_replug 8 -> 17 s). The owner's rule: "Test duration going up like this is anyhow
   something to fix - not cutting back strictness, but making it more efficient". Find where the added time goes (a
   boot per device, a fixed wait) and make it efficient without dropping a wiring; state each file's time before and
   after.
3. The final bus_hazard file at both stages (its bh tree held an older SCD30 call form), then the remaining sites
   CMr1b lists (the scd30 and sgp40 helpers, launch, wifi_modes, the tests_scripts `DEVICE_NAMES[0]` sites), each
   classed by measurement and widened or kept with its reason; fram_less_boot and `_lag_run` deduplicated the same way
   if their read keys allow it.
4. Item 4's bites, item 5's matrices.md rows, item 6's E.2.1 sentence for D3r (CMr1b's text, re-checked).
5. Commit item 3 first (subject `U35 lane CMr1b: ...` for CMr1b's work is fine), then items 1-2, then your own (`U35
   lane CMr1c: <summary>`), each green on its own; times against CHECKLIST 14 stated.
6. Delete CMr1b's scratch trees (`S/u35/laneC/cmr1b/trees`, about 1.1 GB) with one literal-path rm once nothing reads
   them, and say so.

## Checks
As the parent brief; lint with `S/u35/lead/lint_direct.sh`. Shell rules: scripts as files you wrote, never `bash -c`
holding rm, never nohup chains; a timed-out run's children killed. Past 80 tool calls, commit what is green and hand
back at a seam. Last line "nothing of mine is running".
