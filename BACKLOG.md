# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently is migrated, not duplicated: its
facts to SPECIFICATION.md, its rules to CLAUDE.md, orientation to README.md.

**Everything that needs the dev bench is gathered in "Real-hardware work still owed" below**, so a
go-ahead session can work it in one pass; `tests_hardware/README.md` stays the reference for how.

## Refactor targets not yet done

None open.

## Open questions (need owner input or further investigation)

None open.

## Real-hardware work still owed

Folded in from the retired `REAL_HARDWARE_TEST_QUEUE.md` and `HARDWARE_TEST_HANDOVER.md` after the
2026-09-24/25 sitting; row IDs (T4, S4, ...) are kept because commits and the whole-project audit
plan (on its own branch) cite them. **Nothing here authorizes anything**: CLAUDE.md's go-ahead gate
applies, and `tests_hardware/README.md` is the reference for how any of it runs (flags, wear
gates, traps).

- **Not yet confirmed on silicon: the flash tier's watchdog-starvation test ending with
  `hard_reset()`** (`79eb41b`, test-only, no reflash needed) — no full flash-tier run since. Before
  it, the flash tier always left the board parked at the REPL with no watchdog, because the test
  attached within ~1 s of boot. Expected: `flash/test_watchdog_starvation.py` closes with one
  `hard_reset()` and the USB device back (its `closing_reset` fixture), so the tier no longer ends
  on a board parked without its watchdog. Wear: none (test only, no reflash). Twin row: the twin
  CI's watchdog hang backstop run (`ci_suite._run_10_watchdog_hang_backstop`, the file's named
  cover).
- **M1 + S3b, the ISL29125 light programs** — needs the owner at the bench, ~30 min. M1 first
  (`scripts/run_manual_hardware_tests.sh --only isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry`,
  interactive: repeatability on an unchanged scene, continuity across the range switch, and writing
  down the rig geometry S3b depends on; the reference light meter is an optional data point, never
  pass/fail), then
  `scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep --allow-persistence-write` (~10 min;
  the envelope test's config pushes need the second flag). The `Overrange` field (SPECIFICATION.md M.1.1,
  item 21) has never run on silicon; S3b runs it. Expected: M1, the operator's verdict
  on repeatability and on continuity across the range switch, with the rig geometry written down;
  S3b, no task died, `Overrange` set at full white and the envelope check reporting nothing
  (`flash/test_sensor_accuracy.py::test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration`). Wear: M1 none; S3b seven flash writes to a scratch config file, removed
  afterwards (the run's other persistence-gated flash tests spend their own,
  `tests_hardware/README.md`'s budget table). Twin row: M1 none (an operator observation); S3b the
  `isl29125` and `isl29125_autorange` scenarios its file names.
- **T4, the FRAM command hold on silicon** — on `dev`, `scripts/run_flash_hardware_suite.sh` runs
  `flash/test_fram_storage.py::test_fram_command_hold_stays_under_the_uart_poll_floor` (device
  script `tests_hardware/device_scripts/fram_command_hold_timing.py`, which writes only in its
  scratch region, the part's top 256 bytes above every chunk, and never calls `get_chunk()`, so
  production's error logs are safe). Its first run on silicon with the synchronous path is owed.
  Expected: one command within one UART poll floor (80 B at 115200 baud, 6,944 µs,
  SPECIFICATION.md J.6), and a log entry's 51 commands recorded for Part F.3's `stall.fram_entry`,
  which holds the chunk path's silicon figures. Wear: none (FRAM writes are not wear). Twin row: none (the twin's FRAM chip models
  no wire time).
- **The two unfed boot stretches, measured** — a `dev` boot log with a `ticks_ms()` stamp at every
  watchdog feed, taken in a hardware session (zero wear): the stretch from `WDT()` to the first
  setup feed, and from the last setup feed to the supervisor's first, each expected well inside the
  8,000 ms timeout. It replaces the estimates in Part N
  `boot.unfed_stretch_1_ms`/`boot.unfed_stretch_2_ms` (SPECIFICATION.md) and checks the L1
  boot-stretch scenario's sleep sum. The same log gives each setup unit's stretch between two feeds,
  against Part N `boot.setup_unit_stretch_ms` (79-91 ms per unit, dev, 2026-09-25); one more boot
  with a damaged config file adds that unit's repair write (`asy_config_manager.py`'s one write per
  boot), so it spends one flash write and runs only behind `--allow-persistence-write`. Twin row:
  the twin's boots assert the watchdog would never have fired
  (`tests/test_digital_twin_sensortask_integration.py`, `would_have_triggered_count` 0); that proves
  the sequence, not rp2 timing, so the figures are silicon-only.
- **The supervisor's scan budget, measured** — one pass with every supervised task ended at once,
  timed on `dev` with SYSTEM's entries on FRAM (Part N `system.scan_budget`): the default flash tier's
  `flash/test_task_supervisor.py::test_one_supervisor_pass_with_every_task_ended_stays_inside_the_watchdog`
  (device script `supervisor_scan_timing.py`), zero wear.
- **The on-target no-yield stretches and a flash write's loop gap** — on `dev`,
  `flash/test_memory_stress.py`'s `test_routine_no_yield_stretches_stay_under_the_gc_term` (the
  default flash tier, zero wear) and `test_flash_write_loop_gap_is_recorded` (one scratch flash
  write, `--allow-persistence-write`). Expected: the collection, VOC-step and CRC-gap figures under
  the 21 ms GC term (Part N `uart.gc_pause_worst_ms`), and the flash calls' spans recorded. The
  figures go into SPECIFICATION.md Part F.3's `stall.gc`, `stall.voc_process`, `stall.crc` and
  `stall.flash_program` rows. Twin row: none (silicon-only figures).
- **Loop lag under combined load on the bench** — on `dev`, the bench tier's
  `bench/test_memory_stress_bench.py::test_loop_lag_under_http_load_on_every_route_stays_under_the_smallest_hard_consumer`
  (`device_scripts/loop_lag_under_combined_load.py` in BENCH mode `"production"`, on the board's own
  config and address, its error log saved first): the shipped `main()` beside a 10 ms lag probe, an
  allocation-churn task and FRAM block writes in the script's scratch region, while the bench host's
  readers cycle every GET route. Expected: the worst lag under `dev`'s smallest hard consumer (Part
  F.3's `con.uart_reply`); its max and p99 go into Part F.3's `lag.loop` row. Wear: none (FRAM block
  writes in the script's scratch region). Twin row: the flash test
  `test_loop_lag_under_combined_load_stays_under_the_uart_reply_budget` under `--twin` and the
  `loop_lag_under_combined_load` scenario (Part F.3's `lag.loop`).
- **The UART hazard run under API load** — on `dev`,
  `bench/test_uart_link_under_api_load.py::test_a_hazard_run_under_the_readers_load_reports_every_verdict`:
  one `PUT /uart {"UartHazards": true}` while 3 readers GET `/status` until the run ends.
  Expected: every hazard verdict as the twin judges it, the echo's `Failures` unchanged, the echo
  resumed, the WEBSERVER counter at 0 and no task ended; the run's elapsed is recorded against the
  test's estimated 600 s run timeout. Wear: none (the command
  is dispatch-only). Twin row: `tests/test_digital_twin_uart_link.py`'s
  `test_a_hazard_run_put_through_the_api_while_readers_hammer_it_reports_every_verdict`.
- **Hard resets during natural FRAM backups, the torn writes expected** — on `dev`, the gated
  bench run's
  `bench/test_end_to_end_timing.py::test_real_hard_resets_during_natural_fram_backup_activity_recover_cleanly`
  (`--allow-persistence-write`): three hard resets 25 s apart across the SGP40's 60 s backup
  cadence. Expected: the SGP40 log empty, FRAM's log holding nothing beyond `E FRAM_STATUS_BYTE`
  and `W FRAM_BLOCK_INVALID` (agent, 2026-10-22), saved before it is cleared, a fresh backup completing
  after the last reset and no task ended. Wear: 2 flash writes (the `BackupPeriod` change and its
  restore); FRAM writes are not wear. Twin row: none (its twin record: the module needs the bench
  bridge).
- **The free alarm count on silicon** —
  `tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py` on `dev`: record its
  `constructed=N` (the alarms free at that moment, not the pool size) with the image's other
  default-pool users named. Expected: N at most the pool's 16 (SPECIFICATION.md F.1). Zero wear; no
  twin row confirms it yet (neither machine fake models the pool's size).
- **The idle poll rate** — the event-loop share an idle captive-DNS listener's 100 ms poll takes,
  and its first-query latency, on the twin and on the bench: a hotspot run with a counter task
  running flat out beside the listener, then one query after a silence, timed. The rate stays at
  100 ms with its measurement owed (owner, 2026-10-05); the figures go into Part N `udp.poll_idle_ms`'s
  Basis (SPECIFICATION.md F.5.9). Expected: queued datagrams answered back to back, and only the
  first query after a silence waiting up to one 100 ms idle poll (`src/asy_udp_socket.py`'s
  `ready()`); the listener's loop share at idle recorded beside it. Zero wear; twin row: none yet,
  the twin measurement is owed with it.
- **The SGP40's lost samples over ten minutes** — `flash/test_sensor_accuracy.py::
  test_sgp40_sample_cadence` on `dev` (`scripts/run_bench_soak_tests.sh --duration short`): its
  cadence facts, cycles near 600 expected; the figures go into SPECIFICATION.md M.3 (no pass threshold: a
  dropped soft-timer tick is not mitigated in software, owner, 2026-07-18, `f3924e1`). Wear: none (FRAM writes
  are not wear; read the FRAM logs first). Twin row: none (the twin's timers model no rp2 drop).
- **The modlwip send stall, reproduced and then the override proven (owner, 2026-09-30)** — on
  `dev`, `errcount` read and saved first (CLAUDE.md's FRAM rule). (1) Flash a control image: the
  pinned tree built without `apply_modlwip_eagain_override()` (the build code changed in a throwaway
  worktree, never committed); `bench/test_modlwip_send_stall.py::test_send_stall_on_the_unpatched_image`
  runs it with `--lwip-control-image <uf2>` and `--allow-flash-cycle`, flashing the control image
  and back. Hold the connection ceiling open with clients that stop reading
  mid-`app.js` (sockets kept open without `recv()`), then request one more page: record whether the
  board freezes for up to 10 s and whether a watchdog reset follows (`/status`'s `ResetReason`).
  (2) Flash the normal build and repeat that load, plus dead-client and slow-client page loads on
  every route at the ceiling. Expected: no watchdog reset, no VM stall longer than Part N `web.per_call_timeout_s`,
  the stalled connections reclaimed, service back to baseline once the clients go, and no
  `MemoryError` or `memory allocation failed` marker; page-load time before and after and the CPU
  cost of the cooperative retry recorded. While one connection sits in the retry (a client holding
  its socket open without `recv()` during a large route), a concurrent `GET /status` completes
  within a bound this run sets, its Part N row landing with the bench test, and the supervisor's
  task check keeps running with no task-error growth. A failed bound goes to the owner as a change
  to the override (a short POLLOUT back-off after `EAGAIN`), not absorbed by a larger bound. Wear:
  two flash cycles (the control image and the normal build), no persistence write. Twin row: none
  (the twin has no lwIP); `tests/lwip_host/test_modlwip_eagain.py` runs the same send path on the
  `build-lwip` host build.
- **`env --tier bench` creating a bridge under its own recovery timer** — on the bench Pi4, a
  fresh bridge (the old one deleted per `tests_hardware/README.md`'s 'Host network' section), with
  a second, manually armed SPECIFICATION.md B.13 timer as the outer safety. Expected: the
  installer's `sensors-bench-recovery-<pid>` timer is active before the first `nmcli connection
  add`, `br0` holds an address and the default route within Part N `tool.bench_bridge_up_poll_s`,
  and the timer is gone afterwards; the sequence's wall time and the time to a DHCP lease go into
  the Basis of `tool.bench_bridge_recovery_arm_s` and `tool.bench_bridge_up_poll_s`. Wear: none
  (host network state only, no flash). Twin row: none.
- **The hotspot role reversal's failed-credential cases** — on `dev`, `errcount` read and saved
  first (CLAUDE.md's FRAM rule; the module itself clears the error logs in stages 3-5), then
  `tests_hardware/bench/test_hotspot_role_reversal.py`'s two stage-6 cases for a credentials change
  landing in the fresh-boot state (owner, 2026-10-08, paraphrase). (a)
  `test_a_wrong_password_over_the_hotspot_reopens_the_hotspot`, about 3-4 min: a well-formed wrong
  password over the DUT's hotspot. (b)
  `test_a_second_failed_streak_goes_silent_and_links_on_a_later_attempt`, two `hotspot_time_min`
  windows (16 min on `dev`) plus its streaks: the reopened hotspot's window ends with no client,
  then a second streak fails. (b) runs on the real-credentials test's write, so both run as the
  whole module in one invocation with `--soak-duration long` and `--allow-persistence-write`
  (`tests_hardware/README.md`'s "The hotspot role reversal" names a candidate invocation). Expected:
  (a) the hotspot reopens once more, with one more `WLAN_TO_HOTSPOT` and no `WLAN_SILENT` in WIFI's
  history; (b) the second streak goes silent (one `WLAN_SILENT`, no `WLAN_GIVE_UP`) and a later
  attempt links once the bench AP is back, with no reset. Wear: (a) one owned flash write, restored
  by the real-credentials test; (b) none. Twin row: `tests/test_digital_twin_wifi_modes.py`.
- **Whether the chips other than the SGP40 ACK or NAK a general call** — on `dev`, a device script
  sending the general-call reset (address 0x00, 0x06) on each I2C bus and recording ACK or NAK per
  bus and which chips answer afterwards. Expected: none stated, since no datasheet states it; the
  answers are recorded, not judged, and the fidelity row follows them. Wear:
  none (no NVM write). Twin row: the fidelity table's general-call assumption
  (`digital_twin/README.md`). Needs that device script.
- **A lone BMP3xx under general calls** — on `dev`, the default flash tier's
  `flash/test_bus_concurrency.py::test_bmp3xx_alone_survives_a_general_call`
  (`device_scripts/bmp3xx_alone_survives_a_general_call.py`: distinctive volatile settings, then a
  range-checked reader racing 0x06 broadcasts to address 0x00 under the bus lock) and the
  self-hazard broadcasts of `test_bus_topology_autodetect_address_and_reserved_range_sweep`.
  Expected: every planned broadcast sent, reads completing, and the configuration, chip ID,
  power-control bits and power-on flag unchanged; at least one sweep broadcast on each bus it
  races, a NAK on `dev`'s i2c0, whose lone BMP3xx takes no general call (C.8's general-call finding). Wear:
  none (volatile registers only, restored by a soft reset at the end). Twin row: the same test
  under `--twin` (the file's twin record names its silicon-only cases, and this is not one).
- **The SCD30's reaction to a wrong argument CRC or an out-of-range interval** — on `dev`,
  `flash/test_chip_conformance.py::test_scd30_argument_reaction_is_recorded`
  (`scd30_argument_reaction.py`): 0x4600 once with a wrong argument CRC and once with 0 and a
  correct CRC, each read back and the period then in effect timed, the original put back; recorded,
  not judged, since the datasheet states no reaction and the twin ignores each. The out-of-range
  values 1 s and 1801 s are not sent. Expected: the measurement interval back at its start value
  afterwards (`restored=ok` and the interval equal to the start snapshot, the test's only
  assertions). Wear: up to three SCD30 NVM writes (`--allow-persistence-write` and
  `--allow-scd30-extra-write`). Twin row: the fidelity table's SCD30 argument assumption.
- **Whether a CONFIG1 write restarts an in-flight ISL29125 conversion** — on `dev`, a device script
  writing CONFIG1 unchanged part-way through a 100 ms 16-bit conversion and timing the next
  conversion-done flag against the previous one; FN8424 Table 7 says only "ADC start at I2C write
  0x01", the twin restarts it. Wear: none (volatile registers). Twin row: the fidelity table's
  ISL29125 CONFIG1 assumption, which no test is tuned to. The register probe measures it
  (`isl29125_mock_conformance_probe.py`'s `G01`/`G02` keys,
  `flash/test_chip_conformance.py::test_isl29125_matches_its_twin_fake`). Expected: none stated; the
  probe's `G01`/`G02` facts are reported only, and the fidelity row stays an assumption unless they
  settle it.
- **The BMP3XX's real calibration block** — on `dev`, the 21 calibration bytes from register 0x31
  (`asy_bmp3xx_driver.py`'s `_REGISTER_CAL_DATA`) printed once by a device script, so the twin's
  synthetic block can be checked against a real one. The probe reads it
  (`bmp3xx_conformance_probe.py`'s `A02_calibration`,
  `flash/test_chip_conformance.py::test_bmp3xx_matches_its_twin_fake`). Expected: 21 bytes, neither
  erased nor floating (the probe's `_bmp3xx_calibration_set`), recorded so the twin's synthetic
  block can be set against them. Wear: none (a read). Twin row: the fidelity table's BMP3XX
  calibration row, synthetic until then.
- **The bootloader command's BOOTSEL round trip** — the bench found both backup regions lost
  (the bootrom's `reset_usb_boot()`; cause 3, REASON TIMER), so the command writes no code of its
  own. `bench/test_reset_reasons.py::test_a_bootloader_reboot_is_attributed` runs the round trip
  through `PUT /system {"SystemCmd": "bootloader"}`. Expected: the board serves again and
  `GET /status`'s `ResetReason` reads 2. Wear: none (no flash write; leaving BOOTSEL needs the owner
  or `picotool reboot`). Twin row: the fidelity table's BOOTSEL row.
- **Every reset code read back through `/status`** — `bench/test_reset_reasons.py` on `dev`, the
  session saving `errcount` and the raw FRAM first: the harness hard reset (its `mpremote` Ctrl-C
  ends `main.py` first), the bootloader reboot, the supervisor's escalation reboot, the
  starved-watchdog fallback, an invalid record, an incomplete command, a hang in each boot phase, a
  C-stack exhaustion and a console interrupt, each read back as `GET /status`'s `ResetReason`;
  `tests_hardware/README.md`'s "Reset codes proven on the bench" fills from the run. Expected: each
  `ResetReason` the code its reset fixes (`bench/test_reset_reasons.py`, from
  `src/asy_system_service.py`'s constants): 2 the bootloader reboot (the bootrom's own reboot leaves
  no record), 5 the escalation reboot with SYSTEM's escalation entry, 6 the starved-watchdog
  fallback, 0 an invalid record, 9 an incomplete command, 10 + phase a hang in boot phases 1-5, 20 a
  C-stack exhaustion, 21 a console interrupt and the harness hard reset; the board serving after
  each. Wear: no owned write (the tests carry no wear marker). Twin row: each script's twin run.
- **The UART receive ring under the bench's interrupts-off windows** — on `dev`, the responder's
  `rx_ring` is the 512 B default (`devices/dev.toml`, J.6), whose bound a continuous sender passes
  at about 44 ms, so the 45 ms window lies just past it;
  `flash/test_uart_crossover.py::test_no_frame_is_lost_while_interrupts_are_off` runs on it and
  reports the ring's heap cost. Expected: every frame intact with the overrun bit clear within the ring's bound,
  an overrun reported past it, the frames after its resync intact, and the receive-DMA-off overrun
  failing one transaction and recovering. Wear: none (`uart_dma_ring_interrupts_off.py` holds
  interrupts off with a busy-wait, no flash write). Twin row: none.
- **Whether a changed `Altitude` applies at once while `AmbPres` is 0** — on `dev`,
  `bench/test_sensor_config_push_over_real_hardware.py::test_scd30_altitude_takes_effect_while_ambient_pressure_is_zero`:
  `AmbPres` 0, a stepped `Altitude`, both restored; the answer goes into SPECIFICATION.md M.2.
  Expected: `AmbPres` 0 and the `Altitude` step answered `Valid`, both restores `Valid` or
  `Unchanged`, and `CFGMGR_SCD30`'s log empty (the test's assertions); the CO2 readings before and
  after the step recorded, not presumed. Wear: 4 SCD30 NVM writes (`--allow-persistence-write` and
  `--allow-scd30-extra-write`). Twin row: none (a silicon question).
- **`env --tier bench` on the bench Pi4 once more, after the tooling pins** — `uv run
  toolchain/setup_toolchain.py env --tier bench`, a host step that writes nothing to the board: the
  bench host's `uv` must be the version `pyproject.toml`'s `[tool.uv] required-version` names (any
  other uv refuses to run in this tree), and the Playwright step is now fatal — a failed `npx
  playwright install chromium` stops `env` by name, and so does a failed `install-deps` unless
  `--skip-apt` skips it (pass it where the libraries are present). Expected: `env` completes, its
  Playwright step included. Wear: none (host only). Twin row: none.
- **The default and the gated bench round over the files the tooling consolidation touched** — on
  `dev`, `errcount` read and saved first (CLAUDE.md's FRAM rule). Every hardware runner
  (`scripts/_require_clean_hardware_run.sh` and so the flash, bench and soak runners,
  `scripts/run_bench_rollover_test.sh`, `scripts/run_manual_hardware_tests.sh`,
  `scripts/mpremote_connect.sh`) now runs `scripts/uv_sync_retried.sh` before its hardware step, a
  failed sync exiting 1 before anything reaches the board. The default flash and bench tiers run,
  each through the flash and bench tests that run it: the device scripts whose suppression comments
  moved, comments only (`isl29125_mechanism_envelope.py`, `sgp40_voc_algorithm_quality.py`,
  `uart_comm_hazards.py`, `uart_dma_ring_interrupts_off.py`,
  `uart_driver_read_never_blocks_the_loop.py`); the 11 whose `start_tasks()` call now passes the
  required `task_names` (`c_stack_budget.py`, `heap_layout_after_full_boot_sequence.py`, whose list
  collection also follows `main()`'s order now, `reset_code_command_incomplete.py`,
  `reset_code_stack_exhausted.py`, `sgp40_sample_cadence.py`, `system_command_config_reset.py`,
  `system_command_fram_erase.py`, `system_command_hang.py`, `system_command_reboot.py`,
  `system_service_restarts_a_real_dead_task.py`, `unretrieved_task_exception_handler.py`; of them
  `sgp40_sample_cadence.py`, `system_command_fram_erase.py` and `system_command_hang.py` also carry
  moved suppression comments); the host files edited (`bench/test_hotspot_role_reversal.py`,
  `bench/test_reset_reasons.py`, `bench/test_system_commands_over_rest.py`,
  `flash/test_system_commands.py`, `conftest.py`'s `bench` fixture, now a plain return, and its
  VL805 read, `bench_control.py`'s two `contextlib.suppress` forms, `twin_board.py`,
  `website_identity.py`); and one `GET /status` on `dev`'s own firmware, its
  `system.LastTaskEnd` read (`null` while no supervised task has ended this boot). Then the gated
  run, `--allow-persistence-write`, for the persistence-gated tests among them
  (`bench/test_hotspot_role_reversal.py`, `bench/test_system_commands_over_rest.py`,
  `flash/test_system_commands.py`, and the ISL29125 envelope behind `--allow-neopixel-sweep`), and
  `bench/test_uart_link_crc16.py` behind `--allow-flash-cycle` (its CRC16 image flashed, the
  standard one flashed back). Expected: clean verdicts on all three runs. Wear: the gated run's own
  budget ("Persistence-write gating", `tests_hardware/README.md`) plus that test's two flash cycles;
  none in the default run. Twin row: none new (`tests_hardware/twin_board.py` runs the same device
  scripts under `--twin`).
- **The bench `ResetErrors` budget** — on `dev`, after the round's FRAM evidence is saved: the
  `ResetErrors` sweep timed three times each against 0, 1, 2, 3 and 4 concurrent `GET /status`
  readers, on the reset one source after another (owner, 2026-11-07). Then the bench analogue of
  the twin's per-sweep budget check goes into `tests_hardware/error_log_helpers.py`, beside its 30 s
  timeout, which alone asserts nothing about elapsed time. Expected: a curve that leaves room for a
  budget below the server's 15 s `outer_cap_s` that "reliably won't fail the pipeline accidentally
  with a false positive" and "will reliably fail if something really went wrong" (the owner's
  standing requirement as BACKLOG.md recorded it on 2026-09-17, `569c6bb`). Last measured 2026-09-25
  on an earlier one-after-another reset: about 3.5 s per reader, three readers at
  13.2-14.7 s, four past the connection ceiling. Wear: none (the clears are FRAM writes). Twin row:
  `_RESET_ERRORS_BUDGET_S` in `scripts/_digital_twin_ci_suite.py`.
- **S4, the six-hour soak** — on `dev`, after the round's FRAM evidence is saved and on top of a
  clean bench run, `scripts/run_bench_soak_tests.sh --duration long` (six hours,
  `tests_hardware/soak_durations.py`) runs the soak-duration tests, among them
  `bench/test_memory_stress_bench.py::test_http_soak_stays_live`, a modest request stream over every
  JSON GET route. Expected: no allocation-failure marker, crash line or reboot in the board's log,
  no supervised task ended, and failed requests at most Part N `l4.soak_request_failure_rate`
  (0.1 %) of those sent. This is a liveness check with no leak bound; last run 2026-09-08 at the
  10-minute `--duration mid`, clean. Wear: none (the soak's error-log clears are FRAM writes).
  Twin row: none as a parameter (a silicon duration); the twin CI's soak run
  (`ci_suite._run_11_soak`) is the scenario the test names as its cover.
- **G6, the tick rollover on silicon** — on `dev`, `scripts/run_bench_rollover_test.sh` builds the
  tick-offset test image (its millisecond count starts 15 minutes short of `2**32`), flashes it and
  runs `bench/test_ticks_ms_rollover.py` for about two hours, polling over REST only (owner,
  2026-10-01; a serial attach ends in a watchdog reset, `tests_hardware/README.md`); the runner passes
  `--allow-multi-day-rollover` and `--allow-flash-cycle` itself, on top of a clean bench run.
  Expected: across the `ticks_ms()`, soft-timer and lwIP wraps nothing reboots or stalls: the uptime
  keeps rising under one boot signature, NTP keeps syncing within its interval, and every sensor's
  timestamp advances. Wear: one flash cycle (the tick-offset image, left for the next round to
  replace). Twin row: none for the wrap, which the Unix port never reaches
  (`digital_twin/README.md`'s fidelity table: the wrap proofs are fake-clock unit tests); the twin's
  `sensortask_integration` run, the test's named cover, covers the rest.
- **F17, the board anomalies of the connection-limit sittings** — on `dev`, across every round
  (HEAP_FRAGMENTATION_MEASUREMENTS.md archive §7R.5): a reset the round did not intend is read
  through `GET /status`'s `ResetReason` and the FRAM `errcount`, both saved before anything clears
  them (CLAUDE.md's FRAM rule); `reset_cause()` separates only power-on from everything else, so it
  cannot attribute one (SPECIFICATION.md F.5.4). Open, each needing silicon: (1) one silent reset in
  1 of 9 instrumented peak-load boots, cause lost; watchdog starvation is the first candidate to
  rule out, since the supervisor loop is the only feed site (`asy_system_service.py`'s
  `feed_watchdog()`) and a board CPU-bound at ~2.2 requests/s can miss the 8,388 ms cap. (2) Hotspot
  fallback after a reset, three times; `devices/dev.toml`'s `conn_fail_to_hotspot = 5` is the
  mechanism that would take it there. One instance is measured (2026-09-25): a watchdog reset with
  no `kick_all_stations()` before it gave `reset_cause()` = `WDT_RESET` and WIFI
  `WLAN_CONNECT_FAILED` (`W38`) ×5 (`STAT_CONNECT_FAIL`), the stale-AP-station mechanism, cleared by
  a kick; whether the earlier three were the same is not recoverable. (3) The USB serial dropped
  mid-upload of `uart_idle_poll_rate.py` (2026-09-24); later resets overwrote `reset_cause()`, an
  isolated re-run passed, and two later full bench tiers did not reproduce it. Expected: no reset a
  round did not intend, and a hotspot fallback only after a reset with no kick right before it
  (A.4's reset rules). Wear: none (reads only). Twin row: none (the twin fakes Wi-Fi connection
  state only).
- **The MQTT PoC's scoped bench run** (branch `claude/whole-project-audit-plan-followup` only, until it
  merges) — on `dev`: `mqtt_poc/BENCH_HANDOVER.md` is its run sheet and its full context, `--scope mqtt`
  with writes scoped to `networking/identity`, `networking/mqtt`, `networking/ntp` and
  `notification/autoConfig` (owner, 2026-10-08: "include the ntp tests too, allow networking/ntp";
  "include the hotspot role reversal too"); its section 7 says where the results go. Wear: the
  flash-filesystem writes the scope's tests own in those four groups (`tests_hardware/README.md`'s
  budget table), no SCD30 write of their own. Twin row: `ci_suite._run_14_mqtt_broker_faults`, the
  MQTT module's named cover.
- **Still owed elsewhere in this file**: H1, the owner's two-chroot run (the chroot entry below).
  Excluded on purpose: G10, the UART protocol against its C implementation (post-audit only), and
  the two unbought bench-rig capabilities (SPECIFICATION.md E.6.6).

## Deferred / explicitly out-of-scope work

- **The MQTT client against the full-system heap bound, after the audit** (branch
  `claude/whole-project-audit-plan-followup` only, until it merges; owner, 2026-10-08: "The heap limit should
  definitely be obeyed in the final version, but that's a topic becoming relevant when the audit is done.").
  The client costs 11,360 B in all, its imports included (`mqtt_poc/DESIGN.md` §5); the `dev` image's flash
  step read 114,768 B against the 100,000 B total `test_real_gc_heap_headroom_survives_a_full_system_build`
  then bounded. Its bound is now at most 41,000 B added by the build and its setups (SPECIFICATION.md Part
  N's `l3.heap_headroom_after_full_system_build_max_added`; owner, 2026-11-11), derived from `dev`'s
  35,984 B without the client, so `dev` with it is expected over the bound; the bound stays where it is.
- **`arduino/` and the C reconciliation are post-audit only** (owner, 2026-09-25: 'the C port stays
  out of scope, anything there is post-audit only'). That covers the UART protocol's C
  implementation (its reconciliation against `UART_C_PORT_CHANGELOG.md` included) and the
  BME688/BSEC material with its licensing. Nothing here tracks work on it.
- **R13 + N3, UART `wrnno` 54 (`UART_DRAIN_BOUND`) against a real babbling peer — deferred** (owner,
  2026-11-06: "Defer, that can be done once the UART C implementation is done and can go into both
  directions. But this is out of the audit scope."). N3 also owes a check that
  `UART_C_PORT_CHANGELOG.md` records the reclassification (receiver-side only, no emitted bytes change).
  Expected: `GET /status` shows `W54` for `UART_init`/`UART_resp` once the drain hits its bound, and a
  boot drain against the same peer persists nothing (SPECIFICATION.md C.7.1). Wear: none (FRAM log
  entries only; FRAM writes are not wear). Twin row: none; the mock tier covers the logic
  (`tests/test_asy_uart_comm.py`'s `test_a_drain_that_hits_its_bound_persists_the_drain_warning` and
  `test_a_boot_drain_that_hits_its_bound_persists_nothing`).
- **Build-environment changes since the clean-chroot legs were last satisfied** (noble 2026-11-07 on
  the bench Pi4 in the `--arch=arm64` ports-mirror form: `env --tier generic`, lint and typecheck
  clean, `scripts/test.sh` green at 4 and at 16 test jobs with its scratch in RAM; trixie 2026-09-12
  on the bench Pi4, GCC 14.2.0, lint and typecheck clean, then `env --tier generic` end to end). The
  owner's next run follows README.md "Build-environment verification" at the current head (the
  periodic-check rule: CLAUDE.md), which covers every later change; this entry holds only what changes
  how a run goes. A change that needs nothing new installed, no new host requirement and no recipe
  step gets no line here.
  - **Trixie on 2026-11-07, not satisfied** (a fresh chroot, GCC 14.2.0, `scripts/test.sh`'s scratch
    still on the microSD): `env --tier generic`, lint and typecheck clean; at 4 test jobs the pytest
    tier passed (6,966) and the MicroPython tier 5,838 tests, with 8 twin scenario-harness failures
    read as the card's write stalls, which the noble leg's scratch in RAM removed (inferred for
    trixie, not re-run there: a fresh chroot is the heaviest card write; owner, 2026-11-07: "too
    heavy write cycles should not be conducted allover again...").
  - **Installed now that 2026-09-12 did not**: the `.nvmrc` Node (then 22) and the refreshed npm tree;
    uv exactly as `pyproject.toml`'s `[tool.uv] required-version` names it (pinned in the recipe); the
    refreshed dev-group pins, `coverage` among them; the stub post-releases `toolchain/versions.toml`'s
    `[stubs]` names; a third Unix-port binary, `build-lwip`, so a from-scratch run builds the Unix port
    three times.
  - **Moved after both legs (2026-11-10), Python tools**: uv 0.8.17 → 0.13.7 (the recipe's `pip install`,
    `uv.lock` rewritten at lock revision 5) and the dev group's mypy 2.4.1, ruff 0.17.4, pytest 9.2.0,
    coverage 7.17.2, zizmor 1.32.0 and types-pyserial 3.5.0.20261104.
  - **Moved after both legs (2026-11-10), Node**: Node 24 → 26 (`.nvmrc`; `env` fetches `latest-v26.x`)
    and the regenerated npm tree, Stylelint 18 and Playwright 1.65 among it, whose Chromium 158 `env`
    downloads.
  - **Host requirements, present on both targets**: `flock` (util-linux), coreutils' `timeout`, a
    writable `${XDG_RUNTIME_DIR:-/tmp}` for the port locks, and a copied tree that is a git checkout
    with its own `.git`.
  - **The installer, much changed since the legs** (the recipe's `env --tier generic` step runs it):
    the `[lwip]` table and its readback through the C compiler CMake recorded, the patched `modlwip.c`
    copy in every rp2 image and in `build-lwip` (SPECIFICATION.md B.14.4), the Unix variant header's
    GC mark stack (B.14.6) and two-byte qstr lengths (F.7 row 32, read back by each Unix build's version
    probe), bounded and retried network steps, apt as one non-fatal update and one install with no
    wall-clock limit (apt's own retries and stall timeout, `apt_options()`; newer than both legs),
    `sudo --preserve-env`, the tier command table, Node's checksum-verified install. The host lwIP
    build has met GCC 13 on x86-64 and arm64 and GCC 14.2 on arm64 (both 2026-11-07 legs), and only
    the GCC 14 leg exercises the mbedtls `-Wno-array-bounds` rule. One reading is owed too:
    `sudo -k`'s exact semantics for the passwordless-sudo probe.
  - **A reused chroot**: a changed `toolchain/micropython_overrides.py` makes `scripts/_unix_port.sh
    ensure` rebuild the three Unix binaries once; a binary from before the settrace split is detected
    and rebuilt; a toolchain without its `toolchain-record.json` counts as unbuilt.
  - **Fewer jobs, nothing installed** (2026-11-09): `scripts/test.sh` and the twin legs take one device
    per `hardware_family` (`scripts/_devices.sh`'s `distinct_devices`: bash and `sed`), and
    `GC_THRESHOLD=32768 scripts/test.sh` runs no pytest tier, its summary listing it as skipped.
  - **An arm64 leg runs two functions as plain twins** (2026-11-11): the Unix port compiles no native code
    on arm64 (v1.29.0), so the CRC engine and the UART ring copy run as `build/portable_src/` copies there
    (SPECIFICATION.md F.1); nothing installed. Before this, every arm64 Unix-port run failed at import.
  - **`[lwip]` `TCP_SND_BUF` 6,400 → 1,600 B** (2026-11-11): nothing installed; a reused chroot's changed
    `toolchain/versions.toml` runs setup once, as above, and `build-lwip` takes the new value.
  - **`mosquitto`, a new apt package (MQTT PoC branch, 2026-10-08)**: `toolchain/versions.toml`'s
    `apt_packages` gains the broker the MQTT client's twin and bench tests start themselves (owner,
    2026-10-07: 'apt package (Recommended)'). Its Debian/Ubuntu package also enables a system broker on
    `localhost:1883`, which no test uses; a chroot without systemd only installs it. The twin suite's
    Run 14 needs it on `PATH` or in `/usr/sbin`, so a chroot's `scripts/run_digital_twin_ci.sh dev` also
    proves the package landed.
- **Owner requirement for the final wiring stage (owner, 2026-08-08, `7f498c1`, paraphrase) —
  fulfilled; held here only until the owner's audit of the whole refactor closes.** Every
  `sensortask-*.py` built as part of the real rewrite needs a full Unix-port equivalent, runnable on
  a local computer, with whatever hardware is physically unavailable there mocked at the lowest
  level of bus data exchange (i.e. the same mocking boundary SPECIFICATION.md Part
  E.4/`tests/machine.py` already establish for unit tests — fake `machine.I2C`/`machine.SPI`/etc.
  byte-level transactions, not higher-level driver stand-ins) so the whole wired-together sensortask
  can be exercised as close to the real target as possible without physical hardware. **Fulfilled**:
  `digital_twin/` is the lowest-level-mocking module this requirement calls for (see
  `SPECIFICATION.md` Part A.10), and `scripts/run_unix_port_integration.sh` runs any device's whole
  wired-together (buildgen-generated) module against it end to end (see
  `digital_twin/README.md`'s "Swapping the twin in for a Unix-port run" section). Comes out when
  that audit closes.
- **Adopt a genuine non-blocking alternative to every currently-unavoidable blocking call as soon as
  one reliably exists** (owner, 2026-07-24, `cc911be`: 'Don't treat the current state as
  permanently accepted risk'; confirmed by the owner, 2026-09-29). Today's list, each backstopped by
  the hardware watchdog after the recovery ladder (SPECIFICATION.md F.2): a `machine.I2C` transfer
  on a wedged bus; a single `machine.SPI` transfer (synchronous, `ports/rp2/machine_spi.c:303-335`,
  v1.29.0; the FRAM's waits around it wait only on other coroutines, SPECIFICATION.md F.2).
  `socket.getaddrinfo()` is called from `src/` on numeric hosts only: `asyncio.start_server()`'s bind
  host and the MQTT client's broker address, the IPv4 literal its resolver returned (SPECIFICATION.md F.2). Re-checked at each MicroPython version re-check (CLAUDE.md 'Platform
  target').
- **Resize the rp2 littlefs reservation** — only once flash space is actually short (owner,
  2026-09-26); trigger: the firmware image-size report; mechanism SPECIFICATION.md B.14.3.
- **modlwip non-blocking send stall — watched upstream**: micropython issue 19704, with PRs 19705
  (partial write, `ENOBUFS`) and 19708 (`EAGAIN` on `ERR_MEM`); upstream commit `6e79dcf9c` (after
  v1.29.0) only swaps the retry loop's 50 ms sleep for `poll_sockets()` and keeps its 10 s limit, so
  the stall stays. The `modlwip_eagain` build override (SPECIFICATION.md B.14.4) stays until the pin
  carries a real fix; the override's anchor check fails the build when upstream changes the loop
  (owner, 2026-09-30).
- **modlwip listener close — watched upstream** (owner, 2026-10-26): at v1.29.0 `close()` calls
  `tcp_err()` and `tcp_recv()` on every TCP pcb and `tcp_poll()` on all but a listening socket's,
  three calls lwIP forbids on a `LISTEN` pcb. No upstream issue exists (nearest: PR 17333, `recv()`
  on a listening socket, a different path). The same copy's second patch skips all three on the
  pcb's own state, and its third allocates `listen()`'s accept queue before storing `alloc`, whose
  byte a refused `listen()` otherwise leaves in the pbuf pointer `close()` frees (SPECIFICATION.md
  B.14.4; agent, 2026-10-26). Each is removed, not re-anchored, once the pin fixes its defect; an
  anchor check failing at a pin move is the watch. Same class, not reached by this
  firmware and left as upstream's: `POLL_WR` (`extmod/modlwip.c:1639`), `send()`/`write()` (`:760`)
  and a non-blocking `sendall()` (`:1417`) read `tcp_sndbuf()` past a listener, and
  `setsockopt(TCP_NODELAY)` writes its flags (`:1528-1535`). asyncio polls a listener for reading
  only (`extmod/asyncio/stream.py:149`), nothing sends on it, and no `TCP_NODELAY` call is made.

## Owner questions

Questions for the project owner, each dated, in the owner's format; nothing else in the repo parks a
question.
