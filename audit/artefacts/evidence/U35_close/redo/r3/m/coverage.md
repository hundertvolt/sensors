# R3 lane M: the coverage run classed (agent, 2026-11-04)

Run `r3m_cov` on `S/wt-r3` at `17688315` (rebuilt by `r3m_rebuild`): `PICO_TOOLCHAIN_DIR=S/tc-int scripts/test.sh
--coverage`, rc 3, 864 s. Every test passed (files 129 passed, 0 failed, 62 skipped by design; tests_scripts 6,786
passed, 6 skipped; MicroPython tests 5,441 passed, 54 skipped). rc 3 is "coverage report not rendered" for src/,
digital_twin/ and the generated modules: each `uv run scripts/_render_coverage.py` found no `coverage==7.16.2` in the
offline uv cache of this sandbox (class (c): the sandbox's cache, not the tree). The raw dumps were kept by the runner
(`build/archive/test_sh/20261104T164016Z/coverage_raw`, 129 dumps) and rendered by `r3m_cov_render` with the shared
venv's coverage 7.16.2 (`python scripts/_render_coverage.py --raw-dir ... --data-file <outside the tree>`):
src/ 9,639 statements, 798 missed (92 %); the generated modules 1,071, 127 missed (88 %); digital_twin/ 4,448, 356
missed. The host chain rendered in the run itself: 10,353 statements, 2,605 missed (75 %). The reports were moved out
of the tree (`git status` clean).

`r3m_e51`: `audit/sweeps/e51_sweep.py`'s own functions over that data (its `analyse`, `artifact_lines`, `build_sites`),
scope src/ and build/generated_src/, joined with `e51_verdicts.json` (sites in `m/data/e51_r3.json`, the host chain's
missed lines in `m/data/host_missed.json`); the sweep's `--self-test` passes.

## src/: 798 missed statements = 785 tracer artefacts + 13 lines at 12 sites

Artefacts (executed, never recorded; SPECIFICATION.md E.5.1): private_const 730, while_true 26, decorated_def 19,
elif_leaf_test 5, bare_annotation 5.

| site | reached when | class | verdict and evidence |
|---|---|---|---|
| `src/asy_base_classes.py:594` `SensorReader._init_done` | `bus is None` true (new site) | (b) guard | an extension point: every current caller (BMP3XX `:167`, ISL29125 `:245`, SCD30 `:214`, SGP40 `:204`) sets `_recovery_bus` in its constructor, so only a reader not on I2C reaches it; "regard the modules as libraries" (owner). Kept. |
| `src/asy_scd30_driver.py:313` `SCD30_Reader._set_mgr_cfg` | ContMeas False and `stop_continuous_measurement(value=False)` answers False | (a) **reachable, untested: gap** | the verdict named `test_contmeas_false_with_the_bus_down_after_the_snapshot_comes_back_failed`; that test went with `dddb3902` (it dropped the bus with `deinit()`, a no-op since). Reached when the snapshot read succeeds and the stop command's write fails (`stop_continuous_measurement()`'s `except` at `:670`, a NAK). Proposed test below. |
| `src/asy_fram_manager.py:461, 526, 539, 600` | `dbuf/tbuf/bbuf is None` true | (c) | unchanged verdicts: type narrowing, stated in place |
| `src/asy_system_service.py:431` | `task is None or not task.done()` true | (b) | unchanged verdict: safety guard registered untestable in E.5.1 |
| `src/asy_uart_comm.py:556, 972-973, 1073`; `src/asy_uart_link_driver.py:160, 226` | `rx/buf/own/bus is None` true | (c) | unchanged verdicts: type narrowing, stated in place |

Dead lines: none. Stale verdicts (sites no longer unexecuted or no longer present, the subtraction): 25, among them the
I2C clear's held-SCL returns (now executed), the bus-not-initialized raises `dddb3902` removed, the UART driver's
ring-absent returns and the web server's `_system_cmd is None` return.

## The generated modules: 127 missed = 121 artefacts + 6 lines, one site per device

Artefacts: bare_annotation 79, private_const 42.

| site | reached when | class | verdict |
|---|---|---|---|
| `build/generated_src/sensortask_<device>.py` `_system_cmd_callback`'s last `return False` (arzi:80, dev:91, grkizi:80, klkizi:80, schlafzi:80, wozi:82) | `cmd == "erasefram"` false: a command none of the five names | (c) guard | the callback's bool return needs the fall-through; through the product only `_dispatch_system_cmd` (`src/asy_webserver_service.py:721-727`) calls it, with a member of `_SYSTEM_CMDS`. Kept. |

## Host chain (buildgen/, scripts/, toolchain/): 2,605 missed

Per file, by the reason the line does not run in this tier. "main" means `raise SystemExit(main())` under
`__name__ == "__main__"`: the tests call `main()` in-process, the scripts run it as a subprocess. "(b) I/O" is a
documented runtime failure (an `OSError` on a read, a missing tool) turned into the tool's own error.

| file | missed | class and reason |
|---|---|---|
| `buildgen/codegen.py` | 3 | `:215`, `:663` (b) internal-invariant raises (`BuildInternalError`); `:525` (d) an ISL29125 with a `name_ext` (no device TOML has one) |
| `buildgen/definitions.py` | 12 | `:241-243`, `:265-270` (d) a readonly special that is a string, `null` or an int (no current field has one); `:393` (d) a tuple-valued literal; `:856-858` (b) I/O; `:873` main |
| `buildgen/driver_registry.py` | 2 | `:52` (b) a non-UTF-8 driver source; `:102` (b) a class not in its file |
| `buildgen/frozen_modules.py`, `schema_ast.py`, `web_tag.py` | 3 | `:74` (b) a module reached twice (no diamond import today); `:92` (b) a non-tuple schema record; `:100` (b) a tag line ending in whitespace after its last pair |
| `buildgen/generate.py` | 2 | `:72` (b) internal invariant; `:186` main |
| `buildgen/validate.py` | 8 | `:464`, `:1068`, `:1075`, `:1094` (b) internal invariants; `:715` (b) a non-numeric limit (the schema check refuses it first); `:1154-1155` (b) I/O; `:501` (b) an optional pin left unset (every TOML sets each at this call) |
| `scripts/_generate_sensortask_modules.py`, `_render_coverage.py`, `_strip_type_checking.py`, `_check_gc_collect_sites.py`, `build_firmware.py`, `toolchain/micropython_overrides.py` | 27 | (b) I/O and missing-tool errors, main, and `_strip_type_checking.py:31-36` (b) non-guard `if` shapes; `_check_gc_collect_sites.py:139` (b) a generated source that does not parse, `:282-283` its generate-all path, run by `scripts/lint.sh` as a subprocess |
| `scripts/_digital_twin_scenarios.py` | 1,069 | executed by the plain pass's scenario tier (`scripts/test.sh:739-742`, "not run under --coverage") and by `run_digital_twin_ci.sh` |
| `scripts/_digital_twin_ci_suite.py` | 539 | executed by `run_digital_twin_ci.sh` (CI's `digital-twin-e2e`, 12 jobs); the run here is tests_scripts' unit tests only |
| `scripts/_stage_website.py` | 365 | run as a subprocess of `scripts/build_website.sh`, which `tests_scripts/test_stage_website.py` drives; coverage follows no subprocess |
| `scripts/record_twin_instrument_runs.py` | 170 | its test went with the twin record (R0, `ffdee74e`; ACTION_LIST item 1 keeps both out); this lane's run 4 drives it end to end |
| `scripts/_hardware_verdict.py` | 75 | the hardware tiers' verdict, run by their shell runners as a subprocess |
| `scripts/ci_apt_cache.py` | 94 | CI's mirror and cache CLI paths (network); its tests drive the planning and check functions |
| `toolchain/setup_toolchain.py` | 108 | real-host install paths (apt, sudo, picotool, the bench bridge, clean builds): the owner's manual chroot run covers them (CLAUDE.md "Build-environment verification") |
| `scripts/_archive_evidence.py`, `_port_lock.py`, `_pytest_run_record.py`, `_summary_block.py`, `_twin_process.py`, `preview_server.py` | 128 | each a CLI `main` run as a subprocess (`_archive_evidence`, `_summary_block`, `preview_server`), a stale-lock or dead-pid path (`_port_lock`: `_clear_stale`, `_take`), pytest hooks only a real hardware session calls (`_pytest_run_record`), or a twin that exits or never serves (`_twin_process`: `wait_until_serving`, `wait_exit`) |

No host line is classed dead. Gaps from the host chain: none (every unexecuted error path has a reason above).

## Gaps (to the lead)

1. `src/asy_scd30_driver.py:313`: proposed test in `tests/test_asy_scd30_driver.py`: ContMeas False with the snapshot
   answered and the stop command's write refused (`nak_addresses` set after the snapshot) answers `Failed` and logs one
   E CHIP_SET.
