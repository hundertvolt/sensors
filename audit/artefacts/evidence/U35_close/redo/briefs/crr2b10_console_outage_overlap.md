# CRr2b10: the console drain, the outage and flap windows, the overlap siblings (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/crr2_hardware_rows.md` (its proof, checks, "Not yours"
and shell discipline apply), `crr2b9_bleed_rest_overlap.md` (its rulings stand; items 3-5 are yours) and the item
text its item 5 points to, and the hand-backs `S/u35r/handbacks_redo/CRr2b8.md` and `CRr2b9.md` (its designs for
items 3 and 4 are your starting point, with lines). Worktree `S/wt-u35crr2b`, branch `audit/u35-crr2b` at d8dfde93
(clean). Logs in `S/u35/laneC/crr2b10/`; CRr2b9's in `S/u35/laneC/crr2b9/`.

## The lead's review of CRr2b9 (binding)
- d8dfde93 is kept as written (the ResetVOC settle: one SGP40 cycle read from src by ast plus a 2 s margin; bites 8/8;
  the dev twin at both stages). Item 2 is settled by reading (the script's own server, then a soft and a hard reset
  before the after-read): accepted, no change.
- CRr2b9 started a run as `nohup bash run.sh … &`, against the shell rules (no nohup chains). It ran to rc 0, and the
  breach is named in the report. Run everything through your wrapper, as a Bash background call with its own
  `timeout` if it is long.
- Its find in item 4 is a gap in CRr2b5's sets. CRr2b4's research put the NTP mid-flight group (NTP_DNS_NOT_SENT,
  NTP_DNS, NTP_NOT_SENT, NTP_NO_REPLY) on every window where `bench.ap_down()` lands on a running STA link. CRr2b5
  applied it only to the bus flapping test. network_resilience's outage test (:155-159) and flap test (:174-178) still
  name only the WLAN entries. The group joins both sets, with its lines.

## Items, in order (each committed green on its own)
1. The outage and flap tests:
   - the NTP mid-flight group joins both sets;
   - the reset path's boot sync: a bounded wait for ntp synced in `_assert_recovered`, the bound reusing
     `_NTP_RESYNC_AFTER_RESET_TIMEOUT_S`;
   - the retry chain: when NTP's counter grew in the window, wait for a fresh NTPLastSyncAge, or until
     `_NTP_SYNC_RETRIES` × (`_NTP_RETRY_INTERV` + one attempt) has passed since serving, whichever comes first. Each
     bound is derived from src with lines, as a tunable with its row.
   Bites on synthetic data:
   - an entry of the group fails the old set and passes the new one;
   - a retry failure landing after the old end fails the next window under the old test, and lands in its own window
     under the new one.
   Put it through the dev twin where the body runs there. The body needs `bench.ap_down()`, so if it does not run
   there, say so and rely on the bites.
2. The console test: the drain after `port.close()`, as CRr2b9 designed it (`_wait_for_slots_to_drain`, its timeout a
   new tunable with its row). Add a synthetic bite: an adversary entry logged after the old end fails the next window
   under the old test, and lands in its own window under the new one.
3. If within budget: the overlap fix in its two sibling scripts and the HTTP bench counterpart of the ISL test
   (crr2b2_bench_log_check_rest.md item 3).

## Notes
- File edits use the Edit or Write tool. A deletion is its own Bash call. No `git stash`, no nohup.
- Every run goes through your own run wrapper (copy CRr2b9's), with RUNS.md lines naming `U35 lane CRr2b10`.
- Before each heavy twin run, check `uptime` and the process list: never more than 4 heavy processes on the host.
- Never touch `S/u35/laneC/crr2b4/plant_i1`.
- Commit subject `U35 lane CRr2b10: <summary>`, with the two trailers. Do not push. A refused command stops you.
- Count your tool calls. At 80, commit what is green and hand back at a seam.
- Hand-back:
  - commits;
  - per item, the evidence with log paths;
  - every set changed (before, after, lines);
  - added bench time per test;
  - the twin runs;
  - the review_rows.py counts;
  - the files whose twin record changes;
  - last line "nothing of mine is running".
