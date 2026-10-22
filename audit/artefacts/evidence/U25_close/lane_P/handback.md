WIP 491d91a (branch audit/u25-p, worktree S/wt-u25p, based on 8e7dedc). P1 is done and I have stopped here to wait for <API>/<W1>.
Steps
- A-5 `pins` applied: `buildgen/twin_wiring.py` now builds `pins: dict[str, I2CPins|SpiPins|UartPins]` from the `[bus.*]` tables, using validate's `_BUS_WIRE_FIELDS`/`_VALID_BUS_IDS`. Tested in `test_buildgen_twin_wiring.py` (values per TOML) and in `test_twin_wiring_contract.py` (role sets per kind, plus scanning reads of the pin union). Generated tree rebuilt (rebuild.sh rc 0).
- `tests/_twin_devices.py` is new: `generated_devices`, `wiring_plan`, `device_with(*drivers)`, `devices_with_shared_bus`. It restates the plan TypedDicts for mypy (explicit `Any` is not allowed and tests/ cannot import buildgen); the contract test checks they match buildgen's text.
- `tests/_port_bands.py` is new: `BANDS`, `PER_DEVICE_OWNERS`, `PortAllocator(owner, device=None)` with `.next()`/`.taken(port)`, and `band_for_device`. L0 tests are in the new `tests_scripts/test_port_bands.py`.
- `load_device(device)` added to `_digital_twin_construction_scenarios.py`; `_boot_device` now goes through it.
- `scripts/test.sh` gets `_job_tag`. `run_test_file <file> <status> [<device>] [<binary>]` runs with `exec env -u TEST_DEVICE ${device:+TEST_DEVICE=…}` inside the unchanged interrupt-once wrapper (the delivery-count test is still green). It expands any file with a whole line `PER_DEVICE = True` into one job per device, tagged `<file>[<device>]`. The summary tail reads tags with brackets as plain text (awk index, quoted `=~`).
Deviations (all reversible)
- The device set in test.sh comes from the stems of the generated wiring plans, not from `devices/*.toml`. That keeps test.sh's own rule that nothing re-globs `devices/` after generation, and it is the same set `generated_devices()` returns.
- `load_device` does only the import and the check that the device was generated. The C4 boot (reset_peripherals, reset_interfaces) waits for the MN/N APIs.
- Band rows follow the owner names the consumer packets use (`dtsi`, `asy_udp_socket`, `asy_wifi_service`). I also reserved rows that other lanes will bind: `_digital_twin_scenarios` 20000-20999, `_webserver_concurrency_scenarios` 19700-19999, `test_digital_twin_ntp` and `test_digital_twin_clock_jump` (UDP 29000-29999). The `test_digital_twin_http_client` band is widened to 18090-18119.
- From the scan: test.sh now stops if it cannot read a file's `PER_DEVICE` marker, the same way the memory gate does.
- `/usr/bin/time` does not exist on this host, so timings use bash `time` (TIMEFORMAT=%R).
Seen failing first (logs in S/u25/laneP/)
- `test_buildgen_twin_wiring.py:153 KeyError: 'pins'`; contract `:245 KeyError: 'pins'`; the planted read gave `[(2,'pins'),(3,'pins')] != [(3,'clk')]`.
- Missing modules: `FileNotFoundError …/tests/_twin_devices.py` and `_port_bands.py`.
- MicroPython: `NameError: name 'load_device' isn't defined`.
- test.sh: first "no longer defines _job_tag()"; then behaviour: `'tests/test_a.py[/std] unset' != 'tests/test_a.py /std'`, the PER_DEVICE file ran once, the empty tree and the unreadable marker each gave "DID NOT RAISE", the plain job leaked `TEST_DEVICE=fixture-device-a`, and the device job came out FAIL.
Checks green
- pytest: test_buildgen_twin_wiring, test_twin_wiring_contract, test_port_bands, test_test_sh (138), test_generate_sensortask_modules and test_buildgen_generate (353), and the 12 convention checks.
- The six construction wrappers at -1 and 32768: 4/4 each, zero memory errors. dev's wrapper took 3.43 s / 4.14 s against the base 3.49 s / 4.37 s.
- ruff and shellcheck clean. The four mypy passes (main pass with no args and with `src tests tests_hardware/device_scripts`, twin, host) were clean and cold; the typings symlink is removed.
Red checks / waits
- None at P1.
- Coming next: removing the wrappers and `_DEVICES` (steps 69/100) will turn `tests_scripts/test_device_tomls.py:156-178` red. That file is SH's, not mine; it globs `test_<family>_<device>.py` and regexes `^_DEVICES = (`. The lead or SH needs to decide that edit.
- `test_port_bands`' binder scan (step 86) will stay red until each lane migrates its binders.
Scan
- Class 4: test.sh treated a marker grep returning ≥2 as "no marker". Found and fixed in this WIP, `scripts/test.sh` at the job_list loop. Nothing else found.
Facts owed to D
- SPEC L.4: the plan gains `pins`.
- SPEC E.1: the port paragraph should point to `tests/_port_bands.py` (rows as listed there).
- SPEC E.2.1: `tests/_twin_devices.py` and `load_device()`.
- E.3.1 / README: the PER_DEVICE/TEST_DEVICE jobs and the `<file>[<device>]` tags.
- No new @tunable.
Facts owed to the lead
- No allow-list, Any-baseline or typecheck.ini line retired.
After-times beyond 10 %: none.
Runs: mypy ×4 and the convention batch are logged in RUNS.md, both rc=0. Nothing of mine is running.

---

Final commit bd51782 on audit/u25-p (P1 491d91a, then the merge of audit/u25-api1 e34ffd6 as 3d50a5a). All my MicroPython files are green at -1 and 32768 with zero memory-error lines (44 runs). Six checks are red, each waiting on another lane, D or you (listed below).
Steps
- Applied:
  - 32/100: the construction library boots each device on a fresh board (reset_peripherals, reset_interfaces, configure_wiring(wiring_plan), load_device). Its devices, port band and expected names come from the generated plan and expected facts. This fixes your 2/4 reds.
  - 54: two new scenarios, `boot_sequence_matches_the_generated_expectation` and `irq_pins_are_shared_by_chip_fake_and_driver`.
  - 69/100: `tests/test_sensortask.py` and `tests/test_digital_twin_construction.py` replace the twelve wrappers (deleted).
  - 32: the heavy-file list is re-ordered by base_times; `_check_heavy_list` stops the run (exit 2) on a missing file.
  - 41: the generator gains `--device-toml PATH --out-dir DIR`; orphan removal and stamps are unchanged.
  - 64-68: the six UDP files use `PortAllocator`.
  - 86: the L0 now scans every binding test file and checks each fixed row's constant.
  - A-17: the L0 checks both board probes' constants are equal.
  - Your point 8: `test_device_tomls.py` now accepts a family as either one PER_DEVICE file with no wrappers left, or one wrapper per device.
  - 11: the no-plan RuntimeError test.
- Partly: 39 and 75 (the per-device tags and dispatch L0s here; the harness/scenarios job parts are U27's); 41 (the in-memory all-or-nothing default mode is U27's).
- Already landed, verified: 2, 3, 4 (`codegen.py:825-832`, the start line names only `watchdog=` and one comment names the other four keywords), 10, 12, 17, 62, and 81 (`_devices.py:28`; `bench_device` is U26's).
Deviations
- `expected_entries()` moved from `_sensortask_scenarios` into `_boot_recorder.py`, so both tiers share it.
- The prewarm and UDP shim moved out of the construction library into its entry file (M.TWIN.108 over the conflicting M.TEST_HELP.029).
- The L1 library draws its two never-bound override ports from a new row, `_sensortask_scenarios` 17500-17509, because the scan flags `port=` literals.
- The generated fixture TOML is named `fixture_device`: a hyphen does not compile as a module name.
Seen failing first (logs in S/u25/laneP/)
- The new entry files were missing at first.
- The unguarded entry raised AssertionError instead of RuntimeError.
- `test_device_tomls`: "covers [] … no longer declares a _DEVICES tuple".
- Heavy list: it named the six removed files, and a missing file did not stop the run.
- Single-device mode: `main() takes 0 positional arguments`.
- Planted bites that failed as they should: a setup reorder (boot-sequence scenario), SCD30 IRQ pin 8→9 (IRQ scenario), a marker-less entry (coverage check), probe constants 3/4 plus a stray `_HIGH_BAND`, and a default plan (no-plan test).
Red checks
- `test_port_bands::…draws_it_from_its_band`: `test_digital_twin_sensortask_integration.py` (G2) and `_webserver_concurrency_scenarios.py` (SH).
- `test_citations`: SPECIFICATION.md still cites `tests/test_sensortask_dev.py` → D.
- Allow-list lines my change retires → you:
  - `test_no_variant_literals.py:48-53, 67-72`;
  - decision allow-list: five "Below the OS ephemeral range…" entries and the `test_device_tomls.py` `_DEVICES` entry;
  - citations allow-list: the construction library's `WP1`×2 and `decision 10`;
  - import-placement `_PENDING` entry `('tests/_digital_twin_construction_scenarios.py', '_scenario_bus_fault_degrades.scenario', 'errno')`.
- Not caused by me, already on the API tree:
  - `test_tunables_register`: R's and MN's tags have no Part N rows.
  - Twin mypy pass: 47 errors (`configure_i2c_wiring` and others) in G1, G2, R and MN files.
Silent-failure scan: nothing new in this commit (P1's unreadable-marker case is fixed).
Facts owed to D
- SPEC E.2.1 / E.3.1 and README: TEST_DEVICE recipe; the tag form `[test_sensortask[dev]]` (README:183); `pyproject.toml:387`'s comment about six files.
- SPEC E.1: the band rows, including 17500-17509.
- Generator usage: the new `--device-toml/--out-dir` mode.
- Fidelity table: the two new scenario names; `digital_twin/README.md:36-41` should name the IRQ guard.
- No new @tunable.
Two HTTP scenarios moved to SH, quoted from the 8e7dedc text:
- `_scenario_measurements_and_sensors_shape`: GET /measurements and GET /sensors on the twin each return 200, and `assert_sensor_payload_not_self_wrapped(json, expected)`, where expected is the upper-cased present SCD30/SGP40/BMP3XX/ISL29125.
- `_scenario_bus_fault_degrades`: SGP40 `writeto` gets `OSError(EIO)` with times=5 on its plan bus; GET /measurements returns 200 (never 500) and its body contains "SGP40".
After-times: none beyond 10 %. Construction per device: 1.9-3.6 s against 3.2-4.4 s before. sensortask per device: ≤ +1.7 % (wozi 61.0 s against 60.0 s).
Runs: batch pid 9251 rc=0 (44 runs); mypy ×4, two pytest batches and the contiguity file (34 passed after a rebuild) are logged in RUNS.md. The first contiguity run failed only because my generator comment edit made the tree stale; the rebuild fixed it. Nothing of mine is running.
