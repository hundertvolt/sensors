# R_fx1: firmware and buildgen lane (worktree S/wt-fx1, branch final-fx1)

One commit on `final-fx1`: `6cf43bff` (on 590cffcf). 38 files, +528 / -426. Not pushed.

## Per item

### 1. Boot-confined gc.collect() restored (owner, 2026-11-13 11:58) - DONE, with one stop inside it
- **Firmware** `src/asy_system_service.py` (+9/-1 for this item): `import gc`; `run_setups()` collects once before the
  list and once after each unit's feed; `start_tasks()` once before the loop and once after each starter (its pre-removal
  comment back). Fitted to today's code: both one-time lists live in `SystemService` (the generated module only calls
  `run_setups()`/`start_tasks()`), exactly as at `512bb0dc^`; buildgen/codegen.py carries no collect (the checker still
  refuses one there). The brief's "generated start_tasks() starter loop in codegen.py" does not exist today.
- **Guards**: `scripts/_check_gc_collect_sites.py` (+4/-1): categories `placement reset`/`boot mirror` and the two src
  rows plus the probe's `_ProbeGc.collect` row back. `tests_scripts/test_gc_collect_sites.py` (+5/-3): the now-false
  "no src row" test flipped to "src's rows are exactly run_setups and start_tasks".
- **Unit tests** `tests/test_asy_system_service.py` (+70/-7): the pre-removal `_CountingGc` pair (start_tasks collects
  N+1, the supervisor never; zero starters still one) replaces the now-failing `test_neither_boot_list_nor_the_supervisor_collects`;
  `_RecordingGc` and the collect-after-feed order back in the two run_setups tests.
- **Twin effect test**: `tests/_boot_contiguity_probe.py` (+49/-11, `_ProbeGc`, live/suppressed arms, LISTS/COUNTS) and
  `tests_scripts/test_digital_twin_boot_contiguity.py` (+172/-47) restored from `512bb0dc^`, fitted to today
  (`distinct_devices()`, `module_str_const`, one mirrored bound). Measured 2026-11-13 on build-standard, 16M heap:

  | device | arm | batch median depth | batch reach | boot median depth | boot reach | high blocks | used after batch | collects (batch/starter) |
  |---|---|---|---|---|---|---|---|---|
  | arzi/grkizi/klkizi | live | 898,816 | -806,176 | 942,368 | -805,376 | 0 | 544,000 | 9 / 14 |
  | arzi/grkizi/klkizi | suppressed | 769,856 | -514,272 | 825,472 | -519,360 | 0 | 544,000 | |
  | schlafzi | live / suppr. | 898,720 / 769,760 | -806,080 / -513,728 | 942,272 / 825,376 | | 0 | 543,776 | 9 / 14 |
  | wozi | live / suppr. | 910,784 / 793,280 | -827,200 / -453,024 | 965,600 / 831,168 | -821,536 / -457,984 | 0 | 566,176 | 10 / 16 |
  | dev (control) | live | 1,194,272 | -1,133,792 | 1,303,808 | -1,133,792 | 0 | 904,864 | 13 / 20 |
  | dev (control) | suppressed | 665,216 | -617,280 | 1,106,848 | -621,280 | 0 | 904,768 | |

  (bytes below/above the seam; bounds: batch depth >= 307,200, reach <= 65,536, high <= 32). The test itself prints
  only "dev: 2 receive rings, 1024 B of windows; largest free run 15224544 B before the batch, 15224544 B after".
- **STOPPED part**: "a suppressed control arm shows the bound would otherwise break" no longer holds on today's code -
  the suppressed arm lands low too (dev 665,216 B deep, reach -617,280 B: inside every absolute bound), which is the
  fact that led to the 11-10 removal. Retuning the bounds per device would be new machinery, so I did not restore
  `test_suppressing_the_placement_collects_breaks_both_bounds`. Restored instead, unchanged: the arms' ratio test
  (live median 1.80x deeper, bound 1.5x), retention (arms differ 0.011%, bound 1%), the real-boot collect count
  (setups+1, starters+1) with its reader test, and the control-set guards. Comments carry today's numbers.
- **Docs**: SPEC I.4(f.1) rewritten as the one structural exception with its record (owner 2026-09-18; 09-26 quote
  "gc.collect is allowed IN THE CODE at exactly the place you found it..."; 11-13 quote); the "(lead, 2026-11-10)"
  record and the "re-checks it on silicon on the next image" sentence are gone. Also restored at A.7 step 15, the stretch
  table rows 1/2, F.3's `feed.boot_first`/`feed.setup_unit`, Part N `boot.*` rows, the F.9 workaround row, I.1's "only places
  left", I.4(e)'s exception clause, the checker paragraph (src rows, boot-list mirror) and the effect paragraph (one
  device per hardware family; the ratio control). CLAUDE.md memory bullet (11-13 quote), work-routines skill line,
  HEAP_FRAGMENTATION_MEASUREMENTS.md (2 places), the device script's and flash test's docstrings, one test comment.
- Not restored (outside the brief): the hardware tier's suppressed arm (`heap_layout_after_full_boot_sequence.py`'s
  `_ProbeGc`, the flash suppressed test). The flash test keeps holding the live boot to the twin's high band.

### 2. CFGMGR_SCD30 back on FRAM (owner, 2026-11-13 12:01) - DONE
- src: `_CFG_LOG_FRAM` gone from `asy_base_classes.py` (-4/+1) and `asy_scd30_driver.py` (-3); every
  `SensorReaderConfig` hands `log` to its ConfigManager as at the baseline.
- Scaffolding gone: `tests/test_asy_base_classes.py` `_RamConfigLogReader` + its test (-26);
  `tests/_sensortask_scenarios.py` RAM-only branches and `_ram_only_config_logs` (-12, in-memory set is `["FRAM"]`);
  `scripts/_generate_sensortask_modules.py` `_config_log_on_fram`/`_sets_config_log_off` (-15);
  `scripts/_digital_twin_ci_suite.py` `_IN_MEMORY_ONLY_ERROR_SOURCES = {"FRAM"}`; its errcount test now asserts `["FRAM"]`;
  `test_buildgen_generate.py`'s RAM-only test flipped to "a FRAM-wired SCD30 keeps its CFGMGR_ log on FRAM too".
- Docs: SPEC A.7 chunk numbers (SCD30 cfgmgr chunk 9; SGP40 10/11, BMP3XX 12/13, NOTIFY 14/15, webserver 16; wozi 16
  log chunks), the chunk-order line, the G catalog's "Config-log placement" entry removed; CLAUDE.md corrected with the
  owner's 11-13 words; digital_twin/README.md Run 5c sentence.
- Device effect: each SCD30 device gains one ~30 B chunk and every later chunk shifts; the per-owner seed reads the
  shifted ones blank at first boot (decided handling). Read errcount before reflashing the bench board (CLAUDE.md rule).

### 3. FWA-1 unreachable non-dict chain - DONE (src -8/+3, tests -20/+5)
- `compare_before_write(data: "JsonMapping") -> tuple` (no None); `write_config`'s "not an object" branch and the
  SCD30 `[misc]` ignore gone (the SCD30 call now unpacks directly). Removed
  `test_write_config_non_dict_data_returns_false_not_uncaught`; `test_compare_before_write_refuses_a_non_object` lost
  its non-dict loop (no longer type-checks) and keeps its empty-body assertion under a fitting name; two test inputs
  annotated `JsonValue` for mypy.

### 4. FWA-3 one begin-or-refuse - DONE (src -24/+11)
- `FRAM_SPI.begin_or_refuse()` is public (D.15 position after `begin()`); the manager's `_begin()` is gone and its five
  sites call `self.fram.begin_or_refuse()`. Same logger object, text, errno 23, call depth.

### 5. FWA-5 `_republish()` - DONE (src -9/+3, test -9, SPEC -3)
- SCD30 `_frc_not_measuring()` stores `SCD30(None, ..., _FRC_NOT_MEASURING, None, getattr(self._datastruct, "TS", None))`
  directly; with no await left it is now a plain method (its two callers drop `await`). Base method, its test and both
  SPEC mentions (G catalog entry, I.2 allocation line) removed; the stale "data-lock hold" wording is gone with them.

### 6. FWA-4 SPEC session_begin() wording - DONE (2 lines): C.3.1 and the G.2 catalog entry now say "when no async session holds the bus".

### 7. FWB-2 escalation MemoryError arm - DONE (src -3/+0 net), SPEC F.2 clause plus the same claim in C.9's
  supervisor row and F.3's `feed.supervisor` row; the full-heap test's comment no longer names the arm (it
  passes unchanged: the supervisor's own handler records the fault, the watchdog resets with the code recorded first).

### 8. FWB-3 - DONE: three typing-only `isinstance` halves (poll_wait_ms, chunk_bytes, max_transfer_bytes) in
  `_validate_link()`/`_validate_receive()` dropped, range checks kept, pre-audit ones untouched. UART_C_PORT_CHANGELOG
  Class B entry B104 ("no C impact"). No wire, constant or timing change.

### 9. FWB-4 - DONE: `_Holder` and `_RequestLike.sock` gone (-6); SPEC's Microdot stand-in list fixed; two test
  `type: ignore[arg-type]` that became unused (mypy warn_unused_ignores) removed.

### 10. BUILD-5 - DONE: `smallest_hard_consumer` (now returns the int ms, the one-field NamedTuple dropped),
  `device_max_connections_by_name` and `_owns_config_store`/`_declares_config_store` moved from buildgen/validate.py
  (-50) to scripts/_generate_sensortask_modules.py (+47; tests_hardware/bench_facts.py already imports from there).
  Import edits: scripts/_digital_twin_scenarios.py, scripts/_digital_twin_ci_suite.py, tests_hardware/harness.py,
  flash/test_memory_stress.py, bench/test_memory_stress_bench.py, tests_scripts/test_digital_twin_scenarios.py (its
  "imports the one export" regex now names the new module), tests_scripts/test_buildgen_validate.py. `.ms` dropped at
  the 5 call sites. No generated output changes.

### 11. BUILD-9 - DONE: validate's max-timeout check and its num/den/mult read (-10), its validate test (-11) and
  error-contract row (-1), the rule token in SPEC L.6 and two SPEC sentences that said the build refuses a timeout above
  the ticks horizon (the runtime `_max_timeout()` keeps refusing it).

## Checks
- `rebuild.sh`: ok. lint_direct (ruff, shellcheck, actionlint, zizmor, method-assign guard, gc-site checker): rc 0.
- mypy main / host / twin: all "no issues" (fx1_c4).
- tests_scripts readers (29 files incl. gc sites, boot contiguity separately, buildgen generate/validate/error contract,
  twin scenarios, ci-suite errcount, code conventions, comment cap, citations, decision vocabulary, uart changelog):
  2,313 passed after fixes (fx1_c4: 1 member-order fail, fixed, re-run 687 passed); boot contiguity + gc sites 94 passed.
- MicroPython, gc -1 and 32768 (both clean, zero MemoryError lines): test_asy_system_service 182, base_classes 172,
  config_manager 240, scd30 132, fram_manager 135, fram_driver 77, fram_wire_trace 10, fram_allocation_budget 2,
  uart_comm 201, uart_link_driver 51, webserver_service 225, api_response 25, fram_integration 11, twin fram 57,
  twin scd30 57, test_sensortask x4 devices 86 each.
- Full `scripts/test.sh` under the ports lock (gc -1, fx1_testsh, 665 s): Result PASS - files 121 passed / 0 failed
  (29 skipped, 4 deselected, by their own device rules), tests 5,259 passed, tests_scripts 6,573 passed / 6 skipped,
  scenarios arzi 62, dev 63, grkizi 61, wozi 61 passed, 0 failed; no retry, no recovery pass.
- Extra: `scripts/run_digital_twin_ci.sh dev --gc-threshold -1 --part suite` (fx1_twin_dev): PASS, 13 checks; Run 5c now
  sweeps CFGMGR_SCD30 too (kept its history across the commanded reboot). The 32768 stage and other devices not run.

## Noticed, not done
- The twin CI suite ran for dev at -1 only (above); its 32768 stage and the other devices are left to the gate.
- The hardware tier's suppressed arm (see item 1); bench silicon has no recorded placement reading for this image.
- UART_C_PORT_CHANGELOG.md's "(lead, 2026-11-03)" credit (DOCS-7's relabel) is outside this lane.
- FWB-4's test-side residue (`allocation_need_per_source.py` `_NoopHolder`, `test_fram_less_boot.py` `_Holder`) left.
- Shared docs touched by this lane (merge with fx2/fx3): SPECIFICATION.md, CLAUDE.md, HEAP_FRAGMENTATION_MEASUREMENTS.md,
  digital_twin/README.md, .claude/skills/work-routines/SKILL.md, UART_C_PORT_CHANGELOG.md.
- Slip: one unfiltered grep (`_staged_src` in test_buildgen_validate.py) printed two schema-default fixture lines of
  the Wi-Fi service; nothing from them is repeated here.
