# Intent map per layer (M.PROC.023, A.U35.07)

Requirement: the intent of each layer (function, module, functional integration, system integration), one row per intent item with its cited source, derived mechanically where possible (`raise`/`except`/catalog-code sites, each schema field's bounds, `None`, NaN/±inf for float fields) and mapped to biting tests. An unmapped item gets a test at the lowest layer that can prove it; a test proving no item is tied or removed with a register entry (OR33.a). Completion: every module has a direct row and a real-chain row, and every item maps to a biting test. A defect any file records goes the OR12.a path (fixed with a regression test seen failing first, or an owner question), never a note alone, and passes A-C as a delta before it is applied (OR106.a). The file is complete when every row is terminal: biting, fixed, or justified with its reason. Opened by A.U35.01 / M.PROC.022 (agent, 2026-10-22); deleted with `audit/` at phase D.

| layer | module | intent item | source | biting tests (level) | gap → action |
|---|---|---|---|---|---|

## Items

Built by `audit/b3/levels_walk.py` at `e1ad71f` (agent, 2026-10-22): per module its direct and real-chain rows, then each catalog code
it defines with the tests naming it. Schema bounds, `None` and NaN/±inf rows, and the functional and system integration layers, are open.

| layer | module | intent item | source | biting tests (level) | gap → action |
|---|---|---|---|---|---|
| module | asy_api_response.py | direct row (tests/test_asy_api_response.py) / real-chain row (L2 mention or booted) | asy_api_response.py: 0 raise, 2 except sites | yes / yes |  |
| function | asy_api_response.py | E CALLBACK (14) | src/asy_api_response.py:38 | L1 11: test_asy_api_response.py, test_asy_base_classes.py, test_asy_fram_manager.py … |  |
| module | asy_base_classes.py | direct row (tests/test_asy_base_classes.py) / real-chain row (L2 mention or booted) | asy_base_classes.py: 1 raise, 13 except sites | yes / yes |  |
| function | asy_base_classes.py | E STREAK (1) | src/asy_base_classes.py:78 | L0 1: test_error_catalog.py; L1 7: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py … |  |
| function | asy_base_classes.py | E GIVE_UP (2) | src/asy_base_classes.py:79 | L1 6: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py … |  |
| function | asy_base_classes.py | E CFG_GET_RAISED (3) | src/asy_base_classes.py:80 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_base_classes.py |  |
| function | asy_base_classes.py | E CFG_CALLBACK_RAISED (4) | src/asy_base_classes.py:81 | L0 1: test_fault_or_warning_never_both.py; L1 3: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py |  |
| function | asy_base_classes.py | E CFG_SET_RAISED (5) | src/asy_base_classes.py:82 | - | gap: no test names the code |
| function | asy_base_classes.py | E PUSH_RAISED (6) | src/asy_base_classes.py:83 | - | gap: no test names the code |
| function | asy_base_classes.py | E CFG_SNAPSHOT_RAISED (7) | src/asy_base_classes.py:84 | - | gap: no test names the code |
| function | asy_base_classes.py | E RECOVERY_READ_RAISED (8) | src/asy_base_classes.py:85 | - | gap: no test names the code |
| function | asy_base_classes.py | E RECOVERY_WRITE_RAISED (9) | src/asy_base_classes.py:86 | - | gap: no test names the code |
| function | asy_base_classes.py | E CALLBACK (14) | src/asy_base_classes.py:87 | L1 11: test_asy_api_response.py, test_asy_base_classes.py, test_asy_fram_manager.py … |  |
| function | asy_base_classes.py | E TIMER (17) | src/asy_base_classes.py:88 | L1 8: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py …; L2 3: test_digital_twin_machine.py, test_digital_twin_timer_pool.py, test_digital_twin_wifi_modes.py; L4 1: test_reset_reasons.py |  |
| function | asy_base_classes.py | W CALLBACK_KEYS (1) | src/asy_base_classes.py:89 | L0 1: test_fault_or_warning_never_both.py; L1 2: test_asy_base_classes.py, test_asy_isl29125_driver.py |  |
| function | asy_base_classes.py | W CFG_KEYS (2) | src/asy_base_classes.py:90 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_base_classes.py |  |
| function | asy_base_classes.py | W DEVICE_RECOVERY (14) | src/asy_base_classes.py:91 | L1 7: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py …; L2 2: test_digital_twin_bus_hazard_concurrency.py, test_digital_twin_sensortask_integration.py |  |
| function | asy_base_classes.py | W BUS_RECOVERY (15) | src/asy_base_classes.py:92 | L1 5: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py …; L2 1: test_digital_twin_bus_hazard_concurrency.py |  |
| module | asy_bmp3xx_driver.py | direct row (tests/test_asy_bmp3xx_driver.py) / real-chain row (L2 mention or booted) | asy_bmp3xx_driver.py: 25 raise, 14 except sites | yes / yes |  |
| function | asy_bmp3xx_driver.py | E INIT (10) | src/asy_bmp3xx_driver.py:36 | L0 1: test_error_catalog.py; L1 7: test_asy_bmp3xx_driver.py, test_asy_captive_dns.py, test_asy_fram_manager.py … |  |
| function | asy_bmp3xx_driver.py | E READ (11) | src/asy_bmp3xx_driver.py:37 | L0 2: test_fault_or_warning_never_both.py, test_setup_toolchain_env.py; L1 12: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_fram_driver.py …; L2 1: test_digital_twin_fram.py; L3 1: fram_conformance_probe.py |  |
| function | asy_bmp3xx_driver.py | E CHIP_GET (12) | src/asy_bmp3xx_driver.py:38 | L1 4: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py … |  |
| function | asy_bmp3xx_driver.py | E CHIP_SET (13) | src/asy_bmp3xx_driver.py:39 | L0 1: test_fault_or_warning_never_both.py; L1 6: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py … |  |
| function | asy_bmp3xx_driver.py | E BAD_ARG (21) | src/asy_bmp3xx_driver.py:40 | L1 14: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_captive_dns.py …; L4 2: test_network_resilience.py, test_sensor_config_push_over_real_hardware.py |  |
| function | asy_bmp3xx_driver.py | E CFG_READ (26) | src/asy_bmp3xx_driver.py:41 | L0 1: test_fault_or_warning_never_both.py; L1 6: test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py, test_asy_notification_service.py … |  |
| function | asy_bmp3xx_driver.py | E READ_RANGE (27) | src/asy_bmp3xx_driver.py:42 | L0 1: test_fault_or_warning_never_both.py; L1 2: test_asy_bmp3xx_driver.py, test_asy_scd30_driver.py; L4 1: test_bus_concurrency_under_api_load.py |  |
| function | asy_bmp3xx_driver.py | W DERIVED_DOMAIN (11) | src/asy_bmp3xx_driver.py:43 | L1 1: test_asy_bmp3xx_driver.py |  |
| function | asy_bmp3xx_driver.py | W BMP_CHIP_RESET (71) | src/asy_bmp3xx_driver.py:44 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_bmp3xx_driver.py; L2 1: test_digital_twin_hot_replug.py; L4 1: test_bus_concurrency_under_api_load.py |  |
| module | asy_captive_dns.py | direct row (tests/test_asy_captive_dns.py) / real-chain row (L2 mention or booted) | asy_captive_dns.py: 6 raise, 7 except sites | yes / yes |  |
| function | asy_captive_dns.py | E INIT (10) | src/asy_captive_dns.py:30 | L0 1: test_error_catalog.py; L1 7: test_asy_bmp3xx_driver.py, test_asy_captive_dns.py, test_asy_fram_manager.py … |  |
| function | asy_captive_dns.py | E BAD_ARG (21) | src/asy_captive_dns.py:31 | L1 14: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_captive_dns.py …; L4 2: test_network_resilience.py, test_sensor_config_push_over_real_hardware.py |  |
| function | asy_captive_dns.py | E UNEXPECTED (23) | src/asy_captive_dns.py:32 | L0 1: test_fault_or_warning_never_both.py; L1 9: test_asy_captive_dns.py, test_asy_config_manager.py, test_asy_fram_manager.py …; L2 1: test_digital_twin_fram.py |  |
| function | asy_captive_dns.py | W SOCKET_TEARDOWN (12) | src/asy_captive_dns.py:33 | L0 1: test_fault_or_warning_never_both.py; L1 3: test_asy_captive_dns.py, test_asy_dns_client.py, test_asy_ntp_client.py |  |
| function | asy_captive_dns.py | W DNS_REPLY_DROPPED (41) | src/asy_captive_dns.py:34 | L0 1: test_fault_or_warning_never_both.py; L1 2: test_asy_captive_dns.py, test_asy_udp_socket.py |  |
| function | asy_captive_dns.py | W DNS_RECV_FAILED (42) | src/asy_captive_dns.py:35 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_captive_dns.py |  |
| module | asy_config_manager.py | direct row (tests/test_asy_config_manager.py) / real-chain row (L2 mention or booted) | asy_config_manager.py: 0 raise, 12 except sites | yes / yes |  |
| function | asy_config_manager.py | E ALLOC (20) | src/asy_config_manager.py:55 | L1 4: test_asy_config_manager.py, test_asy_fram_manager.py, test_asy_ntp_client.py … |  |
| function | asy_config_manager.py | E BAD_ARG (21) | src/asy_config_manager.py:56 | L1 14: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_captive_dns.py …; L4 2: test_network_resilience.py, test_sensor_config_push_over_real_hardware.py |  |
| function | asy_config_manager.py | E UNEXPECTED (23) | src/asy_config_manager.py:57 | L0 1: test_fault_or_warning_never_both.py; L1 9: test_asy_captive_dns.py, test_asy_config_manager.py, test_asy_fram_manager.py …; L2 1: test_digital_twin_fram.py |  |
| function | asy_config_manager.py | E CONTRACT (24) | src/asy_config_manager.py:58 | L1 4: test_asy_config_manager.py, test_asy_fram_driver.py, test_asy_notification_service.py … |  |
| function | asy_config_manager.py | E CFG_PATH_IS_DIR (30) | src/asy_config_manager.py:59 | L1 2: test_asy_config_manager.py, test_asy_ntp_client.py |  |
| function | asy_config_manager.py | E CFG_NO_DEFAULTS (31) | src/asy_config_manager.py:60 | L0 1: test_fault_or_warning_never_both.py |  |
| function | asy_config_manager.py | E CFG_BAD_DEFAULT (32) | src/asy_config_manager.py:61 | L0 2: test_config_schemas.py, test_fault_or_warning_never_both.py |  |
| function | asy_config_manager.py | E CFG_FILE_WRITE (33) | src/asy_config_manager.py:62 | L0 1: test_fault_or_warning_never_both.py; L1 5: test_asy_bmp3xx_driver.py, test_asy_config_manager.py, test_asy_isl29125_driver.py … |  |
| function | asy_config_manager.py | E CFG_NOT_VALID (34) | src/asy_config_manager.py:63 | L1 8: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_config_manager.py … |  |
| function | asy_config_manager.py | W STORED_DEFAULT (10) | src/asy_config_manager.py:64 | L0 1: test_fault_or_warning_never_both.py; L1 3: test_asy_ntp_client.py, test_asy_wifi_service.py, test_fram_integration.py |  |
| function | asy_config_manager.py | W CFG_FILE_NOT_OBJECT (20) | src/asy_config_manager.py:65 | L0 1: test_fault_or_warning_never_both.py |  |
| function | asy_config_manager.py | W CFG_FILE_JSON (21) | src/asy_config_manager.py:66 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_config_manager.py |  |
| function | asy_config_manager.py | W CFG_FILE_UNREADABLE (22) | src/asy_config_manager.py:67 | L0 1: test_fault_or_warning_never_both.py; L1 3: test_asy_base_classes.py, test_asy_config_manager.py, test_asy_system_service.py |  |
| function | asy_config_manager.py | W CFG_KEYS_REMOVED (23) | src/asy_config_manager.py:68 | L0 1: test_fault_or_warning_never_both.py |  |
| module | asy_crc_checks.py | direct row (tests/test_asy_crc_checks.py) / real-chain row (L2 mention or booted) | asy_crc_checks.py: 0 raise, 2 except sites | yes / yes |  |
| module | asy_dns_client.py | direct row (tests/test_asy_dns_client.py) / real-chain row (L2 mention or booted) | asy_dns_client.py: 2 raise, 5 except sites | yes / yes |  |
| function | asy_dns_client.py | W SOCKET_TEARDOWN (12) | src/asy_dns_client.py:25 | L0 1: test_fault_or_warning_never_both.py; L1 3: test_asy_captive_dns.py, test_asy_dns_client.py, test_asy_ntp_client.py |  |
| function | asy_dns_client.py | W DNS_REPLY_TRUNCATED (16) | src/asy_dns_client.py:26 | L1 1: test_asy_dns_client.py |  |
| module | asy_fram_driver.py | direct row (tests/test_asy_fram_driver.py) / real-chain row (L2 mention or booted) | asy_fram_driver.py: 4 raise, 4 except sites | yes / yes |  |
| function | asy_fram_driver.py | E NOT_INIT (18) | src/asy_fram_driver.py:103 | L1 5: test_asy_fram_driver.py, test_asy_fram_manager.py, test_asy_uart_comm.py … |  |
| function | asy_fram_driver.py | E LOCK_TIMEOUT (19) | src/asy_fram_driver.py:104 | L1 2: test_asy_fram_driver.py, test_fram_integration.py |  |
| function | asy_fram_driver.py | E BAD_ARG (21) | src/asy_fram_driver.py:105 | L1 14: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_captive_dns.py …; L4 2: test_network_resilience.py, test_sensor_config_push_over_real_hardware.py |  |
| function | asy_fram_driver.py | E CONTRACT (24) | src/asy_fram_driver.py:106 | L1 4: test_asy_config_manager.py, test_asy_fram_driver.py, test_asy_notification_service.py … |  |
| function | asy_fram_driver.py | E FRAM_WP_MISMATCH (45) | src/asy_fram_driver.py:107 | L1 1: test_asy_fram_driver.py |  |
| function | asy_fram_driver.py | E FRAM_BUS_DOWN (52) | src/asy_fram_driver.py:108 | L1 2: test_asy_fram_driver.py, test_asy_fram_manager.py |  |
| function | asy_fram_driver.py | E FRAM_WP_PARTIAL (53) | src/asy_fram_driver.py:109 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_fram_driver.py |  |
| function | asy_fram_driver.py | E FRAM_CHIP_LOST (54) | src/asy_fram_driver.py:110 | L1 3: test_asy_fram_driver.py, test_asy_fram_manager.py, test_fram_integration.py |  |
| function | asy_fram_driver.py | W FRAM_WEL_NOT_SET (26) | src/asy_fram_driver.py:111 | L1 2: test_asy_fram_driver.py, test_asy_fram_manager.py |  |
| function | asy_fram_driver.py | W FRAM_WEL_STUCK (27) | src/asy_fram_driver.py:112 | L1 1: test_asy_fram_driver.py |  |
| function | asy_fram_driver.py | W FRAM_WRITE_PROTECTED (28) | src/asy_fram_driver.py:113 | L1 1: test_asy_fram_driver.py |  |
| function | asy_fram_driver.py | W FRAM_ID_RETRIED (29) | src/asy_fram_driver.py:114 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_fram_driver.py; L2 1: test_digital_twin_generic_wiring.py |  |
| module | asy_fram_manager.py | direct row (tests/test_asy_fram_manager.py) / real-chain row (L2 mention or booted) | asy_fram_manager.py: 0 raise, 9 except sites | yes / yes |  |
| function | asy_fram_manager.py | E INIT (10) | src/asy_fram_manager.py:40 | L0 1: test_error_catalog.py; L1 7: test_asy_bmp3xx_driver.py, test_asy_captive_dns.py, test_asy_fram_manager.py … |  |
| function | asy_fram_manager.py | E CALLBACK (14) | src/asy_fram_manager.py:41 | L1 11: test_asy_api_response.py, test_asy_base_classes.py, test_asy_fram_manager.py … |  |
| function | asy_fram_manager.py | E ALLOC (20) | src/asy_fram_manager.py:42 | L1 4: test_asy_config_manager.py, test_asy_fram_manager.py, test_asy_ntp_client.py … |  |
| function | asy_fram_manager.py | E BAD_ARG (21) | src/asy_fram_manager.py:43 | L1 14: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_captive_dns.py …; L4 2: test_network_resilience.py, test_sensor_config_push_over_real_hardware.py |  |
| function | asy_fram_manager.py | E UNEXPECTED (23) | src/asy_fram_manager.py:44 | L0 1: test_fault_or_warning_never_both.py; L1 9: test_asy_captive_dns.py, test_asy_config_manager.py, test_asy_fram_manager.py …; L2 1: test_digital_twin_fram.py |  |
| function | asy_fram_manager.py | E FRAM_STATUS_BYTE (46) | src/asy_fram_manager.py:45 | L1 1: test_asy_fram_manager.py; L2 2: test_digital_twin_fram.py, test_digital_twin_fram_crash_points.py |  |
| function | asy_fram_manager.py | E FRAM_STATUS_DISAGREE (47) | src/asy_fram_manager.py:46 | L1 2: test_asy_fram_manager.py, test_asy_system_service.py; L2 1: test_digital_twin_fram_crash_points.py |  |
| function | asy_fram_manager.py | E FRAM_CRC_FAILED (48) | src/asy_fram_manager.py:47 | L1 1: test_asy_fram_manager.py |  |
| function | asy_fram_manager.py | E FRAM_DATA_CRC (49) | src/asy_fram_manager.py:48 | L1 1: test_asy_fram_manager.py; L2 1: test_digital_twin_fram_crash_points.py |  |
| function | asy_fram_manager.py | E FRAM_VERIFY (50) | src/asy_fram_manager.py:49 | L1 1: test_asy_fram_manager.py |  |
| function | asy_fram_manager.py | E FRAM_COPIES_DIFFER (51) | src/asy_fram_manager.py:50 | L1 1: test_asy_fram_manager.py; L2 1: test_digital_twin_fram_crash_points.py |  |
| function | asy_fram_manager.py | W FRAM_PAUSED (25) | src/asy_fram_manager.py:51 | L1 2: test_asy_fram_manager.py, test_asy_sgp40_driver.py |  |
| function | asy_fram_manager.py | E FRAM_BLOCK_WRITE (100) | src/asy_fram_manager.py:53 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_fram_manager.py |  |
| function | asy_fram_manager.py | E FRAM_STATUS_READ (101) | src/asy_fram_manager.py:54 | L1 1: test_asy_fram_manager.py |  |
| function | asy_fram_manager.py | E FRAM_STATUS_WRITE (102) | src/asy_fram_manager.py:55 | L1 1: test_asy_fram_manager.py |  |
| function | asy_fram_manager.py | E FRAM_PAYLOAD_WRITE (103) | src/asy_fram_manager.py:56 | L1 1: test_asy_fram_manager.py |  |
| function | asy_fram_manager.py | E FRAM_READ (104) | src/asy_fram_manager.py:57 | L1 1: test_asy_fram_manager.py |  |
| function | asy_fram_manager.py | E FRAM_CLEAR_WRITE (105) | src/asy_fram_manager.py:58 | L1 1: test_asy_fram_manager.py |  |
| function | asy_fram_manager.py | E FRAM_CLEAR (106) | src/asy_fram_manager.py:59 | L1 1: test_asy_fram_manager.py |  |
| function | asy_fram_manager.py | W FRAM_BLOCK_INVALID (63) | src/asy_fram_manager.py:60 | L0 1: test_fault_or_warning_never_both.py; L1 3: test_asy_fram_manager.py, test_asy_sgp40_driver.py, test_asy_system_service.py; L2 1: test_digital_twin_fram_crash_points.py |  |
| module | asy_framing_codecs.py | direct row (tests/test_asy_framing_codecs.py) / real-chain row (L2 mention or booted) | asy_framing_codecs.py: 0 raise, 1 except sites | yes / yes |  |
| module | asy_i2c_driver.py | direct row (tests/test_asy_i2c_driver.py) / real-chain row (L2 mention or booted) | asy_i2c_driver.py: 4 raise, 8 except sites | yes / yes |  |
| module | asy_isl29125_driver.py | direct row (tests/test_asy_isl29125_driver.py) / real-chain row (L2 mention or booted) | asy_isl29125_driver.py: 14 raise, 26 except sites | yes / yes |  |
| function | asy_isl29125_driver.py | E INIT (10) | src/asy_isl29125_driver.py:37 | L0 1: test_error_catalog.py; L1 7: test_asy_bmp3xx_driver.py, test_asy_captive_dns.py, test_asy_fram_manager.py … |  |
| function | asy_isl29125_driver.py | E READ (11) | src/asy_isl29125_driver.py:38 | L0 2: test_fault_or_warning_never_both.py, test_setup_toolchain_env.py; L1 12: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_fram_driver.py …; L2 1: test_digital_twin_fram.py; L3 1: fram_conformance_probe.py |  |
| function | asy_isl29125_driver.py | E CHIP_GET (12) | src/asy_isl29125_driver.py:39 | L1 4: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py … |  |
| function | asy_isl29125_driver.py | E CHIP_SET (13) | src/asy_isl29125_driver.py:40 | L0 1: test_fault_or_warning_never_both.py; L1 6: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py … |  |
| function | asy_isl29125_driver.py | E BAD_ARG (21) | src/asy_isl29125_driver.py:41 | L1 14: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_captive_dns.py …; L4 2: test_network_resilience.py, test_sensor_config_push_over_real_hardware.py |  |
| function | asy_isl29125_driver.py | E CFG_READ (26) | src/asy_isl29125_driver.py:42 | L0 1: test_fault_or_warning_never_both.py; L1 6: test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py, test_asy_notification_service.py … |  |
| function | asy_isl29125_driver.py | E ISL_STATUS_READ (55) | src/asy_isl29125_driver.py:43 | L1 1: test_asy_isl29125_driver.py |  |
| function | asy_isl29125_driver.py | E ISL_BUS_FAULT (56) | src/asy_isl29125_driver.py:44 | L1 1: test_asy_isl29125_driver.py |  |
| function | asy_isl29125_driver.py | W ISL_BROWNOUT (30) | src/asy_isl29125_driver.py:45 | L1 1: test_asy_isl29125_driver.py; L2 1: test_digital_twin_isl29125_autorange.py |  |
| function | asy_isl29125_driver.py | W ISL_DIVERGED (31) | src/asy_isl29125_driver.py:46 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_isl29125_driver.py; L4 1: test_bus_concurrency_under_api_load.py |  |
| function | asy_isl29125_driver.py | W ISL_PERIODIC_ONLY (32) | src/asy_isl29125_driver.py:47 | L1 1: test_asy_isl29125_driver.py; L2 1: test_digital_twin_isl29125_autorange.py; L3 3: isl29125_lighting_scenarios.py, isl29125_mechanism_envelope.py, test_sensor_accuracy.py |  |
| function | asy_isl29125_driver.py | W ISL_CAL_TIMEOUT (75) | src/asy_isl29125_driver.py:48 | L1 1: test_asy_isl29125_driver.py; L2 1: test_digital_twin_isl29125_autorange.py |  |
| module | asy_neopixel_driver.py | direct row (tests/test_asy_neopixel_driver.py) / real-chain row (L2 mention or booted) | asy_neopixel_driver.py: 0 raise, 3 except sites | yes / yes |  |
| module | asy_notification_service.py | direct row (tests/test_asy_notification_service.py) / real-chain row (L2 mention or booted) | asy_notification_service.py: 0 raise, 4 except sites | yes / yes |  |
| function | asy_notification_service.py | E CALLBACK (14) | src/asy_notification_service.py:50 | L1 11: test_asy_api_response.py, test_asy_base_classes.py, test_asy_fram_manager.py … |  |
| function | asy_notification_service.py | E SOURCE (15) | src/asy_notification_service.py:51 | L1 2: test_asy_notification_service.py, test_asy_sgp40_driver.py |  |
| function | asy_notification_service.py | E CFG_READ (26) | src/asy_notification_service.py:52 | L0 1: test_fault_or_warning_never_both.py; L1 6: test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py, test_asy_notification_service.py … |  |
| function | asy_notification_service.py | W CFG_READ (13) | src/asy_notification_service.py:53 | L0 1: test_fault_or_warning_never_both.py; L1 6: test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py, test_asy_notification_service.py … |  |
| function | asy_notification_service.py | W NOTIFY_NAME_COLLISION (44) | src/asy_notification_service.py:54 | L1 1: test_asy_notification_service.py |  |
| function | asy_notification_service.py | W NOTIFY_SCHEMA_SHAPE (45) | src/asy_notification_service.py:55 | L1 1: test_asy_notification_service.py |  |
| function | asy_notification_service.py | W NOTIFY_SIGNAL_DROPPED (67) | src/asy_notification_service.py:56 | L1 2: test_asy_notification_service.py, test_notification_neopixel_integration.py |  |
| module | asy_ntp_client.py | direct row (tests/test_asy_ntp_client.py) / real-chain row (L2 mention or booted) | asy_ntp_client.py: 0 raise, 7 except sites | yes / yes |  |
| function | asy_ntp_client.py | E CALLBACK (14) | src/asy_ntp_client.py:40 | L1 11: test_asy_api_response.py, test_asy_base_classes.py, test_asy_fram_manager.py … |  |
| function | asy_ntp_client.py | E TIMER (17) | src/asy_ntp_client.py:41 | L1 8: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py …; L2 3: test_digital_twin_machine.py, test_digital_twin_timer_pool.py, test_digital_twin_wifi_modes.py; L4 1: test_reset_reasons.py |  |
| function | asy_ntp_client.py | E ALLOC (20) | src/asy_ntp_client.py:42 | L1 4: test_asy_config_manager.py, test_asy_fram_manager.py, test_asy_ntp_client.py … |  |
| function | asy_ntp_client.py | E BAD_ARG (21) | src/asy_ntp_client.py:43 | L1 14: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_captive_dns.py …; L4 2: test_network_resilience.py, test_sensor_config_push_over_real_hardware.py |  |
| function | asy_ntp_client.py | E CFG_READ (26) | src/asy_ntp_client.py:44 | L0 1: test_fault_or_warning_never_both.py; L1 6: test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py, test_asy_notification_service.py … |  |
| function | asy_ntp_client.py | E NTP_DNS (67) | src/asy_ntp_client.py:45 | L1 2: test_asy_ntp_client.py, test_ntp_wifi_dns_integration.py; L4 1: test_network_resilience.py |  |
| function | asy_ntp_client.py | E NTP_IMPLAUSIBLE (68) | src/asy_ntp_client.py:46 | L1 1: test_asy_ntp_client.py; L2 1: test_digital_twin_ntp.py; L4 1: test_network_resilience.py |  |
| function | asy_ntp_client.py | E NTP_MALFORMED (69) | src/asy_ntp_client.py:47 | L1 1: test_asy_ntp_client.py; L2 1: test_digital_twin_ntp.py; L4 1: test_network_resilience.py |  |
| function | asy_ntp_client.py | E NTP_RETRIES (70) | src/asy_ntp_client.py:48 | L1 1: test_asy_ntp_client.py |  |
| function | asy_ntp_client.py | E NTP_NO_REPLY (71) | src/asy_ntp_client.py:49 | L0 2: test_digital_twin_ci_suite_errcount.py, test_fault_or_warning_never_both.py; L1 2: test_asy_ntp_client.py, test_ntp_wifi_dns_integration.py; L2 1: test_digital_twin_ntp.py; L4 3: test_bus_concurrency_under_api_load.py, test_network_resilience.py, test_wifi_networking.py |  |
| function | asy_ntp_client.py | E NTP_NOT_SENT (72) | src/asy_ntp_client.py:50 | L0 1: test_digital_twin_ci_suite_errcount.py; L1 1: test_asy_ntp_client.py |  |
| function | asy_ntp_client.py | E NTP_DNS_NOT_SENT (73) | src/asy_ntp_client.py:51 | L1 2: test_asy_ntp_client.py, test_ntp_wifi_dns_integration.py |  |
| function | asy_ntp_client.py | E NTP_DNS_NXDOMAIN (74) | src/asy_ntp_client.py:52 | L1 1: test_asy_ntp_client.py; L4 1: test_network_resilience.py |  |
| function | asy_ntp_client.py | W STORED_DEFAULT (10) | src/asy_ntp_client.py:53 | L0 1: test_fault_or_warning_never_both.py; L1 3: test_asy_ntp_client.py, test_asy_wifi_service.py, test_fram_integration.py |  |
| function | asy_ntp_client.py | W SOCKET_TEARDOWN (12) | src/asy_ntp_client.py:54 | L0 1: test_fault_or_warning_never_both.py; L1 3: test_asy_captive_dns.py, test_asy_dns_client.py, test_asy_ntp_client.py |  |
| function | asy_ntp_client.py | W NTP_UNSYNC_REPLY (40) | src/asy_ntp_client.py:55 | L1 1: test_asy_ntp_client.py; L2 1: test_digital_twin_ntp.py |  |
| module | asy_print_log.py | direct row (tests/test_asy_print_log.py) / real-chain row (L2 mention or booted) | asy_print_log.py: 0 raise, 6 except sites | yes / yes |  |
| function | asy_print_log.py | E LOG_RAM_ONLY (28) | src/asy_print_log.py:71 | L1 6: test_asy_base_classes.py, test_asy_print_log.py, test_asy_sgp40_driver.py … |  |
| module | asy_scd30_driver.py | direct row (tests/test_asy_scd30_driver.py) / real-chain row (L2 mention or booted) | asy_scd30_driver.py: 16 raise, 20 except sites | yes / yes |  |
| function | asy_scd30_driver.py | E INIT (10) | src/asy_scd30_driver.py:82 | L0 1: test_error_catalog.py; L1 7: test_asy_bmp3xx_driver.py, test_asy_captive_dns.py, test_asy_fram_manager.py … |  |
| function | asy_scd30_driver.py | E READ (11) | src/asy_scd30_driver.py:83 | L0 2: test_fault_or_warning_never_both.py, test_setup_toolchain_env.py; L1 12: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_fram_driver.py …; L2 1: test_digital_twin_fram.py; L3 1: fram_conformance_probe.py |  |
| function | asy_scd30_driver.py | E CHIP_GET (12) | src/asy_scd30_driver.py:84 | L1 4: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py … |  |
| function | asy_scd30_driver.py | E CHIP_SET (13) | src/asy_scd30_driver.py:85 | L0 1: test_fault_or_warning_never_both.py; L1 6: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py … |  |
| function | asy_scd30_driver.py | E BAD_ARG (21) | src/asy_scd30_driver.py:86 | L1 14: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_captive_dns.py …; L4 2: test_network_resilience.py, test_sensor_config_push_over_real_hardware.py |  |
| function | asy_scd30_driver.py | E READ_RANGE (27) | src/asy_scd30_driver.py:87 | L0 1: test_fault_or_warning_never_both.py; L1 2: test_asy_bmp3xx_driver.py, test_asy_scd30_driver.py; L4 1: test_bus_concurrency_under_api_load.py |  |
| function | asy_scd30_driver.py | W SCD_NOT_READY (73) | src/asy_scd30_driver.py:88 | L1 1: test_asy_scd30_driver.py; L2 1: test_digital_twin_scd30.py |  |
| module | asy_sgp40_driver.py | direct row (tests/test_asy_sgp40_driver.py) / real-chain row (L2 mention or booted) | asy_sgp40_driver.py: 10 raise, 9 except sites | yes / yes |  |
| function | asy_sgp40_driver.py | E INIT (10) | src/asy_sgp40_driver.py:49 | L0 1: test_error_catalog.py; L1 7: test_asy_bmp3xx_driver.py, test_asy_captive_dns.py, test_asy_fram_manager.py … |  |
| function | asy_sgp40_driver.py | E READ (11) | src/asy_sgp40_driver.py:50 | L0 2: test_fault_or_warning_never_both.py, test_setup_toolchain_env.py; L1 12: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_fram_driver.py …; L2 1: test_digital_twin_fram.py; L3 1: fram_conformance_probe.py |  |
| function | asy_sgp40_driver.py | E CHIP_SET (13) | src/asy_sgp40_driver.py:51 | L0 1: test_fault_or_warning_never_both.py; L1 6: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py … |  |
| function | asy_sgp40_driver.py | E CALLBACK (14) | src/asy_sgp40_driver.py:52 | L1 11: test_asy_api_response.py, test_asy_base_classes.py, test_asy_fram_manager.py … |  |
| function | asy_sgp40_driver.py | E SOURCE (15) | src/asy_sgp40_driver.py:53 | L1 2: test_asy_notification_service.py, test_asy_sgp40_driver.py |  |
| function | asy_sgp40_driver.py | E CFG_READ (26) | src/asy_sgp40_driver.py:54 | L0 1: test_fault_or_warning_never_both.py; L1 6: test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py, test_asy_notification_service.py … |  |
| function | asy_sgp40_driver.py | E SGP_ALGO_STATE (58) | src/asy_sgp40_driver.py:55 | L1 1: test_asy_sgp40_driver.py |  |
| function | asy_sgp40_driver.py | E SGP_BACKUP_CLEAR (59) | src/asy_sgp40_driver.py:56 | L1 1: test_asy_sgp40_driver.py |  |
| function | asy_sgp40_driver.py | E SGP_BACKUP_WRITE (110) | src/asy_sgp40_driver.py:57 | L1 1: test_asy_sgp40_driver.py |  |
| function | asy_sgp40_driver.py | W SGP_RESTORED_NO_TS (33) | src/asy_sgp40_driver.py:58 | L1 1: test_asy_sgp40_driver.py |  |
| function | asy_sgp40_driver.py | W SGP_BACKUP_AGE (34) | src/asy_sgp40_driver.py:59 | L1 1: test_asy_sgp40_driver.py; L2 1: test_digital_twin_clock_jump.py |  |
| function | asy_sgp40_driver.py | W SGP_WRITTEN_NO_TS (35) | src/asy_sgp40_driver.py:60 | L1 1: test_asy_sgp40_driver.py |  |
| function | asy_sgp40_driver.py | W SGP_NO_BACKUP (65) | src/asy_sgp40_driver.py:61 | L1 1: test_asy_sgp40_driver.py |  |
| module | asy_spi_driver.py | direct row (tests/test_asy_spi_driver.py) / real-chain row (L2 mention or booted) | asy_spi_driver.py: 5 raise, 4 except sites | yes / yes |  |
| module | asy_system_service.py | direct row (tests/test_asy_system_service.py) / real-chain row (L2 mention or booted) | asy_system_service.py: 0 raise, 18 except sites | yes / yes |  |
| function | asy_system_service.py | E CALLBACK (14) | src/asy_system_service.py:45 | L1 11: test_asy_api_response.py, test_asy_base_classes.py, test_asy_fram_manager.py … |  |
| function | asy_system_service.py | E TIMER (17) | src/asy_system_service.py:46 | L1 8: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py …; L2 3: test_digital_twin_machine.py, test_digital_twin_timer_pool.py, test_digital_twin_wifi_modes.py; L4 1: test_reset_reasons.py |  |
| function | asy_system_service.py | E UNEXPECTED (23) | src/asy_system_service.py:47 | L0 1: test_fault_or_warning_never_both.py; L1 9: test_asy_captive_dns.py, test_asy_config_manager.py, test_asy_fram_manager.py …; L2 1: test_digital_twin_fram.py |  |
| function | asy_system_service.py | E STACK_EXHAUSTED (25) | src/asy_system_service.py:48 | L1 1: test_asy_system_service.py; L4 1: test_reset_reasons.py |  |
| function | asy_system_service.py | E TASK_STARTER_RAISED (40) | src/asy_system_service.py:49 | L1 1: test_asy_system_service.py |  |
| function | asy_system_service.py | E TASK_BUDGET_REBOOT (41) | src/asy_system_service.py:50 | L0 1: test_bench_no_task_ended_completeness.py; L1 2: test_asy_system_service.py, test_asy_webserver_service.py; L4 1: test_reset_reasons.py |  |
| function | asy_system_service.py | E TASK_RAISED (42) | src/asy_system_service.py:51 | L0 2: test_bench_no_task_ended_completeness.py, test_exception_handler_contract.py; L1 2: test_asy_neopixel_driver.py, test_asy_system_service.py |  |
| function | asy_system_service.py | E TASK_CANCELLED (43) | src/asy_system_service.py:52 | L1 1: test_asy_system_service.py |  |
| function | asy_system_service.py | E TASK_RETURNED (44) | src/asy_system_service.py:53 | L0 1: test_bench_no_task_ended_completeness.py; L1 2: test_asy_system_service.py, test_ntp_fram_system_integration.py; L3 1: test_task_supervisor.py |  |
| function | asy_system_service.py | E SUPERVISOR_RAISED (115) | src/asy_system_service.py:54 | L1 1: test_asy_system_service.py |  |
| function | asy_system_service.py | W CONFIG_LOST (69) | src/asy_system_service.py:55 | L1 1: test_asy_system_service.py; L3 1: test_heap_layout.py |  |
| module | asy_uart_comm.py | direct row (tests/test_asy_uart_comm.py) / real-chain row (L2 mention or booted) | asy_uart_comm.py: 0 raise, 6 except sites | yes / yes |  |
| function | asy_uart_comm.py | E CALLBACK (14) | src/asy_uart_comm.py:120 | L1 11: test_asy_api_response.py, test_asy_base_classes.py, test_asy_fram_manager.py … |  |
| function | asy_uart_comm.py | E NOT_INIT (18) | src/asy_uart_comm.py:121 | L1 5: test_asy_fram_driver.py, test_asy_fram_manager.py, test_asy_uart_comm.py … |  |
| function | asy_uart_comm.py | E ALLOC (20) | src/asy_uart_comm.py:122 | L1 4: test_asy_config_manager.py, test_asy_fram_manager.py, test_asy_ntp_client.py … |  |
| function | asy_uart_comm.py | E BAD_ARG (21) | src/asy_uart_comm.py:123 | L1 14: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_captive_dns.py …; L4 2: test_network_resilience.py, test_sensor_config_push_over_real_hardware.py |  |
| function | asy_uart_comm.py | E TIMEOUT (22) | src/asy_uart_comm.py:124 | L1 3: test_asy_uart_comm.py, test_asy_wifi_service.py, test_uart_comm_hazard.py; L2 1: test_digital_twin_uart_link.py |  |
| function | asy_uart_comm.py | E UNEXPECTED (23) | src/asy_uart_comm.py:125 | L0 1: test_fault_or_warning_never_both.py; L1 9: test_asy_captive_dns.py, test_asy_config_manager.py, test_asy_fram_manager.py …; L2 1: test_digital_twin_fram.py |  |
| function | asy_uart_comm.py | E UART_PAYLOAD_SIZE (75) | src/asy_uart_comm.py:126 | L1 3: test_asy_uart_comm.py, test_asy_uart_link_driver.py, test_readiness_gates.py |  |
| function | asy_uart_comm.py | E UART_TIMEOUT_PARAM (76) | src/asy_uart_comm.py:127 | L0 1: test_buildgen_validate.py; L1 1: test_asy_uart_comm.py |  |
| function | asy_uart_comm.py | E UART_NO_BUS (77) | src/asy_uart_comm.py:128 | L1 2: test_asy_uart_comm.py, test_readiness_gates.py |  |
| function | asy_uart_comm.py | E UART_RXBUF (78) | src/asy_uart_comm.py:129 | L0 1: test_buildgen_validate.py; L1 2: test_asy_uart_comm.py, test_uart_comm_hazard.py |  |
| function | asy_uart_comm.py | E UART_ROLE_REFUSED (79) | src/asy_uart_comm.py:130 | L1 1: test_asy_uart_comm.py |  |
| function | asy_uart_comm.py | E UART_FRAME_INVALID (80) | src/asy_uart_comm.py:131 | L1 2: test_asy_uart_comm.py, test_uart_comm_hazard.py; L3 1: test_uart_crossover.py |  |
| function | asy_uart_comm.py | E UART_NO_ACK (81) | src/asy_uart_comm.py:132 | L0 1: test_manual_runner_summary.py; L1 2: test_asy_uart_comm.py, test_uart_comm_hazard.py; L2 1: test_digital_twin_uart_link.py; L3 1: test_uart_crossover.py |  |
| function | asy_uart_comm.py | E UART_WRITE_FAILED (82) | src/asy_uart_comm.py:133 | L1 1: test_asy_uart_comm.py |  |
| function | asy_uart_comm.py | E UART_PAYLOAD_TOO_LARGE (83) | src/asy_uart_comm.py:134 | L1 2: test_asy_uart_comm.py, test_uart_comm_hazard.py |  |
| function | asy_uart_comm.py | E UART_SIZE_MISMATCH (84) | src/asy_uart_comm.py:135 | L1 2: test_asy_uart_comm.py, test_uart_comm_hazard.py |  |
| function | asy_uart_comm.py | E UART_REENTRANT (85) | src/asy_uart_comm.py:136 | L1 1: test_uart_comm_hazard.py; L2 1: test_digital_twin_uart_comm_hazard.py; L3 1: test_uart_crossover.py |  |
| function | asy_uart_comm.py | E UART_WRONG_KIND (86) | src/asy_uart_comm.py:137 | - | gap: no test names the code |
| function | asy_uart_comm.py | E UART_GET_ID_MISMATCH (87) | src/asy_uart_comm.py:138 | L1 1: test_asy_uart_comm.py |  |
| function | asy_uart_comm.py | E UART_PEER_INITIATED (88) | src/asy_uart_comm.py:139 | L1 1: test_uart_comm_hazard.py; L2 1: test_digital_twin_uart_comm_hazard.py; L3 1: test_uart_crossover.py |  |
| function | asy_uart_comm.py | E UART_LINK_UNINTELLIGIBLE (89) | src/asy_uart_comm.py:140 | L0 1: test_fault_or_warning_never_both.py; L1 2: test_asy_uart_comm.py, test_uart_comm_hazard.py; L2 1: test_digital_twin_uart_link.py |  |
| function | asy_uart_comm.py | E UART_STREAM_SHORT (90) | src/asy_uart_comm.py:141 | L1 1: test_asy_uart_comm.py |  |
| function | asy_uart_comm.py | E UART_POLL_RATE (91) | src/asy_uart_comm.py:142 | L0 1: test_buildgen_validate.py; L1 1: test_asy_uart_comm.py |  |
| function | asy_uart_comm.py | E UART_CODEC_SIZE (92) | src/asy_uart_comm.py:143 | L1 1: test_asy_uart_comm.py |  |
| function | asy_uart_comm.py | E UART_TRANSFER_CAP (93) | src/asy_uart_comm.py:144 | L1 2: test_asy_uart_comm.py, test_asy_uart_driver.py; L3 1: test_uart_crossover.py |  |
| function | asy_uart_comm.py | W UART_DRAIN_BOUND (54) | src/asy_uart_comm.py:146 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_uart_comm.py |  |
| function | asy_uart_comm.py | W UART_CANCEL_UNACKED (55) | src/asy_uart_comm.py:147 | L1 2: test_asy_uart_comm.py, test_asy_uart_driver.py |  |
| function | asy_uart_comm.py | W UART_CMD_DECLINED (56) | src/asy_uart_comm.py:148 | L1 1: test_asy_uart_comm.py |  |
| function | asy_uart_comm.py | W UART_RX_OVERRUN (57) | src/asy_uart_comm.py:149 | L1 1: test_asy_uart_comm.py |  |
| module | asy_uart_driver.py | direct row (tests/test_asy_uart_driver.py) / real-chain row (L2 mention or booted) | asy_uart_driver.py: 1 raise, 14 except sites | yes / yes |  |
| function | asy_uart_driver.py | E UART_TRANSFER_CAP (93) | src/asy_uart_driver.py:51 | L1 2: test_asy_uart_comm.py, test_asy_uart_driver.py; L3 1: test_uart_crossover.py |  |
| module | asy_uart_link_driver.py | direct row (tests/test_asy_uart_link_driver.py) / real-chain row (L2 mention or booted) | asy_uart_link_driver.py: 0 raise, 1 except sites | yes / yes |  |
| module | asy_udp_socket.py | direct row (tests/test_asy_udp_socket.py) / real-chain row (L2 mention or booted) | asy_udp_socket.py: 2 raise, 9 except sites | yes / yes |  |
| module | asy_webserver_service.py | direct row (tests/test_asy_webserver_service.py) / real-chain row (L2 mention or booted) | asy_webserver_service.py: 9 raise, 25 except sites | yes / yes |  |
| function | asy_webserver_service.py | E CALLBACK (14) | src/asy_webserver_service.py:102 | L1 11: test_asy_api_response.py, test_asy_base_classes.py, test_asy_fram_manager.py … |  |
| function | asy_webserver_service.py | E UNEXPECTED (23) | src/asy_webserver_service.py:103 | L0 1: test_fault_or_warning_never_both.py; L1 9: test_asy_captive_dns.py, test_asy_config_manager.py, test_asy_fram_manager.py …; L2 1: test_digital_twin_fram.py |  |
| function | asy_webserver_service.py | W HTTP_PEER_RESET (48) | src/asy_webserver_service.py:104 | L0 1: test_fault_or_warning_never_both.py; L1 2: test_asy_webserver_connections.py, test_asy_webserver_service.py; L4 1: test_network_resilience.py |  |
| function | asy_webserver_service.py | W HTTP_CALL_TIMEOUT (49) | src/asy_webserver_service.py:105 | L0 1: test_request_timeout_ceiling.py; L1 2: test_asy_webserver_connections.py, test_asy_webserver_service.py; L4 1: test_network_resilience.py |  |
| function | asy_webserver_service.py | W HTTP_REQUEST_CAP (50) | src/asy_webserver_service.py:106 | L1 2: test_asy_webserver_connections.py, test_asy_webserver_service.py; L4 1: test_network_resilience.py |  |
| function | asy_webserver_service.py | W HTTP_SOCKET_ERROR (51) | src/asy_webserver_service.py:107 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_webserver_connections.py; L4 1: test_network_resilience.py |  |
| function | asy_webserver_service.py | W HTTP_CLOSE_RAISED (52) | src/asy_webserver_service.py:108 | L1 1: test_asy_webserver_service.py |  |
| function | asy_webserver_service.py | W HTTP_WAIT_CLOSED (53) | src/asy_webserver_service.py:109 | L1 1: test_asy_webserver_service.py |  |
| function | asy_webserver_service.py | W HTTP_REFUSED (60) | src/asy_webserver_service.py:110 | L1 2: test_asy_webserver_connections.py, test_asy_webserver_service.py; L4 1: test_network_resilience.py |  |
| function | asy_webserver_service.py | W HTTP_BAD_HEAD (61) | src/asy_webserver_service.py:111 | L0 1: test_fault_or_warning_never_both.py; L1 1: test_asy_webserver_connections.py; L4 2: test_hotspot_role_reversal.py, test_network_resilience.py |  |
| function | asy_webserver_service.py | W HTTP_START_FAILED (62) | src/asy_webserver_service.py:112 | L1 1: test_asy_webserver_connections.py |  |
| module | asy_wifi_service.py | direct row (tests/test_asy_wifi_service.py) / real-chain row (L2 mention or booted) | asy_wifi_service.py: 0 raise, 18 except sites | yes / yes |  |
| function | asy_wifi_service.py | E TIMER (17) | src/asy_wifi_service.py:41 | L1 8: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py …; L2 3: test_digital_twin_machine.py, test_digital_twin_timer_pool.py, test_digital_twin_wifi_modes.py; L4 1: test_reset_reasons.py |  |
| function | asy_wifi_service.py | E BAD_ARG (21) | src/asy_wifi_service.py:42 | L1 14: test_asy_base_classes.py, test_asy_bmp3xx_driver.py, test_asy_captive_dns.py …; L4 2: test_network_resilience.py, test_sensor_config_push_over_real_hardware.py |  |
| function | asy_wifi_service.py | E TIMEOUT (22) | src/asy_wifi_service.py:43 | L1 3: test_asy_uart_comm.py, test_asy_wifi_service.py, test_uart_comm_hazard.py; L2 1: test_digital_twin_uart_link.py |  |
| function | asy_wifi_service.py | E UNEXPECTED (23) | src/asy_wifi_service.py:44 | L0 1: test_fault_or_warning_never_both.py; L1 9: test_asy_captive_dns.py, test_asy_config_manager.py, test_asy_fram_manager.py …; L2 1: test_digital_twin_fram.py |  |
| function | asy_wifi_service.py | E WLAN_MODE_SWITCH (60) | src/asy_wifi_service.py:45 | L1 1: test_asy_wifi_service.py |  |
| function | asy_wifi_service.py | E WLAN_AP_START (61) | src/asy_wifi_service.py:46 | L1 1: test_asy_wifi_service.py |  |
| function | asy_wifi_service.py | E WLAN_STA_START (62) | src/asy_wifi_service.py:47 | L1 1: test_asy_wifi_service.py |  |
| function | asy_wifi_service.py | E WLAN_STA_POLL (63) | src/asy_wifi_service.py:48 | L1 1: test_asy_wifi_service.py |  |
| function | asy_wifi_service.py | E WLAN_STA_DISCONNECT (64) | src/asy_wifi_service.py:49 | L1 1: test_asy_wifi_service.py |  |
| function | asy_wifi_service.py | E WLAN_GIVE_UP (66) | src/asy_wifi_service.py:50 | L1 1: test_asy_wifi_service.py; L4 1: test_hotspot_role_reversal.py |  |
| function | asy_wifi_service.py | W STORED_DEFAULT (10) | src/asy_wifi_service.py:51 | L0 1: test_fault_or_warning_never_both.py; L1 3: test_asy_ntp_client.py, test_asy_wifi_service.py, test_fram_integration.py |  |
| function | asy_wifi_service.py | W CFG_READ (13) | src/asy_wifi_service.py:52 | L0 1: test_fault_or_warning_never_both.py; L1 6: test_asy_bmp3xx_driver.py, test_asy_isl29125_driver.py, test_asy_notification_service.py … |  |
| function | asy_wifi_service.py | W WLAN_AUTH_FAILED (36) | src/asy_wifi_service.py:53 | L1 1: test_asy_wifi_service.py; L4 1: test_network_resilience.py |  |
| function | asy_wifi_service.py | W WLAN_NO_AP (37) | src/asy_wifi_service.py:54 | L1 1: test_asy_wifi_service.py; L4 1: test_network_resilience.py |  |
| function | asy_wifi_service.py | W WLAN_CONNECT_FAILED (38) | src/asy_wifi_service.py:55 | L1 1: test_asy_wifi_service.py |  |
| function | asy_wifi_service.py | W WLAN_STATUS_UNKNOWN (39) | src/asy_wifi_service.py:56 | L1 1: test_asy_wifi_service.py |  |
| function | asy_wifi_service.py | W WLAN_STATIONS_UNKNOWN (77) | src/asy_wifi_service.py:57 | L1 1: test_asy_wifi_service.py; L2 1: test_digital_twin_wifi_modes.py |  |
| function | asy_wifi_service.py | W WLAN_STATUS_UNREADABLE (78) | src/asy_wifi_service.py:58 | L1 1: test_asy_wifi_service.py; L2 1: test_digital_twin_sensortask_integration.py |  |
| function | asy_wifi_service.py | W WLAN_TO_HOTSPOT (79) | src/asy_wifi_service.py:59 | L1 1: test_asy_wifi_service.py; L2 1: test_digital_twin_wifi_modes.py; L4 1: test_hotspot_role_reversal.py |  |
| function | asy_wifi_service.py | W WLAN_SILENT (80) | src/asy_wifi_service.py:60 | L1 1: test_asy_wifi_service.py; L2 1: test_digital_twin_wifi_modes.py; L4 1: test_hotspot_role_reversal.py |  |
| function | asy_wifi_service.py | W WLAN_NO_VERDICT (81) | src/asy_wifi_service.py:61 | L1 1: test_asy_wifi_service.py |  |
| module | math_helpers.py | direct row (tests/test_math_helpers.py) / real-chain row (L2 mention or booted) | math_helpers.py: 0 raise, 5 except sites | yes / yes |  |
| module | voc_algorithm.py | direct row (tests/test_voc_algorithm.py) / real-chain row (L2 mention or booted) | voc_algorithm.py: 0 raise, 2 except sites | yes / yes |  |
