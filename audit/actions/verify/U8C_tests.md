# A-L verify U8C_tests — U8C + U8C2, files under `tests/` (HEAD 854675a)

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
