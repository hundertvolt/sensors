U3f hand-back (lane U, its last block). The commit is **6f6e99a** on 8039259, branch audit/u35-u, in S/wt-u35u. Nothing is uncommitted and nothing of mine is running. I used about 63 tool calls.

**Items (all three applied, in one commit, because they touch the same files)**
- **Task top: applied.** The two tasks in `_two_initiations()` (src/asy_uart_link_driver.py:215-226) now run `_initiate()` (:146). Its top calls report_if_fatal and logs through `err_s` with the catalog's shared E23 UNEXPECTED (`_ERR_UNEXPECTED = const(23)`, :28), then answers None. The run goes on, and its verdict shows the raise. task_tops is green (19 passed).
- **The constant rename: applied.** The constant is now `_HAZARD_RECOVERY_ATTEMPTS` (:56). Its readers changed with it: the link driver test, the twin link test and the bench test. The tag line is unchanged. const_mirrors is green. mpy-cross on the rename alone gives identical bytes (3516 B). The head is 3680 B, as expected for a behaviour change.
- **Class-1 sweep finding: fixed.** A raw write that fails now records None, where it used to record "not ACKed" (:206).
- **Judges made exact (needed so a None cannot read as a refusal).** I changed the TwoInitiations judge in the link driver test, the twin and the bench. `sorted(r is True)` read [True, None] as a pass. The new judge accepts only [True, False] or [False, True]. The FieldSweep judges already compared exactly, so a None fails the run there too.

**Seen failing first** (src with the rename only):
- Link driver file: 43/46 passed. The planted raising `uart_set()` made the run raise "ValueError: planted initiation fault". The planted failed raw write gave `[['cmd', [False, True], True]]` in both CRC modes.
- Twin plant: the same `[False, True]`.
- Bite of the exact judges (a scratch src whose refusal reads None): the link driver's full-run checks failed in both CRC modes, and the twin hazard test failed on `TwoInitiations [True, None]`. The scratch copy is deleted.

**Effect:** dev only, since the other five devices do not construct this module. STA and AP reach it through PUT /status's UartHazards. Silent and Off have no API. USB is unaffected. Nothing is stored. The wire format and the protocol module are untouched.

**Runs on the head (logged in RUNS.md; times in s at -1 / 32768; zero memory markers in every run):**
- link_driver 46/46: 3.60 / 4.78. U3e had 3.42 / 4.73, so it grew 0.18 s at -1 (5%).
- twin_link 22/22: 61.36 / 76.05. U3e had 61.30 / 76.28, so no change. The new plant takes about 0.5 s.
- webserver_service 224/224: 4.38 / 6.99.
- uart_hazard 123/123: 102.83 / 106.85.
- The bench file: 5 tests collected.
- I stopped batch pid 29004 myself while it was waiting at the load gate, because mypy had found a plant's parameter name. Its rerun, 29518, finished. seen1, seen2, green1 and the bite run also finished.

**Checks:**
- ruff is clean, and all 4 mypy passes are clean.
- The 12 checks are green except tunables_register.
- The 17 scans: 5 failures, which are tunables_register (1) and task_inventory (4).
- Readers: all green except threat_model_statement and twin_record.

**Red checks, waiting on D2 / D:**
- tunables_register: the same 10 tags as before, with no Part N row. They now sit at src :51, :53, :55; link driver test :607; twin :145, :147, :151, :154; test_uart_comm_hazard.py:1397; bench :59.
- task_inventory (4 failures): there is still no C.9 row for `_two_initiations()` (:218, :219).
- threat_model_statement: A.11 does not yet name UartHazards.
- twin_record: red, as expected.

**Silent-failure scan** (classes 1-7, all modes, over my changes): the class-1 finding is fixed. The raise in an initiation is logged and counted, not swallowed. After a partial write, a lost next frame cannot pass silently, because the run already holds a None and fails. No new finding.

**Relay:** I wrote 3 lines under `## D`:
- the amendment to U3e's C.9 row (the tasks now run `_initiate()`);
- for J.7 and A.8: what a None verdict means;
- for Part N: the constant's new name.

**Decisions (agent, 2026-10-22):**
- None is the one "no verdict" value for both faults.
- The task top uses the shared E23 code, not a new catalog code.
- The TwoInitiations judges are exact.
- The twin and link driver plants swap `_HAZARD_FIELDS` to one field with two values, so the twin file's time stays flat.
- I used one commit for all three items. The rename's identical-bytes check was taken before the other edits.

**Logs:** S/u35/laneU/u3f/runs/ (summary.tsv, summary_pre.tsv, seen_*, green_*, bite_two_*, scans17.log, r_*.log, static.out), plus S/u35/laneU/u3f/st_*.log and S/u35/laneU/u3f/mpy/compare.txt.

**Owed:** D needs the C.9 row, the A.11 sentence and the Part N rows. Nothing is owed to the lead. U3e's three open items are closed.