U3e hand-back (lane U). The head is **a3c3392** on 181c954, branch audit/u35-u, S/wt-u35u. Nothing is uncommitted and nothing of mine is running. I used about 70 tool calls, so the remaining steps go back (CHECKLIST 21).

**Steps**
- **Twin pacing: applied (14e5407).** Each reader starts a GET at every multiple of 2500 ms on the driven clock, and its response writes pause on that clock too. Every run now serves exactly 249 reads at both stages (83 per reader). Under U3d's real-clock readers it was 243-281 at -1 and 1464 at 32768. All assertions are kept. A new exact assertion checks that every reader starts a read at each period start during the run. The test's own PUT and final GET keep the real 1 ms pause, because the clock moves only inside run_until.
- **Times for the twin file (s, paired bfc6519 → head):** 54.70 → 61.30 at -1, and 58.60 → 76.28 at 32768 (U3d had 128.3). The growth is the new test alone, which takes 7.0 s at -1 and 16.7 s at 32768. About 19 ms of each read is at -1; at 32768 the reads cost most of the 16.7 s.
- **Bites (scratch copies of src):** U3d's three still bite: the crossing, the sweep inversion, and the first value (208442 > 208370). The new guard bites on a status read held 3 s while the run is pending: 126 reads instead of 249.
- **Bench: applied (9f01fd4), collected only (5 tests).** The new test is `test_a_hazard_run_under_the_readers_load_reports_every_verdict`. 3 readers GET /status until the run ends. The host judges every verdict as the twin does, reading `_HAZARD_FIELDS` from the src text. It also checks Failures unchanged, the echo resumed, the WEBSERVER counter at 0 and no task ended. The silicon run is parked for hardware session 1.
- **Relays: done.** I wrote 13 lines under `## D`:
  - E.6.6, J.7 :9607-9609 and README :1083-1084;
  - A.8's UartHazards sentence and G.2 naming `_run_status_cmd()`;
  - BACKLOG question 5's removal and the two hazards left out;
  - TAG lines: U3d's three (:145, :147, :154) and my two (:151, bench :59). U3a's five were already there;
  - three rows found by the checks: C.9, I.2 and A.11.
- **D.15: applied, one commit per file** (8848de0 9b4a29e 10c38f6 94e93a8 36e2c59 e79da0a a0e0af0 a3c3392): codegen, definitions, the two buildgen tests, link_driver, twin_link, uart_comm_hazard, webserver_service.
  - Each commit keeps the same line multiset and the same top-level node multiset (a class counted by its members).
  - Two classes moved up because CPython or ruff evaluates the annotations: `_Ctx` in codegen and `_Readers` in the twin file.
  - The regenerated src for all six devices is identical apart from `_BUILD_DATE`.
  - Both src files were already in order. The checker covers Python only, so JS was not checked.
- **Checks:**
  - ruff is clean after the `_Readers` move. All 4 mypy passes are clean.
  - MicroPython files on the head pass at both stages, with zero memory markers: link_driver 43/43, webserver_service 224/224, twin_link 21/21, uart_hazard 123/123.
  - The 63 readers and the 12 checks are green, except the reds below.

**Red checks, waiting on others** (most come from U3a's src change, and no earlier U block ran the 17 scans)
- tunables_register: 10 tags with no Part N row. They wait on D2.
- task_inventory (4 failures) and task_tops (16): all from `_two_initiations()` at src/asy_uart_link_driver.py:204-205. It has no C.9 row (relayed to D), and its tasks run `uart_set()` with no task top. **That top is a src fix and is still to do.**
- memory_catalog: `_run_hazards`'s `_hazard_facts` needs an entry in `_RUN_PHASE_ALLOWED`. That is the lead's allow-list. The I.2 row is relayed to D.
- threat_model_statement: A.11 must name UartHazards (relayed to D).
- const_mirrors: test_uart_comm_hazard.py:76 (`= 4`) and tests/test_digital_twin_uart_comm_hazard.py:38 (`= 2`, not lane U's file) share a name with src's new `_RECOVERY_ATTEMPTS`. **Proposed fix, still to do:** rename the src constant to `_HAZARD_RECOVERY_ATTEMPTS` and update its three readers (twin link, bench, link-driver test). A const() rename should leave the bytecode identical; confirm with mpy-cross.
- twin_record: red, as expected.

**Silent-failure scan** (classes 1-7, all modes, over every file lane U changed). One new finding, class 1, at src/asy_uart_link_driver.py `_sweep_fields`, `got = ... if await self._write_raw(...) else None`. A raw write that fails is recorded as "not ACKed". For an illegal value that is the expected verdict, so a dropped frame passes silently. It is reachable in STA and AP on dev under load. Per D.1 it is flagged, not fixed. Everything else is covered: refusals answer Failed, raises are logged, the supervisor sees task ends, and the stateless mock is U3c's decision.

**Decisions (agent, 2026-10-21)**
- The readers' period is 2500 ms, which keeps the -1 load. Their writes moved to the driven clock.
- The bench bound is 600 s, an estimate. The bench needs no device-script change, because the run is the firmware's own route.
- I ran the 12 checks once on the final tree, not before each of the 10 commits. Each reorder commit is checked by its multisets.

**Runs** (all logged in RUNS.md):
- exp1 2641 rc 0.
- batch1 4002 rc 0.
- static.
- batch2 9882: I stopped it myself (generated_src went stale after the codegen reorder), rebuilt, and restarted it as 11012, which finished.

**Logs:** S/u35/laneU/u3e/runs/ (summary.tsv, summary_batch1.tsv, bite_*.log, twin_*.log, scans17.log, r_*.log) and st_*.log.

**The next block starts at a3c3392 with:** the const_mirrors rename, the task top for `_two_initiations`, and the class 1 sweep finding.