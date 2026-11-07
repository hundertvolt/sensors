# CRr2b8: the calibration bleed, the scanner's decorator text, the overlap siblings (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/crr2_hardware_rows.md` (its proof, checks, "Not yours"
and shell discipline apply), `crr2b7_bench_last.md` (items 3 and 4 are yours) and the item texts it points to
(`crr2b4_clears_bleed_sets.md` items 2 and 3, `crr2b2_bench_log_check_rest.md` item 3), and the hand-backs
`S/u35r/handbacks_redo/CRr2b6.md` and `CRr2b7.md`. Worktree `S/wt-u35crr2b`, branch `audit/u35-crr2b` at 7e7451f5
(clean). Logs in `S/u35/laneC/crr2b8/`; CRr2b7's in `S/u35/laneC/crr2b7/` (sets_map.txt, run.sh, its ring-dump copy).

## The lead's review of CRr2b7 (binding)
- 1a2226c6 and 7e7451f5 are kept as written. The wide side stays: CFG_GET_RAISED for seven modules and
  CFG_CALLBACK_RAISED for three. Each is reachable under the sieve, and each carries its lines. A set names every
  entry its provocation can reach, with lines, as the NTP mid-flight group does. An entry the twin did not show is
  still in the set if src can produce it there.
- The lesson of 4a2e3ddf binds you too: a set derived by reading alone missed three entries the twin showed. Any set
  you change, or any check you add, is run through the twin wherever its script runs there (TwinBoard, or a dev twin
  booted as CRr2b6's twin_hammer.py did), at both stages, with every FRAM-backed ring dumped after it. Name the runs.

## Items, in order (each committed green on its own)
1. The calibration bleed: a bounded wait for W ISL_CAL_TIMEOUT (`_CAL_WINDOW_MS`, 120 s) or a published candidate,
   then the bleed scan, as crr2b4 item 2 states. Its bound is a tunable with its tag and Part N row. Put it through the
   twin, plus a synthetic bite: a run whose calibration logs into the next window fails.
2. redflags.py's segment-reading flags read decorator text. Self-test red first, then re-render, then `--check` rc 0.
3. If within budget: the overlap fix in its two sibling scripts and the HTTP bench counterpart of the ISL test, as
   crr2b2 item 3 states.

## Notes
- File edits use the Edit or Write tool, never a heredoc or interpreter edit, own log files included.
- A deletion is its own Bash call.
- Every run goes through your own run wrapper (copy CRr2b7's), with RUNS.md lines naming `U35 lane CRr2b8`.
- Two other lanes take timing pairs. Before each heavy twin run, check `uptime` and the process list; never start one
  that would put more than 4 heavy processes on the host.
- Never touch `S/u35/laneC/crr2b4/plant_i1`.
- Commit subject `U35 lane CRr2b8: <summary>`, with the two trailers. Do not push.
- A refused command stops you.
- Count your tool calls; at 80, commit what is green and hand back at a seam.
- Hand-back:
  - commits;
  - per item, the evidence with log paths;
  - every set changed (before, after, lines);
  - the bleed list;
  - the twin runs;
  - the review_rows.py counts;
  - the files whose twin record changes;
  - last line "nothing of mine is running".
