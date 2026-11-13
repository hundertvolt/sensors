# TESTS: the test machinery (tests/, tests_scripts/, tests_hardware/, digital_twin/, tests_js/, test-side scripts/)

## Verdict (3-6 lines): do the rulings hold in this scope; are drift leftovers gone?

Partly. The audit's records are gone: no test or tool reads `audit/` or `PROJECT_AUDIT_PLAN.md`, the owner-kept gates are
in place, and the summary block now has one emitter. But M8, the test-machinery runaway, is still mostly here. The
machinery is 2.1x its pre-audit size (+117,700 lines against +3,800 lines of `src/` and `buildgen/` together). R2 was
the only cleanup aimed at it, and it removed about 3,800 lines. The slims R2 named itself were never carried out: the
tests of tests, the growth of the twin harness and the triple port lock. Since R1 ended, the test directories have
shrunk by only about 800 lines net. None of this decides a firmware or buildgen verdict.

## Shape since the baseline (a few lines: what was added/removed and what it is for)

- Six directories, files/lines at `25caf528` -> release: `tests/` 104/62,532 -> 144/101,794; `tests_scripts/`
  65/14,529 -> 213/61,326 (4.2x); `tests_hardware/` 98/13,911 -> 178/26,690; `digital_twin/` 19/4,443 -> 22/7,529;
  `tests_js/` 16/4,697 -> 44/11,694; `scripts/` 20/3,451 -> 52/12,243. Total: 322/103,563 -> 653/221,276. For
  comparison, the product grew from 13,427 to 14,964 lines (`src/`) and from 3,681 to 5,960 (`buildgen/`).
- What the additions are for:
  - Product verdicts: the unit tests of `src/` (`tests/test_asy_*`, 28 files, 59,619 lines) and the twin tests in
    `tests/` (6,989 -> 16,677).
  - Build-chain depth: the `test_buildgen_*` files, plus `test_micropython_overrides.py` (+1,239 net) and
    `test_setup_toolchain_env.py` (+1,407 net).
  - 43 new whole-tree static gates in `tests_scripts/` (about 10,200 lines).
  - Tests whose subject is another piece of test machinery: in `tests_scripts/`, 22 files/3,628 lines -> 78/18,125.
  - Release fixtures: `fixtures/api_reference/*.json` (7,526 lines) and `golden/*.json` (296).
  - Twin harness: `scripts/_digital_twin_scenarios.py` (2,408, new), `_digital_twin_ci_suite.py` (1,326 -> 1,878),
    `_twin_process.py` (460) and `run_generic_integration.py` (439 -> 1,503).
  - Hardware tier: `device_scripts/` 56 -> 110 files, `harness.py` 501 -> 1,040, `conftest.py` 270 -> 616 (most of
    these tests the owner asked for, 2026-11-06).
- Since R1 ended (`8a32d826`), lines added/removed: `tests/` -4,618, `tests_scripts/` +4,206 (the 2026-11-10 release
  fixtures), `tests_hardware/` +692, `digital_twin/` -801, `tests_js/` -318, `scripts/` +58.

## Findings (most important first, max 15)

### TESTS-1 [class L] [VERIFIED sizes; SUSPECTED value] The tests of the test machinery grew about 5x, and R2's named slims were never carried out
- Where:
  - `tests/test_shared_helpers.py:1-3`: 678 lines, 43 tests, "the shared test doubles and readers no consumer test
    pins yet ... each against the behaviour its former copies had". This is the proof of a helper merge, not a
    product test.
  - `tests/test_driven_time.py:1`: 642 lines, a self-test of `tests/_fake_time.py`.
  - `tests_scripts/test_test_sh.py`: 839 -> 2,435 lines, 151 tests for a 1,166-line runner.
  - `tests_scripts/test_digital_twin_ci_suite_{errcount,soak,ceiling,matrix,state}.py`,
    `test_digital_twin_scenarios.py`, `test_run_digital_twin_ci_sh.py` and `test_twin_runner_test_flags.py`: 656 ->
    2,783 lines.
  - `tests_scripts/test_bench_harness_helpers.py`: 171 -> 1,219.
  - `tests/test_digital_twin_run_generic_integration.py` (290 -> 1,399) and `tests/test_digital_twin_machine.py`
    (539 -> 1,763).
- What:
  - These files test the runner, the fakes, the twin CI suite and the bench helpers. Together they grew by about
    8,400 lines.
  - The whole class in `tests_scripts/` went from 22 files/3,628 lines to 78 files/18,125.
  - This is DRIFT 2.6 (3): "the tests and tools were scanned too".
- Ruling/pillar it meets:
  - 2026-10-28: "The unit tests shall have good quality, but don't need deep dives. The audit verification machinery
    is just a temporary tool."
  - 2026-11-11: "don't drift into fixing tests, concentrate on the quality of the firmware and the buildgen".
  - PICTURE M8.
- Decision record:
  - R2's list, section 1.8 (agent, 2026-11-04), named exactly these files "for phase B to read, not proposed":
    `test_test_sh.py`, the five ci_suite files, the two twin self-test files, and the shared-helpers/driven-time
    overlap.
  - R2's hand-back shows that none of them was read or slimmed (`test_test_sh.py` went only from 2,530 to 2,435).
  - The owner never saw the classification. Only R2's questions 1 and 2 were put to him.
- Smallest fix: owner must decide the cut.
  - The clearest candidates: delete `test_shared_helpers.py` and `test_driven_time.py` whole (1,320 lines), and take
    the others back toward their baseline size (about 7,100 lines of growth).
  - Nothing a firmware or buildgen verdict depends on goes with them. I checked the imports of the six largest: they
    load only test-side modules, runners and buildgen's readers.

### TESTS-2 [class L] [VERIFIED] The twin harness grew well beyond "keep tiny": 14 `--test-*` fault hooks that patch product private members, and a scenario harness twice its baseline size
- Where:
  - `digital_twin/run_generic_integration.py:605-648`: the parser of 14 `--test-*` flags. The baseline had none.
  - `:777-1190`: the `_test_*` hooks, about 415 lines.
  - `:817-833`: `_test_drop_timer_fire` rebinds `sysfunct._reset_timer.init`.
  - `:896-914`: `_test_hold_closing_slot` rebinds `webserver._close_writer`.
  - `:999-1013`: `_test_pin_send_buffer` rebinds `webserver._serve`.
  - `:1171-1190`: `_test_watchdog_fault` rebinds `sysfunct._log_dead_task`.
  - The callers in `scripts/_digital_twin_scenarios.py`: `:524`, `:638`, `:656`, `:687`, `:824`, `:914`, `:1077`,
    `:1273`, `:1651`, `:1680`, `:1702`, `:2137`, `:2214`. That file holds 66 scenarios in 2,408 lines; the baseline's
    `_webserver_concurrency_scenarios.py` plus the real-website integration file held 1,211.
- What:
  - The twin runner went from 439 to 1,503 lines. `digital_twin/` as a whole went from 4,443 to 7,529.
  - The hooks plant faults by patching private product names from outside, so a product refactor breaks the twin.
  - Concrete duplicate: `watchdog_fault_block` (`_digital_twin_scenarios.py:2229`, a loop blocked past the watchdog
    timeout) proves what the baseline's Run 10 already proves (`scripts/_digital_twin_ci_suite.py:777-794`, a
    blocking sleep that starves the watchdog). Its own exception row, `SPECIFICATION.md:5875`, names Run 10's flash
    test as its counterpart.
- Ruling/pillar it meets:
  - OR20: "Only if there is no alternative, and keep tiny anyway".
  - 2026-10-23: planting faults is "not required for the straightforward tests".
  - 2026-11-11: negative tests "extremely prone to become overkill".
  - PICTURE M8: "The twin's harness growth goes beyond OR20's 'keep tiny anyway'".
- Decision record:
  - R2 kept `test_twin_runner_test_flags.py` under "OR20, OR36". That reading only says the flags stay test-only; the
    size was never put against "keep tiny".
  - The twin-only rows in `SPECIFICATION.md` E.6.6 (`:5866`, `:5871`, `:5875`) are agent-written.
  - No owner decision on the hooks.
- Smallest fix: owner must decide per hook.
  - Clear now: `--test-watchdog-fault block` and its scenario go, because Run 10 covers it.
  - Some hook scenarios are the only proof of their case:
    - `client_gone_mid_response_is_counted`, `a_connection_still_closing_holds_its_slot...`,
      `a_reboots_reset_fire_lost...` and the other two `watchdog_fault_*` have no L3/L4 counterpart (E.6.6 rows).
      Dropping a hook drops that proof.
    - `a_hung_shutdown_step_is_ended_by_the_watchdog` and `an_escalation_entry_that_never_finishes...` do have
      silicon counterparts (`tests_hardware/flash/test_system_commands.py` and
      `tests_hardware/bench/test_reset_reasons.py`).

### TESTS-3 [class L] [VERIFIED] The twin record was decided out of the tree, but the runner still writes it there and four doc sites still promise or cite it
- Where:
  - `scripts/record_twin_instrument_runs.py:33` writes `tests_hardware/twin_record.json`. `.gitignore` has no entry
    for it, and the release tracks no such file.
  - `tests_hardware/README.md:588`: "Then commit the record | review (the committed record returns on the final
    tree)".
  - `digital_twin/README.md:647-649` ("writes the twin record ... never listed in this file").
  - `BACKLOG.md:102` ("its twin record") and `BACKLOG.md:160` ("the file's twin record names its silicon-only cases").
  - Also `tests_scripts/test_record_twin_instrument_runs.py` (101 lines).
- What: a run of the owner-approved runner leaves an untracked file in `tests_hardware/`, and the hardware README tells
  the reader to commit it. The plan decided the opposite.
- Ruling/pillar it meets:
  - 2026-10-28: the verification machinery is temporary.
  - P8: one source of truth.
  - The cleanup's own decision (below).
- Decision record:
  - The owner's review answer `twin-first-for-instruments` was "ok": "A committed runner runs every device script and
    hardware test once against the twin ... exceptions are listed."
  - PLAN R0: "The twin record's committed copy and its staleness test go ... The runner, `twin_board.py` and `--twin`
    stay."
  - R3 action list, item 1: "not committed to the product tree again", recorded as a decision taken on the owner's
    behalf.
- Smallest fix: about 10 changed lines.
  - The runner's output path moves out of the tree (to `build/` or the evidence archive).
  - The four doc sites drop "commit the record" and the "its twin record" citations.
  - The owner may instead confirm or reverse R3's decision, which was taken on his behalf.
  - Nothing a firmware or buildgen verdict depends on.

### TESTS-4 [class L] [VERIFIED] Planted-negative control arms survive inside the whole-tree gates
- Where:
  - `tests_scripts/test_exception_handler_contract.py` (769 lines, 21 tests):
    - Real-tree checks: `:275-295`, `:539`, `:666`.
    - The section headed "Planted negatives: each rule fails on the shape it exists to stop" (`:296-443`), plus
      `:561-611` and `:694-731`: about 230 lines of planted-or-clean pairs.
  - `tests_scripts/test_tunables_register.py:298-371`: 13 of its 19 tests run on synthetic trees.
  - `tests_scripts/test_error_catalog.py:760-811`: "the checks on a planted catalog and module".
  - Function names like `a_planted_*`/`a_clean_*_nothing`: about 40 across roughly 25 files, mainly in
    `tests_scripts/`.
- What: these tests check that the checker bites. They are not tests of a product property. A 769-line contract file
  guarding one 3-line install site (`src/asy_system_service.py:697-699`) is mostly control arm.
- Ruling/pillar it meets:
  - 2026-11-11: "be careful with such negative tests. they are extremely prone to become overkill".
  - OR21.a: the control arms are "overkill".
  - R2's own rule (its hand-back): "a check that stops biting is a review matter (no permanent control arms in CI)".
    R2 removed 48 such functions; these survived under "clean/planted" names.
- Decision record:
  - The owner kept the exception-handler guard itself on 2026-11-02 ("That's okay."). That decision covers the guard,
    not its 769-line contract.
  - The gc-site checker is owner-kept in full, so its planted cases are excluded from this finding.
  - No record covers the others.
- Smallest fix: delete the planted and clean-control tests in the gates the owner has not kept in full; keep each
  gate's real-tree checks. That is about 350-450 lines. No verdict depends on them: the real-tree checks stay.

### TESTS-5 [class L] [VERIFIED] The CI caps went from 45 to 175, 175 and 95 minutes, set by an agent's 5x margin multiplied by the retries, while a warm run takes about 10 minutes
- Where:
  - `.github/workflows/ci.yml:385` and `:411` (`timeout-minutes: 175`), and `:436` (95).
  - `SPECIFICATION.md:12189-12190`: warm runs measured at 8.9-10.1 minutes.
  - `SPECIFICATION.md:12201`: `runner.scenarios_timeout_s` is 2,555 s, "5x the 511 s CI's slowest", based on a
    "single observation". Multiplied by 3 attempts that gives about 128 minutes, which the cap takes in full.
- What: the 175-minute cap is derived. It is the decided per-attempt retry multiplied by an agent-picked 5x margin on
  a scenario job that folds 66 scenarios together. PICTURE M8 lists it ("CI went from 45 to 175 minutes, against
  OR39's 'speeding up'").
- Ruling/pillar it meets:
  - OR39: "Look for opportunities for speeding up the test suite".
  - 2026-11-09: remove the cause so the mitigation built around it can go.
- Decision record:
  - The retry is the owner's (`runner.per_file_attempts`: owner 2026-09-26 and 2026-10-20).
  - The 5x margin is not the owner's.
  - R2 planned "CI timeouts from measured need" and kept every value ("measure on the bench").
- Smallest fix: set the per-attempt bound from the measured need with an ordinary margin. The caps then fall back
  toward the baseline's 45 minutes. The retry rule and the hang backstop stay as they are. No verdict changes.

### TESTS-6 [class E] [VERIFIED] One flock is implemented three times, plus a test-only probe inside the JS copy
- Where:
  - `scripts/_port_lock.sh` (60), `scripts/_port_lock.py` (61) and `tests_js/_port_lock.js` (260).
  - `tests_js/_port_lock.js:3`: "probePortLock() is the Commands API probe behind tests_js/port-lock.test.js; no
    runner calls it".
  - Their tests: `tests_scripts/test_port_lock.py` (466) and `tests_js/port-lock.test.js` (82). About 930 lines in all.
- What: the same lock file, owner chain and messages exist in three runtimes. The summary block was already merged
  into one shape: `scripts/_summary_block.sh:2-3` and `tests_js/_summary_reporter.js:2` hand their records to the one
  emitter, `scripts/_summary_block.py`.
- Ruling/pillar it meets:
  - "One shape per job".
  - 2026-11-07: "could the same outcome be implemented leaner without losing anything".
- Decision record:
  - R2's O-lock-1 to O-lock-5 (agent) proposed one lock, citing OR38.a (3) and the owner's 2026-11-03 "Generally
    target low complexity". R2 left it "to the lead", because the documented direct run of
    `_digital_twin_ci_suite.py` would then take no lock.
  - R5's C #3 only moved the lock onto `flock`.
  - No owner decision.
- Smallest fix: owner must decide. Use the summary block's shape: the shell lock is the one implementation, and the
  CPython and Node launchers go through it. The `.py` and `.js` copies go with the probe, and `test_port_lock.py` is
  slimmed. That removes about 400-600 lines. No verdict depends on it.

### TESTS-7 [class L] [VERIFIED] The repo scanners still exclude the deleted audit set
- Where:
  - `tests_scripts/_repo_scan.py:25-28` ("The audit working set is excluded until its close deletes it"; `"audit/"`
    and `"PROJECT_AUDIT_PLAN.md"`).
  - `tests_scripts/test_import_graph.py:22-24` (`"audit/"`).
- What: the close deleted both paths, so these entries are dead.
- Ruling/pillar it meets: dead code; the archive holds the records.
- Decision record: none found. The comment itself names the close as the end point.
- Smallest fix: delete the two entries, the file name, and the sentence that explains them (about 4 lines).

## Checked and clean (one line each)

- No test or tool reads `audit/` or `PROJECT_AUDIT_PLAN.md`. The only remaining references are the dead exclusions in
  TESTS-7.
- `test_citations.py` and `test_decision_vocabulary.py` with their allow-lists (1,102 + 362 lines) stay by owner
  decision, 2026-11-03: "Option A, this is valuable for future sessions as well".
- Owner-kept in full and present: the comment-cap gate, the gc-site checker, the memory-gate agreement, the
  persistence-marker completeness check and the four-tier bus-hazard files.
- The summary block has one emitter, `scripts/_summary_block.py` (OR15.a). Earlier there were three.
- The skill helpers in `scripts/` (`_log_verdict.py`, `_errcount_digest.py`, `_failed_tests.py`, `_preflight.sh`,
  `_run_checks.sh`, `_tidy.sh`; 613 lines) and `test_work_routines_helpers.py`: the owner asked for the skills on
  2026-11-06.
- The device-TOML keys `bench` and `hardware_family` (`buildgen/validate.py:78-80`, `devices/*.toml:17`) are test-only,
  but the owner decided them: OR141.a (1), 2026-10-05, "keep keys in the device files"; DR1 says "the owner stands".
- `TestOverrides` (`buildgen/codegen.py:603-604`) appears only in the owner's tick-offset test image (owner
  2026-10-01). A release module keeps exactly three build keys (`tests_scripts/test_buildgen_generate.py:783`).
- P4: I found no test hook in `src/` or the generated modules besides the exception-handler guard
  (`src/asy_system_service.py:697-699`), which is owner-kept (2026-11-02, "That's okay.").
- No test pins a removed mechanism: every `src/` constant that tests read through `src_int`/`src_*` still resolves, and
  no test references the removed M2 timers.
- `tests/_cancel_sweep.py` is a fault generator with 13 call sites in concurrency-heavy modules: bounded, and within
  the owner's "complex" scope.
- The hardware-tier growth (`device_scripts/` 56 -> 110) is covered: the owner asked for the tests on 2026-11-06 ("I
  would like all of the tests, except #9"), and he approved the twin-first runner.
- `test_level_containment.py` and the 36 `COVERS_TWIN_SCENARIOS` declarations rest on an owner row (OR45.a).
- The stored-config golden (`tests_scripts/golden/`) rests on the owner's migration rule of 2026-09-26.

## Notes (anything else, one line each)

- The 43 new whole-tree static gates (about 10,200 lines; the largest are `test_error_catalog.py` 811,
  `_await_depth.py` 909 + its test 207, `test_ci_workflow.py` 454, `test_code_conventions.py` 439 and
  `test_import_graph.py` 358) are where DRIFT 2.2's "rules that expand got gates" still lives. R2 found an owner row
  for each, so I did not raise them; a one-line owner look may still be worth it.
- `tests_scripts/fixtures/api_reference/*.json` (7,526 lines, added 2026-11-10): I found no owner record for the REST
  reference golden (SPECIFICATION.md A.8). This is the BUILDGEN scan's call.
- `src/asy_uart_comm.py:342` says its log text is chosen "for the memory gates" (M6). That belongs to the FIRMWARE scan.
- `scripts/test.sh`'s host speed probe and its bands are pre-audit, not drift.
- `digital_twin/README.md` grew from 919 to 1,240 lines, and many of its fidelity rows read "accepted (agent, ...)"
  (M10). That belongs to the DOCS scan.
