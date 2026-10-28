CRr1b hand-back, saved by the lead from the message it sent (2026-10-27). No commits; work uncommitted in S/wt-u35crr1b (audit/u35-crr1b at 4d6cf385).

CRr1b hand-back: stopped early because a safety check refused a command. No commits; the work is uncommitted in S/wt-u35crr1b (branch audit/u35-crr1b, at 4d6cf385).

**The refusal.** A command that wrote the bite copies and chained the bite runs was blocked. The check said: "passes a shell -c script that runs rm, and Claude Code could not check the script". The rm was `rm -f S/u35/laneC/crr1b/bite/summary.txt` (my own scratch summary), next to a `nohup bash -c "tail --pid=3791 …; bites.sh"`. Nothing in that command ran, so no bite files exist and no bite was run. I did not retry it in any form. Afterwards I only stopped my own timing run: pid 3791, run1.sh, plus its `sleep 15`, both checked by their args. It was waiting for a run slot, so no micropython of mine was running.

**Item 1: all 12 rows edited, none committed, none bitten yet.** `git diff` covers 6 files:
- **base_classes :2941 and :2983:** now `(reader.pr._err_count, _entries(reader, "E", <code>)) == (1, 1)`, with CFG_SNAPSHOT_RAISED and RECOVERY_WRITE_RAISED.
- **base_classes :2969:** a write-counting subclass. It asserts `(_write_calls, pr._err_count, cfgmgr.pr._err_count) == (0, 0, 0)` and the stored config unchanged.
- **fram :1385, :1397, :1407, :1420, :1432:** now `(fram.pr._err_count, _count(fram, code)) == (1, 1)`. This is stronger than the planned history-count-only fix: a repeated code spends no ring slot, so only ErrCount sees the second event.
- **http_client :392:** `_EofReader([None, b"ab", None, b"cNEXT"])`, asserting `(None, 4, b"NEXT")`.
- **ntp :1831:** under `_SteppedClock`, synced with the invalid config. The tick at 12 h minus 10 s does not trigger a resync, the tick at 12 h does. Plus `_slots == (2, [CFG_READ])`.
- **_sensortask_scenarios :2785:** sync spies on `SystemService.start_tasks`/`start_timers`, restored in a finally, then `started == [] and len(tasks) > 0`.
- **site-functions.test.js :135:** each field's [group key, kind] compared exactly: identity/string, identity/string, wifiLed/toggle, ntp/string.

**Runs** (base copy S/u35/laneC/crr1b/basetree, then head, back to back; summaries in S/u35/laneC/crr1b/r1/{base,head}/summary.txt):
- All pass at both stages with 0 memory markers: base_classes 197/197 (0.5 s → 0.4 s), fram 104/104 (0.2/0.3 s, same), ntp 196/196 (23.9/24.3 s → 23.9/24.4 s). No file is over 10 % slower.
- Not run yet: http_client, test_sensortask for the 6 devices, vitest.

**Bites still owed** (designs, for the next agent; S/u35/laneC/crr1b/tools/mkbites.py holds the edits but was never run):
- base_classes: call `_set_dict_cfg` twice; input "NoSuchField" changed to "SampleInterval".
- fram: run the scenario twice (WRDI with `drop_next_wrdi` 4).
- http_client: n 3 → 2.
- ntp: plant `ntp_interv = [11]` in a scratch copy of the module.
- scenario: plant `sysfunct.start_tasks([], [])` in a scratch copy of sensortask_wozi.py.
- JS: change SSID's kind to "readonly" in a scratch test.

**Also not done:** lint_direct, the mypy passes, comment cap, citations, decision vocabulary and tunables checks; the verdict updates (`was:<flag>` → fixed) and the review_rows.py re-render.

**Item 2** (read by hand plus S/u35/laneC/crr1b/tools/blind.py, output in blind_*.txt):
- **tests/_generated_tree.py:** a helper with no tests; its reader is tests_scripts/test_generated_tree.py (12 tests). It is weak in one place: no test removes an input after generation, so `require_fresh()`'s `len(current) != len(recorded)` clause is unpinned (an added TOML is still caught by `path not in recorded`). Proposed fix: add `test_a_toml_removed_after_the_generation_is_refused` (unlink the fixture's TOML, expect `_STALE`), bitten by dropping the len clause in a scratch copy.
- **test_asy_sgp40_driver.py:** checked the tests with no assert statement or no top-level assert (:182, :193, :232, :245, :411, :469, :774, :2995). All bite: `raise AssertionError` sits inside the try, and the loops run over literal tables. The remaining bound/in hits were not read one by one.
- **test_asy_uart_comm.py:** weak. Six provoked faults are checked only by membership in `persisted()` or ErrNum, where the rule asks for an exact entry: :567, :616, :636, :2268, :2854, :2977. The scan misses them because the log arrives through `persisted()`. They are unfixed, and their exact logs need a run.

**Item 3: searched, nothing removed.** `git grep` outside audit/: `_restore_is_all_or_nothing` (scripts/_digital_twin_ci_suite.py:790) is reached only by tests_scripts/test_digital_twin_ci_suite_errcount.py:106-128. Those are 4 tests that exercise only it. Run 5b (`_run_5b_error_log_restore_is_all_or_nothing`, :1339 and :1907) is a different, live function, and so is its COVERS_TWIN_SCENARIOS string in tests_hardware/flash/test_fram_storage.py:16. No README or SPEC line names the helper. Still to check: whether `_non_empty_slots`/`_counter` keep other callers once it goes. Its row lives in review_rows.py's SUITE_ROWS.

**Counts:** unchanged from the base (review_rows.py not re-run): 8467 rows, weak 12.

nothing of mine is running
