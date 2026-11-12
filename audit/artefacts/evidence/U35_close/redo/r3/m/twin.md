# R3 lane M: the twin instrument runner, both stages (agent, 2026-11-04)

Checked first: `scripts/record_twin_instrument_runs.py` drives the twin only. Its flash run is `pytest tests_hardware/flash
--twin`, where `board` is a `TwinBoard` (`tests_hardware/conftest.py:200-204`), `bench` skips (`:219-220`), the autouse
session fixtures act on no board (`_board_if_present()`, `:313`), picotool returns early under `--twin`
(`flash/test_system_commands.py:271-273`), and the reflash and toolchain tests skip without `--allow-flash-cycle` /
`--allow-toolchain-reverify`, which the runner never passes; the device scripts run through `TwinBoard`; the bench tier is
recorded as needing the bridge without a run. The run sat in its own network namespace (`run.sh`), no serial node
present. Nothing could reach a board or the host's network config.

- **`r3m_twinrec`**: rc 0, 2,097 s. Reasons passed with `--reasons`: the 35 kept in
  `S/u35r/knowledge/twin_record_exceptions.md` (55 paths), and a placeholder for every other path so the record is
  written (decision, agent, 2026-11-04: the runner refuses a failure without a reason, and each new one was to be
  classed here). 126 instruments: 68 pass, 58 exception (19 bench, recorded without a run; 39 reds). The record moved
  to `m/twin_record.json` (the tree is clean); the reasons in it are the classed ones below.
- **`r3m_twinrec_texts`**: rc 0, 2,097 s: the runner's own loop again (its functions imported, the record not written),
  keeping each failure's text (`m/data/twin_problems.json`). 36 reds: the same set less three intermittent ones, each then
  reproduced on its own: `r3m_listener_repro` (20 back-to-back runs, 19 red with EADDRINUSE) and `r3m_voc_repro`
  (15 runs at 32768, 2 red, "algorithm looks frozen"; `r3m_voc_repro1` timed one run, 77 s).

Against R0's record (`ffdee74e^`): `system_command_fram_erase.py` now passes (B3's 50/150/250 ms cuts land inside the
twin's erase), `heap_layout_after_full_boot_sequence.py` and `test_heap_layout.py` now pass at -1, and four
instruments are new (`reset_code_loop_end.py`, `setup_resets_each_chip_once.py` passing,
`listener_close_leaves_the_pcb_pools.py`, `test_modlwip_listener_close.py`). The held SDA is red as expected (its
reason row). No class (a): no red is a product defect.

## The 39 reds (19 bench instruments aside), classed: (a) product, (b) twin fidelity, (c) test

| instrument | -1 / 32768 | class | reason (as in `m/twin_record.json`) |
|---|---|---|---|
| `device_scripts/float_boundary_2pow24.py` | exception / exception | (b) | silicon-only case of the flash test running it: the 2^24 single-precision float boundary (the Unix port's float is double) |
| `device_scripts/fram_cs_hijack_fault_injection_and_recovery.py` | exception / exception | (b) | silicon-only case of the flash test running it: the FRAM CS hijack (the FRAM fake frames by write() pairing, ignoring CS) |
| `device_scripts/fram_write_protect_roundtrip.py` | exception / exception | (b) | silicon-only case of the flash test running it: write protection gating a real write and read (the twin's FRAM fake keeps the data a WP-gated write would not reach on silicon) |
| `device_scripts/heap_headroom_after_full_system_build.py` | exception / exception | (b) | silicon-only case of the flash test running it: the used-heap bound after a full system build (the twin's heap is the Unix port's, not the RP2040's 264 KB) |
| `device_scripts/heap_layout_after_full_boot_sequence.py` | pass / exception | (b) | the same as flash/test_heap_layout.py: at gc.threshold(32768) only, the live arm's 55 blocks above the high band (bound 32), the stage applied before the script's imports |
| `device_scripts/heap_under_connection_ceiling.py` | exception / exception | (c) | a bench serving script: it boots main() and holds its maps while the host's bench test drives the connection load, so alone in the twin it runs past the record's 60 s bound (its twin runs at -1 and 32768: about 112 s each, READY once, zero allocation failures) |
| `device_scripts/i2c_held_sda_recovery.py` | exception / exception | (b) | silicon-only case of the flash test running it: the held-SDA recovery (bit-banged pins hold no SDA in the twin: an open-drain Pin.value() reads only planted levels, and the twin's chips drive no pin) |
| `device_scripts/isl29125_lighting_scenarios.py` | exception / exception | (b) | silicon-only case of the flash test running it: a NeoPixel sweep needing the rig aiming the NeoPixel at the ISL29125 (--allow-neopixel-sweep; the twin's ISL29125 fake is not optically coupled to the NeoPixel) |
| `device_scripts/isl29125_mechanism_envelope.py` | exception / exception | (b) | silicon-only case of the flash test running it: a NeoPixel sweep needing the rig aiming the NeoPixel at the ISL29125 (--allow-neopixel-sweep; the twin's ISL29125 fake is not optically coupled to the NeoPixel) |
| `device_scripts/isl29125_real_irq_edge.py` | exception / exception | (b) | silicon-only case of the flash test running it: the ISL29125's real INT edge (the twin drives no INT edge into the reader's IRQ) |
| `device_scripts/listener_close_leaves_the_pcb_pools.py` | exception / pass | (c) | intermittent in the twin, root cause reproduced (19 of 20 back-to-back runs, r3m_listener_repro): the twin half's bind without SO_REUSEADDR on 127.0.0.1:50100 is refused with EADDRINUSE (98) while that port sits in TIME_WAIT on the host stack, left by its own round trip within the last 60 s or by any connection whose ephemeral port was 50100 (inside Linux's 32768-60999 range); silicon's lwIP is fresh per session |
| `device_scripts/reboot_fallback_starves_the_watchdog.py` | exception / exception | (b) | silicon-only case of the flash test running it: the reboot's starvation fallback (a blocking starvation never reaches the twin's asyncio watchdog: the run times out) |
| `device_scripts/reset_code_command_incomplete.py` | exception / exception | (b) | silicon-only: the watchdog takeover after an accepted command - the twin reports it as 'starved the watchdog', its form of the reset |
| `device_scripts/reset_code_invalid_record.py` | exception / exception | (b) | ends in the reset it exists to provoke (exit 3, the twin's simulated reset); its after-boot half reads the reset reason a production boot reports, and the twin boots no production image (bench/test_reset_reasons.py runs both halves on silicon) |
| `device_scripts/reset_code_loop_end.py` | exception / exception | (b) | imports the board's own main.py (the boot entry it ends), which the twin's filesystem does not hold: the twin boots no production image (ImportError: no module named 'main'); bench/test_reset_reasons.py runs it on silicon |
| `device_scripts/reset_code_stack_exhausted.py` | exception / exception | (b) | ends in the reset it exists to provoke (exit 3, the twin's simulated reset); its after-boot half reads the reset reason a production boot reports, and the twin boots no production image (bench/test_reset_reasons.py runs both halves on silicon) |
| `device_scripts/scheduler_saturation_drop.py` | exception / exception | (b) | silicon-only case of the flash test running it: the timer-callback drop under scheduler saturation (twin Timers are asyncio tasks: no scheduler queue, a synchronous script gives them no turn) |
| `device_scripts/serving_at_default_gc.py` | exception / exception | (c) | a bench serving script: it boots main() and waits for the host's request sweep, which only the bench tier sends, so alone in the twin it runs past the record's 60 s bound (its twin runs at -1 and 32768: about 622 s each, webserver built, phases incomplete without the sweep, zero allocation failures) |
| `device_scripts/sgp40_sample_cadence.py` | exception / exception | (c) | the flash test running it: the SGP40 cadence is a 600 s soak (--soak-duration) |
| `device_scripts/sgp40_voc_algorithm_quality.py` | pass / exception | (b) | intermittent, reproduced 2 of 15 at gc.threshold(32768) (r3m_voc_repro): the SGP40 fake's raw walk (1000 ticks a sample, not datasheet-derived) leaves the real VOC algorithm's integer index constant over the 8 post-blackout samples (observed 2 and 5, not only the floor of 1), which the frozen-algorithm check reads as frozen |
| `device_scripts/system_command_hang.py` | exception / exception | (b) | silicon-only case of the flash test running it: a hung shutdown step's watchdog takeover (the twin reports 'starved the watchdog', its form of the reset) |
| `device_scripts/system_debug_level_set_standard.py` | exception / exception | (c) | needs the per-run extra standard_debug_level that tests_hardware/conftest.py's standard-state repair passes; run alone it has none (KeyError). With it the twin run writes DebugLevel and reports valid (checked 2026-10-14) |
| `device_scripts/uart_dma_ring_interrupts_off.py` | exception / exception | (b) | silicon-only case of the flash test running it: interrupts-off windows, the UART break, the DMA ring's soft reset and the config-write window (the twin has no machine.disable_irq()/enable_irq(), no UART.sendbreak() and no rp2.DMA paced by a UART TX DREQ: streamed False) |
| `device_scripts/uart_driver_read_never_blocks_the_loop.py` | exception / exception | (b) | silicon-only case of the flash test running it: the driver read's control arm (the twin UART serves min(nbytes, queued), so the control span stays about 10 us) |
| `device_scripts/uart_link_echo_under_serving_load.py` | exception / exception | (c) | a bench serving script: the multi-chunk echo needs the bench board's UART jumper under main()'s own link and the host's reader load, so alone in the twin it runs past the record's 60 s bound (its twin runs at -1 and 32768: about 192 s each, the initiator found, zero allocation failures) |
| `device_scripts/watchdog_starvation_reset.py` | exception / exception | (b) | silicon-only case of the flash test running it: a blocking watchdog starvation (a blocking starvation never reaches the twin's asyncio watchdog: the run times out) |
| `device_scripts/wifi_country_code_reaction.py` | exception / exception | (b) | silicon-only case of the flash test running it: the malformed country-code reaction (the twin WLAN has no scan()) |
| `flash/test_bus_concurrency.py` | exception / exception | (b) | silicon-only cases: the ISL29125's real INT edge (the twin drives no INT edge into the reader's IRQ), the held-SDA recovery (bit-banged pins hold no SDA in the twin) and the FRAM CS hijack (the FRAM fake frames by write() pairing, ignoring CS) |
| `flash/test_bus_electrical_timing.py` | exception / exception | (b) | silicon-only cases: the 2^24 single-precision float boundary (the Unix port's float is double), the malformed country-code reaction (the twin WLAN has no scan()), and the timer-callback drop under scheduler saturation (twin Timers are asyncio tasks: no scheduler queue, a synchronous script gives them no turn); and the SCD30 clock-stretch watch is a soak (--soak-duration: a real stretch comes about once a day) |
| `flash/test_fram_storage.py` | exception / exception | (b) | silicon-only case: write protection gating a real write and read (the twin's FRAM fake keeps the data a WP-gated write would not reach on silicon) |
| `flash/test_heap_layout.py` | pass / exception | (b) | at gc.threshold(32768) only: the live arm leaves 55 new blocks above the high band against the twin's bound of 32; the script sets -1 itself, but the twin runner applies the stage before the script (digital_twin/run_device_script.py:127), so the script's own imports load their bytecode onto the Unix port's heap under 32768's collections, which frozen code on silicon never does; at -1 both arms hold (mechanism inferred, not measured separately) |
| `flash/test_memory_stress.py` | exception / exception | (b) | silicon-only case: the used-heap bound after a full system build (the twin's heap is the Unix port's, not the RP2040's 264 KB); and the single-core timing headroom is a passive soak (--soak-duration) |
| `flash/test_modlwip_listener_close.py` | exception / pass | (c) | the same: its device script's twin bind check meets a TIME_WAIT pcb on port 50100 (EADDRINUSE 98), see listener_close_leaves_the_pcb_pools.py |
| `flash/test_reboot_persistence.py` | exception / exception | (b) | silicon-only case: the boot import after a genuine hard reset (the twin boots no production image, so no boot lines arrive) |
| `flash/test_sensor_accuracy.py` | exception / exception | (b) | silicon-only cases: the two NeoPixel sweeps need the rig aiming the NeoPixel at the ISL29125 (--allow-neopixel-sweep; the twin's ISL29125 fake is not optically coupled to the NeoPixel) and the SGP40 cadence is a 600 s soak (--soak-duration); twin fidelity: the SGP40 fake's raw walk (1000 ticks a sample, not datasheet-derived) leaves the real VOC algorithm's integer index constant over the 8 post-blackout samples (at its floor of 1 in 21 of 300 simulated runs at R0; at 2 and 5 in 2 of 15 runs here, r3m_voc_repro), which the frozen-algorithm check reads as frozen |
| `flash/test_system_commands.py` | exception / exception | (b) | silicon-only case: a hung shutdown step's watchdog takeover (the twin reports 'starved the watchdog', its form of the reset); the mid-erase resets now land inside the twin's erase (50/150/250 ms) and pass |
| `flash/test_toolchain_flash_boot.py` | exception / exception | (c) | gated, never run in the twin: the UF2 reflash is a real flash cycle (--allow-flash-cycle) and the toolchain re-verification fetches over the network and builds for about 8 min (--allow-toolchain-reverify) |
| `flash/test_uart_crossover.py` | exception / exception | (b) | silicon-only cases: interrupts-off windows, the UART break, the DMA ring's soft reset and the config-write window (the twin has no machine.disable_irq()/enable_irq(), no UART.sendbreak() and no rp2.DMA paced by a UART TX DREQ: streamed False), and the driver read's control arm (the twin UART serves min(nbytes, queued), so the control span stays about 10 us); and test_no_frame_is_lost_while_interrupts_are_off fails up front, on silicon as here, until devices/dev.toml sizes rx_ring for the 400 ms window (BACKLOG "The UART receive ring sized for the bench's interrupts-off window") |
| `flash/test_watchdog_starvation.py` | exception / exception | (b) | silicon-only cases: a blocking watchdog starvation and the reboot's starvation fallback (a blocking starvation never reaches the twin's asyncio watchdog: the run times out) |

Totals: (a) 0, (b) 31, (c) 8. The (c) reds are bench or gated instruments (serving scripts past the record's 60 s
bound, soaks, the per-run standard-state parameter, the reflash and toolchain gates) and one test defect: the
listener-close twin half (below).

## Findings for the hand-back

1. (c) `tests_hardware/device_scripts/listener_close_leaves_the_pcb_pools.py:27`: `_PORT = 50100` lies in the host's
   ephemeral range (32768-60999 here), and the twin half's no-SO_REUSEADDR bind check (`_port_held()`) meets a TIME_WAIT
   pcb there: its own round trip's within 60 s (19 of 20 back to back), or any earlier connection whose ephemeral port
   was 50100 (the recorder's -1 run). Proposed fix, one line: the twin half takes a port below the ephemeral range.
2. (c) `flash/test_uart_crossover.py::test_no_frame_is_lost_while_interrupts_are_off` fails up front, on silicon as
   in the twin, until `devices/dev.toml` sizes `rx_ring` (already a BACKLOG entry; round 1's).
3. (b) The SGP40 VOC quality check's twin case is not only the floor: constant indices of 2 and 5 seen (2 of 15 at 32768).
