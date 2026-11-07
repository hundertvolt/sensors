U30 lane X FINAL
Commits on audit/u30-x (S/wt-u30x, nothing pushed): 0c09556 (the new tests_scripts/_await_depth.py, test_await_depth.py and test_memory_catalog.py; c_stack_budget.py drives GET /status and wraps get_register_into), da4eb2f (the docs: SPECIFICATION.md minus Part N, CLAUDE.md, BACKLOG.md, DEVICE_REFERENCE.md, HEAP_FRAGMENTATION_MEASUREMENTS.md, digital_twin/README.md, tests_hardware/README.md), c1e3e5f (c_stack_budget.py asserts the 200; README says so).
Steps:
- Applied: 1, 4, 5, 6, 7, 16, 20, 21, 30, 31, 77, 85, 86, 112, 115, 117, 118, 119, 121, 122.
- 3 checked, with R-35 applied. 114 confirmed by grep: no listed tag missing.
- 136 and the option-1 wording are left at f594679, because ## V and ## L were still empty at hand-back. Run 12 has no stack cell yet. Fold (6) states the unit tier's W1 level, with option 1 as the target.
- Rulings: R-8 (DEVICE_REFERENCE quotes '1 b' and '2 b' with their questions), R-33 (C.7's part only), R-34 (CRC 160/416 B kept), R-35 and R-36 (await-depth rules), R-32 (owner quote; landed state described only from relay lines).
Code wins over packet: the lead's relay was right that tests_hardware/README.md:938 stays as written. Only row 5 (:817) was stale, and I rewrote it.
Seen failing first (logs in S/u30/laneX/):
- memory catalog: an unlisted planted site failed by name (seen_failing_memory_catalog.log, bite_memory_catalog.log).
- await depth: a planted 29-level chain failed (bite_await_depth.log).
- wait_for, async with and inherited-receiver rules: each failed before its fix (bite_await_rules.log).
- Nothing planted was committed.
Result: 38 task tops, 44 chains; deepest 28: GET /status → Microdot dispatch → _system_status → NTP config read → config log → FRAM write → lost chip → FRAM manager log. Pinned as `# @tunable mem.max_await_depth = 28`.
Checks on the final tree (S/u30/laneX/scans_2.log):
- 18 tests_scripts files (16 scans plus both new tests): 851 passed, 2 expected reds (both under ## X):
  - test_decision_vocabulary::test_the_allowlist_only_shrinks: stale rows 28 and 71 of tests_scripts/_decision_vocab_allowlist.txt; the lead deletes them.
  - test_tunables_register: mem.max_await_depth has no Part N row; the row is in the relay.
- ruff clean; host mypy clean (3 files); main mypy clean (260 files).
- Device-script and doc checks after c1e3e5f: 768 passed. collect-only 196/226.
Times: test_await_depth 4.4 s, test_memory_catalog 1.2 s; citations about 10 s (base 13.3), vocabulary 8.4 (8.8), cap 4.4 (4.35), tunables 3.5 (5.3).
Silent-failure scan (S/u30/laneX/silent_failure_scan.log):
- class 4, found and fixed in c1e3e5f: Microdot turns a raising handler into a returned 500, and c_stack_budget.py discarded that response. Swept project-wide: no other site.
- class 3: an await the analysis cannot resolve counts one level, now stated in F.1 and guarded by the walk-reach test.
- class 3: the catalog check sees only stores on self; I.2 states that scope.
Relay lines written under ## X:
- the Part N row for mem.max_await_depth, with its tunables red;
- the two stale allow-list rows;
- the note that 136 and the option-1 wording stay at W1 until V and L land.
Decisions (agent, 2026-10-20):
- c_stack_budget runs GET /status in-process through the app's dispatch_request() and asserts the 200.
- invoke_handler is modelled per context: "errors" from error_response, "all" otherwise.
- An unresolved callee counts one level.
- Fold (6) states the W1 unit-tier level, with option 1 as the target.
Runs: one dev-twin fram_peak.py (ResetErrors FRAM-buffer peak 50,464-58,816 B, now in I.2), rc 0, 0 markers. RUNS.md has start and done lines. Nothing of mine is running; the typings symlink is removed.
