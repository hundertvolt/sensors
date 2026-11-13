# V_FWA: verification of FWA-1 to FWA-7 (firmware: sensors, buses, FRAM, config manager, print log)

All paths are relative to `S/wt-final` (590cffcf) unless marked. The baseline is `25caf528`.

## Summary table

| id | verdict | one-line reason | fix size (lines) | touches device behaviour? |
|---|---|---|---|---|
| FWA-1 | CONFIRMED | Every caller passes a dict, and the REST boundary owns the non-object refusal, so both of the owner's 10-27 conditions hold. FWA's provenance is wrong, though: the substance is pre-audit, and D2S kept it on a reason that fails. | ~7 src lines, plus 1 test (~16) | n |
| FWA-2 | CONFIRMED-OWNER | The fact holds. The RAM-only reading is the lead's 09-30 widening of OR99, and the owner's later rule is general. The fix is larger than FWA states, since the flag carries test, CI and doc scaffolding. | src -5; ~40-50 removed in total | y |
| FWA-3 | CONFIRMED | The two bodies are identical: same logger object, same errno 23, same text, same call depth. No test references either one. | ~12 | n |
| FWA-4 | MINOR | It is true that nothing calls it, but it is pre-audit library API (the sync pair with `session_end`), and SPEC recommends it to new SPI drivers. The real leftover is the SPEC text, which contradicts the method's refusal. | 2 doc lines (keep the method) | n |
| FWA-5 | CONFIRMED | An audit-era base primitive (U15) with one caller. The same job is already done inline at scd30:531. It carries a type ignore and stale SPEC wording. | ~-12 (src, test, SPEC) | n |
| FWA-6 | MINOR | The four copies are pre-audit and identical at the baseline. Merging them reworks four drivers to save ~25 lines, grows the diff against main, and closes no gap. | ~40 touched | n |
| FWA-7 | MINOR | Pre-audit and construction-only. A merge needs a reserve/commit split or a factory, because the chunk is built at the address fixed by the check, so it saves only ~10 lines. | ~30 touched | n |

## Per finding (short)

### FWA-1: CONFIRMED (with a provenance correction)
- **Fact: true.**
  - `src/asy_config_manager.py:194`: `data: object`.
  - `:200`: `| None` return.
  - `:204-205`: `type(data) is not dict` -> None.
  - `:599-601`: the BAD_ARG "write data is not an object" branch.
  - `src/asy_scd30_driver.py:278`: the `# type: ignore[misc]` that exists only for the Optional.
- **Reachability: none.** The only two callers of `compare_before_write` are `asy_config_manager.py:595` and `asy_scd30_driver.py:277`. Every path into `write_config` hands over a dict:
  - REST `_body_as_dict` (`asy_webserver_service.py:194`, isinstance dict) and `_put_sensors` (`:792`, isinstance dict);
  - the `_apply_settings_groups` subset comprehension (`:642`);
  - SCD30 `rest`/`frc` comprehensions (`asy_scd30_driver.py:265-266`);
  - NTP and Wi-Fi comprehensions (`asy_ntp_client.py:198`, `asy_wifi_service.py:299`);
  - the recovery `{key: recovered}` (`asy_base_classes.py:529`).
  The base `_set_dict_cfg` already runs `key in data` and `data.items()` before `_set_mgr_cfg` (`asy_base_classes.py:366`, `:389`, `:393`), so the base would fail earlier anyway.
- **Correction to FWA's "Decision record".**
  - The guard is not new in substance. The baseline `write_config` caught `(MemoryError, AttributeError)` for "a non-dict `data` param" (25caf528 `src/config_manager.py:353-356`). It had a pre-audit test, `test_write_config_non_dict_data_returns_false_not_uncaught` (25caf528 `tests/test_config_manager.py:1813`), which survives as `tests/test_asy_config_manager.py:1973`.
  - The D2S typing-guard lane named this site and kept it (archive `audit/artefacts/evidence/U35_close/redo/handbacks_redo/D2S.md`, table row: "asy_config_manager.py:204 | ty | compare_before_write | keep | data is JsonMapping (a Mapping), which admits a non-dict mapping").
  - That keep is agent text, and its reason fails:
    - the parameter is `object`, not JsonMapping;
    - `.items()` serves any Mapping, so a non-dict Mapping needs no refusal; the guard would wrongly refuse one;
    - no caller passes one.
  - The owner's rule applies to pre-audit code too (11-07). The rule (10-27): "if the check you remove really solely covers typing breakages and nothing else it can go (option b)"; the test is "fully covered by typing adherence alone, and ... unreachable with today's code". Both hold once `data` is typed `JsonMapping`, which every caller already satisfies.
- **Smallest fix (as FWA's):**
  - type `data: "JsonMapping"` and make the return non-Optional;
  - delete `:204-205` and the "None for a non-dict data" clause in the comment at `:203`;
  - delete `:599-601`;
  - drop the `[misc]` ignore at scd30:278, which `warn_unused_ignores` would otherwise flag;
  - delete the one test that feeds non-dicts through a `type: ignore`.
- No behaviour change on the device.

### FWA-2: CONFIRMED-OWNER
- **Fact: true.**
  - `src/asy_base_classes.py:598-599` (`_CFG_LOG_FRAM = True`, commented "owner, 2026-09-29: 'no extra FRAM chunk'") and `:617` (`LogConfig(None, ...)` rebuild).
  - `src/asy_scd30_driver.py:193-194` (`False`).
  - Baseline `SensorReaderConfig` handed `fram` to every ConfigManager (25caf528 `src/base_classes.py:277-281`). The flag is audit-era (U15).
- **Decision record: checked.**
  - OR99, owner, 2026-09-29, archive plan row 459: "No flash writes, no extra FRAM chunk (FRAM stays optional)". It sits beside a third condition that makes the FRC criteria "true config parameters ... (that is an allowed API triggered flash write)".
  - OR99.a (the agent's integration, row 460) places "no FRAM chunk" on "the whole state", meaning the readiness state.
  - The U15 plan at first read it the same way (archive `audit/actions/U15.md:346`, `:1627`). It was then widened: "Lead, 2026-09-30: the `CFGMGR_SCD30` FRAM chunk is not taken" (`:1632`).
  - `CLAUDE.md:321` now credits that reading to the owner, "on the FRC settings".
  - Owner, 2026-11-09 21:27 (rulings file :1331): "either it gets FRAM if it has something to log, or it should get no logger at all".
  - No owner word applies or exempts SCD30 since then.
  - CFGMGR_SCD30 does have things to log: unreadable or damaged file, failed write.
  - The owner's literal 09-29 words can still be read as "no extra chunk for anything this feature adds", so the owner must decide.
- **Fix size: FWA understates it.** Removing the flag also removes its scaffolding:
  - `tests/_sensortask_scenarios.py:394`, `:1100`, `:1350-1352`;
  - `tests/test_asy_base_classes.py:~2098-2122`;
  - `tests_scripts/test_buildgen_generate.py:451-463`;
  - `scripts/_digital_twin_ci_suite.py:144-146`, plus `tests_scripts/test_digital_twin_ci_suite_errcount.py:151-153`;
  - SPEC `:844`, `:938`, `:7713-7714`; `CLAUDE.md:320-322`; `digital_twin/README.md:775`;
  - the fixtures, test and mock rows that list `CFGMGR_SCD30` may change their FRAM-backed expectations.
  All of this is audit-era, so the change against main shrinks.
- **Device behaviour: yes.**
  - Each SCD30 device gains one chunk, about 2 x (2+10+1+2) = 30 B.
  - Every later chunk shifts. The per-owner seed makes the first boot read the shifted ones as blank, which is the decided handling for a layout change.
- **Owner question:** Did your 2026-09-29 "no extra FRAM chunk" mean only the FRC readiness state? If so, the SCD30's config error log should get FRAM like every other `CFGMGR_` logger, under your 11-09 "FRAM if it has something to log" rule.

### FWA-3: CONFIRMED
- **Fact: true.**
  - `src/asy_fram_manager.py:67-75` and `src/asy_fram_driver.py:153-161` are the same try/`begin()`/`err_s("FRAM bus not available:", e, errno=_ERR_UNEXPECTED)`/False.
  - `_ERR_UNEXPECTED = 23` in both (manager `:45`, driver `:90`).
  - Same logger object: the chunk's `self.pr = manager.pr` (`:94`), and `FRAM_SPI(..., logger=self.pr)` (`:496`, driver `:109`).
  - The manager uses it at `:178`, `:267`, `:325`, `:337`, `:620`. The driver's only users are `set_write_protected`/`verify_present` (`:299`, `:345`), library methods with no product caller.
  - No test references either helper.
- Both came in 910a0a62 (2026-11-10). No decision keeps two.
- **Fix:** make the driver's helper public, call `self.fram.begin_or_refuse()` at the five manager sites, and delete `asy_fram_manager.py:67-75`.
- Call depth is unchanged (one call, then `begin()`, then `begin_sync()`), and so are log text and errno.

### FWA-4: MINOR (keep the method; fix the stale SPEC wording)
- **Fact: true.** `src/asy_spi_driver.py:197-202` has no product caller. FRAM uses `begin_sync()` (`asy_fram_driver.py:318`); `__aenter__` uses `_begin()` (`:134`). Only the tests use it (`tests/test_asy_spi_driver.py` ~12 sites, `tests/test_readiness_gates.py:221`).
- **Why not worth removing:**
  - It is pre-audit public API (25caf528 `src/asy_spi_driver.py:126`). It is the synchronous counterpart of `async with`, paired with the still-used `session_end()` (`:204`, called by `__aexit__`) and the `*_sync` transfers.
  - SPEC C.3.1 (`SPECIFICATION.md:3171`) names it the form "a new SPI sensor driver should prefer".
  - `begin_sync()` is a different shape. It asserts no CS and returns the wiring for per-command framing, so the only shared code is the 2-line refusal.
  - Owner 10-23 (library rule) and 11-09 (ask before removing an unused feature) apply. Removing a baseline method grows the diff against main.
- **What is a real leftover:**
  - `SPECIFICATION.md:3172-3173` and `:7786-7787` still describe it as "for a caller that already holds the bus lock". That is the baseline's semantics.
  - The 11-10 body refuses exactly that case: `asy_spi_driver.py:200-201` raises while `session_lock.locked()`.
  - A driver written from the SPEC would hit the RuntimeError.
- **Smallest fix:** reword the two SPEC sentences to "when no async session holds the bus".

### FWA-5: CONFIRMED (low priority)
- **Fact: true.**
  - `src/asy_base_classes.py:537-542`: async, no await, a generator, `type: ignore[arg-type]`. Added in 5689e2f4 (U15, 2026-10-07).
  - Its one caller is `src/asy_scd30_driver.py:400`.
  - The same "store a new SCD30 tuple, no await" job is done inline at `:529-531`. The owner's 11-04 "option c" decides the behaviour (a stopped sensor publishes no values), not the primitive.
  - SPEC `:7711-7712` lists it as a catalog primitive. That is agent text, and stale: "in one data-lock hold", although `_datastruct` has no lock (`asy_base_classes.py:294`).
- **Fix:** `:400` becomes one direct store, `SCD30(None, None, None, None, None, _FRC_NOT_MEASURING, None, getattr(self._datastruct, "TS", None))`, the `getattr` form `:529` already uses. Then delete `_republish`, its test (`tests/test_asy_base_classes.py:1417-~1422`) and the SPEC entry.
- The stored tuple is identical and there is still no await, so the SCD30's interleaving test is unaffected.

### FWA-6: MINOR
- **Fact: true.** The cited blocks are identical apart from timer, period and flag.
- They are pre-audit, and identical at the baseline:
  - `src/asy_bmp3xx_driver.py:288`;
  - `src/asy_scd30_driver.py:212`;
  - `src/asy_sgp40_driver.py:463`;
  - `src/asy_isl29125_driver.py:847`.
- No decision record either way.
- A base `_arm_timer` touches four drivers and the base to save about 25 lines, and closes no gap. The brief's lens: reworking pre-audit code grows the change against main, and the gain is marginal.

### FWA-7: MINOR
- **Fact: true.** `src/asy_fram_manager.py:515-540` and `:557-593` are pre-audit (25caf528 `:645-716`) and run only at construction.
- FWA's "one placement step that takes the full size and the built chunk" does not fit as stated. The chunk is constructed at `self._allocated_size` after the capacity check (`:529-532`, `:579-585`).
- A merge needs a reserve-then-commit pair, or a factory closure. Either way it saves ~10 lines of pre-audit code for no gain on the device.

## Duplicates and notes
- **Duplicates.** None across FWB, BUILD, DOCS and TESTS.
  - FWB-3 (UARTComm `isinstance` guards) and FWB-5 (config getter `len` checks) share FWA-1's root class (M4, typing-only or unreachable checks) but are different sites. They are not duplicates.
- **FWA's Notes, checked:**
  - **BMP3XX derived-domain gate:** accurate (`asy_bmp3xx_driver.py:295-297` against `math_helpers.py:81`). It is audit-era (U15, 5689e2f4; the baseline only called `altitude_baro`). Agreed marginal.
  - **I2C boot clear:** `.send(None)` is safe, because `StopIteration` is caught at `asy_i2c_driver.py:97-98`.
  - **Removed I2C parameters:** confirmed present at the baseline (25caf528 `src/asy_i2c_driver.py:238-250`, `:325`).
    - `out_start`/`in_start` lose no capability, since memoryview slicing gives the same.
    - `setup(probe=False)` was a real option with no caller. It was removed before the owner's 10-23 and 11-09 rules. It is an owner question only if the owner wants it, not a finding.
- **FWA's "checked and clean":** spot-checked.
  - C-stack records in scope are only at `asy_base_classes.py:130`, `asy_isl29125_driver.py:959` and `asy_print_log.py:90`.
  - No per-episode flags remain (no `_episode`, `repeat=` or `_warned` in `src/`).
  - Both agree with FWA.
