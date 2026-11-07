# The twin record's exception reasons (kept before the record goes, R0, 2026-11-02)
 `tests_hardware/twin_record.json` at the integration head `497b3eda`: 122 entries, 55 exception, 67 pass; 35 distinct
reasons for the exception entries. Each reason says why an instrument cannot run in the twin; the runner
(`scripts/record_twin_instrument_runs.py`) stays and R3 re-records once on the final tree.

- needs the bench bridge (network, WLAN role-reversal) (19):
  - `tests_hardware/bench/test_boot_order_and_triggers.py`
  - `tests_hardware/bench/test_bus_concurrency_under_api_load.py`
  - `tests_hardware/bench/test_end_to_end_timing.py`
  - `tests_hardware/bench/test_heap_under_connection_ceiling.py`
  - `tests_hardware/bench/test_hotspot_role_reversal.py`
  - `tests_hardware/bench/test_memory_stress_bench.py`
  - `tests_hardware/bench/test_modlwip_send_stall.py`
  - `tests_hardware/bench/test_network_resilience.py`
  - `tests_hardware/bench/test_reset_reasons.py`
  - `tests_hardware/bench/test_rest_endpoints_over_sta.py`
  - `tests_hardware/bench/test_scd30_frc_readiness_baseline.py`
  - `tests_hardware/bench/test_sensor_config_push_over_real_hardware.py`
  - `tests_hardware/bench/test_serving_heap_at_default_gc.py`
  - `tests_hardware/bench/test_system_commands_over_rest.py`
  - `tests_hardware/bench/test_ticks_ms_rollover.py`
  - `tests_hardware/bench/test_uart_link_crc16.py`
  - `tests_hardware/bench/test_uart_link_under_api_load.py`
  - `tests_hardware/bench/test_wifi_networking.py`
  - `tests_hardware/bench/test_wifi_radio_reinit.py`
- ends in the reset it exists to provoke (exit 3, the twin's simulated reset); its after-boot half reads the reset
  reason a production boot reports, and the twin boots no production image (bench/test_reset_reasons.py runs both halves
  on silicon) (2):
  - `tests_hardware/device_scripts/reset_code_invalid_record.py`
  - `tests_hardware/device_scripts/reset_code_stack_exhausted.py`
- silicon-only case of the flash test running it: a NeoPixel sweep needing the rig aiming the NeoPixel at the ISL29125
  (--allow-neopixel-sweep; the twin's ISL29125 fake is not optically coupled to the NeoPixel) (2):
  - `tests_hardware/device_scripts/isl29125_lighting_scenarios.py`
  - `tests_hardware/device_scripts/isl29125_mechanism_envelope.py`
- a bench serving script: it boots main() and holds its maps while the host's bench test drives the connection load, so
  alone in the twin it runs past the record's 60 s bound (its twin runs at -1 and 32768: about 112 s each, READY once,
  zero allocation failures) (1):
  - `tests_hardware/device_scripts/heap_under_connection_ceiling.py`
- a bench serving script: it boots main() and waits for the host's request sweep, which only the bench tier sends, so
  alone in the twin it runs past the record's 60 s bound (its twin runs at -1 and 32768: about 622 s each, webserver
  built, phases incomplete without the sweep, zero allocation failures) (1):
  - `tests_hardware/device_scripts/serving_at_default_gc.py`
- a bench serving script: the multi-chunk echo needs the bench board's UART jumper under main()'s own link and the
  host's reader load, so alone in the twin it runs past the record's 60 s bound (its twin runs at -1 and 32768: about
  192 s each, the initiator found, zero allocation failures) (1):
  - `tests_hardware/device_scripts/uart_link_echo_under_serving_load.py`
- gated, never run in the twin: the UF2 reflash is a real flash cycle (--allow-flash-cycle) and the toolchain
  re-verification fetches over the network and builds for about 8 min (--allow-toolchain-reverify) (1):
  - `tests_hardware/flash/test_toolchain_flash_boot.py`
- needs the per-run extra standard_debug_level that tests_hardware/conftest.py's standard-state repair passes; run alone
  it has none (KeyError). With it the twin run writes DebugLevel and reports valid (checked 2026-10-14) (1):
  - `tests_hardware/device_scripts/system_debug_level_set_standard.py`
- silicon-only case of the flash test running it: a blocking watchdog starvation (a blocking starvation never reaches
  the twin's asyncio watchdog: the run times out) (1):
  - `tests_hardware/device_scripts/watchdog_starvation_reset.py`
- silicon-only case of the flash test running it: a hung shutdown step's watchdog takeover (the twin reports 'starved
  the watchdog', its form of the reset) (1):
  - `tests_hardware/device_scripts/system_command_hang.py`
- silicon-only case of the flash test running it: interrupts-off windows, the UART break, the DMA ring's soft reset and
  the config-write window (the twin has no machine.disable_irq()/enable_irq(), no UART.sendbreak() and no rp2.DMA paced
  by a UART TX DREQ: streamed False) (1):
  - `tests_hardware/device_scripts/uart_dma_ring_interrupts_off.py`
- silicon-only case of the flash test running it: the 1.0/2.0 s mid-erase resets (the twin erases 256 KB in about 1.0 s,
  silicon about 2.2 s at 1 MHz, so they land after it) (1):
  - `tests_hardware/device_scripts/system_command_fram_erase.py`
- silicon-only case of the flash test running it: the 2^24 single-precision float boundary (the Unix port's float is
  double) (1):
  - `tests_hardware/device_scripts/float_boundary_2pow24.py`
- silicon-only case of the flash test running it: the FRAM CS hijack (the FRAM fake frames by write() pairing, ignoring
  CS) (1):
  - `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py`
- silicon-only case of the flash test running it: the ISL29125's real INT edge (the twin drives no INT edge into the
  reader's IRQ) (1):
  - `tests_hardware/device_scripts/isl29125_real_irq_edge.py`
- silicon-only case of the flash test running it: the driver read's control arm (the twin UART serves min(nbytes,
  queued), so the control span stays about 10 us) (1):
  - `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py`
- silicon-only case of the flash test running it: the held-SDA recovery (bit-banged pins hold no SDA in the twin: an
  open-drain Pin.value() reads only planted levels, and the twin's chips drive no pin) (1):
  - `tests_hardware/device_scripts/i2c_held_sda_recovery.py`
- silicon-only case of the flash test running it: the malformed country-code reaction (the twin WLAN has no scan()) (1):
  - `tests_hardware/device_scripts/wifi_country_code_reaction.py`
- silicon-only case of the flash test running it: the reboot's starvation fallback (a blocking starvation never reaches
  the twin's asyncio watchdog: the run times out) (1):
  - `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py`
- silicon-only case of the flash test running it: the suppressed arm breaking the high band (in the twin it runs after
  the state load in one session, on the Unix port's heap, not the RP2040's) (1):
  - `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py`
- silicon-only case of the flash test running it: the timer-callback drop under scheduler saturation (twin Timers are
  asyncio tasks: no scheduler queue, a synchronous script gives them no turn) (1):
  - `tests_hardware/device_scripts/scheduler_saturation_drop.py`
- silicon-only case of the flash test running it: the used-heap bound after a full system build (the twin's heap is the
  Unix port's, not the RP2040's 264 KB) (1):
  - `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py`
- silicon-only case of the flash test running it: write protection gating a real write and read (the twin's FRAM fake
  keeps the data a WP-gated write would not reach on silicon) (1):
  - `tests_hardware/device_scripts/fram_write_protect_roundtrip.py`
- silicon-only case: the boot import after a genuine hard reset (the twin boots no production image, so no boot lines
  arrive) (1):
  - `tests_hardware/flash/test_reboot_persistence.py`
- silicon-only case: the suppressed arm breaking the high band (in the twin it runs after the state load in one session,
  on the Unix port's heap, not the RP2040's) (1):
  - `tests_hardware/flash/test_heap_layout.py`
- silicon-only case: the used-heap bound after a full system build (the twin's heap is the Unix port's, not the RP2040's
  264 KB); and the single-core timing headroom is a passive soak (--soak-duration) (1):
  - `tests_hardware/flash/test_memory_stress.py`
- silicon-only case: write protection gating a real write and read (the twin's FRAM fake keeps the data a WP-gated write
  would not reach on silicon) (1):
  - `tests_hardware/flash/test_fram_storage.py`
- silicon-only cases: a blocking watchdog starvation and the reboot's starvation fallback (a blocking starvation never
  reaches the twin's asyncio watchdog: the run times out) (1):
  - `tests_hardware/flash/test_watchdog_starvation.py`
- silicon-only cases: interrupts-off windows, the UART break, the DMA ring's soft reset and the config-write window (the
  twin has no machine.disable_irq()/enable_irq(), no UART.sendbreak() and no rp2.DMA paced by a UART TX DREQ: streamed
  False), and the driver read's control arm (the twin UART serves min(nbytes, queued), so the control span stays about
  10 us) (1):
  - `tests_hardware/flash/test_uart_crossover.py`
- silicon-only cases: the 1.0/2.0 s mid-erase resets (the twin erases 256 KB in about 1.0 s, silicon about 2.2 s at 1
  MHz, so they land after it) and a hung shutdown step's watchdog takeover (the twin reports 'starved the watchdog', its
  form of the reset) (1):
  - `tests_hardware/flash/test_system_commands.py`
- silicon-only cases: the 2^24 single-precision float boundary (the Unix port's float is double), the malformed
  country-code reaction (the twin WLAN has no scan()), and the timer-callback drop under scheduler saturation (twin
  Timers are asyncio tasks: no scheduler queue, a synchronous script gives them no turn); and the SCD30 clock-stretch
  watch is a soak (--soak-duration: a real stretch comes about once a day) (1):
  - `tests_hardware/flash/test_bus_electrical_timing.py`
- silicon-only cases: the ISL29125's real INT edge (the twin drives no INT edge into the reader's IRQ), the held-SDA
  recovery (bit-banged pins hold no SDA in the twin) and the FRAM CS hijack (the FRAM fake frames by write() pairing,
  ignoring CS) (1):
  - `tests_hardware/flash/test_bus_concurrency.py`
- silicon-only cases: the two NeoPixel sweeps need the rig aiming the NeoPixel at the ISL29125 (--allow-neopixel-sweep;
  the twin's ISL29125 fake is not optically coupled to the NeoPixel) and the SGP40 cadence is a 600 s soak
  (--soak-duration); twin fidelity: the SGP40 fake's raw walk (1000 ticks a sample, not datasheet-derived) drives the
  real VOC algorithm's index to its floor of 1 for all 8 post-blackout samples in about 7% of runs (21 of 300
  simulated), which the frozen-algorithm check reads as frozen (1):
  - `tests_hardware/flash/test_sensor_accuracy.py`
- silicon-only: the watchdog takeover after an accepted command - the twin reports it as 'starved the watchdog', its
  form of the reset (1):
  - `tests_hardware/device_scripts/reset_code_command_incomplete.py`
- the flash test running it: the SGP40 cadence is a 600 s soak (--soak-duration) (1):
  - `tests_hardware/device_scripts/sgp40_sample_cadence.py`
