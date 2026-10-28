TH1 hand-back, written by the lane (2026-10-28 04:15 UTC)

Branch audit/u35-th1, base 4265a61d. Worktree clean, nothing pushed. Logs are in S/u35/laneC/th1/.

## Commits
- **661630c5**: items 1 and 2. Every host-run twin launcher drops a caller's TEST_TWIN_HOST before the twin starts. The commit carries the seven red-first tests.
- **fc87e05b**: item 3. The runner's starting line names twin_host when it is not 127.0.0.1. Carries its test.
- **c77ae474**: audit/b3/review.md re-rendered. It has 8 new rows, all biting with no flag, plus line shifts. No verdict changed.

## Launchers found, and each one's fix
No launcher keeps the variable. None of their talkers reads TEST_TWIN_HOST, so dropping it is the conservative choice (agent, 2026-10-28).

1. **scripts/_twin_process.py spawn()**
   - This is the one env construction behind:
     - run_digital_twin_ci.sh's suite: Run 7's `_try_dns_query(HOST)`;
     - its harness pass (`--exclusive-port-53`);
     - the scenario harness run alone;
     - the harness under test.sh (already closed by test.sh:19).
   - Fix: a new public `twin_env(micropypath)` at :454. It is the caller's environment minus `_TWIN_HOST_ENV` (:57), plus MICROPYPATH and TZ=UTC. spawn() uses it (:432).
   - I made it one shared primitive rather than four inline drops (agent, 2026-10-28).
2. **tests_hardware/twin_board.py TwinBoard** (:65)
   - This covers the live tier `pytest --twin` flash tier, tests_hardware/conformance.py and scripts/record_twin_instrument_runs.py.
   - Fix: `twin_env(twin_micropypath())`. The now-unused `import os` is gone.
3. **tests_scripts/test_digital_twin_generated_boot.py `_twin_launch`** (:419)
   - These are the tests_scripts twins that boot run_generic_integration.py.
   - Fix: `twin_env(...)`.
4. **tests_js/_twin_process.js spawnTwin()** (:213), found by reading
   - This is the JS live tier: `_live_twin_command.js` and `_live_matrix_command.js`. It takes port 53's lock for 127.0.0.1.
   - Fix: `delete env.TEST_TWIN_HOST`. The env is typed `NodeJS.ProcessEnv`, as `_port_lock.js:111` already does.
5. **scripts/run_unix_port_integration.sh** (:41), found by reading
   - This is the manual launcher. It also takes port 53's lock.
   - Fix: `unset TEST_TWIN_HOST` beside its `export TZ=UTC`.

Not fixed, because a caller's variable has no effect there:
- **scripts/test.sh**: already closed (:19 unset, per-job pool). Unchanged.
- **digital_twin/launch.py**: src-free, with no shim.
- **The tests_scripts probes that never patch the shim**: boot_contiguity, fram_regions, fram_less_boot, frozen_first_shadowing, microtest, threshold_runner, coverage_runner.
- **tests/ in-process twins**: their peers already read twin_host.
- **digital_twin/run_device_script.py**: prints no starting line, and I left it without one (agent, 2026-10-28). TwinBoard now drops the variable, and a new line would enter every device script's parsed output.

## Red-first evidence (S/u35/laneC/th1/red1.log, red2.log, red_start.log)
Each test sets TEST_TWIN_HOST=127.0.0.77 in the caller's environment. On the old code each failed at its own assertion, `the caller's TEST_TWIN_HOST='127.0.0.77' reached ...`:
- test_twin_process_spawn.py (now :82);
- test_digital_twin_ci_suite_state.py :94, "while Run 7 queries 127.0.0.1";
- test_digital_twin_scenarios.py :489, the real Context.boot() through the real spawn(), with only Popen stubbed;
- test_twin_board.py :116, through a new `_recorded_twin_run()` helper that the existing MICROPYPATH test now shares;
- test_digital_twin_generated_boot.py :542;
- test_run_unix_port_integration_sh.py :108 and test_twin_process_js_spawn.py :109. In these two the stub interpreter wrote `'127.0.0.77\n'`.

The starting-line test (tests/test_digital_twin_run_generic_integration.py :1186) failed first: the old line had no twin_host field.

## End to end on this base
- **Base copy at 4265a61d:** `run_digital_twin_ci.sh dev --part suite --only 6,7 --gc-threshold -1`, run under an exported TEST_TWIN_HOST=127.0.0.77. Result: `FAIL: Run 7: the real CaptiveDNS answered a real UDP DNS query after WiFi hotspot fallback - no bind failure was logged`, and the starting line had no twin_host. This is N15's finding, reproduced (repro_base.log, repro_base_run7.log).
- **Head copy with only spawn()'s fix bitten:** Run 7 fails the same way, and its starting line now ends `twin_host='127.0.0.77'` (repro_bite_run7.log). This is item 3 doing its job.

## Bites (scratch copy of fc87e05b; S/u35/laneC/th1/bites.py, bites.log)
The control run with no bite was all 7 green. Each fix removed again turned exactly its own tests red:

| Fix removed | Red |
|---|---|
| `twin_env` filter | spawn, suite, harness, TwinBoard, generated_boot (manual, JS green) |
| spawn() back to os.environ | spawn, suite, harness |
| TwinBoard back to os.environ | TwinBoard |
| generated-boot launch back to os.environ | generated_boot |
| the unset | manual |
| the delete | JS |
| `_twin_host_field()` always returning "" | the runner test, both stages |
| `_twin_host_field()` naming the default too | the runner test, both stages |

## Start-line change (fc87e05b)
- `_twin_host_field()` (digital_twin/run_generic_integration.py :1052, between `_test_watchdog_fault` and `_uart_links`, D.15) returns `" twin_host='<addr>'"` when the shim's twin_host differs from its `_DEFAULT_TWIN_HOST`, else "".
- The starting print's last f-string line appends it.
- An inline form put main() over `max-statements = 73` (75), so I used a helper instead of raising the bound.
- No test or tool reads that line's text: I grepped scripts, tests, tests_scripts, tests_js, tests_hardware and digital_twin.
- A run made like a test.sh job (TEST_TWIN_HOST=127.0.0.150) prints the field on the file's other six main() runs, as intended.
- CMr1m may also touch this file. My hunk is that one print line plus the helper.

## Checks (all on the final content; logs in S/u35/laneC/th1/)
**Changed tests_scripts files and conventions**
- The 7 changed tests_scripts files, test_test_sh.py, test_citations, test_code_conventions, test_comment_block_cap and test_decision_vocabulary: 1125 passed (c1_tests.log).
- One warning: the datasheets/ submodule is not initialised in this worktree.

**The runner unit file**
- 50/50 at -1 and at 32768, zero markers.
- Time, base copy against head copy, three alternating rounds:
  - -1: 1.827 → 1.824 s;
  - 32768: 1.984 → 2.047 s (+3 %).
- The new tests_scripts tests each take under 0.3 s.

**run_digital_twin_ci.sh dev, both stages**
- Run under an exported TEST_TWIN_HOST=127.0.0.77, inside unshare -n S/u24/ns_xdg.sh at nice 19, with PICO_TOOLCHAIN_DIR=S/tc-int. Its record hashes equal this tree's toolchain/.
- Started from a tree without build/generated_html or frozen_modules (rebuild.sh afterwards).
- rc 0, 46 min. Results:
  - suite: 664 checks passed;
  - CRC16 Run 3: 32 checks passed;
  - harness (exclusive): 65 passed and 2 named skips per stage. The skips are the root file-mode one and an arzi-only one.
- Run 7 answered at both stages. No twin log names twin_host.
- 0 real memory markers. All 80 mentions are "carries none of" check lines (ci_dev.log).

**The dev scenario harness alone, both stages, same exported variable**
- 64 passed, 2 skipped, 1 deselected per stage. The deselected one is the DNS scenario, by the default `--shared-port-53`.
- 11m27s and 11m41s; 122 twin boots. No twin log names twin_host, and there are 0 markers (harness_dev.log).

**Web tier**
- npm run lint, npm run typecheck and lint-ceilings: PASS.
- npm run test:unit in the namespace: 26 files, 1340 passed.
- node_modules was linked from wt-base after the lock check, and removed after.

**Lint, types and audit checks**
- lint_direct: rc 0.
- The six mypy passes, cold: 275/59/315/1/1/1, clean.
- raising walk --check, e51 --check and --self-test, review_rows --check: all 0, with 8653 rows.

**The whole tests_scripts tier on c77ae474** (tier_final.log)
- 7112 passed, 6 skipped, 2 failed. Both failures are test_twin_record.
- Its two lists, 4 unrecorded instruments and 224 stale entries, are identical on base 4265a61d (rec_base.log).
- So neither red comes from this lane. Both wait for the lead's re-record.

## Silent-failure scan (all classes; modes: twin and tooling, WiFi AP)
- **Class 7 (asymmetric): closed.** Every launcher's twin and its talkers now agree on 127.0.0.1. A residual leak now names itself on the starting line.
- **A caller's deliberate TEST_TWIN_HOST is dropped without a line** by every launcher but test.sh. This is by design: the variable is test.sh's own. The doc text below states it.
- **No other class touched.**

Modes:
- Twin and runner tooling only; no firmware file.
- STA/Silent/Off/USB are unaffected. Only AP (hotspot) binds a captive DNS, so only AP-mode twin runs were exposed. All six devices are alike.
- No write to flash or SCD30 NVM is added or changed.

## Facts owed
**To the lead**
- This container has no `ss`. run_digital_twin_ci.sh's port_53_holders prints "ss: command not found" and goes on (`|| true`).
- `TEST_TWIN_HOST` now has two copies:
  - `_TWIN_HOST_ENV` in scripts/_twin_process.py (host CPython);
  - the shim's own constant (MicroPython, and it imports nothing from there).
  The literal in the new tests and in test_twin_host_isolation.py pins both.
- test_twin_board.py has an older fixture also named `twin_env`, unrelated and not importing the new function. I left it as is.
- No allowlist row is orphaned.

**To CMr1m:** the run_generic_integration.py hunk described above.

**To the owner:** none.

## Deviations
- I used a base copy and a bitten head copy for the end-to-end Run 7 reproduction and for the runner file's timing, because the base table has no per-file times.
- Headers that I did not change, all decided (agent, 2026-10-28):
  - test_digital_twin_scenarios.py, test_run_unix_port_integration_sh.py and test_twin_process_js_spawn.py: the property does not fit their 3-line headers without dropping content. Each new test has its own comment.
  - Three other tests_scripts headers and the runner unit file's header do name it. I made no meaning change to their existing text.

## Doc text for D3r (not applied: the brief leaves both files to the lead)
### digital_twin/README.md
In N15's D3r paragraph "**One address per process, because the port is the real one.**", replace the sentence that begins "Everything else sets none, so its twin binds `127.0.0.1` as before ..." up to its ";" with:

Every other launcher of a host-run twin drops a caller's `TEST_TWIN_HOST` before the twin starts:
- `scripts/_twin_process.py`'s `twin_env()`, which covers the CI suite, the scenario harness, `tests_hardware/twin_board.py`'s `TwinBoard` and the `tests_scripts/` twin boots;
- `tests_js/_twin_process.js`'s `spawnTwin()`;
- `scripts/run_unix_port_integration.sh`.

So its twin binds `127.0.0.1`, and the host-side talkers reach it there: `run_digital_twin_ci.sh`'s Run 7, the scenario harness's DNS scenarios and the live tiers. The runner's starting line ends with `twin_host='<address>'` whenever the address is not `127.0.0.1`, so a launch that lets one through shows it in the twin's own log;

Keep the rest of N15's sentence ("inside `scripts/test.sh` the scenario jobs ... `--shared-port-53`).") and the paragraph's last sentence. Optionally, add `tests_scripts/test_twin_process_spawn.py` and its six sibling launcher tests to the pinning sentence.

### CLAUDE.md, "Two suites that both bind real ports" (N15's D3r text)
1. Replace "and everything else - the scenario jobs, the `tests_scripts/` twins, every host-side talker - stays on `127.0.0.1`, where nothing inside `scripts/test.sh` queries port 53" with:

   and every other launcher drops a caller's `TEST_TWIN_HOST` (`scripts/_twin_process.py`'s `twin_env()`), so the scenario jobs, the `tests_scripts/` twins and every host-side talker stay on `127.0.0.1`, where nothing inside `scripts/test.sh` queries port 53

2. After "Don't re-diagnose a listener count over by exactly one burst as a code defect before checking each job's `TEST_TWIN_HOST`.", add:

   A host-run twin whose captive DNS never answers its talker: read the twin's starting line first. A `twin_host=` field there means a `TEST_TWIN_HOST` reached a launcher that should have dropped it.

## Runs
All runs went through S/u35/laneC/th1/run.sh, with RUNS.md lines: namespace, nice 19, disk ≥ 3 GB at every start.
- red1, red2, red_start;
- green1, green2, green_start, green_start2;
- lint1 (the PLR0915 red, then fixed), lint2, lint_final;
- mypy1, mypy_final;
- web_lint, web_unit;
- c1_tests, c2_m1, c2_32768, c2_jobhost;
- bites, times;
- repro_base: rc 1, as expected (the reproduction). An earlier attempt exited rc 2 on `--only 7 needs 6`;
- repro_bite: rc 1, as expected;
- ci_dev: rc 0;
- harness_dev: rc 0;
- audit1, rows_render;
- tier_final: rc 1, the 2 test_twin_record reds above;
- rec_base: rc 1, identical lists.

The scratch copies and raw twin logs are deleted.

nothing of mine is running
