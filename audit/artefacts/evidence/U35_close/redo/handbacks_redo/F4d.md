F4d hand-back, saved by the lead from the message it sent (2026-10-26). Commit 5f63546e on audit/u35-f4d (on 2a46984a).

F4d hand-back. The work is in commit 5f63546e on audit/u35-f4d, on top of 2a46984a. It is not pushed and nothing is left uncommitted. Logs are in S/u35/laneR/f4d/.

**Files changed:** src/asy_system_service.py, tests/test_asy_system_service.py, tests/test_digital_twin_loop_end.py, tests/_port_bands.py, tests_hardware/manual/manual_persistence.py, buildgen/codegen.py (comment only), buildgen/error_catalog.json, SPECIFICATION.md, tests_hardware/README.md, digital_twin/README.md.

**Step 1 (applied): the swap.** `begin_boot()` now decides in this order:
1. a valid region-0 record (its code)
2. PWRON (1)
3. a torn record (0)
4. a boot phase (10 + p)
5. else 2

The comment is 2 lines and points to F.5.4. Two things worth knowing:
- `code: int = record[1]` is annotated. Without it, mypy's main pass reported "Returning Any", because the first assignment is now the memoryview item.
- mpy-cross compare: base and head are both 11392 B and differ from byte 5177 (the branch order). That is expected for a behaviour change. The line table moves by 2 lines.

**Proofs, each seen red first, both GC stages, zero memory markers**
- **Unit**, `test_a_console_soft_reset_after_a_power_on_boot_reads_the_recorded_code` (21 and 22). It replaces the old-order test.
  - Red on the old code at :3853 (`AssertionError: 21`); red_unit.m1.log.
  - Green 194/194 at both stages, 24.8 s and 25.8 s (unchanged); green2_unit.*.
  - The two guards passed at once, so I bit them in scratch copies. Torn checked after the record and before PWRON: `test_a_torn_record_under_a_power_on_cause_reads_1` goes red at :3870. PWRON branch removed: `test_a_power_cycle_after_a_record_reads_1` goes red at :3862, plus the torn test and the existing power-cycle flags test (biteA/biteB.m1.log).
- **Twin**, test_digital_twin_loop_end.py, three first-device cases:
  - soft reset after Ctrl-C reads 21;
  - soft reset after a loop-core failure reads 22;
  - power cycle reads 1.
  - Each also checks that ResetBits has HAD_POR and no TIMER or FORCE bit.
  - Bite: the old order planted on arzi turns both soft-reset cases red with ResetReason 1 and ResetBits 256; the power-cycle case stays green (bite_twin_oldorder.m1.log).
  - Green: arzi 7/7; the other five devices 1 passed and 6 skipped; both stages (green2_twin_*).
  - Time: arzi went from about 9 s to 16.3/16.7 s. That is the three added cases at about 2.4 s each, the same cost as the existing ones. The other devices are unchanged at 2.7-3.7 s.
- **Your edit to review:** 7 cases need 14 ports on arzi, and the band gave 10. I widened `test_digital_twin_loop_end` in tests/_port_bands.py from 19600-19659 to 19600-19719 (20 per device; the next band starts at 20000). test_port_bands is green. Revert it if you count this as raising a bound.

**Step 2: the sweep, site by site**
- **src/:** no `machine.soft_reset()` and no `sys.exit()`, as expected.
- **scripts/_digital_twin_ci_suite.py:935/945, Run 12:** unaffected. A SIGINT relaunch writes no state file (run_generic_integration.py:1164 never flushes mem_backup), so it is a power-on with empty regions and still reads 1.
- **tests_hardware:**
  - The `_served_after_power` power-cut asserts and the resetconfig cut (manual_persistence.py:79, :204) rely on the silicon fact. Under the new order they also prove it.
  - test_reset_reasons and reset_code_loop_end.py are unaffected. The script's own boot now reads 21 after a power-on, but nothing asserts it, and every raw-REPL flow ends in a watchdog reset with cause WDT.
  - The RUN-pin manual test (:237) could never read 3 under the old order (PWRON came first). Its "3 means it survives" reading is only meaningful now.
- **Website and tests_js:** code 1's text is still true. The texts for 21 and 22 changed in the catalog and the A.8 table to "the watchdog reset or a console soft reset followed". That is a meaning change for the website text.
- **Twin README:** the mem_backup row gains the soft-reset model. The README's "boot read a power-on" at :533 is unaffected.

**Step 3: docs**
- **SPEC F.5.4:** the decode order, why a valid record under a power-on cause means a soft reset, the decision tag as given, and citations to RP2040 datasheet §4.7.4 and §2.13.1 (re-read in S/ds/rp2040.txt :41001 and :12224-12240) plus the machine.rst note.
- **SPEC A.7 and A.8:** updated where they state what 21 means.
- **tests_hardware/README.md:** the Ctrl-C bullet and the rows for codes 1 and 21.

**The SPEC:6933 sentence: what is left of its reason (your call; the entry is unchanged)**
- The old reason, that a power-on boot drops the record, is gone: after the swap a soft reset keeps the 22.
- Facts that still hold:
  - A re-raised SystemExit returns PYEXEC_FORCED_EXIT (pyexec.c:166-185; EXIT_CODE_HANDLING is 0, mpconfig.h:1218).
  - main.c:247-249 then goes to soft_reset_exit (main.c:265-305). That releases network, DMA, PIO, PWM, pins, UARTs and soft timers, but no I2C or SPI controller.
  - main.py then re-runs at once, with no chip reset and no TIMER bit.
  - Not re-raising ends every loop in the watchdog's reset.
- SPEC now states exactly these facts. The generated entry's comment said "a power-on losing the record", which is now false. I changed only the comment: it is still 3 lines and the generated behaviour is unchanged.
- Whether "no chip reset" is reason enough to keep not re-raising is for you or the owner.

**Hardware step (prepared, never run): `manual_persistence::test_console_soft_reset_keeps_the_reset_record`**
It appears in `python tests_hardware/manual --list`; the pytest collect-only gives 200/231. Steps:
1. **Evidence first:** errcount and the FRAM raw dump, then `hard_reset`. This is the FRAM-log rule, as in power_loss_during_the_shutdown_commands.
2. **Silicon fact:** `run_isolated_expect_reset` runs reset_code_invalid_record.py with STATE valid_record_wait. That script is reused unchanged and builds no FRAM manager. mpremote's Ctrl-C records 21; the raw-REPL soft reset does not run main.py (main.c:246); the script writes record 3 and feeds the static WDT (machine_wdt.c:47-61). The operator cuts power. The next boot must read 1 with HAD_POR and no watchdog bit.
3. **The change:** pyserial sends Ctrl-C and waits up to 3 s for `>>> ` (new tunable `l4.manual_persistence_repl_prompt_s`, with its SPEC N row). It then sends Ctrl-D and waits for "soft reboot" (pyexec.c:676-681, main.c:246-262). The next boot must read 21 with HAD_POR and no TIMER or FORCE bit.
4. **Wear:** no flash write and no flash cycle. `mpremote run` executes from RAM (commands.py:508-515), Ctrl-C and Ctrl-D are console bytes, and the record lives in RAM.
5. **Boots:** the step adds three ordinary production boots (the evidence reset, the power-on, the soft reset). Whatever a boot itself sends the SCD30 is the product's per-boot behaviour, which this step does not change.

**Checks**
- Green: ruff on my files; all six mypy invocations (cold cache, typings symlink, now removed).
- Green: comment cap, test_citations, test_error_catalog, tunables, decision vocabulary, code conventions, and 30 readers of the changed files (checks.log, run2.log, pt3.log).
- test_generated_boot_entry 5/5 at both stages.
- An earlier host-pass red was my own PYTHONPATH=scripts making `_summary_block` look installed. It was clean when re-run without it.
- Not run (toolchain hazard, they start the Unix port or twins): test_digital_twin_ci_suite_errcount, test_stripped_image_boots, test_digital_twin_generated_boot, test_digital_twin_scenarios, test_build_firmware, test_setup_toolchain_env.

**Red, waiting on you:** test_twin_record, 2 failed. One is pre-existing: reset_code_loop_end.py has no entry. The other is stale hashes, now including test_reset_reasons.py and reset_code_invalid_record.py (api_sha256); it needs a `record_twin_instrument_runs.py` run.

**Silent-failure scan of begin_boot** (all modes STA/AP/Silent/Off/USB alike, every device):
- Class 7 (soft reset unattributed): covered now.
- Class 3 (record validity): inherently safe; magic plus check word, and power-on clears the regions.
- Classes 1, 4 and 5: nothing added.
- New, not covered (console only, within the brief's order): a loop that ends during boot writes no record. A Ctrl-D after a power-on boot then reads 1, not 10+p.

**Surprise:** I ran `git stash list` once, by mistake. It is read-only, and no stash was made.

**Runs:** every run has RUNS.md start and done lines, and all exited. The scratch bite and mpy dirs are deleted.

nothing of mine is running
