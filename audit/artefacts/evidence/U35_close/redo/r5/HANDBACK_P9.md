P9 hand-back, written by the agent (Tue Nov 10 10:44:37 UTC 2026)
Commit 54bac5f8 on audit/p9 (S/wt-p9, from 81e2ebcd), not pushed. 21 files, +357/-409 (CLAUDE.md 878 -> 801, SPEC 12163 -> 12192).
1. Credits. 136 "owner-reviewed, 2026-11-06" suffixes gone (SPEC 127, CLAUDE.md 6, UART changelog 1, integrate-module skill 1,
   scripts/_digital_twin_scenarios.py 1); the 10-01/02 review tags stay. CREDIT_ledger audit-era rows in my files: 16 changed
   (CLAUDE.md 3, SPEC 12, src 1); 5 already plain (G/C); SPEC:4031 gone (fsync). G had credited the webserver's sequential
   ResetErrors to the owner ("the error-log reset sequential"), in no record: agent, in src/asy_webserver_service.py:815 and SPEC A.8.
   CREDIT2 rows in my files: 86 = 81 changed + 4 needing no edit (CLAUDE.md :64/:66; SPEC :10204/:10236 already
   "(owner, 2026-09-24)") + 1 gone (:6791). Comment-only in src/ (5 files), devices/ (12 lines), scripts/ (2 files); line counts
   kept, mpy-cross output byte-identical for all five src modules (9123/9399/9915/14278/6764 B): sizes, imageFreeBytes unchanged.
   UART changelog B10: the link's codes are its bands in the one global catalog (E 75-99, W 54-59; owner, 2026-09-25).
2. SPEC A.4: "each status byte is its own WRITE, so every byte is committed by a CS deselect (owner, 2026-11-10)" replaces the
   power-loss reason; the 09-18 account's other elements stay; the 2-byte-write sentence was not in SPEC (nothing to drop). 2 lines.
3. Starter role KEPT (agent, 2026-10-07: the name alone sorted start_calibration(), a REST command, among the starters). English
   KEPT (agent, 2026-11-05: the legacy code carries German comments, e.g. legacy async_connect.py:512). "Unrelated issue fixed or
   entered" REMOVED (2 lines): only a session's record of a WP-phase instruction, no incident; the owner's words in the bullet above
   ("Do not ignore any test or run failures", out-of-scope items parked) cover it. One declared scope per config value: rule
   REMOVED (no owner words, no demonstrated need), the three homes stay as current fact (7 -> 4 lines). BACKLOG settings-store goal
   REMOVED (5 lines): no owner words, no need, nothing waits on it. Knowledge: texts in 81e2ebcd (CLAUDE.md:542, SPEC:3379, BACKLOG:427).
4. CLAUDE.md UART 47 -> 7 lines, memory 45 -> 9 (rule + pointer). Moved whole, actor/qualifier/scope unchanged: J intro (dev's two
   instances, 09-11 quote), J.1 (+13: Python-led flag-day, untouched wire format, prototypical/owner holds every unit, C-side testing
   post-audit, changelog scope), J.6 (reconciliation clause 09-26), D.3 (the whole 10-22 exerciser answer, +3), I.4 (rock-solid quote
   +2; the outside-the-firmware collect rule with its three quotes, +14). README: 3 stale per-device lines -> per hardware family.
   BACKLOG :26-31 -> "None open." (both facts live in SPEC :211 and C.5). work-routines SKILL :29 and :48 fixed (still false).
5. Part N: 12 rows estimated -> legacy <path:line>: system.reset_delay_s/task_check_s/timer_base_period_ms/task_fail_increment/
   task_fail_max (legacy/dev_drivers/system_service.py:11/15/14/16/17), module.max_error (sensortask-wozi.py:29), led.min_signal_s,
   notify.min_sleep_ms, notify.cfg_fail_interval_s (neopixel_signal.py:128/190/161), sgp40.fram_verify_mins (asy_sgp40_driver/
   __init__.py:22), sgp40.backup_counter_max, i2c.probe_settle_ms (dev_drivers :175/:259). ntp.plausible_* stay estimated (no legacy
   check exists). HTTP 5 s/15 s and DNS rows untouched, as G left them.
6. H.7: ~2.2 req/s = one /status build's CPU (~455 ms) before the 11-06 fix, re-measure owed; BACKLOG bench row added (4 lines).
   C.7: the 1 s UART cadence through the sweep -> silicon figure owed. A.4: the twin's 1-in-8 names its condition (no wire time, the
   earlier yielding path) and the owed silicon figure. Twin fidelity rows (digital_twin/README.md:213/:248, T's) still hold;
   stall.wlan_switch holds (its BACKLOG bench item is filtered: identifiers only). 7. No T sentences reached me; G's credit, item 1.
Checks: targeted tests_scripts 1,113 (2 red on my first forms: comment cap on a >120-char script header line, decision vocabulary on
   the AmbPres tag; both green after); lint_direct clean; under heavy.lock p9: uv run pytest tests_scripts 6,804 passed, 1 failed
   (test_twin_process_spawn: default /root/pico-toolchain lacks C's qstr override, (c); passes with PICO_TOOLCHAIN_DIR=S/tc-c);
   rebuild ok; PICO_TOOLCHAIN_DIR=S/tc-c scripts/test.sh PASS: 121 files, 5,347 tests, tests_scripts 6,805, 0 failed, no MemoryError.
Decisions (agent, 2026-11-10): no audit IDs in text (test_citations fails on OR\d+ and E05): OR forms as owner + the row's date;
   "DP E05" as "the wiring plan deleted in `7356bc8`" (E09 likewise); `8c4a73d`; uv_sync_backoff_step_s estimated, "choice".
Findings: SPEC:547 is a filtered line: only its credit fragment was read and edited (quote dropped, owner 10-08 kept). Slip: one
   unfiltered sed of two CLAUDE.md lines was refused by the harness, nothing printed. Scratch: ftmp_p9 only. Nothing of mine is running.
