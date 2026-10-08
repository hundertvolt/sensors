# Measurements, 2026-10-08 on `51a5bd2d`

The `result_note` values from `bench_step/run_record.json`, against `mqtt_poc/BENCH_HANDOVER.md` section 8.
Each figure is from one run on the dev bench (one board, one bench Pi4); the bench session records, it does
not retune. The Part N rows named move only in a later commit that cites this directory.

| Test (`test_mqtt_broker_faults.py`) | Measured | Part N rows |
|---|---|---|
| `test_the_client_connects_and_announces_itself_online` | connected within 1.3 s of the first poll; `MQTTState` `connected` | `mqtt.connect_timeout_ms`, `mqtt.response_timeout_ms` |
| `test_every_sensor_publishes_strict_json_on_its_own_topic` | largest measurement payload 245 B of the 384 B slot | `mqtt.out_payload_max` |
| `test_a_killed_broker_is_reconnected_after_its_restart` | reconnected 4.2 s after the restart (outage 5 s) | `mqtt.backoff_min_ms`, `l4.mqtt_connect_wait_s` |
| `test_a_stalled_broker_is_detected_by_the_pingresp_deadline` | stall detected in 21.0 s; reconnected 8.7 s after the resume | `mqtt.ping_interval_ms`, `l4.mqtt_detect_bound_s` |
| `test_a_silent_path_loss_is_detected_and_recovered` | path loss detected in 21.5 s (`no pingresp`); reconnected 13.8 s after the restore | `mqtt.ping_interval_ms`, `l4.mqtt_detect_bound_s` |
| `test_a_reset_path_ends_the_connection_and_attempts_stay_bounded` | the reset path ended the connection in 6.7 s; reconnected 11.4 s after the restore | (no row named in the handover) |
| `test_a_duplicate_client_id_is_bounded_by_the_backoff` | 0 retakes in 20 s against 1 by the duplicate; reconnected 39.8 s after it left | `mqtt.stable_after_ms`, `mqtt.short_session_warn`, `l4.mqtt_takeover_max_connects` |
| `test_an_inbound_flood_leaves_rest_serving_and_the_session_up` | 3001 of 3001 messages taken; `GET /status` under the flood max 1.93 s, median 1.84 s | `l4.mqtt_flood_messages`, `l4.mqtt_rest_budget_s` |
| `test_an_inbound_qos1_burst_is_acknowledged_in_full` | 500 QoS 1 messages acknowledged in 7.1 s | `mqtt.qos1_retry_ms`, `l4.mqtt_detect_wait_s` |
| `test_the_broker_is_found_by_the_bench_hosts_local_name` | `raspberrypi.local` resolved to 192.168.85.75; connected within 1.6 s | none: the `.local` path itself |
| `test_an_ap_outage_pauses_the_client_and_it_returns_with_the_link` | **recovery pass**: reconnected 15.4 s after a recovery hard reset; 0 failed attempts logged | `l4.mqtt_ap_reconnect_timeout_s`, `l4.mqtt_ap_max_failed_attempts` |
| `test_a_reboot_reconnects_from_the_stored_settings` | connected 15.8 s after the reset; the broker published the will on the takeover | `l4.mqtt_reboot_wait_s` |
| `test_the_broker_faults_run_clean_at_micropythons_default_gc` | timeline connected → reconnected after kill → stall detected → reconnected after stall → connected after floods → reconnected after takeover → done; free heap minimum 2,192 B over 42 samples | `l4.mqtt_at_default_gc_window_s`, `l4.mqtt_default_gc_script_timeout_s` |

## Beside them

- **The AP outage needed the bench's documented recovery** (a station kick, then one hard reset, the CYW43
  reconnect behaviour); it is counted as a pass with recovery, not a clean pass.
- **Free heap minimum 2,192 B at `gc.threshold(-1)`** under the broker faults with the client resident, with
  zero memory markers (the test passed). It is the smallest free-heap figure this run produced.
- **`test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status`**: 19 answered, 21 refused at
  the connection ceiling (5 on this image), 0 answered wrongly.
- **The heap tests** (`test_heap_at_peak_while_a_full_ceiling_is_held`, `test_report_the_boards_own_connection_wall`,
  `test_every_source_and_route_fits_a_small_free_run`, `test_serving_sweep_at_the_reactive_default`,
  `test_real_hardware_survives_max_speed_hammer_load_without_memoryerror_or_reboot`) all passed, but recorded
  no `result_note`: their figures go to captured stdout, which pytest discards on a pass, so this run kept
  none of them. Rerunning them with `-s` (or giving them `result_note`s) is what would keep the first
  figures with the client resident.
- **The flash step's full-build heap**: 113,280 B allocated after `build_system()` against the 100,000 B
  tripwire; the client measured at 11,360 B of it (README, attempt 3).
