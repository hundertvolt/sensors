H2 hand-back (lane H, block 2). Commit e9fd1c7 on audit/u35-h, in S/wt-u35h. Nothing is uncommitted and nothing of mine is running. I used about 71 tool calls.

Steps by verdict:
- OF-226 (R-14), applied in H1's form.
  - The loop-lag script takes BENCH["mode"] "production": main() runs on the board's own config and serves on the board's address. With no mode it keeps the scratch config on 127.0.0.1:8080.
  - New bench test, test_memory_stress_bench.py `test_loop_lag_under_http_load_on_every_route_stays_under_the_smallest_hard_consumer`. It saves errcount first, waits with wait_for_script_server, and runs the hammer's ceiling of readers (now `_readers()`, shared with the hammer) on every JSON GET route. It asserts every route answered, the memory markers, main_running, the FRAM writes and the lag against smallest_hard_consumer. It restores serving in a finally.
  - The flash loop-lag test now runs on the twin only, with the same load and evidence on 127.0.0.1:8080. Silicon's run is the bench test. Both tests fail on an empty route table.
- The probe finding, applied. The sweep's `_probe()` treats only ENODEV as an absent device: on rp2, soft I2C's address NAK (ports/rp2/machine_i2c.c:127-145, extmod/machine_i2c.c:199-203). ETIMEDOUT, or any other errno, is reported as "a bus fault, not a NAK".
- Held-SDA rc=1: it matches its record entry, so it is not a new failure.
  - The entry at f3fff0e (unchanged since 1dd6dd5): result "exception", reason "...the held-SDA recovery (bit-banged pins hold no SDA in the twin)...". It sits on both i2c_held_sda_recovery.py and test_bus_concurrency.py.
  - The line-level cause of H1's r7/r8 (AssertionError at test_bus_concurrency.py:258, held False): the script reads sda.value() after the ACK clock (i2c_held_sda_recovery.py:53-77). In the twin an open-drain Pin.value() returns `_line()` (digital_twin/machine.py:313-314). `_line()` reads only planted external levels (:223-227), and the twin's chips drive no pin, so SDA reads 1. Not re-run: the script and its test are unchanged.

Seen failing first, and the bites (scratch copy deleted; nothing planted was committed):
- A2: the new bench test on the old script fails at test_memory_stress_bench.py:162, "GET routes never served ...; the loop-lag script's own server never answered".
- A1: the new flash test passed on the old script, so its route check is a guard. Bite B2: the script's server moved to 8081 fails at test_memory_stress.py:159.
- A3: the old sweep with a planted ETIMEDOUT at 0x78 passes with 0 errors, which shows the gap. B1: the new sweep with the same plant fails at test_bus_concurrency.py:247, "i2c0: probing 0x78 misbehaved: a bus fault, not a NAK: ... ETIMEDOUT" (i2c1 too).
- G1/G2: an empty route table passed both tests with nothing checked. G3/G4: with the guards both fail, "[] of 0 routes".

Effect per device and mode:
- No firmware changes. These are device scripts on the bench board (dev).
- Sweep: on dev's i2c0 and i2c1, a probe that times out now fails the sweep. A NAK still reads as absent. A healthy twin is unchanged (errors 0).
- Loop-lag, production mode (bench only):
  - STA: reachable on the board's own address.
  - AP, Silent, Off: the host cannot reach it, and the test fails visibly with "never answered".
  - USB: the facts go out as before.
  - Wear: silicon no longer writes the scratch defaults each run. The production boot writes only an absent file or a repair.

Decisions (agent, 2026-10-21):
- I reused the declared extra `mode` (bench_facts.pyi:65), so bench_facts.pyi is unchanged.
- The flash test is twin-only; silicon runs the bench test.
- The twin keeps the scratch config, so nothing goes into the session's twin filesystem and it needs no port 80.
- Only ENODEV counts as absent.
- I added one new tunable, the bench script timeout of 90 s, on the flash test's basis.

Red checks:
- test_persistence_write_marker_completeness.py:689 (lead). Its message: the script now "runs main() over the production config unmarked". It needs loop_lag_under_combined_load.py in `_PREREQUISITE_DEVICE_SCRIPTS` (:443-449) with `_SERVING_REASON`, like uart_link_echo, or a ruling. That is an allow-list, so I did not touch it.
- test_tunables_register.py:253 waits on D. The new l4.memory_stress_bench_loop_lag_script_timeout_s (bench :49) needs its Part N row. I wrote the relay TAG line in `## H`.
- test_twin_record: expected.

Facts owed to D: tests_hardware/README.md:826-834 is stale ("the bench round only", "skipped unless the bench bridge is configured"). SPECIFICATION.md:12629's row should also name the bench timeout.

Scan:
- Class 4/1 at the sweep's `_probe` and class 3 (an empty route table passing with nothing checked): fixed.
- New and only partly covered (class 4, test side; owner lane H): in test_memory_stress.py, a `_lag_load` reader that dies of an unexpected exception gives only a pytest thread warning. The per-route check still fails if no reader reaches a route.

Runs (twin, dev; RUNS.md lined):
- E1/E2 flash test at -1 and 32768 (final tree): PASS. Lag max 29.4 and 54.9 ms, p99 20 and 31 ms, against a 925 ms bound. Every route answered 33-38 times.
- D3/D4 bench test at -1 and 32768: PASS. Max 54.1 and 45.2 ms; 219 and 207 reads answered.
- C5/C6 sweep at -1 and 32768: PASS.
- Zero MemoryError and zero "memory allocation failed" in every output.
- mypy main, device-script and host passes: clean on cold caches.
- pytest --collect-only tests_hardware: rc 0, 197 of 228 collected.
- 42 readers: 38 green and the 3 reds above. test_bench_harness_helpers was also red ("join in a finally"). I fixed that and reran it green, with comment_block_cap, decision_vocabulary, citations, code_conventions and digital_twin_scenarios.
- One batch, checks.sh pid 23729, died on a syntax error in my loop line after mypy and collect-only had run; its RUNS.md done line says so.
- Times: about 31 s per loop-lag run. No unit-tier or twin-tier file changed, so there is nothing to compare with the base table.

H3's start state: e9fd1c7. H2's four files are final: the sweep, loop_lag_under_combined_load.py, test_memory_stress.py and test_memory_stress_bench.py. Still owed at H3: step 140 with OF-229, the 17 scans, H's full silent-failure scan, and the reader-death thread above.

Logs: S/u35/laneH/h2/ (A1-G4 .log and _out.txt, runs.rc, checks.rc, final.rc, again.rc, ts*_*.log, mypy_*.log, collect.log, and the drivers h2_call.py, h2_bite.py and runs.sh).