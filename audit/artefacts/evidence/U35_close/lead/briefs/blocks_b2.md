# U35 lane B, blocks B2a, B2b and B2c: the B3 measurements and the conformance review (lead, 2026-10-22)

## All three blocks
- Base: the integration head the lead names when starting you (the W6 gate's head, every lane merged, the twin record
  re-recorded at both stages). Branch `audit/u35-b2`, worktree `S/wt-u35b2`, already rebuilt. Logs in `S/u35/laneB/b2/`.
  Commit subject `U35 lane B2<x>: <summary>`; decision tags "(agent, 2026-10-22)".
- Read first: `S/CHECKLIST.md`, `S/u35/briefs/common_u35.md`, `S/u35/handbacks/B1_final.md` (your start state and what
  B1 left), the rulings R-20, R-21 and R-22 and LEAD NOTES 4 and 20 in `S/u35/lane_plan.md`, and each step's text
  (`python3 -I S/u35/tools/steps.py --standing <numbers>`) with its P1 row (`grep -n "^| <n> |" S/u35/lane_plan.md`).
  Every `audit/b3/` file states its requirement, completion rule and row format in its header: fill to that, nothing
  invented, and a cell that cannot be measured here says why in one line (hardware cells go to queue_c, which is U37's).
- Your files: `audit/b3/*` and `scripts/test.sh` (its heavy-file dispatch list only). You measure; you do not change
  the twin suite, the runner, `src/` or SPECIFICATION.md: a value they need goes in your hand-back for T4 (suite
  values) and D3 (SPEC sentences, Part N Basis cells), with its source log.
- Gate 2 (on `7851668`, the head you start from) has its logs, both stages, in `S/u35/gate2/` (`gc_default.log`, `gc_32768.log`, `coverage.log`,
  `twin_<device>.log`, `npm_*.log`, `vmstat.log`); read them, do not re-run what they already measured.
- Never run real hardware tools (mpremote, picotool, nmcli, iw, iptables); never read arduino/; never edit ext/ or
  legacy/; no git stash; kill only by a pid you checked; one test run at a time in your worktree; every run's start
  and exit line in RUNS.md; disk check before every long run (CHECKLIST 22). Do not push. About 60-80 tool calls per
  block; past 80, commit what is green and hand back the rest at a seam.

## B2a: the timing measurements (alone on the host: the lead runs nothing else meanwhile)
1. `audit/b3/timing.md` (A.U35.23, M.PROC.024 (1)): its post-B3 column per level and GC stage: wall clock, peak RSS,
   host SSD writes (`/proc/diskstats`, as CLAUDE.md's host-wear rule measures them), test counts. Wall clocks from the
   gate logs where they hold them; RSS and SSD writes from one quiet run per level and stage you start yourself.
2. Steps 107, 120 and 161 (3): the heavy-file dispatch list in `scripts/test.sh` re-ordered from timing.md's per-file
   times (longest first, as the list's own rule says); `tests_scripts/test_test_sh.py`'s heavy-list tests green.
3. The coverage tier's shard measurement (LEAD NOTES 20's first proposal): `scripts/test.sh --coverage` alone on the
   host, the tests_scripts tier as two `--parallel-mode` shards against one process, on one tree. Change test.sh only
   if the leg's wall drops; otherwise record the measurement in timing.md and leave the tier one process.
4. OF-150 and OF-71: what their rows ask to be measured locally, into timing.md; the lead reads CI's times after
   the push.
Hand-back (at most 35 lines): commits, per item done or left with its reason, the figures T4 and D3 need with their
logs, last line "nothing of mine is running".

## B2b: the conformance review and the walks (after B2a; the host is shared again)
1. Re-run `audit/b3/raising_walk.py`, `levels_walk.py` and `conformance_walk.py` on your head (B1 ran them at
   `f3fff0e`; lanes P and Y changed four of the walked modules since): step 104's open call groups, step 137's levels
   and intent, steps 138 and 153's rows.
2. Step 136 and R-20: review every exception in `tests_hardware/twin_record.json` against its stated reason (a reason
   that no longer holds on this head is a finding); the bite review (A.U35.03), the memory gates proven through the
   twin in a throwaway worktree (step 156, A.U35.05: each gate red on a planted `MemoryError` worded clear of both
   markers), and the wear gates (A.U35.51), into `conformance.md`.
3. Step 102's remaining columns (review, faults, matrices, e51), each to its file's completion rule.
4. One reason known not to hold (H4_final.md): `system_command_fram_erase.py` and `test_system_commands.py` say the
   resets "land after" the twin's erase, but the twin's erase took 1033-1349 ms in H4's re-record, so the 1.0 s case lands
   either side (it failed at -1 and passed at 32768; the 2.0 s case fails at both): the reason's text in the record and in
   `S/u35/laneH/h3/reasons.json` says what happens, with H4's logs as its source; no result changes.
Hand-back as B2a's.

## B2c: Run 11's calibration, the sampler and the l0-l2 Basis values (alone on the host)
1. Steps 157 (1)-(2) and 162: Run 11's calibration measured per device at both stages (M.PROC.024 (2)); the values
   T4 applies to the suite and the clause D3 writes.
2. R-22 (steps 157 (3), 163, 165): the sparser-sampling run. Whether one sampling interval gives Run 11 the same
   verdict as today's decides whether `_mem_sampler` keeps its `gc.collect()`; report the interval and both verdicts.
   If none does, say so: the owner question (step 159) is the lead's.
3. Steps 105 and 147: the `l0`-`l2` Part N rows still reading "estimated", measured where one run on this host can
   measure them, as a table (row key, value, source log) for D3; at the valve stop at a row boundary and list the rest.
4. Step 160: `load.md`'s cells this host can measure, and the FRAM write-count rate the suite's Run 3 needs (step 151's
   `fram_writes*` fields are in the runner's shutdown line), as a value for T4.
5. The FRAM both-copies-marked loss rate (SPECIFICATION.md's "roughly 1 abrupt restart in 8", measured by `399c027`'s
   twin run 5b on the earlier write order; LEAD NOTES 113): re-measured on your head the way that commit measured it,
   as a value with its source log for D3.
Hand-back as B2a's.
