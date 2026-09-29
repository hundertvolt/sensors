# A-L U8C — `@tunable` classification of `tests/` and `tests_hardware/` (HEAD d982cf0)

Finishes the one NOT-DONE item of U8 (Ledger G4/R54 row "per-value classification … of the `tests/` and
`tests_hardware/` candidates"; register fix 6 of `audit/actions/U8.md`). Code at `d982cf0` equals `0ae0d4f`
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

Classified files: 25 of 156 (hits 610 of 2265). IDs used: 104 (new and mirrored). Actions: 18. Verdicts: deferred U25 6, mirror 19, not tagged 168, test input 108, tuned 309.

**NOT-DONE** (not yet classified; to be finished file by file under the same rule): `tests/test_asy_uart_link_driver.py` (7), `tests/test_asy_udp_socket.py` (70), `tests/test_asy_webserver_service.py` (94), `tests/test_asy_wifi_service.py` (31), `tests/test_base_classes.py` (3), `tests/test_bus_hazard_generated.py` (1), `tests/test_bus_hazard_multi_device.py` (7), `tests/test_captive_dns.py` (43), `tests/test_config_manager.py` (29), `tests/test_digital_twin_bus_hazard_concurrency.py` (16), `tests/test_digital_twin_fram.py` (2), `tests/test_digital_twin_http_client.py` (9), `tests/test_digital_twin_isl29125.py` (10), `tests/test_digital_twin_isl29125_autorange.py` (6), `tests/test_digital_twin_launch.py` (10), `tests/test_digital_twin_machine.py` (33), `tests/test_digital_twin_machine_uart.py` (2), `tests/test_digital_twin_network_neopixel.py` (6), `tests/test_digital_twin_poll_prewarm.py` (2), `tests/test_digital_twin_real_website_integration.py` (12), `tests/test_digital_twin_run_generic_integration.py` (3), `tests/test_digital_twin_scd30.py` (4), `tests/test_digital_twin_sensortask_integration.py` (35), `tests/test_digital_twin_uart_link.py` (20), `tests/test_fake_timer_and_network.py` (5), `tests/test_framing_codecs.py` (2), `tests/test_neopixel_wifi_integration.py` (4), `tests/test_notification_fram_integration.py` (2), `tests/test_notification_neopixel_integration.py` (4), `tests/test_notification_scd30_integration.py` (4), `tests/test_notification_scd30_sgp40_integration.py` (3), `tests/test_notification_sgp40_integration.py` (4), `tests/test_ntp_fram_system_integration.py` (18), `tests/test_ntp_wifi_dns_integration.py` (9), `tests/test_setter_microdot_integration.py` (6), `tests/test_system_service.py` (21), `tests/test_ticks_rollover.py` (8), `tests/test_uart_comm_hazard.py` (110), `tests/test_voc_algorithm.py` (3), `tests_hardware/bench/dns_probe.py` (2), `tests_hardware/bench/test_bus_concurrency_under_api_load.py` (77), `tests_hardware/bench/test_end_to_end_timing.py` (52), `tests_hardware/bench/test_heap_under_connection_ceiling.py` (10), `tests_hardware/bench/test_hotspot_role_reversal.py` (47), `tests_hardware/bench/test_memory_stress_bench.py` (6), `tests_hardware/bench/test_network_resilience.py` (195), `tests_hardware/bench/test_rest_endpoints_over_sta.py` (20), `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py` (25), `tests_hardware/bench/test_serving_heap_at_default_gc.py` (11), `tests_hardware/bench/test_uart_link_under_api_load.py` (21), `tests_hardware/bench/test_wifi_networking.py` (13), `tests_hardware/bench_control.py` (10), `tests_hardware/conftest.py` (12), `tests_hardware/device_scripts/allocation_need_per_source.py` (16), `tests_hardware/device_scripts/bmp3xx_plausibility_read.py` (2), `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py` (11), `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py` (4), `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py` (10), `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py` (7), `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py` (7), `tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py` (1), `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py` (18), `tests_hardware/device_scripts/fram_busy_status_lockout.py` (1), `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py` (5), `tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py` (2), `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py` (4), `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py` (5), `tests_hardware/device_scripts/fram_error_log_roundtrip.py` (2), `tests_hardware/device_scripts/fram_manager_roundtrip.py` (1), `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py` (5), `tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py` (2), `tests_hardware/device_scripts/fram_reset_race_during_write_verify_recovery.py` (1), `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py` (6), `tests_hardware/device_scripts/fram_write_protect_roundtrip.py` (1), `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py` (6), `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py` (9), `tests_hardware/device_scripts/heap_under_connection_ceiling.py` (3), `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py` (6), `tests_hardware/device_scripts/isl29125_lighting_scenarios.py` (15), `tests_hardware/device_scripts/isl29125_mechanism_envelope.py` (18), `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py` (4), `tests_hardware/device_scripts/isl29125_plausibility_read.py` (6), `tests_hardware/device_scripts/isl29125_real_irq_edge.py` (8), `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py` (12), `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py` (3), `tests_hardware/device_scripts/reboot_persist_read.py` (2), `tests_hardware/device_scripts/reboot_persist_write.py` (2), `tests_hardware/device_scripts/scd30_plausibility_read.py` (5), `tests_hardware/device_scripts/scd30_real_irq_edge.py` (4), `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py` (7), `tests_hardware/device_scripts/scheduler_saturation_drop.py` (3), `tests_hardware/device_scripts/serving_at_default_gc.py` (8), `tests_hardware/device_scripts/sgp40_fram_backup_restore.py` (4), `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py` (5), `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py` (5), `tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py` (3), `tests_hardware/device_scripts/system_debug_level_restore_after_boot_log_check.py` (2), `tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py` (2), `tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py` (1), `tests_hardware/device_scripts/uart_crossover_exchange.py` (9), `tests_hardware/device_scripts/uart_crossover_recovery.py` (9), `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py` (11), `tests_hardware/device_scripts/uart_idle_poll_rate.py` (11), `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py` (18), `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py` (7), `tests_hardware/device_scripts/watchdog_starvation_reset.py` (1), `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py` (15), `tests_hardware/device_scripts/wifi_service_reconnect_repro.py` (4), `tests_hardware/error_log_helpers.py` (2), `tests_hardware/flash/conftest.py` (1), `tests_hardware/flash/test_bus_concurrency.py` (19), `tests_hardware/flash/test_bus_electrical_timing.py` (5), `tests_hardware/flash/test_fram_storage.py` (14), `tests_hardware/flash/test_memory_stress.py` (2), `tests_hardware/flash/test_reboot_persistence.py` (9), `tests_hardware/flash/test_sensor_accuracy.py` (7), `tests_hardware/flash/test_task_supervisor.py` (1), `tests_hardware/flash/test_toolchain_flash_boot.py` (8), `tests_hardware/flash/test_uart_crossover.py` (6), `tests_hardware/flash/test_watchdog_starvation.py` (29), `tests_hardware/harness.py` (34), `tests_hardware/heap_map.py` (1), `tests_hardware/http_client.py` (1), `tests_hardware/isl29125_conformance.py` (1), `tests_hardware/manual/manual_bus_electrical.py` (2), `tests_hardware/manual/manual_sensor_accuracy.py` (5), `tests_hardware/manual/manual_toolchain.py` (2), `tests_hardware/manual/runner.py` (1), `tests_hardware/ntp_probe.py` (1), `tests_hardware/rogue_udp_responder.py` (2), `tests_hardware/soak_tiers.py` (4)


## Actions

### A.U8C.01 Tag the tuned literals of `_boot_contiguity_probe.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/_boot_contiguity_probe.py` — `l3.heap_layout_after_full_boot_sequence_starter_loop_timeout_ms` :36 (20000); `l3.heap_layout_after_full_boot_sequence_starter_loop_grace_ms` :37 (250); `l3.heap_layout_after_full_boot_sequence_timers_timeout_s` :38 (15); `l3.heap_layout_after_full_boot_sequence_starter_poll_ms` :106 (20)
- **Change**: tag `# @tunable l3.heap_layout_after_full_boot_sequence_starter_loop_timeout_ms = 20000` above `_STARTER_LOOP_TIMEOUT_MS` (:36); tag `# @tunable l3.heap_layout_after_full_boot_sequence_starter_loop_grace_ms = 250` above `_STARTER_LOOP_GRACE_MS` (:37); tag `# @tunable l3.heap_layout_after_full_boot_sequence_timers_timeout_s = 15` above `_TIMERS_TIMEOUT_S` (:38); `_STARTER_POLL_MS = 20` (new, module level) tagged `# @tunable l3.heap_layout_after_full_boot_sequence_starter_poll_ms = 20`; the literal at :106 becomes `_STARTER_POLL_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.02 Tag the tuned literals of `_digital_twin_construction_scenarios.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/_digital_twin_construction_scenarios.py` — `l2.construction_scenarios_run_timeout_s` :131, :160, :203 (10.0); deferred U25: `:147` (1.0); deferred U25: `:193` (1.0)
- **Change**: `_RUN_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l2.construction_scenarios_run_timeout_s = 10.0`; the literal at :131, :160, :203 becomes `_RUN_TIMEOUT_S`; deferred sleeps (:147, :193): no tag now; classified once U25 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, U25
- **Kind**: test

### A.U8C.03 Tag the tuned literals of `_uart_comm_harness.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/_uart_comm_harness.py` — `l1.uart_comm_harness_timeout_ms` :33 (100); `l1.uart_comm_harness_poll_wait_ms` :34 (1); `l1.uart_comm_harness_run_limit_s` :37 (10); `l1.uart_comm_harness_listener_drain_s` :103 (5)
- **Change**: tag `# @tunable l1.uart_comm_harness_timeout_ms = 100` above `TIMEOUT_MS` (:33); tag `# @tunable l1.uart_comm_harness_poll_wait_ms = 1` above `POLL_WAIT_MS` (:34); `_RUN_LIMIT_S = 10` (new, module level) tagged `# @tunable l1.uart_comm_harness_run_limit_s = 10`; the literal at :37 becomes `_RUN_LIMIT_S`; `_LISTENER_DRAIN_S = 5` (new, module level) tagged `# @tunable l1.uart_comm_harness_listener_drain_s = 5`; the literal at :103 becomes `_LISTENER_DRAIN_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged ; shared IDs also sited in `tests/test_asy_uart_comm.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.04 Tag the tuned literals of `_webserver_concurrency_scenarios.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/_webserver_concurrency_scenarios.py` — `web.max_content_length` :105 (2048); `l2.webserver_concurrency_scenarios_flaky_hold_s` :168 (0.05); `l2.webserver_concurrency_scenarios_still_serving_timeout_s` :174 (5.0); `l2.webserver_concurrency_scenarios_request_timeout_s` :181 (2.0); `l2.webserver_concurrency_scenarios_still_serving_poll_s` :187 (0.1); `l2.webserver_concurrency_scenarios_drain_timeout_s` :190 (10.0); `l2.webserver_concurrency_scenarios_drain_poll_s` :201 (0.05); `l2.webserver_concurrency_scenarios_health_check_interval_s` :470 (0.25); `l2.webserver_concurrency_scenarios_health_check_timeout_s` :471 (3.0); `l2.webserver_concurrency_scenarios_reclaim_timeout_s` :543 (20.0); `l2.webserver_concurrency_scenarios_served_elapsed_max_ms` :678 (10000); `l2.webserver_concurrency_scenarios_loop_stall_ms` :740 (200); deferred U25: `:140` (0.5); deferred U25: `:495` (0.3); deferred U25: `:532` (0.2); deferred U25: `:741` (0.5)
- **Change**: mirror tag `# @tunable web.max_content_length = 2048` above :105; listed as a further site of that row; `_FLAKY_HOLD_S = 0.05` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_flaky_hold_s = 0.05`; the literal at :168 becomes `_FLAKY_HOLD_S`; `_STILL_SERVING_TIMEOUT_S = 5.0` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_still_serving_timeout_s = 5.0`; the literal at :174 becomes `_STILL_SERVING_TIMEOUT_S`; `_REQUEST_TIMEOUT_S = 2.0` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_request_timeout_s = 2.0`; the literal at :181 becomes `_REQUEST_TIMEOUT_S`; `_STILL_SERVING_POLL_S = 0.1` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_still_serving_poll_s = 0.1`; the literal at :187 becomes `_STILL_SERVING_POLL_S`; `_DRAIN_TIMEOUT_S = 10.0` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_drain_timeout_s = 10.0`; the literal at :190 becomes `_DRAIN_TIMEOUT_S`; `_DRAIN_POLL_S = 0.05` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_drain_poll_s = 0.05`; the literal at :201 becomes `_DRAIN_POLL_S`; `_HEALTH_CHECK_INTERVAL_S = 0.25` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_health_check_interval_s = 0.25`; the literal at :470 becomes `_HEALTH_CHECK_INTERVAL_S`; `_HEALTH_CHECK_TIMEOUT_S = 3.0` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_health_check_timeout_s = 3.0`; the literal at :471 becomes `_HEALTH_CHECK_TIMEOUT_S`; `_RECLAIM_TIMEOUT_S = 20.0` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_reclaim_timeout_s = 20.0`; the literal at :543 becomes `_RECLAIM_TIMEOUT_S`; `_SERVED_ELAPSED_MAX_MS = 10000` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_served_elapsed_max_ms = 10000`; the literal at :678 becomes `_SERVED_ELAPSED_MAX_MS`; `_LOOP_STALL_MS = 200` (new, module level) tagged `# @tunable l2.webserver_concurrency_scenarios_loop_stall_ms = 200`; the literal at :740 becomes `_LOOP_STALL_MS`; deferred sleeps (:140, :495, :532, :741): no tag now; classified once U25 decides keep-or-poll under G7/R23; if kept, each becomes the named constant with the provisional ID in the table. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.04, U25
- **Kind**: test

### A.U8C.05 Tag the tuned literals of `test_asy_bmp3xx_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_bmp3xx_driver.py` — `l1.asy_bmp3xx_driver_event_wait_s` :1808, :1879 (1)
- **Change**: `_EVENT_WAIT_S = 1` (new, module level) tagged `# @tunable l1.asy_bmp3xx_driver_event_wait_s = 1`; the literal at :1808, :1879 becomes `_EVENT_WAIT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.06 Tag the tuned literals of `test_asy_dns_client.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_dns_client.py` — `udp.conn_tries_default` :57, :548 (1); `l1.asy_dns_client_prompt_return_max_ms` :332 (200); `l1.asy_dns_client_fake_server_wait_ms` :349 (2000); `l1.asy_dns_client_fake_server_poll_ms` :371 (5); `l1.asy_dns_client_reply_timeout_ms` :389, :587 (1000); `l1.asy_dns_client_no_reply_timeout_ms` :402, :509 (100); `l1.asy_dns_client_bad_reply_timeout_ms` :414, :433 (300); `l1.asy_dns_client_fallback_timeout_ms` :456, :487 (200); `l1.asy_dns_client_cname_reply_timeout_ms` :611 (500)
- **Change**: mirror tag `# @tunable udp.conn_tries_default = 1` above :57, :548; listed as a further site of that row; `_PROMPT_RETURN_MAX_MS = 200` (new, module level) tagged `# @tunable l1.asy_dns_client_prompt_return_max_ms = 200`; the literal at :332 becomes `_PROMPT_RETURN_MAX_MS`; `_FAKE_SERVER_WAIT_MS = 2000` (new, module level) tagged `# @tunable l1.asy_dns_client_fake_server_wait_ms = 2000`; the literal at :349 becomes `_FAKE_SERVER_WAIT_MS`; `_FAKE_SERVER_POLL_MS = 5` (new, module level) tagged `# @tunable l1.asy_dns_client_fake_server_poll_ms = 5`; the literal at :371 becomes `_FAKE_SERVER_POLL_MS`; `_REPLY_TIMEOUT_MS = 1000` (new, module level) tagged `# @tunable l1.asy_dns_client_reply_timeout_ms = 1000`; the literal at :389, :587 becomes `_REPLY_TIMEOUT_MS`; `_NO_REPLY_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l1.asy_dns_client_no_reply_timeout_ms = 100`; the literal at :402, :509 becomes `_NO_REPLY_TIMEOUT_MS`; `_BAD_REPLY_TIMEOUT_MS = 300` (new, module level) tagged `# @tunable l1.asy_dns_client_bad_reply_timeout_ms = 300`; the literal at :414, :433 becomes `_BAD_REPLY_TIMEOUT_MS`; `_FALLBACK_TIMEOUT_MS = 200` (new, module level) tagged `# @tunable l1.asy_dns_client_fallback_timeout_ms = 200`; the literal at :456, :487 becomes `_FALLBACK_TIMEOUT_MS`; `_CNAME_REPLY_TIMEOUT_MS = 500` (new, module level) tagged `# @tunable l1.asy_dns_client_cname_reply_timeout_ms = 500`; the literal at :611 becomes `_CNAME_REPLY_TIMEOUT_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
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
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged ; shared IDs also sited in `tests/test_asy_spi_driver.py`, `tests/test_asy_uart_driver.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.10 Tag the tuned literals of `test_asy_isl29125_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_isl29125_driver.py` — `isl29125.gain_ratio_min` :39 (20.0); `isl29125.gain_ratio_max` :40 (34.0); `isl29125.cal_converge_n` :42 (3)
- **Change**: mirror tag `# @tunable isl29125.gain_ratio_min = 20.0` above :39; listed as a further site of that row; mirror tag `# @tunable isl29125.gain_ratio_max = 34.0` above :40; listed as a further site of that row; mirror tag `# @tunable isl29125.cal_converge_n = 3` above :42; listed as a further site of that row. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.13
- **Kind**: test

### A.U8C.11 Tag the tuned literals of `test_asy_neopixel_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_neopixel_driver.py` — `l1.asy_neopixel_driver_overlay_settle_s` :88, :101, :103, :116, :130, :132, :146, :149, :206, :641 (0.05); `l1.asy_neopixel_driver_mid_ramp_s` :167, :361, :434, :437 (0.02); `l1.asy_neopixel_driver_ramp_and_restore_s` :172 (0.2); `l1.asy_neopixel_driver_signal_done_s` :191, :208, :222, :272, :325, :380, :520, :556, :579, :594, :609, :626 (0.15); `l1.asy_neopixel_driver_queued_signals_done_s` :238, :259, :416, :439 (0.3); `l1.asy_neopixel_driver_low_freq_signal_done_s` :290 (1.5); `l1.asy_neopixel_driver_one_s_signal_done_s` :305 (1.1); `l1.asy_neopixel_driver_long_and_short_ramp_done_s` :366 (0.6); `l1.asy_neopixel_driver_long_signal_done_s` :395 (1.6)
- **Change**: `_OVERLAY_SETTLE_S = 0.05` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_overlay_settle_s = 0.05`; the literal at :88, :101, :103, :116, :130, :132, :146, :149, :206, :641 becomes `_OVERLAY_SETTLE_S`; `_MID_RAMP_S = 0.02` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_mid_ramp_s = 0.02`; the literal at :167, :361, :434, :437 becomes `_MID_RAMP_S`; `_RAMP_AND_RESTORE_S = 0.2` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_ramp_and_restore_s = 0.2`; the literal at :172 becomes `_RAMP_AND_RESTORE_S`; `_SIGNAL_DONE_S = 0.15` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_signal_done_s = 0.15`; the literal at :191, :208, :222, :272, :325, :380, :520, :556, :579, :594, :609, :626 becomes `_SIGNAL_DONE_S`; `_QUEUED_SIGNALS_DONE_S = 0.3` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_queued_signals_done_s = 0.3`; the literal at :238, :259, :416, :439 becomes `_QUEUED_SIGNALS_DONE_S`; `_LOW_FREQ_SIGNAL_DONE_S = 1.5` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_low_freq_signal_done_s = 1.5`; the literal at :290 becomes `_LOW_FREQ_SIGNAL_DONE_S`; `_ONE_S_SIGNAL_DONE_S = 1.1` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_one_s_signal_done_s = 1.1`; the literal at :305 becomes `_ONE_S_SIGNAL_DONE_S`; `_LONG_AND_SHORT_RAMP_DONE_S = 0.6` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_long_and_short_ramp_done_s = 0.6`; the literal at :366 becomes `_LONG_AND_SHORT_RAMP_DONE_S`; `_LONG_SIGNAL_DONE_S = 1.6` (new, module level) tagged `# @tunable l1.asy_neopixel_driver_long_signal_done_s = 1.6`; the literal at :395 becomes `_LONG_SIGNAL_DONE_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.12 Tag the tuned literals of `test_asy_notification_service.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_notification_service.py` — `l1.asy_notification_service_cycle_wait_s` :138, :1245, :1296 (0.1); `l1.asy_notification_service_three_flash_cycle_s` :912, :982 (3.5); `l1.asy_notification_service_one_flash_cycle_s` :933, :958 (1.2); `l1.asy_notification_service_task_start_settle_s` :1005, :1147, :1184, :1192 (0.05); `l1.asy_notification_service_one_flash_settle_s` :1008 (1.3); `l1.asy_notification_service_override_tick_s` :1153, :1155, :1186 (1.1); `l1.asy_notification_service_elapsed_stimulus_ms` :1266 (50); `l1.asy_notification_service_two_flash_cycle_s` :1322 (2.5)
- **Change**: `_CYCLE_WAIT_S = 0.1` (new, module level) tagged `# @tunable l1.asy_notification_service_cycle_wait_s = 0.1`; the literal at :138, :1245, :1296 becomes `_CYCLE_WAIT_S`; `_THREE_FLASH_CYCLE_S = 3.5` (new, module level) tagged `# @tunable l1.asy_notification_service_three_flash_cycle_s = 3.5`; the literal at :912, :982 becomes `_THREE_FLASH_CYCLE_S`; `_ONE_FLASH_CYCLE_S = 1.2` (new, module level) tagged `# @tunable l1.asy_notification_service_one_flash_cycle_s = 1.2`; the literal at :933, :958 becomes `_ONE_FLASH_CYCLE_S`; `_TASK_START_SETTLE_S = 0.05` (new, module level) tagged `# @tunable l1.asy_notification_service_task_start_settle_s = 0.05`; the literal at :1005, :1147, :1184, :1192 becomes `_TASK_START_SETTLE_S`; `_ONE_FLASH_SETTLE_S = 1.3` (new, module level) tagged `# @tunable l1.asy_notification_service_one_flash_settle_s = 1.3`; the literal at :1008 becomes `_ONE_FLASH_SETTLE_S`; `_OVERRIDE_TICK_S = 1.1` (new, module level) tagged `# @tunable l1.asy_notification_service_override_tick_s = 1.1`; the literal at :1153, :1155, :1186 becomes `_OVERRIDE_TICK_S`; `_ELAPSED_STIMULUS_MS = 50` (new, module level) tagged `# @tunable l1.asy_notification_service_elapsed_stimulus_ms = 50`; the literal at :1266 becomes `_ELAPSED_STIMULUS_MS`; `_TWO_FLASH_CYCLE_S = 2.5` (new, module level) tagged `# @tunable l1.asy_notification_service_two_flash_cycle_s = 2.5`; the literal at :1322 becomes `_TWO_FLASH_CYCLE_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.13 Tag the tuned literals of `test_asy_ntp_client.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_ntp_client.py` — `dns.timeout_ms` :73 (500); `dns.tries` :74 (1); `ntp.fetch_timeout_ms` :75 (5000); `ntp.retry_s_default` :76 (10); `ntp.retry_max_s_default` :77 (600); `ntp.check_interval_s` :517 (10/1000); `l1.asy_ntp_client_event_wait_s` :527, :607, :1186, :1275, :1326, :1350, :1844 (0.2); `udp.conn_tries_default` :871, :2072 (1); `udp.round_trip_tries_default` :876 (1); `l1.asy_ntp_client_fake_server_poll_ms` :936, :940, :2113, :2118 (10); `ntp.retry_interval_s` :1175 (1000/15); `l1.asy_ntp_client_fired_probe_s` :1296, :2446 (0.05); `l1.asy_ntp_client_serve_wait_s` :2140, :2190, :2228, :2242, :2487, :2519 (5); `l1.asy_ntp_client_state_poll_ms` :2144, :2219, :2237 (20); `l1.asy_ntp_client_no_answer_wait_s` :2167 (1); `l1.asy_ntp_client_reply_process_s` :2191 (0.2); `l1.asy_ntp_client_no_reply_fetch_timeout_ms` :2366 (100); `l1.asy_ntp_client_past_fetch_timeout_ms` :2488 (200)
- **Change**: mirror tag `# @tunable dns.timeout_ms = 500` above :73; listed as a further site of that row; mirror tag `# @tunable dns.tries = 1` above :74; listed as a further site of that row; mirror tag `# @tunable ntp.fetch_timeout_ms = 5000` above :75; listed as a further site of that row; mirror tag `# @tunable ntp.retry_s_default = 10` above :76; listed as a further site of that row; mirror tag `# @tunable ntp.retry_max_s_default = 600` above :77; listed as a further site of that row; mirror tag `# @tunable ntp.check_interval_s = 10` above :517; listed as a further site of that row; `_EVENT_WAIT_S = 0.2` (new, module level) tagged `# @tunable l1.asy_ntp_client_event_wait_s = 0.2`; the literal at :527, :607, :1186, :1275, :1326, :1350, :1844 becomes `_EVENT_WAIT_S`; mirror tag `# @tunable udp.conn_tries_default = 1` above :871, :2072; listed as a further site of that row; mirror tag `# @tunable udp.round_trip_tries_default = 1` above :876; listed as a further site of that row; `_FAKE_SERVER_POLL_MS = 10` (new, module level) tagged `# @tunable l1.asy_ntp_client_fake_server_poll_ms = 10`; the literal at :936, :940, :2113, :2118 becomes `_FAKE_SERVER_POLL_MS`; mirror tag `# @tunable ntp.retry_interval_s = 15` above :1175; listed as a further site of that row; `_FIRED_PROBE_S = 0.05` (new, module level) tagged `# @tunable l1.asy_ntp_client_fired_probe_s = 0.05`; the literal at :1296, :2446 becomes `_FIRED_PROBE_S`; `_SERVE_WAIT_S = 5` (new, module level) tagged `# @tunable l1.asy_ntp_client_serve_wait_s = 5`; the literal at :2140, :2190, :2228, :2242, :2487, :2519 becomes `_SERVE_WAIT_S`; `_STATE_POLL_MS = 20` (new, module level) tagged `# @tunable l1.asy_ntp_client_state_poll_ms = 20`; the literal at :2144, :2219, :2237 becomes `_STATE_POLL_MS`; `_NO_ANSWER_WAIT_S = 1` (new, module level) tagged `# @tunable l1.asy_ntp_client_no_answer_wait_s = 1`; the literal at :2167 becomes `_NO_ANSWER_WAIT_S`; `_REPLY_PROCESS_S = 0.2` (new, module level) tagged `# @tunable l1.asy_ntp_client_reply_process_s = 0.2`; the literal at :2191 becomes `_REPLY_PROCESS_S`; `_NO_REPLY_FETCH_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l1.asy_ntp_client_no_reply_fetch_timeout_ms = 100`; the literal at :2366 becomes `_NO_REPLY_FETCH_TIMEOUT_MS`; `_PAST_FETCH_TIMEOUT_MS = 200` (new, module level) tagged `# @tunable l1.asy_ntp_client_past_fetch_timeout_ms = 200`; the literal at :2488 becomes `_PAST_FETCH_TIMEOUT_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03, A.U8.09, A.U8.11
- **Kind**: test

### A.U8C.14 Tag the tuned literals of `test_asy_scd30_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_scd30_driver.py` — `scd30.start_trigger_period_ms` :652 (500); `l1.asy_scd30_driver_event_wait_s` :660, :661, :689, :745 (1)
- **Change**: mirror tag `# @tunable scd30.start_trigger_period_ms = 500` above :652; listed as a further site of that row; `_EVENT_WAIT_S = 1` (new, module level) tagged `# @tunable l1.asy_scd30_driver_event_wait_s = 1`; the literal at :660, :661, :689, :745 becomes `_EVENT_WAIT_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
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
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged ; shared IDs also sited in `tests/test_asy_i2c_driver.py`, `tests/test_asy_uart_driver.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.17 Tag the tuned literals of `test_asy_uart_comm.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_uart_comm.py` — `l1.uart_comm_harness_poll_wait_ms` :57, :82, :145, :156, :160, :177, :183 (1); `l1.asy_uart_comm_short_reply_timeout_ms` :267, :1645, :1661, :1680, :1725, :1751, :1770, :1836, :1854, :1871, :1897, :1987, :2018 (30); `l1.asy_uart_comm_step_bound_s` :269, :272, :450, :719, :777, :793, :815, :833, :850, :871, :886, :916, :926, :1106, :1158, :1173, :1196, :1284, :1651, :1667, :1686, :1758, :1877, :1903, :1990, :1994, :1997 (10); `l1.asy_uart_comm_loop_survival_wait_ms` :445 (20); `l1.asy_uart_comm_silent_bound_s` :683, :691, :894, :895, :896, :897, :1004, :1977 (15); `l1.asy_uart_comm_listener_run_bound_s` :721, :1015, :1055, :1108, :1161, :1176, :1199, :1286, :1653, :1669, :1689, :1729, :1760, :1780, :1839, :1857, :1880, :1906, :2032, :2151 (25); `l1.asy_uart_comm_short_bound_s` :736, :1033 (5); `l1.asy_uart_comm_past_deadline_bound_s` :756 (2); `l1.asy_uart_comm_flood_step_ms` :787, :809, :845 (1); `l1.asy_uart_comm_run_bound_s` :798, :820, :855, :919, :949, :952, :1037, :1252, :1312, :1321, :1330, :1349, :1373, :1375, :1434, :1465, :1481, :1482, :1486, :1488, :1503, :1536, :1562, :1624, :1637, :1937, :2142, :2155 (20); `l1.asy_uart_comm_listener_park_ms` :915 (10); `l1.asy_uart_comm_inside_lock_ms` :945, :1961 (5); `l1.asy_uart_comm_listener_short_bound_s` :1052, :2148 (8); `l1.asy_uart_comm_async_callback_yield_ms` :1126 (1); `l1.asy_uart_comm_bsec_run_bound_s` :2120 (60)
- **Change**: the literal at :57, :82, :145, :156, :160, :177, :183 becomes `POLL_WAIT_MS` imported from the file that holds `l1.uart_comm_harness_poll_wait_ms`'s tag (no tag here: an import is not a restatement); `_SHORT_REPLY_TIMEOUT_MS = 30` (new, module level) tagged `# @tunable l1.asy_uart_comm_short_reply_timeout_ms = 30`; the literal at :267, :1645, :1661, :1680, :1725, :1751, :1770, :1836, :1854, :1871, :1897, :1987, :2018 becomes `_SHORT_REPLY_TIMEOUT_MS`; `_STEP_BOUND_S = 10` (new, module level) tagged `# @tunable l1.asy_uart_comm_step_bound_s = 10`; the literal at :269, :272, :450, :719, :777, :793, :815, :833, :850, :871, :886, :916, :926, :1106, :1158, :1173, :1196, :1284, :1651, :1667, :1686, :1758, :1877, :1903, :1990, :1994, :1997 becomes `_STEP_BOUND_S`; `_LOOP_SURVIVAL_WAIT_MS = 20` (new, module level) tagged `# @tunable l1.asy_uart_comm_loop_survival_wait_ms = 20`; the literal at :445 becomes `_LOOP_SURVIVAL_WAIT_MS`; `_SILENT_BOUND_S = 15` (new, module level) tagged `# @tunable l1.asy_uart_comm_silent_bound_s = 15`; the literal at :683, :691, :894, :895, :896, :897, :1004, :1977 becomes `_SILENT_BOUND_S`; `_LISTENER_RUN_BOUND_S = 25` (new, module level) tagged `# @tunable l1.asy_uart_comm_listener_run_bound_s = 25`; the literal at :721, :1015, :1055, :1108, :1161, :1176, :1199, :1286, :1653, :1669, :1689, :1729, :1760, :1780, :1839, :1857, :1880, :1906, :2032, :2151 becomes `_LISTENER_RUN_BOUND_S`; `_SHORT_BOUND_S = 5` (new, module level) tagged `# @tunable l1.asy_uart_comm_short_bound_s = 5`; the literal at :736, :1033 becomes `_SHORT_BOUND_S`; `_PAST_DEADLINE_BOUND_S = 2` (new, module level) tagged `# @tunable l1.asy_uart_comm_past_deadline_bound_s = 2`; the literal at :756 becomes `_PAST_DEADLINE_BOUND_S`; `_FLOOD_STEP_MS = 1` (new, module level) tagged `# @tunable l1.asy_uart_comm_flood_step_ms = 1`; the literal at :787, :809, :845 becomes `_FLOOD_STEP_MS`; `_RUN_BOUND_S = 20` (new, module level) tagged `# @tunable l1.asy_uart_comm_run_bound_s = 20`; the literal at :798, :820, :855, :919, :949, :952, :1037, :1252, :1312, :1321, :1330, :1349, :1373, :1375, :1434, :1465, :1481, :1482, :1486, :1488, :1503, :1536, :1562, :1624, :1637, :1937, :2142, :2155 becomes `_RUN_BOUND_S`; `_LISTENER_PARK_MS = 10` (new, module level) tagged `# @tunable l1.asy_uart_comm_listener_park_ms = 10`; the literal at :915 becomes `_LISTENER_PARK_MS`; `_INSIDE_LOCK_MS = 5` (new, module level) tagged `# @tunable l1.asy_uart_comm_inside_lock_ms = 5`; the literal at :945, :1961 becomes `_INSIDE_LOCK_MS`; `_LISTENER_SHORT_BOUND_S = 8` (new, module level) tagged `# @tunable l1.asy_uart_comm_listener_short_bound_s = 8`; the literal at :1052, :2148 becomes `_LISTENER_SHORT_BOUND_S`; `_ASYNC_CALLBACK_YIELD_MS = 1` (new, module level) tagged `# @tunable l1.asy_uart_comm_async_callback_yield_ms = 1`; the literal at :1126 becomes `_ASYNC_CALLBACK_YIELD_MS`; `_BSEC_RUN_BOUND_S = 60` (new, module level) tagged `# @tunable l1.asy_uart_comm_bsec_run_bound_s = 60`; the literal at :2120 becomes `_BSEC_RUN_BOUND_S`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged ; shared IDs also sited in `tests/_uart_comm_harness.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
- **Depends**: A.U8.01, A.U8.02, A.U8.03
- **Kind**: test

### A.U8C.18 Tag the tuned literals of `test_asy_uart_driver.py`
- **Why**: G4/R54 — "every test tier (sleeps, bounds, per-file/suite timeouts, backstops, hardware waits, retries, soak durations, tolerances, allocation and heap-rate budgets, twin durations …) has an OR30 register entry" (OR30.a (1) "(owner, 2026-09-25)"); U8 Appendix C.0.2 applied to C.0.1's hits
- **Site**: `tests/test_asy_uart_driver.py` — `l1.asy_uart_driver_run_bound_s` :27 (5); `l1.asy_uart_driver_data_timeout_ms` :365, :388, :500, :502, :579, :593, :607, :636, :645, :656, :667, :960, :1053, :1079, :1499, :1523, :1661, :1686, :1708, :1799, :1852 (200); `l1.asy_uart_driver_no_data_timeout_ms` :371, :875 (20); `l1.asy_uart_driver_task_inside_ms` :417, :711, :736, :757, :780, :803, :825, :1144 (5); `l1.asy_uart_driver_step_bound_s` :419, :712, :713, :737, :738, :760, :761, :781, :783, :804, :806, :826, :827, :1146 (2); `l1.asy_uart_driver_no_delimiter_timeout_ms` :619 (100); `l1.asy_uart_driver_locked_work_ms` :706, :730 (30); `l1.asy_uart_driver_wedged_hold_ms` :799 (400); `l1.asy_uart_driver_short_cancel_ack_ms` :804 (50); `l1.asy_uart_driver_holder_work_ms` :821 (20); `l1.asy_uart_driver_cancel_ack_ms` :826 (500); `l1.asy_uart_driver_ready_timeout_ms` :846, :1574 (100); `l1.asy_i2c_driver_deadlock_wait_s` :1372 (0.2); `l1.asy_uart_driver_poll_wait_ms` :1591, :1595, :1650, :1677, :1791 (1); `l1.asy_uart_driver_idle_poll_ms` :1591, :1595 (40); `l1.asy_uart_driver_silent_line_timeout_ms` :1809, :1810, :1880 (30)
- **Change**: `_RUN_BOUND_S = 5` (new, module level) tagged `# @tunable l1.asy_uart_driver_run_bound_s = 5`; the literal at :27 becomes `_RUN_BOUND_S`; `_DATA_TIMEOUT_MS = 200` (new, module level) tagged `# @tunable l1.asy_uart_driver_data_timeout_ms = 200`; the literal at :365, :388, :500, :502, :579, :593, :607, :636, :645, :656, :667, :960, :1053, :1079, :1499, :1523, :1661, :1686, :1708, :1799, :1852 becomes `_DATA_TIMEOUT_MS`; `_NO_DATA_TIMEOUT_MS = 20` (new, module level) tagged `# @tunable l1.asy_uart_driver_no_data_timeout_ms = 20`; the literal at :371, :875 becomes `_NO_DATA_TIMEOUT_MS`; `_TASK_INSIDE_MS = 5` (new, module level) tagged `# @tunable l1.asy_uart_driver_task_inside_ms = 5`; the literal at :417, :711, :736, :757, :780, :803, :825, :1144 becomes `_TASK_INSIDE_MS`; `_STEP_BOUND_S = 2` (new, module level) tagged `# @tunable l1.asy_uart_driver_step_bound_s = 2`; the literal at :419, :712, :713, :737, :738, :760, :761, :781, :783, :804, :806, :826, :827, :1146 becomes `_STEP_BOUND_S`; `_NO_DELIMITER_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l1.asy_uart_driver_no_delimiter_timeout_ms = 100`; the literal at :619 becomes `_NO_DELIMITER_TIMEOUT_MS`; `_LOCKED_WORK_MS = 30` (new, module level) tagged `# @tunable l1.asy_uart_driver_locked_work_ms = 30`; the literal at :706, :730 becomes `_LOCKED_WORK_MS`; `_WEDGED_HOLD_MS = 400` (new, module level) tagged `# @tunable l1.asy_uart_driver_wedged_hold_ms = 400`; the literal at :799 becomes `_WEDGED_HOLD_MS`; `_SHORT_CANCEL_ACK_MS = 50` (new, module level) tagged `# @tunable l1.asy_uart_driver_short_cancel_ack_ms = 50`; the literal at :804 becomes `_SHORT_CANCEL_ACK_MS`; `_HOLDER_WORK_MS = 20` (new, module level) tagged `# @tunable l1.asy_uart_driver_holder_work_ms = 20`; the literal at :821 becomes `_HOLDER_WORK_MS`; `_CANCEL_ACK_MS = 500` (new, module level) tagged `# @tunable l1.asy_uart_driver_cancel_ack_ms = 500`; the literal at :826 becomes `_CANCEL_ACK_MS`; `_READY_TIMEOUT_MS = 100` (new, module level) tagged `# @tunable l1.asy_uart_driver_ready_timeout_ms = 100`; the literal at :846, :1574 becomes `_READY_TIMEOUT_MS`; `_DEADLOCK_WAIT_S = 0.2` (new, module level) tagged `# @tunable l1.asy_i2c_driver_deadlock_wait_s = 0.2`; the literal at :1372 becomes `_DEADLOCK_WAIT_S`; `_POLL_WAIT_MS = 1` (new, module level) tagged `# @tunable l1.asy_uart_driver_poll_wait_ms = 1`; the literal at :1591, :1595, :1650, :1677, :1791 becomes `_POLL_WAIT_MS`; `_IDLE_POLL_MS = 40` (new, module level) tagged `# @tunable l1.asy_uart_driver_idle_poll_ms = 40`; the literal at :1591, :1595 becomes `_IDLE_POLL_MS`; `_SILENT_LINE_TIMEOUT_MS = 30` (new, module level) tagged `# @tunable l1.asy_uart_driver_silent_line_timeout_ms = 30`; the literal at :1809, :1810, :1880 becomes `_SILENT_LINE_TIMEOUT_MS`. Rows: every new row: Basis `estimated (agent, <commit from git log -S>) — measurement owed: elapsed of the test at both GC stages on the slowest host that runs it` (N.1 rule), Margin against that measurement, Re-check trigger "the code under test or the host class changes".
- **Blast**: callers — (module-private test constants) · generated — · js — · tests this file only; each literal becomes its constant, behaviour unchanged ; shared IDs also sited in `tests/test_asy_i2c_driver.py`, `tests/test_asy_spi_driver.py` · twin — · docs SPEC Part N rows (A.U8.01) · toml — · uart —
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


