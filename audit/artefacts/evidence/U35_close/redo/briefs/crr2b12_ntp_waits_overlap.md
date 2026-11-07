# CRr2b12: the NTP end waits, the overlap fix, the HTTP claim (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then CRr2b11's hand-back `S/u35r/handbacks_redo/CRr2b11.md` (its findings and bites), and
`S/u35r/briefs/crr2b10_console_outage_overlap.md` item 3 only when a point is unclear. Worktree `S/wt-u35crr2b`,
branch `audit/u35-crr2b` at 34cd5235 (clean). Logs in `S/u35/laneC/crr2b12/`; the bites in `S/u35/laneC/crr2b11/`.

## The lead's review of CRr2b11 (binding)
- Item 1's proofs are kept; the lead added 34cd5235 (E NTP_RETRIES in the bus flapping set). Item 2's root cause is
  accepted: a torn block from a stop mid-write, the design's allowed cut, correctly reported; not a defect.
- Item 3's two questions are test-only, add no write and add coverage, so they are the lead's (CHECKLIST 1d),
  decided (agent, 2026-10-27): the SCD30 script's writer waits for an SGP40 round in flight through the shared
  `read_loop`, and `_overlapped()` moves to `_shared/bus_reader_loops.py`; the HTTP counterpart cannot prove bus
  overlap (GET /sensors does no I2C), so that proof stays with the flash tier, and the bench test states exactly
  what it proves. No firmware exposure for a test.

## Items, in order (each committed green on its own)
1. The bus flapping test's end wait: move `_wait_for_ntp_quiet()` and its two Part N rows into `_load.py`, used by
   test_network_resilience.py and the flapping test alike. CRr2b11's bite cases 3 and 4 then pass their next window.
2. test_wifi_networking.py:97's narrow NO_REPLY: bite the reading first (a fake board, the attempt sent in the last
   5 s before the unblock); if it bites, end the test with its siblings' `wait_until(ntp_synced)`. Fix the stale
   comment at test_network_resilience.py:371-374 (a settings change clears Synced since the 2026-09-29 ruling).
3. The SCD30 sibling script: the writer waits for an SGP40 round in flight; the overlap check as b63be1b6's, gated.
   The NVM write count and sites stay exactly as they are (two: the write and its restore). Bite: a writer that
   does not wait fails the check on a run where it starts in a gap. Run it through the twin harness where it runs.
4. The ISL HTTP bench test: its docstring and claim name what it proves (the REST path under load while the write
   runs) and point at the flash tier for the overlap proof. No assertion is weakened.
5. Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
Commits; the bites; per item the result; the NVM write count before and after (unchanged); the added bench time;
last line "nothing of mine is running".
