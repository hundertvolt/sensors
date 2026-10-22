T2a hand-back (lane T, branch audit/u35-t, worktree S/wt-u35t). Commits: 9ccf6f8 (T1's two reds), ecac120 (suite carries, 118, 166). Nothing uncommitted.
Steps:
- T1's reds, applied and green. tests/test_digital_twin_run_generic_integration.py gets the 12th TestFlags field; the parse case now names `--test-watchdog-fault block`, and "reboot" is refused. tests_scripts/test_digital_twin_scenarios.py `_SHUTDOWN_LINE` gains `fram_writes=0 fram_writes_by=-`. Results: rgi 43/43 at -1 and 32768, scenarios 60 passed, twin mypy 0 errors.
- T1's carries, applied. `_check_exit()` fails on `run.stop_ignored`. `_shutdown()` and `_relaunch_reason()` take `interrupt=`. Run 12's after-bootloader boot (the boot its "SIGINT relaunch" follows) ends by SIGINT.
- 118, applied.
  - Run 1 reads GET /status once, after the walk. It keeps the errcount table as `<logs>/runs/run1_errcount.json` (new `RunContext.runs_dir`) and requires no E and no W entry. The read must land before the deadline, which is read by AST from `_digital_twin_scenarios._SHARED_BOOT_DEADLINE_S`.
  - New `_run_1_reformat_relaunch()`: config dir emptied, FRAM kept, relaunched. It requires exactly SYSTEM's W CONFIG_LOST and keeps `run1_reformat_errcount.json`, then ResetErrors. No Run-1 NTPSynced poll (R-4).
- 166, applied. Normal-boot cases: one W fails; an NTP E or W entry fails whether NTPSynced is true or false; a late read fails; an unreadable /status raises. Reformat cases (1, 0 or 2 CONFIG_LOST, or one more elsewhere). Run 1 with a planted W, and the relaunch, over stubs. The NTPSynced-bound case targets `_wait_for_ntp_sync`.
Seen failing / bites (logs in S/u35/laneT/):
- 19 new cases fail on 9ccf6f8's suite (t2a_seen_failing.log): stop_ignored gives `assert (0 == 1)`, `_shutdown(interrupt=)` a TypeError, Run 12 `('run12_b…', False) != (…, True)`, quiet boot an AttributeError.
- Bite 1: base suite with a planted W in Run 1 fails with `AssertionError: []`. Bite 2: `_wait_for_ntp_sync` bitten to answer True at its bound fails 3 cases (t2a_bites.log). Nothing planted committed.
- Real dev twin, head, both stages: run1_errcount.json has 22 modules and no E/W. run1_reformat_errcount.json holds exactly ('SYSTEM','W',69). Run 2's settings survive. Run 12's SIGINT relaunch reads 1. Evidence in S/u35/laneT/twin/.
Decisions (agent, 2026-10-21):
- (1) Run 1's settings PUTs move into the reformat relaunch. Emptying the config dir after them would erase what Run 2 reads, and no product-written file is restored by hand.
- (2) interrupt=True goes on run b's shutdown, not on the relaunch, whose ResetReason is read at its own boot.
- (3) Twin-suite base = 9ccf6f8's suite swapped into my own tree. The run rewrites frozen_modules, so S/wt-u35base was not used for it. My tree was rebuilt with rebuild.sh after. The readers were paired against S/wt-u35base.
- (4) The kept file is the /status errcount table. GET /system carries no errcount, so there is no separate /system file.
- (5) The stop-file child cases go through the suite's `_shutdown()`; the ignored-stop wait is 0.5 s -> 0.1 s (the child never acts on its stop file).
Times (base/head):
- Dev suite `--only 1,2,12`: -1 34.5/39.9 s, 32768 35.5/41.3 s (+16 %). That is the step's one added boot (the relaunch serves at about 4.0 s, plus PUTs and a 1.2 s ResetErrors). It already reuses Run 1's state, and there is nothing to cut without dropping the boot. Lead: please rule on it.
- errcount, vs f3fff0e: 0.83/1.26 s and 0.91/1.15 s (+0.34 s mean, under 0.5 s).
- The 11 other readers are flat (ceiling, matrix, soak, state, level_containment, port_bands, request_timeout_ceiling, twin_fake_catalog, no_variant_literals 7.39/7.34, scenarios, run_digital_twin_ci_sh 4.87/5.28). rgi 1.37/1.44 and 1.46/1.45 s.
Runs: all rc=0, mem=0.
- t2a_twin.sh (pid 11265): 4 suite runs + rebuild.
- t2a_readers.sh (pid 20597): ruff, host mypy, the 12 checks (797 passed), 12 readers paired, rgi at both stages.
- Final errcount pairs, the 12 checks again (797 passed) and host mypy 0.
- RUNS.md has start and done lines.
Red checks: none. No allow-list row orphaned. No relay lines written.
Scan (all classes, twin/tooling modes):
- T1's class-6 finding (stop file left unanswered) is closed by `_check_exit`. Nothing new found.
- STA, AP, Silent, Off and USB are unchanged on every device: no src/ or image change.
Owed:
- T4: digital_twin/README.md's Run 1 text (about :669-671 at 1dd6dd5): the relaunch, the runs/ files, settings PUT in the relaunch. Also T1's "SIGINT shutdown" wording.
- D: SPEC:8848 "Run 1 sets 5" still holds.
T2b starts from ecac120. The tree is rebuilt and the suite file is at head; twin evidence is in S/u35/laneT/twin (4.8 MB).
nothing of mine is running
