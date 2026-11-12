Unit-tier logging audit at S/wt-u29 (442a564). Read-only: nothing written, nothing run.

**Key mechanism.** `_LOG_ERR = const(1)` (src/asy_print_log.py:54). Each logger starts at the level `build_system`/`main` get as `debug=` (codegen.py:34/494/527), which defaults to None (OFF). The catch: `SystemService.setup()` (asy_system_service.py:666-669) re-applies the stored DebugLevel to every logger, and a fresh cfg dir is written with the default 0 (:109). So for any test that runs the setup list, `debug=1` alone is undone at the second setup (pinned by tests/_sensortask_scenarios.py:921-927). The smallest complete change per boot has two parts:
- pass `debug=1` (main() takes it too);
- before the boot, plant `<cfg>/config_SYSTEM.cfg` = `{"DebugLevel": 1}`. That one key is the whole schema, so nothing is rewritten and no warning is logged.

Add both as an opt-in keyword on tests/_generated_module.py `boot_generated` (:84-94; `offline_ntp` is the precedent), not as its default. Other callers would otherwise change too: tests_scripts/test_fram_less_boot.py:38, test_device_script_fram_regions.py:44 and the heap-placement probe tests/_boot_contiguity_probe.py:168.

**1. Files that qualify** (construction site; level today; change; lane)

System builds:
- **test_sensortask.py[dev]** (none): `_boot` at tests/_sensortask_scenarios.py:188-196 → boot_generated, plus direct `main()` at :492, :769, :1553. Level: none passed (debug=2 only at :922). Change: opt-in `debug=1` + plant in `_boot`/`main` calls. The same path covers test_neopixel_wifi_integration.py:355 (C1_extra).
- **test_digital_twin_construction.py[dev]** (none): tests/_digital_twin_construction_scenarios.py:73 (boot_generated), :110 (`build_system`), :115 (`main`). No debug. Same change.
- **Files with their own `_boot`** (offline-NTP write, then `build_system` with no debug, then `run_setups`). Change: add `debug=1` and plant next to the existing config write.
  - test_digital_twin_sensortask_integration.py:163 (G)
  - test_digital_twin_timer_pool.py:105[dev] (none)
  - test_digital_twin_bus_hazard_concurrency.py:138 (none)
  - test_digital_twin_hot_replug.py:88 (none)
  - test_digital_twin_clock_jump.py:90 and `main` :117 (none)
  - test_digital_twin_wifi_modes.py:114 (none; writes no NTP config)
  - test_digital_twin_uart_link.py:137 (G; its UARTComm at :492 has no log either)
  - test_digital_twin_ntp.py `main` :107, beside its config writes at :95-96 (none)
  - test_digital_twin_fram.py:839 via boot_generated (none)
- **test_digital_twin_run_generic_integration.py:658-670** (V): `runner.main` → digital_twin/run_generic_integration.py:751 (V), which calls `module.main(...)` with no debug. Plant into `config_dir` before :670. Construction and `fram.setup` stay OFF unless the runner gets a debug flag, which also means updating its Protocol at :42.
- **Scenario harness** (V): `Context.boot` scripts/_digital_twin_scenarios.py:247-262 → `spawn` scripts/_twin_process.py:350-363 (none) → runner :751. Plant into `state/config` (mkdir first) before `spawn` at :261. Don't put it inside `spawn()`: `_digital_twin_ci_suite` shares it. Same construction-phase caveat as above.

Load tests:
- **UART hazard/sweep/large-train tests**: tests/_uart_comm_harness.py:84-91 `Pair` builds both UARTComm with no log (DEFAULT_LOG, print_log.py:370). Change: add an opt-in `debug` to `Pair`, `build_pair` (:211) and `hazard_pair` (_uart_comm_hazard_common.py:52-58), giving `log=LogConfig(None, 10, debug)`. Users (lane):
  - test_uart_comm_hazard.py, all via hazard_pair (G)
  - test_uart_comm_cancel_sweep.py:179 (none)
  - test_digital_twin_uart_comm_hazard.py:190 (none)
  - test_digital_twin_uart_field_sweep.py:83 (none)
  - test_asy_uart_comm.py flood/large-train tests at :1441, :2063, :2504 (via `_cap_pair` :2415), :2532 (none)
  - Flipping the default instead would turn logging on for all 87 `build_pair` tests in test_asy_uart_comm.py, plus test_asy_uart_driver.py.
- **test_asy_webserver_service.py** (C1_extra and N): the real logger is `WebserverService`'s own (`_FakeModule` loggers are fakes). `_make_service` :468 passes `LogConfig(None, history_length, None)`. Change: add a `debug` keyword there and pass 1 from the hammer builders at :2221, :3654, :3791, :3861, :3928, :3987 (f2b/h3/i2/i2b/i3/i4).
- **Borderline — test_bus_hazard_multi_device.py** (none): a concurrency test, but with small fixed allocations. Sites: ISL29125_Reader :610, `make_fram_manager` :888 (tests/_fram_builders.py:22, DEFAULT_LOG), ConfigManager :1094.

Excluded:
- digital_twin/launch.py: has no src/ code, so no loggers.
- test_bus_hazard_generated.py: builds only the `*_I2C` chip classes, which have no logger.
- test_asy_webserver_connections.py: connection tests, with an explicit "silent at DebugLevel 0" contract (:480, :971, :1019).
- Partial hand-wired chains: test_ntp_*_integration, test_fram_integration, notification_*.
- captive DNS "burst" :1103: a fixed, small malformed set.
- UDPSocket: logs through `console()`, which is never level-gated.

**2. Assertions raising the level would break**
- Planting level 1 in every `_sensortask_scenarios` build breaks:
  - :921-927 (expects the seed resolved to 0);
  - :936, :945, :1794, :1989: a PUT of DebugLevel 1 then answers "Unchanged", not "Valid" (asy_config_manager.py:224-228);
  - :865: the fresh-filesystem write list lacks SYSTEM;
  - :2209: the SYSTEM file after `resetconfig` + rebuild no longer equals the defaults;
  - :2558 and :2560: SYSTEM is never listed as unpersisted, and the PUT answers "Unchanged".
- Planting level 2 instead clears the four "Valid" checks but not :927, :865, :2209 or :2558. Those scenarios need an opt-out (most already pass an explicit `cfg_path` or `offline_ntp=False`).
- Scenario harness: :714 expects GET /system DebugLevel 0.
- Nothing else found: the twin, UART, webserver-hammer and bus-hazard files have no silent-output, printed-line-list or `.level` assertions. test_asy_uart_comm.py's captures (:752, :1303, :2004) set level 1 themselves, and the exact-list check at :2008 uses `_make_comm`, not `Pair`.
- Not determinable read-only: runtime/timeout effects of the extra output, and whether the harness's "STALL" not-in-log check (:498) or feed-gap verdicts shift.

**3. The gate reads the loggers' stream — confirmed.**
- Loggers `print()` to process stdout. The command runs as `2>&1 | sed -u | tee -a "$log_file"` (test.sh:490).
- `_flag_memory_errors` greps that file (test.sh:439-456, pattern at :444) and is called at :498 and :517. The threshold and coverage runners run in the same process.
- Scenario jobs: each twin's stdout and stderr go to its own `twin_NN.log` (_twin_process.py:361-362). `_append_twin_logs` (test.sh:526-533) appends those logs into the job log as the after-hook (:496), before the gate runs. The harness also checks each twin log itself (_digital_twin_scenarios.py:282/:346).
- One gap: `record_prints` with `echo` off (tests/_recording_print.py:24-28) swallows logger lines inside its `with` block, so they never reach the gate.

**4. Lanes** are given in brackets above.
- G: twin_sensortask_integration, twin_uart_link, uart_comm_hazard.
- V: run_generic_integration test and runner, _digital_twin_scenarios.
- C1_extra: neopixel_wifi_integration, webserver_service (also in N).
- Every other listed file, including the helpers (_sensortask_scenarios, _digital_twin_construction_scenarios, _generated_module, _uart_comm_harness, _uart_comm_hazard_common, _fram_builders, _twin_process), is in no lane.
