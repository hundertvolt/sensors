# U31 relay (lanes write only where their brief says; the lead writes merges and messages)

<BASE> = aba11d5 (U30's squash 06a8ae5 plus its two CI fixes: the cross-browser installer, every CI job on ubuntu-24.04)

## C
<CORE> 8f11025

## S
<LED> 83d86ce (branch audit/u31-s; also carries the five lane-S integration builders' _frame_ms writes, since mypy flags a write of the removed neopixel_dt; W's test_neopixel_wifi_integration.py:59 stays mypy-red until W converts it)
S1 602bb5c: tests_scripts/test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree red until the lead's Part N edit: "src/asy_notification_service.py:62: notify.min_sleep_ms is tagged but has no SPECIFICATION.md Part N row"; "tests/test_asy_notification_service.py:42: l1.asy_notification_service_next_sleep_min_ms is tagged but has no SPECIFICATION.md Part N row"; "SPECIFICATION.md:11436: notify.min_sleep_s is a tuned row, but no file carries its @tunable tag"; "SPECIFICATION.md:11437: notify.cfg_fail_interval_s: Sites list [('src/asy_notification_service.py', '600.0')], the tags say [('src/asy_notification_service.py', '600')]"; "SPECIFICATION.md:11663: l1.asy_notification_service_next_sleep_min_s is a tuned row, but no file carries its @tunable tag"

## W
<NET> 851a4cb

## F

## T
- T→D (README rows): digital_twin/README.md flag table gains `--test-loop-lag-ms N` (LOOP_LAG max_us/p99_us/samples, one line per 5 s window) and `--test-drop-timer-fire reset|sequencer` (the twin's drop knob set before that one-shot's arm, cleared once its fire was dropped; DROP_ARMED/FIRE_DROPPED lines); tests_hardware/README.md flash-tier list gains `test_flash_write_loop_gap_is_recorded` (persistence_write, device_scripts/flash_write_loop_gap.py, relative `_stretch.bin`); SPEC E.9's runner-only exception lists both flags; F.3 `lag.loop` names `loop_lag_under_combined_load` (L2, every device) and `hold.fram_block` is cited by fram_command_hold_timing.py:30.
- T→lead (Part N, R-24): rows owed for l2.twin_loop_lag_report_ms = 5000 (digital_twin/run_generic_integration.py), l2.loop_lag_load_s = 60.0, l2.loop_lag_settle_s = 10.0, l2.loop_lag_recovered_ms = 50, l2.loop_lag_period_ms = 10 (scripts/_digital_twin_scenarios.py), l3.memory_stress_flash_gap_script_timeout_s = 30.0 (tests_hardware/flash/test_memory_stress.py); twin_record re-record (flash_write_loop_gap.py new; fram_command_hold_timing.py, test_memory_stress.py changed).
- T3 consumer export: buildgen.validate.smallest_hard_consumer (c4fe5ad); takes (DeviceModel, src_dir), returns HardConsumer(ms, what, relief); dev 925 ms, every other device 6000 ms

## D
- lead→D (facts owed by wave 1; each block's hand-back in S/u31/handbacks/ has the source):
  - C1: `arm_tick_timer(..., quiet=False)` API end state; quiet= drops only the refusal line (SPEC mentions at about :4019, :8285).
  - C2: L.3 table and F.3 `stall.i2c_transfer` gain the build rule `bus.i2c-timeout-consumer` (formula 2 × timeout ≤ min of each uart_link's reply slack and (wdt.timeout_ms − system.task_check_s × 1000) × 1000; fix text 'set timeout to at most N, or lower poll_idle_ms'); D.4 is checked by tests_scripts/test_src_sleep_forms.py.
  - F: digital_twin/README.md fidelity rows: EPERM row (`connect_on_an_inactive_station_raises_eperm`); the AP-down row extended (the link drops to LINK_JOIN, address kept); a deactivation row (`deactivating_the_station_drops_its_link_its_address_and_a_pending_connect`).
  - W3: still say `asyncio.wait_for()`, now `wait_for_ms`: SPEC about :6196-6198 (F.2), :7509 ('applied via `asyncio.wait_for()`'), tests_hardware/README.md about :1400.
  - T: its own T→D line under ## T.
  - C3: A.7 (setup costs) gains that each unit's feed margin is Part N's `boot.setup_unit_stretch_ms`, and that a uart_link's boot drain (5 × its bus's poll_wait_ms) is the one timed wait in a setup unit; CLAUDE.md's `UartLinkExerciser` is `UARTLinkDriver` (src/asy_uart_link_driver.py:43); F.1/C.9.1 gain the supervisor's own fault (one SYSTEM E42 entry, then the watchdog reset, code 2); F.3 gains the escalation entry bounded by `system.escalation_entry_wait_ms`.
  - L1 (lead's fix block, running): a MemoryError at that bounded wait takes the timeout's path to the reset; D states it beside the timeout once L1 lands (its hand-back: S/u31/handbacks/L1_final.md).
  - Part N (renames, the two rule rows, the BMP3XX timing cells, M.2's SCD30 names) is the lead's: S/u31/lead/partn.py, applied at the merge; D never edits Part N.

## Lead
- 00:25 lead: <CORE> 8f11025 merged into audit/u31-api (ff). W: merge audit/u31-api for OF-29's WiFi sibling.
- 00:27 lead: C1 FINAL 8f11025 (handbacks/C1_final.md); C2 launched from it.
- 00:28 lead: <LED> 83d86ce and <NET> 851a4cb merged into audit/u31-api (now 75e26ef, with <CORE>). W: merge audit/u31-api for test_neopixel_wifi_integration.py. F: merge audit/u31-api for :56's edge.
- 00:41 lead: S1 FINAL 602bb5c (handbacks/S1_final.md); S2 launched. Lead edits owed: S/u31/lead_edits.md.
- 01:54 lead: int 996a252 (lanes C, S, W, F + Part N + import-placement shrink); L1 (lead fixes) and D2 launched from it; lane D order D2, D3, D1.
- 02:55 lead: d56c92d = int with T merged + Part N rows; T3 and D1 launched from it.
- FX1 supervisor fault code: SUPERVISOR_RAISED 115 (696bc87)
