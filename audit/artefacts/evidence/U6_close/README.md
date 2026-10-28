# U6 close: first full run's failures and the measurements behind their fixes

The first full gate on the merged U6 tree (`audit/u6` at `2029f41`) failed four pytest cases (the same at gc.threshold
-1 and 32768) and three live PUT matrix cases; all 88 MicroPython test files, every twin on all six devices and every
other npm test passed. Raw failure output: `first_run_pytest_failures_gc-1.txt`, `first_run_pytest_summary_gc32768.txt`,
`first_run_npm_failures.txt`. Each failure's cause, fix and record (SF-U6-06..08 in
`audit/sweeps/scan_runs/20261006_U6_close.md`):

1. **`test_synthetic_fixture_boots_and_serves_over_real_http[multi_instance.toml]`**, a product-generator bug. With
   two SGP40s the generated `_sgp_maintenance_status()` read `sgp40`, which no line assigns (`sgp40_a`, `sgp40_b`):
   `sensortask_multi_instance_before_fix.py.txt` lines 128-131. Every `/status` read raised `NameError` and the
   maintenance rows vanished. `scripts/name_sweep.py <dir>` lists every name a generated function reads that nothing
   defines: `['sgp40']` on that file, clean on all eight generated modules after the fix.
2. **`test_suppressing_the_emitted_collects_breaks_both_bounds[wozi]`**, a guard that had lost its margin.
   `scripts/contig_measure.py` and `scripts/band_measure.py` (run from a checkout root) print the probe's metrics. Wozi,
   suppressed arm, blocks more than 128 KiB above the seam: 33 at U5 (`c3df14e`), 10 at U6, against 32 allowed; the
   count depends on the length of the config path, so fresh, pytest-length directories are used. Blocks above N KiB:

   | arm, tree | 16 | 24 | 32 | 48 | 64 | 96 | 128 |
   |---|---|---|---|---|---|---|---|
   | wozi suppressed, U5 | 1120 | 864 | 708 | 607 | 533 | 240 | 33 |
   | wozi suppressed, U6 | 1045 | 789 | 703 | 592 | 516 | 236 | 10 |
   | dev suppressed, U5 | 1669 | 1630 | 1530 | 1348 | 1201 | 582 | 347 |
   | dev suppressed, U6 | 1669 | 1603 | 1510 | 1331 | 1198 | 538 | 332 |
   | live arm, all six devices, U5 and U6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

   The band moved to 32 KiB (live reach 16,352 B on every device). Repeated runs give identical counts.
3. **`test_no_function_level_or_dynamic_import_outside_the_named_lists`, `test_the_pending_list_only_shrinks`**: a
   renamed CLI test kept its function-level import while the allow-list named the old function; the import moved to
   the module top and three entries left the list.
4. **Live PUT matrix, dev, BMP3XX `PressOvers`/`TempOvers` option 1, `FiltCoeff` option 0**: each is the option the
   card already shows. A card without a dispatch field sends nothing for it, so no reply comes
   (`live_matrix_bmp3xx_before_fix.log`); `scripts/bmp_put.sh <checkout> <outdir>` shows the device itself answers
   every real change within 0.12 s. After the fix, 55 passed and 3 skipped visibly (`live_matrix_bmp3xx_after_fix.log`).

Also checked in the passing output, nothing found: the 13 case-insensitive "MemoryError" matches per GC stage are
test names (`..._memoryerror_...`), never a runtime marker; the 3 pytest warnings are `PytestUnknownMarkWarning`s for
`persistence_write` imported into `tests_scripts` (SF-U0-08, M.TOOL.034, U26/U27).

CI on U5 (`c3df14e`): `firmware-build-verify (dev)` stalled inside the runner's `apt-get install` with no output for
15 minutes until the job's 15-minute cap cancelled it (job 112436172126, before any project step); the other five
devices ran the same install in seconds. One re-run passed in 2 min 52 s.

Second full run (`a2ad6fc`): the MicroPython tier 88/88 at both stages again; one pytest case failed at both,
`test_each_ruff_ceiling_sits_at_its_measured_maximum[max-statements]` (`second_run_pytest_failure_gc-1.txt`): the
per-instance loop left `buildgen/codegen.py`'s `_emit_callbacks()` at 78 statements, the old maximum of 79 gone, so
the ceiling moved down to 78 (found with `ruff --select PLR0915` at descending `max-statements`).

## The final gate's read (1a721b9)

Both `scripts/test.sh` stages: 88/88 MicroPython files, pytest 2477 passed, 7 skipped, run with `-rs`. Six skips are
`test_build_firmware.py`'s real ARM compile, opt-in through `RUN_SLOW_FIRMWARE_BUILD=1`, which CI's
`firmware-build-verify` job sets; one is the dict case of `test_device_wiring_value_must_be_a_string_reference`
(`skip_inline_table/`). The 13 case-insensitive memory-marker matches per stage are test names; the 3 warnings are the
unregistered `persistence_write` marker on two bench modules tests_scripts imports. No test file needed a retry. The
twin suite on all six devices: every check at both stages, Run 11 on its first attempt everywhere, zero memory
markers. `npm test`: 1064 passed, 5 skipped, zero memory markers; the five, named by a verbose rerun of the two live
files (`npm_live_skips.txt`): four on `dev` are the enum option each card already shows (the resubmit
probe covers it); one is the SSID resubmit on `arzi`, the first device in the deduplicated matrix and so the one SSID
case, whose fresh twin has an empty SSID, so there is no value to resubmit (the empty-submit case is
`render.test.js`'s "skips the PUT ... nothing to submit").
