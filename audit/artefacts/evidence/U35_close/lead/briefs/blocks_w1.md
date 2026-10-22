# U35 wave 1 blocks (lead, 2026-10-21)

Each block reads `S/u35/briefs/common_u35.md` first, then its own section here. About 60-80 tool calls each; at the
valve, stop at a seam, commit, and hand back what is left.

## C1 (lane C: the driven clock, the cancel sweep, the NTP frame server)
Files this block: tests/_fake_time.py, tests/test_driven_time.py (new), tests/_cancel_sweep.py (new),
tests/_ntp_frames.py, tests/test_shared_helpers.py. C's test_asy_* files are C2's and C3's.

**<CORE>: steps 32 and 97 (R-2, L-1).**
- Extend `DrivenTime` in place with opt-in virtual sleeps and `wait_for`. The default it gives today stays unchanged:
  test_shared_helpers.py's ticks-only cases (:269-300) stay green untouched.
- The sleeper queue is bounded, and no real sleep is left in the opt-in path.
- Self-test in tests/test_driven_time.py, bitten by planted off-by-ones in `advance` (a sleeper due at n+1 stays
  parked), `run_until`, `jump` and `wait_for_ms`.
- Commit, then relay `<CORE> <hash>` under `## C` at once: N, Y and C2 wait on it.

**<SWEEP>: step 36.**
- The cancel-sweep helper: cancel at each await point and check its invariants (no leaked socket, a balanced lock).
- Seen failing on a planted leak and on a planted unbalanced lock.
- Commit, and relay `<SWEEP> <hash>`.

**<NTPF>: step 57.** `serve_once` returns whether it served (`tests/_ntp_frames.py:36` returns None today). Seen
failing. Commit, and relay `<NTPF> <hash>`.

**Check-only (R-33).** Verify 30, 31, 38, 50, 51, 54, 63, 68, 69 (read :1593-1694), 70, 72, 115 and 117 on the base, one
line each.

**Runs.**
- At both stages, on the head: every importer of `DrivenTime` (9 files, P2.1, test_shared_helpers.py included) and of
  `_ntp_frames`.
- Paired base/head times only for the files you changed: test_driven_time.py is after-only.
- Readers: import_placement, microtest, radio_shape_corpus, plus any reader of your files that grep finds.

**Hand-back.** The three tokens' hashes, the shim's API as C2, N1 and Y4 will call it (signatures, one line each), and
C2's start state.

## D1 (lane D: <PARTN>, tests_hardware/README.md, the documents' independent steps)
Files: SPECIFICATION.md, BACKLOG.md, tests_hardware/README.md, which stay D's through D3. Wrap lines as the
surrounding text does.

**<PARTN> first: the Part N rows for the two tag changes known now.**
- Step 48 withdraws `l1.asy_notification_service_override_bound_ms`; step 76 adds `l1.bus_fault_isolation_bound_s = 5`
  (its basis from step 76's text).
- Use step 145's row form, commit alone, and relay `<PARTN> <hash>` under `## D`.
- tests_scripts/test_tunables_register.py then goes red on exactly those two named rows until N2's and Y2's tag
  changes merge (R-17). Prove that this is its only red.

**Then the steps with no dependency:**
- tests_hardware/README.md: steps 4 and 8, their "Left (U35)" parts in P1a's rows;
- SPECIFICATION.md: steps 9, 10, 116 (its part (7)), 145 (b), 161's clause, R-23's I.4(e)(6), and :3794's actor form
  (R-24);
- any other D step whose P1 row names no dependency.

**Check-only on the base (R-33):** 11, 13, 110, 135.

**Left for D2 and D3:** every other D step (34, 37, 111, 112, 126, 128, 142, 143, 144, 146, 147, 158, 159, 162, 163,
105's Basis cells, R-28's E.1, R-9's J.6, R-8's FRAM sentence). Your hand-back lists each with what it waits on (P2.3).

**Checks after each commit:** test_citations, test_decision_vocabulary, test_legacy_paths, test_tunables_register (the
two expected reds only). At your end, also test_timing_budget, test_memory_catalog, test_lock_order and
test_task_inventory. The 17 scans are D3's.

## P1 (lane P: CRC widths, the changelog, the UART comments, the math stand-in)
Files this block: src/asy_crc_checks.py, tests/test_asy_crc_checks.py, UART_C_PORT_CHANGELOG.md, src/asy_uart_comm.py,
tests/test_math_helpers.py. P's other files are P2's and P3's.

**The CRC steps.**
- Steps 23 then 85, tests first. `CRCBase(1, 0x1FF, ">B")` still reports `length()` 1 at the base. Write one case per
  width plus the pass-through case, each seen failing, then the width fix.
- Steps 20 and 21: dead-code removals. The existing tests stay green; relay one line under `## D` naming the change
  for E.5.1's register.
- Only invalid polynomials change behaviour, but `asy_crc_checks` is imported by six `src/` modules and by buildgen
  (P2.1). So:
  - every importer's test file runs at both stages on the head;
  - the buildgen readers run (buildgen_*, fram_chunk_crc_sites, import_graph).

**The changelog.** Step 22: row B87 covers steps 20 and 21, row B88 covers step 23. Both are Class B, in the table's
landing order (R-18).

**The UART comments.**
- Steps 24 to 27 plus the :712 comment, comments only (R-18). Step 25's reads "kept: it guards the copy into a
  caller's buffer".
- The wire is untouched: test_asy_uart_comm.py, test_uart_comm_hazard.py and test_digital_twin_uart_link.py run at
  both stages on the head (they are U's files, run, not edited).

**The math stand-in.** Step 119 is test-only, in tests/test_math_helpers.py. Its stand-in `ArithmeticError` cases are
seen failing against a scratch copy of src/math_helpers.py with the except narrowed; src/math_helpers.py stays
unedited.

**Check-only on the base (R-33):** 12 to 19, and 42.

**Proofs.**
- The mpy-cross byte compare for both `src/` files (LEAD NOTES 7): crc's bytes change, and uart_comm's change only
  where lines moved.
- Paired times for the changed test files.

## Y1 (lane Y: the typing residue's first modules, OF-32)
Files this block:
- pyproject.toml, digital_twin/typecheck.ini, host_typecheck.ini and tests_scripts/test_mypy_any_baseline.py, which
  stay Y's through Y5;
- tests/machine.py, digital_twin/machine.py, tests/test_digital_twin_machine.py, src/asy_system_service.py;
- tests/test_bus_hazard_generated.py, tests/test_digital_twin_bus_hazard_concurrency.py;
- tests_hardware/conftest.py, tests_hardware/device_scripts/serving_at_default_gc.py,
  tests_scripts/test_cross_browser_smoke_probe.py.

**R-15 for the eight modules this block holds.**
- The modules: `machine` (both passes), `asy_system_service`, `test_bus_hazard_generated`,
  `test_digital_twin_bus_hazard_concurrency`, `test_cross_browser_smoke_probe`, `conftest`, `serving_at_default_gc`.
- Each module leaves in one commit, with its baseline line, its ANN401 entry and its `_RESIDUAL` row. The sites are in
  `S/u34/handbacks/T1_final.md`.
- A module whose `Any` cannot go without a cast or an ignore stays listed with its sites (U34 R-2's form). Settle
  `Task[Any]` against `Task[object]` (src/asy_system_service.py:229-230) under the stubs.
- When the twin pass empties, digital_twin/typecheck.ini's :35-36 comment and the clause at :32 go too.
- `scripts/typecheck.sh` runs after every module commit; time it once.

**OF-32 (R-30).**
- Re-anchor `_epoch_us` (digital_twin/machine.py:900, :930), seen failing first in test_digital_twin_machine.py: a twin
  `ticks_us` driven past 2**29 misreads.
- The 2**30 build's confirmation comes later, on B1's <T30>, and is not yours.

**Runs.**
- Annotation-only files: LEAD NOTES 4 (head at both stages against the known figure).
- machine.py's fix: paired times for test_digital_twin_machine.py, plus the twin dev integration at both stages on the
  head.
- The mpy-cross compare for src/asy_system_service.py is expected byte-identical.
- Readers: pyproject's (P2.2's Y list) and every reader of the files you changed; ruff on your files.

**Hand-back.** Every module still listed, with its sites and why. The state Y2 starts from.

## T1 (lane T: the twin runner's shutdown line and test flags, the twin-process stop; launched after D1)
Files this block: digital_twin/run_generic_integration.py, scripts/_twin_process.py,
tests_scripts/test_twin_runner_test_flags.py. T's other files are T2's, T3's and T4's; step 152's three host-side cases
live in scripts/_digital_twin_scenarios.py and are T3's (P1d's row 152).

**<SHUT>: step 151.**
- The runner's `_shutdown_line()` gains `fram_writes=`, `fram_writes_by=` and `fram_writes_unattributed=`. Their sources
  are in P1d's row 151.
- `scripts/_twin_process.py`'s `ShutdownLine` parses them, with parser cases seen failing first.
- Commit, and relay `<SHUT> <hash>` under `## T`: T2's 125 (h), 160 and 166 read these fields.

**Step 152.**
- `--test-watchdog-fault {supervisor-raise,main-exit,block}`, off by default and unreachable from the product path, as
  the other `--test-*` flags are.
- Its `WDT_AT_FAULT <feed_count>` line, and its row in the flag table: test_twin_runner_test_flags.py is seen red until
  the flag exists.

**Step 154 and OF-215 stage 3 (R-27).**
- 154 is landed; confirm it on the base, one line.
- `shutdown()` (scripts/_twin_process.py:366-388) stops the twin through `--stop-file`, with SIGINT as the fallback.
  Seen failing first on the stop-file path; the fallback is kept and tested.

**Runs.**
- At both stages on the head: the twin integration file for dev
  (`tests/test_digital_twin_sensortask_integration.py`, dev), paired base/head times.
- The `tests_scripts` readers of your three files: P2.2's T list, the ones grep finds for these files (twin_process_spawn,
  twin_process_js_spawn, twin_runner_test_flags, twin_entry_point_order, run_digital_twin_ci_sh and the suite's tests
  that import `_twin_process`), base/head paired.
- The runner's hash covers only run_device_script.py and twin_board.py, so test_twin_record stays green; confirm it.

**Hand-back.** The `ShutdownLine` fields as T2 will read them, one line each, and T2's start state.
