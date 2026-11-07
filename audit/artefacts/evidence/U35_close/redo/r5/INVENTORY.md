# R5 closure inventory (agent r5I_, read-only, tree `S/wt-u35int` at `3b9d7218`, 2026-11-05)

States: **F** fixed · **R** resolved or stale, removed · **D** decided, documented at the site named · **O** out of scope
by owner, documented as a limitation (an owner-deferred goal stays in BACKLOG with its reason) · **N** needs the owner.
W = waits on round 1's results (Y / N / part). Round 1 is under way (precheck 2026-11-05, `r3/bench_r1c_msg.txt`); what
it leaves goes to the last round (PLAN.md R5/last round). SPECIFICATION.md is cited by Part, plus a line only for orientation.

## Counts

| table | rows | F | R | D | O | N |
|---|---|---|---|---|---|---|
| OR5.a: findings (r5I_F) | 9 | 3 | 4 | 2 | 0 | 0 |
| OR5.a: BACKLOG (r5I_B) | 67 | 11 | 11 | 33 | 7 | 5 |
| OR5.a: markers and found on the way (r5I_X) | 3 | 2 | 0 | 1 | 0 | 0 |
| OR5.a: U37 items (r5I_U) | 6 | 5 | 0 | 0 | 0 | 1 |
| **OR5.a total** | **85** | **21** | **15** | **36** | **7** | **6** |
| OR11 stray files (r5I_S): final cleanup 4, hardware follow-up's close 2, stays 6 | 12 | | | | | |

Waiting on round 1: 40 rows (37 Y; 3 in part: B25, B27, U04); r5I_F3 waits for the real SGP40 raw walk.
**Needs the owner (6):** r5I_B02 (tier-scan "future work"), r5I_B18 (UART drain bound with no babbling peer),
r5I_B25 (line levels need an oscilloscope; with X1's FRAM CS at power-off), r5I_B52 (the two-chroot run, H1),
r5I_B58 (real Safari / mobile spot check), r5I_U14 (444 "(agent, …)" decisions to review).

## 1. OR5.a closure table

### Findings (`S/u35r/findings/FINDINGS.md`)

| id | where | subject | state | evidence | W |
|---|---|---|---|---|---|
| r5I_F1 | FINDINGS:6 | twin CI `--only` filters the suite part only | D: already stated | `scripts/run_digital_twin_ci.sh:18` (`--help`) | N |
| r5I_F2 | FINDINGS:9 | no `ss` → holder-list diagnostic lost | D: one comment at the call | `run_digital_twin_ci.sh:105` (an or-true keeps the run going), nothing reads the list | N |
| r5I_F3 | FINDINGS:12 | `sgp40_voc_algorithm_quality` red 2/15 on the twin at 32768 only | F in the last round (OR17.a twin correction), stage dependence root-caused first | `r3/m/twin.md:50`: fake raw walk 1000 ticks/sample leaves the index constant | Y (real raw walk) |
| r5I_F4 | FINDINGS:14 | FRAM allocation test header claims "any comparable per-call allocation" | F: header narrowed to what its ceiling catches | `tests/test_asy_fram_allocation_budget.py:1-3`; `r3/m/plants.md:118-122` (16 B survives) | N |
| r5I_F5 | FINDINGS:16 | R3 twin record row holds one (c) case (dev's 512 B ring) | R: subject sized since | `devices/dev.toml:64-66` `rx_ring = 8192` (`33974760`) | N |
| r5I_F6 | FINDINGS:18 | hotspot case (b) soak invocation selects (b) alone | R: fixed in R4 | `tests_hardware/README.md:1027-1031` (module runs whole) | N |
| r5I_F7 | FINDINGS:22 | manual runner's DUT prompt cites a missing passage | R: passage exists | `tests_hardware/README.md:305`; `tests_hardware/manual/runner.py:93` | N |
| r5I_F8 | FINDINGS:24 | L.6.6 line "a rule no device TOML can trip is not written" vs `bus.i2c-frequency-range` | R: check kept as the boot-loop exception, line not placed | `buildgen/validate.py:536-546` (0 Hz divides by zero); `r1/B8/HANDBACK.md:191` (F1 restored); L.6.6 lists range checks | N |
| r5I_F9 | FINDINGS:26 | `disallow_any_explicit` exemptions remain (= B01, U02) | F: clear 7 modules, drop the baselines | `pyproject.toml:411-420` (5), `digital_twin/typecheck.ini:36-38` (machine), `host_typecheck.ini:44-46` (`scripts._hardware_verdict`) | N |

### BACKLOG.md (every item; owed-hardware rows each one line)

| id | where | subject | state | evidence | W |
|---|---|---|---|---|---|
| r5I_B01 | BACKLOG:19 | mypy disallows `Any`: baselines left | F (with F9, U02) | owner 2026-09-28 "do it in this audit" (BACKLOG:25); `tests_scripts/test_mypy_any_baseline.py:16` | N |
| r5I_B02 | BACKLOG:29 | tier/layering scan ran once; "re-running … future work" | N: standing per-change practice (CLAUDE.md, OR45.a containment) or owner-deferred goal | owner 2026-09-15/09-29 "highly important to be applied"; open-ended as written | N |
| r5I_B03 | BACKLOG:48 | ISL29125 shadow/chip divergence: fixed; `Overrange` half owed | R after S3b; lock fact at Part C.8 | `tests/test_asy_isl29125_driver.py::test_configure_never_exposes_…`; rides r5I_B17 | Y |
| r5I_B04 | BACKLOG:78 | W12 → live `Overrange` field | R: documented | Part M (`:11452`); `mockdata/samples.json`; device-script re-run rides S3b | Y |
| r5I_B05 | BACKLOG:93 | item 1, `_boot.py`'s `import sensortask.py` trace | D: trace to Part F, CLAUDE.md:95 repointed, stub removed | only citer `CLAUDE.md:95` ("BACKLOG.md #1") | N |
| r5I_B06 | BACKLOG:105 | item 2, config-schema migration risk | F with OR52.a (2)'s golden fixture; removed | Part C.5 (`:3356-3359`), `tests_scripts/test_stored_config_golden.py`; no `tests_scripts/golden/` yet | N |
| r5I_B07 | BACKLOG:111 | item 3, MicroPython version drift | R: documented | Part F.5; `CLAUDE.md:49-50`; no citer | N |
| r5I_B08 | BACKLOG:123 | item 4, `write_config()` needs no long-block coordination | D: Part F.2 / C.5 (deferred flush); removed | owner 2026-08-11; no citer | N |
| r5I_B09 | BACKLOG:131 | item 5 stub, UDP/captive-DNS verification closed | D: `tests_hardware/README.md` "Fourth pass" (:1479); 5 citers repointed | `tests/test_asy_udp_socket.py:450`, `tests_hardware/README.md:1363,1491,1513`, `tests_hardware/bench_control.py:266` | N |
| r5I_B10 | BACKLOG:141 | item 6 stub, Wi-Fi reachability probe | D: Part F.2; 2 citers repointed | `CLAUDE.md:220`, `tests/test_ntp_wifi_dns_integration.py:526` | N |
| r5I_B11 | BACKLOG:149 | item 8, rig capabilities stay `[MANUAL]` | D: `tests_hardware/README.md:1169` + Part E.6.6; removed | owner 2026-09-22 (no hardware bought); no citer | N |
| r5I_B12 | BACKLOG:161 | item 9 stub, Wi-Fi reconnect flakiness | D: `tests_hardware/README.md:1293`; citer repointed | `tests_hardware/bench/test_network_resilience.py:1040` | N |
| r5I_B13 | BACKLOG:171 | item 12, soft reset vs `ticks_ms()` | R: fact placed, only BACKLOG:526 cites it | `tests_hardware/README.md:1236` | N |
| r5I_B14 | BACKLOG:182 | item 29, spurious `WLAN_AUTH_FAILED` | R: fact placed, no citer left | Part C.7.1 (`:3749`); `src/asy_wifi_service.py:609-610` | N |
| r5I_B15 | BACKLOG:200 | "How a sitting runs" (D1-D3) | R: duplicate | `tests_hardware/README.md:432-449` "How a round runs" | N |
| r5I_B16 | BACKLOG:209 | watchdog-starvation test ends with `hard_reset()` | F on a clean flash tier | `flash/test_watchdog_starvation.py` | Y |
| r5I_B17 | BACKLOG:217 | M1 + S3b, ISL29125 light programs | D: rig geometry and verdicts at `tests_hardware/README.md` rig section | owner at the bench, ~30 min | Y |
| r5I_B18 | BACKLOG:232 | R13 + N3, `wrnno` 54 vs a babbling peer | N: limitation (mock covers the logic) or kept owed | owner 2026-09-25 (bench lacks the peer), 2026-09-22 (no hardware bought); N3's changelog half see X2 | N |
| r5I_B19 | BACKLOG:241 | T4, FRAM command hold | D: Part F.3 `hold.fram_block`, J.6 | `flash/test_fram_storage.py::test_fram_command_hold_…` | Y |
| r5I_B20 | BACKLOG:252 | the two unfed boot stretches | D: Part N `boot.unfed_stretch_*`, `boot.setup_unit_stretch_ms` | boot log with feed stamps | Y |
| r5I_B21 | BACKLOG:264 | no-yield stretches, flash write loop gap | D: Part F.3 `stall.*` | `flash/test_memory_stress.py` (2 tests) | Y |
| r5I_B22 | BACKLOG:271 | loop lag under combined load | D: Part F.3 `lag.loop` | bench copy; flash copy permanently skipped (`8882a25b`) | Y |
| r5I_B23 | BACKLOG:281 | UART hazard run under API load | F (verdicts, elapsed vs 600 s) | `bench/test_uart_link_under_api_load.py` | Y |
| r5I_B24 | BACKLOG:289 | hard resets during natural FRAM backups | F | `bench/test_end_to_end_timing.py::test_real_hard_resets_…` | Y |
| r5I_B25 | BACKLOG:299 | SCL/SDA through a bus recovery | N: line levels need an oscilloscope, the held-SDA resets a script of their own; else limitation at Part F.5.1 | held-SDA test half is in the flash tier (`i2c_held_sda_recovery.py`) | Y (half) |
| r5I_B26 | BACKLOG:312 | free alarm count | D: Part F.1 | `timer_alarm_pool_exhaustion.py` | Y |
| r5I_B27 | BACKLOG:317 | idle poll rate | D: Part N `udp.poll_idle_ms` Basis | twin half needs no board (can run in R5) | part |
| r5I_B28 | BACKLOG:325 | SGP40 lost samples over 10 min | D: Part M.3 | `--duration short` soak | Y |
| r5I_B29 | BACKLOG:330 | SCD30 keeps `AmbPres` over a power cycle | D: Part M.2, fidelity row; the PUT half's instrument written for the last round | "no instrument yet" (BACKLOG:336) | Y |
| r5I_B30 | BACKLOG:342 | modlwip send stall, control image vs override | D: Part N bound, B.14.4; a failed bound goes to the owner | owner 2026-09-30; two flash cycles | Y |
| r5I_B31 | BACKLOG:362 | `env --tier bench` bridge under its recovery timer | D: Part N `tool.bench_bridge_*` Basis | host only | Y |
| r5I_B32 | BACKLOG:370 | hotspot role reversal's failed-credential cases | F | `bench/test_hotspot_role_reversal.py` stage 6 | Y |
| r5I_B33 | BACKLOG:385 | other chips ACK/NAK a general call | D: fidelity row; per-chip script for the last round | sweep records per-bus NAKs (`bus_topology_autodetect_and_hazard_sweep.py:104-123`) | Y |
| r5I_B34 | BACKLOG:391 | lone BMP3xx under general calls | F | `flash/test_bus_concurrency.py::test_bmp3xx_alone_…` | Y |
| r5I_B35 | BACKLOG:401 | SCD30 wrong CRC / interval 0 reaction | D: fidelity row | `flash/test_chip_conformance.py` (≤3 NVM writes) | Y |
| r5I_B36 | BACKLOG:410 | ISL29125 CONFIG1 write restarts a conversion? | D: fidelity row | probe keys `G01`/`G02` | Y |
| r5I_B37 | BACKLOG:419 | SGP40 unknown command | D: fidelity row; script for the last round | "Needs that device script" | Y |
| r5I_B38 | BACKLOG:424 | BMP3XX real calibration block | D: fidelity row | `bmp3xx_conformance_probe.py` `A02_calibration` | Y |
| r5I_B39 | BACKLOG:432 | bootloader BOOTSEL round trip | D: fidelity BOOTSEL row | `bench/test_reset_reasons.py::test_a_bootloader_…` | Y |
| r5I_B40 | BACKLOG:438 | every reset code via `/status` | D: `tests_hardware/README.md:924` "Reset codes proven" | `bench/test_reset_reasons.py` | Y |
| r5I_B41 | BACKLOG:449 | UART ring for the interrupts-off window | D: Part J.6/I.2 heap cost; **row text stale** ("512 B … until dev.toml sizes it") | `devices/dev.toml:64-66` 8192 since `33974760` | Y |
| r5I_B42 | BACKLOG:458 | `Altitude` applies while `AmbPres` is 0 | D: Part M.2 | 4 SCD30 NVM writes | Y |
| r5I_B43 | BACKLOG:465 | `env --tier bench` once more after the pins | F (host step) | `[tool.uv] required-version` | Y |
| r5I_B44 | BACKLOG:472 | default and gated round over the tooling files | F (three clean verdicts) | `scripts/uv_sync_retried.sh` in every runner | Y |
| r5I_B45 | BACKLOG:502 | bench `ResetErrors` budget | D: `tests_hardware/error_log_helpers.py` budget | owner 2026-09-26 (concurrent reset) | Y |
| r5I_B46 | BACKLOG:513 | S4, six-hour soak | F | Part N `l4.soak_request_failure_rate` | Y |
| r5I_B47 | BACKLOG:523 | G6, tick rollover on silicon | F | `scripts/run_bench_rollover_test.sh` | Y |
| r5I_B48 | BACKLOG:534 | F17, unintended resets across rounds | D: `tests_hardware/README.md` (or R if none occurs) | Part F.5.4 | Y |
| r5I_B49 | BACKLOG:552 | "still owed elsewhere" pointer | R with the section's rewrite | points to B52 and item 8 | Y |
| r5I_B50 | BACKLOG:558 | SPI RX overrun not retried | D: Part F.5.2 / C.6 (`:3036`, `:3139`); removed | owner 2026-09-24 | N |
| r5I_B51 | BACKLOG:562 | `arduino/` and the C reconciliation | O: stays (C-port kind) | OR5.a (3); `README.md` licences paragraph | N |
| r5I_B52 | BACKLOG:566-1121 | build-environment list since the legs (H1) | N: the owner's two-chroot run closes it | CLAUDE.md periodic-check rule (owner 2026-09-18); last entries 2026-11-04 | N |
| r5I_B53 | BACKLOG:1122 | Session 7 `max-args` ratchet, trixie leg | R: stale | `pyproject.toml:169` `max-args = 8`; leg covered by B52 | N |
| r5I_B54 | BACKLOG:1134 | `[device].name`/`hostname`/`hotspot_password` wired: done | R: documented | `buildgen/codegen.py:200-202`; Part L (`:10537`) | N |
| r5I_B55 | BACKLOG:1153 | UART fakes do not wait, deliberately | D: Part F.5.8 (`:7254`); removed | `tests/_uart_link_contract.py` | N |
| r5I_B56 | BACKLOG:1167 | three UART-audit findings left as they are | D: Part J (to place); agent 2026-09-11 → U14 list | not in Part J today | N |
| r5I_B57 | BACKLOG:1183 | standalone `mypy device_scripts` `Timer()` findings | D: `CLAUDE.md:963` (stub gap) gains device_scripts | same gap, same resolution | N |
| r5I_B58 | BACKLOG:1193 | manual Safari / mobile spot check | N: owner pass, else limitation at Part H.1 | "needs the project owner directly" | N |
| r5I_B59 | BACKLOG:1198 | UART link carries no sensor | O: documented, removed | owner 2026-08-20 `b6cb852`; Part J (`:9537`), `CLAUDE.md:144` | N |
| r5I_B60 | BACKLOG:1207 | final-wiring requirement fulfilled | R at D ("comes out when that audit closes") | Part A.10; `scripts/run_unix_port_integration.sh` | N |
| r5I_B61 | BACKLOG:1220 | config-duplication centralization | R: stale | no `_DEFAULT_CONFIG` in `src/`; per-driver `_VAL_*` + `@web` feed the site (Part C.5, K.4); dead pointers to `sensortask-wozi.py` and "Refactor targets" | N |
| r5I_B62 | BACKLOG:1225 | SystemService settings store grows | O: owner-deferred goal stays; fix its cite | owner 2026-08-11 `249f2ae`; `asy_system_service.py:78, :121` stale, schema now `:110` | N |
| r5I_B63 | BACKLOG:1230 | non-blocking alternative to blocking calls | O: owner-deferred goal stays | owner 2026-07-24/09-29; pointed to by `CLAUDE.md:212`, Part F.2 (`:7278`) | N |
| r5I_B64 | BACKLOG:1239 | resize the littlefs reservation | O: deferred goal with trigger | owner 2026-09-26; Part B.14.3 | N |
| r5I_B65 | BACKLOG:1241 | modlwip send stall, watched upstream | O: watch, trigger = anchor check | owner 2026-09-30; Part B.14.4 | N |
| r5I_B66 | BACKLOG:1247 | modlwip listener close, watched upstream | O: watch, trigger = anchor check | owner 2026-10-26; Part B.14.4 | N |
| r5I_B67 | BACKLOG:1259 | CI to Ubuntu 26.04 is its own step | D: Part B.10.1 (`:1705-1711`) takes the uutils facts; agent 2026-10-20 → U14 list | Part B.10.1 cites "BACKLOG.md's Ubuntu 26.04 entry" | N |

BACKLOG:1275 "Owner questions" is empty: nothing to close. After the B-rows, BACKLOG holds only owed hardware (what
round 1 leaves), the C-port item and the owner-deferred goals (`PROJECT_AUDIT_PLAN.md:73-74`).

### Markers (`git grep -nIE 'TODO|FIXME|XXX|open question|deferred'` minus the five paths): 131 hits

No TODO or FIXME exists. 18 hits are `PROJECT_AUDIT_PLAN.md`'s audit process (closes with the plan at D). 9 cite a
numbered BACKLOG stub (folded into B05, B09, B10, B12); 3 point to the deferred goal (B63); `BACKLOG.md:1051` is part
of B52. Excluded as prose that is no open item: 4 descriptions of BACKLOG (`BACKLOG.md:3`, `CLAUDE.md:488`,
`README.md:1220`, Part 0 `:8`), 6 rules and checklists (`CLAUDE.md:598`, Part H `:4423`, D `:4890`, K.9/K.10
`:10408`/`:10468`, `digital_twin/README.md:1180`), and 90 uses of the design term (deferred flush/write/final ACK/faults/
SIGINT delivery) or test data (`XXXX`). Found on the way, outside the regex:

| id | where | subject | state | evidence | W |
|---|---|---|---|---|---|
| r5I_X1 | `tests_hardware/README.md:1369-1386` | "Open on silicon" list (8 rows) outside BACKLOG's one owed list | D: each answer at its site; rows moved into BACKLOG's owed list or closed by round 1; the scope-only row joins B25 | DMA/UARTRSR, RUN-pin record, SCD30 read-before-command and cut NVM write, FRAM MISO idle, CS at power-off (oscilloscope), unplug timings, ASC restart | Y |
| r5I_X2 | `UART_C_PORT_CHANGELOG.md:144` | B20 names `wrnno` 10/11/14; the global catalog numbers the drain bound 54 | F: numbers aligned or stated as "at the time" (U37.04 (4)) | `buildgen/error_catalog.json:155`, `src/asy_uart_comm.py:142` | N |
| r5I_X3 | `tests_scripts/test_comment_block_cap.py:44`, `test_counter_steps.py:34` | empty `_HEADER_PENDING` / `_PENDING` with their stale-entry halves | F: removed (U37.02's rule, no dead code) | both `frozenset()`/`{}`; stale checks `:271-272`, `:168-170` | N |

### U37's items (`audit/actions/U37.md`)

| id | where | subject | state | evidence | W |
|---|---|---|---|---|---|
| r5I_U01 | U37.md:29 (2); SUPP_deps.md:835 | A.SDEP.25, second dependency check | F: every pin vs newest stable; "last re-check" re-dated | `CLAUDE.md:49-50` (last 2026-10-06, `v1.29.0`), `toolchain/versions.toml:10` | N (a new MicroPython pin would reopen round 1's image) |
| r5I_U02 | U37.md:42 | shrinking allow-lists removed once empty | F: none is empty — emptied first, then list, loader and stale test go | import placement `_PENDING` 70 (`test_import_placement.py:46-117`) + `PLC0415` scopes (`pyproject.toml:207,223,295`); citations 87; decision vocabulary 388; variant literals 5 (`test_no_variant_literals.py:27-33`); mypy 7 (F9) | N |
| r5I_U04 | U37.md:99 | knowledge base, fidelity table, side obligations | F: checks (1),(4),(5) owed | (6) met: `README.md:1206-1266` names every root doc; (2) statuses present `digital_twin/README.md:202`; (3) list current to 2026-11-04 (`BACKLOG.md:1115-1120`); (4) see X2 | part |
| r5I_U05 | U37.md:128 | BACKLOG's owed-hardware list | F: rewritten after round 1 to what it left | R3 prepared `BACKLOG.md:192-554`; B41's stale text | Y |
| r5I_U14 | U37.md:370 | owner review of decisions taken on the owner's behalf | N: the list put to the owner | 444 "(agent, 20…)" tags outside `audit/`, 11 "owner-reviewed"; B56, B67, release version `2.0` among them | N |
| r5I_U17 | U37.md:431 | owner-row trace, deleted/loosened tests, unexecuted lines | F (audit file only) | needs the final coverage run after the last code change | Y |

## 2. OR11 stray-file table

Scope checked: every tracked file outside the 20 listed directories (27 paths), every helper (non-`test_*`) file in the
code directories (353; each has a reader, the thinnest `tests/_littlefs_fake.py` and `tests_hardware/ntp_probe.py` with
one) and every device script (each run by a test or a sibling). Nothing is tracked that `.gitignore` ignores.

| id | path | why it looks stray | inbound references | migrate first | OR11.a timing |
|---|---|---|---|---|---|
| r5I_S01 | `tests_scripts/_citation_allowlist.txt` | temporary by design ("only shrinks"), 87 rows | `test_citations.py` (loader), `test_decision_vocabulary.py:18`, `test_no_variant_literals.py:30` | fix the 87 citing lines (README 29, SPEC 26, CLAUDE 14, BACKLOG 3 to deleted `HARDWARE_TEST_*`/`REAL_HARDWARE_TEST_QUEUE.md`) | final cleanup (U02) |
| r5I_S02 | `tests_scripts/_decision_vocab_allowlist.txt` | same, 388 rows | `test_decision_vocabulary.py` (loader), `test_citations.py:25`, `test_no_variant_literals.py:31` | actor tags on 388 texts (SPEC 63, `test_asy_wifi_service.py` 23, …) | final cleanup (U02) |
| r5I_S03 | `tests_scripts/golden/`, `tests_scripts/fixtures/api_reference/` in `test_no_variant_literals.py:16` | exemption prefixes for paths that do not exist | that line only | R5's golden fixtures (OR52.a (2)) land there, else the prefixes go | final cleanup |
| r5I_S04 | `_NOT_YET_CLEANED` in `test_no_variant_literals.py:27-33` | shrinking list, 5 entries (2 are S01/S02) | the test itself | the two test files and `novel_combo.toml` cleaned | final cleanup (U02) |
| r5I_S05 | `PROJECT_AUDIT_PLAN.md` | audit plan | `README.md:1259`, CI/lint exclusions, many docs | OR rows' forward value placed (PLAN D) | hardware follow-up's close (not now) |
| r5I_S06 | `audit/` (14,051 files; 13,607 under `artefacts/`, 11,352 `.log/.out/.txt`) | working records and raw logs | `README.md:1259`, scope exclusions | last commit holding it tagged and named in the final report | hardware follow-up's close (not now) |
| r5I_S07 | `UART_C_PORT_CHANGELOG.md` | marked temporary | README "Temporary", CLAUDE.md | — | stays until the post-audit C reconciliation |
| r5I_S08 | `HEAP_FRAGMENTATION_MEASUREMENTS.md` | name reads like a measurement log | 25 SPEC cites, `src/asy_fram_driver.py`, 7 tests | — (a method doc; its record is archived at `12640c2`) | stays |
| r5I_S09 | `mockdata/samples.json` | outside the directory list | `js/app.js`, README, SPEC, BACKLOG | — | stays |
| r5I_S10 | root configs (`.htmlvalidate.json`, `.stylelintrc.json`, `eslint.config.js`, `tsconfig*.json`, `vitest.config.js`, `package*.json`, `.nvmrc`, `uv.lock`, `host_typecheck.ini`, `.gitmodules`) | outside the directory list | `.github/workflows/ci.yml`, README, SPEC | — | stays |
| r5I_S11 | `tests/_littlefs_fake.py`, `tests_hardware/ntp_probe.py` | one reader each | `tests/test_asy_config_manager.py`; `tests_hardware/bench/test_network_resilience.py` | — | stays |
| r5I_S12 | `legacy/README.md` + `legacy/` (77 files) | reference-only | README "Further reading" | — | stays (legacy rule) |

Not tracked, so outside OR11: the worktree holds `build_{arzi,dev,grkizi,klkizi,schlafzi,wozi}.out` and a
`node_modules` symlink; `.gitignore` has no `*.out` and its `node_modules/` does not match a symlink, so a wholesale
`git add` would commit them.

## 3. Could not classify / notes

- `tests_hardware/README.md:1388-1990` still holds the "Third pass" … "Tenth pass" history sections (B02 points into
  the Tenth); R4's OR27.a territory, not an open item, so not a row.
- B41's row text and B62's line cites are stale and need the rewrite U05 does anyway.
- B33/B37/B29's PUT half have no instrument; written in R5 they run in the last round, otherwise each becomes a
  fidelity-row limitation, which would make them owner items.
