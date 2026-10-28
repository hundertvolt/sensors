# U25 wave-1 relay (from the finals; the lead fills each wave-2/D/lead section as hand-backs arrive)

## Lead rows to retire at the W1 merge (print each, match, delete; never add)
- C: tests_scripts/test_import_placement.py:64-65; _decision_vocab_allowlist.txt:138, 141, 376 (lines at C's final).
- P: test_no_variant_literals.py:48-53, 67-72; vocab: the five "Below the OS ephemeral range..." rows and the
  test_device_tomls.py `_DEVICES` row; citations: the construction library's `WP1` x2 and `decision 10`; _PENDING
  ('tests/_digital_twin_construction_scenarios.py', '_scenario_bus_fault_degrades.scenario', 'errno').

## For SH (wave 2)
- P moved two HTTP scenarios out of the construction library (quoted from 8e7dedc): `_scenario_measurements_and_sensors_shape`
  (GET /measurements and GET /sensors each 200, `assert_sensor_payload_not_self_wrapped(json, expected)`, expected = the
  upper-cased present SCD30/SGP40/BMP3XX/ISL29125); `_scenario_bus_fault_degrades` (SGP40 `writeto` gets OSError(EIO)
  times=5 on its plan bus; GET /measurements 200, never 500, body contains "SGP40").
- test_port_bands red on `tests/_webserver_concurrency_scenarios.py` (draw from its band) until SH removes/migrates it.
- 8e7dedc's put-matrix ResetErrors probe turns SGP40 backups off first (keep it; the twin has no NTP unless R's responder).

## For G (wave 2)
- test_port_bands red on `tests/test_digital_twin_sensortask_integration.py` (draw from its band).
- C: a FRAM `write` fault is now refused (rp2 SPI writes cannot raise): bus_hazard_concurrency:296, :344, :878;
  autorange :16, 62, 90, 559, 584; generic_wiring :117, 162 (default RDID gone).

## For D (wave 3)
- C: tags l2.bmp3xx_probe_hang_s=0.05 (tests/test_digital_twin_bmp3xx.py:15), l2.isl29125_probe_hang_s=0.05
  (test_digital_twin_isl29125.py:34), basis "a bounded small hang"; l2.fram_booted_until_yields=2000
  (test_digital_twin_fram.py:61, scheduler-yield bound). Fidelity rows (FRAM, SCD30, SGP40, BMP3XX, ISL29125) in C's
  final hand-back (b6f50ac); old names SPECIFICATION.md:4601, 9928, digital_twin/README.md:65, 356, 401, 740;
  README "SCD30 persistence" (six keys), "FRAM persistence" (load line, atomic save).
- MN (WIP): tags l2.http_client_fetch_timeout_s=0.005, l2.http_client_silent_server_s=2,
  l2.machine_timer_short_period_ms=5, l2.machine_timer_rearm_window_ms=18, l2.machine_spi_wire_time_us_per_byte=200.
- R (WIP): l2.twin_feed_gap_fold_ms=5000 (runner:167), twin.ntp_responder_poll_ms=10 (responder:22, estimated).
- P: SPEC E.2.1/E.3.1 + README: TEST_DEVICE recipe, tag form `[test_sensortask[dev]]` (README:183),
  pyproject.toml:387's six-files comment; E.1 band rows incl. 17500-17509; generator `--device-toml/--out-dir`;
  fidelity: scenarios `boot_sequence_matches_the_generated_expectation`, `irq_pins_are_shared_by_chip_fake_and_driver`;
  digital_twin/README.md:36-41 names the IRQ guard. SPEC cites tests/test_sensortask_dev.py (test_citations red).

## From MN's final (4d40389)
- Lead rows at W1: _decision_vocab_allowlist.txt:143, :145; test_import_placement.py:68-70 (lines at MN's final).
- Lead step (after wave 2): digital_twin/typecheck.ini:34-35, :40-41, :50-51, :56-57, :58-59 ([mypy-machine] stays);
  pyproject.toml:278-279, :306 (_http_client ANN401), :302 (S106); each probe-verified by MN.
- test_counter_steps: C's 3 counters, green in MN's trial merge with b6f50ac (expect green at W1).
- G: twin mypy 89 errors in G's files (bus_hazard 23, generic_wiring 6, isl29125_autorange 2,
  sensortask_integration 56, uart_link 2) = the wave-2 migration to MN's API.
- D: tags (estimated, agent 2026-10-14, measurement owed) l2.http_client_fetch_timeout_s=0.001 (:32, replaces 0.005),
  l2.http_client_silent_server_s=2, l2.machine_timer_short_period_ms=5, l2.machine_timer_rearm_window_ms=18,
  l2.machine_spi_wire_time_us_per_byte=200, l2.machine_uart_frame_wire_ms=5, l2.machine_uart_frame_timeout_ms=50,
  l2.machine_uart_stall_baud=38400, l2.machine_uart_stall_pages=32; changes: machine_wdt_short_timeout_ms 150->100
  (SPECIFICATION.md:10823), machine_timer_rearm_period_ms withdrawn. API end states: UART.init(baudrate, bits, parity,
  stop, *, tx, rx, **settings) raising TypeError("extra keyword arguments given"); _flash_stall (EPOCH_US, windows,
  irqs_were_off, stall, flush_us, install, reset_test_state); machine._report_uncaught. Fidelity tests:
  test_digital_twin_rp2_constants.py, the two flash-stall cases, test_init_refuses_a_keyword_rp2_does_not_take, the
  soft/hard callback cases, test_an_unreadable_mem_backup_state_path_raises..., tests/_mem_backup_contract.py.
- New open finding (scan class 5, MN, parked; CONCURRENCY rule 2): the twin soft Timer never drops a callback, rp2
  drops one once its depth-8 scheduler queue is full (ports/rp2/mpconfigport.h:131, shared/runtime/mpirq.c:105);
  target: the next unit whose work-order files hold digital_twin/machine.py (lead names it at U25's close).

## From R's final (d300267)
- SH and G: tests_scripts/test_twin_entry_point_order.py is red on 8 files until wave 2 migrates them:
  test_digital_twin_bus_hazard_concurrency (G), test_digital_twin_real_website_integration (SH), the six
  test_digital_twin_webserver_concurrency_* through _webserver_concurrency_scenarios.py (SH).
- SH: the runner's shutdown line gains `flash_stall_longest_ms=<n> uart=<key>:transfers=<n>,failures=<n>,overruns=<n>`
  (overruns = asy_uart_driver.UART.rx_overruns, which counts laps and receive errors together: name it so in the suite
  parser and docs); runner exits 3/4/5; persistent defaults digital_twin/{fram,scd30,mem_backup}_state.json and
  digital_twin/config/; the NTP responder holds 127.0.0.1:123 exclusively (refused bind + retake).
- Lead step: _NOT_YET_CLEANED retired at W1; pyproject.toml:381 exclude, typecheck.ini:9 comment,
  [mypy-unix_port_poll_prewarm] freed (lead step, with MN's typecheck.ini/ANN401 lines).
- D: tags l2.twin_test_stdin_poll_ms=50 (runner), twin.ntp_responder_take_rounds=20, twin.ntp_responder_poll_ms=10
  (responder), l2.twin_feed_gap_fold_ms=5000 (runner), l2.ntp_reply_wait_ms=1000, l2.ntp_run_bound_s=10.0,
  l2.ntp_sync_wait_timeout_s=20.0 (tests/test_digital_twin_ntp.py); l2.twin_ready_poll_ms loses its
  segfault_stress_repro.py site. API: runner product_modules(), _uart_links(); NtpResponder(port, host): mode,
  offset_s, holding, requests, ignored, serve(), close(). Fidelity: tests/test_digital_twin_ntp.py's five booted
  cases, test_asy_ntp_client.py's responder section. Citations to fix: CLAUDE.md and SPECIFICATION.md cite
  unix_port_gc_unwedge.py, segfault_stress_repro.py, tests/test_digital_twin_unix_port_gc_unwedge.py (retired) and
  tests/test_sensortask_dev.py (P's removal).
- Review list: test_asy_ntp_client.py not D.15-reordered (out of order at base; sorting scatters 35 helpers) -> open
  finding for the next unit working that file; tests/test_digital_twin_ntp.py is a new 34-35 s file (38.8 s settrace):
  where its time goes is checked at the W1 timing pass before it is accepted.

## Wave 2: SH final fa31ee7 (07:08)
- D: 33 tunables (new, moved, withdrawn; value, site, basis) in S/u25/laneSH/tunables_SH.tsv, incl. l0.live_smoke_timeout_ms=45000 at
  tests_js/live-backend.test.js:10 (measured 6.2-7.2 s, six devices); SPEC :10757 and :10780-10783 sites; :10842-10843 rows retire.
- D: the in-DUT webserver/real-website files are gone (tests/_webserver_concurrency_scenarios.py, test_digital_twin_real_website_integration.py,
  six test_digital_twin_webserver_concurrency_<dev>.py); the host harness scripts/_digital_twin_scenarios.py (families (a)-(e), (k), (l), (m), 50
  ported) runs from run_digital_twin_ci.sh after the suite, both GC stages; scripts/_twin_process.py is the shared twin launcher.
- D (pending lane E): the twin CI job's shape and per-device times change once E lands (boot sharing, per-stage CI job); take E's facts.
- D (pending lead W2 fix): the twin AP's address is the cyw43 layout on the loopback (127.0.0.1/24), not 192.168.4.1; README fidelity row.
- Lead W2: DNS (twin AP subnet vs loopback clients), hang arming (after start_tasks), CFGMGR_NTP W10 x4 (partial planted NTP store: 2 of 6 keys).

## Wave 2: G final 926f2ac (08:19)
- D tunables (all l2.): twin_readiness_poll_ms=10; timer_pool_wait_s=20.0, timer_pool_run_bound_s=60.0; hot_replug_wait_s=40.0,
  hot_replug_run_bound_s=90.0; bus_hazard_command_wait_s=20.0; clock_jump_wait_timeout_s=20.0; sensortask_integration_idle_window_s=3.0,
  sensortask_integration_heap_floor_reads=3; uart_comm_hazard_timeout_ms=100, _run_limit_s=30, _recovery_attempts=2;
  uart_field_sweep_timeout_ms=30, _quiet_window_ms=45, _run_limit_s=120; uart_link_crc16_rounds=3, uart_link_leak_warmup_rounds=20,
  uart_link_leak_rate_bytes_per_transfer=16 (replaces uart_link_leak_budget_bytes; basis 0.6 B clean, 78 B with a planted 16-byte leak);
  wifi_modes_sleep_scale=5. Changed: hotspot_wait_timeout_s 40.0, hotspot_run_bound_s 60.0, wifi_modes_wait_poll_s 0.1.
- D API: tests/_twin_readiness.wait_for_value(read, expected, limit_ms) -> bool. Fidelity table: the test_* of G's 4 new G2 and 3 new G1 files.
- D: the in-process hotspot DNS answer check moved host-side (harness); MEASURE udp.idle_wakeups_per_s=9.66 (test 10).

## Lead step (W3) facts for D
- SPEC F.1: drop tests/_webserver_concurrency_scenarios.py from the named import-placement exceptions (test_import_placement's
  _NAMED_EXCEPTIONS already dropped it: red until F.1 matches).
- SPEC E.6.6: rows (ID, scenario, reason) for every twin scenario with no L3/L4 counterpart: ci_suite._run_12_reset_reasons,
  ci_suite._run_13_system_commands, clock_jump, fram_crash_points, hot_replug, ntp, rp2_constants, ... and the harness families E
  declares that no bench file covers (test_level_containment.py names them; run it on W3+E).
- Citations to fix (CLAUDE.md, SPECIFICATION.md): digital_twin/unix_port_gc_unwedge.py, digital_twin/segfault_stress_repro.py,
  tests/test_digital_twin_unix_port_gc_unwedge.py, tests/_webserver_concurrency_scenarios.py, tests/test_digital_twin_real_website_integration.py,
  tests/test_sensortask_dev.py (test_citations.py lists each line).
- Part N: every tag test_tunables_register.py names (SH's 33, G's list, R's and MN's from relay W1).
- digital_twin/README.md: the AP-mode fidelity row (127.0.0.1/24, cyw43's layout on the loopback, and why).

## Lane E (26fb9be) and the lead's CI split (a8dc1a1) - facts for D
- scripts/run_digital_twin_ci.sh <device> [--gc-threshold -1|32768] [--part suite|harness]: without options both stages and
  both parts (local runs, scripts/_run_lower_levels.sh); ci.yml digital-twin-e2e is device x gc_threshold x part (24 jobs), the
  artifact digital-twin-ci-logs-<device>-gc<stage>-<part>; the 20-minute limit and its tag unchanged.
- Harness: @scenario(name, family=..., shared=..., moves=...): shared scenarios run first on one twin per group, an idle check
  between them (twin alive, slots drained, kernel accept queue 0 from /proc/net/tcp, error counts after the drain, memory gate);
  a failure names the scenario and the next boots fresh. Families: webserver_concurrency 20, sensortask_integration 10,
  real_website_integration 9, bus_hazard_concurrency 1, system_commands 6, webserver_requests 3, uart_load 1 (30 share, 20 own boot).
- Runner: the WDT prints WATCHDOG_WOULD_TRIGGER count=N when it would reset silicon; the hung-step scenario ends on it.
- Suite Run 13: the erase precondition is the planted chip's own entry (a timed-out wait or exited twin fails naming chip and fault).
- @tunable l2.scenario_commanded_reset_margin_s gains a site (S1's wait in the hung-step scenario).
- E.6.6 rows owed (test_level_containment.py on W5 names them): ci_suite._run_12_reset_reasons, ci_suite._run_13_system_commands,
  clock_jump, fram_crash_points, hot_replug, ntp, rp2_constants, system_commands, timer_pool, uart_comm_hazard, ... and the stale
  row `twin-instrument` naming unix_port_gc_unwedge (retired).
