# N11d: the last measured waits, the scanner made fit, and the tagging from it (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then `S/u35r/briefs/n11c_waits_rest.md` (its rules stand), then N11c's hand-back `S/u35r/handbacks_redo/N11c.md`
(the state, the scanner `S/u35/laneC/n11c/tools/waits2.py`, its bites and counts, the 7 item-3 candidates).
Worktree `S/wt-u35n11c`, branch `audit/u35-n11c`, fast-forwarded to the integration head 173b88ea (N11c, CMr1i and
CRr2b merged; clean, rebuilt). Logs in `S/u35/laneC/n11d/`.

## The lead's review of N11c (binding)
- 7a0884d9 is kept (14 tags, no value changed, AST identical after substitution).
- Its four test files were edited with a Python heredoc: against the rule. Every file edit is the Edit or Write tool.
- The scanner is right to be held back from tagging while it over-reports. Count numbers are not the goal: every
  untagged real-time wait found, nothing tagged that is not one.

## Items, in order (each committed green on its own)
0. A gate red, first (lead, 2026-10-27). The full gate on int 9ce2e376 at 32768 (`S/u35/lead/gate9ce_32768.log`
   :12138-12160 and :12435-12447) failed `tests/test_asy_uart_link_driver.py`'s
   `test_a_hazard_run_reports_every_verdict_then_returns_to_the_echo_nocrc` and
   `test_a_hazard_run_sends_every_raw_frame_without_a_copy` with TimeoutError from `run(go(clock), RUN_LIMIT_S)`:
   `l1.uart_comm_harness_run_limit_s = 10`, a real-time bound on a driven-clock run, registered "estimated -
   measurement owed" (SPECIFICATION.md, its L1 row). The -1 stage passed 50/50; at 32768 the host also carried a
   lane's whole tier, a lane's reader runs and a lane's load loops. The same stage retried `tests/test_sensortask.py`
   [dev] and `tests/test_digital_twin_uart_link.py` past scripts/test.sh's 240 s per-file bound (log :8491, :11073).
   Root-cause each: wall and CPU time (`/usr/bin/time`, user+sys) of every RUN_LIMIT_S user and of the two files, at
   both stages, on 5a8c6e35 (before lane CMr1i's DrivenTime change) and on your head, quiet and under a load like the
   gate's; say whether a change brought the cost and how close the unloaded case sits to each bound. Fix by
   efficiency first (owner: "Test duration is to be fixed by efficiency, not by cutting strictness"); a bound's value
   changes only from a measured basis, put to the lead with the numbers before you change it, and scripts/test.sh's
   per-file bound and retry stay. Bite: a fixed test still fails on a planted hang. For 5a8c6e35 use `S/wt-u35hp1`
   (clean, rebuilt; runs only, no commits, one run at a time).
1. Item 1's rest: `_sensortask_scenarios:2612-2613` at 32768; `sensortask_integration:307` and `timer_pool:81`
   measured at both stages, then tagged; the fake NTP server rows at 32768 (fix the runner path, show it reaches the
   threshold runner). Same rules as N11c: no value changed, AST identical after substitution, a bite per row.
2. The scanner: fix its two named causes (the driven-clock class from every name and attribute, call targets
   included; `obj.m()` resolved only to classes the file constructs or imports by that name). Re-bite: the 9 plants
   9/9, the tagged control 0. Recount, then class every site left by reading: a real-time wait (tag it, measured
   L1 row), a driven or virtual wait, or a count that is not a wait (each with its reason). Tag per file, a commit
   per batch of files. The real find already shown (`run_generic_integration`'s `_WIRE_LOG_CLEAR_INTERVAL_MS = 1`)
   among them. Once it is fit, the scanner replaces v1 wherever v1 is a check, so the gate sees the six shapes.
3. Item 3: the CMr1h candidates (the 7, and re-find the 8th).
- Lanes CMr1j/CMr1k will edit the integration, clock_jump, ntp, scd30, sgp40 and wifi_modes twin files later: tag
  waits there, change nothing else in them.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
Commits; per tag its measured basis (both stages); the scanner's bites and counts before and after; every classed
site's class and reason (a summary per class, the list in a log); last line "nothing of mine is running".
