R2 phase A hand-back, written by the agent (Wed Nov  4 10:12 UTC 2026)

# R2 list: every test and tool file classified, with the proposals

Tree: `S/wt-r2`, branch `audit/r2`, at 8a32d826 (R1 complete); the base is `25caf528`. Read-only: git, grep and
reading only, nothing run, nothing edited. Counts are `git show HEAD:<path> | wc -l`; "new" means added after
`25caf528` (the unit is the commit that first added it, `git log --diff-filter=A`), "base" means it existed there
(8 of them under U10's names: `tests/test_asy_{api_response,base_classes,captive_dns,config_manager,crc_checks,
framing_codecs,print_log,system_service}.py`, `digital_twin/unixport/_unix_port_udp_addr_shim.py`,
`tests_js/vitest-commands.ts`).

Classes (PLAN R2): **P** pins a product property, kept; **O** a tool test or tool covered by an owner row or word,
kept, slimmed where it repeats itself; **A** audit machinery born in the audit, removed; **T** one of the eight
SPECIFICATION.md table pins; **H** harness, kept unless a lighter form does the same. **K** marks the files kept in
full by owner rule (section 2); they are counted apart. **owner** marks a row that needs the owner's word.

## 0. Totals

Files / lines per directory and class at 8a32d826 (654 files, 226,121 lines; 295 base-derived, 359 new):

| directory | all | P | O | T | H | A | K |
|---|---|---|---|---|---|---|---|
| `tests/` | 146 / 106,412 | 81 / 88,965 | 1 / 325 | | 62 / 14,812 | | 2 / 2,310 |
| `tests_scripts/` | 211 / 57,120 | 31 / 7,446 | 104 / 34,843 | 8 / 1,701 | 56 / 9,660 | 3 / 345 | 9 / 3,125 |
| `tests_js/` | 45 / 12,012 | 21 / 8,586 | 9 / 1,215 | | 15 / 2,211 | | |
| `tests_hardware/` | 169 / 25,998 | 128 / 17,856 | 6 / 420 | | 32 / 6,556 | | 3 / 1,166 |
| `digital_twin/` | 27 / 8,330 | | 2 / 159 | | 25 / 8,171 | | |
| `scripts/` | 45 / 12,185 | 1 / 2,431 | 22 / 3,469 | | 21 / 5,910 | | 1 / 375 |
| `toolchain/` | 3 / 3,031 | | 3 / 3,031 | | | | |
| `mockdata/` | 1 / 46 | | | | 1 / 46 | | |
| `.github/` | 7 / 987 | | 2 / 164 | | 5 / 823 | | |
| **all** | **654 / 226,121** | **262 / 125,284** | **149 / 43,626** | **8 / 1,701** | **217 / 48,189** | **3 / 345** | **15 / 6,976** |

What the proposals would remove (section 1.10 has one row per file; sections 3-5 the rest):

| proposal | files | lines or size |
|---|---|---|
| (A) whole files | 3 | 345 |
| check self-bites (OR21.a (2)) | 23 slimmed | 48 functions, 351 lines |
| Part N back to OR30.a's scope | SPEC + 204 tagged files | 1,081 of 1,278 rows, about 456 KB of SPECIFICATION.md's 1,590 KB; 1,127 `@tunable` lines (narrow reading of "hardware-tier budgets"; with the broad one 546 rows, about 241 KB, 570 tag lines: **owner**, row N3) |
| one port lock instead of three | 3 removed, 2 slimmed | 646 lines plus their share of `test_port_lock.py` |
| twin knobs read only by their own tests (carries) | 8 slimmed | measured in phase B |
| the 89 s retirement and the launcher stop file | 5 slimmed | about 30 lines of tool, 7 tests, 2 Part N rows |
| CI | `ci.yml` | the twin matrix 24 to 12 jobs (126 runner-min per run, R0's run); `unit-tests`/`unit-tests-gc-threshold` caps 175 to 95 min |

Rows marked **owner**: 4 (N3, C1 option (a), the carry "REPL banner", P-sleep). Whole-file removals are few because the
audit-born gates mostly carry an owner row (OR15.a, OR23.a, OR38.a, OR46.a/b, OR50.a, OR81.a, OR141.a, the review
page, CLAUDE.md); the volume is in Part N, the CI duplication and the slims.

## 1. The files

Base-derived files are grouped per directory and class (count, lines now, lines at `25caf528`). New files are named
one by one inside their class row as `` `name` lines (unit) ``. None of the grouped base files changed its purpose.

### 1.1 `tests/` (146 files, 106,412 lines)

| class | files | lines | which, and the basis |
|---|---|---|---|
| P base | 59 | 82,469 (55,786) | `test_asy_*.py` (28, the unit tests of `src/`), the 11 integration files `test_*_integration.py`, `test_digital_twin_{bmp3xx,fram,generic_wiring,isl29125,isl29125_autorange,network_neopixel,scd30,sensortask_integration,sgp40,uart_link}.py`, `test_math_helpers.py`, `test_voc_algorithm.py`, `test_ticks_rollover.py`, `test_machine_uart_link.py`, `test_reset_call_site_invariant.py`, `test_uart_comm_hazard.py`, `test_bus_hazard_generated.py`, and the scenario libraries `_sensortask_scenarios.py`, `_digital_twin_construction_scenarios.py`, `_bus_hazard_catalog.py` |
| P new | 22 | 6,496 | `_radio_shape_cases.json` 18 (U6), `_schema_cases.py` 94 (IN+LV; E.md keep), `lwip_host/test_modlwip_eagain.py` 463 (U21; the patch is the owner's, 2026-09-30), `lwip_host/test_modlwip_listener_close.py` 77 (F4a; owner 2026-10-26), `test_asy_webserver_connections.py` 1233 (U19; E.md keep), `test_digital_twin_clock_jump.py` 427 (U25; review `driven-time-and-rtc-steps` ok), `test_digital_twin_construction.py` 33 (U25), `test_digital_twin_fram_crash_points.py` 286 (U25; E.md keep), `test_digital_twin_held_i2c_line.py` 340 (CO4; E.md keep), `test_digital_twin_hot_replug.py` 247 (U25; owner 2026-07-13), `test_digital_twin_loop_end.py` 349 (F4b), `test_digital_twin_ntp.py` 587 (U25; review `twin-tolerates-ntp-offline` "change": the local responder and NTP tests), `test_digital_twin_setup_resets.py` 184 (CO4), `test_digital_twin_timer_pool.py` 245 (U25; E.md keep), `test_digital_twin_uart_comm_hazard.py` 216 (U25), `test_digital_twin_uart_field_sweep.py` 158 (U25), `test_digital_twin_wifi_modes.py` 332 (U22), `test_generated_boot_entry.py` 163 (U24), `test_readiness_gates.py` 382 (U10), `test_sensortask.py` 18 (U25), `test_uart_comm_cancel_sweep.py` 271 (U18), `voc_reference_vectors.py` 373 (U12) |
| O base | 1 | 325 (237) | `test_tmp_scratch.py`: CLAUDE.md's wear rule names it as the structural precedent |
| H base | 20 | 8,421 (3,861) | the fakes `machine.py`, `network.py`, `neopixel.py`; `microtest.py`, `_coverage_runner.py`, `_threshold_runner.py`, `_tmp_scratch.py`, `_boot_contiguity_probe.py`, `_fram_chip_fake.py`, `_shared_rest_roundtrip.py`, `_strict_json.py`, `_uart_comm_harness.py`, `_uart_link_contract.py`; twin self-tests `test_digital_twin_{http_client,launch,machine,machine_uart,poll_prewarm,run_generic_integration}.py`, `test_strict_json.py` |
| H new | 42 | 6,391 | `_async_harness.py` 295 (U24), `_boot_recorder.py` 141 (U20), `_cancel_sweep.py` 156 (U35), `_error_codes.py` 35 (U2), `_fake_time.py` 368 (U24; review `driven-time-and-rtc-steps` ok), `_fake_timer_arm.py` 20 (U24), `_fast_sleep.py` 70 (U24), `_fram_builders.py` 28 (U24), `_generated_module.py` 128 (U20), `_generated_tree.py` 82 (U24), `_littlefs_fake.py` 62 (U35), `_machine_contract.py` 164 (U24), `_mem_backup_contract.py` 82 (U25), `_ntp_frames.py` 53 (U24), `_port_bands.py` 73 (U25), `_protocols.py` 45 (U24), `_recording_print.py` 46 (U24), `_src_const.py` 102 (U24), `_src_schema.py` 21 (U27), `_stack_overflow.py` 15 (CRr1), `_task_names.py` 31 (U32), `_ticks30.py` 45 (U14), `_twin_devices.py` 173 (U25), `_twin_random.py` 50 (U24), `_twin_readiness.py` 29 (U25), `_uart_comm_hazard_common.py` 85 (U18), `_udp_port_redirect.py` 46 (U18), `_udp_step_fault.py` 86 (CO5), `_untraced.py` 29 (CE2r), `_write_counters.py` 69 (U4; CLAUDE.md wear counters), `rp2.py` 255 (U13; OR141.a (4)(g) unit fake), `test_async_harness.py` 420 (U24), `test_digital_twin_driven_clock.py` 287 (UM4), `test_digital_twin_rp2_constants.py` 78 (U25), `test_digital_twin_unix_port_idle_poll.py` 80 (CMr1f), `test_digital_twin_unix_port_unretrieved_report.py` 234 (U11), `test_driven_time.py` 646 (U35), `test_fakes.py` 691 (U24), `test_microtest_hooks.py` 135 (U24), `test_shared_helpers.py` 690 (U24), `test_untraced.py` 81 (CE2r), `test_write_counters.py` 165 (U4) |
| K | 2 | 2,310 | `test_bus_hazard_multi_device.py`, `test_digital_twin_bus_hazard_concurrency.py` (section 2) |

No pre-audit test function is lost here: the 20 scenarios of the deleted `tests/_webserver_concurrency_scenarios.py`
(866 lines) and the real-website file live on as named scenarios in `scripts/_digital_twin_scenarios.py` (checked name
by name); the per-device files became the `TEST_DEVICE` dispatchers.

### 1.2 `tests_scripts/` (211 files, 57,120 lines)

| class | files | lines | which, and the basis |
|---|---|---|---|
| O base | 36 | 20,344 (10,618) | the build chain under OR23.a: `test_build_firmware.py`, `test_build_frozen_html_sh.py`, `test_build_website_sh.py`, `test_buildgen_*.py` (16), `test_device_tomls.py`, `test_generate_sensortask_modules.py`, `test_strip_type_checking.py`, `test_measurement_field_tuple_agreement.py`, `test_js_coverage_{excludes_json,report_dir}.py`, `test_micropython_overrides.py`, `test_setup_toolchain_env.py`; the runners under OR15.a/OR37.a (2)/OR40.a (2)/CLAUDE.md: `test_test_sh.py`, `test_lint_sh.py`, `test_coverage_runner.py`, `test_threshold_runner.py`, `test_require_clean_hardware_run_sh.py`, `test_tests_hardware_persistence_write_gating.py`, `test_digital_twin_ci_suite_{ceiling,errcount,soak}.py` |
| O new | 68 | 14,499 | `_await_depth.py` 909 and `test_await_depth.py` 207 (U30; review `c-stack-reboot` ok, "a host test fails if the chain grows past a pinned depth"), `test_archive_evidence.py` 141 (U7; OR38.a (2)), `test_bench_control_restore.py` 237 (U26; CLAUDE.md B.13), `test_bench_device.py` 71 (U26; OR78.a), `test_bench_log_check.py` 426 (CRr2b; owner "no evidence to a bug ... is silently lost"), `test_board_image_fixture.py` 127 (U26; review `standard-board-state` ok), `test_build_device_websites_sh.py` 112 (U6; OR54.a (1)), `test_buildgen_error_contract.py` 573, `test_buildgen_fuzz.py` 194, `test_buildgen_locale.py` 50, `test_buildgen_reproducible.py` 71, `test_buildgen_source_agreement.py` 172 (U20; OR23.a, review `reproducible-image`), `test_buildgen_pico_gpio.py` 125 (U24), `test_buildgen_source_ast.py` 61 (U18), `test_ci_apt_cache.py` 407 (CI1; owner 2026-10-27 "Yes do it like you proposed"), `test_ci_workflow.py` 414 (U28; CLAUDE.md's `if: !cancelled()` rule), `test_code_conventions.py` 443 (U10 names, an owner foundation), `test_config_paths_resolve.py` 141 (U28; OR50.a (1)), `test_definitions_js_mirrors.py` 131 (U6; CLAUDE.md's src/js mirror obligation), `test_device_script_fram_regions.py` 208 (U26; CLAUDE.md FRAM caveat), `test_devices_sh.py` 78 (U27; owner 2026-10-23 device set), `test_digital_twin_ci_suite_state.py` 107 (U25; OR38.a (2)), `test_driver_shape.py` 180 (U15; CLAUDE.md Part C), `test_error_catalog.py` 921 (U3; OR28.a (2), decision 6), `test_evidence_snapshot.py` 68 (U26; CLAUDE.md FRAM rule), `test_exception_handler_contract.py` 744 (U11; owner 2026-11-02 20:30 "That's okay"), `test_fault_or_warning_never_both.py` 320 (U3; owner (e) 2026-11-03), `test_frozen_inputs_reproducible.py` 125 (U27; review `reproducible-image`), `test_hardware_runners.py` 426 (U7; OR45.a (2)(a)), `test_hardware_verdict.py` 298 (U7; OR21.a (3)), `test_host_cli_exit_idiom.py` 123 (U27; OR23.a (3)), `test_import_placement.py` 268 (U0; OR141.a (2)), `test_legacy_paths.py` 66 (U1; CLAUDE.md legacy rule), `test_lint_ceilings.py` 295 (U5; OR46.a/b), `test_lint_type_scopes.py` 179 (U27; CLAUDE.md's eight scopes), `test_live_command_device_args.py` 152 (U6; OR54.a (1)), `test_manual_runner_summary.py` 261 (U7; OR15.a (2)), `test_microtest.py` 335 (U7; OR15.a, CLAUDE.md hang cause #2), `test_mypy_any_baseline.py` 102 (U8; OR81.a), `test_no_variant_literals.py` 169 (U6; owner 2026-10-23, OR54.a (1)), `test_offline_ntp_config.py` 60 (U25; review `twin-tolerates-ntp-offline`), `test_port_lock.py` 531 (U24; OR38.a (3)), `test_pytest_run_record.py` 176 (U7; OR21.a (3)), `test_render_coverage_anchors.py` 45 (U18; OR23.a (2)), `test_repo_scan_regex_literals.py` 59 (N12), `test_repo_scan_template_literals.py` 84 (N13), `test_repo_scan_walk.py` 50 (U26) (PLAN R2: "the repo scanner's own tests"), `test_retry_counts.py` 134 (U29; owner 2026-10-20), `test_ruff_exemptions_live.py` 158 (U28; OR50.a (1)), `test_scd30_prerequisite.py` 130 (U26; CLAUDE.md wear gates, OR70.a (3)), `test_script_metadata_pins.py` 86 (U27; CLAUDE.md pins), `test_stage_website.py` 240 (U23; OR23.a, E.md keep), `test_stored_config_golden.py` 173 (U11; OR52.a (2)), `test_summary_block.py` 369 (U7; OR15.a (2)), `test_suppression_form.py` 160 (U28; OR83.a L44), `test_tests_hardware_collect_matrix.py` 141 (U26; OR16.a (2)), `test_tests_hardware_run_record.py` 90 (U7; OR21.a (3)), `test_tool_help.py` 127 (U7; OR15.a (1)), `test_tool_pins.py` 98 (U28; CLAUDE.md, review `stub-versions-pinned`), `test_twin_board.py` 281 (U26; review `twin-first-for-instruments` ok), `test_twin_runner_test_flags.py` 123 (U25; OR20, OR36), `test_typecheck_sh.py` 285 (U7; CLAUDE.md stub repairs), `test_uart_changelog.py` 263 (U17; CLAUDE.md UART rule), `test_uart_link_bench_only.py` 41 (U35; owner 2026-10-22), `test_uv_sync_retried_sh.py` 77 (U28; OR37.a (2)), `test_vendored_freezefs.py` 38 (U0), `test_vendored_microdot.py` 43 (U19) (CLAUDE.md vendoring, OR131.a) |
| P base | 6 | 2,110 (1,317) | `test_digital_twin_boot_contiguity.py` (CLAUDE.md, OR21.a (2)'s named control arm), `test_digital_twin_generated_boot.py`, `test_request_body_cap_headroom.py`, `test_request_timeout_ceiling.py`, `test_http_client_ceiling_close.py`, `test_ceiling_probe.py` |
| P new | 25 | 5,336 | `definitions_shape_cases.json` 78 (U6), `test_api_reference.py` 396 (U19), `test_config_schemas.py` 250 (U11), `test_const_mirrors.py` 161 (U24; holds the tests' UART wire-constant copies to the protocol, SPEC J), `test_counter_steps.py` 214 (U10; OR110.a (2)), `test_fatal_report_sites.py` 267 (U30; review `c-stack-reboot`), `test_firmware_write_sites.py` 240 (U35; E.md keep, OR42.a), `test_fram_chunk_crc_sites.py` 83 (U16; owner 2026-10-28 "keep it!"), `test_fram_chunk_owner_sites.py` 224 (U16; OR47), `test_fram_less_boot.py` 102 (U24), `test_frozen_first_shadowing.py` 46 (U25), `test_import_graph.py` 358 (U10; OR46.a (1)), `test_js_api_mirrors.py` 306 (U23; E.md keep), `test_radio_shape_corpus.py` 61 (U24), `test_readiness_gates.py` 201 (U10), `test_result_words.py` 98 (U19), `test_setter_contract.py` 267 (U10), `test_src_sleep_forms.py` 212 (U31; row P-sleep), `test_stripped_image_boots.py` 113 (U27; E.md keep), `test_task_tops.py` 299 (U32; legacy parity), `test_third_party_attribution.py` 132 (U34), `test_ticks_wrap_scan.py` 471 (U14), `test_watchdog_feed_sites.py` 402 (U10; OR31.a, E.md keep), `test_website_layering.py` 245 (U23), `test_website_tokens.py` 110 (U23) |
| T | 8 | 1,701 | section 1.9 |
| H base | 18 | 3,550 (1,797) | `conftest.py`, `_devices.py`, `_script_loader.py`, `_toml_fixtures.py`, `buildgen_fixtures/*.toml` (3), `test_bench_harness_helpers.py`, `test_bench_no_task_ended_completeness.py`, `test_bench_restores_serving.py`, `test_device_script_config_flush.py`, `test_device_script_gc_threshold.py`, `test_heap_map_parser.py`, `test_live_twin_ceiling_parser.py`, `test_resolve_board_device.py`, `test_setup_cross_browser_toolchain_sh.py`, `test_tests_hardware_conftest_constants.py`, `test_twin_never_needs_tests_on_its_path.py` |
| H new | 38 | 6,110 | `test_cross_browser_page_load_connections.py` 138 (U8), `test_cross_browser_smoke_probe.py` 230 (U6), `test_device_script_bench_facts.py` 164, `test_device_script_facts.py` 205, `test_device_script_rig_parking.py` 75, `test_device_script_watchdog.py` 122, `test_dns_probe.py` 46, `test_harness_mpremote_retry.py` 269, `test_http_client_shape_parity.py` 105, `test_rogue_udp_responder.py` 45, `test_script_loader_names.py` 29, `test_session_exit_guard.py` 56, `test_spoof_udp.py` 68, `test_tests_hardware_product_copies.py` 63 (all U26), `test_device_script_config_schemas.py` 265 (U11), `test_digital_twin_ci_suite_matrix.py` 128, `test_digital_twin_scenarios.py` 730, `test_isl29125_copies.py` 146, `test_port_bands.py` 169, `test_twin_entry_point_order.py` 150, `test_twin_fake_catalog.py` 74 (all U25), `test_fake_surface_conformance.py` 149, `test_generated_tree.py` 151, `test_ntp_generated_wiring.py` 58, `test_run_unix_port_integration_sh.py` 166 (all U24), `test_html_validate_config.py` 64 (U28; kept: its commit records a real miss, "an html-validate that never ran read as a pass"), `test_preview_server.py` 96 (U28), `test_js_generated_definitions_loader.py` 68 (U6), `test_mpremote_connect_sh.py` 82, `test_require_python.py` 143, `test_require_venv_sh.py` 77, `test_run_digital_twin_ci_sh.py` 184, `test_shell_conventions.py` 237, `test_unix_port_sh.py` 477 (all U27), `test_twin_host_isolation.py` 168 (N15), `test_twin_process_js_spawn.py` 121, `test_twin_process_spawn.py` 105 (U30), `test_twin_wiring_contract.py` 487 (U20) |
| A | 3 | 345 | section 1.10, rows A1-A3 |
| K | 9 | 3,125 | section 2 |

### 1.3 `tests_js/` (45 files, 12,012 lines)

| class | files | lines | which, and the basis |
|---|---|---|---|
| P base | 13 | 7,266 (3,979) | `app`, `definitions`, `definitions-mockdata-coverage`, `live-backend`, `live-backend-put-matrix`, `main`, `mock-server`, `mock-server-put-matrix`, `nav`, `poll-manager`, `render`, `templates` (`*.test.js`), `_put_field_cases.js` |
| P new | 8 | 1,320 | `_a11y_checks.js` 112, `accessibility.test.js` 216 (U23; E.md keep), `_expected_display.js` 45 (U23; OR19.a (2) independent oracle), `api-reference-agreement.test.js` 60 (U23), `definitions-shape-corpus.test.js` 9 (U6), `generated-definitions-render.test.js` 98 (U6), `shell.test.js` 592 (U23; review `website-unattended` ok), `site-functions.test.js` 188 (U23; OR48.a legacy parity, E.md keep) |
| O new | 9 | 1,215 | `_lint_command.js` 32, `lint-ceilings.test.js` 36 (U5; OR46.a), `_memory_markers.js` 174, `memory-markers.test.js` 101 (U7; CLAUDE.md four gates), `_summary_layout.js` 160, `_summary_reporter.js` 122, `summary-reporter.test.js` 107 (U7; OR15.a (2)), `_port_lock.js` 402, `port-lock.test.js` 81 (U24; OR38.a (3); row O-lock) |
| H base | 3 | 1,193 (718) | `_live_matrix_command.js`, `_live_twin_command.js`, `vitest-commands.ts` |
| H new | 12 | 1,018 | `_dom_helpers.js` 38, `_test_setup.js` 6, `_twin_process.js` 300 (U24), `_generated_definitions.js` 99, `mock-data-compose.test.js` 309 (U6), `_micropypath.js` 38, `micropypath.test.js` 29 (U27), `_source_constants.js` 60, `source-constants.test.js` 64, `expected-display.test.js` 40 (U23), `_twin_start_failure.js` 16, `twin-start-failure.test.js` 19 (U7) |

### 1.4 `tests_hardware/` (169 files, 25,998 lines)

| class | files | lines | which, and the basis |
|---|---|---|---|
| P base | 73 | 11,328 (9,220) | `bench/test_*.py` (10), `flash/test_*.py` (9), `manual/manual_*.py` (5), `device_scripts/*.py` (49 base scripts, the bus-concurrency and same-device scripts among them) |
| P new | 55 | 6,528 | bench: `test_boot_order_and_triggers.py` 156, `test_modlwip_send_stall.py` 265, `test_reset_reasons.py` 243, `test_scd30_frc_readiness_baseline.py` 76, `test_system_commands_over_rest.py` 230, `test_ticks_ms_rollover.py` 104 (owner 2026-10-01), `test_uart_link_crc16.py` 101 (owner 2026-09-30), `test_wifi_radio_reinit.py` 34; flash: `test_chip_conformance.py` 184, `test_config_float_round_trip.py` 30, `test_heap_layout.py` 85, `test_modlwip_listener_close.py` 97, `test_system_commands.py` 288, `test_unretrieved_task_exception_handler.py` 44; device scripts: `bmp3xx_alone_survives_a_general_call.py` 90, `bmp3xx_conformance_probe.py` 104, `c_stack_budget.py` 111, `config_files_dump.py` 36, `config_files_restore.py` 36, `config_float_round_trip.py` 85, `flash_write_loop_gap.py` 63, `fram_command_hold_timing.py` 72, `fram_conformance_probe.py` 121, `fram_raw_dump.py` 64, `i2c_held_sda_recovery.py` 148, `listener_close_leaves_the_pcb_pools.py` 186, `loop_lag_under_combined_load.py` 134, `loop_stretch_timing.py` 109, `reboot_fallback_starves_the_watchdog.py` 76, `reset_code_{boot_phase_hang,command_incomplete,invalid_record,loop_end,stack_exhausted}.py` 67/98/64/45/110, `scd30_{argument_reaction,conformance_probe,data_ready_wait,measurement_interval_read,start_continuous_measurement}.py` 170/130/53/39/48, `setup_resets_each_chip_once.py` 83, `sgp40_{conformance_probe,same_device_concurrent_sessions,sample_cadence}.py` 73/53/117, `system_command_{config_reset,fram_erase,hang,reboot}.py` 91/207/95/159, `uart_comm_hazards.py` 276, `uart_dma_ring_interrupts_off.py` 435 (OR141.a (4)(g)), `uart_driver_read_never_blocks_the_loop.py` 223 (G12), `uart_link_echo_under_serving_load.py` 124, `unretrieved_task_exception_handler.py` 219, `wifi_country_code_reaction.py` 68, `wifi_radio_reinit_recovery.py` 74; `plausibility_bounds.py` 35 (OR29.a (4)) |
| O new | 6 | 420 | `twin_board.py` 143, `conformance.py` 83 (review `twin-first-for-instruments`, OR29.a (4)), `evidence.py` 61 (CLAUDE.md FRAM rule), `heap_bounds.py` 7 (review `heap-floors-kept`), `scd30_prerequisite.py` 74 (CLAUDE.md wear gates), `device_scripts/system_debug_level_set_standard.py` 52 (review `standard-board-state`) (all U26) |
| H base | 14 | 5,100 (3,203) | `README.md`, `harness.py`, `conftest.py`, `flash/conftest.py`, `bench_control.py`, `error_log_helpers.py`, `heap_map.py`, `http_client.py`, `ntp_probe.py`, `rogue_udp_responder.py`, `website_identity.py`, `bench/dns_probe.py`, `manual/runner.py`, `manual/__main__.py` |
| H new | 18 | 1,456 | `bench/_load.py` 488, `bench/conftest.py` 201, `bench_facts.py` 152, `device_scripts/bench_facts.pyi` 70, `device_scripts/_shared/` (9 files: `bus_reader_loops.py` 183, `heap_probe.py` 71, `watchdog.py` 38, `settle.py` 32, `facts.py` 20, `isl_error_log.py` 20, `fixed_source.py` 15, `map_dump.py` 11, `__init__.py` 0), `kick_then_reset.py` 25, `markers.py` 36, `soak_durations.py` 7, `spoof_udp.py` 63 (all U26), `device_scripts/_bench_device.pyi` 24 (U15) |
| K | 3 | 1,166 | `flash/test_bus_concurrency.py`, `bench/test_bus_concurrency_under_api_load.py`, `device_scripts/bus_topology_autodetect_and_hazard_sweep.py` |

The deleted base scripts (`wifi_*_repro.py`, U5; `wifi_country_hostname_edge_values.py`, `system_debug_level_*`,
`isl29125_conformance.py`, `soak_tiers.py`, U26) were diagnostics ("NOT part of the routine test suite") or have a
successor named above; no pre-audit test function is lost.

### 1.5 `digital_twin/` (27 files, 8,330 lines)

| class | files | lines | which, and the basis |
|---|---|---|---|
| H base | 17 | 7,158 (4,317) | `README.md`, `machine.py`, `network.py`, `neopixel.py`, the chip fakes `_bmp3xx_chip.py`, `_fram_chip.py`, `_isl29125_chip.py`, `_scd30_chip.py`, `_sgp40_chip.py`, `_crc8.py`, `_fault_injection.py`, `_http_client.py`, `launch.py`, `run_generic_integration.py`, `unix_port_poll_prewarm.py`, `unixport/_unix_port_udp_addr_shim.py`, `typecheck.ini` |
| H new | 8 | 1,013 | `_driven_clock.py` 190 (UM4), `_flash_stall.py` 126 (U25; OR141.a (4)(g)), `_twin_common.py` 126 (U5), `_wall_clock.py` 82 (U25), `rp2.py` 259 (U13), `run_device_script.py` 149 (U26; review `twin-first-for-instruments`), `unix_port_idle_poll.py` 43 (CMr1e), `unix_port_unretrieved_report.py` 38 (U11) |
| O new | 2 | 159 | `unixport/_ntp_responder.py` 121, `unixport/_offline_ntp_config.py` 38 (U25; review `twin-tolerates-ntp-offline` "change", 2026-10-02) |

### 1.6 `scripts/` (45 files, 12,185 lines)

| class | files | lines | which, and the basis |
|---|---|---|---|
| O base | 7 | 950 (615) | the build chain (OR23.a): `build_firmware.py`, `build_frozen_html.sh`, `build_website.sh`, `_generate_sensortask_modules.py`, `_strip_type_checking.py`, `_render_coverage.py` (OR23.a (2)); `_require_clean_hardware_run.sh` (CLAUDE.md wear rule) |
| O new | 15 | 2,519 | `_archive_evidence.py` 112 (U7; OR38.a (2)), `_hardware_verdict.py` 157, `_pytest_run_record.py` 124 (U7; OR21.a (3)), `_run_lower_levels.sh` 50 (U7; OR45.a (2)(a)), `_summary_block.py` 256, `_summary_block.sh` 163 (U7; OR15.a (2)), `_port_lock.sh` 107 (U24), `_port_lock.py` 163 (U27) (OR38.a (3); row O-lock), `_devices.sh` 38 (U27; owner 2026-10-23), `_stage_website.py` 500 (U23; E.md keep), `build_device_websites.sh` 73 (U6; OR54.a (1)), `ci_apt_cache.py` 466 (CI1; owner 2026-10-27), `record_twin_instrument_runs.py` 231 (U26; review `twin-first-for-instruments`, PLAN R3 re-records), `run_bench_rollover_test.sh` 51 (U27; owner 2026-10-01), `uv_sync_retried.sh` 28 (U28; CLAUDE.md, OR37.a (2)) |
| P new | 1 | 2,431 | `_digital_twin_scenarios.py` (U25): the L2 scenarios, 67, the pre-audit webserver concurrency set among them |
| H base | 13 | 4,783 (2,836) | `test.sh`, `lint.sh`, `typecheck.sh`, `_digital_twin_ci_suite.py`, `run_digital_twin_ci.sh`, `run_unix_port_integration.sh`, `run_{bench_hardware_suite,bench_soak_tests,flash_hardware_suite,manual_hardware_tests}.sh`, `mpremote_connect.sh`, `cross_browser_smoke.mjs`, `setup_cross_browser_toolchain.sh` |
| H new | 8 | 1,127 | `_twin_process.py` 485 (U25), `_unix_port.sh` 315, `_require_python.sh` 19, `_require_venv.sh` 27, `micropypath.toml` 5 (U27), `_cross_browser_probe.mjs` 73 (U6), `_page_load_connections.mjs` 129 (U8), `preview_server.py` 74 (U28) |
| K | 1 | 375 | `_check_gc_collect_sites.py` (section 2) |

### 1.7 `toolchain/`, `mockdata/`, `.github/`

| class | files | lines | which, and the basis |
|---|---|---|---|
| O base (`toolchain/`) | 3 | 3,031 (1,689) | `setup_toolchain.py`, `micropython_overrides.py`, `versions.toml`: OR23.a's build chain; the overrides' patches are owner decisions except the third modlwip patch (agent, under the owner's ruling, E.md) |
| H new (`mockdata/`) | 1 | 46 | `samples.json` (U6, an owner foundation; replaced the base `dev.json`/`wozi.json`) |
| H base (`.github/`) | 3 | 728 (690) | `workflows/ci.yml`, `actions/setup-micropython-toolchain/action.yml`, `zizmor.yml` (section 4) |
| H new (`.github/`) | 2 | 95 | `actions/uv-sync/action.yml` 18 (U28; CLAUDE.md retried sync), `actions/playwright-chromium/action.yml` 77 (CI1) |
| O new (`.github/`) | 2 | 164 | `actions/apt-cache-restore/action.yml` 125, `actions/apt-cache-save/action.yml` 39 (CI1; owner 2026-10-27, "Yes do it like you proposed"; the slow-mirror fault actions/runner-images#14823) |

### 1.8 Read-only notes on the O and H rows

- The large tool tests stay O; "slimmed where it repeats itself" is not proven from names alone, so they are named for
  phase B to read, not proposed: `test_test_sh.py` 2,530 (155 tests for a 1,231-line runner), `test_micropython_overrides.py`
  2,126 (1,115), `test_setup_toolchain_env.py` 2,021 (1,850), the five `test_digital_twin_ci_suite_*.py` 1,918 (1,955),
  `tests/test_digital_twin_run_generic_integration.py` 1,220 (base 290), `tests/test_digital_twin_machine.py` 1,770
  (base 539). Groups seen in `test_test_sh.py`'s names that phase B checks first: the speed bands (12 tests; their five
  Part N values all read "calibration owed"), the GitHub annotations (10), the per-file twin-host isolation (6, next to
  `test_twin_host_isolation.py`), the memory-gate wording (6, next to K's `test_memory_error_gate_agreement.py`), and the
  scenario jobs (8, which go with C1 option (a)).
- `tests/test_shared_helpers.py` (690) says of itself "the shared test doubles and readers no consumer test pins yet";
  its DrivenTime cases sit beside `tests/test_driven_time.py` (646). Phase B reads both for overlap; no proposal here.
- The summary block has three emitters (sh, py, js) held byte-identical: OR15.a (2) needs one block per runner in
  three runtimes, so they stay; a single emitter is a design change, not proposed.

### 1.9 The eight table pins (T)

| file | lines | tests | what it checks; proposal |
|---|---|---|---|
| `test_tunables_register.py` | 371 | 19 | OR30.a (2), the owner's row: tag and row agree (2 tests on the tree) and four relations, product properties (`wdt.timeout_ms` ≤ 8388, the reset delay and supervisor scan under the watchdog, a page load within the ceiling). Keep those 6; the 13 fabricated-input checker tests shrink to OR30.a (2)'s three failures (unlisted, untagged, number differs) when Part N shrinks (section 5) |
| `test_lock_order.py` | 367 | 10 | product: a lower lock never taken before a higher one (deadlock order), through C.8's table. Keep; the table's completeness half stays because the order check needs every lock levelled |
| `test_timing_budget.py` | 262 | 7 | product: F.3's code-derived timing rows recomputed from the code (the reset delay against the watchdog among them). Keep the tree test; its 6 bite tests go with section 1.10's S rows |
| `test_level_containment.py` | 182 | 7 | OR45.a (2)(b)/(3), the owner's row: every twin scenario has a hardware counterpart or an exception row. Keep |
| `test_memory_catalog.py` | 175 | 5 | product: no unlisted long-lived run-phase allocation (OR110.a, CLAUDE.md's memory rule). Keep |
| `test_task_inventory.py` | 139 | 6 | product: every task is a starter's (supervised) or a tabled row. Keep |
| `test_threat_model_statement.py` | 120 | 4 | A.11 names every unauthenticated write (review `threat-model-table` ok, OR52.a (3)). Keep the 3 tree tests; the bite goes (S rows) |
| `test_toml_schema_contract.py` | 85 | 3 | L.3's key table equals what the build accepts (the TOML author's reference). Keep |

### 1.10 Proposed removals and slims, one row each

Proof for every (A) row: `git grep -l <name> HEAD -- ':!arduino'` finds, outside `audit/` (audit machinery), only the
docs lines named in the row; no test, runner, CI step or import reads the file.

| # | path | lines | class | proposal | basis | proof / readers | left once it goes |
|---|---|---|---|---|---|---|---|
| A1 | `tests_scripts/test_hardware_clones.py` | 41 | A | remove | none found (U26 `0c0ad52c`, no owner row or word; no observed failure in its commit) | `tests_hardware/README.md:560` (a table row naming it) | the README rule as text; its one bite test goes with it |
| A2 | `tests_scripts/test_host_annotations.py` | 181 | A | remove | none found (U20 `f76385a6`) | `SPECIFICATION.md:11188-11190`, `BACKLOG.md:801`, `:817` | `requires-python >= 3.11` (pyproject.toml); a runtime-evaluated TYPE_CHECKING name is ruff TC004's (select ALL): phase B confirms TC004 fires on one before the removal |
| A3 | `tests_scripts/test_host_text_encoding.py` | 123 | A | remove | none found (U27 `15b8633c`); its reason is a chroot without a UTF-8 locale (`BACKLOG.md:987`), while CLAUDE.md's chroot recipe sets `LANG=C.UTF-8` | `BACKLOG.md:987` | `test_buildgen_locale.py` (OR23.a: the whole build under a non-UTF-8 locale) |
| S | the 23 files of appendix S | 351 of them | O/P/H/T | remove the check self-bite tests (functions named `*_bites`) | OR21.a (2), 2026-09-25: "Not adopted: no new permanent control arms in CI — the sensitivity proof is done once in the audit; existing control arms (e.g. `test_digital_twin_boot_contiguity.py`) are left as they are"; owner 2026-10-23: "Planting errors for those straightforward tests would be complete overkill" | each is read only by pytest collection | every check still runs on the real tree; R3 triggers a changed check once (PLAN R3, OR21.a). Excluded: K's `test_persistence_write_marker_completeness.py` (2 bites) and the named arm in `test_digital_twin_boot_contiguity.py` |
| O-lock-1 | `scripts/_port_lock.py` | 163 | O | remove: the CPython callers (`_digital_twin_ci_suite.py:35`, `_digital_twin_scenarios.py:33`) take the lock their shell launcher (`run_digital_twin_ci.sh`, `test.sh`) already holds and hands down | OR38.a (3) asks for one lock per product-fixed port ("used by one tier at a time under a lock"), not three; owner 2026-11-03 "Generally target low complexity" | readers: the two callers, `test_port_lock.py`, `pyproject.toml` | `scripts/_port_lock.sh`, one implementation |
| O-lock-2 | `tests_js/_port_lock.js` | 402 | O | remove: npm's live tiers take the lock through the shell library (a wrapper), as the Python runners do | as O-lock-1 | readers: `vitest.config.js:23`, `tests_js/_twin_process.js`, `scripts/cross_browser_smoke.mjs`, `vitest-commands.ts`, the eslint/ts configs | as O-lock-1 |
| O-lock-3 | `tests_js/port-lock.test.js` | 81 | O | remove with O-lock-2 | as O-lock-1 | collection only | the shell lock's tests in `test_port_lock.py` |
| O-lock-4 | `tests_scripts/test_port_lock.py` | 531 | O | slim: drop the CPython reader's cases | as O-lock-1 | collection only | the shell lock's contract tests |
| O-lock-5 | `tests_scripts/test_twin_process_js_spawn.py` | 121 | H | slim: drop the port-lock cases, if any, with O-lock-2 (phase B reads) | as O-lock-1 | collection only | spawn's interning refusal tests |
| W1 | `scripts/_digital_twin_scenarios.py` | 2,431 | P | slim: `_SHARED_BOOT_DEADLINE_S` 89.0 and `_SHARED_BOOT_BUDGET_S` 30.0 (`:93-96`), the retirement (`:364`, `:425`) and the deadline failure (`:405-406`) give way to the idle event (section 3.2) | DECREV 3.2 on the owner's "hardcoded delay checks like this are a very bad, very awkward pattern" (2026-10-28); PLAN R2 | `tests_scripts/test_digital_twin_scenarios.py:674`, `:689`, `:702`; Part N `l2.scenario_shared_boot_deadline_s`, `l2.scenario_shared_boot_budget_s` | boot sharing (kept); the idle check naming SGP40's W35 as the boot's own |
| W2 | `tests_scripts/test_digital_twin_scenarios.py` | 730 | H | slim: its three clocked-stub tests of W1's deadline (`:674`, `:689`, `:702`) become one test of the idle event | as W1 | collection only | the frame's other tests |
| W3 | `scripts/_twin_process.py` | 485 | H | slim: the stop-file ownership (`stop_file` field `:86-93`, touch and DIAG fallback `:395-404`, the `--stop-file` refusal `:427-447`), about 15 lines; `shutdown()` ends by SIGINT as before | DECREV 3.3: added for a twin hang "reproduced 0 times in about 1,900 tries" (OF-215); PLAN R2 "the launcher stop file ... go" | `_digital_twin_ci_suite.py:398-402` (the "never acted on its stop file" failure) | the runner's own `--stop-file` option (older, U18/U25, stays per DECREV) |
| W4 | `tests_scripts/test_digital_twin_ci_suite_errcount.py` | 1,120 | O | slim: the stop-file fixture and 4 tests (`:724-811`) go with W3 | as W3 | collection only | the suite's errcount tests |
| W5 | `scripts/_digital_twin_ci_suite.py` | 1,955 | H | slim: the stop-file check `:398-402` goes with W3 | as W3 | — | the SIGINT shutdown checks |
| N-knob-1 | `digital_twin/_bmp3xx_chip.py` | 209 | H | slim: `fatal_err` and the EVENT model, which no driver reads since B4 | OR20 (2026-09-25): "Try to avoid putting test code inside the digital twin ... Only if there is no alternative, and keep tiny anyway"; CARRY_LATER (B4) | readers: `tests/test_digital_twin_bmp3xx.py` (its self-test) and `tests/test_asy_bmp3xx_driver.py` (phase B checks whether that unit test reads the twin knob or the unit fake's) | the chip fake |
| N-knob-2 | `digital_twin/_scd30_chip.py` | 320 | H | slim: `rdy_stuck_high` | as N-knob-1 | `tests/test_digital_twin_scd30.py` only | the chip fake |
| N-knob-3 | `digital_twin/neopixel.py` | 70 | H | slim: `power_dip()`, `displayed()`, `raise_on_write` | as N-knob-1; CARRY_LATER (B7) | `tests/test_digital_twin_network_neopixel.py`, `digital_twin/README.md` (the unit fake `tests/neopixel.py`'s own `raise_on_write` stays: product unit tests read it) | the pixel fake |
| N-knob-4 | `tests/_fram_chip_fake.py` | 179 | H | slim: the `silent` knob | as N-knob-1; B3 hand-back ("keeps one reader, the fake's own test in `test_asy_system_service.py`") | phase B re-reads: `silent` is a common word, 13 files match it | the fake |
| N-knob-5 | `tests/test_digital_twin_bmp3xx.py`, `test_digital_twin_scd30.py`, `test_digital_twin_network_neopixel.py`, `tests/test_asy_system_service.py` | 350 / 910 / 617 / 4,356 | P/H | slim: the self-tests of N-knob-1..4 go with them | as N-knob-1 | collection only | the files' product tests |
| P-sleep | `tests_scripts/test_src_sleep_forms.py` | 212 | P | **owner**: narrow to waits in loops | DECREV 3.2 "whole-millisecond waits extended to one-off sleeps | the rule only where it matters (waits in loops)" is the lead's, no owner word; it changes a product test's goal | — | the rule for waits in loops |

Appendix S, the self-bite functions (file, functions, lines): `test_error_catalog.py` 12/76,
`test_buildgen_definitions.py` 2/40, `test_timing_budget.py` 6/36, `test_js_api_mirrors.py` 3/30 (DECREV 3.3's
planted mismatches), `test_shell_conventions.py` 1/30, `test_fram_chunk_owner_sites.py` 4/19,
`test_device_script_facts.py` 2/18, `test_website_layering.py` 2/17, `test_device_script_config_flush.py` 1/10,
`test_device_script_bench_facts.py` 1/8, `test_device_script_watchdog.py` 1/8, `test_device_script_fram_regions.py`
2/7, `test_js_generated_definitions_loader.py` 1/7, `test_build_device_websites_sh.py` 1/6,
`test_fault_or_warning_never_both.py` 1/6, `test_src_sleep_forms.py` 1/6, `test_host_cli_exit_idiom.py` 1/5,
`test_lint_type_scopes.py` 1/5, `test_website_tokens.py` 1/5, `test_fram_chunk_crc_sites.py` 1/4,
`test_tests_hardware_product_copies.py` 1/4, `test_device_script_rig_parking.py` 1/2,
`test_threat_model_statement.py` 1/2 (all in `tests_scripts/`). Tests that plant a fault into the product or a fake
(`tests/test_asy_fram_manager.py`, `tests/test_write_counters.py` and the like) are product or harness tests, not
self-bites, and stay.

## 2. Kept in full by owner rule (K)

| rule | files | lines |
|---|---|---|
| comment-cap gate | `tests_scripts/test_comment_block_cap.py` | 360 |
| gc-site checker | `tests_scripts/test_gc_collect_sites.py`, `scripts/_check_gc_collect_sites.py` | 385 + 375 |
| memory-gate agreement | `tests_scripts/test_memory_error_gate_agreement.py` | 122 |
| persistence-marker completeness | `tests_scripts/test_persistence_write_marker_completeness.py` | 866 |
| four-tier bus hazard | `tests/test_bus_hazard_multi_device.py`, `tests/test_digital_twin_bus_hazard_concurrency.py`, `tests_hardware/flash/test_bus_concurrency.py`, `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py`, `tests_hardware/bench/test_bus_concurrency_under_api_load.py` (their helpers `_bus_hazard_catalog.py`, `test_bus_hazard_generated.py` and the bus-concurrency device scripts are P and untouched) | 1,064 + 1,246 + 405 + 195 + 566 |
| decision records (clarification (i), owner 2026-11-03: "Option A, this is valuable for future sessions as well") | `tests_scripts/test_citations.py`, `test_decision_vocabulary.py`, `_citation_allowlist.txt` (89), `_decision_vocab_allowlist.txt` (392), `_repo_scan.py` (the shared walk); the allow-lists only shrink | 392 + 146 + 89 + 392 + 373 |

## 3. Waits, the shared twin, the stop file, the rig override

### 3.1 The seven fixed sleeps (OR37.a (3), owner "yes, all exactly like this"; DR7 family E1)

Each value becomes the backstop of a bounded poll or an event wait; the assertion stays.

| # | Part N row, site | value | the sleep is followed by | wait instead for |
|---|---|---|---|---|
| 1 | `l1.asy_webserver_service_admit_settle_s`, `tests/test_asy_webserver_service.py:2176` | 0.01 s | `assert await service._open_conns.get_value() == 2` | that counter reaching 2 (poll; the file has `_CLOSE_POLL_*`) |
| 2 | `l1.asy_uart_comm_inside_lock_ms`, `tests/test_asy_uart_comm.py:1638`, `:3129` | 5 ms | `:3129` asserts `bus.session_lock.locked()`; `:1638` calls `clear()` once the holder is "inside" | `bus.session_lock.locked()` true (both sites) |
| 3 | `l1.uart_comm_hazard_in_flight_ms`, `tests/test_uart_comm_hazard.py:521`, `:658` | 2 ms | a second `uart_get()` refused / `clear()` racing the transfer | the initiator's session lock held by the first transaction |
| 4 | `l1.captive_dns_bind_wait_ms`, `tests/test_asy_captive_dns.py:915`, `:1140`, `:1172` | 50 ms | `:1141` asserts `server._udps._sock is not None`, then queries | `server._udps._sock is not None` (the bind done) |
| 5 | `l1.asy_ntp_client_reply_process_s`, `tests/test_asy_ntp_client.py:2818` | 0.2 s | `ntp_issynced()` read as False after a garbage reply | the attempt's end: the failure's log entry or the retry armed (the file polls the retry with `l1.asy_ntp_client_retry_armed_poll_tries`) |
| 6 | `l2.run_generic_integration_reach_ms`, `tests/test_digital_twin_run_generic_integration.py:608` (and `:674`) | 5 ms | `:609` asserts `said == ["ENTRY_HELD"]` and the held write not done; `:674` starts a stall once the lag probe runs | `said == ["ENTRY_HELD"]`; at `:674` the probe's first sample |
| 7 | `l2.run_generic_integration_slot_reach_ms`, same file `:871` | 1 ms | `assert booted.webserver.closed == 1 and not closing.done()` | `booted.webserver.closed == 1` |

### 3.2 The shared twin's 89 s retirement

`scripts/_digital_twin_scenarios.py:93-96` (`_SHARED_BOOT_DEADLINE_S = 89.0`, `_SHARED_BOOT_BUDGET_S = 30.0`), read at
`:364`, `:405-406` and `:425`; pinned by `tests_scripts/test_digital_twin_scenarios.py:674`, `:689`, `:702`; Part N rows
`l2.scenario_shared_boot_deadline_s`, `l2.scenario_shared_boot_budget_s`. The 89 s is "60 x BackupPeriod + WaitTimeNTP
- 1" read cycles, the earliest time of the boot's first untimestamped SGP40 backup; an idle dev twin measured that
event at +94.0 s and +155.1 s (DR5 D2). The idle event: on a shared boot that never syncs NTP, the idle check names
SGP40's W35 ("backup written without a timestamp", `buildgen/error_catalog.json`) as the boot's own move, so no
deadline, budget or age retirement remains (rows W1, W2).

### 3.3 The launcher stop file and the rig override

- Stop file: written by `scripts/_twin_process.py` (`spawn()` hands `--stop-file <state>/stop` to the runner,
  `shutdown()` touches it and falls back to SIGINT with a DIAG line); read by the runner
  `digital_twin/run_generic_integration.py:554-570` (`_serve_until`, its `--stop-file` option, which stays) and checked
  by `scripts/_digital_twin_ci_suite.py:398-402`; pinned by `test_digital_twin_ci_suite_errcount.py:724-811`. Rows
  W3-W5.
- Rig override (DECREV 3.3 / DR5 D7, OF-224, the stale parse-tree root): **not in the tree**. No override for it was
  ever added (`git log -S OF-224` finds two commits, U30 and U32, and no file outside `audit/` names it at head; `toolchain/micropython_overrides.py` holds
  `unix_kbd_intr`, `unix_gc_stack`, `lwip_connection_counts`, `modlwip_eagain`, `unix_lwip_host`, `tick_offset`).
  Nothing reads it; what is left is records only (OF-223/OF-224 close). The one test-rig override that does exist is
  `unix_gc_stack` (SPEC B.14.6, U30 `06a8ae5d`, "time only, the firmware keeps 64"), read by the Unix-port builds and
  `l1.unix_gc_stack_entries`; it is not the DECREV item and is not proposed.

## 4. CI

### 4.1 Timeouts against measured need

Measured: R0's full run (`c901f111`, run 41512927022, 2026-11-02, `S/u35r/r0/ci/jobs.tsv`) and Part N's 2026-10-20
runs. Rule stated (N.1 and B.10.1, kept): a cap is the slowest measured run plus the largest single retry budget it
must contain, plus 25 %, at least 5 min. Margins are against R0's run.

| job | `timeout-minutes` | measured | margin now | proposal |
|---|---|---|---|---|
| web-changes, devices, web-lint-and-typecheck, lint-and-typecheck, shellcheck, actionlint, zizmor | 5 each | 0:09-0:40 | 7-33× | keep (the 5-min floor) |
| web-unit-tests | 20 | 3:25 (cold 7.1 with the toolchain build) | 2.8× cold | keep |
| web-put-matrix (3 shards) | 15 | 5:04-5:17 (cold 8.9) | 1.7× cold | keep |
| web-coverage | 20 | 3:37 | 5.5× | keep |
| web-cross-browser-smoke | 15 | 5:57 (cold 10.1) | 1.5× cold | keep |
| unit-tests | 175 | 11:55 (8.9-10.4 on 2026-10-20) | 175 = warm + one hung scenario job's 3 × 2,555 s (128 min) + 25 % | **95**: `runner.scenarios_timeout_s` 2,555 → 1,050 s (2× the slowest CI scenario job, 511 s; 2.65× the standalone local run, 396 s), so the largest budget becomes the backgrounded `tests_scripts/` tier's 3 × 1,200 s = 60 min: (13 + 60) × 1.25 = 91, rounded to 95. The bench Pi4's in-suite scenario time is unmeasured (N.1's slowest host): measure in phase B before the change |
| unit-tests-gc-threshold | 175 | 12:46 | as above | **95**, as unit-tests |
| unit-tests-coverage | 95 | 16:54 (11.7-14.2 on 2026-10-20) | (17 + 60) × 1.25 = 96 | keep 95 (or 100 for the 25 % to hold exactly) |
| digital-twin-e2e (each leg) | 20 | 8:39-12:46 | 1.57× + its longest single wait (2 min) | keep |
| firmware-build-verify (6) | 20 | 1:37-2:04, + the ARM apt step's worst 10.5 min | 1.6× with the apt worst case | keep |

The two retries stay: `runner.per_file_attempts` = 3 (two retries on a timeout only; owner 2026-09-26 and 2026-10-20)
and the three-attempt `uv sync` (`scripts/uv_sync_retried.sh`, CLAUDE.md, OR37.a (2)). The hang backstop stays as
CLAUDE.md states it (per-file timeout and retry, `stdbuf -oL -eL`, `needs: lint-and-typecheck` with
`if: ${{ !cancelled() }}`; `digital-twin-e2e` stays success-gated). With 95 min a hung scenario job is named after
53 min instead of 128.

### 4.2 The twin matrix

Now: 6 devices × 2 GC stages × 2 parts (suite, harness) = 24 jobs, 238 runner-min of R0's 322 (suite legs 112.4,
harness legs 126.0; slowest leg 12:46). It must cover every device (owner, 2026-10-23: "Single device tests with
different wiring should actually be avoided, so these tests should go for all devices."; OR16.a (1)) at both GC
stages (CLAUDE.md's four gates, OR40.a (2)). The part is a wall-clock split, not a coverage dimension.

Finding: the harness part repeats what `unit-tests` already runs. `scripts/test.sh:675-680` runs
`_digital_twin_scenarios.py` for every derived device at its job's GC stage with `--shared-port-53`, which deselects
only the scenarios needing port 53 exclusively; `run_digital_twin_ci.sh --part harness` runs the same harness with
`--exclusive-port-53`. Of the 67 scenarios one needs the exclusive port
(`wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server`), so 66 run twice per device and stage.

- **C1, option (b), proposed:** the harness part runs only the exclusive-port-53 scenarios, inside the suite job;
  the matrix becomes 6 × 2 = 12 jobs (the per-device rule and both stages kept), about 110-120 runner-min less per run (R0's run), the
  critical path unchanged (the suite leg's 10.5 min plus one scenario).
- **C1, option (a), owner:** `scripts/test.sh` drops its scenario jobs (they are L2, OR45.a's ladder puts them in the
  twin tier) and the twin job's harness part stays as now. It shortens `test.sh` and its tests (about 8 in
  `test_test_sh.py`) but changes what the owner's everyday local `scripts/test.sh` covers, so it needs their word.

## 5. Part N

### 5.1 Scope, row by row in groups

OR30.a (1), 2026-09-25: "every tuned (not derived) value that must be retuned as the project changes: test-suite
values (CI `timeout-minutes` ...; per-file timeouts and retries; Unix-port `-X heapsize`; twin run and soak durations;
hardware-tier budgets) and firmware/build-time values of the same kind (watchdog timeout, NTP retry/backoff,
notification timing, buildgen validation thresholds); contract constants (UART wire constants, FRAM layout) are
excluded." Part N's own N.1 classes (derived, fact, config, test input: not tagged) apply on top. Rows counted from the
register between the markers (1,278 ID rows, 9 rule rows); "tags" are `@tunable` lines in code.

| # | table | rows | in | out | why out (the row's own words) |
|---|---|---|---|---|---|
| N1 | Firmware | 115 | 107 | 8 | facts or derived, N.1's own untagged classes: `uart.flash_hold_max_ms` (datasheet tSE/tPP), `i2c.clear_half_period_us` (datasheet SCD30 100 kHz), `spi.cs_settle_us` (datasheet tCSU/tCSH), `bmp3xx.reset_settle_ms` (Bosch's reference wait), `uart.chunk_bytes` ("the webserver's piece size ... reused"), `uart.hazard_{quiet_timeouts,window_timeouts,recovery_attempts}` (derived from the peer's budgets and a bench script's value) |
| N2 | Build | 29 | 23 | 6 | `dev.uart_{poll_wait_ms,poll_idle_ms,rxbuf,txbuf,rx_ring,max_transfer_bytes}`: values set in `devices/dev.toml`, N.1's *config* class ("not tagged") |
| N3 | L3/L4 | 547 | 12 | 535 | **owner**: OR30.a names "hardware-tier budgets". Read narrowly (proposed): the tier's soak durations (`l4.soak_duration_{short_s,mid_s,long_h}`, `l4.memory_stress_bench_hammer_duration_s`, `l4.soak_request_failure_rate`), the heap floors (`l3.heap_headroom_after_full_system_build_{max_used,worst_case_factor}`) and the named budgets (`l3.settle_budget_ms`, `l3.c_stack_budget_window_ms`, `l3.fram_command_hold_block_budget_us`, `l3.wifi_radio_reinit_connect_budget_ms`, `l4.uart_link_under_api_load_request_budget_s`) are in; each test's own waits, polls, timeouts and counts are out. Read broadly, all 547 stay. DECREV 7 condition 2 asks that the cut keep the hardware-tier budgets and their pending accuracy check visible |
| N4 | L2 | 224 | 6 | 218 | in: "twin run and soak durations": `l2.soak_{warmup_cycles,plateau_cycles,cycles}`, `l2.mem_sample_interval_ms`, `l2.mem_trend_tolerance_sd_multiplier`, and `web.connections_per_page_load` (read by the build relation check); out: each scenario's or test's waits, polls and bounds |
| N5 | L1 | 268 | 3 | 265 | in: `l1.unix_heapsize` ("Unix-port `-X heapsize`"), `l1.unix_gc_stack_entries` (the rig build's same kind), `web.serving_demand_budget_b` (a firmware heap budget the unit tier checks); out: each unit test's sleeps and bounds (the N8-N11 tagging, E.md chain 5) |
| N6 | L0 | 52 | 3 | 49 | in: `l0.vitest_test_timeout_ms`, `l0.vitest_timeout_retries` (the JS tier's per-test timeout and retries), `mem.max_await_depth` (the review's pinned depth); out: subprocess bounds inside single tests |
| N7 | CI | 21 | 21 | 0 | all are CI values |
| N8 | Runners | 22 | 22 | 0 | per-file timeouts and retries, the scenario timeout, the lock and probe values |
| N9 | Rule rows (N.4) | 9 | 4 | 5 | in: `boot.unfed_stretch_{1,2}_ms`, `boot.setup_unit_stretch_ms`, `system.scan_budget` (the watchdog budget); out of the register (kept as text in their Parts, J.6/F.5.8): `uart.{timeout,rxbuf,rx_ring}_floor` (UART-derived rules), `loop.sync_wait_max_us`, `loop.uart_call_span_max_us` |
| | **total** | 1,278 (+9) | 197 (+4) | 1,081 (+5) | |

Size: the out rows are about 456 KB of SPECIFICATION.md's 1,590 KB (L3/L4 215 KB, L1 118 KB, L2 96 KB, L0 21 KB,
firmware and build 7 KB); with N3 read broadly, about 241 KB.

### 5.2 The `@tunable` tags outside the scope

1,127 tag lines in 204 files go with the narrow reading (570 with the broad one): `tests_hardware/` 554 in 102 files,
`tests/` 433 in 61, `scripts/` 58 in 5, `tests_scripts/` 29 in 15, `tests_js/` 20 in 10, `digital_twin/` 13 in 5,
`devices/` 12 in 1 (`dev.toml`), `src/` 8 in 5 (the N1 rows; comment lines, no bytecode change). The removal is
mechanical (the tag line above the literal; the literal stays); the list of the 204 files is not written out here
(PLAN 4.1 rule 5: no matrix as a work list); phase B takes it from `git grep "@tunable <id>"` over the out IDs.
`test_tunables_register.py` shrinks with it (section 1.9).

### 5.3 Accuracy of what stays, and the heap-floor row

- The heap-floor row `l3.heap_headroom_after_full_system_build_max_used` (100000; `SPECIFICATION.md:12970`) reads
  "estimated (agent, `3fe0fb2`) — measurement owed". The review's `heap-floors-kept` "ok" (2026-10-02): "stay as they
  are; each states its basis and changes only through a new derivation of the need, never to fit a reading". New
  Basis: that owner decision; Margin: "none: the bound is the requirement" (as its sibling `..._worst_case_factor`
  already reads). N.2's check 5 then needs no "measurement owed" on it.
- CI rows (N7): R0's run is newer than their 2026-10-20 basis; the three unit-job rows change with section 4.1, the
  others keep their values and gain R0's run as a second observation.
- Firmware rows (N1): 65 of the 107 read "estimated ... measurement owed" and 27 "legacy"; the board measurements are
  round 1's, not R2's. `mem.max_await_depth`'s basis names the lost-chip chain that B3 removed (B3 hand-back: now 25
  levels): its Basis and value are re-read in phase B from `_await_depth.py`'s output (a host run, no hardware).
- Runners (N8): the five speed-band rows read "calibration owed" on the bench Pi4; they stay owed (the Pi4 is the
  owner's host).

## 6. The carries

From `S/u35r/r2/CARRY.md`:

| item | decision |
|---|---|
| `_UART_BUFFER_MAX`'s comment (`buildgen/validate.py:86`) cites `machine_uart.c:68, :376-377`; pinned 1.29.0 has `:69`, `:374-375`, `:389-390` | change, in phase B: the one comment line (build chain, no behaviour) |
| `SETTINGS_GROUPS` (`validate.py:110`) and `_owns_config_store()` (`:1151`) have no reader left in `validate.py`; the kept test checks only `networking` and `system` | keep both where they are (readers: `codegen.py:18`, `:599`, `:748`; `generate.py:20`, `:76`; two tests); change the test: `test_real_device_serves_the_settings_groups_of_the_one_table` (`test_buildgen_generate.py:466-471`) compares every emitted section with the table again (B8 FALSIFY claim 11's narrowing), seen red once on a planted extra section |
| `HardConsumer.what`/`.relief` (`validate.py:120`) unread since B8 row 1 (every reader takes `.ms`) | change, in phase B: drop the two fields and their strings at `:1325`, `:1332` (build chain; test first: the reader tests keep `.ms`) |
| rp2's REPL banner and "Type help()" after the boot entry returns at a loop end, at every DebugLevel (`ports/rp2/main.c:246-259`, `shared/runtime/pyexec.c:626-631`, read at v1.29.0) | **owner**, out of R2 (product boot entry): pre-audit port behaviour, printed once before the unfed watchdog resets the board; against "There must be a mode which is really silent on the console, ever. That's level 0." (2026-11-02). Options: accept it as port output (one Part F line), or end the boot entry at a loop end without returning to the REPL (a reset right after the loop-end record, reset code 22 kept) |

R2 lines in `S/u35r/r1/CARRY_LATER.md` and the R1 hand-backs:

| item | decision |
|---|---|
| `flash/test_system_commands.py::test_a_reset_mid_erase_leaves_every_chunk_old_or_blank[1000]`, `[2000]` fail under `--twin` (the twin's 256 KB erase ends in about 1,064 ms) | keep, phase B: root-cause under `--twin` and fix the twin's erase timing or the cut points |
| `run_digital_twin_ci.sh --only` selects no scenario; `ss: command not found` where `ss` is missing | keep, phase B (script fix, test first in `test_run_digital_twin_ci_sh.py`) |
| `tests/machine.py`'s reset-register model has no product reader | keep: the twin loop-end test and the bench reset test read it |
| `manual/manual_persistence.py`'s HAD_POR and RUN-bit checks lost their `ResetBits` read | keep, phase B writes the device-side read (B2 item 7's form), `--collect-only` checked; the run is round 1's |
| twin knobs `_bmp3xx_chip.py` `fatal_err`/EVENT, `_scd30_chip.py` `rdy_stuck_high`; bench tests expecting an empty SGP40 log after boot meet the restored W65 | change: rows N-knob-1/2; the bench expectations take W65, phase B |
| `flash/test_bus_concurrency.py::test_a_held_sda_line_is_cleared_and_every_device_answers` fails under `--twin` (no twin chip holds SDA against a bit-banged read) | change, phase B: list it as a twin exception with its reason (OR21.a (1): what the twin cannot inject is a hardware-queue check); no new twin model |
| `machine.UART.deinit()` waits out the TX FIFO (`machine_uart.c:484`, v1.29.0) | out of R2: one Part F line, R4 |
| the twin pixel's `power_dip()`, `displayed()`, `raise_on_write` | change: row N-knob-3 |
| measure each `tests/` file's live heap after each test once (snapshot 29's `_SEQUENCES` leak) | keep, phase B: one probe run, a fix only where a file grows per test |
| B3: `tests/_fram_chip_fake.py`'s `silent` knob; `mem.max_await_depth`'s basis | change: row N-knob-4; section 5.3 |
| B1 row 7: the catalog's owners, bands and range checks ("R2 and B8 judge") | keep: host only, OR28.a (2) (one global catalog, bands) |
| B8 row 20: `js/mock-server.js` (never staged), `device_max_connections_by_name()` (two tool readers: `_digital_twin_ci_suite.py`, `tests_hardware/harness.py`) | keep both: the mock serves the JS tiers and `npm run preview`; the function's two tool readers are live |

## 7. Decisions taken on the owner's behalf, and notes for the lead

- New files that stay are named inside their class row rather than one row each; every file that goes or is slimmed
  has its own row (agent, 2026-11-04: 359 one-line rows would be a matrix, PLAN 4.1 rule 5).
- The 204 files losing out-of-scope `@tunable` lines are counted per directory, not listed (same reason).
- Build-chain tests are O under OR23.a, as PLAN R2 names them, though they pin build behaviour.
- `test_shell_conventions.py`, `test_const_mirrors.py`, `test_tests_hardware_product_copies.py`,
  `test_isl29125_copies.py` and `test_http_client_shape_parity.py` were (A) candidates and are kept: the first guards
  the runners' `set -euo pipefail` (a failed step cannot read as a pass), the second pins the tests' UART wire-constant
  copies to the two-implementation protocol (SPEC J), the others keep twin and hardware copies of product facts true.
- No legacy or pre-audit function was found lost (sections 1.1, 1.4).
- Nothing was run, built or edited; `S/u35r/r2/ftmp/` is deleted.
