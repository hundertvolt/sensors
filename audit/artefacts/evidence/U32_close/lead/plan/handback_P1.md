U32 P1 hand-back (saved by the lead, verbatim in substance, 2026-10-21). Read-only at 6eed1ff (S/wt-u32plan); helper S/u32/plan_scratch/steps.py (each packet step's site, unit, kind, carried actions). 72 tool calls. Every path:line is at 6eed1ff. Verdicts by U32's stage (the Unit/Stages slot), not the whole merged change; "names" = the `task_names` argument at a `start_tasks()` call, which M.SRC_CORE.016 Resolved (g) makes required (GAP-G5).

1. STEP TABLE
| # | M.ID | files | verdict | evidence |
|---|---|---|---|---|
| 1 | DOCS.048 | README.md | to write | no runbook (`git grep "Moving a legacy unit"` none); rule :407-409 still "Always flash `dev`, never `wozi` — `wozi` is never physically flashed; its hardcoded pins…"; other stages landed (:345-401: `<device>`, image record, work dirs, `--no-autostart`); `wozi` recipe lines :356-361 are U36's; step (8) follows fold (1) (silent mode landed, src/asy_wifi_service.py:196 `_PHASE_SILENT`) |
| 2 | DOCS.044 | README.md | part landed | no-auth sentence landed :10-11 (U29); frozen sentence :7-8 still old; its dependency landed (buildgen/codegen.py:846 `sys.path.insert(0, ".frozen")`) |
| 3 | GEN.006 | buildgen/codegen.py | part landed | `_emit_main` :544-559 final except :551 `start_tasks(_collect_task_starters())` needs `task_names=_collect_task_names()` |
| 4 | DOCS.024 | UART_C_PORT_CHANGELOG.md | landed | U32's row is B41 (:164, merged with A.U10.44); table to B84 (:207); no U32 row |
| 5 | GEN.008 | codegen.py | part landed | `_system_status()` :664-676 all keys but `LastTaskEnd` (after `ConfigUnpersisted` :673, before `LocalTime` :674) |
| 6 | GEN.010 | codegen.py | part landed | collectors :771-811; new `_collect_task_names()` after `_collect_task_starters()` (:799-803) |
| 7 | GEN.014 | buildgen/definitions.py | part landed | `system_fields` :668-701 in `_system_status()` order (:667 comment); `LastTaskEnd` row between `ConfigUnpersisted` (:691-694) and `LocalTime` (:695) |
| 8 | HW_DEV.009 | 16 device scripts | landed (+names) | all 16 carry `_SCRATCH_CFG_PATH`; no `build_system(`/`main(` call lacks `watchdog=`; names land at the 11 script `start_tasks` calls (section 3) |
| 9 | HW_DEV.026 | …/system_service_restarts_a_real_dead_task.py | part landed; hardware | modes landed (:26, :28, :49-70, HOLD_FROM_HERE :56); names at :57 `start_tasks([_dying_starter])` → `["dying"]`; bench R1 H16 (L3), escalation R1 H12 |
| 10 | HW_DEV.025 | tests_hardware/flash/test_task_supervisor.py | landed; hardware | :13, :16, :21 `mode="restart"`, :31 leak check; bench R1 H16 |
| 11 | HW_DEV.080 | tests_hardware/flash/test_bus_concurrency.py | landed; hardware | :99 `scd30_measuring`, :243-245 sweep facts, :250, :267, :339, :358; U32 "holds"; bench R1 H25/H29/H31, R3 H30/H31 (owned writes, persistence and scd30 gates) |
| 12 | HW_DEV.117 | …/heap_layout_after_full_boot_sequence.py | part landed; hardware | `start_tasks` under `wait_for_ms` :83; names there; bench R1 H44 |
| 13 | SCR.065 | scripts/build_firmware.py | check-only | CLI landed (:206 `--device-toml`, :207, :224; no-autostart, tick-offset-test, toolchain-dir); A.U32.01 only names the command |
| 14 | SPEC.020 | SPECIFICATION.md (A.7) | to write (1 clause) | packet folds U32's names into U36's rewrite; collector paragraph :871-875 lists three collectors, lacks `_collect_task_names()`; the current-state rule argues adding it now; P2 rules |
| 15 | SPEC.088 | SPECIFICATION.md (F.1) | to write | :5824-5825 "stay on it until the owner reflashes one;" gains `(README.md, "Moving a legacy unit to this firmware")`; other stages landed (:5826-5830) |
| 16 | SRC_CORE.003 | src/asy_system_service.py | check-only | U32 stage "none"; imports :9-37; `JsonDict` into the TYPE_CHECKING list (:34) only if the record is typed JsonDict |
| 17 | SRC_CORE.008 | asy_system_service.py | to write | new `_task_names: list[str] = []`, `_last_task_end = None` beside :227-229 |
| 18 | SRC_CORE.016 | asy_system_service.py | part landed | body landed (U11/U20/U30/U31: :262-265, :291-302, :462-468, :506-578, :720-735, :758-766). To write: `start_tasks(self, task_starters, task_names)` (:720); the name in `_start_task` (:467); in `_log_dead_task` the record and names (:291-302); restart `wrn` :538 appends the name (the bench greps only the prefix, test_wifi_networking.py:115); `get_last_task_end()` among the getters :606-640 |
| 19 | SRC_CORE.072 | src/asy_api_response.py | landed | comment :61-63, `_ERR_CALLBACK` :38, hook failure :73 |
| 20 | SPEC.056 | SPECIFICATION.md (C.5.3) | landed | :3240-3243 "one hook per endpoint, not one per field, as legacy's `post_fct`/`post_asy_fct` (agent, 2026-08-03)" |
| 21 | SRC_NET.170 | src/asy_uart_comm.py | landed | `start_asy_listen` :1024-1026; starters :1014-1019 |
| 22 | SRC_NET.215 | src/asy_uart_link_driver.py | landed | :111-124 |
| 23 | TEST_HELP.028 | tests/_boot_contiguity_probe.py | part landed | names at :135; starters collected :177 |
| 24 | TEST_HELP.038 | tests/_sensortask_scenarios.py | part landed | main-call-order (:1584-1639), supervisor scenario (:1290-1297) landed; to write (2): a names scenario; names at :671, :1293, :1357, :1402, :1969, :2154; expected args :1639 |
| 25 | TEST_HELP.041 | tests/_sensortask_scenarios.py | part landed | status keys checked :2469; U32's (4): `LastTaskEnd` null on a clean boot + per-device "kill one task, `/status` names it" scenario (A.U32.06 blast) |
| 26 | TEST_UNIT.159 | tests/test_asy_uart_comm.py | landed | :723, :801, :831, :858, :2299, :2323 |
| 27 | TEST_UNIT.179 | tests/test_asy_uart_link_driver.py | part landed | U10's two equality asserts missing: :104 and :124 read `len(starters) == 1`, not `== [initiator.start_asy_exercise]` / `== [responder._comm.start_asy_listen]`; U32 holds the file |
| 28 | TEST_UNIT.211 | tests/test_asy_wifi_service.py | landed | :327, :332 |
| 29 | TEST_UNIT.284 | tests/test_ntp_fram_system_integration.py | part landed | names `["NTP"]`, `["BMP3XX"]`, `["SCD30"]`, `["SGP40"]` at :392, :509, :571, :600 |
| 30 | TEST_UNIT.309 | tests/test_asy_system_service.py | part landed | names at 14 calls: :1204, :2622, :2637, :2674, :2706, :2830, :2859, :2918, :2966, :3287, :3324, :3360, :3429, :3517; new `get_last_task_end()` L1s near :2762-2798 |
| 31 | TEST_UNIT.322 | tests/test_uart_comm_cancel_sweep.py | landed | :138 restarts with `start_asy_listen()` by name |
| 32 | TSC.046 | tests_scripts/test_buildgen_generate.py | part landed | pinned line :240 gains names; type table :379-385 gains `_collect_task_names` `'list[str]'`; new test: equal lengths, unique names |
| 33 | TWIN.102 | tests/test_digital_twin_bus_hazard_concurrency.py | part landed | names at :200, :256, :491, :877 |
| 34 | TWIN.144 | tests/test_digital_twin_sensortask_integration.py | part landed | names at :458, :513 |
| 35 | TWIN.158 | tests/test_digital_twin_uart_link.py | check-only | starters "hold" (:226, :395-398); OF-223 joins |
| 36 | WEB.004 | js/definitions.js | to write | :13 union gains `"lasttaskend"` |
| 37 | WEB.006 | js/definitions.js | to write | `FIELD_FORMATS` :82; its comment :80 names web_tag's `_FORMATS`; mirror tests_scripts/test_buildgen_definitions.py:894 |
| 38 | WEB.012 | js/field-format.js | part landed | U23's (:1-100) landed; to write: the (6) `lasttaskend` branch after the `gmtimestruct` branch (:82-84) |
| 39 | PROC.021 | audit/ only | check-only (audit) | re-run A.U32.04/.05 at the sync point; reading legacy allowed here, nothing permanent written |
| 40 | PROC.015 | legacy/README.md | landed | no runbook pointer (grep none); never edited |
| 41 | WEB.045 | mockdata/samples.json | part landed | dev.json/wozi.json gone; `status.system` stops at UnixTime; add `"LastTaskEnd": null` after ConfigUnpersisted |
| 42 | WEB.056 | tests_js/mock-data-compose.test.js (+render test) | part landed | both exist; a `lasttaskend` kind check beside the `gmtimestruct` one :79-81 |
| 43 | WEB.058 | tests_js/templates.test.js | to write | two cases: `{Task, Uptime}` and `null` |

Totals: 12 landed (4, 8, 10, 11, 19, 20, 21, 22, 26, 28, 31, 40); 4 check-only (13, 16, 35, 39); 4 to write (1, 15, 36, 37); 1 one-clause write (14); 22 part landed (2, 3, 5-7, 9, 12, 17, 18, 23-25, 27, 29, 30, 32-34, 38, 41-43; 17 and 43 wholly to write but merged changes). Hardware: runs parked for 9, 10, 11, 12 (all U26-written; U32 edits only 9 and 12); work order `hardware_rounds` `{}`; each run needs the owner's go-ahead, the FRAM evidence saved first, the wear gates. Conflicts: none outright (the packet resolves A.U32.06 (2), (3) itself: names required; `start_asy_*`).
Carried: A.U32.01 → 1, 15 (write), 13, 28 (check); A.U32.02 → 2; A.U32.03 → 19, 20 (landed); A.U32.04 → 39, 40; A.U32.05 → 39; A.U32.06 → 3-12, 17, 18, 21-24, 26, 29-36, 38, 41, 43.
UART marks: 4, 21, 22 edit nothing in U32 (no emitted byte, accept/reject rule or recovery timing). OF-210: log text only, no wire or timing effect, needs a Class B row. OF-180 (b) would touch asy_uart_link_driver.py, only after the owner's answer.

2. OPEN FINDINGS
- OF-36: open; default unchanged; owner answer pending since U11, not in BACKLOG.md's list (:1226+); handler installed asy_system_service.py:725-728, `report_unretrieved` prints only at `level >= _LOG_ERR` (asy_print_log.py:111-117). Joins 18, or moves with no code (R-18 precedent).
- OF-79: open. Sites codegen.py:217 `SgpBackup(fram, ntp.ntp_issynced)`, codegen.py:666 (UTCTime gate), asy_sgp40_driver.py:546-549, asy_fram_manager.py:560-565, :595-599. The clock-set gate exists as `utc_now()` (None until the clock was set this boot, asy_base_classes.py:774-776; `cettime()` uses it, asy_ntp_client.py:526-529). SGP40 half: one emitted wiring line + a small async clock-set callable; UTCTime half stays (REGISTER.md:513 keeps the end state). Joins 5 (codegen).
- OF-180: open; waits on owner question 5 in BACKLOG.md (UART hazards under API load). No U32 work until answered.
- OF-184: open; site moved to asy_system_service.py:713 (`_WRN_CONFIG_LOST`, :54); the row says "no code change"; test_heap_layout.py:39 allows exactly this entry; a product-side scratch-build-only suppression would collide with OR36.a (1). Own step: likely kept open or moved on.
- OF-210: open; sites asy_uart_comm.py:694, :738, :998; the `_discarded_seen` comparison exists at :561-564, :881-888. Own step + Class B row. Log text only.
- OF-223: open; soak bounds tests/test_digital_twin_uart_link.py:116, :278, :680. Joins 35. The padding sweep needs runs; OF-224 is the root cause.
- OF-70: parked until the R2 H37 bench evidence; if causes must be told apart it lands as OF-210.

3. PACKET VS CODE
- Stale names: src/system_service.py → asy_system_service.py; src/api_response.py → asy_api_response.py; tests/test_system_service.py → test_asy_system_service.py; tests/test_api_response.py → test_asy_api_response.py; src/captive_dns.py → asy_captive_dns.py; `UartLinkExerciser` → UARTLinkDriver; `start_listen`/`start_exercise` → `start_asy_listen`/`start_asy_exercise`; `start_and_check_tasks()` gone; `status_counter()` → `_status_loop()`; `_report_unretrieved` → `PrintLog.report_unretrieved` (installed :726-728); legacy `IndividualDrivers/neopixel_signal.py` → legacy/firmware/python/CommonDrivers/neopixel_signal.py; M.TEST_UNIT.322's section is in tests/test_uart_comm_cancel_sweep.py.
- Moved sites: README :263-327 → :345-435, :299 → :407; SPEC C.5.3 → :3225-3249, F.1 → :5822, A.7 → :641-906, A.8 → :907 (its `/status` meanings :958-985 need a `LastTaskEnd` entry); codegen `_emit_main` :544, `_emit_callbacks` :620, `_system_status` :664, collectors :752-811; definitions `_status_section` :650.
- Sites the packet misses: SPEC H.5's format list (:7672); js/definitions.js:80's comment; test_buildgen_definitions.py:894; test_buildgen_generate.py:379-385; tests_js/_expected_display.js checked: PUT matrix only, no change.
- Names outside the 47 work-order files (cost of required names): tests/test_asy_neopixel_driver.py:884, tests/test_asy_webserver_service.py:1323, tests/test_digital_twin_fram.py:847, tests/test_digital_twin_hot_replug.py:142, tests/test_digital_twin_timer_pool.py:182; device_scripts c_stack_budget.py:70, reset_code_command_incomplete.py:72, reset_code_stack_exhausted.py:76, sgp40_sample_cadence.py:79, system_command_config_reset.py:62, system_command_fram_erase.py:120, system_command_hang.py:69, system_command_reboot.py:115, unretrieved_task_exception_handler.py:146.
- Earlier units' parts: U10 never landed step 27's equality asserts. U28's RUF005 unpack (M.GEN.010) not landed (codegen.py:753 `["conn", "ntp"] + [...]`), not U32's. M.SRC_CORE.016's `list[TaskStarter]` typing waits on the reason at :227-228, not U32's.
- Pinned source (v1.29.0): a bound method's `__name__` exists on both targets (function attrs on via rp2 mpconfigport.h:81 and the Unix standard variant mpconfigvariant.h:28; bound method forwards the attribute, objboundmeth.c:112-121, objfun.c:362).
- For P2 to rule: (a) the record typed `JsonDict | None` (a `dict[str, str | int]` is not a JsonDict: invariance, as `ConfigFaults` is copied with `list()` at codegen.py:672); (b) a dict per task end in the supervisor allocates on that path; alternative: keep the task index and uptime as ints, build the dict when read (memory-safety rule); (c) whether `start_tasks()` checks equal lengths of starters and names; (d) `lasttaskend` into web_tag `_FORMATS`, or reword js/definitions.js:80; (e) the runbook's "DEVICE_REFERENCE.md's commissioning list" has no target yet (headings :7-153 none; U36 writes it): drop the pointer or cite what exists; (f) step 14's clause now or at U36.
- Not determinable read-only: the suite with names required (L1/L2 runs); the OF-223 padding sweep; whether the owner answered OF-36 or REGISTER.md:513; where the OR43.a value inventory lives (`git ls-files audit | grep inventor` none: the lead names the file, or the trace goes into U32's close evidence); the A.U32.04/.05 re-run itself (their cited lines are from the A-L HEAD).
