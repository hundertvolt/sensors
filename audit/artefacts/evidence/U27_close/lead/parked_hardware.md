# U27 close: parked hardware items (draft)

Nothing ran on hardware in U27 (R-19; `tests_hardware/` only with `--collect-only` or `--twin`): every item below waits for
phase C, each round with the owner's go-ahead given in its own conversation (CLAUDE.md). Rounds and H numbers are plan §7's
(`S/u27/lane_plan.md`), which follows the work order's `hardware_rounds`; instruments are named by their file at `7f34f35` (W2 plus lane E; no instrument below changed since `6b953ae`).
This list extends U26's (`audit/artefacts/evidence/U26_close/lead/parked_hardware.md`, same form): U27 wrote the runners,
the image flags and the manual steps several of U26's rows waited for.

## Every round, before anything writes (plan §7)

- The owner's go-ahead in that round's own conversation; a go-ahead never carries over.
- The FRAM-backed `errcount` and the raw FRAM saved first (U26's session fixture `fram_evidence_saved`); an isolated-driver
  FRAM script lands on production's first chunk, so the logs are read before any FRAM script and before any `ResetErrors`.
- The lower levels L0-L2 at both GC stages first, through the runners (`scripts/_run_lower_levels.sh <L3|L4>` now derives the
  device set before any level runs; `--skip-lower-levels` off by default).
- The image record and `board_image` (U26); the standard board state at start and end.
- Gates: `persistence_write` and `scd30_extra_write` deselect; `flash_cycle`, `soak_duration`, `multi_day_rollover`,
  `neopixel_sweep`, `toolchain_reverify` skip in the test body (U26). New at U27: each runner passes its floor through
  `--marker-floor`, and a caller's `-m` narrows it, never replaces it (`scripts/_require_clean_hardware_run.sh`: the one
  `-m "(FLOOR) and (EXPR)"` printed as `== Marker selection:` into stdout and the archived `pytest.log`).
- Before any round: `[ -c /dev/null ]` on the host the round's checks run from (U27's incident; review list).

## Per round (plan §7)

| round | item | what runs (U27 code it depends on) | markers and wear gates |
|---|---|---|---|
| R0 | H56 | the speed-probe bands, `tool.*` step timings and the lwIP host hammer's slowest write measured on the bench host (`tests_scripts/test_test_sh.py`'s speed-band cases hold the logic); also the `tests_scripts` tier's wall clock there (Part N `runner.tests_scripts_timeout_s`, "measurement owed: ... on the bench Pi4", OF-89; placed in R0 beside H56, agent, 2026-10-15) | none (host only) |
| R0 | H57 | `uv run toolchain/setup_toolchain.py env --tier bench` on the bench Pi: OS record, sudo/`--preserve-env`/`nmcli edit`/picotool checks, uv pin, stale packages, and the spoof's own sudo rule, now probed (`check_spoof_sudo()`, `toolchain/setup_toolchain.py:758-767`; OF-182 closed in code) | none (reads only) |
| R1 | H61 | the two spoofing tests and the off-subnet attempt (`tests_hardware/bench/test_network_resilience.py`, `test_hotspot_role_reversal.py`); needs the sudo rule H57 confirms; A.U26.56's permanent-skip entry decided after (`tests_scripts/test_hardware_verdict.py` holds it) | default run |
| R1 | H73 | A.U27.19: each runner with a caller `-m` runs the floored selection (`scripts/run_flash_hardware_suite.sh -m <expr>`, `scripts/run_bench_hardware_suite.sh`); A.U27.29: `scripts/run_manual_hardware_tests.sh --list`; A.U27.37: the bench tests reading the ceiling through `device_max_connections_by_name()` (`bench/test_heap_under_connection_ceiling.py`, `bench/test_network_resilience.py`); OF-183's DNAT delivery (C) | default run, wear gates off |
| R2 | H17 (OF-60) | `scripts/run_manual_hardware_tests.sh --only fram_unplug_replug_recovery`: the seconds from the FRAM pull to its first FRAM log entry, evidence `fram-pull-latency.txt` (`tests_hardware/manual/manual_bus_electrical.py:117-126`); the watch `l4.manual_bus_electrical_fram_detect_watch_s` = 120 s is estimated, its measurement owed here | manual `confirm()` at the pull; no persisting write |
| R2 | H37 (OF-70) | `--only uart_crossover_pull_recovery`: the seconds to the first failed transfer, every code logged while the jumper is off, the seconds until Transfers resume, evidence `uart-crossover-pull.txt` and the verbatim errcount (`:138-168`); dev only (the one device wiring a `uart_link` pair) | manual `confirm()` at the pull and the replug; no persisting write |
| R3 | H73 (gated) | the floored runners with `--allow-persistence-write` where U26's gated rows run | `--allow-persistence-write` |
| R6 | H63 | `scripts/run_bench_rollover_test.sh` (now written): builds the bench board's tick-offset image (`scripts/build_firmware.py <device> --tick-offset-test --output build/firmware-<device>-tickoffset.uf2`, record `TestOverrides` names it), then the wrapper with `--marker-floor multi_day_rollover --allow-multi-day-rollover --allow-flash-cycle --rollover-image <image>` (`:41`, `:46`); one reflash, about 2 h of REST polls (`tests_hardware/bench/test_ticks_ms_rollover.py`), then the release image again; inside session 1 after R5 and before R4 (U26 §7); U26's row "not runnable until U27 lands" no longer holds | `--allow-multi-day-rollover` + `--allow-flash-cycle`; evidence saved before the reflash |

Parked from U26 and untouched here: M.HW_BENCH.038 (R1 [H25, H26]), M.HW_DEV.116 (R1 [H44]), M.HW_DEV.001 (R1 [H73]); U26's
R7 row (H45, the two-image GC proof) names "a second image per U27's test overrides": U27 landed `test_overrides` with one
member, `tick_offset_test` (M.GEN.009/.019); no second override for H45 was in U27's plan.

## Open findings parked on these rounds

| finding | round, item | what the run reads | instrument |
|---|---|---|---|
| OF-60 | R2, H17 | the FRAM loss's detection latency (the read-path probe option stays U30's) | `manual/manual_bus_electrical.py::test_fram_unplug_replug_recovery` |
| OF-70 | R1 (stalled TX, U26), R2, H37 (pulled line) | the cause each TX failure logs; whether a driver-side cause string is needed (U28, R-23) | `flash/test_uart_crossover.py` (`stalled_tx`); `manual/manual_bus_electrical.py::test_uart_crossover_pull_recovery` |
| OF-181 | R1 (R-12) | measured SGP40 raw steps per sample, the basis for a twin walk (U30): the datasheet gives only the sensitivity, -870 ticks per doubling of VOC concentration (`datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf` Table 1), no per-sample step | `flash/test_sensor_accuracy.py::test_sgp40_voc_algorithm_produces_plausible_and_stable_results` (`sgp40_voc_algorithm_quality.py`, raw ticks per sample) |
| OF-182 | R0, H57 | the bench host's spoof sudo rule, through the new probe | `env --tier bench` |
| OF-183 | R1 | whether DNAT to 127.0.0.1 delivers at `route_localnet` 0 (a setup fix, if needed, is U28's) | `bench/test_network_resilience.py` (`answered_from`) |
| OF-89 | R0 (agent, 2026-10-15) | the `tests_scripts` tier's wall clock on the bench Pi4 | `scripts/test.sh` on the bench host |

## Items added at U27's end

| item | when | what is needed first | where |
|---|---|---|---|
| the board's largest free block after the UART load | R1, H37 or H44 (agent, 2026-10-15; plan §7 names neither) | none: the twin's free-block figures are not the silicon's (the Unix port keeps every module's bytecode and the fakes in its GC heap, about 1.2 MB live after dev's load, against the board's 88 KB built graph), so the twin asserts its floor at gc 32768 only and the board's tripwire stays the device script | `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py`; twin fidelity row (2), `digital_twin/README.md`; relay S :161 |
| the rollover round's tick-offset image | R6, H63 | U27 landed the image flag and the runner; the round still needs U26's session frame and the owner's flash-cycle go-ahead | `scripts/run_bench_rollover_test.sh`; `scripts/build_firmware.py --tick-offset-test` |
