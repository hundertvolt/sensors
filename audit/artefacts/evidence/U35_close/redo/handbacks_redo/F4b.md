F4b hand-back, saved by the lead from the message it sent (2026-10-26). Commit 16121317 on audit/u35-f4b.

F4b hand-back: commit 16121317 on audit/u35-f4b, not pushed, nothing left uncommitted. Logs are in S/u35/laneR/f4b/.

**Steps**
- Step 1 applied. src/asy_system_service.py adds `_RR_LOOP_ENDED = const(22)` and `record_loop_end()`. After BOOT_DONE it writes 22 unless region 0 already holds a valid record, which it keeps (agent, 2026-10-26). A torn record is replaced. During boot it writes nothing. The entry (buildgen/codegen.py) keeps its own KeyboardInterrupt clause, then adds `except BaseException as ended:` which runs `record_loop_end()`, a fixed-argument print and `sys.print_exception(ended)`. It does not re-raise, so the entry ends and the watchdog resets.
- Step 2 applied, checked against v1.29.0. A SystemExit is a soft reset: pyexec.c:166-185 returns FORCED_EXIT (EXIT_CODE_HANDLING is 0 on rp2), and main.c:246-249 then goes to soft_reset_exit. After a soft reset `reset_cause()` still reads the last hard reset (modmachine.c:81-89), so `begin_boot()`'s PWRON check runs first and clears the record. That is why nothing is re-raised. Other classes go to the REPL with the watchdog still armed.
- Step 3 applied. Code 22 is in error_catalog.json (the website gets its codes from there through buildgen definitions; there is no hand-written js mirror), SPECIFICATION.md A.7 text, A.8 table and F.5.4, and tests_hardware/README.md. README.md and DEVICE_REFERENCE.md list no codes.

**Deviations**
- The record is written before the print: the three RAM stores cannot fail, a print could.
- `ended: BaseException | None = None` is bound before the `try`, so the handler's binding never grows the globals dict (it would allocate).

**Seen failing first, then green**
- Unit, tests/test_asy_system_service.py: 3 new tests red at :2500 (`KeyError _RR_LOOP_ENDED`), then 192/192 at both GC stages, ~24-25 s.
- tests/test_generated_boot_entry.py: red at :117 (the RuntimeError propagated), then 5/5 at both stages. It covers RuntimeError, SystemExit and GeneratorExit for every device.
- tests_scripts/test_buildgen_generate.py shape test: red for all 6 devices plus the variants test, then green. It also checks that every name the clause calls is bound by the entry.
- Twin, new tests/test_digital_twin_loop_end.py (per device; port band 19600-19659 added in tests/_port_bands.py):
  - Every device: the loop core fails after boot (OSError) and the next boot's `/status` reads 22.
  - First device only, three cases: SystemExit from a task reads 22; an escape in boot phase 2 reads 10 + phase; Ctrl-C still reads 21.
  - Every case checks ResetBits has TIMER set and FORCE clear.
  - Bite: the old entry tail planted in arzi's generated main.py made 3 of 4 fail; restored, 4/4.
  - All 6 devices green at both stages, zero memory markers. Times per stage: arzi ~9 s, others 2.6-3.6 s.
- Not done: a bite of the catalog-row guard. My importlib load of test_error_catalog.py failed (bite_catalog.log); the existing `test_the_reset_table_check_bites` already shows that check bites.

**Checks**
- Clean: ruff on my files, mypy main/host/twin passes (typings symlink, cold cache), comment cap.
- tests_scripts subset: 1839 passed, 4 failed. Those reds wait on you:
  - test_twin_record.py, 2 tests. The new script has no entry, and `test_reset_reasons.py` plus 13 device scripts that import asy_system_service.py have stale hashes. This needs a `record_twin_instrument_runs.py` run. The new script cannot run under TwinBoard (the twin has no frozen `main` module), so it needs a `--reasons` entry.
  - test_device_script_watchdog.py: `reset_code_loop_end.py` belongs in `_STARVATION_SCRIPTS` at tests_scripts/test_device_script_watchdog.py:20. That is an allow-list, so it is your edit.
  - test_comment_block_cap.py: the subset's 4th failure; fixed before the commit, now 637 passed.
- Not run (call budget): the dev and wozi twin CI, the full scripts/lint.sh, the silent-failure scan.

**Hardware test (prepared, collect-only OK, 2 cases)**
`test_a_loop_ended_by_an_exception_after_boot_is_attributed[exception|base]` with tests_hardware/device_scripts/reset_code_loop_end.py.
1. `_evidence` saves errcount and raw FRAM first (the FRAM-log rule).
2. `run_isolated_expect_reset`: mpremote's Ctrl-C makes the entry record 21, then raw REPL and soft reset (main.py is not re-run). The script patches `IOQueue.wait_io_event`, which arms only after this boot marks a phase below BOOT_DONE, because the BOOT_DONE left in region 1 is stale.
3. `sys.path.insert(0, ".frozen")`, then `import main`. The entry re-arms the one static WDT (machine_wdt.c:47-61, 8000 < 8388) and boots under the production config: no flash write, no FRAM seeding. `begin_boot` reads and clears the 21. It raises OSError or SystemExit at BOOT_DONE, and the fact line shows region 0 = 22.
4. The test waits for USB loss within the watchdog window, then asserts ResetReason 22, TIMER set and FORCE clear.

Wear is the same as the Ctrl-C test: no flash write site added or changed.

**Surprises**
- test_generated_boot_entry.py has always left its exec'd entry's `gc.threshold(32768)` unstubbed, so the -1 stage runs at 32768 after its first test. My twin file stubs `gc`.
- The Unix port has no `micropython.alloc_emergency_exception_buf`.
- An ended loop leaves `asyncio.core.cur_task` set, and `new_event_loop()` does not clear it.
- An exception before the entry's `try` (the device or system-service import) is still unrecorded. It is outside this brief; you may want to raise it with the owner under the "no uncaught exceptions" pillar.

**Facts owed**
- To you: the twin_record re-run and its reason, the allow-list line, the two twin CI runs, the surprise just above.
- To others: none.

**Runs:** every MicroPython run exited 0 once its fix was in; RUNS.md lines are written.

nothing of mine is running

---
F4b follow-up hand-back, saved by the lead from the message it sent (2026-10-26). Commit 980c0f7d on audit/u35-f4b (on 73fdae55).

F4b follow-up: the four tests_scripts reds you listed are fixed, plus a fifth my change caused. Commit 980c0f7d on audit/u35-f4b (on top of 73fdae55), not pushed, nothing uncommitted. Logs are in S/u35/laneR/f4b/. I reproduced all four reds first on 73fdae55 (four_red.log).

**The four fixes**
1. **no_print**: the rule allows print() only inside src/asy_print_log.py. The entry now imports `console` from there and calls `console("SYSTEM", "event loop ended with an exception:")`, the same fixed-argument primitive the other layers use. `sys.print_exception(ended)` stays; the rule does not match it. Neither allocates, and the record is still written first.
2. **level_containment**: the bench test file's `COVERS_TWIN_SCENARIOS` now includes "loop_end". That file holds the scenario's L4 counterpart, so this declares coverage rather than adding an exception row.
3. **Trailer**: tests/test_digital_twin_loop_end.py now ends with the canonical trailer, `import microtest` included.
4. **json_loads**: `/status` is read through `_strict_json.strict_loads()`, and the unused `import json` is gone.

**A fifth red, also mine, fixed**
`test_fatal_report_sites` requires every broad handler to call `report_if_fatal(<name>)` first, and the generated entries did not. The handler now starts with `report_if_fatal(ended)`, which allocates and prints nothing. tests/test_generated_boot_entry.py now checks it sees the planted exception, and the tests_scripts shape test pins the four-statement body.

**Whole tests_scripts tier**
Every file ran in its own `unshare -n` pytest process with PYTHONPATH=scripts, 481 s in total (ts_all/summary.txt). My first attempt had uv's python first on PATH and found no pytest; the rerun used the shared venv's python.
- 195 files: 192 green, 3 red.
  - test_fatal_report_sites: mine, fixed as above.
  - test_twin_record (2): stale hashes, expected, waiting on you.
  - test_readiness_gates (6 failed): **not mine, already red on 73fdae55.** I confirmed it on a clean `git archive 73fdae55` copy, also 6 failed. The trigger is asy_fram_manager.py:801, where `self.fram.initialized` is read through another object; F2r's c56b366b last touched that file.
- After the report_if_fatal fix I reran the 60 tests_scripts files that read the generated entry or asy_print_log: 3705 passed, 0 failed.

**MicroPython files, both GC stages, after the last edit (zero memory markers)**
- test_generated_boot_entry: 5/5.
- test_digital_twin_loop_end: 4/4 on arzi, 1 passed + 3 skipped on each of the other five devices. Per stage: arzi about 9 s, the others 2.6-3.6 s.
- test_asy_system_service: 192/192, about 24-25 s. src/ has not changed since that run.
- ruff on my files and the three mypy passes are clean.

**Silent-failure scan over my diff**
The product sites are the generated main.py lines 24-46 and src/asy_system_service.py:171, `record_loop_end()`. All classes, modes: boot, boot path files, each kind of restart, reset countdown, console.
- Class 4 (swallowed exception): covered by this change. The exception is recorded as 22 (or the existing record is kept), printed, then the watchdog resets.
- Class 6 (recovery): the recovery is visible as ResetReason 22 with the TIMER bit in ResetBits. A boot loop writes only the RAM record, so there is no wear.
- Class 5 (a print blocking on a stalled USB host): inherently safe. The record is written before the print, and an unfed watchdog still resets.
- Class 1: inherently safe. `record_loop_end` checks the magic and check word of both regions.
- Class 7, soft reset (new finding, not covered, already true for code 21): a friendly-REPL Ctrl-D inside the 8 s watchdog window re-runs main.py. `begin_boot` (asy_system_service.py:155) then reads the last hard reset's cause, so after a power-on it reports 1 and clears the 22. Only someone at the console can trigger this. Whether a soft reset needs its own code is your question or the owner's.
- Class 7, before the entry's try (not covered): an exception in the entry's imports (main.py:22-25) is unrecorded and reads 2. It is close to safe by construction: the frozen imports are deterministic, and every twin boot and the firmware build check exercise them. The smallest fix would be a `mem_backup` write from the entry itself; that is the owner's decision.
- Class 7, partly covered by the owner's decision: the exception's text reaches only the console, and the record keeps just the code.

**Facts owed to you**
- The twin_record re-run; test_reset_reasons.py's hash changed again.
- The allow-list line at tests_scripts/test_device_script_watchdog.py:20 for `reset_code_loop_end.py`. That test was green in this run, so check whether it still needs adding.
- test_readiness_gates, red on 73fdae55 (above).

**Runs:** every run has its RUNS.md start and exit lines.

nothing of mine is running
