# CRr2b4: the bench log check across a test's own clears; the calibration bleed; the scanner; the sets re-checked (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/crr2_hardware_rows.md` (its proof, checks, "Not yours"
and shell discipline apply), `crr2b3_expected_entries.md` (the task; items 2-4 are yours) and the hand-backs
`S/u35r/handbacks_redo/CRr2b2.md` and `CRr2b3.md`. Worktree `S/wt-u35crr2b`, branch `audit/u35-crr2b` at 575f8c22
(clean). Logs in `S/u35/laneC/crr2b4/`; CRr2b3's (sets_map.txt, clear_tests.out, mark_sets.py) in
`S/u35/laneC/crr2b3/`: read before reusing.

## The lead's rulings on CRr2b3's open points
- WLAN_CONNECT_FAILED, WLAN_STATUS_UNKNOWN and WLAN_NO_VERDICT stay out of the outage group: the outage tests already
  fail on them, so the set must not admit them. Confirmed.
- An NTP attempt caught mid-flight by an outage must go IN the outage tests' sets. src/asy_ntp_client.py
  `_run_ntp_sync_attempt()` (near :426-455) checks the network only at the start, under wifi_mode_lock, so an attempt
  under way when the outage begins can reach the DNS, send and no-reply errors. That is a consequence of the provoked
  fault that depends on timing, and the rule in crr2b3's item 1 applies: list every entry src can produce there, each
  with its line. Leaving them out would turn a timing coincidence into a bench failure.
- test_an_incomplete_command's set (SYSTEM W CONFIG_LOST only): confirm it by reading the device script and the cut
  write in full, or widen it.
- The three less certain sets (the UART hazard run, serving_heap per-source, escalation and stack exhaustion): re-derive
  each by reading its device script in full and every src site it reaches, then narrow or widen it with lines.

## Items, in order (each red first where it is a mechanism, committed green on its own)
1. Item 2 of crr2b3, with its sets in the same commit: never the mechanism alone. Implement CRr2b3's planned design:
   `reset_all_error_logs()` keeps the parsed pre-clear read it already takes, and the fixture checks each segment.
   Every unmarked bench test that provokes and then clears (CRr2b3's clear_tests.out: 56 clear, 45 unmarked, about
   22 provoke) gets provokes_log with its src-derived set, or a stated reason it leaves nothing. Tests: an entry
   logged then cleared inside an unmarked test fails it (red on 575f8c22); a clear with nothing before it passes; a
   marked test's entry before its clear inside the set passes.
2. Item 3 of crr2b3, the calibration bleed. test_isl29125_calibrate_command_push_over_real_rest waits until its run has
   ended, observed through what the board already shows: W ISL_CAL_TIMEOUT in ISL29125's errcount history, or a
   published candidate in the measurements. The wait is bounded by `_CAL_WINDOW_MS` plus one read cycle plus a margin,
   tagged per Part N. The test asserts that one of the two ends happened, and carries provokes_log with the W entry.
   State its added time. Then the scan: every bench test with device activity still running at its end that can log
   later, each with src lines, settled or shown harmless. No src change: a status field would be a firmware feature,
   not ours.
3. Item 4 of crr2b3: redflags.py's segment-reading flags read the function body and its helpers, never its decorators;
   a self-test red first; re-render; the rows that reappear get verdicts (fixed, covered by the log check with its set,
   named); `--check` rc 0.

## Notes
The flash tests' markers and the flash fixture are CRr2c's; the overlap fix in the SCD30 sibling script and the HTTP
bench counterpart comes after you. Commit subject `U35 lane CRr2b4: <summary>`, the two trailers; do not push. Past 80
tool calls, commit what is green and hand back at a seam (item 1 is one commit or none). Hand-back: commits; per item
the evidence with log paths; every set changed (before, after, lines); the bleed list; times; the review_rows.py
counts; the files whose twin record changes; last line "nothing of mine is running".
