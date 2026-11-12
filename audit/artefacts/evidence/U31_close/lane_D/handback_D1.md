U31 lane D block D1 FINAL
Branch: audit/u31-d (S/wt-u31d), head 490ecdc. Nothing uncommitted, nothing pushed. Merged d56c92d as 91eb526 with no conflicts; rebuild.sh rc 0.
Commits: 399066b (F.3 table and test), 0fbdd28 (E.9/F.2/C.9), e40c960 (both READMEs), 7847e61 (BACKLOG and CLAUDE.md), f38b63b (F.3 persisted-log row fix), 490ecdc (D.4, the lead's item 1).
Steps:
- 50 + 61 M.SPEC.097, applied. F.3 now has 9 consumer rows and 27 budget rows between the markers. The rows include con.uart_tx, stall.wlan_switch and stall.console, the last per the owner's 2026-09-30 debug-mode limitation. con.watchdog is 6000 ms, with no scan term subtracted (asy_system_service.py:63; buildgen/validate.py:95). con.uart_reply is 925 ms (asy_uart_comm.py:95, :112; devices/dev.toml). hold.fram_block is 23,148 µs against the 25,000 µs l3 budget (fram_command_hold_timing.py:30).
- 61 M.DOCS.064, applied: two BACKLOG rows (the stretch/flash-gap runs, the bench loop lag) and a build-environment entry for scripts/_digital_twin_scenarios.py.
- 66 (E.9 lists both flags), applied. 67, lane T's part: two rows in the twin README flag table, checked against run_generic_integration.py:254-255, :523, :529 and :645.
- 63's remainder, applied: tests_hardware/README paragraphs for flash_write_loop_gap.py and loop_lag_under_combined_load.py, plus the "three F.3 rows owed" line (test_memory_stress.py:92-122).
- F.2 and the C.9 Supervisor row now say a MemoryError takes the timeout's path to the reset (asy_system_service.py:548-551). CLAUDE.md's boot-latency bullet gains one new sentence pointing at F.3.
- Lead item 1: D.4 now names the ServingLimits seconds-to-ms exception (asy_webserver_service.py:155-158, :582-583). Lead item 2: the relay's `## Lead` part names no new code, so C.9's Supervisor row and F.1 still say TASK_RAISED.
Seen failing first: before the table existed, test_timing_budget.py:177 failed with "SPECIFICATION.md must hold Part F.3's timing tables exactly once between <!-- timing-budget:begin --> and <!-- timing-budget:end -->".
Bites: committed fixtures on tmp copies, 9 classes, each failing as intended: a value that differs from the code; a crossing not marked; a stale crossing; an unknown Part N ID; a missing row; an unknown consumer; the task-end count; a lost marker; `_RESET_DELAY` = 9 in a tmp src copy (the relation to the watchdog).
Checks, one process on f38b63b: the 26 files (lane D's 7, the 17 repo scans, and the readers device_script_bench_facts, lock_order, memory_catalog, threat_model_statement, src_sleep_forms, twin_runner_test_flags) gave 973 passed, rc 0, 0 memory markers. On 490ecdc, 8 of them gave 712 passed, rc 0. Host mypy and ruff on the new test: clean. The one warning is the uninitialised datasheets/ submodule.
- No red checks. Time: the new test runs in 0.54 s and has no base. Silent-failure scan: docs plus one host test, no code changed, so no class applies.
For the lead to reconcile with T3: the relay now names buildgen.validate.smallest_hard_consumer (c4fe5ad), but my tree lacks it. test_timing_budget.py's `_device_terms()` computes the uart_link slack from the same constants through module_int_const/_uart_bus_value/_WDT_TIMEOUT_MS. It gives the same figures, 925 ms and 6000 ms. At merge: swap that slack loop for smallest_hard_consumer(load_device(device_toml(d)), src).ms; optionally assert lag.loop's bound per device. The docs cite the l2.loop_lag_* rows only by ID and never name the helper, so a T3 retune leaves my text correct.
Decisions (agent, 2026-10-21):
- A cell that opens with a figure states its value. stall/hold/lag rows are held to the consumers they name. feed rows are held below the whole wdt.timeout_ms.
- hold.fram_block cites F.5.8's owner decision (2026-09-26, 'Probably better to keep'), not the packet's 2026-09-18.
- Facts I could not check against the code were left out: the SCD30 read of about 1.8 ms, the 110-116 ms idle chunk write, the "<25 ms" FRAM erase, and the console test's flash-write count.
- The CLAUDE.md pointer is a new sentence, so no existing byte changed.
- The persisted-log row follows asy_fram_manager.py:96-97: one block at a time device-wide, plus a per-chunk lock.
RUNS.md: two start/exit pairs, both rc 0.
nothing of mine is running
