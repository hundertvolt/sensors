D2c hand-back (lane D, U35). Branch `audit/u35-d2` in S/wt-u35d2. One commit, `5392e71`, on top of `03c46b6`. I ran S/u23/rebuild.sh first. The commit touches only SPECIFICATION.md, CLAUDE.md, BACKLOG.md and tests_hardware/README.md. Nothing is uncommitted and nothing is pushed.

**Where each owner answer now lives** (owner's words and the question quoted from REGISTER.md's three U33 rows):
- **Q1 (a), the grkizi crash:** SPEC A.10's "Automated CI suite" paragraph.
  - A signal death fails its check by name (`exit_reason()`), and nothing reruns a twin job. The condition's check is logged as (agent, 2026-10-21).
- **Q2 (a), reboot with no free alarm:** SPEC C.9's read-trigger failure path, with the owner's words.
  - C.4.1's "A restart is not free" has a short dated pointer to it.
- **Q4 (a), SCD30 soft reset at every start:** SPEC A.4's SCD30 start sequence, with the owner's words. M.2 has a dated pointer.
- **Q3 (a), the extra-write flag:** SPEC C.8, CLAUDE.md's `scd30_extra_write` sentence, and three README places (the flag comment, the gates-table row, the budget row gaining "up to 12 in all").
  - Named change: C.8's one-write-per-session cap (owner, 2026-09-16) keeps its words, with the 2026-10-21 decision named beside it.
- **Q6 (c), comment-line length:** CLAUDE.md's "How a block is counted" gains the length rule (stripped length over 120, rounded up), quoting "6: c" as the relay and the cap test do.
- **BACKLOG.md:** questions 1, 2, 3, 4 and 6 are removed. The list keeps its heading and rule, and no question is open.

**Figures checked against tests_hardware/:**
- Four `scd30_extra_write` tests: flash test_bus_concurrency.py:201 (2 writes) and test_chip_conformance.py:174 (up to 3); bench test_bus_concurrency_under_api_load.py:322 (up to 3: 2 offsets and the restore) and test_sensor_config_push_over_real_hardware.py:202 (4). That is 12.
- Plus 1 under `persistence_write` alone (flash :99), so 13. Plus at most one `scd30_measuring` start command.
- `_ECHO_READERS = 3`; `_TASK_FAIL_*` 100/300; the alarm pool holds 16 (F.1).

**README items:**
- H3 loop-lag paragraph (:826): the flash test runs in the twin only, on 127.0.0.1:8080. Silicon's run is the bench test in BENCH mode "production", with the error log saved first.
- H3 twin-record habit row (:538): both GC stages, per-stage outcomes, a script charged per flash test.
- U3e (:1090): the "not written" sentence is replaced by the bench hazard run (collected, silicon run owed).

**Beyond the brief, in my files:**
- BACKLOG's owed-work entry for the bench loop lag still named the flash test and "no concurrent API load". I fixed it as a consistency fix (agent, 2026-10-22).
- I added the bench hazard run's owed entry (LEAD NOTES 12: "D2 adds its owed row").

**Where the tree differed from the brief or relay:**
- CLAUDE.md no longer had the brief's quoted "a *second* SCD30 NVM write" wording; it read "beyond those `persistence_write` admits".
- REGISTER's line numbers have moved: `exit_reason()` is now `_twin_process.py:261-271`, Run 5c's check `_digital_twin_ci_suite.py:1396`, and the pin `test_digital_twin_ci_suite_errcount.py:657`.
- REGISTER quotes Q6's answer as "c"; the relay and the cap test quote "6: c".
- SPEC's `l3.loop_lag_window_s` row already names the bench timeout, so that half of H3 was already landed.

**Left (not my files):** H3's twin-record text in digital_twin/README.md:607-611 and HEAP_FRAGMENTATION_MEASUREMENTS.md:282. Then D2d: D1's open steps and the 17 scans.

**Checks:** two runs of 10 files (citations, decision_vocabulary, legacy_paths, device_script_bench_facts, comment_block_cap, lock_order, persistence_write_marker_completeness, tests_hardware_persistence_write_gating, task_inventory, timing_budget), one before and one after the commit. Each: 745 passed, rc 0, about 37-40 s, zero memory markers. The one warning is "datasheets/ submodule not initialised" in the worktree.

**Modes:** documentation only, so nothing changes in STA, AP, Silent, Off or USB on any device.

Logs and the edit scripts are in S/u35/laneD/d2c/. All runs were pure-parse pytest and all have exited.

nothing of mine is running