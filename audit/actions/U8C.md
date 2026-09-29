# A-L U8C — `@tunable` classification of `tests/` and `tests_hardware/` (HEAD a4766a9)

Finishes the one NOT-DONE item of U8 (Ledger G4/R54 row "per-value classification … of the `tests/` and
`tests_hardware/` candidates"; register fix 6 of `audit/actions/U8.md`). Code at `a4766a9` equals `d982cf0` and `0ae0d4f`
(the base Appendix C was counted at) outside `audit/`: `git diff --stat 0ae0d4f HEAD -- . ':!audit'` is empty.
Tag grammar, Part N, the register check and the comment-cap exemption are A.U8.01-A.U8.03; product IDs a mirror
points at are the ones A.U8.04-A.U8.22 define.

## Search (C.0.1, own implementation)

Script: `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/al/U8C/c01.py`, run as
`python3 c01.py 'tests/**/*.py' 'tests_hardware/**/*.py'` from the repo root; written from C.0.1's text, not from
the reference `inv2.py`. 203 files parsed, **0 parse failures**, 156 files with hits. A hit is keyed
(kind, file, literal line, literal) as C.0.1 says; a unary minus stays part of the literal.

**Hits: 2,265** on 1,943 distinct (kind, file, line) triples — const 290, const-c 253, call 599, kw 915,
param 60, assert 131, deadline 17.

Differences from the reference `inv2.py` (2,286 at the same HEAD), each checked:
- assert −1: `tests/test_asy_uart_driver.py:1861` `bytes(got) == b"\x41" * 40` — the reference counts `b"…" * 40`
  as literal arithmetic; C.0.1 says "BinOp/UnaryOp over numeric literals", and a bytes operand is not numeric.
- kw −31: the reference keys a kw hit by its call and keyword text, so one literal value reached through two
  keywords on one line counts twice (e.g. `test_asy_uart_driver.py:500` `start_timeout_ms=200, timeout_ms=200`);
  C.0.1's key (kind, file, line, literal) counts it once. The table below classifies the line once; both
  keywords get the verdict.
- const-c +11: the reference drops the sign inside a container (`(-500.0, 500.0)` is one key); C.0.1 keeps a
  unary minus with its literal, so both are hits.

Per file and kind:

| file | const | const-c | call | kw | param | assert | deadline | total |
|---|---|---|---|---|---|---|---|---|
| `tests/_boot_contiguity_probe.py` | 3 |  | 1 |  |  |  |  | 4 |
| `tests/_bus_hazard_catalog.py` | 8 | 6 |  |  |  |  |  | 14 |
| `tests/_digital_twin_construction_scenarios.py` |  |  | 2 | 3 |  |  |  | 5 |
| `tests/_sensortask_scenarios.py` |  | 2 |  |  |  | 2 |  | 4 |
| `tests/_strict_json.py` | 1 |  |  |  |  |  |  | 1 |
| `tests/_uart_comm_harness.py` | 3 |  | 1 |  | 1 |  |  | 5 |
| `tests/_uart_link_contract.py` |  |  |  |  |  | 5 |  | 5 |
| `tests/_webserver_concurrency_scenarios.py` | 1 |  | 10 | 2 | 2 | 1 |  | 16 |
| `tests/machine.py` | 14 |  |  |  | 4 |  |  | 18 |
| `tests/network.py` | 8 |  |  |  |  |  |  | 8 |
| `tests/test_api_response.py` |  | 3 |  |  |  |  |  | 3 |
| `tests/test_asy_bmp3xx_driver.py` | 4 | 37 | 2 | 1 |  | 4 |  | 48 |
| `tests/test_asy_dns_client.py` |  |  | 1 | 24 | 3 | 1 |  | 29 |
| `tests/test_asy_fram_driver.py` |  | 3 | 2 |  |  |  |  | 5 |
| `tests/test_asy_fram_manager.py` |  | 2 | 1 | 1 |  |  |  | 4 |
| `tests/test_asy_i2c_driver.py` |  |  | 3 | 1 |  | 2 |  | 6 |
| `tests/test_asy_isl29125_driver.py` | 14 |  |  |  |  | 7 | 5 | 26 |
| `tests/test_asy_neopixel_driver.py` |  |  | 35 |  |  |  |  | 35 |
| `tests/test_asy_notification_service.py` |  | 10 | 11 | 5 | 1 |  |  | 27 |
| `tests/test_asy_ntp_client.py` | 1 | 13 | 25 | 22 | 9 | 15 |  | 85 |
| `tests/test_asy_scd30_driver.py` |  |  | 4 |  |  | 3 |  | 7 |
| `tests/test_asy_sgp40_driver.py` | 1 | 6 | 1 |  | 1 | 16 |  | 25 |
| `tests/test_asy_spi_driver.py` |  |  | 4 |  |  |  |  | 4 |
| `tests/test_asy_uart_comm.py` | 16 |  | 29 | 101 |  | 2 |  | 148 |
| `tests/test_asy_uart_driver.py` |  |  | 29 | 46 |  | 3 |  | 78 |
| `tests/test_asy_uart_link_driver.py` | 3 |  | 3 |  | 1 |  |  | 7 |
| `tests/test_asy_udp_socket.py` |  |  | 18 | 47 | 1 | 4 |  | 70 |
| `tests/test_asy_webserver_service.py` | 3 | 22 | 4 | 62 | 3 |  |  | 94 |
| `tests/test_asy_wifi_service.py` |  | 15 | 10 | 2 |  | 4 |  | 31 |
| `tests/test_base_classes.py` |  | 3 |  |  |  |  |  | 3 |
| `tests/test_bus_hazard_generated.py` |  | 1 |  |  |  |  |  | 1 |
| `tests/test_bus_hazard_multi_device.py` | 4 | 3 |  |  |  |  |  | 7 |
| `tests/test_captive_dns.py` |  |  | 15 | 4 | 4 | 20 |  | 43 |
| `tests/test_config_manager.py` |  | 29 |  |  |  |  |  | 29 |
| `tests/test_digital_twin_bus_hazard_concurrency.py` |  |  | 4 | 12 |  |  |  | 16 |
| `tests/test_digital_twin_fram.py` | 1 |  |  |  |  | 1 |  | 2 |
| `tests/test_digital_twin_http_client.py` | 2 |  | 1 | 5 | 1 |  |  | 9 |
| `tests/test_digital_twin_isl29125.py` | 8 |  |  |  |  | 2 |  | 10 |
| `tests/test_digital_twin_isl29125_autorange.py` | 4 | 2 |  |  |  |  |  | 6 |
| `tests/test_digital_twin_launch.py` |  |  | 4 | 4 |  | 2 |  | 10 |
| `tests/test_digital_twin_machine.py` |  |  | 16 | 14 |  | 3 |  | 33 |
| `tests/test_digital_twin_machine_uart.py` |  |  |  |  |  | 1 | 1 | 2 |
| `tests/test_digital_twin_network_neopixel.py` |  |  | 4 |  | 2 |  |  | 6 |
| `tests/test_digital_twin_poll_prewarm.py` | 2 |  |  |  |  |  |  | 2 |
| `tests/test_digital_twin_real_website_integration.py` |  |  | 1 | 9 |  | 2 |  | 12 |
| `tests/test_digital_twin_run_generic_integration.py` |  |  |  | 1 | 1 | 1 |  | 3 |
| `tests/test_digital_twin_scd30.py` | 2 |  |  |  |  | 2 |  | 4 |
| `tests/test_digital_twin_sensortask_integration.py` |  |  | 10 | 23 | 2 |  |  | 35 |
| `tests/test_digital_twin_uart_link.py` |  |  | 8 | 10 | 1 | 1 |  | 20 |
| `tests/test_fake_timer_and_network.py` |  |  |  | 5 |  |  |  | 5 |
| `tests/test_framing_codecs.py` |  |  | 1 |  |  | 1 |  | 2 |
| `tests/test_neopixel_wifi_integration.py` |  |  | 4 |  |  |  |  | 4 |
| `tests/test_notification_fram_integration.py` |  | 2 |  |  |  |  |  | 2 |
| `tests/test_notification_neopixel_integration.py` |  |  | 4 |  |  |  |  | 4 |
| `tests/test_notification_scd30_integration.py` |  |  | 4 |  |  |  |  | 4 |
| `tests/test_notification_scd30_sgp40_integration.py` | 1 |  | 2 |  |  |  |  | 3 |
| `tests/test_notification_sgp40_integration.py` | 1 |  | 3 |  |  |  |  | 4 |
| `tests/test_ntp_fram_system_integration.py` | 1 |  | 12 | 1 | 2 | 2 |  | 18 |
| `tests/test_ntp_wifi_dns_integration.py` | 1 |  | 6 | 1 | 1 |  |  | 9 |
| `tests/test_setter_microdot_integration.py` |  | 6 |  |  |  |  |  | 6 |
| `tests/test_system_service.py` |  |  | 7 |  |  | 14 |  | 21 |
| `tests/test_ticks_rollover.py` |  |  |  |  |  | 5 | 3 | 8 |
| `tests/test_uart_comm_hazard.py` | 10 | 2 | 35 | 63 |  |  |  | 110 |
| `tests/test_voc_algorithm.py` |  |  |  | 1 |  | 2 |  | 3 |
| `tests_hardware/bench/dns_probe.py` | 1 |  |  |  | 1 |  |  | 2 |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py` | 3 | 4 | 19 | 50 | 1 |  |  | 77 |
| `tests_hardware/bench/test_end_to_end_timing.py` |  |  | 21 | 31 |  |  |  | 52 |
| `tests_hardware/bench/test_heap_under_connection_ceiling.py` | 6 |  | 1 | 3 |  |  |  | 10 |
| `tests_hardware/bench/test_hotspot_role_reversal.py` |  |  | 19 | 26 | 1 |  | 1 | 47 |
| `tests_hardware/bench/test_memory_stress_bench.py` | 1 |  |  | 5 |  |  |  | 6 |
| `tests_hardware/bench/test_network_resilience.py` | 6 |  | 78 | 109 | 1 | 1 |  | 195 |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py` |  |  | 4 | 16 |  |  |  | 20 |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py` |  | 7 | 1 | 17 |  |  |  | 25 |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py` | 5 |  |  | 6 |  |  |  | 11 |
| `tests_hardware/bench/test_uart_link_under_api_load.py` | 3 |  | 6 | 12 |  |  |  | 21 |
| `tests_hardware/bench/test_wifi_networking.py` |  |  | 4 | 9 |  |  |  | 13 |
| `tests_hardware/bench_control.py` |  |  |  | 6 | 4 |  |  | 10 |
| `tests_hardware/conftest.py` |  |  | 4 | 8 |  |  |  | 12 |
| `tests_hardware/device_scripts/allocation_need_per_source.py` |  | 16 |  |  |  |  |  | 16 |
| `tests_hardware/device_scripts/bmp3xx_plausibility_read.py` |  |  | 1 | 1 |  |  |  | 2 |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py` | 2 | 6 | 2 | 1 |  |  |  | 11 |
| `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py` | 1 |  | 1 | 2 |  |  |  | 4 |
| `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py` |  | 5 | 3 | 2 |  |  |  | 10 |
| `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py` | 3 |  | 2 | 2 |  |  |  | 7 |
| `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py` |  |  | 5 | 2 |  |  |  | 7 |
| `tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py` | 1 |  |  |  |  |  |  | 1 |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py` | 1 | 14 | 2 | 1 |  |  |  | 18 |
| `tests_hardware/device_scripts/fram_busy_status_lockout.py` | 1 |  |  |  |  |  |  | 1 |
| `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py` | 2 |  | 2 | 1 |  |  |  | 5 |
| `tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py` | 2 |  |  |  |  |  |  | 2 |
| `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py` | 4 |  |  |  |  |  |  | 4 |
| `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py` | 4 | 1 |  |  |  |  |  | 5 |
| `tests_hardware/device_scripts/fram_error_log_roundtrip.py` | 2 |  |  |  |  |  |  | 2 |
| `tests_hardware/device_scripts/fram_manager_roundtrip.py` | 1 |  |  |  |  |  |  | 1 |
| `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py` | 4 |  |  | 1 |  |  |  | 5 |
| `tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py` |  |  | 1 | 1 |  |  |  | 2 |
| `tests_hardware/device_scripts/fram_reset_race_during_write_verify_recovery.py` |  |  |  | 1 |  |  |  | 1 |
| `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py` | 1 | 3 | 1 | 1 |  |  |  | 6 |
| `tests_hardware/device_scripts/fram_write_protect_roundtrip.py` | 1 |  |  |  |  |  |  | 1 |
| `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py` | 4 | 2 |  |  |  |  |  | 6 |
| `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py` | 6 | 2 | 1 |  |  |  |  | 9 |
| `tests_hardware/device_scripts/heap_under_connection_ceiling.py` | 2 |  | 1 |  |  |  |  | 3 |
| `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py` | 1 |  | 3 | 2 |  |  |  | 6 |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py` | 12 |  | 1 | 2 |  |  |  | 15 |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py` | 5 | 7 | 4 | 2 |  |  |  | 18 |
| `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py` | 2 |  |  | 2 |  |  |  | 4 |
| `tests_hardware/device_scripts/isl29125_plausibility_read.py` | 2 |  | 2 | 2 |  |  |  | 6 |
| `tests_hardware/device_scripts/isl29125_real_irq_edge.py` | 3 |  | 3 | 2 |  |  |  | 8 |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py` | 2 | 5 | 3 | 2 |  |  |  | 12 |
| `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py` | 1 |  | 1 | 1 |  |  |  | 3 |
| `tests_hardware/device_scripts/reboot_persist_read.py` | 1 | 1 |  |  |  |  |  | 2 |
| `tests_hardware/device_scripts/reboot_persist_write.py` | 1 | 1 |  |  |  |  |  | 2 |
| `tests_hardware/device_scripts/scd30_plausibility_read.py` | 1 |  | 2 | 2 |  |  |  | 5 |
| `tests_hardware/device_scripts/scd30_real_irq_edge.py` | 2 |  | 1 | 1 |  |  |  | 4 |
| `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py` | 2 |  | 3 | 2 |  |  |  | 7 |
| `tests_hardware/device_scripts/scheduler_saturation_drop.py` | 3 |  |  |  |  |  |  | 3 |
| `tests_hardware/device_scripts/serving_at_default_gc.py` | 8 |  |  |  |  |  |  | 8 |
| `tests_hardware/device_scripts/sgp40_fram_backup_restore.py` | 3 |  |  | 1 |  |  |  | 4 |
| `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py` | 1 |  | 2 | 2 |  |  |  | 5 |
| `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py` | 4 |  |  | 1 |  |  |  | 5 |
| `tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py` | 1 | 2 |  |  |  |  |  | 3 |
| `tests_hardware/device_scripts/system_debug_level_restore_after_boot_log_check.py` |  | 2 |  |  |  |  |  | 2 |
| `tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py` | 1 |  | 1 |  |  |  |  | 2 |
| `tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py` |  |  |  | 1 |  |  |  | 1 |
| `tests_hardware/device_scripts/uart_crossover_exchange.py` | 8 |  |  | 1 |  |  |  | 9 |
| `tests_hardware/device_scripts/uart_crossover_recovery.py` | 8 |  |  | 1 |  |  |  | 9 |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py` | 4 |  | 2 | 4 |  |  | 1 | 11 |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py` | 5 |  | 4 | 2 |  |  |  | 11 |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py` | 9 |  | 7 | 2 |  |  |  | 18 |
| `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py` | 3 |  | 2 | 2 |  |  |  | 7 |
| `tests_hardware/device_scripts/watchdog_starvation_reset.py` | 1 |  |  |  |  |  |  | 1 |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py` | 1 |  | 8 | 6 |  |  |  | 15 |
| `tests_hardware/device_scripts/wifi_service_reconnect_repro.py` |  |  | 2 |  |  |  | 2 | 4 |
| `tests_hardware/error_log_helpers.py` | 1 |  |  | 1 |  |  |  | 2 |
| `tests_hardware/flash/conftest.py` |  |  |  | 1 |  |  |  | 1 |
| `tests_hardware/flash/test_bus_concurrency.py` |  |  | 2 | 17 |  |  |  | 19 |
| `tests_hardware/flash/test_bus_electrical_timing.py` |  | 4 |  | 1 |  |  |  | 5 |
| `tests_hardware/flash/test_fram_storage.py` |  |  | 2 | 12 |  |  |  | 14 |
| `tests_hardware/flash/test_memory_stress.py` | 1 |  |  | 1 |  |  |  | 2 |
| `tests_hardware/flash/test_reboot_persistence.py` |  |  | 4 | 5 |  |  |  | 9 |
| `tests_hardware/flash/test_sensor_accuracy.py` |  |  |  | 7 |  |  |  | 7 |
| `tests_hardware/flash/test_task_supervisor.py` |  |  |  | 1 |  |  |  | 1 |
| `tests_hardware/flash/test_toolchain_flash_boot.py` |  |  | 3 | 5 |  |  |  | 8 |
| `tests_hardware/flash/test_uart_crossover.py` |  |  |  | 6 |  |  |  | 6 |
| `tests_hardware/flash/test_watchdog_starvation.py` | 1 |  | 12 | 14 |  | 2 |  | 29 |
| `tests_hardware/harness.py` | 1 |  | 7 | 12 | 10 |  | 4 | 34 |
| `tests_hardware/heap_map.py` | 1 |  |  |  |  |  |  | 1 |
| `tests_hardware/http_client.py` |  |  |  |  | 1 |  |  | 1 |
| `tests_hardware/isl29125_conformance.py` |  |  |  |  | 1 |  |  | 1 |
| `tests_hardware/manual/manual_bus_electrical.py` |  |  |  | 2 |  |  |  | 2 |
| `tests_hardware/manual/manual_sensor_accuracy.py` | 5 |  |  |  |  |  |  | 5 |
| `tests_hardware/manual/manual_toolchain.py` |  |  |  | 2 |  |  |  | 2 |
| `tests_hardware/manual/runner.py` |  |  | 1 |  |  |  |  | 1 |
| `tests_hardware/ntp_probe.py` | 1 |  |  |  |  |  |  | 1 |
| `tests_hardware/rogue_udp_responder.py` |  |  | 1 | 1 |  |  |  | 2 |
| `tests_hardware/soak_tiers.py` |  | 4 |  |  |  |  |  | 4 |


## How the classification was done

Every hit was opened in its source context (the enclosing function, and where the value is consumed) at HEAD;
nothing was classified by name alone. Whether a sleep is real or patched was checked per file (`asyncio.sleep`/
`sleep_ms` monkeypatches, fake timers, fake clocks). The C.0.2 order was applied: not tagged (identifier / fact /
contract, plus "API domain", "config" and "derived" as named in U8's N.1 class list) → mirror → test input → tuned.
Readings made where C.0.2 is silent, applied the same way everywhere:
- A timeout passed to the code under test and **waited out in full** (a no-reply case, a deadlock bound) is tuned:
  it is a real-clock wait, and it counts against the per-file timeout (`runner.per_file_timeout_s`), so host
  load can fail the file. "Test input" is kept for values never waited out (C.0.2 item 3's own wording).
- A literal passed to a fake that the case then **never waits on** (a `tries=1` that selects the single-attempt
  path, a lock holder's `sleep(10)` the test cancels, a period given to a fake `Timer`) is test input.
- A value restating an **API domain** (a REST field's range, a `_VAL_*` schema tuple the test copies because the
  product's is compiled away) is not tagged: API domains are not tunables (N.1), even when the test says
  "mirrors".
- A fixed readiness sleep in an `l2.` file is "deferred U25", in an `l3.`/`l4.` file "deferred U26" (C.0.2
  "Deferred"); a fixed sleep in an `l1.` file is tuned (no unit defers it). Poll steps inside a polling loop
  are tuned, never deferred.
- Cross-file IDs: one ID only where the same test or the same instrument is duplicated across files (the
  comment says so, or the code is a copy); the ID takes the stem of the file that holds the original.
- Constant names are proposals checked against each file for collisions; values never change in this unit
  (OR30.a (3): a stale value is corrected with its measurement).


## Status

Classified files: 156 of 156 (hits 2265 of 2265; files NOT-DONE: none). Verdicts: deferred U25 13, deferred U26 14, mirror 84, not tagged 351, test input 298, tuned 1505. IDs: 576 new tuned test-tier IDs, 18 existing U8 IDs that gain sites here, 28 product IDs mirrored, 20 provisional IDs for deferred sleeps. Actions: 119 (A.U8C.01-A.U8C.119, one per file holding a tuned, mirror or deferred hit; files whose hits are all not-tagged or test input need no action and appear only in the table).


## Actions

### A.U8C.01 Tag the tuned literals of `_boot_contiguity_probe.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits; G4/R54 "allocation and heap-rate budgets" (the probe's bounds pace a heap measurement)
- **Site**: `tests/_boot_contiguity_probe.py` — `l3.heap_layout_after_full_boot_sequence_starter_loop_timeout_ms` :36 (20000); `l3.heap_layout_after_full_boot_sequence_starter_loop_grace_ms` :37 (250); `l3.heap_layout_after_full_boot_sequence_timers_timeout_s` :38 (15); `l3.heap_layout_after_full_boot_sequence_starter_poll_ms` :106 (20)
- **Change**: tag `# @tunable l3.heap_layout_after_full_boot_sequence_starter_loop_timeout_ms = 20000` above `_STARTER_LOOP_TIMEOUT_MS` (:36); tag `# @tunable l3.heap_layout_after_full_boot_sequence_starter_loop_grace_ms = 250` above `_STARTER_LOOP_GRACE_MS` (:37); tag `# @tunable l3.heap_layout_after_full_boot_sequence_timers_timeout_s = 15` above `_TIMERS_TIMEOUT_S` (:38); `_STARTER_POLL_MS = 20` (new, module level) tagged `# @tunable l3.heap_layout_after_full_boot_sequence_starter_poll_ms = 20`; the literal at :106 becomes `_STARTER_POLL_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers the probe is executed by `tests_scripts/test_digital_twin_boot_contiguity.py:33` (whose own `_PROBE_TIMEOUT_S` is A.U8.22's) and parsed by `tests_scripts/test_heap_map_parser.py:200`; neither reads these constants (grep) · generated — · js — · tests — · twin — · docs SPEC Part N: the four IDs are shared with `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:32, :35, :38, :190`, which the comment `:34-35` says these mirror, so the two tiers keep measuring at the same positions · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.02 Tag the tuned literals of `_digital_twin_construction_scenarios.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits; G8/R31; G7/R23 (readiness sleeps deferred to U25)
- **Site**: `tests/_digital_twin_construction_scenarios.py` — `l2.construction_scenarios_run_timeout_s` :131, :160, :203 (10.0); deferred U25: `:147` (1.0); deferred U25: `:193` (1.0)
- **Change**: `_RUN_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l2.construction_scenarios_run_timeout_s = 10.0`; each literal at :131, :160, :203 becomes `_RUN_TIMEOUT_S`; deferred sleeps (:147, :193): no tag now; classified once U25 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run by the six `tests/test_digital_twin_construction_<device>.py` files through `register_for_device` (grep) · generated — · js — · tests those six files · twin — · docs SPEC Part N rows · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, U25
- **Kind**: test

### A.U8C.03 Tag the tuned literals of `_uart_comm_harness.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits; G8/R31 (run() is the UART tests' per-test bound)
- **Site**: `tests/_uart_comm_harness.py` — `l1.uart_comm_harness_timeout_ms` :33 (100); `l1.uart_comm_harness_poll_wait_ms` :34 (1); `l1.uart_comm_harness_run_limit_s` :37 (10); `l1.uart_comm_harness_listener_drain_s` :103 (5)
- **Change**: tag `# @tunable l1.uart_comm_harness_timeout_ms = 100` above `TIMEOUT_MS` (:33); tag `# @tunable l1.uart_comm_harness_poll_wait_ms = 1` above `POLL_WAIT_MS` (:34); `_RUN_LIMIT_S = 10` (new, module level) tagged `# @tunable l1.uart_comm_harness_run_limit_s = 10`; the literal at :37 becomes `_RUN_LIMIT_S`; `_LISTENER_DRAIN_S = 5` (new, module level) tagged `# @tunable l1.uart_comm_harness_listener_drain_s = 5`; the literal at :103 becomes `_LISTENER_DRAIN_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers `run()`, `TIMEOUT_MS` are imported by `tests/test_asy_uart_comm.py:8`, `run()` by `tests/test_uart_comm_hazard.py:7`; after A.U8C actions for those files and for `tests/test_asy_uart_link_driver.py` (which today restates `PAYLOAD_SIZE`/`TIMEOUT_MS`/`POLL_WAIT_MS`/`run(limit=10)`/`wait_for(listener, 5)` at `:24-29, :58`), `POLL_WAIT_MS`, `_RUN_LIMIT_S`, `_LISTENER_DRAIN_S` are imported too, so this file holds the only tags · generated — · js — · tests the importers (behaviour unchanged) · twin — · docs SPEC Part N rows · toml — · uart — (test harness, no protocol change)
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.04 Tag the tuned literals of `_webserver_concurrency_scenarios.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits; G8/R31; G7/R23 (the deferred readiness sleeps, `:128-140` named in its State)
- **Site**: `tests/_webserver_concurrency_scenarios.py` — `web.max_content_length` :105 (2048); `l2.webserver_concurrency_scenarios_flaky_hold_s` :168 (0.05); `l2.webserver_concurrency_scenarios_still_serving_timeout_s` :174 (5.0); `l2.webserver_concurrency_scenarios_request_timeout_s` :181 (2.0); `l2.webserver_concurrency_scenarios_still_serving_poll_s` :187 (0.1); `l2.webserver_concurrency_scenarios_drain_timeout_s` :190 (10.0); `l2.webserver_concurrency_scenarios_drain_poll_s` :201 (0.05); `l2.webserver_concurrency_scenarios_health_check_interval_s` :470 (0.25); `l2.webserver_concurrency_scenarios_health_check_timeout_s` :471 (3.0); `l2.webserver_concurrency_scenarios_reclaim_timeout_s` :543 (20.0); `l2.webserver_concurrency_scenarios_served_elapsed_max_ms` :678 (10000); `l2.webserver_concurrency_scenarios_loop_stall_ms` :740 (200); deferred U25: `:140` (0.5); deferred U25: `:495` (0.3); deferred U25: `:532` (0.2); deferred U25: `:741` (0.5)
- **Change**: mirror tag `# @tunable web.max_content_length = 2048` above :105; listed as a further site of that row; `_FLAKY_HOLD_S = 0.05` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_flaky_hold_s = 0.05`; the literal at :168 becomes `_FLAKY_HOLD_S`; `_STILL_SERVING_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_still_serving_timeout_s = 5.0`; the literal at :174 becomes `_STILL_SERVING_TIMEOUT_S`; `_REQUEST_TIMEOUT_S = 2.0` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_request_timeout_s = 2.0`; the literal at :181 becomes `_REQUEST_TIMEOUT_S`; `_STILL_SERVING_POLL_S = 0.1` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_still_serving_poll_s = 0.1`; the literal at :187 becomes `_STILL_SERVING_POLL_S`; `_DRAIN_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_drain_timeout_s = 10.0`; the literal at :190 becomes `_DRAIN_TIMEOUT_S`; `_DRAIN_POLL_S = 0.05` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_drain_poll_s = 0.05`; the literal at :201 becomes `_DRAIN_POLL_S`; `_HEALTH_CHECK_INTERVAL_S = 0.25` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_health_check_interval_s = 0.25`; the literal at :470 becomes `_HEALTH_CHECK_INTERVAL_S`; `_HEALTH_CHECK_TIMEOUT_S = 3.0` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_health_check_timeout_s = 3.0`; the literal at :471 becomes `_HEALTH_CHECK_TIMEOUT_S`; `_RECLAIM_TIMEOUT_S = 20.0` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_reclaim_timeout_s = 20.0`; the literal at :543 becomes `_RECLAIM_TIMEOUT_S`; `_SERVED_ELAPSED_MAX_MS = 10000` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_served_elapsed_max_ms = 10000`; the literal at :678 becomes `_SERVED_ELAPSED_MAX_MS`; `_LOOP_STALL_MS = 200` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_loop_stall_ms = 200`; the literal at :740 becomes `_LOOP_STALL_MS`; deferred sleeps (:140, :495, :532, :741): no tag now; classified once U25 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table; search gap recorded under "Search gaps", not classified here: the 20 per-scenario budgets passed positionally to `_register(name, timeout_s)` (`:277-790`) are hang bounds C.0.1 does not see. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers the scenario library is run by the six `tests/test_digital_twin_webserver_concurrency_<device>.py` files through `register_for_device` (grep) · generated — · js — · tests those six files (behaviour unchanged) · twin — · docs SPEC Part N rows; `l2.webserver_concurrency_scenarios_reclaim_timeout_s` names `web.outer_cap_s` as its source in Dependants (SPEC H.7.1) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.04, U25
- **Kind**: test

### A.U8C.05 Tag the tuned literals of `test_asy_bmp3xx_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_bmp3xx_driver.py` — `l1.asy_bmp3xx_driver_event_wait_s` :1808, :1879 (1)
- **Change**: `_EVENT_WAIT_S = 1` (new, module level) tagged `# @tunable l1.asy_bmp3xx_driver_event_wait_s = 1`; each literal at :1808, :1879 becomes `_EVENT_WAIT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.06 Tag the tuned literals of `test_asy_dns_client.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_dns_client.py` — `udp.conn_tries_default` :57, :548 (1); `l1.asy_dns_client_prompt_return_max_ms` :332 (200); `l1.asy_dns_client_fake_server_wait_ms` :349 (2000); `l1.asy_dns_client_fake_server_poll_ms` :371 (5); `l1.asy_dns_client_reply_timeout_ms` :389, :587 (1000); `l1.asy_dns_client_no_reply_timeout_ms` :402, :509 (100); `l1.asy_dns_client_bad_reply_timeout_ms` :414, :433 (300); `l1.asy_dns_client_fallback_timeout_ms` :456, :487 (200); `l1.asy_dns_client_cname_reply_timeout_ms` :611 (500)
- **Change**: mirror tag `# @tunable udp.conn_tries_default = 1` above :57, :548; listed as a further site of that row; `_PROMPT_RETURN_MAX_MS = 200` (new, module level) tagged `# @tunable l1.asy_dns_client_prompt_return_max_ms = 200`; the literal at :332 becomes `_PROMPT_RETURN_MAX_MS`; `_FAKE_SERVER_WAIT_MS = 2000` (new, module level) tagged `# @tunable l1.asy_dns_client_fake_server_wait_ms = 2000`; the literal at :349 becomes `_FAKE_SERVER_WAIT_MS`; `_FAKE_SERVER_POLL_MS = 5` (new, module level) tagged `# @tunable l1.asy_dns_client_fake_server_poll_ms = 5`; the literal at :371 becomes `_FAKE_SERVER_POLL_MS`; `_REPLY_TIMEOUT_MS = 1000` (new, module level) tagged `# @tunable l1.asy_dns_client_reply_timeout_ms = 1000`; each literal at :389, :587 becomes `_REPLY_TIMEOUT_MS`; `_NO_REPLY_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l1.asy_dns_client_no_reply_timeout_ms = 100`; each literal at :402, :509 becomes `_NO_REPLY_TIMEOUT_MS`; `_BAD_REPLY_TIMEOUT_MS = 300` (new, module level) tagged `# @tunable l1.asy_dns_client_bad_reply_timeout_ms = 300`; each literal at :414, :433 becomes `_BAD_REPLY_TIMEOUT_MS`; `_FALLBACK_TIMEOUT_MS = 200` (new, module level) tagged `# @tunable l1.asy_dns_client_fallback_timeout_ms = 200`; each literal at :456, :487 becomes `_FALLBACK_TIMEOUT_MS`; `_CNAME_REPLY_TIMEOUT_MS = 500` (new, module level) tagged `# @tunable l1.asy_dns_client_cname_reply_timeout_ms = 500`; the literal at :611 becomes `_CNAME_REPLY_TIMEOUT_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.11
- **Kind**: test

### A.U8C.07 Tag the tuned literals of `test_asy_fram_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_fram_driver.py` — `l1.asy_fram_driver_lock_wait_s` :1374 (1.0)
- **Change**: `_LOCK_WAIT_S = 1.0` (new, module level) tagged `# @tunable l1.asy_fram_driver_lock_wait_s = 1.0`; the literal at :1374 becomes `_LOCK_WAIT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.08 Tag the tuned literals of `test_asy_fram_manager.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_fram_manager.py` — `l1.asy_fram_manager_read_wait_s` :751 (5)
- **Change**: `_READ_WAIT_S = 5` (new, module level) tagged `# @tunable l1.asy_fram_manager_read_wait_s = 5`; the literal at :751 becomes `_READ_WAIT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.09 Tag the tuned literals of `test_asy_i2c_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_i2c_driver.py` — `l1.asy_i2c_driver_gather_wait_s` :719 (1.0); `l1.asy_i2c_driver_deadlock_wait_s` :843 (0.2)
- **Change**: `_GATHER_WAIT_S = 1.0` (new, module level) tagged `# @tunable l1.asy_i2c_driver_gather_wait_s = 1.0`; the literal at :719 becomes `_GATHER_WAIT_S`; `_DEADLOCK_WAIT_S = 0.2` (new, module level) tagged `# @tunable l1.asy_i2c_driver_deadlock_wait_s = 0.2`; the literal at :843 becomes `_DEADLOCK_WAIT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_asy_spi_driver.py`, `tests/test_asy_uart_driver.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.10 Tag the mirrored product values in `test_asy_isl29125_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_isl29125_driver.py` — `isl29125.gain_ratio_min` :39 (20.0); `isl29125.gain_ratio_max` :40 (34.0); `isl29125.cal_converge_n` :42 (3)
- **Change**: mirror tag `# @tunable isl29125.gain_ratio_min = 20.0` above :39; listed as a further site of that row; mirror tag `# @tunable isl29125.gain_ratio_max = 34.0` above :40; listed as a further site of that row; mirror tag `# @tunable isl29125.cal_converge_n = 3` above :42; listed as a further site of that row. Rows: no new row; each mirror is a further site in its product row.
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.13
- **Kind**: test

### A.U8C.11 Tag the tuned literals of `test_asy_neopixel_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_neopixel_driver.py` — `l1.asy_neopixel_driver_overlay_settle_s` :88, :101, :103, :116, :130, :132, :146, :149, :206, :641 (0.05); `l1.asy_neopixel_driver_mid_ramp_s` :167, :361, :434, :437 (0.02); `l1.asy_neopixel_driver_ramp_and_restore_s` :172 (0.2); `l1.asy_neopixel_driver_signal_done_s` :191, :208, :222, :272, :325, :380, :520, :556, :579, :594, :609, :626 (0.15); `l1.asy_neopixel_driver_queued_signals_done_s` :238, :259, :416, :439 (0.3); `l1.asy_neopixel_driver_low_freq_signal_done_s` :290 (1.5); `l1.asy_neopixel_driver_one_s_signal_done_s` :305 (1.1); `l1.asy_neopixel_driver_long_and_short_ramp_done_s` :366 (0.6); `l1.asy_neopixel_driver_long_signal_done_s` :395 (1.6)
- **Change**: `_OVERLAY_SETTLE_S = 0.05` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_overlay_settle_s = 0.05`; each literal at :88, :101, :103, :116, :130, :132, :146, :149, :206, :641 becomes `_OVERLAY_SETTLE_S`; `_MID_RAMP_S = 0.02` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_mid_ramp_s = 0.02`; each literal at :167, :361, :434, :437 becomes `_MID_RAMP_S`; `_RAMP_AND_RESTORE_S = 0.2` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_ramp_and_restore_s = 0.2`; the literal at :172 becomes `_RAMP_AND_RESTORE_S`; `_SIGNAL_DONE_S = 0.15` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_signal_done_s = 0.15`; each literal at :191, :208, :222, :272, :325, :380, :520, :556, :579, :594, :609, :626 becomes `_SIGNAL_DONE_S`; `_QUEUED_SIGNALS_DONE_S = 0.3` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_queued_signals_done_s = 0.3`; each literal at :238, :259, :416, :439 becomes `_QUEUED_SIGNALS_DONE_S`; `_LOW_FREQ_SIGNAL_DONE_S = 1.5` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_low_freq_signal_done_s = 1.5`; the literal at :290 becomes `_LOW_FREQ_SIGNAL_DONE_S`; `_ONE_S_SIGNAL_DONE_S = 1.1` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_one_s_signal_done_s = 1.1`; the literal at :305 becomes `_ONE_S_SIGNAL_DONE_S`; `_LONG_AND_SHORT_RAMP_DONE_S = 0.6` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_long_and_short_ramp_done_s = 0.6`; the literal at :366 becomes `_LONG_AND_SHORT_RAMP_DONE_S`; `_LONG_SIGNAL_DONE_S = 1.6` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_long_signal_done_s = 1.6`; the literal at :395 becomes `_LONG_SIGNAL_DONE_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_neopixel_wifi_integration.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.12 Tag the tuned literals of `test_asy_notification_service.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_notification_service.py` — `l1.asy_notification_service_cycle_wait_s` :138, :1245, :1296 (0.1); `l1.asy_notification_service_three_flash_cycle_s` :912, :982 (3.5); `l1.asy_notification_service_one_flash_cycle_s` :933, :958 (1.2); `l1.asy_notification_service_task_start_settle_s` :1005, :1147, :1184, :1192 (0.05); `l1.asy_notification_service_one_flash_settle_s` :1008 (1.3); `l1.asy_notification_service_override_tick_s` :1153, :1155, :1186 (1.1); `l1.asy_notification_service_elapsed_stimulus_ms` :1266 (50); `l1.asy_notification_service_two_flash_cycle_s` :1322 (2.5)
- **Change**: `_CYCLE_WAIT_S = 0.1` (new, module level) tagged `# @tunable l1.asy_notification_service_cycle_wait_s = 0.1`; each literal at :138, :1245, :1296 becomes `_CYCLE_WAIT_S`; `_THREE_FLASH_CYCLE_S = 3.5` (new, module level) tagged `# @tunable l1.asy_notification_service_three_flash_cycle_s = 3.5`; each literal at :912, :982 becomes `_THREE_FLASH_CYCLE_S`; `_ONE_FLASH_CYCLE_S = 1.2` (new, module level) tagged `# @tunable l1.asy_notification_service_one_flash_cycle_s = 1.2`; each literal at :933, :958 becomes `_ONE_FLASH_CYCLE_S`; `_TASK_START_SETTLE_S = 0.05` (new, module level) tagged `# @tunable l1.asy_notification_service_task_start_settle_s = 0.05`; each literal at :1005, :1147, :1184, :1192 becomes `_TASK_START_SETTLE_S`; `_ONE_FLASH_SETTLE_S = 1.3` (new, module level) tagged `# @tunable l1.asy_notification_service_one_flash_settle_s = 1.3`; the literal at :1008 becomes `_ONE_FLASH_SETTLE_S`; `_OVERRIDE_TICK_S = 1.1` (new, module level) tagged `# @tunable l1.asy_notification_service_override_tick_s = 1.1`; each literal at :1153, :1155, :1186 becomes `_OVERRIDE_TICK_S`; `_ELAPSED_STIMULUS_MS = 50` (new, module level) tagged `# @tunable l1.asy_notification_service_elapsed_stimulus_ms = 50`; the literal at :1266 becomes `_ELAPSED_STIMULUS_MS`; `_TWO_FLASH_CYCLE_S = 2.5` (new, module level) tagged `# @tunable l1.asy_notification_service_two_flash_cycle_s = 2.5`; the literal at :1322 becomes `_TWO_FLASH_CYCLE_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_notification_neopixel_integration.py`, `tests/test_notification_scd30_integration.py`, `tests/test_notification_scd30_sgp40_integration.py`, `tests/test_notification_sgp40_integration.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.13 Tag the tuned literals of `test_asy_ntp_client.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_ntp_client.py` — `dns.timeout_ms` :73 (500); `dns.tries` :74 (1); `ntp.fetch_timeout_ms` :75 (5000); `ntp.retry_s_default` :76 (10); `ntp.retry_max_s_default` :77 (600); `ntp.check_interval_s` :517 (10/1000); `l1.asy_ntp_client_event_wait_s` :527, :607, :1186, :1275, :1326, :1350, :1844 (0.2); `udp.conn_tries_default` :871, :2072 (1); `udp.round_trip_tries_default` :876 (1); `l1.asy_ntp_client_fake_server_poll_ms` :936, :940, :2113, :2118 (10); `ntp.retry_interval_s` :1175 (1000/15); `l1.asy_ntp_client_fired_probe_s` :1296, :2446 (0.05); `l1.asy_ntp_client_serve_wait_s` :2140, :2190, :2228, :2242, :2487, :2519 (5); `l1.asy_ntp_client_state_poll_ms` :2144, :2219, :2237 (20); `l1.asy_ntp_client_no_answer_wait_s` :2167 (1); `l1.asy_ntp_client_reply_process_s` :2191 (0.2); `l1.asy_ntp_client_no_reply_fetch_timeout_ms` :2366 (100); `l1.asy_ntp_client_past_fetch_timeout_ms` :2488 (200)
- **Change**: mirror tag `# @tunable dns.timeout_ms = 500` above :73; listed as a further site of that row; mirror tag `# @tunable dns.tries = 1` above :74; listed as a further site of that row; mirror tag `# @tunable ntp.fetch_timeout_ms = 5000` above :75; listed as a further site of that row; mirror tag `# @tunable ntp.retry_s_default = 10` above :76; listed as a further site of that row; mirror tag `# @tunable ntp.retry_max_s_default = 600` above :77; listed as a further site of that row; mirror `ntp.check_interval_s` at :517: already named by A.U8.09; it gets the tag there; `_EVENT_WAIT_S = 0.2` (new, module level) tagged `# @tunable l1.asy_ntp_client_event_wait_s = 0.2`; each literal at :527, :607, :1186, :1275, :1326, :1350, :1844 becomes `_EVENT_WAIT_S`; mirror tag `# @tunable udp.conn_tries_default = 1` above :871, :2072; listed as a further site of that row; mirror tag `# @tunable udp.round_trip_tries_default = 1` above :876; listed as a further site of that row; `_FAKE_SERVER_POLL_MS = 10` (new, module level) tagged `# @tunable l1.asy_ntp_client_fake_server_poll_ms = 10`; each literal at :936, :940, :2113, :2118 becomes `_FAKE_SERVER_POLL_MS`; mirror `ntp.retry_interval_s` at :1175: already named by A.U8.09; it gets the tag there; `_FIRED_PROBE_S = 0.05` (new, module level) tagged `# @tunable l1.asy_ntp_client_fired_probe_s = 0.05`; each literal at :1296, :2446 becomes `_FIRED_PROBE_S`; `_SERVE_WAIT_S = 5` (new, module level) tagged `# @tunable l1.asy_ntp_client_serve_wait_s = 5`; each literal at :2140, :2190, :2228, :2242, :2487, :2519 becomes `_SERVE_WAIT_S`; `_STATE_POLL_MS = 20` (new, module level) tagged `# @tunable l1.asy_ntp_client_state_poll_ms = 20`; each literal at :2144, :2219, :2237 becomes `_STATE_POLL_MS`; `_NO_ANSWER_WAIT_S = 1` (new, module level) tagged `# @tunable l1.asy_ntp_client_no_answer_wait_s = 1`; the literal at :2167 becomes `_NO_ANSWER_WAIT_S`; `_REPLY_PROCESS_S = 0.2` (new, module level) tagged `# @tunable l1.asy_ntp_client_reply_process_s = 0.2`; the literal at :2191 becomes `_REPLY_PROCESS_S`; `_NO_REPLY_FETCH_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l1.asy_ntp_client_no_reply_fetch_timeout_ms = 100`; the literal at :2366 becomes `_NO_REPLY_FETCH_TIMEOUT_MS`; `_PAST_FETCH_TIMEOUT_MS = 200` (new, module level) tagged `# @tunable l1.asy_ntp_client_past_fetch_timeout_ms = 200`; the literal at :2488 becomes `_PAST_FETCH_TIMEOUT_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_ntp_fram_system_integration.py`, `tests/test_ntp_wifi_dns_integration.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.09, A.U8.11
- **Kind**: test

### A.U8C.14 Tag the tuned literals of `test_asy_scd30_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_scd30_driver.py` — `scd30.start_trigger_period_ms` :652 (500); `l1.asy_scd30_driver_event_wait_s` :660, :661, :689, :745 (1)
- **Change**: mirror tag `# @tunable scd30.start_trigger_period_ms = 500` above :652; listed as a further site of that row; `_EVENT_WAIT_S = 1` (new, module level) tagged `# @tunable l1.asy_scd30_driver_event_wait_s = 1`; each literal at :660, :661, :689, :745 becomes `_EVENT_WAIT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.07
- **Kind**: test

### A.U8C.15 Tag the tuned literals of `test_asy_sgp40_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_sgp40_driver.py` — `l1.asy_sgp40_driver_event_wait_s` :539 (1)
- **Change**: `_EVENT_WAIT_S = 1` (new, module level) tagged `# @tunable l1.asy_sgp40_driver_event_wait_s = 1`; the literal at :539 becomes `_EVENT_WAIT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.16 Tag the tuned literals of `test_asy_spi_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_spi_driver.py` — `l1.asy_i2c_driver_gather_wait_s` :655 (1.0); `l1.asy_i2c_driver_deadlock_wait_s` :831 (0.2)
- **Change**: `_GATHER_WAIT_S = 1.0` (new, module level) tagged `# @tunable l1.asy_i2c_driver_gather_wait_s = 1.0`; the literal at :655 becomes `_GATHER_WAIT_S`; `_DEADLOCK_WAIT_S = 0.2` (new, module level) tagged `# @tunable l1.asy_i2c_driver_deadlock_wait_s = 0.2`; the literal at :831 becomes `_DEADLOCK_WAIT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_asy_i2c_driver.py`, `tests/test_asy_uart_driver.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.09
- **Kind**: test

### A.U8C.17 Tag the tuned literals of `test_asy_uart_comm.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits; G8/R31 (every async test body bounded; the `limit=`/`wait_for` bounds are this file's)
- **Site**: `tests/test_asy_uart_comm.py` — `l1.uart_comm_harness_poll_wait_ms` :57, :82, :145, :156, :160, :177, :183 (1); `l1.asy_uart_comm_short_reply_timeout_ms` :267, :1645, :1661, :1680, :1725, :1751, :1770, :1836, :1854, :1871, :1897, :1987, :2018 (30); `l1.asy_uart_comm_step_bound_s` :269, :272, :450, :719, :777, :793, :815, :833, :850, :871, :886, :916, :926, :1106, :1158, :1173, :1196, :1284, :1651, :1667, :1686, :1758, :1877, :1903, :1990, :1994, :1997 (10); `l1.asy_uart_comm_loop_survival_wait_ms` :445 (20); `l1.asy_uart_comm_silent_bound_s` :683, :691, :894, :895, :896, :897, :1004, :1977 (15); `l1.asy_uart_comm_listener_run_bound_s` :721, :1015, :1055, :1108, :1161, :1176, :1199, :1286, :1653, :1669, :1689, :1729, :1760, :1780, :1839, :1857, :1880, :1906, :2032, :2151 (25); `l1.asy_uart_comm_short_bound_s` :736, :1033 (5); `l1.asy_uart_comm_past_deadline_bound_s` :756 (2); `l1.asy_uart_comm_flood_step_ms` :787, :809, :845 (1); `l1.asy_uart_comm_run_bound_s` :798, :820, :855, :919, :949, :952, :1037, :1252, :1312, :1321, :1330, :1349, :1373, :1375, :1434, :1465, :1481, :1482, :1486, :1488, :1503, :1536, :1562, :1624, :1637, :1937, :2142, :2155 (20); `l1.asy_uart_comm_listener_park_ms` :915 (10); `l1.asy_uart_comm_inside_lock_ms` :945, :1961 (5); `l1.asy_uart_comm_listener_short_bound_s` :1052, :2148 (8); `l1.asy_uart_comm_async_callback_yield_ms` :1126 (1); `l1.asy_uart_comm_bsec_run_bound_s` :2120 (60)
- **Change**: the literal at :57, :82, :145, :156, :160, :177, :183 is replaced by `POLL_WAIT_MS`, imported from the file that holds `l1.uart_comm_harness_poll_wait_ms`'s tag (no tag here: an import is not a restatement); `_SHORT_REPLY_TIMEOUT_MS = 30` (new, module level) tagged `# @tunable l1.asy_uart_comm_short_reply_timeout_ms = 30`; each literal at :267, :1645, :1661, :1680, :1725, :1751, :1770, :1836, :1854, :1871, :1897, :1987, :2018 becomes `_SHORT_REPLY_TIMEOUT_MS`; `_STEP_BOUND_S = 10` (new, module level) tagged `# @tunable l1.asy_uart_comm_step_bound_s = 10`; each literal at :269, :272, :450, :719, :777, :793, :815, :833, :850, :871, :886, :916, :926, :1106, :1158, :1173, :1196, :1284, :1651, :1667, :1686, :1758, :1877, :1903, :1990, :1994, :1997 becomes `_STEP_BOUND_S`; `_LOOP_SURVIVAL_WAIT_MS = 20` (new, module level) tagged `# @tunable l1.asy_uart_comm_loop_survival_wait_ms = 20`; the literal at :445 becomes `_LOOP_SURVIVAL_WAIT_MS`; `_SILENT_BOUND_S = 15` (new, module level) tagged `# @tunable l1.asy_uart_comm_silent_bound_s = 15`; each literal at :683, :691, :894, :895, :896, :897, :1004, :1977 becomes `_SILENT_BOUND_S`; `_LISTENER_RUN_BOUND_S = 25` (new, module level) tagged `# @tunable l1.asy_uart_comm_listener_run_bound_s = 25`; each literal at :721, :1015, :1055, :1108, :1161, :1176, :1199, :1286, :1653, :1669, :1689, :1729, :1760, :1780, :1839, :1857, :1880, :1906, :2032, :2151 becomes `_LISTENER_RUN_BOUND_S`; `_SHORT_BOUND_S = 5` (new, module level) tagged `# @tunable l1.asy_uart_comm_short_bound_s = 5`; each literal at :736, :1033 becomes `_SHORT_BOUND_S`; `_PAST_DEADLINE_BOUND_S = 2` (new, module level) tagged `# @tunable l1.asy_uart_comm_past_deadline_bound_s = 2`; the literal at :756 becomes `_PAST_DEADLINE_BOUND_S`; `_FLOOD_STEP_MS = 1` (new, module level) tagged `# @tunable l1.asy_uart_comm_flood_step_ms = 1`; each literal at :787, :809, :845 becomes `_FLOOD_STEP_MS`; `_RUN_BOUND_S = 20` (new, module level) tagged `# @tunable l1.asy_uart_comm_run_bound_s = 20`; each literal at :798, :820, :855, :919, :949, :952, :1037, :1252, :1312, :1321, :1330, :1349, :1373, :1375, :1434, :1465, :1481, :1482, :1486, :1488, :1503, :1536, :1562, :1624, :1637, :1937, :2142, :2155 becomes `_RUN_BOUND_S`; `_LISTENER_PARK_MS = 10` (new, module level) tagged `# @tunable l1.asy_uart_comm_listener_park_ms = 10`; the literal at :915 becomes `_LISTENER_PARK_MS`; `_INSIDE_LOCK_MS = 5` (new, module level) tagged `# @tunable l1.asy_uart_comm_inside_lock_ms = 5`; each literal at :945, :1961 becomes `_INSIDE_LOCK_MS`; `_LISTENER_SHORT_BOUND_S = 8` (new, module level) tagged `# @tunable l1.asy_uart_comm_listener_short_bound_s = 8`; each literal at :1052, :2148 becomes `_LISTENER_SHORT_BOUND_S`; `_ASYNC_CALLBACK_YIELD_MS = 1` (new, module level) tagged `# @tunable l1.asy_uart_comm_async_callback_yield_ms = 1`; the literal at :1126 becomes `_ASYNC_CALLBACK_YIELD_MS`; `_BSEC_RUN_BOUND_S = 60` (new, module level) tagged `# @tunable l1.asy_uart_comm_bsec_run_bound_s = 60`; the literal at :2120 becomes `_BSEC_RUN_BOUND_S`; `from _uart_comm_harness import …` (`:8`) gains `POLL_WAIT_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — · generated — · js — · tests this file only (behaviour unchanged) · twin — · docs SPEC Part N rows · toml — · uart — (test-only constants: no `UART_C_PORT_CHANGELOG.md` entry, no wire or Python-internal protocol change)
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.03
- **Kind**: test

### A.U8C.18 Tag the tuned literals of `test_asy_uart_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_uart_driver.py` — `l1.asy_uart_driver_run_bound_s` :27 (5); `l1.asy_uart_driver_data_timeout_ms` :365, :388, :500, :502, :579, :593, :607, :636, :645, :656, :667, :960, :1053, :1079, :1499, :1523, :1661, :1686, :1708, :1799, :1852 (200); `l1.asy_uart_driver_no_data_timeout_ms` :371, :875 (20); `l1.asy_uart_driver_task_inside_ms` :417, :711, :736, :757, :780, :803, :825, :1144 (5); `l1.asy_uart_driver_step_bound_s` :419, :712, :713, :737, :738, :760, :761, :781, :783, :804, :806, :826, :827, :1146 (2); `l1.asy_uart_driver_no_delimiter_timeout_ms` :619 (100); `l1.asy_uart_driver_locked_work_ms` :706, :730 (30); `l1.asy_uart_driver_wedged_hold_ms` :799 (400); `l1.asy_uart_driver_short_cancel_ack_ms` :804 (50); `l1.asy_uart_driver_holder_work_ms` :821 (20); `l1.asy_uart_driver_cancel_ack_ms` :826 (500); `l1.asy_uart_driver_ready_timeout_ms` :846, :1574 (100); `l1.asy_i2c_driver_deadlock_wait_s` :1372 (0.2); `l1.asy_uart_driver_poll_wait_ms` :1591, :1595, :1650, :1677, :1791 (1); `l1.asy_uart_driver_idle_poll_ms` :1591, :1595 (40); `l1.asy_uart_driver_silent_line_timeout_ms` :1809, :1810, :1880 (30)
- **Change**: `_RUN_BOUND_S = 5` (new, module level) tagged `# @tunable l1.asy_uart_driver_run_bound_s = 5`; the literal at :27 becomes `_RUN_BOUND_S`; `_DATA_TIMEOUT_MS = 200` (new, module level) tagged `# @tunable l1.asy_uart_driver_data_timeout_ms = 200`; each literal at :365, :388, :500, :502, :579, :593, :607, :636, :645, :656, :667, :960, :1053, :1079, :1499, :1523, :1661, :1686, :1708, :1799, :1852 becomes `_DATA_TIMEOUT_MS`; `_NO_DATA_TIMEOUT_MS = 20` (new, module level) tagged `# @tunable l1.asy_uart_driver_no_data_timeout_ms = 20`; each literal at :371, :875 becomes `_NO_DATA_TIMEOUT_MS`; `_TASK_INSIDE_MS = 5` (new, module level) tagged `# @tunable l1.asy_uart_driver_task_inside_ms = 5`; each literal at :417, :711, :736, :757, :780, :803, :825, :1144 becomes `_TASK_INSIDE_MS`; `_STEP_BOUND_S = 2` (new, module level) tagged `# @tunable l1.asy_uart_driver_step_bound_s = 2`; each literal at :419, :712, :713, :737, :738, :760, :761, :781, :783, :804, :806, :826, :827, :1146 becomes `_STEP_BOUND_S`; `_NO_DELIMITER_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l1.asy_uart_driver_no_delimiter_timeout_ms = 100`; the literal at :619 becomes `_NO_DELIMITER_TIMEOUT_MS`; `_LOCKED_WORK_MS = 30` (new, module level) tagged `# @tunable l1.asy_uart_driver_locked_work_ms = 30`; each literal at :706, :730 becomes `_LOCKED_WORK_MS`; `_WEDGED_HOLD_MS = 400` (new, module level) tagged `# @tunable l1.asy_uart_driver_wedged_hold_ms = 400`; the literal at :799 becomes `_WEDGED_HOLD_MS`; `_SHORT_CANCEL_ACK_MS = 50` (new, module level) tagged `# @tunable l1.asy_uart_driver_short_cancel_ack_ms = 50`; the literal at :804 becomes `_SHORT_CANCEL_ACK_MS`; `_HOLDER_WORK_MS = 20` (new, module level) tagged `# @tunable l1.asy_uart_driver_holder_work_ms = 20`; the literal at :821 becomes `_HOLDER_WORK_MS`; `_CANCEL_ACK_MS = 500` (new, module level) tagged `# @tunable l1.asy_uart_driver_cancel_ack_ms = 500`; the literal at :826 becomes `_CANCEL_ACK_MS`; `_READY_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l1.asy_uart_driver_ready_timeout_ms = 100`; each literal at :846, :1574 becomes `_READY_TIMEOUT_MS`; `_DEADLOCK_WAIT_S = 0.2` (new, module level) tagged `# @tunable l1.asy_i2c_driver_deadlock_wait_s = 0.2`; the literal at :1372 becomes `_DEADLOCK_WAIT_S`; `_POLL_WAIT_MS = 1` (new, module level) tagged `# @tunable l1.asy_uart_driver_poll_wait_ms = 1`; each literal at :1591, :1595, :1650, :1677, :1791 becomes `_POLL_WAIT_MS`; `_IDLE_POLL_MS = 40` (new, module level) tagged `# @tunable l1.asy_uart_driver_idle_poll_ms = 40`; each literal at :1591, :1595 becomes `_IDLE_POLL_MS`; `_SILENT_LINE_TIMEOUT_MS = 30` (new, module level) tagged `# @tunable l1.asy_uart_driver_silent_line_timeout_ms = 30`; each literal at :1809, :1810, :1880 becomes `_SILENT_LINE_TIMEOUT_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_asy_i2c_driver.py`, `tests/test_asy_spi_driver.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.09
- **Kind**: test

### A.U8C.19 Tag the tuned literals of `test_asy_uart_link_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_uart_link_driver.py` — `l1.uart_comm_harness_timeout_ms` :25 (100); `l1.uart_comm_harness_poll_wait_ms` :26 (1); `l1.uart_comm_harness_run_limit_s` :29 (10); `l1.uart_comm_harness_listener_drain_s` :58 (5); `l1.asy_uart_link_driver_round_poll_s` :151 (0.005); `l1.asy_uart_link_driver_ticker_step_ms` :370 (1)
- **Change**: the literal at :25 is replaced by `TIMEOUT_MS`, imported from the file that holds `l1.uart_comm_harness_timeout_ms`'s tag (no tag here: an import is not a restatement); the literal at :26 is replaced by `POLL_WAIT_MS`, imported from the file that holds `l1.uart_comm_harness_poll_wait_ms`'s tag (no tag here: an import is not a restatement); the literal at :29 is replaced by `_RUN_LIMIT_S`, imported from the file that holds `l1.uart_comm_harness_run_limit_s`'s tag (no tag here: an import is not a restatement); the literal at :58 is replaced by `_LISTENER_DRAIN_S`, imported from the file that holds `l1.uart_comm_harness_listener_drain_s`'s tag (no tag here: an import is not a restatement); `_ROUND_POLL_S = 0.005` (new, module level) tagged `# @tunable l1.asy_uart_link_driver_round_poll_s = 0.005`; the literal at :151 becomes `_ROUND_POLL_S`; `_TICKER_STEP_MS = 1` (new, module level) tagged `# @tunable l1.asy_uart_link_driver_ticker_step_ms = 1`; the literal at :370 becomes `_TICKER_STEP_MS`; `from _uart_comm_harness import POLL_WAIT_MS, TIMEOUT_MS, _LISTENER_DRAIN_S, _RUN_LIMIT_S` replaces the local definitions at `:25-26` (deleted) and the literals at `:29, :58`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/_uart_comm_harness.py`, `tests/test_asy_uart_comm.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.03
- **Kind**: test

### A.U8C.20 Tag the tuned literals of `test_asy_udp_socket.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_udp_socket.py` — `l1.asy_udp_socket_recv_empty_timeout_ms` :207 (50); `l1.asy_udp_socket_attempt_timeout_ms` :240 (200); `l1.asy_udp_socket_exhaust_timeout_ms` :256 (30); `l1.asy_udp_socket_peer_recv_timeout_ms` :286, :1058, :1126 (1000); `l1.asy_udp_socket_peer_poll_ms` :295 (5); `l1.asy_udp_socket_reply_timeout_ms` :322, :344, :419, :1193, :1223, :1226 (500); `l1.asy_udp_socket_spoof_wait_ms` :416 (150); `l1.asy_udp_socket_kernel_queue_s` :444, :633, :1313, :1502 (0.05); `l1.asy_udp_socket_recv_timeout_ms` :447, :637, :758, :1314, :1503 (200); `l1.asy_udp_socket_in_time_delay_ms` :472 (40); `l1.asy_udp_socket_in_time_timeout_ms` :473 (300); `l1.asy_udp_socket_too_late_delay_ms` :476 (300); `l1.asy_udp_socket_too_late_timeout_ms` :477 (100); `l1.asy_udp_socket_ready_empty_timeout_ms` :523 (80); `l1.asy_udp_socket_ready_poll_ms` :758, :919 (10); `l1.asy_udp_socket_fix_address_after_retry_s` :786 (0.6); `l1.asy_udp_socket_task_park_s` :890, :1425 (0.05); `l1.asy_udp_socket_ms_check_timeout_ms` :919 (50); `l1.asy_udp_socket_ms_check_elapsed_max_ms` :926 (2000); `l1.asy_udp_socket_icmp_delivery_s` :985 (0.2); `l1.asy_udp_socket_icmp_recv_timeout_ms` :987 (5000); `l1.asy_udp_socket_icmp_elapsed_max_ms` :994 (1000); `l1.asy_udp_socket_long_reply_timeout_ms` :1070, :1135, :1161, :1164 (1000); `l1.asy_udp_socket_unreachable_timeout_ms` :1101 (500); `l1.asy_udp_socket_no_sender_timeout_ms` :1191 (100); `l1.asy_udp_socket_first_attempt_s` :1340, :1365, :1394, :1423 (0.1); `l1.asy_udp_socket_retry_cycle_min_ms` :1350 (1000); `l1.asy_udp_socket_retry_cycle_max_ms` :1351 (5000); `l1.asy_udp_socket_fix_address_after_s` :1368 (0.5); `l1.asy_udp_socket_disconnect_bound_s` :1403, :1439 (2); `l1.asy_udp_socket_connect_bound_s` :1434 (3); `l1.asy_udp_socket_forever_poll_ms` :1605 (20); `l1.asy_udp_socket_enter_sleep_s` :1606 (0.1)
- **Change**: `_RECV_EMPTY_TIMEOUT_MS = 50` (new, module level) tagged `# @tunable l1.asy_udp_socket_recv_empty_timeout_ms = 50`; the literal at :207 becomes `_RECV_EMPTY_TIMEOUT_MS`; `_ATTEMPT_TIMEOUT_MS = 200` (new, module level) tagged `# @tunable l1.asy_udp_socket_attempt_timeout_ms = 200`; the literal at :240 becomes `_ATTEMPT_TIMEOUT_MS`; `_EXHAUST_TIMEOUT_MS = 30` (new, module level) tagged `# @tunable l1.asy_udp_socket_exhaust_timeout_ms = 30`; the literal at :256 becomes `_EXHAUST_TIMEOUT_MS`; `_PEER_RECV_TIMEOUT_MS = 1000` (new, module level) tagged `# @tunable l1.asy_udp_socket_peer_recv_timeout_ms = 1000`; each literal at :286, :1058, :1126 becomes `_PEER_RECV_TIMEOUT_MS`; `_PEER_POLL_MS = 5` (new, module level) tagged `# @tunable l1.asy_udp_socket_peer_poll_ms = 5`; the literal at :295 becomes `_PEER_POLL_MS`; `_REPLY_TIMEOUT_MS = 500` (new, module level) tagged `# @tunable l1.asy_udp_socket_reply_timeout_ms = 500`; each literal at :322, :344, :419, :1193, :1223, :1226 becomes `_REPLY_TIMEOUT_MS`; `_SPOOF_WAIT_MS = 150` (new, module level) tagged `# @tunable l1.asy_udp_socket_spoof_wait_ms = 150`; the literal at :416 becomes `_SPOOF_WAIT_MS`; `_KERNEL_QUEUE_S = 0.05` (new, module level) tagged `# @tunable l1.asy_udp_socket_kernel_queue_s = 0.05`; each literal at :444, :633, :1313, :1502 becomes `_KERNEL_QUEUE_S`; `_RECV_TIMEOUT_MS = 200` (new, module level) tagged `# @tunable l1.asy_udp_socket_recv_timeout_ms = 200`; each literal at :447, :637, :758, :1314, :1503 becomes `_RECV_TIMEOUT_MS`; `_IN_TIME_DELAY_MS = 40` (new, module level) tagged `# @tunable l1.asy_udp_socket_in_time_delay_ms = 40`; the literal at :472 becomes `_IN_TIME_DELAY_MS`; `_IN_TIME_TIMEOUT_MS = 300` (new, module level) tagged `# @tunable l1.asy_udp_socket_in_time_timeout_ms = 300`; the literal at :473 becomes `_IN_TIME_TIMEOUT_MS`; `_TOO_LATE_DELAY_MS = 300` (new, module level) tagged `# @tunable l1.asy_udp_socket_too_late_delay_ms = 300`; the literal at :476 becomes `_TOO_LATE_DELAY_MS`; `_TOO_LATE_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l1.asy_udp_socket_too_late_timeout_ms = 100`; the literal at :477 becomes `_TOO_LATE_TIMEOUT_MS`; `_READY_EMPTY_TIMEOUT_MS = 80` (new, module level) tagged `# @tunable l1.asy_udp_socket_ready_empty_timeout_ms = 80`; the literal at :523 becomes `_READY_EMPTY_TIMEOUT_MS`; `_READY_POLL_MS = 10` (new, module level) tagged `# @tunable l1.asy_udp_socket_ready_poll_ms = 10`; each literal at :758, :919 becomes `_READY_POLL_MS`; `_FIX_ADDRESS_AFTER_RETRY_S = 0.6` (new, module level) tagged `# @tunable l1.asy_udp_socket_fix_address_after_retry_s = 0.6`; the literal at :786 becomes `_FIX_ADDRESS_AFTER_RETRY_S`; `_TASK_PARK_S = 0.05` (new, module level) tagged `# @tunable l1.asy_udp_socket_task_park_s = 0.05`; each literal at :890, :1425 becomes `_TASK_PARK_S`; `_MS_CHECK_TIMEOUT_MS = 50` (new, module level) tagged `# @tunable l1.asy_udp_socket_ms_check_timeout_ms = 50`; the literal at :919 becomes `_MS_CHECK_TIMEOUT_MS`; `_MS_CHECK_ELAPSED_MAX_MS = 2000` (new, module level) tagged `# @tunable l1.asy_udp_socket_ms_check_elapsed_max_ms = 2000`; the literal at :926 becomes `_MS_CHECK_ELAPSED_MAX_MS`; `_ICMP_DELIVERY_S = 0.2` (new, module level) tagged `# @tunable l1.asy_udp_socket_icmp_delivery_s = 0.2`; the literal at :985 becomes `_ICMP_DELIVERY_S`; `_ICMP_RECV_TIMEOUT_MS = 5000` (new, module level) tagged `# @tunable l1.asy_udp_socket_icmp_recv_timeout_ms = 5000`; the literal at :987 becomes `_ICMP_RECV_TIMEOUT_MS`; `_ICMP_ELAPSED_MAX_MS = 1000` (new, module level) tagged `# @tunable l1.asy_udp_socket_icmp_elapsed_max_ms = 1000`; the literal at :994 becomes `_ICMP_ELAPSED_MAX_MS`; `_LONG_REPLY_TIMEOUT_MS = 1000` (new, module level) tagged `# @tunable l1.asy_udp_socket_long_reply_timeout_ms = 1000`; each literal at :1070, :1135, :1161, :1164 becomes `_LONG_REPLY_TIMEOUT_MS`; `_UNREACHABLE_TIMEOUT_MS = 500` (new, module level) tagged `# @tunable l1.asy_udp_socket_unreachable_timeout_ms = 500`; the literal at :1101 becomes `_UNREACHABLE_TIMEOUT_MS`; `_NO_SENDER_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l1.asy_udp_socket_no_sender_timeout_ms = 100`; the literal at :1191 becomes `_NO_SENDER_TIMEOUT_MS`; `_FIRST_ATTEMPT_S = 0.1` (new, module level) tagged `# @tunable l1.asy_udp_socket_first_attempt_s = 0.1`; each literal at :1340, :1365, :1394, :1423 becomes `_FIRST_ATTEMPT_S`; `_RETRY_CYCLE_MIN_MS = 1000` (new, module level) tagged `# @tunable l1.asy_udp_socket_retry_cycle_min_ms = 1000`; the literal at :1350 becomes `_RETRY_CYCLE_MIN_MS`; `_RETRY_CYCLE_MAX_MS = 5000` (new, module level) tagged `# @tunable l1.asy_udp_socket_retry_cycle_max_ms = 5000`; the literal at :1351 becomes `_RETRY_CYCLE_MAX_MS`; `_FIX_ADDRESS_AFTER_S = 0.5` (new, module level) tagged `# @tunable l1.asy_udp_socket_fix_address_after_s = 0.5`; the literal at :1368 becomes `_FIX_ADDRESS_AFTER_S`; `_DISCONNECT_BOUND_S = 2` (new, module level) tagged `# @tunable l1.asy_udp_socket_disconnect_bound_s = 2`; each literal at :1403, :1439 becomes `_DISCONNECT_BOUND_S`; `_CONNECT_BOUND_S = 3` (new, module level) tagged `# @tunable l1.asy_udp_socket_connect_bound_s = 3`; the literal at :1434 becomes `_CONNECT_BOUND_S`; `_FOREVER_POLL_MS = 20` (new, module level) tagged `# @tunable l1.asy_udp_socket_forever_poll_ms = 20`; the literal at :1605 becomes `_FOREVER_POLL_MS`; `_ENTER_SLEEP_S = 0.1` (new, module level) tagged `# @tunable l1.asy_udp_socket_enter_sleep_s = 0.1`; the literal at :1606 becomes `_ENTER_SLEEP_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.21 Tag the tuned literals of `test_asy_webserver_service.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits; G8/R31 (run_timed bounds); A.U8.04's and A.U8.17's named sites in this file are kept as those actions state
- **Site**: `tests/test_asy_webserver_service.py` — `l1.asy_webserver_service_run_bound_s` :45, :1184, :1205, :1219, :1237, :1265, :1538, :1976, :2048 (5.0); `l1.asy_webserver_service_tiny_per_call_s` :1033 (0.01); `l1.asy_webserver_service_reclaim_per_call_s` :1062, :1158, :1209, :1302, :1529, :1569, :1639, :1659, :3081, :3096 (0.05); `l1.asy_webserver_service_short_outer_cap_s` :1062, :1556, :1569 (0.2); `l1.asy_webserver_service_serve_bound_s` :1065, :1160, :1312, :1377, :1445, :1641, :1661, :1741, :3083, :3099 (2.0); `l1.asy_webserver_service_headroom_s` :1158, :1209, :1326, :1639, :3081 (2.0); `l1.asy_webserver_service_run_long_bound_s` :1179, :1457, :1552, :1769 (10.0); `l1.asy_webserver_service_admit_settle_s` :1192 (0.01); `l1.asy_webserver_service_close_poll_s` :1248 (0.01); `l1.asy_webserver_service_mid_headroom_s` :1302, :1326, :1542, :1659, :3096 (1.0); `l1.asy_webserver_service_serve_long_bound_s` :1306, :1316, :1329, :1385, :1571, :1745, :1800 (3.0); `web.max_content_length` :1362 (2048); `l1.asy_webserver_service_long_headroom_s` :1445 (5.0); `l1.asy_webserver_service_wedge_outer_cap_s` :1529 (0.5); `l1.asy_webserver_service_fast_per_call_s` :1542, :1556, :1812 (0.02); `l1.asy_webserver_service_rewedge_run_bound_s` :1565 (15.0); `l1.asy_webserver_service_task_reach_s` :1792, :3065 (0.05); `l1.asy_webserver_service_tiny_outer_cap_s` :1812 (0.1); `l1.webserver_leak_scenario_timeout_s` :1835 (60.0); `web.chunk_bytes` :1954, :2469 (256); `l1.asy_webserver_service_cancel_outer_cap_s` :3055 (10.0)
- **Change**: `_RUN_BOUND_S = 5.0` (new, module level) tagged `# @tunable l1.asy_webserver_service_run_bound_s = 5.0`; each literal at :45, :1184, :1205, :1219, :1237, :1265, :1538, :1976, :2048 becomes `_RUN_BOUND_S`; `_TINY_PER_CALL_S = 0.01` (new, module level) tagged `# @tunable l1.asy_webserver_service_tiny_per_call_s = 0.01`; the literal at :1033 becomes `_TINY_PER_CALL_S`; `_RECLAIM_PER_CALL_S = 0.05` (new, module level) tagged `# @tunable l1.asy_webserver_service_reclaim_per_call_s = 0.05`; each literal at :1062, :1158, :1209, :1302, :1529, :1569, :1639, :1659, :3081, :3096 becomes `_RECLAIM_PER_CALL_S`; `_SHORT_OUTER_CAP_S = 0.2` (new, module level) tagged `# @tunable l1.asy_webserver_service_short_outer_cap_s = 0.2`; each literal at :1062, :1556, :1569 becomes `_SHORT_OUTER_CAP_S`; `_SERVE_BOUND_S = 2.0` (new, module level) tagged `# @tunable l1.asy_webserver_service_serve_bound_s = 2.0`; each literal at :1065, :1160, :1312, :1377, :1445, :1641, :1661, :1741, :3083, :3099 becomes `_SERVE_BOUND_S`; `_HEADROOM_S = 2.0` (new, module level) tagged `# @tunable l1.asy_webserver_service_headroom_s = 2.0`; each literal at :1158, :1209, :1326, :1639, :3081 becomes `_HEADROOM_S`; `_RUN_LONG_BOUND_S = 10.0` (new, module level) tagged `# @tunable l1.asy_webserver_service_run_long_bound_s = 10.0`; each literal at :1179, :1457, :1552, :1769 becomes `_RUN_LONG_BOUND_S`; `_ADMIT_SETTLE_S = 0.01` (new, module level) tagged `# @tunable l1.asy_webserver_service_admit_settle_s = 0.01`; the literal at :1192 becomes `_ADMIT_SETTLE_S`; `_CLOSE_POLL_S = 0.01` (new, module level) tagged `# @tunable l1.asy_webserver_service_close_poll_s = 0.01`; the literal at :1248 becomes `_CLOSE_POLL_S`; `_MID_HEADROOM_S = 1.0` (new, module level) tagged `# @tunable l1.asy_webserver_service_mid_headroom_s = 1.0`; each literal at :1302, :1326, :1542, :1659, :3096 becomes `_MID_HEADROOM_S`; `_SERVE_LONG_BOUND_S = 3.0` (new, module level) tagged `# @tunable l1.asy_webserver_service_serve_long_bound_s = 3.0`; each literal at :1306, :1316, :1329, :1385, :1571, :1745, :1800 becomes `_SERVE_LONG_BOUND_S`; mirror `web.max_content_length` at :1362: already named by A.U8.04; it gets the tag there; `_LONG_HEADROOM_S = 5.0` (new, module level) tagged `# @tunable l1.asy_webserver_service_long_headroom_s = 5.0`; the literal at :1445 becomes `_LONG_HEADROOM_S`; `_WEDGE_OUTER_CAP_S = 0.5` (new, module level) tagged `# @tunable l1.asy_webserver_service_wedge_outer_cap_s = 0.5`; the literal at :1529 becomes `_WEDGE_OUTER_CAP_S`; `_FAST_PER_CALL_S = 0.02` (new, module level) tagged `# @tunable l1.asy_webserver_service_fast_per_call_s = 0.02`; each literal at :1542, :1556, :1812 becomes `_FAST_PER_CALL_S`; `_REWEDGE_RUN_BOUND_S = 15.0` (new, module level) tagged `# @tunable l1.asy_webserver_service_rewedge_run_bound_s = 15.0`; the literal at :1565 becomes `_REWEDGE_RUN_BOUND_S`; `_TASK_REACH_S = 0.05` (new, module level) tagged `# @tunable l1.asy_webserver_service_task_reach_s = 0.05`; each literal at :1792, :3065 becomes `_TASK_REACH_S`; `_TINY_OUTER_CAP_S = 0.1` (new, module level) tagged `# @tunable l1.asy_webserver_service_tiny_outer_cap_s = 0.1`; the literal at :1812 becomes `_TINY_OUTER_CAP_S`; l1.webserver_leak_scenario_timeout_s at :1835: already created and tagged by A.U8.17; nothing further here; mirror `web.chunk_bytes` at :1954, :2469: already named by A.U8.04; it gets the tag there; `_CANCEL_OUTER_CAP_S = 10.0` (new, module level) tagged `# @tunable l1.asy_webserver_service_cancel_outer_cap_s = 10.0`; the literal at :3055 becomes `_CANCEL_OUTER_CAP_S`; the service timeouts passed to `_make_service()` are named once per value; where one call passes the same value to both `per_call_timeout_s` and `outer_cap_s` (`:1184, :1237, :1312, :1377, :1741`) both keywords use the one constant. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.04, A.U8.17; A.U8.17 (`:1835`)
- **Kind**: test

### A.U8C.22 Tag the tuned literals of `test_asy_wifi_service.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_wifi_service.py` — `l1.asy_wifi_service_connect_bound_s` :2233 (2.0); `l1.asy_wifi_service_no_reply_wait_s` :2343 (0.3); `l1.asy_wifi_service_sent_poll_ms` :2389 (10); `l1.asy_wifi_service_off_subnet_wait_s` :2409 (0.2); `l1.asy_wifi_service_connect_poll_ms` :2446 (50); `l1.asy_wifi_service_phase_poll_ms` :2469 (20); `l1.asy_wifi_service_flash_cancel_bound_s` :2636 (1)
- **Change**: `_CONNECT_BOUND_S = 2.0` (new, module level) tagged `# @tunable l1.asy_wifi_service_connect_bound_s = 2.0`; the literal at :2233 becomes `_CONNECT_BOUND_S`; `_NO_REPLY_WAIT_S = 0.3` (new, module level) tagged `# @tunable l1.asy_wifi_service_no_reply_wait_s = 0.3`; the literal at :2343 becomes `_NO_REPLY_WAIT_S`; `_SENT_POLL_MS = 10` (new, module level) tagged `# @tunable l1.asy_wifi_service_sent_poll_ms = 10`; the literal at :2389 becomes `_SENT_POLL_MS`; `_OFF_SUBNET_WAIT_S = 0.2` (new, module level) tagged `# @tunable l1.asy_wifi_service_off_subnet_wait_s = 0.2`; the literal at :2409 becomes `_OFF_SUBNET_WAIT_S`; `_CONNECT_POLL_MS = 50` (new, module level) tagged `# @tunable l1.asy_wifi_service_connect_poll_ms = 50`; the literal at :2446 becomes `_CONNECT_POLL_MS`; `_PHASE_POLL_MS = 20` (new, module level) tagged `# @tunable l1.asy_wifi_service_phase_poll_ms = 20`; the literal at :2469 becomes `_PHASE_POLL_MS`; `_FLASH_CANCEL_BOUND_S = 1` (new, module level) tagged `# @tunable l1.asy_wifi_service_flash_cancel_bound_s = 1`; the literal at :2636 becomes `_FLASH_CANCEL_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.23 Tag the tuned literals of `test_captive_dns.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_captive_dns.py` — `l1.captive_dns_wait_until_timeout_ms` :370 (1000); `l1.captive_dns_wait_until_poll_ms` :375 (10); `l1.captive_dns_stray_reply_wait_ms` :423 (20); `l1.captive_dns_no_backoff_elapsed_max_ms` :482 (1000); `l1.captive_dns_reach_recv_ms` :512, :647, :972, :1077, :1096 (20); `l1.captive_dns_bind_wait_ms` :595, :824, :854, :884 (50); `l1.captive_dns_reply_wait_ms` :597, :858 (200); `l1.captive_dns_cycle_wait_ms` :827 (100); `l1.captive_dns_cleanup_tick_ms` :890 (10); `l1.captive_dns_backoff_wait_timeout_ms` :941 (5000); `dns_server.error_retry_wait_s` :952 (3000); `l1.captive_dns_backoff_series_timeout_ms` :999, :1034 (15000); `l1.captive_dns_gap_initial_min_ms` :1012, :1041, :1044 (400); `l1.captive_dns_gap_initial_max_ms` :1012, :1041, :1044 (800); `l1.captive_dns_gap_doubled_min_ms` :1013, :1042 (900); `l1.captive_dns_gap_doubled_max_ms` :1013, :1042 (1400); `l1.captive_dns_gap_quad_min_ms` :1014 (1900); `l1.captive_dns_gap_quad_max_ms` :1014 (2600); `l1.captive_dns_gap_no_backoff_max_ms` :1043 (300); `l1.captive_dns_backoff_cap_timeout_ms` :1059 (20000); `l1.captive_dns_gap_cap_min_ms` :1067 (4700); `l1.captive_dns_gap_cap_max_ms` :1067 (5400)
- **Change**: `_WAIT_UNTIL_TIMEOUT_MS = 1000` (new, module level) tagged `# @tunable l1.captive_dns_wait_until_timeout_ms = 1000`; the literal at :370 becomes `_WAIT_UNTIL_TIMEOUT_MS`; `_WAIT_UNTIL_POLL_MS = 10` (new, module level) tagged `# @tunable l1.captive_dns_wait_until_poll_ms = 10`; the literal at :375 becomes `_WAIT_UNTIL_POLL_MS`; `_STRAY_REPLY_WAIT_MS = 20` (new, module level) tagged `# @tunable l1.captive_dns_stray_reply_wait_ms = 20`; the literal at :423 becomes `_STRAY_REPLY_WAIT_MS`; `_NO_BACKOFF_ELAPSED_MAX_MS = 1000` (new, module level) tagged `# @tunable l1.captive_dns_no_backoff_elapsed_max_ms = 1000`; the literal at :482 becomes `_NO_BACKOFF_ELAPSED_MAX_MS`; `_REACH_RECV_MS = 20` (new, module level) tagged `# @tunable l1.captive_dns_reach_recv_ms = 20`; each literal at :512, :647, :972, :1077, :1096 becomes `_REACH_RECV_MS`; `_BIND_WAIT_MS = 50` (new, module level) tagged `# @tunable l1.captive_dns_bind_wait_ms = 50`; each literal at :595, :824, :854, :884 becomes `_BIND_WAIT_MS`; `_REPLY_WAIT_MS = 200` (new, module level) tagged `# @tunable l1.captive_dns_reply_wait_ms = 200`; each literal at :597, :858 becomes `_REPLY_WAIT_MS`; `_CYCLE_WAIT_MS = 100` (new, module level) tagged `# @tunable l1.captive_dns_cycle_wait_ms = 100`; the literal at :827 becomes `_CYCLE_WAIT_MS`; `_CLEANUP_TICK_MS = 10` (new, module level) tagged `# @tunable l1.captive_dns_cleanup_tick_ms = 10`; the literal at :890 becomes `_CLEANUP_TICK_MS`; `_BACKOFF_WAIT_TIMEOUT_MS = 5000` (new, module level) tagged `# @tunable l1.captive_dns_backoff_wait_timeout_ms = 5000`; the literal at :941 becomes `_BACKOFF_WAIT_TIMEOUT_MS`; mirror `dns_server.error_retry_wait_s` at :952: already named by A.U8.11; it gets the tag there; `_BACKOFF_SERIES_TIMEOUT_MS = 15000` (new, module level) tagged `# @tunable l1.captive_dns_backoff_series_timeout_ms = 15000`; each literal at :999, :1034 becomes `_BACKOFF_SERIES_TIMEOUT_MS`; `_GAP_INITIAL_MIN_MS = 400` (new, module level) tagged `# @tunable l1.captive_dns_gap_initial_min_ms = 400`; each literal at :1012, :1041, :1044 becomes `_GAP_INITIAL_MIN_MS`; `_GAP_INITIAL_MAX_MS = 800` (new, module level) tagged `# @tunable l1.captive_dns_gap_initial_max_ms = 800`; each literal at :1012, :1041, :1044 becomes `_GAP_INITIAL_MAX_MS`; `_GAP_DOUBLED_MIN_MS = 900` (new, module level) tagged `# @tunable l1.captive_dns_gap_doubled_min_ms = 900`; each literal at :1013, :1042 becomes `_GAP_DOUBLED_MIN_MS`; `_GAP_DOUBLED_MAX_MS = 1400` (new, module level) tagged `# @tunable l1.captive_dns_gap_doubled_max_ms = 1400`; each literal at :1013, :1042 becomes `_GAP_DOUBLED_MAX_MS`; `_GAP_QUAD_MIN_MS = 1900` (new, module level) tagged `# @tunable l1.captive_dns_gap_quad_min_ms = 1900`; the literal at :1014 becomes `_GAP_QUAD_MIN_MS`; `_GAP_QUAD_MAX_MS = 2600` (new, module level) tagged `# @tunable l1.captive_dns_gap_quad_max_ms = 2600`; the literal at :1014 becomes `_GAP_QUAD_MAX_MS`; `_GAP_NO_BACKOFF_MAX_MS = 300` (new, module level) tagged `# @tunable l1.captive_dns_gap_no_backoff_max_ms = 300`; the literal at :1043 becomes `_GAP_NO_BACKOFF_MAX_MS`; `_BACKOFF_CAP_TIMEOUT_MS = 20000` (new, module level) tagged `# @tunable l1.captive_dns_backoff_cap_timeout_ms = 20000`; the literal at :1059 becomes `_BACKOFF_CAP_TIMEOUT_MS`; `_GAP_CAP_MIN_MS = 4700` (new, module level) tagged `# @tunable l1.captive_dns_gap_cap_min_ms = 4700`; the literal at :1067 becomes `_GAP_CAP_MIN_MS`; `_GAP_CAP_MAX_MS = 5400` (new, module level) tagged `# @tunable l1.captive_dns_gap_cap_max_ms = 5400`; the literal at :1067 becomes `_GAP_CAP_MAX_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.11
- **Kind**: test

### A.U8C.24 Tag the tuned literals of `test_digital_twin_bus_hazard_concurrency.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_digital_twin_bus_hazard_concurrency.py` — `l2.twin_wdt_feed_interval_s` :76 (1.0); `l2.bus_hazard_concurrency_run_bound_s` :187, :201, :272, :314, :349, :438, :469, :498 (20.0); `l2.bus_hazard_concurrency_api_run_bound_s` :215, :229 (40.0); `l2.bus_hazard_concurrency_established_poll_s` :357 (0.5); `l2.bus_hazard_concurrency_reconnect_poll_s` :360 (1.0); `l2.bus_hazard_concurrency_flap_window_s` :392 (75.0); `l2.bus_hazard_concurrency_flap_run_bound_s` :408 (95.0); `l2.bus_hazard_concurrency_state_run_bound_s` :533 (30.0)
- **Change**: `_WDT_FEED_INTERVAL_S = 1.0` (new, module level) tagged `# @tunable l2.twin_wdt_feed_interval_s = 1.0`; the literal at :76 becomes `_WDT_FEED_INTERVAL_S`; `_RUN_BOUND_S = 20.0` (new, module level) tagged `# @tunable l2.bus_hazard_concurrency_run_bound_s = 20.0`; each literal at :187, :201, :272, :314, :349, :438, :469, :498 becomes `_RUN_BOUND_S`; `_API_RUN_BOUND_S = 40.0` (new, module level) tagged `# @tunable l2.bus_hazard_concurrency_api_run_bound_s = 40.0`; each literal at :215, :229 becomes `_API_RUN_BOUND_S`; `_ESTABLISHED_POLL_S = 0.5` (new, module level) tagged `# @tunable l2.bus_hazard_concurrency_established_poll_s = 0.5`; the literal at :357 becomes `_ESTABLISHED_POLL_S`; `_RECONNECT_POLL_S = 1.0` (new, module level) tagged `# @tunable l2.bus_hazard_concurrency_reconnect_poll_s = 1.0`; the literal at :360 becomes `_RECONNECT_POLL_S`; `_FLAP_WINDOW_S = 75.0` (new, module level) tagged `# @tunable l2.bus_hazard_concurrency_flap_window_s = 75.0`; the literal at :392 becomes `_FLAP_WINDOW_S`; `_FLAP_RUN_BOUND_S = 95.0` (new, module level) tagged `# @tunable l2.bus_hazard_concurrency_flap_run_bound_s = 95.0`; the literal at :408 becomes `_FLAP_RUN_BOUND_S`; `_STATE_RUN_BOUND_S = 30.0` (new, module level) tagged `# @tunable l2.bus_hazard_concurrency_state_run_bound_s = 30.0`; the literal at :533 becomes `_STATE_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_digital_twin_sensortask_integration.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.25 Tag the tuned literals of `test_digital_twin_http_client.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_digital_twin_http_client.py` — `l2.http_client_run_bound_s` :24, :344, :377, :410, :431, :446 (5.0); `l2.http_client_mid_body_pause_ms` :360 (20)
- **Change**: `_RUN_BOUND_S = 5.0` (new, module level) tagged `# @tunable l2.http_client_run_bound_s = 5.0`; each literal at :24, :344, :377, :410, :431, :446 becomes `_RUN_BOUND_S`; `_MID_BODY_PAUSE_MS = 20` (new, module level) tagged `# @tunable l2.http_client_mid_body_pause_ms = 20`; the literal at :360 becomes `_MID_BODY_PAUSE_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.26 Tag the tuned literals of `test_digital_twin_launch.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_digital_twin_launch.py` — `l2.launch_short_duration_s` :212, :246 (0.5); `l2.launch_main_bound_s` :213, :234, :247 (10); `l2.launch_fault_duration_s` :230 (2.5); `l2.launch_long_duration_s` :258 (4.5); `l2.launch_long_main_bound_s` :259 (15)
- **Change**: `_SHORT_DURATION_S = 0.5` (new, module level) tagged `# @tunable l2.launch_short_duration_s = 0.5`; each literal at :212, :246 becomes `_SHORT_DURATION_S`; `_MAIN_BOUND_S = 10` (new, module level) tagged `# @tunable l2.launch_main_bound_s = 10`; each literal at :213, :234, :247 becomes `_MAIN_BOUND_S`; `_FAULT_DURATION_S = 2.5` (new, module level) tagged `# @tunable l2.launch_fault_duration_s = 2.5`; the literal at :230 becomes `_FAULT_DURATION_S`; `_LONG_DURATION_S = 4.5` (new, module level) tagged `# @tunable l2.launch_long_duration_s = 4.5`; the literal at :258 becomes `_LONG_DURATION_S`; `_LONG_MAIN_BOUND_S = 15` (new, module level) tagged `# @tunable l2.launch_long_main_bound_s = 15`; the literal at :259 becomes `_LONG_MAIN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.27 Tag the tuned literals of `test_digital_twin_machine.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_digital_twin_machine.py` — `l2.machine_wdt_short_timeout_ms` :357, :382, :394, :410 (150); `l2.machine_wdt_poll_ms` :361, :386, :400, :414 (5); `l2.machine_run_bound_s` :364, :375, :403, :417, :501, :532 (5); `l2.machine_wdt_fed_timeout_ms` :369 (100); `l2.machine_feed_step_ms` :371 (20); `l2.machine_double_trigger_bound_s` :389 (8); `l2.machine_timer_period_ms` :460, :525 (20); `l2.machine_before_deinit_ms` :463 (60); `l2.machine_after_deinit_ms` :466 (80); `l2.machine_chain_period_ms` :491, :494 (10); `l2.machine_chain_poll_ms` :498 (10); `l2.machine_fire_poll_ms` :529 (20)
- **Change**: `_WDT_SHORT_TIMEOUT_MS = 150` (new, module level) tagged `# @tunable l2.machine_wdt_short_timeout_ms = 150`; each literal at :357, :382, :394, :410 becomes `_WDT_SHORT_TIMEOUT_MS`; `_WDT_POLL_MS = 5` (new, module level) tagged `# @tunable l2.machine_wdt_poll_ms = 5`; each literal at :361, :386, :400, :414 becomes `_WDT_POLL_MS`; `_RUN_BOUND_S = 5` (new, module level) tagged `# @tunable l2.machine_run_bound_s = 5`; each literal at :364, :375, :403, :417, :501, :532 becomes `_RUN_BOUND_S`; `_WDT_FED_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l2.machine_wdt_fed_timeout_ms = 100`; the literal at :369 becomes `_WDT_FED_TIMEOUT_MS`; `_FEED_STEP_MS = 20` (new, module level) tagged `# @tunable l2.machine_feed_step_ms = 20`; the literal at :371 becomes `_FEED_STEP_MS`; `_DOUBLE_TRIGGER_BOUND_S = 8` (new, module level) tagged `# @tunable l2.machine_double_trigger_bound_s = 8`; the literal at :389 becomes `_DOUBLE_TRIGGER_BOUND_S`; `_TIMER_PERIOD_MS = 20` (new, module level) tagged `# @tunable l2.machine_timer_period_ms = 20`; each literal at :460, :525 becomes `_TIMER_PERIOD_MS`; `_BEFORE_DEINIT_MS = 60` (new, module level) tagged `# @tunable l2.machine_before_deinit_ms = 60`; the literal at :463 becomes `_BEFORE_DEINIT_MS`; `_AFTER_DEINIT_MS = 80` (new, module level) tagged `# @tunable l2.machine_after_deinit_ms = 80`; the literal at :466 becomes `_AFTER_DEINIT_MS`; `_CHAIN_PERIOD_MS = 10` (new, module level) tagged `# @tunable l2.machine_chain_period_ms = 10`; each literal at :491, :494 becomes `_CHAIN_PERIOD_MS`; `_CHAIN_POLL_MS = 10` (new, module level) tagged `# @tunable l2.machine_chain_poll_ms = 10`; the literal at :498 becomes `_CHAIN_POLL_MS`; `_FIRE_POLL_MS = 20` (new, module level) tagged `# @tunable l2.machine_fire_poll_ms = 20`; the literal at :529 becomes `_FIRE_POLL_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.28 Tag the tuned literals of `test_digital_twin_machine_uart.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_digital_twin_machine_uart.py` — `l2.machine_uart_wire_time_floor_ms` :58 (100); `l2.machine_uart_pump_deadline_ms` :84 (500)
- **Change**: `_WIRE_TIME_FLOOR_MS = 100` (new, module level) tagged `# @tunable l2.machine_uart_wire_time_floor_ms = 100`; the literal at :58 becomes `_WIRE_TIME_FLOOR_MS`; `_PUMP_DEADLINE_MS = 500` (new, module level) tagged `# @tunable l2.machine_uart_pump_deadline_ms = 500`; the literal at :84 becomes `_PUMP_DEADLINE_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.29 Tag the tuned literals of `test_digital_twin_network_neopixel.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_digital_twin_network_neopixel.py` — `l2.network_neopixel_wait_timeout_s` :37, :45 (5.0); `l2.network_neopixel_poll_ms` :40, :48 (20); `l2.network_neopixel_never_connects_wait_s` :149, :251 (1.0)
- **Change**: `_WAIT_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l2.network_neopixel_wait_timeout_s = 5.0`; each literal at :37, :45 becomes `_WAIT_TIMEOUT_S`; `_POLL_MS = 20` (new, module level) tagged `# @tunable l2.network_neopixel_poll_ms = 20`; each literal at :40, :48 becomes `_POLL_MS`; `_NEVER_CONNECTS_WAIT_S = 1.0` (new, module level) tagged `# @tunable l2.network_neopixel_never_connects_wait_s = 1.0`; each literal at :149, :251 becomes `_NEVER_CONNECTS_WAIT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.30 Tag the tuned literals of `test_digital_twin_real_website_integration.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_digital_twin_real_website_integration.py` — `l2.real_website_integration_run_bound_s` :113, :155, :173, :192, :224, :251, :281, :300 (10.0); `l2.real_website_integration_burst_run_bound_s` :339 (30.0); deferred U25: `:75` (1.0)
- **Change**: `_RUN_BOUND_S = 10.0` (new, module level) tagged `# @tunable l2.real_website_integration_run_bound_s = 10.0`; each literal at :113, :155, :173, :192, :224, :251, :281, :300 becomes `_RUN_BOUND_S`; `_BURST_RUN_BOUND_S = 30.0` (new, module level) tagged `# @tunable l2.real_website_integration_burst_run_bound_s = 30.0`; the literal at :339 becomes `_BURST_RUN_BOUND_S`; deferred sleeps (:75): no tag now; classified once U25 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, U25
- **Kind**: test

### A.U8C.31 Tag the tuned literals of `test_digital_twin_run_generic_integration.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_digital_twin_run_generic_integration.py` — `l2.run_generic_integration_run_bound_s` :29 (5.0); `l2.run_generic_integration_main_run_bound_s` :244 (15.0)
- **Change**: `_RUN_BOUND_S = 5.0` (new, module level) tagged `# @tunable l2.run_generic_integration_run_bound_s = 5.0`; the literal at :29 becomes `_RUN_BOUND_S`; `_MAIN_RUN_BOUND_S = 15.0` (new, module level) tagged `# @tunable l2.run_generic_integration_main_run_bound_s = 15.0`; the literal at :244 becomes `_MAIN_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.32 Tag the tuned literals of `test_digital_twin_sensortask_integration.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_digital_twin_sensortask_integration.py` — `l2.sensortask_integration_dns_query_timeout_s` :126 (5.0); `l2.sensortask_integration_dns_query_poll_ms` :156 (5); `l2.sensortask_integration_wait_poll_s` :164 (0.25); `l2.sensortask_integration_run_bound_s` :253, :272, :293, :320, :346, :412 (10.0); `l2.sensortask_integration_override_poll_s` :378 (0.5); `l2.sensortask_integration_long_run_bound_s` :391, :469 (15.0); `l2.twin_wdt_feed_interval_s` :446 (1.0); `l2.wdt_overrun_wait_s` :461 (9.0); `l2.sensortask_integration_wait_timeout_s` :512, :599, :672, :696, :738, :752, :774 (5.0); `l2.sensortask_integration_restart_wait_timeout_s` :522 (6.0); `l2.sensortask_integration_supervisor_run_bound_s` :548, :818 (20.0); `l2.sensortask_integration_hotspot_wait_timeout_s` :594 (25.0); `l2.sensortask_integration_bind_poll_s` :599 (0.01); `l2.sensortask_integration_hotspot_run_bound_s` :630 (35.0); `l2.sensortask_integration_reboot_run_bound_s` :708, :781 (30.0); deferred U25: `:105` (1.0); deferred U25: `:586` (0.2); deferred U25: `:666` (2.5); deferred U25: `:694` (2.5); deferred U25: `:735` (2.5); deferred U25: `:772` (2.5)
- **Change**: `_DNS_QUERY_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l2.sensortask_integration_dns_query_timeout_s = 5.0`; the literal at :126 becomes `_DNS_QUERY_TIMEOUT_S`; `_DNS_QUERY_POLL_MS = 5` (new, module level) tagged `# @tunable l2.sensortask_integration_dns_query_poll_ms = 5`; the literal at :156 becomes `_DNS_QUERY_POLL_MS`; `_WAIT_POLL_S = 0.25` (new, module level) tagged `# @tunable l2.sensortask_integration_wait_poll_s = 0.25`; the literal at :164 becomes `_WAIT_POLL_S`; `_RUN_BOUND_S = 10.0` (new, module level) tagged `# @tunable l2.sensortask_integration_run_bound_s = 10.0`; each literal at :253, :272, :293, :320, :346, :412 becomes `_RUN_BOUND_S`; `_OVERRIDE_POLL_S = 0.5` (new, module level) tagged `# @tunable l2.sensortask_integration_override_poll_s = 0.5`; the literal at :378 becomes `_OVERRIDE_POLL_S`; `_LONG_RUN_BOUND_S = 15.0` (new, module level) tagged `# @tunable l2.sensortask_integration_long_run_bound_s = 15.0`; each literal at :391, :469 becomes `_LONG_RUN_BOUND_S`; `_WDT_FEED_INTERVAL_S = 1.0` (new, module level) tagged `# @tunable l2.twin_wdt_feed_interval_s = 1.0`; the literal at :446 becomes `_WDT_FEED_INTERVAL_S`; l2.wdt_overrun_wait_s at :461: already created and tagged by A.U8.08; nothing further here; `_WAIT_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l2.sensortask_integration_wait_timeout_s = 5.0`; each literal at :512, :599, :672, :696, :738, :752, :774 becomes `_WAIT_TIMEOUT_S`; `_RESTART_WAIT_TIMEOUT_S = 6.0` (new, module level) tagged `# @tunable l2.sensortask_integration_restart_wait_timeout_s = 6.0`; the literal at :522 becomes `_RESTART_WAIT_TIMEOUT_S`; `_SUPERVISOR_RUN_BOUND_S = 20.0` (new, module level) tagged `# @tunable l2.sensortask_integration_supervisor_run_bound_s = 20.0`; each literal at :548, :818 becomes `_SUPERVISOR_RUN_BOUND_S`; `_HOTSPOT_WAIT_TIMEOUT_S = 25.0` (new, module level) tagged `# @tunable l2.sensortask_integration_hotspot_wait_timeout_s = 25.0`; the literal at :594 becomes `_HOTSPOT_WAIT_TIMEOUT_S`; `_BIND_POLL_S = 0.01` (new, module level) tagged `# @tunable l2.sensortask_integration_bind_poll_s = 0.01`; the literal at :599 becomes `_BIND_POLL_S`; `_HOTSPOT_RUN_BOUND_S = 35.0` (new, module level) tagged `# @tunable l2.sensortask_integration_hotspot_run_bound_s = 35.0`; the literal at :630 becomes `_HOTSPOT_RUN_BOUND_S`; `_REBOOT_RUN_BOUND_S = 30.0` (new, module level) tagged `# @tunable l2.sensortask_integration_reboot_run_bound_s = 30.0`; each literal at :708, :781 becomes `_REBOOT_RUN_BOUND_S`; deferred sleeps (:105, :586, :666, :694, :735, :772): no tag now; classified once U25 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_digital_twin_bus_hazard_concurrency.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08, A.U8C.24, U25
- **Kind**: test

### A.U8C.33 Tag the tuned literals of `test_digital_twin_uart_link.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_digital_twin_uart_link.py` — `l2.uart_link_run_limit_s` :48 (30); `l2.uart_link_listener_settle_s` :103 (5); `l2.uart_link_poll_wait_max_ms` :169 (10); `l2.uart_link_exchange_limit_s` :227, :231, :232, :261, :279, :305 (60); `l2.uart_link_ticker_step_ms` :252, :322 (2); `l2.uart_link_collect_step_ms` :297 (3); `l2.uart_link_max_train_limit_s` :331 (240); `l2.uart_link_hammer_limit_s` :373, :469 (300); `l2.uart_link_churn_step_ms` :404 (1); `l2.uart_link_cancel_settle_ms` :418, :466 (5); `l2.uart_link_churn_limit_s` :420 (180); `l2.uart_link_noise_step_ms` :482 (1)
- **Change**: `_RUN_LIMIT_S = 30` (new, module level) tagged `# @tunable l2.uart_link_run_limit_s = 30`; the literal at :48 becomes `_RUN_LIMIT_S`; `_LISTENER_SETTLE_S = 5` (new, module level) tagged `# @tunable l2.uart_link_listener_settle_s = 5`; the literal at :103 becomes `_LISTENER_SETTLE_S`; `_POLL_WAIT_MAX_MS = 10` (new, module level) tagged `# @tunable l2.uart_link_poll_wait_max_ms = 10`; the literal at :169 becomes `_POLL_WAIT_MAX_MS`; `_EXCHANGE_LIMIT_S = 60` (new, module level) tagged `# @tunable l2.uart_link_exchange_limit_s = 60`; each literal at :227, :231, :232, :261, :279, :305 becomes `_EXCHANGE_LIMIT_S`; `_TICKER_STEP_MS = 2` (new, module level) tagged `# @tunable l2.uart_link_ticker_step_ms = 2`; each literal at :252, :322 becomes `_TICKER_STEP_MS`; `_COLLECT_STEP_MS = 3` (new, module level) tagged `# @tunable l2.uart_link_collect_step_ms = 3`; the literal at :297 becomes `_COLLECT_STEP_MS`; `_MAX_TRAIN_LIMIT_S = 240` (new, module level) tagged `# @tunable l2.uart_link_max_train_limit_s = 240`; the literal at :331 becomes `_MAX_TRAIN_LIMIT_S`; `_HAMMER_LIMIT_S = 300` (new, module level) tagged `# @tunable l2.uart_link_hammer_limit_s = 300`; each literal at :373, :469 becomes `_HAMMER_LIMIT_S`; `_CHURN_STEP_MS = 1` (new, module level) tagged `# @tunable l2.uart_link_churn_step_ms = 1`; the literal at :404 becomes `_CHURN_STEP_MS`; `_CANCEL_SETTLE_MS = 5` (new, module level) tagged `# @tunable l2.uart_link_cancel_settle_ms = 5`; each literal at :418, :466 becomes `_CANCEL_SETTLE_MS`; `_CHURN_LIMIT_S = 180` (new, module level) tagged `# @tunable l2.uart_link_churn_limit_s = 180`; the literal at :420 becomes `_CHURN_LIMIT_S`; `_NOISE_STEP_MS = 1` (new, module level) tagged `# @tunable l2.uart_link_noise_step_ms = 1`; the literal at :482 becomes `_NOISE_STEP_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.34 Tag the tuned literals of `test_framing_codecs.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_framing_codecs.py` — `l1.framing_codecs_run_bound_s` :22 (5)
- **Change**: `_RUN_BOUND_S = 5` (new, module level) tagged `# @tunable l1.framing_codecs_run_bound_s = 5`; the literal at :22 becomes `_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.35 Tag the tuned literals of `test_neopixel_wifi_integration.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_neopixel_wifi_integration.py` — `l1.asy_neopixel_driver_overlay_settle_s` :53, :56, :59, :83 (0.05)
- **Change**: `_OVERLAY_SETTLE_S = 0.05` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_overlay_settle_s = 0.05`; each literal at :53, :56, :59, :83 becomes `_OVERLAY_SETTLE_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_asy_neopixel_driver.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.11
- **Kind**: test

### A.U8C.36 Tag the tuned literals of `test_notification_neopixel_integration.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_notification_neopixel_integration.py` — `l1.asy_notification_service_one_flash_settle_s` :94 (1.3); `l1.asy_notification_service_two_flash_cycle_s` :120 (2.5); `l1.notification_neopixel_integration_mid_ramp_s` :145 (0.1); `l1.notification_neopixel_integration_both_ramps_done_s` :147 (1.5)
- **Change**: `_ONE_FLASH_SETTLE_S = 1.3` (new, module level) tagged `# @tunable l1.asy_notification_service_one_flash_settle_s = 1.3`; the literal at :94 becomes `_ONE_FLASH_SETTLE_S`; `_TWO_FLASH_CYCLE_S = 2.5` (new, module level) tagged `# @tunable l1.asy_notification_service_two_flash_cycle_s = 2.5`; the literal at :120 becomes `_TWO_FLASH_CYCLE_S`; `_MID_RAMP_S = 0.1` (new, module level) tagged `# @tunable l1.notification_neopixel_integration_mid_ramp_s = 0.1`; the literal at :145 becomes `_MID_RAMP_S`; `_BOTH_RAMPS_DONE_S = 1.5` (new, module level) tagged `# @tunable l1.notification_neopixel_integration_both_ramps_done_s = 1.5`; the literal at :147 becomes `_BOTH_RAMPS_DONE_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_asy_notification_service.py`, `tests/test_notification_scd30_integration.py`, `tests/test_notification_scd30_sgp40_integration.py`, `tests/test_notification_sgp40_integration.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.12
- **Kind**: test

### A.U8C.37 Tag the tuned literals of `test_notification_scd30_integration.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_notification_scd30_integration.py` — `l1.asy_notification_service_one_flash_settle_s` :148, :176, :253 (1.3); `l1.notification_scd30_integration_idle_pass_s` :201 (0.2)
- **Change**: `_ONE_FLASH_SETTLE_S = 1.3` (new, module level) tagged `# @tunable l1.asy_notification_service_one_flash_settle_s = 1.3`; each literal at :148, :176, :253 becomes `_ONE_FLASH_SETTLE_S`; `_IDLE_PASS_S = 0.2` (new, module level) tagged `# @tunable l1.notification_scd30_integration_idle_pass_s = 0.2`; the literal at :201 becomes `_IDLE_PASS_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_asy_notification_service.py`, `tests/test_notification_neopixel_integration.py`, `tests/test_notification_scd30_sgp40_integration.py`, `tests/test_notification_sgp40_integration.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.12
- **Kind**: test

### A.U8C.38 Tag the tuned literals of `test_notification_scd30_sgp40_integration.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_notification_scd30_sgp40_integration.py` — `l1.notification_scd30_sgp40_integration_two_signals_done_s` :231 (2.6); `l1.asy_notification_service_one_flash_settle_s` :270 (1.3)
- **Change**: `_TWO_SIGNALS_DONE_S = 2.6` (new, module level) tagged `# @tunable l1.notification_scd30_sgp40_integration_two_signals_done_s = 2.6`; the literal at :231 becomes `_TWO_SIGNALS_DONE_S`; `_ONE_FLASH_SETTLE_S = 1.3` (new, module level) tagged `# @tunable l1.asy_notification_service_one_flash_settle_s = 1.3`; the literal at :270 becomes `_ONE_FLASH_SETTLE_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_asy_notification_service.py`, `tests/test_notification_neopixel_integration.py`, `tests/test_notification_scd30_integration.py`, `tests/test_notification_sgp40_integration.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.12
- **Kind**: test

### A.U8C.39 Tag the tuned literals of `test_notification_sgp40_integration.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_notification_sgp40_integration.py` — `l1.asy_notification_service_one_flash_settle_s` :181, :255 (1.3); `l1.notification_scd30_integration_idle_pass_s` :211 (0.2)
- **Change**: `_ONE_FLASH_SETTLE_S = 1.3` (new, module level) tagged `# @tunable l1.asy_notification_service_one_flash_settle_s = 1.3`; each literal at :181, :255 becomes `_ONE_FLASH_SETTLE_S`; `_IDLE_PASS_S = 0.2` (new, module level) tagged `# @tunable l1.notification_scd30_integration_idle_pass_s = 0.2`; the literal at :211 becomes `_IDLE_PASS_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_asy_notification_service.py`, `tests/test_notification_neopixel_integration.py`, `tests/test_notification_scd30_integration.py`, `tests/test_notification_scd30_sgp40_integration.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.12, A.U8C.37
- **Kind**: test

### A.U8C.40 Tag the tuned literals of `test_ntp_fram_system_integration.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_ntp_fram_system_integration.py` — `ntp.fetch_timeout_ms` :77 (5000); `udp.conn_tries_default` :161 (1); `l1.asy_ntp_client_fake_server_poll_ms` :196, :200 (10); `l1.asy_ntp_client_serve_wait_s` :230 (5); `l1.asy_ntp_client_state_poll_ms` :234 (20); `l1.ntp_fram_system_integration_utc_tolerance_s` :263, :360 (5); `l1.fram_lock_fetch_timeout_ms` :313 (2000); `l1.fram_write_prompt_s` :329 (1.0); `l1.ntp_fram_system_integration_supervisor_scan_wait_s` :443, :550, :614, :644 (2.5); `l1.ntp_fram_system_integration_start_poll_s` :548, :612, :642 (0.01)
- **Change**: mirror tag `# @tunable ntp.fetch_timeout_ms = 5000` above :77; listed as a further site of that row; mirror tag `# @tunable udp.conn_tries_default = 1` above :161; listed as a further site of that row; `_FAKE_SERVER_POLL_MS = 10` (new, module level) tagged `# @tunable l1.asy_ntp_client_fake_server_poll_ms = 10`; each literal at :196, :200 becomes `_FAKE_SERVER_POLL_MS`; `_SERVE_WAIT_S = 5` (new, module level) tagged `# @tunable l1.asy_ntp_client_serve_wait_s = 5`; the literal at :230 becomes `_SERVE_WAIT_S`; `_STATE_POLL_MS = 20` (new, module level) tagged `# @tunable l1.asy_ntp_client_state_poll_ms = 20`; the literal at :234 becomes `_STATE_POLL_MS`; `_UTC_TOLERANCE_S = 5` (new, module level) tagged `# @tunable l1.ntp_fram_system_integration_utc_tolerance_s = 5`; each literal at :263, :360 becomes `_UTC_TOLERANCE_S`; l1.fram_lock_fetch_timeout_ms at :313: already created and tagged by A.U8.17; nothing further here; l1.fram_write_prompt_s at :329: already created and tagged by A.U8.17; nothing further here; `_SUPERVISOR_SCAN_WAIT_S = 2.5` (new, module level) tagged `# @tunable l1.ntp_fram_system_integration_supervisor_scan_wait_s = 2.5`; each literal at :443, :550, :614, :644 becomes `_SUPERVISOR_SCAN_WAIT_S`; `_START_POLL_S = 0.01` (new, module level) tagged `# @tunable l1.ntp_fram_system_integration_start_poll_s = 0.01`; each literal at :548, :612, :642 becomes `_START_POLL_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_asy_ntp_client.py`, `tests/test_ntp_wifi_dns_integration.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.09, A.U8.11, A.U8.17, A.U8C.13; A.U8.17 (`:313`, `:329`)
- **Kind**: test

### A.U8C.41 Tag the tuned literals of `test_ntp_wifi_dns_integration.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_ntp_wifi_dns_integration.py` — `l1.ntp_wifi_dns_integration_lock_blocked_wait_s` :229 (0.05); `udp.conn_tries_default` :274 (1); `l1.asy_ntp_client_fake_server_poll_ms` :312, :316 (10); `l1.asy_ntp_client_serve_wait_s` :347 (5); `l1.asy_ntp_client_state_poll_ms` :351 (20); `l1.asy_ntp_client_no_reply_fetch_timeout_ms` :379 (100); `l1.ntp_wifi_dns_integration_past_fetch_timeout_ms` :388 (150)
- **Change**: `_LOCK_BLOCKED_WAIT_S = 0.05` (new, module level) tagged `# @tunable l1.ntp_wifi_dns_integration_lock_blocked_wait_s = 0.05`; the literal at :229 becomes `_LOCK_BLOCKED_WAIT_S`; mirror tag `# @tunable udp.conn_tries_default = 1` above :274; listed as a further site of that row; `_FAKE_SERVER_POLL_MS = 10` (new, module level) tagged `# @tunable l1.asy_ntp_client_fake_server_poll_ms = 10`; each literal at :312, :316 becomes `_FAKE_SERVER_POLL_MS`; `_SERVE_WAIT_S = 5` (new, module level) tagged `# @tunable l1.asy_ntp_client_serve_wait_s = 5`; the literal at :347 becomes `_SERVE_WAIT_S`; `_STATE_POLL_MS = 20` (new, module level) tagged `# @tunable l1.asy_ntp_client_state_poll_ms = 20`; the literal at :351 becomes `_STATE_POLL_MS`; `_NO_REPLY_FETCH_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l1.asy_ntp_client_no_reply_fetch_timeout_ms = 100`; the literal at :379 becomes `_NO_REPLY_FETCH_TIMEOUT_MS`; `_PAST_FETCH_TIMEOUT_MS = 150` (new, module level) tagged `# @tunable l1.ntp_wifi_dns_integration_past_fetch_timeout_ms = 150`; the literal at :388 becomes `_PAST_FETCH_TIMEOUT_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/test_asy_ntp_client.py`, `tests/test_ntp_fram_system_integration.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.11, A.U8C.13
- **Kind**: test

### A.U8C.42 Tag the tuned literals of `test_system_service.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_system_service.py` — `system.reset_delay_s` :623 (1000/4); `l1.system_service_run_bound_s` :1249 (5)
- **Change**: mirror `system.reset_delay_s` at :623: already named by A.U8.08; it gets the tag there; `_RUN_BOUND_S = 5` (new, module level) tagged `# @tunable l1.system_service_run_bound_s = 5`; the literal at :1249 becomes `_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.43 Tag the tuned literals of `test_uart_comm_hazard.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits; G8/R31 (the `limit=`/`wait_for` bounds); G4/R54 "allocation and heap-rate budgets" (`_WARMUP`, `_MEASURED`, `_HAMMER_ROUNDS`)
- **Site**: `tests/test_uart_comm_hazard.py` — `l1.uart_comm_hazard_timeout_ms` :33 (30); `l1.uart_comm_hazard_limit_s` :109, :311, :328, :337, :570, :587, :628, :637, :658, :659, :673, :674 (10); `l1.uart_comm_hazard_task_bound_s` :128, :150, :174, :175, :194 (8); `l1.uart_comm_hazard_listener_settle_ms` :129, :151, :176, :221, :354, :359, :376, :381, :397, :401, :418, :423, :440, :445 (5); `l1.uart_comm_hazard_concurrency_limit_s` :133, :155, :181, :225 (25); `l1.uart_comm_hazard_lock_take_ms` :148 (1); `l1.uart_comm_hazard_in_flight_ms` :173, :597 (2); `l1.uart_comm_hazard_listener_park_ms` :193, :583 (5); `l1.uart_comm_hazard_exchange_limit_s` :198, :601, :618, :654, :660, :670, :675, :697, :716, :725, :749, :777, :871, :1101, :1229 (20); `l1.uart_comm_hazard_recovery_limit_s` :363, :385, :405, :427, :449, :872, :918, :919, :975, :976, :1080, :1081, :1176, :1211 (30); `l1.uart_comm_hazard_warmup_rounds` :457 (20); `l1.uart_comm_hazard_measured_rounds` :458 (100); `l1.uart_comm_hazard_retention_limit_s` :531, :853, :909 (120); `l1.uart_comm_hazard_step_bound_s` :585, :599, :609, :693, :694, :826, :849, :891, :1135, :1163, :1188 (5); `l1.uart_comm_hazard_fragment_gap_ms` :690 (3); `l1.uart_comm_hazard_mismatch_limit_s` :832, :923, :970, :973, :980, :1084, :1141, :1167, :1192, :1206, :1215 (60); `l1.uart_comm_hazard_hammer_rounds` :993 (150); `l1.uart_comm_hazard_hammer_limit_s` :1026, :1072 (300); `gc.threshold_bytes` :1247 (32768)
- **Change**: tag `# @tunable l1.uart_comm_hazard_timeout_ms = 30` above `_TIMEOUT_MS` (:33); `_LIMIT_S = 10` (new, module level) tagged `# @tunable l1.uart_comm_hazard_limit_s = 10`; each literal at :109, :311, :328, :337, :570, :587, :628, :637, :658, :659, :673, :674 becomes `_LIMIT_S`; `_TASK_BOUND_S = 8` (new, module level) tagged `# @tunable l1.uart_comm_hazard_task_bound_s = 8`; each literal at :128, :150, :174, :175, :194 becomes `_TASK_BOUND_S`; `_LISTENER_SETTLE_MS = 5` (new, module level) tagged `# @tunable l1.uart_comm_hazard_listener_settle_ms = 5`; each literal at :129, :151, :176, :221, :354, :359, :376, :381, :397, :401, :418, :423, :440, :445 becomes `_LISTENER_SETTLE_MS`; `_CONCURRENCY_LIMIT_S = 25` (new, module level) tagged `# @tunable l1.uart_comm_hazard_concurrency_limit_s = 25`; each literal at :133, :155, :181, :225 becomes `_CONCURRENCY_LIMIT_S`; `_LOCK_TAKE_MS = 1` (new, module level) tagged `# @tunable l1.uart_comm_hazard_lock_take_ms = 1`; the literal at :148 becomes `_LOCK_TAKE_MS`; `_IN_FLIGHT_MS = 2` (new, module level) tagged `# @tunable l1.uart_comm_hazard_in_flight_ms = 2`; each literal at :173, :597 becomes `_IN_FLIGHT_MS`; `_LISTENER_PARK_MS = 5` (new, module level) tagged `# @tunable l1.uart_comm_hazard_listener_park_ms = 5`; each literal at :193, :583 becomes `_LISTENER_PARK_MS`; `_EXCHANGE_LIMIT_S = 20` (new, module level) tagged `# @tunable l1.uart_comm_hazard_exchange_limit_s = 20`; each literal at :198, :601, :618, :654, :660, :670, :675, :697, :716, :725, :749, :777, :871, :1101, :1229 becomes `_EXCHANGE_LIMIT_S`; `_RECOVERY_LIMIT_S = 30` (new, module level) tagged `# @tunable l1.uart_comm_hazard_recovery_limit_s = 30`; each literal at :363, :385, :405, :427, :449, :872, :918, :919, :975, :976, :1080, :1081, :1176, :1211 becomes `_RECOVERY_LIMIT_S`; tag `# @tunable l1.uart_comm_hazard_warmup_rounds = 20` above `_WARMUP` (:457); tag `# @tunable l1.uart_comm_hazard_measured_rounds = 100` above `_MEASURED` (:458); `_RETENTION_LIMIT_S = 120` (new, module level) tagged `# @tunable l1.uart_comm_hazard_retention_limit_s = 120`; each literal at :531, :853, :909 becomes `_RETENTION_LIMIT_S`; `_STEP_BOUND_S = 5` (new, module level) tagged `# @tunable l1.uart_comm_hazard_step_bound_s = 5`; each literal at :585, :599, :609, :693, :694, :826, :849, :891, :1135, :1163, :1188 becomes `_STEP_BOUND_S`; `_FRAGMENT_GAP_MS = 3` (new, module level) tagged `# @tunable l1.uart_comm_hazard_fragment_gap_ms = 3`; the literal at :690 becomes `_FRAGMENT_GAP_MS`; `_MISMATCH_LIMIT_S = 60` (new, module level) tagged `# @tunable l1.uart_comm_hazard_mismatch_limit_s = 60`; each literal at :832, :923, :970, :973, :980, :1084, :1141, :1167, :1192, :1206, :1215 becomes `_MISMATCH_LIMIT_S`; tag `# @tunable l1.uart_comm_hazard_hammer_rounds = 150` above `_HAMMER_ROUNDS` (:993); `_HAMMER_LIMIT_S = 300` (new, module level) tagged `# @tunable l1.uart_comm_hazard_hammer_limit_s = 300`; each literal at :1026, :1072 becomes `_HAMMER_LIMIT_S`; mirror `gc.threshold_bytes` at :1247: already named by A.U8.14; it gets the tag there. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — · generated — · js — · tests this file only (behaviour unchanged) · twin — · docs SPEC Part N rows; SPEC J.7 (derivation of `_TIMEOUT_MS`'s sustained budget) cites `l1.uart_comm_hazard_timeout_ms` · toml — · uart — (test-only; no changelog entry)
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.14
- **Kind**: test

### A.U8C.44 Tag the tuned literals of `bench/dns_probe.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench/dns_probe.py` — `l4.dns_probe_query_timeout_s` :27 (5.0)
- **Change**: `_QUERY_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l4.dns_probe_query_timeout_s = 5.0`; the literal at :27 becomes `_QUERY_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.45 Tag the tuned literals of `bench/test_bus_concurrency_under_api_load.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench/test_bus_concurrency_under_api_load.py` — `l4.bus_concurrency_under_api_load_get_iterations` :27 (8); `l4.bus_concurrency_under_api_load_put_reset_count` :28 (2); `l4.bus_concurrency_under_api_load_fetch_timeout_s` :42, :94, :107, :416, :437, :506, :528 (15.0); `l4.bus_concurrency_under_api_load_ceiling_retry_backoff_s` :54 (0.25); `l4.bus_concurrency_under_api_load_join_timeout_s` :119, :450, :541 (120.0); `l4.bus_concurrency_under_api_load_probe_timeout_s` :128, :142, :211, :232, :237, :278, :367, :378, :402, :456, :464, :492, :545, :551 (10.0); `l4.bus_concurrency_under_api_load_recovery_timeout_s` :129, :212, :242, :465, :552 (30.0); `l4.bus_concurrency_under_api_load_recovery_poll_s` :130, :213, :242, :466, :553 (2.0); `l4.bus_concurrency_under_api_load_degraded_fetch_timeout_s` :175, :186, :255, :266, :297, :324, :335 (20.0); `l4.bus_concurrency_under_api_load_degraded_join_timeout_s` :201, :288, :358 (180.0); `l4.bus_concurrency_under_api_load_ntp_resync_timeout_s` :297 (20.0); `l4.bus_concurrency_under_api_load_ntp_resync_poll_s` :297 (1.0); `l4.network_resilience_flap_step_s` :348, :350 (3.0); `l4.bus_concurrency_under_api_load_flap_recovery_timeout_s` :368 (150.0); `l4.bus_concurrency_under_api_load_flap_recovery_poll_s` :369 (5.0); `l4.bus_concurrency_under_api_load_reboot_ready_timeout_s` :378 (60.0); `l4.bus_concurrency_under_api_load_reboot_ready_poll_s` :378 (3.0); `l4.bus_concurrency_under_api_load_isl29125_write_cycles` :395 (4)
- **Change**: tag `# @tunable l4.bus_concurrency_under_api_load_get_iterations = 8` above `_GET_ITERATIONS_PER_WORKER` (:27); tag `# @tunable l4.bus_concurrency_under_api_load_put_reset_count = 2` above `_PUT_RESET_COUNT` (:28); `_FETCH_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_fetch_timeout_s = 15.0`; each literal at :42, :94, :107, :416, :437, :506, :528 becomes `_FETCH_TIMEOUT_S`; `_CEILING_RETRY_BACKOFF_S = 0.25` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_ceiling_retry_backoff_s = 0.25`; the literal at :54 becomes `_CEILING_RETRY_BACKOFF_S`; `_JOIN_TIMEOUT_S = 120.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_join_timeout_s = 120.0`; each literal at :119, :450, :541 becomes `_JOIN_TIMEOUT_S`; `_PROBE_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_probe_timeout_s = 10.0`; each literal at :128, :142, :211, :232, :237, :278, :367, :378, :402, :456, :464, :492, :545, :551 becomes `_PROBE_TIMEOUT_S`; `_RECOVERY_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_recovery_timeout_s = 30.0`; each literal at :129, :212, :242, :465, :552 becomes `_RECOVERY_TIMEOUT_S`; `_RECOVERY_POLL_S = 2.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_recovery_poll_s = 2.0`; each literal at :130, :213, :242, :466, :553 becomes `_RECOVERY_POLL_S`; `_DEGRADED_FETCH_TIMEOUT_S = 20.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_degraded_fetch_timeout_s = 20.0`; each literal at :175, :186, :255, :266, :297, :324, :335 becomes `_DEGRADED_FETCH_TIMEOUT_S`; `_DEGRADED_JOIN_TIMEOUT_S = 180.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_degraded_join_timeout_s = 180.0`; each literal at :201, :288, :358 becomes `_DEGRADED_JOIN_TIMEOUT_S`; `_NTP_RESYNC_TIMEOUT_S = 20.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_ntp_resync_timeout_s = 20.0`; the literal at :297 becomes `_NTP_RESYNC_TIMEOUT_S`; `_NTP_RESYNC_POLL_S = 1.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_ntp_resync_poll_s = 1.0`; the literal at :297 becomes `_NTP_RESYNC_POLL_S`; `_FLAP_STEP_S = 3.0` (new, module level) tagged `# @tunable l4.network_resilience_flap_step_s = 3.0`; each literal at :348, :350 becomes `_FLAP_STEP_S`; `_FLAP_RECOVERY_TIMEOUT_S = 150.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_flap_recovery_timeout_s = 150.0`; the literal at :368 becomes `_FLAP_RECOVERY_TIMEOUT_S`; `_FLAP_RECOVERY_POLL_S = 5.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_flap_recovery_poll_s = 5.0`; the literal at :369 becomes `_FLAP_RECOVERY_POLL_S`; `_REBOOT_READY_TIMEOUT_S = 60.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_reboot_ready_timeout_s = 60.0`; the literal at :378 becomes `_REBOOT_READY_TIMEOUT_S`; `_REBOOT_READY_POLL_S = 3.0` (new, module level) tagged `# @tunable l4.bus_concurrency_under_api_load_reboot_ready_poll_s = 3.0`; the literal at :378 becomes `_REBOOT_READY_POLL_S`; tag `# @tunable l4.bus_concurrency_under_api_load_isl29125_write_cycles = 4` above `_ISL29125_WRITE_CYCLES` (:395). Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/bench/test_network_resilience.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.46 Tag the tuned literals of `bench/test_end_to_end_timing.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench/test_end_to_end_timing.py` — `l4.end_to_end_timing_reboot_phase_timeout_s` :40, :41, :49, :53 (30.0); `l4.end_to_end_timing_down_poll_s` :40 (0.5); `l4.end_to_end_timing_poll_s` :41, :106, :154, :163, :201 (1.0); `l4.end_to_end_timing_ready_probe_timeout_s` :46, :115 (5.0); `l4.end_to_end_timing_serving_poll_s` :49, :53, :192 (2.0); `l4.end_to_end_timing_probe_timeout_s` :72, :88, :130, :136, :173, :183, :204, :211 (10.0); `l4.end_to_end_timing_join_timeout_s` :81 (15.0); `l4.end_to_end_timing_recovery_sanity_timeout_s` :105 (120.0); `l4.end_to_end_timing_reset_spacing_s` :143 (25.0); `l4.end_to_end_timing_reset_recovery_timeout_s` :153, :162, :200 (60.0); `l4.end_to_end_timing_backup_advance_timeout_s` :177 (90.0); `l4.end_to_end_timing_backup_poll_s` :178 (5.0); `l4.end_to_end_timing_restore_recovery_timeout_s` :191 (20.0)
- **Change**: `_REBOOT_PHASE_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_reboot_phase_timeout_s = 30.0`; each literal at :40, :41, :49, :53 becomes `_REBOOT_PHASE_TIMEOUT_S`; `_DOWN_POLL_S = 0.5` (new, module level) tagged `# @tunable l4.end_to_end_timing_down_poll_s = 0.5`; the literal at :40 becomes `_DOWN_POLL_S`; `_POLL_S = 1.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_poll_s = 1.0`; each literal at :41, :106, :154, :163, :201 becomes `_POLL_S`; `_READY_PROBE_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_ready_probe_timeout_s = 5.0`; each literal at :46, :115 becomes `_READY_PROBE_TIMEOUT_S`; `_SERVING_POLL_S = 2.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_serving_poll_s = 2.0`; each literal at :49, :53, :192 becomes `_SERVING_POLL_S`; `_PROBE_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_probe_timeout_s = 10.0`; each literal at :72, :88, :130, :136, :173, :183, :204, :211 becomes `_PROBE_TIMEOUT_S`; `_JOIN_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_join_timeout_s = 15.0`; the literal at :81 becomes `_JOIN_TIMEOUT_S`; `_RECOVERY_SANITY_TIMEOUT_S = 120.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_recovery_sanity_timeout_s = 120.0`; the literal at :105 becomes `_RECOVERY_SANITY_TIMEOUT_S`; `_RESET_SPACING_S = 25.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_reset_spacing_s = 25.0`; the literal at :143 becomes `_RESET_SPACING_S`; `_RESET_RECOVERY_TIMEOUT_S = 60.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_reset_recovery_timeout_s = 60.0`; each literal at :153, :162, :200 becomes `_RESET_RECOVERY_TIMEOUT_S`; `_BACKUP_ADVANCE_TIMEOUT_S = 90.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_backup_advance_timeout_s = 90.0`; the literal at :177 becomes `_BACKUP_ADVANCE_TIMEOUT_S`; `_BACKUP_POLL_S = 5.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_backup_poll_s = 5.0`; the literal at :178 becomes `_BACKUP_POLL_S`; `_RESTORE_RECOVERY_TIMEOUT_S = 20.0` (new, module level) tagged `# @tunable l4.end_to_end_timing_restore_recovery_timeout_s = 20.0`; the literal at :191 becomes `_RESTORE_RECOVERY_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.47 Tag the tuned literals of `bench/test_heap_under_connection_ceiling.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits; G1/R15 "every instrument value is a registered tunable" (`:49` joins the instrument rows); G8/R31 (join and script bounds)
- **Site**: `tests_hardware/bench/test_heap_under_connection_ceiling.py` — `web.max_content_length` :25 (2048); `l4.ceiling_hold_s` :27 (55.0); `l4.ceiling_drip_interval_s` :31 (2.0); `l4.ceiling_recycle_s` :34 (10.0); `l4.ceiling_min_fraction_at_ceiling` :37 (0.55); `l4.ceiling_admission_wait_s` :40 (0.3); `l4.ceiling_holder_socket_timeout_s` :49 (5.0); `l4.heap_under_connection_ceiling_worker_join_s` :109 (10.0); `l4.heap_under_connection_ceiling_script_timeout_s` :121 (240.0); `l4.heap_under_connection_ceiling_hammer_join_s` :124 (30.0)
- **Change**: mirror `web.max_content_length` at :25: already named by A.U8.05; it gets the tag there; l4.ceiling_hold_s at :27: already created and tagged by A.U8.05; nothing further here; l4.ceiling_drip_interval_s at :31: already created and tagged by A.U8.05; nothing further here; l4.ceiling_recycle_s at :34: already created and tagged by A.U8.05; nothing further here; l4.ceiling_min_fraction_at_ceiling at :37: already created and tagged by A.U8.05; nothing further here; l4.ceiling_admission_wait_s at :40: already created and tagged by A.U8.05; nothing further here; `_HOLDER_SOCKET_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l4.ceiling_holder_socket_timeout_s = 5.0`; the literal at :49 becomes `_HOLDER_SOCKET_TIMEOUT_S`; `_WORKER_JOIN_S = 10.0` (new, module level) tagged `# @tunable l4.heap_under_connection_ceiling_worker_join_s = 10.0`; the literal at :109 becomes `_WORKER_JOIN_S`; `_SCRIPT_TIMEOUT_S = 240.0` (new, module level) tagged `# @tunable l4.heap_under_connection_ceiling_script_timeout_s = 240.0`; the literal at :121 becomes `_SCRIPT_TIMEOUT_S`; `_HAMMER_JOIN_S = 30.0` (new, module level) tagged `# @tunable l4.heap_under_connection_ceiling_hammer_join_s = 30.0`; the literal at :124 becomes `_HAMMER_JOIN_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.04, A.U8.05; A.U8.05 (`:25-40`)
- **Kind**: test

### A.U8C.48 Tag the tuned literals of `bench/test_hotspot_role_reversal.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench/test_hotspot_role_reversal.py` — `l4.hotspot_role_reversal_join_attempts` :27 (5); `l4.conftest_join_hotspot_timeout_s` :33 (45.0); `l4.conftest_hotspot_scan_timeout_s` :38, :80 (30.0); `l4.conftest_hotspot_scan_poll_s` :38, :80 (2.0); `l4.hotspot_role_reversal_probe_timeout_s` :68, :270, :287, :324, :348, :363 (10.0); `l4.hotspot_role_reversal_dhcp_timeout_s` :86, :187 (45.0); `l4.hotspot_role_reversal_dhcp_poll_s` :86, :187 (2.0); `l4.hotspot_role_reversal_restore_put_timeout_s` :95 (15.0); `l4.hotspot_role_reversal_flip_back_timeout_s` :109 (90.0); `l4.hotspot_role_reversal_flip_back_poll_s` :109 (3.0); `l4.hotspot_role_reversal_recovery_timeout_s` :115 (30.0); `l4.hotspot_role_reversal_recovery_poll_s` :115 (1.0); `l4.hotspot_role_reversal_ready_probe_timeout_s` :121 (5.0); `l4.hotspot_role_reversal_reassoc_visible_timeout_s` :185, :361 (15.0); `l4.hotspot_role_reversal_reassoc_visible_poll_s` :185, :361 (1.0); `l4.hotspot_role_reversal_dns_flood_s` :251 (3.0); `l4.hotspot_role_reversal_dns_flood_step_s` :254 (0.05); `l4.hotspot_role_reversal_dns_recovery_timeout_s` :258 (8.0); `l4.hotspot_role_reversal_raw_socket_timeout_s` :300, :339 (10.0)
- **Change**: `_JOIN_ATTEMPTS = 5` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_join_attempts = 5`; the literal at :27 becomes `_JOIN_ATTEMPTS`; `_JOIN_HOTSPOT_TIMEOUT_S = 45.0` (new, module level) tagged `# @tunable l4.conftest_join_hotspot_timeout_s = 45.0`; the literal at :33 becomes `_JOIN_HOTSPOT_TIMEOUT_S`; `_HOTSPOT_SCAN_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.conftest_hotspot_scan_timeout_s = 30.0`; each literal at :38, :80 becomes `_HOTSPOT_SCAN_TIMEOUT_S`; `_HOTSPOT_SCAN_POLL_S = 2.0` (new, module level) tagged `# @tunable l4.conftest_hotspot_scan_poll_s = 2.0`; each literal at :38, :80 becomes `_HOTSPOT_SCAN_POLL_S`; `_PROBE_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_probe_timeout_s = 10.0`; each literal at :68, :270, :287, :324, :348, :363 becomes `_PROBE_TIMEOUT_S`; `_DHCP_TIMEOUT_S = 45.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_dhcp_timeout_s = 45.0`; each literal at :86, :187 becomes `_DHCP_TIMEOUT_S`; `_DHCP_POLL_S = 2.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_dhcp_poll_s = 2.0`; each literal at :86, :187 becomes `_DHCP_POLL_S`; `_RESTORE_PUT_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_restore_put_timeout_s = 15.0`; the literal at :95 becomes `_RESTORE_PUT_TIMEOUT_S`; `_FLIP_BACK_TIMEOUT_S = 90.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_flip_back_timeout_s = 90.0`; the literal at :109 becomes `_FLIP_BACK_TIMEOUT_S`; `_FLIP_BACK_POLL_S = 3.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_flip_back_poll_s = 3.0`; the literal at :109 becomes `_FLIP_BACK_POLL_S`; `_RECOVERY_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_recovery_timeout_s = 30.0`; the literal at :115 becomes `_RECOVERY_TIMEOUT_S`; `_RECOVERY_POLL_S = 1.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_recovery_poll_s = 1.0`; the literal at :115 becomes `_RECOVERY_POLL_S`; `_READY_PROBE_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_ready_probe_timeout_s = 5.0`; the literal at :121 becomes `_READY_PROBE_TIMEOUT_S`; `_REASSOC_VISIBLE_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_reassoc_visible_timeout_s = 15.0`; each literal at :185, :361 becomes `_REASSOC_VISIBLE_TIMEOUT_S`; `_REASSOC_VISIBLE_POLL_S = 1.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_reassoc_visible_poll_s = 1.0`; each literal at :185, :361 becomes `_REASSOC_VISIBLE_POLL_S`; `_DNS_FLOOD_S = 3.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_dns_flood_s = 3.0`; the literal at :251 becomes `_DNS_FLOOD_S`; `_DNS_FLOOD_STEP_S = 0.05` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_dns_flood_step_s = 0.05`; the literal at :254 becomes `_DNS_FLOOD_STEP_S`; `_DNS_RECOVERY_TIMEOUT_S = 8.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_dns_recovery_timeout_s = 8.0`; the literal at :258 becomes `_DNS_RECOVERY_TIMEOUT_S`; `_RAW_SOCKET_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_raw_socket_timeout_s = 10.0`; each literal at :300, :339 becomes `_RAW_SOCKET_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/bench/test_network_resilience.py`, `tests_hardware/conftest.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.49 Tag the tuned literals of `bench/test_memory_stress_bench.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench/test_memory_stress_bench.py` — `l4.memory_stress_bench_hammer_duration_s` :27 (120.0); `l4.memory_stress_bench_fetch_timeout_s` :46, :63, :151 (5.0); `l4.memory_stress_bench_join_timeout_s` :82, :164 (10.0)
- **Change**: tag `# @tunable l4.memory_stress_bench_hammer_duration_s = 120.0` above `_HAMMER_DURATION_S` (:27); `_FETCH_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l4.memory_stress_bench_fetch_timeout_s = 5.0`; each literal at :46, :63, :151 becomes `_FETCH_TIMEOUT_S`; `_JOIN_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.memory_stress_bench_join_timeout_s = 10.0`; each literal at :82, :164 becomes `_JOIN_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.50 Tag the tuned literals of `bench/test_network_resilience.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench/test_network_resilience.py` — `l4.network_resilience_outage_s` :44 (15.0); `l4.network_resilience_outage_reconnect_timeout_s` :57, :95 (150.0); `l4.network_resilience_outage_reconnect_poll_s` :58, :96 (5.0); `l4.network_resilience_reconnect_timeout_s` :67, :105, :198, :228, :319, :323, :346, :350, :410, :414, :554, :584, :591 (60.0); `l4.network_resilience_reconnect_poll_s` :67, :105, :150, :199, :229, :319, :323, :346, :350, :410, :414, :487, :584, :591 (3.0); `l4.network_resilience_probe_timeout_s` :70, :108, :180, :254, :259, :273, :374, :401, :431, :441, :459, :465, :476, :510, :520, :581, :606, :685, :706, :741, :754, :783, :822, :836, :894, :917, :927, :968, :990 (10.0); `l4.network_resilience_flap_step_s` :80, :82 (3.0); `l4.network_resilience_ready_probe_timeout_s` :128, :163, :210, :240, :597 (5.0); `l4.network_resilience_degraded_reconnect_timeout_s` :149 (90.0); `l4.network_resilience_crash_check_tail_s` :156, :205, :235 (5.0); `l4.network_resilience_wait_timeout_s` :164, :211, :241, :265, :453, :483, :571 (30.0); `l4.network_resilience_wait_poll_s` :165, :212, :242, :265, :454, :483, :555, :571 (2.0); `l4.network_resilience_probe_spacing_s` :182 (1.0); `l4.network_resilience_ntp_fail_wait_s` :275 (8.0); `l4.network_resilience_ntp_resync_timeout_s` :281 (20.0); `l4.network_resilience_quick_poll_s` :281, :687, :896 (1.0); `l4.network_resilience_rogue_tail_s` :304, :335 (90.0); `l4.bench_control_udp_capture_timeout_s` :391 (55.0); `l4.network_resilience_rtc_write_wait_s` :400 (3.0); `l4.network_resilience_ntp_resync_after_reset_timeout_s` :487 (120.0); `l4.network_resilience_no_ap_tail_s` :530 (15.0); `l4.conftest_join_hotspot_timeout_s` :563 (45.0); `l4.network_resilience_join_retry_backoff_s` :568 (3.0); `l4.hotspot_role_reversal_dhcp_timeout_s` :569 (45.0); `l4.hotspot_role_reversal_dhcp_poll_s` :569 (2.0); `l4.network_resilience_slot_release_wait_s` :633, :673, :849, :1049, :1064, :1079, :1101 (1.0); `l4.network_resilience_raw_socket_timeout_s` :642, :656, :721, :981 (10.0); `l4.network_resilience_held_admit_wait_s` :649 (2.0); `l4.network_resilience_admitted_silence_s` :662 (1.0); `l4.network_resilience_quick_recovery_timeout_s` :686, :895 (15.0); `web.max_content_length` :768 (2048); `l4.network_resilience_loaded_fetch_timeout_s` :860, :1041, :1076, :1086 (30.0); `l4.network_resilience_storm_join_s` :873 (60.0); `l4.network_resilience_slowloris_socket_timeout_s` :950 (30.0); `l4.network_resilience_trickle_step_s` :959 (3.0); `l4.network_resilience_burst_join_s` :1054, :1096 (40.0); `l4.network_resilience_served_elapsed_max_s` :1063 (30.0)
- **Change**: `_OUTAGE_S = 15.0` (new, module level) tagged `# @tunable l4.network_resilience_outage_s = 15.0`; the literal at :44 becomes `_OUTAGE_S`; `_OUTAGE_RECONNECT_TIMEOUT_S = 150.0` (new, module level) tagged `# @tunable l4.network_resilience_outage_reconnect_timeout_s = 150.0`; each literal at :57, :95 becomes `_OUTAGE_RECONNECT_TIMEOUT_S`; `_OUTAGE_RECONNECT_POLL_S = 5.0` (new, module level) tagged `# @tunable l4.network_resilience_outage_reconnect_poll_s = 5.0`; each literal at :58, :96 becomes `_OUTAGE_RECONNECT_POLL_S`; `_RECONNECT_TIMEOUT_S = 60.0` (new, module level) tagged `# @tunable l4.network_resilience_reconnect_timeout_s = 60.0`; each literal at :67, :105, :198, :228, :319, :323, :346, :350, :410, :414, :554, :584, :591 becomes `_RECONNECT_TIMEOUT_S`; `_RECONNECT_POLL_S = 3.0` (new, module level) tagged `# @tunable l4.network_resilience_reconnect_poll_s = 3.0`; each literal at :67, :105, :150, :199, :229, :319, :323, :346, :350, :410, :414, :487, :584, :591 becomes `_RECONNECT_POLL_S`; `_PROBE_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.network_resilience_probe_timeout_s = 10.0`; each literal at :70, :108, :180, :254, :259, :273, :374, :401, :431, :441, :459, :465, :476, :510, :520, :581, :606, :685, :706, :741, :754, :783, :822, :836, :894, :917, :927, :968, :990 becomes `_PROBE_TIMEOUT_S`; `_FLAP_STEP_S = 3.0` (new, module level) tagged `# @tunable l4.network_resilience_flap_step_s = 3.0`; each literal at :80, :82 becomes `_FLAP_STEP_S`; `_READY_PROBE_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l4.network_resilience_ready_probe_timeout_s = 5.0`; each literal at :128, :163, :210, :240, :597 becomes `_READY_PROBE_TIMEOUT_S`; `_DEGRADED_RECONNECT_TIMEOUT_S = 90.0` (new, module level) tagged `# @tunable l4.network_resilience_degraded_reconnect_timeout_s = 90.0`; the literal at :149 becomes `_DEGRADED_RECONNECT_TIMEOUT_S`; `_CRASH_CHECK_TAIL_S = 5.0` (new, module level) tagged `# @tunable l4.network_resilience_crash_check_tail_s = 5.0`; each literal at :156, :205, :235 becomes `_CRASH_CHECK_TAIL_S`; `_WAIT_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.network_resilience_wait_timeout_s = 30.0`; each literal at :164, :211, :241, :265, :453, :483, :571 becomes `_WAIT_TIMEOUT_S`; `_WAIT_POLL_S = 2.0` (new, module level) tagged `# @tunable l4.network_resilience_wait_poll_s = 2.0`; each literal at :165, :212, :242, :265, :454, :483, :555, :571 becomes `_WAIT_POLL_S`; `_PROBE_SPACING_S = 1.0` (new, module level) tagged `# @tunable l4.network_resilience_probe_spacing_s = 1.0`; the literal at :182 becomes `_PROBE_SPACING_S`; `_NTP_FAIL_WAIT_S = 8.0` (new, module level) tagged `# @tunable l4.network_resilience_ntp_fail_wait_s = 8.0`; the literal at :275 becomes `_NTP_FAIL_WAIT_S`; `_NTP_RESYNC_TIMEOUT_S = 20.0` (new, module level) tagged `# @tunable l4.network_resilience_ntp_resync_timeout_s = 20.0`; the literal at :281 becomes `_NTP_RESYNC_TIMEOUT_S`; `_QUICK_POLL_S = 1.0` (new, module level) tagged `# @tunable l4.network_resilience_quick_poll_s = 1.0`; each literal at :281, :687, :896 becomes `_QUICK_POLL_S`; `_ROGUE_TAIL_S = 90.0` (new, module level) tagged `# @tunable l4.network_resilience_rogue_tail_s = 90.0`; each literal at :304, :335 becomes `_ROGUE_TAIL_S`; `_UDP_CAPTURE_TIMEOUT_S = 55.0` (new, module level) tagged `# @tunable l4.bench_control_udp_capture_timeout_s = 55.0`; the literal at :391 becomes `_UDP_CAPTURE_TIMEOUT_S`; `_RTC_WRITE_WAIT_S = 3.0` (new, module level) tagged `# @tunable l4.network_resilience_rtc_write_wait_s = 3.0`; the literal at :400 becomes `_RTC_WRITE_WAIT_S`; `_NTP_RESYNC_AFTER_RESET_TIMEOUT_S = 120.0` (new, module level) tagged `# @tunable l4.network_resilience_ntp_resync_after_reset_timeout_s = 120.0`; the literal at :487 becomes `_NTP_RESYNC_AFTER_RESET_TIMEOUT_S`; `_NO_AP_TAIL_S = 15.0` (new, module level) tagged `# @tunable l4.network_resilience_no_ap_tail_s = 15.0`; the literal at :530 becomes `_NO_AP_TAIL_S`; `_JOIN_HOTSPOT_TIMEOUT_S = 45.0` (new, module level) tagged `# @tunable l4.conftest_join_hotspot_timeout_s = 45.0`; the literal at :563 becomes `_JOIN_HOTSPOT_TIMEOUT_S`; `_JOIN_RETRY_BACKOFF_S = 3.0` (new, module level) tagged `# @tunable l4.network_resilience_join_retry_backoff_s = 3.0`; the literal at :568 becomes `_JOIN_RETRY_BACKOFF_S`; `_DHCP_TIMEOUT_S = 45.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_dhcp_timeout_s = 45.0`; the literal at :569 becomes `_DHCP_TIMEOUT_S`; `_DHCP_POLL_S = 2.0` (new, module level) tagged `# @tunable l4.hotspot_role_reversal_dhcp_poll_s = 2.0`; the literal at :569 becomes `_DHCP_POLL_S`; `_SLOT_RELEASE_WAIT_S = 1.0` (new, module level) tagged `# @tunable l4.network_resilience_slot_release_wait_s = 1.0`; each literal at :633, :673, :849, :1049, :1064, :1079, :1101 becomes `_SLOT_RELEASE_WAIT_S`; `_RAW_SOCKET_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.network_resilience_raw_socket_timeout_s = 10.0`; each literal at :642, :656, :721, :981 becomes `_RAW_SOCKET_TIMEOUT_S`; `_HELD_ADMIT_WAIT_S = 2.0` (new, module level) tagged `# @tunable l4.network_resilience_held_admit_wait_s = 2.0`; the literal at :649 becomes `_HELD_ADMIT_WAIT_S`; `_ADMITTED_SILENCE_S = 1.0` (new, module level) tagged `# @tunable l4.network_resilience_admitted_silence_s = 1.0`; the literal at :662 becomes `_ADMITTED_SILENCE_S`; `_QUICK_RECOVERY_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l4.network_resilience_quick_recovery_timeout_s = 15.0`; each literal at :686, :895 becomes `_QUICK_RECOVERY_TIMEOUT_S`; mirror tag `# @tunable web.max_content_length = 2048` above :768; listed as a further site of that row; `_LOADED_FETCH_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.network_resilience_loaded_fetch_timeout_s = 30.0`; each literal at :860, :1041, :1076, :1086 becomes `_LOADED_FETCH_TIMEOUT_S`; `_STORM_JOIN_S = 60.0` (new, module level) tagged `# @tunable l4.network_resilience_storm_join_s = 60.0`; the literal at :873 becomes `_STORM_JOIN_S`; `_SLOWLORIS_SOCKET_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.network_resilience_slowloris_socket_timeout_s = 30.0`; the literal at :950 becomes `_SLOWLORIS_SOCKET_TIMEOUT_S`; `_TRICKLE_STEP_S = 3.0` (new, module level) tagged `# @tunable l4.network_resilience_trickle_step_s = 3.0`; the literal at :959 becomes `_TRICKLE_STEP_S`; `_BURST_JOIN_S = 40.0` (new, module level) tagged `# @tunable l4.network_resilience_burst_join_s = 40.0`; each literal at :1054, :1096 becomes `_BURST_JOIN_S`; `_SERVED_ELAPSED_MAX_S = 30.0` (new, module level) tagged `# @tunable l4.network_resilience_served_elapsed_max_s = 30.0`; the literal at :1063 becomes `_SERVED_ELAPSED_MAX_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/bench/test_bus_concurrency_under_api_load.py`, `tests_hardware/bench/test_hotspot_role_reversal.py`, `tests_hardware/bench/test_serving_heap_at_default_gc.py`, `tests_hardware/bench/test_wifi_networking.py`, `tests_hardware/bench_control.py`, `tests_hardware/conftest.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.04, A.U8C.45, A.U8C.48
- **Kind**: test

### A.U8C.51 Tag the tuned literals of `bench/test_rest_endpoints_over_sta.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench/test_rest_endpoints_over_sta.py` — `l4.rest_endpoints_over_sta_probe_timeout_s` :32, :46, :91, :95, :98, :113, :129, :137, :150, :155 (10.0); `l4.rest_endpoints_over_sta_ready_probe_timeout_s` :108, :145 (5.0); `l4.rest_endpoints_over_sta_reboot_ready_timeout_s` :109, :146 (120.0); `l4.rest_endpoints_over_sta_reboot_ready_poll_s` :110, :147 (3.0)
- **Change**: `_PROBE_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.rest_endpoints_over_sta_probe_timeout_s = 10.0`; each literal at :32, :46, :91, :95, :98, :113, :129, :137, :150, :155 becomes `_PROBE_TIMEOUT_S`; `_READY_PROBE_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l4.rest_endpoints_over_sta_ready_probe_timeout_s = 5.0`; each literal at :108, :145 becomes `_READY_PROBE_TIMEOUT_S`; `_REBOOT_READY_TIMEOUT_S = 120.0` (new, module level) tagged `# @tunable l4.rest_endpoints_over_sta_reboot_ready_timeout_s = 120.0`; each literal at :109, :146 becomes `_REBOOT_READY_TIMEOUT_S`; `_REBOOT_READY_POLL_S = 3.0` (new, module level) tagged `# @tunable l4.rest_endpoints_over_sta_reboot_ready_poll_s = 3.0`; each literal at :110, :147 becomes `_REBOOT_READY_POLL_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.52 Tag the tuned literals of `bench/test_sensor_config_push_over_real_hardware.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py` — `l4.sensor_config_push_over_real_hardware_probe_timeout_s` :38, :48, :54, :61, :78, :88, :94, :101, :120, :124, :133, :148, :155, :165, :170, :178, :185 (10.0); `l4.sensor_config_push_over_real_hardware_override_poll_s` :132 (1.0)
- **Change**: `_PROBE_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.sensor_config_push_over_real_hardware_probe_timeout_s = 10.0`; each literal at :38, :48, :54, :61, :78, :88, :94, :101, :120, :124, :133, :148, :155, :165, :170, :178, :185 becomes `_PROBE_TIMEOUT_S`; `_OVERRIDE_POLL_S = 1.0` (new, module level) tagged `# @tunable l4.sensor_config_push_over_real_hardware_override_poll_s = 1.0`; the literal at :132 becomes `_OVERRIDE_POLL_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.53 Tag the tuned literals of `bench/test_serving_heap_at_default_gc.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench/test_serving_heap_at_default_gc.py` — `l4.serving_heap_at_default_gc_rounds` :28 (12); `l4.network_resilience_slot_release_wait_s` :29 (1.0); `l4.serving_heap_at_default_gc_level_gap_s` :30 (3.0); `l4.serving_heap_at_default_gc_pre_idle_s` :31 (30.0); `l4.serving_heap_at_default_gc_max_route_need` :35 (480); `l4.serving_heap_at_default_gc_connect_timeout_s` :42 (30.0); `l4.serving_heap_at_default_gc_barrier_timeout_s` :72 (30.0); `l4.serving_heap_at_default_gc_burst_join_s` :78 (60.0); `l4.serving_heap_at_default_gc_need_script_timeout_s` :109 (300.0); `l4.serving_heap_at_default_gc_serving_script_timeout_s` :130 (900.0); `l4.serving_heap_at_default_gc_driver_join_s` :133 (90.0)
- **Change**: tag `# @tunable l4.serving_heap_at_default_gc_rounds = 12` above `_ROUNDS` (:28); tag `# @tunable l4.network_resilience_slot_release_wait_s = 1.0` above `_ROUND_SETTLE_S` (:29); tag `# @tunable l4.serving_heap_at_default_gc_level_gap_s = 3.0` above `_LEVEL_GAP_S` (:30); tag `# @tunable l4.serving_heap_at_default_gc_pre_idle_s = 30.0` above `_PRE_IDLE_S` (:31); tag `# @tunable l4.serving_heap_at_default_gc_max_route_need = 480` above `_MAX_ROUTE_NEED` (:35); `_CONNECT_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.serving_heap_at_default_gc_connect_timeout_s = 30.0`; the literal at :42 becomes `_CONNECT_TIMEOUT_S`; `_BARRIER_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.serving_heap_at_default_gc_barrier_timeout_s = 30.0`; the literal at :72 becomes `_BARRIER_TIMEOUT_S`; `_BURST_JOIN_S = 60.0` (new, module level) tagged `# @tunable l4.serving_heap_at_default_gc_burst_join_s = 60.0`; the literal at :78 becomes `_BURST_JOIN_S`; `_NEED_SCRIPT_TIMEOUT_S = 300.0` (new, module level) tagged `# @tunable l4.serving_heap_at_default_gc_need_script_timeout_s = 300.0`; the literal at :109 becomes `_NEED_SCRIPT_TIMEOUT_S`; `_SERVING_SCRIPT_TIMEOUT_S = 900.0` (new, module level) tagged `# @tunable l4.serving_heap_at_default_gc_serving_script_timeout_s = 900.0`; the literal at :130 becomes `_SERVING_SCRIPT_TIMEOUT_S`; `_DRIVER_JOIN_S = 90.0` (new, module level) tagged `# @tunable l4.serving_heap_at_default_gc_driver_join_s = 90.0`; the literal at :133 becomes `_DRIVER_JOIN_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/bench/test_network_resilience.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.50
- **Kind**: test

### A.U8C.54 Tag the tuned literals of `bench/test_uart_link_under_api_load.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench/test_uart_link_under_api_load.py` — `l4.uart_link_under_api_load_get_workers` :24 (2); `l4.uart_link_under_api_load_get_iterations` :25 (10); `l4.uart_link_under_api_load_request_budget_s` :28 (15.0); `l4.uart_link_under_api_load_request_budget_s` :35 (15.0); `l4.uart_link_under_api_load_join_timeout_s` :92, :139 (120.0); `l4.uart_link_under_api_load_probe_timeout_s` :98, :187 (10.0); `l4.uart_link_under_api_load_wait_timeout_s` :99, :147, :188 (30.0); `l4.uart_link_under_api_load_wait_poll_s` :100, :148, :189 (2.0); `l4.uart_link_under_api_load_short_join_timeout_s` :181 (60.0)
- **Change**: tag `# @tunable l4.uart_link_under_api_load_get_workers = 2` above `_GET_WORKERS` (:24); tag `# @tunable l4.uart_link_under_api_load_get_iterations = 10` above `_GET_ITERATIONS_PER_WORKER` (:25); tag `# @tunable l4.uart_link_under_api_load_request_budget_s = 15.0` above `_REQUEST_BUDGET_S` (:28); the literal at :35 becomes the existing `_REQUEST_BUDGET_S` (same value and purpose; the tag stays on the constant); `_JOIN_TIMEOUT_S = 120.0` (new, module level) tagged `# @tunable l4.uart_link_under_api_load_join_timeout_s = 120.0`; each literal at :92, :139 becomes `_JOIN_TIMEOUT_S`; `_PROBE_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.uart_link_under_api_load_probe_timeout_s = 10.0`; each literal at :98, :187 becomes `_PROBE_TIMEOUT_S`; `_WAIT_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.uart_link_under_api_load_wait_timeout_s = 30.0`; each literal at :99, :147, :188 becomes `_WAIT_TIMEOUT_S`; `_WAIT_POLL_S = 2.0` (new, module level) tagged `# @tunable l4.uart_link_under_api_load_wait_poll_s = 2.0`; each literal at :100, :148, :189 becomes `_WAIT_POLL_S`; `_SHORT_JOIN_TIMEOUT_S = 60.0` (new, module level) tagged `# @tunable l4.uart_link_under_api_load_short_join_timeout_s = 60.0`; the literal at :181 becomes `_SHORT_JOIN_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.55 Tag the tuned literals of `bench/test_wifi_networking.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench/test_wifi_networking.py` — `l4.wifi_networking_boot_tail_s` :37 (45.0); `l4.wifi_networking_sync_tail_s` :55, :68 (60.0); `l4.network_resilience_rogue_tail_s` :88 (90.0); `l4.wifi_networking_reconnect_timeout_s` :103, :107 (60.0); `l4.wifi_networking_reconnect_poll_s` :103, :107 (3.0); `l4.wifi_networking_ready_probe_timeout_s` :118 (5.0)
- **Change**: `_BOOT_TAIL_S = 45.0` (new, module level) tagged `# @tunable l4.wifi_networking_boot_tail_s = 45.0`; the literal at :37 becomes `_BOOT_TAIL_S`; `_SYNC_TAIL_S = 60.0` (new, module level) tagged `# @tunable l4.wifi_networking_sync_tail_s = 60.0`; each literal at :55, :68 becomes `_SYNC_TAIL_S`; `_ROGUE_TAIL_S = 90.0` (new, module level) tagged `# @tunable l4.network_resilience_rogue_tail_s = 90.0`; the literal at :88 becomes `_ROGUE_TAIL_S`; `_RECONNECT_TIMEOUT_S = 60.0` (new, module level) tagged `# @tunable l4.wifi_networking_reconnect_timeout_s = 60.0`; each literal at :103, :107 becomes `_RECONNECT_TIMEOUT_S`; `_RECONNECT_POLL_S = 3.0` (new, module level) tagged `# @tunable l4.wifi_networking_reconnect_poll_s = 3.0`; each literal at :103, :107 becomes `_RECONNECT_POLL_S`; `_READY_PROBE_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l4.wifi_networking_ready_probe_timeout_s = 5.0`; the literal at :118 becomes `_READY_PROBE_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/bench/test_network_resilience.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.50
- **Kind**: test

### A.U8C.56 Tag the tuned literals of `bench_control.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/bench_control.py` — `l4.bench_control_nmcli_timeout_s` :24 (30.0); `l4.bench_control_nmcli_short_timeout_s` :43, :198 (15.0); `l4.bench_control_cmd_timeout_s` :90, :249, :255, :271 (10.0); `l4.bench_control_udp_capture_timeout_s` :138 (55.0); `l4.bench_control_join_hotspot_timeout_s` :201 (30.0); deferred U26: `:277` (10.0)
- **Change**: `_NMCLI_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.bench_control_nmcli_timeout_s = 30.0`; the literal at :24 becomes `_NMCLI_TIMEOUT_S`; `_NMCLI_SHORT_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l4.bench_control_nmcli_short_timeout_s = 15.0`; each literal at :43, :198 becomes `_NMCLI_SHORT_TIMEOUT_S`; `_CMD_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.bench_control_cmd_timeout_s = 10.0`; each literal at :90, :249, :255, :271 becomes `_CMD_TIMEOUT_S`; `_UDP_CAPTURE_TIMEOUT_S = 55.0` (new, module level) tagged `# @tunable l4.bench_control_udp_capture_timeout_s = 55.0`; the literal at :138 becomes `_UDP_CAPTURE_TIMEOUT_S`; `_JOIN_HOTSPOT_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.bench_control_join_hotspot_timeout_s = 30.0`; the literal at :201 becomes `_JOIN_HOTSPOT_TIMEOUT_S`; deferred sleeps (:277): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/bench/test_network_resilience.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.50, U26
- **Kind**: test

### A.U8C.57 Tag the tuned literals of `conftest.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/conftest.py` — `l4.conftest_hotspot_scan_timeout_s` :183 (30.0); `l4.conftest_hotspot_scan_poll_s` :184 (2.0); `l4.conftest_join_hotspot_timeout_s` :187 (45.0); `l4.conftest_provision_put_timeout_s` :192 (10.0); `l4.conftest_dut_ip_exec_timeout_s` :218 (15.0); `l4.conftest_http_ready_probe_timeout_s` :230 (5.0); `l4.conftest_http_ready_timeout_s` :248 (30.0); `l4.conftest_http_ready_poll_s` :249 (2.0)
- **Change**: `_HOTSPOT_SCAN_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.conftest_hotspot_scan_timeout_s = 30.0`; the literal at :183 becomes `_HOTSPOT_SCAN_TIMEOUT_S`; `_HOTSPOT_SCAN_POLL_S = 2.0` (new, module level) tagged `# @tunable l4.conftest_hotspot_scan_poll_s = 2.0`; the literal at :184 becomes `_HOTSPOT_SCAN_POLL_S`; `_JOIN_HOTSPOT_TIMEOUT_S = 45.0` (new, module level) tagged `# @tunable l4.conftest_join_hotspot_timeout_s = 45.0`; the literal at :187 becomes `_JOIN_HOTSPOT_TIMEOUT_S`; `_PROVISION_PUT_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.conftest_provision_put_timeout_s = 10.0`; the literal at :192 becomes `_PROVISION_PUT_TIMEOUT_S`; `_DUT_IP_EXEC_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l4.conftest_dut_ip_exec_timeout_s = 15.0`; the literal at :218 becomes `_DUT_IP_EXEC_TIMEOUT_S`; `_HTTP_READY_PROBE_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l4.conftest_http_ready_probe_timeout_s = 5.0`; the literal at :230 becomes `_HTTP_READY_PROBE_TIMEOUT_S`; `_HTTP_READY_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l4.conftest_http_ready_timeout_s = 30.0`; the literal at :248 becomes `_HTTP_READY_TIMEOUT_S`; `_HTTP_READY_POLL_S = 2.0` (new, module level) tagged `# @tunable l4.conftest_http_ready_poll_s = 2.0`; the literal at :249 becomes `_HTTP_READY_POLL_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/bench/test_hotspot_role_reversal.py`, `tests_hardware/bench/test_network_resilience.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.48
- **Kind**: test

### A.U8C.58 Tag the tuned literals of `device_scripts/bmp3xx_plausibility_read.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/bmp3xx_plausibility_read.py` — `wdt.timeout_ms` :17 (8000); `l3.bmp3xx_plausibility_read_poll_s` :36 (0.5)
- **Change**: mirror `wdt.timeout_ms` at :17: already named by A.U8.08; it gets the tag there; `_POLL_S = 0.5` (new, module level) tagged `# @tunable l3.bmp3xx_plausibility_read_poll_s = 0.5`; the literal at :36 becomes `_POLL_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_sensor_accuracy.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.59 Tag the tuned literals of `device_scripts/bmp3xx_same_device_rw_concurrency.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py` — `l3.bmp3xx_same_device_rw_concurrency_read_iterations` :16 (20); `l3.bmp3xx_same_device_rw_concurrency_write_iterations` :17 (6); `wdt.timeout_ms` :21 (8000); `l3.bmp3xx_same_device_rw_concurrency_write_spread_s` :49 (0.05); `l3.bmp3xx_same_device_rw_concurrency_run_bound_s` :60 (60.0)
- **Change**: tag `# @tunable l3.bmp3xx_same_device_rw_concurrency_read_iterations = 20` above `READ_ITERATIONS` (:16); tag `# @tunable l3.bmp3xx_same_device_rw_concurrency_write_iterations = 6` above `WRITE_ITERATIONS` (:17); mirror `wdt.timeout_ms` at :21: already named by A.U8.08; it gets the tag there; `_WRITE_SPREAD_S = 0.05` (new, module level) tagged `# @tunable l3.bmp3xx_same_device_rw_concurrency_write_spread_s = 0.05`; the literal at :49 becomes `_WRITE_SPREAD_S`; `_RUN_BOUND_S = 60.0` (new, module level) tagged `# @tunable l3.bmp3xx_same_device_rw_concurrency_run_bound_s = 60.0`; the literal at :60 becomes `_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.60 Tag the tuned literals of `device_scripts/bus_concurrency_cross_device_scd30_sgp40.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py` — `l3.bus_concurrency_cross_device_scd30_sgp40_sgp40_cycles` :14 (6); `wdt.timeout_ms` :18 (8000); `l3.bus_concurrency_cross_device_scd30_sgp40_run_bound_s` :59 (60.0)
- **Change**: tag `# @tunable l3.bus_concurrency_cross_device_scd30_sgp40_sgp40_cycles = 6` above `SGP40_CYCLES` (:14); mirror `wdt.timeout_ms` at :18: already named by A.U8.08; it gets the tag there; `_RUN_BOUND_S = 60.0` (new, module level) tagged `# @tunable l3.bus_concurrency_cross_device_scd30_sgp40_run_bound_s = 60.0`; the literal at :59 becomes `_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.61 Tag the tuned literals of `device_scripts/bus_concurrency_isl29125_write_vs_siblings.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py` — `l3.bus_concurrency_isl29125_write_vs_siblings_write_delays_ms` :18 (120/15/40/5/80); `wdt.timeout_ms` :24 (8000); `l3.bus_concurrency_isl29125_write_vs_siblings_sibling_step_ms` :54, :70 (15); `l3.bus_concurrency_isl29125_write_vs_siblings_run_bound_s` :86 (60.0)
- **Change**: tag `# @tunable l3.bus_concurrency_isl29125_write_vs_siblings_write_delays_ms = 5` above `_WRITE_DELAYS_MS` (:18); mirror `wdt.timeout_ms` at :24: already named by A.U8.08; it gets the tag there; `_SIBLING_STEP_MS = 15` (new, module level) tagged `# @tunable l3.bus_concurrency_isl29125_write_vs_siblings_sibling_step_ms = 15`; each literal at :54, :70 becomes `_SIBLING_STEP_MS`; `_RUN_BOUND_S = 60.0` (new, module level) tagged `# @tunable l3.bus_concurrency_isl29125_write_vs_siblings_run_bound_s = 60.0`; the literal at :86 becomes `_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py`, `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.62 Tag the tuned literals of `device_scripts/bus_concurrency_same_device_scd30.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py` — `l3.bus_concurrency_same_device_scd30_reader_iterations` :16 (120); `l3.bus_concurrency_same_device_scd30_snapshotter_iterations` :17 (40); `l3.bus_concurrency_same_device_scd30_settle_s` :21 (12.0); `wdt.timeout_ms` :25 (8000); `l3.bus_concurrency_same_device_scd30_settle_step_s` :39 (0.5); `l3.bus_concurrency_same_device_scd30_run_bound_s` :81 (90.0)
- **Change**: tag `# @tunable l3.bus_concurrency_same_device_scd30_reader_iterations = 120` above `READER_ITERATIONS` (:16); tag `# @tunable l3.bus_concurrency_same_device_scd30_snapshotter_iterations = 40` above `SNAPSHOTTER_ITERATIONS` (:17); tag `# @tunable l3.bus_concurrency_same_device_scd30_settle_s = 12.0` above `_SETTLE_S` (:21); mirror `wdt.timeout_ms` at :25: already named by A.U8.08; it gets the tag there; `_SETTLE_STEP_S = 0.5` (new, module level) tagged `# @tunable l3.bus_concurrency_same_device_scd30_settle_step_s = 0.5`; the literal at :39 becomes `_SETTLE_STEP_S`; `_RUN_BOUND_S = 90.0` (new, module level) tagged `# @tunable l3.bus_concurrency_same_device_scd30_run_bound_s = 90.0`; the literal at :81 becomes `_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.63 Tag the tuned literals of `device_scripts/bus_concurrency_scd30_write_vs_siblings.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py` — `wdt.timeout_ms` :19 (8000); `l3.bus_concurrency_scd30_write_vs_siblings_sibling_step_ms` :52, :66 (15); `l3.bus_concurrency_scd30_write_vs_siblings_after_write_s` :80 (1.0); `l3.bus_concurrency_scd30_write_vs_siblings_run_bound_s` :83 (60.0); deferred U26: `:70` (0.3)
- **Change**: mirror `wdt.timeout_ms` at :19: already named by A.U8.08; it gets the tag there; `_SIBLING_STEP_MS = 15` (new, module level) tagged `# @tunable l3.bus_concurrency_scd30_write_vs_siblings_sibling_step_ms = 15`; each literal at :52, :66 becomes `_SIBLING_STEP_MS`; `_AFTER_WRITE_S = 1.0` (new, module level) tagged `# @tunable l3.bus_concurrency_scd30_write_vs_siblings_after_write_s = 1.0`; the literal at :80 becomes `_AFTER_WRITE_S`; `_RUN_BOUND_S = 60.0` (new, module level) tagged `# @tunable l3.bus_concurrency_scd30_write_vs_siblings_run_bound_s = 60.0`; the literal at :83 becomes `_RUN_BOUND_S`; deferred sleeps (:70): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08, U26
- **Kind**: test

### A.U8C.64 Tag the tuned literals of `device_scripts/bus_topology_autodetect_and_hazard_sweep.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py` — `l3.bus_topology_autodetect_and_hazard_sweep_broadcast_step_s` :137 (0.2); `l3.bus_topology_autodetect_and_hazard_sweep_run_bound_s` :139 (30.0); `wdt.timeout_ms` :144 (8000)
- **Change**: `_BROADCAST_STEP_S = 0.2` (new, module level) tagged `# @tunable l3.bus_topology_autodetect_and_hazard_sweep_broadcast_step_s = 0.2`; the literal at :137 becomes `_BROADCAST_STEP_S`; `_RUN_BOUND_S = 30.0` (new, module level) tagged `# @tunable l3.bus_topology_autodetect_and_hazard_sweep_run_bound_s = 30.0`; the literal at :139 becomes `_RUN_BOUND_S`; mirror `wdt.timeout_ms` at :144: already named by A.U8.08; it gets the tag there. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.65 Tag the tuned literals of `device_scripts/fram_cs_hijack_fault_injection_and_recovery.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py` — `wdt.timeout_ms` :85 (8000); `l3.fram_cs_hijack_fault_injection_and_recovery_victim_bound_s` :116, :156 (30.0)
- **Change**: mirror `wdt.timeout_ms` at :85: already named by A.U8.08; it gets the tag there; `_VICTIM_BOUND_S = 30.0` (new, module level) tagged `# @tunable l3.fram_cs_hijack_fault_injection_and_recovery_victim_bound_s = 30.0`; each literal at :116, :156 becomes `_VICTIM_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests/test_digital_twin_bus_hazard_concurrency.py`, `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.66 Tag the mirrored product values in `device_scripts/fram_error_log_reset_race_seed_and_race.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py` — `wdt.timeout_ms` :17 (8000)
- **Change**: mirror `wdt.timeout_ms` at :17: already named by A.U8.08; it gets the tag there. Rows: no new row; each mirror is a further site in its product row.
- **Blast**: callers run on the board by `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py`, `tests_hardware/flash/test_fram_storage.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.67 Tag the tuned literals of `device_scripts/fram_pause_unpause_and_gating.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py` — `l3.fram_pause_unpause_and_gating_pause_s` :18 (2); `l3.fram_pause_unpause_and_gating_rearm_s` :19 (6); `wdt.timeout_ms` :20 (8000)
- **Change**: tag `# @tunable l3.fram_pause_unpause_and_gating_pause_s = 2` above `PAUSE_SEC` (:18); tag `# @tunable l3.fram_pause_unpause_and_gating_rearm_s = 6` above `REARM_SEC` (:19); mirror `wdt.timeout_ms` at :20: already named by A.U8.08; it gets the tag there. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_fram_storage.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.68 Tag the tuned literals of `device_scripts/fram_reset_race_during_write_seed_and_race.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py` — `wdt.timeout_ms` :26 (8000); `l3.fram_reset_race_during_write_seed_and_race_victim_bound_s` :68 (30.0)
- **Change**: mirror `wdt.timeout_ms` at :26: already named by A.U8.08; it gets the tag there; `_VICTIM_BOUND_S = 30.0` (new, module level) tagged `# @tunable l3.fram_reset_race_during_write_seed_and_race_victim_bound_s = 30.0`; the literal at :68 becomes `_VICTIM_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py`, `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.69 Tag the mirrored product values in `device_scripts/fram_reset_race_during_write_verify_recovery.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/fram_reset_race_during_write_verify_recovery.py` — `wdt.timeout_ms` :25 (8000)
- **Change**: mirror `wdt.timeout_ms` at :25: already named by A.U8.08; it gets the tag there. Rows: no new row; each mirror is a further site in its product row.
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.70 Tag the tuned literals of `device_scripts/fram_same_device_rw_concurrency.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py` — `l3.fram_same_device_rw_concurrency_read_iterations` :18 (30); `wdt.timeout_ms` :22 (8000); `l3.fram_same_device_rw_concurrency_run_bound_s` :61 (60.0)
- **Change**: tag `# @tunable l3.fram_same_device_rw_concurrency_read_iterations = 30` above `READ_ITERATIONS` (:18); mirror `wdt.timeout_ms` at :22: already named by A.U8.08; it gets the tag there; `_RUN_BOUND_S = 60.0` (new, module level) tagged `# @tunable l3.fram_same_device_rw_concurrency_run_bound_s = 60.0`; the literal at :61 becomes `_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.71 Tag the tuned literals of `device_scripts/heap_headroom_after_full_system_build.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py` — `l3.heap_headroom_after_full_system_build_probe_min` :18 (64); `l3.heap_headroom_after_full_system_build_probe_max_kib` :19 (192); `l3.heap_headroom_after_full_system_build_probe_retries` :22 (3); `l3.heap_headroom_after_full_system_build_max_used` :39 (100000)
- **Change**: tag `# @tunable l3.heap_headroom_after_full_system_build_probe_min = 64` above `_PROBE_MIN` (:18); tag `# @tunable l3.heap_headroom_after_full_system_build_probe_max_kib = 192` above `_PROBE_MAX` (:19); tag `# @tunable l3.heap_headroom_after_full_system_build_probe_retries = 3` above `_PROBE_RETRIES` (:22); tag `# @tunable l3.heap_headroom_after_full_system_build_max_used = 100000` above `_MAX_USED` (:39). Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py`, `tests_hardware/flash/test_memory_stress.py`, `tests_scripts/test_device_script_gc_threshold.py`, `tests_scripts/test_heap_map_parser.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.72 Tag the tuned literals of `device_scripts/heap_layout_after_full_boot_sequence.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py` — `l3.heap_headroom_after_full_system_build_probe_min` :19 (64); `l3.heap_headroom_after_full_system_build_probe_max_kib` :20 (192); `l3.heap_headroom_after_full_system_build_probe_retries` :23 (3); `l3.heap_layout_after_full_boot_sequence_starter_settle_ms` :28 (4000); `l3.heap_layout_after_full_boot_sequence_starter_loop_timeout_ms` :32 (20000); `l3.heap_layout_after_full_boot_sequence_starter_loop_grace_ms` :35 (250); `l3.heap_layout_after_full_boot_sequence_timers_timeout_s` :38 (15); `l3.heap_layout_after_full_boot_sequence_starter_poll_ms` :190 (20)
- **Change**: tag `# @tunable l3.heap_headroom_after_full_system_build_probe_min = 64` above `_PROBE_MIN` (:19); tag `# @tunable l3.heap_headroom_after_full_system_build_probe_max_kib = 192` above `_PROBE_MAX` (:20); tag `# @tunable l3.heap_headroom_after_full_system_build_probe_retries = 3` above `_PROBE_RETRIES` (:23); tag `# @tunable l3.heap_layout_after_full_boot_sequence_starter_settle_ms = 4000` above `_STARTER_SETTLE_MS` (:28); tag `# @tunable l3.heap_layout_after_full_boot_sequence_starter_loop_timeout_ms = 20000` above `_STARTER_LOOP_TIMEOUT_MS` (:32); tag `# @tunable l3.heap_layout_after_full_boot_sequence_starter_loop_grace_ms = 250` above `_STARTER_LOOP_GRACE_MS` (:35); tag `# @tunable l3.heap_layout_after_full_boot_sequence_timers_timeout_s = 15` above `_TIMERS_TIMEOUT_S` (:38); `_STARTER_POLL_MS = 20` (new, module level) tagged `# @tunable l3.heap_layout_after_full_boot_sequence_starter_poll_ms = 20`; the literal at :190 becomes `_STARTER_POLL_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests/_boot_contiguity_probe.py`, `tests_scripts/test_device_script_gc_threshold.py`, `tests_scripts/test_digital_twin_boot_contiguity.py`, `tests_scripts/test_heap_map_parser.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests/_boot_contiguity_probe.py`, `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.01, A.U8C.71
- **Kind**: test

### A.U8C.73 Tag the tuned literals of `device_scripts/heap_under_connection_ceiling.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/heap_under_connection_ceiling.py` — `l3.heap_under_connection_ceiling_sample_interval_ms` :16 (1000); `l3.heap_under_connection_ceiling_window_s` :18 (90); `l3.heap_under_connection_ceiling_boot_wait_s` :44 (20)
- **Change**: tag `# @tunable l3.heap_under_connection_ceiling_sample_interval_ms = 1000` above `_SAMPLE_INTERVAL_MS` (:16); tag `# @tunable l3.heap_under_connection_ceiling_window_s = 90` above `_WINDOW_S` (:18); `_BOOT_WAIT_S = 20` (new, module level) tagged `# @tunable l3.heap_under_connection_ceiling_boot_wait_s = 20`; the literal at :44 becomes `_BOOT_WAIT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_scripts/test_bench_restores_serving.py`, `tests_scripts/test_device_script_gc_threshold.py`, `tests_scripts/test_heap_map_parser.py`, `tests_scripts/test_request_timeout_ceiling.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/device_scripts/serving_at_default_gc.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.74 Tag the tuned literals of `device_scripts/isl29125_cross_device_concurrency.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py` — `l3.isl29125_cross_device_concurrency_sgp40_cycles` :15 (6); `wdt.timeout_ms` :43 (8000); `l3.isl29125_cross_device_concurrency_sibling_step_ms` :75, :89 (20); `l3.isl29125_cross_device_concurrency_run_bound_s` :103 (60.0)
- **Change**: tag `# @tunable l3.isl29125_cross_device_concurrency_sgp40_cycles = 6` above `SGP40_CYCLES` (:15); mirror `wdt.timeout_ms` at :43: already named by A.U8.08; it gets the tag there; `_SIBLING_STEP_MS = 20` (new, module level) tagged `# @tunable l3.isl29125_cross_device_concurrency_sibling_step_ms = 20`; each literal at :75, :89 becomes `_SIBLING_STEP_MS`; `_RUN_BOUND_S = 60.0` (new, module level) tagged `# @tunable l3.isl29125_cross_device_concurrency_run_bound_s = 60.0`; the literal at :103 becomes `_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.75 Tag the tuned literals of `device_scripts/isl29125_lighting_scenarios.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/isl29125_lighting_scenarios.py` — `l3.isl29125_lighting_scenarios_switch_hold_s` :32 (8.0); `l3.isl29125_lighting_scenarios_step_ms` :33 (100); `l3.isl29125_lighting_scenarios_sample_ms` :34 (300); `l3.isl29125_lighting_scenarios_settle_s` :35 (4.0); `l3.isl29125_lighting_scenarios_max_sample_gap_s` :36 (8.0); `l3.isl29125_lighting_scenarios_baseline_tol` :38 (0.35); `l3.isl29125_lighting_scenarios_park_stable_samples` :39 (3); `l3.isl29125_lighting_scenarios_park_timeout_s` :40 (20.0); `wdt.timeout_ms` :306 (8000); deferred U26: `:323` (500)
- **Change**: tag `# @tunable l3.isl29125_lighting_scenarios_switch_hold_s = 8.0` above `_SWITCH_HOLD_S` (:32); tag `# @tunable l3.isl29125_lighting_scenarios_step_ms = 100` above `_STEP_MS` (:33); tag `# @tunable l3.isl29125_lighting_scenarios_sample_ms = 300` above `_SAMPLE_MS` (:34); tag `# @tunable l3.isl29125_lighting_scenarios_settle_s = 4.0` above `_SETTLE_S` (:35); tag `# @tunable l3.isl29125_lighting_scenarios_max_sample_gap_s = 8.0` above `_MAX_SAMPLE_GAP_S` (:36); tag `# @tunable l3.isl29125_lighting_scenarios_baseline_tol = 0.35` above `_BASELINE_TOL` (:38); tag `# @tunable l3.isl29125_lighting_scenarios_park_stable_samples = 3` above `_PARK_STABLE_SAMPLES` (:39); tag `# @tunable l3.isl29125_lighting_scenarios_park_timeout_s = 20.0` above `_PARK_TIMEOUT_S` (:40); mirror `wdt.timeout_ms` at :306: already named by A.U8.08; it gets the tag there; deferred sleeps (:323): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_sensor_accuracy.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08, U26
- **Kind**: test

### A.U8C.76 Tag the tuned literals of `device_scripts/isl29125_mechanism_envelope.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/isl29125_mechanism_envelope.py` — `l3.isl29125_mechanism_envelope_settle_s` :24 (4.5); `l3.isl29125_mechanism_envelope_max_wait_s` :25 (12.0); `l3.isl29125_mechanism_envelope_max_switches` :26 (4); `l3.isl29125_mechanism_envelope_max_range_step` :31 (0.25); `l3.isl29125_mechanism_envelope_poll_ms` :52, :82 (200); `wdt.timeout_ms` :200 (8000); deferred U26: `:209` (500); deferred U26: `:237` (200)
- **Change**: tag `# @tunable l3.isl29125_mechanism_envelope_settle_s = 4.5` above `SETTLE_S` (:24); tag `# @tunable l3.isl29125_mechanism_envelope_max_wait_s = 12.0` above `MAX_WAIT_S` (:25); tag `# @tunable l3.isl29125_mechanism_envelope_max_switches = 4` above `MAX_SWITCHES` (:26); tag `# @tunable l3.isl29125_mechanism_envelope_max_range_step = 0.25` above `MAX_RANGE_STEP` (:31); `_POLL_MS = 200` (new, module level) tagged `# @tunable l3.isl29125_mechanism_envelope_poll_ms = 200`; each literal at :52, :82 becomes `_POLL_MS`; mirror `wdt.timeout_ms` at :200: already named by A.U8.08; it gets the tag there; deferred sleeps (:209, :237): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_sensor_accuracy.py`, `tests_scripts/test_device_script_config_flush.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08, U26
- **Kind**: test

### A.U8C.77 Tag the mirrored product values in `device_scripts/isl29125_mock_conformance_probe.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py` — `wdt.timeout_ms` :12 (8000)
- **Change**: mirror `wdt.timeout_ms` at :12: already named by A.U8.08; it gets the tag there. Rows: no new row; each mirror is a further site in its product row.
- **Blast**: callers run on the board by `tests_hardware/flash/test_sensor_accuracy.py`, `tests_hardware/isl29125_conformance.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.78 Tag the tuned literals of `device_scripts/isl29125_plausibility_read.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/isl29125_plausibility_read.py` — `l3.isl29125_plausibility_read_room_light_min_lux` :17 (5.0); `wdt.timeout_ms` :22 (8000); `l3.isl29125_plausibility_read_poll_s` :50 (0.5); deferred U26: `:29` (300)
- **Change**: tag `# @tunable l3.isl29125_plausibility_read_room_light_min_lux = 5.0` above `ROOM_LIGHT_MIN_LUX` (:17); mirror `wdt.timeout_ms` at :22: already named by A.U8.08; it gets the tag there; `_POLL_S = 0.5` (new, module level) tagged `# @tunable l3.isl29125_plausibility_read_poll_s = 0.5`; the literal at :50 becomes `_POLL_S`; deferred sleeps (:29): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_sensor_accuracy.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08, U26
- **Kind**: test

### A.U8C.79 Tag the tuned literals of `device_scripts/isl29125_real_irq_edge.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/isl29125_real_irq_edge.py` — `l3.isl29125_real_irq_edge_fast_path_deadline_s` :18 (6.0); `l3.isl29125_real_irq_edge_int_poll_ms` :58 (50); `wdt.timeout_ms` :69 (8000); `l3.isl29125_real_irq_edge_fast_path_poll_ms` :108 (100); deferred U26: `:76` (300)
- **Change**: tag `# @tunable l3.isl29125_real_irq_edge_fast_path_deadline_s = 6.0` above `FAST_PATH_DEADLINE_S` (:18); `_INT_POLL_MS = 50` (new, module level) tagged `# @tunable l3.isl29125_real_irq_edge_int_poll_ms = 50`; the literal at :58 becomes `_INT_POLL_MS`; mirror `wdt.timeout_ms` at :69: already named by A.U8.08; it gets the tag there; `_FAST_PATH_POLL_MS = 100` (new, module level) tagged `# @tunable l3.isl29125_real_irq_edge_fast_path_poll_ms = 100`; the literal at :108 becomes `_FAST_PATH_POLL_MS`; deferred sleeps (:76): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08, U26
- **Kind**: test

### A.U8C.80 Tag the tuned literals of `device_scripts/isl29125_same_device_rw_concurrency.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py` — `l3.isl29125_same_device_rw_concurrency_read_iterations` :12 (20); `l3.isl29125_same_device_rw_concurrency_write_iterations` :13 (6); `wdt.timeout_ms` :19 (8000); `l3.isl29125_same_device_rw_concurrency_read_step_ms` :49 (50); `l3.isl29125_same_device_rw_concurrency_write_step_ms` :69 (90); deferred U26: `:53` (120)
- **Change**: tag `# @tunable l3.isl29125_same_device_rw_concurrency_read_iterations = 20` above `READ_ITERATIONS` (:12); tag `# @tunable l3.isl29125_same_device_rw_concurrency_write_iterations = 6` above `WRITE_ITERATIONS` (:13); mirror `wdt.timeout_ms` at :19: already named by A.U8.08; it gets the tag there; `_READ_STEP_MS = 50` (new, module level) tagged `# @tunable l3.isl29125_same_device_rw_concurrency_read_step_ms = 50`; the literal at :49 becomes `_READ_STEP_MS`; `_WRITE_STEP_MS = 90` (new, module level) tagged `# @tunable l3.isl29125_same_device_rw_concurrency_write_step_ms = 90`; the literal at :69 becomes `_WRITE_STEP_MS`; deferred sleeps (:53): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08, U26
- **Kind**: test

### A.U8C.81 Tag the tuned literals of `device_scripts/reboot_fallback_starves_the_watchdog.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py` — `l3.starvation_wdt_ms` :12 (1500); `l3.reboot_fallback_starves_the_watchdog_feed_attempt_ms` :49 (250)
- **Change**: l3.starvation_wdt_ms at :12: already created and tagged by A.U8.08; nothing further here; `_FEED_ATTEMPT_MS = 250` (new, module level) tagged `# @tunable l3.reboot_fallback_starves_the_watchdog_feed_attempt_ms = 250`; the literal at :49 becomes `_FEED_ATTEMPT_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_watchdog_starvation.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/device_scripts/watchdog_starvation_reset.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.82 Tag the tuned literals of `device_scripts/scd30_plausibility_read.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/scd30_plausibility_read.py` — `l3.scd30_plausibility_read_settle_s` :15 (45.0); `wdt.timeout_ms` :19 (8000); `l3.scd30_plausibility_read_step_s` :30, :41 (0.5)
- **Change**: tag `# @tunable l3.scd30_plausibility_read_settle_s = 45.0` above `_SETTLE_S` (:15); mirror `wdt.timeout_ms` at :19: already named by A.U8.08; it gets the tag there; `_STEP_S = 0.5` (new, module level) tagged `# @tunable l3.scd30_plausibility_read_step_s = 0.5`; each literal at :30, :41 becomes `_STEP_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_sensor_accuracy.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.83 Tag the tuned literals of `device_scripts/scd30_real_irq_edge.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/scd30_real_irq_edge.py` — `l3.scd30_real_irq_edge_fast_path_deadline_s` :11 (5.0); `l3.scd30_real_irq_edge_poll_ms` :31 (100)
- **Change**: tag `# @tunable l3.scd30_real_irq_edge_fast_path_deadline_s = 5.0` above `FAST_PATH_DEADLINE_S` (:11); `_POLL_MS = 100` (new, module level) tagged `# @tunable l3.scd30_real_irq_edge_poll_ms = 100`; the literal at :31 becomes `_POLL_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_electrical_timing.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.84 Tag the tuned literals of `device_scripts/scd30_same_device_rw_concurrency.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py` — `l3.scd30_same_device_rw_concurrency_read_iterations` :16 (40); `l3.bus_concurrency_same_device_scd30_settle_s` :20 (12.0); `wdt.timeout_ms` :24 (8000); `l3.bus_concurrency_same_device_scd30_settle_step_s` :35 (0.5); `l3.scd30_same_device_rw_concurrency_run_bound_s` :72 (60.0); deferred U26: `:64` (0.2)
- **Change**: tag `# @tunable l3.scd30_same_device_rw_concurrency_read_iterations = 40` above `READ_ITERATIONS` (:16); tag `# @tunable l3.bus_concurrency_same_device_scd30_settle_s = 12.0` above `_SETTLE_S` (:20); mirror `wdt.timeout_ms` at :24: already named by A.U8.08; it gets the tag there; `_SETTLE_STEP_S = 0.5` (new, module level) tagged `# @tunable l3.bus_concurrency_same_device_scd30_settle_step_s = 0.5`; the literal at :35 becomes `_SETTLE_STEP_S`; `_RUN_BOUND_S = 60.0` (new, module level) tagged `# @tunable l3.scd30_same_device_rw_concurrency_run_bound_s = 60.0`; the literal at :72 becomes `_RUN_BOUND_S`; deferred sleeps (:64): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py`, `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py`, `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py`, `tests_hardware/flash/conftest.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08, A.U8C.62, U26
- **Kind**: test

### A.U8C.85 Tag the tuned literals of `device_scripts/scheduler_saturation_drop.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/scheduler_saturation_drop.py` — `l3.scheduler_saturation_drop_timer_period_ms` :18 (2); `l3.scheduler_saturation_drop_busy_wait_ms` :19 (100); `l3.scheduler_saturation_drop_heal_window_ms` :20 (500)
- **Change**: tag `# @tunable l3.scheduler_saturation_drop_timer_period_ms = 2` above `TIMER_PERIOD_MS` (:18); tag `# @tunable l3.scheduler_saturation_drop_busy_wait_ms = 100` above `BUSY_WAIT_MS` (:19); tag `# @tunable l3.scheduler_saturation_drop_heal_window_ms = 500` above `HEAL_WINDOW_MS` (:20). Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_electrical_timing.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.86 Tag the tuned literals of `device_scripts/serving_at_default_gc.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/serving_at_default_gc.py` — `l3.heap_under_connection_ceiling_boot_wait_s` :27 (20); `l3.serving_at_default_gc_poll_ms` :28 (1000); `l3.serving_at_default_gc_dump_every` :29 (5); `l3.serving_at_default_gc_busy_to_enter` :30 (2); `l3.serving_at_default_gc_quiet_to_leave` :31 (10); `l3.serving_at_default_gc_post_dumps` :32 (3); `l3.serving_at_default_gc_window_s` :33 (600)
- **Change**: tag `# @tunable l3.heap_under_connection_ceiling_boot_wait_s = 20` above `_BOOT_S` (:27); tag `# @tunable l3.serving_at_default_gc_poll_ms = 1000` above `_POLL_MS` (:28); tag `# @tunable l3.serving_at_default_gc_dump_every = 5` above `_DUMP_EVERY` (:29); tag `# @tunable l3.serving_at_default_gc_busy_to_enter = 2` above `_BUSY_TO_ENTER` (:30); tag `# @tunable l3.serving_at_default_gc_quiet_to_leave = 10` above `_QUIET_TO_LEAVE` (:31); tag `# @tunable l3.serving_at_default_gc_post_dumps = 3` above `_POST_DUMPS` (:32); tag `# @tunable l3.serving_at_default_gc_window_s = 600` above `_WINDOW_S` (:33). Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/bench/test_serving_heap_at_default_gc.py`, `tests_scripts/test_device_script_gc_threshold.py`, `tests_scripts/test_heap_map_parser.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/device_scripts/heap_under_connection_ceiling.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.73
- **Kind**: test

### A.U8C.87 Tag the tuned literals of `device_scripts/sgp40_fram_backup_restore.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/sgp40_fram_backup_restore.py` — `l3.sgp40_fram_backup_restore_backup_wait_s` :15 (75.0); `l3.sgp40_fram_backup_restore_restore_wait_s` :16 (10.0); `l3.sgp40_fram_backup_restore_wdt_feed_interval_s` :17 (2.0); `wdt.timeout_ms` :53 (8000)
- **Change**: tag `# @tunable l3.sgp40_fram_backup_restore_backup_wait_s = 75.0` above `BACKUP_WAIT_S` (:15); tag `# @tunable l3.sgp40_fram_backup_restore_restore_wait_s = 10.0` above `RESTORE_WAIT_S` (:16); tag `# @tunable l3.sgp40_fram_backup_restore_wdt_feed_interval_s = 2.0` above `_WDT_FEED_INTERVAL_S` (:17); mirror `wdt.timeout_ms` at :53: already named by A.U8.08; it gets the tag there. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_fram_storage.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.88 Tag the tuned literals of `device_scripts/sgp40_general_call_reset_hazard.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py` — `l3.sgp40_general_call_reset_hazard_reset_cycles` :18 (8); `wdt.timeout_ms` :43 (8000); `l3.sgp40_general_call_reset_hazard_sibling_step_ms` :101 (15); `l3.sgp40_general_call_reset_hazard_run_bound_s` :117 (90.0)
- **Change**: tag `# @tunable l3.sgp40_general_call_reset_hazard_reset_cycles = 8` above `SGP40_RESET_CYCLES` (:18); mirror `wdt.timeout_ms` at :43: already named by A.U8.08; it gets the tag there; `_SIBLING_STEP_MS = 15` (new, module level) tagged `# @tunable l3.sgp40_general_call_reset_hazard_sibling_step_ms = 15`; the literal at :101 becomes `_SIBLING_STEP_MS`; `_RUN_BOUND_S = 90.0` (new, module level) tagged `# @tunable l3.sgp40_general_call_reset_hazard_run_bound_s = 90.0`; the literal at :117 becomes `_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_bus_concurrency.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.89 Tag the tuned literals of `device_scripts/sgp40_voc_algorithm_quality.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py` — `l3.sgp40_voc_algorithm_quality_blackout_wait_s` :15 (60.0); `l3.sgp40_voc_algorithm_quality_sample_interval_s` :17 (2.0); `l3.sgp40_voc_algorithm_quality_max_single_step_jump` :18 (300); `l3.sgp40_fram_backup_restore_wdt_feed_interval_s` :19 (2.0); `wdt.timeout_ms` :45 (8000)
- **Change**: tag `# @tunable l3.sgp40_voc_algorithm_quality_blackout_wait_s = 60.0` above `BLACKOUT_WAIT_S` (:15); tag `# @tunable l3.sgp40_voc_algorithm_quality_sample_interval_s = 2.0` above `SAMPLE_INTERVAL_S` (:17); tag `# @tunable l3.sgp40_voc_algorithm_quality_max_single_step_jump = 300` above `MAX_SINGLE_STEP_JUMP` (:18); tag `# @tunable l3.sgp40_fram_backup_restore_wdt_feed_interval_s = 2.0` above `_WDT_FEED_INTERVAL_S` (:19); mirror `wdt.timeout_ms` at :45: already named by A.U8.08; it gets the tag there. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/bench/test_bus_concurrency_under_api_load.py`, `tests_hardware/flash/test_sensor_accuracy.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/device_scripts/sgp40_fram_backup_restore.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08, A.U8C.87
- **Kind**: test

### A.U8C.90 Tag the tuned literals of `device_scripts/system_service_restarts_a_real_dead_task.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py` — `wdt.timeout_ms` :11 (8000); `l3.system_service_restarts_a_real_dead_task_watch_step_s` :38 (0.9)
- **Change**: mirror `wdt.timeout_ms` at :11: already named by A.U8.08; it gets the tag there; `_WATCH_STEP_S = 0.9` (new, module level) tagged `# @tunable l3.system_service_restarts_a_real_dead_task_watch_step_s = 0.9`; the literal at :38 becomes `_WATCH_STEP_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_task_supervisor.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.91 Tag the tuned literals of `device_scripts/uart_crossover_exchange.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/uart_crossover_exchange.py` — `dev.uart_poll_wait_ms` :29 (2); `dev.uart_poll_idle_ms` :32 (50); `dev.uart_rxbuf` :33 (512); `l3.uart_crossover_exchange_join_step_ms` :37 (100); `l3.uart_crossover_exchange_join_budget_ms` :38 (2000); `wdt.timeout_ms` :83 (8000)
- **Change**: mirror tag `# @tunable dev.uart_poll_wait_ms = 2` above :29; listed as a further site of that row; mirror tag `# @tunable dev.uart_poll_idle_ms = 50` above :32; listed as a further site of that row; mirror tag `# @tunable dev.uart_rxbuf = 512` above :33; listed as a further site of that row; tag `# @tunable l3.uart_crossover_exchange_join_step_ms = 100` above `JOIN_STEP_MS` (:37); tag `# @tunable l3.uart_crossover_exchange_join_budget_ms = 2000` above `JOIN_BUDGET_MS` (:38); mirror `wdt.timeout_ms` at :83: already named by A.U8.08; it gets the tag there. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests/test_asy_uart_link_driver.py`, `tests_hardware/flash/test_uart_crossover.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/device_scripts/uart_crossover_recovery.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.06, A.U8.08
- **Kind**: test

### A.U8C.92 Tag the tuned literals of `device_scripts/uart_crossover_recovery.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/uart_crossover_recovery.py` — `dev.uart_poll_wait_ms` :29 (2); `dev.uart_poll_idle_ms` :32 (50); `dev.uart_rxbuf` :33 (512); `l3.uart_crossover_exchange_join_step_ms` :38 (100); `l3.uart_crossover_exchange_join_budget_ms` :39 (2000); `wdt.timeout_ms` :118 (8000)
- **Change**: mirror tag `# @tunable dev.uart_poll_wait_ms = 2` above :29; listed as a further site of that row; mirror tag `# @tunable dev.uart_poll_idle_ms = 50` above :32; listed as a further site of that row; mirror tag `# @tunable dev.uart_rxbuf = 512` above :33; listed as a further site of that row; tag `# @tunable l3.uart_crossover_exchange_join_step_ms = 100` above `JOIN_STEP_MS` (:38); tag `# @tunable l3.uart_crossover_exchange_join_budget_ms = 2000` above `JOIN_BUDGET_MS` (:39); mirror `wdt.timeout_ms` at :118: already named by A.U8.08; it gets the tag there. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_uart_crossover.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/device_scripts/uart_crossover_exchange.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.06, A.U8.08, A.U8C.91
- **Kind**: test

### A.U8C.93 Tag the tuned literals of `device_scripts/uart_driver_read_never_blocks_the_loop.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py` — `l3.uart_driver_read_never_blocks_the_loop_trials` :26 (5); `dev.uart_poll_wait_ms` :27 (2); `l3.uart_driver_read_never_blocks_the_loop_start_timeout_ms` :79 (500); `l3.uart_driver_read_never_blocks_the_loop_read_timeout_ms` :79 (200); `l3.uart_driver_read_never_blocks_the_loop_raw_deadline_ms` :88 (500); `l3.uart_driver_read_never_blocks_the_loop_idle_window_ms` :119 (20); `wdt.timeout_ms` :126 (8000); deferred U26: `:106` (5)
- **Change**: tag `# @tunable l3.uart_driver_read_never_blocks_the_loop_trials = 5` above `TRIALS` (:26); mirror tag `# @tunable dev.uart_poll_wait_ms = 2` above :27; listed as a further site of that row; `_START_TIMEOUT_MS = 500` (new, module level) tagged `# @tunable l3.uart_driver_read_never_blocks_the_loop_start_timeout_ms = 500`; the literal at :79 becomes `_START_TIMEOUT_MS`; `_READ_TIMEOUT_MS = 200` (new, module level) tagged `# @tunable l3.uart_driver_read_never_blocks_the_loop_read_timeout_ms = 200`; the literal at :79 becomes `_READ_TIMEOUT_MS`; `_RAW_DEADLINE_MS = 500` (new, module level) tagged `# @tunable l3.uart_driver_read_never_blocks_the_loop_raw_deadline_ms = 500`; the literal at :88 becomes `_RAW_DEADLINE_MS`; `_IDLE_WINDOW_MS = 20` (new, module level) tagged `# @tunable l3.uart_driver_read_never_blocks_the_loop_idle_window_ms = 20`; the literal at :119 becomes `_IDLE_WINDOW_MS`; mirror `wdt.timeout_ms` at :126: already named by A.U8.08; it gets the tag there; deferred sleeps (:106): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_uart_crossover.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.06, A.U8.08, U26
- **Kind**: test

### A.U8C.94 Tag the tuned literals of `device_scripts/uart_idle_poll_rate.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/uart_idle_poll_rate.py` — `dev.uart_poll_wait_ms` :14 (2); `dev.uart_poll_idle_ms` :15 (50); `l3.uart_idle_poll_rate_sample_ms` :16 (3000); `l3.uart_idle_poll_rate_min_ratio` :20 (5); `l3.uart_idle_poll_rate_sample_step_ms` :68 (250); `l3.uart_idle_poll_rate_stop_poll_ms` :75 (10); `l3.uart_idle_poll_rate_cancel_settle_ms` :78 (20); `wdt.timeout_ms` :84 (8000); deferred U26: `:64` (100)
- **Change**: mirror tag `# @tunable dev.uart_poll_wait_ms = 2` above :14; listed as a further site of that row; mirror tag `# @tunable dev.uart_poll_idle_ms = 50` above :15; listed as a further site of that row; tag `# @tunable l3.uart_idle_poll_rate_sample_ms = 3000` above `SAMPLE_MS` (:16); tag `# @tunable l3.uart_idle_poll_rate_min_ratio = 5` above `_MIN_RATIO` (:20); `_SAMPLE_STEP_MS = 250` (new, module level) tagged `# @tunable l3.uart_idle_poll_rate_sample_step_ms = 250`; the literal at :68 becomes `_SAMPLE_STEP_MS`; `_STOP_POLL_MS = 10` (new, module level) tagged `# @tunable l3.uart_idle_poll_rate_stop_poll_ms = 10`; the literal at :75 becomes `_STOP_POLL_MS`; `_CANCEL_SETTLE_MS = 20` (new, module level) tagged `# @tunable l3.uart_idle_poll_rate_cancel_settle_ms = 20`; the literal at :78 becomes `_CANCEL_SETTLE_MS`; mirror `wdt.timeout_ms` at :84: already named by A.U8.08; it gets the tag there; deferred sleeps (:64): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_uart_crossover.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.06, A.U8.08, U26
- **Kind**: test

### A.U8C.95 Tag the tuned literals of `device_scripts/uart_link_under_concurrent_system_load.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py` — `dev.uart_poll_wait_ms` :24 (2); `dev.uart_poll_idle_ms` :25 (50); `dev.uart_rxbuf` :26 (512); `l3.uart_link_under_concurrent_system_load_run_ms` :29 (12000); `l3.uart_link_under_concurrent_system_load_min_transfers` :33 (20); `l3.uart_link_under_concurrent_system_load_churn_block` :37 (512); `l3.uart_link_under_concurrent_system_load_sensor_load_step_ms` :69, :80 (5); `l3.uart_link_under_concurrent_system_load_spi_load_step_ms` :87 (10); `l3.uart_link_under_concurrent_system_load_churn_step_ms` :104 (2); `l3.uart_link_under_concurrent_system_load_heap_sample_step_ms` :116 (8); `wdt.timeout_ms` :121 (8000); `l3.uart_link_under_concurrent_system_load_transfer_step_ms` :183 (5); `l3.uart_link_under_concurrent_system_load_cancel_settle_ms` :191 (50)
- **Change**: mirror tag `# @tunable dev.uart_poll_wait_ms = 2` above :24; listed as a further site of that row; mirror tag `# @tunable dev.uart_poll_idle_ms = 50` above :25; listed as a further site of that row; mirror tag `# @tunable dev.uart_rxbuf = 512` above :26; listed as a further site of that row; tag `# @tunable l3.uart_link_under_concurrent_system_load_run_ms = 12000` above `RUN_MS` (:29); tag `# @tunable l3.uart_link_under_concurrent_system_load_min_transfers = 20` above `_MIN_TRANSFERS` (:33); tag `# @tunable l3.uart_link_under_concurrent_system_load_churn_block = 512` above `_CHURN_BLOCK` (:37); `_SENSOR_LOAD_STEP_MS = 5` (new, module level) tagged `# @tunable l3.uart_link_under_concurrent_system_load_sensor_load_step_ms = 5`; each literal at :69, :80 becomes `_SENSOR_LOAD_STEP_MS`; `_SPI_LOAD_STEP_MS = 10` (new, module level) tagged `# @tunable l3.uart_link_under_concurrent_system_load_spi_load_step_ms = 10`; the literal at :87 becomes `_SPI_LOAD_STEP_MS`; `_CHURN_STEP_MS = 2` (new, module level) tagged `# @tunable l3.uart_link_under_concurrent_system_load_churn_step_ms = 2`; the literal at :104 becomes `_CHURN_STEP_MS`; `_HEAP_SAMPLE_STEP_MS = 8` (new, module level) tagged `# @tunable l3.uart_link_under_concurrent_system_load_heap_sample_step_ms = 8`; the literal at :116 becomes `_HEAP_SAMPLE_STEP_MS`; mirror `wdt.timeout_ms` at :121: already named by A.U8.08; it gets the tag there; `_TRANSFER_STEP_MS = 5` (new, module level) tagged `# @tunable l3.uart_link_under_concurrent_system_load_transfer_step_ms = 5`; the literal at :183 becomes `_TRANSFER_STEP_MS`; `_CANCEL_SETTLE_MS = 50` (new, module level) tagged `# @tunable l3.uart_link_under_concurrent_system_load_cancel_settle_ms = 50`; the literal at :191 becomes `_CANCEL_SETTLE_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/flash/test_uart_crossover.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.06, A.U8.08
- **Kind**: test

### A.U8C.96 Tag the tuned literals of `device_scripts/uart_read_never_blocks_the_loop.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py` — `l3.uart_read_never_blocks_the_loop_trials` :14 (5); `l3.uart_read_never_blocks_the_loop_trial_gap_ms` :48, :63 (30)
- **Change**: tag `# @tunable l3.uart_read_never_blocks_the_loop_trials = 5` above `TRIALS` (:14); `_TRIAL_GAP_MS = 30` (new, module level) tagged `# @tunable l3.uart_read_never_blocks_the_loop_trial_gap_ms = 30`; each literal at :48, :63 becomes `_TRIAL_GAP_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py`, `tests_hardware/flash/test_uart_crossover.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.97 Tag the tuned literals of `device_scripts/watchdog_starvation_reset.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/watchdog_starvation_reset.py` — `l3.starvation_wdt_ms` :7 (1500)
- **Change**: l3.starvation_wdt_ms at :7: already created and tagged by A.U8.08; nothing further here. Rows: no new row; each mirror is a further site in its product row.
- **Blast**: callers run on the board by `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py`, `tests_hardware/flash/test_watchdog_starvation.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.08
- **Kind**: test

### A.U8C.98 Tag the tuned literals of `device_scripts/wifi_reconnect_after_failed_attempts_repro.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py` — `l3.wifi_reconnect_after_failed_attempts_repro_control_max_polls` :76 (240); `wifi.sta_connect_poll_s` :76, :94, :134 (500); `wifi.sta_connect_poll_iters` :94 (10); `wifi.refresh_s` :96 (5); `wifi.wlan_down_settle_s` :104, :118 (2); `wifi.wlan_deinit_settle_s` :106, :120 (1); `l3.wifi_reconnect_after_failed_attempts_repro_ap_dwell_s` :114 (10); `wifi.wlan_mode_settle_s` :122 (1); `l3.wifi_reconnect_after_failed_attempts_repro_reconnect_max_polls` :134 (1200); deferred U26: `:83` (1)
- **Change**: `_CONTROL_MAX_POLLS = 240` (new, module level) tagged `# @tunable l3.wifi_reconnect_after_failed_attempts_repro_control_max_polls = 240`; the literal at :76 becomes `_CONTROL_MAX_POLLS`; mirror tag `# @tunable wifi.sta_connect_poll_s = 500` above :76, :94, :134; listed as a further site of that row; mirror tag `# @tunable wifi.sta_connect_poll_iters = 10` above :94; listed as a further site of that row; mirror tag `# @tunable wifi.refresh_s = 5` above :96; listed as a further site of that row; mirror tag `# @tunable wifi.wlan_down_settle_s = 2` above :104, :118; listed as a further site of that row; mirror tag `# @tunable wifi.wlan_deinit_settle_s = 1` above :106, :120; listed as a further site of that row; `_AP_DWELL_S = 10` (new, module level) tagged `# @tunable l3.wifi_reconnect_after_failed_attempts_repro_ap_dwell_s = 10`; the literal at :114 becomes `_AP_DWELL_S`; mirror tag `# @tunable wifi.wlan_mode_settle_s = 1` above :122; listed as a further site of that row; `_RECONNECT_MAX_POLLS = 1200` (new, module level) tagged `# @tunable l3.wifi_reconnect_after_failed_attempts_repro_reconnect_max_polls = 1200`; the literal at :134 becomes `_RECONNECT_MAX_POLLS`; deferred sleeps (:83): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (not referenced by any test file: a manual diagnostic) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.10, U26
- **Kind**: test

### A.U8C.99 Tag the tuned literals of `device_scripts/wifi_service_reconnect_repro.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/device_scripts/wifi_service_reconnect_repro.py` — `l3.wifi_service_reconnect_repro_hotspot_deadline_ms` :89 (180000); `l3.wifi_service_reconnect_repro_poll_s` :103, :135 (1); `l3.wifi_service_reconnect_repro_reconnect_deadline_ms` :119 (600000)
- **Change**: `_HOTSPOT_DEADLINE_MS = 180000` (new, module level) tagged `# @tunable l3.wifi_service_reconnect_repro_hotspot_deadline_ms = 180000`; the literal at :89 becomes `_HOTSPOT_DEADLINE_MS`; `_POLL_S = 1` (new, module level) tagged `# @tunable l3.wifi_service_reconnect_repro_poll_s = 1`; each literal at :103, :135 becomes `_POLL_S`; `_RECONNECT_DEADLINE_MS = 600000` (new, module level) tagged `# @tunable l3.wifi_service_reconnect_repro_reconnect_deadline_ms = 600000`; the literal at :119 becomes `_RECONNECT_DEADLINE_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers run on the board by `tests_scripts/test_device_script_config_flush.py` (script name unchanged; comment lines only on the device side) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.100 Tag the tuned literals of `error_log_helpers.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/error_log_helpers.py` — `l4.reset_errors_timeout_s` :14 (30.0); `l4.error_log_helpers_errcount_timeout_s` :23 (10.0)
- **Change**: l4.reset_errors_timeout_s at :14: already created and tagged by A.U8.05; nothing further here; `_ERRCOUNT_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.error_log_helpers_errcount_timeout_s = 10.0`; the literal at :23 becomes `_ERRCOUNT_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.05; A.U8.05 (`:14`)
- **Kind**: test

### A.U8C.101 Tag the tuned literals of `flash/conftest.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/flash/conftest.py` — `l3.conftest_scd30_rw_script_timeout_s` :32 (90.0)
- **Change**: `_SCD30_RW_SCRIPT_TIMEOUT_S = 90.0` (new, module level) tagged `# @tunable l3.conftest_scd30_rw_script_timeout_s = 90.0`; the literal at :32 becomes `_SCD30_RW_SCRIPT_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.102 Tag the tuned literals of `flash/test_bus_concurrency.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/flash/test_bus_concurrency.py` — `l3.bus_concurrency_long_script_timeout_s` :34, :49 (120.0); `l3.bus_concurrency_script_timeout_s` :40, :56, :64, :72, :81, :91, :99, :107, :115 (90.0); `l3.bus_concurrency_short_script_timeout_s` :123, :136, :148 (60.0); `l3.bus_concurrency_reset_script_timeout_s` :131 (30.0); `l3.bus_concurrency_reachable_timeout_s` :135 (30.0); `l3.bus_concurrency_reachable_poll_s` :135 (1.0)
- **Change**: `_LONG_SCRIPT_TIMEOUT_S = 120.0` (new, module level) tagged `# @tunable l3.bus_concurrency_long_script_timeout_s = 120.0`; each literal at :34, :49 becomes `_LONG_SCRIPT_TIMEOUT_S`; `_SCRIPT_TIMEOUT_S = 90.0` (new, module level) tagged `# @tunable l3.bus_concurrency_script_timeout_s = 90.0`; each literal at :40, :56, :64, :72, :81, :91, :99, :107, :115 becomes `_SCRIPT_TIMEOUT_S`; `_SHORT_SCRIPT_TIMEOUT_S = 60.0` (new, module level) tagged `# @tunable l3.bus_concurrency_short_script_timeout_s = 60.0`; each literal at :123, :136, :148 becomes `_SHORT_SCRIPT_TIMEOUT_S`; `_RESET_SCRIPT_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l3.bus_concurrency_reset_script_timeout_s = 30.0`; the literal at :131 becomes `_RESET_SCRIPT_TIMEOUT_S`; `_REACHABLE_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l3.bus_concurrency_reachable_timeout_s = 30.0`; the literal at :135 becomes `_REACHABLE_TIMEOUT_S`; `_REACHABLE_POLL_S = 1.0` (new, module level) tagged `# @tunable l3.bus_concurrency_reachable_poll_s = 1.0`; the literal at :135 becomes `_REACHABLE_POLL_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.103 Tag the tuned literals of `flash/test_bus_electrical_timing.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/flash/test_bus_electrical_timing.py` — `l3.bus_electrical_timing_irq_script_timeout_s` :59 (30.0); `l3.bus_electrical_timing_wrap_headroom_h` :107 (2)
- **Change**: `_IRQ_SCRIPT_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l3.bus_electrical_timing_irq_script_timeout_s = 30.0`; the literal at :59 becomes `_IRQ_SCRIPT_TIMEOUT_S`; tag `# @tunable l3.bus_electrical_timing_wrap_headroom_h = 2` above `_WRAP_FLOOR_MS` (:107). Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.104 Tag the tuned literals of `flash/test_fram_storage.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/flash/test_fram_storage.py` — `l3.fram_storage_short_script_timeout_s` :33, :53, :60, :87 (30.0); `l3.fram_storage_backup_script_timeout_s` :44 (150.0); `l3.fram_storage_reachable_timeout_s` :61 (30.0); `l3.fram_storage_reachable_poll_s` :61 (1.0); `l3.fram_storage_script_timeout_s` :62, :73, :123 (60.0); `l3.fram_storage_pause_script_timeout_s` :101 (90.0); `l3.fram_storage_lockout_script_timeout_s` :112 (45.0)
- **Change**: `_SHORT_SCRIPT_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l3.fram_storage_short_script_timeout_s = 30.0`; each literal at :33, :53, :60, :87 becomes `_SHORT_SCRIPT_TIMEOUT_S`; `_BACKUP_SCRIPT_TIMEOUT_S = 150.0` (new, module level) tagged `# @tunable l3.fram_storage_backup_script_timeout_s = 150.0`; the literal at :44 becomes `_BACKUP_SCRIPT_TIMEOUT_S`; `_REACHABLE_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l3.fram_storage_reachable_timeout_s = 30.0`; the literal at :61 becomes `_REACHABLE_TIMEOUT_S`; `_REACHABLE_POLL_S = 1.0` (new, module level) tagged `# @tunable l3.fram_storage_reachable_poll_s = 1.0`; the literal at :61 becomes `_REACHABLE_POLL_S`; `_SCRIPT_TIMEOUT_S = 60.0` (new, module level) tagged `# @tunable l3.fram_storage_script_timeout_s = 60.0`; each literal at :62, :73, :123 becomes `_SCRIPT_TIMEOUT_S`; `_PAUSE_SCRIPT_TIMEOUT_S = 90.0` (new, module level) tagged `# @tunable l3.fram_storage_pause_script_timeout_s = 90.0`; the literal at :101 becomes `_PAUSE_SCRIPT_TIMEOUT_S`; `_LOCKOUT_SCRIPT_TIMEOUT_S = 45.0` (new, module level) tagged `# @tunable l3.fram_storage_lockout_script_timeout_s = 45.0`; the literal at :112 becomes `_LOCKOUT_SCRIPT_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.105 Tag the tuned literals of `flash/test_memory_stress.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/flash/test_memory_stress.py` — `l3.memory_stress_headroom_script_timeout_s` :35 (120.0)
- **Change**: `_HEADROOM_SCRIPT_TIMEOUT_S = 120.0` (new, module level) tagged `# @tunable l3.memory_stress_headroom_script_timeout_s = 120.0`; the literal at :35 becomes `_HEADROOM_SCRIPT_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.106 Tag the tuned literals of `flash/test_reboot_persistence.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/flash/test_reboot_persistence.py` — `l3.reboot_persistence_reachable_timeout_s` :36, :79 (30.0); `l3.reboot_persistence_reachable_poll_s` :36, :79 (1.0); `l3.reboot_persistence_boot_log_tail_s` :64 (20.0)
- **Change**: `_REACHABLE_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l3.reboot_persistence_reachable_timeout_s = 30.0`; each literal at :36, :79 becomes `_REACHABLE_TIMEOUT_S`; `_REACHABLE_POLL_S = 1.0` (new, module level) tagged `# @tunable l3.reboot_persistence_reachable_poll_s = 1.0`; each literal at :36, :79 becomes `_REACHABLE_POLL_S`; `_BOOT_LOG_TAIL_S = 20.0` (new, module level) tagged `# @tunable l3.reboot_persistence_boot_log_tail_s = 20.0`; the literal at :64 becomes `_BOOT_LOG_TAIL_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.107 Tag the tuned literals of `flash/test_sensor_accuracy.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/flash/test_sensor_accuracy.py` — `l3.sensor_accuracy_scd30_script_timeout_s` :24 (100.0); `l3.sensor_accuracy_bmp3xx_script_timeout_s` :31 (60.0); `l3.sensor_accuracy_sgp40_script_timeout_s` :40 (150.0); `l3.sensor_accuracy_isl29125_script_timeout_s` :48 (30.0); `l3.sensor_accuracy_envelope_script_timeout_s` :61 (420.0); `l3.sensor_accuracy_scenarios_script_timeout_s` :74 (900.0); `l3.sensor_accuracy_conformance_script_timeout_s` :84 (120.0)
- **Change**: `_SCD30_SCRIPT_TIMEOUT_S = 100.0` (new, module level) tagged `# @tunable l3.sensor_accuracy_scd30_script_timeout_s = 100.0`; the literal at :24 becomes `_SCD30_SCRIPT_TIMEOUT_S`; `_BMP3XX_SCRIPT_TIMEOUT_S = 60.0` (new, module level) tagged `# @tunable l3.sensor_accuracy_bmp3xx_script_timeout_s = 60.0`; the literal at :31 becomes `_BMP3XX_SCRIPT_TIMEOUT_S`; `_SGP40_SCRIPT_TIMEOUT_S = 150.0` (new, module level) tagged `# @tunable l3.sensor_accuracy_sgp40_script_timeout_s = 150.0`; the literal at :40 becomes `_SGP40_SCRIPT_TIMEOUT_S`; `_ISL29125_SCRIPT_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l3.sensor_accuracy_isl29125_script_timeout_s = 30.0`; the literal at :48 becomes `_ISL29125_SCRIPT_TIMEOUT_S`; `_ENVELOPE_SCRIPT_TIMEOUT_S = 420.0` (new, module level) tagged `# @tunable l3.sensor_accuracy_envelope_script_timeout_s = 420.0`; the literal at :61 becomes `_ENVELOPE_SCRIPT_TIMEOUT_S`; `_SCENARIOS_SCRIPT_TIMEOUT_S = 900.0` (new, module level) tagged `# @tunable l3.sensor_accuracy_scenarios_script_timeout_s = 900.0`; the literal at :74 becomes `_SCENARIOS_SCRIPT_TIMEOUT_S`; `_CONFORMANCE_SCRIPT_TIMEOUT_S = 120.0` (new, module level) tagged `# @tunable l3.sensor_accuracy_conformance_script_timeout_s = 120.0`; the literal at :84 becomes `_CONFORMANCE_SCRIPT_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.108 Tag the tuned literals of `flash/test_task_supervisor.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/flash/test_task_supervisor.py` — `l3.task_supervisor_script_timeout_s` :19 (15.0)
- **Change**: `_SCRIPT_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l3.task_supervisor_script_timeout_s = 15.0`; the literal at :19 becomes `_SCRIPT_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.109 Tag the tuned literals of `flash/test_toolchain_flash_boot.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/flash/test_toolchain_flash_boot.py` — `l3.toolchain_flash_boot_env_setup_timeout_s` :39 (1200); `l3.toolchain_flash_boot_build_timeout_s` :65 (600); `l3.toolchain_flash_boot_load_timeout_s` :82 (120); `l3.toolchain_flash_boot_load_retry_backoff_s` :87 (2.0); `l3.toolchain_flash_boot_reachable_timeout_s` :92 (30.0); `l3.toolchain_flash_boot_reachable_poll_s` :92 (1.0)
- **Change**: `_ENV_SETUP_TIMEOUT_S = 1200` (new, module level) tagged `# @tunable l3.toolchain_flash_boot_env_setup_timeout_s = 1200`; the literal at :39 becomes `_ENV_SETUP_TIMEOUT_S`; `_BUILD_TIMEOUT_S = 600` (new, module level) tagged `# @tunable l3.toolchain_flash_boot_build_timeout_s = 600`; the literal at :65 becomes `_BUILD_TIMEOUT_S`; `_LOAD_TIMEOUT_S = 120` (new, module level) tagged `# @tunable l3.toolchain_flash_boot_load_timeout_s = 120`; the literal at :82 becomes `_LOAD_TIMEOUT_S`; `_LOAD_RETRY_BACKOFF_S = 2.0` (new, module level) tagged `# @tunable l3.toolchain_flash_boot_load_retry_backoff_s = 2.0`; the literal at :87 becomes `_LOAD_RETRY_BACKOFF_S`; `_REACHABLE_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l3.toolchain_flash_boot_reachable_timeout_s = 30.0`; the literal at :92 becomes `_REACHABLE_TIMEOUT_S`; `_REACHABLE_POLL_S = 1.0` (new, module level) tagged `# @tunable l3.toolchain_flash_boot_reachable_poll_s = 1.0`; the literal at :92 becomes `_REACHABLE_POLL_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/manual/manual_toolchain.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.110 Tag the tuned literals of `flash/test_uart_crossover.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/flash/test_uart_crossover.py` — `l3.uart_crossover_script_timeout_s` :47, :62, :69 (120.0); `l3.uart_crossover_long_script_timeout_s` :54, :76, :84 (180.0)
- **Change**: `_SCRIPT_TIMEOUT_S = 120.0` (new, module level) tagged `# @tunable l3.uart_crossover_script_timeout_s = 120.0`; each literal at :47, :62, :69 becomes `_SCRIPT_TIMEOUT_S`; `_LONG_SCRIPT_TIMEOUT_S = 180.0` (new, module level) tagged `# @tunable l3.uart_crossover_long_script_timeout_s = 180.0`; each literal at :54, :76, :84 becomes `_LONG_SCRIPT_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.111 Tag the tuned literals of `flash/test_watchdog_starvation.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/flash/test_watchdog_starvation.py` — `l3.watchdog_starvation_script_timeout_s` :23 (15.0); `l3.watchdog_starvation_reset_elapsed_max_s` :29 (10.0); `l3.watchdog_starvation_device_present_timeout_s` :41, :47, :72, :77 (15.0); `l3.watchdog_starvation_device_present_poll_s` :41, :47, :72, :77 (0.3); `l3.watchdog_starvation_reachable_after_reset_timeout_s` :42 (15.0); `l3.watchdog_starvation_reachable_after_reset_poll_s` :42 (0.5); `l3.watchdog_starvation_reachable_timeout_s` :58 (30.0); `l3.watchdog_starvation_reachable_poll_s` :58 (1.0); `l3.watchdog_starvation_fallback_script_timeout_s` :62 (20.0); `l3.watchdog_starvation_fallback_elapsed_max_s` :68 (12.0)
- **Change**: `_SCRIPT_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l3.watchdog_starvation_script_timeout_s = 15.0`; the literal at :23 becomes `_SCRIPT_TIMEOUT_S`; `_RESET_ELAPSED_MAX_S = 10.0` (new, module level) tagged `# @tunable l3.watchdog_starvation_reset_elapsed_max_s = 10.0`; the literal at :29 becomes `_RESET_ELAPSED_MAX_S`; `_DEVICE_PRESENT_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l3.watchdog_starvation_device_present_timeout_s = 15.0`; each literal at :41, :47, :72, :77 becomes `_DEVICE_PRESENT_TIMEOUT_S`; `_DEVICE_PRESENT_POLL_S = 0.3` (new, module level) tagged `# @tunable l3.watchdog_starvation_device_present_poll_s = 0.3`; each literal at :41, :47, :72, :77 becomes `_DEVICE_PRESENT_POLL_S`; `_REACHABLE_AFTER_RESET_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l3.watchdog_starvation_reachable_after_reset_timeout_s = 15.0`; the literal at :42 becomes `_REACHABLE_AFTER_RESET_TIMEOUT_S`; `_REACHABLE_AFTER_RESET_POLL_S = 0.5` (new, module level) tagged `# @tunable l3.watchdog_starvation_reachable_after_reset_poll_s = 0.5`; the literal at :42 becomes `_REACHABLE_AFTER_RESET_POLL_S`; `_REACHABLE_TIMEOUT_S = 30.0` (new, module level) tagged `# @tunable l3.watchdog_starvation_reachable_timeout_s = 30.0`; the literal at :58 becomes `_REACHABLE_TIMEOUT_S`; `_REACHABLE_POLL_S = 1.0` (new, module level) tagged `# @tunable l3.watchdog_starvation_reachable_poll_s = 1.0`; the literal at :58 becomes `_REACHABLE_POLL_S`; `_FALLBACK_SCRIPT_TIMEOUT_S = 20.0` (new, module level) tagged `# @tunable l3.watchdog_starvation_fallback_script_timeout_s = 20.0`; the literal at :62 becomes `_FALLBACK_SCRIPT_TIMEOUT_S`; `_FALLBACK_ELAPSED_MAX_S = 12.0` (new, module level) tagged `# @tunable l3.watchdog_starvation_fallback_elapsed_max_s = 12.0`; the literal at :68 becomes `_FALLBACK_ELAPSED_MAX_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.112 Tag the tuned literals of `harness.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits; G1/R15 "every instrument value is a registered tunable with its basis" (the ceiling instrument); G8/R31 (subprocess and wait bounds); G7/R23 (the two USB settle sleeps deferred to U26)
- **Site**: `tests_hardware/harness.py` — `l4.ceiling_settle_s` :56 (1.0); `l4.ceiling_dwell_s` :56 (0.3); `l4.ceiling_probe_connect_timeout_s` :113 (2.0); `l4.ceiling_drain_timeout_s` :138 (10.0); `l4.ceiling_drain_release_s` :138 (1.0); `l4.ceiling_drain_hold_s` :138 (0.3); `l4.ceiling_hold_check_timeout_s` :165 (0.05); `l4.harness_usb_rebind_cmd_timeout_s` :201, :203 (10.0); `l4.harness_wait_until_poll_s` :224 (1.0); `l4.harness_serving_probe_timeout_s` :257 (10.0); `l4.harness_serving_restore_timeout_s` :258 (90.0); `l4.harness_serving_restore_poll_s` :259 (3.0); `l4.harness_script_server_timeout_s` :264 (120.0); `l4.harness_script_server_handover_s` :264 (20.0); `l4.harness_script_server_probe_timeout_s` :272 (3.0); `l4.harness_max_device_rebinds` :304 (2); `l4.harness_mpremote_default_timeout_s` :345 (60.0); `l4.harness_usb_grace_s` :368, :399, :404, :486 (10.0); `l4.harness_usb_grace_poll_s` :389, :499 (0.5); `l4.harness_mpremote_short_timeout_s` :413, :480 (10.0); `l4.harness_presence_probe_timeout_s` :423 (0.2); `l4.harness_mpremote_reset_timeout_s` :462, :470 (15.0); `l4.harness_log_tail_read_timeout_s` :491 (0.5); deferred U26: `:202` (2.0); deferred U26: `:204` (3.0)
- **Change**: l4.ceiling_settle_s at :56: already created and tagged by A.U8.05; nothing further here; l4.ceiling_dwell_s at :56: already created and tagged by A.U8.05; nothing further here; l4.ceiling_probe_connect_timeout_s at :113: already created and tagged by A.U8.05; nothing further here; l4.ceiling_drain_timeout_s at :138: already created and tagged by A.U8.05; nothing further here; l4.ceiling_drain_release_s at :138: already created and tagged by A.U8.05; nothing further here; l4.ceiling_drain_hold_s at :138: already created and tagged by A.U8.05; nothing further here; `_HOLD_CHECK_TIMEOUT_S = 0.05` (new, module level) tagged `# @tunable l4.ceiling_hold_check_timeout_s = 0.05`; the literal at :165 becomes `_HOLD_CHECK_TIMEOUT_S`; `_USB_REBIND_CMD_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.harness_usb_rebind_cmd_timeout_s = 10.0`; each literal at :201, :203 becomes `_USB_REBIND_CMD_TIMEOUT_S`; `_WAIT_UNTIL_POLL_S = 1.0` (new, module level) tagged `# @tunable l4.harness_wait_until_poll_s = 1.0`; the literal at :224 becomes `_WAIT_UNTIL_POLL_S`; `_SERVING_PROBE_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.harness_serving_probe_timeout_s = 10.0`; the literal at :257 becomes `_SERVING_PROBE_TIMEOUT_S`; `_SERVING_RESTORE_TIMEOUT_S = 90.0` (new, module level) tagged `# @tunable l4.harness_serving_restore_timeout_s = 90.0`; the literal at :258 becomes `_SERVING_RESTORE_TIMEOUT_S`; `_SERVING_RESTORE_POLL_S = 3.0` (new, module level) tagged `# @tunable l4.harness_serving_restore_poll_s = 3.0`; the literal at :259 becomes `_SERVING_RESTORE_POLL_S`; `_SCRIPT_SERVER_TIMEOUT_S = 120.0` (new, module level) tagged `# @tunable l4.harness_script_server_timeout_s = 120.0`; the literal at :264 becomes `_SCRIPT_SERVER_TIMEOUT_S`; `_SCRIPT_SERVER_HANDOVER_S = 20.0` (new, module level) tagged `# @tunable l4.harness_script_server_handover_s = 20.0`; the literal at :264 becomes `_SCRIPT_SERVER_HANDOVER_S`; `_SCRIPT_SERVER_PROBE_TIMEOUT_S = 3.0` (new, module level) tagged `# @tunable l4.harness_script_server_probe_timeout_s = 3.0`; the literal at :272 becomes `_SCRIPT_SERVER_PROBE_TIMEOUT_S`; tag `# @tunable l4.harness_max_device_rebinds = 2` above `_MAX_DEVICE_REBINDS` (:304); `_MPREMOTE_DEFAULT_TIMEOUT_S = 60.0` (new, module level) tagged `# @tunable l4.harness_mpremote_default_timeout_s = 60.0`; the literal at :345 becomes `_MPREMOTE_DEFAULT_TIMEOUT_S`; `_USB_GRACE_S = 10.0` (new, module level) tagged `# @tunable l4.harness_usb_grace_s = 10.0`; each literal at :368, :399, :404, :486 becomes `_USB_GRACE_S`; `_USB_GRACE_POLL_S = 0.5` (new, module level) tagged `# @tunable l4.harness_usb_grace_poll_s = 0.5`; each literal at :389, :499 becomes `_USB_GRACE_POLL_S`; `_MPREMOTE_SHORT_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.harness_mpremote_short_timeout_s = 10.0`; each literal at :413, :480 becomes `_MPREMOTE_SHORT_TIMEOUT_S`; `_PRESENCE_PROBE_TIMEOUT_S = 0.2` (new, module level) tagged `# @tunable l4.harness_presence_probe_timeout_s = 0.2`; the literal at :423 becomes `_PRESENCE_PROBE_TIMEOUT_S`; `_MPREMOTE_RESET_TIMEOUT_S = 15.0` (new, module level) tagged `# @tunable l4.harness_mpremote_reset_timeout_s = 15.0`; each literal at :462, :470 becomes `_MPREMOTE_RESET_TIMEOUT_S`; `_LOG_TAIL_READ_TIMEOUT_S = 0.5` (new, module level) tagged `# @tunable l4.harness_log_tail_read_timeout_s = 0.5`; the literal at :491 becomes `_LOG_TAIL_READ_TIMEOUT_S`; deferred sleeps (:202, :204): no tag now; classified once U26 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers every bench and flash test through `board`/`bench` fixtures and `restore_board_to_serving()`/`wait_for_script_server()`/`discover_max_connections()` (grep); defaults only are renamed, no signature changes · generated — · js — · tests existing: `tests_scripts/test_request_timeout_ceiling.py:117-131` reads the ceiling defaults by AST (unchanged, comment lines only), `tests_scripts/test_bench_harness_helpers.py` (drives `wait_for_script_server` against a fake: unchanged) · twin — · docs SPEC Part N rows; `tests_hardware/README.md` timing statements cite the IDs · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.05, U26; A.U8.05 (the six ceiling defaults)
- **Kind**: test

### A.U8C.113 Tag the tuned literals of `http_client.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/http_client.py` — `l4.http_client_fetch_timeout_s` :28 (10.0)
- **Change**: `_FETCH_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l4.http_client_fetch_timeout_s = 10.0`; the literal at :28 becomes `_FETCH_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers every bench test and helper calling `http_client.fetch()` without `timeout_s` (default unchanged) · generated — · js — · tests — · twin — · docs SPEC Part N row · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.114 Tag the tuned literals of `isl29125_conformance.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/isl29125_conformance.py` — `l3.isl29125_conformance_probe_timeout_s` :56 (180.0)
- **Change**: `_PROBE_TIMEOUT_S = 180.0` (new, module level) tagged `# @tunable l3.isl29125_conformance_probe_timeout_s = 180.0`; the literal at :56 becomes `_PROBE_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.115 Tag the tuned literals of `manual/manual_bus_electrical.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/manual/manual_bus_electrical.py` — `l4.manual_bus_electrical_recovery_watch_s` :27 (30.0); `l4.manual_bus_electrical_reboot_watch_s` :44 (30.0)
- **Change**: `_RECOVERY_WATCH_S = 30.0` (new, module level) tagged `# @tunable l4.manual_bus_electrical_recovery_watch_s = 30.0`; the literal at :27 becomes `_RECOVERY_WATCH_S`; `_REBOOT_WATCH_S = 30.0` (new, module level) tagged `# @tunable l4.manual_bus_electrical_reboot_watch_s = 30.0`; the literal at :44 becomes `_REBOOT_WATCH_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.116 Tag the tuned literals of `manual/manual_sensor_accuracy.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/manual/manual_sensor_accuracy.py` — `l4.manual_sensor_accuracy_isl29125_repeatability_pct` :59 (10.0)
- **Change**: tag `# @tunable l4.manual_sensor_accuracy_isl29125_repeatability_pct = 10.0` above `_ISL29125_REPEATABILITY_TOLERANCE_PCT` (:59). Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.117 Tag the tuned literals of `manual/manual_toolchain.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/manual/manual_toolchain.py` — `l3.toolchain_flash_boot_build_timeout_s` :28 (600); `l3.toolchain_flash_boot_load_timeout_s` :42 (120)
- **Change**: `_BUILD_TIMEOUT_S = 600` (new, module level) tagged `# @tunable l3.toolchain_flash_boot_build_timeout_s = 600`; the literal at :28 becomes `_BUILD_TIMEOUT_S`; `_LOAD_TIMEOUT_S = 120` (new, module level) tagged `# @tunable l3.toolchain_flash_boot_load_timeout_s = 120`; the literal at :42 becomes `_LOAD_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged; shared IDs also sited in `tests_hardware/flash/test_toolchain_flash_boot.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8C.109
- **Kind**: test

### A.U8C.118 Tag the tuned literals of `rogue_udp_responder.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests_hardware/rogue_udp_responder.py` — `l4.rogue_udp_responder_recv_timeout_s` :15 (0.5); `l4.rogue_udp_responder_join_timeout_s` :38 (5.0)
- **Change**: `_RECV_TIMEOUT_S = 0.5` (new, module level) tagged `# @tunable l4.rogue_udp_responder_recv_timeout_s = 0.5`; the literal at :15 becomes `_RECV_TIMEOUT_S`; `_JOIN_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l4.rogue_udp_responder_join_timeout_s = 5.0`; the literal at :38 becomes `_JOIN_TIMEOUT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.119 Tag the tuned literals of `soak_tiers.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits; G4/R54 names "soak durations"; the file was absent from the old search (V.U8.28 gap (c))
- **Site**: `tests_hardware/soak_tiers.py` — `l4.soak_tiers_short_s` :7 (60.0); `l4.soak_tiers_mid_s` :7 (600.0); `l4.soak_tiers_long_h` :7 (6)
- **Change**: tag `# @tunable l4.soak_tiers_short_s = 60.0` above `SOAK_TIER_SECONDS["short"]` (:7); tag `# @tunable l4.soak_tiers_mid_s = 600.0` above `SOAK_TIER_SECONDS["mid"]` (:7); tag `# @tunable l4.soak_tiers_long_h = 6` above `SOAK_TIER_SECONDS["long"]` (:7); the three tags stack above `:7` (the tag grammar allows stacking above one line). Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: the value's own observable on the dev bench (elapsed, count or reading) with date and run count, L3/L4` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers `tests_hardware/conftest.py:19, :29, :33`, `tests_hardware/flash/test_memory_stress.py:91`, `tests_hardware/flash/test_bus_electrical_timing.py:90`, `tests_hardware/bench/test_memory_stress_bench.py` (import `SOAK_TIER_SECONDS`, unchanged) · generated — · js — · tests — · twin — · docs `tests_hardware/README.md:87` ("long=6h") cites the IDs · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

## Hit table

Every hit of C.0.1 in a classified file, keyed (file:line, kind, literal). Verdict classes per C.0.2.

| file:line | kind | literal | verdict | ID or reason |
|---|---|---|---|---|
| `tests/_boot_contiguity_probe.py:36` | const | 20000 | tuned | `l3.heap_layout_after_full_boot_sequence_starter_loop_timeout_ms` — shared with the device script it mirrors (comment :34-35) |
| `tests/_boot_contiguity_probe.py:37` | const | 250 | tuned | `l3.heap_layout_after_full_boot_sequence_starter_loop_grace_ms` — shared, as above |
| `tests/_boot_contiguity_probe.py:38` | const | 15 | tuned | `l3.heap_layout_after_full_boot_sequence_timers_timeout_s` — shared, as above |
| `tests/_boot_contiguity_probe.py:106` | call | 20 | tuned | `l3.heap_layout_after_full_boot_sequence_starter_poll_ms` — poll step of the starter-loop wait; same step at the device script :190 |
| `tests/_bus_hazard_catalog.py:29` | const-c | 7 | not tagged (fact) | I2C reserved address ranges (I2C-bus specification) |
| `tests/_bus_hazard_catalog.py:29` | const-c | 120 | not tagged (fact) | I2C reserved address ranges (I2C-bus specification) |
| `tests/_bus_hazard_catalog.py:29` | const-c | 127 | not tagged (fact) | I2C reserved address ranges (I2C-bus specification) |
| `tests/_bus_hazard_catalog.py:84` | const | 8300000 | test input | seeded BMP3xx ADC values and the expected results computed from them |
| `tests/_bus_hazard_catalog.py:85` | const | 8500000 | test input | seeded BMP3xx ADC values and the expected results computed from them |
| `tests/_bus_hazard_catalog.py:86` | const | 28.460795242070162 | test input | seeded BMP3xx ADC values and the expected results computed from them |
| `tests/_bus_hazard_catalog.py:87` | const | 713.765147356092 | test input | seeded BMP3xx ADC values and the expected results computed from them |
| `tests/_bus_hazard_catalog.py:117` | const | 412.5 | test input | seeded known-good sensor values a torn read would miss |
| `tests/_bus_hazard_catalog.py:118` | const | 23.4 | test input | seeded known-good sensor values a torn read would miss |
| `tests/_bus_hazard_catalog.py:119` | const | 45.6 | test input | seeded known-good sensor values a torn read would miss |
| `tests/_bus_hazard_catalog.py:120` | const | 32768 | test input | seeded known-good sensor values a torn read would miss |
| `tests/_bus_hazard_catalog.py:121` | const-c | 8192 | test input | seeded known-good sensor values a torn read would miss |
| `tests/_bus_hazard_catalog.py:121` | const-c | 6144 | test input | seeded known-good sensor values a torn read would miss |
| `tests/_bus_hazard_catalog.py:121` | const-c | 4096 | test input | seeded known-good sensor values a torn read would miss |
| `tests/_digital_twin_construction_scenarios.py:131` | kw | 10.0 | tuned | `l2.construction_scenarios_run_timeout_s` — run_timed hang bound, one value in the file |
| `tests/_digital_twin_construction_scenarios.py:147` | call | 1.0 | deferred U25 | if kept: `l2.sensortask_integration_webserver_bind_wait_s` — fixed readiness sleep for the webserver bind (G7/R23 twin readiness sleep); same purpose as test_digital_twin_sensortask_integration.py's _start_webserver() |
| `tests/_digital_twin_construction_scenarios.py:160` | kw | 10.0 | tuned | `l2.construction_scenarios_run_timeout_s` — run_timed hang bound, one value in the file |
| `tests/_digital_twin_construction_scenarios.py:193` | call | 1.0 | deferred U25 | if kept: `l2.sensortask_integration_webserver_bind_wait_s` — fixed readiness sleep for the webserver bind (G7/R23 twin readiness sleep); same purpose as test_digital_twin_sensortask_integration.py's _start_webserver() |
| `tests/_digital_twin_construction_scenarios.py:203` | kw | 10.0 | tuned | `l2.construction_scenarios_run_timeout_s` — run_timed hang bound, one value in the file |
| `tests/_sensortask_scenarios.py:78` | const-c | 8192 | not tagged (fact) | FRAM part sizes keyed to their fakes (MB85RS64V 8 KiB, MB85RS2MTA 256 KiB) |
| `tests/_sensortask_scenarios.py:79` | const-c | 262144 | not tagged (fact) | FRAM part sizes keyed to their fakes (MB85RS64V 8 KiB, MB85RS2MTA 256 KiB) |
| `tests/_sensortask_scenarios.py:293` | assert | 150000 | not tagged (fact) | SCD30 clock stretching up to 150 ms (Interface Description p.2), in µs |
| `tests/_sensortask_scenarios.py:300` | assert | 50000 | not tagged (fact) | rp2 port I2C timeout default 50 ms, in µs |
| `tests/_strict_json.py:18` | const | 32 | not tagged (fact) | RFC 8259 §7 control-character bound |
| `tests/_uart_comm_harness.py:32` | const | 8 | test input | payload size chosen for the test pair (every test file computes its frames from it) |
| `tests/_uart_comm_harness.py:33` | const | 100 | tuned | `l1.uart_comm_harness_timeout_ms` — the test pair's reply timeout, waited out on the real clock in every timeout test |
| `tests/_uart_comm_harness.py:34` | const | 1 | tuned | `l1.uart_comm_harness_poll_wait_ms` — the test pair's driver poll step (real clock) |
| `tests/_uart_comm_harness.py:37` | param | 10 | tuned | `l1.uart_comm_harness_run_limit_s` — default hang bound of run() |
| `tests/_uart_comm_harness.py:103` | call | 5 | tuned | `l1.uart_comm_harness_listener_drain_s` — bound on awaiting the listener out |
| `tests/_uart_link_contract.py:154` | assert | 4 | test input | byte counts computed from the scripted writes of the case |
| `tests/_uart_link_contract.py:204` | assert | 3 | test input | byte counts computed from the scripted writes of the case |
| `tests/_uart_link_contract.py:206` | assert | 7 | test input | byte counts computed from the scripted writes of the case |
| `tests/_uart_link_contract.py:217` | assert | 1 | test input | byte counts computed from the scripted writes of the case |
| `tests/_uart_link_contract.py:221` | assert | 1 | test input | byte counts computed from the scripted writes of the case |
| `tests/_webserver_concurrency_scenarios.py:105` | const | 2048 | mirror | → `web.max_content_length` — "shipped max_content_length … stated, never read back" |
| `tests/_webserver_concurrency_scenarios.py:140` | call | 0.5 | deferred U25 | if kept: `l2.webserver_concurrency_scenarios_start_wait_s` — fixed readiness sleep G7/R23 names (`:128-140`) |
| `tests/_webserver_concurrency_scenarios.py:168` | call | 0.05 | tuned | `l2.webserver_concurrency_scenarios_flaky_hold_s` — how long the flaky client holds its partial request before closing |
| `tests/_webserver_concurrency_scenarios.py:174` | param | 5.0 | tuned | `l2.webserver_concurrency_scenarios_still_serving_timeout_s` — poll deadline default of _still_serving() |
| `tests/_webserver_concurrency_scenarios.py:181` | call | 2.0 | tuned | `l2.webserver_concurrency_scenarios_request_timeout_s` — per-probe bound inside _still_serving() |
| `tests/_webserver_concurrency_scenarios.py:187` | call | 0.1 | tuned | `l2.webserver_concurrency_scenarios_still_serving_poll_s` — poll step |
| `tests/_webserver_concurrency_scenarios.py:190` | param | 10.0 | tuned | `l2.webserver_concurrency_scenarios_drain_timeout_s` — poll deadline default of _drained() |
| `tests/_webserver_concurrency_scenarios.py:201` | call | 0.05 | tuned | `l2.webserver_concurrency_scenarios_drain_poll_s` — poll step |
| `tests/_webserver_concurrency_scenarios.py:470` | call | 0.25 | tuned | `l2.webserver_concurrency_scenarios_health_check_interval_s` — paces the health checks during the fluctuating waves |
| `tests/_webserver_concurrency_scenarios.py:471` | kw | 3.0 | tuned | `l2.webserver_concurrency_scenarios_health_check_timeout_s` — per-check deadline during the waves |
| `tests/_webserver_concurrency_scenarios.py:495` | call | 0.3 | deferred U25 | if kept: `l2.webserver_concurrency_scenarios_slow_open_wait_s` — fixed sleep for the slow connections to open (a probe would take a slot: G7/R23 decides) |
| `tests/_webserver_concurrency_scenarios.py:532` | call | 0.2 | deferred U25 | if kept: `l2.webserver_concurrency_scenarios_hang_open_wait_s` — fixed sleep for the hanging connections to be admitted (as :495) |
| `tests/_webserver_concurrency_scenarios.py:543` | kw | 20.0 | tuned | `l2.webserver_concurrency_scenarios_reclaim_timeout_s` — poll deadline covering the outer_cap_s reclaim; Dependant of web.outer_cap_s |
| `tests/_webserver_concurrency_scenarios.py:678` | assert | 10000 | tuned | `l2.webserver_concurrency_scenarios_served_elapsed_max_ms` — per-response time budget |
| `tests/_webserver_concurrency_scenarios.py:740` | call | 200 | tuned | `l2.webserver_concurrency_scenarios_loop_stall_ms` — deliberate loop stall; must stay under one Linux SYN retry (1 s, comment :722) |
| `tests/_webserver_concurrency_scenarios.py:741` | call | 0.5 | deferred U25 | if kept: `l2.webserver_concurrency_scenarios_burst_settle_s` — fixed sleep before counting admitted connections |
| `tests/machine.py:19` | const | 0 | not tagged (identifier) | enum value of the faked machine API (bit values match rp2, comment :21-23) |
| `tests/machine.py:20` | const | 1 | not tagged (identifier) | enum value of the faked machine API (bit values match rp2, comment :21-23) |
| `tests/machine.py:24` | const | 4 | not tagged (identifier) | enum value of the faked machine API (bit values match rp2, comment :21-23) |
| `tests/machine.py:25` | const | 8 | not tagged (identifier) | enum value of the faked machine API (bit values match rp2, comment :21-23) |
| `tests/machine.py:29` | const | 1 | not tagged (identifier) | enum value of the faked machine API (bit values match rp2, comment :21-23) |
| `tests/machine.py:30` | const | 2 | not tagged (identifier) | enum value of the faked machine API (bit values match rp2, comment :21-23) |
| `tests/machine.py:118` | param | 50000 | not tagged (fact) | real machine.I2C default timeout 50 ms (ports/rp2/machine_i2c.c:38 DEFAULT_I2C_TIMEOUT); freq default is not a hit |
| `tests/machine.py:206` | const | 32 | not tagged (fact) | ports/rp2/machine_spi.c:267 dma_min_size_threshold |
| `tests/machine.py:213` | const | 0 | not tagged (identifier) | enum value of the faked machine API (bit values match rp2, comment :21-23) |
| `tests/machine.py:214` | const | 1 | not tagged (identifier) | enum value of the faked machine API (bit values match rp2, comment :21-23) |
| `tests/machine.py:330` | const | 3 | not tagged (identifier) | py/stream.h MP_STREAM_POLL |
| `tests/machine.py:331` | const | 32 | not tagged (fact) | ports/rp2/machine_uart.c:68-69 buffer bounds |
| `tests/machine.py:332` | const | 32766 | not tagged (fact) | ports/rp2/machine_uart.c:68-69 buffer bounds |
| `tests/machine.py:348` | param | 1 | not tagged (fact) | fake's default of the real parameter; rp2 floors timeout_char at 13000/baud+1 ms (machine_uart.c:406-409); stored only, never waited on (`:372`) |
| `tests/machine.py:605` | const | 0 | not tagged (identifier) | enum value of the faked machine API (bit values match rp2, comment :21-23) |
| `tests/machine.py:606` | const | 1 | not tagged (identifier) | enum value of the faked machine API (bit values match rp2, comment :21-23) |
| `tests/machine.py:632` | param | -1 | not tagged (identifier) | "unset" sentinel of the fake Timer's period |
| `tests/machine.py:685` | param | 5000 | not tagged (fact) | real machine.WDT default timeout 5000 ms (extmod/machine_wdt.c:47); every product site passes wdt.timeout_ms |
| `tests/network.py:11` | const | 0 | not tagged (identifier) | network interface and CYW43 status codes (comment :7-9) |
| `tests/network.py:12` | const | 1 | not tagged (identifier) | network interface and CYW43 status codes (comment :7-9) |
| `tests/network.py:14` | const | 0 | not tagged (identifier) | network interface and CYW43 status codes (comment :7-9) |
| `tests/network.py:15` | const | 1 | not tagged (identifier) | network interface and CYW43 status codes (comment :7-9) |
| `tests/network.py:16` | const | 3 | not tagged (identifier) | network interface and CYW43 status codes (comment :7-9) |
| `tests/network.py:17` | const | -1 | not tagged (identifier) | network interface and CYW43 status codes (comment :7-9) |
| `tests/network.py:18` | const | -2 | not tagged (identifier) | network interface and CYW43 status codes (comment :7-9) |
| `tests/network.py:19` | const | -3 | not tagged (identifier) | network interface and CYW43 status codes (comment :7-9) |
| `tests/test_api_response.py:32` | const-c | 2 | not tagged (API domain) | restates the SampleInterv schema entry shape of asy_bmp3xx_driver.py:74 (default 2, 1-3600); API domain is untagged |
| `tests/test_api_response.py:32` | const-c | 1 | not tagged (API domain) | restates the SampleInterv schema entry shape of asy_bmp3xx_driver.py:74 (default 2, 1-3600); API domain is untagged |
| `tests/test_api_response.py:32` | const-c | 3600 | not tagged (API domain) | restates the SampleInterv schema entry shape of asy_bmp3xx_driver.py:74 (default 2, 1-3600); API domain is untagged |
| `tests/test_asy_bmp3xx_driver.py:35` | const-c | 1 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:35` | const-c | 2 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:35` | const-c | 4 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:35` | const-c | 8 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:35` | const-c | 16 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:35` | const-c | 32 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:36` | const-c | 1 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:36` | const-c | 3 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:36` | const-c | 7 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:36` | const-c | 15 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:36` | const-c | 31 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:36` | const-c | 63 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:36` | const-c | 127 | not tagged (fact) | BMP3xx oversampling / IIR coefficient settings (datasheet) |
| `tests/test_asy_bmp3xx_driver.py:122` | const | 8300000 | test input | seeded ADC values and the results computed from them |
| `tests/test_asy_bmp3xx_driver.py:123` | const | 8500000 | test input | seeded ADC values and the results computed from them |
| `tests/test_asy_bmp3xx_driver.py:124` | const | 28.460795242070162 | test input | seeded ADC values and the results computed from them |
| `tests/test_asy_bmp3xx_driver.py:125` | const | 713.765147356092 | test input | seeded ADC values and the results computed from them |
| `tests/test_asy_bmp3xx_driver.py:305` | kw | 0.01 | test input | custom setup() argument; the test checks it is stored |
| `tests/test_asy_bmp3xx_driver.py:307` | assert | 0.01 | test input | custom setup() argument; the test checks it is stored |
| `tests/test_asy_bmp3xx_driver.py:996` | const-c | 2 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:996` | const-c | 1 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:996` | const-c | 3600 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:997` | const-c | 1 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:998` | const-c | 1 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1000` | const-c | -500.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1000` | const-c | 500.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1001` | const-c | -10.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1001` | const-c | 10.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1002` | const-c | -1000.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1002` | const-c | 5000.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1003` | const-c | -50.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1003` | const-c | 15.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1003` | const-c | 50.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1010` | const-c | 1 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1010` | const-c | 3600 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1011` | const-c | -500.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1011` | const-c | 500.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1012` | const-c | -10.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1012` | const-c | 10.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1013` | const-c | -1000.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1013` | const-c | 5000.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1014` | const-c | -50.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1014` | const-c | 50.0 | not tagged (API domain) | restates the driver's REST field ranges (asy_bmp3xx_driver.py _VAL_* schema) |
| `tests/test_asy_bmp3xx_driver.py:1801` | assert | 1000 | not tagged (derived) | 1 s trigger tick (asy_bmp3xx_driver.py:290 period=1000, derived unit) |
| `tests/test_asy_bmp3xx_driver.py:1808` | call | 1 | tuned | `l1.asy_bmp3xx_driver_event_wait_s` — wait_for hang bound on an event the test sets; one value in the file |
| `tests/test_asy_bmp3xx_driver.py:1825` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_bmp3xx_driver.py:1842` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_bmp3xx_driver.py:1879` | call | 1 | tuned | `l1.asy_bmp3xx_driver_event_wait_s` — wait_for hang bound on an event the test sets; one value in the file |
| `tests/test_asy_dns_client.py:57` | param | 1 | mirror | → `udp.conn_tries_default` — the double stands in for AsyUDPSocket's constructor (comments :50-56, :546-547) |
| `tests/test_asy_dns_client.py:332` | assert | 200 | tuned | `l1.asy_dns_client_prompt_return_max_ms` — "returns promptly" budget on the real clock |
| `tests/test_asy_dns_client.py:349` | param | 2000 | tuned | `l1.asy_dns_client_fake_server_wait_ms` — fake server's deadline for the query to arrive |
| `tests/test_asy_dns_client.py:371` | call | 5 | tuned | `l1.asy_dns_client_fake_server_poll_ms` — fake server's poll step |
| `tests/test_asy_dns_client.py:389` | kw | 1000 | tuned | `l1.asy_dns_client_reply_timeout_ms` — a reply is expected within it (real loopback) |
| `tests/test_asy_dns_client.py:389` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_dns_client.py:402` | kw | 100 | tuned | `l1.asy_dns_client_no_reply_timeout_ms` — waited out in full: nobody answers |
| `tests/test_asy_dns_client.py:402` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_dns_client.py:414` | kw | 300 | tuned | `l1.asy_dns_client_bad_reply_timeout_ms` — the bad reply must land inside it for the case to be the one named |
| `tests/test_asy_dns_client.py:414` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_dns_client.py:433` | kw | 300 | tuned | `l1.asy_dns_client_bad_reply_timeout_ms` — the bad reply must land inside it for the case to be the one named |
| `tests/test_asy_dns_client.py:433` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_dns_client.py:456` | kw | 200 | tuned | `l1.asy_dns_client_fallback_timeout_ms` — per-server timeout; the fallback's reply must land inside it |
| `tests/test_asy_dns_client.py:457` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_dns_client.py:487` | kw | 200 | tuned | `l1.asy_dns_client_fallback_timeout_ms` — per-server timeout; the fallback's reply must land inside it |
| `tests/test_asy_dns_client.py:488` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_dns_client.py:509` | kw | 100 | tuned | `l1.asy_dns_client_no_reply_timeout_ms` — waited out in full: nobody answers |
| `tests/test_asy_dns_client.py:509` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_dns_client.py:527` | kw | 50 | test input | resolve_ipv4() fails before any wait (query build or socket construction raises), so the value is never waited out |
| `tests/test_asy_dns_client.py:527` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_dns_client.py:537` | kw | 50 | test input | resolve_ipv4() fails before any wait (query build or socket construction raises), so the value is never waited out |
| `tests/test_asy_dns_client.py:537` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_dns_client.py:548` | param | 1 | mirror | → `udp.conn_tries_default` — the double stands in for AsyUDPSocket's constructor (comments :50-56, :546-547) |
| `tests/test_asy_dns_client.py:562` | kw | 100 | test input | resolve_ipv4() fails before any wait (query build or socket construction raises), so the value is never waited out |
| `tests/test_asy_dns_client.py:562` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_dns_client.py:587` | kw | 1000 | tuned | `l1.asy_dns_client_reply_timeout_ms` — a reply is expected within it (real loopback) |
| `tests/test_asy_dns_client.py:587` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_dns_client.py:611` | kw | 500 | tuned | `l1.asy_dns_client_cname_reply_timeout_ms` — a CNAME+A reply is expected within it |
| `tests/test_asy_dns_client.py:611` | kw | 1 | test input | tries=1 selects the single-attempt path under test; not the product's dns.tries (the line does not name it) |
| `tests/test_asy_fram_driver.py:1090` | call | 10 | test input | lock holder's sleep, cancelled by the test before it ends (never waited out) |
| `tests/test_asy_fram_driver.py:1113` | const-c | 16 | test input | chip address regions of the hazard case |
| `tests/test_asy_fram_driver.py:1114` | const-c | 4096 | test input | chip address regions of the hazard case |
| `tests/test_asy_fram_driver.py:1114` | const-c | 16 | test input | chip address regions of the hazard case |
| `tests/test_asy_fram_driver.py:1374` | call | 1.0 | tuned | `l1.asy_fram_driver_lock_wait_s` — wait_for hang bound on a leaked lock |
| `tests/test_asy_fram_manager.py:35` | const-c | 1 | not tagged (identifier) | injected status bit no real return uses |
| `tests/test_asy_fram_manager.py:35` | const-c | 20 | not tagged (identifier) | injected status bit no real return uses |
| `tests/test_asy_fram_manager.py:751` | call | 5 | tuned | `l1.asy_fram_manager_read_wait_s` — wait_for hang bound (one literal, reported as call and kw) |
| `tests/test_asy_fram_manager.py:751` | kw | 5 | tuned | `l1.asy_fram_manager_read_wait_s` — wait_for hang bound (one literal, reported as call and kw) |
| `tests/test_asy_i2c_driver.py:719` | call | 1.0 | tuned | `l1.asy_i2c_driver_gather_wait_s` — wait_for hang bound on the concurrent workers |
| `tests/test_asy_i2c_driver.py:813` | call | 10 | test input | lock holder's sleep, cancelled by the test before it ends |
| `tests/test_asy_i2c_driver.py:843` | call | 0.2 | tuned | `l1.asy_i2c_driver_deadlock_wait_s` — wait_for bound waited out in full by the deadlock case |
| `tests/test_asy_i2c_driver.py:929` | assert | 50000 | not tagged (fact) | real machine.I2C default timeout 50 ms (ports/rp2/machine_i2c.c:38), as the comment says |
| `tests/test_asy_i2c_driver.py:933` | kw | 12345 | test input | custom timeout the test passes and reads back |
| `tests/test_asy_i2c_driver.py:934` | assert | 12345 | test input | custom timeout the test passes and reads back |
| `tests/test_asy_isl29125_driver.py:25` | const | 1 | not tagged (identifier) | ISL29125 register addresses and field bits (datasheet p9-p10) |
| `tests/test_asy_isl29125_driver.py:26` | const | 2 | not tagged (identifier) | ISL29125 register addresses and field bits (datasheet p9-p10) |
| `tests/test_asy_isl29125_driver.py:27` | const | 4 | not tagged (identifier) | ISL29125 register addresses and field bits (datasheet p9-p10) |
| `tests/test_asy_isl29125_driver.py:28` | const | 8 | not tagged (identifier) | ISL29125 register addresses and field bits (datasheet p9-p10) |
| `tests/test_asy_isl29125_driver.py:29` | const | 9 | not tagged (identifier) | ISL29125 register addresses and field bits (datasheet p9-p10) |
| `tests/test_asy_isl29125_driver.py:31` | const | 8 | not tagged (identifier) | ISL29125 register addresses and field bits (datasheet p9-p10) |
| `tests/test_asy_isl29125_driver.py:32` | const | 16 | not tagged (identifier) | ISL29125 register addresses and field bits (datasheet p9-p10) |
| `tests/test_asy_isl29125_driver.py:36` | const | 375 | not tagged (fact) | ISL29125 range full scales (datasheet p3) |
| `tests/test_asy_isl29125_driver.py:37` | const | 10000 | not tagged (fact) | ISL29125 range full scales (datasheet p3) |
| `tests/test_asy_isl29125_driver.py:38` | const | 26.666666666666668 | not tagged (derived) | 10000/375 and 2x it, as the product derives them (asy_isl29125_driver.py:95, :105) |
| `tests/test_asy_isl29125_driver.py:39` | const | 20.0 | mirror | → `isl29125.gain_ratio_min` — the product's _GAIN_RATIO_MIN plausibility band (comment :39); ID as A.U8.13 forms it |
| `tests/test_asy_isl29125_driver.py:40` | const | 34.0 | mirror | → `isl29125.gain_ratio_max` — the product's _GAIN_RATIO_MAX, as :39 |
| `tests/test_asy_isl29125_driver.py:41` | const | 53.333333333333336 | not tagged (derived) | 10000/375 and 2x it, as the product derives them (asy_isl29125_driver.py:95, :105) |
| `tests/test_asy_isl29125_driver.py:42` | const | 3 | mirror | → `isl29125.cal_converge_n` — "mirrors the driver's own const" (comment :42); ID as A.U8.13 forms it |
| `tests/test_asy_isl29125_driver.py:647` | assert | 303 | not tagged (fact) | 3 x tINT (datasheet p3, p6) |
| `tests/test_asy_isl29125_driver.py:649` | assert | 19 | not tagged (fact) | 3 x tINT (datasheet p3, p6) |
| `tests/test_asy_isl29125_driver.py:661` | deadline | 500 | test input | synthetic settle deadline set by the test; no real wait follows |
| `tests/test_asy_isl29125_driver.py:662` | assert | 500 | test input | synthetic settle deadline set by the test; no real wait follows |
| `tests/test_asy_isl29125_driver.py:1301` | deadline | 500 | test input | settle deadline set inside a patched sleep_ms (`:1304`) |
| `tests/test_asy_isl29125_driver.py:1306` | deadline | 500 | test input | settle deadline set inside a patched sleep_ms (`:1304`) |
| `tests/test_asy_isl29125_driver.py:1384` | deadline | 500 | test input | synthetic settle deadline set by the test; no real wait follows |
| `tests/test_asy_isl29125_driver.py:2056` | assert | 30.0 | test input | the value the test itself pushed |
| `tests/test_asy_isl29125_driver.py:2378` | assert | 1000 | not tagged (derived) | 1 s trigger tick (asy_isl29125_driver.py:850 period=1000) |
| `tests/test_asy_isl29125_driver.py:2666` | assert | 300.0 | test input | the value the test itself pushed |
| `tests/test_asy_isl29125_driver.py:2830` | assert | 10.0 | test input | the value the test itself pushed |
| `tests/test_asy_isl29125_driver.py:3018` | deadline | 10000 | test input | synthetic settle deadline set by the test; no real wait follows |
| `tests/test_asy_neopixel_driver.py:88` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — real sleep for the overlay task to commit an on/off write (C.0.2's own example, :88) |
| `tests/test_asy_neopixel_driver.py:101` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — real sleep for the overlay task to commit an on/off write (C.0.2's own example, :88) |
| `tests/test_asy_neopixel_driver.py:103` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — real sleep for the overlay task to commit an on/off write (C.0.2's own example, :88) |
| `tests/test_asy_neopixel_driver.py:116` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — real sleep for the overlay task to commit an on/off write (C.0.2's own example, :88) |
| `tests/test_asy_neopixel_driver.py:130` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — real sleep for the overlay task to commit an on/off write (C.0.2's own example, :88) |
| `tests/test_asy_neopixel_driver.py:132` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — real sleep for the overlay task to commit an on/off write (C.0.2's own example, :88) |
| `tests/test_asy_neopixel_driver.py:146` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — real sleep for the overlay task to commit an on/off write (C.0.2's own example, :88) |
| `tests/test_asy_neopixel_driver.py:149` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — real sleep for the overlay task to commit an on/off write (C.0.2's own example, :88) |
| `tests/test_asy_neopixel_driver.py:167` | call | 0.02 | tuned | `l1.asy_neopixel_driver_mid_ramp_s` — real sleep to land mid-ramp |
| `tests/test_asy_neopixel_driver.py:172` | call | 0.2 | tuned | `l1.asy_neopixel_driver_ramp_and_restore_s` — ramp end plus the overlay restore |
| `tests/test_asy_neopixel_driver.py:191` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:206` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — real sleep for the overlay task to commit an on/off write (C.0.2's own example, :88) |
| `tests/test_asy_neopixel_driver.py:208` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:222` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:238` | call | 0.3 | tuned | `l1.asy_neopixel_driver_queued_signals_done_s` — every queued ramp finished, plus margin |
| `tests/test_asy_neopixel_driver.py:259` | call | 0.3 | tuned | `l1.asy_neopixel_driver_queued_signals_done_s` — every queued ramp finished, plus margin |
| `tests/test_asy_neopixel_driver.py:272` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:290` | call | 1.5 | tuned | `l1.asy_neopixel_driver_low_freq_signal_done_s` — freq=1: one 1 s step plus margin |
| `tests/test_asy_neopixel_driver.py:305` | call | 1.1 | tuned | `l1.asy_neopixel_driver_one_s_signal_done_s` — a 1.0 s signal plus margin |
| `tests/test_asy_neopixel_driver.py:325` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:361` | call | 0.02 | tuned | `l1.asy_neopixel_driver_mid_ramp_s` — real sleep to land mid-ramp |
| `tests/test_asy_neopixel_driver.py:366` | call | 0.6 | tuned | `l1.asy_neopixel_driver_long_and_short_ramp_done_s` — a 0.3 s and a 0.1 s ramp finished |
| `tests/test_asy_neopixel_driver.py:380` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:395` | call | 1.6 | tuned | `l1.asy_neopixel_driver_long_signal_done_s` — a 1.5 s signal plus margin |
| `tests/test_asy_neopixel_driver.py:416` | call | 0.3 | tuned | `l1.asy_neopixel_driver_queued_signals_done_s` — every queued ramp finished, plus margin |
| `tests/test_asy_neopixel_driver.py:434` | call | 0.02 | tuned | `l1.asy_neopixel_driver_mid_ramp_s` — real sleep to land mid-ramp |
| `tests/test_asy_neopixel_driver.py:437` | call | 0.02 | tuned | `l1.asy_neopixel_driver_mid_ramp_s` — real sleep to land mid-ramp |
| `tests/test_asy_neopixel_driver.py:439` | call | 0.3 | tuned | `l1.asy_neopixel_driver_queued_signals_done_s` — every queued ramp finished, plus margin |
| `tests/test_asy_neopixel_driver.py:520` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:556` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:579` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:594` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:609` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:626` | call | 0.15 | tuned | `l1.asy_neopixel_driver_signal_done_s` — one 0.1 s signal (the led.min_signal_s floor) plus margin |
| `tests/test_asy_neopixel_driver.py:641` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — real sleep for the overlay task to commit an on/off write (C.0.2's own example, :88) |
| `tests/test_asy_notification_service.py:138` | param | 0.1 | tuned | `l1.asy_notification_service_cycle_wait_s` — real time for one monitor pass with no flash (the _one_cycle() default and two direct sleeps) |
| `tests/test_asy_notification_service.py:281` | const-c | 23 | not tagged (API domain) | restates the coordinator's REST field ranges (OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur) |
| `tests/test_asy_notification_service.py:282` | const-c | 59 | not tagged (API domain) | restates the coordinator's REST field ranges (OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur) |
| `tests/test_asy_notification_service.py:283` | const-c | 23 | not tagged (API domain) | restates the coordinator's REST field ranges (OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur) |
| `tests/test_asy_notification_service.py:284` | const-c | 59 | not tagged (API domain) | restates the coordinator's REST field ranges (OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur) |
| `tests/test_asy_notification_service.py:285` | const-c | 1 | not tagged (API domain) | restates the coordinator's REST field ranges (OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur) |
| `tests/test_asy_notification_service.py:285` | const-c | 255 | not tagged (API domain) | restates the coordinator's REST field ranges (OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur) |
| `tests/test_asy_notification_service.py:286` | const-c | 60.0 | not tagged (API domain) | restates the coordinator's REST field ranges (OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur) |
| `tests/test_asy_notification_service.py:286` | const-c | 3600.0 | not tagged (API domain) | restates the coordinator's REST field ranges (OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur) |
| `tests/test_asy_notification_service.py:287` | const-c | 0.5 | not tagged (API domain) | restates the coordinator's REST field ranges (OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur) |
| `tests/test_asy_notification_service.py:287` | const-c | 10.0 | not tagged (API domain) | restates the coordinator's REST field ranges (OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur) |
| `tests/test_asy_notification_service.py:912` | kw | 3.5 | tuned | `l1.asy_notification_service_three_flash_cycle_s` — three flashes' settle (3.0 s) plus margin (comment :908-909) |
| `tests/test_asy_notification_service.py:933` | kw | 1.2 | tuned | `l1.asy_notification_service_one_flash_cycle_s` — one flash's 2 x FlashDur settle (1.0 s) plus margin |
| `tests/test_asy_notification_service.py:958` | kw | 1.2 | tuned | `l1.asy_notification_service_one_flash_cycle_s` — one flash's 2 x FlashDur settle (1.0 s) plus margin |
| `tests/test_asy_notification_service.py:982` | kw | 3.5 | tuned | `l1.asy_notification_service_three_flash_cycle_s` — three flashes' settle (3.0 s) plus margin (comment :908-909) |
| `tests/test_asy_notification_service.py:1005` | call | 0.05 | tuned | `l1.asy_notification_service_task_start_settle_s` — real sleep for a started task to reach its first iteration |
| `tests/test_asy_notification_service.py:1008` | call | 1.3 | tuned | `l1.asy_notification_service_one_flash_settle_s` — first flash's 1.0 s settle plus margin |
| `tests/test_asy_notification_service.py:1147` | call | 0.05 | tuned | `l1.asy_notification_service_task_start_settle_s` — real sleep for a started task to reach its first iteration |
| `tests/test_asy_notification_service.py:1153` | call | 1.1 | tuned | `l1.asy_notification_service_override_tick_s` — one 1 s override decrement plus margin; Dependant of notify.loop_tick_s |
| `tests/test_asy_notification_service.py:1155` | call | 1.1 | tuned | `l1.asy_notification_service_override_tick_s` — one 1 s override decrement plus margin; Dependant of notify.loop_tick_s |
| `tests/test_asy_notification_service.py:1184` | call | 0.05 | tuned | `l1.asy_notification_service_task_start_settle_s` — real sleep for a started task to reach its first iteration |
| `tests/test_asy_notification_service.py:1186` | call | 1.1 | tuned | `l1.asy_notification_service_override_tick_s` — one 1 s override decrement plus margin; Dependant of notify.loop_tick_s |
| `tests/test_asy_notification_service.py:1192` | call | 0.05 | tuned | `l1.asy_notification_service_task_start_settle_s` — real sleep for a started task to reach its first iteration |
| `tests/test_asy_notification_service.py:1245` | call | 0.1 | tuned | `l1.asy_notification_service_cycle_wait_s` — real time for one monitor pass with no flash (the _one_cycle() default and two direct sleeps) |
| `tests/test_asy_notification_service.py:1266` | call | 50 | tuned | `l1.asy_notification_service_elapsed_stimulus_ms` — real elapsed time the assertion's 1 s band is computed around |
| `tests/test_asy_notification_service.py:1296` | call | 0.1 | tuned | `l1.asy_notification_service_cycle_wait_s` — real time for one monitor pass with no flash (the _one_cycle() default and two direct sleeps) |
| `tests/test_asy_notification_service.py:1322` | kw | 2.5 | tuned | `l1.asy_notification_service_two_flash_cycle_s` — two flashes' settle (2.0 s) plus margin |
| `tests/test_asy_ntp_client.py:53` | const-c | 3 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:53` | const-c | 1024 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:54` | const-c | -43200 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:54` | const-c | 43200 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:55` | const-c | 12 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:55` | const-c | 1 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:55` | const-c | 24 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:56` | const-c | -43200 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:56` | const-c | 3600 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:56` | const-c | 43200 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:57` | const-c | -43200 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:57` | const-c | 3600 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:57` | const-c | 43200 | not tagged (API domain) | restates asy_ntp_client.py's _VAL_* REST schema (comment :50-52); API domain is untagged |
| `tests/test_asy_ntp_client.py:73` | param | 500 | mirror | → `dns.timeout_ms` — make_client()'s default restates the product parameter dns_timeout_ms it forwards (`:95`) |
| `tests/test_asy_ntp_client.py:74` | param | 1 | mirror | → `dns.tries` — as :73, dns_tries |
| `tests/test_asy_ntp_client.py:75` | param | 5000 | mirror | → `ntp.fetch_timeout_ms` — as :73, ntp_fetch_timeout_ms |
| `tests/test_asy_ntp_client.py:76` | param | 10 | mirror | → `ntp.retry_s_default` — as :73, retry_s |
| `tests/test_asy_ntp_client.py:77` | param | 600 | mirror | → `ntp.retry_max_s_default` — as :73, retry_max_s |
| `tests/test_asy_ntp_client.py:517` | assert | 10 | mirror | → `ntp.check_interval_s` — "_NTP_CHECK_INTERV: const(), compiled away, hardcoded" (A.U8.09 names this site); 1000 is the s-to-ms scale |
| `tests/test_asy_ntp_client.py:517` | assert | 1000 | mirror | → `ntp.check_interval_s` — "_NTP_CHECK_INTERV: const(), compiled away, hardcoded" (A.U8.09 names this site); 1000 is the s-to-ms scale |
| `tests/test_asy_ntp_client.py:527` | call | 0.2 | tuned | `l1.asy_ntp_client_event_wait_s` — wait_for hang bound on an event or task the test drives (one value in the file) |
| `tests/test_asy_ntp_client.py:541` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_ntp_client.py:552` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_ntp_client.py:566` | assert | 1000 | not tagged (derived) | 1 s counter tick |
| `tests/test_asy_ntp_client.py:573` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_ntp_client.py:582` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_ntp_client.py:607` | call | 0.2 | tuned | `l1.asy_ntp_client_event_wait_s` — wait_for hang bound on an event or task the test drives (one value in the file) |
| `tests/test_asy_ntp_client.py:618` | kw | 5000 | test input | period given to a fake Timer the test then checks is deinit'ed |
| `tests/test_asy_ntp_client.py:808` | kw | 1234 | test input | custom values whose forwarding the test checks |
| `tests/test_asy_ntp_client.py:808` | kw | 3 | test input | custom values whose forwarding the test checks |
| `tests/test_asy_ntp_client.py:871` | param | 1 | mirror | → `udp.conn_tries_default` — the double stands in for AsyUDPSocket's constructor (comments :866-868, :2059-2061) |
| `tests/test_asy_ntp_client.py:876` | param | -1 | not tagged (identifier) | "no timeout" sentinel, as AsyUDPSocket's own |
| `tests/test_asy_ntp_client.py:876` | param | 1 | mirror | → `udp.round_trip_tries_default` — "keep AsyUDPSocket's own parameter order/positions" (comment :874) |
| `tests/test_asy_ntp_client.py:886` | kw | 9999 | test input | custom value whose forwarding the test checks |
| `tests/test_asy_ntp_client.py:936` | call | 10 | tuned | `l1.asy_ntp_client_fake_server_poll_ms` — fake NTP server's poll step (two server classes) |
| `tests/test_asy_ntp_client.py:940` | call | 10 | tuned | `l1.asy_ntp_client_fake_server_poll_ms` — fake NTP server's poll step (two server classes) |
| `tests/test_asy_ntp_client.py:965` | const | 2208988800 | not tagged (fact) | NTP-to-Unix epoch offset (RFC 5905) |
| `tests/test_asy_ntp_client.py:999` | assert | 3600 | test input | offset the test passed (`:997`) |
| `tests/test_asy_ntp_client.py:1166` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_ntp_client.py:1175` | assert | 15 | mirror | → `ntp.retry_interval_s` — "_NTP_RETRY_INTERV: const(), compiled away" (A.U8.09 names this site); 1000 is the s-to-ms scale |
| `tests/test_asy_ntp_client.py:1175` | assert | 1000 | mirror | → `ntp.retry_interval_s` — "_NTP_RETRY_INTERV: const(), compiled away" (A.U8.09 names this site); 1000 is the s-to-ms scale |
| `tests/test_asy_ntp_client.py:1186` | call | 0.2 | tuned | `l1.asy_ntp_client_event_wait_s` — wait_for hang bound on an event or task the test drives (one value in the file) |
| `tests/test_asy_ntp_client.py:1201` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_ntp_client.py:1236` | kw | 5000 | test input | period given to a fake Timer the test then checks is deinit'ed |
| `tests/test_asy_ntp_client.py:1275` | call | 0.2 | tuned | `l1.asy_ntp_client_event_wait_s` — wait_for hang bound on an event or task the test drives (one value in the file) |
| `tests/test_asy_ntp_client.py:1296` | call | 0.05 | tuned | `l1.asy_ntp_client_fired_probe_s` — wait_for window that decides fired / not fired; waited out in full in the not-fired case |
| `tests/test_asy_ntp_client.py:1326` | call | 0.2 | tuned | `l1.asy_ntp_client_event_wait_s` — wait_for hang bound on an event or task the test drives (one value in the file) |
| `tests/test_asy_ntp_client.py:1350` | call | 0.2 | tuned | `l1.asy_ntp_client_event_wait_s` — wait_for hang bound on an event or task the test drives (one value in the file) |
| `tests/test_asy_ntp_client.py:1429` | assert | 9 | not tagged (fact) | length of MicroPython's gmtime() tuple |
| `tests/test_asy_ntp_client.py:1844` | call | 0.2 | tuned | `l1.asy_ntp_client_event_wait_s` — wait_for hang bound on an event or task the test drives (one value in the file) |
| `tests/test_asy_ntp_client.py:1932` | kw | 10 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1932` | kw | 70 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1946` | kw | 10 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1946` | kw | 600 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1953` | assert | 10 | test input | expected backoff step computed from the case's retry_s |
| `tests/test_asy_ntp_client.py:1959` | kw | 10 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1959` | kw | 600 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1967` | assert | 10 | test input | expected backoff step computed from the case's retry_s |
| `tests/test_asy_ntp_client.py:1971` | kw | 10 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1971` | kw | 600 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1981` | kw | 10 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1981` | kw | 600 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1988` | kw | 3 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1988` | kw | 5 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1990` | kw | 40 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:1990` | kw | 20 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:2072` | param | 1 | mirror | → `udp.conn_tries_default` — the double stands in for AsyUDPSocket's constructor (comments :866-868, :2059-2061) |
| `tests/test_asy_ntp_client.py:2113` | call | 10 | tuned | `l1.asy_ntp_client_fake_server_poll_ms` — fake NTP server's poll step (two server classes) |
| `tests/test_asy_ntp_client.py:2118` | call | 10 | tuned | `l1.asy_ntp_client_fake_server_poll_ms` — fake NTP server's poll step (two server classes) |
| `tests/test_asy_ntp_client.py:2140` | call | 5 | tuned | `l1.asy_ntp_client_serve_wait_s` — wait_for hang bound on the fake server's one exchange |
| `tests/test_asy_ntp_client.py:2144` | call | 20 | tuned | `l1.asy_ntp_client_state_poll_ms` — poll step of a wait for synced / retry-armed state |
| `tests/test_asy_ntp_client.py:2167` | call | 1 | tuned | `l1.asy_ntp_client_no_answer_wait_s` — real wait before reading "not synced"; its comment names _NTP_CONN_TIMEOUT, but the fetch timeout is 5 s (ntp.fetch_timeout_ms), longer than this wait; the not-synced verdict holds at any point in it |
| `tests/test_asy_ntp_client.py:2190` | call | 5 | tuned | `l1.asy_ntp_client_serve_wait_s` — wait_for hang bound on the fake server's one exchange |
| `tests/test_asy_ntp_client.py:2191` | call | 0.2 | tuned | `l1.asy_ntp_client_reply_process_s` — real wait for the client to process the served garbage reply |
| `tests/test_asy_ntp_client.py:2219` | call | 20 | tuned | `l1.asy_ntp_client_state_poll_ms` — poll step of a wait for synced / retry-armed state |
| `tests/test_asy_ntp_client.py:2228` | call | 5 | tuned | `l1.asy_ntp_client_serve_wait_s` — wait_for hang bound on the fake server's one exchange |
| `tests/test_asy_ntp_client.py:2237` | call | 20 | tuned | `l1.asy_ntp_client_state_poll_ms` — poll step of a wait for synced / retry-armed state |
| `tests/test_asy_ntp_client.py:2242` | call | 5 | tuned | `l1.asy_ntp_client_serve_wait_s` — wait_for hang bound on the fake server's one exchange |
| `tests/test_asy_ntp_client.py:2366` | kw | 100 | tuned | `l1.asy_ntp_client_no_reply_fetch_timeout_ms` — short fetch timeout waited out by the no-reply cases; also replaces the literal of `:2475` (not a search hit) |
| `tests/test_asy_ntp_client.py:2420` | kw | 10 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:2420` | kw | 600 | test input | backoff pair chosen for the case; the arithmetic is driven by sleep(0) pumps (_drive_attempts, `:1900-1913`), never waited out |
| `tests/test_asy_ntp_client.py:2446` | call | 0.05 | tuned | `l1.asy_ntp_client_fired_probe_s` — wait_for window that decides fired / not fired; waited out in full in the not-fired case |
| `tests/test_asy_ntp_client.py:2487` | call | 5 | tuned | `l1.asy_ntp_client_serve_wait_s` — wait_for hang bound on the fake server's one exchange |
| `tests/test_asy_ntp_client.py:2488` | call | 200 | tuned | `l1.asy_ntp_client_past_fetch_timeout_ms` — "past the 100ms fetch timeout either way"; Dependant of l1.asy_ntp_client_no_reply_fetch_timeout_ms |
| `tests/test_asy_ntp_client.py:2519` | call | 5 | tuned | `l1.asy_ntp_client_serve_wait_s` — wait_for hang bound on the fake server's one exchange |
| `tests/test_asy_scd30_driver.py:652` | assert | 500 | mirror | → `scd30.start_trigger_period_ms` — asserts the product object's timer period (asy_scd30_driver.py:215 period=500, tagged in A.U8.07) |
| `tests/test_asy_scd30_driver.py:660` | call | 1 | tuned | `l1.asy_scd30_driver_event_wait_s` — wait_for hang bound on an event the test fires (one value in the file) |
| `tests/test_asy_scd30_driver.py:661` | call | 1 | tuned | `l1.asy_scd30_driver_event_wait_s` — wait_for hang bound on an event the test fires (one value in the file) |
| `tests/test_asy_scd30_driver.py:675` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_scd30_driver.py:689` | call | 1 | tuned | `l1.asy_scd30_driver_event_wait_s` — wait_for hang bound on an event the test fires (one value in the file) |
| `tests/test_asy_scd30_driver.py:703` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_scd30_driver.py:745` | call | 1 | tuned | `l1.asy_scd30_driver_event_wait_s` — wait_for hang bound on an event the test fires (one value in the file) |
| `tests/test_asy_sgp40_driver.py:47` | const | 49 | not tagged (fact) | SGP40 CRC polynomial (datasheet Table 7) |
| `tests/test_asy_sgp40_driver.py:335` | assert | 1 | test input | number of processed samples the case drives |
| `tests/test_asy_sgp40_driver.py:335` | assert | 65536 | not tagged (fact) | Q16 fixed-point scale of the VOC algorithm's muptime (voc_algorithm.py _f16) |
| `tests/test_asy_sgp40_driver.py:539` | call | 1 | tuned | `l1.asy_sgp40_driver_event_wait_s` — wait_for hang bound on an event the fake timer sets |
| `tests/test_asy_sgp40_driver.py:568` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_sgp40_driver.py:579` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_sgp40_driver.py:742` | assert | 1 | test input | number of processed samples the case drives |
| `tests/test_asy_sgp40_driver.py:742` | assert | 65536 | not tagged (fact) | Q16 fixed-point scale of the VOC algorithm's muptime (voc_algorithm.py _f16) |
| `tests/test_asy_sgp40_driver.py:780` | assert | 1 | test input | number of processed samples the case drives |
| `tests/test_asy_sgp40_driver.py:780` | assert | 65536 | not tagged (fact) | Q16 fixed-point scale of the VOC algorithm's muptime (voc_algorithm.py _f16) |
| `tests/test_asy_sgp40_driver.py:788` | assert | 2 | test input | number of processed samples the case drives |
| `tests/test_asy_sgp40_driver.py:788` | assert | 65536 | not tagged (fact) | Q16 fixed-point scale of the VOC algorithm's muptime (voc_algorithm.py _f16) |
| `tests/test_asy_sgp40_driver.py:796` | assert | 3 | test input | number of processed samples the case drives |
| `tests/test_asy_sgp40_driver.py:796` | assert | 65536 | not tagged (fact) | Q16 fixed-point scale of the VOC algorithm's muptime (voc_algorithm.py _f16) |
| `tests/test_asy_sgp40_driver.py:1250` | assert | 45 | not tagged (fact) | the algorithm's 45 s initial blackout (voc_algorithm.py:15, Sensirion constant) |
| `tests/test_asy_sgp40_driver.py:1250` | assert | 65536 | not tagged (fact) | Q16 fixed-point scale of the VOC algorithm's muptime (voc_algorithm.py _f16) |
| `tests/test_asy_sgp40_driver.py:1280` | const-c | 1 | not tagged (API domain) | restates asy_sgp40_driver.py's _VAL_BP/_VAL_BMAX/_VAL_WT REST schema (comment :1277-1279) |
| `tests/test_asy_sgp40_driver.py:1280` | const-c | 1440 | not tagged (API domain) | restates asy_sgp40_driver.py's _VAL_BP/_VAL_BMAX/_VAL_WT REST schema (comment :1277-1279) |
| `tests/test_asy_sgp40_driver.py:1281` | const-c | 7200 | not tagged (API domain) | restates asy_sgp40_driver.py's _VAL_BP/_VAL_BMAX/_VAL_WT REST schema (comment :1277-1279) |
| `tests/test_asy_sgp40_driver.py:1281` | const-c | 10080 | not tagged (API domain) | restates asy_sgp40_driver.py's _VAL_BP/_VAL_BMAX/_VAL_WT REST schema (comment :1277-1279) |
| `tests/test_asy_sgp40_driver.py:1282` | const-c | 30 | not tagged (API domain) | restates asy_sgp40_driver.py's _VAL_BP/_VAL_BMAX/_VAL_WT REST schema (comment :1277-1279) |
| `tests/test_asy_sgp40_driver.py:1282` | const-c | 600 | not tagged (API domain) | restates asy_sgp40_driver.py's _VAL_BP/_VAL_BMAX/_VAL_WT REST schema (comment :1277-1279) |
| `tests/test_asy_sgp40_driver.py:1637` | assert | 45 | not tagged (fact) | the algorithm's 45 s initial blackout (voc_algorithm.py:15, Sensirion constant) |
| `tests/test_asy_sgp40_driver.py:1637` | assert | 65536 | not tagged (fact) | Q16 fixed-point scale of the VOC algorithm's muptime (voc_algorithm.py _f16) |
| `tests/test_asy_sgp40_driver.py:2330` | param | 10 | test input | the fake's copy of _read_word_from_command()'s untagged delay_ms default (A.U8.07: not tagged); never waited (the fake returns or delegates) |
| `tests/test_asy_spi_driver.py:404` | call | 10 | test input | lock holder's sleep, cancelled by the test before it ends |
| `tests/test_asy_spi_driver.py:655` | call | 1.0 | tuned | `l1.asy_i2c_driver_gather_wait_s` — same test as test_asy_i2c_driver.py:719 (shared ID, further site) |
| `tests/test_asy_spi_driver.py:804` | call | 10 | test input | lock holder's sleep, cancelled by the test before it ends |
| `tests/test_asy_spi_driver.py:831` | call | 0.2 | tuned | `l1.asy_i2c_driver_deadlock_wait_s` — same test as test_asy_i2c_driver.py:843 (shared ID, further site) |
| `tests/test_asy_uart_comm.py:36` | const | 0 | not tagged (identifier) | frame-header field indices (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:38` | const | 2 | not tagged (identifier) | frame-header field indices (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:39` | const | 3 | not tagged (identifier) | frame-header field indices (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:40` | const | 4 | not tagged (identifier) | frame-header field indices (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:41` | const | 5 | not tagged (identifier) | frame-header field indices (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:57` | kw | 1 | tuned | `l1.uart_comm_harness_poll_wait_ms` — the same test-driver poll step the harness defines: import it instead of restating 1 |
| `tests/test_asy_uart_comm.py:82` | kw | 1 | tuned | `l1.uart_comm_harness_poll_wait_ms` — the same test-driver poll step the harness defines: import it instead of restating 1 |
| `tests/test_asy_uart_comm.py:108` | kw | 10 | test input | construction-time floor case: the refusal is computed from these, nothing is waited |
| `tests/test_asy_uart_comm.py:110` | kw | 30 | test input | construction-time floor case: the refusal is computed from these, nothing is waited |
| `tests/test_asy_uart_comm.py:111` | kw | 200 | test input | construction-time floor case: the refusal is computed from these, nothing is waited |
| `tests/test_asy_uart_comm.py:119` | kw | 2 | test input | construction-time floor case: the refusal is computed from these, nothing is waited |
| `tests/test_asy_uart_comm.py:123` | kw | 1000 | test input | construction-time floor case: the refusal is computed from these, nothing is waited |
| `tests/test_asy_uart_comm.py:124` | kw | 1000 | test input | construction-time floor case: the refusal is computed from these, nothing is waited |
| `tests/test_asy_uart_comm.py:145` | kw | 1 | tuned | `l1.uart_comm_harness_poll_wait_ms` — the same test-driver poll step the harness defines: import it instead of restating 1 |
| `tests/test_asy_uart_comm.py:156` | kw | 1 | tuned | `l1.uart_comm_harness_poll_wait_ms` — the same test-driver poll step the harness defines: import it instead of restating 1 |
| `tests/test_asy_uart_comm.py:160` | kw | 1 | tuned | `l1.uart_comm_harness_poll_wait_ms` — the same test-driver poll step the harness defines: import it instead of restating 1 |
| `tests/test_asy_uart_comm.py:168` | kw | 20 | test input | construction-time floor case: the refusal is computed from these, nothing is waited |
| `tests/test_asy_uart_comm.py:177` | kw | 1 | tuned | `l1.uart_comm_harness_poll_wait_ms` — the same test-driver poll step the harness defines: import it instead of restating 1 |
| `tests/test_asy_uart_comm.py:183` | kw | 1 | tuned | `l1.uart_comm_harness_poll_wait_ms` — the same test-driver poll step the harness defines: import it instead of restating 1 |
| `tests/test_asy_uart_comm.py:267` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:269` | kw | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — hang bound, value 10 (limit= and wait_for share it: one constant per value) |
| `tests/test_asy_uart_comm.py:272` | kw | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — hang bound, value 10 (limit= and wait_for share it: one constant per value) |
| `tests/test_asy_uart_comm.py:445` | call | 20 | tuned | `l1.asy_uart_comm_loop_survival_wait_ms` — real wait before checking the listen loop survived its callback's raise |
| `tests/test_asy_uart_comm.py:450` | kw | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — hang bound, value 10 (limit= and wait_for share it: one constant per value) |
| `tests/test_asy_uart_comm.py:683` | kw | 15 | tuned | `l1.asy_uart_comm_silent_bound_s` — hang bound, value 15 (silent peer, cancel, refusal cases) |
| `tests/test_asy_uart_comm.py:691` | kw | 15 | tuned | `l1.asy_uart_comm_silent_bound_s` — hang bound, value 15 (silent peer, cancel, refusal cases) |
| `tests/test_asy_uart_comm.py:719` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:721` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:736` | call | 5 | tuned | `l1.asy_uart_comm_short_bound_s` — hang bound, value 5 (write gate, listener) |
| `tests/test_asy_uart_comm.py:744` | assert | 150 | test input | timeout given to construction and the 1.5 x window computed from it (the _RESYNC_NUM/DEN contract); never waited |
| `tests/test_asy_uart_comm.py:744` | kw | 100 | test input | timeout given to construction and the 1.5 x window computed from it (the _RESYNC_NUM/DEN contract); never waited |
| `tests/test_asy_uart_comm.py:745` | assert | 600 | test input | timeout given to construction and the 1.5 x window computed from it (the _RESYNC_NUM/DEN contract); never waited |
| `tests/test_asy_uart_comm.py:745` | kw | 400 | test input | timeout given to construction and the 1.5 x window computed from it (the _RESYNC_NUM/DEN contract); never waited |
| `tests/test_asy_uart_comm.py:756` | call | 2 | tuned | `l1.asy_uart_comm_past_deadline_bound_s` — hang bound on a gate whose deadline is already past |
| `tests/test_asy_uart_comm.py:777` | kw | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — hang bound, value 10 (limit= and wait_for share it: one constant per value) |
| `tests/test_asy_uart_comm.py:787` | call | 1 | tuned | `l1.asy_uart_comm_flood_step_ms` — pace of the babbling-peer flood the drain bound is tested against |
| `tests/test_asy_uart_comm.py:793` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:798` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:809` | call | 1 | tuned | `l1.asy_uart_comm_flood_step_ms` — pace of the babbling-peer flood the drain bound is tested against |
| `tests/test_asy_uart_comm.py:815` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:820` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:833` | kw | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — hang bound, value 10 (limit= and wait_for share it: one constant per value) |
| `tests/test_asy_uart_comm.py:845` | call | 1 | tuned | `l1.asy_uart_comm_flood_step_ms` — pace of the babbling-peer flood the drain bound is tested against |
| `tests/test_asy_uart_comm.py:850` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:855` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:871` | kw | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — hang bound, value 10 (limit= and wait_for share it: one constant per value) |
| `tests/test_asy_uart_comm.py:886` | kw | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — hang bound, value 10 (limit= and wait_for share it: one constant per value) |
| `tests/test_asy_uart_comm.py:894` | kw | 15 | tuned | `l1.asy_uart_comm_silent_bound_s` — hang bound, value 15 (silent peer, cancel, refusal cases) |
| `tests/test_asy_uart_comm.py:895` | kw | 15 | tuned | `l1.asy_uart_comm_silent_bound_s` — hang bound, value 15 (silent peer, cancel, refusal cases) |
| `tests/test_asy_uart_comm.py:896` | kw | 15 | tuned | `l1.asy_uart_comm_silent_bound_s` — hang bound, value 15 (silent peer, cancel, refusal cases) |
| `tests/test_asy_uart_comm.py:897` | kw | 15 | tuned | `l1.asy_uart_comm_silent_bound_s` — hang bound, value 15 (silent peer, cancel, refusal cases) |
| `tests/test_asy_uart_comm.py:915` | call | 10 | tuned | `l1.asy_uart_comm_listener_park_ms` — real wait for the listener to park in its read holding the lock |
| `tests/test_asy_uart_comm.py:916` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:919` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:926` | kw | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — hang bound, value 10 (limit= and wait_for share it: one constant per value) |
| `tests/test_asy_uart_comm.py:945` | call | 5 | tuned | `l1.asy_uart_comm_inside_lock_ms` — real wait for the other task to be inside the locked region |
| `tests/test_asy_uart_comm.py:949` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:952` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1004` | kw | 15 | tuned | `l1.asy_uart_comm_silent_bound_s` — hang bound, value 15 (silent peer, cancel, refusal cases) |
| `tests/test_asy_uart_comm.py:1015` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1033` | call | 5 | tuned | `l1.asy_uart_comm_short_bound_s` — hang bound, value 5 (write gate, listener) |
| `tests/test_asy_uart_comm.py:1037` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1052` | call | 8 | tuned | `l1.asy_uart_comm_listener_short_bound_s` — hang bound, value 8, on the listener |
| `tests/test_asy_uart_comm.py:1055` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1106` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:1108` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1126` | call | 1 | tuned | `l1.asy_uart_comm_async_callback_yield_ms` — real suspension inside the async callback |
| `tests/test_asy_uart_comm.py:1158` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:1161` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1173` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:1176` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1196` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:1199` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1252` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1284` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:1286` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1312` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1321` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1330` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1349` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1373` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1375` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1434` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1465` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1481` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1482` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1486` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1488` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1503` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1536` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1562` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1624` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1637` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1645` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:1651` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:1653` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1661` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:1667` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:1669` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1680` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:1686` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:1689` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1725` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:1729` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1751` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:1758` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:1760` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1770` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:1780` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1836` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:1839` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1854` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:1857` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1871` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:1877` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:1880` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1897` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:1903` | call | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — as above |
| `tests/test_asy_uart_comm.py:1906` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:1933` | kw | 1 | test input | internal call on a missing buffer; returns before any wait |
| `tests/test_asy_uart_comm.py:1937` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:1961` | call | 5 | tuned | `l1.asy_uart_comm_inside_lock_ms` — real wait for the other task to be inside the locked region |
| `tests/test_asy_uart_comm.py:1977` | kw | 15 | tuned | `l1.asy_uart_comm_silent_bound_s` — hang bound, value 15 (silent peer, cancel, refusal cases) |
| `tests/test_asy_uart_comm.py:1987` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:1990` | kw | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — hang bound, value 10 (limit= and wait_for share it: one constant per value) |
| `tests/test_asy_uart_comm.py:1994` | kw | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — hang bound, value 10 (limit= and wait_for share it: one constant per value) |
| `tests/test_asy_uart_comm.py:1997` | kw | 10 | tuned | `l1.asy_uart_comm_step_bound_s` — hang bound, value 10 (limit= and wait_for share it: one constant per value) |
| `tests/test_asy_uart_comm.py:2018` | kw | 30 | tuned | `l1.asy_uart_comm_short_reply_timeout_ms` — protocol timeout of the pair in the fast-failure cases; waited out in full on the real clock |
| `tests/test_asy_uart_comm.py:2032` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:2043` | const | 32 | not tagged (identifier) | legacy BSEC command ids (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:2044` | const | 33 | not tagged (identifier) | legacy BSEC command ids (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:2045` | const | 34 | not tagged (identifier) | legacy BSEC command ids (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:2046` | const | 48 | not tagged (identifier) | legacy BSEC command ids (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:2047` | const | 49 | not tagged (identifier) | legacy BSEC command ids (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:2048` | const | 50 | not tagged (identifier) | legacy BSEC command ids (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:2049` | const | 51 | not tagged (identifier) | legacy BSEC command ids (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:2050` | const | 52 | not tagged (identifier) | legacy BSEC command ids (C.0.2's own example) |
| `tests/test_asy_uart_comm.py:2051` | const | 13 | not tagged (contract) | legacy BSEC link layout the conformance case restates (dev_legacy, comment :2039-2041) |
| `tests/test_asy_uart_comm.py:2052` | const | 221 | not tagged (contract) | legacy BSEC link layout the conformance case restates (dev_legacy, comment :2039-2041) |
| `tests/test_asy_uart_comm.py:2053` | const | 20 | not tagged (contract) | legacy BSEC link layout the conformance case restates (dev_legacy, comment :2039-2041) |
| `tests/test_asy_uart_comm.py:2120` | kw | 60 | tuned | `l1.asy_uart_comm_bsec_run_bound_s` — hang bound of the ten-exchange BSEC conformance run |
| `tests/test_asy_uart_comm.py:2142` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:2148` | call | 8 | tuned | `l1.asy_uart_comm_listener_short_bound_s` — hang bound, value 8, on the listener |
| `tests/test_asy_uart_comm.py:2151` | kw | 25 | tuned | `l1.asy_uart_comm_listener_run_bound_s` — hang bound, value 25 (runs that also await the listener) |
| `tests/test_asy_uart_comm.py:2155` | kw | 20 | tuned | `l1.asy_uart_comm_run_bound_s` — hang bound, value 20 |
| `tests/test_asy_uart_comm.py:2163` | kw | 2 | test input | the legacy BSEC bus the floor case builds (comment :2158-2161); construction only |
| `tests/test_asy_uart_comm.py:2163` | kw | 50 | test input | the legacy BSEC bus the floor case builds (comment :2158-2161); construction only |
| `tests/test_asy_uart_comm.py:2165` | kw | 1000 | test input | the legacy BSEC bus the floor case builds (comment :2158-2161); construction only |
| `tests/test_asy_uart_driver.py:27` | call | 5 | tuned | `l1.asy_uart_driver_run_bound_s` — run()'s per-test hang bound ("5s is generous next to this file's tightest inner bound", :26) |
| `tests/test_asy_uart_driver.py:69` | assert | 9600 | not tagged (config) | the driver's standalone default baudrate (TOML bus value; U8 Appendix A) |
| `tests/test_asy_uart_driver.py:365` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — deadline of a wait whose data is already there (shares the read deadlines' value) |
| `tests/test_asy_uart_driver.py:371` | kw | 20 | tuned | `l1.asy_uart_driver_no_data_timeout_ms` — deadline waited out in full: the poller never becomes ready |
| `tests/test_asy_uart_driver.py:388` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — deadline of a wait whose data is already there (shares the read deadlines' value) |
| `tests/test_asy_uart_driver.py:413` | kw | -1 | not tagged (identifier) | "wait forever" sentinel of the driver API |
| `tests/test_asy_uart_driver.py:417` | call | 5 | tuned | `l1.asy_uart_driver_task_inside_ms` — real wait for the other task to enter its locked region / poll loop |
| `tests/test_asy_uart_driver.py:419` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:432` | assert | 115200 | test input | values the test constructs with and reads back |
| `tests/test_asy_uart_driver.py:435` | assert | 9600 | test input | values the test constructs with and reads back |
| `tests/test_asy_uart_driver.py:500` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:502` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:579` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:593` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:607` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:619` | kw | 100 | tuned | `l1.asy_uart_driver_no_delimiter_timeout_ms` — deadline the codec bound races on a delimiter-less stream |
| `tests/test_asy_uart_driver.py:636` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:645` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:656` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:667` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:673` | kw | 50 | test input | refused before any wait (buffer too small, nameless delimiter, worst-case buffer unallocatable: asy_uart_driver.py:363-372) |
| `tests/test_asy_uart_driver.py:706` | call | 30 | tuned | `l1.asy_uart_driver_locked_work_ms` — real work inside the locked region the cancel lands in |
| `tests/test_asy_uart_driver.py:711` | call | 5 | tuned | `l1.asy_uart_driver_task_inside_ms` — real wait for the other task to enter its locked region / poll loop |
| `tests/test_asy_uart_driver.py:712` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:713` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:730` | call | 30 | tuned | `l1.asy_uart_driver_locked_work_ms` — real work inside the locked region the cancel lands in |
| `tests/test_asy_uart_driver.py:731` | kw | -1 | not tagged (identifier) | "wait forever" sentinel of the driver API |
| `tests/test_asy_uart_driver.py:736` | call | 5 | tuned | `l1.asy_uart_driver_task_inside_ms` — real wait for the other task to enter its locked region / poll loop |
| `tests/test_asy_uart_driver.py:737` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:738` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:753` | kw | -1 | not tagged (identifier) | "wait forever" sentinel of the driver API |
| `tests/test_asy_uart_driver.py:757` | call | 5 | tuned | `l1.asy_uart_driver_task_inside_ms` — real wait for the other task to enter its locked region / poll loop |
| `tests/test_asy_uart_driver.py:760` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:761` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:776` | kw | -1 | not tagged (identifier) | "wait forever" sentinel of the driver API |
| `tests/test_asy_uart_driver.py:780` | call | 5 | tuned | `l1.asy_uart_driver_task_inside_ms` — real wait for the other task to enter its locked region / poll loop |
| `tests/test_asy_uart_driver.py:781` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:783` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:799` | call | 400 | tuned | `l1.asy_uart_driver_wedged_hold_ms` — holder that never acknowledges; must outlast the short cancel bound (:804) |
| `tests/test_asy_uart_driver.py:803` | call | 5 | tuned | `l1.asy_uart_driver_task_inside_ms` — real wait for the other task to enter its locked region / poll loop |
| `tests/test_asy_uart_driver.py:804` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:804` | kw | 50 | tuned | `l1.asy_uart_driver_short_cancel_ack_ms` — cancel-acknowledgement bound waited out against the wedged holder; the product bound is uart.cancel_ack_timeout_ms (1000) |
| `tests/test_asy_uart_driver.py:806` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:821` | call | 20 | tuned | `l1.asy_uart_driver_holder_work_ms` — holder's real work before it acknowledges |
| `tests/test_asy_uart_driver.py:825` | call | 5 | tuned | `l1.asy_uart_driver_task_inside_ms` — real wait for the other task to enter its locked region / poll loop |
| `tests/test_asy_uart_driver.py:826` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:826` | kw | 500 | tuned | `l1.asy_uart_driver_cancel_ack_ms` — cancel-acknowledgement bound the prompt holder must meet |
| `tests/test_asy_uart_driver.py:827` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:846` | kw | 100 | tuned | `l1.asy_uart_driver_ready_timeout_ms` — ready() deadline where the mask is already met (bound only) |
| `tests/test_asy_uart_driver.py:875` | kw | 20 | tuned | `l1.asy_uart_driver_no_data_timeout_ms` — deadline waited out in full: the poller never becomes ready |
| `tests/test_asy_uart_driver.py:960` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:1053` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:1079` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:1144` | call | 5 | tuned | `l1.asy_uart_driver_task_inside_ms` — real wait for the other task to enter its locked region / poll loop |
| `tests/test_asy_uart_driver.py:1146` | call | 2 | tuned | `l1.asy_uart_driver_step_bound_s` — wait_for hang bound, value 2 |
| `tests/test_asy_uart_driver.py:1314` | call | 10 | test input | lock holder's sleep, cancelled by the test before it ends |
| `tests/test_asy_uart_driver.py:1372` | call | 0.2 | tuned | `l1.asy_i2c_driver_deadlock_wait_s` — same test as test_asy_i2c_driver.py:843 ("same as I2CDevice/SPIDevice", comment :1360-1361): shared ID, further site |
| `tests/test_asy_uart_driver.py:1499` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:1523` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:1574` | kw | 100 | tuned | `l1.asy_uart_driver_ready_timeout_ms` — ready() deadline where the mask is already met (bound only) |
| `tests/test_asy_uart_driver.py:1591` | kw | 1 | tuned | `l1.asy_uart_driver_poll_wait_ms` — real poll step between not-ready rounds |
| `tests/test_asy_uart_driver.py:1591` | kw | 40 | tuned | `l1.asy_uart_driver_idle_poll_ms` — idle rate the case's real-time assertions (>= 2 x 40, < 40) are computed from |
| `tests/test_asy_uart_driver.py:1595` | kw | 1 | tuned | `l1.asy_uart_driver_poll_wait_ms` — real poll step between not-ready rounds |
| `tests/test_asy_uart_driver.py:1595` | kw | 40 | tuned | `l1.asy_uart_driver_idle_poll_ms` — idle rate the case's real-time assertions (>= 2 x 40, < 40) are computed from |
| `tests/test_asy_uart_driver.py:1650` | kw | 1 | tuned | `l1.asy_uart_driver_poll_wait_ms` — real poll step between not-ready rounds |
| `tests/test_asy_uart_driver.py:1661` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:1677` | kw | 1 | tuned | `l1.asy_uart_driver_poll_wait_ms` — real poll step between not-ready rounds |
| `tests/test_asy_uart_driver.py:1686` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:1708` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:1791` | kw | 1 | tuned | `l1.asy_uart_driver_poll_wait_ms` — real poll step between not-ready rounds |
| `tests/test_asy_uart_driver.py:1799` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:1809` | kw | 30 | tuned | `l1.asy_uart_driver_silent_line_timeout_ms` — deadline waited out in full by a delimited/line read on a silent line |
| `tests/test_asy_uart_driver.py:1810` | kw | 30 | tuned | `l1.asy_uart_driver_silent_line_timeout_ms` — deadline waited out in full by a delimited/line read on a silent line |
| `tests/test_asy_uart_driver.py:1818` | kw | 30 | test input | refused before any wait (buffer too small, nameless delimiter, worst-case buffer unallocatable: asy_uart_driver.py:363-372) |
| `tests/test_asy_uart_driver.py:1819` | kw | 30 | test input | refused before any wait (buffer too small, nameless delimiter, worst-case buffer unallocatable: asy_uart_driver.py:363-372) |
| `tests/test_asy_uart_driver.py:1830` | kw | 10 | test input | refused before any wait (buffer too small, nameless delimiter, worst-case buffer unallocatable: asy_uart_driver.py:363-372) |
| `tests/test_asy_uart_driver.py:1852` | kw | 200 | tuned | `l1.asy_uart_driver_data_timeout_ms` — read deadline (start_timeout_ms and timeout_ms) of a read whose data arrives |
| `tests/test_asy_uart_driver.py:1880` | kw | 30 | tuned | `l1.asy_uart_driver_silent_line_timeout_ms` — deadline waited out in full by a delimited/line read on a silent line |
| `tests/test_asy_uart_link_driver.py:24` | const | 8 | test input | payload size chosen for the test pair (same as the UART harness's PAYLOAD_SIZE) |
| `tests/test_asy_uart_link_driver.py:25` | const | 100 | tuned | `l1.uart_comm_harness_timeout_ms` — the same test-pair reply timeout the UART harness defines ("the same shape tests/_uart_comm_harness.py's own Pair uses", :35-36) |
| `tests/test_asy_uart_link_driver.py:26` | const | 1 | tuned | `l1.uart_comm_harness_poll_wait_ms` — as :25, the test-pair poll step |
| `tests/test_asy_uart_link_driver.py:29` | param | 10 | tuned | `l1.uart_comm_harness_run_limit_s` — as :25, run()'s default hang bound |
| `tests/test_asy_uart_link_driver.py:58` | call | 5 | tuned | `l1.uart_comm_harness_listener_drain_s` — as :25, the listener drain bound |
| `tests/test_asy_uart_link_driver.py:151` | call | 0.005 | tuned | `l1.asy_uart_link_driver_round_poll_s` — poll step of the wait for one counted round |
| `tests/test_asy_uart_link_driver.py:370` | call | 1 | tuned | `l1.asy_uart_link_driver_ticker_step_ms` — pace of the background ticker whose progress (ticks > 2) is asserted |
| `tests/test_asy_udp_socket.py:147` | kw | 1.5 | test input | invalid conn_tries type the constructor must refuse |
| `tests/test_asy_udp_socket.py:207` | kw | 50 | tuned | `l1.asy_udp_socket_recv_empty_timeout_ms` — recvfrom deadline waited out in full (nothing sent) |
| `tests/test_asy_udp_socket.py:240` | kw | 200 | tuned | `l1.asy_udp_socket_attempt_timeout_ms` — per-attempt timeout; the first attempt waits it out before the retry gets the reply |
| `tests/test_asy_udp_socket.py:240` | kw | 3 | test input | attempt count that selects the case (retry after a drop, exhaustion) |
| `tests/test_asy_udp_socket.py:256` | kw | 30 | tuned | `l1.asy_udp_socket_exhaust_timeout_ms` — per-attempt timeout waited out on every try (nobody listens) |
| `tests/test_asy_udp_socket.py:256` | kw | 2 | test input | attempt count that selects the case (retry after a drop, exhaustion) |
| `tests/test_asy_udp_socket.py:286` | param | 1000 | tuned | `l1.asy_udp_socket_peer_recv_timeout_ms` — adversarial peer's deadline for the query it expects (default and two explicit uses) |
| `tests/test_asy_udp_socket.py:295` | call | 5 | tuned | `l1.asy_udp_socket_peer_poll_ms` — adversarial peer's poll step |
| `tests/test_asy_udp_socket.py:322` | kw | 500 | tuned | `l1.asy_udp_socket_reply_timeout_ms` — recv deadline where the datagram is expected |
| `tests/test_asy_udp_socket.py:344` | kw | 500 | tuned | `l1.asy_udp_socket_reply_timeout_ms` — recv deadline where the datagram is expected |
| `tests/test_asy_udp_socket.py:416` | kw | 150 | tuned | `l1.asy_udp_socket_spoof_wait_ms` — deadline waited out while the spoofed datagram is ignored |
| `tests/test_asy_udp_socket.py:419` | kw | 500 | tuned | `l1.asy_udp_socket_reply_timeout_ms` — recv deadline where the datagram is expected |
| `tests/test_asy_udp_socket.py:444` | call | 0.05 | tuned | `l1.asy_udp_socket_kernel_queue_s` — real wait for the kernel to queue the sent datagrams |
| `tests/test_asy_udp_socket.py:447` | kw | 200 | tuned | `l1.asy_udp_socket_recv_timeout_ms` — recv deadline of a datagram already queued |
| `tests/test_asy_udp_socket.py:472` | kw | 40 | tuned | `l1.asy_udp_socket_in_time_delay_ms` — sender delay that must land inside the in-time window (:473) |
| `tests/test_asy_udp_socket.py:473` | kw | 300 | tuned | `l1.asy_udp_socket_in_time_timeout_ms` — window the delayed datagram must land in |
| `tests/test_asy_udp_socket.py:476` | kw | 300 | tuned | `l1.asy_udp_socket_too_late_delay_ms` — sender delay that must land after the short window (:477) |
| `tests/test_asy_udp_socket.py:477` | kw | 100 | tuned | `l1.asy_udp_socket_too_late_timeout_ms` — window the late datagram must miss |
| `tests/test_asy_udp_socket.py:523` | kw | 80 | tuned | `l1.asy_udp_socket_ready_empty_timeout_ms` — ready() deadline waited out in full (nothing arrives) |
| `tests/test_asy_udp_socket.py:633` | call | 0.05 | tuned | `l1.asy_udp_socket_kernel_queue_s` — real wait for the kernel to queue the sent datagrams |
| `tests/test_asy_udp_socket.py:637` | kw | 200 | tuned | `l1.asy_udp_socket_recv_timeout_ms` — recv deadline of a datagram already queued |
| `tests/test_asy_udp_socket.py:758` | kw | 200 | tuned | `l1.asy_udp_socket_recv_timeout_ms` — ready() deadline, bound only (the poller disconnects first) |
| `tests/test_asy_udp_socket.py:758` | kw | 10 | tuned | `l1.asy_udp_socket_ready_poll_ms` — ready()'s real poll step |
| `tests/test_asy_udp_socket.py:782` | kw | 3 | test input | attempt count that selects the case; the real waits between attempts are the product's udp.retry_backoff_s |
| `tests/test_asy_udp_socket.py:786` | call | 0.6 | tuned | `l1.asy_udp_socket_fix_address_after_retry_s` — "after >=1 failed attempt (0.5s backoff), before conn_tries=3 is exhausted (1.5s)"; Dependant of udp.retry_backoff_s |
| `tests/test_asy_udp_socket.py:807` | kw | 1 | test input | attempt count that selects the case; the real waits between attempts are the product's udp.retry_backoff_s |
| `tests/test_asy_udp_socket.py:890` | call | 0.05 | tuned | `l1.asy_udp_socket_task_park_s` — real wait for a started task to park in its wait |
| `tests/test_asy_udp_socket.py:919` | kw | 50 | tuned | `l1.asy_udp_socket_ms_check_timeout_ms` — deadline waited out by the milliseconds-not-seconds case |
| `tests/test_asy_udp_socket.py:919` | kw | 10 | tuned | `l1.asy_udp_socket_ready_poll_ms` — ready()'s real poll step |
| `tests/test_asy_udp_socket.py:926` | assert | 2000 | tuned | `l1.asy_udp_socket_ms_check_elapsed_max_ms` — real elapsed budget of that case |
| `tests/test_asy_udp_socket.py:985` | call | 0.2 | tuned | `l1.asy_udp_socket_icmp_delivery_s` — real wait for the kernel to deliver the ICMP unreachable |
| `tests/test_asy_udp_socket.py:987` | kw | 5000 | tuned | `l1.asy_udp_socket_icmp_recv_timeout_ms` — deadline the POLLERR path must beat (the assertion :994 is its detector) |
| `tests/test_asy_udp_socket.py:994` | assert | 1000 | tuned | `l1.asy_udp_socket_icmp_elapsed_max_ms` — "detected via POLLERR promptly" |
| `tests/test_asy_udp_socket.py:1058` | kw | 1000 | tuned | `l1.asy_udp_socket_peer_recv_timeout_ms` — adversarial peer's deadline for the query it expects (default and two explicit uses) |
| `tests/test_asy_udp_socket.py:1070` | kw | 1000 | tuned | `l1.asy_udp_socket_long_reply_timeout_ms` — round-trip deadline where the reply is expected (NTP-shaped cases) |
| `tests/test_asy_udp_socket.py:1101` | kw | 500 | tuned | `l1.asy_udp_socket_unreachable_timeout_ms` — round-trip deadline to an unbound port (nobody listens) |
| `tests/test_asy_udp_socket.py:1126` | kw | 1000 | tuned | `l1.asy_udp_socket_peer_recv_timeout_ms` — adversarial peer's deadline for the query it expects (default and two explicit uses) |
| `tests/test_asy_udp_socket.py:1135` | kw | 1000 | tuned | `l1.asy_udp_socket_long_reply_timeout_ms` — round-trip deadline where the reply is expected (NTP-shaped cases) |
| `tests/test_asy_udp_socket.py:1161` | kw | 1000 | tuned | `l1.asy_udp_socket_long_reply_timeout_ms` — round-trip deadline where the reply is expected (NTP-shaped cases) |
| `tests/test_asy_udp_socket.py:1164` | kw | 1000 | tuned | `l1.asy_udp_socket_long_reply_timeout_ms` — round-trip deadline where the reply is expected (NTP-shaped cases) |
| `tests/test_asy_udp_socket.py:1191` | kw | 100 | tuned | `l1.asy_udp_socket_no_sender_timeout_ms` — deadline waited out in full (nobody sends) |
| `tests/test_asy_udp_socket.py:1193` | kw | 500 | tuned | `l1.asy_udp_socket_reply_timeout_ms` — recv deadline where the datagram is expected |
| `tests/test_asy_udp_socket.py:1223` | kw | 500 | tuned | `l1.asy_udp_socket_reply_timeout_ms` — recv deadline where the datagram is expected |
| `tests/test_asy_udp_socket.py:1226` | kw | 500 | tuned | `l1.asy_udp_socket_reply_timeout_ms` — recv deadline where the datagram is expected |
| `tests/test_asy_udp_socket.py:1313` | call | 0.05 | tuned | `l1.asy_udp_socket_kernel_queue_s` — real wait for the kernel to queue the sent datagrams |
| `tests/test_asy_udp_socket.py:1314` | kw | 200 | tuned | `l1.asy_udp_socket_recv_timeout_ms` — recv deadline of a datagram already queued |
| `tests/test_asy_udp_socket.py:1336` | kw | 3 | test input | attempt count that selects the case; the real waits between attempts are the product's udp.retry_backoff_s |
| `tests/test_asy_udp_socket.py:1340` | call | 0.1 | tuned | `l1.asy_udp_socket_first_attempt_s` — real wait for the first bind attempt to fail and enter its backoff |
| `tests/test_asy_udp_socket.py:1350` | assert | 1000 | tuned | `l1.asy_udp_socket_retry_cycle_min_ms` — lower bound of the 3-try retry cycle; Dependant of udp.retry_backoff_s |
| `tests/test_asy_udp_socket.py:1351` | assert | 5000 | tuned | `l1.asy_udp_socket_retry_cycle_max_ms` — upper bound ("didn't hang forever") |
| `tests/test_asy_udp_socket.py:1362` | kw | 3 | test input | attempt count that selects the case; the real waits between attempts are the product's udp.retry_backoff_s |
| `tests/test_asy_udp_socket.py:1365` | call | 0.1 | tuned | `l1.asy_udp_socket_first_attempt_s` — real wait for the first bind attempt to fail and enter its backoff |
| `tests/test_asy_udp_socket.py:1368` | call | 0.5 | tuned | `l1.asy_udp_socket_fix_address_after_s` — real delay before the address becomes bindable |
| `tests/test_asy_udp_socket.py:1392` | kw | 5 | test input | attempt count that selects the case; the real waits between attempts are the product's udp.retry_backoff_s |
| `tests/test_asy_udp_socket.py:1394` | call | 0.1 | tuned | `l1.asy_udp_socket_first_attempt_s` — real wait for the first bind attempt to fail and enter its backoff |
| `tests/test_asy_udp_socket.py:1403` | call | 2 | tuned | `l1.asy_udp_socket_disconnect_bound_s` — wait_for hang bound on disconnect() |
| `tests/test_asy_udp_socket.py:1421` | kw | 3 | test input | attempt count that selects the case; the real waits between attempts are the product's udp.retry_backoff_s |
| `tests/test_asy_udp_socket.py:1423` | call | 0.1 | tuned | `l1.asy_udp_socket_first_attempt_s` — real wait for the first bind attempt to fail and enter its backoff |
| `tests/test_asy_udp_socket.py:1425` | call | 0.05 | tuned | `l1.asy_udp_socket_task_park_s` — real wait for a started task to park in its wait |
| `tests/test_asy_udp_socket.py:1434` | call | 3 | tuned | `l1.asy_udp_socket_connect_bound_s` — wait_for hang bound on the first connect task |
| `tests/test_asy_udp_socket.py:1439` | call | 2 | tuned | `l1.asy_udp_socket_disconnect_bound_s` — wait_for hang bound on disconnect() |
| `tests/test_asy_udp_socket.py:1502` | call | 0.05 | tuned | `l1.asy_udp_socket_kernel_queue_s` — real wait for the kernel to queue the sent datagrams |
| `tests/test_asy_udp_socket.py:1503` | kw | 200 | tuned | `l1.asy_udp_socket_recv_timeout_ms` — recv deadline of a datagram already queued |
| `tests/test_asy_udp_socket.py:1530` | kw | 50 | test input | tries=0 / an invalid tries returns before any wait |
| `tests/test_asy_udp_socket.py:1571` | kw | 200 | test input | malformed argument: ready() returns False on its first iteration, the deadline is never reached |
| `tests/test_asy_udp_socket.py:1588` | kw | 200 | test input | malformed argument: ready() returns False on its first iteration, the deadline is never reached |
| `tests/test_asy_udp_socket.py:1605` | kw | -1 | not tagged (identifier) | "wait forever" sentinel of the API |
| `tests/test_asy_udp_socket.py:1605` | kw | 20 | tuned | `l1.asy_udp_socket_forever_poll_ms` — poll step of the deadline-less wait the case cancels mid-sleep |
| `tests/test_asy_udp_socket.py:1606` | call | 0.1 | tuned | `l1.asy_udp_socket_enter_sleep_s` — real wait for that wait to enter its sleep_ms() |
| `tests/test_asy_udp_socket.py:1648` | kw | 50 | test input | tries=0 / an invalid tries returns before any wait |
| `tests/test_asy_webserver_service.py:45` | param | 5.0 | tuned | `l1.asy_webserver_service_run_bound_s` — run_timed()'s default hang bound; the explicit 5.0 bounds share it |
| `tests/test_asy_webserver_service.py:92` | const-c | 5 | test input | schema of the test's fake module (default 5, 1-60; 0, -10..10) |
| `tests/test_asy_webserver_service.py:92` | const-c | 1 | test input | schema of the test's fake module (default 5, 1-60; 0, -10..10) |
| `tests/test_asy_webserver_service.py:92` | const-c | 60 | test input | schema of the test's fake module (default 5, 1-60; 0, -10..10) |
| `tests/test_asy_webserver_service.py:93` | const-c | -10 | test input | schema of the test's fake module (default 5, 1-60; 0, -10..10) |
| `tests/test_asy_webserver_service.py:93` | const-c | 10 | test input | schema of the test's fake module (default 5, 1-60; 0, -10..10) |
| `tests/test_asy_webserver_service.py:1033` | kw | 0.01 | tuned | `l1.asy_webserver_service_tiny_per_call_s` — per-call timeout of the service under test, waited out by the reclaim the case checks |
| `tests/test_asy_webserver_service.py:1062` | kw | 0.05 | tuned | `l1.asy_webserver_service_reclaim_per_call_s` — per-call timeout waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:1062` | kw | 0.2 | tuned | `l1.asy_webserver_service_short_outer_cap_s` — outer cap waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:1065` | kw | 2.0 | tuned | `l1.asy_webserver_service_serve_bound_s` — run_timed hang bound on one _serve(), value 2.0 |
| `tests/test_asy_webserver_service.py:1158` | kw | 0.05 | tuned | `l1.asy_webserver_service_reclaim_per_call_s` — per-call timeout waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:1158` | kw | 2.0 | tuned | `l1.asy_webserver_service_headroom_s` — service timeout (per-call and/or outer cap) that must not fire before the case's own event |
| `tests/test_asy_webserver_service.py:1160` | kw | 2.0 | tuned | `l1.asy_webserver_service_serve_bound_s` — run_timed hang bound on one _serve(), value 2.0 |
| `tests/test_asy_webserver_service.py:1179` | kw | 10.0 | tuned | `l1.asy_webserver_service_run_long_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_asy_webserver_service.py:1184` | kw | 5.0 | tuned | `l1.asy_webserver_service_run_bound_s` — run_timed hang bound, value 5.0 |
| `tests/test_asy_webserver_service.py:1192` | call | 0.01 | tuned | `l1.asy_webserver_service_admit_settle_s` — real wait for the held connections to be admitted |
| `tests/test_asy_webserver_service.py:1205` | kw | 5.0 | tuned | `l1.asy_webserver_service_run_bound_s` — run_timed hang bound, value 5.0 |
| `tests/test_asy_webserver_service.py:1209` | kw | 0.05 | tuned | `l1.asy_webserver_service_reclaim_per_call_s` — per-call timeout waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:1209` | kw | 2.0 | tuned | `l1.asy_webserver_service_headroom_s` — service timeout (per-call and/or outer cap) that must not fire before the case's own event |
| `tests/test_asy_webserver_service.py:1219` | kw | 5.0 | tuned | `l1.asy_webserver_service_run_bound_s` — run_timed hang bound, value 5.0 |
| `tests/test_asy_webserver_service.py:1237` | kw | 5.0 | tuned | `l1.asy_webserver_service_run_bound_s` — run_timed hang bound, value 5.0 |
| `tests/test_asy_webserver_service.py:1248` | call | 0.01 | tuned | `l1.asy_webserver_service_close_poll_s` — poll step (200 rounds) of the wait for the close |
| `tests/test_asy_webserver_service.py:1265` | kw | 5.0 | tuned | `l1.asy_webserver_service_run_bound_s` — run_timed hang bound, value 5.0 |
| `tests/test_asy_webserver_service.py:1302` | kw | 0.05 | tuned | `l1.asy_webserver_service_reclaim_per_call_s` — per-call timeout waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:1302` | kw | 1.0 | tuned | `l1.asy_webserver_service_mid_headroom_s` — as _HEADROOM_S, value 1.0 |
| `tests/test_asy_webserver_service.py:1306` | kw | 3.0 | tuned | `l1.asy_webserver_service_serve_long_bound_s` — run_timed hang bound, value 3.0 |
| `tests/test_asy_webserver_service.py:1312` | kw | 2.0 | tuned | `l1.asy_webserver_service_serve_bound_s` — run_timed hang bound on one _serve(), value 2.0 |
| `tests/test_asy_webserver_service.py:1316` | kw | 3.0 | tuned | `l1.asy_webserver_service_serve_long_bound_s` — run_timed hang bound, value 3.0 |
| `tests/test_asy_webserver_service.py:1326` | kw | 1.0 | tuned | `l1.asy_webserver_service_mid_headroom_s` — as _HEADROOM_S, value 1.0 |
| `tests/test_asy_webserver_service.py:1326` | kw | 2.0 | tuned | `l1.asy_webserver_service_headroom_s` — service timeout (per-call and/or outer cap) that must not fire before the case's own event |
| `tests/test_asy_webserver_service.py:1329` | kw | 3.0 | tuned | `l1.asy_webserver_service_serve_long_bound_s` — run_timed hang bound, value 3.0 |
| `tests/test_asy_webserver_service.py:1362` | const | 2048 | mirror | → `web.max_content_length` — "what _make_service() sets, matching the shipped default" (A.U8.04 names this site) |
| `tests/test_asy_webserver_service.py:1365` | param | 7 | test input | Interval value written in the PUT body the case sends |
| `tests/test_asy_webserver_service.py:1377` | kw | 2.0 | tuned | `l1.asy_webserver_service_serve_bound_s` — run_timed hang bound on one _serve(), value 2.0 |
| `tests/test_asy_webserver_service.py:1382` | param | 7 | test input | Interval value written in the PUT body the case sends |
| `tests/test_asy_webserver_service.py:1385` | kw | 3.0 | tuned | `l1.asy_webserver_service_serve_long_bound_s` — run_timed hang bound, value 3.0 |
| `tests/test_asy_webserver_service.py:1445` | kw | 2.0 | tuned | `l1.asy_webserver_service_serve_bound_s` — run_timed hang bound on one _serve(), value 2.0 |
| `tests/test_asy_webserver_service.py:1445` | kw | 5.0 | tuned | `l1.asy_webserver_service_long_headroom_s` — as _HEADROOM_S, value 5.0 (held connections must outlive the case) |
| `tests/test_asy_webserver_service.py:1457` | kw | 10.0 | tuned | `l1.asy_webserver_service_run_long_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_asy_webserver_service.py:1529` | kw | 0.05 | tuned | `l1.asy_webserver_service_reclaim_per_call_s` — per-call timeout waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:1529` | kw | 0.5 | tuned | `l1.asy_webserver_service_wedge_outer_cap_s` — outer cap waited out by the N-wedged case |
| `tests/test_asy_webserver_service.py:1538` | kw | 5.0 | tuned | `l1.asy_webserver_service_run_bound_s` — run_timed hang bound, value 5.0 |
| `tests/test_asy_webserver_service.py:1542` | kw | 0.02 | tuned | `l1.asy_webserver_service_fast_per_call_s` — per-call timeout waited out by the rewedge/cooldown cases |
| `tests/test_asy_webserver_service.py:1542` | kw | 1.0 | tuned | `l1.asy_webserver_service_mid_headroom_s` — as _HEADROOM_S, value 1.0 |
| `tests/test_asy_webserver_service.py:1552` | kw | 10.0 | tuned | `l1.asy_webserver_service_run_long_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_asy_webserver_service.py:1556` | kw | 0.02 | tuned | `l1.asy_webserver_service_fast_per_call_s` — per-call timeout waited out by the rewedge/cooldown cases |
| `tests/test_asy_webserver_service.py:1556` | kw | 0.2 | tuned | `l1.asy_webserver_service_short_outer_cap_s` — outer cap waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:1565` | kw | 15.0 | tuned | `l1.asy_webserver_service_rewedge_run_bound_s` — run_timed hang bound of the repeated-rewedging case |
| `tests/test_asy_webserver_service.py:1569` | kw | 0.05 | tuned | `l1.asy_webserver_service_reclaim_per_call_s` — per-call timeout waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:1569` | kw | 0.2 | tuned | `l1.asy_webserver_service_short_outer_cap_s` — outer cap waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:1571` | kw | 3.0 | tuned | `l1.asy_webserver_service_serve_long_bound_s` — run_timed hang bound, value 3.0 |
| `tests/test_asy_webserver_service.py:1639` | kw | 0.05 | tuned | `l1.asy_webserver_service_reclaim_per_call_s` — per-call timeout waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:1639` | kw | 2.0 | tuned | `l1.asy_webserver_service_headroom_s` — service timeout (per-call and/or outer cap) that must not fire before the case's own event |
| `tests/test_asy_webserver_service.py:1641` | kw | 2.0 | tuned | `l1.asy_webserver_service_serve_bound_s` — run_timed hang bound on one _serve(), value 2.0 |
| `tests/test_asy_webserver_service.py:1659` | kw | 0.05 | tuned | `l1.asy_webserver_service_reclaim_per_call_s` — per-call timeout waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:1659` | kw | 1.0 | tuned | `l1.asy_webserver_service_mid_headroom_s` — as _HEADROOM_S, value 1.0 |
| `tests/test_asy_webserver_service.py:1661` | kw | 2.0 | tuned | `l1.asy_webserver_service_serve_bound_s` — run_timed hang bound on one _serve(), value 2.0 |
| `tests/test_asy_webserver_service.py:1741` | kw | 2.0 | tuned | `l1.asy_webserver_service_serve_bound_s` — run_timed hang bound on one _serve(), value 2.0 |
| `tests/test_asy_webserver_service.py:1745` | kw | 3.0 | tuned | `l1.asy_webserver_service_serve_long_bound_s` — run_timed hang bound, value 3.0 |
| `tests/test_asy_webserver_service.py:1769` | kw | 10.0 | tuned | `l1.asy_webserver_service_run_long_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_asy_webserver_service.py:1792` | call | 0.05 | tuned | `l1.asy_webserver_service_task_reach_s` — real wait for the started task to reach its server/handler wait |
| `tests/test_asy_webserver_service.py:1800` | kw | 3.0 | tuned | `l1.asy_webserver_service_serve_long_bound_s` — run_timed hang bound, value 3.0 |
| `tests/test_asy_webserver_service.py:1812` | kw | 0.02 | tuned | `l1.asy_webserver_service_fast_per_call_s` — per-call timeout waited out by the rewedge/cooldown cases |
| `tests/test_asy_webserver_service.py:1812` | kw | 0.1 | tuned | `l1.asy_webserver_service_tiny_outer_cap_s` — outer cap of the leak scenario (:1812) |
| `tests/test_asy_webserver_service.py:1835` | kw | 60.0 | tuned | `l1.webserver_leak_scenario_timeout_s` — run_timed bound 30 -> 60 s, registered as it is by A.U8.17 |
| `tests/test_asy_webserver_service.py:1954` | const | 256 | mirror | → `web.chunk_bytes` — "WebserverService's chunk_bytes default, as observed from outside" (A.U8.04 names this site) |
| `tests/test_asy_webserver_service.py:1956` | const-c | 127 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1956` | const-c | 128 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1956` | const-c | 129 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1956` | const-c | 255 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1956` | const-c | 256 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1956` | const-c | 257 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1956` | const-c | 511 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1956` | const-c | 512 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1956` | const-c | 513 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1956` | const-c | 767 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1956` | const-c | 768 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1956` | const-c | 769 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1957` | const-c | 1023 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1957` | const-c | 1024 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1957` | const-c | 1025 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1957` | const-c | 9292 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1957` | const-c | 65553 | test input | response sizes picked around multiples of the 256-byte piece (and 9292, a size seen truncated on the bench); they move with web.chunk_bytes but are case selection, not a budget |
| `tests/test_asy_webserver_service.py:1976` | kw | 5.0 | tuned | `l1.asy_webserver_service_run_bound_s` — run_timed hang bound, value 5.0 |
| `tests/test_asy_webserver_service.py:2048` | kw | 5.0 | tuned | `l1.asy_webserver_service_run_bound_s` — run_timed hang bound, value 5.0 |
| `tests/test_asy_webserver_service.py:2469` | const | 256 | mirror | → `web.chunk_bytes` — "the firmware's chunk_bytes default, restated: a const() is not …" (A.U8.04 names this site) |
| `tests/test_asy_webserver_service.py:3055` | kw | 10.0 | tuned | `l1.asy_webserver_service_cancel_outer_cap_s` — outer cap that must not fire before the test cancels |
| `tests/test_asy_webserver_service.py:3065` | call | 0.05 | tuned | `l1.asy_webserver_service_task_reach_s` — real wait for the started task to reach its server/handler wait |
| `tests/test_asy_webserver_service.py:3081` | kw | 0.05 | tuned | `l1.asy_webserver_service_reclaim_per_call_s` — per-call timeout waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:3081` | kw | 2.0 | tuned | `l1.asy_webserver_service_headroom_s` — service timeout (per-call and/or outer cap) that must not fire before the case's own event |
| `tests/test_asy_webserver_service.py:3083` | kw | 2.0 | tuned | `l1.asy_webserver_service_serve_bound_s` — run_timed hang bound on one _serve(), value 2.0 |
| `tests/test_asy_webserver_service.py:3096` | kw | 0.05 | tuned | `l1.asy_webserver_service_reclaim_per_call_s` — per-call timeout waited out by the reclaim cases |
| `tests/test_asy_webserver_service.py:3096` | kw | 1.0 | tuned | `l1.asy_webserver_service_mid_headroom_s` — as _HEADROOM_S, value 1.0 |
| `tests/test_asy_webserver_service.py:3099` | kw | 2.0 | tuned | `l1.asy_webserver_service_serve_bound_s` — run_timed hang bound on one _serve(), value 2.0 |
| `tests/test_asy_wifi_service.py:24` | const-c | 32 | not tagged (API domain) | restates asy_wifi_service.py's _VAL_* REST schema (comment :22-23) |
| `tests/test_asy_wifi_service.py:25` | const-c | 8 | not tagged (API domain) | restates asy_wifi_service.py's _VAL_* REST schema (comment :22-23) |
| `tests/test_asy_wifi_service.py:25` | const-c | 63 | not tagged (API domain) | restates asy_wifi_service.py's _VAL_* REST schema (comment :22-23) |
| `tests/test_asy_wifi_service.py:26` | const-c | 2 | not tagged (API domain) | restates asy_wifi_service.py's _VAL_* REST schema (comment :22-23) |
| `tests/test_asy_wifi_service.py:27` | const-c | 1 | not tagged (API domain) | restates asy_wifi_service.py's _VAL_* REST schema (comment :22-23) |
| `tests/test_asy_wifi_service.py:27` | const-c | 32 | not tagged (API domain) | restates asy_wifi_service.py's _VAL_* REST schema (comment :22-23) |
| `tests/test_asy_wifi_service.py:29` | const-c | 8 | not tagged (API domain) | restates asy_wifi_service.py's _VAL_* REST schema (comment :22-23) |
| `tests/test_asy_wifi_service.py:29` | const-c | 63 | not tagged (API domain) | restates asy_wifi_service.py's _VAL_* REST schema (comment :22-23) |
| `tests/test_asy_wifi_service.py:276` | assert | 1000 | not tagged (derived) | 1 s counter tick |
| `tests/test_asy_wifi_service.py:283` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_wifi_service.py:293` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_asy_wifi_service.py:1256` | kw | 5000 | test input | period given to a fake Timer the test then checks |
| `tests/test_asy_wifi_service.py:1267` | assert | 60000 | test input | computed from the case's hotspot_time_min=1 (x 60000 ms) |
| `tests/test_asy_wifi_service.py:1852` | kw | 5000 | test input | period given to a fake Timer the test then checks |
| `tests/test_asy_wifi_service.py:1904` | call | 100 | test input | "sleep forever" stand-in the test cancels |
| `tests/test_asy_wifi_service.py:1994` | call | 100 | test input | "sleep forever" stand-in the test cancels |
| `tests/test_asy_wifi_service.py:2233` | call | 2.0 | tuned | `l1.asy_wifi_service_connect_bound_s` — wait_for hang bound: wlan_connect() must complete |
| `tests/test_asy_wifi_service.py:2343` | call | 0.3 | tuned | `l1.asy_wifi_service_no_reply_wait_s` — real wait for the captive DNS server to (not) answer a malformed query |
| `tests/test_asy_wifi_service.py:2368` | call | 3600 | test input | "sleep forever" stand-in the test cancels |
| `tests/test_asy_wifi_service.py:2389` | call | 10 | tuned | `l1.asy_wifi_service_sent_poll_ms` — poll step of the wait for the fake socket's send |
| `tests/test_asy_wifi_service.py:2409` | call | 0.2 | tuned | `l1.asy_wifi_service_off_subnet_wait_s` — real wait for the server to (not) answer an off-subnet query |
| `tests/test_asy_wifi_service.py:2446` | call | 50 | tuned | `l1.asy_wifi_service_connect_poll_ms` — poll step (200 rounds, 10 s) of the wait for Connected; the connect itself takes the product's ~5 s (wifi.sta_connect_poll_iters x wifi.sta_connect_poll_s, comment :2425-2427) |
| `tests/test_asy_wifi_service.py:2469` | call | 20 | tuned | `l1.asy_wifi_service_phase_poll_ms` — poll step of the wait for the hotspot phase |
| `tests/test_asy_wifi_service.py:2636` | call | 1 | tuned | `l1.asy_wifi_service_flash_cancel_bound_s` — wait_for hang bound on the cancelled flash task |
| `tests/test_asy_wifi_service.py:2885` | const-c | 16 | not tagged (API domain) | byte/character bounds of the same REST fields (32 / 63 bytes) |
| `tests/test_asy_wifi_service.py:2886` | const-c | 32 | not tagged (API domain) | byte/character bounds of the same REST fields (32 / 63 bytes) |
| `tests/test_asy_wifi_service.py:2886` | const-c | 31 | not tagged (API domain) | byte/character bounds of the same REST fields (32 / 63 bytes) |
| `tests/test_asy_wifi_service.py:2888` | const-c | 16 | not tagged (API domain) | byte/character bounds of the same REST fields (32 / 63 bytes) |
| `tests/test_asy_wifi_service.py:2888` | const-c | 17 | not tagged (API domain) | byte/character bounds of the same REST fields (32 / 63 bytes) |
| `tests/test_asy_wifi_service.py:2889` | const-c | 32 | not tagged (API domain) | byte/character bounds of the same REST fields (32 / 63 bytes) |
| `tests/test_asy_wifi_service.py:2889` | const-c | 31 | not tagged (API domain) | byte/character bounds of the same REST fields (32 / 63 bytes) |
| `tests/test_base_classes.py:103` | const-c | 2 | not tagged (API domain) | restates the SampleInterv schema entry shape of asy_bmp3xx_driver.py:74 (default 2, 1-3600) |
| `tests/test_base_classes.py:103` | const-c | 1 | not tagged (API domain) | restates the SampleInterv schema entry shape of asy_bmp3xx_driver.py:74 (default 2, 1-3600) |
| `tests/test_base_classes.py:103` | const-c | 3600 | not tagged (API domain) | restates the SampleInterv schema entry shape of asy_bmp3xx_driver.py:74 (default 2, 1-3600) |
| `tests/test_bus_hazard_generated.py:144` | const-c | 80 | test input | an I2C address in a made-up attachment the case feeds to buildgen |
| `tests/test_bus_hazard_multi_device.py:71` | const-c | 7 | not tagged (fact) | I2C reserved address ranges (comment :68-70) |
| `tests/test_bus_hazard_multi_device.py:71` | const-c | 120 | not tagged (fact) | I2C reserved address ranges (comment :68-70) |
| `tests/test_bus_hazard_multi_device.py:71` | const-c | 127 | not tagged (fact) | I2C reserved address ranges (comment :68-70) |
| `tests/test_bus_hazard_multi_device.py:85` | const | 8300000 | test input | seeded ADC values and the results computed from them |
| `tests/test_bus_hazard_multi_device.py:86` | const | 8500000 | test input | seeded ADC values and the results computed from them |
| `tests/test_bus_hazard_multi_device.py:87` | const | 28.460795242070162 | test input | seeded ADC values and the results computed from them |
| `tests/test_bus_hazard_multi_device.py:88` | const | 713.765147356092 | test input | seeded ADC values and the results computed from them |
| `tests/test_captive_dns.py:351` | param | -1 | not tagged (identifier) | "no timeout" sentinel of the doubled socket API |
| `tests/test_captive_dns.py:357` | call | 3600 | test input | "no more traffic" park the test cancels |
| `tests/test_captive_dns.py:360` | param | -1 | not tagged (identifier) | "no timeout" sentinel of the doubled socket API |
| `tests/test_captive_dns.py:370` | param | 1000 | tuned | `l1.captive_dns_wait_until_timeout_ms` — default deadline of _wait_until() |
| `tests/test_captive_dns.py:375` | call | 10 | tuned | `l1.captive_dns_wait_until_poll_ms` — _wait_until()'s poll step |
| `tests/test_captive_dns.py:423` | call | 20 | tuned | `l1.captive_dns_stray_reply_wait_ms` — real wait that gives a stray second reply the chance to appear |
| `tests/test_captive_dns.py:482` | assert | 1000 | tuned | `l1.captive_dns_no_backoff_elapsed_max_ms` — budget "well under" the 3 s error backoff; Dependant of dns_server.error_retry_wait_s |
| `tests/test_captive_dns.py:512` | call | 20 | tuned | `l1.captive_dns_reach_recv_ms` — real wait for the server to reach its pending recvfrom() |
| `tests/test_captive_dns.py:595` | call | 50 | tuned | `l1.captive_dns_bind_wait_ms` — real wait for the server to bind |
| `tests/test_captive_dns.py:597` | call | 200 | tuned | `l1.captive_dns_reply_wait_ms` — real wait for the server to process what the peer sent |
| `tests/test_captive_dns.py:647` | param | 20 | tuned | `l1.captive_dns_reach_recv_ms` — _run_briefly_and_cancel()'s default run time, the same purpose |
| `tests/test_captive_dns.py:824` | call | 50 | tuned | `l1.captive_dns_bind_wait_ms` — real wait for the server to bind |
| `tests/test_captive_dns.py:827` | call | 100 | tuned | `l1.captive_dns_cycle_wait_ms` — real wait before checking the server survived the cycle's query |
| `tests/test_captive_dns.py:854` | call | 50 | tuned | `l1.captive_dns_bind_wait_ms` — real wait for the server to bind |
| `tests/test_captive_dns.py:858` | call | 200 | tuned | `l1.captive_dns_reply_wait_ms` — real wait for the server to process what the peer sent |
| `tests/test_captive_dns.py:884` | call | 50 | tuned | `l1.captive_dns_bind_wait_ms` — real wait for the server to bind |
| `tests/test_captive_dns.py:890` | call | 10 | tuned | `l1.captive_dns_cleanup_tick_ms` — ten real ticks for the cancelled task's own cleanup to run |
| `tests/test_captive_dns.py:941` | kw | 5000 | tuned | `l1.captive_dns_backoff_wait_timeout_ms` — deadline covering the 3 s error backoff; Dependant of dns_server.error_retry_wait_s |
| `tests/test_captive_dns.py:952` | assert | 3000 | mirror | → `dns_server.error_retry_wait_s` — "proves the 3s backoff genuinely ran" (A.U8.11 names this site); 3000 = 3 s x 1000 |
| `tests/test_captive_dns.py:972` | call | 20 | tuned | `l1.captive_dns_reach_recv_ms` — real wait for the server to reach its pending recvfrom() |
| `tests/test_captive_dns.py:999` | kw | 15000 | tuned | `l1.captive_dns_backoff_series_timeout_ms` — deadline covering 0.5 + 1 + 2 (+4) s of recv backoff |
| `tests/test_captive_dns.py:1008` | assert | 4 | test input | call counts the case's scripted empty results produce |
| `tests/test_captive_dns.py:1012` | assert | 400 | tuned | `l1.captive_dns_gap_initial_min_ms` — lower edge of the ~0.5 s gap band; Dependant of dns_server.recv_backoff_initial_s |
| `tests/test_captive_dns.py:1012` | assert | 800 | tuned | `l1.captive_dns_gap_initial_max_ms` — upper edge of that band |
| `tests/test_captive_dns.py:1013` | assert | 900 | tuned | `l1.captive_dns_gap_doubled_min_ms` — lower edge of the ~1.0 s band; Dependant of dns_server.recv_backoff_initial_s and _mult |
| `tests/test_captive_dns.py:1013` | assert | 1400 | tuned | `l1.captive_dns_gap_doubled_max_ms` — upper edge of that band |
| `tests/test_captive_dns.py:1014` | assert | 1900 | tuned | `l1.captive_dns_gap_quad_min_ms` — lower edge of the ~2.0 s band |
| `tests/test_captive_dns.py:1014` | assert | 2600 | tuned | `l1.captive_dns_gap_quad_max_ms` — upper edge of that band |
| `tests/test_captive_dns.py:1034` | assert | 5 | test input | call counts the case's scripted empty results produce |
| `tests/test_captive_dns.py:1034` | kw | 15000 | tuned | `l1.captive_dns_backoff_series_timeout_ms` — deadline covering 0.5 + 1 + 2 (+4) s of recv backoff |
| `tests/test_captive_dns.py:1041` | assert | 400 | tuned | `l1.captive_dns_gap_initial_min_ms` — lower edge of the ~0.5 s gap band; Dependant of dns_server.recv_backoff_initial_s |
| `tests/test_captive_dns.py:1041` | assert | 800 | tuned | `l1.captive_dns_gap_initial_max_ms` — upper edge of that band |
| `tests/test_captive_dns.py:1042` | assert | 900 | tuned | `l1.captive_dns_gap_doubled_min_ms` — lower edge of the ~1.0 s band; Dependant of dns_server.recv_backoff_initial_s and _mult |
| `tests/test_captive_dns.py:1042` | assert | 1400 | tuned | `l1.captive_dns_gap_doubled_max_ms` — upper edge of that band |
| `tests/test_captive_dns.py:1043` | assert | 300 | tuned | `l1.captive_dns_gap_no_backoff_max_ms` — "no backoff sleep" bound |
| `tests/test_captive_dns.py:1044` | assert | 400 | tuned | `l1.captive_dns_gap_initial_min_ms` — lower edge of the ~0.5 s gap band; Dependant of dns_server.recv_backoff_initial_s |
| `tests/test_captive_dns.py:1044` | assert | 800 | tuned | `l1.captive_dns_gap_initial_max_ms` — upper edge of that band |
| `tests/test_captive_dns.py:1059` | kw | 20000 | tuned | `l1.captive_dns_backoff_cap_timeout_ms` — deadline covering five backoff steps up to the 5 s cap |
| `tests/test_captive_dns.py:1065` | assert | 6 | test input | call counts the case's scripted empty results produce |
| `tests/test_captive_dns.py:1067` | assert | 4700 | tuned | `l1.captive_dns_gap_cap_min_ms` — lower edge of the band around the 5 s cap; a Dependant of dns_server.recv_backoff_max_s, not a mirror (neither edge equals 5000; see Register fixes) |
| `tests/test_captive_dns.py:1067` | assert | 5400 | tuned | `l1.captive_dns_gap_cap_max_ms` — upper edge of that band (below the uncapped ~8 s) |
| `tests/test_captive_dns.py:1077` | call | 20 | tuned | `l1.captive_dns_reach_recv_ms` — real wait for the server to reach its pending recvfrom() |
| `tests/test_captive_dns.py:1096` | call | 20 | tuned | `l1.captive_dns_reach_recv_ms` — real wait for the server to reach its pending recvfrom() |
| `tests/test_config_manager.py:34` | const-c | 5 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:34` | const-c | 10 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:35` | const-c | -10.0 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:35` | const-c | 1.5 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:35` | const-c | 10.0 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:36` | const-c | 1 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:36` | const-c | 5 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:38` | const-c | 10 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:38` | const-c | 99 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:43` | const-c | 10.0 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:43` | const-c | 99.0 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:44` | const-c | 1 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:44` | const-c | 5 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:49` | const-c | 1 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:49` | const-c | 100 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:50` | const-c | 2 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:50` | const-c | 100 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:51` | const-c | 3 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:51` | const-c | 100 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:52` | const-c | 4 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:52` | const-c | 100 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:53` | const-c | 5 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:53` | const-c | 100 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:54` | const-c | 6 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:54` | const-c | 100 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:55` | const-c | 7 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:55` | const-c | 100 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:56` | const-c | 8 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_config_manager.py:56` | const-c | 100 | test input | synthetic schema entries the ConfigManager cases run on (comment :32-33, :47-48) |
| `tests/test_digital_twin_bus_hazard_concurrency.py:76` | call | 1.0 | tuned | `l2.twin_wdt_feed_interval_s` — the same 1 s twin watchdog feed as digital_twin/launch.py:41 (A.U8.08's ID): shared, further site |
| `tests/test_digital_twin_bus_hazard_concurrency.py:187` | kw | 20.0 | tuned | `l2.bus_hazard_concurrency_run_bound_s` — run_timed hang bound, value 20.0 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:201` | kw | 20.0 | tuned | `l2.bus_hazard_concurrency_run_bound_s` — run_timed hang bound, value 20.0 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:215` | kw | 40.0 | tuned | `l2.bus_hazard_concurrency_api_run_bound_s` — run_timed hang bound of the runs with the API under load |
| `tests/test_digital_twin_bus_hazard_concurrency.py:229` | kw | 40.0 | tuned | `l2.bus_hazard_concurrency_api_run_bound_s` — run_timed hang bound of the runs with the API under load |
| `tests/test_digital_twin_bus_hazard_concurrency.py:272` | kw | 20.0 | tuned | `l2.bus_hazard_concurrency_run_bound_s` — run_timed hang bound, value 20.0 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:314` | kw | 20.0 | tuned | `l2.bus_hazard_concurrency_run_bound_s` — run_timed hang bound, value 20.0 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:349` | kw | 20.0 | tuned | `l2.bus_hazard_concurrency_run_bound_s` — run_timed hang bound, value 20.0 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:357` | call | 0.5 | tuned | `l2.bus_hazard_concurrency_established_poll_s` — poll step of the wait for the first connection |
| `tests/test_digital_twin_bus_hazard_concurrency.py:360` | call | 1.0 | tuned | `l2.bus_hazard_concurrency_reconnect_poll_s` — poll step of the wait for the reconnection |
| `tests/test_digital_twin_bus_hazard_concurrency.py:392` | call | 75.0 | tuned | `l2.bus_hazard_concurrency_flap_window_s` — observation window that must cover the product's 60 s ESTABLISHED retry; Dependant of wifi.sta_retry_after_loss_s |
| `tests/test_digital_twin_bus_hazard_concurrency.py:408` | kw | 95.0 | tuned | `l2.bus_hazard_concurrency_flap_run_bound_s` — run_timed hang bound of the 75 s flap run |
| `tests/test_digital_twin_bus_hazard_concurrency.py:438` | kw | 20.0 | tuned | `l2.bus_hazard_concurrency_run_bound_s` — run_timed hang bound, value 20.0 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:469` | kw | 20.0 | tuned | `l2.bus_hazard_concurrency_run_bound_s` — run_timed hang bound, value 20.0 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:498` | kw | 20.0 | tuned | `l2.bus_hazard_concurrency_run_bound_s` — run_timed hang bound, value 20.0 |
| `tests/test_digital_twin_bus_hazard_concurrency.py:533` | kw | 30.0 | tuned | `l2.bus_hazard_concurrency_state_run_bound_s` — run_timed hang bound, value 30.0 |
| `tests/test_digital_twin_fram.py:185` | assert | 153 | test input | byte the case wrote and reads back from the state file |
| `tests/test_digital_twin_fram.py:257` | const | 1 | test input | chunk size patched down to force the multi-round load path |
| `tests/test_digital_twin_http_client.py:24` | param | 5.0 | tuned | `l2.http_client_run_bound_s` — run_timed()'s default and explicit hang bound, value 5.0 |
| `tests/test_digital_twin_http_client.py:229` | const | 4 | test input | read-chunk size patched down to force several bounded reads |
| `tests/test_digital_twin_http_client.py:278` | const | 4 | test input | read-chunk size patched down to force several bounded reads |
| `tests/test_digital_twin_http_client.py:344` | kw | 5.0 | tuned | `l2.http_client_run_bound_s` — run_timed()'s default and explicit hang bound, value 5.0 |
| `tests/test_digital_twin_http_client.py:360` | call | 20 | tuned | `l2.http_client_mid_body_pause_ms` — real pause between the two halves of the served body the client must read across |
| `tests/test_digital_twin_http_client.py:377` | kw | 5.0 | tuned | `l2.http_client_run_bound_s` — run_timed()'s default and explicit hang bound, value 5.0 |
| `tests/test_digital_twin_http_client.py:410` | kw | 5.0 | tuned | `l2.http_client_run_bound_s` — run_timed()'s default and explicit hang bound, value 5.0 |
| `tests/test_digital_twin_http_client.py:431` | kw | 5.0 | tuned | `l2.http_client_run_bound_s` — run_timed()'s default and explicit hang bound, value 5.0 |
| `tests/test_digital_twin_http_client.py:446` | kw | 5.0 | tuned | `l2.http_client_run_bound_s` — run_timed()'s default and explicit hang bound, value 5.0 |
| `tests/test_digital_twin_isl29125.py:11` | const | 1 | not tagged (identifier) | ISL29125 register addresses and field bits |
| `tests/test_digital_twin_isl29125.py:12` | const | 2 | not tagged (identifier) | ISL29125 register addresses and field bits |
| `tests/test_digital_twin_isl29125.py:13` | const | 3 | not tagged (identifier) | ISL29125 register addresses and field bits |
| `tests/test_digital_twin_isl29125.py:14` | const | 4 | not tagged (identifier) | ISL29125 register addresses and field bits |
| `tests/test_digital_twin_isl29125.py:15` | const | 8 | not tagged (identifier) | ISL29125 register addresses and field bits |
| `tests/test_digital_twin_isl29125.py:16` | const | 9 | not tagged (identifier) | ISL29125 register addresses and field bits |
| `tests/test_digital_twin_isl29125.py:19` | const | 8 | not tagged (identifier) | ISL29125 register addresses and field bits |
| `tests/test_digital_twin_isl29125.py:20` | const | 16 | not tagged (identifier) | ISL29125 register addresses and field bits |
| `tests/test_digital_twin_isl29125.py:420` | assert | 303 | not tagged (fact) | 3 x tINT (datasheet p3, p6) |
| `tests/test_digital_twin_isl29125.py:422` | assert | 19 | not tagged (fact) | 3 x tINT (datasheet p3, p6) |
| `tests/test_digital_twin_isl29125_autorange.py:34` | const | 375 | not tagged (fact) | ISL29125 range full scales (datasheet p3) |
| `tests/test_digital_twin_isl29125_autorange.py:35` | const | 10000 | not tagged (fact) | ISL29125 range full scales (datasheet p3) |
| `tests/test_digital_twin_isl29125_autorange.py:36` | const | 26.666666666666668 | not tagged (derived) | 10000/375 |
| `tests/test_digital_twin_isl29125_autorange.py:37` | const | 25.9 | test input | the twin chip's own gain-ratio default, the value the case must learn (digital_twin/_isl29125_chip.py:76) |
| `tests/test_digital_twin_isl29125_autorange.py:41` | const-c | 0.85 | not tagged (config) | the driver's AutoRangeThresh default (85 %, a REST field; asy_isl29125_driver.py:245) |
| `tests/test_digital_twin_isl29125_autorange.py:41` | const-c | 375.0 | not tagged (fact) | low range full scale |
| `tests/test_digital_twin_launch.py:141` | assert | 2.5 | test input | parsed CLI value the case checks |
| `tests/test_digital_twin_launch.py:202` | assert | 1.5 | test input | parsed CLI value the case checks |
| `tests/test_digital_twin_launch.py:212` | kw | 0.5 | tuned | `l2.launch_short_duration_s` — real run length of main() in the short cases (one sensor-loop iteration) |
| `tests/test_digital_twin_launch.py:213` | call | 10 | tuned | `l2.launch_main_bound_s` — wait_for hang bound on main() |
| `tests/test_digital_twin_launch.py:230` | kw | 2.5 | tuned | `l2.launch_fault_duration_s` — real run length that must clear the twin's 0.7 s connect delay and one 2.0 s sensor poll (comment :219-224); Dependant of l2.twin_wifi_connect_delay_s |
| `tests/test_digital_twin_launch.py:234` | call | 10 | tuned | `l2.launch_main_bound_s` — wait_for hang bound on main() |
| `tests/test_digital_twin_launch.py:246` | kw | 0.5 | tuned | `l2.launch_short_duration_s` — real run length of main() in the short cases (one sensor-loop iteration) |
| `tests/test_digital_twin_launch.py:247` | call | 10 | tuned | `l2.launch_main_bound_s` — wait_for hang bound on main() |
| `tests/test_digital_twin_launch.py:258` | kw | 4.5 | tuned | `l2.launch_long_duration_s` — real run length past SCD30's 2 s cadence (comment :251-253) |
| `tests/test_digital_twin_launch.py:259` | call | 15 | tuned | `l2.launch_long_main_bound_s` — wait_for hang bound on the long main() run |
| `tests/test_digital_twin_machine.py:152` | assert | 212 | not tagged (fact) | first byte of the SGP40 self-test pass reply (0xD4, datasheet) the twin chip returns |
| `tests/test_digital_twin_machine.py:249` | assert | 2000000 | test input | baudrate the case sets and reads back |
| `tests/test_digital_twin_machine.py:312` | kw | 8000 | test input | construction-only timeout, never waited (A.U8.08 already classes it an input) |
| `tests/test_digital_twin_machine.py:332` | kw | 8389 | not tagged (fact) | rp2 WDT cap 8388 ms (ports/rp2/machine_wdt.c:37) and one above it |
| `tests/test_digital_twin_machine.py:339` | kw | 8388 | not tagged (fact) | rp2 WDT cap 8388 ms (ports/rp2/machine_wdt.c:37) and one above it |
| `tests/test_digital_twin_machine.py:340` | assert | 8388 | not tagged (fact) | rp2 WDT cap 8388 ms (ports/rp2/machine_wdt.c:37) and one above it |
| `tests/test_digital_twin_machine.py:344` | kw | 8000 | test input | construction-only timeout, never waited (A.U8.08 already classes it an input) |
| `tests/test_digital_twin_machine.py:357` | kw | 150 | tuned | `l2.machine_wdt_short_timeout_ms` — twin WDT timeout the case waits out on the real clock (see Register fixes: A.U8.08 calls it an input) |
| `tests/test_digital_twin_machine.py:361` | call | 5 | tuned | `l2.machine_wdt_poll_ms` — poll step of the wait for the notification |
| `tests/test_digital_twin_machine.py:364` | call | 5 | tuned | `l2.machine_run_bound_s` — wait_for hang bound, value 5 |
| `tests/test_digital_twin_machine.py:369` | kw | 100 | tuned | `l2.machine_wdt_fed_timeout_ms` — twin WDT timeout the 20 ms feeds must keep beating on the real clock |
| `tests/test_digital_twin_machine.py:371` | call | 20 | tuned | `l2.machine_feed_step_ms` — real feed interval, must stay well under _WDT_FED_TIMEOUT_MS |
| `tests/test_digital_twin_machine.py:375` | call | 5 | tuned | `l2.machine_run_bound_s` — wait_for hang bound, value 5 |
| `tests/test_digital_twin_machine.py:382` | kw | 150 | tuned | `l2.machine_wdt_short_timeout_ms` — twin WDT timeout the case waits out on the real clock (see Register fixes: A.U8.08 calls it an input) |
| `tests/test_digital_twin_machine.py:386` | call | 5 | tuned | `l2.machine_wdt_poll_ms` — poll step of the wait for the notification |
| `tests/test_digital_twin_machine.py:389` | call | 8 | tuned | `l2.machine_double_trigger_bound_s` — wait_for hang bound of the two-notification case |
| `tests/test_digital_twin_machine.py:394` | kw | 150 | tuned | `l2.machine_wdt_short_timeout_ms` — twin WDT timeout the case waits out on the real clock (see Register fixes: A.U8.08 calls it an input) |
| `tests/test_digital_twin_machine.py:400` | call | 5 | tuned | `l2.machine_wdt_poll_ms` — poll step of the wait for the notification |
| `tests/test_digital_twin_machine.py:403` | call | 5 | tuned | `l2.machine_run_bound_s` — wait_for hang bound, value 5 |
| `tests/test_digital_twin_machine.py:410` | kw | 150 | tuned | `l2.machine_wdt_short_timeout_ms` — twin WDT timeout the case waits out on the real clock (see Register fixes: A.U8.08 calls it an input) |
| `tests/test_digital_twin_machine.py:414` | call | 5 | tuned | `l2.machine_wdt_poll_ms` — poll step of the wait for the notification |
| `tests/test_digital_twin_machine.py:417` | call | 5 | tuned | `l2.machine_run_bound_s` — wait_for hang bound, value 5 |
| `tests/test_digital_twin_machine.py:460` | kw | 20 | tuned | `l2.machine_timer_period_ms` — short real timer period the fire/deinit cases run on |
| `tests/test_digital_twin_machine.py:463` | call | 60 | tuned | `l2.machine_before_deinit_ms` — real run time before deinit (must see >= 1 fire) |
| `tests/test_digital_twin_machine.py:466` | call | 80 | tuned | `l2.machine_after_deinit_ms` — real window in which no further fire may appear |
| `tests/test_digital_twin_machine.py:491` | kw | 10 | tuned | `l2.machine_chain_period_ms` — period of the self-rearming chained one-shots |
| `tests/test_digital_twin_machine.py:494` | kw | 10 | tuned | `l2.machine_chain_period_ms` — period of the self-rearming chained one-shots |
| `tests/test_digital_twin_machine.py:498` | call | 10 | tuned | `l2.machine_chain_poll_ms` — poll step of the wait for the chain |
| `tests/test_digital_twin_machine.py:501` | call | 5 | tuned | `l2.machine_run_bound_s` — wait_for hang bound, value 5 |
| `tests/test_digital_twin_machine.py:513` | kw | 1000 | test input | period of a timer deinit'ed at once, never waited |
| `tests/test_digital_twin_machine.py:525` | kw | 20 | tuned | `l2.machine_timer_period_ms` — short real timer period the fire/deinit cases run on |
| `tests/test_digital_twin_machine.py:529` | call | 20 | tuned | `l2.machine_fire_poll_ms` — poll step of the wait for the fire |
| `tests/test_digital_twin_machine.py:532` | call | 5 | tuned | `l2.machine_run_bound_s` — wait_for hang bound, value 5 |
| `tests/test_digital_twin_machine_uart.py:58` | assert | 100 | tuned | `l2.machine_uart_wire_time_floor_ms` — floor well under the ~533 ms wire time of 64 bytes at 1200 baud (comment :46-47) |
| `tests/test_digital_twin_machine_uart.py:84` | deadline | 500 | tuned | `l2.machine_uart_pump_deadline_ms` — real deadline for the byte-by-byte delivery |
| `tests/test_digital_twin_network_neopixel.py:37` | param | 5.0 | tuned | `l2.network_neopixel_wait_timeout_s` — default deadline of the two state waits |
| `tests/test_digital_twin_network_neopixel.py:40` | call | 20 | tuned | `l2.network_neopixel_poll_ms` — poll step of the two state waits |
| `tests/test_digital_twin_network_neopixel.py:45` | param | 5.0 | tuned | `l2.network_neopixel_wait_timeout_s` — default deadline of the two state waits |
| `tests/test_digital_twin_network_neopixel.py:48` | call | 20 | tuned | `l2.network_neopixel_poll_ms` — poll step of the two state waits |
| `tests/test_digital_twin_network_neopixel.py:149` | call | 1.0 | tuned | `l2.network_neopixel_never_connects_wait_s` — absence wait "longer than _CONNECT_DELAY_S"; Dependant of l2.twin_wifi_connect_delay_s |
| `tests/test_digital_twin_network_neopixel.py:251` | call | 1.0 | tuned | `l2.network_neopixel_never_connects_wait_s` — absence wait "longer than _CONNECT_DELAY_S"; Dependant of l2.twin_wifi_connect_delay_s |
| `tests/test_digital_twin_poll_prewarm.py:23` | const | 17500 | not tagged (identifier) | the test's own port band (base, width) |
| `tests/test_digital_twin_poll_prewarm.py:24` | const | 8 | not tagged (identifier) | the test's own port band (base, width) |
| `tests/test_digital_twin_real_website_integration.py:75` | call | 1.0 | deferred U25 | if kept: `l2.sensortask_integration_webserver_bind_wait_s` — fixed readiness sleep for the webserver ("~400ms, so 1.0s keeps a ~2.5x margin", :73-74); same purpose as the construction scenarios' and the sensortask integration's |
| `tests/test_digital_twin_real_website_integration.py:113` | kw | 10.0 | tuned | `l2.real_website_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_real_website_integration.py:155` | kw | 10.0 | tuned | `l2.real_website_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_real_website_integration.py:173` | kw | 10.0 | tuned | `l2.real_website_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_real_website_integration.py:192` | kw | 10.0 | tuned | `l2.real_website_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_real_website_integration.py:224` | kw | 10.0 | tuned | `l2.real_website_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_real_website_integration.py:251` | kw | 10.0 | tuned | `l2.real_website_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_real_website_integration.py:281` | kw | 10.0 | tuned | `l2.real_website_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_real_website_integration.py:300` | kw | 10.0 | tuned | `l2.real_website_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_real_website_integration.py:333` | assert | 1000 | test input | size floor that separates the real pages from an empty or truncated body (case check, not a budget) |
| `tests/test_digital_twin_real_website_integration.py:334` | assert | 1000 | test input | size floor that separates the real pages from an empty or truncated body (case check, not a budget) |
| `tests/test_digital_twin_real_website_integration.py:339` | kw | 30.0 | tuned | `l2.real_website_integration_burst_run_bound_s` — run_timed hang bound of the concurrent-tabs case |
| `tests/test_digital_twin_run_generic_integration.py:29` | param | 5.0 | tuned | `l2.run_generic_integration_run_bound_s` — run_timed()'s default hang bound |
| `tests/test_digital_twin_run_generic_integration.py:133` | assert | 25 | test input | parsed CLI value the case checks |
| `tests/test_digital_twin_run_generic_integration.py:244` | kw | 15.0 | tuned | `l2.run_generic_integration_main_run_bound_s` — run_timed hang bound on a full boot-and-shutdown main() |
| `tests/test_digital_twin_scd30.py:239` | const | 8 | not tagged (identifier) | IRQ edge constants of the local fake Pin |
| `tests/test_digital_twin_scd30.py:240` | const | 4 | not tagged (identifier) | IRQ edge constants of the local fake Pin |
| `tests/test_digital_twin_scd30.py:287` | assert | 10 | test input | the 10 s interval the case set at :285, in ms |
| `tests/test_digital_twin_scd30.py:287` | assert | 1000 | test input | the 10 s interval the case set at :285, in ms |
| `tests/test_digital_twin_sensortask_integration.py:105` | call | 1.0 | deferred U25 | if kept: `l2.sensortask_integration_webserver_bind_wait_s` — fixed readiness sleep for the webserver bind (G7/R23 twin readiness sleep); the construction scenarios and the real-website file copy it |
| `tests/test_digital_twin_sensortask_integration.py:126` | param | 5.0 | tuned | `l2.sensortask_integration_dns_query_timeout_s` — default deadline of the real DNS query |
| `tests/test_digital_twin_sensortask_integration.py:156` | call | 5 | tuned | `l2.sensortask_integration_dns_query_poll_ms` — poll step of that query's reply wait |
| `tests/test_digital_twin_sensortask_integration.py:164` | param | 0.25 | tuned | `l2.sensortask_integration_wait_poll_s` — _wait_until()'s default poll step |
| `tests/test_digital_twin_sensortask_integration.py:253` | kw | 10.0 | tuned | `l2.sensortask_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_sensortask_integration.py:272` | kw | 10.0 | tuned | `l2.sensortask_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_sensortask_integration.py:293` | kw | 10.0 | tuned | `l2.sensortask_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_sensortask_integration.py:320` | kw | 10.0 | tuned | `l2.sensortask_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_sensortask_integration.py:346` | kw | 10.0 | tuned | `l2.sensortask_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_sensortask_integration.py:378` | call | 0.5 | tuned | `l2.sensortask_integration_override_poll_s` — poll step (20 rounds) past the ~1 s override tick; Dependant of notify.loop_tick_s |
| `tests/test_digital_twin_sensortask_integration.py:391` | kw | 15.0 | tuned | `l2.sensortask_integration_long_run_bound_s` — run_timed hang bound, value 15.0 |
| `tests/test_digital_twin_sensortask_integration.py:412` | kw | 10.0 | tuned | `l2.sensortask_integration_run_bound_s` — run_timed hang bound, value 10.0 |
| `tests/test_digital_twin_sensortask_integration.py:446` | call | 1.0 | tuned | `l2.twin_wdt_feed_interval_s` — the same 1 s twin watchdog feed as digital_twin/launch.py:41 (A.U8.08's ID): shared, further site |
| `tests/test_digital_twin_sensortask_integration.py:461` | call | 9.0 | tuned | `l2.wdt_overrun_wait_s` — "just over the hardcoded 8000ms WDT timeout" |
| `tests/test_digital_twin_sensortask_integration.py:469` | kw | 15.0 | tuned | `l2.sensortask_integration_long_run_bound_s` — run_timed hang bound, value 15.0 |
| `tests/test_digital_twin_sensortask_integration.py:512` | kw | 5.0 | tuned | `l2.sensortask_integration_wait_timeout_s` — _wait_until() deadline, value 5.0 |
| `tests/test_digital_twin_sensortask_integration.py:522` | kw | 6.0 | tuned | `l2.sensortask_integration_restart_wait_timeout_s` — deadline for the supervisor to restart the dead task; Dependant of system.task_check_s |
| `tests/test_digital_twin_sensortask_integration.py:548` | kw | 20.0 | tuned | `l2.sensortask_integration_supervisor_run_bound_s` — run_timed hang bound, value 20.0 |
| `tests/test_digital_twin_sensortask_integration.py:586` | call | 0.2 | deferred U25 | if kept: `l2.sensortask_integration_connect_prefix_wait_s` — fixed sleep for wlan_connect()'s synchronous prefix before the attribute seam is set |
| `tests/test_digital_twin_sensortask_integration.py:594` | kw | 25.0 | tuned | `l2.sensortask_integration_hotspot_wait_timeout_s` — deadline for hotspot activation after the scripted last failure; Dependant of the WiFi connect timings (A.U8.10) |
| `tests/test_digital_twin_sensortask_integration.py:599` | kw | 5.0 | tuned | `l2.sensortask_integration_wait_timeout_s` — _wait_until() deadline, value 5.0 |
| `tests/test_digital_twin_sensortask_integration.py:599` | kw | 0.01 | tuned | `l2.sensortask_integration_bind_poll_s` — fine poll step of the wait for the DNS socket bind |
| `tests/test_digital_twin_sensortask_integration.py:630` | kw | 35.0 | tuned | `l2.sensortask_integration_hotspot_run_bound_s` — run_timed hang bound of the hotspot case |
| `tests/test_digital_twin_sensortask_integration.py:666` | call | 2.5 | deferred U25 | if kept: `l2.sensortask_integration_sgp40_init_wait_s` — fixed sleep: "No public init done flag exists to poll, so this is a plain, generously-bounded sleep" (:664-665) |
| `tests/test_digital_twin_sensortask_integration.py:672` | kw | 5.0 | tuned | `l2.sensortask_integration_wait_timeout_s` — _wait_until() deadline, value 5.0 |
| `tests/test_digital_twin_sensortask_integration.py:694` | call | 2.5 | deferred U25 | if kept: `l2.sensortask_integration_sgp40_init_wait_s` — fixed sleep: "No public init done flag exists to poll, so this is a plain, generously-bounded sleep" (:664-665) |
| `tests/test_digital_twin_sensortask_integration.py:696` | kw | 5.0 | tuned | `l2.sensortask_integration_wait_timeout_s` — _wait_until() deadline, value 5.0 |
| `tests/test_digital_twin_sensortask_integration.py:708` | kw | 30.0 | tuned | `l2.sensortask_integration_reboot_run_bound_s` — run_timed hang bound of the two-boot VOC backup cases |
| `tests/test_digital_twin_sensortask_integration.py:735` | call | 2.5 | deferred U25 | if kept: `l2.sensortask_integration_sgp40_init_wait_s` — fixed sleep: "No public init done flag exists to poll, so this is a plain, generously-bounded sleep" (:664-665) |
| `tests/test_digital_twin_sensortask_integration.py:738` | kw | 5.0 | tuned | `l2.sensortask_integration_wait_timeout_s` — _wait_until() deadline, value 5.0 |
| `tests/test_digital_twin_sensortask_integration.py:752` | kw | 5.0 | tuned | `l2.sensortask_integration_wait_timeout_s` — _wait_until() deadline, value 5.0 |
| `tests/test_digital_twin_sensortask_integration.py:772` | call | 2.5 | deferred U25 | if kept: `l2.sensortask_integration_sgp40_init_wait_s` — fixed sleep: "No public init done flag exists to poll, so this is a plain, generously-bounded sleep" (:664-665) |
| `tests/test_digital_twin_sensortask_integration.py:774` | kw | 5.0 | tuned | `l2.sensortask_integration_wait_timeout_s` — _wait_until() deadline, value 5.0 |
| `tests/test_digital_twin_sensortask_integration.py:781` | kw | 30.0 | tuned | `l2.sensortask_integration_reboot_run_bound_s` — run_timed hang bound of the two-boot VOC backup cases |
| `tests/test_digital_twin_sensortask_integration.py:818` | kw | 20.0 | tuned | `l2.sensortask_integration_supervisor_run_bound_s` — run_timed hang bound, value 20.0 |
| `tests/test_digital_twin_uart_link.py:48` | param | 30 | tuned | `l2.uart_link_run_limit_s` — run()'s default hang bound on the twin link (real wire time) |
| `tests/test_digital_twin_uart_link.py:103` | call | 5 | tuned | `l2.uart_link_listener_settle_s` — bound on awaiting the listener out; own ID, the twin link runs at real wire time |
| `tests/test_digital_twin_uart_link.py:169` | assert | 10 | tuned | `l2.uart_link_poll_wait_max_ms` — "single-digit, or poll latency dominates throughput": upper bound dev.uart_poll_wait_ms must stay under (Dependant of that row) |
| `tests/test_digital_twin_uart_link.py:227` | kw | 60 | tuned | `l2.uart_link_exchange_limit_s` — run() hang bound, value 60 |
| `tests/test_digital_twin_uart_link.py:231` | kw | 60 | tuned | `l2.uart_link_exchange_limit_s` — run() hang bound, value 60 |
| `tests/test_digital_twin_uart_link.py:232` | kw | 60 | tuned | `l2.uart_link_exchange_limit_s` — run() hang bound, value 60 |
| `tests/test_digital_twin_uart_link.py:252` | call | 2 | tuned | `l2.uart_link_ticker_step_ms` — pace of the co-running ticker whose progress is asserted |
| `tests/test_digital_twin_uart_link.py:261` | kw | 60 | tuned | `l2.uart_link_exchange_limit_s` — run() hang bound, value 60 |
| `tests/test_digital_twin_uart_link.py:279` | kw | 60 | tuned | `l2.uart_link_exchange_limit_s` — run() hang bound, value 60 |
| `tests/test_digital_twin_uart_link.py:297` | call | 3 | tuned | `l2.uart_link_collect_step_ms` — pace of the forced collections mid-transfer |
| `tests/test_digital_twin_uart_link.py:305` | kw | 60 | tuned | `l2.uart_link_exchange_limit_s` — run() hang bound, value 60 |
| `tests/test_digital_twin_uart_link.py:322` | call | 2 | tuned | `l2.uart_link_ticker_step_ms` — pace of the co-running ticker whose progress is asserted |
| `tests/test_digital_twin_uart_link.py:331` | kw | 240 | tuned | `l2.uart_link_max_train_limit_s` — run() hang bound of the maximum-length train |
| `tests/test_digital_twin_uart_link.py:373` | kw | 300 | tuned | `l2.uart_link_hammer_limit_s` — run() hang bound of the 120-transaction hammers |
| `tests/test_digital_twin_uart_link.py:404` | call | 1 | tuned | `l2.uart_link_churn_step_ms` — pace of the allocation churn |
| `tests/test_digital_twin_uart_link.py:418` | call | 5 | tuned | `l2.uart_link_cancel_settle_ms` — real wait for the cancelled background tasks to unwind |
| `tests/test_digital_twin_uart_link.py:420` | kw | 180 | tuned | `l2.uart_link_churn_limit_s` — run() hang bound of the heap-churn case |
| `tests/test_digital_twin_uart_link.py:466` | call | 5 | tuned | `l2.uart_link_cancel_settle_ms` — real wait for the cancelled background tasks to unwind |
| `tests/test_digital_twin_uart_link.py:469` | kw | 300 | tuned | `l2.uart_link_hammer_limit_s` — run() hang bound of the 120-transaction hammers |
| `tests/test_digital_twin_uart_link.py:482` | call | 1 | tuned | `l2.uart_link_noise_step_ms` — pace of the uptime-noise consumer |
| `tests/test_fake_timer_and_network.py:21` | kw | 1000 | test input | period of a fake Timer the case fires with trigger(); never waited |
| `tests/test_fake_timer_and_network.py:31` | kw | 1000 | test input | period of a fake Timer the case fires with trigger(); never waited |
| `tests/test_fake_timer_and_network.py:41` | kw | 1000 | test input | period of a fake Timer the case fires with trigger(); never waited |
| `tests/test_fake_timer_and_network.py:43` | kw | 1000 | test input | period of a fake Timer the case fires with trigger(); never waited |
| `tests/test_fake_timer_and_network.py:54` | kw | 1000 | test input | period of a fake Timer the case fires with trigger(); never waited |
| `tests/test_framing_codecs.py:22` | call | 5 | tuned | `l1.framing_codecs_run_bound_s` — run()'s hang bound |
| `tests/test_framing_codecs.py:194` | assert | 1 | test input | allocation count the case expects (one scratch buffer) |
| `tests/test_neopixel_wifi_integration.py:53` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — the same real overlay-commit wait as test_asy_neopixel_driver.py:88 (shared ID, further site) |
| `tests/test_neopixel_wifi_integration.py:56` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — the same real overlay-commit wait as test_asy_neopixel_driver.py:88 (shared ID, further site) |
| `tests/test_neopixel_wifi_integration.py:59` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — the same real overlay-commit wait as test_asy_neopixel_driver.py:88 (shared ID, further site) |
| `tests/test_neopixel_wifi_integration.py:83` | call | 0.05 | tuned | `l1.asy_neopixel_driver_overlay_settle_s` — the same real overlay-commit wait as test_asy_neopixel_driver.py:88 (shared ID, further site) |
| `tests/test_notification_fram_integration.py:40` | const-c | 1600 | not tagged (API domain) | the WarnCO2 REST field entry (default 1600, 0-3000) the case registers |
| `tests/test_notification_fram_integration.py:40` | const-c | 3000 | not tagged (API domain) | the WarnCO2 REST field entry (default 1600, 0-3000) the case registers |
| `tests/test_notification_neopixel_integration.py:94` | call | 1.3 | tuned | `l1.asy_notification_service_one_flash_settle_s` — "one triggered cycle's real settle time (2*0.5=1.0s) + margin"; same purpose and value as test_asy_notification_service.py:1008 (shared ID) |
| `tests/test_notification_neopixel_integration.py:120` | call | 2.5 | tuned | `l1.asy_notification_service_two_flash_cycle_s` — "both triggered cycles' settle time (2*1.0s) + margin"; shared with test_asy_notification_service.py:1322 |
| `tests/test_notification_neopixel_integration.py:145` | call | 0.1 | tuned | `l1.notification_neopixel_integration_mid_ramp_s` — real wait to land mid-animation |
| `tests/test_notification_neopixel_integration.py:147` | call | 1.5 | tuned | `l1.notification_neopixel_integration_both_ramps_done_s` — real wait for the notification ramp and the queued external one |
| `tests/test_notification_scd30_integration.py:148` | call | 1.3 | tuned | `l1.asy_notification_service_one_flash_settle_s` — one triggered cycle's settle + margin (shared ID) |
| `tests/test_notification_scd30_integration.py:176` | call | 1.3 | tuned | `l1.asy_notification_service_one_flash_settle_s` — one triggered cycle's settle + margin (shared ID) |
| `tests/test_notification_scd30_integration.py:201` | call | 0.2 | tuned | `l1.notification_scd30_integration_idle_pass_s` — "one monitor_loop() pass - nothing to settle" |
| `tests/test_notification_scd30_integration.py:253` | call | 1.3 | tuned | `l1.asy_notification_service_one_flash_settle_s` — one triggered cycle's settle + margin (shared ID) |
| `tests/test_notification_scd30_sgp40_integration.py:124` | const | 49 | not tagged (fact) | SGP40 CRC polynomial (datasheet Table 7) |
| `tests/test_notification_scd30_sgp40_integration.py:231` | call | 2.6 | tuned | `l1.notification_scd30_sgp40_integration_two_signals_done_s` — both signals' ramps in either order plus margin (comment :228-230) |
| `tests/test_notification_scd30_sgp40_integration.py:270` | call | 1.3 | tuned | `l1.asy_notification_service_one_flash_settle_s` — one triggered cycle's settle + margin (shared ID) |
| `tests/test_notification_sgp40_integration.py:68` | const | 49 | not tagged (fact) | SGP40 CRC polynomial (datasheet Table 7) |
| `tests/test_notification_sgp40_integration.py:181` | call | 1.3 | tuned | `l1.asy_notification_service_one_flash_settle_s` — one triggered cycle's settle + margin (shared ID) |
| `tests/test_notification_sgp40_integration.py:211` | call | 0.2 | tuned | `l1.notification_scd30_integration_idle_pass_s` — "one monitor_loop() pass - nothing to settle"; same as test_notification_scd30_integration.py:201 (shared ID) |
| `tests/test_notification_sgp40_integration.py:255` | call | 1.3 | tuned | `l1.asy_notification_service_one_flash_settle_s` — one triggered cycle's settle + margin (shared ID) |
| `tests/test_ntp_fram_system_integration.py:77` | param | 5000 | mirror | → `ntp.fetch_timeout_ms` — make_ntp()'s default restates the product parameter it forwards |
| `tests/test_ntp_fram_system_integration.py:161` | param | 1 | mirror | → `udp.conn_tries_default` — the double stands in for AsyUDPSocket's constructor |
| `tests/test_ntp_fram_system_integration.py:196` | call | 10 | tuned | `l1.asy_ntp_client_fake_server_poll_ms` — poll step of the same FakeNtpServer class test_asy_ntp_client.py:2087 defines (copied; shared ID) |
| `tests/test_ntp_fram_system_integration.py:200` | call | 10 | tuned | `l1.asy_ntp_client_fake_server_poll_ms` — poll step of the same FakeNtpServer class test_asy_ntp_client.py:2087 defines (copied; shared ID) |
| `tests/test_ntp_fram_system_integration.py:206` | const | 2208988800 | not tagged (fact) | NTP-to-Unix epoch offset (RFC 5905) |
| `tests/test_ntp_fram_system_integration.py:230` | call | 5 | tuned | `l1.asy_ntp_client_serve_wait_s` — wait_for bound on the fake server's exchange (shared ID) |
| `tests/test_ntp_fram_system_integration.py:234` | call | 20 | tuned | `l1.asy_ntp_client_state_poll_ms` — poll step of the wait for the synced state (shared ID) |
| `tests/test_ntp_fram_system_integration.py:263` | assert | 5 | tuned | `l1.ntp_fram_system_integration_utc_tolerance_s` — tolerance between the NTP-derived stamp and the host clock |
| `tests/test_ntp_fram_system_integration.py:313` | kw | 2000 | tuned | `l1.fram_lock_fetch_timeout_ms` — the 2000 ms lock-hold fetch timeout |
| `tests/test_ntp_fram_system_integration.py:329` | call | 1.0 | tuned | `l1.fram_write_prompt_s` — the 0.2 -> 1.0 s "completes promptly" bound |
| `tests/test_ntp_fram_system_integration.py:360` | assert | 5 | tuned | `l1.ntp_fram_system_integration_utc_tolerance_s` — tolerance between the NTP-derived stamp and the host clock |
| `tests/test_ntp_fram_system_integration.py:443` | call | 2.5 | tuned | `l1.ntp_fram_system_integration_supervisor_scan_wait_s` — "real wall-clock wait for start_and_check_tasks()'s own 2s poll"; Dependant of system.task_check_s (2.5 is not its value, so not a mirror) |
| `tests/test_ntp_fram_system_integration.py:548` | call | 0.01 | tuned | `l1.ntp_fram_system_integration_start_poll_s` — poll step of the wait for the first start to end |
| `tests/test_ntp_fram_system_integration.py:550` | call | 2.5 | tuned | `l1.ntp_fram_system_integration_supervisor_scan_wait_s` — "real wall-clock wait for start_and_check_tasks()'s own 2s poll"; Dependant of system.task_check_s (2.5 is not its value, so not a mirror) |
| `tests/test_ntp_fram_system_integration.py:612` | call | 0.01 | tuned | `l1.ntp_fram_system_integration_start_poll_s` — poll step of the wait for the first start to end |
| `tests/test_ntp_fram_system_integration.py:614` | call | 2.5 | tuned | `l1.ntp_fram_system_integration_supervisor_scan_wait_s` — "real wall-clock wait for start_and_check_tasks()'s own 2s poll"; Dependant of system.task_check_s (2.5 is not its value, so not a mirror) |
| `tests/test_ntp_fram_system_integration.py:642` | call | 0.01 | tuned | `l1.ntp_fram_system_integration_start_poll_s` — poll step of the wait for the first start to end |
| `tests/test_ntp_fram_system_integration.py:644` | call | 2.5 | tuned | `l1.ntp_fram_system_integration_supervisor_scan_wait_s` — "real wall-clock wait for start_and_check_tasks()'s own 2s poll"; Dependant of system.task_check_s (2.5 is not its value, so not a mirror) |
| `tests/test_ntp_wifi_dns_integration.py:229` | call | 0.05 | tuned | `l1.ntp_wifi_dns_integration_lock_blocked_wait_s` — wait_for window waited out while the WiFi-mode lock is held |
| `tests/test_ntp_wifi_dns_integration.py:274` | param | 1 | mirror | → `udp.conn_tries_default` — the double stands in for AsyUDPSocket's constructor |
| `tests/test_ntp_wifi_dns_integration.py:312` | call | 10 | tuned | `l1.asy_ntp_client_fake_server_poll_ms` — poll step of the copied FakeNtpServer (shared ID) |
| `tests/test_ntp_wifi_dns_integration.py:316` | call | 10 | tuned | `l1.asy_ntp_client_fake_server_poll_ms` — poll step of the copied FakeNtpServer (shared ID) |
| `tests/test_ntp_wifi_dns_integration.py:322` | const | 2208988800 | not tagged (fact) | NTP-to-Unix epoch offset (RFC 5905) |
| `tests/test_ntp_wifi_dns_integration.py:347` | call | 5 | tuned | `l1.asy_ntp_client_serve_wait_s` — wait_for bound on the fake server's exchange (shared ID) |
| `tests/test_ntp_wifi_dns_integration.py:351` | call | 20 | tuned | `l1.asy_ntp_client_state_poll_ms` — poll step of the wait for the synced state (shared ID) |
| `tests/test_ntp_wifi_dns_integration.py:379` | kw | 100 | tuned | `l1.asy_ntp_client_no_reply_fetch_timeout_ms` — the short fetch timeout the no-reply cases wait out (shared ID) |
| `tests/test_ntp_wifi_dns_integration.py:388` | call | 150 | tuned | `l1.ntp_wifi_dns_integration_past_fetch_timeout_ms` — per-cycle wait past the 100 ms fetch timeout; Dependant of l1.asy_ntp_client_no_reply_fetch_timeout_ms |
| `tests/test_setter_microdot_integration.py:700` | const-c | 2 | not tagged (API domain) | restates SCD30 REST field entries (MeasInt 2-1800, AmbPres 700-1400, ForceCalRef 400-2000) |
| `tests/test_setter_microdot_integration.py:700` | const-c | 1800 | not tagged (API domain) | restates SCD30 REST field entries (MeasInt 2-1800, AmbPres 700-1400, ForceCalRef 400-2000) |
| `tests/test_setter_microdot_integration.py:702` | const-c | 700 | not tagged (API domain) | restates SCD30 REST field entries (MeasInt 2-1800, AmbPres 700-1400, ForceCalRef 400-2000) |
| `tests/test_setter_microdot_integration.py:702` | const-c | 1400 | not tagged (API domain) | restates SCD30 REST field entries (MeasInt 2-1800, AmbPres 700-1400, ForceCalRef 400-2000) |
| `tests/test_setter_microdot_integration.py:703` | const-c | 400 | not tagged (API domain) | restates SCD30 REST field entries (MeasInt 2-1800, AmbPres 700-1400, ForceCalRef 400-2000) |
| `tests/test_setter_microdot_integration.py:703` | const-c | 2000 | not tagged (API domain) | restates SCD30 REST field entries (MeasInt 2-1800, AmbPres 700-1400, ForceCalRef 400-2000) |
| `tests/test_system_service.py:623` | assert | 4 | mirror | → `system.reset_delay_s` — "_RESET_DELAY: micropython.const(), compiled away, hardcoded" (A.U8.08 names this site); 1000 is the s-to-ms scale |
| `tests/test_system_service.py:623` | assert | 1000 | mirror | → `system.reset_delay_s` — "_RESET_DELAY: micropython.const(), compiled away, hardcoded" (A.U8.08 names this site); 1000 is the s-to-ms scale |
| `tests/test_system_service.py:733` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_system_service.py:754` | assert | 3600 | not tagged (API domain) | _MAX_STORAGE_PAUSE (1 h, the mempause REST maximum; U8 Appendix A: API domain) x 1000 |
| `tests/test_system_service.py:754` | assert | 1000 | not tagged (API domain) | _MAX_STORAGE_PAUSE (1 h, the mempause REST maximum; U8 Appendix A: API domain) x 1000 |
| `tests/test_system_service.py:761` | assert | 3600 | not tagged (API domain) | _MAX_STORAGE_PAUSE (1 h, the mempause REST maximum; U8 Appendix A: API domain) x 1000 |
| `tests/test_system_service.py:761` | assert | 1000 | not tagged (API domain) | _MAX_STORAGE_PAUSE (1 h, the mempause REST maximum; U8 Appendix A: API domain) x 1000 |
| `tests/test_system_service.py:769` | assert | 60 | test input | pause duration the case passed, x 1000 |
| `tests/test_system_service.py:769` | assert | 1000 | test input | pause duration the case passed, x 1000 |
| `tests/test_system_service.py:782` | assert | 120 | test input | pause duration the case passed, x 1000 |
| `tests/test_system_service.py:782` | assert | 1000 | test input | pause duration the case passed, x 1000 |
| `tests/test_system_service.py:845` | assert | 1000 | not tagged (derived) | the 1 s uptime tick (system_service.py:204 period=1000, a unit) |
| `tests/test_system_service.py:857` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_system_service.py:868` | assert | -1 | not tagged (identifier) | "never armed" sentinel of the fake Timer |
| `tests/test_system_service.py:972` | call | 3600 | test input | long-lived task stand-in, cancelled by the case |
| `tests/test_system_service.py:1033` | call | 3600 | test input | long-lived task stand-in, cancelled by the case |
| `tests/test_system_service.py:1062` | call | 3600 | test input | long-lived task stand-in, cancelled by the case |
| `tests/test_system_service.py:1086` | call | 3600 | test input | long-lived task stand-in, cancelled by the case |
| `tests/test_system_service.py:1146` | call | 3600 | test input | long-lived task stand-in, cancelled by the case |
| `tests/test_system_service.py:1184` | call | 3600 | test input | long-lived task stand-in, cancelled by the case |
| `tests/test_system_service.py:1249` | call | 5 | tuned | `l1.system_service_run_bound_s` — wait_for hang bound (real clock even with sleep patched) |
| `tests/test_ticks_rollover.py:62` | deadline | 200 | test input | synthetic tick values around the wrap, computed by the case; no real wait |
| `tests/test_ticks_rollover.py:63` | assert | 200 | test input | synthetic tick values around the wrap, computed by the case; no real wait |
| `tests/test_ticks_rollover.py:70` | deadline | 5 | test input | synthetic tick values around the wrap, computed by the case; no real wait |
| `tests/test_ticks_rollover.py:72` | assert | -55 | test input | synthetic tick values around the wrap, computed by the case; no real wait |
| `tests/test_ticks_rollover.py:81` | assert | 300 | test input | synthetic tick values around the wrap, computed by the case; no real wait |
| `tests/test_ticks_rollover.py:89` | deadline | 150 | test input | synthetic tick values around the wrap, computed by the case; no real wait |
| `tests/test_ticks_rollover.py:90` | assert | 100 | test input | synthetic tick values around the wrap, computed by the case; no real wait |
| `tests/test_ticks_rollover.py:91` | assert | 200 | test input | synthetic tick values around the wrap, computed by the case; no real wait |
| `tests/test_uart_comm_hazard.py:33` | const | 30 | tuned | `l1.uart_comm_hazard_timeout_ms` — the tier's short reply timeout, waited out in every recovery case (derivation in its comment :29-31: over the 24 ms floor); the x8 CRC and sustained budgets derive from it |
| `tests/test_uart_comm_hazard.py:34` | const | 8 | test input | payload size chosen for the hazard pair |
| `tests/test_uart_comm_hazard.py:40` | const | 0 | not tagged (identifier) | frame-header field indices |
| `tests/test_uart_comm_hazard.py:42` | const | 2 | not tagged (identifier) | frame-header field indices |
| `tests/test_uart_comm_hazard.py:43` | const | 3 | not tagged (identifier) | frame-header field indices |
| `tests/test_uart_comm_hazard.py:44` | const | 4 | not tagged (identifier) | frame-header field indices |
| `tests/test_uart_comm_hazard.py:45` | const | 5 | not tagged (identifier) | frame-header field indices |
| `tests/test_uart_comm_hazard.py:109` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:128` | call | 8 | tuned | `l1.uart_comm_hazard_task_bound_s` — wait_for hang bound, value 8 |
| `tests/test_uart_comm_hazard.py:129` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:133` | kw | 25 | tuned | `l1.uart_comm_hazard_concurrency_limit_s` — run() hang bound, value 25 |
| `tests/test_uart_comm_hazard.py:148` | call | 1 | tuned | `l1.uart_comm_hazard_lock_take_ms` — "let the first take the lock" |
| `tests/test_uart_comm_hazard.py:150` | call | 8 | tuned | `l1.uart_comm_hazard_task_bound_s` — wait_for hang bound, value 8 |
| `tests/test_uart_comm_hazard.py:151` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:155` | kw | 25 | tuned | `l1.uart_comm_hazard_concurrency_limit_s` — run() hang bound, value 25 |
| `tests/test_uart_comm_hazard.py:173` | call | 2 | tuned | `l1.uart_comm_hazard_in_flight_ms` — real wait for the first transaction to be in flight |
| `tests/test_uart_comm_hazard.py:174` | call | 8 | tuned | `l1.uart_comm_hazard_task_bound_s` — wait_for hang bound, value 8 |
| `tests/test_uart_comm_hazard.py:175` | call | 8 | tuned | `l1.uart_comm_hazard_task_bound_s` — wait_for hang bound, value 8 |
| `tests/test_uart_comm_hazard.py:176` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:181` | kw | 25 | tuned | `l1.uart_comm_hazard_concurrency_limit_s` — run() hang bound, value 25 |
| `tests/test_uart_comm_hazard.py:193` | call | 5 | tuned | `l1.uart_comm_hazard_listener_park_ms` — real wait for the listener to park before clear() |
| `tests/test_uart_comm_hazard.py:194` | call | 8 | tuned | `l1.uart_comm_hazard_task_bound_s` — wait_for hang bound, value 8 |
| `tests/test_uart_comm_hazard.py:198` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:221` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:225` | kw | 25 | tuned | `l1.uart_comm_hazard_concurrency_limit_s` — run() hang bound, value 25 |
| `tests/test_uart_comm_hazard.py:311` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:328` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:337` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:354` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:359` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:363` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:376` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:381` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:385` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:397` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:401` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:405` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:418` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:423` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:427` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:440` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:445` | call | 5 | tuned | `l1.uart_comm_hazard_listener_settle_ms` — real wait before cancelling the listener after an exchange |
| `tests/test_uart_comm_hazard.py:449` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:457` | const | 20 | tuned | `l1.uart_comm_hazard_warmup_rounds` — warm-up transactions before the retention sample |
| `tests/test_uart_comm_hazard.py:458` | const | 100 | tuned | `l1.uart_comm_hazard_measured_rounds` — transactions the per-transaction retention rate is averaged over |
| `tests/test_uart_comm_hazard.py:531` | kw | 120 | tuned | `l1.uart_comm_hazard_retention_limit_s` — run() hang bound, value 120 |
| `tests/test_uart_comm_hazard.py:570` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:583` | call | 5 | tuned | `l1.uart_comm_hazard_listener_park_ms` — real wait for the listener to park before clear() |
| `tests/test_uart_comm_hazard.py:585` | call | 5 | tuned | `l1.uart_comm_hazard_step_bound_s` — hang bound, value 5 (wait_for and limit= share it) |
| `tests/test_uart_comm_hazard.py:587` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:597` | call | 2 | tuned | `l1.uart_comm_hazard_in_flight_ms` — real wait for the first transaction to be in flight |
| `tests/test_uart_comm_hazard.py:599` | call | 5 | tuned | `l1.uart_comm_hazard_step_bound_s` — hang bound, value 5 (wait_for and limit= share it) |
| `tests/test_uart_comm_hazard.py:601` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:609` | kw | 5 | tuned | `l1.uart_comm_hazard_step_bound_s` — hang bound, value 5 (wait_for and limit= share it) |
| `tests/test_uart_comm_hazard.py:618` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:628` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:637` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:654` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:658` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:659` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:660` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:670` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:673` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:674` | kw | 10 | tuned | `l1.uart_comm_hazard_limit_s` — run() hang bound, value 10 |
| `tests/test_uart_comm_hazard.py:675` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:690` | call | 3 | tuned | `l1.uart_comm_hazard_fragment_gap_ms` — how long the delayed bytes are held mid-transaction |
| `tests/test_uart_comm_hazard.py:693` | call | 5 | tuned | `l1.uart_comm_hazard_step_bound_s` — hang bound, value 5 (wait_for and limit= share it) |
| `tests/test_uart_comm_hazard.py:694` | call | 5 | tuned | `l1.uart_comm_hazard_step_bound_s` — hang bound, value 5 (wait_for and limit= share it) |
| `tests/test_uart_comm_hazard.py:697` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:716` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:725` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:749` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:777` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:788` | kw | 1 | test input | construction-only case: the refused comm never waits |
| `tests/test_uart_comm_hazard.py:826` | call | 5 | tuned | `l1.uart_comm_hazard_step_bound_s` — hang bound, value 5 (wait_for and limit= share it) |
| `tests/test_uart_comm_hazard.py:832` | kw | 60 | tuned | `l1.uart_comm_hazard_mismatch_limit_s` — run() hang bound, value 60 |
| `tests/test_uart_comm_hazard.py:849` | call | 5 | tuned | `l1.uart_comm_hazard_step_bound_s` — hang bound, value 5 (wait_for and limit= share it) |
| `tests/test_uart_comm_hazard.py:853` | kw | 120 | tuned | `l1.uart_comm_hazard_retention_limit_s` — run() hang bound, value 120 |
| `tests/test_uart_comm_hazard.py:871` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:872` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:891` | call | 5 | tuned | `l1.uart_comm_hazard_step_bound_s` — hang bound, value 5 (wait_for and limit= share it) |
| `tests/test_uart_comm_hazard.py:909` | kw | 120 | tuned | `l1.uart_comm_hazard_retention_limit_s` — run() hang bound, value 120 |
| `tests/test_uart_comm_hazard.py:918` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:919` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:923` | kw | 60 | tuned | `l1.uart_comm_hazard_mismatch_limit_s` — run() hang bound, value 60 |
| `tests/test_uart_comm_hazard.py:970` | kw | 60 | tuned | `l1.uart_comm_hazard_mismatch_limit_s` — run() hang bound, value 60 |
| `tests/test_uart_comm_hazard.py:973` | kw | 60 | tuned | `l1.uart_comm_hazard_mismatch_limit_s` — run() hang bound, value 60 |
| `tests/test_uart_comm_hazard.py:975` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:976` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:980` | kw | 60 | tuned | `l1.uart_comm_hazard_mismatch_limit_s` — run() hang bound, value 60 |
| `tests/test_uart_comm_hazard.py:993` | const | 150 | tuned | `l1.uart_comm_hazard_hammer_rounds` — length of the sustained hammer (the sample point and measured span derive from it) |
| `tests/test_uart_comm_hazard.py:1026` | kw | 300 | tuned | `l1.uart_comm_hazard_hammer_limit_s` — run() hang bound of the hammers |
| `tests/test_uart_comm_hazard.py:1072` | kw | 300 | tuned | `l1.uart_comm_hazard_hammer_limit_s` — run() hang bound of the hammers |
| `tests/test_uart_comm_hazard.py:1080` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:1081` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:1084` | kw | 60 | tuned | `l1.uart_comm_hazard_mismatch_limit_s` — run() hang bound, value 60 |
| `tests/test_uart_comm_hazard.py:1101` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:1135` | call | 5 | tuned | `l1.uart_comm_hazard_step_bound_s` — hang bound, value 5 (wait_for and limit= share it) |
| `tests/test_uart_comm_hazard.py:1141` | kw | 60 | tuned | `l1.uart_comm_hazard_mismatch_limit_s` — run() hang bound, value 60 |
| `tests/test_uart_comm_hazard.py:1163` | call | 5 | tuned | `l1.uart_comm_hazard_step_bound_s` — hang bound, value 5 (wait_for and limit= share it) |
| `tests/test_uart_comm_hazard.py:1167` | kw | 60 | tuned | `l1.uart_comm_hazard_mismatch_limit_s` — run() hang bound, value 60 |
| `tests/test_uart_comm_hazard.py:1176` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:1188` | call | 5 | tuned | `l1.uart_comm_hazard_step_bound_s` — hang bound, value 5 (wait_for and limit= share it) |
| `tests/test_uart_comm_hazard.py:1192` | kw | 60 | tuned | `l1.uart_comm_hazard_mismatch_limit_s` — run() hang bound, value 60 |
| `tests/test_uart_comm_hazard.py:1206` | kw | 60 | tuned | `l1.uart_comm_hazard_mismatch_limit_s` — run() hang bound, value 60 |
| `tests/test_uart_comm_hazard.py:1211` | kw | 30 | tuned | `l1.uart_comm_hazard_recovery_limit_s` — run() hang bound, value 30 |
| `tests/test_uart_comm_hazard.py:1215` | kw | 60 | tuned | `l1.uart_comm_hazard_mismatch_limit_s` — run() hang bound, value 60 |
| `tests/test_uart_comm_hazard.py:1229` | kw | 20 | tuned | `l1.uart_comm_hazard_exchange_limit_s` — run() hang bound, value 20 |
| `tests/test_uart_comm_hazard.py:1247` | const-c | -1 | not tagged (fact) | gc.threshold(-1), MicroPython's own reactive default |
| `tests/test_uart_comm_hazard.py:1247` | const-c | 32768 | mirror | → `gc.threshold_bytes` — the project's chosen threshold (A.U8.14 names this site) |
| `tests/test_voc_algorithm.py:86` | assert | 45 | not tagged (fact) | the algorithm's 45 s initial blackout in its Q16 scale (voc_algorithm.py:15) |
| `tests/test_voc_algorithm.py:86` | assert | 65536 | not tagged (fact) | the algorithm's 45 s initial blackout in its Q16 scale (voc_algorithm.py:15) |
| `tests/test_voc_algorithm.py:558` | kw | 180.0 | not tagged (fact) | Sensirion's default gating_max_duration_minutes (180) passed to the algorithm's own setter |
| `tests_hardware/bench/dns_probe.py:11` | const | 53 | not tagged (identifier) | DNS port 53 |
| `tests_hardware/bench/dns_probe.py:27` | param | 5.0 | tuned | `l4.dns_probe_query_timeout_s` — default reply deadline of the bench DNS probe |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:27` | const | 8 | tuned | `l4.bus_concurrency_under_api_load_get_iterations` — load volume per GET worker |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:28` | const | 2 | tuned | `l4.bus_concurrency_under_api_load_put_reset_count` — number of concurrent reset PUTs |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:42` | param | 15.0 | tuned | `l4.bus_concurrency_under_api_load_fetch_timeout_s` — per-request timeout of the load workers (the helper's default; the explicit 15.0 calls share it) |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:54` | call | 0.25 | tuned | `l4.bus_concurrency_under_api_load_ceiling_retry_backoff_s` — pause before retrying a connection-ceiling refusal |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:94` | kw | 15.0 | tuned | `l4.bus_concurrency_under_api_load_fetch_timeout_s` — as :42 |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:107` | kw | 15.0 | tuned | `l4.bus_concurrency_under_api_load_fetch_timeout_s` — as :42 |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:119` | kw | 120.0 | tuned | `l4.bus_concurrency_under_api_load_join_timeout_s` — join bound on the load threads |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:128` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:129` | call | 30.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_timeout_s` — deadline of a wait_until recovery/precondition check |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:129` | kw | 30.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_timeout_s` — deadline of a wait_until recovery/precondition check |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:130` | call | 2.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:130` | kw | 2.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:142` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:175` | kw | 20.0 | tuned | `l4.bus_concurrency_under_api_load_degraded_fetch_timeout_s` — per-request timeout under injected loss/latency or an outage |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:186` | kw | 20.0 | tuned | `l4.bus_concurrency_under_api_load_degraded_fetch_timeout_s` — per-request timeout under injected loss/latency or an outage |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:194` | kw | 30 | test input | injected fault environment (netem loss 2 %, delay 30 ms, jitter 20 ms): the stimulus, not a budget (see Open points) |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:194` | kw | 20 | test input | injected fault environment (netem loss 2 %, delay 30 ms, jitter 20 ms): the stimulus, not a budget (see Open points) |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:201` | kw | 180.0 | tuned | `l4.bus_concurrency_under_api_load_degraded_join_timeout_s` — join bound under degradation ("generous over the plain-load test's 120s", :201) |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:211` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:212` | call | 30.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_timeout_s` — deadline of a wait_until recovery/precondition check |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:212` | kw | 30.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_timeout_s` — deadline of a wait_until recovery/precondition check |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:213` | call | 2.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:213` | kw | 2.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:232` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:237` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:242` | call | 30.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_timeout_s` — deadline of a wait_until recovery/precondition check |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:242` | call | 2.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:242` | kw | 30.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_timeout_s` — deadline of a wait_until recovery/precondition check |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:242` | kw | 2.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:255` | kw | 20.0 | tuned | `l4.bus_concurrency_under_api_load_degraded_fetch_timeout_s` — per-request timeout under injected loss/latency or an outage |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:266` | kw | 20.0 | tuned | `l4.bus_concurrency_under_api_load_degraded_fetch_timeout_s` — per-request timeout under injected loss/latency or an outage |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:278` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:288` | kw | 180.0 | tuned | `l4.bus_concurrency_under_api_load_degraded_join_timeout_s` — join bound under degradation ("generous over the plain-load test's 120s", :201) |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:297` | call | 20.0 | tuned | `l4.bus_concurrency_under_api_load_ntp_resync_timeout_s` — deadline for NTP to resync after the transient outage |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:297` | call | 1.0 | tuned | `l4.bus_concurrency_under_api_load_ntp_resync_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:297` | kw | 20.0 | tuned | `l4.bus_concurrency_under_api_load_degraded_fetch_timeout_s` — per-request timeout under injected loss/latency or an outage |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:297` | kw | 1.0 | tuned | `l4.bus_concurrency_under_api_load_ntp_resync_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:324` | kw | 20.0 | tuned | `l4.bus_concurrency_under_api_load_degraded_fetch_timeout_s` — per-request timeout under injected loss/latency or an outage |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:335` | kw | 20.0 | tuned | `l4.bus_concurrency_under_api_load_degraded_fetch_timeout_s` — per-request timeout under injected loss/latency or an outage |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:348` | call | 3.0 | tuned | `l4.network_resilience_flap_step_s` — "Same 3x(3s down/3s up) shape as test_network_resilience.py's flapping test" (:344-345): shared ID |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:350` | call | 3.0 | tuned | `l4.network_resilience_flap_step_s` — "Same 3x(3s down/3s up) shape as test_network_resilience.py's flapping test" (:344-345): shared ID |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:358` | kw | 180.0 | tuned | `l4.bus_concurrency_under_api_load_degraded_join_timeout_s` — join bound under degradation ("generous over the plain-load test's 120s", :201) |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:367` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:368` | call | 150.0 | tuned | `l4.bus_concurrency_under_api_load_flap_recovery_timeout_s` — deadline to serve again after the flapping |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:368` | kw | 150.0 | tuned | `l4.bus_concurrency_under_api_load_flap_recovery_timeout_s` — deadline to serve again after the flapping |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:369` | call | 5.0 | tuned | `l4.bus_concurrency_under_api_load_flap_recovery_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:369` | kw | 5.0 | tuned | `l4.bus_concurrency_under_api_load_flap_recovery_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:378` | call | 60.0 | tuned | `l4.bus_concurrency_under_api_load_reboot_ready_timeout_s` — deadline to serve after the hard reset |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:378` | call | 3.0 | tuned | `l4.bus_concurrency_under_api_load_reboot_ready_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:378` | kw | 60.0 | tuned | `l4.bus_concurrency_under_api_load_reboot_ready_timeout_s` — deadline to serve after the hard reset |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:378` | kw | 3.0 | tuned | `l4.bus_concurrency_under_api_load_reboot_ready_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:378` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:394` | const-c | 12 | not tagged (API domain) | the ISL29125 Resolution field's two valid values (asy_isl29125_driver.py _RESOLUTIONS) |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:394` | const-c | 16 | not tagged (API domain) | the ISL29125 Resolution field's two valid values (asy_isl29125_driver.py _RESOLUTIONS) |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:395` | const | 4 | tuned | `l4.bus_concurrency_under_api_load_isl29125_write_cycles` — ISL29125 config-write cycles ("modest relative to flash tier's 8") |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:402` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:416` | kw | 15.0 | tuned | `l4.bus_concurrency_under_api_load_fetch_timeout_s` — as :42 |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:437` | kw | 15.0 | tuned | `l4.bus_concurrency_under_api_load_fetch_timeout_s` — as :42 |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:450` | kw | 120.0 | tuned | `l4.bus_concurrency_under_api_load_join_timeout_s` — join bound on the load threads |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:456` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:464` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:465` | call | 30.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_timeout_s` — deadline of a wait_until recovery/precondition check |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:465` | kw | 30.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_timeout_s` — deadline of a wait_until recovery/precondition check |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:466` | call | 2.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:466` | kw | 2.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:485` | const-c | 1 | not tagged (API domain) | two valid BMP3xx oversampling values (asy_bmp3xx_driver.py _OSR_SETTINGS) |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:485` | const-c | 2 | not tagged (API domain) | two valid BMP3xx oversampling values (asy_bmp3xx_driver.py _OSR_SETTINGS) |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:492` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:506` | kw | 15.0 | tuned | `l4.bus_concurrency_under_api_load_fetch_timeout_s` — as :42 |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:528` | kw | 15.0 | tuned | `l4.bus_concurrency_under_api_load_fetch_timeout_s` — as :42 |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:541` | kw | 120.0 | tuned | `l4.bus_concurrency_under_api_load_join_timeout_s` — join bound on the load threads |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:545` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:551` | kw | 10.0 | tuned | `l4.bus_concurrency_under_api_load_probe_timeout_s` — HTTP timeout of a status/precondition/restore request |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:552` | call | 30.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_timeout_s` — deadline of a wait_until recovery/precondition check |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:552` | kw | 30.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_timeout_s` — deadline of a wait_until recovery/precondition check |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:553` | call | 2.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_bus_concurrency_under_api_load.py:553` | kw | 2.0 | tuned | `l4.bus_concurrency_under_api_load_recovery_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_end_to_end_timing.py:40` | call | 30.0 | tuned | `l4.end_to_end_timing_reboot_phase_timeout_s` — deadline of each reboot phase (down, up, serving) |
| `tests_hardware/bench/test_end_to_end_timing.py:40` | call | 0.5 | tuned | `l4.end_to_end_timing_down_poll_s` — poll step of the wait for the board to go away |
| `tests_hardware/bench/test_end_to_end_timing.py:40` | kw | 30.0 | tuned | `l4.end_to_end_timing_reboot_phase_timeout_s` — deadline of each reboot phase (down, up, serving) |
| `tests_hardware/bench/test_end_to_end_timing.py:40` | kw | 0.5 | tuned | `l4.end_to_end_timing_down_poll_s` — poll step of the wait for the board to go away |
| `tests_hardware/bench/test_end_to_end_timing.py:41` | call | 30.0 | tuned | `l4.end_to_end_timing_reboot_phase_timeout_s` — deadline of each reboot phase (down, up, serving) |
| `tests_hardware/bench/test_end_to_end_timing.py:41` | call | 1.0 | tuned | `l4.end_to_end_timing_poll_s` — poll step of the reachability / fetch-ok waits |
| `tests_hardware/bench/test_end_to_end_timing.py:41` | kw | 30.0 | tuned | `l4.end_to_end_timing_reboot_phase_timeout_s` — deadline of each reboot phase (down, up, serving) |
| `tests_hardware/bench/test_end_to_end_timing.py:41` | kw | 1.0 | tuned | `l4.end_to_end_timing_poll_s` — poll step of the reachability / fetch-ok waits |
| `tests_hardware/bench/test_end_to_end_timing.py:46` | kw | 5.0 | tuned | `l4.end_to_end_timing_ready_probe_timeout_s` — per-probe HTTP timeout of a readiness check |
| `tests_hardware/bench/test_end_to_end_timing.py:49` | call | 30.0 | tuned | `l4.end_to_end_timing_reboot_phase_timeout_s` — deadline of each reboot phase (down, up, serving) |
| `tests_hardware/bench/test_end_to_end_timing.py:49` | call | 2.0 | tuned | `l4.end_to_end_timing_serving_poll_s` — poll step of the serving waits |
| `tests_hardware/bench/test_end_to_end_timing.py:49` | kw | 30.0 | tuned | `l4.end_to_end_timing_reboot_phase_timeout_s` — deadline of each reboot phase (down, up, serving) |
| `tests_hardware/bench/test_end_to_end_timing.py:49` | kw | 2.0 | tuned | `l4.end_to_end_timing_serving_poll_s` — poll step of the serving waits |
| `tests_hardware/bench/test_end_to_end_timing.py:53` | call | 30.0 | tuned | `l4.end_to_end_timing_reboot_phase_timeout_s` — deadline of each reboot phase (down, up, serving) |
| `tests_hardware/bench/test_end_to_end_timing.py:53` | call | 2.0 | tuned | `l4.end_to_end_timing_serving_poll_s` — poll step of the serving waits |
| `tests_hardware/bench/test_end_to_end_timing.py:53` | kw | 30.0 | tuned | `l4.end_to_end_timing_reboot_phase_timeout_s` — deadline of each reboot phase (down, up, serving) |
| `tests_hardware/bench/test_end_to_end_timing.py:53` | kw | 2.0 | tuned | `l4.end_to_end_timing_serving_poll_s` — poll step of the serving waits |
| `tests_hardware/bench/test_end_to_end_timing.py:72` | kw | 10.0 | tuned | `l4.end_to_end_timing_probe_timeout_s` — HTTP timeout of a status/sensors/PUT request |
| `tests_hardware/bench/test_end_to_end_timing.py:81` | kw | 15.0 | tuned | `l4.end_to_end_timing_join_timeout_s` — join bound on the concurrent GET threads |
| `tests_hardware/bench/test_end_to_end_timing.py:88` | kw | 10.0 | tuned | `l4.end_to_end_timing_probe_timeout_s` — HTTP timeout of a status/sensors/PUT request |
| `tests_hardware/bench/test_end_to_end_timing.py:105` | call | 120.0 | tuned | `l4.end_to_end_timing_recovery_sanity_timeout_s` — "generous sanity ceiling, not a validated tight budget" |
| `tests_hardware/bench/test_end_to_end_timing.py:105` | kw | 120.0 | tuned | `l4.end_to_end_timing_recovery_sanity_timeout_s` — "generous sanity ceiling, not a validated tight budget" |
| `tests_hardware/bench/test_end_to_end_timing.py:106` | call | 1.0 | tuned | `l4.end_to_end_timing_poll_s` — poll step of the reachability / fetch-ok waits |
| `tests_hardware/bench/test_end_to_end_timing.py:106` | kw | 1.0 | tuned | `l4.end_to_end_timing_poll_s` — poll step of the reachability / fetch-ok waits |
| `tests_hardware/bench/test_end_to_end_timing.py:115` | kw | 5.0 | tuned | `l4.end_to_end_timing_ready_probe_timeout_s` — per-probe HTTP timeout of a readiness check |
| `tests_hardware/bench/test_end_to_end_timing.py:130` | kw | 10.0 | tuned | `l4.end_to_end_timing_probe_timeout_s` — HTTP timeout of a status/sensors/PUT request |
| `tests_hardware/bench/test_end_to_end_timing.py:136` | kw | 10.0 | tuned | `l4.end_to_end_timing_probe_timeout_s` — HTTP timeout of a status/sensors/PUT request |
| `tests_hardware/bench/test_end_to_end_timing.py:143` | call | 25.0 | tuned | `l4.end_to_end_timing_reset_spacing_s` — spacing that spreads the three resets across the 60 s backup cadence (BackupPeriod=1 min set at :136) |
| `tests_hardware/bench/test_end_to_end_timing.py:153` | call | 60.0 | tuned | `l4.end_to_end_timing_reset_recovery_timeout_s` — deadline to serve again after each reset |
| `tests_hardware/bench/test_end_to_end_timing.py:153` | kw | 60.0 | tuned | `l4.end_to_end_timing_reset_recovery_timeout_s` — deadline to serve again after each reset |
| `tests_hardware/bench/test_end_to_end_timing.py:154` | call | 1.0 | tuned | `l4.end_to_end_timing_poll_s` — poll step of the reachability / fetch-ok waits |
| `tests_hardware/bench/test_end_to_end_timing.py:154` | kw | 1.0 | tuned | `l4.end_to_end_timing_poll_s` — poll step of the reachability / fetch-ok waits |
| `tests_hardware/bench/test_end_to_end_timing.py:162` | call | 60.0 | tuned | `l4.end_to_end_timing_reset_recovery_timeout_s` — deadline to serve again after each reset |
| `tests_hardware/bench/test_end_to_end_timing.py:162` | kw | 60.0 | tuned | `l4.end_to_end_timing_reset_recovery_timeout_s` — deadline to serve again after each reset |
| `tests_hardware/bench/test_end_to_end_timing.py:163` | call | 1.0 | tuned | `l4.end_to_end_timing_poll_s` — poll step of the reachability / fetch-ok waits |
| `tests_hardware/bench/test_end_to_end_timing.py:163` | kw | 1.0 | tuned | `l4.end_to_end_timing_poll_s` — poll step of the reachability / fetch-ok waits |
| `tests_hardware/bench/test_end_to_end_timing.py:173` | kw | 10.0 | tuned | `l4.end_to_end_timing_probe_timeout_s` — HTTP timeout of a status/sensors/PUT request |
| `tests_hardware/bench/test_end_to_end_timing.py:177` | call | 90.0 | tuned | `l4.end_to_end_timing_backup_advance_timeout_s` — deadline for the SGP40 backup stamp to advance (1.5 backup periods) |
| `tests_hardware/bench/test_end_to_end_timing.py:177` | kw | 90.0 | tuned | `l4.end_to_end_timing_backup_advance_timeout_s` — deadline for the SGP40 backup stamp to advance (1.5 backup periods) |
| `tests_hardware/bench/test_end_to_end_timing.py:178` | call | 5.0 | tuned | `l4.end_to_end_timing_backup_poll_s` — poll step of the backup-advance wait |
| `tests_hardware/bench/test_end_to_end_timing.py:178` | kw | 5.0 | tuned | `l4.end_to_end_timing_backup_poll_s` — poll step of the backup-advance wait |
| `tests_hardware/bench/test_end_to_end_timing.py:183` | kw | 10.0 | tuned | `l4.end_to_end_timing_probe_timeout_s` — HTTP timeout of a status/sensors/PUT request |
| `tests_hardware/bench/test_end_to_end_timing.py:191` | call | 20.0 | tuned | `l4.end_to_end_timing_restore_recovery_timeout_s` — deadline to serve before the config restore retry |
| `tests_hardware/bench/test_end_to_end_timing.py:191` | kw | 20.0 | tuned | `l4.end_to_end_timing_restore_recovery_timeout_s` — deadline to serve before the config restore retry |
| `tests_hardware/bench/test_end_to_end_timing.py:192` | call | 2.0 | tuned | `l4.end_to_end_timing_serving_poll_s` — poll step of the serving waits |
| `tests_hardware/bench/test_end_to_end_timing.py:192` | kw | 2.0 | tuned | `l4.end_to_end_timing_serving_poll_s` — poll step of the serving waits |
| `tests_hardware/bench/test_end_to_end_timing.py:200` | call | 60.0 | tuned | `l4.end_to_end_timing_reset_recovery_timeout_s` — deadline to serve again after each reset |
| `tests_hardware/bench/test_end_to_end_timing.py:200` | kw | 60.0 | tuned | `l4.end_to_end_timing_reset_recovery_timeout_s` — deadline to serve again after each reset |
| `tests_hardware/bench/test_end_to_end_timing.py:201` | call | 1.0 | tuned | `l4.end_to_end_timing_poll_s` — poll step of the reachability / fetch-ok waits |
| `tests_hardware/bench/test_end_to_end_timing.py:201` | kw | 1.0 | tuned | `l4.end_to_end_timing_poll_s` — poll step of the reachability / fetch-ok waits |
| `tests_hardware/bench/test_end_to_end_timing.py:204` | kw | 10.0 | tuned | `l4.end_to_end_timing_probe_timeout_s` — HTTP timeout of a status/sensors/PUT request |
| `tests_hardware/bench/test_end_to_end_timing.py:211` | kw | 10.0 | tuned | `l4.end_to_end_timing_probe_timeout_s` — HTTP timeout of a status/sensors/PUT request |
| `tests_hardware/bench/test_heap_under_connection_ceiling.py:25` | const | 2048 | mirror | → `web.max_content_length` — PER_CONNECTION_ALLOCATION: "(2048)" the per-connection body buffer (comment :22-23; A.U8.05 names it a mirror) |
| `tests_hardware/bench/test_heap_under_connection_ceiling.py:27` | const | 55.0 | tuned | `l4.ceiling_hold_s` — ceiling holder duration |
| `tests_hardware/bench/test_heap_under_connection_ceiling.py:31` | const | 2.0 | tuned | `l4.ceiling_drip_interval_s` — drip interval |
| `tests_hardware/bench/test_heap_under_connection_ceiling.py:34` | const | 10.0 | tuned | `l4.ceiling_recycle_s` — recycle period |
| `tests_hardware/bench/test_heap_under_connection_ceiling.py:37` | const | 0.55 | tuned | `l4.ceiling_min_fraction_at_ceiling` — minimum fraction at the ceiling |
| `tests_hardware/bench/test_heap_under_connection_ceiling.py:40` | const | 0.3 | tuned | `l4.ceiling_admission_wait_s` — admission wait |
| `tests_hardware/bench/test_heap_under_connection_ceiling.py:49` | call | 5.0 | tuned | `l4.ceiling_holder_socket_timeout_s` — socket timeout of each holder connection; an instrument value A.U8.05 does not list (G1/R15) |
| `tests_hardware/bench/test_heap_under_connection_ceiling.py:109` | kw | 10.0 | tuned | `l4.heap_under_connection_ceiling_worker_join_s` — join bound on the holder workers |
| `tests_hardware/bench/test_heap_under_connection_ceiling.py:121` | kw | 240.0 | tuned | `l4.heap_under_connection_ceiling_script_timeout_s` — run_isolated bound of the device script |
| `tests_hardware/bench/test_heap_under_connection_ceiling.py:124` | kw | 30.0 | tuned | `l4.heap_under_connection_ceiling_hammer_join_s` — join bound on the hammer thread |
| `tests_hardware/bench/test_hotspot_role_reversal.py:27` | param | 5 | tuned | `l4.hotspot_role_reversal_join_attempts` — re-verify retry count of the hotspot join |
| `tests_hardware/bench/test_hotspot_role_reversal.py:33` | kw | 45.0 | tuned | `l4.conftest_join_hotspot_timeout_s` — the same DUT-hotspot join deadline as tests_hardware/conftest.py:187 (shared ID) |
| `tests_hardware/bench/test_hotspot_role_reversal.py:38` | call | 30.0 | tuned | `l4.conftest_hotspot_scan_timeout_s` — the same hotspot-visible scan deadline as conftest.py:183 (shared ID) |
| `tests_hardware/bench/test_hotspot_role_reversal.py:38` | call | 2.0 | tuned | `l4.conftest_hotspot_scan_poll_s` — the same scan poll step as conftest.py:184 (shared ID) |
| `tests_hardware/bench/test_hotspot_role_reversal.py:38` | kw | 30.0 | tuned | `l4.conftest_hotspot_scan_timeout_s` — the same hotspot-visible scan deadline as conftest.py:183 (shared ID) |
| `tests_hardware/bench/test_hotspot_role_reversal.py:38` | kw | 2.0 | tuned | `l4.conftest_hotspot_scan_poll_s` — the same scan poll step as conftest.py:184 (shared ID) |
| `tests_hardware/bench/test_hotspot_role_reversal.py:68` | kw | 10.0 | tuned | `l4.hotspot_role_reversal_probe_timeout_s` — HTTP timeout of a request over the hotspot / bridge |
| `tests_hardware/bench/test_hotspot_role_reversal.py:80` | call | 30.0 | tuned | `l4.conftest_hotspot_scan_timeout_s` — the same hotspot-visible scan deadline as conftest.py:183 (shared ID) |
| `tests_hardware/bench/test_hotspot_role_reversal.py:80` | call | 2.0 | tuned | `l4.conftest_hotspot_scan_poll_s` — the same scan poll step as conftest.py:184 (shared ID) |
| `tests_hardware/bench/test_hotspot_role_reversal.py:80` | kw | 30.0 | tuned | `l4.conftest_hotspot_scan_timeout_s` — the same hotspot-visible scan deadline as conftest.py:183 (shared ID) |
| `tests_hardware/bench/test_hotspot_role_reversal.py:80` | kw | 2.0 | tuned | `l4.conftest_hotspot_scan_poll_s` — the same scan poll step as conftest.py:184 (shared ID) |
| `tests_hardware/bench/test_hotspot_role_reversal.py:86` | call | 45.0 | tuned | `l4.hotspot_role_reversal_dhcp_timeout_s` — deadline for the bench radio's DHCP lease on the DUT hotspot |
| `tests_hardware/bench/test_hotspot_role_reversal.py:86` | call | 2.0 | tuned | `l4.hotspot_role_reversal_dhcp_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:86` | kw | 45.0 | tuned | `l4.hotspot_role_reversal_dhcp_timeout_s` — deadline for the bench radio's DHCP lease on the DUT hotspot |
| `tests_hardware/bench/test_hotspot_role_reversal.py:86` | kw | 2.0 | tuned | `l4.hotspot_role_reversal_dhcp_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:95` | kw | 15.0 | tuned | `l4.hotspot_role_reversal_restore_put_timeout_s` — HTTP timeout of the SSID-restoring PUT |
| `tests_hardware/bench/test_hotspot_role_reversal.py:109` | call | 90.0 | tuned | `l4.hotspot_role_reversal_flip_back_timeout_s` — deadline to reach the DUT over the bridge after the role flip back |
| `tests_hardware/bench/test_hotspot_role_reversal.py:109` | call | 3.0 | tuned | `l4.hotspot_role_reversal_flip_back_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:109` | kw | 90.0 | tuned | `l4.hotspot_role_reversal_flip_back_timeout_s` — deadline to reach the DUT over the bridge after the role flip back |
| `tests_hardware/bench/test_hotspot_role_reversal.py:109` | kw | 3.0 | tuned | `l4.hotspot_role_reversal_flip_back_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:115` | call | 30.0 | tuned | `l4.hotspot_role_reversal_recovery_timeout_s` — deadline after the recovery hard reset |
| `tests_hardware/bench/test_hotspot_role_reversal.py:115` | call | 1.0 | tuned | `l4.hotspot_role_reversal_recovery_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:115` | kw | 30.0 | tuned | `l4.hotspot_role_reversal_recovery_timeout_s` — deadline after the recovery hard reset |
| `tests_hardware/bench/test_hotspot_role_reversal.py:115` | kw | 1.0 | tuned | `l4.hotspot_role_reversal_recovery_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:121` | kw | 5.0 | tuned | `l4.hotspot_role_reversal_ready_probe_timeout_s` — per-probe HTTP timeout of _dut_reachable_again() |
| `tests_hardware/bench/test_hotspot_role_reversal.py:185` | call | 15.0 | tuned | `l4.hotspot_role_reversal_reassoc_visible_timeout_s` — deadline for the hotspot to be visible on each reassociation cycle |
| `tests_hardware/bench/test_hotspot_role_reversal.py:185` | call | 1.0 | tuned | `l4.hotspot_role_reversal_reassoc_visible_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:185` | kw | 15.0 | tuned | `l4.hotspot_role_reversal_reassoc_visible_timeout_s` — deadline for the hotspot to be visible on each reassociation cycle |
| `tests_hardware/bench/test_hotspot_role_reversal.py:185` | kw | 1.0 | tuned | `l4.hotspot_role_reversal_reassoc_visible_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:187` | call | 45.0 | tuned | `l4.hotspot_role_reversal_dhcp_timeout_s` — deadline for the bench radio's DHCP lease on the DUT hotspot |
| `tests_hardware/bench/test_hotspot_role_reversal.py:187` | call | 2.0 | tuned | `l4.hotspot_role_reversal_dhcp_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:187` | kw | 45.0 | tuned | `l4.hotspot_role_reversal_dhcp_timeout_s` — deadline for the bench radio's DHCP lease on the DUT hotspot |
| `tests_hardware/bench/test_hotspot_role_reversal.py:187` | kw | 2.0 | tuned | `l4.hotspot_role_reversal_dhcp_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:251` | deadline | 3.0 | tuned | `l4.hotspot_role_reversal_dns_flood_s` — length of the malformed-DNS flood |
| `tests_hardware/bench/test_hotspot_role_reversal.py:254` | call | 0.05 | tuned | `l4.hotspot_role_reversal_dns_flood_step_s` — pace of that flood |
| `tests_hardware/bench/test_hotspot_role_reversal.py:258` | kw | 8.0 | tuned | `l4.hotspot_role_reversal_dns_recovery_timeout_s` — reply deadline of the post-flood query ("well within a normal timeout", :257); Dependant of dns_server.recv_backoff_max_s |
| `tests_hardware/bench/test_hotspot_role_reversal.py:270` | kw | 10.0 | tuned | `l4.hotspot_role_reversal_probe_timeout_s` — HTTP timeout of a request over the hotspot / bridge |
| `tests_hardware/bench/test_hotspot_role_reversal.py:287` | kw | 10.0 | tuned | `l4.hotspot_role_reversal_probe_timeout_s` — HTTP timeout of a request over the hotspot / bridge |
| `tests_hardware/bench/test_hotspot_role_reversal.py:300` | call | 10.0 | tuned | `l4.hotspot_role_reversal_raw_socket_timeout_s` — raw TCP socket timeout of the malformed-request cases |
| `tests_hardware/bench/test_hotspot_role_reversal.py:324` | kw | 10.0 | tuned | `l4.hotspot_role_reversal_probe_timeout_s` — HTTP timeout of a request over the hotspot / bridge |
| `tests_hardware/bench/test_hotspot_role_reversal.py:339` | call | 10.0 | tuned | `l4.hotspot_role_reversal_raw_socket_timeout_s` — raw TCP socket timeout of the malformed-request cases |
| `tests_hardware/bench/test_hotspot_role_reversal.py:348` | kw | 10.0 | tuned | `l4.hotspot_role_reversal_probe_timeout_s` — HTTP timeout of a request over the hotspot / bridge |
| `tests_hardware/bench/test_hotspot_role_reversal.py:361` | call | 15.0 | tuned | `l4.hotspot_role_reversal_reassoc_visible_timeout_s` — deadline for the hotspot to be visible on each reassociation cycle |
| `tests_hardware/bench/test_hotspot_role_reversal.py:361` | call | 1.0 | tuned | `l4.hotspot_role_reversal_reassoc_visible_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:361` | kw | 15.0 | tuned | `l4.hotspot_role_reversal_reassoc_visible_timeout_s` — deadline for the hotspot to be visible on each reassociation cycle |
| `tests_hardware/bench/test_hotspot_role_reversal.py:361` | kw | 1.0 | tuned | `l4.hotspot_role_reversal_reassoc_visible_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_hotspot_role_reversal.py:363` | kw | 10.0 | tuned | `l4.hotspot_role_reversal_probe_timeout_s` — HTTP timeout of a request over the hotspot / bridge |
| `tests_hardware/bench/test_memory_stress_bench.py:27` | const | 120.0 | tuned | `l4.memory_stress_bench_hammer_duration_s` — request-hammer duration ("reproduces the request density that originally found real MemoryErrors within 45s", :25-26) |
| `tests_hardware/bench/test_memory_stress_bench.py:46` | kw | 5.0 | tuned | `l4.memory_stress_bench_fetch_timeout_s` — per-request HTTP timeout of the hammer threads |
| `tests_hardware/bench/test_memory_stress_bench.py:63` | kw | 5.0 | tuned | `l4.memory_stress_bench_fetch_timeout_s` — per-request HTTP timeout of the hammer threads |
| `tests_hardware/bench/test_memory_stress_bench.py:82` | kw | 10.0 | tuned | `l4.memory_stress_bench_join_timeout_s` — join bound on the hammer threads |
| `tests_hardware/bench/test_memory_stress_bench.py:151` | kw | 5.0 | tuned | `l4.memory_stress_bench_fetch_timeout_s` — per-request HTTP timeout of the hammer threads |
| `tests_hardware/bench/test_memory_stress_bench.py:164` | kw | 10.0 | tuned | `l4.memory_stress_bench_join_timeout_s` — join bound on the hammer threads |
| `tests_hardware/bench/test_network_resilience.py:44` | call | 15.0 | tuned | `l4.network_resilience_outage_s` — length of the real AP outage ("brief … realistic, low-risk", :40-42) |
| `tests_hardware/bench/test_network_resilience.py:57` | call | 150.0 | tuned | `l4.network_resilience_outage_reconnect_timeout_s` — deadline to reconnect after the outage / flapping (spans the 60 s retry cadence) |
| `tests_hardware/bench/test_network_resilience.py:57` | kw | 150.0 | tuned | `l4.network_resilience_outage_reconnect_timeout_s` — deadline to reconnect after the outage / flapping (spans the 60 s retry cadence) |
| `tests_hardware/bench/test_network_resilience.py:58` | call | 5.0 | tuned | `l4.network_resilience_outage_reconnect_poll_s` — its poll step |
| `tests_hardware/bench/test_network_resilience.py:58` | kw | 5.0 | tuned | `l4.network_resilience_outage_reconnect_poll_s` — its poll step |
| `tests_hardware/bench/test_network_resilience.py:67` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:67` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:67` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:67` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:70` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:80` | call | 3.0 | tuned | `l4.network_resilience_flap_step_s` — half-period of the 3x(3 s down / 3 s up) flap, "short relative to the 60s retry cadence"; Dependant of wifi.sta_retry_after_loss_s |
| `tests_hardware/bench/test_network_resilience.py:82` | call | 3.0 | tuned | `l4.network_resilience_flap_step_s` — half-period of the 3x(3 s down / 3 s up) flap, "short relative to the 60s retry cadence"; Dependant of wifi.sta_retry_after_loss_s |
| `tests_hardware/bench/test_network_resilience.py:95` | call | 150.0 | tuned | `l4.network_resilience_outage_reconnect_timeout_s` — deadline to reconnect after the outage / flapping (spans the 60 s retry cadence) |
| `tests_hardware/bench/test_network_resilience.py:95` | kw | 150.0 | tuned | `l4.network_resilience_outage_reconnect_timeout_s` — deadline to reconnect after the outage / flapping (spans the 60 s retry cadence) |
| `tests_hardware/bench/test_network_resilience.py:96` | call | 5.0 | tuned | `l4.network_resilience_outage_reconnect_poll_s` — its poll step |
| `tests_hardware/bench/test_network_resilience.py:96` | kw | 5.0 | tuned | `l4.network_resilience_outage_reconnect_poll_s` — its poll step |
| `tests_hardware/bench/test_network_resilience.py:105` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:105` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:105` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:105` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:108` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:128` | kw | 5.0 | tuned | `l4.network_resilience_ready_probe_timeout_s` — per-probe HTTP timeout of a readiness check |
| `tests_hardware/bench/test_network_resilience.py:142` | kw | 150 | test input | injected netem fault profile: the stimulus, not a budget (see Open points) |
| `tests_hardware/bench/test_network_resilience.py:142` | kw | 50 | test input | injected netem fault profile: the stimulus, not a budget (see Open points) |
| `tests_hardware/bench/test_network_resilience.py:149` | call | 90.0 | tuned | `l4.network_resilience_degraded_reconnect_timeout_s` — deadline to reconnect under heavy degradation |
| `tests_hardware/bench/test_network_resilience.py:149` | kw | 90.0 | tuned | `l4.network_resilience_degraded_reconnect_timeout_s` — deadline to reconnect under heavy degradation |
| `tests_hardware/bench/test_network_resilience.py:150` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:150` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:156` | kw | 5.0 | tuned | `l4.network_resilience_crash_check_tail_s` — passive log window for the crash check |
| `tests_hardware/bench/test_network_resilience.py:163` | kw | 5.0 | tuned | `l4.network_resilience_ready_probe_timeout_s` — per-probe HTTP timeout of a readiness check |
| `tests_hardware/bench/test_network_resilience.py:164` | call | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:164` | kw | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:165` | call | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:165` | kw | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:177` | kw | 30 | test input | injected netem fault profile: the stimulus, not a budget (see Open points) |
| `tests_hardware/bench/test_network_resilience.py:177` | kw | 20 | test input | injected netem fault profile: the stimulus, not a budget (see Open points) |
| `tests_hardware/bench/test_network_resilience.py:180` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:182` | call | 1.0 | tuned | `l4.network_resilience_probe_spacing_s` — spacing of the five probes under light degradation |
| `tests_hardware/bench/test_network_resilience.py:198` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:198` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:199` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:199` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:205` | kw | 5.0 | tuned | `l4.network_resilience_crash_check_tail_s` — passive log window for the crash check |
| `tests_hardware/bench/test_network_resilience.py:210` | kw | 5.0 | tuned | `l4.network_resilience_ready_probe_timeout_s` — per-probe HTTP timeout of a readiness check |
| `tests_hardware/bench/test_network_resilience.py:211` | call | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:211` | kw | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:212` | call | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:212` | kw | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:224` | kw | 20 | test input | injected netem fault profile: the stimulus, not a budget (see Open points) |
| `tests_hardware/bench/test_network_resilience.py:228` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:228` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:229` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:229` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:235` | kw | 5.0 | tuned | `l4.network_resilience_crash_check_tail_s` — passive log window for the crash check |
| `tests_hardware/bench/test_network_resilience.py:240` | kw | 5.0 | tuned | `l4.network_resilience_ready_probe_timeout_s` — per-probe HTTP timeout of a readiness check |
| `tests_hardware/bench/test_network_resilience.py:241` | call | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:241` | kw | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:242` | call | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:242` | kw | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:254` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:259` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:265` | call | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:265` | call | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:265` | kw | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:265` | kw | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:273` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:275` | call | 8.0 | tuned | `l4.network_resilience_ntp_fail_wait_s` — "longer than the real 5s fetch timeout"; Dependant of ntp.fetch_timeout_ms |
| `tests_hardware/bench/test_network_resilience.py:281` | call | 20.0 | tuned | `l4.network_resilience_ntp_resync_timeout_s` — deadline for NTP to resync via its own retry timer (15 s retry, ntp.retry_interval_s) |
| `tests_hardware/bench/test_network_resilience.py:281` | call | 1.0 | tuned | `l4.network_resilience_quick_poll_s` — poll step of the resync and quick-recovery waits |
| `tests_hardware/bench/test_network_resilience.py:281` | kw | 20.0 | tuned | `l4.network_resilience_ntp_resync_timeout_s` — deadline for NTP to resync via its own retry timer (15 s retry, ntp.retry_interval_s) |
| `tests_hardware/bench/test_network_resilience.py:281` | kw | 1.0 | tuned | `l4.network_resilience_quick_poll_s` — poll step of the resync and quick-recovery waits |
| `tests_hardware/bench/test_network_resilience.py:292` | const | 42123 | not tagged (identifier) | local ports of the rogue responders |
| `tests_hardware/bench/test_network_resilience.py:293` | const | 42153 | not tagged (identifier) | local ports of the rogue responders |
| `tests_hardware/bench/test_network_resilience.py:304` | kw | 90.0 | tuned | `l4.network_resilience_rogue_tail_s` — log window "generous relative to asy_ntp_client.py's own retry/backoff budget" |
| `tests_hardware/bench/test_network_resilience.py:319` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:319` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:319` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:319` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:323` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:323` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:323` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:323` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:335` | kw | 90.0 | tuned | `l4.network_resilience_rogue_tail_s` — log window "generous relative to asy_ntp_client.py's own retry/backoff budget" |
| `tests_hardware/bench/test_network_resilience.py:346` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:346` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:346` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:346` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:350` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:350` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:350` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:350` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:367` | const | 2524608000 | test input | spoofed NTP transmit time the case injects (2050-01-01) |
| `tests_hardware/bench/test_network_resilience.py:374` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:391` | kw | 55.0 | tuned | `l4.bench_control_udp_capture_timeout_s` — the same capture wait as bench_control.py:138's default (shared ID) |
| `tests_hardware/bench/test_network_resilience.py:400` | call | 3.0 | tuned | `l4.network_resilience_rtc_write_wait_s` — absence wait: the spoofed reply must not have moved the RTC |
| `tests_hardware/bench/test_network_resilience.py:401` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:410` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:410` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:410` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:410` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:414` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:414` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:414` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:414` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:431` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:441` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:453` | call | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:453` | kw | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:454` | call | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:454` | kw | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:459` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:465` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:476` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:483` | call | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:483` | call | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:483` | kw | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:483` | kw | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:487` | call | 120.0 | tuned | `l4.network_resilience_ntp_resync_after_reset_timeout_s` — deadline for NTP to resync after a recovery reset |
| `tests_hardware/bench/test_network_resilience.py:487` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:487` | kw | 120.0 | tuned | `l4.network_resilience_ntp_resync_after_reset_timeout_s` — deadline for NTP to resync after a recovery reset |
| `tests_hardware/bench/test_network_resilience.py:487` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:510` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:520` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:530` | kw | 15.0 | tuned | `l4.network_resilience_no_ap_tail_s` — log window for one STAT_NO_AP_FOUND cycle |
| `tests_hardware/bench/test_network_resilience.py:554` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:554` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:555` | call | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:555` | kw | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:563` | kw | 45.0 | tuned | `l4.conftest_join_hotspot_timeout_s` — the same DUT-hotspot join deadline as conftest.py:187 (shared ID) |
| `tests_hardware/bench/test_network_resilience.py:568` | call | 3.0 | tuned | `l4.network_resilience_join_retry_backoff_s` — pause between hotspot-join retries |
| `tests_hardware/bench/test_network_resilience.py:569` | call | 45.0 | tuned | `l4.hotspot_role_reversal_dhcp_timeout_s` — the same DHCP-lease deadline as test_hotspot_role_reversal.py:86 (shared ID) |
| `tests_hardware/bench/test_network_resilience.py:569` | call | 2.0 | tuned | `l4.hotspot_role_reversal_dhcp_poll_s` — its poll step (shared ID) |
| `tests_hardware/bench/test_network_resilience.py:569` | kw | 45.0 | tuned | `l4.hotspot_role_reversal_dhcp_timeout_s` — the same DHCP-lease deadline as test_hotspot_role_reversal.py:86 (shared ID) |
| `tests_hardware/bench/test_network_resilience.py:569` | kw | 2.0 | tuned | `l4.hotspot_role_reversal_dhcp_poll_s` — its poll step (shared ID) |
| `tests_hardware/bench/test_network_resilience.py:571` | call | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:571` | call | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:571` | kw | 30.0 | tuned | `l4.network_resilience_wait_timeout_s` — deadline of a serving / synced / log-entry wait |
| `tests_hardware/bench/test_network_resilience.py:571` | kw | 2.0 | tuned | `l4.network_resilience_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_network_resilience.py:581` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:584` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:584` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:584` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:584` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:591` | call | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:591` | call | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:591` | kw | 60.0 | tuned | `l4.network_resilience_reconnect_timeout_s` — deadline to be reachable / back in STA / hotspot visible |
| `tests_hardware/bench/test_network_resilience.py:591` | kw | 3.0 | tuned | `l4.network_resilience_reconnect_poll_s` — poll step of the reconnect waits |
| `tests_hardware/bench/test_network_resilience.py:597` | kw | 5.0 | tuned | `l4.network_resilience_ready_probe_timeout_s` — per-probe HTTP timeout of a readiness check |
| `tests_hardware/bench/test_network_resilience.py:606` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:633` | call | 1.0 | tuned | `l4.network_resilience_slot_release_wait_s` — "a slot outlives the response" (SPEC I.6): kept fixed sleep, a probe would occupy a slot (G7/R23's own exception) |
| `tests_hardware/bench/test_network_resilience.py:642` | call | 10.0 | tuned | `l4.network_resilience_raw_socket_timeout_s` — raw TCP socket timeout |
| `tests_hardware/bench/test_network_resilience.py:649` | call | 2.0 | tuned | `l4.network_resilience_held_admit_wait_s` — kept fixed sleep for the accept loop to admit the held sockets (a probe would take a slot, G7/R23) |
| `tests_hardware/bench/test_network_resilience.py:656` | call | 10.0 | tuned | `l4.network_resilience_raw_socket_timeout_s` — raw TCP socket timeout |
| `tests_hardware/bench/test_network_resilience.py:662` | call | 1.0 | tuned | `l4.network_resilience_admitted_silence_s` — "Silent past 1 s means admitted", kept under the 5 s per-call timeout; Dependant of web.per_call_timeout_s |
| `tests_hardware/bench/test_network_resilience.py:673` | call | 1.0 | tuned | `l4.network_resilience_slot_release_wait_s` — "a slot outlives the response" (SPEC I.6): kept fixed sleep, a probe would occupy a slot (G7/R23's own exception) |
| `tests_hardware/bench/test_network_resilience.py:685` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:686` | call | 15.0 | tuned | `l4.network_resilience_quick_recovery_timeout_s` — deadline to serve again after a ceiling/storm case |
| `tests_hardware/bench/test_network_resilience.py:686` | kw | 15.0 | tuned | `l4.network_resilience_quick_recovery_timeout_s` — deadline to serve again after a ceiling/storm case |
| `tests_hardware/bench/test_network_resilience.py:687` | call | 1.0 | tuned | `l4.network_resilience_quick_poll_s` — poll step of the resync and quick-recovery waits |
| `tests_hardware/bench/test_network_resilience.py:687` | kw | 1.0 | tuned | `l4.network_resilience_quick_poll_s` — poll step of the resync and quick-recovery waits |
| `tests_hardware/bench/test_network_resilience.py:706` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:721` | call | 10.0 | tuned | `l4.network_resilience_raw_socket_timeout_s` — raw TCP socket timeout |
| `tests_hardware/bench/test_network_resilience.py:741` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:754` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:768` | const | 2048 | mirror | → `web.max_content_length` — "asy_webserver_service.py's max_content_length" |
| `tests_hardware/bench/test_network_resilience.py:769` | const | 4096 | test input | the former cap (4096); the 2048..4096 band is the case's discriminator |
| `tests_hardware/bench/test_network_resilience.py:770` | const | 1312 | not tagged (derived) | largest schema-permitted PUT body (NTP_Host's 1024 plus the envelope, SPEC I.6) |
| `tests_hardware/bench/test_network_resilience.py:783` | param | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:822` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:836` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:849` | call | 1.0 | tuned | `l4.network_resilience_slot_release_wait_s` — "a slot outlives the response" (SPEC I.6): kept fixed sleep, a probe would occupy a slot (G7/R23's own exception) |
| `tests_hardware/bench/test_network_resilience.py:860` | kw | 30.0 | tuned | `l4.network_resilience_loaded_fetch_timeout_s` — per-request timeout under the storm/burst |
| `tests_hardware/bench/test_network_resilience.py:873` | kw | 60.0 | tuned | `l4.network_resilience_storm_join_s` — join bound on the mixed-size PUT storm |
| `tests_hardware/bench/test_network_resilience.py:894` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:895` | call | 15.0 | tuned | `l4.network_resilience_quick_recovery_timeout_s` — deadline to serve again after a ceiling/storm case |
| `tests_hardware/bench/test_network_resilience.py:895` | kw | 15.0 | tuned | `l4.network_resilience_quick_recovery_timeout_s` — deadline to serve again after a ceiling/storm case |
| `tests_hardware/bench/test_network_resilience.py:896` | call | 1.0 | tuned | `l4.network_resilience_quick_poll_s` — poll step of the resync and quick-recovery waits |
| `tests_hardware/bench/test_network_resilience.py:896` | kw | 1.0 | tuned | `l4.network_resilience_quick_poll_s` — poll step of the resync and quick-recovery waits |
| `tests_hardware/bench/test_network_resilience.py:917` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:927` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:950` | call | 30.0 | tuned | `l4.network_resilience_slowloris_socket_timeout_s` — "generous relative to production's own outer_cap_s=15.0"; Dependant of web.outer_cap_s |
| `tests_hardware/bench/test_network_resilience.py:959` | call | 3.0 | tuned | `l4.network_resilience_trickle_step_s` — pace of the slowloris header trickle |
| `tests_hardware/bench/test_network_resilience.py:968` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:981` | call | 10.0 | tuned | `l4.network_resilience_raw_socket_timeout_s` — raw TCP socket timeout |
| `tests_hardware/bench/test_network_resilience.py:990` | kw | 10.0 | tuned | `l4.network_resilience_probe_timeout_s` — HTTP timeout of a status/config request (and _put_sized()'s default) |
| `tests_hardware/bench/test_network_resilience.py:1041` | kw | 30.0 | tuned | `l4.network_resilience_loaded_fetch_timeout_s` — per-request timeout under the storm/burst |
| `tests_hardware/bench/test_network_resilience.py:1049` | call | 1.0 | tuned | `l4.network_resilience_slot_release_wait_s` — "a slot outlives the response" (SPEC I.6): kept fixed sleep, a probe would occupy a slot (G7/R23's own exception) |
| `tests_hardware/bench/test_network_resilience.py:1054` | kw | 40.0 | tuned | `l4.network_resilience_burst_join_s` — join bound on the ceiling bursts |
| `tests_hardware/bench/test_network_resilience.py:1063` | assert | 30.0 | tuned | `l4.network_resilience_served_elapsed_max_s` — per-response time budget under the full-ceiling burst |
| `tests_hardware/bench/test_network_resilience.py:1064` | call | 1.0 | tuned | `l4.network_resilience_slot_release_wait_s` — "a slot outlives the response" (SPEC I.6): kept fixed sleep, a probe would occupy a slot (G7/R23's own exception) |
| `tests_hardware/bench/test_network_resilience.py:1076` | kw | 30.0 | tuned | `l4.network_resilience_loaded_fetch_timeout_s` — per-request timeout under the storm/burst |
| `tests_hardware/bench/test_network_resilience.py:1079` | call | 1.0 | tuned | `l4.network_resilience_slot_release_wait_s` — "a slot outlives the response" (SPEC I.6): kept fixed sleep, a probe would occupy a slot (G7/R23's own exception) |
| `tests_hardware/bench/test_network_resilience.py:1086` | kw | 30.0 | tuned | `l4.network_resilience_loaded_fetch_timeout_s` — per-request timeout under the storm/burst |
| `tests_hardware/bench/test_network_resilience.py:1096` | kw | 40.0 | tuned | `l4.network_resilience_burst_join_s` — join bound on the ceiling bursts |
| `tests_hardware/bench/test_network_resilience.py:1101` | call | 1.0 | tuned | `l4.network_resilience_slot_release_wait_s` — "a slot outlives the response" (SPEC I.6): kept fixed sleep, a probe would occupy a slot (G7/R23's own exception) |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:32` | kw | 10.0 | tuned | `l4.rest_endpoints_over_sta_probe_timeout_s` — HTTP timeout of a request over STA |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:46` | kw | 10.0 | tuned | `l4.rest_endpoints_over_sta_probe_timeout_s` — HTTP timeout of a request over STA |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:91` | kw | 10.0 | tuned | `l4.rest_endpoints_over_sta_probe_timeout_s` — HTTP timeout of a request over STA |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:95` | kw | 10.0 | tuned | `l4.rest_endpoints_over_sta_probe_timeout_s` — HTTP timeout of a request over STA |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:98` | kw | 10.0 | tuned | `l4.rest_endpoints_over_sta_probe_timeout_s` — HTTP timeout of a request over STA |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:108` | kw | 5.0 | tuned | `l4.rest_endpoints_over_sta_ready_probe_timeout_s` — per-probe HTTP timeout of the post-reboot wait |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:109` | call | 120.0 | tuned | `l4.rest_endpoints_over_sta_reboot_ready_timeout_s` — deadline to serve after the reboot |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:109` | kw | 120.0 | tuned | `l4.rest_endpoints_over_sta_reboot_ready_timeout_s` — deadline to serve after the reboot |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:110` | call | 3.0 | tuned | `l4.rest_endpoints_over_sta_reboot_ready_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:110` | kw | 3.0 | tuned | `l4.rest_endpoints_over_sta_reboot_ready_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:113` | kw | 10.0 | tuned | `l4.rest_endpoints_over_sta_probe_timeout_s` — HTTP timeout of a request over STA |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:129` | kw | 10.0 | tuned | `l4.rest_endpoints_over_sta_probe_timeout_s` — HTTP timeout of a request over STA |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:137` | kw | 10.0 | tuned | `l4.rest_endpoints_over_sta_probe_timeout_s` — HTTP timeout of a request over STA |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:145` | kw | 5.0 | tuned | `l4.rest_endpoints_over_sta_ready_probe_timeout_s` — per-probe HTTP timeout of the post-reboot wait |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:146` | call | 120.0 | tuned | `l4.rest_endpoints_over_sta_reboot_ready_timeout_s` — deadline to serve after the reboot |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:146` | kw | 120.0 | tuned | `l4.rest_endpoints_over_sta_reboot_ready_timeout_s` — deadline to serve after the reboot |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:147` | call | 3.0 | tuned | `l4.rest_endpoints_over_sta_reboot_ready_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:147` | kw | 3.0 | tuned | `l4.rest_endpoints_over_sta_reboot_ready_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:150` | kw | 10.0 | tuned | `l4.rest_endpoints_over_sta_probe_timeout_s` — HTTP timeout of a request over STA |
| `tests_hardware/bench/test_rest_endpoints_over_sta.py:155` | kw | 10.0 | tuned | `l4.rest_endpoints_over_sta_probe_timeout_s` — HTTP timeout of a request over STA |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:20` | const-c | 4 | test input | config values the case pushes and reads back (valid REST values chosen to differ from the defaults) |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:20` | const-c | 2 | test input | config values the case pushes and reads back (valid REST values chosen to differ from the defaults) |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:20` | const-c | 3 | test input | config values the case pushes and reads back (valid REST values chosen to differ from the defaults) |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:32` | const-c | 12 | test input | config values the case pushes and reads back (valid REST values chosen to differ from the defaults) |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:32` | const-c | 375 | test input | config values the case pushes and reads back (valid REST values chosen to differ from the defaults) |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:32` | const-c | 1 | test input | config values the case pushes and reads back (valid REST values chosen to differ from the defaults) |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:32` | const-c | 20 | test input | config values the case pushes and reads back (valid REST values chosen to differ from the defaults) |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:38` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:48` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:54` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:61` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:78` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:88` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:94` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:101` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:120` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:124` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:132` | call | 1.0 | tuned | `l4.sensor_config_push_over_real_hardware_override_poll_s` — poll step (10 rounds) over the ~1 s override tick; Dependant of notify.loop_tick_s |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:133` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:148` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:155` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:165` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:170` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:178` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py:185` | kw | 10.0 | tuned | `l4.sensor_config_push_over_real_hardware_probe_timeout_s` — HTTP timeout of a config GET/PUT |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py:28` | const | 12 | tuned | `l4.serving_heap_at_default_gc_rounds` — rounds per concurrency level |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py:29` | const | 1.0 | tuned | `l4.network_resilience_slot_release_wait_s` — "a slot outlives the response its client holds": the same slot-release wait as test_network_resilience.py (shared ID) |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py:30` | const | 3.0 | tuned | `l4.serving_heap_at_default_gc_level_gap_s` — "under the device script's own 10 s quiet-to-leave"; Dependant of that device-script value |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py:31` | const | 30.0 | tuned | `l4.serving_heap_at_default_gc_pre_idle_s` — idle lead-in before the first level ("~4 idle dumps") |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py:35` | const | 480 | tuned | `l4.serving_heap_at_default_gc_max_route_need` — allocation budget placed between the measured rungs 24 and 32 (comment :33-34) |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py:42` | kw | 30.0 | tuned | `l4.serving_heap_at_default_gc_connect_timeout_s` — connect/read timeout of one raw request |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py:72` | kw | 30.0 | tuned | `l4.serving_heap_at_default_gc_barrier_timeout_s` — barrier bound of one burst |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py:78` | kw | 60.0 | tuned | `l4.serving_heap_at_default_gc_burst_join_s` — join bound of one burst's threads |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py:109` | kw | 300.0 | tuned | `l4.serving_heap_at_default_gc_need_script_timeout_s` — run_isolated bound of allocation_need_per_source.py |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py:130` | kw | 900.0 | tuned | `l4.serving_heap_at_default_gc_serving_script_timeout_s` — run_isolated bound of serving_at_default_gc.py |
| `tests_hardware/bench/test_serving_heap_at_default_gc.py:133` | kw | 90.0 | tuned | `l4.serving_heap_at_default_gc_driver_join_s` — join bound on the traffic driver |
| `tests_hardware/bench/test_uart_link_under_api_load.py:24` | const | 2 | tuned | `l4.uart_link_under_api_load_get_workers` — concurrent GET workers of the load |
| `tests_hardware/bench/test_uart_link_under_api_load.py:25` | const | 10 | tuned | `l4.uart_link_under_api_load_get_iterations` — load volume per worker |
| `tests_hardware/bench/test_uart_link_under_api_load.py:28` | const | 15.0 | tuned | `l4.uart_link_under_api_load_request_budget_s` — per-request timeout of the load ("the claim is coexistence, not a latency number", :26-27) |
| `tests_hardware/bench/test_uart_link_under_api_load.py:35` | kw | 15.0 | tuned | `l4.uart_link_under_api_load_request_budget_s` — the literal equals _REQUEST_BUDGET_S and serves the same purpose: use the constant (no own tag) |
| `tests_hardware/bench/test_uart_link_under_api_load.py:92` | kw | 120.0 | tuned | `l4.uart_link_under_api_load_join_timeout_s` — join bound on the load threads |
| `tests_hardware/bench/test_uart_link_under_api_load.py:98` | kw | 10.0 | tuned | `l4.uart_link_under_api_load_probe_timeout_s` — per-probe HTTP timeout of the recovery waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:99` | call | 30.0 | tuned | `l4.uart_link_under_api_load_wait_timeout_s` — deadline of the serving / transfers-advanced waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:99` | kw | 30.0 | tuned | `l4.uart_link_under_api_load_wait_timeout_s` — deadline of the serving / transfers-advanced waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:100` | call | 2.0 | tuned | `l4.uart_link_under_api_load_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:100` | kw | 2.0 | tuned | `l4.uart_link_under_api_load_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:139` | kw | 120.0 | tuned | `l4.uart_link_under_api_load_join_timeout_s` — join bound on the load threads |
| `tests_hardware/bench/test_uart_link_under_api_load.py:147` | call | 30.0 | tuned | `l4.uart_link_under_api_load_wait_timeout_s` — deadline of the serving / transfers-advanced waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:147` | kw | 30.0 | tuned | `l4.uart_link_under_api_load_wait_timeout_s` — deadline of the serving / transfers-advanced waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:148` | call | 2.0 | tuned | `l4.uart_link_under_api_load_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:148` | kw | 2.0 | tuned | `l4.uart_link_under_api_load_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:181` | kw | 60.0 | tuned | `l4.uart_link_under_api_load_short_join_timeout_s` — join bound on the third arm's threads |
| `tests_hardware/bench/test_uart_link_under_api_load.py:187` | kw | 10.0 | tuned | `l4.uart_link_under_api_load_probe_timeout_s` — per-probe HTTP timeout of the recovery waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:188` | call | 30.0 | tuned | `l4.uart_link_under_api_load_wait_timeout_s` — deadline of the serving / transfers-advanced waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:188` | kw | 30.0 | tuned | `l4.uart_link_under_api_load_wait_timeout_s` — deadline of the serving / transfers-advanced waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:189` | call | 2.0 | tuned | `l4.uart_link_under_api_load_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_uart_link_under_api_load.py:189` | kw | 2.0 | tuned | `l4.uart_link_under_api_load_wait_poll_s` — poll step of those waits |
| `tests_hardware/bench/test_wifi_networking.py:37` | kw | 45.0 | tuned | `l4.wifi_networking_boot_tail_s` — log window after the hard reset for the connect lines |
| `tests_hardware/bench/test_wifi_networking.py:55` | kw | 60.0 | tuned | `l4.wifi_networking_sync_tail_s` — log window in which a real NTP sync / DNS resolution must appear |
| `tests_hardware/bench/test_wifi_networking.py:68` | kw | 60.0 | tuned | `l4.wifi_networking_sync_tail_s` — log window in which a real NTP sync / DNS resolution must appear |
| `tests_hardware/bench/test_wifi_networking.py:88` | kw | 90.0 | tuned | `l4.network_resilience_rogue_tail_s` — "generous relative to asy_ntp_client.py's own retry/backoff budget", as test_network_resilience.py:304 (shared ID) |
| `tests_hardware/bench/test_wifi_networking.py:103` | call | 60.0 | tuned | `l4.wifi_networking_reconnect_timeout_s` — deadline to be reachable after the hard reset |
| `tests_hardware/bench/test_wifi_networking.py:103` | call | 3.0 | tuned | `l4.wifi_networking_reconnect_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_wifi_networking.py:103` | kw | 60.0 | tuned | `l4.wifi_networking_reconnect_timeout_s` — deadline to be reachable after the hard reset |
| `tests_hardware/bench/test_wifi_networking.py:103` | kw | 3.0 | tuned | `l4.wifi_networking_reconnect_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_wifi_networking.py:107` | call | 60.0 | tuned | `l4.wifi_networking_reconnect_timeout_s` — deadline to be reachable after the hard reset |
| `tests_hardware/bench/test_wifi_networking.py:107` | call | 3.0 | tuned | `l4.wifi_networking_reconnect_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_wifi_networking.py:107` | kw | 60.0 | tuned | `l4.wifi_networking_reconnect_timeout_s` — deadline to be reachable after the hard reset |
| `tests_hardware/bench/test_wifi_networking.py:107` | kw | 3.0 | tuned | `l4.wifi_networking_reconnect_poll_s` — poll step of that wait |
| `tests_hardware/bench/test_wifi_networking.py:118` | kw | 5.0 | tuned | `l4.wifi_networking_ready_probe_timeout_s` — per-probe HTTP timeout of _http_ok() |
| `tests_hardware/bench_control.py:24` | param | 30.0 | tuned | `l4.bench_control_nmcli_timeout_s` — default subprocess bound of an nmcli call |
| `tests_hardware/bench_control.py:43` | kw | 15.0 | tuned | `l4.bench_control_nmcli_short_timeout_s` — bound of a listing/scan nmcli call |
| `tests_hardware/bench_control.py:90` | kw | 10.0 | tuned | `l4.bench_control_cmd_timeout_s` — subprocess bound of an iw/iptables/tc call |
| `tests_hardware/bench_control.py:138` | param | 55.0 | tuned | `l4.bench_control_udp_capture_timeout_s` — wait for the captured packet (under tcpdump's own `timeout 60`, `:132`) |
| `tests_hardware/bench_control.py:198` | kw | 15.0 | tuned | `l4.bench_control_nmcli_short_timeout_s` — bound of a listing/scan nmcli call |
| `tests_hardware/bench_control.py:201` | param | 30.0 | tuned | `l4.bench_control_join_hotspot_timeout_s` — default deadline for joining the DUT hotspot |
| `tests_hardware/bench_control.py:249` | kw | 10.0 | tuned | `l4.bench_control_cmd_timeout_s` — subprocess bound of an iw/iptables/tc call |
| `tests_hardware/bench_control.py:255` | kw | 10.0 | tuned | `l4.bench_control_cmd_timeout_s` — subprocess bound of an iw/iptables/tc call |
| `tests_hardware/bench_control.py:271` | kw | 10.0 | tuned | `l4.bench_control_cmd_timeout_s` — subprocess bound of an iw/iptables/tc call |
| `tests_hardware/bench_control.py:277` | param | 10.0 | deferred U26 | if kept: `l4.bench_control_link_local_teardown_s` — default of wait_for_link_local_teardown(), whose body is a fixed min(2.0, timeout_s) sleep; G7/R23 (RF309): removed (no caller) or made a poll in U26 |
| `tests_hardware/conftest.py:183` | call | 30.0 | tuned | `l4.conftest_hotspot_scan_timeout_s` — deadline for the DUT hotspot to become visible (one literal, reported as call and kw) |
| `tests_hardware/conftest.py:183` | kw | 30.0 | tuned | `l4.conftest_hotspot_scan_timeout_s` — deadline for the DUT hotspot to become visible (one literal, reported as call and kw) |
| `tests_hardware/conftest.py:184` | call | 2.0 | tuned | `l4.conftest_hotspot_scan_poll_s` — poll step of that scan |
| `tests_hardware/conftest.py:184` | kw | 2.0 | tuned | `l4.conftest_hotspot_scan_poll_s` — poll step of that scan |
| `tests_hardware/conftest.py:187` | kw | 45.0 | tuned | `l4.conftest_join_hotspot_timeout_s` — deadline for joining the DUT hotspot in the provisioning fixture |
| `tests_hardware/conftest.py:192` | kw | 10.0 | tuned | `l4.conftest_provision_put_timeout_s` — HTTP timeout of the provisioning PUT /networking |
| `tests_hardware/conftest.py:218` | kw | 15.0 | tuned | `l4.conftest_dut_ip_exec_timeout_s` — mpremote bound of the DUT-IP read |
| `tests_hardware/conftest.py:230` | kw | 5.0 | tuned | `l4.conftest_http_ready_probe_timeout_s` — per-probe HTTP timeout of the readiness wait |
| `tests_hardware/conftest.py:248` | call | 30.0 | tuned | `l4.conftest_http_ready_timeout_s` — deadline for the DUT to serve |
| `tests_hardware/conftest.py:248` | kw | 30.0 | tuned | `l4.conftest_http_ready_timeout_s` — deadline for the DUT to serve |
| `tests_hardware/conftest.py:249` | call | 2.0 | tuned | `l4.conftest_http_ready_poll_s` — poll step of that wait |
| `tests_hardware/conftest.py:249` | kw | 2.0 | tuned | `l4.conftest_http_ready_poll_s` — poll step of that wait |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 1 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 2 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 3 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 4 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 6 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 8 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 10 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 12 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 16 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 20 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 24 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 32 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 48 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 64 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 96 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/allocation_need_per_source.py:28` | const-c | 128 | test input | sieve sizes (GC blocks) the measurement steps through; the verdict budget is l4.serving_heap_at_default_gc_max_route_need, placed between rungs 24 and 32 |
| `tests_hardware/device_scripts/bmp3xx_plausibility_read.py:17` | kw | 8000 | mirror | → `wdt.timeout_ms` — "matches src/system_service.py's own production value" (A.U8.08 names this site) |
| `tests_hardware/device_scripts/bmp3xx_plausibility_read.py:36` | call | 0.5 | tuned | `l3.bmp3xx_plausibility_read_poll_s` — pace of the read loop |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:14` | const-c | 1 | not tagged (API domain) | BMP3xx oversampling settings (datasheet, the PressOvers/TempOvers field values) |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:14` | const-c | 2 | not tagged (API domain) | BMP3xx oversampling settings (datasheet, the PressOvers/TempOvers field values) |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:14` | const-c | 4 | not tagged (API domain) | BMP3xx oversampling settings (datasheet, the PressOvers/TempOvers field values) |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:14` | const-c | 8 | not tagged (API domain) | BMP3xx oversampling settings (datasheet, the PressOvers/TempOvers field values) |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:14` | const-c | 16 | not tagged (API domain) | BMP3xx oversampling settings (datasheet, the PressOvers/TempOvers field values) |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:14` | const-c | 32 | not tagged (API domain) | BMP3xx oversampling settings (datasheet, the PressOvers/TempOvers field values) |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:16` | const | 20 | tuned | `l3.bmp3xx_same_device_rw_concurrency_read_iterations` — reader iterations of the hazard case |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:17` | const | 6 | tuned | `l3.bmp3xx_same_device_rw_concurrency_write_iterations` — writer iterations of the hazard case |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:21` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:49` | call | 0.05 | tuned | `l3.bmp3xx_same_device_rw_concurrency_write_spread_s` — "spread writes out across the reader's whole run" |
| `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:60` | call | 60.0 | tuned | `l3.bmp3xx_same_device_rw_concurrency_run_bound_s` — wait_for hang bound of the gather |
| `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py:14` | const | 6 | tuned | `l3.bus_concurrency_cross_device_scd30_sgp40_sgp40_cycles` — SGP40 cycles of the cross-device case |
| `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py:18` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py:19` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py:59` | call | 60.0 | tuned | `l3.bus_concurrency_cross_device_scd30_sgp40_run_bound_s` — wait_for hang bound of the gather |
| `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:18` | const-c | 5 | tuned | `l3.bus_concurrency_isl29125_write_vs_siblings_write_delays_ms` — phase spread of the config write against the siblings' reads (one tag for the tuple; the tag's literal is its first element, 5) |
| `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:18` | const-c | 15 | tuned | `l3.bus_concurrency_isl29125_write_vs_siblings_write_delays_ms` — phase spread of the config write against the siblings' reads (one tag for the tuple; the tag's literal is its first element, 5) |
| `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:18` | const-c | 40 | tuned | `l3.bus_concurrency_isl29125_write_vs_siblings_write_delays_ms` — phase spread of the config write against the siblings' reads (one tag for the tuple; the tag's literal is its first element, 5) |
| `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:18` | const-c | 80 | tuned | `l3.bus_concurrency_isl29125_write_vs_siblings_write_delays_ms` — phase spread of the config write against the siblings' reads (one tag for the tuple; the tag's literal is its first element, 5) |
| `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:18` | const-c | 120 | tuned | `l3.bus_concurrency_isl29125_write_vs_siblings_write_delays_ms` — phase spread of the config write against the siblings' reads (one tag for the tuple; the tag's literal is its first element, 5) |
| `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:24` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:25` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:54` | call | 15 | tuned | `l3.bus_concurrency_isl29125_write_vs_siblings_sibling_step_ms` — pace of the sibling read loops |
| `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:70` | call | 15 | tuned | `l3.bus_concurrency_isl29125_write_vs_siblings_sibling_step_ms` — pace of the sibling read loops |
| `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:86` | call | 60.0 | tuned | `l3.bus_concurrency_isl29125_write_vs_siblings_run_bound_s` — wait_for hang bound of the gather |
| `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:16` | const | 120 | tuned | `l3.bus_concurrency_same_device_scd30_reader_iterations` — reader iterations of the hazard case |
| `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:17` | const | 40 | tuned | `l3.bus_concurrency_same_device_scd30_snapshotter_iterations` — snapshotter iterations |
| `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:21` | const | 12.0 | tuned | `l3.bus_concurrency_same_device_scd30_settle_s` — discard window for the stale first conversions ("scd30_same_device_rw_concurrency.py carries the same constant", :20): shared ID |
| `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:25` | kw | 8000 | mirror | → `wdt.timeout_ms` — "matches src/system_service.py's own production value" (A.U8.08 names this site) |
| `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:26` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:39` | call | 0.5 | tuned | `l3.bus_concurrency_same_device_scd30_settle_step_s` — step of the settle loop (also the divisor in `int(_SETTLE_S / 0.5)`, :36, which then uses the constant) |
| `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:81` | call | 90.0 | tuned | `l3.bus_concurrency_same_device_scd30_run_bound_s` — wait_for hang bound of the gather |
| `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:19` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:20` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:52` | call | 15 | tuned | `l3.bus_concurrency_scd30_write_vs_siblings_sibling_step_ms` — pace of the sibling read loops |
| `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:66` | call | 15 | tuned | `l3.bus_concurrency_scd30_write_vs_siblings_sibling_step_ms` — pace of the sibling read loops |
| `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:70` | call | 0.3 | deferred U26 | if kept: `l3.bus_concurrency_scd30_write_vs_siblings_siblings_start_s` — fixed sleep "let both siblings get real cycles running first" |
| `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:80` | call | 1.0 | tuned | `l3.bus_concurrency_scd30_write_vs_siblings_after_write_s` — how long the siblings keep running after the write (stimulus length) |
| `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:83` | call | 60.0 | tuned | `l3.bus_concurrency_scd30_write_vs_siblings_run_bound_s` — wait_for hang bound of the gather |
| `tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py:15` | const | 32 | test input | chunk size the no-op deinit case writes and reads back |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:23` | const-c | 97 | not tagged (identifier) | I2C addresses of the known devices |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:23` | const-c | 89 | not tagged (identifier) | I2C addresses of the known devices |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:23` | const-c | 119 | not tagged (identifier) | I2C addresses of the known devices |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:23` | const-c | 68 | not tagged (identifier) | I2C addresses of the known devices |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:24` | const | 0 | not tagged (identifier) | I2C general-call address |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:25` | const-c | 7 | not tagged (fact) | I2C reserved address ranges |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:25` | const-c | 120 | not tagged (fact) | I2C reserved address ranges |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:25` | const-c | 127 | not tagged (fact) | I2C reserved address ranges |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:30` | const-c | 13 | not tagged (config) | the dev bench's bus wiring (pins, frequency, i2c1 timeout) as devices/dev.toml declares it |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:30` | const-c | 12 | not tagged (config) | the dev bench's bus wiring (pins, frequency, i2c1 timeout) as devices/dev.toml declares it |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:30` | const-c | 50000 | not tagged (config) | the dev bench's bus wiring (pins, frequency, i2c1 timeout) as devices/dev.toml declares it |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:30` | const-c | 1 | not tagged (config) | the dev bench's bus wiring (pins, frequency, i2c1 timeout) as devices/dev.toml declares it |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:30` | const-c | 15 | not tagged (config) | the dev bench's bus wiring (pins, frequency, i2c1 timeout) as devices/dev.toml declares it |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:30` | const-c | 14 | not tagged (config) | the dev bench's bus wiring (pins, frequency, i2c1 timeout) as devices/dev.toml declares it |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:30` | const-c | 200000 | not tagged (config) | the dev bench's bus wiring (pins, frequency, i2c1 timeout) as devices/dev.toml declares it |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:137` | call | 0.2 | tuned | `l3.bus_topology_autodetect_and_hazard_sweep_broadcast_step_s` — pace of the general-call broadcasts during the reads |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:139` | call | 30.0 | tuned | `l3.bus_topology_autodetect_and_hazard_sweep_run_bound_s` — wait_for hang bound of the sweep |
| `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:144` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/fram_busy_status_lockout.py:11` | const | 32 | test input | chunk size of the case |
| `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:15` | const | 37376 | not tagged (identifier) | scratch FRAM addresses of the case |
| `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:16` | const | 37632 | not tagged (identifier) | scratch FRAM addresses of the case |
| `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:85` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:116` | call | 30.0 | tuned | `l3.fram_cs_hijack_fault_injection_and_recovery_victim_bound_s` — wait_for hang bound on the hijacked victim |
| `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:156` | call | 30.0 | tuned | `l3.fram_cs_hijack_fault_injection_and_recovery_victim_bound_s` — wait_for hang bound on the hijacked victim |
| `tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py:11` | const | 10 | not tagged (contract) | FRAM error-log history_length (FRAM layout, excluded as contract) |
| `tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py:12` | const | 5 | not tagged (identifier) | seeded error number |
| `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:13` | const | 10 | not tagged (contract) | FRAM error-log history_length (FRAM layout) |
| `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:14` | const | 5 | not tagged (identifier) | seeded error numbers |
| `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:15` | const | 6 | not tagged (identifier) | seeded error numbers |
| `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:17` | const | 8000 | mirror | → `wdt.timeout_ms` — named 8000 (A.U8.08 names this site) |
| `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:11` | const | 10 | not tagged (contract) | FRAM error-log history_length (FRAM layout) |
| `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:12` | const | 5 | not tagged (identifier) | seeded error numbers |
| `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:13` | const | 6 | not tagged (identifier) | seeded error numbers |
| `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:14` | const | 7 | not tagged (identifier) | seeded error numbers |
| `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:20` | const-c | 3 | test input | number of settled entries the seed script wrote (three) |
| `tests_hardware/device_scripts/fram_error_log_roundtrip.py:11` | const | 5 | test input | history length of the case's own logger (not the product's) |
| `tests_hardware/device_scripts/fram_error_log_roundtrip.py:12` | const | 42 | not tagged (identifier) | seeded error number |
| `tests_hardware/device_scripts/fram_manager_roundtrip.py:11` | const | 32 | test input | chunk size of the case |
| `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:14` | const | 32 | test input | chunk size of the case |
| `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:18` | const | 2 | tuned | `l3.fram_pause_unpause_and_gating_pause_s` — real storage pause the case waits out (with a 1.5 s margin in arithmetic, see Search gaps) |
| `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:19` | const | 6 | tuned | `l3.fram_pause_unpause_and_gating_rearm_s` — the re-armed, longer pause the case waits out |
| `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:20` | const | 8000 | mirror | → `wdt.timeout_ms` — named 8000 (A.U8.08 names this site) |
| `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:110` | kw | 60000 | test input | period of the timers that exhaust the alarm pool; they are never waited on |
| `tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py:26` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py:68` | call | 30.0 | tuned | `l3.fram_reset_race_during_write_seed_and_race_victim_bound_s` — wait_for hang bound on the victim writer |
| `tests_hardware/device_scripts/fram_reset_race_during_write_verify_recovery.py:25` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:13` | const-c | 32 | test input | FRAM regions of the case (address, length) |
| `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:14` | const-c | 32768 | test input | FRAM regions of the case (address, length) |
| `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:14` | const-c | 32 | test input | FRAM regions of the case (address, length) |
| `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:18` | const | 30 | tuned | `l3.fram_same_device_rw_concurrency_read_iterations` — reader iterations of the hazard case |
| `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:22` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:61` | call | 60.0 | tuned | `l3.fram_same_device_rw_concurrency_run_bound_s` — wait_for hang bound of the gather |
| `tests_hardware/device_scripts/fram_write_protect_roundtrip.py:19` | const | 16 | test input | chunk size of the case |
| `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:18` | const | 64 | tuned | `l3.heap_headroom_after_full_system_build_probe_min` — lower bound of the largest-block binary search; shared with heap_layout_after_full_boot_sequence.py:19 ("Same doubling/halving bounds … deliberately", its :17-18) |
| `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:19` | const-c | 192 | tuned | `l3.heap_headroom_after_full_system_build_probe_max_kib` — upper bound of that search in KiB ("already above the RP2040's whole 264 KB SRAM"); shared as :18 |
| `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:19` | const-c | 1024 | not tagged (fact) | bytes per KiB |
| `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:22` | const | 3 | tuned | `l3.heap_headroom_after_full_system_build_probe_retries` — retries of one probe step; shared as :18 |
| `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:27` | const | 16384 | not tagged (fact) | Microdot v2.6.2's max_body_length default (16384 B), the worst case the headroom is measured against (comment :25-26) |
| `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:39` | const | 100000 | tuned | `l3.heap_headroom_after_full_system_build_max_used` — allocation budget of the built object graph ("~14% over the measured cost", :37) |
| `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:19` | const | 64 | tuned | `l3.heap_headroom_after_full_system_build_probe_min` — the same probe bound as heap_headroom_after_full_system_build.py:18 (shared ID, comment :17-18) |
| `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:20` | const-c | 192 | tuned | `l3.heap_headroom_after_full_system_build_probe_max_kib` — as :19 (shared ID) |
| `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:20` | const-c | 1024 | not tagged (fact) | bytes per KiB |
| `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:23` | const | 3 | tuned | `l3.heap_headroom_after_full_system_build_probe_retries` — as :19 (shared ID) |
| `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:28` | const | 4000 | tuned | `l3.heap_layout_after_full_boot_sequence_starter_settle_ms` — settle after the starter loop before the reading (comment :24-27) |
| `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:32` | const | 20000 | tuned | `l3.heap_layout_after_full_boot_sequence_starter_loop_timeout_ms` — "only exists so a wedged starter fails honestly" (:30-31); tests/_boot_contiguity_probe.py:36 mirrors it (shared ID) |
| `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:35` | const | 250 | tuned | `l3.heap_layout_after_full_boot_sequence_starter_loop_grace_ms` — grace after the last starter lands; shared with the twin probe |
| `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:38` | const | 15 | tuned | `l3.heap_layout_after_full_boot_sequence_timers_timeout_s` — bound on start_timers(); shared with the twin probe |
| `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:190` | call | 20 | tuned | `l3.heap_layout_after_full_boot_sequence_starter_poll_ms` — poll step of the starter-loop wait; shared with the twin probe's :106 |
| `tests_hardware/device_scripts/heap_under_connection_ceiling.py:16` | const | 1000 | tuned | `l3.heap_under_connection_ceiling_sample_interval_ms` — heap-dump interval of the sampler |
| `tests_hardware/device_scripts/heap_under_connection_ceiling.py:18` | const | 90 | tuned | `l3.heap_under_connection_ceiling_window_s` — length of the sampling window (spans the host's 55 s hold, l4.ceiling_hold_s) |
| `tests_hardware/device_scripts/heap_under_connection_ceiling.py:44` | call | 20 | tuned | `l3.heap_under_connection_ceiling_boot_wait_s` — kept fixed boot wait: an in-process readiness probe would share the heap under measurement (comment :41-43, G7/R23's exception) |
| `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py:15` | const | 6 | tuned | `l3.isl29125_cross_device_concurrency_sgp40_cycles` — SGP40 cycles of the cross-device case |
| `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py:43` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py:44` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py:75` | call | 20 | tuned | `l3.isl29125_cross_device_concurrency_sibling_step_ms` — pace of the sibling read loops |
| `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py:89` | call | 20 | tuned | `l3.isl29125_cross_device_concurrency_sibling_step_ms` — pace of the sibling read loops |
| `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py:103` | call | 60.0 | tuned | `l3.isl29125_cross_device_concurrency_run_bound_s` — wait_for hang bound of the gather |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:26` | const | 18 | not tagged (config) | the bench NeoPixel pin |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:30` | const | 1 | test input | light-program levels of the scenarios (stimulus, relative to the hysteresis band, comment :27-29) |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:31` | const | 12 | test input | light-program levels of the scenarios (stimulus, relative to the hysteresis band, comment :27-29) |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:32` | const | 8.0 | tuned | `l3.isl29125_lighting_scenarios_switch_hold_s` — "the derived 2 cycles + settle + a 1s sample interval, with margin" |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:33` | const | 100 | tuned | `l3.isl29125_lighting_scenarios_step_ms` — light-program update period |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:34` | const | 300 | tuned | `l3.isl29125_lighting_scenarios_sample_ms` — reader poll step |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:35` | const | 4.0 | tuned | `l3.isl29125_lighting_scenarios_settle_s` — settle before sampling a scenario |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:36` | const | 8.0 | tuned | `l3.isl29125_lighting_scenarios_max_sample_gap_s` — stall bound: "a longer stall means the read chain died" |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:37` | const | 20 | test input | light-program levels of the scenarios (stimulus, relative to the hysteresis band, comment :27-29) |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:38` | const | 0.35 | tuned | `l3.isl29125_lighting_scenarios_baseline_tol` — return-to-baseline tolerance |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:39` | const | 3 | tuned | `l3.isl29125_lighting_scenarios_park_stable_samples` — consecutive samples that count as settled |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:40` | const | 20.0 | tuned | `l3.isl29125_lighting_scenarios_park_timeout_s` — deadline for the entry range to settle |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:306` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:307` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:323` | call | 500 | deferred U26 | if kept: `l3.isl29125_mechanism_envelope_dark_settle_ms` — fixed sleep after switching the light rig off, before the first reading |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:23` | const-c | 2 | test input | steady light levels of the envelope (stimulus) |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:23` | const-c | 4 | test input | steady light levels of the envelope (stimulus) |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:23` | const-c | 8 | test input | steady light levels of the envelope (stimulus) |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:23` | const-c | 16 | test input | steady light levels of the envelope (stimulus) |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:23` | const-c | 40 | test input | steady light levels of the envelope (stimulus) |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:23` | const-c | 100 | test input | steady light levels of the envelope (stimulus) |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:23` | const-c | 255 | test input | steady light levels of the envelope (stimulus) |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:24` | const | 4.5 | tuned | `l3.isl29125_mechanism_envelope_settle_s` — "SampleInterv=1 + the fixed 2-cycle settle + slack" |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:25` | const | 12.0 | tuned | `l3.isl29125_mechanism_envelope_max_wait_s` — deadline for a fresh reading |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:26` | const | 4 | tuned | `l3.isl29125_mechanism_envelope_max_switches` — chatter tolerance ("one up and one down is ideal") |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:27` | const | 4 | test input | steady light levels of the envelope (stimulus) |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:31` | const | 0.25 | tuned | `l3.isl29125_mechanism_envelope_max_range_step` — tolerance on the reading step across a range switch (comment :28-30) |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:52` | call | 200 | tuned | `l3.isl29125_mechanism_envelope_poll_ms` — poll step of the reading and settle loops |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:82` | call | 200 | tuned | `l3.isl29125_mechanism_envelope_poll_ms` — poll step of the reading and settle loops |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:200` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:201` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:209` | call | 500 | deferred U26 | if kept: `l3.isl29125_mechanism_envelope_dark_settle_ms` — fixed sleep after the pixel goes off, before the first level (same purpose as isl29125_lighting_scenarios.py:323) |
| `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:237` | call | 200 | deferred U26 | if kept: `l3.isl29125_mechanism_envelope_off_settle_ms` — fixed sleep letting the final pixel-off land before exit |
| `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:12` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:16` | const | 68 | not tagged (identifier) | ISL29125 I2C address |
| `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:17` | const | 6 | not tagged (config) | the bench INT pin |
| `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:63` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/isl29125_plausibility_read.py:16` | const | 20 | test input | self-light level of the case (stimulus, "~750 lx at this geometry") |
| `tests_hardware/device_scripts/isl29125_plausibility_read.py:17` | const | 5.0 | tuned | `l3.isl29125_plausibility_read_room_light_min_lux` — plausibility floor with the board lighting itself |
| `tests_hardware/device_scripts/isl29125_plausibility_read.py:22` | kw | 8000 | mirror | → `wdt.timeout_ms` — "matches src/system_service.py's own production value" (A.U8.08 names this site) |
| `tests_hardware/device_scripts/isl29125_plausibility_read.py:29` | call | 300 | deferred U26 | if kept: `l3.isl29125_plausibility_read_light_settle_ms` — fixed sleep after switching the self-light on, before reading |
| `tests_hardware/device_scripts/isl29125_plausibility_read.py:30` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/isl29125_plausibility_read.py:50` | call | 0.5 | tuned | `l3.isl29125_plausibility_read_poll_s` — poll step of the reading loop |
| `tests_hardware/device_scripts/isl29125_real_irq_edge.py:18` | const | 6.0 | tuned | `l3.isl29125_real_irq_edge_fast_path_deadline_s` — deadline only the INT path can meet ("~3030ms worst case … 5x under the periodic fallback", :15-17) |
| `tests_hardware/device_scripts/isl29125_real_irq_edge.py:19` | const | 30 | test input | trigger period chosen so only a real interrupt can beat it (case selection; never waited out) |
| `tests_hardware/device_scripts/isl29125_real_irq_edge.py:20` | const | 303 | not tagged (fact) | 3 x tINT (datasheet p3) |
| `tests_hardware/device_scripts/isl29125_real_irq_edge.py:58` | call | 50 | tuned | `l3.isl29125_real_irq_edge_int_poll_ms` — poll step (30 rounds) of the INT-line persistence timing; its resolution bounds the measured PRST unit |
| `tests_hardware/device_scripts/isl29125_real_irq_edge.py:69` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/isl29125_real_irq_edge.py:76` | call | 300 | deferred U26 | if kept: `l3.isl29125_real_irq_edge_dark_settle_ms` — fixed sleep after the pixel goes dark, before the first reading (300 ms here, 500 ms in isl29125_mechanism_envelope.py:209) |
| `tests_hardware/device_scripts/isl29125_real_irq_edge.py:77` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/isl29125_real_irq_edge.py:108` | call | 100 | tuned | `l3.isl29125_real_irq_edge_fast_path_poll_ms` — poll step of the fast-path wait |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:12` | const | 20 | tuned | `l3.isl29125_same_device_rw_concurrency_read_iterations` — reader iterations of the hazard case |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:13` | const | 6 | tuned | `l3.isl29125_same_device_rw_concurrency_write_iterations` — writer iterations |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:14` | const-c | 16 | not tagged (API domain) | legal IrCompAdjust values (datasheet p10, 0-63) |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:14` | const-c | 32 | not tagged (API domain) | legal IrCompAdjust values (datasheet p10, 0-63) |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:14` | const-c | 40 | not tagged (API domain) | legal IrCompAdjust values (datasheet p10, 0-63) |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:14` | const-c | 48 | not tagged (API domain) | legal IrCompAdjust values (datasheet p10, 0-63) |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:14` | const-c | 63 | not tagged (API domain) | legal IrCompAdjust values (datasheet p10, 0-63) |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:19` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:23` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:49` | call | 50 | tuned | `l3.isl29125_same_device_rw_concurrency_read_step_ms` — reader pace |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:53` | call | 120 | deferred U26 | if kept: `l3.isl29125_same_device_rw_concurrency_writer_start_ms` — fixed sleep "let the reader get well into its run first" |
| `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:69` | call | 90 | tuned | `l3.isl29125_same_device_rw_concurrency_write_step_ms` — writer pace |
| `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py:12` | const | 1500 | tuned | `l3.starvation_wdt_ms` — the short starvation watchdog |
| `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py:27` | kw | 60000 | test input | period of the timers that exhaust the alarm pool; never waited on |
| `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py:49` | call | 250 | tuned | `l3.reboot_fallback_starves_the_watchdog_feed_attempt_ms` — interval of the (starved) feed attempts, well under the 1500 ms watchdog; Dependant of l3.starvation_wdt_ms |
| `tests_hardware/device_scripts/reboot_persist_read.py:9` | const-c | 999999999 | test input | schema of the case's marker field |
| `tests_hardware/device_scripts/reboot_persist_read.py:11` | const | 424242 | test input | marker value the write half persisted |
| `tests_hardware/device_scripts/reboot_persist_write.py:9` | const-c | 999999999 | test input | schema of the case's marker field |
| `tests_hardware/device_scripts/reboot_persist_write.py:11` | const | 424242 | test input | marker value the case persists across the reboot |
| `tests_hardware/device_scripts/scd30_plausibility_read.py:15` | const | 45.0 | tuned | `l3.scd30_plausibility_read_settle_s` — "datasheet-bound response-time window … plus margin" |
| `tests_hardware/device_scripts/scd30_plausibility_read.py:19` | kw | 8000 | mirror | → `wdt.timeout_ms` — "matches src/system_service.py's own production value" (A.U8.08 names this site) |
| `tests_hardware/device_scripts/scd30_plausibility_read.py:20` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/scd30_plausibility_read.py:30` | call | 0.5 | tuned | `l3.scd30_plausibility_read_step_s` — step of the settle and read loops (also the divisor in `int(_SETTLE_S / 0.5)`, :28) |
| `tests_hardware/device_scripts/scd30_plausibility_read.py:41` | call | 0.5 | tuned | `l3.scd30_plausibility_read_step_s` — step of the settle and read loops (also the divisor in `int(_SETTLE_S / 0.5)`, :28) |
| `tests_hardware/device_scripts/scd30_real_irq_edge.py:11` | const | 5.0 | tuned | `l3.scd30_real_irq_edge_fast_path_deadline_s` — "comfortably above the SCD30's own ~2s natural interval + IRQ latency" |
| `tests_hardware/device_scripts/scd30_real_irq_edge.py:13` | const | 10 | test input | trigger period chosen so only the IRQ path can beat the deadline (case selection) |
| `tests_hardware/device_scripts/scd30_real_irq_edge.py:17` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/scd30_real_irq_edge.py:31` | call | 100 | tuned | `l3.scd30_real_irq_edge_poll_ms` — poll step of the fast-path wait |
| `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:16` | const | 40 | tuned | `l3.scd30_same_device_rw_concurrency_read_iterations` — reader iterations of the hazard case |
| `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:20` | const | 12.0 | tuned | `l3.bus_concurrency_same_device_scd30_settle_s` — the same stale-conversion discard window as bus_concurrency_same_device_scd30.py:21 (shared ID) |
| `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:24` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:25` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:35` | call | 0.5 | tuned | `l3.bus_concurrency_same_device_scd30_settle_step_s` — the same settle-loop step (shared ID) |
| `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:64` | call | 0.2 | deferred U26 | if kept: `l3.scd30_same_device_rw_concurrency_writer_start_s` — fixed sleep "let the reader get partway into its first few cycles first" |
| `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:72` | call | 60.0 | tuned | `l3.scd30_same_device_rw_concurrency_run_bound_s` — wait_for hang bound of the gather |
| `tests_hardware/device_scripts/scheduler_saturation_drop.py:18` | const | 2 | tuned | `l3.scheduler_saturation_drop_timer_period_ms` — period of the saturating timers (stimulus) |
| `tests_hardware/device_scripts/scheduler_saturation_drop.py:19` | const | 100 | tuned | `l3.scheduler_saturation_drop_busy_wait_ms` — deliberate loop stall that forces drops |
| `tests_hardware/device_scripts/scheduler_saturation_drop.py:20` | const | 500 | tuned | `l3.scheduler_saturation_drop_heal_window_ms` — real window in which the schedule must heal |
| `tests_hardware/device_scripts/serving_at_default_gc.py:27` | const | 20 | tuned | `l3.heap_under_connection_ceiling_boot_wait_s` — the same kept fixed boot wait (no in-process readiness probe) as heap_under_connection_ceiling.py:44 (shared ID) |
| `tests_hardware/device_scripts/serving_at_default_gc.py:28` | const | 1000 | tuned | `l3.serving_at_default_gc_poll_ms` — observation poll step |
| `tests_hardware/device_scripts/serving_at_default_gc.py:29` | const | 5 | tuned | `l3.serving_at_default_gc_dump_every` — polls per heap dump |
| `tests_hardware/device_scripts/serving_at_default_gc.py:30` | const | 2 | tuned | `l3.serving_at_default_gc_busy_to_enter` — busy polls (of the last 3) that count as load |
| `tests_hardware/device_scripts/serving_at_default_gc.py:31` | const | 10 | tuned | `l3.serving_at_default_gc_quiet_to_leave` — consecutive idle polls that end a level; l4.serving_heap_at_default_gc_level_gap_s must stay below it |
| `tests_hardware/device_scripts/serving_at_default_gc.py:32` | const | 3 | tuned | `l3.serving_at_default_gc_post_dumps` — dumps after the last level |
| `tests_hardware/device_scripts/serving_at_default_gc.py:33` | const | 600 | tuned | `l3.serving_at_default_gc_window_s` — "hard bound, whatever the host does" |
| `tests_hardware/device_scripts/serving_at_default_gc.py:34` | const | 3 | not tagged (output cap) | cap on printed failure maps: bounds no wait and decides no verdict (see Open points) |
| `tests_hardware/device_scripts/sgp40_fram_backup_restore.py:15` | const | 75.0 | tuned | `l3.sgp40_fram_backup_restore_backup_wait_s` — "60s to the first natural BackupPeriod=1min trigger, plus margin" |
| `tests_hardware/device_scripts/sgp40_fram_backup_restore.py:16` | const | 10.0 | tuned | `l3.sgp40_fram_backup_restore_restore_wait_s` — deadline for the restore after the rebuild |
| `tests_hardware/device_scripts/sgp40_fram_backup_restore.py:17` | const | 2.0 | tuned | `l3.sgp40_fram_backup_restore_wdt_feed_interval_s` — "comfortably under the 8.388s hardware ceiling"; Dependant of wdt.timeout_ms |
| `tests_hardware/device_scripts/sgp40_fram_backup_restore.py:53` | kw | 8000 | mirror | → `wdt.timeout_ms` — "matches src/system_service.py's own production value" (A.U8.08 names this site) |
| `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py:18` | const | 8 | tuned | `l3.sgp40_general_call_reset_hazard_reset_cycles` — general-call resets of the hazard case |
| `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py:43` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py:44` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py:101` | call | 15 | tuned | `l3.sgp40_general_call_reset_hazard_sibling_step_ms` — pace of the sibling read loops |
| `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py:117` | call | 90.0 | tuned | `l3.sgp40_general_call_reset_hazard_run_bound_s` — wait_for hang bound of the gather |
| `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:15` | const | 60.0 | tuned | `l3.sgp40_voc_algorithm_quality_blackout_wait_s` — "45s documented blackout + margin" |
| `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:17` | const | 2.0 | tuned | `l3.sgp40_voc_algorithm_quality_sample_interval_s` — sampling interval of the quality run |
| `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:18` | const | 300 | tuned | `l3.sgp40_voc_algorithm_quality_max_single_step_jump` — smoothness tolerance on the index |
| `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:19` | const | 2.0 | tuned | `l3.sgp40_fram_backup_restore_wdt_feed_interval_s` — the same feed interval and comment as sgp40_fram_backup_restore.py:17 (shared ID) |
| `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:45` | kw | 8000 | mirror | → `wdt.timeout_ms` — "matches src/system_service.py's own production value" (A.U8.08 names this site) |
| `tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py:9` | const-c | 5 | not tagged (API domain) | DebugLevel field entry (0-5) and its backup copy |
| `tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py:11` | const-c | 5 | not tagged (API domain) | DebugLevel field entry (0-5) and its backup copy |
| `tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py:13` | const | 3 | not tagged (identifier) | print_log.py's _LOG_ONCE level |
| `tests_hardware/device_scripts/system_debug_level_restore_after_boot_log_check.py:9` | const-c | 5 | not tagged (API domain) | DebugLevel field entry (0-5) and its backup copy |
| `tests_hardware/device_scripts/system_debug_level_restore_after_boot_log_check.py:11` | const-c | 5 | not tagged (API domain) | DebugLevel field entry (0-5) and its backup copy |
| `tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py:11` | const | 8000 | mirror | → `wdt.timeout_ms` — named 8000 (A.U8.08 names this site) |
| `tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py:38` | call | 0.9 | tuned | `l3.system_service_restarts_a_real_dead_task_watch_step_s` — step of the ~3.5 s observation window: two restarts expected, short of the ~7 s reboot threshold (comment :34-36); Dependant of system.task_check_s, system.task_fail_increment, system.task_fail_max |
| `tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py:14` | kw | 60000 | test input | period of the timers that exhaust the alarm pool; "never expected to fire" |
| `tests_hardware/device_scripts/uart_crossover_exchange.py:26` | const | 48 | not tagged (contract) | payload_size / timeout / baud agreed out of band (CLAUDE.md UART rule): excluded as contract |
| `tests_hardware/device_scripts/uart_crossover_exchange.py:27` | const | 1000 | not tagged (contract) | payload_size / timeout / baud agreed out of band (CLAUDE.md UART rule): excluded as contract |
| `tests_hardware/device_scripts/uart_crossover_exchange.py:28` | const | 115200 | not tagged (contract) | payload_size / timeout / baud agreed out of band (CLAUDE.md UART rule): excluded as contract |
| `tests_hardware/device_scripts/uart_crossover_exchange.py:29` | const | 2 | mirror | → `dev.uart_poll_wait_ms` — "Mirrors sensortask_dev.py's own pair" (comment :30-31) |
| `tests_hardware/device_scripts/uart_crossover_exchange.py:32` | const | 50 | mirror | → `dev.uart_poll_idle_ms` — as :29 |
| `tests_hardware/device_scripts/uart_crossover_exchange.py:33` | const | 512 | mirror | → `dev.uart_rxbuf` — the bench's shipped rxbuf/txbuf (used for both at the UART construction); a second stacked tag names dev.uart_txbuf |
| `tests_hardware/device_scripts/uart_crossover_exchange.py:37` | const | 100 | tuned | `l3.uart_crossover_exchange_join_step_ms` — poll-and-feed step of the bounded listener join (comment :34-36) |
| `tests_hardware/device_scripts/uart_crossover_exchange.py:38` | const | 2000 | tuned | `l3.uart_crossover_exchange_join_budget_ms` — total bound of that join |
| `tests_hardware/device_scripts/uart_crossover_exchange.py:83` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/uart_crossover_recovery.py:26` | const | 48 | not tagged (contract) | payload_size / timeout / baud agreed out of band (CLAUDE.md UART rule): excluded as contract |
| `tests_hardware/device_scripts/uart_crossover_recovery.py:27` | const | 1000 | not tagged (contract) | payload_size / timeout / baud agreed out of band (CLAUDE.md UART rule): excluded as contract |
| `tests_hardware/device_scripts/uart_crossover_recovery.py:28` | const | 115200 | not tagged (contract) | payload_size / timeout / baud agreed out of band (CLAUDE.md UART rule): excluded as contract |
| `tests_hardware/device_scripts/uart_crossover_recovery.py:29` | const | 2 | mirror | → `dev.uart_poll_wait_ms` — "Mirrors sensortask_dev.py's own pair" (comment :30-31) |
| `tests_hardware/device_scripts/uart_crossover_recovery.py:32` | const | 50 | mirror | → `dev.uart_poll_idle_ms` — as :29 |
| `tests_hardware/device_scripts/uart_crossover_recovery.py:33` | const | 512 | mirror | → `dev.uart_rxbuf` — the bench's shipped rxbuf/txbuf (used for both at the UART construction); a second stacked tag names dev.uart_txbuf |
| `tests_hardware/device_scripts/uart_crossover_recovery.py:38` | const | 100 | tuned | `l3.uart_crossover_exchange_join_step_ms` — the same bounded-join step as uart_crossover_exchange.py:37 (shared ID) |
| `tests_hardware/device_scripts/uart_crossover_recovery.py:39` | const | 2000 | tuned | `l3.uart_crossover_exchange_join_budget_ms` — the same join bound (shared ID) |
| `tests_hardware/device_scripts/uart_crossover_recovery.py:118` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:24` | const | 115200 | not tagged (contract) | link baud rate (agreed out of band) |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:25` | const | 53 | not tagged (derived) | one framed frame at payload_size=48 (contract) plus framing |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:26` | const | 5 | tuned | `l3.uart_driver_read_never_blocks_the_loop_trials` — trials per measured read path |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:27` | const | 2 | mirror | → `dev.uart_poll_wait_ms` — "mirrors sensortask_dev.py's own transaction rate" |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:79` | kw | 500 | tuned | `l3.uart_driver_read_never_blocks_the_loop_start_timeout_ms` — first-byte deadline of the measured read |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:79` | kw | 200 | tuned | `l3.uart_driver_read_never_blocks_the_loop_read_timeout_ms` — inter-byte deadline of the measured read |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:88` | deadline | 500 | tuned | `l3.uart_driver_read_never_blocks_the_loop_raw_deadline_ms` — deadline of the raw-read comparison path |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:106` | call | 5 | deferred U26 | if kept: `l3.uart_driver_read_never_blocks_the_loop_ticker_start_ms` — fixed sleep "the ticker is running before the first byte leaves" |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:119` | call | 20 | tuned | `l3.uart_driver_read_never_blocks_the_loop_idle_window_ms` — length of the idle-gap baseline measurement |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:126` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:127` | kw | 1 | test input | raw writer port configuration (timeout_char floor of the stimulus side) |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py:13` | const | 115200 | not tagged (contract) | link baud rate (agreed out of band) |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py:14` | const | 2 | mirror | → `dev.uart_poll_wait_ms` — "mirrors sensortask_dev.py's own pair" (comment :15 covers both rates) |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py:15` | const | 50 | mirror | → `dev.uart_poll_idle_ms` — "mirrors sensortask_dev.py's own pair" |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py:16` | const | 3000 | tuned | `l3.uart_idle_poll_rate_sample_ms` — length of the idle-round count window |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py:20` | const | 5 | tuned | `l3.uart_idle_poll_rate_min_ratio` — "measured 20.6x; anything under 5x means the idle rate is not being selected" |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py:59` | kw | 1000 | not tagged (contract) | link timeout (agreed out of band) |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py:64` | call | 100 | deferred U26 | if kept: `l3.uart_idle_poll_rate_park_wait_ms` — fixed sleep "let it reach the parked wait before counting" |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py:68` | call | 250 | tuned | `l3.uart_idle_poll_rate_sample_step_ms` — feed step of the counting window (also the divisor in `SAMPLE_MS // 250`, :66) |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py:75` | call | 10 | tuned | `l3.uart_idle_poll_rate_stop_poll_ms` — poll step (40 rounds) of the wait for the listener to stop after clear() |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py:78` | call | 20 | tuned | `l3.uart_idle_poll_rate_cancel_settle_ms` — wait after cancelling a listener that did not stop |
| `tests_hardware/device_scripts/uart_idle_poll_rate.py:84` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:21` | const | 115200 | not tagged (contract) | baud / payload_size / timeout agreed out of band |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:22` | const | 48 | not tagged (contract) | baud / payload_size / timeout agreed out of band |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:23` | const | 1000 | not tagged (contract) | baud / payload_size / timeout agreed out of band |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:24` | const | 2 | mirror | → `dev.uart_poll_wait_ms` — equal to devices/dev.toml [bus.uart*] and used to build the same pair; the file lacks the "mirrors" comment its siblings carry (see Open points) |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:25` | const | 50 | mirror | → `dev.uart_poll_idle_ms` — as :24 |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:26` | const | 512 | mirror | → `dev.uart_rxbuf` — as :24 (rxbuf and txbuf; a second stacked tag names dev.uart_txbuf) |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:29` | const | 12000 | tuned | `l3.uart_link_under_concurrent_system_load_run_ms` — length of the loaded run |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:33` | const | 20 | tuned | `l3.uart_link_under_concurrent_system_load_min_transfers` — progress floor ("measured 58 unloaded … a floor, not a throughput target") |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:37` | const | 512 | tuned | `l3.uart_link_under_concurrent_system_load_churn_block` — allocation size of the churn task (load shape) |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:69` | call | 5 | tuned | `l3.uart_link_under_concurrent_system_load_sensor_load_step_ms` — pace of the two I2C load tasks |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:80` | call | 5 | tuned | `l3.uart_link_under_concurrent_system_load_sensor_load_step_ms` — pace of the two I2C load tasks |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:87` | call | 10 | tuned | `l3.uart_link_under_concurrent_system_load_spi_load_step_ms` — pace of the FRAM load task |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:104` | call | 2 | tuned | `l3.uart_link_under_concurrent_system_load_churn_step_ms` — pace of the heap churn |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:116` | call | 8 | tuned | `l3.uart_link_under_concurrent_system_load_heap_sample_step_ms` — pace of the heap sampler |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:121` | kw | 8000 | mirror | → `wdt.timeout_ms` — the boot entry's watchdog (A.U8.08 names this site) |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:142` | kw | 200000 | not tagged (config) | dev.toml [bus.i2c1] frequency/timeout restated for the isolated bus |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:183` | call | 5 | tuned | `l3.uart_link_under_concurrent_system_load_transfer_step_ms` — pause between link transfers |
| `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:191` | call | 50 | tuned | `l3.uart_link_under_concurrent_system_load_cancel_settle_ms` — wait for the cancelled load tasks to unwind |
| `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:12` | const | 115200 | not tagged (contract) | link baud rate (agreed out of band) |
| `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:13` | const | 53 | not tagged (derived) | one framed frame at payload_size=48 (contract) |
| `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:14` | const | 5 | tuned | `l3.uart_read_never_blocks_the_loop_trials` — trials per read shape |
| `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:28` | kw | 1 | test input | raw port configuration whose per-byte wait the pre-fix measurement exposes (the stimulus) |
| `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:29` | kw | 1 | test input | raw port configuration whose per-byte wait the pre-fix measurement exposes (the stimulus) |
| `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:48` | call | 30 | tuned | `l3.uart_read_never_blocks_the_loop_trial_gap_ms` — pause between trials |
| `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py:63` | call | 30 | tuned | `l3.uart_read_never_blocks_the_loop_trial_gap_ms` — pause between trials |
| `tests_hardware/device_scripts/watchdog_starvation_reset.py:7` | const | 1500 | tuned | `l3.starvation_wdt_ms` — the short starvation watchdog |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:15` | const | 2 | not tagged (identifier) | CYW43 STAT_OBTAINING_IP (as asy_wifi_service.py's own constant) |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:76` | kw | 240 | tuned | `l3.wifi_reconnect_after_failed_attempts_repro_control_max_polls` — control-phase poll budget ("up to 120s") |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:76` | kw | 500 | mirror | → `wifi.sta_connect_poll_s` — wait_for_outcome() is "same shape as asy_wifi_service.py's own _poll_sta_connect_status()" with "its own 0.5s poll interval" (:37-38, :86-87); 500 = 0.5 s x 1000 |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:83` | call | 1 | deferred U26 | if kept: `l3.wifi_reconnect_after_failed_attempts_repro_disconnect_settle_s` — fixed sleep after the control-phase disconnect |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:94` | kw | 10 | mirror | → `wifi.sta_connect_poll_iters` — the treatment attempt window mirrors the product's 10-poll connect status loop (:86-87) |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:94` | kw | 500 | mirror | → `wifi.sta_connect_poll_s` — wait_for_outcome() is "same shape as asy_wifi_service.py's own _poll_sta_connect_status()" with "its own 0.5s poll interval" (:37-38, :86-87); 500 = 0.5 s x 1000 |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:96` | call | 5 | mirror | → `wifi.refresh_s` — "wifi_refresh_sec cadence" |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:104` | call | 2 | mirror | → `wifi.wlan_down_settle_s` — the 2 s after active(False) in the mirrored _switch_wlan_mode() sequence (asy_wifi_service.py:283) |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:106` | call | 1 | mirror | → `wifi.wlan_deinit_settle_s` — the 1 s after deinit() in that sequence (asy_wifi_service.py:286) |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:114` | call | 10 | tuned | `l3.wifi_reconnect_after_failed_attempts_repro_ap_dwell_s` — "a brief real hotspot dwell" (stimulus length) |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:118` | call | 2 | mirror | → `wifi.wlan_down_settle_s` — the 2 s after active(False) in the mirrored _switch_wlan_mode() sequence (asy_wifi_service.py:283) |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:120` | call | 1 | mirror | → `wifi.wlan_deinit_settle_s` — the 1 s after deinit() in that sequence (asy_wifi_service.py:286) |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:122` | call | 1 | mirror | → `wifi.wlan_mode_settle_s` — the 1 s after the new WLAN object in that sequence (asy_wifi_service.py:290) |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:134` | kw | 1200 | tuned | `l3.wifi_reconnect_after_failed_attempts_repro_reconnect_max_polls` — treatment reconnect poll budget ("up to 600s") |
| `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py:134` | kw | 500 | mirror | → `wifi.sta_connect_poll_s` — wait_for_outcome() is "same shape as asy_wifi_service.py's own _poll_sta_connect_status()" with "its own 0.5s poll interval" (:37-38, :86-87); 500 = 0.5 s x 1000 |
| `tests_hardware/device_scripts/wifi_service_reconnect_repro.py:89` | deadline | 180000 | tuned | `l3.wifi_service_reconnect_repro_hotspot_deadline_ms` — "up to 3 minutes to reach hotspot" |
| `tests_hardware/device_scripts/wifi_service_reconnect_repro.py:103` | call | 1 | tuned | `l3.wifi_service_reconnect_repro_poll_s` — observation poll step |
| `tests_hardware/device_scripts/wifi_service_reconnect_repro.py:119` | deadline | 600000 | tuned | `l3.wifi_service_reconnect_repro_reconnect_deadline_ms` — "up to 10 minutes" observation deadline |
| `tests_hardware/device_scripts/wifi_service_reconnect_repro.py:135` | call | 1 | tuned | `l3.wifi_service_reconnect_repro_poll_s` — observation poll step |
| `tests_hardware/error_log_helpers.py:14` | const | 30.0 | tuned | `l4.reset_errors_timeout_s` — ResetErrors PUT bound |
| `tests_hardware/error_log_helpers.py:23` | kw | 10.0 | tuned | `l4.error_log_helpers_errcount_timeout_s` — GET /status timeout of get_errcount() |
| `tests_hardware/flash/conftest.py:32` | kw | 90.0 | tuned | `l3.conftest_scd30_rw_script_timeout_s` — host bound on the fixture's device-script run (the script bounds itself at 60 s internally) |
| `tests_hardware/flash/test_bus_concurrency.py:34` | kw | 120.0 | tuned | `l3.bus_concurrency_long_script_timeout_s` — host bound on a device script whose own internal bound is 90 s ("Generous relative to the device script's own ~90s", :33) |
| `tests_hardware/flash/test_bus_concurrency.py:40` | kw | 90.0 | tuned | `l3.bus_concurrency_script_timeout_s` — host bound on a device script whose own internal bound is 60 s or less |
| `tests_hardware/flash/test_bus_concurrency.py:49` | kw | 120.0 | tuned | `l3.bus_concurrency_long_script_timeout_s` — host bound on a device script whose own internal bound is 90 s ("Generous relative to the device script's own ~90s", :33) |
| `tests_hardware/flash/test_bus_concurrency.py:56` | kw | 90.0 | tuned | `l3.bus_concurrency_script_timeout_s` — host bound on a device script whose own internal bound is 60 s or less |
| `tests_hardware/flash/test_bus_concurrency.py:64` | kw | 90.0 | tuned | `l3.bus_concurrency_script_timeout_s` — host bound on a device script whose own internal bound is 60 s or less |
| `tests_hardware/flash/test_bus_concurrency.py:72` | kw | 90.0 | tuned | `l3.bus_concurrency_script_timeout_s` — host bound on a device script whose own internal bound is 60 s or less |
| `tests_hardware/flash/test_bus_concurrency.py:81` | kw | 90.0 | tuned | `l3.bus_concurrency_script_timeout_s` — host bound on a device script whose own internal bound is 60 s or less |
| `tests_hardware/flash/test_bus_concurrency.py:91` | kw | 90.0 | tuned | `l3.bus_concurrency_script_timeout_s` — host bound on a device script whose own internal bound is 60 s or less |
| `tests_hardware/flash/test_bus_concurrency.py:99` | kw | 90.0 | tuned | `l3.bus_concurrency_script_timeout_s` — host bound on a device script whose own internal bound is 60 s or less |
| `tests_hardware/flash/test_bus_concurrency.py:107` | kw | 90.0 | tuned | `l3.bus_concurrency_script_timeout_s` — host bound on a device script whose own internal bound is 60 s or less |
| `tests_hardware/flash/test_bus_concurrency.py:115` | kw | 90.0 | tuned | `l3.bus_concurrency_script_timeout_s` — host bound on a device script whose own internal bound is 60 s or less |
| `tests_hardware/flash/test_bus_concurrency.py:123` | kw | 60.0 | tuned | `l3.bus_concurrency_short_script_timeout_s` — host bound on the fault-injection / verify / deinit scripts |
| `tests_hardware/flash/test_bus_concurrency.py:131` | kw | 30.0 | tuned | `l3.bus_concurrency_reset_script_timeout_s` — host bound on the script expected to reset the board |
| `tests_hardware/flash/test_bus_concurrency.py:135` | call | 30.0 | tuned | `l3.bus_concurrency_reachable_timeout_s` — deadline for the board to be reachable after the reset |
| `tests_hardware/flash/test_bus_concurrency.py:135` | call | 1.0 | tuned | `l3.bus_concurrency_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_bus_concurrency.py:135` | kw | 30.0 | tuned | `l3.bus_concurrency_reachable_timeout_s` — deadline for the board to be reachable after the reset |
| `tests_hardware/flash/test_bus_concurrency.py:135` | kw | 1.0 | tuned | `l3.bus_concurrency_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_bus_concurrency.py:136` | kw | 60.0 | tuned | `l3.bus_concurrency_short_script_timeout_s` — host bound on the fault-injection / verify / deinit scripts |
| `tests_hardware/flash/test_bus_concurrency.py:148` | kw | 60.0 | tuned | `l3.bus_concurrency_short_script_timeout_s` — host bound on the fault-injection / verify / deinit scripts |
| `tests_hardware/flash/test_bus_electrical_timing.py:59` | kw | 30.0 | tuned | `l3.bus_electrical_timing_irq_script_timeout_s` — host bound on scd30_real_irq_edge.py |
| `tests_hardware/flash/test_bus_electrical_timing.py:107` | const-c | 2 | tuned | `l3.bus_electrical_timing_wrap_headroom_h` — the two hours of headroom below 2**30 ("wider than the poll interval below"); the same key also covers the 2 of `2**30`, a fact |
| `tests_hardware/flash/test_bus_electrical_timing.py:107` | const-c | 30 | not tagged (fact) | ticks_ms() period 2**30 ms |
| `tests_hardware/flash/test_bus_electrical_timing.py:107` | const-c | 1000 | not tagged (fact) | ms per second |
| `tests_hardware/flash/test_bus_electrical_timing.py:107` | const-c | 60 | not tagged (fact) | minutes per hour / seconds per minute |
| `tests_hardware/flash/test_fram_storage.py:33` | kw | 30.0 | tuned | `l3.fram_storage_short_script_timeout_s` — host bound on the quick FRAM scripts (and the one expected to reset) |
| `tests_hardware/flash/test_fram_storage.py:44` | kw | 150.0 | tuned | `l3.fram_storage_backup_script_timeout_s` — host bound on sgp40_fram_backup_restore.py ("~90s real runtime … generous"); Dependant of l3.sgp40_fram_backup_restore_backup_wait_s |
| `tests_hardware/flash/test_fram_storage.py:53` | kw | 30.0 | tuned | `l3.fram_storage_short_script_timeout_s` — host bound on the quick FRAM scripts (and the one expected to reset) |
| `tests_hardware/flash/test_fram_storage.py:60` | kw | 30.0 | tuned | `l3.fram_storage_short_script_timeout_s` — host bound on the quick FRAM scripts (and the one expected to reset) |
| `tests_hardware/flash/test_fram_storage.py:61` | call | 30.0 | tuned | `l3.fram_storage_reachable_timeout_s` — deadline for the board to be reachable after the reset |
| `tests_hardware/flash/test_fram_storage.py:61` | call | 1.0 | tuned | `l3.fram_storage_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_fram_storage.py:61` | kw | 30.0 | tuned | `l3.fram_storage_reachable_timeout_s` — deadline for the board to be reachable after the reset |
| `tests_hardware/flash/test_fram_storage.py:61` | kw | 1.0 | tuned | `l3.fram_storage_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_fram_storage.py:62` | kw | 60.0 | tuned | `l3.fram_storage_script_timeout_s` — host bound on the verify / boot-window / capacity scripts |
| `tests_hardware/flash/test_fram_storage.py:73` | kw | 60.0 | tuned | `l3.fram_storage_script_timeout_s` — host bound on the verify / boot-window / capacity scripts |
| `tests_hardware/flash/test_fram_storage.py:87` | kw | 30.0 | tuned | `l3.fram_storage_short_script_timeout_s` — host bound on the quick FRAM scripts (and the one expected to reset) |
| `tests_hardware/flash/test_fram_storage.py:101` | kw | 90.0 | tuned | `l3.fram_storage_pause_script_timeout_s` — host bound on fram_pause_unpause_and_gating.py (its real pause windows, :98-100) |
| `tests_hardware/flash/test_fram_storage.py:112` | kw | 45.0 | tuned | `l3.fram_storage_lockout_script_timeout_s` — host bound on fram_busy_status_lockout.py |
| `tests_hardware/flash/test_fram_storage.py:123` | kw | 60.0 | tuned | `l3.fram_storage_script_timeout_s` — host bound on the verify / boot-window / capacity scripts |
| `tests_hardware/flash/test_memory_stress.py:25` | const | 16384 | not tagged (fact) | Microdot v2.6.2's max_body_length default (16384 B), the worst-case unit every figure is a multiple of (comment :22-24) |
| `tests_hardware/flash/test_memory_stress.py:35` | kw | 120.0 | tuned | `l3.memory_stress_headroom_script_timeout_s` — host bound on heap_headroom_after_full_system_build.py |
| `tests_hardware/flash/test_reboot_persistence.py:36` | call | 30.0 | tuned | `l3.reboot_persistence_reachable_timeout_s` — deadline for the board to be reachable after the hard reset |
| `tests_hardware/flash/test_reboot_persistence.py:36` | call | 1.0 | tuned | `l3.reboot_persistence_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_reboot_persistence.py:36` | kw | 30.0 | tuned | `l3.reboot_persistence_reachable_timeout_s` — deadline for the board to be reachable after the hard reset |
| `tests_hardware/flash/test_reboot_persistence.py:36` | kw | 1.0 | tuned | `l3.reboot_persistence_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_reboot_persistence.py:64` | kw | 20.0 | tuned | `l3.reboot_persistence_boot_log_tail_s` — passive log window over the undisturbed boot |
| `tests_hardware/flash/test_reboot_persistence.py:79` | call | 30.0 | tuned | `l3.reboot_persistence_reachable_timeout_s` — deadline for the board to be reachable after the hard reset |
| `tests_hardware/flash/test_reboot_persistence.py:79` | call | 1.0 | tuned | `l3.reboot_persistence_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_reboot_persistence.py:79` | kw | 30.0 | tuned | `l3.reboot_persistence_reachable_timeout_s` — deadline for the board to be reachable after the hard reset |
| `tests_hardware/flash/test_reboot_persistence.py:79` | kw | 1.0 | tuned | `l3.reboot_persistence_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_sensor_accuracy.py:24` | kw | 100.0 | tuned | `l3.sensor_accuracy_scd30_script_timeout_s` — host bound on scd30_plausibility_read.py ("~60s real runtime … generous"); Dependant of l3.scd30_plausibility_read_settle_s |
| `tests_hardware/flash/test_sensor_accuracy.py:31` | kw | 60.0 | tuned | `l3.sensor_accuracy_bmp3xx_script_timeout_s` — host bound on bmp3xx_plausibility_read.py |
| `tests_hardware/flash/test_sensor_accuracy.py:40` | kw | 150.0 | tuned | `l3.sensor_accuracy_sgp40_script_timeout_s` — host bound on sgp40_voc_algorithm_quality.py ("~90s real runtime"); Dependant of l3.sgp40_voc_algorithm_quality_blackout_wait_s |
| `tests_hardware/flash/test_sensor_accuracy.py:48` | kw | 30.0 | tuned | `l3.sensor_accuracy_isl29125_script_timeout_s` — host bound on isl29125_plausibility_read.py ("~15s worst-case wait window") |
| `tests_hardware/flash/test_sensor_accuracy.py:61` | kw | 420.0 | tuned | `l3.sensor_accuracy_envelope_script_timeout_s` — host bound on isl29125_mechanism_envelope.py (22 holds x SETTLE_S + MAX_WAIT_S, :58-60); Dependant of l3.isl29125_mechanism_envelope_settle_s and _max_wait_s |
| `tests_hardware/flash/test_sensor_accuracy.py:74` | kw | 900.0 | tuned | `l3.sensor_accuracy_scenarios_script_timeout_s` — host bound on isl29125_lighting_scenarios.py (~8.5 min of segments, :72-73) |
| `tests_hardware/flash/test_sensor_accuracy.py:84` | kw | 120.0 | tuned | `l3.sensor_accuracy_conformance_script_timeout_s` — host bound on isl29125_mock_conformance_probe.py |
| `tests_hardware/flash/test_task_supervisor.py:19` | kw | 15.0 | tuned | `l3.task_supervisor_script_timeout_s` — host bound on system_service_restarts_a_real_dead_task.py (~3.5 s of observation) |
| `tests_hardware/flash/test_toolchain_flash_boot.py:39` | kw | 1200 | tuned | `l3.toolchain_flash_boot_env_setup_timeout_s` — subprocess bound of the flash-tier env run ("~481s wall clock on this bench's Pi4; 1200s leaves headroom", :30-31) |
| `tests_hardware/flash/test_toolchain_flash_boot.py:65` | kw | 600 | tuned | `l3.toolchain_flash_boot_build_timeout_s` — subprocess bound of build_firmware.py dev |
| `tests_hardware/flash/test_toolchain_flash_boot.py:82` | kw | 120 | tuned | `l3.toolchain_flash_boot_load_timeout_s` — subprocess bound of one picotool load attempt |
| `tests_hardware/flash/test_toolchain_flash_boot.py:87` | call | 2.0 | tuned | `l3.toolchain_flash_boot_load_retry_backoff_s` — pause between picotool load attempts |
| `tests_hardware/flash/test_toolchain_flash_boot.py:92` | call | 30.0 | tuned | `l3.toolchain_flash_boot_reachable_timeout_s` — deadline for the board after the reflash |
| `tests_hardware/flash/test_toolchain_flash_boot.py:92` | call | 1.0 | tuned | `l3.toolchain_flash_boot_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_toolchain_flash_boot.py:92` | kw | 30.0 | tuned | `l3.toolchain_flash_boot_reachable_timeout_s` — deadline for the board after the reflash |
| `tests_hardware/flash/test_toolchain_flash_boot.py:92` | kw | 1.0 | tuned | `l3.toolchain_flash_boot_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_uart_crossover.py:47` | kw | 120.0 | tuned | `l3.uart_crossover_script_timeout_s` — host bound on the exchange / blocking-read scripts |
| `tests_hardware/flash/test_uart_crossover.py:54` | kw | 180.0 | tuned | `l3.uart_crossover_long_script_timeout_s` — host bound on the recovery / idle-rate / loaded-link scripts |
| `tests_hardware/flash/test_uart_crossover.py:62` | kw | 120.0 | tuned | `l3.uart_crossover_script_timeout_s` — host bound on the exchange / blocking-read scripts |
| `tests_hardware/flash/test_uart_crossover.py:69` | kw | 120.0 | tuned | `l3.uart_crossover_script_timeout_s` — host bound on the exchange / blocking-read scripts |
| `tests_hardware/flash/test_uart_crossover.py:76` | kw | 180.0 | tuned | `l3.uart_crossover_long_script_timeout_s` — host bound on the recovery / idle-rate / loaded-link scripts |
| `tests_hardware/flash/test_uart_crossover.py:84` | kw | 180.0 | tuned | `l3.uart_crossover_long_script_timeout_s` — host bound on the recovery / idle-rate / loaded-link scripts |
| `tests_hardware/flash/test_watchdog_starvation.py:23` | kw | 15.0 | tuned | `l3.watchdog_starvation_script_timeout_s` — host bound on watchdog_starvation_reset.py |
| `tests_hardware/flash/test_watchdog_starvation.py:29` | assert | 10.0 | tuned | `l3.watchdog_starvation_reset_elapsed_max_s` — bound on the observed reset (the 1.5 s watchdog plus the disconnect detection); Dependant of l3.starvation_wdt_ms |
| `tests_hardware/flash/test_watchdog_starvation.py:41` | call | 15.0 | tuned | `l3.watchdog_starvation_device_present_timeout_s` — deadline for the USB device node to reappear |
| `tests_hardware/flash/test_watchdog_starvation.py:41` | call | 0.3 | tuned | `l3.watchdog_starvation_device_present_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_watchdog_starvation.py:41` | kw | 15.0 | tuned | `l3.watchdog_starvation_device_present_timeout_s` — deadline for the USB device node to reappear |
| `tests_hardware/flash/test_watchdog_starvation.py:41` | kw | 0.3 | tuned | `l3.watchdog_starvation_device_present_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_watchdog_starvation.py:42` | call | 15.0 | tuned | `l3.watchdog_starvation_reachable_after_reset_timeout_s` — deadline for mpremote to talk to the board again |
| `tests_hardware/flash/test_watchdog_starvation.py:42` | call | 0.5 | tuned | `l3.watchdog_starvation_reachable_after_reset_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_watchdog_starvation.py:42` | kw | 15.0 | tuned | `l3.watchdog_starvation_reachable_after_reset_timeout_s` — deadline for mpremote to talk to the board again |
| `tests_hardware/flash/test_watchdog_starvation.py:42` | kw | 0.5 | tuned | `l3.watchdog_starvation_reachable_after_reset_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_watchdog_starvation.py:47` | call | 15.0 | tuned | `l3.watchdog_starvation_device_present_timeout_s` — deadline for the USB device node to reappear |
| `tests_hardware/flash/test_watchdog_starvation.py:47` | call | 0.3 | tuned | `l3.watchdog_starvation_device_present_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_watchdog_starvation.py:47` | kw | 15.0 | tuned | `l3.watchdog_starvation_device_present_timeout_s` — deadline for the USB device node to reappear |
| `tests_hardware/flash/test_watchdog_starvation.py:47` | kw | 0.3 | tuned | `l3.watchdog_starvation_device_present_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_watchdog_starvation.py:51` | const | 3 | not tagged (identifier) | machine.WDT_RESET on rp2 |
| `tests_hardware/flash/test_watchdog_starvation.py:58` | call | 30.0 | tuned | `l3.watchdog_starvation_reachable_timeout_s` — deadline for the board before the fallback run |
| `tests_hardware/flash/test_watchdog_starvation.py:58` | call | 1.0 | tuned | `l3.watchdog_starvation_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_watchdog_starvation.py:58` | kw | 30.0 | tuned | `l3.watchdog_starvation_reachable_timeout_s` — deadline for the board before the fallback run |
| `tests_hardware/flash/test_watchdog_starvation.py:58` | kw | 1.0 | tuned | `l3.watchdog_starvation_reachable_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_watchdog_starvation.py:62` | kw | 20.0 | tuned | `l3.watchdog_starvation_fallback_script_timeout_s` — host bound on reboot_fallback_starves_the_watchdog.py |
| `tests_hardware/flash/test_watchdog_starvation.py:68` | assert | 12.0 | tuned | `l3.watchdog_starvation_fallback_elapsed_max_s` — "the script's watchdog is armed for 1.5s, so something else timed out"; Dependant of l3.starvation_wdt_ms |
| `tests_hardware/flash/test_watchdog_starvation.py:72` | call | 15.0 | tuned | `l3.watchdog_starvation_device_present_timeout_s` — deadline for the USB device node to reappear |
| `tests_hardware/flash/test_watchdog_starvation.py:72` | call | 0.3 | tuned | `l3.watchdog_starvation_device_present_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_watchdog_starvation.py:72` | kw | 15.0 | tuned | `l3.watchdog_starvation_device_present_timeout_s` — deadline for the USB device node to reappear |
| `tests_hardware/flash/test_watchdog_starvation.py:72` | kw | 0.3 | tuned | `l3.watchdog_starvation_device_present_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_watchdog_starvation.py:77` | call | 15.0 | tuned | `l3.watchdog_starvation_device_present_timeout_s` — deadline for the USB device node to reappear |
| `tests_hardware/flash/test_watchdog_starvation.py:77` | call | 0.3 | tuned | `l3.watchdog_starvation_device_present_poll_s` — poll step of that wait |
| `tests_hardware/flash/test_watchdog_starvation.py:77` | kw | 15.0 | tuned | `l3.watchdog_starvation_device_present_timeout_s` — deadline for the USB device node to reappear |
| `tests_hardware/flash/test_watchdog_starvation.py:77` | kw | 0.3 | tuned | `l3.watchdog_starvation_device_present_poll_s` — poll step of that wait |
| `tests_hardware/harness.py:56` | param | 1.0 | tuned | `l4.ceiling_settle_s` — ceiling instrument default |
| `tests_hardware/harness.py:56` | param | 0.3 | tuned | `l4.ceiling_dwell_s` — ceiling instrument default |
| `tests_hardware/harness.py:113` | param | 2.0 | tuned | `l4.ceiling_probe_connect_timeout_s` — ceiling probe connect timeout |
| `tests_hardware/harness.py:138` | param | 10.0 | tuned | `l4.ceiling_drain_timeout_s` — drain wait default |
| `tests_hardware/harness.py:138` | param | 1.0 | tuned | `l4.ceiling_drain_release_s` — drain wait default |
| `tests_hardware/harness.py:138` | param | 0.3 | tuned | `l4.ceiling_drain_hold_s` — drain wait default |
| `tests_hardware/harness.py:165` | call | 0.05 | tuned | `l4.ceiling_hold_check_timeout_s` — per-socket read window of the "still held" check at the refusal; an instrument value A.U8.05 does not list (G1/R15) |
| `tests_hardware/harness.py:201` | kw | 10.0 | tuned | `l4.harness_usb_rebind_cmd_timeout_s` — subprocess bound on each sysfs unbind/bind write |
| `tests_hardware/harness.py:202` | call | 2.0 | deferred U26 | if kept: `l4.harness_usb_unbind_settle_s` — fixed sleep after the USB unbind before the bind |
| `tests_hardware/harness.py:203` | kw | 10.0 | tuned | `l4.harness_usb_rebind_cmd_timeout_s` — subprocess bound on each sysfs unbind/bind write |
| `tests_hardware/harness.py:204` | call | 3.0 | deferred U26 | if kept: `l4.harness_usb_rebind_settle_s` — fixed sleep for re-enumeration after the bind |
| `tests_hardware/harness.py:224` | param | 1.0 | tuned | `l4.harness_wait_until_poll_s` — wait_until()'s default poll step |
| `tests_hardware/harness.py:257` | kw | 10.0 | tuned | `l4.harness_serving_probe_timeout_s` — per-probe HTTP timeout while waiting for the DUT to serve again |
| `tests_hardware/harness.py:258` | call | 90.0 | tuned | `l4.harness_serving_restore_timeout_s` — deadline for the DUT to serve after a hard reset (one literal, reported as call and kw) |
| `tests_hardware/harness.py:258` | kw | 90.0 | tuned | `l4.harness_serving_restore_timeout_s` — deadline for the DUT to serve after a hard reset (one literal, reported as call and kw) |
| `tests_hardware/harness.py:259` | call | 3.0 | tuned | `l4.harness_serving_restore_poll_s` — poll step of that wait (one literal, reported as call and kw) |
| `tests_hardware/harness.py:259` | kw | 3.0 | tuned | `l4.harness_serving_restore_poll_s` — poll step of that wait (one literal, reported as call and kw) |
| `tests_hardware/harness.py:264` | param | 120.0 | tuned | `l4.harness_script_server_timeout_s` — deadline for a device script's own server to answer |
| `tests_hardware/harness.py:264` | param | 20.0 | tuned | `l4.harness_script_server_handover_s` — wait for main.py's server to go quiet first |
| `tests_hardware/harness.py:272` | kw | 3.0 | tuned | `l4.harness_script_server_probe_timeout_s` — per-probe HTTP timeout of that wait |
| `tests_hardware/harness.py:304` | const | 2 | tuned | `l4.harness_max_device_rebinds` — retry count of the USB rebind escalation |
| `tests_hardware/harness.py:345` | param | 60.0 | tuned | `l4.harness_mpremote_default_timeout_s` — default subprocess bound of one mpremote call |
| `tests_hardware/harness.py:368` | deadline | 10.0 | tuned | `l4.harness_usb_grace_s` — grace window for a transient USB/serial failure |
| `tests_hardware/harness.py:389` | call | 0.5 | tuned | `l4.harness_usb_grace_poll_s` — retry step inside that grace window |
| `tests_hardware/harness.py:399` | deadline | 10.0 | tuned | `l4.harness_usb_grace_s` — grace window for a transient USB/serial failure |
| `tests_hardware/harness.py:404` | deadline | 10.0 | tuned | `l4.harness_usb_grace_s` — grace window for a transient USB/serial failure |
| `tests_hardware/harness.py:413` | kw | 10.0 | tuned | `l4.harness_mpremote_short_timeout_s` — bound of a probe exec / the bootloader drop |
| `tests_hardware/harness.py:423` | kw | 0.2 | tuned | `l4.harness_presence_probe_timeout_s` — serial open/read timeout of is_device_present() |
| `tests_hardware/harness.py:462` | kw | 15.0 | tuned | `l4.harness_mpremote_reset_timeout_s` — bound of a soft reset / reset |
| `tests_hardware/harness.py:470` | kw | 15.0 | tuned | `l4.harness_mpremote_reset_timeout_s` — bound of a soft reset / reset |
| `tests_hardware/harness.py:480` | kw | 10.0 | tuned | `l4.harness_mpremote_short_timeout_s` — bound of a probe exec / the bootloader drop |
| `tests_hardware/harness.py:486` | deadline | 10.0 | tuned | `l4.harness_usb_grace_s` — grace window for a transient USB/serial failure |
| `tests_hardware/harness.py:491` | kw | 0.5 | tuned | `l4.harness_log_tail_read_timeout_s` — serial read timeout of the passive log tail |
| `tests_hardware/harness.py:499` | call | 0.5 | tuned | `l4.harness_usb_grace_poll_s` — retry step inside that grace window |
| `tests_hardware/heap_map.py:13` | const | 64 | not tagged (fact) | blocks per line of MicroPython mem_info(1) output |
| `tests_hardware/http_client.py:28` | param | 10.0 | tuned | `l4.http_client_fetch_timeout_s` — default per-request timeout of the bench HTTP client |
| `tests_hardware/isl29125_conformance.py:56` | param | 180.0 | tuned | `l3.isl29125_conformance_probe_timeout_s` — default bound of the twin conformance probe run |
| `tests_hardware/manual/manual_bus_electrical.py:27` | kw | 30.0 | tuned | `l4.manual_bus_electrical_recovery_watch_s` — log window for evidence of recovery |
| `tests_hardware/manual/manual_bus_electrical.py:44` | kw | 30.0 | tuned | `l4.manual_bus_electrical_reboot_watch_s` — log window for a reboot ("generous relative to the 8388ms WDT cap") |
| `tests_hardware/manual/manual_sensor_accuracy.py:14` | const | 50.0 | not tagged (fact) | BMP388 datasheet accuracy figures (comment :9-13) |
| `tests_hardware/manual/manual_sensor_accuracy.py:15` | const | 0.5 | not tagged (fact) | BMP388 datasheet accuracy figures (comment :9-13) |
| `tests_hardware/manual/manual_sensor_accuracy.py:37` | const | 10 | not tagged (fact) | SGP40 datasheet Table 1 response times (comment :35-36) |
| `tests_hardware/manual/manual_sensor_accuracy.py:38` | const | 30 | not tagged (fact) | SGP40 datasheet Table 1 response times (comment :35-36) |
| `tests_hardware/manual/manual_sensor_accuracy.py:59` | const | 10.0 | tuned | `l4.manual_sensor_accuracy_isl29125_repeatability_pct` — by-hand repeatability tolerance on one scene |
| `tests_hardware/manual/manual_toolchain.py:28` | kw | 600 | tuned | `l3.toolchain_flash_boot_build_timeout_s` — the same build_firmware.py dev subprocess bound as flash/test_toolchain_flash_boot.py:65 (shared ID) |
| `tests_hardware/manual/manual_toolchain.py:42` | kw | 120 | tuned | `l3.toolchain_flash_boot_load_timeout_s` — the same picotool load bound as flash/test_toolchain_flash_boot.py:82 (shared ID) |
| `tests_hardware/manual/runner.py:46` | call | 1 | not tagged (derived) | the 1 s step of the operator countdown (a unit) |
| `tests_hardware/ntp_probe.py:9` | const | 2208988800 | not tagged (fact) | NTP-to-Unix epoch offset (RFC 5905) |
| `tests_hardware/rogue_udp_responder.py:15` | call | 0.5 | tuned | `l4.rogue_udp_responder_recv_timeout_s` — per-recvfrom bound so stop() interrupts promptly |
| `tests_hardware/rogue_udp_responder.py:38` | kw | 5.0 | tuned | `l4.rogue_udp_responder_join_timeout_s` — thread join bound in stop() |
| `tests_hardware/soak_tiers.py:7` | const-c | 60.0 | tuned | `l4.soak_tiers_short_s` — short soak tier (G4/R54 "soak durations") |
| `tests_hardware/soak_tiers.py:7` | const-c | 600.0 | tuned | `l4.soak_tiers_mid_s` — mid soak tier |
| `tests_hardware/soak_tiers.py:7` | const-c | 6 | tuned | `l4.soak_tiers_long_h` — long soak tier in hours; the tag carries `6` because the dict writes `6 * 3600.0` |
| `tests_hardware/soak_tiers.py:7` | const-c | 3600.0 | not tagged (fact) | seconds per hour (the unit scale of the long tier) |
## Search gaps met while classifying (not hits of C.0.1, so not in the table)

Found in context while opening hits; each is a tuned value of a G4/R54 family the corrected search still misses.
They are recorded for A-C; not classified here beyond what is stated.

1. `tests/_webserver_concurrency_scenarios.py:277-790` — 20 per-scenario hang budgets passed **positionally**
   to `_register(name, timeout_s)` (15.0, 20.0, 30.0, 40.0, 60.0). C.0.1's kw rule sees only keyword syntax, and
   the param rule sees only defaults. Same shape as the per-file hang bounds: one constant per distinct value,
   `l2.webserver_concurrency_scenarios_<name>_s`.
2. `tests/test_asy_uart_comm.py:949` — `scenario(1300)`, a holder kept past "the driver's own 1000ms
   acknowledgement bound" (positional, so not a hit). It is a Dependant of `uart.cancel_ack_timeout_ms` and
   moves with it: named `_PAST_CANCEL_ACK_HOLD_MS = 1300` and listed as that row's Dependant.
3. `tests/test_digital_twin_bus_hazard_concurrency.py:185, :199, :213, :227` — `run_seconds=9.0`, the run
   window of the real task graph (the keyword ends in `_seconds`, not `_s`, so the kw rule misses it). It is
   the "9 s budget" SPEC E.3.1 ties to `l1.unix_heapsize` (A.U8.15): tuned, one constant
   `_RUN_SECONDS = 9.0`, `l2.bus_hazard_concurrency_run_seconds`, with `l1.unix_heapsize` naming it as a
   Dependant.
4. `tests/test_digital_twin_uart_link.py:379, :475` — `assert leaked < 8192`,
   a heap-retention budget; `leaked` matches none of C.0.1's assert names. Tuned (G4/R54 "allocation and
   heap-rate budgets"): `_LEAK_BUDGET_BYTES = 8192`, `l2.uart_link_leak_budget_bytes`.
5. `threading.Event.wait(N)` / `stop.wait(N)` poll steps (7 sites: `tests_hardware/harness.py:278, :284`, `tests_hardware/bench/test_heap_under_connection_ceiling.py:62, :78, :101` — ceiling-instrument pacing, G1/R15 — and `tests_hardware/bench/test_memory_stress_bench.py:61, :156`) — the call
   name `wait` is outside C.0.1's call list (`sleep…|wait_for…|wait_until|settimeout|timeout`). They are poll
   steps or request pacing of real waits: tuned, one constant per purpose (`grep -rn '\.wait([0-9]' tests_hardware tests`
   lists them).
6. Margins written inside arithmetic with a name, e.g. `PAUSE_SEC + 1.5` and `REARM_SEC - PAUSE_SEC + 0.5`
   (`tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:81, :95, :97, :119`) — C.0.1's const-c
   accepts literal-only arithmetic and no other kind reads a BinOp operand. The margin is tuned: one
   constant per purpose (`_PAUSE_MARGIN_S = 1.5`, `_REARM_MARGIN_S = 0.5`).
7. Lower-case local timing variables, e.g. `poll_interval_s = 3600.0` and the `+ 60` headroom in
   `target_wait_s` (`tests_hardware/flash/test_bus_electrical_timing.py:114, :116`) — the const rule reads
   upper-case targets only. Tuned: promoted to named constants with their own IDs when this file is tagged.

## Deferred sites (classification working list only)

C.0.2 "Deferred": fixed sleeps U25 (twin) or U26 (hardware) decide on under G7/R23. They carry no tag and
no Part N row now; the provisional ID in the table is what each becomes if that unit keeps it. 13 hits
deferred to U25, 14 to U26 (the table lists every site). The fixed sleeps G7/R23 itself keeps — a probe
would occupy a slot or share the heap under measurement — are classified tuned, not deferred
(`tests_hardware/bench/test_network_resilience.py` slot-release waits, `tests_hardware/device_scripts/heap_under_connection_ceiling.py:44`,
`serving_at_default_gc.py:27`).

## Ledger
| register block | clause for this unit (short) | result |
|---|---|---|
| G4/R54 | code in U8 — `@tunable` tags and register; the U8 NOT-DONE item: per-value classification of the `tests/` and `tests_hardware/` candidates (U8 Ledger, register fix 6) | DONE in this file: all 2,265 C.0.1 hits in 156 files classified; actions A.U8C.01-A.U8C.119 (one per file holding a tuned, mirror or deferred hit). No file NOT-DONE |
| G1/R15 | tags in U8 — every instrument value a registered tunable | two instrument values A.U8.05 does not list: `tests_hardware/harness.py:165` (`l4.ceiling_hold_check_timeout_s`), `tests_hardware/bench/test_heap_under_connection_ceiling.py:49` (`l4.ceiling_holder_socket_timeout_s`), in the actions for those files; Register fixes (G1/R15 item) |
| G8/R31 | tunables in U8 (every test bounded; the bounds are tunables) | every `run`/`run_timed`/`wait_for`/`limit=`/`join`/`run_isolated`/subprocess hang bound among the hits is tuned, one constant per file per distinct value (C.0.2) |
| G7/R23 | tunable in U8 (kept sleeps) | kept sleeps tuned (see "Deferred sites"); 27 fixed sleeps deferred to U25/U26 |

## Register fixes

- **`audit/actions/U8.md` A.U8.11 Blast** lists `tests/test_captive_dns.py:1067` (4700-5400 ms) as a mirror
  site of `dns_server.recv_backoff_max_s`. By C.0.2's mechanical test it is not: neither literal equals 5000.
  It is a tolerance band around the cap. Fix: "`:1067` is a Dependant of `dns_server.recv_backoff_max_s`
  (its own tuned band edges, A.U8C)". `:952` (3000) stays a mirror of `dns_server.error_retry_wait_s`.
- **`audit/actions/U8.md` A.U8.08 Blast** says `tests/test_digital_twin_machine.py:312-410` "uses
  8000/8388/8389/150 as test inputs — inputs, not tagged". Under C.0.2 (written later, V.U8.29) that holds for
  8000/8388/8389 (construction only) but not for 150 and 100 (`:357, :369, :382, :394, :410`): the twin WDT
  counts them down on the real clock and the cases wait for (or feed against) that expiry, so they are tuned
  (A.U8C). Fix the phrase to "8000/8388/8389 construction inputs; the short 100/150 ms timeouts are tuned
  (A.U8C)".
- **`audit/actions/U8.md` Ledger G4/R54 NOT-DONE row and register fix 6**: the per-value classification is
  done in `audit/actions/U8C.md`; the row's result becomes "A.U8C.01-A.U8C.119" and register fix 6's
  "NOT-DONE in A-L, to be split in A-C" line is dropped.
- **G1/R15 / `audit/actions/U8.md` A.U8.05**: the instrument's value list lacks `tests_hardware/harness.py:165`
  (`sock.settimeout(0.05)`, the per-socket read window of `_assert_probe_held()`) and
  `tests_hardware/bench/test_heap_under_connection_ceiling.py:49` (`sock.settimeout(5.0)`, each holder's
  socket timeout). Add both to A.U8.05's Site and Change (IDs as in this file).
- **`audit/actions/U8.md` Appendix C.0.1** states "2,286 hits … const-c 242, … kw 946, … assert 132" for the
  reference script. Applied as its own text says, the count is 2,265 (const-c 253, kw 915, assert 131): the
  reference keys a kw hit by call and keyword text, drops a unary minus inside containers, and counts
  `b"\x41" * 40` as numeric arithmetic (preamble of this file). Replace the numbers, or name the reference
  script's keying as the counted one.
- **`audit/actions/U8.md` Appendix C.0.1** misses seven families of tuned values ("Search gaps" above).
  Either extend C.0.1 by those seven rules or record them as known exclusions; the sites found are listed.

## Open points

No owner question. Cases C.0.2 could not decide mechanically, each classified by a stated reading:

- `tests_hardware/bench/test_bus_concurrency_under_api_load.py:194` — `inject_network_degradation(loss_pct=2, delay_ms=30, jitter_ms=20)`: the netem fault profile. C.0.2 item 3 defines test input as "never waited out in real time", yet netem delay is real; item 4 (tuned) needs "bounds or paces a wait the code under test runs … and pass/fail depends on it", which fits a stimulus only loosely. Classified test input (the stimulus of the case, not a budget); the same reading applies to every netem profile hit.
- `tests_hardware/device_scripts/serving_at_default_gc.py:34` — `_MAX_FAILURE_MAPS = 3`, a cap on printed diagnostics. It bounds no wait, feeds no fake, restates nothing and decides no verdict, so none of C.0.2's four outcomes fits. Classified not tagged ("output cap"), following U8 Appendix B's reading for the twin's log caps ("tagged only where a test's outcome depends on them").
- `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:24-26` — `POLL_WAIT_MS = 2`, `POLL_IDLE_MS = 50`, `BUF_BYTES = 512` equal `devices/dev.toml`'s `[bus.uart*]` values and build the same initiator/responder pair, but unlike `uart_crossover_exchange.py:30-31` no comment says they mirror it, so C.0.2's mechanical mirror test (value equal **and** named) fails on the second half. Classified mirror of `dev.uart_poll_wait_ms`/`dev.uart_poll_idle_ms`/`dev.uart_rxbuf` (the sibling scripts state the intent; "equal only by coincidence" does not fit a copied configuration), with the tag supplying the missing statement.

Readings applied throughout (preamble "How the classification was done"): a timeout the code under test
waits out in full is tuned, not a test input; `tries=`/`conn_tries=` values that select an attempt path are
test inputs; API-domain restatements are not tagged; a fixed sleep in an `l1.` file is tuned; cross-file IDs
only for duplicated tests or instruments. The scale that follows from C.0.2 — 576 new test-tier IDs besides
the 18 existing U8 IDs these files also carry and 28 product IDs they mirror — is OR30.a (1)'s own reach
("every test tier … has an OR30 register entry"), so it is not raised again; almost every new row starts as
"estimated — measurement owed", which makes Part N's test-tier rows the measurement list for the B3 campaign.


