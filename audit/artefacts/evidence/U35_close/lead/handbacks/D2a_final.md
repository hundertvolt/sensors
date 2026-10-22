D2a hand-back (lane D, U35). I worked on branch `audit/u35-d2`, created at `e06966b`, in worktree `S/wt-u35d2`, and ran rebuild.sh on it (rc 0). There is one commit, `8453305`, and it changes only SPECIFICATION.md. Nothing is uncommitted and nothing is pushed.

**Each check, red on `e06966b`, then green on `8453305`:**
- **test_tunables_register:** red with 16 tags that had no Part N row, plus the `l1.notification_neopixel_wait_until_timeout_ms` row that had no tag. Now 15 passed.
- **test_level_containment:** red on `fault_storm`, `ntp_unreachable_load`, `reader_saturation` and `watchdog_fault`. Now 26 passed.
- **test_task_inventory:** 4 red. The `_two_initiations()` row in C.9 turned all four green, the NeoPixel self-tests included. Now 6 passed.
- **test_threat_model_statement:** red on `UartHazards`. Now 4 passed.
- **test_memory_catalog:** green on base as well (the lead's allow-list entry had already landed). I added I.2's entry anyway. 22 passed.
- citations, decision_vocabulary, legacy_paths, task_tops, lock_order, timing_budget and toml_schema_contract are green, as are the other before-commit checks.
- **The 17 repo-wide scans, run once:** 1 failed and 877 passed in 57.9 s. The one red is the expected `test_comment_block_cap`, at `tests/_sensortask_scenarios.py:477` (lane V's). No output contains a memory marker.

**What I changed:**
- **Part N, 16 new rows:**
  - `config.flush_slice_bytes`;
  - `uart.hazard_quiet_timeouts`, `uart.hazard_window_timeouts`, `uart.hazard_recovery_attempts`;
  - `l1.uart_comm_hazard_clean_transaction_virtual_ms`, `l1.asy_uart_link_driver_hazard_run_virtual_ms`;
  - `l2.uart_link_hazard_readers`, `l2.uart_link_hazard_write_pause_ms`, `l2.uart_link_hazard_read_period_ms`, `l2.uart_link_hazard_run_virtual_ms`;
  - `l2.zero_think_reads_per_reader`, `l2.zero_think_reader_floor`, `l2.zero_think_writer_period_s`, `l2.ntp_unreachable_write_period_s`;
  - `l4.memory_stress_bench_loop_lag_script_timeout_s`, `l4.uart_link_under_api_load_hazard_run_timeout_s`.
- **Part N, withdrawn:** the `l1.notification_neopixel_wait_until_timeout_ms` row. No other row named it.
- **Part N, restated:** `l2.bus_hazard_concurrency_flap_window_s`, `l2.twin_wdt_feed_interval_s` (×4 now also bounds one SCD30 cycle), `l2.timer_pool_wait_s` (driven seconds; the reboot case stays real), `l2.hot_replug_wait_s`, `l3.uart_idle_poll_rate_cancel_settle_ms` (R2's twin figures) and `l3.loop_lag_window_s` (now names the bench timeout, per H3's line).
- **E.6.6:** four new rows: `fault-storm-persisted-writes`, `ntp-unreachable-under-load`, `reader-saturation-floor` and `watchdog-fault-planted`. Each names its partial L3/L4 counterpart and why it falls short. I restated `uart-hazards-under-api-load` with the L2 and L4 tests, the owner's 2026-10-21 quote, and the two hazards left out of the mode.
- **Other sections:** a "Hazard initiations" task row in C.9, `UartHazards` in A.11 (dev only), and the run-phase sentence for `_hazard_facts` in I.2.

**Sources I used:**
- Relay TAG lines: N3, H2, U3a ×5, P3, P4, U3d ×3, U3e ×2, T3g ×4.
- Other relay lines: V1, R2, H3 (the `l3.loop_lag_window_s` part only), U3e (E.6.6, C.9, I.2, A.11), U3f (C.9 and the constant name).
- LEAD NOTES 30, 49, 55, 57, 59, 68 and 70. I checked each claim against the tree and the pinned littlefs config (`extmod/vfs_lfsx.c:102`).

**Where the tree overrode the relay:**
- The P3 tag is now `config.flush_slice_bytes` (P4).
- The clean-transaction bound is 4, not U2's 14.
- The recovery constant is `_HAZARD_RECOVERY_ATTEMPTS`.
- U3e's `asy_uart_driver.py:472-475` reference moved to `init()` at :443, and `_two_initiations()` now sits at :218-228.
- The SPEC line numbers in the relay are all shifted (11780→11787, 5528→5535, 12629→12636, 12374→12381).
- The comment above H2's tag omits "and the teardown". I kept the relay's fuller basis.

**Decisions (agent, 2026-10-22):**
- The four new E.6.6 rows are recorded as exceptions with "a gap until written" wherever a counterpart is technically possible.
- I listed `UartHazards` under A.11's accepted limitation with its own actor tag.
- I left `uart.flash_hold_max_ms`'s stale basis ("5 erases + 43 programs as one stretch") for D2b, together with P3's F.3 and J.6 prose, because they are one group of facts and no check reads that row.

**Left for D2b:**
- P1 and the lead's P1 line: E.5.1.
- C4: A.8, F.1, the stale lines and BACKLOG question 7.
- U2: J.7's latency sentence.
- P2b: the FRAM sentence.
- Q2: E.1.
- P3/P4: J.6, F.3 `stall.flash_program` (:6427), the J.6 "littlefs runs without yielding" sentence (:9490), A.4, C.7.3, and the `uart.flash_hold_max_ms` basis.
- H3: the README and twin-record texts.
- U3e: the J.7 "not written" sentence (now about :9614), the A.8 UartHazards sentence, G.2's `_run_status_cmd()`, BACKLOG question 5, and README :1083.
- U3f: the None verdict in J.7 and A.8.
- R2: J's E22 fact.
- Block K: CLAUDE.md's length rule and BACKLOG question 6.
- T2b: E.9's window, and Run 3 as a reader of `rate.persisted_log`.
- D1's open steps.

**Modes:** this is documentation only, so nothing changes in STA, AP, Silent, Off or USB on any device. `UartHazards` is described as dev-only, reachable in STA and AP.

**Runs:** only pure-parse tests_scripts pytest files (total about 1:11 for the pre-commit set, 57.9 s for the scan), all exited as listed above. I changed no test file, so there are no paired times. Logs and helper scripts are in `S/u35/laneD/d2a/`.

nothing of mine is running