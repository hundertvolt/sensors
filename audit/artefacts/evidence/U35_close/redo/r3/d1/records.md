# R3 lane D1 working records (agent, 2026-11-04): a reading aid, never committed

Tree: `S/wt-u35int` at `17688315`, read-only (its `git status` before and after: `git_status_before.txt`, identical).
Base for "changed": `497b3eda`. Walks ran on a `git archive` copy (`ftmp/tree`, deleted at the hand-back) or wrote
their output here: `redflags_17688315.json`, `levels_17688315.md`, `intent_17688315.md`, `raising_17688315.md`,
`e51.md`. Run logs: `S/u35/lead/r3d1_*.log`.

## OR16 (2): R2's final gate skip and deselect list (`S/u35/lead/r2x_gate2_unit.log:25062-25171`)
- 80 skips, 6 deselects, 6 `tests_scripts` skips, "Checked nothing: none"; the 32768 log carries the same counts.
- 49 "runs on [..], one device per distinct wiring of [..]" and 5 "runs on arzi, the first generated device": derived at
  run time from `devices/*.toml`, true by construction.
- 5 "device wires no isl29125" and 5 "no uart_link": true (only `dev` wires either, `devices/*.toml`).
- 10 "a device-independent mechanism, run on dev / arzi only (E.2.1)": `first_device="stagger_wait"` / `"any"`
  (`scripts/_digital_twin_scenarios.py:1806`, `:1674`; reason text `:2381`; SPEC `:5155`). True.
- 6 "file modes do not bind for this process": this host runs as root (`:1561`); CI's non-root runner runs it. True.
- 6 deselected `wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server` (needs port 53): run by
  `run_digital_twin_ci.sh`'s harness part (`:133-137`), which CI calls per device and stage (`ci.yml:580`). True.
- 6 `test_real_firmware_build_produces_a_valid_uf2[*]`: CI's firmware-build-verify sets the opt-in (`ci.yml:673`). True.
- Verdict: every reason holds; no gap.

## U35-37: normal-situation hits
- 39 hits now (37 `ns_seed_text`, 2 `ns_allow_list` on one row); 38 verdicted flags at `98d8b71d`, all still matching.
- New hits: none. Verdicted hits gone: none. No (a): nothing for the owner.
- Two hit rows whose test changed, re-read, verdicts carry: `test_asy_notification_service.py:1080` (the word is
  about an override flag); `bench/test_sensor_config_push_over_real_hardware.py:169` (about a null value; the test
  asserts the ISL29125 log empty).
- Seen in the OR37 read, invisible to the scan (exact expectations, no allow list), each owner-ruled, none (a):
  `_check_quiet_boot()` (`:387`) owes each fresh store's W22 and each blank SGP40 chunk's W65
  (`scripts/_digital_twin_ci_suite.py`; owner 2026-10-01 in `8019a9ef`, owner 2026-10-02 in `1206e862`); the scenario
  harness's `_own_backup()` (`scripts/_digital_twin_scenarios.py:384`) excuses exactly one W35 per backup period of a twin that never syncs (the twin's
  environment, the product's correct code).

## OR25: levels and intent, re-rendered on `17688315`
- Walk: 143 files {closed 140, open 2, gap 1}; intent 214 rows, schema 238, functional 28, system 32, all biting.
  At `98d8b71d`: closed 141, open 2; intent 237. The walk exits 1 on three hand-named tests the scan no longer knows.
- Subtraction, items: 23 catalog-code rows drop out, each with its mechanism and no name left in its module:
  base TIMER and ISL `ISL_CAL_TIMEOUT` (`80b513b5`); BMP `READ_RANGE`, `BMP_CHIP_RESET`, SCD `SCD_NOT_READY`
  (`b4341646`); captive-DNS `INIT`, DNS `DNS_REPLY_TRUNCATED`, `SOCKET_TEARDOWN` x2, NTP `NTP_DNS_NOT_SENT`,
  `NTP_DNS_NXDOMAIN`, `STORED_DEFAULT` (`c29196b9`); FRAM `FRAM_BUS_DOWN`, `FRAM_CHIP_LOST`, `FRAM_WP_PARTIAL`, manager
  `ALLOC` (`eac7cd4c`); NTP `ALLOC` (`25a14b4f`); notify `NOTIFY_SIGNAL_DROPPED` (`6c00e98e`); SGP40 `CALLBACK`
  (`1206e862`); system `CONFIG_LOST` (`8019a9ef`); UART `UART_RX_OVERRUN` (`1b4caa17`); webserver `HTTP_REQUEST_CAP`,
  `HTTP_START_FAILED` (`ce199ebb`). One functional row's consumer list loses `asy_api_response.py`.
- Subtraction, hand-named tests: `refused_config_write_is_reported_unpersisted` (`16047d96`, ConfigUnpersisted gone),
  `test_read_triggers_that_never_arm_end_at_the_budgets_reboot_with_one_entry` (`80b513b5`, the failed-arm end gone),
  `test_a_stopped_scd30_ends_its_alerts_and_sgp40_compensation` (`963d0de1`, renamed to `..._ends_its_alerts`). Each
  system row still bites with its two other tests (`intent_17688315.md:531`, `:538`, `:547`).
- Levels narrowed, still mapped: L2 of E19 `LOCK_TIMEOUT` (lost-chip test gone, `eac7cd4c`) and E42-E44 (the overlay
  test gone, `6c00e98e`), L1 bites; L2 of E41 `TASK_BUDGET_REBOOT` lost its only scan-visible test (`80b513b5`), but the
  twin suite's Run 3 to 4 still proves the escalation's reset at L2 (`scripts/_digital_twin_ci_suite.py:1259-1261`),
  outside the walk's L2 globs; L0 of eight codes as `test_fault_or_warning_never_both.py`'s pairs shrank.
- Unmapped, one: `scripts/record_twin_instrument_runs.py`, L0 "gap: no test names it" (`levels_17688315.md:111`). See
  the hand-back's gaps.

## OR26: raising map for the seven never-raise modules (all seven changed since `497b3eda`)
- The walk refuses 65 hand verdicts as stale (sites gone); pruned in a scratch copy, it renders 1,149 sites, 587
  groups: unreachable 472, handled 535, defect 3 (the three fixed-in-lane rows, carried), open 6, transitive 8.
- Hand verdicts for the 14 non-terminal sites (all new since `497b3eda`):

| site | call | verdict | proof |
|---|---|---|---|
| base_classes:161 `RegionBuffer.__init__` | `logger.err` | handled | `PrintLog.err` (print_log:108-109, handled row): an at-level print's small fixed allocation, inside the except |
| base_classes:187 `PieceBuffer.copy_into` | `self.read_at` | handled | read_at's own rows (:194-201) are all terminal |
| print_log:148, :273, :306, :333 | `self.err` | handled | the same `PrintLog.err`; no subclass overrides it |
| print_log:211 `_store_err` | `self._write` | handled | `PrintLogHistory._write` returns True; the store's rows (:322-331) all terminal |
| system_service:372 `_request_shutdown` | `self._storage.erase_ready` | handled | neither raises nor yields (`eac7cd4c`): the manager's `initialized` implies the driver's (`verify_present()` has no product caller), `get_write_protected()` returns at :312 without an await, `_is_write_protected()` is an attribute or `Pin.value()`; the coroutines are small fixed allocations |
| fram_manager:462, :527 `read()` | `bytearray` | handled | no product caller (every product read uses `read_into()`); a library caller's task ends, conventions' run-time rule |
| fram_manager:625 `_watch_chip_loop` | `asyncio.Event().wait()` | handled | a small fixed allocation at the task's top (conventions) |
| math_helpers:166 `rel_humidity` | `max`, `min` | unreachable | two floats; NaN compares without raising |

- New raises outside the seven, each caught by its reader's handler (the pre-audit read paths): BMP3XX :470, :551
  (`b4341646`); ISL29125 :1167, :1201, :1449 (`80b513b5`); SCD30 :698, :838 (the read cycle's `except Exception`, :480);
  SPI `configure()` :50 (the chunk layer's UNEXPECTED and setup's INIT, `eac7cd4c`). I2C `_reg()`'s ValueError :150 is
  unreachable: no product caller passes `addrsize`.
- Seven carried verdicts keep their word but name a removed mechanism in the proof text (re-render text only):
  `_climb_ladder::_recover_bus` (old line numbers), `_trigger_loop::_read_event.set` ("as `_timer_failed`'s"),
  `err_s::_store_err` ("`_write_through`"), `FRAMChunkBuffer.__init__::super` ("report as ALLOC"),
  `erase_chip::report_set_values` ("`_report_chip_lost()`"), `invalidate::_handle_status_bytes` and
  `erase_ready::get_write_protected` ("called only by erase_chip()": `_request_shutdown()` :372 now calls it too).
- Limit: 241 hand verdicts sit on 90 functions the diff touched; only those naming a removed mechanism were re-read.
- No defect: nothing to reproduce.

## OR37 and OR38: the read of R1 and R2's additions
- Scope: 3,682 added lines in 353 files (`src` 844, `buildgen` 60, `digital_twin` 79, `scripts` 137, `js` 44, the test
  directories 2,518). `src`, `buildgen`, `digital_twin`, `scripts` and `js` read line by line; the test directories by
  their code lines with a pattern lens (sleeps, loops, retries, ports, sockets, tasks, timers, temp dirs, files,
  module patches).
- Found no harmful construct, race, leak or unguarded host step. What the read checked:
  - every new loop is bounded: `resolve_ipv4()`'s `range(tries)`, `_scl_released()`'s timeout, `UDPSocket.ready()`'s
    deadline or idle rate, the neopixel's queue deadline, the scenario helpers' deadlines;
  - new tests cancel what they start in a `finally` (`test_asy_captive_dns.py:433-438`,
    `test_asy_ntp_client.py:2571-2586`), take ports from their file's band (`tests/_port_bands.py`), patch module names
    under `try`/`finally` (`test_asy_uart_comm.py:270-275`), use `_tmp_cfg_dir()` or `tmp_path`;
  - no new fixed port, `rm`, `while True`, `kill` or host network step;
  - `microtest.py:101-103` resets `_utc_valid` after every test, so the 44 hand resets added are redundant, never needed.
- Observations, no defect, no gap:
  - `_request_shutdown()` lost its preflight catch and re-check (`eac7cd4c`). Sound while `erase_ready()` neither
    raises nor yields; a later raise there would leave `_shutdown` set and the gate stuck until reboot.
  - `I2C.__init__` runs `_clear_bus(...).send(None)` and sets `_boot_clear_status` only in the `StopIteration`
    handler (`asy_i2c_driver.py:95-98`): sound while `awaited=False` never suspends.
  - `voc_algorithm.py` is back on the C reference's `FIX16_MAX` 32767 (`1206e862`): from about 4.5 h the two uptime
    counters exceed rp2's small-int range, so each SGP40 cycle allocates. The owner ruled that this is accepted
    (2026-09-29, quoted in `1206e862`).
- Whole-tree scan: `rm -rf`/`rmtree` sites (31) are pre-existing, on variables with defaults or `mktemp` results;
  `build_device_websites.sh:51-57` removes only dirs holding an `index.html` under the named root, as its usage text
  says; ports 53 and 18080 sit behind `scripts/_port_lock.sh`; `while True` loops in `scripts/` and `tests_hardware/`
  exit on a deadline or a bounded retry count (`harness.py:790-812`).
- The per-file heap probe (OR38's other half) is lane M's run.

## OR19: verdicts for every flagged row whose test or target changed
- Scan: 8,359 tests, 347 flagged. `review_rows.py --check`: 19 stale verdicts, 13 flags on 12 rows unverdicted.
- In scope: 30 rows whose test changed; 36 whose test names a changed `src/` function; plus
  `test_supervise_tasks_without_watchdog_does_not_raise` (flag changed). That makes 67 rows and 70 flag verdicts,
  below. 89 more rows only share a changed module, and their flags are about test structure (setup helpers 36,
  `_retire` 16, fixed loops 14, seed words 12, two-path compares 10, others 5), so their verdicts carry. 191 unchanged.
- Stale: 17 verdicts went with their tests (renamed ones are re-verdicted below). Two tests stay with a flag gone:
  `test_a_crash_in_each_boot_phase_decodes_to_10_plus_the_phase` and
  `test_supervise_tasks_without_watchdog_does_not_raise`.
| # | test (file:line) | why in scope | flag | verdict | reason |
|---|---|---|---|---|---|
| 1 | test_asy_bmp3xx_driver.py:739 `test_pressure_oversampling_round_trip_every_valid_setting` | target fn: get_pressure_oversampling, set_pressure_oversampling | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 2 | test_asy_bmp3xx_driver.py:758 `test_temperature_oversampling_round_trip_every_valid_setting` | target fn: get_temperature_oversampling, set_temperature_oversampling | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 3 | test_asy_bmp3xx_driver.py:809 `test_filter_coefficient_round_trip_every_valid_setting` | target fn: get_filter_coefficient, set_filter_coefficient | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 4 | test_asy_bmp3xx_driver.py:1106 `test_config_write_accepts_every_field_at_its_valid_boundaries_and_midp` | target fn: get_dict | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 5 | test_asy_bmp3xx_driver.py:1118 `test_config_write_rejects_single_out_of_range_field` | target fn: get_dict | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 6 | test_asy_bmp3xx_driver.py:1136 `test_config_write_wrong_type_rejected_for_int_field_but_coerced_for_fl` | target fn: get_dict | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 7 | test_asy_bmp3xx_driver.py:1268 `test_config_write_accepts_every_legal_discrete_value` | target fn: get_dict | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 8 | test_asy_fram_driver.py:1235 `test_write_protected_and_access_not_locked_are_now_persisted` | target fn: set_write_protected | ns_seed_text | biting | carried, re-read: (b) both refusals are provoked by the test, each expecting its persisted code |
| 9 | test_asy_i2c_driver.py:532 `test_bus_busy_surfaces_as_etimedout` | target fn: readfrom_into, writeto | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 10 | test_asy_isl29125_driver.py:1229 `test_read_returns_a_narrow_results_tuple_without_cct` | target fn: _read_isl | ns_seed_text | biting | carried, re-read: the seed word is about an input, a value, a lock or a typo, not a logged code |
| 11 | test_asy_isl29125_driver.py:1761 `test_a_periodic_only_switch_warns_after_five_consecutive_occurrences` | target fn: _read_isl | ns_seed_text | biting | carried, re-read: (b) five provoked switches expecting their warning |
| 12 | test_asy_isl29125_driver.py:2899 `test_start_timer_degrades_when_the_alarm_pool_is_exhausted` | test changed | weak_only | weak | GAP: only `irq_handler is not None`; the wake check left with 80b513b5 and nothing pins the in-place print |
| 13 | test_asy_notification_service.py:321 `test_each_int_float_field_boundary_values_accepted` | target fn: _set_dict_cfg | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 14 | test_asy_notification_service.py:340 `test_each_int_float_field_just_outside_bounds_rejected` | target fn: _set_dict_cfg | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 15 | test_asy_notification_service.py:762 `test_check_one_never_raises` | test changed | no_assertion | justified | carried, re-read: the claim is the absence of a raise; run() propagates one (stated at :848) |
| 16 | test_asy_notification_service.py:1080 `test_monitor_loop_restart_does_not_clobber_an_active_led_override` | test changed | ns_seed_text | biting | carried, re-read: the seed word is about an input, a value, a lock or a typo, not a logged code |
| 17 | test_asy_ntp_client.py:2930 `test_the_shape_corpus_judges_ntp_host_and_dns_fallback` | target fn: get_dict | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 18 | test_asy_print_log.py:1604 `test_level_0_prints_nothing_for_a_caught_memory_error` | test changed | loop_vacuous | biting | _ENTRIES is a fixed 7-entry table (:1595) |
| 19 | test_asy_sgp40_driver.py:310 `test_reset_tolerates_nak_at_general_call_address` | target fn: writeto, _reset | ns_seed_text | biting | carried, re-read: the seed word is about an input, a value, a lock or a typo, not a logged code |
| 20 | test_asy_sgp40_driver.py:614 `test_read_sgp_without_compensation_data_yet_logs_nothing` | target fn: _read_sgp | ns_seed_text | biting | carried, re-read: a normal situation asserting no entry: SGP40's first-boot wrnno 10 landed |
| 21 | test_asy_spi_driver.py:117 `test_device_operations_on_an_already_deinitialized_bus_return_none_or_` | test changed | no_assertion | justified | a no-raise claim: every transfer returns before the bus while _spi is None (asy_spi_driver.py:71-90); removing a guard raises |
| 22 | test_asy_system_service.py:1245 `test_bootloader_takes_over_closes_quiesces_stops_then_enters_the_bootl` | test changed | setup_credit_only | biting | _takes_over() (:1225-1238) carries nine assertions |
| 23 | test_asy_system_service.py:1245 `test_bootloader_takes_over_closes_quiesces_stops_then_enters_the_bootl` | test changed | helper_swallows | justified | _retire() (:1047-1055) only cleans up a task the scenario leaves; its end is not the claim |
| 24 | test_asy_system_service.py:1305 `test_an_erased_chip_boots_like_a_new_one` | target fn: err_s | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 25 | test_asy_system_service.py:1370 `test_every_refusal_answers_false_and_changes_nothing` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 26 | test_asy_system_service.py:1386 `test_the_same_command_again_answers_true_and_any_other_answers_false` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 27 | test_asy_system_service.py:1411 `test_two_commands_at_once_start_one_sequence_and_one_reset` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 28 | test_asy_system_service.py:1451 `test_a_command_in_its_preflight_refuses_a_mempause_and_another_word_an` | target fn: pause_permanent_storage | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 29 | test_asy_system_service.py:1472 `test_a_refused_preflight_answers_the_same_word_waiting_on_it_with_its_` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 30 | test_asy_system_service.py:1487 `test_a_raising_flush_reaches_the_reset_and_reads_9_unless_a_config_res` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 31 | test_asy_system_service.py:1573 `test_a_fault_in_a_shutdown_step_is_logged_and_the_watchdog_still_reset` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 32 | test_asy_system_service.py:1597 `test_a_chunk_that_cannot_be_blanked_stops_the_erase_before_any_overwri` | target fn: invalidate | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 33 | test_asy_system_service.py:1783 `test_a_command_before_the_supervisor_runs_waits_for_its_first_pass` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 34 | test_asy_system_service.py:1842 `test_a_fram_write_in_flight_completes_both_blocks_and_a_later_one_is_r` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 35 | test_asy_system_service.py:1918 `test_an_erase_under_an_active_mempause_completes` | target fn: pause_permanent_storage | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 36 | test_asy_system_service.py:1938 `test_tasks_dying_while_a_command_runs_never_escalate` | target fn: _log_dead_task, release | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 37 | test_asy_system_service.py:2022 `test_a_command_during_the_escalations_entry_write_is_refused_and_the_e` | test changed | helper_swallows | justified | _retire() (:1047-1055) only cleans up a task the scenario leaves; its end is not the claim |
| 38 | test_asy_system_service.py:2048 `test_a_command_during_an_entry_write_that_never_ends_leaves_the_escala` | test changed | helper_swallows | justified | _retire() (:1047-1055) only cleans up a task the scenario leaves; its end is not the claim |
| 39 | test_asy_system_service.py:2093 `test_the_escalation_decides_and_records_the_reset_before_its_entry_wri` | test changed | helper_swallows | justified | _retire() (:1047-1055) only cleans up a task the scenario leaves; its end is not the claim |
| 40 | test_asy_system_service.py:2127 `test_the_systems_own_log_reset_is_refused_from_the_reset_decision_on` | target fn: reset_error_counter, err_s | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 41 | test_asy_system_service.py:2160 `test_after_the_takeover_no_other_site_feeds` | target fn: _log_dead_task, release | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 42 | test_asy_system_service.py:2267 `test_a_hang_in_any_step_is_never_fed` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 43 | test_asy_system_service.py:2333 `test_a_command_that_hangs_before_its_arm_reads_command_incomplete_at_t` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 44 | test_asy_system_service.py:2372 `test_a_refused_command_never_stops_the_supervisor_feeding` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 45 | test_asy_system_service.py:2407 `test_a_deadline_crossed_after_an_accepted_command_leaves_storage_pause` | target fn: _status_loop, pause_permanent_storage | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 46 | test_asy_system_service.py:2453 `test_a_loop_ended_during_boot_writes_nothing_so_the_next_boot_reads_it` | target fn: begin_boot | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 47 | test_asy_system_service.py:2866 `test_supervise_tasks_without_watchdog_does_not_raise` | new flag | setup_credit_only | justified | a no-raise claim: a supervisor raise keeps its exception in task.data (extmod/asyncio/core.py:229-237), which cancel() awaits and re-raises |
| 48 | test_asy_system_service.py:3375 `test_a_config_put_mid_write_when_a_command_starts_is_flushed_before_th` | test changed | helper_swallows | justified | carried, re-read: _retire() (tests/test_asy_system_service.py:1130-1137) only cleans up a task the scenario leaves behind; its e |
| 49 | test_asy_system_service.py:3551 `test_a_command_during_the_stack_escalations_entry_write_is_refused_and` | test changed | helper_swallows | justified | _retire() (:1047-1055) only cleans up a task the scenario leaves; its end is not the claim |
| 50 | test_asy_uart_comm.py:1908 `test_both_halves_of_each_pair_move_identical_bytes` | target fn: uart_set_into | same_callee | biting | carried, re-read: two distinct paths, objects or runs compared: their agreement is the claim |
| 51 | test_asy_webserver_service.py:1933 `test_d_get_error_sources_reports_the_service_itself_for_a_uniform_call` | target fn: err_s | same_callee | biting | carried, re-read: two distinct paths, objects or runs compared: their agreement is the claim |
| 52 | test_asy_wifi_service.py:2427 `test_print_wlan_diagnostics_does_not_raise_on_success` | target fn: _print_wlan_diagnostics | no_assertion | justified | carried, re-read: a print-only diagnostic whose one contract is never raising (stated in place) |
| 53 | test_asy_wifi_service.py:2437 `test_print_wlan_diagnostics_degrades_gracefully_when_ifconfig_raises` | target fn: _print_wlan_diagnostics | no_assertion | justified | carried, re-read: a print-only diagnostic whose one contract is never raising (stated in place) |
| 54 | test_digital_twin_hot_replug.py:233 `test_a_power_cycled_bmp3xx_reads_on_at_the_chip_defaults_without_a_lad` | test changed | setup_credit_only | weak | GAP: the helper's 'nothing logged' reads W slots only, so an E entry passes; 'the chip defaults' is unchecked |
| 55 | test_generated_boot_entry.py:114 `test_any_other_exception_ending_the_loop_is_recorded_then_resets_the_c` | test changed | loop_vacuous | biting | devices() is the shipped device list and the planted tuple is fixed |
| 56 | test_generated_boot_entry.py:129 `test_a_console_interrupt_is_recorded_before_it_propagates` | test changed | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 57 | test_voc_algorithm.py:109 `test_process_after_blackout_produces_index_in_documented_range` | target fn: vocalgorithm_process | wide_tolerance | justified | carried, re-read: 1..500 is the VOC index's documented output range, the claim itself |
| 58 | test_voc_algorithm.py:109 `test_process_after_blackout_produces_index_in_documented_range` | target fn: vocalgorithm_process | wide_tolerance | justified | carried, re-read: 1..500 is the VOC index's documented output range, the claim itself |
| 59 | test_voc_algorithm.py:122 `test_process_sraw_out_of_valid_range_still_produces_an_index` | target fn: vocalgorithm_process | wide_tolerance | justified | carried, re-read: 1..500 is the VOC index's documented output range, the claim itself |
| 60 | test_voc_algorithm.py:149 `test_process_oscillating_extreme_readings_widens_the_variance_scaling` | target fn: vocalgorithm_process | wide_tolerance | justified | carried, re-read: 1..500 is the VOC index's documented output range, the claim itself |
| 61 | test_voc_algorithm.py:165 `test_process_sustained_extreme_low_then_high_readings_clamps_the_sigmo` | target fn: vocalgorithm_process | wide_tolerance | justified | carried, re-read: 1..500 is the VOC index's documented output range, the claim itself |
| 62 | test_voc_algorithm.py:344 `test_a_stack_overflow_or_an_allocation_failure_in_the_state_codec_prop` | target fn: pack_into, unpack_from | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 63 | test_voc_algorithm.py:384 `test_the_ports_own_state_always_restores` | test changed | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 64 | test_voc_algorithm.py:384 `test_the_ports_own_state_always_restores` | test changed | wide_tolerance | justified | carried, re-read: int32 is the state codec's stored width; the claim is representability |
| 65 | test_voc_algorithm.py:393 `test_the_lowered_uptime_limit_leaves_the_output_unchanged` | target fn: pack_into, unpack_from | same_callee | biting | two runs compared; but its subject, the port's 16383 limit, went in 1206e862 (see gaps) |
| 66 | test_voc_algorithm.py:518 `test_fix16_helpers_match_the_c_reference_vectors` | target fn: _fix16_exp | loop_vacuous | biting | carried, re-read: the iterable is a fixed non-empty table, vector list, constant or the shipped device list |
| 67 | test_sensor_config_push_over_real_hardware.py:169 `test_isl29125_calibrate_command_push_over_real_rest` | test changed | ns_seed_text | biting | carried, re-read: the seed word is about an input, a value, a lock or a typo, not a logged code |
| 68 | test_bus_concurrency.py:237 `test_bus_topology_autodetect_address_and_reserved_range_sweep` | test changed | hw_no_log | CRr2 | carried, re-read: the bench log fixture and marker / the flash tier's logs fact |
| 69 | test_bus_concurrency.py:316 `test_fram_cs_pin_hijack_fault_injection_and_recovery` | test changed | hw_no_log | CRr2 | as its siblings: the flash tier's logs fact; the chip-lost errnos check left with eac7cd4c |
| 70 | test_memory_stress.py:148 `test_loop_lag_under_combined_load_stays_under_the_uart_reply_budget` | test changed | hw_no_log | CRr2 | carried, re-read: the bench log fixture and marker / the flash tier's logs fact |
