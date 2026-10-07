"""Imports run once, at module load, and every import is static (SPECIFICATION.md F.1): no import inside a
function body and no dynamic load anywhere in the eight lint scopes, outside _NAMED_EXCEPTIONS and the
_PENDING list, which only shrinks; `uv run python tests_scripts/test_import_placement.py --regenerate` prunes it."""

import ast
import re
import sys
from collections import Counter
from pathlib import Path

import pytest
from _repo_scan import REPO_ROOT, exit_on_new, repo_files

SCOPES = ("src/", "buildgen/", "digital_twin/", "tests/", "tests_scripts/", "tests_hardware/", "scripts/", "toolchain/")
# tests/_tmp/ is scratch; this file's own fixtures are the patterns themselves.
_SKIPPED = ("tests/_tmp/", "tests_scripts/test_import_placement.py")
# The import-graph check plants dynamic loads as string fixtures; its code is still checked, its strings are not launchers.
_FIXTURE_LITERALS = frozenset({"tests_scripts/test_import_graph.py"})
# __import__ counts only as a bare call, importlib's names in any spelling. Executing a file by path
# (exec) is not an import (F.1): ruff's S102 and its per-file ignores govern it.
_BUILTIN_LOADS = frozenset({"__import__"})
_IMPORTLIB_LOADS = frozenset({"import_module", "spec_from_file_location", "module_from_spec", "exec_module"})
_EMBEDDED_TRIGGERS = tuple(f"{name}(" for name in (*_BUILTIN_LOADS, *_IMPORTLIB_LOADS))

Site = tuple[str, str, str]

# SPECIFICATION.md F.1's named host and test sites, each with the reason F.1 gives: a dynamic load in one
# of these files passes; a function-level import there does not.
_NAMED_EXCEPTIONS: dict[str, str] = {
    "buildgen/validate.py": "loads toolchain/micropython_overrides.py by path: it is no package",
    "digital_twin/run_generic_integration.py": "the module its device config names",
    "ext/freezefs/ffsextract.py": "vendored, build-time only; its extract mode is never used",
    "tests/_boot_contiguity_probe.py": "a device module by its derived name",
    "tests/_digital_twin_construction_scenarios.py": "a device module by its derived name",
    "tests/_sensortask_scenarios.py": "a device module by its derived name",
    "tests/_webserver_concurrency_scenarios.py": "a device module by its derived name",
    "tests/test_asy_isl29125_driver.py": '__import__("time") inside two test statements',
    "tests_scripts/_script_loader.py": "a scripts/ file by path",
    "tests_scripts/conftest.py": "sets the path that loader relies on; names importlib in a comment",
    "tests_scripts/test_buildgen_validate.py": "a test of the named loader in buildgen/validate.py",
    "tests_scripts/test_js_coverage_report_dir.py": "names importlib in a comment; reads import statements by AST",
}
_DYNAMIC_LOADS = _BUILTIN_LOADS | _IMPORTLIB_LOADS

# Sites present when this check landed, each moved to module level or named above by the unit owning
# its file. Rebuilt only by --regenerate; the second test fails on an entry that no longer occurs.
_PENDING: tuple[Site, ...] = (
    ("digital_twin/_bmp3xx_chip.py", "Bmp3xxChip.__init__", "random"),
    ("digital_twin/_http_client.py", "HttpResponse.json", "_strict_json"),
    ("digital_twin/_isl29125_chip.py", "Isl29125Chip.__init__", "random"),
    ("digital_twin/_isl29125_chip.py", "Isl29125Chip._start_timer", "machine"),
    ("digital_twin/_scd30_chip.py", "Scd30Chip.__init__", "random"),
    ("digital_twin/_scd30_chip.py", "Scd30Chip._start_timer", "machine"),
    ("digital_twin/launch.py", "main", "random"),
    ("digital_twin/machine.py", "_build_i2c_chip", "_bmp3xx_chip"),
    ("digital_twin/machine.py", "_build_i2c_chip", "_isl29125_chip"),
    ("digital_twin/machine.py", "_build_i2c_chip", "_scd30_chip"),
    ("digital_twin/machine.py", "_build_i2c_chip", "_sgp40_chip"),
    ("digital_twin/machine.py", "_wire_spi_device", "_fram_chip"),
    ("digital_twin/run_generic_integration.py", "_apply_fault", "errno"),
    ("digital_twin/run_generic_integration.py", "_ensure_dir", "os"),
    ("digital_twin/run_generic_integration.py", "main", "random"),
    ("scripts/_digital_twin_ci_suite.py", "_configured_max_connections", "buildgen.validate"),
    ("tests/_boot_contiguity_probe.py", "_main", "asy_system_service"),
    ("tests/_digital_twin_construction_scenarios.py", "_scenario_bus_fault_degrades.scenario", "errno"),
    ("tests/_sensortask_scenarios.py", "_scenario_fram_chunk_order", "asy_fram_manager"),
    ("tests/_sensortask_scenarios.py", "_scenario_main_call_order", "asy_ntp_client"),
    ("tests/_sensortask_scenarios.py", "_scenario_main_call_order", "asy_system_service"),
    ("tests/_sensortask_scenarios.py", "_scenario_main_forwards_web_host_port", "asy_ntp_client"),
    ("tests/_sensortask_scenarios.py", "_scenario_main_forwards_web_host_port", "asy_system_service"),
    ("tests/test_asy_bmp3xx_driver.py", "test_init_bmp_runs_on_the_defaults_when_its_config_file_cannot_be_written", "asy_config_manager"),
    ("tests/test_asy_fram_manager.py", "_RaisingPackInto.calcsize", "struct"),
    ("tests/test_asy_fram_manager.py", "_RaisingPackInto.unpack_from", "struct"),
    ("tests/test_asy_fram_manager.py", "_RaisingUnpackFrom.calcsize", "struct"),
    ("tests/test_asy_fram_manager.py", "_RaisingUnpackFrom.pack_into", "struct"),
    ("tests/test_asy_isl29125_driver.py", "ready_reader", "time"),
    ("tests/test_asy_notification_service.py", "test_next_sleep_s_floors_at_point_one_when_elapsed_exceeds_interv", "time"),
    ("tests/test_asy_notification_service.py", "test_next_sleep_s_subtracts_elapsed_time", "time"),
    ("tests/test_asy_sgp40_driver.py", "_OldTime.gmtime", "time"),
    ("tests/test_asy_sgp40_driver.py", "_OldTime.mktime", "time"),
    ("tests/test_asy_uart_comm.py", "test_the_next_uid_prediction_is_correct_at_the_wrap_boundary", "asy_uart_comm"),
    ("tests/test_asy_uart_comm.py", "test_the_uid_cycle_covers_every_legal_value_and_never_0xff", "asy_uart_comm"),
    ("tests/test_asy_webserver_service.py", "test_f9_soak_100_plus_start_wedge_reclaim_cycles_hold_counter_and_memory_flat", "gc"),
    ("tests/test_asy_wifi_service.py", "_client_with_stored", "json"),
    ("tests/test_asy_wifi_service.py", "test_radio_bytes_ok_passes_through_everything_the_schema_check_owns", "asy_wifi_service"),
    ("tests/test_asy_base_classes.py", "_RaisingFramChunk.get_buffer", "asy_base_classes"),
    ("tests/test_asy_captive_dns.py", "test_run_backs_off_on_a_genuinely_unexpected_exception_then_recovers", "asy_captive_dns"),
    ("tests/test_digital_twin_fram.py", "test_load_state_handles_a_hex_byte_pair_straddling_a_chunk_boundary", "_fram_chip"),
    ("tests/test_digital_twin_fram.py", "test_save_state_round_trips_correctly_across_chunk_boundaries", "_fram_chip"),
    ("tests/test_digital_twin_machine.py", "test_configure_scd30_state_path_and_flush_scd30_round_trip_settings", "_crc8"),
    ("tests/test_digital_twin_machine.py", "test_configure_scd30_state_path_and_flush_scd30_round_trip_settings", "os"),
    ("tests/test_digital_twin_machine_uart.py", "test_twin_poller_is_not_a_real_select_poll", "select"),
    ("tests/test_digital_twin_machine_uart.py", "test_twin_poller_requeries_ioctl", "select"),
    ("tests/test_digital_twin_network_neopixel.py", "test_country_and_hostname_enforce_the_real_byte_bounds", "network"),
    ("tests/test_digital_twin_network_neopixel.py", "test_country_and_hostname_set_then_get_round_trip", "network"),
    ("tests/test_digital_twin_network_neopixel.py", "test_neopixel_writes_stays_bounded_across_many_writes", "neopixel"),
    ("tests/test_digital_twin_network_neopixel.py", "test_wlan_config_calls_stays_bounded_across_many_calls", "network"),
    ("tests/test_digital_twin_network_neopixel.py", "test_wlan_connect_calls_stays_bounded_across_many_calls", "network"),
    ("tests/test_digital_twin_real_website_integration.py", "_decompress", "deflate"),
    ("tests/test_digital_twin_real_website_integration.py", "_decompress", "io"),
    ("tests/test_digital_twin_sensortask_integration.py", "test_start_and_check_tasks_restarts_a_real_dead_task_from_the_real_full_task_list.scenario", "asy_system_service"),
    ("tests/test_digital_twin_sensortask_integration.py", "test_wifi_sta_failure_falls_back_to_hotspot_and_drives_the_real_dns_server_and_status_led.scenario", "network"),
    ("tests/test_digital_twin_uart_link.py", "_hammer_with_the_graph_running", "gc"),
    ("tests/test_digital_twin_uart_link.py", "test_a_forced_collection_mid_transfer_does_not_break_the_link", "gc"),
    ("tests/test_digital_twin_uart_link.py", "test_many_back_to_back_transfers_do_not_degrade_or_leak", "gc"),
    ("tests/test_digital_twin_uart_link.py", "test_the_link_survives_sustained_allocation_pressure", "gc"),
    ("tests/test_machine_uart_link.py", "test_a_long_run_keeps_the_fake_log_from_growing_without_bound", "machine"),
    ("tests/test_machine_uart_link.py", "test_the_call_log_is_bounded_and_says_when_it_dropped", "machine"),
    ("tests/test_ntp_wifi_dns_integration.py", "test_dns_resolution_totally_unreachable_through_the_real_chain_persists_errno_12", "asy_dns_client"),
    ("tests/test_setter_microdot_integration.py", "_fault_i2c_write", "machine"),
    ("tests/test_setter_microdot_integration.py", "_fault_next_i2c_write", "machine"),
    ("tests/test_setter_microdot_integration.py", "_nak_i2c_address", "machine"),
    ("tests/test_setter_microdot_integration.py", "_scd_writes", "machine"),
    ("tests/test_uart_comm_hazard.py", "_check_a_receive_buffer_smaller_than_a_frame_is_refused_at_construction", "asy_uart_comm"),
    ("tests/test_uart_comm_hazard.py", "_check_a_receive_buffer_smaller_than_a_frame_is_refused_at_construction", "asy_uart_driver"),
    ("tests/test_uart_comm_hazard.py", "_hammer_clean", "gc"),
    ("tests/test_uart_comm_hazard.py", "_hammer_faulted", "gc"),
    ("tests/test_uart_comm_hazard.py", "_measure_retention", "gc"),
    ("tests/test_uart_comm_hazard.py", "_under_threshold", "gc"),
    ("tests/test_website_build_integration.py", "_decompress", "deflate"),
    ("tests/test_website_build_integration.py", "_decompress", "io"),
    ("tests_hardware/bench/test_hotspot_role_reversal.py", "test_dns_flood_backoff_curve_recovers_once_flood_stops", "socket"),
    ("tests_hardware/bench/test_hotspot_role_reversal.py", "test_malformed_http_request_over_real_wireless_degrades_cleanly", "socket"),
    ("tests_hardware/bench/test_hotspot_role_reversal.py", "test_nonsense_path_redirects_to_root_over_the_hotspot_link", "socket"),
    ("tests_hardware/harness.py", "configured_max_connections", "buildgen.validate"),
    ("tests_hardware/harness.py", "restore_board_to_serving", "http_client"),
    ("tests_hardware/harness.py", "wait_for_script_server", "http_client"),
    ("tests_hardware/manual/runner.py", "main", "manual_bus_electrical"),
    ("tests_hardware/manual/runner.py", "main", "manual_persistence"),
    ("tests_hardware/manual/runner.py", "main", "manual_sensor_accuracy"),
    ("tests_hardware/manual/runner.py", "main", "manual_toolchain"),
    ("tests_hardware/manual/runner.py", "main", "manual_wifi"),
    ("tests_scripts/test_bench_harness_helpers.py", "test_configured_max_connections_is_the_builds_own_ceiling_for_every_device", "buildgen.validate"),
    ("tests_scripts/test_build_firmware.py", "test_build_stage_dir_rejects_a_frozen_module_colliding_with_a_reserved_staging_name", "types"),
    ("tests_scripts/test_build_firmware.py", "test_build_stage_dir_rejects_a_frozen_module_resolving_to_neither_src_nor_ext", "types"),
    ("tests_scripts/test_build_firmware.py", "test_build_stage_dir_stages_exactly_the_computed_frozen_modules", "buildgen.frozen_modules"),
    ("tests_scripts/test_build_firmware.py", "test_build_stage_dir_stages_exactly_the_computed_frozen_modules", "buildgen.validate"),
    ("tests_scripts/test_build_firmware.py", "test_build_stage_dir_writes_the_generated_entry_module_and_boot_entry", "buildgen.codegen"),
    ("tests_scripts/test_build_firmware.py", "test_build_stage_dir_writes_the_generated_entry_module_and_boot_entry", "buildgen.generate"),
    ("tests_scripts/test_buildgen_definitions.py", "test_measurements_and_sensors_sections_fails_loud_if_driver_info_still_unset", "buildgen.definitions"),
    ("tests_scripts/test_buildgen_definitions.py", "test_notification_section_fails_loud_if_driver_info_still_unset", "buildgen.definitions"),
    ("tests_scripts/test_buildgen_definitions.py", "test_resolved_key_fails_loud_if_resolved_name_still_unset", "buildgen.definitions"),
    ("tests_scripts/test_buildgen_driver_registry.py", "test_needs_setup_returns_false_when_the_class_is_absent_from_the_file", "ast"),
    ("tests_scripts/test_buildgen_driver_registry.py", "test_needs_setup_returns_false_when_the_class_is_absent_from_the_file", "buildgen.driver_registry"),
    ("tests_scripts/test_buildgen_frozen_modules.py", "test_a_seed_module_with_no_file_on_disk_contributes_no_imports", "buildgen.frozen_modules"),
    ("tests_scripts/test_buildgen_frozen_modules.py", "test_an_import_cycle_between_two_modules_terminates", "buildgen.frozen_modules"),
    ("tests_scripts/test_buildgen_frozen_modules.py", "test_frozen_modules_exclude_type_checking_only_import", "buildgen.driver_registry"),
    ("tests_scripts/test_buildgen_frozen_modules.py", "test_frozen_modules_exclude_type_checking_only_import", "buildgen.model"),
    ("tests_scripts/test_buildgen_frozen_modules.py", "test_frozen_modules_real_import_is_included", "buildgen.driver_registry"),
    ("tests_scripts/test_buildgen_frozen_modules.py", "test_frozen_modules_real_import_is_included", "buildgen.model"),
    ("tests_scripts/test_buildgen_generate.py", "test_cli_entry_point_reports_a_build_error_and_exits_nonzero", "subprocess"),
    ("tests_scripts/test_buildgen_generate.py", "test_cli_entry_point_reports_a_build_error_and_exits_nonzero", "sys"),
    ("tests_scripts/test_buildgen_generate.py", "test_cli_entry_point_writes_both_files_and_exits_zero", "subprocess"),
    ("tests_scripts/test_buildgen_generate.py", "test_cli_entry_point_writes_both_files_and_exits_zero", "sys"),
    ("tests_scripts/test_buildgen_generate.py", "test_cli_prints_module_source_without_out_dir", "buildgen.generate"),
    ("tests_scripts/test_buildgen_generate.py", "test_cli_reports_build_error_on_stderr_and_exits_nonzero", "buildgen.generate"),
    ("tests_scripts/test_buildgen_generate.py", "test_cli_writes_module_and_boot_entry_to_out_dir", "buildgen.generate"),
    ("tests_scripts/test_buildgen_generate.py", "test_codegen_has_no_build_recipe_for_an_unknown_driver", "buildgen.codegen"),
    ("tests_scripts/test_buildgen_generate.py", "test_codegen_has_no_build_recipe_for_an_unknown_driver", "buildgen.validate"),
    ("tests_scripts/test_buildgen_generate.py", "test_construction_order_entry_that_is_neither_a_bare_node_nor_an_instance_key_fails_loud", "buildgen.codegen"),
    ("tests_scripts/test_buildgen_generate.py", "test_construction_order_entry_that_is_neither_a_bare_node_nor_an_instance_key_fails_loud", "buildgen.graph"),
    ("tests_scripts/test_buildgen_generate.py", "test_construction_order_entry_that_is_neither_a_bare_node_nor_an_instance_key_fails_loud", "buildgen.validate"),
    ("tests_scripts/test_buildgen_generate.py", "test_identifier_rejects_a_name_python_could_not_use", "buildgen.codegen"),
    ("tests_scripts/test_buildgen_generate.py", "test_instance_with_no_driver_info_fails_loud_at_codegen_time", "buildgen.codegen"),
    ("tests_scripts/test_buildgen_generate.py", "test_instance_with_no_driver_info_fails_loud_at_codegen_time", "buildgen.graph"),
    ("tests_scripts/test_buildgen_generate.py", "test_instance_with_no_driver_info_fails_loud_at_codegen_time", "buildgen.validate"),
    ("tests_scripts/test_buildgen_generate.py", "test_notification_with_no_signal_sink_wiring_field_fails_loud", "buildgen.codegen"),
    ("tests_scripts/test_buildgen_generate.py", "test_notification_with_no_signal_sink_wiring_field_fails_loud", "buildgen.validate"),
    ("tests_scripts/test_buildgen_graph.py", "test_cycle_detection_raises", "buildgen.wiring"),
    ("tests_scripts/test_buildgen_twin_wiring.py", "digital_twin_machine", "machine"),
    ("tests_scripts/test_buildgen_validate.py", "_lwip_pcbs", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_a_malformed_lwip_table_is_a_named_build_error_never_a_traceback", "buildgen"),
    ("tests_scripts/test_buildgen_validate.py", "test_a_malformed_lwip_table_is_a_named_build_error_never_a_traceback", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_an_lwip_entry_that_is_not_a_table_is_refused_by_the_loader", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_an_unreadable_lwip_table_is_a_named_build_error_never_a_traceback", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_an_unreadable_webserver_source_is_a_named_build_error", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_default_provider_params_check_fails_loud_if_driver_info_still_unset", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_default_provider_params_check_fails_loud_if_driver_info_still_unset", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_default_value_selection_check_fails_loud_for_a_non_table_wiring_value", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_default_value_selection_check_fails_loud_for_a_non_table_wiring_value", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_default_value_selection_check_fails_loud_for_a_non_table_wiring_value", "buildgen.value_wiring"),
    ("tests_scripts/test_buildgen_validate.py", "test_device_max_connections_reads_the_toml_else_the_src_default", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_device_wiring_required_field_missing_is_rejected", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_device_wiring_required_field_missing_is_rejected", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_every_shipped_device_passes_the_uart_link_bus_check", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_gpio_collision_cs_pin_synthetic_two_instances", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_gpio_collision_cs_pin_synthetic_two_instances", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_init_int_default_reads_the_named_class_in_the_named_file_only", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_instance_label_collision_synthetic", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_instance_label_collision_synthetic", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_instance_name_collision_check_fails_loud_if_resolved_name_still_unset", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_instance_name_collision_check_fails_loud_if_resolved_name_still_unset", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_instance_name_collision_via_distinct_drivers_same_resolved_name", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_instance_name_collision_via_distinct_drivers_same_resolved_name", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_module_int_const_reads_a_const_or_a_plain_int_and_names_a_miss", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_ntp_backoff_keys_are_optional_and_their_src_defaults_pass_the_check", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_required_fields_check_fails_loud_for_a_bus_attached_driver_with_no_bus_kind_entry", "buildgen.buildspec"),
    ("tests_scripts/test_buildgen_validate.py", "test_required_fields_check_fails_loud_for_a_bus_attached_driver_with_no_bus_kind_entry", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_required_fields_check_fails_loud_for_a_bus_attached_driver_with_no_bus_kind_entry", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_the_shipped_ntp_backoff_defaults_are_readable_from_the_real_source", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_the_src_default_itself_is_servable_by_the_pinned_lwip_table", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_the_src_default_itself_is_servable_by_the_pinned_lwip_table", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_webserver_init_default_reads_only_an_int_literal_of_the_real_class", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_wiring_reference_check_fails_loud_if_target_driver_info_still_unset", "buildgen.model"),
    ("tests_scripts/test_buildgen_validate.py", "test_wiring_reference_check_fails_loud_if_target_driver_info_still_unset", "buildgen.validate"),
    ("tests_scripts/test_buildgen_validate.py", "test_wiring_reference_check_fails_loud_if_target_driver_info_still_unset", "buildgen.wiring"),
    ("tests_scripts/test_device_tomls.py", "test_no_fixed_driver_address_falls_in_a_reserved_range", "buildgen.twin_wiring"),
    ("tests_scripts/test_http_client_ceiling_close.py", "_bench_module", "test_bus_concurrency_under_api_load"),
    ("tests_scripts/test_micropython_overrides.py", "TestBuildFirmwareAppliesTheLwipOverride.test_without_an_explicit_table_the_build_applies_versions_tomls_own", "tomllib"),
    ("tests_scripts/test_micropython_overrides.py", "TestLwipEnsemble.test_the_shipped_table_is_coherent_at_every_devices_own_ceiling", "tomllib"),
    ("tests_scripts/test_request_timeout_ceiling.py", "_largest_shipped_ceiling", "buildgen.validate"),
)


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr if func.attr in _IMPORTLIB_LOADS else None
    bare = func.id if isinstance(func, ast.Name) else None
    return bare if bare in _BUILTIN_LOADS or bare in _IMPORTLIB_LOADS else None


def is_named(site: Site) -> bool:
    return site[2] in _DYNAMIC_LOADS and site[0] in _NAMED_EXCEPTIONS


def sites_in_source(path: str, source: str) -> list[Site]:
    # Every function-level import (by module) and every dynamic load (by call), with the dotted name
    # of what encloses it - "<module>" at module level, where only a dynamic load counts. Source held in a
    # string literal (a launcher another interpreter runs) is parsed and checked the same way.
    sites: list[Site] = []

    def visit(node: ast.AST, scope: tuple[str, ...], *, in_function: bool) -> None:
        for child in ast.iter_child_nodes(node):
            qualname = ".".join(scope) or "<module>"
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit(child, (*scope, child.name), in_function=in_function or not isinstance(child, ast.ClassDef))
                continue
            if in_function and isinstance(child, ast.Import):
                sites.extend((path, qualname, alias.name) for alias in child.names)
            elif in_function and isinstance(child, ast.ImportFrom):
                sites.append((path, qualname, "." * child.level + (child.module or "")))
            elif isinstance(child, ast.Call) and (call := _call_name(child)):
                sites.append((path, qualname, call))
            elif isinstance(child, ast.Constant) and isinstance(child.value, str) and path not in _FIXTURE_LITERALS and any(t in child.value for t in _EMBEDDED_TRIGGERS):
                sites.extend((path, qualname, name) for _, _, name in _embedded_sites(path, child.value))
            visit(child, scope, in_function=in_function)

    visit(ast.parse(source, filename=path), (), in_function=False)
    return sites


def _embedded_sites(path: str, text: str) -> list[Site]:
    try:
        return sites_in_source(path, text)
    except SyntaxError:
        return []


def collect_sites() -> Counter[Site]:
    found: Counter[Site] = Counter()
    for path in repo_files():
        if path.endswith(".py") and path.startswith(SCOPES) and not path.startswith(_SKIPPED):
            found.update(sites_in_source(path, (REPO_ROOT / path).read_text(encoding="utf-8")))
    return found


def test_no_function_level_or_dynamic_import_outside_the_named_lists() -> None:
    unexpected = collect_sites() - Counter(_PENDING)
    new = sorted(site for site in unexpected.elements() if not is_named(site))
    assert not new, "imports belong at module top, static (SPECIFICATION.md F.1) - move these, or name them there:\n" + "\n".join(f"  {s}" for s in new)


def test_the_pending_list_only_shrinks() -> None:
    stale = sorted((Counter(_PENDING) - collect_sites()).elements())
    assert not stale, "_PENDING entries that no longer occur - delete them (or --regenerate):\n" + "\n".join(f"  {s}" for s in stale)


def test_each_kind_of_site_is_caught(tmp_path: Path) -> None:
    source = (
        "import importlib\n"
        "def f():\n    import json\n    from . import sibling\n"
        "class C:\n    async def g(self):\n        from os import path\n"
        "def h(p):\n    spec = importlib.util.spec_from_file_location('m', p)\n    spec.loader.exec_module(importlib.util.module_from_spec(spec))\n"
        "mod = __import__('time')\nimportlib.import_module('x')\nexec(compile(open('f').read(), 'f', 'exec'))\n"
    )
    probe = tmp_path / "probe.py"
    probe.write_text(source)
    assert sorted(sites_in_source("probe.py", probe.read_text())) == sorted([
        ("probe.py", "f", "json"),
        ("probe.py", "f", "."),
        ("probe.py", "C.g", "os"),
        ("probe.py", "h", "spec_from_file_location"),
        ("probe.py", "h", "exec_module"),
        ("probe.py", "h", "module_from_spec"),
        ("probe.py", "<module>", "__import__"),
        ("probe.py", "<module>", "import_module"),
    ])


def test_a_named_file_passes_only_its_dynamic_loads() -> None:
    named = next(iter(_NAMED_EXCEPTIONS))
    source = "def f():\n    import json\n    return __import__('time')\n"
    sites = sites_in_source(named, source)
    assert [is_named(site) for site in sites] == [False, True], sites
    assert not any(is_named(site) for site in sites_in_source("src/unnamed.py", source))


def f1_named_paths() -> set[str]:
    # The files F.1's list names: code spans at parenthesis depth 0 between its colon and the exec
    # sentence (a reason's own code spans sit inside its parentheses).
    spec = (REPO_ROOT / "SPECIFICATION.md").read_text(encoding="utf-8")
    listed = re.search(r"judges every listed one harmless \(owner, 2026-10-05\):\n(.*?)Executing a file by path", spec, re.DOTALL)
    assert listed is not None, "SPECIFICATION.md F.1's named list moved - re-anchor f1_named_paths()"
    paths, depth = set(), 0
    for index, part in enumerate(listed.group(1).split("`")):
        if index % 2:
            if depth == 0 and part.endswith(".py"):
                paths.add(part)
        else:
            depth += part.count("(") - part.count(")")
    return paths


def test_the_named_exceptions_mirror_specification_f1() -> None:
    assert set(_NAMED_EXCEPTIONS) == f1_named_paths(), "_NAMED_EXCEPTIONS and SPECIFICATION.md F.1's named list differ - one of them moved"
    missing = sorted(path for path in _NAMED_EXCEPTIONS if not (REPO_ROOT / path).is_file())
    assert not missing, f"named in F.1 but no such file: {missing}"


def test_module_level_and_type_checking_imports_pass() -> None:
    source = "import os\nfrom typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import json\nclass C:\n    import re\n"
    assert sites_in_source("ok.py", source) == []


def test_regenerate_keeps_only_pending_sites_still_present_and_refuses_new_ones(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    copy = tmp_path / "test_import_placement.py"
    copy.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")
    kept, gone, new = ("src/a.py", "f", "os"), ("src/b.py", "g", "re"), ("src/x.py", "f", "json")
    this = sys.modules[__name__]
    monkeypatch.setattr(this, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(this, "_PENDING", (kept, kept, gone))
    monkeypatch.setattr(this, "collect_sites", lambda: Counter([kept, new]))
    with pytest.raises(SystemExit, match=r"src/x\.py"):
        _regenerate(copy)
    pending = re.search(r"(?m)^_PENDING: tuple\[Site, \.\.\.\] = \(\n((?:.*\n)*?)\)\n", copy.read_text(encoding="utf-8"))
    assert pending is not None
    assert pending.group(1) == f'    ("{kept[0]}", "{kept[1]}", "{kept[2]}"),\n'


def _regenerate(this: Path = Path(__file__)) -> None:
    # Keeps the _PENDING sites still present (the list only shrinks) and exits 1 naming any new one.
    current, previous = collect_sites(), Counter(_PENDING)
    body = "".join(f'    ("{path}", "{qualname}", "{name}"),\n' for path, qualname, name in sorted((previous & current).elements()))
    text = re.sub(r"(?m)^(_PENDING: tuple\[Site, \.\.\.\] = \(\n)(?:.*\n)*?(\)\n)", lambda m: m.group(1) + body + m.group(2), this.read_text(encoding="utf-8"), count=1)
    this.write_text(text, encoding="utf-8")
    exit_on_new(f"_PENDING in {this.relative_to(REPO_ROOT)}", sorted(s for s in (current - previous).elements() if not is_named(s)))


if __name__ == "__main__":
    if sys.argv[1:] != ["--regenerate"]:
        sys.exit("usage: uv run python tests_scripts/test_import_placement.py --regenerate")
    _regenerate()
