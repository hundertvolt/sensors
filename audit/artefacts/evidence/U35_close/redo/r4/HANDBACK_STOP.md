stop hand-back, written by the agent (Fri Nov  6 07:19 UTC 2026). One commit `e53ca758` on `audit/stop` (`S/wt-stop`, from `f509c906`), not pushed.
1. **Stop file restored.** `scripts/_twin_process.py:37,366-381,401,407`: `spawn()` passes `--stop-file <state>/stop` and deletes a stale one; `shutdown()` creates it. A twin still running at the bound gets a DIAG line (/proc fields, log tail) and a SIGKILL. No SIGINT fallback, no second signal. The kill reason now reads "ignored its shutdown". SIGINT is sent only with `interrupt=True`. The one caller that tests SIGINT on purpose is the CI suite's Run 12 after-bootloader boot (`scripts/_digital_twin_ci_suite.py:753-767,919,1604-1605`). The harness, the other suite runs and `tests_hardware` send twins no SIGINT.
2. **Removed as dead:** `_second_sigint` and its two waits; the scenarios' `--test-kbd-traceback` arming; the runner flag itself (`_test_kbd_traceback`, `_KBD_CAPTURE_SPINS`, `_SIGINT`, its TestFlags field and usage line, the README row); their tests (the second-SIGINT test, the runner's kbd test, the flag-table entry). **Kept:** `_sigint_state`, part of the /proc description on Run 12's SIGINT path. Knowledge line: these were added 2026-10-19/20 (`8ad2bb37`, `06a8ae5d`) to find why twins ignored SIGINT. The cause is now known (F.6.1). Their code stays at `f509c906`.
3. **Tests, red then green.**
   - `test_shutdown_ends_a_twin_through_its_stop_file_and_by_sigint_only_when_asked` (`tests_scripts/test_digital_twin_ci_suite_errcount.py:665-716`): structural, with a fake process that records signals; cases stop file / sigint / stop ignored. Red on `f509c906` (spawn handed no stop file).
   - Restored `test_run_12_ends_the_boot_its_sigint_relaunch_follows_by_sigint` (`:973`): red on `f509c906` (every relaunch `interrupt=False`).
4. **Docs.** New SPECIFICATION.md F.6.1 (`:7369`): every cited line read at v1.29.0, and `py/emitbc.c:681-683` also at master `a39e77f08`. Also SPEC B.14.1 (`:2278`); `digital_twin/README.md` `:724-726`, `:864`, `:894-896`; `CLAUDE.md:830-832`.
5. **Lines.** Code and tests +104/-159 (net -55). Docs +32/-12. No `src/` change, so module bytecode and dev's `imageFreeBytes` are unchanged.
6. **Checks.**
   - `lint_direct.sh` rc 0 (after I dropped an unused `import time`); three mypy passes clean (276/312/59 files).
   - Changed and adjacent pytest files: 956 passed.
   - `tests/test_digital_twin_run_generic_integration.py`: 50/50 at -1 and at 32768.
   - Scenario tier, as `scripts/test.sh` runs it: arzi 62 passed and dev 64 passed, 0 failed, at both stages. 47/55 and 52/60 twins ended "stop file seen"; the rest ended on a claimed reset. 0 SIGINT, 0 DIAG, 0 memory markers.
   - `run_digital_twin_ci.sh dev`, suite + harness, at -1 and at 32768: 329/0, CRC16 15/0, harness 1/0 at each stage. 26 twins ended on the stop file and only `run12_b` by SIGINT, cleanly. 0 memory markers.
   - `tests_scripts` whole: 6887 passed, 9 skipped. The one failure was my test comment ("never signalled again" matched `test_decision_vocabulary`). I reworded it in the amend; that file, the errcount file and the comment cap then re-ran green (788 passed).
7. **Decision (agent, 2026-11-06):** text names the suite's "Run 12" as product vocabulary, not an audit run number.
8. **Findings, (c) other, not pursued.**
   - `tests_js/_twin_process.js` `stopProcess()` still ends live-tier twins by SIGINT, so it is open to the same loss.
   - `BACKLOG.md:808-809`'s build-env list is stale ("waits for a second SIGINT"), and this `scripts/` change is not recorded there; BACKLOG.md is outside my limits.
nothing of mine is running
