# U26 lane plan: gaps (sites at `a8dc1a1`; packet `pk/U26_steps.md`; rulings `briefs/rulings.md`)

Every default below is conservative and reversible, decided on the owner's behalf for review at the close (agent,
2026-10-14). "R-n" is a ruling.

## 1. Changes placed only in part: the U26 stage of an entry whose unit is later

| step | change | unit slot | what U26 applies (lane) | what stays |
|---|---|---|---|---|
| 23, 28, 117 | M.SCR.029, .033, .028 | U27 | `--no-sync` on every `uv run` (A.U26.75) in `mpremote_connect.sh`, `run_manual_hardware_tests.sh`, `typecheck.sh` (B) | help texts, `uv_sync_retried.sh` (U28's retry), the generator step order |
| 24, 29, 116, 118 | M.SCR.032, .034, .005, .030 | U27 | the renamed markers and flags (A.U26.35/.74), `$EVIDENCE_DIR` and `--no-sync` (B) | floors, `-m` narrowing, lower-level order, exports |
| 30, 119 | M.SCR.067, .065 | U27 | the image record and its `overrides` key (A.U26.02), `--device-toml` (A.S0930.06 (1), R-18) (B) | size report, work dirs, `--no-autostart`, lock, `--tick-offset-test` |
| 36 | M.TOOL.034 | U27 | `addopts = ["--strict-markers"]` with SF-U0-08's one marker table (lead line at `<W1>`, R-23) | `testpaths`, `pythonpath` comments |
| 35, 48, 131, 133 | M.TOOL.031, .030, .032, .079 | U28/U27/U34 | the per-file entries and mypy lines the U26 files need, the five manual names, Any-baseline sections leaving as modules clean (lead, relayed) | the restructures |
| 46, 142, 143 | M.TSC.122, .031, .032 | U27 | the record case and the renamed names (B) | U27's cases |
| 50, 144, 145 | M.GEN.019, M.TSC.046, .056 | U27/U32/U31 | `fram_backed_loggers` in the expected facts and its case; the `bench` validation rows (A) | the rest |
| 26, 192, 25, 31, 97, 121 | M.DOCS.066, .064, .057, .048, .086, .049 | U36/U37 | the U26 paragraph, rows and flag names (X) | U36/U37 rewrites |
| 33, 124-130, 195-199, 212, 219-221 | M.SPEC.* | staged | the U26 stage each names (X) | other stages |
| 22, 113, 164, 175-178, 187-189 | M.HW_DEV.152, .151, .092, .122, .124, .125, .136, .153, .155, .156 | U11/U16/U35/U31/U30/U15/phase C "(U26 form)" | the script and test in the facts/`BENCH` form (D1/D2) | their units' later passes |
| 34 | M.TEST_UNIT.041 | U16 | the seam-count case with A.U26.43 in `tests/test_asy_fram_manager.py` (D1) | — |
| 225, 224 | M.TSC.165, .155 | U35/U31 | A.S0930.34's parts that need A.U26.71's guard derivation (B) | the rest |
| 134 | M.TSC.002 | U24 | the variant-literal form in U26's own tests_scripts files (A, B) | buildgen/twin test files: U24 (landed) or U27 |

## 2. Steps with nothing to write at U26 (verify only, R-17)

| step | change | proof at `a8dc1a1` |
|---|---|---|
| 1 | M.HW_BENCH.004 | `def result_note(` `tests_hardware/conftest.py:139`, `def record_session_note(` `:148` (U7); B keeps them |
| 37, 38, 132 | M.TOOL.041, .055, .038 | `def check_lwip_ensemble(` `toolchain/micropython_overrides.py:275`, `def read_lwip_macros_from_build(` `:841`, `def resolve_board_serial(` `toolchain/setup_toolchain.py:1434`, `BOARD_BY_ID_GLOB` `:208` (U21) |
| 48 | M.HW_DEV.112 (A.U26.19) | no `*reconnect*repro*` file or citation outside `PROJECT_AUDIT_PLAN.md` (removed at U5, `c3df14e`) |
| 115 | M.SCR.003 | `scripts/_archive_evidence.py` exists (U7); A's `evidence.py` calls its API |
| 245, 246, 249, 250 | M.TWIN.013, .016, .102, .120 | `_CMD_CONTINUOUS_MEASUREMENT = 0x0010` `digital_twin/_scd30_chip.py:44`, `_CMD_GET_DATA_READY = 0x0202` `:47`; `class CeilingRefusedError(OSError):` `digital_twin/_http_client.py:65`; the L2 counterparts A.U26.32/.53 call "exists"/"unchanged" (U25) |
| 19 | M.HW_DEV.013 | `### F.5.7` `SPECIFICATION.md:6024`, `### F.5.8` `:6049`, `### F.5.9` `:6213`: the F.8 renumbering is U36's (R-6) |

## 3. Changes each lane applies in its own files (one convention, several lanes)

M.HW_DEV.001, .002, .004 (A writes `bench_facts.pyi`, `_shared/facts.py`, `_shared/watchdog.py`; D1, D2, E convert
their scripts), .003 (A writes the shared includes, D2 two of its own, each lane switches its scripts to `# @include`,
R-21), .011 (B the flash conftest, D1 and D2 their flash modules), .006, .007, .008, .009, .012 (D1+D2, .009 also E), .010 (each wave-2 lane twin-runs its instruments, the lead writes
the record, R-11), M.TSC.002 (A+B), M.HW_BENCH.038 (A writes `conformance.py`, the lead deletes the old module), .040
(B writes `soak_durations.py`, the lead deletes `soak_tiers.py`), .092 (A the runner, the lead the record).

## 4. Files no M entry's Site names that U26 must edit

- `tests_hardware/device_scripts/unretrieved_task_exception_handler.py`, `watchdog_starvation_reset.py` and
  `flash/test_unretrieved_task_exception_handler.py` (D1): no M entry rewrites them, but B's facts and bench-facts guards
  cover every script (`RESULT:` at `unretrieved_task_exception_handler.py`, 3 lines); D1 converts them in the same form,
  seen failing on the guard at `<W1>`.
- `tests_hardware/markers.py`, `tests_scripts/conftest.py` (B): SF-U0-08's fold (R-23).
- `tests_scripts/test_rogue_udp_responder.py`, `test_spoof_udp.py` (B), `test_dns_probe.py` (E) (R-20).
- `tests_hardware/device_scripts/_shared/__init__.py` (A): the `from _shared.<name> import …` type-check imports need a package.
- OF-52's float32 FRC-window script and its case (D2, R-12): name chosen by D2, e.g. `scd30_frc_window_float32.py`.

## 5. Paths in the M texts that are gone or live elsewhere

`dev_legacy/README.md` → `tests_hardware/README.md` "The dev bench" (`:69`, R-14); `src/system_service.py` →
`src/asy_system_service.py`; `tests/test_system_service.py` → `tests/test_asy_system_service.py`;
`tests/_webserver_concurrency_scenarios.py` (retired at U25: A.U26.64's OpenHAB twin scenario is now a family of
`scripts/_digital_twin_scenarios.py`, E names that family); `HARDWARE_TEST_HANDOVER.md`, `REAL_HARDWARE_TEST_QUEUE.md`
(retired, BACKLOG holds the queue); `rig-geometry.json` (a run-time evidence file, not a repo file). Not yet born, so not
cited until their unit lands (R-6's rule for paths): `scripts/micropypath.toml` (U27, R-10), `scripts/uv_sync_retried.sh`
(U28), `scripts/run_bench_rollover_test.sh` (U27, M.SCR.074), `scripts/_devices.sh` (M.TSC.175's docstring names it: A
writes the sentence only if the file exists), `tests_scripts/test_lint_type_scopes.py`, `test_mpremote_connect_sh.py`
(U27), `test_ruff_exemptions_live.py` (U28).

## 6. Cross-lane contracts and expected reds (R-3, R-15, R-22)

- Wave 2 on wave 1: B's guards (`test_device_script_{bench_facts,facts,watchdog,fram_regions,rig_parking,gc_threshold,
  config_flush,config_schemas}`, `test_hardware_clones`, `test_tests_hardware_product_copies`, `test_level_containment`,
  `test_bench_no_task_ended_completeness`, `test_bench_restores_serving`, `test_persistence_write_marker_completeness`)
  and A's worker rule (`test_bench_harness_helpers.py`, M.TSC.024) are red at `<W1>` on D1/D2/E files; each wave-2 lane's
  hand-back names the guard lines that turned green.
- A's final signatures with old callers in wave-2 files (e.g. `reset_all_error_logs(dut_ip, reason)`, ≈30 callers;
  `website_identity.assert_page_is_this_devices_build(..., device=)`; `configured_max_connections(device=None)` keeps old
  calls working): host mypy red at `<W1>` on those callers only, listed in the relay.
- Scripts read across lanes: D2's `sgp40_voc_algorithm_quality.py` by E's `bench/test_bus_concurrency_under_api_load.py`;
  D2's `uart_comm_hazards.py` by E's `bench/test_uart_link_under_api_load.py`; D1's `reboot_fallback_starves_the_watchdog.py`
  and `system_service_restarts_a_real_dead_task.py` stay in D1 with both readers.
- Doc checks red until X: SPEC L.3 `bench` row (`test_toml_schema_contract.py`), E.6.6 rows (`test_level_containment.py`),
  Part N rows (`test_tunables_register.py`), citations of renamed or deleted files (`test_citations.py`).

## 7. Pending owner answers, defaults applied (R-13)

OF-122 (guard the listener close in the `modlwip_eagain` copy): (a) upstream watch only — default; (b) a guard and a host
test (U30) plus a bench check (U26 would add an R1 item). OF-127 (narrow the bench host's passwordless sudo): (a) keep,
the bench host is dedicated on the trusted LAN — default; (b) root-owned wrapper scripts with fixed arguments (U26:
`toolchain/setup_toolchain.py` `_BENCH_SUDO_COMMANDS`, README's sudoers line, every `sudo` call in `bench_control.py`,
`harness.py`, `spoof_udp.py`; about 150 lines across A, B, X). OF-36 (a level-0 death counter in `/status`): default as the
row states; a counter would be a `src/` change outside U26's files. None blocks a lane.

## 8. Counts that differ from the brief

The brief's "162 actions" and "145 scoped tests" match no field at `a8dc1a1`: `work_order.json` U26 has `actions` 161 (=
the union of the steps' `carries`) and 191 `scoped_tests`; 325 steps, 313 files and full gate 6 match.
