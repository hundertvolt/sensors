# B4 falsification, verified at the source (lead, 2026-11-03)

Each refutation in `FALSIFY.md` read against `963d0de1`, `3129bf21`, `25caf528` and `ACTION_LIST.md`.

- Claim 3 holds as planned: row 3 names `:1235` (a refused STOP) as going with its catch; a refused STOP gives ENODEV,
  every caller catches any `OSError`, only the log text differs. No change.
- Claim 5: both changes are on the action list: `_words` is row 4's SCD-12, the FRC guard row 21's episode flags; a
  repeated CFGMGR entry counts but takes no new slot (the newest-entry rule, OR35.b). The brief's wording was too wide.
- Claim 8 CONFIRMED: `_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX` is 16383 at the head (an agent change of
  2026-09-29, `2949ed97`), 32767 at `25caf528`, in legacy (`python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:43`)
  and in the C reference. No proof of a failure for the pre-audit value; OR109 settles the transient allocation. Restore (F3).
- Claim 13 CONFIRMED: `tests_hardware/flash/test_bus_concurrency.py:258` asserts `reset()` consumed `por_detected`;
  row 5 removed that read, and `bus_reader_loops.py:89` reads EVENT right after `setup()`. `b4f_flash_twin` fails,
  `b4f_flash_twin_planted` passes. Fix (F1).
- Claim 14: the settle (row 21), the allocation pins (rows 4, 15), EIO (row 3) and the VOC restore checks (row 16)
  follow listed rows. CONFIRMED weaker: `_reset_errors_not_undone` admits any one non-E entry (`<= 1`), and
  `SharedBoot.acquire()` drops `_wait_entry()`'s answer. Fix (F4, F5).
- Defect B CONFIRMED: `bench/test_system_commands_over_rest.py:172-174` and `bench/test_bus_concurrency_under_api_load.py:424-426`
  expect blank FRAM logs after an erase; the next boot logs SGP40 W65 (row 13). Fix (F2).
- Defect C CONFIRMED: SPECIFICATION.md:8952-8955 (the SCD30 word buffer) and `asy_isl29125_driver.py:745` are stale. Fix (F6).
- Defect D follows rows 5 (BMP-1), 11 (owner quote) and 19 (ISL-8, REVIEW.md). Accepted, no change.
