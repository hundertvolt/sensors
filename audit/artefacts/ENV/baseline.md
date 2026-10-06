# B0 baseline (M.PROC.007)

Measured on the baseline worktree at `798e5a7` (`origin/main` at the go-ahead), host `Linux 6.18.44`, 2026-10-06.
Every row ran once more on a quiet host as the repeat (the spread); the quiet run is the B0 column, the first
run's figures are the busy-host bound. Raw records: `scratchpad/b0/run_baseline.out` (first run) and
`scratchpad/b0/quiet/results.jsonl` (B0), produced by `audit/sweeps/b0_measure.py` (1 s `MemAvailable` sampler, the
runner's max child RSS, `/proc/diskstats` sectors written on the worktree's device; the quiet run with
`NETNS=1`, each port-binding tier in its own network namespace, U0 (5a)).

## Tiers

| row | command | result (B0) | wall s (B0 / first) | host peak RAM MB (B0 / first) | SSD writes MB (B0 / first) |
|---|---|---|---|---|---|
| L0 | `uv run pytest tests_scripts -q` | 2135 passed, 7 skipped | 314.7 / 302.3 | 152.1 / 226.2 | 81.5 / 579.9 |
| L0 | `npm run lint` | rc 0 | 1.8 / 1.6 | 55.1 / 56.1 | 0.0 / 0.4 |
| L0 | `npm run typecheck` | rc 0 | 0.9 / 0.8 | 0.0 / 0.0 | 0.0 / 0.0 |
| L0 | `npm run lint:html` | rc 0 | 0.7 / 0.5 | 0.0 / 0.0 | 0.3 / 0.0 |
| L0 | `npm run lint:css` | rc 0 | 1.1 / 0.8 | 23.9 / 0.0 | 0.0 / 0.1 |
| L0 | `npm test` | 12 files, 817 tests passed | 553.1 / 569.3 | 586.5 / 1117.0 | 257.6 / 1241.7 |
| L1 | `scripts/test.sh` (gc `-1`) | 87/87 files passed; pytest tier as L0 | 317.9 / 308.7 | 200.7 / 214.0 | 48.3 / 183.4 |
| L1 | `GC_THRESHOLD=32768 scripts/test.sh` | 87/87 files passed | 328.5 / 319.5 | 67.3 / 277.6 | 61.4 / 306.5 |
| L1 | `scripts/test.sh --coverage` | 87/87 files passed | 358.7 / 347.1 | 777.8 / 255.6 | 375.2 / 221.6 |
| L2 | `scripts/run_digital_twin_ci.sh arzi` | passed at both GC stages | 713.0 / 714.2 | 8.7 / 36.3 | 34.8 / 25.1 |
| L2 | `… dev` | passed at both GC stages | 864.5 / 861.2 | 112.9 / 1104.5 | 43.2 / 621.4 |
| L2 | `… grkizi` | passed at both GC stages | 712.8 / 728.5 | 19.4 / 2307.7 | 2.9 / 11682.5 |
| L2 | `… klkizi` | passed at both GC stages | 715.4 / 722.2 | 88.1 / 208.9 | 5.4 / 1393.2 |
| L2 | `… schlafzi` | passed at both GC stages | 714.3 / 695.9 | 77.8 / 698.3 | 10.2 / 1237.5 |
| L2 | `… wozi` | passed at both GC stages | 764.9 / 764.7 | 212.4 / 1034.8 | 34.7 / 2145.0 |
| L3/L4 | `uv run pytest tests_hardware --collect-only -q` | 116/138 collected (22 deselected) | 0.4 / 0.4 | 0.0 / 0.0 | 0.0 / 1.1 |
| lint | `scripts/lint.sh` | ruff, shellcheck, actionlint clean; zizmor no findings (16 suppressed) | 0.9 / 1.2 | 0.0 / 2.7 | 0.0 / 4.5 |
| types | `scripts/typecheck.sh` | main 167 files, twin 48, host 131: no issues | 6.4 / 15.4 | 34.5 / 103.1 | 0.2 / 54.1 |
| build | `RUN_SLOW_FIRMWARE_BUILD=1 … test_real_firmware_build_produces_a_valid_uf2` | 6 passed | 257.4 / 166.2 (rc 1) | 409.4 / 389.8 | 724.2 / 445.3 |
| toolchain | `uv run toolchain/setup_toolchain.py test` | rc 0 | 70.1 / 66.0 | 293.9 / 309.1 | 154.8 / 137.3 |

Zero `MemoryError`s and zero "memory allocation failed" lines at both GC stages in every MicroPython tier (the four
gates passed). `test.sh`'s 48 MB write is in line with the expected ~46 MB.

**Differences between the two runs, each root-caused.** The SSD and RAM columns of the first run are device-wide and
include the concurrent gate worktrees of the dependency refresh; the B0 column ran alone. The first run's firmware row
(rc 1) collided with gate (a)'s firmware build in the shared `mpy-cross/build` (the same collision gate (a) recorded,
`dependency_refresh.md`); every later build holds the toolchain lock and passes. The pytest tier's 31 skips in the
first run against 7 here: on a fresh worktree it ran before `scripts/test.sh` had generated `build/generated_src`, so
`test_digital_twin_boot_contiguity.py` skipped 24 tests by design; moving the generated modules away reproduces exactly
those 24 skips. The 7 remaining skips are the steady state.

## Coverage (`--coverage`, line coverage, advisory)

`src/`: 7874 statements, 514 missed, 93 %. Digital twin: 2137 statements, 201 missed, 91 %. Not measured by the
pipeline: the generated device modules (`build/generated_src/`) and the host build chain (`buildgen/`, `scripts/`,
`toolchain/`), which `tests_scripts` exercises under CPython without coverage.

## Type-check flags (measured only, not switched on)

| pass | files | `disallow_any_explicit` | `disallow_any_unimported` |
|---|---|---|---|
| main (`[tool.mypy]`) | 167 | 345 errors in 77 files | 52 errors in 5 files |
| twin (`digital_twin/typecheck.ini`) | 48 | 61 errors in 17 files | none |
| host (`host_typecheck.ini`) | 131 | 82 errors in 21 files | none |

Files no pass names: `tests/network.py` (excluded from the main pass, outside the twin pass's arguments) and
`tests_scripts/conftest.py` (excluded from the host pass for the duplicate-`conftest` reason in `host_typecheck.ini`).
`tests/_webserver_concurrency_scenarios.py` and `tests/_digital_twin_construction_scenarios.py` are excluded from the
main pass and reached by the twin pass only through the imports of the test files it names.

ANN401 per-file exemptions (25):

`tests/machine.py`, `digital_twin/machine.py`, `src/print_log.py`, `tests/test_asy_uart_driver.py`, `tests/test_asy_uart_comm.py`, `tests/_uart_comm_harness.py`, `tests/test_asy_webserver_service.py`, `tests/test_asy_wifi_service.py`, `tests/test_ntp_fram_system_integration.py`, `tests/test_ntp_wifi_dns_integration.py`, `tests/test_asy_udp_socket.py`, `src/asy_notification_service.py`, `src/asy_sgp40_driver.py`, `tests/test_asy_sgp40_driver.py`, `tests/test_notification_scd30_sgp40_integration.py`, `tests/test_notification_sgp40_integration.py`, `tests/test_setter_microdot_integration.py`, `tests/_bus_hazard_catalog.py`, `digital_twin/run_generic_integration.py`, `tests_scripts/test_buildgen_twin_wiring.py`, `tests/_webserver_concurrency_scenarios.py`, `tests/_sensortask_scenarios.py`, `tests/_digital_twin_construction_scenarios.py`, `src/asy_webserver_service.py`, `digital_twin/_http_client.py`.

## Firmware images (`firmware.elf` per device, toolchain lock held across build and read)

Pending: the six builds run under the toolchain lock; this section is filled when they finish.

## Environment

MicroPython `v1.29.0` (`~/pico-toolchain/micropython`); Unix-port probes: `build-standard` plain (no `sys.settrace`),
`build-settrace` settrace. `arm-none-eabi-gcc` 13.2.1 (20231009). Tools against their pins: ruff 0.16.6 (pin 0.16.6),
mypy 2.3.1 (2.3.1), pytest 9.1.1, zizmor 1.30.1 (1.30.1), actionlint 1.7.12 (`actionlint-py` 1.7.12.24), shellcheck
0.11.0 (`shellcheck-py` 0.11.0.1); all match. `uv --version`: 0.8.17 (the value a later uv pin takes). Node v22.22.2
(`.nvmrc` 22), npm 10.9.7.
