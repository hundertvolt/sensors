# Owner test demands and recovery rungs per level (M.PROC.026, M.PROC.027, A.U35.50, A.U35.51)

Requirement: one row per (fault path, rung R1-R7) from `audit/actions/SUPP_recovery.md` with the test reaching it at L1-L4 or "not reachable at <level>: <reason>", each proven bounded, logged once per event and race-free (M.PROC.026); one checklist cell per owner row × level × test type (M.PROC.027); one four-tier bus-hazard row per bus-facing change of B2 and B3 (A.U35.50); the wear-gate and host-churn table (A.U35.51). L3/L4 cells join `queue_c.md`. Completion: every cell names its test or its reason. A defect any file records goes the OR12.a path (fixed with a regression test seen failing first, or an owner question), never a note alone, and passes A-C as a delta before it is applied (OR106.a). The file is complete when every row is terminal: biting, fixed, or justified with its reason. Opened by A.U35.01 / M.PROC.022 (agent, 2026-10-22); deleted with `audit/` at phase D.

| fault path or owner row | rung or part | L1 | L2 | L3 | L4 | bounded / once / race-free | gap → action |
|---|---|---|---|---|---|---|---|

## Recovery rungs (M.PROC.026)

Built by `audit/b3/conformance_walk.py` at `e1ad71f` from SUPP_recovery.md's rung tables (agent, 2026-10-22): 120 rows, one per
fault path and rung the record names; a cell lists the tests the record itself cites, "open" where it cites none (L1/L2),
"queue_c" where silicon is the only way (236 L3/L4 cells). Bounded, once and race-free are each proven by the review.

| fault path or owner row | rung or part | L1 | L2 | L3 | L4 | bounded / once / race-free | gap → action |
|---|---|---|---|---|---|---|---|
| U10: a sensor/WLAN cycle fails | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a sensor/WLAN cycle fails | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a sensor/WLAN cycle fails | R3 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a sensor/WLAN cycle fails | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a sensor/WLAN cycle fails | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a sensor/WLAN cycle fails | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a sensor/WLAN cycle fails | R7 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a reader's `_init_* | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a reader's `_init_* | R3 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a reader's `_init_* | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a reader's `_init_* | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a reader's `_init_* | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a reader's `_init_* | R7 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: any supervised task ends | R5 | test_system_service.py | test_digital_twin_sensortask_integration.py | system_service_restarts_a_real_dead_task.py | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: any supervised task ends | R6 | test_system_service.py | test_digital_twin_sensortask_integration.py | system_service_restarts_a_real_dead_task.py | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: any supervised task ends | R7 | test_system_service.py | test_digital_twin_sensortask_integration.py | system_service_restarts_a_real_dead_task.py | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a Timer arm fails | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a Timer arm fails | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a Timer arm fails | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a blocking `machine.I2C`/`machine.SPI` transfer never returns | R7 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: the supervisor loop dies or the loop blocks | R7 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: a deferred config flush fails | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U10: FRAM `verify_present | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: I2C transfer raises `OSError | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: I2C transfer raises `OSError | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: I2C transfer raises `OSError | R3 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: I2C transfer raises `OSError | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: I2C transfer raises `OSError | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: I2C bus held at power-up / after an MCU-only reset | R3 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: a slave holds **SCL** low | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: a slave holds **SCL** low | R3 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: a slave holds **SCL** low | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: I2C `scan | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: zero-length probe NAK → `ValueError | R3 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: zero-length probe NAK → `ValueError | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: zero-length probe NAK → `ValueError | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: zero-length probe NAK → `ValueError | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: I2C/SPI construction raises | R7 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: SPI read of 32+ bytes raises `OSError | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: SPI read of 32+ bytes raises `OSError | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: SPI "held bus" | R3 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: SPI controller state | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: UART driver fault paths | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U13: UART driver fault paths | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 periodic read fails | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 periodic read fails | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 periodic read fails | R3 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 periodic read fails | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 periodic read fails | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 periodic read fails | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 periodic read fails | R7 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 data-ready interrupt edge missed | R2 | test_asy_scd30_driver.py | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 goes silent — data-ready never rises again | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 setup fails at a task | R3 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 setup fails at a task | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 setup fails at a task | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SCD30 setup fails at a task | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SGP40 read fails | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SGP40 read fails | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SGP40 read fails | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SGP40 read fails | R7 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SGP40 skips a cycle for missing compensation | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: SGP40 FRAM backup write or restore fails | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: BMP3XX read fails | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: BMP3XX read fails | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: BMP3XX read fails | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: BMP3XX read fails | R7 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: ISL29125 read fails | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: ISL29125 read fails | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: ISL29125 read fails | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: ISL29125 read fails | R7 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: ISL29125 INT not delivering | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: a driver's chip identification fails at setup | R3 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: a driver's chip identification fails at setup | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: a driver's chip identification fails at setup | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: a driver's chip identification fails at setup | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U15: the SGP40 general call reaches the other devices on its bus | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: write-enable latch does not set after WREN | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: latch does not clear after WRDI | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: chip identification fails at `setup | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: chip identification fails at `setup | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: chip identification fails at `setup | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: chip stops answering mid-operation | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: chip stops answering mid-operation | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: chip stops answering mid-operation | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: chip stops answering mid-operation | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: 32+ byte read raises `OSError | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: 32+ byte read raises `OSError | R3 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: 32+ byte read raises `OSError | R4 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: one copy invalid or blank | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: both copies valid but different | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: write verification mismatch | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: torn write by a reset | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: storage paused | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: write-protection readback mismatch | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: `verify_present | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U16: SPI bus clear / controller re-init | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U17: a frame fails | R1 | test_uart_comm_hazard.py | test_digital_twin_uart_link.py | queue_c | test_uart_link_under_api_load.py | open | open: the review confirms each cell or adds its test at the lowest level |
| U17: controller re-init | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U17: construction refused / task ends | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U17: construction refused / task ends | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U17: construction refused / task ends | R7 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U17: participant | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: a WLAN hardware call raises | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: a WLAN hardware call raises | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: a WLAN hardware call raises | R5 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: a WLAN hardware call raises | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: a WLAN hardware call raises | R7 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: STA connect fails | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: CYW43 `isconnected | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: hotspot timer cannot be armed | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: NTP: name does not resolve, no reply, reply rejected, request not sent | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: NTP: name does not resolve, no reply, reply rejected, request not sent | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: NTP: name does not resolve, no reply, reply rejected, request not sent | R6 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: NTP retry/refresh timer cannot be armed | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: a UDP socket cannot be set up, bound or connected | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: a UDP socket cannot be set up, bound or connected | R2 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: a send/receive on a live UDP socket fails | R1 | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: captive DNS loop error | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |
| U18: TCP send stall on a full lwIP arena | no rung named | open | open | queue_c | queue_c | open | open: the review confirms each cell or adds its test at the lowest level |

## Owner test demands (M.PROC.027)

| fault path or owner row | rung or part | L1 | L2 | L3 | L4 | bounded / once / race-free | gap → action |
|---|---|---|---|---|---|---|---|
| OR115 modlwip hammer reach | an `EAGAIN` seen while a zero-timeout poll said writable; A.U21.13's unpatched control run (faults.md) | test_modlwip_eagain.py (lwip_host) | not reachable at L2: the twin's sockets are host sockets, no modlwip | queue_c | queue_c (R4 H39) | open | open: confirm each named test reaches the part |
| OR116/OR123 CRC16 arm | both CRC modes, twin pair in both modes, the jumper pair, the reflash run | test_asy_crc_checks.py, test_asy_uart_comm.py, test_asy_framing_codecs.py | test_digital_twin_uart_link.py, test_digital_twin_uart_comm_hazard.py | test_uart_crossover.py, uart_crossover_exchange.py (R1 H37) | test_uart_link_crc16.py (R4 H38) | open | open: confirm each named test reaches the part |
| OR122.a SystemCmd words | resetconfig, erasefram, reboot, bootloader: function, refusal, error paths | test_asy_system_service.py, test_asy_webserver_service.py, test_asy_config_manager.py | test_digital_twin_bus_hazard_concurrency.py | test_system_commands.py, system_command_*.py (R1-R3 H13/H14) | test_system_commands_over_rest.py, test_reset_reasons.py | open | open: confirm each named test reaches the part |
| OR122.a SystemCmd words | near-miss words refused as "Invalid"; the OR119.a states raced deterministically | open | open | queue_c (H13) | queue_c | open | open: confirm each named test reaches the part |
| OR122.a SystemCmd words | bus and storage hazards; watchdog takeover, healthy and hung step; power loss per step; both GC stages | test_reset_call_site_invariant.py | open | queue_c (H13/H14) | queue_c | open | open: confirm each named test reaches the part |
| OR130 supervisor feeds | two feed sites pinned (L0 test_watchdog_feed_sites.py); the escalation's single feed; twin Run 3's feed_count stop | test_asy_system_service.py | Run 3 (scripts/_digital_twin_scenarios.py) | test_watchdog_starvation.py, reboot_fallback_starves_the_watchdog.py | not reachable at L4 beyond L3: no bench-only path | open | open: confirm each named test reaches the part |

## Bus hazards of B2 and B3 (A.U35.50) and wear and host churn (A.U35.51)

Open: one four-tier row per bus-facing change, and the wear-gate and host-churn table, from the integration head (B2).
