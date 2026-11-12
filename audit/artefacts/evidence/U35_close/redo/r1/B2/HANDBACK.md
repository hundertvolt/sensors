B2 hand-back, written by the agent (Tue Nov  3 05:44:31 UTC 2026)

Worktree `S/wt-b2`, branch `audit/r1-b2`, from 93224dab. Commits: 82cbf08a (items 3, 4), 16047d96 (items 1, 2),
8019a9ef (items 5-9). Nothing pushed. Run logs: `S/u35/lead/b2_*.log`.

## Items

1. **`/status` ResetBits and ConfigUnpersisted: removed** (16047d96). Emitter lines (`buildgen/codegen.py`), both
   website rows (`buildgen/definitions.py`), `get_reset_bits()`/`get_config_unpersisted()`, the `mem32` reads and their
   constants, `mockdata/samples.json` keys, their unit tests (4 reset-bit tests, 1 unpersisted test) and the twin's
   unpersisted scenario (now `refused_config_write_is_logged_and_the_next_one_lands`, which waits on E33). ResetReason
   and the store's internal unpersisted flag (the shutdown flush) stay. Test: the key-set tests
   `tests_scripts/test_buildgen_definitions.py::test_system_status_lists_its_rows_in_the_published_order` and
   `test_buildgen_generate.py::test_real_device_system_status_reports_every_system_key_in_order` changed first, red
   (b2_keys_red, b2_keys_red2: 1 and 6 failed), then green. Hardware readers: `tests_hardware/bench/test_reset_reasons.py`
   reads the raw REASON bits itself (`_READ_REASON_BITS`, one `board.exec` of `mem32[0x40058008] & 3`);
   `tests_hardware/manual/manual_persistence.py` loses its ResetBits reads, and its HAD_POR/RUN-bit checks are **listed
   for R2** (basis: a manual script with no device-side read path of its own; the check needs the bench). The twin loop-end
   test reads `machine.mem32` directly. Checked by `--collect-only` (and `--twin` where the file has a twin form).
2. **Reset code 4: removed** (16047d96). The bootloader command records code 9 at acceptance (`_BOOTLOADER = const(_RR_COMMAND_INCOMPLETE)`,
   no new branch) and writes no code of its own; catalog row 4 goes; both machine fakes model BOOTSEL as silicon does
   (both regions lost, cause 3, REASON TIMER), so the next boot reads 2. Tests: the bootloader command tests in
   `tests/test_asy_system_service.py` changed first, red (b2_sys_red: 7 failed), then green; the shared fake contract
   `check_a_bootsel_round_trip_loses_both_regions` (new, `tests/_mem_backup_contract.py`) red on a planted break of the
   fake (b2_plant_bootsel), green; the twin suite's Run 12/13 and the bench/flash tests expect 2.
3. **The wet bulb's cold-dry corner: removed** (82cbf08a). `_WB_CORNER_*` and the check go, the pre-audit range check
   stays. Test: the corner test went first; `test_wet_bulb_answers_across_the_whole_range_check` (a corner point
   returns a value) red, then green (b2_math_red/green).
4. **`rel_humidity()` clamps to 0-100 % again** (82cbf08a), with `_MAGNUS_RH_ROUNDING` gone. Test:
   `test_rel_humidity_clamps_to_0_100` (a value just over 100 reads 100.0) red, then green (b2_math_red/green).
5. **W69 CONFIG_LOST, `absent_at_boot`, the logger's `restored`: removed** (8019a9ef). A missing file logs W22 "not
   found" (persisted, once per boot) where its defaults are written once; a command-only schema keeps its printed note.
   Pinning tests that went first: the CONFIG_LOST tests in `test_asy_system_service.py`, the `absent_at_boot` asserts in
   `test_asy_config_manager.py`, the `restored` uses in `test_asy_print_log.py`/`test_asy_fram_manager.py`. Test:
   `test_configmanager_writes_the_defaults_once_when_the_file_is_absent` and
   `test_an_enoent_from_the_same_stand_in_is_the_absent_file_path` read W22, red on the committed sources (b2_red5),
   green. The suite's fresh-boot check (`_check_quiet_boot(..., fresh_config=True)`) now expects each CFGMGR_* W22;
   the generated-boot checker keeps it and the storm scenario's bound allows it (both found by the first gate run).
   Four FRAM-layout scenarios in `tests/_sensortask_scenarios.py` assumed a boot on an empty config dir logs nothing;
   they now boot on the filesystem an earlier boot wrote (a mechanical premise change, their assertions unchanged).
6. **The uptime timer's re-arm: removed** (8019a9ef). `_status_loop` waits on the tick again; a refused arm is printed
   (not persisted) and the status passes it wakes stop (see Falsification fixes, item 2). Pinning tests that went first: the
   three `test_a_dead_uptime_timer_*` tests and `test_mempause_answers_valid_with_every_timer_arm_failing`. Test:
   `test_start_uptime_timer_degrades_when_it_cannot_be_armed` and the twin timer-pool test, red (b2_up_red, b2_red67),
   green.
7. **`_ESCALATION_ENTRY_WAIT_MS`: removed** (8019a9ef); the entry write is awaited plainly. Decided from the code: the
   reset record is written before the entry write. Test: `test_the_escalation_decides_and_records_the_reset_before_its_entry_write`
   reads `mem_backup(0)[1]` at the write, red on a planted record-after-write (b2_plant_rec), green; the bound's own
   test went first. Twin scenario `an_escalation_entry_that_never_finishes_leaves_code_20_to_the_watchdog` (starved
   feed, the watchdog's reset, the record reads 20) green (b2_twin_esc: 65 passed, 2 skipped by premise, 0 failed).
8. **A chip-setup failure follows the ladder's order** (8019a9ef). `_init_failed()` (a bus-recovery rung run at a setup
   failure) goes: the task ends, the supervisor's restart retries, the restart budget's reboot is above that. Test:
   the four drivers' setup-failure tests (no BUS_RECOVERY after a setup failure) and the twin's
   `test_two_setups_failing_together_are_each_retried_by_the_restart_with_no_bus_rung`, red on the committed sources
   (b2_red8b: bmp3xx 2, isl29125 3, scd30 1, sgp40 2 failed), green. bmp3xx's `_CHIP_WRITE_FAILED` now routes only the
   applied-or-not check.
9. **Cleanups** (8019a9ef): every `setup()` returns None (the wifi/notification overrides too); `set_utc_valid()` only
   sets (tests reset `asy_base_classes._utc_valid`); `_shutdown_task` goes (the run queue holds the created task,
   `extmod/asyncio/core.py:147`, v1.29.0; its RUF006 exemption in `pyproject.toml`); `_read_failing` (every failed read logs, one slot per
   run by the newest-entry rule), `_timer_reported` (`_timer_fault` always persists), `quiet=`. Tests: the setup asserts
   converted mechanically; the per-run tests now pin the logger's rule (counts per read, one slot), red on the committed
   sources, green. Narrowing branches: none in this unit's own code that can never run (the reader trigger loop's
   `period is not None` is the reader trio's, B4's). Whole-millisecond rule: every wait in these files is in a loop;
   nothing changes.
10. **Kept**, existing tests green: E115, the mempause deadline, the recovery ladder, the reset path, the system
    commands, the staged write, the newest-entry rule, the counter caps, the measured uptime.
11. **Other hunks against 25caf528**: see "Item 11" below.

## Knowledge lines (removed items)

- ResetBits/ConfigUnpersisted: `/status` keys reporting the raw watchdog REASON bits and an unflushed-config flag; gone
  on the owner's word (2026-11-02 21:11); code at 82cbf08a (`src/asy_system_service.py`, `buildgen/codegen.py`).
- Reset code 4: the bootloader's own reset record; it never reads back (BOOTSEL loses both regions; the next boot reads
  2); owner, 21:22; code at 82cbf08a.
- Wet-bulb cold-dry corner: a second range gate inside Stull's domain; owner, 21:25; code at 93224dab.
- `rel_humidity()` without clamp, `_MAGNUS_RH_ROUNDING`: agent text; code at 93224dab.
- W69 CONFIG_LOST/`absent_at_boot`/`restored`: a warning for a missing settings file beside surviving FRAM history,
  which raised itself after every scratch build; code at 16047d96.
- The uptime re-arm: a one-second sleep and re-arm each pass after a refused arm, whose trigger (alarm-pool exhaustion)
  is refuted; code at 16047d96.
- `_ESCALATION_ENTRY_WAIT_MS`: a 1,200 ms bound on the escalation's entry write; the record written first makes the
  watchdog's reset read the right reason; code at 16047d96.
- `_init_failed()`: a bus-recovery rung run on a chip-setup failure, ahead of the restart; code at 16047d96.
- Setup bools, `set_utc_valid(valid=)`, `_shutdown_task`, `_read_failing`, `_timer_reported`, `quiet=`: test-only
  product code and per-episode flags; code at 16047d96.

## Proof check (PLAN 0) on the remove items

Items 1-3 are the owner's decisions; no proof of goodness found for them beyond the agent's own text. Item 5: the
scan's row (S2-G4-21) records only a hypothetical condition and a defect it created (OF-184); none found. Item 6: its
trigger is refuted (V6, a pool of 16 for at most 12 timers); none found. Item 7: the closure kept the escalation wait
under the owner's C-stack "ok"; that "ok" is for "Running out of C stack reboots the unit with its own reset reason",
which still holds without the bound (record first, then the watchdog's reset reads it; the twin scenario shows it), so
it is not proof for the bound itself. Item 9's flags: no failure they fix found; the newest-entry rule keeps one slot.
Nothing became a shrink item.

## Gate

**First run (b2_gate, on the first form of the items 5-9 commit): stopped after its unit tier failed** (7 jobs; (b)
defects in my deliverable, all from item 5's restored warning or the lint form): the scenario harness's
`a_bounded_fault_storm_persists_only_what_its_events_allow` on all six devices (its per-logger bound allowed no entry
for a config store's not-found warning: CFGMGR_* 4 writes against a bound of 2); `tests_scripts`'
`test_digital_twin_generated_boot.py` (8: a "normal boot" read W22 as a fault) and `test_stripped_image_boots.py` (same
checker); `test_suppression_form.py` (an inline `noqa` in `src/`); `test_ruff_exemptions_live.py` (the system service's
PLW0603 exemption, dead since item 1 removed `_reset_bits`'s `global`). Fixed in the commit: the storm bound counts one
not-found entry per config store, the boot checker keeps a config store's one W22 (its own test,
`test_a_config_stores_not_found_warning_is_the_one_entry_a_fresh_config_dir_boot_keeps`, red then green), RUF006 moves
to `pyproject.toml` in place of the dead PLW0603 (BACKLOG.md's chroot list gets its line). Checked before the rerun:
the storm scenario on dev, the five host files (724 passed), lint and all three mypy passes clean.

**Second run (b2_gate2, on 57469eee, the commit's second form; 79 min):** unit tier at -1 PASS (137 files passed, 0
failed, 86 skipped by their own device/premise rules, 6 deselected; tests 6,027 passed; `tests_scripts` 7,123 passed, 6 skipped)
and at 32768 PASS (the same counts); dev's twin harness PASS at -1 and at 32768 (65 scenarios passed, 0 failed, 2
skipped by premise: `refused_config_write_is_logged_and_the_next_one_lands`, file modes do not bind under root, and
the full-scheduler-queue reset scenario, run on arzi only); `npm run lint`, `npm run typecheck` PASS, `npm run
test:unit` PASS (1,340 passed). Dev's twin suite: 330 checks passed and 2 failed at each stage, both the same (b):
Run 1's and the reformat relaunch's fresh-boot check wanted CFGMGR_NTP's not-found warning too, but the launcher
writes NTP's file (its offline responder's) before the boot. Fixed in 8019a9ef (`_check_quiet_boot` leaves
CFGMGR_NTP out; its test `test_a_fresh_config_wants_exactly_one_not_found_warning_per_config_store_and_nothing_else`
changed first, red on 2 cases, then 131/131 green).

**Third run (b2_gate3_suite, on 8019a9ef): the twin suite at both stages only**, since 8019a9ef changes nothing
else from 57469eee (the checker and its host test): PASS at -1 and at 32768, 332 checks passed and 0 failed
each (16 more in its second block, all passed); 22 min.

Before the gate: every `tests/test_*.py` at stage e (105 jobs: every per-device file at dev and wozi,
`test_sensortask.py` at all six; b2_all_e) passed after two mechanical fixes (the four FRAM-layout scenarios, the
setter integration's setup asserts); lint (`lint_direct.sh`) and the three mypy passes clean; `tests_hardware
--collect-only` 202/233 collected (31 deselected by the default gates); the changed flash-tier files under `--twin`:
9 passed, 2 failed, both pre-existing (Findings).

## Sizes

`module_sizes.sh` (bytecode with bare names; `S/u35r/r1/B2/sizes/`): `src/` 207,155 B at 93224dab (measured here;
B1's recorded figure is 207,188 B) to **205,832 B at 8019a9ef (-1,323 B)**, 16,514 to 16,408 lines;
against R0's 208,708 B, -2,876 B. No module grows. Per module: system service 11,274 to 10,532 (-742), config
manager 8,440 to 8,258 (-182), base classes 10,840 to 10,665 (-175), math helpers 2,344 to 2,286 (-58), bmp3xx -42,
isl29125 -36, sgp40 -27, scd30 -25, print log -22, wifi -13, notification -1.

`scripts/build_firmware.py dev` at 8019a9ef (b2_fw): image 1,182,332 B of 1,228,800 B, **imageFreeBytes 46,468 B**
(R0: 43,068 B; +3,400 B).

## Decisions (agent, 2026-11-03)

- The bootloader keeps code 9 (command incomplete), its acceptance's code, rather than writing none: a BOOTSEL round
  trip loses it anyway, and a watchdog end before BOOTSEL still reads "command incomplete"; no new branch.
- Item 8's form: the setup-failure rung goes rather than reordering it, since the restart and the budget reboot already
  form the ladder above a failed setup; a test of the order (no bus rung) pins it.
- The FRAM-layout scenarios boot on a written filesystem rather than counting W22 (their subject is the chip).
- One commit for items 5-9: their hunks interleave in the same functions.

## Item 11

Nothing further restored. The pre-audit files differ from today's by about 3,000 changed lines (system service 949,
base classes 910, config manager 795, math helpers 173, API response 134; renames under U10's names included). Named
by group, each with the basis found at the source:

- `asy_system_service.py`: the reset record in backup RAM (`begin_boot`, `write_reset_record`, `record_loop_end`;
  owner 2026-09-26, 2026-10-26) and the system commands with their shutdown sequence, the one-way command flag, the
  ResetErrors refusal and the config flush (owner 2026-09-30, 2026-10-02, 2026-10-13 "2 b"; Erase FRAM and Reset to
  defaults, SPECIFICATION.md A.8) - item 10's reset path and system commands. The supervisor (`start_tasks`,
  `_supervise`, the budget, E115, the C-stack reboot, `LastTaskEnd`; owner 2026-07-18, 2026-09-30) - item 10's E115 and
  ladder. The mempause deadline (decision 3) and the measured uptime (`TickSeconds`) - item 10. `run_setups()` and
  `boot_phase()` (the boot setup list, owner-approved boot-confined placement reset, CLAUDE.md) and `ConfigFaults`
  (owner 2026-10-01). **Named, no basis found in the code:** the stagger timer's failed-arm sleep in `start_timers()`
  (one of the six timer-arm shapes; not on the action list).
- `asy_base_classes.py`: the recovery ladder (`_climb_ladder`, the rungs; owner 2026-09-30) - item 10; the counter caps
  (`COUNTER_CAP`) and `HourlyWindowCounter` (owner 2026-10-01); `PieceBuffer` (owner 2026-10-05); the staged write's
  `_commit_mgr_cfg`/`_writes_closed` (owner 2026-10-02) - item 10; `TickSeconds`, `utc_now()` (Part G.2); the typing
  protocols (type-check only); the error-code constants (the catalog). **Not mine:** the reader trigger trio
  (`_trigger_loop`, `_timer_fault`, `_timer_failed`, `_rearm_timer`) is B4's (its sites are the drivers').
  **Named, no marker found:** `DeviceSession` (Part C.2/G.2), `_republish()`, `_init_done()`'s boot-clear report.
- `asy_config_manager.py`: the staged write (`commit`, `close_writes`, `_flush_staged`, `flush_pending`) - item 10;
  `delete_file()` (Reset to defaults, owner 2026-09-30, 2026-10-01); `compare_before_write()` (owner "ok": "A rejected
  setting costs no flash write"); the write-once (owner 2026-10-01); the accepted float round-trip gap (owner
  2026-08-24). **Named:** the typed getters (A-C7), see Findings.
- `math_helpers.py`: `abs_humidity`'s 237.3 and the supercooled branch (owner 2026-10-07: "Adapt the humidity to the
  verified range"); `cct_mccamy`, `chromaticity_xy`, `ema_step` (moved in from the drivers, Part G.2); the CCT span
  comment (agent, 2026-09-29); `altitude_baro` renamed `pressure_at_height`.
- `asy_api_response.py`: **named, user-visible, no owner word found:** the envelope code catalog lost codes 2, 3, 4,
  5 and 100 and gained 400/404/405/413/500 (SPECIFICATION.md C.5.3 carries no marker); `_ERRNO_UNHANDLED_DISPATCH` (99)
  replaced by the catalog's E14.

## Findings

- Typed getters (A-C7) not converted: a stored value's type follows its schema key, which mypy cannot see (keys are
  strings), so the owner's first half, "fully covered by typing adherence alone" (2026-10-27), does not hold. Lead's call.
- The reader timer trio (S2-G4-7's reader sites) is untouched; it is B4's. Only `_timer_reported` went here (item 9),
  so `_timer_fault()` persists every failure, one slot by the newest-entry rule. The trio's `period is not None`
  (a narrowing that cannot fail) is B4's too.
- The stagger fallback sleep in `start_timers()` (S2-G4-7) remains; not on the action list.
- bmp3xx's three-way `_apply_stored_config()` outcome is now read only as applied or not (the setup and the POR
  re-apply); a bool would do (B4's file; its comment corrected in 2970ff9e).
- SYSTEM's warning band 69-70 is empty after W69 went (no placeholder, as for code 4).
- `tests/machine.py`'s reset-register model (`mem32` at the REASON/CHIP_RESET addresses) has no product reader left;
  the twin loop-end test and the bench test read it. R2's to judge.
- `tests_hardware/manual/manual_persistence.py`'s HAD_POR/RUN-bit checks are listed for R2 (bench work).
- Cross-unit edits made for items 5/8/9 (mechanical): `asy_wifi_service.py`, `asy_notification_service.py`, the four
  drivers and their tests (B4/B5/B7 files), `tests_hardware` readers. The lead merges them.
- `tests_hardware/flash/test_system_commands.py::test_a_reset_mid_erase_leaves_every_chunk_old_or_blank[1000]` and
  `[2000]` fail under `--twin`, the same at 93224dab (b2_base_erase, a throwaway worktree, removed): the twin's 256 KB
  erase ends in about 1,064 ms, so the 2,000 ms cut cannot land inside it, and the 1,000 ms cut did not either.
  (c) other (the cut points fit silicon's erase time, not the twin's); not pursued. The other 9 selected pass.
- `scripts/run_digital_twin_ci.sh --only` does not select scenarios (it ran all 67); (c) other, not pursued.
- `scripts/run_digital_twin_ci.sh` prints `ss: command not found` in this sandbox (port-53 holder listing); (c).

## Falsification fixes (2970ff9e, on 8019a9ef)

The lead's seven fixes from `FALSIFY.md`, one commit; `src/` bytecode 205,832 to 205,834 B (system service +2 B, the
gate's longer refusal text: an admitted fix). Runs: `b2x_*` in `S/u35/lead/`.

1. **Done.** `_request_shutdown()` refuses once a reset is decided (both checks, text "a reset is already decided");
   the escalation's `if self._feed_owned: continue` re-check kept as asked. As I read it, it can no longer fire: the
   in-loop `_feed_owned` check precedes the decision with no await between, so a command accepted before the decision
   breaks the pass first. Tests changed first, seen red (b2x_red1: 3 failed, the hung case reading `[True, 9, 1, False,
   9]`, the falsifier's finding): `test_a_command_during_the_escalations_entry_write_is_refused_and_the_escalation_resets`
   (reboot and erase: refused, record 5, nothing erased, one arm), the stack form `..._is_refused_and_the_record_keeps_20`,
   and the new hung-write case `test_a_command_during_an_entry_write_that_never_ends_leaves_the_escalations_code_to_the_watchdog`
   (refused, record 5, no feed, not armed). Two refusal helpers that call `_reboot()` directly now decide first, as
   both product callers do. Comments at the decision and the re-check, SPECIFICATION.md A.8 (two lines), F.1 and G.2.
2. **Done (comments and docs only).** `pause_permanent_storage()`'s and `start_uptime_timer()`'s comments, and
   SPECIFICATION.md's two lines (the auto-unpause, the refused tick): with the tick refused (refuted in normal operation)
   a pause lasts until the reboot, uptime reads right only while read at least every 2**29 ms. Correction to item 6
   above: a refused tick arm is printed, not persisted (`arm_tick_timer()`).
3. **Done.** Code 9's catalog text and SPECIFICATION.md's row: "a system command that did not complete: its shutdown
   did not finish, its delete, erase or config flush fell short, or the bootloader command never reached BOOTSEL".
   `asy_bmp3xx_driver.py:92` corrected. Correction to item 2 above: the bootloader records 9, not 3.
4. **Done.** The storm bound's extra event only for config stores whose file the boot did not find
   (`_PLANTED_CONFIG_LOGS`: SYSTEM's and NTP's). With the falsifier's plant (one extra persisted CFGMGR_SYSTEM warning in
   `SystemService.setup()`): red (b2x_storm_plant: `{'CFGMGR_SYSTEM': (4, 2)}`); plant restored: green at -1 and 32768
   (b2x_storm_green).
5. **Done.** `_normal_boot_log_failures(body, absent)`: a store whose file the boot wrote owes exactly one W22 with
   count 1, any other module (a planted NTP file's store included) none; `_absent_config_logs()` reads the config dir
   less the runner's NTP file. Tests first, red (b2x_nb_red: 3 failed), then all 29 boots and helpers green
   (b2x_nb_green, both boot files).
6. **Done.** The erase-cut test wants the ring restored whole or blank (every slot empty, count 0). A planted ring
   neither whole nor blank with nothing counted passed the previous check and fails this one (b2x_fram_plant: lax copy
   155/155, strict copy 154/155), the real file 155/155.
7. **Done, in the device-side form.** `board.exec` cannot be used inline here: its Ctrl-C ends main.py (record 21) and
   leaves the armed watchdog unfed, which would change the records the next steps read. So
   `reset_code_invalid_record.py` (STATE boot_phase, run right after the soft reset) reports CHIP_RESET's HAD_POR and
   the REASON bits, and the manual test asserts `[0x100, 0]`: the power-on boot's and the soft reset's registers (a
   console soft reset changes neither). **Still for R2:** the third read (after the boot-phase soft reset) and the
   RUN-pin test's HAD_RUN figure; each would need an exec after which the watchdog resets the board. Checked by
   `--collect-only` (202/233 collected, 31 deselected).

Runs: both GC stages for `test_asy_system_service.py` (192/192), `test_asy_fram_manager.py` (155/155),
`test_asy_webserver_service.py` (227/227) and `test_sensortask.py`@dev (104/104) (b2x_both, b2x_sys3); the storm on dev
at both stages; `tests_scripts` (generated boot, stripped image, error catalog, buildgen definitions and generate,
comment cap, scenarios, ci-suite errcount, suppression form, ruff exemptions, feed sites, citations: 1,836 passed);
`lint_direct.sh` clean; the three mypy passes clean.

