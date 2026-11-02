# R0 baseline (2026-11-02): the "before" column for every report

Per module: `src/*.py` at the pre-audit commit `25caf528` and at the integration head `497b3eda` (the product tree R1
starts from; R0 changes no product file), lines and bytecode compiled by the pinned `mpy-cross -s <bare name>`
(`r0/module_sizes.sh`). Eight modules gained the `asy_` prefix in U10; each row pairs them.

| module | lines before | lines now | bytecode before | bytecode now | change |
|---|---|---|---|---|---|
| `asy_api_response.py` | 105 | 89 | 1,301 B | 1,322 B | +21 B |
| `asy_base_classes.py` | 414 | 850 | 5,561 B | 10,858 B | +5,297 B |
| `asy_bmp3xx_driver.py` | 646 | 725 | 9,938 B | 11,020 B | +1,082 B |
| `asy_captive_dns.py` | 212 | 216 | 2,573 B | 2,810 B | +237 B |
| `asy_config_manager.py` | 485 | 673 | 6,108 B | 8,471 B | +2,363 B |
| `asy_crc_checks.py` | 162 | 186 | 1,672 B | 1,879 B | +207 B |
| `asy_dns_client.py` | 129 | 191 | 1,299 B | 2,110 B | +811 B |
| `asy_fram_driver.py` | 432 | 510 | 4,427 B | 5,554 B | +1,127 B |
| `asy_fram_manager.py` | 740 | 834 | 9,742 B | 11,724 B | +1,982 B |
| `asy_framing_codecs.py` | 149 | 155 | 1,223 B | 1,387 B | +164 B |
| `asy_i2c_driver.py` | 368 | 555 | 2,869 B | 4,846 B | +1,977 B |
| `asy_isl29125_driver.py` | 1,448 | 1,562 | 17,788 B | 19,202 B | +1,414 B |
| `asy_neopixel_driver.py` | 187 | 189 | 2,840 B | 2,565 B | -275 B |
| `asy_notification_service.py` | 376 | 384 | 5,021 B | 4,712 B | -309 B |
| `asy_ntp_client.py` | 483 | 587 | 6,768 B | 8,959 B | +2,191 B |
| `asy_print_log.py` | 296 | 487 | 3,311 B | 6,000 B | +2,689 B |
| `asy_scd30_driver.py` | 630 | 923 | 9,214 B | 12,888 B | +3,674 B |
| `asy_sgp40_driver.py` | 690 | 825 | 8,444 B | 10,514 B | +2,070 B |
| `asy_spi_driver.py` | 213 | 224 | 1,954 B | 2,020 B | +66 B |
| `asy_system_service.py` | 397 | 813 | 5,798 B | 11,412 B | +5,614 B |
| `asy_uart_comm.py` | 1,149 | 1,218 | 13,102 B | 14,858 B | +1,756 B |
| `asy_uart_driver.py` | 455 | 817 | 3,678 B | 7,658 B | +3,980 B |
| `asy_uart_link_driver.py` | 160 | 293 | 1,681 B | 3,697 B | +2,016 B |
| `asy_udp_socket.py` | 208 | 172 | 2,343 B | 2,001 B | -342 B |
| `asy_webserver_service.py` | 807 | 1,120 | 10,927 B | 15,436 B | +4,509 B |
| `asy_wifi_service.py` | 860 | 997 | 12,111 B | 13,753 B | +1,642 B |
| `math_helpers.py` | 216 | 231 | 2,281 B | 2,344 B | +63 B |
| `voc_algorithm.py` | 797 | 852 | 7,652 B | 8,708 B | +1,056 B |
| **total** | **13,214** | **16,678** | **161,626 B** | **208,708 B** | **+47,082 B** |

Per device: the image before is U0's baseline (`audit/artefacts/ENV/baseline.md`, `.uf2` bytes; free = the
1,228,800 B image area minus half the `.uf2`, as each 512 B block carries 256 B); now is `scripts/build_firmware.py`'s
image record at `497b3eda` (built 2026-11-02 19:21-19:28 UTC; marked dirty only by R0's uncommitted doc edits).

| device | `.uf2` before | `.uf2` now | free before | free now |
|---|---|---|---|---|
| arzi | 2,145,280 B | 2,248,192 B | about 156,160 B (152.5 KiB) | 104,892 B (102.4 KiB) |
| dev | 2,237,952 B | 2,371,584 B | about 109,824 B (107.2 KiB) | 43,068 B (42.1 KiB) |
| grkizi | 2,145,280 B | 2,248,192 B | about 156,160 B (152.5 KiB) | 104,884 B (102.4 KiB) |
| klkizi | 2,145,280 B | 2,248,192 B | about 156,160 B (152.5 KiB) | 104,884 B (102.4 KiB) |
| schlafzi | 2,145,280 B | 2,248,192 B | about 156,160 B (152.5 KiB) | 104,876 B (102.4 KiB) |
| wozi | 2,166,272 B | 2,270,720 B | about 145,664 B (142.2 KiB) | 93,448 B (91.3 KiB) |

Test and tool lines (`tests`, `tests_scripts`, `tests_js`, `tests_hardware`, `digital_twin`, `scripts`, `toolchain`,
`.github`): 105,942 at `25caf528`, 232,891 at `497b3eda`, 231,286 in 653 files after R0 (the twin record's copy and
its test removed, 1,605 lines).

CI time per job: from R0's first full CI run (below, once it ends).

