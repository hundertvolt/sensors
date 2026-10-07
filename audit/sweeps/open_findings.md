# Open scan findings

Silent-failure findings that no planned step closes, each held here until a unit closes it (agent, 2026-10-07: a
finding left only in a scan record has no unit to act on it). A unit's lead reads the rows naming that unit before
building its packets, puts each into a step, and at the close marks it closed (with the commit) or moves it on, with a reason.

| # | site | class / mode | from | target | state |
|---|---|---|---|---|---|
| OF-01 | `tests_hardware/device_scripts/uart_idle_poll_rate.py`: a listener still running after `comm.clear()` is cancelled without a word | 4, 6 / listener stop | SF-U8C2-01 | U30 (M.HW_DEV.050) | open |
| OF-02 | `bus_topology_autodetect_and_hazard_sweep.py` `broadcasts()`: a NACKed general call is swallowed, so the self-hazard can run with no reset sent | 4, 3 / bus hazard | SF-U8C2-02 | U35 (M.HW_DEV.090) | open |
| OF-03 | `uart_link_under_concurrent_system_load.py`: a `verify_present()` False is counted nowhere | 4, 1 / load | SF-U8C2-03 | U30 (M.HW_DEV.051) | open |
| OF-04 | `uart_link_under_concurrent_system_load.py`, `uart_idle_poll_rate.py`: `setup()` results ignored | 1 / script boot | SF-U8C2-04 | U30 (M.HW_DEV.050, .051) | open |
| OF-05 | `bus_topology…`: the SCD30 self-hazard read checks only "no exception" | 3 / bus hazard | SF-U8C2-05 | U35 (M.HW_DEV.090) | open |
| OF-06 | `fram_pause_unpause_and_gating.py`: a `hog.deinit()` failure is swallowed | 4 / alarm pool exhausted | SF-U8C2-06 | U26 (M.HW_DEV.068) | open |
| OF-07 | `isl29125_mechanism_envelope.py`: the restore `_set_dict_cfg(...)` results are ignored | 1, 4 / reconfiguration | SF-U8C2-07 | U26 (M.HW_DEV.142) | open |
| OF-08 | `isl29125_mechanism_envelope.py`, `isl29125_lighting_scenarios.py`: "no E entries" reads the capped history only; `ErrCount` beyond its length is unchecked | 2 / error log full | SF-U8C2-08 | U26 (M.HW_DEV.142, .143) | open |
| OF-09 | `tests_hardware/harness.py` `wait_for_script_server()`: `main.py`'s server answering past the handover window reads as the script's | 3 / boot handover | SF-U8C2-09 | U26 (M.HW_BENCH.015) | open |
| OF-10 | `tests_hardware/bench/test_network_resilience.py`: a connection admitted above the ceiling is retried and unreported when a later attempt passes | 6, 3 / load | SF-U8C2-10 | U26 (M.HW_BENCH.080) | open |
| OF-11 | `tests_hardware/bench_control.py` `start_udp_source_capture()`: tcpdump's stderr goes to `DEVNULL`, so a tcpdump or sudo failure reads as "no packet" | 4 / network fault injection | SF-U8C2-11 | U26 (M.HW_BENCH.021) | open |
| OF-12 | `tests/test_asy_uart_comm.py`: literals added after the classification baseline (`limit=20` three times, `sleep_ms(1)`, `wait_for(…, 10)`) are untagged | 3 / retune | U8C scan | U16 (M.TEST_UNIT.158) | open |
| OF-13 | `tests/test_asy_webserver_service.py`: A.U8C.21 and A.U8C2.05's tags are in no step | 3 / retune | U8C, U8C2 scans | U11 (M.TEST_UNIT.200) | open |
| OF-14 | `tests_hardware/conftest.py`: A.U8C2.25's tags are in no step | 3 / retune | U8C2 scan | U26 (M.HW_BENCH.003) | open |
| OF-15 | `src/asy_wifi_service.py` `_STA_DISCONNECT_WAIT_ITERS = const(20)`: a tuned count no step tags | 3 / retune | U8 scan | U10 (M.SRC_NET.001) | open |
| OF-16 | `tests_scripts/test_tunables_register.py`: Sites list each literal once per file, so deleting one of two same-literal tags in a file goes unnoticed | 3 / retune | U8 scan | owner review | open: closing it extends Part N's Sites format with a per-file count (16 file and ID pairs carry several tags); the format is in force, so the extension waits for the owner (U9 review row) |
| OF-17 | `src/asy_webserver_service.py` `RouteSources.error_sources: Sequence[_ModuleLike]`: the generated wiring passes `NeopixelDriver` and `DNSServer`, which lack the protocol's methods; mypy does not see it because the generated modules are outside the typecheck pass | 3 / typing, boot wiring | U9 scan | U10 lane A (A.U10.46, the typing aliases and generated wiring) | open |
| OF-18 | `tests/microtest.py`: a file's tests run in its globals dict's hash order, so an unrelated module-level name reorders them (U8C's constants did, exposing SF-U8C-02); order-dependent effects surface by accident | 3 / every test file | U8C fix | U24 (M.TEST_HELP.001) | open |
| OF-19 | the digital twin runs on the Unix port, whose `time.gmtime()` has 9 fields where rp2's has 8, so `asy_ntp_client.cettime()` returns `None` in every twin run: the generated notification wiring never has a local time there, and no twin run or twin CI check evaluates a notification window | 3 / twin, every run | U9 gate | U25 (M.TWIN.049, the generic twin runner) | open |
