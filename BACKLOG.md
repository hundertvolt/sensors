# BACKLOG

Active working memory: open questions, deferred/not-yet-done work, and in-flux design decisions —
not a historical log. Once an item is resolved (bug fixed, decision settled, question answered) it
comes out of this file; anything from it worth keeping permanently is migrated, not duplicated: its
facts to SPECIFICATION.md, its rules to CLAUDE.md, orientation to README.md.

**Everything that needs the dev bench is gathered in "Real-hardware work still owed" below**, so a
go-ahead session can work it in one pass; `tests_hardware/README.md` stays the reference for how.

## Refactor targets not yet done

None open.

## Real-hardware work still owed

Folded in from the retired `REAL_HARDWARE_TEST_QUEUE.md` and `HARDWARE_TEST_HANDOVER.md` after the
2026-09-24/25 sitting; row IDs (T4, F17, ...) are kept because commits cite them. **Nothing here
authorizes anything**: CLAUDE.md's go-ahead gate applies, and `tests_hardware/README.md` is the
reference for how any of it runs (flags, wear gates, traps).

- **T4, the FRAM command hold's entry figure on silicon** — on `dev`,
  `scripts/run_flash_hardware_suite.sh` runs
  `flash/test_fram_storage.py::test_fram_command_hold_stays_under_the_uart_poll_floor` (device
  script `tests_hardware/device_scripts/fram_command_hold_timing.py`, which writes only in its
  scratch region, the part's top 256 bytes above every chunk, and never calls `get_chunk()`, so
  production's error logs are safe). It passed on the final image on 2026-11-13 (one command within
  one UART poll floor, 80 B at 115200 baud, 6,944 µs, SPECIFICATION.md J.6); owed: a log entry's 51
  commands recorded into Part F.3's `stall.fram_entry`, which holds the chunk path's silicon figures.
  Wear: none (FRAM writes are not wear). Twin row: none (the twin's FRAM chip models
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
- **A flash write's loop gap** — on `dev`, `flash/test_memory_stress.py`'s
  `test_flash_write_loop_gap_is_recorded` (one scratch flash write, `--allow-persistence-write`).
  Expected: the flash calls' spans recorded, into SPECIFICATION.md Part F.3's `stall.flash_program`
  row. Twin row: none (silicon-only figures).
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
- **Whether a changed `Altitude` applies at once while `AmbPres` is 0** — on `dev`,
  `bench/test_sensor_config_push_over_real_hardware.py::test_scd30_altitude_takes_effect_while_ambient_pressure_is_zero`:
  `AmbPres` 0, a stepped `Altitude`, both restored; the answer goes into SPECIFICATION.md M.2.
  Expected: `AmbPres` 0 and the `Altitude` step answered `Valid`, both restores `Valid` or
  `Unchanged`, and `CFGMGR_SCD30`'s log empty (the test's assertions); the CO2 readings before and
  after the step recorded, not presumed. Wear: 4 SCD30 NVM writes (`--allow-persistence-write` and
  `--allow-scd30-extra-write`). Twin row: none (a silicon question).
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
- **The bench `ResetErrors` budget** — the bench analogue of the twin's per-sweep budget check goes
  into `tests_hardware/error_log_helpers.py`, beside its 30 s timeout, which alone asserts nothing
  about elapsed time, at a budget below the server's 15 s `outer_cap_s` that "reliably won't fail
  the pipeline accidentally with a false positive" and "will reliably fail if something really went
  wrong" (the owner's standing requirement as BACKLOG.md recorded it on 2026-09-17, `569c6bb`). Its
  curve is measured (dev, 2026-11-12, the reset one source after another): 15 sweeps against 0-4
  concurrent `GET /status` readers, each answered `Valid` in 0.62-0.91 s, no GET failed. Wear: none
  (the clears are FRAM writes). Twin row:
  `_RESET_ERRORS_BUDGET_S` in `scripts/_digital_twin_ci_suite.py`.
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
- **Still owed elsewhere in this file**: H1, the owner's two-chroot run (the chroot entry below).
  Excluded on purpose: G10, the UART protocol against its C implementation (post-audit only), and
  the two unbought bench-rig capabilities (SPECIFICATION.md E.6.6).

## Deferred / explicitly out-of-scope work

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
  clean, `scripts/test.sh` green at 4 and at 16 test jobs with its scratch in RAM; trixie 2026-11-12
  on the bench Pi4 in a fresh chroot with its scratch in RAM, GCC 14.2.0: `env --tier generic`, lint,
  typecheck and `scripts/test.sh` clean). The
  owner's next run follows README.md "Build-environment verification" at the current head (the
  periodic-check rule: CLAUDE.md), which covers every later change; this entry holds only what changes
  how a run goes. A change that needs nothing new installed, no new host requirement and no recipe
  step gets no line here.
  - **Moved after the noble leg (2026-11-10), Python tools**: uv 0.8.17 → 0.13.7 (the recipe's `pip install`,
    `uv.lock` rewritten at lock revision 5) and the dev group's mypy 2.4.1, ruff 0.17.4, pytest 9.2.0,
    coverage 7.17.2, zizmor 1.32.0 and types-pyserial 3.5.0.20261104.
  - **Moved after the noble leg (2026-11-10), Node**: Node 24 → 26 (`.nvmrc`; `env` fetches `latest-v26.x`)
    and the regenerated npm tree, Stylelint 18 and Playwright 1.65 among it, whose Chromium 158 `env`
    downloads.
  - **Host requirements, present on both targets**: `flock` (util-linux), coreutils' `timeout`, a
    writable `${XDG_RUNTIME_DIR:-/tmp}` for the port locks, and a copied tree that is a git checkout
    with its own `.git`.
  - **The installer, much changed since the noble leg** (the recipe's `env --tier generic` step runs it):
    the `[lwip]` table and its readback through the C compiler CMake recorded, the patched `modlwip.c`
    copy in every rp2 image and in `build-lwip` (SPECIFICATION.md B.14.4), the Unix variant header's
    GC mark stack (B.14.6) and two-byte qstr lengths (F.7 row 32, read back by each Unix build's version
    probe), bounded and retried network steps, apt as one non-fatal update and one install with no
    wall-clock limit (apt's own retries and stall timeout, `apt_options()`; newer than the noble leg),
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
  - **An arm64 leg runs two functions as plain twins** (2026-11-11, 2026-11-12): the Unix port compiles no
    native code on arm64 (v1.29.0), so the CRC engine and the UART ring copy run as `build/portable_src/`
    copies there, regenerated with the generated tree whenever its stamp no longer holds (SPECIFICATION.md
    F.1, E.3); every launcher's path carries them; nothing installed. Before this, every arm64 Unix-port
    run failed at import. The trixie leg ran it green; the noble leg's 2026-11-12 run predates it
    (20 arm64-only build-tool reds).
  - **`[lwip]` `TCP_SND_BUF` 6,400 → 1,600 B** (2026-11-11): nothing installed; a reused chroot's changed
    `toolchain/versions.toml` runs setup once, as above, and `build-lwip` takes the new value.
- **Adopt a genuine non-blocking alternative to every currently-unavoidable blocking call as soon as
  one reliably exists** (owner, 2026-07-24, `cc911be`: 'Don't treat the current state as
  permanently accepted risk'; confirmed by the owner, 2026-09-29). Today's list, each backstopped by
  the hardware watchdog after the recovery ladder (SPECIFICATION.md F.2): a `machine.I2C` transfer
  on a wedged bus; a single `machine.SPI` transfer (synchronous, `ports/rp2/machine_spi.c:303-335`,
  v1.29.0; the FRAM's waits around it wait only on other coroutines, SPECIFICATION.md F.2).
  `socket.getaddrinfo()` is not called from `src/`; its one call is `asyncio.start_server()`'s, on the
  numeric bind host (SPECIFICATION.md F.2). Re-checked at each MicroPython version re-check (CLAUDE.md 'Platform
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
- **Upstream findings, reported later as one bundle, if at all** (owner, 2026-10-27: "we should
  report it later and bundled, if at all", and on this entry: "Yes, let's do it like that"): the
  MicroPython defects this tree meets, among them `py/pairheap.c`'s pop leaving `child_last` set and
  the second await of an ended task raising `None` (SPECIFICATION.md F.1), and the defects behind
  every standing workaround (SPECIFICATION.md F.9). Nothing is reported one by one.

## Owner questions

Questions for the project owner, each dated, in the owner's format; nothing else in the repo parks a
question.
