CRr2b6 hand-back, saved by the lead from the message it sent (2026-10-27). Commits 68ce7043, e8452ccc, 4a2e3ddf on audit/u35-crr2b (on c12d1bd6).

U35 lane CRr2b6 hand-back. I made three commits on audit/u35-crr2b (in S/wt-u35crr2b, based on c12d1bd6) and pushed nothing. The tree is clean. I stopped at a seam at about 80 tool calls. Done: item 1, item 2, and the serving_heap part of item 3. Not started: the UART hazard set and the quiesce() check (the rest of item 3), item 4 and item 5.

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad. Logs are in S/u35/laneC/crr2b6/. Each set's before, after and source lines are in S/u35/laneC/crr2b6/sets_map.txt. Every run went through my S/u35/laneC/crr2b6/run.sh (own session, `timeout -k`, namespace, nice 19, disk check). Its RUNS.md lines read "U35 lane CRr2b6": 39 runs, 78 lines.

**Commits**
- 68ce7043: the escalation test reads its budget entry off the run's own rounds, not production's history.
- e8452ccc: the extended hammer admits the ceiling refusals its own load provokes, and nothing else.
- 4a2e3ddf: the per-source heap test's log set names only what its probes and scratch boot can persist.

**Item 1: the escalation ruling (68ce7043)**
- I confirmed the find on the tree. The script builds SystemService with `LogConfig(None, 10, 0)` (system_service_restarts_a_real_dead_task.py:54), so its log is RAM-only.
- Escalate mode can carry the entry on the console. The entry is written at asy_system_service.py:589, then `_reboot()` arms a 4 s one-shot (`_RESET_DELAY`, :64/:367). The script keeps printing `round_<n>` facts every 0.9 s with SYSTEM's RAM log in them.
- The new check, `_round_holds_the_budget_entry(facts)` in test_reset_reasons.py: in escalate mode, a round before the reset must hold SYSTEM E TASK_BUDGET_REBOOT. The old `get_errcount` assertion is gone.
- hold_console prints nothing after its marker. Its comment names tests/test_asy_system_service.py::test_the_supervisor_escalates_past_the_failure_budget as the test that pins the entry.
- Bites (bites_escalation.log, bites_escalation_b.log, 7/7 ok):

| Synthetic case | Old test | New test |
|---|---|---|
| Stale entry on the board, no round holds it | pass | FAIL |
| Rounds hold it, board cleared | FAIL | pass |
| Rounds hold it, stale entry too | pass | pass |
| No round at all | FAIL | FAIL |
| hold_console, board cleared | FAIL | pass |

- Through TwinBoard, the real script passes at gc.threshold -1 and 32768. Each run printed 11 rounds and 5 held the entry, as ErrNum [.., 44, 41] (TASK_RETURNED, TASK_BUDGET_REBOOT).
- **Set changed:** I removed the provokes_log marker.
  - Before: SYSTEM E TASK_RAISED + SYSTEM E TASK_BUDGET_REBOOT.
  - After: unmarked. The test leaves no entry in any FRAM-backed history.
  - The old set was also wrong on its own terms: `_dies_at_once` returns, so the entry is TASK_RETURNED (:330), never TASK_RAISED.
  - I did this on the crr2b4 ruling (re-derive the escalation set, then narrow or widen it). It is the stricter side. Undo it if you want the marker kept.
- Also in this commit: the README recovery-table row says the same, and the script's ds_facts verdict went from biting to fixed, with the evidence.

**Item 2: memory_stress's extended hammer (e8452ccc)**
- HTTP_REFUSED does land there. The load is 6 readers (`configured_max_connections()`, devices/dev.toml:14) plus the VOC writer, one client past the ceiling. A connection past the ceiling goes through asy_webserver_service.py:917-925, `_note_drop` and `wrn_s` (:799-802), and WEBSERVER is FRAM-backed on dev.
- About "run it through the twin": `--twin` only skips bench tests ("the twin has no bench bridge"). So twin_hammer.py boots the dev twin on 127.0.0.1:80 inside the namespace and runs the test function itself, unchanged, at its own `--soak-duration short` (60 s).
  - The old test FAILED twice: WEBSERVER counter 239, then 213, history holding only W 60 (HTTP_REFUSED).
  - The new test passed on the same boot.
  - Logs: twin_hammer_head.log, bites_hammer.log.
- The fix keeps the load and the duration. The test now asserts every FRAM-backed logger except WEBSERVER at counter 0, and WEBSERVER's history holding nothing but W HTTP_REFUSED and W HTTP_PEER_RESET.
- **Set changed:** before, unmarked (its own body required every FRAM-backed logger empty). After, CEIL = WEBSERVER W HTTP_REFUSED + W HTTP_PEER_RESET, the same set as the plain hammer.
- Synthetic bites (bites_hammer.log, 6/6 ok):
  - The ceiling pair alone: the old test FAILS, the new one passes.
  - A call timeout or an E entry in WEBSERVER, or any entry in SGP40 or SYSTEM: both fail.
  - Nothing logged: both pass.
- Residual limit: WEBSERVER's history is the newest 10 slots, so a non-ceiling entry early in a long soak can be pushed out by alternating ceiling codes. The log check already has the same limit for every marked test. Loggers other than WEBSERVER stay counter-exact.
- No added bench time.

**Item 3, partly done**
- serving_heap per-source (4a2e3ddf). I read allocation_need_per_source.py in full (207 lines).
  - Before: WEBSERVER E UNEXPECTED, WEBSERVER E CALLBACK, FRAM E ALLOC, SYSTEM W CONFIG_LOST.
  - After: WEBSERVER E CALLBACK, SYSTEM W CONFIG_LOST.
  - CALLBACK stays: asy_webserver_service.py:1003-1008 and :1013-1019 log it when a streamed source raises under a sieve.
  - CONFIG_LOST stays: the scratch-config boot, :753-756.
  - UNEXPECTED goes. Its sites are :796, which is only Microdot's errorhandler (registered at :617), and :948/:962, which are only in `_serve()` and the connection task. The script calls the handlers directly and no client connects.
  - FRAM ALLOC goes: FRAM is not in `fram_backed_logger_names("dev")`, so its entries die with the reset.
  - No CFGMGR entry can appear: the one defaults write runs at setup, before any sieve, and the script stages no write.
  - Open, not added: WEBSERVER E LOG_RAM_ONLY (asy_print_log.py:229-239), if a FRAM chunk write returns False under a sieve (asy_fram_manager.py:497-514). I did not verify whether that buffer can be missing there, so I took the conservative side.
- Not done:
  - The UART hazard set's SIZE_MISMATCH narrowing.
  - test_an_incomplete_command: reading `quiesce()` in full. CRr2b5's inference is still unconfirmed.

**Items 4 and 5:** not started, so there is no bleed list and no redflags change.

**Checks**
- Items 1 and 2:
  - lint_direct rc=0; mypy main, host and bench-conftest rc=0.
  - collect-only 201/232.
  - review_rows `--check` rc=0.
  - Readers: 1592 passed, 2 failed. Both failures are test_twin_record (the instruments with no entry, which are red at base, and the hash re-record).
  - checks_i1b.out, checks_i2.out, readers_i2b.log.
- Item 3: lint, mypy host, readers (1089 passed), collect-only and review_rows `--check` all rc=0 (checks_i3.out).
- **review_rows.py:** 8512 rows: CRr2 63, fixed 62, justified 128, biting 8259. One row moved from biting to fixed: the escalation script's facts row.

**Files whose twin record changes:** tests_hardware/bench/test_reset_reasons.py, tests_hardware/bench/test_memory_stress_bench.py, tests_hardware/bench/test_serving_heap_at_default_gc.py and tests_hardware/README.md.

**Deviation:** I appended item 2's entry to my own sets_map.txt with a `cat >>` heredoc chained to a `git diff --stat`. That is a file edit outside Edit/Write. It touched only my own log file; every later edit used the Edit tool.

**Deletions:** the worktree's typings link, three times, each as its own literal-path rm. Nothing was refused. I did not touch S/u35/laneC/crr2b4/plant_i1.

nothing of mine is running
