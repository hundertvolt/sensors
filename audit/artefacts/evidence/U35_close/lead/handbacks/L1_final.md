L1 hand-back (lane L). Branch audit/u35-l in S/wt-u35l, head abdeb6f on 152f1ca. One commit, five files. Nothing is uncommitted. Nothing of mine is running. About 58 tool calls. The session restart at 02:31 cut off only a wait call. Batch pid 666 survived and finished rc=0, and I wrote its done line.

Verdicts:
- LEAD NOTES 38: applied. While a sweep runs, tests/_cancel_sweep.py swaps asyncio.Lock.release for a counting stand-in and restores it on exit. The stand-in counts each call on a lock that is not held (the one call lock.py:22-23 refuses), then calls the real release. Every count, cancelled or completed, fails with "<where>: a lock refused N release(s): a double release". A floor at entry checks that one refused release is counted. Seen failing first, with a double release planted in Lockable.__aexit__: the old sweep missed it (uart_driver 166/166, uart_link 46/46); the new sweep failed both ("cancelled after 1 turns: a lock refused 1 release(s)..."). A scratch path bit each branch on its own (cancel branch, completion branch). The floor was bitten with the count dropped ("the release ledger did not count a refused release").
- LEAD NOTES 56: applied. The refusal test moved unchanged into tests/test_async_harness.py, after run()'s refusal test. That file's header now names run_to_interrupt()'s refusal. It still bites there: with the check removed from a scratch harness, it is 17/18.
- LEAD NOTES 55: nothing to change. None of the 20 stand-ins reaches UTCTime or a VOC backup. The only reader of the flag is ntp_clock_valid() (src/asy_ntp_client.py:553). No stand-in test calls it, and none builds SgpBackup or the generated module. Named with why:
  - notification :241 reads only cettime(), which gates on utc_now(), not the flag (asy_ntp_client.py:528-531).
  - ntp 747/758/768/777/786 test the state helpers themselves.
  - ntp 951 (force_sync), 1676-1742 (7 retry tests), 1857/1880/3150 (cadence), 2393 and 2700 read Synced or the retries only.
  - ntp 2052 sets Synced without the clock on purpose.
  - The tests that do read the flag (1005, 1021, 1908) use the real _handle_ntp_sync_success(). The list is in S/u35/laneL/standins.txt.
- LEAD NOTES 66: applied.
  - The put matrix gains staleNotDriven(), a check "lists as not driven only actions some device's definitions still declare", and a planted case (fixture-device without UartHazards). With a stale row planted, head red and base green.
  - source-constants gains 4 readStringSetConst cases. Two bitten reader copies: no export/escape fails 2 cases; no ^ anchor fails the nested case.

Runs (all in RUNS.md; zero MemoryError and zero "memory allocation failed" in every log):
- batch3: the 15 _cancel_sweep importers, plus config_manager, async_harness and notification, at -1 and 32768. 36/36 rc=0. Logs: S/u35/laneL/b3/, rows in batch3.tsv.
- I killed batch1 and batch2 myself (pids 30935, 32085) before edits; their partial rows were green.
- Pair on test_uart_comm_cancel_sweep, base helper against head, alternating: 39.90→37.42 s (-1), 41.90→39.26 s (32768). No growth. pair/pair.txt.
- JS in the namespace: lint, typecheck, lint-ceilings 4/4, source-constants 11/11, put matrix -t actions 4 passed. Logs in js/.
- ruff clean. Both main mypy passes clean, cold cache; the typings link is removed.
- The 12 commit checks plus test_js_api_mirrors, test_no_variant_literals and test_radio_shape_corpus: 856 passed, 1 failed.

Red checks, not mine:
- tests_scripts/test_tunables_register.py:253: config.flush_slice_bytes has no Part N row (known; waits on D).
- tests_scripts/test_microtest.py:305: tests/test_digital_twin_uart_link.py:454 is a json.loads site the allow-list lacks. That file is lane U's, and it is the same at base 152f1ca. The lead adds the row or U removes the call.

Decisions (agent, 2026-10-22):
- The count is a class attribute swap for the sweep's lifetime, so locks built inside src/ are counted too.
- Completed counts are checked, not only cancelled ones.
- The ledger floors itself at entry.
- A permanent planted test for staleNotDriven sits beside the existing PlantedCmd one.

For the lead:
- E's _BalanceLock/_assert_balanced in tests/test_asy_base_classes.py is now partly redundant with the sweep. It is E's file, so I left it.
- No allow-list row is orphaned.
- Effect is test code only: no device and no mode (STA, AP, Silent, Off, USB) changes.

Logs: S/u35/laneL/ (bite38/, bite56/, b3/, js/, pair/, checks.log, microtest.log, mypy_*.log).