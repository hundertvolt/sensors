# Lines owed to U30's close record (lead)

- CI on U29's squash `5ba138c`: run 39394914980 (pull_request), 46/46 green. The push run 39394906268 was cancelled by
  the workflow's concurrency group (`cancel-in-progress` on the same head), as at U28. Minutes (budget): unit-tests 7.7
  (175), unit-tests-gc-threshold 8.6 (175), unit-tests-coverage 13.0 (95), the slowest digital-twin-e2e leg 9.6 (dev,
  32768, suite; 20), the slowest firmware build 2.0 (20), web-unit-tests 3.2 (20), the slowest web-put-matrix shard 5.6
  (15), web-coverage 3.7 (20), web-cross-browser-smoke 5.1 (15). The first run under the 20-minute web budgets.

## For the records (lead, 2026-10-20)
- Open finding (new, route: hardware session 1): the board (RPI_PICO_W) keeps MicroPython's 64-entry GC mark stack
  (py/mpconfig.h:255-256; rp2's 1024 is its PSRAM branch only, ports/rp2/mpconfigport.h:89-99). Any object with about 55
  or more unmarked heap children (a module's globals, a registry list) overflows it, and the collection then re-scans the
  whole heap area (py/gc.c:620-639). On the rig that cost is 0.5 ms per collection at 16 MB; on the board's ~200 KB heap it is
  unmeasured. Measure in session 1: gc.collect() duration on the dev build at both stages, with and without the overflow
  (a probe script with 30 vs 200 module globals). No firmware change before a measurement (agent, 2026-10-20).
- Rig change (lane R): all three Unix builds get a larger mark stack; time only, marked set and heap maps identical
  (u30/lead/gcstack/layout.py). Evidence: u30/lead/gcstack/pairs2/pairs.tsv, w*.py cliff table.
- pairs1 void: my error, both binaries run in one worktree (tests/_tmp collided); killed by pid, redone as pairs2.
- pairs2 caveat: wt-u30n's build/generated_src stamp (09:37) predates N's last edits, so generated-module files
  (test_neopixel_wifi_integration.py) refuse to run there; re-pair that file on fresh trees.
- Lane N's remedy "build the rig with rp2's stack size" rested on a misread (the PSRAM branch); the lead's correction is
  the source lines above.
- Lane N's two "handlers without report_if_fatal" (asy_fram_driver.py:156, asy_spi_driver.py:145/:187) clean up and
  re-raise: none needed.
- _SHUTDOWN_CMDS is dead in src/ after N (read only by tests/test_shared_helpers.py): lead edit after C merges.
- C final afef401 merged as e2e2ef4 (clean, 18 files). Lead commit a4f6517: bench reset-reason test + device script expect
  ResetReason 20 for a stack exhaustion (not run: hardware); feed-site bite anchors; _SHUTDOWN_CMDS removed, helper tests
  read _SYSTEM_CMDS. Checks: 545 tests_scripts targeted passed (fatal-report sites 0 findings on W1), shared_helpers 32/32
  both stages, ruff clean, mypy main + host clean, collect-only 196/226.
- Carry to U34 (LIC): UDPSocket.write_and_recvfrom() has no src/ caller since C's resolver change; its removal changes
  THIRD_PARTY_LICENSES.md:196's provenance comparison, so it goes with that note (agent, 2026-10-20).
- REGISTER residual (from C, class 4, mempause landing while a ResetErrors write waits on a lock): reset() checks the pause
  before clearing; a pause set while the clear's write waits is still refused after RAM was cleared. Fix proposed (restore
  the pre-clear count and ring on a refused write) needs a snapshot allocation. Route: decide at close (lead).
- C's squash text must not repeat C1's "a boot-time arm failure now leaves one E17" (wrong for the generated boot order).
- C's dns_client +11 % (0.79 -> 0.87 s at -1): each resolver exchange waits the product's 20 ms poll; check at W1 with
  the new rig whether it still exceeds; then decide (efficiency, never a cut).
- W1 sync (lead): G f221308 merged f0f51da; toolchain installed via setup_toolchain.py test (rc 0, 1m29s; bss
  10704/10704/49648; readbacks passed; record inputs updated; cliff script 55 globals -> 2 us). Part N 9a706d9 (R row,
  threshold Sites -3, five sensortask run-bound rows withdrawn, import-placement -6). Hazard files on W1:
  multi_device 3.22/3.64, generated 63.53/63.83, uart_comm_hazard 105.33/108.24, twin bus hazard 1 FAIL at both stages
  -> root cause: S2's _exchange() sleep_ms + the file's own _FastSleep patching asyncio.sleep only; fixed 34d8a1c with the
  shared FastAsyncSleep (22/22, 150.48/152.04 s, 0 markers). Twin record re-recorded a104068 (121, every result/reason/
  stage unchanged, 1030 s).
- For U31 L0 (PERF, fast sleeps): tests patching asyncio.sleep without sleep_ms: test_asy_bmp3xx_driver.py,
  test_asy_wifi_service.py, test_neopixel_wifi_integration.py (pass today; check each against the waits its code uses).
- test_asy_dns_client.py +10-17 % at both stages (0.87-0.95 s vs 0.79/0.81) on the new rig: the product's 20 ms
  udp.poll_wait_ms per new resolver exchange over the real loopback socket the file exists to exercise; C cut 6 -> 5
  exchanges. Accepted: a further cut removes a cause path or fakes the socket (agent, 2026-10-20).
- W1 tier on a104068 (lead): 3 reds, all W1 edits the lanes' targeted checks missed, fixed in f594679:
  test_config_schemas (8 errors: C's report_if_fatal import, the CPython stub of asy_print_log lacked the name);
  test_const_mirrors (S1/S2's `str(src_const(...))` is no bare reader call; RuntimeError takes the object, as
  test_asy_system_service.py:3243 does); test_suppression_form (two `method-assign, assignment` lists out of order).
  scd30 22.18/29.02 s, sgp40 8.12/8.88 s, 0 markers. W2 lanes now run the 16 repo-wide source scans before their final
  (common_u30.md; ~70 s under load).
- S2's scan line "a contract-type store failure on SCD30 still logs every cycle" (S2_final.md): routed by the lead as
  C's item "the config store's half of the per-episode logging fix"; closed in 518afc3: unknown key and wrong-typed
  value (`_ERR_CONTRACT`) persist and print once per run, a good read or a cleared history ends it
  (`src/asy_config_manager.py` `_read_run_starts()`; tests/test_asy_config_manager.py:2344, :2363). SCD30's
  `_capture_frc_config()` keeps reading each cycle on a valid store and the store stays quiet after the first entry.
- Records prep (read-only agent, f594679; u30/close/records_prep.md, 111 lines): 56 rows: closed-W1 26, partly-W1 11,
  W2 6, not-U30 11, lead-only 2, GAP 0. Draft last cells for the 21 closed OF rows + X01 are in that file.
  Close to-dos from it:
  - Re-point (not-U30, row names U30 in passing): OF-60 (FRAM probe option; next holder of asy_fram_manager.py),
    OF-70 (UART cause string -> U32 per REGISTER:699), OF-181 (_sgp40_chip.py walk; find next holder in the order),
    OF-184 (system_service -> U31, as R-24 for OF-36). OF-122 stays the owner's pending U21 question, default (a).
  - Move partly rows: OF-36 -> U31 (R-24); OF-69 -> C (H44) + U36 (R-25); OF-83 stays C (R-26, USB repeat rate);
    OF-90 rest -> H44 (R-18; note the rig mark-stack share); OF-149/OF-188 -> U35 (R-27, not reproduced in 6 settrace
    runs, laneG/batch2b.log); OF-167 -> U35 (R-23); OF-123/145/146 after X and V.
  - Row texts whose lines moved: OF-145 print_log :219-233 -> :226-240 (store reset :323-329); OF-146 _reboot :320;
    OF-167 :192 -> :197; OF-184 :662-665 -> :688. OF-50's row states the boot order backwards (main() starts tasks first).
  - Relay correction: tests_hardware/README.md:938 was wrongly relayed as stack text; only :817 is stale (X told 12:58).
  - Verified by the lead: OF-152's maxima against datasheets/sgp40 (Table 8 self test max 320 ms; Table 3 tSR max 0.6 ms).
  - Handler pairing re-checked by the agent: only re-raising handlers (fram_driver:156, spi_driver:145/:187,
    isl29125_driver:1371) and the exempt report_unretrieved lack report_if_fatal.
- Re-point targets settled (agent, 2026-10-20; next later unit holding the file in audit/order/work_order.json, U28's
  fallback rule at REGISTER:699): OF-60 -> U35 (asy_fram_manager.py: M.SRC_CORE.087/.090); OF-184 -> U31
  (asy_system_service.py: M.HW_DEV.095, M.SCR.015); OF-70 -> U32 (first unit holding asy_uart_comm.py and its test, as
  OF-210); OF-181 -> C (its R1 run) then U35 (no later unit holds digital_twin/_sgp40_chip.py; U35 as OF-207/OF-212).
- X final (u30/handbacks/X_final.md): c1e3e5f fast-forwarded onto W1; lead 2e6c5bd (Part N mem.max_await_depth in the L0
  table; allow-list rows 28 and 71 removed). 18 scans 853 passed, ruff, mypy main + host, collect-only 196/226 green.
  After V and L merge: (1) launch X2 (fresh agent, S/u30/briefs/brief_laneX2.md, <HEAD> = the head with V and L merged; replaces resuming X) for step 136 (Run 12's stack cell, code 20) and fold (6)'s option-1 sentence on the
  landed state; (2) re-record the twin record (only c_stack_budget.py stale now; plus any V/L device-script change).
  X's class-4 find: c_stack_budget.py discarded Microdot's 500 for a raising handler; fixed c1e3e5f (asserts the 200).
- REGISTER row (U30): owner, 2026-10-20: "Once you are done with U35, wait for my decision in which order and at what time to start the parallel hardware session and the doc works." Question: none asked; the owner's direction after the budget report. Supersedes REGISTER:691's "runs beside U36/U37" timing (owner, 2026-10-19); WORK_ORDER.md section 5 item 1 edited in wt-u30api.
- (17:58) Records draft merged as d343f61 (rec 4d9f36a: 21 OF closed, 11 partly, 4 re-pointed, OF-122 unchanged, OF-219 new; 6 REGISTER rows after U29's CI row). PENDING-LEAD at the close:
  - REGISTER:56 U30 unit row; gate, CI and W1 sync/tier lines; the U29-squash CI run REGISTER:721 promises (39394914980, 46/46).
  - Twin record re-record (after M2).
  - X2: step 136 + fold (6) (REGISTER:770, :787 are SF-A12/SF-M3-06).
  - OF-215: target still U30; name stage 3's holder (the next unit holding the runner, else C).
  - Rows for lanes M (9 silent handlers fixed, B81/B82), M2 (init/deinit, sentinel), V2 (spawn() refusal), V3 (three launchers), L's two sites (now M's), C's class-5 early first read; V's Run 12 +54-64 % and V2's errcount +24 % into the time-growth row; lanes' own (agent) decisions as the unit row's pointer.
  - The "Residual kept open" row's route.
  - The rig row's "re-pair of test_neopixel_wifi_integration.py owed": check whether the paired timing was done (close_notes :20), correct the row either way.
- (19:20) U34 carry addition: UDPSocket.write_and_recvfrom()'s tries guard (src/asy_udp_socket.py:186-189) catches TypeError only, not OverflowError (F1c); moot while it has no src/ caller, goes with its removal.
(19:36) Gate1 on fef34d0 complete (rc of gate script 0): lint, typecheck x2, collect-only 196/226, 6 twins, npm x7 all rc 0. gc-1, gc32768 and coverage(settrace) each rc 1 on the same 4 tests_scripts reds only (test_port_lock x2, test_run_digital_twin_ci_sh x1, test_twin_never_needs_tests_on_its_path x1), all fixed in d860130; MicroPython tests 0 failed at every stage (coverage leg: 5198 passed, tests_scripts 6518 passed/4 failed), 0 memory markers in coverage.log. Gate2 on the final head carries the fix.
