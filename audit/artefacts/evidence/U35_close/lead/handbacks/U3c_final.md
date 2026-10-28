U3c hand-back (lane U). Commit **962602d** on bfc6519, branch audit/u35-u, S/wt-u35u. Nothing is uncommitted and nothing of mine is running. I stopped at the 70-call valve, so this block is partly done.

**Steps**
- **Guard: applied.** A registered PUT /status command now goes through the new `_run_status_cmd()`, which has the same shape as `_run_system_cmd`: the errno, `report_if_fatal`, "Failed". It sits just before `_run_system_cmd` (D.15).
  - Seen failing: tests/test_asy_webserver_service.py:1185, `AssertionError: 500`.
  - New service test of `add_status_command`: Valid, Failed, Invalid for false/1/"true" and for an unregistered key, zero writes. It passed at once, so I bit it twice: accept any truthy value (fails at :1171) and a planted write (fails at :1173 with (0, 2)).
- **Buildgen readers: applied.** On base, using a scratch copy with the head's test file, both fail on dev only (2 failed, 10 passed). On the head, 12 passed.
- **samples.json: applied.** Added `status.sensors.UART_init {Runs, Pending, Last}`. Before it, the coverage test failed with `no sample for "status/sensors/UART_init_Runs"`.
- **Mock mirror: applied.** js/mock-server.js now answers {key: true} with "Valid" for any dispatch key the status section lists, and every other value with "Invalid".
  - Seen failing at definitions-mockdata-coverage.test.js:127 (dev: Valid expected, Invalid received).
  - I then rewrote the loop as `Promise.all` to fix `no-await-in-loop`. It asserts the same list, but I did not re-run it against the old mock.
- **Templates case: applied.** It renders each status command group per device. It passed at once, so I bit it twice: drop `onLabel` (all six fail, :771) and dev's toggle with confirm set to false (dev only, :769).
- **New defect, fixed:** at bfc6519, tests/test_asy_uart_link_driver.py stopped at its import (`no module named 'microdot'`). scripts/test.sh's MICROPYPATH excludes ext/. I added the `sys.path.insert(0, "ext")` that the webserver test uses. Now 43/43 at both stages. U3b's 43/43 must have run with ext/ on the path.

**Effect per device and mode.** The guard matters on dev only, the one device that registers a command. In STA and AP, a raising command now answers "Failed" and logs WEBSERVER CALLBACK, where it answered 500 before. Silent and Off have no API. USB is unaffected. The other five devices are unchanged. The mock and samples changes affect the website preview only. mpy-cross for the webserver: base 15017 B, U3b 15177 B, head 15312 B.

**Times (s)**
- Webserver, paired base → head: 4.61 → 4.56 at -1; 7.82 → 7.29 at 32768.
- Link driver, head only: 3.51 at -1 and 4.97 at 32768 (U3b had 3.60 and 4.70).
- Zero memory markers in all runs.

**Checks**
- ruff clean; mypy main 264 and src/tests 230 files, 0 issues; npm lint and typecheck clean; lint-ceilings 4/4.
- JS readers all green: mock-server, put-matrix, mock-data-compose, generated-definitions-render, site-functions, app, accessibility, templates (128), coverage (18).
- 12 checks: 798 passed, 1 red. The red is test_tunables_register: the five tags from LEAD NOTES 31, waiting on D2. My edit moved the link-driver-test tag from :495 to :500. Five checks re-run green after that edit.

**Decisions (agent, 2026-10-21)**
- The guard is a helper method, not inlined.
- The mock does not track state for a command: it always answers "Valid" and never shows the pending "Failed".
- The mock test lives in definitions-mockdata-coverage.test.js, because mock-server.test.js is not lane U's.
- The sample's `Last` follows the link driver test's expected sweep.

**Owed**
- SPECIFICATION.md G.2's list of guarded callbacks should name `_run_status_cmd()` (D2 or the lead).
- Deviation: the 12-check pytest run took 68.5 s and has no RUNS.md lines.

**U3d starts at 962602d with:**
1. The link driver test paired against f6f54cc at both stages.
2. Every dev generated-module test file at both stages.
3. The tests_scripts readers of my files: test_error_catalog, test_preview_server, test_js_api_mirrors, test_definitions_js_mirrors, test_api_reference and the rest of the grep list.
4. test_twin_record (red expected), relay lines, the silent-failure scan and the 17 scans.

node_modules in S/wt-u35u is a gitignored symlink to S/wt-u8 (same lock hash). Logs: S/u35/laneU/u3c/ (pair/summary.txt, bites/, readers_*.log, checks12.log, mpy/sizes.txt).