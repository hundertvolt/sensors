# U28 lane plan: gaps (sites at `b1fecfb`; packet `pk/U28_steps.md`; rulings `briefs/rulings.md`)

Every default below is conservative and reversible, decided on the owner's behalf for review at the close (agent,
2026-10-19). "R-n" is a ruling.

## 1. Changes placed only in part: U28's stage of an entry whose main unit is another

| step | change | unit slot | what U28 writes (lane) | what stays |
|---|---|---|---|---|
| 6, 8, 34, 101, 102, 106 | M.HW_BENCH.036, .071, M.TEST_HELP.010, M.TWIN.040, .044, .132 | U26/U24/U25/U35 | their `pyproject.toml` homes (R) | the files' content (landed) |
| 16, 29, 30, 32, 33, 36-39, 105, 108 | M.HW_DEV.140, M.SRC_NET.096, .130, M.TEST_HELP.003/.004, M.TEST_UNIT.058/.095/.113/.249, M.TWIN.122/.158 | U26/U28/U30/U24/U18/U11/U25/U36 | the inline `noqa` removals and E402 reasons (P) | their units' content |
| 20, 21, 25 | M.SCR.046, .068, .065 | U27 | a per-file home, six E402 reasons, OF-194 (R) | U27's content (landed) |
| 22 | M.SCR.069 | U28 | the XML removal, pathlib, docstring (C) | the pin landed U27 (`scripts/_render_coverage.py:4`) |
| 40 | M.TEST_UNIT.272 | U12 | the `_srgb_` rename (P) | the rest landed |
| 87, 91-93 | M.HW_DEV.048, M.SRC_NET.030, .081, .165 | U26/U28/U31/U30 | the reason and trigger comments (P) | their content |
| 104 | M.TWIN.102 | U36 | the cancelled-session twin case, REGISTER `:671`'s carry (P) | U30/U32/U35/U36's stages |
| 26, 28, 88, 89, 116, 141, 143-145 | M.SPEC.* | staged | each entry's U28 stage (X) | other stages |
| 1, 3, 23, 43, 46, 47, 78, 79, 114, 119, 120, 138, 139, 142 | M.DOCS.*, M.HW_BENCH.125 | U36/U34/U37 | the U28 sentences (X) | the later rewrites |
| 72, 76 | M.TOOL.018, .052 | U28/U21 | CI's picotool install (C); nothing in the installer (W verify) | U21's build |
| 113, 130 | M.SCR.063, .064 | U36/U28 | the engine flag; the shared frame, `-displayfd`, the Chromium fallback (W) | U36's reorder |
| 125 | M.TOOL.078 | U28 | the lead's `uv lock` after R's pins | U37's re-check |

## 2. Steps with nothing to write at U28 (verify only)

41 rows, each with its proof in plan §10 and the packets' indexes: the generated hotspot form (M.GEN.003/.005, M.TSC.047,
R-9); M.TOOL.031 (`pyproject.toml:202-204`); the device scripts U26 cleaned (M.HW_DEV.062-.064, .090, .107); M.HW_BENCH.038,
.100, .103, M.HW_DEV.112, M.SCR.070 (no `visit_*`), M.SCR.025 (lint.sh names the generated tree; R confirms ruff reads
it); M.SCR.009, .010, .036, .038, .061, .071, .072 (scripts unchanged); M.SRC_CORE.016, M.SRC_SENS.038, M.TEST_UNIT.037, .332,
M.TWIN.011, .025, .057, .144, .164 (no site left, or a citation the submodule keeps); M.TOOL.020 (U0's refreshed tags),
.046, .052; M.TSC.021, .027, .168, .175; M.WEB.072 (U0: `.nvmrc` 24, `package.json:7-9`), .077; M.SPEC.126 (U30's catalog).

## 3. Files no M entry's Site names that U28 edits

- The suppression sweep's files (P 64, R's noqa and E402 files): the 69 mis-ordered ignore lists (27 files), 79 E402s without the
  ` - reason` form and 103 non-E402 inline `noqa` of `b1fecfb` (P 70, R 33) (A.U28.28 counted 76 inline at the A-L HEAD, A.U28.30 66
  lists): tables `tools/supp_P.md`, `tools/supp_R.md`, in the packets.
- The host-fix files of R-4 (AST estimate `tools/ast_host_fix_files.txt`, the lead's L0 listing final) and the PT006/011/022
  files (`tests_scripts/test_buildgen_{defaults,driver_registry,graph,limits,pico_gpio,requires_tag,schema_ast,tag_comments,validate,value_wiring,web_tag,wiring}.py`,
  `test_config_schemas.py`, `test_coverage_runner.py`, `test_digital_twin_boot_contiguity.py`,
  `test_digital_twin_ci_suite_errcount.py`, `tests_hardware/conftest.py`).
- `scripts/test.sh`, `scripts/typecheck.sh`, `scripts/_unix_port.sh` and their tests (C): OF-204, OF-125, OF-191.
- `tests_scripts/test_lint_type_scopes.py` (C, OF-24), `test_hardware_runners.py`, `test_require_clean_hardware_run_sh.py`,
  `test_mpremote_connect_sh.py`, `test_manual_runner_summary.py`, `test_tool_help.py` (C, the runners' first call),
  `test_render_coverage_anchors.py` (C, pathlib).
- `tests_scripts/test_html_validate_config.py` (W, new, OF-140), `.htmlvalidate.json` (W), `tests_js/_twin_process.js` (W, if
  the smoke needs an export), `toolchain/setup_toolchain.py` and `tests_scripts/test_setup_toolchain_env.py` (W, A.U28.20).
- `tests_scripts/test_device_script_config_schemas.py`, `test_stored_config_golden.py` (R, OF-28), `tests_scripts/conftest.py`
  and `test_build_firmware.py` (R, OF-194/195).
- `tests/test_asy_uart_comm.py` (P, OF-159's case), `tests/test_digital_twin_bus_hazard_concurrency.py` (P, the carry).

## 4. Paths in the M texts that are gone, renamed or live elsewhere

`src/system_service.py` → `src/asy_system_service.py`; `tests/test_config_manager.py` → `tests/test_asy_config_manager.py`;
`tests_hardware/isl29125_conformance.py` → `tests_hardware/conformance.py` (U26);
`tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py` and `wifi_service_reconnect_repro.py` deleted
(U26); `datasheets` is a directory of 21 PDFs until A.U28.35's move; new at U28: `.github/actions/uv-sync/action.yml`,
`scripts/uv_sync_retried.sh`, `scripts/preview_server.py`, `tsconfig.base.json`, `tests_scripts/test_{ci_workflow,
uv_sync_retried_sh,tool_pins,ruff_exemptions_live,suppression_form,config_paths_resolve,preview_server,html_validate_config}.py`,
`.gitmodules`; `tests_js/vitest-commands.ts` only if the skipLibCheck trial needs it.

## 5. Facts at `b1fecfb` that change a step's premise

- dorny is already a commit pin (`ci.yml:36` `uses: dorny/paths-filter@ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d # v4.0.3`, U0's
  refresh); A.U28.13's remaining part: confirm it is the peeled commit and the newest v4 tag (R-22).
- Node is already 24 on all three sites (`.nvmrc` `24`; `package.json:7-9` engines `>=24 <25`; `:39` `@types/node` `^24.19.1`):
  A.U28.23's code part landed at U0; only `test_tool_pins.py`'s Node case is U28's.
- `digital-twin-e2e` already runs device x GC stage x part (`ci.yml:628-633`, 24 jobs; CI run 38777834467 45/45): R-8.
- CI's mypy paths already equal pyproject's `files` (`ci.yml:362`, `pyproject.toml:360`): OF-24 reduces to calling
  `typecheck.sh` with no arguments (R-13).
- The generated code passes the hotspot default positionally (`buildgen/codegen.py:506`): R-9.
- Host lint premise moved: PT018 418 sites in 115 files (A.U28.27: 31), host-test EM101/EM102 ~170 sites (none planned):
  R-5, owner question 1. Inline `noqa`: 304 (200 E402) where A.U28.28 counted 76 (39 E402).
- `src/` holds 25 `type: ignore`; the ones with no reason on the line or above are 7 (`src/asy_scd30_driver.py:276`,
  `:295`, `:298`; `src/asy_uart_comm.py:411`, `:632`, `:634`, `:635`) - A.U28.30's `asy_notification_service.py`/
  `system_service.py` sites are gone.
- The coverage pin landed at U27 (`scripts/_render_coverage.py:4`) with `tests_scripts/test_script_metadata_pins.py`.
- `scripts/test.sh` already renders four reports (`:902-909`) and archives the two XML names (`:181`).
- The hardware runners call `uv run --no-sync` with no sync before (`scripts/mpremote_connect.sh:21`,
  `scripts/run_manual_hardware_tests.sh:22`, `scripts/_require_clean_hardware_run.sh:67`, `scripts/run_bench_rollover_test.sh:33`).
- The four web jobs carry a `setcap` in their build-if-missing block (`ci.yml:136-137`): the action's build step keeps it.
- `digital_twin/_http_client.py:101-103` states why there is no `from e` (B904 per file, R-6).
- M.TWIN.104's `test_a_sensor_task_cancelled_inside_its_session_leaves_the_bus_usable` exists only in the mock tier
  (`tests/test_bus_hazard_multi_device.py:1032`); the twin file has none (REGISTER `:671`'s carry).

## 6. Cross-lane contracts and expected reds

- At `<API>` (R1): ruff RUF100 red on every inline `noqa` of P's files that now has a central home, and on R's files R has not
  yet changed (R lists both); `test_suppression_form.py` red on P's files (lists, E402 reasons, `src/` reasons);
  `test_ruff_exemptions_live.py` red on entries P's inline comments still shadow. Each P line is P's seen-failing-first.
- C and W, on `b1fecfb`, see R1's narrowed list only through the L0 listing: their own files' findings are in their briefs;
  at `<W1>` ruff runs with R's pyproject over every file.
- C's headers on ci.yml and the action, W's on `eslint.config.js` and `vitest.config.js` turn `test_comment_block_cap.py`'s
  gained-row assertion red until the lead deletes the rows (R-10).
- C's ci.yml edits turn `test_test_sh.py:1687` (report count) and `test_js_coverage_report_dir.py:46-47` (substrings) -
  both C's to keep green; `test_lint_type_scopes.py` (C).
- R's pins make `test_tool_pins.py` red until the lead's `uv lock` (R-11); `uv sync --locked` refuses the un-relocked tree, so
  every lane runs on its worktree's existing venv and never syncs.
- C's uv-sync action reads `[tool.uv] required-version`, which R writes: the action is proven only on `<W1>` (and by CI);
  `test_tool_pins.py` (R) pins that no `.github/**` file carries a second uv version.
- W's `--require-all-engines` and C's ci.yml line `node scripts/cross_browser_smoke.mjs --require-all-engines` land together
  at `<W1>`; W's `setup_cross_browser_toolchain.sh` path is the Firefox key's hash input (C).
- New tags (C: `ci.devices_timeout_min`, `runner.unix_port_probe_timeout_s`, the moved `tool.uv_sync_*`, the Playwright step
  timeouts; W: the installer's; P: none) make `test_tunables_register.py` red until X writes Part N rows (relay).
- Doc checks red until X: `test_citations.py` (new files the docs name), `test_tunables_register.py`.

## 7. Pending owner answers, defaults applied

Owner question 1 (R-5): host test suites' PT018 and EM/TRY003. Default: exempt with a reason. OF-36 (pending since U11) keeps
its default and moves on. BACKLOG.md owner question 6 (U27's comment-cap length rule) keeps its default (no length rule).

## 8. Counts that differ from the brief

The brief's figures match the work order at `b1fecfb`: 156 steps (in 147 numbered steps: 145 single, one group of 7, one of 4),
56 actions, 113 files, 200 scoped tests, full gate 7, hardware rounds R0 [H57], R1 [H73], R3 [H73]; 23 open findings
target U28 (OF-70, OF-183, OF-184 name a U28 part with target C).
