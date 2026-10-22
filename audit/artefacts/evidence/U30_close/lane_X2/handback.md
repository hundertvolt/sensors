U30 lane X2 FINAL
Commit c12668a on audit/u30-x2 (S/wt-u30x2, from e668031). Not pushed and nothing left uncommitted. Only SPECIFICATION.md (Part N untouched) and digital_twin/README.md changed.
Edit 1, applied, README:803-810, Run 12's stack cell. It follows the code: scripts/_digital_twin_ci_suite.py:100-101 (the read op for each driver), :903-916 (the cell: the `:stack` fault, the 120 s wait, exit 3, would_have_triggered_count==0, relaunch ResetReason 20 with one SYSTEM STACK_EXHAUSTED entry, the named skip), :1585-1594 (subject: I2C before SPI), :720-735 (relaunch on the same state). The injection is digital_twin/launch.py:210 (RuntimeError "maximum recursion depth exceeded"); code 20 is src/asy_system_service.py:86.
Edit 2, applied, SPEC:8618-8635, I.4(e) fold (6), rewritten to the landed option 1. The owner's question and "Option 1 is good" are kept. Each claim checked against:
- tests/_generated_module.py:36 (ERROR_LEVEL = 1), :93-105 (log_errors) and :120-128 (the plant only when no config is stored);
- the direct build_system/main callers' write_error_level_config() calls (9 twin files plus the scenario library :494/:771/:1558);
- Pair/build_pair (tests/_uart_comm_harness.py:45-74, :219), hazard_pair (tests/_uart_comm_hazard_common.py:52) and _make_service (test_asy_webserver_service.py:3889, :3927, :4018);
- the opt-outs (_sensortask_scenarios.py:188-190, 11 log_errors=False); test_bus_hazard_multi_device has no debug at all (L's decision (5), tagged agent).
Owed lines also applied:
- README:438, 462-463: the three runner-flag rows, checked against run_generic_integration.py:232, 245-246, 323-331, 537-571.
- README:825-832, harness paragraph: error-level boots and the --test-kbd-traceback / second-SIGINT description. Checked against _digital_twin_scenarios.py:248-263 (the only spawn site), :706, :975-985 and _twin_process.py:171-185, 366-386. The harness extension is tagged agent, 2026-10-20.
- README:1163-1170 plus a new SPEC F.7 row 32 (6898): the 255-byte qstr limit on launch strings. Re-checked in v1.29.0 source: ports/unix/main.c:412/560/688, py/qstr.c:319-321, py/mpconfig.h:367-369, ports/rp2/main.c:208. The refusals are at _twin_process.py:210-216/:400-402, test.sh:191-264, tests_js/_twin_process.js:32/:200, twin_board.py:67-69 and run_unix_port_integration.sh:20.
- SPEC:3418-3421, C.7 teardown (M2): asy_uart_driver.py:467-468; I2C/SPI always True (asy_i2c_driver.py:340-347, asy_spi_driver.py:62-69).
- SPEC:4938-4940, E.3 exit 2 (V4): test.sh:256-264.
- SPEC:8611-8613: the I.4(e) console() list adds asy_uart_driver (its 9 console sites).
- C.7.1 was already done: SPEC:3496-3497 already lists asy_uart_driver.py among the layers with no logger.
Checks:
- the 16 scans in one call: 837 passed, 0 failed, 68 s;
- the 13 doc-reading tests_scripts files (unshare ns_xdg): 330 passed, 58 s;
- the pre-commit checks error_catalog, lint_ceilings and mypy_any_baseline, plus vocabulary, citations and cap after git add: 711 passed;
- zero memory markers in any log.
I narrowed "reads either doc" to the 13 files that open a doc at runtime, not the brief's ~110-file mention grep (agent, 2026-10-20).
No code changed, so there was no silent-failure finding and nothing to time. Nothing relayed. Logs are in S/u30/laneX2/, and RUNS.md has the start and done lines. Nothing of mine is running.
