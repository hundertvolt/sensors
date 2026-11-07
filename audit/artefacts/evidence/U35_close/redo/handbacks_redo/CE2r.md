CE2r hand-back, saved by the lead from the message it sent (2026-10-26). Commit fef0321a on audit/u35-ce2r (on f3fb02c0).

CE2r hand-back. Commit fef0321a on audit/u35-ce2r (base f3fb02c0), not pushed. Logs are in S/u35/laneE/ce2r/.

**Mechanism, re-derived from the v1.29.0 checkout and proved by runs**
- py/profile.c:168-173: `mp_prof_callback_invoke` sets `mp_prof_is_executing = true`, calls the callback, then clears it. A raise jumps out before the clear.
- py/vm.c:161-185: FRAME_ENTER, FRAME_UPDATE and TRACE_TICK all check `!mp_prof_is_executing` first, so nothing is traced after that.
- `mp_prof_settrace` (profile.c:181) only replaces the callback. Measured: `settrace(None)` followed by `settrace(tracer)` does not bring tracing back (proof/reset.log). Only thread init (runtime.c:169) clears the flag.
- Minimal proof on the old runner (proof/min_before.log): `after()` ran, but `src/<after>:2` is missing from the dump.

**Sweep: every committed job under the coverage runner, one at a time**
114 jobs (89 files, 5 per-device files × 6 devices). All exited 0, 0 memory markers, exactly 6 notes (sweep/results.tsv; base line numbers):
1. test_asy_bmp3xx_driver: `_stack_overflow()` :275 (via :809). Last traced line src/asy_print_log.py:467.
2. test_asy_isl29125_driver: `_stack_overflow()` :181 (via :3238-3239). Last traced line asy_print_log.py:467.
3. test_asy_print_log: `_stack_overflow()` :1807 (first called :1820). Last traced line asy_print_log.py:200.
4. test_asy_webserver_service: `_stack_overflow()` :4122 (raised from the fakes at :3540/:3556). Last traced line asy_webserver_service.py:633.
5. test_asy_system_service: test at :3630, its `bottomless` setter called from src/asy_system_service.py:282. Last traced line :282.
6. test_digital_twin_run_generic_integration :507: the SIGINT in `_test_kbd_traceback`. Last traced line digital_twin/run_generic_integration.py:702.

**After the fix**
- Each of the six runs only its exhausting call through `untraced()`, with every assertion kept.
- The six files plus test_untraced pass at -1, at 32768 and under the coverage runner, with no note and 0 memory markers (files_final/results.tsv).
- 1347 more lines are traced: bmp3xx +721, isl +234, system_service +227, webserver +135, twin +27, print_log +3.
- The twin file's digital_twin/run_generic_integration.py:699-702 now run untraced and are no longer counted; E.5.1 says so.

**Seen failing first**
- Runner tests: the 4 death-note cases failed on the missing note file, with the dump assertion already holding; the `untraced()` case failed on ImportError (red_runner_tests.log). The healthy-file guard was bitten twice: a note on every file, and the probe line left in the dump (bite/bite_a.log, bite_b.log).
- test_untraced: bite u1 (no `finally`) and bite u2 (settrace touched with no tracer) both red.
- test.sh tests: the listing test and the both-named test, plus the code-3-with-reason test, were red on the old scripts (red_testsh.log). The guards were bitten: bite_plainrun.log and bite_outrank.log.

**Decision for you to review**
- To make "the summary line says which" true, the code-3 Result now takes a reason in all three emitters (sh, py, js). The default stays "coverage report not rendered". test.sh prints "PASS (coverage incomplete in N job(s), listed under Notes)", or both reasons joined by "; ".
- The py and js fields are still named `not_clean_reason`/`notCleanReason`, now also carrying code 3's reason. A rename would touch _hardware_verdict.py and tests; flagged, not done.
- One existing assertion in test_summary_block.py changed: code 3 with reason "why" now expects "PASS (why)", and the default text moved to a new test.

**Owed to you or others**
- ci.yml:598's warning "coverage rendering failed, but every test passed (exit 3)" is now stale for the tracer case (ci.yml is not mine).
- tests_scripts/test_twin_record.py fails 2 tests on base f3fb02c0 as well (twin_record_base.log): reset_code_loop_end.py has no entry and several hashes are stale. Not mine.
- The T4r2 lane also edits test_digital_twin_run_generic_integration.py; my change there is one import line and :507.
- The four test files with a recursion helper (bmp3xx, isl29125, print_log, webserver) each carry an identical copy of `_stack_overflow()`. I left them as they are.
- Nothing for any allow-list.

**Silent-failure scan (twin and tooling mode)**
- Class 4: the runner's dump was not written if the probe raised; fixed with a nested try/finally.
- Class 7: the ci.yml warning above.
- test.sh reads notes only for its own jobs, and raw_dir is fresh each run: safe by construction.

**Checks**
- ruff, shellcheck, and the mypy main, twin and host passes are clean; npm lint, typecheck and lint-ceilings are green.
- The readers batch (59 tests_scripts files, including comment cap, citations, decision vocabulary, test_test_sh and test_coverage_runner): 1993 passed, plus the 2 twin_record failures above.
- Docs: SPECIFICATION.md E.5.1 has the tracer-death paragraph and says what `untraced()` excludes; E.5.3's code-3 row and its Result text; E.10's Result line and exit code 3. Also test.sh's usage text and a BACKLOG.md build-environment entry.
- After-times: system_service 24.3/25.3 s against base 24.92/26.40; webserver 4.1/6.3 s against 4.42/8.01. bmp3xx 13.7/13.7, isl 2.5/2.7, print_log 0.4/0.4 and twin 1.4/1.4 s have no base row. Nothing slower.

**Runs and cleanup**
- The sweep, three file runs and two readers runs all finished (RUNS.md lines).
- Deleted S/tc-ce2r, the two snapshot trees and all raw dumps. Nothing uncommitted.

nothing of mine is running
