# U26 close: parked hardware items (draft)

Nothing ran on hardware in U26: every item below waits for phase C, each round with the owner's go-ahead given in its own
conversation (CLAUDE.md). Rounds and H numbers are plan section 7's (`S/u26/lane_plan.md`), which follows the work order's
`hardware_rounds`; instruments are named by their file at `ee42b0e`. BACKLOG.md's "Real-hardware work still owed" holds the
same rows for the repo (X's rows: the reset codes, the UART receive ring, Altitude with `AmbPres` 0, the SCD30 argument reaction,
among others); this list is the close's view, with the items U26 added at its end.

## Every round, before anything writes (plan section 7)

- H01: the owner's go-ahead in that round's own conversation; a go-ahead never carries over.
- H02: the FRAM-backed `errcount` and the raw FRAM saved first: the session's autouse `fram_evidence_saved`
  (`tests_hardware/conftest.py:323`, `GET /status` through `save_errcount`, then `save_fram_raw("session-start")`, `:299-306`)
  and the session-end pair (`:493-496`). The first-chunk caveat stands: an isolated-driver FRAM script lands on production's first
  chunk, so the logs are read before any FRAM script runs, and a scratch build plants `W CONFIG_LOST` (69) (OF-184).
- H03: the lower levels L0-L2 at both GC stages first (the runners' `--skip-lower-levels` is off by default).
- H04: the image record and the identity fixture (`tests_hardware/bench/conftest.py:71`, `:83`); a reflash mid-session is
  re-checked by `check_image()`.
- H05: the standard board state at start and end (`tests_hardware/conftest.py:463`; a deviation exits unless
  `--repair-standard-state`, a repair read back).
- H06: the boot log; H07: the bench network dead-man's switch armed around every `br0` change (the owner's operation,
  SPECIFICATION.md B.13).
- Gates: `persistence_write` and `scd30_extra_write` deselect (AND-gated); `flash_cycle`, `soak_duration`,
  `multi_day_rollover`, `neopixel_sweep`, `toolchain_reverify` skip in the test; the pinned prerequisites stay unmarked (the SCD30
  start at most once, the `joined_hotspot` SSID clear and restore, the standard-state repairs under `--repair-standard-state`).

## Per round (plan section 7)

| round | items (H) | instruments (lane that wrote them) | gates |
|---|---|---|---|
| R0 | H65 bench facts; H01 prerequisites, H07 host network | README Prerequisites and host recipe (X); the sweep's per-bus scan (`bus_topology_autodetect_and_hazard_sweep.py`, D2), FRAM RDID (`fram_raw_dump.py`, A), the rig, DHCP keying, BME688, host OS (the owner) | none (reads only) |
| R1 | H08 pre-audit capture; H10, H12, H14, H15 reset and reboot codes; H13 ungated command rows; H16, H18 (L3 case), H81 recovery rungs; H20, H21, H23 loop lag, stretches, C stack; H22, H72 FRAM hold, forensic scripts, reset-race seams; H25, H26, H27, H29 conformance probes, register volatility, PRST, lone BMP3xx; H31 SCD30 prerequisite and the five dependents; H37 UART hazards, multi-chunk SET, both CRC modes over the jumper; H39 (override half), H40, H41 lwIP hammer, PCB count at the ceiling, body cap; H44, H83 heap bounds, loaded `MemFree`; H48, H51 float boundary, deinit, scheduler drop, alarm pool, country code; H55 estimated tunables; H61 spoofing; H65 scan; H69 starvation test ends serving; H71 interaction cells; H73 every other new or changed test | D1 (reset codes, commands, FRAM, memory, loop scripts, starvation, supervisor), D2 (bus hazards, conformance, UART flash, electrical, rungs), E (STA, network resilience, ceiling, bus and link under API load, radio re-init, spoofing, boot order), B (session fixtures, prerequisite) | default run only: every wear gate off |
| R2 | H11 power-on code; H13 two manual power cuts; H17 SCD30/FRAM unplug-replug, SDA-to-GND (OF-60); H18 scope; H28 M1 rig geometry; H30 0x0010 across a power cycle; H49 power cut during a config write; H65 rig row; H66 Safari/mobile, captive portal | D1 `tests_hardware/manual/` (persistence, bus electrical, sensor accuracy, wifi, toolchain) through `scripts/run_manual_hardware_tests.sh` | `confirm()` before each persisting step (`_MANUAL_PERSISTING_STEPS`); the SCD30 power-loss step's up to 21 NVM writes declinable at the step (REGISTER `:125`) |
| R3 | H13 `resetconfig`; H28 S3b envelope with `Overrange`; H30 SCD30 argument reaction and the two owned offset writes; H31 read-while-write; H32 config-write arm under API load; H33 Altitude with `AmbPres` 0; H36 `TempOffs` 0.53 as typed; H42 console output with a non-reading host at level 0; H47 config float round trip; H62 role reversal, destructive stage last; H68 torn write on the reset race; H73 gated rows | D1 (commands, float round trip, reboot persistence), D2 (envelope, SCD30 writes), E (hazard arm, sensor push, network row (3), role reversal, end-to-end backup reset) | `--allow-persistence-write`; `--allow-scd30-extra-write` on top where marked (owner question 3 on its reach); `--allow-neopixel-sweep` (envelope) |
| R4 | H38 CRC16 bench run on a reflashed image; H39 lwIP stall on the unpatched control image, then the override; H55; H70 reflash smoke test and toolchain re-verification | E (`bench/test_uart_link_crc16.py`, `bench/test_modlwip_send_stall.py`), D1 (`flash/test_toolchain_flash_boot.py`), A (`harness.reflash()`), B (image record, `--device-toml`) | `--allow-flash-cycle` (each of the three image tests skips without it since the lead's fix, OF-178); `--allow-toolchain-reverify`; evidence saved before each reflash; the round ends on the release image (`board_image`) |
| R5 | H19 trigger spacing; H34 FRC readiness defaults; H55; H64 6 h soak; H35 SGP40 cadence; the memory and clock-stretch soaks | E (boot order, FRC baseline, memory stress bench), D2 (cadence, electrical soak), D1 (memory stress soak) | `--soak-duration short|mid|long` through `scripts/run_bench_soak_tests.sh`; the bench suite runner's floor now holds these back (`not soak_duration`, OF-179) |
| R6 | H63 rollover across the tick and 32-bit wraps, about 2 h, inside session 1 after R5 and before R4 | E (`bench/test_ticks_ms_rollover.py`) | `--allow-multi-day-rollover` + `--allow-flash-cycle`; needs U27's tick-offset image and rollover runner (M.SCR.074): not runnable until U27 lands |
| R7 | H45 two-image GC proof | D1's heap-layout arms (`flash/test_heap_layout.py`) on two images | a second image per U27's test overrides; phase C |

H08, H18, H36, H45, H55, H69 are in the work order's U26 rounds but named by no U26 change's Kind; each maps above to the instrument
that serves it. M.HW_BENCH.104 (first flash of a blank board) is in no round by its own text.

## Open findings parked on these rounds (from `of_updates.md`, `of_new.md`)

| finding | round, item | what the run reads | instrument |
|---|---|---|---|
| OF-40, OF-107 | R1, H10/H12 | whether REASON/CHIP_RESET tell a soft reset from the hard one before it; an exception after `BOOT_DONE` against code 2 | `bench/test_reset_reasons.py` (records `ResetBits` with every attributed reset) |
| OF-52 | R1 | the first silicon run of the float32 FRC-window check | `flash/test_sensor_accuracy.py::test_scd30_frc_window_sums_hold_in_float32` (no SCD30 command) |
| OF-105 | R1, H44 | dev's post-boot free heap at its six-connection ceiling; the Part N row follows | `bench/test_heap_under_connection_ceiling.py`, `bench/test_serving_heap_at_default_gc.py` |
| OF-119 | R1, H37 | the receive ring for the 400 ms continuous-sender window and its heap cost | `flash/test_uart_crossover.py::test_no_frame_is_lost_while_interrupts_are_off` (fails up front naming the size until `devices/dev.toml` sizes it) |
| OF-123 | R1/R4, H39 | ENOMEM after queued bytes on silicon (the U30 reachability half stays U30's) | the lwIP hammer; `bench/test_modlwip_send_stall.py` |
| OF-183 | R1 (the network-resilience run) | whether DNAT to 127.0.0.1 delivers at `route_localnet` 0; the garbage NTP/DNS tests fail "the injection never reached the DUT" if not | `bench/test_network_resilience.py` (`answered_from`) |
| OF-60 | R2, H17 (after U27 adds the figure) | the FRAM loss's detection latency per device | `manual/manual_bus_electrical.py::test_fram_unplug_replug_recovery` (no latency recorded at ee42b0e) |
| OF-70 | R1 (stalled TX), R2, H37 (pulled line, after U27 writes the step) | the cause each TX failure logs | `flash/test_uart_crossover.py` (`stalled_tx`); the pulled-line manual step (not written) |
| OF-184 | every round reading FRAM evidence | the scratch-build `W CONFIG_LOST` and test-band residue, read against the session-start dump | `tests_hardware/README.md:972-977` |

## Items added at U26's end

| item | when | what is needed first | where |
|---|---|---|---|
| dev's UART receive ring sized for the 400 ms continuous-sender window, with its heap cost measured | R1, H37 | the size chosen from the run (lane D2 relayed 8192 B on `uart1`, 4,608 B arriving in the window at 115200 baud; the driver-default 512 B stands, SPEC J.6/I.2, agent, 2026-10-08); then `devices/dev.toml` (its next unit U36) | BACKLOG.md "The UART receive ring sized for the bench's interrupts-off window"; OF-119 |
| the DNAT delivery check | R1 | none; if it does not deliver, `route_localnet` on the bench host or a redirect to a host address (OF-183) | `tests_hardware/README.md:913-922` |
| the spoof's sudo line | before R1's H61 | the owner adds the rule for `sudo -n <venv python> tests_hardware/spoof_udp.py` by hand: `env --tier bench` does not probe it (OF-182, U27) | `tests_hardware/README.md:40-44` |
| `PERMANENT_SKIPS`' spoof entry removed | after the spoof test passes on the bench (R1, H61) | the phase-C attempt (A.U0.35, A.U26.56 (3), a C delta); until then the entry is inert, since the test no longer skips | `scripts/_hardware_verdict.py:34-36`; checked by `tests_scripts/test_hardware_verdict.py:294` |
| `config_write_loop_scratch.py` and `config_scratch_readback.py` | R2, H49 (the power cut during a config write) | both scripts written, in the U26 form (M.HW_DEV.155, "Unit: phase C (U26 form)"); the manual step names them and fails while they are absent | `tests_hardware/manual/manual_persistence.py:146-163`; `_MANUAL_PERSISTING_STEPS` gains the scratch script's row ("up to 20 scratch flash writes and one removal") when it lands |
| the C-stack exhaustion's reset code | R1, H10/H12 reads 5; 20 once U30 lands it | A.U30.19 adds `ResetReason` 20; `bench/test_reset_reasons.py::test_a_c_stack_exhaustion_is_attributed` reads 5 until then (the lead's CARRY U30) | `bench/test_reset_reasons.py:175` |
| the flash-write loop-gap test | its round once U31 lands it | `flash_write_loop_gap.py` and `test_flash_write_loop_gap_is_recorded` written at U31 (M.HW_DEV.115 "U30/U31 tests written in U26 form when those units land", M.HW_DEV.123) | D1's step 84 (partly) |
| the twin record's silicon-only cases | each at its round | none: every exception entry of `tests_hardware/twin_record.json` names its reason (100 exceptions at the close head); those cases are proven on silicon only | `scripts/record_twin_instrument_runs.py`; `tests_scripts/test_twin_record.py:40` |
| OF-122 (b)'s bench check, OF-180 (b)'s hazard mode | only on the owner's (b) | the owner's answer (R-13; `owner_questions.md` 5) | — |
