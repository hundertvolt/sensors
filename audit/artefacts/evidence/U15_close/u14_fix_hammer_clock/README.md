# U14 fix evidence (the commit "U14 fix: the UART hazard hammer and retention checks judged on a poll-round clock", pushed with the U15 close). Paths below name the session scratchpad the runs used.

# U14 fix evidence: the UART hazard hammer/retention checks on a poll-round clock

Worktree `scratchpad/wt-u14fix`, branch `audit/u14fix`, base `1cff5a2`. Every run at `nice -n 19`, under
`unshare -n`, one interpreter at a time, `-X heapsize=16M`, `TZ=UTC`,
`MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen` (device modules regenerated first).
`orig/` is `git show 1cff5a2:tests/test_uart_comm_hazard.py`; `oldclock/` is the FIXED file with the one line
that installs the poll-round `time` removed (deadlines back on the wall clock, the planted stall still installed).

## 1. Reproduction on the current code (`orig/`)

Scripts (in `scratchpad/u14fix/`): `repro_stall.py` blocks the whole interpreter `D` ms right after the k-th
`asyncio.sleep_ms()` the UART modules make once the body's measured window has opened (counted by the body's own
`_scrub()` calls); `probe_outcomes.py` records every GET's outcome of one faulted-hammer body.

- `count_clean.log`: sleeps inside each body's measured window, no stall.
- `sweep_faulted_nocrc_D40.log`, `..._D40_figures.log`, `sweep_faulted_nocrc_th32768_D40_figures.log`:
  one 40 ms stall at every 2nd/3rd point of the faulted window, standard binary. Never above the bound there
  (max 448 B = 14.9 B/failure at -1, 320 B at 32768); the large figures cluster at the END of the burst.
- `tail_faulted_nocrc_th-1_D40.log`: k = 560..596, every point, standard binary, with the responder's failed
  listens counted. The large figures (352-416 B) are exactly the runs where the initiator's LAST GET failed and
  the responder had not yet failed its listen (`responder_failed_listens=0+0`): its recovery is in flight at the
  final `gc.collect()`, so live state is counted as growth.
- `tail_faulted_nocrc_th-1_D40_settrace_binary.log`, `repro_faulted_nocrc_th-1_D40_settrace_binary_repeat.log`:
  the same on `build-settrace` (the binary CI's coverage job runs), where every frame allocates: the same pattern
  measures 576-672 B = 19.2-22.4 B/failure > 16. **The flip, reproduced** (about half the repeats at one k, since
  the wall-clock round count varies). CI's 1216 B is consistent with the same live state under the active tracer
  and a slower runner (inferred, not reproduced byte for byte).
- `periodic_faulted_nocrc_th-1_D40_probe.log`: up to 119 stalls spread over the window, up to 30 failed calls
  in it: 0 B every time. Mid-burst failures retain nothing; only the state in flight at the sample counts.
- `faulted_outcomes_orig.log`, `faulted_outcomes_newclock.log`: the faulted hammer's
  fault is ONE stream offset, so only the first GET of 60 fails; the measured burst holds 0 failures.

Clean hammer and retention (`sweep_clean_*_th-1_D300_first_transactions.log`): one 300 ms stall in the
reply wait of a measured transaction drops it: `only 149/150 hammered transactions completed` (27/40 and 22/40
of the first 40 points).

## 2. Guard positions

`guard_probe.py` runs the three new guards (both CRC arms) at chosen stall positions.
- `guard_positions_oldclock_standard.log`: on the wall clock, k = 3..5 flips the retention check (`119`) and the
  sustained hammer (`149/150`) in both arms; the faulted hammer never flips on the standard binary.
- `guard_positions_faulted_oldclock.log`: the faulted guard on the wall clock flips on `build-settrace` at
  k = 2..5 (D 40 and 300; 576 B) in both arms; never on the standard binary.
- `guard_positions_newclock.log`: on the poll-round clock, 96/96 pass (k = 1..6, 14, 16, both binaries).
Chosen: `_PLANTED_STALL_AFTER = 4`, `_PLANTED_STALL_MS = 300` (past both budgets, 30 and 240 ms).

## 3. Verdict runs on the final file (`final/`, `final/SUMMARY.txt`)

3x standard at gc -1, 3x at 32768 (`tests/_threshold_runner.py`), 3x coverage (`build-settrace`,
`tests/_coverage_runner.py`), plus the old-clock variant once standard and once under coverage:

| run | result | wall |
| --- | --- | --- |
| gc -1, x3 | 104/104 each, 0 MemoryError lines | 71 s each (orig file: 98/98 in 64 s) |
| gc 32768, x3 | 104/104 each, 0 MemoryError lines | 74 s each |
| coverage, x3 | 104/104 each, 0 MemoryError lines | 99-100 s |
| old clock, gc -1 | 100/104: retention `119` x2, sustained `149/150` x2 | 78 s |
| old clock, coverage | 98/104: the same four plus faulted `576 bytes over 30 failures = 19.2 B/failure` x2 | 104 s |

## 4. Checks

`ruff.log`, `mypy_ci_scope.log` (`src tests tests_hardware/device_scripts`, cold cache), `mypy_noargs_scope.log`
(pyproject scope, cold cache), `pytest_checks.log` (comment cap, decision vocabulary, citations, tunables).
