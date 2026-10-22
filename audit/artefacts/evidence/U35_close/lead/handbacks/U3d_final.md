U3d hand-back (lane U). Commit **181c954** on 962602d, branch audit/u35-u, S/wt-u35u. Nothing is uncommitted and nothing of mine is running. About 68 tool calls.

**Steps**
- **Twin proof: applied, with deviations.** tests/test_digital_twin_uart_link.py has a new test. It starts the run with PUT /status {"UartHazards": true} while 3 readers GET /status back to back. It reads every verdict back through GET /status: two initiations, the crossing, and the field sweep against J.3/J.4. It also asserts the echo resumes with 0 failures, the initiator's log is [REENTRANT, NO_ACK], the webserver logs no error, no feed is late (would_have_triggered 0) and reset_count stays 0.
- **Mock mirror: done.** In a scratch tree at 962602d with bfc6519's js/mock-server.js, the Promise.all form fails at definitions-mockdata-coverage.test.js:127 (UartHazards: Valid expected, Invalid received; 1 failed, 17 passed). On the head: 18/18.
- **Runs: done.** Zero memory markers in every log.

**Seen failing (bites in scratch copies of src/asy_uart_link_driver.py)**
- Crossed SET reported as completed: fails at :887.
- Each sweep ACK reported inverted: fails at :894, on the cmd verdict.
- Plant "any answer is an ACK" did not bite. The twin peer answers only legal frames, so it reports the same verdicts. Not a valid plant.
- Plant "first value sent for every value": caught by the exact virtual bound at :856 (208442 > 208370).

**Times (s, paired)**
- Link driver, f6f54cc → head: 2.39 → 3.40 at -1; 2.52 → 4.86 at 32768. All 43/43 pass. The growth is U3a-U3c's new tests, and the file stays under 10 s.
- Twin link, bfc6519 → head: 55.05 → 61.92 at -1 (+12.5 %); 58.73 → 128.29 at 32768 (+118 %).
  - The new test's reads grow with its wall time: 243 at -1, 1464 at 32768.
  - **Not efficient yet at 32768. This is U3e's first item.** Proposal: pace the readers on the driven clock, so each run serves a fixed number of requests at either stage.
- Dev files on the head, -1 / 32768:
  - sensortask 44.96 / 52.37, **89/91**;
  - construction 2.47 / 2.65, 4/4;
  - timer_pool 43.34 / 43.60, 4/4;
  - dtsi 23.08 / 23.42, 4/12 passed (8 skipped by design: arzi only).

**Red, in another lane's file (tests/_sensortask_scenarios.py, V's per LEAD NOTES 20)**
- Both pass at f3fff0e and fail at bfc6519, on dev, at both stages.
- :2491: the test expects sensors == {SGP40, UARTLINK}. Since bfc6519, dev also has UART_init (the hazard report). The fix is to add the initiator's name when `_has_uart_link`.
- :2728: UTCTime stays None after the test patches ntp_issynced. Cause not traced; it lies between f3fff0e and bfc6519 (the 78fb201 merge or bfc6519). Output: runs/dev_sensortask_-1.log:479, runs/bisect_*.log.

**Checks**
- ruff clean. mypy twin pass: 0 issues in 52 files.
- The 12 checks: 1 red, test_tunables_register. It now has 8 tags with no Part N row: the 5 old ones plus my 3 at test_digital_twin_uart_link.py:145, :147 and :150. They wait on D2.

**Decisions (agent, 2026-10-21)**
- The link runs on DrivenTime, and the twin wire's byte times run on it too (link._now_us). In one interpreter the readers' work is never charged to a reply budget (J.7). Dev's 1000 ms timeout is unchanged, and the run is 208370 virtual ms.
- The readers drive WebserverService._serve() over in-memory streams. A real listener would need a band in tests/_port_bands.py, which is not lane U's file. The socket path stays the bench test's.
- Each response write pauses 1 ms on the real loop, as a socket send does.
- The virtual bound is the measured 208370 with no margin.
- A test feeder runs at timeout/4.

**Effect per device and mode:** test-only, dev only. STA and AP reach the route; Silent and Off have no API; USB is unaffected. The other five devices are unchanged.

**Silent-failure scan** (my file, classes 1-7, all modes): none found.
- The not_ok list is capped at 8, which is safe by construction: the assert fails on its first entry.
- A reader that dies is not lost: its error is raised by the await in cancel() (tests/_async_harness.py:229).

**Deviations**
- The 12-check run (68.4 s) has no RUNS.md lines.
- Three diagnostic or bite runs started with 5-6 heavy processes on the host. They run on the driven clock, so their results do not depend on timing.

**Runs:** batch pid 16292 and bisect, both with RUNS.md lines; results as above. The scratch worktrees and bite copies are removed.

**U3e starts at 181c954 with:**
1. The 32768 efficiency of the twin test.
2. The scenario reds above, routed to V.
3. The bench collection.
4. The relays: 3 tag rows for D2, and G.2 naming `_run_status_cmd()`.
5. D.15 order, the 17 scans, the readers, and test_twin_record.

**Logs:** S/u35/laneU/u3d/ — runs/summary.tsv, runs/*.log, js_cov_mock.log, js_cov_head.log, bite_crossing.log, bite_sweep2.log, bite_sweep3.log, diag_*.log, checks12.log, mypy_twin.log.