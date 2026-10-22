# U28 close: the plan's 41 verify rows (research, agent, 2026-10-19)

Each row of `S/u28/lane_plan.md` §10 whose verdict is `verify` (C 10, R 12, P 14, W 4, X 1), its named proof run against
`b4b7557` through git only (`git grep`, `git show`, `git ls-tree`, `git diff --quiet b1fecfb b4b7557`). A proof that is a
test or lint result is marked "proved by the gate/tier" with its file, for the lead; its static half was still read here.
Commands and their raw output: `verify_rows_checks.sh`, `verify_rows_out.txt` beside this file.

Result: 41 rows; 32 hold on their static proof, 9 hold on their static half with the test or lint half proved by the
gate/tier (2g GEN.003, GEN.005, TOOL.031, TSC.047; 45, 75, 95, 110, 147); 0 fail. One gap noted (TOOL.031).

| step | M ID | lane | the check run | result at b4b7557 |
|---|---|---|---|---|
| 2g | GEN.003 | R | `git show b4b7557:buildgen/codegen.py`, `git grep _HOTSPOT_PW_DEFAULT`, pyproject's generated entry | holds: `buildgen/codegen.py:506` `wifi = f"WifiConfig({_lit(device_table['hostname'])}, {_lit(device_table['hotspot_password'])}, ...`; `_HOTSPOT_PW_DEFAULT` nowhere (rc 1); `pyproject.toml:190` `"build/generated_src/**" = ["PLW0603", "S104"]` (no S105/S106), `:344` "S105/S106 stay on everywhere else"; the ruff run itself: proved by the gate (lint leg, `scripts/lint.sh:49`) |
| 2g | GEN.005 | R | as GEN.003 | holds, as GEN.003 (no `hotspot_password=_HOTSPOT_PW_DEFAULT` anywhere); ruff: proved by the gate |
| 2g | TOOL.031 | R | `git show b4b7557:pyproject.toml`; `git grep` the table in `tests_scripts/test_ruff_exemptions_live.py` | holds: `pyproject.toml:157-159` `[tool.ruff.lint.pyflakes]` / "Imported for their side effect" / `allowed-unused-imports = ["frozen_html", "manual_bus_electrical", "manual_persistence", "manual_sensor_accuracy", "manual_toolchain", "manual_wifi"]`; GAP: the test never reads this table (it reads `ignore`, `per-file-ignores` and `allowed-confusables`, `:34-38`, `:122`; `_POLICY` `:25-27` holds only D106), so "listed with its reason" holds in pyproject's comment, not in the test; test result: proved by the tier (`tests_scripts/test_ruff_exemptions_live.py`) |
| 2g | TSC.047 | R | `git grep -i hotspot tests_scripts/test_buildgen_generate.py` | holds: `tests_scripts/test_buildgen_generate.py:1307` `assert f"WifiConfig({_lit(stated['hostname'])}, {_lit(stated['hotspot_password'])}, " in result.module_source`; file green: proved by the tier (`tests_scripts/test_buildgen_generate.py`) |
| 7 | HW_BENCH.038 | R | `git grep '# noqa' b4b7557 -- tests_hardware/conformance.py`; `git ls-tree b4b7557 tests_hardware/isl29125_conformance.py` | holds: no noqa (rc 1; file present, 83 lines); `isl29125_conformance.py` absent |
| 9 | HW_BENCH.100 | R | `git grep '# noqa' b4b7557 -- tests_hardware/manual/runner.py` | holds: none (rc 1; file 172 lines); the manual modules named at `pyproject.toml:159` |
| 10 | HW_DEV.062 | P | `git grep noqa b4b7557 -- tests_hardware/device_scripts/fram_error_log_roundtrip.py` | holds: none (rc 1); file present, unchanged in U28 |
| 11 | HW_DEV.063 | P | `git grep noqa ... fram_error_log_reset_race_seed_and_race.py` | holds: none (rc 1); file present, unchanged |
| 12 | HW_DEV.064 | P | `git grep noqa ... fram_error_log_reset_race_verify.py` | holds: none (rc 1); file present, unchanged |
| 13 | HW_DEV.090 | P | `git grep 'lambda\|noqa' ... bus_topology_autodetect_and_hazard_sweep.py` | holds: none (rc 1); file 187 lines, unchanged |
| 14 | HW_DEV.107 | P | `git show ...timer_alarm_pool_exhaustion.py \| grep 'for _ in range(64):\|fact("constructed", len(timers))\|noqa'` | holds: `:20` `for _ in range(64):  # an upper bound only`, `:27` `fact("constructed", len(timers))`; no noqa |
| 15 | HW_DEV.112 | R | `git ls-tree -r b4b7557 -- tests_hardware \| grep repro`; `git grep` both names in `pyproject.toml` | holds: `wifi_reconnect_after_failed_attempts_repro.py`, `wifi_service_reconnect_repro.py` absent (rc 1); no pyproject entry (rc 1) |
| 18 | HW_BENCH.103 | R | `git grep datasheets/ ...manual_sensor_accuracy.py`; `git diff --quiet b1fecfb b4b7557 -- ...` | holds: file unchanged (rc 0); its citations, e.g. `:14` `datasheets/bmp3xx/bst-bmp384-ds003.pdf`, `:19` `datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf`, existed at `b1fecfb`; `datasheets` is now submodule commit `15f4b93` (`.gitmodules`), whose tree is not fetched here (the lead's blob check covers it) |
| 19 | SCR.009 | C | `git diff --quiet b1fecfb b4b7557 -- scripts/micropypath.toml` | holds: unchanged (rc 0) |
| 24 | SCR.070 | R | `git grep 'def visit_' b4b7557 -- scripts/_strip_type_checking.py` | holds: none (rc 1; file 135 lines) |
| 27 | SPEC.126 | X | none named ("-"); read: `git diff -U0 b1fecfb b4b7557 -- SPECIFICATION.md` hunks against I.2's span | holds: nothing written (X's hand-back); no hunk inside I.2 (`SPECIFICATION.md:7951-7998`, "## I.2 Hotspot catalog"), the catalog is U30's |
| 31 | SRC_SENS.038 | P | `git grep datasheets/ src/asy_bmp3xx_driver.py`; `git diff --quiet` | holds: unchanged (rc 0); `src/asy_bmp3xx_driver.py:7` "... BST-MPS-AN006 (datasheets/bmp3xx/); one register map" |
| 35 | TEST_UNIT.037 | P | `git grep noqa b4b7557 -- tests/test_asy_fram_driver.py` | holds: none (rc 1) |
| 41 | TEST_UNIT.332 | P | `git show ...:tests/test_website_build_integration.py \| sed -n 13p`; `git grep noqa` | holds: `:13` `import frozen_html  # mounts /html on import`; no noqa (rc 1) |
| 45 | TOOL.020 | C | `git show ...ci.yml \| grep -o 'uses: [^ ]*'`; `grep submodules` | holds: `actions/checkout@v7` x16, `actions/cache@v6` x5, `actions/setup-node@v7` x8, `actions/upload-artifact@v7` x6, `dorny/paths-filter@ceb8a2b8...` (SHA), local `uses: ./.github/actions/...` x14; no `submodules:` key (rc 1); rules (3), (4): proved by the tier (`tests_scripts/test_ci_workflow.py`) |
| 60 | SCR.025 | R | `git show ...:scripts/lint.sh`; ci.yml's ruff line; lane R's planted run | holds: `scripts/lint.sh:49` `ruff check src tests ... tests_scripts build/generated_src`, `.github/workflows/ci.yml:431` the same; no `--no-respect-gitignore` needed: the planted file was reported (`build/generated_src/zz_scratch_probe.py:241:8: F401`, lane R's `scr025_planted.txt`) |
| 63 | SCR.010 | C | `git diff --quiet b1fecfb b4b7557 -- scripts/_require_python.sh` | holds: unchanged (rc 0); `.github/actions/uv-sync/action.yml:14` `source scripts/_require_python.sh && require_python311` |
| 65 | SCR.036 | C | `git diff b1fecfb b4b7557 -- scripts/test.sh \| grep '^[-+]' \| grep -i 'unix_port\|probe\|flavour'` | holds: no changed line (rc 1); the hunks are `:178`, `:851`, `:874`, `:899` (archive list, summary helper, renders); probe at `scripts/test.sh:109`, `:194` unchanged |
| 66 | SCR.072 | C | `git diff --quiet ... -- scripts/build_frozen_html.sh` | holds: unchanged (rc 0) |
| 67 | SCR.071 | C | `git diff --quiet ... -- scripts/build_website.sh` | holds: unchanged (rc 0) |
| 75 | TOOL.046 | W | `git show ...:toolchain/setup_toolchain.py \| grep '^NETWORK_ATTEMPTS\|backoff_s: float ='` | holds: `toolchain/setup_toolchain.py:104` `NETWORK_ATTEMPTS = 3  # mirrors scripts/uv_sync_retried.sh`, `:1609` `backoff_s: float = 10.0`; `scripts/uv_sync_retried.sh:19-22` `attempts=3`, `step=10`; equality: proved by the tier (`tests_scripts/test_uv_sync_retried_sh.py`) |
| 76 | TOOL.052 | W | none named ("-"); read: picotool lines of ci.yml and of the installer's U28 diff | holds: CI installs from the cached build tree, `.github/workflows/ci.yml:710-713` "Install the cached picotool" / `sudo make -C "$HOME/pico-toolchain/picotool/build" install`; no picotool line in `toolchain/setup_toolchain.py`'s U28 diff (rc 1) |
| 81 | TSC.021 | R | `git grep noqa b4b7557 -- tests_scripts/test_bench_harness_helpers.py` | holds: none (rc 1); unchanged |
| 82 | TSC.027 | R | `git grep noqa ... tests_scripts/test_bench_no_task_ended_completeness.py` | holds: none (rc 1); unchanged |
| 90 | SRC_CORE.016 | P | `git grep 'type: ignore' b4b7557 -- src/asy_system_service.py` | holds: none (rc 1); file unchanged |
| 95 | TSC.168 | C | `git show ...:tests_scripts/test_js_coverage_report_dir.py`; grep ci.yml for its two substrings | holds: the test asserts `hashFiles('{name}/index.html')` and `path: {name}/` (`:46-47`); `vitest.config.js:47` `reportsDirectory: "htmlcov_js"`, `.github/workflows/ci.yml:338` `hashFiles('htmlcov_js/index.html')`, `:342` `path: htmlcov_js/`; file green: proved by the tier (`tests_scripts/test_js_coverage_report_dir.py`) |
| 96 | TSC.175 | C | `git grep 'def bench_device(\|def devices_with(' b4b7557 -- tests_scripts/_devices.py` | holds: `:25` `def bench_device(devices_dir: Path = DEVICES_DIR) -> str:`, `:42` `def devices_with(driver: str) -> "list[str]":` |
| 99 | TWIN.011 | P | none named ("-"); read: `git diff --quiet ... -- digital_twin/_fram_chip.py` | holds: unchanged (rc 0); its citations name the datasheets, not a path (`:146` "MB85RS64V datasheet p10", `:264` "both FRAM datasheets, p10") |
| 100 | TWIN.025 | P | none named ("-"); read: datasheet lines of `digital_twin/machine.py` and of its U28 diff | holds: `digital_twin/machine.py:603` `datasheets/fram/MB85RS64V-DS501-00015-4v0-E.pdf p.10`, `:604` `datasheets/fram/MB85RS2MTA-DS501-00032-3v0-E.pdf p.10`; no diff line touches them (0); both paths existed at `b1fecfb` |
| 103 | TWIN.057 | P | `git grep noqa b4b7557 -- digital_twin/unix_port_poll_prewarm.py` | holds: none (rc 1); unchanged |
| 107 | TWIN.144 | P | `git grep 'noqa: E402' ... tests/test_digital_twin_sensortask_integration.py`, filtered for a missing ` - ` reason | holds: 22 E402 lines `:27-49`, each `# noqa: E402 - imported after the prewarm and the UDP shim (C4 order)`; none without a reason (rc 1); OF-47/149/187/188 to U35 (R-14) |
| 109 | TWIN.164 | P | `git ls-tree -r b4b7557 -- tests \| grep 'webserver_concurrency\|_webserver_concurrency_scenarios'` | holds: absent (rc 1; only archived logs under `audit/artefacts/` carry the name) |
| 110 | WEB.072 | W | `git show b4b7557:.nvmrc`; `package.json` engines and `@types/node` | holds: `.nvmrc` `24`; `package.json:7-8` `"engines": {` / `"node": ">=24 <25"`, `:39` `"@types/node": "^24.19.1"`; Node case: proved by the tier (`tests_scripts/test_tool_pins.py`) |
| 122 | SCR.038 | C | none named ("-"); read: U28's diff of the run record and the tier's conftest | holds: `tests_scripts/conftest.py` unchanged; `scripts/_pytest_run_record.py` changed only by lane R's host fixes (`os.replace` to `tmp.replace(path)`, the PLR2004 noqa to `_SKIP_LONGREPR_LEN = 3`), nothing of M.SCR.038 |
| 140 | SCR.061 | C | `git diff --quiet ... -- scripts/run_digital_twin_ci.sh` | holds: unchanged (rc 0); `.github/workflows/ci.yml:657` `run: scripts/run_digital_twin_ci.sh "$DEVICE" --gc-threshold "$TWIN_GC_THRESHOLD" --part "$TWIN_PART"` |
| 147 | WEB.077 | W | `git show b4b7557:tsconfig.node.json \| grep _summary_reporter` | holds: `tsconfig.node.json:10` `"include": [..., "tests_js/_summary_reporter.js", ...]` (`:30` at `b1fecfb`, moved by the base split); `npm run typecheck`: proved by the gate (web leg) |

Gap (agent, 2026-10-19): step 2g TOOL.031's proof expects `test_ruff_exemptions_live.py` to list the pyflakes table "with
its reason"; the test never reads `[tool.ruff.lint.pyflakes]`, so the table is unjudged by any check (it is live: steps 9
and 41 rely on it). Not a failure of the row's end state, which holds.
