T4r3c hand-back, saved by the lead from the message it sent (2026-10-27). Commit f78e6b15 on audit/u35-t4r3 (on f7d6962b).

T4r3c hand-back (worktree S/wt-u35t4r3, branch audit/u35-t4r3). One commit, **f78e6b15** (on f7d6962b), not pushed. Nothing is uncommitted. `config_SYSTEM.cfg` at the worktree root is left for you to delete.

**Item 1, the five remaining devices: all green at both GC stages, one device run at a time.**
- All six derived devices now pass at both stages: 12 counted runs. Each one has rc 0, `Result: PASS`, 0 FAIL, zero memory markers, and exactly one wrap inside Run 11's window, at 0.085-0.809 of it.
- The step across the wrap was 101-107 ms each time, which reads the 2**30 period from inside the run.
- In every run the binary hash was build-ticks30's (7c241764…) before and after, the suite launched the copy's path, and there was no rebuild line.
- Per device (-1 / 32768): dev 0.415 / 0.651 (348 OK), grkizi 0.132 / 0.401, klkizi 0.529 / 0.496, schlafzi 0.603 / 0.446, wozi 0.085 / 0.474 (308 OK).
- The records are in S/u35/laneT/t4r3/twin/results.jsonl, logs and kept stage directories in S/u35/laneT/t4r3/twin/logs/.

**Item 2, placement misses: 5 uncounted, every one a clean pass.** The cause is Run 11 itself: `_soak_warm_up` ends adaptively (no new MEM_SAMPLE floor for 20 cycles, at most 100), so the window's start moves by tens of seconds between runs, at -1 too. grkizi -1's window started 56.7 s after the first read in its place run and 123.7 s in its suite run.
- The misses: grkizi -1 at -0.204; grkizi 32768 at -0.116; wozi -1 at -0.017; wozi 32768 at -0.092, and again in round 1, where Run 11 ended before its wrap.
- **Deviation:** the brief's rule covered only a 32768 miss at 1 or more, and re-placing from a single place run proved unreliable. The driver now re-places a miss at either stage: a fresh place run at that stage, then the middle of the span every window observed at that stage shares (place runs plus each suite run's own Run 11), at most 3 rounds per stage. Misses stay in the table, marked not counted.
- I first allowed only one round. wozi 32768 needed two (shared span 130726-146995 ms).
- Seen failing first, under the old rule: twin_rest stopped at grkizi -1's miss, twin_wozi3 at wozi's round-1 miss. The guard (S/u35/laneT/t4r3c/check_stage_logic.py) passes all 14 cases; scratch bites of the -1 re-place and of the miss detection fail it, and both bites are deleted.

**Item 3: no wrap-safety defect.** Two defects were the driver's own:
- dev's suite runs Run 3 again on CRC16, which prints a second `Result:` line, and its logs sit outside the stage directory. The driver now expects both parts and keeps and scans those logs. Red first: case 8 failed on the old check.
- dev -1's record was written before that fix. I amended it in place, marked `amended`: its CRC16 log was kept and scanned, with no marker.

**Item 4:** timing.md's 2**30 section is regenerated with my finalize copy (S/u35/laneT/t4r3c/finalize_new.py). The "State (partial)" paragraph is gone, the table has 17 rows, and the L1 half is unchanged byte for byte. Checks before the commit: ruff and host mypy (cold cache) clean on ticks30_twin.py; test_citations and test_decision_vocabulary 21 passed.

**Item 5, the F.1 sentence for D3r:** "Wrap safety was run once on a scratch Unix-port build with the `2**30` tick period, its counter started just before the wrap: every L1 test file whose code reads ticks (84 files; 109 jobs with the per-device files on every derived device; 654 runs) passed with the wrap a quarter, half and three quarters into its run, and every derived device's twin suite (all six) passed with the wrap inside Run 11's soak window, at both GC stages and with no memory marker (agent, 2026-10-27)."

**Item 6:** S/tc-t4r3 (1.1 GB) and S/u35/laneT/t4r3/build (103 MB) are deleted. I used literal paths, after checking that no process used either.

**Runs** (each has a RUNNING line and a done or CUT line in RUNS.md):
- twin_dev rc 1 (the two-`Result:` stop) and twin_dev2 rc 0.
- twin_rest rc 1 (grkizi -1 miss).
- twin_rest2 was cut by the 05:15 restart. All its records up to wozi -1 round 1 were whole, and wozi 32768 had no record, so only that stage ran again.
- twin_wozi3 rc 1 (round-1 miss) and twin_wozi4 rc 0.
- checks4 rc 0.

**Facts for the lead:** the restart left my twin_rest2 namespace runtime directory under S/u24/nsrt/, and I did not remove it.

nothing of mine is running
