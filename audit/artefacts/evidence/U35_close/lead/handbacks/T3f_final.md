T3f hand-back (lane T, audit/u35-t, S/wt-u35t). One commit, b7d9f31, on 7f5501d. Nothing is uncommitted and nothing of mine is running. I used about 72 tool calls, so I stopped after (f), (h) and (i). No src/ change, so no rebuild.

**Steps by verdict (step 125)**
- **(f) applied:** `watchdog_fault_block`, `watchdog_fault_main_exit` and `watchdog_fault_supervisor_raise` (family watchdog_fault, every device). Each reads `WDT_AT_FAULT`, waits for `WATCHDOG_WOULD_TRIGGER` with the twin still up, and checks `would_have_triggered_count >= 1`. For raise and main-exit it also checks that the exit's `feed_count` equals the count at the fault.
- **(h) applied:** `a_bounded_fault_storm_keeps_every_logger_within_its_persisted_log_rate` (family fault_storm). The storm is 5 SGP40 measure-read faults (codegen's `_MAX_MODULE_ERROR`) plus a burst above the ceiling.
  - Each `fram_writes_by` entry must stay within window / 627 ms x 2. The 627 is read from the suite's `_PERSISTED_LOG_CHUNK_WRITE_MS`.
  - `fram_writes_unattributed` must be 0, the entries must sum within `fram_writes=`, and there is no reset. A missing field fails through the parser.
- **(i) applied:** `zero_think_time_readers_saturate_then_recover`. Four /status readers send 20 reads each, beside an unchanged DebugLevel PUT every 0.5 s.
  - Each reader must be answered at least 10 times, every answer must parse, and SYSTEM's count must not move.
  - After the load, GET /status and the PUT must each answer within `_DEFAULT_OUTER_CAP_S`. The writer's answers are printed, not asserted.
- **(g)(a), (g)(b) and folds (1)-(3): not started (budget).** Facts I found for them:
  - The harness boots in AP mode, so (g) needs a PUT of SSID plus NTPHost and a relaunch on the same state.
  - Under `unshare -n` the NTP code is NTP_NOT_SENT, not NTP_NO_REPLY (suite `_ntp_unreachable_verdict`, `_route_leaves_host`). The harness may not import `tests/`, so it cannot use the `code()` helper.
  - Fold (3): we run as root, so a skip by uid would always skip. A write probe plus `setpriv --bounding-set=-dac_override` would let it run here.
  - Fold (1) uses `HTTP_PEER_RESET`. Fold (2) needs a `--fault` MATCH that only the config snapshot hits (`DEVICE:OP:TIMES:MATCH`, digital_twin/launch.py:500).

**Seen failing first (plants in their own scratch trees, arzi, at -1 and 32768 alike)**
- Plant A (the runner keeps feeding after the fault; block sleeps only 1 s): all three fail with "the watchdog did not engage within 8.5 s of the fault and its margin".
- Plant B (each history write repeated 40 times): "loggers over twice the persisted-log rate, 122 writes over the 38364 ms run: {'SGP40': 1068, 'WEBSERVER': 164}" (126 at 32768).
- Plant C (the server refuses every connection after 30): "a reader was answered 4 times of 20, under the floor of 10".
- Two fixes came out of the bites, so failures name the behaviour (agent, 2026-10-22):
  - (h) now checks the rate before the storm's liveness; it first failed on the streak check.
  - (i)'s recovery requests and its SYSTEM read now report a refusal as such; they first ended on a bare RefusedError.

**Controls:** all 5 pass on all 6 devices at both stages, mem=0. After the edits, (h) and (i) were re-run on all 6 at both stages, and (i) again on arzi and dev at both stages: all pass.

**Times (new scenarios, so there is no base):** (f) 10.4-13.7 s each; (h) 10.0-11.0 s; (i) 18.8-28.8 s (dev is the slowest). A device's 5-scenario run takes 62-77 s. The readers are unchanged in count: scenarios 60 passed in 2.4 s, matrix 18, errcount 134, soak 24.

**Red, waits on lane D:** `test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree`. SPECIFICATION.md Part N has no rows for `l2.zero_think_reads_per_reader` = 20, `l2.zero_think_reader_floor` = 10 and `l2.zero_think_writer_period_s` = 0.5 (scripts/_digital_twin_scenarios.py:147-151). All three values are estimated (agent, 2026-10-22).

**Green:** ruff; the host mypy pass, cold (306 files, 0 issues); the other 11 checks (796 passed; the one warning is the uninitialised datasheets submodule); the 4 readers.

**Finding for the lead (class 5/2, new):** each SGP40 storm event writes two persisted entries: the read failure, then `err_s("Error counter increased to", errno=_ERR_STREAK)` at src/asy_base_classes.py:584.
- In every control SGP40 wrote 28 counted writes against a bound of 30. The margin is that thin only because the window includes the idle boot.
- On a host where the run takes under about 8.8 s, (h) would fail.
- A sustained 4-in-5 fault pattern gives 1.6 entries/s per module, which is the 627 ms rate's ceiling. I left the bound as written.

**Decisions (agent, 2026-10-22)**
- The watchdog cases run on every device, not on the first one only, because the supervised task set is each device's own graph.
- The storm window runs from spawn to exit, as the chip counts.
- The storm faults SGP40 only, setup spared, as the loop-lag storm does; the WEBSERVER refusals are the second logger.
- (g) and the folds are deferred whole rather than left half-done.

**Effect per mode:** test-only. AP mode on every device at both stages; STA, Silent, Off and USB have no change.

**Owed to T4:** digital_twin/README.md's test list has no text on the five scenarios.

**Scan (my file, all classes):** nothing new. The writer's refusals are counted and printed. A refused SYSTEM read becomes None and fails the verdict.

**Allow-lists:** no row orphaned. Relay: none.

**T4 / next block starts** from b7d9f31, clean. Left: (g)(a), (g)(b) and folds (1)-(3), each seen failing first; the README text; the Part N rows (lane D).

**Runs** (all in RUNS.md): r1 rc=0 (12 controls rc=0; pA, pB and pC rc=1 as planted). r2 rc=0 (12 controls rc=0; pB2 and pC2 rc=1). r3 rc=0 (4 controls rc=0; pC3 rc=1). checks12 rc=1 (the red above). Readers all rc=0.

**Logs:** S/u35/laneT/t3f/ (runs.sum, logs/, ctl/ with the twin logs and state, the edit scripts, plants.py, r1-r3.sh, commit1.txt). The plant trees are deleted.