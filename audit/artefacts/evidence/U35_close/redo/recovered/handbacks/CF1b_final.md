CF1b hand-back (U35 lane C, audit/u35-cf in S/wt-u35cf). Not pushed. Nothing is left uncommitted.

**Commit:** 99fc7d3 on 328c80d, "U35 lane CF1b: the owner-scoped plant pass, direct tests for its survivors". It changes audit/b3/faults.md, audit/sweeps/plant.py, audit/sweeps/plant_named.json and six tests/test_<module>.py files. My changes are new test functions only.

**Scope (owner, 2026-10-23, your relay, applied as you gave it).** Planted: the named bites, the boot entry's five, every K row, CF2's named items and 27 seeded picks. Each of the 27 is named in faults.md with its reason (memory, leak, timing bound, soak, log gate or accumulation). The other 108 seeded picks read "not planted: straightforward logic (owner, 2026-10-23)". The method line quotes the owner's words and records that there is no widening (agent, 2026-10-23).

**Counts:** 226 rows (217 plus 9 new: A.U23.25, .27, .41, K.42, K.43 and K.53, two plants for each K row).
- 118 planted: 96 biting, 12 fixed, 5 equivalent, 5 open.
- 108 not planted.
- Routed product findings: 0.

**Fixes.** Each new test is red on its re-plant, green unplanted, and has zero memory markers at -1 and 32768:
- K.20-log flip (asy_fram_manager.py:748): test_get_timestamped_chunk_allocation_succeeds_at_exact_remaining_capacity_boundary, red at :1675.
- asy_fram_manager.5 (the erase loop's sleep(0) dropped): test_erase_chip_lets_another_task_run_between_every_two_units, red at :1701.
- asy_framing_codecs.4 (the decode loop's sleep(0) dropped): test_cobs_decode_lets_another_task_run_after_every_code_block, red at :49.
- K.28-seq flip and drop: test_the_error_sequence_wraps_from_its_top_to_zero, red at :313.
- K.29-gamma and K.29-gating, flip and drop (4 plants): test_both_estimator_uptimes_stop_at_the_uptime_limit, red at :466.
- asy_uart_link_driver.4 (the recovery-window sleep dropped): test_each_recovery_try_first_waits_one_window, red at :481.
- K.04 drop: test_the_task_budget_steps_once_past_its_max_and_stops, red at :3141.
- The 12th fix is CF1's asy_crc_checks.4.

**Equivalent.** K.28-merge flip; K.bins-total flip and asy_base_classes.2 (the same site: total() is COUNTER_CAP either way); K.02/06/08 and K.12-down from CF1.

**K.42, K.43 and K.53 caught.** K.42 by test_bounded_log_counts_what_it_drops_and_saturates_at_the_cap, K.43 by test_prst_count_stops_at_the_target, K.53 by the vitest test "steps SysUptime and WifiUptime … saturates both at COUNTER_CAP". The three A.U23 plants are caught by their real-tree tests; their own in-file bites are cited.

**Open, for the next block** (test files, U35's):
- Three exact-bound survivors, each with a proposed driven or frozen-clock test in faults.md:
  - asy_isl29125_driver.py:569
  - asy_neopixel_driver.py:184
  - asy_notification_service.py:230 (test_a_stale_producer_sample_is_not_evaluated skips the exact age).
- named.fram_two_entries (A.U3.04): no test fails the CRC-computation path in _write_chunk() (asy_fram_manager.py:415) with an entry count. Proposed: inject a None from add_into() and assert exactly one FRAM_CRC entry.
- named.pair_scan (A.U3.11): its L0 scan, tests_scripts/test_one_entry_per_event.py, is absent from the tree. That check is owed before the plant can be re-run.
- Caught only by the file timeout, because the test hangs (its wait has no bound): K.04 flip and asy_system_service.4 at test_asy_system_service.py::test_a_command_accepted_while_the_escalation_logs_keeps_its_own_reset, and asy_uart_driver.5 at test_asy_uart_driver.py::test_a_caught_allocation_failure_in_a_poll_or_teardown_prints_its_own_text. Proposed: give each a run bound.
- A.U21.13's modlwip control: not run. Its cost is one private compile: apply_unix_lwip_host_override()'s make variables minus the modlwip swap, with BUILD= and the overrides directory in /dev/shm, after a `make -n` check that nothing outside BUILD is written. The build otherwise runs in the shared checkout's ports/unix and writes the overrides into /root/pico-toolchain/build_overrides. Then tests/lwip_host/test_modlwip_eagain.py runs on it.

**Deviations (agent, 2026-10-23).**
- main5 was stopped by the stop file for the scope change and relaunched on the trimmed list.
- A vitest parse bug crashed main6 at K.53 (an IndexError); its finally restored the copy.
- The resume loader misread vitest baselines as red, so two invalid K.53 records were written. I moved them to laneC/cf/k53_invalid.jsonl and re-ran K.53 (caught).
- The copy matched the tree before I removed it.

**Checks:** ruff clean; mypy main pass clean, both forms (231 and 265 files); the 12 doc checks pass (803 passed); silent-failure scan: no class applies (no except in my additions; every test asserts values).

**After-times (-1 / 32768), against the base table:** fram_manager 0.78/1.66 (base 6.5/8.6); framing 0.66/0.74 (0.82/1.03); print_log 0.41/0.43 (0.42/0.51); voc 2.50/5.85 (3.86/17.8); system_service 25.2/26.5 (23.7/27.4; +6.5 % at -1, but the base held 137 tests and the file now holds 190); uart_link_driver, paired against HEAD's file: 3.71–3.75/5.25–5.31 against 3.53–3.57/4.91–5.02 (+5 %/+6 %). No file is over 10 %.

**For D3:** none.
nothing of mine is running

[Lead's notes, 2026-10-23, LEAD NOTES 145: named.pair_scan's scan is not absent but renamed and narrowed (audit/consolidation/M_TSC.md M.TSC.111, tests_scripts/test_fault_or_warning_never_both.py); named.fram_two_entries' requirement A.U3.04 is dropped by OR140.a (7) (audit/actions/FOLD_BRIEF.md F11). The notification:230 survivor went to F2 item 2; the rest to CF1c.]
