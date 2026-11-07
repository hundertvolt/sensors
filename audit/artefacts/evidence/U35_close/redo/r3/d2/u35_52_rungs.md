U35-52: conformance.md's rung rows on the final tree (lane D2, agent, 2026-11-04)

Source: `audit/b3/conformance.md` lines 17-136 at `17688315` (120 rows, built at `e83504cb`). Check: every
`file.py::name` in a row's L1, L2 and bounded/once/race-free cells looked up at `17688315` (a `def` of the name, or a
`@_register`/`@scenario` of it) by a static walk (run `r3d2_rungs`, 1 s; the script went with `ftmp`, its method is in the hand-back). 591 named tests found, 77
missing, in 36 rows; the 84 other rows have every named test present and stand as reviewed (2026-10-27). L3/L4 cells
are "queue_c" (round 1's R1 H71 row); the 3 device scripts named there exist.

## Rows dropped: the rung R1 removed (16)
| rows | rung | removed by | what holds now (test) |
|---|---|---|---|
| U10 reader `_init_*` R3, R4; U13 zero-length probe NAK R3, R4; U15 SCD30 setup fails R3, R4; U15 chip identification fails at setup R3, R4 (8) | the bus clear / controller rebuild at a setup failure (`_init_failed()`) | B2 item 8 (`8019a9ef`; code at `16047d96`) | no bus rung: the task ends, the restart retries, the budget reboots; `test_digital_twin_bus_hazard_concurrency.py::test_two_setups_failing_together_are_each_retried_by_the_restart_with_no_bus_rung` (L2) and the four drivers' setup-failure tests |
| U10 a Timer arm fails R1, R5, R6 (3) | the reader trigger trio's persist, re-arm, task end | B4 item 18; B2 item 6 (the uptime re-arm) | the pre-audit catch per arm: `test_asy_bmp3xx_driver.py::test_start_timer_degrades_gracefully_when_the_trigger_timer_cannot_be_armed` and its SCD30/SGP40/ISL29125 twins (L1); `test_digital_twin_timer_pool.py::test_the_tick_timers_degrade_in_place_and_rearm_once_the_pool_frees` (L2) |
| U16 chip stops answering mid-operation R1, R2, R5, R6 (4) | the lost-FRAM chain (probe, E54, watch task end) | B3 items 1-2 | a silent chip's writes fail and the first write after it answers lands, no task end: `test_digital_twin_fram.py::test_a_booted_device_whose_fram_goes_silent_fails_its_writes_and_resumes_when_the_chip_answers` (L2) |
| U15 ISL29125 INT not delivering R2 (1) | the INT re-arm (ISL-2) | B4 item 19 | W32 only (pre-audit): `test_asy_isl29125_driver.py::test_five_periodic_led_decisions_in_a_row_report_a_possibly_dead_interrupt` (L1), `test_digital_twin_isl29125_autorange.py::test_a_dead_interrupt_line_eventually_warns_rather_than_staying_invisible` (L2) |

## Rows that stay, cells re-pointed to today's tests (20)
| row | missing name | today's test |
|---|---|---|
| R6 in U10 cycle fails, U10 `_init_*`, U10 any task ends, U13 zero-length, U15 SCD30 read, U15 SCD30 setup, U15 chip ID, U16 chip ID, U17 construction, U18 WLAN (10 rows) | L2 `test_digital_twin_fram.py::test_a_booted_device_whose_fram_goes_silent_restarts_its_task_and_recovers_or_arms_the_reset`; race-free `test_asy_system_service.py::test_a_command_accepted_while_the_escalation_logs_keeps_its_own_reset` | L2: `_digital_twin_ci_suite.py`'s Run 3 (`_run_3_sustained_bus_fault_matrix`: every instance faulted, FRAM silent, the restart budget resets the device) and Run 4 (ResetReason the escalation code); tw. `an_escalation_entry_that_never_finishes_leaves_code_20_to_the_watchdog`; race-free: `test_asy_system_service.py::test_a_command_during_the_escalations_entry_write_is_refused_and_the_escalation_resets` |
| U10 `_init_*` R2 | `test_asy_isl29125_driver.py::test_init_returns_false_and_logs_an_init_error_and_reinitialises_the_controller` | `test_asy_isl29125_driver.py::test_init_returns_false_and_logs_an_init_error_and_leaves_the_bus_to_the_restart` (B2 item 8) |
| U10 and U16 FRAM `verify_present` (2) | `test_asy_fram_manager.py::test_a_probe_that_cannot_take_the_lock_keeps_the_blank_verdict`; twin `..._stays_blank_and_declares_no_loss` | the blank verdict's probe is gone (B3 row 2); `verify_present()` is a library entry with no product caller: `test_asy_fram_driver.py::test_verify_present_bounded_wait_returns_false_instead_of_hanging_when_lock_already_held` (L1), `test_digital_twin_fram.py::test_a_blank_read_beside_a_held_session_stays_blank_makes_no_rdid_and_logs_nothing` (L2) |
| U16 chip identification fails at setup R1, R5 (2) | L2 the silent-FRAM twin test | Run 3 above (FRAM silent from boot: identification fails, the watch ends, the budget reboots); W29's retries asserted at L1 only (`test_asy_fram_driver.py::test_a_chip_that_never_identifies_is_asked_id_attempts_times_before_setup_raises`); L1 escalation sc. `a_declared_dead_fram_chip_escalates_to_a_reboot` |
| U15 SCD30 goes silent | `test_asy_scd30_driver.py::test_frc_readiness_publishes_not_measuring_after_two_intervals_without_data` | `test_asy_scd30_driver.py::test_two_intervals_without_data_publish_not_measuring_with_no_values_until_the_next_measurement`; L2 unchanged |
| U15 SGP40 skips a cycle for missing compensation | `test_asy_sgp40_driver.py::test_a_stale_compensation_sample_skips_the_cycle` | the stale half went (B4 item 11); `test_read_sgp_without_compensation_data_yet_logs_nothing` remains (L1), L2 unchanged |
| U15 BMP3XX read fails R2 | `test_asy_bmp3xx_driver.py::test_a_chip_reset_reapplies_the_stored_configuration` | `test_asy_bmp3xx_driver.py::test_two_failed_reads_reset_the_chip_and_reapply_the_stored_config` (already in the cell) |
| U18 captive DNS loop error | `test_run_bind_failure_logs_init_once_and_backs_off`; `test_a_heap_failure_while_parsing_is_persisted_not_dropped_as_malformed` | `test_asy_captive_dns.py::test_run_bind_failure_logs_one_warning_and_backs_off`; the parse heap failure now drops the query as malformed (B5): `::test_a_heap_failure_while_parsing_the_query_drops_it_as_malformed`, `::test_a_heap_failure_at_the_subnet_check_is_persisted` |
| U15 SCD30 data-ready interrupt edge missed R2 | L2 `test_digital_twin_scd30.py::test_a_stuck_high_rdy_line_warns_once_after_five_empty_reads_and_new_data_ends_it` (removed with W73, `b4341646`) | L1 stays: `test_asy_scd30_driver.py::test_scd_init_irq_sets_irq_trigger_after_enough_consecutive_stuck_ticks`; **L2: none** (gap G1 below) |

## Totals
- 120 rows: 16 dropped, 104 stay; of these 84 unchanged and 20 re-pointed, 19 of them to an existing test.
- Gap G1 (A8, OR113.a (2)): the SCD30's 500 ms fallback trigger (a missed RDY edge) has no L2 test since W73's
  twin test went (`b4341646`); `git grep` over the twin tier finds no SCD30 stuck-RDY or fallback case. Proposed:
  the fallback half of the removed twin test, without W73: the twin SCD30's rising edge muted with the pin held
  high, one read within `_trigger_half_ticks` ticks, no entry logged.
