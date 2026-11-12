B2 falsification, written by the agent (Tue Nov  3 06:19:37 UTC 2026)

Worktree `S/wt-b2f` at `8019a9ef`, read-only: one planted break, restored with `git checkout`. Runs (all through
`S/u35/lead/run.sh`): `b2f_rebuild`, `b2f_probe1` (one probe file, 8 probes), `b2f_rebuild2`, `b2f_storm_plant`
(planted), `b2f_sizes`, `b2f_collect` (`tests_hardware --collect-only`), `b2f_wbcorner` (CPython arithmetic only).
That is 3 test-type runs out of the 10 allowed. Probe sources and outputs: `S/u35r/r1/B2/fz/` (`probe/probe_b2f.py`, the
copied old modules `probe/math_25c.py`, `probe/cm_base.py` (93224dab), `probe/api_response_25c.py`, `sizes_*.tsv`,
`storm_logs/`). Line numbers below are at `8019a9ef` unless a commit is named.

## Per claim

**1. Reset codes: STANDS.** `_BOOTLOADER = const(_RR_COMMAND_INCOMPLETE)` (src/asy_system_service.py:97); the sequence
records `purpose if done and (flushed or purpose == _RR_CONFIG_RESET) else 9` (:467) and calls `system_bootloader` only
for `_BOOTLOADER` (:476). `machine.bootloader` has no other call site in src/ or the generated modules. No `_RR_BOOTLOADER`,
no reset code 4 anywhere in firmware, catalog (buildgen/error_catalog.json:185-200 skips 4), js/html/mockdata, tests/,
tests_hardware/, digital_twin/ or scripts/ (the remaining 4s are the twin runner's *exit* code for a bootloader entry,
e.g. scripts/_digital_twin_scenarios.py:2105). Wording caveat only: a hung step or an unarmable reset ends in a watchdog
reset with no `machine.reset()` call at all (record 9 or 6).

**2. ResetBits/ConfigUnpersisted gone: STANDS.** No hit in the tree outside `audit/`, in `build/generated_src` (all six
devices' modules and definitions), `build/generated_html` or `frozen_modules/`. `get_reset_reason()` serves the decoded
record; `_flush_config_stores()` still answers False for `store.unpersisted` (:294). tests_hardware: no marker line
added or removed in the diff, 231 `def test_` at both commits, collect-only 202/233 collected (31 deselected by the
default gates), no collection error. Wording caveat: src/ still reads the reset registers indirectly, through
`machine.reset_cause()` in `begin_boot()` (:149), which reads CHIP_RESET and WATCHDOG REASON inside the port; no raw
`mem32` read of them remains.

**3. Wet bulb / rel_humidity: REFUTED (second sentence).** `rel_humidity()` uses b = 237.3 above 0 degC (src/math_helpers.py:158),
`25caf528:src/math_helpers.py:129` uses 237.4. `b2f_probe1`: on a -30..40 degC x 0..100 g/m3 grid 634 of 5,781 points
differ, e.g. `rel_humidity(20.0, 10.0)` 57.89359 (25caf528) vs 57.86340 (now); T <= 0 and clamped points agree. The
clamp itself matches 25caf528. First sentence stands: 330,291 points of -20..50 x 5..99 all finite (corners included),
and 12 outside inputs (just past each bound, NaN, +-inf, None) all None.

**4. Config store: REFUTED (narrow, the word "persisted").** SCD30's store is value-storing (FRCNoise/FRCRate/FRCWindow,
src/asy_scd30_driver.py:122-124, 210) but its logger is RAM-only by the owner's decision (`_CFG_LOG_FRAM = False`,
:193-194; src/asy_base_classes.py:785), so its absent file's W22 is logged and never persisted - `b2f_storm_plant`'s
`fram_writes_by` has no CFGMGR_SCD30 while config_SCD30.cfg was written. So "one persisted W22 per store" and "a fresh dev
boot persists exactly one W22 per value-storing store" are false for SCD30 (the twin's check reads errcount, RAM
included, so it counts it). Everything else held: one `wrn_s` per `setup()` (src/asy_config_manager.py:565), one
write; an unreadable file sets `writable = False` and `write_config()` refuses it; a command-only schema only prints.
Note: `_check_quiet_boot` compares slots, not counts, so "exactly one" rests on the code, not on that check.

**5. W69/absent_at_boot/restored readers: STANDS.** No `.restored`, `absent_at_boot`, `CONFIG_LOST` or W69 in src/,
generated modules/definitions, js/html/tests_js, tests/, tests_hardware/, digital_twin/, scripts/. "69" survives only as
E NTP_MALFORMED and as SYSTEM's reserved W band `[[69, 70]]` (error_catalog.json:8, nothing reads it).

**6. Refused uptime tick: REFUTED.** `TickSeconds` requires a read at least once per 2**29 ms (src/asy_base_classes.py:352-354;
a longer gap reads negative and is dropped). With the tick refused, `_status_loop()` never passes, and the remaining
readers are request-driven (`GET /status`, a task end, a webserver drop). `b2f_probe1` (`uptime_unread`): 536,930 s with
no read -> `get_uptime()` answers 0; a twin service read every 3.1 days answers 536,930. So SysUptime is not right on
every read, and "what stops is exactly this" misses the periodic read. "Nothing reboots" holds.

**7. Escalation record: REFUTED (narrow).** A system command accepted while the entry write hangs rewrites the record:
the gate checks only `_reset_armed` (:369), not the `_reset_decided` the escalation set (:551), and acceptance writes 9
(:394); the shutdown sequence feeds once, then waits for a parked supervisor forever. `b2f_probe1`
(`command_during_hung_entry`, the rig of `test_a_command_accepted_while_the_escalation_logs_keeps_its_own_reset` with the
write never released): record 5 at the hang, `reboot_system()` True, record 9 after, one feed, reset never armed, so the
watchdog's reset reads 9 and the escalation's cause is lost. The code comment at :549-550 states this interleaving.

**8. Chip-setup failure path: STANDS.** `_init_failed` had six call sites at 93224dab, all inside `_init_*()`; each
`_init_*()` is called only from its `_read_loop()` start (git grep at 93224dab). No `_recover_device()` calls an
`_init_*()`. `_error_check`, `_climb_ladder`, `_recover_bus` are unchanged in the diff.

**9. Repeats in one slot: REFUTED (narrow).** The newest-entry rule collapses consecutive repeats only
(src/asy_print_log.py:181-190); the old run flags collapsed a run with other entries in between. `b2f_probe1`
(`interleaved_slots`): six rounds of `get_dict(["Missing"])` + `write_config({"Unknown": 1})` on one store: 93224dab's
manager 2 slots (ErrCount 7), 8019a9ef's 10 of 10 slots (ErrCount 12), the ring full and older history gone. Needs two
distinct failures in one store's logger (a contract error is itself a firmware defect). A store invalid for the boot
logs one code throughout and keeps one slot, as claimed.

**10. setup() return values: REFUTED (first sentence).** Product callers read them: src/asy_fram_manager.py:671 (`if not
await self.setup(): return`, the chip-watch loop) and src/asy_uart_link_driver.py:290 (`if await self._comm.setup():`).
tests/test_readiness_gates.py:3 now says "setup() answers a bool where product code reads it". The boot batch
(`run_setups`, :692-700) reads none. Second sentence stands: `b2f_probe1` (`unreferenced_sequence`, a SystemService built
without the tests' `track_starts`, `gc.collect()` every 10 ms) -> record 3, reset armed.

**11. api_response replies: REFUTED.** A raising `_set_dict_cfg()` differs too: at 25caf528 it ran inside
`handle_set_cmd`'s try (api_response.py:92-105, ERR 100, which the endpoint turned into "Failed" for the group and a
200, 25caf528 asy_webserver_service.py:463-469); now it runs outside the try (src/asy_api_response.py:63), the route
raises and the reply is the 500 envelope (src/asy_webserver_service.py:788-792), the other groups' results of that PUT
lost. `b2f_probe1` (`api_response_raise`, MemoryError): 25caf528 `{'res': 'ERR', 'code': 100, ...}`, now raised.
`_set_dict_cfg()` guards its extension points but not its own allocations. Also: for a raising hook the 25caf528
*endpoint* already answered OK with the group "Failed"; only the module's return changed. "Codes 2-5 had no product
producer at 25caf528" stands (`parse_cmd_request` is never called there).

**12. No check weaker: REFUTED.**
- Storm bound: `events = {name: 1 for ... if name.startswith("CFGMGR_")}` (scripts/_digital_twin_scenarios.py:614) gives
  every config logger one event, but each scenario boot plants config_SYSTEM.cfg (`_log_at_error_level`, :1244-1254) and
  the runner plants config_NTP.cfg (digital_twin/run_generic_integration.py:1121-1125), so CFGMGR_SYSTEM and CFGMGR_NTP
  log no W22 and their bound doubled for nothing. Planted break (`b2f_storm_plant`): one extra persisted CFGMGR_SYSTEM
  warning in `SystemService.setup()` -> the scenario PASSED with `CFGMGR_SYSTEM:4` writes (old bound 2; CFGMGR_NTP 2 of
  a bound 4). Restored.
- tests_scripts/test_digital_twin_generated_boot.py:243-245: a tolerance, not an expectation: any W22 in any CFGMGR_
  logger passes, none is required, CFGMGR_NTP's included (its file is planted, so a W22 there means it was unreadable),
  counts unchecked. `_check_quiet_boot` does the exact version.
- tests_hardware/manual/manual_persistence.py dropped `_power_on_bits` (93224dab :77-79, used at :308, :311, :321) instead
  of reading the registers over the exec as bench/test_reset_reasons.py now does.
- Minor: tests/test_asy_fram_manager.py's erase-cut test accepts `ErrCount == 0` with any ring where 93224dab required a
  restored store's ring to match.
- Checked and mechanical: `_check_quiet_boot` (exact; the NTP exclusion matches the launcher); the four FRAM-layout
  scenarios in tests/_sensortask_scenarios.py now boot over the image build's own filesystem so no file is absent, their
  chunk assertions unchanged; each of the 35 removed test functions and the one removed scenario
  (`webserver_status_lists_a_module_whose_config_write_failed_until_its_next_good_write`, item 2) maps to an item above;
  the one without a replacement is `test_mempause_answers_valid_with_every_timer_arm_failing` (item 6).

**13. Numbers: STANDS for bytecode, imageFreeBytes not verified.** `module_sizes.sh`: 93224dab 207,155 B, 8019a9ef
205,832 B, -1,323 B; 11 modules shrank (system_service -742, config_manager -182, base_classes -175, math_helpers -58,
bmp3xx -42, isl29125 -36, sgp40 -27, scd30 -25, print_log -22, wifi -13, notification -1), none grew. I did not run
`scripts/build_firmware.py dev`: it builds inside the shared toolchain tree.

## Defects outside the claims
- (a) A "Valid" mempause with the uptime tick refused leaves FRAM paused for the rest of the boot (`b2f_probe1`
  `mempause_refused_tick`: still paused an hour after a 5 s pause). src/asy_system_service.py:659-660 still says "a pause
  always ends"; 25caf528 aborted a pause it could not end ("safer to abort the pause than risk that"). The claim names it,
  but the answer and the comment are now untrue.
- (c) ResetReason 9's catalog text "reboot after either command whose purpose did not complete" (error_catalog.json:192)
  no longer covers what records 9: a reboot whose flush failed and a bootloader command whose shutdown hung.
- (c) Stale comment src/asy_bmp3xx_driver.py:92 "the config unreadable (no bus rung)": no path runs a bus rung now, and
  `_init_bmp()` no longer uses the `_CFG_UNREADABLE`/`_CHIP_WRITE_FAILED` distinction.
- (a, as at 25caf528) With the cold-dry corner refusal gone, the wet bulb exceeds the dry bulb at 204 of 13,395 grid points
  (`b2f_wbcorner`): -20 degC/5 % -> -17.59 degC, 2.4 K above. 93224dab refused that corner.
