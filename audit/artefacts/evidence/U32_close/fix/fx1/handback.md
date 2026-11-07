FX1 hand-back. Commit de1a8ad on audit/u32-fx1 (worktree S/wt-u32fx1, from 889cb5e). Not pushed. Nothing uncommitted, nothing running.

Steps
- RA-1 code part: applied. Backup wired `SgpBackup({fram_var}, ntp.ntp_issynced)` again, same line as 72b1281. `_clock_was_set()` emission and comment removed from codegen.py; `_EMITTED_FUNCTIONS` no longer lists it. Both comments (asy_sgp40_driver.py:39-40, asy_base_classes.py:42) byte-identical to 72b1281 again. Every other C2 change in codegen.py kept (task names, LastTaskEnd, unpack). Legacy read first: sensortask-wozi.py:86 wires `conn.ntp_issynced`; async_connect.py clears it at the stale bound (:450-454), on a force sync (:130) and on missing config (:434). Current asy_ntp_client.py `ntp_force_sync()` also clears Synced.
- RA-1 test: renamed to `test_real_device_gates_the_voc_backup_timestamp_on_the_ntp_sync`, per device: every backup matches `SgpBackup\(\w+, ntp\.ntp_issynced\)`, and no `_clock_was_set` defined.
- RA-5: applied. definitions.py LastTaskEnd description uses the lead's exact text; exact-row pin in test_buildgen_definitions.py matches. Old text not in js/, tests_js/, mockdata/. SPECIFICATION.md is FX6's.
- Effect per mode: STA with NTP reachable unchanged. STA after the stale bound, or after a force sync until the next sync: backups no longer timestamped (legacy's behaviour; BASE kept stamping). AP/Silent/Off: no sync this boot gives no stamp under either gate; a unit that synced then left STA stops stamping at the stale bound. USB: none.

Seen failing first on BASE: new gate pin, all 6 devices `AssertionError: ['SgpBackup(fram, _clock_was_set)']`; `test_generated_module_defines_only_the_functions_l2_lists` (6 devices + novel_combo) "Left contains one more item: '_clock_was_set'"; LastTaskEnd row pin description mismatch. Scratch bite (S/u32/laneFX1/bite/): gate on ntp.ntp_issynced with `_clock_was_set` planted, second assert fails naming it.

Generated wozi diff: removed `async def _clock_was_set() -> bool:` / `return utc_now() is not None`; gate `SgpBackup(fram, _clock_was_set)` -> `SgpBackup(fram, ntp.ntp_issynced)`. Every device module has 3 `ntp.ntp_issynced` sites after.

Runs (all rc 0, zero memory markers)
- test_buildgen_generate.py 380 passed, 9.35 -> 6.17 s. test_buildgen_definitions.py 401 passed, 4.13 -> 4.26 s.
- test_sensortask.py 91/91 per device, -1 / 32768: arzi 29.4/33.2, dev 46.4/54.9, grkizi 29.4/33.6, klkizi 29.4/33.2, schlafzi 29.1/33.7, wozi 33.4/37.4; all within 10 % of base.
- Readers of the gate/timestamp, both stages, passed: test_asy_sgp40_driver 164, test_asy_webserver_service 222, test_ntp_fram_system_integration 12, test_digital_twin_ntp 16, test_digital_twin_clock_jump 6.
- One pytest process (4m49s): 17 scans, 12 pre-commit checks, 63 grep readers: 3487 passed, 6 skipped (opt-in real ARM build per device).
- ruff clean; host, main, and main with `src tests tests_hardware/device_scripts` passes clean. RUNS.md start/done lines.
Red checks: none. test_twin_record not run (expected red, lead re-records).
Silent-failure scan: nothing new; the gate's class 7 / time-mode effect is legacy behaviour, open as the owner question.
Facts owed: to FX6, SPECIFICATION.md still names `_clock_was_set` at :747, :898, :10157, and A.8/H.5.1 need the new LastTaskEnd text. Allow-list rows: none. Decisions: none. Logs in S/u32/laneFX1/.
