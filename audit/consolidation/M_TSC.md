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
  `bytes=true` field set of `asy_wifi_service.py` equals `_RADIO_FIELDS`, which M.SRC_NET.075 writes as
  `schema_names(...)` over the radio schemas — the test resolves that call through `buildgen.schema_ast` (SRC_NET gap 3)
  (`HotspotPW` included: A.U18.38 publishes it, the exception goes); (k) the `SystemCmd` options are exactly `_SYSTEM_CMDS` (`ast`, `src/asy_webserver_service.py`)
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

## tests_scripts/test_buildgen_frozen_modules.py
### M.TSC.042 The frozen set is the closure of the generated module's imports
- **From**: A.U20.13, A.U24.66, M.TSC.001 (old module names in the expectations).
- **Site**: `tests_scripts/test_buildgen_frozen_modules.py:23-123`.
- **Change**: `:23-26` parametrised over `DEVICE_NAMES` (every declared driver's module in the set); `:29-31`
  (`>= CORE_MODULES`) → the set equals the closure of the generated module's imports and contains every module the
  generated source imports that has a file in `src/`/`ext/`; `:48-106` pass a small module source to
  `compute_frozen_modules(module_source, src_dir, ext_dir)` instead of synthetic models; new: every member is imported
  by the generated module or by another member (no stray name), and an `if TYPE_CHECKING: … else: import x` fixture
  includes `x`. Expected names use the renamed modules (`asy_system_service`, `asy_base_classes`,
  `asy_config_manager`, `asy_print_log`, `asy_api_response`, `asy_crc_checks`, `asy_captive_dns`).
- **Resolved**: —
- **Unit**: U20 (names from U10; devices U24).
- **Depends**: M.GEN.020.
- **Blast carried by**: `test_build_firmware.py:91-101` → M.TSC.031.
- **Kind**: test

## tests_scripts/test_buildgen_fuzz.py
### M.TSC.043 Seeded mutation fuzz: only success or `BuildError`
- **From**: A.U20.19 (3).
- **Site**: new `tests_scripts/test_buildgen_fuzz.py`.
- **Change**: `random.Random(<fixed seed>)`, 2,000 cases: mutations of `base_doc()` and of each `DEVICE_NAMES` TOML's
  parsed dict — delete a key, change a value's type (int/str/bool/list/table, written as real TOML by M.TSC.012), swap
  two pins, duplicate an instance, point a wiring value at a random label — each through `write_doc()` and
  `build_model()` + `build_construction_order()` + `generate_module_source()`; the only allowed outcomes are success or
  `BuildError`; anything else fails printing seed and case index. Host-I/O rule: every case rewrites ONE `tmp_path`
  file (no per-case file or directory creation; ≈ 2,000 × 1 KB rewrites of one inode per run).
- **Resolved**: —
- **Unit**: U20
- **Depends**: M.TSC.012, M.GEN.022/.028.
- **Blast carried by**: SPEC L.5 names the fuzz → A.U20.19 (SPEC).
- **Kind**: test

## tests_scripts/test_buildgen_generate.py
### M.TSC.044 Devices, fixtures and comments of the generator tests
- **From**: A.U24.66 (24 literals), A.U24.75 (`codegen`'s named test home; module-level tests), A.U20.19 (`:420, 430,
  440, 454` gain `"name_ext": ""`), A.U10.43 (`:415-446` `trigger_sec` → `trigger_s`, test names follow), A.U24.39
  (`:125` value check), A.U36.544 (`:59`, `:71` targets go with their tests), A.U36.004 (`:221-223` comment), A.U20.15
  (docstring/file names); read: A.U1.23 (`:44, :380, :557` parse/exist only), A.U33.03 (`:488` comment unaffected),
  A.U36.038 (asserts content, not order), A.U11.03/A.U11.S04 (no `_flush_pending_configs` pin), A.U6.21/A.U9.03/
  A.U18.33/A.U19.02/A.U19.10 (no pin on those lines).
- **Site**: `tests_scripts/test_buildgen_generate.py:1-130`, `:221-223`, `:405-457`.
- **Change**: docstring "End-to-end: buildgen.generate.generate_device() over every devices/*.toml plus the novel and
  multi-instance fixtures (SPECIFICATION.md Part L.1) - the validate -> sort -> generate pipeline from one TOML."; real-
  device tests parametrise over `DEVICE_NAMES` (ids = names); single-device text pins use the device a property selects
  (e.g. the one with `isl29125`, the bench device for `uart_link`); `:125` → the parsed build date is timezone-aware UTC
  and within one minute of the test's `datetime.now(UTC)`; `:221-223` → "# The implicit FRAM-wiring rule
  (SPECIFICATION.md A.7): every mandatory-infra module inherits the / # device's own FRAM chip, exactly like every
  FRAM-wirable [[instance]] - base_doc() already / # declares [device.wiring].fram_target = "fram", so this is the
  happy path." (≤ 3 lines); synthetic non-singleton instances carry `"name_ext": ""`; `trigger_s` everywhere.
- **Resolved**: —
- **Unit**: U24 (U10/U20/U36 pieces in their units).
- **Depends**: M.TSC.002, M.TSC.005.
- **Blast carried by**: —
- **Kind**: test

### M.TSC.045 Boot-entry pins: watchdog first, frozen path, buffer, two variants
- **From**: A.U20.02 (`:48-53`), A.U20.03, A.U20.04, A.U20.05, A.U20.15 (`:373-383`, `:541-560` file names), A.U11.05
  (read: the `WDT(` count moves to the boot entry), GEN gap 1; M.GEN.001, M.GEN.019.
- **Site**: `tests_scripts/test_buildgen_generate.py:48-53`, `:101-103`, `:373-381`, `:541-558`, new tests.
- **Change**: per device: the module has zero `WDT(` and the boot entry exactly one; the boot entry's first statements
  after the docstring are `from machine import WDT` and `watchdog = WDT(timeout=8000)` (AST); exactly one
  `sys.path.insert(0, ".frozen")`, after the watchdog assignment, with no import of a name outside `{"machine", "sys"}`
  before it; `micropython.alloc_emergency_exception_buf(<int ≥ 77>)` exactly once, before the device-module import;
  both variants compile, are equal up to the watchdog lines and the tail, carry `gc.threshold(32768)` after the
  device-module import; the no-autostart variant has no `WDT(` outside its printed string and no `asyncio.run(`. The CLI
  tests assert `sensortask_<device>.py`, `sensortask_<device>_main.py` and `sensortask_<device>_main_noautostart.py`
  exist (not `<device>_boot.py`).
- **Resolved**: boot-entry name `sensortask_<device>_main.py` (M.GEN.019, GEN gap 1) over A.U24.54's `<device>_boot.py`.
- **Unit**: U20 (U27 for the CLI exit idiom).
- **Depends**: M.GEN.001, M.GEN.019.
- **Blast carried by**: twin boot of the entry → {{gen_boot}}; hardware reflash checks → M.HW_BENCH.014.
- **Kind**: test

### M.TSC.046 `main()`, collectors and expected facts pinned per device
- **From**: A.U20.06 (`:56-97` replaced; `main()` call order), A.U11.10 (`_collect_setups()` order, no `gc.collect`),
  A.U10.10 (every logger store set up: scd30/neopixel/webserver in the list), A.U10.12 (`start_timers` two lists),
  A.U16.17 + A.U16.R03 (fram's starters in the collectors; the `fram_target`-less fixture `:266-285` still declares
  fram, so its collectors gain it), A.U32.06 (starters and names equal length, names unique), A.U15.12 (setup order gains
  scd30), A.U20.07 (expected boot sequence), A.U26.23 (`fram_backed_loggers`), A.U25.69 (signature pins hold),
  A.U11.08 (`:92` `import gc` reason); M.GEN.006, M.GEN.010, M.GEN.019.
- **Site**: `tests_scripts/test_buildgen_generate.py:56-97`, `:266-285`, new tests.
- **Change**: `:56-66` and `:70-97` → per device: `_collect_setups()` (AST) returns, in order, `fram.setup` (if
  declared), `sysfunct.setup`, `conn.setup`, `ntp.setup`, every `needs_setup` instance in construction order (fram
  skipped), `webserver.setup` last; the module contains no `gc.collect(` and no `feed_watchdog(` anywhere; `import gc`
  stays (its use is `gc.mem_free()` for `MemFree`). New: `main()`'s awaited calls (AST) are exactly `build_system`,
  `sysfunct.run_setups`, `sysfunct.start_tasks`, `sysfunct.start_timers`, `ntp.ntp_force_sync`,
  `sysfunct.supervise_tasks` in that order, with `boot_phase(BOOT_SETUP/TASKS/TIMERS/NTP/DONE)` between them;
  `main()`'s parameters are keyword-only `watchdog, cfg_path, debug, web_host, web_port`; `_collect_task_starters()`
  and `_collect_timer_starters()` include fram's when declared; `_collect_task_starters()` and `_collect_task_names()`
  have equal length and unique names; `expected_facts(model)["boot_sequence"]`'s setup part equals the bound-method
  list of `_collect_setups()` and its construction part equals `build_construction_order(model)`;
  `fram_backed_loggers` ⊇ {"SYSTEM"} exactly when `[device.wiring].fram_target` is set and holds no name of the FRAM
  instance itself.
- **Resolved**: A.U20.06 (5) "collectors exclude fram" vs A.U16.17/A.U16.R03 — fram included (M.GEN.010, OR89.a (5)).
- **Unit**: U32 (stage U20 for everything but the task-name row; U26 `fram_backed_loggers`).
- **Depends**: M.GEN.006, M.GEN.010, M.GEN.019.
- **Blast carried by**: twin recorded boot sequence (L2) → A.U20.07 (TWIN); `_collect_setups()` count in the
  contiguity test → {{contiguity}}.
- **Kind**: test

### M.TSC.047 Construction lines follow the new constructor shapes
- **From**: A.U5.03 (`fram=` → `log=` at `:151, :230-233, :268-281, :433, :444`; new: every constructor's `log=` is its
  FRAM target's `LogConfig`, the FRAM manager's FRAM-less), A.U5.04 (webserver config objects; `:578-596`
  `_webserver_keywords`), A.U5.06 (`:183-184` signals at construction), A.U5.07 (`:178-179`, `:343-351` `ext_led=`
  kwarg, no `set_ext_led`), A.U5.09 + A.U18.40 (`WifiConfig`), A.U5.11 (`:183-184` SGP40 `ValueRef`/`SgpBackup`),
  A.U15.12 (SCD30 `cfg_path=cfg_path`), A.U18.10 (networking `SettingsGroup(ntp, ("DNSFallback",))`), A.U18.38
  (identity group gains `"HotspotPW"`), A.U20.08 (every bus before any instance), A.U20.22 (`:220-240`, `:266-287` follow;
  new synthetic tag-target case), A.U20.41 (class names), A.U20.42 (`"… | None" = None` pins → declared globals),
  A.U28.41 (`:411`), A.U24.44 (provider positions, GEN gap 2), A.S0930.02 (CRC16 case), A.U16.20 (read: `:132-190`
  build unchanged), A.U11.S01 (read: no `_notification_led_callback` text pin), A.U28.29 (via A.U28.41).
- **Site**: `tests_scripts/test_buildgen_generate.py:132-370`, `:405-457`, `:578-596`, new tests.
- **Change**: expected text and AST pins follow M.GEN.005/.009/.012: `log=<LogConfig var>` instead of `fram=`; `conn =
  WifiService(WifiConfig(<hostname>, hotspot_password=_HOTSPOT_PW_DEFAULT, …), ext_led=<led var or None>, log=…)`;
  `_HOTSPOT_PW_DEFAULT = '<toml value>'` is a module constant and `hotspot_password=_HOTSPOT_PW_DEFAULT` its use
  (`:411`); `NTPClient(conn.get_wifi_mode_lock(), conn.network_available_locked, conn.get_dns_server_ip,
  NtpTiming(...))` and `SystemService(ntp.ntp_issynced, …)` — the provider positions also asserted for the two
  `make_ntp()` bodies in `tests/test_ntp_fram_system_integration.py` and its sibling (A.U24.44's check, parsed by
  `ast`); notification signals passed at construction (no `register`/`finalize` line); SGP40 with `ValueRef`/`SgpBackup`;
  SCD30 with `cfg_path=cfg_path`; the webserver's `ServingLimits` carries the stated `max_connections` (absent → the
  constructor default); networking settings rows as M.GEN.009; every `[bus.*]` construction precedes the first
  instance; globals annotation-only; a synthetic `src_dir` copy whose `asy_system_service.py` wiring tag targets `store`
  emits `store=` on the `sysfunct` line; the bench device's TOML (selected by its `uart_link` pair) copied to
  `tmp_path` with `crc = "crc16"` on both ends generates `crc=CRC16()` on both UART bus lines and imports `CRC16`,
  every shipped device's text has no `crc=`.
- **Resolved**: A.U24.44 asserts HEAD's `conn.network_available`; A.U10.18 renames it (M.GEN.005 Resolved (c), GEN
  gap 2) — the pin uses `network_available_locked`. A.U24.44 names no file for its L0 check; it lives here, generating
  in memory (codegen's named test home, A.U24.75) rather than reading `build/generated_src/`.
- **Unit**: U28 (stages U5, U10, U15, U18, U20, U24 as each constructor shape lands).
- **Depends**: M.GEN.005, M.GEN.009, M.GEN.012.
- **Blast carried by**: —
- **Kind**: test

### M.TSC.048 Generated-module hygiene: no suppression, resolvable names, compiled
- **From**: A.U20.14 (no `# type: ignore`/`# noqa`; strippable `TYPE_CHECKING`), A.U20.16 (top-level names allowed;
  every load resolves), A.U20.18 (4) (invalid template → `BuildInternalError`), A.U20.17 (`:497-538` →
  `BuildInternalError`), A.U20.30 (`:460-466` moves to `test_buildgen_validate.py`), A.S0930.20 (3) (generated
  `_system_cmd_callback`), A.U27.29/M.TSC.008 (CLI error cases `:393-402`, `:561-575`).
- **Site**: `tests_scripts/test_buildgen_generate.py:460-575`, new tests.
- **Change**: per device and both fixtures: the module and both boot entries contain no `# type: ignore` and no
  `# noqa`; the module through `_strip_type_checking` has no `TYPE_CHECKING` name left and still compiles; every
  top-level `def`/`async def` is `build_system`, `main` or in L.2's emitted list (`_sgp_maintenance_status_` prefix
  matched); every `ast.Name` load in a generated function that is not a parameter/local resolves to a module global,
  import or builtin; a monkeypatched template emitting invalid Python raises `BuildInternalError`; `:497-538` expect
  `BuildInternalError`; `test_unknown_warn_signal_is_a_fail_loud_build_error` leaves this file
  ({{validate_warn}}); `_system_cmd_callback`'s compared string constants (AST) equal `_SYSTEM_CMDS` (read from
  `src/asy_webserver_service.py`), every branch `return`s its call, the two new branches call
  `sysfunct.reset_to_defaults()`/`sysfunct.erase_fram()`; CLI error cases assert one stderr line with `- fix: `, no
  `Traceback`, exit 1.
- **Resolved**: —
- **Unit**: U20 (S0930 row with U10's command words).
- **Depends**: M.GEN.003, M.GEN.008, M.GEN.019, M.GEN.022.
- **Blast carried by**: ruff on the generated tree → A.U28.41/A.U27.09 (TOOL/SCR); liveness of the generated-scope
  exemption → {{ruff_live}}.
- **Kind**: test

## tests_scripts/test_buildgen_limits.py
### M.TSC.049 `@limits` matrix complete; real drivers' limits and the FRAM set agree
- **From**: A.U20.37 (1) (SPEC L.5 dimensions; new name-shape and typo-boundary cases), A.U20.24 (3) (`nan`, `inf`,
  `-inf` rejection rows, M.GEN.037), A.U15.10 (`:201-203` gains `asy_scd30_driver.py`; new
  `test_parse_limits_real_scd30_driver`), A.U16.20 (new `test_fram_max_size_limits_match_the_known_product_ids`),
  A.U10.43 (`trigger_sec` → `trigger_s`), A.U24.66 (4 literals).
- **Site**: `tests_scripts/test_buildgen_limits.py:188-203`, new tests.
- **Change**: the value dimension gains `nan`/`inf`/`-inf` rows each raising `BuildError` with
  `rule="tag.non-finite-number"`; `test_parse_limits_real_scd30_driver` asserts `LimitField("trigger_s", None, 1,
  1800)` beside the BMP3xx case; the real-driver list `:201-203` includes `asy_scd30_driver.py` and
  `asy_fram_manager.py`; `test_fram_max_size_limits_match_the_known_product_ids` parses `asy_fram_manager.py`'s
  `@limits max_size` with `parse_limits()` and equals it to `_KNOWN_PRODUCT_IDS`' keys read by `ast` from
  `src/asy_fram_driver.py`; plus `test_parse_limits_accepts_every_name_shape` and
  `…_leaves_a_word_outside_the_typo_boundary_alone` (as `test_buildgen_wiring.py:58, :145`).
- **Resolved**: —
- **Unit**: U20 (U15 SCD30, U16 FRAM rows in their units).
- **Depends**: M.GEN.037, A.U15.10/A.U16.20 tags (SRC_SENS/SRC_CORE).
- **Blast carried by**: the build-time rejections → `test_buildgen_validate.py` ({{validate_limits}}).
- **Kind**: test

## tests_scripts/test_buildgen_pico_gpio.py
### M.TSC.050 One home for the pin-table tests
- **From**: A.U24.75 (1) (new file), A.U20.09 (its pin-table tests land here; M.GEN.042).
- **Site**: new `tests_scripts/test_buildgen_pico_gpio.py`; `tests_scripts/test_buildgen_validate.py` (moved tests).
- **Change**: holds A.U20.09's `test_newly_legal_pin_is_accepted` and `test_pin_table_agrees_with_micropython_pin_macros`
  plus every existing `test_buildgen_validate.py` test exercising `pico_gpio` directly (the wireless-reserved test
  `:295-` and the role-transposed tests); module-level functions, no `Test*` class; `test_buildgen_validate.py` keeps
  only the pin tests going through `build_model()`.
- **Resolved**: —
- **Unit**: U24 (U20 tests created in `test_buildgen_validate.py`, moved here in U24).
- **Depends**: M.GEN.042.
- **Blast carried by**: SPEC E.2.1 file map → A.U24.75 (SPEC).
- **Kind**: test

## tests_scripts/test_buildgen_reproducible.py
### M.TSC.051 Generated build inputs are byte-identical across hash seeds
- **From**: A.U20.36.
- **Site**: new `tests_scripts/test_buildgen_reproducible.py`.
- **Change**: for every device in `DEVICE_NAMES` and both fixtures, a CPython subprocess run twice with
  `PYTHONHASHSEED=0` and `=4242` prints one JSON document of `generate_device(…, build_date="2026-01-01T00:00:00Z")`
  (module source, both boot entries), `compute_twin_wiring()`, `expected_facts()`, `generate_definitions()` and
  `sorted(frozen_modules)`; the two outputs are byte-identical, a difference names the device and first differing line.
  stdout only (nothing written).
- **Resolved**: —
- **Unit**: U20
- **Depends**: M.GEN.019.
- **Blast carried by**: manifest/image reproducibility → {{frozen_inputs}}.
- **Kind**: test

## tests_scripts/test_buildgen_source_agreement.py
### M.TSC.052 Restated `src/` facts and owner-kept catalogs pinned to their sources
- **From**: A.U20.27 (2), (5); A.U33.01/A.U33.03 (read: SPEC K.3/L.6.6 cite this file).
- **Site**: new `tests_scripts/test_buildgen_source_agreement.py`.
- **Change**: (a) `_FIELD_SCHEMA_LEN` equals the element count of `asy_config_manager.FieldSchema`'s `tuple[...]`
  alias (AST); (b) the "5 minutes" in `SystemCmd`'s `mempause` label equals `pause_permanent_storage(300)` in the
  generated `_system_cmd_callback()`; (c) every driver `driver_registry` resolves (each `src/asy_*_driver.py` with one
  reader class, plus `_OVERRIDES`) has a `buildspec.REQUIRED_TOML_FIELDS` row and, if bus-attached, a
  `BUS_KIND_BY_DRIVER` row; (d) every driver and mandatory module has an `_ERRCOUNT_CATALOG` row and, where its class
  owns a `cfgmgr` (AST), a `_CFGMGR_LABEL` row; (e) the BMP3xx catalog/group labels read "BMP3xx" (family name).
- **Resolved**: —
- **Unit**: U20
- **Depends**: M.GEN.016, M.GEN.025, M.GEN.026.
- **Blast carried by**: SPEC K.3/L.6.6 → A.U33.01/A.U33.03 (SPEC).
- **Kind**: test

## tests_scripts/test_buildgen_tag_comments.py
### M.TSC.053 Tag scanner: lookup registration, column-0 comments, predicates
- **From**: A.U20.24 (1)-(2), A.U20.39 (`looks_like_tag_payload()` call sites → family predicates), A.U20.37 (`:307,
  :325, :329, :340` accept sides assert), A.U5.11 (`:369` value-wiring grammar), A.U10.43, A.U24.66 (19 literals).
- **Site**: `tests_scripts/test_buildgen_tag_comments.py` (whole file; `:307-369`).
- **Change**: new AST test: every buildgen module calling `check_for_near_miss_tags` passes a non-empty spec tuple, and
  each `KNOWN_TAG_NAMES` entry is fetched by exactly one module (`specs_for()`); `specs_for("nope")` raises
  `BuildInternalError`; the scan dimension gains a column-0 comment inside a function body (inside) and after a
  function (module level); calls to `looks_like_tag_payload()` become `tag_comments._looks_like_requires_payload()`
  (no-spec default) and `spec.looks_like_payload()` (named family), same inputs and goals; `:307, :325, :329, :340`:
  `check_for_near_miss_tags()` returns `None` and the same token list with one sigil typo raises; `:369` follows the
  `@value-wiring` grammar (field, kwarg, required); device literals → fixture/derived.
- **Resolved**: —
- **Unit**: U20 (U5 grammar, U10 suffix, U24 devices).
- **Depends**: M.GEN.047, M.GEN.049.
- **Blast carried by**: every real `src/` file still parses to the same tags → each family's own test file.
- **Kind**: test

## tests_scripts/test_buildgen_twin_wiring.py
### M.TSC.054 The twin plan: one producer, addresses from drivers, explicit loading <!--@twin_wiring_main-->
- **From**: A.U20.28 (2) (`:13` import, `:95-99` addresses from driver constants; `:110-127` → `BuildError` rule),
  A.U25.25 (`:44-62` → `configure_wiring(plan)`; plan gains `pins`), A.U17.18 (bus-id `uart` pair), A.U16.20 (`:141,
  :152` → `== 0x40000`), A.U24.13 (fixture pops every module it added), A.U24.66 (`:48` → `DEVICE_NAMES`), A.U24.73 +
  A.U20.32 (`Any` and the ANN401 exemption), A.U6.04 (`:31` comment), A.U5.03 (read: no `fram=` in the plan); dropped:
  A.U25.44's "the fixture's one test goes with A.U25.25" (A.U25.25 moves it; the fixture has a second user, `:102-107`);
  read: A.U33.03 (`:114-116` comment unaffected), A.U36.513 (the generated-boot docstring names this file).
- **Site**: `tests_scripts/test_buildgen_twin_wiring.py:1-160`.
- **Change**: docstring (≤ 3 lines) "Tests for buildgen.twin_wiring (SPECIFICATION.md Part L.4): the plan's shape and JSON
  round trip per device, addresses read from the drivers, the bus pins and UART pair, and the twin loading an
  explicit plan."; imports `fixed_address`; the fixture `digital_twin_machine` records `before = set(sys.modules)`
  and after `yield` pops every key not in it (in `finally`), typed `Iterator[ModuleType]`, comment `:31` "…plain
  `import machine` under CPython works." (no golden reference); `:44-62` → per `DEVICE_NAMES`:
  `machine.configure_wiring(compute_twin_wiring(build_model(...)))` then the twin's current plan equals it, and before
  any configure `_current_wiring_plan()` raises `RuntimeError("no wiring plan configured …")`; `:95-99` → each plan
  address equals the address constant read by an independent `ast` read of the driver file; `:110-127` → a bus driver
  with no address constant raises `BuildError` with `rule="twin.no-address-rule"`; new: the plan's `pins` equal each
  `[bus.*]` table's pin keys, and a device's `uart` equals `{"initiator_bus": <bus of role initiator>,
  "responder_bus": <bus of role responder>}` read from its TOML (`None` without a pair); `:141, :152` → `== 0x40000`;
  no `Any`.
- **Resolved**: A.U25.25 vs A.U25.44 on the `:44-62` test — moved, not deleted (above).
- **Unit**: U25 (stages U17 pair, U20 addresses, U24 fixture/typing/devices).
- **Depends**: M.GEN.043, A.U25.25 (`digital_twin/machine.py`, TWIN).
- **Blast carried by**: contract test → {{twin_contract}}; `pyproject.toml:295` ANN401 entry removal → TOOL (Gaps).
- **Kind**: test

## tests_scripts/test_buildgen_validate.py
### M.TSC.055 Fixture name, device loops, accept-side assertions, comments
- **From**: A.U20.37 (2)-(3) (`_build()` default name `"dev"` → `"fixture"`; the 30 no-assert accept tests gain their
  assertion), A.U24.51 (`:1326-1331`, `:1730-1738` → `DEVICE_NAMES`), A.U24.66 (26 literals), A.U20.19 (`:479, 500,
  745, 753, 760, 768` gain `"name_ext": ""`; `:549-650` collision guards keep a one-line extension-point comment),
  A.U10.43 (`trigger_sec` keys and test names), A.U24.75 (pin tests out), A.U10.30 (`:5`, `:1593` `importlib`), A.U2.23
  (`:1257`, `:1268` code-number comments), A.U36.004 (`:935-936`), A.U36.544 (`:718` "(Phase 2)" dropped), A.U0.28
  (`:1729` tag); read: A.SDEP.08 (`:1576` fixture literal stays, a synthetic input), A.U7.26 (`:1208` stays a skip),
  A.U28.29 (the S105/S106 per-file comment is `pyproject.toml`'s), A.U20.41 (staged consumer file names hold),
  A.U33.01 (`:362-374` the named error holds).
- **Site**: `tests_scripts/test_buildgen_validate.py:1-60`, the accept tests at `:38, 190, 200, 232, 241, 408, 428,
  716, 733, 751, 766, 772, 830, 845, 851, 864, 878, 884, 928, 970, 981, 1017, 1079, 1088, 1180, 1326, 1334, 1386, 1481,
  1524`, `:549-650`, `:718`, `:935-936`, `:1257`, `:1268`, `:1326-1331`, `:1593`, `:1729-1738`.
- **Change**: `_build()` and every `write_doc(tmp_path, …)` use the device name `"fixture"`; each accept test asserts
  what it accepted (A.U20.37 (2)'s list: instance keys equal the doc's and `build_construction_order()` succeeds;
  stated addresses/buses present; `spec.fields[...]` and `spec.limits_schema` carry the tag's set/range;
  `spec.wiring[<field>] == {"default": True, …}` and the rendered `_Default<Field>(…)` call; absent optional fields
  absent from `spec.wiring` and the rendered call; `spec.requires_tags`; the link roles and buses; the effective
  connection ceiling via `device_max_connections()`; the bus/instance tables); every-device loops are
  `@pytest.mark.parametrize("device", DEVICE_NAMES)` with `device_toml(device)`; `:5` `import importlib.util` goes and
  `:1593` patches `"buildgen.validate.importlib.util.spec_from_file_location"` by dotted name (no `importlib` import
  in the test, so the import-graph check needs no exception for it); `:1257`, `:1268` cite catalog names, not
  numbers; `:935-936` → "(sysfunct/conn/ntp/webserver, the implicit FRAM-wiring / # rule of SPECIFICATION.md A.7)";
  `:718` drops "(Phase 2)"; `:1729` sentence gains "; the ceiling value itself is the agent's sweep result (agent,
  2026-09-22)"; the direct `pico_gpio` tests (`:279-292`, `:295-`, role-transposed) move to
  `test_buildgen_pico_gpio.py` (M.TSC.050).
- **Resolved**: A.U10.30 offers "patch without importing" or "list in F.1"; the first is taken (no new named exception).
- **Unit**: U24 (U0 tag; U2 comments; U10 suffix/import; U20 assertions, fixture name, `name_ext`; U36 comments).
- **Depends**: M.TSC.002, M.TSC.005.
- **Blast carried by**: —
- **Kind**: test

### M.TSC.056 Device-table, field and range rejections <!--@validate_limits--><!--@validate_trigger--><!--@validate_defaults-->
- **From**: A.U20.34 (numeric `[device]`/bus ranges), A.U31.08 (`bus.i2c-timeout-max`), A.U16.20 (`max_size = 0x1000`),
  A.U15.10 (SCD30 `trigger_s` range, shaped as `:757-769`), A.U20.18 (`irq_pull_up` type, `poll_idle_ms` range,
  compile → `BuildInternalError`), A.U20.21 (required keyword-only `_Default*` parameter), A.U26.01 (`bench` key
  accepted), A.U20.19 (`hardware_family` key; `instance.name-ext-missing`), A.U6.29 (hostname host-label corpus; a
  `[device].name` with a space and with a dot), A.U20.17 (`"internal:"` matches → `BuildInternalError`), A.U20.20
  (`{source, field}` names a real `get_data()` field), A.U20.09 (pin-table tests, created here, moved by A.U24.75),
  A.U20.27 (read: hostname/WPA2/NTP-tick cases hold with the same numbers), A.U10.43 (`trigger_sec` refused as unknown).
- **Site**: `tests_scripts/test_buildgen_validate.py:100-480`, `:757-769`, new rows.
- **Change**: new rows, each asserting the `BuildError`'s `rule`, `(field, instance)` and the `- fix:` range: `hotspot_time_min`
  0 and 35792 refused, 1 and 35791 built; `conn_fail_to_hotspot` 0 refused; `ntp_retry_max_s` one above
  `(2**30 - 1) // _NTP_BACKOFF_MULT` refused; I2C `frequency` 0 and 1000001 refused; `timeout` 0 refused; `baudrate` 0
  and 7812501 refused; `rxbuf` 31 and 32767 refused, the edges built; I2C `timeout` at the device's bound accepted and
  one above refused (with and without a `uart_link`); FRAM `max_size = 0x1000` refused naming the legal set; SCD30
  `trigger_s` 0/1801/−1 refused, 1/1800/3 built; `irq_pull_up = "yes"` refused; `poll_idle_ms` out of range refused; a
  synthetic `_Default*` with a required keyword-only parameter rejects a sub-table missing it; `[device] bench = true`
  accepted, `bench = "yes"` refused; `[device] hardware_family = ""` refused, a non-empty string accepted; a
  non-singleton instance without `name_ext` refused (`instance.name-ext-missing`); host-label corpus rows refused
  (A.U6.29's shared corpus) and a name with a space or dot refused; `warn_co2 = {source = "scd30", field = "Co2"}`
  refused naming `CO2` among the choices, `temperature_source = {source = "bmp3xx", field = "Temp"}` built, a producer
  whose `get_data()` is not a namedtuple (synthetic `src_dir` copy) refused with `source.fields-unreadable`; a TOML
  still using `trigger_sec` refused as an unknown key.
- **Resolved**: —
- **Unit**: U31 (A.U31.08 rows; stages U10, U15, U16, U20, U26 in each owner's unit).
- **Depends**: M.GEN.026-.031, M.GEN.042.
- **Blast carried by**: the contract table rows → {{errcontract}}.
- **Kind**: test

### M.TSC.057 UART-link rules: CRC mode, single owner, baud pair, poll and timeout ceilings
- **From**: A.S0930.01 (crc cases), A.U20.01 (single owner; responder without initiator), A.U17.32 (baud mismatch),
  A.U17.21 (poll ceiling, timeout ceiling, source-read variant), A.U13.17 (`:1290-1299` defaults comment, `rxbuf = 52`
  refusal; `:1301-1310` replacement), A.U2.23 (`:1257`, `:1268`, in M.TSC.055); read: A.S0930.01 (`:1240-1384` hold —
  absent `crc` is `"none"`), A.U17.21 (`:1255-1287` hold).
- **Site**: `tests_scripts/test_buildgen_validate.py:1236-1384`, new rows.
- **Change**: `crc = "crc8"`, `16`, `"CRC16"`, `["crc16"]` each refused naming the legal set with `(field, instance) ==
  ("crc", label)`; a `none`/`crc16` pair refused naming both labels; `crc16`/`crc16` builds; a CRC pair at
  `baudrate` 9600 and `poll_wait_ms` 1 checks the per-poll `rxbuf` floor with the 2-byte trailer counted;
  `test_uart_link_responder_with_no_initiator_is_rejected` (0/1) and `test_uart_link_pair_on_one_bus_is_rejected`
  (both labels, "point-to-point", `rule="bus.uart-shared"`); uart1 at 9600 against uart0 at 115200 refused naming both
  buses, equal rates built; `poll_wait_ms` 9 builds, 10 and 0 refused with `(field, instance) == ("poll_wait_ms",
  "uart_link_init")`; a `tmp_path` `src/` copy with `UartLinkExerciser`'s `timeout` default 89,478,486 refused naming
  the ceiling, 89,478,485 built; `:1290-1299` comment "rxbuf 256, poll_wait_ms 2, poll_idle_ms 50", its refusal case
  `rxbuf = 52`; `:1301-1310` → `test_an_unstated_poll_idle_ms_is_read_from_the_driver_source`: a `tmp_path` `src/` copy
  whose `asy_uart_driver.UART` default reads `poll_idle_ms: int = 975` builds (2 × 2 + 975 + 21 = 1000) and `976` is
  refused matching `poll_idle_ms 976`, `poll_idle_ms` unstated in the TOML.
- **Resolved**: A.U13.17's replacement (poll 464/465) fails A.U17.21's single-digit poll check before its floor; the
  source-copy form A.U17.21 writes is taken (its own AC note amends A.U13.17's test).
- **Unit**: U17 (stages U13 comment/defaults; S0930 CRC rows with A.S0930.01's unit).
- **Depends**: M.GEN.027, M.GEN.029; A.U13.17/A.U17.20 driver constants (SRC_UART).
- **Blast carried by**: twin CRC boot → {{gen_boot}}; UART changelog entries → A.U13.17/A.S0930.01 (SRC_UART).
- **Kind**: test

### M.TSC.058 Connection-ceiling and lwIP-ensemble cases follow the new shapes
- **From**: A.U14.30 (`:1489-1495`, `:1502` expected messages hold — the check and its message are unchanged), A.U5.04
  (`:1493-1495`, `:1614-1658`, `:1719-1725` staged webserver source follows the three config objects), A.U5.10
  (`:1628-1658` NTP timing group), A.U27.37 (new: by-name ceiling helper equals the path form per derived device),
  A.SDEP.14 (read: ensemble cases are the re-verify's coverage).
- **Site**: `tests_scripts/test_buildgen_validate.py:1480-1738`.
- **Change**: `_webserver_src()` and the staged sources write `WebserverService(app, *, routes, serving, static, log)`
  with `ServingLimits(max_connections=…)` defaults, so `webserver_init_default(src_dir, "max_connections")` reads
  through the config object as M.GEN.026 defines; the NTP staged source takes `NtpTiming`; new
  `@pytest.mark.parametrize("device", DEVICE_NAMES)` test: `device_max_connections_by_name(device)` equals
  `device_max_connections(device_toml(device), src)`; message pins of the lwIP ensemble unchanged.
- **Resolved**: —
- **Unit**: U27 (stage U5 constructor shapes).
- **Depends**: M.GEN.026, A.U27.37 (SCR/GEN).
- **Blast carried by**: —
- **Kind**: test

### M.TSC.059 Wiring rows follow the construction-time APIs <!--@validate_warn-->
- **From**: A.U5.03 (`:951-966` staged tag text "… log optional kwarg"), A.U5.07 (a `setter` wiring tag is rejected as
  unknown), A.U5.11 (`:624-628`, `:1173-1190` value-wiring cases), A.U20.30 (`test_unknown_warn_signal_is_a_fail_loud_build_error`
  moves here; `warn_co2` under an `scd30` instance rejected), A.U20.41 (read).
- **Site**: `tests_scripts/test_buildgen_validate.py:600-1190`.
- **Change**: staged tag text reads `FramManager log optional kwarg` (class name per A.U10.38); the setter-mode case
  asserts a `setter` mode is refused as an unknown wiring mode; value-wiring cases use the `{source, field}` →
  `ValueRef` grammar (field, kwarg, required); new: `warn_foo` on notification refused at validation, `warn_co2` on an
  `scd30` instance refused (`warn_*` legal only on notification).
- **Resolved**: —
- **Unit**: U20 (stage U5).
- **Depends**: M.GEN.030, M.GEN.036, M.GEN.048, M.GEN.049.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_buildgen_value_wiring.py
### M.TSC.060 `@value-wiring` matrix complete for the new grammar
- **From**: A.U20.37 (1) (L.5 dimensions; `test_parse_value_wiring_accepts_every_name_shape`,
  `…_leaves_a_word_outside_the_typo_boundary_alone`), A.U5.11 (grammar: field, kwarg, required), A.U15.16, A.U24.66.
- **Site**: `tests_scripts/test_buildgen_value_wiring.py` (whole file).
- **Change**: cases follow M.GEN.049's grammar; the two new tests (plain, underscored, digit-bearing field and kwarg
  names; a word outside the typo boundary left alone); device literals → fixture.
- **Resolved**: —
- **Unit**: U20 (stage U5).
- **Depends**: M.GEN.049.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_buildgen_version.py
### M.TSC.061 The version test pins the form, never the value
- **From**: A.U20.31 (G8/R17), A.U36.519 (read: the `version.py` docstring is M.GEN.021's); dropped: A.U37.11's test
  edit (`:24-27` → `test_release_values_match_the_specification` asserting `"2.0"`) — see Resolved.
- **Site**: `tests_scripts/test_buildgen_version.py:1-38`.
- **Change**: docstring → "Tests for buildgen.version (SPECIFICATION.md Part L.7): the two version constants are
  well-formed and the build date is a real UTC timestamp; bumps are by hand."; `:10-12` comment → "# <major>.<minor>,
  optionally a|b|rc<N> (e.g. 2.0b0, 2.1rc1, 2.1): enough to catch a stray space or a missing digit before it
  ships."; `_VERSION_RE` unchanged; `test_starting_values_match_the_plan` (`:24-27`) goes; new table test: `2.0b0`,
  `2.1`, `10.12rc3` accepted; `2.0 b0`, `2.0.1`, `2.0.dev1`, `v2.0` rejected. The release value `"2.0"`
  (M.GEN.021) passes the form tests.
- **Resolved**: A.U20.31 (U20, register G8/R17 Req "a bump edits no test") removes the value pin; A.U37.11 (U37)
  re-adds one as a blast clause. The register requirement settles it: a value pin makes every bump edit a test, which
  G8/R17 forbids — A.U37.11's test half is dropped (its version values, L.7 text and README section stand,
  M.GEN.021). M.GEN.021's blast pointer `test_buildgen_version.py:24-27 → A.U37.11 (TST)` is answered by this
  change.
- **Unit**: U20
- **Depends**: —
- **Blast carried by**: SPEC L.7 scheme statement → A.U36.519 (SPEC).
- **Kind**: test

## tests_scripts/test_ci_workflow.py
### M.TSC.062 One L0 check pins the workflow's standing rules
- **From**: A.U28.08, A.U28.07/A.U6.12 (web filter inputs; A.U6.12's filter test folds in), A.U28.06 (device-matrix
  equality moves here from `test_device_tomls.py:271-282`), A.U28.17 (rule 8), A.U28.43 (rule 9); read: A.U28.11
  (CLAUDE.md names this file), A.U28.37 (SPEC B.10 names it).
- **Site**: new `tests_scripts/test_ci_workflow.py` (regex over the text, no YAML parser).
- **Change**: one test per rule, each naming the job and the fix: (1) every `needs:` edge is read through
  `needs.<job>.outputs`/`.result`, or the job's `if:` holds `!cancelled()`, or a comment line in the job says
  "success-gated on purpose" (`fail-fast` never counts); (1a) `unit-tests`, `unit-tests-gc-threshold`,
  `firmware-build-verify`, `web-unit-tests` carry `!cancelled()`; `digital-twin-e2e` needs `unit-tests` without it;
  (2) the `web:` filter lists `src/**`, `buildgen/**`, `devices/**`, `digital_twin/**`, `toolchain/**`, `ext/**`,
  `.github/workflows/ci.yml`, `.github/actions/**`, `pyproject.toml`, `uv.lock` and every path it lists today; `base:`
  reads `steps.base.outputs.sha`; the `web` output falls back to `'true'` when that SHA is empty on a push; (3) every
  `uses:` outside `actions/*` and `./` is `@<40 hex>` followed by `# v<major>.<minor>.<patch>`; (4) no `fetch-depth`,
  no `submodules:`; (5) no `continue-on-error` on a step whose `run:` starts `scripts/test.sh`, `npm run test`, `node
  scripts/cross_browser_smoke.mjs`, `scripts/run_digital_twin_ci.sh` or `uv run pytest`; (6) the toolchain action's
  cache key hashes `toolchain/versions.toml`, `toolchain/setup_toolchain.py`, `toolchain/micropython_overrides.py` and
  `steps.ident.outputs.id`, its description names exactly the jobs using it, no job repeats a build-if-missing block;
  (7) both device matrices read `fromJSON(needs.devices.outputs.list)`; (8) the cross-browser step passes
  `--require-all-engines`; (9) `web-lint-and-typecheck` runs `npm run lint:html:built`.
- **Resolved**: A.U6.12 (U6) adds the definitions sources to the filter; A.U28.07 (U28) rewrites the filter whole —
  one check, U28's list (a superset).
- **Unit**: U28
- **Depends**: A.U28.07-.43 (`ci.yml`, TOOL).
- **Blast carried by**: `test_device_tomls.py:271-282` removal → {{device_tomls}}.
- **Kind**: test

## tests_scripts/test_citations.py
### M.TSC.063 Every citation resolves; old legacy paths excluded by one prefix <!--@citations-->
- **From**: A.U0.08 (check), A.U1.09 (the four pre-move exclusions → `legacy/`), A.U37.02 (allow-list reading goes),
  A.U0.10 (read: CLAUDE.md names the check).
- **Site**: new `tests_scripts/test_citations.py`.
- **Change**: scans every tracked text file except `legacy/` (U0: `python/`, `modules/`, `html_raw/`, `dev_legacy/`,
  `build-*.sh`, `update_and_install.txt` until U1), `arduino/`, `ext/`, `datasheets/`, `audit/`,
  `PROJECT_AUDIT_PLAN.md`, lock files; fails on (a) a repo path token that does not exist (upstream roots, absolute
  and `$VAR` paths skipped; `datasheets/` checked only with the submodule initialised, else one printed notice); (b) a
  SPEC Part/section citation whose heading does not exist; (c) a BACKLOG item citation whose numbered item does not
  exist; (d) an undefined label (`Session N`, `Step N`, `WP[1-8]`, `Topic N`, `decision N`, `measure [AB]`, `Phase N`,
  and the audit's own ID forms after close); (e) an `archive §N` citation passes while `12640c2` is an ancestor
  (skipped with a notice in a shallow clone). Staged: U0 with `_citation_allowlist.txt` (`path<TAB>token`, shrink-only
  second test); U1 replaces the six pre-move exclusions by `legacy/`; U37 drops the allow-list reading and its test.
  The `audit/` and `PROJECT_AUDIT_PLAN.md` exclusions go in phase D's close commit (the paths are deleted then).
- **Resolved**: —
- **Unit**: U37 (stages U0, U1).
- **Depends**: M.TSC.009.
- **Blast carried by**: the citing sites → A.U36.544 (DOC/SPEC); `.github` shallow-clone behaviour → (e)'s notice.
- **Kind**: test

## tests_scripts/test_code_conventions.py
### M.TSC.064 Code conventions over `src/` and generated modules
- **From**: A.U10.47; SRC_SENS GAP-3 (`voc_algorithm.py` exempt from D.15 order); A.U36.542 (read: SPEC 0.4 catalog names
  this file); A.U36.038 (D.15 checks widen beyond `src/` — its own checks).
- **Site**: new `tests_scripts/test_code_conventions.py`.
- **Change**: parses every `src/*.py` and every generated module built into `tmp_path` over `DEVICE_NAMES`; fails on
  (1) a module with an `async def` in its public API lacking the `asy_` prefix (generated `sensortask_<device>`
  modules exempt), or one with none carrying it (`math_helpers.py`, `voc_algorithm.py` stay unprefixed); (2) `_NAME =
  const("<X>")` whose measurement namedtuple type name differs from `<X>`; (3) a `get_task_starters()` method not named
  `start_asy_*`, a `get_timer_starters()` method not `start_timer`/`start_*_timer`, a task coroutine not `_*_loop`;
  (4) an `err_s`/`wrn_s` call passing its number positionally or without `errno=`/`wrnno=`; (5) `print(` outside
  `asy_print_log.py`; (6) `assert` in `src/` and in generated modules (the generated narrowing asserts are gone,
  M.GEN.004/A.U20.42, so no name exemption remains); (7) D.15 order in every `src/` class and module-level function
  list, `src/voc_algorithm.py` exempt by name (a literal port keeps the upstream operation order, M.SRC_SENS.018);
  (8) a quoted annotation naming no `TYPE_CHECKING` symbol. One `tmp_path` negative copy per rule.
- **Resolved**: A.U10.47 (6) exempts the generated asserts "until U20 decides"; A.U20.42 removes them (M.GEN.004) — the
  exemption is not written.
- **Unit**: U20 (stage U10 with the exemption for the generated asserts; U20 removes it with A.U20.42).
- **Depends**: A.U10.31-A.U10.45 (SRC_CORE et al.), M.GEN.004.
- **Blast carried by**: SPEC 0.4 → A.U36.542 (SPEC).
- **Kind**: test

### M.TSC.080 Config file names are built by the one helper
- **From**: A.U11.32 (its L0 grep test, file unnamed — placed beside the other `src/` convention checks).
- **Site**: `tests_scripts/test_code_conventions.py` (new test).
- **Change**: no `"config_"` string literal is concatenated (`+`, f-string, `%`, `.format`) in `src/` outside
  `asy_config_manager.py` (`config_filename()` builds every name); bite on a `tmp_path` copy.
- **Resolved**: —
- **Unit**: U11
- **Depends**: A.U11.32 (`config_filename()`, SRC_CORE).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_comment_block_cap.py
### M.TSC.065 The cap counts per line, per length, and checks headers everywhere
- **From**: A.U27.28 (1)-(6), A.U27.30 (`_DIVIDER`), A.U8.03 (`@tunable` in `_TAGS`), A.U20.33 (future import); read
  (each "stays green" — the edited comments obey the cap, no change here): A.S0930.08, A.S0930.30, A.SDEP.21, A.U0.07,
  A.U0.16, A.U0.18, A.U0.20, A.U0.28, A.U0.29, A.U0.31, A.U0.35, A.U0.39, A.U0.40, A.U0.41, A.U0.42, A.U0.48, A.U1.09,
  A.U1.21, A.U1.25, A.U10.34, A.U11.30, A.U16.01, A.U16.08, A.U16.12, A.U16.14, A.U16.16, A.U19.21, A.U20.15, A.U20.23,
  A.U21.31, A.U25.01, A.U25.50, A.U27.03, A.U29.03, A.U33.01, A.U34.07, A.U36.004, A.U36.020, A.U36.513, A.U36.533
  (CLAUDE.md states this counting; must match the docstring at landing), A.U36.542, A.U36.544, A.U36.546, A.U36.548,
  A.U36.549, A.U4.06.
- **Site**: `tests_scripts/test_comment_block_cap.py:1-109`.
- **Change**: `from __future__ import annotations` goes; `_TAGS` gains `"@tunable"` (comment names the family); a tag
  line leaves the count but its block's other lines count (the `:59` whole-block exemption goes); PEP 723 lines count
  as punctuation only between `# /// script` and the closing `# ///`; a line counts `ceil(len(stripped) / 110)` (the
  110 width stated in the docstring as "(agent, 2026-09-30)"); `_DIVIDER = re.compile(r"^#\s*-{4,}\s*$")` and a test
  that no comment line consists only of `=`, `~`, `*` or `#` rule characters; header presence: every Python file in the
  eight scopes plus `build/generated_src` has a module docstring, every shell file a comment block after the shebang,
  every `js/`, `tests_js/`, `html/` script and CSS file a leading `/** */` or `//` block, `html/index.html` a `<!-- -->`
  header after the doctype; the config files without one (`eslint.config.js`, `vitest.config.js`, `ci.yml`, the
  composite action) sit in a pending set that empties in U28; `_REVIEW_ENFORCED` names every tracked extension the gate
  cannot measure with its reason, and a test fails on an unlisted extension; the scope floor
  (`test_the_scan_actually_reaches_every_scope_with_files_in_it`) gains the new scopes.
- **Resolved**: —
- **Unit**: U27 (U8 `_TAGS`; U20 future import); the pending set empties in U28.
- **Depends**: the 84 over-cap blocks rewrapped in the same change (A.U27.28's own list, every owning cluster), A.U27.30's
  20 `# ====` rules → `# ----` (TEST_UNIT files).
- **Blast carried by**: CLAUDE.md "How a block is counted" → A.U36.533 (DOC); the rewrapped files → A.U27.28 (each
  cluster's file owner).
- **Kind**: test

## tests_scripts/test_config_paths_resolve.py
### M.TSC.066 Every config path resolves to something tracked
- **From**: A.U28.39.
- **Site**: new `tests_scripts/test_config_paths_resolve.py`.
- **Change**: fails naming file, key and path when a `pyproject.toml` per-file-ignores glob matches no tracked file; a
  `[tool.mypy]` `files`/`mypy_path` entry (except `build/generated_src`, created by `typecheck.sh`) or `exclude` regex
  matches nothing; a `host_typecheck.ini`/`digital_twin/typecheck.ini` `files` entry is missing; a `tsconfig*.json`
  `include`/`exclude`/`extends` entry matches nothing; a `package.json` script or a `ci.yml`/composite `run:` names a
  missing repo script (`scripts/…`, `toolchain/…`, `tests_scripts/…`); a `vitest.config.js` import path is missing.
  `.gitignore` out of scope.
- **Resolved**: —
- **Unit**: U28
- **Depends**: —
- **Blast carried by**: SPEC B.15 names the check → A.U28.39 (SPEC).
- **Kind**: test

## tests_scripts/test_config_schemas.py
### M.TSC.067 Every schema checked statically, `src/` and generated
- **From**: A.U11.18, A.U20.12 (selection by last dotted part; name uniqueness; concatenation evaluated), A.U11.25 (read:
  its comment names this file).
- **Site**: new `tests_scripts/test_config_schemas.py`.
- **Change**: for every `src/*.py` and every module generated into `tmp_path` (from `DEVICE_NAMES` plus both
  `buildgen_fixtures/` TOMLs), every module-level assignment named `_VAL_*` or annotated with a type whose last dotted
  part is `ConfigSchema` or `FieldSchema` is evaluated with `schema_ast._eval_literal()` (which reads tuple
  concatenation); each element is a 6-tuple, first two items `str`; type in `{"int", "float", "str", "bool"}`;
  `int`/`str` bounds `int` or `None`, `float` bounds `float` or `None`, `min <= max`; a `special` scalar or every element
  of a tuple `special` has the field's type; a default is `None` only with a scalar `special`; the default (or
  special-alone value) passes `type_or_range_error()` of `src/asy_config_manager.py` loaded as a plain module (its
  `asy_print_log` import stubbed); `float` bounds within ±2**24; field names unique over the leaf schemas one
  `ConfigManager`/`SettingsGroup` serves (an aggregate `_VAL_*` built by concatenation or by name is not counted
  again; the LED command fields are `asy_webserver_service._LIGHT_CMD_FIELDS`, a `src/` leaf after M.GEN.008). Bites on
  `tmp_path` copies: a float bound 2**24 + 1, an int bound on a float field, a tuple special on a special-alone field, a
  5-tuple record, a duplicate name across two `_VAL_*` of one module.
- **Resolved**: A.U20.12 extends A.U11.18's selection and adds uniqueness — one file, one commit.
- **Unit**: U20 (stage U11 without the uniqueness/selection widening).
- **Depends**: M.GEN.045 (`_eval_literal()` concatenation), M.SRC_CORE.047 (validator), M.TSC.001.
- **Blast carried by**: concatenation row → {{schema_ast}}; SPEC C.5 → A.U11.18 (SPEC).
- **Kind**: test

## tests_scripts/test_const_mirrors.py
### M.TSC.068 Every test copy of a `src/` constant is read or pinned
- **From**: A.U24.02, A.U24.01 (the copies it converts).
- **Site**: new `tests_scripts/test_const_mirrors.py`.
- **Change**: collect every module-level `NAME = const(...)` in `src/*.py` (value resolved over earlier bindings); for
  every module-level assignment in `tests/*.py` to such a name: pass if (a) `src_const(...)` naming an existing file and
  name, (b) a literal citing an external source (`datasheet`, `RFC`, `SPEC`, `p.`, `§`) on its line or the line above
  and equal to the `src/` value in the module the test imports, or (c) `code(<kind>, <name>)` from
  `tests/_error_codes.py` for an `_ERR_*`/`_WRN_*` name; a copy under another name carries `# pins src/<file>.py
  <NAME>` and is compared the same way (a `# pins` naming a missing file/name fails); anything else fails naming
  file:line, name and `src/` value. Floor: ≥ 1 `src_const` binding and ≥ 1 cited copy found.
- **Resolved**: —
- **Unit**: U24
- **Depends**: A.U24.01 (TEST_UNIT/TEST_HELP conversions), M.TEST_HELP.045 (`code()`).
- **Blast carried by**: SPEC E test standard → A.U24.01 (SPEC).
- **Kind**: test

## tests_scripts/test_counter_steps.py
### M.TSC.069 Counters stay allocation-free in `src/`, generated code and the twin
- **From**: A.U10.05, A.U25.23 (`digital_twin/*.py` joins), A.U12.13 (VOC fix16 sentinels and uptime fields), A.U15.31
  (ISL29125 write-failure count is a masked sequence); SRC_CORE GAP-G6 (`SensorReader._err_cnt_internal`); SRC_NET gap 3
  (post-U10 private names; `discarded_bytes` masked, `_blind_resyncs` capped).
- **Site**: new `tests_scripts/test_counter_steps.py`.
- **Change**: parses every `src/*.py`, every module generated into `tmp_path` over `DEVICE_NAMES`, and every
  `digital_twin/*.py`; fails on (1) any `min(<expr> + <n>, <cap>)` or `min(max(<x> + …` step; (2) an integer above
  `0x3FFFFFFF` bound to a `*_CAP|*max_val*|*MAX*` name or passed as `max_val=`, except `asy_ntp_client._NTP_MAX_PLAUSIBLE_UNIX_TIME`
  and `voc_algorithm.py`'s `_FIX16_MAXIMUM`/`_FIX16_MINIMUM`/`_FIX16_OVERFLOW` ("C int32 fix16 sentinels, not
  counters"); (3) a `+= <int>`/`-= <int>` on a `self.` attribute unless guarded by a cap comparison, reset to 0 at a
  threshold, or in the exemption table. The table (each with its reason in place, no inventory ID, names as they stand
  after U10's privatisation): `_trigger_counter`, `_verify_counter`, `_backup_counter`, `_periodic_only_switches`,
  `_ntp_sec_count`, `_unsynced_wait_s`, `_connection_failures`, `_allocated_size`, `_cancel_req`/`_cancel_unacknowledged`
  and `_discarded_bytes` (masked sequences), ISL29125's write-failure count (masked sequence, A.U15.31), `_blind_resyncs`
  (capped), `_episode_events` (a flag), `SensorReader._err_cnt_internal` (bounded by the give-up, M.SRC_CORE.037), VOC
  `m_mean_variance_estimator_uptime_gamma`/`_gating` with the asserted bound
  `(_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX - _VOCALGORITHM_SAMPLING_INTERVAL) * 65536 <= 0x3FFFFFFF` read from
  the parsed `const()` values, and the twin's `COUNTER_CAP` in `digital_twin/_twin_common.py` (checked equal to
  `asy_base_classes.COUNTER_CAP`). Must not flag `asy_print_log`'s capped counter (`if self.err_count < …`). Negative
  cases on `tmp_path` copies, one per rule.
- **Resolved**: SRC_NET gap 3 asks for the post-U10 private names (the table is written after A.U10.35's renames).
- **Unit**: U25 (stage U10; rows added in U12, U15, U17 as their counters change).
- **Depends**: A.U10.01-A.U10.04, M.TWIN.001, M.SRC_CORE.037.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_coverage_runner.py
### M.TSC.070 Coverage runner: the probe names the binary; incomplete files fail
- **From**: A.U27.12 (`:21-28` → `unix_port_bin settrace`), A.U7.26 (`:27` skip → fail), A.U36.512 (`:27` "variant" →
  "build flavour"), A.U27.15 (`:35` → `scripts/micropypath.toml`'s `unit`), A.SDEP.16 (`:35` `TZ`), A.U24.05 (new
  cases), A.U24.72 (generated modules traced), A.U8.22 (`:38` timeout tag); read: A.U28.15 (no `--xml-file` here),
  A.U7.07 (exit codes only).
- **Site**: `tests_scripts/test_coverage_runner.py:20-60`, new cases.
- **Change**: `settrace_bin` runs `bash scripts/_unix_port.sh check settrace` and fails (never skips) with the script's
  message ("…the --coverage build flavour…"); `_run()`'s `MICROPYPATH` is read from `scripts/micropypath.toml` `unit`;
  `TZ: "UTC"` stays unless A.SDEP.16's re-check at the new tag retires the `$TZ` workaround (then it goes in the same
  change as every other listed site); `timeout=_RUN_TIMEOUT_S` (`# @tunable l0.coverage_runner_timeout_s = 60`); new:
  a trailer-less test file exits 1; a file whose top level raises exits 1 and the dump still exists; `sys.exit("x")`
  exits 1; a fixture importing a module under `build/generated_src/` gets its lines in the dump.
- **Resolved**: —
- **Unit**: U27 (stages U7, U24, U36 wording).
- **Depends**: A.U27.12, A.U27.15 (SCR), A.U24.05/A.U24.72 (`tests/_coverage_runner.py`, TEST_HELP).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_decision_vocabulary.py
### M.TSC.071 Decision vocabulary carries its actor <!--@vocab-->
- **From**: A.U0.09 (check), A.U36.549 (named narrowing regexes per recurring descriptive shape; empty list), A.U37.02
  (allow-list reading goes), A.U0.10 (read: CLAUDE.md names it).
- **Site**: new `tests_scripts/test_decision_vocabulary.py`.
- **Change**: scope: living `*.md` outside `audit/`, `legacy/`, `arduino/`, `ext/`, `PROJECT_AUDIT_PLAN.md` and
  `THIRD_PARTY_LICENSES.md`'s quoted licence text, plus comments/docstrings in `src/`, `buildgen/`, `digital_twin/`,
  `tests*/`, `scripts/`, `toolchain/`, `js/`, `html/`, config files; unit a sentence; vocabulary `accepted`, `settled`,
  `decided`, `by design`, `deliberate(ly)`, `don't|do not re-propose|re-raise`, rule-sense `never`; each narrowing a
  named regex with a one-line reason (A.U36.549 adds one per recurring descriptive shape); a hit passes with an actor
  tag `\((owner|agent)[^)]*\d{4}-\d{2}-\d{2}` or a source citation on its sentence/first block line. The module
  docstring cites CLAUDE.md's decision-records rule, not the audit's provenance document. Staged: U0 with
  `_decision_vocab_allowlist.txt` (shrink-only); U36 empties it; U37 drops the allow-list reading.
- **Resolved**: —
- **Unit**: U37 (stages U0, U36).
- **Depends**: M.TSC.010.
- **Blast carried by**: the tagged sentences → A.U36.549 (every owning cluster).
- **Kind**: test

## tests_scripts/test_definitions_js_mirrors.py
### M.TSC.072 The website's copies of generator bounds are pinned <!--@defs_js_mirrors-->
- **From**: A.U6.16 (2), A.U23.09 (`MAX_POLL_INTERVAL_MS`), A.U23.37 (the JS-constant regex reads `const`).
- **Site**: new `tests_scripts/test_definitions_js_mirrors.py`.
- **Change**: reads `js/definitions.js` as text: `export const SUPPORTED_SCHEMA_MAJOR = N;` equals the major of
  `buildgen.definitions.SCHEMA_VERSION`; `const MAX_DECIMALS = M;` equals `buildgen.web_tag._MAX_DECIMALS`; `const
  MAX_POLL_INTERVAL_MS = 2 ** 31 - 1;` equals the `_MAX_POLL_INTERVAL_MS` literal read by `ast` from
  `test_buildgen_definitions.py` (the Python shape check's bound; no test module is imported); constants matched by one helper regex accepting `const`/`export const`.
- **Resolved**: —
- **Unit**: U23 (stage U6).
- **Depends**: A.U6.16 (1), A.U23.09 (WEB).
- **Blast carried by**: SPEC G mirror catalog → A.U6.16 (SPEC).
- **Kind**: test

## tests_scripts/test_device_script_config_flush.py
### M.TSC.073 Config-flush guard: scratch files removed, retired scripts gone
- **From**: A.U26.18 (new check: every `config_HWTEST_*` literal removed in a `finally`), A.U26.11 (`:26-28` exemption
  reason → "flushes in its `finally` before removing the scratch file", or the entry goes when the explicit flush
  satisfies the main check), A.U26.12 (the two deleted DebugLevel scripts' coverage goes; M.HW_DEV.039), A.U26.19 (`:70`
  comment and `_writing_scripts()` lose `wifi_service_reconnect_repro.py`; M.HW_DEV.112), A.U20.33, M.TSC.001
  (`base_classes.py` ×2 → `asy_base_classes.py`); read: A.U11.28 (`:130-140` holds), A.S0930.16 (flush semantics kept
  for scripts), A.U26.44 (one `BENCH` line, unaffected), A.U24.13 (`:13` insert), A.U8C.76/A.U8C.99/A.U8C2.32 (static
  readers unaffected).
- **Site**: `tests_scripts/test_device_script_config_flush.py:1-140`, new test.
- **Change**: `from __future__ import annotations` goes; `_JUSTIFIED_UNFLUSHED["isl29125_mechanism_envelope.py"]` →
  "flushes in its `finally` before removing the scratch file" — or the entry is deleted if the explicit flush makes
  the main check pass (the stale-entry test then requires it); `:68-70` comment names no retired script ("a write can
  sit in a helper that takes the object as a parameter while the flush sits in `_main`"); new
  `test_every_scratch_config_file_is_removed`: every `config_HWTEST_*` literal in a device script is removed by a
  script of the same host test in a `finally` (or by the host test's own cleanup), naming any path nobody removes. Reads
  the raw sources (includes carry no config writes, M.HW_DEV.003).
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_DEV.039, .101, .112, .142.
- **Blast carried by**: the flagged scripts fixed in the same change → M.HW_DEV (their scripts).
- **Kind**: test

## tests_scripts/test_device_script_config_schemas.py
### M.TSC.074 A script's `ConfigManager` on a production file takes the full schema
- **From**: A.U11.33 (1); HW_DEV GAP-D3 (M.HW_DEV.040, AD-4).
- **Site**: new `tests_scripts/test_device_script_config_schemas.py`.
- **Change**: L0 (`ast`): every `ConfigManager(` construction in `tests_hardware/device_scripts/` (raw sources and the
  `_shared/` includes) whose path argument resolves (string literal or module-level name bound to one, resolved like
  `buildgen.schema_ast`'s consts) to a production file `config_<NAME>.cfg` (`SYSTEM`, `WIFI`, `NTP`, `NOTIFY`, `SGP40`,
  `BMP3XX`, `ISL29125` and their `_<ext>` forms) passes a schema equal to that module's full production schema (from
  `buildgen.schema_ast` on its `src/` owner); a schema argument `BENCH["system_schema"]` is accepted as the production
  schema by construction (it is rendered from `schema_ast`, M.HW_DEV.040); `config_HWTEST_*` files exempt. Bite on a
  `tmp_path` copy with one field dropped.
- **Resolved**: the HEAD example sites (the two DebugLevel scripts) are deleted (M.HW_DEV.039); the guard's live case is
  the standard-state repair script.
- **Unit**: U26 (stage U11 at HEAD's scripts).
- **Depends**: M.HW_DEV.040, M.HW_BENCH.041.
- **Blast carried by**: SPEC C.5 hazard paragraph → A.U11.33 (SPEC).
- **Kind**: test

## tests_scripts/test_device_script_fram_regions.py
### M.TSC.075 Raw FRAM scratch regions lie outside the production layout
- **From**: A.U26.24; HW_DEV GAP-D7 (M.HW_DEV.066), AD-8 (disjoint regions, M.HW_DEV.124/.132).
- **Site**: new `tests_scripts/test_device_script_fram_regions.py`.
- **Change**: every device script issuing a raw `set_values`/`get_values` declares `_SCRATCH_REGIONS`
  (and `_EVIDENCE_REGIONS` for a production read) covering every raw call, its addresses expressed from those tuples;
  regions of different scripts are disjoint; every scratch region lies in `[allocated_size, part_size)`, with
  `allocated_size` read by booting the bench device's generated module under the Unix-port twin (the
  `test_digital_twin_boot_contiguity.py` harness) and `part_size` the bench TOML's FRAM `max_size`; every
  `_EVIDENCE_REGIONS` script runs under the session evidence save; a raw call addressed through a `get_chunk()`
  result (`chunk.block_addr …`) is chunk-scoped (covered by the clear-in-`finally` check), not undeclared scratch. A
  missing Unix-port build fails.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_DEV.007, M.HW_DEV.066, M.HW_BENCH.006.
- **Blast carried by**: README convention → M.HW_BENCH.116.
- **Kind**: test

## tests_scripts/test_device_script_gc_threshold.py
### M.TSC.076 Every heap-measuring script sets and reports its GC stage, any spelling
- **From**: A.U26.48 (aliases: `from gc import threshold`, `import gc as g`), A.U26.68 (marker → the `gc_threshold`
  fact), A.U20.33, A.U8.14 (`:96` tag); HW_DEV GAP-D10 (M.HW_DEV.116: reads rendered sources where an include does the
  measuring); read: A.U26.44, A.U26.61 (sibling file), A.U30.14 (scripts may set their own stage), A.U30.18 (its new
  script obeys this), A.U36.012 (SPEC E.8 names this check), A.U8C.71-.73/.86, A.U8C2.30 (static readers unaffected).
- **Site**: `tests_scripts/test_device_script_gc_threshold.py:1-110`.
- **Change**: docstring (≤ 3 lines) "Pins that every device script measuring the heap sets gc.threshold itself and
  reports the gc_threshold fact first: mpremote's soft reset keeps the boot entry's threshold, so a figure not naming its
  stage is void (SPECIFICATION.md E.8)." (the "(MEASUREMENTS M3.8)" pointer goes, A.U36.544's rule); `from __future__`
  goes; `_calls()` resolves `import gc as <alias>` and `from gc import threshold [as x]`/`mem_free` so every spelling
  counts; `_MARKER` → the call `fact("gc_threshold", …)` (a measuring script's first report must follow its first set);
  each script is checked on its rendered source (`# @include _shared/heap_probe.py` inlined), so a measurement through
  the shared probe counts as measuring; `:96`'s `gc.threshold(32768)` line carries `# @tunable gc.threshold_bytes =
  32768` (A.U8.14's site list).
- **Resolved**: —
- **Unit**: U26 (U8 tag; U20 future import).
- **Depends**: M.HW_DEV.002, M.HW_DEV.003, M.HW_BENCH.012 (render).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_device_script_rig_parking.py
### M.TSC.077 NeoPixel construction sits inside a parking `try` <!--@rigparking-->
- **From**: A.U26.16 (file choice: its own file, not `test_bench_harness_helpers.py`); M.HW_DEV.008.
- **Site**: new `tests_scripts/test_device_script_rig_parking.py`.
- **Change**: parses each device script (rendered); every `NeopixelDriver(`/`neopixel.NeoPixel(` construction is the
  first statement inside a `try` whose `finally` sets it dark (`.off()` or an all-zero `write()`); fails naming a
  construction outside one; a synthetic non-conforming script bites.
- **Resolved**: A.U26.16 offers either file — the separate file is taken (one device-script guard per file, beside its
  siblings).
- **Unit**: U26
- **Depends**: M.HW_DEV.008.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_device_script_watchdog.py
### M.TSC.078 A long device script feeds the watchdog in short steps
- **From**: A.U26.61; M.HW_DEV.004.
- **Site**: new `tests_scripts/test_device_script_watchdog.py`.
- **Change**: for every `device_scripts/*.py` (rendered): (a) no single `sleep`/`sleep_ms`/`sleep_us` call with a literal
  (or rendered constant) above 2 s — waits go through `_shared/watchdog.py`'s `fed_sleep_ms()`/`fed_wait_ms()`, whose
  `_FEED_STEP_MS` the check reads and requires ≤ 2000; (b) a script whose host `run_isolated(…, timeout_s=…)` literal
  exceeds 8 arms through `arm()` (or `machine.WDT(`) and feeds; the two starvation scripts are named exceptions (their
  subject is the reset); (c) bite cases for both.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_DEV.004.
- **Blast carried by**: README habit → M.HW_BENCH.121.
- **Kind**: test

## tests_scripts/test_device_tomls.py
### M.TSC.079 Device-TOML checks validate.py does not make <!--@device_tomls-->
- **From**: A.U20.19 (1) (rewrite), A.U20.10 (FRAM part comment check), A.U20.29 (banner layout check), A.U20.28
  (`:841-848` → `fixed_address()`), A.U26.01 (`bench` key accepted), A.U28.06/A.U28.08 (`:271-282` moves to
  `test_ci_workflow.py`), A.U24.66, A.U24.73, A.U10.43; dropped: A.U0.29's `:761` sentence (lands U0, its test goes with
  A.U20.19 in U20), A.U20.37's `:285` accept assertion (its test is deleted by A.U20.19); read: A.U1.24, A.U36.520
  (TOML comments, not parsed), A.U28.01/A.U6.12 (`:275` regex cited as precedent), A.U32.01 (cites `:294`), A.S0930.01
  (no `uart_link` field set pinned).
- **Site**: `tests_scripts/test_device_tomls.py:1-849`.
- **Change**: header "Device-TOML checks `validate.py` does not make: reserved I2C addresses, the FRAM part comment,
  section layout and banners, and per-device test coverage."; one parametrised test over `DEVICE_NAMES`:
  `build_model(devices/<d>.toml, src)` returns and `build_construction_order()` succeeds; deleted: the `check_*`
  functions `:70-245` and their tests `:284-411`, `:484-801`, `test_parses_as_valid_toml`, `_ALWAYS_PRESENT_DRIVERS`,
  `_DEVICES_WITH_BMP3XX`, `_DEVICES_WITH_UART_LINK`, `_DEVICES_WITH_ISL29125`, `test_instance_list_has_the_expected_driver_kinds`,
  `test_bmp3xx_only_present_on_wozi_and_dev`, `test_isl29125_only_present_on_dev`, the two "every wirable instance"
  tests, the multi-instance `name_ext` hand test, `:271-282`; kept: reserved-I2C-address tests (`:817-848`, looping
  `fixed_address()` over the fixed-address drivers) and the device-coverage derivations `:247-282` minus the CI matrix;
  `test_klkizi_grkizi_schlafzi_share_identical_wiring` → `test_devices_of_one_hardware_family_differ_only_in_identity`
  (grouping by `[device] hardware_family`, only `name`/`hostname` differ); new: the comment line directly above every
  FRAM `max_size` names the part `_KNOWN_PRODUCT_IDS` (read by `ast`/`tokenize`) maps the size to; banners match `^#
  --- [a-z -]+ -+$` at 100 characters, sections in the fixed order (`sensor drivers`, `singleton services`,
  `multi-instance services`), each `[[instance]]` under the banner its driver's kind selects, every non-singleton
  instance states `name_ext`; the `bench` key is accepted in the `[device]` layout. No `Any`.
- **Resolved**: A.U28.06 says `:271-282` is rewritten here; A.U28.08 (7) moves it to `test_ci_workflow.py` — moved
  (A.U28.08 names the move; one home for workflow rules).
- **Unit**: U20 (stage U28 removes `:271-282`; U26 `bench`).
- **Depends**: M.GEN.028 (`name_ext` rule), M.GEN.052-.059 (TOML edits), M.GEN.043.
- **Blast carried by**: SPEC L.3 sentence about this file → A.U20.19 (SPEC); README runbook's `:294` citation → Gaps
  (DOC).
- **Kind**: test

## tests_scripts/test_digital_twin_boot_contiguity.py
### M.TSC.081 The contiguity probe follows the setup list now inside `SystemService` <!--@contiguity-->
- **From**: A.U11.10 + A.U20.06 (`:242-254` counts `_collect_setups()`, the module holds no `gc.collect()`; `:189`
  comment names `start_tasks()`), TEST_HELP GAP-H1 (`_MIRRORED_BOUNDS` drops `_STARTER_LOOP_GRACE_MS`, M.TEST_HELP.028),
  A.U25.61 (1) + HW_DEV GAP-D10 (probe constants read from `_shared/heap_probe.py`, M.HW_DEV.116); read: A.U30.04
  (bounds hold), A.U26.24 (this harness reused), A.SDEP.17 (W38 re-check), A.U8C.01/A.U8C.72 (constants read by name,
  tag lines leave the `^NAME = (-?\d+)$` match intact).
- **Site**: `tests_scripts/test_digital_twin_boot_contiguity.py:170-300`.
- **Change**: `test_a_real_boot_fires_exactly_the_collects_the_static_guards_count`: `setup_calls` = the length of the
  list `_collect_setups()` returns (read from the generated module's AST), `counters["batch_collects"] ==
  setup_calls + 1` (`run_setups()` collects once before the list and after each unit, M.SRC_CORE.010/.015),
  `counters["starter_collects"] == counters["starters"] + 1` (the collects inside `start_tasks()`), and the generated
  module contains no `gc.collect(` at all; the `:189` comment names `start_tasks()` for the starter loop;
  `_MIRRORED_BOUNDS = ("_STARTER_LOOP_TIMEOUT_MS", "_TIMERS_TIMEOUT_S")`; new: `_PROBE_MIN`, `_PROBE_MAX`,
  `_PROBE_RETRIES` are defined once, in `tests_hardware/device_scripts/_shared/heap_probe.py`, no device script keeps a
  copy, and they equal the twin probe's own (`tests/_boot_contiguity_probe.py`); `_HIGH_BAND`/`_HIGH_BAND_BLOCKS_MAX`
  have no device-script copy (report only). The bounds tests `:170-238` stay (LEAD/R20); the batch-level reach and
  band-count checks stay as regression tripwires and the suppressed arm asserts nothing on them (A.U25.61 (4)).
- **Resolved**: A.U11.10 and A.U20.06 name the same edit (A.U20.06 Blast cites A.U11.10) — one change, U20.
- **Unit**: U26 (stage U20 for the count; U25/U26 for the probe-constant read with M.HW_DEV.116).
- **Depends**: M.SRC_CORE.010/.015/.016, M.GEN.010, M.TEST_HELP.028, M.HW_DEV.116.
- **Blast carried by**: the board mirror's order → M.TEST_HELP.028/HW_DEV; the flash wrapper's per-arm assertion →
  A.U25.61 (3) (HW_DEV).
- **Kind**: test

### M.TSC.082 Probe harness: derived control pair, shared path, marker gate, tags
- **From**: A.U24.66 (`:42` `_CONTROL_DEVICES` → the first two derived devices), A.U36.512 (`:39` wording, superseded by
  the rewrite), A.U27.15 (`:31`, `:285` → `scripts/micropypath.toml`'s `unit`), A.U7.26 (`:109` skip → fail), A.U7.22
  (`boot_probe` gates on the marker set), A.U8.15 (`:32` `_HEAPSIZE` tag), A.U8.22 (`:34`, `:71`, `:76-77`, `:81` tags),
  A.U20.33, A.U24.13 (read: `:20` insert unchanged).
- **Site**: `tests_scripts/test_digital_twin_boot_contiguity.py:1-170`, `:276-290`.
- **Change**: `from __future__` goes, `Callable` imported at runtime; `_MICROPYPATH` is read from
  `scripts/micropypath.toml` (`unit`), and `:285`'s parity check asserts `scripts/test.sh` reads the same file (not a
  literal); `-X heapsize={_HEAPSIZE}` parity (`:286`) holds; `_HEAPSIZE = "16M"  # @tunable` (A.U8.15's ID);
  `_CONTROL_DEVICES = tuple(DEVICE_NAMES[:2])` with `assert len(DEVICE_NAMES) >= 2`, comment (≤ 3 lines) "Two devices
  get the suppressed arm: it proves the bound would otherwise break, and six runs would prove the same thing six times
  at double the subprocess count." (the existing control arm, not a new one — OR21.a (2)); `test_the_control_arm_devices_are_real_devices`
  goes (derived by construction); `generated_src` fails (never skips) naming `scripts/test.sh`'s generation step;
  `boot_probe` imports `harness.MEMORY_ERROR_MARKERS` through `_script_loader` and fails quoting any output line holding
  a marker; tags `l0.boot_contiguity_probe_timeout_s`, `l0.boot_contiguity_high_band_blocks_max`,
  `l0.boot_contiguity_arm_depth_ratio_min`, `l0.boot_contiguity_arm_reach_ratio_min`,
  `l0.boot_contiguity_retention_tolerance`.
- **Resolved**: A.U36.512 rewords `:39` ("exemplary device"); A.U24.66 removes the names it explains — the U24 text wins
  (it removes the sentence's subject).
- **Unit**: U27 (stages U7, U8, U20, U24).
- **Depends**: A.U27.15 (SCR), M.HW_BENCH.016 (marker set).
- **Blast carried by**: gate agreement → {{gate_agreement}}.
- **Kind**: test

## tests_scripts/test_digital_twin_ci_suite_ceiling.py
### M.TSC.083 Ceiling runs over derived routes and neutral fixtures
- **From**: A.U27.32 (`:74` `RunContext(...)` gains `get_routes`; `:117-176` burst cycles the fixture's GET routes; new:
  the suite's route list equals the fixture reference's GET entries), A.U24.66 (`:77-78`, `:100`, `:138` → `fixture_device`),
  A.U8.22 (`:105`, `:111` → `l0.ci_suite_ceiling_get_timeout_s`), A.U28.27 (`do_GET` N802 → per-file entry), A.U28.28
  (`A002` inline `noqa` → per-file entry "overrides `http.server`'s `log_message(format, …)`"); read: A.U27.37 (`:99`
  holds), A.U20.28 (the plan reader follows the one producer), A.U8.20 (constants read by name, unchanged).
- **Site**: `tests_scripts/test_digital_twin_ci_suite_ceiling.py:70-180`.
- **Change**: as listed; the inline `# noqa: A002`/N802 suppressions go (central entries, TOOL); one constant
  `_GET_TIMEOUT_S = 5.0  # @tunable l0.ci_suite_ceiling_get_timeout_s = 5.0` used at both sites; fixture route
  references come from a `tmp_path` reference document shaped like A.U19.20's output.
- **Resolved**: —
- **Unit**: U28 (stages U8, U24, U27).
- **Depends**: A.U27.32 (`scripts/_digital_twin_ci_suite.py`, SCR), M.GEN.033.
- **Blast carried by**: `pyproject.toml` entries → A.U28.27/A.U28.28 (TOOL: Gaps).
- **Kind**: test

## tests_scripts/test_digital_twin_ci_suite_soak.py
### M.TSC.084 Run 11 decides on one attempt; samples joined by log position
- **From**: A.U27.17 (one attempt), A.U35.26 (offset join; backwards clock step), A.U7.09 (summary block for the
  missing-plan path), A.U24.66 (`:16`, `:25` log fixture names → `fixture_device`); dropped: A.U7.09's "first trend
  fails, second passes → `retried 1`" case (A.U27.17 removes the retry; OR37.a (2), A.U35.27 "no retry is added");
  read: A.U25.44 (log fixtures name the runner with no launch — not flagged), A.U35.27 (calibration, helpers hold),
  A.U8.20.
- **Site**: `tests_scripts/test_digital_twin_ci_suite_soak.py` (whole file).
- **Change**: new: `_run_11_soak()` with `_run_11_soak_attempt` monkeypatched to return an over-tolerance run records
  exactly one failure and calls the attempt once; `_parse_mem_samples()` cases carry the log offset and a fixture log
  with a backwards `time.time()` step between lines still selects the right samples; the missing-plan path prints the
  summary block (A.U7.02's form); fixture logs name `fixture_device`.
- **Resolved**: A.U7.09 (U7) vs A.U27.17 (U27) on the retry — the later unit removes it, so the retry case is never
  written (above).
- **Unit**: U35 (stages U7, U24, U27).
- **Depends**: A.U27.17, A.U35.26 (`scripts/_digital_twin_ci_suite.py`, SCR), A.U7.02 (summary block, SCR).
- **Blast carried by**: SPEC E.9 → A.U27.17 (SPEC).
- **Kind**: test

## tests_scripts/test_digital_twin_generated_boot.py
### M.TSC.085 Header, launch and state paths of the generated boot <!--@gen_boot-->
- **From**: A.U36.513 (5) (`:1-2`, `:150-152`), A.U36.548 (7) (carried by A.U36.513), A.U36.004 (`:35` history comment →
  current fact), A.U27.05 (`_boot_generated_device()` takes a path root), A.U27.15 (`:153` → `twin` with the tmp tree,
  reason line), A.U25.44 (the launch guard reads this site), A.U25.32 (`:155-164` state paths and `--config-dir`),
  A.SDEP.16 (`:154` `TZ`), A.U20.02 (the runner passes a `WDT`), A.U20.33, A.U24.73, A.U24.66, A.U24.67 (`:201-202`
  set-claim comment), A.U8.22 (`:29-30`, `:42`, `:100`, `:105`, `:185`, `:188`); TWIN: `twin` MICROPYPATH gains
  `digital_twin/unixport` (M.TWIN.017, via the file); read: A.U1.23, A.U6.01 (`:111` model already ordered), A.U16.20,
  A.U16.17 (fixtures move to 0x40000 in their own files, {{fixtures}}), A.U19.20, A.U11.05 (twin fakes land in
  the same commit).
- **Site**: `tests_scripts/test_digital_twin_generated_boot.py:1-60`, `:136-202`.
- **Change**: docstring `"""Proves each generated sensortask_<device>.py boots under the digital twin's real MicroPython
  Unix-port environment and serves real REST requests, beyond ast.parse() and the wiring plan's own tests
  (test_buildgen_twin_wiring.py). See digital_twin/README.md's "Booting a generated device"."""` (≤ 3 lines);
  `from __future__` goes; no `Any`; `_boot_generated_device(root, device)` takes the path root; `MICROPYPATH` is the
  file's `twin` value with its `build/generated_src` segment replaced by the tmp tree and `frozen_modules` dropped, the
  reason on one comment line ("the tmp tree carries its own generated module and stub frozen_html.py"); the runner gets
  `--fram-state-path "" --scd30-state-path "" --mem-backup-state-path "" --config-dir <tmp_path>/config`; `TZ=UTC`
  stays unless A.SDEP.16 retires the workaround; `:35` → the current reason for `_BOOT_TIMEOUT_S` (no history); `:201-202`
  comment claims no device set; tags `l0.generated_boot_boot_timeout_s`, `l0.generated_boot_shutdown_timeout_s`,
  `l0.generated_boot_twin_duration_s`, `l0.generated_boot_poll_step_s`, `l0.generated_boot_poll_timeout_s`,
  `l0.generated_boot_exit_wait_s`. Parametrised over `DEVICE_NAMES` plus both fixtures.
- **Resolved**: —
- **Unit**: U27 (stages U8, U20, U24, U25, U36 text).
- **Depends**: A.U27.15 (SCR), M.TWIN.017, A.U25.32 (TWIN runner flags).
- **Blast carried by**: stripped-image reuse → {{stripped}}.
- **Kind**: test

### M.TSC.086 A booted device answers as its definitions say, cleanly
- **From**: A.U24.55 (2) (strict JSON with the device's own sections; boot-sequence markers in order), A.U24.36 (`:47`
  `_SMOKE_ENDPOINTS` from `ROUTES` by `ast`), A.U6.22 (Status readonly-field parity), A.U6.24 (System `path` parity),
  A.U6.25 (`:108-113` errcount union), A.U35.39 (normal boot logs no E/W, the named NTP tolerance from
  `scripts/_twin_process.py`), A.U7.22 (marker gate), A.U20.16 (the multi-instance fixture serves both SGP40 entries),
  A.U6.20 (read: errcount only, unaffected).
- **Site**: `tests_scripts/test_digital_twin_generated_boot.py:40-135`, `:196-221`.
- **Change**: `_SMOKE_ENDPOINTS` = the GET paths of `ROUTES` read by `ast` from `src/asy_webserver_service.py`, with only
  a property filter; every smoke GET returns strict JSON (A.U24.60's parser) holding the device's own section keys
  (from its definitions); every readonly Status field key (non-errcount groups, maintenance keys flattened as
  `render.js` does) is present in `GET /status` and every readonly System `path` resolves in `GET /system`; the errcount
  module set is the union over every errcount group; the twin log shows the boot-sequence markers of
  `expected_facts()["boot_sequence"]` in order; `_normal_boot_log_failures(body)`: any errcount history item of type E
  or W fails ("<module> logged <type><num> on a normal boot") except the NTP tolerance constant loaded from
  `scripts/_twin_process.py` via `load_script_module` (condition NTP `Synced` false); any output line holding a
  `harness.MEMORY_ERROR_MARKERS` marker fails; the multi-instance fixture's `/status` carries `SGP40` and `SGP40_<ext>`.
- **Resolved**: —
- **Unit**: U35 (stages U6, U7, U20, U24).
- **Depends**: M.GEN.014/.033, A.U25.46 (`scripts/_twin_process.py`, SCR), M.HW_BENCH.016.
- **Blast carried by**: —
- **Kind**: test

### M.TSC.087 Two more boots: the CRC16 link and a simulated reset
- **From**: A.S0930.04 (3), A.U25.09.
- **Site**: new tests in `tests_scripts/test_digital_twin_generated_boot.py`.
- **Change**: (a) the bench device's TOML (selected by its `uart_link` pair) copied to `tmp_path` with `crc = "crc16"`
  on both ends, generated and booted like the shipped devices; after boot `GET /status` →
  `sensors.UARTLINK.Transfers` rises across two polls ≥ 3 s apart and `Failures` stays 0 (`_BOOT_TIMEOUT_S` holds);
  (b) a run with `--fault sgp40:writeto:500` exits 3, prints the `machine reset:` line, its flushed
  `--mem-backup-state-path` file carries cause 3, and a second spawn on the same state paths reports the
  supervisor-escalation `ResetReason` over HTTP. Key names follow A.U10.40.
- **Resolved**: —
- **Unit**: U25 (S0930 row lands with A.U24.55's file edits, U25).
- **Depends**: M.GEN.024/.005 (CRC wiring), A.U25.07-.09 (TWIN), A.U11.05.
- **Blast carried by**: Run 3's CRC cell → A.S0930.04 (4) (SCR).
- **Kind**: test

## tests_scripts/test_error_catalog.py
### M.TSC.088 One catalog, every logging call, every mirror of it
- **From**: A.U2.02 (1)-(9), A.U2.25 + A.U6.06 (mockdata pass reads `mockdata/samples.json`), A.U3.15 (no adjacent
  duplicate code in a mock history), A.U36.537 (marked SPEC tables equal the catalog), TEST_UNIT GAP-U2 (the keyword
  scan's non-vacuity floor, M.TEST_UNIT.157); read: A.U2.01 (catalog file), A.U2.22 (SPEC C.7.1 names this check).
- **Site**: new `tests_scripts/test_error_catalog.py`.
- **Change**: one function per check: (1) catalog shape (ints 1-127; each owner's codes in its band; bands disjoint per
  type; names and texts unique per type; a `retired` code has no live site); (2) every `err_s`/`wrn_s` call in `src/`
  passes the code by keyword — and the scan asserts it matched at least one `err_s` and one `wrn_s` call per scanned
  scope (non-vacuity floor, GAP-U2); (3) the keyword value and every argument bound to an `errno`/`wrnno` helper
  parameter is built only from `_ERR_`/`_WRN_` names, parameters, locals, attributes and `or`, no literal or arithmetic;
  every feeder (`_init_errno`, frame-check returns, `_pending_wrn`) is such a name or `0`; (4) the constant's value
  equals the catalog number of its suffix name and that number's owner is `base`/`shared` or one of the file's owners;
  (5) every non-retired code has a live site (owner `test` exempt); (6) no `_ERR_`/`_WRN_` constant holds a non-catalog
  value; (7) every generated module (in memory, `DEVICE_NAMES`) passes (2)-(4) or has no such call; (8) no module in
  `tests/`, `tests_hardware/`, `tests_scripts/`, `digital_twin/`, `scripts/` binds an int to `_ERR_*`/`_WRN_*`/
  `*_ERRNO*`/`*_WRNNO*` and no `assert` compares a literal code with a logged-code expression unless seeded in the same
  test (seed-only names exempt); (9) every `E_<NAME>`/`W_<NAME>` binding in `tests_hardware/device_scripts/` equals the
  catalog; (10) every `mockdata/samples.json` errcount history code is a non-retired catalog code of that row's logger,
  with no two adjacent identical non-`N` entries and `counter` ≥ the non-`N` slots; (11)
  `test_every_marked_spec_table_equals_its_catalog_table`: each `<!-- catalog: status.<name> -->` table in
  SPECIFICATION.md lists exactly the catalog's codes, names and tones. Planted-violation bites per check (fixtures).
- **Resolved**: A.U2.25's check reads the retired `mockdata/{dev,wozi}.json` at U2; A.U6.06 moves the rule to
  `samples.json` — staged.
- **Unit**: U36 (stages U2 checks (1)-(9) and the mockdata pass, U3 adjacency, U6 samples file).
- **Depends**: M.GEN.034 (catalog), M.TEST_HELP.045, A.U6.06 (WEB).
- **Blast carried by**: the range-sweep tests retired → M.TEST_UNIT.157.
- **Kind**: test

## tests_scripts/test_fake_surface_conformance.py
### M.TSC.089 Stand-ins offer only their real class's surface
- **From**: A.U24.18 (2).
- **Site**: new `tests_scripts/test_fake_surface_conformance.py`.
- **Change**: for each fake class in `tests/machine.py` (and the twin's `digital_twin/machine.py`, same rule), public
  names minus its `TEST_API` ⊆ the real type's locals-dict names read from the pinned MicroPython checkout
  (`MP_ROM_QSTR(MP_QSTR_<name>)` entries of `ports/rp2/machine_pin.c`, `extmod/machine_i2c.c`, `extmod/machine_spi.c` +
  `ports/rp2/machine_spi.c`, `extmod/machine_uart.c`, `ports/rp2/machine_timer.c`, `ports/rp2/machine_rtc.c`,
  `extmod/machine_wdt.c`), counting methods, class attributes and public `self.<name>` from `__init__`; for
  `_FakeModule`/`_FakeLogger`, public names ⊆ the AST public methods of `SensorReaderConfig` (`src/asy_base_classes.py`)
  and `PrintLogHistory` (`src/asy_print_log.py`). A missing checkout fails.
- **Resolved**: A.U24.18 names `tests/machine.py`; the twin's fakes stand in for the same types and follow the same rule
  (agent decision D-TSC2; M.TWIN keeps their `TEST_API`).
- **Unit**: U24
- **Depends**: A.U24.18 (1) (`TEST_API` declarations, TEST_HELP), M.TSC.001.
- **Blast carried by**: twin `TEST_API` → TWIN (Gaps).
- **Kind**: test

## tests_scripts/test_fatal_report_sites.py
### M.TSC.090 Every broad handler records a C-stack overflow first
- **From**: A.U30.19 (4); SRC_CORE GAP-G8 (`report_if_fatal`/`fatal_reported` live in `asy_print_log`, M.SRC_CORE.034).
- **Site**: new `tests_scripts/test_fatal_report_sites.py`.
- **Change**: AST walk of `src/` and every generated module (in memory): fails on a broad handler (`except Exception`/
  `BaseException`/bare) whose first statement is not `report_if_fatal(<its name>)` and that does not end in a bare
  `raise`, and on a function registered through `app.errorhandler(Exception)` not starting with
  `report_if_fatal(<its exception parameter>)`; the name resolves to `asy_print_log.report_if_fatal`; one fabricated
  bite.
- **Resolved**: A.U30.19 places the function in `base_classes.py`; M.SRC_CORE.034 moves it to `asy_print_log` (GAP-G8).
- **Unit**: U30
- **Depends**: M.SRC_CORE.034.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_fram_chunk_crc_sites.py
### M.TSC.091 Every FRAM chunk is created with a real CRC
- **From**: A.S0930.20 (7).
- **Site**: new `tests_scripts/test_fram_chunk_crc_sites.py`.
- **Change**: every `get_chunk(`/`get_timestamped_chunk(` call in `src/` passes `crc=` one of `CRC8()`, `CRC16()`,
  `CRC32()` (by `ast`; the module is `asy_crc_checks`); bite: a synthetic call without `crc=` fails.
- **Resolved**: —
- **Unit**: U16 (with the S0930 erase-gate rows; names per U10).
- **Depends**: M.TSC.001.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_fram_chunk_owner_sites.py
### M.TSC.092 Chunks and loggers are built only in constructors
- **From**: A.U16.02 (2).
- **Site**: new `tests_scripts/test_fram_chunk_owner_sites.py`.
- **Change**: in `src/`, every call of `get_chunk`, `get_timestamped_chunk`, `make_logger`, `PrintLogHistoryStore` and
  `ConfigManager` sits inside an `__init__` (extra allowed site: `make_logger()`'s own body in `asy_print_log.py`); in
  every generated `sensortask_<device>.py` (in memory, `DEVICE_NAMES`) every instance construction is a direct statement
  of `build_system()`'s body (never nested in `if`/`for`/`while`/`try`/`with`) and no other generated function constructs
  an instance. Modelled on the gc-site checker's attribution.
- **Resolved**: —
- **Unit**: U16
- **Depends**: M.GEN.005.
- **Blast carried by**: the L1 owner-order scenario → A.U16.02 (1) (TEST_HELP).
- **Kind**: test

## tests_scripts/test_frozen_first_shadowing.py
### M.TSC.093 A filesystem module never shadows a frozen one
- **From**: A.U25.58.
- **Site**: new `tests_scripts/test_frozen_first_shadowing.py`.
- **Change**: in a `tmp_path` cwd holding `asyncio.py` that prints `SHADOWED`, the Unix port runs the boot entry's path
  lines (read by AST from `generate_boot_entry_source()`: `import sys`, `sys.path.insert(0, ".frozen")`) then `import
  asyncio; print(asyncio.__file__)`: no `SHADOWED`, path starts `.frozen`; the premise run without the two lines prints
  `SHADOWED` (a check of the premise, harmonization 5 — not a CI control arm). Binary via the shared probe; missing fails.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.GEN.001, A.U27.12.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_frozen_inputs_reproducible.py
### M.TSC.094 Staged firmware inputs are reproducible <!--@frozen_inputs-->
- **From**: A.U27.34 (2).
- **Site**: new `tests_scripts/test_frozen_inputs_reproducible.py`.
- **Change**: for every `DEVICE_NAMES` device, a CPython subprocess run twice (`PYTHONHASHSEED=0`, `=4242`) stages the
  Python modules with `stage_python_modules()` into its own `tmp_path` under a fixed build date and prints `name  sha256`
  for every staged file plus the rendered manifest text; the outputs are byte-identical.
- **Resolved**: —
- **Unit**: U27
- **Depends**: A.U27.04, A.U27.05, A.U27.34 (SCR).
- **Blast carried by**: the website archive half → M.TSC.034.
- **Kind**: test

## tests_scripts/test_gc_collect_sites.py
### M.TSC.095 One checker confines every gc policy call, aliases included
- **From**: A.U27.21 (checker, live-tree and alias cases), A.U11.10 + A.U20.06 (the `src/` allowance:
  `run_setups`, `start_tasks`), A.U30.14 (threshold/disable/enable policy column), A.U30.16 (baseline, boot-mirror,
  timed-window and twin rows), A.U24.64 (the f9 soak row stays a baseline), A.U35.25 (sampler row conditional), M.TSC.001
  (`system_service.py` → `asy_system_service.py`), TWIN gap (two `tests/test_digital_twin_uart_link.py` rows keep their
  function names, M.TWIN.158), M.TWIN.055 (the unwedge helper is deleted: its conditional row is not written), HW_DEV
  (the probe/map functions moved into `_shared/`, M.HW_DEV.116/.117/.120); read: A.U16.02 (modelled on this file),
  A.U20.14 (unrelated), A.SDEP.17 (W38 re-check of the premise).
- **Site**: `tests_scripts/test_gc_collect_sites.py:1-74`.
- **Change**: imports `scripts/_check_gc_collect_sites.py` through `_script_loader` and asserts the live tree clean on
  every scope; the table's `src/` rows are `("asy_system_service.py", "run_setups")` and `("asy_system_service.py",
  "start_tasks")`; generated modules and boot entries (in memory, `DEVICE_NAMES`) no collect, each boot entry exactly
  one module-level `gc.threshold(<int>)`; `buildgen/` emits no `gc.collect`; threshold-with-argument allowed only in
  `tests/_threshold_runner.py`, `tests/microtest.py` (restore), `digital_twin/run_generic_integration.py`
  (`--gc-threshold`), `tests_hardware/device_scripts/`; `disable`/`enable` nowhere; collect rows — baseline:
  `tests/_boot_contiguity_probe.py` `_dump`, `tests/test_asy_fram_allocation_budget.py` `_priced`,
  `tests/test_asy_webserver_service.py` the f9 soak scenario, `tests/test_uart_comm_hazard.py` `_measure_retention`,
  `_hammer_clean.hammer`, `_hammer_faulted.hammer`, `tests/test_digital_twin_uart_link.py` the two named scenarios,
  `allocation_need_per_source.py` `_build_sieve`, `_release_sieve`, `_run`, `_shared/heap_probe.py`'s probe and map
  functions, `_shared/map_dump.py`'s dump, `serving_at_default_gc.py` `_observe`, `uart_link_under_concurrent_system_load.py`
  `_heap_floor`, `_main`; boot mirror: `_ProbeGc.collect` in the probe and in `heap_layout_after_full_boot_sequence.py`
  (both wrap `asy_system_service.gc`); before a timed window: `uart_driver_read_never_blocks_the_loop.py` `_trial`,
  `main`, `uart_idle_poll_rate.py` `_count_rounds`; twin: `run_generic_integration.py` `_mem_sampler` while A.U35.25's
  measurement keeps it (else the row goes with the line). Every row's function name is re-derived at the landing tree.
  Fabricated cases: `import gc as g; g.collect()` and `from gc import collect; collect()` outside the allowance
  reported, `bag.collect()` not; a renamed allowed function (stale row) reported; a test-body `gc.threshold(32768)` in
  `tests/`, a second threshold in a boot entry, a `gc.disable()` in `src/` reported; a zero-argument `gc.threshold()`
  read not reported; a collect in a fabricated `tests/test_x.py` body reported.
- **Resolved**: A.U27.21 lists `start_and_check_tasks`; A.U20.06 renames it `start_tasks` and A.U11.10 adds `run_setups`
  (M.SRC_CORE.015/.016) — the table carries the end names. A.U30.16's unwedge row is conditional on A.U25.39, which
  M.TWIN.055 lands — no row.
- **Unit**: U30 (stages U11/U20 allowance, U27 checker; U35 sampler row decision).
- **Depends**: A.U27.21 (`scripts/_check_gc_collect_sites.py`, SCR), M.SRC_CORE.015/.016, M.HW_DEV.116/.117/.120.
- **Blast carried by**: the moved `test_lint_sh.py` grep cases → {{lint_sh}}; SPEC I.4(f.1) → A.U27.21/A.U30.14 (SPEC).
- **Kind**: test

## tests_scripts/test_http_client_ceiling_close.py
### M.TSC.096 Ceiling-close cases follow the refused-connection class
- **From**: A.U26.70 (cases adapt to `CeilingRefusedError`), A.U36.548 (6) (`:1` "two bench tests" → "the bench tests"),
  A.U8C2.16 (read: `:82-100` pins the retry count 3 — unchanged), A.U24.13 (read: `:14` insert unchanged).
- **Site**: `tests_scripts/test_http_client_ceiling_close.py:1-100`.
- **Change**: docstring "…the predicate the bench tests use…" (or names `CeilingRefusedError` if `is_ceiling_close()`
  goes with its callers' switch); a `CEILING_CLOSE` exception before any response byte surfaces from `fetch()` as
  `CeilingRefusedError` (cause kept), one after the first byte does not; `is_ceiling_close(exc)` is
  `isinstance(exc, CeilingRefusedError)` while it exists; the retry wrapper's three-outcome case holds.
- **Resolved**: —
- **Unit**: U26 (U36 docstring word).
- **Depends**: M.HW_BENCH.030.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_http_client_shape_parity.py
### M.TSC.097 The hardware and twin HTTP clients keep one shape
- **From**: A.U26.70 (2).
- **Site**: new `tests_scripts/test_http_client_shape_parity.py`.
- **Change**: `ast` over `tests_hardware/http_client.py` and `digital_twin/_http_client.py` (no import of the latter):
  same `HttpResponse` attribute names (`status_code`, `headers`, `body`, `drained`), same `json()` return annotation form,
  same `fetch()` parameter names in order (`host, port, method, path, json_body, timeout_s, read_body`; the twin's being
  `async` the one allowed difference), both define `CeilingRefusedError`; a drift fails naming the member.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.030, A.U25.31 (twin client, TWIN).
- **Blast carried by**: the two clients' docstrings name this file → M.HW_BENCH.030 / A.U25.31.
- **Kind**: test

## tests_scripts/test_import_graph.py
### M.TSC.098 The import graph: no cycles, no driver-to-driver edge, named dynamic loads <!--@importgraph-->
- **From**: A.U10.30; HW_BENCH GAP-B4 (the conformance `exec()` exception moves to `digital_twin/run_device_script.py`,
  M.HW_BENCH.038/.091, M.TWIN.054); TEST_HELP GAP-H6 (`tests/_generated_module.py` `load_generated`).
- **Site**: new `tests_scripts/test_import_graph.py`.
- **Change**: parses `src/`, `ext/` and every generated module built into `tmp_path` (`DEVICE_NAMES`): static edges
  after `TYPE_CHECKING` stripping; fails on a cycle, a sensor driver (`asy_*_driver.py` with a `*_Reader`) importing
  another driver, `asy_print_log.py` importing `asy_fram_manager` at runtime, a name imported from a module that
  re-exports rather than defines it, a module name in both `src/` and `ext/`; repo-wide AST scan: any `__import__`,
  `exec`, `eval` call or `import importlib`/`from importlib …` outside SPEC F.1's named list fails. The list (one place,
  read from SPEC F.1's table or mirrored in the test with a pin to it): `tests/_generated_module.py` (`load_generated`),
  `digital_twin/run_generic_integration.py` (device module by config), `buildgen/validate.py` (loads
  `toolchain/micropython_overrides.py` by path), `tests_scripts/_script_loader.py` (a `scripts/`/`toolchain/` file by
  path), `tests/_coverage_runner.py`, `tests/_threshold_runner.py` (execute a test file), `digital_twin/run_device_script.py`
  (renders and executes a device script under the twin; replaces `tests_hardware/isl29125_conformance.py:35`).
- **Resolved**: GAP-B4 moves the conformance exception's site; `test_buildgen_validate.py` patches `importlib` by dotted
  name (M.TSC.055), so it needs no entry.
- **Unit**: U26 (stage U10; the site moves with M.HW_BENCH.038 in U26).
- **Depends**: A.U10.30 (`tests/_generated_module.py`, TEST_HELP), M.TWIN.054.
- **Blast carried by**: SPEC F.1 list → A.U10.30/GAP-B4 (SPEC).
- **Kind**: test

## tests_scripts/test_import_placement.py
### M.TSC.099 No function-level or dynamic import outside the named list <!--@importplacement-->
- **From**: A.U0.07, A.U37.02 (`_PENDING` removed once empty), TEST_HELP GAP-H6 (this cluster's `_PENDING` entries leave
  in U24; `_NAMED_EXCEPTIONS` holds `load_generated` and the two runners' `exec`), HW_BENCH GAP-B4, HW_BENCH M.HW_BENCH
  (its `_PENDING` entries leave in U26), TEST_UNIT (`tests/test_asy_isl29125_driver.py:1301, 1306` entries leave with
  the module-level `import time`).
- **Site**: new `tests_scripts/test_import_placement.py`.
- **Change**: AST walk over every `.py` in `src/`, `buildgen/`, `digital_twin/`, `tests/`, `tests_scripts/`,
  `tests_hardware/`, `scripts/`, `toolchain/` (skipping `tests/_tmp/`): fails on an `Import`/`ImportFrom` inside a
  function body, and on `__import__`, `importlib.import_module`, `importlib.util.spec_from_file_location`/
  `module_from_spec`/`exec_module`, or `exec()`/`compile(…, "exec")` of a file's source, unless in `_NAMED_EXCEPTIONS`
  (SPEC F.1's list — the same seven entries as {{importgraph}}) or `_PENDING` (keyed `(path, qualname, module or call)`,
  the HEAD set); a second test fails on a `_PENDING` entry that no longer occurs. Staged: U0 with the HEAD set; U10 names
  the dynamic sites; U24 empties `tests/`'s; U25 `digital_twin/`'s; U26 `tests_hardware/`'s (GAP-B4 site included);
  U27 `tests_scripts/`'s (85 entries in 13 files) and `scripts/`'s; U37 removes `_PENDING` and its test.
- **Resolved**: —
- **Unit**: U37 (stages U0, U10, U24-U27).
- **Depends**: each owning unit's import moves.
- **Blast carried by**: `pyproject.toml` PLC0415 entries leave per scope → A.U0.07/A.U37.02 (TOOL).
- **Kind**: test

## tests_scripts/test_js_api_mirrors.py
### M.TSC.100 The JS wire-fact mirror and the derived dispatch fields are pinned
- **From**: A.U23.25 (result words, `isUnavailable()`, `COUNTER_CAP`), A.U23.24 (`GMTIME_KEYS`), A.U23.26 (response code
  table), A.U23.27 (definitions vs `src/` dispatch facts), A.S0930.20 (2) (`SystemCmd` covers both new words; bite drops
  `"erasefram"`).
- **Site**: new `tests_scripts/test_js_api_mirrors.py`.
- **Change**: reads the Python side by `ast` — the four result-word `Final`s (`src/asy_config_manager.py`),
  `COUNTER_CAP = const(0x3FFFFFFF)` (`src/asy_base_classes.py`), the `'{"error":"unavailable"}'` literal in
  `_write_guarded()`, the first six keys of `_gmtimestruct_to_dict()`'s template dict (`buildgen/codegen.py`), and
  `_STANDARD_CODES` — and the JS side by regex (`js/api-contract.js`; `COUNTER_CAP` in `js/mock-server.js`; the code
  table); asserts equality; per device, the generated `SystemCmd` option values equal `_SYSTEM_CMDS`, `PauseTime` min/max
  equal `_PAUSE_TIME_FIELD`'s, `lightCmdLED` sub-field names and bounds equal `_LIGHT_CMD_FIELDS` (all `ast` from
  `src/asy_webserver_service.py`); bites on temp copies: a planted mismatch, and a definitions dict with `"erasefram"`
  dropped.
- **Resolved**: —
- **Unit**: U23 (S0930 row with the command words).
- **Depends**: A.U23.24-.27 (WEB), M.GEN.015.
- **Blast carried by**: JS side → WEB.
- **Kind**: test

## tests_scripts/test_legacy_paths.py
### M.TSC.101 No current file names a pre-move legacy path
- **From**: A.U1.09; A.U1.10 (read: CLAUDE.md names this file).
- **Site**: new `tests_scripts/test_legacy_paths.py`.
- **Change**: three tests, docstring ≤ 3 lines: (1) `test_no_current_file_names_a_pre_move_legacy_path` over `git
  ls-files` (git from `shutil.which`), skipping `legacy/`, `arduino/`, `datasheets/`, `audit/`, `PROJECT_AUDIT_PLAN.md`,
  this file and non-UTF-8 files, with A.U1.09's validated pattern; (2) the pattern's property test (each pre-move form
  hits, each new path and each real look-alike does not); (3) `test_the_legacy_tree_is_where_the_rules_say` (no tracked
  path under the old roots; the `legacy/firmware/…` set, four `build-*.sh`, `legacy/dev_drivers/`, `legacy/README.md`
  tracked). The `audit/`/`PROJECT_AUDIT_PLAN.md` exclusions go in phase D's close commit.
- **Resolved**: —
- **Unit**: U1
- **Depends**: A.U1.01-A.U1.04 (the move).
- **Blast carried by**: CLAUDE.md legacy rule → A.U1.10 (DOC).
- **Kind**: test

## tests_scripts/test_level_containment.py
### M.TSC.102 Level containment is checked, not stated
- **From**: A.U7.24 (check), A.U26.51 (the constants' content), A.U7.01 (read: SPEC E.6 cites it).
- **Site**: new `tests_scripts/test_level_containment.py`.
- **Change**: every L3/L4 module declares `COVERS_TWIN_SCENARIOS`; twin scenario IDs are the stems of
  `tests/test_digital_twin_*.py` (per-device families collapsed) and `ci_suite.<function>` for each function
  `run_suite()` calls; AST only: (1) every twin ID covered or in SPEC E.6's exception list with a reason; (2) every
  named ID exists; (3) `run_bench_hardware_suite.sh` runs the flash tier first and every flash bus-hazard test names a
  bench counterpart or an exception row; (4) family sizes equal `_devices.DEVICE_NAMES`; (5) no exception row names a
  covered scenario. Twin scenario IDs read the post-U25 file set (the in-DUT scenarios moved to
  `scripts/_digital_twin_scenarios.py`, A.U25.46 — their IDs are `scenarios.<name>` from that module's registry).
- **Resolved**: A.U7.24's ID scheme predates A.U25.46's move of the in-DUT HTTP scenarios out of `tests/`; the moved
  scenarios join the ID space by their registry name (agent decision D-TSC3).
- **Unit**: U26 (stage U7 with the scheme; U26 fills the constants).
- **Depends**: A.U25.46 (SCR/TWIN), A.U26.51 (HW_BENCH/HW_DEV modules).
- **Blast carried by**: SPEC E.6/E.6.6 → A.U7.25/A.U26.51 (SPEC).
- **Kind**: test

## tests_scripts/test_lint_ceilings.py
### M.TSC.103 Every lint ceiling sits at its measured maximum
- **From**: A.U5.18, A.U5.17 (read: the `max-args` comment names this file).
- **Site**: new `tests_scripts/test_lint_ceilings.py`.
- **Change**: for each ruff ceiling in `pyproject.toml`, `ruff check --select <rule> --config <option>=<value-1>` over
  the eight scopes finds at least one finding and at `<value>` none; an AST walk lists every function above `max-args`
  and requires exactly the exempt set (`src/asy_uart_driver.py` `UART.__init__`, `UART.init`;
  `src/asy_isl29125_driver.py` `ISL29125_I2C.configure`; `tests/machine.py` and `digital_twin/machine.py` `UART.__init__`,
  `SPI.__init__` — class names as renamed by A.U10.38); every `src/` `__init__` with a `log` parameter ends
  `(…[, max_module_error][, name_ext][, cfg_path], log[, logger])`. Bites: a ceiling raised by one, a ninth parameter on a
  non-exempt function. The JS half is `tests_js/lint-ceilings.test.js` (WEB).
- **Resolved**: —
- **Unit**: U5 (re-measured at landing of each later unit that moves a ceiling).
- **Depends**: A.U5.17 (TOOL).
- **Blast carried by**: JS half → A.U5.18 (WEB).
- **Kind**: test

## tests_scripts/test_lint_type_scopes.py
### M.TSC.104 One test pins the three mypy configs and every lint scope
- **From**: A.U27.24, A.U27.25 (CI's explicit mypy paths), A.U27.23 (the two single-file runs).
- **Site**: new `tests_scripts/test_lint_type_scopes.py`.
- **Change**: (1) all three mypy configs: `strict`, `no_implicit_optional`, `warn_unreachable`, `enable_error_code ⊇
  {ignore-without-code}`, `disallow_any_explicit` once on; `no_implicit_reexport = false` only in the main pass; the only
  `[[tool.mypy.overrides]]` are named with their reason; (2) `EIGHT_SCOPES` plus `build/generated_src` equal `lint.sh`'s
  ruff list and CI's ruff step, `shellcheck` covers `scripts/*.sh`; (3) every `*.py` under the scopes is checked by at
  least one mypy run (main `files` minus excludes, the twin pass's `files`, the host pass, `tests/network.py` and
  `tests_scripts/conftest.py` alone) and none by two runs with different resolution except a named, reasoned list; (4)
  `ci.yml`'s mypy step passes exactly the main pass's `files`.
- **Resolved**: —
- **Unit**: U27
- **Depends**: A.U27.22-.25 (TOOL/SCR).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_lock_order.py
### M.TSC.105 The lock-order table is complete and obeyed
- **From**: A.U10.16; SRC_SENS GAP-13 (`ISL29125_Reader._threshold_lock`; private session attributes `self._i2c_<chip>`,
  M.SRC_SENS.080).
- **Site**: new `tests_scripts/test_lock_order.py`.
- **Change**: reads SPEC C.8's table between `<!-- locks:begin -->`/`<!-- locks:end -->` (every lock attribute in `src/`
  after A.U10.18/A.U10.35, with level and "may be held while taking", `ISL29125_Reader._threshold_lock` included); parses
  every `src/*.py`: each `async with <expr>`/`<expr>.acquire()` resolves to a table entry by attribute name
  (`self._i2c_<chip>`/`self._spi_<chip>` and their public forms where a class keeps one → the session level;
  `.i2c_device`/`.spi_device` → level 1); fails on an untabled lock attribute, a lower level taken before a higher one
  within a function, or any acquisition inside a leaf lock. Negative cases on `tmp_path` copies.
- **Resolved**: A.U10.16's resolver is written for `self.i2c_<chip>`; A.U10.35 privatises them — the resolver matches the
  private form (GAP-13).
- **Unit**: U10 (after A.U10.35 in the same unit; the ISL29125 row lands with M.SRC_SENS.080's unit).
- **Depends**: A.U10.16 (SPEC C.8 table), A.U10.35.
- **Blast carried by**: SPEC C.8 table row → GAP-13 (SPEC).
- **Kind**: test

## tests_scripts/test_measurement_field_tuple_agreement.py
### M.TSC.106 Each driver's fields bound to its own tuple; SCD30's always-set pinned
- **From**: A.U24.57 (1), A.U28.30 (5) (`:30` typed loop, the `attr-defined` ignore goes), SRC_SENS GAP-11 (SCD30 backend
  `always=` tuple vs fields tagged `alwaysExecuted=true`, `ContMeas` aside, M.SRC_SENS.053); read: A.U15.12, A.U15.19,
  A.U15.36 (tuple and `_FIELDS` change together — holds).
- **Site**: `tests_scripts/test_measurement_field_tuple_agreement.py` (whole file, `:30`).
- **Change**: the tuple `_FIELDS` must equal is the NamedTuple the module's reader passes as the first positional argument
  of its `super().__init__(...)` call (AST `Call` whose `func` names the tuple); a module whose reader passes none fails
  naming it; `:30` builds the tuple in a typed loop (no `# type: ignore`); new: SCD30's backend `always=` tuple (`ast`)
  equals the `@web` fields tagged `alwaysExecuted=true` minus `ContMeas`, read through `buildgen.web_tag`.
- **Resolved**: —
- **Unit**: U28 (stages U15 GAP-11 row, U24 binding).
- **Depends**: M.SRC_SENS.053, A.U6.17 (tag key).
- **Blast carried by**: the L1 nested-body half → A.U24.57 (2) (TEST_UNIT).
- **Kind**: test

## tests_scripts/test_memory_catalog.py
### M.TSC.107 Every module catalogued; no unlisted run-phase allocation
- **From**: A.U30.03; SRC_CORE GAP-G9 (`FRAMManager._chunks`, M.SRC_CORE.091); SRC_NET gap 3 (renamed WiFi sites,
  M.SRC_NET.092).
- **Site**: new `tests_scripts/test_memory_catalog.py`.
- **Change**: header (≤ 3 lines) "SPECIFICATION.md I.2 classifies every module's allocations; run-phase code allocates
  nothing long-lived except the listed, reasoned cases."; (1) SPEC I.2's text names every `src/*.py` basename (by
  `Path.glob`) plus "generated device modules" and "generated boot entry"; (2) an AST walk of `src/*.py`: in every method
  other than `__init__`/`setup`, `self.<attr> = <constructor call | display | comprehension | bytearray/bytes/memoryview/
  list/dict/set/create_task>` must be a key of `_RUN_PHASE_ALLOWED[(module, "Class.method", attr)] = reason`, the rows
  being A.U30.02 (5)'s list as the landing tree has it — class and method names after A.U10.35/A.U10.38 (e.g.
  `asy_wifi_service.py`/`WifiService._connect_loop`, the LED-flash task, `._switch_wlan_mode`/`wlan`), and
  `asy_fram_manager.py`/`FRAMManager.<allocating method>`/`_chunks` "grows once per allocation at construction" (GAP-G9).
- **Resolved**: —
- **Unit**: U30
- **Depends**: A.U30.02 (SPEC I.2), M.SRC_CORE.091, M.SRC_NET.092.
- **Blast carried by**: SPEC I.2 rows → A.U30.02/GAP-G9 (SPEC).
- **Kind**: test

## tests_scripts/test_memory_error_gate_agreement.py
### M.TSC.108 Every allocation gate agrees, the JS and heap-map gates included <!--@gate_agreement-->
- **From**: A.U7.23 (JS gate, smoke and live-command imports, the two twin-boot files), A.U26.47 (`heap_map` joins the
  hardware list), A.U14.05 (`:12-14` comment gains the placement condition), WEB gap 7 (the import now sits in
  `tests_js/_twin_process.js`, M.WEB.082); read: A.U35.05 (plants live in a throwaway worktree; the gate changes only if
  blind), A.U14.26 (injections use "simulated allocation failure"), A.SDEP.02, A.U20.04, A.U36.002, A.U8.20, A.U8C2.20.
- **Site**: `tests_scripts/test_memory_error_gate_agreement.py:1-30`, new tests.
- **Change**: docstring names the gates by name (unit, twin, flash, bench, heap map, JS) instead of "four"; `:12-14` →
  "# The interpreter's own MemoryError wordings (py/runtime.c:1692/1696, v1.29.0). The message is placed only while an
  / # emergency exception buffer exists, which the boot entry reserves - without one it is empty. src/ logs str(e), so
  / # the second marker sees a caught degrade; the class name appears only in an uncaught traceback."; `_HARDWARE_TIER_FILES`
  gains `tests_hardware/heap_map.py`; new `test_the_js_gate_agrees_with_it` (parses `tests_js/_memory_markers.js`'s array
  literal), a check that `tests_js/_twin_process.js` and `scripts/cross_browser_smoke.mjs` import it (the two
  `_live_*_command.js` modules reach it through `_twin_process.js`), and that `test_digital_twin_generated_boot.py` and
  `test_digital_twin_boot_contiguity.py` reference `MEMORY_ERROR_MARKERS`.
- **Resolved**: A.U7.23 names the two command modules as importers; M.WEB.082 moves the import into
  `_twin_process.js` (WEB gap 7) — the check follows the import's home.
- **Unit**: U26 (stages U7, U14).
- **Depends**: M.WEB.082, M.HW_BENCH.035.
- **Blast carried by**: CLAUDE.md gate count → A.U7.23 (DOC).
- **Kind**: test

## tests_scripts/test_mypy_any_baseline.py
### M.TSC.109 The explicit-`Any` flag is on everywhere; the baseline ends empty
- **From**: A.U8.24 (create: flag set in all three configs; every baseline module still exists), A.U34.11 (2) (no
  baseline section, no `false` anywhere), A.U37.02 (the baseline mechanism removed once empty); read: A.U10.46,
  A.U15.43, A.U18.44, A.U19.17, A.U23.47 (each shrinks the list), A.U36.527 (doc).
- **Site**: new `tests_scripts/test_mypy_any_baseline.py`.
- **Change**: staged — U8: the three configs set `disallow_any_explicit = true`; every module in a baseline override/
  section exists (a renamed or deleted module cannot linger); U34: no section or override sets it `false` (a new
  per-module exemption fails); the existence check goes with the list (U37, A.U37.02).
- **Resolved**: A.U34.11 empties the list in U34; A.U37.02 removes the mechanism — the U34 form is already the
  no-baseline check, so U37 only deletes the dead existence check.
- **Unit**: U34 (stages U8; U37 removal).
- **Depends**: A.U8.24/A.U34.11 (TOOL).
- **Blast carried by**: `pyproject.toml`/`.ini` baseline lists → A.U8.24/A.U34.11 (TOOL).
- **Kind**: test

## tests_scripts/test_no_variant_literals.py
### M.TSC.110 No variant literal outside the device TOMLs <!--@novariant-->
- **From**: A.U6.15, A.U37.02 (`_NOT_YET_CLEANED` removed once empty), A.U37.10 (committed fixtures excluded).
- **Site**: new `tests_scripts/test_no_variant_literals.py`.
- **Change**: variant names = `DEVICE_NAMES`; scanned: every `git ls-files` path except `devices/`, `*.md`, `audit/`,
  `legacy/`, `ext/`, `datasheets/`, `arduino/`, lock files, and the committed fixtures `tests_scripts/golden/` and
  `tests_scripts/fixtures/api_reference/` (data read from the devices, A.U37.10); a non-homonym name matches as a
  case-insensitive substring anywhere; a homonym (`dev`) only in variant-shaped forms (A.U6.15's list, with its
  path-join and `iw`/`tc` argv exceptions); `_NOT_YET_CLEANED: dict[str, str]` maps each file still carrying a literal at
  landing to the content change that removes it (never an audit label), a stale entry fails, and the dict is removed at
  U37; self-test on a temp tree (comment/string/identifier fail; `/dev/ttyACM0`, `libffi-dev`, `dev-tooling`,
  `["iw", "dev", iface]`, `["qdisc", "del", "dev", iface]`, `tmp_path / "dev"` pass; `SensorStationWozi`, `woziData`,
  `SensorStationDev` fail).
- **Resolved**: —
- **Unit**: U37 (stage U6).
- **Depends**: M.TSC.002.
- **Blast carried by**: CLAUDE.md/SPEC L.1 name the check → A.U6.15 (DOC/SPEC).
- **Kind**: test

## tests_scripts/test_one_entry_per_event.py
### M.TSC.111 No two persisted log entries for one event on one path
- **From**: A.U3.11.
- **Site**: new `tests_scripts/test_one_entry_per_event.py`.
- **Change**: AST scan of every function in `src/*.py` and every generated module: two persisted `err_s`/`wrn_s` calls on
  one straight-line path with no `return` between fail unless allow-listed with both events named and why they differ;
  the list is the U3 tree's pairs with A.U3.11's reasons (ISL `_recover_brownout()`, `_check_divergence()`; UART
  `_resync()`; `_get_dict_cfg()`; `_set_dict_cfg()`; `set_write_protected()`; `ConfigManager.setup()` (two); SGP40
  `_read_sgp()`; WEBSERVER `_serve()`), each keyed by function name and catalog names (not numbers), re-derived at
  each later landing that renames a function; `_close_writer()` is not listed; bite: a planted second `err_s`.
- **Resolved**: —
- **Unit**: U3
- **Depends**: A.U3.03-A.U3.09 (SRC).
- **Blast carried by**: cross-function pairs → their L1 tests (A.U3.03-.09, A.U3.14; TEST_UNIT).
- **Kind**: test

## tests_scripts/test_readiness_gates.py
### M.TSC.112 Every class with an async `setup()` gates on readiness
- **From**: A.U10.22 (L0 half); SRC_SENS GAP-17 per the lead's ruling (AC_NOTES 38); SRC_NET gap 3 (`WifiService`'s
  `setup()` override, `SensorReaderConfig`, `UARTLinkDriver` gains the flag, M.SRC_NET.213/.215).
- **Site**: new `tests_scripts/test_readiness_gates.py`.
- **Change**: AST over `src/`: every class defining `async def setup` assigns `self.initialized = False` in `__init__`
  and `True` inside `setup()` (or inherits both from a base that does, resolved within `src/`), except a named list
  with reasons: `ConfigManager` (`valid`), `NotificationService` (`_finalized` is its gate), and the protocol classes
  `BMP3XX_I2C`, `SCD30_I2C`, `SGP40_I2C`, `ISL29125_I2C` plus `I2CDevice` ("build everything in `__init__`; `setup()`
  only probes and configures the chip"); `NeopixelDriver` is checked (it gains the gate); every `deinit`/`close`/
  `disconnect`/`stop_*`/`cleanup` method on a class with no `self.pr` returns `-> bool`, except chip commands
  (`stop_*` on a `*_I2C` protocol class) and `_TimeoutStreamProxy.close` (a mirror, by name).
- **Resolved**: GAP-17 — the lead's ruling (AC_NOTES 38): protocol classes and `I2CDevice` named exempt,
  `NotificationService`'s `_finalized` counts as its gate, `NeopixelDriver` gets `initialized`.
- **Unit**: U10 (after A.U13's `deinit()` changes; until then they are listed pending).
- **Depends**: M.SRC_SENS (NeopixelDriver gate), M.SRC_NET.213/.215, A.U10.21.
- **Blast carried by**: the L1 half → M.TEST_UNIT (A.U10.22 L1); SPEC C.13 → A.U10.22 (SPEC).
- **Kind**: test

## tests_scripts/test_readme_reference.py
### M.TSC.113 README's command reference equals every tool's `--help`
- **From**: A.U36.547 (7).
- **Site**: new `tests_scripts/test_readme_reference.py`.
- **Change**: imports the tool set from `test_tool_help.py` (the shared list, a module-level constant there); per tool runs
  `--help` and compares its option names (`--x`/`-x`) and environment-variable names with the README block's options and
  variables (equal sets, every Meaning non-empty); every README block names a tool in the set and every tool has a
  block; `package.json` scripts equal the README's npm table; every tracked `*.md` other than README.md and licence files
  outside `legacy/`, `audit/`, `arduino/`, `node_modules/` is named in "Further reading"; mutation fixtures (a README row
  removed, an extra option in a stub tool's help, an unmapped `.md`) fail.
- **Resolved**: —
- **Unit**: U36
- **Depends**: {{tool_help}}, A.U36.547 (DOC).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_micropython_overrides.py
### M.TSC.114 Module-level tests, build-flavour names, derived devices, fail not skip
- **From**: A.U24.75 (3) (nine `Test*` classes → module-level `def test_<class_snake>_<method>`), A.U36.512 (variant →
  build flavour in names and text at `:174-230`), A.U7.26 (`:48`, `:350` skip → fail), A.U24.51 (`:488-495` →
  `DEVICE_NAMES`), A.U24.73 (`Any`), A.U21.17 (fake `run`s accept the new keyword-only shape at `:153, :181, :243,
  :813`), A.U27.29 (read: `pytest.raises(OverrideError)` holds — its base changes), A.SDEP.08 (read: `:857` fixture literal
  stays), A.SDEP.03, A.U8.14, A.U21.03, A.U21.15 (read: fakes unaffected).
- **Site**: `tests_scripts/test_micropython_overrides.py` (whole file; classes at `:44, 69, 135, 347, 373, 462, 680, 780,
  804`).
- **Change**: every class becomes module-level functions with module fixtures and `parametrize` (no `Test*` class
  remains, including the classes U21 adds — they are written in function form from the start);
  `test_the_test_rig_variant_is_built_without_the_settrace_flag` → `…_test_rig_flavour_…`,
  `test_the_coverage_variant_gets_the_flag_and_its_own_build_dir` → `…_coverage_flavour_…`, "variant" → "build flavour"
  in the other named lines (`test_the_constructed_make_command_carries_variant_and_variant_dir` keeps MicroPython's
  `VARIANT`/`VARIANT_DIR`); a missing toolchain checkout fails naming `toolchain/setup_toolchain.py setup`; the per-device
  loop is `@pytest.mark.parametrize("device", DEVICE_NAMES)`; fake `run`s take `(cmd, cwd=None, *, capture=False,
  timeout_s=None, retries=0, redact=())`-shaped keywords as A.U21.17 defines them; no `Any`.
- **Resolved**: A.U21.06/.11/.12 add classes in U21; A.U24.75 forbids classes in U24 — written as functions at once.
- **Unit**: U24 (stages U7, U21; U36 wording).
- **Depends**: A.U21.17 (`run()` signature, TOOLCHAIN/SCR).
- **Blast carried by**: SPEC E.2.1 → A.U24.75 (SPEC).
- **Kind**: test

### M.TSC.115 The SIGINT override is proven in every built Unix binary
- **From**: A.U21.06 (readback tests; `:83-96` header gains the sentinel; fake `make` branches), A.SDEP.11 (conditional:
  if upstream made deferred delivery the Unix default, the override and its tests `:40-270` go).
- **Site**: `tests_scripts/test_micropython_overrides.py:40-270`.
- **Change**: the generated header test asserts the sentinel line and keeps the "include before #undef" order;
  `fake_run` returns "LINK …" for `make` and gains a branch for the `…/unix_kbd_intr` preprocessed output; new
  readback tests over fake `.pp` texts: clean passes; no sentinel → named error; last define `(1)` → named; `nlr_jump(`
  in the handler body → named; no `sighandler` → named "re-verify"; the `make` command carries the build's own
  `VARIANT`/`VARIANT_DIR`. If A.SDEP.11's re-check finds deferred delivery upstream-default at the new pin, the override's
  tests are deleted with the override (and B.14.1/F.6 follow, SPEC).
- **Resolved**: —
- **Unit**: U21 (A.SDEP.11's branch decided at the pin refresh, U0/U37 per OR129).
- **Depends**: A.U21.06 (TOOLCHAIN), A.SDEP.11.
- **Blast carried by**: SPEC B.14.1/F.6 → A.SDEP.11/A.U21.06 (SPEC).
- **Kind**: test

### M.TSC.116 Override paths quoted; every anchor counted
- **From**: A.U21.08 (`:105-112`, `:398-418` quoted `!r` forms; refusal cases), A.U24.40 (`:347-350` the anchor check
  counts).
- **Site**: `tests_scripts/test_micropython_overrides.py:105-112`, `:347-418`.
- **Change**: manifest/board-cmake assertions take `f"include({str(path)!r})"`; new: a path with a space and one with `"`
  → `OverrideError` naming the character, nothing written; a relative `overrides_dir` → every generated include line is
  absolute; `:347`: besides the verify call, each of the 18 anchors of `_EVERY_LWIP_ANCHOR` occurs in the file
  `verify_lwip_connection_counts_anchor()` reads it from, and the three relayed board files are present.
- **Resolved**: —
- **Unit**: U24 (stage U21).
- **Depends**: A.U21.08 (TOOLCHAIN).
- **Blast carried by**: —
- **Kind**: test

### M.TSC.117 lwIP and modlwip overrides: anchors, copies, build readback, third binary
- **From**: A.U21.10 (`_write_fake_lwip_tree()` gains the modlwip anchors; `:804-880` both overrides applied), A.U21.11
  (modlwip anchor/apply/readback tests), A.U21.12 (third, `lwip`-flavour Unix binary; `:217-232` structural tests gain
  it), A.U21.16 (`:194-203` `CFLAGS_EXTRA` assertion per the GCC branch), A.U21.29 (`:855-859` match `\[lwip\]`), A.U21.31
  (`:643-646` test name and comment), A.U14.30 (read: `:625-647`, `:485-495` messages unchanged), A.SDEP.14 (read: the
  lwIP tests are the re-verify's coverage), A.U8.14 (read: `:463-560` ensemble checks unchanged).
- **Site**: `tests_scripts/test_micropython_overrides.py:194-232`, `:274-880`.
- **Change**: the fake tree carries `extmod/modlwip.c` with the loop, the insertion point and the include, the
  `extmod.cmake` line and the three CMake lines; modlwip tests: the real pinned source passes (after a toolchain build;
  missing fails), each anchor dropped raises `OverrideError` naming it, the parametrisation covers every anchor the
  code checks, the loop present twice or the CMake lines out of order are refused; apply returns `{"USER_C_MODULES":
  …}`, never writes inside the fake tree (recursive listing/mtime compare), the copy differs from the pinned text by
  exactly the insertion and include hunks (`difflib`), the inserted block sits after `tcp_output()`'s `ERR_OK` check and
  before `MICROPY_PY_LWIP_EXIT`/`mp_hal_delay_ms(50)`, the generated `micropython.cmake` is pinned byte for byte,
  idempotent, nothing written on a missing anchor; readback: `build.make` naming the copy + object passes, naming the
  original or both → named error, no `build.make` → "layout changed", object missing/empty → named; structural:
  `build_firmware()` calls both `apply_modlwip_eagain_override` and `verify_modlwip_eagain_in_build`; the `lwip` flavour
  build is recorded with its own variant dir and the modlwip override; `:194-203` → per A.U21.16's branch (2a: no
  `CFLAGS_EXTRA` argument carries `MICROPY_PY_SYS_SETTRACE`; 2b: the generated variant mk/board cmake carry the one-file
  suppression and no global flag remains); `:855-859` `match=r"\[lwip\]"`;
  `test_the_mem_size_floor_is_the_fielded_designs_own_share` → `…_is_the_earlier_configurations_share`, comment keeps
  "8000 / 4 = 2000".
- **Resolved**: —
- **Unit**: U21
- **Depends**: A.U21.09-.12, A.U21.16, A.U21.29, A.U21.31 (TOOLCHAIN).
- **Blast carried by**: host lwIP hammer → A.U21.13 (TOOLCHAIN/TEST_UNIT); `test_test_sh.py` second loop → {{test_sh_lwip}}.
- **Kind**: test

## tests_scripts/test_microtest.py
### M.TSC.118 The unit runner's contract and the test-tree conventions it relies on
- **From**: A.U7.07 (runner behaviour on tmp files), A.U24.03 (`async def test_*` and `sys.exit` inside a test), A.U24.04
  (canonical trailer), A.U24.08 (no `asyncio.run(` outside `tests/_async_harness.py`), A.U24.11 (unique scratch keys),
  A.U24.60 (`json.loads(` only in `_strict_json.py` and the allow-list), A.U24.76 (no module-level `class Fake…`/`def
  make_…` in a `tests/test_*.py` file).
- **Site**: new `tests_scripts/test_microtest.py`.
- **Change**: runner cases (tmp test files, `micropython_bin`, `MICROPYPATH=tests`): one Skip + one pass + one fail →
  the `SKIP`/`PASS`/`FAIL` lines, closing `1/3 passed, 1 failed, 1 skipped`, exit 1; no `test_*` function → exit 1 with the
  "no test_* functions" message; an `async def test_x` → exit 1, `FAIL test_x … async`; `sys.exit(0)` inside a test →
  exit 1, `ABORT`, no later test run. Static checks over `tests/` (AST, each with a floor so it cannot pass vacuously):
  every `tests/test_*.py` (≥ 80) ends with exactly `if __name__ == "__main__":` / `import microtest` /
  `microtest.run(globals())`, has no module-level `async def test_*`, and binds `test_*` only to functions or
  `register_for_device()` results; `asyncio.run(` only in `tests/_async_harness.py` (≥ 1 there); `json.loads(` only in
  `tests/_strict_json.py` plus the named non-response reads; no module-level `class Fake…`/`def make_…` in a test file;
  `TmpScratch(<key>)` keys (literal, or an f-string prefix expanded over `DEVICE_NAMES`) unique across files and never
  colliding with another file's literal (≥ 10 keys found).
- **Resolved**: —
- **Unit**: U24 (stage U7 for the runner cases).
- **Depends**: A.U7.07, A.U24.03/.04/.08/.11/.60/.76 (TEST_HELP/TEST_UNIT).
- **Blast carried by**: SPEC E.2/E.2.1 → those actions (SPEC).
- **Kind**: test
