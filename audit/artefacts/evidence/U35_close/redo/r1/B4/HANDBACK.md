B4 hand-back, written by the agent (Tue Nov  3 10:30:04 UTC 2026)

Branch `audit/r1-b4` in `S/wt-b4`, from `3129bf21`. Six commits:

- `dddb3902` the I2C and SPI wrappers back to their pre-audit no-bus forms, one bus clear (items 1, 2, 3, 4-I2C, 21-bus)
- `b4341646` BMP3XX and SCD30 back to their pre-audit read paths (items 4, 5, 6, 7, 8, 21, 22)
- `1206e862` SGP40 and its VOC port back to their pre-audit forms (items 4, 11-17, 21, 22)
- `80b513b5` ISL29125 and the reader timer arms back to their pre-audit forms (items 4, 9, 10, 18, 19, 21, 22; `get_register_into()` goes)
- `57771f12` the twin harnesses expect a fresh FRAM's first-boot SGP40 W65 (item 13's consequence, from the gate)
- `963d0de1` the remaining pins of removed forms go or follow them (items 9, 11, 12, 19, 21, from the gate)

Red runs: `S/b4work/red.sh REV TEST SRC...` runs a changed test file against REV's version of the named `src/` files
(logs `S/u35/lead/b4_red_*.log`). A void-return change (setter, transfer, `setup()`, `deinit()` to `None`) cannot be
asserted at run time under strict mypy (`func-returns-value`): it is pinned by mypy and by the pre-audit "no-op, must
not raise" test form.

## Per item

1. **I2C/SPI "no bus" contract — removed.** Getters answer `None`, setters/transfers/`setup()`/`deinit()` answer
   nothing, SPI `configure()` raises `RuntimeError("SPI bus not initialized - call init() first")` again, `recover()` =
   clear + `init(*stored)` with no catch (`_REC_NO_CONTROLLER` gone); the 26 driver raises go, a read that gets `None`
   raises its pre-audit message (BMP3XX `failed to read N bytes from register`, ISL29125 `failed to read register`,
   `failed to read the config registers back after reset`). `_probe_for_device()`'s `RuntimeError` and `SPI.available`
   (B3's) stay. Tests: I2C `test_operations_after_deinit_return_none_or_noop`, `..._already_deinitialized_bus_return_none_or_noop`,
   the mid-session deinit test and the malformed-format/type-mismatch tests back to the pre-audit form — red on the old
   driver (4 fails, `b4_red_i2c`); SPI's pre-audit tests back (`configure` raises on a deinit'ed bus, none/no-op) — red
   (5 fails, `b4_red_spi`); BMP3XX's three pre-audit no-bus tests back — red (2 fails, `b4_red_bmp1`). Gone first: I2C
   `test_every_completed_transfer_and_write_returns_true`, `test_recover_reports_a_controller_that_will_not_construct_and_leaves_no_bus`;
   SPI `test_every_completed_transfer_returns_true`, `test_aenter_on_a_deinitialized_bus_holds_the_lock_and_every_transfer_is_false`,
   `test_session_begin_returns_false_on_a_deinitialized_bus`; SCD30 four (`test_a_command_write_the_bus_refuses_raises_oserror`,
   `test_a_deinitialised_bus_fails_the_read_without_checking_a_stale_buffer`, `test_a_register_read_the_session_refuses_raises_before_the_crc_check`,
   `test_contmeas_false_with_the_bus_down_after_the_snapshot_comes_back_failed`); SGP40 three; ISL29125 two; the fake's
   `I2C.raise_on_construct` knob and its guard test. The EIO tests stay green. Four `tests_hardware/device_scripts`
   adapted mechanically to the void returns (mypy).
2. **I2C clear — shrunk to one routine.** `_clear_bus(scl, sda, timeout, *, awaited)` and `_scl_released(..., awaited)`:
   the runtime rungs await each SCL wait (F.3 kept), the constructor drives the same coroutine with one `send(None)`
   (it never suspends with `awaited=False`). −1 routine, −1 wait helper. Boot-clear and rung tests green unchanged;
   `tests_scripts/test_src_sleep_forms.py` lost its `_clear_bus_awaiting` waiver (seen green after; its red is by
   construction: the waiver named a function the old code had); `test_ticks_rollover.py` adapted mechanically.
3. **Short-ACK path — shrunk.** `_write_all()` (a short count is EIO after the STOP a no-stop write owes, no catch
   around that STOP) plus `_reg()` (the register address as `fill_memaddr_buf()` sends it); the setters send
   `_reg(...) + payload` in one `writeto()`; `_fill_reg_addr()`/`_write_buffer()` and the setter fills go. `_point_at()`
   (I2C-7) stays. Tests 1222/1257/1278/1292 green; 1235 (a refused STOP) gone with its catch; 1336 mechanical.
4. **Allocation reductions — removed.** I2C `_scratch_view`, whole-buffer fast paths, `get_register_into()` (+ its
   `I2CDevice` forwarder, last caller gone in `80b513b5`); BMP3XX `_pt_burst`; ISL29125 `_rgb_burst`/`_config_burst`;
   SCD30 `_words`; SGP40 `_backup_buf` and `_read_word()` (`_exchange()` folded into `_read_words()`). Gone first: I2C
   `test_the_scratch_view_is_one_object_for_the_bus_life`, `test_a_full_buffer_transfer_hands_the_fake_the_callers_object`
   and the three `get_register_into` tests; BMP3XX `:670`; ISL29125 two buffer pins; SCD30 the word-buffer pin; SGP40
   `:2099` and the in-place word test. **SGP-14's pending restore kept**: with the block removed,
   `test_a_failed_backup_buffer_leaves_the_restore_pending` fails (the restore reads as "no backup" and the next backup
   would overwrite it; probe `b4_probe_sgp14`) — but the failure is planted, see findings. **Construction-time
   `VOCAlgorithm()` kept** (judged by `test_digital_twin_boot_contiguity.py`, green with it; not probed lazily).
   I2C `:1139` (I2C-7's no-mem-call sequence) and `:1168` (the pre-audit scratch copy) kept: not pins of this item.
5. **BMP3XX power-on detector, W71 — removed.** `_apply_stored_config()` answers a bool. Gone first: the reset's EVENT
   read, both `take_por_detected` tests, both chip-reset re-apply tests, the reset-between-sessions no-bus test. The
   mock hazard catalog and `test_bus_hazard_multi_device.py` drop the EVENT read; `test_digital_twin_hot_replug.py`'s
   power-cycle test now pins "reads on at the chip defaults, nothing logged, no task ends"; the bench scripts read
   EVENT themselves (`take_por()` in `_shared/bus_reader_loops.py`; `--collect-only` 202/233).
6. **BMP3XX conversion wait and ERR_REG burst — changed back** to forced mode, the STATUS poll, the 6-byte burst from
   0x04; `fatal_err` goes. Gone first: the 8-byte burst, fatal-err, computed-wait and reserved-OSR-before-trigger
   tests. Changed: `:724` (every sleep a poll step) and `:757/:773` (`_BadBurstRead` now patches the PRESSUREDATA read)
   — red on the old driver (`b4_red_bmp2`, 6 fails with item 7/21's). `:542, :605` green. The split-session hazard
   test seeds before its not-ready STATUS so the poll yields (mechanical).
7. **E27 at the BMP3XX — removed.** `:1931` expects READ, red then green. E27 stays at the SCD30.
8. **W73 — removed.** SCD30 `:2155` and the twin's stuck-RDY warning test gone; `:749, :2129` green.
9. **ISL29125 shadow compare — changed back** to `_verify_after_failed_write()`. New
   `test_a_clean_cycle_reads_no_config_snapshot` red on the old driver (`b4_red_isl`), green after. Reconcile tests
   green (method name and the pre-audit silent failure adapted); `test_a_corrupted_config_byte_is_found_on_a_cycle_without_a_failed_write` gone.
   The pre-audit bare `except Exception: return` failed `test_fatal_report_sites.py`; it now starts with
   `report_if_fatal(e)`, silent as before (`test_a_reconciling_re_read_that_itself_fails_...` pins `printed == []`).
10. **W75 — changed back** to the console line. `test_a_calibration_window_ends_with_its_console_line_alone` red then
    green; the twin autorange test expects no entry; the bench Calibrate test waits the window out and asserts an
    empty log (`_calibration_end()` and `l4.sensor_config_push_calibration_poll_s` go, the margin stays).
11. **SGP40 sample-age check — removed**; the raw-reading raise becomes `# type: ignore[arg-type]` at `_voc_state()`.
    Gone first: `:817`, `:841`. `:2949, :3524, :3533` green. From the gate: the twin integration file read
    `_COMP_MAX_AGE_S` at import (all six devices crashed); its stale bound is the notification's alone, and
    `test_a_stopped_scd30_ends_its_alerts` (was `..._and_sgp40_compensation`) loses its stale-measure half.
12. **Restart restores — changed back.** `:2348`, `:2369` changed (a restart restores, VOCState 3), red then green;
    `:2390` green. From the gate: the twin `test_a_restarted_sgp40_task_keeps_its_live_voc_state` becomes
    `..._restores_its_voc_state_from_fram` (it read `(1, 0)`, a restore, where it pinned `(4, None)`).
13. **W65 for every invalid read — restored.** `:2411` (first boot: one W65) and the CRC-invalid backup test (both
    layers log) red then green; the twin two-setups test expects the W65 on the fresh FRAM. From the gate (`57771f12`):
    every fresh twin now logs it at its SGP40's first cycle, so the scenario harness waits it out before a shared
    boot's first count snapshot (the idle-check reds on all six devices), the fault storm's SGP40 bound counts its one
    entry (30 > 28 on all six), the ResetErrors-not-undone scenario allows this boot's own one W65 (E-entry check
    kept); the CI suite's Run 1 boots wait for it and expect it (`_blank_backups()`; new L0
    `test_a_blank_backup_chunk_owes_its_sgp40_no_backup_warning_once_waited_for`, red `b4_red_ci` then green; Run 1
    passed before by a race, the W65 landing after its read at 5.6 s); the twin NTP restore test reads boot 1's W65
    back with the restored log, `(1, [65])`.
14. **Restore-while-waiting — removed** (`_restore_waiting`, the callback's E14, W33 for an unknown age, `_ntp_synced`,
    `_ERR_CALLBACK`). Chunk read each cycle (red), the two unknown-age tests silent (red), the raising-callback test
    gone. `:3276` green.
15. **VOC constants — changed back** to per-sample `_f16()`: `voc_algorithm.py` now equals the pre-audit text except
    VOC-1, VOC-2, VOC-4, the docstring and the owner-quoted pack comment. Gone first: the 35-constants pin and the
    no-per-sample-conversion pin (the trajectory helper lost its counter). Sensirion vectors green.
16. **VOC-3 — removed**; `"32q"` again. `:380, :396` gone; `:431, :776`, the round trip green.
17. **"settled"** in the catalog and the `@web` description; the vocabulary check passes for it via one prose line in
    the tag block, `# VOCState 2's word is the owner's (owner, 2026-10-02: "2 settled").` (no allow-list growth).
18. **Reader timer trio — changed back** to the pre-audit catch per arm in all four drivers; `_timer_error`,
    `_rearm_timer()`, `_timer_failed()`, `_timer_fault()` and the base `_ERR_TIMER` go; `_trigger_loop()` keeps the
    divider, its never-None narrowing as `# type: ignore[operator]`. E17 stays (Wi-Fi, NTP, system). Gone first:
    BMP3XX `:2325`, SCD30 `:1055/:1062` (+ helper), SGP40 `:987/:1015/:1036`, ISL29125 `:3077`, five base tests and
    their helpers, two twin timer-pool tests (+ five helpers). The "degrades gracefully" tests stay green without
    their wake asserts.
19. **ISL-2, ISL-8, ISL-12 — removed.** W32 and `_int_held`'s reset stay; `_measured_ratio()` and
    `_measure_gain_ratio()`'s window check are the pre-audit forms. Gone first: `:1949`, `:4269`, `:1163`, `:1183`,
    `:3933`, the two failing-reads/week tests, the week-old switch-tick test, the twin's muted-interrupt test; the W32
    test (`:1927`) green with its re-arm asserts dropped; `:841` green. From the gate (`963d0de1`), gone: the sensortask
    scenario `isl29125_calibration_ticks_end_on_their_deadlines_across_wraps_and_five_day_stalls` (called
    `_expire_calibration()`) and `test_an_isl29125_interrupt_rearm_mid_read_leaves_every_sibling_read_valid` (the re-arm's
    CONFIG burst); the reapply-rung hazard test stays green.
20. **Chip-config unavailable marker — kept.** BMP3XX `:1465`, ISL29125 `:2270` green.
21. **Per-unit cleanups — done.** `setup()`/`deinit()` to `None` (I2CDevice, SPIDevice, I2C, SPI, BMP3XX, SCD30,
    SGP40, ISL29125); never-running narrowings as `# type: ignore[...]` (SCD30 `[misc]`, ISL29125 `[arg-type]`, base
    `[operator]`, SGP40 `[arg-type]`); `_comp_unreadable` gone (`:1685` one entry per failed read, red then green);
    SCD30's `_frc_cfg_ok` guard gone (test changed to one entry per refused read, red then green);
    `_RESET_SETTLE_MS` 2 and the heater-off 1 ms (red then green). From the gate: `tests_scripts/test_readiness_gates.py`
    exempts `I2C.deinit()`/`SPI.deinit()` as rp2 no-ops (`_NO_OPS`, as C.13 already says), its pending-list example is
    `UART.deinit()`; `tests/test_readiness_gates.py` calls `SPIDevice.setup()` plainly; ISL29125 `set_resolution()`'s
    narrowing reason moved beside its ignore (`test_suppression_form.py`).
22. **Shared files.** `error_catalog.json`: W71, W73, W75 gone, E27 stays, VOCState 2 "settled"; `codegen.py`,
    `definitions.py` untouched.
23. **Kept items** untouched; the mock and twin bus-hazard tiers green, flash/bench `--collect-only`.
24. **Other hunks against the pre-audit text**, named: `get_register_bytes()` kept (C.md "not counted") and now used
    for the BMP3XX/ISL29125 bursts in place of `get_register_struct(.., "6s"/"3s")`; `_MAX_ADDRSIZE` kept; SPI
    `configure()` keeps U10's lock message; ISL29125 `_decode_rgb_burst()`'s `unpack_from` left (not on the list).

Docs: SPECIFICATION.md C.3, C.13's teardown line, D.4, A.4 (SCD30 not-ready, SGP40, BMP3XX recovery), G.2 (stale
sample, trigger divider), the Part I memory paragraphs (I2C, BMP3XX, SGP40, VOC, ISL29125), the ISL29125 cycle order,
restart table and calibration line, the BMP3XX wait table, C.9's arm paragraph, Part N rows (`bmp3xx.reset_settle_ms`
2, `scd30.not_ready_warn_at`, `sgp40.comp_max_age_s`, `l1.asy_base_classes_trigger_loop_bound_s`,
`l4.sensor_config_push_calibration_poll_s` gone, the margin row reworded). From the gate: the twin harnesses' shared-boot paragraph
(SPECIFICATION.md, `digital_twin/README.md`) and README's Run 1 entry name the first-boot W65.

## Knowledge lines (removed items; code at `3129bf21` unless named)

- I2C/SPI no-bus bool contract and 26 driver raises: a no-bus state reachable only through `recover()`'s
  `_REC_NO_CONTROLLER`, which rp2's re-construction with once-valid arguments cannot produce; removed in `dddb3902`.
- `_clear_bus_awaiting()`/`_scl_released_sync()`: a line-for-line copy of the boot clear; one routine replaces both (`dddb3902`).
- `_fill_reg_addr()`, `_write_buffer()`, the setters' scratch fills, the STOP's catch: ~35 lines where ~13 close SF-A01 (`dddb3902`).
- I2C scratch view, whole-buffer paths, `get_register_into()`; BMP3XX `_pt_burst`; ISL29125 `_rgb_burst`/`_config_burst`;
  SCD30 `_words`; SGP40 `_backup_buf`, `_read_word()`: transient-allocation reductions with no observed MemoryError
  (OR110); removed in `dddb3902`, `b4341646`, `1206e862`, `80b513b5`.
- BMP3XX POR detector + W71 and the ERR_REG `fatal_err` burst: after a POR the chip runs at its defaults and forced mode
  is written every cycle, readings stay valid; 0 resets seen on the bench; `b4341646`.
- BMP3XX computed conversion wait: the pre-audit STATUS poll worked (BMP-3); `b4341646`.
- BMP3XX E27, `_comp_unreadable`, the 3 ms settle: E11 as before, the logger's slot rule, Bosch's 2 ms; `b4341646`.
- SCD30 W73 and `_not_ready_reads`; `_frc_cfg_ok`'s guard: hypothetical stuck RDY; per-episode flags under OR35.b; `b4341646`.
- SGP40 `_COMP_MAX_AGE_S`/`_current_value()`, the raw-reading raise, the restart's kept state, W65 only for unreadable,
  `_restore_waiting` + E14 + W33-unknown-age: hardcoded delay check; unreachable; pre-audit restart restore; owner's
  "blast radius" word; FRAM reads are free here; `1206e862`.
- VOC-5 (35 hoisted constants) and VOC-3 (int32 check, uptime clamp, `"<32q"`): OR109; served only the audit's own
  backups; `1206e862`.
- ISL29125 every-cycle CONFIG snapshot, W75, ISL-2 re-arm, ISL-8 tick bounds, ISL-12 restart resets: CONFIG changes
  only by reset/brownout; console line as before; unobserved; 6.2 days on the high range; one filter step; `80b513b5`.
- Reader timer trio (`_timer_error`, `_rearm_timer()`, `_timer_failed()`, `_timer_fault()`): pool exhaustion refuted
  (≤ 12 Timers, pool 16); the owner calls a boot-time shortage a malformed firmware; `80b513b5`.

## Gate

Run in the background through `run.sh` (logs `S/u35/lead/b4_gate.log`, `b4_gate2.log`, `b4_gate3.log`; scripts in
`S/u35r/r1/B4/tools/`). First pass at `80b513b5` (`gate.sh`): rebuild, lint, the three mypy passes rc 0; unit-1 red
(18 files, 9 L0 tests; above). I stopped it at unit-32768's start, fixed (`57771f12`, `963d0de1`), reran each fixed
MicroPython file at both GC stages (`b4_fix1`, `b4_fix2`, `b4work/t.sh`) and the failing L0 files, then the rest at
`963d0de1`:

| step | result |
|---|---|
| rebuild, lint (ruff, shellcheck, actionlint, zizmor), mypy main/host/twin | rc 0 (`gate2`) |
| scenarios at GC -1, six devices | 0 failed: dev 64, arzi 62, the other four 61 passed (dev in `gate2`, the five others in `gate3`: `gate2`'s parallel launch lost them to the port-53 lock, a launch error of mine, no scenario ran) |
| unit tier at GC 32768 (`scripts/test.sh`) | all 131 MicroPython file runs N/N passed, 0 failed, no memory marker; all six scenario jobs 0 failed; pytest tier 7125 passed, 1 failed: the base-known decision-vocabulary test, its six B2 sentences only. The wrapper hit its 30-min background limit during test.sh's closing archive step, so its summary block never printed; every per-file line did |
| dev twin suite, GC -1 / 32768 | rc 0 / rc 0 (Run 1's boots log the blank chunk's W65, expected) |
| dev twin harness, GC -1 / 32768 | 65 passed, 0 failed each |
| npm lint, typecheck, test:unit | rc 0; 26 files, 1340 tests passed |

Unit tier at GC -1 in full was not rerun after the fixes: its non-scenario reds were the fixed files, rerun at both
stages, and the unchanged files passed at -1 in the first run and at 32768 after. `tests_hardware`: `--collect-only`
202/233 at `80b513b5`; no `tests_hardware` file changed after.

## Sizes (lines / bytecode B; `S/u35r/r1/B4/sizes/`)

| module | pre-audit | R0 | start `3129bf21` | head `963d0de1` |
|---|---|---|---|---|
| asy_base_classes.py | 414 / 5561 | 850 / 10858 | 824 / 10652 | 794 / 10310 |
| asy_bmp3xx_driver.py | 646 / 9938 | 725 / 11020 | 712 / 10876 | 653 / 10015 |
| asy_i2c_driver.py | 368 / 2869 | 555 / 4846 | 555 / 4846 | 468 / 4117 |
| asy_isl29125_driver.py | 1448 / 17788 | 1562 / 19202 | 1539 / 18994 | 1499 / 18505 |
| asy_scd30_driver.py | 630 / 9214 | 923 / 12888 | 905 / 12717 | 874 / 12405 |
| asy_sgp40_driver.py | 690 / 8444 | 825 / 10514 | 819 / 10424 | 754 / 9606 |
| asy_spi_driver.py | 213 / 1954 | 224 / 2020 | 224 / 2020 | 215 / 2073 |
| voc_algorithm.py | 797 / 7652 | 852 / 8708 | 852 / 8708 | 809 / 7790 |

`src/` +317 −681 lines over the unit; tests (`tests/`, `tests_scripts/`, `tests_hardware/`) +290 −2006. One module grows: **asy_spi_driver.py +53 B**, the restored
pre-audit `configure()` `RuntimeError` text (item 1's own form), admitted. Firmware (`dev`, `963d0de1`): 1,177,444 B image, **51,356 B free** (R0 43,068 B; B2 46,468 B).

## Decisions taken (agent, 2026-11-03)

- One clear routine with an `awaited` flag, the boot clear driven by one `send(None)`: keeps F.3's awaited runtime
  waits with one body (the alternative, a synchronous runtime clear, blocks the loop up to the bus timeout per wait).
- `_MAX_ADDRSIZE` kept: the pre-audit addrsize `ValueError` (machine.I2C's) needs a bound, and ruff's PLR2004 a name.
- `reg_addr.to_bytes()` raises `OverflowError` for an address wider than `addrsize` where `fill_memaddr_buf()`
  truncated; no caller passes one.
- The BMP3XX/ISL29125 bursts read through `get_register_bytes()`, not the pre-audit `get_register_struct("6s"/"3s")`:
  no union to narrow at the caller.
- "Typing-side form" taken as `# type: ignore[code]` at the use: `src/` has no `cast` shim, and one costs ~5 lines.
- SGP-14's pending restore and the construction-time `VOCAlgorithm()` kept (item 4).
- I2C `:1139/:1168` kept; the twin hot-replug test kept, inverted to the defaults behaviour; the bench scripts read
  EVENT through one shared `take_por()`; the uart-link load script sets the SGP40 up outside its setups dict.
- Spec lines outside the action list's set edited where they described a removed mechanism (listed under Docs).
- A fresh twin's restored W65 is waited for, never tolerated: the scenario harness's first shared-boot snapshot and
  the CI suite's Run 1 reads wait for it (bounded 30 s / 45 s) and Run 1 expects it exactly; tolerating it when
  present would be the tolerance list `_check_quiet_boot()` rules out.
- ISL29125's reconcile re-read keeps its pre-audit silence through `report_if_fatal(e)`, not the base's console line.
- The readiness check exempts the I2C/SPI `deinit()` no-ops by name (`_NO_OPS`, beside `_MIRRORS`) and keeps its
  teardown rule for every other class.

## Findings for the lead

- Base-known: `tests_scripts/test_decision_vocabulary.py` fails only on the six B2 sentences at `3129bf21`
  (SPECIFICATION.md 1201, 7878; `src/asy_system_service.py:378`; `tests/test_asy_system_service.py:1393, 2103, 3727`),
  fixed on the integration branch in `942ca477`; untouched here. B4's own hit (an ISL29125 "can never be") reworded.
- The gate's first unit-1 run found 18 red files and 9 red L0 tests, all B4's but the vocabulary one: pins of removed forms my
  per-file runs had not reached. Fixed in `57771f12`/`963d0de1`, each fixed file rerun at both GC stages.
- SGP-14's pending restore: its test plants the allocation failure (`buf._buf = None`); no observed failure. Kept on
  the probe; the lead's call whether that is proof enough.
- Twin knobs with no driver reader left: `digital_twin/_bmp3xx_chip.py`'s `fatal_err` and EVENT model,
  `_scd30_chip.py`'s `rdy_stuck_high` (each keeps its own twin guard test) — R2's.
- Bench tests that expect an empty SGP40 log after a boot can now meet the restored W65 on a blank or invalid chunk
  (bench round).
- FRAM `E19` (`LOCK_TIMEOUT`) moved twice in the first unit-1 scenario runs (schlafzi, arzi; overflow-burst
  scenarios, beside the then-unwaited W65's FRAM write); in neither rerun at either GC stage. Not pursued.
- `I2C.writeto()`'s and the setters' short-count EIO: a short no-stop write's STOP that itself raises now surfaces
  that `OSError` (not the EIO) — both are `OSError`, every caller treats them alike.

## Fix round

Written by the agent (Tue Nov  3 11:26:15 UTC 2026). Brief: `B4/FIX_BRIEF.md`. One commit on `audit/r1-b4` in `S/wt-b4`:
`b8ed30e5` (from `963d0de1`; 13 files, +31 -55). Runs: `S/u35/lead/b4x_*.log`; probes and their inputs:
`S/u35r/r1/B4/xtmp/`; the two-stage runner `S/u35r/r1/B4/b4x_two_stages.sh` (full output, RC and a
MemoryError/"memory allocation failed" count per file and stage).

- **F1 flash sweep follows the removed EVENT read - done.** `Seen.por_after_setup` and `device_reader()`'s
  `take_por()` after a BMP3XX `setup()` go (`_shared/bus_reader_loops.py`), the sweep's `por_after_setup` fact
  goes, and so does its assertion (`flash/test_bus_concurrency.py:258`). `take_por()` stays for
  `bmp3xx_alone_survives_a_general_call.py`. The falsifier's `b4f_flash_twin` command: red in this worktree before
  the change (`b4x_flash_twin_red`, `por_after_setup={'bmp3xx': True}` at `:258`), green after
  (`b4x_flash_twin_green`, again on the commit `b4x_flash_twin_final`). The other two flash tests reading through
  `Seen`/`device_reader()` under `--twin` (`b4x_flash_twin_seen`): the chip-setup test passes; the held-SDA test
  fails, identically at `963d0de1` (`b4x_flash_held_base`) - see findings. Flash+bench `--collect-only`: 202/233.
- **F2 bench erase tests admit exactly the SGP40 W65 - done.** Both
  (`bench/test_system_commands_over_rest.py:173-175`, `bench/test_bus_concurrency_under_api_load.py:424-426`) now
  keep a FRAM-backed log unless its (counter, used slots) is (0, []) or, for an SGP40 logger
  (`_load.instance_loggers("sgp40")`), (1, [W SGP_NO_BACKUP]). Red then green by probe (`b4x_probe_erase`,
  `xtmp/probes/probe_erase_kept.py`, evaluating each file's own two lines on synthetic tables): at `963d0de1` an
  SGP40 W65 alone is kept (red); now it passes, while W65 counted twice, another W, W65 plus another, or a W65 on a
  non-SGP40 logger are kept. `--collect-only` for both files: 10/14 collected (4 gate-deselected), both erase tests
  among them (`b4x_bench_collect`).
- **F3 VOC uptime cap 32767 - done.** `voc_algorithm.py` back to `const(32767)` without its comment; SPECIFICATION.md's
  "one deliberate deviation" sentence goes. `test_voc_algorithm.py`'s
  `test_both_estimator_uptimes_stop_at_the_uptime_limit` follows to `32767 - 1`: red on 16383 (`b4x_voc_red`,
  42/43), green after at both stages, no memory marker (`b4x_voc_green2`). Pins removed first (they assert the cap stays
  a small int): `tests_scripts/test_counter_steps.py`'s `voc_uptime_limit()`, `test_the_voc_uptime_counters_stay_small_ints`,
  `test_a_planted_voc_uptime_limit_above_the_range_fails`; the file then 8/8 (`b4x_counter_steps`). Probe
  (`b4x_probe_voc`): the falsifier's `probe_voc.py` unchanged and an every-sample copy, both 20,000 samples of the four
  sequences, `25caf528`'s port (`voc_pre.py`, checked byte-identical to `25caf528:src/voc_algorithm.py`) against the new
  one: no output and no packed-state mismatch on any sample, codecs repack identically both ways. A 36,000-sample
  every-sample run (`b4x_probe_voc_cap`) reaches the cap (uptime_gamma 2147352576 = F16(32766) on both): equal throughout.
- **F4 ResetErrors scenario admits only the W65 - done.** `_reset_errors_not_undone`: (counter, newest slots) must be
  (0, []) or (1, [[W, 65]]) (`_newest_entries()`, the file's existing slot reader); the separate E filter goes.
- **F5 shared boot fails without its W65 - done.** `SharedBoot.acquire()` `_expect`s the wait's answer, naming the
  missing warning; a raise there leaves the boot on the stack, which `release(failed=True)` closes. Digital-twin README
  and the deadline comment say "waits for" it.
  F4 and F5 seen red then green on one planted break (`_run_restore()` logging the blank chunk as W34, reverted with
  `git checkout`, rebuilt each way): `b4x_scen_planted` (`--only` the ResetErrors scenario and the shared
  `negative_content_length_is_refused`, dev, GC -1): both FAILED with the new messages; the same plant under
  `963d0de1`'s harness (`b4x_scen_planted_base`): both PASSED - the gap. Unplanted (`b4x_scen_green`): both PASSED
  at GC -1 and 32768.
- **F6 docs follow - done.** SPECIFICATION.md's SCD30 memory entry now: the 18-byte buffer only; per read, three
  two-slice joins into a 4-byte `bytes` each with one `struct.unpack()` tuple, the derived points, the sample.
  `asy_isl29125_driver.py:745`'s "next snapshot refills raw" comment goes (decode order kept: with a fresh copy it no
  longer matters), and the matching test's comment (`test_asy_isl29125_driver.py:2173`) says the snapshot is a fresh copy.
  ISL29125 file 237/237 at both stages, no memory marker (`b4x_isl_twostage`).

End checks: `lint_direct.sh` rc 0 (`b4x_lint`); mypy main 276, host 314, twin 59 files, no issues
(`b4x_typecheck`; typings link removed); `test_comment_block_cap`, `test_digital_twin_scenarios`,
`test_device_script_bench_facts`, `test_counter_steps` 787 passed (`b4x_pytests2`); `test_memory_catalog`,
`test_citations`, `test_tunables_register` pass; `test_decision_vocabulary` fails on the six base-known B2 sentences only
(`b4x_pytests`), none of this round's. Sizes (`xtmp/sizes_b8ed30e5.tsv` against `ftmp/head.tsv`): `voc_algorithm.py`
7,790 B and `asy_isl29125_driver.py` 18,505 B, both unchanged; every module equal, so no firmware rebuild.

Knowledge lines (each removed item's code is in `963d0de1`):
- the sweep's `por_after_setup` fact and assertion: pinned `reset()`'s EVENT read, which row 5 removed.
- the VOC 16383 cap and its comment, and `test_counter_steps.py`'s VOC small-int pins: kept both uptime counters small
  ints; 32767 is the C reference's, legacy's and `25caf528`'s value, and past ~4.5 h of samples each uptime step
  allocates a transient long int, which the owner's VOC ruling of 2026-09-29 settles (lead, FALSIFY_VERIFIED).

Decisions (agent, 2026-11-03):
- F5 is shown by a planted twin run rather than a new unit test: the harness check is the test, and the plant shows
  both the gap and the fix without new code.
- F6 keeps the ISL29125 decode-then-check order and drops only the comment (one line, equal bytecode).
- F2 counts the counter too ((1, [W65]), not just the slot): a W65 logged twice after an erase is a second restore,
  not the one the erase owes.

Findings:
- (c) `flash/test_bus_concurrency.py::test_a_held_sda_line_is_cleared_and_every_device_answers` fails under `--twin`
  at `:270` (`held: False`), at `963d0de1` too, before any `device_reader()` call: the twin's open-drain `Pin.value()`
  reads the planted line level (`digital_twin/machine.py:314-325`); no chip model answers a bit-banged read by driving
  SDA, so the hold this silicon test makes cannot be made on the twin. Not pursued.
- (c, fixed by F2's form) `bench/test_system_commands_over_rest.py`'s erase test (since `0c0ad52c`) kept every
  FRAM-backed logger on a blank table: `counts[name]["history"]` is the fixed-length slot list, "N" slots included
  (`asy_webserver_service.py:1073-1082`), so it was always truthy (probe: all 20 dev loggers kept on "blank").
