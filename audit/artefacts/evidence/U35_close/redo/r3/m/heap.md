# R3 lane M: the per-file live-heap probe over tests/ (agent, 2026-11-04)

Run `r3m_heap` (rc 0, 367 s): every `tests/test_*.py` (94 files; a PER_DEVICE file for `dev`) once under build-standard
at the reactive default (-1), heap 16 MB, three at a time, through a scratch wrapper that appends one last after-each
hook to microtest: `gc.collect()`, then `gc.mem_alloc()` printed, after the file's own resets and hooks (R1's B36
method). All 94 files passed every test. Live heap after each test, in bytes, sorted by last minus first.

**Result: no file grows per test.** Every series is a step and a plateau: the steps are a test that first loads a
device module or the twin (about 1 MB in `test_digital_twin_fram`, `test_digital_twin_run_generic_integration`,
`test_neopixel_wifi_integration`, `test_digital_twin_bus_hazard_concurrency`) or a helper's first use, and the
plateau holds to the file's last test. The largest second-half slopes are small and not monotone:
`test_digital_twin_clock_jump` (6 tests, 1,683-1,841 kB, up and down), `test_digital_twin_bus_hazard_concurrency`
(1,787-1,911 kB after its step), `test_digital_twin_sensortask_integration` (1,385-1,432 kB over 18 tests). B36's case
stays fixed: `test_asy_system_service` holds 683-685 kB over its last 174 tests (it grew 423 kB to 4.88 MB before
`d922323b`). Gaps: none.

| file | tests | first B | peak B | last B | last-first B | 2nd-half slope B/test | rises | summary |
|---|---|---|---|---|---|---|---|---|
| test_digital_twin_bus_hazard_concurrency | 25 | 644,576 | 1,956,960 | 1,830,848 | 1,186,272 | 4,437 | 11 | 25/25 passed, 0 failed, 0 skipped |
| test_digital_twin_run_generic_integration | 50 | 553,152 | 1,690,688 | 1,690,688 | 1,137,536 | 1 | 13 | 50/50 passed, 0 failed, 0 skipped |
| test_digital_twin_fram | 59 | 491,456 | 1,569,696 | 1,569,664 | 1,078,208 | -0 | 18 | 59/59 passed, 0 failed, 0 skipped |
| test_neopixel_wifi_integration | 8 | 739,680 | 1,698,272 | 1,698,240 | 958,560 | -10 | 3 | 8/8 passed, 0 failed, 0 skipped |
| test_digital_twin_uart_link | 22 | 1,377,152 | 1,822,912 | 1,812,128 | 434,976 | -66 | 9 | 22/22 passed, 0 failed, 0 skipped |
| test_digital_twin_construction | 4 | 1,253,472 | 1,660,128 | 1,660,128 | 406,656 | 0 | 1 | 4/4 passed, 0 failed, 0 skipped |
| test_digital_twin_hot_replug | 2 | 1,391,296 | 1,538,496 | 1,538,496 | 147,200 | 0 | 1 | 2/2 passed, 0 failed, 0 skipped |
| test_asy_webserver_service | 223 | 679,936 | 846,592 | 810,688 | 130,752 | -4 | 103 | 223/223 passed, 0 failed, 0 skipped |
| test_digital_twin_clock_jump | 6 | 1,723,520 | 1,841,440 | 1,841,440 | 117,920 | 10,304 | 3 | 6/6 passed, 0 failed, 0 skipped |
| test_asy_system_service | 186 | 625,280 | 702,368 | 699,808 | 74,528 | -0 | 29 | 186/186 passed, 0 failed, 0 skipped |
| test_shared_helpers | 43 | 272,224 | 341,120 | 341,120 | 68,896 | 2,791 | 18 | 43/43 passed, 0 failed, 0 skipped |
| test_voc_algorithm | 43 | 333,408 | 390,208 | 390,208 | 56,800 | 3,567 | 9 | 43/43 passed, 0 failed, 0 skipped |
| test_digital_twin_sensortask_integration | 18 | 1,419,424 | 1,467,104 | 1,467,104 | 47,680 | 3,306 | 10 | 17/18 passed, 0 failed, 1 skipped |
| test_sensortask | 101 | 1,466,432 | 1,728,832 | 1,498,848 | 32,416 | 891 | 43 | 101/101 passed, 0 failed, 0 skipped |
| test_readiness_gates | 14 | 407,616 | 439,104 | 439,104 | 31,488 | 3,571 | 2 | 14/14 passed, 0 failed, 0 skipped |
| test_asy_uart_link_driver | 51 | 379,008 | 396,704 | 396,672 | 17,664 | 0 | 8 | 51/51 passed, 0 failed, 0 skipped |
| test_asy_print_log | 101 | 314,464 | 328,384 | 328,352 | 13,888 | -0 | 24 | 101/101 passed, 0 failed, 0 skipped |
| test_asy_api_response | 25 | 112,640 | 126,112 | 126,112 | 13,472 | 0 | 2 | 25/25 passed, 0 failed, 0 skipped |
| test_bus_hazard_multi_device | 22 | 438,144 | 451,520 | 451,520 | 13,376 | 0 | 4 | 22/22 passed, 0 failed, 0 skipped |
| test_asy_fram_driver | 94 | 282,560 | 295,904 | 295,904 | 13,344 | 1 | 6 | 94/94 passed, 0 failed, 0 skipped |
| test_asy_uart_comm | 199 | 533,760 | 547,104 | 547,072 | 13,312 | 28 | 17 | 199/199 passed, 0 failed, 0 skipped |
| test_asy_base_classes | 191 | 498,080 | 511,360 | 511,328 | 13,248 | 0 | 26 | 191/191 passed, 0 failed, 0 skipped |
| test_digital_twin_held_i2c_line | 3 | 1,353,696 | 1,366,752 | 1,366,752 | 13,056 | 0 | 1 | 3/3 passed, 0 failed, 0 skipped |
| test_asy_uart_driver | 165 | 431,776 | 446,144 | 444,672 | 12,896 | 0 | 21 | 165/165 passed, 0 failed, 0 skipped |
| test_digital_twin_ntp | 17 | 1,823,680 | 1,856,480 | 1,836,448 | 12,768 | -1,466 | 9 | 17/17 passed, 0 failed, 0 skipped |
| test_digital_twin_generic_wiring | 15 | 245,888 | 258,240 | 258,240 | 12,352 | 1,758 | 5 | 15/15 passed, 0 failed, 0 skipped |
| test_asy_config_manager | 244 | 339,776 | 351,872 | 351,872 | 12,096 | 0 | 3 | 244/244 passed, 0 failed, 0 skipped |
| test_asy_ntp_client | 183 | 484,128 | 496,096 | 496,096 | 11,968 | -0 | 6 | 183/183 passed, 0 failed, 0 skipped |
| test_asy_isl29125_driver | 237 | 533,856 | 545,760 | 545,760 | 11,904 | 0 | 19 | 237/237 passed, 0 failed, 0 skipped |
| test_digital_twin_isl29125_autorange | 21 | 295,168 | 306,912 | 306,912 | 11,744 | 0 | 2 | 21/21 passed, 0 failed, 0 skipped |
| test_ntp_fram_system_integration | 12 | 447,200 | 458,944 | 458,944 | 11,744 | 2,979 | 3 | 12/12 passed, 0 failed, 0 skipped |
| test_digital_twin_scd30 | 55 | 309,824 | 321,600 | 321,536 | 11,712 | -0 | 7 | 55/55 passed, 0 failed, 0 skipped |
| test_ntp_wifi_dns_integration | 13 | 282,144 | 293,728 | 293,728 | 11,584 | 0 | 2 | 13/13 passed, 0 failed, 0 skipped |
| test_asy_neopixel_driver | 46 | 259,104 | 270,688 | 270,656 | 11,552 | 435 | 7 | 46/46 passed, 0 failed, 0 skipped |
| test_notification_scd30_sgp40_integration | 2 | 256,800 | 268,224 | 268,224 | 11,424 | 0 | 1 | 2/2 passed, 0 failed, 0 skipped |
| test_asy_notification_service | 62 | 210,944 | 222,208 | 222,208 | 11,264 | 0 | 1 | 62/62 passed, 0 failed, 0 skipped |
| test_fram_integration | 11 | 211,008 | 222,304 | 222,272 | 11,264 | -1 | 3 | 11/11 passed, 0 failed, 0 skipped |
| test_setter_microdot_integration | 34 | 483,392 | 495,840 | 494,336 | 10,944 | -5 | 13 | 34/34 passed, 0 failed, 0 skipped |
| test_digital_twin_http_client | 38 | 87,584 | 95,008 | 95,008 | 7,424 | 0 | 2 | 38/38 passed, 0 failed, 0 skipped |
| test_digital_twin_network_neopixel | 41 | 84,256 | 90,848 | 90,848 | 6,592 | 0 | 2 | 41/41 passed, 0 failed, 0 skipped |
| test_digital_twin_machine_uart | 26 | 255,584 | 261,632 | 261,632 | 6,048 | 592 | 6 | 26/26 passed, 0 failed, 0 skipped |
| test_asy_webserver_connections | 25 | 370,816 | 401,600 | 375,744 | 4,928 | 191 | 10 | 25/25 passed, 0 failed, 0 skipped |
| test_asy_i2c_driver | 113 | 409,568 | 411,648 | 411,616 | 2,048 | 3 | 16 | 113/113 passed, 0 failed, 0 skipped |
| test_ticks_rollover | 24 | 319,072 | 321,120 | 321,088 | 2,016 | -1 | 4 | 24/24 passed, 0 failed, 0 skipped |
| test_async_harness | 18 | 49,792 | 51,744 | 51,744 | 1,952 | 123 | 2 | 18/18 passed, 0 failed, 0 skipped |
| test_bus_hazard_generated | 39 | 326,368 | 328,320 | 328,320 | 1,952 | -1 | 6 | 39/39 passed, 0 failed, 0 skipped |
| test_write_counters | 9 | 124,096 | 126,016 | 125,984 | 1,888 | 374 | 2 | 9/9 passed, 0 failed, 0 skipped |
| test_asy_fram_manager | 148 | 463,488 | 465,344 | 465,344 | 1,856 | 22 | 15 | 148/148 passed, 0 failed, 0 skipped |
| test_driven_time | 26 | 140,032 | 141,696 | 141,696 | 1,664 | 60 | 2 | 26/26 passed, 0 failed, 0 skipped |
| test_digital_twin_launch | 26 | 269,696 | 271,104 | 271,040 | 1,344 | -1 | 7 | 26/26 passed, 0 failed, 0 skipped |
| test_asy_sgp40_driver | 157 | 495,424 | 496,608 | 496,608 | 1,184 | 15 | 24 | 157/157 passed, 0 failed, 0 skipped |
| test_asy_wifi_service | 270 | 628,896 | 630,016 | 630,016 | 1,120 | 1 | 6 | 270/270 passed, 0 failed, 0 skipped |
| test_digital_twin_machine | 116 | 352,608 | 353,600 | 353,600 | 992 | 1 | 29 | 116/116 passed, 0 failed, 0 skipped |
| test_asy_scd30_driver | 130 | 391,712 | 392,672 | 392,672 | 960 | 0 | 12 | 130/130 passed, 0 failed, 0 skipped |
| test_asy_bmp3xx_driver | 129 | 427,328 | 428,224 | 428,224 | 896 | 12 | 21 | 129/129 passed, 0 failed, 0 skipped |
| test_asy_dns_client | 41 | 180,704 | 181,568 | 181,568 | 864 | 1 | 2 | 41/41 passed, 0 failed, 0 skipped |
| test_asy_udp_socket | 62 | 256,512 | 257,280 | 257,280 | 768 | 0 | 2 | 62/62 passed, 0 failed, 0 skipped |
| test_asy_spi_driver | 64 | 205,824 | 206,560 | 206,560 | 736 | 0 | 3 | 64/64 passed, 0 failed, 0 skipped |
| test_tmp_scratch | 14 | 39,520 | 40,736 | 39,904 | 384 | -153 | 11 | 14/14 passed, 0 failed, 0 skipped |
| test_generated_boot_entry | 5 | 91,008 | 91,328 | 91,328 | 320 | 160 | 1 | 5/5 passed, 0 failed, 0 skipped |
| test_machine_uart_link | 18 | 102,912 | 103,136 | 103,136 | 224 | 25 | 5 | 18/18 passed, 0 failed, 0 skipped |
| test_digital_twin_poll_prewarm | 6 | 26,144 | 26,336 | 26,336 | 192 | 96 | 1 | 6/6 passed, 0 failed, 0 skipped |
| test_notification_neopixel_integration | 6 | 210,944 | 211,104 | 211,104 | 160 | 0 | 1 | 6/6 passed, 0 failed, 0 skipped |
| test_notification_scd30_integration | 4 | 238,720 | 238,880 | 238,880 | 160 | 0 | 2 | 4/4 passed, 0 failed, 0 skipped |
| test_reset_call_site_invariant | 3 | 41,408 | 41,536 | 41,536 | 128 | 0 | 1 | 3/3 passed, 0 failed, 0 skipped |
| test_notification_sgp40_integration | 3 | 227,680 | 227,776 | 227,776 | 96 | 0 | 1 | 3/3 passed, 0 failed, 0 skipped |
| test_digital_twin_unix_port_unretrieved_report | 10 | 39,456 | 39,520 | 39,520 | 64 | 0 | 1 | 10/10 passed, 0 failed, 0 skipped |
| test_digital_twin_fram_crash_points | 3 | 275,552 | 275,584 | 275,584 | 32 | 0 | 1 | 3/3 passed, 0 failed, 0 skipped |
| test_digital_twin_loop_end | 6 | 1,337,216 | 1,337,248 | 1,337,248 | 32 | 240 | 2 | 6/6 passed, 0 failed, 0 skipped |
| test_digital_twin_uart_field_sweep | 10 | 255,616 | 255,648 | 255,648 | 32 | 0 | 1 | 10/10 passed, 0 failed, 0 skipped |
| test_fakes | 54 | 152,096 | 152,128 | 152,128 | 32 | 1 | 14 | 54/54 passed, 0 failed, 0 skipped |
| test_notification_fram_integration | 3 | 215,328 | 215,360 | 215,360 | 32 | 0 | 1 | 3/3 passed, 0 failed, 0 skipped |
| test_uart_comm_hazard | 123 | 377,152 | 377,184 | 377,184 | 32 | 0 | 2 | 123/123 passed, 0 failed, 0 skipped |
| test_asy_captive_dns | 67 | 210,688 | 210,688 | 210,688 | 0 | 0 | 0 | 67/67 passed, 0 failed, 0 skipped |
| test_asy_crc_checks | 76 | 89,408 | 89,408 | 89,408 | 0 | 0 | 0 | 76/76 passed, 0 failed, 0 skipped |
| test_asy_fram_allocation_budget | 2 | 183,008 | 183,008 | 183,008 | 0 | 0 | 0 | 2/2 passed, 0 failed, 0 skipped |
| test_asy_fram_wire_trace | 9 | 209,184 | 209,184 | 209,184 | 0 | 0 | 0 | 9/9 passed, 0 failed, 0 skipped |
| test_asy_framing_codecs | 21 | 70,528 | 70,528 | 70,528 | 0 | 0 | 0 | 21/21 passed, 0 failed, 0 skipped |
| test_digital_twin_bmp3xx | 25 | 60,320 | 60,320 | 60,320 | 0 | 0 | 0 | 25/25 passed, 0 failed, 0 skipped |
| test_digital_twin_driven_clock | 10 | 60,448 | 60,448 | 60,448 | 0 | 0 | 0 | 10/10 passed, 0 failed, 0 skipped |
| test_digital_twin_isl29125 | 47 | 79,648 | 79,648 | 79,648 | 0 | 0 | 0 | 47/47 passed, 0 failed, 0 skipped |
| test_digital_twin_rp2_constants | 8 | 133,888 | 133,888 | 133,888 | 0 | 0 | 0 | 8/8 passed, 0 failed, 0 skipped |
| test_digital_twin_setup_resets | 1 | 1,275,712 | 1,275,712 | 1,275,712 | 0 | 0 | 0 | 1/1 passed, 0 failed, 0 skipped |
| test_digital_twin_uart_comm_hazard | 10 | 275,648 | 275,648 | 275,648 | 0 | 0 | 0 | 10/10 passed, 0 failed, 0 skipped |
| test_digital_twin_unix_port_idle_poll | 5 | 23,296 | 23,296 | 23,296 | 0 | 0 | 0 | 5/5 passed, 0 failed, 0 skipped |
| test_digital_twin_wifi_modes | 1 | 1,443,584 | 1,443,584 | 1,443,584 | 0 | 0 | 0 | 1/1 passed, 0 failed, 0 skipped |
| test_math_helpers | 91 | 81,920 | 81,920 | 81,920 | 0 | 0 | 0 | 91/91 passed, 0 failed, 0 skipped |
| test_microtest_hooks | 7 | 29,280 | 29,280 | 29,280 | 0 | 0 | 0 | 7/7 passed, 0 failed, 0 skipped |
| test_strict_json | 10 | 33,568 | 33,568 | 33,568 | 0 | 0 | 0 | 10/10 passed, 0 failed, 0 skipped |
| test_untraced | 3 | 21,216 | 21,216 | 21,216 | 0 | 0 | 0 | 3/3 passed, 0 failed, 0 skipped |
| test_website_build_integration | 7 | 206,784 | 206,784 | 206,784 | 0 | -16 | 2 | 7/7 passed, 0 failed, 0 skipped |
| test_digital_twin_sgp40 | 25 | 266,368 | 266,400 | 266,336 | -32 | -1 | 3 | 25/25 passed, 0 failed, 0 skipped |
| test_uart_comm_cancel_sweep | 10 | 219,904 | 219,904 | 219,872 | -32 | -6 | 0 | 10/10 passed, 0 failed, 0 skipped |
| test_digital_twin_timer_pool | 3 | 1,333,056 | 1,333,056 | 1,322,912 | -10,144 | 0 | 1 | 3/3 passed, 0 failed, 0 skipped |
