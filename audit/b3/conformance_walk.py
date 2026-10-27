# M.PROC.026/.027/.029: writes conformance.md's rung and owner rows (from audit/actions/SUPP_recovery.md) and queue_c.md's rows.
# Usage: python3 -I audit/b3/conformance_walk.py <tree>. A cell names the tests the record cites; the B2 review checks each bites.
import re, subprocess, sys
from pathlib import Path

tree = Path(sys.argv[1])
head = subprocess.run(["git", "-C", str(tree), "log", "-1", "--format=%h"], capture_output=True, text=True, check=False).stdout.strip() or "unknown"  # never an empty stamp
TEST = re.compile(r"(tests(?:_hardware)?/[\w/]+\.py)")


def level(path):
    if path.startswith("tests_hardware/bench/"):
        return "L4"
    if path.startswith(("tests_hardware/flash/", "tests_hardware/device_scripts/")):
        return "L3"
    return "L2" if path.startswith("tests/test_digital_twin_") else "L1"


def keep_header(path):
    return path.read_text(encoding="utf-8").split("\n## ")[0].rstrip() + "\n"


# The reviewed rows (lane CO1, agent, 2026-10-27): (unit, fault path, rung) -> L1, L2, bounded / once / race-free, gap.
# Every file::test named is biting or justified in review.md at the walked commit; L3/L4 stay the record's.
B, SS, SC, I2, BH, TB, TI, TF, TM, TS, W, TP, CM = ("test_asy_base_classes.py::", "test_asy_system_service.py::", "_sensortask_scenarios.py::", "test_asy_i2c_driver.py::", "test_bus_hazard_multi_device.py::", "test_digital_twin_bus_hazard_concurrency.py::", "test_digital_twin_sensortask_integration.py::", "test_digital_twin_fram.py::", "test_digital_twin_machine.py::", "_digital_twin_scenarios.py::", "test_asy_wifi_service.py::", "test_digital_twin_timer_pool.py::", "test_asy_config_manager.py::")
DONE = "L1/L2 named, each test biting in review.md or, for a test this review added, red on a planted fault (agent, 2026-10-27); L3/L4 as the record's cells"
R5 = (f"{B}test_error_check_failure_increments_until_giving_up, {SS}test_supervise_tasks_restarts_a_dead_task_and_logs_its_end", f"{TI}test_the_supervisor_restarts_a_real_dead_task", f"bounded: {SS}test_three_deaths_stay_inside_the_budget_and_decay (the budget); once: {SS}test_each_task_end_adds_exactly_one_entry; race-free: {SC}one_supervisor_pass_over_dead_tasks_persists_at_most_one_entry_per_end (several ends in one pass)", DONE)
R6 = (f"{SS}test_the_supervisor_escalates_past_the_failure_budget", f"{TF}test_a_booted_device_whose_fram_goes_silent_restarts_its_task_and_recovers_or_arms_the_reset", f"bounded: {SS}test_the_task_budget_steps_once_past_its_max_and_stops; once: {SS}test_an_escalating_pass_retires_the_dead_task_so_no_later_pass_awaits_it_again; race-free: {SS}test_a_command_accepted_while_the_escalation_logs_keeps_its_own_reset (a command session forced into the escalation's log write)", DONE)
R7 = (f"{SC}a_task_that_keeps_ending_stops_every_feed_once_its_reboot_is_armed, {SS}test_an_armed_reset_stops_every_feed_so_a_dropped_one_shot_still_resets", f"{TS}watchdog_fault_supervisor_raise (twin scenario)", f"bounded and once: {TM}test_wdt_notifies_once_after_a_feed_free_window (one period, one notification); race-free: {SS}test_after_the_takeover_no_other_site_feeds, {SC}a_cancelled_main_leaves_no_timer_feeding_the_watchdog (every Timer and pin IRQ fired, none feeds)", DONE)
BUS_PROOF = f"bounded: {I2}test_clear_and_recover_end_a_held_scl_at_the_bus_timeout_on_the_fake_clock (driven clock); once: {B}test_two_readers_failing_on_one_bus_clear_it_once_and_rebuild_it_once; race-free: {B}test_a_bus_rung_parked_behind_a_sibling_session_is_spent_for_every_reader_on_the_bus (a held bus lock as the gate), {BH}test_a_recovery_during_a_held_bus_clear_lets_no_sibling_transfer_in"
BUS_FIX = "defect fixed (agent, 2026-10-27): a second reader re-ran a rung parked on the bus lock; I2C.clear()/recover() now step recoveries before the lock wait (the race test was red on the base)"
FD, FM = ("test_asy_fram_driver.py::", "test_asy_fram_manager.py::")
SCD, SGP, BMP, ISL, SP, UD, UL, BG = ("test_asy_scd30_driver.py::", "test_asy_sgp40_driver.py::", "test_asy_bmp3xx_driver.py::", "test_asy_isl29125_driver.py::", "test_asy_spi_driver.py::", "test_asy_uart_driver.py::", "test_digital_twin_uart_link.py::", "test_buildgen_pico_gpio.py::")
SETUP_L2 = f"{TB}test_two_setups_failing_together_each_rebuild_the_controller_once_one_after_the_other"
SETUP_RACE = f"race-free: {SETUP_L2} (a sibling session holding the bus lock as the gate)"
SETUP_DONE = DONE + "; kept as designed (agent, 2026-10-27): each failed setup starts its own episode, so two run one rebuild each, serialized by the bus lock and bounded by the restart budget; a rung cancelled in its lock wait counts as run, since reader tasks are cancelled only by the shutdown sequence (src/asy_system_service.py:462-464), after which the unit resets"
PROBE = (f"{FD}test_verify_present_bounded_wait_returns_false_instead_of_hanging_when_lock_already_held, {FM}test_a_probe_that_cannot_take_the_lock_keeps_the_blank_verdict", "open: no twin test holds the FRAM session past the probe's bounded wait (gap, left)", f"bounded: {FD}test_verify_present_bounded_wait_returns_false_instead_of_hanging_when_lock_already_held; once: {FM}test_a_probe_that_cannot_take_the_lock_keeps_the_blank_verdict (one probe per blank read); race-free: the same two (the lock held by a sibling session)", "re-triaged (agent, 2026-10-27): the probe has a product caller, the blank-read verdict (src/asy_fram_manager.py:149-154); a timed-out wait keeps the blank verdict and declares no loss, so no rung follows; L2 open (left)")
REVIEWED = {
    ("U10", "a sensor/WLAN cycle fails", "R1"): (f"{B}test_the_ladder_fires_each_rung_once_in_order, {W}test_wlan_connect_recovers_the_streak_on_alternating_failure_and_success", f"{TB}test_a_sustained_fault_on_one_twin_chip_climbs_to_the_bus_clear_and_recovers_once_cleared", f"bounded: {B}test_error_check_failure_increments_until_giving_up (max_module_error); once: {B}test_a_failing_cycle_keeps_the_drivers_and_the_streaks_entries; race-free: {SC}a_bus_nak_storm_climbs_each_rung_once_per_bus_and_every_reader_recovers (every loop released together by counted triggers)", DONE),
    ("U10", "a sensor/WLAN cycle fails", "R2"): (f"{B}test_a_successful_hook_adds_one_warning_and_a_failed_one_only_its_own_error, {W}test_the_radio_rung_fires_again_after_a_restart_and_a_good_iteration", f"{TB}test_a_sustained_fault_on_one_twin_chip_climbs_to_the_bus_clear_and_recovers_once_cleared (one heater-off)", f"bounded: {B}test_a_success_mid_streak_fires_nothing_new_until_the_streak_returns_to_zero (once per episode); once: {B}test_a_raising_hook_is_logged_once_as_a_callback_failure_and_the_check_returns; race-free: {SC}a_bus_nak_storm_climbs_each_rung_once_per_bus_and_every_reader_recovers (one participant rung per reader)", DONE),
    ("U10", "a sensor/WLAN cycle fails", "R3"): (f"{B}test_the_ladder_fires_each_rung_once_in_order", f"{TB}test_a_sustained_fault_on_one_twin_chip_climbs_to_the_bus_clear_and_recovers_once_cleared", BUS_PROOF, BUS_FIX),
    ("U10", "a sensor/WLAN cycle fails", "R4"): (f"{B}test_the_ladder_fires_each_rung_once_in_order, {I2}test_recover_clears_then_re_constructs_with_the_stored_frequency_and_timeout", f"{TB}test_two_failing_readers_on_one_bus_run_each_bus_rung_once", BUS_PROOF, BUS_FIX),
    ("U10", "a sensor/WLAN cycle fails", "R5"): (R5[0] + f", {W}test_connect_loop_gives_up_after_repeated_hardware_failures_and_persists_both_entries", *R5[1:]),
    ("U10", "a sensor/WLAN cycle fails", "R6"): R6,
    ("U10", "a sensor/WLAN cycle fails", "R7"): R7,
    ("U10", "a reader's `_init_*", "R2"): (f"{SCD}test_setup_probes_reads_firmware_version_then_soft_resets_and_reads_the_temperature_offset, {SGP}test_initialize_success_probes_serial_number_then_self_test_then_resets, {BMP}test_setup_soft_resets_the_chip_once_after_its_id_check, {ISL}test_setup_sequence_is_id_reset_brownout_config (each setup resets its own chip once)", f"SGP40: {TB}test_the_real_task_graph_survives_concurrent_bus_load_including_a_real_general_call (its setup's general call under load); SCD30, BMP3XX, ISL29125: open (every twin boot runs their setup reset, but no twin test asserts it: gap, left)", f"bounded: a fixed sequence with one reset per setup, each wait bounded ({SGP}test_initialize_waits_out_each_command_and_the_reset_past_the_datasheet_maxima, {BMP}test_reset_raises_oserror_on_cmd_rdy_timeout, {ISL}test_reset_raises_when_the_config_registers_do_not_clear); once: {SCD}test_init_scd_returns_false_immediately_when_probe_fails_no_reset_reached, {SGP}test_init_sgp_fails_and_logs_when_setup_raises, {BMP}test_init_bmp_fails_and_logs_when_setup_raises, {ISL}test_init_returns_false_and_logs_an_init_error_and_reinitialises_the_controller; race-free: SGP40 as its L2, SCD30 {TB}test_an_scd30_soft_reset_mid_read_leaves_every_twin_sibling_read_valid (its reset beside sibling sessions), BMP3XX and ISL29125 open (no sibling interleaving of their setup reset)", "L1 named, each test biting in review.md or, for a test this review added, red on a planted fault (agent, 2026-10-27); open: three L2 cells and two race-free cells (left)"),
    ("U10", "a reader's `_init_*", "R3"): (f"{B}test_init_failed_rebuilds_the_controller_once_per_episode (_init_failed() runs recover(), whose clear is this rung), {I2}test_recover_clears_then_re_constructs_with_the_stored_frequency_and_timeout", SETUP_L2, f"bounded: {I2}test_clear_and_recover_end_a_held_scl_at_the_bus_timeout_on_the_fake_clock; once: {B}test_init_failed_rebuilds_the_controller_once_per_episode; " + SETUP_RACE, SETUP_DONE),
    ("U10", "a reader's `_init_*", "R4"): (f"{B}test_init_failed_rebuilds_the_controller_once_per_episode", SETUP_L2, f"bounded: {I2}test_clear_and_recover_end_a_held_scl_at_the_bus_timeout_on_the_fake_clock; once: {B}test_init_failed_rebuilds_the_controller_once_per_episode; " + SETUP_RACE, SETUP_DONE),
    ("U10", "a reader's `_init_*", "R5"): R5,
    ("U10", "a reader's `_init_*", "R6"): R6,
    ("U10", "a reader's `_init_*", "R7"): R7,
    ("U10", "any supervised task ends", "R5"): (R5[0] + f", {SS}test_supervise_tasks_logs_the_real_exception_of_a_crashed_task, {SS}test_supervise_tasks_logs_a_self_cancelled_task_as_a_persisted_error", *R5[1:]),
    ("U10", "any supervised task ends", "R6"): R6,
    ("U10", "any supervised task ends", "R7"): R7,
    ("U10", "a Timer arm fails", "R1"): (f"{B}test_trigger_loop_persists_an_arm_failure_no_task_saw_once_then_re_arms", f"{TP}test_a_reader_whose_trigger_cannot_arm_ends_restarts_and_reads_once_the_pool_frees", f"bounded: {B}test_a_failed_re_arm_persists_the_stored_failure_then_its_own_and_ends_the_loop (one re-arm per start); once: {B}test_a_failure_the_loop_persisted_is_not_persisted_again_by_the_restarts_re_arm; race-free: {B}test_two_wakes_finding_one_failed_arm_persist_it_once_however_they_interleave (the first wake's log write held open as the gate)", DONE),
    ("U10", "a Timer arm fails", "R5"): (f"{B}test_a_failed_timer_wakes_the_reader_and_logs_once", f"{TP}test_a_reader_whose_trigger_cannot_arm_ends_restarts_and_reads_once_the_pool_frees", R5[2], DONE),
    ("U10", "a Timer arm fails", "R6"): (R6[0], f"{TP}test_read_triggers_that_never_arm_end_at_the_budgets_reboot_with_one_entry", R6[2], DONE),
    ("U10", "a blocking `machine.I2C`/`machine.SPI` transfer never returns", "R7"): (f"{SC}a_cancelled_main_leaves_no_timer_feeding_the_watchdog (the structural half: Timers and IRQs fired as under a blocked loop)", f"{TS}watchdog_fault_block (twin scenario)", R7[2], DONE),
    ("U10", "the supervisor loop dies or the loop blocks", "R7"): (f"{SC}an_exception_escaping_the_supervisor_ends_every_feed, {SC}a_cancelled_main_leaves_no_timer_feeding_the_watchdog, {SS}test_a_fault_of_the_supervisor_itself_is_persisted_once_and_ends_it_unfed", f"{TS}watchdog_fault_supervisor_raise, {TS}watchdog_fault_main_exit, {TS}watchdog_fault_block (twin scenarios)", R7[2].replace("bounded and once:", f"once: {SS}test_a_fault_of_the_supervisor_itself_is_persisted_once_and_ends_it_unfed; bounded:"), DONE),
    ("U10", "a deferred config flush fails", "R1"): (f"{CM}test_self_heals_a_failed_flush_on_the_next_accepted_change", "open: no twin test heals a failed flush by the next PUT (gap, left)", f"bounded: no automatic re-write by design (the wear rule), {CM}test_many_failed_flushes_still_write_once_per_change; once: {CM}test_a_failed_flush_marks_the_store_unpersisted_until_a_good_flush; race-free: {CM}test_a_change_queued_behind_a_failing_flushs_log_write_heals_it_and_keeps_its_value (the failed flush's log write held open as the gate)", "race-free added (agent, 2026-10-27); open: L2, no twin test heals a failed flush by the next PUT (left; home: a twin config or webserver file)"),
    ("U10", "FRAM `verify_present", "-"): PROBE,
    ("U16", "`verify_present", "-"): PROBE,
}
# The U13 rows (lane CO3, agent, 2026-10-27): a rung the bus layer only propagates is the driver's or the supervisor's (U10).
CYC = {r: REVIEWED[("U10", "a sensor/WLAN cycle fails", r)] for r in ("R1", "R2", "R3", "R4", "R5")}
INIT = {r: REVIEWED[("U10", "a reader's `_init_*", r)] for r in ("R3", "R4", "R5", "R6")}
RAISE = f"{I2}test_nak_surfaces_as_eio_matching_real_rp2040_behavior, {I2}test_bus_busy_surfaces_as_etimedout, {I2}test_get_register_bytes_lets_a_bus_oserror_propagate (the raise reaches the driver)"
PROBE_RAISE = f"{I2}test_probe_raises_value_error_when_device_missing, {I2}test_device_probe_converts_any_oserror_to_value_error (the probe's refusal fails the setup)"
SCL_L2 = "open: no twin test holds SCL through the ladder; the twin's Pin.set_external_level() can plant it (gap, left; home: a new twin file)"
SCL_PROOF = f"bounded: {I2}test_clear_and_recover_end_a_held_scl_at_the_bus_timeout_on_the_fake_clock (driven clock); once: {I2}test_each_clear_and_recover_steps_recoveries_once_and_the_sequence_wraps; race-free: {I2}test_a_session_holding_the_bus_delays_clear_and_a_session_started_during_it_waits (a held session as the gate)"
DISPO = "disposition confirmed on the tree (agent, 2026-10-27)"
NA_SPI = "not reachable as a fault: the disposition leaves no SPI fault class for this rung"
REVIEWED.update({
    **{("U13", "I2C transfer raises `OSError", r): (RAISE + "; then U10's: " + CYC[r][0], CYC[r][1], CYC[r][2], "as U10's 'a sensor/WLAN cycle fails' " + r + ": the wrapper propagates, the rung is the driver's or the supervisor's; " + CYC[r][3]) for r in ("R1", "R2", "R5")},
    ("U13", "I2C transfer raises `OSError", "R3"): (f"{I2}test_clear_of_a_held_sda_sends_nine_pulses_and_a_stop, " + CYC["R3"][0], CYC["R3"][1], BUS_PROOF, BUS_FIX),
    ("U13", "I2C transfer raises `OSError", "R4"): (CYC["R4"][0], CYC["R4"][1], BUS_PROOF, BUS_FIX),
    ("U13", "I2C bus held at power-up / after an MCU-only reset", "R3"): (f"{I2}test_the_boot_clear_stops_pulsing_once_the_slave_releases_sda, {I2}test_the_boot_clear_gives_up_after_nine_pulses_and_construction_proceeds, {I2}test_the_boot_clear_reports_a_held_scl_and_pulses_nothing", "open: no twin test boots with a held line; the twin's Pin.set_external_level() can plant one (gap, left; home: a new twin file)", f"bounded: {I2}test_the_boot_clear_ends_at_the_bus_timeout_on_the_fake_clock (driven clock), the nine-pulse bound in its L1; once: {B}test_init_done_re_arms_the_rungs_and_reports_a_held_boot_bus_once_per_bus, {SCD}test_a_held_boot_bus_is_reported_once_at_setup; race-free: synchronous inside construction, before any task exists, and never again ({I2}test_a_later_init_never_clears)", "L1 and proofs named (agent, 2026-10-27); open: L2 (left)"),
    ("U13", "a slave holds **SCL** low", "R2"): ("per driver: U15's participant (R2) rows", "per driver: U15's rows", "per driver: U15's rows", "open: the U15 table's R2 rows (left)"),
    ("U13", "a slave holds **SCL** low", "R3"): (f"{I2}test_clear_with_scl_held_past_the_timeout_pulses_nothing, {I2}test_clear_waits_out_a_stretched_clock_and_still_sends_nine_effective_pulses", SCL_L2, SCL_PROOF, "L1 and proofs named (agent, 2026-10-27); open: L2 (left)"),
    ("U13", "a slave holds **SCL** low", "R4"): (f"{I2}test_recover_re_constructs_even_after_a_held_scl", SCL_L2, SCL_PROOF, "L1 and proofs named (agent, 2026-10-27); open: L2 (left)"),
    ("U13", "I2C `scan", "-"): ("not reachable: no product caller (git grep '.scan(' in src/ and buildgen/ finds only the wrapper, src/asy_i2c_driver.py:399-402)", "not reachable: as L1", "none: no product fault path", DISPO),
    **{("U13", "zero-length probe NAK → `ValueError", r): (PROBE_RAISE + "; then U10's: " + INIT[r][0], INIT[r][1], INIT[r][2], "as U10's `_init_*()` " + r + "; " + INIT[r][3]) for r in ("R3", "R4", "R5", "R6")},
    ("U13", "I2C/SPI construction raises", "R7"): (f"not reachable for a generated device: buildgen refuses the pins ({BG}test_i2c_pin_role_transposed_rejected, {BG}test_spi_pin_role_transposed_rejected, {BG}test_wireless_reserved_gpio_rejected_on_any_pin_field, test_buildgen_validate.py::test_i2c_pin_belonging_to_the_other_i2c_index_rejected)", "not reachable: as L1, every twin build is a generated device", "the R7 rung itself: U10's R7 rows", DISPO + "; a configuration not matching the hardware escalates to the reboot, which OR18.a intends"),
    ("U13", "SPI read of 32+ bytes raises `OSError", "R1"): (f"{SP}test_long_read_overrun_raises_oserror_eio_uncaught, {SP}test_device_read_propagates_rx_overrun_and_still_releases_the_lock, {FM}test_rx_overrun_on_block_0s_payload_read_is_absorbed_by_the_dual_copy_recovery", f"{TB}test_fram_recovers_after_an_injected_spi_read_fault, {TB}test_fram_chunk_loop_absorbs_a_transient_spi_rx_overrun", f"bounded: two copies, one read each, {FM}test_rx_overrun_on_every_payload_read_fails_cleanly_instead_of_killing_the_caller; race-free: the FRAM is alone on its bus and the lock is free after the fault ({SP}test_device_read_propagates_rx_overrun_and_still_releases_the_lock); once: open (no test counts one failed read's entries)", "L1/L2 named (agent, 2026-10-27); open: once (left; home: test_asy_fram_manager.py)"),
    ("U13", "SPI read of 32+ bytes raises `OSError", "R4"): (f"{FM}test_an_overrun_leaves_the_spi_bus_itself_reusable_rather_than_wedged", f"{TB}test_fram_recovers_after_an_injected_spi_read_fault", "none: the port clears the overrun flag inside the failing call, so no latched state is left to re-init", DISPO),
    ("U13", "SPI \"held bus\"", "R3"): (f"{SP}test_cs_pin_active_only_during_the_session, {SP}test_cs_pin_returns_to_inactive_after_exception_inside_session, {SP}test_cs_pin_returns_to_inactive_after_task_cancellation, {SP}test_session_begin_deasserts_cs_if_configure_raises_mid_session (CS inactive after every session)", NA_SPI, f"each transaction ends deselected; race-free: {SP}test_cs_pin_returns_to_inactive_after_task_cancellation (a session cancelled mid-transfer)", DISPO),
    ("U13", "SPI controller state", "R4"): (f"{SP}test_configure_is_applied_fresh_on_every_aenter, {SP}test_configure_is_applied_fresh_on_every_synchronous_session", NA_SPI, "each session re-configures the controller", DISPO),
    ("U13", "UART driver fault paths", "R1"): (f"{UD}test_cancel_read_timeout_unblocks_a_pending_wait, {UD}test_the_fragment_after_a_resync_is_discarded_never_decoded", f"{UL}test_one_sided_silence_forces_a_resync_and_both_sides_recover", "U17's 'a frame fails' row", "cross-reference only: U17's table carries it (left with it)"),
    ("U13", "UART driver fault paths", "R4"): ("not reachable: rp2 latches no receive error (ports/rp2/machine_uart.c:162-190)", "not reachable: as L1", "none: no fault class for a re-init", "cross-reference only: U17's 'controller re-init' row"),
})
rows, unit, l34_open = [], "", 0
supp = (tree / "audit/actions/SUPP_recovery.md").read_text(encoding="utf-8").split("## Actions")[0]
for line in supp.splitlines():
    if line.startswith("### U"):
        unit = line[4:].split(" ")[0]
    if not line.startswith("| ") or line.startswith(("| fault path", "|---")) or not unit:
        continue
    cols = [c.strip() for c in line.strip("|").split(" | ")]
    path = re.sub(r"\s*\(.*", "", cols[0]).replace("|", "/")[:110]
    rungs = sorted(set(re.findall(r"\bR([1-7])\b", " ".join(cols[1:]))))
    cells = {lv: [] for lv in ("L1", "L2", "L3", "L4")}
    for t in sorted(set(TEST.findall(line))):
        cells[level(t)].append(t.split("/")[-1])
    for r in rungs or ["-"]:
        shown = {lv: ", ".join(v) if v else ("queue_c" if lv in ("L3", "L4") else "open") for lv, v in cells.items()}
        l34_open += sum(1 for lv in ("L3", "L4") if not cells[lv])
        l1, l2, proof, gap = REVIEWED.get((unit, path, "R" + r if r != "-" else "-"), (shown["L1"], shown["L2"], "open", "open: the review confirms each cell or adds its test at the lowest level"))
        rows.append(f"| {unit}: {path} | {'R' + r if r != '-' else 'no rung named'} | {l1} | {l2} | {shown['L3']} | {shown['L4']} | {proof} | {gap} |")
OWNER = [  # owner row, part, L1, L2, L3, L4 (located by grep at the walked commit; each to confirm)
    ("OR115 modlwip hammer reach", "an `EAGAIN` seen while a zero-timeout poll said writable; A.U21.13's unpatched control run (faults.md)", "test_modlwip_eagain.py (lwip_host)", "not reachable at L2: the twin's sockets are host sockets, no modlwip", "queue_c", "queue_c (R4 H39)"),
    ("OR116/OR123 CRC16 arm", "both CRC modes, twin pair in both modes, the jumper pair, the reflash run", "test_asy_crc_checks.py, test_asy_uart_comm.py, test_asy_framing_codecs.py", "test_digital_twin_uart_link.py, test_digital_twin_uart_comm_hazard.py", "test_uart_crossover.py, uart_crossover_exchange.py (R1 H37)", "test_uart_link_crc16.py (R4 H38)"),
    ("OR122.a SystemCmd words", "resetconfig, erasefram, reboot, bootloader: function, refusal, error paths", "test_asy_system_service.py, test_asy_webserver_service.py, test_asy_config_manager.py", "test_digital_twin_bus_hazard_concurrency.py", "test_system_commands.py, system_command_*.py (R1-R3 H13/H14)", "test_system_commands_over_rest.py, test_reset_reasons.py"),
    ("OR122.a SystemCmd words", "near-miss words refused as \"Invalid\"; the OR119.a states raced deterministically", "open", "open", "queue_c (H13)", "queue_c"),
    ("OR122.a SystemCmd words", "bus and storage hazards; watchdog takeover, healthy and hung step; power loss per step; both GC stages", "test_reset_call_site_invariant.py", "open", "queue_c (H13/H14)", "queue_c"),
    ("OR130 supervisor feeds", "two feed sites pinned (L0 test_watchdog_feed_sites.py); the escalation's single feed; twin Run 3's feed_count stop", "test_asy_system_service.py", "Run 3 (scripts/_digital_twin_scenarios.py)", "test_watchdog_starvation.py, reboot_fallback_starves_the_watchdog.py", "not reachable at L4 beyond L3: no bench-only path"),
]
orows = [f"| {o} | {p} | {a} | {b} | {c} | {d} | open | open: confirm each named test reaches the part |" for o, p, a, b, c, d in OWNER]
conf = tree / "audit/b3/conformance.md"
conf.write_text(keep_header(conf) + f"""
## Recovery rungs (M.PROC.026)

Built by `audit/b3/conformance_walk.py` at `{head}` from SUPP_recovery.md's rung tables (agent, 2026-10-22): {len(rows)} rows, one per
fault path and rung the record names; a cell lists the tests the record itself cites, "open" where it cites none (L1/L2),
"queue_c" where silicon is the only way ({l34_open} L3/L4 cells). Bounded, once and race-free are each proven by the review;
{sum(1 for k in REVIEWED)} rows carry their reviewed L1/L2 cells and proofs (the walk's REVIEWED table, agent, 2026-10-27).

| fault path or owner row | rung or part | L1 | L2 | L3 | L4 | bounded / once / race-free | gap → action |
|---|---|---|---|---|---|---|---|
""" + "\n".join(rows) + """

## Owner test demands (M.PROC.027)

| fault path or owner row | rung or part | L1 | L2 | L3 | L4 | bounded / once / race-free | gap → action |
|---|---|---|---|---|---|---|---|
""" + "\n".join(orows) + """

## Bus hazards of B2 and B3 (A.U35.50) and wear and host churn (A.U35.51)

Open: one four-tier row per bus-facing change, and the wear-gate and host-churn table, from the integration head (B2).
""", encoding="utf-8")
QUEUE = [  # item, source, level, round (H row), gate, property proved
    ("silicon arm of the hardware memory gates", "A.U35.05 (3), M.PROC.037", "L3/L4", "R1 (H43)", "none", "a caught allocation failure prints the interpreter's wording and turns both hardware gates red"),
    ("lone-BMP3xx general call", "A.U35.21", "L3", "R1", "none", "the lone-BMP3xx general-call expectation, as A.U35.21 states it"),
    ("torn write on the bench reset race", "A.U35.40", "L4", "R3", "persistence_write", "the torn-write expectation on the bench reset race, as A.U35.40 states it"),
    ("silicon-only interaction, recombination and rung cells", "A.U35.08, A.U35.09, M.PROC.026", "L3/L4", "R1 (H71)", "none", f"every conformance.md queue_c cell ({l34_open} at the walked commit)"),
    ("OR115 lwIP stall, then the override hammer", "A.U21.14", "L4", "R4 (H39)", "flash_cycle", "the stall reproduces on the unpatched image and the override ends it"),
    ("OR116 CRC16 over the jumper and on a reflashed image", "A.S0930.05, A.S0930.06", "L3, L4", "R1 (H37), R4 (H38)", "flash_cycle (H38)", "both CRC modes interoperate over real wire"),
    ("the four SystemCmd words on the board", "A.S0930.28, .29, .39, .40", "L3/L4", "R1-R3 (H13, H14)", "persistence_write (resetconfig)", "function, refusal, timing and race of each word on silicon"),
    ("two-image GC proof", "SPECIFICATION.md E.6.1", "L3/L4", "R7 (H45)", "flash_cycle", "both GC stages hold on silicon"),
    ("bench trigger timestamps for the read stagger", "-", "L4", "R5 (H19)", "long_soak", "trigger spacing over a long run"),
    ("speed-probe bands on the bench Pi4, no board", "A.U35.23", "host", "R0 (H56)", "none", "the probe bands and step timings on the real host"),
    ("l3./l4. tunable rows", "M.PROC.028", "L3/L4", "R1/R4/R5 (H55)", "none", "each estimated tunable measured"),
]
qrows = [f"| {i} | {s} | {lv} | {r} | {g} | open (A.U35.49) | {p} |" for i, s, lv, r, g, p in QUEUE]
queue = tree / "audit/b3/queue_c.md"
queue.write_text(keep_header(queue) + f"\n## Items\n\nFrom M.PROC.029's list (agent, 2026-10-22); every H row checked present in audit/actions/C.md at `{head}`. Gates are\nthe default-off markers a round must name; a twin-first record is A.U35.49's.\n\n| item | source | level | round (H row) | gate | twin-first record | property proved |\n|---|---|---|---|---|---|---|\n" + "\n".join(qrows) + "\n", encoding="utf-8")
print(len(rows), "rung rows;", l34_open, "L3/L4 queue cells;", len(orows), "owner rows;", len(qrows), "queue rows")
