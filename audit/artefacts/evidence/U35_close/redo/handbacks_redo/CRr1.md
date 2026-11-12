CRr1 hand-back, saved by the lead from the message it sent (2026-10-26). Commits 945c7c8f, 353bd29a on audit/u35-crr1 (on c3866e12).

U35 lane CRr1: hand-back (block stopped at a seam after about 95 tool calls)

**Commits** on audit/u35-crr1 in S/wt-u35crr1. Not pushed. Nothing is uncommitted.
- 945c7c8f: the tool and the rows. audit/sweeps/redflags.py, review_rows.py, review_verdicts.json, and audit/b3/review.md re-rendered with its header kept.
- 353bd29a: the 10 fixes, item 6, and the verdict update.

**Counts** (rendered by review_rows.py): 8,467 rows, 345 flagged now (355 before the fixes).
- **By level:** unit 3,920; host 2,899; twin 662; web 492; twin scenario 174; bench 121; device script 90; flash 88; manual 21.
- **By verdict:** biting 8,194; CRr2 178; justified 73; fixed 10; weak 12 (open); blank 0; lead 0.
- **By flag:**

| flag | rows |
|---|---|
| no_assertion | 23 |
| weak_only | 1 (5 before the fixes) |
| except_pass | 7 |
| log_existence_only | 13 (17) |
| loop_vacuous | 60 (62) |
| wide_tolerance | 7 |
| name_overclaims | 8 |
| helper_swallows | 42 (one helper, `_retire`, justified) |
| same_callee | 36 |
| ns_seed_text | 39 |
| ns_allow_list | 4 |
| setup_credit_only | 38 |
| hw_no_log | 83 (all CRr2) |

  cannot_fail, canned_return, ns_count_bound and ns_code_in_set have no row at this base.
- **Detector tests:** `python3 -I audit/sweeps/redflags.py --self-test` runs 22 cases. They cover facts read through f-string keys, a subscript index never read as a literal, dispatch through a table, `globals()`/`getattr` with f-strings, a loop over an imported check table, a raise in the test or in the code under test (never credit), and a JS string that contains `expect(`.

**Fixes.** Each bite applies one input edit; the old form passes and the new one fails. Logs are in S/u35/laneC/crr1/: bites_old.out, bites_new.out, bites_new2.out, ceiling_bite.out.
- dns `ipv4_to_int`: values hand-computed from RFC 791.
- math wet bulb: Stull 2011 eq. 1, hand-computed.
- system_service `_start_task`: returns the starter's own task.
- wifi: the LED flash task is running.
- bmp3xx ×2, webserver reclaim: exactly one persisted entry of the right type.
- isl29125 partner read: ErrCount 2 in one READ slot. My first guess of 1 was wrong: the calibration reads twice (src/asy_isl29125_driver.py:542-546, the third leg always runs) and a repeated code raises the count without a new slot.
- notification: every written field is named Valid.
- tests_scripts ceiling test: one result per path.
- **Item 6:** tests/_stack_overflow.py replaces the four copies.
- **Runs:** all 9 MicroPython files pass at both GC stages with zero memory markers (S/u35/laneC/crr1/files_both.out, runs/). ruff is clean. Main mypy (136 files) and host mypy (309) are clean with a cold cache. comment cap, citations, decision vocabulary, tunables, code conventions and coverage_runner: 733 passed.
- **Not done:** the after-times are not compared with base_testsh_m1.log; no file gained a test.

**Open, with state:**
- **12 weak rows**, planned fix in review.md:
  - tests/test_asy_base_classes.py :2941 and :2983 (`_err_count >= 1`) and :2969 (no-op checks nothing).
  - tests/test_asy_fram_driver.py :1385, :1397, :1407, :1420, :1432 (a code merely present in the history).
  - tests/test_digital_twin_http_client.py :392.
  - tests/test_asy_ntp_client.py :1831 (the 12 h fallback is never asserted).
  - tests/_sensortask_scenarios.py :2785 (start_tasks is never spied).
  - tests_js/site-functions.test.js :135.
- **Item 6:** the settrace/coverage-runner run of the four files is not done.
- **Item 4, CR2 cross-check:** my scan re-finds CR2's fixes in bmp3xx, dns, isl29125, notification, system_service, wifi, math_helpers and _sensortask_scenarios. It finds nothing to fix in tests/_generated_tree.py, test_asy_sgp40_driver.py or test_asy_uart_comm.py. That is unexplained, because CR2's diff is lost.

**Item 5:** `_restore_is_all_or_nothing` (scripts/_digital_twin_ci_suite.py:790) is dead suite code. No run calls it: Run 5b (:1339) asserts the exact ring, and the cut-write case moved to tests/test_digital_twin_fram_crash_points.py. Its only caller is tests_scripts/test_digital_twin_ci_suite_errcount.py:105-128. I changed nothing; removal is yours.

**For CRr2** (5 rows besides the device scripts and hw_no_log):
- flash test_bus_concurrency :291: the chip-lost errnos fact should be exact.
- bench test_hotspot_role_reversal :319 and test_network_resilience :560: the allow-lists should become an exact count of the provoked entry.
- bench :258 (test_network_resilience) and :118 (test_wifi_networking): read the provoked entry before the clear.
- bench test_uart_link_under_api_load :93: `intact == total` also passes when both facts are missing.

**Normal-situation scan:** no (a) found, so no product question. The U11 seed texts are gone from the tiers and the twin suite, and SGP40's first boot logs nothing (landed). CR3's unread CONFIG_LOST question (flash test_system_commands :117) was not re-examined.

**What the scan cannot see** (also listed in review.md):
- whether a credited assertion actually runs (branches, callbacks), and credit that comes through fixtures;
- helpers reached through parameters, and same-named methods (any match credits);
- canned values passed through the code under test;
- scripted values inside a tight bound;
- expected values copied from the code by any means but a same-named call;
- mutation strength;
- for JS: no AST, helpers matched by name only, nothing imported from js/, and an expect inside a callback is credited whether it runs or not.

nothing of mine is running
