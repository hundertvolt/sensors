# Lane T hand-back (the agent's final report, verbatim)

Lane T, commit 0151a7a on audit/u29-t (S/wt-u29t, base b3d25ae): 9 files, all in files_T.txt. Logs are in S/u29/laneT/.
Steps:
- 1: applied. New guard tests_scripts/test_retry_counts.py puts every tagged _attempts/_retries/_rebinds count in one table with three classes. "timeout retry" must be 3 attempts or 2 retries: runner.per_file_attempts and l0.vitest_timeout_retries. "event retry, outside the rule" is held at its recorded value, each reason ending "not a timeout retry". "a bound": the l1/l2 UART recovery counts and l4.network_resilience_over_ceiling_attempts. An unclassified count fails by name, and both tiers must loop on their count.
- 2: applied. The pytest tier retries 124, or 137 past its bound, up to max_attempts. It has its own loop without the memory gate, because a failing tests_scripts check's source prints its marker in pytest's traceback (gate_misread/pytest_q.log). The run record is removed before each attempt. RETRIED-PASS shows as "Passed only on retry", "L0 PASS (retried 1)" and a root-cause item. The annotation fires only on FAIL. max_attempts moved up, unchanged.
- 3: applied, `retry: {count: 2, condition: /^(?:Test|Hook) timed out in \d+ms/u}`. Deviation from the brief: the condition is a RegExp, not a string. vitest 5.0.3 types SerializableRetry.condition as RegExp, and the runner retries only on `instanceof RegExp`. Browser mode turns it into a string and back (sources in relay ## T). _summary_reporter.js's `retry?.count` already covers the object form (proof shows "attempt 2/3").
- 4: cancelled by the owner. No count changed; all four hardware files are byte-identical to b3d25ae. tests_hardware/README.md corrected as fact only: the join keeps five attempts on the nmcli rescan race; the cause of the 2026-09-08 exhaustion is open and goes to the next hardware round; the AP-reconfiguration theory is stated as ruled out. I checked this against 4d06553, BACKLOG #9 and src/asy_wifi_service.py:380-388/716-724.
- 5: applied. SPEC E.3.1 rule paragraph (owner's "Simply put..." first, then "The retry logic is for tests running into timeout.", "Firmware stays unaffected."). Also E.1, B.10.1, and the Part N rows per_file_attempts, tests_scripts_timeout_s and the new l0.vitest_timeout_retries. CLAUDE.md gets one sentence in the backstop bullet.
- 6: applied (see Budgets).
- 7: applied. The ruff exemptions check now names all four exemptions, and E.2.1 has the device-independent case.
Recorded reasons of the four counts, unchanged: hotspot 5 (nmcli rescan misses a just-seen hotspot), picotool 5 (no BOOTSEL device enumerated yet), association 2 (one association can fail outside the DUT, 1 miss in 3 runs, 2026-09-19), heap-probe rereads 3 (probe pins its own buffer through a stale root). Each failure message reads its count from the constant or the loop.
Seen failing first / proofs:
- Guard on base: the two tiers only (tier not looping on max_attempts; l0.vitest_timeout_retries tagged nowhere).
- test_test_sh on base: hang-once got ('FAIL',1) not ('RETRIED-PASS 2/3',2); always-hang got 1 attempt not 3; base tail read RETRIED-PASS as "L0 FAIL".
- Bite (passed at once, so planted): "exit 1 not retried" caught a retry-on-any-exit test.sh; the guard bite caught a changed and an untabled count; a loose /timed out/u condition fails the JS check.
- summary-reporter on base: "expected undefined to be 2".
- Vitest scratch proof: timeout-once test and hook-once each show "Passed only on retry (attempt 2/3)"; the failed assertion ran once ("expected 1 to be 100"); always-timeout ran 3 attempts, then FAIL. Control run with the base config: all four FAIL.
Budgets (max(cold, warm + largest single retry) × 1.25, rounded up to 5):
- unit-tests-coverage 35 → 95: (14.15 + tier 3×1200 s = 60) × 1.25 = 92.7.
- unit-tests / gc-threshold stay 175: max(scenario 127.75, tier 60), 9.65/10.12 + 127.75 → 171.8/172.3.
- web-unit-tests / web-coverage stay 15: a live test's two retries (2 × 200 s = 6.7 min) now decide over the install's 5 min, 3.28/3.40 + 6.7 → 12.4/12.6; rows updated.
- put-matrix stays 15 (install still decides, retry 2 × 20 s); cross-browser-smoke runs no vitest.
Red checks: none, no allow-list line needed.
Silent-failure scan (both new, details in relay ## T): the guard cannot see untagged counts (scripts/_port_lock.py:13, lwip_host test:53, uart_comm_hazards.py:60, the _tries poll bound), none a timeout retry. A live test retried after a vitest timeout starts beside the uncancelled command of the timed-out attempt; a clash fails, it is never hidden (review item). The tier's 137 branch is copied from _run_with_retries and has no tier test of its own.
BACKLOG build-environment line owed by the lead: "scripts/test.sh: the tests_scripts/ tier retries a timed-out run up to runner.per_file_attempts (three attempts); vitest.config.js: retry { count: 2, timeout-message condition }; ci.yml: unit-tests-coverage timeout-minutes 35 -> 95 (agent, 2026-10-20)."
Times:
- test_test_sh.py 29.6 s → 31.2 s (+5.4 %).
- test_retry_counts.py 0.48 s; test_ci_workflow.py 0.30 s; summary-reporter.test.js 7.1 s.
Runs:
- rebuild rc 0, lock_check rc 0.
- 12 checks: 781 passed rc 0. Doc checks: 654 passed.
- Readers: 97 runs over 144 files, every test file green; the runner exited rc 1 only because three non-test modules in the list collected nothing (pytest rc 5). Zero memory markers.
- npm lint, npm typecheck, lint-ceilings, ruff, shellcheck, mypy host pass, actionlint, zizmor, collect-only tests_hardware: all rc 0.
- Nothing of mine is running.
