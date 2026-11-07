CO2 hand-back, written by the lane (2026-10-27 08:54 UTC)

Lane CO2, branch audit/u35-conf2, worktree S/wt-u35conf2, on cce274e1. Seam taken after the U10 table at about 84 tool
calls. Nothing pushed, nothing uncommitted (node_modules was untracked before I started). Logs: S/u35/laneB/co2/.

## Commits
- 780d2c62 U35 lane CO2: U10's open rung cells get their tests and the probe row its re-triage.
  Files: audit/b3/conformance.md, conformance_walk.py, queue_c.md (stamp only), tests/test_asy_base_classes.py,
  tests/test_digital_twin_bus_hazard_concurrency.py (one new test in the ladder section, nothing else in the file
  touched), tests/test_digital_twin_timer_pool.py.

## Cells by table, before → after
- U10, 23 rows:
  - L1 named: 21 → 22 (the FRAM probe row).
  - L2 named: 17 → 20 (`_init_*()` R3 and R4, Timer arm R6).
  - Bounded / once / race-free complete: 17 → 21 (adds `_init_*()` R3/R4, Timer arm R1, Timer arm R6).
  - The FRAM verify_present row is re-triaged (below). Its L1 and proofs are filled; its L2 is still open.
- U16: the `verify_present()` row (no rung named) takes the same cells as U10's probe row. The other 19 U16 rows are
  not started.
- U13 (21 rows), U15 (33), U16 (19 more), U17 (6), U18 (17): not started. They are still as the record has them.
- The walk's DONE text now reads "each test biting in review.md or, for a test this review added, red on a planted
  fault". CO1's race test and my three new tests have no review.md row (see the render, below), so their bite is the
  plant recorded here.

## Lead's decisions applied (agent, 2026-10-27)
- `_init_*()` R3/R4 is kept as designed. Each failed setup starts its own episode. Two failed setups run one rebuild
  each, serialized by the bus lock and bounded by the restart budget.
- A rung cancelled in its lock wait counts as run. Reader tasks are cancelled only by the shutdown sequence, at
  src/asy_system_service.py:462-464 (the `t.cancel()` loop after "Shutdown: storage quiesced" at :461), and the unit
  resets after it.
- Both are written into the walk's SETUP_DONE cell text.

## Tests added, each with its red-first evidence
Each test passed at once on the base, so each is a guard. Its bite is a planted fault in a scratch copy of the src module
(PLANT dir first on MICROPYPATH). Nothing planted is committed.

1. tests/test_digital_twin_bus_hazard_concurrency.py::test_two_setups_failing_together_each_rebuild_the_controller_once_one_after_the_other (L2)
   - What it does: both chips of the shared bus (SGP40 + BMP3XX ladder device) fail their task's setup once. A gate on
     each reader's `_init_failed()` holds both until both setups have failed. A sibling session then holds the bus lock.
     The first rebuild is released and parks on the lock (recoveries already stepped). Then the second is released.
   - What it asserts: two rebuilds, at most one inside the lock at a time, none beside the sibling's session. Each reader
     has exactly [E INIT, W BUS_RECOVERY]. Chips stay wired. The supervisor restarts both inside its budget (no reset
     armed, no watchdog trigger).
   - Plant B, no own episode (the `_bus_mark` reset removed from `_init_failed()`): red with "the rebuild of SGP40's
     failed setup never started" (bite2_plantB.log).
   - Plant A, no bus lock in `recover()`: red with "got 2 rebuild(s), 1 at once, 2 outside the lock"
     (bite2_plantA.log).
2. tests/test_asy_base_classes.py::test_two_wakes_finding_one_failed_arm_persist_it_once_however_they_interleave (L1, Timer arm R1 race-free)
   - What it does: the first `_timer_fault()` parks in its log write, held open by a gate. A second wake runs meanwhile.
     The waits are bounded condition waits, with no sleep count.
   - Plant: `_timer_reported` set after the await. Red with "a failed arm two wakes found was persisted 2 times"
     (biteT_plantT.log).
3. tests/test_digital_twin_timer_pool.py::test_read_triggers_that_never_arm_end_at_the_budgets_reboot_with_one_entry (L2, Timer arm R6)
   - What it does: the alarm pool is held at 0 under the real supervisor on a driven clock.
   - What it asserts: the budget escalates (`_reset_decided`, then the starve flag), with exactly one E TASK_BUDGET_REBOOT.
     No board reset and no watchdog trigger before the reboot path.
   - Plant: no budget escalation in `_supervise`. Red, but the failure is run_timed's real-time bound (TimeoutError at
     the run), not the scenario's own message. The log shows the supervisor restarting for good. The driven 20 s wait
     takes longer than the 60 s real bound under endless restarts (biteR6.log).

## Formal checks on the finished change
- Both GC stages, zero memory markers:
  - test_asy_base_classes.py: 199/199, 0.56 s at -1, 0.66 s at 32768.
  - test_digital_twin_timer_pool.py on all six devices: 5/5 each, 12.7-16.4 s.
  - test_digital_twin_bus_hazard_concurrency.py: 23/23, 125.8 s at -1, 132.5 s at 32768 (u10_checks.log).
  - After the last annotation and comment edits, the new twin test alone at both stages (u10_checks3.log).
- After-times are not compared with a base table. The lead's S/u24/base_times.tsv has no rows for these files here, and
  the bus-hazard file's time in base_testsh_m1.log was not extracted.
- lint_direct: rc 0.
- mypy, main pass and twin pass: clean (the twin pass after typing the two saved methods).
- The readers (test_citations, test_decision_vocabulary, test_comment_block_cap): 668 passed.
- `review_rows.py --check`: rc 1, from six flagged rows with no verdict, none of them mine:
  - test_digital_twin_clock_jump.py::test_a_reader_stamps_each_sample_with_the_clock_as_stepped
  - test_digital_twin_clock_jump.py::test_a_backup_dated_after_a_backward_step_is_expired_under_a_max_age_and_kept_under_none
  - test_digital_twin_hot_replug.py::test_a_power_cycled_bmp3xx_is_reconfigured_without_a_ladder_step
  - test_digital_twin_ntp.py::test_an_sgp40_restore_waits_out_the_outage_and_follows_the_sync
  - test_digital_twin_ntp.py::test_a_lost_sync_keeps_the_local_time_and_the_alert_flashing
  - tests_scripts/test_twin_wiring_contract.py::test_identical_devices_share_one_run_on_the_first_of_them
  - The first five are setup_credit_only, the last same_callee. They came in with the CMr1 merge, and CMr1h is still
    editing some of those files. The render refuses while they lack verdicts, so review.md was NOT refreshed and CO1's
    test has no row yet. My three new tests are unflagged by the scan, so once those six get verdicts a plain
    `python3 -I audit/sweeps/review_rows.py` renders all four as "biting as is". Lead's call: who gives those six their
    verdicts.

## Defects
None. Every rung examined held its property; the three new tests are guards.

## FRAM verify_present re-triage (U10 row and U16 row)
- The record's "no product caller" is stale. The probe is called from the blank-read verdict,
  `_blank_verdict()` src/asy_fram_manager.py:149-154.
- A lock wait that times out returns False with one E LOCK_TIMEOUT (src/asy_fram_driver.py:492-496) and leaves `lost`
  unset. So the chunk keeps its blank verdict and no loss is declared, and no rung follows.
- L1 tests: test_asy_fram_driver.py::test_verify_present_bounded_wait_returns_false_instead_of_hanging_when_lock_already_held
  and test_asy_fram_manager.py::test_a_probe_that_cannot_take_the_lock_keeps_the_blank_verdict. Both are biting in
  review.md.

## Cells still open, with their reasons
- U10 `_init_*()` R2 (participant): points to U15's "a driver's chip identification fails at setup" rows. U15 is not
  started.
- U10 deferred config flush R1: L2 and race-free are open.
  - The L2 gap: no twin test heals a failed flush by the next PUT. Its natural home is a twin config or webserver file;
    the bus-hazard file is not the place.
  - The race-free gap: a forced interleaving of a PUT with a failing flush is needed at L1, in test_asy_config_manager.py.
- U10/U16 FRAM probe: L2 is open.
  - Why: no twin test holds the FRAM session past the probe's bounded wait.
  - Where it belongs: tests/test_digital_twin_fram.py or a new twin file.
  - Not the bus-hazard file: CMr1h owns its erase tests.

## Map for the next lane, U13
Read-only work, done while my checks ran. The test names are on cce274e1; check their review.md verdicts before citing
them.
- "I2C transfer raises OSError" row:
  - R1, R2, R5 are the drivers' and the supervisor's: point them to U10 "a sensor/WLAN cycle fails".
  - R3 and R4 take U10's BUS_PROOF cells (the I2C clear/recover tests named there).
- "bus held at power-up" R3:
  - test_asy_i2c_driver.py :1556-1630, the `test_the_boot_clear_*` group, including the fake-clock bound at :1611.
  - test_asy_base_classes.py::test_init_done_re_arms_the_rungs_and_reports_a_held_boot_bus_once_per_bus (once per bus).
- "slave holds SCL" row:
  - R3 and R4: test_asy_i2c_driver.py :1708-1760, including clear_and_recover_end_a_held_scl… at :1718.
  - R2: the drivers' participant rungs (U15).
- `scan()`: still no product caller. `git grep '\.scan('` in src/ and buildgen/ finds only the wrapper itself,
  src/asy_i2c_driver.py:399-402. The disposition stands.
- "zero-length probe NAK":
  - R3/R4: U10's `_init_*()` R3/R4 cells.
  - R5/R6: U10's `_init_*()` R5/R6 cells.
  - Probe tests: test_asy_i2c_driver.py:420-578.
- SPI "held bus" R3: test_asy_spi_driver.py:414-445, the cs_pin_* tests (CS inactive after a session, an exception, or a
  released lock).
- SPI controller state R4: test_asy_spi_driver.py:394::test_configure_is_applied_fresh_on_every_aenter.
- SPI 32+ byte read R1/R4: the dual copy. At L2, test_digital_twin_bus_hazard_concurrency.py::test_fram_recovers_after_an_injected_spi_read_fault
  and test_fram_chunk_loop_absorbs_a_transient_spi_rx_overrun.
- Construction raises R7 and the UART rows: dispositions (buildgen's pin checks; U17 cross-reference).

## Questions for the owner
None. The two open design questions were the lead's and are decided above.

## Runs
All exited; logs in S/u35/laneB/co2/; RUNS.md lines "U35 lane CO2".
- u10_checks rc 0 (539 s)
- u10_checks2 rc 0 (wrapper; its ruff and readers findings were fixed)
- u10_vocab rc 1, fixed
- u10_checks3 rc 0 (its review_rows step rc 1, as above)
- Direct single-test runs and plant runs: new1/new2, bite_*, bite2_*, biteT_*, r6, biteR6.

nothing of mine is running
