# CRr2b9: the bleed list's open entries, then the overlap siblings (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/crr2_hardware_rows.md` (its proof, checks, "Not yours"
and shell discipline apply), `crr2b8_bleed_scanner_overlap.md` (its rulings stand; its item 3 is yours) and the item
text it points to (`crr2b2_bench_log_check_rest.md` item 3), and the hand-backs `S/u35r/handbacks_redo/CRr2b7.md` and
`CRr2b8.md`. Worktree `S/wt-u35crr2b`, branch `audit/u35-crr2b` at d340b368 (clean). Logs in `S/u35/laneC/crr2b9/`;
CRr2b8's in `S/u35/laneC/crr2b8/` (bleed_scan.log, twin_cal.py, run.sh).

## The lead's review of CRr2b8 (binding)
- 171144df and d340b368 are kept as written. Its departure is accepted: a published candidate does not end the wait,
  because src publishes on every stable sandwich and runs until three agree or the window closes (src lines in its
  hand-back). The test's added bench time (about 2 min) goes to the owner in the report.
- CRr2b8 used `git stash push`/`pop`. CHECKLIST 1 and common_u35.md forbid `git stash`, and both are binding through
  redo_common.md. Nothing was left stashed, and the lead names the breach in the report. Never use it: to commit one
  item alone, stage paths with `git add <path>` and commit, or finish the item first.

## Items, in order (each committed green on its own, each through the twin where its body runs there, every
## FRAM-backed ring dumped after, both stages)
1. ResetVOC, the lead's call (accuracy before speed): add a settle so the reset's own outcome lands in its own window.
   Wait one SGP40 cycle, bounded and derived from src's cycle length with lines. Its bound is a tunable with its row.
   Bite: on synthetic data, a failed FRAM clear logged after the test (SGP40 E SGP_BACKUP_CLEAR) is blamed on the next
   window without the settle and lands in its own with it.
2. The heap ceiling test. Either show from src that no server-side entry can land after its last read, or add a drain
   wait like the lwip test's `_wait_for_slots_to_drain` (WEBSERVER's per-call timeout 5 s, asy_webserver_service.py
   :159-160 and :942-953). If a provoked entry can land, it joins the set with its lines.
3. The console test: prove that its adversarial sockets' server tasks finish inside its window, or add a bounded drain.
4. The outage and flap recoveries: prove that NTP's re-sync is quiet before each test ends, or add a bounded wait for
   ntp synced. An entry the re-sync can log goes in the test's set with its lines (the NTP mid-flight rule).
5. If within budget: crr2b8 item 3 (the overlap fix in its two sibling scripts and the HTTP bench counterpart of the
   ISL test).

## Notes
- File edits use the Edit or Write tool. A deletion is its own Bash call. No `git stash`.
- Every run goes through your own run wrapper (copy CRr2b8's), with RUNS.md lines naming `U35 lane CRr2b9`.
- Before each heavy twin run, check `uptime` and the process list: never more than 4 heavy processes on the host.
- Never touch `S/u35/laneC/crr2b4/plant_i1`.
- Commit subject `U35 lane CRr2b9: <summary>`, with the two trailers. Do not push.
- A refused command stops you. Count your tool calls; at 80, commit what is green and hand back at a seam.
- Hand-back:
  - commits;
  - per item, the evidence with log paths;
  - every set changed (before, after, lines);
  - added bench time per test;
  - the twin runs;
  - the review_rows.py counts;
  - the files whose twin record changes;
  - last line "nothing of mine is running".
