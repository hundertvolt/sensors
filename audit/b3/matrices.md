# Assembly and actor × resource matrices (A.U35.08, A.U35.09)

Requirement: the assembly dimensions (device, driver set, bus, mode) and the actor × resource matrix, each gap tested at the lowest level that proves it (A.U35.08), and the recombination row (A.U35.09 (1)). Completion: every cell names its test or its reason. A defect any file records goes the OR12.a path (fixed with a regression test seen failing first, or an owner question), never a note alone, and passes A-C as a delta before it is applied (OR106.a). The file is complete when every row is terminal: biting, fixed, or justified with its reason. Opened by A.U35.01 / M.PROC.022 (agent, 2026-10-22); deleted with `audit/` at phase D.

| actor | resource | interaction | test (level) | gap → action |
|---|---|---|---|---|

## Device-pick sites (CMr1, CMr1b, CMr1c; agent, 2026-10-27)

Class: W = the part is wired differently across devices, so the site runs once per distinct wiring of what it reads (`distinct_wirings()`, the key computed at run time from the generated plan and module); I = the subject is identical on every device, so one device serves. Measured from the generated plans and modules (lines at 56c3eb8e). Device differences: NeoPixel pin 18 on dev, 15 elsewhere; FRAM 256 KiB CS 5 on dev, 8 KiB CS 1 SPI 2/3/4 on arzi and wozi, CS 17 SPI 18/19/16 on grkizi, klkizi, schlafzi; dev puts scd30 (irq 11), sgp40 and isl29125 on i2c1 14/15, wozi puts sgp40 and bmp3xx on i2c1 18/19; only dev has UART. grkizi, klkizi and schlafzi differ only in hostname, which no driver statement names.

| site | class | measured reason | device set |
|---|---|---|---|
| tests/test_digital_twin_sensortask_integration.py:317 `_driver_specific()` | W | each scenario's drivers' statements and buses differ as above | per scenario's drivers, e.g. scd30: arzi, dev; sgp40: arzi, dev, wozi |
| tests/test_digital_twin_sensortask_integration.py:953 `_first_device_wiring("neopixel")` | I | asserts only asy_udp_socket's poll_idle_ms rate; conn_fail_to_hotspot is 5 on every device, no TOML key reaches it | arzi |
| tests/test_digital_twin_network_neopixel.py:681 | W | NeoPixel pin and the FRAM its log writes to | arzi, dev, grkizi |
| tests/test_neopixel_wifi_integration.py:121 | W | the whole device's wiring (timer list) | arzi, dev, grkizi, wozi |
| tests/test_digital_twin_bus_hazard_concurrency.py:113 `_FRAM_DEVICES` (10 tests) | W | FRAM SPI pins, CS and size | arzi, dev, grkizi |
| tests/test_digital_twin_bus_hazard_concurrency.py:772 SGP40 race | W | SGP40 bus pins and neighbours | arzi, dev, wozi |
| tests/test_digital_twin_bus_hazard_concurrency.py:1122 SCD30 system commands | W | SCD30 bus, irq pin and neighbours | arzi, dev |
| tests/test_digital_twin_fram.py:915 silent FRAM | W | FRAM wiring | arzi, dev, grkizi |
| tests/test_digital_twin_clock_jump.py:258 stamps | W | BMP3XX bus (dev i2c0 alone, wozi i2c1 with sgp40) | dev, wozi |
| tests/test_digital_twin_clock_jump.py:267 backup age | W | SGP40 bus and FRAM wiring | arzi, dev, grkizi, wozi |
| tests/test_digital_twin_ntp.py:471 restore after outage | W | SGP40, SCD30 (its compensation input) and FRAM wiring | arzi, dev, grkizi, wozi |
| tests/test_digital_twin_ntp.py:503 lost sync | W | notification thresholds, SCD30 wiring, NeoPixel pin | arzi, dev |
| tests/test_digital_twin_hot_replug.py:144 replug per driver | W | the driver's bus and neighbours | bmp3xx: dev, wozi; isl29125: dev; scd30: arzi, dev; sgp40: arzi, dev, wozi |
| tests/test_digital_twin_hot_replug.py:239 BMP3XX power cycle | W | BMP3XX bus | dev, wozi |
| test_fram_less_boot (2 tests), scenarios `_lag_run` (4 tests) | W | parametrized over DEVICE_NAMES by CMr1; deduplication by read key still open | all six |
| tests/test_digital_twin_scd30.py:54, tests/test_digital_twin_sgp40.py:239, tests/test_digital_twin_launch.py:51, tests/test_digital_twin_wifi_modes.py `_scenario_plan()`, clock_jump :275/:314/:336/:354, ntp :440/:464/:495, loop_end :238, run_generic_integration :933/:1031/:1072, the tests_scripts `DEVICE_NAMES[0]` sites | open | not yet measured: next block | - |
| tests/test_digital_twin_isl29125_autorange.py:67, tests/test_digital_twin_uart_link.py:81 | W | only dev wires the part | dev |
