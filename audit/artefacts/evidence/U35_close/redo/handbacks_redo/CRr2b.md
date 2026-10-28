CRr2b hand-back, saved by the lead from the message it sent (2026-10-27). Commits b63be1b6, 59021b11 on audit/u35-crr2b (on 0dcc13d2).

U35 lane CRr2b hand-back. I stopped at a seam at about 80 tool calls. Branch audit/u35-crr2b in S/wt-u35crr2b, on 0dcc13d2. Not pushed; nothing uncommitted.

**Commits**
- b63be1b6: the "Added for CRr2b" item (ISL29125 sibling-read overlap).
- 59021b11: the bench log check, partly done.

**Counts (review_rows.py, after b63be1b6):** 8482 rows: CRr2 83, fixed 46, justified 128, biting 8225. `--check` rc=0.
- At base, `--check` was already red: CMr1's split left `tests/test_digital_twin_network_neopixel.py::test_a_restarted_signal_task_ends_dark_with_the_overlay_restored setup_credit_only` without a verdict. I gave it "biting": a false flag, because the assertions sit in `_restart_ends_dark`'s nested `scenario()`, which `run()` drives.

**Added item: fixed.**
- The device script now records every sibling read's window and reports `overlapped_reads`: sibling reads whose window intersects a write window, compared through ticks_diff.
- The test at `flash/test_bus_concurrency.py:213` asserts `overlapped_reads > 0` before `_no_errors`.
- The ds_facts row is now "fixed". README :1719-1723 is updated (it said WRITE_CYCLES=8; the script runs 10).
- Bites on synthetic output: with no overlap, HEAD's test passes and the new one fails; with an overlap, both pass. HEAD-shaped output (no fact) fails the new test. `_overlapped()` is right on 6 hand-made window cases, the tick wrap included (`S/u35/laneC/crr2b/bites_isl.out`).
- TwinBoard: the script passes (`twin_isl.log`, rc=0). A plant that stops the siblings before the first write passes HEAD's test and fails the new one (`plant_test_bus_concurrency_old.log` / `plant_test_bus_concurrency.log`).

**Bench log check (CR4's item 1): partly done.**
- **Fixture:** `bench/conftest.py` has `no_unprovoked_log_entry` (autouse) and a `log_check_host` callable. Each test gets a GET /status before and after, and nothing is cleared or written. A new E or W entry in any logger fails the test, naming the logger, the code, its catalog name and the test.
- **Marker:** `provokes_log` is in markers.py's table. A marker without exactly one non-empty reason fails the test.
- **Helpers:** `error_log_helpers.py` gains `gained_entries()`, `new_logged_entries()`, `assert_no_unprovoked_entry()` and `clears_made()`. `tests/_error_codes.py` gains `name()`, the reverse lookup.
  - `gained_entries()` is the hotspot module's shift alignment, moved there and now shared by both.
  - A clear made through `reset_all_error_logs()`, or a history the later read does not continue, makes the whole log new.
  - A counter that grew with no new slot counts as a repeat of the newest entry.
- **Hotspot route, re-checked:** reads go through the DUT's gateway while the bench radio is its client, and through dut_ip after that.
  - After the real-credentials PUT, the DUT is not reachable by either route, so that test, the second-streak test and the flip-back test are marked.
- **Marked so far: 13 bench tests.** end_to_end burst ×1, hotspot ×6, modlwip control image ×1, network_resilience ×5 (outage, flaps, above-ceiling, oversized body, console misbehaviour).
- **Tests:** `tests_scripts/test_bench_log_check.py`, 18 tests. All were seen failing first: an ImportError for `name`, an unknown-marker collection error, then 16 AttributeError/assert failures.
- **Plants:** 10 of 10 caught (`plants.out`): no after-check, W ignored, fallen counter, marker not honoured, hotspot always gateway, bare marker, reason not enforced, clear count ignored, repeat ignored, catalog name dropped.

**Left for the next agent**
1. Class the remaining bench tests by reading src:
   - network_resilience :729 (exact ceiling) and :604 (concurrent body sizes);
   - heap_under_connection_ceiling :116 and serving_heap :75 (both go past the ceiling, so HTTP_REFUSED is likely);
   - all of test_reset_reasons;
   - uart_link_under_api_load :72 and :101;
   - wifi_radio_reinit :21;
   - system_commands_over_rest.
   My map is `S/u35/laneC/crr2b/bench_map.txt`, and `mark_bench.py` applies marks.
2. The 19 flash markers.
3. Verdicts for the 21 bench hw_no_log rows, then a re-render.
4. A short README paragraph on the log check.

**Not verified on silicon:** the fixture assumes the board answers /status at each test's bounds. A test that ends while the board is still booting would raise a teardown error.

**The lead should not run the bench tier until step 1 lands:** an unmarked test that provokes entries would fail.

**Checks**
- lint_direct: clean after fixes (ruff on the last pass, run directly).
- Main mypy: clean, 271 files. Host mypy: clean, 310 files. Bench-conftest pass: clean. All with no cache.
- `--collect-only`: 201/232 (31 deselected by the wear gates).
- Readers: 1668 passed, 2 failed, both in test_twin_record. One is the three un-recorded instruments that were red at base; the other is the hash re-record.
- `test_notification_fram_integration.py` (imports `_error_codes`): 3/3 at -1 and at 32768, zero memory markers.
- Silent-failure scan: no finding. No timing growth.

**For the lead**
- Re-record the twin for `flash/test_bus_concurrency.py`, `bus_concurrency_isl29125_write_vs_siblings.py` and the changed bench files. No allow-list row is needed.
- The same overlap gap exists, untouched, in `bus_concurrency_scd30_write_vs_siblings.py` and in the HTTP bench counterpart of the ISL test.

**Product question:** none.

**Deviation:** `plant_setup.sh` removed `__pycache__` with `find -exec rm` inside my own plant copy, which is not rm as its own command. Both plant trees are now removed.

**Runs (all in RUNS.md):** twin_isl rc=0. Plant runs: old rc=0, new rc=1 (expected). Checks: i1 readers rc=1, i2 lint/mypy rc=1 then fixed, readers rc=1 (twin_record ×2). collect rc=0. mp_both rc=1, which is only the grep exit on zero memory markers (both stages passed).

nothing of mine is running
