# CRr2b6: the bench log check's remaining items, the escalation assertion, the overlap fix's siblings (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/crr2_hardware_rows.md` (its proof, checks, "Not yours"
and shell discipline apply), `crr2b4_clears_bleed_sets.md` and `crr2b5_finish_clears.md` (the items still open there
are yours), and the hand-backs `S/u35r/handbacks_redo/CRr2b4.md` and `CRr2b5.md`. Worktree `S/wt-u35crr2b`, branch
`audit/u35-crr2b` at c12d1bd6 (clean). Logs in `S/u35/laneC/crr2b6/`.

## The lead's ruling on CRr2b5's escalation find (test code, no wear, the lead's call)
The lead confirmed it: `system_service_restarts_a_real_dead_task.py` builds its SystemService with
`LogConfig(None, ...)`, so its TASK_RAISED and TASK_BUDGET_REBOOT entries are RAM-only and die with the reset. Yet
`test_the_supervisor_escalation_reboot_is_attributed` (test_reset_reasons.py near :124) asserts
`any(... TASK_BUDGET_REBOOT ...)` over production's SYSTEM history after the reboot. That passes only on an older
entry, and fails on a cleared board. The assertion goes as written. The escalation reboot itself is already proved by
the reset-reason attribution and the forced bit just above it. Replace the assertion with evidence of the entry that
the run itself produces:
- in escalate mode, if the script's console output up to the reset can carry the logged entry, assert it there;
- otherwise name the tests/ test that pins TASK_BUDGET_REBOOT being logged on budget exhaustion, and say why the bench
  cannot see it.
Do not switch the script to the FRAM-backed log: that would write fabricated entries into production's FRAM history
(CLAUDE.md's device-script caveat). Bites: a board whose history holds a stale TASK_BUDGET_REBOOT passes the old test.
Show the new test cannot pass on that entry alone (on synthetic data).

## Items, in order (each committed green on its own)
1. The escalation ruling above.
2. CRr2b5's find 3: memory_stress's extended hammer, through the twin and src, as crr2b5's brief states it.
3. The serving_heap per-source set re-derived from `allocation_need_per_source.py` read in full. The UART hazard set:
   show SIZE_MISMATCH unreachable on the responder at every site, with lines, and narrow it; or keep it with the
   reason. test_an_incomplete_command: read `quiesce()` in full and confirm or correct CRr2b5's inference.
4. crr2b4's item 2 (the calibration bleed: a bounded wait for W ISL_CAL_TIMEOUT or a published candidate, then the bleed
   scan) and item 3 (redflags.py's segment-reading flags never read decorator text; self-test red first; re-render;
   `--check` rc 0).
5. If within budget: the overlap fix in `bus_concurrency_scd30_write_vs_siblings.py` and the HTTP bench counterpart of
   the ISL test (crr2b2_bench_log_check_rest.md item 3, unchanged: its NVM write sites unchanged and named,
   `_overlapped()` moved into `_shared/` if two scripts use it, bites on synthetic output and through TwinBoard).

## Notes
File edits with the Edit or Write tool. A deletion is its own Bash call. Every run goes through your own run wrapper in
your log dir, modelled on `S/u35/lead/run.sh` (namespace, nice 19, disk check, RUNS.md lines), with its RUNS.md lines
naming `U35 lane CRr2b6` (the lead's wrapper writes "U35 lead", which misnames a lane's runs). Never touch
`S/u35/laneC/crr2b4/plant_i1`. Commit subject `U35 lane CRr2b6: <summary>`, the two trailers; do not push. Past 80 tool
calls, commit what is green and hand back at a seam. Hand-back: commits; per item the evidence with log paths; every
set changed (before, after, lines); the bleed list; times; the review_rows.py counts; the files whose twin record
changes; last line "nothing of mine is running".
