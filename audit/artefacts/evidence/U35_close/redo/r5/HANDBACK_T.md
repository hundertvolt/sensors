T hand-back, written by the agent (Tue Nov 10 11:51 UTC 2026)
Commit 777f7640 on audit/t (S/wt-t, from 81e2ebcd), not pushed: 157 files, +2,196/-6,512; src/, ext/, devices/ untouched.
1. REMOVE: the 55 self-bites (watchdog_feed_sites 18, ticks_wrap_scan 16, setter_contract 7, lock_order 7, task_tops 5, js_api_mirrors
   1, counter_steps 1) and their src_copy/tree_copy fixtures; each check's real-tree run stays the catcher. 8 SPEC-table checks gone
   (timing_budget, memory_catalog, task_inventory, readiness_gates, threat_model_statement, src_sleep_forms, suppression_form,
   legacy_paths: 39 tests, -1,258): the code each table described keeps its own tests, retired-tree citations test_citations'
   _RETIRED_TOPS; C.8's levels now sit in test_lock_order, C.9's task data in test_task_tops.
2. SIMPLIFY: 4 per-handler C-stack tests (-147) -> test_asy_print_log's every-entry-point record test. Feed sites 377 -> 45 lines,
   one rule (feed()/feed_watchdog() only in SystemService, none in generated modules or boot entries). Counter steps: cap rule and
   twin-cap pin stay, exempt list goes (-114). Lock order: order check stays (session 2 > bus 1), C.8 table match goes (-167).
3. GIVEUP_3: run()'s limit and run_timed gone (890 call-site limits, 65 wait_for wraps, their constants); a hang is the per-file
   timeout's. Reap: _REAP_ROUNDS = 2 (a cancelled task ends at its next await, the reaper takes it next round; 2 suffice at both
   stages); once the reaper is done it only yields, so a flash task a sync helper started no longer holds a reap 5 s
   (test_asy_wifi_service 24.6 -> 19.7 s). UART harness: an undeclared listener is awaited to its end (5 s limit and its self-test
   gone); a declared stall keeps its drain, now printed. Twin harness: NTP watch, request wait (= _DEFAULT_OUTER_CAP_S), reset
   deadline read from src/; Run 3's 627 ms ceiling had no source: gone, with the FRAM chip's silent-write counters.
4. SIMPLER_3 (1) 13 per-device scenarios (5 AP-mode, 8 LED; the AP redirect one stays the wiring's catcher); setup and main-call
   order merged into _scenario_boot_sequence. (2) the twin report is PrintLog's at level 1 (-24; 5 re-pinned tests -109). (4) 7
   single cases (udp 4, captive_dns 2, uart_driver 1). (6) _tmp_cfg_dir in 12 files, driven_modules() 8, record_prints(),
   src_const(); rx_stall_ms gone. SIMPLER_4 #5 distinct_devices() at 9 twin boots; #11 helpers in scripts/_twin_process.py.
5. fakes/ holds rp2.py, neopixel.py, _twin_common.py, _strict_json.py once, both layouts read it; the twin imports nothing from tests/.
6. launch.py (-557) and its test (-377) gone; its flags in run_generic_integration.py, 17 tests moved. 7. uart_comm_hazard's
   _get_frame plain (an await on a returned bytes loses the task for good, a MicroPython finding): fails at once. _load.py:477 fixed.
8. R0, all KEPT: bench torn-write tolerance (agent, 2026-09-13: three resets in FRAM writes left those entries on the bench); import
   placement (agent, 2026-10-06; SPEC F.1, owner ok 2026-10-05 in OR141.a (2)); twin state-file notice (agent, 2026-10-14: the
   persisted state the owner asked for, 2026-08-13, never goes without a word). 9. definitions.py main()/__main__ (-49) and tests
   (-64) gone; the error contract's 17 rows run through the batch CLI. 10. Credits: 54 suffixes gone in 22 files; plain forms applied.
Gate (tc-c, heavy.lock as t): -1 unit 5252 PASS, tests_scripts 3 red, all P9's (citations, level_containment, tunables_register;
a 4th, test_test_sh's hung-file probe, fixed, re-run green); 32768 PASS; twin suite 327 + harness 13 PASS at both. Coverage build
114 runs, 0 failed, 0 MemoryError; npm lint/typecheck, test:unit 1192; lint_direct, three mypy passes clean. Wall -1: 678 -> 677 s.
Tests: unit 5347 -> 5252, tests_scripts 6808 -> 6555. Sizes identical (module_sizes.sh, to uart_driver's viper); imageFreeBytes 71,044.
For P9: SPEC:2888/9838 rp2, 5260/6536/7563 _strict_json, 7616/7615 _twin_common: now fakes/; 2889/10293/11968, README:655/684/1076/
1078 launch.py gone; 5825 E.6.6 'launch' row; 5828/7639/9222 the PC report is PrintLog's at level 1; 5135-5141 run() unbounded, reap
in rounds; 5265 Run 3 bound gone; 11949 web.outer_cap_s loses the ci_suite site; 4014 C.8, 4277 C.9 tables read by no check; 6721-6769,
8802/9034, 1431/4515/4528, 1444, 4799/4801/6761, 4829/7092: checks gone; 5271/7840 feed sites one rule; CLAUDE.md:187/:694 removed
checks; nine scopes with fakes/ (CLAUDE.md:497/613/621, README:324, SPEC 2951/4946/5693/6222).
Not done: the declared-stall drain (LISTENER_DRAIN_S/_STALL_DRAIN_S: a second exchange relies on it); caught listener wait_for's
(uart_comm_hazard, ntp); other twin numbers (_ESCALATION_WAIT_S); _cycle/_crc8 copies; device-script _REPORT; dead _record_reads.
Slips: 2 grep -o outputs (pyproject:337 earlier) printed identifiers with a filtered word, no secret; port-binding wifi_service ran 4x,
udp_socket 1x under another unit's lock; single files ran via my one.sh, not run.sh; an ls overflow landed in /root/.claude, unopened.
