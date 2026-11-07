F4e hand-back, saved by the lead from the message it sent (2026-10-26). Commit c60d1ae2 on audit/u35-f4e (on 1ad9cff7).

F4e hand-back. The work is in commit c60d1ae2 on audit/u35-f4e, on top of 1ad9cff7. It is not pushed and nothing is uncommitted. Logs are in S/u35/laneR/f4e/. Every fact in the brief held on this base.

**Files changed (8):** src/asy_system_service.py, tests/test_asy_system_service.py, tests/test_digital_twin_loop_end.py, tests_hardware/device_scripts/reset_code_invalid_record.py, tests_hardware/manual/manual_persistence.py, SPECIFICATION.md, buildgen/error_catalog.json, tests_hardware/README.md.

## Step 1: the move
- `begin_boot()` now decides in this order: a valid record, then an in-boot phase (10 + p), then PWRON (1), then a torn record (0), else 2.
- The comment above the chain covers both reads in 2 lines and points to F.5.4.
- The change is RAM only and the same on every device. Every mode (STA, AP, Silent, Off, USB) takes the same path, because `begin_boot()` runs once per boot, before construction.
- mpy-cross compare: base 11392 B, head 11391 B. They differ from byte 5790 on, which is `begin_boot()`'s branch order. The line count is unchanged.

**Torn record next to an in-boot phase.** It now reads 10 + p under any cause; before, it read 0, or 1 under power-on. A unit test pins this.
- **Not reachable from a cleared record.** `_write_region()` stores the magic last, and `begin_boot()` clears the magic first. So any cut into a write over a cleared record leaves word 0 at 0, which reads as no record.
- **Only one way in.** It takes a second record write over a valid record, during a boot still below BOOT_DONE:
  - the writes: a system command's 9 and then its own code, or the entry's 21 after either. Tasks and the webserver run from phase 3 and the first NTP sync is phase 5, so a command during phases 4-5 is possible;
  - and a watchdog reset landing exactly between that write's value store and its check store. A power cut clears both regions instead.
- **Verdict:** practically unreachable. If it does happen, 10 + p is still true: that boot did not complete. SPEC F.5.4 says this.

## Proofs (zero memory markers in every log)
**Unit**, in tests/test_asy_system_service.py. Four new tests:
- `test_a_console_soft_reset_after_a_boot_phase_failure_reads_10_plus_the_phase` (:3877), every phase 1-5;
- `test_a_boot_done_marker_under_a_power_on_cause_reads_1` (:3891);
- `test_a_power_cycle_during_boot_reads_1` (:3899), the cleared-regions case;
- `test_a_torn_record_beside_an_in_boot_phase_reads_10_plus_the_phase_under_either_cause` (:3907).

Results:
- **Red on the old order:** red_unit.m1.log, `AssertionError: 1` at :3888 and :3915.
- **Green:** 198/198 at both stages, 24.3 s and 25.4 s (final_unit.*), unchanged from F4d's 24.8 s and 25.8 s.
- **The two guards passed at once, so I bit them in scratch copies:**
  - widening the phase range to `<= BOOT_DONE` turns :3896 red (biteA.m1.log);
  - removing the PWRON branch turns :3904 red (biteB.m1.log).
- No existing test plants an in-boot phase and expects 1. F4d's tests and the order tests stay green.

**Twin:** `test_a_console_soft_reset_after_a_loop_ended_during_boot_reads_10_plus_its_phase`, next to F4d's soft cases.
- **Bite:** F4d's order planted in a scratch copy turns it red with ResetReason 1 and ResetBits 256 (red_twin_f4dorder.m1.log).
- **Green:** arzi 8/8 at both stages; the other five devices 1 passed and 7 skipped at both stages (final_loopend.*).
- **Port band:** 8 cases need 16 of the 20 ports per device, so it fits with 4 to spare.

**Timing (decision for you):** arzi ran base and head back to back: 16.2 → 17.5 s at -1 and 16.6 → 17.9 s at 32768 (final_pair.*). That is +8 % and +1.3 s, under 10 %. But LEAD NOTES 4 says a file already over 10 s at base must not grow. The growth is the one case the brief requires; each case costs two device boots. An option I did not take: merge it with `test_a_loop_ended_during_boot_reads_10_plus_its_phase` by saving the regions after one ended entry. That saves about half the case.

## Step 2: the sweep (verdict per site)
- **bench/test_reset_reasons.py:** unaffected. Every flow ends in a watchdog reset, either the script's `machine.reset()` or a starvation, before ResetReason is read (:138, :176, :213, :223). The new order only matters under a power-on cause.
- **The 15 device scripts that call `begin_boot()` or build the system:**
  - Those that build the system clear region 1 at the end (for example heap_layout_after_full_boot_sequence.py:175-178).
  - Those that do not clear it end in a reset with cause WDT.
  - A script whose boot reads 10 + p under power-on (one script leaves the marker, a raw-REPL soft reset follows, the next script calls `begin_boot()`) is not an issue: no script prints or asserts its `begin_boot()` value.
  - Unaffected.
- **Harness flows:**
  - mpremote's raw-REPL soft reset runs no main.py (main.c:246), so `begin_boot()` runs there only when a script calls it.
  - `hard_reset()` is `machine.reset()`, cause WDT.
  - `run_isolated` then `soft-reset` is a raw soft reset.
  - The only friendly-REPL Ctrl-D is the manual test. Unaffected.
- **Twin:**
  - run_generic_integration.py:1170-1173 flushes the mem_backup state only on SimulatedRebootError, with cause WDT. SIGINT (:1164) and power loss (:1177) do not flush, so the next launch is a power-on with empty regions.
  - run_device_script.py never flushes.
  - Only the test's own `_case(..., "soft")` keeps PWRON with the regions. Unaffected.
- **scripts/_digital_twin_ci_suite.py Run 12:** :935 is a fresh boot after `_archive_state`, and :945 is a SIGINT relaunch with no state file. Both are empty regions and read 1. Unaffected.
- **Website and tests_js:** labels come from the catalog. tests_js uses only fixture codes (`ResetReason: 1`, `3`). The 11-15 texts change.
- **The twin README's mem_backup row** (:238) does not state the order, so it is unchanged.

## Step 3: docs
- **SPEC F.5.4:** the order, the phase marker under a power-on cause, the `BOOT_DONE` case, the torn-plus-phase consequence and its reachability, and the decision tag exactly as given (both owner decisions, quoted, with paraphrased questions).
- **SPEC A.7:** a Ctrl-D before the watchdog fires reads the same 22 or 10 + phase.
- **A.8 table and catalog, codes 11-15:** now "boot failure in phase p (name), the watchdog reset or a console soft reset followed". This changes what the website text means.
- **tests_hardware/README.md:** the 11-15 row names the manual step.

## Hardware step (prepared, never run)
**Placement:** a third step in `manual_persistence.py::test_console_soft_reset_keeps_the_reset_record`, not a sibling. It needs a power-on cause with no watchdog reset since, which only the operator's cut gives. Reusing this test's cut and evidence dump avoids a second cut.
- The new STATE `boot_phase` in reset_code_invalid_record.py calls the product's `begin_boot()`, records the facts (its return value, region 0, region 1), feeds, prints DONE and returns. There is no new script and no FRAM manager.
- The Ctrl-C/Ctrl-D block is now the helper `_console_soft_reset()`, used by steps 2 and 3.

**Step 3's sequence, checked against the pinned source:**
1. `run_isolated(..., soft_reset_after=False, STATE="boot_phase")`. mpremote's first command enters the raw REPL with a soft reset (mpremote main.py:536, :548-553; transport_serial.py:178-212; docs/reference/mpremote.rst:552-555). Its Ctrl-C makes the entry write 21. The raw soft reset skips main.py (main.c:246) and keeps both regions.
2. The script's `begin_boot()` must return 21, leave region 0 at [0, 0, 0, 0] and region 1 at phase 1. The host asserts all three.
3. When mpremote disconnects it sends Ctrl-B (commands.py:82-83, transport_serial.py:214-216), so the board is in the friendly REPL.
4. The helper sends Ctrl-C (a fresh prompt, pyexec.c:672-675), then Ctrl-D (pyexec.c:676-681), then reads "soft reboot". main.py runs again (main.c:246-249).
5. The boot that follows must read 11 with HAD_POR and no TIMER or FORCE bit.

**Watchdog window:** it runs from the script's last feed. If it were overrun, the watchdog's reset would set TIMER, so the test fails loudly.

**Wear:** no flash write and no flash cycle. `run` executes from RAM, and the control keys are console bytes.

**Checks:** `--collect-only` gives 200/231 (31 deselected). `python tests_hardware/manual --list` shows the new description.

## Checks
- ruff clean on all changed files.
- All six mypy invocations green (cold cache, typings symlink, now removed).
- test_generated_boot_entry 5/5 at both stages.
- 54 tests_scripts readers (readers1.log): 3534 passed.
  - 2 failed, both test_twin_record and expected: the pre-existing missing entry for reset_code_loop_end.py, and stale hashes that now include reset_code_invalid_record.py (sha256 and api_sha256). It needs a re-record.
  - 1 error: test_device_script_fram_regions, a stale generated tree after my catalog edit. Green after the rebuild (readers2.log, 471 passed with error_catalog, buildgen_definitions and generate_sensortask_modules).
  - Comment cap, citations, error catalog, decision vocabulary, tunables, port bands and code conventions all passed.
- Not run (toolchain hazard): test_digital_twin_ci_suite_errcount, test_stripped_image_boots, test_digital_twin_generated_boot, test_digital_twin_scenarios, test_build_firmware, test_setup_toolchain_env, test_digital_twin_boot_contiguity.

## Surprise: two hardware-test defects found by the sweep, outside my brief, not changed
`board.exec()` runs mpremote's auto soft reset first (sources above). That soft reset re-runs `mp_init` (ports/rp2/main.c), which empties sys.modules. So two hardware tests that look up the running product's `sysfunct` there find no `sensortask_` module:
- `manual_persistence.py:37/:210` (`_READ_REASON`, in `test_power_loss_during_the_shutdown_commands`) prints "REASON None", and the :216 assert fails on silicon.
- `flash/test_system_commands.py:28-37/:66` (`_READ_AFTER_BOOT`) prints "AFTER null", and :70 fails. That is the flash tier, another lane's file.

A likely fix is `mpremote ... resume exec ...` (docs mpremote.rst:127-136), so no soft reset runs first. These are your call to route.

nothing of mine is running
