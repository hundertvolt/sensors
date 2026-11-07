# R3 lane M: the plant run (agent, 2026-11-04)

Run `r3m_plant` (rc 0, 2,149 s), after `r3m_plant_check` (snapshot `/dev/shm/r3m_snap` of `S/wt-r3` at `17688315`,
every anchor matched its stated count, the driver's selftest passed). Driver: `audit/sweeps/plant.py` copied unchanged
but for the interpreter (`S/tc-int`'s build-standard, the common rule) and its stop-file path; set: `m/data/plant_set_r3.py`, built
from `audit/sweeps/plant_set.py`; results `m/data/plant_results.jsonl`. Every target file ran green unplanted first (32 baselines, both
GC stages for MicroPython files); the snapshot was unchanged at the end; every copy was removed.

## Scope (decision, agent, 2026-11-04)

Against `audit/b3/faults.md` (its record ends at `2e826c28`, so a site "changed" means changed since then; R1 and R2
are 72 of the 96 commits since):
- **Re-run as is (52):** every plant whose anchor still matches and whose enclosing function changed since `2e826c28`
  (36), or one of whose catching tests changed or went (K.04-flip/drop, K.24, `named.write_counters`,
  `asy_uart_link_driver.quiet`), plus the record's check-style triggers whose subject changed: the five catalog plants
  (the catalog and codes changed; R1 also removed the catalog's 12 self-bite tests, `95e4fbde`), `named.pair_scan`,
  `named.result_words`, `named.api_contract` (its test changed), `named.layering` (`js/render.js` changed) and the
  twin memory gate's control and two plants (`scripts/_digital_twin_ci_suite.py` changed).
- **Adapted (7):** anchors that no longer match, on the mechanism's new home: the ramp's clamp (`6c00e98e`), the boot
  entry's `reset()` (report_if_fatal's successor), the UART driver's two `_report()` allocation lines (`a8d0028a`),
  NTP's 60 s unsynced retry (the backoff cap's successor, `25a14b4f`), the ISL29125 hold and the LED request deadline
  (both now inside a compound condition).
- **New (7):** R1's own complex-measurement sites: the UART ring's unchain before stop (`1b4caa17`), the I2C clear's nine
  pulses, its early stop and its stretch-wait yield (`dddb3902`), the command gate's and the escalation's reset
  decision (`2970ff9e`), NTP's no-overlap tick (`60a88be1`).
- **Check-style triggers (6):** checks whose self-bite test `95e4fbde` removed and whose subject (src/ or the device
  scripts) R1 changed: FRAM chunk CRC sites, FRAM chunk owner sites, src sleep forms, the F.3 timing budget, device
  script FRAM regions, device script watchdog sleeps. The other bite-removed convention checks (shell, website tokens,
  lint scopes and the like) are not triggered: the owner's "the sensitivity proof is done once" (2026-09-25) and
  straightforward-test scope (2026-10-23).
- **Carried over, not re-run (53 of the record's 115 plants):** anchor matching, function unchanged, every catching
  test unchanged: K.01, K.bins, K.bins-total, K.02-06-08, K.12-down, K.12-cap, K.18, K.23, K.25 (three), K.26, K.28,
  K.28-seq, K.20, K.20-log, K.42, K.42-log, K.43, K.53, `named.mock_routes`, the gate.unit and gate.flash triples (their
  subjects did not change), and nine seeds (decode_yield, gate_step, recovery_window, last_feed, alarm_enomem, stream,
  check_inc_reset, conn_failures, bins_advance).
- **Site removed by R1, nothing to plant (3 plants):** K.28-merge flip and drop (the log restore replaces the count, it
  no longer merges, B3) and `asy_notification_service.sample_age` (no published cycle sample, `15b2175b`).

## Result: 72 planted, 69 red, the twin gate's control green as required, 2 survivors

| plant | why (seed) | site | result | catching tests (first three) |
|---|---|---|---|---|
| K.04-flip | - | `src/asy_system_service.py:274: return budget + _TASK_FAIL_INCREMENT if budget <= _TASK_FAIL_MAX else` | RED (-1,32768) | test_a_command_during_an_entry_write_that_never_ends_leaves_the_escalations_code_to_the_watchdog; test_a_command_during_the_escalations_entry_write_is_refused_a |
| K.04-drop | - | `src/asy_system_service.py:274: return budget + _TASK_FAIL_INCREMENT if budget <= _TASK_FAIL_MAX else` | RED (-1,32768) | - |
| K.04-trigger-flip | - | `src/asy_system_service.py:535: if task_errors > _TASK_FAIL_MAX and not self._reset_armed:` | RED (-1,32768) | test_a_pass_with_every_task_dead_escalates_at_the_first_end_past_the_budget |
| K.04-trigger-drop | - | `src/asy_system_service.py:535: if task_errors > _TASK_FAIL_MAX and not self._reset_armed:` | RED (-1,32768) | test_a_command_during_an_entry_write_that_never_ends_leaves_the_escalations_code_to_the_watchdog; test_a_command_during_the_escalations_entry_write_is_refused_a |
| K.05-flip | - | `src/asy_webserver_service.py:840: if current > self._max_connections:` | RED (-1,32768) | test_a_connection_whose_trace_waits_closes_at_one_per_call_timeout_and_keeps_its_entry; test_client_faults_print_nothing_at_debug_level_zero; test_dropped_conne |
| K.05-drop | - | `src/asy_webserver_service.py:840: if current > self._max_connections:` | RED (-1,32768) | test_a_connection_whose_trace_waits_closes_at_one_per_call_timeout_and_keeps_its_entry; test_client_faults_print_nothing_at_debug_level_zero; test_dropped_conne |
| K.14-flip | - | `src/asy_scd30_driver.py:439: if self._irq_pin.value() == 1 and self._scd_timer_triggers < self._trig` | RED (-1,32768) | test_the_stuck_pin_count_saturates_at_the_threshold |
| K.14-drop | - | `src/asy_scd30_driver.py:439: if self._irq_pin.value() == 1 and self._scd_timer_triggers < self._trig` | RED (-1,32768) | test_the_stuck_pin_count_saturates_at_the_threshold |
| K.24-flip | - | `src/asy_uart_comm.py:791: if self._blind_resyncs < _DIAG_RESYNC_STREAK:  # saturates: only the thres` | RED (-1,32768) | test_the_blind_resync_streak_saturates |
| K.24-drop | - | `src/asy_uart_comm.py:791: if self._blind_resyncs < _DIAG_RESYNC_STREAK:  # saturates: only the thres` | RED (-1,32768) | test_the_blind_resync_streak_saturates |
| K.27-transfers-flip | - | `src/asy_uart_link_driver.py:135: if self._transfers < COUNTER_CAP:` | RED (-1,32768) | test_the_transfer_count_stops_at_the_counter_cap |
| K.27-transfers-drop | - | `src/asy_uart_link_driver.py:135: if self._transfers < COUNTER_CAP:` | RED (-1,32768) | test_the_transfer_count_stops_at_the_counter_cap |
| K.27-failures-flip | - | `src/asy_uart_link_driver.py:137: elif self._failures < COUNTER_CAP:` | RED (-1,32768) | test_the_failure_count_stops_at_the_counter_cap |
| K.27-failures-drop | - | `src/asy_uart_link_driver.py:137: elif self._failures < COUNTER_CAP:` | RED (-1,32768) | test_the_failure_count_stops_at_the_counter_cap |
| K.29-gamma-flip | - | `src/voc_algorithm.py:428: if self.params.m_mean_variance_estimator_uptime_gamma < uptime_limit:` | RED (-1,32768) | test_both_estimator_uptimes_stop_at_the_uptime_limit |
| K.29-gamma-drop | - | `src/voc_algorithm.py:428: if self.params.m_mean_variance_estimator_uptime_gamma < uptime_limit:` | RED (-1,32768) | test_both_estimator_uptimes_stop_at_the_uptime_limit |
| K.29-gating-flip | - | `src/voc_algorithm.py:433: if self.params.m_mean_variance_estimator_uptime_gating < uptime_limit:` | RED (-1,32768) | test_both_estimator_uptimes_stop_at_the_uptime_limit |
| K.29-gating-drop | - | `src/voc_algorithm.py:433: if self.params.m_mean_variance_estimator_uptime_gating < uptime_limit:` | RED (-1,32768) | test_both_estimator_uptimes_stop_at_the_uptime_limit |
| named.clamp_byte-overlay | - | `src/asy_neopixel_driver.py:72: bri = _clamp_byte(self._overlay_bri)` | RED (-1,32768) | test_overlay_bri_out_of_range_clamped_not_raised |
| named.fram_alloc | - | `src/asy_fram_manager.py:377: async def _write_chunk(self, buf: bytearray, addr: int) -> bool:` | GREEN | - |
| named.webserver_leak | - | `src/asy_webserver_service.py:834: async def _serve(self, reader: "_StreamLike", writer: "_StreamLike` | RED (-1,32768) | test_f9_soak_100_plus_start_wedge_reclaim_cycles_hold_counter_and_memory_flat |
| named.uart_latency | - | `src/asy_uart_comm.py:1129: async def uart_set_into(self, set_id: int, buf: "Readable \| None", size:` | RED (-1,32768) | test_a_clean_transaction_completes_within_its_virtual_time_bound_crc16; test_a_clean_transaction_completes_within_its_virtual_time_bound_nocrc |
| named.write_counters | - | `src/asy_config_manager.py:419: f.write(text)` | RED (-1,32768) | test_write_counting_open_counts_reads_apart_from_writes; test_a_boot_over_a_valid_file_reads_it_and_writes_nothing; test_a_boot_over_an_absent_file_writes_it_on |
| named.catalog-literal | - | `src/asy_notification_service.py:209: await self.pr.err_s(notif.name, "Value read failed:", e, errno=` | RED (host) | test_every_code_argument_is_built_from_catalog_names |
| named.catalog-band | - | `src/asy_notification_service.py:EOF + '_ERR_PLANTED = const(126)'` | RED (host) | test_every_code_constant_equals_its_catalog_entry_and_owner |
| named.catalog-dupname | - | `src/asy_scd30_driver.py:EOF + '_ERR_SOURCE = const(7)'` | RED (host) | test_every_code_constant_equals_its_catalog_entry_and_owner |
| named.catalog-testcopy | - | `tests/test_asy_uart_comm.py:EOF + '_ERR_NO_ACK = 20'` | RED (host) | test_no_test_tier_keeps_its_own_copy_of_a_code |
| named.catalog-persisted | - | `tests/test_asy_notification_service.py:EOF + 'def _planted_assert(c: object) -> None:\n    assert pe` | RED (host) | test_no_test_tier_keeps_its_own_copy_of_a_code |
| named.pair_scan | - | `src/asy_notification_service.py:209: await self.pr.err_s(notif.name, "Value read failed:", e, errno=` | RED (host) | test_no_occurrence_is_persisted_as_both_a_fault_and_a_warning |
| named.result_words | - | `src/asy_notification_service.py:EOF + '_PLANTED_WORD = "Valid"'` | RED (host) | test_src_spells_no_result_word_outside_the_config_manager |
| named.api_contract | - | `js/api-contract.js:7: export const VALID = "Valid"; // src/asy_config_manager.py's VALID` | RED (host) | - |
| named.layering | - | `js/render.js:EOF + 'export function plantedBuild() { return document.createElement("div"); }'` | RED (host) | test_the_real_tree_keeps_the_layering |
| boot.interrupt_record | - | `buildgen/codegen.py:860: "    write_reset_record(RR_INTERRUPTED)\n"` | RED (-1,32768) | test_a_console_interrupt_is_recorded_before_it_propagates |
| boot.interrupt_raise | - | `buildgen/codegen.py:861: "    raise\n"` | RED (-1,32768) | test_a_console_interrupt_is_recorded_before_it_propagates; test_an_interrupt_the_stub_did_not_plant_ends_the_run |
| boot.loop_end | - | `buildgen/codegen.py:866: "    record_loop_end()\n"` | RED (-1,32768) | test_any_other_exception_ending_the_loop_is_recorded_then_resets_the_chip_printing_nothing |
| boot.finally | - | `buildgen/codegen.py:869: "    asyncio.new_event_loop()\n"` | RED (-1,32768) | test_a_console_interrupt_is_recorded_before_it_propagates; test_each_entry_arms_the_watchdog_and_sets_the_threshold_before_main |
| gate.twin-control | - | `-` | GREEN | - |
| gate.twin-caught | - | `src/asy_print_log.py:EOF + 'print("planted: memory allocation failed, allocating 64 bytes")'` | RED (-1,32768) | - |
| gate.twin-class | - | `src/asy_print_log.py:EOF + 'print("MemoryError: ")'` | RED (-1,32768) | - |
| asy_fram_manager.erase_yield | never-block: the chip erase's per-unit yield (timing) | `src/asy_fram_manager.py:751: await asyncio.sleep(0)` | RED (-1,32768) | test_erase_chip_lets_another_task_run_between_every_two_units |
| asy_fram_manager.read_yield | never-block: the read loop's per-slice yield (timing) | `src/asy_fram_manager.py:300: await asyncio.sleep(0)` | RED (-1,32768) | test_a_read_lets_another_task_run_after_every_slice_it_compares |
| asy_fram_manager.status_yield | never-block: the yield after the status-byte pair (timing) | `src/asy_fram_manager.py:152: await asyncio.sleep(0)  # after the status-byte pair; the bus lock is h` | RED (-1,32768) | test_every_block_operation_yields_even_when_it_returns_early |
| asy_uart_driver.idle_poll | F.5.9: an open-ended wait polls at the idle rate (timing) | `src/asy_uart_driver.py:689: wait_ms = self.poll_wait_ms if timeout_ms > 0 else self.poll_idle_ms` | RED (-1,32768) | test_a_deadlineless_wait_polls_at_the_idle_rate_and_a_bounded_one_does_not; test_an_idle_wait_beyond_the_ticks_range_returns_false |
| asy_uart_driver.drain_yield | F.5.8: never block the loop, the drain's own yield (timing) | `src/asy_uart_driver.py:257: await asyncio.sleep_ms(0)  # this loop never reaches ready()'s own yield` | RED (-1,32768) | test_a_delimited_frame_longer_than_the_yield_interval_still_yields; test_a_run_of_delimiters_lets_another_task_run |
| asy_uart_driver.rx_clamp | F.5.8: each read clamped to what has arrived (timing) | `src/asy_uart_driver.py:211: return min(max(want, 0), level)` | RED (-1,32768) | test_a_delimited_frame_read_across_rounds_reads_the_ring_only; test_a_lap_during_the_copy_fails_every_read_path_and_no_phantom_byte_reaches_the_next_read; test_ |
| asy_uart_link_driver.quiet | the peer's own timeout passes first (timing, multi-layer) | `src/asy_uart_link_driver.py:206: await asyncio.sleep_ms(self._quiet_ms)  # the peer answered: its ow` | RED (-1,32768) | test_a_hazard_run_reports_every_verdict_then_returns_to_the_echo_crc16; test_a_hazard_run_reports_every_verdict_then_returns_to_the_echo_nocrc |
| asy_system_service.supervisor_memerr | memory: the supervisor's caught allocation failure (memory exhaustion) | `src/asy_system_service.py:380: except MemoryError as e:` | RED (-1,32768) | test_every_refusal_answers_false_and_changes_nothing |
| asy_print_log.ring_alloc | memory: the history ring's allocation failure degrades to a 0-length ring | `src/asy_print_log.py:145: except MemoryError as e:  # a 0-length ring: get_log() then reports no slo` | RED (-1,32768) | test_a_failed_history_allocation_prints_its_text_and_keeps_a_zero_ring; test_a_failed_history_allocation_prints_nothing_with_logging_off |
| asy_captive_dns.backoff_cap | accumulating: the receive-failure backoff stops at its cap | `src/asy_captive_dns.py:117: recv_fail_backoff_ms * _RECV_FAIL_BACKOFF_MULTIPLIER, _RECV_FAIL_BACKOFF` | RED (-1,32768) | test_run_recv_backoff_caps_at_the_ceiling; test_run_recv_backoff_is_asked_in_milliseconds |
| asy_sgp40_driver.backup_cadence | long-running: the FRAM backup cadence (accumulation) | `src/asy_sgp40_driver.py:269: if cfg_values[0] > 0 and self._backup_counter >= (60 * cfg_values[0]):` | RED (-1,32768) | test_a_backup_period_of_zero_never_triggers_a_backup; test_run_backup_resyncs_with_timestamp_once_ntp_available_again; test_run_backup_updates_verify_when_backu |
| asy_sgp40_driver.backup_counter_max | long-running: the backup counter's own bound (accumulation) | `src/asy_sgp40_driver.py:274: if self._backup_counter >= _BACKUP_COUNTER_MAX:` | RED (-1,32768) | test_check_storage_backup_counter_wraps_before_it_could_overflow |
| asy_i2c_driver.recoveries | accumulating: the recovery sequence wraps at COUNTER_CAP | `src/asy_i2c_driver.py:258: self.recoveries = self.recoveries + 1 if self.recoveries < COUNTER_CAP el` | RED (-1,32768) | test_each_clear_and_recover_steps_recoveries_once_and_the_sequence_wraps |
| r3.clamp_byte-ramp | the ramp's own clamp (the signal clamp's new home, 6c00e98e) | `src/asy_neopixel_driver.py:92: r_s = _clamp_byte(self._rgbt[0]) * steps_inv  # red` | RED (-1,32768) | test_led_signal_out_of_range_rgb_clamped_not_raised; test_request_signal_out_of_range_rgb_clamped_not_raised |
| r3.boot.reset | the loop end resets at once (report_if_fatal's successor) | `buildgen/codegen.py:867: "    reset()\n"` | RED (-1,32768) | test_any_other_exception_ending_the_loop_is_recorded_then_resets_the_chip_printing_nothing |
| r3.uart_driver.read_alloc_report | memory: a caught allocation failure reports its own text (log gate) | `src/asy_uart_driver.py:511: self._report("read buffer allocation failed:", e)` | RED (-1,32768) | test_an_allocating_read_whose_buffer_fails_prints_its_own_text |
| r3.uart_driver.line_alloc_report | memory: a caught allocation failure reports its own text (log gate) | `src/asy_uart_driver.py:632: self._report("line buffer allocation failed:", e)` | RED (-1,32768) | test_an_allocating_read_whose_buffer_fails_prints_its_own_text |
| r3.ntp.unsynced_retry | accumulating/timing: a failed unsynced attempt waits 60 s (the backoff cap's successor, 25a14b4f) | `src/asy_ntp_client.py:408: self._retry_wait_s = _NTP_RETRY_UNSYNCED_S` | RED (-1,32768) | test_a_check_tick_during_a_failing_attempt_starts_no_other_before_the_retry_wait; test_a_responder_back_mid_backoff_syncs_at_the_next_attempt; test_a_short_repl |
| r3.isl.cal_hold | timing bound: the measured ratio's hold expires at its exact tick | `src/asy_isl29125_driver.py:539: if self._cal_meas is None or time.ticks_diff(time.ticks_ms(), self._` | RED (-1,32768) | test_a_published_candidate_still_reads_one_tick_before_its_hold_ends_and_is_gone_at_it |
| r3.neopixel.signal_deadline | timing bound: an internal request waits at most _SIGNAL_WAIT_MS | `src/asy_neopixel_driver.py:158: while self._start_signal_event.is_set() and time.ticks_diff(deadline` | RED (-1,32768) | test_request_signal_queues_at_its_deadline_when_the_signal_task_never_runs |
| r3.uart_driver.rx_stop_unchain | external dependency: the ring stops only unchained (1b4caa17) | `src/asy_uart_driver.py:362: data.ctrl = (data.ctrl & ~_CTRL_CHAIN_TO_MASK) \| (data.channel << _CTRL` | RED (-1,32768) | test_a_caught_allocation_failure_in_a_poll_or_teardown_prints_its_own_text; test_a_re_init_masks_first_and_fails_the_next_read; test_a_reinit_whose_teardown_fai |
| r3.i2c.clear_pulses | multi-layer recovery: nine pulses free a slave holding SDA mid-byte (dddb3902) | `src/asy_i2c_driver.py:45: for _ in range(_CLEAR_PULSES):` | RED (-1,32768) | test_a_clear_whose_scl_is_held_at_the_stop_lets_sda_go_and_reports_it; test_clear_and_recover_end_a_held_scl_at_the_bus_timeout_on_the_fake_clock; test_clear_of |
| r3.i2c.clear_break | multi-layer recovery: the pulses stop once SDA is released | `src/asy_i2c_driver.py:53: break` | RED (-1,32768) | test_clear_stops_once_sda_is_released_and_reports_it; test_recover_clears_then_re_constructs_with_the_stored_frequency_and_timeout; test_the_boot_clear_proceeds |
| r3.i2c.stretch_yield | never-block: a stretching slave never holds the loop (F.3) | `src/asy_i2c_driver.py:75: await asyncio.sleep_ms(1)` | GREEN | - |
| r3.ss.gate_decided | multi-layer race: the gate refuses once a reset is decided (2970ff9e) | `src/asy_system_service.py:368: if self._reset_decided:` | RED (-1,32768) | test_a_command_during_an_entry_write_that_never_ends_leaves_the_escalations_code_to_the_watchdog; test_a_command_during_the_escalations_entry_write_is_refused_a |
| r3.ss.escalation_decides | multi-layer race: the escalation decides before its entry write | `src/asy_system_service.py:545: self._reset_decided = True` | RED (-1,32768) | test_a_command_during_an_entry_write_that_never_ends_leaves_the_escalations_code_to_the_watchdog; test_a_command_during_the_escalations_entry_write_is_refused_a |
| r3.ntp.no_overlap | timing: a check tick during an attempt starts none (60a88be1) | `src/asy_ntp_client.py:324: due = self._unsynced_wait_s >= self._retry_wait_s and not self._attemptin` | RED (-1,32768) | test_a_check_tick_during_a_failing_attempt_starts_no_other_before_the_retry_wait |
| r3.check.fram_crc | a chunk with no CRC | `src/asy_scd30_driver.py:EOF + "def _planted_chunk(fram):\n    return fram.get_chunk(8, owner='X')"` | RED (host) | test_every_fram_chunk_in_src_is_created_with_a_real_crc |
| r3.check.fram_owner_site | a chunk built outside a constructor | `src/asy_scd30_driver.py:EOF + "def _planted_chunk(fram, crc):\n    return fram.get_chunk(8, crc=crc,` | RED (host) | test_src_builds_chunks_and_loggers_only_in_constructors |
| r3.check.sleep_forms | a float sleep_ms | `src/asy_ntp_client.py:EOF + 'async def _planted_sleep():\n    await asyncio.sleep_ms(1.5)'` | RED (host) | test_every_src_sleep_takes_whole_milliseconds |
| r3.check.timing_budget | a code-derived F.3 row's input changed | `src/asy_system_service.py:70: _TASK_CHECK_TIME = const(2)  # seconds period to check running tasks (` | RED (host) | test_the_code_derived_rows_match_the_code |
| r3.check.dev_fram_regions | a raw FRAM write at a literal production address | `tests_hardware/device_scripts/fram_conformance_probe.py:EOF + 'def _planted(chip, buf):\n    chip.se` | RED (host) | test_every_raw_fram_call_is_addressed_from_a_declared_region |
| r3.check.dev_watchdog_sleep | a sleep past the shared feed step | `tests_hardware/device_scripts/bmp3xx_plausibility_read.py:EOF + 'import time as _t\n_t.sleep(5)'` | RED (host) | test_no_rendered_script_sleeps_longer_than_one_feed_step |

## The two survivors

1. `named.fram_alloc` (`bytearray(16)` in `FRAMManager._write_chunk`): green at both stages; read as **below the
   test's stated granularity, not a gap**. Measured (`r3m_fram_budget`): a blank setup prices 26,464-26,944 B at -1
   (budget 30,000), so the plant's two calls per setup (+192-224 B) sit inside the 11 % headroom; B3 lowered the figure
   from the record's 28,544 B, which is why the record saw it red at -1. The test's own goal is "a coroutine-per-CS-
   cycle, or any comparable per-call allocation" (`tests/test_asy_fram_allocation_budget.py:1-3`): planted per CS cycle
   in `SPIDevice.session_begin()` (`r3m_fram_budget2`), 16 B prices the blank setup at 30,464 B (first run) and the valid
   one at 23,232 B, both over budget; 64 B at 32,224 / 24,736 B. At 32,768 the figures are 8-11 kB, under the budget
   by design ("the budgets' bite is the -1 stage's", `:24`).
2. `r3.i2c.stretch_yield` (`await asyncio.sleep_ms(1)` in `_scl_released()`'s awaited branch made `pass`): green at
   both stages; **a gap**. The held-SCL tests reach the wait and its timeout (`test_clear_and_recover_end_a_held_scl_at_
   the_bus_timeout`), but none checks that another task runs while a runtime clear waits on a stretched SCL, so a clear
   that spins for the whole `timeout_us` (50 ms by default, per wait) holding the loop passes (F.3's never-block rule,
   the routine's own comment at `src/asy_i2c_driver.py:35-37`). Proposed test (one line): in `tests/test_asy_i2c_driver.py`,
   a runtime `clear()` whose SCL reads low lets a sibling task run before it returns `_REC_SCL_HELD`.
