CO4 hand-back, written by the lane (2026-10-27 11:39 UTC)

Lane CO4, branch audit/u35-conf2, worktree S/wt-u35conf2. I started on CO3's head 04cdd831. Nothing is pushed and
nothing is uncommitted (node_modules was untracked before I started). Logs are in S/u35/laneB/co4/. The brief ran to
its end with no seam, per the lead's 2026-10-27 update.

## Commits
1. a0ea910a: U13's held-line rows get their twin tests.
   - New file tests/test_digital_twin_held_i2c_line.py.
   - Two Part N rows in SPECIFICATION.md.
   - The new file is added to Part E's per-device table and to tests_scripts/test_device_tomls.py's family list.
2. 3c6829f2: U10's setup-reset cells and U13's SPI overrun "once" cell.
   - New file tests/test_digital_twin_setup_resets.py, with its two Part N rows and its family-list entry.
   - One test added to tests/test_digital_twin_bus_hazard_concurrency.py.
   - One test added to tests/test_asy_fram_manager.py.
3. 405cea2b: U10's last two L2 cells (tests/test_digital_twin_scd30.py, tests/test_digital_twin_fram.py).
4. 7303e4d0: U15's 33 rows. Three new tests, in test_digital_twin_scd30.py, test_digital_twin_sgp40.py and
   test_bus_hazard_multi_device.py.
5. a5e0707c: U16's 19 rows. Two new tests in test_digital_twin_fram.py.
6. df5bfab1: U17's 6 rows, celled on today's code. Audit text only.
7. 71729142: U18's 17 rows. Audit text only.

Every commit also re-ran audit/b3/conformance_walk.py into conformance.md, and queue_c.md got its stamp.

## Cells by table, before → after
- U10 (23 rows):
  - Before: `_init_*()` R2 had three L2 cells open (SCD30, BMP3XX, ISL29125) and two race-free cells open (BMP3XX,
    ISL29125). The deferred flush R1 L2 cell was open.
  - After: none open.
- U16's verify_present (probe) row: its L2 cell was open; now named.
- U13 (21 rows):
  - Before: L2 open for power-up R3, SCL R3 and SCL R4. SCL R2 was only a pointer. SPI 32+ R1 "once" was open. UART
    R1/R4 were cross-references.
  - After: none open. SCL R2 cites U15's R2 rows and the held-SCL twin test. UART R1 points at U17's frame row.
- U15 (33 rows): all 33 were the record's "open"; all 33 are now celled, none left open.
- U16 (19 rows besides the probe row): all 19 were "open"; all are now celled, and two L2 cells stay open (below).
- U17 (6 rows): all 6 were "open"; all are now celled on today's code. The two PieceBuffer sites are marked pending owner.
- U18 (17 rows): all 17 were "open"; all are now celled, and three L2 cells stay open (below).

Totals: all 120 rung rows carry reviewed cells, and no row keeps the default text. Five cells are open, each with its
reason below.

## Defects
No firmware defect: every rung examined held its property.

One finding is put to the owner as a question (below): a sustained FRAM read fault fills the 10-slot ring two slots per
failed read.

## New tests and their red-first evidence
Each new test passed at once on the base, so each is a guard. Each was bitten by a fault planted in a scratch copy of
the src module (the plant directory goes first on MICROPYPATH), and each planted directory was deleted afterwards.
Nothing planted is committed. review.md has no rows for these tests: the render still waits on BR4's six verdicts.

tests/test_digital_twin_held_i2c_line.py (per device; biteH.log):
1. test_a_bus_held_at_power_up_is_clocked_free_before_construction_and_reported_once.
   - P1 (the boot clear skipped): red, "the boot clear returned 0, expected 1".
   - P2 (the boot status never taken): red, "the boot status was never taken".
2. test_a_scl_held_at_power_up_pulses_nothing_and_is_reported_as_held.
   - P1: red, "returned 0, expected 4".
   - P3 (no SCL check before the pulses): red, "returned 5, expected 4".
   - P2: red, "2 W BUS_RECOVERY reports".
3. test_a_slave_holding_scl_at_runtime_gets_a_clear_that_pulses_nothing_then_one_controller_rebuild.
   - P4 (the runtime clear neither waits for SCL nor checks SDA): red, "bus clears returned [5]".
   - While the hold is on, the test's wrapper makes the twin's transfers end ETIMEDOUT, as rp2's machine_i2c.c:150-152
     does. The fault is injected in the test only; digital_twin/ is unchanged.

tests/test_digital_twin_setup_resets.py (per device; biteR.log):
4. test_every_chip_is_reset_once_by_its_setup_after_its_identity_check.
   - BMP3XX setup without its reset: red, "got 0 reset write(s)".
   - ISL29125 reset before its ID check: red, "was reset before any read identified it".
   - SCD30 reset twice: red, "got 2 reset write(s)".

tests/test_digital_twin_bus_hazard_concurrency.py (biteB.log):
5. test_a_bmp3xx_setup_reset_mid_read_leaves_every_twin_sibling_read_valid.
   - Wrong reset opcode: red, "the soft reset never reached the BMP3XX".

tests/test_asy_fram_manager.py (biteF.log):
6. test_one_rx_overrun_logs_the_fault_and_the_fall_through_once_each_and_the_repair_nothing.
   - An extra warning on block 0's repair: red, "the count rose by 3".

tests/test_digital_twin_fram.py:
7. test_a_blank_read_whose_probe_meets_a_held_session_stays_blank_and_declares_no_loss.
   - An unbounded lock wait in verify_present(): red, no LOCK_TIMEOUT (biteP.log).
8. test_two_valid_but_differing_copies_fail_each_read_with_one_slot_and_the_next_write_heals_them.
   - The read picks a copy: red, "read [True, True]" (biteM.log).
9. test_a_paused_twin_fram_refuses_every_chunk_operation_with_one_slot_and_resumes_untouched.
   - The pause ignored: red, "answered (True, True, True)" (biteM.log).

tests/test_digital_twin_scd30.py:
10. test_a_failed_deferred_flush_is_healed_by_the_next_accepted_put.
    - The failed value dropped from the cache: red, "the healed file holds {'FRCNoise': 20.0, ...}" (biteC.log).
    - It uses file-held FRC fields only. TempOffset and the other chip settings live in the SCD30's NVM, not in the file.
11. test_a_silent_scd30_publishes_not_measuring_and_runs_no_cycle_streak_or_entry.
    - The tick counting with the pin ignored: red, "a low data-ready line re-triggered a read" (biteS.log).

tests/test_digital_twin_sgp40.py:
12. test_a_cycle_without_compensation_sends_no_measurement_and_steps_no_streak_or_entry.
    - The streak stepped without compensation: red, "streak 5, 8 entr(ies)" (biteG.log).

tests/test_bus_hazard_multi_device.py:
13. test_an_isl29125_interrupt_rearm_mid_read_leaves_every_sibling_read_valid.
    - The re-arm without its thresholds: red, "the thresholds were not re-armed" at 6/6 offsets (biteI.log).

Two existing tests were cited with a new reading, each re-read on the tree:
- The ISL29125 twin reapply test's rung runs setup(), the 0x46 reset included, at every offset. It is now the
  race-free cell for ISL29125's setup reset.
- The SCD30 stuck-high RDY twin test is the L2 cell for the "data-ready edge missed" row.

Every other cited test was looked up in review.md with CO3's verdict.py: all are "biting", or "fixed" for three tests
that had been strengthened.

## Cells still open, with their reasons
1. U16 "latch does not clear after WRDI" R1, L2: the twin FRAM chip has drop_next_wren but no dropped-WRDI knob.
   Home: test_digital_twin_fram.py, once digital_twin/_fram_chip.py has the knob (a twin change; not made).
2. U16 "write verification mismatch" R1, L2: the twin chip stores what it is sent, so no readback disagrees. This also
   needs a twin knob.
3. U18 "hotspot timer cannot be armed" R1, L2: no twin test empties the alarm pool while the hotspot shutoff timer
   arms. Home: test_digital_twin_timer_pool.py.
4. U18 "a UDP socket cannot be set up, bound or connected", R1 and R2, L2: no twin test fails a product socket's setup
   and watches the next call rebuild it. Home: test_digital_twin_ntp.py.

## Question for the owner
**A sustained FRAM read fault takes two log slots per failed read.** One RX-overrun read logs two entries:
- E UNEXPECTED, from `_read_chunk`'s "General read error";
- W FRAM_BLOCK_INVALID, "Read fault in block 0, reading block 1", from the dual-copy layer. A.U16.06 introduced this
  warning to tell a fault from bad content.

Test 6 pins that one event logs these two entries, once each. Under a sustained fault the two codes alternate (E, W, E,
W). The newest-entry rule only folds a repeat of the last code, so it never applies here. Each repeated failed read
therefore adds two slots to the manager's 10-slot ring, where "a repeat raises only the count" would keep one.

The options:
- (a) Keep it as designed. The two entries are two facts: the fault, and the fall-through to the other copy.
- (b) Log only the W for a fault.
- (c) Log only the E for a fault.

(b) and (c) change the codes the device reports through /status.

Recommendation: (a). This ring is RAM-only (owner G5/R32), so it costs no wear. A fault that persists ends at the
chip-loss probe, which logs its own entry once. Nothing was changed on this point.

## Formal checks on the finished changes
Both GC stages, zero memory markers, through the wrapper (checks1-8):

| test file | result | -1 | 32768 |
|---|---|---|---|
| test_digital_twin_held_i2c_line.py, 6 devices | 3/3 each | 4.3-5.1 s (dev 10.2 s) | 4.5-5.4 s (dev 11.2 s) |
| test_digital_twin_setup_resets.py, 6 devices | 1/1 each | 1.0-2.2 s | 1.0-2.2 s |
| test_asy_fram_manager.py | all pass | 1.6 s | 3.0 s |
| test_digital_twin_bus_hazard_concurrency.py | all pass | 126.6 s | 135.7 s |
| test_digital_twin_fram.py | all pass | 2.8 s | 3.4 s |
| test_digital_twin_scd30.py | all pass | 0.6 s | 0.8 s |
| test_digital_twin_sgp40.py | all pass | 0.4 s | 0.4 s |
| test_bus_hazard_multi_device.py | all pass | 3.7 s | 4.5 s |

- There is no base row for any of these files: S/u24/base_times.tsv has none, and base_testsh_m1.log carries no
  per-file time for them.
- Two files changed after their formal pair, in comments only, and each was re-checked by the static checks afterwards:
  - the held-line file: its docstring, and the type-ignores mypy found unused;
  - the setup-resets file: a noqa ruff found unused.
- lint_direct: rc 0.
- mypy: twin pass rc 0, main pass rc 0, host pass rc 0 (on test_device_tomls.py).
- Readers: test_citations, test_decision_vocabulary, test_comment_block_cap, test_tunables_register and
  test_device_tomls gave 725 passed. With the audit-only commits (the first three readers): 670 passed.
- `review_rows.py --check`: rc 1, from the same six unverdicted rows CO2 and CO3 named. They are BR4's.

## Runs
All exited, every one through S/u35/laneB/co4/run.sh (namespace, nice 19, RUNS.md lines "U35 lane CO4").
- held1-held5: the new file being fixed. The failures were test-side and were root-caused:
  - SCD30 init runs in its read task;
  - the boot's driven sleeps must be driven;
  - the reader list was read before construction;
  - recoveries steps before the rung runs.
- resets1-2: resets1 failed because MicroPython has no starred item in a tuple display.
- spi1-2, probe1-2, flush1-3 and silent1-4: each new test iterated to its final form.
- The bites: biteH, biteR, biteF, biteB, biteP, biteC, biteS, biteI, biteG, biteM.
- checks1-10 and static1: the formal checks above.

Deviations: none. Every run went through the wrapper.

nothing of mine is running
