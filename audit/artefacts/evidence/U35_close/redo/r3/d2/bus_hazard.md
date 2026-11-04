Bus-hazard rule for B3's, B4's and B6's bus-facing changes: three kinds x four tiers (lane D2, agent, 2026-11-04)

Read-only on `S/wt-u35int` at `17688315`. Kinds (CLAUDE.md, SPEC C.8): S same-device read vs write, X cross-device
interleave (where the bus is shared on any wiring), W address/command sweep. Tiers: mock `tests/` (L1), twin (L2),
flash `tests_hardware/flash/` + device scripts (L3), bench `tests_hardware/bench/` (L4). "gen." is
`tests/test_bus_hazard_generated.py` (per device x per I2C bus, from the TOMLs, so it re-ran on every final driver).
L3/L4 cells have their first run on the final image in round 1. Names checked present at `17688315`.

## B3: the FRAM SPI clock 1 -> 8 MHz (`asy_fram_driver.py:124`)
- S L1: `test_bus_hazard_multi_device.py::test_spi_async_and_synchronous_sessions_share_one_bus_without_cs_overlap`, `::test_an_erase_lets_a_write_and_a_read_in_flight_finish_whole_refuses_later_ones_and_holds_each_unit_whole`; `test_asy_fram_driver.py::test_same_device_concurrent_read_and_write_never_corrupt_each_other`; the 8 MHz init pinned by `test_asy_fram_wire_trace.py` (`_INIT_EVENT`)
- S L2: `test_digital_twin_bus_hazard_concurrency.py::test_the_erase_racing_a_logger_write_never_tears_a_chunk`; the twin models no baud (fidelity row), so L2 proves the sequence, not the clock
- S L3: `flash/test_bus_concurrency.py::test_fram_same_device_read_write_concurrency`, `::test_fram_erase_racing_a_chunk_write_leaves_no_torn_chunk`; `flash/test_fram_storage.py::test_fram_chunk_write_read_roundtrips_against_the_real_chip`; plus round 1's overnight `long_fram.py` (needs its edit, `round1_sheet.md` item 14)
- S L4: `bench/test_bus_concurrency_under_api_load.py::test_fram_erase_under_api_load`
- X all tiers: reason: the FRAM is alone on `spi0` on all six devices (`devices/*.toml`, one `bus = "spi0"` each); `SPI_HAZARD_CATALOG` is empty and gen. fails loud for a shared SPI bus with no adapter (`test_a_shared_spi_bus_fails_loud_for_a_driver_with_no_catalog_adapter`)
- W L1: `test_asy_fram_wire_trace.py` (every opcode of setup, write, read and clear against the golden), `test_bus_hazard_multi_device.py::test_the_erase_writes_each_status_byte_then_every_unit_once_ascending_at_the_parts_address_width`
- W L2: `test_digital_twin_fram.py::test_fram_rdid_table_matches_the_driver`, `::test_opcode_address_and_data_in_one_write_are_refused`
- W L3: `flash/test_chip_conformance.py::test_fram_matches_its_twin_fake`
- W L4: reason: E.6.6 `flash-only-bus-checks` (no REST route reaches an opcode)

## B4 (a): one clock-out routine for the boot clear and `clear()`/`recover()`
- S: reason: the routine addresses no device (nine SCL pulses, then STOP), so it has no same-device read/write
- X L1: `test_bus_hazard_multi_device.py::test_a_recovery_during_a_held_bus_clear_lets_no_sibling_transfer_in`, `::test_a_host_stall_inside_a_stretched_clear_does_not_read_as_a_held_clock`; gen. `..._a_bus_recovery_does_not_disturb_concurrent_sibling_reads_across_timing_offsets`
- X L2: `test_digital_twin_bus_hazard_concurrency.py::test_a_bus_recovery_does_not_disturb_concurrent_sibling_reads`, `::test_a_sustained_fault_on_one_twin_chip_climbs_to_the_bus_clear_and_recovers_once_cleared`; `test_digital_twin_held_i2c_line.py::test_a_bus_held_at_power_up_is_clocked_free_before_construction_and_reported_once`
- X L3: `flash/test_bus_concurrency.py::test_a_held_sda_line_is_cleared_and_every_device_answers`
- X L4: reason: E.6.6 `flash-only-bus-checks` ("a held SDA line cleared")
- W: reason: no address; the bus it serves is swept by gen. `..._each_real_occupant_never_touches_an_unexpected_address` (L1) and `flash/test_bus_concurrency.py::test_bus_topology_autodetect_address_and_reserved_range_sweep` (L3)

## B4 (b): the I2C "no bus" contract gone (pre-audit `None` returns, `configure()`'s `RuntimeError`)
- S, X L1: `test_bus_hazard_multi_device.py::test_a_sensor_cancelled_inside_its_session_leaves_the_bus_free_and_the_sibling_read_valid`; L2: `test_digital_twin_bus_hazard_concurrency.py::test_a_sensor_task_cancelled_inside_its_session_leaves_the_bus_usable`
- S, X L3: `flash/test_bus_concurrency.py::test_i2c_and_spi_deinit_are_silent_noops_and_each_bus_id_is_a_singleton`
- S, X, W L4: reason: no REST route deinits a bus (E.6.6 `flash-only-bus-checks`: "deinit() and the bus singletons"); rp2's `deinit()` is a no-op (F.5.1)
- W: reason: the change adds or drops no transfer

## B4 (c): BMP3XX back to forced mode, the STATUS poll and the 6-byte burst from 0x04
- S L1: gen. `test_<device>_<bus>_same_occupant_own_write_does_not_disturb_own_concurrent_read_across_timing_offsets` (BMP3XX has a `write_once` adapter); `test_asy_bmp3xx_driver.py::test_a_pres_offset_put_during_a_conversion_does_not_change_the_stored_sample`
- S L2: `test_digital_twin_bus_hazard_concurrency.py::test_a_bmp3xx_setup_reset_mid_read_leaves_every_twin_sibling_read_valid`, the twin graph test's per-cycle register check (`_PER_CYCLE_REGISTER`)
- S L3: `flash/test_bus_concurrency.py::test_bmp3xx_same_device_read_write_concurrency`, `::test_bmp3xx_alone_survives_a_general_call`
- S L4: `bench/test_bus_concurrency_under_api_load.py::test_bmp3xx_config_write_does_not_disturb_its_own_concurrent_reads_under_api_load` (gated)
- X L1: `test_bus_hazard_multi_device.py::test_cross_device_bmp3xx_and_sgp40_interleave_and_both_stay_correct`, `::test_sgp40_general_call_reset_does_not_disturb_a_concurrent_bmp3xx_read`; X L2: the twin graph test (wozi i2c1); X L3: reason: dev's BMP3XX is alone on i2c0, so dev has no neighbour (wozi is never flashed); X L4: as L3
- W L1: `test_asy_bmp3xx_driver.py::test_never_touches_any_address_but_its_own`, gen. `..._each_real_occupant_never_touches_an_unexpected_address`; W L2: the twin graph test; W L3: `test_bus_topology_autodetect_address_and_reserved_range_sweep`, `flash/test_chip_conformance.py::test_bmp3xx_matches_its_twin_fake`; W L4: reason, E.6.6 `flash-only-bus-checks`

## B4 (d): the ISL29125 shadow compare back to after a failed write
- S L1: `test_asy_isl29125_driver.py::test_concurrent_read_and_write_never_interleave_on_the_wire`, `::test_a_clean_cycle_reads_no_config_snapshot`; gen. same-occupant case
- S L2: tw. `isl29125_config_put_during_get_loops`; S L3: `flash/test_bus_concurrency.py::test_isl29125_same_device_read_write_concurrency`; S L4: `bench/..._isl29125_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load` (gated)
- X L1: `test_bus_hazard_multi_device.py::test_cross_device_isl29125_and_sgp40_interleave_and_both_stay_correct`, `::test_an_isl29125_reapply_mid_read_leaves_every_sibling_read_valid`; X L2: `test_digital_twin_bus_hazard_concurrency.py::test_an_isl29125_reapply_mid_read_leaves_every_twin_sibling_read_valid`; X L3: `flash/test_bus_concurrency.py::test_isl29125_cross_device_concurrency_with_its_i2c1_neighbours`, `::test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads`; X L4: the bench arm above
- W L1: `test_asy_isl29125_driver.py::test_never_touches_any_address_but_its_own`; W L2: the twin graph test; W L3: the topology sweep, `flash/test_chip_conformance.py::test_isl29125_matches_its_twin_fake`; W L4: reason, E.6.6

## B4 (e): the SGP40 restart back to the restore (one FRAM chunk read per restart)
- S L1: `test_asy_sgp40_driver.py::test_a_task_restart_after_fed_samples_restores_the_backup`, `::test_simultaneous_restore_and_backup_in_one_cycle_reads_then_rewrites_the_same_buffer`; S L2: `test_digital_twin_bus_hazard_concurrency.py::test_three_concurrent_sgp40_measurements_each_send_and_read_their_own_words`; S L3: `flash/test_fram_storage.py::test_sgp40_voc_state_backs_up_to_and_restores_from_the_real_chip`, `flash/test_bus_concurrency.py::test_sgp40_concurrent_sessions_each_get_a_tick`; S L4: `bench/test_end_to_end_timing.py::test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly` (gated)
- X: the restore is a chunk read on the FRAM's own bus (B3's X reason); the SGP40's I2C traffic is unchanged by the restore (gen. and the SGP40 rows above)
- W: reason: no new transfer kind (one chunk read through `_FRAMBaseChunk`)

## B6: `_rx_stop()`, the receive ring's teardown (UART kinds, SPEC J: same-instance concurrency, both ends transmitting, frame-field sweep)
- L1: the driver tests that stop an armed ring against `tests/rp2.py`'s raising fake (`test_asy_uart_driver.py::test_deinit_calls_real_hardware_deinit_and_clears_poller`, `::test_reinit_deinits_the_previous_bus_first`, `::test_a_re_init_masks_first_and_fails_the_next_read`, `::test_cancel_or_deinit_during_the_drain_wait_returns_false`, `::test_ready_survives_a_concurrent_deinit_mid_loop`); `tests/test_uart_comm_hazard.py` (all three kinds, both CRC modes); `tests/test_uart_comm_cancel_sweep.py`
- L2: every dev twin boot (the twin's DMA fake raises for a busy chained channel, B6 row 1); `test_digital_twin_uart_comm_hazard.py` (two initiations, `clear()` racing, both ends transmitting); `test_digital_twin_uart_field_sweep.py` (W)
- L3: `flash/test_uart_crossover.py::test_comm_hazards_are_serialised_refused_or_recovered` (its script re-inits a driver, `uart_comm_hazards.py:111`), `::test_silence_and_desync_recover_within_the_resync_bound_and_a_mismatch_fails_loudly` (`uart_crossover_recovery.py:54, :63`), `::test_a_soft_reset_during_traffic_leaves_no_running_ring`
- L4: `bench/test_uart_link_under_api_load.py::test_a_hazard_run_under_the_readers_load_reports_every_verdict` for the three kinds; `_rx_stop()` itself: reason, a link deinit happens only on a task restart, which no REST route forces (L3 is its silicon tier)

## Result
Every change has a test or a reason per kind and tier: 7 changes, 84 cells. No missing cell found.
