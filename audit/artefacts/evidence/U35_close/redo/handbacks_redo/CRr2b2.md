CRr2b2 hand-back, saved by the lead from the message it sent (2026-10-27). Commits 1def1d58, 2d73a934 on audit/u35-crr2b (after 59021b11).

U35 lane CRr2b2 hand-back. Branch audit/u35-crr2b in S/wt-u35crr2b, now at 2d73a934 (it was 59021b11). Not pushed, and the tree is clean. I stopped at a seam at about 78 tool calls. Item 1 is done. Item 2's bench classing, bounded fixture failure, bench verdicts and README paragraph are done. Item 2's flash markers and all of item 3 are not started.

**Commits**
- 1def1d58: item 1, bench/conftest.py back in its base order.
- 2d73a934: item 2 (bench part), every bench test classed, the fixture fails bounded, verdicts and README.

**Item 1: done**
- The five existing functions are back in 0dcc13d2's order: record_path, load_record, image_deviations, check_image, board_image. log_check_host and no_unprovoked_log_entry come after them.
- AST proof: every function's AST (decorators, signature, body) is identical to 59021b11's, and the other module-level nodes are identical and in the same order. The diff against base is now additions only (plus the docstring and imports).
- Files: `S/u35/laneC/crr2b2/reorder_conftest.py`, `reorder_proof.out` ("RESULT: OK").
- None of 59021b11's other changed files was reordered (`order_check.py`).
- Checks: ruff, the bench-conftest mypy pass, readers (715 passed) and collect-only (201/232) were all green (`i1_*.log`).

**Item 2: bench part done**
- **Class map:** `S/u35/laneC/crr2b2/bench_class.txt`, built by `bench_class.py`. It lists all 121 bench tests: **29 provokes_log** (13 from CRr2b, 16 new) and **92 unmarked**, each with a reason; none left unclassed.
- **New marks (16):**
  - network_resilience: largest body (its over-bound NTPHost is refused Invalid, which logs BAD_ARG), concurrent mixed sizes and exact ceiling (HTTP_REFUSED).
  - heap_at_peak and connection_wall (refusals at the ceiling).
  - serving_heap: per-source need (a probe that degrades catches its MemoryError and logs ALLOC) and the sweep (two past the ceiling).
  - reset_reasons: escalation (TASK_RAISED / TASK_BUDGET_REBOOT), stack exhaustion, incomplete command and boot-phase hang (see "Found on the way").
  - uart_link_under_api_load: overload (a burst of 6 at dev's ceiling of 6) and the hazard run (the responder refuses its frames).
  - uart_crc16 (it runs check_overload).
  - modlwip with the override (dead clients reclaimed at the per-call timeout, plus refusals).
  - loop lag (the hammer saturates admission).
- **Unmarked, main reasons:**
  - A normal operation or boot logs nothing. The only boot-time wrn_s is CONFIG_LOST, which needs an absent config.
  - SystemCmd near-misses and races are answered with no logger call (`_dispatch_system_cmd` / `_run_system_cmd`).
  - An FRAM erase leaves blank chunks; SGP40's "No backup found" on blank is pr.one(), not a warning.
  - The scripts whose services have no FRAM (radio reinit, starve fallback) lose their entries at the reset.
  - Many tests clear their own provoked entries at their end. Note that the fixture then sees only what follows that clear (a gap the tests' own clears create, not one I changed).
- **CR4's count is not met:** it predicted 21+10 = 31 bench marks; reading src gives 29.
- **What the after-read meets:**
  - Every reboot and reset test waits until the board serves again (recover_by_reset, restore_board_to_serving, or wait_until serving). So the after-read meets the rebooted board: RAM loggers start fresh and FRAM-backed ones continue.
  - Only test_serving_heap_at_default_gc's two tests leave the board without main.py, because isolated_board restores it once, after the module. Both are marked, so they are not read.
- **Fixture, bounded failure:**
  - Both reads go through a new `_read_logs()`: one GET /status under error_log_helpers' 10 s timeout.
  - On an OSError, HTTPException, AssertionError (a non-200 answer or a missing errcount), ValueError or TypeError, it calls `pytest.fail("<test>: the log check cannot read the loggers before|after the test - GET /status on <host>: ...", pytrace=False)`.
  - Test: `test_a_board_that_cannot_answer_fails_the_test_plainly_and_bounded`, three cases (timeout before the test; refused or 503 after it). All three were red first, raising bare TimeoutError / ConnectionRefusedError / AssertionError (`i2_red.log`), then green: 21/21 (`i2_green.log`).
- **Verdicts:** 15 bench hw_no_log rows set to fixed (covered by the autouse check). 5 are now stale, because the marker text makes a marked test "name a log", so their verdicts are dropped.
  - Two network_resilience rows got a new ns_seed_text flag from CRr2b's marker reason, which names `_assert_wifi_log_has_only_benign_outage_warnings`. I judged both "biting", with that reason.
  - 15 + 5 = 20 rows, not the 21 CRr2b counted.
- **README:** a new section "The bench log check" in tests_hardware/README.md.

**review_rows.py:** 8498 rows: CRr2 63, fixed 61, justified 128, biting 8246. `--check` rc=0 (`review_rows_check.out`).

**Checks for 2d73a934**
- lint_direct rc=0.
- mypy: main 271 files clean, host 310 clean, bench-conftest clean.
- collect-only: 201/232.
- Readers (with test_bench_log_check and test_suppression_form): 1333 passed, 2 failed, both in test_twin_record. One is the instruments without an entry, red at base; the other is the hash re-record. Logs: `checks_i2.out`, `*_i2.log`.

**Not done (next agent)**
1. Item 2's flash markers: the 19 flash tests from CR3's list, markers only, after classing each against src.
2. Item 3 in full:
   - Read `_shared/bus_reader_loops.py`'s window helpers first.
   - The b63be1b6 overlap fix in `bus_concurrency_scd30_write_vs_siblings.py`, with its NVM write sites unchanged and named.
   - The fix in the HTTP bench counterpart of the ISL test: `test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load` (bench/test_bus_concurrency_under_api_load.py:226; its readers run from `_load.readers`).
   - Move `_overlapped()` into `_shared/` if two scripts use it.
   - Bites on synthetic output and through TwinBoard.

**Twin record changes for the lead to re-record:** bench/conftest.py, test_heap_under_connection_ceiling.py, test_memory_stress_bench.py, test_modlwip_send_stall.py, test_network_resilience.py, test_reset_reasons.py, test_serving_heap_at_default_gc.py, test_uart_link_crc16.py, test_uart_link_under_api_load.py, plus CRr2b's files. No allow-list row is needed.

**Found on the way (for the lead, no change made)**
- The scratch-config device scripts can write a W CONFIG_LOST into production's SYSTEM FRAM log: reset_code_boot_phase_hang phases 3-5, reset_code_stack_exhausted, reset_code_command_incomplete, allocation_need_per_source. Each builds the system over a freshly emptied `hwtest-scratch/`, so `cfgmgr.absent_at_boot` is true beside FRAM history, and the reset reason is not a config reset (asy_system_service.py setup(), ~:753). This is a test artifact, not a normal situation, so it is no product question. It is one more instance of CLAUDE.md's "device scripts fabricate FRAM log entries" caveat.
- test_isl29125_calibrate_command_push asserts ISL29125's log empty right after the PUT. A later W75 ISL_CAL_TIMEOUT would land in the next test's window.

**Product question:** none. **Deviations:** none; deletions were only the typings symlink, as its own `rm "${W:?}/typings"` in checks.sh.

**Runs:** all 12 are in RUNS.md with done lines: i1_ruff, i1_mypy_benchconf, i1_readers and i1_collect rc=0; i2_red rc=1 (expected red); i2_green rc=0; lint_i2, mypy_main_i2, mypy_host_i2, mypy_benchconf_i2 and collect_i2 rc=0; readers_i2 rc=1 (test_twin_record ×2 only).

nothing of mine is running
