T1 hand-back (lane T, branch audit/u35-t, worktree S/wt-u35t from f3fff0e). Commits: 8b524eb (<SHUT>), dac9046 (soak fixture). Nothing uncommitted. Nothing of mine is running; the leaked fixture child (pid 17829) was killed by pid, and the fixture now reaps on any outcome.
Steps:
- 151 applied, with one deviation (agent, 2026-10-21). The printed shutdown line gains ` fram_writes=<n> fram_writes_by=<LOGGER>:<n>,…|-` and, when writes_at dropped any, ` fram_writes_unattributed=<n>`, from a new `_fram_write_fields(_module, machine._current_fram_chip)` added at the print site. `_shutdown_line()` itself is unchanged, so the exact-line case at tests/test_digital_twin_run_generic_integration.py:218 (no lane's file) stays green. The `_module` global sits beside `_watchdog`.
- 152 applied: `--test-watchdog-fault supervisor-raise|main-exit|block` (TestFlags field 12) and `WDT_AT_FAULT <feed_count>`. Deviation (agent, 2026-10-21): the fault arms at the first feed after the supervisor's tasks exist, because a boot feed comes before them and `feed_count>=1` alone would arm supervisor-raise with no task to end. `block` = `_WDT_TIMEOUT_MS+1000` ms.
- 154 landed: confirmed at f3fff0e, no normal-boot tolerance list in scripts/ or tests_scripts/ (grep).
- OF-215 stage 3 applied. `spawn()` owns `--stop-file` (state_dir/stop; a stale one is removed; a caller's own is refused). `shutdown()` touches it; SIGINT stays as the fallback (sets `run.stop_ignored` and prints a DIAG line), and `interrupt=True` sends SIGINT first. The runner now honours `--stop-file` without `--duration`.
ShutdownLine fields as T2 reads them:
- `fram_writes: int` is required. It is the chip's write_count, 0 when no chip is wired.
- `fram_writes_by: dict[str, int]` is required ("-" parses as {}). Each value is the sum over both chunk copies, so one persisted entry counts 2. A logger named twice or a malformed entry raises.
- `fram_writes_unattributed: int` defaults to 0. It is present only when writes_at overflowed, and fram_writes_by is short by that many.
- Real dev boot: fram_writes=40 = 20 loggers × 2. In that boot, fram_writes_by == {each logger: 2}.
Seen failing first:
- the flag table, until the flag existed;
- 9 parser cases and 4 stop-file/spawn cases (13 failed on base, S/u35/laneT/seen_failing_1.log).
- Real dev twin (S/u35/laneT/proof/):
  - (B) base shutdown() on a twin with SIGINT blocked: killed after 13.0 s, no shutdown line.
  - (C) head shutdown() on the base runner: the stop file was ignored, the SIGINT fallback ended it, and parsing gave "no fram_writes= field".
  - (A) head on head with SIGINT blocked: exit 0 in 0.11 s, fields parsed.
- Watchdog-fault smoke on a real dev twin: all three kinds print WDT_AT_FAULT 14. supervisor-raise and main-exit starve: feed_count stays 14, would_trigger 2. block gives 1 would_trigger, a largest gap of 9041 ms, and feeds resume.
Red checks, waiting on the lead (no lane holds these files):
- tests/test_digital_twin_run_generic_integration.py:124 and :130 (one test, `TypeError: TestFlags() takes 12 positional arguments but 11 were given`). Twin mypy pass: 2 call-arg errors at the same lines. Fix: append `, None` at :124; at :130 add `--test-watchdog-fault block` to the parsed args and a 12th value `"block"`.
- tests_scripts/test_digital_twin_scenarios.py:396 `_SHUTDOWN_LINE` lacks the new required fields, which makes 23 tests fail with "carries no fram_writes= field". Fix: append ` fram_writes=0 fram_writes_by=-`.
Owed to T2:
- the suite's `_shutdown()`/`_check_exit` should fail on `run.stop_ignored`;
- Run 12's "SIGINT relaunch" now ends on the stop file, so use `interrupt=True` there to keep its meaning;
- README/SPEC wording on "SIGINT shutdown" (runner docs, README "Runner flags") for T4/D.
Decision (agent, 2026-10-21): parser and stop-file cases went into tests_scripts/test_digital_twin_ci_suite_errcount.py, and the fixture fix into test_digital_twin_ci_suite_soak.py (both lane T files, T2's block, run in sequence). That file already holds every ShutdownLine and shutdown() case.
Scan (all classes, twin/tooling modes):
- New, class 6: a stop file left unanswered ends the run cleanly through the fallback, visible only through the DIAG line and stop_ignored until T2's check lands.
- Class 2 is covered: writes_at overflow is surfaced as fram_writes_unattributed.
- STA, AP, Silent, Off and USB are unchanged on every device: no src/ or image change.
Runs, base/head paired, all rc=0, mem=0:
- dev integration: -1 23.12/23.20 s, 32768 23.84/23.97 s.
- errcount 0.97/1.44 s (+0.47 s, under the 0.5 s bar). soak 0.73/0.53 s after the fix.
- 16 more readers green and flat, including twin_record (6 passed, green as expected), test_sh 32.95/32.50 s and generated_boot 57.60/57.57 s.
- no_variant_literals +1.08 s and twin_wiring_contract +0.55 s: neither file is mine, from one alternated pair, probably host noise.
- Before-commit checks: 907 passed. ruff clean; host mypy clean.
- RUNS.md has start and done lines.
T2 starts from dac9046.
