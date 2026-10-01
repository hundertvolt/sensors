# A-C merge TSC (HEAD 39d93f6)

Cluster `tests_scripts/` (CLUSTERS.md "## TSC", 113 listed paths). The site index misses many `tests_scripts/` sites
(existing files no Site names, and ~50 new files other actions create); this merge carries the whole directory: the
listed files first (CLUSTERS.md order), then the unlisted existing files, then the new files. M_GEN calls this
cluster "TST". End states of the finished merges are cited by M-ID; SCR is not finished (no `M_SCR.md` at writing):
where a test pins an SCR product, the constituent action is cited and the dependency named.

## Cluster-wide changes (each lands file by file; the per-file sections below cite them)

### M.TSC.001 Follow the module renames in every path and import
- **From**: A.U10.37 (renames); SRC_CORE GAP-G10 (`crc_checks.py` → `asy_crc_checks.py`, class `CRCPass`); SRC_CORE
  GAP-G8 (`report_if_fatal()`/`fatal_reported` import from `asy_print_log`); A.U30.19 (fatal-report site check).
- **Site**: every `tests_scripts/` string or import naming an old module: `test_build_firmware.py` (`config_manager.py`
  ×3), `test_buildgen_definitions.py` (`system_service.py` ×4), `test_buildgen_frozen_modules.py` (`api_response`,
  `base_classes`, `captive_dns`, `config_manager`, `crc_checks` ×4, `print_log`, `system_service`),
  `test_buildgen_validate.py`, `test_buildgen_web_tag.py` ×3, `test_buildgen_wiring.py` ×2,
  `test_device_script_config_flush.py` ×2, `test_digital_twin_ci_suite_errcount.py`, `test_gc_collect_sites.py`,
  `test_lint_sh.py` ×3, `test_persistence_write_marker_completeness.py`, `test_fatal_report_sites.py`,
  `test_fram_chunk_crc_sites.py`, `test_watchdog_feed_sites.py`, `test_lock_order.py`, `test_readiness_gates.py`,
  `test_counter_steps.py`, `test_memory_catalog.py` (whatever path tables they hold at landing).
- **Change**: `system_service.py`→`asy_system_service.py`, `base_classes.py`→`asy_base_classes.py`,
  `config_manager.py`→`asy_config_manager.py`, `print_log.py`→`asy_print_log.py`, `api_response.py`→
  `asy_api_response.py`, `crc_checks.py`→`asy_crc_checks.py` (its pass-through class read as `CRCPass`),
  `framing_codecs.py`→`asy_framing_codecs.py`, `captive_dns.py`→`asy_captive_dns.py`; `math_helpers.py`,
  `voc_algorithm.py` and `asy_fram_*` keep their names. Any test importing `report_if_fatal`/`fatal_reported` imports
  them from `asy_print_log`. A test written after U10 uses the new names from the start.
- **Resolved**: —
- **Unit**: U10 (same commit as the rename); a test created later carries the new names in its own unit.
- **Depends**: A.U10.37 (SRC_CORE merge of the renames).
- **Blast carried by**: product side → M.SRC_CORE (rename); docs → A.U10.37 (SPEC/DOC).
- **Kind**: test

### M.TSC.002 No device-variant literal in `tests_scripts/`
- **From**: A.U24.66 (OR78.a: device set from data), A.U6.15 (variant-literal check), A.U37.10 (golden exclusions);
  A.U24.51/A.U6.14/A.U6.03 (derived device lists), HW_BENCH M.HW_BENCH.010 (`bench_device()`).
- **Site**: 25 files carry `"dev"`/`"wozi"`/device-name literals at HEAD: `test_buildgen_validate.py` (26),
  `test_buildgen_generate.py` (22), `test_buildgen_definitions.py` (23), `test_buildgen_tag_comments.py` (19),
  `test_buildgen_web_tag.py` (17), `test_build_firmware.py` (13), `test_buildgen_driver_registry.py` (13),
  `test_buildgen_requires_tag.py` (13), `test_buildgen_defaults.py` (11), `test_device_tomls.py` (8),
  `test_build_website_sh.py` (7), `test_buildgen_frozen_modules.py` (7), `test_buildgen_graph.py`,
  `test_buildgen_limits.py`, `test_digital_twin_ci_suite_ceiling.py` (4 each), `test_buildgen_wiring.py`,
  `test_buildgen_twin_wiring.py`, `test_buildgen_value_wiring.py`, `test_request_body_cap_headroom.py`,
  `test_digital_twin_boot_contiguity.py`, `test_setup_toolchain_env.py`, `test_digital_twin_generated_boot.py` (3
  each), `test_digital_twin_ci_suite_soak.py` (2), `test_resolve_board_device.py`,
  `test_tests_hardware_conftest_constants.py` (1 each).
- **Change**: a test that means "every device" iterates `_devices.DEVICE_NAMES` (parametrize ids = the names); a test
  that means "a device with property P" selects it from data (`_devices.devices_with(...)`-style query over the parsed
  TOMLs: the device with a `uart_link` pair, the device with an `isl29125`, the bench device via `bench = true`
  (A.U26.01)); a test that needs only *a* well-formed device uses the synthetic fixture named `fixture` (TOML
  `[device] name = "fixture"`, file `devices/zz_test_fixture*.toml` or `tmp_path`); prose comments name no variant. A
  device name may remain only inside data the test reads (TOMLs, goldens) — never as a literal the test compares
  against. The check (`test_no_variant_literals.py`, {{novariant}}) covers `tests_scripts/` with an exclusion list only for
  committed fixtures (`golden/`, `fixtures/api_reference/`, A.U37.10).
- **Resolved**: A.U24.66 and the per-file actions that each name one literal (A.U24.51, A.U6.14, A.U6.03, A.U20.19)
  agree; one end state.
- **Unit**: U24 (A.U24.66); files whose own unit is later (U26 bench, U27 scripts) adopt it in that unit.
- **Depends**: A.U26.01 (`bench` key, HW_BENCH/GEN), M.GEN (device-set derivation).
- **Blast carried by**: per-file sections below.
- **Kind**: test

### M.TSC.003 Host test code drops `from __future__ import annotations`
- **From**: A.U20.33.
- **Site**: `_script_loader.py`, `test_bench_harness_helpers.py`, `test_bench_restores_serving.py`,
  `test_comment_block_cap.py`, `test_device_script_config_flush.py`, `test_device_script_gc_threshold.py`,
  `test_digital_twin_boot_contiguity.py`, `test_digital_twin_generated_boot.py`, `test_heap_map_parser.py`,
  `test_twin_never_needs_tests_on_its_path.py` (line 1-10 import blocks).
- **Change**: the import goes (Python ≥ 3.11 host floor evaluates every annotation used); any forward reference it was
  hiding becomes a quoted name. New L0 `tests_scripts/test_host_annotations.py` ({{hostann}}) fails when a host file
  (`buildgen/`, `scripts/`, `toolchain/`, `tests_scripts/`, `tests_hardware/` host code) carries the import.
- **Resolved**: —
- **Unit**: U20
- **Depends**: —
- **Blast carried by**: `buildgen/`/`scripts/`/`toolchain/` sites → A.U20.33 (GEN/SCR); `tests_hardware/` → HW_BENCH.
- **Kind**: test

### M.TSC.004 Clear explicit `Any` from `tests_scripts/`
- **From**: A.U24.73, A.U20.32 (`_toml_fixtures.py:16` alias "typed the same way").
- **Site**: 21 lines in 8 files: `_toml_fixtures.py`, `test_buildgen_definitions.py`, `test_buildgen_twin_wiring.py`,
  `test_device_tomls.py`, `test_digital_twin_generated_boot.py`, `test_micropython_overrides.py`,
  `test_request_body_cap_headroom.py`, `test_strip_type_checking.py`.
- **Change**: TOML documents typed with buildgen's own `TomlDoc`/`TomlValue` aliases (the M.GEN typed form,
  A.U20.32), JSON with `JsonValue`; parsed JSON narrowed with `isinstance` before use; no `Any` import remains in
  `tests_scripts/`. The `test_buildgen_twin_wiring.py` ANN401 per-file exemption (`pyproject.toml:295`) is removed in
  the same commit (TOOL: Gaps).
- **Resolved**: —
- **Unit**: U24
- **Depends**: A.U20.32 (`TomlDoc` typed, GEN), A.U8.24 baseline (TOOL).
- **Blast carried by**: `pyproject.toml` exemption → Gaps (TOOL).
- **Kind**: test

### M.TSC.005 Follow the unit-suffix rename `trigger_sec` → `trigger_s`
- **From**: A.U10.43.
- **Site**: `_toml_fixtures.py:37`; `test_buildgen_validate.py:410, 466, 728, 758-770`; `test_buildgen_generate.py:150`;
  `test_buildgen_tag_comments.py`, `test_buildgen_limits.py`, `test_device_tomls.py` (any `_sec` key/identifier);
  `buildgen_fixtures/multi_instance.toml`, `novel_combo.toml`.
- **Change**: every TOML key and expected constructor kwarg reads `trigger_s`; test names `*_trigger_sec_*` →
  `*_trigger_s_*`; a TOML still carrying `trigger_sec` is a rejected unknown key (A.U10.43's validation), pinned by one
  case in `test_buildgen_validate.py` ({{validate_trigger}}).
- **Resolved**: —
- **Unit**: U10
- **Depends**: A.U10.43 (GEN/SRC renames).
- **Blast carried by**: per-file sections.
- **Kind**: test

### M.TSC.006 A missing build prerequisite fails, never skips
- **From**: A.U7.26.
- **Site**: `conftest.py:60`, `test_coverage_runner.py:27`, `test_test_sh.py:408`,
  `test_digital_twin_boot_contiguity.py:109`, `test_micropython_overrides.py:48, 350`.
- **Change**: each `pytest.skip(msg)` → `pytest.fail(msg)` (message unchanged, naming the command that builds the
  prerequisite). The opt-in gate `test_build_firmware.py:197` (`skipif` on `RUN_SLOW_FIRMWARE_BUILD`) and
  `test_buildgen_validate.py:1208` (a declared opt-in, not a prerequisite) stay skips.
- **Resolved**: —
- **Unit**: U7
- **Depends**: —
- **Blast carried by**: CI provisions every prerequisite before the pytest tier → A.U28.08 (TOOL).
- **Kind**: test

### M.TSC.007 Tag the `tests_scripts/` budgets with `@tunable`
- **From**: A.U8.22, A.U8.14, A.U8.15, A.U8.20, A.U8.05, A.U30.18 (its own tag).
- **Site**: per A.U8.22's list (`test_digital_twin_boot_contiguity.py:34, 71, 76-77, 81`;
  `test_digital_twin_generated_boot.py:29-30, 42, 100, 105, 185, 188`; `test_coverage_runner.py:38`;
  `test_live_twin_ceiling_parser.py:24`; `test_threshold_runner.py:26`; `test_test_sh.py:307, 453, 471, 544, 650, 699,
  737, 780`; `test_bench_harness_helpers.py:134`; `test_digital_twin_ci_suite_ceiling.py:105, 111`;
  `test_request_timeout_ceiling.py:237, 290`); `test_await_depth.py` `_MAX_AWAIT_DEPTH`.
- **Change**: one `# @tunable l0.<file_stem>_<name> = <literal>` per named budget (IDs as A.U8.22 lists, e.g.
  `l0.boot_contiguity_probe_timeout_s`, `l0.generated_boot_poll_timeout_s`, `l0.generated_boot_exit_wait_s`,
  `l0.bench_helpers_stop_wait_s`, `l0.ci_suite_ceiling_get_timeout_s`); `test_test_sh.py`'s subprocess timeouts share
  `_NESTED_RUN_TIMEOUT_S = 60` and `_SNIPPET_TIMEOUT_S = 30`; the await budget keeps A.U30.18's ID
  `mem.max_await_depth`. Test inputs that drive a fake (A.U8.22's list) stay untagged. Each tag has its Part N row
  (A.U8.22/A.U8.02, SPEC).
- **Resolved**: —
- **Unit**: U8 (U30 for the await budget)
- **Depends**: A.U8.01/A.U8.02 (grammar, register check {{tunables}}).
- **Blast carried by**: Part N rows → A.U8.22 (SPEC).
- **Kind**: test

### M.TSC.008 Build-error assertions match `rule`/`fix` and the internal-error class
- **From**: A.U20.17 (1)-(5), A.U27.29; M.GEN.022 (`BuildError(device, message, *, rule, fix, …)`,
  `BuildInternalError`).
- **Site**: every `pytest.raises(BuildError, match=…)` in `test_buildgen_validate.py`, `test_buildgen_generate.py`,
  `test_buildgen_limits.py`, `test_buildgen_requires_tag.py`, `test_buildgen_wiring.py`, `test_buildgen_graph.py`,
  `test_build_firmware.py:31, 49, 73`, `test_generate_sensortask_modules.py:58`.
- **Change**: the ~150 existing `pytest.raises(BuildError, match=…)` sites keep matching the message part (the
  `- fix: …` suffix is appended after it; no edit needed); a test whose match string included a fix clause that moved
  into `fix=` ("- add one to …", "- give one a disambiguating name_ext", the `_check_limits()` range/choice tails)
  matches the new `- fix: <sentence>` tail instead; the one direct constructor (`test_generate_sensortask_modules.py:58`)
  passes `rule=`/`fix=`; the synthetic "internal" tests (`test_buildgen_generate.py:497-538`, the `"internal:"` matches
  in `test_buildgen_validate.py`) expect `BuildInternalError`. `_toml_fixtures._dump_scalar()` renders inline
  tables/arrays (M.TSC.012). New `test_buildgen_error_contract.py` ({{errcontract}}) pins the contract once.
- **Resolved**: —
- **Unit**: U20 (U27 for the CLI exit idiom cases)
- **Depends**: M.GEN.022.
- **Blast carried by**: per-file sections.
- **Kind**: test

## tests_scripts/_citation_allowlist.txt
### M.TSC.009 Create, shrink and finally delete the citation allow-list
- **From**: A.U0.08 (create), A.U1.08 (drop `dev_legacy/` entries), A.U36.544 (6) (empty it), A.U37.02 (remove).
- **Site**: new `tests_scripts/_citation_allowlist.txt` (one entry per unresolved citation at U0's landing).
- **Change**: staged — U0: generated at landing from A.U0.08's check (every failing citation listed, the check fails
  on a listed entry that no longer occurs, so the list only shrinks); U1: every entry for `dev_legacy/README.md` and for
  each sentence A.U1.10-A.U1.21 rewrite or delete goes in the same commit; U36: A.U36.544 fixes every remaining entry
  (pointer to a permanent home, or the fact stated in place; an entry needing an owner decision goes to BACKLOG's
  owner-question list, never stays listed) so the file is empty; U37: the file and the check's allow-list reading go
  (A.U37.02), the check itself stays.
- **Resolved**: —
- **Unit**: U37 (stages U0 create, U1 shrink, U36 empty).
- **Depends**: {{citations}} (check), A.U36.544 (DOC/SPEC rewrites).
- **Blast carried by**: the rewritten citers → A.U1.10-A.U1.21, A.U36.544 (DOC/SPEC).
- **Kind**: test

## tests_scripts/_decision_vocab_allowlist.txt
### M.TSC.010 Create, shrink and finally delete the decision-vocabulary allow-list
- **From**: A.U0.09 (create), A.U1.08 (drop entries of deleted/rewritten legacy sentences), A.U36.549 (empty it),
  A.U37.02 (remove).
- **Site**: new `tests_scripts/_decision_vocab_allowlist.txt`.
- **Change**: staged — U0: generated at landing from A.U0.09's check (shrink-only, like M.TSC.009); U1: entries for
  `dev_legacy/README.md` and A.U1.10-A.U1.21's sentences go; U36: A.U36.549 resolves every remaining entry (the
  sentence gains its actor — owner or agent with date — or loses the vocabulary) so the file is empty; U37: file and
  allow-list reading removed (A.U37.02), the check stays.
- **Resolved**: —
- **Unit**: U37 (stages U0, U1, U36).
- **Depends**: {{vocab}} (check), A.U36.549 (DOC).
- **Blast carried by**: rewritten sentences → A.U36.549 (DOC/SPEC/code-comment owners).
- **Kind**: test

## tests_scripts/_script_loader.py
### M.TSC.011 Keep the by-path script loader as a named dynamic load
- **From**: A.U10.30 (the loader is one of the F.1-named dynamic loads; the import-graph check allows it by name),
  A.U0.07 (`_script_loader.py:15-23` in the import-placement `_PENDING` list until its owning unit names it);
  adherence (comment `:19-21` cites the `from __future__` mechanism that M.TSC.003/A.U20.33 removes from the hosts).
- **Site**: `tests_scripts/_script_loader.py:15-23` (`load_script_module`).
- **Change**: behaviour unchanged (`spec_from_file_location` + `sys.modules[name] = module` before `exec_module`).
  The `_PENDING` entry for `:15-23` is removed in U10, when SPEC F.1's list names this loader ("loads a `scripts/` or
  `toolchain/` file by path; neither is a package") and `test_import_graph.py` ({{importgraph}}) allows it by that name.
  Comment `:19-21` → "# Registered in sys.modules BEFORE exec_module(): a @dataclass resolves its string annotations
  through sys.modules[cls.__module__] while the class body still runs." (the `from __future__` clause goes once no host
  file carries the import).
- **Resolved**: —
- **Unit**: U10 (comment in U20 with A.U20.33).
- **Depends**: A.U10.30 (SPEC F.1 list), {{importplacement}} (`_PENDING`).
- **Blast carried by**: SPEC F.1 named-loader list → A.U10.30 (SPEC).
- **Kind**: test

## tests_scripts/_toml_fixtures.py
### M.TSC.012 `_dump_scalar()` writes inline tables and arrays
- **From**: A.U20.17 (4).
- **Site**: `tests_scripts/_toml_fixtures.py:63-68` (`_dump_scalar`).
- **Change**: a `dict` renders as a TOML inline table `{k = v, …}` (recursively through `_dump_scalar`), a `list` as a
  TOML array `[a, b]`; `bool`/`str`/number unchanged. A test writing a non-table where a table belongs (e.g.
  `wiring = "fram"`, `[device] wiring = 1`) then reaches the check it targets instead of `TOMLDecodeError`.
- **Resolved**: —
- **Unit**: U20
- **Depends**: —
- **Blast carried by**: callers writing sub-tables as sections already (`write_doc(` users) unchanged; new error rows →
  {{errcontract}}.
- **Kind**: test

### M.TSC.013 Type the local `TomlDoc` alias and rename the trigger key
- **From**: A.U20.32 (Blast: "keeps its own local alias — typed the same way"), A.U24.73, A.U10.43 (`:37`).
- **Site**: `tests_scripts/_toml_fixtures.py:11-16` (alias), `:37` (scd30 instance).
- **Change**: `from typing import Any` goes; `TomlDoc` becomes the same recursive shape buildgen types (`TomlValue =
  str | int | float | bool | list["TomlValue"] | dict[str, "TomlValue"]`, `TomlDoc = dict[str, TomlValue]`), kept local
  (the module stays import-independent of `buildgen/`, as its docstring says); comment `:13-15` shortened to "# Same
  shape as buildgen.model.TomlDoc, kept local: this module never imports buildgen/." `:37` `"trigger_sec": 3` →
  `"trigger_s": 3` (M.TSC.005).
- **Resolved**: —
- **Unit**: U24 (alias); U10 (key).
- **Depends**: A.U20.32 (buildgen alias, GEN), A.U10.43.
- **Blast carried by**: callers reading nested values narrow with `isinstance` → their own files' M.TSC.004 edits.
- **Kind**: test

## tests_scripts/conftest.py
### M.TSC.014 Drop the repo-root `sys.path` insert for pytest's `pythonpath`
- **From**: A.U27.37 (a new `pythonpath = ["."]` in `[tool.pytest.ini_options]` makes `:18` redundant; it goes);
  A.U24.13 ("`conftest.py:18` unchanged" — a no-shadowing statement, superseded by the later unit).
- **Site**: `tests_scripts/conftest.py:15-18`.
- **Change**: the comment and `sys.path.insert(0, str(REPO_ROOT))` go; `import sys` goes if unused.
- **Resolved**: A.U24.13 (U24) states the line is unchanged for its own purpose (no shadowing); A.U27.37 (U27) removes
  it — later unit, and A.U24.13's reason (no module shadowing) holds either way.
- **Unit**: U27
- **Depends**: `pyproject.toml` `pythonpath = ["."]` → A.U27.37 (TOOL: Gaps).
- **Blast carried by**: `import buildgen` in every test resolves through `pythonpath` (same root).
- **Kind**: test

### M.TSC.015 `micropython_bin` asks the shared Unix-port probe and fails on mismatch
- **From**: A.U27.12 (3), A.U7.26 (`:60` skip → fail), A.U21.11 (Blast: `micropython_dir` fixture reused, holds).
- **Site**: `tests_scripts/conftest.py:44-61` (`micropython_dir`, `micropython_bin`).
- **Change**: `micropython_bin` runs `bash scripts/_unix_port.sh check standard` (`subprocess.run`, `cwd=REPO_ROOT`,
  captured) and returns `Path(stdout.strip())`; exit 1 → `pytest.fail(<the script's message>)` (never skip); the
  hand-built `build-standard` path and the `:55-57` comment go (the path has one home, `scripts/_unix_port.sh`).
  `micropython_dir` stays (the checkout path used by `test_micropython_overrides.py`, A.U21.11), comment `:46-48`
  reworded to "# The toolchain checkout (PICO_TOOLCHAIN_DIR, else ~/pico-toolchain), as scripts/_unix_port.sh resolves
  it." — or the fixture reads the same script's printed root if A.U27.12 (4)'s single reading of
  `PICO_TOOLCHAIN_DIR` is to hold for Python callers too (the fixture then calls `unix_port_bin standard` and takes
  `parents[3]`).
- **Resolved**: A.U7.26 (U7) turns `:60`'s skip into a fail; A.U27.12 (U27) replaces the check by the probe and keeps
  the fail — one end state, staged.
- **Unit**: U27 (stage U7: `:60` skip → fail).
- **Depends**: A.U27.12 (`scripts/_unix_port.sh`, SCR).
- **Blast carried by**: callers `test_digital_twin_generated_boot.py`, `test_digital_twin_boot_contiguity.py`,
  `test_stripped_image_boots.py` (fixture name unchanged).
- **Kind**: test

### M.TSC.016 conftest stays clean under its own host type-check run
- **From**: A.U27.23 (2) (`mypy --config-file host_typecheck.ini tests_scripts/conftest.py` run alone by
  `typecheck.sh`); A.U0.06 (U0 measured this exclusion; read).
- **Site**: `tests_scripts/conftest.py` (whole file).
- **Change**: no code edit required by the action; the file must pass `--strict` in that separate run (all five
  fixtures annotated at HEAD). If the run still reports a duplicate module, the file gets A.U27.24's named exclusion
  row instead (the action's own fallback).
- **Resolved**: —
- **Unit**: U27
- **Depends**: A.U27.23 (`typecheck.sh`, SCR/TOOL).
- **Blast carried by**: SPEC B.15 "two trivial fixtures" wording → A.U27.23 (SPEC).
- **Kind**: test

## tests_scripts/definitions_shape_cases.json
### M.TSC.017 Shared definitions-shape corpus for pytest and vitest
- **From**: A.U6.16 (3); U23's G7/R38 validator additions add cases (A.U6.16's own clause; A.U23.09/A.U23.10 per
  M.WEB).
- **Site**: new `tests_scripts/definitions_shape_cases.json`.
- **Change**: `[{"name": str, "definitions": object, "valid": bool}]`: one valid minimal document plus one invalid case
  per rejection `validateDefinitions()` makes (A.U6.16's list: non-object; schemaVersion missing/non-semver; wrong
  major; device.id missing; landingSection missing; defaultPollIntervalMs ≤ 0; sections empty; section not an object;
  section key/label/rest.get missing; bad pollGroup; pollIntervalMs ≤ 0; groups not an array; group key/label missing;
  errcount modules not an array; fields not an array; path malformed; path on a writable kind; decimals −1/1.5/"2"/101;
  landingSection matching no section), plus one case per rejection U23 adds to `validateDefinitions()` in the same
  commit. Read by `test_buildgen_definitions.py` ({{defs_shape}}) and `tests_js/definitions-shape-corpus.test.js`
  (A.U6.16, WEB), each asserting `problems == [] ⇔ valid`.
- **Resolved**: —
- **Unit**: U6 (U23 appends).
- **Depends**: A.U6.16 (1) `MAX_DECIMALS` (WEB).
- **Blast carried by**: vitest reader → A.U6.16 (WEB); SPEC G mirror catalog entry → A.U6.16 (SPEC).
- **Kind**: test

## tests_scripts/golden/stored_config.json
### M.TSC.018 Commit the stored-config golden at the release point
- **From**: A.U11.33 (2), A.U37.10.
- **Site**: new `tests_scripts/golden/stored_config.json`.
- **Change**: per device of `devices/*.toml` (read from data), each config file name → stored key → type map
  (special-alone fields excluded), generated from the tip after the key harmonisation (A.U10.40) and committed at U37;
  from the merge on, any change to it carries a migration in the same commit.
- **Resolved**: A.U11.33 says "written once at the release point (B5 close)"; A.U37.10 is that commit — same end state.
- **Unit**: U37
- **Depends**: A.U10.40 (harmonisation), {{golden}} (test).
- **Blast carried by**: SPEC C.5/L key-stability rule → A.U11.33 (SPEC).
- **Kind**: test

## tests_scripts/test_api_reference.py
### M.TSC.019 The normative REST reference is generated, complete and pinned
- **From**: A.U19.20 (3)-(4), A.U37.10; M.GEN (reference generator; GEN line 774-783: "committed fixtures at the
  release point are TST/SCR's").
- **Site**: new `tests_scripts/test_api_reference.py`; new `tests_scripts/fixtures/api_reference/<device>.json`.
- **Change**: L0, per device of `_devices.DEVICE_NAMES`: (a) the generated reference is byte-identical over two
  generations; (b) every `ROUTES` entry appears; (c) every `@web` field appears under its route; (d) no route outside
  `ROUTES` (none of the 14 legacy paths, G6/R38). Staged: U19 lands (a)-(d); U37 commits
  `fixtures/api_reference/<device>.json` from the release tip and (a) becomes "equals the committed fixture; any
  difference needs a migration recorded in the same commit" (failure message says so).
- **Resolved**: —
- **Unit**: U37 (stage U19).
- **Depends**: A.U19.20 (1)-(2) (ROUTES, generator; GEN/SRC_NET), A.U10.40.
- **Blast carried by**: SPEC A.8 normative-reference statement → A.U19.20 (SPEC); staging in `build_website.sh` →
  A.U19.20 (SCR).
- **Kind**: test

## tests_scripts/test_await_depth.py
### M.TSC.020 Pin the longest static await chain as a C-stack tripwire
- **From**: A.U30.18 (1)-(2).
- **Site**: new `tests_scripts/test_await_depth.py` (+ the analysis it runs).
- **Change**: the AST analysis lives in this test file (or a `tests_scripts/_await_depth.py` helper beside it): from
  every task top — each coroutine handed to `create_task()` in `src/` and in the generated modules (generated in
  memory via `generate_device()` for every device of `DEVICE_NAMES`) — follow `await` edges through module functions
  and attributes whose class the constructor or annotation names; report the longest chain and its path per top. The
  test fails when the longest chain exceeds `_MAX_AWAIT_DEPTH` (`# @tunable mem.max_await_depth = <n>`, n = the
  measured longest chain at landing; Part N row basis "longest static await chain at landing; per-level C-stack cost
  from the phase-C reading"). One fabricated bite: a synthetic `tmp_path` module whose chain exceeds the bound fails
  the analysis (a fixture, not a CI control arm, OR21.a (2)).
- **Resolved**: A.U30.18 (1) names "new audit-scratch analysis `audit/stack_depth.py`"; a permanent test cannot depend
  on `audit/` (temporary, G9/R12) — the analysis the test reruns lives under `tests_scripts/` (agent decision D-TSC1).
- **Unit**: U30
- **Depends**: M.TSC.007 (tag), A.U8.02 (register).
- **Blast carried by**: device script + flash runner entry → A.U30.18 (HW_DEV); SPEC F.1/I.4 paragraphs → A.U30.18
  (SPEC).
- **Kind**: test

## tests_scripts/test_bench_harness_helpers.py
### M.TSC.021 Header, imports and the device loop
- **From**: A.U20.33 (future import), A.U24.51 + A.U27.37 (`:138-143` per-device loop; the ceiling lookup holds),
  A.U28.28 (inline `noqa` reasons, one per file), A.U24.13 (`:20` insert unchanged — read), A.U8C.112 (read: drives
  `wait_for_script_server` against a fake, unchanged), A.U26.83 (read: no removed name referenced), A.U35.40 (read: the
  helper it revives is not used here; M.HW_BENCH.052 keeps it), M.TSC.002.
- **Site**: `tests_scripts/test_bench_harness_helpers.py:1-25`, `:138-143`.
- **Change**: docstring (≤ 3 lines) "Covers tests_hardware/'s shared host helpers offline against fakes: serving
  restore and recovery, boot/crash line observers, errcount oracles, mpremote/picotool/iptables wrappers and the
  thread-worker rules over every hardware module."; `from __future__ import annotations` goes and `Callable` is imported
  at runtime (`from collections.abc import Callable`, no `TYPE_CHECKING` block); the three `# noqa: E402` keep the one
  reason on the first. `:138-143` → `@pytest.mark.parametrize("device", DEVICE_NAMES)` over
  `harness.configured_max_connections(device) == device_max_connections(device_toml(device), REPO_ROOT / "src")` (the
  live `devices/` glob, which read concurrently written `zz_test_*` fixtures, goes).
- **Resolved**: —
- **Unit**: U26 (U20 future import; U24 loop).
- **Depends**: A.U27.37 (by-name ceiling helper, SCR/GEN), M.HW_BENCH.010.
- **Blast carried by**: `pyproject.toml` per-file ignores → A.U28.28 (TOOL).
- **Kind**: test

### M.TSC.022 Serving restore and recovery-by-reset cases
- **From**: A.U26.29 (new L0 cases; existing `restore_board_to_serving` tests adapt), A.U8.22 (`:134` tag); M.HW_BENCH.015.
- **Site**: `tests_scripts/test_bench_harness_helpers.py:62-79`, `:128-135`, new cases.
- **Change**: `:62-79` asserts the call order through `kick_then_reset()` (one kick before one reset, then the HTTP
  wait). New: `recover_by_reset(board, bench, ready, …)` with a fake board/bench and a recording `note` — ready at once →
  no note, no reset; ready only after the reset → one recovery note naming `skipped`, kick before reset (order
  recorded); never ready → raises after exactly one reset. New AST rule: no module under `tests_hardware/bench/` calls
  `.hard_reset()` outside `kick_then_reset`/`recover_by_reset` (A.U26.29's "no bare reset" check). `:134`'s `2.0` →
  `_STOP_WAIT_S = 2.0  # @tunable l0.bench_helpers_stop_wait_s = 2.0`; `:51, :58` stay untagged (test inputs).
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.015.
- **Blast carried by**: Part N row → A.U8.22 (SPEC).
- **Kind**: test

### M.TSC.023 Errcount oracles fail closed; the clear saves first
- **From**: A.U26.67 (`:82-91`), A.U26.22 (stubs of `reset_all_error_logs` follow its `reason`); M.HW_BENCH.050/.051.
- **Site**: `tests_scripts/test_bench_harness_helpers.py:82-91`, new cases.
- **Change**: `test_a_module_absent_before_that_logs_now_is_a_new_error` → `test_a_logger_absent_before_and_present_now_is_a_shape_change`:
  `assert_no_module_logged_a_new_error("dut", {}, "burst")` with `SGP40` present after raises `AssertionError`
  naming `'SGP40'` and the shape change; a new case for the reverse (present before, absent after); new:
  `errcount_entry(counts, "NOPE")` raises naming the missing logger and the sorted names present; an entry without
  `counter`/`history` fails. `:88-90` (unchanged counter) passes with `history` present in both fakes. Any stub of
  `reset_all_error_logs` takes `(dut_ip, reason)`.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.051, M.HW_BENCH.050.
- **Blast carried by**: the save-before-PUT order → {{evidence}}.
- **Kind**: test

### M.TSC.024 The thread-worker rule sees every worker's fetch, and joins
- **From**: A.U26.50.
- **Site**: `tests_scripts/test_bench_harness_helpers.py:93-125`.
- **Change**: targets read from `target=` and from the second positional argument of any `…Thread(` call; a fetching
  call is `http_client.fetch`, a module-local `fetch`, or a module-level helper whose body makes one (transitively in
  the module, then across `tests_hardware/*.py` helpers by name); a target is flagged when a fetching call in it (or in a
  nested function it calls) lies outside every `try` whose handlers name `http_client.HTTP_ERROR`, `Exception` or
  `BaseException` beside `OSError`. Parametrised over every `tests_hardware/**/*.py` except `device_scripts/`. Second
  rule: a `threading.Thread(...)` started in a test has a `join()` reachable in a `finally`. Bites (fixtures, not CI arms):
  a try-less worker, a positional-target worker calling a helper, an unjoined started thread.
- **Resolved**: —
- **Unit**: U26
- **Depends**: —
- **Blast carried by**: sites newly flagged → fixed in their bench modules (M.HW_BENCH.061/.064/.074/.081).
- **Kind**: test

### M.TSC.025 Boot, crash and fault-window observers pinned against `src/`
- **From**: A.U26.26 (pinned strings), A.U26.27 (`"RTC set to:"` joins), A.U26.47 (2) (`observe_during` L0);
  M.HW_BENCH.016.
- **Site**: new cases in `tests_scripts/test_bench_harness_helpers.py`.
- **Change**: each `harness.BOOT_COMPLETION_MARKERS` entry and `"RTC set to:"` occurs in a `pr.one(`/`pr.*(` call text
  in `src/` (read by `ast`, so a reworded log line fails here); `boot_lines()` ignores a `CFGMGR_` tag line without a
  marker; `crash_lines()` returns a `Traceback` line and each `MEMORY_ERROR_MARKERS` line; `observe_during()` with a
  fake board whose log thread yields lines before, during and after the action returns all three windows (the tail
  constant `_OBSERVE_TAIL_AFTER_S` patched small).
- **Resolved**: A.U11.19 rewords the missing-file branch (no `:478` line); the pin keeps `config is ready` (`:468`) and
  the FRAM line — as M.HW_BENCH.016 states.
- **Unit**: U26
- **Depends**: M.HW_BENCH.016, A.U11.19.
- **Blast carried by**: —
- **Kind**: test

### M.TSC.026 Wrapper contracts: DebugLevel parse, picotool retry, iptables listing, no-sync
- **From**: A.U26.12 (LEVEL parse), A.U26.14 (`_retryable_picotool_exit`), A.U26.15 (default reads), A.U26.21
  (`allow_missing` stubs → listing form), A.U26.13 (stubs adapt to two calls), A.U26.75 (`--no-sync` argv);
  M.HW_BENCH.006/.011/.014/.020/.080.
- **Site**: new cases and existing `subprocess.run` stubs in `tests_scripts/test_bench_harness_helpers.py`.
- **Change**: (a) the standard-state fixture's DebugLevel parse on a fake board: `LEVEL=5` passes, `LEVEL=3` and
  `LEVEL=absent` fail naming the repair. (b) `_retryable_picotool_exit(249)` is true, any other code false. (c) the
  default read of `_VAL_NH` and of each pushed sensor field equals the value its `src/` tuple declares (independent
  `ast` read of `src/`). (d) any stub of the bench `iptables` wrapper answers the `-D` then listing form
  (M.HW_BENCH.020); stubs of `_mpremote` expect the two-call shape (M.HW_BENCH.011). (e) AST rule: no `["uv", "run", …]`
  argument list in `tests_hardware/` lacks `"--no-sync"`.
- **Resolved**: A.U26.16's rig-parking check could live here or in its own file; it gets its own file
  (`test_device_script_rig_parking.py`, {{rigparking}}) — the device-script guards each have one file.
- **Unit**: U26
- **Depends**: M.HW_BENCH.006, .011, .014, .020, .080; A.U28's retried sync (TOOL).
- **Blast carried by**: retry/no-retry cases → {{mpremote_retry}}; listing cases → {{control_restore}}.
- **Kind**: test

## tests_scripts/test_bench_no_task_ended_completeness.py
### M.TSC.027 The no-task-ended guard covers methods, helpers, fixtures and flash
- **From**: A.U26.62, A.U26.67 (`(None, True)` flips), A.U2.03 + A.U2.08 + A.U3.06 (`:64-66` numbers → catalog
  names), A.U28.28 (`FBT001` moves to a per-file entry), A.U24.13 (read: `:12` insert unchanged); M.HW_BENCH.051.
- **Site**: `tests_scripts/test_bench_no_task_ended_completeness.py:15-78`.
- **Change**: (1) scanned functions include methods of `Test*` classes; (2) a fault is also a call to a module-level or
  `tests_hardware/*.py` helper whose body (transitively, by name) calls an injector, and a requested fixture that
  injects (e.g. `joined_hotspot`) unless that fixture asserts no task ended in its teardown; (3) the scan covers
  `tests_hardware/flash/test_*.py` with `_FLASH_FAULT_SCRIPTS` (CS hijack, UART silence and desync, reset races), whose
  required check is the script's own SYSTEM-logger assertion or an `_EXEMPT` entry with its reason; `recover_by_reset`
  stays out of `_CHECKERS`; (4) `len(names) >= 15` → equals the number of injector call sites the scan found (derived).
  `:59-78` parametrisation: the `(None, True)` row → `(None, False)` ("a missing SYSTEM entry is a shape change, fails
  closed", match the `errcount_entry` message); the history rows use `code("E", "TASK_RAISED")` (42),
  `code("E", "TASK_BUDGET_REBOOT")` (41), and a restart warning row becomes `code("E", "TASK_RETURNED")` (44) — the
  dynamic `wrnno` goes (M.SRC_CORE.005), so no W row; numbers come from `tests/_error_codes.code` (M.TEST_HELP.045), no
  literal. The inline `# noqa: FBT001` goes to `pyproject.toml` per-file-ignores with "pytest passes parametrized values
  by name".
- **Resolved**: A.U2.08 (U2) and A.U3.06 (U3) both rewrite `:64-66`'s codes; the end state is the catalog names of
  both (A.U3.06's 44 added); A.U26.67 (U26) flips `(None, True)` — staged, one end state.
- **Unit**: U26 (stages U2: catalog names 40-43; U3: 44 and W row removed).
- **Depends**: M.SRC_CORE.005, M.TEST_HELP.045, M.HW_BENCH.051, A.U26.34 (script SYSTEM assertion, HW_DEV).
- **Blast carried by**: `pyproject.toml` FBT001 entry → A.U28.28 (TOOL: Gaps); README scope `:838-845` → A.U26.62
  (HW_BENCH).
- **Kind**: test

## tests_scripts/test_bench_restores_serving.py
### M.TSC.028 Bench and flash tiers end on a serving board
- **From**: A.U26.17 (flash-tier check), A.U20.33; read/coverage: A.U26.28, A.U26.87, A.S0930.28, A.S0930.39, A.C.12
  (new modules running device scripts are covered by the existing rule), A.U26.41/A.U26.85 (no device script: n/a).
- **Site**: `tests_scripts/test_bench_restores_serving.py:1-123`.
- **Change**: `from __future__ import annotations` goes. New `test_the_flash_tier_leaves_the_board_serving`:
  `tests_hardware/flash/conftest.py` defines an autouse session fixture whose teardown (after `yield`) calls
  `hard_reset` (same `ast` helpers as the bench rule). The bench rule's scan stays generic (every `bench/test_*.py`
  calling a runner), so the modules A.U26.28/.87, A.S0930.28/.39 and A.C.12 add are covered with no list edit; if a
  new flash module runs an isolated device script, the flash fixture covers it.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_DEV.021 (`leave_board_serving`), A.U26.26.
- **Blast carried by**: README traps sentence → A.U26.17 (HW_BENCH, M.HW_BENCH.127).
- **Kind**: test

## tests_scripts/test_build_firmware.py
### M.TSC.029 Staging rejections raise the build-error classes
- **From**: A.U27.29 (`:31` `RuntimeError` → `BuildError`; `:49`, `:73` → `BuildInternalError`), A.U24.66 (literals).
- **Site**: `tests_scripts/test_build_firmware.py:20-74`.
- **Change**: `:27-32` expects `BuildError` (`match="no-such-device"`; `rule` asserted); `:35-50` (frozen module
  resolving to neither `src/` nor `ext/`) and `:53-74` (reserved staging-name collision) expect `BuildInternalError`;
  any device used is `DEVICE_NAMES[0]` or the synthetic fixture (M.TSC.002).
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.GEN.022, A.U27.29 (`build_firmware.py`, SCR).
- **Blast carried by**: —
- **Kind**: test

### M.TSC.030 The manifest freezes a sorted file list
- **From**: A.U27.34.
- **Site**: `tests_scripts/test_build_firmware.py:77-87`.
- **Change**: `:87`'s `freeze('<stage_dir>')` assertion → the sorted file-list form the manifest now carries (each
  staged module named once, in sorted order); the default board-manifest include assertion holds.
- **Resolved**: —
- **Unit**: U27
- **Depends**: A.U27.34 (SCR).
- **Blast carried by**: reproducibility proof → {{frozen_inputs}}.
- **Kind**: test

### M.TSC.031 Staged modules follow the import-seeded set and the staging split
- **From**: A.U20.13 (`:91-101` follows `compute_frozen_modules(module_source, src_dir, ext_dir)`), A.U27.05 (follows
  `stage_python_modules()`), A.U24.66 (`:90`, `:124`, `:145-146`, `:149`, `:160` — four `["wozi", "dev"]`
  parametrisations), A.U26.02 (`:135-138` date), A.U19.18 (read: `:107-121` copies `ext/microdot.py`, holds),
  M.GEN.019 (boot entries).
- **Site**: `tests_scripts/test_build_firmware.py:89-167`.
- **Change**: every parametrisation is `@pytest.mark.parametrize("device", DEVICE_NAMES)`; the identity branch
  `:145` (a device-name special case) goes — what the device stages is read from its own generation;
  `:91-101` recomputes the expected set with `compute_frozen_modules(generated.module_source, src, ext)` and stages via
  `stage_python_modules()` (or `build_stage_dir()`, which calls it); `:125-146` asserts the staged
  `sensortask_<device>.py` equals `generate_device(...).module_source` and the staged `main.py` equals
  `boot_entry_source`; `:135-138` passes `build_date=` explicitly instead of monkeypatching
  `buildgen.generate.current_build_date` (the default-`None` path keeps one case).
- **Resolved**: —
- **Unit**: U27 (stages U20 signature, U24 device set).
- **Depends**: M.GEN.019, M.GEN (frozen set, A.U20.13), A.U27.05/A.U26.02 (`build_firmware.py`, SCR).
- **Blast carried by**: the stripped-image boot → {{stripped}}.
- **Kind**: test

### M.TSC.032 CLI cases: device TOML, no-autostart, toolchain lock, record, work dir
- **From**: A.S0930.06 (`--device-toml`), A.U27.36 (`--no-autostart`), A.U21.22 (dir without a record), A.U21.08
  (relative `--toolchain-dir` resolved), A.U27.29 (missing device through `main()`), A.U26.02 (record keys), A.U27.35
  (work dir), A.SDEP.03 (read: pytest deprecations; refresh in U0/U37).
- **Site**: `tests_scripts/test_build_firmware.py:170-199`, new cases.
- **Change**: new cases — (a) `--device-toml <tmp>.toml` (a copy of a derived device's TOML with a different hostname)
  stages a generated module carrying that hostname; a missing `--device-toml` path fails before staging; (b)
  `--no-autostart`: the staged `main.py` equals `boot_entry_noautostart_source`, every other staged file is
  byte-identical to a default staging of the same device, the default output name ends `-noautostart.uf2`; (c) a
  toolchain dir with no setup record fails with A.U21.22's message (`:186-193`'s missing-dir message holds); (d) a
  relative `--toolchain-dir` reaches `st.build_firmware()` resolved (monkeypatched to record); (e) a missing device
  through `main()` prints one line, no `Traceback`, exit 1; (f) with `st.build_firmware` stubbed to return a fake uf2,
  `main()` writes the image record beside it with keys `buildDate`, `commit`, `device`, `dirty`, `firmwareVersion`,
  `lwip`, `maxConnections`, `websiteVersion` (+ A.U27.31's three size keys) and `buildDate` equals the date in the
  staged module; the record's work dir is `tmp_path` (the test points `REPO_ROOT`-relative `build/` away by
  monkeypatching the module's work root), so no case writes into the live tree; the error-path cases assert no work
  dir was created.
- **Resolved**: —
- **Unit**: U27 (U26 record; S0930 rows land with their U26/U27 owners).
- **Depends**: A.S0930.06, A.U27.36, A.U21.22, A.U21.08, A.U26.02, A.U27.35 (all `build_firmware.py`/toolchain, SCR).
- **Blast carried by**: HW reflash helper → M.HW_BENCH.014; README build recipe → A.U27.36 (DOC).
- **Kind**: test

### M.TSC.033 The slow real build asserts the image report
- **From**: A.U27.31, A.U21.10 / A.U28.05 / A.SDEP.02 (read: `:202` real build runs in `firmware-build-verify`,
  holds), A.U7.26 (read: `:197` opt-in `skipif` stays).
- **Site**: `tests_scripts/test_build_firmware.py:197-216`, new case.
- **Change**: `test_real_firmware_build_produces_a_valid_uf2` (parametrised over `DEVICE_NAMES`) also asserts the
  `== Image: <used> B of <fs_base> B before the filesystem …` line and the record's size keys; new fast case:
  `image_report()` over a stub `arm-none-eabi-nm` symbol table yields the expected numbers, and an overlap raises
  `BuildInternalError`.
- **Resolved**: —
- **Unit**: U27
- **Depends**: A.U27.31 (SCR).
- **Blast carried by**: SPEC B.11 → A.U27.31 (SPEC).
- **Kind**: test

## tests_scripts/test_build_frozen_html_sh.py
### M.TSC.034 Frozen website: reproducible, quoted, work dir in `tmp_path`
- **From**: A.U27.06, A.U27.35, A.U1.25 (`:55` comment), A.U27.10 (read: runs under the venv's python3, holds),
  A.SDEP.07 / A.U34.08 (read: freezefs re-vendor and its record — this file is the L0 coverage, holds).
- **Site**: `tests_scripts/test_build_frozen_html_sh.py:14-76`.
- **Change**: `_run_build_frozen_html` sets `FROZEN_HTML_WORK_DIR=<tmp_path>/work` (no write into the live tree);
  `:55` comment → "…and how the legacy site's legacy/firmware/html_raw/{general,<device>} split worked."; `:73-76`
  asserts the message (`HTML_SRC_DIRS entry '<dir>' is not a directory - fix: point it at an existing source tree`);
  new: two builds of the same tree one second apart are byte-identical and the output contains `date_frozen = const(
  '1970/01/01 00:00:00' )`; an archive path of ≥ 255 characters fails with A.U27.06 (3)'s message before freezefs
  runs.
- **Resolved**: —
- **Unit**: U27 (U1 comment).
- **Depends**: A.U27.06, A.U27.35 (`build_frozen_html.sh`, SCR).
- **Blast carried by**: python-version stub case → {{require_python}}.
- **Kind**: test

## tests_scripts/test_build_website_sh.py
### M.TSC.035 Website build tests take devices from data, generation is the only path
- **From**: A.U6.14, A.U6.03, A.U24.66, A.U27.33 (`:58-68` valid-devices message), A.U27.35 (`WEBSITE_WORK_DIR`),
  A.U36.544 (`:73` L.4 → H.5), A.U36.517 (read: comments name H.2), A.U27.10 (read).
- **Site**: `tests_scripts/test_build_website_sh.py:9-110`, `:130-138`.
- **Change**: `_run_build_website` sets `WEBSITE_WORK_DIR=<tmp_path>/work`; `from _devices import DEVICE_NAMES`;
  single-device tests (`:19`, `:49`, `:130`) use `DEVICE_NAMES[0]` and drop "wozi" from their names; `:54` negative
  list → `("/js/mock-server.js.gz", "/definitions.json.gz", *(f"/definitions/{d}.json.gz" for d in DEVICE_NAMES),
  *(f"/{d}.json.gz" for d in DEVICE_NAMES))`; `:58-67` asserts the message names `devices/no-such-device.toml` and
  lists the valid devices (A.U27.33), not `html/definitions/…`; `:70-86` → `test_every_device_inlines_generated_definitions_and_never_stages_them`
  parametrised over `DEVICE_NAMES` (`/index.html.gz`, `/js/app.js.gz`, no `/definitions.json.gz`); comments say "the
  buildgen generation step", not "fallback"; the Part pointer at `:73` reads H.5; `:89-110` (malformed TOML) holds with
  its `zz_test_` name.
- **Resolved**: —
- **Unit**: U27 (U6 device derivation; U36 pointer).
- **Depends**: A.U6.03, A.U27.33, A.U27.35 (`build_website.sh`, SCR/WEB).
- **Blast carried by**: `test_test_sh.py:61-66` reads this file's `devices/` write text (unchanged).
- **Kind**: test

### M.TSC.036 The hand-kept staging cross-check yields to the drift rule
- **From**: A.U23.38 (`:113-127` passes on a comment mention, WEB.S14 → replaced by the drift rule's own tests).
- **Site**: `tests_scripts/test_build_website_sh.py:113-127`.
- **Change**: `test_every_real_js_and_html_file_is_accounted_for_by_the_staging_script` goes; its job is
  `scripts/_stage_website.py`'s import-closure and stray-file refusals, proven in `test_stage_website.py` ({{stage_website}}).
- **Resolved**: —
- **Unit**: U23
- **Depends**: A.U23.38 (`_stage_website.py`, SCR/WEB).
- **Blast carried by**: {{stage_website}}.
- **Kind**: test

## tests_scripts/test_buildgen_defaults.py
### M.TSC.037 Keyword-only default parameters, renamed classes, neutral devices
- **From**: A.U20.21 (`:34, 42, 62-68, 77`, new keyword-only case), A.U10.38 (class names in fixtures), A.U24.66,
  A.U10.34 (read: `_Default*` detection reads class names, not docstrings — holds).
- **Site**: `tests_scripts/test_buildgen_defaults.py:26-84`.
- **Change**: calls are `default_init_params(class_node)` (the unused `_path/_device/_driver` parameters gone); new
  case `def __init__(self, *, need, opt=1)` → `need` required, `opt` optional; `:62-68` stays the positional case;
  driver class names follow A.U10.38 (CapWords, no `Asy`); device literals go (M.TSC.002).
- **Resolved**: —
- **Unit**: U20 (U10 names, U24 devices).
- **Depends**: M.GEN (A.U20.21 `defaults.py`).
- **Blast carried by**: validate's keyword-only `_Default*` case → `test_buildgen_validate.py` ({{validate_defaults}}).
- **Kind**: test

## tests_scripts/test_buildgen_definitions.py
### M.TSC.038 Retire the golden comparison; an independent tag oracle replaces it
- **From**: A.U6.04 (`:1-3`, `:28-30`, `:60-69` deleted; new oracle), A.U6.01 (`_generate()` `:55-57`, `:183-184`,
  `:194-195`, `:203-204` → `definitions_for_toml()`), A.U24.66 (`:19-20` name sets → data), A.U24.73 (`Any`), M.TSC.001
  (`system_service.py` ×4 → `asy_system_service.py`); dropped: A.U9.01's "edit the golden files unless A.U6.04 has
  landed" (A.U6.04 lands in U6, before U9 — nothing to edit); read: A.U36.515 (doc describing this file), A.U18.35
  (status-catalog text only; pins re-read at execution), A.U8.18 (value unchanged), A.U6.22/A.U6.24 (`:115-123` holds).
- **Site**: `tests_scripts/test_buildgen_definitions.py:1-123`.
- **Change**: docstring (≤ 3 lines) "Tests for buildgen.definitions (SPECIFICATION.md Part H.5/H.5.1): every tagged field
  lands once in its group, every device's output passes the shared shape corpus, and the catalog-derived blocks equal
  their sources."; `definitions_dir` and `test_generated_definitions_match_hand_written_reference` go; `_generate()`
  calls `definitions_for_toml()`; `BMP3XX_DEVICES`/`ISL29125_DEVICES` → helpers selecting the devices whose TOML
  declares `bmp3xx`/`isl29125`; new `test_every_tagged_field_lands_once_in_its_group` parametrised over `DEVICE_NAMES`:
  expected fields from `buildgen.web_tag.parse_web_tags()` on each instance's `driver_info.source_path` and the mandatory
  files (`asy_wifi_service.py`, `asy_ntp_client.py`, `asy_system_service.py`, notification's path), grouped by
  `(section, submitGroup→resolved_name)`, compared with the generated groups' `(key, label, unit)`. Typed with
  `JsonValue`, no `Any`.
- **Resolved**: —
- **Unit**: U6 (U24 typing/devices; U10 rename).
- **Depends**: A.U6.01, A.U6.03 (generated-only definitions, GEN/WEB).
- **Blast carried by**: `test_js_coverage_excludes_json.py:13` → {{js_cov_excl}}; `test_buildgen_twin_wiring.py:31`
  comment → {{twin_wiring_main}}; docs → A.U6.04 (SPEC/DOC).
- **Kind**: test

### M.TSC.039 `_shape_problems()` mirrors `validateDefinitions()` over one corpus <!--@defs_shape-->
- **From**: A.U6.16 (2)-(3), A.U23.09 (poll-interval upper bound), A.U2.21 (`:161-163` errcount `codes` object check).
- **Site**: `tests_scripts/test_buildgen_definitions.py:126-174`.
- **Change**: `_shape_problems()` gains semver + supported major, section-not-an-object, `pollIntervalMs` and
  `defaultPollIntervalMs` numbers with `0 < v <= 2**31 - 1` (read from `js/definitions.js`'s `MAX_POLL_INTERVAL_MS`
  by the mirror test, not re-typed here — the bound is a module constant `_MAX_POLL_INTERVAL_MS = 2**31 - 1` pinned by
  `test_definitions_js_mirrors.py`), the path/decimals field hints, and an errcount group's `codes` object; new
  `test_shape_corpus_agrees` parametrised over `definitions_shape_cases.json`: `(problems == []) == case["valid"]`;
  `:173-174` keeps every device's output passing.
- **Resolved**: —
- **Unit**: U23 (stage U6: the corpus and the HEAD rejections; U2: codes object).
- **Depends**: M.TSC.017, A.U23.09 (WEB).
- **Blast carried by**: JS side → A.U6.16/A.U23.09 (WEB); the constant pin → {{defs_js_mirrors}}.
- **Kind**: test

### M.TSC.040 Catalog-derived definition blocks equal their sources
- **From**: A.U2.21 (codes block = non-retired catalog codes), A.U23.20 (`codeTones` = catalog tones), A.U6.27 (field
  `codes` tables, every `codes=` names a present table), A.U6.19 (epoch format), A.U6.20 (SGP40 special values; tag
  field names = `_sgp_maintenance_status()` keys), A.U6.25 + A.U36.508 (each published logger key in exactly one
  errcount group; `DNSSRV` in networking), A.U23.18 (`PauseTime`'s `statusPath` resolves in `_notification_status()`),
  A.U23.30 (`float: true` ⇔ `ConfigSchema` float), A.U6.18 (identity/NTP submit labels), A.U6.28 + A.U18.38 (`bytes=true`
  set = `_RADIO_FIELDS` with no `HotspotPW` exception), A.S0930.20 (1) (`SystemCmd` options), A.U15.12 (SCD30 errcount
  expectations), A.U16.20 (read: `:182-210` builds unchanged).
- **Site**: new tests in `tests_scripts/test_buildgen_definitions.py` (all parametrised over `DEVICE_NAMES`).
- **Change**: one test per property: (a) the errcount `codes` block equals `buildgen/error_catalog.json`'s non-retired
  codes exactly; (b) `codeTones` equals the catalog's tones; (c) every field `codes` table equals the catalog's
  `status.<table>` and every `codes=` tag names a present table; (d) every field whose key ends in `TS` or is
  `NtpLastSync` carries `format: "epoch"` and no `unit`; (e) every sgp40 device's maintenance group has both backup
  timestamps with the two special values, field names equal to the keys `_sgp_maintenance_status()` returns (regex over
  `generate_device()` source); (f) each published logger key appears in exactly one errcount group across the whole
  definitions and `DNSSRV` sits in the networking section; (g) `PauseTime`'s `statusPath` resolves in the generated
  `_notification_status()` keys; (h) every `number` field carries `float: true` exactly when `extract_field_schemas()`
  types it `"float"`; (i) the networking `identity`/`ntp` groups carry "Apply & Reconnect"/"Apply & Resync"; (j) the
  `bytes=true` field set of `asy_wifi_service.py` equals the `ast`-read `_RADIO_FIELDS` (`HotspotPW` included: A.U18.38
  publishes it, the exception goes); (k) the `SystemCmd` options are exactly `_SYSTEM_CMDS` (`ast`, `src/asy_webserver_service.py`)
  in order, labels "Reset to defaults" and "Erase FRAM", no confirmation key in the group; (l) SCD30's errcount and
  readiness rows match its catalog entries (the three FRC readiness keys, A.U15.12). Key names follow A.U10.40.
- **Resolved**: A.U2.21's edit of the golden files falls away with A.U6.04 (its test compares with the catalog only).
- **Unit**: U23 (each property in its owner's unit: U2 (a), U6 (c)-(f), (i), (j at U18), U15 (l), U23 (b), (g), (h),
  S0930 (k) with U10).
- **Depends**: A.U2.01 catalog (GEN), A.U6.17-A.U6.28 tags (SRC/GEN), A.U10.40 (keys).
- **Blast carried by**: JS/mock halves → A.U6.27/A.U23.20/A.S0930.20 (4)-(5) (WEB).
- **Kind**: test

### M.TSC.041 Build errors replace silent drops; CLI and build agree on order
- **From**: A.U20.25 (`:247-255` silent drop → build error), A.U6.01 (`:430` CLI parity; new order tests),
  A.U20.17/M.TSC.008 (CLI error case `:442-448`).
- **Site**: `tests_scripts/test_buildgen_definitions.py:215-448`.
- **Change**: `test_missing_web_field_tag_for_a_schema_field_is_tolerated_but_field_is_absent` →
  `test_a_schema_field_without_a_web_tag_fails_the_build` (`BuildError` naming the field; a field tagged `hidden` is
  the accepted way to keep it off the website); new: `main()` output equals `generate_definitions()` of a graph-ordered
  model for every `DEVICE_NAMES` device and for `multi_instance.toml`; `_sensor_instance_specs()` raises on a model with
  an empty `construction_order` and one sensor instance; `:442-448` asserts one stderr line with `- fix: ` and no
  `Traceback`.
- **Resolved**: —
- **Unit**: U20
- **Depends**: M.GEN (A.U20.25 schema/tag rule, A.U6.01 ordering).
- **Blast carried by**: `hidden=` rows → {{web_tag}}; schema-ast raise → {{schema_ast}}.
- **Kind**: test
