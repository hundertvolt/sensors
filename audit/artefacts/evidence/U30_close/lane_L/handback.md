U30 lane L FINAL
Commit a8eadb9 on audit/u30-l (S/wt-u30l, from f594679), 20 files under tests/. Not pushed. No src/ change, so no product change: STA, AP, Silent, Off and USB behave as before.
Applied: tests/_generated_module.py gains ERROR_LEVEL, write_error_level_config() (plants config_SYSTEM.cfg = {"DebugLevel": 1} only when absent, like the NTP writer) and an opt-in log_errors on boot_generated, beside offline_ntp. The default stays off, so its 3 other callers are unchanged. Opted in:
- the scenario library's _boot() and its 3 main() calls, which covers test_sensortask and test_neopixel_wifi_integration;
- the twin construction scenarios;
- 9 twin files' own boots;
- Pair, build_pair and hazard_pair take debug, passed by: the whole comm-hazard file, the cancel sweep, the twin comm-hazard and field-sweep files, and test_asy_uart_comm's 4 flood and large-train tests (its plain build_pair tests stay off);
- _make_service takes debug, passed by its 6 hammer builders.
The 8 section-2 scenarios (11 calls) pass log_errors=False. No opted-in test sits inside an echo-off record_prints block.
Decisions taken (agent, 2026-10-20):
(1) The scenario library's _boot defaults to log_errors=True, with explicit opt-outs.
(2) Pair and build_pair take a PairOptions TypedDict. A 9th parameter breaks ruff's max-args 8, and I added no ignore; test_asy_webserver_service's _ServiceKeywords is the precedent.
(3) ERROR_LEVEL and the SYSTEM store name are `# pins` literals, checked by test_const_mirrors, instead of src_int(). An import-time read of src/ turned test_digital_twin_boot_contiguity red for dev: "319776 B below the seam, past the 307200 B bound". It is green on W1 and green twice with the pins.
(4) The UARTComms and link ends that opted-in files build directly also log at ERROR_LEVEL: 3 in test_uart_comm_hazard, plus UART_MISMATCH and the CRC16 pair in test_digital_twin_uart_link.
(5) test_bus_hazard_multi_device.py stays at OFF, so _fram_builders.py is unchanged. Its error-level catch sites (logged only when the level allows) allocate tens of bytes (a one-key config, a timer arm). Its big allocations are test-fake code with nothing catching them, so they fail loudly at any level, and FRAMManager's catches print through console(), which ignores the level. Heap probe: 22 of 23 pass at 2 MB and at 1 MB; the one failure is an uncaught allocation in tests/machine.py's SPI log append. The twin files' small chip-level builds follow the same rule.
Seen failing first: I planted a caught fault ("planted fault", printed through err()) in scratch copies of src/ at the end of SystemService.setup(), UARTComm.__init__ and WebserverService.__init__. On W1, all 18 opted-in files printed 0 lines in their opted-in tests; at the head they print 2-390 (S/u30/laneL/bite_summary.tsv). The only W1 lines (4) came from 2 sensortask scenarios not opted in.
- test_asy_uart_comm prints only in its 4 load tests, and the webserver file only in its 10 hammers.
- Opt-out bite: with every log_errors=False removed, exactly those 8 scenarios fail (82/90).
- Pin bite: changing either pin turns test_const_mirrors red, naming both.
Markers: zero everywhere, so nothing was relayed.
- Final sweep on a8eadb9: 78 rows (19 files, every device of the per-device files, -1 and 32768), all rc 0.
- build-settrace: 39 rows, rc 0 (run before the pin edit, which only removes import-time reads).
Checks: ruff clean; mypy main pass (both forms) and twin pass clean. 16 repo-wide scans: 832 passed. The 12 pre-commit checks plus code_conventions: all passed. test_memory_error_gate_agreement, test_digital_twin_boot_contiguity and test_fram_less_boot are unchanged and green.
Times (base S/u30/laneL/base_times.tsv on W1, final final_times.tsv): total 2583.6 -> 2570.4 s (-0.5%), no row over 10%. Largest: construction[arzi]@32768 1.69->1.83 s and neopixel@32768 3.00->3.25 s (+8.3% each). Three rows of the earlier after-sweep read over 10%; re-timed against W1 five times each, they came out +1.3%, +3.3% and +6.5%.
Scan findings (silent-failure class 4, "a check that matches nothing"):
- Covered by a8eadb9: the unit gate could not see lines that loggers suppress at OFF in the system builds and load tests.
- New, for the lead (no wave-2 lane holds these files): src/asy_uart_comm.py _allocate() `except (MemoryError, OverflowError): return tx, rx, bytearray(0), ...` logs no exception text, only "Construction failed, errno". src/asy_uart_driver.py deinit `except (MemoryError, OSError): ok = False` does the same. Both stay invisible to every marker gate at any level.
Owed to X: SPEC I.4(e) can now say the unit tests that can run out of memory (system builds, load tests) log at error level via boot_generated(log_errors=True), Pair/build_pair/hazard_pair debug and _make_service debug, and that test_bus_hazard_multi_device stays at OFF. Owed to Y: none. Owed to the lead: the two src sites above; no allow-list lines.
Runs, all logged in RUNS.md: base sweep pid 6392 rc 0, chain 21539 rc 0, chain2 3029 rc 0, settrace 4268 rc 0, final 10875 rc 0. Nothing of mine is running, and the helper worktree wt-u30l-w1 is removed. Logs are in S/u30/laneL/.
