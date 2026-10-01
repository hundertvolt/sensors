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
  against. The check (`test_no_variant_literals.py`, M.TSC.110) covers `tests_scripts/` with an exclusion list only for
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
  hiding becomes a quoted name. New L0 `tests_scripts/test_host_annotations.py` (M.TSC.199) fails when a host file
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
  the same commit (M.TOOL.030: every `ANN401` entry goes).
- **Resolved**: —
- **Unit**: U24
- **Depends**: A.U20.32 (`TomlDoc` typed, GEN), A.U8.24 baseline (TOOL).
- **Blast carried by**: `pyproject.toml` exemption → M.TOOL.030.
- **Kind**: test

### M.TSC.005 Follow the unit-suffix rename `trigger_sec` → `trigger_s`
- **From**: A.U10.43.
- **Site**: `_toml_fixtures.py:37`; `test_buildgen_validate.py:410, 466, 728, 758-770`; `test_buildgen_generate.py:150`;
  `test_buildgen_tag_comments.py`, `test_buildgen_limits.py`, `test_device_tomls.py` (any `_sec` key/identifier);
  `buildgen_fixtures/multi_instance.toml`, `novel_combo.toml`.
- **Change**: every TOML key and expected constructor kwarg reads `trigger_s`; test names `*_trigger_sec_*` →
  `*_trigger_s_*`; a TOML still carrying `trigger_sec` is a rejected unknown key (A.U10.43's validation), pinned by one
  case in `test_buildgen_validate.py` (M.TSC.056).
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
- **Depends**: A.U8.01/A.U8.02 (grammar, register check M.TSC.147).
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
  tables/arrays (M.TSC.012). New `test_buildgen_error_contract.py` (M.TSC.182) pins the contract once.
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
- **Depends**: M.TSC.063 (check), A.U36.544 (DOC/SPEC rewrites).
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
- **Depends**: M.TSC.071 (check), A.U36.549 (DOC).
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
  `toolchain/` file by path; neither is a package") and `test_import_graph.py` (M.TSC.098) allows it by that name.
  Comment `:19-21` → "# Registered in sys.modules BEFORE exec_module(): a @dataclass resolves its string annotations
  through sys.modules[cls.__module__] while the class body still runs." (the `from __future__` clause goes once no host
  file carries the import).
- **Resolved**: —
- **Unit**: U10 (comment in U20 with A.U20.33).
- **Depends**: A.U10.30 (SPEC F.1 list), M.TSC.099 (`_PENDING`).
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
  M.TSC.182.
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
- **Depends**: `pyproject.toml` `pythonpath = ["."]` → A.U27.37 (M.TOOL.034).
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
- **Depends**: M.SCR.008 (`scripts/_unix_port.sh`).
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
  commit. Read by `test_buildgen_definitions.py` (M.TSC.039) and `tests_js/definitions-shape-corpus.test.js`
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
- **Depends**: A.U10.40 (harmonisation), M.TSC.129 (test).
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
- **Blast carried by**: the save-before-PUT order → M.TSC.194.
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
  (`test_device_script_rig_parking.py`, M.TSC.077) — the device-script guards each have one file.
- **Unit**: U26
- **Depends**: M.HW_BENCH.006, .011, .014, .020, .080; A.U28's retried sync (TOOL).
- **Blast carried by**: retry/no-retry cases → M.TSC.198; listing cases → M.TSC.178.
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
- **Blast carried by**: `pyproject.toml` FBT001 entry → A.U28.28 (M.TOOL.030); README scope `:838-845` → A.U26.62
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
- **Depends**: M.GEN.022, M.SCR.065.
- **Blast carried by**: —
- **Kind**: test

### M.TSC.030 The manifest freezes a sorted file list
- **From**: A.U27.34.
- **Site**: `tests_scripts/test_build_firmware.py:77-87`.
- **Change**: `:87`'s `freeze('<stage_dir>')` assertion → the sorted file-list form the manifest now carries (each
  staged module named once, in sorted order); the default board-manifest include assertion holds.
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.SCR.066.
- **Blast carried by**: reproducibility proof → M.TSC.094.
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
- **Depends**: M.GEN.019, M.GEN (frozen set, A.U20.13), M.SCR.066, M.SCR.067.
- **Blast carried by**: the stripped-image boot → M.TSC.131.
- **Kind**: test

### M.TSC.032 CLI cases: device TOML, no-autostart, toolchain lock, record, work dir
- **From**: A.S0930.06 (`--device-toml`), A.U27.36 (`--no-autostart`), A.U21.22 (dir without a record), A.U21.08
  (relative `--toolchain-dir` resolved), A.U27.29 (missing device through `main()`), A.U26.02 (record keys), A.U26.85
  (`overrides`), A.U27.35 (work dir), A.SDEP.03 (read: pytest deprecations; refresh in U0/U37); M.SCR.067's end state
  (`BuildDate`, `deviceToml`, `uartCrc`, `autostart`; `lwip`/`overrides` re-read from the build dir — GAPS_G4 hand-off
  3 (d), gap pass G3).
- **Site**: `tests_scripts/test_build_firmware.py:170-199`, new cases.
- **Change**: new cases — (a) `--device-toml <tmp>.toml` (a copy of a derived device's TOML with a different hostname)
  stages a generated module carrying that hostname; a missing `--device-toml` path fails before staging; (b)
  `--no-autostart`: the staged `main.py` equals `boot_entry_noautostart_source`, every other staged file is
  byte-identical to a default staging of the same device, the default output name ends `-noautostart.uf2`; (c) a
  toolchain dir with no setup record fails with A.U21.22's message (`:186-193`'s missing-dir message holds); (d) a
  relative `--toolchain-dir` reaches `st.build_firmware()` resolved (monkeypatched to record); (e) a missing device
  through `main()` prints one line, no `Traceback`, exit 1; (f) with `st.build_firmware` stubbed to return a fake uf2,
  `main()` writes the image record beside it with keys `BuildDate`, `commit`, `device`, `deviceToml`, `dirty`,
  `firmwareVersion`, `lwip`, `maxConnections`, `overrides`, `uartCrc`, `websiteVersion`, `autostart` (+ A.U27.31's three
  size keys) and `BuildDate` equals the date in the staged module; with the two `micropython_overrides` readers faked,
  `lwip` is the dict the fake `read_lwip_macros_from_build()` returns, `overrides` is `["modlwip_eagain"]` when the fake
  `verify_modlwip_eagain_in_build()` passes and `[]` when it raises `OverrideError`, and both readers receive the port
  build dir (the returned uf2's parent), never the copied output; the record's work dir is `tmp_path` (the test points
  `REPO_ROOT`-relative `build/` away by
  monkeypatching the module's work root), so no case writes into the live tree; the error-path cases assert no work
  dir was created; a `--no-autostart` build stages into its own `-noautostart` work dir (M.SCR.065).
- **Resolved**: —
- **Unit**: U27 (U26 record; S0930 rows land with their U26/U27 owners).
- **Depends**: M.SCR.065, M.SCR.066, M.SCR.067 (A.S0930.06, A.U27.36, A.U21.22, A.U21.08, A.U26.02, A.U27.35).
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
- **Depends**: M.SCR.067.
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
- **Depends**: M.SCR.072.
- **Blast carried by**: python-version stub case → M.TSC.209.
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
- **Depends**: M.SCR.071, M.SCR.020.
- **Blast carried by**: `test_test_sh.py:61-66` reads this file's `devices/` write text (unchanged).
- **Kind**: test

### M.TSC.036 The hand-kept staging cross-check yields to the drift rule
- **From**: A.U23.38 (`:113-127` passes on a comment mention, WEB.S14 → replaced by the drift rule's own tests).
- **Site**: `tests_scripts/test_build_website_sh.py:113-127`.
- **Change**: `test_every_real_js_and_html_file_is_accounted_for_by_the_staging_script` goes; its job is
  `scripts/_stage_website.py`'s import-closure and stray-file refusals, proven in `test_stage_website.py` (M.TSC.214).
- **Resolved**: —
- **Unit**: U23
- **Depends**: M.SCR.019 (`scripts/_stage_website.py`).
- **Blast carried by**: M.TSC.214.
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
- **Blast carried by**: validate's keyword-only `_Default*` case → `test_buildgen_validate.py` (M.TSC.056).
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
- **Blast carried by**: `test_js_coverage_excludes_json.py:13` → M.TSC.167; `test_buildgen_twin_wiring.py:31`
  comment → M.TSC.054; docs → A.U6.04 (SPEC/DOC).
- **Kind**: test

### M.TSC.039 `_shape_problems()` mirrors `validateDefinitions()` over one corpus
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
- **Blast carried by**: JS side → A.U6.16/A.U23.09 (WEB); the constant pin → M.TSC.072.
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
- **Blast carried by**: `hidden=` rows → M.TSC.159; schema-ast raise → M.TSC.163.
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
- **Site**: `tests_scripts/test_buildgen_generate.py:1-130`, `:221-223`, `:405-457`, `:487-489`.
- **Change**: docstring "End-to-end: buildgen.generate.generate_device() over every devices/*.toml plus the novel and
  multi-instance fixtures (SPECIFICATION.md Part L.1) - the validate -> sort -> generate pipeline from one TOML."; real-
  device tests parametrise over `DEVICE_NAMES` (ids = names); single-device text pins use the device a property selects
  (e.g. the one with `isl29125`, the bench device for `uart_link`); `:125` → the parsed build date is timezone-aware UTC
  and within one minute of the test's `datetime.now(UTC)`; `:221-223` → "# The implicit FRAM-wiring rule
  (SPECIFICATION.md A.7): every mandatory-infra module inherits the / # device's own FRAM chip, exactly like every
  FRAM-wirable [[instance]] - base_doc() already / # declares [device.wiring].fram_target = "fram", so this is the
  happy path." (≤ 3 lines); synthetic non-singleton instances carry `"name_ext": ""`; `trigger_s` everywhere; adherence fix (no history narrative, CLAUDE.md working agreement): `:416-418` → "# trigger_s is declared only on
  scd30 in every real device and fixture; this pins bmp3xx's own trigger_s rendering, which its @limits domain
  / # depends on." and `:489` ends "... long before codegen sees it." ("Found by …", "Phase 3", "Phase 4" go); `:5-7` →
  "# Correctness-proof scope: generated output is proven valid Python of the documented construction-order/wiring
  / # shape (ast.parse() + structural inspection); booting it is test_digital_twin_generated_boot.py's." ("Session 5's" goes).
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
- **Blast carried by**: twin boot of the entry → M.TSC.085; hardware reflash checks → M.HW_BENCH.014.
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
  contiguity test → M.TSC.081.
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
  (M.TSC.059); `_system_cmd_callback`'s compared string constants (AST) equal `_SYSTEM_CMDS` (read from
  `src/asy_webserver_service.py`), every branch `return`s its call, the two new branches call
  `sysfunct.reset_to_defaults()`/`sysfunct.erase_fram()`; CLI error cases assert one stderr line with `- fix: `, no
  `Traceback`, exit 1.
- **Resolved**: —
- **Unit**: U20 (S0930 row with U10's command words).
- **Depends**: M.GEN.003, M.GEN.008, M.GEN.019, M.GEN.022.
- **Blast carried by**: ruff on the generated tree → A.U28.41/A.U27.09 (TOOL/SCR); liveness of the generated-scope
  exemption → M.TSC.123.
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
- **Blast carried by**: the build-time rejections → `test_buildgen_validate.py` (M.TSC.056).
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
- **Blast carried by**: manifest/image reproducibility → M.TSC.094.
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
### M.TSC.054 The twin plan: one producer, addresses from drivers, explicit loading
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
- **Blast carried by**: contract test → M.TSC.151; `pyproject.toml:295` ANN401 entry removal → M.TOOL.030.
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

### M.TSC.056 Device-table, field and range rejections
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
- **Blast carried by**: the contract table rows → M.TSC.182.
- **Kind**: test

### M.TSC.057 UART-link rules: CRC mode, single owner, baud pair, poll and timeout ceilings
- **From**: A.S0930.01 (crc cases), A.U20.01 (single owner; responder without initiator), A.U17.32 (baud mismatch),
  A.U17.21 (poll ceiling, timeout ceiling, source-read variant), A.U13.17 (`:1290-1299` defaults comment, `rxbuf = 52`
  refusal; `:1301-1310` replacement), A.U2.23 (`:1257`, `:1268`, in M.TSC.055); read: A.S0930.01 (`:1240-1384` hold —
  absent `crc` is `"none"`), A.U17.21 (`:1255-1287` hold); A.S0930.01's `test_uart_crc_modes_match_crc_checks` with
  SRC_CORE GAP-G10's names (`asy_crc_checks`, `CRCPass`; gap pass G3 — the test had no carrier).
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
  refused matching `poll_idle_ms 976`, `poll_idle_ms` unstated in the TOML. New
  `test_uart_crc_modes_match_crc_checks`: reads `src/asy_crc_checks.py` by `ast`; every class named in
  `buildspec.UART_CRC_MODES` exists there and its `__init__`'s `super().__init__(<int>, …)` first argument equals the
  table's width (`CRCPass` 0, `CRC16` 2); a table naming a class the module lacks fails naming it (bite on a `tmp_path`
  copy).
- **Resolved**: A.S0930.01 writes the agreement test against HEAD's `src/crc_checks.py` and `CRC_Pass`; it lands after
  U10's rename (A.U10.37/A.U10.38, M.SRC_CORE.115), so it reads the end-state module and class (SRC_CORE GAP-G10; the
  table itself says `CRCPass`, M.GEN.024 as amended in gap pass G1). A.U13.17's replacement (poll 464/465) fails
  A.U17.21's single-digit poll check before its floor; the
  source-copy form A.U17.21 writes is taken (its own AC note amends A.U13.17's test).
- **Unit**: U17 (stages U13 comment/defaults; S0930 CRC rows with A.S0930.01's unit).
- **Depends**: M.GEN.024, M.GEN.027, M.GEN.029; M.SRC_CORE.115 (module and class names); A.U13.17/A.U17.20 driver
  constants (SRC_UART).
- **Blast carried by**: twin CRC boot → M.TSC.085; UART changelog entries → A.U13.17/A.S0930.01 (SRC_UART).
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

### M.TSC.059 Wiring rows follow the construction-time APIs
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
- **Blast carried by**: `test_device_tomls.py:271-282` removal → M.TSC.079.
- **Kind**: test

## tests_scripts/test_citations.py
### M.TSC.063 Every citation resolves; old legacy paths excluded by one prefix
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
- **Resolved**: header presence is settled by G9/R16 (AC_NOTES 42 (1)): the 23 L1 files and `tests/microtest.py`
  without one each gain a ≤ 3-line docstring in U27, in the same change as this check.
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
- **Change**: fails naming file, key and path when a `pyproject.toml` per-file-ignores glob matches no tracked file
  (except `build/generated_src/**`, which matches only git-ignored generated files — its liveness is
  M.TSC.123's, M.TOOL.030, TOOL gap 1); a
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
- **Blast carried by**: concatenation row → M.TSC.163; SPEC C.5 → A.U11.18 (SPEC).
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
- **Depends**: M.SCR.008, M.SCR.009, A.U24.05/A.U24.72 (`tests/_coverage_runner.py`, TEST_HELP).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_decision_vocabulary.py
### M.TSC.071 Decision vocabulary carries its actor
- **From**: A.U0.09 (check), A.U36.549 (named narrowing regexes per recurring descriptive shape; empty list), A.U37.02
  (allow-list reading goes), A.U0.10 (read: CLAUDE.md names it); A.U37.15 (phase D: the `audit/`/`PROJECT_AUDIT_PLAN.md` exclusion goes; M.DOCS.043's blast, gap pass G3).
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
- **Unit**: U37 (stages U0, U36); phase D drops the `audit/` and `PROJECT_AUDIT_PLAN.md` scope exclusions in its close
  commit (A.U37.15), the paths being deleted there.
- **Depends**: M.TSC.010.
- **Blast carried by**: the tagged sentences → A.U36.549 (every owning cluster).
- **Kind**: test

## tests_scripts/test_definitions_js_mirrors.py
### M.TSC.072 The website's copies of generator bounds are pinned
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
- **From**: A.U26.24; HW_DEV GAP-D7 (M.HW_DEV.066), AD-8 (disjoint regions, M.HW_DEV.124/.132); GAPS_G2 H-4 (b) (the
  chunk's address is `_block_addr` after M.SRC_CORE.081; gap pass G3).
- **Site**: new `tests_scripts/test_device_script_fram_regions.py`.
- **Change**: every device script issuing a raw `set_values`/`get_values` declares `_SCRATCH_REGIONS`
  (and `_EVIDENCE_REGIONS` for a production read) covering every raw call, its addresses expressed from those tuples;
  regions of different scripts are disjoint; every scratch region lies in `[allocated_size, part_size)`, with
  `allocated_size` read by booting the bench device's generated module under the Unix-port twin (the
  `test_digital_twin_boot_contiguity.py` harness) and `part_size` the bench TOML's FRAM `max_size`; every
  `_EVIDENCE_REGIONS` script runs under the session evidence save; a raw call addressed through a `get_chunk()`
  result (`chunk._block_addr …`, the private name M.SRC_CORE.081 gives it) is chunk-scoped (covered by the clear-in-`finally` check), not undeclared scratch. A
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
### M.TSC.077 NeoPixel construction sits inside a parking `try`
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
### M.TSC.079 Device-TOML checks validate.py does not make
- **From**: A.U20.19 (1) (rewrite), A.U20.10 (FRAM part comment check), A.U20.29 (banner layout check), A.U20.28
  (`:841-848` → `fixed_address()`), A.U26.01 (`bench` key accepted), A.U28.06/A.U28.08 (`:271-282` moves to
  `test_ci_workflow.py`), A.U24.66, A.U24.73, A.U10.43; dropped: A.U0.29's `:761` sentence (lands U0, its test goes with
  A.U20.19 in U20), A.U20.37's `:285` accept assertion (its test is deleted by A.U20.19); read: A.U1.24, A.U36.520
  (TOML comments, not parsed), A.U28.01/A.U6.12 (`:275` regex cited as precedent), A.U32.01 (cites `:294`), A.S0930.01
  (no `uart_link` field set pinned).
- **Site**: `tests_scripts/test_device_tomls.py:1-849`.
- **Change**: header "Device-TOML checks `validate.py` does not make: reserved I2C addresses, the hostname convention,
  the FRAM part comment, section layout and banners, and per-device test coverage."; one parametrised test over `DEVICE_NAMES`:
  `build_model(devices/<d>.toml, src)` returns and `build_construction_order()` succeeds; deleted: the `check_*`
  functions `:70-245` and their tests `:284-411`, `:484-801`, `test_parses_as_valid_toml`, `_ALWAYS_PRESENT_DRIVERS`,
  `_DEVICES_WITH_BMP3XX`, `_DEVICES_WITH_UART_LINK`, `_DEVICES_WITH_ISL29125`, `test_instance_list_has_the_expected_driver_kinds`,
  `test_bmp3xx_only_present_on_wozi_and_dev`, `test_isl29125_only_present_on_dev`, the two "every wirable instance"
  tests, the multi-instance `name_ext` hand test, `:271-282`; kept: reserved-I2C-address tests (`:817-848`, looping
  `fixed_address()` over the fixed-address drivers), `:294`'s hostname convention as
  `test_hostname_is_sensorstation_plus_name` (`hostname == "SensorStation" + name`, per device) and the device-coverage
  derivations `:247-282` minus the CI matrix;
  `test_klkizi_grkizi_schlafzi_share_identical_wiring` → `test_devices_of_one_hardware_family_differ_only_in_identity`
  (grouping by `[device] hardware_family`, only `name`/`hostname` differ); new: the comment line directly above every
  FRAM `max_size` names the part `_KNOWN_PRODUCT_IDS` (read by `ast`/`tokenize`) maps the size to; banners match `^#
  --- [a-z -]+ -+$` at 100 characters, sections in the fixed order (`sensor drivers`, `singleton services`,
  `multi-instance services`), each `[[instance]]` under the banner its driver's kind selects, every non-singleton
  instance states `name_ext`; the `bench` key is accepted in the `[device]` layout. No `Any`.
- **Resolved**: A.U20.19 deletes `:284-411` as validate checks restated by hand, but `:294`'s `SensorStation<Name>`
  assertion has no `validate.py` twin (it checks a host label only, M.GEN.026) — kept by A.U20.19's own rule "a hand
  check stays only where it tests something `validate.py` does not" (agent decision D-TSC7). A.U28.06 says `:271-282` is rewritten here; A.U28.08 (7) moves it to `test_ci_workflow.py` — moved
  (A.U28.08 names the move; one home for workflow rules).
- **Unit**: U20 (stage U28 removes `:271-282`; U26 `bench`).
- **Depends**: M.GEN.028 (`name_ext` rule), M.GEN.052-.059 (TOML edits), M.GEN.043.
- **Blast carried by**: SPEC L.3 sentence about this file → A.U20.19 (SPEC); README runbook's `:294` citation → the kept test's
  name (Gaps, DOCS).
- **Kind**: test

## tests_scripts/test_digital_twin_boot_contiguity.py
### M.TSC.081 The contiguity probe follows the setup list now inside `SystemService`
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
- **Depends**: M.SCR.009, M.HW_BENCH.016 (marker set).
- **Blast carried by**: gate agreement → M.TSC.108.
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
- **Depends**: M.SCR.058 (Run 11b), M.GEN.033.
- **Blast carried by**: `pyproject.toml` entries → A.U28.27/A.U28.28 (M.TOOL.030).
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
- **Depends**: M.SCR.057 (Run 11), M.SCR.002 (summary block).
- **Blast carried by**: SPEC E.9 → A.U27.17 (SPEC).
- **Kind**: test

## tests_scripts/test_digital_twin_generated_boot.py
### M.TSC.085 Header, launch and state paths of the generated boot
- **From**: A.U36.513 (5) (`:1-2`, `:150-152`), A.U36.548 (7) (carried by A.U36.513), A.U36.004 (`:35` history comment →
  current fact), A.U27.05 (`_boot_generated_device()` takes a path root), A.U27.15 (`:153` → `twin` with the tmp tree,
  reason line), A.U25.44 (the launch guard reads this site), A.U25.32 (`:155-164` state paths and `--config-dir`),
  A.SDEP.16 (`:154` `TZ`), A.U20.02 (the runner passes a `WDT`), A.U20.33, A.U24.73, A.U24.66, A.U24.67 (`:201-202`
  set-claim comment), A.U8.22 (`:29-30`, `:42`, `:100`, `:105`, `:185`, `:188`); TWIN: `twin` MICROPYPATH gains
  `digital_twin/unixport` (M.TWIN.017, via the file); read: A.U1.23, A.U6.01 (`:111` model already ordered), A.U16.20,
  A.U16.17 (fixtures move to 0x40000 in their own files, M.TSC.176), A.U19.20, A.U11.05 (twin fakes land in
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
- **Depends**: M.SCR.009, M.TWIN.017, A.U25.32 (TWIN runner flags).
- **Blast carried by**: stripped-image reuse → M.TSC.131.
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
  `harness.MEMORY_ERROR_MARKERS` marker fails; the multi-instance fixture's `/status` carries `SGP40` and `SGP40_<ext>`;
  adherence fix (no history narrative): `:213-215` → "# Every real device's own TOML, generated fresh here: proof the
  generator's module runs for every device, not just ast.parse()s (SPECIFICATION.md Part L.4)." ("Session 3's" goes).
- **Resolved**: —
- **Unit**: U35 (stages U6, U7, U20, U24).
- **Depends**: M.GEN.014/.033, M.SCR.016 (`scripts/_twin_process.py`), M.HW_BENCH.016.
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
- **Blast carried by**: Run 3's CRC cell → M.SCR.051/M.SCR.061.
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
- **Blast carried by**: twin `TEST_API` tuples → M.TWIN.020-.036 ("every class gains a `TEST_API` tuple").
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
### M.TSC.094 Staged firmware inputs are reproducible
- **From**: A.U27.34 (2).
- **Site**: new `tests_scripts/test_frozen_inputs_reproducible.py`.
- **Change**: for every `DEVICE_NAMES` device, a CPython subprocess run twice (`PYTHONHASHSEED=0`, `=4242`) stages the
  Python modules with `stage_python_modules()` into its own `tmp_path` under a fixed build date and prints `name  sha256`
  for every staged file plus the rendered manifest text; the outputs are byte-identical.
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.SCR.066, M.SCR.070.
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
- **Depends**: M.SCR.015 (`scripts/_check_gc_collect_sites.py`), M.SRC_CORE.015/.016, M.HW_DEV.116/.117/.120.
- **Blast carried by**: the moved `test_lint_sh.py` grep cases → M.TSC.157; SPEC I.4(f.1) → A.U27.21/A.U30.14 (SPEC).
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
### M.TSC.098 The import graph: no cycles, no driver-to-driver edge, named dynamic loads
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
### M.TSC.099 No function-level or dynamic import outside the named list
- **From**: A.U0.07, A.U37.02 (`_PENDING` removed once empty), TEST_HELP GAP-H6 (this cluster's `_PENDING` entries leave
  in U24; `_NAMED_EXCEPTIONS` holds `load_generated` and the two runners' `exec`), HW_BENCH GAP-B4, HW_BENCH M.HW_BENCH
  (its `_PENDING` entries leave in U26), TEST_UNIT (`tests/test_asy_isl29125_driver.py:1301, 1306` entries leave with
  the module-level `import time`).
- **Site**: new `tests_scripts/test_import_placement.py`.
- **Change**: AST walk over every `.py` in `src/`, `buildgen/`, `digital_twin/`, `tests/`, `tests_scripts/`,
  `tests_hardware/`, `scripts/`, `toolchain/` (skipping `tests/_tmp/`): fails on an `Import`/`ImportFrom` inside a
  function body, and on `__import__`, `importlib.import_module`, `importlib.util.spec_from_file_location`/
  `module_from_spec`/`exec_module`, or `exec()`/`compile(…, "exec")` of a file's source, unless in `_NAMED_EXCEPTIONS`
  (SPEC F.1's list — the same seven entries as M.TSC.098) or `_PENDING` (keyed `(path, qualname, module or call)`,
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
- **From**: A.U1.09; A.U1.10 (read: CLAUDE.md names this file); M_PROC gap 4 (the legacy check also asserts
  `legacy/README.md` tracked and `dev_legacy/` absent, M.PROC.014/.015; gap pass G3).
- **Site**: new `tests_scripts/test_legacy_paths.py`.
- **Change**: three tests, docstring ≤ 3 lines: (1) `test_no_current_file_names_a_pre_move_legacy_path` over `git
  ls-files` (git from `shutil.which`), skipping `legacy/`, `arduino/`, `datasheets/`, `audit/`, `PROJECT_AUDIT_PLAN.md`,
  this file and non-UTF-8 files, with A.U1.09's validated pattern; (2) the pattern's property test (each pre-move form
  hits, each new path and each real look-alike does not); (3) `test_the_legacy_tree_is_where_the_rules_say` (no tracked
  path under the old roots `python/`, `modules/`, `html_raw/` and `dev_legacy/` (dissolved, M.PROC.014), nor a root
  `build-*.sh` or `update_and_install.txt`; the `legacy/firmware/…` set, its four `build-*.sh`, `legacy/dev_drivers/`
  and `legacy/README.md` tracked). The `audit/`/`PROJECT_AUDIT_PLAN.md` exclusions go in phase D's close commit.
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
### M.TSC.108 Every allocation gate agrees, the JS and heap-map gates included
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
### M.TSC.110 No variant literal outside the device TOMLs
- **From**: A.U6.15, A.U37.02 (`_NOT_YET_CLEANED` removed once empty), A.U37.10 (committed fixtures excluded); A.U37.15 (phase D: the `audit/`/`PROJECT_AUDIT_PLAN.md` exclusion goes; M.DOCS.043's blast, gap pass G3).
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
- **Unit**: U37 (stage U6); phase D drops the `audit/` exclusion in its close commit (A.U37.15).
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
  `setup()` override, `SensorReaderConfig`, `UARTLinkDriver` gains the flag, M.SRC_NET.213/.215); GAPS_G2 H-4 (a) (an
  override that awaits `super().setup()` inherits the flag; `SystemService`, `SensorReader` and `FRAMManager` now carry
  it, M.SRC_CORE.008/.036/.039/.092; gap pass G3).
- **Site**: new `tests_scripts/test_readiness_gates.py`.
- **Change**: AST over `src/`: every class defining `async def setup` assigns `self.initialized = False` in `__init__`
  and `True` inside `setup()` (or inherits both from a base that does, resolved within `src/`: a class whose `setup()`
  awaits `super().setup()` of such a base counts as setting it — `SensorReaderConfig` over `SensorReader`, `WifiService`
  and `NotificationService` over theirs; `SystemService`, `SensorReader` and `FRAMManager`, whose `initialized` replaces
  `_was_up`, set it themselves), except a named list
  with reasons: `ConfigManager` (`valid`) and the protocol classes
  `BMP3XX_I2C`, `SCD30_I2C`, `SGP40_I2C`, `ISL29125_I2C` plus `I2CDevice` ("build everything in `__init__`; `setup()`
  only probes and configures the chip"); `NeopixelDriver` and `NotificationService` are checked (each carries
  `self.initialized`, AC_NOTES 42 (2): `_finalized` is gone with M.SRC_SENS.033); every `deinit`/`close`/
  `disconnect`/`stop_*`/`cleanup` method on a class with no `self.pr` returns `-> bool`, except chip commands
  (`stop_*` on a `*_I2C` protocol class) and `_TimeoutStreamProxy.close` (a mirror, by name).
- **Resolved**: GAP-17 — the lead's ruling (AC_NOTES 38): protocol classes and `I2CDevice` named exempt,
  `NeopixelDriver` gets `initialized`; AC_NOTES 42 (2) voids "`_finalized` counts as its gate" (M.SRC_SENS.033 removes
  `_finalized`): `NotificationService` carries `initialized` and stays in the check.
- **Unit**: U10 (after A.U13's `deinit()` changes; until then they are listed pending).
- **Depends**: M.SRC_SENS.023/.024 (NeopixelDriver gate, AC_NOTES 44), M.SRC_SENS.033 (NotificationService
  gate), M.SRC_NET.213/.215, A.U10.21.
- **Blast carried by**: the L1 half → M.TEST_UNIT (A.U10.22 L1); SPEC C.13 → A.U10.22 (SPEC).
- **Kind**: test

## tests_scripts/test_readme_reference.py
### M.TSC.113 README's command reference equals every tool's `--help`
- **From**: A.U36.547 (7); A.U37.15 (phase D: the `audit/`/`PROJECT_AUDIT_PLAN.md` exclusion goes; M.DOCS.043's blast, gap pass G3).
- **Site**: new `tests_scripts/test_readme_reference.py`.
- **Change**: imports the tool set from `test_tool_help.py` (the shared list, a module-level constant there); per tool runs
  `--help` and compares its option names (`--x`/`-x`) and environment-variable names with the README block's options and
  variables (equal sets, every Meaning non-empty); every README block names a tool in the set and every tool has a
  block; `package.json` scripts equal the README's npm table; every tracked `*.md` other than README.md and licence files
  outside `legacy/`, `audit/`, `arduino/`, `node_modules/` is named in "Further reading"; mutation fixtures (a README row
  removed, an extra option in a stub tool's help, an unmapped `.md`) fail.
- **Resolved**: —
- **Unit**: U36; phase D drops the `audit/` exclusion in its close commit (A.U37.15), when README's "Further reading"
  loses the plan and `audit/` entries (M.DOCS.043).
- **Depends**: M.TSC.217, A.U36.547 (DOC).
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
- **Blast carried by**: host lwIP hammer → A.U21.13 (TOOLCHAIN/TEST_UNIT); `test_test_sh.py` second loop → M.TSC.135.
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

## tests_scripts/test_persistence_write_marker_completeness.py
### M.TSC.119 The wear guard derives its classes and sees every way a test writes
- **From**: A.U26.06 (class/module marks; device scripts; raw sockets; docstring blind-spot lines; bites), A.U26.71 (2)
  (dispatch-only derivation from the `@web`-derived classes; the always-executed class persists; `_JUSTIFIED_UNMARKED`
  proofs `Invalid`/`Unchanged`/ignored, checked in their own file), A.U6.17 (7) (`_ROUTE_DISPATCH_FIELDS` and the regex
  replaced by the union over `DEVICE_NAMES` of `dispatch: true` fields in `definitions_for_toml()`; sibling
  `_always_executed_fields()`; the subset guard), A.S0930.19 (`"resetconfig"` counts as persisting), A.S0930.34 (3)
  (`'{"SystemCmd": "bootloader"}'` not flagged), HW_DEV GAP-D8 (a write-mode `open(` and a raw SCD30 configuration
  `writeto` count as persisting device calls, M.HW_DEV.101/.123/.155/.156), A.U26.15 (`_repair_leftover` joins
  `_KNOWN_PERSISTING_HELPERS`), A.U26.79 (the standard-state repair script joins `_PREREQUISITE_DEVICE_SCRIPTS`,
  "restores the standard board state"; M.HW_DEV's script), A.U26.10 (the two `main()`-based serving scripts join
  `_PREREQUISITE_DEVICE_SCRIPTS`; M.HW_DEV.009/.120's blast, gap pass G3), A.C.17 (the manual branch: a persisting script
  run from a `tests_hardware/manual/` step needs the operator's confirmation; M.HW_BENCH.102's blast, gap pass G3),
  A.U26.20 and A.C.13 and A.U26.71 (1) (`_JUSTIFIED_UNMARKED` reasons), A.U10.41 (`:29`
  reason names the new largest string field), A.U36.544 (`:230`, `:243` "F14"/"F15" → the reason in place), M.TSC.001
  (`config_manager.py` → `asy_config_manager.py` in the `:22-23` comment); read: A.U26.39 (`:38-44` fixture stays),
  A.U26.07/.08/.12/.14, A.U31.05, A.U16.07, A.S0930.06, A.S0930.28, A.U36.504, A.U35.51 (its conformance list reads this
  file), A.U8C2.16 (`:206` forwarding wrapper shape unchanged).
- **Site**: `tests_scripts/test_persistence_write_marker_completeness.py:1-350`, new tests.
- **Change**: docstring (≤ 3 lines) plus one line per remaining blind spot naming its closing check; `_marked_tests(path)`
  reads function, enclosing-class and module `pytestmark` marks; the dispatch-only class = union over `DEVICE_NAMES` of
  `dispatch: true` fields from `definitions_for_toml()`, the always-executed class = `alwaysExecuted: true` fields, guard:
  `{"SGPResetVOC", "ISLCalibrate", "SystemCmd", "PauseTime", "lightCmdLED", "ResetErrors"} <= dispatch_only` and
  `{"AmbPres", "ForceCalRef", "ContMeas"} <= always_executed` (names after A.U10.40's harmonisation); always-executed
  fields persist even when repeated; `_PERSISTING_COMMAND_WORDS` = the one `_SYSTEM_CMDS` word whose purpose deletes every
  config file (`"resetconfig"`, read by `ast` from `src/asy_webserver_service.py`), so a PUT body carrying it is
  persisting while `"erasefram"`, `"reboot"`, `"bootloader"` stay unflagged (`:340-344` parametrisation gains those three
  rows, plus a flagged `resetconfig` row and its synthetic bite); `_JUSTIFIED_UNMARKED` proofs accepted: `== "Invalid"`,
  `== "Unchanged"` (stored fields only), the ignored-key form, each entry found in its own tier file; entries: the
  all-invalid PUT, the largest-body test ("its <field> is one over its own max, so it is rejected Invalid and nothing is
  staged"), the hotspot role-reversal and bus-concurrency re-trigger PUTs ("Unchanged: nothing is written"), the
  Hostname/SSID edge values ("exceed their byte bounds and are rejected"), the oversized-body test ("refused unread:
  nothing persists"); `_KNOWN_PERSISTING_HELPERS` gains `_repair_leftover` ("repairs an aborted run's leftover; runs only
  when one exists"); new `test_every_device_script_that_persists_is_run_only_by_a_gated_test` (`_PERSISTING_DEVICE_CALLS`
  = the two config writers and the SCD30 NVM setters, each asserted still an `async def` in `src/`, plus a write-mode
  `open(` and an SCD30 `writeto` of a configuration command 0x4600/0x0010/0x5403…, plus `build_system(`/`main(` without a
  scratch `cfg_path`; runners found by the `"<script>.py"` string; each runner marked, a named persisting helper, or the
  script in `_PREREQUISITE_DEVICE_SCRIPTS` with its reason — the SCD30 start script, the standard-state repair
  script, and the two `main()`-based serving scripts `serving_at_default_gc.py` and `heap_under_connection_ceiling.py`
  ("boots `main()` over the production config, which carries the WiFi credentials; its only possible write is the repair
  a production boot of a malformed file makes", A.U26.10); a persisting script with no runner fails); runners are also
  searched in `tests_hardware/manual/*.py`: a manual step that runs a persisting script must hold a `confirm(` call
  before the run call in the same step function (`ast`) and the script be listed in `_MANUAL_PERSISTING_STEPS =
  {<script>: <reason>}` (`config_write_loop_scratch.py`: "up to 20 scratch flash writes and one removal, stated and
  confirmed by the operator before the run", A.C.17; `config_files_restore.py`: "rewrites the config files saved before
  the `resetconfig` power cut, once", M.HW_BENCH.102 (4) — its step takes the same `confirm()`, hand-off HW_BENCH in
  GAPS_G3), with a bite (a tmp manual step without the `confirm(` fails);
  new `test_no_raw_socket_request_persists` (`_JUSTIFIED_RAW_REQUESTS`,
  today the malformed raw-request test); every new check has a synthetic bite; `:230`, `:243` comments state the reason
  without the F-labels.
- **Resolved**: A.U6.17 (7) (U6) and A.U26.71 (2) (U26) both replace `_ROUTE_DISPATCH_FIELDS` — U26's derivation reads
  A.U6.17's classes, one end state; A.S0930.19's word list is expressed as a value-level exception inside that
  derivation (its own Depends).
- **Unit**: U26 (stages U6 derivation, U10 names/reason).
- **Depends**: M.GEN.017 (`alwaysExecuted`), M.HW_DEV.040/.101/.123/.155/.156, M.HW_BENCH.080/.088.
- **Blast carried by**: README dispatch-only sentence → A.S0930.19 (HW_BENCH, M.HW_BENCH.130).
- **Kind**: test

### M.TSC.120 Marker registry: strict, every gate flag names its marker
- **From**: A.U26.74 (4) (built-in set drops `timeout`; every `--allow-*` maps to a registered marker of the same kebab
  name, `--soak-duration` named), M.HW_BENCH.002 (marker set), A.U26.14 (read: `toolchain_reverify` registered).
- **Site**: `tests_scripts/test_persistence_write_marker_completeness.py:366-384`.
- **Change**: `test_no_test_carries_an_unregistered_marker`: comment → "--strict-markers is on (pyproject addopts), so an
  unregistered marker fails collection; this names it before a hardware run would."; built-in set `{"parametrize",
  "skipif", "skip", "xfail", "usefixtures", "filterwarnings"}`; new: every `--allow-<x>` option in
  `tests_hardware/conftest.py` maps to registered marker `<x>` with dashes as underscores (`--soak-duration` ↔
  `soak_duration` named as the one valued gate); `test_the_extra_write_marker_is_never_carried_alone` holds.
- **Resolved**: A.U26.74's blast says the test "allows an inert `timeout`"; its Change (4) drops it — the Change governs
  (M.HW_BENCH.002 Blast agrees).
- **Unit**: U26
- **Depends**: M.HW_BENCH.001, M.HW_BENCH.002, `pyproject.toml` `addopts` → A.U26.74 (1) (M.TOOL.034).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_request_timeout_ceiling.py
### M.TSC.121 Ceiling and timeout mirrors read their sources through config objects
- **From**: A.U23.37 (`:67` regex `export const DEFAULT_TIMEOUT_MS` → `const DEFAULT_TIMEOUT_MS`), A.U5.05 (`:48-59`,
  `:105-107` a `const()`-aware reader of the `_DEFAULT_*` constants that now default `ServingLimits`/`StaticSite`),
  A.U5.04 (`:106-114` webserver construction through the three config objects), A.U24.51 (`:110-113` per-device loop →
  `DEVICE_NAMES`), A.U8C.50 (`:295-313` resolve a `Name` argument of `extra.settimeout` and the retry sleep through
  `_module_constant()`), A.U2.19 (`:296` comment names catalog codes 49/50 by name), A.U8.22 (`:237`, `:290` join bounds
  tagged; `:211, :232, :288` test inputs untagged); read: A.U8.02/A.U8.04 (overlap settled below), A.U8.05, A.U8C.112,
  A.U8C.121, A.U8C2.18, A.U8C2.21, A.U8C2.47, A.U8.20 (constants read by name/AST, unaffected), A.U23.02
  (15 s mirrors kept), A.U31.18 (parameter defaults unchanged), A.U36.503, A.U36.532 (`:101` "H.7.1" still lands), A.U6.16
  (pattern cited); A.U19.14 (BACKLOG item 24 leaves at U19: its citer `:88` repoints in the same unit — M_DOCS gap 2,
  gap pass G3).
- **Site**: `tests_scripts/test_request_timeout_ceiling.py:40-313`.
- **Change**: `_module_constant()` reads `NAME = const(<int|float literal>)` and plain literals; the webserver defaults are
  read from `ServingLimits`/`StaticSite` field defaults (`_DEFAULT_OUTER_CAP_S`, `_DEFAULT_MAX_CONTENT_LENGTH`, …) as
  A.U5.05 names them; the JS regex matches `(?:export )?const DEFAULT_TIMEOUT_MS = (\d+);`; the per-device loop is
  parametrised over `DEVICE_NAMES` with `device_max_connections()`; `:295-313` resolves `extra.settimeout(<Name>)` and the
  retry sleep via `_module_constant(…)`; `:296`'s comment names `HTTP_WRITE_TIMEOUT`/`HTTP_OUTER_CAP` (catalog names) for
  49/50; join bounds `_JOIN_TIMEOUT_S = 5.0  # @tunable l0.request_timeout_ceiling_join_timeout_s = 5.0` and the 2.0 one
  likewise. `:86-88` keeps its two sentences and ends "… is misdiagnosed as a network fault (SPECIFICATION.md C.7)." in
  place of "(BACKLOG item 24 has the measurements)" — the item leaves BACKLOG at U19 (A.U19.14) and SPEC C.7 holds the
  ceiling rule.
- **Resolved**: A.U8.02 keeps the `:62-70` JS-literal check "until A-C" beside A.U8.04's tag on `js/poll-manager.js:8`
  (`web.outer_cap_s = 15000`): both stay — the register pins each literal to its row, this test pins the cross-unit
  relation `DEFAULT_TIMEOUT_MS == outer_cap_s × 1000`, which no register row expresses (agent decision D-TSC4).
- **Unit**: U24 (stages U2 comment, U5 readers, U8 tags, U19 the `:88` pointer with A.U19.14, U23 regex).
- **Depends**: M.SRC_NET (webserver config objects, A.U5.04/.05), A.U23.37 (WEB); A.U19.14's SPEC C.7 text (SPEC).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_require_clean_hardware_run_sh.py
### M.TSC.122 The hardware wrapper: pytest's exit kept, the verdict delegated, `-m` narrowed
- **From**: A.U7.14 (whole file rewritten against canned run records; the whitelist tests become marker-map tests),
  A.U27.19 (`--marker-floor`), A.U26.74 (`:18-19` flag strings), A.U26.35 (`long_soak` → `soak_duration`), A.U26.08 and
  A.U26.36 (names in canned text, read), A.U26.56 (the permanent-skip nodeid follows its outcome); M.SCR.074 (the
  rollover runner's floor; GAPS_G4 hand-off 3 (b), gap pass G3).
- **Site**: `tests_scripts/test_require_clean_hardware_run_sh.py:1-190`.
- **Change**: with a stub `uv`/pytest writing a canned run record: the wrapper runs pytest once, keeps its exit code, calls
  `scripts/_hardware_verdict.py --run-record … --pytest-exit … --runner … --levels …` and exits with its code; a nonzero
  pytest exit propagates unchanged (`:183`'s pin); `--marker-floor EXPR` is consumed: no caller `-m` → pytest gets `-m
  "<floor>"`; one or more caller `-m`/`-mEXPR` → exactly one `-m "(<floor>) and (<last caller expr>)"`, printed and in
  the record; flash and bench runners pass `not soak_duration and not multi_day_rollover`, the soak runner
  `soak_duration` with `--soak-duration`, the rollover runner `multi_day_rollover` (no caller `-m` → `-m
  "multi_day_rollover"`; `-m foo` → `-m "(multi_day_rollover) and (foo)"`) with `--allow-multi-day-rollover` reaching
  pytest; the wrapper exports `EVIDENCE_DIR` pointing at the run's archive directory
  (M.SCR.034, HW_BENCH GAP-B6); the verdict cases themselves live in `test_hardware_verdict.py` (M.TSC.197).
- **Resolved**: A.U26.35/A.U26.74's edits of `:18-19` fall inside A.U7.14's rewrite — one rewrite with the new names.
- **Unit**: U27 (stage U7 rewrite; names U26).
- **Depends**: M.SCR.034, M.SCR.005, M.SCR.074, M.HW_BENCH.001/.002.
- **Blast carried by**: verdict rules → M.TSC.197.
- **Kind**: test

## tests_scripts/test_ruff_exemptions_live.py
### M.TSC.123 Every ruff exemption still fires
- **From**: A.U28.31 (check), A.U28.34 (read: CLAUDE.md names it), A.U34.11 (read: confirms no ANN401 entry is left).
- **Site**: new `tests_scripts/test_ruff_exemptions_live.py`.
- **Change**: one ruff run over the eight scopes with every exemption lifted (`--output-format json --config 'lint.ignore
  = []' --config 'lint.per-file-ignores = {}' --config 'lint.allowed-confusables = []'`): fails for each global code
  with no finding, each per-file code with no finding in a file its glob matches, and `allowed-confusables` with no
  RUF001-RUF003 finding naming `×` — the message names the entry and "remove it"; policy-only rules are listed with their
  reason; the `build/generated_src/**` entry is tested on a tree generated into `tmp_path` for every `DEVICE_NAMES`
  device with `--select <codes>` and lifted exemptions.
- **Resolved**: —
- **Unit**: U28
- **Depends**: A.U28.27-.29, A.U28.41 (TOOL).
- **Blast carried by**: first-run removals in `pyproject.toml` → A.U28.31 (2) (M.TOOL.030).
- **Kind**: test

## tests_scripts/test_setter_contract.py
### M.TSC.124 Setters answer `bool`; push callbacks registered once
- **From**: A.U10.25 (L0 half).
- **Site**: new `tests_scripts/test_setter_contract.py`.
- **Change**: AST over `src/`: every `self._push_callbacks[<key>] = <method>` sits in `__init__`; every method registered
  in `_push_callbacks` and every `set_*` reached by a `SettingsGroup`, a push callback or a REST dispatcher is annotated
  `-> bool` (or `WriteValidity` where C.5.2 documents it); chip-protocol classes (`*_I2C`, `FRAM_SPI`), `Locked*`,
  logging and wiring setters are named out of the rule; `_push_callbacks` is never assigned outside `__init__`.
- **Resolved**: —
- **Unit**: U10
- **Depends**: A.U10.25 (SRC).
- **Blast carried by**: L1 half → M.TEST_UNIT (A.U10.25); SPEC C.5.2 → A.U10.25 (SPEC).
- **Kind**: test

## tests_scripts/test_setup_toolchain_env.py
### M.TSC.125 Toolchain record, ref writer, pin notice, build diagnostics, cleanup
- **From**: A.U21.01 (ref writer refusals), A.U21.02 (pin-moving notice), A.U21.03 (record round trip), A.U21.15 (build
  output `error:`/`warning:` helper), A.U21.17 (fakes take `run()`'s keyword-only shape at `:32, 210, 224, 242, 253, 273,
  385, 484`; `run_retried` cases `:495-515` hold), A.U21.30 (leftover removal), A.U27.29 (read: `SetupError` holds),
  A.U8.14 (read: `:498-507` holds), A.U28.01 (read: `run_retried` holds).
- **Site**: `tests_scripts/test_setup_toolchain_env.py` (fakes; new tests).
- **Change**: new: `write_micropython_ref()` on a `tmp_path` TOML — no `ref` → `SetupError` and the file byte-identical,
  two `ref` lines → `SetupError`, a `ref` under `[toolchain]` only → `SetupError` naming `[micropython]`, one line →
  rewritten with the rest byte-identical; `run_setup()` (monkeypatched) — `--latest` resolving to the pinned tag writes
  nothing and prints no notice, to a newer tag writes it and prints the notice naming both refs, `--micropython-ref
  v1.28.0` prints the notice and leaves the file byte-identical, both flags → `SetupError`; `write_toolchain_record()`
  then `read_toolchain_record()` round-trips every key, a raise inside `run_verification_sequence()` leaves no record,
  the hashes equal an independent `hashlib.sha256` of the three files; `build_mpy_cross()` with a fake `make` printing
  `foo.c:1: error: x` (exit 0) → `SetupError` "…reported an error", a `warning:` line → the warnings message, clean →
  the binary path; leftover removal on a fabricated toolchain dir (`build-coverage`, `build_overrides/old_override`,
  `node/node-v22.1.0-linux-x64` removed; the rest, a symlink pointing outside, `ports/rp2/build-OTHER` kept; the tuple
  equals the names the `apply_*()` functions write in a `tmp_path` run); fake `run`s accept the keyword-only shape.
- **Resolved**: —
- **Unit**: U21
- **Depends**: A.U21.01-.03, .15, .17, .30 (TOOLCHAIN).
- **Blast carried by**: —
- **Kind**: test

### M.TSC.126 Bench host: password off argv, documentation MAC, armed switch, netfilter, commands
- **From**: A.U21.19 (password never in argv), A.U21.20 (`:239-249` → MAC `00:00:5e:00:53:01`), A.U21.23 (dead-man's
  switch around bridge changes; `:394-429` fakes answer the new queries), A.U21.25 (`:370-382`: `tee` not a temp `cp`),
  A.U21.24 (`:154-198` → table-driven command checks; `ensure_node()` asks for `curl` first), A.U21.21 (`:519-571`
  `ensure_node`: `_node_release` pair; SHASUMS errors named), A.U21.28 (`:60-112` resolver by `2e8a` plus the MicroPython
  by-id link), A.U28.20 (Playwright install failure named), A.U1.05/A.U1.08 (read), A.U1.22 (`:5-7` comment), A.U24.66
  (3 literals); A.U21.26 (passwordless-sudo check L0) and A.U21.27 (picotool skip, USB and shadowing L0) — named for TSC
  by M.TOOL.052/.065/.071's blasts, carried nowhere (gap pass G3).
- **Site**: `tests_scripts/test_setup_toolchain_env.py:1-10`, `:60-112`, `:154-198`, `:239-249`, `:370-571`, new tests.
- **Change**: header comment `:5` → "README.md's tier table defines 'flash' and 'bench'; tests_hardware/README.md holds
  the manual nmcli recipe"; the parsed MAC fixture is `00:00:5e:00:53:01` (a documentation-reserved address);
  credential tests: no recorded argv contains the password, the `edit` call's `stdin_text` sets it, `main(["--password",
  "x"])` is an argparse error, `run_env()` reads `BENCH_AP_PASSWORD`; bridge creation fakes answer `nmcli -g
  GENERAL.CONNECTION device show eth0`, `systemctl is-active` (active → inactive), `ip -o -4 addr show br0`, `ip -o route
  get`; new: a poll that never sees an address raises `SetupError` with no `systemctl stop` recorded, `is-active` not
  active after arming → `SetupError` and no `nmcli connection add`, a profile name with a space is shell-quoted in the
  `bash -c` argument, no uplink profile → no `connection up`; netfilter: no recorded argv references a `/tmp` path;
  command checks table-driven (present → no install; missing → one `apt-get install` for several; still missing → named
  error; `--skip-apt` and missing → the new message); `ensure_node()` with no matching Node and no `curl` asks for `curl`
  before downloading, a SHASUMS text without this arch's line → `SetupError`; resolver: a `2e8a` node without a
  MicroPython by-id link is not selected, `MPREMOTE_DEVICE` wins, `board` prints the path (`main()` with
  `resolve_board_serial` monkeypatched); Playwright install failure → `SetupError` naming `--skip-npm`, `install-deps`
  failure with `skip_apt=False` named; device literals → fixture names. Passwordless sudo (A.U21.26), fake `run`/`which`:
  every command allowed → no error; `iw` refused → the `SetupError` names `iw` only; each probe is `sudo -n <absolute
  path> <version argument>`; the check runs after the command check and before `ensure_bench_bridge()`. picotool
  (A.U21.27): a previous record naming the same `picotool_tag` and a fake `version` output carrying it → no `cmake` and
  no `sudo` recorded, the "already installed" line logged; a different tag → the build and `sudo make install` recorded;
  a fake `--help` with "compiled without USB support" → `SetupError` in the flash tier, a warning in `setup`/`generic`;
  a second `picotool` earlier on the fake `PATH` → a warning naming both paths.
- **Resolved**: —
- **Unit**: U21 (U1 comment; U24 literals; U28 Playwright).
- **Depends**: A.U21.19-.28, A.U28.20 (TOOLCHAIN).
- **Blast carried by**: harness resolver cases → M.TSC.171.
- **Kind**: test

## tests_scripts/test_spec_structure.py
### M.TSC.127 SPEC headings numbered, in their Part, listed under it
- **From**: A.U36.532 (6), A.U36.541 (Part 0 joins the letters).
- **Site**: new `tests_scripts/test_spec_structure.py`.
- **Change**: every `##`/`###`/`####` heading outside fenced code starts with its Part's letter and a number one level
  deeper than its parent and sits after its `# Part X` heading; front matter before the first `# Part` is exempt; Part
  letters `0`, `A` … `M`; numbers ascend within their parent but may skip; each Part's "Sections:" line equals its `##`
  headings; mutation fixtures (a `##`-level `X.n.m`, a stray section, a stale Sections line) fail.
- **Resolved**: —
- **Unit**: U36
- **Depends**: A.U36.532, A.U36.541 (SPEC).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_src_sleep_forms.py
### M.TSC.128 No float reaches an asyncio sleep; synchronous sleeps only where named
- **From**: A.U31.19 (1); SRC_SENS GAP-1 (`time.sleep`/`sleep_ms`/`sleep_us` in `src/` only at the two named exceptions,
  M.SRC_SENS.002/.008).
- **Site**: new `tests_scripts/test_src_sleep_forms.py`.
- **Change**: AST over `src/*.py`: `asyncio.sleep(` takes an int literal or a module-level `const(<int literal>)` name;
  no `asyncio.wait_for(` remains; `sleep_ms(`/`wait_for_ms(` arguments contain no float literal and no `/`; any
  `time.sleep`/`time.sleep_ms`/`time.sleep_us` (any alias) outside the two named exceptions (SPI CS settle, the boot bus
  clear in `asy_i2c_driver.py`) fails; bite fixtures `await asyncio.sleep(0.05)` and a stray `time.sleep_ms(1)`.
- **Resolved**: —
- **Unit**: U31 (the GAP-1 case with M.SRC_SENS.002's unit if earlier).
- **Depends**: A.U31.09-A.U31.18 (SRC), M.SRC_SENS.002/.008.
- **Blast carried by**: SPEC D.4/F.1, Part N `loop.sync_wait_max_us` "Checked by" → A.U31.19/GAP-1 (SPEC).
- **Kind**: test

## tests_scripts/test_stored_config_golden.py
### M.TSC.129 Stored config keys pinned at the release
- **From**: A.U11.33 (2), A.U37.10.
- **Site**: new `tests_scripts/test_stored_config_golden.py`.
- **Change**: per `DEVICE_NAMES` device, each config file name and its stored key → type map (special-alone fields
  excluded) derived from the generated construction and the schemas; staged: U11 asserts two derivations are identical;
  U37 compares with `golden/stored_config.json` and fails with "a change to a persisted key or file name needs a
  migration in the same commit".
- **Resolved**: —
- **Unit**: U37 (stage U11).
- **Depends**: M.TSC.018.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_strip_type_checking.py
### M.TSC.130 The stripper handles every `TYPE_CHECKING` form, line-preserving
- **From**: A.U27.04 (`:50-62` rewritten; new cases), A.U15.02 (`:96-98` SCD30 guard is the plain form), A.U24.73
  (`Any`); read: A.U20.14 (the stripper's own tests unchanged by it).
- **Site**: `tests_scripts/test_strip_type_checking.py` (whole file).
- **Change**: `test_leaves_compound_condition_untouched`/`test_leaves_if_else_untouched` → the compound body stays with
  `False` in place of the name, the else body stays live, the import guard goes, and the output executes under CPython
  with `TYPE_CHECKING` undefined; `:22-47`, `:72-104` assert "no load of the name" instead of a substring test; new: for
  every real `src/*.py` the line count and every untouched line equal the input's; a single-statement suite gets `pass`;
  `x = TYPE_CHECKING or y` becomes `x = False or y`; a load left after stripping raises `StripError` naming path and
  line; `:96-98` asserts every `src/` guard is the plain D.6 two-line form and is removed; no `Any`.
- **Resolved**: —
- **Unit**: U27 (stages U15, U24).
- **Depends**: M.SCR.070, A.U15.02.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_stripped_image_boots.py
### M.TSC.131 The stripped, compiled image set boots under the twin
- **From**: A.U27.05 (2).
- **Site**: new `tests_scripts/test_stripped_image_boots.py`.
- **Change**: per `DEVICE_NAMES` device: `stage_python_modules()` into `tmp_path/stage`; the toolchain's `mpy-cross`
  (copied into `tmp_path` first) compiles every staged `.py` except `main.py` to `.mpy` (a compile error fails naming the
  module); the `.py` files are removed; the boot `_boot_generated_device()` performs runs with `MICROPYPATH=<stage>:
  digital_twin:digital_twin/unixport:.frozen` and the same stub `frozen_html.py`, asserting what the source boot asserts
  (M.TSC.086). A missing `mpy-cross` or Unix port fails.
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.TSC.085 (helper takes a root), M.SCR.066 (staging split), M.TWIN.017.
- **Blast carried by**: SPEC B.11 production-readiness paragraph → A.U27.05 (SPEC).
- **Kind**: test

## tests_scripts/test_suppression_form.py
### M.TSC.132 Every suppression coded, ordered and reasoned
- **From**: A.U28.30 (1).
- **Site**: new `tests_scripts/test_suppression_form.py`.
- **Change**: over the eight scopes' `.py` files (tokenised comments): fails, naming file:line and the expected form, on a
  bare `# type: ignore` or `# noqa`; a code list not ascending or not ", "-separated; an inline `# noqa` without ` -
  <reason>`; in `src/`, a `# type: ignore[…]` without a trailing `  # <reason>` or a reason line directly above; in
  `src/`, any `# noqa`.
- **Resolved**: —
- **Unit**: U28
- **Depends**: A.U28.30 (2)-(5) (the rewrites, TOOL and each file's owner).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_task_inventory.py
### M.TSC.133 Every task site is a starter or a tabled row
- **From**: A.U10.19 (L0 half).
- **Site**: new `tests_scripts/test_task_inventory.py`.
- **Change**: every `create_task(`/`start_server(` in `src/` sits in a starter returned by `get_task_starters()`/
  `get_timer_starters()` or is a row of SPEC C.9's table between `<!-- tasks:begin -->`/`<!-- tasks:end -->` (config
  flush, captive DNS, hotspot LED flash, per-connection HTTP), matched by file and enclosing function; an untabled site
  fails; a tabled row with no site fails (stale).
- **Resolved**: —
- **Unit**: U10
- **Depends**: A.U10.19 (SPEC C.9 table).
- **Blast carried by**: L1 fan-in scenario → A.U10.19 (TEST_HELP/TEST_UNIT).
- **Kind**: test

## tests_scripts/test_test_sh.py
### M.TSC.134 `test.sh` validation, help and the rejection contract (exit 2)
- **From**: A.U7.06 (`:512-527` extended; new timeout-variable cases), A.U7.19 (`--help` precedes the sweeps), A.U35.24
  (heavy-file list check), AC_NOTES 43/OR133 (usage and setting errors exit 2), A.U24.40 (`:373-380` asserts the tree
  is unchanged), A.U27.14 (read: `:31-46` ordering unaffected), A.U7.08 (read: `_PYTEST_LINE` stays a substring),
  A.U36.548 (`:446` "every one of the 85 files" → "every file"), A.U24.66 (`:359` fixture → `fixture_device`), A.U6.03 +
  A.U6.14 (read: `:61-66` finds `test_build_website_sh.py`'s `devices/` write), A.U8.22 (subprocess timeouts → two
  tagged constants); M.SCR.035, M.SCR.042.
- **Site**: `tests_scripts/test_test_sh.py:20-70`, `:300-380`, `:440-530`, new tests.
- **Change**: `_NESTED_RUN_TIMEOUT_S = 60` (`# @tunable l0.test_sh_nested_run_timeout_s = 60`) at `:307, :453, :471, :544`
  and `_SNIPPET_TIMEOUT_S = 30` (`l0.test_sh_snippet_timeout_s`) at `:650, :699, :737, :780`; `:314`'s 0.1 stays a test
  input; rejection cases expect exit 2: an unknown argument, a bad `GC_THRESHOLD`, `PER_FILE_TIMEOUT_S=0`/`-5`/`abc`,
  `TESTS_SCRIPTS_TIMEOUT_S=0`, each before `tests/_tmp` or `devices/zz_test_*` is touched (tree listing unchanged, the
  `:512-527` pattern); `--help` prints the usage (every option and env variable M.SCR.035 lists, with defaults) and exits
  0 before any sweep; the heavy-file list parsed from the script names only existing `tests/test_*.py` files, and the
  list-check function run against a fixture list with a missing name exits 2 with "heavy-file list names <file>, which
  does not exist"; `:373-380`: after each call the tmp tree's listing is unchanged; `:446` comment as above; `:359`'s
  fixture TOML is `fixture_device.toml`.
- **Resolved**: SCR Q1 → (a), OR133 (AC_NOTES 43): exit 2 for every usage or setting error, firm; A.U7.06's "exit 1"
  cases take 2.
- **Unit**: U27 (stages U7, U8, U24, U35, U36 text).
- **Depends**: M.SCR.035, M.SCR.042.
- **Blast carried by**: SPEC E.10 exit codes → A.U7.02 (SPEC).
- **Kind**: test

### M.TSC.135 The job runner: flavours, retries, fail-closed log, per-device and harness jobs
- **From**: A.U27.12 (`:384-440` retargeted to `scripts/_unix_port.sh`: `unix_port_flavour`, `"standard"`; `:406-408`
  settrace path via `unix_port_bin settrace`), A.U36.512 (`_variant_of` → `_flavour_of`, four test names), A.U7.26
  (`:408` skip → fail), A.U21.22 (the rebuild condition includes the record), A.U21.12 (lwIP host loop), A.U7.04
  (`RETRIED-PASS 2/3`), A.U7.05 (`_flag` self-contained; no-verdict marker), A.U24.65 (per-device expansion; heavy list
  names the three files; `_flag_memory_errors` count stays 2), A.U27.38 (harness jobs), A.U8.16 (speed-probe stub on a
  monotonic uptime clock), A.U8.15 (read: tag lines stripped by `_without_comments()`), A.U27.33 (read: trap tests hold),
  A.U7.20 (`_cleanup` copies failed logs first); M.SCR.036, .040, .041, .043; SCR gap 3 (harness jobs, timeout key,
  `--coverage` skipping lwIP and harness jobs).
- **Site**: `tests_scripts/test_test_sh.py:100-260`, `:319-345`, `:384-440`, `:564-628`, new tests.
- **Change**: the flavour tests extract `unix_port_flavour()` from `scripts/_unix_port.sh` and assert `"standard"`,
  `"settrace"`, `"lwip"`, `"unusable"`; the rebuild/re-check assertions read `unix_port_ensure` and the toolchain-record
  condition; the settrace path comes from `unix_port_bin settrace`, a missing build fails; speed-band tests drive a canned
  two-read `/proc/uptime` stub: each band picks its multiplier, a stepped realtime clock leaves the band unchanged, an
  unreadable uptime file yields 1×; `_flag` (extracted by regex, run with only `results_dir` set) on a nonexistent path
  and with a stub `grep` exiting 2 each write a `.noverdict` marker, `_flag_memory_errors "$tag" "$log_file"` occurs
  exactly twice; a stub interpreter timing out once then passing yields `RETRIED-PASS 2/3` (counted retried, Result
  PASS, root-cause line printed); a fixture tree with two TOMLs and one `PER_DEVICE = True` file dispatches two jobs with
  the right `TEST_DEVICE` and tags `<file>[<device>]`, a file without the marker one job; the dispatch list has one
  `scenarios[<device>]` job per derived device (first) with its `per_file_timeout_overrides_s[scenarios]` key and one job
  per `tests/lwip_host/test_*.py` on the lwIP binary (last), neither under `--coverage`; the trap kills recorded PIDs and
  copies failed logs to the archive before removing scratch.
- **Resolved**: —
- **Unit**: U27 (stages U7, U8, U21, U24, U36 names).
- **Depends**: M.SCR.036, M.SCR.040, M.SCR.041, M.SCR.043, M.SCR.044.
- **Blast carried by**: —
- **Kind**: test

### M.TSC.136 The E.10 summary block, coverage reports and the step-summary rule
- **From**: A.U7.03 (`:764-813` `_verdict_block()` rewritten; fixture results dir case), A.U7.07 (read: noise text holds),
  A.U24.72 + A.U28.15 (`:815-823` three render calls → four reports; `:826-842` `always() &&` count 6 → 8), A.U28.16
  (`:828-830` comment "that one gates too"), A.U28.08 (read: `:826-842` stays here), A.U27.18 (new
  `test_the_runner_never_writes_the_github_step_summary`), A.U7.20 (evidence archived, never deleted); M.SCR.044,
  M.SCR.045.
- **Site**: `tests_scripts/test_test_sh.py:760-842`, new tests.
- **Change**: a fixture results dir with one `RETRIED-PASS`, one crashed log (no count line) and one `.memerr` renders the
  E.10 block with the right file and test counts and exit 1; Result lines for pass, fail and "PASS (coverage report not
  rendered)" (exit 3); under `--coverage` the lwIP and harness jobs are listed under `Skipped:` with the plain-pass reason,
  and the port-53 scenarios under `Deselected:`; the render step produces four reports (src, digital_twin, generated,
  host) and `ci.yml` uploads four summaries and four HTML artifacts (`always() &&` count 8); `GITHUB_STEP_SUMMARY`
  appears in neither `scripts/test.sh` nor anything it sources or runs for its summary; the block is also written to
  `$results_dir/summary.txt`.
- **Resolved**: —
- **Unit**: U28 (stages U7 block, U24 render calls, U27 step-summary rule).
- **Depends**: M.SCR.001, M.SCR.044, M.SCR.045.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_tests_hardware_collect_matrix.py
### M.TSC.137 The hardware levels collect under every option with nothing attached
- **From**: A.U26.31; HW_BENCH GAP-B1 (`--dut-ip <addr>`, `--lwip-control-image <tmp path>`, M.HW_BENCH.001).
- **Site**: new `tests_scripts/test_tests_hardware_collect_matrix.py`.
- **Change**: one subprocess (venv CPython; `PATH` stripped of `mpremote`, `nmcli`, `iw`, `tc`, `iptables`, `picotool`)
  loops `pytest.main(["tests_hardware", "--collect-only", "-q", "-p", "no:cacheprovider", *combo])` over every subset of
  the eight booleans (`--allow-flash-cycle`, `--allow-multi-day-rollover`, `--allow-neopixel-sweep`,
  `--allow-persistence-write`, `--allow-scd30-extra-write`, `--allow-toolchain-reverify`, `--repair-standard-state`,
  `--twin`) crossed with {no soak option, `--soak-duration short|mid|long`}, and each valued option once with all
  booleans on (`--bench-device <each derived device>`, `--image-record <tmp path>`, `--device <sentinel>`, `--dut-ip
  192.0.2.1`, `--lwip-control-image <tmp path>`); every call returns 0 and collects ≥ 1 item; nothing is written but
  stdout. Second test (AST): the only options read at collection time are `--allow-persistence-write` and
  `--allow-scd30-extra-write`, and no option is read at import time of any `tests_hardware` module.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.001, M.HW_BENCH.003.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_tests_hardware_persistence_write_gating.py
### M.TSC.138 Wear-gate deselection with the new flags and the routine set
- **From**: A.U26.74 (`:36-51` flag strings → `--allow-persistence-write`), A.U26.08 (`_ROUTINE_TEST` selected by default;
  the "deselected without the flag" assertions move to the read-while-write test; the five SCD30 dependents collected
  with no flag), A.U26.71 (read: the bench deselection set shrinks by three — "deselected" assertions hold), A.U7.13 (the
  deselection carries its flag in the run record — the property, here; the record file test is M.TSC.216),
  A.U4.08 (`:1-3` docstring: help text only), A.U26.06/A.U26.31/A.U8C2.20 (read).
- **Site**: `tests_scripts/test_tests_hardware_persistence_write_gating.py:1-80`.
- **Change**: flags `--allow-persistence-write`/`--allow-scd30-extra-write`; `_ROUTINE_TEST` → the read-while-write test's
  name for the "deselected without the flag" assertions; new assertion: the five SCD30 dependents are collected with no
  flag; each deselected item is tagged `deselected_by` its flag (M.HW_BENCH.003); docstring states the gate's current
  marker names.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.002, M.HW_BENCH.003, M.HW_BENCH.044.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_third_party_attribution.py
### M.TSC.139 Third-party headers and THIRD_PARTY_LICENSES entries agree
- **From**: A.U34.07 (2).
- **Site**: new `tests_scripts/test_third_party_attribution.py`.
- **Change**: reads `src/*.py` and `THIRD_PARTY_LICENSES.md`: a file whose first line starts `# SPDX-FileCopyrightText:`
  has line 2 `# SPDX-License-Identifier: <expr>` and line 3 a comment naming `THIRD_PARTY_LICENSES.md`, then the module
  docstring; `src/asy_udp_socket.py` has its three comment lines (karfas, the discussion link, `THIRD_PARTY_LICENSES.md`);
  each such file is named by exactly one top-level entry whose first code span is its path, and every entry naming a
  `src/` file points at an existing file with that header.
- **Resolved**: —
- **Unit**: U34
- **Depends**: A.U34.07 (1) (SRC headers).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_threat_model_statement.py
### M.TSC.140 The threat model names every unauthenticated write
- **From**: A.U29.02; A.U29.01 (read: SPEC A.11 names this file).
- **Site**: new `tests_scripts/test_threat_model_statement.py`.
- **Change**: header (≤ 3 lines) "SPECIFICATION.md A.11 names every unauthenticated write the firmware accepts: each PUT
  route, each SystemCmd word, each dispatch field of every device."; `_a11_text()` (from `## A.11 ` to the next `## `/`---`,
  fails naming the heading when absent); `_missing(text, names)`; derived sets: the PUT paths of `ROUTES` (`ast`), the
  `_SYSTEM_CMDS` words (`ast`), every `dispatch: true` field key over `DEVICE_NAMES` (`definitions_for_toml()`); tests
  `test_a11_names_every_put_route`, `test_a11_names_every_system_command_word`, `test_a11_names_every_dispatch_field`, each
  with a mutation fixture.
- **Resolved**: A.U29.02 calls `generate_definitions(build_model(...))` "as `_generate()` does"; `_generate()` moves to
  `definitions_for_toml()` (A.U6.01, M.TSC.038) — the same helper here.
- **Unit**: U29
- **Depends**: A.U29.01 (SPEC A.11), A.U19.20 (`ROUTES`).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_threshold_runner.py
### M.TSC.141 The GC-stage runner: incomplete files fail, the shipped value tagged
- **From**: A.U24.05 (new cases), A.U8.14 (`:11` `_SHIPPED_THRESHOLD = 32768` tagged `gc.threshold_bytes`; `:51` site),
  A.U8.22 (`:26` timeout tag), A.U36.548 (`:59` "exec 85 files" → "exec every file"), A.U7.07 (read: exit codes only).
- **Site**: `tests_scripts/test_threshold_runner.py:1-70`.
- **Change**: `_SHIPPED_THRESHOLD = 32768  # @tunable gc.threshold_bytes = 32768` (and the `:51` site per A.U8.14's list);
  `timeout=_RUN_TIMEOUT_S` (`l0.threshold_runner_timeout_s = 60`); `:59` wording; new: a trailer-less test file exits 1;
  a file whose top level raises exits 1; `sys.exit("x")` exits 1; the threshold is set before `exec()`.
- **Resolved**: —
- **Unit**: U24 (U8 tags; U36 wording).
- **Depends**: A.U24.05 (`tests/_threshold_runner.py`, TEST_HELP), M.SCR.008 (binary).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_ticks_wrap_scan.py
### M.TSC.142 Every tick user scanned statically, generated modules and twin included
- **From**: A.U14.33.
- **Site**: new `tests_scripts/test_ticks_wrap_scan.py`.
- **Change**: over `src/*.py`, `digital_twin/*.py` and every generated module (in memory, `DEVICE_NAMES`): per function,
  every name/attribute assigned from `time.ticks_ms()`, `ticks_us()`, `ticks_add()` or from another such name; fails on a
  `Sub`/`Add` `BinOp` or an ordering `Compare` with one of them as a direct operand (`ticks_diff()` results, `is None`
  and `==` pass) and on a literal `ticks_add()` delta ≥ 2**29; reads the known-users list from the L1 file (one list);
  bite fixtures.
- **Resolved**: —
- **Unit**: U14
- **Depends**: A.U14.33 (L1 file keeps its interpreter-level tests, TEST_UNIT).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_timer_stagger_no_coincidence.py
### M.TSC.143 Retire the arithmetic re-implementation of the timer stagger
- **From**: A.U10.13 (kept), A.U11.39 (the same action, A.U10.13's text: "A-C keeps this one"), A.U8.12 (`:7` mirror site
  of `system.timer_base_period_ms` — the Part N row drops it), A.U36.544 and A.U10.43 (dropped: their edits target a
  deleted file).
- **Site**: `tests_scripts/test_timer_stagger_no_coincidence.py` (95 lines).
- **Change**: the file is deleted; the real sequencer's fake-clock scenario per generated device replaces it (L1,
  `tests/_sensortask_scenarios.py`).
- **Resolved**: A.U10.13 and A.U11.39 are one scenario; A.U10.13's text says A-C keeps it (it runs over A.U10.12's
  `_collect_trigger_starters()`) — kept, A.U11.39 merged into it.
- **Unit**: U10
- **Depends**: A.U10.12, A.U10.13 (TEST_HELP scenario).
- **Blast carried by**: Part N row site list → A.U8.12 (SPEC).
- **Kind**: test

## tests_scripts/test_timing_budget.py
### M.TSC.144 F.3's code-derived timing rows are recomputed
- **From**: A.U31.02; A.U31.01 (read: the table it parses).
- **Site**: new `tests_scripts/test_timing_budget.py`.
- **Change**: parses F.3's table between its markers and recomputes from `src/` (`module_int_const()`/`init_int_default()`,
  no import) and `DEVICE_NAMES`' TOMLs: `hold.scd30_command`, `hold.scd30_snapshot`, `hold.i2c_probe`,
  `stall.i2c_transfer` (largest I2C `timeout`, ≤ its Part N bound), `con.uart_reply`, `con.led_frame`,
  `feed.supervisor`'s terms (`_TASK_CHECK_TIME` × 1000 and ⌈(`_TASK_FAIL_MAX` + 1) / `_TASK_FAIL_INCREMENT`⌉), and
  `_RESET_DELAY × 1000 < 8000`; each equals the row's Value; a value ≤ its consumer's tolerance unless the row says
  "crossed"; every Part N ID exists (A.U8.02's reader); one bite. Constants read from `asy_system_service.py`.
- **Resolved**: —
- **Unit**: U31
- **Depends**: A.U31.01 (SPEC F.3), M.TSC.001.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_toml_schema_contract.py
### M.TSC.145 SPEC L.3's key table equals the validator's
- **From**: A.U20.35 (2).
- **Site**: new `tests_scripts/test_toml_schema_contract.py`.
- **Change**: parses L.3's key table and asserts its rows equal, per table: `[device]` keys from `validate.py`'s allowed
  and required sets (including `bench` (A.U26.01) and `hardware_family` (A.U20.19)), `[device.wiring]` from
  `_DEVICE_WIRING_CONSUMERS`, bus keys from `_BUS_WIRE_FIELDS`/`_BUS_ALLOWED_FIELDS`, `[[instance]]` keys per driver from
  `buildspec.REQUIRED_TOML_FIELDS`/`OPTIONAL_TOML_FIELDS` plus `driver`/`name_ext`, `[instance.wiring]` per driver from
  its `@wiring`/`@value-wiring` tags (and `warn_*` from the signal catalog on notification); the Required column matches.
- **Resolved**: —
- **Unit**: U26 (stage U20; the `bench` row with A.U26.01).
- **Depends**: A.U20.35 (1) (SPEC), M.GEN.025/.036.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_tool_pins.py
### M.TSC.146 Every pin agrees with the lock; Node versions agree
- **From**: A.U28.03, A.U28.23 (`.nvmrc` major), A.U36.528 (read: CLAUDE.md names it).
- **Site**: new `tests_scripts/test_tool_pins.py`.
- **Change**: `tomllib` on `pyproject.toml` and `uv.lock`: every `[dependency-groups] dev` entry is `name==version`; the
  lock's `requires-dev` specifier is `==version` and its `[[package]]` block has `version = "<version>"` (contradiction
  named with "re-run `uv lock`"); `scripts/_render_coverage.py`'s PEP 723 `coverage` pin equals the dev group's;
  `[tool.uv] required-version` is an exact `==` pin and no `.github/**` file carries a second uv version literal;
  `.nvmrc`'s major equals the `@types/node` range's major and the `engines.node` lower bound, and `package-lock.json`'s
  resolved `@types/node` has that major.
- **Resolved**: —
- **Unit**: U28
- **Depends**: A.U28.02/.23 (TOOL).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_tunables_register.py
### M.TSC.147 `@tunable` tags and Part N rows agree
- **From**: A.U8.02 (grammar and register check, relation checks), A.U8.03 (the tag family's exemption is the cap
  gate's), WEB gap 7 (new `tests_js` tags, e.g. `l0.poll_manager_poll_ms`, `l0.render_*`, are scanned), A.U35.56 (read:
  values move only by measurement), A.U8C.120/A.U8C.121/A.U8C2.51 (read: Dependants not checked).
- **Site**: new `tests_scripts/test_tunables_register.py`.
- **Change**: scans `src/ buildgen/ digital_twin/ tests/ tests_scripts/ tests_hardware/ scripts/ toolchain/ js/ tests_js/
  devices/ .github/` and `vitest.config.js` (Python via `buildgen.tag_comments.iter_comment_tokens`; sh/yml/toml `#`;
  js/mjs `//`); fails on a malformed or near-miss tag, a literal missing from the next non-comment line, a tagged ID
  without a Part N row, a `tuned` row without a tag or whose Sites differ from the tagged files and literals, an empty
  Basis/Margin/Re-check trigger or an `estimated` Basis without "measurement owed", a `rule` row naming no check;
  relations: `wdt.timeout_ms` ≤ 8388, `system.reset_delay_s` × 1000 < `wdt.timeout_ms`, `system.task_check_s` × 1000 × 4
  ≤ `wdt.timeout_ms`, `web.connections_per_page_load` ≤ the largest shipped `max_connections`; negative cases on a tmp
  tree (untagged row, unlisted tag, mismatched literal, `@tunabel`, missing literal).
- **Resolved**: the `:62-70` overlap with `test_request_timeout_ceiling.py` — both kept (M.TSC.121).
- **Unit**: U8
- **Depends**: A.U8.01 (SPEC Part N).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_twin_entry_point_order.py
### M.TSC.148 Every booting twin entry prewarms, then shims; the margin holds
- **From**: A.U25.43 (2)-(3), A.U25.34 (UDP shim order; its loud bind failure); TWIN M.TWIN.017 (the shim lives in
  `digital_twin/unixport/`), M.TWIN.057 (prewarm margin).
- **Site**: new `tests_scripts/test_twin_entry_point_order.py`.
- **Change**: AST: every `tests/test_digital_twin_*.py` that boots a device (a load of `sensortask_*`, of
  `run_generic_integration`, or of a scenario library that does) calls `prewarm_poll_set()` at module level before any
  other module-level call except `sys.path` edits, then `patch_asy_udp_socket_for_unix_port()` (from
  `digital_twin/unixport/`); a scenario library is exempt, its entry file carries the calls; every `main()` in
  `digital_twin/` that boots a device has them as its first two statements; `3 × max(device_max_connections(d) for d in
  DEVICE_NAMES) < 512`.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN.017, M.TWIN.057.
- **Blast carried by**: the capability helper unit test → M.TSC.191.
- **Kind**: test

## tests_scripts/test_twin_fake_catalog.py
### M.TSC.149 Every bus-attached driver has its twin fake, dispatch and test
- **From**: A.U25.67; A.U36.543 (read: K.5 names it).
- **Site**: new `tests_scripts/test_twin_fake_catalog.py`.
- **Change**: for every driver in `buildgen.buildspec.BUS_ATTACHED_DRIVERS`: an I2C driver has a branch in
  `digital_twin/machine.py`'s `_build_i2c_chip()` (AST string literals) and a `digital_twin/_<driver>_chip.py`; `fram` via
  `_wire_spi_device()`; `uart_link` via `attach_crossover_jumper()`/`UARTLink`; each has `tests/test_digital_twin_<driver>.py`
  (`uart_link` → `test_digital_twin_uart_link.py`); a branch for a driver outside the set fails; the CI suite's
  per-driver tables (`_SUSTAINED_FAULT`, `_DRIVER_ERRCOUNT_NAME`, `_MEASUREMENT_DRIVERS`) cover the same set.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN (fakes), M.SCR.046 (suite tables).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_twin_never_needs_tests_on_its_path.py
### M.TSC.150 The twin's path guard covers every launch site
- **From**: A.U25.44, A.U27.15 (values read from `scripts/micropypath.toml`'s `twin`; `unit`/`twin` shape cases), HW_BENCH
  GAP-B5 (`tests_hardware/twin_board.py` is a launch site), WEB gap 7 (`tests_js/_twin_process.js` is the JS launch
  site), TWIN gap (`digital_twin/unixport` on the twin path), A.U20.33; read: A.U25.35 (MICROPYPATH constant stays).
- **Site**: `tests_scripts/test_twin_never_needs_tests_on_its_path.py` (whole file).
- **Change**: `from __future__` goes; `_micropypath_values()` finds every twin launch site itself (every `MICROPYPATH`
  assignment in `scripts/`, `tests_scripts/`, `tests_js/`, `tests_hardware/` whose value contains `digital_twin`, in the four
  forms, or a read of `scripts/micropypath.toml`'s `twin`); a file spawning `digital_twin/run_generic_integration.py` with
  no such assignment fails (log fixtures that only name the runner are not launches); every value has no `tests` segment
  and names the file's `twin` value or derives from it with a one-line reason; the file's `unit` has `tests` and no
  `ext`/`digital_twin`, `twin` has `digital_twin`, `digital_twin/unixport` and `ext` and no `tests`, both end in `.frozen`;
  `digital_twin/machine.py` imports under CPython (no MicroPython-only import at module scope).
- **Resolved**: —
- **Unit**: U27 (stage U25 guard).
- **Depends**: M.SCR.009, M.HW_BENCH.091, M.WEB.082, M.TWIN.017.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_twin_wiring_contract.py
### M.TSC.151 The twin plan's shape, its readers and `main()`'s keywords agree
- **From**: A.U20.28 (3); GEN gap 3 (runner keywords ⊆ `main()`'s; `uart` keys `initiator_bus`/`responder_bus`,
  M.GEN.043); A.U25.25 (3) (`pins`); A.U36.518 (read: SPEC L.4 names the test).
- **Site**: new `tests_scripts/test_twin_wiring_contract.py`.
- **Change**: for every `DEVICE_NAMES` device and both fixtures the plan validates against `TwinWiringPlan` (keys and
  value types, recursively, `pins` and `uart: UartPair | None` included); an AST scan of every `.py` under
  `digital_twin/`, `tests/`, `tests_scripts/`, `scripts/` that reads `*_wiring_plan.json` (found by grepping
  `wiring_plan`) collects every string key read off a plan value and asserts it is declared; `uart`'s `initiator_bus`/
  `responder_bus` name buses the device declares; the keyword arguments the twin runner passes to `main()` are a subset of
  the generated `main()`'s keyword-only parameters (`watchdog`, `cfg_path`, `debug`, `web_host`, `web_port`).
- **Resolved**: A.U20.28 asserts equality of the keyword sets and `initiator_var`/`responder_var`; M.GEN.006 keeps
  `debug` (A.U25.69) and M.GEN.043 takes the bus ids (A.U17.18) — GEN gap 3: subset and `_bus` keys.
- **Unit**: U25 (stage U20).
- **Depends**: M.GEN.006, M.GEN.043.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_uart_changelog.py
### M.TSC.152 The UART changelog's constants table matches the module
- **From**: A.U17.11 (2), A.U17.08 (read: deleting the changelog deletes this test), A.S0930.07 (read: row order and
  status apply to its entry).
- **Site**: new `tests_scripts/test_uart_changelog.py`.
- **Change**: docstring (≤ 3 lines) "Ties UART_C_PORT_CHANGELOG.md to the protocol module: its constants table, its closed
  status set and its row order. Deleted with the changelog at the post-audit C reconciliation."; (a) the `(name, value)`
  pairs of every non-log-code `const()` in `src/asy_uart_comm.py` equal the table's (fix text "add a changelog entry
  naming the constant, then set its row's Value and Last entry"); (b) every Last entry is `baseline` or an existing row
  whose Change names the constant; (c) Class is `A` or `B`; (d) Status is one of A.U17.09's four values; (e) Class A and B
  rows each ascend; negative cases on `tmp_path` copies.
- **Resolved**: —
- **Unit**: U17
- **Depends**: A.U17.09/.11 (1) (changelog table, SRC_UART/DOCS).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_vendored_freezefs.py
### M.TSC.153 freezefs pinned by commit hash
- **From**: A.U34.08 (new L0 hash file), A.SDEP.07 (read: a re-vendor at a newer commit renames the pinned commit).
- **Site**: new `tests_scripts/test_vendored_freezefs.py`.
- **Change**: a `{path: (commit, sha256)}` table for `ext/freezefs/__main__.py`, `archive.py`, `ffsextract.py`,
  `ffsmount.py`, `LICENSE` at the commit THIRD_PARTY_LICENSES.md records (`26be9e3…` unless the U0 refresh moved it);
  each file's sha256 asserted; the failure message names the commit and says a move is a recorded decision.
- **Resolved**: —
- **Unit**: U34 (hashes follow the U0 refresh).
- **Depends**: A.SDEP.07, A.U34.08 (1).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_vendored_microdot.py
### M.TSC.154 Microdot and its stubs pinned by hash
- **From**: A.U19.18, A.U34.12 (stubs join the table), A.U19.19 (read: SPEC A.5 names the test), A.U36.030 (read); GEN Q1
  → (a), OR131 (AC_NOTES 41): stubs byte-identical in `ext/typings/microdot/` (M.GEN.050/.051).
- **Site**: new `tests_scripts/test_vendored_microdot.py`.
- **Change**: one `{path: (tag, sha256)}` table for `ext/microdot.py`, `ext/LICENSE-microdot` and
  `ext/typings/microdot/__init__.pyi`, `microdot.pyi`, `multipart.pyi`, all at the tag M.GEN.051 vendors (THIRD_PARTY
  records it; `v2.6.2` digests at HEAD, the refreshed tag's after U0); each sha256 asserted; no network or git history;
  the failure message names the tag and says a move is a recorded decision (THIRD_PARTY_LICENSES.md).
- **Resolved**: GEN Q1 answered (a) (OR131) — firm.
- **Unit**: U19 (stubs row from U0/U8 with M.GEN.050).
- **Depends**: M.GEN.050, M.GEN.051.
- **Blast carried by**: THIRD_PARTY wording → A.U19.18/A.U34.12 (DOC).
- **Kind**: test

## tests_scripts/test_watchdog_feed_sites.py
### M.TSC.155 The watchdog feed sites are exactly the pinned set
- **From**: A.U10.08 (L0 half), A.S0930.20 (6), A.S0930.34 (2), A.U31.07; M.SRC_CORE.009 (the pinned set),
  M.SRC_CORE.010/.011 (`_reboot()`/`_supervise()` end states).
- **Site**: new `tests_scripts/test_watchdog_feed_sites.py`.
- **Change**: parses `src/*.py` and every generated module (in memory, `DEVICE_NAMES`); every `feed_watchdog(`/`.feed(`
  call must be in the pinned set: (a) `SystemService.feed_watchdog()`'s body, which must test `_feed_owned`; (b)
  `_supervise()`'s exactly two `feed_watchdog()` calls (escalation block, pass end); (c) `run_setups()`'s per-unit call
  inside its bounded `for`; (d) `_own_feed()`'s body, referenced only by `_shutdown_sequence()`, by `_reboot()` once under
  `if fed:` as the statement immediately before `self._reset_timer.init(`, and as the `step_done` argument of
  `_flush_config_stores(close=True, step_done=self._own_feed)`, `self._storage.quiesce(self._own_feed)` and
  `erase_chip(self._own_feed)`; fails on any other site, a feed in a `callback=`/`lambda` of `Timer.init(`/`Pin.irq(`, a
  feed in any `while` other than (b) (a `while` reaching `_own_feed()` fails; calls through `step_done` do not), a
  generated-module feed; `_supervise()` references none of `reboot_system`, `reboot_bootloader`, `_request_shutdown` and
  calls `_reboot(` exactly once without `fed=`; bites: a fifth `.feed(` site, a dropped `_feed_owned` test, the
  escalation `_reboot(` replaced by `self.reboot_system()`.
- **Resolved**: OR31.a (3) "one runtime feed site" vs OR120/OR130 — the latest owner decisions win (M.SRC_CORE.009); the
  three constituents are one file's content.
- **Unit**: U31 (stages U10, U11, S0930 rows).
- **Depends**: M.SRC_CORE.009, .010, .011.
- **Blast carried by**: L1 scan budget → A.U10.08 (TEST_UNIT).
- **Kind**: test

## tests_scripts/test_website_layering.py
### M.TSC.156 The visual/mechanics layering is guarded
- **From**: A.U23.41, A.U23.40 (the ESLint rule it checks is configured).
- **Site**: new `tests_scripts/test_website_layering.py`.
- **Change**: over every `js/*.js` (comments and plain string contents stripped, template `${…}` kept):
  `createElement` only in `js/templates.js`; `document.` queries only in `js/main.js`/`js/app.js`; `.className`/
  `.classList`/`.style.` writes only in `js/templates.js`; controllers' `dataset.` writes only the documented hooks
  (A.U23.42's list in SPEC H.3); every `querySelector(`/`querySelectorAll(`/`closest(` call with a `${` template contains
  `CSS.escape(`; `eslint.config.js` configures A.U23.40's rule for both production globs; the docstring states the
  text-based limit; bites on a temp copy.
- **Resolved**: —
- **Unit**: U23
- **Depends**: A.U23.07/.40/.42 (WEB).
- **Blast carried by**: —
- **Kind**: test

## Unlisted existing files (site index missed them; `tests_scripts/` is this cluster's directory)

## tests_scripts/test_lint_sh.py
### M.TSC.157 `lint.sh`'s guard block, help and arguments; gc greps leave for the checker
- **From**: A.U27.20 (`grep_guard` extraction), A.U27.21 + A.U11.10 + A.U20.06 + A.U30.14 (the two gc greps and their
  cases `:12-13, :41-45, :78-106` move to the checker's tests), A.U7.11 (summary block; arguments rejected), A.U1.21
  (read: `:16-21` extraction untouched by the comment repath); M.SCR.024, M.SCR.025.
- **Site**: `tests_scripts/test_lint_sh.py` (whole file).
- **Change**: `_SRC_COLLECT`/`_BUILDGEN_COLLECT` and every gc case go (now M.TSC.095's fabricated cases on
  `scripts/_check_gc_collect_sites.py`); the method-assign guard is extracted as the `grep_guard` call that names it and
  run against a fabricated tree: a suppression anywhere in `src/` fails, the same suppression outside `src/` passes, an
  unreadable tree or grep exit ≥ 2 fails closed; `scripts/lint.sh --help` exits 0 with the usage, any other argument
  exits 2 with the usage on stderr; the live tree satisfies the guard; the summary block's Result line names each check.
- **Resolved**: —
- **Unit**: U27 (stage U7 block).
- **Depends**: M.SCR.024, M.SCR.025.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_generate_sensortask_modules.py
### M.TSC.158 The one writer of the generated tree: all or nothing, pruned, stamped
- **From**: A.U27.11 (writer, pruning), A.U20.28 (`:41-46` → the written plan equals `compute_twin_wiring()`), A.U20.17
  (`:58` `BuildError(..., rule=, fix=)`), A.U6.02 (definitions written), A.U5.03 (read: `fram=` text gone), A.S0930.02
  (read: holds), SCR gap 3 (`api/` written and pruned; single-device `--device-toml --out-dir` mode); M.SCR.068.
- **Site**: `tests_scripts/test_generate_sensortask_modules.py` (whole file).
- **Change**: for every `DEVICE_NAMES` device the tree holds `sensortask_<d>.py`, `sensortask_<d>_wiring_plan.json`
  (equal to `compute_twin_wiring()`, `instances` included by it), `sensortask_<d>_expected.json`, `sensortask_<d>_main.py`,
  `sensortask_<d>_main_noautostart.py`, `definitions/<d>.json`, `api/<d>.json` and the stamps, each equal to the in-memory
  generation; a stale file of a removed device (in every output kind, `api/` included) is pruned; a build error in one
  device leaves the previous tree untouched (all or nothing), prints one line with `- fix: ` and exits 1 (the fixture
  raises `BuildError(device, message, rule=..., fix=...)`); `--device-toml <tmp> --out-dir <tmp>` writes only that
  device's outputs into `--out-dir`. Output dirs in `tmp_path`.
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.SCR.068, M.GEN.019, M.GEN.022, M.GEN.043.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_buildgen_web_tag.py
### M.TSC.159 `@web` grammar: the full tagged-file inventory and every new key
- **From**: A.U20.26 (`~510-530` → one full-inventory test), A.U6.17 (`alwaysExecuted` bool only, exclusive with
  `dispatch`), A.U6.19 (`format` accept/reject), A.U6.20 (`special:null` accept), A.U6.27 (`codes=` accept/reject),
  A.U6.29 + WEB gap 2 (`shape=` values `hostLabel|countryCode|hostName|ipv4List`), A.U20.25 (`hidden=` alone accepted, with
  another key rejected), A.U23.16 (`defaultValue` rejected as a retired key), A.U23.17 (`clearable` on a string accepted,
  on a number rejected), A.U23.23 (the warn-sibling key, an unknown sibling rejected), A.U36.514 (the L.6.4 key list equals
  `_FIELD_KNOWN_KEYS | _GROUP_KNOWN_KEYS`), A.U18.38 (`:492` identity set gains `HotspotPW`), A.U15.12 (`:409` SCD30 config
  set gains the three FRC keys), A.U6.26 (`:491-538` the DNS group and file), A.U36.544 (`:102-103`, `:477` pointers),
  A.U24.66 (17 literals), A.U5.16 (read: messages unchanged), A.U6.18/A.U15.11/A.U9.01 (read: field sets only).
- **Site**: `tests_scripts/test_buildgen_web_tag.py` (whole file; `:49-62`, `:102-103`, `:409`, `:477`, `:491-538`).
- **Change**: known-key accept/reject rows for each new key as listed; one inventory test asserting, over every
  `src/*.py`, `{p.name: sorted((t.section, t.submit_group) for t in parse_web_group_tags(p, …))}` equals the expected
  map (files with no tag absent); the real-file field-set pins follow the new fields; a test reads SPEC L.6.4's `@web`/
  `@web-group` key table and asserts it equals the parser's known keys; `:102-103` comment → "the `path`/`decimals` tag
  capability (SPECIFICATION.md L.6.4)", `:477` "Part L" → H.5.1; device literals → fixture.
- **Resolved**: —
- **Unit**: U23 (stages U6, U15, U18, U20, U36).
- **Depends**: M.GEN.046, M.GEN.017.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_buildgen_driver_registry.py
### M.TSC.160 Registry: every reader needs setup; renamed classes
- **From**: A.U10.10 (`:21, :26` `needs_setup` for scd30 and neopixel → True), A.U10.38 (`:86` class names), A.U24.66,
  A.U24.75 (read: named `buildspec` home).
- **Site**: `tests_scripts/test_buildgen_driver_registry.py:21-90`.
- **Change**: every `SensorReader` driver and neopixel report `needs_setup` True; class names per A.U10.38; device
  literals → fixture/derived.
- **Resolved**: —
- **Unit**: U10 (U24 literals).
- **Depends**: M.GEN.040, M.GEN.041.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_buildgen_graph.py
### M.TSC.161 Construction graph: the LED and NTP edges
- **From**: A.U5.07 (`:28-32`, `:86-87`; new: with `led_target` and an `sgp40`, `ntp` precedes `sgp40` and notification,
  the NeoPixel precedes `conn`), A.U16.20 (read: `:41-60` builds unchanged), A.U24.66.
- **Site**: `tests_scripts/test_buildgen_graph.py`.
- **Change**: as listed; a `setter` wiring mode is not a graph edge kind any more.
- **Resolved**: —
- **Unit**: U5 (U24 literals).
- **Depends**: M.GEN.044.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_buildgen_requires_tag.py
### M.TSC.162 `@requires`: accept sides assert, typed comparison
- **From**: A.U20.37 (2) (`:298, :337`: `check_requires_tags()` returns `None` and one value moved across the bound
  raises), A.U20.24 (3) (`nan`/`inf`/`-inf` rows), A.U20.32 (read: the non-comparable message holds), A.U24.66.
- **Site**: `tests_scripts/test_buildgen_requires_tag.py:290-340`, new rows.
- **Change**: as listed (rule `tag.non-finite-number` on the non-finite rows).
- **Resolved**: —
- **Unit**: U20 (U24 literals).
- **Depends**: M.GEN.038.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_buildgen_schema_ast.py
### M.TSC.163 Schema extraction: raise for a schema-named constant, read concatenation
- **From**: A.U20.25 (the silent-skip pin → a raise for a schema-named unreadable constant, the skip for others), A.U20.12
  (a tuple-concatenation row).
- **Site**: `tests_scripts/test_buildgen_schema_ast.py`.
- **Change**: as listed.
- **Resolved**: —
- **Unit**: U20
- **Depends**: M.GEN.045.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_buildgen_wiring.py
### M.TSC.164 `@wiring` grammar without the setter mode; `log=` targets
- **From**: A.U5.07 (setter-mode cases → a `setter` mode rejected as unknown), A.U5.03 (`fram=` → `log=` rendered
  targets), A.U20.37 (read: name-shape and typo-boundary cases stay the model for the other families), A.U10.38 (class
  names), M.TSC.001 (`system_service.py` ×2).
- **Site**: `tests_scripts/test_buildgen_wiring.py`.
- **Change**: as listed.
- **Resolved**: —
- **Unit**: U5 (U10 names).
- **Depends**: M.GEN.048.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_digital_twin_ci_suite_errcount.py
### M.TSC.165 Suite helpers: failure events, signals, strict readers, a missing log fails
- **From**: A.U25.36 (`_failure_events()`/`_error_codes()`/`_reset_line()` cases), A.U25.64 (signal-report cases), A.U25.66
  (missing-counter case per site), A.U27.01 (`:367-377` inverted: a missing log and an empty log fail), A.U35.38
  (normal-boot check cases), SCR gap 3 (Run 1's `UTCTime`/`LocalTime` null check, M.SCR.049), A.U25.35 (helpers move to
  the run context), A.U20.28 (the plan reader follows the producer), M.TSC.001 (`print_log.py`), A.U11.31 (read: status
  codes only), A.U8.22 (read: `:223-286` test inputs untagged); A.U19.14 (`:257-259` cites BACKLOG item 24, which leaves
  at U19 — M_DOCS gap 2, gap pass G3); A.U25.33/A.U25.36 (2) and A.U35.28 (3) (the runner's shutdown-line fields this
  file parses — M.TWIN.050's Blast "their L0 parsers (TSC)" and M_SCR gap 4, gap pass G3).
- **Site**: `tests_scripts/test_digital_twin_ci_suite_errcount.py`.
- **Change**: new cases: a history `[E10, W15, E10]` with counter 4 → 3 failures; fake procs with returncode −11, the
  suite's own timeout and its own SIGKILL each reported by name; each strict reader fails on a missing counter;
  `test_a_missing_log_is_not_reported_as_a_memory_error` → `test_a_missing_or_empty_log_fails_the_run`; normal-boot check:
  one W fails, NTP's tolerated code passes while not synced, synced + NTP entry fails; Run 1: `UTCTime`/`LocalTime` are
  null before the first sync and both present after; the tolerance constant comes from `scripts/_twin_process.py`.
  The section comment `:257-259` → "# _put_reset_errors_timed() - the elapsed-time budget (SPECIFICATION.md C.7). A
  timeout only catches a call that never finished; the budget covers the band between a normal reset and the server's
  own cap." (history clause "the suite was blind" goes). Shutdown-line parser cases (the suite's helper for the runner's
  `shutdown:` line, M.TWIN.050): `mem_backup: r0=<4 words>` yields four ints, `public_destinations_refused=<n>` an int
  and a nonzero value fails the run naming the field, `fram_writes=<n>` an int, `fram_writes_by=SCD30:4,CFGMGR_SCD30:2`
  a name → int dict (`-` → empty; a name out of order, a duplicate or a non-int count fails naming it),
  `fram_writes_unattributed=<n>` when present an int; a line missing any required field fails naming it.
- **Resolved**: —
- **Unit**: U35 (stages U19 the `:257-259` pointer, U25, U27; the `fram_writes`/`fram_writes_by` cases with A.U35.28).
- **Depends**: M.SCR.046-.049, M.SCR.016; M.TWIN.050 (the shutdown line's fields).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_heap_map_parser.py
### M.TSC.166 The heap-map parser reads the shared dump
- **From**: A.U20.33, A.U26.47 (read: parser unchanged), A.U8C.01/.71/.72/.73/.86, A.U8C2.30 (read: output formats
  unchanged), HW_DEV GAP-D10 (the dump lives in `_shared/map_dump.py`/`_shared/heap_probe.py`, M.HW_DEV.116/.120), A.U24.13
  (read).
- **Site**: `tests_scripts/test_heap_map_parser.py:1-20`, `:195-210`.
- **Change**: `from __future__` goes; the cases that read a device script's output format read the shared include's
  rendered form (the probe and dump text are in `_shared/`, per M.HW_DEV.116's statement of which source each check
  reads).
- **Resolved**: —
- **Unit**: U26 (U20 import).
- **Depends**: M.HW_DEV.003, M.HW_DEV.116.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_js_coverage_excludes_json.py
### M.TSC.167 Only `mockdata/` holds runtime JSON
- **From**: A.U6.04 (`:13` `_RUNTIME_JSON_DIRS` → `("mockdata",)`), A.U6.06 (read: `samples.json` stays), A.SDEP.19
  (conditional: if `@vitest/coverage-v8` stopped re-parsing JSON, the exclude and this test go), A.SDEP.04/A.U1.01/A.U28.26
  (read).
- **Site**: `tests_scripts/test_js_coverage_excludes_json.py:13`.
- **Change**: as listed; the whole file is deleted with `vitest.config.js`'s exclude if A.SDEP.19's re-check (W34) finds it
  fixed upstream.
- **Resolved**: —
- **Unit**: U6 (A.SDEP.19's branch at the U0/U37 refresh).
- **Depends**: A.U6.04 (WEB).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_js_coverage_report_dir.py
### M.TSC.168 Coverage report directory pin holds
- **From**: read: A.SDEP.04, A.U28.04, A.U28.16 (`:43-45` substrings hold), A.U28.26 (DONE-AT-HEAD), A.U7.20 (`htmlcov_js`
  unchanged).
- **Site**: `tests_scripts/test_js_coverage_report_dir.py`.
- **Change**: none.
- **Resolved**: —
- **Unit**: —
- **Depends**: —
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_live_twin_ceiling_parser.py
### M.TSC.169 The live-twin ceiling resolver reads the config object; no stray `rmSync`
- **From**: A.U5.04 (`:13, :50` read `ServingLimits`' `max_connections`), A.U24.53 (sibling text check: no `rmSync` of a
  path outside `os.tmpdir()` in the JS twin module — `tests_js/_twin_process.js`, WEB gap 7), A.U8.22 (`:24` timeout tag),
  read: A.U23.34, A.U24.52 (`node` is a hard prerequisite, asserted), A.U6.10 (device passed explicitly), A.U6.11,
  A.U7.21.
- **Site**: `tests_scripts/test_live_twin_ceiling_parser.py`.
- **Change**: as listed; `_NODE_TIMEOUT_S = 120  # @tunable l0.live_twin_ceiling_parser_timeout_s = 120`.
- **Resolved**: A.U24.53 names the command modules; the per-run removal moved into `_twin_process.js` (M.WEB.082) — the
  check reads that file.
- **Unit**: U24 (U5 reader; U8 tag).
- **Depends**: M.WEB.082.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_request_body_cap_headroom.py
### M.TSC.170 Body-cap headroom recomputed from definitions and the config object
- **From**: A.U5.05 (`:44-59` `const()`-aware read of `_DEFAULT_MAX_CONTENT_LENGTH`), A.U6.01 (`:104-105` →
  `definitions_for_toml()`), A.U10.41 (largest string field now `NTPHost` at 253, re-derived), A.U18.10 (the `/networking`
  bound includes `DNSFallback`), A.U6.26 (the DNS group), A.U23.47 (`Mapping[str, JsonValue]` at `:12, :62, :81`), A.U24.66,
  A.U24.73, read: A.U19.13, A.U8.04.
- **Site**: `tests_scripts/test_request_body_cap_headroom.py`.
- **Change**: as listed: the per-route PUT bound is recomputed from each device's generated definitions with the
  current schemas; typed with `JsonValue`; parametrised over `DEVICE_NAMES`.
- **Resolved**: —
- **Unit**: U23 (stages U5, U6, U10, U18, U24).
- **Depends**: M.SRC_NET (webserver defaults), M.GEN.018.
- **Blast carried by**: SPEC I.6 margin → A.U10.41 (SPEC).
- **Kind**: test

## tests_scripts/test_resolve_board_device.py
### M.TSC.171 The harness resolver keeps its seven cases
- **From**: A.U21.28 (U26's delegation keeps the seven cases), A.U24.66 (1 literal); M.HW_BENCH.018.
- **Site**: `tests_scripts/test_resolve_board_device.py`.
- **Change**: the seven cases run against `harness` delegating to `setup_toolchain.resolve_board_serial()`; the fixture
  device name is neutral.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.018.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_setup_cross_browser_toolchain_sh.py
### M.TSC.172 Cross-browser installer: Xvfb checked alone, verified downloads
- **From**: A.U28.21 (Xvfb's own check), A.U28.22 (verified Edge key and micromamba), A.SDEP.19 (read), A.U21.18 (read:
  different script), A.U28.01 (pattern reused), A.U6.11 (read: installer only).
- **Site**: `tests_scripts/test_setup_cross_browser_toolchain_sh.py`.
- **Change**: the stub `PATH` lacks `Xvfb`, so the Xvfb block reaches apt (`:59-63` holds); new: with a stub download
  whose fingerprint/SHA-256 differs the script exits non-zero naming the artifact; with `Xvfb` on the stub path no apt call
  is made for it; the closing summary prints the Xvfb path.
- **Resolved**: —
- **Unit**: U28
- **Depends**: M.SCR.073.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_tests_hardware_conftest_constants.py
### M.TSC.173 Hardware conftest constants: renamed schema, derived password
- **From**: A.U10.39 (`:62, :79` `_VAL_HOST` → `_VAL_HOSTNAME`), A.U26.07 (fixture name follows), A.U26.49 (`_DUT_HOTSPOT_PASSWORD`
  pinned by the helper/TOML/`_VAL_HOTSPOT_PW` triple, not a literal), A.U24.66, A.U7.13 (read).
- **Site**: `tests_scripts/test_tests_hardware_conftest_constants.py`.
- **Change**: as listed; the password test asserts the conftest value equals the bench TOML's `hotspot_password` read by
  the harness helper and passes `_VAL_HOTSPOT_PW`'s bounds.
- **Resolved**: —
- **Unit**: U26 (U10 name).
- **Depends**: M.HW_BENCH.007, M.HW_BENCH.044.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_ceiling_probe.py
### M.TSC.174 Ceiling-probe unit test holds
- **From**: read: A.U24.13 (`:15` insert unchanged), A.U36.532 (`:3` "H.7.1" still lands), A.U8.05 and A.U8.22 (`:33-215`
  test inputs, untagged).
- **Site**: `tests_scripts/test_ceiling_probe.py`.
- **Change**: none (the probe's typed signature follows M.HW_BENCH.017 by keyword names only, unchanged).
- **Resolved**: —
- **Unit**: —
- **Depends**: —
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/_devices.py
### M.TSC.175 The derived device set gains the property queries the tests share
- **From**: M.TSC.002 (A.U24.66's "selected from data" form), A.U26.01 (the bench device by `bench = true`); read (each
  imports `DEVICE_NAMES`/`device_toml` unchanged): A.U20.19, A.U24.11, A.U24.51, A.U24.65, A.U25.25, A.U25.48, A.U27.08,
  A.U28.06, A.U31.02, A.U35.08, A.U36.015, A.U36.016, A.U6.02, A.U6.05, A.U6.11, A.U7.24.
- **Site**: `tests_scripts/_devices.py`.
- **Change**: beside `DEVICE_NAMES`/`device_toml()`: `devices_with(driver: str) -> list[str]` (devices whose TOML declares
  an instance of `driver`, by `tomllib`) and `bench_device() -> str` (the one TOML with `[device] bench = true`; zero or
  two fail naming the files); docstring (≤ 3 lines) names `scripts/_devices.sh` as the shell statement of the same rule.
- **Resolved**: A.U24.66 asks for "the devices whose TOML declares the driver"; one helper serves every test instead of
  per-file parsing (agent decision D-TSC5).
- **Unit**: U24 (`bench_device()` with A.U26.01 in U26).
- **Depends**: A.U26.01 (GEN key).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/buildgen_fixtures/novel_combo.toml, multi_instance.toml, malformed_missing_device_table.toml
### M.TSC.176 Fixture TOMLs follow the schema changes
- **From**: A.U16.20/A.U16.17 (`novel_combo.toml:121`, `multi_instance.toml:98` → `max_size = 0x40000`), A.U10.43
  (`trigger_s`), A.U36.544 (`multi_instance.toml:1` "axis 9's own dedicated multi-instance fixture" → "the dedicated
  multi-instance fixture", `:12` "(axis 11 - legal, just unusual)" → "(legal, just unusual)"), A.U20.16 and A.U25.53 (read:
  the multi-instance fixture's SGP40s and twin boot), A.U20.20 (read: `bmp3xx` `Temp` reference builds), A.U6.01/A.U36.515
  (read), A.S0930.01 (read: `novel_combo.toml:142-153` holds), A.U6.14 (`malformed_missing_device_table.toml` header: "the
  buildgen generation step", not "fallback").
- **Site**: the three fixture TOMLs.
- **Change**: as listed; every non-singleton instance states `name_ext` (A.U20.19's rule).
- **Resolved**: —
- **Unit**: U16 (sizes); U10 (keys); U20 (`name_ext`); U36 (comments).
- **Depends**: —
- **Blast carried by**: —
- **Kind**: test

## New files other actions create (unlisted in CLUSTERS.md; each is a `tests_scripts/` L0 test)

## tests_scripts/test_archive_evidence.py
### M.TSC.177 The evidence archive keeps three runs per runner, touching nothing else
- **From**: A.U7.20; SCR gap 3 (`new_run_dir()`/`--new-dir`, per-runner keep; M.SCR.003).
- **Site**: new `tests_scripts/test_archive_evidence.py`.
- **Change**: with `root=tmp_path`: four successive `archive("x", paths)` keep the newest three, nothing outside
  `<root>/x` is touched, a missing path is skipped; `new_run_dir("x")` twice in one second yields `<ts>` and `<ts>-1`;
  the `--new-dir` CLI prints the created path; runner `y`'s runs are not pruned by runner `x`'s keep.
- **Resolved**: —
- **Unit**: U27 (stage U7).
- **Depends**: M.SCR.003.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_bench_control_restore.py
### M.TSC.178 Bench network restores are proven by state; the host access path is untouched
- **From**: A.U26.21 (L0 cases and (4)'s host-access guard); M.HW_BENCH.020/.022.
- **Site**: new `tests_scripts/test_bench_control_restore.py`.
- **Change**: `subprocess.run` stubbed: `-D` fails and the listing shows no rule → no raise; `-D` fails and the listing
  still shows the rule → raises naming it; the listing command fails → raises naming sudo/the tool; `clear_leftovers()`
  removes only this project's tagged rules/qdiscs and reports them; AST guard: no `tests_hardware/` module passes
  `BENCH_BRIDGE_CONN`/`BENCH_ETH_CONN` (or their literal names) to `_nmcli`.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.020, M.HW_BENCH.022.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_bench_device.py
### M.TSC.179 Exactly one TOML names the bench board
- **From**: A.U26.01.
- **Site**: new `tests_scripts/test_bench_device.py`.
- **Change**: exactly one derived TOML sets `bench = true` (no device name in the test); `bench_device()` over a tmp
  `devices/` with zero or two flagged TOMLs raises naming the files; `--bench-device` of a missing TOML is a usage error;
  `_check_device_table()` refuses `bench = 1`.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.GEN.052, M.HW_BENCH.010, M.TSC.175.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_board_image_fixture.py
### M.TSC.180 The bench tier proves the board runs this round's image
- **From**: A.U26.03; M.HW_BENCH.060.
- **Site**: new `tests_scripts/test_board_image_fixture.py`.
- **Change**: the fixture function with a fake `http_client.fetch` and a tmp image record: equal build dates pass; a
  different date, a different device, a non-empty ensemble finding, a missing record each exit with the named cause.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.060, M.SCR.067 (record).
- **Blast carried by**: collect-only behaviour → M.TSC.137.
- **Kind**: test

## tests_scripts/test_build_device_websites_sh.py
### M.TSC.181 Every device's site builds from generated definitions
- **From**: A.U6.03; M.SCR.020.
- **Site**: new `tests_scripts/test_build_device_websites_sh.py`.
- **Change**: with `out_root = tmp_path`, every `DEVICE_NAMES` device gets `<tmp_path>/<d>/frozen_html.py` containing
  `/index.html.gz` whose inlined definitions carry `"id": "<d>"`; `--stage-only <tmp>` writes each device's staged
  `index.html` and no archive; an unknown device exits 2 listing valid ones.
- **Resolved**: —
- **Unit**: U27 (stage U6).
- **Depends**: M.SCR.020, M.SCR.071.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_buildgen_error_contract.py
### M.TSC.182 Every build-error rule proven through the CLI
- **From**: A.U20.17 (5); rows added by A.U20.01 (`bus.uart-shared`), A.U20.19 (`instance.name-ext-missing`), A.U20.24
  (`tag.non-finite-number`), A.U20.34 (range rules), A.U31.08 (`bus.i2c-timeout-max`), A.U17.21/A.U17.32, A.S0930.01 (CRC
  rules), A.U20.28 (`twin.no-address-rule`); M.GEN.022.
- **Site**: new `tests_scripts/test_buildgen_error_contract.py`.
- **Change**: a table with one malformed-fixture row per `rule` id (built on `base_doc()`), each run through
  `generate.main([path])` in-process with `capsys`: return 1, stderr starts `buildgen: [<device>`, contains the row's
  expected place and `- fix: `, no `Traceback`; an AST scan of `buildgen/*.py` collects every `rule=` literal and the
  table's ids must equal that set; rows for the bus-less device (generates), `wiring = "fram"`, `[device] wiring = 1`, the
  twin rule on a synthetic driver, an unwritable `--out-dir` (a file in its place).
- **Resolved**: —
- **Unit**: U31 (stage U20; each later rule's row lands with its rule).
- **Depends**: M.GEN.022, M.TSC.012.
- **Blast carried by**: SPEC L.5 → A.U20.17 (SPEC).
- **Kind**: test

## tests_scripts/test_ci_web_filter_covers_definitions_sources.py
### M.TSC.183 Not created: the web-filter check is part of the workflow test
- **From**: A.U6.12 (planned file), A.U28.07 (it "folds into A.U28.08's file").
- **Site**: — (never created).
- **Change**: none; the check is M.TSC.062 rule (2).
- **Resolved**: A.U28.07 states the fold.
- **Unit**: —
- **Depends**: M.TSC.062.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_cross_browser_smoke_probe.py
### M.TSC.184 The smoke's probe field and engine verdict, without browsers
- **From**: A.U6.11, A.U28.17; M.SCR.023.
- **Site**: new `tests_scripts/test_cross_browser_smoke_probe.py`.
- **Change**: `node -e` importing `scripts/_cross_browser_probe.mjs`: `pickProbe()` yields an in-range int field for every
  device's generated definitions; a definitions file with no candidate throws naming the device; `engineVerdict()` with
  `requireAllEngines` and a missing WebKit yields FAIL with the binary path and the setup hint, without it SKIP.
- **Resolved**: —
- **Unit**: U28 (stage U6).
- **Depends**: M.SCR.023.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_device_script_bench_facts.py
### M.TSC.185 Device scripts take board facts from `BENCH` only
- **From**: A.U26.44 (4); HW_DEV GAP-D1 (`.pyi` keys = `bench_facts.build()` keys + declared extras, M.HW_DEV.001), GAP-D14
  (conformance probes' register maps exempt, M.HW_DEV.132/.144); A.U26.46 (the README bench-facts table has no row without
  a date and a source; placed here, beside the facts it records).
- **Site**: new `tests_scripts/test_device_script_bench_facts.py`.
- **Change**: AST over every device script: no numeric pin/bus argument literal in an `I2C(`/`SPI(`/`UART(`/`Pin(`/
  `NeopixelDriver(`/`NeoPixel(` call, no `import sensortask_`, no copy of a driver's `_…_ADDR`/register constant bound to
  a name — except the register maps of `*_conformance_probe.py` (datasheet values with pages; their addresses, pins and
  mode values still come from `BENCH`); every `BENCH[...]` key a script reads exists in `bench_facts.build()` for every
  `bench = true` TOML (rendered for every derived device, builds without error) or is a declared render extra;
  `bench_facts.pyi`'s `BenchFacts` keys equal `build()`'s keys plus the declared extras; `tests_hardware/README.md`'s
  "Bench facts" table has a date and a source on every filled row.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_DEV.001, M.HW_BENCH.041, M.HW_BENCH.120.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_device_script_facts.py
### M.TSC.186 Device scripts report facts; the host gives the verdict; loops yield
- **From**: A.U26.68 (no `print("RESULT:` in `device_scripts/`; every host test running a script calls `parse_facts`;
  `parse_facts()` cases), HW_DEV GAP-D11 (runners of `run_isolated_expect_reset()` exempt from the `DONE` rule; AD-3),
  A.U26.69 (every `while`/`for` in an `async def` of a device script awaits on every looping branch); file placement:
  agent decision D-TSC6.
- **Site**: new `tests_scripts/test_device_script_facts.py`.
- **Change**: AST/text: no `print("RESULT:` in `tests_hardware/device_scripts/`; every host test that runs a script calls
  `harness.parse_facts(...)`, except runners of `run_isolated_expect_reset()`, which call
  `parse_facts(output, allow_missing_done=True)`; `parse_facts()` cases: `FACT k=<json>` lines parsed, a missing `DONE`
  fails with the output, `allow_missing_done=True` accepts it, a malformed JSON value fails naming the key; every loop in
  an `async def` of a device script has an `await` on each branch that continues or loops back; bites for each rule.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_DEV.002, M.HW_BENCH.012.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_hardware_clones.py
### M.TSC.187 No new clone group in the hardware levels
- **From**: A.U26.78 (3) (file unnamed; placement D-TSC6).
- **Site**: new `tests_scripts/test_hardware_clones.py`.
- **Change**: identical function bodies by normalised `ast` dump across `tests_hardware/` (the `_shared/` include files
  excluded) — a clone group of two or more non-trivial functions fails naming them.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_DEV.003.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_tests_hardware_product_copies.py
### M.TSC.188 Product values the hardware levels copy are read or cited
- **From**: A.U26.49 (4) (file unnamed; placement D-TSC6).
- **Site**: new `tests_scripts/test_tests_hardware_product_copies.py`.
- **Change**: over `tests_hardware/`: any numeric literal equal to a `src/` `_VAL_*` bound or a known product constant,
  bound to an upper-case name without a `# source:` comment, fails naming file:line and the product name.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH (the copies fixed or cited at execution).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_devices_sh.py
### M.TSC.189 The shell device list equals the Python one
- **From**: A.U27.08; M.SCR.007.
- **Site**: new `tests_scripts/test_devices_sh.py`.
- **Change**: `derived_devices` over the real `devices/` equals `_devices.DEVICE_NAMES`; over a tmp `devices/` with a
  `zz_test_x.toml` it omits it; `require_device` of an unknown or `zz_test_` name exits 2 listing the valid devices; an
  empty `devices/` fails with "no devices/*.toml found".
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.SCR.007.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_digital_twin_ci_suite_matrix.py
### M.TSC.190 Every fake fault op is in the fault matrix or named left out
- **From**: A.U25.37.
- **Site**: new `tests_scripts/test_digital_twin_ci_suite_matrix.py`.
- **Change**: every `maybe_hang`/`maybe_raise` op of `digital_twin/_*_chip.py` (AST) is in the suite's fault matrix or in
  `_LEFT_OUT` with its reason; the matrix names only existing ops; `uart_link:silent` appears per instance for devices
  wiring the pair; the suite's `--device-toml PATH` option parses (A.S0930.04 (4)).
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.SCR.051, M.SCR.046.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_digital_twin_ci_suite_state.py
### M.TSC.191 Suite state archived, never deleted; the capability helper
- **From**: A.U25.35 (`_archive_state()`), A.U25.34 (the capability helper with a fake xattr).
- **Site**: new `tests_scripts/test_digital_twin_ci_suite_state.py`.
- **Change**: `_archive_state()` on a tmp logs dir moves files, never deletes, numbers archives, recreates the state dir;
  the port-53 capability helper reports granted/absent from a fake xattr reader.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.SCR.047.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_digital_twin_scenarios.py
### M.TSC.192 The host scenario harness: registry, selection, record
- **From**: A.U25.46 (pure helpers); SCR gap 3 (`--shared-port-53` deselection reported; a device lacking a scenario's
  driver skipped by name; `--run-record` written); M.SCR.017/.018.
- **Site**: new `tests_scripts/test_digital_twin_scenarios.py`.
- **Change**: every registered scenario has a goal docstring line and a known device filter; `--only` with an unknown name
  exits 2; no scenario module imports from `tests/`; `--shared-port-53` lists the exclusive-port-53 scenarios as deselected
  with that reason; a device without a scenario's driver reports the scenario skipped by name; `--run-record <tmp>` writes
  the record with each scenario's outcome.
- **Resolved**: —
- **Unit**: U27 (stage U25).
- **Depends**: M.SCR.017, M.SCR.018.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_driver_shape.py
### M.TSC.193 Sensor driver modules keep one shape
- **From**: A.U15.40.
- **Site**: new `tests_scripts/test_driver_shape.py`.
- **Change**: AST over every `src/asy_*_driver.py` defining a `SensorReader`/`SensorReaderConfig` subclass: a module-level
  `_NAME = const("<NAME>")`; every `namedtuple("<T>", …)` bound to `<T>`; no `_NAME` in a REST-key position (the key is
  `self.name`); module order constants → `_VAL_*` → derived `_N_*` counts → tags/namedtuple → `_Default*`/`_ConstValue`
  helpers → `*_Reader` → `*_I2C`/`*_SPI`.
- **Resolved**: —
- **Unit**: U15
- **Depends**: SRC_SENS driver edits.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_evidence_snapshot.py
### M.TSC.194 Evidence is saved before anything clears it
- **From**: A.U26.22 (L0), HW_BENCH GAP-B2 (REST save before any raw-REPL call when `--dut-ip` answers; M.HW_BENCH.006).
- **Site**: new `tests_scripts/test_evidence_snapshot.py`.
- **Change**: `reset_all_error_logs(dut_ip, reason)` with a stubbed `fetch` issues the GET and writes the file before the
  PUT (call order recorded); `evidence_dir()` honours `$EVIDENCE_DIR`; `fram_raw_dump.py` contains no
  `set_values`/`get_chunk`/`write` call (`ast`); a session start with `--dut-ip` answering saves `/status` over REST before
  the first raw-REPL call (order recorded on fakes).
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.006, M.HW_BENCH.050, M.HW_BENCH.055, M.HW_DEV.150.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_generated_tree.py
### M.TSC.195 A stale generated tree is refused
- **From**: A.U24.46.
- **Site**: new `tests_scripts/test_generated_tree.py`.
- **Change**: on a tmp tree, touching a TOML after generation makes `require_fresh()` (run under the Unix-port binary)
  raise; regenerating clears it; the stamp path equals `scripts/_generate_sensortask_modules.py`'s (M.SCR.068).
- **Resolved**: —
- **Unit**: U24
- **Depends**: A.U24.46 (`tests/_generated_tree.py`, TEST_HELP), M.SCR.068.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_hardware_runners.py
### M.TSC.196 Hardware runners run every lower level first
- **From**: A.U7.18; M.SCR.006, M.SCR.030-.032; M.SCR.074 (the rollover runner; GAPS_G4 hand-off 3 (a), gap pass G3).
- **Site**: new `tests_scripts/test_hardware_runners.py`.
- **Change**: with stubbed `scripts/test.sh`, `npm`, `run_digital_twin_ci.sh`, `uv`: a failing L1 stops before any
  pytest-on-hardware call; the device loop is derived from `devices/*.toml` minus `zz_test_*`; `--skip-lower-levels`
  yields NOT CLEAN; the bench runner runs flash then bench as two steps; the soak runner's block says `Levels: soak
  duration <d> (not a level)`; `scripts/run_bench_rollover_test.sh` makes no lower-level call (no stubbed `test.sh`,
  `npm` or twin-suite invocation recorded) and its block reads `Levels: rollover (not a level)`.
- **Resolved**: —
- **Unit**: U27 (stage U7).
- **Depends**: M.SCR.006, M.SCR.030, M.SCR.031, M.SCR.032, M.SCR.074.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_hardware_verdict.py
### M.TSC.197 The hardware verdict from the run record
- **From**: A.U7.14; M.SCR.005; A.U26.56 (the permanent-skip set follows its outcome).
- **Site**: new `tests_scripts/test_hardware_verdict.py`.
- **Change**: canned run records: nonzero pytest exit → FAIL propagated; `-q` by the caller still judged; a module-level
  skip fails; a gate-marker skip with its option unset is accepted, with the option set fails; `--soak-duration=short` and
  `--soak-duration short` read alike; a substring-named test no longer masks another; `-m` exclusions reported as runner
  selection with no `--allow-*` advice; wear-gate deselections listed with their flag; a recovery pass counted apart; zero
  passed → FAIL; `--collect-only` → "NOT A RUN"; the E.10 block printed. The permanent-skip set is empty once the spoofed
  off-subnet test runs (M.HW_BENCH.045); if A.U26.56's attempt restores the skip, its exact nodeid with its recorded reason.
- **Resolved**: —
- **Unit**: U27 (stage U7).
- **Depends**: M.SCR.005, M.SCR.004.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_harness_mpremote_retry.py
### M.TSC.198 A transient mpremote retry never re-runs a script
- **From**: A.U26.13, A.U26.37 (refused USB rebind), HW_BENCH GAP-B3 (bounded settle polls replace the two fixed
  sleeps; M.HW_BENCH.011), A.U26.75 (the argv carries `--no-sync`).
- **Site**: new `tests_scripts/test_harness_mpremote_retry.py`.
- **Change**: a stubbed `subprocess.run`: a transient failure with empty stdout → retried once, the event recorded; a
  transient failure with script output → not retried, returned; a soft-reset failure after a good run → raises naming it;
  a refused unbind → `HardwareNotAvailableError` naming the README prerequisite and one event; the settle polls end when
  the port reappears and give up at their bound (no fixed sleep); every `uv run` argv holds `--no-sync`.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.011.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_host_annotations.py
### M.TSC.199 No host file carries `from __future__ import annotations`
- **From**: A.U20.33.
- **Site**: new `tests_scripts/test_host_annotations.py`.
- **Change**: an AST scan of `buildgen/`, `scripts/`, `toolchain/`, `tests_scripts/` and `tests_hardware/` host code
  (`device_scripts/` excluded) fails on the import; every name used only under `TYPE_CHECKING` appears quoted in
  annotations evaluated at runtime.
- **Resolved**: —
- **Unit**: U20
- **Depends**: M.TSC.003.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_isl29125_copies.py
### M.TSC.200 ISL29125 constant copies agree
- **From**: A.U25.49.
- **Site**: new `tests_scripts/test_isl29125_copies.py`.
- **Change**: AST-reads the driver's `const()` values (`_REGISTER_*`, `_MODE_RGB`, `_CONFIG1_RNG`, `_CONFIG1_BITS`,
  `_INTSEL_GREEN`, `_STATUS_*`, `_DEVICE_ID`, `_RANGE_LOW_LUX`, `_RANGE_HIGH_LUX`, `_GAIN_RATIO_NOMINAL`, `_VAL_AR_THRESH`'s
  default), the twin chip's constants and the two test files' copies; any disagreement fails.
- **Resolved**: —
- **Unit**: U25
- **Depends**: M.TWIN (chip), SRC_SENS names.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_js_generated_definitions_loader.py
### M.TSC.201 The JS loader reads where the generator writes
- **From**: A.U6.05.
- **Site**: new `tests_scripts/test_js_generated_definitions_loader.py`.
- **Change**: the helper's glob path (`tests_js/_generated_definitions.js`) equals `scripts/_generate_sensortask_modules.py`'s
  definitions output dir, and its stamp path equals `build/generated_src/definitions/inputs_stamp.json` (M.SCR.068).
- **Resolved**: —
- **Unit**: U6 (stamp with U27).
- **Depends**: M.SCR.068, M.WEB.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_live_command_device_args.py
### M.TSC.202 Live JS commands take the device they are given
- **From**: A.U6.10; WEB gap 7 (the launch lives in `tests_js/_twin_process.js`).
- **Site**: new `tests_scripts/test_live_command_device_args.py`.
- **Change**: text checks: every exported live command in `tests_js/_live_twin_command.js`/`_live_matrix_command.js`
  takes a `device` argument and passes it to `_twin_process.js`'s launch; `_twin_process.js` has no default device and
  builds `MICROPYPATH` from the twin layout with `build/generated_html/<device>` in place of `frozen_modules`.
- **Resolved**: —
- **Unit**: U23 (stage U6).
- **Depends**: M.WEB.082, SCR gap 1(a).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_manual_runner_summary.py
### M.TSC.203 The manual runner can fail and ends with the block
- **From**: A.U7.17, A.U26.42; M.HW_BENCH.100.
- **Site**: new `tests_scripts/test_manual_runner_summary.py`.
- **Change**: a scripted run with one pass and one fail prints the block and exits 1; a test returning with no judgment
  is FAIL; a stubbed `input` raising `KeyboardInterrupt` prints the block and exits 130; per-test level from its tier
  (`[USB]` → L3, `[USB+WiFi]` → L4).
- **Resolved**: —
- **Unit**: U26 (stage U7).
- **Depends**: M.HW_BENCH.100, M.SCR.033.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_mpremote_connect_sh.py
### M.TSC.204 `mpremote_connect.sh` resolves the board through the installer
- **From**: A.U27.13.
- **Site**: new `tests_scripts/test_mpremote_connect_sh.py`.
- **Change**: with a stub `uv` on `PATH`: `MPREMOTE_DEVICE` set → `mpremote connect <it>` and no `board` call; unset → the
  stub's `board` output used; a failing `board` → exit 1, no `mpremote` call.
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.SCR.029.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_port_bands.py
### M.TSC.205 Test port bands are disjoint and derived
- **From**: A.U24.70.
- **Site**: new `tests_scripts/test_port_bands.py`.
- **Change**: the port table's rows are disjoint and below 32768; every `tests/*.py` binding a socket draws from
  `PortAllocator` or a fixed row naming it; the per-device blocks cover `DEVICE_NAMES` without overlap.
- **Resolved**: —
- **Unit**: U24
- **Depends**: A.U24.70 (TEST_HELP).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_port_lock.py
### M.TSC.206 One lock per product-fixed port, inherited by children
- **From**: A.U24.69, A.U27.39; SCR gap 3 (inherited-owner cases, M.SCR.012/.013); GAPS_G2 H-4 (c) (the JS lock of
  M.WEB.078 keeps the same contract; gap pass G3).
- **Site**: new `tests_scripts/test_port_lock.py`.
- **Change**: two shells taking the same lock: the second exits 1 naming the port and the holder; a lock left by a dead
  PID is taken over; the lock dir is gone after the holder exits (normally and on `kill -TERM`); a child of the holder (the
  inherited `SENSORS_PORT_LOCK_OWNER`/`SENSORS_PORT_LOCKS_HELD`) is accepted, an unrelated holder refused; release
  removes only own locks; the CPython reader (M.SCR.013) honours the same contract; `tests_js/_port_lock.js` (driven
  through `node -e`) honours it too: a second acquisition in the same process is re-entrant, a child of a shell holder
  (inherited variables) is accepted, an unrelated holder refused (M.WEB.078); a held 53 lock makes
  `run_unix_port_integration.sh --device <derived>` exit 1.
- **Resolved**: —
- **Unit**: U27 (stage U24).
- **Depends**: M.SCR.012, M.SCR.013, M.WEB.078.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_preview_server.py
### M.TSC.207 `npm run preview` serves only the site, on localhost
- **From**: A.U28.24; M.SCR.021.
- **Site**: new `tests_scripts/test_preview_server.py`.
- **Change**: server on port 0 in a thread: `/html/index.html` 200, `/js/app.js` 200, `/.git/HEAD`, `/config_WIFI.cfg`,
  `/html/../pyproject.toml` 404; bound to `127.0.0.1`; an already-bound port → exit 1 naming `--port`.
- **Resolved**: —
- **Unit**: U28
- **Depends**: M.SCR.021.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_pytest_run_record.py
### M.TSC.208 The pytest plugin writes one complete run record
- **From**: A.U7.08; M.SCR.004.
- **Site**: new `tests_scripts/test_pytest_run_record.py`.
- **Change**: a subprocess run over a tmp suite with one pass, one skip, one module-level skip, one `-m`-deselected and one
  `deselected_by` item produces the expected record (outcomes, reasons, deselection kinds).
- **Resolved**: —
- **Unit**: U7
- **Depends**: M.SCR.004.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_require_python.py
### M.TSC.209 Every bare `python3` is version-checked first
- **From**: A.U27.10; M.SCR.010.
- **Site**: new `tests_scripts/test_require_python.py`.
- **Change**: a stub `python3` on `PATH` reporting 3.10 makes `build_frozen_html.sh` exit 1 with the message before
  touching the output.
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.SCR.010.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_require_venv_sh.py
### M.TSC.210 Lint and typecheck refuse an inactive or stale venv
- **From**: A.U27.26; M.SCR.011.
- **Site**: new `tests_scripts/test_require_venv_sh.py`.
- **Change**: `VIRTUAL_ENV` unset → exit 1 naming activation; a stub `uv` whose `sync --check` fails → exit 1 naming
  `uv sync`; a stub `ruff` earlier on `PATH` than `.venv/bin` → exit 1 naming it.
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.SCR.011.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_run_digital_twin_ci_sh.py
### M.TSC.211 The twin CI runner: archive per device, harness at both stages, CRC16 rerun
- **From**: A.U27.16; SCR gap 3 (per-device archive runner name; the CRC16 rerun only for a `uart_link` device and its
  line-count check; the harness at both stages; the worst exit; M.SCR.061).
- **Site**: new `tests_scripts/test_run_digital_twin_ci_sh.py`.
- **Change**: with stubbed `uv`, `setcap`, `build_website.sh` and suite: an existing `digital_twin_ci_logs/<d>` moves under
  `build/archive/digital_twin_ci_<d>/` (the per-device runner name), a fourth run keeps three, nothing else is touched;
  extra args reach the suite; the suite and the harness each run at `-1` and `32768`; the CRC16 rerun of Run 3's link cell
  runs only for a device wiring a `uart_link` pair and its log is checked for the expected cell lines; the exit is the worst
  of the runs; a missing device argument exits 2.
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.SCR.061.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_scd30_prerequisite.py
### M.TSC.212 The SCD30 prerequisite starts measurement at most once
- **From**: A.U26.07; M.HW_BENCH.044 (OR92.a).
- **Site**: new `tests_scripts/test_scd30_prerequisite.py`.
- **Change**: a fake board: already measuring → no send; not measuring → exactly one start send per session; each failure
  mode (read error, start refused, still not measuring) raises naming it after at most one send.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.044, M.HW_DEV.020.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_shell_conventions.py
### M.TSC.213 Every shell script follows the one convention
- **From**: A.U27.33 (4); A.U24.68 (L0: no argument at all exits 2 naming the valid devices; M.SCR.062's blast, gap pass
  G3).
- **Site**: new `tests_scripts/test_shell_conventions.py`.
- **Change**: every `scripts/*.sh` starts `#!/usr/bin/env bash` + `set -euo pipefail`, quotes expansions per the
  convention, handles `-h|--help` (exit 0) and rejects unknown arguments (exit 2); `run_unix_port_integration.sh` with no
  argument exits 2 listing the valid devices (A.U24.68), `--device` with no value exits 2 naming the flag, and an unknown
  device exits 2 listing the valid ones.
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.SCR (each script's convention change).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_stage_website.py
### M.TSC.214 The stager derives the bundle and refuses every drift
- **From**: A.U23.38, A.U23.39; M.SCR.019.
- **Site**: new `tests_scripts/test_stage_website.py`.
- **Change**: temp trees proving each refusal (multi-line import, default export, re-export, dynamic import, cycle,
  duplicate export, a stray file under `html/`, an unreferenced module), each exiting nonzero with what/where/fix and no
  traceback; the derived module list equals `js/main.js`'s import closure; the staged `<link rel="icon">` carries a
  `data:image/x-icon;base64,` URI decoding to `html/favicon.ico`; a missing tag fails naming `html/index.html`; the
  stager writes only inside `<stage_dir>`.
- **Resolved**: —
- **Unit**: U23
- **Depends**: M.SCR.019.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_summary_block.py
### M.TSC.215 One E.10 block, three emitters, byte-identical
- **From**: A.U7.02, A.U7.10; M.SCR.001/.002.
- **Site**: new `tests_scripts/test_summary_block.py`.
- **Change**: the bash and Python emitters, and `node tests_js/_summary_layout.js`, render the same canned input
  byte-identically; a missing verdict counts failed; vacuous > 0 forces FAIL; the `Exit code:` line equals the given code;
  a usage error exits 2 (OR133).
- **Resolved**: —
- **Unit**: U7
- **Depends**: M.SCR.001, M.SCR.002, A.U7.10 (WEB layout).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_tests_hardware_run_record.py
### M.TSC.216 Collecting the hardware levels yields a run record with the gate flags
- **From**: A.U7.13; M.HW_BENCH.003/.004.
- **Site**: new `tests_scripts/test_tests_hardware_run_record.py`.
- **Change**: collecting `tests_hardware` with nothing attached yields a record whose wear-gate deselections carry their
  flag and whose `-m` exclusions read "runner selection"; a stub test calling `result_note(..., recovery=True)` lands in
  the record.
- **Resolved**: —
- **Unit**: U26 (stage U7).
- **Depends**: M.HW_BENCH.003, M.HW_BENCH.004, M.SCR.004.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_tool_help.py
### M.TSC.217 Every user-facing tool answers `--help` and touches nothing
- **From**: A.U7.19; M.SCR.074 (`TOOLS` gains the rollover runner; GAPS_G4 hand-off 3 (c), gap pass G3).
- **Site**: new `tests_scripts/test_tool_help.py`.
- **Change**: a module-level `TOOLS` list (every runner and user-facing tool, `scripts/run_bench_rollover_test.sh`
  among them) shared with `test_readme_reference.py`;
  each `--help` exits 0, prints "Usage:", and leaves the tree listing unchanged.
- **Resolved**: —
- **Unit**: U7
- **Depends**: M.SCR (help in each tool).
- **Blast carried by**: README comparison → M.TSC.113.
- **Kind**: test

## tests_scripts/test_twin_board.py
### M.TSC.218 `TwinBoard` keeps `Board`'s shape
- **From**: A.U26.05; M.HW_BENCH.091.
- **Site**: new `tests_scripts/test_twin_board.py`.
- **Change**: `TwinBoard`'s public methods and their parameter names equal `Board`'s (`ast`); a one-line script run through
  it returns the script's output; its `MICROPYPATH` is the file's `twin` value (M.TSC.150 covers the launch guard).
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.091, M.TWIN.054.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_twin_record.py
### M.TSC.219 Every hardware instrument has a current twin-run record
- **From**: A.U26.05; M.HW_BENCH.092, M.SCR.022.
- **Site**: new `tests_scripts/test_twin_record.py`.
- **Change**: every `device_scripts/*.py`, `flash/test_*.py`, `bench/test_*.py` has a record entry; each entry's three
  hashes equal the current files'; every `exception` has a non-empty reason; no entry names a deleted file.
- **Resolved**: —
- **Unit**: U26
- **Depends**: M.HW_BENCH.092, M.SCR.022.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_twin_runner_test_flags.py
### M.TSC.220 Test-only runner flags stay off and out of the product path
- **From**: A.U25.74, A.U31.06 (its flag joins the table); TWIN gap (`--test-fault-status-interval-ms`, M.TWIN.051).
- **Site**: new `tests_scripts/test_twin_runner_test_flags.py`.
- **Change**: every `--test-` flag's argparse default is off (the table includes `--test-fault-status-interval-ms` and
  A.U31.06's flag); every rebind or instrumentation call in the runner is reached only under its flag's `if` (`ast`); no
  `--test-` name, no runner module and no `digital_twin/` import appears in `src/`, any generated module or the frozen
  module set; a bite fixture (a flag defaulting on) fails.
- **Resolved**: —
- **Unit**: U31 (stage U25).
- **Depends**: M.TWIN.051.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_typecheck_sh.py
### M.TSC.221 `typecheck.sh`: exact stub pins, repairs that fail on a moved tree, summary
- **From**: A.U21.04 (stub install block), A.U27.02 (pin check and repairs), A.U7.12 (summary block), A.SDEP.15 (the
  fabricated trees keep all three states); M.SCR.026, M.SCR.027.
- **Site**: new `tests_scripts/test_typecheck_sh.py`.
- **Change**: the stub block (between its marker comments) run with a fake `uv`: a spec change wipes a planted stale file,
  an unchanged spec keeps it, two dist-info dirs → exit 1 with the message; the pin check against a tmp `versions.toml`:
  mismatched X.Y.Z → exit 1 naming the key, matching → prints both; the repair block on fabricated trees: defect present →
  repaired, fixed tree → untouched, missing `asyncio/` or `builtins.pyi` → exit 1 naming the path, `_asyncio.pyi` without
  `class _Future` → exit 1; stub `mypy`/`uv`/`python3`: one failing twin pass → `failed 1` naming
  `digital_twin/typecheck.ini`, exit 1; a failing stub install → the block names "stub install", exit 1.
- **Resolved**: A.U21.04, A.U27.02 and A.U7.12 each create this file — one file.
- **Unit**: U27 (stages U7, U21).
- **Depends**: M.SCR.026, M.SCR.027.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_unix_port_sh.py
### M.TSC.222 One Unix-port probe by build flavour
- **From**: A.U27.12; M.SCR.008.
- **Site**: new `tests_scripts/test_unix_port_sh.py`.
- **Change**: `check` on a stub binary printing each flavour (`standard`, `settrace`, `lwip`), on a missing path and on a
  binary without asyncio (`unusable`); `ensure` with a stub `uv` records one `setup` call on mismatch and exits 1 if the
  flavour is still wrong; `unix_port_bin <flavour>` prints the path under `$PICO_TOOLCHAIN_DIR`; the toolchain-record
  condition (A.U21.22) joins the rebuild decision.
- **Resolved**: —
- **Unit**: U27
- **Depends**: M.SCR.008.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_uv_sync_retried_sh.py
### M.TSC.223 One retried `uv sync --locked`
- **From**: A.U28.01; TOOL gap 2 (attempts and backoff compared with `setup_toolchain.NETWORK_ATTEMPTS` and
  `run_retried()`'s `backoff_s`, M.TOOL.046); M.SCR.014.
- **Site**: new `tests_scripts/test_uv_sync_retried_sh.py`.
- **Change**: with stub `uv` and `sleep` as the whole `PATH`: `uv` failing twice then passing → exit 0, three calls each
  `sync --locked`, sleeps `10` then `20`; failing three times → exit 1 naming the attempts; the script's tagged attempt
  count and backoff step equal `setup_toolchain.NETWORK_ATTEMPTS` and `run_retried()`'s `backoff_s` default.
- **Resolved**: —
- **Unit**: U28
- **Depends**: M.SCR.014, M.TOOL.046.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_website_tokens.py
### M.TSC.224 Website colour tokens meet the contrast table in both themes
- **From**: A.U23.44, A.U36.510 (read: SPEC names it); GEN Q2 → (a), OR132 (AC_NOTES 41): light-theme AA tokens applied
  (M.GEN.062) — firm.
- **Site**: new `tests_scripts/test_website_tokens.py`.
- **Change**: parses both token blocks of `html/style.css` and asserts the ratio table (text 4.5 on every background it
  sits on, status colours 4.5 on their bg tokens and on surface, control borders 3.0), `color-scheme: light dark`, and the
  reduced-motion rule of A.U23.43.
- **Resolved**: GEN Q2 answered (a) (OR132).
- **Unit**: U23
- **Depends**: M.GEN.062.
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_doc_refs.py
### M.TSC.225 Not created: no action defines it
- **From**: A.S0930.08 (names `tests_scripts/test_doc_refs*` conditionally: "if the J.6 wording is pinned" — grep finds none).
- **Site**: —
- **Change**: none; the citation check (M.TSC.063) covers document references.
- **Resolved**: —
- **Unit**: —
- **Depends**: —
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_bench_harness_helpers.py (gap pass G3)

### M.TSC.226 The bench's route set is the REST reference's, `/notification` included
- **From**: A.U26.80 (new L0: `get_routes()` returns every GET route of the table, `/notification` included);
  M.HW_BENCH.010's blast "→ A.U26.80 (TSC)", carried by no TSC change (gap pass G3).
- **Site**: `tests_scripts/test_bench_harness_helpers.py`, new cases.
- **Change**: for every `DEVICE_NAMES` device, `harness.get_routes()` equals the GET paths with a JSON body listed in
  that device's generated REST reference (`build/generated_src/api/<device>.json`, A.U19.20), read by the test's own
  JSON load, and contains `/notification`; `json_only=False` adds the non-JSON GET routes; `streams=True` returns
  exactly the reference's streaming routes; a stub reference with one extra GET route (a `tmp_path` copy, the helper
  pointed at it) shows that route — no literal route list in the test.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.010 (`get_routes()`), A.U19.20 (the reference; GEN/SRC_NET).
- **Blast carried by**: —
- **Kind**: test

## tests_scripts/test_result_words.py (new; gap pass G3)

### M.TSC.227 The four result words are spelled once, in the config manager
- **From**: A.U19.16 (new L0: an AST scan of `src/` and the generated modules fails on a string literal equal to one of
  the four result words outside the config manager's definitions); M.SRC_CORE.045's blast "→ A.U19.16 (TSC)", carried by
  no TSC change (gap pass G3).
- **Site**: new `tests_scripts/test_result_words.py`.
- **Change**: docstring (≤ 3 lines) "Every per-field result word comes from asy_config_manager's VALID/UNCHANGED/INVALID/
  FAILED (SPECIFICATION.md G.2): a second spelling of one drifts from the wire contract unseen." The scan walks
  `src/*.py` and every `build/generated_src/sensortask_<device>.py` (generated into `tmp_path` per `DEVICE_NAMES`, as
  the other generated-module checks do); an `ast.Constant` whose value is `"Valid"`, `"Unchanged"`, `"Invalid"` or
  `"Failed"` fails naming `file:line`, except the four assignments in `src/asy_config_manager.py` and the members of
  its `WriteValidity` `Literal[…]`; docstrings are skipped (comments never reach the AST). Bite: a `tmp_path` copy of
  `src/` with one `"Valid"` planted in a setter fails naming it. `tests/` keeps its literals (they state the wire
  contract, A.U19.16).
- **Resolved**: —
- **Unit**: U19.
- **Depends**: M.SRC_CORE.045 (the constants); A.U19.16's SRC_NET/SRC_SENS literal sites.
- **Blast carried by**: the JS mirror's L0 check → M.TSC.100 (A.U23.25).
- **Kind**: test

## Gaps for other clusters

1. **SRC_SENS** — `NeopixelDriver` carries no `initialized` gate in any merged change (M.SRC_SENS.023/.024; TEST_UNIT
   GAP-U3 says the same). M.TSC.112's readiness check needs it under AC_NOTES 38: `self.initialized = False` in
   `__init__`, `True` once `setup()`'s logger setup has run. The check fails on `NeopixelDriver` until it lands.
2. **DOCS** — A.U32.01's README reflash runbook cites `tests_scripts/test_device_tomls.py:294` as where the refactor
   pins the hostname. M.TSC.079 keeps that assertion as `test_hostname_is_sensorstation_plus_name` but rewrites the
   file around it, so the line number moves. The runbook should cite the test by name; a line number cannot survive the
   rewrite.
3. **TOOL (confirmation only, no new edit)** — the `pyproject.toml` pointers from this cluster are already in M.TOOL
   end states: `pythonpath = ["."]` and `addopts = ["--strict-markers"]` → M.TOOL.034 (M.TSC.014, M.TSC.120); the FBT001
   entry for `test_bench_no_task_ended_completeness.py`, the A002/N802 entry for `test_digital_twin_ci_suite_ceiling.py`,
   the removal of the `test_buildgen_twin_wiring.py` ANN401 entry, A.U28.31's first-run removals and the per-scope
   PLC0415 entries → M.TOOL.030 (M.TSC.027, M.TSC.083, M.TSC.054, M.TSC.123, M.TSC.099); M.TSC.066's
   `build/generated_src/**` exception matches M.TOOL.030 (TOOL gap 1).
4. **TWIN (confirmation only)** — M.TSC.089's conformance check also covers `digital_twin/machine.py`'s fakes. Their
   `TEST_API` tuples are already in M.TWIN.020-.036.

Incoming gaps carried here: HW_BENCH GAP-B1-B5; HW_DEV GAP-D1, D3, D7, D8, D10, D11, D14; SRC_CORE GAP-G6, G8, G9,
G10; SRC_SENS GAP-1, 3, 11, 13, 17; SRC_NET gap 3; TEST_HELP GAP-H1, H6; TWIN's TSC item; WEB gaps 2, 5, 7; GEN gaps
1-3; SCR gaps 1, 3; TOOL gaps 1, 2. Each is cited in the From line of the M.TSC change that carries it.

## Adherence findings

Each rule was checked against every file section above, using the merged end state. Breaches found at HEAD were fixed in
the file's own merged change. None was raised as a question.

- **No temporary or history citations in permanent text** (CLAUDE.md working agreement; A.U36.544): HEAD breaches —
  `test_buildgen_validate.py:718` "(Phase 2)", `:935` "WP1" → M.TSC.055; `test_buildgen_generate.py:7` "Session 5's",
  `:221` "WP1/Topic 2", `:417-418` "Phase 3 … Found by an error-path coverage sweep", `:489` "Phase 4" → M.TSC.044 (the
  `:7`, `:417-418` and `:489` rewrites are adherence fixes added by this merge, since no action names them);
  `test_digital_twin_generated_boot.py:2` "Session 6's job" → M.TSC.085, `:213` "Session 3's" → M.TSC.086 (adherence
  fix added by this merge); `test_device_tomls.py:3` "Session 3's" → M.TSC.079; `test_persistence_write_marker_completeness.py:230,
  :243` "F14"/"F15" → M.TSC.119; `test_device_script_gc_threshold.py:3, :63` "MEASUREMENTS M3.8" → M.TSC.076;
  `test_timer_stagger_no_coincidence.py:1` "WP7" → the file is deleted (M.TSC.143). `test_digital_twin_boot_contiguity.py:52`'s
  "MEASUREMENTS archive §7L.7" points to a permanent doc; M.TSC.063's `archive §N` rule accepts it → ok.
- **Header and comment cap** (G9/R16; CLAUDE.md 3-line cap): every rewritten docstring and comment in this file is ≤ 3
  prose lines. Header presence for `tests/` is gated by M.TSC.065 (AC_NOTES 42 (1)). `_devices.py`, the fixtures and
  every new file get a header → ok.
- **Host annotations** (G8/R05 hidden-name rule): 10 HEAD files carry `from __future__ import annotations`. Each loses
  it in its own change (M.TSC.011, .021, .028, .065, .073, .076, .082, .085, .150, .166), and M.TSC.199 keeps the
  count at zero.
- **No variant literal outside `devices/`** (OR78.a): HEAD's per-device lists and names in `test_device_tomls.py`,
  `test_build_firmware.py`, `test_build_website_sh.py`, `test_buildgen_generate.py`, `test_error_catalog.py` and
  `test_digital_twin_boot_contiguity.py` are derived through `_devices.py` (M.TSC.002, .175 and each file's change).
  M.TSC.110 enforces this, with an exclusion list that can only shrink.
- **Host-I/O wear** (CLAUDE.md wear rule): the fuzz test writes one file per case in `tmp_path` and rewrites it in
  place (M.TSC.043). The collect-only matrix writes nothing (M.TSC.137). The website, frozen-HTML and firmware staging
  tests work in `tmp_path` (M.TSC.034, .035, .094, .181). No test brute-forces scale, so ok.
- **No new permanent CI control arm** (OR21.a (2)): the contiguity suppressed arm is the existing one (M.TSC.082). Each
  "synthetic bite" is a fixture inside its own test, not a CI arm. A.U25.58's premise check (M.TSC.093) follows harmonization 5,
  so ok.
- **Stale comments**: `_script_loader.py` (M.TSC.011) and the `--strict-markers` comment (M.TSC.120) are rewritten to
  match current behaviour, so ok.
- **Legacy tree** (reference-only): no change edits `python/`, `modules/` or the `build-*.sh` scripts. The legacy-path
  checks only read them (M.TSC.101), so ok.
- **Credentials**: no change adds one. The TOMLs' hotspot value `12345678` stays fixture data where it already is
  (`_toml_fixtures.py:27`, synthetic inputs). The bench AP password leaves argv (M.TSC.126), and the hardware conftest
  value is derived from the bench TOML (M.TSC.173), so ok.
- **`arduino/`, `ext/`**: neither was read or edited. `ext/` files are only hashed and compared (M.TSC.153, .154), so ok.

## Owner questions

None. Every conflict was settled from the actions, the registers or an owner answer: GEN Q1 → OR131 and GEN Q2 → OR132
(M.TSC.154, M.TSC.224), SCR Q1 → OR133 (M.TSC.134-.136, exit 2, firm).

## Agent decisions for the OR2.c review

- **D-TSC1** (M.TSC.020): the await-depth analysis lives under `tests_scripts/`, not `audit/stack_depth.py`, because a
  permanent test cannot depend on `audit/`.
- **D-TSC2** (M.TSC.089): the twin's `machine.py` fakes follow the same conformance rule as `tests/machine.py`.
- **D-TSC3** (M.TSC.102): in-DUT scenarios moved by A.U25.46 join the level ID space as `scenarios.<name>`.
- **D-TSC4** (M.TSC.121, .147): the JS timeout relation check stays next to the `@tunable` tag, since it pins a
  cross-unit relation that no register row expresses.
- **D-TSC5** (M.TSC.175): one `_devices.py` pair, `devices_with()` and `bench_device()`, replaces per-file TOML parsing.
- **D-TSC6** (M.TSC.185-.188, .080, .047): files for checks whose action names none — `test_device_script_facts.py`,
  `test_hardware_clones.py`, `test_tests_hardware_product_copies.py`, A.U26.46 in `test_device_script_bench_facts.py`,
  A.U11.32 in `test_code_conventions.py`, A.U24.44 in `test_buildgen_generate.py`.
- **D-TSC7** (M.TSC.079): `test_device_tomls.py:294`'s `hostname == "SensorStation" + name` assertion is kept.
  A.U20.19 deletes `:284-411` as validate checks restated by hand, but `validate.py` checks only the host-label form
  (M.GEN.026). A.U20.19's own rule ("a hand check stays only where it tests something `validate.py` does not") therefore
  keeps it, and the header names it.
- **Adherence fixes added beyond the actions**: the comment rewrites at `test_buildgen_generate.py:5-7, :416-418, :489`
  (M.TSC.044) and `test_digital_twin_generated_boot.py:213-215` (M.TSC.086).
- **Settled conflicts** (each in its change's Resolved line): A.U37.11 vs G8/R17 (M.TSC.061); A.U10.13/A.U11.39
  (M.TSC.143); A.U6.12 folded into A.U28.07 (M.TSC.062, .183); A.U25.25 vs A.U25.44 (M.TSC.054); A.U20.28 subset and
  `_bus` keys, GEN gap 3 (M.TSC.151); boot-entry name per M.GEN.019 (M.TSC.045); A.U20.06 (5) vs A.U16.17, fram
  included (M.TSC.046); A.U24.44's renamed attribute (M.TSC.047); A.U7.09 vs A.U27.17 (M.TSC.084); A.U13.17 vs
  A.U17.21 (M.TSC.057); A.U28.06 vs A.U28.08 (M.TSC.079); A.U26.74 blast vs change (M.TSC.120); A.U24.13 vs A.U27.37
  (M.TSC.014); A.U10.47's generated-assert exemption not written (M.TSC.064); A.U36.512 vs A.U24.66 (M.TSC.082);
  A.U27.21 end names (M.TSC.095); A.U30.19 placement per GAP-G8 (M.TSC.090); A.U34.11 vs A.U37.02 (M.TSC.109); GAP-17
  plus AC_NOTES 42 (2) (M.TSC.112); A.U21 classes vs A.U24.75 (M.TSC.114); A.U6.17 (7) vs A.U26.71 (2) (M.TSC.119);
  OR31.a (3) vs OR120/OR130 (M.TSC.155); A.U7.23/A.U24.53 follow M.WEB.082 (M.TSC.108, .169).

## Ledger

| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.C.01 | dropped (the hardware-round procedure; names `tests_hardware/conftest.py`, never `tests_scripts/conftest.py` — HW_BENCH/PROC) |
| A.C.12 | merged into M.TSC.028 |
| A.C.13 | merged into M.TSC.119 |
| A.S0930.01 | merged into M.TSC.057, M.TSC.079, M.TSC.176, M.TSC.182 |
| A.S0930.02 | merged into M.TSC.047, M.TSC.158 |
| A.S0930.04 | merged into M.TSC.087 |
| A.S0930.06 | merged into M.TSC.032, M.TSC.119 |
| A.S0930.07 | merged into M.TSC.152 |
| A.S0930.08 | merged into M.TSC.065, M.TSC.225 |
| A.S0930.16 | merged into M.TSC.073 |
| A.S0930.19 | merged into M.TSC.119 |
| A.S0930.20 | merged into M.TSC.040, M.TSC.048, M.TSC.091, M.TSC.100, M.TSC.155 |
| A.S0930.28 | merged into M.TSC.028, M.TSC.119 |
| A.S0930.30 | merged into M.TSC.065 |
| A.S0930.34 | merged into M.TSC.119, M.TSC.155 |
| A.S0930.39 | merged into M.TSC.028 |
| A.SDEP.02 | merged into M.TSC.033, M.TSC.108 |
| A.SDEP.03 | merged into M.TSC.032, M.TSC.114 |
| A.SDEP.04 | merged into M.TSC.167, M.TSC.168 |
| A.SDEP.07 | merged into M.TSC.034, M.TSC.153 |
| A.SDEP.08 | merged into M.TSC.055, M.TSC.114 |
| A.SDEP.11 | merged into M.TSC.115 |
| A.SDEP.14 | merged into M.TSC.058, M.TSC.117 |
| A.SDEP.15 | merged into M.TSC.221 (carried from another file's action or a gap) |
| A.SDEP.16 | merged into M.TSC.070, M.TSC.085 |
| A.SDEP.17 | merged into M.TSC.081, M.TSC.095 |
| A.SDEP.19 | merged into M.TSC.167, M.TSC.172 |
| A.SDEP.21 | merged into M.TSC.065 |
| A.U0.06 | merged into M.TSC.016 |
| A.U0.07 | merged into M.TSC.011, M.TSC.065, M.TSC.099 |
| A.U0.08 | merged into M.TSC.009, M.TSC.063 |
| A.U0.09 | merged into M.TSC.010, M.TSC.071 |
| A.U0.10 | merged into M.TSC.063, M.TSC.071 |
| A.U0.16 | merged into M.TSC.065 |
| A.U0.18 | merged into M.TSC.065 |
| A.U0.20 | merged into M.TSC.065 |
| A.U0.28 | merged into M.TSC.055, M.TSC.065 |
| A.U0.29 | merged into M.TSC.065; its `test_device_tomls.py:761` sentence dropped (the test goes with A.U20.19, M.TSC.079) |
| A.U0.31 | merged into M.TSC.065 |
| A.U0.35 | merged into M.TSC.065 |
| A.U0.39 | merged into M.TSC.065 |
| A.U0.40 | merged into M.TSC.065 |
| A.U0.41 | merged into M.TSC.065 |
| A.U0.42 | merged into M.TSC.065 |
| A.U0.48 | merged into M.TSC.065 |
| A.U1.01 | merged into M.TSC.167 |
| A.U1.05 | merged into M.TSC.126 |
| A.U1.08 | merged into M.TSC.009, M.TSC.010, M.TSC.126 |
| A.U1.09 | merged into M.TSC.063, M.TSC.065, M.TSC.101 |
| A.U1.10 | merged into M.TSC.101 |
| A.U1.21 | merged into M.TSC.065, M.TSC.157 |
| A.U1.22 | merged into M.TSC.126 |
| A.U1.23 | merged into M.TSC.044, M.TSC.085 |
| A.U1.24 | merged into M.TSC.079 |
| A.U1.25 | merged into M.TSC.034, M.TSC.065 |
| A.U10.05 | merged into M.TSC.069 |
| A.U10.08 | merged into M.TSC.155 |
| A.U10.10 | merged into M.TSC.046, M.TSC.160 |
| A.U10.12 | merged into M.TSC.046 |
| A.U10.13 | merged into M.TSC.143 |
| A.U10.16 | merged into M.TSC.105 |
| A.U10.19 | merged into M.TSC.133 |
| A.U10.22 | merged into M.TSC.112 |
| A.U10.25 | merged into M.TSC.124 |
| A.U10.30 | merged into M.TSC.011, M.TSC.055, M.TSC.098 |
| A.U10.34 | merged into M.TSC.037, M.TSC.065 |
| A.U10.37 | merged into M.TSC.001 (carried from another file's action or a gap) |
| A.U10.38 | merged into M.TSC.037, M.TSC.160, M.TSC.164 |
| A.U10.39 | merged into M.TSC.173 |
| A.U10.41 | merged into M.TSC.119, M.TSC.170 |
| A.U10.43 | merged into M.TSC.005, M.TSC.013, M.TSC.044, M.TSC.049, M.TSC.053, M.TSC.055, M.TSC.056, M.TSC.079, M.TSC.176 (its `test_timer_stagger_no_coincidence.py` edit dropped: file deleted, M.TSC.143) |
| A.U10.46 | merged into M.TSC.109 |
| A.U10.47 | merged into M.TSC.064 |
| A.U11.03 | merged into M.TSC.044 |
| A.U11.05 | merged into M.TSC.045, M.TSC.085 |
| A.U11.08 | merged into M.TSC.046 |
| A.U11.10 | merged into M.TSC.046, M.TSC.081, M.TSC.095, M.TSC.157 |
| A.U11.18 | merged into M.TSC.067 |
| A.U11.25 | merged into M.TSC.067 |
| A.U11.28 | merged into M.TSC.073 |
| A.U11.30 | merged into M.TSC.065 |
| A.U11.31 | merged into M.TSC.165 |
| A.U11.32 | merged into M.TSC.080 (carried from another file's action or a gap) |
| A.U11.33 | merged into M.TSC.018, M.TSC.074, M.TSC.129 |
| A.U11.39 | merged into M.TSC.143 |
| A.U11.S01 | merged into M.TSC.047 |
| A.U11.S04 | merged into M.TSC.044 |
| A.U12.13 | merged into M.TSC.069 (carried from another file's action or a gap) |
| A.U13.17 | merged into M.TSC.057 |
| A.U14.05 | merged into M.TSC.108 |
| A.U14.26 | merged into M.TSC.108 |
| A.U14.30 | merged into M.TSC.058, M.TSC.117 |
| A.U14.33 | merged into M.TSC.142 |
| A.U15.02 | merged into M.TSC.130 |
| A.U15.10 | merged into M.TSC.049, M.TSC.056 |
| A.U15.11 | merged into M.TSC.159 |
| A.U15.12 | merged into M.TSC.040, M.TSC.046, M.TSC.047, M.TSC.106, M.TSC.159 |
| A.U15.16 | merged into M.TSC.060 |
| A.U15.19 | merged into M.TSC.106 |
| A.U15.31 | merged into M.TSC.069 (carried from another file's action or a gap) |
| A.U15.36 | merged into M.TSC.106 |
| A.U15.40 | merged into M.TSC.193 (carried from another file's action or a gap) |
| A.U15.43 | merged into M.TSC.109 |
| A.U16.01 | merged into M.TSC.065 |
| A.U16.02 | merged into M.TSC.092, M.TSC.095 |
| A.U16.07 | merged into M.TSC.119 |
| A.U16.08 | merged into M.TSC.065 |
| A.U16.12 | merged into M.TSC.065 |
| A.U16.14 | merged into M.TSC.065 |
| A.U16.16 | merged into M.TSC.065 |
| A.U16.17 | merged into M.TSC.046, M.TSC.085, M.TSC.176 |
| A.U16.20 | merged into M.TSC.040, M.TSC.047, M.TSC.049, M.TSC.054, M.TSC.056, M.TSC.085, M.TSC.161, M.TSC.176 |
| A.U16.R03 | merged into M.TSC.046 |
| A.U17.08 | merged into M.TSC.152 |
| A.U17.11 | merged into M.TSC.152 |
| A.U17.18 | merged into M.TSC.054 |
| A.U17.21 | merged into M.TSC.057, M.TSC.182 |
| A.U17.32 | merged into M.TSC.057, M.TSC.182 |
| A.U18.10 | merged into M.TSC.047, M.TSC.170 |
| A.U18.33 | merged into M.TSC.044 |
| A.U18.35 | merged into M.TSC.038 |
| A.U18.38 | merged into M.TSC.040, M.TSC.047, M.TSC.159 |
| A.U18.40 | merged into M.TSC.047 (carried from another file's action or a gap) |
| A.U18.44 | merged into M.TSC.109 |
| A.U19.02 | merged into M.TSC.044 |
| A.U19.10 | merged into M.TSC.044 |
| A.U19.13 | merged into M.TSC.170 |
| A.U19.14 | merged into M.TSC.121, M.TSC.165 |
| A.U19.17 | merged into M.TSC.109 |
| A.U19.18 | merged into M.TSC.031, M.TSC.154 |
| A.U19.19 | merged into M.TSC.154 |
| A.U19.20 | merged into M.TSC.019, M.TSC.085 |
| A.U19.21 | merged into M.TSC.065 |
| A.U2.01 | merged into M.TSC.088 |
| A.U2.02 | merged into M.TSC.088 |
| A.U2.03 | merged into M.TSC.027 |
| A.U2.08 | merged into M.TSC.027 |
| A.U2.19 | merged into M.TSC.121 |
| A.U2.21 | merged into M.TSC.039, M.TSC.040 |
| A.U2.22 | merged into M.TSC.088 |
| A.U2.23 | merged into M.TSC.055, M.TSC.057 |
| A.U2.25 | merged into M.TSC.088 |
| A.U20.01 | merged into M.TSC.057, M.TSC.182 |
| A.U20.02 | merged into M.TSC.045, M.TSC.085 |
| A.U20.03 | merged into M.TSC.045 |
| A.U20.04 | merged into M.TSC.045, M.TSC.108 |
| A.U20.05 | merged into M.TSC.045 |
| A.U20.06 | merged into M.TSC.046, M.TSC.081, M.TSC.095, M.TSC.157 |
| A.U20.07 | merged into M.TSC.046 |
| A.U20.08 | merged into M.TSC.047 |
| A.U20.09 | merged into M.TSC.050, M.TSC.056 |
| A.U20.10 | merged into M.TSC.079 |
| A.U20.12 | merged into M.TSC.067, M.TSC.163 |
| A.U20.13 | merged into M.TSC.031, M.TSC.042 |
| A.U20.14 | merged into M.TSC.048, M.TSC.095, M.TSC.130 |
| A.U20.15 | merged into M.TSC.044, M.TSC.045, M.TSC.065 |
| A.U20.16 | merged into M.TSC.048, M.TSC.086, M.TSC.176 |
| A.U20.17 | merged into M.TSC.008, M.TSC.012, M.TSC.041, M.TSC.048, M.TSC.056, M.TSC.158, M.TSC.182 |
| A.U20.18 | merged into M.TSC.048, M.TSC.056 |
| A.U20.19 | merged into M.TSC.043, M.TSC.044, M.TSC.055, M.TSC.056, M.TSC.079, M.TSC.175, M.TSC.182 |
| A.U20.20 | merged into M.TSC.056, M.TSC.176 |
| A.U20.21 | merged into M.TSC.037, M.TSC.056 |
| A.U20.22 | merged into M.TSC.047 |
| A.U20.23 | merged into M.TSC.065 |
| A.U20.24 | merged into M.TSC.049, M.TSC.053, M.TSC.162, M.TSC.182 |
| A.U20.25 | merged into M.TSC.041, M.TSC.159, M.TSC.163 |
| A.U20.26 | merged into M.TSC.159 |
| A.U20.27 | merged into M.TSC.052, M.TSC.056 |
| A.U20.28 | merged into M.TSC.054, M.TSC.079, M.TSC.083, M.TSC.151, M.TSC.158, M.TSC.165, M.TSC.182 |
| A.U20.29 | merged into M.TSC.079 |
| A.U20.30 | merged into M.TSC.048, M.TSC.059 |
| A.U20.31 | merged into M.TSC.061 |
| A.U20.32 | merged into M.TSC.004, M.TSC.013, M.TSC.054, M.TSC.162 |
| A.U20.33 | merged into M.TSC.003, M.TSC.011, M.TSC.021, M.TSC.028, M.TSC.065, M.TSC.073, M.TSC.076, M.TSC.082, M.TSC.085, M.TSC.150, M.TSC.166, M.TSC.199 |
| A.U20.34 | merged into M.TSC.056, M.TSC.182 |
| A.U20.35 | merged into M.TSC.145 |
| A.U20.36 | merged into M.TSC.051 |
| A.U20.37 | merged into M.TSC.049, M.TSC.053, M.TSC.055, M.TSC.060, M.TSC.162, M.TSC.164; its `test_device_tomls.py:285` assertion dropped (the test is deleted, M.TSC.079) |
| A.U20.39 | merged into M.TSC.053 |
| A.U20.41 | merged into M.TSC.047, M.TSC.055, M.TSC.059 |
| A.U20.42 | merged into M.TSC.047 |
| A.U21.01 | merged into M.TSC.125 |
| A.U21.02 | merged into M.TSC.125 |
| A.U21.03 | merged into M.TSC.114, M.TSC.125 |
| A.U21.04 | merged into M.TSC.221 (carried from another file's action or a gap) |
| A.U21.06 | merged into M.TSC.115 |
| A.U21.08 | merged into M.TSC.032, M.TSC.116 |
| A.U21.09 | dropped for this file (its edit is `toolchain/micropython_overrides.py`, TOOL; the test file appears only in its owner quote — its tests are A.U21.10-.12, M.TSC.117) |
| A.U21.10 | merged into M.TSC.033, M.TSC.117 |
| A.U21.11 | merged into M.TSC.015, M.TSC.117 |
| A.U21.12 | merged into M.TSC.117, M.TSC.135 |
| A.U21.15 | merged into M.TSC.114, M.TSC.125 |
| A.U21.16 | merged into M.TSC.117 |
| A.U21.17 | merged into M.TSC.114, M.TSC.125 |
| A.U21.18 | merged into M.TSC.172 |
| A.U21.19 | merged into M.TSC.126 |
| A.U21.20 | merged into M.TSC.126 |
| A.U21.21 | merged into M.TSC.126 |
| A.U21.22 | merged into M.TSC.032, M.TSC.135 |
| A.U21.23 | merged into M.TSC.126 |
| A.U21.24 | merged into M.TSC.126 |
| A.U21.25 | merged into M.TSC.126 |
| A.U21.28 | merged into M.TSC.126, M.TSC.171 |
| A.U21.29 | merged into M.TSC.117 |
| A.U21.30 | merged into M.TSC.125 |
| A.U21.31 | merged into M.TSC.065, M.TSC.117 |
| A.U23.02 | merged into M.TSC.121 |
| A.U23.09 | merged into M.TSC.017, M.TSC.039, M.TSC.072 |
| A.U23.10 | merged into M.TSC.017 (carried from another file's action or a gap) |
| A.U23.16 | merged into M.TSC.159 |
| A.U23.17 | merged into M.TSC.159 |
| A.U23.18 | merged into M.TSC.040 |
| A.U23.20 | merged into M.TSC.040 |
| A.U23.23 | merged into M.TSC.159 |
| A.U23.24 | merged into M.TSC.100 |
| A.U23.25 | merged into M.TSC.100 |
| A.U23.26 | merged into M.TSC.100 |
| A.U23.27 | merged into M.TSC.100 |
| A.U23.30 | merged into M.TSC.040 |
| A.U23.34 | merged into M.TSC.169 |
| A.U23.37 | merged into M.TSC.072, M.TSC.121 |
| A.U23.38 | merged into M.TSC.036, M.TSC.214 |
| A.U23.39 | merged into M.TSC.214 (carried from another file's action or a gap) |
| A.U23.40 | merged into M.TSC.156 |
| A.U23.41 | merged into M.TSC.156 |
| A.U23.44 | merged into M.TSC.224 (carried from another file's action or a gap) |
| A.U23.47 | merged into M.TSC.109, M.TSC.170 |
| A.U24.01 | merged into M.TSC.068 |
| A.U24.02 | merged into M.TSC.068 |
| A.U24.03 | merged into M.TSC.118 |
| A.U24.04 | merged into M.TSC.118 |
| A.U24.05 | merged into M.TSC.070, M.TSC.141 |
| A.U24.08 | merged into M.TSC.118 |
| A.U24.11 | merged into M.TSC.118, M.TSC.175 |
| A.U24.13 | merged into M.TSC.014, M.TSC.021, M.TSC.027, M.TSC.054, M.TSC.073, M.TSC.082, M.TSC.096, M.TSC.166, M.TSC.174 |
| A.U24.18 | merged into M.TSC.089 |
| A.U24.36 | merged into M.TSC.086 |
| A.U24.39 | merged into M.TSC.044 |
| A.U24.40 | merged into M.TSC.116, M.TSC.134 |
| A.U24.44 | merged into M.TSC.047 (carried from another file's action or a gap) |
| A.U24.46 | merged into M.TSC.195 (carried from another file's action or a gap) |
| A.U24.51 | merged into M.TSC.002, M.TSC.021, M.TSC.055, M.TSC.114, M.TSC.121, M.TSC.175 |
| A.U24.52 | merged into M.TSC.169 |
| A.U24.53 | merged into M.TSC.169 |
| A.U24.55 | merged into M.TSC.086 |
| A.U24.57 | merged into M.TSC.106 |
| A.U24.60 | merged into M.TSC.118 |
| A.U24.64 | merged into M.TSC.095 |
| A.U24.65 | merged into M.TSC.135, M.TSC.175 |
| A.U24.66 | merged into M.TSC.002, M.TSC.029, M.TSC.031, M.TSC.035, M.TSC.037, M.TSC.038, M.TSC.042, M.TSC.044, M.TSC.049, M.TSC.053, M.TSC.054, M.TSC.055, M.TSC.060, M.TSC.079, M.TSC.082, M.TSC.083, M.TSC.084, M.TSC.085, M.TSC.126, M.TSC.134, M.TSC.159, M.TSC.160, M.TSC.161, M.TSC.162, M.TSC.170, M.TSC.171, M.TSC.173, M.TSC.175 |
| A.U24.67 | merged into M.TSC.085 |
| A.U24.69 | merged into M.TSC.206 (carried from another file's action or a gap) |
| A.U24.70 | merged into M.TSC.205 (carried from another file's action or a gap) |
| A.U24.72 | merged into M.TSC.070, M.TSC.136 |
| A.U24.73 | merged into M.TSC.004, M.TSC.013, M.TSC.038, M.TSC.054, M.TSC.079, M.TSC.085, M.TSC.114, M.TSC.130, M.TSC.170 |
| A.U24.75 | merged into M.TSC.044, M.TSC.050, M.TSC.055, M.TSC.056, M.TSC.114, M.TSC.160 |
| A.U24.76 | merged into M.TSC.118 |
| A.U25.01 | merged into M.TSC.065 |
| A.U25.09 | merged into M.TSC.087 |
| A.U25.23 | merged into M.TSC.069 |
| A.U25.25 | merged into M.TSC.054, M.TSC.151, M.TSC.175 |
| A.U25.32 | merged into M.TSC.085 |
| A.U25.34 | merged into M.TSC.148, M.TSC.191 |
| A.U25.35 | merged into M.TSC.150, M.TSC.165, M.TSC.191 |
| A.U25.36 | merged into M.TSC.165 |
| A.U25.37 | merged into M.TSC.190 (carried from another file's action or a gap) |
| A.U25.43 | merged into M.TSC.148 |
| A.U25.44 | merged into M.TSC.054, M.TSC.084, M.TSC.085, M.TSC.150 (its "the fixture's one test goes" dropped: A.U25.25 moves it, M.TSC.054) |
| A.U25.46 | merged into M.TSC.192 (carried from another file's action or a gap) |
| A.U25.48 | merged into M.TSC.175 |
| A.U25.49 | merged into M.TSC.200 (carried from another file's action or a gap) |
| A.U25.50 | merged into M.TSC.065 |
| A.U25.53 | merged into M.TSC.176 |
| A.U25.58 | merged into M.TSC.093 |
| A.U25.61 | merged into M.TSC.081 |
| A.U25.64 | merged into M.TSC.165 |
| A.U25.66 | merged into M.TSC.165 |
| A.U25.67 | merged into M.TSC.149 |
| A.U25.69 | merged into M.TSC.046 |
| A.U25.74 | merged into M.TSC.220 (carried from another file's action or a gap) |
| A.U26.01 | merged into M.TSC.056, M.TSC.079, M.TSC.175, M.TSC.179 |
| A.U26.02 | merged into M.TSC.031, M.TSC.032 |
| A.U26.03 | merged into M.TSC.180 |
| A.U26.05 | merged into M.TSC.218, M.TSC.219 |
| A.U26.06 | merged into M.TSC.119, M.TSC.138 |
| A.U26.07 | merged into M.TSC.119, M.TSC.173, M.TSC.212 |
| A.U26.08 | merged into M.TSC.119, M.TSC.122, M.TSC.138 |
| A.U26.09 | dropped (names `tests_hardware/conftest.py`, same basename; HW_BENCH) |
| A.U26.11 | merged into M.TSC.073 |
| A.U26.12 | merged into M.TSC.026, M.TSC.073, M.TSC.119 |
| A.U26.13 | merged into M.TSC.026, M.TSC.198 |
| A.U26.14 | merged into M.TSC.026, M.TSC.119, M.TSC.120 |
| A.U26.15 | merged into M.TSC.026, M.TSC.119 |
| A.U26.16 | merged into M.TSC.077 |
| A.U26.17 | merged into M.TSC.028 |
| A.U26.18 | merged into M.TSC.073 |
| A.U26.19 | merged into M.TSC.073 |
| A.U26.20 | merged into M.TSC.119 |
| A.U26.21 | merged into M.TSC.026, M.TSC.178 |
| A.U26.22 | merged into M.TSC.023, M.TSC.194 |
| A.U26.23 | merged into M.TSC.046 |
| A.U26.24 | merged into M.TSC.075, M.TSC.081 |
| A.U26.26 | merged into M.TSC.025 |
| A.U26.27 | merged into M.TSC.025 |
| A.U26.28 | merged into M.TSC.028 |
| A.U26.29 | merged into M.TSC.022 |
| A.U26.31 | merged into M.TSC.137, M.TSC.138 |
| A.U26.35 | merged into M.TSC.122 |
| A.U26.36 | merged into M.TSC.122 |
| A.U26.37 | merged into M.TSC.198 (carried from another file's action or a gap) |
| A.U26.38 | dropped (names `tests_hardware/conftest.py`, same basename; HW_BENCH) |
| A.U26.39 | merged into M.TSC.119 |
| A.U26.41 | merged into M.TSC.028 |
| A.U26.42 | merged into M.TSC.203 (carried from another file's action or a gap) |
| A.U26.44 | merged into M.TSC.073, M.TSC.076, M.TSC.185 |
| A.U26.45 | dropped (names `tests_hardware/conftest.py`, same basename; HW_BENCH) |
| A.U26.46 | merged into M.TSC.185 (carried from another file's action or a gap) |
| A.U26.47 | merged into M.TSC.025, M.TSC.108, M.TSC.166 |
| A.U26.48 | merged into M.TSC.076 |
| A.U26.49 | merged into M.TSC.173, M.TSC.188 |
| A.U26.50 | merged into M.TSC.024 |
| A.U26.51 | merged into M.TSC.102 |
| A.U26.56 | merged into M.TSC.122, M.TSC.197 |
| A.U26.61 | merged into M.TSC.076, M.TSC.078 |
| A.U26.62 | merged into M.TSC.027 |
| A.U26.67 | merged into M.TSC.023, M.TSC.027 |
| A.U26.68 | merged into M.TSC.076, M.TSC.186 |
| A.U26.69 | merged into M.TSC.186 (carried from another file's action or a gap) |
| A.U26.70 | merged into M.TSC.096, M.TSC.097 |
| A.U26.71 | merged into M.TSC.119, M.TSC.138 |
| A.U26.74 | merged into M.TSC.120, M.TSC.122, M.TSC.138 |
| A.U26.75 | merged into M.TSC.026, M.TSC.198 |
| A.U26.78 | merged into M.TSC.187 (carried from another file's action or a gap) |
| A.U26.79 | merged into M.TSC.119 |
| A.U26.83 | merged into M.TSC.021 |
| A.U26.85 | merged into M.TSC.028, M.TSC.032 |
| A.U26.87 | merged into M.TSC.028 |
| A.U27.01 | merged into M.TSC.165 |
| A.U27.02 | merged into M.TSC.221 (carried from another file's action or a gap) |
| A.U27.03 | merged into M.TSC.065 |
| A.U27.04 | merged into M.TSC.130 |
| A.U27.05 | merged into M.TSC.031, M.TSC.085, M.TSC.131 |
| A.U27.06 | merged into M.TSC.034 |
| A.U27.08 | merged into M.TSC.175, M.TSC.189 |
| A.U27.10 | merged into M.TSC.034, M.TSC.035, M.TSC.209 |
| A.U27.11 | merged into M.TSC.158 |
| A.U27.12 | merged into M.TSC.015, M.TSC.070, M.TSC.135, M.TSC.222 |
| A.U27.13 | merged into M.TSC.204 (carried from another file's action or a gap) |
| A.U27.14 | merged into M.TSC.134 |
| A.U27.15 | merged into M.TSC.070, M.TSC.082, M.TSC.085, M.TSC.150 |
| A.U27.16 | merged into M.TSC.211 (carried from another file's action or a gap) |
| A.U27.17 | merged into M.TSC.084 |
| A.U27.18 | merged into M.TSC.136 |
| A.U27.19 | merged into M.TSC.122 |
| A.U27.20 | merged into M.TSC.157 |
| A.U27.21 | merged into M.TSC.095, M.TSC.157 |
| A.U27.23 | merged into M.TSC.016, M.TSC.104 |
| A.U27.24 | merged into M.TSC.104 |
| A.U27.25 | merged into M.TSC.104 |
| A.U27.26 | merged into M.TSC.210 (carried from another file's action or a gap) |
| A.U27.28 | merged into M.TSC.065 |
| A.U27.29 | merged into M.TSC.008, M.TSC.029, M.TSC.032, M.TSC.048, M.TSC.114, M.TSC.125 |
| A.U27.30 | merged into M.TSC.065 |
| A.U27.31 | merged into M.TSC.033 |
| A.U27.32 | merged into M.TSC.083 |
| A.U27.33 | merged into M.TSC.035, M.TSC.135, M.TSC.213 |
| A.U27.34 | merged into M.TSC.030, M.TSC.094 |
| A.U27.35 | merged into M.TSC.032, M.TSC.034, M.TSC.035 |
| A.U27.36 | merged into M.TSC.032 |
| A.U27.37 | merged into M.TSC.014, M.TSC.021, M.TSC.058, M.TSC.083 |
| A.U27.38 | merged into M.TSC.135 |
| A.U27.39 | merged into M.TSC.206 (carried from another file's action or a gap) |
| A.U28.01 | merged into M.TSC.079, M.TSC.125, M.TSC.172, M.TSC.223 |
| A.U28.03 | merged into M.TSC.146 |
| A.U28.04 | merged into M.TSC.168 |
| A.U28.05 | merged into M.TSC.033 |
| A.U28.06 | merged into M.TSC.062, M.TSC.079, M.TSC.175 |
| A.U28.07 | merged into M.TSC.062, M.TSC.183 (carried from another file's action or a gap) |
| A.U28.08 | merged into M.TSC.062, M.TSC.079, M.TSC.136, M.TSC.183 |
| A.U28.11 | merged into M.TSC.062 |
| A.U28.15 | merged into M.TSC.070, M.TSC.136 |
| A.U28.16 | merged into M.TSC.136, M.TSC.168 |
| A.U28.17 | merged into M.TSC.062, M.TSC.184 (carried from another file's action or a gap) |
| A.U28.20 | merged into M.TSC.126 |
| A.U28.21 | merged into M.TSC.172 |
| A.U28.22 | merged into M.TSC.172 |
| A.U28.23 | merged into M.TSC.146 |
| A.U28.24 | merged into M.TSC.207 (carried from another file's action or a gap) |
| A.U28.26 | merged into M.TSC.167, M.TSC.168 |
| A.U28.27 | merged into M.TSC.083 |
| A.U28.28 | merged into M.TSC.021, M.TSC.027, M.TSC.083 |
| A.U28.29 | merged into M.TSC.047, M.TSC.055 |
| A.U28.30 | merged into M.TSC.106, M.TSC.132 |
| A.U28.31 | merged into M.TSC.123 |
| A.U28.34 | merged into M.TSC.123 |
| A.U28.37 | merged into M.TSC.062 |
| A.U28.39 | merged into M.TSC.066 |
| A.U28.41 | merged into M.TSC.047 |
| A.U28.43 | merged into M.TSC.062 (carried from another file's action or a gap) |
| A.U29.01 | merged into M.TSC.140 |
| A.U29.02 | merged into M.TSC.140 |
| A.U29.03 | merged into M.TSC.065 |
| A.U3.06 | merged into M.TSC.027 |
| A.U3.11 | merged into M.TSC.111 |
| A.U3.15 | merged into M.TSC.088 |
| A.U30.03 | merged into M.TSC.107 |
| A.U30.04 | merged into M.TSC.081 |
| A.U30.14 | merged into M.TSC.076, M.TSC.095, M.TSC.157 |
| A.U30.16 | merged into M.TSC.095 |
| A.U30.18 | merged into M.TSC.007, M.TSC.020, M.TSC.076 |
| A.U30.19 | merged into M.TSC.001, M.TSC.090 |
| A.U31.01 | merged into M.TSC.144 |
| A.U31.02 | merged into M.TSC.144, M.TSC.175 |
| A.U31.05 | merged into M.TSC.119 |
| A.U31.06 | merged into M.TSC.220 (carried from another file's action or a gap) |
| A.U31.07 | merged into M.TSC.155 |
| A.U31.08 | merged into M.TSC.056, M.TSC.182 |
| A.U31.18 | merged into M.TSC.121 |
| A.U31.19 | merged into M.TSC.128 |
| A.U32.01 | merged into M.TSC.079 |
| A.U32.06 | merged into M.TSC.046 |
| A.U33.01 | merged into M.TSC.052, M.TSC.055, M.TSC.065 |
| A.U33.03 | merged into M.TSC.044, M.TSC.052, M.TSC.054 |
| A.U33.04 | dropped (a BACKLOG.md chroot-list entry, DOCS; names `tests_scripts/conftest.py` only in its text) |
| A.U34.07 | merged into M.TSC.065, M.TSC.139 |
| A.U34.08 | merged into M.TSC.034, M.TSC.153 |
| A.U34.11 | merged into M.TSC.109, M.TSC.123 |
| A.U34.12 | merged into M.TSC.154 |
| A.U35.05 | merged into M.TSC.108 |
| A.U35.08 | merged into M.TSC.175 |
| A.U35.24 | merged into M.TSC.134 |
| A.U35.25 | merged into M.TSC.095 |
| A.U35.26 | merged into M.TSC.084 |
| A.U35.27 | merged into M.TSC.084 |
| A.U35.38 | merged into M.TSC.165 |
| A.U35.39 | merged into M.TSC.086 |
| A.U35.40 | merged into M.TSC.021 |
| A.U35.51 | merged into M.TSC.119 |
| A.U35.56 | merged into M.TSC.147 |
| A.U36.002 | merged into M.TSC.108 |
| A.U36.004 | merged into M.TSC.044, M.TSC.055, M.TSC.065, M.TSC.085 |
| A.U36.012 | merged into M.TSC.076 |
| A.U36.015 | merged into M.TSC.175 |
| A.U36.016 | merged into M.TSC.175 |
| A.U36.020 | merged into M.TSC.065 |
| A.U36.030 | merged into M.TSC.154 |
| A.U36.038 | merged into M.TSC.044, M.TSC.064 |
| A.U36.503 | merged into M.TSC.121 |
| A.U36.504 | merged into M.TSC.119 |
| A.U36.508 | merged into M.TSC.040 |
| A.U36.510 | merged into M.TSC.224 (carried from another file's action or a gap) |
| A.U36.512 | merged into M.TSC.070, M.TSC.082, M.TSC.114, M.TSC.135 |
| A.U36.513 | merged into M.TSC.054, M.TSC.065, M.TSC.085 |
| A.U36.514 | merged into M.TSC.159 |
| A.U36.515 | merged into M.TSC.038, M.TSC.176 |
| A.U36.517 | merged into M.TSC.035 |
| A.U36.518 | merged into M.TSC.151 |
| A.U36.519 | merged into M.TSC.061 |
| A.U36.520 | merged into M.TSC.079 |
| A.U36.527 | merged into M.TSC.109 |
| A.U36.528 | merged into M.TSC.146 |
| A.U36.532 | merged into M.TSC.121, M.TSC.127, M.TSC.174 |
| A.U36.533 | merged into M.TSC.065 |
| A.U36.537 | merged into M.TSC.088 |
| A.U36.541 | merged into M.TSC.127 |
| A.U36.542 | merged into M.TSC.064, M.TSC.065 |
| A.U36.543 | merged into M.TSC.149 |
| A.U36.544 | merged into M.TSC.009, M.TSC.035, M.TSC.044, M.TSC.055, M.TSC.065, M.TSC.119, M.TSC.159, M.TSC.176 (its `test_timer_stagger_no_coincidence.py` edit dropped: file deleted, M.TSC.143) |
| A.U36.546 | merged into M.TSC.065 |
| A.U36.547 | merged into M.TSC.113 |
| A.U36.548 | merged into M.TSC.065, M.TSC.085, M.TSC.096, M.TSC.134, M.TSC.141 |
| A.U36.549 | merged into M.TSC.010, M.TSC.065, M.TSC.071 |
| A.U37.02 | merged into M.TSC.009, M.TSC.010, M.TSC.063, M.TSC.071, M.TSC.099, M.TSC.109, M.TSC.110 |
| A.U37.10 | merged into M.TSC.002, M.TSC.018, M.TSC.019, M.TSC.110, M.TSC.129 |
| A.U37.11 | merged into M.TSC.061 for its read; its test edit (a value pin) dropped — G8/R17 "a bump edits no test" (Resolved there) |
| A.U4.06 | merged into M.TSC.065 |
| A.U4.08 | merged into M.TSC.138 |
| A.U5.03 | merged into M.TSC.047, M.TSC.054, M.TSC.059, M.TSC.158, M.TSC.164 |
| A.U5.04 | merged into M.TSC.047, M.TSC.058, M.TSC.121, M.TSC.169 |
| A.U5.05 | merged into M.TSC.121, M.TSC.170 |
| A.U5.06 | merged into M.TSC.047 |
| A.U5.07 | merged into M.TSC.047, M.TSC.059, M.TSC.161, M.TSC.164 |
| A.U5.09 | merged into M.TSC.047 |
| A.U5.10 | merged into M.TSC.058 |
| A.U5.11 | merged into M.TSC.047, M.TSC.053, M.TSC.059, M.TSC.060 |
| A.U5.16 | merged into M.TSC.159 |
| A.U5.17 | merged into M.TSC.103 |
| A.U5.18 | merged into M.TSC.103 |
| A.U6.01 | merged into M.TSC.038, M.TSC.041, M.TSC.085, M.TSC.170, M.TSC.176 |
| A.U6.02 | merged into M.TSC.158, M.TSC.175 |
| A.U6.03 | merged into M.TSC.002, M.TSC.035, M.TSC.134, M.TSC.181 |
| A.U6.04 | merged into M.TSC.038, M.TSC.054, M.TSC.167 |
| A.U6.05 | merged into M.TSC.175, M.TSC.201 |
| A.U6.06 | merged into M.TSC.088, M.TSC.167 |
| A.U6.10 | merged into M.TSC.169, M.TSC.202 |
| A.U6.11 | merged into M.TSC.169, M.TSC.172, M.TSC.175, M.TSC.184 |
| A.U6.12 | merged into M.TSC.062, M.TSC.079, M.TSC.183 |
| A.U6.14 | merged into M.TSC.002, M.TSC.035, M.TSC.134, M.TSC.176 |
| A.U6.15 | merged into M.TSC.002, M.TSC.110 |
| A.U6.16 | merged into M.TSC.017, M.TSC.039, M.TSC.072, M.TSC.121 |
| A.U6.17 | merged into M.TSC.119, M.TSC.159 |
| A.U6.18 | merged into M.TSC.040, M.TSC.159 |
| A.U6.19 | merged into M.TSC.040, M.TSC.159 |
| A.U6.20 | merged into M.TSC.040, M.TSC.086, M.TSC.159 |
| A.U6.21 | merged into M.TSC.044 |
| A.U6.22 | merged into M.TSC.038, M.TSC.086 |
| A.U6.24 | merged into M.TSC.038, M.TSC.086 |
| A.U6.25 | merged into M.TSC.040, M.TSC.086 |
| A.U6.26 | merged into M.TSC.159, M.TSC.170 |
| A.U6.27 | merged into M.TSC.040, M.TSC.159 |
| A.U6.28 | merged into M.TSC.040 |
| A.U6.29 | merged into M.TSC.056, M.TSC.159 |
| A.U7.01 | merged into M.TSC.102 |
| A.U7.02 | merged into M.TSC.215 (carried from another file's action or a gap) |
| A.U7.03 | merged into M.TSC.136 |
| A.U7.04 | merged into M.TSC.135 |
| A.U7.05 | merged into M.TSC.135 |
| A.U7.06 | merged into M.TSC.134 |
| A.U7.07 | merged into M.TSC.070, M.TSC.118, M.TSC.136, M.TSC.141 |
| A.U7.08 | merged into M.TSC.134, M.TSC.208 |
| A.U7.09 | merged into M.TSC.084 for the rest; its retry case dropped — A.U27.17 removes the retry |
| A.U7.10 | merged into M.TSC.215 (carried from another file's action or a gap) |
| A.U7.11 | merged into M.TSC.157 |
| A.U7.12 | merged into M.TSC.221 (carried from another file's action or a gap) |
| A.U7.13 | merged into M.TSC.138, M.TSC.173, M.TSC.216 |
| A.U7.14 | merged into M.TSC.122, M.TSC.197 |
| A.U7.17 | merged into M.TSC.203 (carried from another file's action or a gap) |
| A.U7.18 | merged into M.TSC.196 (carried from another file's action or a gap) |
| A.U7.19 | merged into M.TSC.134, M.TSC.217 |
| A.U7.20 | merged into M.TSC.135, M.TSC.136, M.TSC.168, M.TSC.177 |
| A.U7.21 | merged into M.TSC.169 |
| A.U7.22 | merged into M.TSC.082, M.TSC.086 |
| A.U7.23 | merged into M.TSC.108 |
| A.U7.24 | merged into M.TSC.102, M.TSC.175 |
| A.U7.26 | merged into M.TSC.006, M.TSC.015, M.TSC.033, M.TSC.055, M.TSC.070, M.TSC.082, M.TSC.114, M.TSC.135 |
| A.U8.02 | merged into M.TSC.121, M.TSC.147 |
| A.U8.03 | merged into M.TSC.065, M.TSC.147 |
| A.U8.04 | merged into M.TSC.121, M.TSC.170 |
| A.U8.05 | merged into M.TSC.007, M.TSC.121, M.TSC.174 |
| A.U8.12 | merged into M.TSC.143 |
| A.U8.14 | merged into M.TSC.007, M.TSC.076, M.TSC.114, M.TSC.117, M.TSC.125, M.TSC.141 |
| A.U8.15 | merged into M.TSC.007, M.TSC.082, M.TSC.135 |
| A.U8.16 | merged into M.TSC.135 |
| A.U8.18 | merged into M.TSC.038 |
| A.U8.20 | merged into M.TSC.007, M.TSC.083, M.TSC.084, M.TSC.108, M.TSC.121 |
| A.U8.22 | merged into M.TSC.007, M.TSC.022, M.TSC.070, M.TSC.082, M.TSC.083, M.TSC.085, M.TSC.121, M.TSC.134, M.TSC.141, M.TSC.165, M.TSC.169, M.TSC.174 |
| A.U8.24 | merged into M.TSC.109 |
| A.U8C.01 | merged into M.TSC.081, M.TSC.166 |
| A.U8C.48 | dropped (names `tests_hardware/conftest.py`, same basename; HW_BENCH) |
| A.U8C.50 | merged into M.TSC.121 |
| A.U8C.57 | dropped (names `tests_hardware/conftest.py`, same basename; HW_BENCH) |
| A.U8C.71 | merged into M.TSC.076, M.TSC.166 |
| A.U8C.72 | merged into M.TSC.076, M.TSC.081, M.TSC.166 |
| A.U8C.73 | merged into M.TSC.076, M.TSC.166 |
| A.U8C.76 | merged into M.TSC.073 |
| A.U8C.84 | dropped (names `tests_hardware/conftest.py`, same basename; HW_BENCH) |
| A.U8C.86 | merged into M.TSC.076, M.TSC.166 |
| A.U8C.99 | merged into M.TSC.073 |
| A.U8C.101 | dropped (names `tests_hardware/conftest.py`, same basename; HW_BENCH) |
| A.U8C.112 | merged into M.TSC.021, M.TSC.121 |
| A.U8C.119 | dropped (names `tests_hardware/conftest.py`, same basename; HW_BENCH) |
| A.U8C.120 | merged into M.TSC.147 |
| A.U8C.121 | merged into M.TSC.121, M.TSC.147 |
| A.U8C2.16 | merged into M.TSC.096, M.TSC.119 |
| A.U8C2.18 | merged into M.TSC.121 |
| A.U8C2.20 | merged into M.TSC.108, M.TSC.138 |
| A.U8C2.21 | merged into M.TSC.121 |
| A.U8C2.25 | dropped (names `tests_hardware/conftest.py`, same basename; HW_BENCH) |
| A.U8C2.30 | merged into M.TSC.076, M.TSC.166 |
| A.U8C2.32 | merged into M.TSC.073 |
| A.U8C2.37 | dropped (names `tests_hardware/conftest.py`, same basename; HW_BENCH) |
| A.U8C2.47 | merged into M.TSC.121 |
| A.U8C2.51 | merged into M.TSC.147 |
| A.U9.01 | merged into M.TSC.159; its golden-file edit in `test_buildgen_definitions.py` dropped (A.U6.04 retires the golden files first, M.TSC.038) |
| A.U9.03 | merged into M.TSC.044 |
| A.U25.33 | merged into M.TSC.165 (gap pass G3) |
| A.U35.28 | merged into M.TSC.165 (gap pass G3) |
| A.U37.15 | merged into M.TSC.071, M.TSC.110, M.TSC.113 (gap pass G3) |
| A.U26.10 | merged into M.TSC.119 (gap pass G3) |
| A.C.17 | merged into M.TSC.119 (gap pass G3) |
| A.U21.26 | merged into M.TSC.126 (gap pass G3) |
| A.U21.27 | merged into M.TSC.126 (gap pass G3) |
| A.U24.68 | merged into M.TSC.213 (gap pass G3) |
| A.U26.80 | merged into M.TSC.226 (gap pass G3) |
| A.U19.16 | merged into M.TSC.227 (gap pass G3) |
