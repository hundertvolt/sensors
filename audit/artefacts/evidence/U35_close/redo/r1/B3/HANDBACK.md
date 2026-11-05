B3 hand-back, written by the agent (Tue Nov  3 17:13:11 UTC 2026)

Worktree `S/wt-b3`, branch `audit/r1-b3`, from 90691b6d. Commits: eac7cd4c (every row), 08113e9c (a leaner
`check_from()`, superseded), cc5daeb7 (the gate's findings: A-K2 kept, the vocabulary rule, Run 3). Nothing pushed.
Run logs: `S/u35/lead/b3_*.log`; the gate (on 08113e9c): `S/u35/lead/b3_gate.log` (the first gate run, killed by the
container restart at 14:05, is `b3_gate_killed_1405.log`); the quiet re-run on cc5daeb7: `b3_quiet.log`. Line numbers
are the action list's (90691b6d tree). Red/green runs: b3_red1 (unit files on the unchanged source), b3_red2/b3_red3
(twin FRAM file), b3_red4 (the clock alone), b3_green1-4 and b3_crc2 (both GC stages, 0 memory markers in every file).

## Items

1. **Lost-FRAM chain, driver half: removed** (eac7cd4c). `_SR_FIXED_ZERO`, `_PROBE_AT` and `@tunable
   fram.chip_probe_at` (its Part N row), `_SV_CHIP_LOST`, E54, `_anomalies`, `lost`, `_check_write_anomaly()`,
   `_report_chip_lost()`, `is_ready()`, setup's resets and the header words go; `set_values_sync()` returns
   `self._write(...)`, `set_write_protected()` the plain status; `verify_present()` is the pre-audit entry (bounded
   wait, E19, `initialized = False` on a mismatch) without A-D9's unreachable ID-error branch. Pinning tests went
   first: FD `test_a_chip_gone_silent_mid_run_is_probed_once_and_marked_lost`,
   `test_the_first_write_to_a_chip_whose_so_reads_high_reports_the_loss_not_a_success`,
   `test_set_write_protected_on_a_chip_whose_so_reads_high_reports_the_loss`,
   `test_an_anomaly_with_a_matching_id_keeps_the_chip_up`, `test_a_clean_write_between_two_anomalies_resets_the_count`,
   `test_setup_after_a_loss_clears_it_and_the_chip_works_again`,
   `test_verify_present_on_a_dead_chip_persists_chip_lost_once`
   and helpers `_assert_lost_and_quiet`, `_read_then_write`; mechanical: FD `_setup_fram` (no answer), `:642` (two
   stuck-latch writes, no probe expectation), `:963`, `:995`, `:1009` drop their `lost`/E54 asserts;
   `test_readiness_gates.py` drops `is_ready`; `tests_hardware` `flash/test_bus_concurrency.py` (E54 constant and the
   `chip_lost` asserts) and `device_scripts/fram_cs_hijack_fault_injection_and_recovery.py` (scenario 4,
   `_CHIP_LOST_AT`, `_LOST_AFTER_WRITES`, `hold_inactive()`), collected in the gate. WREN-retry neighbours green.
2. **Lost-FRAM chain, manager half: removed** (eac7cd4c). `_blank_verdict()`, the four `lost` guards and the watch's
   re-setup go; `:244` reads `return None if fault or fault1 else False`; the watch keeps its escalation and parks with
   `await asyncio.Event().wait()`. Went first: FM `test_every_chunk_operation_stays_silent_while_the_chip_is_lost`,
   `test_a_blank_read_of_a_silent_chip_finds_the_loss_and_reads_none`,
   `test_every_blank_read_probes_once_so_a_chip_that_stops_answering_is_found_at_the_next`,
   `test_a_probe_that_cannot_take_the_lock_keeps_the_blank_verdict`,
   `test_an_erase_asked_while_a_found_chip_loss_is_still_being_reported_is_refused`; `test_fram_integration.py`
   `test_after_a_chip_loss_ten_logger_writes_add_no_fram_log_entry_beyond_the_loss`; twin
   `test_a_blank_read_of_a_silent_twin_chip_finds_the_loss_and_reads_none`,
   `test_every_chunk_operation_stays_silent_on_the_twin_while_the_chip_is_lost` and helper `_lose`. Changed first,
   red: the wire golden without `w:9f r:047f0302` and count 56→55, docstring (b3_red4: "CS cycle 4 changed - recorded
   'w:9f r:047f0302'"); twin `:946` now
   `test_a_booted_device_whose_fram_goes_silent_fails_its_writes_and_resumes_when_the_chip_answers` (two silent logger
   writes refused with W FRAM_WEL_NOT_SET, the first write after the chip answers lands, the watch task the first one,
   no reset armed; red b3_red3 "the first logger write after the chip answered did not land"). FM `:3584` keeps its
   healthy half (`test_the_watch_task_waits_while_healthy`); mechanical: twin `:1033` (no `lost` assert),
   `test_asy_print_log.py:675` (`test_a_reset_whose_write_the_chip_refuses_clears_ram_and_answers_false`, the write
   failed by the fake's `drop_wren`), `test_digital_twin_hot_replug.py:3` repointed in its words; FM `:3615` green.
   All green (b3_green1, b3_green3).
   **Two mechanical consequences in the twin suite's Run 3 (cc5daeb7, the lead's forms, 2026-11-03),** both found by
   the gate, both resting on the removed blank-read probe: (a) Run 3 waited for an "E" entry from every faulted
   instance; with its link silent, `UART_resp` logs nothing of its own, and its only E on the base tree was the
   LOG_RAM_ONLY entry every FRAM-backed logger persisted once the probe made its setup read "unreadable". Now each
   logger's setup reads blank, its one write fails, it prints `PrintLog: FRAM setup failed!` and records no entry
   (`run3_sustained_bus_fault_matrix.log`: no `UART_resp` line after `UART link ready as responder`), so the host
   polled until the device's escalation reset (~5 s) and the next poll was refused (gate: ConnectionRefusedError and
   IncompleteRead at GC -1, IncompleteRead at 32768, plain and CRC16-derived runs). Run 3 now leaves the link's
   responders, read by role from the TOML model (`_link_responders()`, as `_link_crc_modes()` reads `crc`), out of the
   wait and its check. (b) The write-attempt ceiling (window / 627 ms x 2) counted the 20 boot setup writes (one per
   FRAM-backed logger, 40 WRENs, 0 data phases), which the probe used to cut off after the first (B5's gate: 0-1
   attempts): 20/22 passed at GC -1 (6,910 ms), 20/18 failed at 32768 (6,173 ms). The ceiling now adds one write per
   `PrintLog: FRAM setup failed!` line of the run's own log (none printed counts 0, failing safe); the data-phase check
   is unchanged. `digital_twin/README.md`'s Run 3 entry says both.
3. **`erase_ready()`: shrunk** to `self.initialized and not await self.fram.get_write_protected()`. FM `:3483` drops
   its `lost` case; `test_readiness_gates.py:251` green.
4. **Preflight catch and re-check: removed** (`asy_system_service.py`, only those lines). Went first:
   `test_a_raising_preflight_leaves_the_gate_as_a_refusal_does`,
   `test_an_escalation_armed_during_the_erase_preflight_refuses_the_command`, and the latter's now-unused
   `_ARM_SETTLE_MS` with `@tunable l1.system_service_arm_settle_ms` and its Part N row. `:1421`, `:2452` green (187/187
   both stages).
5. **E19 in B4's scenarios: no own change.** Twin `:955` changed first, now
   `test_a_blank_read_beside_a_held_session_stays_blank_makes_no_rdid_and_logs_nothing` (the sibling session starts
   right after the chunk's second block read and holds 1,200 ms; RDIDs counted at the chip): red b3_red2 ("logged
   [..., 19]", one E19), green after row 2.
6. **SPI "no bus" consumers and `SPI.available`: removed.** Changed first: FD `:1201` back to
   `test_bus_deinit_mid_operation_raises_uncaught_runtimeerror` (red b3_red1: returned instead of raising), `:1249`
   expects the `RuntimeError` (red b3_red1: `OSError: SPI bus not initialized`), FM `:1891` expects E UNEXPECTED, E
   FRAM_BLOCK_WRITE and E FRAM_CLEAR, no E52 (red b3_red1); `:1218`, `:1234` and helper `_bus_down_entries` went. Green.
7. **FRAM SPI clock: changed** to `SPIDevice(spi_bus, spi_cs, baudrate=8_000_000)  # 24 MHz (rp2's ceiling) / 3,
   exact (owner, 2026-11-02)`; `_ERASE_UNIT`'s comment "0.3 ms at 8 MHz". Datasheets read (main checkout): MB85RS64V
   fCK 20 MHz, MB85RS2MTA 40 MHz at 2.7-3.6 V. `_INIT_EVENT` "init 8000000/0/0/8/1" first: red b3_red1 (all nine
   wire tests at event 0), green after. `test_asy_spi_driver.py` green (64/64). Twin `_ERASE_US_PER_BYTE` stays 8 µs,
   its comment and Part N row reworded as a deliberately 8x-slow bus.
8. **Read copy `_copy_out()`: removed**, `bytearray(dbuf)` again. Went first: FM
   `test_a_failed_read_copy_returns_the_sentinel_on_both_chunk_classes`.
9. **Check buffer: restored.** No check buffer reads as invalid block 1: `_compare_with()` answers
   `(False, False, False, False)`, `_read()` warns W63 and rewrites; `_no_check_logged`, its ALLOC entry and the
   block-1 guard go; the construction catch with its `err()` line stays, comment back to the pre-audit text. FM `:726`
   changed first, now `test_an_unallocatable_check_length_reads_block_1_as_invalid_and_rewrites_it_each_read` (3
   rewrites, one W63 slot counted 3; verified writes one E FRAM_VERIFY each): red b3_red1, green. `:1200`, `:1240`,
   `:1961`, `:1986`, `:3001` green.
10. **ALLOC on a missing buffer: removed** (six entries and `_ERR_ALLOC`), the sentinels stay. Went first: FM
    `test_a_missing_chunk_buffer_logs_alloc`.
11. **Partly protected status register: restored** `self._wp = (self._read_status() & _SR_WP_MASK) == _SR_WP_SET`;
    `_SR_BP_MASK`, E53 and `wp_bits` go. Went first: FD
    `test_a_partly_protected_status_register_is_reported_and_writes_refused`;
    `tests_scripts/test_fault_or_warning_never_both.py`'s FRAM setup pair. FD `:380`, `:705` green.
12. **`setup()`/`set_write_protected()` lock: restored** to the bus lock alone (`async with self._bus_lock:`). Went
    first: FD `test_set_write_protected_and_setup_wait_for_a_held_driver_lock`; `:907` green.
13. **Per-unit cleanups.** `FRAM_SPI.setup()` and `FRAMManager.setup()` answer `None` (lead's decision); the four
    pre-audit guards stay without their "Unreachable" comments; `_VERIFY_PRESENT_LOCK_TIMEOUT_MS` as landed. Every
    reader of a FRAM setup answer reads `initialized` instead: `tests/test_asy_fram_driver.py` (`_setup_fram`),
    `test_asy_fram_manager.py` (`_setup_manager`, `:2723`, the device-ID setup test, the idempotent-setup test, the two
    watch tests), `test_asy_fram_wire_trace.py:519`, `test_asy_fram_allocation_budget.py:44`,
    `test_asy_ntp_client.py:592, :598`, `test_asy_sgp40_driver.py:2505, :2855`, `test_asy_webserver_service.py:1078`,
    `test_bus_hazard_multi_device.py:577, :621, :826`, `test_digital_twin_fram.py:211`,
    `test_digital_twin_fram_crash_points.py:70`, `test_digital_twin_generic_wiring.py:191`,
    `test_fram_integration.py:118`,
    `test_readiness_gates.py:267`; device scripts `bus_deinit_is_a_noop_on_real_hardware.py`,
    `fram_busy_status_lockout.py`, `fram_command_hold_timing.py`, `fram_error_log_reset_during_boot_window.py`,
    `fram_error_log_reset_race_seed_and_race.py`, `fram_error_log_reset_race_verify.py`, `fram_error_log_roundtrip.py`
    (2), `fram_manager_roundtrip.py:37, :40`, `fram_pause_unpause_and_gating.py`, `fram_write_protect_roundtrip.py`,
    `sgp40_fram_backup_restore.py` (2). **B6's files, on the lead's word, only these lines:**
    `tests/test_asy_uart_comm.py:538` and `:546`, and
    `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:256` (the FRAM setup moved after the
    two UART setups' dict, order kept).
14. **CRC: A-K3 restored, A-K2 kept.** A-K3: the width fields from the width again, as `25caf528`/U10 (`__init__` and
    `length()`'s comment); went first: `_assert_pure_pass_through` and the three
    `test_a_polynomial_above_the_*_mask_is_pure_pass_through`; `:394`, `:401` back to their pre-audit asserts.
    **A-K2 kept (lead, 2026-11-03): a delimited UART read passes `check_from()` a decoded size of 0 from the wire.**
    eac7cd4c had restored pass mode's early answer in `add_into()`/`check_from()`; the gate's unit tier then failed
    B6's `tests/test_asy_uart_driver.py::test_a_delimited_frame_that_decodes_to_nothing_is_a_failed_read` at both GC
    stages (an encoded empty COBS frame read as 0 bytes, not a failed read; it passes at 90691b6d): a reproduction
    against the real code of a failure the wire can supply, so A-K2 is proven good. cc5daeb7 puts both methods' bounds
    back exactly as landed (`git diff 90691b6d` shows only A-K3) and brings back
    `test_pass_mode_add_into_and_check_from_refuse_bad_bounds`; `_crc_wide()`, `_WORD_BYTES` and the removed catches
    keep. 08113e9c's leaner `check_from()` is superseded.
15. **Erase unit buffer catch: kept.** `test_asy_system_service.py:1652`, FM `:3502` green.
16. **Shared files.** Catalog rows 52, 53, 54 go, no placeholder; E19, E20, W29, E49/W63 stay; no status-emitter or
    `definitions.py` change. `test_error_catalog.py`, `test_buildgen_definitions.py`, `test_tunables_register.py`
    green (b3_host1); web tier in the gate.
17. **Kept** as listed; existing tests green; bus-hazard tiers: mock `test_bus_hazard_multi_device.py` and twin
    `test_digital_twin_bus_hazard_concurrency.py` green at both stages, the two hardware tiers collected.
18. **Other hunks.** Restored to U10's text: the driver's header comment, the `_wp_pin` and `_is_write_protected()`
    notes, the `report_get_values()` "WP8" comment, the manager's `_clear_chunk` note (pointer kept at Part F.1, which
    corrects "CLAUDE.md"). Kept as correcting a fact: FD:41-43, FD:229-231, FD:344-345, the scratch-buffer comment
    (now: the bus lock, which every path takes), the manager docstring (pointer to A.4/A.7, not CLAUDE.md),
    `SPI.configure()`'s caller comment. Kept as landed because a rule of the tree needs them, which I learned by
    restoring them first: two reflows (the comment cap counts a line over 120 characters as several: the driver's
    `_send_*()` comment, the CRC zero-padding comment; `test_comment_block_cap.py`, b3_host1) and four rewordings
    (`test_decision_vocabulary.py` refuses "decided"/"deliberate" without an actor: the `_SV` comment, two "WP8"
    comments, the torn-copies comment; the gate, fixed in cc5daeb7). `review_hunks.py 90691b6d cc5daeb7` over `src`
    and `buildgen` leaves 28 hunks for the lead's read (`S/u35r/r1/B3/review_hunks.out`).
19. **R0 item 5's other two reverts: restored** (`a4f0ccea`: `_unpause_at = None` before the unpause in both sites;
    `8cf55c6b`: the flag after the boot-signature line). Their forced-raise tests went first:
    `test_an_auto_unpause_that_raises_keeps_its_deadline_for_the_restarted_loop`,
    `test_an_immediate_unpause_that_raises_keeps_the_pending_deadline`,
    `test_a_raising_signature_line_never_lets_the_restarted_loop_draw_a_second_signature` and helpers
    `_raising_unpause`, `_ended`; the system-service file green.

## Knowledge lines (removed items; code at 90691b6d unless named)

- Lost-chip chain (driver): a write-latch anomaly count with one RDID probe after two in a row, or at once on a status
  byte with bit 0 set, the `lost` Event, `is_ready()`, E54 FRAM_CHIP_LOST; went because with the chip absent SO floats
  (owner, 2026-10-28), so detection rested on a hypothesis (decision 3); from 2977c4e0, `is_ready()` d4c51d7b.
- Lost-chip chain (manager): `_blank_verdict()`'s RDID probe after a blank read, the chunk operations' `lost` guards,
  the watch task's re-setup on a loss; same reason; 656fc82f, 2977c4e0.
- `erase_ready()`'s `is_ready()`/`lost` terms and the preflight's catch and re-check: no window left once the chain
  went, and the preflight cannot raise (R0); ad1fae73, f76385a6.
- `SPI.available`, E52 FRAM_BUS_DOWN and the driver's five bus checks: no runtime `deinit()` caller; cbb65df2.
- E53 FRAM_WP_PARTIAL and `_SR_BP_MASK`: H implausible (the firmware writes protection all-or-nothing); 2977c4e0.
- Driver lock around `setup()`/`set_write_protected()`: H (every scratch-buffer body runs synchronously under the bus
  lock; setups run one at a time); 2977c4e0.
- `_copy_out()` read-copy catch: H, one 268 B copy per boot; 7ceb50b2.
- Check-buffer ALLOC entry and the block-1 guard: H, an 8-byte allocation at construction; 06a8ae5d.
- Missing-buffer ALLOC entries: H; one entry per fault per level (owner, 2026-11-03); 65a0df3b.
- CRC width fields from the checked polynomial: H, no caller constructs a CRC with an out-of-range polynomial;
  656fc82f.
- The two status-loop order changes and their tests: each guarded call raises only a MemoryError at call entry (R0);
  a4f0ccea, 8cf55c6b.

Docs (eac7cd4c): SPECIFICATION.md A.4 (the knowledge line on a chip lost after boot, the erase gate, 8 MHz), the
`erasefram` refusal line, C.3 (the dropped bus's RuntimeError; "never raise on a live bus"; the caller rule's locks;
the A-D4 line, with the WPEN/WP fact the removed `_wp_pin` comment carried), C.8 (the setups' bus lock), C.13 (the
failed-write list; `FRAMManager` answers nothing; `FRAM_SPI`'s gate cleared by `verify_present()`), F.1 (the longest
static await chain is now 25 levels, budget 28), F (hot replug: FRAM's writes resume), F.5.8 (the figures were measured
at 1 MHz; ~40 µs wire time at 8 MHz; the bench's 1 KB figures), the memory catalog's two FRAM entries, Part N (the
probe row and the settle row go, the erase row reworded); `tests_hardware/README.md:968-969`;
`manual/manual_bus_electrical.py` (its description and countdown text). cc5daeb7: `digital_twin/README.md`'s Run 3
entry (the responder exception, the setup-write allowance); Part N's twin erase row without the decision word.

## Gate

The gate (`S/u35r/r1/B3/tools/gate.sh`, B5's steps) ran once on 08113e9c, 14:07-15:52, the UART unit's gate beside it:
lint 0, the three mypy passes 0, twin harness at -1 and 32768 0 (65 passed, 2 skipped each), hardware collection 0
(202/233 collected, 31 deselected), npm lint 0, npm typecheck 0, npm test:unit 0 (1,340 passed). Failed:
- Unit tier at -1: 5,876 passed, 1 failed (`test_asy_uart_driver.py`'s empty frame, b: mine, row 14); tests_scripts
  7,110 passed, 1 failed (`test_decision_vocabulary.py`, b: mine, row 18). Both fixed in cc5daeb7.
- Unit tier at 32768: the same two, plus `scenarios[arzi|dev|grkizi|klkizi]` `loop_lag_under_combined_load` (lag
  past 50 ms after the load, or past 500,000 us), `scenarios[klkizi]` `failed_config_snapshot_is_sent_as_unavailable`,
  `test_asy_udp_socket.py` `test_recvfrom_respects_timeout_against_a_realistically_delayed_genuine_reply`: all passed
  at -1 on the same tree, with the UART gate running beside (15-min load 5.38 on 4 cores); the lead's reading: host
  load from two gates at once, pending the quiet re-run below.
- Twin suite at -1 and 32768: Run 3, plain and CRC16-derived (b: mine, row 2's two Run 3 consequences, fixed in
  cc5daeb7); every other check passed (324 of 326 at 32768, 325 of 326 at -1).

Quiet re-run on cc5daeb7 (`S/u35r/r1/B3/tools/quiet.sh`, b3_quiet, 16:43-17:10, the host idle, the lead's list),
every step rc=0:
- `test_asy_crc_checks.py` 76/76, `test_asy_uart_driver.py` 174/174, `test_asy_fram_driver.py` 94/94,
  `test_asy_udp_socket.py` 62/62, each at -1 and 32768, 0 memory markers.
- At 32768 alone: `loop_lag_under_combined_load` passed on arzi (30.7 s), dev (36.1 s), grkizi (30.7 s) and klkizi
  (30.8 s); klkizi's `failed_config_snapshot_is_sent_as_unavailable` passed. With the UART re-run also green alone,
  the gate's 32768 timing failures came from two gates at once (c), as the lead read them.
- tests_scripts: `test_decision_vocabulary.py`, `test_code_conventions.py`, `test_comment_block_cap.py`,
  `test_digital_twin_ci_suite_errcount.py`, `test_digital_twin_ci_suite_matrix.py`: 838 passed.
- Lint 0; mypy main (276 files), host (314), twin (59): no issues.
- Dev twin suite at -1: 331/331 checks, the CRC16-derived Run 3 15/15; at 32768: 331/331 and 15/15. Run 3's attempt
  checks: 20 within 36 (-1, 6,001 ms; 18 setup lines) and 20 within 36 (32768, 6,169 ms); CRC16-derived 20 within 24
  at both (7,729 and 7,664 ms; 0 setup lines, see Findings).

## Sizes

`src/` at cc5daeb7 against the base 90691b6d (`S/u35r/r0/module_sizes.sh`): 15,819 → 15,683 lines, 198,243 →
196,591 B (−1,652). Per module (lines, bytecode B): `asy_fram_driver.py` 510/5,554 → 437/4,669;
`asy_fram_manager.py` 827/11,638 → 776/10,950; `asy_crc_checks.py` 186/1,879 → 185/1,876; `asy_spi_driver.py`
215/2,073 → 210/2,028; `asy_system_service.py` 759/10,513 → 753/10,482. Against R0's `now.tsv`:
208,708 → 196,591 B.
No module grows.
Pre-audit (25caf528): 161,626 B. Free flash on dev (`scripts/build_firmware.py dev` at cc5daeb7,
`build/firmware-dev.json`):
**imageFreeBytes 56,684 B** (image 1,172,116 B of 1,228,800 B; R0: 43,068 B, +13,616 B).

## Decisions taken (agent, 2026-11-03)

- `check_from()` (08113e9c, superseded by cc5daeb7): the restored pre-audit text grew the module by 13 B; a one-
  condition form was 1,872 B. Moot once A-K2 stayed.
- Twin `:946`: two silent writes so it is red against the old chain; 2,000 yields for the supervisor's polls.
- Twin `:955`: the sibling session starts from a wrapper on the chunk's block read, RDIDs counted at the chip's
  `write()`; `test_asy_print_log.py:675` fails the write with `drop_wren` (not `silent`).
- `_ARM_SETTLE_MS`, its tag and Part N row went with their only test (row 4).
- The FRAM clock's comment: "24 MHz (rp2's ceiling) / 3, exact (owner, 2026-11-02)".
- C.13 names `FRAMManager` among the setups that answer nothing.

## Findings

- (c) The first both-stage run's twin bus-hazard file failed with "build/generated_src/ is missing or stale": I had
  edited `src/` comments while it ran; rebuilt and green (b3_green4). Once more, at 14:30, I edited `src/` comments
  for about 30 s during the gate's 32768 unit stage and put the committed text back at once; that stage logged no
  stale-tree error.
- For the lead, Run 3's new allowance: it counts `PrintLog: FRAM setup failed!` lines, which print only with a
  logger's console on. The plain Run 3 (DebugLevel 5 from Run 1's state) prints 18 for its 20 setup writes; the
  CRC16-derived Run 3 boots fresh with the console off and prints none, so its allowance is 0 and it passes on its
  window alone (24 >= 20 at 7.7 s; it would fail below 6,270 ms). As the lead set it: no fallback, failing safe.
- The UART unit's `test_asy_uart_driver.py` empty-frame test pins A-K2 through the UART driver; with A-K2 kept, the
  CRC's own `test_pass_mode_add_into_and_check_from_refuse_bad_bounds` is back beside it.
- For R2: Part N `mem.max_await_depth`'s basis still names the lost-chip chain (now 25 levels, a verify-pass status
  read); `tests/_fram_chip_fake.py`'s `silent` knob keeps one reader (the fake's own test in
  `test_asy_system_service.py`).
- Owed to the bench: F.5.8's per-command times and `test_asy_fram_wire_trace.py`'s endurance check use the 1 MHz
  figures; at 8 MHz the wire share drops by about 70 µs per write command, which leaves the bound near 140 years
  (estimated, against 144), still over the 100-year floor.
- `tests_hardware/README.md:1360` and `:1609` left as they are: the pull-to-first-entry measurement and
  `verify_present()` in the CS-hijack recovery both still hold.
- Merge with B6: `tests/test_readiness_gates.py`, `tests_scripts/test_fault_or_warning_never_both.py`, SPECIFICATION.md
  C.13, the catalog, and the three B6-file lines in item 13.
