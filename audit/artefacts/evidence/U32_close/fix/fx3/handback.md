FX3 hand-back. Commit 674bd54 on audit/u32-fx3 (worktree S/wt-u32fx3, based on 889cb5e). Not pushed. Nothing uncommitted.

Rulings:
- RB-2 applied (tests/_sensortask_scenarios.py, the kill scenario). The ruling asked for `assert not sup.done()`, but alone it proves nothing: `supervise_tasks()` never ends on its own (it waits on `_never`), so it stays not-done even when the real loop, `sysfunct._supervisor_task`, has ended. The scenario now waits one more supervisor pass after the restart, then asserts: sup running, the loop task running, and the killed slot holds a new task that is not done. (agent, 2026-10-21)
- RB-3 applied (tests/test_asy_system_service.py). Both stand-ins raise RuntimeError("injected close fault") / RuntimeError("injected delete fault"); each class comment says the stand-in is for any unexpected fault and what the real object does instead.
- RB-5 applied. New helper tests/_task_names.py: `task_name(owner, starter)`, `task_names_of(*owners)`. Not tests/_generated_module.py: it calls require_fresh() on import, and the neopixel and NTP/FRAM unit tests have no generated module. (agent, 2026-10-21) Used at hot_replug:144, timer_pool:206/238, neopixel:884, fram:847 and the four NTP/FRAM sites (now the wrapped real starter's name, e.g. "NTP.start_asy_sync"); the scenario's name pin too. Synthetic "T"/"t0"/"mod.a" stay.
- RD-7 applied. Probe and device script collect the trigger and timer lists after start_tasks() returns; comments say so; the probe's LISTS line and the script's `fact("lists")` emitted after the starter loop. SPEC :8938's "run main()'s order" stays true.
- RD-8 applied. _bench_device.pyi follows D.15 in full: private `_collect_*` first, alphabetical, then `build_system` and `main`. (agent, 2026-10-21)

Bites (scratch copies of src/asy_system_service.py first on MICROPYPATH, wozi at -1; nothing planted committed):
- RB-2, supervisor returns after the pass that recorded the end: BASE passes; mine fails `[(False, True, True)]`.
- RB-2, ended task never restarted: BASE passes 91/91; mine fails `[(True, False, False)]`.
- RB-3, both task tops narrowed to `except OSError`: BASE passes; mine fails both tests.

Times BASE vs fix, both stages, all rc 0, zero memory markers: all 36 rows within +-4 %. E.g. test_sensortask wozi 33.92->32.73 / 37.77->36.57; system_service 25.12->24.92; hot_replug 70.87->70.75; timer_pool dev 43.39->43.26; ntp_fram 7.67->7.92 at 32768; boot_contiguity 12.24->12.71. Tables S/u32/review/fx3/{before,after}.tsv.

Checks: ruff clean; all three mypy passes clean (main, `src tests tests_hardware/device_scripts`, twin). One pytest process of 40 tests_scripts files (17 scans, 12 pre-commit checks, every reader): 2106 passed, 1 failed: test_twin_record (heap_layout script hashes plus other lanes' entries), expected. test_digital_twin_boot_contiguity green with and without GC_THRESHOLD=32768 (the probe sets no threshold; the binary ignores the variable: the same run).

Scan and effects: silent-failure scan of the files, all classes, boot mode: no findings. No firmware effect in any mode (STA, AP, Silent, Off, USB); only the bench reading point moves.
For the lead: allow-list rows none. For the docs (RC-4): the bench-round item can say heap_layout collects its lists as main() does.
Runs, all exited: times.sh before pid 6479 rc 0; after pid 16486 rc 0; five bite runs as expected; tests_scripts process rc 1 (twin_record only). Nothing running; scratch base worktree removed.
