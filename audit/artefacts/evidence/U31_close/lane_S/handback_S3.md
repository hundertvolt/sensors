U31 lane S block S3 FINAL
Commits on audit/u31-s (S/wt-u31s), after 4ba0e09: 79be20c (BMP3XX reset-settle basis, the lead's item), 42552d6 (SCD30 waits). Nothing pushed, nothing uncommitted, rebuild.sh rc 0.
Steps:
- Applied, step 17 SCD30 (.050/.055/.057, U31 part): `_CMD_RESPONSE_WAIT_MS = const(50)`, `_ASC_ENABLE_WAIT_MS = const(10)`, `_SOFT_RESET_WAIT_MS = const(2500)`, tags renamed to `_ms`, all four call sites now `sleep_ms`. Values unchanged. Datasheet text from S/dstxt (no PDF renderer here): boot-up < 2 s (Interface Description :54), > 3 ms read delay (:570, :656).
- Applied, step 37 U31 part: the test reads the three values via `src_int`, the comments name `_SOFT_RESET_WAIT_MS`, and there is a new test `test_each_command_wait_is_a_whole_millisecond_sleep`. Shared FastAsyncSleep and RaiseOnArm were already in place.
- Lead's item, applied: src/asy_bmp3xx_driver.py:82 now reads `_RESET_SETTLE_MS = const(3)  # Bosch's reference bmp3_soft_reset() settles 2 ms (DS001 4.3.22 gives none for 0xB6); one tick more: sleep_ms() may wake up to 1 ms early`. DS001 :1717 states no wait for 0xB6. The test said the same wrong thing, so I fixed it too: `_TSTARTUP_MS` → `_BOSCH_RESET_SETTLE_MS = 2`, and the test is now `test_reset_settles_one_tick_past_the_reference_settle`.
- Already landed: step 41 (test_bus_hazard_multi_device.py:26 shared FastAsyncSleep); step 33 (test_asy_isl29125_driver.py:12-13); SGP40 .059/.068/.069 (`_HEATER_OFF_MAX_MS = const(1)` :65, `sleep_ms(_HEATER_OFF_MAX_MS + 1)` :825, `_exchange` `sleep_ms(delay_ms)` :699; the int-second general-call wait at :82 stays).
- Carry 1 (`PollRoundClock`): no test change needed. All four probes run inside `async with <session>, <dev>.i2c_device as i2c: await i2c.setup()` (bmp3xx :708-709, isl29125 :1539-1540, scd30 :910-911, sgp40 :815-816). That is the bus lock `recover()`/`clear()` hold for `_clear_locked`. So a +100 ms settle never lands inside a measured SCL-release window, and every clock-reading test still asserts what it meant.
- Carry 2 (twin `_FastSleep`): there is no `_FastSleep` on this tree; U30 had already switched the file to the shared FastAsyncSleep (:27, :309, :849), which covers both sleep forms. The file's time is unchanged, so I did not edit it.
Seen failing: the new SCD30 test, run against a never-committed version with only the names changed (int `_MS`, calls `sleep(_X_MS / 1000)`), failed with `AssertionError: [('sleep', 0.05), ('sleep', 0), …, ('sleep', 0.05), ('sleep', 0.01), ('sleep', 0.05), ('sleep', 2.5)]`. No guards, so no bites.
Checks (rc at -1 / 32768), all 0 / 0 with 0 memory markers: scd30 131, bmp3xx 138, i2c 119, neopixel 54, notification 67, the four notification integrations, ticks_rollover, notification_fram, sgp40 164, isl29125 246, bus_hazard_multi_device 23, bus_hazard_generated 39, twin bmp3xx/scd30/sgp40, twin bus hazard 22. Ruff on all 15 lane files is clean. Boot contiguity and every other tests_scripts reader pass (2173 passed).
Red checks (all the known ones, none mine to fix):
- test_tunables_register. My new lines: "src/asy_scd30_driver.py:72: scd30.cmd_response_wait_ms is tagged but has no SPECIFICATION.md Part N row", same at :74 (asc_enable_wait_ms) and :76 (soft_reset_wait_ms); "SPECIFICATION.md:11439: scd30.cmd_response_wait_s is a tuned row, but no file carries its @tunable tag", same at :11440 and :11441. S1's and S2's lines are unchanged.
- test_import_placement::test_the_pending_list_only_shrinks: S1's two `test_next_sleep_s_*` rows.
- test_twin_record: api_sha256 drift.
- mypy: only tests/test_neopixel_wifi_integration.py:59 (waits on W).
Part N, the lead's. Renamed tags: scd30.cmd_response_wait_s 0.05 → scd30.cmd_response_wait_ms 50 (src :72), asc_enable_wait_s 0.01 → asc_enable_wait_ms 10 (:74), soft_reset_wait_s 2.5 → soft_reset_wait_ms 2500 (:76). SPEC lines naming them: M.2 table :11126, :11127, :11128, :11129; Part N rows :11439-11441.
Relay line I would have written (to the lead): the three scd30 rows above, plus M.2's four `_s` tag names becoming `_ms`.
Times -1/32768 (base): scd30 22.16/28.41 (22.09/28.90); bmp3xx 13.74/13.83 (13.69/13.77); twin bus hazard 150.08/151.62 (149.96/151.56); every other lane file within 3 % of its base.
Modes: STA, AP, Silent, Off, USB and boot are all identical; the SCD30 waits are the same `sleep_ms` underneath as before. Each SCD30 register read, command and reset now allocates one fewer heap float. No console change. The BMP3XX edit changes comments and test names only.
Silent-failure scan, lane S's whole set (five src files, classes 1-7): nothing new. The early wakes are inherently safe: 49 ms ≥ 3 ms, 2499 ms ≥ 2 s, and ASC has no documented bound.
Decisions (agent, 2026-10-21):
1. The seen-failing run used a version with only the names changed, as S2 did.
2. The new test uses a local `_SleepForms` recorder that yields instead of waiting. I did not extend tests/_fast_sleep.py because it is outside lane S's set.
3. The BMP3XX test copy and name were changed to match the corrected basis.
Runs: precommit rc 1 (the known reds); s3_post1 rc 0; s3_full (pid 13781): I killed my own batch by pid 13785 because its count of busy processes was too strict and it was blocking itself; RUNS.md logs that as rc=143; s3_twinhaz rc 0; s3_ts rc 1 (the known reds). Logs: S/u31/laneS/s3_*.
Nothing is left for lane S.
nothing of mine is running
