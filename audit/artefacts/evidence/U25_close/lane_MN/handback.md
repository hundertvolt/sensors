WIP 72ece42 (branch audit/u25-mn, worktree S/wt-u25mn, based on 8e7dedc). Stopped here as the brief says; I resume on <API>.
Steps, by verdict:
- Applied: 88 (_twin_common: COUNTER_CAP, saturating_add, LOG_MAXLEN, BoundedLog moved from machine.py with a saturating `dropped`, fill_buffer defined, StatePaths(fram, scd30, mem_backup)); 90 (both FRAM RDIDs, unknown size raises); 32/.030 Timer in full (rp2 signature, 16-alarm pool, set_alarm_pool_free, _pool=False, generation number, soft/hard callback rules); .034 in full; A-6 (tests_hardware/isl29125_conformance.py:32 now calls configure_wiring(json.load(dev plan)); `pytest --collect-only tests_hardware` clean: 120/145 collected).
- Partly applied: .022/.035 (the three registries, peripheral(), reset_peripherals() closing DMA, reset_test_state(), _require_unconstructed in all 5 hooks, configure_wiring no longer clears, configure_i2c_wiring and the wozi default gone); .032 (configure_mem_backup_state_path/flush_mem_backup); .026 (only lose_power_after and wire_time); .024 (only unplug/plug); .023 (chip imports at module top under C1 names, _simulation_timer); .040 (singletons, constructions, reset_interfaces/reset_test_state, raise_on with times and a param filter, TEST-NET); step 21's behaviour (IncompleteResponseError, refusal reclassification, parse_header_line(b"") raises, fetch timeout_s). Step 21's types and header come later.
Deviations:
- I pulled the whole Timer, step 90, step 21's behaviour and A-6 into MN1. C1 makes rdid required, so wozi's FRAM needs both table sizes, and removing the sugar would otherwise break collect-only.
- BoundedLog keeps U24's in-place ring, not a deque. It is generic through a runtime-subscriptable Generic stand-in, so _twin_common has no explicit Any.
- peripheral() raises ValueError on a malformed name (the packet says return None).
- raise_on entries are (type, args, times[, params]).
- ECONNREFUSED stays a plain OSError: MicroPython's open_connection only reports it at the first write. There is no `from e`, because MicroPython prints "exception chaining not supported".
- The mem_backup state file has the keys cause/watchdog_reason/chip_reset/regions. A bad file prints a line and boots as a power-on; an empty path means in memory.
- The UART registry is now the module-level _UART_OBJECTS; supersede semantics stay for now.
- I dropped two owner attributions I could not verify (COUNTER_CAP; Connection: close).
- The FRAM datasheet PDFs cannot be rendered here (no pdftoppm). The RDID bytes come from asy_fram_driver._KNOWN_PRODUCT_IDS.
Seen failing first: new tests run on a scratch copy of 8e7dedc. The failing lines are in S/u25/laneMN/base2_*.log and base_*.log. Representative ones:
- Machine: machine.py:999 (a bus without a plan), :980 (a configure after a bus is accepted), :1185 (re-arm runs two loops, 5 calls), :1141 (17th alarm armed), :1119 (Timer(0)), :1287 (unknown FRAM size wired), :1111 (counter steps past the cap), :915 (BoundedLog drops past the cap), :1096 (a reset is swallowed), :1245 (no wire time).
- HTTP: http:523 (a reset before any byte is a plain OSError(104)).
- Network: :178 (singletons), :229 (192.168.1.42), :202 and :211 (raise_on).
- Guard: the outcome-2 test passed on base; a planted `outcome >= 2` bite failed it at network_neopixel.py:243. The nothing-listening case failed on my first draft (CeilingRefusedError(111)).
Red until C1: every file importing the twin machine (machine.py:16-20, the twin mypy pass too) and tests_scripts/test_buildgen_twin_wiring.py (CPython ImportError).
Still red under a C1-names shim:
- G: bus_hazard_concurrency (20), generic_wiring (15) and isl29125_autorange (20), all from configure_i2c_wiring; uart_link (fails at import); sensortask_integration (14, configure after a bus, needs reset_peripherals).
- C: fram (5), scd30 (2), configure after a bus.
- SH: webserver_concurrency_* (19 each) and real_website_integration (9, no wozi default).
- P: construction_* (2 each); test_buildgen_twin_wiring.py (_current_wiring_plan).
- R: launch (crash) and run_generic_integration (14), from StatePaths' 3 fields and the raise_on form. Twin mypy: launch.py:186,199; run_generic_integration.py:85,151,450; their tests :24,121,215 and :68,315.
- wifi_modes passes.
Lines owed to the lead (stale entries):
- tests_scripts/test_import_placement.py:55-59
- tests_scripts/_citation_allowlist.txt:80-81 ("Step 5")
- tests_scripts/test_no_variant_literals.py:38 (machine.py) and the tests_hardware/isl29125_conformance.py entry
- I removed Timer from test_fake_surface_conformance.py:27 and check_reset_never_returns from test_digital_twin_machine.py's pending list (A-3).
Owed to X: test_tunables_register is red on 5 new tags, each estimated with its measurement owed: l2.http_client_fetch_timeout_s=0.005, l2.http_client_silent_server_s=2, l2.machine_timer_short_period_ms=5, l2.machine_timer_rearm_window_ms=18, l2.machine_spi_wire_time_us_per_byte=200.
Scan: no new silent failure. Drops are counted; a bad state file prints; peripheral() raises on a bad name.
After-times (all on the C1 shim, zero MemoryError at -1, 32768 and settrace):
- machine: 1.39 s / 1.43 s against base 1.317 / 1.334.
- network: 15.57 s / 15.56 s against 14.79 / 14.78.
- uart: 3.61 s / 4.25 s against 3.73 / 4.41.
- http_client: 0.053 s / 0.064 s against base 0.044 / 0.049. That is more than 10 %, but +9 to +15 ms in absolute terms, mostly the 5 new real-socket cases including the irreducible 5 ms timeout case.
Runs: redsweep (pid 15121), redsweep2 (16097) and redsweep3 (17533) all exited 0; the late-logged 84 s convention run exited 1 on the three expected reds. Nothing of mine is running.

---

U25 lane MN, final hand-back (S/wt-u25mn, branch audit/u25-mn). Nothing of mine is running, and the typings link is removed.
1. Commits: 72ece42 (WIP MN1), 68ffbc1 (merge <API> e34ffd6), 91d8b98 (the 5 priority items), **4d40389 FINAL** (19 files, all in files_MN.txt).
2. Applied: 21/104, all of 32 (incl. M.TWIN.036 comments), 59, 88, 89, 90, 107-109/123, 111, 122, the FE/BE case, the KeyboardInterrupt fix and isl29125_conformance (A-6). C relay done: co2 line, OSR 0x02.
3. Already landed, verify only: 50 tests/machine.py:49-225; 51 tests/neopixel.py:1-41; 52 tests/machine.py:378-556; 53 tests/machine.py:591-603; 56 tests/machine.py:500-505,689-696; 58 tests/_machine_contract.py:32-137 (needs no hook); 91 digital_twin/machine.py:1335. Pending lists emptied: test_digital_twin_machine.py:99, test_fake_surface_conformance.py:27.
4. Deviations:
   - NeoPixel writes stay RGB-tuple lists.
   - peripheral() raises on a malformed name.
   - settle deadline is the last due time + 1 µs.
   - UART deinit keeps U24's register reset; Pin keeps U24's line model.
   - machine.py keeps 3 explicit Any (:134, :414, :459; I2C.devices by design).
   - FLUSH_EXTRA_PAGES=36 is derived from the ~1.6 KB config; tSE/tPP come from S/w25.txt:3103-3104.
   - The stall windows moved into _flash_stall: the main mypy pass resolves `machine` to tests/machine.py.
   - UART.init takes txbuf/rxbuf/timeout/timeout_char/invert as **settings:int: max-args 8, no exemption added.
   - _in_running_task reads asyncio.core.cur_task (core.py:259) and allocates nothing.
5. Seen failing first (this phase):
   - rp2_constants: missing module, then bites at :36 and :69; settle steps :173 [9]; UART keyword :100.
   - Stall FIFO: old test fails with a planted 500 µs gap, new one passes; DMA guard :380 (0); window bites :397/:395.
   - Hard-callback report :1418; unreadable mem_backup path :1270; reset knob bite :1198.
6. Red, not mine:
   - test_tunables_register: D (my 9 tags, and SPECIFICATION.md:10823 150→100).
   - test_decision_vocabulary: lead deletes _decision_vocab_allowlist.txt:143 and :145.
   - test_import_placement: lead deletes :68-70.
   - test_counter_steps: C's 3 counters, green in a trial merge with b6f50ac.
   - Twin mypy, 89 errors, all G's: bus_hazard 23, generic_wiring 6, isl29125_autorange 2, sensortask_integration 56, uart_link 2.
7. Scan:
   - Class 4: twin hard Timer callback failure was silent. Fixed (mpirq.c:91-92). New.
   - Class 4: non-ENOENT OSError on the mem_backup state path booted as a power-on. Fixed (raises). New.
   - Floors: the stall tests rode the run-up gap (FIFO case red under settrace; DMA case could pass with no window). Fixed with a measured window and a guard. New.
   - Class 5: the twin soft Timer never drops a callback; rp2 drops one once its depth-8 scheduler queue is full (mpconfigport.h:131, mpirq.c:105). New, parked under A-35.
8. Owed to D:
   - Tunables (estimated, agent 2026-10-14, measurement owed): http_client_fetch_timeout_s=0.001 (:32); http_client_silent_server_s=2 (:34); machine_timer_short_period_ms=5 (:90); machine_timer_rearm_window_ms=18 (:92); machine_spi_wire_time_us_per_byte=200 (:94); machine_uart_frame_wire_ms=5 (:31); machine_uart_frame_timeout_ms=50 (:33); machine_uart_stall_baud=38400 (:37); machine_uart_stall_pages=32 (:39).
   - Tunable changes: machine_wdt_short_timeout_ms 150→100; machine_timer_rearm_period_ms withdrawn.
   - API: UART.init(baudrate, bits, parity, stop, *, tx, rx, **settings), raising TypeError("extra keyword arguments given"); _flash_stall: EPOCH_US, windows, irqs_were_off, stall, flush_us, install, reset_test_state (machine.reset_test_state calls it and _wall_clock's); machine._report_uncaught.
   - Fidelity tests: test_digital_twin_rp2_constants.py, the two flash-stall cases, test_init_refuses_a_keyword_rp2_does_not_take, the soft/hard callback cases, test_an_unreadable_mem_backup_state_path_raises..., tests/_mem_backup_contract.py.
9. Lines for the lead to retire (each probe-verified):
   - digital_twin/typecheck.ini:34-35, :40-41, :50-51, :56-57, :58-59 ([mypy-machine] stays).
   - pyproject.toml:278-279 and :306 (_http_client ANN401), :302 (S106).
   - The Mapping change clears C's scd30:55, fram:829 and sgp40:241: mypy-clean in the trial merge with b6f50ac, where my 6 files also pass.
10. Timing:
    - machine 1.107/1.181 (−16%/−11%); uart 3.810/4.844 vs 4.413 at 32768 (+9.8% to the table, +9.2% to an interleaved base run; made efficient); network +5%/+6%; fakes +2% interleaved.
    - Only http_client is over 10% to the table (0.060/0.057 vs 0.044/0.049); interleaved base runs give +8%/+1%.
11. Runs (all logged in RUNS.md):
    - Both GC stages 12/12 and settrace 6/6 rc 0, with zero MemoryError.
    - mypy: main, main-with-args and host 0; twin 1 (G's files).
    - The 14 checks: 4 red (item 6); collect-only rc 0.
    - Logs in S/u25/laneMN.
