# U24 open findings, staged for the close records (one line each; evidence path; target = the unit that next works the file)
- OF-149 (TEST, open): unit-tests-coverage red on 37a259a, tests/test_digital_twin_sensortask_integration.py 14/15 under
  settrace, test unnamed (log truncated); did not recur on 9efb630; not root-caused, not a flake. Since 9efb630 the
  runner summary names a failing test. Evidence: S/u23/cifix/cov/.
- OF-150 (TEST, open): tests/test_voc_algorithm.py at gc 32768 takes 17.8 s on W1 and 28.5 s with only a no-op trailer
  change (29.8 s after U1's migration); -1 3.9 s. Per-collection cost 1.40 vs 0.79 ms with identical survivors;
  hypothesis py/gc.c mark-stack overflow + full-heap rescan (:567-578, :620-637), decided by layout. Ruling (agent,
  2026-10-13): not a U1 regression (the no-op change reproduces it); open, to make efficient where the file is next
  worked. Evidence: S/u24/laneU1/handback_U1.md, S/u24/laneU1/logs/.
- OF-151 (TEST, silent-failure class 4, open): sweeps swallow every exception, so a method raising before the bus
  passes: tests/test_asy_bmp3xx_driver.py:2423, test_asy_scd30_driver.py:2254, test_asy_isl29125_driver.py:4065 (lines
  at d00e02c). Fix: assert each call reached the bus or raised only what the fake raises, seen failing on a planted
  early raise. Evidence: S/u24/laneU1/handback_U1.md.
- OF-152 (TEST, open): SGP40's datasheet waits are recorded (FastAsyncSleep.slept) but asserted nowhere:
  src/asy_sgp40_driver.py _SELF_TEST_WAIT_MS, _GENERAL_CALL_RESET_WAIT_S. Fix: assert each against the datasheet
  minimum (cite table/page), as SCD30's soft-reset assert does. Evidence: lead check of d00e02c.
- OF-145/OF-146: decided (b) (owner, 2026-10-13: "1 b, 2 b"), target U30 (S/u30/carried.md).
- OF-153 (TEST, typing, open): tests/_src_const.py src_const() returns object, so every typed read carries
  `# type: ignore[assignment]` (lane U2). Fix: a typed form; then every such ignore goes at once (warn_unused_ignores).
  Target: the unit that next works the shared test helpers. Evidence: S/u24/laneU2/handback_U2.md.
- OF-154 (TOOL, efficiency, open): buildgen/source_ast.py `_parse`'s lru_cache keys on (source, filename) and holds 926
  trees, so test_buildgen_error_contract.py spends 17 s of 42 s tearing down 5.2M objects (key on the text alone: a
  SyntaxError is never cached); frozen_modules.compute_frozen_modules re-walks every file per call (49 of 57 s of
  generate_device under cProfile; 11.8M iter_child_nodes). Target: the unit that next works buildgen/. Evidence:
  S/u24/laneB/handback_B.md, S/u24/laneB/gen.prof.
- OF-155 (TEST, silent-failure class 4/6, open): with the timeout's first signal now SIGINT, a broad `except BaseException`
  can swallow it, so the file runs on to the hard stop (137): tests/_machine_contract.py:25, tests/test_fakes.py:99,
  tests/test_generated_boot_entry.py:61, tests/test_asy_system_service.py:3764,
  tests/test_digital_twin_unix_port_unretrieved_report.py:84, digital_twin/run_generic_integration.py:364 (lines at
  e262d67's base); microtest's drain is still unbounded (an interrupt there is named now). Target: the unit that next
  works each file. Evidence: S/u24/laneK/handback_K.md.
- OF-156 (TEST, open): tests_js/live-backend.test.js:9 `SMOKE_TIMEOUT_MS = 45000` is a tuned test budget with no
  @tunable tag or Part N row (the docs lane's N.1 reading; a row shaped like l0.live_restart_recovery_timeout_ms with a
  measured basis). Target: the unit that next works tests_js. Evidence: S/u24/laneXY/handback_XY.md.
