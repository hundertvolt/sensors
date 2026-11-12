WIP 0d05ed9 (branch audit/u25-r, worktree S/wt-u25r). I stopped here as the brief says and am waiting for <API>.
- **Steps:** R1 is applied: the step-32 parts M.TWIN.044, .045, .047, .049 and .050; .051's parsing only; .046's `_shutdown_cleanup()`; the new modules `unixport/_offline_ntp_config.py` (step 94's writer) and `unixport/_ntp_responder.py` (step 116). Step 37 got one line: `digital_twin/mem_backup_state.json` is now ignored. Two later items also landed early in R1: A-22 (`_wire_log_clearer` calls `clear()`) and OF-114 (`largest_feed_gap_ms=`). Left for after R1, as plan §2's "Then" lists them: the shim refusal and `public_destinations_refused=` (OF-87, so that field is not on R1's line yet), step 131's `uart=` and `flash_stall_longest_ms=`, and every `--test-*` behaviour. Until then, `main()` raises `NotImplementedError` if any test flag is set. Everything else in the brief is untouched.
- **Deviations (agent, 2026-10-14):**
  - PLR0913 (max-args 8) does not allow 11 parameters, so the signature is `RunConfig(module, wiring_plan_path, listen=(host, port), device, state, injections, *, run, environment=RunEnvironment(config_dir, online_ntp, instrumentation))`. The flat attributes are kept.
  - `main()` opens `install()`, `prewarm_poll_set()`, then the shim. `test_exception_handler_contract.py` needs `install()` first, and it registers no poll object.
  - `uart_link_<ext>:silent` finds its bus from the generated `<key> = UARTLinkDriver(uartN, …)` line. The plan's `uart` pair names the buses only by role, and this avoids reading a private attribute.
  - The NTP responder binds 127.0.0.1:123 with SO_REUSEADDR, using the binary's CAP_NET_BIND_SERVICE as the captive DNS does for 53. It serves a host time bound at import, so the wall clock install cannot rebind it.
  - The shutdown line prints `r0` as 4 comma-joined `0x%08x` words.
  - In the NTP writer, `_NTP_STORE_NAME = "NTP"` is a named copy: src's `_NAME` is a private const and does not exist at run time (py/parse.c:854-860, v1.29.0). Its pin comes with step 94's test.
  - The shim keeps a local counter cap because L1 tests put only `unixport/` on their path.
  - `/usr/bin/time` is not installed; I timed with bash `time`.
- **Seen failing first** (the new test files run against `8e7dedc`, `after_each` lines stripped): launch 23 of 26 failed (`_apply_fault() takes 5 positional arguments but 3 were given`, `--fault op 'int_stuck_high' not recognized`, `unrecognized argument: '--wiring-plan'`, `--fault TIMES 'stack' is not an integer`). Runner 16 of 22 failed (`unrecognized argument: '--config-dir'`, `no attribute '_exit_code'`, `a config dir whose parent is missing must be refused, not swallowed`, `a cleared log must stay the link's own object`, `_collect_chips() takes 2 positional arguments but 1 were given`). The guards that passed at once: help, refusals, serve-until.
- **Verification:** run on a scratch copy with stand-ins for the MN1/N1/C1 contract (`S/u25/laneR/overlay_tools/`), never committed. Both files pass at -1, 32768 and settrace with zero MemoryError. `test_digital_twin_uart_link.py` passes 19/19 there. A probe confirmed all five responder modes.
- **Red until `<API>`:**
  - Both test files, and the 5 twin files that import the runner (bus_hazard_concurrency, real_website_integration, sensortask_integration, uart_link, wifi_modes), fail at import until MN1: `import _wall_clock`, `machine.reset_test_state`, a 3-field `StatePaths`, `peripheral()`, `configure_mem_backup_state_path`/`flush_mem_backup`/`SimulatedPowerLoss`.
  - They also need N1 (the WLAN singleton, the `raise_on` tuple) and C1 (`inject_fault(op, exc_type, *args, times, match)`, FRAM `silent`/`drop_next_wren`).
  - Twin mypy has 44 errors, all from that contract, for example `launch.py:337` (the `raise_on` tuple, N1) and `configure_wiring(_Plan)` against `dict[str, Any]` (MN's `_WiringPlan`). MN must type `Injections.faults` as `list[tuple[str, str, int, int | None, str]]`.
  - `test_twin_wiring_contract`: `digital_twin/launch.py:225: TwinWiringPlan['pins']` (waits on P1).
  - `test_tunables_register`: `run_generic_integration.py:167 l2.twin_feed_gap_fold_ms` and `_ntp_responder.py:22 twin.ntp_responder_poll_ms` have no Part N row (waits on X).
- **For the lead** (I edited none of these lists):
  - `test_decision_vocabulary` has 3 stale rows: launch "Bus devices only…", runner "deliberately reused…", the runner test's "Deliberately exactly one…".
  - `test_import_placement` has 4 stale `_PENDING` rows: (launch, main, random) and (runner: `_apply_fault`/errno, `_ensure_dir`/os, `main`/random).
  - `test_no_variant_literals`: drop launch.py from `_NOT_YET_CLEANED`.
  - These retire, since the files now have no explicit Any: `typecheck.ini` sections `[mypy-launch]`, `[mypy-run_generic_integration]`, `[mypy-test_digital_twin_launch]`, `[mypy-test_digital_twin_run_generic_integration]`, and the pyproject ANN401 row for the runner (checked with a copy without them).
  - The plan's `uart` block naming each instance (P's) would replace the source-line read.
- **Silent-failure scan:**
  - Class 4: the old `_ensure_dir` swallowed every OSError; fixed, new.
  - Class 2: the wire-log rebind (OF-74); fixed.
  - Class 2: the bounded `feed_times`; covered, since a dropped span is shorter than one fold (5 s), under the 6 s flag.
  - Class 4: the responder silently dropping non-client datagrams; now counted in `ignored`.
  - Still open in their own steps: the runner's `finally` swallowing KeyboardInterrupt (OF-155), and the shim refusing nothing (OF-87).
- **Facts for D:** tunables `l2.twin_feed_gap_fold_ms = 5000` (runner:167; basis: the 200-entry feed log, a dropped span is under one fold) and `twin.ntp_responder_poll_ms = 10` (responder:22, estimated; measurement owed). End states are as above: the reset line, exits 3/4/5, the RunConfig groups, responder knobs `mode`/`offset_s` and counters `requests`/`ignored`, and persistent defaults `digital_twin/{fram,scd30,mem_backup}_state.json` and `digital_twin/config/`.
- **After-times** (stand-in copy): launch 8.07 / 8.08 s against a base of 8.04 / 8.06 s; runner 1.35 / 1.46 s against 1.31 / 1.50 s. None is beyond 10 %.
- **Runs:** the one run over a minute was `test_digital_twin_uart_link.py` on the stand-in copy, rc=0, with both RUNS.md lines. Nothing of mine is running now; the `typings` symlink is removed.

---

U25 lane R hand-back. Commits: 0d05ed9 (R1 WIP), 0d8507a (API merge), d300267 (the rest). Nothing pushed; nothing of mine running.
Steps applied: 16, 22/29/32 (gc_unwedge, its test and segfault_stress_repro retired; nothing imports them), 32 entry order, shim, launcher, runner exits, 87 flags, 37, 57/61/94, 63/117, 77, 92/93, 116/121 (booted cases 2-5), OF-155. Partly: 78 (only the persistent-defaults doc; the rest is U27's text, the guard is 77's); 131 DUT side (no lap counter exists in src/, so `overruns=` reads asy_uart_driver.UART.rx_overruns, which counts laps and receive errors together).
Deviations:
- RunConfig groups its args (PLR0913). install() runs before prewarm. The uart_link instance read stays.
- The responder holds port 123 exclusively by a refused bind plus a retake.
- The stack fault form landed at U25. The shim keeps a local counter cap. A frozen `__file__` has no .frozen prefix. .gitignore keeps the coverage XML lines. S4 is not tested in-process.
- The wall clock goes only into src/, ext/ and generated modules.
- `_Booted` is now read-only, which clears tests/test_digital_twin_uart_link.py:287's mypy error.
- No new l1 responder tunable; silent attempts reuse l1.asy_ntp_client_no_reply_fetch_timeout_ms.
- The L1 staleness test forces the 1 h and 2 h resyncs instead of driving 1080 ticks.
- Booted cases run the real main() via load_device, with an SSID file written before boot. Case (5) flashes through one fresh monitor cycle, because FlashInterval is at least 60 s.
- tests/test_asy_ntp_client.py is not D.15-reordered: it was out of order at base, and sorting would scatter its 35 helpers across sections.
Seen failing first, one line each:
- Runner stand-in test asserting ntp_client.time is the wall clock: `AssertionError: (<WallClock>, <WallClock>)`, test :563 (runner/twin fakes also rebound).
- `_uart_links` AttributeError and the `_shutdown_line()` arity TypeError (both runner); "never installed the flash stall".
- Drain interrupt: "the interrupt was swallowed", test :661.
- L1 bites (failure as sync, age restart, backoff kept, RTC from host) and booted bites (restore without waiting, RTC unset, cettime gated on Synced) each failed their tests.
- Link-line guard bite (changed marker): `('dev', [])`.
Red checks, each waiting on someone else:
- test_twin_entry_point_order: 8 files: test_digital_twin_bus_hazard_concurrency (G), test_digital_twin_real_website_integration (SH), and the 6 test_digital_twin_webserver_concurrency_* through _webserver_concurrency_scenarios.py (SH).
- test_citations: CLAUDE.md and 5 SPECIFICATION.md cites of the deleted files (D). test_tunables_register: missing Part N rows (D).
- Twin mypy at the API tree: `_wall_clock`/`_flash_stall` import-not-found until W1. With MN's 91d8b98 code plus MN's uncommitted `_flash_stall.py`, the twin pass is clean in my files, and so are the main and host passes.
- G/SH runtime red at the API tree, not mine: configure_i2c_wiring gone, and configure_wiring refused once a bus exists. Affected: sensortask_integration 14/15, uart_link (import), bus_hazard 0/20, construction_arzi 2/4.
Scan: two findings, both boot/NTP mode. New: a codegen drift in the link lines would silently drop the counters (new guard added). Covered: product_modules() skipping a module with no `__file__` (the boot test checks asy_ntp_client got the clock).
Facts owed to D:
- New tags: l2.twin_test_stdin_poll_ms=50 (runner), twin.ntp_responder_take_rounds=20 and twin.ntp_responder_poll_ms=10 (responder), l2.twin_feed_gap_fold_ms=5000 (runner); l2.ntp_reply_wait_ms=1000, l2.ntp_run_bound_s=10.0, l2.ntp_sync_wait_timeout_s=20.0 (tests/test_digital_twin_ntp.py). l2.twin_ready_poll_ms loses its segfault_stress_repro.py site.
- API: runner product_modules() and _uart_links(); shutdown line gains `flash_stall_longest_ms=<n> uart=<key>:transfers=<n>,failures=<n>,overruns=<n>`; NtpResponder(port, host): mode, offset_s, holding, requests, ignored, serve(), close().
- Fidelity-table tests: tests/test_digital_twin_ntp.py's five booted cases, and test_asy_ntp_client.py's responder section.
For the lead: decision-vocab allow-list rows: delete `tests/test_asy_ntp_client.py	Below the OS ephemeral range…` (besides your three); _NOT_YET_CLEANED: .gitignore, run_generic_integration.py, segfault_stress_repro.py; pyproject.toml:381 exclude, typecheck.ini:9 comment, [mypy-unix_port_poll_prewarm] are freed.
After-times (none over 10%), base → now: runner test 1.31/1.50 → 1.00/1.15 s (shortened its serve waits); test_asy_ntp_client 22.5/24.3 → 23.5/25.2 s; launch 8.04/8.06 → 8.06/8.12 s; prewarm equal. New test_digital_twin_ntp: 33.8/35.0 s, 38.8 s settrace.
Zero MemoryError at gc -1, 32768 and settrace. Every run is in RUNS.md: batches A, B, C2, D, E, F, G exited; C was killed by pid because its overlay carried MN's machine.py, and its rerun is C2.
