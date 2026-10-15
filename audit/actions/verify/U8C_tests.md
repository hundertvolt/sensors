# A-L verify U8C_tests — U8C + U8C2, files under `tests/` (HEAD 854675a, finished at 0e00aa7 — no code change between them or since a4766a9 outside `audit/`)

Counts: 60 actions checked (A.U8C.01-A.U8C.43, A.U8C2.01-A.U8C2.15, A.U8C2.50, the `tests/` part of A.U8C2.51) · OK 52 ·
FIX 8 (A.U8C.21, A.U8C.24, A.U8C.32, A.U8C.33, A.U8C2.03, A.U8C2.04, A.U8C2.05, A.U8C2.51) · REJECT 0 · ADD 1 action;
1,921 verdict rows checked in context, 14 need a correction (V.01 2, V.03 1, V.05 6, V.06 1, V.07 3, V.08 1); findings
V.U8C_tests.01-10 (9 FIX, 1 ADD); ledger complete for `tests/`. Search: C.0.1 re-run identical (2,265); G1-G15 re-run
identical except 2 G15 zero strings (V.01); 997 − 140 = 857 appearances, the 11 double-family sites listed below → 846.

Per-file counts (rows U8C+U8C2 · non-OK): every file OK except `test_asy_ntp_client.py` 85+28 · 1,
`test_asy_uart_comm.py` 148+18 · 2, `test_asy_webserver_service.py` 94+65 · 2, `test_config_manager.py` 29+7 · 1,
`test_digital_twin_machine.py` 33+14 · 1, `test_digital_twin_uart_link.py` 20+9 · 1, `test_digital_twin_bus_hazard_concurrency.py`
16+6 · 1, `test_digital_twin_sensortask_integration.py` 35+5 · 1 (V.10 shared), plus the cross-file ADD V.09.

## Checked OK
A.U8C.01-A.U8C.20, A.U8C.22, A.U8C.23, A.U8C.25-A.U8C.31, A.U8C.34-A.U8C.43, A.U8C2.01, A.U8C2.02, A.U8C2.06-A.U8C2.15,
A.U8C2.50

Scope: every hit-table row, action and ledger/register-fix item of `audit/actions/U8C.md` and
`audit/actions/U8C2.md` whose file is under `tests/` (70 files, 1,921 rows: 1,268 U8C + 653 U8C2; actions
A.U8C.01-A.U8C.43, A.U8C2.01-A.U8C2.15, A.U8C2.50, the `tests/` entries of A.U8C2.51). Code at `854675a` equals
`a4766a9` outside `audit/` (`git diff --stat a4766a9 HEAD -- . ':!audit'` empty), so both files' line numbers apply.
Scripts: `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/al/verifyU8C_tests/`
(`mysearch.py` C.0.1, `myfam.py` G1-G15, `cmp1.py`/`cmp2.py` comparisons, `actcheck.py`/`chgcheck.py` action
cross-checks), written from the rule texts, not from the authors' scripts.

## Completeness (check 1)

- **C.0.1** (own `mysearch.py`): 2,265 hits, identical key for key to U8C's table (const 290, const-c 253, call 599,
  kw 915, param 60, assert 131, deadline 17), every line the literal's own. Note: C.0.1 kind 1 has no "nonzero"
  clause, and U8C correctly keeps the eight `const … = 0` hits (`tests/machine.py:19, :213, :605`,
  `tests/network.py:11, :14`, `tests/test_asy_uart_comm.py:36`, `tests/test_uart_comm_hazard.py:40`, one in
  `tests_hardware/`).
- **G1-G15** (own `myfam.py`, U8C2's rules as written, same callee index): 995 (family, site) keys on 984 sites;
  U8C2's table + dropped list give 997 on 986. The only difference is two G15 keys U8C2 has and the stated rule
  excludes (V.U8C_tests.01). Every other key matches, family for family; no site in both U8C's and U8C2's tables;
  no duplicate row; every line is the literal's own.
- **Arithmetic 997 − 140 = 857 vs 846**: the table's family column sums to 857 appearances (G4 220, G10 120,
  G12 94, G6 70, G9 69, G2 55, G1 43, G3 41, G7 27, G6s 26, G15 25, G8 20, G13 19, G14 13, G5 7, G7b 4, G11 4);
  the 11 are the sites listed under two families, each counted once:
  `tests/_webserver_concurrency_scenarios.py:185, :199` (G6s/G9), `tests/test_asy_isl29125_driver.py:642` (G4/G6),
  `:1828` (G4/G6s), `tests/test_digital_twin_isl29125_autorange.py:363, :364, :400` (G4/G6),
  `tests_hardware/device_scripts/heap_under_connection_ceiling.py:32`, `serving_at_default_gc.py:71` (G6s/G9),
  `uart_link_under_concurrent_system_load.py:173` (G6/G9), `tests_hardware/flash/test_memory_stress.py:54` (G4/G6).
  The ledger's "new sites" column agrees (G6 75−5−5 = 65, G6s 26−1 = 25, G9 69−5 = 64). Reconciled; with
  V.U8C_tests.01 applied the true figures are 995 − 140 = 855 appearances, 844 sites.
- **Actions ↔ table** (`actcheck.py`, `chgcheck.py`): every tuned/mirror row of a `tests/` file is in its action's
  Site with the same ID and line, and every Site line is in the Change; the 13 deferred-U25 rows are named in their
  actions' Site as "deferred U25"; 323 new constants, no name clash with the file or between U8C and U8C2.

## Per-file results

Per file: rows (U8C + U8C2) opened in context · actions checked · non-OK items. A file with no finding line
is OK in every verdict, ID, mirror and action slot.

- `tests/_boot_contiguity_probe.py` 4+3 · A.U8C.01 · OK (the four shared `l3.heap_layout_after_full_boot_sequence_*`
  IDs: the device script's constants predate the probe's, `git log -S` `c500bb9` vs `309857c`, so its stem is right).
- `tests/_bus_hazard_catalog.py` 14+3 · — · OK.
- `tests/_digital_twin_construction_scenarios.py` 5+0 · A.U8C.02 · OK.
- `tests/_sensortask_scenarios.py` 4+3 · — · OK.
- `tests/_strict_json.py` 1+1 · — · OK.
- `tests/_uart_comm_harness.py` 5+0 · A.U8C.03 · OK.
- `tests/_uart_link_contract.py` 5+0 · — · OK.
- `tests/_webserver_concurrency_scenarios.py` 16+38 · A.U8C.04, A.U8C2.01 · OK (`:140` deferral matches G7/R23's own
  site `:128-140`; `:495, :532, :741` readiness sleeps a counter poll like `_drained()` could replace — deferral right).
- `tests/machine.py` 18+2 · — · OK (every cited port fact checked in `mp/` v1.29.0: `machine_i2c.c:38`,
  `machine_spi.c:267`, `machine_uart.c:68-69, :407`, `extmod/machine_wdt.c:47`).
- `tests/network.py` 8+3 · — · OK.
- `tests/test_api_response.py` 3+0 · — · OK.
- `tests/test_asy_bmp3xx_driver.py` 48+11 · A.U8C.05 · OK.
- `tests/test_asy_dns_client.py` 29+3 · A.U8C.06 · OK.
- `tests/test_asy_fram_driver.py` 5+1 · A.U8C.07 · OK.
- `tests/test_asy_fram_manager.py` 4+4 · A.U8C.08 · OK.
- `tests/test_asy_fram_wire_trace.py` 0+1 · — · OK.
- `tests/test_asy_i2c_driver.py` 6+0 · A.U8C.09 · OK.
- `tests/test_asy_isl29125_driver.py` 26+37 · A.U8C.10 · OK (mirrors `:39, :40, :42` equal `src/asy_isl29125_driver.py:96,
  :97, :102`; `:38, :41` equal the untagged derived `:95, :105`).
- `tests/test_asy_neopixel_driver.py` 35+1 · A.U8C.11 · OK (no sleep patch in the file: every sleep is real).
- `tests/test_asy_notification_service.py` 27+32 · A.U8C.12, A.U8C2.02 · OK.
- `tests/test_asy_ntp_client.py` 85+28 · A.U8C.13, A.U8C2.03 · 1 FIX:
  - V.U8C_tests.02 | A.U8C2.03 (and A.U8C.13) | FIX | U8C row `:2366` says `_NO_REPLY_FETCH_TIMEOUT_MS` "also replaces
    the literal of `:2475`" and A.U8C2.03 says `:2475` is "already covered by A.U8C.13 … no new work", but A.U8C.13's
    Site lists `:2366 (100)` only and its Change replaces only "the literal at :2366"; `tests/test_asy_ntp_client.py:2475`
    (`client.ntp_fetch_timeout_ms = 100`, paired with `:2488` "past the 100ms fetch timeout") is replaced by no action |
    A.U8C2.03 Change, replace the `:2475` clause with: "the literal at :2475 (`client.ntp_fetch_timeout_ms = 100`)
    becomes `_NO_REPLY_FETCH_TIMEOUT_MS`, the constant A.U8C.13 creates for `l1.asy_ntp_client_no_reply_fetch_timeout_ms`
    (a further site of that row)"; and the closing sentence "`:2475` is A.U8C.13's: no work here" becomes "`:2475` is
    replaced here with A.U8C.13's constant".
- `tests/test_asy_scd30_driver.py` 7+16 · A.U8C.14 · OK.
- `tests/test_asy_sgp40_driver.py` 25+62 · A.U8C.15 · OK.
- `tests/test_asy_spi_driver.py` 4+1 · A.U8C.16 · OK (`:655`, `:831` are verbatim copies of `test_asy_i2c_driver.py:719`,
  `:843`: shared IDs right).
- `tests/test_asy_uart_comm.py` 148+18 · A.U8C.17, A.U8C2.04 · 2 FIX:
  - V.U8C_tests.03 | U8C2 row `tests/test_asy_uart_comm.py:952` and A.U8C2.04 | FIX | `:952` `run(scenario(5), limit=20)`
    passes `hold_ms` to `hold()` (`:939-941`: `async with bus: await asyncio.sleep_ms(ms)`) — how long the holder keeps
    the lock, "a holder that acknowledges promptly", the counterpart of `:949`'s 1300. `:945` (`_INSIDE_LOCK_MS`) is the
    scenario's own wait before `clear()` — a different purpose, so "same purpose and value as `:945`" is wrong (C.0.2
    "literals of one purpose … share one constant") | row: `tuned | \`l1.asy_uart_comm_prompt_hold_ms\` — the holder's
    real hold inside the lock, well under the driver's cancel-acknowledgement bound (counterpart of \`:949\`)`;
    A.U8C2.04 Site: "`l1.asy_uart_comm_prompt_hold_ms` :952 (5); derived, untagged: :949 (1300)"; Change: "`_PROMPT_HOLD_MS
    = 5` (new, module level) tagged `# @tunable l1.asy_uart_comm_prompt_hold_ms = 5`; the literal at :952 becomes
    `_PROMPT_HOLD_MS`" (rest unchanged); Blast docs: "`uart.cancel_ack_timeout_ms` Dependants gain
    `_PAST_CANCEL_ACK_HOLD_MS` and `_PROMPT_HOLD_MS` (must stay under 1000 ms)"; U8C2 Status/IDs count +1 new l1 ID.
  - V.U8C_tests.04 | A.U8C2.04 Site | FIX | the Change rewrites `:949` (`scenario(1300)` → `scenario(_PAST_CANCEL_ACK_HOLD_MS)`)
    but Site lists only `:952` (check 3: Site lists every literal's own line the action edits) | Site as in V.U8C_tests.03
    (adds "derived, untagged: :949 (1300)").
- `tests/test_asy_uart_driver.py` 78+13 · A.U8C.18, A.U8C2.50 · OK.
- `tests/test_asy_uart_link_driver.py` 7+1 · A.U8C.19 · OK (`:24-29, :58` restate the harness Pair, comment `:35-36`;
  importing the harness names is right; `_ROOT` in `tests/test_tmp_scratch.py:8` is precedent for an underscore import).
- `tests/test_asy_udp_socket.py` 70+3 · A.U8C.20 · OK.
- `tests/test_asy_webserver_service.py` 94+65 · A.U8C.21, A.U8C2.05 · 2 FIX:
  - V.U8C_tests.05 | U8C rows `tests/test_asy_webserver_service.py:1184, :1237, :1312, :1377, :1445` (the 2.0), `:1741`
    and A.U8C.21 | FIX | these six lines are `_make_service(… per_call_timeout_s=…, outer_cap_s=…)` construction
    arguments — service timeouts that must *not* fire during the case (e.g. `:1184` "Two long-lived (never-completing)
    connections occupy the ceiling"; `:1312` 413 case; `:1741` 8 KiB path) — but the rows give them the run_timed
    hang-bound IDs (`run_bound_s` "run_timed hang bound, value 5.0"; `serve_bound_s` "run_timed hang bound on one
    _serve()"). The file already has the right IDs for exactly this purpose (`headroom_s` 2.0 at `:1158, :1209, :1326,
    :1639, :3081`; `long_headroom_s` 5.0 at `:1445`'s `outer_cap_s`); C.0.2: one purpose → one constant, and a hang bound
    is a different purpose | rows `:1184`, `:1237` → `tuned | \`l1.asy_webserver_service_long_headroom_s\` — service
    timeouts (per-call and outer cap) that must not fire while the held connections occupy the ceiling`; rows `:1312`,
    `:1377`, `:1445` (literal 2.0), `:1741` → `tuned | \`l1.asy_webserver_service_headroom_s\` — service timeout
    (per-call and/or outer cap) that must not fire before the case's own event`. A.U8C.21 Site: `run_bound_s` becomes
    ":45, :1205, :1219, :1265, :1538, :1976, :2048 (5.0)"; `serve_bound_s` ":1065, :1160, :1641, :1661, :3083, :3099
    (2.0)"; `headroom_s` ":1158, :1209, :1312, :1326, :1377, :1445, :1639, :1741, :3081 (2.0)"; `long_headroom_s`
    ":1184, :1237, :1445 (5.0)"; Change: the literals at :1184, :1237 become `_LONG_HEADROOM_S`, those at :1312, :1377,
    :1741 and the `per_call_timeout_s` literal at :1445 become `_HEADROOM_S` (both keyword literals on each of these
    lines).
  - V.U8C_tests.06 | U8C2 row `:1285` and A.U8C2.05 | FIX | `audit/actions/U8.md` A.U8.17 already owns this literal: "`:1285`'s
    factor becomes a module constant `_SERVE_BACKSTOP_CAP_MULT = 20` tagged `l1.serve_backstop_cap_mult = 20`", Basis
    "widened without a stated cause (agent, `<commit>`)" (RF140, `a035736` 4× → 20×). A.U8C2.05 creates a second constant
    and ID for it (`_OUTER_CAP_RUN_FACTOR`, `l1.asy_webserver_service_outer_cap_run_factor`) — two tags and rows for one
    literal | row `:1285` → `tuned | \`l1.serve_backstop_cap_mult\` — run_timed hang bound written as 20 × the outer cap;
    registered by A.U8.17 (widened 4× → 20× without a stated cause)`; A.U8C2.05 Site: `l1.serve_backstop_cap_mult` :1285
    (20); Change: "the factor at :1285 is A.U8.17's `_SERVE_BACKSTOP_CAP_MULT` (`l1.serve_backstop_cap_mult`); no new
    constant or row here" (drop `_OUTER_CAP_RUN_FACTOR`); Depends add A.U8.17; U8C2 Status "108 new test-tier IDs" → 107
    (l1 26 → 25).
- `tests/test_asy_wifi_service.py` 31+37 · A.U8C.22, A.U8C2.06 · OK (the file's `_FastAsyncSleep` is entered only at
  `:679, :2603`; every yield-count loop checked to sleep `0`).
- `tests/test_base_classes.py` 3+2, `tests/test_bus_hazard_generated.py` 1+2, `tests/test_bus_hazard_multi_device.py`
  7+21 · — · OK (the multi-device file patches `asyncio.sleep` to `sleep(0)`, `:44-56`: its counts are yield counts).
- `tests/test_captive_dns.py` 43+16 · A.U8C.23, A.U8C2.07 · OK.
- `tests/test_config_manager.py` 29+7 · — · 1 FIX:
  - V.U8C_tests.01 | U8C2 rows `tests/test_config_manager.py:473` "0" and `:680` "0" (G15) | FIX | U8C2's Families rule
    says "(nonzero literals only …)"; a G15 hit is the number a string encodes, and `"0"` encodes zero. Own re-run of
    G15 with the stated rule: 23 keys, U8C2 lists 25 — these two are the difference | delete both rows (their siblings
    `:473 "10"`, `:681 "10"` stay); U8C2 counts: G15 hits 25 → 23, new sites 25 → 23, test input 22 → 20; total hits 997 →
    995, new sites 846 → 844, test input 275 → 273; Search "Result" line and the ledger total row likewise — or, if zero
    strings are meant to count, add "G15 keeps zero" to the Families rule and leave the rows.
- `tests/test_crc_checks.py` 0+4 · — · OK.
- `tests/test_digital_twin_bmp3xx.py` 0+9 · — · OK.
- `tests/test_digital_twin_bus_hazard_concurrency.py` 16+6 · A.U8C.24, A.U8C2.08 · 1 FIX (V.U8C_tests.10, below).
- `tests/test_digital_twin_fram.py` 1+1, `tests/test_digital_twin_http_client.py` 9+1, `tests/test_digital_twin_isl29125.py`
  10+5, `tests/test_digital_twin_isl29125_autorange.py` 6+14 · A.U8C.25 · OK.
- `tests/test_digital_twin_launch.py` 10+9 · A.U8C.26, A.U8C2.09 · OK (Dependant bookkeeping: V.U8C_tests.09).
- `tests/test_digital_twin_machine.py` 33+14 · A.U8C.27, A.U8C2.10 · 1 FIX:
  - V.U8C_tests.07 | U8C rows `tests/test_digital_twin_machine.py:332, :339, :340` | FIX | the reason cites
    "ports/rp2/machine_wdt.c:37"; `WDT_TIMEOUT_MAX 8388` is at `:38` in the pinned v1.29.0 (`mp/ports/rp2/machine_wdt.c:38`;
    `:33` in v1.28.0); A.U8.08 cites the range `:32-38` | in the three reasons, "machine_wdt.c:37" → "machine_wdt.c:38".
- `tests/test_digital_twin_machine_uart.py` 2+1, `tests/test_digital_twin_network_neopixel.py` 6+0,
  `tests/test_digital_twin_poll_prewarm.py` 2+4, `tests/test_digital_twin_real_website_integration.py` 12+1,
  `tests/test_digital_twin_run_generic_integration.py` 3+4, `tests/test_digital_twin_scd30.py` 4+7,
  `tests/test_digital_twin_sgp40.py` 0+4 · A.U8C.28-A.U8C.31 · OK.
- `tests/test_digital_twin_sensortask_integration.py` 35+5 · A.U8C.32, A.U8C2.11 · 1 FIX (V.U8C_tests.10, below).
- `tests/test_digital_twin_uart_link.py` 20+9 · A.U8C.33, A.U8C2.12 · 1 FIX:
  - V.U8C_tests.08 | U8C row `tests/test_digital_twin_uart_link.py:169` and A.U8C.33 | FIX | `assert driver.poll_wait_ms < 10`
    (`:158-169`) checks the configured `poll_wait_ms` of the generated dev build — a deterministic TOML value
    (`devices/dev.toml`, `dev.uart_poll_wait_ms = 2`); nothing waits and nothing varies run to run, so C.0.2 item 4
    ("bounds or paces a wait the code under test runs on the real clock") does not apply, and U8C2's own reading E puts
    a bound on a deterministic quantity under not tagged | row → `not tagged (property) | design bound "single-digit, or
    poll latency dominates throughput" on the configured dev.uart_poll_wait_ms (deterministic value); recorded in that
    row's Dependants`; A.U8C.33: drop `l2.uart_link_poll_wait_max_ms` :169 (10) from Site and its `_POLL_WAIT_MAX_MS`
    constant/tag from Change; Blast docs add "`dev.uart_poll_wait_ms` (A.U8.06) Dependants: `tests/test_digital_twin_uart_link.py:169`
    (single-digit bound)"; Depends add A.U8.06; U8C Status tuned 1505 → 1504, not tagged 351 → 352, new IDs 576 → 575.
- `tests/test_fake_timer_and_network.py` 5+0, `tests/test_framing_codecs.py` 2+0 (A.U8C.34), `tests/test_math_helpers.py`
  0+30, `tests/test_neopixel_wifi_integration.py` 4+0 (A.U8C.35), `tests/test_notification_fram_integration.py` 2+0,
  `tests/test_notification_neopixel_integration.py` 4+1, `tests/test_notification_scd30_integration.py` 4+2,
  `tests/test_notification_scd30_sgp40_integration.py` 3+5, `tests/test_notification_sgp40_integration.py` 4+7
  (A.U8C.36-A.U8C.39) · OK.
- `tests/test_ntp_fram_system_integration.py` 18+6 · A.U8C.40, A.U8C2.13 · OK (`:313`, `:329` defer to A.U8.17 correctly).
- `tests/test_ntp_wifi_dns_integration.py` 9+3 · A.U8C.41, A.U8C2.14 · OK.
- `tests/test_print_log.py` 0+4, `tests/test_setter_microdot_integration.py` 6+8, `tests/test_ticks_rollover.py` 8+3,
  `tests/test_voc_algorithm.py` 3+10 · — · OK.
- `tests/test_system_service.py` 21+27 · A.U8C.42 · OK.
- `tests/test_uart_comm_hazard.py` 110+15 · A.U8C.43, A.U8C2.15 · OK (Blast line refs checked: `scripts/test.sh:400, :405,
  :413` `_heavy_files_priority`; SPEC J.7 `:5568` holds the `_TIMEOUT_MS * 8` derivation).

## Cross-file findings

- V.U8C_tests.09 | U8C (tests/ part) | ADD | 17 tuned test rows of U8C name a product or test row they depend on
  ("Dependant of …" in the table), but no action writes that relation into the source row's Dependants — U8C2 did so
  for its own cases in A.U8C2.51 and U8C's A.U8C.04 Blast only for `:543`. Without it the source rows' re-check
  triggers cannot find the test values that must move with them (N.1 derived/Dependants rule, A.U8.01) | new action:

  ### A.U8C.120 List the tuned `tests/` sites under their source rows' Dependants
  - **Why**: G4/R54 (as A.U8C.01); U8 N.1 "Dependants" (A.U8.01); the U8C hit-table rows below each state "Dependant of …"
  - **Site**: SPECIFICATION.md Part N (created by A.U8.01), the rows below
  - **Change**: add to Dependants — `notify.loop_tick_s` (A.U8.12): `l1.asy_notification_service_override_tick_s`
    (`tests/test_asy_notification_service.py:1153, :1155, :1186`, one ~1 s decrement plus margin),
    `l2.sensortask_integration_override_poll_s` (`tests/test_digital_twin_sensortask_integration.py:378`);
    `udp.retry_backoff_s` (A.U8.11): `l1.asy_udp_socket_fix_address_after_retry_s` (`tests/test_asy_udp_socket.py:786`,
    after one 0.5 s backoff, before three), `l1.asy_udp_socket_retry_cycle_min_ms` (`:1350`); `dns_server.error_retry_wait_s`
    (A.U8.11): `l1.captive_dns_no_backoff_elapsed_max_ms` (`tests/test_captive_dns.py:482`, well under the 3 s wait),
    `l1.captive_dns_backoff_wait_timeout_ms` (`:941`, covers it); `dns_server.recv_backoff_initial_s` and
    `dns_server.recv_backoff_mult` (A.U8.11): `l1.captive_dns_gap_initial_min_ms`/`_max_ms` (`:1012, :1041, :1044`),
    `l1.captive_dns_gap_doubled_min_ms`/`_max_ms` (`:1013, :1042`), `l1.captive_dns_gap_quad_min_ms`/`_max_ms` (`:1014`);
    `dns_server.recv_backoff_max_s` (A.U8.11): `l1.captive_dns_gap_cap_min_ms`/`_max_ms` (`:1067`, the band around the
    cap, below the uncapped next step); `wifi.sta_retry_after_loss_s` (A.U8.10): `l2.bus_hazard_concurrency_flap_window_s`
    (`tests/test_digital_twin_bus_hazard_concurrency.py:392`, must outlast the 60 s retry); `l2.twin_wifi_connect_delay_s`
    (A.U8.20): `l2.launch_fault_duration_s` (`tests/test_digital_twin_launch.py:230`), `l2.network_neopixel_never_connects_wait_s`
    (`tests/test_digital_twin_network_neopixel.py:149, :251`, longer than the delay); `system.task_check_s` (A.U8.08):
    `l2.sensortask_integration_restart_wait_timeout_s` (`tests/test_digital_twin_sensortask_integration.py:522`),
    `l1.ntp_fram_system_integration_supervisor_scan_wait_s` (`tests/test_ntp_fram_system_integration.py:443, :550, :614,
    :644`, one scan plus margin); `wifi.sta_connect_poll_iters` and `wifi.sta_connect_poll_s` (A.U8.10):
    `l2.sensortask_integration_hotspot_wait_timeout_s` (`tests/test_digital_twin_sensortask_integration.py:594`);
    `l1.asy_ntp_client_no_reply_fetch_timeout_ms` (A.U8C.13): `l1.asy_ntp_client_past_fetch_timeout_ms`
    (`tests/test_asy_ntp_client.py:2488`), `l1.ntp_wifi_dns_integration_past_fetch_timeout_ms`
    (`tests/test_ntp_wifi_dns_integration.py:388`). Each entry states the relation in words; no audit ID in the text.
  - **Blast**: callers — · generated — · js — · tests `tests_scripts/test_tunables_register.py` (A.U8.02) does not check
    Dependants — unaffected · twin — · docs SPEC Part N only · toml — · uart — (`uart.*` rows untouched)
  - **Depends**: A.U8.01, A.U8.08, A.U8.10, A.U8.11, A.U8.12, A.U8.20, A.U8C.12, A.U8C.13, A.U8C.20, A.U8C.23, A.U8C.24, A.U8C.26,
    A.U8C.29, A.U8C.32, A.U8C.40, A.U8C.41
  - **Kind**: doc

  (The `tests_hardware/` rows of the same kind are outside this verification's scope.)
- V.U8C_tests.10 | A.U8C.24, A.U8C.32 | FIX | both site `l2.twin_wdt_feed_interval_s` (`tests/test_digital_twin_bus_hazard_concurrency.py:76`,
  `tests/test_digital_twin_sensortask_integration.py:446`), whose row and first tag are created by A.U8.08/A.U8.20 at
  `digital_twin/launch.py:41` (`_WDT_FEED_INTERVAL_S = 1.0`); A.U8C.24's Depends lists only A.U8.01-A.U8.03, and both
  Blasts name each other but not the twin site | A.U8C.24 Depends: add "A.U8.08, A.U8.20"; A.U8C.32 Depends: add
  "A.U8.20"; both Blast twin slot: "`digital_twin/launch.py:41` carries the same ID (A.U8.20); the row's Sites list all three".

## Ledger, register fixes, open points (the `tests/` parts)

- A.U8C2.51, `tests/` entries (`:949`, `test_uart_comm_hazard.py:844`, `test_asy_uart_driver.py:1862`,
  `test_system_service.py:1251`, `l2.bus_hazard_concurrency_run_seconds`, `l1.asy_ntp_client_retry_armed_poll_tries`,
  `l1.asy_notification_service_override_secs`, `l2.launch_long_min_readings`): each relation checked in context, OK;
  with V.U8C_tests.03 its `uart.cancel_ack_timeout_ms` entry gains "`_PROMPT_HOLD_MS` (5, `:952`, a holder that
  acknowledges well inside the bound)".
- U8C register fixes on `tests/` sites — A.U8.11 `:1067` not a mirror (4700/5400 ≠ 5000), A.U8.08 `:357, :369, :382, :394,
  :410` tuned (real-clock twin WDT), C.0.1's 2,265 — all right. U8C2 register fixes — A.U8.04 `:2569` (`src/asy_webserver_service.py:107`
  `_MAX_PENDING_FRAGMENTS = const(16)`), A.U8.09 `:402, :1198, :1375`, U8C search-gaps 1-4 closed — right; the C.0.1
  total becomes 2,265 + 844 = 3,109 with V.U8C_tests.01. Missing: none beyond V.U8C_tests.06 (A.U8.17 `:1285`, a
  conflict, not a stale U8 line).
- Ledger rows G4/R54, G8/R31, G7/R23 of both files: the `tests/` share is complete (every hit classified, 13 deferred-U25
  sites all in `tests/`, named in A.U8C.02, .04, .30, .32). Open points: the four U8C2 readings and U8C's three cases
  are applied consistently in every `tests/` row checked; none was self-resolvable from an owner row.
