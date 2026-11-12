T3e hand-back (lane T, audit/u35-t, S/wt-u35t). One commit, 7f5501d, on 5ca6b30. Nothing is uncommitted and none of my runs are still going. I used about 62 tool calls. No src/ change, so no rebuild.

**Steps by verdict**
- **(18) gap, test 10: applied.** A new `_ListenerSleeps` (asyncio as asy_udp_socket and asy_captive_dns see it) counts the listener task's sleeps of at least `_POLL_IDLE_MS` during the burst. The bound is at most 1. `_dns_burst` now returns (answered, rounds, sleeps).
- **149, booted boot order (R-24): applied.** The twin log had no boot-phase lines. Markers located: the runner's new `_print_boot_phases()` wraps asy_system_service's `_write_region` and prints `... [<dev>] boot phase: <BOOT_*>` on each region-1 write. The write itself is unchanged, and the wrapper is installed once per process. `_boot_order_failures()` in test_digital_twin_generated_boot.py checks every booted device and fixture against `expected_facts()["boot_sequence"]["phases"]`: the BOOT_* marks in order, with BOOT_CONSTRUCTION first. A pure-function case pins the message.
- **125 (f)-(i) and folds (1)-(3): not started (budget).** Their blockers have landed: `--test-watchdog-fault` plus `WDT_AT_FAULT` (runner :452, :868), and `fram_writes_by=`/`fram_writes_unattributed=` (runner :381-400). The scenario registry has none of the nine yet.

**Seen failing first and bites**
- 149 booted wozi on the old runner: `the twin logged the boot phases [], not main()'s order ['BOOT_CONSTRUCTION', 'BOOT_SETUP', 'BOOT_TASKS', 'BOOT_TIMERS', 'BOOT_NTP', 'BOOT_DONE']`.
- 149 bite (generated main() with timers before tasks, a planted test copy in its own tree): fails with `...['BOOT_CONSTRUCTION', 'BOOT_SETUP', 'BOOT_TIMERS', 'BOOT_TASKS', ...]`.
- (18) bite p18a (the DNS loop sleeps 100 ms before each read): `the listener slept 6 idle polls during the burst`. The 5ca6b30 test passes on the same plant, which is the gap.
- (18) bite p18b (`_poll` sleeps before it polls): `slept 11 idle polls`. Control (arzi): passes.

**Times** (s, base = 5ca6b30's files / head; all rc=0, mem=0)
- Integration file, arzi: -1 60.03/60.03; 32768 60.64/60.79.
- Integration file, dev: -1 22.54/22.64; 32768 22.92/23.12.
- test_digital_twin_run_generic_integration, -1: 1.36/1.37.
- generated_boot: 56.69/56.04 (23 → 24 tests).
- No file is more than 10 % slower.

**Red, not mine:** `tests_scripts/test_twin_record.py::test_every_entrys_hashes_are_the_current_files`: `changed since their twin run was recorded ... api_sha256`. The list is identical on the 5ca6b30 tree, so it predates this block. It waits on the re-record (LEAD NOTES 8).

**Green:**
- ruff on my 3 files.
- twin and host mypy passes, cold: 0 issues.
- 12 checks: 797 passed. The one warning is the datasheets submodule not being initialised.
- Readers: stripped_image_boots, twin_runner_test_flags, ci_suite_errcount/soak, scenarios, run_unix_port_integration_sh, twin_process_js_spawn, entry_point_order, never_needs_tests_on_its_path, exception_handler_contract, no_variant_literals, buildgen_generate, device_tomls.

**Decisions (agent, 2026-10-22)**
- The sleep count is filtered by the task seen in ready(POLLIN).
- The boot-phase line prints on every twin run (a diagnostic like the reset line), not behind a --test-* flag.
- The test names BOOT_CONSTRUCTION as begin_boot()'s mark.
- 125 is deferred to the next block rather than left part-done.

**Effect per mode:** test and twin only. (18): AP mode. 149: every device's generated boot (AP, no SSID). The new line appears in twin logs in every mode. STA, Silent, Off and USB have no behaviour change.

**Owed to T4:** digital_twin/README.md has no text on the runner's `boot phase:` line.

**Scan (my files, all classes):** nothing new. A missing system module or a missing phase list fails visibly as "logged []".

**Allow-lists:** no row orphaned. Relay: none.

**Runs** (all in RUNS.md):
- r1: sf149 rc=1 (the expected seen-failing), ctl18 0, p18a_new 1, p18a_old 0, p18b_new 1.
- r2: h149 0, p149 1.
- r3: everything 0 except twin_record (rc=1, the red above).
- twin_record on the base tree: rc=1.

**T4 / next block starts** from 7f5501d, clean. Open items:
- 125 (f)-(i) and folds (1)-(3), each seen failing first.
- The README text above.

**Logs:** S/u35/laneT/t3e/ (runs.sum, logs/, r3/results.tsv and its logs, the plants p18a, p18b and p149/tests_scripts, the edit scripts, commit1.txt).