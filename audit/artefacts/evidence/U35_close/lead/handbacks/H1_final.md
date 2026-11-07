H1 hand-back (lane H, block 1). Commit 76b2d7f on audit/u35-h. The worktree is S/wt-u35h, created from f3fff0e and rebuilt with rebuild.sh. Nothing is uncommitted and nothing of mine is running. I used about 74 tool calls.

Steps by verdict:
- 3, applied. test_end_to_end_timing.py: the FRAM check now uses assert_module_error_log_clean. It allows one warning, code("W","FRAM_BLOCK_INVALID"), and one error, code("E","FRAM_STATUS_BYTE"), per R-7. The comment quotes the owner: (owner, 2026-09-13, on the torn-write trace: "Settled as acceptable degradation rather than a robustness gap"). The import gains the clean helper and `code`. It is hardware only (R3 H68), so it is collected, not run.
- 5, applied: OF-02 and OF-05 fixed.
  - OF-02: the sweep's self-hazard now records broadcasts, naks and broadcasts_planned. An EIO counts as a NAK (rp2 machine_i2c.c:150-155). Any other OSError fails the sweep; it was swallowed before. The host test (test_bus_concurrency.py, sweep test) requires at least one broadcast.
  - OF-05: read_scd30 checks the cached CO2, temperature and humidity against BENCH["bounds"] (co2_ppm, scd30_temp_c, humidity_rh).
- 122, applied. The run_device_script.py comment cites ports/rp2/machine_wdt.c:44-61.
- OF-226, not applied (blocked). Details below.
- Check-only, all confirmed in the tree at f3fff0e: 1, 2 (`_nonempty` is gone), 7, 101, 103, 127, 129, 130, 131, 132, 133.

Seen failing first, and the bites:
- r1: the new host check on the old script fails with KeyError 'broadcasts'.
- r2: the old reader passes with the twin's SCD30 at 15000 ppm. This shows the OF-05 gap.
- r5: with the fix, the same plant fails. The errors fact reads "co2_ppm=15000.34… outside [200, 10000]".
- r6: a general call that times out, planted in a scratch copy, fails with "i2c0: no general call reached the bus (0 of 3 sent, 0 NAKed)".
- The scratch copy is deleted. Nothing planted was committed.

Decisions taken on the owner's behalf:
- "Sent" means the call reached the bus, NAKed or not. It does not mean acknowledged (agent, 2026-10-21). Reason: dev's only i2c0 device is a BMP3xx. The BMP388 datasheet has no general call, and the twin acks one only for an SGP40 (digital_twin/machine.py:495-500). So every broadcast is NAKed on a healthy bench, and an "acknowledged" check would always be red there. The brief's "all-NAK twin" is dev's normal twin, and it stays green (r3/r4: naks 3 of 3). I bit with a twin where the broadcast never reaches the bus instead.
- R-25: I cited :44-61, not :43-57 (agent, 2026-10-21). Line 44 holds the one static WDT object and line 61 returns it; :57 stops before that return.
- OF-226 is parked for the lead (agent, 2026-10-21). It needs files outside lane H:
  - The bench run needs a per-run extra declared in tests_hardware/device_scripts/bench_facts.pyi, which is not H's file.
  - The loop-lag host test is tests_hardware/flash/test_memory_stress.py:103-112, which no lane holds.
  - The script serves on 127.0.0.1:8080 with a scratch config, and silicon cannot reach that address. The serving scripts that work on the bench run main() on the production config instead (uart_link_echo_under_serving_load.py:106).
  - Proposed fix: add an extra that runs main() on the production config. Then a bench test in test_memory_stress_bench.py waits with wait_for_script_server, runs _load.readers at configured_max_connections() over get_routes(), and asserts that every route answered (the twin's _lag_load evidence, scripts/_digital_twin_scenarios.py:989-1013) plus the lag, main_running and FRAM checks.

Effect of each device-script edit:
- These are device scripts, not firmware. No device's shipped firmware changes in any mode (STA, AP, Silent, Off, USB).
- They run on the bench board (dev) under run_isolated. main() is not started, so no WiFi mode is involved. Facts still go out over USB as before.
- Sweep: on dev, the self-hazard runs on i2c0 against the lone BMP3xx, with 3 of 3 broadcasts NAKed. A bench whose lone device is an SGP40 would see 0 NAKs.
- SCD30 bound: reaches every script that reads through device_reader: the sweep and i2c_held_sda_recovery. On dev that is i2c1, during the recover() reads and the heater-off sibling read. A read before the SCD30's first data-ready has nothing to check.

Runs (twin on dev, all exits explained):
- r3/r4: sweep at -1 and 32768, PASS.
- r7/r8: held-SDA at -1 and 32768, rc=1. This is its known twin-only failure ("the bit-banged read left SDA high"), the same at both stages.
- Zero MemoryError and zero "memory allocation failed" in every output.
- pytest --collect-only tests_hardware: rc 0, 196 of 227 collected, 31 deselected by the wear gates.
- ruff clean. mypy clean on a cold cache in all four passes: main, device scripts (src tests tests_hardware/device_scripts), host and twin.

Commit checks and readers, 42 tests_scripts files: all green except test_twin_record.
- test_twin_record is red, as expected: the runner_sha256 and 17 changed scripts. The lead re-records at W6.
- test_decision_vocabulary was red once on my first owner-tag form. I fixed it to the "(owner, date" form and reran it, comment_block_cap and citations: all green.

Silent-failure scan of my 5 files:
- Class 4 and 3 at sweep :116-127 and bus_reader_loops :79-83 are fixed here.
- New, not fixed (class 4/1, bus modes): sweep _probe() :72-75 treats ETIMEDOUT the same as an absent device in the reserved-address sweep. A wedged bus still fails every device read, so this is partly covered. The owner is lane H.
- Nothing found in the other files.

Times: no unit-tier or twin-tier file changed, so there is nothing to compare with the base table.

H2's start state: audit/u35-h at 76b2d7f. H1's edits are final for test_end_to_end_timing.py, the sweep, bus_reader_loops, test_bus_concurrency.py and run_device_script.py. test_memory_stress_bench.py and loop_lag_under_combined_load.py are untouched until the lead rules on OF-226. H2 holds record_twin_instrument_runs.py, test_twin_record.py and twin_record.json (step 140 and OF-229). The 17 repo-wide scans are still owed at H's final.

Logs are in S/u35/laneH/: r1-r8 .log and _out.txt, collect.log, mypy_*.log, ts_*.log, ts2_*.log, seq3.rc, plus the drivers twin_call.py, edits1.py and plant_gc.py.