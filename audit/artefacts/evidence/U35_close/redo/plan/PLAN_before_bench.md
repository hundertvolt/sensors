# Finishing the audit: the repair, the remaining work, and how it ends

Written by the lead, 2026-10-28 13:20 UTC; checked row by row against the sources the same day (`plancheck/`). A
plan only: nothing in it starts without the owner's go-ahead.

The owner's request (2026-10-28): "a plan to do all the tidy and repair work in the existing status"; "a plan about
which items remain open from current U35 until the end - revised with the new knowledge"; "a plan how to implement it,
not drifting away but having a clear and defined end, not cutting back on quality".

What it rests on:
- the scan against the pre-audit state, `scan/REPORT.md`;
- the second pass and its removal closure, `scan/scan2/SCAN2.md`;
- the decision review, `scan/decrev/DECREV.md`;
- the drift analysis and its ten rules, `scan/DRIFT.md`;
- the picture and the cleanup's rules, `scan/PICTURE.md` sections 2 and 8;
- the owner's rows in `PROJECT_AUDIT_PLAN.md` 3.2 and the rulings file.

## 0. In short

- **One target state, unchanged since the scan.** Each module is the pre-audit code, plus the confirmed gaps' small
  fixes, plus the owner's decided features in their smallest form. Everything else goes, and stays documented as
  knowledge (PICTURE 8).
- **The old plans are retired, not followed.**
  - Retired: the seven paused lanes, the U35 closing ledger's lane items, and U35-U37's 170 planned actions.
  - What they owe the owner is carried by the owner's own rows, which this plan maps phase by phase.
  - Their recipes, written against old line numbers and in the old way of working, are not executed.
- **Seven phases and two hardware rounds, each phase a finite list with a done-criterion, and a stop at each phase
  end:**
  - R0, settling (no product code);
  - R1, the firmware and build chain repair;
  - R2, the tests, tooling, CI and register repair;
  - R3, the test campaign done once, on the final tree;
  - the first hardware round;
  - R4, the docs, written once from the final state;
  - R5, the close of execution;
  - then the last round and the close (D).
- **The way of working is fixed before the start.**
  - Code changes only on evidence.
  - Every change is mapped to a reason.
  - Numbers go to the owner after every batch.
  - A budget per phase stops the work at 80 % for a report.
  - New work is admitted only by rule.
  - At most two lanes run at a time, and the lead reads every changed line.
- **Quality is not cut.** Every owner decision, every confirmed gap and every rare-but-real case stays effective. All
  gates stay strict: the memory gates at both GC stages, the hang backstop, strict typing, the comment cap, the bus
  hazard rule, the wear rules and the UART changelog. Machinery serving only the audit goes; no check of a product
  property goes with it.
- **Checked row by row (2026-10-28, on the owner's request).** Every row was checked against the code, the pre-audit
  tree, the owner's rows and the pinned sources, and corrected where the evidence did not hold
  (`plancheck/CHANGES.md`); independent agents then tried to falsify the claims (4.4, rule 11).
- **All seven decisions were taken by the owner on 2026-10-28** (section 6). R0 starts only with its own go-ahead.
  Six clarifications are asked later, each at the start of the batch or checkpoint it affects (section 7).

## 1. Where the project stands

**The tree.**
- The pushed audit head is `0603e74d` (snapshot 18). Its product tree equals the integration head `497b3eda`.
- The integration history (300 commits since the redo's base, 97 on the first-parent line) stays in this container:
  its messages carry lane names, which the redo keeps out of pushed commit messages (a practice of the redo, not an
  owner rule; ten earlier pushed subjects carry them). Its messages and changed files are kept in the evidence folder
  (`redo/int_history.txt.gz`). The plan does not need the history itself.
- CI on snapshots 16-18 was red only on `test_twin_record`'s two checks. All 6,058 unit-tier MicroPython tests pass at
  both GC stages. The 24 twin end-to-end jobs and the coverage job are success-gated behind the red unit jobs and have
  not run in CI since 2026-10-21 (run 39665515089 on `49fde7b5`, green, 27 minutes).
- Paused by the owner:
  - lanes LD+CM3, CRr2c and IN2, whose unmerged work is saved as patches in the evidence folder (`redo/paused/`);
  - lane CRr2d, just started;
  - lanes CMr1n, RF1 and CM4, queued.

**The size against the pre-audit state** (`REPORT.md` 1, 2, 9, 10):

| | before the audit | now |
|---|---|---|
| free flash in the dev image | 107 KiB (U0 baseline) | about 42 KiB (a lane build of 2026-10-26; R0 re-measures it) |
| `src/` bytecode (bare source names) | 161,626 B | 208,708 B (+47,082 B, +29 %) |
| firmware lines in behavioural changes (`REPORT.md` 2's rows) | | about 3,900, of which about 1,640 are in doubt, plus about 230 newly in doubt (SCAN2); in git, 11,726 lines added in `src/`, net +2,649 |
| test and tool lines | 105,942 | 232,891 |
| CI unit-tier timeout | 45 min | 175 min, for a warm run of about 12 min (9-10 min on 2026-10-20) |
| twin end-to-end jobs | 6 | 24 |
| SPECIFICATION.md | 514 KiB | 1,573 KiB, of which 562 KiB is the tunables register |
| `audit/` | | 14,052 files, 127 MiB at `497b3eda` (14,347 files, 131 MiB at the pushed head) |

**What is known and verified:**
- 17 confirmed gaps in the pre-audit code, most closable in 1-14 lines (CRC32 about 22; the lwIP listener close a
  toolchain patch) (`REPORT.md` 3).
- The keep list: the owner's decisions in their smallest form, the confirmed gaps and the rare-but-real cases that
  stay in scope (`SCAN2.md` 5).
- The removal closure: every dependent site of each root that goes, 2,129 rows from 173 roots
  (`scan2/G4_closure.tsv`, `G4b_closure.tsv`). It loses no confirmed gap and no rare-but-real case, provided the five
  named items stay.
- The decision review covers 2,784 decisions:
  - 82 would be answered differently;
  - 71 become obsolete with the cleanup;
  - 75 shrink to a smaller form;
  - 11 need a check.
  It also lists eight places where the build differs from the owner's words.
- Twelve hardware-round items (`REPORT.md` 7), four of which also decide a cleanup item (`DECREV.md` 9).

**What was planned and is not finished:**
- U35: 57 actions. On 2026-10-27 (Q35), 33 were done, 14 partly done and 10 open; later lanes advanced some of them.
- U36a and U36b, the docs pass: 96 actions.
- U37, the close: 17 actions.
- The closing ledger: 9 items.
- The open findings list (`audit/sweeps/open_findings.md`): 260 rows, 73 of them open or partly closed.

## 2. Plan 1: the repair of the existing state

### 2.1 The target and the method

- **Target per module.** The pre-audit file (`25caf528`), plus the owner's foundations of U1-U8 and U10's one name
  scheme and member order (OR24, OR96), plus the confirmed gaps' fixes, plus the owner's features and "ok" decisions in
  their smallest form, plus the rare-but-real cases on the keep list. Nothing else.
- **Method (recommended; decision 2).** Work from the current file, not from scratch. Where a whole mechanism goes,
  restore the pre-audit code of that region under today's names; never patch around the mechanism. Where an owner
  decision stays, shrink it to the smaller form the scans named (`REPORT.md` 5, `SCAN2.md` 5, DECREV's 75 FORM rows).
- **The change ledger.** One working file per batch, made at the batch's start from the scan rows of its files. Its
  rows:
  - the hunk against `25caf528`;
  - its class (R, K, H, X, C);
  - the decision: keep, shrink, remove or restore;
  - its basis: an owner row or review item, a gap id, or a scan row with its proof;
  - what it affects;
  - how a regression would show.
  This is the per-change table the owner's 2026-10-22 test asks for ("double check where it came from what it affects,
  what its intended function is ... no regressions, also no hidden ones").
- **The batch's gate.** Every hunk of the module's final diff against `25caf528` (rename-aware) maps to a ledger row
  marked keep or shrink. Anything unmapped is removed, or goes to the owner. No module's bytecode grows in a batch.
- **Test first (TDD; owner, 2026-10-28: "Option A, and keep TDD style").** For each ledger row, before its code:
  - a behaviour that changes (a revert to the pre-audit form, a shrink that alters an outcome, a form that follows the
    owner's words such as the LED queue at its deadline): its test is written or changed to the target behaviour first
    and seen red against the current code, then the code is changed until it is green;
  - a mechanism that goes with no outcome a caller can see: the tests that pin it are removed first, listed in the
    ledger, and the tests of the behaviour around it must stay green through the removal;
  - a kept behaviour with no test gets one, seen red on a planted break first.
  Then the whole suite runs. A failure on a kept behaviour is fixed in the code, never in the test.
- **Knowledge.** Every removed item gets one line in the knowledge list: what it was, why it went, and the commit
  holding the removed code. Decision 7 places it: a finding a future reader might rebuild gets one line at its
  module's Part in SPECIFICATION.md, platform facts go to Part F, unverified ones become owed-hardware rows, and
  trivial items stay only in the audit evidence.
- **In every batch**, for the batch's own files (DECREV 3.2-3.6):
  - test-only product code goes: `setup()` bools (dev's `UARTComm.setup()` keeps its bool, since its caller reads
    it), the I2C and SPI `deinit()` and `set_level()` bools (`UARTDriver.deinit()` keeps its, which its `init()` reads),
    `set_utc_valid(valid=)`, `_shutdown_task`;
  - a narrowing branch that can never run becomes a typing-side form;
  - the per-episode log flags give way to the central newest-entry rule (OR35.b, "Pure and simple.");
  - the whole-millisecond rule stays only for waits in loops.

### 2.2 R0, settling (no product code)

- **The lanes close.** The paused lanes' patches are complete in the evidence folder (checked 2026-10-28: no file in
  their worktrees is newer than its patch; CRr2d's holds no work; CMr1n, RF1 and CM4 never started). Their worktrees go,
  and so do those of every merged lane. The register's U35-U37 rows point to this plan.
- **The twin record's committed copy goes** (2.4): `tests_hardware/twin_record.json` and its staleness test
  `tests_scripts/test_twin_record.py` (about 1,600 lines), with their references in BACKLOG.md,
  HEAP_FRAGMENTATION_MEASUREMENTS.md, `digital_twin/README.md`, `digital_twin/run_device_script.py`, `pyproject.toml`,
  `tests_hardware/README.md` and Part N. The runner `scripts/record_twin_instrument_runs.py` stays: it is the committed
  runner of the owner's `twin-first-for-instruments` "ok" and the only path to the twin hardware run at 32768. R3 runs
  it once on the final tree at both stages and commits the record and its test again, exceptions listed. The record's
  exception reasons (about 36) become the first knowledge-list lines before the copy goes. `twin_board.py` and `--twin`
  stay.
- **DECREV 9's three checks** run before B1: the logger-side C-stack check at a near-exhausted C stack, a Unix-port run
  (item 3; this half decides B1's form, and its board half, REPORT 7's item 1, checks that form in round 1); the three
  BR2 fixes, read at the parent of `7008730e` against v1.29.0 (item 5); and the 2026-10-07 proposal behind the
  exception-handler guard (item 6). Each decides its batch item before the batch starts.
- **The baseline numbers** are recorded as the "before" column: per-module lines and bytecode against `25caf528`
  (compiled with `-s`, bare source names), the image size and free flash per device, test and tool lines, CI time per
  job.
- **The first full CI run** after R0 is the first run of the 24 twin jobs and the coverage job since 2026-10-21. Its
  result is part of R0's close: a red job is root-caused in R0, and its fix goes to the batch that owns the code.
- **The section 4 rules** go into the lead's checklist. A new findings list (4.2) starts empty; the knowledge list
  starts with the twin record's exception reasons. `audit/sweeps/open_findings.md` keeps its 73 open or partly closed
  rows, as input to R1's ledgers and as R5's OR5.a list.

### 2.3 The batches (R1: firmware and build chain)

| batch | files | the main content (from the scans) |
|---|---|---|
| B1 logging and catalog | `asy_print_log.py`, `buildgen/error_catalog.json`; the `report_if_fatal()` sites in every module | The C-stack reboot (the owner's "ok": "A C-stack overflow caught anywhere is recorded") in smallest form: the 123 calls in `src/` become one check at each logger entry point, ahead of the level gate and of any FRAM write, so that the 12 handlers reporting only through `pr.err()` are covered too, plus explicit calls at the 5 handlers that log nothing (`asy_base_classes.py:132`, `asy_captive_dns.py:190`, `asy_fram_driver.py:174`, `asy_system_service.py:474`, `asy_webserver_service.py:203`) and the Microdot hook; the generated boot entry's call, which nothing reads, goes in B8. Every `console()` line in `src/` that prints a caught exception (the UART driver 10, the UDP socket 7, which print `OSError`s too, RegionBuffer, the COBS codec, the logger's own arm and four more of its lines, and one each in the base classes, the system service, the DNS client and the webserver, three in the FRAM manager): their fate is clarification (d), widened to them, since the owner's "Option 1" (2026-10-20) set the unit tests' log level and no owner word covers these lines. E28 shrinks to one entry at setup for an unreadable store; its run flag, its heap-failure arm and its setup-write arm go, and a full FRAM stays silent (owner, 2026-09-16: "we do not even add errno/wrnno for the out of FRAM memory"). Catalog rows of removed codes go, with no placeholder, and the 6 existing placeholders go (decision 6); the no-reuse rule's text says it applies from the release on. Runs alone, because it touches every module. Clarification (d) first. |
| B2 core | `asy_base_classes.py`, `asy_system_service.py`, `asy_config_manager.py`, `math_helpers.py`, `asy_api_response.py`; the `/status` emitter lines and website rows of its keys (`buildgen/codegen.py:293`, `:297`; `definitions.py:635-649`) | Go: `ResetBits` in `/status` with its emitter line and website row (the decoded `ResetReason`, OR60, stays; the RUN-pin and HAD_POR hardware checks that read the raw bits are re-planned in R2 and round 1); `ConfigUnpersisted` in `/status` the same way (the flag stays for the shutdown flush); W69 with `absent_at_boot` and the logger's `restored` flag, a missing config file returning to the pre-audit persisted warning (one per boot) where the defaults are then written, while a command-only schema keeps its printed note (OR136.a (3)), and OR136.a's write-once kept; the uptime re-arm; the 1,200 ms escalation bound (the reset record is written before it). Changed: a chip-setup failure follows OR113's order, mild rung first (there was no ladder before the audit). Changed back: `rel_humidity()` clamps again, as legacy and the pre-audit code did (the owner's note kept the helpers and asked for the tests to be aligned; the no-clamp rule is agent text). Kept: E115, the one persisted trace of a supervisor crash (without it the reset reads as reason 2, a watchdog reset with no record); the mempause deadline (decision 3, item 2), its two cascade parts judged in the ledger; the recovery ladder (smaller form); the reset path; the system commands; the staged write; the newest-entry rule; the counter caps (OR103); the measured uptime (OR101). The wet bulb's cold-dry corner: clarification (h) first. |
| B3 storage | `asy_fram_driver.py`, `asy_fram_manager.py`, `asy_crc_checks.py`; `erase_ready()`'s caller in `asy_system_service.py` | Go: the lost-FRAM chain (decision 3, item 1), with `erase_ready()`'s shrink and its caller; the SPI "no bus" consumers and E52 in `asy_fram_driver.py` (B4's contract, this batch's file); the chunk read's `MemoryError` catch and the two rows of the same kind beside it (A-M9, A-M10, A-M11, judged in the ledger). Kept: the setup's identification retries with W29 (decision 3, item 4); the watch task's escalation for a declared FRAM that never sets up (OR89); the per-owner CRC seed, which is the layout-shift fix (owner, 2026-10-28); the blank chunk; the unreadable store; the CRC32 in two 16-bit words (a confirmed gap, as landed). Clarification (e) first. |
| B4 buses and sensors | `asy_i2c_driver.py`, `asy_spi_driver.py`, the SCD30, SGP40 (with `voc_algorithm.py`), BMP3XX and ISL29125 drivers | Go: the I2C "no bus" contract at every consumer, and the SPI driver's side of it, whose consumers in the FRAM driver go in B3 (rp2's constructors cannot fail with their stored arguments, `machine_i2c.c:61-118`, `machine_spi.c:138-217` at v1.29.0); the BMP3XX power-on detector with W71, its conversion wait and scratch view back to the STATUS poll; E27 at the BMP3XX site, a plain read failure there (E27 stays for the SCD30 range gate, DECREV 3.1); W73; the ISL shadow compare back to after a failed write, W75 back to the pre-audit console line; the SGP40's sample-age check and `None` branch, its restart back to the restore, its own "no backup" warning back; the VOC constants back to the per-sample port. Shrunk: the I2C clear as one clock-out routine, the short-ACK path in about 4 lines. Kept: I2C-6/7, the ISL settle horizon, the SGP40 restore cycle, a wedged bus at boot, a chip failing in operation. VOC-3's restore validation is judged in the ledger. |
| B5 network | `asy_wifi_service.py` (form only), `asy_ntp_client.py`, `asy_dns_client.py`, `asy_captive_dns.py`, `asy_udp_socket.py`, `asy_webserver_service.py` | Go: the web server's start retries and W62 (one start; asyncio sets `SO_REUSEADDR` and rp2's lwIP builds with `SO_REUSE 1`, so a restart rebinds at once); WS-2's head refusals, the HTTP version refusal among them, except the `Content-Length` check, and WS-9's quiet print with its merge list (decision 3, item 3); W16; the captive DNS re-raise; the NTP 44-47-byte refusal; the NTP cadence chain (NTP-12, NTP-13, NTP-15); the resolver's passed-in logger and `(address, cause)` widening (a diagnostic beyond need; one E67 as before), its console line for a caught `MemoryError` (`asy_dns_client.py:154`) joining clarification (d)'s list; the stored NTPHost/DNSFallback re-check. Kept: `TickSeconds` with its owner-decided users (SysUptime, LastSyncAge, WifiUptime, the LED pause); the Wi-Fi behaviour as decided (form only); the zero NTP timestamp; the 512 B receive with one yield per datagram; the listener close; the head bounds; a trace per dropped connection; W12. |
| B6 UART | `asy_uart_driver.py`, `asy_uart_comm.py`, `asy_uart_link_driver.py`, `asy_framing_codecs.py`; `PieceBuffer` in `asy_base_classes.py` | Go: the zero-length guard. Kept: `PieceBuffer.trim()`, which `uart_get()`, the SET receive and `readline()` call; `PieceBuffer.read_at()` with the responder's piece reply and the echo's piece answer (without them the echo copies the peer's whole train, 12,192 bytes on dev, per GET: the scans' one measured row, and OR143 bounds contiguous allocations); the construction refusals, E91 with its build mirror and E92 (no TOML reaches it: generated code wires no framing), the pre-audit pattern of a standalone module that refuses its own bad parameters (the ledger may shrink their form); the DMA ring; the hazard mode; the link's `initialized`. The codec's decode-size change and its removed counter are judged in the ledger, the codec being a real feature of the module. The wire format stays untouched, and every change gets its changelog entry. Clarification (c) first. |
| B7 LED | `asy_neopixel_driver.py`, `asy_notification_service.py`; the `State` field's buildgen, catalog and website sites | Not a rewrite: the module's audit diff is mostly names, typing and comments, with five behavioural rows. The overlay rewritten every 300 s (NP-5, 5 lines) goes back to the pre-audit wait, which also removes the lost shutdown cancel. The entry sanitiser (NP-3, 11 lines) goes back to the pre-audit clamp, per channel with the 0.1 s floor; its 60 s cap and its move to the entry go. NP-4's defined end state is settled in the ledger, since the two scans differ on it. The internal request queues at its deadline, as the approved text says, and W67 goes (DECREV 4.4). The notification's sample-age check and its `State` field go, with the field's generated status key (`buildgen/codegen.py:307`), its website row (`definitions.py:700-702`), its `NotifyState` code table, the mock data and the website test that names it, all in this batch. Kept: the refusal of an external command while a signal runs (NP-1), the bounded internal wait (NP-2), the REST refusal, the overnight window (OR69), the measured LED pause (OR104). |
| B8 build chain and generated code | `buildgen/`, the generated modules, `devices/*.toml`, `js/` and `html/` frozen into the image, the website stager in `scripts/` | Go: the build checks that no device TOML can trip (about 260 lines; the twin-wiring typing and the compile check of the generated text are judged on their own), except a rule whose violation would make a boot refuse or boot-loop: of the four I2C timeout rules, `bus.i2c-timeout-range` and `bus.i2c-timeout-max` stay as one 1-200,000 us range (rp2 stores the timeout as `uint32_t`, `machine_i2c.c:47`), the boot-clear budget and the loop-hold rule go, and `smallest_hard_consumer()` stays for the twin, flash, bench and timing tests that read it; the UART ranges stay as the build mirror of B6's kept refusals. The website lines with no recorded agreement (the items the owner approved stay; `PICTURE.md` 5), among them the page build-date stamp, with its stager half in `scripts/_stage_website.py`, `build_firmware.py` and `build_website.sh`. The device TOMLs follow their drivers (the UART keys follow B6, the `@tunable` tags R2's Part N scope). Kept: the generated boot entry's confirmed gaps (the emergency exception buffer, the loop-end labels); the read triggers' bus-spread order, OR47's "it's always only about sensors with bus access" (it equals the construction order on today's six devices). |

The table names each batch's main items; the ledger judges every hunk, unnamed ones included. Outside R1: `ext/` stays
as re-vendored (Microdot v2.7.0, byte-identical upstream; OR129.a, OR131.a); `src/LICENSE-captive_dns` (path names
and the holder line, U34) is R4's.

**Order.** B1 runs alone, then B2. B3-B7 run at most two at a time, on disjoint `src/` files. Three files are shared:
`buildgen/error_catalog.json`, the generated status emitter (`buildgen/codegen.py`) and its website rows
(`definitions.py`). `tests_scripts/test_error_catalog.py` makes a code's row go with its last site, and
`test_buildgen_definitions.py` makes a status row go with its key, so each batch removes its own rows and keys there,
and the lead merges those hunks of two parallel batches. B8 runs last for the rest of buildgen, because buildgen reads
the drivers' tags.

**The places where the build differs from the owner's words** (DECREV 4) are repaired where their code lives:
- the VOC "settled" wording in B4: the catalog's VOCState row and the SGP40 `@web` description, worded so that the
  decision-vocabulary check, whose allow-list only shrinks, passes;
- the LED queue in B7;
- E28 in B1;
- the clamp in B2;
- the heap-floor row in R2;
- the WoZi wording and the seven misattributed texts in R4.

**R1 is done when:**
- every module's diff against `25caf528` is fully mapped;
- every removed item is on the knowledge list;
- the full unit tier passes at both GC stages, the twin CI passes on all six devices, lint and typecheck are clean,
  and CI is green;
- the image size and free flash are measured per device and reported.

### 2.4 Tests, tooling, CI and the register (R2)

- **Retired first, in R0:** the twin record's committed copy and its staleness test (2.2, about 1,600 lines; the
  runner, `twin_board.py` and `--twin` stay). The copy is the only red in CI; with it gone the whole CI runs again, and
  the first run after R0 shows whether every later push starts from green (2.2).
- **Each test and tool file is classified once** (`tests/`, `tests_scripts/`, `tests_js/`, `tests_hardware/`,
  `digital_twin/`, `scripts/`, `toolchain/`, `mockdata/` and the CI files). The classes:
  - it pins a product property: kept;
  - it is a tool test covered by an owner row or an owner word in the rulings file (OR23.a's build chain,
    `setup_toolchain.py` and `micropython_overrides.py` included; OR15.a's summary block; the CI apt mirror check and
    cache, 2026-10-27; the repo scanner's own tests, which test the reader the owner's comment-cap gate runs on): kept,
    slimmed where it repeats itself;
  - it is audit machinery born in the audit (the bite self-tests of the tests, which OR21.a (2) did not adopt):
    removed;
  - the eight files that pin SPECIFICATION.md tables (about 1,700 lines) are classified one by one by what they check:
    those that check a product property through the table (lock order, run-phase allocation, task inventory, timing
    bounds) or carry an owner row (OR30.a (2)'s tunables check, the owner-signed A.11, OR23.a's key table, OR45's
    levels) fall under the first two classes, and only their restatement of the table is slimmed;
  - it is harness: kept, unless a lighter form keeps the same property.
  The list goes to the owner at R2's checkpoint before anything is removed.
  The owner rules stay in full: the comment cap gate, the gc-site checker, the memory-gate agreement, the persistence
  marker completeness and the four-tier bus hazard files. The two decision-records checks (`test_citations.py`,
  `test_decision_vocabulary.py`, the owner's prevention rule 5, OR68 "4. yes") stay until clarification (i), with
  their allow-lists only shrinking.
- **Tests of removed code** have already gone in R1, batch by batch.
- **Waits in tests.** The seven tests that sleep a fixed time and then assert wait for their condition instead (OR37.a
  (3)). The shared twin's 89 s wall-clock retirement gives way to its idle event. The launcher stop file and the rig
  override go (DECREV 3.2-3.3).
- **CI.** The timeouts are set from measured need with a stated margin (OR30.a's accuracy), keeping the owner's two
  retries for tests that hit a timeout (DECREV 7 condition 1). The twin matrix is sized to the devices and stages it
  must cover; the per-device rule stays ("Single device tests with different wiring should actually be avoided, so
  these tests should go for all devices."). The hang backstop stays as CLAUDE.md states it.
- **The tunables register** (SPECIFICATION.md Part N) returns to OR30.a's own scope:
  - included: CI and per-file timeouts and retries, the Unix-port heap flag, twin run and soak durations, the
    hardware-tier budgets, and the firmware and build values of the same kind;
  - not included: the rows for numbers inside test bodies (about 860 by the plan's count; R2's checkpoint list states
    the split from the hardware-tier budgets row by row before the cut);
  - the `@tunable` tags outside that scope go;
  - the values that stay are checked for accuracy.
  The heap-floor row loses "measurement owed" (the owner's `heap-floors-kept` "ok": "never to fit a reading").
- **R2 is done when:**
  - every file is classified and the agreed removals are made;
  - CI is green with the new timeouts;
  - Part N holds only OR30.a's scope, every value with its basis;
  - the numbers are reported (test lines, CI time per job, twin job count).

## 3. Plan 2: what remains from U35 to the end, revised

### 3.1 Retired, and why

- **The paused lanes** (LD+CM3, CRr2c, IN2, CRr2d, CMr1n, RF1, CM4) close without merging. They build group-B3 records
  and machinery on a tree that R1 changes; their patches stay in the evidence folder. Their owner rows (OR41.a, OR49.a,
  OR21.a, OR25.a) are met in R3 on the final tree. LD+CM3's patch also holds two L2 load tests that OR49.a (1) names
  (the full soft-callback queue, the DNS flood at the hotspot); R3's OR49.a takes them from the patch.
- **The closing ledger's items 1-7** go the same way. Item 8 (the NeoPixel) is batch B7. Item 9, the serial close, is
  replaced as follows:
  - the coverage re-run becomes R3's one coverage run;
  - the measurements go to R2's accuracy check and the phase numbers;
  - the twin record re-record becomes R3's one runner run on the final tree (2.2);
  - the twin CI on the integration head becomes R1's twin done-criterion and the first full CI run after R0;
  - D3r becomes R4;
  - REC2 becomes R5's terminal states;
  - W10 becomes each phase's close.
  The ledger's admission rules carry over into section 4.
- **U35-U37's 170 actions** are not executed as written. Their sites were read at old heads, and many serve
  mechanisms R1 removes. Each is mapped in the appendices:
  - done and kept;
  - carried as an owner row into a phase;
  - a checklist input for its target document;
  - dropped, with the reason.

### 3.2 What remains, by phase

**R3, the test campaign once, on the final tree.** The owner's rows stay as decided. Their form is decision 4. For each
row:
- **OR16.a:**
  - (1) the twin boots every device (exists);
  - (2) every test is collected, and every skip has a reason;
  - (3) one coverage run, with every unexecuted line classed as feature, guard or dead (the owner's dead-code ruling:
    "Always regard the modules as libraries");
  - (4) faults planted only where the owner scoped it ("Planting faults is a good measure for complex measurement
    tests ... but not required for the straightforward tests").
- **OR19.a.** Every test reviewed. A test keeps the verdict it already has in `review.md` only where neither it nor the
  code it targets changed in R1 or R2 (decision 4), matched by name and body, not line. Others are reviewed fresh.
- **OR21.a and OR29.a (4).** Each check-style test whose subject changed is triggered once. No new permanent control
  arms. The twin runner runs every device script and hardware test once at both GC stages on the final tree, and the
  record and its test are committed again with the exceptions listed (the owner's `twin-first-for-instruments`).
- **OR22.a and OR23.a.** The generated code and the build chain are checked once on the final tree, and a gap gets a
  test.
- **OR25.a.** The intent map is updated by subtraction, and a gap gets a test. The map stays a working file.
- **OR37.a and OR38.a.** One pass over the tests, scripts, runners, tools and `src/` modules changed since the audit
  start, for harmful constructs, races, leaked resources and hygiene.
- **OR39.a and OR40.a.** Speed and footprint are measured. Both GC stages run in the unit and twin tiers (this
  exists); the hardware tiers by OR40.a (3).
- **OR41.a.** The assembly and interaction matrices are reading aids: each cell carries a reason or names its existing
  test. A new test is written only for a real interaction with none.
- **OR49.a.** Each finite resource gets a test or a reason, and every new load test gets its report entry (OR49.a (3)).
- **OR26, the "no uncaught exceptions" pillar.** The raising-call map is redone only for the modules R1 changed. A
  defect counts only with a reproduction.
- **U35's 37 and 52.** The normal situations that accept a logged code (the owner's 2026-09-12 startup-jitter rule), and
  every recovery rung that stays, tested at every level that can reach it (OR113.a (2)).
- **The four-tier bus hazard rule and the wear-gate table**, for the final tree's bus-facing changes and the hardware
  tests' writes.
- **Round 1's preparation** (OR8.a, OR17.a, OR29.a):
  - the queue (BACKLOG.md's "Real-hardware work still owed", which replaced OR8.a's queue file) in order, with
    expected outcomes and the wear budget;
  - the hardware tests linted, typechecked and collection-checked;
  - the twin fidelity table;
  - the hardware knowledge, cross-checked against the datasheets.

**R3 is done when:** every group-B3 owner row (`audit/CONSOLIDATION.md` 2, with section 4's B3 additions OR20/OR36,
OR45, OR55 and OR77/OR79) has its outcome on the final tree (met and where, or one stated limit for the owner), and
round 1 is fully prepared.

**The first hardware round** (its own go-ahead):
- `REPORT.md` 7's items 1, 3, 4, 5, 7, 8 and 10, with the optional 12 (item 1, the C-stack peak, is the bench reading
  of the owner's `c-stack-reboot` "ok" and checks B1's logger-side form);
- item 11, the owner's owed rows (the DMA ring proof, reset reasons 21, 22 and 10+phase, the first unfed watchdog
  stretch, dev's receive-ring peak);
- the queue R3 prepares (OR8.a: the hardware phase "works through the queue"), the lone-BMP3xx general call among it;
- the actions of `audit/actions/C.md` that survive R1 (OR47.a's boot log and trigger stamps, OR60.a (4)'s reset codes
  0, 9, 10+p and 20, OR50.a (3)(b)'s bench packages, OR79.a's off-subnet DNS attempt);
- the review "ok"s that name the bench: the SGP40 chip identity and serial read, the SCD30 readiness limits;
- B2's RUN-pin and HAD_POR checks, re-planned;
- the FRAM log's W29 history, read before anything is flashed (decision 3, item 4: knowledge only).
What the session on the bare MicroPython image before R1 answers (owner, 2026-10-28) is not repeated. Items 2, 6 and 9
are not run: the owner's decisions of 2026-10-28 settled what they were to decide (the lost-FRAM chain goes and the
mempause deadline stays, without a measurement; NP-5 is reverted).
FRAM logs are read and saved first. A confirmed failure gets its minimal fix, on evidence. The twin is corrected until
it agrees.

**R4, the docs, written once from the final state** (the group-B4 owner rows):
- **OR27.a.** Facts, rules and agreements only, no history.
- **OR13 and OR14.** The scans already did most of the drift check.
- **OR15.a.** The README's task-first layout with a checked CLI reference.
- **OR44.a.** The principles Part and the one ordered checklist.
- **OR10 and OR10.b.** The new-module procedure, proven by fresh builds against two baselines, capped at three runs,
  then a report.
- **OR68.a.** Provenance, plus DECREV 4's WoZi wording and section 5's seven misattributed texts fixed.
- **OR51.a (4).** The quality bar and test standard in SPECIFICATION.md (Part D, D.12, Part E); session practice in
  CLAUDE.md's working agreements.
- **The knowledge list** placed as decision 7 says.
- **U36's 96 actions** are the checklist inputs for their documents. Each is kept if its subject survives R1 and R2.
  Its rule actions are proposals unless an owner row stands behind them.

**R5, the close of execution** (U37's substance):
- **OR9.a.** Re-verification passes until one ends all green, capped at three passes, then a report.
- **OR11.** Stray and temporary files go, with their links migrated.
- **OR5.a.** Every open finding and every BACKLOG item reaches one terminal state.
- **OR52.a (2).** The golden stored-config and REST fixtures, at the release point.
- **The release.** The version and the release note.
- **The final report**, with OR49.a (3)'s entries.
- **The build-environment list.** The chroot list covers every build-environment change since the legs were last run.
- **The D.15 order beyond `src/`** (A.U36.038; OR96: "2. a but not the unit tests themselves"; "Option d is fine",
  2026-10-27): the sweep and its all-scope check.
- **U37's 01 (2), 02, 04, 05 and 17.** The second dependency check (A.SDEP.25, OR129.a (1)), the allow-lists removed
  once empty, the knowledge base and the twin fidelity table made final, BACKLOG's owed-hardware list from phase C's
  inventory, and the owner-row trace.

**The last round:**
- OR40.a (3)'s two-image GC proof, as release proof;
- what round 1 left;
- OR17.a's further twin corrections.

**D, the close:**
- the Stull paper moves to the datasheets repository, after clarification (j);
- the do-not-reopen decisions are checked at their doc sites;
- the plan and `audit/` are deleted;
- one merge into `main`, tagged v2.0 as the release with the owner's agreement (OR11.a, OR52.a (4); the review's
  `release-version-2-0` and `release-defined-point`).

## 4. Plan 3: how it is carried out without drifting

### 4.1 The end is defined

- Every phase has a finite, numbered list, fixed at its start and shown to the owner, plus a done-criterion stated
  above.
- The plan ends at D. There is no phase after it, and no list grows except by the admission rule (4.2).
- A phase ends with a report and a stop. The next phase starts only with the owner's go-ahead.
- Inside a phase, batches run one after the other without waiting, except for a batch's clarification (section 7).
  Each batch ends with a short report of numbers and carries no question.
- **Caps on the loops.**
  - OR9.a's passes and OR10.b's runs stop after three, with a report.
  - An item gets at most one follow-up lane.
  - A done-criterion that proves unreachable is handed back once, with the measured limit. The owner then decides.

### 4.2 Admission of new work (carried over from the closing ledger)

A new item joins a list only if it is one of these:
- (a) a defect in the firmware or the build chain, with evidence: an owner decision, an observed failure, or a
  reproduction against the real code;
- (b) a defect that makes one of the list's own deliverables wrong (a check that cannot fail, a record stating
  something false, a red test).

Each addition is named in the next report, with its reason. Everything else is routed to the findings list with its
evidence, for the owner, never into the work: improvements, stronger forms of a correct check, coverage beyond the
done-criteria, observations.

### 4.3 Numbers and budgets

- **After every batch**, five lines:
  - `src/` lines and bytecode against the pre-audit state;
  - image size and free flash per device;
  - test and tool lines;
  - CI time;
  - the decisions taken on the owner's behalf in that batch, each with its reason.
- **These decisions are reviewed at each phase end**, not at the very end.
- **A budget per phase** (decision 5): wall-clock hours and lane runs. At 80 % of either, the work stops and reports
  where it stands and what is left. Tokens cannot be metered from inside the session; the lane count and hours are
  the proxy, and the owner sees the real usage on their side.

### 4.4 Rules for the work itself (DRIFT 6, made binding)

1. Product code changes only for an owner decision, an observed failure, or a reproduction against the real code. A
   hypothesis becomes knowledge, a hardware-round item, or at most one cheap test; never code.
2. "Conservative" means the smallest change. For solid code, that is often no change.
   Every change to the firmware or the build chain is made test first (owner, 2026-10-28), as 2.1 describes.
3. Code that exists because of another addition questions its root first. A chain two deep goes to the owner.
4. Rigor is tiered:
   - firmware and build chain: deep;
   - tests: good quality, no campaigns;
   - the audit's own machinery: minimal and throwaway. No tests of audit tools, no records keyed on line numbers, no
     raw logs committed.
5. Inventories and matrices are reading aids, never work lists.
6. No new hardcoded delay check of the NP-5 kind, in the product or in tests; a new wait uses an event, an order, or
   the driven clock. The owner-decided deadlines (the mempause deadline, the LED request's deadline, the NTP stale
   interval) and the hang backstop stay.
7. Agent-written requirements are proposals. Only the owner's words bind. A planning-phase ".a" row the owner
   answered "yes" to is the owner's.
8. Every owner word goes into the rulings file, verbatim, as it is given.
9. Unforeseen decisions take the smallest change. Each is recorded and shown in the next batch report.
10. **The five checks, before anything is written or shown** (owner, 2026-10-28: "Revise our current plans, so they do
    not contain such glitches anymore."). A ledger row, a finding, a recommendation or an answer to the owner carries
    its evidence, and changes before it is used when the evidence does not hold:
    - where it is: the file and line now and at `25caf528`;
    - what governs it: the pre-audit specification and the owner's rows and rulings, quoted;
    - who uses it: a search over firmware, website, build chain, device files, tests, twin and docs;
    - what the platform does: the pinned MicroPython, Microdot or lwIP source, never a report or memory;
    - how big it is: counted from git, never described.
11. **Falsification as the final verification** (owner, 2026-10-28: "The claim falsification check agent scan seems
    reasonable, too. Add this as a final verification and adapt the run counts accordingly."). The plan check ends
    with independent agents that get the plan's claims and the repository, without the lead's evidence or reasoning,
    and try to refute each claim. The lead verifies every refutation at the source before it changes the plan.

### 4.5 Lanes and review

- A lane's brief lists items from the phase list only. A finding outside it goes to the findings list, never to a new
  lane.
- At most two lanes run at a time, on disjoint `src/` files; the three shared files as in 2.3. The lead does small
  items directly.
- The lead reads every changed line before a merge. A lane fixes its own reds before it hands back.
- Every push follows the local gate (lint, typecheck, the unit tier and dev's twin suite at both GC stages; the other
  devices' twins run in CI). CI is followed through the PR's notifications; nothing is pushed while CI runs.
- Records are few and fixed in advance:
  - this plan;
  - one state ledger per phase;
  - the batch change ledgers (working files);
  - the findings list;
  - the rulings file.
  The evidence folder gets summaries, not logs.

### 4.6 What stays strict

- Every owner decision and every "ok" on the review page, in its smallest form; the Wi-Fi behaviour as decided; the
  FRAM seed.
- Every confirmed gap and every rare-but-real case on the keep list.
- The four memory gates, with zero `MemoryError` or "memory allocation failed" at both GC stages.
- The hang backstop, strict mypy, ruff's full rule set, and the comment cap.
- The four-tier bus hazard rule for bus-facing changes, and the wear rules on board and host.
- The UART module's wire format, untouched, with a changelog entry for any change.
- CI green on every pushed head.
- No failure is called a flake without a root cause.

## 5. Effort (estimates, for the budgets in decision 5; corrected 2026-10-28 on the owner's question)

What drives the time is machine time, not analysis: the removal list is already known (the closure). Measured inputs:
- the full local unit tier takes about 10-11 minutes per GC stage on a quiet host (2026-10-26 17:31-17:53), and 17-35
  minutes under load (2026-10-27, four lead gates, all with failures);
- dev's local twin suite takes about 21-22 minutes per GC stage (2026-10-26);
- one CI run takes about 16 minutes with the twin and coverage jobs skipped (run 40678957431), and took 27 minutes with
  them (run 39665515089, 2026-10-21).

Per R1 batch (judgement):
- the change ledger from the scan rows: about 0.5 h;
- the edits: 0.5-1 h;
- test first: each row's red run is one test file on the Unix port, about 0.5 h per batch in all;
- the full gate at both GC stages, twice (once more after the fixes): 1-1.4 h;
- dev's twin suite at both GC stages, once: about 0.7 h;
- the line-by-line review: 0.3-0.5 h;
- the push and CI: 0.5 h.
That is about 4.0-5.1 h per batch. Eight batches, five of them two at a time, take six slots.

| phase | lane runs (cap) | wall-clock hours (estimate) |
|---|---|---|
| P the plan check, before R0 (2026-10-28) | 5 (its falsification agents) | 12-22 at its go-ahead; about 1.7 used |
| R0 settling | 0 | 2-2.5 |
| R1 firmware and build chain, 8 batches, test first | 12 (8 + 4 follow-ups) | 24-31 |
| R2 tests, tooling, CI, register | 6 | 5-8 |
| R3 test campaign once, round 1 preparation (decision 4's lean form) | 8 | 9-15 |
| round 1 | (the owner's bench time) | 2-3 sessions |
| R4 docs (with up to 3 OR10.b runs) | 8 | 8-12 |
| R5 close of execution | 6 | 6-10 |
| last round and D | 2 | 2-4 plus the owner's session |
| **total before round 1** | **31** | **about 42-58** |
| **total after round 1** | **16** | **16-26** |

P and R0 were added or corrected by the plan check: P's own runs, and R0's twin-record edits, Unix-port run and twelve
baseline builds (a firmware build takes about a minute on a built toolchain). These are estimates, not measurements. The
first version (40-60 hours before round 1) carried unstated padding, partly anchored on the U35 redo's pace, which was
the runaway pace. The falsification added the twin suite and the full CI time to each batch, R0's first full CI run,
R3's wider OR37.a/OR38.a pass and its twin runner run, and R5's D.15 sweep and U37 items. The softest numbers are the
number of fix rounds per batch, R3 (the twin runner's run time is not measured) and R5's D.15 sweep.

## 6. Decisions needed before R0 starts (one at a time)

1. **The plan's shape.**
   - Facts: the old plans carry hypothetical-based actions and the old way of working; the owner's 2026-10-23 words
     put the firmware first ("The goal for the first hardware round after U35 was to have the firmware final. That's
     still in place."), and on 2026-10-26: "there is no need to restrict on "firmware first" alone".
   - Proposal: retire the old plans as in 3.1. Run R0, R1, R2, R3, round 1, R4, R5, the last round and D, in that
     order.
   - The alternative: docs before round 1. The docs would then be written twice, once more after the round's
     results.
   - Recommendation: the order as proposed.
   - **Decided (owner, 2026-10-28): "then take option a".** The order as proposed.
2. **The repair method.**
   - (a) Work from the current files, restoring pre-audit regions where a mechanism goes, with the hunk-ledger gate.
   - (b) Rebuild each module from the pre-audit file and port the kept items into it. This is cleaner on paper. But
     U10's name scheme and the U1-U8 foundations touch every file, so each port re-does work that is already right.
   - Recommendation: (a). It reaches the same end state, and the gate makes it provable.
   - **Decided (owner, 2026-10-28): "Option A, and keep TDD style".** Option (a), every change test first (2.1).
3. **The suspicious hypotheticals** (DECREV 9's items 1, 2, 4, 7: the FRAM line level with the chip absent, eight
   queued soft callbacks, a USB host that never reads, W29 in dev's FRAM log).
   - **Item 1 settled by the owner's fact (2026-10-28):** "high impedance and floating, the pull resistor is on the
     chip. the pin picks up any stray noise." No fixed pattern can tell a lost chip, so the lost-FRAM chain goes whole
     in B3, the 4-line status-bit fallback included. Noise is already covered before the audit: the setup's RDID check
     does not match it, and every chunk's CRC turns it into invalid data. No measurement is needed.
   - **Item 2 decided (owner, 2026-10-28: "okay, as recommended"):** the mempause's end stays the deadline on the 1 s
     status pass. The pre-audit one-shot broke the pre-audit SPEC's own rule (F.1, C.9: "every timer that must fire uses
     `PERIODIC`"), and the drop it risks is confirmed in the pinned source. Its two cascade parts (the shutdown refusal,
     the clearing order) are judged in B2's ledger. No measurement.
   - **Item 3 decided (owner, 2026-10-28: "good, accepted"):** settled from the pinned source, no measurement. The USB
     console waits only with an open, non-reading host, up to 500 ms per write (`mp_usbd_cdc.c:102-145`); field units
     have none. WS-2 goes except the `Content-Length` check (ASCII digits, once, 2-3 lines on WS-1's refusal path): a
     negative length otherwise ends in a caught MemoryError inside Microdot (`ext/microdot.py:411-426`,
     `py/stream.c:122-128`). WS-9's quiet print and merge list go; WS-1's head limits and the 3-4 line C-stack hook
     stay.
   - **Item 4 decided (owner, 2026-10-28: "keep it"):** the setup's up-to-three identification reads with W29 stay,
     OR113.a's first rung ("retry the transaction"); without it a single disturbed read would skip the ladder's mild
     step. Round 1's FRAM log read records whether W29 ever appeared, as knowledge only.
   - **Decision 3 is closed.**
4. **Where R3's effort goes.** The owner asked for this distinction (06:37: "So we will have to find a distinction
   where to put the effort.").
   - Proposal: each B3 row is met on the final tree, in the form listed in 3.2. The review verdicts of unchanged
     tests carry over; faults are planted only where the owner scoped it; matrices and maps are reading aids and
     working files; nothing new is permanent.
   - This keeps every row's bar and spends the effort only where the code or tests changed.
   - The alternative is the rows' full original form on the final tree, about 2-3 times R3's estimate.
   - Recommendation: the proposal.
   - **Decided (owner, 2026-10-28): "Yes, take A".** The lean form. A review verdict or plant result carries over only
     where neither the test nor the code it targets changed in R1 or R2.
5. **The budgets.** The caps and hours in section 5, with the stop at 80 %. Or the owner's own figures.
   Recommendation: the owner sets them; section 5 is the proposal.
   - **Decided (owner, 2026-10-28): "A".** Each budget at the top of its estimate: R0 1 h; R1 25 h, 12 runs; R2 8 h,
     6 runs; R3 10 h, 8 runs; R4 12 h, 8 runs; R5 5 h, 4 runs; the last round and D 4 h, 2 runs. A stop with a report
     at 80 % of either; hours count from a phase's go-ahead, without time waiting for the owner.
   - Applied by the same rule after the plan check and its falsification: R0 2.5 h; R1 31 h; R3 15 h; R5 10 h and 6
     runs; the plan check 22 h (its estimate at the go-ahead was 12-22 h; about 1.7 h used) and 5 runs, the runs added
     for its falsification agents (owner, 2026-10-28: "adapt the run counts accordingly").
6. **Retired error numbers.**
   - Facts: the never-reuse rule is agent text, and it would leave about 20 tombstone rows. The tree states no reason;
     the scan gives FRAM history across reflashes (DECREV.md), which the owner does not require (OR47.a: "no
     requirement for the fram to stay consistent through firmware re-flashes"). The refactored firmware has only ever
     run on the dev bench.
   - (a) Drop the rule: a removed code's row goes, and its number may be reused.
   - (b) Keep the tombstones.
   - Recommendation: (a), the smaller change, resting on OR47.a.
   - **Decided (owner, 2026-10-28): "third option accepted".** The owner pointed out that the device's own page
     explains each logged code by its number (`buildgen/definitions.py:296-306`, `js/templates.js:222-237`, :399-401),
     so a reused number would explain an entry from an older firmware wrongly. No placeholder rows for numbers retired
     before the release: the 6 existing ones go, and the codes R1 removes leave none. From the release on, a removed
     code keeps its number unused; the rule and its catalog check stay, applied from then.
7. **Where the obsolete findings live** (PICTURE 8: "worth to know about in general"). Options as put to the owner on
   2026-10-28, replacing the first draft's three:
   - (A) One appendix in SPECIFICATION.md, one line per removed finding with its commit: complete, but a list of
     removed code (OR27.a's "this used to be ..."), about 150-250 lines.
   - (B) The audit evidence only: no doc lines; reachable through the final merge commit (PQ2) for whoever digs.
   - (C) Folded into the facts, as OR27.a has it: a finding a future reader might otherwise rebuild becomes one line at
     its module's Part (the condition, why the code does not handle it, what covers it); platform facts go to Part F;
     unverified ones become owed-hardware rows; trivial items stay only in the evidence. A few dozen lines.
   - Recommendation: (C).
   - **Decided (owner, 2026-10-28): "C".**

## 7. Clarifications asked later, at the start of the batch they affect

Each sets an owner statement against another owner statement or a code fact (DECREV 6; (i) and (j) found by the plan
check). Each is asked once, in prose, when its batch or checkpoint begins, and never before:
- **(d)** the console at DebugLevel 0: OR35.a against Q6's "Option a", and with it every `console()` line in `src/`
  that prints a caught exception, weighed against the owner's "no evidence to a bug ... is silently lost" and the
  memory gates, which see a caught MemoryError only through a printed line (batch B1);
- **(h)** whether the owner's "Adapt the humidity to the verified range" (said of the Magnus pair) extends to the wet
  bulb's cold-dry corner, an agent-added exclusion (batch B2; the `rel_humidity()` clamp is not part of it);
- **(e)** FRAM's own log for one invalid block: OR56 against "stay as is" (batch B3);
- **(c)** a lost UART frame: the `uart-flash-erase-overrun` "change" note against the accepted flash-stall
  degradation (batch B6);
- **(i)** the two decision-records checks: the owner's prevention rule 5 (OR68 "4. yes", CLAUDE.md's decision records)
  against "The audit verification machinery is just a temporary tool" (2026-10-28) (R2's checkpoint);
- **(j)** the Stull paper's move: write access to the `datasheets` repository (the owner's grant names fetching only)
  and the paper's redistribution terms (OR52.a (7)) (at D).

Not asked:
- (b) is settled by decision 4; (a), OR30.a's scope of the tunables register, by R2's Part N scope, shown at R2's
  checkpoint.
- (f) is Wi-Fi, which the owner has decided ("I decided everything already.").
- (g), the hazard clause added to A.11's row 2 after the owner signed it off, is a records fix: the signed-off table
  is restored in R4, and since B6 keeps the hazard mode, row 2 keeps naming the `UartHazards` dispatch field (A.11's
  own rule, `test_a11_names_every_dispatch_field`), marked as agent text.

## Appendix A: U35 and the closing ledger, item by item

U35's states are from Q35 (2026-10-27). Later lanes advanced 03, 07, 08, 22, 36, 37, 41 and 52 without finishing them.

| action | state | where it goes |
|---|---|---|
| 01 B3 working files | done | retired with the records; R3 keeps working files only where it needs them |
| 02 every level at both stages against the baseline | open | replaced by each batch's full runs and the phase numbers |
| 03 review every test | partly (8,482 rows) | R3, OR19.a: verdicts carry over where neither the test nor its target changed; the rest reviewed |
| 04 faults planted per module | partly (153 rows, 1 open) | R3, OR16.a (4), in the owner's planting scope; results carry over for unchanged code |
| 05 check-style tests triggered | done | R3, OR21.a: re-triggered only where the subject changed |
| 06 J.7's latency blindness | done | stays; R2 reviews it with the UART tests |
| 07 intent per layer | partly | R3, OR25.a, by subtraction |
| 08 assembly and interaction matrices | open | R3, OR41.a, as reading aids |
| 09 the owner's two twin recombinations | partly | R3 (the owner's row) |
| 10 one driven clock for L1 | done | R2 reviews it as harness |
| 11, 16 BMP3xx interleaving, SGP40 window | done | stay if R1 keeps their subject |
| 12, 14 NTP readiness, wall-clock waits | done | stay: they replaced timed waits |
| 13 NeoPixel and notification on driven time | done | re-checked after B7's revert |
| 15 NTP loopback cap | partly | R2 |
| 17-20 the small test fixes | done | stay |
| 21 lone-BMP3xx general call on the flash tier | done | its silicon run is in round 1, through the queue R3 prepares |
| 22 N.27 and the ladder of levels | open | R2 (Part N); the levels record retires |
| 23 every tier's cost | open | replaced by the phase numbers |
| 24 the heavy-file list | partly | R2 |
| 25-27 sampler, soak join, Run 11 calibration | done | stay (Run 11: owner Q1 "This is okay, go ahead.") |
| 28, 29 load on every finite resource, zero-think readers | partly | R3, OR49.a |
| 30, 31 planted failures stop the feed | done | stay |
| 32 the real 2**30 wrap | partly (the run merged, green) | its result is recorded as knowledge; no more work |
| 33-35 forty days, dropped wake-ups, counter caps | done | stay (the caps: OR103, "No unbounded counters anywhere") |
| 36 raising-call map | open (BR1-BR4 advanced) | R3, OR26, for the modules R1 changed, reproduction required |
| 37 normal situations that accept a logged code | partly | R3 |
| 38-40 twin boot log, smoke log, torn write | done | stay |
| 41 E.5.1 verdicts | partly | R3's one coverage run (OR16.a (3)) |
| 42-47, 55 removals of unreachable guards | done (45 reversed: `logger=` kept under the owner's library rule) | consistent with R1; the batches of their files re-check them (B2, B3, B6, B8) |
| 48 the cancel-at-each-await sweep | done | R2 reviews it as harness |
| 49 every instrument through the twin runner | partly | the record's committed copy retires in R0 and the runner stays; R3 runs it once on the final tree (OR21.a, OR29.a (4)) |
| 50 the four-tier rule for every bus change | open | R3, for the final tree's bus-facing changes |
| 51 the wear gate of every hardware test | open | R3: one table, and a marker fix if one is wrong |
| 52 every recovery rung at every level | open (CO1-CO5 advanced) | R3, for the rungs that stay (the owner's ladder) |
| 53 the owner's latest test demands | partly | R3: the group-B3 rows are its checklist |
| 54 B3's hardware items | partly | R3: round 1's preparation |
| 56 test-tier tunables owed | open | R2: Part N to OR30.a's scope; its values measured |
| 57 the BACKLOG chroot list | open | R5: one paragraph for every build-environment change since the legs |

| closing ledger item | where it goes |
|---|---|
| 1 LD+CM3, load records and the assembly matrix | retired; OR49.a and OR41.a (1) in R3 |
| 2 CRr2c, the flash-tier log check through the twin | retired; R3's twin runner run (OR21.a, OR29.a (4)) |
| 3 IN2, the reverse map and the lwIP review rows | retired; OR25.a in R3 |
| 4 CRr2d, the bench tier's sets through the dev twin | retired, as item 2 |
| 5 CMr1n, the drift arms | retired; the drift check is reviewed in R2 as twin machinery |
| 6 RF1, the red-flag tool's credit | retired; the tool is audit machinery, usable in R3 as a reading aid |
| 7 CM4, the interaction matrix | retired; OR41.a (2) in R3 |
| 8 the NeoPixel's lost cancel | batch B7: the revert removes it |
| 9 the serial close | replaced, as in 3.1 |

Phase C's action list (`audit/actions/C.md`, A.C.01-A.C.19): each action that survives R1 goes to round 1's list (3.2);
the rest is dropped at R3's preparation, each with its reason.

## Appendix B: U36 and U37, by group

- **U36a and U36b, 96 actions.** 81 are doc actions, 14 rule actions and 1 a code action, all written against heads
  `b10c88a` and `82c430e`. At R4's start each is filtered against the final tree:
  - its subject is gone: dropped;
  - its subject stays: a checklist input for its document.
  The substance they carry is the owner's rows OR27.a, OR13, OR14, OR15.a, OR44.a, OR10.b, OR51.a (4) and OR68.a,
  which R4 meets directly. The rule actions add CLAUDE.md or SPECIFICATION.md rules; each is shown to the owner at R4's
  checkpoint, and only those with an owner row behind them are adopted. The one code action, A.U36.038, goes to R5.
- **U37, 17 actions, by where they go:**
  - **R5:** the fixed close order (01), the allow-lists removed once empty (02), stray files (03), the knowledge base
    and the twin fidelity (04), the owed-hardware list (05), BACKLOG's four kinds of content (06), the re-verification
    (07, capped), every entry terminal (09), the golden fixtures (10), the version (11), the release note (12), the
    end-of-execution report (13) and the owner-row trace (17).
  - **Moved to each phase end:** the owner's review of decisions taken on the owner's behalf (14).
  - **Shown in R4 as proposals:** the close-out agreements for CLAUDE.md (08).
  - **D:** the plan and `audit/` deleted (15); one merge and the tag (16).

## Appendix C: sources

- `PROJECT_AUDIT_PLAN.md` at `fc509999`:
  - 3.2, the rows OR5, OR8-OR11, OR13-OR17, OR19, OR21-OR23, OR25, OR27, OR29, OR30, OR37-OR41, OR44, OR49, OR51,
    OR52 and OR68 with their ".a" answers;
  - 4.1, the units.
- `audit/CONSOLIDATION.md` 2; `audit/REGISTER.md`, the unit table; `audit/actions/U35.md`, `U36a.md`, `U36b.md`,
  `U37.md`.
- The evidence folder:
  - `scan/REPORT.md` 1-11, `scan/E.md`;
  - `scan/scan2/SCAN2.md` 1, 4, 5 and 9, with the closure tables;
  - `scan/decrev/DECREV.md` 4-9;
  - `scan/DRIFT.md` 5-6;
  - `scan/PICTURE.md` 8;
  - `redo/REDO.md`, `redo/closing_ledger.md`;
  - `redo/recovered/owner_rulings_after_LN118.md`, for the owner's 2026-10-23 and 2026-10-28 words.
- Q35's completion inventory (`redo/handbacks_redo/Q35.md`), for U35's states.
