U30 lane S2 hand-back (branch audit/u30-s2, worktree S/wt-u30s2, nothing pushed). Commits: b42a097 (memory steps), 0bd91fb (merge of audit/u30-api at c253487), 7838df9 (report_if_fatal and re-arm). Logs: S/u30/laneS2/.
Steps applied: 55 (codec handlers narrowed; the format, range check and clamp were already on BASE), 63 (`unpack` import out, `report_if_fatal` import in; the docstring was already landed), 64 (13 forwarders), 65 (import), 67 (VOC algorithm built at construction), 81 (the decode part only: the copy-free `_words` decode; the waits are U31's), 82, 83 (folds (1) and (2) were already on BASE), 84 (`_exchange`/`_read_word`/`_read_words`, `sleep_ms`), 88 (including `_compensation()`, where BASE moved that handler), 89 (including `_run_restore`'s NTP callback handler), 99 and 101–104 (the test parts; the `_NoneReadWord` tests were already gone on BASE). Open findings: OF-50 (both halves, through `_rearm_timer()`), OF-51 (SCD30 half), OF-64, OF-90, OF-152.
Step 66: its own U30 part needed nothing, because the handler is already `except MemoryError` on BASE (asy_sgp40_driver.py:244), not a broad one. Part (1) skipped: dropped at U16 (REGISTER A-26).
Seen failing first (BASE code, new test, failing line):
- `_voc_algorithm` was None (sgp40 test :565).
- `_read_word` and `_read_words` were missing.
- The measurement waited with `sleep(0.1)` (:553).
- `get_buffer()` was called on every waiting cycle (:2035).
- `_backup_buf` was missing.
- SCD30 `_words` was missing.
- The store logged twice per cycle and again every cycle (scd30 :2024).
- VOC: 1.5 M `_f16` calls over the 20,000 reference samples (:578); the `_f16_*` attributes were missing (:592); RuntimeError and MemoryError were swallowed by the codec (:367, then :369).
- The SGP40 restore under an injected MemoryError fell back to a silent fresh start (:2119).
- Re-arm not persisted (scd30 :909, sgp40 :1018); fatal flag not set (scd30 :2212, sgp40 :3372).
Bites (scratch copies only, S/u30/laneS2/bites/):
- Reset settle dropped, self-test wait cut to 300 ms, reset wait set to 0: the wait guard fails (:288 and :290).
- SCD30 word bytes swapped: the decode guard fails (:213).
- A double-precision literal for one constant (:594), and a truncating conversion (the reference index sequence fails, :569).
- MemoryError and OverflowError dropped from the handler tuple: the codec guard fails (:351).
Times, after (base) at -1 / 32768: VOC 2.77 s (3.36) / 20.49 s (25.80); SGP40 8.03 s (7.88) / 10.88 s (10.62); SCD30 22.44 s (21.79) / 43.46 s (43.78). All within 10 %.
Checks, all green at both stages with zero MemoryError / "memory allocation failed": the twin SCD30 and SGP40 files, notification_scd30, the L1 hazard file, boot contiguity unchanged (36 passed, 12.7 s), the 12 pre-commit checks, ruff, both mypy passes, `tests_hardware --collect-only` (196 collected). `test_twin_record.py` will be red, as expected.
Decisions (agent, 2026-10-20):
1. `unpack_from()` lets MemoryError propagate instead of the step's `(MemoryError, …)`. The scan rule wants a loggerless catcher to print the text, which `voc_algorithm.py` cannot (no `asy_print_log` import by R-5, T20 bans `print`). SF-A12's own alternative is to let it propagate, as `asy_crc_checks.py` does. The read path then logs `str(e)` and retries the restore next cycle.
2. OverflowError is added to both handlers: a huge offset raises it in both, measured on v1.29.0.
3. The backup buffer is retried once per due cycle while its allocation has failed, so it still heals itself.
4. The SCD30 episode ends only at the next good read, matching lane C's store-level episode, and the int read is skipped once the float read fails.
5. The redundant `is not None` asserts are removed; the one at :2616 stays, with the comment "built at construction".
6. The negative-offset comment is corrected: v1.29.0 counts a negative offset from the buffer's end.
Modes: every change applies in STA, AP, Silent, Off and USB.
- No output, wire or value change: the decode, the word read, the VOC constants (output identical to the C reference).
- Boot placement changes on the SGP40 devices.
- The buffer reuse matters most where NTP never syncs (AP, Silent, Off).
- The fewer config console lines matter most on USB.
Scan (all classes, my files): the one new finding is the codec MemoryError that the memory gates could not see, fixed by decision 1. A contract-type store failure on SCD30 still logs every cycle (a code defect, outside the finding).
Facts owed to the lead:
- C1's `_rearm_timer()` comment says start_timers() runs before the tasks; the generated main starts tasks first (`build/generated_src/sensortask_wozi.py:233-235`). The helper is correct either way.
- For X's I.2 catalog and await-depth test: SGP40 now has VOCAlgorithm (35 new attributes) and a 268 B backup buffer as construction survivors (the H44 survivor figure needs re-reading), and `_exchange()` adds one await level.
No relay lines written. Nothing of mine is running.
