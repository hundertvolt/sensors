OR41 actor x shared resource, with U35-09's recombination x level row (lane D2, agent, 2026-11-04)

Read-only on `S/wt-u35int` at `17688315`; a reading aid, never committed. Resources are SPEC's lock table
(`SPECIFICATION.md` 3965-3981, locks:begin to locks:end) plus the unlocked ones (heap, loop, alarm pool, TCP slots, UART ring). One line per
cell: actor x resource | interaction | test (level) or reason. L1 unit, L2 twin, L3 flash, L4 bench (E.6.1).
"gen." is `tests/test_bus_hazard_generated.py`'s per-device x per-bus registration; "sc." a
`tests/_sensortask_scenarios.py` scenario (L1, every device); "tw." a `scripts/_digital_twin_scenarios.py` scenario (L2).
Every name below was checked present at `17688315` (a static walk, run `r3d2_names2`; method in the hand-back).

## I2C buses (`I2C.bus_lock`, `Lockable.session_lock`)
- readers x readers on one bus | cross-device interleave | gen. `..._all_real_occupants_concurrent_reads_stay_correct_and_genuinely_interleave` (L1); `test_digital_twin_bus_hazard_concurrency.py::test_the_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call` (L2); `flash/test_bus_concurrency.py::test_cross_device_concurrent_sessions_genuinely_interleave` (L3); `bench/test_bus_concurrency_under_api_load.py::test_concurrent_get_sensors_under_real_multi_client_load_never_corrupts_or_crashes` (L4)
- reader x its own split register read | sibling between the two transfers | `test_bus_hazard_multi_device.py::test_a_register_read_is_two_transfers_with_no_sibling_transfer_between_them` (L1)
- reader's bus rung (clear/recover) x sibling readers | a sibling transfer inside the clear | `test_bus_hazard_multi_device.py::test_a_recovery_during_a_held_bus_clear_lets_no_sibling_transfer_in` (L1); `test_digital_twin_bus_hazard_concurrency.py::test_a_bus_recovery_does_not_disturb_concurrent_sibling_reads` (L2); `flash/test_bus_concurrency.py::test_a_held_sda_line_is_cleared_and_every_device_answers` (L3); L4: E.6.6 `flash-only-bus-checks` (no REST route)
- two readers' rungs x one bus | a rung run twice | `test_asy_base_classes.py::test_a_bus_rung_parked_behind_a_sibling_session_is_spent_for_every_reader_on_the_bus` (L1); `test_digital_twin_bus_hazard_concurrency.py::test_two_failing_readers_on_one_bus_run_each_bus_rung_once` (L2)
- SGP40 general call x bus siblings | broadcast mid-read | `test_bus_hazard_multi_device.py::test_sgp40_general_call_reset_does_not_disturb_a_concurrent_bmp3xx_read` (L1); twin graph test above (L2); `flash/test_bus_concurrency.py::test_sgp40_general_call_reset_does_not_corrupt_concurrent_scd30_and_isl29125_transactions` (L3); L4: E.6.6 `sgp40-general-call`
- participant rungs (SCD30 reset, SGP40 heater-off, BMP3XX reset, ISL re-apply) x siblings | reset mid sibling read | `test_digital_twin_bus_hazard_concurrency.py::test_an_scd30_soft_reset_mid_read_leaves_every_twin_sibling_read_valid`, `::test_sgp40_heater_off_mid_read_leaves_every_twin_sibling_read_valid`, `::test_a_bmp3xx_setup_reset_mid_read_leaves_every_twin_sibling_read_valid`, `::test_an_isl29125_reapply_mid_read_leaves_every_twin_sibling_read_valid` (L2); L1 twins of each in `test_bus_hazard_multi_device.py`
- REST PUT (chip write) x sibling reads | write mid read | gen. `..._a_<driver>_write_does_not_disturb_concurrent_sibling_reads_across_timing_offsets` (L1); tw. `isl29125_config_put_during_get_loops` (L2); `flash/test_bus_concurrency.py::test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads` (L3); bench `test_isl29125_config_write_..._under_api_load`, `test_bmp3xx_config_write_..._under_api_load`, `test_scd30_config_write_..._under_api_load` (L4, gated)
- REST GET chip config x reader | snapshot torn by a write | `test_asy_scd30_driver.py::test_get_dict_cfg_snapshot_is_atomic_against_a_concurrent_config_write` (L1); `test_asy_isl29125_driver.py::test_a_config_get_answers_the_snapshot_it_checked_when_another_lands_meanwhile` (L1)
- task cancelled inside a session x bus | lock left held | `test_bus_hazard_multi_device.py::test_a_sensor_cancelled_inside_its_session_leaves_the_bus_free_and_the_sibling_read_valid` (L1); `test_digital_twin_bus_hazard_concurrency.py::test_a_sensor_task_cancelled_inside_its_session_leaves_the_bus_usable` (L2)
- system command x SCD30 write | NVM write during a shutdown | sc. `only_the_api_writes_the_scd30`, sc. `every_api_write_is_refused_from_a_system_commands_acceptance_to_its_reset` (L1); `test_digital_twin_bus_hazard_concurrency.py::test_no_scd30_write_reaches_the_chip_while_a_system_command_runs` (L2)
- boot clear x bus | held line at power-up | `test_digital_twin_held_i2c_line.py::test_a_bus_held_at_power_up_is_clocked_free_before_construction_and_reported_once` (L2)
- read triggers x one bus | trigger spread (OR47) | sc. `read_triggers_follow_the_stagger_on_the_real_sequencer` (L1)

## SPI bus and FRAM (`FRAM_SPI._bus_lock`, `_FRAMBaseChunk._op_lock`, `PrintLogHistoryStore._write_lock`)
- async x synchronous SPI sessions | CS overlap | `test_bus_hazard_multi_device.py::test_spi_async_and_synchronous_sessions_share_one_bus_without_cs_overlap` (L1)
- loggers x loggers | two writes into one chunk | `test_asy_fram_manager.py::test_op_lock_prevents_concurrent_writes_from_interleaving_between_blocks`, `test_asy_print_log.py::test_concurrent_writes_land_newest_last` (L1); `flash/test_bus_concurrency.py::test_fram_same_device_read_write_concurrency` (L3)
- erasefram x chunk writes | torn chunk | `test_bus_hazard_multi_device.py::test_an_erase_lets_a_write_and_a_read_in_flight_finish_whole_refuses_later_ones_and_holds_each_unit_whole` (L1); `test_digital_twin_bus_hazard_concurrency.py::test_the_erase_racing_a_logger_write_never_tears_a_chunk` (L2); `flash/test_bus_concurrency.py::test_fram_erase_racing_a_chunk_write_leaves_no_torn_chunk` (L3); `bench/test_bus_concurrency_under_api_load.py::test_fram_erase_under_api_load` (L4)
- ResetErrors x logger writes | a clear undone | `test_asy_print_log.py::test_an_entry_logged_while_a_reset_waits_on_the_write_lock_rides_its_write`, `test_asy_webserver_service.py::test_reset_errors_runs_every_source_at_once` (L1); tw. `reset_errors_over_real_http_is_not_undone_by_a_fram_loggers_later_setup` (L2)
- mempause x loggers | writes in a pause | `test_asy_fram_manager.py::test_a_held_mempause_spends_one_slot_for_paused_writes_and_reads` (L1); `test_digital_twin_bus_hazard_concurrency.py::test_storage_pause_gates_the_real_twin_chip` (L2); `flash/test_fram_storage.py::test_storage_pause_gates_the_real_chip_and_the_real_auto_unpause_timer_fires` (L3)
- SGP40 backup x restore | one buffer | `test_asy_sgp40_driver.py::test_simultaneous_restore_and_backup_in_one_cycle_reads_then_rewrites_the_same_buffer` (L1); `flash/test_fram_storage.py::test_sgp40_voc_state_backs_up_to_and_restores_from_the_real_chip` (L3); `bench/test_end_to_end_timing.py::test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly` (L4, gated)
- a timestamped write x a concurrent NTP sync | blocked stamp | `test_ntp_fram_system_integration.py::test_calling_real_ntp_issynced_from_fram_write_into_does_not_block_on_a_concurrent_real_sync` (L1)

## Flash filesystem and config (`ConfigManager._config_lock`, `owner_lock` / `_set_lock`)
- PUT x PUT, one store | a lost value | `test_asy_config_manager.py::test_concurrent_writes_are_serialized_not_lost`, `test_asy_base_classes.py::test_concurrent_puts_keep_the_later_value` (L1)
- GET x PUT | mixed before/after | `test_asy_webserver_service.py::test_e_a_config_get_never_mixes_values_from_before_and_after_a_concurrent_put` (L1)
- reader of the file x write/delete | half-written file | `test_bus_hazard_multi_device.py::test_a_concurrent_reader_never_sees_a_config_file_half_written_or_half_deleted` (L1)
- recovery rung x PUT | rung overwrites an accepted value | `test_asy_scd30_driver.py::test_a_put_during_the_recovery_completes_after_it` (L1)
- command flush x pending PUT | lost staged write | sc. `webserver_system_put_reboot_flushes_a_still_pending_config_write_first`; `test_asy_config_manager.py::test_a_write_queued_behind_the_lock_at_close_time_is_refused`; `test_asy_base_classes.py::test_a_put_queued_behind_the_put_lock_when_the_store_closes_is_refused` (L1)
- failing flush x next change | flush's log write held | `test_asy_config_manager.py::test_a_change_queued_behind_a_failing_flushs_log_write_heals_it_and_keeps_its_value` (L1)
- config flush (interrupts off) x UART ring | frame lost | tw. `uart_ring_under_concurrent_load` (L2); `flash/test_uart_crossover.py::test_a_real_config_write_during_traffic_loses_no_frame` (L3, gated)
- config flush x Wi-Fi link | link drop | `bench/test_network_resilience.py::test_a_flash_write_holding_interrupts_off_keeps_the_wifi_link` (L4, gated)

## Samples (`SensorReader._data_lock`, leaf)
- reader store x GET | torn sample | `test_asy_webserver_service.py::test_i4_hammer_measurements_and_sensors_concurrently_with_a_real_config_write` (L1); bench `test_concurrent_get_sensors_..._never_corrupts_or_crashes` (L4)
- reader store x republish / PUT | stale overwrite | `test_asy_scd30_driver.py::test_a_store_interleaved_with_a_republish_keeps_the_fresh_sample`, `test_asy_bmp3xx_driver.py::test_a_pres_offset_put_during_a_conversion_does_not_change_the_stored_sample` (L1)
- notification monitor x three config groups | unlocked read | reason: a `ConfigManager` value read never suspends on success, so the three reads run as one unit (SPEC 3984-3986)
- two sensors x notification | cross-contamination | `test_notification_scd30_sgp40_integration.py::test_both_sensors_crossing_threshold_together_trigger_their_own_signal_without_cross_contamination` (L1)

## Radio and sockets (`WifiService.wifi_mode_lock`, `UDPSocket._connect_lock`, TCP slots)
- NTP sync x Wi-Fi mode switch | one radio | `test_ntp_wifi_dns_integration.py::test_ntp_sync_holding_the_lock_blocks_a_concurrent_real_wifi_mode_switch`, `::test_a_reconnect_asked_during_the_hold_runs_in_the_next_wifi_iteration` (L1); bench `test_concurrent_get_sensors_..._survives_repeated_real_wifi_flapping` (L4)
- GET /status x held mode lock | blocked status | sc. `webserver_status_answers_the_networking_snapshot_while_wifi_mode_lock_is_held`; `test_asy_wifi_service.py::test_get_dns_server_ip_returns_the_last_snapshot_value_while_the_lock_is_held` (L1)
- connect x disconnect of one socket | crash mid connect | `test_asy_udp_socket.py::test_disconnect_no_longer_crashes_a_concurrent_in_flight_connect_retry`, `::test_concurrent_caller_joins_an_in_flight_connect_instead_of_a_premature_none` (L1)
- hotspot start x captive DNS task | leaked server task | `test_asy_wifi_service.py::test_start_hotspot_does_not_leak_a_dns_server_task_when_called_again_while_already_running` (L1); tw. `wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server` (L2); `bench/test_hotspot_role_reversal.py` (L4)
- clients x TCP slots | ceiling | tw. `connections_beyond_max_connections_are_rejected_cleanly_not_crashed`, `the_accept_queue_is_never_shallower_than_the_admission_ceiling` (L2); `bench/test_network_resilience.py::test_connections_at_and_above_the_real_socket_limit_degrade_cleanly` (L4)

## LED (`NeopixelDriver._overlay_lock`)
- notification ramp x LightCmdLED | two flashes | `test_notification_neopixel_integration.py::test_led_signal_during_a_notification_ramp_is_refused_at_once` (L1); sc. `webserver_notification_light_cmd_led_refuses_a_second_flash_at_once` (L1)
- Wi-Fi LED overlay x ramp | overlay write mid ramp | `test_asy_neopixel_driver.py::test_overlay_write_deferred_while_ramp_holds_the_overlay_lock`, `::test_overlay_calls_during_active_ramp_only_become_visible_after_ramp_finishes` (L1); L3/L4: E.6.6 `ws2812-no-readback`
- notification x busy LED | lost signal | `test_notification_neopixel_integration.py::test_a_notification_behind_a_busy_led_queues_at_its_deadline_with_no_entry` (L1)

## Commands (`SystemService._command_lock`) and ISL thresholds (`_threshold_lock`)
- command x command | two resets | `test_asy_system_service.py::test_two_commands_at_once_start_one_sequence_and_one_reset` (L1); tw. `erasefram_concurrent_with_a_reboot_accepts_exactly_one`, `reboot_and_bootloader_at_once_accept_exactly_one` (L2); `bench/test_system_commands_over_rest.py` (L4, E.6.6 `system-commands-instrumented`)
- command x escalation | two resets | `test_asy_system_service.py::test_a_command_during_the_escalations_entry_write_is_refused_and_the_escalation_resets` (L1); tw. `reset_errors_while_the_escalation_logs_is_refused_and_clears_nothing` (L2)
- tasks dying x a command | escalation mid command | `test_asy_system_service.py::test_tasks_dying_while_a_command_runs_never_escalate` (L1)
- ResetErrors x a command | clear during shutdown | tw. `reset_errors_while_a_command_owns_the_reset_is_refused_and_clears_nothing` (L2)
- threshold push x threshold push / range switch | interleaved registers | `test_asy_isl29125_driver.py::test_two_concurrent_threshold_pushes_end_on_the_later_one` (L1)

## Unlocked shared resources
- every task x heap | allocation failure under load | the four memory gates at both stages (CLAUDE.md); `test_digital_twin_uart_link.py::test_every_train_crosses_intact_while_the_heap_churns` (L2); tw. `high_concurrency_burst_at_historical_segfault_repro_scale_survives` (L2); `bench/test_memory_stress_bench.py` (L4)
- every task x loop vs watchdog | starved feed | `test_digital_twin_sensortask_integration.py::test_watchdog_is_never_starved_while_the_real_supervisor_runs` (L2); tw. `loop_lag_under_combined_load`, `zero_think_time_readers_saturate_then_recover` (L2); `test_digital_twin_bus_hazard_concurrency.py::test_the_erase_feeds_the_watchdog_at_bus_speed` (L2); LAN UDP storm: reason, owner ("Live with the udp storm", 2026-11-02)
- Timers x alarm pool / soft-IRQ queue | lost fire | `test_digital_twin_timer_pool.py` (L2, 3 tests); tw. `a_boot_stagger_fire_lost_to_a_full_scheduler_queue_stalls_the_timer_start_until_the_watchdog`, `a_reboots_reset_fire_lost_to_a_full_scheduler_queue_leaves_the_reset_to_the_watchdog` (L2); A1 (lane M) (L2); `device_scripts/timer_alarm_pool_exhaustion.py`, `scheduler_saturation_drop.py` (L3)
- UART initiator x responder (dev) | two initiations, both ends transmitting | `tests/test_uart_comm_hazard.py` (L1); `test_digital_twin_uart_comm_hazard.py` (L2); `flash/test_uart_crossover.py::test_comm_hazards_are_serialised_refused_or_recovered` (L3); `bench/test_uart_link_under_api_load.py::test_a_hazard_run_under_the_readers_load_reports_every_verdict` (L4)
- UART link x API load | starved link | `test_digital_twin_uart_link.py::test_a_hazard_run_put_through_the_api_while_readers_hammer_it_reports_every_verdict` (L2); `bench/test_uart_link_under_api_load.py::test_the_link_stays_healthy_while_the_api_is_hammered` (L4)
- boot setups x watchdog | unfed stretch | sc. `boot_feeds_the_watchdog_exactly_once_per_setup_call`, `the_unfed_boot_stretch_after_the_last_setup_feed_stays_within_two_seconds` (L1)

## U35-09: the owner's two recombinations x level
| recombination | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| bus + API load, NTP unreachable from boot | reason: the parts only, single-factor (sc. `an_ntp_server_that_never_replies_spends_one_slot_and_a_reply_syncs_once_it_answers`; `test_i4_hammer_...`); the booted, served recombination is L2's (E.6.1) | tw. `survives_bus_and_api_load_while_ntp_is_unreachable` (`:1404`, every device, both stages) | reason: L3 has no network (E.6.6 `ntp-unreachable-under-load`) | `bench/test_bus_concurrency_under_api_load.py::test_concurrent_get_sensors_under_real_multi_client_load_survives_an_ntp_transient_outage_and_retry` (reset under the NTP block, readers and SGP40 resets during it) |
| the same with a config write every second | reason as above (parts: `test_concurrent_writes_are_serialized_not_lost`) | tw. `survives_bus_and_api_load_while_ntp_is_unreachable_with_concurrent_config_writes` (`:1410`) | reason: no network | none: E.6.6's reason, a flash write a second behind `persistence_write`, "a gap until written" |

## Result
- Cells: 55 interaction lines plus the 10 recombination cells. A real interaction with no test anywhere: none found.
- Finding (doc, for R4): E.6.6 `ntp-unreachable-under-load` (`SPECIFICATION.md:5831`) says the outage under load is "a
  gap until written", but the bench test above has reset the board under the NTP block with load running since
  `0c0ad52c` (2026-10-15). The row's first half is stale; its write variant's L4 gap stands as recorded.
