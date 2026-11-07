CFr hand-back, saved by the lead from the message it sent (2026-10-27). Commits 1222ab21, ec7d7ea7 on audit/u35-cfr (on c3866e12).

CFr hand-back (U35 lane C, S/wt-u35cfr, branch audit/u35-cfr, on c3866e12). Not pushed. Nothing is uncommitted except stray state of other lanes (none of mine).

**Commits:** 1222ab21 (audit/sweeps/plant.py, plant_set.py, plant_twin_gate.py, plant_faults.py, plant_notes.json, audit/b3/faults.md), then ec7d7ea7 (5 test files, new or changed test functions only).

**Counts (faults.md):** 111 planted: 90 biting, 10 fixed, 5 equivalent, 6 open. 39 rows not planted. That is 28 src modules "not planted: straightforward logic", with the owner's ruling quoted once in the method line, plus 6 non-src groups, K.03, K.21/22, the bench gate, fram_two_entries and Run 11. 2 further rows are open (modlwip, system:441). No widening. Product findings routed: 0.

**Fixes.** Each is red on its re-plant (S/u35/laneC/cfr/replant.jsonl, logs in plant_logs/), green unplanted at -1 and 32768, with 0 memory markers:
- K.04-drop: test_the_task_budget_steps_once_past_its_max_and_stops.
- K.28-seq flip and drop: test_the_error_sequence_wraps_from_its_top_to_zero.
- K.29 gamma/gating flip and drop (4 plants): test_both_estimator_uptimes_stop_at_the_uptime_limit.
- K.20-log-flip: test_get_timestamped_chunk_allocation_succeeds_at_exact_remaining_capacity_boundary.
- K.04-flip and K.04-trigger-drop:
  - First pass: caught only by the file timeout (124 at both stages, 300 s each). The record classes them as CF1b's class.
  - Fix (item 5 (2)): test_a_command_accepted_while_the_escalation_logs_keeps_its_own_reset now polls `reached` within _RUN_BOUND_S. Both re-plants then fail by assertion in about 45 s.
- The uart file's run bound was found landed: the test already calls run(..., _RUN_BOUND_S).
- Item 7: the uart test is renamed to test_an_allocating_read_started_before_its_bytes_arrive_returns_them_all. Its assertions are unchanged.

**Equivalent:** K.bins-total-flip, K.02-06-08-flip, K.12-down-flip, K.28-merge-flip, K.42-flip. In each, both forms land exactly on the cap.

**Found landed:**
- The neopixel :184 exact bound (test at :619).
- The notification sample-age bound (F2r). Both plants are red.

**Open, each with its proposal in faults.md:**
- K.25-mask-drop: no test crosses the wrap.
- named.fram_alloc: red at -1 but green at 32768, so the allocation-budget test misses a 16-byte per-call allocation at the threshold stage.
- Exact-bound survivor asy_isl29125_driver:569, plus fram erase_yield, framing decode_yield and uart_link recovery_window.
- Item 6 (system:453-454, reachable by a cancel): my drafted direct test hung inside its own run bound (probe log S/u35/laneC/cfr/probe_test_a_cancel_of_the_shutdown_task_before_the_supervisor_stops_ends_the_sequence_there.log, rc 124). It is not committed and the reading is not settled.
- Item 5 (5), the modlwip control: not run, because the budget was spent. S/u35/laneC/cfr/modlwip_control.sh prep|build|test|clean is ready: make -n check, one private compile in a tc-int copy, test, removal.

**Other items:**
- pair_scan, retargeted to test_fault_or_warning_never_both.py: red.
- fram_two_entries: not applicable, the requirement is dropped by the owner.
- Run 11: re-established by the 2026-10-26 calibration (suite :208-209). Not re-run here, because no twin CI runs against the shared toolchain.
- Gates:
  - unit (`_flag_memory_errors` on the file's real log), twin (`_check_no_memory_error_in_log` on a real dev twin boot) and flash (`--twin`): each red on both markers, with its unplanted control green.
  - bench: skips under --twin, so it is not plantable there (reason in the row).

**Lead's notes:**
- (1) plant.py now starts each run with start_new_session=True. On a timeout it kills the whole group with os.killpg. A run that any process outlives fails with rc 125. A /proc cwd scan between plants stops the run on a stray. `plant.py selftest` passes on a timed-out run and on one that leaves a child.
- (2) The hung UNPLANTED base runs of test_asy_system_service.py were on snap2. The root cause is my own draft cancel test: run alone, it hangs at 60 s. It is dropped. On snap3 the base is green at 24.07/25.03 s.
- (3) Every plant whose base was that hung run (only K.04-flip, in replant_draft.jsonl) was discarded and re-run on snap3.
- Runs that met the timeout: first pass K.04-flip and K.04-trigger-drop (both stages); snap2 base.system_service and K.04-flip. No other run.
- ps after the last run: no process of mine. The remaining interpreters belong to lanes crr1b/crr1c and crr2 (cwd checked).
- Copies and snapshots are removed, and /dev/shm/cfr_plant is gone.
- My earlier runs used nohup, and I once used rm with an unguarded "$S" glob; neither is repeated.

**Checks:**
- ruff on the 5 files: clean. mypy src tests (S/shared/typings link, removed after): clean.
- comment_cap, citations, decision_vocabulary, tunables_register and the 12 tests_scripts readers of the changed files: 1112 passed.
- Silent-failure scan: no except in my additions, and every test asserts values.

**After-times (-1 / 32768), against the first-pass bases on this host:**
- system_service 24.07/25.03 (base 24.24/25.43)
- voc 1.92/4.57 (2.12/5.53)
- print_log 0.42/0.42
- fram_manager 0.67/1.37 (0.62/1.47)
- uart_driver 4.98/7.73

None is over 10 % and 0.5 s.

**For D3:** K.10's planting rule should read: "Fault planting is for complex measurement tests (memory exhaustion, leaks, long-running accumulating processes, multi-layer or external dependencies, timing bounds, log gates): one targeted pass per such module in a throwaway copy, nothing kept; straightforward tests get none (owner, 2026-10-23)."

nothing of mine is running
