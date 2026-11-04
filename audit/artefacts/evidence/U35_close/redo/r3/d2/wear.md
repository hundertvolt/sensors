Wear table: every hardware test that writes the flash filesystem or the SCD30 NVM, or reflashes (lane D2, agent, 2026-11-04)

Read-only on `S/wt-u35int` at `17688315`. Sources: the markers on every `tests_hardware/{flash,bench}/test_*.py`
function (an awk walk, 32 marked tests), README's budget table (`tests_hardware/README.md:2009-2019`), the 18 device
scripts that build the system (`device.build_system(`/`device.main(`) and their 25 callers. FRAM writes are not wear
(CLAUDE.md). Owned = the write is the test's subject, behind its marker; prerequisite = unmarked by the owner's rule
(2026-09-18), pinned in `tests_scripts/test_persistence_write_marker_completeness.py`. dev has 8 config stores (WIFI,
NTP, SYSTEM, SCD30, SGP40, BMP3XX, ISL29125, NOTIFY: `_collect_config_stores()` in the generated module).

## Owned: flash filesystem (`persistence_write`)
| test | writes | marker |
|---|---|---|
| flash `test_config_floats_round_trip_unchanged` | 1 scratch | persistence_write |
| flash `test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration` | 7 scratch | persistence_write, neopixel_sweep |
| flash `test_a_real_config_write_during_traffic_loses_no_frame` | 1 per CRC mode, 2 | persistence_write |
| flash `test_link_transactions_during_config_writes_are_recorded` | 5 per CRC mode, 10 | persistence_write |
| flash `test_config_value_survives_a_genuine_hard_reset` | 2 | persistence_write |
| flash `test_config_reset_deletes_every_config_file_and_reboots` | 8 defaults, 1 damaged file, 8 deletions | persistence_write |
| flash `test_a_hung_shutdown_step_ends_in_a_watchdog_reset` x2 | per command 8 defaults and up to 8 deletions | persistence_write |
| flash `test_flash_write_loop_gap_is_recorded` | 1 (1 KiB, created and removed) | persistence_write |
| bench, 2 each (change, restore): `test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value`, `test_representative_put_round_trips_over_the_hotspot_link`, `test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly`, `test_garbage_ntp_host_via_rest_config_degrades_and_recovers_cleanly`, `test_garbage_ssid_via_rest_config_is_handled_gracefully`, `test_console_output_with_a_non_reading_usb_host_never_starves_the_watchdog`, `test_a_flash_write_holding_interrupts_off_keeps_the_wifi_link`, `test_bmp3xx_oversampling_and_filter_push_over_real_rest_and_readback`, `test_isl29125_resolution_range_and_ir_comp_push_over_real_rest_and_readback` | 18 | persistence_write |
| bench `test_isl29125_config_write_..._under_api_load`, `test_bmp3xx_config_write_..._under_api_load` | up to 5 each, 10 | persistence_write |
| bench `test_a_wrong_password_over_the_hotspot_reopens_the_hotspot` | 1 | persistence_write |
| bench `test_real_credentials_put_succeeds_and_confirms_accepted_values` | 1 | persistence_write |
| bench `test_a_second_failed_streak_goes_silent_and_links_on_a_later_attempt` | 0 (AND-gate on the previous test's write) | persistence_write, soak_duration |
| bench `test_config_reset_over_rest_brings_back_the_defaults` | 8 deletions, 8 defaults, up to 8 restores | persistence_write |

## Owned: SCD30 NVM
| test | writes | marker |
|---|---|---|
| flash `test_scd30_same_device_read_write_concurrency` | 1 (AmbPres re-sent) | persistence_write |
| flash `test_scd30_config_write_does_not_disturb_concurrent_sibling_reads` | 2 | persistence_write, scd30_extra_write |
| flash `test_scd30_argument_reaction_is_recorded` | up to 3 | persistence_write, scd30_extra_write |
| bench `test_scd30_config_write_..._under_api_load` | up to 3 | persistence_write, scd30_extra_write |
| bench `test_scd30_altitude_takes_effect_while_ambient_pressure_is_zero` | 4 | persistence_write, scd30_extra_write |

## Owned: reflash (`flash_cycle`)
| test | flashes | marker |
|---|---|---|
| flash `test_real_uf2_reflash_and_boot_smoke_test` | 1 | flash_cycle |
| bench `test_the_link_suite_runs_on_a_crc16_image` | 2 (CRC16 image, back) | flash_cycle |
| bench `test_send_stall_on_the_unpatched_image` | 2 (control image, back) | flash_cycle |
| bench `test_ticks_ms_rollover_is_survived` | 1 (tick-offset image; the next round flashes its own) | flash_cycle, multi_day_rollover |

## Prerequisite (unmarked, allowed)
| writer | writes | where pinned |
|---|---|---|
| the 25 scratch builds of the default tiers: flash `test_every_fram_wired_module_gets_a_real_chunk_after_a_full_system_build` 1, `test_heap_layout.py`'s two arms 2, `test_c_stack_peak_is_within_half_the_limit` 1, `test_real_gc_heap_headroom_survives_a_full_system_build` 1, `test_routine_no_yield_stretches_stay_under_the_gc_term` 1, `flash/test_bus_concurrency.py`'s erase race and reboot 2, `flash/test_system_commands.py`'s reboot-paused 1, mid-erase 3, erase-in-flight 2, bootloader 1, erase-blanks 1, refused 1; bench `test_reset_reasons.py`'s boot-phase hangs 5, incomplete command 1, C-stack 1, `test_every_source_and_route_fits_a_small_free_run` 1 | up to 8 defaults each into `hwtest-scratch/` and the directory's removal: up to 200 file writes (a boot-phase hang before the setups writes fewer) | README budget table, default row |
| `joined_hotspot` (role-reversal module) | 2 (SSID clear, restore) | `_KNOWN_PERSISTING_HELPERS` |
| `_recover_stale_dut_credentials()` | 0-1 | `_KNOWN_PERSISTING_HELPERS` |
| `--repair-standard-state` repairs, an aborted run's leftover | 0 or more, 0-1 | `_KNOWN_PERSISTING_HELPERS` (`_repair`, `_repair_leftover`) |
| `scd30_measuring`'s start command | SCD30 NVM 0-1 per session | README budget table |
| `sgp40_sample_cadence.py` (soak `test_sgp40_sample_cadence`) | 8 defaults | default row (soak runner) |

## Markers checked
- All 32 marked tests appear in README's budget table with the same store and count; every table row names a
  marked test. Spot checks beyond the completeness test: the SCD30 NVM writers among the device scripts
  (`scd30_same_device_rw_concurrency.py`, `scd30_start_continuous_measurement.py`, `scd30_argument_reaction.py`,
  `bus_concurrency_scd30_write_vs_siblings.py`) are each run by a gated test or `scd30_measuring`; the product's setup
  sends no 0x0010 (the measurement status is NVM, Interface Description 1.4.1), so a setup reset writes no NVM.
- Wrong markers found: none.

## Round 1's wear budget (dev), from the rows above
- Flash cycles: 1 (the final image) + 1 (smoke) + 2 (CRC16) + 2 (send stall) = 6; the rollover round adds 1 and leaves
  the tick-offset image (1 more to restore the final image) = 8 with G6.
- Flash filesystem, owned: flash tier 1+7+2+10+2+17+up to 32+1 = up to 72; bench tier 18+10+1+1+up to 24 = up to 54;
  owned total up to 126 file writes and deletions.
- Flash filesystem, prerequisite: up to 200 scratch defaults writes (25 builds) + 8 (soak) + 2 (hotspot) + 0-1 + repairs.
- SCD30 NVM: up to 13 owned (1 + up to 12 with both flags) + at most 1 start command = up to 14.
- Manual (owner at the bench, each step states it first): flash up to 2 + 63 + resetconfig's; NVM up to 2 + 22.
- The W25Q16JV holds at least 100K program-erase cycles per sector (Winbond W25Q16JV Rev F, section 1 "Features",
  PDF p. 5); littlefs spreads the writes, so a round's few hundred small writes stay far inside it.
