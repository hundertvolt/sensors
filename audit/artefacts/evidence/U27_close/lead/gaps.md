# U27 lane plan: gaps (sites at `0c0ad52`; packet `pk/U27_steps.md`; rulings `briefs/rulings.md`)

Every default below is conservative and reversible, decided on the owner's behalf for review at the close (agent,
2026-10-15). "R-n" is a ruling.

## 1. Changes placed only in part: the U27 stage of an entry whose unit is earlier or later

| step | change | unit slot | what U27 applies (lane) | what stays |
|---|---|---|---|---|
| 1, 77 | M.GEN.009, .019 | U20 / U27 | `TestOverrides` in the build info and `test_overrides` through `generate_device()` (B) | the rest landed U20 |
| 14 | M.SCR.073 | U28 | the shell convention only (T) | Xvfb, verified downloads (U28) |
| 31g | M.TEST_UNIT.111, .118, .220 | U18/U15/U24 | the `# ====` → `# ----` rule lines only (U) | their unit's content |
| 31g, 32, 190-195 | M.TSC.065, M.GEN.060, M.WEB.051-.059 | U27/U23/U24/U25/U32 | the gate and the headers (U) | the files' other content (landed) |
| 42 | M.TOOL.003 | U28 | listed in the cap gate's pending set (U) | ci.yml's header (U28) |
| 77 | M.SCR.064 | U28 | the smoke on the shared JS twin frame: probe, layout file, port-53 lock (S) | the rest (U28) |
| 77 | M.SCR.069 | U28 | docstring, idiom, the `coverage` ignore (B) | the pin and the renders (U28) |
| 77 | M.TOOL.011, .018 | U28 | ci.yml's two U27 stages: lint-and-typecheck's generation, ruff and mypy lines; firmware-build-verify's python check (B) | the uv-sync action, the matrices (U28) |
| 77 | M.TOOL.079, M.TWIN.075 | U34 / U27 | `ignore-without-code`, the conftest reason, `mypy_path` gains scripts; the twin pass's `files` (B) | the empty Any baseline's removal (U34) |
| 107 | M.SCR.057 | U35 | one attempt, the derived soak route set, a device-free comment (S) | offsets, calibration (U35) |
| 109-122, 138-140 | M.SPEC.* | staged | each entry's U27 stage (X) | other stages |
| 78-83, 85, 86, 88, 98, 111 | M.DOCS.*, M.HW_BENCH.126 | U36 | the U27 sentences (X) | U36's rewrites |
| 153, 154 | M.TSC.083, .084 | U28 / U35 | the derived routes, the one-attempt case (S) | the rest |
| 197, 198 | M.WEB.070, .073 | U36 / U28 | `tests_js/_micropypath.js` in the Node-context lists (S) | the restructures |
| 3, 43, 50, 135, 136 | M.HW_BENCH.010, M.TOOL.034, M.TSC.014, M.TOOL.030, .033 | U26/U27/U28/U34 | the lead's W1 lines (R-6, R-7) | U28's restructure |

## 2. Steps with nothing to write at U27 (verify only, R-10)

51 rows, each with its proof in the plan's §10 and the packets' index. The groups: the twin headers (M.TWIN.002, .010-.014,
.016, .017, .020, .031, .036, .040, .042, .044, .047, .057; they pass the gate without the length rule, R-4); the test-helper
headers (M.TEST_HELP.002-.004, .010: `tests/microtest.py:1`, `tests/_threshold_runner.py:1`, `tests/_coverage_runner.py:1`,
`tests/machine.py:1-3`); A.U27.01's landed halves (M.SCR.047's helpers, M.SCR.016's `class TwinRun:` at
`scripts/_twin_process.py:58`, `def log_memory_verdict(` `:209`, M.TSC.165's cases at
`tests_scripts/test_digital_twin_ci_suite_errcount.py:443`, `:595`, M.TWIN.050); the summary emitters (M.SCR.001/.002,
`tests_scripts/test_summary_block.py:360` `def test_no_emitter_writes_the_github_step_summary`); the record and verdict
(M.SCR.004 `"markexpr"` at `scripts/_pytest_run_record.py:115`, M.SCR.005, M.TSC.197); M.SCR.012 (`scripts/_port_lock.sh`,
U24), M.SCR.044, M.TSC.177, M.TSC.180 (`tests_scripts/test_board_image_fixture.py:106`), M.HW_BENCH.089
(`tests_hardware/bench/test_ticks_ms_rollover.py:47` `option = request.config.getoption("--rollover-image")`), .038, .106,
M.HW_DEV.001/.003/.116, M.TSC.002/.021/.045/.048/.016, M.GEN.016, M.TOOL.078/.080, M.SRC_CORE.071, M.SRC_SENS.062,
M.TEST_HELP.033, M.TWIN.136, M.WEB.060, .063.

## 3. Files no M entry's Site names that U27 must edit

- `tests_scripts/test_host_cli_exit_idiom.py` (B, new): A.U27.29's L0 ("each CLI run with a malformed input prints one
  line, no Traceback, exit 1") has no file; it also pins the idiom over the CLIs born after the A-L survey (R-11):
  `scripts/_archive_evidence.py:113`, `scripts/_stage_website.py:499`, `scripts/record_twin_instrument_runs.py:152`,
  `tests_hardware/kick_then_reset.py:24`, `tests_hardware/spoof_udp.py:63` (each `sys.exit(main())`).
- `tests_scripts/test_host_text_encoding.py` (M, new): OF-118's guard (R-13).
- `src/asy_scd30_driver.py:172-180` (U): a comment block of six prose lines between three tag lines (`# @requires
  bus.timeout>=200000`, `# @requires bus.frequency<=100000`, `# @wiring fram_target …`), exempt today by
  `tests_scripts/test_comment_block_cap.py:57` `if not any(tag in line …` and over the cap once only the tag lines leave
  the count: split with a bare `#`.
- `tests/test_asy_uart_comm.py`, `tests/test_asy_ntp_client.py`, `tests/test_asy_scd30_driver.py`,
  `tests/test_asy_wifi_service.py` (U): 22 `=` rule lines at `0c0ad52` (A.U27.30 counted 20 at the A-L HEAD).
- `scripts/_archive_evidence.py`, `scripts/record_twin_instrument_runs.py`, `tests_hardware/kick_then_reset.py`,
  `tests_hardware/spoof_udp.py` (T, S): the idiom only.
- `tests_scripts/test_manual_runner_summary.py` (T): OF-60's latency case and A.U27.37's fresh-interpreter `--list` case.
- `tests/test_digital_twin_machine.py`, `tests/test_digital_twin_run_generic_integration.py`,
  `tests_scripts/test_twin_runner_test_flags.py` (S): OF-157, OF-165, OF-166's cases.
- `tests_js/micropypath.test.js` (S, new): M.WEB.079's reader has no test file named.

## 4. Paths in the M texts that are gone, renamed or live elsewhere

`src/api_response.py` → `src/asy_api_response.py`; `tests/test_api_response.py` → `tests/test_asy_api_response.py`;
`src/system_service.py` → `src/asy_system_service.py`; `digital_twin/_unix_port_udp_addr_shim.py` →
`digital_twin/unixport/_unix_port_udp_addr_shim.py`; `tests/_webserver_concurrency_scenarios.py` and
`tests/test_digital_twin_real_website_integration.py` retired at U25 (their scenarios run in `scripts/_digital_twin_scenarios.py`);
`tests_hardware/isl29125_conformance.py` replaced at U26 by `tests_hardware/conformance.py`; bare names in the work order's
file list resolve to `tests_hardware/device_scripts/…` and `tests_scripts/…`. Not born in U27 (U28's): `scripts/uv_sync_retried.sh`,
`tsconfig.base.json`, `tests_scripts/test_ruff_exemptions_live.py`, `test_tool_pins.py`, `test_ci_workflow.py` (R-22).

## 5. Facts at `0c0ad52` that change a step's premise

- A.U27.01 landed at U25 (fail-closed log verdict, `TwinRun`); A.U27.38's twin-runner half landed too
  (`scripts/run_digital_twin_ci.sh:143` runs the harness at each stage); A.S0930.04's CRC16 rerun (`:126-135`) is in place.
  What U27 still owes: test.sh's harness jobs and the standalone harness's port lock.
- A.U27.37's import placement is done (`scripts/_digital_twin_ci_suite.py:34` `from buildgen.validate import
  device_max_connections, module_int_const`); only the by-name helper and two one-line callers remain (R-6).
- `scripts/test.sh` arms two EXIT traps (`:115` `trap port_lock_release_all EXIT`, `:410` `trap _cleanup EXIT`) and creates
  `tests_scripts_status_file` (`:344`) and `tests_scripts_inner_pidfile` (`:355`) before the second; the convention allows
  one trap, armed before any `mktemp` (M.SCR.038: `_cleanup` calls `port_lock_release_all`).
- The comment-cap length rule's premise moved: A.U27.28 measured 84 blocks in 80 files over at 110 characters on
  2026-09-30; at `0c0ad52` the same counting finds 675 blocks in 396 files (`tools/cap_new.py`; 99th percentile of comment
  line length 120). Owner question 1, R-4.
- OF-118's count moved: the row says 23 + 17 + 458 sites; the plan's AST count (open() text mode, `read_text`,
  `write_text`, `Path.open` text mode) finds 31 in `scripts/`, 31 in `toolchain/`, 673 in `tests_scripts/`, 94 files.
- U26's review `:116` ("Reverse: a streaming run API (U27's)") names no M entry or action: a reversal option, not written
  in U27 (rule 13); the lead may move it to the open findings for phase C.
- `tests_scripts/test_no_variant_literals.py:33-46` `_NOT_YET_CLEANED` lists `scripts/_digital_twin_ci_suite.py`,
  `scripts/build_firmware.py`, `scripts/test.sh`, `scripts/typecheck.sh`, `pyproject.toml`, `.github/workflows/ci.yml` and
  three twin test files; an entry whose file is clean fails the test, so the lead deletes the rows U27 cleans at W1 (R-8).
  ci.yml's row stays (U28).

## 6. Cross-lane contracts and expected reds (R-3, R-9)

- At `<API>`: `test_shell_conventions.py` red on every `scripts/*.sh` not yet in the convention (T's own, B's three website
  scripts and lint/typecheck, S's two twin runners); `test_twin_never_needs_tests_on_its_path.py` red on every twin launch
  site not reading `micropypath.toml` (`scripts/_twin_process.py:24`, `tests_hardware/twin_board.py:16`, the JS commands,
  the smoke, `scripts/run_unix_port_integration.sh`, `tests_scripts/test_digital_twin_generated_boot.py`);
  `test_require_python.py` red on `scripts/build_frozen_html.sh`. Each is that lane's seen-failing-first.
- B's `test_host_cli_exit_idiom.py` is red at B's hand-back on T's and S's `sys.exit(main())` sites until W1.
- B's `test_lint_type_scopes.py` (2) asserts CI's ruff and mypy lines equal `lint.sh`'s and `files`: B edits ci.yml's two
  U27 stages itself (R-18).
- T's test.sh harness jobs call `scripts/_digital_twin_scenarios.py` with the CLI at `0c0ad52` (`--device`,
  `--micropython-bin`, `--gc-threshold`, `--logs-dir`, `--run-record`, `--shared-port-53` the default,
  `--exclusive-port-53`); several jobs run at once, so test.sh's use the default (the DNS scenarios deselected and listed,
  M.TSC.136) while `scripts/run_digital_twin_ci.sh:143` keeps `--exclusive-port-53`; S keeps that CLI (additive only) and
  relays any new flag.
- U's cap gate checks every Python and shell file's header and blocks: a new file from T, B, S, M must carry a ≤ 3-line
  header (all new files planned do).
- Doc checks red until X: `test_citations.py` (renamed or new files the docs cite), `test_tunables_register.py` (new
  `@tunable` rows), `test_readme_reference.py` (`--help` texts against README).

## 7. Pending owner answers, defaults applied

Owner question 1 (R-4): the comment-cap length rule. Default: the gate lands without it. U26's pending answers (OF-122,
OF-127, OF-36, OF-180's question 5) touch no U27 file and keep their stated defaults.

## 8. Counts that differ from the brief

The brief's figures match the work order at `0c0ad52`: 246 steps, 58 actions, 216 files, 239 scoped tests, full gate 7,
4 hardware rounds. The 25 open findings are the rows whose target is U27; three more (OF-125, OF-141, OF-183) target
U28 or C and name a U27 part, placed in §6 of the plan.
