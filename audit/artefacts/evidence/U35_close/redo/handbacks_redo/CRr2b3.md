CRr2b3 hand-back, saved by the lead from the message it sent (2026-10-27). Commits 83dbc882, 575f8c22 on audit/u35-crr2b (after 2d73a934).

U35 lane CRr2b3 hand-back. I stopped at a seam after item 1, at about 76 tool calls.
- Branch audit/u35-crr2b in S/wt-u35crr2b moved from 2d73a934 to 575f8c22.
- Not pushed. The tree is clean.
- Item 1 is done and committed. Items 2, 3 and 4 are not committed. For items 2 and 3 I have done research only, given below.

S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad. The logs are in S/u35/laneC/crr2b3/.

**Commits**
- 83dbc882, item 1: provokes_log names the entries its test may leave, and the bench log check reads marked tests too.
- 575f8c22: verdicts for the log check's two new fixture-driven cases, then a re-render.

**Item 1: done**

*Marker form.* `provokes_log("<why>", (logger, kind, catalog name), ...)`.
- `error_log_helpers.provoked_entries()` resolves each entry through tests/_error_codes.py.
- It refuses, with a ValueError:
  - a reason alone;
  - a keyword argument;
  - an entry that is not a 3-tuple, or whose kind is not E or W;
  - a name with no live catalog row of that kind, whether unknown, retired (WLAN_OFF) or of the other kind.

*Refused at collection.* bench/conftest.py's `pytest_collection_modifyitems` raises a `pytest.UsageError` that names each bad test. It applies to bench items only, because the flash tier is CRr2c's.
- Proved on the real tier: a plant tree with one marker cut to its reason gives collect rc=4 and names the test (`collect_plant_i1.log`).
- The real tree collects 201/232 (`collect_i1.log`).

*Fixture.* `no_unprovoked_log_entry` now reads marked tests too. It fails on any E or W entry outside the test's set, and it does not require a set entry to appear.

*Added: an `ends_unreachable` marker,* in markers.py's one table.
- Why: once marked tests are read, four tests would fail on an unreadable end. These are the hotspot real-credentials and second-streak tests, and serving_heap's two isolated-board tests, which leave main.py stopped.
- How it works: an unanswered end of a test with this marker carries its first read on. The next read that answers closes the window against the union of the sets it spans: the next test's before-read, its after-read if that read also fails, or one last read at the session's end (`log_check_carry_settled`).
- Without the marker, an unreadable bound still fails plainly, as before.

*Tests.* tests_scripts/test_bench_log_check.py now has 37 tests (14 new or replaced).
- 10 of them were red on 2d73a934's fixture and helpers (plant 0).
- `plants_i1.out` shows all 10 plants caught: plant 0, the set admitting nothing, the set admitting a whole logger, a reason alone accepted, no live row accepted, the collection refusal off, the carry dropped, the carried set not joined, the session end left unsettled, and ends_unreachable ignored.
- Earlier red log: `i1_red.log` (the marker was missing from the table). Green log: `i1_green1.log`.

*Checks.*
- lint_direct rc=0 (`lint_i1c.log`, after fixing Q003, PLR0913 and RUF043; `lint_i1.log` was the red pass).
- mypy: main, host (re-run after the fixes, `mypy_host_i1b.log`) and the bench-conftest pass are all clean.
- Readers: 1483 passed, 2 failed (`readers_i1.log`). Both failures are test_twin_record: the instruments with no entry (red at base) and the hash re-record.
- `readers_i1b.log`: 1138 passed (the log check, citations, comment cap, decision vocabulary, persistence-write marker completeness, conftest constants, runners, harness helpers).
- No flash file and no MicroPython file changed, so there was no `--twin` run and no Unix-port run.
- tests_hardware/README.md "The bench log check" is updated.

**The 29 sets**
- Each entry's src file:line is in `S/u35/laneC/crr2b3/sets_map.txt`. `mark_sets.py` applied them.
- Entries summed over the 29 markers, per logger: WEBSERVER 39, WIFI 18, SYSTEM 8, UART_init 8, UART_resp 8, CFGMGR_WIFI 1, NTP 1, FRAM 1.
- Shared groups:
  - The ceiling group is HTTP_REFUSED (asy_webserver_service.py:925) plus HTTP_PEER_RESET (:953). This is the same pair as test_network_resilience.py:151 `_CEILING_TRACES`.
  - The outage group is WLAN_NO_AP (asy_wifi_service.py:623) plus WLAN_AUTH_FAILED (:620). This is the same pair as `_assert_wifi_log_has_only_benign_outage_warnings`.
  - Where a test parks or stalls clients, the set has both HTTP_CALL_TIMEOUT (:348 or :942) and HTTP_REQUEST_CAP (:942), because which timeout ends first depends on timing.
- Narrow choices I made deliberately. Please confirm or widen:
  - WLAN_CONNECT_FAILED, WLAN_STATUS_UNKNOWN and WLAN_NO_VERDICT (:626, :632, :636) are left out of the outage group, because the outage tests already fail on them.
  - An NTP attempt caught mid-flight by an outage is left out of the outage tests' sets, so the check surfaces it.
  - test_an_incomplete_command lists only SYSTEM W CONFIG_LOST. I reason that the planted EIO's own entry cannot persist, because its FRAM write is the one that is cut.
- Less certain sets, derived from the test's own assertions and src without reading the whole device script:
  - The hazard run: UART_init and UART_resp each get 8 codes from asy_uart_comm.py's fault sites, since which side logs what depends on the hazard.
  - serving_heap per-source: WEBSERVER E UNEXPECTED (:796) and E CALLBACK (:1007/:1018), FRAM E ALLOC (asy_fram_manager.py:493-633), and SYSTEM W CONFIG_LOST.
  - The escalation and stack-exhaustion SYSTEM sets.

**review_rows.py:** 8506 rows: CRr2 63, fixed 61, justified 128, biting 8254. `--check` rc=0 (`review_rows_check_i1c.log`). The two new rows got "biting" with their plant evidence.

**Twin record changes for the lead:** bench/conftest.py, error_log_helpers.py, markers.py, README.md, and the 10 bench files: end_to_end_timing, heap_under_connection_ceiling, hotspot_role_reversal, memory_stress_bench, modlwip_send_stall, network_resilience, reset_reasons, serving_heap_at_default_gc, uart_link_crc16, uart_link_under_api_load. No allow-list row is needed.

**Item 2: not started in code. Do not land the mechanism alone.**
- Checking the segments before each clear will make every unmarked test that provokes entries and then clears fail on the bench, unless it gets a marker with its set.
- `S/u35/laneC/crr2b3/clear_tests.out` lists 56 bench tests that clear (`clear_tests.py`): 45 unmarked, each with the codes and modules its body names.
- CRr2b2's map counts 22 tests that "clear at end after provoking". Examples: network_resilience's NTP and DNS garbage tests, slowloris (HTTP_REQUEST_CAP), nonsense field values (BAD_ARG on CFGMGR_BMP3XX and WIFI), and bus_concurrency_under_api_load's degradation tests.
- So item 2 is the mechanism plus about 22 more src-derived sets.
- Planned design: `reset_all_error_logs()` already reads GET /status before its PUT, through `save_errcount`. It would keep that parsed read in `_CLEARS` (a list in place of the count). The fixture would then check before → first pre-clear read (continuity), each clear → the next pre-clear read (all of it new), and the last clear → the after-read. This adds no read and no write.

**Item 3, research only: yes, the bleed is real.**
- test_isl29125_calibrate_command_push_over_real_rest is at bench/test_sensor_config_push_over_real_hardware.py:165. It ends right after its PUT.
- A run that does not converge ends at `_CAL_WINDOW_MS` = 120 s (asy_isl29125_driver.py:118). `_end_calibration(converged=False)` then logs W ISL_CAL_TIMEOUT (:400).
- The test itself says the bench light is not arranged, so a run that never converges, and so a W75 in a later test's window, is likely.
- I found no REST field that shows a run in progress (no grep hit). The fix needs one, or a bounded wait on what the measurements body shows. Not done.

**Item 4: not started.**

**Deviation:** I ran one lint pass directly from the shell, outside run.sh. Its rc=1 was only because the shell tools were not on PATH; ruff was clean. I added its line to RUNS.md by hand. All other runs are in RUNS.md through run.sh.

**Deletions:** the typings symlink and the plant tree, each as its own literal-path rm.

**Product question:** none.

nothing of mine is running
