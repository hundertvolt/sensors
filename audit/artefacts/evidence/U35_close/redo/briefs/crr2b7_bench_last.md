# CRr2b7: the bench log check's last items (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/crr2_hardware_rows.md` (its proof, checks, "Not yours"
and shell discipline apply), `crr2b6_bench_rest.md` (items 3-5 are yours; its rulings stand) and the briefs it names
for those items (`crr2b4_clears_bleed_sets.md` items 2 and 3, `crr2b2_bench_log_check_rest.md` item 3), and the
hand-backs `S/u35r/handbacks_redo/CRr2b5.md` and `CRr2b6.md`. Worktree `S/wt-u35crr2b`, branch `audit/u35-crr2b` at
4a2e3ddf (clean). Logs in `S/u35/laneC/crr2b7/`; CRr2b6's in `S/u35/laneC/crr2b6/` (sets_map.txt, run.sh).

## The lead's review of CRr2b6 (binding)
- 68ce7043, e8452ccc and 4a2e3ddf are kept as written. The escalation test is unmarked, like its sibling reset tests
  (bootloader, harness hard reset, starved watchdog). A production boot after a reset reports its reason through
  /status and logs nothing FRAM-backed, and the script's own log is RAM-only.
- serving_heap's open entry is resolved, not left open. Decide with lines whether WEBSERVER E LOG_RAM_ONLY
  (asy_print_log.py:229-239) can land while a source runs under a sieve: read asy_fram_manager.py :497-514 and the
  chunk write path in full. If it can, it is a provoked outcome and joins the set with its lines. If it cannot, say
  why. An entry the test provokes but leaves out of the set fails silicon for a test-design reason.

## Items, in order (each committed green on its own)
1. serving_heap's LOG_RAM_ONLY decision (above).
2. crr2b6 item 3's rest: the UART hazard set (show SIZE_MISMATCH unreachable on the responder at every site with
   lines, and narrow it, or keep it with the reason), and `quiesce()` read in full for test_an_incomplete_command
   (confirm or correct CRr2b5's inference).
3. crr2b6 item 4: the calibration bleed and redflags.py's decorator text.
4. If within budget: crr2b6 item 5 (the overlap fix's two siblings and the HTTP bench counterpart of the ISL test).

## Notes
File edits with the Edit or Write tool, never a heredoc or interpreter edit, own log files included. A deletion is its
own Bash call. Every run goes through your own run wrapper in your log dir (copy CRr2b6's), with its RUNS.md lines
naming `U35 lane CRr2b7`. The lead's `mc_cov` (a full test.sh --coverage on int) runs from 05:46: no timing
measurement while it runs (correctness runs are fine). Never touch `S/u35/laneC/crr2b4/plant_i1`. Commit subject
`U35 lane CRr2b7: <summary>`, the two trailers; do not push. A refused command stops you. Count your tool calls, and
at 80 commit what is green and hand back at a seam. Hand-back: commits; per item the evidence with log paths; every
set changed (before, after, lines); the bleed list; times; the review_rows.py counts; the files whose twin record
changes; last line "nothing of mine is running".
