# A-C gap pass, group G3: TEST_UNIT, TEST_HELP, TWIN, TSC (2026-10-01)

Inputs read: the "Gaps for other clusters" section of all 16 `M_*.md`, the three late SPEC gaps of `gap_prompt.md`,
`AC_NOTES.md` items 34-45 (45 in full), OR126-OR133, and the coordinator's three hand-offs (GAPS_G1 H3, GAPS_G2 H-2
to H-4, GAPS_G4 hand-off 3). Each item's carrying change was read in its body, not only its ledger row. The brief also lists the change bodies of
all 16 merges as input, so a second sweep read every "Blast carried by" line that names TEST_UNIT, TEST_HELP, TWIN, TSC
or "TST": about 1,000 pointers. Each named A-ID was checked against the target file's text, and every pointer the target
did not carry was read against its action (table B). Edited: `M_TEST_UNIT.md`, `M_TEST_HELP.md`, `M_TWIN.md`,
`M_TSC.md` and this file. Every edit says "gap pass G3" in its text, and each ledger row it touches names the M-ID.

## A. Items from the "Gaps for other clusters" sections, the late SPEC gaps, AC_NOTES and the hand-offs

| # | Source, item | Target | Gist | Carried by | Reason (when disposed) |
|---|---|---|---|---|---|
| 1 | M_DOCS gap 2 | TSC | `test_request_timeout_ceiling.py:88` cites BACKLOG item 24, which A.U19.14 deletes; repoint to SPEC C.7 at U19 | amended M.TSC.121 | — |
| 2 | M_DOCS gap 2 | TSC | `test_digital_twin_ci_suite_errcount.py:259`, same | amended M.TSC.165 | — (the comment's "was blind" history clause goes in the same edit) |
| 3 | M_DOCS gap 2 | TWIN | `digital_twin/README.md:669` cites item 24 | amended M.TWIN.067 | — (M.TWIN.067 had named item 24 by title, but the item is gone before U25. The edit is staged at U19. The same paragraph's "resets every source in turn" is false after A.U11.31's concurrent reset and is reworded in the same edit, as G4 did for M.SCR.046) |
| 4 | M_DOCS gap 5 = M_PROC gap 3 (c) = GAPS_G1 H3 | TWIN | `README.md:453-456`: no BACKLOG row matches, so the clause goes | amended M.TWIN.064 | — (the change now states the deletion outright and gives its reason) |
| 5 | M_GEN gap 1 | TEST_UNIT | reset-invariant glob reads `sensortask_<device>_main.py` | M.TEST_UNIT.294 (and .269) | — |
| 6 | M_GEN gap 2 | TSC (+TEST_UNIT) | A.U24.44's provider check uses `network_available_locked` | M.TSC.047; M.TEST_UNIT.282/.285 builders | — |
| 7 | M_GEN gap 3 | TSC, TWIN | runner keywords ⊆ `main()`'s; `uart` keys `initiator_bus`/`responder_bus` | M.TSC.151; TWIN: M.TWIN.050 passes the four keywords | — |
| 8 | M_GEN gap 7 | TEST_HELP | SCD30 adds the reader's chunk only (config log RAM-only) | M.TEST_HELP.036 | — |
| 9 | M_GEN gap 10 | all four | mention-only blast items | disposed | a pointer to the "Blast carried by" lines, not an item of its own. Those lines are swept in table B |
| 10 | M_HW_BENCH GAP-B1 | TSC | collect matrix passes `--dut-ip`, `--lwip-control-image` | M.TSC.137 | — |
| 11 | M_HW_BENCH GAP-B2 | TSC | REST save of `/status` before any raw-REPL call | M.TSC.194 | — |
| 12 | M_HW_BENCH GAP-B3 | TSC | bounded settle-poll cases | M.TSC.198 | — |
| 13 | M_HW_BENCH GAP-B4 | TWIN | the named `exec()` moves to `digital_twin/run_device_script.py` | M.TWIN.054 | — |
| 14 | M_HW_BENCH GAP-B4 | TSC | import-graph and import-placement checks follow | M.TSC.098, M.TSC.099 | — |
| 15 | M_HW_BENCH GAP-B5 | TWIN | launch-site guard reads `twin_board.py` | disposed | no TWIN site: the guard is M.TSC.150, the file is HW_BENCH's (M.HW_BENCH.091) |
| 16 | M_HW_BENCH GAP-B5 | TSC | same | M.TSC.150 | — |
| 17 | M_HW_DEV GAP-D1 | TSC | `.pyi` keys = `build()` keys + extras | M.TSC.185 | — |
| 18 | M_HW_DEV GAP-D3 | TSC | schema guard accepts `BENCH["system_schema"]` | M.TSC.074 | — |
| 19 | M_HW_DEV GAP-D7 | TSC | `chunk.block_addr` calls are chunk-scoped | M.TSC.075 | — |
| 20 | M_HW_DEV GAP-D8 | TSC | write-mode `open(` and raw SCD30 config writes count as persisting | M.TSC.119 | — |
| 21 | M_HW_DEV GAP-D9 | TEST_UNIT | U5/U10/U18 edits listing the two deleted WiFi repro scripts are skipped | disposed | no TEST_UNIT change lists them (grep); the TSC list loses them in M.TSC.073 |
| 22 | M_HW_DEV GAP-D10 | TSC | probe constants from `_shared/heap_probe.py`; parsers read rendered or raw sources | M.TSC.076, .081, .166 | — |
| 23 | M_HW_DEV GAP-D11 | TSC | `run_isolated_expect_reset()` runners exempt from the `DONE` rule | M.TSC.186 | — |
| 24 | M_HW_DEV GAP-D14 | TSC | conformance-probe register maps exempt from the copied-constant guard | M.TSC.185 | — |
| 25 | M_PROC gap 4 | TSC | cross-browser probe test; device-script loop check; shell conventions with `--device` cases; legacy check (`legacy/README.md` tracked, `dev_legacy/` absent) | M.TSC.184, .186, .213; amended M.TSC.101 | — (M.TSC.101 now names the old roots, `dev_legacy/` among them) |
| 26 | M_PROC gap 7 | TWIN | M_TWIN's LEAD gap (`.gitignore`) | disposed | closed by M.PROC.019 (PROC owns `.gitignore`) |
| 27 | M_SCR gap 3 | TSC | port-lock inheritance, scenario harness, twin-CI runner, generator, archive, `EVIDENCE_DIR`, `-noautostart`, `test.sh` jobs and exit 2, Run 1 nulls | M.TSC.206, .192, .211, .158, .177, .122, .032, .134-.136, .165 | — |
| 28 | M_SCR gap 3 (M_SRC_NET gap 3) | TSC | A.U6.28 radio fields, A.U10.05 counters, A.U30.03 run-phase rows, A.U10.22 readiness | M.TSC.040, .069, .107, .112 | — |
| 29 | M_SCR gap 4 | TWIN | the runner's shutdown line carries the twin FRAM chip's write count (A.U35.28 (3)) | amended M.TWIN.011 (`write_count`, `writes_at`), .050 (`fram_writes=`, `fram_writes_by=`), .110, .140; M.TSC.165 parser | — (per-logger field added by row 96) |
| 30 | M_SPEC gap 3 = late SPEC gap 3 | TEST_UNIT | idle-wait degrade test cannot reach its path on the 2**62 rig | amended M.TEST_UNIT.176 | — (`poll_idle_ms = 2**61`, a precondition that the rig raises, and a poller ready on its second poll; F.8.2 is unchanged) |
| 31 | M_SRC_CORE GAP-G3 | TEST_UNIT, TEST_HELP | debug-level tests go through the `/system` PUT | M.TEST_UNIT.311; M.TEST_HELP.039 | — |
| 32 | M_SRC_CORE GAP-G4 | TEST_UNIT | unpause after `_reboot()`/acceptance leaves storage paused | M.TEST_UNIT.307 | — |
| 33 | M_SRC_CORE GAP-G5 | TEST_UNIT, TEST_HELP, TWIN | every direct `start_tasks()` passes `task_names` | M.TEST_UNIT.284, .309; M.TEST_HELP.028, .036, .038, .040; M.TWIN.102, .144, .152 | — |
| 34 | M_SRC_CORE GAP-G6 | TSC | counter check exempts `_err_cnt_internal` | M.TSC.069 | — |
| 35 | M_SRC_CORE GAP-G8 | TSC, TEST_UNIT | `report_if_fatal` from `asy_print_log` | M.TSC.001, .090; M.TEST_UNIT.292 | — |
| 36 | M_SRC_CORE GAP-G9 | TSC | catalog gains `FRAMManager._chunks` | M.TSC.107 | — |
| 37 | M_SRC_CORE GAP-G10 | TSC | `asy_crc_checks`/`CRCPass` in A.S0930.01's agreement test | amended M.TSC.057 | — (no TSC change wrote `test_uart_crc_modes_match_crc_checks`; it now reads the end-state module and class. GEN's table is M.GEN.024 as G1 amended it) |
| 38 | M_SRC_CORE GAP-G11 | TEST_UNIT | `_crc()` takes the polynomial | M.TEST_UNIT.260 | — |
| 39 | M_SRC_CORE GAP-G13 | TEST_UNIT | `coerce_numeric()` tests call the private halves | M.TEST_UNIT.251 | — |
| 40 | M_SRC_NET gap 5 | TEST_UNIT, TEST_HELP | raising `_led_on` double; `led_pin` L1s void; UDP crossing tests lose their site; `_transfers`; `_BANNER` by `src_const`; `set_callback` readers | M.TEST_UNIT.213, .210, .313 (Resolved), .179, .181, .154; M.TEST_HELP.023 | — |
| 41 | M_SRC_SENS GAP-1 | TSC | `src/` sleep-form scan with the two exceptions | M.TSC.128 | — |
| 42 | M_SRC_SENS GAP-2 | TEST_UNIT | `recoveries` wraps at `COUNTER_CAP` | M.TEST_UNIT.056 | — |
| 43 | M_SRC_SENS GAP-3 | TSC | `voc_algorithm.py` exempt from D.15 order | M.TSC.064 | — |
| 44 | M_SRC_SENS GAP-5 | TEST_UNIT | `_overlay_*` names | M.TEST_UNIT.078, .079, .274, .276 | — |
| 45 | M_SRC_SENS GAP-6 | TEST_UNIT | the `sea_level_pressure <= 0` guard test goes | M.TEST_UNIT.011 | — |
| 46 | M_SRC_SENS GAP-8 | TEST_UNIT | the `test_base_classes.py` case uses `_trigger_loop()` | amended M.TEST_UNIT.228 | — (it still named `_divide_trigger()` and the public `read_event`) |
| 47 | M_SRC_SENS GAP-10 | TEST_HELP | one SCD30 chunk, not two | M.TEST_HELP.036 | — |
| 48 | M_SRC_SENS GAP-11 | TSC | SCD30 `always=` tuple pinned to `alwaysExecuted` | M.TSC.106 | — |
| 49 | M_SRC_SENS GAP-13 | TSC | lock table `_threshold_lock`; `self._i2c_<chip>` | M.TSC.105 | — |
| 50 | M_SRC_SENS GAP-15 | TEST_UNIT | pre-sync `TS` `None`, no streak step | M_TEST_UNIT conventions; M.TEST_UNIT.017, .061, .122, .130 | — |
| 51 | M_SRC_SENS GAP-15 | TWIN | no twin boot expects a restart for want of NTP | M_TWIN convention C4 (applied by each booting change) | — |
| 52 | M_SRC_SENS GAP-17 (+ AC_NOTES 38/42/44/45) | TSC | readiness gate: protocol classes exempt; `NeopixelDriver`, `NotificationService` gated | M.TSC.112 | — |
| 53 | M_TEST_HELP GAP-T1 | TEST_UNIT | public `RUN_LIMIT_S`/`LISTENER_DRAIN_S`; `build_pair()` asserts setup | M.TEST_UNIT.153, .178 | — |
| 54 | M_TEST_HELP GAP-T2 | TEST_UNIT | reset/bootloader raise after counting; `WDT(>8388)` raises | M.TEST_UNIT.264, .301, .305 | — |
| 55 | M_TEST_HELP GAP-T3 | TEST_UNIT | RTC fake normalises and recomputes the weekday; per-id `Pin`/`I2C` | M.TEST_UNIT.264 (fake cases), conventions (`reset_id`); amended M.TEST_UNIT.104 | — (the NTP read-back `:987-989` still expected the `tm[6] + 1` the client writes; it now expects the recomputed weekday) |
| 56 | M_TEST_HELP GAP-T4 | TEST_UNIT | `ioctl()` answers `-EINVAL`; the real-poll L1 zeroes its counter | M.TEST_UNIT.169; new M.TEST_UNIT.335 | — (the real-poll L1 lives in `tests/test_machine_uart_link.py`, a file in no cluster) |
| 57 | M_TEST_HELP GAP-T5 | TEST_UNIT | network fake seeds, static objects, cyw43 raises, AP `STAT_GOT_IP` | M.TEST_UNIT.215, .216, .219, .264 | — |
| 58 | M_TEST_HELP GAP-T6 | TEST_UNIT | NeoPixel fake GRB bytearray | M.TEST_UNIT.081 | — |
| 59 | M_TEST_HELP GAP-H1 | TSC | `_MIRRORED_BOUNDS` drops `_STARTER_LOOP_GRACE_MS` | M.TSC.081 | — |
| 60 | M_TEST_HELP GAP-H2 | TWIN | in-DUT scenario content lands in the host harness | disposed | the site is SCR's (`scripts/_digital_twin_scenarios.py`): M.SCR.018 carries it, and the TWIN files are deleted (M.TWIN.136, .144, .164) |
| 61 | M_TEST_HELP GAP-H3 | TWIN | one `write_offline_ntp_config()` | M.TWIN.053; amended M.TEST_HELP.047 to match | — (TEST_HELP said "the runner imports it from `tests/`", but TWIN moves it to `digital_twin/unixport/` at U25 because the runner may not import `tests/`. The two now say the same) |
| 62 | M_TEST_HELP GAP-H4 | TWIN | the boot-sequence scenario imports `_boot_recorder.py` | disposed | no TWIN site: the scenario is M.TEST_HELP.030; its twin boot uses C4 and M.TWIN.108 |
| 63 | M_TEST_HELP GAP-H6 | TSC | `_PENDING` leaves in U24; `_NAMED_EXCEPTIONS` | M.TSC.098, .099 | — |
| 64 | M_TEST_UNIT GAP-U2 | TSC | keyword idioms each match at least once | M.TSC.088 | — |
| 65 | M_TEST_UNIT GAP-U7 | TEST_HELP | after-each resets `_utc_valid` and the fatal flag | amended M.TEST_HELP.002 | — (step (d), only for modules already imported; the `_fatal` line lands in U30) |
| 66 | M_TEST_UNIT GAP-U8 | TEST_HELP | `FakeNtpServer.serve_once() -> bool`; port from `PortAllocator` | amended M.TEST_HELP.058 | — |
| 67 | M_TOOL gap 1 | TSC | config-path check excepts `build/generated_src/**` | M.TSC.066 (and .123) | — |
| 68 | M_TOOL gap 2 | TSC | `uv_sync_retried.sh` attempts/backoff equal `NETWORK_ATTEMPTS`/`backoff_s` | M.TSC.223 | — |
| 69 | M_TOOL gap 5 | TEST_UNIT | `test_website_build_integration.py:15` `noqa` goes in U20, not U28 | amended M.TEST_UNIT.332 | — |
| 70 | M_TOOL gap 9 | TWIN | a new twin module using twin-only API joins the main pass `exclude` | amended M.TWIN.054 (names `run_device_script.py`); hand-off 2 | — (`_twin_common.py`, `_wall_clock.py`, `unixport/*` import no twin `machine`/`network`, so none of them joins) |
| 71 | M_TSC gap 4 | TWIN | conformance check covers the twin fakes' `TEST_API` | M.TWIN.020-.036 | — |
| 72 | M_TWIN gap (TEST_HELP) | TEST_HELP | `device_with(*drivers)`, `devices_with_shared_bus()` | amended M.TEST_HELP.055 (and M_TWIN's C2 line) | — (TEST_HELP had `device_with(driver)`/`device_with_shared_bus(a, b)`. A.U36.015 amends A.U25.48 to the all-devices loop that M.TWIN.102 calls) |
| 73 | M_TWIN gap (TEST_HELP) | TEST_HELP | `_generated_module.py` imports the moved writer | amended M.TEST_HELP.047 | — (same as row 61) |
| 74 | M_TWIN gap (TEST_HELP) | TEST_HELP | `_uart_comm_harness.py` keeps its path-resolved import and `Pair(crc_a=, crc_b=)` | amended M.TEST_HELP.023 (item (6) states it) | — |
| 75 | M_TWIN gap (TSC) | TSC | `--test-fault-status-interval-ms` in the flag table | M.TSC.220 | — |
| 76 | M_TWIN gap (TSC) | TSC | A.U30.16's two twin rows keep their function names | M.TSC.095 | — |
| 77 | M_WEB gap 7 | TSC | checks read `tests_js/_twin_process.js`; new `tests_js` tags scanned | M.TSC.108, .147, .150, .169, .202 | — |
| 78 | AC_NOTES 42 (1) | TEST_UNIT | every L1 file opens with a ≤ 3-line header | M.TEST_UNIT.334; new files' headers in .335-.339 | — |
| 79 | AC_NOTES 39 | TEST_UNIT | `CRCBase` out-of-range polynomial cases | M.TEST_UNIT.262 | — |
| 80 | AC_NOTES 41 | TSC | OR131/OR132 written firm | M.TSC.154, .224 | — |
| 81 | AC_NOTES 43 | TSC | OR133: rejection tests expect exit 2 | M.TSC.134 | — |
| 82 | GAPS_G4 hand-off 3 (a) | TSC | rollover runner: no lower level, `Levels: rollover (not a level)` | amended M.TSC.196 | — |
| 83 | GAPS_G4 hand-off 3 (b) | TSC | rollover floor and `--allow-multi-day-rollover` forwarded | amended M.TSC.122 | — |
| 84 | GAPS_G4 hand-off 3 (c) | TSC | `TOOLS` gains the rollover runner | amended M.TSC.217 | — |
| 85 | GAPS_G4 hand-off 3 (d) | TSC | record cases for `overrides` and `lwip` from the build dir | amended M.TSC.032 | — (the key list also takes M.SCR.067's `BuildDate`, `deviceToml`, `uartCrc`, `autostart`; it had HEAD's `buildDate`) |
| 86 | GAPS_G2 H-2 (a) | TEST_UNIT | `handle_set_cmd()` returns the per-field `WriteValidity`; `ok_descr` gone | amended M.TEST_UNIT.004, .005 | — (every `:195-355` test asserts the returned dict; `test_handle_set_cmd_ok_descr_override` goes) |
| 87 | GAPS_G2 H-2 (b) | TEST_UNIT | validators take `object`; `type_or_range_error()` refuses with `(True, None)` | amended M.TEST_UNIT.251 | — |
| 88 | GAPS_G2 H-2 (c) | TEST_UNIT | readers of the G2 private names follow | amended M.TEST_UNIT.111; new conventions bullet in M_TEST_UNIT naming every privatised attribute and its HEAD readers | — |
| 89 | GAPS_G2 H-2 (d) | TEST_UNIT | readiness L1 gains `SystemService`, `SensorReader` (+ subclasses), `FRAMManager`; `WifiService`/`WebserverService` `setup() -> bool` | amended M.TEST_UNIT.293 | — |
| 90 | GAPS_G2 H-3 | TEST_HELP | `sysfunct.watchdog` → `_watchdog`; `_uart_comm_harness.py` UARTComm attributes | amended M.TEST_HELP.037 | the harness half is disposed: the harness reads none of the privatised names (grep at HEAD: only `listener.cancel()`, a task) |
| 91 | GAPS_G2 H-3 | TWIN | twin readers of the private names | amended M.TWIN.158 (`:153-154` `_payload_size`, `_timeout`) | — (no other twin reader: `module.watchdog` is the generated module's global, and the runner reaches the UART buses through `machine.peripheral()`, M.TWIN.049) |
| 92 | GAPS_G2 H-4 (a) | TSC | readiness check counts an inherited flag; three new flag carriers | amended M.TSC.112 | — |
| 93 | GAPS_G2 H-4 (b) | TSC | GAP-D7 check reads `chunk._block_addr` | amended M.TSC.075 | — |
| 94 | GAPS_G2 H-4 (c) | TSC | `test_port_lock.py` also drives the JS lock (re-entrant, inherited) | amended M.TSC.206 | — |
| 95 | GAPS_G2 H-4 (d) | TSC | no E.5.1 narrowing row | disposed | no TSC change writes an E.5.1 row (grep of `E.5.1`/A.U35.41 in M_TSC: none). The row is SPEC's (GAPS_G2 H-5 (c)) |
| 96 | Lead, via coordinator (follow-up to row 29) | TWIN (+TSC) | M.SCR.018 (h) keeps its per-module bound: the shutdown line keeps `fram_writes=<total>` and adds `fram_writes_by=<LOGGER>:<n>,…` (loggers that wrote, sorted, SPEC A.7 names) | amended M.TWIN.011 (chip keeps `writes_at` by start address, capped at 2048 keys with a dropped counter), .050 (runner attributes each address to the logger whose chunk `_block_addr` holds it; `_module` global), .110, .140, .059; M.TSC.165 (parser cases) | — (unit: one landed multi-byte copy write; one persisted entry counts 2, in the total too. TEST_UNIT pins no shutdown line) |

## B. "Blast carried by" pointers naming a G3 cluster that no G3 change carried

Every pointer whose A-ID or content the target file holds was counted as carried. These are the rest.

| # | Pointer (source) | Target | Gist | Result |
|---|---|---|---|---|
| B1 | M.TEST_HELP.017/.025 → A.U24.15, A.U24.06 | TEST_UNIT | real-poll L1, `ioctl(10, 0)` `-EINVAL`, contract-registry completeness, all in `tests/test_machine_uart_link.py` | new M.TEST_UNIT.335 |
| B2 | M.SRC_SENS.031 → A.U2.17 (+ U5/U10 constructor changes) | TEST_UNIT | `tests/test_notification_fram_integration.py` | new M.TEST_UNIT.336 |
| B3 | M.TEST_HELP.035 → A.U24.65 | TEST_UNIT | six `test_sensortask_<device>.py` → one `PER_DEVICE` file | new M.TEST_UNIT.337 |
| B4 | M.TEST_HELP.005 → A.U24.10/.11 | TEST_UNIT | `tests/test_tmp_scratch.py`: errno filter, duplicate key, recorded `ilistdir`/`stat` | new M.TEST_UNIT.338 |
| B5 | M.TEST_HELP.065 → A.U35.10 | TEST_UNIT | `tests/test_driven_time.py` self-test | new M.TEST_UNIT.339 |
| B6 | M.HW_DEV.060/.063 → A.U26.43 (TSC) | TEST_UNIT | seam count: five transfers per `_write_chunk()` in seed-script order | amended M.TEST_UNIT.041 (A.U26.43 allows "an L1 test with a recording fake". An `ast` count of call sites is not the transfer count: the status writes go through one helper) |
| B7 | M.TEST_UNIT.061 → A.U15.R04 | TEST_UNIT, TWIN | ISL29125 re-apply mid-operation, at L1 and L2 ("as A.U15.R01") | amended M.TEST_UNIT.238, M.TWIN.102 (and .061's Blast line) |
| B8 | M.TEST_UNIT.080 → A.U22.01 | TWIN | L2: a restarted signal task ends dark with the overlay restored | amended M.TWIN.132 |
| B9 | M.HW_DEV.106 → A.U26.58 | TWIN | fidelity row: scheduler queue not modelled | amended M.TWIN.059 |
| B10 | M.SCR.053 → TWIN README | TWIN | Run 5's keyed fault `sgp40:readfrom_into:3:0x260F` | amended M.TWIN.064 |
| B11 | M.SRC_CORE.016 → A.U30.19 (TWIN) | TWIN | L2 C-stack proof: a CLI fault raising the stack-exhausted `RuntimeError` in one read | amended M.TWIN.044 (`DEVICE:OP:stack`), .045 (`_apply_fault`), .068 (README), .124 (tests), .059 (row), .064 (Run 12 text); the proof run itself is hand-off 3 (a) |
| B12 | M.SRC_CORE.016, M.TEST_UNIT.309 → A.U31.07 (TEST_HELP) | TEST_HELP | scan-budget scenario: ≤ 4 task-end entries per pass, one escalation feed | amended M.TEST_HELP.037 |
| B13 | M.HW_BENCH.010 → A.U26.80 (TSC) | TSC | `harness.get_routes()` L0, `/notification` included | new M.TSC.226 |
| B14 | M.SRC_CORE.045 → A.U19.16 (TSC) | TSC | result-word literal scan over `src/` and the generated modules | new M.TSC.227 |
| B15 | M.HW_BENCH.102 → A.C.17 (TSC) | TSC | wear guard's manual branch (`_MANUAL_PERSISTING_STEPS`, `confirm(` first) | amended M.TSC.119 |
| B16 | M.HW_DEV.009/.120 → A.U26.10 (TSC) | TSC | the two serving scripts in `_PREREQUISITE_DEVICE_SCRIPTS` | amended M.TSC.119 |
| B17 | M.TOOL.052/.065/.071 → A.U21.26, A.U21.27 (TSC) | TSC | passwordless-sudo L0; picotool skip/USB/shadow L0 | amended M.TSC.126 |
| B18 | M.SCR.062 → A.U24.68 (TSC) | TSC | no argument exits 2 naming the devices | amended M.TSC.213 |
| B19 | M.DOCS.043 → A.U37.15 (TSC) | TSC | phase D drops each check's `audit/`/`PROJECT_AUDIT_PLAN.md` exclusion | amended M.TSC.071, .110, .113 (.063 and .101 already said so) |
| B20 | M.TWIN.050 → "their L0 parsers (TSC)" | TSC | shutdown-line parser cases | amended M.TSC.165 |
| B21 | M.SRC_NET.118/.127, M.SRC_CORE.038, M.TEST_UNIT.202/.203 → A.U19.07, .08, .10, .12 (TWIN) | TWIN | L2 webserver cases: `Content-Length: -1` → 400, `HTTPDropped` rises at the ceiling, ISL29125 PUT concurrent with GET loops | disposed to hand-off 3 (a): the in-DUT concurrency library and its wrappers are retired into SCR's host harness (M.TEST_HELP.033, M.TWIN.164, M.SCR.018) |

Read and found carried or mislabelled (no edit): M.GEN.062 (A.U23.12 is `tests_js`, WEB carries it), M.HW_BENCH.063 and
M.TSC.046 (A.U20.07's L2 half is M.TEST_HELP.030), M.HW_BENCH.064 (A.U26.54 is `pyproject.toml`, TOOL), M.HW_BENCH.111
(`machine.py:482` is M.TWIN.027 via A.U1.25; A.U1.24 is GEN's), M.HW_DEV.132 (the chip fakes against the probes:
M.TWIN.010 rows and phase-C deltas, A.C.10), M.SPEC.153 (A.U36.020 is TWIN's, M.TWIN.122/.126), M.SRC_CORE.002 (holds),
M.SRC_CORE.006 (M.TWIN.032 stage U11), M.SRC_CORE.012 (M.TSC.133's generic rule), M.SRC_CORE.042 (A.S0930.19 is
M.TSC.119), M.SRC_CORE.043 (holds), M.SRC_NET.047 (no twin test asserts NTP codes; the suite is SCR's), M.SRC_SENS.002
(A.U8.19 is SPEC's), M.SRC_SENS.050 (A.U20.28 is GEN's), M.TEST_HELP.031 (SCR), M.TEST_UNIT.127 (A.U15.15's general
call reaches the fakes: M.TWIN.014/.102), M.TEST_UNIT.264 (A.U24.16: no TSC file names the old path, grep), M.TEST_UNIT.309
(A.S0930.28's twin runs are M.TWIN.054's), M.TWIN.054 (A.U35.49 is kept current by M.TSC.219), M.DOCS.064 (M.TWIN.059 (3)),
M.HW_DEV.010 (phase C). The 53 pointers that name no A-ID were each read. Every one is either a gap-section item above or
an "unchanged/holds" note.

## Hand-offs (other groups carry these; no file of theirs was edited)

1. **TOOL**: the main-pass `exclude` in M.TOOL.032 gains `digital_twin/run_device_script\\.py$` in U26. That module calls
   the twin-only `machine.configure_wiring()`, which `tests/machine.py` lacks. This is M.TOOL.032's own rule for a new
   twin-API module (M_TOOL gap 9; M.TWIN.054). Confirm it at landing by running the main pass.
2. **HW_BENCH**: the `resetconfig` power-cut step of M.HW_BENCH.102 (4) takes `confirm()` before it runs
   `config_files_restore.py`, and states "rewrites the saved config files once". M.TSC.119's manual branch requires that
   for every persisting script a manual step runs (A.C.17's rule).
3. **SCR**: (a) M.SCR.018/.059 gain the L2 cases that no harness change carries: A.U19.07 (a raw-socket
   `Content-Length: -1` request answers 400); A.U19.08/.10 (`/status` `HTTPDropped` rises by one after a forced refusal
   at the ceiling); A.U19.12 (an ISL29125 `Resolution` PUT concurrent with `GET /sensors` loops, every GET consistent);
   A.U30.19, in Run 12 or a sibling run (`--fault <device>:<op>:stack` on a device that wires the driver; the run exits 3
   and the relaunch reads `ResetReason` 20; the form is M.TWIN.044). (b) M.SCR.018 (h) and M.SCR.051 read
   `fram_writes_by=` per logger (row 96, the lead's direction; G4 is amending (h) in parallel). Counts are copy writes:
   one persisted entry is 2, so a logger's bound is 2 × `rate.persisted_log` × window; `fram_writes_unattributed=` above
   0 means attribution was incomplete.
4. **SRC_NET**: M.SRC_NET.199's Blast line describes the L1 as "`poll_idle_ms = 2**29`". The test uses `2**61` with a
   poller that is ready on its second poll (M.TEST_UNIT.176). The code change is unaffected; only the pointer text is.
5. **DOCS**: `README.md:157`'s status-tag example `[test_sensortask_dev]` names a file A.U24.65 deletes. The tag is
   `<file>[<device>]` (M.TEST_UNIT.337, M.SCR.040-.042). `CLAUDE.md:577`'s `test_sensortask_wozi.py` 24.6 s → 9.3 s is a
   dated measurement; M_SPEC keeps the same figure at `:739`. Keep it as dated, naming the file as it was then.
6. **Orchestrator (CLUSTERS.md)**: these HEAD files are named under no cluster. G3 took them, and they should be listed:
   `tests/test_machine_uart_link.py`, `tests/test_notification_fram_integration.py`, `tests/test_tmp_scratch.py`,
   `tests/test_sensortask_<device>.py` (six, → `tests/test_sensortask.py`) and `tests/test_fake_timer_and_network.py`
   (M.TEST_UNIT.264) under TEST_UNIT; `tests/_shared_rest_roundtrip.py` (M.TEST_HELP.009) under TEST_HELP;
   `tests/test_digital_twin_fram.py` and the twelve `test_digital_twin_{construction,webserver_concurrency}_<device>.py`
   (M_TWIN's scope) under TWIN.

## Owner questions

None. Every item is settled by a carrying change, a rule (G7/R02 for the offline-NTP writer's home; G9/R12 and OR27.a for
the history clauses; AC_NOTES 38/42/44 for the readiness gates; CLAUDE.md's wear-gate rule for the manual branch), a
finished merge's end state (A.U36.015 over A.U25.48; A.U10.44 over A.U15.40; M.SCR.067 over A.U26.02's key names), or the
action's own stated alternative (A.U26.43's L1 form; A.U25.65's "else the sentence goes").

## Agent decisions for the OR2.c review

- **G3-1**: the A.U30.19 L2 fault is a `DEVICE:OP:stack` form in the existing `--fault` grammar (a fifth spec element
  `kind`). It is not a new flag, which follows A.U30.19's own wording ("`--fault` vocabulary").
- **G3-2**: the twin FRAM chip records landed copy writes by start address; the runner, which holds the booted module,
  attributes them to loggers through each chunk's `_block_addr`, so the chip fake needs no knowledge of the manager's
  layout (row 96).
- **G3-3**: A.U26.43's seam count is an L1 in `test_asy_fram_manager.py`, not a TSC `ast` check (row B6).
- **G3-4**: the four orphan L1 files and the per-device wrapper set are taken into TEST_UNIT (rows B1-B4).

## Counts

- Items read: 117. Table A has 96: 77 gap-section items (row 30 is also late SPEC gap 3; row 4 is also GAPS_G1 H3), 4
  AC_NOTES items, 4 GAPS_G4 hand-off items, 10 GAPS_G2 hand-off items and 1 lead follow-up (row 96). Table B has 21
  uncarried blast pointers.
- Carried as found: 56 (table A).
- Amended: 45. Table A has 32: rows 1-4, 25, 29, 30, 37, 46, 55, 61, 65, 66, 69, 70, 72-74, 82-94 and 96. Table B
  has 13: B6-B12 and B15-B20.
- New merged changes: 7. They are M.TEST_UNIT.335-.339 (B1-B5; .335 also carries table A row 56) and M.TSC.226 and .227
  (B13, B14).
- Disposed: 8. Table A has 7: rows 9, 15, 21, 26, 60, 62 and 95. Table B has 1: row B21, passed to SCR in hand-off
  3 (a).
- Handed off: 6 entries (TOOL, HW_BENCH, SCR, SRC_NET, DOCS, orchestrator).
