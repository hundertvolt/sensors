CO3 hand-back, written by the lane (2026-10-27 09:30 UTC)

Lane CO3, branch audit/u35-conf2, worktree S/wt-u35conf2, on 780d2c62. Seam taken after the U13 table at about 74 tool
calls. Nothing pushed. Nothing uncommitted (node_modules was untracked before I started). Logs: S/u35/laneB/co3/.

## Commits
- e6408055 U35 lane CO3: U10's last rung cells get their tests, and the timer-pool budget test fails on its own claim.
  Files: audit/b3/conformance.md, conformance_walk.py, queue_c.md (stamp only), tests/test_asy_bmp3xx_driver.py,
  tests/test_asy_config_manager.py, tests/test_digital_twin_timer_pool.py.
- 04cdd831 U35 lane CO3: U13's 21 rung rows get their cells, every one checked on the tree.
  Files: audit/b3/conformance.md, conformance_walk.py, queue_c.md (stamp only). Audit text only.

## The lead's timer-pool item (done)
- tests/test_digital_twin_timer_pool.py::test_read_triggers_that_never_arm_end_at_the_budgets_reboot_with_one_entry.
- Root cause: the driven wait was already bounded. With the plant, it failed at virtual t=21323 ms after 6.9 s of real
  time. The `finally` then hung: `_stop_graph()` awaits cancelled tasks, and the supervisor's restarts end those tasks
  on driven sleeps, but nothing drove the clock any more. So run_timed's 60 s TimeoutError replaced the claim's
  AssertionError. Found with a debug copy (dbgR6.log), not committed.
- Fix (one line): the cleanup runs on the driven clock, `await _driven(clock, "the graph never stopped",
  _stop_graph(supervisor))`.
- Re-bite with CO2's plantR6 (no budget escalation in `_supervise`): red in 8 s with "wozi: the restart budget never
  ran out - run_until: the condition still fails at virtual t=21323 ms, 20000 ms after t=1323" (biteR6b.log). Unplanted:
  1/1 pass.
- A real-time bound inside `_until` was tried first and removed: it was never what fired.
- The file's three other tests call the plain `_stop_graph()` in their cleanup. Under their own plants they could hang
  the same way. None was bitten here, so none was changed.

## Cells by table, before → after
- U10 (23 rows):
  - L1 named: 22 → 23 (`_init_*()` R2).
  - L2 named: 20 → 20. `_init_*()` R2 is now partly named: SGP40 is named, the other three drivers are open.
  - Bounded / once / race-free complete: 21 → 22. The deferred flush R1 is now complete. `_init_*()` R2 has its
    bounded and once cells, but race-free is open for BMP3XX and ISL29125.
- U13 (21 rows): every row now carries reviewed cells. Before, all 21 were the record's "open".
  - L1: 20 named or "not reachable" with its reason. One (SCL R2) points to U15's R2 rows.
  - L2: 17 named or "not reachable" with its reason. Four are open: power-up hold R3, SCL R3, SCL R4, and the SCL R2
    pointer.
  - Proofs: 18 complete or dispositioned. Three are open: SCL R2 (U15), SPI 32+ R1 "once", UART R1 (U17 cross-reference).
  - Dispositions were re-checked on the tree and in rp2 v1.29.0:
    - `scan()` has no product caller (`git grep '.scan('` finds src/asy_i2c_driver.py:399-402 only).
    - machine_spi.c:308-313 clears the RX-overrun flag and aborts RX DMA inside the failing call.
    - machine_uart.c:162-190 reads the error bits per byte from the FIFO and latches nothing.
- U15 (33), U16 (19 besides the probe row), U17 (6), U18 (17): not started.

## Tests added, each with its red-first evidence
Each new test passed at once on the base, so each is a guard. Its bite is a planted fault in a scratch copy of the src
module (PLANT dir first on MICROPYPATH). Nothing planted is committed. review.md has no rows for these yet. The render
waits on BR4's six verdicts. Once those land, a plain render should list them.

1. tests/test_asy_bmp3xx_driver.py::test_setup_soft_resets_the_chip_once_after_its_id_check (L1, U10 `_init_*()` R2,
   BMP3XX). This was a gap: no test pinned that setup() sends its 0xB6.
   - Plant BA, setup() without `await self.reset()`: red with "setup() sent CMD writes []" (bite_plantBA.log).
   - Plant BB, reset moved before the CHIP_ID read: red with "setup() reset the chip before identifying it"
     (bite_plantBB.log).
2. tests/test_asy_config_manager.py::test_a_change_queued_behind_a_failing_flushs_log_write_heals_it_and_keeps_its_value
   (L1, U10 deferred flush R1, race-free).
   - Setup: the failed flush's err_s is held open by a gate. A second write_config() is queued during it. The wait is a
     bounded condition wait (queued on the lock, or staged), with no sleep count.
   - Asserts: one write, one error, persisted again, value 8 in effect and in the file.
   - Plant C1, `_flush_staged()` without its lock: red with "the failed snapshot replaced the newer value in effect"
     (bite_plantC1.log).

## Defects
None in firmware. Every rung examined held its property. The one defect was in a test (the timer-pool cleanup above).

## Cells still open, with their reasons
- U10 `_init_*()` R2:
  - L2 for SCD30, BMP3XX and ISL29125: every twin boot runs their setup reset, but no twin test asserts it. A lead to
    check: tests/test_digital_twin_bmp3xx.py::test_event_reports_por_detected_after_power_up_and_a_soft_reset_and_clears_on_read.
  - Race-free for BMP3XX and ISL29125: no sibling-session interleaving of their setup reset. SCD30's is cited.
- U10 deferred flush R1, L2: no twin test heals a failed flush by the next PUT. Home: a twin config or webserver file.
- U10/U16 FRAM probe, L2: as CO2 left it. Home: tests/test_digital_twin_fram.py or a new twin file.
- U13 power-up hold R3, SCL R3 and SCL R4, L2: no twin test boots with, or ladders through, a held line. The twin can
  plant one (`machine.Pin.set_external_level()`, as tests/_bus_hazard_catalog.py:545-567 does at L1). Home: a new twin
  file, not the bus-hazard file.
- U13 SCL R2: points to U15's participant rows.
- U13 SPI 32+ R1 "once": no test counts the entries one failed read writes. Home: tests/test_asy_fram_manager.py.
- U13 UART R1/R4: cross-reference to U17's rows.

## Map for the next lane, U15
Located by name. Verdicts were checked only where marked (b); check the rest in review.md before citing.
- SCD30 R1, R5-R7 (periodic read fails): U10's cycle rows, plus
  test_read_loop_gives_up_after_max_module_error_consecutive_failures_and_logs_via_real_print_log and
  test_read_loop_recovers_error_counter_after_a_good_read_following_failures.
- SCD30 R2 (periodic read fails): test_a_raising_reset_logs_one_chip_set_and_no_recovery_warning, test_a_put_during_the_recovery_completes_after_it,
  and the twin's test_an_scd30_soft_reset_mid_read_leaves_every_twin_sibling_read_valid (b). Name grep found no
  "two failed reads, soft reset" test in the SCD30 file: check.
- SCD30 data-ready edge missed: test_scd_init_irq_sets_irq_trigger_after_enough_consecutive_stuck_ticks,
  test_the_stuck_pin_count_saturates_at_the_threshold, test_scd_init_irq_never_triggers_while_pin_reads_low.
- SCD30 setup fails, and chip ID fails at setup, R3-R6: U10's `_init_*()` rows, plus
  test_setup_probe_failure_never_reaches_firmware_read_or_reset, BMP3XX test_setup_rejects_unknown_chip_id and ISL29125
  test_setup_raises_on_a_wrong_device_id.
- SGP40 R2:
  - test_two_failed_cycles_turn_the_heater_off_once
  - test_a_raising_heater_off_logs_one_chip_set_and_no_recovery_warning
  - test_turn_heater_off_writes_its_command_to_the_sgp40_alone_then_waits_out_its_maximum
  - twin: test_sgp40_heater_off_mid_read_leaves_every_twin_sibling_read_valid
- BMP3XX R2:
  - test_two_failed_reads_reset_the_chip_and_reapply_the_stored_config
  - test_a_rejected_reset_logs_one_chip_set_error_and_writes_no_config
  - test_a_put_racing_the_recovery_ends_with_the_puts_value_in_the_chip
  - test_a_chip_reset_reapplies_the_stored_configuration (b)
- ISL29125 R2:
  - test_read_loop_climbs_the_ladder_then_gives_up
  - test_a_raising_reapply_burst_logs_one_chip_set_and_no_recovery_warning
  - test_a_recovered_brownout_and_the_next_one_share_one_slot
  - twin: test_an_isl29125_reapply_mid_read_leaves_every_twin_sibling_read_valid
- General call:
  - test_reset_writes_single_byte_to_general_call_address_zero
  - test_touches_only_its_own_address_except_reset_which_touches_only_the_general_call_address
  - twin: test_the_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call (b)
- The walk now has prefixes for these files: SCD, SGP, BMP, ISL, SP, UD, UL, BG. The U13 block shows the pattern for
  pointing a row at U10's cells.

## Formal checks on the finished changes
- Both GC stages, zero memory markers (u10_checks.log, u10_checks2.log):
  - test_asy_bmp3xx_driver.py: 140/140, 14.2 s at -1, 14.6 s at 32768.
  - test_asy_config_manager.py: 244/244, 0.3 s at each stage, as both.sh timed it.
  - test_digital_twin_timer_pool.py on all six devices: 5/5 each, 13.1-17.5 s. The run shared the host with 3-4 heavy
    processes from another lane. CO2 measured 12.7-16.4 s.
- No base table: S/u24/base_times.tsv has no rows for these files here, and base_testsh_m1.log carries no per-file time
  for them.
- lint_direct: rc 0.
- mypy main pass: clean after one fix (`Lock.waiting` is missing from the stub, so the line carries an annotated
  `attr-defined` ignore). Twin pass: clean.
- Readers (test_citations, test_decision_vocabulary, test_comment_block_cap): 668 passed, after rewording one test
  comment that used decision vocabulary.
- Walk: 120 rung rows, and no U13 row is left with the default "open" text.
- `review_rows.py --check`: rc 1, from the same six unverdicted rows CO2 named. They are BR4's, none is mine.

## Deviations
The single-test plant and first runs for the BMP3XX and config-manager files ran outside `unshare -n`:
bite_plantBA/BB, bite_plantC1, and the first pass of each new test. Each ran under a minute, and neither file binds a
port. Every twin run and every formal run went through the wrapper.

## Questions for the owner
None.

## Runs
All exited. RUNS.md lines read "U35 lane CO3".
- biteR6, rc 0: the plant was still red only as a TimeoutError.
- dbgR6, rc 1: the debug copy.
- biteR6b, rc 0: the plant is red on the claim.
- u10_checks, rc 0 (339 s): the mypy finding and the vocabulary finding, both fixed.
- u10_checks2, rc 0: RR rc 1 from the six.
- u13_checks, rc 0: RR rc 1 from the six.

nothing of mine is running
