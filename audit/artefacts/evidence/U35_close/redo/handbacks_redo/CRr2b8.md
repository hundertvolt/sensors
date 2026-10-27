CRr2b8 hand-back, saved by the lead from the message it sent (2026-10-27). Commits 171144df, d340b368 on audit/u35-crr2b (on 7e7451f5).

U35 lane CRr2b8 hand-back. Items 1 and 2 are done, in two commits on audit/u35-crr2b (worktree S/wt-u35crr2b, on 7e7451f5). I did not start item 3 because I stopped at a seam at about 82 tool calls. Nothing is pushed, the tree is clean, and the typings link is removed.

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad. Logs are in S/u35/laneC/crr2b8/. Every run went through S/u35/laneC/crr2b8/run.sh, a copy of CRr2b7's wrapper with this lane's name and log folder. RUNS.md has 62 lines naming "U35 lane CRr2b8" (31 runs). There were no refusals, and I did not touch S/u35/laneC/crr2b4/plant_i1.

**Commits**
- 171144df: the Calibrate bench test waits out its own run, so its timeout warning lands in its own log window.
- d340b368: the scanner's segment-reading flags read a test's own text, never its decorators.

## Item 1: the calibration bleed (171144df)

**The change** (tests_hardware/bench/test_sensor_config_push_over_real_hardware.py):
- The test now carries `provokes_log` with one entry, ISL29125 W ISL_CAL_TIMEOUT.
- After the PUT answers, it takes `started` and calls a new helper, `_calibration_end()`. The helper sleeps until the window closes (`started` plus `_CAL_WINDOW_MS`, read with `_load.src_number`). It then polls ISL29125's history every 2 s:
  - it returns "timed out" as soon as W75 appears;
  - one SampleInterval (read from GET /sensors) plus a 10 s margin past the close, it returns "converged" if GainMeas holds a candidate, else None.
- The test fails on None ("the run never ended"). Otherwise it asserts exactly one W75 (`assert_module_logged_one_code`, events=1) if timed out, or an empty log if converged.
- I first used `assert_module_error_log_clean` with allowed_warnings. The scanner then flagged ns_allow_list, so I replaced it with the exact assertion per end.
- The old comment "never by warning" was wrong against src, and I replaced it.

**Where this departs from the brief, for your review:** a published candidate does not end the wait (agent, 2026-10-27).
- src publishes GainMeas on every stable sandwich (`_note_candidate`, asy_isl29125_driver.py:574-583, `_publish_candidate` :613-617). The run continues until three candidates agree (:582-583) or the window closes (:429-434, then :395-400).
- So a wait that stops at a candidate leaves W75 free to land in the next window. The bite below shows exactly that.
- A converged run shows nothing a poll could see, so the wait has no early exit.

**Tunables**, each with a Part N row:
- `l4.sensor_config_push_calibration_end_margin_s` = 10.0
- `l4.sensor_config_push_calibration_poll_s` = 2.0
- `isl29125.cal_window_ms`'s Dependants cell now names the test.

**Added bench time:** about 121-131 s per run.

**Synthetic bites** (bites_cal.py, bites_cal_b.log, 21/21 ok). Each case runs HEAD's test, the new test and a stop-at-candidate variant on a fake board in virtual time, each followed by an idle next test. Every window is judged by `assert_no_unprovoked_entry`.

| Case | HEAD's test | Its next window | New test | Its next window | Stop-at-candidate |
|---|---|---|---|---|---|
| Timeout at 120.5 s | passes | FAILS on W75 | passes | passes | passes |
| A candidate at 20 s, then timeout | passes | FAILS on W75 | passes | passes | its next window FAILS |
| Converged | passes | passes | passes | passes | passes |
| Never ends | passes | passes | FAILS | passes | FAILS |
| W75 past the bound (135 s) | passes | FAILS | FAILS | FAILS | FAILS |
| 30 s SampleInterval, W75 at 150 s | passes | FAILS | passes | passes | passes |
| An unrelated E CHIP_GET at the PUT | FAILS | FAILS | FAILS | passes | FAILS |

**Twin runs:** the dev twin on 127.0.0.1:80 in the namespace, via twin_cal.py.
- Each run executes HEAD's test (7e7451f5's text), a 135 s idle next test, the new test, then another 135 s idle next test, each window judged by the log check's verdict. Every logger's ring is dumped after, with the FRAM-backed ones flagged.
- **twin_cal_a.log**, both stages, on the pre-final assertion:
  - HEAD's test passes and its next window FAILS on ISL29125 W75.
  - The new test reports "timed out 123 s after its PUT" and passes.
  - SGP40 W35 SGP_WRITTEN_NO_TS appears in every window. The namespace has no NTP (asy_sgp40_driver.py:532-534), so later runs admit it as stated twin environment.
- **twin_cal_b.log**, gc -1, final code: HEAD's next window FAILS on W75 alone. The new test's window passes, and its next window passes. Stage 32768 of this run died on my own harness race: I committed item 1 mid-run, so `HEAD:` loaded the new text. That is not a test result.
- **twin_cal_c32768.log**, gc 32768, final code, old ref pinned to 7e7451f5: the same verdicts ("timed out 120 s after its PUT").
- Rings after every run: ISL29125 counter 1, holding only W75 from the new test's own run. No other FRAM-backed entry except the ambient SGP40 W35. Zero memory markers.

**Checks** (checks_i1b): lint_direct rc 0, mypy host rc 0, collect-only 201/232. Readers: 1265 passed, 2 failed, both test_twin_record (red at base, plus the hash re-record). review_rows `--check` rc 0.

## Item 2: redflags.py decorator text (d340b368)

**The change:**
- `py_flags`' segment now starts at the def line.
- A new `walk_own()` gives `ast.walk(node)` in its own order minus the decorator subtrees. It is used in `ns_flags` and in `Scan._walk_credit`, so hw_no_log's helper names never come from decorators.
- I dropped `start` from py_tests and py_flags.

**Self-test:** I added two bench cases first.
- Red on the old code (redflags_selftest_red.log): the decorator-named log case expected hw_no_log and got []; the decorator seed word case expected [] and got ns_seed_text.
- Green now, 24/24.

**Full-scan diff** (records_before.json vs records_after2.json, redflags_diff2.log):
- 5 rows gain hw_no_log:
  - end_to_end_timing burst
  - heap_under_connection_ceiling `test_report_the_boards_own_connection_wall`
  - network_resilience console test
  - serving_heap `test_every_source_and_route_fits_a_small_free_run`
  - serving_heap `test_serving_sweep_at_the_reactive_default`
- 2 rows lose ns_seed_text: network_resilience's wifi outage and wifi flaps tests. Their verdicts had said the seed word sat in the marker's reason.
- No other flag or credit changed. A first version had reordered credit strings; I fixed that by keeping ast.walk's order.

**Verdicts:**
- The 5 new rows are "fixed" by the autouse log check, each naming its provokes_log set.
- I deleted the 2 stale ns_seed_text verdicts.
- The four new keys were not placed in strict alphabetical order. This is cosmetic only.
- review.md is re-rendered. lint_direct rc 0.

## Sets changed
- calibrate test: before, unmarked. After, ISL29125 W ISL_CAL_TIMEOUT. The only site is asy_isl29125_driver.py:395-400, reached from :429-434 each cycle via `_read_isl` :661.
- No other set changed.

## The bleed list
I read src for these. bleed_scan.log lists every bench test that starts device activity, with its markers and last statements.

**Settled:**
- calibrate: fixed here.
- `_load.readers` users: threads joined, and the caller fails on any still alive (_load.py:321-332).
- UART hazard run: waits for the run's end and for the echo to resume (test_uart_link_under_api_load.py:285-298).
- lwip send stall: waits for the slots to drain (:162-167).
- PauseTime test: waits to 0.
- Outage, flap and garbage-SSID tests: `recover_by_reset` until serving or STA.
- Garbage NTP host: until ntp_synced.
- Reboot tests: readiness waits plus ends_unreachable carry.
- burst test: joins its threads (end_to_end_timing.py:112).

**Harmless unless faulted, not settled:**
- ResetVOC: the reset completes at the next SGP40 cycle, after the test ends. It logs only SGP40 E SGP_BACKUP_CLEAR if the FRAM clear fails (asy_sgp40_driver.py:396-409). The next window would still catch that fault, but would blame the wrong test. A settle would wait one SGP40 cycle; that is your call.

**Open, not finished:**
- heap ceiling test: the holder is stopped and joined (:82-83). Its closed connections' server-side handling can still log WEBSERVER W HTTP_PEER_RESET, HTTP_CALL_TIMEOUT or HTTP_BAD_HEAD (asy_webserver_service.py:942-953, per-call timeout 5 s, :159-160) after the test's last read. It has no drain wait like the lwip test's `_wait_for_slots_to_drain`.
- console test: its adversarial sockets close at the end. I did not prove its server tasks finish inside its window.
- I did not prove the NTP re-sync after the outage and flap recoveries quiet before each test ends.

## review_rows.py counts
8512 rows: CRr2 63, fixed 67, justified 128, biting 8254. Five rows moved from biting to fixed.

## Files whose twin record changes
tests_hardware/bench/test_sensor_config_push_over_real_hardware.py.

## Not done
Item 3: the overlap fix in its two sibling scripts and the HTTP bench counterpart of the ISL test.

## Deviations
- I used `git stash push`/`pop` on audit/sweeps/redflags.py so item 1 could be checked and committed on its own.
- Two deletions, each its own literal-path rm of the typings symlink.

nothing of mine is running
