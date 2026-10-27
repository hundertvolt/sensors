CRr1c hand-back, saved by the lead from the message it sent (2026-10-27). Commits d420e6ee, 0279d5d4 on audit/u35-crr1b (on 4d6cf385).

CRr1c hand-back. All items are done and committed on audit/u35-crr1b (worktree S/wt-u35crr1b), not pushed:
- d420e6ee "U35 lane CRr1b: twelve weak tests pinned to exact outcomes": CRr1b's six files, kept as written.
- 0279d5d4 "U35 lane CRr1c: exact UART fault entries, the removed-TOML case, a dead suite helper gone": items 4, 5 and 6.
Nothing is uncommitted. The only untracked entry is the shared node_modules symlink (to S/wt-base/node_modules). S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; logs are in S/u35/laneC/crr1c/{r1,r2}.

**CRr1b's diff:** I reviewed all 12 edits. Each keeps its test's goal, and the JS expectation matches all six devices' generated definitions. Nothing needed fixing. Its mkbites.py was never written (the refused command never created it), so I wrote my own bite generators, tools/mkbites.py and tools/mkbites2.py.

**Item 1 bites:** one scratch copy per bite, each limited to the bitten test. In every case the old form passes and the new fails at its own new assert line. Logs: r1/bite_<name>_{old,new}.log, and r2/ for the scenario and JS bites.
- base_classes:
  - :2941 and :2983: the request is repeated, so the old `>= 1` passes and the new `(1, 1)` fails.
  - :2969: the key changed to SampleInterval, which triggers the correction write.
- fram :1385, :1397, :1407, :1420, :1432: the scenario runs twice (WRDI with drop_next_wrdi 4).
- http :392: n 3 → 2.
- ntp :1831: `ntp_interv = [11]` planted in a scratch copy of the module.
- Scenario :2785: `sysfunct.start_tasks([], [])` planted in a scratch copy of the generated sensortask_wozi.py.
  - Its first attempt failed in both forms. Root cause: `_watchdog_timeout_ms()` (tests/_generated_module.py:79) reads `sensortask_wozi_main.py` from beside the module, and the bite directory lacked it. A harness gap, not the test.
  - With that file copied in, old passes and new fails.
- JS: SSID's kind set to readonly. Old: 6 passed; new: 6 failed.

**Item 2 runs** (base = CRr1b's basetree, which I checked equals 4d6cf385: 0 of 344 tracked files differ, and the generated tree is identical):
- test_digital_twin_http_client: 38/38 passed, 0.1 s at both stages, base and head.
- test_sensortask, base and head at -1 and 32768: 105/105 passed on all six devices. Times: arzi 32/37, dev 50/60, grkizi 36/42, klkizi 35-38/42, schlafzi 36-38/42, wozi 40-41/48-49 s.
- `npm run test:unit` in the namespace: rc 0, 202 s.
- Zero memory markers in every run, and no file more than 10 % slower.
- The container restart at about 00:32 cut run 1 during grkizi's head half. Every unfinished item was re-run in run 2 (grkizi in full, so base and head stay back to back).

**Item 4:**
- (a) Added `test_a_toml_removed_after_the_generation_is_refused` to tests_scripts/test_generated_tree.py. With `len(current) != len(recorded)` dropped from a scratch copy of tests/_generated_tree.py, the new test fails and the other 14 pass (r2/pytest_gentree_bite.log). The head file passes 15/15.
- (b) Values read from a probe run first (r1/uart_probe.log): every one of the six faults logs exactly one entry with ErrCount 1.
  - A new `logged()` helper returns (ErrCount, used slots); `persisted()` now delegates to it.
  - Each of the six sites (:567, :616, :636, :2268, :2854, :2977) asserts its exact entry, for example `(1, [E89])`. The two "not in" controls in the same tests are now `(0, [])`.
  - Bite: `_err` logs every event twice in a scratch copy of src. The old forms pass 6/6, the new fail 6/6 (r2/bite_uart_exact_*).
  - Timing, base vs head: 62.3/63.3 s and 62.3/63.6 s, 202/202 passed, zero markers.

**Item 5:** `_restore_is_all_or_nothing` and its four tests are removed. `_non_empty_slots` and `_counter` stay, because other runs reach them (Run 5b, Run 5c's loss sweep, and more). Nothing else reached the helper (git grep, getattr strings, run table), and no README or SPEC line named it, so nothing is owed to D3r. Its SUITE_ROWS entry now reads "removed".

**Item 6 and checks:**
- The 12 rows are now `was:<flag>` → fixed; the six uart_comm rows are `was:log_existence_only` → fixed, marked as hand-read. The new generated-tree test is unflagged and renders as biting.
- Counts: 8466 rows: CRr2 178, fixed 28, justified 73, biting 8187; weak 0. 8466 rather than 8464 because the base review.md was stale by two rows: the T4r2c merge added two tests without re-rendering it.
- Passing: ruff (lint_direct), all six mypy passes (cold cache), npm lint and typecheck, lint-ceilings, `review_rows --check`, and 1080 tests_scripts readers plus the four convention checks.
- One red, mine and fixed: the comment cap counted my docstring line as 2 (127 characters against its 120 wrap). Reflowed; the cap passes and the file passes 15/15.
- Not run: the silent-failure scan (CHECKLIST 16), since the brief names no modes.

Runs: run1 was cut by the restart (RUNS.md has a note line); run2 exited 0; run3 (the JS bite) completed. Scratch tree copies are deleted.

nothing of mine is running
