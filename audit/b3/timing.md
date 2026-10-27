# Timing per level and GC stage (A.U35.23, A.U35.15, OR141.a (5), M.PROC.024)

Requirement: per level and GC stage the wall clock, peak RSS, host SSD writes and test counts, in B0, post-refresh (M.PROC.007/.012) and post-B3 columns (A.U35.23); the NTP loopback confirmation runs (A.U35.15); the UDP idle poll's twin measurement (OR141.a (5)); the 2**30 tick-wrap build's runs (M.PROC.024). Completion: every column filled from a gate log, every file more than 10 % slower made efficient. A defect any file records goes the OR12.a path (fixed with a regression test seen failing first, or an owner question), never a note alone, and passes A-C as a delta before it is applied (OR106.a). The file is complete when every row is terminal: biting, fixed, or justified with its reason. Opened by A.U35.01 / M.PROC.022 (agent, 2026-10-22); deleted with `audit/` at phase D.

| level | stage | wall clock | peak RSS | host SSD writes | tests | source log |
|---|---|---|---|---|---|---|

## The 2**30 tick-wrap build (M.PROC.024, A.U35.32)

`audit/sweeps/ticks30_build.sh build <scratch>` copies the pinned checkout (`/root/pico-toolchain/micropython`, v1.29.0,
read only) into the scratchpad, renames the Unix port's `mp_hal_ticks_ms()`/`mp_hal_ticks_us()` and wraps them with
one fixed offset each, read once from `TICKS30_WRAP_IN_MS`, and builds `build-ticks30` with the rig's own overrides
(`apply_unix_kbd_intr_override()`, both verified compiled in) plus `CFLAGS_EXTRA=-DMICROPY_PY_TIME_TICKS_PERIOD=1073741824`.
The literal is `(1<<30)`'s value, so make's shell needs no quoting (agent, 2026-10-22). The shared toolchain build is
never touched. Its self-check (`check`): `ticks_add(0, -1) + 1 == 2**30`, and with the wrap 1500 ms out both counters
cross it (`1073740324 -> 102 ms; 1072241825 -> 101775 us`).

**OF-32 (R-30), real clock.** `ticks30_build.sh probe <scratch> <tree> 600`: one twin `UARTLink` (dev's two UARTs),
the raw counters wrapping 300 s in, a byte every 100 s, then a 40-byte burst into a 5.2 ms flash stall, all through
the link's own wire time.

| tree | byte at 0-500 s | byte at 600 s (past 2**29 us) | stall burst at 0 s / 600 s | verdict |
|---|---|---|---|---|
| base `f3fff0e` | arrived | never arrived (`None`) | 32 kept, 8 lost / 0 kept, 0 lost | FAIL: OF-32 trips |
| lane Y final `5cf361c` | arrived | arrived | 32/8 / 32/8 | PASS |
| lane V `8edb5aa` (holds Y's fix and V's flash-stall fix) | arrived | arrived | 32/8 / 32/8 | PASS |

**The wrap tests on lane V's head (`8edb5aa`), on the 2**30 build**, the wrap at a quarter, half and three quarters
of each file's wall clock, both GC stages: `tests/test_ticks_rollover.py` (V's flash-stall wrap test) 23/23 at 950,
1900 and 2850 ms, 3.76-3.82 s each; `tests/test_digital_twin_machine.py` (Y's two link tests) 112/112 at 330, 660 and
1000 ms, 1.15-1.18 s each. Zero memory markers in any of the 12 logs. Both files' new tests drive `tests/_ticks30.py`'s
clock; the build adds a real counter wrap under the rest of each file.

Not exercised: a stall window straddling the 2**29 us alias (Y's finding at `digital_twin/_flash_stall.py:98`, fixed
by V's (start, length) windows) and a window exactly 2**30 us old (V's residual, `digital_twin/machine.py:937`).
Left to B2 (agent, 2026-10-22): M.PROC.024 (1), every L1 file using ticks, and (2), the twin suite per device with the
wrap inside Run 11's window; both need this file's measured wall clocks and Run 11's calibration.

**M.PROC.024 (1), every L1 file whose code reads ticks, on `d78d8f5e`** (agent, 2026-10-27). `audit/sweeps/ticks30_batch.py`
derives the set instead of listing it: every `tests/test_*.py` whose static import closure (over `build/generated_src`,
`src`, `tests`, `digital_twin` and `frozen_modules`, plus the generated device modules a `__import__` by device name
reaches) holds a module whose non-comment code names `ticks_ms`/`ticks_us`/`ticks_diff`/`ticks_add`. That is 84 of
the 89 files, 109 jobs with the five `PER_DEVICE` files once per derived device; the other five import no tick reader
(`test_digital_twin_poll_prewarm`, `test_math_helpers`, `test_microtest_hooks`, `test_strict_json`, `test_tmp_scratch`).
The readers are A.U14.34's grep re-located on this base: 10 `src/` modules, 53 sites (31 at U14; `asy_base_classes.py`, `asy_bmp3xx_driver.py`, `asy_i2c_driver.py`, `asy_isl29125_driver.py`, `asy_neopixel_driver.py`, `asy_notification_service.py`, `asy_system_service.py`, `asy_uart_comm.py`, `asy_uart_driver.py`, `asy_wifi_service.py`),
2 `digital_twin/` modules (`_flash_stall.py`, `run_generic_integration.py`) and 8 `tests/` helpers (`_async_harness.py`, `_bus_hazard_catalog.py`, `_fake_time.py`, `_fast_sleep.py`, `_sensortask_scenarios.py`, `_ticks30.py`, `_uart_comm_harness.py`, `machine.py`). The 25 files
installing `DrivenTime` stay in: it replaces only the time of the modules handed it, while the asyncio scheduler and
every other module read the real counter.

Method. `measure` ran each job once on build-standard at -1 for its wall clock (1349 s in all, every job
green); `wrap` ran each on build-ticks30 at both GC stages with `TICKS30_WRAP_IN_MS` at a quarter, half and three quarters
of that wall clock, one run per point: three runs per file per stage, 654 runs. The build fixes its offset at the
process's first counter read, not at start (a 500 ms busy wait before the first read left the wrap the full 1000 ms out),
so the batch's launcher reads `ticks_ms()` first, runs the file as `tests/_threshold_runner.py` does, and prints the period
and the start and end ticks. A run counts only if its end tick is below its start (the counter crossed). On the wall
clock, startup included, the later points of 6 short files fell after their exit (`test_asy_config_manager.py`, `test_asy_crc_checks.py`, `test_digital_twin_http_client.py`, `test_digital_twin_rp2_constants.py`, `test_digital_twin_unix_port_unretrieved_report.py`, `test_fakes.py`; those 10 runs
passed, crossing nothing); `rewrap` re-placed all six of each one's runs on its in-run span (first read to exit, the
shortest of its six), 36 runs, and the table shows those. The load gate (CHECKLIST 12) held a wall-time-bound file until
at most 4 heavy processes ran: 8 runs waited (1050 s in all, at most 610 s), none reached its 20-min bound.

Result: 654 counted runs (109 jobs x 6), every one exit 0, zero memory markers, period 1073741824 read from
inside the run, start = 2**30 minus its wrap point, the counter crossed, and the test summary identical to the job's
build-standard run (skips included). No failure, so (3) had nothing to fix. A container restart at about 00:32 (2026-10-27)
cut a resume while it waited in the gate, with no run in flight; the results file held only whole records and the
resume skipped them. Logs: `S/u35/laneT/t4r3/l1/logs/`, records `S/u35/laneT/t4r3/l1/results.jsonl`.

| file | build-standard -1 | wrap points (ms) | -1 on build-ticks30 | 32768 on build-ticks30 | time on build-ticks30 |
|---|---|---|---|---|---|
| `tests/test_asy_api_response.py` | 0.26 s, 25/25 passed, 0 failed, 0 skipped | 65, 130, 195 | 3/3 PASS 25/25 passed, 0 failed, 0 skipped | 3/3 PASS 25/25 passed, 0 failed, 0 skipped | 0.21-0.26 s |
| `tests/test_asy_base_classes.py` | 0.37 s, 197/197 passed, 0 failed, 0 skipped | 92, 185, 278 | 3/3 PASS 197/197 passed, 0 failed, 0 skipped | 3/3 PASS 197/197 passed, 0 failed, 0 skipped | 0.36-0.42 s |
| `tests/test_asy_bmp3xx_driver.py` | 13.66 s, 138/138 passed, 0 failed, 0 skipped | 3415, 6830, 10245 | 3/3 PASS 138/138 passed, 0 failed, 0 skipped | 3/3 PASS 138/138 passed, 0 failed, 0 skipped | 13.65-13.80 s |
| `tests/test_asy_captive_dns.py` | 25.59 s, 66/66 passed, 0 failed, 0 skipped | 6398, 12795, 19192 | 3/3 PASS 66/66 passed, 0 failed, 0 skipped | 3/3 PASS 66/66 passed, 0 failed, 0 skipped | 25.60-25.64 s |
| `tests/test_asy_config_manager.py` | 0.11 s, 240/240 passed, 0 failed, 0 skipped | 18, 36, 53, (re-placed on the in-run span; on the wall clock [('-1', 82)] ended before the wrap, passing) | 3/3 PASS 240/240 passed, 0 failed, 0 skipped | 3/3 PASS 240/240 passed, 0 failed, 0 skipped | 0.17-0.27 s |
| `tests/test_asy_crc_checks.py` | 0.03 s, 78/78 passed, 0 failed, 0 skipped | 4, 9, 14, (re-placed on the in-run span; on the wall clock [('-1', 22), ('32768', 22)] ended before the wrap, passing) | 3/3 PASS 78/78 passed, 0 failed, 0 skipped | 3/3 PASS 78/78 passed, 0 failed, 0 skipped | 0.03-0.06 s |
| `tests/test_asy_dns_client.py` | 0.87 s, 47/47 passed, 0 failed, 0 skipped | 218, 435, 652 | 3/3 PASS 47/47 passed, 0 failed, 0 skipped | 3/3 PASS 47/47 passed, 0 failed, 0 skipped | 0.87-0.92 s |
| `tests/test_asy_fram_allocation_budget.py` | 0.06 s, 2/2 passed, 0 failed, 0 skipped | 15, 30, 45 | 3/3 PASS 2/2 passed, 0 failed, 0 skipped | 3/3 PASS 2/2 passed, 0 failed, 0 skipped | 0.11-0.11 s |
| `tests/test_asy_fram_driver.py` | 0.16 s, 104/104 passed, 0 failed, 0 skipped | 40, 80, 120 | 3/3 PASS 104/104 passed, 0 failed, 0 skipped | 3/3 PASS 104/104 passed, 0 failed, 0 skipped | 0.16-0.21 s |
| `tests/test_asy_fram_manager.py` | 0.57 s, 149/149 passed, 0 failed, 0 skipped | 142, 285, 428 | 3/3 PASS 149/149 passed, 0 failed, 0 skipped | 3/3 PASS 149/149 passed, 0 failed, 0 skipped | 0.62-1.42 s |
| `tests/test_asy_fram_wire_trace.py` | 0.37 s, 9/9 passed, 0 failed, 0 skipped | 92, 185, 278 | 3/3 PASS 9/9 passed, 0 failed, 0 skipped | 3/3 PASS 9/9 passed, 0 failed, 0 skipped | 0.36-0.47 s |
| `tests/test_asy_framing_codecs.py` | 0.52 s, 20/20 passed, 0 failed, 0 skipped | 130, 260, 390 | 3/3 PASS 20/20 passed, 0 failed, 0 skipped | 3/3 PASS 20/20 passed, 0 failed, 0 skipped | 0.57-0.62 s |
| `tests/test_asy_i2c_driver.py` | 1.47 s, 119/119 passed, 0 failed, 0 skipped | 368, 735, 1102 | 3/3 PASS 119/119 passed, 0 failed, 0 skipped | 3/3 PASS 119/119 passed, 0 failed, 0 skipped | 1.47-1.47 s |
| `tests/test_asy_isl29125_driver.py` | 2.47 s, 246/246 passed, 0 failed, 0 skipped | 618, 1235, 1852 | 3/3 PASS 246/246 passed, 0 failed, 0 skipped | 3/3 PASS 246/246 passed, 0 failed, 0 skipped | 2.47-2.72 s |
| `tests/test_asy_neopixel_driver.py` | 0.72 s, 54/54 passed, 0 failed, 0 skipped | 180, 360, 540 | 3/3 PASS 54/54 passed, 0 failed, 0 skipped | 3/3 PASS 54/54 passed, 0 failed, 0 skipped | 0.67-0.77 s |
| `tests/test_asy_notification_service.py` | 0.16 s, 70/70 passed, 0 failed, 0 skipped | 40, 80, 120 | 3/3 PASS 70/70 passed, 0 failed, 0 skipped | 3/3 PASS 70/70 passed, 0 failed, 0 skipped | 0.16-0.21 s |
| `tests/test_asy_ntp_client.py` | 23.78 s, 196/196 passed, 0 failed, 0 skipped | 5945, 11890, 17835 | 3/3 PASS 196/196 passed, 0 failed, 0 skipped | 3/3 PASS 196/196 passed, 0 failed, 0 skipped | 23.78-24.28 s |
| `tests/test_asy_print_log.py` | 0.37 s, 112/112 passed, 0 failed, 0 skipped | 92, 185, 278 | 3/3 PASS 112/112 passed, 0 failed, 0 skipped | 3/3 PASS 112/112 passed, 0 failed, 0 skipped | 0.37-0.47 s |
| `tests/test_asy_scd30_driver.py` | 21.83 s, 133/133 passed, 0 failed, 0 skipped | 5458, 10915, 16372 | 3/3 PASS 133/133 passed, 0 failed, 0 skipped | 3/3 PASS 133/133 passed, 0 failed, 0 skipped | 21.82-27.19 s |
| `tests/test_asy_sgp40_driver.py` | 7.79 s, 164/164 passed, 0 failed, 0 skipped | 1948, 3895, 5842 | 3/3 PASS 164/164 passed, 0 failed, 0 skipped | 3/3 PASS 164/164 passed, 0 failed, 0 skipped | 7.78-8.74 s |
| `tests/test_asy_spi_driver.py` | 0.26 s, 67/67 passed, 0 failed, 0 skipped | 65, 130, 195 | 3/3 PASS 67/67 passed, 0 failed, 0 skipped | 3/3 PASS 67/67 passed, 0 failed, 0 skipped | 0.26-0.27 s |
| `tests/test_asy_system_service.py` | 24.38 s, 198/198 passed, 0 failed, 0 skipped | 6095, 12190, 18285 | 3/3 PASS 198/198 passed, 0 failed, 0 skipped | 3/3 PASS 198/198 passed, 0 failed, 0 skipped | 24.28-25.70 s |
| `tests/test_asy_uart_comm.py` | 61.7 s, 202/202 passed, 0 failed, 0 skipped | 15425, 30850, 46275 | 3/3 PASS 202/202 passed, 0 failed, 0 skipped | 3/3 PASS 202/202 passed, 0 failed, 0 skipped | 61.56-62.44 s |
| `tests/test_asy_uart_driver.py` | 5.03 s, 166/166 passed, 0 failed, 0 skipped | 1258, 2515, 3772 | 3/3 PASS 166/166 passed, 0 failed, 0 skipped | 3/3 PASS 166/166 passed, 0 failed, 0 skipped | 4.98-8.49 s |
| `tests/test_asy_uart_link_driver.py` | 3.73 s, 47/47 passed, 0 failed, 0 skipped | 932, 1865, 2798 | 3/3 PASS 47/47 passed, 0 failed, 0 skipped | 3/3 PASS 47/47 passed, 0 failed, 0 skipped | 3.78-5.28 s |
| `tests/test_asy_udp_socket.py` | 5.93 s, 65/65 passed, 0 failed, 0 skipped | 1482, 2965, 4448 | 3/3 PASS 65/65 passed, 0 failed, 0 skipped | 3/3 PASS 65/65 passed, 0 failed, 0 skipped | 5.93-5.93 s |
| `tests/test_asy_webserver_connections.py` | 1.32 s, 26/26 passed, 0 failed, 0 skipped | 330, 660, 990 | 3/3 PASS 26/26 passed, 0 failed, 0 skipped | 3/3 PASS 26/26 passed, 0 failed, 0 skipped | 1.32-1.42 s |
| `tests/test_asy_webserver_service.py` | 4.08 s, 225/225 passed, 0 failed, 0 skipped | 1020, 2040, 3060 | 3/3 PASS 225/225 passed, 0 failed, 0 skipped | 3/3 PASS 225/225 passed, 0 failed, 0 skipped | 3.92-6.28 s |
| `tests/test_asy_wifi_service.py` | 24.4 s, 270/270 passed, 0 failed, 0 skipped | 6100, 12200, 18300 | 3/3 PASS 270/270 passed, 0 failed, 0 skipped | 3/3 PASS 270/270 passed, 0 failed, 0 skipped | 24.38-24.89 s |
| `tests/test_async_harness.py` | 0.06 s, 18/18 passed, 0 failed, 0 skipped | 15, 30, 45 | 3/3 PASS 18/18 passed, 0 failed, 0 skipped | 3/3 PASS 18/18 passed, 0 failed, 0 skipped | 0.06-0.06 s |
| `tests/test_bus_hazard_generated.py` | 63.2 s, 39/39 passed, 0 failed, 0 skipped | 15800, 31600, 47400 | 3/3 PASS 39/39 passed, 0 failed, 0 skipped | 3/3 PASS 39/39 passed, 0 failed, 0 skipped | 63.19-63.36 s |
| `tests/test_bus_hazard_multi_device.py` | 2.97 s, 22/22 passed, 0 failed, 0 skipped | 742, 1485, 2228 | 3/3 PASS 22/22 passed, 0 failed, 0 skipped | 3/3 PASS 22/22 passed, 0 failed, 0 skipped | 2.92-3.37 s |
| `tests/test_digital_twin_bmp3xx.py` | 0.06 s, 26/26 passed, 0 failed, 0 skipped | 15, 30, 45 | 3/3 PASS 26/26 passed, 0 failed, 0 skipped | 3/3 PASS 26/26 passed, 0 failed, 0 skipped | 0.06-0.06 s |
| `tests/test_digital_twin_bus_hazard_concurrency.py` | 92.77 s, 22/22 passed, 0 failed, 0 skipped | 23192, 46385, 69578 | 3/3 PASS 22/22 passed, 0 failed, 0 skipped | 3/3 PASS 22/22 passed, 0 failed, 0 skipped | 92.51-94.16 s |
| `tests/test_digital_twin_clock_jump.py` | 24.38 s, 6/6 passed, 0 failed, 0 skipped | 6095, 12190, 18285 | 3/3 PASS 6/6 passed, 0 failed, 0 skipped | 3/3 PASS 6/6 passed, 0 failed, 0 skipped | 24.37-24.77 s |
| `tests/test_digital_twin_construction.py[arzi]` | 1.72 s, 4/4 passed, 0 failed, 0 skipped | 430, 860, 1290 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 1.62-1.72 s |
| `tests/test_digital_twin_construction.py[dev]` | 2.42 s, 4/4 passed, 0 failed, 0 skipped | 605, 1210, 1815 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 2.37-2.62 s |
| `tests/test_digital_twin_construction.py[grkizi]` | 1.68 s, 4/4 passed, 0 failed, 0 skipped | 420, 840, 1260 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 1.62-1.78 s |
| `tests/test_digital_twin_construction.py[klkizi]` | 1.63 s, 4/4 passed, 0 failed, 0 skipped | 408, 815, 1222 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 1.62-1.72 s |
| `tests/test_digital_twin_construction.py[schlafzi]` | 1.67 s, 4/4 passed, 0 failed, 0 skipped | 418, 835, 1252 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 1.62-1.77 s |
| `tests/test_digital_twin_construction.py[wozi]` | 1.98 s, 4/4 passed, 0 failed, 0 skipped | 495, 990, 1485 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 2.02-2.17 s |
| `tests/test_digital_twin_fram.py` | 0.52 s, 54/54 passed, 0 failed, 0 skipped | 130, 260, 390 | 3/3 PASS 54/54 passed, 0 failed, 0 skipped | 3/3 PASS 54/54 passed, 0 failed, 0 skipped | 0.57-0.67 s |
| `tests/test_digital_twin_fram_crash_points.py` | 9.39 s, 3/3 passed, 0 failed, 0 skipped | 2348, 4695, 7042 | 3/3 PASS 3/3 passed, 0 failed, 0 skipped | 3/3 PASS 3/3 passed, 0 failed, 0 skipped | 9.24-11.49 s |
| `tests/test_digital_twin_generic_wiring.py` | 0.06 s, 15/15 passed, 0 failed, 0 skipped | 15, 30, 45 | 3/3 PASS 15/15 passed, 0 failed, 0 skipped | 3/3 PASS 15/15 passed, 0 failed, 0 skipped | 0.06-0.11 s |
| `tests/test_digital_twin_hot_replug.py` | 7.79 s, 2/2 passed, 0 failed, 0 skipped | 1948, 3895, 5842 | 3/3 PASS 2/2 passed, 0 failed, 0 skipped | 3/3 PASS 2/2 passed, 0 failed, 0 skipped | 7.68-8.09 s |
| `tests/test_digital_twin_http_client.py` | 0.06 s, 38/38 passed, 0 failed, 0 skipped | 8, 17, 26, (re-placed on the in-run span; on the wall clock [('-1', 45), ('32768', 45)] ended before the wrap, passing) | 3/3 PASS 38/38 passed, 0 failed, 0 skipped | 3/3 PASS 38/38 passed, 0 failed, 0 skipped | 0.06-0.07 s |
| `tests/test_digital_twin_isl29125.py` | 0.06 s, 47/47 passed, 0 failed, 0 skipped | 15, 30, 45 | 3/3 PASS 47/47 passed, 0 failed, 0 skipped | 3/3 PASS 47/47 passed, 0 failed, 0 skipped | 0.06-0.07 s |
| `tests/test_digital_twin_isl29125_autorange.py` | 54.17 s, 22/22 passed, 0 failed, 0 skipped | 13542, 27085, 40628 | 3/3 PASS 22/22 passed, 0 failed, 0 skipped | 3/3 PASS 22/22 passed, 0 failed, 0 skipped | 54.09-54.15 s |
| `tests/test_digital_twin_launch.py` | 8.09 s, 26/26 passed, 0 failed, 0 skipped | 2022, 4045, 6068 | 3/3 PASS 26/26 passed, 0 failed, 0 skipped | 3/3 PASS 26/26 passed, 0 failed, 0 skipped | 8.08-8.08 s |
| `tests/test_digital_twin_loop_end.py[arzi]` | 17.51 s, 8/8 passed, 0 failed, 0 skipped | 4378, 8755, 13132 | 3/3 PASS 8/8 passed, 0 failed, 0 skipped | 3/3 PASS 8/8 passed, 0 failed, 0 skipped | 17.61-18.06 s |
| `tests/test_digital_twin_loop_end.py[dev]` | 3.47 s, 1/8 passed, 0 failed, 7 skipped | 868, 1735, 2602 | 3/3 PASS 1/8 passed, 0 failed, 7 skipped | 3/3 PASS 1/8 passed, 0 failed, 7 skipped | 3.47-3.62 s |
| `tests/test_digital_twin_loop_end.py[grkizi]` | 2.62 s, 1/8 passed, 0 failed, 7 skipped | 655, 1310, 1965 | 3/3 PASS 1/8 passed, 0 failed, 7 skipped | 3/3 PASS 1/8 passed, 0 failed, 7 skipped | 2.62-2.72 s |
| `tests/test_digital_twin_loop_end.py[klkizi]` | 2.62 s, 1/8 passed, 0 failed, 7 skipped | 655, 1310, 1965 | 3/3 PASS 1/8 passed, 0 failed, 7 skipped | 3/3 PASS 1/8 passed, 0 failed, 7 skipped | 2.62-2.72 s |
| `tests/test_digital_twin_loop_end.py[schlafzi]` | 2.62 s, 1/8 passed, 0 failed, 7 skipped | 655, 1310, 1965 | 3/3 PASS 1/8 passed, 0 failed, 7 skipped | 3/3 PASS 1/8 passed, 0 failed, 7 skipped | 2.62-2.77 s |
| `tests/test_digital_twin_loop_end.py[wozi]` | 3.12 s, 1/8 passed, 0 failed, 7 skipped | 780, 1560, 2340 | 3/3 PASS 1/8 passed, 0 failed, 7 skipped | 3/3 PASS 1/8 passed, 0 failed, 7 skipped | 3.07-3.17 s |
| `tests/test_digital_twin_machine.py` | 1.17 s, 113/113 passed, 0 failed, 0 skipped | 292, 585, 878 | 3/3 PASS 113/113 passed, 0 failed, 0 skipped | 3/3 PASS 113/113 passed, 0 failed, 0 skipped | 1.17-1.22 s |
| `tests/test_digital_twin_machine_uart.py` | 3.57 s, 25/25 passed, 0 failed, 0 skipped | 892, 1785, 2678 | 3/3 PASS 25/25 passed, 0 failed, 0 skipped | 3/3 PASS 25/25 passed, 0 failed, 0 skipped | 3.57-3.72 s |
| `tests/test_digital_twin_network_neopixel.py` | 14.56 s, 44/44 passed, 0 failed, 0 skipped | 3640, 7280, 10920 | 3/3 PASS 44/44 passed, 0 failed, 0 skipped | 3/3 PASS 44/44 passed, 0 failed, 0 skipped | 14.55-14.70 s |
| `tests/test_digital_twin_ntp.py` | 32.91 s, 16/16 passed, 0 failed, 0 skipped | 8228, 16455, 24682 | 3/3 PASS 16/16 passed, 0 failed, 0 skipped | 3/3 PASS 16/16 passed, 0 failed, 0 skipped | 32.89-34.11 s |
| `tests/test_digital_twin_rp2_constants.py` | 0.03 s, 8/8 passed, 0 failed, 0 skipped | 5, 10, 14, (re-placed on the in-run span; on the wall clock [('-1', 22), ('32768', 22)] ended before the wrap, passing) | 3/3 PASS 8/8 passed, 0 failed, 0 skipped | 3/3 PASS 8/8 passed, 0 failed, 0 skipped | 0.03-0.06 s |
| `tests/test_digital_twin_run_generic_integration.py` | 1.32 s, 43/43 passed, 0 failed, 0 skipped | 330, 660, 990 | 3/3 PASS 43/43 passed, 0 failed, 0 skipped | 3/3 PASS 43/43 passed, 0 failed, 0 skipped | 1.32-1.37 s |
| `tests/test_digital_twin_scd30.py` | 0.21 s, 55/55 passed, 0 failed, 0 skipped | 52, 105, 158 | 3/3 PASS 55/55 passed, 0 failed, 0 skipped | 3/3 PASS 55/55 passed, 0 failed, 0 skipped | 0.21-0.36 s |
| `tests/test_digital_twin_sensortask_integration.py[arzi]` | 59.74 s, 17/18 passed, 0 failed, 1 skipped | 14935, 29870, 44805 | 3/3 PASS 17/18 passed, 0 failed, 1 skipped | 3/3 PASS 17/18 passed, 0 failed, 1 skipped | 59.70-61.84 s |
| `tests/test_digital_twin_sensortask_integration.py[dev]` | 21.88 s, 5/18 passed, 0 failed, 13 skipped | 5470, 10940, 16410 | 3/3 PASS 5/18 passed, 0 failed, 13 skipped | 3/3 PASS 5/18 passed, 0 failed, 13 skipped | 22.62-23.16 s |
| `tests/test_digital_twin_sensortask_integration.py[grkizi]` | 19.93 s, 4/18 passed, 0 failed, 14 skipped | 4982, 9965, 14948 | 3/3 PASS 4/18 passed, 0 failed, 14 skipped | 3/3 PASS 4/18 passed, 0 failed, 14 skipped | 20.35-20.75 s |
| `tests/test_digital_twin_sensortask_integration.py[klkizi]` | 20.02 s, 4/18 passed, 0 failed, 14 skipped | 5005, 10010, 15015 | 3/3 PASS 4/18 passed, 0 failed, 14 skipped | 3/3 PASS 4/18 passed, 0 failed, 14 skipped | 20.46-20.76 s |
| `tests/test_digital_twin_sensortask_integration.py[schlafzi]` | 20.02 s, 4/18 passed, 0 failed, 14 skipped | 5005, 10010, 15015 | 3/3 PASS 4/18 passed, 0 failed, 14 skipped | 3/3 PASS 4/18 passed, 0 failed, 14 skipped | 20.45-20.91 s |
| `tests/test_digital_twin_sensortask_integration.py[wozi]` | 20.68 s, 4/18 passed, 0 failed, 14 skipped | 5170, 10340, 15510 | 3/3 PASS 4/18 passed, 0 failed, 14 skipped | 3/3 PASS 4/18 passed, 0 failed, 14 skipped | 20.86-21.35 s |
| `tests/test_digital_twin_sgp40.py` | 0.06 s, 24/24 passed, 0 failed, 0 skipped | 15, 30, 45 | 3/3 PASS 24/24 passed, 0 failed, 0 skipped | 3/3 PASS 24/24 passed, 0 failed, 0 skipped | 0.06-0.11 s |
| `tests/test_digital_twin_timer_pool.py[arzi]` | 10.75 s, 4/4 passed, 0 failed, 0 skipped | 2688, 5375, 8062 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 10.87-11.12 s |
| `tests/test_digital_twin_timer_pool.py[dev]` | 12.5 s, 4/4 passed, 0 failed, 0 skipped | 3125, 6250, 9375 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 12.78-13.12 s |
| `tests/test_digital_twin_timer_pool.py[grkizi]` | 10.75 s, 4/4 passed, 0 failed, 0 skipped | 2688, 5375, 8062 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 10.86-11.21 s |
| `tests/test_digital_twin_timer_pool.py[klkizi]` | 10.7 s, 4/4 passed, 0 failed, 0 skipped | 2675, 5350, 8025 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 10.86-11.06 s |
| `tests/test_digital_twin_timer_pool.py[schlafzi]` | 10.75 s, 4/4 passed, 0 failed, 0 skipped | 2688, 5375, 8062 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 10.86-11.11 s |
| `tests/test_digital_twin_timer_pool.py[wozi]` | 11.5 s, 4/4 passed, 0 failed, 0 skipped | 2875, 5750, 8625 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 11.63-11.97 s |
| `tests/test_digital_twin_uart_comm_hazard.py` | 1.67 s, 10/10 passed, 0 failed, 0 skipped | 418, 835, 1252 | 3/3 PASS 10/10 passed, 0 failed, 0 skipped | 3/3 PASS 10/10 passed, 0 failed, 0 skipped | 1.77-1.87 s |
| `tests/test_digital_twin_uart_field_sweep.py` | 59.74 s, 10/10 passed, 0 failed, 0 skipped | 14935, 29870, 44805 | 3/3 PASS 10/10 passed, 0 failed, 0 skipped | 3/3 PASS 10/10 passed, 0 failed, 0 skipped | 60.56-61.41 s |
| `tests/test_digital_twin_uart_link.py` | 61.41 s, 22/22 passed, 0 failed, 0 skipped | 15352, 30705, 46058 | 3/3 PASS 22/22 passed, 0 failed, 0 skipped | 3/3 PASS 22/22 passed, 0 failed, 0 skipped | 64.75-85.28 s |
| `tests/test_digital_twin_unix_port_unretrieved_report.py` | 0.03 s, 10/10 passed, 0 failed, 0 skipped | 4, 8, 13, (re-placed on the in-run span; on the wall clock [('-1', 22), ('32768', 22)] ended before the wrap, passing) | 3/3 PASS 10/10 passed, 0 failed, 0 skipped | 3/3 PASS 10/10 passed, 0 failed, 0 skipped | 0.03-0.06 s |
| `tests/test_digital_twin_wifi_modes.py` | 25.68 s, 1/1 passed, 0 failed, 0 skipped | 6420, 12840, 19260 | 3/3 PASS 1/1 passed, 0 failed, 0 skipped | 3/3 PASS 1/1 passed, 0 failed, 0 skipped | 25.83-25.98 s |
| `tests/test_driven_time.py` | 0.03 s, 19/19 passed, 0 failed, 0 skipped | 8, 15, 22 | 3/3 PASS 19/19 passed, 0 failed, 0 skipped | 3/3 PASS 19/19 passed, 0 failed, 0 skipped | 0.03-0.07 s |
| `tests/test_fakes.py` | 0.06 s, 55/55 passed, 0 failed, 0 skipped | 10, 20, 30, (re-placed on the in-run span; on the wall clock [('-1', 45)] ended before the wrap, passing) | 3/3 PASS 55/55 passed, 0 failed, 0 skipped | 3/3 PASS 55/55 passed, 0 failed, 0 skipped | 0.06-0.12 s |
| `tests/test_fram_integration.py` | 1.12 s, 12/12 passed, 0 failed, 0 skipped | 280, 560, 840 | 3/3 PASS 12/12 passed, 0 failed, 0 skipped | 3/3 PASS 12/12 passed, 0 failed, 0 skipped | 1.22-1.47 s |
| `tests/test_generated_boot_entry.py` | 0.06 s, 5/5 passed, 0 failed, 0 skipped | 15, 30, 45 | 3/3 PASS 5/5 passed, 0 failed, 0 skipped | 3/3 PASS 5/5 passed, 0 failed, 0 skipped | 0.11-0.17 s |
| `tests/test_machine_uart_link.py` | 0.16 s, 18/18 passed, 0 failed, 0 skipped | 40, 80, 120 | 3/3 PASS 18/18 passed, 0 failed, 0 skipped | 3/3 PASS 18/18 passed, 0 failed, 0 skipped | 0.22-0.32 s |
| `tests/test_neopixel_wifi_integration.py` | 2.62 s, 8/8 passed, 0 failed, 0 skipped | 655, 1310, 1965 | 3/3 PASS 8/8 passed, 0 failed, 0 skipped | 3/3 PASS 8/8 passed, 0 failed, 0 skipped | 2.73-3.08 s |
| `tests/test_notification_fram_integration.py` | 0.21 s, 3/3 passed, 0 failed, 0 skipped | 52, 105, 158 | 3/3 PASS 3/3 passed, 0 failed, 0 skipped | 3/3 PASS 3/3 passed, 0 failed, 0 skipped | 0.22-0.22 s |
| `tests/test_notification_neopixel_integration.py` | 0.11 s, 6/6 passed, 0 failed, 0 skipped | 28, 55, 82 | 3/3 PASS 6/6 passed, 0 failed, 0 skipped | 3/3 PASS 6/6 passed, 0 failed, 0 skipped | 0.17-0.17 s |
| `tests/test_notification_scd30_integration.py` | 0.42 s, 4/4 passed, 0 failed, 0 skipped | 105, 210, 315 | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 3/3 PASS 4/4 passed, 0 failed, 0 skipped | 0.42-0.47 s |
| `tests/test_notification_scd30_sgp40_integration.py` | 0.37 s, 2/2 passed, 0 failed, 0 skipped | 92, 185, 278 | 3/3 PASS 2/2 passed, 0 failed, 0 skipped | 3/3 PASS 2/2 passed, 0 failed, 0 skipped | 0.42-0.52 s |
| `tests/test_notification_sgp40_integration.py` | 0.11 s, 3/3 passed, 0 failed, 0 skipped | 28, 55, 82 | 3/3 PASS 3/3 passed, 0 failed, 0 skipped | 3/3 PASS 3/3 passed, 0 failed, 0 skipped | 0.16-0.27 s |
| `tests/test_ntp_fram_system_integration.py` | 7.59 s, 12/12 passed, 0 failed, 0 skipped | 1898, 3795, 5692 | 3/3 PASS 12/12 passed, 0 failed, 0 skipped | 3/3 PASS 12/12 passed, 0 failed, 0 skipped | 7.60-7.66 s |
| `tests/test_ntp_wifi_dns_integration.py` | 1.47 s, 13/13 passed, 0 failed, 0 skipped | 368, 735, 1102 | 3/3 PASS 13/13 passed, 0 failed, 0 skipped | 3/3 PASS 13/13 passed, 0 failed, 0 skipped | 1.47-1.52 s |
| `tests/test_readiness_gates.py` | 0.11 s, 14/14 passed, 0 failed, 0 skipped | 28, 55, 82 | 3/3 PASS 14/14 passed, 0 failed, 0 skipped | 3/3 PASS 14/14 passed, 0 failed, 0 skipped | 0.17-0.17 s |
| `tests/test_reset_call_site_invariant.py` | 0.31 s, 3/3 passed, 0 failed, 0 skipped | 78, 155, 232 | 3/3 PASS 3/3 passed, 0 failed, 0 skipped | 3/3 PASS 3/3 passed, 0 failed, 0 skipped | 0.32-0.42 s |
| `tests/test_sensortask.py[arzi]` | 32.85 s, 105/105 passed, 0 failed, 0 skipped | 8212, 16425, 24638 | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 35.73-43.33 s |
| `tests/test_sensortask.py[dev]` | 52.22 s, 105/105 passed, 0 failed, 0 skipped | 13055, 26110, 39165 | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 56.56-70.84 s |
| `tests/test_sensortask.py[grkizi]` | 33.18 s, 105/105 passed, 0 failed, 0 skipped | 8295, 16590, 24885 | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 35.33-43.25 s |
| `tests/test_sensortask.py[klkizi]` | 33.31 s, 105/105 passed, 0 failed, 0 skipped | 8328, 16655, 24982 | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 35.26-49.13 s |
| `tests/test_sensortask.py[schlafzi]` | 32.97 s, 105/105 passed, 0 failed, 0 skipped | 8242, 16485, 24728 | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 40.28-49.90 s |
| `tests/test_sensortask.py[wozi]` | 37.36 s, 105/105 passed, 0 failed, 0 skipped | 9340, 18680, 28020 | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 3/3 PASS 105/105 passed, 0 failed, 0 skipped | 47.73-56.22 s |
| `tests/test_setter_microdot_integration.py` | 0.22 s, 34/34 passed, 0 failed, 0 skipped | 55, 110, 165 | 3/3 PASS 34/34 passed, 0 failed, 0 skipped | 3/3 PASS 34/34 passed, 0 failed, 0 skipped | 0.32-0.57 s |
| `tests/test_shared_helpers.py` | 0.42 s, 43/43 passed, 0 failed, 0 skipped | 105, 210, 315 | 3/3 PASS 43/43 passed, 0 failed, 0 skipped | 3/3 PASS 43/43 passed, 0 failed, 0 skipped | 0.47-0.62 s |
| `tests/test_ticks_rollover.py` | 3.62 s, 23/23 passed, 0 failed, 0 skipped | 905, 1810, 2715 | 3/3 PASS 23/23 passed, 0 failed, 0 skipped | 3/3 PASS 23/23 passed, 0 failed, 0 skipped | 3.78-3.98 s |
| `tests/test_uart_comm_cancel_sweep.py` | 37.32 s, 10/10 passed, 0 failed, 0 skipped | 9330, 18660, 27990 | 3/3 PASS 10/10 passed, 0 failed, 0 skipped | 3/3 PASS 10/10 passed, 0 failed, 0 skipped | 39.29-41.41 s |
| `tests/test_uart_comm_hazard.py` | 97.98 s, 123/123 passed, 0 failed, 0 skipped | 24495, 48990, 73485 | 3/3 PASS 123/123 passed, 0 failed, 0 skipped | 3/3 PASS 123/123 passed, 0 failed, 0 skipped | 103.04-108.51 s |
| `tests/test_voc_algorithm.py` | 2.02 s, 46/46 passed, 0 failed, 0 skipped | 505, 1010, 1515 | 3/3 PASS 46/46 passed, 0 failed, 0 skipped | 3/3 PASS 46/46 passed, 0 failed, 0 skipped | 3.48-7.64 s |
| `tests/test_website_build_integration.py` | 0.17 s, 7/7 passed, 0 failed, 0 skipped | 42, 85, 128 | 3/3 PASS 7/7 passed, 0 failed, 0 skipped | 3/3 PASS 7/7 passed, 0 failed, 0 skipped | 0.22-0.27 s |
| `tests/test_write_counters.py` | 0.03 s, 9/9 passed, 0 failed, 0 skipped | 8, 15, 22 | 3/3 PASS 9/9 passed, 0 failed, 0 skipped | 3/3 PASS 9/9 passed, 0 failed, 0 skipped | 0.03-0.03 s |
