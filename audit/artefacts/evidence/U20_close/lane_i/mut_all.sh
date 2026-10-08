#!/bin/bash
# Re-runs every planted defect (u20i_mut/<x>) against the scenarios that must catch it, wozi, gc-1.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
M=$S/u20i_mut
run() { echo "=== mutation $1"; bash $S/u20i_runs/mut.sh $M/$1 wozi "${@:2}"; }
run a main_runs_setups_then_tasks boot_sequence_matches
run b every_logger_the_boot_constructs
run c fram_chunks_are_all_successfully_allocated the_fram_manager_is_the_only
run d unreadable_or_damaged resetconfig_over_a_damaged
run e config_write_failed_until
run f every_api_write_is_refused reboot_flushes_a_still
run g only_the_api_writes_the_scd30
run h resetconfig_over_a_damaged
run i reboot_flushes_a_still
run j reboot_flushes_a_still
run k reboot_cmd_arms_the_real
echo "=== control (no overlay)"
bash $S/u20i_runs/mut.sh $S/u20i_mut/none wozi main_runs_setups_then_tasks boot_sequence_matches every_logger_the_boot_constructs fram_chunks_are_all_successfully_allocated the_fram_manager_is_the_only unreadable_or_damaged resetconfig_over_a_damaged config_write_failed_until every_api_write_is_refused reboot_flushes_a_still only_the_api_writes_the_scd30 reboot_cmd_arms_the_real
